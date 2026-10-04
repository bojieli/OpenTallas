#!/bin/bash
cd /home/ubuntu/claude-dspark8k/src
python3 tools/qwen_rom_rt_vprm_w12.py --workdir /home/ubuntu/claude-dspark8k/runs/k_L0 --build-dir /home/ubuntu/claude-dspark8k/bld_dbg --hbm-layers 3 --code-banks 1   --plan /home/ubuntu/claude-dspark8k/ctx8k/plans/L0/plan --expect /home/ubuntu/claude-dspark8k/ctx8k/plans/L0/expect.json --kv-dir /home/ubuntu/claude-dspark8k/ctx8k/plans/kv --result /home/ubuntu/claude-dspark8k/res/k_L0.json --threads 12 > /home/ubuntu/claude-dspark8k/runs/k_L0.out 2>&1
echo $? > /home/ubuntu/claude-dspark8k/runs/k_L0.rc
