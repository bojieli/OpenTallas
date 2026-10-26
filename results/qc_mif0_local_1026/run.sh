#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
for tag in nominal wrong_edge wrong_row; do
 src=candidate.sv
 if [ "$tag" != nominal ]; then src=$tag.sv; fi
 verilator --binary --timing -j8 --top-module tb --Mdir obj_$tag -Wno-fatal --x-assign 0 --x-initial 0 baseline.sv "$src" models.sv tb.sv > build_$tag.log 2>&1
 rc=0
 ./obj_$tag/Vtb +seed=3 > sim_$tag.log 2>&1 || rc=$?
 cat sim_$tag.log
 if [ "$tag" = nominal ]; then
  test "$rc" = 0
 else
  test "$rc" != 0
  grep -Eq 'BTAB consumed|PROG consumed|MISMATCH' sim_$tag.log
 fi
done
