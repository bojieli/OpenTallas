#!/bin/bash
set -euo pipefail
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
root=$PWD
p=tools/s81_dv/attw_control_1022/proof
verilator --version
for mode in legal mutant; do
 mkdir -p proof_$mode
 if [[ $mode == mutant ]]; then
  sed 's/bypass_leaf\[word_i\] ? bd/!bypass_leaf[word_i] ? bd/' "$p/fmem_dut.sv" > proof_$mode/fmem_dut.sv
 else cp "$p/fmem_dut.sv" proof_$mode/fmem_dut.sv; fi
 verilator --binary --timing -j 8 -Wno-fatal --top-module tb -DSYNTHESIS -DOT_S81_ATTW_ENABLE_R4 --Mdir proof_$mode/obj "$p/tb.sv" "$p/fmem_ref.sv" proof_$mode/fmem_dut.sv rtl/dsrom_sys/s81_dv/svc_rs/ot_s81_attw_reset_fork.sv > proof_$mode/build.log 2>&1
 set +e
 proof_$mode/obj/Vtb > proof_$mode/run.log 2>&1
 rc=$?
 set -e
 cat proof_$mode/run.log
 if [[ $mode == legal ]]; then [[ $rc == 0 ]]; grep -q FMEM_R4_EQ_PASS proof_$mode/run.log
 else [[ $rc != 0 ]]; grep -q FMEM_R4_MISMATCH proof_$mode/run.log; echo 'FMEM_R4_BYPASS_MUTANT_CAUGHT'; fi
 done
