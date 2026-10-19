#!/usr/bin/env bash
set -eu
out=$1; delay=${2:-7}; mut=${3:-0}; mkdir -p "$out"
vlt="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$vlt" --version
"$vlt" --binary --timing -j 2 -Wno-fatal --top-module tb_svg_meta_delay7 -GD="$delay" -GMUT="$mut" --Mdir "$out/obj" \
 rtl/hbm_accel/loader/service_native/ot_hbm_svg_meta_delay7.sv \
 rtl/test/hbm_accel/svg_rel/meta_delay8_evidence/meta_delay7_reference.sv \
 rtl/test/hbm_accel/svg_rel/tb_svg_meta_delay7.sv > "$out/build.log" 2>&1
ulimit -c 0
"$out/obj/Vtb_svg_meta_delay7"
