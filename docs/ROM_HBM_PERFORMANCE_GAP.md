# ROM and HBM: theoretical limits versus the implementation

Snapshot: 2026-09-23. This is the top-down assessment for optimization decisions.
The [implementation status](OPTIMIZATION_STATUS.md) tracks individual changes.
The reproducible calculations are in
[top_down_performance_gap.json](../results/architecture/top_down_performance_gap.json).

## Assessment

**We have not demonstrated that the implemented ROM or HBM accelerator approaches
state-of-the-art system performance, or established its percentage of the
analytical ceiling.** The architecture has credible opportunities, particularly
weight-local ROM for low-batch decoding and reuse-oriented compute for HBM.
However, the gap includes resource balance, delivery, numerical service and
integration—not just the frequency of a few slow modules.

Three findings set the priorities:

1. The current five-die Qwen ROM budget needs **262.144 µs just to deliver KV**.
   The older analytical projection was **202.388 µs for the entire token**.
   That projection is incompatible with the revised delivery architecture.
2. At batch one, a proposed HBM die with **4.5 TB/s** needs about **2,250
   fully utilized BF16 lanes at 1 GHz** to consume its weight stream. The
   41,536-lane budget has about **18.46 times** that arithmetic capacity. It
   needs substantial weight reuse, independent work, or different provisioning.
3. The current leading-node ROM headline requires **38.39 billion attention
   score items/s** and **848.69 billion index-score items/s** for Flash at 200K.
   Those are requirements in the model; the model does not price their complete
   auxiliary execution. We have not built and qualified that service capacity.

My earlier reports emphasized local improvements without connecting them to these
requirements. They were insufficient evidence that the whole design would be
fast or efficient. Future implementation decisions should be evaluated against
these system budgets first.

## The first-principles model

For a workload, record active weight bytes W, KV bytes K, arithmetic operations
F, auxiliary work N_j, and actual dependencies. A useful initial bound is:

- HBM shared-port service: **T_memory >= (W + K + other traffic) / delivered BW**.
- ROM with independent weight/KV paths: **T_memory >= max(W/BW_ROM, K/BW_KV)**,
  if their overlap can actually be scheduled.
- Arithmetic: **T_compute >= F / sustained operations/s**.
- Each auxiliary engine class: **T_j >= N_j / sustained items/s**.
- A token also obeys its dependency critical path, including communication and
  control. Pipeline stages that the same token visits serially contribute serial
  service. Adding pipeline stages does not divide one user's token latency.

The maximum of resource bounds is an optimistic ceiling on performance. A finite
buffer schedule must establish which services overlap and which add. Bandwidth
means bytes that reach the consumer, after bank, port, format and network limits.
A shared resource cannot be counted once for each consumer as if each owned it.

Area must include compute, all memories, reduction, control, clock trees, routers,
PHYs and placement space. Energy must include actual activity, memory and transport.
Neither a high clock nor a low multiplier area proves good tokens/s/mm² or J/token.

## HBM: bandwidth at low batch, reuse at high batch

Use the repository's Qwen3-8B BF16 inventory, batch one and context 8,192:

| Quantity | Value | Interpretation |
|---|---:|---|
| Active linear weights read/token | 15.137 GB | Ordinary decode; excludes inactive embedding rows |
| KV read/token | 1.208 GB | Full BF16 GQA read at this context |
| Linear arithmetic/token | 15.137 Gop | Multiply and add count as two operations; attention arithmetic is additional |
| Proposed HBM die service | 4.5 TB/s | Assumed delivered rate, not qualified RTL bandwidth |
| B200 package raw HBM bandwidth | 8 TB/s | Published reference input in the repository |
| B200 dense BF16 peak | 2.25 POp/s | Published/derived reference input; not sustained application throughput |

These give simple bounds:

- Proposed **single HBM die**: memory service alone takes about **3.632 ms**,
  or at most **275 tokens/s** on this workload.
- One **B200 package** at its raw bandwidth: at least **2.043 ms**, or at most
  **489 tokens/s**. Real bandwidth losses and other work lower this ceiling.
