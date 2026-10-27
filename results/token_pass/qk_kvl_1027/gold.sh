#!/bin/bash
# TOK-QK-KVL 10-27: per-layer KV-die attention operands (36 layers, P8191) from the history-seeded TP4 ISA golden.
set -eu
K=/srv/opentallas-scratch2/claude/tok-qk-kvl
cd $K
export PYTHONPATH=$K/pylib QWEN_O4_TP=4 QWEN_O4_GROUPS=6144 HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8 OMP_NUM_THREADS=32 PYTHONDONTWRITEBYTECODE=1
PY=/usr/bin/python3.14
echo HIST $(date -Is)
[ -s hist/manifest.json ] || $PY kvl_history.py --out hist --pos 8191 --layers 36 --tp 4
echo GOLD $(date -Is)
$PY src/tools/qwen_layerbench/kv_attn_gold.py --src src --out gold -- --run --device cpu --prep-dir fx/tp4 --layers 36   --tokens fx/inputs/prompt_tokens_8192.txt --positions 8191 --embedding-npz fx/inputs/prompt_embedding.npz   --kv-history hist --out gold/oracle > gold.log 2>&1
echo VEC $(date -Is)
HDC_SU_WIDTH=8 $PY kv_attn_vectors.py --gold gold --fx declared --history-manifest hist/manifest.json --ksrc src   --layers $(seq -s, 0 35) --vec vec --out vec_record.json > vec.log 2>&1
for m in shift pos; do HDC_SU_WIDTH=8 $PY kv_attn_vectors.py --gold gold --fx declared --history-manifest hist/manifest.json --ksrc src   --layers 0,17,35 --vec vec_mut_$m --mutant $m --out vec_mut_$m.json > vec_mut_$m.log 2>&1 || true; done
echo DONE $(date -Is)
