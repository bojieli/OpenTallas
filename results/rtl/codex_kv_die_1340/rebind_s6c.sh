#!/bin/bash
set -euo pipefail
source /home/ubuntu/ot-scratch/claude/qwen-kvsys/kvs14r-c6520b2ee-dsg6f/kv_flags.env
python3 rebind_s6c.py > rebind.log 2>&1
