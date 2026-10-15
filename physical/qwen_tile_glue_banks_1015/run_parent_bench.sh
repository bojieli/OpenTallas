#!/usr/bin/env bash
set -euo pipefail
mut=${1:-0}; out=${2:-sim_parent_m$mut}
mkdir -p "$out"
verilator --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -DOT_QWEN_LSL_FP1 -CFLAGS -O0 --output-split 20000 --output-split-cfuncs 2000 --top-module tb_parent_banked -GMUT="$mut" --Mdir "$out/obj" -f sim_sources.list > "$out/build.log" 2>&1
rc=0;"$out/obj/Vtb_parent_banked" +OT_ROM_DIR=masks > "$out/run.log" 2>&1 || rc=$?
cat "$out/run.log"
if [[ "$mut" == 0 ]]; then
 grep -q '^PASS actual full old-parent' "$out/run.log" && test "$rc" == 0
else
 grep -q 'FAIL parent' "$out/run.log" && test "$rc" != 0
fi
