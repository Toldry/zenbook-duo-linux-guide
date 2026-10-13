# Userspace volume chain (ALSA → SOF DSP → PipeWire/WirePlumber → GNOME → EasyEffects) and speaker hardware of the ASUS Zenbook Duo UX8406MA (SSID 1043:1C43)

Scope note: research done 2026-10-13. Source files were read from GitHub mirrors (torvalds/linux master, PipeWire/pipewire master, PipeWire/wireplumber master, alsa-project/alsa-ucm-conf master and tags, GNOME mirrors, wwmm/easyeffects master, thesofproject/sof and sof-bin). Line numbers are as of that date and may drift. Several review and spec sites (notebookcheck, asus.com, rtings, laptopmedia, ifixit, linux-hardware.org, bugzilla.kernel.org, lore.kernel.org, gitlab.freedesktop.org, gitlab.gnome.org) could not be fetched from this environment (proxy or DNS refusal). For those, only search-engine snippets were available; they are marked "(search snippet only)".

Big-picture summary for the report writer:
1. **Audio path on this laptop.** The UX8406MA runs Intel SOF (`sof-audio-pci-intel-mtl`, card `sof-hda-dsp`). PipeWire therefore uses **ALSA UCM** profiles, not the ACP `analog-output-speaker.conf` path files. At 100% volume the UCM path puts the codec's `Speaker` and `Master` controls at 0 dB. Three volume controls in the SOF DSP are **outside** what PipeWire controls; they default to 0 dB but should be checked.
2. **SOF loudness processing in the DSP.** The SOF DSP topology has a speaker DRC and EQ. alsa-ucm-conf 1.2.12–1.2.15.2 switched them on for the speaker: a 100 Hz high-pass plus a strong compressor with +12.8 dB makeup. From 1.2.15.3 (the version in Ubuntu 26.04), a condition in the UCM file looks inverted. On this laptop that probably leaves the processing **un-applied**, but this was not tested, so check it with `amixer`.
3. **Over-Amplification.** GNOME's switch allows up to `PA_VOLUME_UI_MAX` = +11 dB (152.5% on the cubic scale). Everything above 100% is software gain, applied after EasyEffects' limiter. PipeWire hard-clips it when converting to integer samples. It cannot give clean extra loudness on content that already peaks near 0 dBFS.
4. **The converter's default presets.** The presets made by speaker-tuning-to-easyeffects deliberately leave out loudness stages. The Dolby volume leveler ("Autogain") is bypassed on HDA; the converter's author measured it at about +9 dB. They also apply negative EQ output gain and a −1 dBFS limiter. By the tool's own documentation, they can play **quieter than bypass**.
5. **Speaker hardware.** The Duo has two speakers (stereo, bottom-firing, harman/kardon tuned), one CS35L41 amp each (L/R). The kernel quirk for 1043:1C43 binds two SPI amps and applies **no** bass-speaker or speaker2 routing fixup. No evidence of an undriven second pair was found. The pin configuration itself was not available, so it remains to be checked on the machine.

---

## 1. How many speaker drivers does the UX8406MA have, are they all driven on Linux, does it need a "bass speaker"/"speaker2-to-DAC" quirk, and do the two CS35L41s map to L/R correctly?

### Takeaway
All evidence points to **two drivers**: one per side, bottom-firing, harman/kardon-tuned, each fed by its own CS35L41 (left amp `.0`, right amp `.1`). The mainline quirk for 1043:1C43 is a plain `ALC245_FIXUP_CS35L41_SPI_2`, with no bass-speaker or DAC-routing fixup, and no source reports missing woofers. Confirming that the BIOS pin table has only one internal-speaker pin needs a codec dump from the user's machine.

