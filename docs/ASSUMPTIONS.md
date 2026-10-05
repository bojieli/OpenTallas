# Analytical assumptions and interpretation contract

**Status:** authoritative input ledger for the iso-technology studies

**Last reviewed:** 2026-08-28 UTC

**Scope:** single-token autoregressive decode; no prefill or speculative decoding

This file records assumptions. [`METHODOLOGY.md`](METHODOLOGY.md) is the normative
comparison contract, [`SOURCES.md`](SOURCES.md) is the public evidence register,
and `configs/hardware/technology_inputs.json` is the machine-readable technology
ledger. Generated values are authoritative only when all three agree with the
executable equations in `src/opentallas/`.

The old 160-GB/100-TB/s single-wafer midpoint is **not** the current baseline.
It remains only as a public RTL interface proxy under `spec/` and in superseded
`results/standard/` artifacts.

## 1. Study matrix

| Study | Proposed architecture | GPU comparator | Feasibility anchor | Purpose |
|---|---|---|---|---|
| N7 architecture attribution | N6/N7-class planar mask ROM plus HBM2e-era mutable memory | A100 80 GB, TSMC N7/HBM2e | WSE-2, TSMC N7 | Isolate immutable-ROM versus HBM/SRAM architecture at a common generation. |
| Leading-node market | N4-class mask ROM plus HBM3e | B300, custom TSMC 4NP/HBM3e | WSE-3, TSMC N5 | Bound a contemporary product opportunity without importing N7 assumptions. |

WSE products establish wafer-scale construction and published physical ceilings;
their SRAM bandwidth, compute, topology efficiency, yield, or cost is never
assigned to the proposed ROM wafer. HBM4 is not used. Huawei Tau/韬 scaling is
not used as a multiplier; Section 8 of `METHODOLOGY.md` defines the separate 3-D
scenario gate.

Current target models are DeepSeek-V4-Flash-0731 and DeepSeek-V4-Pro-0813. Both
studies run contexts 8,192, 32,768, 200,000, and 1,000,000 at batch per stage 1,
8, 32, and 64. Kimi K3 and Qwen3-8B remain model-general controls, not members of
the two authoritative comparator matrices.

## 2. Released model bytes and official numerical roles

Storage is measured tensor by tensor from pinned safetensors headers, not inferred
from rounded parameter totals.

| Model | Released checkpoint | Ordinary-decode dense bytes | Ordinary-decode routed bytes | Draft-only | Other resident-only |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 166.879 GB | 7.768 GB | 147.170 GB | 10.863 GB | 1.078 GB |
| DeepSeek-V4-Pro-0813 | 892.728 GB | 26.822 GB | 822.054 GB | 41.979 GB | 1.872 GB |

Ordinary non-speculative decode does not stream draft-only tensors, but full
checkpoint capacity remains resident. DeepSeek roles are preserved:

- routed expert weights: MXFP4 E2M1 with FP8 activation;
- dense/shared matrices: FP8-class weight and activation;
- architectural/vector paths: BF16 where specified;
- mHC reductions/selected operations: FP32;
- sparse index cache and index operations: packed FP4 where specified;
- main KV: FP8 except released/configured BF16 RoPE dimensions and explicit
  scale overhead.

Packed four-bit storage never selects a pure-FP4 compute roof for MXFP4×FP8 work.
A100 has no native floating FP8/MXFP4/FP4 Tensor Core path, so two explicit
deployments bound it:

1. `a100_bf16_expanded`: lossless offline BF16-resident expansion, with exact
   tensor-role capacity expansion;
2. `a100_packed_hbm_bf16_execute`: a GPU-favorable ceiling retaining packed HBM
   bytes and executing as BF16 while omitting the unmeasured unpack cost.

The second case is a ceiling, not a demonstrated A100 serving implementation.

## 3. Operator and traffic accounting

One multiply plus one add is two operations. DeepSeek tensor-contraction work
uses exact operator shapes from the pinned implementation, including sparse-index
scan/gather, context-linear attention, mHC projections, and vocabulary
projection. The current studies do not use `2 × active_parameters`.

At 200K context the exact totals are:

| Model | Tensor operations/user token | FP32 share |
|---|---:|---:|
| Flash | 49.965 Gop | 0.136% |
| Pro | 145.068 Gop | 0.116% |

