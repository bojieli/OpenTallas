#!/usr/bin/env bash
# KV-P8-HUB 10-23: plan v3.8h -> v3.8s = + post_v38s.py (FIRM astk internal stations on hub_Eo/Wo, R3-INTERNAL, KV owner
# option (i) 23:24; lane fixed_cycles += stations) + gen.py latency (R8 with the bound bus groups).  Touches only
# partition_types.{kv3_hub_Eo,kv3_hub_Wo}.internal_stations and the 18 astk lanes; chains after any hg/hgi/pc/pv post step.
#   usage: run_v38s.sh V38H_DIE_PLAN.json OUTDIR [BUS_GROUPS.json]
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd)
IN=${1:?v3.8h die_plan.json}; O=${2:?output directory}; BG=${3:-}; mkdir -p "$O"
python3 "$D/post_v38s.py" "$IN" "$D" --table > "$O/die_plan.json" 2> "$O/stations_v38s.tsv"
python3 "$R/tools/die_plan/gen.py" latency "$O/die_plan.json" --inplace --out "$O/lat" ${BG:+--groups "$BG"}
cp -r "$D/cores" "$D/census" "$D/core_conns.json" "$D/cells_evidence.json" "$D"/l1_cores_v3*.json "$O/"
python3 "$R/tools/die_plan/check.py" "$O/die_plan.json" --out "$O/g0s"
python3 "$R/tools/die_plan/check.py" "$O/die_plan.json" --completeness --out "$O/g0cs" || true
