# Methods to replicate (or beat) the Windows OEM speaker sound on Linux: ASUS Zenbook Duo UX8406MA, Ubuntu 26.04

Scope: general methods and tools. (a) Capturing the Windows processing digitally through loopback. (b) Acoustic measurement with a mic and REW. (c) An Asahi-style DSP chain. (d) EasyEffects settings for clean loudness, with speaker-safety limits. The amp driver/firmware, the Dolby XML and converter internals, and community reports are covered by other researchers. They appear here only where they affect a method.

Research date: 2026-10-13. Access notes: learn.microsoft.com, roomeqwizard.com, asahilinux.org, community.frame.work, reddit, avnirvana and kittenlabs.de were blocked from this environment. So:
- Microsoft docs were read from Microsoft's own GitHub source repositories (MicrosoftDocs/windows-driver-docs, branch `staging`, commit 2d03b8b; MicrosoftDocs/win32, branch `docs`). Both the learn.microsoft.com URL and the GitHub source URL are given.
- Asahi docs were read from github.com/AsahiLinux/docs.
- REW, forum and shop claims come from search-engine summaries of the cited pages, and are marked as such where it matters.
- Code and config facts were read directly from shallow clones of the cited repositories, current as of October 2026.

---

## Q1. Does WASAPI loopback capture the Dolby APO processing, and how do you turn a capture into an EasyEffects/PipeWire impulse response? What can't an IR capture? Who has done it?

### Takeaway
Yes, in practice. Microsoft documents loopback as the stream "being played by a rendering endpoint". In the software audio engine, that stream is the engine's output, after the per-endpoint APO chain. Two independent projects captured Dolby-processed output on Realtek+Dolby laptops through WASAPI loopback (Audacity's "(loopback)" device), and one measured the post-DAX3 signal in detail. A capture gives a good copy of Dolby's static EQ/FIR. It cannot reproduce DAX3's level-dependent parts (volume leveler, per-band regulator/limiter, virtual-bass harmonics, dialog enhancer), and those parts contaminate a naive sweep or single-impulse capture. Use stationary stimuli (pink noise or multitone) or low-level sweeps, check the result, and always follow the convolver with your own compressor/limiter.

### Cited Findings

