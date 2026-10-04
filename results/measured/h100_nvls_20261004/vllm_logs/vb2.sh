#!/bin/sh
. ~/venv2/bin/activate
export HF_HUB_ENABLE_HF_TRANSFER=1
for cfg in "1 auto" "1 fp8" "8 fp8"; do set -- $cfg
  echo "=== ctx8k tp=$1 quant=$2" >> ~/vb2.log
  vllm bench latency --model ~/qwen3-8b --input-len 8192 --output-len 256 --batch-size 1 -tp $1 $( [ $2 = fp8 ] && echo --quantization fp8 ) --num-iters-warmup 1 --num-iters 3 --max-model-len 9000 > ~/vb2_$1_$2.full 2>&1
  grep -E "Avg latency" ~/vb2_$1_$2.full >> ~/vb2.log || tail -3 ~/vb2_$1_$2.full >> ~/vb2.log
done
hf download AngelSlim/Qwen3-8B_eagle3 --local-dir ~/eagle3 > ~/eagle_dl.log 2>&1 || echo DLFAIL >> ~/vb2.log
for n in 3 5; do
  echo "=== eagle3 tp=1 bf16 k=$n ctx128" >> ~/vb2.log
  vllm bench latency --model ~/qwen3-8b --input-len 128 --output-len 512 --batch-size 1 -tp 1 --speculative-config "{\"method\":\"eagle3\",\"model\":\"$HOME/eagle3\",\"num_speculative_tokens\":$n}" --num-iters-warmup 1 --num-iters 3 --max-model-len 4096 > ~/vb2_eagle_$n.full 2>&1
  grep -E "Avg latency" ~/vb2_eagle_$n.full >> ~/vb2.log || tail -3 ~/vb2_eagle_$n.full >> ~/vb2.log
done
echo VB2DONE >> ~/vb2.log
