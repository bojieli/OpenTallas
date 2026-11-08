#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-qc-su1-numeric-1551
out=/srv/opentallas-scratch2/claude/codex-qc-su1-numeric-1551-run3
mkdir -p "$out"
/home/ubuntu/.local/opentallas-tools/bin/verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 --top-module tb_su1_numeric_1551 -f tools/qwen_dv/su1_numeric_1551/sources.f -Mdir "$out/obj" > "$out/build.log" 2>&1
"$out/obj/Vtb_su1_numeric_1551" > "$out/run.log" 2>&1
