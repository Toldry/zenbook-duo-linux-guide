#!/usr/bin/env bash
# Run the Google Drive two-way sync now and report the result.
# Starts the same systemd service as the timer; if a sync is already
# running, this waits for it to finish instead of starting a second one.

app_name="Sync Google Drive"
icon="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps/sync-google-drive.svg"
log_file="$HOME/.cache/rclone-gdrive-bisync.log"

notify-send --app-name="$app_name" --icon="$icon" \
    "Syncing Google Drive…" "Started at $(date +%H:%M)."

if systemctl --user start rclone-gdrive-bisync.service; then
    notify-send --app-name="$app_name" --icon="$icon" \
        "Google Drive is in sync" "Finished at $(date +%H:%M)."
else
    notify-send --app-name="$app_name" --icon="dialog-error" \
        --urgency=critical \
        "Google Drive sync failed" "Details: $log_file"
fi
