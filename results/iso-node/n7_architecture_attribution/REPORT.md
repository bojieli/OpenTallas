# N7 Architecture Attribution

> N7 ROM/SRAM + HBM2e-era interfaces versus A100 80GB; WSE-2 only as wafer feasibility anchor

This is an evidence-bounded decode simulation, not a fabricated-silicon or
product-performance claim. `Low` and `high` below are deterministic hardware
envelopes, not statistical confidence intervals.

## Storage and execution contract

| Architecture | Devices available | Weight store | Mutable KV store | Weight capacity/device | KV capacity/device | Raw weight BW/device | Raw KV BW/device | Deployment |
|---|---:|---|---|---:|---:|---:|---:|---|
| NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x1 | 1 | HBM2e | HBM2e | 80.0 GB | 80.0 GB | 2.04 TB/s | 2.04 TB/s | a100_packed_hbm_bf16_execute |
| NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x2 | 2 | HBM2e | HBM2e | 80.0 GB | 80.0 GB | 2.04 TB/s | 2.04 TB/s | a100_packed_hbm_bf16_execute |
| NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x4 | 4 | HBM2e | HBM2e | 80.0 GB | 80.0 GB | 2.04 TB/s | 2.04 TB/s | a100_packed_hbm_bf16_execute |
| NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x8 | 8 | HBM2e | HBM2e | 80.0 GB | 80.0 GB | 2.04 TB/s | 2.04 TB/s | a100_packed_hbm_bf16_execute |
| NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x16 | 16 | HBM2e | HBM2e | 80.0 GB | 80.0 GB | 2.04 TB/s | 2.04 TB/s | a100_packed_hbm_bf16_execute |
| NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x32 | 32 | HBM2e | HBM2e | 80.0 GB | 80.0 GB | 2.04 TB/s | 2.04 TB/s | a100_packed_hbm_bf16_execute |
| NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 64 | HBM2e | HBM2e | 80.0 GB | 80.0 GB | 2.04 TB/s | 2.04 TB/s | a100_packed_hbm_bf16_execute |
| NVIDIA-A100-SXM-80GB-BF16-resident-x1 | 1 | HBM2e | HBM2e | 80.0 GB | 80.0 GB | 2.04 TB/s | 2.04 TB/s | a100_bf16_expanded |
| NVIDIA-A100-SXM-80GB-BF16-resident-x2 | 2 | HBM2e | HBM2e | 80.0 GB | 80.0 GB | 2.04 TB/s | 2.04 TB/s | a100_bf16_expanded |
| NVIDIA-A100-SXM-80GB-BF16-resident-x4 | 4 | HBM2e | HBM2e | 80.0 GB | 80.0 GB | 2.04 TB/s | 2.04 TB/s | a100_bf16_expanded |
| NVIDIA-A100-SXM-80GB-BF16-resident-x8 | 8 | HBM2e | HBM2e | 80.0 GB | 80.0 GB | 2.04 TB/s | 2.04 TB/s | a100_bf16_expanded |
| NVIDIA-A100-SXM-80GB-BF16-resident-x16 | 16 | HBM2e | HBM2e | 80.0 GB | 80.0 GB | 2.04 TB/s | 2.04 TB/s | a100_bf16_expanded |
| NVIDIA-A100-SXM-80GB-BF16-resident-x32 | 32 | HBM2e | HBM2e | 80.0 GB | 80.0 GB | 2.04 TB/s | 2.04 TB/s | a100_bf16_expanded |
| NVIDIA-A100-SXM-80GB-BF16-resident-x64 | 64 | HBM2e | HBM2e | 80.0 GB | 80.0 GB | 2.04 TB/s | 2.04 TB/s | a100_bf16_expanded |
| ROM-wafer-N7-HBM2e-conservative | 64 | mask_ROM_N7 | HBM2e | 57.8 GB | 256.0 GB | 970.72 TB/s | 6.52 TB/s | official_packed |
| ROM-wafer-N7-HBM2e-central | 64 | mask_ROM_N7 | HBM2e | 170.4 GB | 512.0 GB | 2,662.56 TB/s | 13.05 TB/s | official_packed |
| ROM-wafer-N7-HBM2e-aggressive | 64 | mask_ROM_N7 | HBM2e | 408.6 GB | 768.0 GB | 6,101.70 TB/s | 19.57 TB/s | official_packed |
| N7-SRAM-rich-Graphcore-style-derived-control | 128 | SRAM_N7 | SRAM_N7 | 35.4 GB | 15.2 GB | 1,867.53 TB/s | 800.37 TB/s | official_packed |

GPU HBM capacity and bandwidth are shared by weights and KV. ROM weight
capacity/bandwidth and mutable HBM KV capacity/bandwidth are physically
separate. The SRAM-rich control uses a static 70% weight / 30% KV split.

## Exact model work and deployment storage

