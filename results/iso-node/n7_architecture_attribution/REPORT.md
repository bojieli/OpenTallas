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

## Mechanical consistency audit

| Status | Checks | Max weight/shared-HBM service | Max KV service | Max compute service | Max cooling |
|---|---:|---:|---:|---:|---:|
| PASS | 14,578 | 100.0% | 94.6% | 88.4% | 100.0% |

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
| DeepSeek-V4-Flash-0731 | 1 | 1 | 1 | 9,399.2 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x16 | 618.2 | 15.20× | 15.20× | 0.2816 | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 8 | 1 | 8 | 2,967.0 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 437.9 | 6.78× | 6.78× | 0.1115 | compute_C5 |
| DeepSeek-V4-Flash-0731 | 32 | 1 | 32 | 886.6 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 270.2 | 3.28× | 3.28× | 0.0933 | compute_C5 |
| DeepSeek-V4-Flash-0731 | 64 | 1 | 64 | 458.2 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 188.1 | 2.44× | 2.44× | 0.0902 | compute_C5 |
| DeepSeek-V4-Pro-0813 | 1 | 6 | 6 | 4,506.0 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x32 | 249.3 | 18.08× | 22.67× | 0.3735 | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 8 | 6 | 48 | 1,001.4 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 184.9 | 5.42× | 12.78× | 0.2121 | compute_C5 |
| DeepSeek-V4-Pro-0813 | 32 | 6 | 192 | 271.8 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 100.4 | 2.71× | 8.25× | 0.1957 | compute_C5 |
| DeepSeek-V4-Pro-0813 | 64 | 6 | 384 | 137.9 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 65.3 | 2.11× | 6.62× | 0.1930 | compute_C5 |

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
| DeepSeek-V4-Flash-0731 | 1 | ROM-wafer-N7-HBM2e-central | 28.57 Gitem/s | 631.62 Gitem/s | 17.21 Gitem/s | 5.90 Gitem/s | 9.87 Gitem/s | 258.67 Mitem/s |
| DeepSeek-V4-Flash-0731 | 1 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x16 | 1.88 Gitem/s | 41.54 Gitem/s | 1.13 Gitem/s | 387.89 Mitem/s | 649.10 Mitem/s | 17.01 Mitem/s |
| DeepSeek-V4-Flash-0731 | 8 | ROM-wafer-N7-HBM2e-central | 72.15 Gitem/s | 1.60 Titem/s | 43.47 Gitem/s | 14.89 Gitem/s | 24.92 Gitem/s | 653.21 Mitem/s |
| DeepSeek-V4-Flash-0731 | 8 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 10.65 Gitem/s | 235.39 Gitem/s | 6.42 Gitem/s | 2.20 Gitem/s | 3.68 Gitem/s | 96.40 Mitem/s |
| DeepSeek-V4-Flash-0731 | 32 | ROM-wafer-N7-HBM2e-central | 86.24 Gitem/s | 1.91 Titem/s | 51.96 Gitem/s | 17.80 Gitem/s | 29.79 Gitem/s | 780.80 Mitem/s |
| DeepSeek-V4-Flash-0731 | 32 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 26.28 Gitem/s | 581.00 Gitem/s | 15.83 Gitem/s | 5.42 Gitem/s | 9.08 Gitem/s | 237.93 Mitem/s |
| DeepSeek-V4-Flash-0731 | 64 | ROM-wafer-N7-HBM2e-central | 89.15 Gitem/s | 1.97 Titem/s | 53.71 Gitem/s | 18.40 Gitem/s | 30.79 Gitem/s | 807.09 Mitem/s |
| DeepSeek-V4-Flash-0731 | 64 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 36.60 Gitem/s | 809.12 Gitem/s | 22.05 Gitem/s | 7.55 Gitem/s | 12.64 Gitem/s | 331.35 Mitem/s |
| DeepSeek-V4-Pro-0813 | 1 | ROM-wafer-N7-HBM2e-central | 55.70 Gitem/s | 437.87 Gitem/s | 24.66 Gitem/s | 6.59 Gitem/s | 6.84 Gitem/s | 192.66 Mitem/s |
| DeepSeek-V4-Pro-0813 | 1 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x32 | 2.77 Gitem/s | 23.93 Gitem/s | 1.25 Gitem/s | 332.81 Mitem/s | 373.89 Mitem/s | 9.73 Mitem/s |
| DeepSeek-V4-Pro-0813 | 8 | ROM-wafer-N7-HBM2e-central | 98.09 Gitem/s | 771.13 Gitem/s | 43.43 Gitem/s | 11.60 Gitem/s | 12.05 Gitem/s | 339.30 Mitem/s |
| DeepSeek-V4-Pro-0813 | 8 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 16.46 Gitem/s | 141.98 Gitem/s | 7.40 Gitem/s | 1.97 Gitem/s | 2.22 Gitem/s | 57.74 Mitem/s |
| DeepSeek-V4-Pro-0813 | 32 | ROM-wafer-N7-HBM2e-central | 106.28 Gitem/s | 835.54 Gitem/s | 47.06 Gitem/s | 12.57 Gitem/s | 13.06 Gitem/s | 367.64 Mitem/s |
| DeepSeek-V4-Pro-0813 | 32 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 35.77 Gitem/s | 308.56 Gitem/s | 16.08 Gitem/s | 4.29 Gitem/s | 4.82 Gitem/s | 125.48 Mitem/s |
| DeepSeek-V4-Pro-0813 | 64 | ROM-wafer-N7-HBM2e-central | 107.78 Gitem/s | 847.33 Gitem/s | 47.72 Gitem/s | 12.75 Gitem/s | 13.24 Gitem/s | 372.83 Mitem/s |
| DeepSeek-V4-Pro-0813 | 64 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 46.48 Gitem/s | 400.90 Gitem/s | 20.90 Gitem/s | 5.58 Gitem/s | 6.26 Gitem/s | 163.03 Mitem/s |

