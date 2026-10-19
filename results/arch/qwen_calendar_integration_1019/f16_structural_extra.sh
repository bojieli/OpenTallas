#!/bin/bash
set -euo pipefail
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
SRCS="src/rtl/qwen_dv/qfd_dv_typed_su_observer.sv src/rtl/qwen_dv/qfd_dv_typed_witness_control.sv src/rtl/test/qwen_dv/tb_qwen_typed_witness_control.sv"
for pair in 1 0;do
 "$V" --binary --timing -j 8 -Wno-fatal --top-module tb_qwen_typed_witness_control -GEN=1 -GSAFE=1 -GPAIR=$pair -Mdir paired_obj$pair $SRCS > paired_build$pair.log 2>&1
 done
mkdir -p paired
for stim in vec/stim_*.txt;do
 name=$(basename "$stim" .txt)
 paired_obj1/Vtb_qwen_typed_witness_control +STIM="$stim" > paired/$name.log 2>&1
 done
for mech in SKEW DUE_CORRUPT;do
 paired_obj0/Vtb_qwen_typed_witness_control +STIM=vec/stim_nominal.txt +$mech > paired/mech_$mech.log 2>&1
 grep -q F16_INJECT paired/mech_$mech.log
 grep -q TWC_RESULT_FAULT paired/mech_$mech.log
 done
paired_obj1/Vtb_qwen_typed_witness_control +STIM=vec/stim_nominal.txt +OVERFLOW > paired/overflow.log 2>&1
grep -q F16_ACTUAL_CACHE_OVERFLOW_PASS paired/overflow.log
grep -q TWC_RESULT_FAULT paired/overflow.log
echo F16_PAIRED_28_AND_MECHANISM_2_AND_OVERFLOW_PASS
