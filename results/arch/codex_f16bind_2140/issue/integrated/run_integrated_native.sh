#!/bin/bash
set -euo pipefail
D=results/arch/codex_f16bind_2140/issue/integrated
mkdir -p integrated_native_run/vec integrated_native_run/logs
verilator --version > integrated_native_run/verilator.version
python3 -I "$D/typed_witness_control_vectors.py" --pw "$D/model_pw.hex" --out integrated_native_run/vec
verilator --binary --timing -j 2 -Wno-fatal --top-module tb_qwen_typed_witness_control -GEN=1 -GSAFE=1 -GSELECT=1 -GPHYS=1 -GFACE=1 -Mdir "$PWD/integrated_native_run/obj" "$D/qfd_dv_typed_su_observer.sv" "$D/qfd_dv_typed_witness_control.sv" "$D/actual_wtn_native32.sv" "$D/actual_wtn_helpers.sv" rtl/qwen_dv/f16/qfd_dv_f16_issue_tap.sv "$D/postpin_cut.sv" "$D/tb_actual_nativeface.sv" > integrated_native_run/logs/build.log 2>&1
X=integrated_native_run/obj/Vtb_qwen_typed_witness_control
"$X" +STIM=integrated_native_run/vec/stim_nominal.txt > integrated_native_run/logs/nominal.log 2>&1
grep -q F16_FACE_EXACT_PASS integrated_native_run/logs/nominal.log
grep -q TWC_RESULT_CLEAN integrated_native_run/logs/nominal.log
"$X" +STIM=integrated_native_run/vec/stim_nominal.txt +BEGIN > integrated_native_run/logs/begin.log 2>&1
grep -q F16_FACE_BEGIN_WITHDRAW_PASS integrated_native_run/logs/begin.log
for case in TAP_WRONG_PC TAP_WRONG_USER TAP_INSTALLED_EPOCH;do
 if "$X" +STIM=integrated_native_run/vec/stim_nominal.txt +$case > integrated_native_run/logs/$case.log 2>&1;then echo "MUTANT SURVIVED $case";exit 1;fi
 grep -q TAP_CAUSAL_REJECT integrated_native_run/logs/$case.log
done
cat integrated_native_run/logs/nominal.log
cat integrated_native_run/logs/begin.log
echo PASS F16_ACTUAL_DISPATCH_TO_NATIVE_WITNESS plus3causal_rejects
