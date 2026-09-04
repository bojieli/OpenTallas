# ABI 3.0 tensor-datapath decode-utilization architecture decision and production plan

**Decision ID:** TA-A3-DP-1

**Status:** accepted for implementation; correctness and performance evidence open

**Issue date:** 2026-09-03

**Applies to:** the shared HBM/SRAM tensor-accelerator chip used as one chip for
Qwen3-8B and as 32 identical chips for DeepSeek-V4 Flash; the correctness and
TPOT evidence rules also govern the corresponding Qwen ROM chip and DeepSeek
ROM wafer comparison points

**Governing architecture:**
[Tensor-accelerator ABI 3.0 and RTL 3.0 architecture decision](TENSOR_ACCELERATOR_ABI_3_ARCHITECTURE_DECISION.md)

**Related evidence contracts:**
[four-target master plan](FOUR_TARGET_IMPLEMENTATION_MASTER_PLAN.md),
[four-target progress report](FOUR_TARGET_PROGRESS_REPORT.md), and
[ABI 3.0 frozen wire format](TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md)

## 1. Outcome and release rule

OpenTallas will implement one shared, maskable and row-foldable tensor datapath
for both Qwen3-8B and DeepSeek-V4 Flash. It will not add a second narrow decode
engine to the baseline chip. The tensor front end derives active work from the
resolved ABI 3.0 tensor views, maps only valid output coordinates onto physical
lanes, and reassigns capacity that would have belonged to absent rows to useful
output columns. This is an implementation profile of the existing ABI 3.0
wire format. It adds no ABI 3.1 requirement, opcode, descriptor field, state
member, or host-visible recovery mechanism.

The program has two highest-priority release gates, in this strict order:

1. **Correct-token gate:** a source-current, end-to-end accelerator execution
   must produce the same legal token IDs as the independent model oracle, decode
   to legitimate text, include the first official EOS when one occurs, stop at
   EOS or the exact declared cap, and execute no model step after EOS.
2. **TPOT gate:** only a run that passes the correct-token gate may supply a
   target time per output token. Target TPOT comes from raw architectural token
   commit ticks and characterized target timing, never from Python wall time,
   RTL-simulator wall time, a roofline, or an uncorrelated cycle estimate.

**Normative promotion rule:** a performance point MUST NOT be published as
executed TPOT or used for an SLO verdict unless the exact same execution
identity first passed complete token-ID equality, legal-token and decoded-text
validation, EOS-inclusive-or-exact-cap termination, and no-post-EOS execution.
The identity includes the batch execution, source, checkpoint, tokenizer,
workload, graph, Kernel IR, deployment, descriptor table, capability,
implementation, topology, process/PVT, and timing-source digests. Passing a
different run, even with the same prompt text, does not qualify the timing
point. Host elapsed time and functional- or RTL-simulator wall time are campaign
cost measurements only; architectural TPOT is derived solely from bound target
token-commit ticks and the admitted target timebase.

The aspirational north star remains **10,000 generated tokens/s, equivalent to
100 microseconds per output token**. It is not a release pass criterion. The
release SLO is still unfrozen for each model, target role, context length,
process view, PVT corner, batch size, and concurrency point. Until those budgets
are frozen in the comparison contracts, performance can be measured but the
TPOT gate can only be `not_evaluable`, not `pass`.

Correctness is not traded for speed. Any optimization whose arithmetic order,
conversion point, address set, EOS behavior, or token sequence is not proved
equivalent fails closed.

## 2. Scope and target matrix

The physical comparison remains the one fixed by ABI 3.0:

| Model and workload | HBM/SRAM target | ROM target | Mandatory context and termination |
|---|---|---|---|
| Qwen3-8B | one shared tensor-accelerator chip | one Qwen-specific conventional ROM chip | exactly 8,000 prompt tokens; first official EOS inclusive or exactly 256 generated tokens |
| DeepSeek-V4 Flash | exactly 32 identical copies of the Qwen-class HBM/SRAM chip over the admitted NVLink-class fabric | one DeepSeek-specific wafer-scale ROM accelerator with on-wafer fabric and distributed HBM | exactly 200,000 prompt tokens; first official EOS inclusive or exactly 256 generated tokens |

The HBM/SRAM netlist is model-neutral. Qwen and DeepSeek use different compiled
descriptors and programs but the same tensor lanes, SRAM organization, HBM
interfaces, engine interfaces, device micro-ISA, and link endpoint. DeepSeek
does not authorize a larger model-specific HBM chip.

This decision is primarily the HBM/SRAM tensor-datapath decision. A ROM backend
may exploit a different physical weight-delivery structure, but it must obey the
same logical tensor and numeric contracts and the same correctness-before-TPOT
evidence rule. ROM/HBM performance comparisons use the same process view, PVT,
workload, batch point, correctness policy, and latency boundary.

### 2.1 What counts as a full execution

