#!/usr/bin/env bash
# Removes mouse-debounce. The mouse goes back to sending events directly.
set -euo pipefail

sudo systemctl disable --now mouse-debounce.service 2>/dev/null || true
sudo rm -f /etc/systemd/system/mouse-debounce.service \
    /usr/local/bin/mouse-debounce
sudo rm -rf /etc/systemd/system/mouse-debounce.service.d
sudo systemctl daemon-reload

echo "Uninstalled."
