#!/usr/bin/env bash
# Installs mouse-debounce as a system service. Run it again to update.
set -euo pipefail

source_dir=$(dirname "$(readlink -f "$0")")

if ! /usr/bin/python3 -c 'import evdev' 2> /dev/null; then
    echo "Missing the Python evdev module. Install it first with:" >&2
    echo "    sudo apt install python3-evdev" >&2
    exit 1
fi

sudo install -D --mode=755 "$source_dir/mouse-debounce" \
    /usr/local/bin/mouse-debounce
sudo install -D --mode=644 "$source_dir/mouse-debounce.service" \
    /etc/systemd/system/mouse-debounce.service

sudo modprobe uinput
sudo systemctl daemon-reload
sudo systemctl enable mouse-debounce.service
sudo systemctl restart mouse-debounce.service

echo "Installed. Try a light drag, then check with:"
echo "    journalctl -u mouse-debounce -n 10"
