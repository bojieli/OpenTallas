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

| Model | Official checkpoint | Deployment representation | Resident bytes | 200K tensor ops/token | Dense / routed format |
|---|---:|---|---:|---:|---|
| DeepSeek-V4-Flash-0731 | 166.9 GB | official_packed | 166.9 GB | 50.0 Gop | fp8_e4m3_x_fp8_e4m3 / mxfp4_e2m1_x_fp8_e4m3 |
| DeepSeek-V4-Pro-0813 | 892.7 GB | official_packed | 892.7 GB | 145.1 Gop | fp8_e4m3_x_fp8_e4m3 / mxfp4_e2m1_x_fp8_e4m3 |

## Mechanical consistency audit

| Status | Checks | Max weight/shared-HBM service | Max KV service | Max compute service | Max cooling |
|---|---:|---:|---:|---:|---:|
| PASS | 7,881 | 100.0% | 84.9% | 65.1% | 100.0% |

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
| DeepSeek-V4-Flash-0731 | 1 | 1 | 1 | 14,435.9 | NVIDIA-B300-x8 | 1,665.9 | 8.67× | 8.67× | 0.1833 | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 8 | 1 | 8 | 7,911.5 | NVIDIA-B300-x16 | 1,029.2 | 7.69× | 7.69× | 0.0418 | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 32 | 1 | 32 | 3,073.7 | NVIDIA-B300-x16 | 530.6 | 5.79× | 5.79× | 0.0269 | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 64 | 1 | 64 | 1,693.3 | NVIDIA-B300-x16 | 379.7 | 4.46× | 4.46× | 0.0244 | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 1 | 4 | 4 | 8,283.1 | NVIDIA-B300-x16 | 653.2 | 12.68× | 16.03× | 0.2149 | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 8 | 4 | 32 | 4,343.2 | NVIDIA-B300-x16 | 390.4 | 11.12× | 26.95× | 0.0515 | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 32 | 4 | 128 | 1,539.8 | NVIDIA-B300-x16 | 161.2 | 9.55× | 20.56× | 0.0364 | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 64 | 4 | 256 | 827.5 | NVIDIA-B300-x16 | 104.4 | 7.93× | 13.80× | 0.0339 | collective_floor_C6 |

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
| DeepSeek-V4-Flash-0731 | 1 | ROM-wafer-N4-class-HBM3e-central | 43.88 Gitem/s | 970.09 Gitem/s | 26.44 Gitem/s | 9.06 Gitem/s | 15.16 Gitem/s | 397.27 Mitem/s |
| DeepSeek-V4-Flash-0731 | 1 | NVIDIA-B300-x8 | 5.06 Gitem/s | 111.95 Gitem/s | 3.05 Gitem/s | 1.05 Gitem/s | 1.75 Gitem/s | 45.85 Mitem/s |
| DeepSeek-V4-Flash-0731 | 8 | ROM-wafer-N4-class-HBM3e-central | 192.39 Gitem/s | 4.25 Titem/s | 115.91 Gitem/s | 39.71 Gitem/s | 66.46 Gitem/s | 1.74 Gitem/s |
| DeepSeek-V4-Flash-0731 | 8 | NVIDIA-B300-x16 | 25.03 Gitem/s | 553.30 Gitem/s | 15.08 Gitem/s | 5.17 Gitem/s | 8.65 Gitem/s | 226.59 Mitem/s |
| DeepSeek-V4-Flash-0731 | 32 | ROM-wafer-N4-class-HBM3e-central | 298.99 Gitem/s | 6.61 Titem/s | 180.14 Gitem/s | 61.72 Gitem/s | 103.28 Gitem/s | 2.71 Gitem/s |
| DeepSeek-V4-Flash-0731 | 32 | NVIDIA-B300-x16 | 51.62 Gitem/s | 1.14 Titem/s | 31.10 Gitem/s | 10.65 Gitem/s | 17.83 Gitem/s | 467.29 Mitem/s |
| DeepSeek-V4-Flash-0731 | 64 | ROM-wafer-N4-class-HBM3e-central | 329.42 Gitem/s | 7.28 Titem/s | 198.47 Gitem/s | 68.00 Gitem/s | 113.79 Gitem/s | 2.98 Gitem/s |
| DeepSeek-V4-Flash-0731 | 64 | NVIDIA-B300-x16 | 73.87 Gitem/s | 1.63 Titem/s | 44.50 Gitem/s | 15.25 Gitem/s | 25.52 Gitem/s | 668.75 Mitem/s |
| DeepSeek-V4-Pro-0813 | 1 | ROM-wafer-N4-class-HBM3e-central | 99.68 Gitem/s | 856.56 Gitem/s | 43.86 Gitem/s | 11.72 Gitem/s | 13.38 Gitem/s | 342.63 Mitem/s |
| DeepSeek-V4-Pro-0813 | 1 | NVIDIA-B300-x16 | 7.27 Gitem/s | 62.71 Gitem/s | 3.27 Gitem/s | 872.15 Mitem/s | 979.82 Mitem/s | 25.50 Mitem/s |
| DeepSeek-V4-Pro-0813 | 8 | ROM-wafer-N4-class-HBM3e-central | 416.17 Gitem/s | 3.58 Titem/s | 183.11 Gitem/s | 48.92 Gitem/s | 55.88 Gitem/s | 1.43 Gitem/s |
| DeepSeek-V4-Pro-0813 | 8 | NVIDIA-B300-x16 | 34.76 Gitem/s | 299.84 Gitem/s | 15.63 Gitem/s | 4.17 Gitem/s | 4.68 Gitem/s | 121.93 Mitem/s |
| DeepSeek-V4-Pro-0813 | 32 | ROM-wafer-N4-class-HBM3e-central | 588.21 Gitem/s | 5.05 Titem/s | 258.80 Gitem/s | 69.15 Gitem/s | 78.98 Gitem/s | 2.02 Gitem/s |
| DeepSeek-V4-Pro-0813 | 32 | NVIDIA-B300-x16 | 57.40 Gitem/s | 495.15 Gitem/s | 25.81 Gitem/s | 6.89 Gitem/s | 7.74 Gitem/s | 201.36 Mitem/s |
| DeepSeek-V4-Pro-0813 | 64 | ROM-wafer-N4-class-HBM3e-central | 631.74 Gitem/s | 5.43 Titem/s | 277.95 Gitem/s | 74.26 Gitem/s | 84.82 Gitem/s | 2.17 Gitem/s |
| DeepSeek-V4-Pro-0813 | 64 | NVIDIA-B300-x16 | 74.33 Gitem/s | 641.14 Gitem/s | 33.42 Gitem/s | 8.92 Gitem/s | 10.02 Gitem/s | 260.73 Mitem/s |

