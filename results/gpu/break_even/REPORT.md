# OpenTallas inverse GPU break-even requirements

> **Outcome:** this report derives what OpenTallas would have to achieve;
> it does not report that OpenTallas achieves it. The DeepSeek/B300 model
> and the local Qwen service observation remain deliberately separate.

## Reference equality threshold

The governed reference is `DeepSeek-V4-Flash-0731` on
`NVIDIA-B300-x1` at context
8,192, batch 1. Its analytical target is
**438.315 aggregate tokens/s**. To claim
higher performance, a same-model measurement must be strictly above this
number under the same comparison contract.

| Necessary equality requirement | Value |
| --- | ---: |
| Full usable ROM checkpoint capacity | 166.879 GB |
| Effective active-weight bandwidth | 4.917 TB/s |
| Effective mutable-KV bandwidth | 5.775 GB/s |
| Minimum active-batch KV capacity | 31.953 MB |
| Exact tensor-operation rate | 12.948 TOP/s |
| Effective cross-stage payload lower bound | 14.363 MB/s |
| Absolute decode interval ceiling | 2.281467 ms |
| B300 allocated-energy parity | 4.135158 J/token |
| Energy parity per tensor operation | 139.987 pJ/op |

The interval ceiling is not a component budget: ROM, arithmetic, HBM, NoC,
clock margin, synchronization, and any pipeline bubbles must fit together.

## Exact arithmetic requirement at the reference point

| Format | Required operations/s |
| --- | ---: |
| `bf16_x_bf16` | 901.058 Gop/s |
| `fp32_x_fp32` | 29.702 Gop/s |
| `fp4_e2m1_x_fp4_e2m1` | 308.855 Gop/s |
| `fp8_e4m3_x_fp8_e4m3` | 6.016 Top/s |
| `mxfp4_e2m1_x_fp8_e4m3` | 5.692 Top/s |

The current public integer-DV RTL does not implement these arithmetic
formats, so this table is an implementation requirement, not compute proof.

## Capacity density required for one wafer

| ROM-area scenario | ROM area | Required usable density | Required raw macro density |
| --- | ---: | ---: | ---: |
| `35pct_area_conservative` | 16,178.7 mm^2 | 82.517 Mbit/mm^2 | 103.147 Mbit/mm^2 |
| `48pct_area_central` | 22,188.0 mm^2 | 60.169 Mbit/mm^2 | 69.964 Mbit/mm^2 |
| `55pct_area_aggressive` | 25,423.8 mm^2 | 52.511 Mbit/mm^2 | 58.346 Mbit/mm^2 |

Raw density divides by the declared usable-capacity fraction. It still
does not include an N4 compiler result, sense margin, repair layout,
periphery closure, or a foundry-calibrated scaling error bar.

## Public-assumption envelope screen

| Envelope | Usable capacity | Minimum stages | One-wafer fit? | Reference raw-BW headroom |
| --- | ---: | ---: | --- | ---: |
| `conservative` | 101.111 GB | 2 | no | 148.1x |
| `central` | 242.651 GB | 1 | yes | 528.0x |
| `aggressive` | 473.644 GB | 1 | yes | 1,163.4x |

This is only arithmetic headroom under public and assumed inputs. Large
array-bandwidth headroom cannot be converted into a performance claim
until simultaneous read activity, power delivery, timing, and exact
arithmetic are implemented and validated.

## Context, batch, and speedup sensitivity