A full artifact-driven, or artifact-only, functional accelerator execution
begins with the governed prompt token IDs, takes all model semantics from the
serialized compiled deployment, executes every prefill and decode operation
through the ABI 3.0 engine models, performs selection and token append in the
accelerator model, updates live KV and related buffers, and stops through the
device EOS-or-cap path. It **is** full causal numerical model execution at the
functional-simulator boundary. Host software may load the deployment, tokenize
input, and decode returned token IDs. It may not supply activations, routes,
logits, selected tokens, or hidden model results.

A structural artifact replay only parses, hashes, admits, disassembles, traces,
or costs a compiled bundle without executing all of its numerical model
operations. That is useful compiler evidence, but it is **not** a full model
execution and cannot pass token correctness or qualify TPOT. A full
artifact-driven functional execution is not automatically cycle-accurate, RTL,
post-layout, or silicon execution; the evidence tier must always be stated.

## 3. Current evidence and the defect being addressed

At this decision point neither mandatory token gate is closed:

- Qwen has no source-current exact-8,000 natural-context acceptance pair. The
  retained captures bind stale source, capability, oracle, or deployment
  identities, and the latest source-current attempt received `SIGTERM` after
  1:53:08 without producing a JSON completion or a token.
- DeepSeek has no complete exact-200,000 accelerator execution on either the
  32-node HBM/SRAM cluster or the ROM wafer. The retained external oracle stops
  at an eight-token limit rather than EOS, and retained accelerator prefixes are
  stale after a numeric repair.
- Integrated RTL executes bounded prefixes and individual arithmetic/link
  slices, but no current RTL path generates a complete model token.
- Consequently, no existing tokens/s or TPOT number is correctness-qualified.

The current Qwen decode schedule also exposes a physical-design question that
must be answered before a credible performance claim. Its 253 decode matmuls
contain 7,568,097,280 useful work units but the existing fixed-tile cycle policy
charges 445,151,444,992 issued units. The difference is 437,583,347,712 padded
units, or approximately 98.30 percent. The same matmul set has no row padding
for a 64-token prefill span.

That report is a diagnostic, not a lane measurement. ABI 3.0 already carries
tile rows, columns, and depth, while the existing capability advertises 256
tensor lanes, but the implemented RTL does not bind the tile axes to those
lanes or consume an active-row mask. The current cycle report therefore marks
physical lane utilization `not_derivable`. Changing a compiler tile from 64
rows to one row before implementing the hardware semantics would only create a
cycle-model speedup and is forbidden as performance evidence.

## 4. Alternatives considered

| Criterion | One maskable/foldable datapath | Separate narrow decode engine |
|---|---|---|
| ABI 3.0 fit | Existing tensor opcode, views, schedule, and numeric descriptor are sufficient | Can be hidden behind the same opcode, but needs a second internal dispatch and resource policy |
| Qwen/DeepSeek dynamism | One netlist handles prefill, decode, dense, grouped, and routed contractions | Narrow path risks becoming shape- or model-specific |
| Numerical control | One accumulator and conversion implementation to qualify | Duplicate arithmetic and conversion paths must remain bit-equivalent |
| SRAM/HBM system | One operand network, accumulator store, queue set, and memory arbitration point | Duplicates ports or adds arbitration and capacity that sits idle during prefill |
| Verification | One lane scheduler and one arithmetic path | Two datapaths plus crossover and dispatch verification |
| Likely cost | Folding/valid routing and clock gating add mux and control cost | Extra lanes, controller, buffering, and interfaces add area and leakage |
| Decode utilization | Columns and live batch rows consume lanes that fixed row slots would waste | Naturally efficient for narrow rows |
| Risk | Fold network can hurt frequency, routing, or power | Duplicated engine can hurt area, bandwidth contention, and verification closure |

The selected baseline is the shared datapath because it is the smallest
architecture that is dynamic across both models and both phases. A physically
separate narrow engine remains a fallback only if same-process implementation
evidence shows that the foldable datapath cannot meet a frozen release SLO and
that a narrow engine does meet it within the frozen area, power, memory-port,
and correctness budgets. A roofline or cycle-model-only advantage is not enough
to trigger that fork.

## 5. Physical tensor architecture

### 5.1 Baseline lane organization

The current single-chip capability is the planning baseline: one tensor engine
with four command queues and 256 physical MAC lanes, eight HBM channels, and
128 MiB of SRAM arranged as 32 banks with two advertised ports. These values
remain claims until the integrated netlist and memory boundary are
characterized; a JSON capability alone does not prove their physical existence.

The tensor engine will organize the 256 lanes as four independently gated
64-lane issue groups behind one descriptor front end and one completion point.
The four groups are not four independent semantic engines, and the four ABI
queues do not imply four copies of the datapath. Queue arbitration feeds the one
shared lane fabric.

Each active lane contains or is time-interleaved onto:

- input format decode and scale application required by the selected numeric
  profile;
- one product path;
- an FP32 accumulator context identified by logical output coordinate;
- exact exception and saturation detection; and
- the selected final conversion path.

The physical pipeline may be deeper or interleaved, but it may not change the
declared arithmetic association. Achieved products per lane-cycle, pipeline
fill, and stall behavior come from RTL and post-layout characterization rather
than from the lane count.

