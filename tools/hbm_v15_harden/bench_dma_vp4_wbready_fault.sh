#!/bin/bash
# vp4 controller wb_ready pin capture: not-ready at the first drain faults exactly one edge after the cursor reference.
# MUT=1 removes the registered not-ready fault term (must FAIL).
set -euo pipefail
out=${1:?};mut=${2:-0};mkdir -p "$out"
d=rtl/hbm_accel/generic/peers/static
cp "$d/ot_hgi_dma_back_static_vp4_banks.sv" "$out/vp.sv"
if [ "$mut" = 1 ];then sed -i "s/if(first_drain_q\&\&!wb_ready_q)mv_fault<=1;//" "$out/vp.sv";cmp -s "$out/vp.sv" "$d/ot_hgi_dma_back_static_vp4_banks.sv" && { echo MUTANT_NOT_APPLIED;exit 3; };fi
m=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
iverilog -g2012 -s tb_dma_vp4_wbready_fault -o "$out/a.vvp" "$m" "$d/ot_hgi_dma_back_static_vp_banks.sv" "$d/ot_hgi_dma_back_static_cursor.sv" "$out/vp.sv" "$d/tb_dma_vp4_wbready_fault.sv"
vvp "$out/a.vvp" | tee "$out/run.log";grep -q DMA_WBREADY_FAULT_PASS "$out/run.log"
