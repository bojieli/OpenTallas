#!/bin/bash
# ELEM-HBM: place one generated core kit on a fleet host and run it there through ot-run (inputs synced first:
# ot-run syncs nothing).  Results stay on the host under the same path; collect.py pulls the small artefacts back.
#   launch.sh KITDIR [MEM_GB=32] [THREADS=16] [GOAL=finish]
# HBM-ELEM 10-24: no --hosts (lane rule): ot-run --pick chooses among ALL fleet hosts, the kit is synced there, and the
# run is placed with --dir only (data locality: only the host holding the kit dir qualifies).
set -uo pipefail
KD=$(cd "$1" && pwd -P); MEM=${2:-32}; THR=${3:-16}; GOAL=${4:-finish}
ROOT=/srv/opentallas-scratch/claude/elem-hbm/runs
N=$(basename "$KD")
H=$(ot-run --mem "$MEM" --threads "$THR" --dir "$ROOT" --pick 2>/dev/null | tail -1)
[ -z "$H" ] && { echo "NOT RUN $N: no host admits $MEM GB"; exit 2; }
if [ "$H" = localhost ]; then mkdir -p "$ROOT"; rsync -a --delete "$KD/" "$ROOT/$N/"
else ssh "$H" "mkdir -p $ROOT" && rsync -a --delete "$KD/" "$H:$ROOT/$N/"; fi
echo "$(date '+%F %T') $N -> $H:$ROOT/$N mem $MEM thr $THR" >> /srv/opentallas-scratch/claude/elem-hbm/launch.log
exec ot-run --mem "$MEM" --threads "$THR" --dir "$ROOT/$N" -- bash "$ROOT/$N/run_kit_hbm.sh" "$ROOT/$N" "$GOAL" "$MEM" "$THR"
