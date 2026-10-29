# dax-curve-to-fir

Turns the Dolby-on pink-noise recording from
[DOLBY-CAPTURE.md](../../DOLBY-CAPTURE.md) into a minimum-phase impulse
response (`windows-dolby-<label>.wav`, 48 kHz, stereo, 8192 taps) for
EasyEffects' Convolver. The curve is smoothed to 1/6 octave and scaled so its
loudest point is 0 dB, so the filter only cuts and cannot clip.

```bash
./dax-curve-to-fir                      # reads ~/dax-measure/captures
./dax-curve-to-fir --label dynamic      # another Dolby profile's round
```

It needs only `numpy`. The curve is measured at one input level (−18 dBFS
pink noise). On the Duo, Dolby's tone shape changed by at most about 2 dB
between −60 and −14 dBFS input, except below 150 Hz and above 13 kHz
(measured 2026-10-29), so one curve is a fair copy. Dolby's level-dependent
gain (the volume leveler) is not in it.