## ROM component timing and occupancy at 200K

Times are seconds of bottleneck-stage service expressed in milliseconds.
Weight, KV, and compute may overlap; the layer collective is serialized;
pipeline efficiency and any thermal scaling produce the final interval.
The cross-stage entry is the initiation-interval serialization floor, not
the full end-to-end propagation latency. Occupancies are modeled service
time divided by the final interval, not silicon performance counters.

| Model | Envelope | B/stage | Stages | Final interval ms | User latency ms | Weight ms | KV ms | Compute ms | Collective ms | Cross-stage ms | Weight util | KV util | Compute util | Thermal × | Bind |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Flash-0731 | central | 1 | 1 | 0.1064 | 0.1064 | 0.0078 | 0.0131 | 0.0259 | 0.0698 | — | 7.4% | 12.3% | 24.4% | 1.000 | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | central | 8 | 1 | 0.3370 | 0.3370 | 0.0232 | 0.1049 | 0.2075 | 0.0959 | — | 6.9% | 31.1% | 61.6% | 1.000 | compute_C5 |
| DeepSeek-V4-Flash-0731 | central | 32 | 1 | 1.1279 | 1.1279 | 0.0600 | 0.4194 | 0.8298 | 0.1852 | — | 5.3% | 37.2% | 73.6% | 1.000 | compute_C5 |
| DeepSeek-V4-Flash-0731 | central | 64 | 1 | 2.1823 | 2.1823 | 0.0856 | 0.8388 | 1.6597 | 0.3044 | — | 3.9% | 38.4% | 76.1% | 1.000 | compute_C5 |
| DeepSeek-V4-Flash-0731 | aggressive | 1 | 1 | 0.0279 | 0.0279 | 0.0027 | 0.0072 | 0.0096 | 0.0169 | — | 9.7% | 25.8% | 34.4% | 1.000 | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | aggressive | 8 | 1 | 0.1094 | 0.1094 | 0.0080 | 0.0576 | 0.0767 | 0.0272 | — | 7.4% | 52.6% | 70.2% | 1.000 | compute_C5 |
| DeepSeek-V4-Flash-0731 | aggressive | 32 | 1 | 0.3886 | 0.3886 | 0.0208 | 0.2302 | 0.3069 | 0.0623 | — | 5.4% | 59.2% | 79.0% | 1.000 | compute_C5 |
| DeepSeek-V4-Flash-0731 | aggressive | 64 | 1 | 0.7609 | 0.7609 | 0.0297 | 0.4605 | 0.6137 | 0.1091 | — | 3.9% | 60.5% | 80.7% | 1.000 | compute_C5 |
| DeepSeek-V4-Pro-0813 | central | 1 | 6 | 0.0365 | 0.2219 | 0.0050 | 0.0035 | 0.0152 | 0.0186 | 0.0003 | 13.6% | 9.5% | 41.7% | 1.000 | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | central | 8 | 6 | 0.1660 | 0.9986 | 0.0156 | 0.0278 | 0.1219 | 0.0302 | 0.0023 | 9.4% | 16.7% | 73.4% | 1.000 | compute_C5 |
| DeepSeek-V4-Pro-0813 | central | 32 | 6 | 0.6128 | 3.6794 | 0.0443 | 0.1112 | 0.4877 | 0.0702 | 0.0092 | 7.2% | 18.1% | 79.6% | 1.000 | compute_C5 |
| DeepSeek-V4-Pro-0813 | central | 64 | 6 | 1.2085 | 7.2537 | 0.0690 | 0.2224 | 0.9753 | 0.1236 | 0.0184 | 5.7% | 18.4% | 80.7% | 1.000 | compute_C5 |
| DeepSeek-V4-Pro-0813 | aggressive | 1 | 3 | 0.0198 | 0.0605 | 0.0033 | 0.0037 | 0.0104 | 0.0088 | 0.0003 | 16.7% | 18.9% | 52.5% | 1.000 | compute_C5 |
| DeepSeek-V4-Pro-0813 | aggressive | 8 | 3 | 0.1052 | 0.3168 | 0.0103 | 0.0299 | 0.0832 | 0.0176 | 0.0023 | 9.8% | 28.5% | 79.1% | 1.000 | compute_C5 |
| DeepSeek-V4-Pro-0813 | aggressive | 32 | 3 | 0.3982 | 1.1957 | 0.0294 | 0.1198 | 0.3330 | 0.0476 | 0.0092 | 7.4% | 30.1% | 83.6% | 1.000 | compute_C5 |
| DeepSeek-V4-Pro-0813 | aggressive | 64 | 3 | 0.7889 | 2.3677 | 0.0457 | 0.2396 | 0.6660 | 0.0876 | 0.0184 | 5.8% | 30.4% | 84.4% | 1.000 | compute_C5 |

