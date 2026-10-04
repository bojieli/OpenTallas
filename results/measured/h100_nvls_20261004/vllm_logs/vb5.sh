while ! grep -q VB4DONE ~/vb4.log 2>/dev/null; do sleep 20; done
. ~/venv2/bin/activate
# verify-step proxy: decode step time with B sequences in flight (weight streaming shared), B = 1,2,4,6,8; prefill-only runs at the same B to subtract
for q in auto fp8; do for b in 6; do
  for out in 1 257; do
    echo "=== stepcost tp=1 quant=$q batch=$b in=128 out=$out" >> ~/vb5.log
    vllm bench latency --model ~/qwen3-8b --input-len 128 --output-len $out --batch-size $b -tp 1 $( [ $q = fp8 ] && echo --quantization fp8 ) --num-iters-warmup 2 --num-iters 5 --max-model-len 4096 > ~/vb5_${q}_${b}_${out}.full 2>&1
    grep -E "Avg latency" ~/vb5_${q}_${b}_${out}.full >> ~/vb5.log || tail -3 ~/vb5_${q}_${b}_${out}.full >> ~/vb5.log
  done; done; done
echo VB5DONE >> ~/vb5.log
