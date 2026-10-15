#!/usr/bin/env bash
set -euo pipefail
out=${1:?out};mkdir -p "$out"
src=rtl/qwen_sys/band_fault_tree_20261015/ot_qfd_band_fault_tree3.sv
proof=physical/qwen_band_fault_tree_1015
for mut in 0 1 2 3 4 5 6;do
 rc=0
 yosys -Q -p "read_verilog -sv $src $proof/original_upper_faces.sv $proof/prove_tree3.sv; chparam -set MUT $mut prove_tree3; hierarchy -top prove_tree3; proc; flatten; opt; sat -seq 5 -set-def-inputs -prove-skip 2 -verify -prove exact 1 -show-inputs" > "$out/formal_m$mut.log" 2>&1||rc=$?
 if [[ $mut == 0 ]];then [[ $rc == 0 ]]||exit 10;grep -q 'SUCCESS' "$out/formal_m$mut.log";else [[ $rc != 0 ]]||exit 11;grep -q 'proof did fail' "$out/formal_m$mut.log";fi
 echo "BAND_FORMAL_MUTANT=$mut TOOL_EXIT=$rc EXPECTED_RESULT=PASS"
 iverilog -g2012 -s tb_tree3 -Ptb_tree3.MUT="$mut" -o "$out/m$mut.vvp" "$proof/tb_tree3.sv" "$src" "$proof/original_upper_faces.sv" "$proof/prove_tree3.sv" > "$out/compile_m$mut.log" 2>&1
 rc=0;vvp "$out/m$mut.vvp" > "$out/bench_m$mut.log" 2>&1||rc=$?
 if [[ $mut == 0 ]];then [[ $rc == 0 ]]||{ cat "$out/bench_m$mut.log";exit 12; };grep -q 'BAND_TREE PASS' "$out/bench_m$mut.log";else [[ $rc != 0 ]]||exit 13;grep -q 'BAND_TREE FAIL' "$out/bench_m$mut.log";fi
 echo "BAND_BENCH_MUTANT=$mut TOOL_EXIT=$rc EXPECTED_RESULT=PASS"
done
cat "$out/bench_m0.log"
