#!/usr/bin/env bash
set -eu
out=$1;mut=${2:-0};mkdir -p "$out"
iverilog -g2012 -s tb_svg_landing_sram -Ptb_svg_landing_sram.MUT="$mut" -o "$out/tb.vvp" \
 rtl/lib/ot_reset_sync.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_async_fifo.sv \
 rtl/hbm_accel/loader/service_native/ot_hbm_svc_async_fifo_sram285.sv \
 rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm8_landing_bank.sv \
 rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm8_landing_bank_sram285.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_8x285_m1/ot_sram_1r1w2c_8x285_m1.v \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
 rtl/test/hbm_accel/svg_rel/tb_svg_landing_sram.sv
vvp "$out/tb.vvp"