| Model | Official checkpoint | Deployment representation | Resident bytes | Tensor ops/token | At context | Dense / routed format |
|---|---:|---|---:|---:|---:|---|
| DeepSeek-V4-Flash-0731 | 166.9 GB | a100_bf16_expanded | 608.5 GB | 135.2 Gop | 1,000,000 | fp8_e4m3_x_fp8_e4m3 / mxfp4_e2m1_x_fp8_e4m3 |
| DeepSeek-V4-Flash-0731 | 166.9 GB | a100_packed_hbm_bf16_execute | 166.9 GB | 135.2 Gop | 1,000,000 | fp8_e4m3_x_fp8_e4m3 / mxfp4_e2m1_x_fp8_e4m3 |
| DeepSeek-V4-Flash-0731 | 166.9 GB | official_packed | 166.9 GB | 135.2 Gop | 1,000,000 | fp8_e4m3_x_fp8_e4m3 / mxfp4_e2m1_x_fp8_e4m3 |
| DeepSeek-V4-Pro-0813 | 892.7 GB | a100_bf16_expanded | 3,301.2 GB | 294.2 Gop | 1,000,000 | fp8_e4m3_x_fp8_e4m3 / mxfp4_e2m1_x_fp8_e4m3 |
| DeepSeek-V4-Pro-0813 | 892.7 GB | a100_packed_hbm_bf16_execute | 892.7 GB | 294.2 Gop | 1,000,000 | fp8_e4m3_x_fp8_e4m3 / mxfp4_e2m1_x_fp8_e4m3 |
| DeepSeek-V4-Pro-0813 | 892.7 GB | official_packed | 892.7 GB | 294.2 Gop | 1,000,000 | fp8_e4m3_x_fp8_e4m3 / mxfp4_e2m1_x_fp8_e4m3 |
| Qwen3-8B | 16.4 GB | a100_bf16_expanded | 16.4 GB | 15.1 Gop | 32,768 | bf16_x_bf16 / None |
| Qwen3-8B | 16.4 GB | a100_packed_hbm_bf16_execute | 16.4 GB | 15.1 Gop | 32,768 | bf16_x_bf16 / None |
| Qwen3-8B | 16.4 GB | official_packed | 16.4 GB | 15.1 Gop | 32,768 | bf16_x_bf16 / None |
| DeepSeek-V4.1-Flash | 510.3 GB | a100_bf16_expanded | 1,526.5 GB | 56.5 Gop | 1,000,000 | fp8_e4m3_x_fp8_e4m3 / mxfp4_e2m1_x_fp8_e4m3 |
| DeepSeek-V4.1-Flash | 510.3 GB | a100_packed_hbm_bf16_execute | 510.3 GB | 56.5 Gop | 1,000,000 | fp8_e4m3_x_fp8_e4m3 / mxfp4_e2m1_x_fp8_e4m3 |
| DeepSeek-V4.1-Flash | 510.3 GB | official_packed | 510.3 GB | 56.5 Gop | 1,000,000 | fp8_e4m3_x_fp8_e4m3 / mxfp4_e2m1_x_fp8_e4m3 |
| DeepSeek-V4.1-Flash-engram-host | 307.5 GB | a100_bf16_expanded | 1,133.3 GB | 56.5 Gop | 1,000,000 | fp8_e4m3_x_fp8_e4m3 / mxfp4_e2m1_x_fp8_e4m3 |
| DeepSeek-V4.1-Flash-engram-host | 307.5 GB | a100_packed_hbm_bf16_execute | 307.5 GB | 56.5 Gop | 1,000,000 | fp8_e4m3_x_fp8_e4m3 / mxfp4_e2m1_x_fp8_e4m3 |
| DeepSeek-V4.1-Flash-engram-host | 307.5 GB | official_packed | 307.5 GB | 56.5 Gop | 1,000,000 | fp8_e4m3_x_fp8_e4m3 / mxfp4_e2m1_x_fp8_e4m3 |

## Mechanical consistency audit

| Status | Checks | Max weight/shared-HBM service | Max KV service | Max compute service | Max cooling |
|---|---:|---:|---:|---:|---:|
| PASS | 28,746 | 100.0% | 94.6% | 84.1% | 100.0% |

The service columns are component-time occupancy divided by the final
thermal-adjusted interval. GPU weight and KV time are added because
they share HBM; ROM/SRAM weight and KV services remain separate.
- Generated arithmetic identities and loose published/configured ceilings only.
- Auxiliary vector/softmax/top-k/Sinkhorn rates are break-even requirements, not configured or measured service ceilings, and are excluded from the utilization maxima.
- A passing audit is not evidence for ROM macro timing, simultaneous full-array activity, NoC timing, power delivery, package, yield, or model accuracy.

## Central-envelope 200K results

`GPU` is the fastest feasible allowed GPU cluster at the same active
microbatch. The resident-matched ratio instead runs the GPU at `batch ×
wafer stages`. Ratios above one favor the wafer.
Partial TCO uses assumed acquisition cost, NRE allocation, utilization,
electricity, and PUE. It is shown with enough precision to audit the
arithmetic, but it is not a measured vendor-cost or profitability result.

| Model | B/stage | Stages | Residents | ROM user tok/s | GPU | GPU user tok/s | Same-B ratio | Resident-matched ratio | ROM $/M tok | Bind |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| DeepSeek-V4-Flash-0731 | 1 | 1 | 1 | 8,050.1 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x16 | 614.4 | 13.10× | 13.10× | 0.3288 | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 8 | 1 | 8 | 2,084.7 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 434.0 | 4.80× | 4.80× | 0.1587 | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 32 | 1 | 32 | 588.8 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 264.4 | 2.23× | 2.23× | 0.1405 | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 64 | 1 | 64 | 300.9 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 182.6 | 1.65× | 1.65× | 0.1374 | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 1 | 6 | 6 | 4,506.0 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x32 | 248.8 | 18.11× | 22.77× | 0.3735 | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 8 | 6 | 48 | 1,001.4 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 183.9 | 5.45× | 12.96× | 0.2121 | compute_C5 |
| DeepSeek-V4-Pro-0813 | 32 | 6 | 192 | 271.8 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 99.3 | 2.74× | 8.44× | 0.1957 | compute_C5 |
| DeepSeek-V4-Pro-0813 | 64 | 6 | 384 | 137.9 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 64.3 | 2.15× | 6.81× | 0.1930 | compute_C5 |
| DeepSeek-V4.1-Flash | 1 | 3 | 3 | 9,359.2 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x32 | 564.5 | 16.58× | 18.70× | 0.2005 | collective_floor_C6 |
| DeepSeek-V4.1-Flash | 8 | 3 | 24 | 2,890.9 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 402.8 | 7.18× | 10.75× | 0.0816 | compute_C5 |
| DeepSeek-V4.1-Flash | 32 | 3 | 96 | 857.9 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 231.3 | 3.71× | 7.23× | 0.0689 | compute_C5 |
| DeepSeek-V4.1-Flash | 64 | 3 | 192 | 442.8 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 153.0 | 2.89× | 5.81× | 0.0667 | compute_C5 |
| DeepSeek-V4.1-Flash-engram-host | 1 | 2 | 2 | 9,906.5 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x32 | 564.5 | 17.55× | 18.66× | 0.2091 | collective_floor_C6 |
| DeepSeek-V4.1-Flash-engram-host | 8 | 2 | 16 | 3,069.3 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 402.8 | 7.62× | 9.52× | 0.0846 | compute_C5 |
| DeepSeek-V4.1-Flash-engram-host | 32 | 2 | 64 | 911.7 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 231.3 | 3.94× | 5.96× | 0.0713 | compute_C5 |
| DeepSeek-V4.1-Flash-engram-host | 64 | 2 | 128 | 470.7 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 153.0 | 3.08× | 4.76× | 0.0691 | compute_C5 |

