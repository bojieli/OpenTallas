#!/bin/bash
cd /home/ubuntu/claude-dspark8k/src
python3 tools/qwen_rom_rt_vprm_w12.py --workdir /home/ubuntu/claude-dspark8k/runs/k_D0r --build-dir /home/ubuntu/claude-dspark8k/bld_dbg --hbm-layers 3 --code-banks 1   --plan /home/ubuntu/claude-dspark8k/drafter8k/dgold8k_real/plan --expect /home/ubuntu/claude-dspark8k/drafter8k/dgold8k_real/expect.json --kv-dir /home/ubuntu/claude-dspark8k/drafter8k/dgold8k_real/kv --result /home/ubuntu/claude-dspark8k/res/k_D0r.json --threads 12 > /home/ubuntu/claude-dspark8k/runs/k_D0r.out 2>&1
echo $? > /home/ubuntu/claude-dspark8k/runs/k_D0r.rc
