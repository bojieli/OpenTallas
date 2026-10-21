#!/bin/bash
set -euo pipefail
W=/home/ubuntu/ot-scratch/claude/qwen-kvsys/wt-kvs14r-283f5922a-dsg3c432
B=/home/ubuntu/ot-scratch/claude/codex-k-ctl-geo-1021
source /home/ubuntu/ot-scratch/claude/qwen-kvsys/kvs14r-283f5922a-dsg3c432/kv_flags.env
export PYTHONDONTWRITEBYTECODE=1
cd "$W"
python3 "$B/geo.py"
