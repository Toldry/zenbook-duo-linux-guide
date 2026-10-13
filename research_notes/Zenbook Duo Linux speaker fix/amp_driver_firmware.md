# CS35L41 HDA amplifier driver and firmware on the ASUS Zenbook Duo UX8406MA (codec SSID 1043:1C43), kernels 6.8–7.0

Scope note for the report writer: everything below was checked against the kernel source at the exact tags v6.7, v6.8, v6.9, v6.10, v6.11 and v7.0 (fetched from GitHub's torvalds/linux mirror), against the current linux-firmware tree and its history (GitLab API), against the firmware/tuning files themselves (read as data with `strings`/`od`, nothing executed), and against packages.ubuntu.com. lore.kernel.org, git.kernel.org, lkml.org/lkml.iu.edu, spinics.net and ratatoskr.run were blocked (HTTP 403 from the egress proxy, or DNS failure in the fetch tool), so I could only see mailing-list posts through search snippets or GitHub commit pages; those are flagged. Line anchors below point to the exact tagged files.

Short answer to the main question: **in the healthy case the Linux driver does not cap the amplifiers below Windows.** When the UX8406-specific Cirrus firmware loads, Linux sets the amplifier's analog gain to 17.5 dB. That is exactly the `"amplifier_gain": 17.5` recorded inside Cirrus's UX8406 tuning file, and the amp's own DSP runs the same Cirrus processing blocks (Protect Lite, EQ, DRC, Rattle Distortion Limiter). A large driver-level loss happens only in failure states:
- **DSP bypass** (no firmware, SPI-speed bypass, DSP start failure, warm-boot PUP_DONE failure): a fixed "safe" gain of 4.5 dB, which is **13 dB lower**, with no speaker protection.
- **Fallback to Cirrus's generic default tuning:** a tuning literally named `Fixed_Attenuation_…`, which makes the speakers quiet even though the DSP is running.

Each state can be identified from `journalctl -k` (Question 3).

## 1. Does linux-firmware contain cirrus/cs35l41-dsp1-spk-prot-10431c43* files? When were they added, does Ubuntu 26.04/24.04 ship them, and what happens if they are absent?

### Takeaway
Yes. Upstream linux-firmware has shipped UX8406MA-specific CS35L41 firmware since release tag **20231211**: one shared `.wmfw` link and four speaker-ID-specific tuning files (`-spkid0/-spkid1` × `-l0/-r0`). An updated tuning arrived in tag **20240709**. Ubuntu 26.04 ships them, zstd-compressed, in `linux-firmware-misc` (20260319 snapshot), which the `linux-firmware` metapackage pulls in. Ubuntu 24.04 also ships them, but its 20240318 snapshot predates the July 2024 tuning update. If the SSID files cannot be matched, the driver falls back to Cirrus's generic "Fixed_Attenuation" tuning, which is quiet. If even that is missing, it runs the amps without the DSP at a 4.5 dB "safe" gain.

### Cited Findings
- The current upstream `WHENCE` lists, for this SSID: `Link: cirrus/cs35l41-dsp1-spk-prot-10431c43.wmfw -> cs35l41/v6.83.0/halo_cspl_RAM_revB2_29.85.0.wmfw` and `File: cirrus/cs35l41-dsp1-spk-prot-10431c43-spkid0-l0.bin`, `…-spkid0-r0.bin`, `…-spkid1-l0.bin`, `…-spkid1-r0.bin`. There are **no** non-spkid `-l0/-r0` `.bin` files and **no** `.bincfg` gain override for 10431c43. — [linux-firmware WHENCE](https://gitlab.com/kernel-firmware/linux-firmware/-/blob/main/WHENCE)
- These files were added by commit `978dff6` "linux-firmware: Add firmware for Cirrus CS35L41 on 2024 ASUS Zenbook Laptops" (Stefan Binding, Cirrus; authored 2023-10-04, committed 2023-11-15; message: "Support for 4 laptops using CS35L41."). The same commit added `spk-cali` variants and the 10431c33 (UX5304MA) files. The earliest release tag containing it is **20231211**. — [commit 978dff6](https://gitlab.com/kernel-firmware/linux-firmware/-/commit/978dff67939252711df73b805a85210f276625cf); [tags containing it (GitLab API)](https://gitlab.com/api/v4/projects/kernel-firmware%2Flinux-firmware/repository/commits/978dff679392/refs?type=tag)
- The tuning was updated by commit `fe07c4b` "cirrus: cs35l41: Update various firmware for ASUS laptops using CS35L41" (Stefan Binding, 2024-07-02; "Updated laptops: 10431a63, 10431c03, 10431c43"). The earliest tag containing it is **20240709**. — [commit fe07c4b](https://gitlab.com/kernel-firmware/linux-firmware/-/commit/fe07c4bdd435c623fdf215bb0d94f9e6f838e164); [tags API](https://gitlab.com/api/v4/projects/kernel-firmware%2Flinux-firmware/repository/commits/fe07c4bdd435/refs?type=tag)
- The current tuning file contains the following text, read as data:
  - origin path `C:\Users\tyang\Desktop\Product Setting\SmartAMP\ASUS\ASUS_Zenbook\2024Projects\UX8406\Tuning Release\12082023\UX8406_HX-L_tuning_RDL300Only_ID.bin`
  - `"amplifier_gain": 17.5`, `"client_tuning_name": "UX8406_HX-L_tuning_RDL300Only_ID"`, `"client_version": "6.83.0"`, `"client_name": "LabSuite"`
  - `"feature_blocks": "… Mix, Protect Lite, … Equalizer, Dynamic Range Compressor, Rattle Distortion Limiter 1"`

  The R file is `UX8406_HX-R_tuning_RDL300Only_ID` with the same gain. — [spkid0-l0.bin](https://gitlab.com/kernel-firmware/linux-firmware/-/raw/main/cirrus/cs35l41-dsp1-spk-prot-10431c43-spkid0-l0.bin); [spkid1-r0.bin](https://gitlab.com/kernel-firmware/linux-firmware/-/raw/main/cirrus/cs35l41-dsp1-spk-prot-10431c43-spkid1-r0.bin)
- The spkid1-l0 file carries the same tuning name as spkid0-l0 (`UX8406_HX-L_tuning_RDL300Only_ID`). — [spkid1-l0.bin](https://gitlab.com/kernel-firmware/linux-firmware/-/raw/main/cirrus/cs35l41-dsp1-spk-prot-10431c43-spkid1-l0.bin)
- The original November 2023 version of the L tuning reads `…\UX8406\Tuning Release\08042023\UX8406_Lch_tuning_ID.bin`, with `"amplifier_gain": 17.5`, the same feature-block list, and `"tuning_id": "0x270100"`. It is 5340 bytes, against 5364 bytes for the current file. — [spkid0-l0.bin at 978dff6](https://gitlab.com/kernel-firmware/linux-firmware/-/raw/978dff67939252711df73b805a85210f276625cf/cirrus/cs35l41-dsp1-spk-prot-10431c43-spkid0-l0.bin)
- The linked `.wmfw` is Cirrus's `FIRMWARE_HALO_CSPL` (speaker-protection) build for B2 silicon, with info text "Fri 31 Mar 2023 10:42:49 W. Europe Daylight Time". — [halo_cspl_RAM_revB2_29.85.0.wmfw](https://gitlab.com/kernel-firmware/linux-firmware/-/raw/main/cirrus/cs35l41/v6.83.0/halo_cspl_RAM_revB2_29.85.0.wmfw)
- **Ubuntu 26.04 (resolute):** `/usr/lib/firmware/cirrus/cs35l41-dsp1-spk-prot-10431c43-spkid0-l0.bin.zst`, `…-spkid0-r0.bin.zst`, `…-spkid1-l0.bin.zst`, `…-spkid1-r0.bin.zst` and `…/cs35l41-dsp1-spk-prot-10431c43.wmfw.zst`, all in package **linux-firmware-misc**. — [packages.ubuntu.com contents search, resolute](https://packages.ubuntu.com/search?searchon=contents&keywords=10431c43&mode=filename&suite=resolute&arch=any)
  - The linux-firmware-misc version is 20260319.git217ca6e4-0ubuntu2. — [linux-firmware-misc (resolute)](https://packages.ubuntu.com/resolute/linux-firmware-misc)
  - The `linux-firmware` metapackage depends on `linux-firmware-misc`, among `-amd-graphics`, `-intel-graphics`, `-intel-misc`, `-realtek` and others. — [linux-firmware (resolute)](https://packages.ubuntu.com/resolute/linux-firmware)
- **Ubuntu 24.04 (noble):**
  - The release pocket ships the files in the unsplit `linux-firmware` package (`/lib/firmware/cirrus/…10431c43…zst`). — [contents search, noble](https://packages.ubuntu.com/search?searchon=contents&keywords=10431c43&mode=filename&suite=noble&arch=any)
  - noble-updates ships them in `linux-firmware-misc` 20240318.git3b128b60-0ubuntu3.1. — [contents search, noble-updates](https://packages.ubuntu.com/search?searchon=contents&keywords=10431c43&mode=filename&suite=noble-updates&arch=any); [linux-firmware-misc (noble-updates)](https://packages.ubuntu.com/noble-updates/linux-firmware-misc)
- **Driver search order (v7.0).** File names are built as `cirrus/cs35l41-<dspname>-<fwtype>-<ssid>[-spkid<N>][-<amp>].<wmfw|bin>` and are then lowercased, with non-alphanumerics turned into hyphens. — [cs35l41_hda.c v7.0 L164-L218](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L164-L218)
  - With a speaker ID, the `.wmfw` candidates are tried in this order: `-<ssid>-spkid<N>-<amp>` → `-<ssid>-<amp>` → `-<ssid>-spkid<N>` → `-<ssid>`. Each is paired with `-<ssid>-spkid<N>-<amp>.bin`, then `-<ssid>-spkid<N>.bin`. — [L221-L300](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L221-L300)
  - Without a speaker ID: `-<ssid>-<amp>.wmfw/.bin`, then `-<ssid>.wmfw` with `-<ssid>-<amp>.bin` or `-<ssid>.bin`. — [L340-L400](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L340-L400)
  - If all attempts fail: `dev_warn(… "Falling back to default firmware.\n")`, then `cirrus/cs35l41-dsp1-spk-prot.wmfw` + `.bin`, else `"Unable to find firmware and tuning\n"`. — [L306-L335](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L306-L335)
- The amp name is `"%c%d"`: channel letter (L/R/C) plus channel index, giving "L0"/"R0", which become `l0`/`r0` in file names. — [L868-L876](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L868-L876)
- Generic default files exist upstream: `File: cirrus/cs35l41-dsp1-spk-prot.wmfw` and `File: cirrus/cs35l41-dsp1-spk-prot.bin`, added by linux-firmware `feda1996d56d` "linux-firmware: Add firmware for Cirrus CS35L41" (Vitaly Rodionov, 2022-08-03). — [WHENCE](https://gitlab.com/kernel-firmware/linux-firmware/-/blob/main/WHENCE); [commit feda1996d56d](https://gitlab.com/kernel-firmware/linux-firmware/-/commit/feda1996d56d)
- The generic `.bin` is Cirrus's default tuning `e:\workspace\…\default_tunings\internal\CS35L53\Fixed_Attenuation_Mono_48000_29.78.0\full\Fixed_Attenuation_Mono_48000_29.78.0_full.bin`, with `"amplifier_gain": ""`. — [cs35l41-dsp1-spk-prot.bin](https://gitlab.com/kernel-firmware/linux-firmware/-/raw/main/cirrus/cs35l41-dsp1-spk-prot.bin)
- Sibling-model evidence (UX3405MA, SSID 10431A63, not the UX8406MA):
  - Broken state: on a kernel whose `_DSD` lacked the speaker-ID GPIO, the log showed `SPKID: -19`, "Falling back to default firmware." and generic `cirrus/cs35l41-dsp1-spk-prot.bin` with `FW EN: 1`. Users reported Linux volume at "roughly one-third to one-quarter" of Windows.
  - Fixed state: the log showed `cirrus/cs35l41-dsp1-spk-prot-10431a63-spkid1-l0.bin`, `Calibration applied: R0=10639` and `Firmware Loaded - Type: spk-prot, Gain: 19`. On 6.11, speakers were reported "as loud as on Windows".

  — [smallcms/asus_zenbook_ux3405ma issue #7](https://github.com/smallcms/asus_zenbook_ux3405ma/issues/7)

### Inferences
- On Ubuntu 26.04 with the standard `linux-firmware` metapackage, the correct UX8406MA files are installed (high confidence). A "files missing" state needs `linux-firmware-misc` to have been removed or never installed (medium confidence: I did not inspect minimal or OEM seeds).
- A stock 24.04 system most likely has the August 2023 tuning (`UX8406_Lch_tuning_ID`), and 26.04 has the December 2023 tuning (`UX8406_HX-L/R_tuning_RDL300Only_ID`), unless Canonical cherry-picked `fe07c4b` into noble (medium confidence, not verified). Both specify a 17.5 dB amplifier gain, so maximum analog gain is the same. Their EQ, DRC and limiter content differs, but the direction of any audible change is unknown (low confidence).
- Because no kernel property-table entry exists for 10431C43 (Question 4), the speaker-ID GPIO must come from the BIOS `_DSD`. If a BIOS ever lacked it, the driver would take the generic Fixed_Attenuation path, as the UX3405MA did (medium confidence).
- The folder names `08042023` and `12082023` look like tuning-release dates, most likely 4 Aug 2023 and 8 Dec 2023 in US order (low-to-medium confidence; the format is not documented).

### Gaps
- I could not check whether Ubuntu's noble-updates linux-firmware cherry-picked the July 2024 tuning update: the changelog URL returned 404. The user can check the installed version locally (Question 3 gives the command).
- I found no primary-source UX8406MA kernel log; the linux-hardware.org search returned no probe page. Expected log lines in Question 3 are built from the source code and the firmware file contents.

## 2. What AMP_GAIN_PCM / AMP_VOL_PCM values does cs35l41_hda.c write with and without the DSP, how is tuning_gain set, and what is the hardware maximum?

### Takeaway
The driver has two unmute paths:
- **DSP running:** `AMP_GAIN_PCM = tuning_gain`, which defaults to 17 (17.5 dB). A `<coefficient-file>cfg` ("`.bincfg`") file can override it; none exists for 10431c43. Digital volume `AMP_VOL_PCM` is 0 dB.
- **DSP not running:** a hard-coded `0x84`, which is 4.5 dB, **13 dB lower**.

The hardware maximum is register value 20 (20.5 dB). In 6.8 and 6.9 the DSP path was a hard-coded `0x233` (17.5 dB PCM). So on this laptop, any kernel from 6.8 to 7.0 gives the same 17.5 dB whenever the firmware runs, which equals the gain written into the UX8406 tuning.

### Cited Findings
- v7.0, bypass (no-DSP) unmute and mute sequences — [cs35l41_hda.c v7.0 L129-L137](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L129-L137):
  ```c
  static const struct reg_sequence cs35l41_hda_unmute[] = {
  	{ CS35L41_AMP_DIG_VOL_CTRL,	0x00008000 }, // AMP_HPF_PCM_EN = 1, AMP_VOL_PCM  0.0 dB
  	{ CS35L41_AMP_GAIN_CTRL,	0x00000084 }, // AMP_GAIN_PCM 4.5 dB
  };
  static const struct reg_sequence cs35l41_hda_mute[] = {
  	{ CS35L41_AMP_GAIN_CTRL,	0x00000000 }, // AMP_GAIN_PCM 0.5 dB
  	{ CS35L41_AMP_DIG_VOL_CTRL,	0x0000A678 }, // AMP_HPF_PCM_EN = 1, AMP_VOL_PCM Mute
  };
  ```
- v7.0, the decision in `cs35l41_mute()` — [L713-L739](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L713-L739):
  ```c
  if (cs35l41->cs_dsp.running) {
  	dev_dbg(dev, "Using Tuned Gain: %d\n", cs35l41->tuning_gain);
  	amp_gain = (cs35l41->tuning_gain << CS35L41_AMP_GAIN_PCM_SHIFT) |
  		(DEFAULT_AMP_GAIN_PDM << CS35L41_AMP_GAIN_PDM_SHIFT);
  	/* AMP_HPF_PCM_EN = 1, AMP_VOL_PCM  0.0 dB */
  	regmap_write(reg, CS35L41_AMP_DIG_VOL_CTRL, 0x00008000);
  	regmap_write(reg, CS35L41_AMP_GAIN_CTRL, amp_gain);
  } else {
  	regmap_multi_reg_write(reg, cs35l41_hda_unmute, ARRAY_SIZE(cs35l41_hda_unmute));
  }
  ```
- Defaults: `#define DEFAULT_AMP_GAIN_PCM 17 /* 17.5dB Gain */`, `#define DEFAULT_AMP_GAIN_PDM 19 /* 19.5dB Gain */`, and `#define CS35L41_MAX_ACCEPTABLE_SPI_SPEED_HZ 1000000`. — [cs35l41_hda.h v7.0 L24-L26](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.h#L24-L26)
- Registers: `CS35L41_AMP_DIG_VOL_CTRL 0x00006000`, `CS35L41_AMP_GAIN_CTRL 0x00006C04`, `CS35L41_AMP_GAIN_PCM_MASK 0x3E0`, `…_PCM_SHIFT 5`, `CS35L41_AMP_GAIN_PCM_MAX 20`, `CS35L41_AMP_GAIN_PDM_MAX 20`. The code comments map value *n* to (*n*+0.5) dB, so 0 is 0.5 dB, 17 is 17.5 dB and 20 (the maximum) is 20.5 dB. — [include/sound/cs35l41.h v7.0 L103, L114, L556-L561](https://github.com/torvalds/linux/blob/v7.0/include/sound/cs35l41.h#L556-L561)
- `tuning_gain` is reset to the default before every firmware load, on any load error, and on DSP shutdown. It is otherwise set from the tuning-parameter file: `cs35l41_set_default_tuning_params()` gives `tuning_gain = DEFAULT_AMP_GAIN_PCM`. — [L469-L472](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L469-L472), [init_dsp L556-L605](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L556-L605)
- Tuning-parameter file name: `/* Filename is the same as the tuning file with "cfg" suffix */ *filename = kasprintf(GFP_KERNEL, "%scfg", tuning_filename);`. For this laptop it would be `cirrus/cs35l41-dsp1-spk-prot-10431c43-spkid<N>-<l0|r0>.bincfg`. If the file is missing, a `dev_dbg` "Missing Tuning Param for file" is logged and the default stays. — [L143-L150](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L143-L150), [L529-L553](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L529-L553)
- Format: header `{__le32 signature (0x109A4A35); version (must be 1); size (must equal the file size); num_entries}`, then entries `{tuning_index, type, size, gain}`. Type 0 is `TUNING_PARAM_GAIN`, and the handler does `cs35l41->tuning_gain = le32_to_cpu(param->gain);` with **no range check** against `CS35L41_AMP_GAIN_PCM_MAX`. — [L39-L63](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L39-L63), [L474-L527](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L474-L527)
- Cirrus's own `.bincfg` files are 32 bytes. `cs35l41-dsp1-19_5dB.bincfg` is `109a4a35 00000001 00000020 00000001 00000000 00000000 00000010 00000013` (gain 19); the 14_5dB file ends in `0000000e` (gain 14). They were added by linux-firmware `dfadf5687922` "linux-firmware: Add tuning parameter configs for CS35L41 Firmware" (Stefan Binding, 2024-04-18). — [19_5dB.bincfg](https://gitlab.com/kernel-firmware/linux-firmware/-/raw/main/cirrus/cs35l41/bincfgs/cs35l41-dsp1-19_5dB.bincfg); [14_5dB.bincfg](https://gitlab.com/kernel-firmware/linux-firmware/-/raw/main/cirrus/cs35l41/bincfgs/cs35l41-dsp1-14_5dB.bincfg); [commit dfadf5687922](https://gitlab.com/kernel-firmware/linux-firmware/-/commit/dfadf5687922)
- ASUS SSIDs that do get `.bincfg` links in WHENCE:
  - 14.5 dB: 10431433, 10431473, 10431483, 10431663, 10433d78, 10433d88
  - 15.5 dB: 10431514, 10431fb3
  - 16.5 dB: 104317f3
  - 19.5 dB: 10431a63, 10431c03
  - **10431c43: none**, so it keeps the default 17.5 dB.

  — [WHENCE](https://gitlab.com/kernel-firmware/linux-firmware/-/blob/main/WHENCE)
- v6.8 and v6.9 used a fixed DSP gain: `cs35l41_hda_unmute_dsp[] = { …DIG_VOL 0x00008000…, { CS35L41_AMP_GAIN_CTRL, 0x00000233 }, // AMP_GAIN_PCM = 17.5dB AMP_GAIN_PDM = 19.5dB }`, chosen when the DSP runs, and `0x84` (4.5 dB) otherwise. — [cs35l41_hda.c v6.8 L90-L98, L584-L588](https://github.com/torvalds/linux/blob/v6.8/sound/pci/hda/cs35l41_hda.c#L90-L98); [v6.9](https://github.com/torvalds/linux/blob/v6.9/sound/pci/hda/cs35l41_hda.c)
- The `tuning_gain` mechanism comes from kernel commit "ALSA: hda: cs35l41: Set the max PCM Gain using tuning setting" (Stefan Binding, `ef752c6`, 2024-04-18). It is present in v6.10 and absent in v6.9 (I checked both tags). — [GitHub history of cs35l41_hda.c](https://github.com/torvalds/linux/commits/v6.16/sound/pci/hda/cs35l41_hda.c); [v6.10 source](https://github.com/torvalds/linux/blob/v6.10/sound/pci/hda/cs35l41_hda.c)
  - The series cover letter says patch 1 "adds support for a new firmware tuning file which is used to set special tuning parameters used by the firmware". I saw this only as a search snippet. — [lkml mirror, v2 0/7](https://lkml.rescloud.iu.edu/2404.1/05541.html)
- The bypass path is also used whenever firmware start fails: `if (cs35l41_smart_amp(cs35l41) < 0) dev_warn(… "Cannot Run Firmware, reverting to dsp bypass...\n");`. — [L1469-L1474](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L1469-L1474)

### Inferences
- 17.5 dB minus 4.5 dB is 13 dB: about 4.5 times the output voltage and about 20 times the electrical power for the same digital signal. This is arithmetic from the register values (high confidence). A DSP-bypass state therefore fully explains "maximum volume far below Windows" plus harsh sound, since the protection, EQ and limiter are also gone.
- In the healthy state, Linux's analog gain (17.5 dB) equals the gain written into Cirrus's UX8406 tuning metadata, so the driver is not the limiter (high confidence on the Linux side). That the Windows Cirrus driver uses the same 17.5 dB is likely, since the tuning is the same Cirrus LabSuite project for this model, but I could not verify it from the Windows package (medium confidence).
- With firmware running, the amp DSP's own DRC and limiter (Protect Lite, Rattle Distortion Limiter) handle peaks. A hotter digital signal from userspace (compression or limiting upstream, as the Windows Dolby or harman/kardon APO does) should raise perceived loudness while the amp DSP keeps protecting the drivers. This is my inference, not a Cirrus statement (medium confidence).

### Gaps
- I did not find the CS35L41 datasheet text for the exact meaning of AMP_GAIN_PCM (for example, volts peak at 0 dBFS), so absolute output power per setting is not given.
- I did not find out how the Windows Cirrus driver programs AMP_GAIN for 1043:1C43.

## 3. Which kernel log lines reveal the state, and what are the verification commands, expected output and fix for each case?

### Takeaway
Run `journalctl -k -b 0 | grep -iE 'cs35l41|CSC3551|cirrus'` after a **cold** boot. The decisive lines are:
- `CS35L41 Bound - SSID: …, FW EN: <0|1>, SPKID: <n>` (one per amp)
- `Firmware Loaded - Type: spk-prot, Gain: 17` (kernels 6.10 and later)
- the `DSP1:` lines naming the `.wmfw` and `.bin` actually loaded
- the warnings `Falling back to default firmware.`, `SPI speed is too slow…`, `Bypassing Firmware.`, `Cannot Run Firmware, reverting to dsp bypass...` and `Failed waiting for CS35L41_PUP_DONE_MASK: -110`

### Cited Findings
- Exact format strings (v7.0):
  - `"Cirrus Logic CS35L41 (%x), Revision: %02X\n"` at probe — [L2035](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L2035)
  - `"CS35L41 Bound - SSID: %s, BST: %d, VSPK: %d, CH: %c, FW EN: %d, SPKID: %d\n"`, where **FW EN is `cs35l41->cs_dsp.running`** (whether the DSP really runs) — [L1499-L1504](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L1499-L1504). The same fields exist in v6.8. — [v6.8 L1346-L1351](https://github.com/torvalds/linux/blob/v6.8/sound/pci/hda/cs35l41_hda.c#L1346-L1351)
  - `"Firmware Loaded - Type: %s, Gain: %d\n"` — [L1213-L1214](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L1213-L1214). This string is absent in v6.8 (checked).
  - `"Calibration applied: R0=%d\n"` and `"Failed to apply calibration: %d\n"` — [L401-L414](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L401-L414)
  - `"Falling back to default firmware.\n"` and `"Unable to find firmware and tuning\n"` — [L315, L334](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L306-L335)
  - `"No Coefficient File available.\n"` and `"Unable to load Tuning Parameters: %d\n"` — [L586-L591](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L586-L591)
  - `"Bypassing Firmware.\n"`, `"Cannot Initialize Firmware. Error: %d\n"`, `"Fail to start dsp: %d\n"`, `"Timeout waiting for HALO Core to start. State: %u\n"` and `"Firmware status is invalid: %u\n"` — [L1148-L1220](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L1148-L1220)
  - `"Cannot Run Firmware, reverting to dsp bypass...\n"` — [L1473](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L1469-L1474)
  - `"SPI speed is too slow to support firmware download: %d Hz.\n"` (threshold 1,000,000 Hz) — [L1921-L1929](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L1921-L1929)
  - `"Failed waiting for CS35L41_PUP_DONE_MASK: %d\n"` (in cs35l41-lib) — [cs35l41-lib.c v7.0 L1307](https://github.com/torvalds/linux/blob/v7.0/sound/soc/codecs/cs35l41-lib.c#L1300-L1312)
- Lines from the DSP loader (cs_dsp), each prefixed `DSP1: `:
  - `"%s: format %d timestamp %#llx"` and `"%s: %.*s"` (the wmfw info text, at most 100 characters)
  - `"Firmware: %x vendor: 0x%x v%d.%d.%d, %d algorithms"`
  - for the coefficient file, `"%s (v%d): v%d.%d.%d"` and `"<fwtype>: <name text, max 100 chars>"`

  — [cs_dsp.c v7.0 L1544, L1570, L1839, L2219, L2259](https://github.com/torvalds/linux/blob/v7.0/drivers/firmware/cirrus/cs_dsp.c#L2215-L2262). An example of the format from another ASUS model is the Fedora thread titled "DSP1: spk-prot: C:\Users\…\10431C9F_220930_V1_A0.bi". — [Fedora Discussion](https://discussion.fedoraproject.org/t/dsp1-spk-prot-c-users-dchunyi-documents-asus-rog-project-g6-strix16-tuning-20220930-g614-10431c9f-220930-v1-a0-bi/147999)
- The firmware loader search path is `fw_path_para`, then `/lib/firmware/updates/<uname -r>`, `/lib/firmware/updates`, `/lib/firmware/<uname -r>`, `/lib/firmware`. — [drivers/base/firmware_loader/main.c v7.0 L472-L478](https://github.com/torvalds/linux/blob/v7.0/drivers/base/firmware_loader/main.c#L472-L478)
- The modules are `snd-hda-scodec-cs35l41` (core plus property table), `snd-hda-scodec-cs35l41-spi` and `snd-hda-scodec-cs35l41-i2c`. — [side-codecs Makefile v7.0](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/Makefile)
- A community module list from a UX8406MA on NixOS shows `snd_hda_scodec_cs35l41_spi` and `spi_pxa2xx_platform` loaded, consistent with SPI-attached amps. — [NixOS Discourse, post 97](https://discourse.nixos.org/t/asus-zenbook-duo-2024-ux8406ma-nixos/39792/97)
- A community project for this exact laptop reports, on its unit: "running ASUS's `spk-prot` firmware with this unit's calibration (R0=10223/10307)". On a boot after Windows with Fast Startup on, "both amps sometimes time out their power-up handshake (`Failed waiting for CS35L41_PUP_DONE_MASK: -110`). The speakers still play, without the amp DSP: harsh, crackly…". It warns: "Do not re-bind or reload the driver… Recovery is a full power-off". — [JowiAoun/linux-on-zenbook-duo docs/HARDWARE.md](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/docs/HARDWARE.md)

#### Verification commands
Run after a cold boot, with any sound having played once. Use `-b -1` for the previous boot.
```bash
journalctl -k -b 0 --no-pager | grep -iE 'cs35l41|CSC3551|cirrus'      # or: sudo dmesg | grep -iE 'cs35l41|CSC3551|cirrus'
journalctl -k -b 0 --no-pager | grep -E 'Bound - SSID|Firmware Loaded|Falling back|SPI speed|Bypassing|reverting to dsp bypass|PUP_DONE|Calibration'
ls -l /usr/lib/firmware/cirrus/ | grep -i 10431c43                     # expect 4 x .bin.zst + 1 .wmfw.zst (symlink to cs35l41/v6.83.0/...)
dpkg -S cs35l41-dsp1-spk-prot-10431c43 ; apt policy linux-firmware-misc   # expect linux-firmware-misc (26.04)
zstdcat /usr/lib/firmware/cirrus/cs35l41-dsp1-spk-prot-10431c43-spkid0-l0.bin.zst | strings | grep -E 'client_tuning_name|amplifier_gain'
#   26.04 expected: "UX8406_HX-L_tuning_RDL300Only_ID", 17.5 ; old (2023) package: "UX8406_Lch_tuning_ID", 17.5
cat /sys/module/snd_hda_scodec_cs35l41/parameters/firmware_autostart    # expect Y
grep -r cs35l41 /etc/modprobe.d/ 2>/dev/null                            # expect nothing
amixer -c 0 controls | grep -E 'DSP1|Forced Mute'                       # card index from `aplay -l`
amixer -c 0 cget iface=CARD,name='L0 DSP1 Firmware Load'; amixer -c 0 cget iface=CARD,name='R0 DSP1 Firmware Load'   # expect values=on
# Optional, root, while audio plays: read the actual gain registers through regmap debugfs
sudo grep -E '6c04:|(^| )0*6000:' /sys/kernel/debug/regmap/*CSC3551*/registers   # DSP case: 6c04 -> 00000233 ; bypass: 00000084
```

#### Expected output and fix per case
The device names look like `cs35l41-hda spiN-CSC3551:00-cs35l41-hda.0` and `.1` (the SPI bus number varies). The SSID may print as upper case (`10431C43`, taken from ACPI `_SUB`) or lower case (taken from the codec).

| Case | Distinctive log lines | Effective amp state | Fix |
|---|---|---|---|
| **A. Healthy** (expected on 26.04, cold boot) | `DSP1: cirrus/cs35l41-dsp1-spk-prot-10431c43.wmfw: format 3 timestamp …`; `DSP1: cirrus/cs35l41-dsp1-spk-prot-10431c43-spkid<0/1>-l0.bin (v…): v…`; `DSP1: spk-prot: C:\Users\tyang\Desktop\Product Setting\SmartAMP\ASUS\ASUS_Zenbook\2024Projects\UX8406\Tuning Release` (truncated at 100 characters); `Calibration applied: R0=…`; `Firmware Loaded - Type: spk-prot, Gain: 17`; `CS35L41 Bound - SSID: 10431C43, … CH: L, FW EN: 1, SPKID: 0` (or 1), and the same for `CH: R` / `-r0.bin` | DSP running, UX8406 tuning, AMP_GAIN_PCM 17.5 dB, AMP_VOL 0 dB | None at driver level. Any remaining gap to Windows is upstream processing and volume mapping (other workstreams). |
| **B. Generic fallback** | `Falling back to default firmware.`; `DSP1: cirrus/cs35l41-dsp1-spk-prot.wmfw …`, `…spk-prot.bin …`; `Firmware Loaded - Type: spk-prot, Gain: 17`; `FW EN: 1`, often with `SPKID: -19` (‑ENODEV) or another negative value | DSP running with Cirrus's **Fixed_Attenuation** default tuning: quiet and generic | If SPKID < 0: the BIOS `_DSD` lacks `spk-id-gpios`. Update the BIOS, and report to linux-sound / Cirrus (Stefan Binding) for a property-table fixup like the 10431A63 one. If SPKID ≥ 0 but files are missing: install `linux-firmware-misc`. |
| **C. No firmware at all** | `Falling back to default firmware.` + `Unable to find firmware and tuning`; `Cannot Initialize Firmware. Error: -2`; `Cannot Run Firmware, reverting to dsp bypass...`; `FW EN: 0` | Bypass: AMP_GAIN_PCM **4.5 dB**, no protection | `sudo apt install linux-firmware` (or `linux-firmware-misc`), then cold boot |
| **D. SPI too slow** | `SPI speed is too slow to support firmware download: <N> Hz.`; `Bypassing Firmware.`; `FW EN: 0` | Bypass, 4.5 dB | No user-side override exists (no module parameter). Update the BIOS and report upstream. Not expected on UX8406MA, since community units run the firmware with calibration. |
| **E. Warm boot after Windows** | `Failed waiting for CS35L41_PUP_DONE_MASK: -110` | Plays without the DSP: harsh, quiet | Full power-off. In Windows: `powercfg /h off` (disables Fast Startup) and use Shut down rather than Restart. Do not rebind the driver. |
| **F. DSP start failure** | `Fail to start dsp`, `Timeout waiting for HALO Core to start`, `Firmware status is invalid`, then `Cannot Run Firmware, reverting to dsp bypass...`, `FW EN: 0` | Bypass, 4.5 dB | Cold boot; if it persists, report with the full log |
| **G. Firmware disabled or unloaded** | `FW EN: 0` with no warnings (autostart off), or `amixer` shows `… DSP1 Firmware Load` = off | Bypass, 4.5 dB | Remove any `options snd_hda_scodec_cs35l41 firmware_autostart=0`. Set `amixer -c0 cset iface=CARD,name='L0 DSP1 Firmware Load' on` (and R0) while nothing is playing. If `alsactl` keeps restoring "off", fix or delete the saved state in `/var/lib/alsa/asound.state`. |

### Inferences
- The table's expected lines are built from the v7.0 format strings plus the actual strings inside the UX8406 firmware files. Device names, versions and timestamps will differ in detail (medium-high confidence).
- On 24.04's GA kernel 6.8 there is no `Firmware Loaded … Gain` line and no `Calibration applied` line. Use `FW EN:` and the `DSP1:` lines instead (high confidence, checked in v6.8).
- Reading register 0x6C04 via regmap debugfs during playback is the most direct proof of the gain in use (`0x233` means 17.5 dB PCM / 19.5 dB PDM; `0x84` means 4.5 dB). I have not tested this on a UX8406MA, so treat it as a suggestion (medium confidence).
- Case G with alsactl is a community-reported pattern on sibling Zenbooks (search summaries of the lamperez gist). It is plausible because these CARD-interface controls are saved and restored like any other control (medium-low confidence).

### Gaps
- No real UX8406MA dmesg from linux-hardware.org or bugzilla was retrievable to confirm the exact `BST:`/`VSPK:` values or the speaker-ID value. Those come from the BIOS `_DSD` and need the user's own log.

## 4. What do cs35l41_hda_property.c and the Realtek quirk table say for 10431C43, and could boost or other settings limit output?

### Takeaway
The Realtek table maps 0x1043:0x1c43 "ASUS UX8406MA" to `ALC245_FIXUP_CS35L41_SPI_2`, which binds two SPI-attached CS35L41 amps to the HDA codec. The entry has been there since v6.7. **There is no 10431C43 entry** in `cs35l41_hda_property.c` in v6.8 or v7.0, so the driver takes everything from the BIOS ACPI `_DSD`:
- reset and speaker-ID GPIOs
- speaker position and GPIO functions
- boost peak current, inductor and capacitor

No source shows a UX8406MA-specific boost limit. Peak-current values are validated to 1600–4500 mA, and the driver does not program a boost-voltage or brownout cap of its own.

### Cited Findings
- `SND_PCI_QUIRK(0x1043, 0x1c43, "ASUS UX8406MA", ALC245_FIXUP_CS35L41_SPI_2),` appears at:
  - [v7.0 alc269.c L7317](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/realtek/alc269.c#L7317)
  - [v6.8 patch_realtek.c L10074](https://github.com/torvalds/linux/blob/v6.8/sound/pci/hda/patch_realtek.c#L10074)
  - [v6.7 patch_realtek.c L9997](https://github.com/torvalds/linux/blob/v6.7/sound/pci/hda/patch_realtek.c#L9997), next to `0x1c33 "ASUS UX5304MA"`
- The fixup is `[ALC245_FIXUP_CS35L41_SPI_2] = { .type = HDA_FIXUP_FUNC, .v.func = cs35l41_fixup_spi_two }`, and `cs35l41_fixup_spi_two()` calls `comp_generic_fixup(codec, action, "spi", "CSC3551", "-%s:00-cs35l41-hda.%d", 2);`. — [alc269.c v7.0 L3267-L3270](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/realtek/alc269.c#L3267-L3270), [L6262-L6265](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/realtek/alc269.c#L6262-L6265)
- A third-party driver database ties `ACPI\VEN_CSC&DEV_3551&SUBSYS_10431C43` ("Cirrus Logic Awesome Speaker Amps") and `INTELAUDIO\FUNC_01&VEN_10EC&DEV_0294&SUBSYS_10431C43` (Realtek) to the "ASUS Zenbook Duo UX8406MA". — [driveridentifier (CSC3551)](https://www.driveridentifier.com/scan/cirrus-logic-awesome-speaker-amps-driver/driver-detail/627AC7A05A45437792B8CF97AF64CEEE/5753925/d3541e18b4d7955d429001ed711dd7f7/1122366182/ACPI-VEN_CSC&DEV_3551&SUBSYS_10431C43); [driveridentifier (Realtek)](https://www.driveridentifier.com/scan/realtekr-audio-driver/download/1122366202/627AC7A05A45437792B8CF97AF64CEEE/INTELAUDIO/FUNC_01&VEN_10EC&DEV_0294&SUBSYS_10431C43)
- The property table struct holds `{ssid, num_amps, boost_type, channel[], reset_gpio_index, spkid_gpio_index, cs_gpio_index, boost_ind_nanohenry, boost_peak_milliamp, boost_cap_microfarad}`. ASUS entries run from 104312AF to 10433A60, with typical internal-boost values `1000, 4500, 24`. 10431C43 is absent; a case-insensitive grep for "1c43" over v6.8 and v7.0 found it only in the Realtek tables. — [cs35l41_hda_property.c v7.0 L17-L30, L83-L121](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda_property.c#L17-L121); [v6.8](https://github.com/torvalds/linux/blob/v6.8/sound/pci/hda/cs35l41_hda_property.c)
- When no table entry matches, `cs35l41_add_dsd_properties()` does not apply. The driver then parses the ACPI `_DSD`: `cirrus,dev-index`, `cirrus,speaker-position`, `cirrus,gpio1-func`, `cirrus,gpio2-func`, `cirrus,boost-peak-milliamp`, `cirrus,boost-ind-nanohenry`, `cirrus,boost-cap-microfarad`, `reset-gpios` and `spk-id-gpios`. — [cs35l41_hda.c v7.0 L1720-L1860](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L1720-L1860), [property.c L570-L580](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda_property.c#L570-L580)
- The boost-type enum is `CS35L41_INT_BOOST` (0), `CS35L41_EXT_BOOST` (1), `CS35L41_SHD_BOOST_ACTV`, `CS35L41_SHD_BOOST_PASS`, `CS35L41_EXT_BOOST_NO_VSPK_SWITCH`. The `BST:` value in the Bound line is this number. — [include/sound/cs35l41.h v7.0 L764-L772](https://github.com/torvalds/linux/blob/v7.0/include/sound/cs35l41.h#L764-L772)
- `cs35l41_boost_config()` rejects a peak current outside 1600–4500 mA (`"Invalid boost inductor peak current: %d mA"`) and logs `"Error in Boost DT config"`. — [cs35l41-lib.c v7.0 L1034-L1037, L1150-L1153](https://github.com/torvalds/linux/blob/v7.0/sound/soc/codecs/cs35l41-lib.c#L1030-L1040)
- The SPI-speed bypass applies only when the control bus is SPI, which is the case on UX8406MA. Its commit message says it targets "Some laptops without _DSD have the SPI speed set very low in the BIOS." — [commit d110858](https://github.com/torvalds/linux/commit/d110858a6925827609d11db8513d76750483ec06)

### Inferences
- Since UX8406MA has a working BIOS `_DSD` (no kernel fixup was ever needed, and Cirrus shipped spkid-specific tunings for it), its boost parameters come from ASUS's BIOS, presumably the same values Windows uses (medium confidence). I found no evidence that boost peak current or brownout handling caps Linux output below Windows on this model.
- The SPI-speed problem was aimed at laptops **without** `_DSD`, and community UX8406MA units run the firmware with calibration. So the SPI bypass is unlikely here, but it is cheap to rule out with `grep 'SPI speed'` (medium-high confidence).

### Gaps
- I could not read the UX8406MA ACPI tables (SPI `ConnectionSpeed`, `_DSD` boost values, speaker-ID GPIO). linux-hardware.org and linuxhw dumps were not found by search. The user can dump them with `sudo acpidump -b; iasl -d dsdt.dat ssdt*.dat` and grep for `CSC3551`.
- The driver sets no boost target voltage (VBST) or brownout limits that I could see. Whether the CSPL firmware manages class-H or brownout on this tuning is not documented in the sources I reached.

## 5. Is speaker calibration from the EFI variable (CirrusSmartAmpCalibrationData, cs-amp-lib) applied on this model, and what if it is missing?

### Takeaway
Yes, if the BIOS provides it. Since v6.10 the driver reads the UEFI variable `CirrusSmartAmpCalibrationData` through cs-amp-lib. It matches each entry to the amp's silicon UID and writes CAL_R and related values into the running DSP, logging `Calibration applied: R0=<n>`. A community UX8406MA unit reports R0=10223/10307, so ASUS does provision it. If the variable is missing, the driver continues silently and the DSP runs without per-unit calibration. Calibration does not change the amp gain register.

### Cited Findings
- `#define CIRRUS_LOGIC_CALIBRATION_EFI_NAME L"CirrusSmartAmpCalibrationData"` with GUID `02f9af02-7734-4233-b43d-93fe5aa35db3`. cs-amp-lib also knows an HP variable, `SmartAmpCalibrationData` {53559579-8753-4f5c-9130-e82acfb8d893}. — [cs-amp-lib.c v7.0 L24-L38](https://github.com/torvalds/linux/blob/v7.0/sound/soc/codecs/cs-amp-lib.c#L24-L38)
- The HDA driver reads the silicon UID, calls `cs_amp_get_efi_calibration_data(dev, silicon_uid, index, &cal_data)`, treats `-ENOENT` and `-EOVERFLOW` as "no calibration, continue", and sets `cal_data_valid` only on success. — [cs35l41_hda.c v7.0 L443-L466](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L443-L466)
- After the DSP powers up: `if (!cs35l41->cal_data_valid) return; … cs_amp_write_cal_coeffs(&cs35l41->cs_dsp, &cs35l41_calibration_controls, &cs35l41->cal_data)`, then logs `"Calibration applied: R0=%d\n"` or `"Failed to apply calibration: %d\n"`. — [L401-L414](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L401-L414); [init_dsp L598](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L596-L599)
- The DSP controls written are `CAL_R`, `CAL_STATUS`, `CAL_CHECKSUM` and `CAL_AMBIENT` (alg 205). — [L30-L35, L66-L74](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L30-L74)
- cs-amp-lib warnings: `"No calibration for silicon ID %#llx"`, `"Calibration entry %d does not match silicon ID"` and `"Failed to read calibration data from EFI: %d"`. — [cs-amp-lib.c v7.0 L397, L459, L466](https://github.com/torvalds/linux/blob/v7.0/sound/soc/codecs/cs-amp-lib.c#L395-L467)
- History:
  - v6.8 already read `L"CirrusSmartAmpCalibrationData"` with its own code (`efi.get_variable`, `cs35l41_apply_calibration`). — [v6.8 L365-L435](https://github.com/torvalds/linux/blob/v6.8/sound/pci/hda/cs35l41_hda.c#L365-L435)
  - Commit `068fc7f` "ALSA: hda: cs35l41: Use shared cs-amp-lib to apply calibration" (Stefan Binding, 2024-04-18) moved it to cs-amp-lib; I confirmed it in v6.10. — [history](https://github.com/torvalds/linux/commits/v6.16/sound/pci/hda/cs35l41_hda.c); [v6.10](https://github.com/torvalds/linux/blob/v6.10/sound/pci/hda/cs35l41_hda.c)
- UX8406MA community report: "running ASUS's `spk-prot` firmware with this unit's calibration (R0=10223/10307)". — [JowiAoun docs/HARDWARE.md](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/docs/HARDWARE.md)
- Sibling UX3405MA: `Calibration applied: R0=10639` appeared in the working, loud state. — [issue #7](https://github.com/smallcms/asus_zenbook_ux3405ma/issues/7)

### Inferences
- Calibration is not a loudness knob: no code path touches AMP_GAIN or AMP_VOL based on it (high confidence). It feeds the protection algorithm's reference speaker resistance, so its absence would most plausibly make the thermal estimate less accurate rather than directly cap volume (medium-low confidence; I found no Cirrus statement on the exact effect).
- To check: `journalctl -k -b0 | grep -i calibration` should give two `Calibration applied: R0=…` lines (one per amp), and `ls /sys/firmware/efi/efivars/ | grep -i CirrusSmartAmp` should show the variable (medium-high confidence).

### Gaps
- I found no maintainer statement quantifying the behaviour of the CSPL firmware without calibration (default R0, extra headroom or not).

## 6. Which ALSA controls and module parameters does the driver expose, and can any be used to raise the maximum level safely?

### Takeaway
The driver exposes three CARD-interface controls per amp: `L0/R0 DSP1 Firmware Load` (bool), `L0/R0 DSP1 Firmware Type` (spk-prot / spk-cali / spk-diag / misc) and `L0/R0 Forced Mute Status` (read-only). It has one read-only module parameter, `firmware_autostart` (default on). None of them raises the maximum. Their only effect on loudness is to make things worse, by unloading the firmware into 4.5 dB bypass. The only driver-supported way to change the gain is a `.bincfg` tuning-parameter file. Raising it above the 17.5 dB the UX8406 tuning was built for is technically possible but unvalidated and not advisable.

### Cited Findings
- `static bool firmware_autostart = 1; module_param(firmware_autostart, bool, 0444); MODULE_PARM_DESC(firmware_autostart, "Allow automatic firmware download on boot" "(0=Disable, 1=Enable) (default=1); ");` — [cs35l41_hda.c v7.0 L91-L94](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L91-L94)
- Control names are formatted as `"%s DSP1 Firmware Type"`, `"%s DSP1 Firmware Load"` and `"%s Forced Mute Status"` with `amp_name` ("L0"/"R0"). Type values come from `cs35l41_hda_fw_ids` = {"spk-prot", "spk-cali", "spk-diag", "misc"}. Loading or unloading is refused during playback (`"Cannot Load/Unload firmware during Playback"`). — [L82-L90](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L82-L90), [L1230-L1385](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L1230-L1385)
- Commit `312c04c` "ALSA: hda: cs35l41: Stop creating ALSA Controls for firmware coefficients" (Stefan Binding, 2024-08-05) removed the per-coefficient DSP controls. They still exist in v6.10 (`hda_cs_dsp_add_controls`) and are gone in v6.11 (checked). — [history](https://github.com/torvalds/linux/commits/v6.16/sound/pci/hda/cs35l41_hda.c); [v6.10](https://github.com/torvalds/linux/blob/v6.10/sound/pci/hda/cs35l41_hda.c); [v6.11](https://github.com/torvalds/linux/blob/v6.11/sound/pci/hda/cs35l41_hda.c)
- The gain override exists only through `<coeff-file>cfg`, with no clamp on the value (Question 2). The kernel firmware loader looks in `/lib/firmware/updates/…` before `/lib/firmware/…`. — [cs35l41_hda.c v7.0 L143-L150, L517-L519](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda.c#L143-L150); [firmware_loader/main.c L472-L478](https://github.com/torvalds/linux/blob/v7.0/drivers/base/firmware_loader/main.c#L472-L478)
- The UX8406 tuning records `"amplifier_gain": 17.5`. — [spkid0-l0.bin](https://gitlab.com/kernel-firmware/linux-firmware/-/raw/main/cirrus/cs35l41-dsp1-spk-prot-10431c43-spkid0-l0.bin)
- Cirrus ships `.bincfg` links only for SSIDs whose tuning needs a non-default gain (Question 2), none for 10431c43. — [WHENCE](https://gitlab.com/kernel-firmware/linux-firmware/-/blob/main/WHENCE)

### Inferences
- Technically, placing a file at `/lib/firmware/updates/cirrus/cs35l41-dsp1-spk-prot-10431c43-spkid<N>-l0.bincfg` (and `-r0`, uncompressed is fine) with a valid header and gain 18–20 would make the driver program 18.5–20.5 dB. That is at most +3 dB, logged as `Firmware Loaded … Gain: <n>` (high confidence from the code). It is **not safe in any validated sense**:
  - It departs from the 17.5 dB that the Protect Lite, DRC and limiter tuning was built for.
  - Cirrus did not ship such a file for this model.
  - The parser does not range-check, so a wrong value reaches the register.

  My recommendation: do not do it. The +3 dB at most is small next to the 13 dB bypass loss, and it is easier to win loudness upstream in software while the amp DSP keeps protecting the speakers (medium confidence on the risk assessment).
- Toggling `DSP1 Firmware Load` off, or setting `firmware_autostart=0`, drops to 4.5 dB with no protection. These controls are diagnostic, not tuning (high confidence).
- GNOME's Over-Amplification is a software gain above 100% in the PipeWire/PulseAudio volume. It does not touch these amp registers (high confidence; covered in another workstream).

### Gaps
- No Cirrus or maintainer statement was found on user-supplied `.bincfg` files or on safe headroom for this model.

## 7. Are there mailing-list threads, bugzilla entries or commits (2023–2026) about lower CS35L41 HDA output on Linux, ASUS SSIDs lacking firmware, or gain changes? What did the Cirrus maintainers say?

### Takeaway
Cirrus (Stefan Binding) states in a merged commit that without firmware "the volume will be low to ensure safe operation of the CS35L41". The 2024 tuning-gain work exists so that per-laptop gains match each tuning. ASUS "quiet on Linux" reports were traced to the wrong firmware path: missing speaker-ID GPIO, then generic fallback. They were fixed by kernel `_DSD` fixups and per-SSID firmware, not by raising gains. I found no thread specific to UX8406MA loudness, and no 2025–2026 kernel change to the gain logic.

### Cited Findings
- Commit `d110858` "ALSA: hda: cs35l41: Prevent firmware load if SPI speed too low" (Stefan Binding; Cc stable v6.7+; Link `20231221132518.3213-3-sbinding@opensource.cirrus.com`; signed off by Takashi Iwai). The message reads: "Some laptops without _DSD have the SPI speed set very low in the BIOS… if the SPI speed is too slow, it can take a long time to download. For this reason, disable firmware loading if the maximum SPI speed is too low. **Without Firmware, audio playback will work, but the volume will be low to ensure safe operation of the CS35L41.**" — [GitHub commit page](https://github.com/torvalds/linux/commit/d110858a6925827609d11db8513d76750483ec06)
- A related v2 patch, "ALSA: hda: cs35l41: Safety-guard against capped SPI speed": a tester reported about 180 s of firmware loading after resume, and a 3051 Hz SPI speed on an affected laptop. I saw this only as a search snippet. — [spinics alsa-devel](https://www.spinics.net/lists/alsa-devel/msg169747.html)
- Kernel history of `cs35l41_hda.c`, 2023–2025 — [history v6.16](https://github.com/torvalds/linux/commits/v6.16/sound/pci/hda/cs35l41_hda.c):
  - `8c4c216` "Add config table to support many laptops without _DSD" (2023-12-18)
  - `ef752c6` "Set the max PCM Gain using tuning setting" (2024-04-18)
  - `068fc7f` "Use shared cs-amp-lib to apply calibration" (2024-04-18)
  - `b627054` "Update DSP1RX5/6 Sources for DSP config" (2024-04-18)
  - `5f9f982` "Fix missing Speaker ID GPIO description in _DSD" (2024-07-04)
  - `312c04c` "Stop creating ALSA Controls for firmware coefficients" (2024-08-05)

  The move to `sound/hda/codecs/side-codecs/` was `6014e90` "ALSA: hda: Move codec drivers into sound/hda/codecs directory" (2025-07-11). Commits since then (to Aug 2026) are cleanups and robustness fixes: guard()/auto-cleanup, NULL-pointer fixes, "Fix firmware load work teardown" (2026-05-15). None touch gain. — [history master](https://github.com/torvalds/linux/commits/master/sound/hda/codecs/side-codecs/cs35l41_hda.c)
- Sibling UX3405MA (10431A63): issue opened 2024-06-22 reporting Linux at about 1/3–1/4 of Windows volume with "Falling back to default firmware" and SPKID -19. A user filed kernel bugzilla #218991. Cirrus posted a fix on 2024-07-03, now `missing_speaker_id_gpio2` for 10431A63 in the property table (present in v6.11, absent in v6.10). Users later reported 6.11 "as loud as on Windows", and a full shutdown was still needed after booting Windows. — [issue #7](https://github.com/smallcms/asus_zenbook_ux3405ma/issues/7); [property.c v7.0 L526](https://github.com/torvalds/linux/blob/v7.0/sound/hda/codecs/side-codecs/cs35l41_hda_property.c#L526); [v6.11 property.c](https://github.com/torvalds/linux/blob/v6.11/sound/pci/hda/cs35l41_hda_property.c)
- linux-firmware Cirrus commits for ASUS: `978dff6` (2023), `dfadf5687922` (tuning-parameter configs, 2024-04-18) and `fe07c4b` (2024-07-02, includes 10431c43). — [978dff6](https://gitlab.com/kernel-firmware/linux-firmware/-/commit/978dff67939252711df73b805a85210f276625cf); [dfadf5687922](https://gitlab.com/kernel-firmware/linux-firmware/-/commit/dfadf5687922); [fe07c4b](https://gitlab.com/kernel-firmware/linux-firmware/-/commit/fe07c4bdd435c623fdf215bb0d94f9e6f838e164)
- 2026 mailing-list items seen **only as search-result snippets**. I could not open them (policy-blocked), so treat them as unverified:
  - An August 2026 alsa-devel report "cs35l41-hda: PUP_DONE times out on ASUS…" (UX3405CA) was withdrawn after a BIOS update from .314 to .315 fixed it. — [ratatoskr mirror](https://ratatoskr.run/alsa-devel/2026/08/17368731/t)
  - A July 2026 "[PATCH] ALSA: hda/cs35l41: Support ASUS…" (a UM3405GA SSID) reportedly noted that playback was not verified end-to-end because DSP firmware was not yet available. — [ratatoskr mirror](https://ratatoskr.run/alsa-devel/2026/07/17278087/t)
  - "[PATCH v2] ALSA: hda: cs35l41: Enable VSPK on…" (10431A63) — [ratatoskr mirror](https://ratatoskr.run/linux-sound/2026/08/17417452/t)
  - "CS35L41 HDA SPI: GPIO chip-select not…" (April 2026) — [ratatoskr mirror](https://ratatoskr.run/alsa-devel/2026/04/10731453)

### Inferences
- The maintainers' consistent position is: firmware plus SSID-specific tuning gives full, protected output; no firmware gives deliberately low, safe output. A Linux-vs-Windows gap on a correctly loaded system is not something they have treated as a driver bug (medium confidence, from commit messages and fixes rather than an explicit statement).

### Gaps
- No lore, bugzilla or launchpad thread specific to UX8406MA loudness was found. lore.kernel.org and bugzilla.kernel.org could not be queried directly from this environment.

## 8. Is it possible or safe to use firmware from a sibling ASUS model, or to obtain the tuning from the Windows driver package? What are the risks to the speakers?

### Takeaway
It is unnecessary and risky. The UX8406MA already has its own official Cirrus tuning upstream, built by Cirrus for "UX8406" left and right speakers. A sibling's tuning, for example 10431c33 (UX5304MA) or 10431c03 (19.5 dB), would apply another product's speaker-protection limits, EQ and gain to these drivers. There is no documented route from the Windows driver package to the Linux `.bin` format, which Cirrus generates from its LabSuite tuning projects.

### Cited Findings
- The UX8406 files are product-specific: `ASUS_Zenbook\2024Projects\UX8406\…\UX8406_HX-L_tuning_RDL300Only_ID` / `UX8406_HX-R_…`, made with LabSuite 6.83.0. They include protection (Protect Lite), EQ, DRC and a rattle distortion limiter, and specify a 17.5 dB amplifier gain. — [spkid0-l0.bin](https://gitlab.com/kernel-firmware/linux-firmware/-/raw/main/cirrus/cs35l41-dsp1-spk-prot-10431c43-spkid0-l0.bin)
- Sibling SSIDs carry different gain configs: 10431a63 and 10431c03 link to 19.5 dB `.bincfg` files, and others to 14.5–16.5 dB. — [WHENCE](https://gitlab.com/kernel-firmware/linux-firmware/-/blob/main/WHENCE)
- The UX5304MA (10431c33) uses a different `.wmfw` build (`cs35l41/v6.61.1/halo_cspl_RAM_revB2_29.63.1.wmfw`) from UX8406MA (`v6.83.0/…29.85.0`). — [WHENCE](https://gitlab.com/kernel-firmware/linux-firmware/-/blob/main/WHENCE)
- Cirrus's generic default tuning is a "Fixed_Attenuation" profile, consistent with a policy of attenuating when the speaker is unknown. — [cs35l41-dsp1-spk-prot.bin](https://gitlab.com/kernel-firmware/linux-firmware/-/raw/main/cirrus/cs35l41-dsp1-spk-prot.bin)

### Inferences
- A sibling tuning's excursion, thermal and limiter parameters are matched to different drivers and enclosures. On the UX8406MA they could over-drive the speakers, or simply sound worse. A higher-gain sibling (19.5 dB) adds 2 dB of analog gain on top. Speaker damage is a plausible worst case (medium confidence; no measured data).
- Extracting a tuning from the Windows "Cirrus Logic Awesome Speaker Amps" package and converting it would require Cirrus-internal tooling. It would also most likely reproduce what linux-firmware already contains for this SSID (low-medium confidence).
- The practical fix path for "far worse than Windows" on a correctly loaded system lies above the driver: Windows-like voicing, loudness processing and volume mapping. The JowiAoun project measured this laptop's speakers as "everything below 200 Hz more than 18 dB down", and says Windows does the voicing "in an APO above the driver". — [JowiAoun docs/HARDWARE.md](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/docs/HARDWARE.md) (community measurement with the internal microphone, shape only)

### Gaps
- I did not inspect the ASUS Windows driver package for its Cirrus tuning revision. Whether Windows ships a newer tuning than the December 2023 one in linux-firmware is unknown.
