#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")"
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
for shape in normal end; do
 for mode in good mutant; do
  src=dut.sv; [ "$mode" = mutant ] && src=mutant.sv
  ( cd "$shape"; verilator --binary --timing -Wno-fatal --top-module tb -j 8 --Mdir obj_$mode tb.sv "$src" ot_dp_cells.sv ot_reset_sync.sv ot_s81hd_spo.sv ot_s81hd_spr.sv > build_$mode.log 2>&1 ) || exit 2
  ( cd "$shape"; ./obj_$mode/Vtb > run_$mode.log 2>&1 ); rc=$?
  tail -n 5 "$shape/run_$mode.log"
  if [ "$mode" = good ]; then [ "$rc" = 0 ] || exit 3; else [ "$rc" != 0 ] && grep -q SPINE_STRIP_FAIL "$shape/run_$mode.log" || exit 4; echo MUTANT_CAUGHT; fi
 done
done