## Central-envelope achieved byte rates at 200K

These are rates implied by achieved token throughput, not raw hardware
bandwidth. ROM arrays carry only weights; HBM carries only mutable KV on
the proposed wafer. GPU HBM carries both deployed weights and KV.

| Model | B | Architecture | Deployed weight read | KV read+write | Total HBM | Tensor operations |
|---|---:|---|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | ROM-wafer-N7-HBM2e-central | 105.44 TB/s | 0.932 TB/s | 0.93 TB/s | 0.47 Pop/s |
| DeepSeek-V4-Flash-0731 | 1 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x16 | 6.93 TB/s | 0.061 TB/s | 7.00 TB/s | 0.03 Pop/s |
| DeepSeek-V4-Flash-0731 | 8 | ROM-wafer-N7-HBM2e-central | 98.51 TB/s | 2.353 TB/s | 2.35 TB/s | 1.19 Pop/s |
| DeepSeek-V4-Flash-0731 | 8 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 14.54 TB/s | 0.347 TB/s | 14.89 TB/s | 0.18 Pop/s |
| DeepSeek-V4-Flash-0731 | 32 | ROM-wafer-N7-HBM2e-central | 76.28 TB/s | 2.813 TB/s | 2.81 TB/s | 1.42 Pop/s |
| DeepSeek-V4-Flash-0731 | 32 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 23.25 TB/s | 0.857 TB/s | 24.10 TB/s | 0.43 Pop/s |
| DeepSeek-V4-Flash-0731 | 64 | ROM-wafer-N7-HBM2e-central | 56.22 TB/s | 2.907 TB/s | 2.91 TB/s | 1.47 Pop/s |
| DeepSeek-V4-Flash-0731 | 64 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 23.08 TB/s | 1.194 TB/s | 24.27 TB/s | 0.60 Pop/s |
| DeepSeek-V4-Pro-0813 | 1 | ROM-wafer-N7-HBM2e-central | 1,085.56 TB/s | 4.180 TB/s | 4.18 TB/s | 3.97 Pop/s |
| DeepSeek-V4-Pro-0813 | 1 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x32 | 9.89 TB/s | 0.038 TB/s | 9.93 TB/s | 0.04 Pop/s |
| DeepSeek-V4-Pro-0813 | 8 | ROM-wafer-N7-HBM2e-central | 747.83 TB/s | 7.362 TB/s | 7.36 TB/s | 6.99 Pop/s |
| DeepSeek-V4-Pro-0813 | 8 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 22.95 TB/s | 0.226 TB/s | 23.17 TB/s | 0.21 Pop/s |
| DeepSeek-V4-Pro-0813 | 32 | ROM-wafer-N7-HBM2e-central | 574.82 TB/s | 7.977 TB/s | 7.98 TB/s | 7.58 Pop/s |
| DeepSeek-V4-Pro-0813 | 32 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 35.38 TB/s | 0.491 TB/s | 35.87 TB/s | 0.47 Pop/s |
| DeepSeek-V4-Pro-0813 | 64 | ROM-wafer-N7-HBM2e-central | 454.15 TB/s | 8.089 TB/s | 8.09 TB/s | 7.68 Pop/s |
| DeepSeek-V4-Pro-0813 | 64 | NVIDIA-A100-SXM-80GB-packed-HBM-BF16-execute-x64 | 35.81 TB/s | 0.638 TB/s | 36.45 TB/s | 0.61 Pop/s |

