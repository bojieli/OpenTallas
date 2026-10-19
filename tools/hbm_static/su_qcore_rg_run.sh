#!/bin/bash
# HBM-SU3 10-17: qcore successor r5 (ot_hbm_su_static_qcore_r5) lockstep vs the die qcore. usage: OUT [MUT]
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1"); mut=${2:-0}; mkdir -p "$out"
S=rtl/hbm_accel/generic/adapters/static_su
iverilog -g2012 -s tb_qcore_rg_lockstep -Ptb_qcore_rg_lockstep.MUT=$mut -o "$out/qcore.vvp" \
 $S/top/ot_hbm_su_static_qcore.sv $S/top/ot_hbm_su_static_qcore_r5.sv $S/register_file/ot_hbm_su_static_rf.sv $S/reduction/ot_hbm_su_reduce_static.sv \
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 rtl/test/hbm_qcore_physical_1016/tb_qcore_rg_lockstep.sv
vvp -n "$out/qcore.vvp" | tee "$out/bench.log" | tail -8
