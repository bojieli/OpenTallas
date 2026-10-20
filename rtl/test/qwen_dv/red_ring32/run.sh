#!/usr/bin/env bash
set -euo pipefail
out=$1
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version | grep '5.050'
mkdir -p "$out"
mut=${2:-0}
defs=()
[[ $mut == 0 ]] || defs+=(+define+OT_RED_RING32_AGE_MUT)
verilator "${defs[@]}" --binary --timing -j 4 -Wno-fatal --top-module tb --Mdir "$out/obj" rtl/qwen_dv/s5/qfd_dv_s5_red_ring32.sv rtl/qwen_dv/qfd_dv_reset_tree.sv rtl/test/qwen_dv/red_ring32/tb.sv > "$out/build.log" 2>&1
set +e
"$out/obj/Vtb" > "$out/run.log" 2>&1
rc=$?
set -e
if [[ $mut != 0 ]]; then [[ $rc != 0 ]]; grep RING32_AGE "$out/run.log"; exit 0; fi
[[ $rc == 0 ]]
grep 'RED_RING32 PASS' "$out/run.log"