The existing scalar `ot_a3_mac_lane` is useful arithmetic evidence but is not a
256-lane tensor engine and does not close this decision. The integrated engine
must instantiate or otherwise physically realize the admitted lane capacity,
descriptor front end, SRAM interfaces, masks, accumulator residency, and
completion behavior.

### 5.2 Existing ABI 3.0 schedule-to-lane semantics

No wire-layout change is required. For a tensor instruction, the implementation
resolves the operator's tensor views after applying request symbols, loop
inductions, dynamic extents, and any `edge_mask_id`. The operator convention
then produces the logical contraction:

~~~text
[M, K] x [N, K]^T -> [M, N]
~~~

Grouped and routed forms produce the corresponding bounded set of contractions
before the same lane-mapping rule is applied.

The existing `SCHEDULE` fields have these meanings for the tensor engine:

- `tile_rows`, `tile_cols`, and `tile_depth` are maximum memory/blocking extents
  for one schedule tile. They are not a promise that padding coordinates exist
  and they are not a static reservation of physical lane rows.
- At tile origin `(m0, n0, k0)`, active extents are
  `min(tile_rows, M-m0)`, `min(tile_cols, N-n0)`, and
  `min(tile_depth, K-k0)`. Only positive in-range coordinates are eligible.
- A tensor-view edge mask further removes coordinates. A removed coordinate
  issues no operand read, MAC, accumulator update, conversion, output write, or
  logical operation counter.
- `queue_index`, `issue_window`, `max_outstanding`, `bank_mask`, `port_mask`,
  `noc_route_class`, and `priority` retain their existing scheduling and
  resource meanings.
- `resource_bound` is not repurposed as an active-lane count or mask. Its unit
  is not frozen sufficiently to carry that meaning. Physical lanes come from
  the authenticated capability and must match the implementation identity.
- Folding never crosses an instruction, operator descriptor, event dependency,
  fault boundary, numeric profile, or ownership scope.

Admission rejects zero tile dimensions, incompatible views, an active extent
larger than the admitted bound, unsupported numeric profiles, and any mapping
whose address proof does not cover every eligible coordinate. Inactive tail
coordinates do not need a new descriptor field because the resolved views
already define them.

### 5.3 Deterministic row folding and tail handling

For one ready tensor instruction, the sequencer visits row blocks and column
blocks in increasing-origin order. For an active row block of size `r`, it
chooses `r_wave = min(r, 256)` and
`c_wave = min(columns_remaining, floor(256 / r_wave))`, with a minimum
`c_wave` of one. It enumerates the resulting rectangular set in stable
row-major order and assigns local coordinate `(i, j)` to lane
`i*c_wave+j`. Larger row or column regions become consecutive waves. A lane
owns its output's accumulator until the declared reduction is complete or
until an exact raw-FP32 spill and reload occurs.

This linear assignment is the row-folding mechanism:

- with 64 active rows, a full wave can cover four output columns per row;
- with one decode row, a full wave can cover up to 256 output columns for that
  row; and
- with any intermediate row or live-batch count, useful `(row, column)` pairs
  fill the wave and only the final remainder is masked.

When `tile_cols` is smaller than a wave, the front end may pack consecutive
column tiles from the same instruction and reduction interval only when the
declared issue window admits them and their views are independent. Tags retain
the original tile and output identities. This packing changes neither address
order within one operand stream nor arithmetic order within one output.

There is no multiplication by a padded row. A final wave with `r < 256` valid
outputs asserts valid on exactly `r` lanes; the other lanes are clock-gated and
counted as tail slots. Aligned HBM bursts may still fetch bytes surrounding a
useful tail, but those physical bytes are reported separately and never become
logical MAC work.

### 5.4 Reduction order, split-K, and conversions

For every output coordinate, the default lane walks K in the order required by
the numeric descriptor. A sequential-ascending contract processes increasing K
without reassociation. Depth tiling may change when data is loaded, but the FP32
accumulator remains live across consecutive depth tiles and the next depth tile
cannot update that output before the preceding one.

Split-K is **disabled by default**. It is illegal for
`SEQUENTIAL_ASCENDING`, and it is also illegal for any blocked or tree contract
that does not explicitly bind all of the following through its named contract
and digest:

- partition count and exact K boundaries;
- the arithmetic used to create each partial;
- the exact merge tree and left/right operand order;
- accumulator and intermediate dtypes;
- every scale-application point; and
- the final conversion and saturation point.

The present generic statement that an implementation uses a deterministic
blocked association is not, by itself, permission to invent split-K in RTL. A
future contract can authorize it through the existing numeric-contract and
capability mechanism; unsupported requests fail closed. Until then, idle lanes
remain idle when the number of independent output coordinates is smaller than
256.

Input widening, E8M0 or other scale application, products, FP32 additions,
exception handling, and final narrowing occur at the points fixed by the
numeric profile. Intermediate accumulator spills preserve raw FP32 bits and do
not narrow, saturate, normalize, or add. Exactly one final output conversion is
performed after the complete reduction unless the named contract explicitly
states otherwise.

