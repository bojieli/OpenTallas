#!/usr/bin/env bash
set -eu
out=$1;mut=${2:-0};mkdir -p "$out"
iverilog -g2012 -s tb_xcal_rel_t -Ptb_xcal_rel_t.MUT="$mut" -o "$out/tb.vvp" \
 rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_xcal_rel_t.sv \
 rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_xcal_rel.sv \
 rtl/hbm_accel/host_static_20261015/ot_static_run_target.sv \
 rtl/hbm_accel/sm/static/ot_smh_calendar_static_x.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 rtl/test/hbm_accel/svg_rel/tb_xcal_rel_t.sv
vvp "$out/tb.vvp"
