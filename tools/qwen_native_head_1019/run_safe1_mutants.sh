#!/bin/bash
# QW-CLUSTER3/HEAD 10-19: the three numeric-e mutants of run_safe1_bench.sh alone (each must FAIL: rc 1 + "bench2 (e) MUT=0: FAIL").
set -uo pipefail
export HS1_TOP="${HS1_TOP:-safe1}"; echo "HS1_TOP=$HS1_TOP"
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --version
F="+define+OT_QFD_DV_SAFE_STORAGE -GSU_LT=1 -GHD_W130=1 -GMU_NU=4 -GFACE=1"
mkdir -p logs
for m in "bank OT_HEAD_B64_BANK_MUT" "slot OT_TLS_MUT" "ron OT_HS1_RON_MUT"; do set -- $m
  python3 tools/qwen_native_head_1019/run_safe1_production.py e --work out/${1}_mut --vflags "$F +define+$2" > logs/mut_$1.log 2>&1
  echo "mut_$1 rc=$?" | tee -a logs/mut_$1.log
done