## ROM component timing and occupancy at 200K

Times are seconds of bottleneck-stage service expressed in milliseconds.
Weight, KV, and compute may overlap; the layer collective is serialized;
pipeline efficiency and any thermal scaling produce the final interval.
The cross-stage entry is the initiation-interval serialization floor, not
the full end-to-end propagation latency. Occupancies are modeled service
time divided by the final interval, not silicon performance counters.

| Model | Envelope | B/stage | Stages | Final interval ms | User latency ms | Weight ms | KV ms | Compute ms | Collective ms | Cross-stage ms | Weight util | KV util | Compute util | Thermal × | Bind |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Flash-0731 | central | 1 | 1 | 0.0693 | 0.0693 | 0.0052 | 0.0044 | 0.0024 | 0.0571 | — | 7.5% | 6.4% | 3.5% | 1.000 | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | central | 8 | 1 | 0.1264 | 0.1264 | 0.0154 | 0.0353 | 0.0194 | 0.0784 | — | 12.2% | 27.9% | 15.4% | 1.000 | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | central | 32 | 1 | 0.3253 | 0.3253 | 0.0400 | 0.1412 | 0.0777 | 0.1516 | — | 12.3% | 43.4% | 23.9% | 1.000 | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | central | 64 | 1 | 0.5906 | 0.5906 | 0.0571 | 0.2825 | 0.1554 | 0.2490 | — | 9.7% | 47.8% | 26.3% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | aggressive | 1 | 1 | 0.0176 | 0.0176 | 0.0022 | 0.0026 | 0.0011 | 0.0141 | — | 12.4% | 14.8% | 6.1% | 1.000 | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | aggressive | 8 | 1 | 0.0457 | 0.0457 | 0.0064 | 0.0208 | 0.0086 | 0.0226 | — | 14.1% | 45.4% | 18.9% | 1.000 | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | aggressive | 32 | 1 | 0.1421 | 0.1421 | 0.0167 | 0.0831 | 0.0345 | 0.0519 | — | 11.7% | 58.5% | 24.3% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | aggressive | 64 | 1 | 0.2706 | 0.2706 | 0.0238 | 0.1661 | 0.0689 | 0.0910 | — | 8.8% | 61.4% | 25.5% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | central | 1 | 4 | 0.0299 | 0.1207 | 0.0048 | 0.0018 | 0.0020 | 0.0221 | 0.0001 | 16.1% | 5.9% | 6.9% | 1.000 | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | central | 8 | 4 | 0.0573 | 0.2302 | 0.0151 | 0.0141 | 0.0164 | 0.0360 | 0.0011 | 26.4% | 24.6% | 28.6% | 1.000 | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | central | 32 | 4 | 0.1621 | 0.6495 | 0.0430 | 0.0563 | 0.0656 | 0.0836 | 0.0046 | 26.5% | 34.7% | 40.5% | 1.000 | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | central | 64 | 4 | 0.3018 | 1.2084 | 0.0669 | 0.1125 | 0.1311 | 0.1470 | 0.0092 | 22.2% | 37.3% | 43.4% | 1.000 | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | aggressive | 1 | 2 | 0.0155 | 0.0314 | 0.0039 | 0.0020 | 0.0017 | 0.0108 | 0.0001 | 25.2% | 13.0% | 11.0% | 1.000 | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | aggressive | 8 | 2 | 0.0397 | 0.0798 | 0.0122 | 0.0161 | 0.0137 | 0.0216 | 0.0011 | 30.8% | 40.6% | 34.4% | 1.000 | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | aggressive | 32 | 2 | 0.1294 | 0.2592 | 0.0347 | 0.0644 | 0.0546 | 0.0585 | 0.0046 | 26.8% | 49.8% | 42.2% | 1.000 | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | aggressive | 64 | 2 | 0.2491 | 0.4985 | 0.0540 | 0.1288 | 0.1092 | 0.1078 | 0.0092 | 21.7% | 51.7% | 43.8% | 1.000 | kv_beachfront_C8 |

