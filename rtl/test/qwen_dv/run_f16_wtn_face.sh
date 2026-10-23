#!/bin/bash
# QW-F16PROG4/F16SUB bench: CTLM F16 witness face qfd_tt_ctlm_dv_wtn vs the standalone SAFE_PHYS WTN1 controller on every
# edge.  usage: run_f16_wtn_face.sh OUTDIR MODE   MODE = face (28 stimuli exact + BEGIN withdraw; pass line F16_WTN_FACE_PASS)
#   | fmut1 (no BEGIN withdraw -> F16_FACE_BEGIN_NOT_WITHDRAWN) | fmut2 (installed epoch as identity) | fmut3 (retire user
#   swap) (fmut2/3 -> F16_FACE_EDGE_MISMATCH).  Stimuli are generated here from the committed PW image.  Run from repo root;
#   uses `verilator` on PATH (the closure daemon pins 5.050).
set -uo pipefail
OUT=${1:?outdir}; MODE=${2:?mode}
R=$(pwd)
mkdir -p "$OUT/vec" "$OUT/logs"
verilator --version
python3 -I "$R/tools/qwen_layerbench/typed_witness_control_vectors.py" \
  --pw "$R/results/arch/qwen_calendar_integration_1019/witness/witness_template_packet/model_pw.hex" --out "$OUT/vec" || { echo F16_WTN_VEC_FAIL; exit 2; }
SRCS="$R/rtl/qwen_dv/qfd_dv_typed_su_observer.sv $R/rtl/qwen_dv/qfd_dv_typed_witness_control.sv $R/rtl/qwen_dv/qfd_tt_ctlm_dv_wtn.sv $R/rtl/test/qwen_dv/tb_qwen_typed_witness_control.sv"
case $MODE in face) m=0;; fmut1) m=1;; fmut2) m=2;; fmut3) m=3;; *) echo "bad mode $MODE"; exit 2;; esac
verilator --binary --timing -j 8 -Wno-fatal --top-module tb_qwen_typed_witness_control -GEN=1 -GSAFE=1 -GSELECT=1 -GPHYS=1 -GFACE=1 \
  -GFMUT=$m -Mdir "$OUT/obj" $SRCS > "$OUT/logs/build.log" 2>&1 || { tail -30 "$OUT/logs/build.log"; echo F16_WTN_BUILD_FAIL; exit 3; }
X="$OUT/obj/Vtb_qwen_typed_witness_control"
if [ $m = 1 ]; then "$X" +STIM="$OUT/vec/stim_nominal.txt" +BEGIN 2>&1; exit 1; fi
if [ $m -gt 1 ]; then "$X" +STIM="$OUT/vec/stim_nominal.txt" 2>&1; exit 1; fi
ok=1; n=0
for stim in "$OUT"/vec/stim_*.txt; do
  s=$(basename "$stim" .txt); n=$((n+1))
  "$X" +STIM="$stim" > "$OUT/logs/$s.log" 2>&1
  if grep -q F16_FACE_EXACT_PASS "$OUT/logs/$s.log"; then echo "FACE $s EXACT $(grep -o 'TWC_RESULT_[A-Z]*' "$OUT/logs/$s.log")"
  else echo "FACE $s MISMATCH"; tail -5 "$OUT/logs/$s.log"; ok=0; fi
done
[ $n = 28 ] || { echo "F16_WTN_STIM_COUNT $n != 28"; ok=0; }
grep -q 'F16_FACE_EXACT_PASS' "$OUT/logs/stim_nominal.log" && grep -q TWC_RESULT_CLEAN "$OUT/logs/stim_nominal.log" || { echo NOMINAL_NOT_CLEAN; ok=0; }
for s in "$OUT"/logs/stim_*.log; do case $s in *stim_nominal.log) ;; *) grep -q TWC_RESULT_FAULT "$s" || { echo "MUTANT_STIM_NOT_FAULT $s"; ok=0; };; esac; done
"$X" +STIM="$OUT/vec/stim_nominal.txt" +BEGIN > "$OUT/logs/begin.log" 2>&1
grep -q F16_FACE_BEGIN_WITHDRAW_PASS "$OUT/logs/begin.log" && echo BEGIN_WITHDRAW_PASS || { echo BEGIN_WITHDRAW_FAIL; ok=0; }
[ $ok = 1 ] && { echo F16_WTN_FACE_PASS; exit 0; } || { echo F16_WTN_FACE_FAIL; exit 1; }
