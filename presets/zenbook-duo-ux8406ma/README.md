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

`Windows-Music.json` is the author's EasyEffects 8 preset: a Convolver with
this impulse at +17 dB output gain (above that, the author heard distortion),
then a Limiter with threshold −1 dB, output −1 dB, attack and lookahead 1 ms.
Copy both files into place, from this folder:

```bash
mkdir -p ~/.local/share/easyeffects/irs ~/.local/share/easyeffects/output
```

```bash
cp windows-dolby-music.wav ~/.local/share/easyeffects/irs/
cp Windows-Music.json ~/.local/share/easyeffects/output/
```

Those are EasyEffects 8's folders. Version 7 keeps presets in
`~/.config/easyeffects/output/` and impulses in `~/.config/easyeffects/irs/`.
Then, in EasyEffects:

1. **Presets → Local**: load `Windows-Music`.
2. **☰ → Preferences → General**: switch on **Launch service at system
   startup**.
3. **Presets → Autoload**: pick **Meteor Lake-P HD Audio Controller
   Speaker** (GNOME calls it *Speaker - Meteor Lake-P HD Audio Controller*)
   and `Windows-Music`, press **+ Create**, and delete any older entries for
   the same device.

Keep **Speaker** as the output device in GNOME's sound settings, not *Easy
Effects Sink*.

## Not reproduced yet

- Dolby's volume leveler: up to +25 dB on quiet input, with output near
  −25 dBFS for anything above −30 dBFS input.
- Its stereo widening: side/mid +6.3 dB on correlated stereo.
