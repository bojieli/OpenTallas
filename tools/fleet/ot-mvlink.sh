#!/bin/bash
# ot-mvlink.sh SRC DST  (FLEET-DISK 2026-10-24): move an idle directory SRC (on the root fs) to DST (scratch disk) and
# leave a symlink SRC -> DST.  Never touches a busy directory: no running container may bind-mount it (docker inspect)
# and `lsof +D` must show no process, both before the bulk copy AND right before the switch.  The switch is mv SRC SRC.ot-moving.PID + ln -s (microseconds); a catch-up rsync --update
# then copies anything written between the bulk copy and the switch, and only then is the old copy removed.
# DST may already exist (merge): files that exist on both sides with different content abort the move (nothing removed).
# Exit: 0 moved, 2 busy, 3 conflict, 1 error.  Prints one line: MOVED / BUSY / CONFLICT / SKIP.
set -u
src=${1%/}; dst=${2%/}
[ -L "$src" ] && { echo "SKIP $src (already a symlink -> $(readlink "$src"))"; exit 0; }
[ -d "$src" ] || { echo "SKIP $src (not a directory)"; exit 0; }
SUDO=; [ -w "$(dirname "$src")" ] || SUDO=sudo
# busy = a process holds a file / cwd under SRC (lsof +D), OR a running container bind-mounts SRC, a path inside it or a
# parent of it.  lsof +D does NOT see docker bind mounts: container processes report container-side paths (/work), so
# a mover that trusts lsof alone deletes a live container's work dir (FLEET-DISK 2026-10-24 lesson).
docker_busy() {
    command -v docker >/dev/null || return 1
    local rs m rm c hit=
    rs=$(readlink -f "$src")
    for c in $(sudo docker ps -q 2>/dev/null); do
        for m in $(sudo docker inspect -f '{{range .Mounts}}{{.Source}} {{end}}' "$c" 2>/dev/null); do
            rm=$(readlink -f "$m" 2>/dev/null || echo "$m")
            case "$rm/" in "$rs"/*) hit="$hit $c";; esac
            case "$rs/" in "$rm"/*) hit="$hit $c";; esac
            case "$m/" in "$src"/*) hit="$hit $c";; esac
        done
    done
    [ -n "$hit" ] && { echo "BUSY $src (docker bind mount: containers$(echo $hit | tr ' ' '\n' | sort -u | tr '\n' ' ' | sed 's/^/ /'))"; return 0; }
    return 1
}
busy() { local n; docker_busy && return 0; n=$(sudo lsof +D "$src" 2>/dev/null | awk 'NR>1{print $2}' | sort -u | tr '\n' ' '); [ -n "$n" ] && { echo "BUSY $src (pids $n)"; return 0; }; return 1; }
busy && exit 2
mkdir -p "$dst" || exit 1
if [ -n "$(ls -A "$dst" 2>/dev/null)" ]; then           # merge: refuse when a file differs on both sides
    c=$(rsync -a --dry-run --itemize-changes --existing --checksum "$src/" "$dst/" | grep -v '^\.d' | grep -v '^cd' | head -5)
    [ -n "$c" ] && { echo "CONFLICT $src -> $dst: $(echo $c | head -c 300)"; exit 3; }
fi
rsync -a --update "$src/" "$dst/" || { echo "ERROR rsync $src"; exit 1; }
busy && exit 2
tmp="$src.ot-moving.$$"
$SUDO mv "$src" "$tmp" && $SUDO ln -s "$dst" "$src" && $SUDO chown -h "$(id -un):$(id -gn)" "$src" || { echo "ERROR switch $src"; exit 1; }
rsync -a --update "$tmp/" "$dst/" || { echo "ERROR catch-up rsync $tmp (old copy kept)"; exit 1; }
$SUDO rm -rf "$tmp"
echo "MOVED $src -> $dst"
