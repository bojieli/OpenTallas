#!/bin/bash
# TOK-QK-KVL 10-27 (epyc2): after the real prefill history (hist_real) -> check vs the ISA golden's own prefill rows
# 0..15 (pf16) -> history-seeded ISA golden decode at P8191 -> 36-layer x 8-head KV-die vectors (vec_real) -> intel2.
set -u
KH=/srv/opentallas-scratch2/claude/tok-qk-kvh; K=/srv/opentallas-scratch2/claude/tok-qk-kvl
cd $KH
until docker ps -a --filter name=kvh-prefill --format '{{.Status}}' | grep -q Exited; do sleep 60; done
fail() { echo "FAILED $1 $(date -Is)" >> post.log; ssh -o ControlPath=none hub "mkdir -p $K/vec_real && touch $K/vec_real/.failed"; exit 1; }
grep -q 'KVL_PREFILL_HIST done' prefill.log || fail prefill
D="docker run --rm -m 160g --cpus 64 -u $(id -u):$(id -g) -e HOME=/tmp -e PYTHONPATH=/w/kvlsrc:/w/pylib:/w/src/tools -e QWEN_O4_TP=4 -e QWEN_O4_GROUPS=6144 -e HDC_KV_FMT=fp8 -e OMP_NUM_THREADS=64 -e PYTHONDONTWRITEBYTECODE=1 -v $KH:/w -w /w python:3.14-slim"
echo "CHECK $(date -Is)" >> post.log
$D python3 kvlsrc/kvl_hist_check.py --hist hist_real --kvpre pf16/P16/kv_pre --rows 16 --out hist_check.json >> post.log 2>&1 || fail check
echo "GOLD $(date -Is)" >> post.log
$D sh -c 'HDC_SU_WIDTH=1024 python3 src/tools/qwen_layerbench/kv_attn_gold.py --src src --out gold_real -- --run --device cpu --prep-dir fx/tp4 --layers 36 --tokens inputs/prompt_tokens_8192.txt --positions 8191 --embedding-npz inputs/prompt_embedding.npz --kv-history hist_real --out gold_real/oracle' > gold_real.log 2>&1 || fail gold
echo "VEC $(date -Is)" >> post.log
$D sh -c "HDC_SU_WIDTH=8 python3 kvlsrc/kv_attn_vectors.py --gold gold_real --fx declared --history-manifest hist_real/manifest.json --ksrc src --layers $(seq -s, 0 35) --vec vec_real --out vec_real_record.json" > vec_real.log 2>&1 || fail vec
rsync -a vec_real hist_real/manifest.json hist_check.json vec_real_record.json hub:$K/ || fail rsync
ssh -o ControlPath=none hub "mv $K/manifest.json $K/hist_real_manifest.json; touch $K/vec_real/.done"
echo "DONE $(date -Is)" >> post.log
