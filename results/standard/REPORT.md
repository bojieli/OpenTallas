# Standard analytical simulation report

> **Legacy/superseded technology comparison.** This single-midpoint
> B200/B300 study is retained for model-general regression and provenance.
> Current product comparisons are in `results/iso-node/` and must not be
> combined with the figures below.

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

## Numeric format contract

Storage width is not used as a proxy for arithmetic precision. In particular,
DeepSeek routed experts store MXFP4 weights but multiply them by FP8 activations.
The compatible B200/B300 roof is therefore FP8-rate, not the larger pure-FP4 peak.

| Model | Dense/shared matrix format | Routed expert matrix format | Evidence status |
|---|---|---|---|
| DeepSeek-V4-Flash-0731 | fp8_e4m3_x_fp8_e4m3 | mxfp4_e2m1_x_fp8_e4m3 | published DeepSeek report and pinned config |
| DeepSeek-V4-Pro-0813 | fp8_e4m3_x_fp8_e4m3 | mxfp4_e2m1_x_fp8_e4m3 | published DeepSeek report and pinned config |
| Kimi-K3 | bf16_x_bf16 | mxfp4_e2m1_x_mxfp8_e4m3 | mixed published checkpoint/README and derived classification |
| Qwen3-8B | bf16_x_bf16 | not applicable | released BF16 baseline |

## Required operating points

The table uses the no-speculation scenario. `GPU` is the fastest feasible B200/B300
configuration at the same active microbatch; ratios above 1 favor ROM. ROM batch
is per pipeline stage, so its resident session count is batch × stages.

