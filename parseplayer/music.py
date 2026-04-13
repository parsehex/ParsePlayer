from pathlib import Path

SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".m4a", ".ogg", ".wav", ".aac"}


def parse_track_name(file_path: Path) -> tuple[str, str | None]:
    stem = file_path.stem
    if " - " in stem:
        artist, title = stem.split(" - ", 1)
        return title.strip(), artist.strip()
    return stem, None


def discover_tracks(root: Path) -> list[dict[str, str | None]]:
    if not root.exists():
        return []

    tracks: list[dict[str, str | None]] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        title, artist = parse_track_name(path)
        tracks.append(
            {
                "path": str(path),
                "title": title,
                "artist": artist,
            }
        )
    return tracks
