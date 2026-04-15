# Fresh Pi Setup (Minimal OS)

This guide recreates a working ParsePlayer Pi from a brand-new SD card.

It is written for a minimal Raspberry Pi OS style install where you add only the GUI pieces needed for local kiosk display.

## Goal state

- ParsePlayer runs as a systemd service on port 5000
- SPI LCD works with Xorg on fb1
- Chromium launches in kiosk mode on boot
- USB import/sync workflow is available in the app UI

## 0) Flash and first boot

1. Flash a new SD card with minimal Raspberry Pi OS.
2. Boot the Pi and complete first-boot basics:
   - hostname
   - locale/timezone
   - user account
   - network
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
  chromium-browser
```

If your distro provides Chromium under a different package name, install that equivalent package.

## 2) Install the SPI display driver (GoodTFT)

Driver source used for this setup:
- goodtft/LCD-show
- script used: MHS35-show

Commands:

```bash
cd ~
git clone https://github.com/goodtft/LCD-show.git
cd LCD-show
chmod +x MHS35-show
sudo ./MHS35-show
```

Expect a reboot during/after driver install.

## 3) Verify framebuffer mapping

After reboot, verify the LCD device node:

```bash
cat /proc/fb
```

Expected working mapping in this setup:
- fb0 = BCM2708 FB
- fb1 = fb_ili9486 (the LCD panel)

If this mapping is different on your device, adjust the next step accordingly.

## 4) Force Xorg to LCD framebuffer

Create Xorg config directory and file:

```bash
sudo mkdir -p /etc/X11/xorg.conf.d
sudo tee /etc/X11/xorg.conf.d/99-fbdev.conf >/dev/null <<'EOF'
Section "Device"
    Identifier  "SPI Display"
    Driver      "fbdev"
    Option      "fbdev" "/dev/fb1"
EndSection

Section "Screen"
    Identifier "Screen0"
    Device     "SPI Display"
EndSection
EOF
```

## 5) Get ParsePlayer onto the Pi

Choose one of the following.

Option A: Clone directly on Pi

```bash
cd ~
git clone <your-repo-url> ParsePlayer
cd ~/ParsePlayer
```

Option B: Rsync from your dev machine

```bash
rsync -avz \
  --exclude '.git' \
  --exclude 'venv/' \
  --exclude '.venv/' \
  --exclude 'data/' \
  --exclude '__pycache__/' \
  --exclude 'parseplayer/__pycache__/' \
  --exclude 'node_modules/' \
  --exclude 'frontend/node_modules/' \
  --exclude 'dist/' \
  . raspberrypi:~/ParsePlayer/
```

## 6) Create Python virtual environment

```bash
cd ~/ParsePlayer
python3 -m venv venv
source venv/bin/activate
pip install -U pip
```

## 7) Install ParsePlayer service

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

## 8) Verify backend service

```bash
sudo systemctl status parseplayer --no-pager
curl -I http://127.0.0.1:5000/
```

## 9) Test local display manually first

Before enabling boot kiosk, validate local launch from console:

```bash
xinit /usr/bin/chromium-browser --app=http://127.0.0.1:5000/ --disable-gpu --use-gl=swiftshader --no-first-run -- :0 vt1
```

If this works, continue with kiosk automation.

## 10) Configure kiosk autostart

### 10.1 Login shell hook for tty1

Append to ~/.profile (or equivalent login shell startup file):

```sh
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ] && [ ! -f "$HOME/.no-kiosk" ]; then
  exec startx "$HOME/.xinitrc" -- :0 vt1 -keeptty
fi
```

### 10.2 Create ~/.xinitrc

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

exec chromium-browser \
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

### 10.3 Optional safety switch

Disable kiosk autostart temporarily:

```bash
touch ~/.no-kiosk
```

Re-enable kiosk autostart:

```bash
rm ~/.no-kiosk
```

## 11) Reboot and confirm end-to-end

```bash
sudo reboot
```

After reboot, confirm:
- ParsePlayer service is active
- Chromium kiosk opens on the LCD
- UI is reachable and usable

## 12) Optional USB safety tuning

If you want automatic FAT32 repair/mount tuning:

```bash
cd ~/ParsePlayer
./scripts/setup_safe_usb.sh
```

Note: the script's generated udiskie service uses User=user by default. Change that line to your actual username if needed in /etc/systemd/system/udiskie.service.

## Troubleshooting

### Blank or wrong display target

- Run cat /proc/fb again and confirm which fb device is the LCD.
- Update /etc/X11/xorg.conf.d/99-fbdev.conf to the correct /dev/fbX.

### ParsePlayer service does not start

```bash
sudo journalctl -u parseplayer -n 200 --no-pager
```

Check that venv exists at ~/ParsePlayer/venv and dependencies installed.

### Kiosk does not launch at boot

- Confirm tty1 autologin is enabled for your user.
- Confirm ~/.profile hook exists and ~/.xinitrc is executable.
- Check if ~/.no-kiosk exists.
