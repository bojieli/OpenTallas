# DeepSeek-V4.1-Flash: single-user-first top-down design

2026-09-28. Design directive and proposed selection process. This document takes precedence over any interpretation of the fabric proposal that treats multiuser utilization as an equal objective. It does not assert a completed design or a measured token rate.

## 1. Objective and constraints

**First minimize single-user decode latency; then improve aggregate throughput without sacrificing the selected single-user operating point.** Utilization is a diagnostic, not an objective. An idle dedicated engine can be the correct latency tradeoff.

Hold checkpoint/arithmetic, context, physical capacity, die/package count, area, cooling and interface feasibility explicit. The existing hardware envelope is the baseline constraint, not proof that its internal placement is correct. If a proposed solution requires more dies or memory, present that as a separate costed alternative.

For autoregressive decode, measure latency from availability of the committed input token/state to availability of the next token and committed state needed by the following step. Include embedding, all layers, transfers, head, sampling policy and feedback. Report 200K and 1M separately, plus representative and concentrated expert routes. Do not hide a regression at one context in an average.

For MTP, maximize accepted output tokens per wall-clock time with the same correctness and physical constraints. Include drafter, verification, acceptance, rejected work and commit/rollback. AR is the first diagnostic and integration gate; the final choice between AR and MTP follows measured accepted-token performance. Independent users enter only as the secondary optimization experiment.

## 2. Start with the token, not a collection of engines

Build one exact, all-layer dependency graph from the executable program and checkpoint. Include non-matrix work, quantization and rounding boundaries, state reads/writes and actual communication. The graph is specific to context, selected experts and speculative positions.

For every node and edge record:

- Exact producer, consumer and readiness condition, with units and data format.
- Work, physical bytes and first/last operand readiness.
- Owning die, ROM bank, compute tile, SRAM ports, HBM stack/PC and link.
- Startup latency, sustained service, queue/storage lifetime and completion rule.
- Evidence type: measured, physically characterized, simulated or unverified assumption.

Use a finite-resource scheduler. Independent branches can overlap only if their shared ports, banks, issue capacity and power permit it. A critical-path DAG with unconstrained resources is a lower bound, not the implementation schedule.

A useful abstraction for one layer is projection and positional work, index/selection and KV fetch where required, attention, output projection, then router/shared/routed FFN work and the specified residual/HC operations. The actual golden program determines each dependency; this abstraction does not authorize reordering it.

## 3. Placement is a latency decision

The lead architecture is distributed ROM with local digital MACs. Keep weights local and distribute activation/results. Select the largest useful locality region that fits and routes; neither one engine per matrix nor one global shared pool is a prerequisite.

Prefer complete executable layer groups when capacity permits. Otherwise keep a coherent layer completion owner and explicitly partition tensors/experts. Minimize exposed synchronization and round trips under actual ROM capacity, not simply the imbalance of stored bytes. The current 28-stage fractional partition is a candidate to replace or validate, not a frozen optimum.

For split experts, compare a correctness-first ordered accumulator round trip with a forward-continuation mapping that moves or replicates completion operators. Charge their weights, state and power; the small remaining ROM margin cannot be assumed to absorb them. Preserve sorted expert addition and shared-last semantics. A balanced multiuser pipeline is a later optimization constraint.

Keep TP-4 as the current exact candidate. Test alternative tensor mappings within the same die envelope only when their change to local work, communication, numerical reduction and capacity is explicit. More parallel ranks can increase single-token latency through communication; fewer ranks can increase compute latency.

## 4. Derive compute and fabric widths together

Choose compute parallelism from exposed single-token work. Every candidate width needs matching ROM read ports, activation delivery, accumulator bandwidth and result drainage. Dedicated quantization, normalization, softmax and reductions remain useful if they shorten the full path and fit.

Compare fixed local ROM/MAC tiles with bounded neighboring-bank sharing. Reject a sharing scheme that saves idle area but adds a critical operand hop or contention that costs more token time than its reallocated resources save. A global weight crossbar needs its own full physical proof before consideration.

For each serial or join-critical transfer, provision the producer, link and sink together. Pipeline at dependency-valid chunk boundaries; do not wait for a complete tensor when an exact chunk can start its consumer. Do not claim this overlap where the golden's scale calculation, reduction or softmax requires the complete input.

