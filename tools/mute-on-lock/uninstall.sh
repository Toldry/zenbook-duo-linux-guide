#!/usr/bin/env bash
# Removes mute-on-lock. If it had muted the sound, the sound is unmuted.
set -euo pipefail

state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/mute-on-lock"

systemctl --user disable --now mute-on-lock.service 2>/dev/null || true
if [[ -f $state_dir/muted-output-id ]]; then
    wpctl set-mute "$(< "$state_dir/muted-output-id")" 0 2>/dev/null || true
fi
rm -f "$HOME/.config/systemd/user/mute-on-lock.service" \
    "$HOME/.local/bin/mute-on-lock"
rm -rf "$state_dir"
systemctl --user daemon-reload

echo "Uninstalled."
