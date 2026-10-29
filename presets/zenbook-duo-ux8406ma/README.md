# EasyEffects preset for the Zenbook Duo UX8406MA speakers

`windows-dolby-music.wav` is the tone shape Windows plays through these
speakers with Dolby's Music profile (intelligent EQ Balanced), recorded by
loopback on 2026-10-29 and turned into a minimum-phase, cut-only impulse by
[`dax-curve-to-fir`](../../tools/dax-curve-to-fir/) (48 kHz, stereo, 8192
taps). The measurements are in
[research_notes/…/measurements-2026-10-29](../../research_notes/Zenbook%20Duo%20Linux%20speaker%20fix/measurements-2026-10-29/).
By ear it sounded much better than the converter's presets.

It is specific to this laptop model: on other hardware, record your own with
[DOLBY-CAPTURE.md](../../DOLBY-CAPTURE.md).

## Set it up

```bash
mkdir -p ~/.local/share/easyeffects/irs
cp windows-dolby-music.wav ~/.local/share/easyeffects/irs/
```

In EasyEffects:

1. **Presets → Local**: type `Windows-Music` in *New preset name*, press
   **+**, and load it.
2. **Add effect → Convolver**. Under **Impulses**, pick `windows-dolby-music`.
   Set its **Output** gain to **+17 dB**. Above that, the author heard
   distortion.
3. **Add effect → Limiter**, after the Convolver. Set **Threshold** to
   **−1 dB** and leave the rest at the defaults.
4. **☰ → Preferences → General**: switch on **Launch service at system
   startup**.
5. **Presets → Autoload**: pick **Meteor Lake-P HD Audio Controller
   Speaker** (GNOME calls it *Speaker - Meteor Lake-P HD Audio Controller*)
   and `Windows-Music`, press **+ Create**, and delete any older entries for
   the same device.

Keep **Speaker** as the output device in GNOME's sound settings, not *Easy
Effects Sink*.

## Not reproduced yet

- Dolby's volume leveler: up to +25 dB on quiet input, with output near
  −25 dBFS for anything above −30 dBFS input.
- Its stereo widening: side/mid +6.3 dB on correlated stereo.
