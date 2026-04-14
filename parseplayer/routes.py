from pathlib import Path
import shutil
from collections import defaultdict
from urllib.parse import parse_qs, urlparse
import os

from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, url_for
import json

from .db import get_db
from .music import SUPPORTED_EXTENSIONS, discover_tracks
from .usb import detect_usb_partitions, mount_usb_by_identifier, unmount_usb_by_identifier

bp = Blueprint("main", __name__)
USB_ROLES = ["unknown", "library_input", "backup", "mp3_player"]


def _fetch_tracks():
    db = get_db()
    rows = db.execute(
        """
        SELECT id, path, title, artist, selected_for_sync, updated_at
        FROM tracks
        ORDER BY selected_for_sync DESC, artist IS NULL, artist, title
        """
    ).fetchall()
    return [_enrich_track_for_display(row) for row in rows]


def _derive_virtual_artist_album(track_path: str, music_root: str) -> tuple[str, str]:
    root = Path(music_root).resolve()
    path = Path(track_path).resolve()

    try:
        rel = path.relative_to(root)
        parts = rel.parts
        if len(parts) >= 3:
            return parts[0], parts[1]
        if len(parts) == 2:
            return parts[0], "[No Album]"
        return "[Music Root]", "[No Album]"
    except ValueError:
        parent = path.parent
        artist = parent.parent.name if parent.parent != parent else "[Unknown Artist]"
        album = parent.name or "[No Album]"
        return artist, album


def _enrich_track_for_display(track_row):
    track = dict(track_row)
    artist, album = _derive_virtual_artist_album(track["path"], current_app.config["MUSIC_ROOT"])
    track["virtual_artist"] = artist
    track["virtual_album"] = album
    return track


def _active_browse_from_request() -> tuple[str, str]:
    """Read current browse scope from htmx current URL when available."""
    current_url = request.headers.get("HX-Current-URL", "")
    if not current_url:
        return "", ""

    query = parse_qs(urlparse(current_url).query)
    artist = (query.get("artist", [""])[0] or "").strip()
    album = (query.get("album", [""])[0] or "").strip()
    return artist, album


def _fetch_usb_devices():
    db = get_db()
    rows = db.execute(
        """
        SELECT id, label, device_uuid, mount_path, role, last_seen_at
        FROM usb_devices
        WHERE mount_path NOT IN ('/', '/boot', '/boot/firmware')
        ORDER BY role, label
        """
    ).fetchall()

    live_lookup: dict[str, dict[str, str]] = {}
    try:
        for item in detect_usb_partitions():
            live_lookup[item["device_uuid"]] = item
    except RuntimeError:
        live_lookup = {}

    devices: list[dict] = []
    for row in rows:
        item = dict(row)
        live = live_lookup.get(item["device_uuid"])
        if live:
            item["label"] = live.get("display_name") or live.get("label") or item["label"]
            item["mount_path"] = live.get("mount_path") or item["mount_path"]
            item["device_path"] = live.get("device_path") or item["device_uuid"]
            item["size_human"] = live.get("size_human") or "-"
            item["is_connected"] = True
        else:
            item["device_path"] = item["device_uuid"] if str(item["device_uuid"]).startswith("/dev/") else "-"
            item["size_human"] = "-"
            item["is_connected"] = False

        uuid_text = str(item["device_uuid"])
        if uuid_text.startswith("/dev/") or len(uuid_text) <= 14:
            item["uuid_short"] = uuid_text
        else:
            item["uuid_short"] = f"{uuid_text[:8]}...{uuid_text[-4:]}"
        devices.append(item)

    return devices


def _fetch_sync_count() -> int:
    count, _size_bytes = _fetch_selected_sync_stats()
    return count


def _fetch_selected_sync_stats() -> tuple[int, int]:
    db = get_db()
    rows = db.execute("SELECT path FROM tracks WHERE selected_for_sync = 1").fetchall()
    total_bytes = 0
    for row in rows:
        try:
            total_bytes += os.path.getsize(row["path"])
        except OSError:
            continue
    return len(rows), total_bytes


def _format_bytes(byte_count: int) -> str:
    size = float(byte_count)
    units = ["B", "KB", "MB", "GB", "TB"]
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    if index == 0:
        return f"{int(size)} {units[index]}"
    return f"{size:.1f} {units[index]}"


