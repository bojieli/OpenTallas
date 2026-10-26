#!/usr/bin/env bash
# usage: run_host_landing.sh OUT [MUT] [PINREG]   MUT 1: read address off by one; MUT 2: pop ignores the out_v mirror
set -euo pipefail
out=$1;mut=${2:-0};pinreg=${3:-1};mkdir -p "$out";defs=()
if [[ "$mut" == 1 ]];then defs=(-DOT_HOST_LANDING_MUT_ADDR);fi
if [[ "$mut" == 2 ]];then defs=(-DOT_HOST_LANDING_MUT_NOMIRROR);fi
iverilog -g2012 -DOT_MEM_NO_INIT "${defs[@]}" -Ptb_hbm_host_landing256.PINREG=$pinreg -s tb_hbm_host_landing256 -o "$out/sim" \
 rtl/hbm_accel/io_native_20261014/{ot_hbm_host_landing256,tb_hbm_host_landing256}.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v > "$out/build.log" 2>&1
vvp -n "$out/sim" > "$out/run.log" 2>&1
cat "$out/run.log"
grep -q '^HBM_HOST_LANDING_PASS' "$out/run.log"