## Unpriced auxiliary-path break-even requirements at 200K

The tensor-rate results above do not price normalization, nonlinear,
attention-softmax score handling, index-score reduction, top-k selection,
compressor pooling, or Sinkhorn execution. The table therefore reports
a requirement, not an achieved hardware rate: each value is the aggregate
category service needed by the bottleneck wafer stage or complete GPU
cluster to fit inside the already reported initiation interval. Categories
have different operation costs and cannot be summed. Dependencies, shared
resources, activation quantization/scaling, RoPE, hyper-connection
elementwise work, and dispatch can require additional time. The generated
JSON also emits the 10× rate that would limit each category alone to 10%
serialized overhead. Until `COMP-01` supplies executable service times, all
token rates and ROM/GPU ratios remain conditional on this gate.

| Model | B | Architecture | Attention scores | Index scores | Normalization | Nonlinear | Top-k candidates | Sinkhorn element-iterations |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | ROM-wafer-N7-HBM2e-central | 24.47 Gitem/s | 540.97 Gitem/s | 14.74 Gitem/s | 5.05 Gitem/s | 8.45 Gitem/s | 221.54 Mitem/s |
| DeepSeek-V4-Flash-0731 | 1 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x16 | 1.87 Gitem/s | 41.29 Gitem/s | 1.13 Gitem/s | 385.49 Mitem/s | 645.09 Mitem/s | 16.91 Mitem/s |
| DeepSeek-V4-Flash-0731 | 8 | ROM-wafer-N7-HBM2e-central | 50.70 Gitem/s | 1.12 Titem/s | 30.54 Gitem/s | 10.46 Gitem/s | 17.51 Gitem/s | 458.97 Mitem/s |
| DeepSeek-V4-Flash-0731 | 8 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 10.55 Gitem/s | 233.34 Gitem/s | 6.36 Gitem/s | 2.18 Gitem/s | 3.65 Gitem/s | 95.56 Mitem/s |
| DeepSeek-V4-Flash-0731 | 32 | ROM-wafer-N7-HBM2e-central | 57.27 Gitem/s | 1.27 Titem/s | 34.51 Gitem/s | 11.82 Gitem/s | 19.78 Gitem/s | 518.51 Mitem/s |
| DeepSeek-V4-Flash-0731 | 32 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 25.72 Gitem/s | 568.63 Gitem/s | 15.50 Gitem/s | 5.31 Gitem/s | 8.88 Gitem/s | 232.87 Mitem/s |
| DeepSeek-V4-Flash-0731 | 64 | ROM-wafer-N7-HBM2e-central | 58.54 Gitem/s | 1.29 Titem/s | 35.27 Gitem/s | 12.08 Gitem/s | 20.22 Gitem/s | 529.97 Mitem/s |
| DeepSeek-V4-Flash-0731 | 64 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 35.52 Gitem/s | 785.32 Gitem/s | 21.40 Gitem/s | 7.33 Gitem/s | 12.27 Gitem/s | 321.61 Mitem/s |
| DeepSeek-V4-Pro-0813 | 1 | ROM-wafer-N7-HBM2e-central | 55.70 Gitem/s | 437.87 Gitem/s | 24.66 Gitem/s | 6.59 Gitem/s | 6.84 Gitem/s | 192.66 Mitem/s |
| DeepSeek-V4-Pro-0813 | 1 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x32 | 2.77 Gitem/s | 23.89 Gitem/s | 1.25 Gitem/s | 332.20 Mitem/s | 373.21 Mitem/s | 9.71 Mitem/s |
| DeepSeek-V4-Pro-0813 | 8 | ROM-wafer-N7-HBM2e-central | 98.09 Gitem/s | 771.13 Gitem/s | 43.43 Gitem/s | 11.60 Gitem/s | 12.05 Gitem/s | 339.30 Mitem/s |
| DeepSeek-V4-Pro-0813 | 8 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 16.37 Gitem/s | 141.21 Gitem/s | 7.36 Gitem/s | 1.96 Gitem/s | 2.21 Gitem/s | 57.42 Mitem/s |
| DeepSeek-V4-Pro-0813 | 32 | ROM-wafer-N7-HBM2e-central | 106.28 Gitem/s | 835.54 Gitem/s | 47.06 Gitem/s | 12.57 Gitem/s | 13.06 Gitem/s | 367.64 Mitem/s |
| DeepSeek-V4-Pro-0813 | 32 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 35.35 Gitem/s | 304.94 Gitem/s | 15.90 Gitem/s | 4.24 Gitem/s | 4.76 Gitem/s | 124.01 Mitem/s |
| DeepSeek-V4-Pro-0813 | 64 | ROM-wafer-N7-HBM2e-central | 107.78 Gitem/s | 847.33 Gitem/s | 47.72 Gitem/s | 12.75 Gitem/s | 13.24 Gitem/s | 372.83 Mitem/s |
| DeepSeek-V4-Pro-0813 | 64 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 45.77 Gitem/s | 394.81 Gitem/s | 20.58 Gitem/s | 5.49 Gitem/s | 6.17 Gitem/s | 160.56 Mitem/s |
| DeepSeek-V4.1-Flash | 1 | ROM-wafer-N7-HBM2e-central | 16.24 Gitem/s | 286.71 Gitem/s | 5.62 Gitem/s | 6.55 Gitem/s | 9.67 Gitem/s | 253.74 Mitem/s |
| DeepSeek-V4.1-Flash | 1 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x32 | 887.88 Mitem/s | 10.22 Gitem/s | 322.15 Mitem/s | 372.85 Mitem/s | 333.36 Mitem/s | 14.45 Mitem/s |
| DeepSeek-V4.1-Flash | 8 | ROM-wafer-N7-HBM2e-central | 39.89 Gitem/s | 704.30 Gitem/s | 13.82 Gitem/s | 16.08 Gitem/s | 23.75 Gitem/s | 623.30 Mitem/s |
| DeepSeek-V4.1-Flash | 8 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 5.07 Gitem/s | 58.32 Gitem/s | 1.84 Gitem/s | 2.13 Gitem/s | 1.90 Gitem/s | 82.50 Mitem/s |
| DeepSeek-V4.1-Flash | 32 | ROM-wafer-N7-HBM2e-central | 47.27 Gitem/s | 834.49 Gitem/s | 16.37 Gitem/s | 19.05 Gitem/s | 28.14 Gitem/s | 738.52 Mitem/s |
| DeepSeek-V4.1-Flash | 32 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 11.64 Gitem/s | 133.94 Gitem/s | 4.22 Gitem/s | 4.89 Gitem/s | 4.37 Gitem/s | 189.47 Mitem/s |
| DeepSeek-V4.1-Flash | 64 | ROM-wafer-N7-HBM2e-central | 48.77 Gitem/s | 861.06 Gitem/s | 16.89 Gitem/s | 19.66 Gitem/s | 29.03 Gitem/s | 762.04 Mitem/s |
| DeepSeek-V4.1-Flash | 64 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 15.40 Gitem/s | 177.23 Gitem/s | 5.59 Gitem/s | 6.47 Gitem/s | 5.78 Gitem/s | 250.71 Mitem/s |
| DeepSeek-V4.1-Flash-engram-host | 1 | ROM-wafer-N7-HBM2e-central | 16.30 Gitem/s | 191.06 Gitem/s | 6.45 Gitem/s | 6.57 Gitem/s | 5.97 Gitem/s | 254.75 Mitem/s |
| DeepSeek-V4.1-Flash-engram-host | 1 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x32 | 887.88 Mitem/s | 10.22 Gitem/s | 322.15 Mitem/s | 372.85 Mitem/s | 333.36 Mitem/s | 14.45 Mitem/s |
| DeepSeek-V4.1-Flash-engram-host | 8 | ROM-wafer-N7-HBM2e-central | 40.29 Gitem/s | 472.10 Gitem/s | 15.95 Gitem/s | 16.24 Gitem/s | 14.75 Gitem/s | 629.47 Mitem/s |
| DeepSeek-V4.1-Flash-engram-host | 8 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 5.07 Gitem/s | 58.32 Gitem/s | 1.84 Gitem/s | 2.13 Gitem/s | 1.90 Gitem/s | 82.50 Mitem/s |
| DeepSeek-V4.1-Flash-engram-host | 32 | ROM-wafer-N7-HBM2e-central | 47.82 Gitem/s | 560.40 Gitem/s | 18.93 Gitem/s | 19.28 Gitem/s | 17.51 Gitem/s | 747.20 Mitem/s |
| DeepSeek-V4.1-Flash-engram-host | 32 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 11.64 Gitem/s | 133.94 Gitem/s | 4.22 Gitem/s | 4.89 Gitem/s | 4.37 Gitem/s | 189.47 Mitem/s |
| DeepSeek-V4.1-Flash-engram-host | 64 | ROM-wafer-N7-HBM2e-central | 49.36 Gitem/s | 578.46 Gitem/s | 19.54 Gitem/s | 19.90 Gitem/s | 18.08 Gitem/s | 771.28 Mitem/s |
| DeepSeek-V4.1-Flash-engram-host | 64 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 15.40 Gitem/s | 177.23 Gitem/s | 5.59 Gitem/s | 6.47 Gitem/s | 5.78 Gitem/s | 250.71 Mitem/s |

