#!/usr/bin/env bash
# KVG3-CORES 10-24: plan v3.8v -> v3.8x = post_v38w.py (pv/pc spreads) + post_v38x.py (head_eighth 285.12 -> 216) +
# g3/ft_channel_regs.py --add-stations (ONE pass on the final core geometry: free channel space changed) + gen.py
# latency, then G0 / G0C.  Pins: core_pins_resize_v38x.py re-spreads the 8 head_eighth pins files (run before this).
#   usage: run_v38x.sh V38V_DIE_PLAN.json OUTDIR
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd)
IN=${1:?v3.8v die_plan.json}; O=${2:?output directory}; mkdir -p "$O"
python3 "$D/post_v38w.py" "$IN" > "$O/die_plan.w.json"
python3 "$D/post_v38x.py" "$O/die_plan.w.json" > "$O/die_plan.0.json"
python3 "$D/g3/ft_channel_regs.py" "$O/die_plan.0.json" --report "$O/ft_channel_regs.json" --add-stations > "$O/die_plan.json"
python3 "$R/tools/die_plan/gen.py" latency "$O/die_plan.json" --inplace --out "$O/lat" --groups "$D/r8/bus_groups.json"
cp -r "$D/cores" "$D/census" "$D/r8" "$D/core_conns.json" "$D/cells_evidence.json" "$D/die_io.json" "$D"/l1_cores_v3*.json "$O/"
python3 "$R/tools/die_plan/check.py" "$O/die_plan.json" --landing "$O/r8/qwen_kvsys_r8_landing.json" --out "$O/g0x"
python3 "$R/tools/die_plan/check.py" "$O/die_plan.json" --completeness --landing "$O/r8/qwen_kvsys_r8_landing.json" --out "$O/g0cx" || true