### 5.5 SRAM, HBM, and accumulator residency

The lane improvement does not remove the decode weight-bandwidth problem. The
implementation must account for compute and memory independently.

For a dense contraction, the preferred dataflow is:

1. double-buffer an admitted weight block from HBM into banked SRAM;
2. load each active activation row/depth block once and multicast it to the
   lanes that consume it;
3. reuse each weight value across active rows and each activation value across
   active output columns;
4. retain up to one wave of FP32 accumulators in the lane fabric across all K
   blocks; and
5. write each final output once after its numeric conversion.

At batch-one decode, the activation row is broadcast while useful columns fill
the lanes. At larger batches or prefill, weights are reused across rows. Routed
expert weights and node shards obey the same rule within their admitted local
ownership; the engine must not fetch an unselected expert to make a regular
tile.

The implementation report must distinguish:

- useful logical operand bytes;
- aligned SRAM and HBM transaction bytes;
- refetch or replay bytes;
- accumulator spill and reload bytes;
- bank, port, queue, and HBM-channel stall cycles; and
- compute-active, masked-tail, dependency-bubble, and memory-starved lane slots.

An idealized claim that every useful weight byte is fetched once is not
accepted without the corresponding RTL transaction trace. SRAM and HBM macros,
controllers, PHY boundaries, and any assumed bandwidth remain named provenance
items in every performance report.

### 5.6 Batch behavior

Batching is a set of independent token sequences, not one concatenated prompt.
The initial characterization sweep is `B = 1, 2, 4, 8`, matching the current
advertised maximum of eight sessions. A target that cannot admit a point must
report it as unsupported; it may not extrapolate token count or TPOT.

Each sequence carries its own prompt length, generation cursor, live buffers,
selected tokens, and EOS state. Live sequence rows participate in row folding.
When one sequence commits EOS, EOS is included in its output count and that
sequence is removed from subsequent lane waves. No padding token is executed to
keep the batch rectangular, and a completed sequence performs no later model
step. The remaining sequences continue until their own EOS or cap.

For every batch point the evidence records, per sequence:

- exact prompt token count and prompt digest;
- complete generated token ID list and generated-token count;
- decoded text and tokenizer round-trip result;
- termination reason and EOS index, if any;
- exact-oracle comparison result; and
- request-start and token-commit ticks.

It also records total generated tokens as the sum of the per-sequence counts.
Aggregate tokens/s and per-sequence TPOT are different metrics and may not be
substituted for one another.

### 5.7 Thirty-two-node DeepSeek behavior

Every DeepSeek HBM node uses this same lane mapping and physical chip netlist.
Compiler sharding, explicit `LINK` descriptors, admitted collectives, fabric
credits, retries, routing, congestion, and completion events remain part of the
executed program. Row folding is local to a node and cannot erase communication
or treat remote operands as coherent local SRAM.

The coordinator's token-commit event occurs only after every required node-local
write, collective, selection dependency, and token-step fence has completed.
DeepSeek TPOT therefore includes the modeled NVLink-class fabric, link stalls,
and global synchronization. For the ROM target the analogous commit includes
the real on-wafer routes and barriers. Neither fabric may be replaced by a host
copy or zero-latency annotation.

## 6. Compiler and runtime obligations

The backend-neutral Model Graph IR and Tensor Kernel IR remain unchanged. The
HBM/SRAM backend must lower Qwen and DeepSeek operations into the existing ABI
3.0 opcodes and descriptors and must emit enough shape, numeric, storage, and
schedule information for the hardware to derive the mapping above.

The implementation work is complete only when all of these agree:

- the compiler's resolved operator extents;
- functional-simulator view resolution;
- cycle-model tile and memory accounting;
- RTL descriptor decode, address generation, and lane valids; and
- the independent checker reconstructed from serialized artifacts.

Compiler tests must cover static and symbolic extents around every physical
boundary: zero-invalid, 1, 2, 63, 64, 65, 127, 128, 129, 255, 256, and 257,
plus real Qwen and DeepSeek shapes. Generated schedules must remain legal for
prefill and decode. The compiler may tune blocking, issue windows, and banking
after RTL support exists, but a schedule-only reduction in charged work cannot
be promoted as a hardware speedup.

The runtime records the implementation-profile identity alongside source,
graph, Kernel IR, deployment, descriptor-table, capability, workload,
tokenizer, checkpoint, oracle, cost-table, process, and PVT digests. An old
token artifact cannot qualify a newly scheduled or newly synthesized datapath.

## 7. Simulation, RTL, and equivalence plan

### 7.1 Functional simulator

The functional simulator remains the fast end-to-end semantic implementation.
It must execute the resolved logical coordinates and numeric contracts without
depending on padded schedule work. A diagnostic lane-scheduling mode will
execute the deterministic waves, masks, accumulator residency, and permitted
spills described here, then compare every output bit and architectural counter
with the ordinary functional engine.

