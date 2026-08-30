# Leading Node Market

> N4-class ROM + HBM3e versus B300 4NP/HBM3e; WSE-3 N5 only as wafer feasibility/physical ceiling anchor

This is an evidence-bounded decode simulation, not a fabricated-silicon or
product-performance claim. `Low` and `high` below are deterministic hardware
envelopes, not statistical confidence intervals.

## Storage and execution contract

| Architecture | Devices available | Weight store | Mutable KV store | Weight capacity/device | KV capacity/device | Raw weight BW/device | Raw KV BW/device | Deployment |
|---|---:|---|---|---:|---:|---:|---:|---|
| NVIDIA-B300-x1 | 1 | HBM3e | HBM3e | 288.0 GB | 288.0 GB | 7.75 TB/s | 7.75 TB/s | official_packed |
| NVIDIA-B300-x2 | 2 | HBM3e | HBM3e | 288.0 GB | 288.0 GB | 7.75 TB/s | 7.75 TB/s | official_packed |
| NVIDIA-B300-x4 | 4 | HBM3e | HBM3e | 288.0 GB | 288.0 GB | 7.75 TB/s | 7.75 TB/s | official_packed |
| NVIDIA-B300-x8 | 8 | HBM3e | HBM3e | 288.0 GB | 288.0 GB | 7.75 TB/s | 7.75 TB/s | official_packed |
| NVIDIA-B300-x16 | 16 | HBM3e | HBM3e | 288.0 GB | 288.0 GB | 7.75 TB/s | 7.75 TB/s | official_packed |
| ROM-wafer-N4-class-HBM3e-conservative | 64 | mask_ROM_N4-class | HBM3e | 101.1 GB | 864.0 GB | 1,456.09 TB/s | 23.25 TB/s | official_packed |
| ROM-wafer-N4-class-HBM3e-central | 64 | mask_ROM_N4-class | HBM3e | 242.7 GB | 1,440.0 GB | 3,993.84 TB/s | 38.75 TB/s | official_packed |
| ROM-wafer-N4-class-HBM3e-aggressive | 64 | mask_ROM_N4-class | HBM3e | 473.6 GB | 2,016.0 GB | 7,627.13 TB/s | 54.25 TB/s | official_packed |

GPU HBM capacity and bandwidth are shared by weights and KV. ROM weight
capacity/bandwidth and mutable HBM KV capacity/bandwidth are physically
separate. The SRAM-rich control uses a static 70% weight / 30% KV split.

## Exact model work and deployment storage

| Model | Official checkpoint | Deployment representation | Resident bytes | Tensor ops/token | At context | Dense / routed format |
|---|---:|---|---:|---:|---:|---|
| DeepSeek-V4-Flash-0731 | 166.9 GB | official_packed | 166.9 GB | 135.2 Gop | 1,000,000 | fp8_e4m3_x_fp8_e4m3 / mxfp4_e2m1_x_fp8_e4m3 |
| DeepSeek-V4-Pro-0813 | 892.7 GB | official_packed | 892.7 GB | 294.2 Gop | 1,000,000 | fp8_e4m3_x_fp8_e4m3 / mxfp4_e2m1_x_fp8_e4m3 |
| Qwen3-8B | 16.4 GB | official_packed | 16.4 GB | 15.1 Gop | 32,768 | bf16_x_bf16 / None |

## Mechanical consistency audit