- B200's linear compute floor is only **6.73 µs**. Batch-one decoding is therefore
  overwhelmingly a data-movement problem under these assumptions.

The first comparison is one 815 mm² proposed die against a two-die, roughly
1,600 mm² B200 package; it is an intuition-building bandwidth comparison, not an
iso-area benchmark. Two proposed dies give 9 TB/s aggregate only if weights and
execution are sharded concurrently and communication is charged. A pipeline of
five dies does not give one token five times the weight bandwidth.

For BF16 matrix weights, one MAC consumes two weight bytes and performs two
operations. Arithmetic intensity is approximately **batch/reuse count operations
per weight byte**, before KV, activation, scale and output traffic. The proposed
41,536-lane die at 1 GHz has an ideal 83.072 TOp/s peak and a compute/bandwidth
ratio of **18.46 op/B**. It needs roughly **19-way reuse** to become compute-bound;
B200's raw BF16/HBM ratio is about **281 op/B**. These are ideal crossover points,
not guaranteed useful batch sizes.

**HBM design consequence:** prioritize sustained memory delivery and weight reuse,
then build enough compute to serve the intended batch/prefill envelope. Decode,
prefill and batched serving need separate measurements. The recent reuse and
coalescing changes target the correct resource, but their small-workload gains do
not establish competitive full-model bandwidth utilization or GEMM efficiency.

## ROM: removing weight traffic exposes other limits

Freshly running the existing N7 and leading-node analytical studies reproduces
the retained analytical JSON byte for byte. The leading-node central envelope
reports the following at batch one per stage:

| Workload | ROM analytical user tokens/s | Fastest allowed modeled HBM comparator | HBM analytical user tokens/s | Modeled ratio |
|---|---:|---|---:|---:|
| Qwen3-8B, 8K | 8,857 | B300 ×16 | 1,791 | 4.94× |
| DeepSeek-V4-Flash, 200K | 12,629 | B300 ×8 | 1,651 | 7.65× |
| DeepSeek-V4-Pro, 1M | 4,816 | B300 ×16 | 642 | 7.50× |
| DeepSeek-V4.1-Flash, 200K | 14,200 | B300 ×8 | 1,520 | 9.35× |

These are **conditional analytical comparisons**, not achieved RTL rates or
measured B300 application benchmarks. They use the study's topology, capacity,
precision, efficiency and communication assumptions. Pro and V4.1 use multiple
pipeline stages and resident users; these are not equal-area or equal-power
comparisons. They also are not the same N5 array design as the Qwen budget below.
The central envelope must not be substituted for the conservative envelope,
which can lose to HBM. The project's published Taalas HC1 reference is another
model/context/system and does not supply an apples-to-apples implementation ratio.

**The useful insight is the shift in bottleneck.** Flash's central estimate has
about 5.22 µs of ROM weight service, 14.14 µs of KV service and 57.13 µs of
collective service; its final modeled latency is 79.18 µs after the study's
composition/efficiency rules. More tensor peak cannot remove a collective or
auxiliary-service bottleneck. The ROM read-density assumptions still need macro
and simultaneous-array qualification.

The revised Qwen N5 resource model makes the implementation implications concrete:

| Proposed profile | Parallelism | Lanes/die | KV source / delivered B/cycle | KV service floor | Ideal linear-compute floor |
|---|---|---:|---:|---:|---:|
| Four dies | Tensor | 31,232 | 4,500 / 4,500 | 67.109 µs | 60.582 µs |
| Five dies | Pipeline | 41,536 | 26,112 / 4,608 | 262.144 µs | 182.213 µs |
| Eight dies | Tensor | 77,504 | 13,056 / 4,608 | 32.768 µs | 12.206 µs |

Clock is assumed 1 GHz with one BF16 MAC/lane/cycle. Tensor rows count concurrent
shards; the pipeline row counts serial token traversal. Compute floors exclude
attention, admission and stalls. All three still have **unavailable qualified
TPOT**; these floors do not add into a validated latency prediction.

The five-die design delivers only **17.65%** of its KV source rate: its delivery
path is **5.67×** narrower than the source. KV alone limits it to **3,815 tokens/s**,
already below its older 4,941-token/s projection. The older model's 46.37 µs KV
term assumed service the revised path cannot deliver.

