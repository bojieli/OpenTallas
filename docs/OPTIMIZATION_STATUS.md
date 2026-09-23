# Accelerator optimization status

Status snapshot: 2026-09-23. Production work is on `main`. This summary covers
changes through `e5f0ed9c`; the commit containing this document follows it.

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

1. Tracing the positive-exponential range pipeline's remaining timing path back
   from mapped cells to RTL. Its worst pre-layout path has only three logic
   cells but large launch/buffer delays; control fanout is a hypothesis being
   checked, not a confirmed source-level diagnosis.
2. Waiting on existing place-and-route comparisons for state admission,
   positive exponential and softmax. Their processes were verified live when
   this document was written. These runs are not being restarted.
3. Turning completed results into implementation decisions. The latest finished
   overlap-controller route was rejected because setup and fanout still fail. The
   retained-capacity state route, current step-four softmax route, softmax key-tree
   pair and positive-range pair remain live physical jobs; their output records
   do not yet exist.

No new production optimization is being claimed from that ongoing work.

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
| Parallel commit-counter increment | Small pre-layout improvement; complete controller route pending | Await route |
| Per-slot parallel bounds checks | Shorter admission path, but 11.8% more mapped area and timing still fails | Not selected |
| Retained remaining capacity per slot | Commit-counter pre-layout slack −1.485 → −0.733 ns; 9.84% more area; no added cycles relative to overlap candidate | Stronger admission candidate; route pending |
| Reset-free private state payload | 4.60% less mapped area than retained-capacity candidate, worse pre-layout timing | Not selected |
| Reuse capacity within apply pipeline | Very small area saving, worse whole-block pre-layout timing | Not selected |
| Positive-exponential range pipeline | Pre-layout slack −7.497 → −4.260 ns; area +3.18%; corpus cycles +0.0739% | Matched baseline/candidate routes pending |
| Softmax sortable-key tree | 4.49% less mapped area, unchanged cycles, slightly worse pre-layout slack | Matched routes pending |
| Four-bit divider steps in complete softmax | Divider itself passes 1 ns, but softmax needs 49.22% more cycles | Requires over 1.49224× complete-engine clock improvement to break even; route pending |
| Two-entry exact exponential cache | Softmax cycles −0.75%; complete attention cycles −0.60%; mapped area +0.36%; slightly worse pre-layout slack | Functional benefit confirmed; no production integration or routed qualification yet |

A pre-layout regression is evidence of risk, not proof that a routed design will
regress. Conversely, improved pre-layout slack is not proof of routed closure.

## What has been verified

- Integrated arithmetic: 4,200-case exponential/sigmoid corpus with 6,637,132 checks.
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
  out of 255 recorded routes. This is a historical-record inventory, **not**
  “nine of 255 required blocks complete” and not a hierarchy-coverage metric.

Physical acceptance includes setup, hold, fanout, slew, capacitance, DRC and
antenna checks. Source and retained-artifact hashes bind results to the measured
configuration. Slack-derived frequency estimates are not tested clock rates.

## What remains, and the next decisions

**Immediate:** finish and audit the existing matched physical runs. Select an
implementation only when its area, actual transaction cycles, correctness and
routed timing justify it. The retained-capacity controller and positive range
pipeline are the main pending candidates for removing timing bottlenecks.

**Next:** implement the next measured bottleneck fix and qualify the containing
engine. Avoid accumulating further minor candidates unless they address a
specific unresolved path or throughput limit.

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
