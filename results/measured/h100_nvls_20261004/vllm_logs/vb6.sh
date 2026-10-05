while ! grep -q VB5DONE ~/vb5.log 2>/dev/null; do sleep 20; done
. ~/venv2/bin/activate
CC="{\"pass_config\":{\"enable_fi_allreduce_fusion\":true,\"enable_noop\":true}}"
for out in 1 513; do
  echo "=== tp8 fp8 allreduce-fusion in=128 out=$out" >> ~/vb6.log
  vllm bench latency --model ~/qwen3-8b --input-len 128 --output-len $out --batch-size 1 -tp 8 --quantization fp8 --compilation-config "$CC" --num-iters-warmup 2 --num-iters 5 --max-model-len 4096 > ~/vb6_fuse_$out.full 2>&1
  grep -E "Avg latency" ~/vb6_fuse_$out.full >> ~/vb6.log || tail -4 ~/vb6_fuse_$out.full >> ~/vb6.log
done
echo "=== profile tp8 fp8 decode" >> ~/vb6.log
rm -rf ~/prof && mkdir -p ~/prof
VLLM_TORCH_PROFILER_DIR=$HOME/prof vllm bench latency --model ~/qwen3-8b --input-len 128 --output-len 64 --batch-size 1 -tp 8 --quantization fp8 --num-iters-warmup 1 --num-iters 1 --profile --max-model-len 4096 > ~/vb6_prof.full 2>&1
ls ~/prof | head -3 >> ~/vb6.log
echo VB6DONE >> ~/vb6.log
