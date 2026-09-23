# Architecture-first optimization plan

Date: 2026-09-22. Status: architecture implementation in progress, following the user’s
requested order before detailed optimization. Supersedes block-by-block timing work as the
priority order; preserves the full recharacterization and optimization scope.

## System-budget checkpoint: 2026-09-23

The [ROM/HBM top-down assessment](ROM_HBM_PERFORMANCE_GAP.md) now sets the
implementation priorities. Fresh resource derivation shows that the five-die
Qwen pipeline cannot meet its older token-latency projection: KV service alone
exceeds that entire budget. The HBM compute budget needs sufficient weight reuse,
and the leading-node ROM study leaves auxiliary service capacity unpriced.
Before selecting further component changes, reconcile these system requirements
with current-source RTL, delivered bandwidth and containing-engine timing. Existing
physical runs remain useful evidence, but they cannot complete this architecture gate.

## Proposed implementation direction for review

[ROM-first architecture proposal](ROM_FIRST_ARCHITECTURE_PROPOSAL.md) specifies
bank-local compute, local KV attention, certified pipelined numerical services,
hierarchical control and dedicated collectives, plus a reuse-oriented HBM variant.
Its eight-die Qwen configuration and 85/75 µs budgets are unqualified engineering
targets. The executable review model explicitly tests HBM persistent weight cache
and identifies where a threefold advantage remains unproven. This proposal does
not switch production defaults or relax numerical/release contracts.

## Assessment

The project contains useful, optimized components, but does not yet demonstrate
a well-optimized integrated accelerator. Significant architectural performance
risks remain. The next decision should be which system organization to build,
not which isolated block has the worst MHz number.

Existing evidence gives specific reasons:

| Observation | Architectural implication | Evidence limitation |
|---|---|---|
| Published compute-unit route is about 1.29 GHz; covered softmax about 251 MHz; the recovered pipelined Sinkhorn experiment estimates 427 MHz but misses its target. | Clock-domain organization and supporting-engine capacity can dominate useful throughput. | These are different historical source/configuration snapshots, not an integrated chip clock. |
| Published control experiment measures 116.4 cycles/command at 265 MHz. Hardware fan-out and three passes/descriptor achieved 99.1% utilization in a bounded 16-unit experiment. | Coarse commands and local scheduling have demonstrated value; verify their use throughout the deployed machine. | Tensor-only and synthetic steady-state evidence does not prove full-model issue, dependencies, or small-kernel performance. |
| The historical model example reported about 3.4% of tensor peak. Current full-symbol Qwen replay instead shows roughly 96–97% tensor service efficiency against its assumed table rate at span 1. | Use the current admitted workload and distinguish modeled service efficiency from integrated utilization. | Neither value is measured RTL utilization; model clock and resource assumptions still require calibration. |
| Existing power attribution assigns roughly 75% of compute-unit power to operand delivery and sequencing. | Reuse, storage organization and data movement deserve priority over multiplier tuning. | Attribution is by subtraction using default switching activity, not measured workload energy. |
| Several engine paths serialize exact arithmetic; softmax handles exponentials one at a time. | Service rate, recurrence latency and engine replication may limit throughput even after timing closes. | Required throughput depends on actual operator shapes and overlap. |
| Coverage inventory reports 18 instantiated modules without closed coverage; other evidence is stale after RTL edits. | Whole-design performance and area remain unproven. | Regenerate and validate configuration-specific coverage before treating the count as current. |

References: `CONTROL_PATH_DESIGN.md`, `DATAPATH_PIPELINE_REDESIGN.md`,
`CHIP_ARCHITECTURE_REVIEW_HANDOFF.md`, current RTL and physical records, and
`results/physical_abi3/asap7/recovered_session_experiments.json`.

## 1. Establish the actual machine and workloads

Trace each supported deployment from compiled descriptors through instantiated
RTL to memories, compute units, vector/reduction units and transport. Distinguish
shipped execution from standalone prototypes and analytical compositions. Record
parameter values, precision, buffer capacities, instance counts, clock domains,
and source identities. Do not combine the best numbers from different designs.

Cover every supported model/capability family in the target inventory. Use
representative operator traces first, then validate full deployed traces. Include
batch-one decode, longer-context attention, prefill/batched reuse, dense and MoE
work, and single-chip versus distributed execution where supported. Use actual
supported sequence lengths, batch sizes and precisions rather than invented
benchmark shapes.

Deliverable: a block/clock/memory diagram and a deployment-to-hardware matrix,
with a list of integration gaps and a reproducible baseline for each workload.

Exit criterion: every performance-critical path and allocated resource has an
identified implementation or an explicit unresolved assumption.

## 2. Attribute end-to-end latency and utilization

Build a dependency-aware timeline from the actual programs. Charge command
admission, address/dependence resolution, weight and activation movement, KV
service, arithmetic, reductions, collectives and final write acknowledgement.
Represent overlap explicitly: concurrent service times cannot simply be summed,
and peak bandwidth cannot imply free overlap. Enforce finite ports and buffers.

For each resource record demand, sustainable service rate, queue occupancy,
useful work, issue stalls, memory stalls and dependency stalls. Separate pipeline
latency, initiation interval and clock frequency. Explain the existing 3.4%
cycle-model utilization example by tracing its actual charging and mapping rules.

Deliverable: ranked end-to-end bottlenecks and sensitivity results for improved
compute, memory, control and network rates, including area costs. Use critical
path and resource bounds to estimate how much each proposed change can help.

Exit criterion: the baseline reconciles operator counts, bytes, cycles and
measured RTL transaction timing; remaining prediction uncertainty is explicit.

## 3. Resolve architecture choices before block tuning

Evaluate the following in this order, revisiting priorities if step 2 contradicts
them:

