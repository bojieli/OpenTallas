#!/bin/bash
# QW-CLUSTER3/HEAD 10-19: safe1 head, fleet bench on the daemon's Verilator 5.050.
#   m0: full production W10 (a c f g k q m o n) + numeric e        -> must PASS
#   mutants (numeric e, each must FAIL): TLS bank swap, TLS slot (read one word late), ring_on copy 1 (new copy mutant)
set -uo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --version
F="+define+OT_QFD_DV_SAFE_STORAGE -GSU_LT=1 -GHD_W130=1 -GMU_NU=4 -GFACE=1"
mkdir -p logs
python3 tools/qwen_native_head_1019/run_safe1_production.py e a c f g k q m o n --work out/positive --vflags "$F" 2>&1 | tee logs/m0.log
rc0=${PIPESTATUS[0]}; echo "m0 rc=$rc0"
python3 tools/qwen_native_head_1019/run_safe1_production.py e --work out/bank_mut --vflags "$F +define+OT_HEAD_B64_BANK_MUT" 2>&1 | tee logs/mut_bank.log; echo "mut_bank rc=${PIPESTATUS[0]}"
python3 tools/qwen_native_head_1019/run_safe1_production.py e --work out/slot_mut --vflags "$F +define+OT_TLS_MUT" 2>&1 | tee logs/mut_slot.log; echo "mut_slot rc=${PIPESTATUS[0]}"
python3 tools/qwen_native_head_1019/run_safe1_production.py e --work out/ron_mut --vflags "$F +define+OT_HS1_RON_MUT" 2>&1 | tee logs/mut_ron.log; echo "mut_ron rc=${PIPESTATUS[0]}"
exit $rc0
