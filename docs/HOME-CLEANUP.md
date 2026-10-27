# Smart Hub Home cleanup

Scope: owner-tested Samsung S90C on Tizen 9 build
`T-PTMCAKUC-0090-REL-202603190200`, October 27, 2026.

This procedure removes Samsung's server-defined **For You** rails while retaining:

- the selected Home Screen application launcher; and
- the **Continue Playing** row.

It was verified visually after terminating and reopening Home Media. Cold-boot
persistence and behavior after Samsung refreshes the Terra response have not yet
been recorded.

## Result and safety boundary

The working change is a narrow allowlist in Home Media's rotating
ContentsBrowser cache. It does not uninstall applications, patch Samsung
binaries, or disable the Home renderer.

**Do not disable or remove `com.samsung.tv.coba.edenview`.** Testing proved that
doing so breaks the graphical interface after reboot. Reactivating Edenview
restored the GUI.

Keep both cache slots backed up. The cache can contain provider data, service
identifiers, viewing-related metadata, and signed URLs; review it before sharing.

## What did not remove the rail

The following tests did not remove **Top Picks For You**:

- globally disabling `adplatform`;
- globally disabling `com.samsung.tv.targeted-ad-service`;
- globally disabling `com.samsung.tv.ad-web-framework`;
- disabling all three together and hard rebooting;
- disabling the `com.samsung.tv.content-tiles-provider` application;
- setting the string Vconf key `db/eden/homeRecommendation` to `false`;
- setting the runtime `TableEntity.visible` value to zero; Home Media regenerated it.

Those results show that the rail is not owned solely by the conventional ad
packages or Content Tiles provider. See [Advertising-package experiment](AD-REMOVAL.md).

## Home implementation identified

The observed implementation path is:

| Component | Role observed |
|---|---|
| `HomeMedia.dll` | Thin Home Media host |
| `CompDHCategory.dll` | Creates and renders dynamic Home categories |
| `CompTerra.dll` | Fetches and transforms server-provided Terra rows |
| `ViewPluginTerra.dll` | Renders Terra content tiles |
| `Tizen.TV.Service.CoBA2.Core.dll` | CoBA category infrastructure |
| `shared/trusted/sqlite.db` | Generated runtime UI model |
| `.ContentsBrowserCache.1/.2` | Rotating persistent metadata cache |

Relevant server configuration strings found in `CompTerra.dll` include:

- `rtc/db/comss/gpmurl/terra`
- `rtc/db/comss/targetgrouptag/terra`
- `terra/service/v3/`
- `home?contentcount=max&groupcount=max&tab_supported=true&`

The runtime database is:

```text
/opt/usr/home/owner/apps_rw/com.samsung.tv.home.media/shared/trusted/sqlite.db
```

Changing its Top Picks entity to `visible=0` did not affect the active GUI and
was reset to `1` after Home Media restarted. It is an output/cache, not the
correct persistent control point.

## Additional reverse-engineering findings

- `com.samsung.tv.coba.dhcategory` is a logical Home component on this build,
  not a separately installed package. Its implementation is
  `/opt/usr/apps/com.samsung.tv.coba.newhome/shared/res/CompDHCategory.dll`.
- Terra implementation files were found at
  `/opt/usr/apps/com.samsung.tv.ContentsBrowser/shared/res/CompTerra.dll` and
  `ViewPluginTerra.dll`.
- CoBA API assemblies were found under
  `/usr/share/dotnet.tizen/tvappapi/`.
- `ServerAPI.HomeRestReceive` passes the Terra response into
  `ViewModel.ParseHomeData`; the exact editorial row identifiers are supplied
  by the server rather than hard-coded in the client.
- `com.samsung.tv.coba.adagent` contains immersive top-banner and sponsored
  label logic. That is distinct from the curated
  `[foryou][curated]_top_picks_for_you` category.
- No exact Top Picks source row was returned from Home Media's `coba.db`.
  The matching entities appeared in `shared/trusted/sqlite.db`, and direct
  visibility changes there were regenerated.
- `db/eden/category/list` contained the top-level Life Plus, Game and Media
  category IDs. It was not changed because it controls broader Home navigation,
  not just recommendation rows.
- The cache contained derived metadata such as `CacheUpdateToken`,
  `CacheFirstRowPMID`, `CacheTabCategoryIDList`, Continue Watching data,
  provider preferences, and polling values. The successful cleanup changed only
  the first-row pointer and tab-22 item list.

## Rotating cache format

The controlling files are:

```text
/opt/usr/home/owner/apps_rw/com.samsung.tv.home.media/data/.ContentsBrowserCache.1
/opt/usr/home/owner/apps_rw/com.samsung.tv.home.media/data/.ContentsBrowserCache.2
```

There is intentionally no unsuffixed live file. Samsung alternates between
`.1` and `.2`.

Each file is UTF-8 text with a CoBA envelope:

```text
<decimal generation>
<one-line JSON document>
EOFCOBA
```

Observed generations were `91694` and `91693`. The outer JSON contains
JSON-encoded strings. Two keys control the tested For You layout:

