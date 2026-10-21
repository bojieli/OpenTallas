#!/bin/bash
set -euo pipefail
R=$(pwd)
V="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
for c in norm eng norm_mutleaf eng_mutassoc; do
 case "$c" in norm) tr=1;defs=();;eng)tr=3;defs=();;norm_mutleaf)tr=1;defs=(-DOT_S81DV_MUT_LEAF);;eng_mutassoc)tr=3;defs=(-DOT_S81DV_MUT_EASSOC);;esac
 mkdir -p "$c"
 "$V" --binary --timing -j 2 -O1 -Wno-fatal -Wno-WIDTH -Wno-UNOPTFLAT --top-module read_oh_tb -GTR=$tr "${defs[@]}" -Mdir "$R/$c/obj" "$R/read_oh_helpers.sv" "$R/read_oh_tb.sv" > "$c/build.log" 2>&1
 "$R/$c/obj/Vread_oh_tb" > "$c/run.log" 2>&1
 cat "$c/run.log"
 grep -q 'bad=0' "$c/run.log"
done
