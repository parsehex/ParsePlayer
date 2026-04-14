import os

def get_all_tracks(db):
    return db.execute(
        """
        SELECT id, path, title, artist, selected_for_sync, updated_at
        FROM tracks
        ORDER BY selected_for_sync DESC, artist IS NULL, artist, title
        """
    ).fetchall()

def get_track_by_id(db, track_id: int):
    return db.execute(
         "SELECT id, title, artist, path, selected_for_sync FROM tracks WHERE id = ?",
         (track_id,),
    ).fetchone()

def update_track_selection(db, track_id: int):
    db.execute(
        """
        UPDATE tracks
        SET selected_for_sync = CASE selected_for_sync WHEN 1 THEN 0 ELSE 1 END,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (track_id,),
    )

def bulk_update_tracks_selection(db, target: int, scope: str, value: str):
    if scope == "all":
        db.execute(
            "UPDATE tracks SET selected_for_sync = ?, updated_at = CURRENT_TIMESTAMP",
            (target,),
        )
    elif scope == "artist":
        if value == "__unknown__":
            db.execute(
                """
                UPDATE tracks
                SET selected_for_sync = ?, updated_at = CURRENT_TIMESTAMP
                WHERE artist IS NULL OR artist = ''
                """,
                (target,),
            )
        else:
            db.execute(
                """
                UPDATE tracks
                SET selected_for_sync = ?, updated_at = CURRENT_TIMESTAMP
                WHERE artist = ?
                """,
                (target, value),
            )
    elif scope == "folder":
        db.execute(
            """
            UPDATE tracks
            SET selected_for_sync = ?, updated_at = CURRENT_TIMESTAMP
            WHERE path = ? OR path LIKE ?
            """,
            (target, value, f"{value}/%"),
        )

def upsert_tracks(db, tracks: list[dict[str, str | None]]) -> int:
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

def get_selected_sync_stats(db) -> tuple[int, int]:
    rows = db.execute("SELECT path FROM tracks WHERE selected_for_sync = 1").fetchall()
    total_bytes = 0
    for row in rows:
        try:
            total_bytes += os.path.getsize(row["path"])
        except OSError:
            continue
    return len(rows), total_bytes

def get_selected_sync_tracks(db):
    return db.execute("SELECT path, title, artist FROM tracks WHERE selected_for_sync = 1").fetchall()

def get_all_usb_devices(db):
    return db.execute(
        """
        SELECT id, label, device_uuid, mount_path, role, last_seen_at
        FROM usb_devices
        WHERE mount_path NOT IN ('/', '/boot', '/boot/firmware')
        ORDER BY role, label
        """
    ).fetchall()

def get_usb_device_by_id(db, usb_id: int):
    return db.execute("SELECT id, label, device_uuid, mount_path, role FROM usb_devices WHERE id = ?", (usb_id,)).fetchone()

def get_usb_device_by_role(db, role: str):
    return db.execute(
        "SELECT id, label, device_uuid, mount_path FROM usb_devices WHERE role = ? ORDER BY last_seen_at DESC LIMIT 1",
        (role,)
    ).fetchone()

def upsert_usb_device(db, label: str, device_uuid: str, mount_path: str, role: str):
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

def upsert_usb_device_from_detect(db, label: str, device_uuid: str, mount_path: str):
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
        (label, device_uuid, mount_path),
    )

def update_usb_device_role(db, usb_id: int, role: str):
    db.execute(
        """
        UPDATE usb_devices
        SET role = ?,
            last_seen_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (role, usb_id),
    )

def update_usb_device_mount(db, identifier: str, mount_path: str, by_uuid: bool = False):
    if by_uuid:
        db.execute(
            "UPDATE usb_devices SET mount_path = ?, last_seen_at = CURRENT_TIMESTAMP WHERE device_uuid = ?",
            (mount_path, identifier),
        )
    else:
        db.execute(
            "UPDATE usb_devices SET mount_path = ?, last_seen_at = CURRENT_TIMESTAMP WHERE id = ?",
            (mount_path, identifier),
        )

def delete_invalid_usb_devices(db):
    db.execute("DELETE FROM usb_devices WHERE mount_path IN ('/', '/boot', '/boot/firmware')")

def log_sync_run(db, action: str, status: str, details: str):
    db.execute(
        "INSERT INTO sync_runs (action, status, details) VALUES (?, ?, ?)",
        (action, status, details),
    )

def delete_usb_device(db, usb_id: int):
    db.execute("DELETE FROM usb_devices WHERE id = ?", (usb_id,))
