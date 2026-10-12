#!/usr/bin/env bash
# Installs daily-wallpaper for the current user. Run it again to update.
set -euo pipefail

source_dir=$(dirname "$(readlink -f "$0")")
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/daily-wallpaper"

if ! /usr/bin/python3 -c 'import gi, PIL' 2>/dev/null; then
    echo "Missing Python libraries. Install them first with:" >&2
    echo "    sudo apt install python3-gi python3-pil" >&2
    exit 1
fi

install -D --mode=755 "$source_dir/daily-wallpaper.py" \
    "$HOME/.local/bin/daily-wallpaper"
install -D --mode=644 "$source_dir/daily-wallpaper.service" \
    "$HOME/.config/systemd/user/daily-wallpaper.service"

if [[ ! -f "$config_dir/config.ini" ]]; then
    install -D --mode=644 "$source_dir/config.example.ini" "$config_dir/config.ini"
    echo "Created settings file: $config_dir/config.ini"
fi
mkdir -p "$HOME/Pictures/Wallpapers"

systemctl --user daemon-reload
systemctl --user enable daily-wallpaper.service
systemctl --user restart daily-wallpaper.service

echo "Installed. Put images in your wallpaper folder, then check with:"
echo "    ~/.local/bin/daily-wallpaper --status"