| Status | Checks | Max weight/shared-HBM service | Max KV service | Max compute service | Max cooling |
|---|---:|---:|---:|---:|---:|
| PASS | 9,056 | 100.0% | 95.0% | 57.1% | 100.0% |

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
| DeepSeek-V4-Flash-0731 | 1 | 1 | 1 | 12,629.3 | NVIDIA-B300-x8 | 1,650.7 | 7.65× | 7.65× | 0.2096 | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 8 | 1 | 8 | 4,698.7 | NVIDIA-B300-x16 | 1,006.3 | 4.67× | 4.67× | 0.0704 | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 32 | 1 | 32 | 1,490.2 | NVIDIA-B300-x16 | 506.8 | 2.94× | 2.94× | 0.0555 | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 64 | 1 | 64 | 780.0 | NVIDIA-B300-x16 | 355.8 | 2.19× | 2.19× | 0.0530 | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 1 | 4 | 4 | 8,211.7 | NVIDIA-B300-x16 | 651.5 | 12.60× | 16.02× | 0.2168 | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 8 | 4 | 32 | 2,879.3 | NVIDIA-B300-x16 | 385.5 | 7.47× | 18.24× | 0.0778 | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 32 | 4 | 128 | 881.5 | NVIDIA-B300-x16 | 157.9 | 5.58× | 12.23× | 0.0637 | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 64 | 4 | 256 | 457.9 | NVIDIA-B300-x16 | 101.6 | 4.51× | 8.11× | 0.0613 | kv_beachfront_C8 |

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
| DeepSeek-V4-Flash-0731 | 1 | ROM-wafer-N4-class-HBM3e-central | 38.39 Gitem/s | 848.69 Gitem/s | 23.13 Gitem/s | 7.92 Gitem/s | 13.26 Gitem/s | 347.56 Mitem/s |
| DeepSeek-V4-Flash-0731 | 1 | NVIDIA-B300-x8 | 5.02 Gitem/s | 110.93 Gitem/s | 3.02 Gitem/s | 1.04 Gitem/s | 1.73 Gitem/s | 45.43 Mitem/s |
| DeepSeek-V4-Flash-0731 | 8 | ROM-wafer-N4-class-HBM3e-central | 114.26 Gitem/s | 2.53 Titem/s | 68.84 Gitem/s | 23.59 Gitem/s | 39.47 Gitem/s | 1.03 Gitem/s |
| DeepSeek-V4-Flash-0731 | 8 | NVIDIA-B300-x16 | 24.47 Gitem/s | 540.97 Gitem/s | 14.74 Gitem/s | 5.05 Gitem/s | 8.45 Gitem/s | 221.54 Mitem/s |
| DeepSeek-V4-Flash-0731 | 32 | ROM-wafer-N4-class-HBM3e-central | 144.95 Gitem/s | 3.20 Titem/s | 87.33 Gitem/s | 29.92 Gitem/s | 50.07 Gitem/s | 1.31 Gitem/s |
| DeepSeek-V4-Flash-0731 | 32 | NVIDIA-B300-x16 | 49.30 Gitem/s | 1.09 Titem/s | 29.70 Gitem/s | 10.18 Gitem/s | 17.03 Gitem/s | 446.32 Mitem/s |
| DeepSeek-V4-Flash-0731 | 64 | ROM-wafer-N4-class-HBM3e-central | 151.75 Gitem/s | 3.35 Titem/s | 91.43 Gitem/s | 31.32 Gitem/s | 52.42 Gitem/s | 1.37 Gitem/s |
| DeepSeek-V4-Flash-0731 | 64 | NVIDIA-B300-x16 | 69.21 Gitem/s | 1.53 Titem/s | 41.70 Gitem/s | 14.29 Gitem/s | 23.91 Gitem/s | 626.62 Mitem/s |
| DeepSeek-V4-Pro-0813 | 1 | ROM-wafer-N4-class-HBM3e-central | 98.81 Gitem/s | 849.11 Gitem/s | 43.47 Gitem/s | 11.62 Gitem/s | 13.27 Gitem/s | 339.64 Mitem/s |
| DeepSeek-V4-Pro-0813 | 1 | NVIDIA-B300-x16 | 7.25 Gitem/s | 62.54 Gitem/s | 3.26 Gitem/s | 869.84 Mitem/s | 977.23 Mitem/s | 25.43 Mitem/s |
| DeepSeek-V4-Pro-0813 | 8 | ROM-wafer-N4-class-HBM3e-central | 275.42 Gitem/s | 2.37 Titem/s | 121.18 Gitem/s | 32.38 Gitem/s | 36.98 Gitem/s | 946.70 Mitem/s |
| DeepSeek-V4-Pro-0813 | 8 | NVIDIA-B300-x16 | 34.33 Gitem/s | 296.08 Gitem/s | 15.43 Gitem/s | 4.12 Gitem/s | 4.63 Gitem/s | 120.41 Mitem/s |
| DeepSeek-V4-Pro-0813 | 32 | ROM-wafer-N4-class-HBM3e-central | 336.48 Gitem/s | 2.89 Titem/s | 148.04 Gitem/s | 39.55 Gitem/s | 45.18 Gitem/s | 1.16 Gitem/s |
| DeepSeek-V4-Pro-0813 | 32 | NVIDIA-B300-x16 | 56.23 Gitem/s | 485.00 Gitem/s | 25.28 Gitem/s | 6.75 Gitem/s | 7.58 Gitem/s | 197.23 Mitem/s |
| DeepSeek-V4-Pro-0813 | 64 | ROM-wafer-N4-class-HBM3e-central | 349.39 Gitem/s | 3.00 Titem/s | 153.72 Gitem/s | 41.07 Gitem/s | 46.91 Gitem/s | 1.20 Gitem/s |
| DeepSeek-V4-Pro-0813 | 64 | NVIDIA-B300-x16 | 72.37 Gitem/s | 624.21 Gitem/s | 32.54 Gitem/s | 8.68 Gitem/s | 9.75 Gitem/s | 253.85 Mitem/s |