## B300 full-FP32 roof sensitivity at 200K

The checked NVIDIA DGX B300 datasheet and system guide do not
publish a full-FP32 roof. The configured 90 TOP/s value is assumed.
The 19.5-TOP/s endpoint is A100's published full-FP32 rate used only
as a deliberately low stress case; 45 and 180 TOP/s are half/double
sweep points, not vendor claims. Each cell is the fastest feasible
B300 cluster's per-user token rate at the stated active batch.

| Model | B | FP32 op share | 19.5 TOP/s | 45 TOP/s | 90 TOP/s | 180 TOP/s | Fastest cluster(s) | Binding(s) | Central ROM/GPU ratio range |
|---|---:|---:|---:|---:|---:|---:|---|---|---:|
| DeepSeek-V4-Flash-0731 | 1 | 0.136% | 1,665.9 | 1,665.9 | 1,665.9 | 1,665.9 | NVIDIA-B300-x8 | gpu_weight_memory_C3 | 8.67×–8.67× |
| DeepSeek-V4-Flash-0731 | 8 | 0.136% | 1,029.2 | 1,029.2 | 1,029.2 | 1,029.2 | NVIDIA-B300-x16 | gpu_weight_memory_C3 | 7.69×–7.69× |
| DeepSeek-V4-Flash-0731 | 32 | 0.136% | 530.6 | 530.6 | 530.6 | 530.6 | NVIDIA-B300-x16 | gpu_weight_memory_C3 | 5.79×–5.79× |
| DeepSeek-V4-Flash-0731 | 64 | 0.136% | 379.7 | 379.7 | 379.7 | 379.7 | NVIDIA-B300-x16 | gpu_weight_memory_C3 | 4.46×–4.46× |
| DeepSeek-V4-Pro-0813 | 1 | 0.116% | 653.2 | 653.2 | 653.2 | 653.2 | NVIDIA-B300-x16 | gpu_weight_memory_C3 | 12.68×–12.68× |
| DeepSeek-V4-Pro-0813 | 8 | 0.116% | 390.4 | 390.4 | 390.4 | 390.4 | NVIDIA-B300-x16 | gpu_weight_memory_C3 | 11.12×–11.12× |
| DeepSeek-V4-Pro-0813 | 32 | 0.116% | 161.2 | 161.2 | 161.2 | 161.2 | NVIDIA-B300-x16 | gpu_weight_memory_C3 | 9.55×–9.55× |
| DeepSeek-V4-Pro-0813 | 64 | 0.116% | 104.4 | 104.4 | 104.4 | 104.4 | NVIDIA-B300-x16 | gpu_weight_memory_C3 | 7.93×–7.93× |

