#!/bin/bash
# A100-BENCH 10-18: runs ON the rented A100. One vLLM server per config, then a `vllm bench serve` sweep.
# usage: remote_bench.sh <tag> <model> <kv_dtype>
set -u
TAG=$1; MODEL=$2; KV=$3
OUT=/root/out/$TAG; mkdir -p $OUT
PORT=8000
MAXLEN=9216            # 8,192 prompt + 512 output + margin
LONG_REQ=8704          # tokens a long request holds at its end
SHORT_REQ=1024
export VLLM_LOGGING_LEVEL=INFO

nvidia-smi -q > $OUT/nvidia-smi-q.txt 2>&1
python3 -c 'import vllm,torch;print("vllm",vllm.__version__,"torch",torch.__version__,"cuda",torch.version.cuda)' > $OUT/versions.txt 2>&1

vllm serve $MODEL --port $PORT --max-model-len $MAXLEN --gpu-memory-utilization 0.92 \
    --max-num-seqs 512 --kv-cache-dtype $KV --no-enable-prefix-caching --seed 0 \
    > $OUT/server.log 2>&1 &
SPID=$!
for i in $(seq 1 180); do
  curl -sf localhost:$PORT/v1/models >/dev/null && break
  kill -0 $SPID 2>/dev/null || { echo "SERVER DIED"; tail -50 $OUT/server.log; exit 2; }
  sleep 5
done
curl -sf localhost:$PORT/v1/models >/dev/null || { echo "SERVER TIMEOUT"; tail -50 $OUT/server.log; kill $SPID; exit 3; }
KVTOK=$(grep -oE 'GPU KV cache size: [0-9,]+ tokens' $OUT/server.log | tail -1 | grep -oE '[0-9,]+' | tr -d ,)
echo "kv_tokens=$KVTOK" | tee $OUT/kv.txt
MAXL=$(( KVTOK / LONG_REQ )); MAXS=$(( KVTOK / SHORT_REQ )); [ $MAXS -gt 512 ] && MAXS=512
echo "max_fit_long=$MAXL max_fit_short=$MAXS" | tee -a $OUT/kv.txt

# GPU sampler (1 s)
nvidia-smi --query-gpu=timestamp,memory.used,memory.total,power.draw,clocks.sm,clocks.mem,utilization.gpu,temperature.gpu \
  --format=csv,noheader,nounits -l 1 > $OUT/smi.csv 2>/dev/null &
SMI=$!

run() {  # ctx_tag in out conc
  local CT=$1 IN=$2 OUTL=$3 C=$4
  local N=$(( C * 2 )); [ $N -lt 8 ] && N=8
  local T0=$(date +%s.%N)
  timeout 1800 vllm bench serve --backend vllm --model $MODEL --port $PORT --endpoint /v1/completions \
    --dataset-name random --random-input-len $IN --random-output-len $OUTL --random-range-ratio 0 \
    --num-prompts $N --max-concurrency $C --ignore-eos --seed 0 \
    --percentile-metrics ttft,tpot,itl,e2el --metric-percentiles 50,90,99 \
    --save-result --result-dir $OUT --result-filename ${CT}_c${C}.json > $OUT/${CT}_c${C}.log 2>&1
  local RC=$?
  local T1=$(date +%s.%N)
  echo "$CT $C $T0 $T1 $RC" >> $OUT/windows.txt
  grep -E 'Output token throughput|Median TPOT|Median TTFT|Median ITL' $OUT/${CT}_c${C}.log | tr -s ' ' | paste -sd' ' | sed "s/^/[$TAG $CT c=$C rc=$RC] /"
}

# warm-up (CUDA graphs captured at start; this warms the bench path)
vllm bench serve --backend vllm --model $MODEL --port $PORT --dataset-name random --random-input-len 512 \
  --random-output-len 32 --num-prompts 4 --max-concurrency 4 --ignore-eos > $OUT/warmup.log 2>&1

for C in $(printf "%s\n" 1 2 4 8 16 32 64 128 $MAXL | sort -un); do run long 8192 512 $C; done
for C in $(printf "%s\n" 1 2 4 8 16 32 64 128 256 $MAXS | sort -un); do run short 512 512 $C; done

kill $SMI; kill $SPID; wait $SPID 2>/dev/null
sleep 5
echo "DONE $TAG"
