# Accelerator optimization status

Status snapshot: 2026-09-23. Production work is on `main`. This summary covers
architecture feasibility work through the V4.1 expert-group study; older component
results below retain their original evidence scope.

For the system-level assessment, start with **[ROM/HBM performance gap](ROM_HBM_PERFORMANCE_GAP.md)**. It compares the analytical ceilings with current delivery/compute budgets and identifies the architecture changes needed before local optimizations can establish a fast accelerator.

The proposed next architecture is now available for review in **[ROM-first architecture proposal](ROM_FIRST_ARCHITECTURE_PROPOSAL.md)**, with executable resource budgets and cache-aware HBM comparisons. It remains a proposal; production defaults are unchanged.

For DeepSeek V4.1 specifically, see the [first-principles architecture redesign](DEEPSEEK_V41_ARCHITECTURE_REDESIGN.md): expert-local ROM, CSA2 ownership, Engram placement, recurrence and fair HBM sizing.

## Latest feasibility finding

The proposed ROM 85/75 µs point fails the first dependency check: unchanged
sequential whole-K accumulation has an optimistic 888.832 µs linear-only floor
at 1 GHz. The area/service checks did not capture insufficient independent work
at batch one. Architecture implementation is deferred while the numerical and
scheduling alternatives are evaluated. See the correction at the top of the
[redesign proposal](ROM_FIRST_ARCHITECTURE_PROPOSAL.md).

## Where we stand

**Several useful architectural improvements are integrated, but the complete
accelerator is not yet qualified at the target clock across all targets.**
The initial ASAP7 target is a 1 ns clock period (1 GHz) for the main compute and
local-control fabric. Passing a standalone block at 1 ns does not establish that
the complete accelerator runs at 1 GHz.

Recent updates have mostly described **isolated experiments**, not changes to
production RTL. They are committed under `results/rtl/` so their code, tests and
measurements can be reviewed. Most have not earned production integration.
The number of experiments is not a measure of completed optimization.

## What I am doing right now

Current work is the first-principles ROM/HBM architecture review, including a
separate [DeepSeek V4.1 redesign](DEEPSEEK_V41_ARCHITECTURE_REDESIGN.md).
The new expert-group screen quantifies concentrated routing: a group containing
at least six experts needs 112.8 TB/s to serve six selected experts in 1 µs.
Pooling reduces replicated service hardware but increases local ROM span and wire
cost. This is a necessary requirement, not a demonstrated implementation rate.

No new RTL implementation or workload simulation was launched for these studies.
Pinned V4.1 source inspection shows independent 32-value expert partials: the
earlier whole-K recurrence is not a universal V4.1 floor. A conditional parallel
partial schedule needs 11.84–35.52 µs for expert dependencies alone at 1 GHz,
before omitted service. Numerical qualification and physical bank service remain
unresolved. The Qwen sequential-contract rejection is unchanged.
Existing component experiments and physical runs are separate historical evidence;
they do not establish the feasibility of the proposed architecture.

## Architecture direction and actual completion

The intended organization is a locally scheduled compute fabric supplied by
reusable operand banks and bounded memory requests, with explicit ownership,
backpressure, completion and writeback. Attention, KV and vector services must
have enough capacity to keep that fabric productive on supported workloads.

| Architectural priority | Progress | Remaining decision or proof |
|---|---|---|
| Reduce repeated data movement | Weight-pass reuse and gather coalescing are integrated | Demonstrate benefits across deployed workloads and supported configurations |
| Overlap useful work with memory service | Bounded outstanding reads and operand delivery have measured gains | Qualify integrated G2 memory/control timing and sustained service |
| Keep repetitive scheduling local | Pass scheduling and runtime control have implementation and block evidence | Close remaining admission/control paths and verify the complete execution path |
| Balance supporting engines | Exact exponential reuse and specialization improve softmax | Complete attention, vector/reduction and distributed service-rate assessment |
| Choose clocks from system requirements | 1 ns is the initial ASAP7 compute/local-control target | Qualify containing engines and real clock boundaries; whole-chip 1 GHz is unproven |

