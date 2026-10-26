#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
R=/srv/opentallas-scratch2/claude/codex-qc-fe-reset-1026
verilator --binary --timing -j 8 -Wno-fatal --top-module tb --Mdir "$R/obj" -o Vtb "$R/new.sv" "$R/gold.sv" "$R/mut.sv" "$R/tb.sv" > "$R/build.log" 2>&1
"$R/obj/Vtb" > "$R/result.log" 2>&1
cat "$R/result.log"
