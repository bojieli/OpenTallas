#!/usr/bin/env bash
set -eu
out=$1;mut=${2:-0};prel=${3:-1};class=${4:-0};cmut=${5:-0};mmut=${6:-0};gap=${7:-9};mkdir -p "$out"
vlt="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$vlt" --version
"$vlt" --binary --timing -j 2 -Wno-fatal --top-module tb_xcal_public_banked \
 -GMUT="$mut" -GPREL="$prel" -GCLASS_ENABLE="$class" -GCLASS_MUT="$cmut" -GMIRROR_MUT="$mmut" -GGAP="$gap" --Mdir "$out/obj" \
 rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_xcal_rel_banked.sv \
 rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_xcal_rel_t_banked.sv \
 rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_xcal_rel.sv \
 rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_xcal_rel_t.sv \
 rtl/hbm_accel/host_static_20261015/ot_static_run_target.sv \
 rtl/hbm_accel/sm/static/ot_smh_calendar_static_x.sv \
 rtl/hbm_accel/sm/static/ot_smh_calendar_banked_cells.sv \
 rtl/hbm_accel/sm/static/ot_smh_calendar_banked_central.sv \
 rtl/hbm_accel/sm/static/ot_smh_calendar_bank_leaf.sv \
 rtl/hbm_accel/sm/static/ot_smh_banked_xc_central.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 rtl/test/hbm_accel/svg_rel/tb_xcal_public_banked.sv > "$out/build.log" 2>&1
"$out/obj/Vtb_xcal_public_banked"
