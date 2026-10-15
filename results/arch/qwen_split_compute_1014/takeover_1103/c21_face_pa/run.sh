#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch/codex/qwen-c21-face-pin-1103/attempt2/src
export OT_TP8_SPLIT=compute OT_SPLIT_PMHS=0 OT_SPLIT_TREE_INTERLEAVE=0 OT_SPLIT_TREE_HOSTS=dp OT_SPLIT_STACK=seamw OT_SPLIT_REPACK=1 OT_SPLIT_BAND1_FLIP=1 OT_RELAY_SKIP=1 OT_RELAY_GATE=warn OT_RESET_GATE=warn OT_PIN_ALIGN_GATE=warn
python3 tools/qwen_tp8/relay_data_run.py ../out --case > ../build.log 2>&1
python3 tools/qwen_tp8/bind_real.py --case ../out/case --repo . --out ../bind.json > ../bind.log 2>&1
bash tools/qwen_kv_die/chain/run_case.sh ../out/case run.tcl run.log 16 16
