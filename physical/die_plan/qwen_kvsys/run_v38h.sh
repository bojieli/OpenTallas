#!/usr/bin/env bash
# KV-P7-HUB 10-23: plan v3.7p -> v3.8h = + post_v38t.py (R4 tap grid 400 um on the 4 hubs, COORD 21:26) + post_v38h.py
# (astk hard cores + top-down pins on hub_Eo/Wo).  Composes after post_v37p (run_v37c.sh); other types untouched.
#   usage: run_v38h.sh V37P_DIE_PLAN.json OUTDIR [RTL_DIR]   (RTL_DIR = bound partition netlists, binder3 kv39 rtl/:
#   regenerates cores/kv3_astk_*_pins.json + the hub_Eo/Wo entries of core_conns.json in this plan dir)
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd)
IN=${1:?v3.7p die_plan.json}; O=${2:?output directory}; RTL=${3:-}; mkdir -p "$O"
python3 "$D/post_v38t.py" "$IN" > "$O/die_plan_t.json"
python3 "$D/post_v38h.py" "$O/die_plan_t.json" "$D" ${RTL:+--gen "$RTL"} > "$O/die_plan.json"; rm "$O/die_plan_t.json"
cp -r "$D/cores" "$D/census" "$D/core_conns.json" "$D/cells_evidence.json" "$D"/l1_cores_v3*.json "$O/"
python3 "${OT_DIE_PLAN_TOOLS:-$R/tools/die_plan}/check.py" "$O/die_plan.json" --png --out "$O/g0h"
python3 "${OT_DIE_PLAN_TOOLS:-$R/tools/die_plan}/check.py" "$O/die_plan.json" --completeness --out "$O/g0ch" || true