## ROM component timing and occupancy at 200K

Times are seconds of bottleneck-stage service expressed in milliseconds.
Weight, KV, and compute may overlap; the layer collective is serialized;
pipeline efficiency and any thermal scaling produce the final interval.
The cross-stage entry is the initiation-interval serialization floor, not
the full end-to-end propagation latency. Occupancies are modeled service
time divided by the final interval, not silicon performance counters.

| Model | Envelope | B/stage | Stages | Final interval ms | User latency ms | Weight ms | KV ms | Compute ms | Collective ms | Cross-stage ms | Weight util | KV util | Compute util | Thermal × | Bind |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Flash-0731 | central | 1 | 1 | 0.0792 | 0.0792 | 0.0052 | 0.0141 | 0.0024 | 0.0571 | — | 6.6% | 17.9% | 3.1% | 1.000 | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | central | 8 | 1 | 0.2128 | 0.2128 | 0.0154 | 0.1131 | 0.0194 | 0.0784 | — | 7.3% | 53.1% | 9.1% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | central | 32 | 1 | 0.6711 | 0.6711 | 0.0400 | 0.4524 | 0.0777 | 0.1516 | — | 6.0% | 67.4% | 11.6% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | central | 64 | 1 | 1.2820 | 1.2820 | 0.0571 | 0.9048 | 0.1554 | 0.2490 | — | 4.5% | 70.6% | 12.1% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | aggressive | 1 | 1 | 0.0236 | 0.0236 | 0.0022 | 0.0083 | 0.0011 | 0.0141 | — | 9.2% | 35.2% | 4.6% | 1.000 | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | aggressive | 8 | 1 | 0.0939 | 0.0939 | 0.0064 | 0.0665 | 0.0086 | 0.0226 | — | 6.9% | 70.9% | 9.2% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | aggressive | 32 | 1 | 0.3347 | 0.3347 | 0.0167 | 0.2661 | 0.0345 | 0.0519 | — | 5.0% | 79.5% | 10.3% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | aggressive | 64 | 1 | 0.6559 | 0.6559 | 0.0238 | 0.5322 | 0.0689 | 0.0910 | — | 3.6% | 81.1% | 10.5% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | central | 1 | 4 | 0.0301 | 0.1218 | 0.0048 | 0.0055 | 0.0020 | 0.0221 | 0.0001 | 16.0% | 18.3% | 6.8% | 1.000 | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | central | 8 | 4 | 0.0865 | 0.3473 | 0.0151 | 0.0442 | 0.0164 | 0.0360 | 0.0011 | 17.5% | 51.0% | 18.9% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | central | 32 | 4 | 0.2833 | 1.1345 | 0.0430 | 0.1766 | 0.0656 | 0.0836 | 0.0046 | 15.2% | 62.3% | 23.1% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | central | 64 | 4 | 0.5457 | 2.1840 | 0.0669 | 0.3533 | 0.1311 | 0.1470 | 0.0092 | 12.3% | 64.7% | 24.0% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | aggressive | 1 | 2 | 0.0179 | 0.0363 | 0.0039 | 0.0062 | 0.0017 | 0.0108 | 0.0001 | 21.7% | 34.7% | 9.5% | 1.000 | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | aggressive | 8 | 2 | 0.0751 | 0.1506 | 0.0122 | 0.0497 | 0.0137 | 0.0216 | 0.0011 | 16.3% | 66.2% | 18.2% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | aggressive | 32 | 2 | 0.2711 | 0.5425 | 0.0347 | 0.1990 | 0.0546 | 0.0585 | 0.0046 | 12.8% | 73.4% | 20.1% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | aggressive | 64 | 2 | 0.5324 | 1.0651 | 0.0540 | 0.3980 | 0.1092 | 0.1078 | 0.0092 | 10.1% | 74.8% | 20.5% | 1.000 | kv_beachfront_C8 |

