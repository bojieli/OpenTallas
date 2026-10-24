#!/usr/bin/env bash
# KV-G3 10-24: plan v3.8v -> v3.8w = post_v38w.py (pv pair / pc core spreads from the KVG3-CORES review; core views
# unchanged, origins only) + g3/ft_channel_regs.py (GEOM-REVIEW batch 1: ft stations declared off hard cores, +1 station
# where no core-free fit exists) + gen.py latency, then G0 / G0C.
# The plan R8 table is r8/ (r8.py --bus leaf --replica type on r8/bus_groups.json, unchanged: L357/L758 are fault lanes);
# lat/ is the latency package only, so G0 names the r8/ table explicitly.
#   usage: run_v38w.sh V38V_DIE_PLAN.json OUTDIR
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd)
IN=${1:?v3.8v die_plan.json}; O=${2:?output directory}; mkdir -p "$O"
python3 "$D/post_v38w.py" "$IN" > "$O/die_plan.0.json"
python3 "$D/g3/ft_channel_regs.py" "$O/die_plan.0.json" --report "$O/ft_channel_regs.json" --add-stations > "$O/die_plan.json"
python3 "$R/tools/die_plan/gen.py" latency "$O/die_plan.json" --inplace --out "$O/lat" --groups "$D/r8/bus_groups.json"
cp -r "$D/cores" "$D/census" "$D/r8" "$D/core_conns.json" "$D/cells_evidence.json" "$D/die_io.json" "$D"/l1_cores_v3*.json "$O/"
python3 "$R/tools/die_plan/check.py" "$O/die_plan.json" --landing "$O/r8/qwen_kvsys_r8_landing.json" --out "$O/g0w"
python3 "$R/tools/die_plan/check.py" "$O/die_plan.json" --completeness --landing "$O/r8/qwen_kvsys_r8_landing.json" --out "$O/g0cw" || true
