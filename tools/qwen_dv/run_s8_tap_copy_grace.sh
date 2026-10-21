#!/usr/bin/env bash
set -euo pipefail
out=$1
mkdir -p "$out"
inputs=(rtl/test/qwen_dv/s8/tb_tap_copy_grace.sv rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_n32.sv rtl/common/landed_parent/ot_pl_land_split.sv rtl/common/landed_parent/ot_pl_land_rst_copy.sv)
sha256sum "${inputs[@]}" > "$out/sources.sha256"
iverilog -g2012 -s tb_tap_copy_grace -o "$out/grace.vvp" "${inputs[@]}" > "$out/build.log" 2>&1
sha256sum "$out/grace.vvp" > "$out/binary.sha256"
timeout 60 vvp "$out/grace.vvp" > "$out/primary.log" 2>&1
cat "$out/primary.log"
grep -q TAP_COPY_GRACE_BOTH_PASS "$out/primary.log"
