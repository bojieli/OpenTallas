# A100 80GB measured: Qwen3-8B decode on vLLM (A100-BENCH2, 2026-10-19)

Purpose: replace the assumed efficiencies in the modelled `a100_qwen` roofline
(claude/s81-balance-1018, `results/arch/s81_balance_1018/compute.py`: 173 tok/s at batch 1, 2,105 tok/s at 103 users,
8K context, INT8 weights + FP8 KV) with measured ones. Per the owner rule (10-18), the GPU baseline is the A100 80GB,
which is in the same 7 nm class as ASAP7.

## Setup
- 1x NVIDIA A100-SXM4-80GB, Vast.ai instance 56687322 (offer 54858898, UAE, $0.988/h), 06:55 to 09:25 UTC.
  The instance is DESTROYED and `vastai show instances` is empty. Cost: about $2.6 (credit 9.96 -> 7.41).
- vLLM 0.31.0 (`vllm/vllm-openai:v0.31.0`), torch 2.13.0+cu130, FlashInfer attention, CUDA graphs on, prefix caching
  off, `--gpu-memory-utilization 0.92`, `--max-num-seqs 512`, `--max-model-len 9216`.
- Models: `Qwen/Qwen3-8B` (BF16) and `nm-testing/Qwen3-8B-W8A8-INT8` (compressed-tensors INT8 W8A8, per-token dynamic
  activations, lm_head BF16). `RedHatAI/Qwen3-8B-quantized.w8a8` does not exist on HF.
- KV dtype: `fp8` (e4m3, no scaling calibration) or `auto` (BF16).
- Sweeps (scripts/remote_bench2.sh):
  - `declong` / `decshort` (**pure decode**, the quantity the roofline models): num_prompts = C, all requests start
    together, `--save-detailed`. The aggregate is the tokens emitted in the window from the LAST first token to the
    FIRST finished request; no prefill runs in that window. declong = 7,680 in + 1,024 out (context 7,680..8,704,
    mean 8,192); decshort = 256 in + 512 out (mean context 512).
  - `long` / `short` (mixed serving, `vllm bench serve` output throughput, N = 2C): 8,192/512 and 512/512.
    These include prefill and are not the modelled quantity; they are given for reference.
- `analysis.json` holds every run (rows), the decode-window results and the derived efficiencies (scripts/analyze.py).
  `raw/<config>/*.json` are the vLLM result files with the per-request arrays stripped; the full 85 MB raw output
  (per-token ITLs and server logs) is on localhost at /home/ubuntu/a100bench/a100_measured_1018_full_raw.tar.xz.

## Measured vs modelled (8K context, pure decode)

| config | b1 tok/s | model b1 | ratio | max fit users | best aggregate tok/s (C) | model aggregate (B) | ratio |
|---|---:|---:|---:|---:|---:|---:|---:|
| **W8A8 + FP8 KV** (modelled config) | **114.8** | 173.0 | **0.66** | 102 | **1,681 (102)** | 2,105 (103) | **0.80** |
| BF16 + FP8 KV | 85.1 | 173.0 | 0.49 | 92 | 1,514 (92) | 2,105 (103) | 0.72 |
| W8A8 + BF16 KV | 113.8 | 173.0 | 0.66 | 51 | 1,055 (51) | 2,105 (103) | 0.50 |
| BF16 + BF16 KV | 84.3 | 173.0 | 0.49 | 47 | 936 (47) | 2,105 (103) | 0.44 |

W8A8 + FP8 KV decode curve at 8K (aggregate / per user / step): C=1 115 / 114.8 / 8.71 ms; C=8 676 / 84.5 / 11.8 ms;
C=32 1,203 / 37.6 / 26.6 ms; C=64 1,537 / 24.0 / 41.6 ms; C=96 1,660 / 17.3 / 57.9 ms; C=102 1,681 / 16.5 / 60.7 ms.
The model's per-user rate at 103 users is 20.4 tok/s.

Short context (512, pure decode), W8A8 + FP8 KV: b1 120.3 tok/s (model 185.8, 0.65); the best aggregate is 9,802 tok/s
at C=384 (vLLM caps at 512 sequences). The model's compute-bound ceiling is 18,184.

Mixed serving (prefill included), W8A8 + FP8 KV: 8K/512 peaks at 608 output tok/s (C=102); 512/512 peaks at
6,062 (C=512).

## Measured efficiencies vs the model's assumptions (W8A8 + FP8 KV)

| term | model | measured | how |
|---|---:|---:|---|
| weight streaming (`eff.weight`) | 0.75 | **0.485** | two batch-1 points (ctx 512 and 8K) solved for the weight and KV terms |
| KV streaming, batch 1 (`eff.kv`) | 0.70 | 0.685 | same fit |
| KV streaming, batched (C=102) | 0.70 | **0.576** | per-user step slope, C=1 -> 102 at 8K |
| effective HBM BW at batch 1 | 1.53 TB/s (0.75 x 2.039) | 0.99-1.01 TB/s | (weight + KV bytes) / step |
| effective HBM BW at C=102, 8K | ~1.43 TB/s | 1.15 TB/s | (weight + 102 x KV) / step |
| compute (`eff.compute`, INT8 624 TOPS) | 0.45 | >= 0.24 (151 TOPS) | short ctx, C=512; a lower bound because the step also streams weights |
| KV capacity at 8K (`eff.capacity` 0.90) | 103 users | 102 users | 895,024 KV tokens at 0.92 memory utilisation |

The model with the measured efficiencies (weight 0.485, KV 0.685 at b1 and 0.576 batched) gives 114.8 tok/s at batch 1
and about 1,678 tok/s at 102 users, which matches the measurement. The batch-1 gap is in weight streaming. vLLM's
INT8 W8A8 GEMV path reaches about 1.0 TB/s, half of the 2.04 TB/s peak, and it also has per-step launch and
sampling overhead. Capacity matches the model.

## Reference, labelled: H100 DeepSeek (NOT the A100 baseline)
For a sense of scale only (different GPU, model and precision):
https://github.com/dzhsurf/deepseek-v3-r1-deploy-and-benchmarks reports **about 33 output tok/s for a single user**
for DeepSeek-V3/R1 671B (AWQ W4A16) on **8x H100 SXM5** with vLLM 0.7.3. It reports about 620 output tok/s at about
100 concurrent users, and above 980 on two nodes (16 GPUs) without InfiniBand.
This is an H100 figure. The owner's comparison baseline remains the A100 80GB.

## Files
- `analysis.json`: rows, decode windows, derived efficiencies, modelled values (constants copied from compute.py a100_qwen)
- `raw/<config>/`: slim vLLM result JSON per run, kv.txt (KV capacity), versions.txt, windows.txt (wall-clock per
  run), smi_*.csv (1 Hz power, clocks, memory), server_excerpt.txt; `raw/all.log` and `raw/nvidia-smi-initial.txt`
- `scripts/`: driver.sh (rent, then bench, then destroy, plus a 6 h watchdog), remote_bench.sh (v1), remote_bench2.sh
  (v2, with pure decode), all3.sh (the sequence that ran), analyze.py

Note on driver.sh: the run's destroy call stopped at vastai's new `[y/N]` prompt. The instance was destroyed by hand
at 09:25 UTC, and the script now passes `-y`.