The current program's seven separate activation gathers must be measured as emitted. Compare early per-expert BF16 transfer with explicit FP8 packing/fusion only after preserving the quantization contract. A fused transfer can reduce startups and still lose latency by waiting for its last producer.

Physical pipeline registers are necessary when wires fail timing, but their fill/drain latency must enter the token schedule. Compare time in seconds at achieved frequency, not cycles at an assumed clock.

## 5. HBM and sparse attention

Index scanning, selected-row service, window KV, constants and comparator weights share physical HBM resources. Schedule them on one stack/PC model with bounded outstanding requests and actual return bandwidth.

Prioritize requests that unblock the current token's next dependent operation, with bounded service for all other admitted work. The priority must be derived from readiness/deadlines and include non-preemptible in-flight transactions. A label such as latency priority does not eliminate contention.

Pipeline scan production, scoring and selection where exact ordering permits. Fix collector cadence before increasing nominal bandwidth. Once selected rows are known, fetch at the owning die and multicast packed rows, preserving the attention computation's exact order. Any progressive selection/fetch optimization must prove that discarded candidates cannot alter the answer.

For single-user operation, retain useful per-user window/activation state when capacity permits. For multiple users, explicitly charge cache replacement and context-switch traffic. Do not use a preloaded single-user window to predict arbitrary multiuser throughput.

## 6. Optimize by end-to-end sensitivity

For each candidate change, recompute the complete finite schedule and achieved-frequency token time. Record latency saved, extra area/capacity/power, newly exposed bottleneck and physical risk. A byte reduction or operator speedup alone is insufficient.

Evaluate coupled changes when one resource masks another: for example, widening a receive link without its SRAM sink can show no benefit, while widening both may help. Limit candidates to those with a plausible token-path gain or those required to resolve an architectural feasibility risk. Do not run open-ended component sweeps.

A current example: the matched full wo_a adapter gate reports 133,261 cycles for narrow loading and 131,345 for wide preload, both exact. The 1,916-cycle saving is only 1.44% of that narrow compute geometry. It establishes a load-path improvement; it does not establish the same percentage at the design-point MAC width or for the full token. Use the implemented geometry in the schedule and identify which resource becomes critical next.

Select a physically feasible latency/Pareto candidate rather than assert a global optimum. Stop widening when expected end-to-end improvement is below the physical cost or when the dependency moves elsewhere. Preserve alternatives for different context lengths instead of choosing an arbitrary average score.

## 7. Multiuser optimization after the single-user design

Freeze the chosen single-user resource allocation and service contract. Then admit independent users into idle stages or unused slots using tagged contexts and credits. Measure throughput, per-user latency and tail latency versus admitted users.

Distinguish preserving isolated latency from guaranteeing that latency under load. Concurrent non-preemptible work may delay the latency-sensitive user. Reserved service windows, limited admission and bounded bursts are needed to bound that interference. If no nonzero latency increase is feasible, publish the tradeoff rather than silently changing the primary goal.

Stage balance, MAC utilization and HBM occupancy are secondary diagnostics. Accept an aggregate optimization only if it preserves the agreed single-user service constraint; otherwise label it as a separate throughput-oriented mode.

## 8. Work order and acceptance artifacts

1. Root owns one exact architecture contract: operating points, resource envelope, numerical rules and the token-completion boundary.
2. Placement/emitter owners produce integer tensor/expert/physical-bank ownership and an executable all-layer packet schedule. Missing mappings are explicit blockers.
3. Schedule/model owner constructs the baseline finite-resource single-token trace, listing measured service and unresolved assumptions. This is the decision tool for compute, memory and fabric changes.
4. RTL owners close the real layer-0 TP sequence, an index-heavy layer and a split-layer forward/return slice. Physical owners characterize precisely the corresponding local memory/fabric boundaries.
5. Root selects a bounded set of coupled candidates from full-token sensitivity, and integrates only changes that pass exact execution and a complete capacity/physical ledger.
6. Execute the full AR chain, then full MTP, at the chosen geometry. Derive performance from cycles, achieved clock and accepted tokens.
7. Optimize spatial multiuser admission and scheduling while preserving the selected latency contract.

The final artifacts are one manifest, compiled program/images, finite resource trace, exact result, physical evidence and derived rate record with matching source pins. This top-down chain is the acceptance criterion for the design.
