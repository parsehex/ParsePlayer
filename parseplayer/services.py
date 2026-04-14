import logging
import os
import shutil
from collections import defaultdict
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from flask import current_app, request

from . import queries
from .music import SUPPORTED_EXTENSIONS, discover_tracks
from .usb import detect_usb_partitions, mount_usb_by_identifier, unmount_usb_by_identifier

logger = logging.getLogger(__name__)

def derive_virtual_artist_album(track_path: str, music_root: str) -> tuple[str, str]:
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

def enrich_track_for_display(track_row, music_root: str):
    track = dict(track_row)
    artist, album = derive_virtual_artist_album(track["path"], music_root)
    track["virtual_artist"] = artist
    track["virtual_album"] = album
    return track

def fetch_enriched_tracks(db, music_root: str):
    rows = queries.get_all_tracks(db)
    return [enrich_track_for_display(row, music_root) for row in rows]

job_state = {
    "status": "idle",
    "message": "",
    "percentage": 0,
    "completed": 0,
    "total": 0,
}

def set_job_state(status, message, percentage=0, completed=0, total=0):
    job_state["status"] = status
    job_state["message"] = message
    job_state["percentage"] = percentage
    job_state["completed"] = completed
    job_state["total"] = total

def fetch_usb_devices(db):
    rows = queries.get_all_usb_devices(db)

    live_lookup: dict[str, dict[str, str]] = {}
    try:
        for item in detect_usb_partitions():
            live_lookup[item["device_uuid"]] = item
    except RuntimeError as e:
        logger.error(f"USB detection failed: {e}")
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

def format_bytes(byte_count: int) -> str:
    size = float(byte_count)
    units = ["B", "KB", "MB", "GB", "TB"]
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    if index == 0:
        return f"{int(size)} {units[index]}"
    return f"{size:.1f} {units[index]}"

def build_track_browse_groups(
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

    if active_artist and all(group["key"] != active_artist for group in artist_groups):
        active_artist = ""
        active_album = ""
        filtered_tracks = list(tracks)

    if active_album and active_artist and all(group["key"] != active_album for group in album_groups):
        active_album = ""

    return artist_groups, album_groups, filtered_tracks

def run_import_library_input(app):
    with app.app_context():
        from .db import get_db
        db = get_db()
        set_job_state("running", "Initializing import...")
        source_device = queries.get_usb_device_by_role(db, 'library_input')
        if not source_device:
            set_job_state("error", "No USB marked as library_input. Detect devices and assign one.")
            return

        device_identifier = source_device["device_uuid"]
        was_mounted = bool((source_device["mount_path"] or "").strip())
        raw_mount = source_device["mount_path"] or ""

        if not raw_mount or not Path(raw_mount).is_dir():
            raw_mount = mount_usb_by_identifier(device_identifier)
            if not raw_mount:
                set_job_state("error", f"Could not mount '{source_device['label']}'. Is it still plugged in?")
                return
            queries.update_usb_device_mount(db, device_identifier, raw_mount, by_uuid=True)
            db.commit()

        mount_path = Path(raw_mount)
        if not mount_path.exists() or not mount_path.is_dir():
            set_job_state("error", f"Library input USB mount path is unavailable: {mount_path}")
            return

        library_root = Path(app.config["MUSIC_ROOT"])
        library_root.mkdir(parents=True, exist_ok=True)

        set_job_state("running", "Scanning files on USB...")
        source_files = [f for f in mount_path.rglob("*") if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS]
        total_files = len(source_files)
        
        if total_files == 0:
            set_job_state("completed", "No supported music files found on USB.", 100, 0, 0)
            return

        copied_files = 0
        try:
            for source_file in source_files:
                relative_path = source_file.relative_to(mount_path)
                target_file = library_root / relative_path
                target_file.parent.mkdir(parents=True, exist_ok=True)

                shutil.copy2(source_file, target_file)
                copied_files += 1
                pct = int((copied_files / total_files) * 100)
                set_job_state("running", f"Importing {source_file.name}...", pct, copied_files, total_files)

            set_job_state("running", "Indexing tracks in database...")
            tracks = discover_tracks(library_root)
            indexed = queries.upsert_tracks(db, tracks)
            details = (
                f"Imported {copied_files} file(s) from '{source_device['label']}' into '{library_root}'. "
                f"Indexed {indexed} track record(s)."
            )
            queries.log_sync_run(db, "import_library_input", "completed", details)
            db.commit()
            set_job_state("completed", details, 100, copied_files, total_files)
        except Exception as e:
            logger.error(f"Error during import: {e}", exc_info=True)
            set_job_state("error", f"Error during import: {e}")
        finally:
            if not was_mounted:
                unmount_usb_by_identifier(device_identifier)
                queries.update_usb_device_mount(db, device_identifier, "", by_uuid=True)
                db.commit()

def run_backup_library(app):
    with app.app_context():
        from .db import get_db
        db = get_db()
        set_job_state("running", "Initializing backup...")
        backup_device = queries.get_usb_device_by_role(db, 'backup')
        if not backup_device:
            set_job_state("error", "No USB marked as backup.")
            return

        device_identifier = backup_device["device_uuid"]
        was_mounted = bool((backup_device["mount_path"] or "").strip())
        raw_mount = backup_device["mount_path"] or ""

        if not raw_mount or not Path(raw_mount).is_dir():
            raw_mount = mount_usb_by_identifier(device_identifier)
            if not raw_mount:
                set_job_state("error", f"Could not mount '{backup_device['label']}'. Is it still plugged in?")
                return
            queries.update_usb_device_mount(db, device_identifier, raw_mount, by_uuid=True)
            db.commit()

        mount_path = Path(raw_mount)
        if not mount_path.exists() or not mount_path.is_dir():
            set_job_state("error", f"Backup USB mount path is unavailable: {mount_path}")
            return

        library_root = Path(app.config["MUSIC_ROOT"])
        if not library_root.exists() or not library_root.is_dir():
            set_job_state("error", f"Library source folder is unavailable: {library_root}")
            return

        backup_root = mount_path / "ParsePlayerLibraryBackup"
        backup_root.mkdir(parents=True, exist_ok=True)
        
        set_job_state("running", "Scanning library files...")
        source_files = [f for f in library_root.rglob("*") if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS]
        total_files = len(source_files)

        if total_files == 0:
            set_job_state("completed", "No music files to backup.", 100, 0, 0)
            return

        copied_files = 0
        try:
            for source_file in source_files:
                relative_path = source_file.relative_to(library_root)
                target_file = backup_root / relative_path
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, target_file)
                copied_files += 1
                pct = int((copied_files / total_files) * 100)
                set_job_state("running", f"Backing up {source_file.name}...", pct, copied_files, total_files)

            details = (
                f"Backed up {copied_files} file(s) from '{library_root}' to "
                f"'{backup_device['label']}' at '{backup_root}'."
            )
            queries.log_sync_run(db, "backup_library", "completed", details)
            db.commit()
            set_job_state("completed", details, 100, copied_files, total_files)
        except Exception as e:
            logger.error(f"Error during backup: {e}", exc_info=True)
            set_job_state("error", f"Error during backup: {e}")
        finally:
            if not was_mounted:
                unmount_ok = unmount_usb_by_identifier(device_identifier)
                queries.update_usb_device_mount(db, device_identifier, "" if unmount_ok else raw_mount, by_uuid=True)
                db.commit()