## ROM component timing and occupancy at 200K

Times are seconds of bottleneck-stage service expressed in milliseconds.
Weight, KV, and compute may overlap; the layer collective is serialized;
pipeline efficiency and any thermal scaling produce the final interval.
The cross-stage entry is the initiation-interval serialization floor, not
the full end-to-end propagation latency. Occupancies are modeled service
time divided by the final interval, not silicon performance counters.

| Model | Envelope | B/stage | Stages | Final interval ms | User latency ms | Weight ms | KV ms | Compute ms | Collective ms | Cross-stage ms | Weight util | KV util | Compute util | Thermal × | Bind |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Flash-0731 | central | 1 | 1 | 0.1242 | 0.1242 | 0.0078 | 0.0420 | 0.0259 | 0.0698 | — | 6.3% | 33.8% | 20.9% | 1.000 | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | central | 8 | 1 | 0.4797 | 0.4797 | 0.0232 | 0.3358 | 0.2075 | 0.0959 | — | 4.8% | 70.0% | 43.2% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | central | 32 | 1 | 1.6984 | 1.6984 | 0.0600 | 1.3433 | 0.8298 | 0.1852 | — | 3.5% | 79.1% | 48.9% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | central | 64 | 1 | 3.3233 | 3.3233 | 0.0856 | 2.6866 | 1.6597 | 0.3044 | — | 2.6% | 80.8% | 49.9% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | aggressive | 1 | 1 | 0.0421 | 0.0421 | 0.0027 | 0.0230 | 0.0096 | 0.0169 | — | 6.5% | 54.8% | 22.8% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | aggressive | 8 | 1 | 0.2227 | 0.2227 | 0.0080 | 0.1844 | 0.0767 | 0.0272 | — | 3.6% | 82.8% | 34.5% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | aggressive | 32 | 1 | 0.8418 | 0.8418 | 0.0208 | 0.7374 | 0.3069 | 0.0623 | — | 2.5% | 87.6% | 36.5% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | aggressive | 64 | 1 | 1.6674 | 1.6674 | 0.0297 | 1.4749 | 0.6137 | 0.1091 | — | 1.8% | 88.5% | 36.8% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | central | 1 | 6 | 0.0365 | 0.2219 | 0.0050 | 0.0106 | 0.0152 | 0.0186 | 0.0003 | 13.6% | 29.1% | 41.7% | 1.000 | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | central | 8 | 6 | 0.1660 | 0.9986 | 0.0156 | 0.0849 | 0.1219 | 0.0302 | 0.0023 | 9.4% | 51.2% | 73.4% | 1.000 | compute_C5 |
| DeepSeek-V4-Pro-0813 | central | 32 | 6 | 0.6128 | 3.6794 | 0.0443 | 0.3397 | 0.4877 | 0.0702 | 0.0092 | 7.2% | 55.4% | 79.6% | 1.000 | compute_C5 |
| DeepSeek-V4-Pro-0813 | central | 64 | 6 | 1.2085 | 7.2537 | 0.0690 | 0.6795 | 0.9753 | 0.1236 | 0.0184 | 5.7% | 56.2% | 80.7% | 1.000 | compute_C5 |
| DeepSeek-V4-Pro-0813 | aggressive | 1 | 3 | 0.0214 | 0.0653 | 0.0033 | 0.0115 | 0.0104 | 0.0088 | 0.0003 | 15.4% | 53.9% | 48.6% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | aggressive | 8 | 3 | 0.1156 | 0.3478 | 0.0103 | 0.0922 | 0.0832 | 0.0176 | 0.0023 | 8.9% | 79.8% | 72.0% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | aggressive | 32 | 3 | 0.4385 | 1.3166 | 0.0294 | 0.3690 | 0.3330 | 0.0476 | 0.0092 | 6.7% | 84.1% | 75.9% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | aggressive | 64 | 3 | 0.8690 | 2.6082 | 0.0457 | 0.7380 | 0.6660 | 0.0876 | 0.0184 | 5.3% | 84.9% | 76.6% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4.1-Flash | central | 1 | 3 | 0.0353 | 0.1068 | 0.0031 | 0.0032 | 0.0087 | 0.0231 | 0.0002 | 8.7% | 9.1% | 24.7% | 1.000 | collective_floor_C6 |
| DeepSeek-V4.1-Flash | central | 8 | 3 | 0.1150 | 0.3459 | 0.0103 | 0.0257 | 0.0698 | 0.0337 | 0.0016 | 9.0% | 22.4% | 60.7% | 1.000 | compute_C5 |
| DeepSeek-V4.1-Flash | central | 32 | 3 | 0.3882 | 1.1656 | 0.0299 | 0.1029 | 0.2794 | 0.0700 | 0.0066 | 7.7% | 26.5% | 72.0% | 1.000 | compute_C5 |
| DeepSeek-V4.1-Flash | central | 64 | 3 | 0.7525 | 2.2584 | 0.0468 | 0.2058 | 0.5588 | 0.1185 | 0.0131 | 6.2% | 27.3% | 74.3% | 1.000 | compute_C5 |
| DeepSeek-V4.1-Flash | aggressive | 1 | 2 | 0.0131 | 0.0267 | 0.0016 | 0.0018 | 0.0044 | 0.0080 | 0.0002 | 12.3% | 13.5% | 33.8% | 1.000 | collective_floor_C6 |
| DeepSeek-V4.1-Flash | aggressive | 8 | 2 | 0.0521 | 0.1046 | 0.0052 | 0.0142 | 0.0355 | 0.0140 | 0.0016 | 10.0% | 27.2% | 68.1% | 1.000 | compute_C5 |
| DeepSeek-V4.1-Flash | aggressive | 32 | 2 | 0.1856 | 0.3717 | 0.0149 | 0.0567 | 0.1419 | 0.0344 | 0.0066 | 8.0% | 30.5% | 76.5% | 1.000 | compute_C5 |
| DeepSeek-V4.1-Flash | aggressive | 64 | 2 | 0.3637 | 0.7279 | 0.0233 | 0.1134 | 0.2839 | 0.0617 | 0.0131 | 6.4% | 31.2% | 78.0% | 1.000 | compute_C5 |
| DeepSeek-V4.1-Flash-engram-host | central | 1 | 2 | 0.0502 | 0.1009 | 0.0047 | 0.0032 | 0.0123 | 0.0329 | 0.0002 | 9.3% | 6.4% | 24.5% | 1.000 | collective_floor_C6 |
| DeepSeek-V4.1-Flash-engram-host | central | 8 | 2 | 0.1627 | 0.3258 | 0.0150 | 0.0258 | 0.0983 | 0.0481 | 0.0016 | 9.2% | 15.9% | 60.4% | 1.000 | compute_C5 |
| DeepSeek-V4.1-Flash-engram-host | central | 32 | 2 | 0.5482 | 1.0968 | 0.0430 | 0.1033 | 0.3933 | 0.1001 | 0.0066 | 7.8% | 18.8% | 71.7% | 1.000 | compute_C5 |
| DeepSeek-V4.1-Flash-engram-host | central | 64 | 2 | 1.0621 | 2.1247 | 0.0671 | 0.2066 | 0.7866 | 0.1693 | 0.0131 | 6.3% | 19.5% | 74.1% | 1.000 | compute_C5 |
| DeepSeek-V4.1-Flash-engram-host | aggressive | 1 | 1 | 0.0258 | 0.0258 | 0.0032 | 0.0034 | 0.0084 | 0.0161 | — | 12.2% | 13.2% | 32.7% | 1.000 | collective_floor_C6 |
| DeepSeek-V4.1-Flash-engram-host | aggressive | 8 | 1 | 0.1004 | 0.1004 | 0.0103 | 0.0272 | 0.0674 | 0.0280 | — | 10.3% | 27.1% | 67.1% | 1.000 | compute_C5 |
| DeepSeek-V4.1-Flash-engram-host | aggressive | 32 | 1 | 0.3562 | 0.3562 | 0.0297 | 0.1087 | 0.2696 | 0.0689 | — | 8.4% | 30.5% | 75.7% | 1.000 | compute_C5 |
| DeepSeek-V4.1-Flash-engram-host | aggressive | 64 | 1 | 0.6973 | 0.6973 | 0.0465 | 0.2173 | 0.5391 | 0.1233 | — | 6.7% | 31.2% | 77.3% | 1.000 | compute_C5 |

