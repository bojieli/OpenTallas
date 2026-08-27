# Analytical assumptions and interpretation contract

**Baseline:** released-checkpoint midpoint, schema version 2

**Last reviewed:** 2026-08-27 UTC
**Authority:** `configs/`, executable equations in `src/opentallas/`, and the
primary-source register in `docs/SOURCES.md`

This document is the interpretation contract for generated analytical results.
If prose here and executable configuration disagree, the generated result is not
reviewable until the disagreement is resolved. None of these assumptions is a
product-silicon commitment.

## Study matrix and comparison rules

- Targets are DeepSeek-V4-Flash-0731 and DeepSeek-V4-Pro-0813. Kimi-K3 is a
  stress/control case, not a recommended target.
- Context lengths are 200,000 and 1,000,000 resident tokens. The standard run is
  single-token autoregressive decode with a fully populated cache at that length.
- Batch 1, 8, and 64 are mandatory user points. Batch 32 and 128 are retained to
  audit provisional brief tiers and capacity cliffs. A dense batch sweep from 1
  through 256 selects latency and balanced knees and maps the superiority band;
  optimization evaluates every integer batch through each architecture's exact
  feasible capacity. The committed sweep CSV retains the dense 1..256 matrix plus
  capacity endpoints; exact optimum point records are retained in analytical JSON.
- A ROM batch is **per pipeline stage**. Resident sessions equal `batch × stages`.
  GPU comparisons are reported both at the same active microbatch and at matched
  total resident concurrency; these answer different service questions.
- GPU candidates are B200 and B300 at analytical x4, x8, and x16 normalization.
  The fastest and cheapest feasible configurations are selected independently.
  x4 is a pro-rata half-system construct, not a purchasable DGX claim.
- TPU is outside scope. No TPU number or conclusion is used.
- A ratio above 1 favors ROM. Speed compares ROM user tokens/s with the fastest
  feasible same-batch GPU. Cost compares ROM with the cheapest feasible
  same-batch GPU under the partial-TCO scope below.

## Published and measured model inputs

Exact encoded checkpoint storage is measured from pinned safetensors headers and
is not reconstructed from rounded parameter counts.

| Model | Released bytes | Ordinary target-decode dense | Ordinary target-decode routed | DSpark draft-only | Other resident-only |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 166,878,536,440 | 7,768,281,308 | 147,169,738,752 | 10,862,838,300 | 1,077,678,080 |
| DeepSeek-V4-Pro-0813 | 892,727,580,904 | 26,822,006,732 | 822,054,223,872 | 41,979,375,900 | 1,871,974,400 |
| Kimi-K3 | 1,560,860,324,864 | 111,160,730,624 | 1,446,456,066,048 | 0 | 3,243,528,192 |

Ordinary non-speculative decode does not stream DeepSeek DSpark/MTP tensors. A
speculative step charges their traffic explicitly. Embeddings, hash lookup tables,
and Kimi's vision/front-end tensors remain capacity-resident but are not treated as
full decode-array reads. Prefill and multimodal execution are not part of the
standard decode result.

## KV and workload derivations

| ID | Baseline rule | Evidence class | Required replacement |
|---|---|---|---|
| A-KV-001 | DeepSeek main cache is FP8 except BF16 RoPE dimensions; one E8M0 scale per 64 FP8 values. Index cache is FP4 with one scale per 32 values. | Serving precision is published; byte packing and scale overhead are derived. | Kernel/HBM profiler traces, allocator overhead, and numerical validation. |
| A-KV-002 | CSA scans the compressed FP4 index for the context divided by compression ratio, then gathers configured top-k main entries; the bounded window is added. | Derived from pinned config/topology. | Production kernel read counters and cache-hit/reread behavior. |
| A-KV-003 | HCA reads the context divided by its configured compression ratio. | Derived. | Production kernel measurement. |
| A-KV-004 | Kimi KDA retains FP32 recurrent matrix state plus BF16 short-convolution history and performs one read plus one write per token. | State shape is derived from config; precision/traffic are assumed from the public reference-kernel style. | Production KDA kernel counters and retained-state precision. |
| A-KV-005 | Kimi gated MLA uses an absorbed latent cache in FP8, 576 bytes per token per layer. | Optimized implementation assumption. | Production serving layout and numerical validation. |
| A-KV-006 | `kv_read_amplification = 1.0` for the midpoint. | Ideal assumed lower bound. | Kernel measurement; sweep upward for rereads/cache-line amplification. |
| A-MOE-001 | Routed expert coverage is `1-(1-k/N)^B` under independent uniform routing. | Derived baseline. | Production per-layer router traces; synthetic Zipf/persistence traces are stress only. |
| A-OPS-001 | One decode position costs two operations per active parameter. | First-order assumed convention. | Operator-level FLOP/operation inventory for each released checkpoint. |
| A-OPS-002 | Active parameters are split algebraically into always-active dense/shared parameters and top-k routed parameters from published total/active/expert counts. Dense/shared operations use the FP8-or-higher roof; routed operations use the FP4-class roof. | Derived topology plus format-class assumption. | Per-operator precision and FLOP traces, including non-matmul work. |

