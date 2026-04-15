#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d "venv" ]]; then
  echo "Missing Python venv at $ROOT_DIR/venv"
  echo "Create it first, then install requirements."
  exit 1
fi

cleanup() {
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

source "$ROOT_DIR/venv/bin/activate"

if [[ ! -d "node_modules" ]]; then
  npm install
fi
if [[ ! -d "frontend/node_modules" ]]; then
  npm install -w frontend
fi

./venv/bin/python -m flask --app app run --host=0.0.0.0 --debug &
BACKEND_PID=$!

npm run dev -w frontend -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

echo "Waiting for frontend at http://127.0.0.1:5173/display ..."
until curl -fsS "http://127.0.0.1:5173/display" >/dev/null 2>&1; do
  sleep 1
  if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo "Frontend process exited unexpectedly."
    exit 1
  fi
done

if command -v chromium-browser >/dev/null 2>&1; then
  BROWSER_CMD="chromium-browser"
elif command -v chromium >/dev/null 2>&1; then
  BROWSER_CMD="chromium"
else
  echo "Chromium not found. Install chromium-browser or chromium."
  exit 1
fi

$BROWSER_CMD \
  --kiosk \
  --app="http://127.0.0.1:5173/display" \
  --window-size=320,480 \
  --window-position=0,0 \
  --force-device-scale-factor=1 \
  --no-first-run \
  --disable-pinch \
  --overscroll-history-navigation=0
