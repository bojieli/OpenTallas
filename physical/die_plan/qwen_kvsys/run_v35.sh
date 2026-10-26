#!/usr/bin/env bash
# Emit plan v3.5 (= v3.4 + R8 source-side replica groups, post_v35.py) and its latency table + G0.
# v3.4 is reproduced by run_v34.sh; G0/latency need the R8 tool (claude/plan-tool3-1023 cc5ebe697+): OT_DIE_PLAN_TOOLS.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
R=$(cd "$D/../../.." && pwd)
O=${1:?output directory required}
mkdir -p "$O"; O=$(cd "$O" && pwd)
T=${OT_DIE_PLAN_TOOLS:-$R/tools/die_plan}
bash "$D/run_v34.sh" "$O/v34"
python3 "$D/post_v35.py" "$O/v34/die_plan.json" > "$O/die_plan.json"
python3 "$T/gen.py" latency "$O/die_plan.json" --inplace --out "$O/lat"
mkdir -p "$O/census" && cp "$O/v34/census/"* "$O/census/"
python3 "$T/check.py" "$O/die_plan.json" --png --out "$O/g0"
