#!/usr/bin/env bash
set -eu
out=$1;mut=${2:-0};mkdir -p "$out"
vlt="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$vlt" --version
"$vlt" --binary --timing -j 2 -Wno-fatal --top-module tb_cache_native8 -GMUT="$mut" --Mdir "$out/obj" \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 rtl/gpu/ot_gpu_payload_assemble.sv \
 rtl/hbm_accel/loader/service_native/ot_hbm_svc_static_sm_packed136.sv \
 rtl/hbm_accel/loader/service_native/ot_hbm_svc_static_sm_packed136_native8.sv \
 rtl/test/hbm_accel/svg_rel/tb_cache_native8.sv > "$out/build.log" 2>&1
"$out/obj/Vtb_cache_native8"
