from pathlib import Path
from flask import Blueprint, current_app, jsonify, make_response, redirect, render_template, request, url_for

from .db import get_db
from .music import discover_tracks
from .usb import detect_usb_partitions, mount_usb_by_identifier, unmount_usb_by_identifier
from . import queries
from . import services

bp = Blueprint("main", __name__)
USB_ROLES = ["unknown", "library_input", "backup", "mp3_player"]


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/api/tracks")
def get_tracks():
    db = get_db()
    music_root = current_app.config["MUSIC_ROOT"]
    
    all_tracks = services.fetch_enriched_tracks(db, music_root)
    active_artist = request.args.get("artist", "").strip()
    active_album = request.args.get("album", "").strip()
    if active_artist == "__root__":
        active_album = ""

    artist_groups, album_groups, tracks = services.build_track_browse_groups(
        all_tracks,
        music_root,
        active_artist,
        active_album,
    )
    selected_count, selected_size_bytes = queries.get_selected_sync_stats(db)
    
    return jsonify({
        "tracks": tracks,
        "allTrackCount": len(all_tracks),
        "artistGroups": artist_groups,
        "albumGroups": album_groups,
        "activeArtist": active_artist,
        "activeAlbum": active_album,
        "selectedCount": selected_count,
        "selectedSizeHuman": services.format_bytes(selected_size_bytes),
        "musicRoot": music_root,
    })


@bp.get("/api/usb")
def get_usb():
    db = get_db()
    return jsonify({
        "devices": services.fetch_usb_devices(db),
        "roles": USB_ROLES
    })


@bp.get("/api/settings")
def get_settings():
    db = get_db()
    music_root = current_app.config["MUSIC_ROOT"]
    selected_count, selected_size_bytes = queries.get_selected_sync_stats(db)
    return jsonify({
        "musicRoot": music_root,
        "selectedCount": selected_count,
        "selectedSizeHuman": services.format_bytes(selected_size_bytes),
    })


@bp.post("/api/library/scan")
def scan_library():
    source = (request.json or {}).get("source_path", current_app.config["MUSIC_ROOT"]).strip()
    source_path = Path(source)
    tracks = discover_tracks(source_path)
    db = get_db()

    inserted = queries.upsert_tracks(db, tracks)
    db.commit()

    return jsonify({
        "success": True,
        "message": f"Scanned {len(tracks)} files from {source_path}. Added or updated {inserted} tracks.",
        "scannedCount": len(tracks),
        "insertedCount": inserted
    })


@bp.post("/api/tracks/<int:track_id>/toggle")
def toggle_track(track_id: int):
    db = get_db()
    queries.update_track_selection(db, track_id)
    db.commit()

    track_row = queries.get_track_by_id(db, track_id)
    track = services.enrich_track_for_display(track_row, current_app.config["MUSIC_ROOT"])
    
    selected_count, selected_size_bytes = queries.get_selected_sync_stats(db)
    
    return jsonify({
        "success": True,
        "track": track,
        "selectedCount": selected_count,
        "selectedSizeHuman": services.format_bytes(selected_size_bytes)
    })


@bp.post("/api/tracks/bulk")
def bulk_track_selection():
    data = request.json or {}
    scope = data.get("scope", "").strip()
    action = data.get("action", "").strip()
    value = data.get("value", "").strip()

    if action not in {"select", "clear"}:
        return jsonify({"success": False, "message": "Invalid bulk selection action."}), 400

    target = 1 if action == "select" else 0
    db = get_db()

    queries.bulk_update_tracks_selection(db, target, scope, value)

    if scope == "all":
        label = "all tracks"
    elif scope == "artist":
        if not value:
             return jsonify({"success": False, "message": "Missing artist for bulk selection."}), 400
        label = "Unknown Artist" if value == "__unknown__" else f"artist '{value}'"
    elif scope == "folder":
        if not value:
             return jsonify({"success": False, "message": "Missing folder for bulk selection."}), 400
        label = f"folder '{Path(value).name or value}'"
    else:
        return jsonify({"success": False, "message": "Invalid bulk selection scope."}), 400

    db.commit()
    verb = "Selected" if target == 1 else "Cleared"
    selected_count, selected_size_bytes = queries.get_selected_sync_stats(db)
    
    return jsonify({
        "success": True, 
        "message": f"{verb} tracks for {label}.",
        "selectedCount": selected_count,
        "selectedSizeHuman": services.format_bytes(selected_size_bytes)
    })