| Context | Batch | Target | Aggregate tok/s | Effective ROM BW | Raw HBM BW | Tensor op/s | Iso-power J/token |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8,192 | 1 | 1.0x | 438.315 | 4.917 TB/s | 8.251 GB/s | 12.948 TOP/s | 4.135158 |
| 8,192 | 1 | 2.0x | 876.629 | 9.834 TB/s | 16.501 GB/s | 25.895 TOP/s | 2.067579 |
| 8,192 | 8 | 1.0x | 1068.917 | 4.436 TB/s | 20.121 GB/s | 31.575 TOP/s | 1.695641 |
| 8,192 | 8 | 2.0x | 2137.835 | 8.873 TB/s | 40.242 GB/s | 63.151 TOP/s | 0.847821 |
| 8,192 | 32 | 1.0x | 1599.420 | 4.300 TB/s | 30.107 GB/s | 47.246 TOP/s | 1.133223 |
| 8,192 | 32 | 2.0x | 3198.840 | 8.601 TB/s | 60.214 GB/s | 94.492 TOP/s | 0.566612 |
| 8,192 | 64 | 1.0x | 2227.374 | 4.270 TB/s | 41.927 GB/s | 65.796 TOP/s | 0.813739 |
| 8,192 | 64 | 2.0x | 4454.748 | 8.539 TB/s | 83.855 GB/s | 131.591 TOP/s | 0.406869 |
| 32,768 | 1 | 1.0x | 437.886 | 4.912 TB/s | 15.131 GB/s | 14.081 TOP/s | 4.139205 |
| 32,768 | 1 | 2.0x | 875.772 | 9.824 TB/s | 30.263 GB/s | 28.162 TOP/s | 2.069602 |
| 32,768 | 8 | 1.0x | 1066.373 | 4.426 TB/s | 36.849 GB/s | 34.291 TOP/s | 1.699687 |
| 32,768 | 8 | 2.0x | 2132.745 | 8.851 TB/s | 73.698 GB/s | 68.582 TOP/s | 0.849844 |
| 32,768 | 32 | 1.0x | 1593.730 | 4.285 TB/s | 55.072 GB/s | 51.249 TOP/s | 1.137269 |
| 32,768 | 32 | 2.0x | 3187.459 | 8.570 TB/s | 110.145 GB/s | 102.499 TOP/s | 0.568635 |
| 32,768 | 64 | 1.0x | 2216.353 | 4.249 TB/s | 76.588 GB/s | 71.271 TOP/s | 0.817785 |
| 32,768 | 64 | 2.0x | 4432.706 | 8.497 TB/s | 153.175 GB/s | 142.542 TOP/s | 0.408892 |
| 200,000 | 1 | 1.0x | 434.992 | 4.880 TB/s | 61.601 GB/s | 21.734 TOP/s | 4.166741 |
| 200,000 | 1 | 2.0x | 869.985 | 9.759 TB/s | 123.203 GB/s | 43.469 TOP/s | 2.083370 |
| 200,000 | 8 | 1.0x | 1049.372 | 4.355 TB/s | 148.607 GB/s | 52.432 TOP/s | 1.727223 |
| 200,000 | 8 | 2.0x | 2098.744 | 8.710 TB/s | 297.213 GB/s | 104.864 TOP/s | 0.863612 |
| 200,000 | 32 | 1.0x | 1556.054 | 4.184 TB/s | 220.360 GB/s | 77.748 TOP/s | 1.164805 |
| 200,000 | 32 | 2.0x | 3112.108 | 8.367 TB/s | 440.721 GB/s | 155.497 TOP/s | 0.582403 |
| 200,000 | 64 | 1.0x | 2144.156 | 4.110 TB/s | 303.644 GB/s | 107.133 TOP/s | 0.845321 |
| 200,000 | 64 | 2.0x | 4288.313 | 8.220 TB/s | 607.289 GB/s | 214.266 TOP/s | 0.422660 |
| 1,000,000 | 1 | 1.0x | 421.663 | 4.730 TB/s | 275.650 GB/s | 56.993 TOP/s | 4.298456 |
| 1,000,000 | 1 | 2.0x | 843.326 | 9.460 TB/s | 551.301 GB/s | 113.986 TOP/s | 2.149228 |
| 1,000,000 | 8 | 1.0x | 975.019 | 4.047 TB/s | 637.391 GB/s | 131.785 TOP/s | 1.858939 |
| 1,000,000 | 8 | 2.0x | 1950.037 | 8.093 TB/s | 1274.782 GB/s | 263.571 TOP/s | 0.929469 |

Comparator-infeasible points were not assigned thresholds:

- Context 1,000,000, batch 32.
- Context 1,000,000, batch 64.

## Local Qwen observation

Attached run: `local-rtx-pro-6000-shared-serving-v1` (pass,
`shared_contended`). It is shown only as a local Qwen
service target and is not substituted into any DeepSeek threshold.

| Qwen prompt | Concurrency | Successful requests | Median TTFT | Median E2E | Median completion tok/s E2E |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 256 | 1 | 2 | 16.563 ms | 373.884 ms | 171.342 |
| 256 | 2 | 4 | 26.362 ms | 450.141 ms | 142.393 |
| 2048 | 1 | 2 | 20.588 ms | 355.165 ms | 180.198 |
| 8192 | 1 | 2 | 30.188 ms | 388.171 ms | 164.876 |

## Claim boundary

- Every number in this artifact is an inverse requirement or an assumption screen; none is an achieved OpenTallas result.
- The DeepSeek/B300 thresholds and local Qwen measurement are separate because they do not execute the same checkpoint.
- Public ROM-density and bandwidth anchors do not validate an N4 ROM compiler, PVT margin, simultaneous-array power, or manufacturability.
- A generic FP8 ceiling is not evidence that the exact FP8, MXFP4 x FP8, FP4, BF16, and FP32 operation mix is implemented.
- Strict performance superiority requires same-model measurement above the equality threshold with accuracy, latency, context, batch, concurrency, power scope, and software stack controlled.
