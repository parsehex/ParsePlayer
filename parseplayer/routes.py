from pathlib import Path
import shutil

from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, url_for
import json

from .db import get_db
from .music import SUPPORTED_EXTENSIONS, discover_tracks
from .usb import detect_usb_partitions, mount_usb_by_identifier, unmount_usb_by_identifier

bp = Blueprint("main", __name__)
USB_ROLES = ["unknown", "library_input", "backup", "mp3_player"]


def _fetch_tracks():
    db = get_db()
    return db.execute(
        """
        SELECT id, path, title, artist, selected_for_sync, updated_at
        FROM tracks
        ORDER BY selected_for_sync DESC, artist IS NULL, artist, title
        """
    ).fetchall()


def _fetch_usb_devices():
    db = get_db()
    return db.execute(
        """
        SELECT id, label, device_uuid, mount_path, role, last_seen_at
        FROM usb_devices
        WHERE mount_path NOT IN ('/', '/boot', '/boot/firmware')
        ORDER BY role, label
        """
    ).fetchall()


def _fetch_sync_count() -> int:
    db = get_db()
    row = db.execute("SELECT COUNT(*) AS count FROM tracks WHERE selected_for_sync = 1").fetchone()
    return int(row["count"])


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


@bp.get("/")
def index():
    music_root = current_app.config["MUSIC_ROOT"]
    return render_template(
        "index.html",
        tracks=_fetch_tracks(),
        usb_devices=_fetch_usb_devices(),
        selected_count=_fetch_sync_count(),
        music_root=music_root,
        usb_roles=USB_ROLES,
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

    track = db.execute(
        "SELECT id, title, artist, path, selected_for_sync FROM tracks WHERE id = ?",
        (track_id,),
    ).fetchone()
    selected_count = _fetch_sync_count()
    response = make_response(render_template("partials/track_row.html", track=track))
    response.headers["HX-Trigger"] = json.dumps(
        {"trackSelectionChanged": {"selectedCount": selected_count}}
    )
    return response


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
