#!/bin/bash
set -euo pipefail
D=results/arch/codex_f16bind_2140/issue/integrated
mkdir -p packed_source_run/vec packed_source_run/logs
verilator --version > packed_source_run/verilator.version
python3 -I "$D/typed_witness_control_vectors.py" --pw "$D/model_pw.hex" --out packed_source_run/vec
verilator --binary --timing -j 2 -Wno-fatal --top-module tb_qwen_typed_witness_control -GEN=1 -GSAFE=1 -GSELECT=1 -GPHYS=1 -GFACE=1 -Mdir "$PWD/packed_source_run/obj" "$D/qfd_dv_typed_su_observer.sv" "$D/qfd_dv_typed_witness_control.sv" "$D/qfd_tt_ctlm_dv_wtn.sv" rtl/qwen_dv/f16/qfd_dv_f16_issue_tap.sv "$D/postpin_cmd_cut.sv" "$D/tb_packed_face.sv" > packed_source_run/logs/build.log 2>&1
X=packed_source_run/obj/Vtb_qwen_typed_witness_control
"$X" +STIM=packed_source_run/vec/stim_nominal.txt > packed_source_run/logs/nominal.log 2>&1
grep -q F16_FACE_EXACT_PASS packed_source_run/logs/nominal.log
grep -q TWC_RESULT_CLEAN packed_source_run/logs/nominal.log
"$X" +STIM=packed_source_run/vec/stim_nominal.txt +BEGIN > packed_source_run/logs/begin.log 2>&1
grep -q F16_FACE_BEGIN_WITHDRAW_PASS packed_source_run/logs/begin.log
for case in TAP_WRONG_PC TAP_WRONG_USER TAP_INSTALLED_EPOCH;do
 if "$X" +STIM=packed_source_run/vec/stim_nominal.txt +$case > packed_source_run/logs/$case.log 2>&1;then echo "MUTANT SURVIVED $case";exit 1;fi
 grep -q TAP_CAUSAL_REJECT packed_source_run/logs/$case.log
done
cat packed_source_run/logs/nominal.log
cat packed_source_run/logs/begin.log
echo PASS F16_PACKED_COMMAND_DISPATCH_TO_WITNESS plus3causal_rejects