Functional equivalence is required for dense, grouped, and routed contractions;
BF16, FP8 E4M3FN, MXFP4 E2M1, and E8M0 scale cases; all relevant reduction
orders; edge masks; stalls and backpressure; invalid descriptors; and injected
non-finite or out-of-range values. Refusal behavior is part of equivalence.

### 7.2 Cycle model

The cycle model must stop charging inactive logical rows as completed MAC work
only after the implemented lane semantics are correlated. It will consume the
same executed trace and resolved views as the functional run and report both
logical work and physical issue behavior.

At minimum its tensor report contains:

- logical MACs and output elements;
- active lane-MAC slots;
- masked edge/tail slots;
- pipeline fill and drain slots;
- dependency, SRAM, HBM, and queue stall cycles;
- row-folded output count;
- split-K partial and merge counts, which must be zero initially;
- useful, transaction, refetch, and accumulator traffic bytes; and
- physical lane utilization with an explicit denominator and provenance.

The model may not derive physical utilization as useful work divided by the old
padded tile volume. Its parameters must identify whether each value is assumed,
RTL-characterized, post-layout-characterized, or measured. A result dependent
on assumed bandwidth or rate remains assumption-dependent.

### 7.3 RTL and co-simulation

RTL implementation proceeds from the lane through the integrated tensor engine
and then through the shipped ABI program path:

1. arithmetic lane and format/scale/conversion blocks;
2. 64-lane issue group with valid masking and accumulator tags;
3. four-group, 256-lane fold network and shared sequencer;
4. banked SRAM, DMA/HBM backpressure, queues, faults, and counters;
5. descriptor resolver and full tensor instruction completion;
6. selection, token append, token-step fence, and timestamp path; and
7. one-chip and exact 32-node integration.

Every stage is dual-simulator checked where the repository supports Icarus and
Verilator. Randomized ready/valid stalls, reset, edge extents, HBM burst tails,
SRAM conflicts, and error injection are mandatory. Assertions prove that a
masked lane cannot read, update an accumulator, write, or increment a logical
counter, and that instruction completion cannot precede all valid outputs.

Co-simulation must replay the exact serialized descriptors, memory images, and
numeric profiles. Per-operator bit equivalence and trace/counter equivalence are
intermediate gates.

Literal serial simulation of every MAC in the complete Qwen exact-8K and
DeepSeek exact-200K workloads is not a tractable primary production campaign.
The production-simulation tier is therefore **RTL-bound accelerated full-system
co-simulation**. In that tier, synthesizable RTL executes program control,
descriptor and view resolution, address generation, queues, SRAM/HBM
transactions, inter-chip or on-wafer fabric, events, fences, faults, selection,
token append, EOS, completion, and raw token-commit timing. A tensor, vector,
attention, route, or reduction engine may use an accelerated exact engine model
only when all of the following are true:

- the model consumes the same descriptor, resolved views, operands, valids,
  stalls, and backpressure as the synthesizable engine;
- every supported mode is bit-equivalence-bound to synthesizable RTL at its
  numeric boundary, including refusal and exception behavior;
- its start, transaction, stall, completion, and counter events are
  cycle-equivalence-bound to that RTL and the characterized implementation;
- its version and equivalence proof are digest-bound into the execution record;
- it cannot inspect oracle results or later model state; and
- replacing it with RTL at the handshake boundary changes neither result bits,
  architectural events, memory traffic, nor target cycles.

If any engine model lacks that proof, the run is downgraded to functional
execution or RTL control replay and is ineligible for production-simulation
TPOT. The host co-simulation harness may advance components and transport
handshakes; it may not calculate or inject a model result.

**Monolithic full-RTL execution** remains the strongest evidence tier: every
token-influencing engine and datapath executes in RTL. It is required for
bounded correlation campaigns and pursued for complete tokens where tractable,
but the exact-8K and exact-200K production-simulation workloads may close on the
explicitly labeled RTL-bound accelerated co-simulation tier. That tier must
never be reported as monolithic full RTL, post-layout simulation, silicon, or a
measurement of simulator wall time.

## 8. Gate C: end-to-end token correctness

Correctness is evaluated against independent model execution, not against a
second run of the same accelerator implementation. The checker reopens and
authenticates the serialized deployment and verifies all source bindings before
comparing output.

### 8.1 Mandatory workload coverage

The acceptance suite contains:

- the governed natural/chat prompt at exactly 8,000 tokens for Qwen;
- the governed natural/chat prompt at exactly 200,000 tokens for DeepSeek;
- the repository's simple reasoning chat template; and
- the repository's deterministic agentic template and simplistic tool
  environment, including exact tool-call/result serialization.

The exact-length natural workloads are mandatory release and performance
points. Reasoning and agentic cases are mandatory behavioral coverage and bind
their own prompt/template/tool-environment digests. A short prefix can diagnose
a defect but cannot substitute for any required horizon.

### 8.2 Required checks

For each target, batch size, and sequence, Gate C requires:

1. current source, checkpoint, tokenizer, graph, Kernel IR, deployment,
   capability, implementation, topology, and workload identities;