| Model | Context | Batch/stage | ROM residents | ROM user tok/s | Fastest GPU | GPU user tok/s | Speed ratio | Cheapest partial-TCO GPU | Partial-TCO ratio | ROM bind |
|---|---:|---:|---:|---:|---|---:|---:|---|---:|---|
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | 2 | 3,246.0 | NVIDIA-B300-x8 | 1,673.4 | 1.94× | NVIDIA-B200-x2 | 1.30× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | 16 | 412.3 | NVIDIA-B300-x16 | 963.6 | 0.43× | NVIDIA-B200-x2 | 0.52× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | 64 | 103.2 | NVIDIA-B300-x16 | 482.2 | 0.21× | NVIDIA-B200-x2 | 0.35× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | 128 | 51.6 | NVIDIA-B300-x16 | 343.5 | 0.15× | NVIDIA-B200-x2 | 0.25× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 200,000 | 128 | 256 | 25.8 | NVIDIA-B300-x16 | 265.7 | 0.10× | NVIDIA-B200-x2 | 0.16× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | 2 | 1,351.0 | NVIDIA-B300-x8 | 1,648.3 | 0.82× | NVIDIA-B200-x2 | 0.56× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | 16 | 170.0 | NVIDIA-B300-x16 | 928.5 | 0.18× | NVIDIA-B200-x2 | 0.23× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | 64 | 42.5 | NVIDIA-B300-x16 | 448.2 | 0.09× | NVIDIA-B200-x2 | 0.16× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | 128 | 21.3 | NVIDIA-B300-x16 | 310.0 | 0.07× | NVIDIA-B200-x4 | 0.12× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 128 | 256 | — | NVIDIA-B300-x16 | 227.7 | — | NVIDIA-B200-x4 | — | capacity_C7_C8_C9 |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | 6 | 1,080.1 | NVIDIA-B300-x16 | 608.9 | 1.77× | NVIDIA-B300-x4 | 2.51× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | 48 | 136.3 | NVIDIA-B300-x16 | 354.3 | 0.38× | NVIDIA-B200-x8 | 0.84× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | 192 | 34.1 | NVIDIA-B300-x16 | 142.9 | 0.24× | NVIDIA-B200-x8 | 0.58× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | 384 | 17.1 | NVIDIA-B300-x16 | 92.2 | 0.18× | NVIDIA-B200-x8 | 0.46× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 200,000 | 128 | 768 | 8.5 | NVIDIA-B300-x16 | 66.4 | 0.13× | NVIDIA-B200-x8 | 0.31× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | 6 | 596.4 | NVIDIA-B300-x16 | 606.3 | 0.98× | NVIDIA-B300-x4 | 1.40× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | 48 | 75.0 | NVIDIA-B300-x16 | 347.3 | 0.22× | NVIDIA-B200-x8 | 0.47× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | 192 | 18.8 | NVIDIA-B300-x16 | 138.4 | 0.14× | NVIDIA-B200-x8 | 0.33× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | 384 | 9.4 | NVIDIA-B300-x16 | 88.5 | 0.11× | NVIDIA-B200-x8 | 0.26× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 128 | 768 | — | NVIDIA-B300-x16 | 62.6 | — | NVIDIA-B300-x8 | — | capacity_C7_C8_C9 |
| Kimi-K3 | 200,000 | 1 | 11 | 332.8 | NVIDIA-B300-x16 | 324.3 | 1.03× | NVIDIA-B300-x8 | 2.74× | rom_full_array_read_C4 |
| Kimi-K3 | 200,000 | 8 | 88 | 70.0 | NVIDIA-B300-x16 | 161.0 | 0.43× | NVIDIA-B300-x8 | 1.36× | compute_C5 |
| Kimi-K3 | 200,000 | 32 | 352 | 17.5 | NVIDIA-B300-x16 | 64.9 | 0.27× | NVIDIA-B300-x8 | 0.89× | compute_C5 |
| Kimi-K3 | 200,000 | 64 | 704 | 8.8 | NVIDIA-B300-x16 | 42.1 | 0.21× | NVIDIA-B300-x8 | 0.69× | compute_C5 |
| Kimi-K3 | 200,000 | 128 | 1,408 | — | NVIDIA-B300-x16 | 29.8 | — | NVIDIA-B300-x8 | — | capacity_C7_C8_C9 |
| Kimi-K3 | 1,000,000 | 1 | 11 | 210.3 | NVIDIA-B300-x16 | 309.1 | 0.68× | NVIDIA-B300-x8 | 1.85× | kv_beachfront_C8 |
| Kimi-K3 | 1,000,000 | 8 | 88 | 26.4 | NVIDIA-B300-x16 | 134.7 | 0.20× | NVIDIA-B300-x8 | 0.63× | kv_beachfront_C8 |
| Kimi-K3 | 1,000,000 | 32 | 352 | — | NVIDIA-B300-x16 | 49.4 | — | NVIDIA-B200-x16 | — | capacity_C7_C8_C9 |
| Kimi-K3 | 1,000,000 | 64 | 704 | — | NVIDIA-B300-x16 | 29.9 | — | NVIDIA-B200-x16 | — | capacity_C7_C8_C9 |
| Kimi-K3 | 1,000,000 | 128 | 1,408 | — | NVIDIA-B300-x16 | 18.9 | — | NVIDIA-B300-x16 | — | capacity_C7_C8_C9 |
| Qwen3-8B | 8,192 | 1 | 1 | 3,279.6 | NVIDIA-B300-x16 | 1,759.8 | 1.86× | NVIDIA-B200-x1 | 1.26× | rom_full_array_read_C4 |
| Qwen3-8B | 8,192 | 8 | 8 | 416.1 | NVIDIA-B300-x16 | 1,399.3 | 0.30× | NVIDIA-B200-x1 | 0.25× | kv_beachfront_C8 |
| Qwen3-8B | 8,192 | 32 | 32 | 104.2 | NVIDIA-B300-x16 | 822.1 | 0.13× | NVIDIA-B200-x1 | 0.14× | kv_beachfront_C8 |
| Qwen3-8B | 8,192 | 64 | 64 | 52.1 | NVIDIA-B300-x16 | 530.3 | 0.10× | NVIDIA-B200-x1 | 0.12× | kv_beachfront_C8 |
| Qwen3-8B | 8,192 | 128 | 128 | 26.0 | NVIDIA-B300-x16 | 310.2 | 0.08× | NVIDIA-B200-x2 | 0.11× | kv_beachfront_C8 |

## Same-microbatch B200 versus B300 family view

This isolates GPU generation from cluster-size selection. Each family column is
the fastest feasible x1/x2/x4/x8/x16 point at the same active microbatch. Ratios above
1 favor ROM; this view does not match the ROM pipeline's larger resident population.