For a 10,000-token/s target, this workload needs at least **12.08 TB/s of KV
delivery** and **151.37 TOp/s of linear arithmetic** during one token's serial
path, before any additional overhead. The five-die proposal has 4.608 TB/s and
83.072 TOp/s on that path. Its delivery and organization must change; polishing
individual arithmetic cells cannot make it meet that budget. The eight-die
tensor organization clears those two optimistic bounds, but still needs
communication, numerical-service and physical qualification.

The same mismatch appears in low-precision compute. The checked tile has a
32-cycle MXFP4 arithmetic pass but needs at least 64 cycles of scalar reduction
service. Its ideal 4-product/lane/cycle arithmetic peak is therefore capped at
**50% utilization by reduction**, before other overheads. To exploit that peak,
reduction capacity and data delivery must grow with it.

## The auxiliary-engine gap is architectural

For Flash at 200K, the central study explicitly reports these unpriced demands:

| Service | Needed to fit its 79.18 µs interval |
|---|---:|
| Attention score processing | 38.39 Gitems/s |
| Index-score processing | 848.69 Gitems/s |
| Normalization | 23.13 Gitems/s |
| Nonlinear functions | 7.92 Gitems/s |
| Top-k candidates | 13.26 Gitems/s |

These categories have different costs and must not be summed. A score item is
not necessarily one arithmetic instruction. The full semantic work, memory
movement and dependencies still need mapping to engines.

A stress calculation illustrates why the current serial exponential is not a
sufficient architectural answer. A non-early-exit production exponential takes
**2,880 service cycles**. Even assuming 1 GHz, that is only **347,222 results/s**
per engine, before wrapper overhead. If each of the 3,039,744 attention scores
needs one such evaluation with no exact reuse, fitting the analytical interval
requires approximately **110,563 concurrent engine equivalents**. Limiting that
category alone to 10% serialized overhead requires about **1.11 million**.
These are service-equivalent sizing requirements, not a proposed replication
count or measured workload demand. Reuse, early exits and a different exact
algorithm can reduce them; dependencies can make scheduling harder.

The issue is visible in real RTL fixtures: exponential wait accounts for **91.82%**
of 2,388,699 active cycles across nine sparse-attention transactions. The baseline
source manifest still matches current RTL. This supports prioritizing numerical
service architecture, but the fixtures are not a full-model score distribution.

**Design consequence:** derive exact numerical-service demand from deployed
traces, then evaluate a much higher-throughput implementation—shared range
reduction, pipelined/interleaved evaluation, and bounded expensive fallback where
correctness can be proven. Numerical equivalence and certification remain hard
requirements. Pure replication of the present serial engine needs an area and
power proof; a modest clock improvement cannot close this service gap.

## How closely does the implementation match the analysis?

There is no valid single current efficiency percentage. We need a common workload,
precision, topology, resource inventory and source revision at all three levels:
analytical model, cycle model and integrated RTL. That chain is incomplete.

| Question | Evidence and conclusion |
|---|---|
| Is the analytical framework reproducible? | Yes: both current iso-node studies regenerate identically. This validates arithmetic reproducibility, not hardware assumptions. |
| Does the revised architecture sustain the old ceilings? | Already contradicted for five-die Qwen: its KV floor exceeds the old entire-token projection by 29.53%. |
| Does the cycle model match the analytical model? | The retained Qwen reconciliation reports ROM latency 28.69× the analytical value; HBM 1.015×. Both cost-table hashes have changed since that run. These are historical assumed-model comparisons, not today's RTL performance. |
| Is the apparently close historical HBM result reassuring? | No: its tensor-only compute term is about 42.5× the analytical term and fabric cost is absent; a matching total can hide compensating errors. |
| Does the cycle model match integrated RTL? | The fresh gate check still fails G4. Historical lane steady-state agreement used measured rates as inputs; the control comparison was roughly 10–11× off. Current full-system calibration is still missing. |
| Is correctness-qualified full-model TPOT available for both targets? | No: fresh gate check fails G1 and G3. There are 9/19 passing gates, with 1/4 terminal gates passing. A gate pass at a bounded scope does not establish current all-target timing. |
| Do block area/frequency wins establish modern device efficiency? | No. Prototype compute-unit density is not the deployed token datapath, and missing memory/PHY/network area changes comparisons materially. Activity-based whole-system energy is unqualified. |

