# Samsung TV tools: S90C research

Owner-tested findings and an unattended verifier for Samsung S90C / Tizen 9.
Companion to [invaliddayta/samsung-tv-tools](https://github.com/invaliddayta/samsung-tv-tools),
using the archive-root work from [chris-ritsen/samsung-tv-root](https://github.com/chris-ritsen/samsung-tv-root).
This repository does not supply a new root exploit or establish compatibility for other builds.

## Tested TV

| Property | Observed value |
|---|---|
| Model | S90C, owner reported; exact model/size not yet recorded |
| Tizen | 9.0.0 (Tizen9/TV) |
| Build | `T-PTMCAKUC-0090-REL-202603190200` |
| Kernel | Linux 5.4.77, ARMv7 (`armv7l`) |
| Kernel build date | January 5, 2026 |
| Test date | October 26, 2026 |
| Root route | `samsung-tv-tools` direct-SDB archive-launcher wrapper |
| Tested tools revision | Not captured in the original manual session |

## Results

Verified means observed in the owner's terminal output. In test means prerequisites
or partial readbacks exist, without a completed functional test. This is not an
unmodified upstream controller test.

| Capability | S90C result |
|---|---|
| Root command execution | Verified UID/GID 0 |
| Interactive root shell | Verified Bash TCP connection and PTY via installed `script` |
| Remote key injection | Command returned `ok`; physical effect not independently recorded |
| Screenshot | Reported by local compatibility output; fresh capture not independently reviewed here |
| Unsigned native execution | Signature-verification rejection observed |
| UEP status/control | In test; no validated kernel-state read or disable operation |
| Current-source metadata | Readable; input-change behavior unverified |
| Source listing / HDMI selection | In test — unverified |
| Remote observation / filtering | In test — unverified; original capture exited before reading |
| Volume / display / events / HDMI policies | Not yet functionally tested |
| HDMI analysis capture / overlays | Not yet tested; distinct from compositor screenshots |
| LCD local-dimming controls | Not applicable to S90C OLED as backlight-zone control |
| Ad-package suppression | In test — three packages identified; targeted-ad service termination triggered immediate autorestart; deactivation pending |\n| App cleanup / restoration prevention | In test — metadata inspected; no uninstall performed |

See [manual evidence](docs/FINDINGS.md) for exact observations and limitations.
The [persistent reverse-shell guide](docs/ROOT-SHELL.md) records the detached
`setsid -f` callback that survives the bounded command runner. The
[advertising-package experiment](docs/AD-REMOVAL.md) records the supported
inspection, deactivate, verification and rollback commands.\nThe [advertising-package experiment](docs/AD-REMOVAL.md) records the supported\ninspection, deactivate, verification and rollback commands.

## Unattended verifier

Run on the Linux computer containing your working `samsung-tv-tools` checkout.
Requires Python 3 and the same transport dependencies as `tv-access`. Nix mode
enables `nix-command` and `flakes` for each invocation.

```sh
python3 tools/verify.py \
  --repo /path/to/samsung-tv-tools \
  --tv TV_IP_ADDRESS \
  --nix
```

Without Nix, omit `--nix` after installing the wrapper's Python/Bash/OpenSSL
dependencies. Run `python3 tools/verify.py --help` for options.

The verifier collects identity, source readbacks, speaker getters, picture/HDR
getters, AVOC introspection, API library presence, input-device open access,
a four-second filtered D-Bus event sample, analysis process inventory, and
existing signature-verification logs. Each root command has a 20-second TV
deadline plus a bounded host-side timeout. Checks run sequentially without retry.

Reports are created in a new private directory under `~/s90c-research/`:

- `summary.md`: capability results and remaining gaps.
- `results.json`: complete commands, stdout, stderr, statuses, and metadata.
- Numbered evidence files for each probe.

Read-only describes the probes. The underlying `tv-access` transport still
performs its normal temporary root bootstrap and staging. D-Bus getters and
introspection may activate their service. The script does not change TV settings,
switch inputs, change volume, turn off the display, grab input devices, read live
video buffers, or patch kernel state. It does not certify all upstream features.
Interface presence is never counted as a functional pass.

The verifier has passed local syntax, report-classification and simulated transport
checks. It has not yet been run on the TV. Its JSON/text evidence is private by
default; review it before sharing. It can contain device names, source identifiers,
paths and process arguments.

## Research order

1. Capture the exact model and `samsung-tv-tools` commit.
2. Run the unattended verifier and review failures.
3. Verify source transitions and selected HDMI input while physically present.
4. Test speaker changes, display off/wake and physical remote events individually.
5. Investigate managed API helpers for source listing, display and HDMI policies.
6. Develop exact-build cleanup support with baseline/readback and recovery evidence.

Keep the working archive-root path. QN90B/QN90F kernel offsets and exploit profiles
are not evidence of compatibility with this S90C build.

## Attribution

This is a separate research companion, not a copy of either upstream codebase.
The verifier uses read-only command sequences and API names documented in upstream
source. [Source references and license](THIRD_PARTY.md).