| Model | Context | Batch/stage | ROM user tok/s | Best B200 user tok/s | ROM/B200 | Best B300 user tok/s | ROM/B300 |
|---|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | 3,246.0 | 1,656.5 | 1.96× | 1,673.4 | 1.94× |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | 412.3 | 947.3 | 0.44× | 963.6 | 0.43× |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | 51.6 | 336.4 | 0.15× | 343.5 | 0.15× |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | 1,351.0 | 1,632.0 | 0.83× | 1,648.3 | 0.82× |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | 170.0 | 913.3 | 0.19× | 928.5 | 0.18× |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | 21.3 | 304.2 | 0.07× | 310.0 | 0.07× |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | 1,080.1 | 600.5 | 1.80× | 608.9 | 1.77× |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | 136.3 | 347.6 | 0.39× | 354.3 | 0.38× |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | 17.1 | 90.1 | 0.19× | 92.2 | 0.18× |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | 596.4 | 597.1 | 1.00× | 606.3 | 0.98× |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | 75.0 | 340.8 | 0.22× | 347.3 | 0.22× |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | 9.4 | 86.6 | 0.11× | 88.5 | 0.11× |
| Kimi-K3 | 200,000 | 1 | 332.8 | 321.4 | 1.04× | 324.3 | 1.03× |
| Kimi-K3 | 200,000 | 8 | 70.0 | 158.4 | 0.44× | 161.0 | 0.43× |
| Kimi-K3 | 200,000 | 64 | 8.8 | 41.3 | 0.21× | 42.1 | 0.21× |
| Kimi-K3 | 1,000,000 | 1 | 210.3 | 306.5 | 0.69× | 309.1 | 0.68× |
| Kimi-K3 | 1,000,000 | 8 | 26.4 | 132.9 | 0.20× | 134.7 | 0.20× |
| Kimi-K3 | 1,000,000 | 64 | — | 29.5 | — | 29.9 | — |
| Qwen3-8B | 8,192 | 1 | 3,279.6 | 1,746.8 | 1.88× | 1,759.8 | 1.86× |
| Qwen3-8B | 8,192 | 8 | 416.1 | 1,390.1 | 0.30× | 1,399.3 | 0.30× |
| Qwen3-8B | 8,192 | 64 | 52.1 | 527.9 | 0.10× | 530.3 | 0.10× |

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
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | 3,246.0 | 1,528.1 | 0.47× | 1,673.4 | 3,034.8 | 1.81× | 0.50× |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | 412.3 | 191.5 | 0.46× | 963.6 | 1,100.8 | 1.14× | 0.17× |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | 51.6 | 23.9 | 0.46× | 343.5 | 507.8 | 1.48× | 0.05× |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | 1,351.0 | 628.9 | 0.47× | 1,648.3 | 2,943.7 | 1.79× | 0.21× |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | 170.0 | 78.7 | 0.46× | 928.5 | 1,010.1 | 1.09× | 0.08× |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | 21.3 | 9.8 | 0.46× | 310.0 | 381.4 | 1.23× | 0.03× |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | 1,080.1 | 504.9 | 0.47× | 608.9 | 1,160.6 | 1.91× | 0.43× |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | 136.3 | 63.2 | 0.46× | 354.3 | 309.9 | 0.87× | 0.20× |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | 17.1 | 7.9 | 0.46× | 92.2 | 136.1 | 1.48× | 0.06× |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | 596.4 | 277.4 | 0.47× | 606.3 | 1,140.8 | 1.88× | 0.24× |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | 75.0 | 34.7 | 0.46× | 347.3 | 298.8 | 0.86× | 0.12× |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | 9.4 | 4.3 | 0.46× | 88.5 | 120.5 | 1.36× | 0.04× |
| Kimi-K3 | 200,000 | 1 | 332.8 | 259.2 | 0.78× | 324.3 | 555.4 | 1.71× | 0.47× |
| Kimi-K3 | 200,000 | 8 | 70.0 | 32.4 | 0.46× | 161.0 | 146.6 | 0.91× | 0.22× |
| Kimi-K3 | 200,000 | 64 | 8.8 | 4.1 | 0.46× | 42.1 | 54.3 | 1.29× | 0.07× |
| Kimi-K3 | 1,000,000 | 1 | 210.3 | 101.2 | 0.48× | 309.1 | 474.1 | 1.53× | 0.21× |
| Kimi-K3 | 1,000,000 | 8 | 26.4 | 12.7 | 0.48× | 134.7 | 107.6 | 0.80× | 0.12× |
| Kimi-K3 | 1,000,000 | 64 | — | — | — | 29.9 | 26.2 | 0.88× | — |

