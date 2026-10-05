# H100 SXM5 HGX NVLS microbenchmarks (MEASURED, 2026-10-04)

These are hardware measurements on an NVLink4 / H100-generation system. They are not NVLink5, GB200 or NVL72. The repository uses them as the anchors for the HBM switch-collective scenarios (`tools/uarch_model.py` `HBM_SWITCH_LATENCY`, record `results/uarch/hbm_switch_latency_authoritative_20261004/`).

**Node:** a rented 8x H100 80GB HBM3 SXM5 HGX with 4x NVSwitch gen3 (NVLink4, NV18). Driver 570.172.08, CUDA 12.8. Fabric Manager state was Completed, and `CU_DEVICE_ATTRIBUTE_MULTICAST_SUPPORTED=1` on all 8 GPUs.

**Method:** one process drives all 8 GPUs. Persistent one-block kernels are timed with `%globaltimer` over 20,000 iterations, and each figure is the worst GPU's time divided by the iteration count. Every run was repeated twice, and the two runs agree to better than 1%. Multicast objects come from `cuMulticastCreate` and `cuMulticastBindMem`. Collectives use the PTX `multimem.ld_reduce`, `multimem.st` and `multimem.red` instructions. The "relaxed" variants use `.relaxed.sys` flags with no fence. They passed the value check (8-GPU sum = 36), but the memory model does not guarantee them, so they bound the HARDWARE path. The "sys" variants use `__threadfence_system` + `multimem.red.release.sys` + `ld.acquire.sys`, which is what correct GPU software pays. The grid sync, kernel launch and graph node figures come from `gpu_sync.cu` on one GPU (cooperative launch on 132 SMs x 256 threads, 20,000 back-to-back empty kernels, and a captured 1,000-node graph replayed 20 times).

**Sources (verbatim):** `nvls_lat.cu`, `gpu_sync.cu`, plus the vLLM runs below. The operator's report is kept as `results_as_reported.md`.

| Measurement | Result |
|---|---|
| Local HBM load round trip (L2-miss chain) | 150-160 ns |
| Remote (peer) load round trip via NVSwitch, GPU0->1/4/7 | 488-496 ns |
| multimem.ld_reduce round trip (in-switch reduce of 8 copies), single thread | 870 ns (2 GPUs) / 880 (4) / 896 (8) |
| One-way remote store, relaxed ping-pong | 762 ns (RTT 1,525) |
| One-way remote store, release/acquire (sys) ping-pong | 2,262 ns (RTT 4,524) |
| Barrier: multimem.red + local poll, relaxed | 704-731 ns (flat for 2/4/8 GPUs) |
| Barrier with __threadfence_system + red.release + ld.acquire (sys) | 4,020-4,044 ns |
| One-shot NVLS all-reduce, relaxed sync (barrier + ld_reduce slice + multimem.st + barrier), 8 GPUs | 2,244 (128 B), 2,249 (512 B), 2,455 (2 KB), 2,510 (8 KB), 2,597 ns (32 KB) |
| same, 2 GPUs / 4 GPUs | 2,220-2,644 / 2,234-2,562 ns (flat in group size) |
| data part only (minus 2 barriers), 8 GPUs | 783-1,136 ns |
| One-shot NVLS all-reduce, sys release/acquire sync | 8,904-9,144 ns |
| All-gather via multimem.st, relaxed sync, 8 GPUs | 1,382 (128 B) / 1,386 (2 KB) / 1,590 ns (32 KB total) |
| In-switch reduce determinism (cancellation inputs, 8 GPUs x 5 repeats) | bit-identical, 0 mismatches |
| NCCL all_reduce_perf (no CUDA graph), 8 GPUs, 128 B-32 KB | 32-36 us (NVLS and default identical) |
| Cooperative grid.sync, 132 SMs | 1,097 ns |
| Back-to-back kernel launch (stream) | 2,672 ns |
| CUDA graph kernel node | 1,014 ns |

## vLLM Qwen3-8B batch-1 decode, same node (AUTHORITATIVE Qwen GPU baseline)

Stack: vLLM 0.11.0 (torch 2.8 cu128, CUDA graphs, V1 engine). Each run is 128 tokens in and 512 tokens out, with 2 warmup and 5 measured iterations. tok/s = 512 / mean end-to-end latency. The 128-token prefill is included and is under 1% of the time. FP8 is vLLM dynamic FP8.

| TP | BF16 latency (s) | BF16 tok/s | FP8 latency (s) | FP8 tok/s |
|---|---|---|---|---|
| 1 | 3.708 | 138.1 | 2.637 | 194.1 |
| 2 | 2.619 | 195.5 | 2.115 | 242.1 |
| 4 | 1.972 | 259.7 | 1.859 | 275.4 |
| 8 | 1.745 | 293.4 | 1.675 | 305.7 |