**Architecture work is not finished.** Recent effort has concentrated on component
and control timing. Those fixes support implementation, but do not complete the
broader architecture review requested for every target. The next architecture
checkpoint must reconcile workload demand, memory traffic, engine service rates
and integrated measurements before expanding component experiments.

## Improvements already integrated

| Area | What changed | Demonstrated result and boundary |
|---|---|---|
| Weight scheduling | Retain weights across output rows and schedule passes around reuse | K160 campaign: 708,336 → 203,111 cycles; weight bytes 207,336 → 34,556, at the same retained SRAM capacity |
| Memory requests | Support bounded outstanding ordered weight reads | Four-read configuration: 109,884 → 80,903.5 median cycles; configurable, default remains one |
| Operand delivery | Coalesce same-line gathers | Tested gather: 704.5 → 570.5 median cycles; 74.6% fewer weight bytes. Credit-four transport passes its tested 1 ns route |
| Softmax service | Reuse the last exact successful exponential result | Softmax corpus: 31.25% fewer cycles; earlier complete-attention comparison: 2.24% improvement |
| Softmax hardware | Instantiate exponential-only arithmetic, removing unused sigmoid hardware | 9.59% lower matched mapped area; complete softmax timing remains unresolved |
| Multiplier | Balanced reduction tree, selected at chunk16 | Final block setup slack −0.312 → +0.118 ns at 1 ns, slightly lower routed area, unchanged transaction cycles |
| KV index | Prefix-count encoding | 15.63% less routed area, passes tested 1 ns block checks, no added cycles |
| Wide divider | Shared dividend/quotient storage | 12.79% lower mapped area; selected CTS8 route passes tested 1 ns checks |
| Small divider | Shared storage, captured divisor and reset-free scratch state | Correctness qualified; step4 width168 passes its tested 1 ns route, but production consumers still use step10 |
| Exponential sizing | Derive series-divisor width from the configured term count | Numerical and protocol regressions pass; does not establish engine timing closure |

These results use different workloads and scopes. Their percentages cannot be
added, and none establishes whole-model energy efficiency.

## Experiments that are not integrated

| Candidate | What we learned | Current decision |
|---|---|---|
| Serial state apply pipeline | Final 1 ns setup improves to −0.370 ns, but still fails; adds area and two cycles per entry | Not selected |
| Overlapping state apply | Preserves 35-cycle general-ring apply, but other policies grow from one to three cycles. Final setup −0.494 ns and two fanout violations | Not selected |
| Parallel commit-counter increment | Final setup −0.351 ns, 1,356 violations; physical checks pass | Not selected |
| Per-slot parallel bounds checks | Shorter admission path, but 11.8% more mapped area and timing still fails | Not selected |
| Retained remaining capacity per slot | Commit-counter pre-layout slack −1.485 → −0.733 ns; 9.84% more area; no added cycles relative to overlap candidate | Stronger admission candidate; route pending |
| Reset-free private state payload | 4.60% less mapped area than retained-capacity candidate, worse pre-layout timing | Not selected |
| Reuse capacity within apply pipeline | Very small area saving, worse whole-block pre-layout timing | Not selected |
| Multiplier operand shifting | Removes idle hold/reset from private operand storage; standalone mapped area −1.39%; containing positive engine area −1.35%, unchanged cycles | Functional comparisons pass; matched standalone routes pending; not integrated |
| Positive-exponential range pipeline | Pre-layout slack −7.497 → −4.260 ns; area +3.18%; corpus cycles +0.0739% | Matched baseline/candidate routes pending |
| Softmax sortable-key tree | 4.49% less mapped area, unchanged cycles, slightly worse pre-layout slack | Matched routes pending |
| Four-bit divider steps in complete softmax | Divider itself passes 1 ns, but softmax needs 49.22% more cycles | Requires over 1.49224× complete-engine clock improvement to break even; route pending |
| Two-entry exact exponential cache | Softmax cycles −0.75%; complete attention cycles −0.60%; mapped area +0.36%; slightly worse pre-layout slack | Functional benefit confirmed; no production integration or routed qualification yet |