These totals are tensor operations, not an operator-complete execution count.
Normalization, nonlinear, attention-score/softmax, index-score, compressor-pool,
top-k, and Sinkhorn categories are counted separately. Each generated operating
point reports the category rate required to fit the baseline interval and a
10%-serialized-overhead threshold; no vector/top-k service roof is assumed.
Consequently those paths contribute no modeled time or energy yet, and all token
rates remain conditional. Activation quantization/scaling, RoPE,
residual/hyper-connection elementwise work, dispatch, and remaining official
source operations still require the `COMP-01` semantic ledger and executable
service measurements.

For a decode step:

```text
expert_coverage(B) = 1 - (1 - top_k / experts)^B
weight_bytes(B)    = dense_bytes + routed_bytes × expert_coverage(B)
KV_bytes(B)        = B × (amplified_KV_read_bytes + KV_write_bytes)
```

Uniform independent routing is an analytical baseline, not a production trace.
GPU routed-weight bandwidth is limited to devices expected to hold at least one
selected expert. ROM interleaving assumes every tile holds a disjoint shard of
every stage-local expert so any legal selection can engage the whole array. That
placement is an architectural hypothesis gated by layout, routing, power, and
repair evidence.

GPU weight and KV transfers share HBM and are additive. ROM weights and mutable
HBM KV use physically separate services and may overlap. KV, recurrent state,
session metadata, and workspaces are mutable and can never be assigned to ROM.
The baseline KV reread amplification is 1.0, an ideal lower bound pending kernel
counters.

## 4. Published GPU facts versus runtime assumptions

| Item | A100 80 GB | B300 |
|---|---:|---:|
| Process/memory | TSMC N7 / HBM2e | custom TSMC 4NP / HBM3e |
| Physical HBM/device | 80 GB | 288 GB |
| Raw HBM bandwidth/device | 2.039 TB/s | 7.75 TB/s |
| Compatible low-precision roof | 312 TOP/s dense BF16 | 4.5 POP/s dense FP8; 2.25 POP/s derived BF16 |
| Full FP32 roof | 19.5 TOP/s published | 90 TOP/s **assumed**, swept 19.5–180 TOP/s |
| Allocated power/device | 400 W | 1,812.5 W system busbar/8 |

The checked official B300 documents do not publish full-FP32 throughput. The
90-TOP/s configured value is provisional; the executable sweep shows no change at
reported 200K points because the fastest clusters bind on weight-memory service.

| Assumed runtime input | A100 | B300 |
|---|---:|---:|
| Usable HBM fraction | 0.90 | 0.90 |
| Weight-bandwidth efficiency | 0.75 | 0.72 |
| KV-bandwidth efficiency | 0.70 | 0.67 |
| Compute efficiency | 0.45 | 0.48 |
| MoE load-balance efficiency | 0.75 | 0.80 |
| Clock efficiency | 0.95 | 0.95 |
| Acquisition proxy/device | $15,000 | $32,000 |

The A100 cluster sweep is x1/x2/x4/x8/x16/x32/x64 because BF16 expansion and Pro
capacity require large counts. The B300 sweep is x1/x2/x4/x8/x16. These are
analytical device-count normalizations, not claims that every count is a purchasable
DGX SKU.

GPU collective latency/bandwidth are assumed by cluster size. A multi-GPU layer
charges two official DeepSeek all-reduces. The configured latency is an optimistic
aggregate floor for both events; two logical FP32-reduction plus BF16-result
payloads are serialized. Topology amplification, runtime launches, contention,
and overlap require exact measured traces.

## 5. ROM capacity and local-read derivation

There is no public fabricated N7 or N4 mask-ROM macro matching this product. The
envelopes are deterministic extrapolations, not confidence intervals.

Capacity starts from a fabricated 28-nm 8.928-Mb/mm² hybrid SRAM/ROM-CIM macro.
N7 uses explicit density exponents 1.0/1.5/2.0. Leading-node conservative uses
linear planar scaling; central is the geometric midpoint between that planar case
and the published 3D-METRO evaluation; aggressive uses the 3D-METRO evaluated
20.7-MB/mm² density directly. 3D-METRO is simulated architecture evidence, not
fabricated silicon and not Huawei Tau evidence.

Read service starts from the YOLoC 28-nm simulated 8-bit ROM-CIM operation rate,
converted to 60 GB/s/mm² of encoded-weight service. It receives explicit
1×/2×/4× N7 or 1.5×/3×/5× leading-node bandwidth-density factors before whole-
wafer efficiency derates. Neither the anchor nor the scaling establishes
simultaneous full-array wafer activity.