## Central-envelope achieved byte rates at 200K

These are rates implied by achieved token throughput, not raw hardware
bandwidth. ROM arrays carry only weights; HBM carries only mutable KV on
the proposed wafer. GPU HBM carries both deployed weights and KV.

| Model | B | Architecture | Deployed weight read | KV read+write | Total HBM | Tensor operations |
|---|---:|---|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | ROM-wafer-N4-class-HBM3e-central | 161.94 TB/s | 1.431 TB/s | 1.43 TB/s | 0.72 Pop/s |
| DeepSeek-V4-Flash-0731 | 1 | NVIDIA-B300-x8 | 18.69 TB/s | 0.165 TB/s | 18.85 TB/s | 0.08 Pop/s |
| DeepSeek-V4-Flash-0731 | 8 | ROM-wafer-N4-class-HBM3e-central | 262.68 TB/s | 6.274 TB/s | 6.27 TB/s | 3.16 Pop/s |
| DeepSeek-V4-Flash-0731 | 8 | NVIDIA-B300-x16 | 34.17 TB/s | 0.816 TB/s | 34.99 TB/s | 0.41 Pop/s |
| DeepSeek-V4-Flash-0731 | 32 | ROM-wafer-N4-class-HBM3e-central | 264.46 TB/s | 9.750 TB/s | 9.75 TB/s | 4.91 Pop/s |
| DeepSeek-V4-Flash-0731 | 32 | NVIDIA-B300-x16 | 45.65 TB/s | 1.683 TB/s | 47.34 TB/s | 0.85 Pop/s |
| DeepSeek-V4-Flash-0731 | 64 | ROM-wafer-N4-class-HBM3e-central | 207.74 TB/s | 10.743 TB/s | 10.74 TB/s | 5.41 Pop/s |
| DeepSeek-V4-Flash-0731 | 64 | NVIDIA-B300-x16 | 46.58 TB/s | 2.409 TB/s | 48.99 TB/s | 1.21 Pop/s |
| DeepSeek-V4-Pro-0813 | 1 | ROM-wafer-N4-class-HBM3e-central | 1,327.23 TB/s | 5.111 TB/s | 5.11 TB/s | 4.85 Pop/s |
| DeepSeek-V4-Pro-0813 | 1 | NVIDIA-B300-x16 | 25.91 TB/s | 0.100 TB/s | 26.01 TB/s | 0.09 Pop/s |
| DeepSeek-V4-Pro-0813 | 8 | ROM-wafer-N4-class-HBM3e-central | 2,167.62 TB/s | 21.339 TB/s | 21.34 TB/s | 20.27 Pop/s |
| DeepSeek-V4-Pro-0813 | 8 | NVIDIA-B300-x16 | 48.46 TB/s | 0.477 TB/s | 48.94 TB/s | 0.45 Pop/s |
| DeepSeek-V4-Pro-0813 | 32 | ROM-wafer-N4-class-HBM3e-central | 2,173.41 TB/s | 30.160 TB/s | 30.16 TB/s | 28.64 Pop/s |
| DeepSeek-V4-Pro-0813 | 32 | NVIDIA-B300-x16 | 56.78 TB/s | 0.788 TB/s | 57.56 TB/s | 0.75 Pop/s |
| DeepSeek-V4-Pro-0813 | 64 | ROM-wafer-N4-class-HBM3e-central | 1,818.53 TB/s | 32.392 TB/s | 32.39 TB/s | 30.76 Pop/s |
| DeepSeek-V4-Pro-0813 | 64 | NVIDIA-B300-x16 | 57.27 TB/s | 1.020 TB/s | 58.29 TB/s | 0.97 Pop/s |

