#!/usr/bin/env bash
# Installs mute-on-lock for the current user. Run it again to update.
set -euo pipefail

source_dir=$(dirname "$(readlink -f "$0")")

for command in wpctl gdbus; do
    if ! command -v "$command" > /dev/null; then
        echo "Missing the '$command' command. Install it first with:" >&2
        echo "    sudo apt install wireplumber libglib2.0-bin" >&2
        exit 1
    fi
done

install -D --mode=755 "$source_dir/mute-on-lock" \
    "$HOME/.local/bin/mute-on-lock"
install -D --mode=644 "$source_dir/mute-on-lock.service" \
    "$HOME/.config/systemd/user/mute-on-lock.service"

systemctl --user daemon-reload
systemctl --user enable mute-on-lock.service
systemctl --user restart mute-on-lock.service

echo "Installed. Lock the screen with Super+L to try it, then check with:"
echo "    journalctl --user -u mute-on-lock -n 10"
