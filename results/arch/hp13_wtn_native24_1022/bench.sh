#!/bin/bash
set -eu
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
python3 -I typed_witness_control_vectors.py --pw model_pw.hex --out vec
$V --binary --timing -j 1 -Wno-fatal --top-module tb_qwen_typed_witness_control -GEN=1 -GSAFE=1 -GSELECT=1 -GPHYS=1 -GFACE=1 -Mdir obj qfd_dv_typed_su_observer.sv qfd_dv_typed_witness_control.sv qfd_tt_ctlm_dv_wtn_native32.sv wtn_native_helpers.sv tb_native.sv > build.log 2>&1
mkdir -p logs
for stim in vec/stim_*.txt; do
 n=$(basename "$stim" .txt)
 obj/Vtb_qwen_typed_witness_control +STIM="$stim" > "logs/$n.log" 2>&1
 grep -q F16_FACE_EXACT_PASS "logs/$n.log"
 echo "NATIVE EXACT $n"
done
obj/Vtb_qwen_typed_witness_control +STIM=vec/stim_nominal.txt +BEGIN > logs/begin.log 2>&1
grep -q F16_FACE_BEGIN_WITHDRAW_PASS logs/begin.log
echo WTN_NATIVE_LOCKSTEP_PASS
