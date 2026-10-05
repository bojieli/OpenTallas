#!/bin/bash
# GPU ISA goldens (layer 0 only) for the 8K verify component: A = the prompt (positions 8187..8191),
# B = the prompt to 8187 then three rejected drafts at 8188..8190.
D=/tmp/claude-1000/-home-ubuntu-OpenTallas/98bed5ce-ef4e-4140-93b4-b898444c4b99/scratchpad/d8k
cd /home/ubuntu/wt-dspark-sys
export QWEN_O4_GROUPS=6144 QWEN_O4_TP=4 HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8
run() { for i in $(seq 1 20); do python3 tools/qwen_rom_position_oracle_gpu.py --run --prep-dir /home/ubuntu/realmem-ctx8k/prep --layers 1 --tokens $D/tokens_$1.txt --positions $2 --embedding-npz /home/ubuntu/qwen-dspark-oracle-run/ref/realmem_gold/prompt_embedding.npz --out $D/gold$1 > $D/gold$1.log 2>&1; rc=$?; [ $rc = 75 ] || break; sleep 3; done; echo $rc > $D/gold$1.rc; }
run A 8187,8188,8189,8190,8191 &
run B 8188,8189,8190 &
wait