## ROM uncertainty bands across context and batch

An `infeasible–high` interval means at least one deterministic hardware
envelope cannot place the checkpoint or resident KV sessions. Numeric
lows are reported only when every envelope is feasible.

| Model | Context | B/stage | Feasible envelopes | ROM user tok/s low–high | Same-B ROM/GPU low–high | Binding terms across envelopes |
|---|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Flash-0731 | 8,192 | 1 | 3/3 | 1,666.2–58,362.1 | 1.00×–34.91× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 8,192 | 8 | 3/3 | 1,460.6–32,673.5 | 1.41×–31.46× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 8,192 | 32 | 3/3 | 971.3–12,479.8 | 1.80×–23.08× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 8,192 | 64 | 3/3 | 661.4–6,816.8 | 1.70×–17.48× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 32,768 | 1 | 3/3 | 1,666.2–58,362.1 | 1.00×–34.92× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 32,768 | 8 | 3/3 | 1,452.6–32,673.5 | 1.40×–31.50× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 32,768 | 32 | 3/3 | 957.3–12,267.8 | 1.78×–22.75× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 32,768 | 64 | 3/3 | 647.6–6,690.5 | 1.67×–17.21× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 200,000 | 1 | 3/3 | 1,666.2–56,884.0 | 1.00×–34.15× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 200,000 | 8 | 3/3 | 1,400.3–21,883.3 | 1.36×–21.26× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 200,000 | 32 | 3/3 | 867.1–7,037.4 | 1.63×–13.26× | collective_floor_C6, kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 200,000 | 64 | 3/3 | 567.3–3,695.0 | 1.49×–9.73× | compute_C5, kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 1 | 3/3 | 1,594.9–36,414.5 | 0.97×–22.19× | collective_floor_C6 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 8 | 3/3 | 968.1–8,015.9 | 0.98×–8.08× | collective_floor_C6, kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 32 | 3/3 | 400.0–2,181.9 | 0.81×–4.43× | kv_beachfront_C8 |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 64 | 3/3 | 224.4–1,107.3 | 0.66×–3.24× | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 8,192 | 1 | 3/3 | 1,082.6–31,846.4 | 1.66×–48.70× | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 8,192 | 8 | 3/3 | 769.3–13,969.0 | 1.96×–35.60× | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 8,192 | 32 | 3/3 | 364.4–4,684.1 | 2.24×–28.82× | collective_floor_C6, compute_C5 |
| DeepSeek-V4-Pro-0813 | 8,192 | 64 | 3/3 | 214.2–2,455.9 | 2.03×–23.29× | collective_floor_C6, compute_C5 |
| DeepSeek-V4-Pro-0813 | 32,768 | 1 | 3/3 | 1,082.6–31,846.4 | 1.66×–48.71× | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 32,768 | 8 | 3/3 | 764.5–13,969.0 | 1.95×–35.63× | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 32,768 | 32 | 3/3 | 360.2–4,622.8 | 2.22×–28.48× | collective_floor_C6, compute_C5 |
| DeepSeek-V4-Pro-0813 | 32,768 | 64 | 3/3 | 211.2–2,423.1 | 2.01×–23.01× | collective_floor_C6, compute_C5 |
| DeepSeek-V4-Pro-0813 | 200,000 | 1 | 3/3 | 1,082.6–31,846.4 | 1.66×–48.75× | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 200,000 | 8 | 3/3 | 733.9–12,535.5 | 1.88×–32.11× | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 200,000 | 32 | 3/3 | 334.0–3,857.3 | 2.07×–23.93× | collective_floor_C6, compute_C5, kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 200,000 | 64 | 3/3 | 193.4–2,005.8 | 1.85×–19.22× | collective_floor_C6, compute_C5, kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1 | 3/3 | 1,082.6–23,872.8 | 1.66×–36.70× | collective_floor_C6 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 8 | 3/3 | 612.5–5,116.0 | 1.60×–13.37× | collective_floor_C6, kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 32 | 3/3 | 245.4–1,385.0 | 1.57×–8.89× | kv_beachfront_C8 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 64 | 3/3 | 136.4–702.2 | 1.36×–7.03× | kv_beachfront_C8 |

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