@bp.post("/api/usb/register")
def register_usb():
    data = request.json or {}
    label = data.get("label", "").strip()
    device_uuid = data.get("device_uuid", "").strip()
    mount_path = data.get("mount_path", "").strip()
    role = data.get("role", "unknown").strip()

    if not label or not device_uuid:
        return jsonify({"success": False, "message": "Label and UUID are required to register a USB device."}), 400

    if role not in USB_ROLES:
        role = "unknown"

    db = get_db()
    queries.upsert_usb_device(db, label, device_uuid, mount_path, role)
    db.commit()
    return jsonify({"success": True, "message": f"Saved USB device '{label}' as role '{role}'."})


@bp.post("/api/usb/<int:usb_id>/role")
def update_usb_role(usb_id: int):
    data = request.json or {}
    role = data.get("role", "unknown").strip()
    if role not in USB_ROLES:
        return jsonify({"success": False, "message": "Invalid USB role."}), 400

    db = get_db()
    usb = queries.get_usb_device_by_id(db, usb_id)
    if usb is None:
        return jsonify({"success": False, "message": "USB device not found."}), 404

    queries.update_usb_device_role(db, usb_id, role)
    db.commit()
    return jsonify({"success": True, "message": f"Updated '{usb['label']}' role to '{role}'."})


@bp.post("/api/usb/<int:usb_id>/mount")
def mount_usb(usb_id: int):
    db = get_db()
    usb = queries.get_usb_device_by_id(db, usb_id)
    if usb is None:
         return jsonify({"success": False, "message": "USB device not found."}), 404

    mount_path = mount_usb_by_identifier(usb["device_uuid"])
    if not mount_path:
        return jsonify({"success": False, "message": f"Could not mount '{usb['label']}'. Is it still plugged in?"}), 500

    queries.update_usb_device_mount(db, usb_id, mount_path)
    db.commit()
    return jsonify({"success": True, "message": f"Mounted '{usb['label']}' at {mount_path}.", "mountPath": mount_path})


@bp.post("/api/usb/<int:usb_id>/unmount")
def unmount_usb(usb_id: int):
    db = get_db()
    usb = queries.get_usb_device_by_id(db, usb_id)
    if usb is None:
         return jsonify({"success": False, "message": "USB device not found."}), 404

    ok = unmount_usb_by_identifier(usb["device_uuid"])
    if not ok:
        return jsonify({"success": False, "message": f"Could not unmount '{usb['label']}'."}), 500

    queries.update_usb_device_mount(db, usb_id, "")
    db.commit()
    return jsonify({"success": True, "message": f"Unmounted '{usb['label']}'."})


@bp.post("/api/usb/detect")
def detect_usb():
    try:
        devices = detect_usb_partitions()
    except RuntimeError as exc:
        current_app.logger.error(f"USB detection runtime error: {exc}")
        return jsonify({"success": False, "message": f"USB detection failed: {exc}"}), 500

    db = get_db()
    queries.delete_invalid_usb_devices(db)
    
    for device in devices:
        queries.upsert_usb_device_from_detect(
            db,
            device["label"],
            device["device_uuid"],
            device["mount_path"]
        )

    db.commit()
    return jsonify({"success": True, "message": f"Detected {len(devices)} USB partition(s).", "devices": services.fetch_usb_devices(db)})


@bp.post("/api/actions/import-library-input")
def import_library_input():
    db = get_db()
    success, message = services.run_import_library_input(db)
    db.commit()
    return jsonify({"success": success, "message": message})


@bp.post("/api/actions/sync-mp3")
def sync_mp3():
    db = get_db()
    success, message = services.run_sync_mp3(db)
    db.commit()
    return jsonify({"success": success, "message": message})


@bp.post("/api/actions/backup-library")
def backup_library():
    db = get_db()
    success, message = services.run_backup_library(db)
    db.commit()
    return jsonify({"success": success, "message": message})
