#!/usr/bin/python3
"""Sync Google Drive now and show what changed in a notification.

Starts the same systemd service as the timer (rclone bisync between Google
Drive and ~/GoogleDriveSync). If a sync is already running, this waits for it
instead of starting a second one. Afterwards it reads that run's part of the
log and reports how many files were added, updated and deleted in each
direction, with their paths when there are only a few.

See CLOUD-STORAGE.md in the repository, section 1.5.
"""

import html
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

APP_NAME = "Sync Google Drive"
SERVICE = "rclone-gdrive-bisync.service"
LOG_FILE = Path.home() / ".cache" / "rclone-gdrive-bisync.log"
DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
ICON = DATA_HOME / "icons" / "hicolor" / "scalable" / "apps" / "sync-google-drive.svg"

# Show file paths when a run changed at most this many files.
MAX_LISTED_PATHS = 6
# The log grows with every run; only its end is needed.
LOG_TAIL_BYTES = 4 * 1024 * 1024

# Where each run starts, e.g.
#   INFO  : Synching Path1 "gdrive{ABCDE}:" with Path2 "/home/me/GoogleDriveSync/"
RUN_START = re.compile(r"Synching Path1 ")
# One line per changed file, found while comparing with the previous run, e.g.
#   INFO  : - Path1    File is new                         - Notes/todo.txt
#   INFO  : - Path2    File changed: size (larger), time (newer) - a.pdf
# Path1 is Google Drive, Path2 the local folder.
FILE_CHANGE = re.compile(
    r"INFO\s*:\s+- (?P<side>Path[12])\s+(?P<what>File [^-]*?)\s+- (?P<path>.+)$"
)
ERROR = re.compile(r"(?:ERROR|CRITICAL)\s*:\s*(?P<message>.+)$")

# Path1's changes are copied to the computer, Path2's to Google Drive.
DIRECTIONS = {"Path1": "From Google Drive", "Path2": "To Google Drive"}
ARROWS = {"Path1": "↓", "Path2": "↑"}


@dataclass
class RunSummary:
    # changes[side][kind] = list of paths; kind is "added", "updated", "deleted"
    changes: dict = field(
        default_factory=lambda: {side: {} for side in DIRECTIONS}
    )
    errors: list = field(default_factory=list)

    def total(self) -> int:
        return sum(
            len(paths) for kinds in self.changes.values() for paths in kinds.values()
        )


def change_kind(what: str) -> str:
    if what.startswith("File was deleted"):
        return "deleted"
    if what.strip() == "File is new":
        return "added"
    return "updated"  # "File is newer", "File is older", "File changed: ..."


def read_last_run() -> RunSummary:
    """Parse the log lines of the most recent run."""
    summary = RunSummary()
    try:
        with open(LOG_FILE, "rb") as log:
            log.seek(0, 2)
            log.seek(max(0, log.tell() - LOG_TAIL_BYTES))
            lines = log.read().decode(errors="replace").splitlines()
    except FileNotFoundError:
        return summary

    starts = [index for index, line in enumerate(lines) if RUN_START.search(line)]
    if not starts:
        return summary
    for line in lines[starts[-1]:]:
        if match := FILE_CHANGE.search(line):
            kinds = summary.changes[match["side"]]
            kinds.setdefault(change_kind(match["what"]), []).append(match["path"])
        elif match := ERROR.search(line):
            summary.errors.append(match["message"].strip())
    return summary


def describe(summary: RunSummary) -> str:
    """The notification text: counts per direction, then paths if few."""
    if summary.total() == 0:
        return "No changes."
    lines = []
    for side, direction in DIRECTIONS.items():
        kinds = summary.changes[side]
        counts = [
            f"{len(kinds[kind])} {kind}"
            for kind in ("added", "updated", "deleted")
            if kinds.get(kind)
        ]
        if counts:
            lines.append(f"{direction}: {', '.join(counts)}")
    if summary.total() <= MAX_LISTED_PATHS:
        for side, kinds in summary.changes.items():
            for kind, paths in kinds.items():
                lines.extend(f"{ARROWS[side]} {path} ({kind})" for path in paths)
    return "\n".join(lines)


def notify(title: str, body: str, *, failed: bool = False) -> None:
    # GNOME reads the body as simple markup, so "&" and "<" must be escaped.
    command = [
        "notify-send",
        f"--app-name={APP_NAME}",
        f"--icon={'dialog-error' if failed else ICON}",
        title,
        html.escape(body, quote=False),
    ]
    if failed:
        command.insert(1, "--urgency=critical")
    subprocess.run(command, check=False)


def main() -> None:
    notify("Syncing Google Drive…", f"Started at {time.strftime('%H:%M')}.")
    result = subprocess.run(["systemctl", "--user", "start", SERVICE], check=False)
    summary = read_last_run()
    finished = f"Finished at {time.strftime('%H:%M')}."

    if result.returncode == 0:
        notify("Google Drive is in sync", f"{describe(summary)}\n{finished}")
    else:
        reason = summary.errors[0] if summary.errors else "Unknown error."
        notify(
            "Google Drive sync failed",
            f"{reason}\nDetails: {LOG_FILE}",
            failed=True,
        )


if __name__ == "__main__":
    main()