## B300 full-FP32 roof sensitivity at 200K

The checked NVIDIA DGX B300 datasheet and system guide do not
publish a full-FP32 roof. The configured 90 TOP/s value is assumed.
The 19.5-TOP/s endpoint is A100's published full-FP32 rate used only
as a deliberately low stress case; 45 and 180 TOP/s are half/double
sweep points, not vendor claims. Each cell is the fastest feasible
B300 cluster's per-user token rate at the stated active batch.

| Model | B | FP32 op share | 19.5 TOP/s | 45 TOP/s | 90 TOP/s | 180 TOP/s | Fastest cluster(s) | Binding(s) | Central ROM/GPU ratio range |
|---|---:|---:|---:|---:|---:|---:|---|---|---:|
| DeepSeek-V4-Flash-0731 | 1 | 0.136% | 1,650.7 | 1,650.7 | 1,650.7 | 1,650.7 | NVIDIA-B300-x8 | gpu_weight_memory_C3 | 7.65×–7.65× |
| DeepSeek-V4-Flash-0731 | 8 | 0.136% | 1,006.3 | 1,006.3 | 1,006.3 | 1,006.3 | NVIDIA-B300-x16 | gpu_weight_memory_C3 | 4.67×–4.67× |
| DeepSeek-V4-Flash-0731 | 32 | 0.136% | 506.8 | 506.8 | 506.8 | 506.8 | NVIDIA-B300-x16 | gpu_weight_memory_C3 | 2.94×–2.94× |
| DeepSeek-V4-Flash-0731 | 64 | 0.136% | 355.8 | 355.8 | 355.8 | 355.8 | NVIDIA-B300-x16 | gpu_weight_memory_C3 | 2.19×–2.19× |
| DeepSeek-V4-Pro-0813 | 1 | 0.116% | 651.5 | 651.5 | 651.5 | 651.5 | NVIDIA-B300-x16 | gpu_weight_memory_C3 | 12.60×–12.60× |
| DeepSeek-V4-Pro-0813 | 8 | 0.116% | 385.5 | 385.5 | 385.5 | 385.5 | NVIDIA-B300-x16 | gpu_weight_memory_C3 | 7.47×–7.47× |
| DeepSeek-V4-Pro-0813 | 32 | 0.116% | 157.9 | 157.9 | 157.9 | 157.9 | NVIDIA-B300-x16 | gpu_weight_memory_C3 | 5.58×–5.58× |
| DeepSeek-V4-Pro-0813 | 64 | 0.116% | 101.6 | 101.6 | 101.6 | 101.6 | NVIDIA-B300-x16 | gpu_weight_memory_C3 | 4.51×–4.51× |

## Central-envelope achieved byte rates at 200K

