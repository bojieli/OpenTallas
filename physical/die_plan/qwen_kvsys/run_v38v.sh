#!/usr/bin/env bash
# KV-G3 10-24: plan v3.8u -> v3.8v = post_v38v.py (hub_Ei fault-OR plan cells FIRM + internal stations on the
# i_dcal_flt / i_hp_fault_N_q legs, L357 +3 / L758 +2) + gen.py latency, then G0 / G0C.
# The plan R8 table is r8/ (r8.py --bus leaf --replica type on r8/bus_groups.json, unchanged: L357/L758 are fault lanes);
# lat/ is the latency package only, so G0 names the r8/ table explicitly.
#   usage: run_v38v.sh V38U_DIE_PLAN.json OUTDIR
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd)
IN=${1:?v3.8u die_plan.json}; O=${2:?output directory}; mkdir -p "$O"
python3 "$D/post_v38v.py" "$IN" > "$O/die_plan.json"
python3 "$R/tools/die_plan/gen.py" latency "$O/die_plan.json" --inplace --out "$O/lat" --groups "$D/r8/bus_groups.json"
cp -r "$D/cores" "$D/census" "$D/r8" "$D/core_conns.json" "$D/cells_evidence.json" "$D/die_io.json" "$D"/l1_cores_v3*.json "$O/"
python3 "$R/tools/die_plan/check.py" "$O/die_plan.json" --landing "$O/r8/qwen_kvsys_r8_landing.json" --out "$O/g0v"
python3 "$R/tools/die_plan/check.py" "$O/die_plan.json" --completeness --landing "$O/r8/qwen_kvsys_r8_landing.json" --out "$O/g0cv" || true