`rho_one` is ordinary target-decode weight bytes at batch 1 divided by KV **read**
bytes for one user token. It is a model-architecture screen, not a hardware
speedup prediction.

## GPU normalization and runtime assumptions

Published system totals are normalized by eight except where NVIDIA publishes an
exact device population. B200 uses 180 GB, 8 TB/s, 9 dense FP4 POP/s, and 1,787.5 W
per GPU-equivalent. Its higher-precision roof is 4.5 dense FP8 POP/s. For B300,
the system guide explicitly specifies 8 × 288 GB; the model therefore uses 288 GB
physical capacity, 7.75 TB/s, 13.5 dense FP4 POP/s, 4.5 dense FP8 POP/s, and
1,812.5 W per GPU-equivalent. The separate February datasheet's 2.1 TB
total label is documented but is not divided into fictitious 262.5 GB devices.

The following are assumptions, not NVIDIA measurements of these models:

| Parameter | B200 x4/x8 | B200 x16 | B300 x4/x8 | B300 x16 |
|---|---:|---:|---:|---:|
| Weight-bandwidth efficiency | 0.70 | 0.65 | 0.72 | 0.67 |
| KV-bandwidth efficiency | 0.65 | 0.60 | 0.67 | 0.62 |
| Compute efficiency (both format roofs) | 0.45 | 0.42 | 0.48 | 0.45 |
| MoE load-balance efficiency | 0.78 | 0.72 | 0.80 | 0.74 |
| Clock efficiency | 0.95 | 0.95 | 0.95 | 0.95 |
| Synchronization efficiency | 0.85 | 0.80 | 0.86 | 0.81 |
| Per-layer collective latency | 3/4.5 µs for x4/x8 | 8 µs | 3/4.5 µs for x4/x8 | 8 µs |
| Effective collective payload bandwidth | 1 TB/s | 0.5 TB/s | 1 TB/s | 0.5 TB/s |
| Acquisition proxy per GPU-equivalent | $25,000 | $25,000 | $32,000 | $32,000 |

Only 90% of published physical HBM capacity is available to checkpoint plus KV;
10% is reserved for allocator, runtime, communication, activation, and safety
workspace. This matches the broad shape of the official serving examples but is
still an assumed capacity policy, not a measured maximum for these exact runs.

At low batch, routed-weight bandwidth engages only the expected devices holding a
selected expert; dense weights and KV can engage all devices. This is an explicit
placement/runtime hypothesis. Actual expert placement, EP/TP/DP topology, kernel
fusion, scheduling, collective overlap, and software overhead require measured
B200/B300 runs.

## ROM-wafer midpoint hypothesis

Every value in this table is assumed unless labeled simulated. A “wafer” is the
architecture model's stage unit, not a manufacturable declaration.

| ID | Midpoint | Meaning |
|---|---:|---|
| A-ROM-CAP | 160 GB released checkpoint bytes/wafer | Via-ROM capacity hypothesis; sets 2 Flash and 6 Pro stages. Kimi requires 11, not the aggregate-byte lower bound of 10, because its ~17 GB main layers are not split across pipeline stages. |
| A-ROM-READ | 100 TB/s/wafer | Full interleaved-array encoded-weight read bandwidth. |
| A-ROM-KV-CAP | 384 GB physical HBM/wafer, 90% usable | Perimeter-attached KV capacity after the same explicit runtime/workspace reserve. |
| A-ROM-KV-BW | 8 TB/s/wafer | Perimeter-attached KV bandwidth. |
| A-ROM-OPS | 1 low-precision POP/s and 0.5 higher-precision POP/s/wafer | Assumed routed-expert FP4-class and dense/shared FP8-or-higher operation roofs. |
| A-ROM-NOC | 100 ns floor + payload/128 GB/s per layer | Calibrated to the best current public NoC sweep, then divided by 0.90 synchronization efficiency. The sweep is simulated, not physical timing. |
| A-ROM-DERATE | read 0.70; KV 0.70; compute 0.55; balance 0.85; repair 0.92; clock 0.90; sync 0.90; pipeline 0.92 | Independent midpoint efficiency hypotheses. |
| A-ROM-POWER | 15 kW operating, 20 kW cooling limit/wafer | Package/cooling hypothesis. |
| A-ROM-LINK | 0.5 µs/stage boundary | Cross-stage latency hypothesis. |
| A-ROM-COST | $100k/wafer + $100M NRE/1,000 units | Acquisition/NRE hypothesis. |

