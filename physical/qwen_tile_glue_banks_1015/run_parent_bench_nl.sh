#!/usr/bin/env bash
# usage: run_parent_bench_nl.sh TB MUT ALLB FAULT   (TB = tb_parent_nl_banked | tb_parent_banked_fault)
set -euo pipefail
tb=$1; mut=${2:-0}; allb=${3:-0}; fault=${4:-0}; out=sim_${tb}_m${mut}_a${allb}_f${fault}
mkdir -p "$out"
G="-GMUT=$mut"; [[ $tb == tb_parent_nl_banked* ]] && G="$G -GALLB=$allb -GFAULT=$fault"
verilator --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -DOT_QWEN_LSL_FP1 -CFLAGS -O0 --output-split 20000 --output-split-cfuncs 2000 --top-module $tb $G --Mdir "$out/obj" -f sim_sources.list physical/qwen_tile_glue_banks_1015/$tb.sv > "$out/build.log" 2>&1 || { tail -30 "$out/build.log"; exit 3; }
rc=0;"$out/obj/V$tb" +OT_ROM_DIR=masks > "$out/run.log" 2>&1 || rc=$?
tail -5 "$out/run.log"; echo "rc=$rc"
