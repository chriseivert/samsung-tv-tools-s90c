# Advertising-package experiment

Scope: Samsung S90C on Tizen 9 build
`T-PTMCAKUC-0090-REL-202603190200`.

The goal is to determine whether Samsung's advertising packages feed the Smart
Hub **Top Picks For You** rail. That rail may be a recommendation surface rather
than a conventional advertisement. Removing ad packages is therefore not yet a
confirmed way to remove it.

Automated `tv-setup apply` remains unsupported on this build. These commands
use Tizen's package manager directly and test one component at a time.

## Host wrapper

From the `invaliddayta/samsung-tv-tools` checkout:

```sh
export TV_HOST=TV_IP_ADDRESS

tv() {
    nix --extra-experimental-features 'nix-command flakes' \
        run .#tv-access -- "$@"
}
```

## Observed packages

The following packages were present on October 27, 2026:

| Package | Name | Type | Version | Observed metadata |
|---|---|---|---|---|
| `adplatform` | Ad Player | WGT | 0.11.1 | Removable; not on-boot; not autorestart |
| `com.samsung.tv.ad-web-framework` | Ad Web Framework | TPK | 1.1.0324 | Removable; not on-boot; not autorestart |
| `com.samsung.tv.targeted-ad-service` | targeted-ad-service | TPK | 0.0.44 | Removable; on-boot; autorestart |

Inventory command:

```sh
tv 'pkgcmd -l | grep -Ei "adplatform|targeted.ad|ad.web.framework" || true'
```

Application metadata:

```sh
tv "sqlite3 -readonly -header -column /opt/dbspace/.pkgmgr_parser.db \
\"SELECT
    app_id,
    package,
    app_exec,
    app_type,
    app_mainapp,
    app_disable,
    app_support_disable,
    app_removable,
    app_onboot,
    app_autorestart,
    app_root_path
FROM package_app_info
WHERE package IN (
    'adplatform',
    'com.samsung.tv.targeted-ad-service',
    'com.samsung.tv.ad-web-framework'
)
ORDER BY package, app_id;\""
```

No `package_app_info_for_uid` row was returned for
`com.samsung.tv.targeted-ad-service` at the time of inspection.

## Temporary termination result

Tizen exposes lifecycle control through `app_launcher`:

```sh
tv 'app_launcher --terminate com.samsung.tv.targeted-ad-service'
```

The command successfully terminated PID 4527, but the application manager
relaunched the service within five seconds as PID 22725. This confirms that
termination alone is ineffective and agrees with `app_autorestart=true`.

Check its current state with:

```sh
tv '
app_launcher --is-running com.samsung.tv.targeted-ad-service || true
ps -ef | grep "[t]argeted-ad-service" || true
'
```

## Reversible package deactivation test

Tizen's installed `pkgcmd` advertises supported package activation and
deactivation operations:

```text
-D, --deactivate    disable package or app or apps or splash-screen
-A, --activate      enable package or app or apps or splash-screen
```

The deactivation test below was executed on October 27, 2026. It first made a
consistent SQLite backup on the TV. The backup contains package metadata and
should be treated as private.

```sh
tv '
set -eu

TEST_DIR=/opt/var/tv-ad-test
mkdir -p "$TEST_DIR"
chmod 700 "$TEST_DIR"

STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP="$TEST_DIR/pkgmgr_parser.$STAMP.db"

sqlite3 /opt/dbspace/.pkgmgr_parser.db ".backup $BACKUP"
chmod 600 "$BACKUP"

printf "=== BACKUP ===\n"
ls -l "$BACKUP"
sha256sum "$BACKUP"

printf "\n=== DEACTIVATE TARGETED AD SERVICE ===\n"
pkgcmd -D -t tpk \
    -n com.samsung.tv.targeted-ad-service \
    --global

sleep 8

printf "\n=== RESULT ===\n"
app_launcher --is-running \
    com.samsung.tv.targeted-ad-service || true
ps -ef | grep "[t]argeted-ad-service" || true
'
```

### Observed result

`pkgcmd` completed with `key[end] val[ok]`. Eight seconds later:

- no targeted-ad process was present;
- `app_launcher` reported the application unavailable to UID 0;
- the package directory and executable remained present;
- `package_app_info.app_disable` remained `false`;
- `package_info.package_disable` changed to `true`;
- no per-user override row was returned; and
- after leaving and reopening Smart Hub, **Top Picks For You remained visible**.

This was a successful package deactivation, not an uninstall. It establishes
that suppressing `targeted-ad-service` alone does not remove the rail. Reboot
persistence and other functional side effects remain unverified.

## Ad Player test

The WGT package `adplatform` was tested separately after restoring
`targeted-ad-service` to `package_disable=false`.

```sh
pkgcmd -D -t wgt -n adplatform --global
```

The operation set `package_info.package_disable` to `true`. Its files
remained installed, and `adplatform.ADPlayer` remained a symbolic link to
Samsung's signed `/usr/bin/wrt`. No Ad Player process was visible. After
leaving and reopening Smart Hub, **Top Picks For You remained unchanged**.
Therefore, disabling `adplatform` alone does not remove the rail.

Reactivate it with:

```sh
pkgcmd -A -t wgt -n adplatform --global
```

## Combined state and reboot result

All three packages were then disabled together with their supported global
package-deactivation operations:

```sh
pkgcmd -D -t wgt -n adplatform --global
pkgcmd -D -t tpk -n com.samsung.tv.targeted-ad-service --global
pkgcmd -D -t tpk -n com.samsung.tv.ad-web-framework --global
```

Readback showed `package_info.package_disable=true` for all three. After a hard
TV reboot, they remained disabled and no functional errors were observed in the
owner's initial check. **Top Picks For You remained visible and unchanged.**

This rules out these three packages, individually and together, as the sole
owner of the recommendation rail on this exact build. They remain disabled by
owner choice. Longer-term application compatibility and restoration by a future
app or firmware update remain unverified.

## Content Tiles provider test

The running app `com.samsung.tv.content-tiles-provider` is a removable,
autorestarting component inside the still-enabled
`com.samsung.tv.contentservicemanager` package. It was disabled at app scope:

```sh
pkgcmd -D -t app -n com.samsung.tv.content-tiles-provider --global
```

The operation completed successfully. Readback showed
`package_app_info.app_disable=true` for the provider while the parent package
remained `package_disable=false`; the provider process was absent and the
Content Service Manager process remained running. **Top Picks For You still
remained visible.** This rules out the provider as the sole owner of the rail.

Rollback:

```sh
pkgcmd -A -t app -n com.samsung.tv.content-tiles-provider --global
```

## Rollback

Reactivate the advertising packages with the supported package-manager operations:

```sh
tv '
pkgcmd -A -t wgt -n adplatform --global
pkgcmd -A -t tpk -n com.samsung.tv.targeted-ad-service --global
pkgcmd -A -t tpk -n com.samsung.tv.ad-web-framework --global

sleep 5
app_launcher --is-running \
    com.samsung.tv.targeted-ad-service || true
'
```

Do not restore the whole SQLite backup over the live database as routine
rollback. It is evidence and an emergency reference; `pkgcmd -A` is the normal
inverse operation.

## Safety boundary

- Do not test all three packages simultaneously.
- Do not use `pkgcmd -u` until deactivation behavior and reboot persistence
  have been characterized.
- Do not manually delete application directories.
- Verify Home, app launching, source switching, settings, and behavior after a
  cold boot before calling the change safe.
- The voice-oriented
  `com.samsung.tv.utterance-recommender-service` was observed running but has
  not been linked to the Smart Hub rail and is intentionally out of scope.
