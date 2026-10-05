# Local RTX PRO 6000 shared-serving measurement

> **Evidence class: shared and contended.** This is a Qwen service-level
> observation, not a clean peak-GPU benchmark, a DeepSeek-V4 comparison,
> an OpenTallas implementation result, or attributable energy evidence.

- Status: **PASS**
- Benchmark: `local-rtx-pro-6000-shared-serving-measured-break-even-v2`
- Generated: `2026-08-28T11:44:55.122+00:00`
- Endpoint model: `qwen-fast`
- Endpoint root: `Qwen/Qwen3-VL-30B-A3B-Instruct-FP8`
- Endpoint runtime: `vLLM 0.19.0`
- GPU: `NVIDIA RTX PRO 6000 Blackwell Workstation Edition`
- GPU UUID: `GPU-592644b2-d169-3424-56fd-98aea433ef09`
- NVIDIA driver: `595.71.05`

## Scenario medians

Completion rate includes all completion tokens. The post-TTFT value is a
service proxy; SSE chunk arrivals are not guaranteed to be token arrivals.

| Prompt tokens | Concurrency | Requests | TTFT ms | End-to-end ms | Completion tok/s (E2E) | Completion tok/s (post-TTFT proxy) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 256 | 1 | 3 | 22.359 | 1634.871 | 156.587 | 158.759 |
| 8192 | 1 | 3 | 32.790 | 1899.412 | 134.779 | 137.052 |
| 32768 | 1 | 3 | 74.596 | 2215.739 | 115.537 | 120.185 |

## Individual requests

| Request | Prompt | Conc. | Status | TTFT ms | End-to-end ms | Completion tokens | Finish |
| --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| `p00-r00-c00` | 256 | 1 | PASS | 35.243 | 1776.570 | 256 | length |
| `p00-r01-c00` | 256 | 1 | PASS | 22.359 | 1634.871 | 256 | length |
| `p00-r02-c00` | 256 | 1 | PASS | 19.677 | 1425.010 | 256 | length |
| `p01-r00-c00` | 8192 | 1 | PASS | 32.790 | 2057.393 | 256 | length |
| `p01-r01-c00` | 8192 | 1 | PASS | 31.505 | 1899.412 | 256 | length |
| `p01-r02-c00` | 8192 | 1 | PASS | 35.143 | 1631.029 | 256 | length |
| `p02-r00-c00` | 32768 | 1 | PASS | 74.596 | 2151.912 | 256 | length |
| `p02-r01-c00` | 32768 | 1 | PASS | 72.850 | 2645.942 | 256 | length |
| `p02-r02-c00` | 32768 | 1 | PASS | 85.682 | 2215.739 | 256 | length |

## Shared-GPU observation

Observed whole-GPU power samples spanned 212.21–352.17 W; utilization samples spanned 0.0–100.0% when available.

Window-integrated joules are retained in `measurement.json` only as
contaminated whole-GPU observations. They are not divided by requests or
tokens and are not attributed to this benchmark because other workloads
were active.

## Claim boundary

- The endpoint reports the Qwen3-VL-30B-A3B-Instruct-FP8 root in text-only mode. The API does not expose a revision; accounting uses the sole local snapshot selected by the default main ref.
- Other serving and audio processes share the GPU, so the observation is a service target rather than clean peak RTX PRO 6000 performance.
- Whole-GPU energy is contaminated and may not be divided by benchmark tokens or requests.
- Logical model bytes, operation lower bounds, and KV traffic are derived from pinned tensor headers and config; only service timing and token usage are measured.
- The report derives what OpenTallas would need to equal the measured service; it does not show OpenTallas achieving those requirements.
