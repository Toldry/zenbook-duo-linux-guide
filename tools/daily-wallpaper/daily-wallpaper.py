#!/usr/bin/python3
"""Show a different, shuffled wallpaper on each monitor, changing once per day.

GNOME has a single wallpaper setting for all monitors. This program picks one
image per monitor, joins them into one image laid out like the monitors, and
sets it with GNOME's "spanned" mode, so each monitor shows its own part.

Run without arguments, it keeps running: it changes the pictures once per day
and rebuilds the image right away when the monitor layout changes (for
example when the Zenbook Duo's keyboard is attached or removed).

See DAILY-WALLPAPER.md in the repository for installation and configuration.
"""

import argparse
import configparser
import contextlib
import dataclasses
import datetime
import fcntl
import json
import logging
import os
import random
import sys
import time
from pathlib import Path

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gio, GLib  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402

APP_NAME = "daily-wallpaper"
CONFIG_FILE = (
    Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    / APP_NAME
    / "config.ini"
)
STATE_DIR = (
    Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / APP_NAME
)
STATE_FILE = STATE_DIR / "state.json"
LOCK_FILE = STATE_DIR / "lock"

DEFAULT_SETTINGS = {
    "folder": "~/Pictures/Wallpapers",
    "change_time": "00:00",
    "include_subfolders": "yes",
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
JPEG_QUALITY = 92

# How often the running program checks whether a new day has started. A
# periodic check (rather than one long timer) also catches the change after
# the laptop wakes from sleep.
CHECK_INTERVAL_SECONDS = 60
# Monitor changes arrive in bursts; wait for them to settle before rebuilding.
MONITOR_CHANGE_DELAY_MILLISECONDS = 1500

MUTTER_DISPLAY_CONFIG = "org.gnome.Mutter.DisplayConfig"
MUTTER_DISPLAY_CONFIG_PATH = "/org/gnome/Mutter/DisplayConfig"
MUTTER_LAYOUT_MODE_LOGICAL = 1

BACKGROUND_SCHEMA = "org.gnome.desktop.background"

log = logging.getLogger(APP_NAME)


class WallpaperError(Exception):
    """A problem the user has to fix, such as an empty wallpaper folder."""


@dataclasses.dataclass(frozen=True)
class Settings:
    folder: Path
    change_time: datetime.time
    include_subfolders: bool


@dataclasses.dataclass(frozen=True)
class Monitor:
    """A monitor's place in GNOME's layout, in layout coordinates."""

    connector: str
    x: int
    y: int
    width: int
    height: int


def load_settings() -> Settings:
    parser = configparser.ConfigParser()
    parser.read_dict({"wallpaper": DEFAULT_SETTINGS})
    parser.read(CONFIG_FILE)
    section = parser["wallpaper"]
    try:
        change_time = datetime.time.fromisoformat(section["change_time"])
        include_subfolders = section.getboolean("include_subfolders")
    except ValueError as error:
        raise WallpaperError(f"Invalid setting in {CONFIG_FILE}: {error}") from None
    return Settings(
        folder=Path(section["folder"]).expanduser(),
        change_time=change_time,
        include_subfolders=include_subfolders,
    )


def current_day(change_time: datetime.time) -> str:
    """The date whose pictures should show now, given the daily change time."""
    now = datetime.datetime.now()
    today = now.date()
    if now.time() < change_time:
        today -= datetime.timedelta(days=1)
    return today.isoformat()


# --- Monitors ---------------------------------------------------------------


def read_monitors() -> tuple[list[Monitor], float]:
    """Ask GNOME for the monitor layout.

    Returns the monitors sorted top-to-bottom, then left-to-right, and the
    factor that turns layout coordinates into real pixels.
    """
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    reply = bus.call_sync(
        MUTTER_DISPLAY_CONFIG,
        MUTTER_DISPLAY_CONFIG_PATH,
        MUTTER_DISPLAY_CONFIG,
        "GetCurrentState",
        None,
        None,
        Gio.DBusCallFlags.NONE,
        -1,
        None,
    )
    return parse_display_state(reply.unpack())


def parse_display_state(display_state) -> tuple[list[Monitor], float]:
    """Turn Mutter's GetCurrentState reply into a list of monitors.

    In "logical" layout mode, positions are in scaled units (a 2880 px wide
    screen at 200 % is 1440 units wide). In "physical" mode they are pixels.
    """
    _serial, physical_monitors, logical_monitors, properties = display_state
    # Mutter documents a missing "layout-mode" as meaning logical mode.
    layout_mode = properties.get("layout-mode", MUTTER_LAYOUT_MODE_LOGICAL)
    layout_is_logical = layout_mode == MUTTER_LAYOUT_MODE_LOGICAL

    current_resolution = {}
    for (connector, *_), modes, _properties in physical_monitors:
        for _id, width, height, _rate, _scale, _scales, mode_properties in modes:
            if mode_properties.get("is-current"):
                current_resolution[connector] = (width, height)

    monitors = []
    pixel_scale = 1.0
    for logical_monitor in logical_monitors:
        x, y, scale, transform, _primary, members, _properties = logical_monitor
        connector = members[0][0]
        if connector not in current_resolution:
            continue
        width, height = current_resolution[connector]
        if transform % 2 == 1:  # rotated by 90 or 270 degrees
            width, height = height, width
        if layout_is_logical:
            width, height = round(width / scale), round(height / scale)
            pixel_scale = max(pixel_scale, scale)
        monitors.append(Monitor(connector, x, y, width, height))

    monitors.sort(key=lambda monitor: (monitor.y, monitor.x))
    return monitors, pixel_scale


# --- Picking images -----------------------------------------------------------


def find_images(settings: Settings) -> list[str]:
    if not settings.folder.is_dir():
        raise WallpaperError(f"Wallpaper folder not found: {settings.folder}")
    pattern = "**/*" if settings.include_subfolders else "*"
    images = [
        str(path)
        for path in settings.folder.glob(pattern)
        if path.suffix.lower() in IMAGE_EXTENSIONS and path.is_file()
    ]
    if not images:
        raise WallpaperError(f"No images found in {settings.folder}")
    return images


def draw_from_bag(state: dict, settings: Settings, avoid: set[str]) -> str:
    """Take the next image from the shuffled bag, refilling it when empty.

    Every image is shown once before any image repeats. Images in `avoid`
    (already on another monitor today) are skipped when possible.
    """
    bag_source = f"{settings.folder}|{settings.include_subfolders}"
    if state.get("bag_source") != bag_source:
        state["bag"], state["bag_source"] = [], bag_source

    for _refill in range(2):
        bag = state["bag"]
        while bag:
            candidate = bag.pop()
            if candidate not in avoid and Path(candidate).is_file():
                return candidate
        bag.extend(find_images(settings))
        random.shuffle(bag)

    # Fewer images than monitors: a repeat can't be avoided.
    return random.choice(find_images(settings))


def load_image_for(
    monitor: Monitor, state: dict, settings: Settings, pixel_scale: float
) -> Image.Image:
    """Open today's image for a monitor, scaled and cropped to fill it.

    Draws a replacement when the picked image is missing or unreadable.
    """
    picks = state["picks"]
    size = (
        round(monitor.width * pixel_scale),
        round(monitor.height * pixel_scale),
    )
    while True:
        path = picks.get(monitor.connector)
        if path and Path(path).is_file():
            try:
                with Image.open(path) as image:
                    image = ImageOps.exif_transpose(image).convert("RGB")
                    return ImageOps.fit(image, size, Image.Resampling.LANCZOS)
            except OSError as error:
                log.warning("Skipping unreadable image %s: %s", path, error)
        other_picks = {
            pick for connector, pick in picks.items() if connector != monitor.connector
        }
        picks[monitor.connector] = draw_from_bag(state, settings, other_picks)


# --- State and output -----------------------------------------------------------


@contextlib.contextmanager
def locked_state():
    """Load the saved state, yield it for changes, then save it.

    A file lock keeps the background service and a manual `--next` from
    changing the state at the same time.
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOCK_FILE, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            state = json.loads(STATE_FILE.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            state = {}
        yield state
        temporary_file = STATE_FILE.with_suffix(".tmp")
        temporary_file.write_text(json.dumps(state, indent=2))
        os.replace(temporary_file, STATE_FILE)


def compose_wallpaper(
    monitors: list[Monitor], state: dict, settings: Settings, pixel_scale: float
) -> Path:
    canvas_width = max(monitor.x + monitor.width for monitor in monitors)
    canvas_height = max(monitor.y + monitor.height for monitor in monitors)
    canvas = Image.new(
        "RGB",
        (round(canvas_width * pixel_scale), round(canvas_height * pixel_scale)),
    )
    for monitor in monitors:
        tile = load_image_for(monitor, state, settings, pixel_scale)
        position = (round(monitor.x * pixel_scale), round(monitor.y * pixel_scale))
        canvas.paste(tile, position)

    # A new file name each time; GNOME doesn't reload a file it already shows.
    output = STATE_DIR / f"wallpaper-{time.time_ns()}.jpg"
    canvas.save(output, quality=JPEG_QUALITY)
    return output


def set_gnome_background(image: Path) -> None:
    background = Gio.Settings.new(BACKGROUND_SCHEMA)
    background.set_string("picture-uri", image.as_uri())
    background.set_string("picture-uri-dark", image.as_uri())
    background.set_string("picture-options", "spanned")
    Gio.Settings.sync()


def delete_old_wallpapers(keep: Path) -> None:
    for old in STATE_DIR.glob("wallpaper-*.jpg"):
        if old != keep:
            old.unlink(missing_ok=True)


# --- Main actions -----------------------------------------------------------


def describe_layout(monitors: list[Monitor], picks: dict) -> list[dict]:
    """What is on screen: each monitor's place and image, for change checks."""
    return [
        dataclasses.asdict(monitor) | {"image": picks[monitor.connector]}
        for monitor in monitors
    ]


def update_wallpaper(new_pictures: bool = False) -> None:
    """Pick today's images if needed and apply them if anything changed."""
    settings = load_settings()
    monitors, pixel_scale = read_monitors()
    if not monitors:
        log.info("No active monitors; nothing to do")
        return

    with locked_state() as state:
        day = current_day(settings.change_time)
        if new_pictures or state.get("day") != day:
            state["day"], state["picks"] = day, {}
        picks = state["picks"]

        # Picks are kept per monitor, so a screen that turns off and on again
        # during the day gets the same picture back.
        for monitor in monitors:
            path = picks.get(monitor.connector)
            if not path or not Path(path).is_file():
                picks[monitor.connector] = draw_from_bag(
                    state, settings, avoid=set(picks.values())
                )

        current_image = Path(state.get("current_image", ""))
        applied = describe_layout(monitors, picks)
        if state.get("applied") == applied and current_image.is_file():
            return

        output = compose_wallpaper(monitors, state, settings, pixel_scale)
        set_gnome_background(output)
        delete_old_wallpapers(keep=output)
        state["current_image"] = str(output)
        state["applied"] = describe_layout(monitors, picks)
        log.info(
            "Wallpaper set: %s",
            ", ".join(
                f"{monitor.connector}={Path(picks[monitor.connector]).name}"
                for monitor in monitors
            ),
        )


def update_and_log_errors() -> bool:
    """Run one update; report problems without stopping the service."""
    try:
        update_wallpaper()
    except WallpaperError as error:
        log.error("%s", error)
    except GLib.Error as error:
        log.warning("Couldn't read the monitor layout (yet): %s", error.message)
    except Exception:
        log.exception("Unexpected error while updating the wallpaper")
    return GLib.SOURCE_CONTINUE


def run_service() -> None:
    pending_update = None

    def on_monitors_changed(*_signal_arguments) -> None:
        nonlocal pending_update
        if pending_update is not None:
            GLib.source_remove(pending_update)

        def run_pending_update() -> bool:
            nonlocal pending_update
            pending_update = None
            update_and_log_errors()
            return GLib.SOURCE_REMOVE

        pending_update = GLib.timeout_add(
            MONITOR_CHANGE_DELAY_MILLISECONDS, run_pending_update
        )

    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    bus.signal_subscribe(
        None,
        MUTTER_DISPLAY_CONFIG,
        "MonitorsChanged",
        MUTTER_DISPLAY_CONFIG_PATH,
        None,
        Gio.DBusSignalFlags.NONE,
        on_monitors_changed,
    )
    GLib.timeout_add_seconds(CHECK_INTERVAL_SECONDS, update_and_log_errors)
    update_and_log_errors()
    GLib.MainLoop().run()


def print_status() -> None:
    settings = load_settings()
    config_note = "" if CONFIG_FILE.exists() else " (not created; using defaults)"
    print(f"Config file:  {CONFIG_FILE}{config_note}")
    print(f"Folder:       {settings.folder}")
    print(f"Change time:  {settings.change_time.strftime('%H:%M')}")
    print(f"Subfolders:   {'yes' if settings.include_subfolders else 'no'}")
    try:
        state = json.loads(STATE_FILE.read_text())
    except FileNotFoundError:
        print("No pictures picked yet.")
        return
    print(f"Pictures for: {state.get('day')}")
    for connector, path in sorted(state.get("picks", {}).items()):
        print(f"  {connector}: {path}")
    print(f"Left before the shuffle repeats: {len(state.get('bag', []))}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Different shuffled wallpaper per monitor, changed daily (GNOME)."
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "--once", action="store_true", help="update the wallpaper once and exit"
    )
    action.add_argument(
        "--next", action="store_true", help="pick new pictures now and exit"
    )
    action.add_argument(
        "--status", action="store_true", help="show settings and today's pictures"
    )
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if arguments.status:
        print_status()
    elif arguments.once or arguments.next:
        try:
            update_wallpaper(new_pictures=arguments.next)
        except WallpaperError as error:
            sys.exit(f"Error: {error}")
        except GLib.Error as error:
            sys.exit(
                "Error: couldn't read the monitor layout from GNOME. Run this "
                f"inside a GNOME session.\n({error.message})"
            )
    else:
        run_service()


if __name__ == "__main__":
    main()
