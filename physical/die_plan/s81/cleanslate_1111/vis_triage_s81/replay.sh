#!/bin/bash
# replay.sh BASE_PLAN.json OUT_DIR : rebuild the COL-H9R0/R2 output plan on a base from this directory's seed_delta.json
# (core_place.py from this branch; core_conns.json here must sit beside the plan as core_conns.json).
set -e
H=$(cd "$(dirname "$0")" && pwd); R=$(cd "$H/../../../../.." && pwd); O=$2; mkdir -p "$O"
cp "$1" "$O/base_plan.json"; cp "$H/core_conns.json" "$O/core_conns.json"
T=$(python3 -I -c "import json,sys;print(','.join(sorted(json.load(open(sys.argv[1])))))" "$H/seed_delta.json")
OMP_NUM_THREADS=1 python3 -I "$R/tools/die_plan/core_place.py" "$O/base_plan.json" --die s81 --types "$T" \
  --seed "$H/seed_delta.json" --no-search --out-plan "$O/plan.json" --event "$O/event.json" --svg "$O/svg" > "$O/log.txt" 2>&1
sha256sum "$O/plan.json"
