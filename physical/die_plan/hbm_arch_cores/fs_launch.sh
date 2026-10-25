#!/bin/bash
# HBM-FACE: run one shelled kit on a fleet host through ot-run (inputs synced first: ot-run syncs nothing).
#   fs_launch.sh KITDIR MODE [MEM_GB=16] [THREADS=8]      MODE = synth (run_kit_hbm.sh synth -> face_guard) | bench
set -uo pipefail
KD=$(cd "$1" && pwd -P); MODE=$2; MEM=${3:-16}; THR=${4:-8}
HERE=$(cd "$(dirname "$0")" && pwd -P); REPO=$(cd "$HERE/../../.." && pwd -P)
ROOT=/srv/opentallas-scratch2/claude/hbm-face/runs_$MODE
# unique run dir per launch: ot-run --dir qualifies EVERY host holding the dir, so a reused name could run a stale copy
N=$(basename "$KD").$(date +%Y%m%d%H%M%S).$$
mkdir -p "$KD/fs_tools" "$KD/macros"
cp "$HERE/face_shell.py" "$HERE/face_shell_bench.py" "$KD/fs_tools/"
for m in $(python3 -c "import json;print(' '.join(json.load(open('$KD/freeze.json')).get('macros',[])))"); do
  f=$(ls "$REPO"/physical/asap7_memory_macros*/"$m"/"$m".v 2>/dev/null | head -1); [ -n "$f" ] && cp "$f" "$KD/macros/"
done
H=$(~/.local/bin/ot-run --mem "$MEM" --threads "$THR" --dir "$ROOT" --pick 2>/dev/null | tail -1)
# FS_AVOID=host: re-pick when ot-run picks a host whose admission is broken (epyc1 user bus lost 10-25 01:37)
if [ -n "${FS_AVOID:-}" ] && [ "$H" = "$FS_AVOID" ]; then
  H=$(~/.local/bin/ot-run --mem "$MEM" --threads "$THR" --dir "$ROOT" --pick 2>&1 | grep -o "^ot-run: [a-z0-9]* *admits" | awk '{print $2}' | grep -vx "$FS_AVOID" | head -1)
fi
[ -z "$H" ] && { echo "NOT RUN $N: no host admits $MEM GB"; exit 2; }
if [ "$H" = localhost ]; then rsync -a --delete "$KD/" "$ROOT/$N/"
else rsync -a --delete "$KD/" "$H:$ROOT/$N/"; fi
echo "$(date '+%F %T') $N $MODE -> $H:$ROOT/$N mem $MEM thr $THR" >> /srv/opentallas-scratch2/claude/hbm-face/launch.log
if [ "$MODE" = synth ]; then
  exec ~/.local/bin/ot-run --mem "$MEM" --threads "$THR" --dir "$ROOT/$N" -- bash "$ROOT/$N/run_kit_hbm.sh" "$ROOT/$N" synth "$MEM" "$THR"
else
  exec ~/.local/bin/ot-run --mem "$MEM" --threads "$THR" --dir "$ROOT/$N" -- python3 "$ROOT/$N/fs_tools/face_shell_bench.py" "$ROOT/$N" --jobs "$THR"
fi
