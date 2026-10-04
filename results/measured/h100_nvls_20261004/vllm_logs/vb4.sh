while ! grep -q VB3DONE ~/vb3.log 2>/dev/null; do sleep 20; done
. ~/venv2/bin/activate
for cfg in "1 auto 128 4096" "1 fp8 128 4096" "8 auto 128 4096" "8 fp8 128 4096" "1 auto 8192 9000" "1 fp8 8192 9000" "8 fp8 8192 9000"; do set -- $cfg
  echo "=== prefill-only tp=$1 quant=$2 in=$3 out=1" >> ~/vb4.log
  vllm bench latency --model ~/qwen3-8b --input-len $3 --output-len 1 --batch-size 1 -tp $1 $( [ $2 = fp8 ] && echo --quantization fp8 ) --num-iters-warmup 2 --num-iters 5 --max-model-len $4 > ~/vb4_$1_$2_$3.full 2>&1
  grep -E "Avg latency" ~/vb4_$1_$2_$3.full >> ~/vb4.log || tail -3 ~/vb4_$1_$2_$3.full >> ~/vb4.log
done
echo VB4DONE >> ~/vb4.log
