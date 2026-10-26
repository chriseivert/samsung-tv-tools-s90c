#!/usr/bin/env python3
"""Unattended, read-only capability evidence collector for samsung-tv-tools.

Run on the Linux controller, NOT on the television. Python standard library only.
Uses the existing tv-access transport; no new listener, TV helper, or boot service.
Interface presence is never scored as functional support. No settings setters,
input injection/grabs, source changes, display changes, memory scans or firmware
operations. tv-access itself performs its usual temporary root bootstrap/staging.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

UPSTREAM = 'https://github.com/chris-ritsen/samsung-tv-root'
REFERENCE = '3b97edf3762db7670585d73e29623dc56195bf98'
SOURCE_FILES = [
    'README.md', 'src/samsung_tv_root/source.py',
    'payloads/qn90f/Qn90fSourceControl.cs', 'src/samsung_tv_root/volume.py',
    'src/samsung_tv_root/local_dimming.py',
    'payloads/common/SamsungTvEventAgent.cs',
    'payloads/qn90f/Qn90fDisplayNative.cs',
    'payloads/qn90f/Qn90fScreenAnalysisDump.cs',
    'payloads/qn90f/Qn90fEflTextOverlayProbe.cs',
]


def bus(method, *args, avoc=False):
    if avoc:
        endpoint = ['org.tizen.tv.avoc', '/org/tizen/tv/avoc',
                    'org.tizen.tv.avoc.AvOutputControl']
    else:
        endpoint = ['org.tizen.speakermanager', '/Org/Tizen/SpeakerManagerInternal',
                    'org.tizen.speakermanager']
    return shlex.join(['busctl', '--system', '--timeout=2', 'call',
                       *endpoint, method, *args])


PROBES = [
    ('identity', 'Root identity',
     'id; uname -a; cat /etc/os-release; '
     'cat /proc/$$/attr/current; printf "\\n"; '
     'grep -E "^(Uid|Gid|CapInh|CapPrm|CapEff|CapBnd|NoNewPrivs|Seccomp):" /proc/$$/status'),
    ('tools', 'Available utilities',
     'for c in bash sh setsid script sqlite3 vconftool pkgcmd app_launcher '
     'input_keyevent busctl dbus-send dbus-monitor aul_test timeout od dd '
     'hexdump readelf nm strings dotnet; do '
     'if command -v "$c"; then :; else printf "MISSING %s\\n" "$c"; fi; done'),
    ('source_type', 'Current source integer',
     'vconftool get memory/system/source_type'),
    ('source_json', 'Current source metadata',
     'vconftool get memory/eden/source/current_source'),
    ('libraries', 'Native API prerequisites',
     'for p in /usr/lib/libsource-api.so /usr/lib/libvconf.so.0 '
     '/usr/lib/libaul.so.0 /usr/lib/libdeviced.so.1 '
     '/usr/lib/libelementary.so.1 /usr/lib/libevas.so.1 '
     '/usr/lib/libecore.so.1 /usr/lib/libcapi-ui-efl-util.so.0; do '
     'if [ -r "$p" ]; then ls -l "$p"; else printf "UNAVAILABLE %s\\n" "$p"; fi; done'),
    ('volume', 'Speaker volume getter', bus('GetSpeakerVolume')),
    ('mute', 'Speaker mute getter', bus('GetSpeakerMute')),
    ('speaker_support', 'Speaker support-type getter', bus('GetSpeakerSupportType')),
    ('picture_active', 'Active picture-mode getter', bus('GetPictureMode', 'i', '0', avoc=True)),
    ('picture_saved', 'Saved picture-mode getter', bus('GetPictureMode', 'i', '1', avoc=True)),
    ('hdr', 'HDR status getter', bus('GetHdrStatus', avoc=True)),
    ('avoc_interface', 'AV output-control introspection',
     'busctl --system --timeout=2 --no-pager introspect '
     'org.tizen.tv.avoc /org/tizen/tv/avoc org.tizen.tv.avoc.AvOutputControl'),
    ('input_devices', 'Input inventory', 'cat /proc/bus/input/devices; ls -l /dev/input'),
    ('input_access', 'Remote device open checks (no reads or grabs)',
     'for p in /dev/input/event*; do '
     '[ -e "$p" ] || continue; '
     'if (exec 3<"$p"); then printf "OPEN_OK %s\\n" "$p"; '
     'else printf "OPEN_FAILED %s\\n" "$p"; fi; done'),
    ('native_events', 'Bounded native D-Bus signal observation', r'''
command -v dbus-monitor >/dev/null 2>&1 || exit 77
command -v sleep >/dev/null 2>&1 || exit 77
dbus-monitor --system "type='signal',interface='org.tizen.tv.appfw.appctxmgr'" \
    "type='signal',interface='org.tizen.aul.AppStatus'" \
    "type='signal',interface='org.tizen.speakermanager',member='SpeakerVolumeChanged'" &
monitor=$!
trap 'kill "$monitor" 2>/dev/null; wait "$monitor" 2>/dev/null' EXIT
sleep 4
if kill -0 "$monitor" 2>/dev/null; then
    printf '\nMONITOR_ALIVE_AT_END\n'
else
    wait "$monitor"
    rc=$?
    printf '\nMONITOR_EXITED=%s\n' "$rc"
    exit "$rc"
fi
'''),
    ('capture_prerequisites', 'HDMI analysis processes (no frame or memory access)',
     'ps -ef | grep -E "[s]creen-analysis-discovery-service|[s]a-ui-detector"; '
     'for p in /usr/bin/screen-analysis-discovery-service /usr/bin/sa-ui-detector '
     '/usr/apps/com.samsung.tv.screen-analysis-discovery-service/bin/screen-analysis-discovery-service '
     '/usr/apps/com.samsung.tv.screen-analysis-ui-detector/bin/sa-ui-detector; do '
     '[ ! -e "$p" ] || ls -l "$p"; done; :'),
    ('signature_evidence', 'Existing signature-verification log evidence',
     'dmesg | grep -Ei "verification fail|not signed|UEP" | tail -n 20'),
    ('mounts', 'Execution mount context', 'cat /proc/mounts'),
]


def text_bytes(value):
    if value is None:
        return ''
    return value.decode('utf-8', 'replace') if isinstance(value, bytes) else value


def execute(prefix, command, repo, env, deadline):
    try:
        p = subprocess.run(prefix + [command], cwd=repo, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=deadline + 45)
        return {'returncode': p.returncode, 'stdout': text_bytes(p.stdout),
                'stderr': text_bytes(p.stderr), 'host_timeout': False}
    except subprocess.TimeoutExpired as e:
        return {'returncode': None, 'stdout': text_bytes(e.stdout),
                'stderr': text_bytes(e.stderr), 'host_timeout': True}
    except OSError as e:
        return {'returncode': None, 'stdout': '', 'stderr': str(e),
                'host_timeout': False}


def pair(result):
    if result['returncode'] != 0:
        return None
    match = re.fullmatch(r'ii\s+(-?\d+)\s+(-?\d+)', result['stdout'].strip())
    if match and int(match[2]) == 0:
        return int(match[1])
    return None


def summarize(results, model):
    root = results['identity']
    root_ok = root['returncode'] == 0 and re.search(r'\buid=0\(root\)', root['stdout'])
    rows = [
        ('Root command execution', 'VERIFIED' if root_ok else 'NOT CONFIRMED',
         'Fresh tv-access invocation; identity and kernel capability evidence recorded.'),
        ('Interactive PTY shell', 'NOT TESTED BY THIS RUN',
         'The existing manual PTY result must be reported separately.'),
        ('UEP / unsigned native execution', 'IN TEST — UNVERIFIED',
         'Existing log evidence collected; no unsigned payload executed and no kernel state changed.'),
        ('Source list / current source / HDMI selection', 'IN TEST — UNVERIFIED',
         'Current-source keys read; list API and input transitions not exercised.'),
        ('HDMI presentation recovery', 'IN TEST — UNVERIFIED',
         'Not triggered: restarting the presentation app needs a controlled functional test.'),
        ('Local-dimming control', 'NOT APPLICABLE' if model.upper() == 'S90C' else 'UNVERIFIED',
         'S90C is OLED; upstream Smart LED backlight control is not an OLED dimming test.'),
        ('PC / Game Mode / Input Signal Plus', 'IN TEST — UNVERIFIED',
         'AVOC interface and picture/HDR readbacks collected; no policy setters invoked.'),
        ('Picture Off / display state / wake', 'IN TEST — UNVERIFIED',
         'libdeviced prerequisite checked; native getters and visible transitions need a helper/test.'),
        ('Remote observation / filtering / actions', 'IN TEST — UNVERIFIED',
         'Device inventory and nonexclusive open access checked; no input consumed, grabbed, or injected.'),
    ]
    values = {k: pair(results[k]) for k in ('volume', 'mute', 'speaker_support')}
    valid = (values['volume'] is not None and 0 <= values['volume'] <= 100
             and values['mute'] in (0, 1) and values['speaker_support'] is not None)
    rows.append(('Speaker state getters', 'VERIFIED' if valid else 'NOT CONFIRMED',
                 f'Validated upstream ii value/result replies: {values}'))
    rows.append(('Speaker volume set / change events', 'IN TEST — UNVERIFIED',
                 'No volume or mute changes made; signal observation is separate evidence.'))
    signal_text = results['native_events']['stdout']
    seen = [name for name in ('org.tizen.tv.appfw.appctxmgr', 'org.tizen.aul.AppStatus',
                             'org.tizen.speakermanager') if f'interface={name};' in signal_text]
    rows.extend([
        ('Foreground app / source / lifecycle / HDMI events', 'IN TEST — UNVERIFIED',
         'Bounded D-Bus sample; matching interfaces seen: ' + (', '.join(seen) or 'none')
         + '. Individual transitions and HDMI receiver monitoring not verified.'),
        ('Processed 960x540 HDMI capture', 'IN TEST — UNVERIFIED',
         'Analysis process prerequisites only; no frame extracted or freshness/geometry tested.'),
        ('Text and graphics overlays', 'IN TEST — UNVERIFIED',
         'EFL library prerequisites only; no overlay displayed.'),
    ])
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tv', default=os.environ.get('TV_HOST'), help='TV IP/hostname (or TV_HOST)')
    ap.add_argument('--repo', type=Path, default=Path.cwd(), help='samsung-tv-tools checkout')
    ap.add_argument('--nix', action='store_true', help='Use Nix with nix-command/flakes enabled')
    ap.add_argument('--model', default='S90C', help='Owner-reported model; not hardware-detected')
    ap.add_argument('--output', type=Path, help='New private report directory; must not already exist')
    args = ap.parse_args()
    if not args.tv:
        ap.error('--tv or TV_HOST is required')
    repo = args.repo.expanduser().resolve()
    if not (repo / 'tools/tv_access/tv-access').is_file():
        ap.error('--repo must point to a samsung-tv-tools checkout')
    if args.nix and not shutil.which('nix'):
        ap.error('nix was not found')
    os.umask(0o077)
    now = dt.datetime.now(dt.timezone.utc)
    out = (args.output or Path.home() / 's90c-research' /
           now.strftime('verify-%Y%m%dT%H%M%S%fZ')).expanduser().resolve()
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    deadline = 20
    if args.nix:
        prefix = ['nix', '--extra-experimental-features', 'nix-command flakes',
                  'run', '--no-write-lock-file', '.#tv-access', '--']
    else:
        prefix = [str(repo / 'tools/tv_access/tv-access')]
    prefix += ['--tv', args.tv, '--timeout', str(deadline)]
    env = dict(os.environ, TV_HOST=args.tv)
    commit = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'],
                            capture_output=True, text=True).stdout.strip()
    metadata = {'version': 1, 'created_utc': now.isoformat(), 'owner_reported_model': args.model,
                'tv_host_private': args.tv, 'tools_commit': commit,
                'reference_commit': REFERENCE, 'reference_files': SOURCE_FILES,
                'scope': 'Read-only unattended checks; capability rows are not all functional tests.'}
    results = {}
    interrupted = False
    try:
        for number, (key, label, command) in enumerate(PROBES, 1):
            print(f'[{number}/{len(PROBES)}] {label}', flush=True)
            result = execute(prefix, command, repo, env, deadline)
            result.update({'label': label, 'command': command})
            results[key] = result
            (out / f'{number:02d}-{key}.json').write_text(json.dumps(result, indent=2) + '\n')
            (out / f'{number:02d}-{key}.txt').write_text(
                result['stdout'] + '\n--- STDERR ---\n' + result['stderr'])
            if key == 'identity' and not (result['returncode'] == 0 and
                    re.search(r'\buid=0\(root\)', result['stdout'])):
                print('Root identity not confirmed. Stopping; evidence saved.', file=sys.stderr)
                break
    except KeyboardInterrupt:
        interrupted = True
        print('\nInterrupted. Partial evidence retained. No commands retried.', file=sys.stderr)
    complete = len(results) == len(PROBES)
    report = {'metadata': metadata, 'complete': complete, 'interrupted': interrupted, 'probes': results}
    (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    lines = ['# S90C capability verification', '', f'Collected: {now.isoformat()}', '',
             f'Owner-reported model: {args.model}', f'Tools checkout commit: `{commit}`', '',
             f'Complete collection: {complete}', '',
             'This report distinguishes a successful readback from interface presence. '
             'Unattended prerequisite checks do not verify switching, recovery, events, '
             'visual output, or security-policy changes.', '',
             '## Capability results', '', '| Capability | Result | Evidence / limitation |',
             '|---|---|---|']
    if complete:
        for name, status, reason in summarize(results, args.model):
            lines.append('| ' + ' | '.join(v.replace('|', '\\|').replace('\n', ' ')
                                          for v in (name, status, reason)) + ' |')
    else:
        lines.append('| Collection | INCOMPLETE | Inspect identity/error evidence before rerunning. |')
    lines += ['', '## Raw probe status', '', '| Probe | Exit status | Host timeout |', '|---|---|---|']
    for key, value in results.items():
        lines.append(f'| {key} | {value["returncode"]} | {value["host_timeout"]} |')
    lines += ['', '## Source reference', '',
              f'Upstream reference: {UPSTREAM}/tree/{REFERENCE}', '',
              '## Sharing', '',
              'Review the raw evidence before posting. Source JSON, process arguments, '
              'device names, paths and logs can contain private identifiers. '
              'The private results.json also records the target host. '
              'This summary omits that host but is not a guarantee of anonymization.', '']
    (out / 'summary.md').write_text('\n'.join(lines))
    print(f'\nReport: {out / "summary.md"}\nRaw evidence: {out / "results.json"}')
    return 0 if complete else 1


if __name__ == '__main__':
    sys.exit(main())
