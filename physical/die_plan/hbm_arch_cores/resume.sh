#!/bin/bash
# ELEM-HBM: continue a kit already placed by launch.sh on its host (same run dir; never --delete: run/ holds the
# placement).  Kit files (config.mk, hooks) are refreshed from KITDIR first.   resume.sh KITDIR [MEM] [THR] [GOAL=finish]
set -uo pipefail
KD=$(cd "$1" && pwd -P); MEM=${2:-32}; THR=${3:-8}; GOAL=${4:-finish}
ROOT=/srv/opentallas-scratch/claude/elem-hbm/runs; N=$(basename "$KD")
H=$(grep " $N -> " /srv/opentallas-scratch/claude/elem-hbm/launch.log | tail -1 | awk '{print $5}' | cut -d: -f1)
[ -z "$H" ] && { echo "NOT RUN $N: never launched"; exit 2; }
if [ "$H" = localhost ]; then rsync -a --exclude run/ --exclude 'run_*.log' "$KD/" "$ROOT/$N/"
else rsync -a --exclude run/ --exclude 'run_*.log' "$KD/" "$H:$ROOT/$N/"; fi
echo "$(date '+%F %T') $N resume $GOAL on $H mem $MEM thr $THR" >> /srv/opentallas-scratch/claude/elem-hbm/launch.log
exec ot-run --mem "$MEM" --threads "$THR" --hosts "$H" --dir "$ROOT/$N" -- bash "$ROOT/$N/run_kit_hbm.sh" "$ROOT/$N" "$GOAL" "$MEM" "$THR"