## Central-envelope achieved byte rates at 200K

These are rates implied by achieved token throughput, not raw hardware
bandwidth. ROM arrays carry only weights; HBM carries only mutable KV on
the proposed wafer. GPU HBM carries both deployed weights and KV.

| Model | B | Architecture | Deployed weight read | KV read+write | Total HBM | Tensor operations |
|---|---:|---|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | ROM-wafer-N7-HBM2e-central | 90.30 TB/s | 2.556 TB/s | 2.56 TB/s | 0.40 Pop/s |
| DeepSeek-V4-Flash-0731 | 1 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x16 | 6.89 TB/s | 0.195 TB/s | 7.09 TB/s | 0.03 Pop/s |
| DeepSeek-V4-Flash-0731 | 8 | ROM-wafer-N7-HBM2e-central | 69.22 TB/s | 5.295 TB/s | 5.30 TB/s | 0.83 Pop/s |
| DeepSeek-V4-Flash-0731 | 8 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 14.41 TB/s | 1.102 TB/s | 15.51 TB/s | 0.17 Pop/s |
| DeepSeek-V4-Flash-0731 | 32 | ROM-wafer-N7-HBM2e-central | 50.66 TB/s | 5.982 TB/s | 5.98 TB/s | 0.94 Pop/s |
| DeepSeek-V4-Flash-0731 | 32 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 22.75 TB/s | 2.687 TB/s | 25.44 TB/s | 0.42 Pop/s |
| DeepSeek-V4-Flash-0731 | 64 | ROM-wafer-N7-HBM2e-central | 36.92 TB/s | 6.114 TB/s | 6.11 TB/s | 0.96 Pop/s |
| DeepSeek-V4-Flash-0731 | 64 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 22.40 TB/s | 3.711 TB/s | 26.11 TB/s | 0.58 Pop/s |
| DeepSeek-V4-Pro-0813 | 1 | ROM-wafer-N7-HBM2e-central | 1,085.56 TB/s | 12.948 TB/s | 12.95 TB/s | 3.97 Pop/s |
| DeepSeek-V4-Pro-0813 | 1 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x32 | 9.87 TB/s | 0.118 TB/s | 9.99 TB/s | 0.04 Pop/s |
| DeepSeek-V4-Pro-0813 | 8 | ROM-wafer-N7-HBM2e-central | 747.83 TB/s | 22.803 TB/s | 22.80 TB/s | 6.99 Pop/s |
| DeepSeek-V4-Pro-0813 | 8 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 22.82 TB/s | 0.696 TB/s | 23.52 TB/s | 0.21 Pop/s |
| DeepSeek-V4-Pro-0813 | 32 | ROM-wafer-N7-HBM2e-central | 574.82 TB/s | 24.708 TB/s | 24.71 TB/s | 7.58 Pop/s |
| DeepSeek-V4-Pro-0813 | 32 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 34.96 TB/s | 1.503 TB/s | 36.47 TB/s | 0.46 Pop/s |
| DeepSeek-V4-Pro-0813 | 64 | ROM-wafer-N7-HBM2e-central | 454.15 TB/s | 25.057 TB/s | 25.06 TB/s | 7.68 Pop/s |
| DeepSeek-V4-Pro-0813 | 64 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 35.27 TB/s | 1.946 TB/s | 37.21 TB/s | 0.60 Pop/s |
| DeepSeek-V4.1-Flash | 1 | ROM-wafer-N7-HBM2e-central | 369.14 TB/s | 1.325 TB/s | 1.32 TB/s | 1.14 Pop/s |
| DeepSeek-V4.1-Flash | 1 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x32 | 7.36 TB/s | 0.026 TB/s | 7.38 TB/s | 0.02 Pop/s |
| DeepSeek-V4.1-Flash | 8 | ROM-wafer-N7-HBM2e-central | 371.36 TB/s | 3.255 TB/s | 3.25 TB/s | 2.79 Pop/s |
| DeepSeek-V4.1-Flash | 8 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 17.20 TB/s | 0.151 TB/s | 17.35 TB/s | 0.13 Pop/s |
| DeepSeek-V4.1-Flash | 32 | ROM-wafer-N7-HBM2e-central | 316.40 TB/s | 3.856 TB/s | 3.86 TB/s | 3.31 Pop/s |
| DeepSeek-V4.1-Flash | 32 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 28.41 TB/s | 0.346 TB/s | 28.76 TB/s | 0.30 Pop/s |
| DeepSeek-V4.1-Flash | 64 | ROM-wafer-N7-HBM2e-central | 255.01 TB/s | 3.979 TB/s | 3.98 TB/s | 3.41 Pop/s |
| DeepSeek-V4.1-Flash | 64 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 29.36 TB/s | 0.458 TB/s | 29.82 TB/s | 0.39 Pop/s |
| DeepSeek-V4.1-Flash-engram-host | 1 | ROM-wafer-N7-HBM2e-central | 259.43 TB/s | 0.931 TB/s | 0.93 TB/s | 0.80 Pop/s |
| DeepSeek-V4.1-Flash-engram-host | 1 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x32 | 7.36 TB/s | 0.026 TB/s | 7.38 TB/s | 0.02 Pop/s |
| DeepSeek-V4.1-Flash-engram-host | 8 | ROM-wafer-N7-HBM2e-central | 262.53 TB/s | 2.301 TB/s | 2.30 TB/s | 1.97 Pop/s |
| DeepSeek-V4.1-Flash-engram-host | 8 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 17.20 TB/s | 0.151 TB/s | 17.35 TB/s | 0.13 Pop/s |
| DeepSeek-V4.1-Flash-engram-host | 32 | ROM-wafer-N7-HBM2e-central | 224.08 TB/s | 2.731 TB/s | 2.73 TB/s | 2.34 Pop/s |
| DeepSeek-V4.1-Flash-engram-host | 32 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 28.41 TB/s | 0.346 TB/s | 28.76 TB/s | 0.30 Pop/s |
| DeepSeek-V4.1-Flash-engram-host | 64 | ROM-wafer-N7-HBM2e-central | 180.68 TB/s | 2.819 TB/s | 2.82 TB/s | 2.42 Pop/s |
| DeepSeek-V4.1-Flash-engram-host | 64 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 29.36 TB/s | 0.458 TB/s | 29.82 TB/s | 0.39 Pop/s |

