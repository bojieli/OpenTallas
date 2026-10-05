#!/bin/bash
set -eu
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
run_case() {
  label=$1; shift
  "$V" --binary --timing -Wno-fatal -j 16 --top-module tb_pcwb_digest_lockstep \
    --Mdir "obj_$label" "$@" \
    9b1d561d10fd_ot_hbm_accel_stream_pc_wb.sv \
    ot_hbm_accel_stream_pc_wb_digest.sv tb_pcwb_digest_lockstep.sv > "compile_$label.log" 2>&1
  for seed in 1 2 26; do
    "./obj_$label/Vtb_pcwb_digest_lockstep" +seed="$seed" +cycles=200000 > "lockstep_${label}_seed${seed}.log" 2>&1
  done
}
run_case late_pb
run_case exact_ab -GLATE=0 -GMODE=0 -GPC=1 -GWQ=4
