#!/bin/bash
set -eu
out=$1;mkdir -p "$out";out=$(cd "$out" && pwd)
vlt="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$vlt" --version | grep 'Verilator 5.050'
python3 rtl/test/hbm_accel/svg_rel/gen_banked_app_references.py "$out"
"$vlt" --binary --timing -j 2 -Wno-fatal -Wno-TIMESCALEMOD --top-module tb_banked_apps --Mdir "$out/obj" -o sim \
 rtl/hbm_accel/sm/static/ot_smh_calendar_banked_cells.sv \
 rtl/hbm_accel/sm/static/ot_smh_calendar_bank_leaf.sv \
 rtl/hbm_accel/sm/static/ot_smh_calendar_banked_central.sv \
 rtl/hbm_accel/sm/static/ot_smh_banked_svg_central.sv \
 rtl/hbm_accel/sm/static/ot_smh_banked_xc_central.sv \
 rtl/hbm_accel/sm/static/ot_smh_calendar_static_x.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 "$out/reference_svg.sv" "$out/reference_xc.sv" rtl/test/hbm_accel/svg_rel/tb_banked_apps.sv > "$out/build.log" 2>&1
"$out/obj/sim"