## ROM uncertainty bands across context and batch

An `infeasible–high` interval means at least one deterministic hardware
envelope cannot place the checkpoint or resident KV sessions. Numeric
lows are reported only when every envelope is feasible.

| Model | Context | B/stage | Feasible envelopes | ROM user tok/s low–high | Same-B ROM/GPU low–high | Binding terms across envelopes |
|---|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | 3/3 | 1,356.6–40,154.8 | 2.19×–64.80× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | 3/3 | 672.7–11,723.2 | 1.53×–26.68× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | 3/3 | 240.3–3,420.2 | 0.88×–12.55× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | 3/3 | 129.4–1,759.1 | 0.68×–9.24× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | 3/3 | 1,349.0–39,543.0 | 2.18×–63.83× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | 3/3 | 657.1–11,314.4 | 1.50×–25.76× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | 3/3 | 232.4–3,281.9 | 0.85×–12.06× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | 3/3 | 124.8–1,686.0 | 0.66×–8.87× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | 3/3 | 1,299.1–35,829.2 | 2.10×–57.96× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | 3/3 | 567.6–9,144.7 | 1.30×–20.89× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | 3/3 | 190.0–2,573.4 | 0.70×–9.52× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | 3/3 | 100.7–1,314.2 | 0.54×–6.99× | compute_C5 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | 3/3 | 1,103.8–18,947.5 | 1.80×–30.96× | collective_floor_C6, kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | 3/3 | 343.5–3,243.7 | 0.80×–7.52× | compute_C5, kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | 3/3 | 101.4–844.4 | 0.39×–3.24× | compute_C5, kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | 3/3 | 52.3–425.1 | 0.29×–2.37× | compute_C5, kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | 3/3 | 692.3–18,360.7 | 2.78×–73.61× | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | 3/3 | 193.6–3,714.3 | 1.04×–20.05× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | 3/3 | 55.8–994.5 | 0.55×–9.86× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | 3/3 | 28.6–503.2 | 0.44×–7.67× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | 3/3 | 688.0–18,107.5 | 2.76×–72.60× | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | 3/3 | 190.9–3,632.1 | 1.03×–19.61× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | 3/3 | 54.9–970.9 | 0.54×–9.63× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | 3/3 | 28.2–491.1 | 0.43×–7.49× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | 3/3 | 659.8–16,533.1 | 2.65×–66.33× | collective_floor_C6, compute_C5 |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | 3/3 | 174.3–3,156.9 | 0.94×–17.08× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | 3/3 | 49.5–836.3 | 0.49×–8.33× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | 3/3 | 25.3–422.4 | 0.39×–6.47× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | 3/3 | 551.5–11,548.9 | 2.22×–46.47× | collective_floor_C6, compute_C5 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | 3/3 | 123.2–1,929.5 | 0.67×–10.53× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | 3/3 | 33.6–500.4 | 0.34×–5.08× | compute_C5 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | 2/3 | infeasible–251.8 | infeasible–3.96× | capacity_C7_C8_C9, compute_C5 |
| Qwen3-8B | 8,192 | 1 | 3/3 | 967.8–9,327.0 | 1.07×–10.29× | kv_beachfront_C8 |
| Qwen3-8B | 8,192 | 8 | 3/3 | 212.5–1,311.7 | 0.32×–1.97× | kv_beachfront_C8 |
| Qwen3-8B | 8,192 | 32 | 3/3 | 57.8–332.4 | 0.15×–0.84× | kv_beachfront_C8 |
| Qwen3-8B | 8,192 | 64 | 3/3 | 29.3–166.6 | 0.12×–0.65× | kv_beachfront_C8 |
| Qwen3-8B | 32,768 | 1 | 3/3 | 385.2–2,603.6 | 0.46×–3.09× | kv_beachfront_C8 |
| Qwen3-8B | 32,768 | 8 | 3/3 | 58.1–335.9 | 0.11×–0.62× | kv_beachfront_C8 |
| Qwen3-8B | 32,768 | 32 | 3/3 | 14.9–84.3 | 0.06×–0.33× | kv_beachfront_C8 |
| Qwen3-8B | 32,768 | 64 | 2/3 | infeasible–42.2 | infeasible–0.28× | capacity_C7_C8_C9, kv_beachfront_C8 |

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
| DeepSeek-V4-Pro-0813 | 8 | 31 | True | 575.7 | compute_C5 |
| DeepSeek-V4-Pro-0813 | 32 | 31 | False | 0.0 | capacity_C7_C8_C9 |
| DeepSeek-V4-Pro-0813 | 64 | 31 | False | 0.0 | capacity_C7_C8_C9 |

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
