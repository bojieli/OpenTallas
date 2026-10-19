#!/bin/bash
set -euo pipefail
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
SRCS="src/rtl/qwen_dv/qfd_dv_typed_su_observer.sv src/rtl/qwen_dv/qfd_dv_typed_witness_control.sv src/rtl/test/qwen_dv/tb_qwen_typed_witness_control.sv"
"$V" --version > verilator.version
for pair in 1 0;do
 "$V" --binary --timing -j 8 -Wno-fatal --top-module tb_qwen_typed_witness_control -GEN=1 -GSAFE=1 -GSELECT=1 -GPAIR=$pair -Mdir obj$pair $SRCS > build$pair.log 2>&1
 done
mkdir -p paired
for stim in vec/stim_*.txt;do
 name=$(basename "$stim" .txt)
 obj1/Vtb_qwen_typed_witness_control +STIM="$stim" > paired/$name.log 2>&1
 done
grep -q 'completions=65 retired=5 starts=5' paired/stim_nominal.log
grep -q TWC_RESULT_CLEAN paired/stim_nominal.log
for mech in SKEW DUE_CORRUPT;do
 obj0/Vtb_qwen_typed_witness_control +STIM=vec/stim_nominal.txt +$mech > paired/mech_$mech.log 2>&1
 grep -q F16_INJECT paired/mech_$mech.log
 grep -q TWC_RESULT_FAULT paired/mech_$mech.log
 done
obj1/Vtb_qwen_typed_witness_control +STIM=vec/stim_nominal.txt +OVERFLOW > paired/overflow.log 2>&1
grep -q F16_ACTUAL_CACHE_OVERFLOW_PASS paired/overflow.log
echo F16_SELECT_PAIRED_28_MECHANISM_2_OVERFLOW_PASS
obj1/Vtb_qwen_typed_witness_control +STIM=vec/stim_nominal.txt +CHECK_SECTORS > paired/coverage.log 2>&1
for mech in SELECT_WRONG SELECT_CLEAR BANK_WRONG;do
 obj0/Vtb_qwen_typed_witness_control +STIM=vec/stim_nominal.txt +$mech > paired/mech_$mech.log 2>&1
 grep -q F16_ paired/mech_$mech.log
 grep -q TWC_RESULT_FAULT paired/mech_$mech.log
 done
obj0/Vtb_qwen_typed_witness_control +STIM=vec/stim_nominal.txt +RESET_CLEAR > paired/reset_clear.log 2>&1
grep -q F16_PENDING_ASYNC_CLEAR_PASS paired/reset_clear.log
echo F16_SELECT_COVERAGE_THREE_MUTANTS_ASYNC_CLEAR_PASS