| Study/envelope | Usable ROM/wafer | Raw local weight service | Mutable-memory stacks | Raw mutable capacity | Raw mutable BW |
|---|---:|---:|---:|---:|---:|
| N7 conservative | 57.8 GB | 970.7 TB/s | 16 HBM2e | 256 GB | 6.52 TB/s |
| N7 central | 170.4 GB | 2,662.6 TB/s | 32 HBM2e | 512 GB | 13.05 TB/s |
| N7 aggressive | 408.6 GB | 6,101.7 TB/s | 48 HBM2e | 768 GB | 19.57 TB/s |
| N4 conservative | 101.1 GB | 1,456.1 TB/s | 24 HBM3e | 864 GB | 23.25 TB/s |
| N4 central | 242.7 GB | 3,993.8 TB/s | 40 HBM3e | 1,440 GB | 38.75 TB/s |
| N4 aggressive | 473.6 GB | 7,627.1 TB/s | 56 HBM3e | 2,016 GB | 54.25 TB/s |

The package calculation checks only first-order perimeter pitch at 12 mm/stack.
It does not establish routing escape, signal integrity, power delivery, cooling,
mechanical clearance, or known-good-stack yield.

## 6. Compute, NoC, pipeline, and efficiency assumptions

N7 format-neutral compute ceilings are the published same-node GC200 FP16 rate
area-scaled to 46,225 mm², then multiplied by explicit 10%/25%/50% composition
fractions. Leading-node ceilings are 10%/30%/50% of WSE-3's ambiguous advertised
125-PFLOP/s ceiling. The source products have different architectures and formats;
these are bounded hypotheses that target synthesis/P&R must replace.

| Envelope | Weight BW eff. | KV BW eff. | Compute eff. | MoE balance | Repair | Clock | Sync | Pipeline |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Conservative | 0.50 | 0.60 | 0.45 | 0.75 | 0.85 | 0.85 | 0.80 | 0.82 |
| Central | 0.65 | 0.70 | 0.60 | 0.85 | 0.92 | 0.90 | 0.88 | 0.90 |
| Aggressive | 0.75 | 0.78 | 0.70 | 0.92 | 0.96 | 0.94 | 0.94 | 0.95 |

Wafer communication is derived from topology, path hops, clock, bisection links,
payload width, endpoint/barrier cycles, and two all-reduces per layer. The three
envelopes use a WSE-like nearest-neighbor mesh, a 64×64 hierarchical mesh, and an
8×8 coarse-reticle exchange respectively. Only the first is a product-style
feasibility anchor; none is placed-and-routed timing for this design.

ROM stage count and contiguous layer partition are calculated from the exact
released checkpoint and local usable capacity. A pipeline batch is per stage and
requires `batch × stages` resident KV shards. Per-user latency is stage interval
times stage count plus cross-stage propagation; aggregate rate is batch per stage
divided by the initiation interval. Confusing these is a stage-count error.

## 7. Power and partial TCO

Every wafer envelope assumes $100,000/unit, 15 kW steady operating power, a 23-kW
cooling limit, $100M NRE spread over 1,000 units, and the common lifetime,
utilization, electricity, and PUE fields in the generated hardware profiles.
These are program hypotheses, not quotes.

`partial_tco_per_million_tokens` contains acquisition/NRE amortization plus active
electricity only. It omits financing, staffing, hosts, networking, facilities
capital, maintenance, spares, downtime, idle power, yield loss beyond configured
repair, and decommissioning. It is not price, cloud cost, gross margin, or a full
business case.

Activity energy and allocated steady power are not added. The simulator uses the
larger, throttles the interval if it exceeds the cooling limit, and reports the
thermal scale explicitly.

## 8. What is not modeled

- prompt prefill, prefix caching, prefill/decode disaggregation, or KV handoff;
- speculative decoding, draft generation, or acceptance distributions in the
  authoritative iso-node studies;
- measured production router distributions, expert placement, KV rereads, kernel
  utilization, collective overlap, or latency tails;
- executed service time, energy, and shared-resource contention for vector,
  softmax, top-k, Sinkhorn, quantization, RoPE, residual, and dispatch paths; the
  reports expose only selected count-derived break-even requirements;
- target-node ROM timing/sense margin, simultaneous read power, detailed PDN and
  thermal fields, package SI/PI, yield/repair correlation, or failure domains;
- logits, benchmark quality, or numerical qualification of a manufactured
  compute path.

## 9. Replacement rule

An assumed value can become measured only when the raw artifact, command,
tool/version, configuration, unit conversion, uncertainty, and reproduction check
are archived. Product authorization requires model-owner commitment, production
GPU/router/KV traces, foundry macro data, target synthesis/P&R, OSAT/package
feasibility, power/thermal signoff, yield/repair evidence, and reticle test-silicon
correlation. A passing arithmetic audit closes none of those external gates.
