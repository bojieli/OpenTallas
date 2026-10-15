#!/bin/bash
# run_qkh_head_stages.sh OUT WHICH(0 tstage / 1 sstage) MUT
set -uo pipefail
out=$1; which=$2; mut=${3:-0}
mkdir -p "$out"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$v" ] || v=$(command -v verilator)
"$v" --binary --timing -O1 -j 2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_qkh_head_stages \
  -GWHICH="$which" -GMUT="$mut" --Mdir "$out/obj" -o tb rtl/test/qwen_split/tb_qkh_head_stages.sv \
  rtl/qwen_sys/split_20261014/qkh_head_stages.sv > "$out/build.log" 2>&1 || { tail -20 "$out/build.log"; exit 2; }
"$out/obj/tb" > "$out/run.log" 2>&1; rc=$?
cat "$out/run.log"; exit $rc
