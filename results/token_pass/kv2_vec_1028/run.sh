#!/bin/bash
# TOK-KV-2 10-28: rebuild the TOK-QK-KVL real-prefill KV-die vectors (36 layers x 8 TP8 KV heads, P8191) on epyc2 (idle; intel1 load ~100), vec copied to intel1 after.
# Inputs: src = git archive origin/main (SOURCE_COMMIT), fx/inputs + fx/tp4 = exactness fixtures qwen_p8191 (sha-checked vs
# tools/exactness/fixtures_archive_1018/qwen_p8191.sha256), hf = released Qwen/Qwen3-8B HF snapshot.
# Steps: [prefill hist_real || pf16 ISA golden prefill rows 0..15] -> hist check -> history-seeded ISA gold P8191 -> vec.
set -u
W=/srv/opentallas-scratch2/claude/tok-kv-2-1028
cd $W
log() { echo "$1 $(date -Is)" >> run.log; }
fail() { log "FAILED $1"; mkdir -p vec; echo "$1 (see $W/run.log and $W/$1.log)" > vec/.failed_reason; touch vec/.failed; exit 1; }
D() { local mem=$1 cpus=$2 name=$3; shift 3; docker run --rm --name $name -m ${mem}g --cpus $cpus -u $(id -u):$(id -g) -e HOME=/tmp \
  -e PYTHONPATH=/w/pylib:/w/src/tools:/w/src/tools/qwen_layerbench -e QWEN_O4_TP=4 -e QWEN_O4_GROUPS=6144 -e HDC_KV_FMT=fp8 \
  -e OMP_NUM_THREADS=$cpus -e PYTHONDONTWRITEBYTECODE=1 -v $W:/w -w /w python:3.14-slim "$@"; }
log START
rm -rf vec; [ "$(cat prefill.rc 2>/dev/null)" = 0 ] && grep -q 'KVL_PREFILL_HIST done' prefill.log || rm -rf hist_real; mkdir -p kvlsrc && cp src/tools/qwen_layerbench/kvl_prefill_hist.py src/tools/qwen3_deployment_quality.py kvlsrc/   # the tool hashes its sibling (flat dir, as 10-27 kvlsrc)
[ -s hist_real/manifest.json ] || ( D 220 96 tokkv2-prefill python3 kvlsrc/kvl_prefill_hist.py --snapshot hf --tokens fx/inputs/prompt_tokens_8192.txt \
    --pos 8191 --out hist_real --prep-dir fx/tp4 > prefill.log 2>&1; echo $? > prefill.rc ) &
[ "$(cat pf16.rc 2>/dev/null)" = 0 ] || ( D 96 24 tokkv2-pf16 sh -c 'HDC_SU_WIDTH=1024 python3 src/tools/qwen_hbmacc_position_oracle_gpu.py --run --device cpu --prep-dir fx/tp4 \
    --layers 36 --tokens fx/inputs/prompt_tokens_8192.txt --positions 16 --embedding-npz fx/inputs/prompt_embedding.npz --out pf16' \
    > pf16.log 2>&1; echo $? > pf16.rc ) &
wait
log "PREFILL rc=$(cat prefill.rc) PF16 rc=$(cat pf16.rc)"
grep -q 'KVL_PREFILL_HIST done' prefill.log || fail prefill
grep -q '"prep_check_all_equal": true' hist_real/manifest.json || log "WARN prep_check_all_equal false: HF-side W8 RTN-MSE codes != pinned TP4 prep codes (recorded caveat; the 10-27 chain did not gate on it; the P8191 decode uses the prep codes)"
log CHECK
if [ "$(cat pf16.rc)" = 0 ]; then
  D 64 16 tokkv2-check python3 src/tools/qwen_layerbench/kvl_hist_check.py --hist hist_real --kvpre pf16/P16/kv_pre --rows 16 --out hist_check.json > check.log 2>&1 || fail check
else log "CHECK skipped (pf16 failed)"; fi
log GOLD
D 160 96 tokkv2-gold sh -c 'HDC_SU_WIDTH=1024 python3 src/tools/qwen_layerbench/kv_attn_gold.py --src src --out gold_real -- --run --device cpu \
  --prep-dir fx/tp4 --layers 36 --tokens fx/inputs/prompt_tokens_8192.txt --positions 8191 --embedding-npz fx/inputs/prompt_embedding.npz \
  --kv-history hist_real --out gold_real/oracle' > gold.log 2>&1 || fail gold
log VEC
D 96 16 tokkv2-vec sh -c "HDC_SU_WIDTH=8 python3 src/tools/qwen_layerbench/kv_attn_vectors.py --gold gold_real --fx declared \
  --history-manifest hist_real/manifest.json --ksrc src --layers $(seq -s, 0 35) --vec vec --out vec_record.json" > vec.log 2>&1 || fail vec
grep -q 'KVATTN_VECTORS PASS' vec.log || fail vec_verdict
log DONE_VEC