## ROM uncertainty bands across context and batch

An `infeasible–high` interval means at least one deterministic hardware
envelope cannot place the checkpoint or resident KV sessions. Numeric
lows are reported only when every envelope is feasible.

| Model | Context | B/stage | Feasible envelopes | ROM user tok/s low–high | Same-B ROM/GPU low–high | Binding terms across envelopes |
|---|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | 3/3 | 1,356.6–40,154.8 | 2.19×–64.83× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | 3/3 | 672.7–11,723.2 | 1.53×–26.70× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | 3/3 | 240.3–3,420.2 | 0.88×–12.57× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | 3/3 | 129.4–1,759.1 | 0.68×–9.26× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | 3/3 | 1,349.0–39,543.0 | 2.18×–63.91× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | 3/3 | 657.1–11,314.4 | 1.50×–25.81× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | 3/3 | 232.4–3,281.9 | 0.86×–12.11× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | 3/3 | 124.8–1,686.0 | 0.66×–8.92× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | 3/3 | 1,287.0–23,767.7 | 2.09×–38.69× | collective_floor_C6, kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | 3/3 | 567.6–4,491.1 | 1.31×–10.35× | compute_C5, kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | 3/3 | 190.0–1,187.9 | 0.72×–4.49× | compute_C5, kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | 3/3 | 100.7–599.7 | 0.55×–3.28× | compute_C5, kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | 3/3 | 775.1–7,462.8 | 1.29×–12.45× | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | 3/3 | 169.5–1,043.8 | 0.41×–2.52× | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | 3/3 | 45.8–264.3 | 0.19×–1.12× | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | 2/3 | infeasible–132.4 | infeasible–0.84× | capacity_C7_C8_C9, kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | 3/3 | 692.3–18,360.7 | 2.78×–73.62× | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | 3/3 | 193.6–3,714.3 | 1.05×–20.06× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | 3/3 | 55.8–994.5 | 0.55×–9.87× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | 3/3 | 28.6–503.2 | 0.44×–7.68× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | 3/3 | 688.0–18,107.5 | 2.76×–72.63× | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | 3/3 | 190.9–3,632.1 | 1.03×–19.63× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | 3/3 | 54.9–970.9 | 0.55×–9.65× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | 3/3 | 28.2–491.1 | 0.43×–7.51× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | 3/3 | 659.8–15,318.1 | 2.65×–61.57× | collective_floor_C6, kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | 3/3 | 174.3–2,875.0 | 0.95×–15.64× | compute_C5, kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | 3/3 | 49.5–759.6 | 0.50×–7.65× | compute_C5, kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | 3/3 | 25.3–383.4 | 0.39×–5.97× | compute_C5, kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | 3/3 | 516.6–5,031.0 | 2.10×–20.42× | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | 3/3 | 109.9–706.4 | 0.62×–3.95× | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | 2/3 | infeasible–179.0 | infeasible–1.92× | capacity_C7_C8_C9, kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | 1/3 | infeasible–89.7 | infeasible–1.51× | capacity_C7_C8_C9, kv_beachfront_C8 |
| Qwen3-8B | 8,192 | 1 | 3/3 | 967.8–9,327.0 | 1.07×–10.29× | kv_beachfront_C8 |
| Qwen3-8B | 8,192 | 8 | 3/3 | 212.5–1,311.7 | 0.32×–1.97× | kv_beachfront_C8 |
| Qwen3-8B | 8,192 | 32 | 3/3 | 57.8–332.4 | 0.15×–0.84× | kv_beachfront_C8 |
| Qwen3-8B | 8,192 | 64 | 3/3 | 29.3–166.6 | 0.12×–0.65× | kv_beachfront_C8 |
| Qwen3-8B | 32,768 | 1 | 3/3 | 385.2–2,603.6 | 0.46×–3.09× | kv_beachfront_C8 |
| Qwen3-8B | 32,768 | 8 | 3/3 | 58.1–335.9 | 0.11×–0.62× | kv_beachfront_C8 |
| Qwen3-8B | 32,768 | 32 | 3/3 | 14.9–84.3 | 0.06×–0.33× | kv_beachfront_C8 |
| Qwen3-8B | 32,768 | 64 | 2/3 | infeasible–42.2 | infeasible–0.28× | capacity_C7_C8_C9, kv_beachfront_C8 |
| DeepSeek-V4.1-Flash | 8,192 | 1 | 3/3 | 1,201.8–38,041.2 | 2.13×–67.36× | collective_floor_C6 |
| DeepSeek-V4.1-Flash | 8,192 | 8 | 3/3 | 459.2–9,887.8 | 1.14×–24.52× | compute_C5 |
| DeepSeek-V4.1-Flash | 8,192 | 32 | 3/3 | 147.2–2,795.2 | 0.63×–12.05× | compute_C5 |
| DeepSeek-V4.1-Flash | 8,192 | 64 | 3/3 | 77.3–1,428.7 | 0.50×–9.30× | compute_C5 |
| DeepSeek-V4.1-Flash | 32,768 | 1 | 3/3 | 1,200.6–37,880.5 | 2.13×–67.08× | collective_floor_C6 |
| DeepSeek-V4.1-Flash | 32,768 | 8 | 3/3 | 457.8–9,801.3 | 1.14×–24.31× | compute_C5 |
| DeepSeek-V4.1-Flash | 32,768 | 32 | 3/3 | 146.7–2,767.6 | 0.63×–11.94× | compute_C5 |
| DeepSeek-V4.1-Flash | 32,768 | 64 | 3/3 | 76.9–1,414.3 | 0.50×–9.21× | compute_C5 |
| DeepSeek-V4.1-Flash | 200,000 | 1 | 3/3 | 1,200.6–37,419.6 | 2.13×–66.29× | collective_floor_C6 |
| DeepSeek-V4.1-Flash | 200,000 | 8 | 3/3 | 457.8–9,557.6 | 1.14×–23.73× | compute_C5 |
| DeepSeek-V4.1-Flash | 200,000 | 32 | 3/3 | 146.7–2,690.1 | 0.63×–11.63× | compute_C5 |
| DeepSeek-V4.1-Flash | 200,000 | 64 | 3/3 | 76.9–1,373.9 | 0.50×–8.98× | compute_C5 |
| DeepSeek-V4.1-Flash | 1,000,000 | 1 | 3/3 | 1,094.6–29,774.4 | 1.94×–52.84× | collective_floor_C6 |
| DeepSeek-V4.1-Flash | 1,000,000 | 8 | 3/3 | 353.4–6,268.7 | 0.88×–15.64× | kv_beachfront_C8 |
| DeepSeek-V4.1-Flash | 1,000,000 | 32 | 3/3 | 106.4–1,691.2 | 0.47×–7.40× | kv_beachfront_C8 |
| DeepSeek-V4.1-Flash | 1,000,000 | 64 | 3/3 | 55.1–856.9 | 0.37×–5.69× | kv_beachfront_C8 |
| DeepSeek-V4.1-Flash-engram-host | 8,192 | 1 | 3/3 | 1,318.8–39,524.3 | 2.34×–69.98× | collective_floor_C6 |
| DeepSeek-V4.1-Flash-engram-host | 8,192 | 8 | 3/3 | 528.2–10,370.5 | 1.31×–25.71× | compute_C5 |
| DeepSeek-V4.1-Flash-engram-host | 8,192 | 32 | 3/3 | 172.8–2,938.7 | 0.75×–12.67× | compute_C5 |
| DeepSeek-V4.1-Flash-engram-host | 8,192 | 64 | 3/3 | 91.1–1,502.8 | 0.59×–9.78× | compute_C5 |
| DeepSeek-V4.1-Flash-engram-host | 32,768 | 1 | 3/3 | 1,317.9–39,381.8 | 2.33×–69.74× | collective_floor_C6 |
| DeepSeek-V4.1-Flash-engram-host | 32,768 | 8 | 3/3 | 527.0–10,292.3 | 1.31×–25.52× | compute_C5 |
| DeepSeek-V4.1-Flash-engram-host | 32,768 | 32 | 3/3 | 172.3–2,913.6 | 0.74×–12.57× | compute_C5 |
| DeepSeek-V4.1-Flash-engram-host | 32,768 | 64 | 3/3 | 90.8–1,489.7 | 0.59×–9.70× | compute_C5 |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 1 | 3/3 | 1,317.9–38,761.3 | 2.33×–68.66× | collective_floor_C6 |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 8 | 3/3 | 527.0–9,959.0 | 1.31×–24.72× | compute_C5 |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 32 | 3/3 | 172.3–2,807.2 | 0.75×–12.14× | compute_C5 |
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 64 | 3/3 | 90.8–1,434.1 | 0.59×–9.37× | compute_C5 |
| DeepSeek-V4.1-Flash-engram-host | 1,000,000 | 1 | 3/3 | 1,275.4–32,366.1 | 2.26×–57.44× | collective_floor_C6 |
| DeepSeek-V4.1-Flash-engram-host | 1,000,000 | 8 | 3/3 | 476.2–7,082.5 | 1.19×–17.67× | compute_C5, kv_beachfront_C8 |
| DeepSeek-V4.1-Flash-engram-host | 1,000,000 | 32 | 3/3 | 151.2–1,925.5 | 0.66×–8.42× | compute_C5, kv_beachfront_C8 |
| DeepSeek-V4.1-Flash-engram-host | 1,000,000 | 64 | 3/3 | 79.2–977.0 | 0.53×–6.48× | compute_C5, kv_beachfront_C8 |

