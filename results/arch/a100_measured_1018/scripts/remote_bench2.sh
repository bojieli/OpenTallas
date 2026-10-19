#!/bin/bash
# A100-BENCH2 10-19: v2 of remote_bench.sh. usage: remote_bench2.sh <tag> <model> <kv_dtype> [all|dec]
# adds a pure-decode sweep (dec*): num_prompts = concurrency, all requests start together, per-token detail saved,
# so the window after the last prefill measures decode alone at batch C.
set -u
TAG=$1; MODEL=$2; KV=$3; MODE=${4:-all}
OUT=/root/out/$TAG; mkdir -p $OUT
PORT=8000; MAXLEN=9216; LONG_REQ=8704; SHORT_REQ=1024
nvidia-smi -q > $OUT/nvidia-smi-q.txt 2>&1
python3 -c 'import vllm,torch;print("vllm",vllm.__version__,"torch",torch.__version__,"cuda",torch.version.cuda)' > $OUT/versions.txt 2>&1
vllm serve $MODEL --port $PORT --max-model-len $MAXLEN --gpu-memory-utilization 0.92 \
    --max-num-seqs 512 --kv-cache-dtype $KV --no-enable-prefix-caching --seed 0 > $OUT/server_$MODE.log 2>&1 &
SPID=$!
for i in $(seq 1 180); do
  curl -sf localhost:$PORT/v1/models >/dev/null && break
  kill -0 $SPID 2>/dev/null || { echo "SERVER DIED $TAG"; tail -30 $OUT/server_$MODE.log; exit 2; }
  sleep 5
done
curl -sf localhost:$PORT/v1/models >/dev/null || { echo "SERVER TIMEOUT"; kill $SPID; exit 3; }
KVTOK=$(grep -oE 'GPU KV cache size: [0-9,]+ tokens' $OUT/server_$MODE.log | tail -1 | grep -oE '[0-9,]+' | tr -d ,)
MAXL=$(( KVTOK / LONG_REQ )); MAXS=$(( KVTOK / SHORT_REQ )); [ $MAXS -gt 512 ] && MAXS=512
echo "kv_tokens=$KVTOK max_fit_long=$MAXL max_fit_short=$MAXS" | tee $OUT/kv.txt
nvidia-smi --query-gpu=timestamp,memory.used,memory.total,power.draw,clocks.sm,clocks.mem,utilization.gpu,temperature.gpu \
  --format=csv,noheader,nounits -l 1 > $OUT/smi_$MODE.csv 2>/dev/null &
SMI=$!
run() {  # ctx_tag in out conc nprompts [extra]
  local CT=$1 IN=$2 OUTL=$3 C=$4 N=$5; shift 5
  local T0=$(date +%s.%N)
  timeout 1500 vllm bench serve --backend vllm --model $MODEL --port $PORT --endpoint /v1/completions \
    --dataset-name random --random-input-len $IN --random-output-len $OUTL --random-range-ratio 0 \
    --num-prompts $N --max-concurrency $C --ignore-eos --seed 0 --temperature 0 \
    --percentile-metrics ttft,tpot,itl,e2el --metric-percentiles 50,90,99 "$@" \
    --save-result --result-dir $OUT --result-filename ${CT}_c${C}.json > $OUT/${CT}_c${C}.log 2>&1
  local RC=$?
  echo "$CT $C $T0 $(date +%s.%N) $RC" >> $OUT/windows.txt
  grep -E 'Output token throughput|Median TPOT|Median ITL' $OUT/${CT}_c${C}.log | tr -s ' ' | paste -sd' ' | sed "s/^/[$TAG $CT c=$C rc=$RC] /"
}
upto(){ local M=$1; shift; for c in "$@" $M; do [ $c -le $M ] && echo $c; done | sort -un; }
vllm bench serve --backend vllm --model $MODEL --port $PORT --dataset-name random --random-input-len 512 \
  --random-output-len 32 --num-prompts 4 --max-concurrency 4 --ignore-eos > $OUT/warmup_$MODE.log 2>&1
# pure decode: 7,680-token prompt + 1,024 decode = context 7,680..8,704 (mean 8,192); short: 256 + 512
for C in $(upto $MAXL 1 8 32 64 96 128); do run declong 7680 1024 $C $C --save-detailed; done
for C in $(upto $MAXS 1 64 128 256 384); do run decshort 256 512 $C $C --save-detailed; done
if [ $MODE = all ]; then
  for C in $(upto $MAXL 1 2 4 8 16 32 64); do run long 8192 512 $C $(( C*2 < 8 ? 8 : C*2 )); done
  for C in $(upto $MAXS 1 2 4 8 16 32 64 128 256); do run short 512 512 $C $(( C*2 < 8 ? 8 : C*2 )); done
fi
kill $SMI; kill $SPID; wait $SPID 2>/dev/null; sleep 5
echo "DONE $TAG $MODE"
