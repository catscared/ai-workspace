#!/usr/bin/env bash
set -euo pipefail

# Install a user-level systemd service to auto-start hot monitor on boot/login.
# Usage:
#   bash scripts/install_autostart.sh [PROJECT_DIR]
# Example:
#   bash scripts/install_autostart.sh /workspace

PROJECT_DIR="${1:-/workspace}"
PYTHON_BIN="$(command -v python3)"

if [[ ! -d "$PROJECT_DIR/src" ]]; then
  echo "ERROR: $PROJECT_DIR does not look like project root (missing src/)."
  exit 1
fi

mkdir -p "$HOME/.config/systemd/user"
SERVICE_FILE="$HOME/.config/systemd/user/hot-monitor.service"

cat >"$SERVICE_FILE" <<EOF
[Unit]
Description=AI Blockchain Hot Monitor
After=network-online.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
Environment=PYTHONPATH=$PROJECT_DIR/src
ExecStart=$PYTHON_BIN -m uvicorn hot_monitor.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable hot-monitor.service
systemctl --user restart hot-monitor.service

echo "Installed and started hot-monitor.service"
echo "Check status: systemctl --user status hot-monitor.service"
echo "View logs: journalctl --user -u hot-monitor.service -f"
