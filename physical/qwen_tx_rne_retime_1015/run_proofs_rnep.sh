#!/usr/bin/env bash
# RNEp (prefix successor) proofs: formal equivalence vs independent full32 RNE + TX198 codec, then the two-edge bench.
set -euo pipefail
out=${1:?out};mkdir -p "$out"
rtl=rtl/qwen_sys/tx_rne_retime_20261015/qwen_tx_rnep.sv
proof=physical/qwen_tx_rne_retime_1015
for mut in 0 1 2 3 4 7;do
 rc=0
 yosys -Q -p "read_verilog -sv $rtl rtl/qwen_sys/tile_glue_banks_20261015/ot_qwen_tx198.sv $proof/prove_tx_rnep.sv; chparam -set MUT $mut prove_tx_rnep; hierarchy -top prove_tx_rnep; proc; flatten; opt; sat -verify -prove exact 1 -show-inputs" > "$out/formal_m$mut.log" 2>&1||rc=$?
 if [[ $mut == 0 ]];then [[ $rc == 0 ]]||exit 10;grep -q 'SUCCESS' "$out/formal_m$mut.log";else [[ $rc != 0 ]]||exit 11;grep -q 'proof did fail' "$out/formal_m$mut.log";fi
 echo "FORMAL_MUTANT=$mut TOOL_EXIT=$rc EXPECTED_RESULT=PASS"
done
for mut in 0 1 2 3 4 5 6 7;do
 iverilog -g2012 -s tb_tx_rne -Ptb_tx_rne.MUT="$mut" -o "$out/m$mut.vvp" "$proof/tb_tx_rnep.sv" "$rtl" rtl/qwen_sys/head_staging_20261015/ot_qkh_packet_stage.sv rtl/lib/ot_rst_relay.sv > "$out/compile_m$mut.log" 2>&1
 rc=0;vvp "$out/m$mut.vvp" > "$out/bench_m$mut.log" 2>&1||rc=$?
 if [[ $mut == 0 ]];then [[ $rc == 0 ]]||{ cat "$out/bench_m$mut.log";exit 12; };grep -q 'PASS RNEprefix267to198' "$out/bench_m$mut.log";else [[ $rc != 0 ]]||exit 13;grep -q 'FAIL RNE' "$out/bench_m$mut.log";fi
 echo "BENCH_MUTANT=$mut TOOL_EXIT=$rc EXPECTED_RESULT=PASS"
done
cat "$out/bench_m0.log"
