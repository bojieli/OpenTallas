# Qwen3-8B / 8K analytical addendum

> Generated from the same equations and hardware assumptions as `REPORT.md`.
> It is a dense control result, not a recommendation to make Qwen3-8B a product target.

## Evidence and workload contract

- Official checkpoint: `Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218`.
- Measured all-BF16 storage: 16,381,470,720 bytes; ordinary decode
  streams 15,136,811,008 bytes and keeps the
  1,244,659,712-byte input embedding as a lookup-resident table.
- Derived decode-active parameter count: 7,568,405,504; the untied LM head
  remains ordinary full-matrix decode traffic.
- Published topology: 36 dense layers, 32 query heads, 8 KV heads, 128 head dimension.
- Study context: 8,192 tokens. The conservative assumed BF16 GQA
  cache reads/stores 1,207,959,552 bytes per resident session.
- No speculative scenario is applied because the pinned checkpoint has no attached draft module.
- B200/B300 x1 and x2 analytical profiles are included alongside x4/x8/x16; only x8 is
  a published DGX device count, and every non-x8 cluster is a stated normalization.

## Required operating points

Ratios above 1 favor ROM. Speed uses the fastest feasible same-batch GPU; partial TCO
uses the cheapest feasible same-batch GPU and remains an incomplete cost proxy.

| Batch | ROM user tok/s | Fastest GPU | GPU user tok/s | ROM/GPU speed | Cheapest GPU | GPU/ROM partial TCO | ROM bind |
|---:|---:|---|---:|---:|---|---:|---|
| 1 | 3,371.9 | NVIDIA-B300-x16 | 1,766.6 | 1.91× | NVIDIA-B200-x1 | 1.29× | rom_full_array_read_C4 |
| 8 | 427.9 | NVIDIA-B300-x16 | 1,434.4 | 0.30× | NVIDIA-B200-x1 | 0.26× | kv_beachfront_C8 |
| 32 | 107.1 | NVIDIA-B300-x16 | 872.2 | 0.12× | NVIDIA-B200-x1 | 0.14× | kv_beachfront_C8 |
| 64 | 53.6 | NVIDIA-B300-x16 | 572.8 | 0.09× | NVIDIA-B200-x1 | 0.12× | kv_beachfront_C8 |
| 128 | 26.8 | NVIDIA-B300-x16 | 339.6 | 0.08× | NVIDIA-B200-x2 | 0.12× | kv_beachfront_C8 |

## Capacity-bound optima and conclusion

- ROM latency/balanced optimum: B1/B1; ROM aggregate-throughput optimum: B286; ROM partial-TCO optimum: B286.
- GPU latency optimum: NVIDIA-B300-x16/B1; balanced: NVIDIA-B300-x16/B29; aggregate throughput: NVIDIA-B300-x16/B3419; partial TCO: NVIDIA-B200-x4/B522.
- ROM exceeds the fastest GPU's global per-user-speed optimum only at batch 1-1. At B8 and above, the modeled ROM HBM beachfront binds and both speed and partial TCO favor GPU.
- One 10.24%-occupied ROM stage is a useful dense/GQA verification control, but poor fixed-weight capacity utilization and the single-batch speed island do not support elevating Qwen3-8B into the target list.
