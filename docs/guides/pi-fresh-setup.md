# Fresh Pi Setup (Minimal OS)

This guide recreates a working ParsePlayer Pi from a brand-new SD card.

It is written for a minimal Raspberry Pi OS style install where you add only the GUI pieces needed for local kiosk display.

## Goal state

- ParsePlayer runs as a systemd service on port 5000
- SPI LCD works with Xorg on fb1
- Chromium launches in kiosk mode on boot
- USB import/sync workflow is available in the app UI

## 0) Flash and first boot

1. Use the official Raspberry Pi Imager: https://www.raspberrypi.com/software/
   - Select "OS → Raspberry Pi OS (other) → Raspberry Pi OS Lite"
   - Click "Customize" and set:
     - Hostname
     - Locale/timezone
     - Username and password
     - WiFi (if needed)
   - Before writing, open the Customization's "Edit File" feature to add to `/boot/firmware/config.txt`:
     ```
     dtoverlay=piscreen,speed=16000000
     ```
   - Write to SD card
2. Boot the Pi and wait for yellow/green LED to settle before attempting SSH.
3. Update packages:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

## 1) Install base packages

After reboot:

```bash
sudo apt update
sudo apt install -y \
  git curl \
  python3-venv python3-pip \
  xauth xinit xserver-xorg openbox unclutter x11-xserver-utils \
  chromium
```

## 2) Install Node.js v24+

VitePress and newer Vite require Node v24 or higher. Use the NodeSource binary distribution:

```bash
sudo apt install -y ca-certificates curl gnupg
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_24.x nodistro main" | sudo tee /etc/apt/sources.list.d/nodesource.list
sudo apt update
sudo apt install -y nodejs
node -v  # Verify version 24.x
```

## 3) Get ParsePlayer onto the Pi

Clone directly on Pi:

```bash
cd ~
git clone https://github.com/parsehex/ParsePlayer ParsePlayer
cd ~/ParsePlayer
```

## 4) Create Python virtual environment

```bash
cd ~/ParsePlayer
python3 -m venv venv
source venv/bin/activate
pip install -U pip
```

## 5) Install ParsePlayer service

Run the installer script:

```bash
cd ~/ParsePlayer
./scripts/install_pi_service.sh
```

This script:
- installs frontend dependencies
- builds frontend assets
- installs Python dependencies
- installs and enables parseplayer.service
- starts the service

## 6) Verify backend service

```bash
sudo systemctl status parseplayer --no-pager
curl -I http://127.0.0.1:5000/
```

## 7) Test Chromium in kiosk mode locally

Before enabling boot kiosk, validate Chromium launch on the LCD:

```bash
xinit /usr/bin/chromium --app=http://127.0.0.1:5000/ --disable-gpu --use-gl=swiftshader --no-first-run -- :0 vt1
```

Chromium should open on the LCD display. If it works, continue with kiosk automation.

## 8) Configure kiosk autostart

### 8.1 Login shell hook for tty1

Append to ~/.profile (or equivalent login shell startup file):

```sh
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ] && [ ! -f "$HOME/.no-kiosk" ]; then
  exec startx "$HOME/.xinitrc" -- :0 vt1 -keeptty
fi
```

### 8.2 Create ~/.xinitrc

```bash
cat > ~/.xinitrc <<'EOF'
#!/usr/bin/env sh
xset -dpms
xset s off
xset s noblank
unclutter -idle 0.5 -root &

until curl -fsS http://127.0.0.1:5000/ >/dev/null; do
  sleep 1
done

exec chromium \
  --kiosk \
  --app=http://127.0.0.1:5000/ \
  --force-device-scale-factor=1 \
  --disable-gpu \
  --use-gl=swiftshader \
  --no-first-run \
  --disable-pinch \
  --overscroll-history-navigation=0
EOF
chmod +x ~/.xinitrc
```

### 8.3 Optional safety switch

Disable kiosk autostart temporarily:

```bash
touch ~/.no-kiosk
```

Re-enable kiosk autostart:

```bash
rm ~/.no-kiosk
```

## 9) Reboot and confirm end-to-end

```bash
sudo reboot
```

After reboot, confirm:
- ParsePlayer service is active
- Chromium kiosk opens on the LCD
- UI is reachable and usable

## 10) Optional USB safety tuning

If you want automatic FAT32 repair/mount tuning:

```bash
cd ~/ParsePlayer
./scripts/setup_safe_usb.sh
```

Note: the script's generated udiskie service uses User=user by default. Change that line to your actual username if needed in /etc/systemd/system/udiskie.service.

## Troubleshooting

### LCD shows console framebuffer but Xorg/Chromium does not display

- Confirm the dtoverlay line in /boot/firmware/config.txt is present and reboot.
- Try running `fbset -s` to query current framebuffer state.

### ParsePlayer service does not start

```bash
sudo journalctl -u parseplayer -n 200 --no-pager
```

Check that venv exists at ~/ParsePlayer/venv and dependencies installed.

### Kiosk does not launch at boot

- Confirm tty1 autologin is enabled for your user.
- Confirm ~/.profile hook exists and ~/.xinitrc is executable.
- Check if ~/.no-kiosk exists.
