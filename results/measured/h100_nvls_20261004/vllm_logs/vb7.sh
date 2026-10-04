
. ~/venv/bin/activate
export LD_LIBRARY_PATH=/usr/local/cuda-13.0/compat:$LD_LIBRARY_PATH; export PATH=/usr/local/cuda-13.0/bin:$PATH; export CUDA_HOME=/usr/local/cuda-13.0; export VLLM_USE_FLASHINFER_SAMPLER=0
b() { tag=$1; shift; echo "=== $tag" >> ~/vb7.log; vllm bench latency "$@" --batch-size 1 --max-num-seqs 16 --num-iters-warmup 1 --num-iters 3 > ~/vb7_$tag.full 2>&1; grep -E "Avg latency" ~/vb7_$tag.full >> ~/vb7.log || tail -4 ~/vb7_$tag.full >> ~/vb7.log; }
Q=/ephemeral/qwen38-27b
for tp in 1 8; do for ctx in "128 4096" "8192 9000"; do set -- $ctx
  b q27_tp${tp}_fp8_in$1_out1 --model $Q -tp $tp --quantization fp8 --input-len $1 --output-len 1 --max-model-len $2
  b q27_tp${tp}_fp8_in$1_out257 --model $Q -tp $tp --quantization fp8 --input-len $1 --output-len 257 --max-model-len $2
done; done
while ! grep -q DSDONE /ephemeral/dl.log 2>/dev/null; do sleep 30; done
D=/ephemeral/dsv41flash
for ctx in "128 4096" "32768 33000"; do set -- $ctx
  b ds_tp8_in$1_out1 --model $D -tp 8 --trust-remote-code --input-len $1 --output-len 1 --max-model-len $2
  b ds_tp8_in$1_out129 --model $D -tp 8 --trust-remote-code --input-len $1 --output-len 129 --max-model-len $2
done
echo VB7DONE >> ~/vb7.log
