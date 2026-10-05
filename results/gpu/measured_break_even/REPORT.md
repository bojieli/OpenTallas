# OpenTallas measured local-GPU break-even requirements

> **Outcome:** the local GPU service timing is measured, and the model
> accounting is pinned to the sole snapshot associated with the served
> model root; the API does not attest its revision. The resulting
> OpenTallas values are requirements, not achieved performance.

## Measurement contract

- GPU: `NVIDIA RTX PRO 6000 Blackwell Workstation Edition` (`GPU-592644b2-d169-3424-56fd-98aea433ef09`)
- Endpoint: `qwen-fast` / `Qwen/Qwen3-VL-30B-A3B-Instruct-FP8`
- Endpoint runtime: `vLLM 0.19.0`
- Accounting snapshot revision: `d9748a51ae66354c4dad665aab2c71f26cf2c8cd`
- Runtime revision linkage: model-root plus sole default-ref snapshot linked; revision is not API-attested
- Evidence class: `shared_contended`
- Energy: **unavailable for attribution** because unrelated workloads remained active

## Measured service distribution

| Prompt | Completion | Concurrency | Repetitions | Median aggregate tok/s | Observed range | Median TTFT | Median E2E |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 256 | 256 | 1 | 3 | 156.587 | 144.098–179.648 | 22.359 ms | 1634.871 ms |
| 8,192 | 256 | 1 | 3 | 134.779 | 124.429–156.956 | 32.790 ms | 1899.412 ms |
| 32,768 | 256 | 1 | 3 | 115.537 | 96.752–118.964 | 74.596 ms | 2215.739 ms |

These are shared-service observations, not a clean RTX PRO 6000 peak.
The range is the observed repetition range, not a confidence interval.
End-to-end timing includes prompt ingestion/prefill; it is a service-level
threshold and cannot be substituted for a pure decode-only comparison.

## Reference measured equality threshold

The governed reference is the 8,192-token prompt, 256-token completion, concurrency 1 point. Its median measured service rate is **134.779 completion tokens/s**.

| Necessary equality requirement | Value | Evidence |
| --- | ---: | --- |
| Aggregate completion rate | 134.779 token/s | measured median |
| Observed comparator range | 124.429–156.956 token/s | measured repetitions |
| Maximum aggregate token interval | 7.419579 ms | inverse of measured median |
| Full endpoint checkpoint capacity | 32.252 GB | exact tensor headers |
| Text-image capacity | 31.175 GB | exact tensor roles |
| Active immutable bytes/token | 3.366 GB | exact dense + 8/128 experts |
| Effective active-weight service | 453.731 GB/s | derived from measured rate |
| Logical KV read service | 110.227 GB/s | topology-derived, not measured HBM |
| Logical KV write service | 13.249 MB/s | topology-derived, not measured HBM |
| Matrix-operation lower bound | 0.820 TOP/s | checkpoint-derived lower bound |
| Attributable energy | unavailable | shared whole-GPU power rejected |

The exact matrix lower-bound mix at equality is:

- `bf16_x_bf16`: 87.269 Gop/s
- `fp8_e4m3_x_fp8_e4m3`: 732.632 Gop/s

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
| 256 | 1.0x | 156.587 | 527.150 GB/s | 5.903 GB/s | 0.953 TOP/s | 6.386 ms |
| 256 | 2.0x | 313.175 | 1054.299 GB/s | 11.807 GB/s | 1.905 TOP/s | 3.193 ms |
| 8,192 | 1.0x | 134.779 | 453.731 GB/s | 110.227 GB/s | 0.820 TOP/s | 7.420 ms |
| 8,192 | 2.0x | 269.557 | 907.461 GB/s | 220.455 GB/s | 1.640 TOP/s | 3.710 ms |
| 32,768 | 1.0x | 115.537 | 388.954 GB/s | 373.619 GB/s | 0.703 TOP/s | 8.655 ms |
| 32,768 | 2.0x | 231.074 | 777.909 GB/s | 747.238 GB/s | 1.406 TOP/s | 4.328 ms |

## Evidence decomposition

| Class | Included quantities |
| --- | --- |
| measured | request token usage; TTFT and end-to-end service timing; observed aggregate completion rate distribution; GPU identity and shared process inventory |
| checkpoint_derived | full and text-image immutable capacity; active selected-expert and dense weight bytes; checkpoint-declared matrix-operation lower bound |
| architecture_derived | logical BF16 KV read/write traffic from attention topology |
| unavailable | attributable GPU energy or power; clean peak RTX PRO 6000 throughput; measured HBM bytes; production router traces and expert locality; achieved OpenTallas capacity, bandwidth, arithmetic, latency, or energy; API-attested served checkpoint revision |

## Claim boundary

- This artifact uses a measured model-root-matched service comparator with accounting tied to the sole local snapshot; the endpoint API does not attest its revision.
- The GPU was shared and contended; it is not a clean peak-GPU characterization.
- Only token usage and service timing are measured. Model bytes and matrix-operation lower bounds come from the exact pinned tensor headers; logical KV traffic comes from the declared topology.
- Whole-GPU power and joules are not attributed because unrelated workloads remained active.
- The matrix-operation values are lower bounds and omit vector, routing, sampling, and control work.
- Every OpenTallas value is a necessary inverse requirement, not an achieved implementation result.
- A performance-superiority claim still requires a statistically governed same-model comparison with accuracy, latency, context, concurrency, software, and power scope controlled.
