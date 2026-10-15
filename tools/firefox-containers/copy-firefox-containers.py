#!/usr/bin/python3
"""Copy Firefox containers from the Windows partition into Ubuntu's Firefox.

Firefox Sync does not carry containers. Firefox keeps them in a file called
containers.json in each profile folder. This program finds that file in the
Windows Firefox profile (on the mounted Windows partition) and in the Ubuntu
Firefox profile, backs up the Ubuntu one, and then either:

  merge   (default) adds every Windows container that Ubuntu lacks, keeping
          the ones Ubuntu already has, or
  replace makes Ubuntu's list exactly the Windows list.

Only the containers themselves (name, colour, icon, order) are copied. Logins
inside containers and Multi-Account Containers' "always open this site in..."
rules are not.

Close Firefox before running it. Run with --dry-run to see what would happen.
"""

import argparse
import configparser
import datetime
import getpass
import json
import shutil
import sys
from pathlib import Path

DEFAULT_WINDOWS_ROOT = Path("/run/media") / getpass.getuser() / "OS"

# Where Firefox keeps profiles.ini on Windows, relative to C:\Users\<name>.
# The second one is the Microsoft Store (MSIX) version of Firefox.
WINDOWS_FIREFOX_DIR_PATTERNS = [
    "AppData/Roaming/Mozilla/Firefox",
    "AppData/Local/Packages/Mozilla.Firefox_*/LocalCache/Roaming/Mozilla/Firefox",
]

# Where Firefox keeps profiles.ini on Linux, depending on how it was installed.
LINUX_FIREFOX_DIRS = [
    Path.home() / "snap/firefox/common/.mozilla/firefox",  # Ubuntu's snap
    Path.home() / ".mozilla/firefox",  # deb / PPA / tarball
    Path.home() / ".config/mozilla/firefox",  # newer XDG location
    Path.home() / ".var/app/org.mozilla.firefox/.mozilla/firefox",  # Flatpak
]

CONTAINERS_FILE_NAME = "containers.json"

# Firefox gives some internal containers fixed IDs at the top of the 32-bit
# range. New containers must count up from the ordinary IDs below them.
FIRST_RESERVED_ID = 2**31


def highest_ordinary_id(data):
    ordinary_ids = [
        identity["userContextId"]
        for identity in data["identities"]
        if identity["userContextId"] < FIRST_RESERVED_ID
    ]
    return max([data.get("lastUserContextId", 0)] + ordinary_ids)


def read_profiles_ini(firefox_dir):
    """Return (all profile folders, default profile folder or None)."""
    ini_path = firefox_dir / "profiles.ini"
    if not ini_path.is_file():
        return [], None
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.read(ini_path, encoding="utf-8")

    def resolve(section):
        relative_or_absolute = section.get("Path", "").replace("\\", "/")
        if section.get("IsRelative", "1") == "1":
            return firefox_dir / relative_or_absolute
        return Path(relative_or_absolute)

    profiles = []
    default_profile = None
    for section_name in parser.sections():
        section = parser[section_name]
        if section_name.startswith("Profile") and "Path" in section:
            profile_dir = resolve(section)
            profiles.append(profile_dir)
            if section.get("Default") == "1" and default_profile is None:
                default_profile = profile_dir
    # [Install...] sections name the profile the installed Firefox really
    # uses. They win over the older Default=1 flag.
    for section_name in parser.sections():
        if section_name.startswith("Install") and "Default" in parser[section_name]:
            default_profile = firefox_dir / parser[section_name]["Default"]
            break
    return profiles, default_profile


def find_firefox_dirs_on_windows(windows_root):
    users_dir = windows_root / "Users"
    if not users_dir.is_dir():
        sys.exit(
            f"No Users folder at {users_dir}. Is the Windows partition mounted?"
            " Open it once in the Files app, or pass --windows-root."
        )
    firefox_dirs = []
    for pattern in WINDOWS_FIREFOX_DIR_PATTERNS:
        firefox_dirs.extend(users_dir.glob(f"*/{pattern}"))
    return [path for path in firefox_dirs if (path / "profiles.ini").is_file()]


