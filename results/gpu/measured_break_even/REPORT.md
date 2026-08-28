# OpenTallas measured local-GPU break-even requirements

> **Outcome:** the local GPU service timing is measured, and the model
> accounting is pinned to the exact served checkpoint. The resulting
> OpenTallas values are requirements, not achieved performance.

## Measurement contract

- GPU: `NVIDIA RTX PRO 6000 Blackwell Workstation Edition` (`GPU-592644b2-d169-3424-56fd-98aea433ef09`)
- Endpoint: `qwen-fast` / `Qwen/Qwen3-VL-30B-A3B-Instruct-FP8`
- Accounting snapshot revision: `d9748a51ae66354c4dad665aab2c71f26cf2c8cd`
- Runtime revision linkage: endpoint API reports the matching model root but not a revision; accounting uses the sole locally cached snapshot selected by the default main ref, so exact runtime revision is strongly linked but not API-attested
- Evidence class: `shared_contended`
- Energy: **unavailable for attribution** because unrelated workloads remained active

## Measured service distribution

| Prompt | Completion | Concurrency | Repetitions | Median aggregate tok/s | Observed range | Median TTFT | Median E2E |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 256 | 256 | 1 | 3 | 188.222 | 187.456–188.511 | 18.149 ms | 1360.094 ms |
| 8,192 | 256 | 1 | 3 | 132.270 | 124.724–152.387 | 28.598 ms | 1935.436 ms |
| 32,768 | 256 | 1 | 3 | 58.093 | 33.416–91.664 | 130.162 ms | 4406.709 ms |

These are shared-service observations, not a clean RTX PRO 6000 peak.
The range is the observed repetition range, not a confidence interval.
End-to-end timing includes prompt ingestion/prefill; it is a service-level
threshold and cannot be substituted for a pure decode-only comparison.

## Reference measured equality threshold

The governed reference is the 8,192-token prompt, 256-token completion, concurrency 1 point. Its median measured service rate is **132.270 completion tokens/s**.

| Necessary equality requirement | Value | Evidence |
| --- | ---: | --- |
| Aggregate completion rate | 132.270 token/s | measured median |
| Observed comparator range | 124.724–152.387 token/s | measured repetitions |
| Maximum aggregate token interval | 7.560297 ms | inverse of measured median |
| Full endpoint checkpoint capacity | 32.252 GB | exact tensor headers |
| Text-image capacity | 31.175 GB | exact tensor roles |
| Active immutable bytes/token | 3.366 GB | exact dense + 8/128 experts |
| Effective active-weight service | 445.285 GB/s | derived from measured rate |
| Logical KV read service | 108.176 GB/s | topology-derived, not measured HBM |
| Logical KV write service | 13.003 MB/s | topology-derived, not measured HBM |
| Matrix-operation lower bound | 0.805 TOP/s | checkpoint-derived lower bound |
| Attributable energy | unavailable | shared whole-GPU power rejected |

The exact matrix lower-bound mix at equality is:

- `bf16_x_bf16`: 85.644 Gop/s
- `fp8_e4m3_x_fp8_e4m3`: 718.995 Gop/s

This operation count is deliberately a lower bound. It excludes
normalization, rotary embedding, softmax, routing selection, sampling,
and other vector/control work.

## Capacity density required for one wafer

| Scenario | ROM area | Required usable density | Required raw density |
| --- | ---: | ---: | ---: |
| `35pct_area_conservative` | 16,178.7 mm² | 15.948 Mbit/mm² | 19.935 Mbit/mm² |
| `48pct_area_central` | 22,188.0 mm² | 11.629 Mbit/mm² | 13.522 Mbit/mm² |
| `55pct_area_aggressive` | 25,423.8 mm² | 10.149 Mbit/mm² | 11.276 Mbit/mm² |

These density requirements retain the full multimodal endpoint checkpoint
even though the measurement exercises text-only decode. They do not include
a target ROM compiler, periphery closure, sense margin, repair, or yield.

## Context and speedup requirements

| Prompt | Target | Required tok/s | Active-weight service | Logical KV read | Matrix lower bound | Max interval |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 256 | 1.0x | 188.222 | 633.649 GB/s | 7.096 GB/s | 1.145 TOP/s | 5.313 ms |
| 256 | 2.0x | 376.445 | 1267.297 GB/s | 14.192 GB/s | 2.290 TOP/s | 2.656 ms |
| 8,192 | 1.0x | 132.270 | 445.285 GB/s | 108.176 GB/s | 0.805 TOP/s | 7.560 ms |
| 8,192 | 2.0x | 264.540 | 890.571 GB/s | 216.351 GB/s | 1.609 TOP/s | 3.780 ms |
| 32,768 | 1.0x | 58.093 | 195.570 GB/s | 187.860 GB/s | 0.353 TOP/s | 17.214 ms |
| 32,768 | 2.0x | 116.186 | 391.141 GB/s | 375.719 GB/s | 0.707 TOP/s | 8.607 ms |

## Evidence decomposition

| Class | Included quantities |
| --- | --- |
| measured | request token usage; TTFT and end-to-end service timing; observed aggregate completion rate distribution; GPU identity and shared process inventory |
| checkpoint_derived | full and text-image immutable capacity; active selected-expert and dense weight bytes; checkpoint-declared matrix-operation lower bound |
| architecture_derived | logical BF16 KV read/write traffic from attention topology |
| unavailable | attributable GPU energy or power; clean peak RTX PRO 6000 throughput; measured HBM bytes; production router traces and expert locality; achieved OpenTallas capacity, bandwidth, arithmetic, latency, or energy; API-attested served checkpoint revision |

## Claim boundary

- This artifact uses a measured same-checkpoint service comparator, but the GPU was shared and contended; it is not a clean peak-GPU characterization.
- Only token usage and service timing are measured. Model bytes and matrix-operation lower bounds come from the exact pinned tensor headers; logical KV traffic comes from the declared topology.
- Whole-GPU power and joules are not attributed because unrelated workloads remained active.
- The matrix-operation values are lower bounds and omit vector, routing, sampling, and control work.
- Every OpenTallas value is a necessary inverse requirement, not an achieved implementation result.
- A performance-superiority claim still requires a statistically governed same-model comparison with accuracy, latency, context, concurrency, software, and power scope controlled.