A pre-layout regression is evidence of risk, not proof that a routed design will
regress. Conversely, improved pre-layout slack is not proof of routed closure.

## What has been verified

- Arithmetic: the 4,200-case exponential/sigmoid corpus has 6,637,132 checks.
  The latest multiplier candidate passes this corpus in Verilator, 12 standalone
  differential tests, and eight positive-engine reset/backpressure tests across
  Icarus and Verilator. The full positive-engine comparison preserves all
  5,962,513 active cycles across 2,201 numerical cases plus four refusal/overflow checks.
- Positive-exponential range candidate: 2,201 exact numerical arguments plus
  four refusal/overflow checks; reset and output-stall tests in both simulators.
- State candidates: 28 differential tests across seven candidates, Icarus and
  Verilator, and 3/16-slot tables. Includes full-table lookup, high slot indices,
  counter carry/wrap, cancellation, refused requests and repeated retirement.
- Containing state-controller campaigns: 65 microsequencer cases and 4,555 checks
  per simulator for the tested candidates. These check control behavior, not
  every engine's arithmetic.
- Two-entry cache: eight protocol tests and fresh complete-attention comparison.
  All nine attention transactions remain exact; 2,388,699 → 2,374,287 active cycles.
- Latest recorded inventory: nine current-source extracted passing configurations
  out of 256 recorded routes. This is a historical-record inventory, **not**
  “nine of 255 required blocks complete” and not a hierarchy-coverage metric.

Physical acceptance includes setup, hold, fanout, slew, capacitance, DRC and
antenna checks. Source and retained-artifact hashes bind results to the measured
configuration. Slack-derived frequency estimates are not tested clock rates.

## What remains, and the next decisions

**Immediate:** collect and audit the existing matched physical runs as they finish. Select an
implementation only when its area, actual transaction cycles, correctness and
routed timing justify it. The retained-capacity controller, positive range
pipeline and multiplier operand shift are pending timing candidates. The latest
operand-service hold-repair retry still fails hold and has not been accepted.

**Next:** refresh the architecture-level bottleneck ranking against integrated
workloads, then implement the highest-value fix and qualify its containing
engine. Compare elapsed time, traffic and area as well as clock period; a faster
block that needs many more cycles can make its workload slower.

**Still required for the full goal:** current-source integrated G2 timing and
memory/control qualification; production scheduling across supported workloads;
coverage of dense, MoE, KV, vector and distributed targets; and qualification of
all requested technology/configuration combinations. Workload energy and
whole-model throughput remain unproven by the block-level results above.

The project is not complete. We have improved important parts, but the pending
integrated and all-target work is substantial.

## Where to look

- Read this document for the current overview.
- [Architecture-first plan](ARCHITECTURE_FIRST_OPTIMIZATION_PLAN.md): objective,
  priorities and exit criteria.
- [Detailed architecture review](ARCHITECTURE_REVIEW_SUMMARY.md): chronological
  findings with links to numerical and physical evidence.
- [Current-source route inventory](../results/physical_abi3/asap7/current_source_route_inventory.json):
  individual recorded configurations and reasons for inclusion/exclusion.

Future progress updates should identify: **production change, experiment, or
verification**, then state its effect on the next integration decision.

Latest technical checkpoint: [`6510912a`](https://github.com/bojieli/OpenTallas/commit/6510912a)
contains the complete positive-engine measurement. Its push to remote `main` was
verified at this reporting checkpoint. The working branch is `main`; unrelated
compiler, prototype and physical-result changes remain outside this report commit.

For reproducible evidence on the latest experiment, see
[`results/rtl/mul_operand_shift/`](../results/rtl/mul_operand_shift/), especially
[`positive_engine/comparison.json`](../results/rtl/mul_operand_shift/positive_engine/comparison.json).
