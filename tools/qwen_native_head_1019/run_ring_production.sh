#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
python3 tools/qwen_native_head_1019/run_production.py a c f g k q m o n --work out/positive --vflags "+define+OT_QFD_DV_SAFE_STORAGE -GSU_LT=1 -GHD_W130=1 -GMU_NU=4 -GFACE=1"
