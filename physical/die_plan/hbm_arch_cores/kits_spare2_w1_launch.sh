#!/bin/bash
# KITS-SPARE-2/W1: launch.sh clone, ROOT on scratch2; ot-run --pick (no --hosts), kit synced to the picked host.
set -uo pipefail
KD=$(cd "$1" && pwd -P); MEM=${2:-32}; THR=${3:-16}; GOAL=${4:-cts}
ROOT=/srv/opentallas-scratch2/claude/kits-spare2/w1/runs
N=$(basename "$KD")
H=$(~/.local/bin/ot-run --mem "$MEM" --threads "$THR" --dir /srv/opentallas-scratch2 --pick 2>/dev/null | tail -n 1)
[ -z "$H" ] && { echo "NOT RUN $N"; exit 2; }
if [ "$H" = localhost ]; then mkdir -p "$ROOT"; rsync -a --delete "$KD/" "$ROOT/$N/"
else ssh -o ControlPath=none "$H" "mkdir -p $ROOT" && rsync -a --delete -e "ssh -o ControlPath=none" "$KD/" "$H:$ROOT/$N/"; fi
echo "$(date "+%F %T") $N -> $H:$ROOT/$N mem $MEM thr $THR goal $GOAL" >> /srv/opentallas-scratch2/claude/kits-spare2/w1/launch.log
exec ~/.local/bin/ot-run --mem "$MEM" --threads "$THR" --dir "$ROOT/$N" -- bash "$ROOT/$N/run_kit_hbm.sh" "$ROOT/$N" "$GOAL" "$MEM" "$THR"