These are rates implied by achieved token throughput, not raw hardware
bandwidth. ROM arrays carry only weights; HBM carries only mutable KV on
the proposed wafer. GPU HBM carries both deployed weights and KV.

| Model | B | Architecture | Deployed weight read | KV read+write | Total HBM | Tensor operations |
|---|---:|---|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | ROM-wafer-N4-class-HBM3e-central | 141.67 TB/s | 4.010 TB/s | 4.01 TB/s | 0.63 Pop/s |
| DeepSeek-V4-Flash-0731 | 1 | NVIDIA-B300-x8 | 18.52 TB/s | 0.524 TB/s | 19.04 TB/s | 0.08 Pop/s |
| DeepSeek-V4-Flash-0731 | 8 | ROM-wafer-N4-class-HBM3e-central | 156.01 TB/s | 11.935 TB/s | 11.93 TB/s | 1.88 Pop/s |
| DeepSeek-V4-Flash-0731 | 8 | NVIDIA-B300-x16 | 33.41 TB/s | 2.556 TB/s | 35.97 TB/s | 0.40 Pop/s |
| DeepSeek-V4-Flash-0731 | 32 | ROM-wafer-N4-class-HBM3e-central | 128.21 TB/s | 15.141 TB/s | 15.14 TB/s | 2.38 Pop/s |
| DeepSeek-V4-Flash-0731 | 32 | NVIDIA-B300-x16 | 43.61 TB/s | 5.149 TB/s | 48.75 TB/s | 0.81 Pop/s |
| DeepSeek-V4-Flash-0731 | 64 | ROM-wafer-N4-class-HBM3e-central | 95.70 TB/s | 15.851 TB/s | 15.85 TB/s | 2.49 Pop/s |
| DeepSeek-V4-Flash-0731 | 64 | NVIDIA-B300-x16 | 43.65 TB/s | 7.229 TB/s | 50.88 TB/s | 1.14 Pop/s |
| DeepSeek-V4-Pro-0813 | 1 | ROM-wafer-N4-class-HBM3e-central | 1,315.67 TB/s | 15.693 TB/s | 15.69 TB/s | 4.81 Pop/s |
| DeepSeek-V4-Pro-0813 | 1 | NVIDIA-B300-x16 | 25.84 TB/s | 0.308 TB/s | 26.15 TB/s | 0.09 Pop/s |
| DeepSeek-V4-Pro-0813 | 8 | ROM-wafer-N4-class-HBM3e-central | 1,434.51 TB/s | 43.742 TB/s | 43.74 TB/s | 13.41 Pop/s |
| DeepSeek-V4-Pro-0813 | 8 | NVIDIA-B300-x16 | 47.86 TB/s | 1.459 TB/s | 49.32 TB/s | 0.45 Pop/s |
| DeepSeek-V4-Pro-0813 | 32 | ROM-wafer-N4-class-HBM3e-central | 1,243.26 TB/s | 53.440 TB/s | 53.44 TB/s | 16.38 Pop/s |
| DeepSeek-V4-Pro-0813 | 32 | NVIDIA-B300-x16 | 55.61 TB/s | 2.390 TB/s | 58.00 TB/s | 0.73 Pop/s |
| DeepSeek-V4-Pro-0813 | 64 | ROM-wafer-N4-class-HBM3e-central | 1,005.75 TB/s | 55.490 TB/s | 55.49 TB/s | 17.01 Pop/s |
| DeepSeek-V4-Pro-0813 | 64 | NVIDIA-B300-x16 | 55.76 TB/s | 3.076 TB/s | 58.84 TB/s | 0.94 Pop/s |

## ROM uncertainty bands across context and batch

An `infeasible–high` interval means at least one deterministic hardware
envelope cannot place the checkpoint or resident KV sessions. Numeric
lows are reported only when every envelope is feasible.