## SRAM-rich N7 control at 200K

This is an area-scaled Graphcore-style storage control, not a Graphcore
product claim. It illustrates the capacity cost of replacing ROM with
writable on-wafer SRAM while holding the general spatial model similar.

| Model | B/stage | Stages | Feasible | User tok/s | Bind/reason |
|---|---:|---:|---|---:|---|
| DeepSeek-V4-Flash-0731 | 1 | 5 | True | 7,972.4 | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 8 | 5 | True | 2,203.3 | compute_C5 |
| DeepSeek-V4-Flash-0731 | 32 | 5 | False | 0.0 | capacity_C7_C8_C9 |
| DeepSeek-V4-Flash-0731 | 64 | 5 | False | 0.0 | capacity_C7_C8_C9 |
| DeepSeek-V4-Pro-0813 | 1 | 31 | True | 3,088.8 | compute_C5 |
| DeepSeek-V4-Pro-0813 | 8 | 31 | False | 0.0 | capacity_C7_C8_C9 |
| DeepSeek-V4-Pro-0813 | 32 | 31 | False | 0.0 | capacity_C7_C8_C9 |
| DeepSeek-V4-Pro-0813 | 64 | 31 | False | 0.0 | capacity_C7_C8_C9 |
| DeepSeek-V4.1-Flash | 1 | 15 | True | 6,762.4 | collective_floor_C6 |
| DeepSeek-V4.1-Flash | 8 | 15 | True | 1,666.5 | compute_C5 |
| DeepSeek-V4.1-Flash | 32 | 15 | False | 0.0 | capacity_C7_C8_C9 |
| DeepSeek-V4.1-Flash | 64 | 15 | False | 0.0 | capacity_C7_C8_C9 |
| DeepSeek-V4.1-Flash-engram-host | 1 | 10 | True | 8,072.1 | collective_floor_C6 |
| DeepSeek-V4.1-Flash-engram-host | 8 | 10 | True | 2,066.8 | compute_C5 |
| DeepSeek-V4.1-Flash-engram-host | 32 | 10 | False | 0.0 | capacity_C7_C8_C9 |
| DeepSeek-V4.1-Flash-engram-host | 64 | 10 | False | 0.0 | capacity_C7_C8_C9 |

