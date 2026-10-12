# An ISO date and a 24-hour clock in the top bar

Change the clock in the middle of GNOME's top bar from `Oct 12  11:53` to `2026-10-12              23:53`: the date written year-month-day, a wide gap, then the time in 24-hour form.

> **Who this is for:** anyone running Ubuntu with GNOME (the default desktop) from [GUIDE.md](GUIDE.md) or [DUAL-BOOT-PLAN.md](DUAL-BOOT-PLAN.md).
>
> **Status:** written in October 2026 for Ubuntu 24.04 (GNOME 46). The extension it uses supports GNOME 45 to 51, so it also works on Ubuntu 25.10 and 26.04. The steps have not yet been run on a real Duo, so please [report problems](https://github.com/Toldry/zenbook-duo-linux-guide/issues).

---

## Contents

- [Why an extension](#why-an-extension)
- [1. Install the extension](#1-install-the-extension)
- [2. Set the format](#2-set-the-format)
- [Other formats](#other-formats)
- [Limitations](#limitations)
- [Troubleshooting](#troubleshooting)
- [How to undo it](#how-to-undo-it)
- [Sources](#sources)

---

## Why an extension

GNOME's own clock settings are three on/off switches: show the date, show the weekday, show seconds, plus a choice between 12-hour and 24-hour time. There is no way to type your own format, so `2026-10-12` isn't possible with GNOME alone.

The [Panel Date Format](https://extensions.gnome.org/extension/1462/panel-date-format/) extension adds that. It hides GNOME's clock text and shows its own in the same place, built from a format string you choose. Clicking it still opens the calendar and notifications as before. No extra program is needed; the whole change is one setting.

---

## 1. Install the extension

Pick **one** of the two ways.

### Option A: with the Extension Manager app (easier)

```bash
sudo apt install gnome-shell-extension-manager
```

1. Open **Extension Manager** from the app grid.
2. Go to the **Browse** tab and search for **Panel Date Format** (by KEIII).
3. Click **Install** and confirm.

The extension starts right away; there is no need to log out.

### Option B: from the terminal only

```bash
uuid="panel-date-format@keiii.github.com"
shell_version="$(gnome-shell --version | grep -oE '[0-9]+' | head -n 1)"
wget -O /tmp/panel-date-format.zip \
  "https://extensions.gnome.org/download-extension/${uuid}.shell-extension.zip?shell_version=${shell_version}"
gnome-extensions install --force /tmp/panel-date-format.zip
```

This downloads the build that matches your GNOME version and installs it for your user only (into `~/.local/share/gnome-shell/extensions/`).

On Wayland, GNOME only notices extensions installed this way after you **log out and back in**. Then switch it on:

```bash
gnome-extensions enable panel-date-format@keiii.github.com
```

### Check that it's running

```bash
gnome-extensions info panel-date-format@keiii.github.com
```

The output should say `State: ACTIVE` (older GNOME versions say `ENABLED`). The top bar now shows the extension's default format, `2026.10.12 23:53`.

---

## 2. Set the format

```bash
dconf write /org/gnome/shell/extensions/panel-date-format/format \
  "'%Y-%m-%d              %H:%M'"
```

There are **14 spaces** between `%d` and `%H`. The double quotes are for the shell; the single quotes inside them are part of the value, because `dconf` wants a quoted text value.

The extension rereads the setting each time the clock ticks, so the new format appears within a minute. The result:

```
 ┌──────────────────────────────────────────────────────────────────┐
 │ ▬ • •          2026-10-12              23:53          en  ◀) 79% │
 └──────────────────────────────────────────────────────────────────┘
```

The whole text stays centred in the bar, so a wider gap pushes the date to the left and the time to the right by the same amount.

What each part means:

| Code | Means | Example |
|---|---|---|
| `%Y` | Year, 4 digits | `2026` |
| `%m` | Month, 2 digits | `10` |
| `%d` | Day of the month, 2 digits | `12` |
| `%H` | Hour, 00 to 23 | `23` |
| `%M` | Minute, 2 digits | `53` |

`%H` always gives 24-hour time, whatever the 12/24-hour switch in Settings says.

To see the current value:

```bash
dconf read /org/gnome/shell/extensions/panel-date-format/format
```

You can also change it in a window instead of the terminal: `sudo apt install dconf-editor`, open **dconf Editor** and go to `/org/gnome/shell/extensions/panel-date-format/format`.

---

## Other formats

| Format string | Shows |
|---|---|
| `'%Y-%m-%d %H:%M'` | `2026-10-12 23:53` (one space) |
| `'%F    %R'` | `2026-10-12    23:53` (`%F` and `%R` are shortcuts for the two halves) |
| `'%a %Y-%m-%d              %H:%M'` | `Mon 2026-10-12              23:53` |
| `'%Y-%m-%d              %H:%M:%S'` | with seconds, see below |
| `'%Y-%m-%d (week %V)              %H:%M'` | `2026-10-12 (week 42)              23:53` |

The full list of codes is in GLib's documentation: https://docs.gtk.org/glib/method.DateTime.format.html

**Seconds:** the extension only redraws when GNOME's own clock ticks, which is once a minute. For `%S` to count up, also switch on seconds in GNOME:

```bash
gsettings set org.gnome.desktop.interface clock-show-seconds true
```

**A gap of a fixed width:** a normal space is fairly narrow in the top-bar font, so the gap's width depends on the font. For a gap that's wider per character, use the "em space" (U+2003), which is as wide as the letter M. This sets 4 of them:

```bash
dconf write /org/gnome/shell/extensions/panel-date-format/format \
  "'%Y-%m-%d$(printf '    ')%H:%M'"
```

---

## Limitations

- **The lock screen keeps GNOME's own clock.** The extension switches itself off while the screen is locked, as GNOME requires of extensions unless they ask otherwise. It comes back when you unlock.
- **The login screen is not changed.** It runs before you log in, so your extensions aren't loaded there.
- **Major Ubuntu upgrades** can briefly disable extensions until the author releases a matching version. If the old clock comes back after an upgrade, open Extension Manager and look for an update.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Clock didn't change after `dconf write` | The minute hasn't ticked yet | Wait up to 60 seconds |
| Clock still didn't change | The extension isn't running | Run the check in [step 1](#check-that-its-running); if it isn't `ACTIVE`, run `gnome-extensions enable panel-date-format@keiii.github.com`, or log out and back in after Option B |
| `gnome-extensions install` worked, but `enable` says the extension doesn't exist | GNOME on Wayland hasn't noticed it yet | Log out and back in |
| `dconf write` says *"error parsing value"* | The single quotes inside the double quotes are missing | Copy the command again exactly |
| Top bar shows the text `%Y-%m-%d…` literally | A typo in a code, or a `%` code GLib doesn't know | Check the format against the table above |
| Extension Manager says it's *"unsupported"* | Your GNOME version is newer than the extension's latest release | Wait for an update; check `gnome-shell --version` |

---

## How to undo it

To go back to the extension's default format but keep it installed:

```bash
dconf reset /org/gnome/shell/extensions/panel-date-format/format
```

To go back to GNOME's own clock, switch the extension off:

```bash
gnome-extensions disable panel-date-format@keiii.github.com
```

To remove it completely:

```bash
gnome-extensions uninstall panel-date-format@keiii.github.com
dconf reset -f /org/gnome/shell/extensions/panel-date-format/
```

(Or use the **Installed** tab in Extension Manager.)

---

## Sources

- The extension, its setting name and the `dconf write` command: https://github.com/KEIII/gnome-shell-panel-date-format (GNOME versions 45 to 51 listed in its `metadata.json`, version 25, September 2026)
- The extension's page: https://extensions.gnome.org/extension/1462/panel-date-format/
- The format codes: GLib, `g_date_time_format`: https://docs.gtk.org/glib/method.DateTime.format.html
- GNOME's own clock settings (`clock-show-date`, `clock-show-weekday`, `clock-show-seconds`, `clock-format`): https://gitlab.gnome.org/GNOME/gsettings-desktop-schemas/-/blob/master/schemas/org.gnome.desktop.interface.gschema.xml.in
- Extension Manager: https://github.com/mjakeman/extension-manager
- The `gnome-extensions` command: https://manpages.ubuntu.com/manpages/noble/man1/gnome-extensions.1.html
- The date format itself, ISO 8601: https://en.wikipedia.org/wiki/ISO_8601
