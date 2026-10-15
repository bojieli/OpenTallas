#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")"
out="${1:-/tmp/hbm-dma-back-static-run}"
bank="${VM_BANK_SOURCE:-../../vm/static/ot_vms_bank_static.sv}"
macro_root="${MACRO_ROOT:-../../../../../physical/asap7_memory_macros}"
macro_bank="$macro_root/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v"
macro_land="$macro_root/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
if [ -f ot_vms_bank_static.sv ]; then bank=ot_vms_bank_static.sv; fi
if [ -f ot_sram_1r1w_1024x256_m2_r2c2.v ]; then macro_bank=ot_sram_1r1w_1024x256_m2_r2c2.v; fi
if [ -f ot_sram_1r1w_128x256_m1_r2c2.v ]; then macro_land=ot_sram_1r1w_128x256_m1_r2c2.v; fi
mkdir -p "$out"
for mut in 0 1 2; do
/usr/bin/time -v -o "$out/compile-$mut.time" iverilog -g2012 -s tb_dma_back_static -Ptb_dma_back_static.MUT="$mut" -o "$out/back-$mut.vvp" ot_hgi_dma_back_static.sv ot_hgi_b2_swap_disp_static.sv ot_hgi_b2_swap_grp_static.sv "$bank" "$macro_bank" "$macro_land" tb_dma_back_static.sv > "$out/compile-$mut.log" 2>&1
set +e
/usr/bin/time -v -o "$out/sim-$mut.time" vvp "$out/back-$mut.vvp" > "$out/sim-$mut.log" 2>&1
rc=$?
set -e
cat "$out/sim-$mut.log"
if [ "$mut" -eq 0 ]; then test "$rc" -eq 0; else test "$rc" -ne 0; fi
done
printf 'PASS actual DMA static production, destination and early-source mutants\n'
/usr/bin/time -v -o "$out/guards-compile.time" iverilog -g2012 -s tb_dma_back_static_guards -o "$out/guards.vvp" ot_hgi_dma_back_static.sv "$macro_land" tb_dma_back_static_guards.sv > "$out/guards-compile.log" 2>&1
/usr/bin/time -v -o "$out/guards-sim.time" vvp "$out/guards.vvp" > "$out/guards-sim.log" 2>&1
cat "$out/guards-sim.log"
/usr/bin/time -v -o "$out/wrap-compile.time" iverilog -g2012 -s tb_dma_calendar_wrap -o "$out/wrap.vvp" ot_hgi_dma_back_static.sv "$macro_land" tb_dma_calendar_wrap.sv > "$out/wrap-compile.log" 2>&1
/usr/bin/time -v -o "$out/wrap-sim.time" vvp "$out/wrap.vvp" > "$out/wrap-sim.log" 2>&1
cat "$out/wrap-sim.log"
verilator --lint-only -Wall -Wno-UNUSEDSIGNAL -Wno-PINCONNECTEMPTY --top-module ot_hgi_b2_swap_grp_static ot_hgi_dma_back_static.sv ot_hgi_b2_swap_disp_static.sv ot_hgi_b2_swap_grp_static.sv "$macro_land" > "$out/lint.log" 2>&1
printf 'PASS DMA static structural lint (unused fields/unconnected per-engine done excluded)\n'