2. independent oracle completion through first official EOS or the exact cap;
3. accelerator completion through the same boundary;
4. element-for-element equality of the complete generated token-ID sequence;
5. every ID inside the tokenizer vocabulary and accepted special-token set;
6. tokenizer ID-to-text-to-ID checks under the governed policy;
7. human-readable input context, output token IDs, token pieces, and decoded
   output retained in the evidence package;
8. first official EOS included exactly once when reached, otherwise exactly
   256 generated tokens and an explicit cap termination;
9. an on-device terminal completion from `TOKEN_APPEND`: official EOS or the
   authenticated request's `MAX_NEW_TOKENS`, bounded by the immutable
   generation-policy ceiling;
10. no model transaction, live-buffer write, or token append after EOS or the
   generation cap; and
11. no host-supplied logits, token IDs, routes, activations, or hidden states.

Two independent source-current Qwen HBM captures remain required by the master
plan before promoting the long-run path. DeepSeek requires one complete
external oracle plus both target executions: exactly 32 HBM/SRAM nodes and one
ROM wafer. ROM/HBM equality does not replace the independent oracle.

Functional accelerator tokens close the functional tier only. The production
simulation tier closes when an explicitly labeled RTL-bound accelerated
full-system co-simulation produces the complete token sequence and satisfies the
same checker; monolithic full RTL remains the stronger tier. Any mismatch
blocks TPOT reporting for that execution and starts from the first divergent
operator, accumulator, logit, or token trace.

## 9. Gate P: correctness-qualified TPOT

### 9.1 Architectural timing boundary

Each target implements a monotonically increasing 64-bit cycle counter or an
equivalent non-lossy target timebase. It captures:

- `request_start_tick` when the accepted request becomes device-owned;
- prefill-complete/first-decode eligibility as a diagnostic event;
- `token_commit_tick[s][j]` when sequence `s` commits generated token `j`; and
- terminal completion after EOS or the generation cap.

A token commit is visible only after `TOKEN_APPEND`, all token-dependent live
buffer and communication writes, and the token-step fence have succeeded. A
selected token or pre-fence append is not a commit. DeepSeek uses the global
coordinator-visible commit described in Section 5.7.

The raw tick arrays are retained, not only percentiles. For one sequence:

- TTFT is the first token commit minus request start and includes prefill;
- decode interval `j` is commit `j` minus commit `j-1`;
- steady-state TPOT uses the comparison contract's frozen starting decode step;
  and
- EOS is an ordinary final committed token in the timing sequence.

For a batch, metrics include every per-sequence interval distribution, mean and
maximum per-sequence steady-state TPOT, aggregate steady-state generated
tokens/s, aggregate end-to-end tokens/s, and the complete output-token counts.
Aggregate throughput is never labeled per-sequence TPOT.

### 9.2 Evidence classes

The following remain distinct:

| Evidence | What it may establish | What it may not be called |
|---|---|---|
| Functional simulator host wall time | software runtime and campaign planning | target TPOT |
| Analytical/roofline result | bound or design projection | executed TPOT |
| ABI 3.0 cycle-model execution | correctness-bound modeled target cycles, with provenance | silicon measurement or production closure by itself |
| RTL simulator wall time | simulator throughput | accelerator TPOT |
| RTL-bound accelerated full-system co-simulation | production-simulation target cycles when every accelerated engine is bit/cycle-equivalence-bound | monolithic full RTL, post-layout simulation, or silicon measurement |
| RTL cycle trace plus characterized clock | target cycle behavior for the correlated RTL and stated PVT | silicon measurement |
| Post-layout timing simulation | implementation timing at its stated extracted view | another process/PVT or silicon result |
| Silicon counters | measured behavior of the named device | a different implementation or workload |

The existing correctness-qualified TPOT schemas and checker are the required
report boundary. The timing trace binds the exact correctness acceptance and
execution records by digest and declares `full_workload_execution=true`,
`token_commits_from_execution=true`, and `counterfactual_or_extrapolated=false`.
Before co-simulation evidence is promoted, that evidence schema and checker
must add an explicit `rtl_bound_accelerated_cosimulation` tier and its proof
bindings. A co-simulation record may not be encoded as
`full_rtl_generated_tokens`. This evidence-schema evolution does not change the
ABI 3.0 program, descriptor, or host wire format.

### 9.3 Freezing the desired TPOT

Before a pass/fail claim, the owner freezes a budget row for every claimed
combination of:

- Qwen exact-8K or DeepSeek exact-200K workload;
- HBM or ROM target role and exact topology;
- SKY130 or ASAP7 process view and PVT corner;
- batch size and concurrency;
- steady-state starting step;
- selected statistic (`max`, `p50`, `p95`, or `p99`); and
- eligible evidence class and whether any assumed value is allowed.

The budget metric is per-sequence steady-state decode-step latency. The
10,000-token/s north star is shown alongside the frozen budget but does not
silently populate it. A comparison with a missing budget remains
`not_evaluable`; a measured number alone is not a passed requirement.

## 10. SKY130 and ASAP7 physical closure

