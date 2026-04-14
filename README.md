# ParsePlayer

> Call this project "vibe-coded" if you wanna fight about it - I call it "solo-pair-programmed".
>
> Want to read my thoughts on the topic? (TODO link)

Early-stage software for a Raspberry Pi based personal music hub.

Current stack:

- Flask
- HTMX
- Pico.css

## What this first version does

- Scans a source folder and indexes audio files into a local SQLite database.
- Lets you toggle tracks for MP3 player sync selection.
- Tracks known USB devices and assigns each a role:
  - `library_input`
  - `backup`
  - `mp3_player`
  - `unknown`
- Detects mounted USB partitions automatically using `lsblk`.
- Provides actions for:
  - MP3 sync
  - Library backup

This gives a practical interface now, while leaving room to add real copy/sync logic later.

## Quick start

1. Create and activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the app:

   ```bash
   flask --app app run --debug
   ```

4. Open <http://127.0.0.1:5000>

The database is created automatically at `data/parseplayer.db`.

## USB detection notes

- Use the **Detect Mounted USB Devices** button in the UI.
- Assign roles directly in the detected device rows.
- Detection expects Linux `lsblk` (typically from `util-linux`) to be available.
- Detected devices are upserted by UUID; previously assigned roles are preserved.

## Next milestone ideas

- Implement actual copy/sync engine with size-aware selection for 1GB targets.
  - Functionality to detect and downsample tracks.
    - Originals would remain in the library.
  - Perhaps different targets could have different sync strategies. Stuff like setting the desired bitrate.
- Support metadata management.
- Add sync history details and basic conflict handling.
  - Human-Dev note - I'm taking inspiration from other well-designed software as well as my RCA PEARL here:
    - I'm looking to respect sources of truth instead of fighting them, which includes the music itself.
    - So it's perfectly fine to list the music in the DB, but the music files themselves are the source of truth there.
      - There's surely some wiggle-room here but the music part of the DB should practically be read-only aside from our app-stuff.
        - I don't have full thoughts on this at this time.
    - I need to think on this more, but I'd like to use the PEARL for UI inspiration too.

## The Long, Long Term

- This isn't just for Raspberry Pi, and not even for a certain model.
   1) The software here is primarily to start building out the Desktop version and figuring out the shape of this whole project.
   2) Once the Desktop version is (and I am) in a good place, my eyes will be set up the Portable version built on top of a Zero W.
   3) As a third end - this software itself doesn't care what it's running on.
