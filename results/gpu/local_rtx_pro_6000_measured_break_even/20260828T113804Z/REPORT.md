# Local RTX PRO 6000 shared-serving measurement

> **Evidence class: shared and contended.** This is a Qwen service-level
> observation, not a clean peak-GPU benchmark, a DeepSeek-V4 comparison,
> an OpenTallas implementation result, or attributable energy evidence.

- Status: **PASS**
- Benchmark: `local-rtx-pro-6000-shared-serving-measured-break-even-v2`
- Generated: `2026-08-28T11:38:29.140+00:00`
- Endpoint model: `qwen-fast`
- Endpoint root: `Qwen/Qwen3-VL-30B-A3B-Instruct-FP8`
- GPU: `NVIDIA RTX PRO 6000 Blackwell Workstation Edition`
- GPU UUID: `GPU-592644b2-d169-3424-56fd-98aea433ef09`

## Scenario medians

Completion rate includes all completion tokens. The post-TTFT value is a
service proxy; SSE chunk arrivals are not guaranteed to be token arrivals.

| Prompt tokens | Concurrency | Requests | TTFT ms | End-to-end ms | Completion tok/s (E2E) | Completion tok/s (post-TTFT proxy) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 256 | 1 | 3 | 18.149 | 1360.094 | 188.222 | 190.827 |
| 8192 | 1 | 3 | 28.598 | 1935.436 | 132.270 | 134.254 |
| 32768 | 1 | 3 | 130.162 | 4406.709 | 58.093 | 59.861 |

## Individual requests

| Request | Prompt | Conc. | Status | TTFT ms | End-to-end ms | Completion tokens | Finish |
| --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| `p00-r00-c00` | 256 | 1 | PASS | 24.728 | 1365.651 | 256 | length |
| `p00-r01-c00` | 256 | 1 | PASS | 16.478 | 1358.008 | 256 | length |
| `p00-r02-c00` | 256 | 1 | PASS | 18.149 | 1360.094 | 256 | length |
| `p01-r00-c00` | 8192 | 1 | PASS | 222.500 | 1679.934 | 256 | length |
| `p01-r01-c00` | 8192 | 1 | PASS | 28.598 | 1935.436 | 256 | length |
| `p01-r02-c00` | 8192 | 1 | PASS | 28.372 | 2052.536 | 256 | length |
| `p02-r00-c00` | 32768 | 1 | PASS | 2082.216 | 7660.987 | 256 | length |
| `p02-r01-c00` | 32768 | 1 | PASS | 130.162 | 4406.709 | 256 | length |
| `p02-r02-c00` | 32768 | 1 | PASS | 80.383 | 2792.811 | 256 | length |

## Shared-GPU observation

Observed whole-GPU power samples spanned 85.66–603.50 W; utilization samples spanned 0.0–100.0% when available.

Window-integrated joules are retained in `measurement.json` only as
contaminated whole-GPU observations. They are not divided by requests or
tokens and are not attributed to this benchmark because other workloads
were active.

## Claim boundary

- The endpoint serves the exact locally pinned Qwen3-VL-30B-A3B-Instruct-FP8 snapshot in text-only mode.
- Other serving and audio processes share the GPU, so the observation is a service target rather than clean peak RTX PRO 6000 performance.
- Whole-GPU energy is contaminated and may not be divided by benchmark tokens or requests.
- Logical model bytes, operation lower bounds, and KV traffic are derived from pinned tensor headers and config; only service timing and token usage are measured.
- The report derives what OpenTallas would need to equal the measured service; it does not show OpenTallas achieving those requirements.