| Key | Observed value before cleanup |
|---|---|
| `CacheFirstRowPMID` | `TerraCategory_22_83114` |
| `CacheTabCategoryIDList` | Tab 22 contained 28 row identifiers |

`FirstTab_FirstRow` is the special cache alias for
`TerraCategory_22_83114`, the **Top Picks For You** row. Removing that alias
and clearing `CacheFirstRowPMID` removed Top Picks.

The selected Home Screen applications are represented by the separate
`d/launcher` runtime component. They are not an item in tab 22's Terra list.
Continue Playing is `d/continuewatchrow` and cache item
`22_GROUP_ID_CW`.

## Observed For You inventory

The following tab-22 cache entries were observed after Top Picks was removed:

| Cache identifier | Runtime title or role | Cleanup action |
|---|---|---|
| `22_GROUP_ID_CW` | Continue Playing | Keep |
| `22_83457` | Fun Family Frights | Remove |
| `22_80957` | New on TV | Remove |
| `22_GROUP_ID_BUBBLE_83552` | Sports: Live & Upcoming | Remove |
| `22_GROUP_ID_EXTERNAL_d/sponsoredrow` | Sponsored row, hidden at capture | Remove |
| `22_83551` | Genres | Remove |
| `22_83335` | Halloween Horror Essentials | Remove |
| `22_GROUP_ID_EXTERNAL_d/external.vac.row` | Vision AI Companion, hidden at capture | Remove |
| `22_GROUP_ID_EXTERNAL_d/sponsoredrow2` | Second sponsored row, hidden at capture | Remove |
| `22_83473` | Halloween Horrors - Scream, Survive and Stream | Remove |
| `22_53683` | New Movies with Subscription | Remove |
| `22_53684` | New Movies to Rent or Buy | Remove |
| `22_83163` | Complimentary Movies | Remove |
| `22_83164` | Complimentary TV Shows | Remove |
| `22_83573` | Stick: Season 1 | Remove |
| `22_83521` | Marvel TV Series | Remove |
| `22_83475` | Cozy Corner - Relax and Play | Remove |
| `22_83483` | Top 10: Movies in the U.S. | Remove |
| `22_51036` | Top 20: Streaming TV | Remove |
| `22_83124` | Title not populated at capture | Remove |
| `22_83550` | Stick: Season One | Remove |
| `22_83525` | Unsolved and Untold: Watch Free | Remove |
| `22_51140` | Title not populated at capture | Remove |
| `22_53945` | Title not populated at capture | Remove |
| `22_82722` | Title not populated at capture | Remove |
| `22_37550` | Trending | Remove |
| `22_80788` | Title not populated at capture | Remove |
| `22_GROUP_ID_OPTIONS` | Media Options | Remove |

The titles and numeric identifiers are server-controlled and can change.
Allowlisting Continue Playing is therefore more durable than maintaining a
title-based blocklist.

## Host wrapper

Run from the working `invaliddayta/samsung-tv-tools` checkout:

```sh
export TV_HOST=TV_IP_ADDRESS

tv() {
    nix --extra-experimental-features 'nix-command flakes' \
        run .#tv-access -- "$@"
}
```

The tested controller required root to access its Nix daemon socket.

## Capture both live slots

```sh
umask 077
WORK_DIR="$HOME/s90c-research/apps-and-continue-only-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$WORK_DIR"

for SLOT in 1 2; do
    REMOTE="/opt/usr/home/owner/apps_rw/com.samsung.tv.home.media/data/.ContentsBrowserCache.$SLOT"
    tv "base64 '$REMOTE'" |
        base64 -d >"$WORK_DIR/ContentsBrowserCache.$SLOT"
done
```

Both observed cache files were about 41.8 KiB, safely below the
`tv-access` one-MiB output cap when Base64 encoded.

## Build the allowlisted slots

Run this on the controller, not the TV:

```sh
python3 - "$WORK_DIR" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
allowed = {"22_GROUP_ID_CW"}

for source in sorted(root.glob("ContentsBrowserCache.[12]")):
    lines = source.read_bytes().splitlines()
    generation = lines[0].decode("ascii")
    footer = lines[-1].decode("ascii")
    assert footer == "EOFCOBA"

    outer = json.loads(b"\n".join(lines[1:-1]).decode("utf-8"))
    tabs = json.loads(outer["CacheTabCategoryIDList"])
    found = False

    for tab in tabs:
        if str(tab.get("tab_id")) != "22":
            continue

        found = True
        before = list(tab.get("items", []))
        tab["items"] = [item for item in before if item in allowed]

        if tab["items"] != ["22_GROUP_ID_CW"]:
            raise RuntimeError(f"Unexpected allowlist result: {tab['items']!r}")

        print(f"{source.name}: removed {len(before) - 1}, kept {tab['items']}")

    if not found:
        raise RuntimeError("For You tab 22 was not found")

    outer["CacheFirstRowPMID"] = ""
    outer["CacheTabCategoryIDList"] = json.dumps(
        tabs, ensure_ascii=False, separators=(",", ":")
    )

    destination = source.with_name(source.name + ".apps-and-cw-only")
    encoded = json.dumps(outer, ensure_ascii=False, separators=(",", ":"))
    destination.write_text(
        f"{generation}\n{encoded}\n{footer}\n",
        encoding="utf-8",
    )
PY

sha256sum "$WORK_DIR"/ContentsBrowserCache.*.apps-and-cw-only
```

