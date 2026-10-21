#!/usr/bin/env bash
set -euo pipefail
out=$1
mkdir -p "$out"
iverilog -V > "$out/version.txt" 2>&1
iverilog -g2012 -s tb_prefix_reset -o "$out/prefix.vvp" rtl/test/qwen_dv/s8/{tb_prefix_reset,prefix_reset_old,prefix_reset_new,prefix_reset_old_deps,prefix_reset_new_deps}.sv rtl/common/landed_parent/{ot_pl_land,ot_pl_land_physical,ot_pl_land_n32}.sv > "$out/build.log" 2>&1
sha256sum rtl/test/qwen_dv/s8/{tb_prefix_reset,prefix_reset_old,prefix_reset_new}.sv "$out/prefix.vvp" > "$out/sources_binary.sha256"
vvp "$out/prefix.vvp" > "$out/primary.log" 2>&1
cat "$out/primary.log"