## Interpretation boundary

- Conservative/central/aggressive are deterministic envelopes, not confidence intervals.
- No target-node ROM macro, full-wafer read path, package, power, yield, or model throughput has been measured.
- A100 is bounded by two explicit deployments: exact offline BF16-resident expansion and a GPU-favorable packed-HBM/on-consumption-BF16 ceiling whose unpack cost is unmeasured and omitted. Neither receives native FP8/MXFP4 execution.
- B300 uses official packed checkpoint storage and public low-precision arithmetic roofs; its undisclosed full-FP32 roof is explicitly assumed and swept.
- Normalization, nonlinear, softmax-score, top-k, compressor-pool, and Sinkhorn categories are counted and assigned break-even rate requirements, but no vector/top-k service roof or time is assumed; reported token rates remain conditional on those paths fitting the baseline interval.
- The auxiliary ledger is not yet operator-complete: activation quantization/scaling, RoPE, residual/hyper-connection elementwise work, dispatch, and other source operations remain under COMP-01.
- Same-batch and resident-session-matched comparisons are both emitted because a wafer pipeline has batch times stages resident sessions.
- Partial TCO is not a vendor-price or profitability claim. It excludes
  staffing, financing, networking, facilities, maintenance, and spares.
- Prefill and speculative decoding are intentionally absent from this
  decode-only attribution study; adding either requires a separately
  evidence-backed execution/deployment profile.
- Huawei Tau/韬 scaling and 3-D integration are not applied as numerical
  multipliers. Any vertical-ROM study must be a separate parameterized
  thermal/yield/interconnect scenario under `docs/METHODOLOGY.md`.
