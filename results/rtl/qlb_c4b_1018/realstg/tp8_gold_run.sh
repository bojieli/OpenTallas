#!/bin/bash
# usage: run.sh OUT POSITIONS PCDUMP
cd /srv/opentallas-scratch/claude/tokpass-qwen-1018/fx/realmem_tp8/stage/tools
export QWEN_O4_AR_WORDS=256 QWEN_O4_TP=8 QWEN_O4_GROUPS=3072 HDC_SU_WIDTH=64 HDC_KV_FMT=fp8 OT_GOLD_ROOT=/srv/opentallas-scratch/claude/tokpass-qwen-1018/fx/realmem_tp8/stage OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8
exec python3 qwen_layerbench/qwen_tp8_layer_gold.py --layer-dirs '/srv/opentallas-scratch/claude/tokpass-qwen-1018/fx/realmem_tp8/stage/img/L{layer}/die{die}' --layers 2 \
  --tokens /srv/opentallas-scratch/claude/tokpass-qwen-1018/fx/realmem_tp8/../inputs/prompt_tokens_8192.txt --embedding-npz /srv/opentallas-scratch/claude/tokpass-qwen-1018/fx/realmem_tp8/../inputs/prompt_embedding.npz \
  --positions "$2" --pc-dump "$3" --check-preload '/srv/opentallas-scratch/claude/tokpass-qwen-1018/fx/realmem_tp8/../realmem/P{p}/x_preload.hex' --out "$1"
