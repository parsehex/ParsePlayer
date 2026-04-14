from pathlib import Path
from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, url_for

from .db import get_db
from .music import discover_tracks
from .usb import detect_usb_partitions, mount_usb_by_identifier, unmount_usb_by_identifier
from . import queries
from . import services

bp = Blueprint("main", __name__)
USB_ROLES = ["unknown", "library_input", "backup", "mp3_player"]


@bp.get("/")
def index():
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
    
    return render_template(
        "index.html",
        tracks=tracks,
        all_track_count=len(all_tracks),
        artist_groups=artist_groups,
        album_groups=album_groups,
        active_artist=active_artist,
        active_album=active_album,
        usb_devices=services.fetch_usb_devices(db),
        selected_count=selected_count,
        selected_size_human=services.format_bytes(selected_size_bytes),
        music_root=music_root,
        usb_roles=USB_ROLES,
    )


@bp.get("/settings")
def settings():
    db = get_db()
    music_root = current_app.config["MUSIC_ROOT"]
    selected_count, selected_size_bytes = queries.get_selected_sync_stats(db)
    return render_template(
        "settings.html",
        music_root=music_root,
        selected_count=selected_count,
        selected_size_human=services.format_bytes(selected_size_bytes),
    )


@bp.post("/library/scan")
def scan_library():
    source = request.form.get("source_path", current_app.config["MUSIC_ROOT"]).strip()
    source_path = Path(source)
    tracks = discover_tracks(source_path)
    db = get_db()

    inserted = queries.upsert_tracks(db, tracks)
    db.commit()

    flash(f"Scanned {len(tracks)} files from {source_path}. Added or updated {inserted} tracks.", "success")
    return_to = request.form.get("return_to", "main.index").strip()
    if return_to == "main.settings":
        return redirect(url_for("main.settings"))
    return redirect(url_for("main.index"))


@bp.post("/tracks/<int:track_id>/toggle")
def toggle_track(track_id: int):
    db = get_db()
    queries.update_track_selection(db, track_id)
    db.commit()

    track_row = queries.get_track_by_id(db, track_id)
    track = services.enrich_track_for_display(track_row, current_app.config["MUSIC_ROOT"])
    active_artist, active_album = services.active_browse_from_request()
    
    all_tracks = services.fetch_enriched_tracks(db, current_app.config["MUSIC_ROOT"])
    artist_groups, album_groups, tracks = services.build_track_browse_groups(
        all_tracks,
        current_app.config["MUSIC_ROOT"],
        active_artist,
        active_album,
    )
    selected_count, selected_size_bytes = queries.get_selected_sync_stats(db)
    
    return make_response(
        render_template(
            "partials/track_toggle_response.html",
            track=track,
            active_artist=active_artist,
            active_album=active_album,
            selected_count=selected_count,
            selected_size_human=services.format_bytes(selected_size_bytes),
            artist_groups=artist_groups,
            album_groups=album_groups,
            tracks=tracks,
            all_track_count=len(all_tracks),
        )
    )


@bp.post("/tracks/bulk")
def bulk_track_selection():
    scope = request.form.get("scope", "").strip()
    action = request.form.get("action", "").strip()
    value = request.form.get("value", "").strip()
    return_artist = request.form.get("return_artist", "").strip()
    return_album = request.form.get("return_album", "").strip()

    if action not in {"select", "clear"}:
        flash("Invalid bulk selection action.", "error")
        return redirect(url_for("main.index", artist=return_artist, album=return_album))

    target = 1 if action == "select" else 0
    db = get_db()

    queries.bulk_update_tracks_selection(db, target, scope, value)

    if scope == "all":
        label = "all tracks"
    elif scope == "artist":
        if not value:
            flash("Missing artist for bulk selection.", "error")
            return redirect(url_for("main.index", artist=return_artist, album=return_album))
        label = "Unknown Artist" if value == "__unknown__" else f"artist '{value}'"
    elif scope == "folder":
        if not value:
            flash("Missing folder for bulk selection.", "error")
            return redirect(url_for("main.index", artist=return_artist, album=return_album))
        label = f"folder '{Path(value).name or value}'"
    else:
        flash("Invalid bulk selection scope.", "error")
        return redirect(url_for("main.index", artist=return_artist, album=return_album))

    db.commit()
    verb = "Selected" if target == 1 else "Cleared"
    flash(f"{verb} tracks for {label}.", "success")
    if not return_artist:
        return_album = ""
    return redirect(url_for("main.index", artist=return_artist, album=return_album))