def _upsert_tracks(db, tracks: list[dict[str, str | None]]) -> int:
    inserted = 0
    for track in tracks:
        result = db.execute(
            """
            INSERT INTO tracks (path, title, artist)
            VALUES (?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                title = excluded.title,
                artist = excluded.artist,
                updated_at = CURRENT_TIMESTAMP
            """,
            (track["path"], track["title"], track["artist"]),
        )
        if result.rowcount == 1:
            inserted += 1
    return inserted


def _build_track_browse_groups(
    tracks,
    music_root: str,
    active_artist: str,
    active_album: str,
) -> tuple[list[dict], list[dict], list]:
    music_root_path = Path(music_root).resolve()
    artist_totals: dict[str, dict[str, int | str]] = defaultdict(
        lambda: {"label": "", "folder_path": "", "total": 0, "selected": 0}
    )
    album_totals: dict[str, dict[str, int | str]] = defaultdict(
        lambda: {"label": "", "folder_path": "", "total": 0, "selected": 0}
    )

    normalized_rows: list[dict] = []

    for track in tracks:
        track_path = Path(track["path"])
        parent_path = track_path.parent.resolve()
        selected = 1 if track["selected_for_sync"] else 0

        try:
            relative_file = track_path.resolve().relative_to(music_root_path)
            parts = relative_file.parts
        except ValueError:
            parts = ()

        artist_key = parts[0] if len(parts) >= 2 else "__root__"
        artist_label = artist_key if artist_key != "__root__" else "[Music Root]"
        artist_folder_path = str(music_root_path / artist_key) if artist_key != "__root__" else str(music_root_path)

        artist_totals[artist_key]["label"] = artist_label
        artist_totals[artist_key]["folder_path"] = artist_folder_path
        artist_totals[artist_key]["total"] = int(artist_totals[artist_key]["total"]) + 1
        artist_totals[artist_key]["selected"] = int(artist_totals[artist_key]["selected"]) + selected

        album_key = parts[1] if len(parts) >= 3 else ""
        album_label = album_key
        album_folder_path = str(Path(artist_folder_path) / album_key) if album_key else ""

        normalized_rows.append(
            {
                "track": track,
                "artist_key": artist_key,
                "album_key": album_key,
                "parent_path": parent_path,
            }
        )

        if active_artist and artist_key == active_artist and album_key:
            album_totals[album_key]["label"] = album_label
            album_totals[album_key]["folder_path"] = album_folder_path
            album_totals[album_key]["total"] = int(album_totals[album_key]["total"]) + 1
            album_totals[album_key]["selected"] = int(album_totals[album_key]["selected"]) + selected

    artist_groups = [
        {
            "key": key,
            "label": data["label"],
            "folder_path": data["folder_path"],
            "total": int(data["total"]),
            "selected": int(data["selected"]),
            "is_active": key == active_artist,
        }
        for key, data in artist_totals.items()
    ]
    album_groups = [
        {
            "key": key,
            "label": data["label"],
            "folder_path": data["folder_path"],
            "total": int(data["total"]),
            "selected": int(data["selected"]),
            "is_active": key == active_album,
        }
        for key, data in album_totals.items()
    ]

    artist_groups.sort(key=lambda item: str(item["label"]).lower())
    album_groups.sort(key=lambda item: str(item["label"]).lower())

    filtered_tracks: list = []
    for row in normalized_rows:
        if active_artist and row["artist_key"] != active_artist:
            continue
        if active_album and row["album_key"] != active_album:
            continue
        filtered_tracks.append(row["track"])

    filtered_tracks.sort(
        key=lambda track: (
            -int(track["selected_for_sync"]),
            (track["artist"] or "").lower(),
            str(track["title"]).lower(),
        )
    )

    # If the selected artist no longer exists, reset the scoped browse.
    if active_artist and all(group["key"] != active_artist for group in artist_groups):
        active_artist = ""
        active_album = ""
        filtered_tracks = list(tracks)

    if active_album and active_artist and all(group["key"] != active_album for group in album_groups):
        active_album = ""

    return artist_groups, album_groups, filtered_tracks


@bp.get("/")
def index():
    music_root = current_app.config["MUSIC_ROOT"]
    all_tracks = _fetch_tracks()
    active_artist = request.args.get("artist", "").strip()
    active_album = request.args.get("album", "").strip()
    if active_artist == "__root__":
        active_album = ""

    artist_groups, album_groups, tracks = _build_track_browse_groups(
        all_tracks,
        music_root,
        active_artist,
        active_album,
    )
    selected_count, selected_size_bytes = _fetch_selected_sync_stats()
    return render_template(
        "index.html",
        tracks=tracks,
        all_track_count=len(all_tracks),
        artist_groups=artist_groups,
        album_groups=album_groups,
        active_artist=active_artist,
        active_album=active_album,
        usb_devices=_fetch_usb_devices(),
        selected_count=selected_count,
        selected_size_human=_format_bytes(selected_size_bytes),
        music_root=music_root,
        usb_roles=USB_ROLES,
    )


