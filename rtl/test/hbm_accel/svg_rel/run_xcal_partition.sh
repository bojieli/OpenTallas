#!/usr/bin/env bash
set -eu
out=$1;mut=${2:-0};early=${3:-0};mkdir -p "$out"
vlt="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$vlt" --version
"$vlt" --binary --timing -j 2 -Wno-fatal -Wno-TIMESCALEMOD --top-module tb_xcal_partition -GMUT="$mut" -GEARLY="$early" --Mdir "$out/obj" -o sim \
 rtl/hbm_accel/loader/service_native/ot_hbm_xcal_partition_t.sv \
 rtl/hbm_accel/loader/service_native/ot_hbm_xcal_desc_native.sv \
 rtl/hbm_accel/loader/service_native/ot_hbm_xcal_prog_native.sv \
 rtl/hbm_accel/host_static_20261015/ot_static_run_target.sv \
 rtl/hbm_accel/sm/static/ot_smh_calendar_static_x.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 rtl/test/hbm_accel/svg_rel/tb_xcal_partition.sv > "$out/build.log" 2>&1
"$out/obj/sim"
