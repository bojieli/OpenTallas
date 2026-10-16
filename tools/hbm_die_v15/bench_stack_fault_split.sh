#!/bin/bash
set -euo pipefail
out=${1:?out};mut=${2:-0};mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
iverilog -g2012 -s tb_hbm_stack_fault_split -Ptb_hbm_stack_fault_split.MUT="$mut" -o "$out/sim.vvp" "$d/ot_hbm_svc_stack_fault.sv" "$d/ot_hbm_svc_stack_fault_split.sv" "$d/tb_hbm_stack_fault_split.sv" > "$out/build.log" 2>&1
vvp "$out/sim.vvp" > "$out/result.log" 2>&1 || { cat "$out/result.log";exit 1; }
cat "$out/result.log";grep -q 'STACK_FAULT_SPLIT PASS' "$out/result.log"
