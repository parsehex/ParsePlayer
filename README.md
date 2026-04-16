# ParsePlayer

> Call this project "vibe-coded" if you wanna fight about it - I call it "solo-pair-programmed".
>
> Read the [raw README](README.raw.md) for the human-written version + history.
<!-- > Want to read my thoughts on this AI-programming topic? (TODO link) -->

Early-stage software for a Raspberry Pi based personal music hub.

Current stack:

- Flask
- Vue
- Pico.css

## Documentation site

A VitePress docs site now lives in `docs/`.

Preview docs locally:

```bash
npm run docs:dev
```

Build static docs:

```bash
npm run docs:build
```

Primary runbook for rebuilding a fresh Pi SD card:

- [`docs/guides/pi-fresh-setup.md`](https://parsehex.github.io/ParsePlayer/guides/pi-fresh-setup)

If you are handing this project off, start there for the end-to-end rebuild path.

## Current hardware context

The current build centers on three pieces of hardware:

- An RCA `PEARL` MP3 player that motivated the project.
- A Raspberry Pi 4 B as the current desktop-style base unit.
- An off-the-shelf case + SPI touchscreen used for the local kiosk display.

Reference photos for the current build live in `resources/ParsePlayer/`:

![RCA PEARL](resources/ParsePlayer/rca-pearl.jpg)

![Case with top removed](resources/ParsePlayer/case-top-off.jpg)

![Assembled case](resources/ParsePlayer/assembled-case.jpg)

The photos in `resources/ParsePlayer/Display booklet/` are product-booklet reference images for the third-party case/display hardware. They are there to document the physical build context, not to describe ParsePlayer itself.

For the shortest "what works now" to "how do I recreate it" path:

- Start with `docs/guides/pi-fresh-setup.md` for a blank-SD-card rebuild.
- Use `scripts/install_pi_service.sh` for the one-time Pi service install.
- Use `scripts/rebuild_prod.sh` for day-to-day Pi updates.

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

## Raspberry Pi local display (320x480)

### Pi Server OS notes

For Raspberry Pi Server OS with a small SPI display, the important detail is that Xorg may start on the wrong framebuffer by default.

On the setup tested here:

- `/dev/fb0` was `BCM2708 FB`
- `/dev/fb1` was the actual `fb_ili9486` display

To make the local display usable, Xorg needed to be forced onto `/dev/fb1`.

Create `/etc/X11/xorg.conf.d/99-fbdev.conf`:

```conf
Section "Device"
    Identifier  "SPI Display"
    Driver      "fbdev"
    Option      "fbdev" "/dev/fb1"
EndSection

Section "Screen"
    Identifier "Screen0"
    Device     "SPI Display"
EndSection
```

Install the minimum local GUI pieces:

```bash
sudo apt update
sudo apt install -y xauth xinit xserver-xorg openbox unclutter x11-xserver-utils chromium-browser curl
```

### Manual test path

Before enabling boot-to-kiosk, first prove the display path locally on the Pi itself.

1. Confirm ParsePlayer is running:

```bash
curl -I http://127.0.0.1:5000/
```

1. Start Chromium directly on the attached display:

```bash
xinit /usr/bin/chromium-browser --app=http://127.0.0.1:5000/ --disable-gpu --use-gl=swiftshader --no-first-run -- :0 vt1
```

If that works, the remaining task is just boot automation.

### Boot-to-kiosk flow

The working direction for a keyboardless boot flow is:

1. `parseplayer.service` starts at boot
2. tty1 autologins the Pi user
3. the user's login shell runs `startx`
4. `.xinitrc` launches Chromium pointed at the local Flask service

Example login-shell hook:

```sh
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ] && [ ! -f "$HOME/.no-kiosk" ]; then
  exec startx "$HOME/.xinitrc" -- :0 vt1 -keeptty
fi
```

Example `.xinitrc`:

```sh
#!/usr/bin/env sh
xset -dpms
xset s off
xset s noblank
unclutter -idle 0.5 -root &

until curl -fsS http://127.0.0.1:5000/ >/dev/null; do
  sleep 1
done

exec chromium-browser \
  --kiosk \
  --app=http://127.0.0.1:5000/ \
  --force-device-scale-factor=1 \
  --disable-gpu \
  --use-gl=swiftshader \
  --no-first-run \
  --disable-pinch \
  --overscroll-history-navigation=0
```

If you see empty/black space to the right, remove hard `--window-size` and `--window-position` flags (as above) so Chromium can fully use the active framebuffer.

### Pi boot splash branding

This repo includes a splash asset at `resources/parseplayer-splash.svg` that matches the app header logo + name.

For the full Plymouth boot splash setup on Raspberry Pi, see [the fresh setup guide](docs/guides/pi-fresh-setup.md#11-boot-splash-plymouth).

### Safety switch

Use a sentinel file to temporarily disable kiosk startup:

```bash
touch ~/.no-kiosk
```

Re-enable kiosk startup:

```bash
rm ~/.no-kiosk
```

If the manual local Chromium test is working and your boot hook is already in place, then yes: removing `.no-kiosk` and rebooting is the right next step.

## Production service mode (Pi Server OS friendly)

For headless Raspberry Pi Server OS, use the systemd service flow.

### One-time install

```bash
./scripts/install_pi_service.sh
```

This will:

- Build frontend assets into `dist/`
- Install Python requirements into your `venv`
- Install and enable `parseplayer.service`
- Start the app on `0.0.0.0:5000`

### Everyday rebuild/update

After pulling changes or syncing files to the Pi:

```bash
./scripts/rebuild_prod.sh
```

This re-installs deps, rebuilds frontend, and restarts the service.

### Useful service commands

```bash
sudo systemctl status parseplayer
sudo systemctl restart parseplayer
sudo journalctl -u parseplayer -f
```

## USB detection notes

- Use the **Detect Mounted USB Devices** button in the UI.
- Assign roles directly in the detected device rows.
- For importing music from a USB drive into the library, assign the drive role to `library_input` and use **Import From Library USB**.
- Import copies supported audio files into the app's music root and indexes them automatically.
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
