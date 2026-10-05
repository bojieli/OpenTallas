#!/bin/bash
# Build and run a self-checking bench with Verilator --binary --timing on ot-epyc1tb:
#   vl_bench.sh <snapshot> <outdir> <top> "<-G/-P params>" "<runs: plusarg sets separated by ;>" <sources...>
R=/srv/opentallas-scratch/claude/hbm-fmax-qcore
src=$1; out=$2; top=$3; prm=$4; runs=$5; shift 5
cd $R/$src || exit 2
mkdir -p $out
verilator --binary --timing -O3 -j 16 -Wno-fatal -Wno-lint -Wno-style --top-module $top $prm -Mdir $out/obj "$@" > $out/build.log 2>&1 || { echo BUILD_FAIL; tail -30 $out/build.log; exit 1; }
IFS=';' read -ra RS <<< "$runs"
for r in "${RS[@]}"; do $out/obj/V$top $r | grep -E "RESULT|MISMATCH|Error|error" | head -12; done | tee $out/run.log
