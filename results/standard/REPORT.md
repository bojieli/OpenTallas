# Standard analytical simulation report

> This report is generated. Hardware results are conditional on the explicit
> architecture assumptions; checkpoint sizes and model topology are measured/published.

## Measured model inputs and derived KV traffic

| Model | Released storage | Active dense / routed | Target-decode dense / routed | Draft / other resident | Context | KV read/user/token | KV store/user | ρ₁ | ROM stages |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 166.879 GB | 6.50 / 6.50 B | 7.768 / 147.170 GB | 10.863 / 1.078 GB | 200,000 | 0.0991 GB | 0.7050 GB | 113.19 | 2 |
| DeepSeek-V4-Flash-0731 | 166.879 GB | 6.50 / 6.50 B | 7.768 / 147.170 GB | 10.863 / 1.078 GB | 1,000,000 | 0.4576 GB | 3.5121 GB | 24.52 | 2 |
| DeepSeek-V4-Pro-0813 | 892.728 GB | 24.38 / 24.62 B | 26.822 / 822.054 GB | 41.979 / 1.872 GB | 200,000 | 0.1527 GB | 1.0093 GB | 259.75 | 6 |
| DeepSeek-V4-Pro-0813 | 892.728 GB | 24.38 / 24.62 B | 26.822 / 822.054 GB | 41.979 / 1.872 GB | 1,000,000 | 0.6737 GB | 5.0283 GB | 58.88 | 6 |
| Kimi-K3 | 1560.860 GB | 54.98 / 49.02 B | 111.161 / 1446.456 GB | 0.000 / 3.244 GB | 200,000 | 3.2142 GB | 3.2142 GB | 42.62 | 11 |
| Kimi-K3 | 1560.860 GB | 54.98 / 49.02 B | 111.161 / 1446.456 GB | 0.000 / 3.244 GB | 1,000,000 | 14.2734 GB | 14.2734 GB | 9.60 | 11 |
| Qwen3-8B | 16.381 GB | 7.57 / 0.00 B | 15.137 / 0.000 GB | 0.000 / 1.245 GB | 8,192 | 1.2080 GB | 1.2080 GB | 12.53 | 1 |

## Required operating points

The table uses the no-speculation scenario. `GPU` is the fastest feasible B200/B300
configuration at the same active microbatch; ratios above 1 favor ROM. ROM batch
is per pipeline stage, so its resident session count is batch × stages.

