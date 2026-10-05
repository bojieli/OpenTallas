# H100 SXM5 HGX (8 GPUs, 4x NVSwitch gen3 / NVLink4, NV18) NVLS microbenchmarks, 2026-10-04
Node: rented 8x H100 80GB HBM3, driver 570.172.08, CUDA 12.8, Fabric Manager state Completed, CU_DEVICE_ATTRIBUTE_MULTICAST_SUPPORTED=1 on all 8.
Method: single process, persistent one-block kernels, %globaltimer over 20,000 iterations, two repeated runs (identical to <1%). Source: nvls_lat.cu, gpu_sync.cu.

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
|   same, 2 GPUs / 4 GPUs | 2,220-2,644 / 2,234-2,562 ns (flat in group size) |
|   data part only (minus 2 barriers), 8 GPUs | 783-1,136 ns |
| One-shot NVLS all-reduce, sys release/acquire sync | 8,904-9,144 ns |
| All-gather via multimem.st, relaxed sync, 8 GPUs | 1,382 (128 B) / 1,386 (2 KB) / 1,590 ns (32 KB total) |
| In-switch reduce determinism (cancellation inputs, 8 GPUs x 5 repeats) | bit-identical, 0 mismatches |
| NCCL all_reduce_perf (no CUDA graph), 8 GPUs, 128 B-32 KB | 32-36 us (NVLS and default identical) |
| Cooperative grid.sync, 132 SMs | 1,097 ns |
| Back-to-back kernel launch (stream) | 2,672 ns |
| CUDA graph kernel node | 1,014 ns |

Notes: relaxed-sync runs passed the value check (sum 36 for 8 GPUs) but are not memory-model-guaranteed; they bound the HARDWARE path. The sys-scope fence variant is what correct GPU software pays. NCCL with CUDA graphs (-G) hung on this node and was killed (not measured).

## vLLM 0.11.0 (torch 2.8 cu128, CUDA graphs, V1 engine) Qwen3-8B batch-1 decode, same node
Input 128 tokens, output 512 tokens, 2 warmup + 5 iterations; tok/s = 512 / average end-to-end latency (prefill of 128 tokens included, <1%).
| TP | BF16 avg latency (s) | BF16 tok/s | FP8 (vLLM dynamic fp8) avg latency (s) | FP8 tok/s |
|---|---|---|---|---|
| 1 | 3.708 | 138.1 | 2.637 | 194.1 |
| 2 | 2.619 | 195.5 | 2.115 | 242.1 |
| 4 | 1.972 | 259.7 | 1.859 | 275.4 |
| 8 | 1.745 | 293.4 | 1.675 | 305.7 |
8K-context and EAGLE-3 speculative runs: pending (appended when done).