`tools/uarch_model.py` publishes these as tier-1 rows (`QWEN_GPU_H100_MEASURED`). The B200 rows are kept as labelled model and published anchors. These runs are short context, while the Qwen HBM die is priced at 8K. The 8K-context and EAGLE-3 speculative runs were still pending when this record was committed.

Not measured:
- NCCL with CUDA graphs (`all_reduce_perf -G`). It hung on this node and was killed.
- Any group larger than 8 GPUs.
- NVLink5 / NVL72.

Readings used by the model:
- The one-shot all-reduce is flat from 2 to 8 GPUs, so its fixed term is carried to the 48-package tier with a 0.15 us (0.1-0.2) striping tail.
- The relaxed barrier costs 0.70-0.73 us, so the all-reduce's two barriers take about 1.4 of its 2.24 us.
- The sys-scope fences add about 3.3 us per barrier.
- Per-leg reach is the peer load RTT minus a local miss, (490 - 155) / 4, which is about 85 ns a leg including the switch. That is board reach, at or below the ROM's light-FEC 130 ns board-link class.

## Addendum (2026-10-04): prefill/decode-separated vLLM baselines and published references
Decode rate = (generated - 1) / (end-to-end latency - prefill-only latency); prefill-only = output length 1. Raw logs in vllm_logs/.

Qwen3-8B, vLLM 0.11, H100 SXM:
| config | prefill 128 | prefill 8K | decode @128 ctx | decode @8K ctx |
|---|---|---|---|---|
| TP1 BF16 | 9.5 ms | 223 ms | 138 tok/s (7.24 ms) | 131 tok/s (7.65 ms) |
| TP1 FP8 | 7.0 ms | 163 ms | 194 tok/s (5.15 ms) | 180 tok/s (5.55 ms) |
| TP8 BF16 | 7.2 ms | - | 294 tok/s (3.40 ms) | - |
| TP8 FP8 | 5.5 ms | 56 ms | 306 tok/s (3.27 ms) | 299 tok/s (3.35 ms) |
| TP8 FP8 + all-reduce/RMSNorm fusion | 5.6 ms | - | 304 tok/s (3.29 ms) | - |
Verify-step proxy (6 sequences in flight, TP1): BF16 7.49 ms vs 7.24 single (+3.5%); FP8 5.35 vs 5.15 ms (+3.9%).

Qwen3.8-27B, vLLM 0.30 (CUDA 13 forward-compat), H100 SXM TP1 FP8: prefill 128 = 52 ms, 8K = 494 ms; decode 80.6 tok/s @128 ctx, 79.7 tok/s @8K ctx.
Multi-GPU (TP8) runs under vLLM 0.30 failed with an NCCL CUDA error under the CUDA-13 forward-compatibility layer (driver 570); not measured. DeepSeek-V4.1-Flash (needs TP8) therefore not measured on this node.
EAGLE-3 runs used vLLM's random-token latency benchmark (acceptance meaningless); excluded. Acceptance comes from published values.

Published references used instead (third party):
- CORRECTED 2026-10-04 (pages re-fetched; registry `results/external/registry.json` id `nvls:lmsys_dsv4_day0`): the LMSYS Day-0 post reports DeepSeek-**V4**-Flash (not V4.1) on H200 TP4 at 266 tok/s for 4K context, falling to 240 tok/s at 900K, and V4-Pro on B200 TP8 at 199 to 180 tok/s, all single batch with OSL 4096 (https://www.lmsys.org/blog/2026-04-25-deepseek-v4/). The post does not say whether speculation was on for that figure, but it most likely was: Figure 1 used EAGLE 3/1/4 and the caption cites in-graph spec metadata. The 30K prefix belongs to Figure 1. The NVIDIA Dynamo V4.1 recipe (https://docs.nvidia.com/dynamo/dev/recipes/deepseek-v4-1-flash) carries no performance figure. See `results/measured/gpu_third_party_20261004/`; H100 is not a supported target (user reports 40-50 tok/s; https://github.com/sgl-project/sglang/discussions/39791).
- Qwen3.8-27B single-stream (concurrency 1) on 2x H100: Together 189.6 tok/s (TP2), g factor MTP4 133.0, Fireworks 114.5, vanilla vLLM 69.3 (https://dev.to/g_factor/benchmarking-qwen-38-27b-across-inference-providers-together-fireworks-doubleword-and-g-factor-4c1i).
Note: figures quoted from search summaries; verify against the pages before publication.