### Cited Findings
- The kernel quirk entry is `SND_PCI_QUIRK(0x1043, 0x1c43, "ASUS UX8406MA", ALC245_FIXUP_CS35L41_SPI_2)`. Its neighbours are UX5304MA (0x1c33, same fixup) and GU605M (0x1c63), which uses `ALC285_FIXUP_ASUS_GU605_SPI_SPEAKER2_TO_DAC1` — [linux master, sound/hda/codecs/realtek/alc269.c#L7902](https://github.com/torvalds/linux/blob/master/sound/hda/codecs/realtek/alc269.c#L7902)
- `ALC245_FIXUP_CS35L41_SPI_2` is only `cs35l41_fixup_spi_two`, which binds **2** `CSC3551` CS35L41 amps on SPI (`comp_generic_fixup(codec, action, "spi", "CSC3551", "-%s:00-cs35l41-hda.%d", 2)`). It does no pin override and no DAC routing — [alc269.c#L3409-L3411 and #L6657-L6660](https://github.com/torvalds/linux/blob/master/sound/hda/codecs/realtek/alc269.c#L3409)
- The bass-speaker fixups that exist for siblings:
  - `alc285_fixup_speaker2_to_dac1` "force[s] NID 0x17 (Bass Speaker) to DAC1 to share it with the main speaker". It is used by GU605M/GU605C/H7606W/GA605W/UM6702RA and others.
  - `alc294_fixup_bass_speaker_15` "disable[s] DAC3 (0x06) selection on NID 0x15 - share Speaker/Bass Speaker DAC 0x03". It is used by UM5606WA (0x1df3) and UM5606KA (0x1264).
  - Neither is applied to 0x1c43.
  - Source: [alc269.c#L2703-L2722, #L7917-L7918](https://github.com/torvalds/linux/blob/master/sound/hda/codecs/realtek/alc269.c#L2703)
- A UX8406MA owner's out-of-tree headset-mic patch gives these codec facts:
  - The codec is an **ALC294** ("autoconfig for ALC294 … inputs:" is empty).
  - The BIOS leaves the analog input pins 0x18/0x19/0x1a "unused" (0x411111f0).
  - "The existing 1043:1c43 ALC294 quirk only attaches the Cirrus CS35L41 speaker amps; no mic pin override is applied."
  - After the fix, `cat /proc/asound/cards` shows `sof-hda-dsp`.
  - Sources: [nrebolloso/zenbook-duo-ux8406ma-mic-fix README](https://github.com/nrebolloso/zenbook-duo-ux8406ma-mic-fix/blob/main/README.md); [alc269.patch](https://github.com/nrebolloso/zenbook-duo-ux8406ma-mic-fix/blob/main/alc269.patch)
- UX8406MA dmesg logs uploaded to the linuxwacom descriptor repo (Feb 2025):
  - `cs35l41-hda spi1-CSC3551:00-cs35l41-hda.0 … Cirrus Logic CS35L41 (35a40), Revision: B2` and the same for `.1`.
  - "Instantiated 2 SPI devices".
  - `sof-audio-pci-intel-mtl … Digital mics found on Skylake+ platform, using SOF driver`.
  - Amp `.1` loads `cirrus/cs35l41-dsp1-spk-prot-10431c43-spkid0-r0.bin` (tuning path `…\2024Projects\UX8406\Tuning Release\12082023\UX8406_HX-R_tuning_RDL300Only_ID.bin`), then "Calibration applied: R0=10207" and "Firmware Loaded - Type: spk-prot, Gain: 17" on both amps.
  - Source: [linuxwacom/wacom-hid-descriptors, "ASUS Zenbook Duo UX8406MA_UX8406MA" sysinfo dmesg.log files](https://github.com/linuxwacom/wacom-hid-descriptors/tree/master/ASUS%20Zenbook%20Duo%20UX8406MA_UX8406MA)
- The cs35l41-hda driver names each amp `<L|R|C><index>` from the ACPI speaker position (`channel_name[3] = { 'L', 'R', 'C' }`; `amp_name = "%c%d", channel_name[spk_pos], channel_index`). It also uses `spk_pos` as the amp's ASP RX slot, so the `r0` file on amp `.1` means that amp plays the right channel — [linux master, sound/hda/codecs/side-codecs/cs35l41_hda.c#L96, #L859-L874](https://github.com/torvalds/linux/blob/master/sound/hda/codecs/side-codecs/cs35l41_hda.c#L859)
- The kernel's CS35L41 override table (`cs35l41_config_table`) has **no** `10431C43` row (it has `10431A63` for the Zenbook 14), so the Duo's amp properties (channel, boost, GPIOs) come from its own ACPI `_DSD` — [cs35l41_hda_property.c](https://github.com/torvalds/linux/blob/master/sound/hda/codecs/side-codecs/cs35l41_hda_property.c)
- A Duo Linux project's hardware notes say:
  - "Audio | Intel SOF `sof-audio-pci-intel-mtl`; ALC294 codec + two Cirrus CS35L41 amps".
  - "Two Cirrus CS35L41 smart amps (L/R) behind the ALC294, running ASUS's `spk-prot` firmware with this unit's own calibration (R0=10223/10307). That firmware is protection … not voicing."
  - Sources: [JowiAoun/linux-on-zenbook-duo docs/HARDWARE.md](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/docs/HARDWARE.md); [nix/audio.nix](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/nix/audio.nix)
- The same project measured, on one UX8406MA (third-octave pink noise through the speakers, captured on the internal DMIC with the DMIC DRC off and EasyEffects bypassed): peak at 630 Hz (0 dB); 400 Hz −4.4; 315 Hz −8.9; 250 Hz −13.7; 200 Hz −18.3; 125 Hz −26.6; 100 Hz −29.4; 1.6 kHz −8.2; 2 kHz −10.0; 4 kHz −10.0; 8 kHz −12.3. Their reading: "the useful band starts around 300–400 Hz and everything below 200 Hz is >18 dB down". The authors warn this is "a shape, not an anechoic curve" — [nix/audio.nix](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/nix/audio.nix)
- ASUS spec page, audio section: "Smart Amp Technology, Built-in speaker, Built-in array microphone, harman/kardon (Premium) with Cortana support". The snippets did not mention Dolby Atmos — [ASUS Zenbook DUO (2024) UX8406 techspec](https://www.asus.com/laptops/for-home/zenbook/asus-zenbook-duo-2024-ux8406/techspec/) (search snippet only)
- Smartprix review of the 2024 UX8406: "dual stereo speaker setup located at the bottom … tuned by Harman Kardon and also support Dolby Atmos … audio quality is quite underwhelming". Its cons list includes "Speakers could've been louder" — [Smartprix](https://www.smartprix.com/bytes/asus-zenbook-duo-2024-review/) (search snippet only)
- Notebookcheck's UX8406MA spec listing shows "Lautsprecher: Stereo" — [notebookcheck.com UX8406MA](https://www.notebookcheck.com/Asus-Zenbook-Duo-OLED-UX8406MA.814545.0.html) (search snippet only; the speaker measurements and maximum dB(A) could not be retrieved)
- LaptopMedia's UX8406 disassembly guide says to "Detach the two fan connectors as well as the ones for the speakers" before lifting the motherboard — [LaptopMedia disassembly](https://laptopmedia.com/?p=1555228) (search snippet only)
- **Sibling model, 2025 UX8406CA:** a spec comparison lists "stereo bottom-firing speakers". **2026 UX8407AA:** "6x speakers, including 2x front-firing" — [Ultrabookreview UX8407](https://www.ultrabookreview.com/74199-asus-zenbook-duo-ux8407) (search snippet only); ASUS's press release confirms "the new six-speaker audio system" for the 2026 model — [ASUS press](https://press.asus.com/news/press-releases/asus-zenbook-duo-2026/) (search snippet only)
- **Sibling 2025 model, RTINGS:** the speakers are "passable … don't get very loud and get muddy at high volume levels" — [RTINGS UX8406 2025](https://www.rtings.com/laptop/reviews/asus/zenbook-duo-ux8406-14-inch-2025) (search snippet only)
- The speaker-tuning-to-easyeffects project keeps a generated table of kernel speaker-route quirks (`lib/data/speaker_route_quirks.py`, built from `alc285_fixup_speaker2_to_dac1` / `alc294_fixup_bass_speaker_15` users). A repository-wide search for `1c43`/`UX8406` finds the SSID only in a Windows Realtek driver-database count, not in the route-quirk data. Its research notes describe the failure mode it guards against: a "Bass Speaker" routed to a DAC with no volume control, "while only the tweeter plays" — [converter repo, docs/research/hardware-and-drivers.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/research/hardware-and-drivers.md); [tools/update_speaker_route_quirks.py](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/tools/update_speaker_route_quirks.py)

### Inferences
- **Two drivers, both driven (confidence: medium-high).** ASUS says "built-in speaker", reviews say "dual stereo … at the bottom", Notebookcheck says "Stereo". Exactly two mono CS35L41 amps exist (one `L`, one `R`), and the kernel binds exactly two. No source reports a second pair, a woofer or a tweeter. A four-driver design would normally show either four amps or a codec-driven second pin with a `Bass Speaker` control. Neither appears in the quirk table or the community repos. The 2026 UX8407's six-speaker system is a different machine.
- **No bass-speaker quirk seems needed (confidence: medium).** The siblings that needed `SPEAKER2_TO_DAC1`/`BASS_SPEAKER_15` (ROG GU605/GA605/H7606, Zenbook S16 UM5606) have a codec-driven second speaker pin. The Duo's quirk is the same plain two-amp fixup that UX5304MA and UX3402VA use. Without a codec dump this is still not proven, so the user should run the checks below. If two pins with "Fixed … Speaker" defaults exist, or a `Bass Speaker` control appears, the conclusion changes.
- **L/R mapping looks correct (confidence: medium-high).** Amp `.1` loads the `r0` tuning, so `spk_pos` = right. The driver sends ASP RX slot `spk_pos` to the amp, so the right amp plays the right channel. A `speaker-test` run settles it.
- **The bass deficit is acoustic, not a missing driver (confidence: medium).** The measured response falls 18 dB by 200 Hz. That matches tiny bottom-firing drivers, and Windows hides it with psychoacoustic bass (see the Dolby researcher's notes). It does not look like an unpowered woofer.

#### Commands to check on the user's machine (Ubuntu 26.04, kernel 7.0)
```bash
# Driver/card: expect "sof-hda-dsp"
cat /proc/asound/cards
sudo dmesg | grep -iE "sof-audio|DMICs detected|tplg|topology" | head

# How the Realtek parser saw the outputs: look for line_outs / speaker_outs / hp_outs
sudo dmesg | grep -iE "autoconfig for ALC294|line_outs|speaker_outs|hp_outs|mono:"

# Full pin table (with SOF the codec file sits under the sofhdadsp card; card0 is a symlink)
grep -E "^Node 0x(14|15|17|1b|21)|Pin Default|Conn|Connection" /proc/asound/card0/codec#0 | less
#   Internal speaker pins show "Pin Default 0x90170110"-style values: [Fixed] Speaker at Int.
#   Exactly ONE such pin (usually 0x17 on ALC294) → 2-speaker design, no bass quirk needed.
#   TWO such pins (e.g. 0x14 and 0x17) → check that both are in speaker_outs and that the second
#   one is wired to a DAC with a volume control (that is the bass-speaker bug class).

# Is there a "Bass Speaker" control at all?
amixer -c0 scontrols | grep -i -E "speaker|bass"

# Full report for sharing (alsa-utils ships it)
sudo alsa-info --no-upload --output ~/alsa-info.txt   # or: alsa-info.sh --no-upload

# Left/right check (through pipewire-alsa): should say "Front Left" from the left side
speaker-test -c 2 -t wav -l 1

# Which amp got which channel's tuning (expect ...-l0.bin on .0 and ...-r0.bin on .1)
sudo dmesg | grep -i cs35l41 | grep -iE "spk-prot|Calibration|Firmware Loaded"
```
- If a second speaker pin turns up, test a pin override without recompiling, using `hdajackretask` (package `alsa-tools-gui`). Then report the pin dump upstream so a `SND_PCI_QUIRK` change can be made (confidence: medium that this would be needed only if two speaker pins exist).

### Gaps
- No `alsa-info`/`codec#0` dump or "autoconfig for ALC294: line_outs=…" line for a UX8406MA could be found. The linuxwacom dmesg logs lack the codec autoconfig lines, and linux-hardware.org/alsa-project.org were unreachable. The GitHub mirror of hw-probe dmesg logs ([linuxhw/Dmesg](https://github.com/linuxhw/Dmesg)) has older ZenBook Pro Duo models (UX581/UX582) and the UX8402ZA, but no UX8406MA folder (checked 2026-10-13); [linuxhw/LsPCI](https://github.com/linuxhw/LsPCI) has UX8406MA probes, but only lspci output. The pin table is therefore unverified. The user's own `alsa-info` output would close this gap.
- No teardown photo or service-manual text describing driver size or count could be retrieved (iFixit and LaptopMedia were unreachable; only snippets were available).
- Notebookcheck's speaker measurements (maximum dB(A), pink-noise curve) for the UX8406MA could not be retrieved.

---

## 2. Which ALSA mixer controls exist on this SOF + ALC294 + CS35L41 setup, does PipeWire (UCM/ACP) drive every element to 0 dB at 100%, and what known pitfalls leave a control below max?

### Takeaway
On SOF, PipeWire uses UCM. At 100% sink volume, the UCM path drives the codec's `Speaker` (or `Master`) element and its `Master` element to 0 dB. Software gain only starts above 100%. The SOF DSP adds volume controls that PipeWire never touches: `Pre Mixer Analog Playback Volume`, `Post Mixer Analog Playback Volume` and `Pre Mixer Deepbuffer HDA Analog Volume`. The kernel initialises them to 0 dB, but `alsactl` restores whatever was last saved. The DSP also has a speaker DRC/EQ block that UCM switches on or off depending on the alsa-ucm-conf version. Pitfalls:
- a lowered DSP gain;
- `api.alsa.soft-mixer=true`, which leaves `Master`/`Speaker` frozen at, for example, UCM's 60% boot value (≈ −26 dB on Speaker);
- a `Bass Speaker` volume that UCM never controls (if one exists);
- the SOF DRC changing dynamics and tone.

### Cited Findings
**UCM is what PipeWire uses on this card**
- With DMICs present, the SOF driver is used ("Digital mics found on Skylake+ platform, using SOF driver" in the Duo's dmesg) — [linuxwacom UX8406MA dmesg](https://github.com/linuxwacom/wacom-hid-descriptors/tree/master/ASUS%20Zenbook%20Duo%20UX8406MA_UX8406MA)
- The `sof-hda-dsp` UCM use case includes `/HDA/HiFi-analog.conf` and then `HiFi-sof.conf` — [alsa-ucm-conf ucm2/Intel/sof-hda-dsp/HiFi.conf](https://github.com/alsa-project/alsa-ucm-conf/blob/master/ucm2/Intel/sof-hda-dsp/HiFi.conf)
- The HDA speaker UCM device:
  - It sets `PlaybackMixerElem "${var:spkvol}"` (= `Speaker` when "Speaker Playback Switch" exists) and adds `PlaybackMasterElem "Master"` unless spkvol is Master.
  - If a `Bass Speaker Playback Switch` exists, it only switches it on and off together with the Speaker switch. It does **not** include the Bass Speaker *volume*.
  - Sources: [ucm2/HDA/HiFi-spk.conf](https://github.com/alsa-project/alsa-ucm-conf/blob/master/ucm2/HDA/HiFi-spk.conf); [ucm2/HDA/HiFi-analog.conf](https://github.com/alsa-project/alsa-ucm-conf/blob/master/ucm2/HDA/HiFi-analog.conf)
- UCM init BootSequence:
  - `cset "name='Auto-Mute Mode' off"`;
  - `Master Playback Volume 60%` with its switch on;
  - `Speaker Playback Volume 60%` with its switch off;
  - `Headphone Playback Volume 60%`.
  - Source: [ucm2/HDA/init.conf](https://github.com/alsa-project/alsa-ucm-conf/blob/master/ucm2/HDA/init.conf)
- PipeWire's ACP builds the UCM volume path with `pa_alsa_path_synthesize(vol->mixer_elem)`, so the element is `volume_use = PA_ALSA_VOLUME_MERGE`. It then adds the master element with `e->volume_use = PA_ALSA_VOLUME_MERGE` — [PipeWire spa/plugins/alsa/acp/alsa-ucm.c#L1438-L1451](https://github.com/PipeWire/pipewire/blob/master/spa/plugins/alsa/acp/alsa-ucm.c#L1438); [alsa-mixer.c#L2960-L2990](https://github.com/PipeWire/pipewire/blob/master/spa/plugins/alsa/acp/alsa-mixer.c#L2960)
- How merged volumes are split: "PA will go through the list of all elements with 'volume = merge' and set the volume on the first element … divides the requested volume by the volume that was set on this element, and then go on to the next element … the remaining elements usually being set to some value next to 0dB" — [analog-output.conf.common](https://github.com/PipeWire/pipewire/blob/master/spa/plugins/alsa/mixer/paths/analog-output.conf.common)
- The hardware/software split in ACP:
  - `base_volume = pa_sw_volume_from_dB(-mixer_path->max_dB)`, so 100% equals the path's maximum dB.
  - The hardware is set as close as possible; then `new_soft_volume = real_volume / hardware_volume` is applied in software. It is skipped when within ±1% (`VOLUME_ACCURACY = PA_VOLUME_NORM/100`).
  - Sources: [acp.c#L1566-L1610 and #L1711-L1720](https://github.com/PipeWire/pipewire/blob/master/spa/plugins/alsa/acp/acp.c#L1566); [acp.c#L25](https://github.com/PipeWire/pipewire/blob/master/spa/plugins/alsa/acp/acp.c#L25)
- PipeWire's sink exposes `channelVolumes` (overall linear volume), `softVolumes` ("a volume array, one (linear) volume per channel … applied in software") and `volumeBase` as node Props — [spa/include/spa/param/props.h#L72-L87](https://github.com/PipeWire/pipewire/blob/master/spa/include/spa/param/props.h#L72); [alsa-acp-device.c#L487-L504](https://github.com/PipeWire/pipewire/blob/master/spa/plugins/alsa/alsa-acp-device.c#L487)

**Non-UCM (legacy ACP path files), only if SOF is bypassed (`snd_intel_dspcfg.dsp_driver=1`) or UCM is disabled**
- `analog-output-speaker.conf` merges `Master`, `Speaker`, `Front`, `PCM` (via `.include analog-output.conf.common`) and others. It treats `Bass Speaker` as `volume = merge` with `override-map.1 = lfe` / `override-map.2 = lfe,lfe` (mapped to the LFE channel) and selects `Auto-Mute Mode:Disabled` — [analog-output-speaker.conf](https://github.com/PipeWire/pipewire/blob/master/spa/plugins/alsa/mixer/paths/analog-output-speaker.conf); [analog-output.conf.common `[Element PCM]`](https://github.com/PipeWire/pipewire/blob/master/spa/plugins/alsa/mixer/paths/analog-output.conf.common)
- The Duo mic-fix README warns that the `snd_intel_dspcfg.dsp_driver=1` workaround removes SOF, and its installer reverts it "so SOF (and the CS35L41 speaker DSP firmware) comes back" — [mic-fix README](https://github.com/nrebolloso/zenbook-duo-ux8406ma-mic-fix/blob/main/README.md)

**SOF DSP controls in the topology this machine loads**
- For HDA-codec machines, SOF builds the topology name from `sof-hda-generic` plus `-%dch` from the NHLT DMIC count ([linux master sound/soc/sof/intel/hda.c#L1597-L1614](https://github.com/torvalds/linux/blob/master/sound/soc/sof/intel/hda.c#L1597)). Text strings extracted from the binary IPC4 `sof-hda-generic-2ch.tplg`/`-4ch.tplg` in sof-bin v2.10, v2.14 and v2.15.1 (read as data with `strings`) include:
  - `Pre Mixer Analog Playback Volume`, `Pre Mixer Deepbuffer HDA Analog Volume`, `Post Mixer Analog Playback Volume`;
  - `Post Mixer Analog Playback IIR Eq bytes`, `Post Mixer Analog Playback FIR Eq bytes`;
  - `Post Mixer Analog Playback DRC bytes`, `Post Mixer Analog Playback DRC switch`;
  - in v2.14+ also `Dmic0 Capture DRC switch`.
  - Source: [thesofproject/sof-bin v2.15.x/sof-ipc4-tplg-v2.15.1](https://github.com/thesofproject/sof-bin/tree/main/v2.15.x/sof-ipc4-tplg-v2.15.1)
- SOF gain widgets are mixer controls with `max 45` and TLV `vtlv_m90s2` (min −90.00 dB, 2.00 dB steps), so step 45 = 0 dB. Their `init_value` is `0x7fffffff` (unity) — [sof tools/topology/topology2/include/components/gain.conf](https://github.com/thesofproject/sof/blob/main/tools/topology/topology2/include/components/gain.conf)
- The kernel's SOF IPC4 control setup says: "Default, initial values: 0dB for volume controls; off (0) for switch controls" — [linux master sound/soc/sof/ipc4-topology.c#L3112-L3121](https://github.com/torvalds/linux/blob/master/sound/soc/sof/ipc4-topology.c#L3112)
- Ubuntu 26.04 ships `firmware-sof` 2025.12.2-1 (24.04: 2023.12.1-1ubuntu1.x) — [Launchpad firmware-sof](https://launchpad.net/ubuntu/+source/firmware-sof)

**SOF speaker DRC/EQ driven from UCM**
- Commit c476091 (2024-05-30, first released in **alsa-ucm-conf v1.2.12**), "UCM2: Intel: sof-hda-dsp: Control SOF processing from UCM":
  - "The speaker mode is by default set up with 100 Hz high-pass IIR. The DRC is set to a default speaker setting that boosts playback loudness. The FIR is bypassed. In the headphone mode all the processing is set to bypass and DRC switch is set off."
  - Customisation goes in `blobs/sof/product_configs/<sys_vendor>/<product_name>.conf` or, to survive package updates, `blobs/sof/user_configs/…`.
  - Source: [alsa-ucm-conf commit c476091](https://github.com/alsa-project/alsa-ucm-conf/commit/c476091a87a4cd43ad500f0f31baa4a8d35bd153)
- The default blobs are `eq_iir/highpass_100hz_0db_48khz.bin`, `eq_fir/pass.bin` and `drc/speaker_default.bin` for the speaker, and pass/passthrough for headphones. They apply when the IPC4 control `Post Mixer Analog Playback IIR Eq bytes` exists — [ucm2/Intel/sof-hda-dsp/dsp.conf](https://github.com/alsa-project/alsa-ucm-conf/blob/master/ucm2/Intel/sof-hda-dsp/dsp.conf)
- I decoded `ucm2/blobs/sof/ipc4/drc/speaker_default.bin` (148 bytes) against SOF's `struct sof_drc_params` (Q formats from `drc_user.h`). It holds:
  - enabled = 1;
  - threshold −25 dB, knee 15 dB, ratio 10:1;
  - pre-delay 6 ms;
  - `master_linear_gain` = 4.379 (**+12.83 dB** makeup).
  - Sources: [blob](https://github.com/alsa-project/alsa-ucm-conf/blob/master/ucm2/blobs/sof/ipc4/drc/speaker_default.bin); [sof src/audio/drc/drc_user.h](https://github.com/thesofproject/sof/blob/main/src/audio/drc/drc_user.h). The makeup formula is `master_linear_gain = db2mag(post_gain) * (1/ratio_base)^0.6`, an "Empirical/perceptual tuning" ([sof_drc_gen_coefs.m](https://github.com/thesofproject/sof/blob/main/src/audio/drc/tune/sof_drc_gen_coefs.m)).
  - The current example script uses different values for 'speaker_default' (threshold −30, knee 20, ratio 10, post_gain 3), so the shipped blob predates the current script ([sof_example_drc.m](https://github.com/thesofproject/sof/blob/main/src/audio/drc/tune/sof_example_drc.m)).
- Commit 34c79da (2026-01-12, first released in **v1.2.15.3**) rewrote the condition in `HiFi-sof.conf`:
  - It went from `Type ControlExists Control "name='Speaker Playback Switch'"` → `True.SectionDevice."Speaker" {SOF macro}` to `Type String Empty "${var:spkvol}"` → `True.SectionDevice."Speaker" {…}`.
  - In the same commit, `HDA/HiFi-analog.conf` defines the real Speaker device under `Empty "${var:spkvol}"` → **False**.
  - Sources: [commit 34c79da](https://github.com/alsa-project/alsa-ucm-conf/commit/34c79da9ae38e7f68f9377ad26b573916337a53f); [HiFi-sof.conf at master](https://github.com/alsa-project/alsa-ucm-conf/blob/master/ucm2/Intel/sof-hda-dsp/HiFi-sof.conf)
- In alsa-lib, a UCM `Type String` condition with `Empty` returns true when the substituted string is empty (`err = s1 == NULL || s1[0] == '\0'`) — [alsa-lib src/ucm/ucm_cond.c#L108-L121](https://github.com/alsa-project/alsa-lib/blob/master/src/ucm/ucm_cond.c#L108)
- Ubuntu 26.04 ships **alsa-ucm-conf 1.2.15.3-1ubuntu1**. Its only Ubuntu change is "Add support for CS42L43B variant (LP: #2146747)". Questing (25.10) ships 1.2.12-1ubuntu2.4 and Noble (24.04) 1.2.10-1ubuntu5.x — [Launchpad alsa-ucm-conf](https://launchpad.net/ubuntu/+source/alsa-ucm-conf); [1.2.15.3-1ubuntu1 changelog](https://launchpad.net/ubuntu/+source/alsa-ucm-conf/1.2.15.3-1ubuntu1)
- The UCM trace for debugging is `LIBASOUND_DEBUG=trace alsaucm -c hw:sofhdadsp dump text` (commit message of 5e9d9e6) — [alsa-ucm-conf commit 5e9d9e6](https://github.com/alsa-project/alsa-ucm-conf/commit/5e9d9e6e896a22e39564a0e424bcb8f4648ed7e6)

### Inferences
- **At 100% the codec mixer is at 0 dB (confidence: high).** HDA Realtek `Master` and `Speaker` both top out at 0 dB, so the path `max_dB` = 0 and `base_volume` = 100%. At 100% both elements sit at 0 dB with no software attenuation. Hardware boost above 0 dB is impossible because no merged element has positive dB. The codec mixer is therefore not what keeps the speakers below maximum, provided PipeWire controls it normally.
- **The SOF DSP gains are the controls most likely to cap volume unnoticed (confidence: medium that they are worth checking; low that they are actually lowered on the user's machine).** `Pre/Post Mixer Analog Playback Volume` (and `Pre Mixer Deepbuffer HDA Analog Volume`) are not in any UCM or PipeWire path. They default to 0 dB (45/45). `alsactl` restores the last saved values at boot, so if a tool or a user lowered them, the cap persists across reboots without showing in GNOME's slider. PipeWire opens `hw:${CardId}` device 0 (UCM `PlaybackPCM`), so the "Analog Playback" pipeline is the relevant one. The Deepbuffer gain mostly matters for other clients.
- **SOF speaker DRC/EQ by version (confidence: medium, from reading the UCM files without running them).**
  - alsa-ucm-conf 1.2.12–1.2.15.2 (e.g. Ubuntu 24.10–25.10) enables, whenever the Speaker device is active, a 100 Hz high-pass plus a DRC.
  - Static curve, computed from the decoded blob with SOF's knee formula: +12.8 dB gain below about −24 dBFS, +8.7 dB at −14 dBFS, +1.9 dB at −6 dBFS, −0.9 dB at −3 dBFS, and **−3.6 dB at 0 dBFS**.
  - On normal content this is a loudness boost; for full-scale test tones it is a ceiling.
  - In **1.2.15.3, the version in Ubuntu 26.04**, the inverted `Empty` condition most likely stops the macro from being applied to the Duo's real Speaker device, because `spkvol` = "Speaker". The DRC switch then keeps its kernel default (off) or whatever `alsactl` restored, and the EQ blobs stay at topology defaults.
  - **Ubuntu 24.04 (1.2.10)** has no UCM handling at all, so topology defaults apply.
  - Either way: (a) EasyEffects presets made from Dolby data may be stacked on an extra SOF compressor and high-pass on some versions; (b) any Windows-vs-Linux level test must record the DRC switch state.
  - The inversion looks like a regression and could be reported to alsa-ucm-conf. Confidence that it is unintended: medium.
- **`api.alsa.soft-mixer=true` freezes the hardware controls (confidence: high from source).** `pa_alsa_path_select` only writes constant volumes (`OFF/ZERO/CONSTANT`) and never `MERGE` elements ([alsa-mixer.c#L1414-L1454, #L1484-L1530](https://github.com/PipeWire/pipewire/blob/master/spa/plugins/alsa/acp/alsa-mixer.c#L1414)). With soft-mixer, `Master`/`Speaker` therefore stay wherever they were, for example UCM's boot 60%. If `Speaker` uses the usual 87 steps × 0.75 dB, 60% (step 52) is about −26 dB (assumed step size; check `amixer`).
- **`Bass Speaker` volume (only if the control exists; confidence: medium).** UCM switches it but never sets its level, so it keeps the driver or `alsactl` level. Under legacy ACP it is mapped to LFE, which a stereo sink does not have. Either way it can sit below max unless a kernel fixup routes it through the main DAC.
- **The CS35L41 amps have no user-visible gain in the mixer path.** Their gain is set by the driver/firmware ("Gain: 17" in dmesg) — the kernel researcher covers this. Everything that is checkable from userspace is listed below.

#### Commands: inspect and fix the mixer state
```bash
# All controls with their current values and dB ranges (card 0 = sofhdadsp on this laptop)
amixer -c0 contents | less          # look at every "...Volume" item: value vs max, and dB
amixer -c0 sget Master; amixer -c0 sget Speaker
amixer -c0 cget name='Pre Mixer Analog Playback Volume'      # want 45,45 (0 dB)
amixer -c0 cget name='Post Mixer Analog Playback Volume'     # want 45,45 (0 dB)
amixer -c0 cget name='Pre Mixer Deepbuffer HDA Analog Volume'
amixer -c0 cget name='Post Mixer Analog Playback DRC switch' # on = SOF compressor active
amixer -c0 cget name='Auto-Mute Mode'                        # UCM sets it off
amixer -c0 scontrols | grep -i bass                          # Bass Speaker present?

# Fix the DSP gains if they are below max, and save so alsactl restores them
amixer -c0 cset name='Pre Mixer Analog Playback Volume' 100%
amixer -c0 cset name='Post Mixer Analog Playback Volume' 100%
amixer -c0 cset name='Pre Mixer Deepbuffer HDA Analog Volume' 100%
sudo alsactl store

# A/B the SOF DRC for listening and measuring (UCM may re-apply its own value on device switch)
amixer -c0 cset name='Post Mixer Analog Playback DRC switch' off

# What UCM actually applies on this machine (verifies the 1.2.15.3 condition question)
LIBASOUND_DEBUG=trace alsaucm -c hw:sofhdadsp dump text 2>&1 | grep -iE "drc|iir|fir|Speaker" | head -40
dpkg -l alsa-ucm-conf | tail -1

# What PipeWire thinks: profile/port, hardware vs software volume split
wpctl status                                   # default sink is marked with *
wpctl inspect @DEFAULT_AUDIO_SINK@ | grep -E "node.name|api.alsa|device.profile|card.profile|api.acp"
pw-dump | jq '.[] | select(.info.props["media.class"]=="Audio/Sink")
   | {name: .info.props["node.name"], props: .info.params.Props}'
#   at 100%: channelVolumes ≈ [1,1], softVolumes ≈ [1,1]; above 100%: softVolumes > 1 (digital gain)
pactl list sinks | grep -E "Name:|Active Port|Volume:|Base Volume"
```
- **Making the SOF processing permanent:** the supported route is a UCM *user config* named after the machine's DMI vendor/product. The path is `/usr/share/alsa/ucm2/blobs/sof/user_configs/<sys_vendor>/<product_name>.conf`; the name comes from `cat /sys/class/dmi/id/sys_vendor /sys/class/dmi/id/product_name`. It can, for example, set pass/passthrough blobs or the DRC switch. That directory is what c476091 defines for user overrides (confidence: medium that a small override file works as expected; untested).

### Gaps
- No `amixer -c0 contents` dump from a real UX8406MA was found, so the exact control list (whether `PCM`, `Bass Speaker` or `Front` exist, and the `Speaker` step count) is unverified on this model.
- Whether alsa-ucm-conf 1.2.15.3 applies the SOF speaker macro on this machine is deduced from the files, not observed. One `alsaucm … dump text` run, or a `cget` of the DRC switch after boot, would settle it.
- The static DRC curve ignores attack/release behaviour; real music levels will vary somewhat.

---

## 3. What exactly does GNOME's Over-Amplification do, and why can't it raise clean maximum loudness when content already peaks near 0 dBFS?

### Takeaway
The switch sets `org.gnome.desktop.sound allow-volume-above-100-percent`. The GNOME Shell and Settings sliders then extend to `PA_VOLUME_UI_MAX` = `pa_sw_volume_from_dB(+11.0)`: 152.5% on the cubic scale, linear ×3.55, **+11.0 dB**. (A 150% setting is +10.6 dB.) Because the hardware path is already at 0 dB at 100%, all of this is digital gain in PipeWire, applied to samples after EasyEffects' limiter. Samples above full scale are clamped when PipeWire converts float to the device's integer format. Content peaking at −1 dBFS gains only about 1 dB cleanly, and the rest is hard clipping. GNOME's own label says "with reduced sound quality".

### Cited Findings
- The schema key: `allow-volume-above-100-percent`, default `false`, "Whether volume can be set above 100%, using software amplification" — [gsettings-desktop-schemas org.gnome.desktop.sound](https://github.com/GNOME/gsettings-desktop-schemas/blob/master/schemas/org.gnome.desktop.sound.gschema.xml.in)
- **GNOME 50 UI location:** Settings → Accessibility → Hearing, an `Adw.SwitchRow` titled "_Overamplification" with subtitle "Allow volume to exceed 100%, with reduced sound quality", bound to that key — [gnome-control-center gnome-50 panels/universal-access/cc-ua-hearing-page.blp](https://github.com/GNOME/gnome-control-center/blob/gnome-50/panels/universal-access/cc-ua-hearing-page.blp); [cc-ua-hearing-page.c#L165-L167](https://github.com/GNOME/gnome-control-center/blob/gnome-50/panels/universal-access/cc-ua-hearing-page.c#L165). The upstream Sound panel (gnome-46 … gnome-50) has no such switch. It only reacts to the key: `cc_volume_slider_set_is_amplified(...)` — [cc-sound-panel.c](https://github.com/GNOME/gnome-control-center/blob/gnome-50/panels/sound/cc-sound-panel.c)
- History: Ubuntu carried a patch adding the switch to the Sound panel (Didier Roche, adapted from unity-control-center). A 2023 Debian/Ubuntu merge request proposed dropping it because the option had moved to Accessibility → Hearing in GNOME 44 — [Launchpad branch](https://code.edge.launchpad.net/~didrocks/gnome-control-center/sound-above-100); [salsa MR 27](https://salsa.debian.org/gnome-team/gnome-control-center/-/merge_requests/27) (search snippets only; whether Ubuntu 26.04's GNOME Settings 50.3 still has the Sound-panel copy was not verified)
- With amplification on, the Settings slider's upper bound becomes `gvc_mixer_control_get_vol_max_amplified()` and a "100%" mark is added — [cc-volume-slider.c#L139-L143](https://github.com/GNOME/gnome-control-center/blob/gnome-50/panels/sound/cc-volume-slider.c#L139). GNOME Shell's quick-settings slider uses `maxVolume = this._control.get_vol_max_amplified()` when `allow-volume-above-100-percent` is set and shows the `audio-volume-overamplified-symbolic` icon — [gnome-shell js/ui/status/volume.js#L12, #L236-L282, #L311](https://github.com/GNOME/gnome-shell/blob/main/js/ui/status/volume.js#L236)
- `gvc_mixer_control_get_vol_max_amplified()` returns `PA_VOLUME_UI_MAX`, and `get_vol_max_norm()` returns `PA_VOLUME_NORM` — [libgnome-volume-control gvc-mixer-control.c#L3929-L3940](https://github.com/GNOME/libgnome-volume-control/blob/master/gvc-mixer-control.c#L3929)
- `#define PA_VOLUME_UI_MAX (pa_sw_volume_from_dB(+11.0))`, described as a "Recommended maximum volume to show in user facing UIs"; `PA_VOLUME_NORM` = 0x10000 ("100%, 0 dB") — [pulseaudio src/pulse/volume.h#L119-L133](https://github.com/pulseaudio/pulseaudio/blob/master/src/pulse/volume.h#L119)
- `pa_sw_volume_from_dB` → `pa_sw_volume_from_linear`, which uses "a cubic mapping" — [pulseaudio src/pulse/volume.c#L243-L274](https://github.com/pulseaudio/pulseaudio/blob/master/src/pulse/volume.c#L243)
- `wpctl` sets the WirePlumber mixer API to `"scale", 1 /* cubic */`, so `wpctl set-volume … 1.5` means 150% on the cubic scale — [wireplumber src/tools/wpctl.c#L2275](https://github.com/PipeWire/wireplumber/blob/master/src/tools/wpctl.c#L2275)
- ACP software gain above the hardware maximum: `new_soft_volume = real_volume / hardware_volume` ([acp.c#L1580-L1605](https://github.com/PipeWire/pipewire/blob/master/spa/plugins/alsa/acp/acp.c#L1580)). It appears as `softVolumes` > 1 ([props.h](https://github.com/PipeWire/pipewire/blob/master/spa/include/spa/param/props.h#L87)).
- PipeWire's float→integer conversion clamps: `FTOI(...) (type)f32_round(SPA_CLAMPF((v) * (scale) + (offs) + (noise), min, max))`, used by `F32_TO_S16`, `F32_TO_S24`, `F32_TO_S24_32` and the others — [spa/plugins/audioconvert/fmt-ops.h#L12-L16, #L51, #L69, #L108](https://github.com/PipeWire/pipewire/blob/master/spa/plugins/audioconvert/fmt-ops.h#L12)
- The converter docs confirm the ordering: "Over-amplification is digital gain applied after the preset's limiter, so extreme values can clip" — [speaker-tuning-to-easyeffects docs/troubleshooting.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/troubleshooting.md)
- EasyEffects routes app streams by setting `target.object` metadata ([wwmm/easyeffects src/pw_manager.cpp#L467](https://github.com/wwmm/easyeffects/blob/master/src/pw_manager.cpp#L467)). The desktop slider therefore keeps controlling the default (hardware) sink, which comes after EasyEffects' output.
- Streaming services normalise to about −14 LUFS, per the Duo project's notes — [JowiAoun nix/audio.nix](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/nix/audio.nix)

### Inferences
- **The numbers (confidence: high).** GNOME maximum = 1.5253 × NORM on the cubic scale = 152.5%. Linear gain is 1.5253³ = 3.55, i.e. +11.0 dB. A 150% setting (for example `wpctl set-volume @DEFAULT_AUDIO_SINK@ 1.5`) is 60·log10(1.5) = +10.6 dB. 125% is +5.8 dB and 110% is +2.5 dB.
- **Why it cannot add clean loudness (confidence: high).** The hardware is already at 0 dB at 100% (section 2), so every dB above 100% multiplies samples. Content whose peaks are at −1 dBFS clips once gain exceeds about +1 dB, and loud masters at 0 dBFS clip immediately. The overshoot is clamped at the integer conversion, which is hard clipping: harsh and buzzy. That is consistent with "sounds worse" when Over-Amplification is used to chase loudness. It also runs after EasyEffects' −1 dBFS limiter, so the preset cannot protect against it.
- **Where it does help (confidence: medium-high).** Quiet or normalised content (YouTube/streaming at about −14 LUFS with peaks a few dB below 0 dBFS) and speech gain a few dB before clipping. Clean extra loudness instead has to come from compression and limiting *before* the ceiling, i.e. a loudness stage in EasyEffects, not sink gain above 100%.
- **Practical rule (confidence: medium-high).** Keep the hardware sink at ≤100% and get loudness inside EasyEffects (Autogain/compressor makeup feeding a limiter). If Over-Amplification stays on for convenience, keep it ≤ ~110–115% and listen for distortion.

#### Commands
```bash
gsettings get org.gnome.desktop.sound allow-volume-above-100-percent
gsettings set org.gnome.desktop.sound allow-volume-above-100-percent false   # or true
wpctl get-volume @DEFAULT_AUDIO_SINK@          # 1.00 = 100% (cubic), >1.00 = software gain
wpctl set-volume @DEFAULT_AUDIO_SINK@ 1.0      # back to 100% / 0 dB hardware
```

### Gaps
- Whether Ubuntu 26.04's GNOME Settings still shows a Sound-panel "Over-Amplification" switch (the Ubuntu patch), in addition to Accessibility → Hearing, could not be checked: the Launchpad librarian was blocked. The behaviour is the same key either way.

---

## 4. How do EasyEffects presets affect loudness (input/output gain, limiter ceiling, negative pre-gain), and how can the level actually reaching the sink be checked?

### Takeaway
The converter's Dolby presets give up loudness in several places. The EQ's output gain is set to minus its largest boost. The FIR is normalised so only its loudest band reaches 0 dB. Dolby's volume leveler (Autogain) is **bypassed by default on HDA**, and the converter's author measured that stage at about +9 dB on program material. Dolby's static "volmax" boost feeds a per-band limiter, and a −1 dBFS brickwall ends the chain. By the tool's own documentation, the result can play *below bypass*. A compressor staged badly can also make loud material quieter (up to −8 dB measured on a Duo). Check levels with EasyEffects' output meter and saturation icon, `pw-top`, and a recording of the ALSA sink monitor analysed with `sox … stats`.

### Cited Findings
- The converter's chain order: Convolver (FIR speaker correction) → Bass Enhancer (SoundWire only) → Equalizer (speaker PEQ) → Dialog Enhancer → **Autogain: bypassed by default on HDA** → Multiband Compressor → Regulator (per-band limiter) → Limiter (brickwall safety net) — [converter README](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/README.md)
- "On HDA speakers, Dolby's dynamic volume leveler ships bypassed … [it] carries most of the loudness gap: ~+9 dB measured on program material … it can audibly saturate when loud sound arrives over a quiet background". The fix is to re-run with `--enable autogain` and optionally raise the Autogain *Target*. With hand-enabled Autogain, raise its *Silence threshold* to about −50 dB to avoid crackle — [docs/troubleshooting.md "correct but too quiet"](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/troubleshooting.md)
- "If it is quieter than with the preset switched off entirely … re-run with `--enable level-restore` … The impulse response is normalised so its loudest band sits at 0 dB, which drops everything else below unity. On tunings whose peak exceeds their volmax-boost, the result plays below bypass." The flag is experimental — [docs/filters.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/filters.md); [troubleshooting.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/troubleshooting.md)
- "`virtual-bass` … Windows DAX synthesizes harmonics that suggest bass small drivers can't physically produce … EasyEffects itself can't express it, so the EE preset's audio is unchanged". Only the PipeWire filter-chain converter builds it — [docs/filters.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/filters.md). The Dolby researcher covers the details.
- Generator code:
  - The PEQ gets `output_gain = -peak_boost`, with peak_boost = the largest effective boost (shelves count fully; peaking bands count as gain × min(1, 2/Q)) — [lib/preset/bands.py#L290-L310](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/lib/preset/bands.py#L290)
  - Dolby's volmax boost goes on the regulator's `input-gain` by default (`--volmax-slot output-gain` moves it after the band limiting) — [lib/preset/plugins.py#L436-L525](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/lib/preset/plugins.py#L436)
  - The final limiter: `"threshold": -1.0`, `"gain-boost": False`, lookahead 1 ms, mode "Herm Thin" — [lib/preset/plugins.py#L744-L770](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/lib/preset/plugins.py#L744)
- The converter's other loudness tips: allow volume above 100% (with the clipping caveat); "Check mixer levels. In `alsamixer`, set Master/PCM/Speaker to 100%"; on the PipeWire filter-chain route, select the speakers, not the `Dolby-… (speaker filter)` node, "since … both volumes apply"; `--volmax-slot output-gain` "can bring back bass and a little loudness that the per-band limiter takes away" (one device, issue #44) — [troubleshooting.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/troubleshooting.md)
- EasyEffects 7 cannot load these presets ("On EasyEffects 7 the speaker-correction filter loads nothing, so the preset is effectively bypassed"); the tool targets EE 8.x — [troubleshooting.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/troubleshooting.md). Ubuntu 26.04 ships easyeffects 8.1.2; Ubuntu 24.04 ships 7.1.6 — [Launchpad easyeffects](https://launchpad.net/ubuntu/+source/easyeffects)
- EasyEffects' limiter is the LSP Sidechain Stereo Limiter. "**Threshold Boost**: If enabled it applies an amount of gain to the limited signal equal to the absolute value of the Threshold. This causes the peak limited at the Threshold level to output at 0 dB." ALR can let the output exceed the threshold — [easyeffects docs/plugins/limiter.md](https://github.com/wwmm/easyeffects/blob/master/src/contents/docs/plugins/limiter.md)
- EasyEffects' Autogain is libebur128-based and targets a loudness level, with Silence threshold, history and reference settings — [docs/plugins/autogain.md](https://github.com/wwmm/easyeffects/blob/master/src/contents/docs/plugins/autogain.md). "If the audio signal coming out from the pipeline is too high … a warning icon is shown near the output level meter in the bottom bar" — [docs/user_interface/saturated.md](https://github.com/wwmm/easyeffects/blob/master/src/contents/docs/user_interface/saturated.md). EE's built-in test signal offers only "sine wave or white noise" — [docs/user_interface/testsignals.md](https://github.com/wwmm/easyeffects/blob/master/src/contents/docs/user_interface/testsignals.md)
- Measured on a UX8406MA, a downward compressor (threshold −24, 4:1, makeup +8) changed gain by +8.0/+5.5/+2.9/−0.1/−3.1/−6.1/−8.3 dB at input −40/−24/−20/−16/−12/−8/−4 dBFS. In the authors' words: "on anything louder it made the speakers *quieter*, by up to 8 dB". Their replacement:
  - high-pass 120 Hz → bass enhancer (amount 6, scope 200 Hz) → compressor (−20 dB, 2:1, knee −6, makeup +9) → limiter at −1 dBFS with gain boost **off**;
  - this measured +5.3/+4.6/+3.2/+1.3/−1.5/−4.6 dB at −24…−4 dBFS, with output peaks bounded at −1.0 dBFS.
  - They note LSP's gain boost "with it on a −1 threshold is a 0 dBFS ceiling with no true-peak headroom (measured: peak 0.000 dBFS, max sample 0.999999)".
  - Sources: [JowiAoun nix/audio.nix](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/nix/audio.nix); [lib/speaker_dsp.py](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/lib/speaker_dsp.py)
- The same project's measurement method: play stepped pink noise into `easyeffects_sink` and record the ALSA sink monitor, with and without `systemctl --user stop easyeffects`. "The monitor tap is upstream of the hardware `Speaker` control, so `amixer -c0 sset Speaker mute` keeps the test silent without changing a single measured number." EE 8 creates `ee_soe_<plugin>` nodes on demand, so `pw-dump | grep ee_soe_` is "only meaningful while audio is PLAYING"; check routing with `pw-link -l | grep -A2 ee_soe_filter`. It also warns that EasyEffects 8's database stores enum *indices*, and a label silently falls back to the default (a Filter set to "High-pass" became a low-pass) — [nix/audio.nix](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/nix/audio.nix)
- `pw-cat`/`pw-record` options: `--volume=VALUE` ("The stream volume, default 1.000") and, in recording mode, `-C | --monitor` ("record from monitor ports") — [PipeWire doc/dox/programs/pw-cat.1.md](https://github.com/PipeWire/pipewire/blob/master/doc/dox/programs/pw-cat.1.md) (master docs; the option may be newer than PipeWire 1.6.2)

### Inferences
- **Where the converter presets lose level against Windows (confidence: medium-high; the Dolby researcher owns the details):**
  - (a) Autogain/leveler bypassed, about −9 dB versus Dolby on program material;
  - (b) the negative EQ output gain;
  - (c) FIR normalisation;
  - (d) the per-band regulator with volmax feeding it;
  - (e) the −1 dBFS ceiling.
  - (a)–(c) explain "quieter than Windows". The missing virtual bass explains much of "thin".
  - Recommended order: (1) `--enable autogain`; (2) `--enable level-restore` if the preset is quieter than bypass; (3) try `--volmax-slot output-gain`.
- **Stacking with the SOF DRC (confidence: medium).** On alsa-ucm-conf versions that enable the SOF speaker DRC (section 2), the EasyEffects limiter output at about −1 dBFS hits a 10:1 compressor with +12.8 dB makeup. Peaks come down to about −3.6 dBFS and low-level detail comes up. This double processing changes the tonal and dynamic balance the Dolby-derived preset assumes, so switch the DRC off when using a full EasyEffects chain.
- **Gain staging rules for this laptop (confidence: medium-high):**
  - Keep every plugin's input/output gain at 0 unless the stage is intended as makeup.
  - Put loudness (Autogain or compressor makeup) before a single final limiter at −1 dBFS with Threshold Boost off.
  - Keep the hardware sink at 100% and Over-Amplification off.
  - Make sure `easyeffects_sink`'s own volume is 100%; in `wpctl status` it is a separate sink.
- **Measuring the level reaching the hardware (confidence: medium on exact flags):** record the hardware sink's monitor and run `sox … -n stats` on it. That gives the true digital peak/RMS after EasyEffects and after any software (over-)gain, which is exactly what reaches the SOF/codec path.

#### Commands
```bash
# Is EasyEffects in the path and running? (only while audio plays)
pw-top                                   # ee_soe_* filter nodes + the ALSA sink, with quantum/rate
pw-link -l | grep -A2 ee_soe_            # easyeffects_sink:monitor -> ee_soe_... -> alsa_output...
wpctl status                             # check "Easy Effects Sink" and the hardware sink volumes
wpctl set-volume <easyeffects_sink id> 1.0

# Digital level actually sent to the hardware sink (after EE and after sink soft-volume):
SINK=$(wpctl inspect @DEFAULT_AUDIO_SINK@ | awk -F'"' '/node.name/{print $2}')
pw-record -C --target "$SINK" /tmp/sinkmon.wav      # if -C/--monitor is unsupported, use:
#   parecord -d "$SINK.monitor" /tmp/sinkmon.wav      (pulseaudio-utils, via pipewire-pulse)
sox /tmp/sinkmon.wav -n stats 2>&1 | grep -E "Pk lev dB|RMS lev dB|Flat factor|Pk count"
#   "Pk lev dB" ≈ 0.00 with "Flat factor" > 0 → clipping before the hardware.

# A/B EasyEffects without changing anything else
systemctl --user stop easyeffects    # if run as a service; otherwise toggle global bypass in the window
```

### Gaps
- No published measurement of the converter's Dolby-Balanced/Detailed/Warm presets *for the UX8406MA* was found. The +9 dB leveler figure was measured on other devices.
- `pw-record -C` availability in PipeWire 1.6.2 was not verified; the `parecord` fallback is standard pipewire-pulse behaviour but was not re-checked in documentation here.

---

## 5. How can the user objectively compare maximum output on Windows vs Linux, to separate an amp/hardware-gain gap from a processing gap?

### Takeaway
Play identical test files at identical digital level, at 100% system and app volume, in two modes per OS: "raw" (Windows audio enhancements off; Linux with EasyEffects bypassed and the SOF DRC off) and "processed" (Dolby on; EasyEffects preset on). Measure SPL with the same phone app, at the same spot and with the same weighting. If raw ≈ raw, the gap is processing (fixable in EasyEffects). If Linux raw is lower at a moderate level such as a −12 dBFS sine, the gap is in amp gain or firmware (kernel/firmware domain) or a mixer control not at 0 dB.

### Cited Findings
- `pw-cat --playback` (= `pw-play`) plays at stream `--volume` default 1.000 — [pw-cat.1.md](https://github.com/PipeWire/pipewire/blob/master/doc/dox/programs/pw-cat.1.md)
- A 0 dBFS steady signal is **reduced by about 3.6 dB** by the UCM default SOF speaker DRC. A −24 dBFS signal is raised by +12.8 dB. This is my static-curve calculation from the decoded `speaker_default.bin`: threshold −25 dB, knee 15 dB, ratio 10, makeup +12.83 dB — [blob](https://github.com/alsa-project/alsa-ucm-conf/blob/master/ucm2/blobs/sof/ipc4/drc/speaker_default.bin); [sof_drc_gen_coefs.m](https://github.com/thesofproject/sof/blob/main/src/audio/drc/tune/sof_drc_gen_coefs.m)
- Pink noise has a crest factor of about 12 dB. Content below about 200 Hz is inaudible on these drivers "but still costs cone excursion, which is what drags the CS35L41's protection DSP in and pulls the *whole* signal down" — the Duo project's interpretation, not vendor documentation — [JowiAoun nix/audio.nix](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/nix/audio.nix)
- Measuring through the laptop's own DMIC requires the SOF DMIC DRC off and still yields "a shape, not a calibration" — [nix/audio.nix](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/nix/audio.nix)
- A sibling Meteor Lake Zenbook (UX3405MA) had a kernel bug report: "maximum volume … is perceptively around 1/4th of what Windows can reach", restored by a patched kernel — [kernel bugzilla 218991](https://bugzilla.kernel.org/show_bug.cgi?id=218991) (search snippet only; sibling model, kernel domain)

### Inferences
**Procedure (confidence: medium-high that it isolates the two gaps; the exact numbers are just sensible choices).**

1. **Make the test files once, on Linux** (sox), and copy the same files to Windows:
   ```bash
   sudo apt install sox
   sox -n -r 48000 -b 24 -c 2 sine1k_-12dBFS.wav  synth 30 sine 1000 gain -12
   sox -n -r 48000 -b 24 -c 2 sine1k_-24dBFS.wav  synth 30 sine 1000 gain -24
   sox -n -r 48000 -b 24 -c 2 pink_bp_-6pk.wav    synth 40 pinknoise sinc 200-12000 norm -6
   sox -n -r 48000 -b 24 -c 2 sweep_-12dBFS.wav   synth 20 sine 100-16000 gain -12
   for f in *.wav; do echo "$f"; sox "$f" -n stats 2>&1 | grep -E "Pk lev dB|RMS lev dB"; done
   ```
   - The band-limited pink noise (200 Hz–12 kHz) avoids sub-bass that triggers speaker protection differently on each OS.
   - The −12 and −24 dBFS sines test pure gain below any limiter.
   - Add one loud commercial music track for the real-world check.
2. **Fix the geometry.** Same table, same lid angle, keyboard in the same place (the speakers fire downward, so the table surface matters). Phone on a tripod or a stack of books about 50 cm in front of the hinge centre, at screen-bottom height. Quiet room, fans idle (let the laptop sit idle first). Same SPL app (any app works, since only relative values are needed), same weighting (A; also record C if offered), and Leq over 20–30 s. Repeat each reading 3 times and average.
3. **Windows runs:**
   - (W-raw) Sound settings → speakers → audio enhancements **off** (Dolby/Realtek effects off, if the driver honours the toggle), system volume 100, player volume 100%.
   - (W-proc) The same with enhancements and Dolby on (the default profile).
   - Play every file in both modes, using a player without its own normalisation (e.g. foobar2000 or VLC with normalisation off).
4. **Linux runs (Ubuntu 26.04):**
   ```bash
   systemctl --user stop easyeffects   # or EE global bypass
   gsettings set org.gnome.desktop.sound allow-volume-above-100-percent false
   wpctl set-volume @DEFAULT_AUDIO_SINK@ 1.0
   amixer -c0 cget name='Post Mixer Analog Playback DRC switch'   # note it, then:
   amixer -c0 cset name='Post Mixer Analog Playback DRC switch' off
   amixer -c0 contents | grep -A3 -iE "Volume'"                   # all at max / 0 dB?
   pw-play --volume 1.0 sine1k_-12dBFS.wav                         # (L-raw)
   ```
   - (L-raw) as above.
   - (L-DRC) the same with the DRC switch back on.
   - (L-proc) with EasyEffects and the chosen preset on.
5. **Interpreting the results:**
   - L-raw ≈ W-raw (within about 1–2 dB) on the −12/−24 dBFS sines → the amps get the same gain. The gap is the Windows processing: Dolby leveler, volmax and virtual bass. Close it in EasyEffects (autogain/level-restore, a staged compressor and a limiter).
   - L-raw several dB below W-raw at −24 dBFS (far from any limiter) → a gain difference upstream: a mixer or DSP control not at 0 dB (section 2), or amp gain or firmware tuning (kernel/firmware researcher's area). Note `Gain: 17` in the cs35l41 dmesg line for that comparison.
   - Equal at −24 dBFS but Linux falls behind at band-limited pink noise peaking at −6 dBFS → limiting or protection behaves differently. This is the CS35L41 spk-prot firmware/tuning question (kernel researcher), or the SOF DRC if it was left on.
   - Comparing W-proc with L-proc shows how close the preset gets, and the spectrum shows the "thin" part. Record the sweep with the phone's voice recorder from the same spot and compare spectra in Audacity (Analyze → Plot Spectrum). Only relative shapes are meaningful.
6. **Linux-only cross-check:** record the hardware sink monitor (section 4) during L-raw and L-proc. This confirms the digital level reaching the DSP/codec (e.g. −12 dBFS RMS for the sine), so any remaining SPL difference is downstream of PipeWire.

### Gaps
- No published Windows-vs-Linux SPL comparison for the UX8406MA was found.
- How the Windows driver handles the "audio enhancements off" toggle for this Realtek/Dolby package (whether Dolby and the Realtek APO are both bypassed) was not verified; the Dolby researcher may know. The converter's research suggests the Windows Realtek driver database has an `RTHDAEQ` (codec EQ) record for `10431C43` ([hardware-and-drivers.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/research/hardware-and-drivers.md), labelled there as a hypothesis-level reading). If so, part of Windows' voicing may live below the APO layer and survive "enhancements off".

---

## 6. Which WirePlumber/PipeWire settings matter here (api.alsa.soft-mixer, api.alsa.ignore-dB, volume limits, default volumes, path/profile handling)?

### Takeaway
None of them needs changing to reach full volume. Defaults give 0 dB hardware at 100%. Over 100% is software gain; there is no volume cap other than the desktop UI's. `api.alsa.soft-mixer=true` is a trap unless every hardware control is first set to max: it freezes `Master`/`Speaker` wherever they are. `api.alsa.ignore-dB` is only for drivers with wrong dB data. `api.alsa.disable-mixer-path` affects jack/path switching, not loudness. WirePlumber's default *new-route* volume is 40% (cubic), which is easy to mistake for a cap after a fresh install.

### Cited Findings
- "`api.alsa.soft-mixer = false` … Setting this option to `true` will disable the hardware mixer for volume control and mute. All volume handling will then use software volume and mute, leaving the hardware mixer untouched … The hardware mixer will still be used to mute unused audio paths." "`api.alsa.disable-mixer-path` … will disable the hardware mixer path selection." "`api.alsa.ignore-dB` … will ignore the decibel setting configured by the driver. Use this when the driver reports wrong settings." The example rule is `monitor.alsa.rules = [ { matches = [ { device.name = "~alsa_card.pci-.*" } ] actions = { update-props = { api.alsa.soft-mixer = true } } } ]` — [PipeWire doc/dox/config/pipewire-props.7.md#L60-L73, #L933-L952](https://github.com/PipeWire/pipewire/blob/master/doc/dox/config/pipewire-props.7.md); the same in [WirePlumber docs/rst/daemon/configuration/alsa.rst#L149-L163](https://github.com/PipeWire/wireplumber/blob/master/docs/rst/daemon/configuration/alsa.rst#L149)
- ACP reads `api.alsa.soft-mixer`, `api.alsa.disable-mixer-path` and `api.alsa.ignore-dB` ([acp.c#L2112-L2117](https://github.com/PipeWire/pipewire/blob/master/spa/plugins/alsa/acp/acp.c#L2112)). With soft-mixer or no dB info, "falling back to software volume control" sets `base_volume = PA_VOLUME_NORM` ([acp.c#L1695-L1701](https://github.com/PipeWire/pipewire/blob/master/spa/plugins/alsa/acp/acp.c#L1695)). Without dB data the hardware volume uses raw steps, `n_volume_steps = max_volume - min_volume + 1` ([acp.c#L1729-L1735](https://github.com/PipeWire/pipewire/blob/master/spa/plugins/alsa/acp/acp.c#L1729)). Path selection writes only `OFF/ZERO/CONSTANT` volume elements ([alsa-mixer.c#L1414-L1454](https://github.com/PipeWire/pipewire/blob/master/spa/plugins/alsa/acp/alsa-mixer.c#L1414))
- `device.routes.default-sink-volume`: "the default volume for sinks that are part of a device route … used when the route is restored and the sink does not have a previously stored volume … Default value: `0.4 ^ 3` (40% on the cubic scale)". The schema default is `0.064`, max 1.0 — [WirePlumber docs/rst/daemon/configuration/settings.rst#L82-L92](https://github.com/PipeWire/wireplumber/blob/master/docs/rst/daemon/configuration/settings.rst#L82); [src/config/wireplumber.conf#L982-L989](https://github.com/PipeWire/wireplumber/blob/master/src/config/wireplumber.conf#L982)
- Path files support `volume-limit = <volume step>` ("Limit the maximum volume by disabling the volume steps above <volume step>"). None is set on the speaker elements in `analog-output-speaker.conf`, and the UCM-synthesised path sets `e->volume_limit = -1` — [analog-output.conf.common](https://github.com/PipeWire/pipewire/blob/master/spa/plugins/alsa/mixer/paths/analog-output.conf.common); [alsa-mixer.c#L2982](https://github.com/PipeWire/pipewire/blob/master/spa/plugins/alsa/acp/alsa-mixer.c#L2982)
- Versions:
  - Ubuntu 26.04: pipewire 1.6.2, wireplumber 0.5.13, alsa-utils 1.2.15.2, gnome-control-center 50.3.
  - Ubuntu 24.04: pipewire 1.0.5, wireplumber 0.4.17, alsa-utils 1.2.9, gnome-control-center 46.7.
  - Sources: [pipewire](https://launchpad.net/ubuntu/+source/pipewire), [wireplumber](https://launchpad.net/ubuntu/+source/wireplumber), [alsa-utils](https://launchpad.net/ubuntu/+source/alsa-utils), [gnome-control-center](https://launchpad.net/ubuntu/+source/gnome-control-center)
- A Duo-specific PipeWire issue (stability, not loudness): on PipeWire 1.0.5 the SOF speaker PCM could wedge in an xrun loop ("`snd_pcm_avail after recover: Broken pipe`"). Recovery is `systemctl --user restart wireplumber pipewire pipewire-pulse`, and the project ships a minimum-quantum floor as the fix — [JowiAoun docs/HARDWARE.md](https://github.com/JowiAoun/linux-on-zenbook-duo/blob/main/docs/HARDWARE.md)

### Inferences
- **Recommended settings: leave the defaults (confidence: high).** Do not set soft-mixer or ignore-dB on this card. If soft-mixer is used as a diagnostic (to rule out a mixer bug), first run `amixer -c0 sset Master 100% unmute; amixer -c0 sset Speaker 100% unmute` and set the SOF gains to 100%. Otherwise the result is a capped "max volume", e.g. 60% Speaker ≈ −26 dB.
- **No hidden volume limit (confidence: high).** No PipeWire or WirePlumber setting caps sink volume below 100%. The only "limit" is GNOME's UI maximum (100%, or +11 dB with Overamplification). `wpctl set-volume -l <max>` limits only that command. (Flag behaviour is from general wpctl knowledge, not re-checked in this session; confidence medium.)
- **The 40% first-boot volume (confidence: medium-high).** It is just a starting value; once the user moves the slider, WirePlumber stores and restores it.
- **Config syntax.** Ubuntu 26.04 / WirePlumber 0.5 uses SPA-JSON drop-ins in `~/.config/wireplumber/wireplumber.conf.d/*.conf` with `monitor.alsa.rules` (as in the cited example). Ubuntu 24.04 / WirePlumber 0.4.17 uses Lua drop-ins (`~/.config/wireplumber/main.lua.d/51-*.lua` with `alsa_monitor.rules` and `apply_properties`). The 0.4 syntax is stated from general knowledge of WirePlumber 0.4; its docs were not fetched in this session (confidence: medium).
  ```
  # ~/.config/wireplumber/wireplumber.conf.d/51-duo-alsa.conf  (WirePlumber 0.5, Ubuntu 26.04) — diagnostic only
  monitor.alsa.rules = [
    { matches = [ { device.name = "~alsa_card.pci-0000_00_1f.3.*" } ]
      actions = { update-props = { api.alsa.soft-mixer = true } } }
  ]
  # then: systemctl --user restart wireplumber pipewire pipewire-pulse
  ```
- **Profile/port check (confidence: high).** `wpctl inspect @DEFAULT_AUDIO_SINK@` should show a UCM HiFi profile/Speaker port (node name like `alsa_output.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__Speaker__sink`; the exact name varies). If it shows a "Pro Audio" profile, PipeWire does no hardware volume handling, which can leave controls wherever they were. Switch back with `wpctl set-profile <device id> <HiFi profile index>` or in GNOME Settings → Sound.
- **Ubuntu 24.04 differences in brief (confidence: medium-high):**
  - alsa-ucm-conf 1.2.10 has no SOF DRC/EQ UCM handling;
  - WirePlumber 0.4 uses Lua config;
  - EasyEffects 7.1.6 cannot run the converter's EE8 presets (use the Flatpak EE 8);
  - Overamplification lives in Accessibility → Hearing, as on 26.04 (GNOME ≥ 44; Ubuntu may also show it in Sound);
  - PipeWire 1.0.5 has the SOF xrun-wedge issue reported by the Duo project.

### Gaps
- The `wpctl set-volume --limit` flag semantics and the WirePlumber 0.4 Lua syntax were not re-verified against documentation in this session: freedesktop.org pages were unreachable.
- No UX8406MA `wpctl inspect` / `pw-dump` output was available, so the exact sink and profile names are illustrative.
