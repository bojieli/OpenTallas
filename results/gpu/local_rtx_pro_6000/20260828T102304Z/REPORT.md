# Local RTX PRO 6000 shared-serving measurement

> **Evidence class: shared and contended.** This is a Qwen service-level
> observation, not a clean peak-GPU benchmark, a DeepSeek-V4 comparison,
> an OpenTallas implementation result, or attributable energy evidence.

- Status: **PASS**
- Benchmark: `local-rtx-pro-6000-shared-serving-v1`
- Generated: `2026-08-28T10:23:07.736+00:00`
- Endpoint model: `qwen-fast`
- Endpoint root: `Qwen/Qwen3-VL-30B-A3B-Instruct-FP8`
- GPU: `NVIDIA RTX PRO 6000 Blackwell Workstation Edition`
- GPU UUID: `GPU-592644b2-d169-3424-56fd-98aea433ef09`

## Scenario medians

Completion rate includes all completion tokens. The post-TTFT value is a
service proxy; SSE chunk arrivals are not guaranteed to be token arrivals.

| Prompt tokens | Concurrency | Requests | TTFT ms | End-to-end ms | Completion tok/s (E2E) | Completion tok/s (post-TTFT proxy) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 256 | 1 | 2 | 16.563 | 373.884 | 171.342 | 179.281 |
| 256 | 2 | 4 | 26.362 | 450.141 | 142.393 | 150.641 |
| 2048 | 1 | 2 | 20.588 | 355.165 | 180.198 | 191.287 |
| 8192 | 1 | 2 | 30.188 | 388.171 | 164.876 | 178.779 |

## Individual requests

| Request | Prompt | Conc. | Status | TTFT ms | End-to-end ms | Completion tokens | Finish |
| --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| `p00-r00-c00` | 256 | 1 | PASS | 17.175 | 385.510 | 64 | length |
| `p00-r01-c00` | 256 | 1 | PASS | 15.952 | 362.258 | 64 | length |
| `p01-r00-c00` | 2048 | 1 | PASS | 20.751 | 355.562 | 64 | length |
| `p01-r01-c00` | 2048 | 1 | PASS | 20.424 | 354.767 | 64 | length |
| `p02-r00-c00` | 8192 | 1 | PASS | 29.931 | 387.411 | 64 | length |
| `p02-r01-c00` | 8192 | 1 | PASS | 30.445 | 388.932 | 64 | length |
| `p03-r00-c00` | 256 | 2 | PASS | 32.084 | 472.734 | 64 | length |
| `p03-r00-c01` | 256 | 2 | PASS | 23.328 | 467.634 | 64 | length |
| `p03-r01-c00` | 256 | 2 | PASS | 17.964 | 428.110 | 64 | length |
| `p03-r01-c01` | 256 | 2 | PASS | 29.397 | 432.649 | 64 | length |

## Shared-GPU observation

Observed whole-GPU power samples spanned 88.25–290.72 W; utilization samples spanned 0.0–100.0% when available.

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
