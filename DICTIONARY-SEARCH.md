# Look up words from the Super search

Press `Super` and type a word in English, Spanish or Hebrew. The overview shows the word with the start of its definition, straight from your dictionaries. Choose a result to open the full entry, with synonyms and translations, in GoldenDict-ng. Everything works offline.

> **Who this is for:** anyone running Ubuntu with GNOME (the default desktop) from [GUIDE.md](GUIDE.md) or [DUAL-BOOT-PLAN.md](DUAL-BOOT-PLAN.md) who wants a quick offline dictionary.
>
> **Status:** written in October 2026 for Ubuntu 24.04 (GNOME 46). The parts it relies on are the same in GNOME 47 to 49, so it should also work on Ubuntu 24.10 to 26.04. The search provider was tested against simulated GNOME Shell calls on D-Bus, with the three Wiktionary dictionaries. It has not yet been run on a real Duo, so please [report problems](https://github.com/Toldry/zenbook-duo-linux-guide/issues).

---

## Contents

- [Why a small add-on is needed](#why-a-small-add-on-is-needed)
- [What you get](#what-you-get)
- [1. Install GoldenDict-ng](#1-install-goldendict-ng)
- [2. Add dictionaries](#2-add-dictionaries)
- [3. Install the search provider](#3-install-the-search-provider)
- [4. Turn it on in Settings](#4-turn-it-on-in-settings)
- [5. Try it](#5-try-it)
- [Optional: only search with a prefix](#optional-only-search-with-a-prefix)
- [How it works](#how-it-works)
- [Limitations](#limitations)
- [Troubleshooting](#troubleshooting)
- [How to undo it](#how-to-undo-it)
- [Sources](#sources)

---

## Why a small add-on is needed

**Settings → Search** has two parts:

- **App Search** is one switch for all results that come from apps (the overview's own app and settings matches are always on).
- **Search Results** lists every installed app that offers results to the overview. You can switch each one on or off and drag them into the order you like.

An app only appears in that list if it ships a *search provider*: a small program GNOME asks for results on every keystroke. GoldenDict-ng doesn't ship one, so with settings alone, typing `hola` after `Super` only finds the GoldenDict-ng app itself, not the word.

This guide adds the missing search provider: one Python script that reads the dictionary files itself ([`tools/goldendict-search/`](tools/goldendict-search/)) and two small config files. It uses only what Ubuntu already has (Python and its GNOME bindings). No launcher such as Ulauncher or Albert is needed, and no GNOME extension. Once it's installed, GoldenDict-ng shows up under **Search Results** like any other app.

---

## What you get

```mermaid
sequenceDiagram
    participant You
    participant GNOME as GNOME overview
    participant P as Search provider
    participant D as Dictionary files
    participant GD as GoldenDict-ng
    You->>GNOME: Super, then type "hablo"
    GNOME->>P: GetInitialResultSet(["hablo"])
    P->>D: Look up "hablo"
    D-->>P: inflected form of "hablar"
    P-->>GNOME: "hablo → hablar", es-es · Verbo intransitivo: Expresar algo usando palabras…
    You->>GNOME: ↓ to the row, Enter (or click it)
    GNOME->>P: ActivateResult
    P->>GD: goldendict -- hablar
    GD-->>You: Window with every dictionary's entry for "hablar"
```

What the overview shows for `Super`, `reaccion`:

```
GoldenDict-ng
  📖 reacción
     es-es · Sustantivo femenino: Hecho o acción que se opone o resiste a otra, …
  📖 reacción química
     es-es · Locución sustantiva femenina: Proceso que involucra la rotura o la creación de …
  📖 reacción estereoespecífica
     es-es · Locución sustantiva: Reacción química en la que reactivos …
  📖 avión a reacción
     es-es · Locución sustantiva y masculina: Avión que es impulsado por uno o más motores a reacción.
```

- **Up to 5 results**, the most GNOME shows per app. Only whole words match, not words that merely start with what you typed. Exact headwords come first, from every dictionary, then inflected forms (`hablo` → `hablar`, `ran` → `run`), then multi-word entries that contain the word anywhere (`reaccion` → `reacción química`, `avión a reacción`), those starting with it first.
- **Accents are optional.** `reaccion` finds `reacción`, `pinguino` finds `pingüino` and `nino` finds `niño`. Hebrew works with or without vowel points (niqqud).
- **One row per word.** When several dictionaries, or several entries of one dictionary, have the same word, they share a row: each dictionary's definition after its label, separated by `‖`, for example *intj: (informal) Hello, hi, hey. ‖ es-es · Interjección: Expresión de saludo…* for `hola`. This leaves more of the 5 rows for other words.
- **The start of the definition** is shown under each word: part of speech, then the senses separated by `·`. GNOME cuts it off at the end of the line, so with several dictionaries in a row, the last one may not fit.
- **Any language, any script.** Hebrew typed right to left works the same as English or Spanish. Switch keyboard layouts with `Super+Space` as usual.
- **Nothing when nothing matches.** A search for an app name that isn't a word shows no GoldenDict-ng group.

---

## 1. Install GoldenDict-ng

GoldenDict-ng is the maintained successor of GoldenDict. Ubuntu's `goldendict` package is the old original, so install the `-ng` one. Open a terminal (`Ctrl+Alt+T`) and run:

```bash
sudo apt install goldendict-ng
```

This adds the command `goldendict` and a **GoldenDict-ng** entry in the app grid.

<details>
<summary>Using the Flatpak instead</summary>

The Flathub version is usually newer than Ubuntu's. The search provider works with it too.

```bash
sudo apt install flatpak
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install flathub io.github.xiaoyifang.goldendict_ng
```

The Flatpak can't see your home folder by default, so give it read access to the folder where the dictionaries will go (step 2):

```bash
mkdir -p ~/.local/share/dictionaries
flatpak override --user --filesystem=xdg-data/dictionaries:ro io.github.xiaoyifang.goldendict_ng
```

It also can't read dictionaries installed with `apt` into `/usr/share`, so the optional WordNet step below doesn't apply to it.

Install only one of the two versions. If both are installed, the search provider uses the `apt` one.

</details>

Open **GoldenDict-ng** once from the app grid, then close it. That creates its settings folder.

---

## 2. Add dictionaries

GoldenDict-ng comes with no dictionaries. Good free ones come from Wiktionary, already converted to StarDict format (a format GoldenDict-ng reads):

| Label | Look up | Explained in | Entries | From |
|---|---|---|---|---|
| `en-en` | English words | English | 462,000 | Wiktionary-Dictionaries, built November 2022 |
| `en-es` | English words | **Spanish**: translations and short definitions | 19,500 | Wiktionary StarDict, September 2026 |
| `es-es` | Spanish words | **Spanish** | 123,000 | Wiktionary StarDict, September 2026 |
| `he-en` | Hebrew words | English | 17,700 | Wiktionary StarDict, September 2026 |

The label, `<word language>-<explanation language>`, is what the overview shows before each definition, except for `en-en`, whose definitions are shown without a label. `en-es` and `es-es` come from the Spanish Wiktionary (*Wikcionario*), so `en-es` is the Spanish Wiktionary's entries for English words: much smaller than `en-en`, but in Spanish.

**There is no free Hebrew-Hebrew dictionary to download.** The Hebrew Wiktionary (*ויקימילון*) exists, but wiktextract, the tool these dictionary files are built with, can't read it yet, and I found no other ready-made conversion. The well-known Hebrew dictionaries (Even-Shoshan, Rav-Milim) aren't free to copy. `he-en`, built from the English Wiktionary, is the best offline option. Its 17,700 entries cover common words well and rare ones thinly.

The English one comes from a different project because the Wiktionary StarDict project's `en-en` file is 130 MB to download, against 22 MB here.

### Step 1: Download them

They go in `~/.local/share/dictionaries`. Linux keeps a user's data files, the files programs read, under `~/.local/share`, as the XDG Base Directory standard says. GoldenDict-ng keeps its own settings and indexes next door, in `~/.local/share/goldendict`. Keep the dictionaries out of that folder, so they don't mix with files the app manages.

The Wiktionary StarDict files are compressed with `zstd`, so install that first if it isn't there already:

```bash
sudo apt install zstd
```

Then download the four dictionaries, about 52 MB (75 MB once unpacked):

```bash
mkdir -p ~/.local/share/dictionaries
cd ~/.local/share/dictionaries

# en-en
file="English-English Wiktionary dictionary stardict.tar.gz"
wget -O "$file" "https://raw.githubusercontent.com/Vuizur/Wiktionary-Dictionaries/master/${file// /%20}"
tar -xzf "$file"
rm "$file"

# en-es, es-es and he-en (each unpacks into its own folder)
for name in en-es es-es he-en; do
    wget -O "$name.tar.zst" "https://github.com/xxyzz/wiktionary_stardict/releases/latest/download/$name.tar.zst"
    mkdir -p "$name"
    tar --zstd -xf "$name.tar.zst" -C "$name"
    rm "$name.tar.zst"
done
```

The Wiktionary StarDict project has files for many other language pairs, named `<word language>-<explanation language>`, such as `fr-fr` or `de-en`. See its release page: https://github.com/xxyzz/wiktionary_stardict/releases/latest

<details>
<summary>Already installed the older Spanish and Hebrew files from this guide?</summary>

An earlier version of this guide used 2022 files from Wiktionary-Dictionaries for Spanish and Hebrew too. Remove them after downloading the new ones, or every Spanish and Hebrew word shows up twice:

```bash
cd ~/.local/share/dictionaries
rm -r "Spanish-English Wiktionary dictionary stardict" "Hebrew-English Wiktionary dictionary stardict"
pkill -f goldendict-search-provider
```

Then, in GoldenDict-ng, open **Edit → Dictionaries** and click **Rescan now** on the **Sources → Files** tab.

</details>

### Step 2 (optional): Add the WordNet thesaurus

WordNet is a large English dictionary grouped by meaning, so it's good for synonyms. Ubuntu packages it for the `dictd` dictionary server, and GoldenDict-ng reads those files directly (I'm about 85% confident of that; if WordNet doesn't show up after step 3, skip it). Not for the Flatpak.

```bash
sudo apt install dict-wn dict-moby-thesaurus
```

`dict-moby-thesaurus` adds the Moby Thesaurus, a plain list of about 30,000 English words with their synonyms. Both install into `/usr/share/dictd`.

### Step 3: Point GoldenDict-ng at them

1. Open **GoldenDict-ng**.
2. Open the menu **Edit → Dictionaries** (or press `F3`).
3. On the **Sources → Files** tab, click **Add…**. The folder is hidden (its path starts with a dot), so type its path instead of clicking through: in GNOME's file picker, press `Ctrl+L`, type `~/.local/share/dictionaries` and press `Enter`.
4. Tick **Recursive** next to it, so the subfolders are read.
5. If you did step 2, check whether `/usr/share/dictd` is in the list. GoldenDict-ng adds it by itself the first time it starts, but only if the folder exists then, and in this guide it didn't yet. If it's missing, click **Add…** again and choose `/usr/share/dictd`.
6. Click **OK**. GoldenDict-ng indexes the dictionaries, which takes a few seconds the first time.

Type `casa` into GoldenDict-ng's search box to check: the `es-es` entry (*Edificación destinada a vivienda*) should appear.

### Step 4: Turn off the online sources

On first start, GoldenDict-ng switches on three online sources: **English Wikipedia**, **English Wiktionary** and the **dict.org** server. They need the internet, and when they answer first, a lookup opens a Wikipedia article instead of your dictionaries. To keep everything offline:

1. Open **Edit → Dictionaries** again (`F3`).
2. On the **Sources → Wikipedia** tab, untick **Enabled** for every row.
3. On the **Sources → DICT servers** tab, untick **Enabled** for **dict.org**.
4. Click **OK**.

Now a lookup only shows the dictionaries from steps 1 and 2.

---

## 3. Install the search provider

### Step 1: Get the files

The provider lives in this repository, in [`tools/goldendict-search/`](tools/goldendict-search/):

```bash
sudo apt install git
git clone https://github.com/Toldry/zenbook-duo-linux-guide.git ~/zenbook-duo-linux-guide
```

If you already cloned it for another tool from this guide, update it instead:

```bash
cd ~/zenbook-duo-linux-guide && git pull
```

### Step 2: Run the installer

```bash
~/zenbook-duo-linux-guide/tools/goldendict-search/install.sh
```

It asks for your password once. The installer:

1. Checks that GoldenDict-ng and Python's GNOME bindings (`python3-gi`, part of Ubuntu Desktop) are installed.
2. Stops an older copy of the provider if one is running, so running the installer again updates it.
3. Copies the provider to `~/.local/bin/goldendict-search-provider`.
4. Tells D-Bus how to start the provider when GNOME first needs it. D-Bus is the message bus desktop programs use to talk to each other.
5. Registers the provider with GNOME in `/usr/local/share/gnome-shell/search-providers/`. GNOME only looks in system folders for these, which is why it needs your password.
6. Makes GNOME reload its list of providers by switching **App Search** off and on again, so there is no need to log out.

---

## 4. Turn it on in Settings

1. Open **Settings → Search**. If Settings was already open, close and reopen it so it picks up the new provider.
2. Make sure **App Search** is on. With it off, no app gives results, this one included.
3. Under **Search Results**, find **GoldenDict-ng** and make sure its switch is on. New providers start switched on.
4. Optional: drag **GoldenDict-ng** by its handle (⋮⋮) higher or lower. The order here is the order of the groups in the overview. Put it at the top if you'll use it often, or at the bottom if you want it out of the way of file and app results.

```
Settings → Search
┌──────────────────────────────────────────────┐
│ App Search                            [ ON ] │
│ Search Locations                           › │
├──────────────────────────────────────────────┤
│ Search Results                               │
│ ⋮⋮  GoldenDict-ng                     [ ON ] │
│ ⋮⋮  Files                             [ ON ] │
│ ⋮⋮  Calculator                        [ ON ] │
│ ⋮⋮  Settings                          [ ON ] │
│ …                                            │
└──────────────────────────────────────────────┘
```

> **Ubuntu 26.04: a "Search online" result stays on top whatever the order.** Ubuntu 26.04 turns on its own extension, `web-search-provider@ubuntu.com`, which adds a *Search online* (Google) result under your default browser's name and icon, so it looks like a Firefox result. It isn't in the **Search Results** list, so dragging Firefox down doesn't move it. The extension adds itself to GNOME Shell directly, and every time GNOME reloads the listed providers (after an update, or when you change the order) they are placed after it, so it ends up first. Checked in October 2026 on GNOME 50.1 by reading the extension's `extension.js` and GNOME Shell's `search.js`. The simplest fix is to turn the extension off; it takes effect at once and lasts across reboots:
>
> ```bash
> gnome-extensions disable web-search-provider@ubuntu.com
> ```
>
> You lose only the *Search online* result. Turn it back on with `gnome-extensions enable web-search-provider@ubuntu.com`, or use the **Extensions** app.

---

## 5. Try it

1. Press `Super` and type `hola`.
2. Under the app matches, a **GoldenDict-ng** group shows **hola** twice: *intj: (informal) Hello, hi, hey.* (from `en-en`, so without a label) and *es-es · Interjección: Expresión de saludo utilizada entre dos o más personas…*. Often that's all you need.
3. For the full entry, press `↓` until a row is highlighted and press `Enter`, or click it.

GoldenDict-ng opens with the entries for *hola*. If it was already open, it shows the new word in the same window.

Tips:

- **`Enter` alone runs the first result.** That's a GoldenDict-ng row only when no app or setting matches what you typed. If `Enter` opened an app instead, use `↓` first.
- **Phrases work** if the dictionary has them: `dar a luz` finds *to give birth*.
- **Clicking the GoldenDict-ng icon** at the left of the group looks up exactly what you typed, even if it isn't in the results.

---

## Optional: only search with a prefix

By default the GoldenDict-ng group appears for every search that matches a word, and most app names are words too (`files`, `calculator`). If that's too much clutter, make it appear only when your query starts with a prefix, such as `d `:

1. Open `~/.local/bin/goldendict-search-provider` in a text editor.
2. Change the line `QUERY_PREFIX = ""` to `QUERY_PREFIX = "d "`.
3. Stop the running copy so GNOME starts the edited one at the next search:

   ```bash
   pkill -f goldendict-search-provider
   ```

Now `Super`, `d hola` looks up *hola*, and plain `hola` doesn't show the group. Running the installer again puts back the default, so redo the edit after updating.

---

## How it works

GNOME's overview asks every search provider for results over D-Bus, using the `org.gnome.Shell.SearchProvider2` interface. The provider is a Python script that answers five questions:

| GNOME asks | The provider answers |
|---|---|
| `GetInitialResultSet` (you started typing) | Up to 5 matching words, or nothing if none match or the query lacks the prefix |
| `GetSubsearchResultSet` (you typed more) | The same, for the longer query |
| `GetResultMetas` (what to show) | Each word, the dictionary's name and the start of the definition, and GoldenDict-ng's icon |
| `ActivateResult` (you chose a row) | Runs `goldendict -- <word>` (or `flatpak run … -- <word>`) |
| `LaunchSearch` (you clicked the group's icon) | The same, with exactly what you typed |

**Reading the dictionaries.** The provider reads StarDict dictionaries (`.ifo` files) in `~/.local/share/dictionaries` and `/usr/share/stardict/dic`, with their subfolders, using only Python's standard library. A StarDict dictionary is three or four files:

| File | Contents | How the provider uses it |
|---|---|---|
| `.ifo` | Name and format | Gives the label, such as `es-es`: the file's name if it's a language pair, else a pair in the dictionary's name, else the whole name |
| `.idx` | Every headword, sorted, with where its article is | Finds the word by binary search |
| `.syn` | Other forms (`hablo`, `ran`) and which headword they belong to | Finds inflected forms |
| `.dict.dz` | The articles, compressed in small independent chunks ("dictzip") | Unpacks only the chunk with the article |

At start it notes where each word begins in the `.idx` and `.syn` files, and lists the words of every multi-word headword, without accents, in a small index (about 15,000 phrases). That takes about half a second for the four dictionaries. After that, each search takes under 1 millisecond.

To make accents optional for single words, the provider also tries each spelling of what you typed with one accent added (`reaccion` → `réaccion`, `reáccion`, … `reacción`, `reaccíon`, …), and keeps the ones that exist. Spanish writes at most one accent per word, apart from `ñ` and `ü`, so this finds almost every word without a bigger index. The Hebrew dictionary's headwords have vowel points, and it lists the unpointed spellings as other forms, so `שלום` finds `שָׁלוֹם`. The files are memory-mapped rather than read in, so they cost little memory.

The article is HTML. The provider turns it into one line: the part of speech, then the senses, separated by `·`, and further parts of speech after a `|`. It leaves out pronunciations, inflection tables, examples and synonym lists. It knows the layouts of both projects' files; for any other dictionary it shows the start of the article's text.

The results come from the dictionaries in the order of their folder names. To put, say, Spanish before English, rename the folders so they sort that way (for example `1-es-es`).

**Opening GoldenDict-ng.** GoldenDict-ng only allows one copy of itself to run. When it's already open, a second `goldendict <word>` hands the word to the open window and exits. The `--` makes sure a word such as `-ing` is looked up, not read as an option. For an inflected form, the provider opens the headword (`hablar`, not `hablo`).

The provider doesn't run all the time. D-Bus starts it the first time you type in the overview after logging in, and it quits after 10 minutes without a search. Dictionaries you add are picked up the next time it starts; to pick them up now, run `pkill -f goldendict-search-provider`.

Files it uses:

| Path | Contents |
|---|---|
| `~/.local/bin/goldendict-search-provider` | The provider |
| `~/.local/share/dbus-1/services/io.github.toldry.GoldenDictSearch.service` | Tells D-Bus how to start the provider |
| `/usr/local/share/gnome-shell/search-providers/goldendict-search-provider.ini` | Tells GNOME the provider exists and that it belongs to GoldenDict-ng |
| `~/.local/share/dictionaries/` | The Wiktionary dictionaries |

---

## Limitations

- **One line of definition.** The overview has room for a title and one line, so long entries are cut off. Open the word in GoldenDict-ng for the rest.
- **StarDict only.** The overview only searches StarDict dictionaries in the two folders above. Dictionaries in other formats, such as WordNet's `dictd` files from step 2.2, still work in GoldenDict-ng but don't appear in the overview.
- **One missing accent at most.** Typing without accents finds words with one accent, `ñ` or `ü`, which covers nearly all Spanish words. A word with two (rare) needs at least one of them typed. For multi-word entries, all accents and Hebrew vowel points are ignored.
- **The English dictionary has no multi-word entries**, so phrases only come from `en-es`, `es-es` and `he-en`.
- **No spelling suggestions.** A misspelled word finds nothing in the overview. Click the GoldenDict-ng icon instead to look up exactly what you typed; GoldenDict-ng suggests close matches.
- **The window may not come to the front.** If GoldenDict-ng is already open behind other windows, GNOME sometimes shows a *"GoldenDict-ng is ready"* notification instead of raising it. This is GNOME's protection against apps stealing focus. I'm not sure how often it happens with GoldenDict-ng; closing GoldenDict-ng after each lookup avoids it.
- **The registration is for all users, the provider for one.** Other accounts on the laptop see GoldenDict-ng under **Search Results**, but it gives them no results until they run the installer too.
- **No Hebrew-Hebrew dictionary** (see [step 2](#2-add-dictionaries)). Hebrew words are explained in English.
- **The English file is from 2022.** The Spanish and Hebrew files are from September 2026, and new ones come out every few months; download them again to update.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| The installer says *"GoldenDict-ng isn't installed"* | Step 1 skipped, or only the old `goldendict` package installed | `sudo apt install goldendict-ng` |
| **GoldenDict-ng** isn't listed under **Search Results** | Settings was open during the install, or the `.ini` file is missing | Close and reopen Settings. Check with `ls /usr/local/share/gnome-shell/search-providers/` |
| It's listed, but no GoldenDict-ng results appear in the overview | GNOME hasn't reloaded its providers | In **Settings → Search**, switch **App Search** off and on again. If that doesn't help, log out and back in |
| Still no results | No dictionaries in `~/.local/share/dictionaries`, or the provider fails to start | Check with `ls ~/.local/share/dictionaries/*/*.ifo`. Then run `pkill -f goldendict-search-provider; ~/.local/bin/goldendict-search-provider` in a terminal, search in the overview, and read the errors. Also check `journalctl --user -b \| grep -i goldendict` |
| Results show only *Look up in GoldenDict-ng*, no definitions | The older version of the provider is installed | Update and rerun the installer: `cd ~/zenbook-duo-linux-guide && git pull && tools/goldendict-search/install.sh` |
| Choosing a result does nothing | GoldenDict-ng can't be started | Run `goldendict hola` in a terminal and read the error |
| Choosing a result opens a Wikipedia article | GoldenDict-ng's online sources are on, and your dictionaries may not be loaded | Do [step 2.4](#step-4-turn-off-the-online-sources), then check [step 2.3](#step-3-point-goldendict-ng-at-them) |
| GoldenDict-ng opens but finds nothing | No dictionaries loaded | Redo [step 2.3](#step-3-point-goldendict-ng-at-them); check that **Recursive** is ticked |
| A *Search online* result (with the Firefox icon) appears above GoldenDict-ng, even though Firefox is lower in **Settings → Search** | Ubuntu 26.04's web search extension ignores the list order | `gnome-extensions disable web-search-provider@ubuntu.com`. See the note in [step 4](#4-turn-it-on-in-settings) |
| WordNet doesn't appear in GoldenDict-ng | Its `dictd` files weren't recognized | Remove `/usr/share/dictd` from the sources; the Wiktionary English dictionary covers synonyms too |

---

## How to undo it

```bash
~/zenbook-duo-linux-guide/tools/goldendict-search/uninstall.sh
```

This removes the provider and its two config files and asks for your password once. GoldenDict-ng and the dictionaries stay.

To do the same by hand:

```bash
pkill -f goldendict-search-provider
rm ~/.local/bin/goldendict-search-provider
rm ~/.local/share/dbus-1/services/io.github.toldry.GoldenDictSearch.service
sudo rm /usr/local/share/gnome-shell/search-providers/goldendict-search-provider.ini
```

Then switch **App Search** off and on in **Settings → Search**.

To also remove GoldenDict-ng and the dictionaries:

```bash
sudo apt remove goldendict-ng dict-wn dict-moby-thesaurus
rm -r ~/.local/share/dictionaries
```

---

## Sources

- GoldenDict-ng, its install options and Ubuntu package name: https://github.com/xiaoyifang/goldendict-ng and https://xiaoyifang.github.io/goldendict-ng/install/
- GoldenDict-ng's command line (a word as argument, handed to a running window): https://github.com/xiaoyifang/goldendict-ng/blob/staged/src/main.cc
- GoldenDict-ng on Flathub: https://flathub.org/apps/io.github.xiaoyifang.goldendict_ng
- Ubuntu 24.04's `goldendict-ng` package and its files: https://packages.ubuntu.com/noble/goldendict-ng
- Wiktionary dictionaries in StarDict format (English): https://github.com/Vuizur/Wiktionary-Dictionaries
- Wiktionary dictionaries in StarDict format (`en-es`, `es-es`, `he-en` and many more pairs): https://github.com/xxyzz/wiktionary_stardict and https://xxyzz.github.io/wiktionary_stardict/
- The tool both projects build on, and the Wiktionary editions it can read (no Hebrew one): https://github.com/tatuylonen/wiktextract
- The Wiktionary data they're built from: https://kaikki.org/
- The Hebrew Wiktionary: https://he.wiktionary.org/
- Where Linux keeps a user's data files (`~/.local/share`): https://specifications.freedesktop.org/basedir-spec/latest/
- GoldenDict-ng's own folder and the system dictionary folders it adds on first start: https://github.com/xiaoyifang/goldendict-ng/blob/staged/src/config.cc
- Flatpak's `xdg-data/…` folder permission: https://docs.flatpak.org/en/latest/sandbox-permissions.html
- WordNet: https://wordnet.princeton.edu/ and the Ubuntu package https://packages.ubuntu.com/noble/dict-wn
- Writing a GNOME search provider: https://developer.gnome.org/documentation/tutorials/search-provider.html
- GoldenDict-ng's default online sources (Wikipedia, Wiktionary, dict.org): https://github.com/xiaoyifang/goldendict-ng/blob/staged/src/config.cc
- The StarDict file formats (`.ifo`, `.idx`, `.syn`, `.dict`): https://github.com/huzheng001/stardict-3/blob/master/dict/doc/StarDictFileFormat
- The dictzip format: https://manpages.ubuntu.com/manpages/noble/man1/dictzip.1.html
- How GNOME Shell finds search providers (system data folders only, `DesktopId`, `Version`): https://gitlab.gnome.org/GNOME/gnome-shell/-/blob/gnome-46/js/ui/remoteSearch.js
- GNOME Shell reloading providers when the search settings change: https://gitlab.gnome.org/GNOME/gnome-shell/-/blob/gnome-46/js/ui/search.js
- The **App Search** and **Search Results** settings: https://gitlab.gnome.org/GNOME/gnome-control-center/-/blob/gnome-46/panels/search/cc-search-panel.ui
- Ubuntu 26.04's web search and Snap search extensions: https://www.omgubuntu.co.uk/2026/03/ubuntu-2604-gnome-search-extensions
- Where Ubuntu develops those extensions: https://gitlab.gnome.org/Community/Ubuntu
- GNOME Shell sorting only the D-Bus search providers by `sort-order`: https://gitlab.gnome.org/GNOME/gnome-shell/-/blob/main/js/ui/remoteSearch.js
- D-Bus service activation files: https://dbus.freedesktop.org/doc/dbus-specification.html#message-bus-starting-services