## Resident-concurrency-matched B200/B300 comparison

A ROM pipeline holds one microbatch at every stage. Here each GPU is simulated
at the resulting total resident-session count, and the smallest feasible 1/2/4/8/16
configuration is shown. This is the capacity-matched service comparison.

| Model | Context | ROM B/stage | Resident sessions | ROM user tok/s | Smallest B200 | user tok/s | Smallest B300 | user tok/s | Partial-TCO ratio vs cheapest GPU |
|---|---:|---:|---:|---:|---|---:|---|---:|---:|
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | 2 | 3,246.0 | NVIDIA-B200-x2 | 595.9 | NVIDIA-B300-x1 | 321.2 | 0.86× |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | 16 | 412.3 | NVIDIA-B200-x2 | 150.8 | NVIDIA-B300-x1 | 78.5 | 0.43× |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | 128 | 51.6 | NVIDIA-B200-x2 | 51.8 | NVIDIA-B300-x1 | 27.0 | 0.16× |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | 2 | 1,351.0 | NVIDIA-B200-x2 | 571.2 | NVIDIA-B300-x1 | 306.9 | 0.37× |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | 16 | 170.0 | NVIDIA-B200-x2 | 138.7 | NVIDIA-B300-x1 | 71.9 | 0.19× |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | 128 | 21.3 | NVIDIA-B200-x4 | 81.7 | NVIDIA-B300-x4 | 82.9 | 0.08× |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | 6 | 1,080.1 | NVIDIA-B200-x8 | 306.0 | NVIDIA-B300-x4 | 168.6 | 0.91× |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | 48 | 136.3 | NVIDIA-B200-x8 | 68.6 | NVIDIA-B300-x4 | 35.9 | 0.51× |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | 384 | 17.1 | NVIDIA-B200-x8 | 33.9 | NVIDIA-B300-x8 | 34.5 | 0.13× |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | 6 | 596.4 | NVIDIA-B200-x8 | 298.7 | NVIDIA-B300-x4 | 164.2 | 0.51× |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | 48 | 75.0 | NVIDIA-B200-x8 | 65.8 | NVIDIA-B300-x8 | 67.0 | 0.29× |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | 384 | 9.4 | infeasible | — | NVIDIA-B300-x16 | 42.6 | 0.14× |
| Kimi-K3 | 200,000 | 1 | 11 | 332.8 | NVIDIA-B200-x16 | 130.2 | NVIDIA-B300-x8 | 84.1 | 0.73× |
| Kimi-K3 | 200,000 | 8 | 88 | 70.0 | NVIDIA-B200-x16 | 34.8 | NVIDIA-B300-x8 | 21.7 | 0.59× |
| Kimi-K3 | 200,000 | 64 | 704 | 8.8 | infeasible | — | NVIDIA-B300-x16 | 13.1 | 0.25× |
| Kimi-K3 | 1,000,000 | 1 | 11 | 210.3 | NVIDIA-B200-x16 | 107.0 | NVIDIA-B300-x8 | 66.8 | 0.58× |
| Kimi-K3 | 1,000,000 | 8 | 88 | 26.4 | infeasible | — | NVIDIA-B300-x16 | 24.1 | 0.40× |
| Kimi-K3 | 1,000,000 | 64 | 704 | — | infeasible | — | infeasible | — | — |
| Qwen3-8B | 8,192 | 1 | 1 | 3,279.6 | NVIDIA-B200-x1 | 323.6 | NVIDIA-B300-x1 | 322.5 | 1.26× |
| Qwen3-8B | 8,192 | 8 | 8 | 416.1 | NVIDIA-B200-x1 | 208.3 | NVIDIA-B300-x1 | 207.7 | 0.25× |
| Qwen3-8B | 8,192 | 64 | 64 | 52.1 | NVIDIA-B200-x1 | 54.1 | NVIDIA-B300-x1 | 54.0 | 0.12× |

## Batch optima and speed-superiority bands

A speed-superiority batch beats the fastest per-user GPU point at *any* batch,
not merely the GPU at the same batch. Bands are evaluated on the dense 1..256 sweep;
all optima are searched exhaustively over integer batches through local capacity.

