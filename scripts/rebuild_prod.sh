#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="parseplayer"

cd "$ROOT_DIR"

if [[ ! -d "venv" ]]; then
  echo "Missing Python venv at $ROOT_DIR/venv"
  exit 1
fi

source "$ROOT_DIR/venv/bin/activate"

echo "Installing Python requirements"
pip install -r requirements.txt

echo "Installing Node dependencies"
npm install
npm install -w frontend

echo "Building frontend"
npm run build -w frontend

if systemctl list-unit-files | grep -q "^${SERVICE_NAME}\.service"; then
  echo "Restarting ${SERVICE_NAME}.service"
  sudo systemctl restart "$SERVICE_NAME"
  sudo systemctl status "$SERVICE_NAME" --no-pager
else
  echo "${SERVICE_NAME}.service is not installed yet."
  echo "Run: ./scripts/install_pi_service.sh"
fi