| Model | Context | Batch/stage | ROM residents | ROM user tok/s | Fastest GPU | GPU user tok/s | Speed ratio | Cheapest partial-TCO GPU | Partial-TCO ratio | ROM bind |
|---|---:|---:|---:|---:|---|---:|---:|---|---:|---|
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | 2 | 4,349.6 | NVIDIA-B300-x8 | 1,676.8 | 2.59× | NVIDIA-B200-x2 | 1.74× | rom_full_array_read_C4 |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | 16 | 1,124.3 | NVIDIA-B300-x16 | 983.4 | 1.14× | NVIDIA-B200-x2 | 1.42× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | 64 | 282.5 | NVIDIA-B300-x16 | 502.4 | 0.56× | NVIDIA-B200-x2 | 0.95× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | 128 | 141.3 | NVIDIA-B300-x16 | 364.4 | 0.39× | NVIDIA-B200-x2 | 0.69× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 200,000 | 128 | 256 | 70.7 | NVIDIA-B300-x16 | 291.6 | 0.24× | NVIDIA-B200-x2 | 0.43× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | 2 | 4,349.6 | NVIDIA-B300-x8 | 1,651.7 | 2.63× | NVIDIA-B200-x2 | 1.79× | rom_full_array_read_C4 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | 16 | 1,026.7 | NVIDIA-B300-x16 | 946.8 | 1.08× | NVIDIA-B200-x2 | 1.39× | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | 64 | 257.8 | NVIDIA-B300-x16 | 465.7 | 0.55× | NVIDIA-B200-x2 | 0.96× | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | 128 | 129.0 | NVIDIA-B300-x16 | 326.9 | 0.39× | NVIDIA-B200-x4 | 0.73× | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 128 | 256 | — | NVIDIA-B300-x16 | 246.4 | — | NVIDIA-B200-x4 | — | capacity_C7_C8_C9 |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | 6 | 1,193.8 | NVIDIA-B300-x16 | 611.3 | 1.95× | NVIDIA-B300-x4 | 2.77× | rom_full_array_read_C4 |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | 48 | 292.4 | NVIDIA-B300-x16 | 360.9 | 0.81× | NVIDIA-B200-x8 | 1.78× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | 192 | 73.3 | NVIDIA-B300-x16 | 147.3 | 0.50× | NVIDIA-B200-x8 | 1.24× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | 384 | 36.7 | NVIDIA-B300-x16 | 95.9 | 0.38× | NVIDIA-B200-x8 | 0.97× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 200,000 | 128 | 768 | 18.3 | NVIDIA-B300-x16 | 70.2 | 0.26× | NVIDIA-B200-x8 | 0.66× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | 6 | 1,193.8 | NVIDIA-B300-x16 | 608.6 | 1.96× | NVIDIA-B300-x4 | 2.80× | rom_full_array_read_C4 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | 48 | 292.4 | NVIDIA-B300-x16 | 353.6 | 0.83× | NVIDIA-B200-x8 | 1.83× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | 192 | 73.3 | NVIDIA-B300-x16 | 142.5 | 0.51× | NVIDIA-B200-x8 | 1.29× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | 384 | 36.7 | NVIDIA-B300-x16 | 91.9 | 0.40× | NVIDIA-B200-x8 | 1.02× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 128 | 768 | — | NVIDIA-B300-x16 | 66.0 | — | NVIDIA-B300-x8 | — | capacity_C7_C8_C9 |
| Kimi-K3 | 200,000 | 1 | 11 | 337.3 | NVIDIA-B300-x16 | 325.3 | 1.04× | NVIDIA-B300-x8 | 2.78× | rom_full_array_read_C4 |
| Kimi-K3 | 200,000 | 8 | 88 | 110.1 | NVIDIA-B300-x16 | 163.0 | 0.68× | NVIDIA-B300-x8 | 2.14× | kv_beachfront_C8 |
| Kimi-K3 | 200,000 | 32 | 352 | 27.6 | NVIDIA-B300-x16 | 66.2 | 0.42× | NVIDIA-B200-x16 | 1.38× | kv_beachfront_C8 |
| Kimi-K3 | 200,000 | 64 | 704 | 13.8 | NVIDIA-B300-x16 | 43.3 | 0.32× | NVIDIA-B200-x16 | 1.06× | kv_beachfront_C8 |
| Kimi-K3 | 200,000 | 128 | 1,408 | — | NVIDIA-B300-x16 | 30.9 | — | NVIDIA-B200-x16 | — | capacity_C7_C8_C9 |
| Kimi-K3 | 1,000,000 | 1 | 11 | 212.1 | NVIDIA-B300-x16 | 310.1 | 0.68× | NVIDIA-B300-x8 | 1.87× | kv_beachfront_C8 |
| Kimi-K3 | 1,000,000 | 8 | 88 | 26.6 | NVIDIA-B300-x16 | 136.2 | 0.20× | NVIDIA-B300-x8 | 0.64× | kv_beachfront_C8 |
| Kimi-K3 | 1,000,000 | 32 | 352 | — | NVIDIA-B300-x16 | 50.1 | — | NVIDIA-B200-x16 | — | capacity_C7_C8_C9 |
| Kimi-K3 | 1,000,000 | 64 | 704 | — | NVIDIA-B300-x16 | 30.5 | — | NVIDIA-B200-x16 | — | capacity_C7_C8_C9 |
| Kimi-K3 | 1,000,000 | 128 | 1,408 | — | NVIDIA-B300-x16 | 19.3 | — | NVIDIA-B300-x16 | — | capacity_C7_C8_C9 |
| Qwen3-8B | 8,192 | 1 | 1 | 3,371.9 | NVIDIA-B300-x16 | 1,766.6 | 1.91× | NVIDIA-B200-x1 | 1.29× | rom_full_array_read_C4 |
| Qwen3-8B | 8,192 | 8 | 8 | 427.9 | NVIDIA-B300-x16 | 1,434.4 | 0.30× | NVIDIA-B200-x1 | 0.26× | kv_beachfront_C8 |
| Qwen3-8B | 8,192 | 32 | 32 | 107.1 | NVIDIA-B300-x16 | 872.2 | 0.12× | NVIDIA-B200-x1 | 0.14× | kv_beachfront_C8 |
| Qwen3-8B | 8,192 | 64 | 64 | 53.6 | NVIDIA-B300-x16 | 572.8 | 0.09× | NVIDIA-B200-x1 | 0.12× | kv_beachfront_C8 |
| Qwen3-8B | 8,192 | 128 | 128 | 26.8 | NVIDIA-B300-x16 | 339.6 | 0.08× | NVIDIA-B200-x2 | 0.12× | kv_beachfront_C8 |

## Same-microbatch B200 versus B300 family view

