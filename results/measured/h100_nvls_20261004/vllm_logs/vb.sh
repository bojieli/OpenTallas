. ~/venv2/bin/activate
for tp in 1 2 4 8; do
 for q in auto fp8; do
  echo "=== tp=$tp quant=$q" >> ~/vb.log
  vllm bench latency --model ~/qwen3-8b --input-len 128 --output-len 512 --batch-size 1 -tp $tp $( [ $q = fp8 ] && echo --quantization fp8 ) --num-iters-warmup 2 --num-iters 5 --max-model-len 4096 > ~/vb_${tp}_${q}.full 2>&1
  grep -E "Avg latency|percentile" ~/vb_${tp}_${q}.full >> ~/vb.log || tail -3 ~/vb_${tp}_${q}.full >> ~/vb.log
 done
done
echo VBDONE >> ~/vb.log