The 256-lane shared datapath, fold network, accumulator storage, descriptor
front end, SRAM interfaces, queues, DMA boundary, and token-commit counter must
be synthesized and placed/routed as an integrated timing path for both
technology views.

For each view the evidence package includes:

- tool, PDK/library, SRAM macro/model, HBM controller/PHY boundary, constraints,
  and source digests;
- die/block floorplan, utilization, standard-cell and macro area, congestion,
  and routing completion;
- setup/hold results and achieved frequency at all frozen PVT corners;
- clock, leakage, dynamic power, and activity provenance for prefill and decode;
- lane-mask, fold-network, accumulator, SRAM, and HBM critical paths;
- per-engine area/power and the incremental fold/mask overhead;
- executed RTL traffic and stall traces used to calibrate the cycle model; and
- reproducible logs, reports, netlist digest, and cost-table derivation.

SKY130 is the mature open 130 nm implementation view. ASAP7 is an academic 7 nm
predictive view and must remain labeled as such. Neither may inherit frequency,
SRAM density, HBM bandwidth, voltage, or energy from the other. A ROM/HBM pair
is comparable only when both reports use the same selected process view, PVT,
package/memory boundary policy, workload, and evidence grade.

An SRAM or HBM interface represented by an assumption is not concealed by a
routed logic block. Reports identify assumed, characterized, and measured
parameters independently. Full production TPOT requires the eligible evidence
class and assumption policy frozen in its SLO row.

## 11. Ordered implementation and evidence plan

This is an ordered delivery plan rather than an unordered task list. Work may
run in parallel only where the inputs and output ownership are disjoint.

### Phase 0 — freeze identities and budgets

The integration owner selects one source-current commit; rebuilds and binds the
checkpoint, tokenizer, prompts, graph, Kernel IR, deployments, capability, and
oracle identities; and freezes output roots for long campaigns. The owner also
freezes the batch matrix and numeric TPOT SLO rows. No long result from a prior
identity is promoted.

`tools/freeze_abi3_execution_release.py` is the create-once boundary for this
phase. It records the clean committed Git tree and complete tracked-file map,
requires every included comparison contract to be source-ready with locked
oracle, IR, deployment, capability, topology, cost/PVT, clock, and explicit
TPOT budget identities, binds the checkpoint/source locks, and reserves one
result namespace. `verify` must pass in the execution worktree before a
production child starts. This record is evidence plumbing outside the ABI 3.0
wire format: it creates no model state, journal, retry, checkpoint, or rollback
mechanism.

Exit evidence is an authenticated comparison/workload manifest and a complete
SLO table. Correctness execution may begin before the numeric SLO is chosen,
but performance cannot receive a pass/fail verdict without it.

### Phase 1 — close source-current functional Gate C

Run Qwen HBM capture A alone, inspect resource headroom, then run independent
capture B. Run the Qwen ROM exact-length case and the reasoning/agentic suite at
the same source identity. Execute the complete DeepSeek external oracle, then
the exact 32-node HBM/SRAM and one-wafer ROM functional simulations. High-memory
campaigns remain serialized on the current host.

Every run retains complete token IDs and text. Any divergence is localized and
fixed before it is used as a timing qualification. Exit is source-current
functional correctness for the four targets; a partial prefix is not exit.

### Phase 2 — implement and prove the lane contract

Implement resolved active extents, deterministic row folding, valid/tail masks,
K-ordered accumulator residency, physical counters, and exact memory
transactions in the compiler-facing model, functional diagnostic mode, cycle
model, and tensor RTL. Split-K stays disabled. Differential and formal checks
cover the boundary shapes and formats in Sections 6 and 7.

Exit is bit-exact functional/RTL equivalence for all tensor modes, identical
architectural counters, proven inactive-lane safety, and a cycle report whose
physical utilization is derived from implemented lane events rather than
inferred from schedule padding.

### Phase 3 — integrate through token commit

Extend the shipped ABI 3.0 RTL path through every Qwen and DeepSeek instruction,
including vector, attention, route, reduction, link, selection, token append,
EOS, and the token-step fence. Integrate the raw 64-bit token-commit cycle trace
without changing arithmetic or completion semantics.

Exit is a complete generated token from each topology, followed by the full
mandatory EOS-or-256 workload at the RTL-bound accelerated full-system
co-simulation tier. Bounded monolithic RTL campaigns replace each accelerated
engine at the same handshake boundary and prove the claimed bit/cycle binding;
complete monolithic full-RTL tokens are retained as the strongest evidence when
tractable. Host-computed substitutions, skipped engines, oracle injection, and
structural artifact replay do not qualify.

### Phase 4 — characterize both technology views

Synthesize and place/route the integrated datapath and relevant system blocks
on SKY130 and ASAP7, run extracted timing/activity campaigns, derive versioned
cost tables, and correlate block cycles and transactions back to RTL. Perform
the same-view ROM work under the existing target-specific plans.

Exit is reproducible timing, area, power, memory-boundary, and correlation
evidence with no unexplained counter or cycle delta.

