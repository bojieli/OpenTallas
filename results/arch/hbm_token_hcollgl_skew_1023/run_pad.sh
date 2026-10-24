#!/bin/bash
# TOKg 10-23: tb_coll_replay (real SW gq + ring A/B + shares) with a die-like delay on the A-ring publish lane into hcollgl.
set -u
cd "$(dirname "$0")"
FILES=$(cat files.txt)
for D in 0 1 3; do
  verilator --binary -j 8 --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_coll_replay -GPA_DLY=$D -Mdir obj_$D tb_coll_replay_pad.sv $FILES > build_$D.log 2>&1 || { echo "BUILD_FAIL D=$D"; tail -20 build_$D.log; continue; }
  for e in pre_l0/*.events.txt; do n=$(basename $e .events.txt)
    r=$(timeout 600 obj_$D/Vtb_coll_replay +EV=$e 2>&1 | grep "COLLRPL PASS\|COLLRPL FAIL" | tail -1)
    echo "D=$D $n $r"
  done
done