#### What Microsoft documents about the loopback tap
- Loopback definition: "In loopback mode, a client of WASAPI can capture the audio stream that is being played by a rendering endpoint device." Loopback exists "primarily to support acoustic echo cancellation (AEC)", and other apps may use it "for capturing the system mix that is being played by the audio engine." — [Microsoft Learn: Loopback Recording](https://learn.microsoft.com/en-us/windows/win32/coreaudio/loopback-recording) (source: [MicrosoftDocs/win32 loopback-recording.md](https://github.com/MicrosoftDocs/win32/blob/docs/desktop-src/CoreAudio/loopback-recording.md), ms.date 04/16/2025)
- Software vs hardware tap: "If the hardware supports a loopback pin on the render endpoint, WASAPI uses the audio provided on this pin for the loopback stream. When the hardware does not support a loopback pin, WASAPI copies the output stream from the audio engine into the loopback application's capture buffer, in addition to copying the audio data to the hardware's render pin." — [Loopback Recording](https://learn.microsoft.com/en-us/windows/win32/coreaudio/loopback-recording)
- Other loopback rules: loopback works only on shared-mode streams ("Exclusive-mode streams cannot operate in loopback mode"). A trusted driver does not let loopback capture DRM-protected streams. "Stereo Mix / Waveout Mix / What You Hear" are vendor hardware loopback *devices*, separate from WASAPI loopback. — [Loopback Recording](https://learn.microsoft.com/en-us/windows/win32/coreaudio/loopback-recording)
- Exclusive mode skips the engine: "In exclusive mode, the application and device exchange audio data directly, without intervention by the audio engine." — [Microsoft Learn: Device Formats](https://learn.microsoft.com/en-us/windows/win32/coreaudio/device-formats) ([source](https://github.com/MicrosoftDocs/win32/blob/docs/desktop-src/CoreAudio/device-formats.md))
- APO placement:
  - Stream effects (SFX) sit "before the mix (render)" for a given mode.
  - Mode effects (MFX) are "applied after the mix (render)… for a given mode, but before the mix… of all modes".
  - Endpoint effects (EFX) are "always applied, even to raw streams… after the mix (render)… of all modes". Microsoft names "speaker protection and speaker compensation" as EFX candidates.
  - Windows 8.1 loads no RAW SFX/MFX. Windows 10 loads RAW MFX but not RAW SFX.
  - The summary diagram draws SFX, MFX and EFX all inside the "Audio Engine (MS)" box, above "Drivers".
  — [Microsoft Learn: Audio Processing Object Architecture](https://learn.microsoft.com/en-us/windows-hardware/drivers/audio/audio-processing-object-architecture) ([source](https://github.com/MicrosoftDocs/windows-driver-docs/blob/staging/windows-driver-docs-pr/audio/audio-processing-object-architecture.md), ms.date 12/13/2024; diagram [audio-apo-software-effects-summary.png](https://github.com/MicrosoftDocs/windows-driver-docs/blob/staging/windows-driver-docs-pr/audio/images/audio-apo-software-effects-summary.png))
- Modes and stream categories: apps tag streams with an audio category, and categories map to driver-defined modes. The modes are Raw, Default, Movies, Media ("default for most media streams"), Speech, Communications and Notification. Raw means "there should not be any signal processing applied to the stream". Apps cannot change or see the category-to-mode mapping. — [Microsoft Learn: Audio signal processing modes](https://learn.microsoft.com/en-us/windows-hardware/drivers/audio/audio-signal-processing-modes) ([source](https://github.com/MicrosoftDocs/windows-driver-docs/blob/staging/windows-driver-docs-pr/audio/audio-signal-processing-modes.md))
- Pre-volume tap: "By default, the loopback stream 'taps into' (listens to) the audio stream prior to any volume or muting being applied." Post-volume loopback is optional and "may not be available on all endpoints". — [Microsoft Learn: Windows 11 APIs for Audio Processing Objects](https://learn.microsoft.com/en-us/windows-hardware/drivers/audio/windows-11-apis-for-audio-processing-objects) ([source](https://github.com/MicrosoftDocs/windows-driver-docs/blob/staging/windows-driver-docs-pr/audio/windows-11-apis-for-audio-processing-objects.md))
- Hardware (offloaded) audio engines. The loopback pin "will return the audio data from the final audio engine output, if the data is encoded to a PCM format". Only for a hardware EFX that encodes to non-PCM "is the loopback stream taken directly after the hardware mixer, before the EFX stage". The stated aim is "parity with the software audio engine". — [Microsoft Learn: Hardware-Offloaded Audio Processing](https://learn.microsoft.com/en-us/windows-hardware/drivers/audio/hardware-offloaded-audio-processing) ([source](https://github.com/MicrosoftDocs/windows-driver-docs/blob/staging/windows-driver-docs-pr/audio/hardware-offloaded-audio-processing.md))
- The newer KSPROPERTY_AUDIOLOOPBACK page is internally inconsistent about the hardware-engine tap:
  - It says "The loopback pin returns mixed audio output after all signal processing has been applied".
  - It also lists the flow as "Signal Processing Output → Volume → Mute → EFX → Output", and says that with no attributes "loopback should be collected before volume and mute is applied".
  - Its KS-topology diagram draws the loopback tap after MFX and before the final VOL/MUTE, with no EFX block.
  - It is required from Windows 11 24H2.
  — [Microsoft Learn: KSPROPERTY_AUDIOLOOPBACK](https://learn.microsoft.com/en-us/windows-hardware/drivers/audio/ksproperty-audioloopback) ([source](https://github.com/MicrosoftDocs/windows-driver-docs/blob/staging/windows-driver-docs-pr/audio/ksproperty-audioloopback.md), ms.date 06/18/2024; diagram [audio-engine-ksftopology-2023.png](https://github.com/MicrosoftDocs/windows-driver-docs/blob/staging/windows-driver-docs-pr/audio/images/audio-engine-ksftopology-2023.png))

#### Measured evidence that loopback contains Dolby processing
- ThinkPad guide (shuhaowu):
  - Method: Audacity host "Windows WASAPI", playback = `Speaker (Realtek(R) Audio)`, recording = `Speaker (Realtek(R) Audio) (loopback)`, 48 kHz, 24-bit. Play a 2-s single-impulse WAV with VLC set to "Windows Multimedia Device output" and Media role "Video". Then cut the region around the peak and rename .wav to .irs.
  - Validity check: "If you see just a single peak without anything else… you probably did something wrong". A bare Dirac means no processing was captured.
  — [shuhaowu/linux-thinkpad-speaker-improvements README](https://github.com/shuhaowu/linux-thinkpad-speaker-improvements)
- Published captures in that repo, from Dolby Audio Premium / Dolby Atmos on Realtek ThinkPads: P53, X1 Nano Gen 1/Gen 2, T495, E495 and P15 Gen 1, several Dolby profiles each. — [repo tree](https://github.com/shuhaowu/linux-thinkpad-speaker-improvements)
- Reported result of Convolver + Limiter on Linux: "The sound is still quieter than Windows. Windows is also more clear". Also: "The chassis resonance I experienced on the ThinkPad X390 is gone", and "Sound quality substantially improved, although Windows + Dolby remains superior". The author found "vast differences between ThinkPad models". — [same README](https://github.com/shuhaowu/linux-thinkpad-speaker-improvements)
- Community IRS database built with the same loopback method. It has captures for Acer Aspire 4743/A315-42G, HP ProBook 445 G10 and Lenovo G40-30 (Dolby, Windows 7), plus EasyEffects JSONs. No ASUS entry. It recommends a limiter after the convolver. The project has moved to Codeberg. — [hazelshantz/Easyeffects-IRS-profiles-database](https://github.com/hazelshantz/Easyeffects-IRS-profiles-database) → [codeberg mirror](https://codeberg.org/lillianrozenwurthz/Easyeffects-IRS-profiles-database)
- EasyEffects issue #2209: a ThinkPad T14s Gen 3 AMD Dolby Atmos capture gave good sound but a large delay. The maintainer noted the IR was "above 2 seconds". Trimming removed the delay, and over-trimming hurt quality. — [wwmm/easyeffects#2209](https://github.com/wwmm/easyeffects/issues/2209)
- The most rigorous capture, from the converter project the user already tried:
  - Tool: `tools/measure_dax/` "plays a stimulus through the speaker output, captures the post-DAX3 signal via WASAPI loopback, and analyses the result".
  - Device: ThinkPad X1 Yoga Gen 7, Realtek ALC287, 17AA:22E6, with 26 DAX captures at a pinned 50% volume on 2026-06-13.
  - Pre-volume confirmed: "the DAX OFF raw transfer is −0.01 dB at 50% master volume. So WASAPI loopback taps the engine mix bus pre-volume, and the master-volume term never enters the captures."
  — [measuring-against-windows.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/research/measuring-against-windows.md); [loudness-and-limiting.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/research/loudness-and-limiting.md)

#### What a capture cannot represent: DAX3 is non-LTI (measured)
- "The volume leveler and regulator engage during capture and apply time-varying, content-adaptive gain". The measured effects:
  - The sweep's 100 ms RMS envelope varied 16–34 dB from start to end, against flat on DAX-off.
  - Multitone clipped on 4 of 6 profiles, with "the regulator engaged as a hard limiter even at −18 dBFS RMS input".
  - "At −42 dBFS the leveler is *more* aggressive, not less, because it targets a fixed loudness".
  - "The recovered 'IR' is therefore not a true linear impulse response: Farina deconvolution conflates frequency response with the time-varying gain applied during the sweep." A clean capture needs the leveler/regulator off, which Dolby Access does not offer, or "continuously-stationary stimuli".
  — [adaptive-processing.md#r-dax-lti-behaviour](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/research/adaptive-processing.md)
- The measure_dax stimulus suite, a ready-made design:
  - Exponential 20 Hz–22 kHz sweep at −18 and −42 dBFS peak.
  - Pink noise at −18/−42 dBFS RMS, plus a −60…−14 dBFS "leveler ladder".
  - 20-tone multitone at Dolby band centres.
  - Stepped sines played ascending, descending and shuffled, so the static EQ separates from the adaptive part.
  - Decorrelated and correlated stereo pink for the width probe.
  - Bass bursts at 50/80/120/180 Hz for the regulator/volmax probe.
  - Speech for the dialog-enhancer probe.
  — [tools/measure_dax/README.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/tools/measure_dax/README.md)
- Linux-side counterpart: `tools/measure_ee/` captures the live EasyEffects chain into the same format, so the EE-on-Linux and DAX-on-Windows responses can be overlaid. — [docs/README.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/README.md)
- Virtual bass is nonlinear. On the X1 Yoga, "DAX runs VBE… odd harmonics at near-fundamental amplitude on a 50 Hz tone". Pink-noise captures "would not show it". Calf BassEnhancer could not reproduce DAX-like harmonics: "historical Calf BassEnhancer capture… scores 18.43, worse than doing nothing", where emitting nothing scores 10.01. — [virtual-bass.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/research/virtual-bass.md)
- Farina's exponential-sweep method (AES 108th Convention, Paris, 2000, preprint 5093) gets the linear IR and separate harmonic-distortion IRs from one sweep. The harmonics land at negative time and can be windowed out. — [AES e-Library id 10211](https://aes2.org/publications/elibrary-page/?id=10211); [Texas Acoustics seminar summary](https://texasacoustics.org/acoustics-seminar-10-27-2000)

#### Turning a capture into an IR
- REW "Import Sweep Recordings" (File menu) builds a measurement from an offline sweep recording, per the search summary of REW's help:
  - The stimulus must be a measurement sweep saved from REW's generator, at the recorder's sample rate.
  - "Using a timing reference signal is recommended for offline measurement."
  - Supported formats are 16/24/32-bit PCM and 32/64-bit float.
  — [REW help: File menu](https://www.roomeqwizard.com/help/help_en-GB/html/file.html); [REW help: Offline Measurements](https://www.roomeqwizard.com/help/help_en-GB/html/offlinemeasurements.html)
- REW's IR export can write the measured IR, the IR after EQ filters, or a minimum-phase version, as 16/24/32-bit PCM or 32-bit float. Float is recommended, and other rates are resampled with a windowed sinc (search summary of REW help). A forum workaround for a minimum-phase IR of EQ filters is "Generate measurement from filters", then export. REW's author advises setting "Place t=0 at sample index" to 0 for minimum-phase IRs. — [REW help: File menu](https://www.roomeqwizard.com/help/help/html/file.html); [AVNirvana: can REW generate convolution wav files](https://www.avnirvana.com/threads/can-rew-generate-convolution-wav-files.12908/)
- Asahi re-exported IRs from REW "with no leading zeroes" to get a cleaner IR. — [asahi-audio commit b07bd7f](https://github.com/AsahiLinux/asahi-audio/commit/b07bd7f)
- IR lengths seen in published files (read from WAV headers):
  - Asahi FIRs at 48 kHz: J313 7,561 taps = 157.5 ms; J314 woofers 92 ms, tweeters 72 ms; mono 32-bit float. — [asahi-audio/firs](https://github.com/AsahiLinux/asahi-audio/tree/main/firs)
  - GPD Pocket 4 REW FIR: 131,072 taps = 2.73 s. — [Manawyrm/gpd-pocket-4-pipewire](https://github.com/Manawyrm/gpd-pocket-4-pipewire)
  - ThinkPad X1 Nano Gen 2 capture: 157 frames = 3.3 ms; P53 capture 40.6 ms. — [shuhaowu repo](https://github.com/shuhaowu/linux-thinkpad-speaker-improvements)
  - HiFiScan Framework IR: 22 ms. — [cab404/framework-dsp](https://github.com/cab404/framework-dsp)
- SoX can merge mono files into one multichannel file with `-M` (`--combine merge`). Ubuntu 26.04 ships sox 14.7.0.9+ds1-1. — [Ubuntu manpage sox(1), resolute](https://manpages.ubuntu.com/manpages/resolute/man1/sox.1.html); [packages.ubuntu.com sox](https://packages.ubuntu.com/resolute/sox)

#### Loading an IR in EasyEffects 8.x (Ubuntu 26.04 ships 8.1.2)
- Package: Ubuntu 26.04 "resolute" has `easyeffects` 8.1.2+ds-1 in universe. — [packages.ubuntu.com/resolute/easyeffects](https://packages.ubuntu.com/resolute/easyeffects)
- File formats: since 8.0.5, "Our convolver now supports mono and true stereo impulse response files". Since 8.0.7 it also loads SOFA files. 8.0.0 moved presets and IRs to `~/.local/share/easyeffects`. — [EasyEffects CHANGELOG](https://github.com/wwmm/easyeffects/blob/master/src/contents/docs/community/CHANGELOG.md)
- Channel handling, verified in the v8.1.2 source:
  - Accepts 1, 2 or 4 channels ("Only mono, stereo and true stereo impulse files are supported").
  - Mono is copied to both channels.
  - A 4-channel file is read as ch0 = L→L, ch1 = L→R, ch2 = R→L, ch3 = R→R. The zita `impdata_create(0,1,…)` call maps ch1 from left input to right output.
  — [convolver_kernel_manager.cpp](https://github.com/wwmm/easyeffects/blob/master/src/convolver_kernel_manager.cpp); [convolver_zita.cpp](https://github.com/wwmm/easyeffects/blob/master/src/convolver_zita.cpp)
- Convolver settings in v8.1.2:
  - `autogain` defaults to true. It peak-normalises the kernel, then scales by 1/sqrt(max channel power).
  - `irWidth` 0–200 (default 100), input/output gain ±36 dB, dry −100 dB, wet 0 dB.
  — [v8.1.2 easyeffects_db_convolver.kcfg](https://github.com/wwmm/easyeffects/blob/v8.1.2/src/contents/kcfg/easyeffects_db_convolver.kcfg); [convolver_zita.cpp apply_kernel_autogain](https://github.com/wwmm/easyeffects/blob/master/src/convolver_zita.cpp)
- Resampling pitfall: EasyEffects resamples the IR to the graph rate without gain correction. With autogain off, a 48 kHz preset "runs hot by exactly the sample-rate ratio in dB": +5.9 dB at 96 kHz and +11.8 dB at 192 kHz, isolated to the convolver. This was measured 2026-09-02 for issue #84 of the converter project, where it caused crackle. The PipeWire filter-chain path did not show it. — [easyeffects-and-pipewire.md#r-convolver-resample-gain](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/research/easyeffects-and-pipewire.md)
- UI steps: add the "Convolver" output effect, then Impulses → import the IRS → Load. The convolver applies to every output, so save a speaker preset and a separate headphone preset, and autoload them per device. — [shuhaowu README](https://github.com/shuhaowu/linux-thinkpad-speaker-improvements); EasyEffects docs [convolver.md](https://github.com/wwmm/easyeffects/blob/master/src/contents/docs/plugins/convolver.md) (Impulses, Combine, Stereo Width)

#### Loading an IR in PipeWire filter-chain (Ubuntu 26.04 ships PipeWire 1.6.2)
- Package: `pipewire` 1.6.2-1ubuntu1.1 and `wireplumber` 0.5.13-1ubuntu1. — [packages.ubuntu.com pipewire](https://packages.ubuntu.com/resolute/pipewire); [wireplumber](https://packages.ubuntu.com/resolute/wireplumber)
- Builtin `convolver` config keys:
  - `gain`, `delay`, `filename`, `offset`, `length`, `channel`, `resample_quality`.
  - `filename` can be an array of files, and "The file with the closest samplerate match" is used.
  - `convolver2` applies one input to up to 8 outputs.
  - Node types are `ladspa`, `lv2`, `builtin`, `sofa`, `ebur128`, `ffmpeg`.
  — [module-filter-chain.c docs](https://github.com/PipeWire/pipewire/blob/master/src/modules/module-filter-chain.c) (rendered at [docs.pipewire.org](https://docs.pipewire.org/page_module_filter_chain.html))
- Volume handling: "With the capture.volumes and playback.volumes properties this can be handled by a control port in the graph instead", with `min`/`max`/`scale` (linear or cubic). — [module-filter-chain.c](https://github.com/PipeWire/pipewire/blob/master/src/modules/module-filter-chain.c)

#### Windows-side tools
- The Audacity manual has a tutorial on recording computer playback on Windows with WASAPI loopback. — [Audacity Manual: Recording Computer Playback on Windows](https://manual.audacityteam.org/man/tutorial_recording_computer_playback_on_windows.html)
- Python/numpy stimulus generation, Windows capture and Linux analysis scripts exist in the converter repo: `make_stimulus.py`, `capture_dax.py`, `analyze.py`. — [tools/measure_dax](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/tree/master/tools/measure_dax)

### Inferences
- **Tap point** [High]. On a standard Realtek HDA laptop with no hardware-offload engine, WASAPI loopback is the software audio engine's output. That output already includes SFX (for the playing stream's mode), MFX and EFX. Every APO-hosted Dolby stage is therefore in the capture, and the endpoint volume is not.
  - Evidence: the "copies the output stream from the audio engine" wording, the diagram placing EFX inside the engine, and two independent Realtek+Dolby captures (shuhaowu, measure_dax).
  - Unconfirmed: whether the Zenbook Duo's Intel Meteor Lake audio exposes a hardware loopback pin. If it did, the doc ambiguity above would matter.
- **Verify on the Zenbook itself** [High]. Before deriving anything, capture the same stimulus with Dolby on and Dolby off, or across two Dolby profiles. If the captures differ, Dolby is in the loopback. This takes about 5 minutes.
- **What loopback cannot see** [Medium-High].
  - Processing after the audio engine: the CS35L41 amps' on-chip DSP (speaker protection and any tuning loaded from firmware), plus analog and acoustic effects.
  - Implication: if Linux loads the same amp firmware/tuning as Windows (another researcher's topic), the loopback difference is exactly what needs replicating in software.
  - If the amp gain or protection differs between OSes, a perfect digital match will still sound different. That case needs the acoustic method (Q2).
- **Use shared mode, not exclusive** [High]. Play the test signal in shared mode, the default for Audacity's WASAPI host and for VLC/MME. Exclusive-mode and kernel-streaming playback bypass the audio engine and therefore the APOs. Exclusive streams can't be loopback-captured anyway.
- **Voicemeeter and VB-Cable can't capture Dolby** [Medium-High]. They are separate endpoints with no Dolby APO, so they route around Dolby instead of capturing it. A Voicemeeter output sent to the speakers in KS or exclusive WASAPI mode also skips the APOs.
- **Stereo Mix** [Medium]. A Realtek "Stereo Mix" hardware loopback device, where one exists, would capture the codec's mix after the APOs. It is usually hidden or absent on modern laptop drivers, so WASAPI loopback is the practical route.
- **Stream category matters** [Medium]. MFX runs per mode, and the mode follows the player's stream category. Dolby may voice Movie/Media/Default differently. Capture with the category you care about (VLC "Media role", or a normal media player), and keep it constant between captures. shuhaowu saw no difference between Video and Music on one ThinkPad.
- **Recommended capture design for DAX3** [High for the principle; Medium for the exact values].
  1. Generate a 48 kHz, 32-bit float stimulus set:
     - 60 s of stationary pink noise at about −20 dBFS RMS.
     - An exponential sweep at −18 dBFS and another at −40 dBFS peak.
     - For a true-stereo capture, left-only and right-only versions of each.
     - REW's own saved measurement sweep if you will use REW's importer.
     - Or simply reuse `tools/measure_dax`.
  2. On Windows: Audacity, host "Windows WASAPI", playback = Speakers, recording = "Speakers (loopback)", 48 kHz, 32-bit float. Set the Dolby profile and keep Windows volume fixed (it doesn't enter the capture, but keep it constant anyway). Record each stimulus with a few seconds of silence before it.
  3. Static magnitude from pink noise: the transfer function H(f) = Pxy/Pxx (Welch cross-spectrum), smoothed to 1/12–1/6 octave. Design a minimum-phase FIR from |H|. For example, import the magnitude into REW and export a minimum-phase IR, or write about 30 lines of numpy/scipy.
  4. Use the two sweeps only as a cross-check. If the quiet and loud sweep IRs differ by more than a level offset, the leveler/regulator is active and the sweep IR must not be used raw.
  5. Trim the IR so the main peak sits within the first ~1 ms, with no leading silence. Keep roughly 50–200 ms; Asahi's FIRs are 72–158 ms.
     - Far shorter IRs, such as the 3.3 ms X1 Nano file, can't represent EQ below about 1/T ≈ 300 Hz, which is where much of the speaker voicing lives.
     - Very long IRs with leading silence add audible delay (EasyEffects #2209).
  6. True stereo: deconvolve L-only → (L→L, L→R) and R-only → (R→L, R→R), then `sox -M LL.wav LR.wav RL.wav RR.wav dolby_ts.wav`. Load the 4-channel result in EasyEffects 8.1.2. This keeps any Dolby speaker-virtualiser crossfeed that a plain stereo or mono IR loses.
  7. In EasyEffects: Convolver with autogain on, then a multiband compressor and limiter. Keep the PipeWire graph at 48 kHz, or turn autogain off only if the rate is pinned.
- **Expected accuracy** [Medium].
  - Static timbre: the steady-state EQ/FIR part should match Dolby closely. The converter matched DAX within about 1 dB RMS on pink using the XML route, which hints at what a good static model achieves.
  - Not reproduced: the leveler's loudness lift (worth up to roughly 8 dB on normal content on the X1 Yoga), the per-band regulator's bass protection at high level, virtual bass and the dialog enhancer. These have to be approximated with EasyEffects/LSP dynamics (Q4). They explain part of "still quieter and less clear than Windows".
- **Safety coupling** [Medium-High]. A low-level capture includes bass and treble boosts that Dolby's regulator pulls back dynamically at high volume. Applying such an IR statically, with no regulator-like stage, can push more low-frequency power into the speakers at full volume than Windows ever does. Always follow the convolver with bass-band compression and a limiter (see Q5).
- **Cost and time** [High]. €0, since Audacity, REW and Python are free and the user already dual-boots Windows 11. About 1–2 h for a first capture and EasyEffects setup; 3–4 h including true-stereo, level-dependence checks and A/B.
- **Digital A/B without a microphone** [Medium-High]. Run the same stimuli through the Linux EasyEffects chain and capture with the converter's `tools/measure_ee` (or `pw-record` of the sink monitor). Overlay against the Windows loopback capture to verify the digital chain objectively before any acoustic work.
- **Relation to the converter presets** [Medium]. A loopback capture is a cross-check on the converter's XML-derived presets, which the user found lacking, not a replacement. If the capture and the preset already agree digitally, the remaining gap is level/dynamics or amp-side, not EQ.

### Gaps
- Not determined: whether the UX8406MA's Windows driver stack (Intel SST/ACE + Realtek + Dolby) exposes a hardware loopback pin, and where it taps relative to Dolby's EFX. The loopback-recording page doesn't name a tap point for EFX in software engines; the inference rests on the "engine output" wording plus measured Realtek ThinkPad captures. The Dolby on/off capture check settles it in minutes.
- Not found: any published loopback IR capture for an ASUS Zenbook (Dolby or ASUS AudioWizard), or for any CS35L41-based laptop.
- Not verified: whether the Aurora deconvolution plugins for Audacity still work with current Audacity versions. Not searched further, since REW import and numpy cover the need.
- Not verified: Windows' WASAPI loopback behaviour with DRM-protected streams (irrelevant for test signals), and whether Dolby applies different processing to 44.1 kHz vs 48 kHz streams.

---

## Q2. Acoustic method: measuring Windows vs Linux with a calibrated mic (or phone) in REW and building a matching EQ

### Takeaway
Measure both OSes on the same machine, with the same mic, position and volume, and treat the Windows curve as the target. The ratio of the two measurements is what you EQ for, so most mic and room errors cancel. Even a phone works for this relative job, if its input processing can be switched off. A calibrated USB mic (UMIK-1, about €115–130) makes absolute tuning and bass work much more trustworthy. Export the EQ from REW in Equalizer APO format and import it into EasyEffects' Equalizer, or build a FIR and load it in the Convolver. Because Dolby is level- and content-adaptive, use stationary pink noise or RTA averaging for the Windows reference rather than relying only on a single sweep. Keep EQ boosts small.

### Cited Findings
- **Mic prices in EUR** (retail, from search results, prices change):
  - miniDSP UMIK-1: €129.00 incl. VAT at Heimkinowelten ([page](https://en.heimkinowelten.de/produkt/minidsp-umik-1/)); €114.95 at Rumoh ([page](https://www.rumoh.eu/accessories/measuring/1291/minidsp-umik-1)); €119.95 at SoundImports ([page](https://www.soundimports.eu/en/minidsp-umik-1.html)).
  - UMIK-2: €279.95 at SoundImports ([page](https://www.soundimports.eu/en/minidsp-umik-2.html)); €278 at UralTone ([page](https://en.uraltone.com/minidsp-umik-2-usb-c-reference-measurement-microphone.html?___store=english_2)).
  - A 2026 "UMIK-1 V3" USB-C revision is listed by Masori in USD. — [masori.de](https://masori.de/en/products/minidsp-umik-1-measurement-microphone)
- **UMIK-1 calibration**: miniDSP's guide says to enter the mic's serial number to download calibration files. Use the on-axis file when pointing at the speaker and the "_90deg" file when the mic points at the ceiling. — [miniDSP: UMIK-1 setup with REW](https://www.minidsp.com/applications/acoustic-measurements/umik-1-setup-with-rew)
- **REW on Linux with PipeWire** (single forum report, via search summary): REW worked when the PipeWire "default device" was selected for input instead of raw `plughw`. REW's UMIK-1 auto-discovery prompt tends to pick plughw, and 48 kHz was more reliable than 192 kHz. — [AVNirvana: Linux guide?](https://www.avnirvana.com/threads/linux-guide.13946/post-105609)
- **REW EQ settings** (via search summaries): the EQ window offers "Match Range" plus "Individual Max Boost" and "Overall Max Boost" limits and a "Flatness Target". One guide sets both max boosts to 0 and flatness target to 1, then clicks "Match Response to Target". — [REW help: EQ Window](https://www.roomeqwizard.com/help/help_en-GB/html/eqwindow.html); [mehlau.net: Room correction with REW using PEQ](https://mehlau.net/audio/room-correction-peq/)
- **Using a target curve and exporting**:
  - A custom target can be loaded as a text file (house curve). Filters are exported with File → Export → filter settings as text, in Equalizer APO format.
  - Keep the preamp so the peak gain stays slightly below 0 dB.
  - A wrong "DSP resolution" setting in the EQ window can double or halve the corrected range.
  — [Head-Fi: auto-EQ step-by-step](https://www.head-fi.org/threads/how-to-automatically-eq-your-headphones-to-online-measurements-a-step-by-step-guide.854773/); [miniDSP forum: REW EQ file not following curve](https://www.minidsp.com/community/threads/rew-eq-file-not-making-output-measurement-follow-room-curve.20187/)
- **REW trace arithmetic**: "all trace arithmetic is done on linear values". A/B takes phase into account, so A/B of two acoustic measurements can differ from a plain dB subtraction. Outside their range, traces count as zero, except a divisor, which counts as unity. Users suggest averaging and smoothing first for a magnitude-only difference. — [AVNirvana: Trace arithmetic issue](https://www.avnirvana.com/threads/trace-arithmetic-issue.11948/latest); [AVNirvana: Explain what trace arithmetic is doing](https://www.avnirvana.com/posts/117187)
- **EasyEffects Equalizer**:
  - It is LSP Parametric Equalizer x32, with 1–32 bands, IIR/FIR/FFT modes, split L/R channels, and an "APO" filter mode that implements Equalizer APO's textbook biquads. — [EasyEffects docs: equalizer.md](https://github.com/wwmm/easyeffects/blob/master/src/contents/docs/plugins/equalizer.md)
  - It imports APO presets (`importApoPreset`) and GraphicEQ presets (`importApoGraphicEqPreset`), and exports APO.
  - APO filter types parsed include PK, LP/HP(Q), BP, LS/LSC/HS/HSC (with 6/12 dB variants) and NO. The `Preamp:` line sets the input gain. The band count is clamped to the plugin's maximum.
  — [equalizer_apo.cpp](https://github.com/wwmm/easyeffects/blob/master/src/equalizer_apo.cpp); [equalizer.cpp](https://github.com/wwmm/easyeffects/blob/master/src/equalizer.cpp)
  - Version history: GraphicEQ import arrived in 7.0.0, APO export in 7.1.4, and an APO/GraphicEQ split-channel import bug was fixed in 8.0.5. — [CHANGELOG](https://github.com/wwmm/easyeffects/blob/master/src/contents/docs/community/CHANGELOG.md)
- **PipeWire alternatives for the same file**:
  - Builtin `param_eq` reads an AutoEQ/Equalizer-APO style file (`Preamp: … dB`, `Filter N: ON PK Fc … Hz Gain … dB Q …`). The parser only accepts `PK`, `LSC` and `HSC`.
  - `filenameX`/`filtersX` give per-channel EQ.
  - `libpipewire-module-parametric-equalizer` (since 1.0.6) builds a filter-chain sink from such a file via `equalizer.filepath`.
  — [module-filter-chain.c](https://github.com/PipeWire/pipewire/blob/master/src/modules/module-filter-chain.c); [plugin_builtin.c parser](https://github.com/PipeWire/pipewire/blob/master/spa/plugins/filter-graph/plugin_builtin.c); [module-parametric-equalizer.c](https://github.com/PipeWire/pipewire/blob/master/src/modules/module-parametric-equalizer.c)
- **HiFiScan**, an easier alternative to REW:
  - Install: `pip install -U hifiscan`. It measures with a chirp and computes "by default a phase-neutral finite impulse response (FIR)" for EasyEffects' Convolver.
  - Its laptop example found a 1 kHz case resonance "about 20 dB above average". It set the low limit to 200 Hz, chose a 22 ms impulse ("The latency added by the equalizer is halve the duration of the impulse") and a Range of 27 dB.
  - It equalizes "by attenuation only", so the volume must be raised afterwards. It can average several mic positions.
  — [erdewit/HiFiScan README](https://github.com/erdewit/HiFiScan)
- **Real laptop uses of the acoustic route**:
  - Framework 13, cab404: started from EasyEffects' guide, then made HiFiScan IRs, moving from 5 dB to 16 dB to 27 dB correction range. Gracefu found "the 27dB IR is indeed best".
  - Practical gain advice from the same repo: "the gain has to come before the compressor, not the limiter, or you will hear very audible clipping artifacts". Setting multiband band-1 makeup to 0 dB removed bass distortion.
  — [cab404/framework-dsp](https://github.com/cab404/framework-dsp); [Framework forum thread](https://community.frame.work/t/guide-framework-dsp-better-linux-audio/44645)
  - A Framework 13 user measured with a UMIK-1, the mic about a foot behind the palm rest, with absorption panels around the laptop to cut reflections. — [Framework forum: Speakers sound quality, p.2](https://community.frame.work/t/speakers-sound-quality/1078?page=2) (via search summary)
  - A user imported REW's filter export directly into EasyEffects after measuring with a UMIK-1. — [Hacker News item 49479924](https://news.ycombinator.com/item?id=49479924) (via search summary)
  - Asahi's own FIRs are made in REW. The J314 FIRs were "Balanced with UMIK-1, honkiness significantly reduced and tweeter-woofer balance improved". — [asahi-audio commit 9a1dbfb](https://github.com/AsahiLinux/asahi-audio/commit/9a1dbfb3795fb3757355cc38b1a112fbe28326a5); [commit b07bd7f](https://github.com/AsahiLinux/asahi-audio/commit/b07bd7f)
  - The GPD Pocket 4 DSP was measured with REW "with very suboptimal measurement equipment (cheap microphone, questionable audio interface)" and still showed the bass slope and a harsh ~4 kHz peak. — [kittenlabs.de GPD Pocket 4 Speaker DSP](https://kittenlabs.de/blog/2025/04/06/gpd-pocket-4-speaker-dsp/) (via search summary)
- **Phone microphones**:
  - Android's CDD defines an `UNPROCESSED` audio source with near-flat mid-band response, ≥60 dB SNR and no AGC/high-pass/echo cancellation in that path. — [Android CDD 5.11 Unprocessed audio (mirror)](https://os.unplugged.com/werunplugged/unplugged-vendor/blame/branch/main/compatibility/cdd/5_multimedia/5_11_unprocessed-audio.md)
  - On iOS, the audio-session mode decides input DSP. Developers report that `.measurement` mode turns off AGC and the high-pass filter. — [Apple: Audio Session Programming Guide](https://developer.apple.com/library/content/documentation/Audio/Conceptual/AudioSessionProgrammingGuide/OptimizingForDeviceHardware/OptimizingForDeviceHardware.html); [Apple forums 695892](https://developer.apple.com/forums/thread/695892); [JUCE forum 2014](https://forum.juce.com/t/disable-agc-and-highpass-filter-on-ios/12812)
- **Dolby adapts during sweeps** (measured, see Q1): the leveler moved the sweep envelope by 16–34 dB, while pink/multitone/stepped stimuli give the leveler a stationary signal. — [adaptive-processing.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/research/adaptive-processing.md)
- **EasyEffects' own guide** argues against boosting EQ on notebook speakers: "users tend to add to the signal (additive equalization)… raising the volume afterwards generally leads to distorted sounds". — [EasyEffects guide_1.md](https://github.com/wwmm/easyeffects/blob/master/src/contents/docs/guides/guide_1.md)

### Inferences
- **Why matching works without a perfect mic** [High]. To match Linux to Windows you EQ by the ratio W(f)/L(f) of two measurements taken with the same mic, position, room and volume. The mic's own response and most room effects appear in both and cancel. Absolute calibration matters only for going "better than Windows" toward a neutral target, and for trusting bass below about 200 Hz.
  - A phone is acceptable for the ratio only if its AGC, noise suppression and high-pass are off (Android UNPROCESSED-capable app, iOS measurement mode). Otherwise the time-varying processing breaks the comparison.
- **Draft procedure** [Medium-High overall]. Time: 2–4 h the first time, 1 h for repeats. Cost: €0 with a phone, about €115–130 with a UMIK-1.
  1. Room and setup:
     - Quiet room. Laptop on a table away from walls, in its normal open position.
     - Mic on a stand or tripod at ear position, about 40–60 cm from the keyboard and at head height, pointed at the screen hinge. Load the 0° calibration file.
     - Mark the position with tape so both OSes are measured at exactly the same spot. Optionally add 3–5 positions in a small (±10 cm) cluster and average them.
  2. Run REW on the laptop itself in each OS, or on a second computer listening through the mic only. Same mic, same USB port, 48 kHz. On Ubuntu choose the PipeWire "default" input. On Windows, Dolby is applied because REW plays through the shared-mode engine; check by toggling Dolby.
  3. Level safety: never exceed the volume you would normally listen at. Set the levels so pink noise reads about 70–80 dB SPL(C) at the mic. Use REW sweeps of a few seconds, and leave cool-down pauses (see Q5 for the tweeter-damage evidence).
  4. Windows reference:
     - Pink noise via REW's generator, plus REW's RTA with many averages (≥32), at a fixed Windows volume, with the Dolby profile you like.
     - Also take one sweep at the same level and one 10 dB lower. If the curves differ in shape, Dolby is adapting, so trust the pink-noise RTA.
  5. Linux measurement: same stimulus at the same mic level. Match level by ear-independent means, by aligning the 500 Hz–4 kHz average of the two curves. Do the Linux run with EasyEffects bypassed, or with only the safety limiter.
  6. Correction: smooth both to 1/6 octave (or REW's variable/psychoacoustic smoothing). Compute the target, either by loading the Windows curve as a house-curve/target file and EQ-ing the Linux measurement to it, or with A/B arithmetic on magnitude-only smoothed curves.
  7. Restrict the match range to where the speakers produce sound, roughly 150–200 Hz to 16 kHz. Below that, leave bass to psychoacoustic bass (Q3/Q4) rather than EQ.
  8. Set max boost to 0–3 dB and prefer cuts. 6–12 parametric filters usually cover the main features; EasyEffects allows up to 32.
  9. Export:
     - (i) "filter settings as text", Equalizer APO format → EasyEffects Equalizer "Import APO". Set all bands to APO mode so the filter shapes match REW/Equalizer APO.
     - (ii) For PipeWire `param_eq`, use only PK/LSC/HSC filters.
     - (iii) Generate a measurement from the filters → export a minimum-phase IR WAV → Convolver.
  10. Verify: re-measure Linux with the EQ on. Iterate once or twice, then listen.
- **Fastest acceptable path** [Medium]. HiFiScan straight to a correction FIR, aiming for flat rather than the Windows curve. It is attenuation-only, so it is inherently boost-safe, but it costs loudness that must be won back with compression and limiting.
  - On Ubuntu 26.04, install it with `pipx` or in a venv, since system pip is externally managed. That is an assumption from the Debian/Ubuntu packaging policy; it was not checked in this session.
- **Pitfalls** [Medium-High]:
  - Desk and wall reflections create comb-filtering above about 500 Hz that differs with mic position, so spatial averaging helps.
  - Too close a mic (under about 20 cm) over-weights one speaker and the keyboard-deck reflection.
  - Heavy smoothing hides narrow chassis resonances; too little makes REW chase room artefacts.
  - Windows volume changes between runs. Dolby's leveler changes level with content; the Windows endpoint volume does not enter loopback, but it does enter acoustic measurements.
  - Fan noise.
  - Measuring Linux with EasyEffects or loudness processing still active.
  - The UMIK-1's 90° file used while pointing the mic at the laptop.
  - Comparing a sweep on one OS with pink noise on the other.
- **Accuracy** [Medium].
  - With a UMIK-1 and averaged positions, ±1–2 dB from about 200 Hz to 10 kHz at the listening spot is a realistic match for static timbre.
  - Above about 10 kHz, and off the measured position, laptop responses vary more.
  - Dynamics (leveler, regulator, virtual bass) can't be captured by EQ and must be approximated as in Q4.

### Gaps
- Not obtained: the REW help pages themselves (site blocked). EQ-window details (exact option names in the current REW version, filter counts per equaliser type, the house-curve file format) come from search summaries and secondary guides and should be checked in REW.
- Not found: any published acoustic Windows-vs-Linux matching study for a CS35L41-based laptop, or for the Zenbook Duo specifically.
- No official miniDSP EUR price was found (retailer prices only). A low-cost alternative such as the Dayton iMM-6C, about €20–30 (assumption, not checked), was not researched.

---

## Q3. Asahi Linux's asahi-audio + speakersafetyd + Bankstown + LSP chain, x86 adaptations, and Ubuntu 26.04 availability

### Takeaway
asahi-audio is a PipeWire filter-chain per Mac model, in five stages:
1. Bankstown psychoacoustic bass.
2. An LSP loudness compensator driven by the system volume slider.
3. A per-channel FIR convolver made in REW and balanced with a UMIK-1.
4. An LSP multiband compressor acting only below 200 Hz.
5. An LSP compressor used as a 0 dBFS limiter.

The hardware volume is locked at 100% and speakersafetyd provides thermal protection. The design is portable to x86. The GPD Pocket 4 project copies it nearly 1:1 with a REW-measured FIR, and Framework users built EasyEffects equivalents. speakersafetyd itself is Apple-specific, because it needs V/I-sense data; on CS35L41 laptops the equivalent protection lives in the amp's own DSP firmware. Bankstown, LSP and Calf are all packaged in Ubuntu 26.04 universe. EasyEffects cannot host Bankstown, so a Bankstown chain must be a PipeWire filter-chain.

### Cited Findings
- **Goals** (Asahi docs):
  - "A balanced (neutral) tone at moderate listening volumes, with a mostly flat frequency response from a typical listening position".
  - "Reasonably high peak volume with acceptable sound degradation (compression, limiting, etc.)".
  - "'Fake bass' processing".
  - "Equal-loudness volume compensation, so that the sound does not become noticeably tinny as the system master volume is lowered".
  - Cloning macOS is explicitly *not* the goal.
  — [Asahi docs: Userspace Audio Stack](https://asahilinux.org/docs/sw/audio-userspace/) ([source](https://github.com/AsahiLinux/docs/blob/main/docs/sw/audio-userspace.md))
- **Why it is needed**: OEMs "work with codec vendors to add all of this processing to their Windows sound drivers". asahi-audio virtual devices are PipeWire filter-chains, and WirePlumber "detect[s] which Mac they are running on, load[s]… the correct virtual device and impulse responses, and then hide[s] the 'raw' hardware output". — [asahi-audio README](https://github.com/AsahiLinux/asahi-audio/blob/main/README.md)
- **Dependencies**: PipeWire ≥1.0, WirePlumber ≥0.5.2, Bankstown ≥1.1.0, Triforce (mics), LSP Plugins ≥1.0.20 (LV2 only), speakersafetyd. Licence: MIT up to 4.2, GPL-2.0 after. — [asahi-audio README](https://github.com/AsahiLinux/asahi-audio/blob/main/README.md)
- **Exact chain for the MacBook Air M1 (J313)** — [firs/j313/graph.json](https://github.com/AsahiLinux/asahi-audio/blob/main/firs/j313/graph.json):
  1. `https://chadmed.au/bankstown`: bypass 0, amt 1.45, sat_second 1.3, sat_third 1.75, blend 1.0, ceil 200.0, floor 20.0, final_hp 200.0.
  2. `http://lsp-plug.in/plugins/lv2/loud_comp_mono`, one per channel: enabled 1, input 1.0, fft 2. The sink volume is mapped onto its `volume` control through `capture.volumes` (min −47.5, max 0.0, scale "cubic"). `state.default-volume` is 0.343.
  3. Builtin `convolver` per channel, with per-rate IR files (44.1/48/96/192 kHz), gain 1.0.
  4. `lsp…/mb_compressor_stereo` "woofer_bp": band 0 enabled, split `sf_1` at 200 Hz, `cr_0` 1.75, `al_0` 0.725, `at_0` 1 ms, `rt_0` 100 ms, `kn_0` 0.125, `sla_0` 5 ms lookahead. All other bands off.
  5. `lsp…/compressor_stereo` "woofer_lim": `al` 1.0, `cr` 15, `at` 1 ms, `rt` 100 ms, `kn` 0.5, `sla` 5 ms.
- **LSP units**: the LSP multiband compressor's `al` (attack threshold), `kn` (knee) and `mk` (makeup) ports are `U_GAIN_AMP`, i.e. linear amplitude. — [lsp-plugins-mb-compressor meta](https://github.com/lsp-plugins/lsp-plugins-mb-compressor/blob/master/src/main/meta/mb_compressor.cpp)
- **Hardware volume is locked**: `asahi-lock-volume.lua` forces the "Speaker(s)" route to `channelVolumes = 1.0` and unmuted, so all volume control happens in the DSP. — [conf/asahi-lock-volume.lua](https://github.com/AsahiLinux/asahi-audio/blob/main/conf/asahi-lock-volume.lua)
- **FIR design history**:
  - "j314: re-export trimmed IRs from REW" (2024-11-29) and "j314: introduce new FIRs – Balanced with UMIK-1" (2025-11-29) — [commit b07bd7f](https://github.com/AsahiLinux/asahi-audio/commit/b07bd7f); [commit 9a1dbfb](https://github.com/AsahiLinux/asahi-audio/commit/9a1dbfb3795fb3757355cc38b1a112fbe28326a5)
  - The 13" Air curve was "pending re-calibration with an individually calibrated microphone". — [Asahi docs](https://github.com/AsahiLinux/docs/blob/main/docs/sw/audio-userspace.md)
- **Safety history in commits**:
  - "j31x: add multiband comp for safety… the speakers won't explode now" (2022-11-20) — [commit 083aca0](https://github.com/AsahiLinux/asahi-audio/commit/083aca0)
  - J313 (2026-06-12): "We were not setting a high pass on Bankstown on this machine, resulting in a lot of double amplification. Coupled with the extremely aggressive FIR, this was resulting in far too much clipping at the low end. Clamp Bankstown's output to above 200 Hz" — [commit 19a3a13](https://github.com/AsahiLinux/asahi-audio/commit/19a3a13)
  - J415: "bring up the high pass filter to the ceiling frequency, avoiding double amplification" — [commit 7ee4c14](https://github.com/AsahiLinux/asahi-audio/commit/7ee4c14)
  - J316: bigger speakers, so the Bankstown ceiling dropped to 125 Hz; "This lets us also bump the volume since we are no longer clipping" — [commit 293465a](https://github.com/AsahiLinux/asahi-audio/commit/293465a)
- **Known limitations (Asahi docs)**: "There is no final limiter/compressor in the current DSP chains… inputs with content in high-gain regions of the EQ curve might cause distortion or clipping… most prominent in the 200Hz region". Bankstown "uses a relatively naïve algorithm right now". The DSP chain "introduces excessive delay". — [Asahi docs](https://github.com/AsahiLinux/docs/blob/main/docs/sw/audio-userspace.md). The current J313 graph does end in a compressor-limiter, so that docs line appears out of date.
- **Bankstown** — [README](https://github.com/chadmed/bankstown/blob/main/README.md); [bankstown.ttl](https://github.com/chadmed/bankstown/blob/main/bankstown.ttl); [src/lib.rs](https://github.com/chadmed/bankstown/blob/main/src/lib.rs):
  - It is a "Halfway-decent three-stage psychoacoustic bass approximation" that saturates bass to create harmonics so "the brain… is able to infer the fundamental". Version 1.1.0, Rust, MIT.
  - Ports: `bypass`; `amt` "Amount" 0–15 (default 1); `floor` 10–250 Hz (default 20); `ceil` 10–250 Hz (default 200); `final_hp` "Output HPF" 10–250 Hz (default 200); `sat_second` 0–15 (default 1); `sat_third` 0–15 (default 1); `blend` "Harmonic Ratio" 0–1 (default 0.5).
  - Signal flow in source: the input is band-passed floor→ceil, saturated, then `out = blend·k·tanh(x·sat_third)` ("Third harmonic from symmetrical" function) plus `(1−blend)·k·tanh(x·sat_second)` ("Second harmonic from asymmetric"), scaled by `amt`. That passes through the `final_hp` high-pass and is **added back to the unmodified input**.
- **speakersafetyd**:
  - It implements "an analogue of the Texas Instruments Smart Amp speaker protection model" using the V/I-sense lines of Apple's TAS2764-family amps. "Only Apple Silicon Macs under Linux are currently supported". It is adaptable to "any device that provides V/ISENSE data in a manner similar to TAS2764". — [speakersafetyd README](https://github.com/AsahiLinux/speakersafetyd/blob/main/README.md)
  - The J313 config shows the thermal parameters: `t_limit = 120.0` °C, `t_headroom = 15`, `tau_coil = 2.40` s, `tau_magnet = 80.00` s. — [conf/apple/j313.conf](https://github.com/AsahiLinux/speakersafetyd/blob/main/conf/apple/j313.conf)
  - It estimates voice-coil temperature with "a two-stage thermal model" and reduces hardware volume when hot. There are "kernel-side interlocks" if the daemon isn't running, and a conservative −7 dBFS hard volume-reduction limit. — [Asahi docs](https://github.com/AsahiLinux/docs/blob/main/docs/sw/audio-userspace.md)
- **x86 adaptation 1, GPD Pocket 4** (Manawyrm):
  - "Similar approach to asahi-audio… Using convolution EQs, bankstown (bass enhancer) and volume-dependent EQ… Speaker response was measured using Room EQ Wizard".
  - Same chain as J313, with: Bankstown sat_second 1.65, sat_third 2.20, final_hp 120; the multiband compressor split at 380 Hz; volume map −42.5…0 dB.
  - Per-channel 48 kHz FIRs. Packaged in AUR and nixpkgs (`gpd-pocket-4-pipewire`, requiring `bankstown-lv2` and `lsp-plugins`).
  — [Manawyrm/gpd-pocket-4-pipewire](https://github.com/Manawyrm/gpd-pocket-4-pipewire) ([sink-gpd-pocket-4.conf](https://github.com/Manawyrm/gpd-pocket-4-pipewire/blob/main/pipewire.conf.d/sink-gpd-pocket-4.conf)); [nixpkgs package.nix](https://github.com/NixOS/nixpkgs/blob/master/pkgs/by-name/gp/gpd-pocket-4-pipewire/package.nix); [kittenlabs.de write-up](https://kittenlabs.de/blog/2025/04/06/gpd-pocket-4-speaker-dsp/)
- **x86 adaptation 2, Framework 13**: EasyEffects presets with a HiFiScan correction IR, plus filter, multiband compressor and limiter ("EEGuide+Exciter", "HifiScan+EEGuide", "Gracefu's Edits"). — [cab404/framework-dsp](https://github.com/cab404/framework-dsp); community presets [ceiphr/ee-framework-presets](https://github.com/ceiphr/ee-framework-presets)
- **x86 adaptation 3, the Dolby converter**: it emits a PipeWire filter-chain alternative to EasyEffects. Its opt-in virtual-bass stage is "PipeWire-only". — [speaker-tuning-to-easyeffects README](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/README.md); [virtual-bass.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/research/virtual-bass.md)
- **Ubuntu 26.04 (resolute) package versions**:
  - `bankstown-lv2` 1.1.0-3build1 (universe) — [packages.ubuntu.com](https://packages.ubuntu.com/resolute/bankstown-lv2)
  - `lsp-plugins-lv2` 1.2.27-1 (universe) — [link](https://packages.ubuntu.com/resolute/lsp-plugins-lv2)
  - `calf-plugins` 0.90.9-0ubuntu1 (universe) — [link](https://packages.ubuntu.com/resolute/calf-plugins)
  - `x42-plugins` 20251025+ds-1 — [link](https://packages.ubuntu.com/resolute/x42-plugins)
  - `zam-plugins` 4.2+ds-1build2 — [link](https://packages.ubuntu.com/resolute/zam-plugins)
  - `asahi-audio` 3.4-2 ("PipeWire DSP profiles for Apple Silicon machines") — [link](https://packages.ubuntu.com/resolute/asahi-audio)
  - `speakersafetyd` 1.1.2-4 — [link](https://packages.ubuntu.com/resolute/speakersafetyd)
- **The CS35L41 equivalent of speaker protection**: Cirrus describes the part as an "11 V Boosted Mono Class D Amplifier with DSP Speaker Protection". Its "speaker protection algorithms enable maximum loudness by allowing the amplifier to safely drive high output power while ensuring that the speaker's thermal and excursion limits are not exceeded" (search summary). The Linux HDA driver series added DSP firmware loading for this. — [Cirrus CS35L41](https://cirrus.com/products/cs35l41); [ALSA hda cirrus DSP patch series v7](https://lore.kernel.org/all/87wnd8n7oa.wl-tiwai@suse.de/T/)

### Inferences
- **What each Asahi stage does**:
  - [High] Bankstown adds odd and/or even harmonics of 20–200 Hz content above `final_hp`, so pitch is perceived even where the speaker cannot move air.
  - [High] The loudness compensator applies ISO-226-type contours tied to the volume slider, adding bass and treble at low volume.
  - [High] The FIR flattens the measured speaker/chassis response.
  - [High] The sub-200 Hz multiband compressor limits woofer excursion and stops the FIR's bass boost from clipping.
  - [High] The final compressor (15:1, 0 dBFS, 5 ms lookahead) is a peak limiter.
  - [High] dB equivalents of the linear LSP values: `al_0` 0.725 ≈ −2.8 dBFS; `kn_0` 0.125 ≈ −18 dB; limiter `kn` 0.5 ≈ −6 dB.
- **Safe Bankstown settings** [High]. Set `final_hp` equal to `ceil`. Otherwise the band-passed bass itself is amplified and added to the dry bass ("double amplification"), which costs headroom and adds excursion. Bankstown never removes the original bass, so a separate high-pass is still needed if the speakers must be spared sub-bass: the FIR roll-off, an LSP/EasyEffects filter, or the multiband compressor.
- **Bankstown blend** [Medium]. `blend` = 1.0, Asahi's choice, gives purely symmetric (odd-harmonic) saturation. That matches what the converter measured from Dolby's virtual-bass on a Realtek ThinkPad: odd harmonics, even harmonics suppressed. Bankstown at blend ≈ 1 is a closer stand-in for Dolby VBE than Calf's enhancer, which scored worse than nothing in that comparison.
- **Porting the template to the Zenbook** [Medium-High]. Use the J313/GPD graph as the template:
  - Replace the FIR with one from Q1 (Dolby capture, for the Windows sound) or Q2 (REW/HiFiScan, for flat or Windows-matched).
  - Tune Bankstown `ceil`/`final_hp` to the speakers' measured low-frequency roll-off, likely 150–250 Hz for slim-laptop micro-speakers; to be measured.
  - Set the multiband compressor split at the same frequency, and keep the final limiter.
  - Point `playback.props` at the speaker sink with `target.object` plus `node.dont-fallback`, so headphones/HDMI don't get speaker DSP. The GPD config omits `target.object`, which is a likely pitfall on machines with several outputs.
  - Install with `sudo apt install bankstown-lv2 lsp-plugins-lv2` and put the config in `~/.config/pipewire/pipewire.conf.d/`.
- **Don't install the Ubuntu asahi packages** [High]. `asahi-audio` and `speakersafetyd` are Apple-only (Mac DT/ALSA control names and V/I sense) and do nothing useful on the Zenbook. Ubuntu's asahi-audio 3.4 also lags upstream, which is now past 4.2 with the GPL relicence.
- **No hardware volume lock without protection** [High]. Do not copy Asahi's "lock hardware volume at 100%" on the Zenbook unless the CS35L41 protection firmware is confirmed loaded and running (another researcher's topic). Asahi can lock at 100% only because speakersafetyd and kernel interlocks exist.
- **Bankstown needs filter-chain** [Medium-High]. EasyEffects only exposes its fixed set of wrapped LSP/Calf/ZAM/MDA/x42 effects (its plugin docs list no generic LV2 host), so a Bankstown chain must be a PipeWire filter-chain. A hybrid is possible: run the filter-chain sink, and use EasyEffects on top only for listening tweaks.
- **Effort and cost** [Medium]. €0 in software. 3–6 h for a careful non-expert to adapt, test and tune, plus measurement time from Q2. Editing JSON-like config is the main barrier, since there is no GUI.

### Gaps
- Not verified: how Asahi chose the exact multiband compressor and Bankstown values beyond the commit messages; no design document was found. Also not verified: the precise semantics of LSP `mode` 0 in the multiband compressor.
- Not found: any published asahi-style PipeWire chain for an ASUS, Dell or ThinkPad x86 laptop. The GPD Pocket 4 and Framework examples are the closest.
- Not determined: whether the Zenbook's CS35L41 firmware gives enough thermal/excursion protection to justify Asahi-like loudness. That depends on the amp-firmware findings.

---

## Q4. EasyEffects best practices for small laptop speakers: bass, loudness, compression, limiting, high-pass, gain staging

### Takeaway
The proven order is: high-pass/filter (or the correction FIR) → bass enhancer → (EQ) → multiband compressor → optional stereo widening → limiter last. Optionally use autogain/loudness as a leveler stand-in before the compressor. EasyEffects' own laptop guide gives concrete starting values, and the Asahi/GPD chains give a protective bass-band compressor and 0 dBFS limiter. Loudness comes from cutting what the speaker can't reproduce, compressing (especially the bass band), and adding makeup gain before a fast limiter, not from EQ boosts or GNOME over-amplification. Ubuntu 26.04's EasyEffects 8.1.2 has a known bad default (compressor "pre-mix" at 0 dB instead of −inf) that must be fixed by hand.

### Cited Findings
- **Official EasyEffects laptop guide** ("Enhancing your internal notebook speakers without using an Equalizer", Markus Schmidt) — [guide_1.md](https://github.com/wwmm/easyeffects/blob/master/src/contents/docs/guides/guide_1.md):
  - **Limiter**, placed last: PreAmp 0 dB, Lookahead 4 ms, Attack 2 ms, Release 8 ms, threshold 0 dB, Stereo Link 100%, Oversampling Half ×4, no external sidechain, no Auto Leveling.
  - **Filter**, placed first: 36 dB/oct high-pass starting at 50 Hz, raised in 10 Hz steps until the low end audibly changes (around 130–160 Hz), then lowered by about 10%. The author's ThinkPad P1 ended at 145 Hz.
  - **Bass Enhancer** (Calf): Floor 10 Hz, Harmonics 10, Scope 200 Hz, Amount raised until too much. The author used +24 dB on the ThinkPad P1.
  - **Multiband Compressor**: input −6 dB, Modern mode, bands 2–4 enabled, splits 250/1250/5000 Hz, downward mode.
    - Band 1: 150/300 ms, −16 dB threshold, ratio 5, knee −12 dB, makeup 4 dB.
    - Band 2: 150/200 ms, −24 dB, ratio 3, knee −9 dB, makeup 4 dB.
    - Band 3: 100/150 ms, −24 dB, ratio 3, knee −9 dB, makeup 4 dB.
    - Band 4: 80/120 ms, −24 dB, ratio 4, knee −9 dB, makeup 4 dB.
    - "Makeup… **this is your Equalizer**". The author's final makeups were 4/3/6/6 dB, with input −3 dB.
  - **Stereo Tools**: Stereo Base 0.25.
  - Notes: "Don't care about clipping in the plugins level meters", because processing is 32-bit float internally; only clipping at the DAC matters. "Set the desired volume directly on your hardware **after** the processing happened."
- **EasyEffects plugin facts** — EasyEffects docs [bassenhancer.md](https://github.com/wwmm/easyeffects/blob/master/src/contents/docs/plugins/bassenhancer.md), [bassloudness.md](https://github.com/wwmm/easyeffects/blob/master/src/contents/docs/plugins/bassloudness.md), [loudness.md](https://github.com/wwmm/easyeffects/blob/master/src/contents/docs/plugins/loudness.md), [maximizer.md](https://github.com/wwmm/easyeffects/blob/master/src/contents/docs/plugins/maximizer.md), [limiter.md](https://github.com/wwmm/easyeffects/blob/master/src/contents/docs/plugins/limiter.md), [autogain.md](https://github.com/wwmm/easyeffects/blob/master/src/contents/docs/plugins/autogain.md):
  - Bass Enhancer = Calf (Amount, Harmonics, Scope, Floor, Blend, Listen).
  - Bass Loudness = MDA Loudness.
  - Loudness = LSP Loudness Compensator: ISO 226:2003, Fletcher-Munson or Robinson-Dadson contours; output volume; optional hard clipping.
  - Maximizer = ZamMaximX2: gain = (−Threshold) − (−Ceiling), brick-wall with a fixed 10 ms lookahead.
  - Limiter = LSP Sidechain Limiter: modes, oversampling, lookahead, attack/release, threshold, Stereo Link, optional "Auto Leveling" (ALR).
  - Autogain = libebur128 EBU R128 loudness target (momentary/short-term/integrated).
- **Version notes relevant to Ubuntu's 8.1.2**:
  - 8.1.7 fixed: "The default Pre-mix control values of the compressor, gate, expander, multiband compressor and multiband gate were incorrectly set to 0 dB when it should be -Inf. Users will need to manually update their presets". — [CHANGELOG](https://github.com/wwmm/easyeffects/blob/master/src/contents/docs/community/CHANGELOG.md)
  - Verified in source: the v8.1.2 multiband compressor defaults `inputToSidechain`, `inputToLink`, `sidechainToInput`, `sidechainToLink`, `linkToSidechain` and `linkToInput` to 0, while master defaults them to −80.01. — [v8.1.2 kcfg](https://github.com/wwmm/easyeffects/blob/v8.1.2/src/contents/kcfg/easyeffects_db_multiband_compressor.kcfg); [master kcfg](https://github.com/wwmm/easyeffects/blob/master/src/contents/kcfg/easyeffects_db_multiband_compressor.kcfg)
  - 8.1.2 itself fixed "a regression that could cause some plugins to create loud sounds when PipeWire changed latency". The crosstalk canceller arrived in 8.2.1 (2026-04-25), Mid-Side EQ in 8.2.9, and convolver IR rename in 8.1.3. — [CHANGELOG](https://github.com/wwmm/easyeffects/blob/master/src/contents/docs/community/CHANGELOG.md)
- **Protective bass compression and limiter values** from Asahi J313 and GPD Pocket 4 (detailed in Q3): bass-band (<200 Hz, or <380 Hz on GPD) ratio 1.75, threshold ≈ −2.8 dB, knee ≈ −18 dB, 1 ms attack, 100 ms release, 5 ms lookahead; then a 15:1 limiter at 0 dBFS. — [J313 graph.json](https://github.com/AsahiLinux/asahi-audio/blob/main/firs/j313/graph.json); [GPD conf](https://github.com/Manawyrm/gpd-pocket-4-pipewire/blob/main/pipewire.conf.d/sink-gpd-pocket-4.conf)
- **Framework practice**: lowering the Filter cutoff and steepening its slope brought bass back; the Bass Enhancer was "not needed"; gain goes before the compressor, not the limiter; multiband band-1 makeup 0 dB removed bass distortion. — [cab404/framework-dsp README](https://github.com/cab404/framework-dsp)
- **Gain staging across two sinks**: when a DSP sink feeds the speaker sink, "two sinks in series, so two volume controls". "The chain's control is ahead of the tuning; the speaker's is behind it". The chain's volume reaches the graph "as a quieter input, and the MBC, regulator and limiter engage differently", while the speaker's control is "applied after everything". Measured on PipeWire filter-chain. — [easyeffects-and-pipewire.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/research/easyeffects-and-pipewire.md)
- **Why Windows can be louder at the same input** (DAX3 measurements):
  - DAX's leveler drives the dynamic/movie/music/game profiles "to a single loudness target", which gave a flat ≈ −8 dB EasyEffects-vs-DAX offset on the X1 Yoga. — [loudness-and-limiting.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/research/loudness-and-limiting.md)
  - `volmax-boost` is "the maximum gain the volume leveler may add above the output target"; "6 dB is the dominant value" (78% of dynamic-profile tunings). — [cross-device-findings.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/cross-device-findings.md)
- **"Why no Equalizer?"** EQ boosts on notebook speakers lead to "a quiet and still castrated sound" or distortion once volume is raised. — [guide_1.md](https://github.com/wwmm/easyeffects/blob/master/src/contents/docs/guides/guide_1.md)

### Inferences
- **Recommended EasyEffects 8.1.2 output chain for the Zenbook**, in order [Medium-High for structure; Medium for numbers, which are starting points to tune by ear and meter]:
  1. **Convolver**: Windows-capture or measured correction IR, autogain on. Or skip it and use an Equalizer with an imported REW/APO file, APO band mode, with cuts preferred.
  2. **Filter**: high-pass 24–36 dB/oct at 10–15% below the measured low-frequency roll-off, likely 120–180 Hz. This is the excursion guard: it removes energy the speaker can't reproduce but would still move the cone for.
  3. **Bass Enhancer (Calf)**: Floor 10–20 Hz, Scope about 150–250 Hz, Harmonics 5–10, Amount raised gradually and kept well below "takes over". Or skip it. On Dolby-like voicing, a Bankstown filter-chain at blend ≈ 1 is the better imitation (Q3).
  4. **Autogain** (optional, leveler analogue): target about −18 to −14 LUFS, Short-Term reference. It narrows the quiet-to-loud range like Dolby's leveler, but is slower and less refined. Keep it before the compressor so the limiter still catches peaks.
  5. **Multiband Compressor**: 3–4 bands. Either the guide's 250/1250/5000 Hz splits and values, or an Asahi-style bass-only band below about 200 Hz (ratio about 2, threshold about −6 to −3 dBFS, 1–10 ms attack, about 100 ms release).
     - Add makeup in the mid/treble bands, not the bass band.
     - **On 8.1.2, set every "Pre-mix" control to −inf first.**
  6. **Stereo Tools**: Stereo Base 0–0.3, only if the image is narrow. Or, from 8.2.1 via an upstream/Flatpak build, the Crosstalk Canceller.
  7. **Limiter**, last: threshold −1 dBFS, lookahead about 4–5 ms, attack about 2 ms, release 8–50 ms, Stereo Link 100%, oversampling Half ×4 or better. Add 2–6 dB of input gain here only if the multiband compressor isn't already doing the work. Loudness gained at the limiter costs transient punch and adds pumping, and beyond roughly 6 dB of sustained gain reduction it becomes audibly distorted.
  - Alternatively, replace step 7 with the Maximizer. Threshold −6, Ceiling −1 gives +5 dB of drive.
- **Loudness compensation** [Medium]. EasyEffects' Loudness (LSP) is not tied to the GNOME slider, so its contour won't track volume the way Asahi's `capture.volumes` mapping does. Use it with a modest fixed setting, or move to a filter-chain if volume-tracking loudness matters.
- **Gain staging rule** [Medium-High]:
  - Keep player and app volume at 100%.
  - Keep the hardware speaker sink at a fixed, known-safe level. Do the everyday volume control on the EasyEffects/virtual sink, which feeds the chain, so the dynamics see less signal at low volume. That suits small speakers.
  - Or follow EasyEffects' guide: chain at 100% and volume on the hardware after the processing. Then the compressors always work at full input, which is denser but keeps a constant tonal balance.
  - In either case, GNOME's over-amplification (above 100% on a sink) adds digital gain after or before the chain. If applied after the limiter it will clip. Prefer limiter or compressor makeup gain.
- **Expected loudness gain** [Medium]. A properly limited and compressed chain can raise perceived loudness by roughly 4–8 dB on typical material relative to a raw, peak-limited signal. That matches the size of DAX's measured leveler/volmax effect. It cannot raise the true maximum acoustic output: that is set by the amp's gain, boost voltage and protection firmware, the other researchers' topic. If Windows is louder by more than about 6–8 dB on loudness-normalised content, the cause is very likely amp-side, not DSP.
- **Metering** [High]. Watch EasyEffects' output level meter and the limiter's gain-reduction meter. Occasional 1–3 dB reduction is fine. Constant reduction above about 6 dB, or audible pumping, means too much input or makeup gain.

### Gaps
- No credible published A/B data for Calf Bass Enhancer vs Bankstown on laptops was found, beyond the converter's DAX-similarity scoring (one device) and Asahi's own listening notes.
- Not verified: the 8.1.2 pre-mix bug for the single-band Compressor, Gate and Expander kcfg files. Only the multiband compressor kcfg was checked, though the changelog lists all five.
- No source was found that quantifies the GNOME over-amplification range and where it sits relative to EasyEffects in the graph. Left to the volume-chain researcher.

---

## Q5. Speaker safety: risks of boosting bass or gain on micro-speakers, with and without amp protection firmware, and the limits to respect

### Takeaway
Laptop micro-speakers and tweeters can be destroyed in seconds to minutes by sustained power, which is mostly a thermal effect, and by excursion at low frequencies. Asahi blew Mac tweeters with 40-second sweeps at −2 dBFS before speakersafetyd existed. Linaro capped ThinkPad X13s speaker gain until active protection was available. On the Zenbook, the CS35L41's on-chip DSP is designed to enforce thermal and excursion limits, but only when its firmware and tuning are loaded and running. Without confirmed protection, treat the hardware volume ceiling as sacred and never add bass boost. Even with protection, keep EQ boosts small, high-pass below the speaker's range, compress the bass band, limit at −1 dBFS, and measure at moderate levels with pauses.

### Cited Findings
- **Asahi's damage tests** (marcan, 2022-09-13, via fetched GitHub issue):
  - "Testing using a sine sweep, 10-20kHz, 40 seconds, volume 0.8 (~-2dB)". The tweeters failed with "a severe drop in volume". "My theory is that this is thermal damage, i.e. the tweeter melted itself and seized up". "damage occurs fairly quickly, even with just 40-second sweeps". "If this is thermal, that suggests even short-term power excursions are dangerous".
  - Estimates: long-term safe average power "on the order of 0.5W or so"; a tweeter cap of about −7.5 dB; "-6dB would get us into 100% safe territory" for woofers. A square wave "delivers 2 times the power" of a sine at the same peak. Rattle can be "identified by the presence of sub harmonics".
  — [AsahiLinux/linux#53 Speaker protection research](https://github.com/AsahiLinux/linux/issues/53)
- **Asahi November 2022 report**: a developer "quickly managed to blow up his tweeters on a MacBook Air M2" even with some volume limits (via search summary). — [Asahi Linux November 2022 Progress Report](https://asahilinux.org/2022/11/november-2022-report/)
- **Smart-amp rationale**: "The cheap component speaker elements used in modern devices… are very fragile. In order to eke the highest possible sound quality out of them, they need to be driven *hard*". Without protection, "the output level on these devices would have to be hard limited to a very low level that is known to be safe for the worst possible input". — [speakersafetyd README](https://github.com/AsahiLinux/speakersafetyd/blob/main/README.md)
- **Voice-coil thermal constants** in a MacBook Air config: `tau_coil` 2.4 s, `tau_magnet` 80 s, limit 120 °C with 15 °C headroom. — [speakersafetyd conf/apple/j313.conf](https://github.com/AsahiLinux/speakersafetyd/blob/main/conf/apple/j313.conf)
- **Stress-test tracks**: "J.Geco – Chicken Song – Konrad said this damaged a ThinkPad X13s's speakers"; "I Won The Loudness War – Speaker torture"; "KZ5 – SUBWOOFA… good test for overexcursion and overzealous compression". — [Asahi docs: Speaker stress tests](https://github.com/AsahiLinux/docs/blob/main/docs/sw/speaker-stress-tests.md)
- **X13s kernel cap**: "limit speaker volumes… to reduce the risk of speaker damage on machines like the Lenovo Thinkpad X13s until we have active speaker protection in place". Digital gain plus PA volume is capped at a combined −3 dB. — [LKML: ASoC: qcom: sc8280xp: limit speaker volumes (v3 3/5)](https://lkml.iu.edu/hypermail/linux/kernel/2401.2/03398.html); [v4](https://lkml.iu.edu/hypermail/linux/kernel/2401.2/04107.html)
- **CS35L41 protection** (search summary of Cirrus page): integrated DSP with "speaker protection algorithms" that "enable maximum loudness by allowing the amplifier to safely drive high output power while ensuring that the speaker's thermal and excursion limits are not exceeded". Linux HDA support needed firmware loading to run this DSP. — [Cirrus CS35L41](https://cirrus.com/products/cs35l41); [ALSA hda cirrus DSP patch series](https://lore.kernel.org/all/87wnd8n7oa.wl-tiwai@suse.de/T/)
- **Low-frequency risk**:
  - Speakers "may be destroyed at low frequencies with only a fraction of the power that they handle at the higher frequencies"; high-pass filters are the traditional protection (patent literature, via search summary). — [US10674263B1 Speaker excursion protection](https://patents.google.com/patent/US10674263B1/en)
  - A frequency-dependent limiter can let bass EQ boost be used, with the limiter reducing "this EQ boost when the signal level is sufficiently high that it would cause… the driver displacement to exceed its recommended range". — [ProSoundTraining: Using limiters to help protect loudspeakers](https://www.prosoundtraining.com/2010/03/21/using-limiters-to-help-protect-loudspeakers/)
- **Dolby's own protective dynamics** (measured): "the regulator engaged as a hard limiter even at −18 dBFS RMS input". The DAX3 regulator is a per-band limiter in the converter's chain. — [adaptive-processing.md](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/docs/research/adaptive-processing.md); [README chain](https://github.com/antoinecellerier/speaker-tuning-to-easyeffects/blob/master/README.md)
- **Asahi's own safety additions**: a multiband compressor for safety ("speakers won't explode now"), and keeping Bankstown's output above the ceiling to avoid low-end clipping. — [commit 083aca0](https://github.com/AsahiLinux/asahi-audio/commit/083aca0); [commit 19a3a13](https://github.com/AsahiLinux/asahi-audio/commit/19a3a13)

### Inferences
- **Two separate failure mechanisms** [High]:
  - **Thermal**: average power over seconds to minutes. Driven by sustained loud, compressed content, test tones and sweeps at high level, and makeup gain.
  - **Excursion**: peak cone movement, rising steeply toward and below the speaker's resonance. Driven by bass EQ boost, unfiltered sub-bass and full-scale low tones.
  - Compression and limiting raise average power, so they *increase* thermal stress for the same peak level, even while they prevent clipping.
- **If the CS35L41 protection firmware is loaded and calibrated** [Medium-High]. The amp should cap thermal and excursion stress itself, as on Windows; this depends on the amp researcher's confirmation that the Windows-equivalent firmware and tuning are active.
  - The DSP chain's job is then mainly sound quality and avoiding clipping.
  - Do: keep a limiter at −1 dBFS, avoid bass boosts beyond a few dB, and use the bass-band compressor.
  - Expect the amp DSP to duck audibly if you push harder.
- **If protection is not confirmed** (firmware missing, bypass mode, or unknown) [High]:
  - Do not raise the hardware/ALSA speaker gain above the distribution default.
  - No bass EQ boost; high-pass at or above the speakers' roll-off.
  - Keep all DSP net gain ≤ 0 dB, with the limiter at −1 to −3 dBFS.
  - Avoid long full-volume sessions with heavily compressed music.
  - Treat Over-Amplification as off-limits.
  - This mirrors the X13s policy of capping gain "until we have active speaker protection".
- **Measurement safety** [High]. Run sweeps and pink noise at moderate level (about 70–80 dB SPL at 50 cm, or stimuli at −18 dBFS or lower with normal volume settings). Keep sweeps short (2–10 s). Pause between runs. Never use full-scale sweeps at maximum volume; that is the exact recipe that killed Asahi's tweeters.
- **Captured Dolby IRs** [Medium-High]. An IR captured from Dolby contains boosts that Dolby's regulator relaxes at high level. Statically applied, it can exceed Windows' excursion at maximum volume, so pair it with bass-band compression and a limiter, and keep the system volume ceiling in mind.
- **Warning signs** [Medium]. Rattle or buzz (sub-harmonics, per marcan), a sudden loss of treble or volume (tweeter damage), audible amp ducking or pumping (protection engaging), or a hot palm rest near the speakers after loud playback. If any appear, back off by 6 dB or more.
- **Target numbers** [Medium]:
  - DSP output ceiling −1 dBFS.
  - Bass-band compression from about −6 to −3 dBFS.
  - High-pass at 10–15% below the measured roll-off.
  - Total EQ boost ≤ +3 dB anywhere below 300 Hz.
  - Long-term listening below the level where the limiter is constantly active.
  - These are conservative rules distilled from the Asahi, EasyEffects-guide and X13s sources, not manufacturer specifications for the Zenbook's speakers.

### Gaps
- No public data on the Zenbook Duo UX8406MA speakers' power rating, resonance frequency or excursion limit; ASUS and Cirrus tuning parameters aren't published.
- Not verified here: whether the Linux cs35l41-hda driver on kernel 7.0 runs the amp in a protected or reduced-gain mode when firmware is missing. That is the amp researcher's question, and it determines which safety branch above applies.
- No documented laptop-speaker damage case caused specifically by EasyEffects bass boost was found. The risk is inferred from the Asahi/X13s evidence and general loudspeaker practice.
