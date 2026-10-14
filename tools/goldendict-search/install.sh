#!/usr/bin/env bash
# Adds GoldenDict-ng lookups to the GNOME overview search for the current
# user. Run it again to update.
set -euo pipefail

source_dir=$(dirname "$(readlink -f "$0")")
bus_name="io.github.toldry.GoldenDictSearch"
provider_dir="/usr/local/share/gnome-shell/search-providers"

if ! command -v goldendict > /dev/null \
    && ! flatpak info io.github.xiaoyifang.goldendict_ng > /dev/null 2>&1; then
    echo "GoldenDict-ng isn't installed. Install it first with:" >&2
    echo "    sudo apt install goldendict-ng" >&2
    exit 1
fi
if ! /usr/bin/python3 -c "from gi.repository import Gio" 2> /dev/null; then
    echo "Missing Python's GNOME bindings. Install them first with:" >&2
    echo "    sudo apt install python3-gi" >&2
    exit 1
fi

install -D --mode=755 "$source_dir/goldendict-search-provider" \
    "$HOME/.local/bin/goldendict-search-provider"

# D-Bus starts the provider on GNOME's first search. Service files need an
# absolute path, so this one is written here rather than copied.
mkdir -p "$HOME/.local/share/dbus-1/services"
cat > "$HOME/.local/share/dbus-1/services/$bus_name.service" << SERVICE
[D-BUS Service]
Name=$bus_name
Exec=/usr/bin/python3 $HOME/.local/bin/goldendict-search-provider
SERVICE

# GNOME Shell only reads search providers from system folders, so this
# step needs sudo.
echo "Registering the search provider with GNOME (asks for your password)..."
sudo install -D --mode=644 "$source_dir/goldendict-search-provider.ini" \
    "$provider_dir/goldendict-search-provider.ini"

# Stop an older copy of the provider, so the next search starts the new one.
pkill -f "$HOME/.local/bin/goldendict-search-provider" 2> /dev/null || true

# GNOME Shell reloads its providers when this setting changes, so flipping
# it off and on again makes the new one show up without logging out.
if [[ $(gsettings get org.gnome.desktop.search-providers disable-external) \
    == "false" ]]; then
    gsettings set org.gnome.desktop.search-providers disable-external true
    gsettings set org.gnome.desktop.search-providers disable-external false
    echo "Installed. Press Super and type a word to try it."
else
    echo "Installed, but App Search is off. Turn it on in"
    echo "Settings > Search, then press Super and type a word."
fi
