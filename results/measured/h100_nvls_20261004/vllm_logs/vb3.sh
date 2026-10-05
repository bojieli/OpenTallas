. ~/venv2/bin/activate
unset HF_HUB_ENABLE_HF_TRANSFER
hf download AngelSlim/Qwen3-8B_eagle3 --local-dir $HOME/eagle3 > ~/eagle_dl.log 2>&1 || huggingface-cli download AngelSlim/Qwen3-8B_eagle3 --local-dir $HOME/eagle3 >> ~/eagle_dl.log 2>&1
ls $HOME/eagle3 >> ~/vb3.log 2>&1
for n in 3 5; do
  echo "=== eagle3 tp=1 bf16 k=$n ctx128" >> ~/vb3.log
  vllm bench latency --model $HOME/qwen3-8b --input-len 128 --output-len 512 --batch-size 1 -tp 1 --speculative-config "{\"method\":\"eagle3\",\"model\":\"$HOME/eagle3\",\"num_speculative_tokens\":$n}" --num-iters-warmup 1 --num-iters 3 --max-model-len 4096 > ~/vb3_$n.full 2>&1
  grep -E "Avg latency" ~/vb3_$n.full >> ~/vb3.log || tail -4 ~/vb3_$n.full >> ~/vb3.log
done
echo VB3DONE >> ~/vb3.log
