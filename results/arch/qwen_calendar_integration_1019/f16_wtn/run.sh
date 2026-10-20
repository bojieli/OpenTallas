#!/bin/bash
# QW-F16PROG4: CTLM face qfd_tt_ctlm_dv_wtn (SAFE_PHYS witness control) vs the standalone SAFE_PHYS controller on every
# edge of all 28 WTN1 stimuli (vec/ from tools/qwen_layerbench/typed_witness_control_vectors.py, as QW-F16PROG3),
# BEGIN withdrawal, face mutants; plus the CTLM lpf parent elaborated with F16WTN=1 PRIVATE_CALR=1 (Verilator 5.050 lint).
set -uo pipefail
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version > verilator.version
S=src
SRCS="$S/rtl/qwen_dv/qfd_dv_typed_su_observer.sv $S/rtl/qwen_dv/qfd_dv_typed_witness_control.sv $S/rtl/qwen_dv/qfd_tt_ctlm_dv_wtn.sv $S/rtl/test/qwen_dv/tb_qwen_typed_witness_control.sv"
sha256sum $SRCS vec/*.txt > sources.sha256
B="--binary --timing -j 8 -Wno-fatal --top-module tb_qwen_typed_witness_control -GEN=1 -GSAFE=1 -GSELECT=1 -GPHYS=1 -GFACE=1"
mkdir -p logs witness
for m in 0 1 2 3; do ( "$V" $B -GFMUT=$m -Mdir obj$m $SRCS > logs/build$m.log 2>&1 || touch logs/build$m.fail ) & done
wait
ls logs/*.fail 2>/dev/null && { echo F16_FACE_BUILD_FAIL; exit 3; }
ok=1
for stim in vec/stim_*.txt; do
  n=$(basename "$stim" .txt)
  obj0/Vtb_qwen_typed_witness_control +STIM="$stim" > logs/$n.log 2>&1
  if grep -q F16_FACE_EXACT_PASS logs/$n.log; then echo "FACE $n EXACT $(grep -o 'TWC_RESULT_[A-Z]*' logs/$n.log)"; else echo "FACE $n MISMATCH"; ok=0; fi
done | tee face.log
grep -q MISMATCH face.log && ok=0
grep -q 'FACE stim_nominal EXACT TWC_RESULT_CLEAN' face.log || { echo NOMINAL_NOT_CLEAN; ok=0; }
obj0/Vtb_qwen_typed_witness_control +STIM=vec/stim_nominal.txt +BEGIN > logs/begin.log 2>&1
grep -q F16_FACE_BEGIN_WITHDRAW_PASS logs/begin.log && echo BEGIN_WITHDRAW_PASS || { echo BEGIN_WITHDRAW_FAIL; ok=0; }
# mutants (fail regex): 1 +BEGIN -> F16_FACE_BEGIN_NOT_WITHDRAWN; 2, 3 nominal -> F16_FACE_EDGE_MISMATCH
obj1/Vtb_qwen_typed_witness_control +STIM=vec/stim_nominal.txt +BEGIN > witness/fmut1.log 2>&1
grep -q F16_FACE_BEGIN_NOT_WITHDRAWN witness/fmut1.log && echo "FMUT 1 FAIL_AS_EXPECTED" || { echo "FMUT 1 ESCAPED"; ok=0; }
for m in 2 3; do
  obj$m/Vtb_qwen_typed_witness_control +STIM=vec/stim_nominal.txt > witness/fmut$m.log 2>&1
  grep -q F16_FACE_EDGE_MISMATCH witness/fmut$m.log && echo "FMUT $m FAIL_AS_EXPECTED" || { echo "FMUT $m ESCAPED"; ok=0; }
done
# CTLM lpf parent with both options: elaboration / lint on the daemon Verilator (no ties: every new port is a parent port)
P="$S/rtl/qwen_dv"
"$V" --lint-only -Wno-fatal -Wno-WIDTH -Wno-UNUSED --top-module qfd_tt_ctlm_dv_lpf -GPRIVATE_CALR=1 -GF16WTN=1 -GXPF_TRANSPORT_EDGES=21 -GOPSEG=0 \
  \
  $(cat ctlm_files.txt) > logs/ctlm_lint.log 2>&1 && echo CTLM_F16_CALR_ELAB_PASS || { echo CTLM_F16_CALR_ELAB_FAIL; ok=0; }
"$V" --lint-only -Wno-fatal -Wno-WIDTH -Wno-UNUSED --top-module qfd_tt_ctlm_dv_lpf -GXPF_TRANSPORT_EDGES=21 \
  $(cat ctlm_files.txt) > logs/ctlm_lint_default.log 2>&1 && echo CTLM_DEFAULT_ELAB_PASS || { echo CTLM_DEFAULT_ELAB_FAIL; ok=0; }
[ $ok = 1 ] && echo F16_CTLM_FACE_PASS || { echo F16_CTLM_FACE_FAIL; exit 1; }
