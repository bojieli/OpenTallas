#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch3/claude/qc-mem9-comp/cap
out=/srv/opentallas-scratch3/claude/qc-mem9-comp/out3
test -e "$out" && { echo exists; exit 2; }
mkdir -p "$out"
/home/ubuntu/.local/opentallas-tools/bin/verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 --top-module tb_mem9comp -f tools/qwen_dv/su1_numeric_1551/sources_comp.f -Mdir "$out/obj" > "$out/build.log" 2>&1
"$out/obj/Vtb_mem9comp" > "$out/run.log" 2>&1
echo done
