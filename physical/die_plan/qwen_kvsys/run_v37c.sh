#!/usr/bin/env bash
# Emit plan v3.7-cores (= v3.6 + partition_types.*.hard_cores[], post_v37c.py) and G0.  Lanes / ports unchanged -> the
# v3.6 latency + R8 tables stand.  usage: run_v37c.sh V36_DIE_PLAN.json OUTDIR
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd)
IN=${1:?v3.6 die_plan.json}; O=${2:?output directory}; mkdir -p "$O"
python3 "$D/post_v37c.py" "$IN" > "$O/die_plan.json"
cp -r "$D/cores" "$D/census" "$O/"   # pins_file / census paths are plan-relative
python3 "${OT_DIE_PLAN_TOOLS:-$R/tools/die_plan}/check.py" "$O/die_plan.json" --png --out "$O/g0"
