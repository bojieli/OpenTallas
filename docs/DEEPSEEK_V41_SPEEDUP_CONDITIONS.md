# V4.1: conditions for a several-fold ROM advantage

**Updated objective:** the user subsequently retained **100 µs/token** as an
explicit feasibility target for wafer-scale systems and fast-interconnected chip arrays. Earlier
statements below that no target is selected describe the prior analysis stage.
The 40 µs expert sub-budget remains adjustable. See the
[physical limits study](DEEPSEEK_V41_PHYSICAL_LIMITS.md) for current scope.

No absolute token deadline is assumed in this analysis. The question is which
parts of the workload ROM must accelerate, and how much unchanged critical-path
work a 3× end-to-end improvement can tolerate. Results are conditional service
calculations, not measured performance or an accepted architecture.

## Expert acceleration alone is not the full design

The current analytical profile charges 13.035 GB of active weight reads per
ordinary batch-one decode token: 4.512 GB routed and 8.523 GB non-routed. The routed
portion is **34.6%** of this inventory. These are profile byte counts, not measured
fractions of execution time. Dense projections, shared experts and the output
head must be accounted for alongside routed execution.

Under an illustrative equal-byte-service model, with no cache or overlap:

`weight speedup = (dense_bytes + routed_bytes) / (dense_bytes + routed_bytes / r)`.

Accelerating only routed reads 10× gives **1.453×** overall weight service;
removing routed service entirely gives at most **1.529×**. This does not prove a
1.529× system ceiling: actual component rates and dependencies differ. It does
show that expert-local ROM alone cannot justify a 3× claim from this inventory.
The architecture must explicitly optimize non-routed matrices and the supporting
attention, index, selection and numerical paths.

## An HBM cache changes the comparison

The candidate HBM design should consider persistent SRAM for repeatedly used
non-routed weights. At the existing assumed 3,869,000 B/mm² raw SRAM density:

| Non-routed cache coverage | Cache capacity | Raw SRAM area, system total | Uncached weight bytes/token |
|---|---:|---:|---:|
| 0% | 0 GB | 0 mm² | 13.035 GB |
| 50% | 4.261 GB | 1,101 mm² | 8.774 GB |
| 100% | 8.523 GB | 2,203 mm² | 4.512 GB |

Full coverage averages 275.4 mm² per die across eight dies, or 26.2 mm² across
84 dies. Neither division proves locality or physical feasibility. Ports, ECC,
alignment, wiring, area for other operators and reserved memory remain unpriced.
The profile's active inventory must be reconciled to executable tensor reads
before choosing exact cache contents. Cache capacity is not a free resource.

For illustration, at 4.5 TB/s delivered per die, eight HBM dies have an ideal
uncached weight floor of 362.1 µs. Caching the whole non-routed inventory lowers
that external-read floor to 125.3 µs. At 84 concurrently usable HBM dies, the same
figures are 34.5 and 11.9 µs. These are optimistic external byte-service floors,
not achievable full token times or validated equal-area systems.

Caching removes external reads on hits; SRAM still supplies local operands and
arithmetic still executes. Expert caching needs a separate route-hit analysis:
storing the six experts selected for one token does not cover every possible
selection from the 384 experts in each layer. Batch reuse likewise needs routing
overlap evidence. Do not count the installed HBM bandwidth of inactive placement
regions as available bandwidth for the active layer.

## Common work limits end-to-end speedup

Let H be HBM weight-service time, H/r the corresponding ROM time, and C unchanged
non-overlapped time on the critical path. Then:

`speedup = (H + C) / (H/r + C)`.

To reach 3×, `C/H <= (1 - 3/r)/2`:

| ROM acceleration of all relevant weight service | Maximum unchanged C/H for 3× |
|---|---:|
| 2× | Impossible in this model |
| 3× | 0 |
| 4× | 0.125 |
| 5× | 0.200 |
| 10× | 0.350 |
| Infinite | 0.500 |

For example, if weight service improves 10×, unchanged service may consume no
more than 35% of the original HBM weight time, or about 25.9% of total HBM time.
Even eliminating weight time entirely cannot reach 3× if unchanged service is
more than one-third of original total latency. Faster memory exposes attention,
indexing, numerical and communication bottlenecks sooner.

These equations require additive, non-overlapped terms. A real dependency schedule
must replace them where memory and compute overlap. If ROM also accelerates C,
that benefit must have its own resource and correctness evidence. Conversely,
ROM cannot claim a benefit from leaving HBM's common engines underprovisioned.

## Consequence for the next architecture decision

Derive separate service and placement budgets for non-routed matrices, routed
experts, KV/index/attention and remaining numerical/control work. Sweep cache
coverage and local bandwidth on both architectures, and retain both batch-one
latency and concurrent throughput. Use the resulting resource-constrained totals
to select a latency target. The 100 µs token and 40 µs expert probes do not serve
as acceptance requirements.

The finite expert streaming schedule remains a supporting, unfinished analysis;
it cannot settle the whole-model comparison. First reconcile the non-routed
inventory and cacheable tensor placement, then combine the complete service ledger
with the expert schedules and physical area/power evidence.

Reproduce with `python3 tools/audit_v41_speedup_conditions.py`; see
[the calculation and input hashes](../results/architecture/v41_speedup_conditions.json).
No implementation or workload simulation is performed by this study.