1. **Dataflow and reuse.** Choose GEMV/output-stationary behavior for decode and
   a reuse-capable GEMM organization for prefill/batched work. Evaluate shared
   hardware versus separate modes. Charge activation filling, weight scales,
   bank conflicts, refill and writeback. A GEMM peak multiplier count is not a
   system speedup.
2. **Memory and transport balance.** Size and bank scratchpads, KV storage and
   staging against delivered bandwidth. Compare single/double buffering with
   real producer/consumer overlap and capacity. Define collective schedules and
   count shared injection, credits and receiver commit bandwidth.
3. **Control hierarchy.** Put repeated tile loops, fan-out and local completion
   tracking near engines. Resolve invariant descriptor/address work once when
   possible. Keep dependence and fault semantics intact. Check issue rate at the
   smallest kernels and widest configurations; deeper queues do not cure a
   sustained rate deficit.
4. **Engine balance.** Size vector, reduction, routing and transcendental service
   to actual tensor output demand. Compare interleaving, replication, pipelining
   and fusion using complete latency/area costs. Maintain existing numerical
   contracts; any proposed relaxation is a separate numerical design decision
   requiring qualification, not an optimization silently built into RTL.
5. **Clock organization.** Compare a common clock with explicit decoupled domains
   or multicycle engines. Include CDC, buffering, latency and backpressure costs.
   Use 1.0 GHz as the initial engineering target for the main ASAP7 compute/local
   control fabric, and investigate 1.2–1.5 GHz only where it improves system
   results. These are targets, not achieved closure. A slower engine needs a
   demonstrated service budget and real boundary; do not exclude it on paper.

Deliverable: an architecture decision record for the selected organization,
alternatives, expected end-to-end benefit, area/memory cost, risks, and acceptance
measurements. Rank work by expected system benefit, not standalone frequency.

Exit criterion: selected resources can meet workload demand with implementable
interfaces and the performance model includes their complete costs.

## 4. Implement the highest-value architectural changes

Integrate one complete producer-to-consumer path at a time, including scheduling,
operand delivery, compute, completion and writeback. Verify stalls, reset,
dependencies, tails, variable shapes and error handling. Calibrate its cycle
model against RTL before expanding to more units and workloads.

Deliverable: integrated improvements with before/after latency, utilization,
area and memory traffic at matched numerical behavior and workload.

Exit criterion: the expected architectural benefit survives integration without
transferring an unbudgeted bottleneck to another resource.

## 5. Optimize and recharacterize the selected implementation

Now use timing reports to balance pipelines, replace dependent arithmetic chains,
reduce mux depth, narrow counters and intermediates safely, eliminate redundant
control work, and map storage appropriately. Evaluate clock times transaction
cycles; pipeline depth alone is not a latency improvement.

Route all instantiated configurations and shared primitives affected by changes,
including containing blocks. Require setup, hold, slew, capacitance, fanout, DRC
and antenna checks, with current source hashes. Report area for registers,
buffers, clock trees and memory as well as arithmetic. Retire or explicitly mark
superseded historical evidence.

Deliverable: current full-scope characterization and functional regression
evidence tied to the selected architecture. No synth-only result substitutes for
routed closure of register-rich blocks.

## 6. Validate the complete outcome

Rebuild deployed programs and refresh cycle calibration. Verify full workload
correctness and numerical contracts. Report prefill latency, decode latency,
throughput, useful utilization, area, traffic and energy with an appropriate
activity basis. Preserve equal implementation effort and accounting for ROM and
HBM comparisons. Include all required memories, network resources and control.

Completion requires evidence for every supported design/configuration in scope,
all remaining bottlenecks reviewed, and architecture improvements verified in
integrated execution. Passing a microbenchmark or completing a PNR sweep is not
sufficient. Predictive ASAP7 results remain distinct from measured silicon.

## Immediate working order

The initial integration audit and Qwen staging analysis identified runtime
operand delivery as the first architecture change. The chosen organization is
specified in `RUNTIME_OPERAND_ARCHITECTURE.md`; detailed findings are in
`ARCHITECTURE_INTEGRATION_REVIEW.md`. The Qwen baseline is a synthetic-input
cycle-model result, not external-oracle qualification or RTL performance.

Ownership, independent SRAM banks, issue-credit stalls and bounded weight-tile
prefetch now have functional checkpoint evidence through actual LQ8 arithmetic.
The matched 92-case comparison reduces aggregate operation cycles by 13.65%
with overlap, using a behavioral activation/scale producer. It is not yet a
complete G2 runtime execution path or a physical performance result.
Proceed in this order:

1. Independent future-address generation and a bounded auxiliary response
   queue now pass the integrated corpus. Two entries retain nearly all of the
   eight-entry benefit with 75% fewer queue storage bits. Next replace the
   behavioral external service with production runtime transport and reusable
   activation/scale SRAM. A synthesizable weight burst/tile scheduler now
   replaces the testbench controller; checked stream-length admission and
   G2 connection remain open. Captured RTL geometry
   admission now feeds the cursor; full format admission and G2 operation
   lifetime still need consolidation.
   Preserve verified accumulator continuity and complete-bundle alignment.
2. Connect a separate runtime refill interface and immutable operation identity
   to cluster admission, fault draining, completion and writeback.
3. Add bounded multi-row reuse and specify/qualify the blocked numerical
   association; calibrate full-workload predictions on the integrated path.
4. Review attention, vector/reduction, transport and clock/service balance across
   the supported inventory, then optimize and route each selected component.

Standalone component tuning remains deferred. Keep existing physical experiments
as historical evidence until the selected integrated design is recharacterized.
Architecture acceptance requires matched before/after workload measurements;
passing delivery tests does not satisfy that gate.
