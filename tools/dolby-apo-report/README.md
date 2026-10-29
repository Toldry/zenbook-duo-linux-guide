# dolby-apo-report

Reads a mounted Windows partition and prints how Windows attaches Dolby's
audio effects (APOs) to the speakers: the effect GUIDs on each audio endpoint,
the DLL behind each GUID, Dolby's registry keys, the bound sound drivers, the
registry lines of the Dolby and ASUS/Realtek driver `.inf` files, every copy of
the UX8406MA tuning XML, and Dolby's saved user settings. Nothing on the
Windows partition is changed.

```bash
sudo apt install libwin-hivex-perl
# Open the Windows partition in Files first (it mounts at /run/media/$USER/OS).
sudo ./dolby-apo-report > ~/dolby-apo-report.txt
```

Pass the mount point as the first argument if Windows is mounted elsewhere.
If Windows was last shut down with Fast Startup on, the registry on disk can
lag slightly behind what Windows had in memory.

It serves [DOLBY-CAPTURE.md](../../DOLBY-CAPTURE.md): the loopback recording
there includes every effect after Dolby, so knowing the chain tells you what a
recording contains.
