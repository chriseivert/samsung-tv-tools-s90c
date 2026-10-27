# S90C / Tizen 9 manual findings

Owner: chriseivert. Observed October 26, 2026. All observations are restricted to
`T-PTMCAKUC-0090-REL-202603190200`. No claim of general S90C compatibility.
No application removals, direct package-database edits, UEP patches, or
update-service changes were performed in the documented sessions. A targeted-ad
process was terminated and later package-disabled through supported Tizen tools.

## Root and interactive shell

`tv-access --probe` reported a working SDB handshake and archive-root chain;
`tv-access 'id -u'` returned `0`. The wrapper reported `dotnet` and
`sdbd-tarlauncher` present and automated cleanup unsupported for this build.

A detached Bash connection from the TV to the Linux controller succeeded.
`/usr/bin/script -q -c '/usr/bin/bash --noprofile --norc -i' /dev/null`
allocated `/dev/pts/0`. Working directory changes persisted. Host-side raw/no-echo
settings removed duplicated input. The connection was a manual, unauthenticated
TCP experiment, not the upstream authenticated controller. Disconnect cleanup,
signal handling, resize propagation, reboot recovery and reconnection are unverified.

```text
Uid:            0 0 0 0
Gid:            0 0 0 0
SMACK label:    User
CapInh:         00000000002000e2
CapPrm:         0000003fffffffff
CapEff:         0000003fffffffff
CapBnd:         0000003fffffffff
NoNewPrivs:     0
Seccomp:        0
```

These are the shell's credentials. They do not establish unrestricted access
through SMACK or unsigned native execution.

## Signature enforcement

An attempted unsigned ARM executable under a temporary `/opt/tv-native-check.*`
directory was rejected with `Operation not permitted`, shell status `126`.

```text
[Verification fail] file /opt/tv-native-check.<temporary>/exit42 is not signed. Sign it.(fsname:vdfs, mnt_flags:8)
```

The pasted Base64 differed from the intended executable. This establishes a
signature rejection but does not validate the ELF or prove the intended exit-42
test would otherwise execute. No UEP state word was read or modified.

Observed mounts included read-only VDFS `/` and writable VDFS `/opt`; `/opt`
had options `rw,noatime,dncs` and no `noexec` flag.

## Source metadata

`/usr/lib/libsource-api.so` exists. Initial Vconf results:

```text
memory/system/source_type = -1 (Int32)
memory/eden/source/current_source = {"source_type":"tv-service","uuid":"SOURCE_TYPE_TV"} (String)
```

Source transitions were not tested because the owner was away. Listing,
selection and HDMI presentation recovery remain in test — unverified.

## Input devices and utilities

Candidate input devices, identified by inventory only:

| Node at capture time | Name | Interpretation |
|---|---|---|
| event1 | wt61p807 rc device | Candidate IR input |
| event2 | wt61p807 panel key device | Candidate panel buttons |
| event3 | Smart Control | Candidate remote input path |
| event7 | Smart Control 2016, bus 0005 | Candidate Bluetooth remote |

Device nodes may change after restart. No physical-event mapping has been
validated. A proposed capture exited before its heading because a prerequisite
utility check failed; the missing utility was not identified. This is not
evidence of device-read denial or absence of remote events.

Present: `sqlite3`, `vconftool`, `pkgcmd`, `app_launcher`, `input_keyevent`,
`dbus-send`, `busctl`, `bash`, `sh`, `setsid`, `script`.
The utility inventory did not find `evtest`, `getevent`, TV-side `socat`, `nc`,
`netcat`, `busybox`, or `python3`.

## Package metadata

SQLite read-only queries succeeded against `/opt/dbspace/.pkgmgr_parser.db`.
The schema exposes `package_app_info.app_disable`, `app_support_disable`,
`app_removable`, and per-user `package_app_info_for_uid.is_disabled`.
The per-user table has an insert trigger that can remove redundant default rows.
Schema similarity alone does not verify package-manager cache behavior.

