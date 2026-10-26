#!/usr/bin/env bash
# Emit the chosen v3.2 plan from its pinned stage1 model and as-built/strap inputs.
# F_DLY=3 remains the qualified schedule; model F_DLY=2 is not adopted.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
R=$(cd "$D/../../.." && pwd)
O=${1:?output directory required}
mkdir -p "$O"
O=$(cd "$O" && pwd)
python3 "$D/emit_v32.py" --stage1 "$D/stage1_v32.json.gz" --asbuilt "$D/asbuilt_rtl6_e33504a6f.json.gz" --out "$O/raw.json" --report "$O/plan_report_v32.json"
python3 "$D/post_v32.py" "$O/raw.json" "$D/stage1_v32.json.gz" "$D/bind/v32_inputs.json.gz" > "$O/die_plan.json"
python3 "$R/tools/die_plan/gen.py" latency "$O/die_plan.json" --inplace --out "$O/lat"
(cd "$O" && python3 "$D/census_rows_v32.py" "$D/stage1_v32.json.gz" "$D/asbuilt_rtl6_e33504a6f.json.gz")
python3 "$D/clocks_v32.py" "$O/die_plan.json" > "$O/clocks_v32.json"
python3 "$R/tools/die_plan/check.py" "$O/die_plan.json" --png --out "$O/g0"
