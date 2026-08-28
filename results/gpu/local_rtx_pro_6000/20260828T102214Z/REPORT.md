# Local RTX PRO 6000 shared-serving measurement

> **Evidence class: shared and contended.** This is a Qwen service-level
> observation, not a clean peak-GPU benchmark, a DeepSeek-V4 comparison,
> an OpenTallas implementation result, or attributable energy evidence.

- Status: **FAIL**
- Benchmark: `local-rtx-pro-6000-shared-serving-v1`
- Generated: `2026-08-28T10:22:18.752+00:00`
- Endpoint model: `qwen-fast`
- Endpoint root: `Qwen/Qwen3-VL-30B-A3B-Instruct-FP8`
- GPU: `NVIDIA RTX PRO 6000 Blackwell Workstation Edition`
- GPU UUID: `GPU-592644b2-d169-3424-56fd-98aea433ef09`

## Scenario medians

Completion rate includes all completion tokens. The post-TTFT value is a
service proxy; SSE chunk arrivals are not guaranteed to be token arrivals.

| Prompt tokens | Concurrency | Requests | TTFT ms | End-to-end ms | Completion tok/s (E2E) | Completion tok/s (post-TTFT proxy) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 256 | 1 | 2 | 41.747 | 544.601 | 120.277 | 131.835 |
| 256 | 2 | 4 | 24.425 | 432.978 | 147.818 | 156.694 |
| 2048 | 1 | 2 | 57.066 | 560.629 | 114.629 | 127.340 |
| 8192 | 1 | 2 | 113.034 | 578.527 | 114.694 | 138.063 |

## Individual requests

| Request | Prompt | Conc. | Status | TTFT ms | End-to-end ms | Completion tokens | Finish |
| --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| `p00-r00-c00` | 256 | 1 | PASS | 52.796 | 462.114 | 64 | length |
| `p00-r01-c00` | 256 | 1 | PASS | 30.697 | 627.088 | 64 | length |
| `p01-r00-c00` | 2048 | 1 | PASS | 70.897 | 596.572 | 64 | length |
| `p01-r01-c00` | 2048 | 1 | PASS | 43.235 | 524.686 | 64 | length |
| `p02-r00-c00` | 8192 | 1 | PASS | 191.959 | 687.484 | 64 | length |
| `p02-r01-c00` | 8192 | 1 | PASS | 34.109 | 469.571 | 64 | length |
| `p03-r00-c00` | 256 | 2 | PASS | 31.452 | 435.802 | 64 | length |
| `p03-r00-c01` | 256 | 2 | PASS | 17.626 | 430.518 | 64 | length |
| `p03-r01-c00` | 256 | 2 | PASS | 31.074 | 435.437 | 64 | length |
| `p03-r01-c01` | 256 | 2 | PASS | 17.776 | 430.375 | 64 | length |

## Shared-GPU observation

Observed whole-GPU power samples spanned 214.70–393.42 W; utilization samples spanned 0.0–100.0% when available.

Window-integrated joules are retained in `measurement.json` only as
contaminated whole-GPU observations. They are not divided by requests or
tokens and are not attributed to this benchmark because other workloads
were active.

## Claim boundary

- The endpoint serves Qwen3-VL-30B-A3B-Instruct-FP8, not a DeepSeek-V4 checkpoint.
- Other serving and audio processes share the GPU, so the run is not a clean peak-throughput or energy benchmark.
- SSE content-event timing is only a chunk-arrival proxy because one event need not equal one generated token.
- No whole-GPU energy value from this shared run is attributable to an individual request or model.
- The measurement supplies a local service target; it does not demonstrate OpenTallas performance.
