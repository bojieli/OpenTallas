#!/bin/bash
set -euo pipefail
task_root=$(cd -- "$(dirname -- "$0")/../../.." && pwd)
cd "$task_root"
out="${FIFO2_OUT:-${task_root}-run-$(date +%Y%m%d_%H%M%S)}"
if test -e "$out";then echo "Refusing existing $out" >&2;exit 2;fi
mkdir -p "$out"
/home/ubuntu/.local/opentallas-tools/bin/verilator --binary --timing -j 2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 --top-module tb_fifo2 physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v rtl/physical/ot_qc_cal_fifo2_512.sv tools/qwen_dv/cal_fifo2_0222/tb_fifo2.sv -Mdir "$out/obj" > "$out/build.log" 2>&1
"$out/obj/Vtb_fifo2" > "$out/run.log" 2>&1
