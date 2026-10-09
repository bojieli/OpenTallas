#!/bin/bash
# Routine terminal harvest only. Never kills/restarts or changes the ECO worker.
set -euo pipefail
TASK=$1
RUNNER=$2
OUT="$TASK/evidence/terminal_a1"
mkdir "$OUT" # Refuse overwriting any earlier terminal/failure evidence.
while [ -r "/proc/$RUNNER/cmdline" ] && tr '\0' ' ' < "/proc/$RUNNER/cmdline" | grep -q 'hold_eco_run.sh'; do
  sleep 45
done
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$OUT/observed_worker_exit_utc.txt"
ECO="$TASK/b4_hold_eco_a1"
for name in result.json corner_sta.json eco.log; do
  [ ! -f "$ECO/$name" ] || cp "$ECO/$name" "$OUT/$name"
done
if [ ! -f "$ECO/result.json" ]; then
  printf '%s\n' 'ECO worker exited without terminal result.json; no qualification.' > "$OUT/collection_failure.txt"
  exit 9
fi
ODB=$(find -L "$ECO/orfs/results" -name 6_final.odb -print -quit)
[ -n "$ODB" ] || { printf '%s\n' 'No selected final ODB; audit unavailable.' > "$OUT/collection_failure.txt"; exit 10; }
sha256sum "$ODB" > "$OUT/final_odb.sha256"
# Evidenced conservative sibling reservation: same-source STA16.16GiB/route16.28GiB.
# No per-process limit. OpenDB audit reads only, with no routing or ODB write.
/srv/opentallas-scratch/admit.sh 17 -- docker run --rm \
  -v "$TASK:/task:ro" -v "$OUT:/out" \
  openroad/orfs:asap7lock bash -lc \
  '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /task/src/tools/dsrom_markov_b4_layer_audit.py -- --odb "$1" --out /out/used_layers.json' \
  bash "/task/${ODB#"$TASK/"}" > "$OUT/layer_audit.log" 2>&1
python3 - "$OUT" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); r=json.loads((p/'result.json').read_text()); a=json.loads((p/'used_layers.json').read_text())
ok=r.get('tt_ps') is not None and r.get('ff_ps') is not None and r['tt_ps']>=0 and r['ff_ps']>=0 and r.get('drc')==0 and not r.get('errors') and a['same_M2_M6_upper_layer_qualification']
(p/'qualification.json').write_text(json.dumps(dict(source_rtl='38f22c6d8',audit_source='51b846604',review='confirmed review-0342 P2',tt_ps=r.get('tt_ps'),ff_ps=r.get('ff_ps'),drc=r.get('drc'),same_M2_M6_upper_layer_qualification=a['same_M2_M6_upper_layer_qualification'],routine_conditions_pass=ok,scope='TT pathfinding only; exact/mutant binding unchanged; no adoption/deployment performed.'),indent=1)+'\n')
PY
