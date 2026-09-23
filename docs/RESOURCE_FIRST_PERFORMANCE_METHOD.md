# Derive performance from the machine, not the deadline

The user's latest direction supersedes fixed-100-µs feasibility planning.
**Choose and constrain a physically plausible architecture first; derive its
latency and throughput afterward.** Keep 100 µs/token only as a historical
sensitivity marker. Do not select lane counts, ROM ports or a 40 µs expert budget
by dividing work by a desired deadline and then call those resources feasible.

## Required comparisons

1. HBM accelerator array: optimized GPU-style baseline.
2. ROM chip array: primary proposed design.
3. Integrated ROM wafer or connected wafers: secondary option, with explicit
   external KV/Engram interfaces and manufacturing/integration uncertainty.

Compare equal total die area and separately equal system power, plus deployments
sized to hold the model. Include interconnect and packaging overhead. Qwen 8B is
a separate compact dense-model design study; V4.1-Flash is the distributed MoE
study. Do not transfer the distributed communication penalty to a local design,
or assume the full 8B checkpoint fits a single tile without a capacity definition.

## Resource-first derivation

For each candidate, specify before computing tokens/s:

- Process and evidence quality; die/wafer count and usable area; ROM/SRAM/HBM
  capacity and port organization; compute and numerical-service area; power cap.
- Weight and KV placement, operator ownership, cache policy and admitted numeric
  contracts. Packed versus expanded execution formats must be explicit.
- Local delivered memory and arithmetic rates, recurrence latencies and finite
  buffers. Use characterized inputs where available; label uncharacterized inputs
  as a sweep, not as physical facts.
- Interconnect topology, delivered payload rate per direction, fixed endpoint/hop
  latency, bisection, collective algorithm and contention assumptions. Count only
  actual cross-chip boundaries after co-location.

Then derive an operator dependency graph. For each operator, local compute time
is constrained by work/rate and recurrence. Memory contributes bytes/delivered
rate plus access constraints. Communication contributes fixed delivery, payload
serialization and collective dependencies. Take a maximum only where overlap is
actually supported; sum operations that must happen serially. Include numerical,
selection, control, cache miss and slow-path service—not merely GEMM and bytes.

Apply finite resource sharing and buffering to that graph. Sum the dependent
critical path to obtain per-sequence time per output token. Improve the architecture
at the binding bottleneck, recompute the path, and stop claiming improvement from
resources that cannot shorten it. Do not credit capacity-only inactive dies as
active compute or bandwidth.

## Report three distinct results

**Optimistic ceiling:** derive a lower bound on latency from required work,
qualified resource limits and unavoidable dependencies. Its reciprocal is an
upper bound on single-sequence tokens/s. It is not an achieved design point.

**Constructive design estimate:** provide a feasible finite schedule, within area,
capacity and power, including service and communication. Report uncertainty in
uncharacterized inputs. Until those inputs and the schedule are qualified, do not
call this physically implementable or measured.

**Aggregate throughput:** separately derive the maximum sustainable token rate
across independent sequences from pipeline occupancy, bottleneck service, memory
capacity, routing skew and queue stability. Give batch/concurrency and per-user
latency. More occupied stages can increase aggregate output without shortening
one user's token recurrence. In steady unbatched single-sequence decoding only,
100 µs TPOT corresponds to 10,000 tokens/s, excluding startup/prefill.

## How existing calculations will be used

The bytes, tensor shapes, arithmetic work and pinned-source findings remain useful.
The 100 µs bandwidth/engine requirements are sensitivity screens, not selected
hardware specifications. The hypothetical link sweeps are communication examples,
not NVLink measurements. The sequential Qwen recurrence and V4.1 native-block
semantics remain contract-dependent constraints, not assumptions to discard for
speed. The previously derived cache and common-work speedup limits still apply.

For example, one hypothetical V4.1 placement with 400 GB/s endpoint service and
0.5 µs fixed one-way delivery spends 52.288 µs on serial expert dispatch/return
and 36.384 µs on central attention-output partial return. Their 88.672 µs sum
excludes most compute, memory and other service. Its reciprocal, about 11,278
single-sequence tokens/s, is only a **communication-only ceiling for that specified
serial placement**, not a whole-system forecast. Co-location and overlap can
change the placement model; omitted work makes that same model slower. This is
how to interpret a bound without designing backward from it.

## Immediate next architecture work

Consolidate a small set of resource-constrained array candidates, with separate
HBM and ROM weight systems and the same numerical and fabric opportunities.
Reconcile their area and active-layer placement before deriving latency. Evaluate
compact Qwen separately. Use physical macro/compute/link evidence to narrow the
resource sweeps; where evidence is absent, report which unknown prevents a numeric
physical maximum rather than fabricating precision. Keep wafer options secondary.

Only surviving feasibility candidates proceed to implementation and workload/RTL
simulation. Documentation volume and isolated arithmetic tests do not establish
that this gate has passed.
