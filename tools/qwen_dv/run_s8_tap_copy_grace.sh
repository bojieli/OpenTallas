#!/usr/bin/env bash
set -euo pipefail
out=$1
mkdir -p "$out"
inputs=(rtl/test/qwen_dv/s8/tb_tap_copy_grace.sv rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_n32.sv rtl/common/landed_parent/ot_pl_land_split.sv rtl/common/landed_parent/ot_pl_land_rst_copy.sv)
sha256sum "${inputs[@]}" > "$out/sources.sha256"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version > "$out/version.txt"
verilator --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style --top-module tb_tap_copy_grace --Mdir "$out/obj" "${inputs[@]}" > "$out/build.log" 2>&1
sha256sum "$out/obj/Vtb_tap_copy_grace" > "$out/binary.sha256"
timeout 60 "$out/obj/Vtb_tap_copy_grace" > "$out/primary.log" 2>&1
cat "$out/primary.log"
grep -q TAP_COPY_GRACE_BOTH_PASS "$out/primary.log"
