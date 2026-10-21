#!/bin/bash
set -euo pipefail
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mkdir -p ../out
for D in 2 8; do
 for M in 0 1 2 3; do
  "$V" --binary --timing -j 2 --top-module tb_ring -GDPT=$D -GMUT=$M -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --Mdir ../out/obj_d${D}m${M} \
   rtl/hdc/v41x/ot_hdc_v41x_merge_ring_sram.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v tools/s81_dv/svc_rs/merge_sram/tb_ring.sv > ../out/build_d${D}m${M}.log 2>&1
  ../out/obj_d${D}m${M}/Vtb_ring > ../out/run_d${D}m${M}.log 2>&1
  cat ../out/run_d${D}m${M}.log
 done
done
