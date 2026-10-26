#!/usr/bin/env bash
# Emit plan v3.3 (= v3.2 + host TX FDI split-bus trunk fix, plan_v33.py) from its pinned stage1 model and as-built/strap inputs.
# F_DLY=3 remains the qualified schedule; model F_DLY=2 is not adopted.
set -euo pipefail
# stage1: python3 plan_v33.py --asbuilt asbuilt_rtl6_e33504a6f.json.gz --out stage1_v33.json.gz (deterministic; plan_v32.py reproduces stage1_v32 byte-identically)
D=$(cd "$(dirname "$0")" && pwd)
R=$(cd "$D/../../.." && pwd)
O=${1:?output directory required}
mkdir -p "$O"
O=$(cd "$O" && pwd)
python3 "$D/emit_v33.py" --stage1 "$D/stage1_v33.json.gz" --asbuilt "$D/asbuilt_rtl6_e33504a6f.json.gz" --out "$O/raw.json" --report "$O/plan_report_v33.json"
python3 "$D/post_v32.py" "$O/raw.json" "$D/stage1_v33.json.gz" "$D/bind/v32_inputs.json.gz" > "$O/die_plan.json"
python3 "$R/tools/die_plan/gen.py" latency "$O/die_plan.json" --inplace --out "$O/lat"
(cd "$O" && python3 "$D/census_rows_v32.py" "$D/stage1_v33.json.gz" "$D/asbuilt_rtl6_e33504a6f.json.gz")
python3 "$D/clocks_v32.py" "$O/die_plan.json" > "$O/clocks_v32.json"
python3 "$R/tools/die_plan/check.py" "$O/die_plan.json" --png --out "$O/g0"