This isolates GPU generation from cluster-size selection. Each family column is
the fastest feasible x1/x2/x4/x8/x16 point at the same active microbatch. Ratios above
1 favor ROM; this view does not match the ROM pipeline's larger resident population.

| Model | Context | Batch/stage | ROM user tok/s | Best B200 user tok/s | ROM/B200 | Best B300 user tok/s | ROM/B300 |
|---|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | 4,349.6 | 1,659.9 | 2.62× | 1,676.8 | 2.59× |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | 1,124.3 | 966.7 | 1.16× | 983.4 | 1.14× |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | 141.3 | 356.7 | 0.40× | 364.4 | 0.39× |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | 4,349.6 | 1,635.3 | 2.66× | 1,651.7 | 2.63× |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | 1,026.7 | 931.3 | 1.10× | 946.8 | 1.08× |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | 129.0 | 320.7 | 0.40× | 326.9 | 0.39× |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | 1,193.8 | 602.1 | 1.98× | 611.3 | 1.95× |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | 292.4 | 354.0 | 0.83× | 360.9 | 0.81× |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | 36.7 | 93.7 | 0.39× | 95.9 | 0.38× |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | 1,193.8 | 599.5 | 1.99× | 608.6 | 1.96× |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | 292.4 | 347.0 | 0.84× | 353.6 | 0.83× |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | 36.7 | 89.8 | 0.41× | 91.9 | 0.40× |
| Kimi-K3 | 200,000 | 1 | 337.3 | 322.4 | 1.05× | 325.3 | 1.04× |
| Kimi-K3 | 200,000 | 8 | 110.1 | 160.5 | 0.69× | 163.0 | 0.68× |
| Kimi-K3 | 200,000 | 64 | 13.8 | 42.4 | 0.33× | 43.3 | 0.32× |
| Kimi-K3 | 1,000,000 | 1 | 212.1 | 307.4 | 0.69× | 310.1 | 0.68× |
| Kimi-K3 | 1,000,000 | 8 | 26.6 | 134.3 | 0.20× | 136.2 | 0.20× |
| Kimi-K3 | 1,000,000 | 64 | — | 30.0 | — | 30.5 | — |
| Qwen3-8B | 8,192 | 1 | 3,371.9 | 1,753.5 | 1.92× | 1,766.6 | 1.91× |
| Qwen3-8B | 8,192 | 8 | 427.9 | 1,425.2 | 0.30× | 1,434.4 | 0.30× |
| Qwen3-8B | 8,192 | 64 | 53.6 | 570.5 | 0.09× | 572.8 | 0.09× |

## Assumed speculative-decoding midpoint

This is a sensitivity case, not a measured serving result: five draft tokens,
70% independent acceptance probability, and serial draft work per candidate equal
to 8% of one target-decode compute pass are assumed for both ROM and GPU. Gain is speculative/no-speculation
per-user throughput at the same batch. The GPU column uses the fastest feasible
B200/B300 configuration in each scenario; ratios above 1 favor ROM.
Qwen3-8B is omitted because its pinned checkpoint has no attached draft module;
no external-draft performance is assumed.

| Model | Context | Batch/stage | ROM no-spec | ROM speculative | ROM gain | GPU no-spec | GPU speculative | GPU gain | Speculative ROM/GPU |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | 4,349.6 | 4,169.2 | 0.96× | 1,676.8 | 3,085.9 | 1.84× | 1.35× |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | 1,124.3 | 524.9 | 0.47× | 983.4 | 1,156.4 | 1.18× | 0.45× |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | 141.3 | 65.7 | 0.46× | 364.4 | 617.3 | 1.69× | 0.11× |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | 4,349.6 | 3,825.9 | 0.88× | 1,651.7 | 2,993.4 | 1.81× | 1.28× |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | 1,026.7 | 481.3 | 0.47× | 946.8 | 1,058.4 | 1.12× | 0.45× |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | 129.0 | 60.2 | 0.47× | 326.9 | 442.3 | 1.35× | 0.14× |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | 1,193.8 | 1,083.6 | 0.91× | 611.3 | 1,179.2 | 1.93× | 0.92× |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | 292.4 | 135.9 | 0.46× | 360.9 | 320.7 | 0.89× | 0.42× |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | 36.7 | 17.0 | 0.46× | 95.9 | 154.5 | 1.61× | 0.11× |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | 1,193.8 | 1,083.6 | 0.91× | 608.6 | 1,159.3 | 1.90× | 0.93× |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | 292.4 | 135.9 | 0.46× | 353.6 | 309.2 | 0.87× | 0.44× |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | 36.7 | 17.0 | 0.46× | 91.9 | 135.0 | 1.47× | 0.13× |
| Kimi-K3 | 200,000 | 1 | 337.3 | 412.1 | 1.22× | 325.3 | 562.0 | 1.73× | 0.73× |
| Kimi-K3 | 200,000 | 8 | 110.1 | 51.6 | 0.47× | 163.0 | 150.4 | 0.92× | 0.34× |
| Kimi-K3 | 200,000 | 64 | 13.8 | 6.5 | 0.47× | 43.3 | 58.5 | 1.35× | 0.11× |
| Kimi-K3 | 1,000,000 | 1 | 212.1 | 103.1 | 0.49× | 310.1 | 478.8 | 1.54× | 0.22× |
| Kimi-K3 | 1,000,000 | 8 | 26.6 | 12.9 | 0.48× | 136.2 | 109.6 | 0.81× | 0.12× |
| Kimi-K3 | 1,000,000 | 64 | — | — | — | 30.5 | 27.1 | 0.89× | — |

