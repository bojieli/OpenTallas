#!/bin/bash
# HBM-SU3 10-17: qcore successor r5 (ot_hbm_su_static_qcore_r5) lockstep vs the die qcore. usage: OUT [MUT]
# HH-11 10-19: Verilator 5.050 (the closure daemon's version; was iverilog); r5 file = the r6 sector structure.
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1"); mut=${2:-0}; mkdir -p "$out"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$VL" ] || VL=verilator
S=rtl/hbm_accel/generic/adapters/static_su
$VL --version | tee "$out/verilator_version.txt"
$VL --binary --timing -j 8 --top-module tb_qcore_rg_lockstep -GMUT=$mut -Wno-fatal -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC \
 -Wno-PINMISSING --Mdir "$out/obj" -o vtb \
 $S/top/ot_hbm_su_static_qcore.sv $S/top/ot_hbm_su_static_qcore_r5.sv $S/register_file/ot_hbm_su_static_rf.sv $S/reduction/ot_hbm_su_reduce_static.sv \
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 rtl/test/hbm_qcore_physical_1016/tb_qcore_rg_lockstep.sv > "$out/build.log" 2>&1 || { tail -30 "$out/build.log"; exit 2; }
(cd "$out" && ./obj/vtb) | tee "$out/bench.log" | tail -8
