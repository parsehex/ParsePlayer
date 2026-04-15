# Update Workflow

Use this after ParsePlayer is already installed on the Pi.

## 1) Sync code to Pi

From your dev machine:

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

Or use:

```bash
./dev_sync.sh
```

## 2) Rebuild and restart on Pi

```bash
cd ~/ParsePlayer
./scripts/rebuild_prod.sh
```

## 3) Verify

```bash
sudo systemctl status parseplayer --no-pager
curl -I http://127.0.0.1:5000/
```

## 4) Optional logs

```bash
sudo journalctl -u parseplayer -f
```

## Kiosk toggle

Disable kiosk autostart:

```bash
touch ~/.no-kiosk
```

Re-enable kiosk autostart:

```bash
rm ~/.no-kiosk
```
