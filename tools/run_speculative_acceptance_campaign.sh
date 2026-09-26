#!/bin/bash
# Sequential GPU campaign behind results/speculative/acceptance_tau.json (run 2026-09-26).
# Start the loggers first, from R:
#   nvidia-smi --query-gpu=timestamp,power.draw.average,power.draw.instant,utilization.gpu,memory.used \
#     --format=csv,noheader,nounits -lms 100 > $R/gpu_power.csv &
# then: python3 tools/measure_speculative_acceptance.py aggregate --manifest <manifest.json>
# Sequential GPU queue for the speculative acceptance measurement.  Each stage waits until
# the shared GPU has room (other users' jobs come and go), then runs; every runner resumes
# from its own JSONL, so a failed stage is simply retried.
WT=$(cd "$(dirname "$0")/.." && pwd)
R=${R:?set R to a scratch directory holding prompts.jsonl (from the prepare subcommand)}
TOOL=$WT/tools/measure_speculative_acceptance.py
VPY=${VPY:-python3}   # a Python with vLLM 0.23 (DFlash support)
HPY=${HPY:-python3}   # a Python with torch 2.13 + transformers 5.15
cd "$WT" || exit 1
export CUDA_HOME=${CUDA_HOME:-/usr/local/cuda}   # nvcc >= 12.8 for FlashInfer JIT on sm_120
export PATH=$CUDA_HOME/bin:$PATH
export VLLM_USE_FLASHINFER_SAMPLER=0

wait_free() {  # $1 = GiB needed, held for 3 consecutive checks
  local need=$1 ok=0
  while [ $ok -lt 3 ]; do
    free=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)
    if [ "$free" -ge $((need * 1024)) ]; then ok=$((ok + 1)); else ok=0; fi
    sleep 20
  done
  echo "$(date +%T) free=${free}MiB >= ${need}GiB"
}

stage() {  # name, GiB, command...
  local name=$1 need=$2; shift 2
  for attempt in $(seq 1 300); do
    wait_free "$need"
    echo "$(date +%T) START $name attempt $attempt"
    "$@" >> "$R/$name.log" 2>&1
    rc=$?
    echo "$(date +%T) END $name rc=$rc"
    [ $rc -eq 0 ] && return 0
    sleep 60
  done
  return 1
}

stage vllm_dflash_k15 25 $VPY $TOOL run-vllm --method dflash --draft z-lab/Qwen3-8B-DFlash-b16 --k 15 \
  --gpu-memory-utilization 0.24 --prompts $R/prompts.jsonl --out $R/vllm_dflash_k15.jsonl
stage vllm_plain 25 $VPY $TOOL run-vllm --method none --k 0 \
  --gpu-memory-utilization 0.24 --prompts $R/prompts.jsonl --out $R/vllm_plain.jsonl
for Q in bf16; do
  stage timing_plain_$Q 25 $VPY $TOOL run-vllm --method none --k 0 --timing --per-workload 8 \
    --gpu-memory-utilization 0.24 --prompts $R/prompts.jsonl --out $R/timing_plain_$Q.jsonl
  stage timing_dflash_$Q 25 $VPY $TOOL run-vllm --method dflash --draft z-lab/Qwen3-8B-DFlash-b16 --k 15 --timing --per-workload 8 \
    --gpu-memory-utilization 0.24 --prompts $R/prompts.jsonl --out $R/timing_dflash_$Q.jsonl
done
stage timing_plain_fp8 25 $VPY $TOOL run-vllm --method none --k 0 --timing --per-workload 8 --quantization fp8 \
  --gpu-memory-utilization 0.24 --prompts $R/prompts.jsonl --out $R/timing_plain_fp8.jsonl
stage timing_dflash_fp8 25 $VPY $TOOL run-vllm --method dflash --draft z-lab/Qwen3-8B-DFlash-b16 --k 15 --timing --per-workload 8 --quantization fp8 \
  --gpu-memory-utilization 0.24 --prompts $R/prompts.jsonl --out $R/timing_dflash_fp8.jsonl
stage dflash_b16_spec 23 $HPY $TOOL run-hf --mode spec --prompts $R/prompts.jsonl \
  --out $R/dflash_b16_spec.jsonl --dflash-repo ${DFLASH_REPO:?checkout of github.com/z-lab/dflash}
# energy: c=1 timing again with the 100 ms power log running, then a concurrency sweep
stage energy_plain_bf16 25 $VPY $TOOL run-vllm --method none --k 0 --timing --per-workload 8 \
  --gpu-memory-utilization 0.24 --prompts $R/prompts.jsonl --out $R/energy_plain_bf16.jsonl
stage energy_dflash_bf16 25 $VPY $TOOL run-vllm --method dflash --draft z-lab/Qwen3-8B-DFlash-b16 --k 15 --timing --per-workload 8 \
  --gpu-memory-utilization 0.24 --prompts $R/prompts.jsonl --out $R/energy_dflash_bf16.jsonl
for C in 1 4 8 16; do
  stage sweep_plain_c$C 25 $VPY $TOOL sweep --method none --concurrency $C --prompts $R/prompts.jsonl --out $R/sweep.jsonl
  stage sweep_dflash_c$C 25 $VPY $TOOL sweep --method dflash --draft z-lab/Qwen3-8B-DFlash-b16 --k 15 --concurrency $C \
    --prompts $R/prompts.jsonl --out $R/sweep.jsonl
done
stage dflash_b16_base 23 $HPY $TOOL run-hf --mode baseline --prompts $R/prompts.jsonl \
  --out $R/dflash_b16_base.jsonl --spec-records $R/dflash_b16_spec.jsonl --dflash-repo ${DFLASH_REPO:?checkout of github.com/z-lab/dflash}
export VLLM_BATCH_INVARIANT=1
stage bi_plain 25 $VPY $TOOL run-vllm --method none --k 0 --per-workload 3 \
  --gpu-memory-utilization 0.24 --prompts $R/prompts.jsonl --out $R/bi_plain.jsonl
stage bi_dflash 25 $VPY $TOOL run-vllm --method dflash --draft z-lab/Qwen3-8B-DFlash-b16 --k 15 --per-workload 3 \
  --gpu-memory-utilization 0.24 --prompts $R/prompts.jsonl --out $R/bi_dflash.jsonl
unset VLLM_BATCH_INVARIANT
stage vllm_eagle3_redhat_k7 25 $VPY $TOOL run-vllm --method eagle3 --draft RedHatAI/Qwen3-8B-speculator.eagle3 --k 7 \
  --gpu-memory-utilization 0.24 --prompts $R/prompts.jsonl --out $R/vllm_eagle3_redhat_k7.jsonl
stage vllm_eagle3_angelslim_k7 25 $VPY $TOOL run-vllm --method eagle3 --draft AngelSlim/Qwen3-8B_eagle3 --k 7 \
  --gpu-memory-utilization 0.24 --prompts $R/prompts.jsonl --out $R/vllm_eagle3_angelslim_k7.jsonl
echo "$(date +%T) CAMPAIGN DONE"
