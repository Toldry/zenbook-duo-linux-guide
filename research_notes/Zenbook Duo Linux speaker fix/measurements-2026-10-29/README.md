# Loopback measurements, 2026-10-29

Windows Dolby (DAX3) on the author's Zenbook Duo UX8406MA (subsystem
1043:1C43), recorded with
[DOLBY-CAPTURE.md](../../../DOLBY-CAPTURE.md) using the converter's
`tools/measure_dax/` at commit 430e3a5 or later.

| Setting | Value |
|---|---|
| Dolby profile | Music, intelligent EQ Balanced (from `C:\ProgramData\Dolby\DAX3\Runtime.xml`) |
| Tuning XML | `dax3_ext_rtk.inf_amd64_12abc9a96438faa5/DEV_0294_SUBSYS_10431C43_PCI_SUBSYS_1C431043.xml`, `tuning_version` 11, sha256 `8530617c…eaad8` |
| Rounds | `off` (Dolby off in Dolby Access), `music`, and `raw` (Audio enhancements off; sweep and pink only) |
| Output format | 48 kHz |

Files:
- [`analysis-summary.txt`](analysis-summary.txt): the converter's
  `analyze.py` output (`--profile music --curve balanced`). Its tables are
  scaled to each curve's peak.
- [`capture-summary.txt`](capture-summary.txt):
  [`dax-capture-summary`](../../../tools/dax-capture-summary/) output in
  absolute dB, including the leveler ladder and stereo widening.

What they show is written up in
[windows_dolby_chain.md](../windows_dolby_chain.md#addendum-2026-10-29-loopback-measurements-on-the-users-duo).
The impulse built from them is in
[presets/zenbook-duo-ux8406ma](../../../presets/zenbook-duo-ux8406ma/).

- [`dax-spectra.tgz`](dax-spectra.tgz): every `spectrum_*.npz` that
  `analyze.py` wrote (`captures/` and `captures-raw/`). Unpack it in
  `~/dax-measure`, and `dax-capture-summary` and `dax-curve-to-fir` run
  without new recordings. `dax-curve-to-fir` rebuilds the committed impulse
  from it bit for bit (checked 2026-10-29).

The recordings themselves (`~/dax-measure/captures*/`) are not in the repo
because of their size.