@bp.get("/settings")
def settings():
    music_root = current_app.config["MUSIC_ROOT"]
    selected_count, selected_size_bytes = _fetch_selected_sync_stats()
    return render_template(
        "settings.html",
        music_root=music_root,
        selected_count=selected_count,
        selected_size_human=_format_bytes(selected_size_bytes),
    )


@bp.post("/library/scan")
def scan_library():
    source = request.form.get("source_path", current_app.config["MUSIC_ROOT"]).strip()
    source_path = Path(source)
    tracks = discover_tracks(source_path)
    db = get_db()

    inserted = _upsert_tracks(db, tracks)

    db.commit()
    flash(f"Scanned {len(tracks)} files from {source_path}. Added or updated {inserted} tracks.", "success")
    return_to = request.form.get("return_to", "main.index").strip()
    if return_to == "main.settings":
        return redirect(url_for("main.settings"))
    return redirect(url_for("main.index"))


@bp.post("/tracks/<int:track_id>/toggle")
def toggle_track(track_id: int):
    db = get_db()
    db.execute(
        """
        UPDATE tracks
        SET selected_for_sync = CASE selected_for_sync WHEN 1 THEN 0 ELSE 1 END,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (track_id,),
    )
    db.commit()

    track_row = db.execute(
        "SELECT id, title, artist, path, selected_for_sync FROM tracks WHERE id = ?",
        (track_id,),
    ).fetchone()
    track = _enrich_track_for_display(track_row)
    active_artist, active_album = _active_browse_from_request()
    all_tracks = _fetch_tracks()
    artist_groups, album_groups, tracks = _build_track_browse_groups(
        all_tracks,
        current_app.config["MUSIC_ROOT"],
        active_artist,
        active_album,
    )
    selected_count, selected_size_bytes = _fetch_selected_sync_stats()
    response = make_response(
        render_template(
            "partials/track_toggle_response.html",
            track=track,
            active_artist=active_artist,
            active_album=active_album,
            selected_count=selected_count,
            selected_size_human=_format_bytes(selected_size_bytes),
            artist_groups=artist_groups,
            album_groups=album_groups,
            tracks=tracks,
            all_track_count=len(all_tracks),
        )
    )
    return response


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

    if scope == "all":
        db.execute(
            "UPDATE tracks SET selected_for_sync = ?, updated_at = CURRENT_TIMESTAMP",
            (target,),
        )
        label = "all tracks"
    elif scope == "artist":
        if not value:
            flash("Missing artist for bulk selection.", "error")
            return redirect(url_for("main.index", artist=return_artist, album=return_album))
        if value == "__unknown__":
            db.execute(
                """
                UPDATE tracks
                SET selected_for_sync = ?, updated_at = CURRENT_TIMESTAMP
                WHERE artist IS NULL OR artist = ''
                """,
                (target,),
            )
            label = "Unknown Artist"
        else:
            db.execute(
                """
                UPDATE tracks
                SET selected_for_sync = ?, updated_at = CURRENT_TIMESTAMP
                WHERE artist = ?
                """,
                (target, value),
            )
            label = f"artist '{value}'"
    elif scope == "folder":
        if not value:
            flash("Missing folder for bulk selection.", "error")
            return redirect(url_for("main.index", artist=return_artist, album=return_album))
        db.execute(
            """
            UPDATE tracks
            SET selected_for_sync = ?, updated_at = CURRENT_TIMESTAMP
            WHERE path = ? OR path LIKE ?
            """,
            (target, value, f"{value}/%"),
        )
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
    db.execute(
        """
        INSERT INTO usb_devices (label, device_uuid, mount_path, role, last_seen_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(device_uuid) DO UPDATE SET
            label = excluded.label,
            mount_path = excluded.mount_path,
            role = excluded.role,
            last_seen_at = CURRENT_TIMESTAMP
        """,
        (label, device_uuid, mount_path, role),
    )
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
    usb = db.execute("SELECT label FROM usb_devices WHERE id = ?", (usb_id,)).fetchone()
    if usb is None:
        flash("USB device not found.", "error")
        return redirect(url_for("main.index"))

    db.execute(
        """
        UPDATE usb_devices
        SET role = ?,
            last_seen_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (role, usb_id),
    )
    db.commit()
    flash(f"Updated '{usb['label']}' role to '{role}'.", "success")
    return redirect(url_for("main.index"))


@bp.post("/usb/<int:usb_id>/mount")
def mount_usb(usb_id: int):
    db = get_db()
    usb = db.execute("SELECT label, device_uuid FROM usb_devices WHERE id = ?", (usb_id,)).fetchone()
    if usb is None:
        flash("USB device not found.", "error")
        return redirect(url_for("main.index"))

    mount_path = mount_usb_by_identifier(usb["device_uuid"])
    if not mount_path:
        flash(f"Could not mount '{usb['label']}'. Is it still plugged in?", "error")
        return redirect(url_for("main.index"))

    db.execute(
        "UPDATE usb_devices SET mount_path = ?, last_seen_at = CURRENT_TIMESTAMP WHERE id = ?",
        (mount_path, usb_id),
    )
    db.commit()
    flash(f"Mounted '{usb['label']}' at {mount_path}.", "success")
    return redirect(url_for("main.index"))


@bp.post("/usb/<int:usb_id>/unmount")
def unmount_usb(usb_id: int):
    db = get_db()
    usb = db.execute("SELECT label, device_uuid FROM usb_devices WHERE id = ?", (usb_id,)).fetchone()
    if usb is None:
        flash("USB device not found.", "error")
        return redirect(url_for("main.index"))

    ok = unmount_usb_by_identifier(usb["device_uuid"])
    if not ok:
        flash(f"Could not unmount '{usb['label']}'.", "error")
        return redirect(url_for("main.index"))

    db.execute(
        "UPDATE usb_devices SET mount_path = '', last_seen_at = CURRENT_TIMESTAMP WHERE id = ?",
        (usb_id,),
    )
    db.commit()
    flash(f"Unmounted '{usb['label']}'.", "success")
    return redirect(url_for("main.index"))


@bp.post("/usb/detect")
def detect_usb():
    try:
        devices = detect_usb_partitions()
    except RuntimeError as exc:
        flash(f"USB detection failed: {exc}", "error")
        return redirect(url_for("main.index"))

    db = get_db()
    # Clean up legacy rows created before strict USB filtering existed.
    db.execute(
        "DELETE FROM usb_devices WHERE mount_path IN ('/', '/boot', '/boot/firmware')"
    )
    for device in devices:
        db.execute(
            """
            INSERT INTO usb_devices (label, device_uuid, mount_path, role, last_seen_at)
            VALUES (?, ?, ?, 'unknown', CURRENT_TIMESTAMP)
            ON CONFLICT(device_uuid) DO UPDATE SET
                label = excluded.label,
                mount_path = excluded.mount_path,
                role = usb_devices.role,
                last_seen_at = CURRENT_TIMESTAMP
            """,
            (device["label"], device["device_uuid"], device["mount_path"]),
        )

    db.commit()
    flash(f"Detected {len(devices)} USB partition(s).", "success")
    return redirect(url_for("main.index"))


@bp.post("/actions/import-library-input")
def import_library_input():
    db = get_db()
    source_device = db.execute(
        "SELECT label, device_uuid, mount_path FROM usb_devices WHERE role = 'library_input' LIMIT 1"
    ).fetchone()

    if source_device is None:
        flash("No USB marked as library_input. Detect devices and assign one.", "error")
        return redirect(url_for("main.index"))

    device_identifier = source_device["device_uuid"]
    was_mounted = bool((source_device["mount_path"] or "").strip())

    raw_mount = source_device["mount_path"] or ""
    if not raw_mount or not Path(raw_mount).is_dir():
        raw_mount = mount_usb_by_identifier(device_identifier)
        if not raw_mount:
            flash(f"Could not mount '{source_device['label']}'. Is it still plugged in?", "error")
            return redirect(url_for("main.index"))
        db.execute(
            "UPDATE usb_devices SET mount_path = ?, last_seen_at = CURRENT_TIMESTAMP WHERE device_uuid = ?",
            (raw_mount, device_identifier),
        )

    mount_path = Path(raw_mount)
    if not mount_path.exists() or not mount_path.is_dir():
        flash(f"Library input USB mount path is unavailable: {mount_path}", "error")
        return redirect(url_for("main.index"))

    library_root = Path(current_app.config["MUSIC_ROOT"])
    library_root.mkdir(parents=True, exist_ok=True)

    copied_files = 0
    for source_file in mount_path.rglob("*"):
        if not source_file.is_file() or source_file.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        relative_path = source_file.relative_to(mount_path)
        target_file = library_root / relative_path
        target_file.parent.mkdir(parents=True, exist_ok=True)

        # Copying with metadata keeps modified times for easier future sync logic.
        shutil.copy2(source_file, target_file)
        copied_files += 1

    tracks = discover_tracks(library_root)
    indexed = _upsert_tracks(db, tracks)
    details = (
        f"Imported {copied_files} file(s) from '{source_device['label']}' into '{library_root}'. "
        f"Indexed {indexed} track record(s)."
    )
    db.execute(
        "INSERT INTO sync_runs (action, status, details) VALUES (?, ?, ?)",
        ("import_library_input", "completed", details),
    )

    if not was_mounted:
        unmount_usb_by_identifier(device_identifier)
        db.execute(
            "UPDATE usb_devices SET mount_path = '', last_seen_at = CURRENT_TIMESTAMP WHERE device_uuid = ?",
            (device_identifier,),
        )

    db.commit()
    flash(details, "success")
    return redirect(url_for("main.index"))


@bp.post("/actions/sync-mp3")
def sync_mp3():
    db = get_db()
    selected_count = _fetch_sync_count()
    mp3_device = db.execute(
        "SELECT id, label, mount_path FROM usb_devices WHERE role = 'mp3_player' LIMIT 1"
    ).fetchone()

    if mp3_device is None:
        flash("No USB marked as mp3_player. Detect devices and assign one.", "error")
        return redirect(url_for("main.index"))

    details = (
        f"Syncing {selected_count} selected tracks to '{mp3_device['label']}' "
        f"at '{mp3_device['mount_path'] or 'unknown mount'}'."
    )
    db.execute(
        "INSERT INTO sync_runs (action, status, details) VALUES (?, ?, ?)",
        ("sync_mp3", "queued", details),
    )
    db.commit()
    flash(details, "success")
    return redirect(url_for("main.index"))


@bp.post("/actions/backup-library")
def backup_library():
    db = get_db()
    backup_device = db.execute(
        "SELECT id, label, device_uuid, mount_path FROM usb_devices WHERE role = 'backup' LIMIT 1"
    ).fetchone()

    if backup_device is None:
        flash("No USB marked as backup. Detect devices and assign one.", "error")
        return redirect(url_for("main.index"))

    device_identifier = backup_device["device_uuid"]
    was_mounted = bool((backup_device["mount_path"] or "").strip())

    raw_mount = backup_device["mount_path"] or ""
    if not raw_mount or not Path(raw_mount).is_dir():
        raw_mount = mount_usb_by_identifier(device_identifier)
        if not raw_mount:
            flash(f"Could not mount '{backup_device['label']}'. Is it still plugged in?", "error")
            return redirect(url_for("main.index"))
        db.execute(
            "UPDATE usb_devices SET mount_path = ?, last_seen_at = CURRENT_TIMESTAMP WHERE device_uuid = ?",
            (raw_mount, device_identifier),
        )

    mount_path = Path(raw_mount)
    if not mount_path.exists() or not mount_path.is_dir():
        flash(f"Backup USB mount path is unavailable: {mount_path}", "error")
        return redirect(url_for("main.index"))

    library_root = Path(current_app.config["MUSIC_ROOT"])
    if not library_root.exists() or not library_root.is_dir():
        flash(f"Library source folder is unavailable: {library_root}", "error")
        return redirect(url_for("main.index"))

    backup_root = mount_path / "ParsePlayerLibraryBackup"
    backup_root.mkdir(parents=True, exist_ok=True)

    copied_files = 0
    for source_file in library_root.rglob("*"):
        if not source_file.is_file() or source_file.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        relative_path = source_file.relative_to(library_root)
        target_file = backup_root / relative_path
        target_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, target_file)
        copied_files += 1

    details = (
        f"Backed up {copied_files} file(s) from '{library_root}' to "
        f"'{backup_device['label']}' at '{backup_root}'."
    )
    db.execute(
        "INSERT INTO sync_runs (action, status, details) VALUES (?, ?, ?)",
        ("backup_library", "completed", details),
    )

    if not was_mounted:
        unmount_ok = unmount_usb_by_identifier(device_identifier)
        db.execute(
            "UPDATE usb_devices SET mount_path = ?, last_seen_at = CURRENT_TIMESTAMP WHERE device_uuid = ?",
            ("" if unmount_ok else raw_mount, device_identifier),
        )

    db.commit()
    flash(details, "success")
    return redirect(url_for("main.index"))
