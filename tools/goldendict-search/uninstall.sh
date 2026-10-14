#!/usr/bin/env bash
# Removes the GoldenDict-ng search provider. GoldenDict-ng itself and its
# dictionaries are left alone.
set -euo pipefail

bus_name="io.github.toldry.GoldenDictSearch"

pkill -f "$HOME/.local/bin/goldendict-search-provider" 2> /dev/null || true
rm -f "$HOME/.local/bin/goldendict-search-provider" \
    "$HOME/.local/share/dbus-1/services/$bus_name.service"
echo "Removing the search provider from GNOME (asks for your password)..."
sudo rm -f /usr/local/share/gnome-shell/search-providers/goldendict-search-provider.ini

if [[ $(gsettings get org.gnome.desktop.search-providers disable-external) \
    == "false" ]]; then
    gsettings set org.gnome.desktop.search-providers disable-external true
    gsettings set org.gnome.desktop.search-providers disable-external false
fi

echo "Uninstalled."