## Resident-concurrency-matched B200/B300 comparison

A ROM pipeline holds one microbatch at every stage. Here each GPU is simulated
at the resulting total resident-session count, and the smallest feasible 1/2/4/8/16
configuration is shown. This is the capacity-matched service comparison.

| Model | Context | ROM B/stage | Resident sessions | ROM user tok/s | Smallest B200 | user tok/s | Smallest B300 | user tok/s | Partial-TCO ratio vs cheapest GPU |
|---|---:|---:|---:|---:|---|---:|---|---:|---:|
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | 2 | 4,349.6 | NVIDIA-B200-x2 | 596.8 | NVIDIA-B300-x1 | 321.2 | 1.15× |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | 16 | 1,124.3 | NVIDIA-B200-x2 | 151.3 | NVIDIA-B300-x1 | 78.5 | 1.17× |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | 128 | 141.3 | NVIDIA-B200-x2 | 52.2 | NVIDIA-B300-x1 | 27.0 | 0.43× |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | 2 | 4,349.6 | NVIDIA-B200-x2 | 572.0 | NVIDIA-B300-x1 | 306.9 | 1.20× |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | 16 | 1,026.7 | NVIDIA-B200-x2 | 139.0 | NVIDIA-B300-x1 | 71.9 | 1.17× |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | 128 | 129.0 | NVIDIA-B200-x4 | 82.8 | NVIDIA-B300-x4 | 84.0 | 0.49× |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | 6 | 1,193.8 | NVIDIA-B200-x8 | 307.7 | NVIDIA-B300-x4 | 169.1 | 1.00× |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | 48 | 292.4 | NVIDIA-B200-x8 | 69.3 | NVIDIA-B300-x4 | 36.1 | 1.09× |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | 384 | 36.7 | NVIDIA-B200-x8 | 35.3 | NVIDIA-B300-x8 | 36.0 | 0.27× |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | 6 | 1,193.8 | NVIDIA-B200-x8 | 300.4 | NVIDIA-B300-x4 | 164.7 | 1.03× |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | 48 | 292.4 | NVIDIA-B200-x8 | 66.4 | NVIDIA-B300-x8 | 67.7 | 1.13× |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | 384 | 36.7 | infeasible | — | NVIDIA-B300-x16 | 47.6 | 0.49× |
| Kimi-K3 | 200,000 | 1 | 11 | 337.3 | NVIDIA-B200-x16 | 132.1 | NVIDIA-B300-x8 | 84.4 | 0.73× |
| Kimi-K3 | 200,000 | 8 | 88 | 110.1 | NVIDIA-B200-x16 | 35.9 | NVIDIA-B300-x8 | 21.9 | 0.91× |
| Kimi-K3 | 200,000 | 64 | 704 | 13.8 | infeasible | — | NVIDIA-B300-x16 | 14.4 | 0.35× |
| Kimi-K3 | 1,000,000 | 1 | 11 | 212.1 | NVIDIA-B200-x16 | 108.3 | NVIDIA-B300-x8 | 67.0 | 0.58× |
| Kimi-K3 | 1,000,000 | 8 | 88 | 26.6 | infeasible | — | NVIDIA-B300-x16 | 24.6 | 0.40× |
| Kimi-K3 | 1,000,000 | 64 | 704 | — | infeasible | — | infeasible | — | — |
| Qwen3-8B | 8,192 | 1 | 1 | 3,371.9 | NVIDIA-B200-x1 | 323.6 | NVIDIA-B300-x1 | 322.5 | 1.29× |
| Qwen3-8B | 8,192 | 8 | 8 | 427.9 | NVIDIA-B200-x1 | 208.3 | NVIDIA-B300-x1 | 207.7 | 0.26× |
| Qwen3-8B | 8,192 | 64 | 64 | 53.6 | NVIDIA-B200-x1 | 54.1 | NVIDIA-B300-x1 | 54.0 | 0.12× |

