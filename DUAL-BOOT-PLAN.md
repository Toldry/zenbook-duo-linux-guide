# Plan: Ubuntu as the Main OS, Dual-Booted on the Internal Disk

A step-by-step plan for moving from "Ubuntu on an external USB drive" ([GUIDE.md](GUIDE.md)) to Ubuntu on the laptop's internal SSD, next to a Windows that's only kept for firmware and Windows updates.

> **Status:** plan, not yet carried out. Each phase ends with a checkpoint, and nothing irreversible happens before [Phase 2](#phase-2-prepare-windows).

---

## Contents

- [The situation this plan is for](#the-situation-this-plan-is-for)
- [Goals and how each one is met](#goals-and-how-each-one-is-met)
- [Target layout](#target-layout)
- [Key decisions, and why](#key-decisions-and-why)
- [Phase 1: Test, without touching the internal disk](#phase-1-test-without-touching-the-internal-disk)
- [Phase 2: Prepare Windows](#phase-2-prepare-windows)
- [Phase 3: Install Ubuntu on the internal disk](#phase-3-install-ubuntu-on-the-internal-disk)
- [Phase 4: Move in](#phase-4-move-in)
- [Everyday rules after the move](#everyday-rules-after-the-move)
- [How to undo it](#how-to-undo-it)
- [Open questions and uncertain points](#open-questions-and-uncertain-points)
- [Glossary](#glossary)

---

## The situation this plan is for

- **Laptop:** ASUS Zenbook Duo UX8406MA, ~1 TB internal NVMe SSD, Windows 11 **Home**.
- **Windows disk (`C:`):** 952 GB. Example starting point: 806 GB used, much of it deletable.
- **Windows encryption:** `manage-bde -status C:` shows *Used Space Only Encrypted*, *Protection Off*, *Key Protectors: None Found*. The disk is encrypted, but the key is stored unprotected on the disk itself. This is Windows 11 Home's *Device Encryption* that was never activated, because activating it needs a Microsoft-account sign-in. **It gives no protection against theft.**
- **No Microsoft account**, and none planned. So BitLocker can't be properly activated on Home.
- **The laptop leaves the house** and holds files that nobody else should see.
- **Those files are also synced with Google Drive**, and are used on an Android phone.

## Goals and how each one is met

| Goal | Solution |
|---|---|
| A thief can't read the files | Ubuntu on an **encrypted (LUKS)** partition. Windows keeps **no sensitive files at all** |
| Google can't read the sensitive files | Keep them in a **Cryptomator vault** inside Google Drive (encrypted on your devices before upload) |
| The sensitive files still work on Android | Cryptomator's **Android app** opens the same vault straight from Google Drive |
| Files are available in both Windows and Ubuntu | **Google Drive is the bridge.** Ubuntu can also read the (decrypted) `C:` directly |
| Windows stays usable for updates | Windows keeps its own ~150 GB partition and boots from the GRUB menu or `Esc` |

```
                     ┌──────────────── Google Drive ────────────────┐
                     │  normal files      │  sensitive files         │
                     │  (Google can read) │  in a Cryptomator vault  │
                     │                    │  (Google sees noise)     │
                     └───────▲────────────┴─────────▲────────────────┘
                             │ sync                  │ sync
        ┌────────────────────┴───────┐      ┌────────┴──────────┐
        │ Laptop                      │      │ Android           │
        │  Ubuntu  ── LUKS encrypted  │      │ Cryptomator app   │
        │  Windows ── no sensitive    │      │ + Google Drive    │
        │             data at all     │      └───────────────────┘
        └─────────────────────────────┘
```

## Target layout

```
Before:  [ESP][MSR][              C: Windows (952 GB)               ][Recovery]
After:   [ESP][MSR][ C: Windows ~150 GB ][ Ubuntu, LUKS, ~800 GB     ][Recovery]
           ▲          no sensitive data     all personal data lives here
           └─ shared: Windows Boot Manager + Ubuntu's shim/GRUB (~20 MB)
```

| Partition | Size | Notes |
|---|---|---|
| EFI System Partition (ESP) | unchanged (~260 MB) | Shared by both systems. Never format it |
| MSR | unchanged (16 MB) | Windows housekeeping |
| `C:` Windows | **~150 GB** | ~40 GB for Windows itself, ~30 GB kept free for feature updates, the rest for programs. Less space than this is what makes updates fail |
| Ubuntu (LUKS → ext4 `/`) | everything else | Ubuntu makes a swap *file*; no swap partition needed |
| Recovery (and any MYASUS partition) | unchanged | **Don't touch.** Factory reset needs them |

No shared data partition: Google Drive moves files between the systems, and Windows hardly needs them anyway.

## Key decisions, and why

**Decrypt `C:` instead of trying to protect it.**
Without a Microsoft account, Windows Home can't turn on real protection (see [open questions](#open-questions-and-uncertain-points)). The current "encrypted but unprotected" state protects nothing, makes resizing harder, and stops Ubuntu from reading `C:`. Once no sensitive files are on `C:`, decrypting costs nothing.

**Cryptomator, not a single VeraCrypt container, for the cloud.**
A VeraCrypt container is one big file. Every change re-uploads the whole thing, and editing it on two devices at once can create a "conflicted copy" that breaks the whole container. VeraCrypt also has no proper Android app. Cryptomator encrypts **each file separately** (names included), so only changed files sync. It has apps for Windows, Linux, Android and iOS, and it's open source. The trade-off: inside the vault, Google can't search, preview or share. So put **only the sensitive files** in the vault.

**A Google Drive sync tool on Linux.**
Google makes no Drive desktop app for Linux. Options:

| Tool | What it is | Notes |
|---|---|---|
| **rclone** `bisync` | Free command-line sync tool | Reliable and flexible; needs a one-time setup and a timer. Native Google Docs/Sheets are exported or skipped, not synced as-is |
| **Insync** | Paid app (one-time licence) | Closest to the Windows Drive app |
| GNOME **Online Accounts** | Built into Ubuntu | Browse-only, no offline copies. Fine for occasional access |

Step-by-step setup for each: [CLOUD-STORAGE.md](CLOUD-STORAGE.md).

**Ubuntu's encryption protects only while the laptop is off.** While asleep, the disk is unlocked in memory. When travelling, shut down.

---

## Phase 1: Test, without touching the internal disk

Goal: prove that daily life on Ubuntu works, and that the installer can do what Phase 3 needs. **Nothing here changes the internal disk.**

1. **Install Ubuntu on an external SSD** ([GUIDE.md](GUIDE.md), Part B) and use it as your main system for a few weeks.
2. **Set up Google Drive sync** on it (rclone or Insync, see above). Check that offline access, sync speed and conflicts behave the way you need.
3. **Set up Cryptomator:**
   - Ubuntu: install it from Flathub or as an AppImage from <https://cryptomator.org>.
   - Create a vault **inside the synced Google Drive folder**, with a strong password. Write down the recovery key it offers, the same way as the BitLocker key in the guide.
   - Move a few test files in, and let them sync.
   - Android: install Cryptomator (a paid app), add the vault from Google Drive, and open the test files.
4. **Check the installer's encryption options.** Boot the installer stick (live session), start **Install Ubuntu**, and click through to *"How do you want to install Ubuntu?"*. Check whether **Install alongside Windows** offers **encryption** (look under *Advanced features*). Then **quit without installing.**
   - Encryption offered → Phase 3 uses that path.
   - Not offered → see [open questions](#open-questions-and-uncertain-points) before going further.
5. **List what Windows is still needed for:** firmware updates (MyASUS), and anything else that has no Linux equivalent.

✅ **Checkpoint:** Ubuntu is good enough as a daily system, the vault works on laptop and phone, and the installer can encrypt next to Windows.

## Phase 2: Prepare Windows

> ⚠️ **From here on, steps change the internal disk.** Do them in order.

1. **Clean up `C:`.** Delete what you don't need. **Settings → System → Storage** shows what's big. Aim for well under ~110 GB used, so `C:` fits in ~150 GB with room for updates.
2. **Make a full backup** to an external drive: everything not already in Google Drive, plus a copy of what is. Don't rely on the cloud as your only copy.
3. **Move sensitive files off `C:`:**
   - Into the Cryptomator vault, if they're needed on the phone or in the cloud.
   - Onto the external SSD's Ubuntu, if they're laptop-only.
   - In **Google Drive for desktop** on Windows, stop syncing folders that hold sensitive files, or sign out of it completely.
4. **Decrypt `C:`** (admin terminal):
   ```powershell
   manage-bde -off C:
   manage-bde -status C:      # repeat until "Conversion Status: Fully Decrypted"
   ```
   It runs in the background and survives restarts. Expect around 30 minutes to a few hours, depending on how much data is left.
5. **Erase deleted data from the SSD's free space:**
   ```powershell
   defrag C: /L
   ```
   `/L` tells the SSD which blocks are no longer in use (TRIM), so it can erase them. Deleted files become much harder to recover.
6. **Shrink `C:`:** right-click Start → **Disk Management** → right-click `C:` → **Shrink Volume**, and shrink it to ~150 GB.
   - If Windows offers much less than expected, some system files sit near the end of the partition. Temporarily turn off **System Restore** (System Properties → System Protection → Configure → Disable) and the **page file** (System Properties → Advanced → Performance → Virtual memory → No paging file). Restart, shrink, then turn both back on.
   - **Leave the new space unallocated.** Don't create a partition there; the Ubuntu installer will.
7. **Check that Fast Startup is still off** ([GUIDE.md](GUIDE.md), step 2.2).

✅ **Checkpoint:** `C:` is decrypted, ~150 GB, holds no sensitive files, and there's ~800 GB of unallocated space after it.

## Phase 3: Install Ubuntu on the internal disk

1. **Dock the keyboard** and plug in the charger. Boot the installer stick: **Shut Down**, power on, tap `Esc`.
2. In the installer, choose **Install Ubuntu alongside Windows** with **encryption** (as checked in Phase 1, step 4).
   - It should use the **unallocated space** and the **existing ESP**.
   - On the summary screen: nothing from Windows (`C:`, Recovery) may be marked *formatted*. Only the new Ubuntu partition, and the ESP marked *used*, not formatted.
3. Choose a strong **encryption passphrase**. Write it down where your BitLocker key would have gone.
4. Finish, reboot, and run [GUIDE.md](GUIDE.md) steps 8.2–8.5: updates, the add-on, Wayland. Also do the battery limit from section 9.
5. **Check the boot menu.** GRUB should list *Windows Boot Manager*. If it doesn't:
   ```bash
   echo 'GRUB_DISABLE_OS_PROBER=false' | sudo tee -a /etc/default/grub
   sudo update-grub
   ```
6. **Fix the clock.** Windows keeps local time in the hardware clock, Ubuntu keeps UTC, so the time is off by hours after switching. Make Windows use UTC (admin terminal in Windows):
   ```powershell
   reg add "HKLM\SYSTEM\CurrentControlSet\Control\TimeZoneInformation" /v RealTimeIsUniversal /t REG_DWORD /d 1 /f
   ```
7. **Boot order:** Ubuntu (GRUB) first. Check it with `F2` → **Boot** if needed.

> 🔑 **Keep the keyboard docked when typing the encryption passphrase.** The passphrase is asked before Ubuntu starts, and Bluetooth doesn't exist yet at that point.

✅ **Checkpoint:** both systems boot, the passphrase prompt appears for Ubuntu, Windows starts from the GRUB menu, and the clock is right in both.

## Phase 4: Move in

1. **Copy your data** from the external SSD's Ubuntu to the internal one. Simplest: plug in the external SSD and copy your home folder's files with the file manager. Or, from a terminal (adjust the path):
   ```bash
   rsync -aH --info=progress2 /media/$USER/<external-root>/home/<name>/ ~/
   ```
   Re-install apps rather than copying them.
2. **Set up Google Drive sync and Cryptomator again** on the internal Ubuntu, the same way as in Phase 1.
3. **Use it for a week before wiping the external SSD.** Then either wipe it, or keep it as a backup drive (Déjà Dup can back up to it).

✅ **Done.**

## Everyday rules after the move

- **Windows → Ubuntu: always Shut Down, never Restart.** Otherwise the speaker amplifiers may not start ([GUIDE.md](GUIDE.md), 4.1).
- **Shut down rather than sleep when travelling.** Encryption only protects a laptop that's off.
- **Boot Windows every month or two** for MyASUS firmware updates and Windows Update. Allow an hour.
- **Keep Ubuntu updated.** A Windows Secure Boot update can block an outdated Ubuntu boot loader; an up-to-date one is fine. Keep the installer stick for repairs.
- **If a Windows update puts Windows first in the boot order:** `F2` → **Boot** → move Ubuntu back to the top. It's annoying, not dangerous.
- **Protect your Google account** with two-factor authentication, and the **phone** with a screen lock. Cryptomator protects the vault from Google, not from someone holding your unlocked phone.
- **Don't open sensitive files on Windows,** even from the vault. Apps can leave unencrypted temporary copies on the unencrypted `C:`.

## How to undo it

1. **Back up** Ubuntu's data first. It's encrypted, so Windows can't read it.
2. In Windows: **Disk Management** → delete the Ubuntu partition (**only** that one; check its size) → right-click `C:` → **Extend Volume**.
3. Remove Ubuntu's boot entry: `F2` → **Boot** → put *Windows Boot Manager* first. Its files on the ESP (`\EFI\ubuntu`, about 20 MB) are harmless to leave. If you want them removed, ask for help instead of deleting EFI files by hand.

## Open questions and uncertain points

| Point | Confidence | What to do |
|---|---|---|
| The 24.04 installer offers encryption with *Install alongside Windows* | ~60% | Check in Phase 1, step 4. If not: the newer **Ubuntu 26.04 LTS** installer may (released April 2026, ~85% sure), but the Duo add-on is tested on 24.04. Or set up LUKS by hand from a terminal before installing; that's an advanced procedure, so get help |
| Windows Home can activate BitLocker with `manage-bde` without a Microsoft account | ~50% | Not needed by this plan, since `C:` holds no sensitive data |
| `defrag C: /L` (TRIM) makes deleted files unrecoverable on this SSD | ~70% | Good enough against a thief; not a forensic-grade wipe |
| Cryptomator Android is a one-time purchase of ~€15–20 | ~70% | Check the Play Store |
| GRUB lists Windows without changing settings | unknown | Phase 3, step 5 covers the fix |

## Glossary

- **UEFI** (often still called "BIOS"): the firmware built into the laptop that runs before any operating system. `F2` opens its settings, and `Esc` its boot menu.
- **ESP** (EFI System Partition): a small FAT32 partition where each OS keeps its boot loader. Windows and Ubuntu share it.
- **GRUB**: Ubuntu's boot loader, which shows the menu for picking Ubuntu or Windows. **shim** is the small Microsoft-signed program that lets GRUB start with Secure Boot on.
- **LUKS**: Linux's standard disk encryption. You type its passphrase before Ubuntu starts.
- **TRIM**: a command that tells the SSD which blocks are free, so it can erase them.
- **Cryptomator vault**: a folder whose files are encrypted one by one, made to live inside a cloud-synced folder.
