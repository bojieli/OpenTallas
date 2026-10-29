#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")"
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
for mode in good mutant; do
 src=dut.sv; [ "$mode" = mutant ] && src=mutant.sv
 verilator --binary --timing -Wno-fatal --top-module tb -j 8 --Mdir obj_$mode tb.sv "$src" ot_dp_cells.sv ot_reset_sync.sv > build_$mode.log 2>&1 || exit 2
 ./obj_$mode/Vtb > run_$mode.log 2>&1; rc=$?
 tail -n 4 run_$mode.log
 if [ "$mode" = good ]; then [ "$rc" = 0 ] || exit 3; else [ "$rc" != 0 ] && grep -q N3_SPLIT_FAIL run_$mode.log || exit 4; echo MUTANT_CAUGHT; fi
done