## Batch optima and speed-superiority bands

A speed-superiority batch beats the fastest per-user GPU point at *any* batch,
not merely the GPU at the same batch. Bands are evaluated on the dense 1..256 sweep;
all optima are searched exhaustively over integer batches through local capacity.

Balanced maximizes the geometric mean of normalized per-user speed and aggregate
throughput. Cost is partial TCO: hardware/NRE amortization plus active electricity;
it excludes staffing, financing, networking, floor space, maintenance, and spares.

| Model | Context | Scenario | ROM latency B | ROM balanced B | ROM throughput B | ROM partial-TCO B | GPU latency arch/B | GPU balanced arch/B | GPU throughput arch/B | GPU partial-TCO arch/B | ROM superiority batches |
|---|---:|---|---:|---:|---:|---:|---|---|---|---|---|
| DeepSeek-V4-Flash-0731 | 200,000 | no_speculation | 1 | 2 | 468 | 468 | NVIDIA-B300-x8/B1 | NVIDIA-B300-x16/B767 | NVIDIA-B300-x16/B5645 | NVIDIA-B200-x8/B1601 | 1-5 |
| DeepSeek-V4-Flash-0731 | 200,000 | speculative_midpoint | 1 | 1 | 468 | 468 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B134 | NVIDIA-B300-x16/B5645 | NVIDIA-B200-x8/B1601 | 1-1 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | no_speculation | 1 | 2 | 94 | 94 | NVIDIA-B300-x8/B1 | NVIDIA-B300-x16/B341 | NVIDIA-B300-x16/B1133 | NVIDIA-B300-x8/B542 | 1-4 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | speculative_midpoint | 1 | 1 | 94 | 94 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B60 | NVIDIA-B300-x16/B1133 | NVIDIA-B200-x8/B321 | 1-1 |
| DeepSeek-V4-Pro-0813 | 200,000 | no_speculation | 1 | 2 | 340 | 340 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B1752 | NVIDIA-B300-x16/B3224 | NVIDIA-B300-x16/B3224 | 1-3 |
| DeepSeek-V4-Pro-0813 | 200,000 | speculative_midpoint | 1 | 1 | 340 | 340 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B301 | NVIDIA-B300-x16/B3224 | NVIDIA-B300-x8/B1169 | none |
| DeepSeek-V4-Pro-0813 | 1,000,000 | no_speculation | 1 | 2 | 68 | 68 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B647 | NVIDIA-B300-x16/B647 | NVIDIA-B300-x16/B647 | 1-3 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | speculative_midpoint | 1 | 1 | 68 | 68 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B165 | NVIDIA-B300-x16/B647 | NVIDIA-B200-x16/B337 | none |
| Kimi-K3 | 200,000 | no_speculation | 1 | 4 | 81 | 81 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B5 | NVIDIA-B300-x16/B804 | NVIDIA-B300-x16/B804 | 1-1 |
| Kimi-K3 | 200,000 | speculative_midpoint | 1 | 1 | 81 | 81 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B804 | NVIDIA-B200-x16/B320 | none |
| Kimi-K3 | 1,000,000 | no_speculation | 1 | 1 | 17 | 17 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B4 | NVIDIA-B300-x16/B181 | NVIDIA-B300-x16/B181 | none |
| Kimi-K3 | 1,000,000 | speculative_midpoint | 1 | 1 | 17 | 17 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B181 | NVIDIA-B200-x16/B72 | none |
| Qwen3-8B | 8,192 | no_speculation | 1 | 1 | 286 | 286 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B29 | NVIDIA-B300-x16/B3419 | NVIDIA-B200-x4/B522 | 1-1 |

## Interpretation boundary

- The curves verify accounting and reveal which constraint binds under each input set.
- They do **not** verify the assumed ROM density, 100 TB/s read path, 1 POP/s MAC
  fabric, wafer yield, package HBM capacity, or cost. Sensitivity and circuit/NoC
  work must survive before any go decision.
- GPU marketing peaks are derated explicitly; production traces remain necessary to
  replace engaged-bandwidth, collective, and speculative-acceptance assumptions.
- Kimi K3 uses an optimized FP8 latent MLA cache. The reference BF16 expanded cache
  is a pessimistic sensitivity case, not silently mixed into this table.
- Qwen3-8B uses a conservative assumed BF16 full-GQA KV cache at 8K and no
  speculative scenario. It is a dense control, not an additional product target.