### Phase 5 — execute the batch and TPOT matrix

For each supported `B = 1, 2, 4, 8` point, run the exact correctness workload,
validate every sequence first, then consume the bound raw target timing trace.
Publish token counts, token IDs/text, EOS/cap outcome, TTFT, every decode
interval, steady-state distribution, per-sequence TPOT, aggregate tokens/s,
lane utilization, memory traffic, communication stalls, and provenance.

Exit is a checker-produced correctness-qualified report for every claimed
point. A point passes only its explicitly frozen SLO. Unsupported, failed,
uncharacterized, assumption-disallowed, or budget-missing points remain typed
as such.

### Phase 6 — decide whether the fallback is needed

Review end-to-end critical-path evidence. Keep the shared datapath unless the
fold/mask implementation itself prevents a frozen SLO from being met. If that
condition is demonstrated, perform a bounded narrow-engine PPA study under the
same memory system, process, PVT, area/power budget, program, and correctness
checker. A fallback architecture requires a new focused ADR; it is not enabled
by a compiler heuristic.

## 12. Required production evidence matrix

| Evidence item | Functional tier | RTL-bound accelerated co-simulation tier | Monolithic full-RTL tier |
|---|---|---|---|
| Source/checkpoint/tokenizer/workload/deployment/capability digests | required | same identities required | same identities required |
| Independent complete oracle | required | required | required |
| Complete accelerator token IDs and decoded text | required | co-simulation-generated sequence required | RTL-generated sequence required |
| Legal IDs, exact equality, EOS/cap, no post-EOS work | required | required | required |
| Descriptor/view/numeric/schedule checks | required | RTL consumes serialized artifact | RTL consumes serialized artifact |
| Tensor lane mapping and inactive-lane safety | diagnostic model | RTL assertions plus model equivalence binding | direct RTL assertions and trace |
| Full model execution | all functional engines | RTL system plus only qualified exact engine models | all token-influencing RTL engines |
| Raw request/token-commit ticks | optional diagnostic | required from RTL control and digest-bound | required and digest-bound |
| Target frequency | not applicable | same-process characterized value required | same-process characterized value required |
| TPOT result | ineligible host time | only from correctness-bound target ticks | only from correctness-bound target ticks |
| SLO verdict | not evaluable | pass/fail only with frozen budget and eligible evidence | pass/fail only with frozen budget and eligible evidence |

The minimum artifact set for one promoted point contains the comparison
contract, workload manifest, source manifest, graph and Kernel IR identities,
deployment bundle, capability, implementation identity, independent oracle
record, accelerator execution record, correctness acceptance, raw timing trace,
physical/cost-table provenance, and correctness-qualified TPOT report. All
cross-references are content digests, not filenames alone.

## 13. Failure policy and rollback

The implementation fails closed on an unsupported schedule, numeric contract,
split-K request, extent, mask, address, format, scale, accumulator overflow,
memory response, link completion, or counter/timing inconsistency. A failed run
produces no correctness or TPOT claim.

If row folding changes a token or arithmetic result, disable the folding path
and debug the first divergent operator; do not update the oracle. If the cycle
model predicts a gain that RTL does not reproduce, retain the RTL result and
mark the model uncorrelated. If post-layout frequency or bandwidth invalidates
the SLO, publish the failed point with provenance and evaluate architecture or
memory changes under a new decision. Historical evidence remains labeled with
its original source and implementation identities.

## 14. Acceptance checklist

This ADR is implemented only when all of the following are true:

- one physical HBM/SRAM tensor datapath dynamically runs both models;
- resolved ABI 3.0 extents, edge masks, lane valids, and addresses agree in
  compiler, functional simulator, cycle model, checker, and RTL;
- row folding is present in integrated RTL and no padded logical row performs
  work;
- reduction association and conversion points are unchanged; split-K is absent
  unless a future explicit numeric contract authorizes it;
- SRAM/HBM traffic, accumulator residency, stalls, and physical lane slots are
  observable and correlated;
- Qwen exact-8K and DeepSeek exact-200K natural workloads complete through EOS
  or 256 with exact independent-oracle agreement on every required target;
- reasoning chat and deterministic agentic contexts produce legitimate,
  oracle-matched behavior;
- batch points report complete per-sequence output-token counts and correctness;
- RTL-bound accelerated full-system co-simulation reaches token append and EOS
  without host-computed or oracle-injected model results, and every accelerated
  engine is bit/cycle-equivalence-bound to synthesizable RTL;
- bounded monolithic RTL campaigns close each accelerated-engine handshake and
  complete monolithic RTL remains distinctly labeled as the strongest tier;
- raw token-commit cycles are bound to those correct executions;
- SKY130 and ASAP7 physical evidence is reproducible and honestly separates
  assumed from characterized components; and
- each claimed performance point is evaluated against a frozen, target-specific
  TPOT SLO, with the 100-microsecond north star kept explicitly aspirational.

Until that checklist is complete, the accurate program status is: **token
correctness open, production TPOT open, and no performance number qualified for
release**.