def run_sync_mp3(app):
    with app.app_context():
        from .db import get_db
        db = get_db()
        set_job_state("running", "Initializing sync...")
        mp3_device = queries.get_usb_device_by_role(db, 'mp3_player')
        if not mp3_device:
            set_job_state("error", "No USB marked as mp3_player.")
            return

        selected_count, selected_size_bytes = queries.get_selected_sync_stats(db)
        if selected_count == 0:
            set_job_state("error", "No tracks selected for sync.")
            return

        device_identifier = mp3_device["device_uuid"]
        was_mounted = bool((mp3_device["mount_path"] or "").strip())
        raw_mount = mp3_device["mount_path"] or ""

        if not raw_mount or not Path(raw_mount).is_dir():
            raw_mount = mount_usb_by_identifier(device_identifier)
            if not raw_mount:
                set_job_state("error", f"Could not mount '{mp3_device['label']}'. Is it still plugged in?")
                return
            queries.update_usb_device_mount(db, device_identifier, raw_mount, by_uuid=True)
            db.commit()

        mount_path = Path(raw_mount)
        if not mount_path.exists() or not mount_path.is_dir():
            set_job_state("error", f"MP3 player USB mount path is unavailable: {mount_path}")
            return

        sync_root = mount_path
        library_root = Path(app.config["MUSIC_ROOT"])

        queries.log_sync_run(db, "sync_mp3", "started", f"Starting sync of {selected_count} tracks.")
        db.commit()

        copied_files = 0
        total_files = selected_count
        try:
            selected_tracks = queries.get_selected_sync_tracks(db)
            for track in selected_tracks:
                source_file = Path(track["path"])
                if not source_file.is_file():
                    total_files -= 1
                    continue

                try:
                    relative_path = source_file.relative_to(library_root)
                except ValueError:
                    relative_path = Path(source_file.name)

                target_file = sync_root / relative_path
                target_file.parent.mkdir(parents=True, exist_ok=True)

                shutil.copy2(source_file, target_file)
                copied_files += 1
                if total_files > 0:
                    pct = int((copied_files / total_files) * 100)
                else: 
                    pct = 0
                set_job_state("running", f"Syncing {source_file.name}...", pct, copied_files, total_files)

            details = (
                f"Synced {copied_files} of {selected_count} selected track(s) to "
                f"'{mp3_device['label']}' at '{sync_root}'."
            )
            queries.log_sync_run(db, "sync_mp3", "completed", details)
            db.commit()
            set_job_state("completed", details, 100, copied_files, total_files)
        except Exception as e:
            logger.error(f"Error during MP3 sync: {e}", exc_info=True)
            queries.log_sync_run(db, "sync_mp3", "failed", f"Failed: {e}")
            db.commit()
            set_job_state("error", f"Error during MP3 sync: {e}")
        finally:
            if not was_mounted:
                unmount_ok = unmount_usb_by_identifier(device_identifier)
                queries.update_usb_device_mount(db, device_identifier, "" if unmount_ok else raw_mount, by_uuid=True)
                db.commit()