The numerical historical discrepancies are retained as diagnostics. The report
records their source drift explicitly; it does not claim the current design is
“28.69× slower than state of the art.” Nor can we claim the HBM implementation is
within 1.5% of its ceiling. The necessary current measurement does not exist.

ASAP7 is a predictive implementation vehicle. Its routed results do not calibrate
an N4/N5 foundry macro or clock. Comparisons against A100/N7, B200/N5-class studies
and the B300/N4-class market study remain separate. The vendor inputs here are
the repository's dated source inventory, not a new survey of every current product.

## Revised architecture-first work order

1. **Define the matched machines and scorecard.** For ROM and HBM, use the same
   numerical contract and workload per comparison. Include Qwen decode at 8K/32K,
   prefill/batched reuse, Flash at 200K/1M, and the supported Pro/V4.1 deployments.
   Record user latency, aggregate throughput, area and energy separately. Mark
   unqualified workloads explicitly instead of extrapolating small fixtures.
2. **Repair the model-to-implementation bridge.** Replace assumed service rates
   with current-source measured cycles, delivered bytes and containing-engine
   timing. Include control, auxiliary engines and finite network/buffer service.
   Reconcile disagreements term by term; matching only final totals is inadequate.
3. **Fix ROM delivery and parallelism.** Reconsider the five-die pipeline against
   tensor/cluster alternatives. Budget KV delivery, scalar reduction and real
   link endpoint serialization before increasing compute. Require a macro-backed
   ROM capacity, bandwidth and energy argument for the target technology.
4. **Balance HBM compute around reuse.** Verify the entire memory-to-compute path
   and measured traffic on batch-one decode, then qualify weight reuse for
   prefill/batched serving. Size SRAM banks, credits and compute together.
5. **Redesign the dominant numerical services.** Measure request distributions
   and certification/fallback rates, then choose a service architecture with a
   credible area/throughput budget. Prove it in complete attention and other
   consumers, including stalls, faults and reset.
6. **Optimize selected components and close the system.** Pipeline the paths
   identified by the chosen architecture, route containing engines, and measure
   complete producer-to-consumer execution. Recompute throughput and energy
   after integration; keep only changes whose benefit survives it.

A useful **proposed engineering target** is at least 70% of a feasible,
implementation-calibrated ceiling on each agreed workload, with cycle predictions
within the existing ±10% calibration band and complete physical/correctness
qualification. The ceiling must include every required service and resource; it
must not be lowered by silently omitting scope. Energy and area need separate
acceptance limits after macro/activity evidence exists. This proposal does not
relax any existing release gate.

The recent reuse and coalescing improvements are necessary progress. They do not
yet prove the desired end state. The next progress report should lead with how
much a change closes one of these quantified system gaps.

## Reproduction and sources

Run `python3 tools/audit_top_down_performance_gap.py`. It regenerates both iso-node
studies under `build/top_down_performance/`, derives the current chip budget,
checks historical input currency, runs the release gate checker, and writes the
compact calculation record. It preserves existing study and physical-run outputs.

- [Analytical framework](../src/opentallas/analytical.py) and
  [area-constrained roofline](../src/opentallas/roofline.py).
- [Leading-node study](../results/iso-node/leading_node_market/REPORT.md) and
  [vendor/source inventory](SOURCES.md).
- [Current chip resource budget](CHIP_RESOURCE_BUDGETS.md) and
  [architecture specification](CHIP_ARCHITECTURE_DESIGN.md).
- [Historical model reconciliation](../results/derived/qwen3_n5_design_target_reconciliation.json)
  and [historical calibration](../results/derived/qwen3_n5_design_target_calibration.json).
- [Attention phase profile](../results/rtl/softmax_exp_reuse/attention_profile.json).