The ROM pipeline uses a fixed, context- and batch-independent contiguous layer
partition that minimizes the largest stage's exact released-format ordinary-decode
layer storage while enforcing 160 GB locally. Non-layer, DSpark, and resident-only
arrays are striped over remaining stage slack for capacity accounting. At run time,
the slowest stage is calculated from its own selected weight bytes, KV bytes,
operation share, and layer collectives. Because exact per-layer active parameter
counts are unavailable, operations are apportioned using released-format active
bytes at batch one as a proxy. KV capacity is also enforced per stage and must hold
`batch × stages` session shards; neither ROM nor HBM capacity may be pooled across
wafer boundaries. At the midpoint this lowers Kimi 1M's maximum batch/stage to 17.

## Speculation

The standard report has two scenarios:

- no speculation;
- an explicitly provisional midpoint with 5 draft candidates, independent
  per-token acceptance probability 0.70, and serial draft compute cost equal to
  0.08 of an active-model one-position compute pass per draft token.

Target verification processes all candidate positions. DSpark draft weights are
also read when speculation is enabled. The acceptance distribution and draft cost
are assumed, not measured on production traces. The midpoint is not evidence that
ROM or GPU will achieve the resulting speed. Both architectures receive the same
algorithmic speculation parameters, but their target/draft service times remain
architecture-specific.

## Power and partial-TCO scope

`partial_tco_per_million_tokens` contains:

1. acquisition proxy plus per-unit NRE share, amortized over four years at 70%
   serving utilization; and
2. active-serving electricity at $0.08/kWh and facility PUE 1.15.

The power charged is the larger of the operation/HBM/ROM dynamic-energy estimate
and the allocated steady operating-power envelope. For B200/B300, the latter is
the official system maximum/busbar power divided by eight, which includes platform
overhead but is a power ceiling rather than a model-specific measurement. For ROM
it is the assumed 15 kW/wafer operating point. If dynamic demand exceeds the
cooling limit, service interval is throttled until it fits.

The cost proxy omits idle-period electricity, financing, depreciation/tax effects,
host/network/storage acquisition beyond the GPU-equivalent proxy, floor space,
cooling-plant capital, staffing, software, maintenance, downtime, replacement
inventory, yield loss beyond the assumed repair derate, and decommissioning. It is
therefore **partial TCO**, not price, cloud cost, or a complete business case. GPU
device acquisition inputs are not official NVIDIA prices; ROM unit/NRE values are
unverified hypotheses.

## Known model boundaries

- The standard result excludes prompt prefill, multimodal prefill, prefix-cache
  sharing, session migration, cold KV handoff, sampling/grammar overhead, and
  network/API latency. Executable hooks exist for some prefill cases but are not
  production-validated.
- Weight and KV memory times share GPU HBM and are added; compute can overlap that
  sum; collective time is serialized. ROM takes the maximum of weight read, KV,
  and compute, then adds collective time. These overlap rules are assumptions.
- Capacity includes the full released checkpoint, including draft and resident-only
  tensors, even when ordinary decode traffic excludes them.
- No PPA, yield, circuit, thermal, package, or cost assumption is promoted by the
  analytical result. The sensitivity grid is not a statistical confidence interval.
- The present numerical model checks traffic and service bounds, not logits or
  accuracy. Numerical-format qualification belongs to the architecture and DV
  specifications before serious RTL.

## Exit criteria for replacing assumptions

A value can move from `assumed` to `measured` only when the raw artifact, command,
tool/version, configuration, unit conversion, and uncertainty are archived and a
reproduction check passes. Production GPU/kernel traces, model-owner router traces,
foundry ROM characterization, synthesized/placed compute and NoC results, package
analysis, and vendor quotes must replace the corresponding midpoint before a
product-silicon decision.