| Model | Context | B/stage | Feasible envelopes | ROM user tok/s low–high | Same-B ROM/GPU low–high | Binding terms across envelopes |
|---|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | 3/3 | 1,666.2–58,362.1 | 1.00×–34.93× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | 3/3 | 1,460.6–32,673.5 | 1.41×–31.51× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | 3/3 | 971.3–12,461.0 | 1.80×–23.13× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | 3/3 | 661.4–6,805.6 | 1.70×–17.54× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | 3/3 | 1,666.2–58,362.1 | 1.00×–34.98× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | 3/3 | 1,452.6–26,051.1 | 1.41×–25.22× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | 3/3 | 957.3–8,860.9 | 1.79×–16.58× | collective_floor_C6, kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | 3/3 | 647.6–4,713.7 | 1.69×–12.29× | collective_floor_C6, kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | 3/3 | 1,637.9–42,373.7 | 0.99×–25.67× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | 3/3 | 1,117.2–10,654.6 | 1.11×–10.59× | collective_floor_C6, kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | 3/3 | 514.9–2,987.4 | 1.02×–5.89× | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | 3/3 | 299.4–1,524.6 | 0.84×–4.29× | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | 3/3 | 1,333.4–17,615.7 | 0.85×–11.21× | collective_floor_C6, kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | 3/3 | 474.5–2,784.0 | 0.53×–3.11× | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | 3/3 | 147.1–716.3 | 0.36×–1.76× | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | 3/3 | 76.6–359.9 | 0.29×–1.36× | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | 3/3 | 1,082.6–31,846.4 | 1.66×–48.71× | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | 3/3 | 769.3–13,969.0 | 1.96×–35.64× | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | 3/3 | 364.4–4,684.1 | 2.25×–28.88× | collective_floor_C6, compute_C5 |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | 3/3 | 214.2–2,455.9 | 2.04×–23.34× | collective_floor_C6, compute_C5 |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | 3/3 | 1,082.6–31,846.4 | 1.66×–48.74× | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | 3/3 | 764.5–13,969.0 | 1.96×–35.72× | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | 3/3 | 360.2–4,514.4 | 2.23×–27.93× | collective_floor_C6, compute_C5 |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | 3/3 | 211.2–2,363.7 | 2.02×–22.57× | collective_floor_C6, compute_C5 |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | 3/3 | 1,082.6–27,563.5 | 1.66×–42.31× | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | 3/3 | 700.1–6,640.4 | 1.82×–17.22× | collective_floor_C6, kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | 3/3 | 307.0–1,843.2 | 1.94×–11.67× | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | 3/3 | 175.5–938.9 | 1.73×–9.24× | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | 3/3 | 878.0–11,866.9 | 1.37×–18.48× | collective_floor_C6, kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | 3/3 | 295.9–1,870.9 | 0.82×–5.18× | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | 3/3 | 90.4–481.2 | 0.64×–3.39× | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | 3/3 | 46.9–241.8 | 0.53×–2.72× | kv_beachfront_C8 |
| Qwen3-8B | 8,192 | 1 | 3/3 | 1,625.2–21,865.9 | 0.91×–12.21× | collective_floor_C6, kv_beachfront_C8 |
| Qwen3-8B | 8,192 | 8 | 3/3 | 602.2–3,491.8 | 0.42×–2.43× | kv_beachfront_C8 |
| Qwen3-8B | 8,192 | 32 | 3/3 | 190.7–899.7 | 0.22×–1.05× | kv_beachfront_C8 |
| Qwen3-8B | 8,192 | 64 | 3/3 | 99.8–452.2 | 0.18×–0.81× | kv_beachfront_C8 |
| Qwen3-8B | 32,768 | 1 | 3/3 | 948.9–6,866.7 | 0.57×–4.15× | kv_beachfront_C8 |
| Qwen3-8B | 32,768 | 8 | 3/3 | 193.5–921.2 | 0.21×–0.98× | kv_beachfront_C8 |
| Qwen3-8B | 32,768 | 32 | 3/3 | 51.9–232.1 | 0.14×–0.61× | kv_beachfront_C8 |
| Qwen3-8B | 32,768 | 64 | 3/3 | 26.3–116.2 | 0.12×–0.55× | kv_beachfront_C8 |

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
