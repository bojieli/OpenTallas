#!/bin/bash
# QW-F16PROG3: SAFE_PHYS functional (paired vs legacy at LAG=2, 28 stimuli, mechanisms) on Verilator 5.050.
set -uo pipefail
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version > verilator.version
SRCS="src/rtl/qwen_dv/qfd_dv_typed_su_observer.sv src/rtl/qwen_dv/qfd_dv_typed_witness_control.sv src/rtl/test/qwen_dv/tb_qwen_typed_witness_control.sv"
B="--binary --timing -j 8 -Wno-fatal --top-module tb_qwen_typed_witness_control"
"$V" $B -GEN=1 -GSAFE=1 -GSELECT=1 -GPHYS=1 -GPAIR=1 -Mdir objP1 $SRCS > buildP1.log 2>&1 || { echo BUILD_FAIL P1; exit 3; }
"$V" $B -GEN=1 -GSAFE=1 -GSELECT=1 -GPHYS=1 -GPAIR=0 -Mdir objP0 $SRCS > buildP0.log 2>&1 || { echo BUILD_FAIL P0; exit 3; }
"$V" $B -GEN=0 -GSAFE=1 -GSELECT=1 -GPHYS=1 -GPAIR=0 -Mdir objL $SRCS > buildL.log 2>&1 || { echo BUILD_FAIL L; exit 3; }
"$V" $B -GEN=1 -GSAFE=1 -GSELECT=1 -GPHYS=0 -GPAIR=1 -Mdir objS1 $SRCS > buildS1.log 2>&1 || { echo BUILD_FAIL S1; exit 3; }
ok=1; mkdir -p paired
for stim in vec/stim_*.txt; do
 n=$(basename "$stim" .txt)
 objP1/Vtb_qwen_typed_witness_control +STIM="$stim" > paired/$n.log 2>&1
 if grep -q F16_STRUCTURAL_EDGE_MISMATCH paired/$n.log || ! grep -q TWC_SUMMARY paired/$n.log; then echo "PAIR $n MISMATCH"; ok=0; continue; fi
 if [ "$n" = stim_nominal ]; then
  grep -q TWC_RESULT_CLEAN paired/$n.log && grep -q 'completions=65 retired=5 starts=5' paired/$n.log && grep -q ready_seen=1 paired/$n.log && ! grep -q ORDER_ERROR paired/$n.log && echo "PAIR $n NOMINAL_PASS" || { echo "PAIR $n NOMINAL_FAIL"; ok=0; }
 else
  grep -q TWC_RESULT_FAULT paired/$n.log && echo "PAIR $n FAIL_AS_EXPECTED $(grep -o 'first_fault=[0-9-]*' paired/$n.log)" || { echo "PAIR $n ESCAPED"; ok=0; }
 fi
 # baseline SAFE_SELECT (no PHYS) still pairs on every edge
 objS1/Vtb_qwen_typed_witness_control +STIM="$stim" > paired/S_$n.log 2>&1
 grep -q TWC_SUMMARY paired/S_$n.log && ! grep -q F16_STRUCTURAL_EDGE_MISMATCH paired/S_$n.log || { echo "SELECTBASE $n MISMATCH"; ok=0; }
done | tee paired.log
grep -qE 'MISMATCH|ESCAPED|NOMINAL_FAIL' paired.log && ok=0
objL/Vtb_qwen_typed_witness_control +STIM=vec/stim_nominal.txt > legacy.log 2>&1
grep -q 'en=0 fault=0 obs_fault=0 ready_seen=0 ready_end=0 completions=0' legacy.log && echo LEGACY_EN0_PASS || { echo LEGACY_EN0_FAIL; ok=0; }
objP1/Vtb_qwen_typed_witness_control +STIM=vec/stim_nominal.txt +OVERFLOW > overflow.log 2>&1
grep -q F16_ACTUAL_CACHE_OVERFLOW_PASS overflow.log && ! grep -q MISMATCH overflow.log && echo OVERFLOW_PASS || { echo OVERFLOW_FAIL; ok=0; }
objP1/Vtb_qwen_typed_witness_control +STIM=vec/stim_nominal.txt +CHECK_SECTORS > coverage.log 2>&1
grep -q 'F16_SELECT_COVERAGE groups=1fff banks=ff users=f' coverage.log && ! grep -qE 'FAIL|MISMATCH' coverage.log && echo COVERAGE_PASS || { echo COVERAGE_FAIL; ok=0; }
mkdir -p mech
for m in SKEW DUE_CORRUPT SELECT_WRONG SELECT_CLEAR BANK_WRONG TPL_WRONG; do
 objP0/Vtb_qwen_typed_witness_control +STIM=vec/stim_nominal.txt +$m > mech/$m.log 2>&1
 grep -q 'F16_' mech/$m.log && grep -q TWC_RESULT_FAULT mech/$m.log && echo "MECH $m FAIL_AS_EXPECTED" || { echo "MECH $m ESCAPED"; ok=0; }
done | tee mech.log
grep -q ESCAPED mech.log && ok=0
objP0/Vtb_qwen_typed_witness_control +STIM=vec/stim_nominal.txt +RESET_CLEAR > mech/RESET_CLEAR.log 2>&1
grep -q F16_PENDING_LANDED_CLEAR_PASS mech/RESET_CLEAR.log && echo RESET_LANDED_CLEAR_PASS || { echo RESET_LANDED_CLEAR_FAIL; ok=0; }
objP0/Vtb_qwen_typed_witness_control +STIM=vec/stim_nominal.txt +RESET_CLEAR +RLEAF_STUCK > mech/RLEAF_STUCK.log 2>&1
grep -q F16_RESET_OWNERSHIP_NOT_CLEAR mech/RLEAF_STUCK.log && echo "MECH RLEAF_STUCK FAIL_AS_EXPECTED" || { echo "MECH RLEAF_STUCK ESCAPED"; ok=0; }
if [ $ok = 1 ]; then echo F16_SAFE_PHYS_FUNCTIONAL_PASS; else echo F16_SAFE_PHYS_FUNCTIONAL_FAIL; exit 1; fi
