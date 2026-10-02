# Running Linux from a USB Drive on the ASUS Zenbook Duo

A step-by-step guide to running Ubuntu from an external USB drive while Windows stays untouched on the laptop's internal disk.

> **Who this is for:** beginners who want to try Linux on the Zenbook Duo (UX8406MA 2024, or UX8406CA 2025) without risking their Windows installation.
>
> **Time needed:** about 1 hour for the live test (Part A), plus about 1–2 hours for the full install (Part B).

---

## Table of contents

0. [Understand the plan](#0-understand-the-plan)
1. [What you need](#1-what-you-need)
2. [Prepare Windows (do not skip)](#2-prepare-windows-do-not-skip)
3. [Create the Ubuntu installer USB](#3-create-the-ubuntu-installer-usb)
4. [Part A: Boot the live session and test the hardware](#4-part-a-boot-the-live-session-and-test-the-hardware)
5. [Decision point](#5-decision-point)
6. [Part B: Install Ubuntu onto the external USB drive](#6-part-b-install-ubuntu-onto-the-external-usb-drive)
7. [Make sure Windows was not touched](#7-make-sure-windows-was-not-touched)
8. [First boot: set up Ubuntu for the Duo](#8-first-boot-set-up-ubuntu-for-the-duo)
9. [Everyday use: switching between Windows and Linux](#9-everyday-use-switching-between-windows-and-linux)
10. [Troubleshooting](#10-troubleshooting)
11. [How to undo everything](#11-how-to-undo-everything)
12. [Sources](#12-sources)

---

## 0. Understand the plan

"Booting from USB" can mean three different things:

| Option | What it is | Saves your changes? | Touches the internal disk? |
|---|---|---|---|
| **Live session** | Ubuntu runs straight from the installer stick | No, everything resets when you shut down | No |
| **Live + persistence** | A live stick with an extra area where changes are saved | Partly; can be fragile | No |
| **Full install on USB** ← *this guide's goal* | A real Ubuntu installation that lives on an external drive | Yes, it's a normal OS | **No, if you follow Step 6 carefully** |

This is what the result looks like:

```
 ┌────────────────────────────┐        ┌────────────────────────────┐
 │ Internal SSD (unchanged)   │        │ External USB drive (new)   │
 │  ├─ EFI partition          │        │  ├─ EFI partition (own)    │
 │  │   └─ Windows Boot Mgr   │        │  │   └─ GRUB (Ubuntu)      │
 │  └─ C:  Windows            │        │  └─ Ubuntu system + files  │
 └────────────────────────────┘        └────────────────────────────┘
        ▲                                         ▲
        │  USB unplugged → laptop boots Windows   │
        └──────────  USB plugged in + boot menu → Ubuntu
```

**The "dual-boot" switch is physical:** USB plugged in and picked from the boot menu means Ubuntu. Anything else means Windows, exactly as before.

> ### 🧪 Doing a quick feasibility test with one small stick (e.g. 16 GB USB-A)?
>
> **Do Part A only (Steps 1–5), then stop.** That's all a feasibility test needs, and it's the zero-risk path:
>
> - A 16 GB stick is plenty for the **live session** (the Ubuntu ISO is about 6 GB). Any port works, including the Duo's USB-A port.
> - A **full install (Part B) isn't possible** with this setup. The installer stick can't install onto itself, so you'd need a *second* drive. Ubuntu 24.04's installer also needs about **25 GB or more** of space, and 64 GB or more is more realistic for actual use.
> - The live session runs in RAM, so a slow flash drive mostly affects startup time, not how well the hardware works. Your test results will reflect the laptop, not the stick.
> - Expect the first boot to take 1–3 minutes, and opening apps to feel sluggish. That's the stick, not Linux.
>
> If Part A looks promising, come back to Part B with a proper target drive.

You'll do it in two parts:

- **Part A (Steps 1–5):** start Ubuntu as a live session and check that the Duo's hardware works. Nothing is installed, and nothing is changed.
- **Part B (Steps 6–8):** if Part A looks good, install Ubuntu properly onto a **second** USB drive.

---

## 1. What you need

### Hardware

| Item | Purpose | Recommendation |
|---|---|---|
| **USB stick #1: installer** | Holds the Ubuntu installer. It gets erased. | 8 GB or larger, USB 3.0+ |
| **USB drive #2: target** (Part B only) | Where Ubuntu gets installed. It gets erased. | **External SSD in a USB-C enclosure, 128 GB or larger.** A fast USB 3.2 flash drive (e.g. Samsung BAR Plus / FIT Plus, SanDisk Extreme Pro) also works. Avoid cheap flash drives: an OS on one is painfully slow and wears the drive out. |
| **USB-C ↔ USB-A adapter** (maybe) | The Duo has 2× USB-C (Thunderbolt) + 1× USB-A | Only if your drives don't match the ports |
| **Power adapter** | Installs shouldn't run on battery | Keep it plugged in the whole time |
| **Your phone / paper** | To store the BitLocker recovery key | — |

> ⚠️ **Back up both USB drives first.** Everything on them will be erased.

### Know your model

In Windows, press `Win + R`, type `msinfo32`, and press Enter. Look at **System Model**:

- `UX8406MA` = 2024 model (Intel Core Ultra "Meteor Lake"): the best-tested model on Linux.
- `UX8406CA` = 2025 model (Intel Core Ultra "Arrow Lake"): works, but less tested.

Write it down. Some add-on projects are model-specific.

### Duo-specific rule: keep the keyboard docked during boot

The Bluetooth connection only exists once an operating system is running. In the UEFI settings, the boot menu, and the first seconds of startup, **the keyboard only works when it's lying on the lower screen** (connected through the metal contacts). So keep it docked for Steps 4, 6, and 9. If the keyboard doesn't respond, you can also use the touchscreen in the Ubuntu installer.

---

## 2. Prepare Windows (do not skip)

None of these steps change your files, but they protect you if something goes wrong.

### 2.1 Save your BitLocker recovery key

Your Windows drive is probably encrypted. Changes to the startup process can make Windows ask for a 48-digit recovery key. **Without that key, your Windows data is gone for good.**

1. Right-click the Start button → **Terminal (Admin)** (or **Windows PowerShell (Admin)**).
2. Check whether BitLocker is on:
   ```powershell
   manage-bde -status C:
   ```
   Look at **Protection Status**. If it says *Protection On* (or *Device Encryption* is on), continue to step 3.
3. Show the key:
   ```powershell
   manage-bde -protectors -get C:
   ```
4. Find the **Numerical Password** section. Its **Password** is a 48-digit number in 8 groups.
5. **Save it outside the laptop:** take a photo with your phone, write it on paper, or both.
6. Check that it's also stored in your Microsoft account: on your phone, open <https://aka.ms/myrecoverykey> and sign in. You should see a key whose ID matches the one shown in step 3.

✅ **Checkpoint:** you can read the 48-digit key **without using this laptop.**

### 2.2 Turn off Fast Startup

Fast Startup doesn't fully shut Windows down. That can leave the speaker amplifier in a bad state, so Linux sounds harsh or distorted. In the same admin terminal, run:

```powershell
powercfg /h off
```

(This also turns off hibernation. Sleep still works normally.)

### 2.3 Update the firmware (recommended)

Open the **MyASUS** app → **Customer Support** → **Live Update**, and install any BIOS or firmware updates. Newer firmware often fixes hardware problems that affect Linux too. Do this *before* you start, not halfway through.

### 2.4 Back up anything important

Do this even though Windows isn't supposed to be touched. OneDrive, an external drive, anything works.

---

## 3. Create the Ubuntu installer USB

### 3.1 Download Ubuntu

Go to <https://ubuntu.com/download/desktop> and download **Ubuntu 24.04 LTS** (the newest 24.04.x point release, e.g. 24.04.4).

> **Why 24.04, not a newer version?** The main Duo add-on ([JowiAoun/linux-on-zenbook-duo](https://github.com/JowiAoun/linux-on-zenbook-duo)) is tested on **Ubuntu 24.04.4 with GNOME on Wayland**. Recent 24.04.x releases also ship kernel **6.11 or newer**, which fixes Wi-Fi switching off when you lift the keyboard. On a 2025 model (UX8406CA), a newer Ubuntu (25.10 / 26.04) is also fine. The [Fmstrat](https://github.com/Fmstrat/zenbook-duo-linux) add-on has been confirmed on 25.10.

The file is about 6 GB and ends in `.iso`.

### 3.2 Check that the download isn't corrupted (optional, recommended)

1. On the download page (or at <https://releases.ubuntu.com/24.04/>), open the **SHA256SUMS** file and find the line for your `.iso`.
2. In PowerShell, run:
   ```powershell
   Get-FileHash "$env:USERPROFILE\Downloads\ubuntu-24.04.4-desktop-amd64.iso" -Algorithm SHA256
   ```
   (Adjust the filename to match yours.)
3. The long hex string must match the one in SHA256SUMS exactly. If it doesn't, download the file again.

### 3.3 Write the ISO to USB stick #1 with Rufus

1. Download **Rufus** from <https://rufus.ie> (the portable version is fine).
2. Plug in **USB stick #1** and **only** that drive. Unplug other USB drives so you can't pick the wrong one.
3. Open Rufus and set:
   - **Device:** your USB stick (check the size!)
   - **Boot selection:** click **SELECT** and choose the Ubuntu `.iso`
   - **Partition scheme:** `GPT`
   - **Target system:** `UEFI (non CSM)`
   - Leave the rest at the defaults
4. Click **START**.
   - If Rufus offers to download extra files (e.g. a newer GRUB/Syslinux), click **Yes**.
   - When asked about the write mode, pick **ISO Image mode (Recommended)**. If the stick later won't boot, redo it with **DD Image mode**.
5. Confirm the warning that the stick will be erased, and wait for **READY**.

> Alternatives: **balenaEtcher** (simpler, fewer options) or **Ventoy** (lets you keep several ISOs on one stick). Rufus is the most predictable.

---

## 4. Part A: Boot the live session and test the hardware

Nothing in this step writes to the laptop's internal disk.

### 4.1 Boot from the USB stick

**Method 1: from inside Windows (easiest, no key timing):**

1. Plug in USB stick #1. Dock the keyboard on the lower screen.
2. **Settings → System → Recovery → Advanced startup → Restart now.**
3. On the blue screen, choose **Use a device** and pick your USB stick (often listed as "UEFI: <brand name>").

**Method 2: the boot menu key:**

1. Shut down completely.
2. Press the power button, then **tap `Esc` repeatedly** until a boot menu appears.
3. Pick the USB stick (the entry starting with **UEFI:**).

> **Do not change the permanent boot order in the UEFI settings, and do not turn off Secure Boot.** The one-time boot menu leaves everything else as it was, which is the safest choice for BitLocker. Ubuntu works with Secure Boot on.

### 4.2 Start the live session

1. A black GRUB menu appears. Pick **Try or Install Ubuntu**.
2. When the welcome window appears, choose your language and then **Try Ubuntu** (not Install).
3. You're now in a temporary Ubuntu desktop. Nothing you do here is saved.

### 4.3 Hardware test checklist

Work through this list and record the results. They'll help you decide in Step 5.

| # | Test | How | Expected in a *plain* live session | Your result |
|---|---|---|---|---|
| 1 | Top screen works | Look at it | ✅ Works | |
| 2 | Bottom screen works | Look at it; open **Settings → Displays** | ✅ Shows as a second monitor (may be blank until you lift the keyboard) | |
| 3 | Touch on top screen | Tap an icon | ✅ Works | |
| 4 | Touch on bottom screen | Tap something on the bottom screen | ⚠️ May move things on the *top* screen (the add-on fixes this) | |
| 5 | Wi-Fi | Top-right menu → connect | ✅ Works | |
| 6 | Docked keyboard typing | Type in a text field | ✅ Works | |
| 7 | Lift keyboard off | Pick it up | ⚠️ Bottom screen doesn't turn on/off by itself (the add-on fixes this) | |
| 8 | Wi-Fi after lifting keyboard | Check whether Wi-Fi stays connected | ✅ Should stay on (kernel 6.11+). If it drops, your kernel is too old. | |
| 9 | Pair keyboard over Bluetooth | **Settings → Bluetooth**, keyboard off the laptop, **hold `F10` for 4–5 s** until the light blinks blue quickly, then pick it in the list | ✅ Pairs | |
| 10 | Fn keys (brightness/volume) | Press them while docked | ⚠️ Often don't work (the add-on fixes this) | |
| 11 | Speakers | Play a YouTube video | ⚠️ Works but sounds flatter than on Windows | |
| 12 | Screen flicker | Watch the OLED for a minute | ⚠️ May flicker (the add-on turns off "Panel Self Refresh") | |
| 13 | Webcam | Open the **Cheese** app if available | Usually ✅ | |

✅ = should work as it is. ⚠️ = a known limitation of a plain install that the add-on fixes later.

### 4.4 Run the read-only "duo doctor" check

The JowiAoun project includes a check that **only reads** hardware information and changes nothing. With Wi-Fi connected, open **Terminal** (`Ctrl + Alt + T`) and run:

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/JowiAoun/linux-on-zenbook-duo ~/linux-on-zenbook-duo
cd ~/linux-on-zenbook-duo
bin/duo-cli doctor
```

(Installing `git` here only affects the temporary live session; it's gone after you shut down.)

Read the report. Save a photo of it, or copy it to a file on another USB stick, if you want to look at it later or share it when asking for help.

Also note your kernel version:

```bash
uname -r
```

It should be **6.11 or higher**.

### 4.5 Shut down

Click top-right → **Power Off**. Remove the stick when told to. The laptop then boots Windows as usual.

---

## 5. Decision point

- **Most things are ✅ or ⚠️, and the ⚠️ items match the table:** continue to Part B. The add-on handles the ⚠️ items.
- **Something is badly broken** (e.g. a screen is black, the keyboard doesn't type when docked, Wi-Fi doesn't work at all): stop here. Try a newer Ubuntu (25.10 / 26.04) live session, or ask in the [asusctl issue #25](https://github.com/flukejones/asusctl/issues/25) thread with your duo doctor output.
- **You just wanted to look around, or test feasibility with a single small stick:** you're done. Nothing was changed. Your filled-in checklist (4.3) and the `duo-cli doctor` output are your feasibility answer.

---

## 6. Part B: Install Ubuntu onto the external USB drive

> 🎯 **The one rule for this part:** every partition, **and the boot loader**, must go onto the **USB target drive**. Never select the internal disk (`nvme0n1`) for anything.

### 6.1 Connect both drives

1. Plug in **USB stick #1** (installer) and **USB drive #2** (target). If you're using an external SSD, put it on a **USB-C/Thunderbolt** port for speed.
2. Dock the keyboard and plug in the charger.
3. Boot the installer stick exactly as in [Step 4.1](#41-boot-from-the-usb-stick), and choose **Try Ubuntu** again.

### 6.2 Identify the drives

Open **Terminal** and run:

```bash
lsblk -o NAME,SIZE,TRAN,MODEL
```

You'll see something like:

```
NAME          SIZE  TRAN   MODEL
sda            7.5G usb    SanDisk Ultra        ← installer stick (#1)
sdb          232.9G usb    Samsung PSSD T7      ← TARGET (#2)  ✅ install here
nvme0n1      953.9G nvme   Micron/SK hynix ...  ← INTERNAL WINDOWS DISK ⛔ never touch
├─nvme0n1p1    260M                              (Windows EFI partition)
├─nvme0n1p2     16M
├─nvme0n1p3  952.0G                              (C:)
└─nvme0n1p4      1G                              (Recovery)
```

**Write down your target's name (e.g. `sdb`) and size.** In this example, **`TRAN = usb`** + matching size + matching model = the right drive. Anything starting with `nvme` is the internal disk.

### 6.3 Start the installer

Double-click **Install Ubuntu 24.04** on the desktop, then:

1. **Language, accessibility, keyboard layout:** pick your preferences.
2. **Internet:** connect to Wi-Fi.
3. **Type of installation:** *Interactive installation*.
4. **Applications:** *Default selection* is fine.
5. **Optimise your computer:**
   - ☑ **Install third-party software for graphics and Wi-Fi hardware**
   - ☑ **Download and install support for additional media formats**
   - If it asks to configure Secure Boot for third-party drivers, set a simple password and **remember it**. You'll need it once, on the next reboot (see [Troubleshooting → blue MOK screen](#10-troubleshooting)).

### 6.4 Partition the target drive manually (the important part)

1. On **"How do you want to install Ubuntu?"**, choose **Manual installation**. *Do **not** choose "Install alongside Windows" or "Erase disk"; those can work on the internal disk.*
2. In the partition editor, select your **target drive** (`sdb` in the example; check the size).
3. If it already has partitions, delete them all (select each one → **−**). **Only on the target drive!**
4. Create these partitions in the free space on the target drive (select free space → **+**):

   | # | Size | Used as / Type | Mount point | Why |
   |---|---|---|---|---|
   | 1 | **512 MB** | **EFI System Partition** (FAT32) | `/boot/efi` (set automatically) | The USB drive's own boot partition, so it never needs the internal one |
   | 2 | **all remaining space** | **ext4** | `/` | Ubuntu and your files |

   (You don't need a swap partition. Ubuntu creates a swap *file* automatically.)

5. At the bottom of the screen, find **"Device for boot loader installation"** and choose **the target drive itself** (e.g. `/dev/sdb`, **not** `sdb1` and **never** `nvme0n1`).
6. **Check the summary screen carefully before you click Install.** Every line that says *formatted* or *created* must mention your target (e.g. `sdb`). If you see `nvme0n1` anywhere, go **Back** and fix it.

> 💡 **Should I encrypt the USB drive?** A USB drive is easy to lose. If you'll carry personal data on it, look for **Advanced features → Use LVM and encryption** on the guided path. It's more complex with manual partitioning on 24.04, so if this is your first time, install without encryption first and learn the basics.

### 6.5 Finish the install

1. **Time zone** → **Create your account** (pick a strong password; you'll type it often).
2. Click **Install**. It takes 10–40 minutes depending on the USB drive's speed.
3. When it's done, click **Restart now**. Remove **only the installer stick #1** when asked, and **leave the target drive #2 plugged in**.

---

## 7. Make sure Windows was not touched

Even when you pick the USB drive as the boot loader location, the Ubuntu installer **sometimes still writes its boot files to the internal EFI partition**, and it may change the boot order so the laptop tries Ubuntu first. This doesn't harm Windows itself, but it can cause:

- a `grub>` prompt when the USB drive is unplugged, and
- a BitLocker recovery prompt the next time Windows starts.

### 7.1 Check the boot order

1. Unplug the USB target drive.
2. Turn on the laptop.
   - **Windows starts normally** → good. Continue to 7.2.
   - **You see `grub>` or a GRUB menu** → type `exit` and press Enter (or reboot and press `Esc` → pick **Windows Boot Manager**). Then fix the order: press **`F2`** at power-on to open the UEFI settings → **Boot** tab → move **Windows Boot Manager** to the top → **Save & Exit**.
   - **BitLocker asks for the recovery key** → type the 48-digit key you saved in [Step 2.1](#21-save-your-bitlocker-recovery-key). Windows will start, and it usually won't ask again.

### 7.2 Check the internal EFI partition for stray Ubuntu files (optional)

In an **admin** PowerShell window, run:

```powershell
mountvol S: /s
dir S:\EFI
mountvol S: /d
```

- You see only `Boot` and `Microsoft` (maybe `ASUS`) → ✅ perfect. The installer kept off the internal disk.
- You also see an `ubuntu` folder → the installer put a copy there. **It's harmless as long as Windows Boot Manager is first in the boot order** (7.1). Beginners should just leave it alone. Deleting files from the EFI partition by hand is how people actually soft-brick their boot setup.

> ⚠️ Always run `mountvol S: /d` at the end. It hides the partition again.

### 7.3 Make the USB drive boot on its own (recommended)

To make sure the USB drive can start Ubuntu **without** anything on the internal disk (even on a different computer), do this once from inside the installed Ubuntu (Step 8 explains how to boot it):

```bash
sudo dpkg-reconfigure grub-efi-amd64
```

Press Enter through the screens and keep the existing values, **except**: when asked **"Force extra installation to the EFI removable media path?"**, answer **Yes**.

This copies the Secure-Boot-signed boot files to the generic location `\EFI\BOOT\BOOTX64.EFI` on the USB drive's own EFI partition. That's the location every UEFI firmware checks on a removable drive.

---

## 8. First boot: set up Ubuntu for the Duo

### 8.1 Boot the installed Ubuntu

1. Plug in the **target USB drive** (#2), dock the keyboard, and power on.
2. Tap **`Esc`** → pick the USB drive (**UEFI: <drive name>**), or use **Windows → Settings → Recovery → Advanced startup → Use a device**.
3. If you set a Secure Boot password in 6.3, a **blue "Perform MOK management" screen** appears the first time: choose **Enroll MOK → Continue → Yes**, type the password, then **Reboot**.
4. Log in with the account you created.

### 8.2 Update everything

```bash
sudo apt update && sudo apt full-upgrade -y
sudo reboot
```

After rebooting, confirm the kernel version:

```bash
uname -r      # must be 6.11 or higher
```

### 8.3 Install the Zenbook Duo add-on

For the **2024 model (UX8406MA)**, use JowiAoun's project:

```bash
sudo apt install -y git
git clone https://github.com/JowiAoun/linux-on-zenbook-duo ~/linux-on-zenbook-duo
cd ~/linux-on-zenbook-duo
bin/duo-cli doctor        # read-only check, same as in Part A
./install.sh              # the actual install
```

Then reboot. The installer is safe to run more than once ("idempotent"), so if something goes wrong halfway, you can simply run `./install.sh` again.

For the **2025 model (UX8406CA)**, use [Fmstrat/zenbook-duo-linux](https://github.com/Fmstrat/zenbook-duo-linux) instead and follow its README. JowiAoun's project says the 2025 model is *likely* compatible but untested.

> Before you run any script from the internet, it's good practice to at least skim it. Open `install.sh` in the Text Editor first. You don't need to understand every line, just make sure it's what the README describes.

### 8.4 Re-run the hardware checklist

Go back to the table in [Step 4.3](#43-hardware-test-checklist). Items 4, 7, 10, 11, and 12 should now be ✅:

- Bottom screen turns off when the keyboard is laid on it, and on when it's lifted
- Touch on the bottom screen hits the bottom screen
- Fn keys and keyboard backlight work
- Speakers sound fuller
- No OLED flicker

### 8.5 Keep the session on GNOME + Wayland

On the login screen, a gear icon (bottom-right, after clicking your name) lets you pick the session. Keep it on **Ubuntu** (Wayland), **not "Ubuntu on Xorg"**. The display features of the add-on need GNOME on Wayland.

---

## 9. Everyday use: switching between Windows and Linux

| You want… | Do this |
|---|---|
| **Windows** | Unplug the USB drive (or leave it in) and power on normally. |
| **Ubuntu** | Plug in the USB drive → power on → tap **`Esc`** → pick the USB drive. |
| **Ubuntu, from inside Windows** | Settings → System → Recovery → Advanced startup → **Use a device**. |

**Rules of thumb:**

- 🔌 **Never unplug the USB drive while Ubuntu is running.** It's like pulling the hard drive out of a running PC. Shut down first.
- 💤 **Prefer shutting down over sleep in Ubuntu.** Sleeping with the OS on a USB drive works on most setups but is the most likely place for glitches. Test it a few times before you trust it.
- 🔋 **Always do a full Shut Down (not Restart) when switching from Windows to Ubuntu**, if the speakers ever sound distorted.
- 🔄 **Keep both systems updated.** If a Windows update ever makes the USB drive stop booting, see Troubleshooting.
- 💾 **Back up the USB drive.** Flash drives fail without warning. Ubuntu has a built-in **Backups** app (Déjà Dup).

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| USB drive not listed in the `Esc` boot menu | Written in the wrong mode, or a slow/unsupported stick | Rewrite with Rufus using **GPT + UEFI (non CSM)**; try **DD mode**; try another port or another stick |
| Keyboard doesn't work in the boot menu / UEFI | Keyboard is detached (Bluetooth isn't active before the OS starts) | Lay the keyboard on the lower screen |
| "Security violation" / blocked boot | Secure Boot rejected something | Use the official Ubuntu ISO; don't use unofficial ISOs or custom kernels. **Don't** turn Secure Boot off as a "fix" (it can trigger BitLocker) |
| Blue **MOK management** screen | First boot after installing third-party drivers with Secure Boot on | **Enroll MOK → Continue → Yes →** enter the password you chose in the installer → **Reboot** |
| `grub>` prompt when the USB drive is unplugged | Ubuntu's boot loader was placed on the internal disk and put first | Type `exit`, or fix the boot order (Windows Boot Manager first). See [Step 7.1](#71-check-the-boot-order) |
| Windows asks for the BitLocker recovery key | Boot order or settings changed | Enter the 48-digit key from [Step 2.1](#21-save-your-bitlocker-recovery-key). It usually only asks once |
| Wi-Fi turns off when you lift the keyboard | Kernel older than 6.11 | `sudo apt full-upgrade`, then check `uname -r` |
| Docked keyboard suddenly stops responding | Known hardware/firmware glitch with the pogo-pin connection | Lift the keyboard off and put it back |
| Fn keys don't work | Add-on not installed or not running | Re-run `./install.sh`; reboot |
| Second screen black after an update | A kernel regression (happened once in 2024) | At the GRUB menu, pick **Advanced options for Ubuntu** → the **previous** kernel |
| Speakers sound harsh/distorted | Windows Fast Startup left the amplifier in a bad state | Make sure `powercfg /h off` was run; do a full **Shut Down** from Windows, then boot Ubuntu |
| Ubuntu very slow | The USB drive is too slow | Use an external SSD on a USB-C port |
| A Windows update made the USB drive unbootable | A Secure Boot list (DBX/SBAT) update blocked an old boot loader (happened in August 2024) | Boot the **installer stick**, open a terminal in the live session, and follow Ubuntu's current guidance for that update; or reinstall onto the USB drive with a newer Ubuntu ISO. Windows is not affected |

**Where to ask for help:**

- [JowiAoun/linux-on-zenbook-duo issues](https://github.com/JowiAoun/linux-on-zenbook-duo/issues): attach your `duo-cli doctor` output
- [asusctl issue #25](https://github.com/flukejones/asusctl/issues/25): the main developer thread for the Duo
- [Ubuntu Discourse](https://discourse.ubuntu.com) / [Ask Ubuntu](https://askubuntu.com): general Ubuntu questions

---

## 11. How to undo everything

Because nothing was installed on the internal disk, undoing is simple:

1. **Unplug the USB drive.** Windows boots exactly as before.
2. **Reuse the USB drive:** in Windows, open **Disk Management** (right-click Start), right-click each partition **on the USB drive** → **Delete Volume**, then right-click the empty space → **New Simple Volume** → NTFS or exFAT. *(Double-check the disk number and size so you're working on the USB drive, not Disk 0.)*
3. **If Windows Boot Manager isn't first in the boot order:** press `F2` at power-on → **Boot** → move it to the top → **Save & Exit**.
4. **If there's an `ubuntu` folder on the internal EFI partition** (Step 7.2) and you want it gone: in an admin terminal, run `bcdedit /enum firmware` to see whether an "ubuntu" entry exists. It's harmless to leave it. If you want it removed, ask for help instead of deleting EFI files by hand.
5. **Optional:** turn Fast Startup back on with `powercfg /h on` (admin terminal).

---

## 12. Sources

- [JowiAoun/linux-on-zenbook-duo](https://github.com/JowiAoun/linux-on-zenbook-duo): install commands, `duo-cli doctor`, kernel ≥ 6.11 and Fast Startup warnings, tested on Ubuntu 24.04.4
- [Fmstrat/zenbook-duo-linux](https://github.com/Fmstrat/zenbook-duo-linux): 2025 model (UX8406CA) support
- [alesya-h/zenbook-duo-2024-ux8406ma-linux](https://github.com/alesya-h/zenbook-duo-2024-ux8406ma-linux/): the original scripts
- [asusctl issue #25](https://github.com/flukejones/asusctl/issues/25): developer discussion
- [UbuntuHandbook: Install Ubuntu 24.04 step by step](https://ubuntuhandbook.org/index.php/2024/04/install-ubuntu-24-04-desktop/): installer screens and the boot-loader device option
- [UbuntuBuzz: Ubuntu with dual boot, external drive and UEFI](https://www.ubuntubuzz.com/2023/04/how-to-install-ubuntu-2304-lunar-lobster-with-dualboot-external-drive-and-uefi-setup.html): choosing the boot loader device for external drives
- [Ubuntu Discourse: Ubuntu 24.04 dual boot with Windows 11](https://discourse.ubuntu.com/t/i-need-to-install-ubuntu-24-04-correctly-with-some-detailed-information-dual-boot-with-w11-pro/79776): Fast Startup and dual-boot advice
- [Rufus](https://rufus.ie) · [Ubuntu downloads](https://ubuntu.com/download/desktop) · [Microsoft recovery key lookup](https://aka.ms/myrecoverykey)

---

*This is a community-knowledge guide, not official ASUS or Canonical documentation. The Duo add-ons are hobby projects. Read their READMEs, since commands can change between versions.*