Balanced maximizes the geometric mean of normalized per-user speed and aggregate
throughput. Cost is partial TCO: hardware/NRE amortization plus active electricity;
it excludes staffing, financing, networking, floor space, maintenance, and spares.

| Model | Context | Scenario | ROM latency B | ROM balanced B | ROM throughput B | ROM partial-TCO B | GPU latency arch/B | GPU balanced arch/B | GPU throughput arch/B | GPU partial-TCO arch/B | ROM superiority batches |
|---|---:|---|---:|---:|---:|---:|---|---|---|---|---|
| DeepSeek-V4-Flash-0731 | 200,000 | no_speculation | 1 | 1 | 468 | 468 | NVIDIA-B300-x8/B1 | NVIDIA-B300-x16/B463 | NVIDIA-B300-x8/B2704 | NVIDIA-B200-x8/B1601 | 1-1 |
| DeepSeek-V4-Flash-0731 | 200,000 | speculative_midpoint | 1 | 1 | 468 | 468 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B80 | NVIDIA-B300-x8/B2704 | NVIDIA-B200-x4/B682 | none |
| DeepSeek-V4-Flash-0731 | 1,000,000 | no_speculation | 1 | 1 | 94 | 94 | NVIDIA-B300-x8/B1 | NVIDIA-B300-x16/B259 | NVIDIA-B300-x16/B1133 | NVIDIA-B300-x8/B542 | none |
| DeepSeek-V4-Flash-0731 | 1,000,000 | speculative_midpoint | 1 | 1 | 94 | 94 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B2 | NVIDIA-B300-x16/B1133 | NVIDIA-B200-x8/B321 | none |
| DeepSeek-V4-Pro-0813 | 200,000 | no_speculation | 1 | 1 | 340 | 340 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B998 | NVIDIA-B300-x16/B3224 | NVIDIA-B300-x8/B1169 | 1-1 |
| DeepSeek-V4-Pro-0813 | 200,000 | speculative_midpoint | 1 | 1 | 340 | 340 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B170 | NVIDIA-B300-x8/B1169 | NVIDIA-B300-x8/B1169 | none |
| DeepSeek-V4-Pro-0813 | 1,000,000 | no_speculation | 1 | 1 | 68 | 68 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B7 | NVIDIA-B300-x16/B647 | NVIDIA-B300-x16/B647 | none |
| DeepSeek-V4-Pro-0813 | 1,000,000 | speculative_midpoint | 1 | 1 | 68 | 68 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B647 | NVIDIA-B300-x8/B234 | none |
| Kimi-K3 | 200,000 | no_speculation | 1 | 2 | 81 | 81 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B5 | NVIDIA-B300-x16/B804 | NVIDIA-B300-x16/B804 | 1-1 |
| Kimi-K3 | 200,000 | speculative_midpoint | 1 | 1 | 81 | 81 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B804 | NVIDIA-B200-x16/B320 | none |
| Kimi-K3 | 1,000,000 | no_speculation | 1 | 1 | 17 | 17 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B4 | NVIDIA-B300-x16/B181 | NVIDIA-B300-x16/B181 | none |
| Kimi-K3 | 1,000,000 | speculative_midpoint | 1 | 1 | 17 | 17 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B181 | NVIDIA-B200-x16/B72 | none |
| Qwen3-8B | 8,192 | no_speculation | 1 | 1 | 286 | 286 | NVIDIA-B300-x16/B1 | NVIDIA-B300-x16/B26 | NVIDIA-B300-x16/B3419 | NVIDIA-B200-x4/B522 | 1-1 |

## Interpretation boundary

- The curves verify accounting and reveal which constraint binds under each input set.
- They do **not** verify the assumed ROM density, 100 TB/s read path, format-specific MAC
  roofs, wafer yield, package HBM capacity, or cost. Sensitivity and circuit/NoC
  work must survive before any go decision.
- GPU marketing peaks are derated explicitly; production traces remain necessary to
  replace engaged-bandwidth, collective, and speculative-acceptance assumptions.
- Kimi K3 uses an optimized FP8 latent MLA cache. The reference BF16 expanded cache
  is a pessimistic sensitivity case, not silently mixed into this table.
- Qwen3-8B uses a conservative assumed BF16 full-GQA KV cache at 8K and no
  speculative scenario. It is a dense control, not an additional product target.
