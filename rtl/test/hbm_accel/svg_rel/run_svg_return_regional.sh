#!/usr/bin/env bash
set -eu
out=$1;mut=${2:-0};profile=${3:-0};mkdir -p "$out"
vlt="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$vlt" --version
"$vlt" --binary --timing -j 2 -Wno-fatal --top-module tb_svg_return_regional -GMUT="$mut" -GCPROFILE="$profile" --Mdir "$out/obj" \
 rtl/hbm_accel/loader/service_native/ot_hbm_svg_return_regional.sv \
 rtl/test/hbm_accel/svg_rel/tb_svg_return_regional.sv > "$out/build.log" 2>&1
"$out/obj/Vtb_svg_return_regional"
