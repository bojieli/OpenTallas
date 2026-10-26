#!/usr/bin/env bash
# Emit plan v3.6 (= v3.5 + kv3_hg_v1 split by row, post_v36.py), its latency table, the R8 landing table and G0.
# BUS_GROUPS = BINDER2's KV bind bus_groups.json (kv35).  Tools: claude/plan-tool3-1023 r8.py with the bus_sub key (OT_DIE_PLAN_TOOLS).
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
R=$(cd "$D/../../.." && pwd)
O=${1:?output directory required}; BG=${2:?BINDER2 bus_groups.json required}
mkdir -p "$O"; O=$(cd "$O" && pwd)
T=${OT_DIE_PLAN_TOOLS:-$R/tools/die_plan}
bash "$D/run_v35.sh" "$O/v35"
python3 "$D/post_v36.py" "$O/v35/die_plan.json" > "$O/die_plan.json"
python3 "$T/gen.py" latency "$O/die_plan.json" --inplace --out "$O/lat"
mkdir -p "$O/census" "$O/r8" && cp "$O/v35/census/"* "$O/census/"
python3 "$D/r8/r8_fault_exempt.py" "$BG" "$O/r8/bg_fx.json"
python3 "$D/r8/r8_invariant_split.py" "$O/die_plan.json" "$O/r8/bg_fx.json" "$O/r8/bus_groups.json" && rm "$O/r8/bg_fx.json"
python3 "$T/r8.py" pads "$O/die_plan.json" "$O/r8/bus_groups.json" --out "$O/r8" --bus leaf --replica type
python3 "$T/check.py" "$O/die_plan.json" --png --out "$O/g0"
