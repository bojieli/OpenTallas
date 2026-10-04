#!/bin/bash
cd /home/ubuntu/wt-dspark-sys
export QWEN_O4_GROUPS=6144 QWEN_O4_TP=4 HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8
for i in $(seq 1 20); do
/usr/bin/time -v python3 tools/qwen_rom_dspark_drafter_layer_golden.py --images /tmp/claude-1000/-home-ubuntu-OpenTallas/98bed5ce-ef4e-4140-93b4-b898444c4b99/scratchpad/d8k/images --layer 0 --x /home/ubuntu/qwen-dspark-oracle-run/ref/realmem_gold/prompt/P255/x_preload.hex,/home/ubuntu/qwen-dspark-oracle-run/ref/realmem_gold/prompt/P255/L00_die0_x.hex,/home/ubuntu/qwen-dspark-oracle-run/ref/realmem_gold/prompt/P255/L01_die0_x.hex --out /tmp/claude-1000/-home-ubuntu-OpenTallas/98bed5ce-ef4e-4140-93b4-b898444c4b99/scratchpad/d8k/dgold8k --remote-root /srv/opentallas-scratch/claude/qwen-dspark-system/ctx8k/drafter > /tmp/claude-1000/-home-ubuntu-OpenTallas/98bed5ce-ef4e-4140-93b4-b898444c4b99/scratchpad/d8k/dgold.log 2>&1
rc=$?; [ $rc = 75 ] || break; sleep 3; done; echo $rc > /tmp/claude-1000/-home-ubuntu-OpenTallas/98bed5ce-ef4e-4140-93b4-b898444c4b99/scratchpad/d8k/dgold.rc