def choose_profile(description, firefox_dirs):
    """Pick the default profile that has containers.json; ask if unclear."""
    candidates = []
    defaults = []
    for firefox_dir in firefox_dirs:
        profiles, default_profile = read_profiles_ini(firefox_dir)
        for profile_dir in profiles:
            if (profile_dir / CONTAINERS_FILE_NAME).is_file():
                candidates.append(profile_dir)
                if profile_dir == default_profile:
                    defaults.append(profile_dir)
    if not candidates:
        sys.exit(
            f"Found no {description} Firefox profile with {CONTAINERS_FILE_NAME}."
            " Pass the profile folder explicitly (see --help)."
        )
    if len(candidates) == 1:
        return candidates[0]
    if len(defaults) == 1:
        return defaults[0]
    print(f"Several {description} Firefox profiles found:")
    for number, profile_dir in enumerate(candidates, start=1):
        marker = "  (default)" if profile_dir in defaults else ""
        print(f"  {number}. {profile_dir}{marker}")
    while True:
        answer = input(f"Which one? [1-{len(candidates)}] ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(candidates):
            return candidates[int(answer) - 1]


def load_containers(profile_dir):
    with open(profile_dir / CONTAINERS_FILE_NAME, encoding="utf-8") as file:
        return json.load(file)


def container_key(identity):
    """Built-in containers have an l10nId instead of a name."""
    return identity.get("name") or identity.get("l10nId")


def container_label(identity):
    if identity.get("name"):
        return identity["name"]
    # "userContextPersonal.label" -> "Personal"
    l10n_id = identity.get("l10nId", "?")
    return l10n_id.removeprefix("userContext").removesuffix(".label")


def visible_containers(data):
    """Containers shown to the user; the others are Firefox internals."""
    return [identity for identity in data["identities"] if identity.get("public")]


def merge(source_data, target_data):
    """Add source containers whose name the target lacks. Returns added list."""
    existing_keys = {container_key(identity) for identity in target_data["identities"]}
    next_id = 1 + highest_ordinary_id(target_data)
    added = []
    for identity in visible_containers(source_data):
        if container_key(identity) in existing_keys:
            continue
        # New ID so it can't clash with a container that already exists here
        # (and with the logins Firefox keeps under that ID).
        new_identity = dict(identity, userContextId=next_id)
        target_data["identities"].append(new_identity)
        added.append(new_identity)
        next_id += 1
    target_data["lastUserContextId"] = next_id - 1
    return added


def replace(source_data, target_data):
    """Use the source's visible containers, keep the target's internal ones."""
    internal = [i for i in target_data["identities"] if not i.get("public")]
    internal_ids = {identity["userContextId"] for identity in internal}
    next_id = 1 + max(
        highest_ordinary_id(source_data), highest_ordinary_id(target_data)
    )
    visible = []
    for identity in visible_containers(source_data):
        new_identity = dict(identity)
        if new_identity["userContextId"] in internal_ids:
            new_identity["userContextId"] = next_id
            next_id += 1
        visible.append(new_identity)
    target_data["identities"] = visible + internal
    target_data["lastUserContextId"] = next_id - 1
    return visible


def firefox_is_running(profile_dir):
    # While it runs, Firefox on Linux keeps a "lock" symlink in the profile
    # pointing at "<IP address>:+<process ID>". After a crash the link stays,
    # so also check that the process still exists.
    lock = profile_dir / "lock"
    if not lock.is_symlink():
        return False
    process_id = str(lock.readlink()).rpartition("+")[2]
    return not process_id.isdigit() or Path("/proc", process_id).exists()


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--windows-root",
        type=Path,
        default=DEFAULT_WINDOWS_ROOT,
        help="where the Windows partition is mounted (default: %(default)s)",
    )
    parser.add_argument(
        "--source", type=Path, help="Windows Firefox profile folder (skips the search)"
    )
    parser.add_argument(
        "--target", type=Path, help="Ubuntu Firefox profile folder (skips the search)"
    )
    parser.add_argument("--mode", choices=["merge", "replace"], default="merge")
    parser.add_argument(
        "--dry-run", action="store_true", help="show what would change, write nothing"
    )
    arguments = parser.parse_args()

    source_profile = arguments.source or choose_profile(
        "Windows", find_firefox_dirs_on_windows(arguments.windows_root)
    )
    target_profile = arguments.target or choose_profile(
        "Ubuntu", [path for path in LINUX_FIREFOX_DIRS if path.is_dir()]
    )
    print(f"From: {source_profile / CONTAINERS_FILE_NAME}")
    print(f"To:   {target_profile / CONTAINERS_FILE_NAME}")

    if firefox_is_running(target_profile) and not arguments.dry_run:
        sys.exit(
            "Firefox is running and would overwrite the change when it quits."
            " Close it (check with: pgrep -a firefox) and run this again."
        )

    source_data = load_containers(source_profile)
    target_data = load_containers(target_profile)
    for system_name, data in [("Windows", source_data), ("Ubuntu", target_data)]:
        labels = ", ".join(map(container_label, visible_containers(data)))
        print(f"{system_name + ' containers:':20}{labels}")

    if arguments.mode == "merge":
        added = merge(source_data, target_data)
        if not added:
            print("Ubuntu already has every Windows container. Nothing to do.")
            return
        print("Adding:", ", ".join(map(container_label, added)))
    else:
        result = replace(source_data, target_data)
        print("Ubuntu will have:", ", ".join(map(container_label, result)))

    if arguments.dry_run:
        print("Dry run: nothing written.")
        return

    target_file = target_profile / CONTAINERS_FILE_NAME
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_file = target_file.with_name(f"{CONTAINERS_FILE_NAME}.{timestamp}.bak")
    copy_number = 1
    while backup_file.exists():
        copy_number += 1
        backup_file = target_file.with_name(
            f"{CONTAINERS_FILE_NAME}.{timestamp}-{copy_number}.bak"
        )
    shutil.copy2(target_file, backup_file)
    temporary_file = target_file.with_suffix(".json.tmp")
    with open(temporary_file, "w", encoding="utf-8") as file:
        json.dump(target_data, file, ensure_ascii=False)
    temporary_file.replace(target_file)
    print(f"Done. Backup of the old file: {backup_file}")
    print("Start Firefox; the containers are in the + button's dropdown.")


if __name__ == "__main__":
    main()
