#!/bin/bash
set -eu
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
OUT=$(mkdir -p "${1:-scratch/launch_age}" && realpath "${1:-scratch/launch_age}")
CAL="$OUT/lists"
PYTHONPATH=tools python3 -m qwen_static_schedule.expand_lifecycle_ovl_model results/arch/mu_context_phase_model_1019/lifecycle_F16_P2.json --out "$CAL" > "$OUT/model.log"
D=rtl/qwen_sys/d2d_static_20261015
"$V" --binary --timing -j 4 -O2 -Wno-fatal -Wno-WIDTH --top-module tb_ovl_launch_age -GDIR="\"$CAL\"" --Mdir "$OUT/obj" "$D/ot_qwen_d2d_cal_seq.sv" "$D/ot_qwen_d2d_ovl_seq.sv" "$D/ot_qwen_d2d_static.sv" rtl/test/qwen_split/tb_ovl_launch_age.sv > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_ovl_launch_age" > "$OUT/run.log"
cat "$OUT/run.log"
grep -q '^OVL_LAUNCH_PASS' "$OUT/run.log"