For `org.tizen.was-appsync`:

| Field | Observed value |
|---|---|
| package | org.tizen.was-appsync |
| executable | /usr/apps/org.tizen.was-appsync/bin/was-appsync |
| app_disable | false |
| app_support_disable | false |
| app_removable | false |
| app_onboot | false |
| app_autorestart | false |
| per-user rows | None returned |
| dependency rows, either direction | None returned |
| running process at inspection | None visible in `ps -ef` |

No rows in the dependency table do not rule out runtime callers. No running
process at one instant does not establish that it never launches. The owner
account was `owner:5001:100`. No guard change or restoration test was attempted.

### Advertising packages

The following packages were installed on October 27, 2026:

| Package | Type | Version | Removable | On boot | Autorestart |
|---|---|---:|---|---|---|
| `adplatform` | WGT | 0.11.1 | true | false | false |
| `com.samsung.tv.ad-web-framework` | TPK | 1.1.0324 | true | false | false |
| `com.samsung.tv.targeted-ad-service` | TPK | 0.0.44 | true | true | true |

`com.samsung.tv.targeted-ad-service` was running as the owner user. A supported
`app_launcher --terminate` operation exited successfully, but Tizen relaunched
the service within five seconds with a new PID.

A subsequent supported global `pkgcmd --deactivate` operation completed
successfully. The files remained installed, the process stayed absent,
`package_app_info.app_disable` remained `false`, and
`package_info.package_disable` became `true`. No per-user override row was
returned. After Smart Hub was left and reopened, **Top Picks For You remained
visible**. Reboot persistence and unrelated side effects remain unverified.
No package was uninstalled.

See [Advertising-package experiment](AD-REMOVAL.md) for commands, backup,
verification, rollback and safety boundaries.

## Update state

| Vconf key | Value | Type |
|---|---|---|
| db/menu/support/softwareupdate/autoupdate | 1 | Int32 |
| db/SyncML/ivi-oma-dm-service/software-update/autoupdate/setting | 1 | Int32 |
| db/apps/auto_update | False | Boolean |
| db/built-in-app-upgrader/server_upgrade | True | Boolean |
| db/menu/support/softwareupdate/reboot | 0 | Int32 |
| db/menu/support/softwareupdate/upgrade_verified_successfully | 0 | Int32 |
| db/menu/support/softwareupdate/upgrade_finalization_schedule | 0 | Int32 |

`/mnt/backup/OS_UPGRADE_FLAG` and `/mnt/systemrw/upgrade/.key` were absent.
This excludes only those specific pending-update indicators. UI correlation,
downloaded-update state and persistence after restart have not been verified.

| Unit | ActiveState | SubState | UnitFileState |
|---|---|---|---|
| pkgmgr-info.service | active | running | disabled |
| pkgmgr-info.socket | active | running | disabled |
| swu-auto-upgrade.service | active | running | disabled |
| swu-auto-upgrade.path | active | waiting | disabled |
| swu-auto-upgrade.timer | active | running | disabled |

Disabled enablement does not mean inactive runtime state. No service was stopped
or disabled during this investigation.

## Remaining evidence

- Exact full model designation, size, regional variant and tools checkout commit.
- Fresh screenshot capture and assessment separate from the wrapper's reported record.
- Valid unsigned-ELF test, if useful, and exact-build UEP investigation.
- Source list, physical input transitions and selected-source confirmation.
- Managed native getters for display/HDMI policy, then bounded functional tests.
- Speaker getter results, controlled setter readback and actual volume events.
- Physical remote event mapping and suppression with recovery behavior.
- Native app/source/lifecycle/HDMI event transitions.
- HDMI frame freshness/geometry and bounded overlay visibility/cleanup.
- App-sync guard, native cache refresh and package recovery behavior before cleanup support.
