#!/usr/bin/env bash
# Installs the Google Drive two-way sync for the current user: a timer that
# syncs every 15 minutes, and a "Sync Google Drive" app for syncing right
# away, pinned to the Dock. Run it again to update.
# Do the first sync (with --resync) by hand before running this; see
# CLOUD-STORAGE.md, section 1.5.
set -euo pipefail

source_dir=$(dirname "$(readlink -f "$0")")
data_dir="${XDG_DATA_HOME:-$HOME/.local/share}"
executable="$HOME/.local/bin/sync-google-drive"
icon="$data_dir/icons/hicolor/scalable/apps/sync-google-drive.svg"
desktop_file_name="sync-google-drive.desktop"

if [[ ! -x /usr/bin/rclone ]]; then
    echo "rclone isn't installed. See CLOUD-STORAGE.md, section 1.2." >&2
    exit 1
fi
if ! rclone listremotes | grep --quiet --line-regexp 'gdrive:'; then
    echo "There's no rclone remote called \"gdrive\"." >&2
    echo "See CLOUD-STORAGE.md, section 1.3." >&2
    exit 1
fi
if [[ ! -d "$HOME/GoogleDriveSync" ]]; then
    echo "~/GoogleDriveSync doesn't exist. Do the first sync by hand" >&2
    echo "first: CLOUD-STORAGE.md, section 1.5, steps 1-3." >&2
    exit 1
fi

install -D --mode=644 "$source_dir/rclone-gdrive-bisync.service" \
    "$HOME/.config/systemd/user/rclone-gdrive-bisync.service"
install -D --mode=644 "$source_dir/rclone-gdrive-bisync.timer" \
    "$HOME/.config/systemd/user/rclone-gdrive-bisync.timer"
install -D --mode=755 "$source_dir/sync-google-drive.py" "$executable"
install -D --mode=644 "$source_dir/sync-google-drive.svg" "$icon"

# App entries need absolute paths; they don't understand "~" or "$HOME".
mkdir -p "$data_dir/applications"
sed -e "s|@EXECUTABLE@|$executable|" -e "s|@ICON@|$icon|" \
    "$source_dir/sync-google-drive.desktop.in" \
    > "$data_dir/applications/$desktop_file_name"

systemctl --user daemon-reload
systemctl --user enable --now rclone-gdrive-bisync.timer

# Pin the app to the Dock, unless it's already there.
favorites=$(gsettings get org.gnome.shell favorite-apps)
if [[ "$favorites" != *"'$desktop_file_name'"* ]]; then
    if [[ "$favorites" == "@as []" || "$favorites" == "[]" ]]; then
        favorites="['$desktop_file_name']"
    else
        favorites="${favorites%]}, '$desktop_file_name']"
    fi
    gsettings set org.gnome.shell favorite-apps "$favorites"
fi

echo "Installed. Google Drive now syncs every 15 minutes, and"
echo "\"Sync Google Drive\" on the Dock or in the app search syncs right away."
echo "Check the timer with:  systemctl --user list-timers"
