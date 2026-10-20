#!/bin/bash
set -eu
out=$PWD/reset_copy_proof;mkdir -p "$out"
for mode in exact no_reset_assumption WRONG_D WRONG_VALUE MISSING_RESET;do
 def="";case "$mode" in WRONG*)def="-D$mode";;MISSING_RESET)def="-D$mode";;esac
 temporal='-seq 5 -set-at 1 rst_n 1 -set-at 2 rst_n 0 -set-at 3 rst_n 1 -set-at 4 rst_n 1 -set-at 5 rst_n 1 -prove-skip 1'
 if [ "$mode" = no_reset_assumption ];then temporal='-seq 1 -set rst_n 1';fi
 set +e
 yosys -Q -T -p "read_verilog -formal -sv $def rtl/test/host_reset_copy_1020/common_reset.sv; hierarchy -top common_reset; proc; flatten; async2sync; opt_clean; sat $temporal -prove equal 1 -verify -show q0,q1,rst_n,d" >"$out/$mode.log" 2>&1
 rc=$?
 set -e
 if [ "$mode" = exact ];then test "$rc" = 0;grep -q 'SUCCESS' "$out/$mode.log";else test "$rc" != 0;grep -q 'proof did fail' "$out/$mode.log";fi
 echo "RESET_COPY $mode expected result confirmed"
done
yosys -Q -T -p "read_verilog -formal -sv rtl/test/host_reset_copy_1020/common_reset.sv; hierarchy -top common_reset; proc; flatten; async2sync; opt_clean; sat -seq 3 -tempinduct -prove qualified_equal 1 -verify -show q0,q1,rst_n,d,reset_seen" >"$out/conditional_induction.log" 2>&1
grep -q 'SUCCESS' "$out/conditional_induction.log"
echo 'RESET_COPY conditional induction confirmed; no arbitrary-initial equality claim'
