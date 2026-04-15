#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="parseplayer"
SERVICE_TEMPLATE="$ROOT_DIR/scripts/parseplayer.service.template"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
APP_USER="${SUDO_USER:-$USER}"
APP_GROUP="$(id -gn "$APP_USER")"
APP_PORT="5000"

if [[ ! -f "$SERVICE_TEMPLATE" ]]; then
  echo "Missing service template: $SERVICE_TEMPLATE"
  exit 1
fi

if [[ ! -d "$ROOT_DIR/venv" ]]; then
  echo "Missing Python venv at $ROOT_DIR/venv"
  echo "Create it first and install dependencies."
  exit 1
fi

if [[ ! -d "$ROOT_DIR/frontend" ]]; then
  echo "Missing frontend directory at $ROOT_DIR/frontend"
  exit 1
fi

TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

sed \
  -e "s|__APP_USER__|$APP_USER|g" \
  -e "s|__APP_GROUP__|$APP_GROUP|g" \
  -e "s|__APP_DIR__|$ROOT_DIR|g" \
  -e "s|__APP_PORT__|$APP_PORT|g" \
  "$SERVICE_TEMPLATE" > "$TMP_FILE"

echo "Installing $SERVICE_PATH"
sudo cp "$TMP_FILE" "$SERVICE_PATH"

if [[ ! -f /etc/default/parseplayer ]]; then
  echo "Creating /etc/default/parseplayer for optional overrides"
  echo "# Example: MUSIC_ROOT=/home/$APP_USER/Music" | sudo tee /etc/default/parseplayer >/dev/null
fi

echo "Reloading systemd"
sudo systemctl daemon-reload

if sudo systemctl is-enabled --quiet "$SERVICE_NAME"; then
  echo "Service already enabled"
else
  echo "Enabling $SERVICE_NAME"
  sudo systemctl enable "$SERVICE_NAME"
fi

echo "Building frontend for production"
cd "$ROOT_DIR"
npm install
npm install -w frontend
npm run build -w frontend

echo "Installing Python requirements"
source "$ROOT_DIR/venv/bin/activate"
pip install -r "$ROOT_DIR/requirements.txt"

echo "Starting $SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"
sudo systemctl status "$SERVICE_NAME" --no-pager

echo

echo "ParsePlayer service is installed."
echo "Open: http://<pi-ip>:$APP_PORT"
