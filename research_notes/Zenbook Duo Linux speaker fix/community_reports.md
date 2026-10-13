# Community reports and fixes: weak or poor-sounding speakers on the Zenbook Duo (UX8406MA / UX8406CA) and related ASUS CS35L41 laptops on Linux

Research date: 2026-10-13. Scope: UX8406MA first (codec SSID 1043:1C43), then UX8406CA and other ASUS laptops with Realtek codecs and Cirrus CS35L41 amps.

Access limits that shape these notes: this environment's egress policy blocked Reddit, the Arch wiki and forums, bugzilla.kernel.org, lore.kernel.org, git.kernel.org, lkml mirrors, ratatoskr.run, dev.to, Phoronix, Fedora Discussion, Launchpad and linux-hardware.org, both for curl and for WebFetch. What I could read directly: GitHub pages, raw.githubusercontent.com, GitLab (linux-firmware, asus-linux/asusctl and its API) and NixOS Discourse. Items marked **(search summary)** come only from a search engine's summary of a page I could not open. Treat them as lower confidence.

## 1. What have UX8406MA/UX8406CA owners reported about speaker volume and quality on Linux, and what fixed it?

### Takeaway
I found no first-hand UX8406MA or UX8406CA report, with logs, that says "quieter or thinner than Windows" and names a fix. Duo owners report something else: silence, garbling or distortion that comes and goes. That is the CS35L41 `PUP_DONE` failure after a warm boot from Windows (fixes: cold shutdown, Fast Startup off, BIOS update), plus a 6.9.12 SOF regression that 6.10 fixed. The only Duo-specific work on sound quality is JowiAoun's measured EasyEffects chain (see Q4). On kernel 7.0 the Duo's amp firmware normally loads correctly, so the user's loudness gap most likely comes from missing Windows-side processing. The cheap log checks listed under Inferences can rule out the amp-side causes first.

### Cited Findings

