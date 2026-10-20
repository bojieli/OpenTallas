#!/usr/bin/env bash
set -euo pipefail
out=$1
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version | grep '5.050'
mkdir -p "$out"
verilator --binary --timing -j 4 -Wno-fatal --top-module tb --Mdir "$out/obj" rtl/qwen_dv/s5/qfd_dv_s5_red_ring32.sv rtl/qwen_dv/qfd_dv_reset_tree.sv rtl/test/qwen_dv/red_ring32/tb.sv > "$out/build.log" 2>&1
"$out/obj/Vtb" > "$out/run.log" 2>&1
grep 'RED_RING32 PASS' "$out/run.log"
