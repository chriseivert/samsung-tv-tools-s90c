# Attribution

Root access in the manual investigation was provided by
[invaliddayta/samsung-tv-tools](https://github.com/invaliddayta/samsung-tv-tools).
Its original code is MIT licensed; its archive-root bootstrap is attributed to
[chris-ritsen/samsung-tv-root](https://github.com/chris-ritsen/samsung-tv-root),
which uses the Unlicense and credits motodrizzle's earlier S90D work.

This repository contains original research notes and a new Python verifier.
It does not redistribute the root bootstrap, Samsung binaries, firmware,
signing keys or upstream exploit payloads.

API names and read-only command shapes were checked against upstream reference
`3b97edf3762db7670585d73e29623dc56195bf98`, including:

- `src/samsung_tv_root/source.py`
- `payloads/qn90f/Qn90fSourceControl.cs`
- `src/samsung_tv_root/volume.py`
- `src/samsung_tv_root/local_dimming.py`
- `payloads/common/SamsungTvEventAgent.cs`
- `payloads/qn90f/Qn90fDisplayNative.cs`
- `payloads/qn90f/Qn90fScreenAnalysisDump.cs`
- `payloads/qn90f/Qn90fEflTextOverlayProbe.cs`

These references establish upstream interfaces, not successful S90C behavior.