**How the UX8406MA's speaker path is supported (verified in source, October 2026)**
- Mainline maps SSID 1043:1c43 to `SND_PCI_QUIRK(0x1043, 0x1c43, "ASUS UX8406MA", ALC245_FIXUP_CS35L41_SPI_2)`, a two-amp SPI CS35L41 fixup. — [alc269.c (mainline)](https://github.com/torvalds/linux/blob/master/sound/hda/codecs/realtek/alc269.c)
- The quirk already existed by March 2024: it shows up as diff context in a March 2024 ASUS quirk patch. — [lkml mirror 2403.3/11993](https://lkml.rescloud.iu.edu/2403.3/11993.html) **(search summary)**. JowiAoun's project states "the ASUS SSID quirks for CSC3551 landed upstream in 6.7". — [46-speaker-amp.sh](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/system/46-speaker-amp.sh)
- 10431C43 has **no** entry in the kernel's CS35L41 `_DSD` override table, so the Duo relies on its own BIOS `_DSD`. The sibling UX3405MA (10431A63) has needed `missing_speaker_id_gpio2` since v6.11. — [cs35l41_hda_property.c (mainline)](https://github.com/torvalds/linux/blob/master/sound/hda/codecs/side-codecs/cs35l41_hda_property.c); [v6.11 copy](https://github.com/torvalds/linux/blob/v6.11/sound/pci/hda/cs35l41_hda_property.c)
- linux-firmware added amp firmware for 10431c43 in commit 978dff67, "Add firmware for Cirrus CS35L41 on 2024 ASUS Zenbook Laptops", by Stefan Binding (Cirrus). It was authored 2023-10-04 and committed 2023-11-15. The commit covers four laptops: 10431c33, 10431c03, 10431a63 and 10431c43. The kernel quirk table names these UX5304MA, UM3406HA, UX3405MA and UX8406MA. — [linux-firmware 978dff67](https://gitlab.com/kernel-firmware/linux-firmware/-/commit/978dff67939252711df73b805a85210f276625cf); [alc269.c](https://github.com/torvalds/linux/blob/master/sound/hda/codecs/realtek/alc269.c)
- The Duo's tuning files (`cs35l41-dsp1-spk-prot-10431c43-spkid{0,1}-{l0,r0}.bin`) were updated on 2024-07-02 in fe07c4bd, "Update various firmware for ASUS laptops using CS35L41". The updated laptops were 10431a63, 10431c03 and 10431c43. The `10431c43.wmfw` entry links to `cs35l41/v6.83.0/halo_cspl_RAM_revB2_29.85.0.wmfw`. — [linux-firmware fe07c4bd](https://gitlab.com/kernel-firmware/linux-firmware/-/commit/fe07c4bdd435c623fdf215bb0d94f9e6f838e164); [WHENCE](https://gitlab.com/kernel-firmware/linux-firmware/-/blob/main/WHENCE)
- linux-firmware ships **no `.bincfg` (amp-gain tuning file) for 10431c43**. The siblings 10431a63 (UX3405MA) and 10431c03 (UM3406HA) got links to `cs35l41/bincfgs/cs35l41-dsp1-19_5dB.bincfg` in commit dfadf568 on 2024-04-18. — [linux-firmware dfadf568](https://gitlab.com/kernel-firmware/linux-firmware/-/commit/dfadf5687922f239eb8b04df0e1726230098b802); [WHENCE](https://gitlab.com/kernel-firmware/linux-firmware/-/blob/main/WHENCE)
- How the driver sets amp gain, from the code:
  - While the DSP firmware runs, it writes the amp's PCM gain from `tuning_gain`. That defaults to `DEFAULT_AMP_GAIN_PCM 17 /* 17.5dB Gain */` unless a file named `<tuning .bin name>cfg` (a `.bincfg`) overrides it.
  - With no DSP firmware running, unmute writes `AMP_GAIN_PCM 4.5 dB`.
  - At load it logs `Firmware Loaded - Type: %s, Gain: %d`. At bind it logs `CS35L41 Bound - SSID, BST, VSPK, CH, FW EN, SPKID`. VSPK is "GPIO1 is the VSPK switch"; FW EN is "DSP running".
  - It exposes `<amp> DSP1 Firmware Load` and `DSP1 Firmware Type` ALSA controls, and `firmware_autostart` defaults to 1.
  - — [cs35l41_hda.c](https://github.com/torvalds/linux/blob/master/sound/hda/codecs/side-codecs/cs35l41_hda.c); [cs35l41_hda.h](https://github.com/torvalds/linux/blob/master/sound/hda/codecs/side-codecs/cs35l41_hda.h)
- Kernel 6.9 used a fixed `0x233` (PCM 17.5 dB) whenever the DSP was on. The tuning-gain code first appears in v6.10. It came from Stefan Binding's April 2024 series, whose patch 1 was "Set the max PCM Gain using tuning setting". — [v6.9 cs35l41_hda.c](https://github.com/torvalds/linux/blob/v6.9/sound/pci/hda/cs35l41_hda.c); [v6.10 cs35l41_hda.c](https://github.com/torvalds/linux/blob/v6.10/sound/pci/hda/cs35l41_hda.c); [LKML 2024-04-11](https://lkml.org/lkml/2024/4/11/713) **(search summary)**

**First-hand UX8406MA logs and reports, in date order**
- **2024-05-23, asusctl GitLab #510** (LightJack05; Arch, kernel 6.9.1-arch1-2, BIOS UX8406MA.305 dated 01/16/2024): "Sound seems to be working sometimes using sof-firmware, but really unreliable." The attached dmesg shows:
  - Both amps load `cirrus/cs35l41-dsp1-spk-prot-10431c43.wmfw` (dated "Fri 31 Mar 2023", "v0.65.0").
  - Both load the `-spkid0-l0/r0.bin` tunings, whose embedded path is `...ASUS_Zenbook\2024Projects\UX8406\Tuning Release\08042023\UX8406_Lch_tuning_ID.bin`.
  - The bind lines are `CS35L41 Bound - SSID: 10431C43, BST: 1, VSPK: 1, CH: L, FW EN: 1, SPKID: 0` and `... BST: 1, VSPK: 0, CH: R, FW EN: 1, SPKID: 0`.
  - The codec autoconfig is `ALC294: line_outs=1 (0x17...) type:speaker`.
  - Six `Failed waiting for CS35L41_PUP_DONE_MASK: -110` lines follow, at about 16–17 s.
  - — [asusctl #510](https://gitlab.com/asus-linux/asusctl/-/work_items/510); [attached dmesg.log](https://gitlab.com/asus-linux/asusctl/uploads/7a57ee0864eb3e0ea9bc44d34cc4e62d/dmesg.log)
- **NixOS Discourse thread "Asus Zenbook Duo (2024 / UX8406MA) & NixOS"** (145 posts, 2024-02-14 to 2025-12-27). Every post that mentions audio:
  - 2024-07-15: xevicb (Fedora 40) reports "frequent sound issues (no sound sometimes...)". tomassplatch confirms "regular sound issues (no sound or sound garbled)". tom1 sees only rare garbling, which he ties to plugging or unplugging the charger. — [#76](https://discourse.nixos.org/t/asus-zenbook-duo-2024-ux8406ma-nixos/39792/76), [#77](https://discourse.nixos.org/t/asus-zenbook-duo-2024-ux8406ma-nixos/39792/77), [#78](https://discourse.nixos.org/t/asus-zenbook-duo-2024-ux8406ma-nixos/39792/78)
  - 2024-07-17/18, xevicb: "100% of the times I've tried, sound works fine when I boot into linux with the PC completely turned off. If I'm on windows and I reboot to linux, almost all the times I'm having … issues." He also asks others whether they run BIOS 306. — [#83](https://discourse.nixos.org/t/asus-zenbook-duo-2024-ux8406ma-nixos/39792/83), [#86](https://discourse.nixos.org/t/asus-zenbook-duo-2024-ux8406ma-nixos/39792/86)
  - 2024-07-18, LGiusti84 (Fedora 40): the sound disconnects, and only a reboot fixes it. — [#85](https://discourse.nixos.org/t/asus-zenbook-duo-2024-ux8406ma-nixos/39792/85)
  - 2024-08-13, mfenniak: going from kernel 6.9.8 to 6.9.12 killed both speaker and mic (`tplg component load failed -22`), and moving to 6.10 fixed it. **Outdated.** — [#92](https://discourse.nixos.org/t/asus-zenbook-duo-2024-ux8406ma-nixos/39792/92)
  - 2025-06-04/05: agoose77 asks "Has anyone been able to get sound working properly?". hacker1024 replies "I've had no problems on recent kernels. No custom configuration, just stock PipeWire." agoose77 then: "…then I updated the BIOS firmware and now it just works. I suspect the recent kernel patches actually depend upon the BIOS update!" — [#137](https://discourse.nixos.org/t/asus-zenbook-duo-2024-ux8406ma-nixos/39792/137), [#138](https://discourse.nixos.org/t/asus-zenbook-duo-2024-ux8406ma-nixos/39792/138), [#139](https://discourse.nixos.org/t/asus-zenbook-duo-2024-ux8406ma-nixos/39792/139)
  - None of the 145 posts discuss loudness or tone compared with Windows. I scanned all of them for audio, speaker, sound, volume, cs35l41, easyeffect, pipewire, sof, dolby and cirrus. — [thread](https://discourse.nixos.org/t/asus-zenbook-duo-2024-ux8406ma-nixos/39792)
- **JowiAoun/linux-on-zenbook-duo** (UX8406MA, Ubuntu 24.04, kernel 7.0, in daily use since July 2026):
  - A normal boot logs `DSP1: cirrus/cs35l41-dsp1-spk-prot-10431c43.wmfw`, `Calibration applied: R0=10223` and `CS35L41 Bound — … CH: L, FW EN: 1`.
  - The `PUP_DONE` timeout is described as a race. Measured 2026-07-23: "eight failures on one boot with the four boots before it completely clean". In that state the speakers "play without the amp DSP, which sounds harsh, crackly and distorted".
  - The author blames Windows Fast Startup in a dual boot. The fix given is `powercfg /h off`, then Shut down rather than Restart.
  - Re-binding the driver made it worse: `Failed to add KControl L0 DSP1 Firmware Type = -16`, then the right amp never probes.
  - — [46-speaker-amp.sh](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/system/46-speaker-amp.sh)
- The calibration values for that unit are R0=10223/10307. A separate "silent-speakers wedge" (an XRUN loop on PipeWire 1.0.5, measured 2026-09-13) is fixed by restarting PipeWire or running `pw-metadata -n settings 0 clock.min-quantum 1024`, plus a buffer-floor config. — [HARDWARE.md#speakers](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/docs/HARDWARE.md#speakers)
- JowiAoun's `duo doctor` audio section checks only these: a sound card exists, SOF is active, the `duo-cs35l41-check` `PUP_DONE` reporter, the Bluetooth headset profile, PipeWire realtime priority, and i915/asus/sof/cs35l41 errors in the kernel log. It does **not** check which amp firmware file loaded, the gain, or FW EN. — [bin/duo-cli](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/bin/duo-cli)
- JowiAoun's issue tracker has 2 issues (both 2026-09-19, about brightness keys and tablet mapping), none about audio. — [issues](https://github.com/JowiAoun/linux-on-zenbook-duo/issues?q=is%3Aissue)
- The asusctl umbrella issue #25 now redirects to OpenGamingCollective/asusctl#25, "UX8406 (Zenbook Duo 2024) support" (opened 2024-04-08 by hacker1024, activity through August 2026). It covers hotkeys, backlight, profiles, PSR, the second screen and fans. Its known-issues table has no audio rows and no comment discusses speakers, according to the page summary. GitLab asusctl #25 is unrelated: a 2020 config warning. — [GitHub #25](https://github.com/OpenGamingCollective/asusctl/issues/25); [GitLab #25](https://gitlab.com/asus-linux/asusctl/-/work_items/25)
- alesya-h/zenbook-duo-2024-ux8406ma-linux: the README has nothing on audio, and none of its 16 issues are about audio. — [repo](https://github.com/alesya-h/zenbook-duo-2024-ux8406ma-linux); [issues](https://github.com/alesya-h/zenbook-duo-2024-ux8406ma-linux/issues?q=is%3Aissue)

**UX8406CA (2025, Core Ultra 285H)**
- Fmstrat/zenbook-duo-linux was validated on a UX8406CA running Ubuntu 25.10. It lists no speaker problem. Its only audio note: games running through Proton lose audio, fixed with `pw-metadata -n settings 0 clock.force-quantum 512`. None of its 7 issues are about audio. — [repo](https://github.com/Fmstrat/zenbook-duo-linux); [issues](https://github.com/Fmstrat/zenbook-duo-linux/issues?q=is%3Aissue)
- rahulc07 (2025-07-06) on the 2025 model: "It needs a very recent version of intel-ucode and sof-firmware for audio." — [alesya-h #24](https://github.com/alesya-h/zenbook-duo-2024-ux8406ma-linux/issues/24)
- The mainline Realtek quirk table has no UX8406CA entry; only UX8406MA is listed. I could not find the UX8406CA's SSID or amp configuration. — [alc269.c](https://github.com/torvalds/linux/blob/master/sound/hda/codecs/realtek/alc269.c)

### Inferences
- **No Duo owner has documented a "quiet vs Windows" fix.** Published Duo audio complaints are about reliability: silence or distortion after a warm boot from Windows, and a 2024 SOF regression. They are not about the loudness gap the user describes. *Confidence: high for the sources I could read; medium overall, because Reddit, the Arch wiki and forums, bugzilla and Launchpad were unreachable.*
- **On the user's setup the amp firmware is probably fine.** That setup is Ubuntu 26.04, kernel 7.0, cold boots only, and linux-firmware certainly newer than July 2024. The Duo's firmware and updated tunings are present. JowiAoun's 7.0 log on the same model shows FW EN: 1 and calibration applied. Expected log on such a boot:
  - the 10431c43 `.wmfw` and a `-spkid0` or `-spkid1` `.bin` for each amp
  - `Calibration applied: R0=…`
  - `Firmware Loaded - Type: spk-prot, Gain: 17`, i.e. 17.5 dB, because the Duo has no `.bincfg`
  - `CS35L41 Bound - SSID: 10431C43, … FW EN: 1`

  *Confidence: medium-high.*
- **Pre-July-2024 Duo impressions may be outdated.** The 2024-05 Duo log ran the original "Tuning Release 08042023" files. Cirrus replaced them on 2024-07-02, so any sound-quality impression of the Duo from before July 2024 predates the current tuning. *Confidence: medium.*
- **Checks to tell which fix applies, cheapest first.**
  1. **Firmware state.** Run `journalctl -k -b | grep -i cs35l41`. Look for `Falling back to default firmware`, `FW EN: 0`, a missing `Calibration applied` line, or a missing or odd `Gain:` value. Any of these puts the user in the UX3405MA-2024 class: one-third to one-quarter of Windows loudness, fixed only by making the right firmware load. See Q2/Q3. *Confidence that this is the single biggest amp-side loudness factor when present: high. Probability it is present on this setup: low.*
  2. **ALSA firmware controls.** Run `amixer -c0 contents | grep -A2 "DSP1 Firmware Load"`. Both the `L0` and `R0` controls should be on. If one is off, a stale `/var/lib/alsa/asound.state` is the likely cause; the fix is `systemctl stop alsa-restore`, delete the file, reboot. This is paul-ri's fix on a UX3405MA (Q2). *Confidence: medium.*
  3. **VSPK asymmetry.** The 2024 Duo log has `VSPK: 1` on the left amp and `VSPK: 0` on the right. That is the same asymmetry a 2026 UX3405CA patch diagnoses as causing "volume drop ~1 second after starting playback due to power imbalance protection" (Q2). The fix is unmerged in mainline as of 2026-10-13. If the user's log shows the same pattern, test for a level drop about 1 s into playback, and for a quieter right channel. *Confidence it applies to the Duo: low; it is a hypothesis.*
  4. **Processing gap.** If 1–3 are clean, the remaining gap is Windows-side processing: Dolby's volume leveler and volmax boost, plus the regulator and bass management. Regenerating the Dolby presets with `--enable autogain`, and/or using JowiAoun's high-pass-plus-makeup chain, is the most likely remedy (Q3–Q5). *Confidence: medium-high.*
  5. **Experimental +2 dB.** Linking the 19.5 dB `.bincfg` the sibling models use would raise amp gain by 2 dB. No Duo owner has reported doing it, Cirrus chose not to ship one for 10431c43, and it is unsupported. *Confidence it is safe and worthwhile: low-medium.*
  6. **BIOS update.** The newest BIOS improved reliability for one Duo owner (2025-06), and BIOS .315 fixed `PUP_DONE` on the UX3405CA. *Confidence: medium for reliability, low for loudness.*

### Gaps
- No Duo-specific thread on Reddit (r/ZenbookDuo, r/zenbook, r/linux_on_laptops), the Arch wiki/BBS, Fedora Discussion, Launchpad or bugzilla could be read; all are blocked here. Searches returned no Duo loudness thread.
- What amp gain the Windows driver uses on the Duo is unknown, so I cannot say whether 17.5 dB on Linux matches Windows.
- The UX8406CA's SSID, amp configuration and firmware status were not found.
- No Duo log since 2024 that shows the VSPK fields was found. JowiAoun's quoted bind line elides them.

## 2. Other ASUS CS35L41 models: what made the speakers quiet on Linux, and what fixed it?

### Takeaway
Across ASUS CS35L41 laptops, "quiet, thin or distorted" usually meant one of these:
- The amp DSP firmware was not loading, or was falling back to the generic default. Causes: missing or incomplete BIOS `_DSD`, especially `spk-id-gpios`; a missing SSID entry in linux-firmware; or a kernel quirk not yet upstream.
- Bass or rear speaker pairs were not routed.
- The amps failed to start after a warm Windows reboot.
- A stale ALSA state turned an amp's firmware off.

The fixes were kernel quirk or property-table entries (6.7–6.14 era), linux-firmware additions (sometimes a sibling's firmware linked in by hand), `.bincfg` gain files, BIOS updates, cold shutdowns, and deleting `asound.state`. The UX3405MA, the Duo's closest sibling from the same firmware batch, is the best-documented case. With firmware falling back it ran at one-third to one-quarter of Windows volume. With the right firmware loaded (6.11, `Gain: 19`) it became "as loud as Windows".

### Cited Findings

**Zenbook 14 OLED UX3405MA** (2024 Meteor Lake, ALC294 plus 2× SPI CS35L41, SSID 10431A63)
- **smallcms #7** (paul-ri, 2024-06-22; BIOS 305, linux-firmware 20240610):
  - Stable kernel 6.9.5 gave low volume, "about one-third to one-quarter of Windows", with `Falling back to default firmware.` and `FW EN: 1, SPKID: -19`.
  - Mainline 6.10.0-rc3 with a patch loaded `cs35l41-dsp1-spk-prot-10431a63.wmfw`, logged `Calibration applied: R0=10639` and `Firmware Loaded - Type: spk-prot, Gain: 19`, and played at high volume.
  - 2024-07-29, kernel 6.10.1: "considerably louder", though still not as loud as Windows.
  - 2024-10-15, kernel 6.11: "as loud as Windows" (matplinta). adpadillar found loudness fixed on Ubuntu 24.10 with 6.11, but warm boots from Windows still killed audio until a hard shutdown.
  - — [smallcms/asus_zenbook_ux3405ma#7](https://github.com/smallcms/asus_zenbook_ux3405ma/issues/7)
- **steffengy gist:** BIOS 304 has almost all the `_DSD` data except `spk-id-gpios`. The patch adds 10431A63, and the gist is titled "NOT NEEDED >=v6.11-rc1".
  - 2024-06-23, paul-ri: "That fixed the volume issues on the UX3405ma here."
  - 2024-07-03: a Cirrus engineer had written an upstream patch, and "They've also freshly updated the firmware for this laptop."
  - — [gist](https://gist.github.com/steffengy/aa48549f40c37acf85de7a7f9a6c0475)
- Kernel bug 218991, "CS35L41 low volume on ASUS Zenbook 14 UX3405MA", was linked 2024-06-27. A search snippet quotes it: "maximum volume on this laptop is perceptively around 1/4th of what Windows can reach". — [bugzilla 218991](https://bugzilla.kernel.org/show_bug.cgi?id=218991) **(search summary)**
- Cirrus's fix was Stefan Binding's July 2024 patch "[PATCH v1] ALSA: hda: cs35l41: Fix missing Speaker ID GPIO description in _DSD", for 10431A63. — [lkml mirror 2407.0/04053](https://lkml.iu.edu/hypermail/linux/kernel/2407.0/04053.html) **(search summary)**. It is in v6.11 as `{ "CSC3551", "10431A63", missing_speaker_id_gpio2 }`, and is absent from v6.10. — [v6.11 property table](https://github.com/torvalds/linux/blob/v6.11/sound/pci/hda/cs35l41_hda_property.c); [v6.10](https://github.com/torvalds/linux/blob/v6.10/sound/pci/hda/cs35l41_hda_property.c)
- **Copying a sibling's or a newer firmware.** smallcms's README, deprecated for kernels 6.11 and later, says that if the maximum volume is still low, symlink `cs35l41/v6.83.0/halo_cspl_RAM_revB2_29.85.0.wmfw` and `cs35l41/bincfgs/cs35l41-dsp1-19_5dB.bincfg` to the 10431a63 names, "at your own risk". — [README](https://github.com/smallcms/asus_zenbook_ux3405ma)
- **lamperez gist** (March 2023, UX3402; its SSDT approach is obsolete from kernel 6.7): when `spk-id-gpios` is missing, the driver falls back to default firmware, "resulting in very low volume and strong distortion". Relevant comments:
  - 2024-09-08, danee940 (UX3405MA, kernel 6.10.7-200.fc40): "the audio is still really quiet", "on Windows it works miles better". He was advised to wait for 6.11.
  - 2026-03-01, paul-ri (UX3405MA): a stale `/var/lib/alsa/asound.state` restored `'L0 DSP1 Firmware Load'` = false, leaving the left speaker "firmware not loaded (and very quiet)". Fix: `systemctl stop alsa-restore`, delete the file, reboot. Separately, hibernation failed because the two amps share a reset pin; his workaround patch, filed as bugzilla 221161, gives "both speakers at full volume now".
  - 2026-02-11, turtleizzy (Zenbook 14): after a Windows restart the speakers are too quiet "with added DISTORTION". "The 6.8 LTR will simply not work well", and 6.14 works perfectly with a full shutdown.
  - — [lamperez gist](https://gist.github.com/lamperez/862763881c0e1c812392b5574727f6ff)

**Zenbook 14 UX3405CA** (2025 variant, same SSID 10431A63; all from mailing-list mirrors I could not open)
- August 2026 patch threads describe the problem as follows. ACPI sets `cirrus,gpio1-func` to VSPK on the left amp but leaves it unused on the right. The right channel therefore binds with `VSPK: 0`, and about 1 s after playback starts the volume drops "due to power imbalance protection". — [v1 thread](https://ratatoskr.run/alsa-devel/2026/08/17356923/t) **(search summary)**
- v1 forced internal boost. Stefan Binding objected that the laptop uses external boost and that overriding the `_DSD` as internal "can damage the amplifiers", and Takashi Iwai declined v1. v2 by Gemayel Lira enables VSPK on GPIO1 only where ACPI left it unused. Tested on 7.0.0-27-generic, both amps then read `VSPK: 1, SPKID: 1`. — [v2 thread](https://ratatoskr.run/linux-sound/2026/08/17417452/t) **(search summary)**
- No such code is in torvalds/linux master's `cs35l41_hda.c` as of 2026-10-13: GPIO1 is handled only as NOT_USED, VSPK_SWITCH or SYNC from `_DSD`. — [cs35l41_hda.c](https://github.com/torvalds/linux/blob/master/sound/hda/codecs/side-codecs/cs35l41_hda.c)
- A UX3405CA `PUP_DONE` timeout report was withdrawn on 2026-08-05. Updating from BIOS UX3405CA.314 (2025-11-20) to .315 (2026-01-21) "fixed it completely"; the reporter called it an ACPI/firmware bug, not a kernel timeout problem. — [alsa-devel thread](https://ratatoskr.run/alsa-devel/2026/08/17368731/t) **(search summary)**

**Other ASUS laptops**
- **ExpertBook P5405CSA (10431F63):**
  - Feb 2025: owners added `ALC245_FIXUP_CS35L41_SPI_2`. Without SSID firmware the log reads `Falling back to default firmware.` and `… FW EN: 1, SPKID: -19`. LK7R copied the Windows tuning files and notes the "default without .bincfg is 17db".
  - 2025-02-27, cristianlivella: "Maybe the volume is a bit lower compared to Windows … Still, it's good enough."
  - The quirk was merged in 6.14 (reported 2025-03-27).
  - — [lamperez gist](https://gist.github.com/lamperez/862763881c0e1c812392b5574727f6ff)
- **ROG Strix SCAR 18 G834JZR (10433a40):** quiet and lacking bass compared with Windows. Both amps log `Falling back to default firmware` even though the firmware directory has symlinks pointing 10433a40 at 10433a30. A reply points to a kernel patch set, and the thread is marked [SOLVED]. — [Arch BBS 305623](https://bbs.archlinux.org/viewtopic.php?id=305623) **(search summary)**; [CachyOS forum](https://discuss.cachyos.org/t/audio-help-asus-rog-strix-scar-18-g834jzr-alc285-2x-cs35l41-poor-speaker-sound-firmware-issues/8935) **(search summary)**. Mainline now lists `10433A40` with `generic_dsd_config`. — [property table](https://github.com/torvalds/linux/blob/master/sound/hda/codecs/side-codecs/cs35l41_hda_property.c)
- **ROG Flow Z13 2025 (GZ302EA 10431fb3, GZ302EAC 10431514):**
  - A dev.to investigation found "significantly lower" volume and quality on Fedora 43 than on Windows, and later an amp probe I2C failure. — [investigation](https://dev.to/ankk98/rog-flow-z13-2025-linux-audio-quality-investigation-3ggk) **(search summary)**
  - The same author's later setup notes say the Cirrus DSP now loads "with proper gain", around the kernel 7.0 release. — [setup notes](https://dev.to/ankk98/asus-rog-flow-z13-2025-linux-setup-notes-1k35) **(search summary)**
  - The GZ302EAC quirk was posted in March 2026. — [lkml mirror 2603.1/12440](https://lkml.iu.edu/hypermail/linux/kernel/2603.1/12440.html) **(search summary)**; [Bazzite #4650](https://github.com/ublue-os/bazzite/issues/4650)
  - linux-firmware gives both SSIDs a 15.5 dB `.bincfg`. — [WHENCE](https://gitlab.com/kernel-firmware/linux-firmware/-/blob/main/WHENCE)
  - A Level1Techs user found that replacing the Cirrus firmware files made the sound noticeably better. — [Level1Techs](https://forum.level1techs.com/t/flow-z13-asus-setup-on-linux-may-2025-wip/229551) **(search summary)**
- **ROG Zephyrus G14 GA402NJ (2023), asusctl #375** (2023-07-08; Ubuntu 22.04, kernel 5.19, ALC285): "very thin and very low … 5% of the normal speaker power … like a telephone handset". Closed 2024-04-17; the comments need a login, so I could not see the resolution. — [asusctl #375](https://gitlab.com/asus-linux/asusctl/-/work_items/375)
- **ROG Zephyrus G14 audio (Arch BBS 306066, [SOLVED]):** an "AMP speaker" mixer volume with a −100 to +12 dB range had to be set to 0 dB. The amp type is not confirmed as CS35L41. — [Arch BBS 306066](https://bbs.archlinux.org/viewtopic.php?id=306066) **(search summary)**
- **G14 2025 GA403, asusctl #649** (2025-05-17): the volume keys move `Speaker Playback Volume` while `AMP1/AMP2 Speaker Playback Volume` (0–448, 0.25 dB steps from −100 dB) set the real loudness. This is a different amp driver from cs35l41-hda. — [asusctl #649](https://gitlab.com/asus-linux/asusctl/-/work_items/649)
- **Bass and second speaker-pair quirks.** In mainline:
  - UM5606WA (0x1df3) and UM5606KA (0x1264) use `ALC294_FIXUP_BASS_SPEAKER_15`.
  - GU605M, GA605W and H7606W use `ALC285_FIXUP_ASUS_GU605_SPI_SPEAKER2_TO_DAC1`.
  - UM6702RA uses `ALC285_FIXUP_ASUS_I2C_SPEAKER2_TO_DAC1`.
  - G634JY/JZ uses `ALC285_FIXUP_ASUS_SPI_REAR_SPEAKERS`.
  - — [alc269.c](https://github.com/torvalds/linux/blob/master/sound/hda/codecs/realtek/alc269.c)
  - The UM5606KA bass fixup was posted in March 2025. — [lkml mirror 2503.3/01966](https://lkml.iu.edu/hypermail/linux/kernel/2503.3/01966.html) **(search summary)**
  - Luke Jones's July 2024 patch moved the remaining Strix models to the rear-speaker fixup and reported them "confirmed to work". — [patchew](https://patchew.org/linux/20240723011224.115579-1-luke@ljones.dev) **(search summary)**
  - The Duo itself uses the plain two-amp `ALC245_FIXUP_CS35L41_SPI_2`, and its codec autoconfig shows a single speaker line-out on pin 0x17. — [Duo dmesg](https://gitlab.com/asus-linux/asusctl/uploads/7a57ee0864eb3e0ea9bc44d34cc4e62d/dmesg.log)
- **Zenbook UM3402YA (I2C, 10431E12):** the right speaker goes silent after suspend, logging `CS35L41 Bound - SSID: 10431E12, … CH: R, FW EN: 0`. The fix is a systemd sleep hook that unloads and reloads the modules (2026-02/03). — [lamperez gist](https://gist.github.com/lamperez/862763881c0e1c812392b5574727f6ff); [ArchWiki UM3402YA](https://wiki.archlinux.org/title/ASUS_Zenbook_UM3402YA) **(search summary)**
- **Cirrus's own statements.** When firmware is not loaded, "audio playback will work, but the volume will be low to ensure safe operation of the CS35L41". — [patch "Prevent firmware load if SPI speed too low", Dec 2023](https://lkml.iu.edu/hypermail/linux/kernel/2312.2/05245.html) **(search summary)**. Firmware and tuning load only as a pair: without the system-specific pair the driver falls back to the default firmware and tuning, and if the default tuning is also missing the DSP is disabled. — [patch Feb 2023](https://lkml.iu.edu/hypermail/linux/kernel/2302.1/05645.html) **(search summary)**
- **Other ASUS reports:**
  - Feb 2026: Cirrus upstreamed firmware for the Zenbook 14 UM3406GA. — [Phoronix](https://www.phoronix.com/news/Linux-Audio-UM3406GA) **(search summary)**
  - 2025: distortion appeared after a linux-firmware update on an ASUS ROG with ALC294 plus CS35L41, and downgrading the firmware "fixes" it. — [Manjaro forum](https://forum.manjaro.org/t/latest-update-causes-sound-distortion-on-alc294-with-cirrus-logic/180930) **(search summary)**
  - Ubuntu bug #2084759, "Fix distorted sound output after suspend more than 30 seconds on Cirrus audio codec", was fixed in linux-oem-6.11. — [Launchpad](https://bugs.launchpad.net/ubuntu/+source/linux/+bug/2084759) **(search summary)**

### Inferences
- **Two classes of "quiet".**
  - Firmware class: fallback or no DSP, which caps amp gain at 4.5 dB or runs generic tuning. It costs about 10–15 dB, matching the one-third to one-quarter reports, and ends when the right firmware loads. On the UX3405MA that made it "as loud as Windows".
  - Processing class: firmware fine, but no Dolby-style leveler or regulator, so Linux sounds smaller and quieter.

  The user's symptom (firmware presumably loading, plus EasyEffects presets already tried) fits the second class. Q1's checks rule out the first. *Confidence: medium-high.*
- **The Duo shares the UX3405MA's 2024 firmware batch.** Both were added together in 2023, and both had tunings updated in July 2024. The difference: the UX3405MA and UM3406HA got 19.5 dB `.bincfg` files and the Duo did not. Whether Cirrus left the Duo at 17.5 dB on purpose (to match its Windows tuning) or by omission is unknown. A 2 dB difference cannot by itself explain a "significant" gap. *Confidence: low-medium.*
- **Outdated reports.** The SSDT patches (obsolete from 6.7 and 6.11), the UX3405MA low volume (fixed in 6.11), the 6.8 problems (fixed by 6.14) and the 6.9.12 SOF regression (fixed in 6.10) are all outdated for Ubuntu 26.04 on kernel 7.0. *Confidence: high.*

### Gaps
- I could not read the texts of bugzilla 218991, the UX3405CA VSPK threads, Arch BBS 305623 or 306066, the dev.to articles, or Phoronix directly (all blocked); only search summaries.
- The resolution of asusctl #375 is not visible without a login.
- I found no report of anyone trying the 19.5 dB `.bincfg` on the Duo, or the VSPK v2 patch on any model other than the UX3405CA.

## 3. Are there reports that quantify the Linux-vs-Windows loudness gap and its cause?

### Takeaway
Yes, for two causes.
- **Missing or fallback amp firmware:** UX3405MA owners measured one-third to one-quarter of Windows volume (2024). The driver code explains why: 4.5 dB PCM amp gain without DSP firmware, against 17.5 dB by default or 19.5 dB via `.bincfg` with it. Cirrus says low volume without firmware is deliberate, for amp safety.
- **Missing Windows processing:** speaker-tuning-to-easyeffects measured about +9 dB of loudness from Dolby's volume leveler, which its presets bypass by default on HDA speakers. The typical Dolby "volmax" boost is 6 dB.

Nothing quantifies the gap on the Duo itself. The only Duo measurements are JowiAoun's EasyEffects-chain gains and frequency response.

### Cited Findings
- **UX3405MA, firmware falling back (2024-06-22):** speakers at "about one-third to one-quarter of Windows volume". The correct firmware with `Gain: 19` gave "high volume", and kernel 6.11 was "as loud as Windows" (2024-10-15). — [smallcms #7](https://github.com/smallcms/asus_zenbook_ux3405ma/issues/7)
- Bug 218991: "perceptively around 1/4th of what Windows can reach". — [bugzilla 218991](https://bugzilla.kernel.org/show_bug.cgi?id=218991) **(search summary)**
- **Driver gain values:** no DSP means PCM 4.5 dB on unmute. DSP running means `tuning_gain`, default 17 = 17.5 dB, raised to 19.5 dB by the `cs35l41-dsp1-19_5dB.bincfg` that UX3405MA and UM3406HA use. That is a 13–15 dB difference between "no firmware" and "firmware". — [cs35l41_hda.c](https://github.com/torvalds/linux/blob/master/sound/hda/codecs/side-codecs/cs35l41_hda.c); [cs35l41_hda.h](https://github.com/torvalds/linux/blob/master/sound/hda/codecs/side-codecs/cs35l41_hda.h); [WHENCE](https://gitlab.com/kernel-firmware/linux-firmware/-/blob/main/WHENCE)
- Cirrus: without firmware, "volume will be low to ensure safe operation of the CS35L41". — [lkml mirror 2312.2/05245](https://lkml.iu.edu/hypermail/linux/kernel/2312.2/05245.html) **(search summary)**
- **speaker-tuning-to-easyeffects:**
  - "On HDA speakers, the volume leveler ships bypassed by default and carries most of the loudness gap: ~+9 dB measured on program material." It is bypassed because without Dolby's content analysis it can saturate on quiet-to-loud transitions. — [troubleshooting.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/troubleshooting.md)
  - "Enabling gained ~+9 dB vs bypassed on −20 dBFS RMS program material." — [adaptive-processing.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/research/adaptive-processing.md)
  - `volmax-boost` is 6 dB in 78% of "dynamic" profiles. — [cross-device-findings.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/cross-device-findings.md)
- **Non-ASUS illustration of the regulator's role:** on a Snapdragon Yoga Slim 7x without a Dolby-style per-band limiter, avoiding speaker damage meant throwing away "about 22 dB of headroom". — [cross-device-findings.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/cross-device-findings.md)
- **Duo measurements, JowiAoun, 2026-07-25:**
  - Third-octave response relative to the 630 Hz peak: 400 Hz −4.4 dB, 250 Hz −13.7, 200 Hz −18.3, 125 Hz −26.6, 1.6 kHz −8.2, 4 kHz −10.0, 8 kHz −12.3. The author's reading: "useful band starts around 300–400 Hz and everything below 200 Hz is >18 dB down".
  - An earlier 4:1 compressor with 8 dB makeup made the speakers quieter: net gain −3.1 dB at −12 dBFS and −8.3 dB at −4 dBFS.
  - The new chain measures +5.3 dB at −24 dBFS, about +3.5 dB over the old one around −14 dBFS, with peaks bounded at −1 dBFS.
  - The author's diagnosis: the amp firmware "is *protection* … not voicing". On Windows the tonal work is done above the driver in an APO, and "That gap, not the amp, is why the machine sounds worse than it does under Windows."
  - — [nix/audio.nix](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/nix/audio.nix)
- **Other subjective gap reports:**
  - TUF A16 FA608WI (ALC256, no CS35L41), 2025-04-05: "about 50% volume on Windows is similar to 80-90% volume on Linux". — [asusctl #633](https://gitlab.com/asus-linux/asusctl/-/work_items/633)
  - G14 GA402NJ, 2023: "5% of the normal speaker power". — [asusctl #375](https://gitlab.com/asus-linux/asusctl/-/work_items/375)
  - P5405CSA, 2025-02-27: "a bit lower compared to Windows". — [lamperez gist](https://gist.github.com/lamperez/862763881c0e1c812392b5574727f6ff)
  - UM3406HA with Dolby presets, 2026-10-13: "Sound is way quiter without auto gain flag." — [#134](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/issues/134)

### Inferences
- **The two gap sizes point to different causes.** The firmware class costs about 10–15 dB, roughly one-third to one-quarter perceived loudness. The processing class costs about 6–9 dB plus tonal differences. A gap that survives GNOME over-amplification with the firmware loaded fits the processing class. Over-amplification is plain digital gain after any limiter, so it clips; Dolby's leveler raises RMS loudness without clipping. *Confidence: medium.*
- **The bass-excursion explanation is plausible but unmeasured.** JowiAoun argues that bass content triggers the spk-prot excursion protection and "pulls the whole signal down". That is the author's inference, consistent with how protection DSPs work. I found no measurement of the amp's internal gain reduction on any ASUS laptop. *Confidence: low-medium.*

### Gaps
- No measurement compares the Duo's maximum SPL or LUFS on Windows and Linux at the same position.
- The gain the Windows Cirrus driver applies on the Duo (17.5 or 19.5 dB, or anything else) is undocumented in the sources found.

## 4. Has anyone published EasyEffects presets, impulse responses or measurements specifically for the Zenbook Duo, or a Duo-specific success story?

### Takeaway
One Duo-specific chain exists: JowiAoun's `duo speaker-dsp` "duo-speakers" EasyEffects chain (UX8406MA, Ubuntu 24.04, from July 2026). It is a high-pass, bass enhancer, positive-net-gain compressor and limiter, backed by documented DMIC measurements. It is tested on one unit only and deliberately leaves the voicing EQ unset. I found no Duo impulse responses and no independent "sounds like Windows now" Duo story. The speaker-tuning-to-easyeffects confirmed-device list does not include the Duo.

### Cited Findings
- JowiAoun's README claims the project makes "the speakers get the voicing they have under Windows". It describes "Speaker voicing: high-pass, bass psychoacoustics, staged compressor, limiter", marked "✅ measured". The status note reads "in daily use since July 2026 on Ubuntu 24.04 … only one machine has run it so far". The chain is opt-in: `./install.sh --user --speaker-dsp`, or `duo speaker-dsp install`. — [README](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/README.md)
- The chain, as defined in `lib/speaker_dsp.py` (preset name `duo-speakers`):
  - High-pass filter: 120 Hz, slope x3. The author warns that leaving out `slope` "is a no-op that measures FLAT".
  - Bass enhancer: amount 6, scope 200 Hz, floor 40 Hz.
  - Downward compressor: threshold −20 dB, ratio 2:1, knee −6, makeup 9 dB, attack 10 ms, release 150 ms.
  - Limiter: −1 dBFS, gain-boost off, lookahead 5 ms.
  - — [lib/speaker_dsp.py](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/lib/speaker_dsp.py)
- Practical pitfalls the author documents for EasyEffects 8:
  - `--load-preset` on the daemon's command line is a silent no-op on a fresh database, so the project seeds `~/.config/easyeffects/db` directly.
  - An enum written as a label in the database is silently ignored. Seeding `type=High-pass` turned the filter into a low-pass: measured −24 dB at 1 kHz with the bass boosted 13 dB.
  - EasyEffects 8 reads presets from `~/.local/share/easyeffects/output`.
  - — [nix/audio.nix](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/nix/audio.nix)
- "Voicing EQ is the knob left deliberately unset: the response above is not calibrated enough to derive a corrective curve from." — [nix/audio.nix](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/nix/audio.nix)
- **Conflicting description of the Windows processing.** JowiAoun says Windows uses "ASUS/harman-kardon's APO". The user's Windows driver ships a Dolby DAX3 tuning, `DEV_0294_SUBSYS_10431C43_PCI_SUBSYS_1C431043.xml`, per the task brief. — [HARDWARE.md#speakers](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/docs/HARDWARE.md#speakers). Both could be true: Harman Kardon branding with Dolby processing.
- The speaker-tuning-to-easyeffects "Supported devices" table, fetched 2026-10-13, lists no Zenbook Duo or UX8406. Its ASUS entries are the TUF A15 FA507NV, the Zenbook 14 UX3405CA/UX3405MA and the Zenbook Pro 16X UX7602BZ. — [README](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects)
- A GitHub repository search for "zenbook duo easyeffects" returned no repositories (2026-10-13). — [GitHub search](https://github.com/search?q=zenbook+duo+easyeffects&type=repositories)

### Inferences
- **The two approaches complement each other.** The Dolby-derived presets supply speaker EQ, a regulator and a limiter; on HDA they include no bass enhancer and bypass autogain. JowiAoun's chain supplies a high-pass, a bass enhancer and positive makeup gain, but no EQ. Combining them, for example adding a high-pass before the Dolby chain, needs care to avoid double limiting. No one has reported trying it. *Confidence: low-medium.*
- **The Duo has no independent success story yet.** JowiAoun's "voicing they have under Windows" is the author's own claim, from one unit, without an A/B against Windows. *Confidence: high that no independent confirmation exists in the sources searched.*

### Gaps
- No Duo impulse responses (for example, WASAPI loopback captures of the Windows Dolby output) were found.
- I could not search Reddit or EasyEffects community-preset collections for Duo presets (Reddit blocked).

## 5. What have users of speaker-tuning-to-easyeffects reported, especially on ASUS laptops?

### Takeaway
ASUS users with the same ALC294 plus CS35L41 generation as the Duo (UX3405MA/CA, UM3406HA) report that the presets work, with no detailed Windows comparisons. One sibling-model owner (UM3406HA, 2026-10-13) reported the key point for the user: "way quiter without auto gain flag", and "almost perfect" with `--enable autogain`. The project's own docs say the default bypassed leveler accounts for about 9 dB of the gap. One ASUS Vivobook report shows that ASUS Dolby tunings can carry deep regulator thresholds that cause bursts or pumping; `--disable volmax --disable regulator` or `--volmax-slot output-gain` are the documented workarounds. No Duo report exists in the tracker.

### Cited Findings
- **Project claims and chain.** The README says "Confirmed on over 40 laptops from ASUS, Framework, Lenovo and Microsoft". The generated chain is: Convolver (FIR speaker correction), Bass Enhancer (SoundWire only), EQ, Dialog Enhancer, "Autogain: bypassed by default on HDA", Multiband Compressor, Regulator and Limiter. — [README](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects)
- **#19** (2026-05-30, Zazou-79): UX3405CA, SSID 0x10431A63, ALC294, kernel 7.0.0-22-generic, sof-hda-dsp. Title "Seems to work …". The maintainer replied: "it's not a perfect match so any feedback on notable differences is useful". No Windows comparison followed. — [#19](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/issues/19)
- **#24** (2026-06-26, kpatzwald): UX3405MA, openSUSE Tumbleweed, kernel 7.0.12-1-default. "I think It sounds much better than before." The tool's `--speaker-info` printed "(no firmware-gated amplifier detected)", although this model has CS35L41 amps. — [#24](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/issues/24)
- **#134** (2026-10-13, Cyanide4567): UM3406HA, SSID 1043:1C03, ALC294, Fedora 44, kernel 7.2.9. "Sound is way quiter without auto gain flag." "Once you run with --enable-autogain, its almost perfect." "i can still notice some differences, but only when i am looking for them." The reporter used Dolby-Detailed on both Windows and Linux. — [#134](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/issues/134)
- **#110** (2026-09-30 to 2026-10-05, arhamingo): Vivobook S14 S5406, 104310C4, ALC294, no smart amp detected; Fedora 44, kernel 7.2.7, PipeWire 1.6.9, WirePlumber 0.5.17, EasyEffects 8.3.0 Flatpak.
  - "Sometimes, the sound just bursts." Adding `--disable volmax --disable regulator` reduced the surges.
  - The maintainer traced the tuning to ASUS Dolby extension v10.123.533.43. Its regulator "starts limiting five midrange bands (328 Hz to 1 kHz) at 20–29 dB below full scale", with the +6 dB boost placed before it. He suggested an A/B with `--volmax-slot output-gain`.
  - Later the reporter heard "a lot of tinny noises when there is dialogue/voice", "only on Linux", "regardless of if EasyEffect enabled or not". The maintainer suspects hardware-level behaviour Linux does not protect against, or the 66 xruns seen.
  - — [#110](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/issues/110)
- **Other ASUS issues:** #117, Zenbook Pro 16X UX7602BZ, "works" (2026-10-08); #34, TUF A15, confirmed working; #29, Zenbook S14, open, "needs verification", 10 comments I could not read; #39, ROG Xbox Ally X, 9 comments. — [ASUS-filtered issue list](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/issues?q=is%3Aissue%20asus)
- **Non-ASUS reports on reaching Windows-level loudness:**
  - #25, ThinkPad E14 Gen 2: "verified close-to-Windows: needs `--enable autogain`, plus to taste a raised Autogain *Target* … and desktop volume >100%".
  - #44, Yoga Slim 7 14ARE05: "on par with Windows with `--volmax-slot output-gain`".
  - #36: the reporter recommends autogain.
  - — [README device table](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects)
- **Official "correct but too quiet" steps, in order:**
  1. `--enable autogain` (about +9 dB; can saturate). Optionally raise the Autogain Target. If enabling Autogain by hand on an older preset, set its Silence threshold to about −50 dB.
  2. `--enable level-restore`, experimental (#50), if the preset is quieter than bypass.
  3. Allow volume above 100%, e.g. `gsettings set org.gnome.desktop.sound allow-volume-above-100-percent true` or `wpctl set-volume @DEFAULT_AUDIO_SINK@ 1.25`.
  4. Set Master, PCM and Speaker to 100% in alsamixer.
  5. `--volmax-slot output-gain` on devices with an aggressive regulator.
  6. If the speakers are "thin and quiet even with EasyEffects off", run `--speaker-info` to check for missing amp firmware. Issue #27 shows firmware extracted from a Windows driver; that device is not an ASUS.
  - — [troubleshooting.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/troubleshooting.md)
- The repository has no GitHub Discussions; the Discussions page returns 404. — [discussions URL](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/discussions)

### Inferences
- **Autogain is the first thing to change.** The user's Dolby-Balanced, Detailed and Warm presets were most likely generated with defaults, which leave autogain bypassed on HDA speakers. That alone may explain much of the shortfall. Regenerating with `--enable autogain` is the first step, then `--volmax-slot output-gain`, or `--disable regulator` if pumping or bursts appear. *Confidence: medium-high*, based on the documented default and the UM3406HA report, a sibling with the same codec, amp family and 2024 firmware batch.
- **Check the amp firmware with journalctl, not the tool.** The tool's amp-firmware check may not detect SPI-attached CS35L41 amps on ASUS laptops (the UX3405MA's #24 output). The user should verify firmware load with `journalctl` rather than rely on `--speaker-info`. *Confidence: medium.*
- **No Duo report exists in the tracker.** None appears on the issue pages I checked: the first page of all issues and the ASUS-filtered list. A Duo device report from the user would be the first. *Confidence: high.*

### Gaps
- I could not read the content of #29 (Zenbook S14) or #39 (Xbox Ally X), or pages 2–4 of the 82-issue list beyond the ASUS filter.
- No ASUS reporter gave a measured comparison with Windows; all ASUS feedback is subjective.
