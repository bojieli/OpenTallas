#!/bin/bash
set -euo pipefail
R=$(pwd)
O=${1:-out}
mkdir -p "$O"
O=$(realpath "$O")
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version > "$O/verilator.version"
sha256sum $(cat tools/s81_dv/layer_prog/rdpair/sources.f) > "$O/sources.sha256"
"$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD +define+OT_S81SL_RD_PAIR --top-module tb_rd_pair -Mdir "$O/obj" -f tools/s81_dv/layer_prog/rdpair/sources.f --build-jobs 8 -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' > "$O/build.log" 2>&1
for mut in 0 1 2 3 4 5 6 7 8 9 10 11; do
 "$O/obj/Vtb_rd_pair" +MUT=$mut > "$O/mut_${mut}.log" 2>&1
 grep -E '^(RDPAIR|PASS|FAIL)' "$O/mut_${mut}.log"
 if [ "$mut" = 0 ]; then grep -q '^PASS$' "$O/mut_${mut}.log"; else grep -q '^FAIL$' "$O/mut_${mut}.log"; fi
done
