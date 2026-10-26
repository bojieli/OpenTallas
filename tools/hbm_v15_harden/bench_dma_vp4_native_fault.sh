#!/bin/bash
set -euo pipefail
out=${1:?};mkdir -p "$out"
d=rtl/hbm_accel/generic/peers/static
m=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
iverilog -g2012 -s tb_dma_vp4_native_fault -o "$out/a.vvp" "$m" "$d/ot_hgi_dma_back_static_vp_banks.sv" "$d/ot_hgi_dma_back_static_vp4_banks.sv" "$d/tb_dma_vp4_native_fault.sv"
vvp "$out/a.vvp"
