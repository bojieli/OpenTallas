#!/bin/bash
# ot-scratch-consolidate.sh [--loop SEC] (FLEET-DISK 2026-10-24, owner: never use root disks for work)
# On a host whose /srv/opentallas-scratch2 is a separate disk and /srv/opentallas-scratch sits on the root fs
# (intel1/intel2/epyc2): move every idle entry of /srv/opentallas-scratch (claude/* and the top-level lane dirs) to the
# same path under /srv/opentallas-scratch2 with ot-mvlink (symlink left behind; busy dirs are skipped and retried),
# and once claude/ holds only symlinks, replace /srv/opentallas-scratch/claude itself by a symlink to
# /srv/opentallas-scratch2/claude.  Never kills or pauses anything.  With --loop SEC it retries until done (max 72 h).
set -u
S1=/srv/opentallas-scratch S2=/srv/opentallas-scratch2
MV=${OT_MVLINK:-$(dirname "$(readlink -f "$0")")/ot-mvlink.sh}
[ -x "$MV" ] || MV=$HOME/.local/bin/ot-mvlink
log() { echo "$(date '+%F %T') $*"; }
pass() {
    [ "$(stat -L -c %d $S2/claude 2>/dev/null)" != "$(stat -c %d /)" ] && [ -d $S2/claude ] || { log "no separate scratch disk; nothing to do"; return 0; }
    left=0
    if [ -d $S1/claude ] && [ ! -L $S1/claude ]; then
        for e in $S1/claude/* $S1/claude/.[!.]*; do
            [ -e "$e" ] || [ -L "$e" ] || continue
            [ -L "$e" ] && continue
            r=$("$MV" "$e" "$S2/claude/${e##*/}"); log "$r"; case "$r" in MOVED*|SKIP*) ;; *) left=$((left+1));; esac
        done
        if [ $left = 0 ]; then                       # only symlinks left: flip claude/ itself
            for l in $S1/claude/* $S1/claude/.[!.]*; do
                [ -L "$l" ] || continue
                n=$S2/claude/${l##*/}
                [ "$(readlink "$l")" = "$n" ] && continue
                [ -e "$n" ] || [ -L "$n" ] || cp -P "$l" "$n"
            done
            old=$S1/claude.ot-flip.$$
            mv $S1/claude "$old" && ln -s $S2/claude $S1/claude && log "FLIPPED $S1/claude -> $S2/claude"
            for e in "$old"/* "$old"/.[!.]*; do          # anything created during the flip window
                [ -e "$e" ] || [ -L "$e" ] || continue
                if [ -L "$e" ]; then rm -f "$e"; else r=$("$MV" "$e" "$S2/claude/${e##*/}"); log "late: $r"; [ -L "$e" ] && rm -f "$e"; fi
            done
            rmdir "$old" 2>/dev/null || { log "WARN $old not empty"; left=1; }
        fi
    fi
    for e in $S1/*; do
        [ "${e##*/}" = claude ] && continue
        case "$e" in *.ot-moving.*|*.ot-flip.*) continue;; esac
        [ -d "$e" ] && [ ! -L "$e" ] || continue
        r=$("$MV" "$e" "$S2/${e##*/}"); log "$r"; case "$r" in MOVED*|SKIP*) ;; *) left=$((left+1));; esac
    done
    log "pass done: $left busy/unmoved; root fs $(df --output=pcent / | tail -1 | tr -d ' ')"
    return $left
}
if [ "${1:-}" = --loop ]; then
    end=$(( $(date +%s) + 72*3600 ))
    until pass; do [ $(date +%s) -gt $end ] && { log "GAVE UP after 72 h"; exit 1; }; sleep "${2:-600}"; done
    log "ALL DONE"
else
    pass
fi