On the tested cache, this retained one item and removed 27.

## Stage and verify

```sh
for SLOT in 1 2; do
    LOCAL="$WORK_DIR/ContentsBrowserCache.$SLOT.apps-and-cw-only"
    REMOTE="/opt/usr/home/owner/apps_rw/com.samsung.tv.home.media/data/.ContentsBrowserCache.$SLOT.apps-and-cw-only"
    EXPECTED=$(sha256sum "$LOCAL" | awk '{print $1}')
    PAYLOAD=$(base64 -w 0 "$LOCAL")

    tv "printf '%s' '$PAYLOAD' | base64 -d > '$REMOTE'"

    ACTUAL=$(tv "sha256sum '$REMOTE'" | awk '{print $1}')
    [ "$ACTUAL" = "$EXPECTED" ] || {
        printf 'Slot %s hash mismatch\n' "$SLOT" >&2
        exit 1
    }

    unset PAYLOAD
done
```

Do not install a slot whose remote hash differs from its local hash.

## Install atomically

```sh
tv '
set -eu

BASE=/opt/usr/home/owner/apps_rw/com.samsung.tv.home.media/data/.ContentsBrowserCache
BACKUP_DIR=/opt/var/tv-ad-test
STAMP=$(date +%Y%m%d-%H%M%S)

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

app_launcher --terminate com.samsung.tv.home.media || true
sleep 3

for SLOT in 1 2; do
    BACKUP="$BACKUP_DIR/ContentsBrowserCache.$SLOT.before-apps-cw-only.$STAMP"
    cp -p "$BASE.$SLOT" "$BACKUP"
    chmod 600 "$BACKUP"

    NEW="$BASE.$SLOT.apps-and-cw-only"
    LIVE="$BASE.$SLOT"

    chown owner:system_share "$NEW"
    chmod 644 "$NEW"
    mv -f "$NEW" "$LIVE"

    sha256sum "$BACKUP" "$LIVE"
done

sync
printf "Backup stamp: %s\n" "$STAMP"
'
```

Reopen Home:

```sh
nix --extra-experimental-features 'nix-command flakes' \
    run .#tv-key -- XF86Home sleep:12
```

The owner observed the selected application icons and Continue Playing while
the remaining For You rails were gone.

## Verification

Extract the JSON body and list the remaining tab-22 items:

```sh
tv '
CACHE=/opt/usr/home/owner/apps_rw/com.samsung.tv.home.media/data/.ContentsBrowserCache.1
BODY=/tmp/contentsbrowser-verify.json

sed "1d;\$d" "$CACHE" >"$BODY"

sqlite3 -readonly -header -column ":memory:" "
WITH cache AS (
    SELECT CAST(readfile('''$BODY''') AS TEXT) AS document
),
tabs AS (
    SELECT tab.value AS tab
    FROM cache
    JOIN json_each(
        json_extract(document, '''$.CacheTabCategoryIDList''')
    ) AS tab
    WHERE json_extract(tab.value, '''$.tab_id''') = '''22'''
)
SELECT item.key AS position, item.value AS cache_identifier
FROM tabs
JOIN json_each(json_extract(tabs.tab, '''$.items''')) AS item;
"

rm -f "$BODY"
'
```

Expected result:

```text
position  cache_identifier
--------  ------------------
0         22_GROUP_ID_CW
```

Also verify visually. Runtime entities can remain in the generated SQLite model
temporarily even when they are no longer presented.

## Rollback

Use the exact matching pair printed during installation:

```sh
tv '
set -eu

BASE=/opt/usr/home/owner/apps_rw/com.samsung.tv.home.media/data/.ContentsBrowserCache
BACKUP_DIR=/opt/var/tv-ad-test
STAMP=REPLACE_WITH_BACKUP_STAMP

app_launcher --terminate com.samsung.tv.home.media || true
sleep 3

for SLOT in 1 2; do
    BACKUP="$BACKUP_DIR/ContentsBrowserCache.$SLOT.before-apps-cw-only.$STAMP"
    [ -f "$BACKUP" ]
    cp -p "$BACKUP" "$BASE.$SLOT"
    chown owner:system_share "$BASE.$SLOT"
    chmod 644 "$BASE.$SLOT"
done

sync
'
```

Then reopen Home with `tv-key XF86Home`. Do not restore
`.pkgmgr_parser.db` to roll back this cache-only experiment.

## Remaining tests

- Hard reboot and verify the allowlist remains active.
- Leave the TV online through at least one Terra refresh interval.
- Check whether a Samsung firmware/app update regenerates the cache.
- Confirm Live and Apps tabs are unaffected.
- Package the procedure into a guarded helper with automatic validation and
  rollback.
