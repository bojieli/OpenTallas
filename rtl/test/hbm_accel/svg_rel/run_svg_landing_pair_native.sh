#!/usr/bin/env bash
set -eu
out=$1;mut=${2:-0};j=${3:-1};mkdir -p "$out"
vlt="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$vlt" --version
"$vlt" --binary --timing -j 2 -Wno-fatal --top-module tb_svg_landing_pair_native -GMUT="$mut" -GJ="$j" --Mdir "$out/obj" \
 rtl/lib/ot_reset_sync.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_async_fifo.sv \
 rtl/hbm_accel/loader/service_native/ot_hbm_svc_async_fifo_sram285.sv \
 rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm8_landing_bank.sv \
 rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm8_landing_bank_sram285.sv \
 rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm8_landing_boundary.sv \
 rtl/hbm_accel/loader/service_native/ot_hbm_svg_return_regional.sv \
 rtl/hbm_accel/loader/service_native/ot_hbm_svg_landing_pair_native.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_8x285_m1/ot_sram_1r1w2c_8x285_m1.v \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
 rtl/test/hbm_accel/svg_rel/tb_svg_landing_pair_native.sv > "$out/build.log" 2>&1
"$out/obj/Vtb_svg_landing_pair_native"
