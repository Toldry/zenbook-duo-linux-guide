#!/usr/bin/env bash
# Removes daily-wallpaper and puts back Ubuntu's default wallpaper.
# Your images and your settings file are kept.
set -euo pipefail

systemctl --user disable --now daily-wallpaper.service 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/daily-wallpaper.service" \
    "$HOME/.local/bin/daily-wallpaper"
systemctl --user daemon-reload

rm -rf "${XDG_STATE_HOME:-$HOME/.local/state}/daily-wallpaper"
for key in picture-uri picture-uri-dark picture-options; do
    gsettings reset org.gnome.desktop.background "$key"
done

echo "Uninstalled. Your settings file is still at:"
echo "    ${XDG_CONFIG_HOME:-$HOME/.config}/daily-wallpaper/config.ini"
echo "Delete that folder too if you don't need it."