@bp.post("/usb/register")
def register_usb():
    label = request.form.get("label", "").strip()
    device_uuid = request.form.get("device_uuid", "").strip()
    mount_path = request.form.get("mount_path", "").strip()
    role = request.form.get("role", "unknown").strip()

    if not label or not device_uuid:
        flash("Label and UUID are required to register a USB device.", "error")
        return redirect(url_for("main.index"))

    if role not in USB_ROLES:
        role = "unknown"

    db = get_db()
    queries.upsert_usb_device(db, label, device_uuid, mount_path, role)
    db.commit()
    flash(f"Saved USB device '{label}' as role '{role}'.", "success")
    return redirect(url_for("main.index"))


@bp.post("/usb/<int:usb_id>/role")
def update_usb_role(usb_id: int):
    role = request.form.get("role", "unknown").strip()
    if role not in USB_ROLES:
        flash("Invalid USB role.", "error")
        return redirect(url_for("main.index"))

    db = get_db()
    usb = queries.get_usb_device_by_id(db, usb_id)
    if usb is None:
        flash("USB device not found.", "error")
        return redirect(url_for("main.index"))

    queries.update_usb_device_role(db, usb_id, role)
    db.commit()
    flash(f"Updated '{usb['label']}' role to '{role}'.", "success")
    return redirect(url_for("main.index"))


@bp.post("/usb/<int:usb_id>/mount")
def mount_usb(usb_id: int):
    db = get_db()
    usb = queries.get_usb_device_by_id(db, usb_id)
    if usb is None:
        flash("USB device not found.", "error")
        return redirect(url_for("main.index"))

    mount_path = mount_usb_by_identifier(usb["device_uuid"])
    if not mount_path:
        flash(f"Could not mount '{usb['label']}'. Is it still plugged in?", "error")
        return redirect(url_for("main.index"))

    queries.update_usb_device_mount(db, usb_id, mount_path)
    db.commit()
    flash(f"Mounted '{usb['label']}' at {mount_path}.", "success")
    return redirect(url_for("main.index"))


@bp.post("/usb/<int:usb_id>/unmount")
def unmount_usb(usb_id: int):
    db = get_db()
    usb = queries.get_usb_device_by_id(db, usb_id)
    if usb is None:
        flash("USB device not found.", "error")
        return redirect(url_for("main.index"))

    ok = unmount_usb_by_identifier(usb["device_uuid"])
    if not ok:
        flash(f"Could not unmount '{usb['label']}'.", "error")
        return redirect(url_for("main.index"))

    queries.update_usb_device_mount(db, usb_id, "")
    db.commit()
    flash(f"Unmounted '{usb['label']}'.", "success")
    return redirect(url_for("main.index"))


@bp.post("/usb/detect")
def detect_usb():
    try:
        devices = detect_usb_partitions()
    except RuntimeError as exc:
        current_app.logger.error(f"USB detection runtime error: {exc}")
        flash(f"USB detection failed: {exc}", "error")
        return redirect(url_for("main.index"))

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
    flash(f"Detected {len(devices)} USB partition(s).", "success")
    return redirect(url_for("main.index"))


@bp.post("/actions/import-library-input")
def import_library_input():
    db = get_db()
    success, message = services.run_import_library_input(db)
    db.commit()
    
    if success:
        flash(message, "success")
    else:
        flash(message, "error")
        
    return redirect(url_for("main.index"))


@bp.post("/actions/sync-mp3")
def sync_mp3():
    db = get_db()
    success, message = services.run_sync_mp3(db)
    db.commit()

    if success:
        flash(message, "success")
    else:
        flash(message, "error")
        
    return redirect(url_for("main.index"))


@bp.post("/actions/backup-library")
def backup_library():
    db = get_db()
    success, message = services.run_backup_library(db)
    db.commit()

    if success:
        flash(message, "success")
    else:
        flash(message, "error")

    return redirect(url_for("main.index"))
