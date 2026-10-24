#!/usr/bin/env bash
# Emit plan v3.4 (= v3.3 + R3 ft stations <= 750 um, emit_v34.py; R5 bitcon census, post_v34.py) from its pinned stage1 model and as-built/strap inputs.
# F_DLY=3 remains the qualified schedule; model F_DLY=2 is not adopted.
set -euo pipefail
# stage1: python3 plan_v33.py --asbuilt asbuilt_rtl6_e33504a6f.json.gz --out stage1_v33.json.gz (deterministic; plan_v32.py reproduces stage1_v32 byte-identically)
D=$(cd "$(dirname "$0")" && pwd)
R=$(cd "$D/../../.." && pwd)
O=${1:?output directory required}
mkdir -p "$O"
O=$(cd "$O" && pwd)
python3 "$D/emit_v34.py" --stage1 "$D/stage1_v33.json.gz" --asbuilt "$D/asbuilt_rtl6_e33504a6f.json.gz" --out "$O/raw.json" --report "$O/plan_report_v34.json"
python3 "$D/post_v32.py" "$O/raw.json" "$D/stage1_v33.json.gz" "$D/bind/v32_inputs.json.gz" > "$O/die_plan.json"
python3 "$D/post_v34.py" "$O/die_plan.json" "$D/census/census_map_v32.json" "$O/census_map_v34.json"
python3 "$R/tools/die_plan/gen.py" latency "$O/die_plan.json" --inplace --out "$O/lat"
(cd "$O" && python3 "$D/census_rows_v32.py" "$D/stage1_v33.json.gz" "$D/asbuilt_rtl6_e33504a6f.json.gz")
python3 "$D/clocks_v32.py" "$O/die_plan.json" > "$O/clocks_v32.json"
# G0 needs the R3/R5 tool (claude/plan-tool-1023 3087b9331+): OT_DIE_PLAN_TOOLS overrides the tool root
T=${OT_DIE_PLAN_TOOLS:-$R/tools/die_plan}
mkdir -p "$O/census" && cp "$D/census/census_rows_v32.tsv.gz" "$D/census/bitcon_rtl6.json.gz" "$O/census/" && cp "$O/census_map_v34.json" "$O/census/"
python3 "$T/check.py" "$O/die_plan.json" --png --out "$O/g0"
