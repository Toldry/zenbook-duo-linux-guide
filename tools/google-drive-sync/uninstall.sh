#!/usr/bin/env bash
# Removes the Google Drive sync timer and the "Sync Google Drive" app.
# Your files in ~/GoogleDriveSync and in Google Drive are kept.
set -euo pipefail

data_dir="${XDG_DATA_HOME:-$HOME/.local/share}"
desktop_file_name="sync-google-drive.desktop"

systemctl --user disable --now rclone-gdrive-bisync.timer 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/rclone-gdrive-bisync.service" \
    "$HOME/.config/systemd/user/rclone-gdrive-bisync.timer" \
    "$HOME/.local/bin/sync-google-drive" \
    "$data_dir/icons/hicolor/scalable/apps/sync-google-drive.svg" \
    "$data_dir/applications/$desktop_file_name"
systemctl --user daemon-reload

# Unpin it from the Dock.
favorites=$(gsettings get org.gnome.shell favorite-apps)
favorites=${favorites//", '$desktop_file_name'"/}
favorites=${favorites//"'$desktop_file_name', "/}
favorites=${favorites//"'$desktop_file_name'"/}
gsettings set org.gnome.shell favorite-apps "$favorites"

echo "Uninstalled. Your files in ~/GoogleDriveSync and in Google Drive are kept."
