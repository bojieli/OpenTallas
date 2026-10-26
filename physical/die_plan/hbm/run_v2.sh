#!/usr/bin/env bash
# Build the selected quadrant plan from pinned inputs with a fixed hash seed.
# This is a plan-stage model; source binding and G2/G3 conditions remain open.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
R=$(cd "$D/../../.." && pwd)
O=${1:?output directory required}
mkdir -p "$O"
O=$(cd "$O" && pwd)
PYTHONHASHSEED=0 python3 "$D/gen_plan_v2.py" --out "$O"
python3 "$R/tools/die_plan/check.py" "$O/die_plan.json" --png --out "$O/g0"
python3 "$D/complete_p7.py" "$O" --tool "${OT_PT4:-$R}"   # P7 G0C completeness (needs plan-tool4 tools/die_plan: check._bus_targets)
