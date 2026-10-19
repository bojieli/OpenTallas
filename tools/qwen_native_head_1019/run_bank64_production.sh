#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --version
python3 tools/qwen_native_head_1019/run_production.py a c f g k q m o n --work out/positive --vflags "+define+OT_QFD_DV_SAFE_STORAGE -GSU_LT=1 -GHD_W130=1 -GMU_NU=4 -GFACE=1"
python3 tools/qwen_native_head_1019/run_production.py g --work out/bank_mut --vflags "+define+OT_QFD_DV_SAFE_STORAGE -GSU_LT=1 -GHD_W130=1 -GMU_NU=4 -GFACE=1 +define+OT_HEAD_B64_BANK_MUT" && exit 31
python3 tools/qwen_native_head_1019/run_production.py g --work out/slot_mut --vflags "+define+OT_QFD_DV_SAFE_STORAGE -GSU_LT=1 -GHD_W130=1 -GMU_NU=4 -GFACE=1 +define+OT_TLS_MUT" && exit 32
