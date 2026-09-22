# Runtime operand delivery and tiled execution

Architecture decision, 2026-09-22. Selected direction for implementation;
integration and performance acceptance remain open. Supersedes the suggestion
that opposite-bank write arbitration alone would solve G2's delivery problem.

## Problem established from source and workload geometry

The current G2 cluster is a preloaded contraction vehicle. Global `!busy` gates
all host writes; LQ8 consumes a one-cycle operand interface without backpressure;
the two weight macros provide a 1024-word linear window; one command remains
outstanding. The workload's complete contractions exceed this window, and even
one eight-output Qwen projection group at K=4096 exceeds it. Its activation row
also exceeds the 2 KiB activation window. A faster clock cannot fix these bounds.

`results/architecture/qwen_tensor_staging_demand.json` derives geometry from the
current IR: zero of 253 complete contractions fit. The 4096x4096 projection needs
2,097,152 128-bit stream words for one input row, compared with 1024 available.
This is a direct whole-operator feasibility check, not an assertion that the
compiler's tiled schedule allocates a 32 MiB on-chip buffer.

## Selected organization

Use coarse operations feeding a local tile scheduler, separate runtime operand
service, banked scratchpads, and a numerically specified pipelined tensor core.
Keep the program loader idle-only. The runtime service has its own request,
credit and completion interface, so loading a next operand tile does not require
stopping the command processor or changing executable state.

Decode maps a row over independent output columns and broadcasts activation
values. Prefill reuses each resident weight tile across multiple input rows,
with a bounded set of independent accumulators. The local scheduler chooses the
row tile to fit accumulators and activation banks; row reuse is not obtained by
pretending external bandwidth increases. All formats carry their scale planes
and metadata in the service budget.

The first implementation retains the existing two weight SRAM banks and adds
independent per-bank address selection. This preserves a measurable baseline
and avoids selecting a larger memory before demand is established. Activation
and scale windows require corresponding tiled addressing and ownership; weight
overlap by itself is not the acceptance criterion.

## Required command and numeric identities

Capture a complete immutable operation record at admission: operation/slot ID,
generation, dimensions and strides, operand objects and resolved offsets,
formats, scale geometry, output mode, numeric contract and association ID.
Completion is tied to that record, after final write acknowledgement, rather
than to live global configuration wires or a transient resolved-view stream.

Sequential mode retains ascending-K FP32 rounding; interleave independent
outputs to hide recurrence without reassociation. Blocked mode declares an
explicit deterministic binary32 association and is qualified as that hardware
implementation. The Qwen functional backend's BLAS result is not automatically
the hardware result. Preserve separate implementation identities and qualify
model correctness before publishing a token-performance comparison.

For sequential mode, K slicing carries the existing binary32 accumulator across
chunks without resetting or rounding through BF16. For blocked mode, choose and
freeze the association boundaries independently of refill timing. Memory stalls
must not change reduction association, outputs, exceptions or completion order.

## Bank ownership protocol

Each bank transitions through `FREE -> FILLING -> READY -> ACTIVE`.

- Reservation binds a bank to a tile ID, generation, expected word count and
  operand/scale identity. A non-free bank cannot be overwritten.
- Data beats are accepted only for the reserved identity, in a declared order,
  with an exact accepted-word count. Backpressure never advances that count.
- Publish READY only after the last accepted write is visible to the read port
  and all required operand planes are complete. Reject incomplete or duplicate
  publication. Reservation is not completion.
- Acquire validates the expected identity and bounds before any compute read.
  Multiple row consumers retain residency until their last use; completion of
  one row is not a licence to overwrite weights needed by another row.
- Release follows the final outstanding read response. It returns to READY
  when reuse remains, otherwise FREE. Release and new reserve on the same edge
  are initially serialized, simplifying unambiguous ownership.
- Reset invalidates all banks and in-flight operations. Abort drains or kills
  all compute/read tokens of its generation before making its banks reusable.
  A delayed refill response for the old generation is refused.

Read and write may proceed on different single-port macros. Same-bank conflicts
are prevented by ownership, with read priority and a counted refusal as a final
guard. Independent banks require independent addresses; changing write enables
while retaining a shared read-selected address would corrupt the fill.

## Streaming and accumulator lifetime

At each tile boundary the scheduler waits for the complete required operand
bundle. Within a tile, consume only when the next data and destination capacity
are available. Issue stalls insert bubbles while already-issued arithmetic and
read responses drain; they must not freeze only half a pipeline or drop tokens.
The issue cursor and weight pointer advance on consumption, not wall-clock time.

The current lane starts a new accumulator chain at each operation. Restarting
it on a smaller K chunk therefore does not implement a full contraction. Add an
explicit first/continue/final contract with resident accumulator ownership, or
keep a single operation live across refill pauses. The first implementation
should keep the operation live and pause issue at tile boundaries to minimize
new accumulator load/store paths. Test equivalence against uninterrupted issue.

Output commits only after the final K chunk. Preserve fault behavior and output
atomicity required by each operation; do not release an operation slot while
write acknowledgements remain outstanding. Size result buffering against actual
consumer bandwidth and propagate backpressure into admission.

## Scheduling and performance acceptance

Coarse descriptors expand into local tile loops. Keep dependency checking at
the operation boundary and explicitly track pending preparation, active compute,
and completion. A queue can overlap preparation/refill with compute; it does
not allow a single tensor core to execute two operations simultaneously.

Compare the current preload/execute path with the new path using identical
weights, activations, numeric contract, SRAM capacities and service bandwidth.
Exercise at least two consecutive tiles and multiple rows, skewed refill,
producer backpressure, activation/scale starvation, output backpressure and
fault/reset during each bank state. Check every result and completion identity.

Measure total latency, first/final result, useful issued work, issue stalls by
cause, external and SRAM bytes, bank occupancy and commands per operation.
Report startup and drain as well as steady state. An ideal overlap upper bound
is `(Tfill + Tcompute) / max(Tfill, Tcompute)` only when the resources are truly
independent. No such speedup is credited before the integrated test demonstrates
it with bounded storage.

## Implementation order

1. Implement and verify the bank ownership protocol with real staged writes and
   one-cycle reads, independent bank addressing and stale-response rejection.
2. Add a separate runtime refill port to the cluster, keeping idle-only program
   loading intact; connect operation identity and operand readiness to admission.
3. Add issue backpressure and tiled address translation with accumulator
   continuity. Verify uninterrupted versus arbitrarily stalled execution.
4. Add local row/column/K scheduling and measured prefill weight reuse; complete
   the blocked numerical implementation/qualification before claiming Qwen RTL
   execution. Integrate vector/reduction/output service at matching capacity.
5. Calibrate cycle predictions on this integrated path, expand to other supported
   model/capability families, then optimize and route every selected component
   for the architecture's high-frequency target.

This architecture addresses delivery, storage feasibility, reuse and control
granularity together. It does not resolve all attention, routing, distributed
transport or whole-chip coverage work; those remain in the broader plan.

## Implementation checkpoint

`rtl/abi3/ot_a3_operand_bank_owner.sv` implements the first ownership controller:
two banks, tagged reservation, bounded sequential fill credits, publication on
the final accepted write, acquire, retain/final release and cancellation.
Cancellation wins over a simultaneous fill or acquire; active banks cannot be
cancelled or overwritten. Ready signals are revoked during reset. Tags must
include scheduler generations and must not be reused while stale responses can
arrive. The scheduler is responsible for draining read responses before release.

The directed Icarus bench and `tests/test_operand_bank_owner.py` pass, covering
opposite-bank ownership/fill, incomplete acquisition refusal, stale tags,
retained reuse, cancellation conflicts, zero/oversize lengths, a full 512-word
fill, final release and reset. Verilator RTL lint passes. These checks establish
controller behavior only: SRAM write/read integration, arbitrary stalls, cluster
admission, fault draining and workload overlap measurements remain open.

The next checkpoint connects ownership to SRAM in
`rtl/abi3/ot_a3_runtime_weight_banks.sv`: two independently addressed
`fakeram_512x128` instances, tagged bounded reads, sequential tagged fill, and a
one-response read interface. Response data and identity hold under consumer
backpressure. Release is withheld while a response from that bank is outstanding
or a new read is accepted. This conservatively inserts a release edge after
response drain; it never frees a bank merely because its request was issued.

Both Icarus and pinned Verilator 5.050 pass the memory-service bench. It checks
four simultaneous opposite-bank reads/writes at deliberately different
addresses, full 512-word fill and reverse readback, a held response throughout
opposite-bank refill, stale/out-of-range read refusal, active overwrite refusal
and reset. Verilator lint also passes against the actual synthesis blackbox
declarations. Source-bound evidence is in
`results/rtl/a3_runtime_weight_banks.json`. Functional simulation uses the
documented one-cycle single-port memory behavior, not transistor SRAM simulation.

This memory service is not yet wired to G2. The next change must define the
complete operand readiness handshake at cluster admission and lane issue,
including activation/scale readiness. Do not bypass the cluster's global loader
gate and call it overlap, or wire variable-latency responses into LQ8's existing
fixed-latency interface without controlling issue and response alignment.

## Operand issue reservation

The lane and LQ8 now expose an opt-in `OPERAND_CREDITS` parameter and shared
`operand_credit` input. Default configurations retain unrestricted issue.
Enabled configurations reserve a complete operand bundle before creating the
registered memory request. When credit is absent, no new lane token is created;
the cursor holds while existing tokens, slot timers, faults and writeback drain.
All LQ8 lanes share the credit, preserving their operand-stream lockstep.

This is a reservation interface, **not a variable-latency read-response port**.
The service granting credit must guarantee every operand plane at the existing
registered-read timing. Credit withdrawal cannot cancel an already-issued read.
The integration needs a prefetched bundle buffer or an equivalent guaranteed
service reservation. Connecting the SRAM response-ready signal directly would
violate that contract.

`tests/test_lane_operand_credits.py` generates the existing numerical/fault
corpora and inserts initial starvation, periodic gaps and pseudorandom credit
bubbles, checking expected outputs and the sequential reference. It also asserts
that no read is issued without a prior credit. The LQ8 counterpart is
`tools/check_lq8_operand_credits.py`, using the existing array checker and reference
lanes with shared pauses. The stalled array passed the Verilator run with 92
cases, 17,103 matching outputs, 18 fault cases and 115,748 checks. These results
do not establish integrated refill performance or hardware clock closure.

The Verilator result is retained in
`results/rtl/a3_lq8_operand_credits.json`. All four single-lane Icarus
parameter/corpus cases passed. The array Icarus retry also passed: 92 cases,
17,103 matching outputs, 18 fault cases and 115,748 checks, recorded in
`build/runtime_credit_array/simulation.log`. Its executable predates the lane
address-preview edits; this is evidence for the credit-stall snapshot, not a
fresh validation of the current lane source. The original 180-second array run
terminated at its timeout; the successful retry used a 600-second limit.

## Variable-latency bundle checkpoint

The lane now exports its next operand addresses and combinational request/issue
signals. Address previews describe the current issue cursor and remain stable
while issue is starved; registered read ports use those same expressions.
`ot_a3_operand_bundle_bridge` captures a preview, waits for a complete bundle,
grants credit, and delivers the consumed bundle one edge after issue, matching
the original registered memory request timing. Existing pipeline tokens drain
normally during request or response stalls.

The bridge is deliberately a one-outstanding-fetch correctness baseline. It
does not claim one bundle/cycle. Clear/reset revokes local requests and delivery;
its upstream service must flush outstanding responses at the same boundary.
The planned tagged prefetch integration must enforce that contract rather than
attach an old response to a new request. A complete service supplies activation,
weight, activation-scale and weight-scale together; missing any plane withholds
credit.

`tools/check_lane_operand_bundle.py` runs the existing quick numerical/fault
corpora through 1–8-cycle delayed behavioral service with request stalls and
checks the original expected images. Verilator passed both corpora: 42 grouped
cases (1,302 checks) and 57 D1 cases (56,992 checks, including sequential-reference
comparisons). `results/rtl/a3_lane_operand_bundle.json` binds sources, generated
benches, manifests and logs. A separate Icarus unit test checks request stability,
held reservations, exact delivery edge, clear and reset; all nine bundle,
ownership and staging-demand tests passed.

Remaining architecture work: decouple future operand request generation from
arithmetic issue with bounded prefetch queueing; attach banked SRAM service and
all operand planes; propagate operation identity and fault flushes through
cluster admission; measure integrated reuse and overlap. This checkpoint proves
that delayed operand service can preserve the existing lane contracts, not
that the single-entry adapter is a high-throughput accelerator implementation.


## Decoupled SRAM tile prefetch checkpoint

`rtl/abi3/ot_a3_weight_tile_prefetch.sv` independently walks a resident tile and
copies SRAM responses into a bounded FIFO. Each outstanding read reserves one
slot before admission. Entries carry the word, tile tag, index and last marker.
A bank is released after its final response is copied; queued copies remain
valid after that bank is overwritten. Retained release makes the same tile
available for another row without refilling it. Acquisition validates the exact
resident extent, refusing both shorter and longer tile requests.

The read admission path does not depend combinationally on downstream ready.
This costs a conservative bubble after a full queue. At depths 3, 4 and 8 the
Icarus bench delivered 32 consecutive words, exercised simultaneous refill and
consumption, and checked all 76 consumed words. Coverage includes a non-power-of-
two FIFO, held output stability, overwrite with old entries queued, retained
replay without refill, and reset while an SRAM read is outstanding followed by
fresh-generation execution. Verilator checks the depth-4 configuration.
Source-bound results are in `results/rtl/a3_weight_tile_prefetch.json`.

This is a weight service with one acquired tile at a time. The observed
one-word-per-cycle burst is a simulation service rate, not a routed frequency,
whole-operation speedup, or integrated compute utilization. Activation and scale
availability, future complete-bundle scheduling, LQ8/cluster wiring and fault
flush remain required. The current lane preview alone cannot drive speculative
prefetch: it exposes only the next issue. The next integration must supply an
independent future cursor and join every required plane before granting credit.

## LQ8 plus SRAM runtime integration checkpoint

The next checkpoint now connects the SRAM prefetch service to the actual LQ8
arithmetic, through `rtl/abi3/ot_a3_lq8_operand_join.sv`. LQ8 exports current
activation, scale and sequential weight previews selected from the lowest
requesting lane, including when earlier lanes have faulted. The stream preview
accounts for the registered read port's pending pointer increment. The checker
compares each issued preview with the following registered read request.

The join requires both a tagged weight word and a complete activation/scale
response. It checks operation generation and all enabled-plane addresses before
granting credit. Neither producer advances until arithmetic issues. Two data
register stages reproduce the lane's registered-request/synchronous-memory
alignment and support consecutive-cycle bundles. Reset/clear flush pending
local delivery; the containing operation must flush both producers and compute
at the same boundary. Identity mismatch is exposed for the caller to handle;
production fault handling must not leave it as an unexplained permanent stall.

`tools/check_lq8_runtime_operands.py` generates an integration top around the
existing LQ8 corpus/checker. The two physical-sized behavioral SRAM macros are
filled in 32-word tiles, with a four-word weight FIFO and periodic fill stalls.
Contractions remain live across all tile boundaries; there is no chunk restart
or intermediate accumulator conversion. Activation and scale responses come
from the test's external image arrays through a one-outstanding variable-delay
producer, with the same address-dependent latency in comparison runs. This
producer models complete-plane availability; it is not bounded on-chip
activation/scale storage or a final high-throughput future-address scheduler.

Pinned Verilator passed both overlapped and serialized-refill modes: 92 cases,
17,103 matching outputs, 18 fault cases and 115,748 checks, including the
independent per-lane reference executions. Each mode issued 48,794 bundles and
acquired 1,562 tiles. The serial control permits the next tile's fill only after
the current tile's final issue; overlap permits filling a free bank earlier.
Both use the same source snapshot, capacities, images and producer rules.

`tools/compare_lq8_runtime_operands.py` verifies source/artifact hashes, equal
images and numerical verdicts, and equal per-case issued work before recording
`results/rtl/a3_lq8_runtime_operands.json`:

| Metric | Serialized refill | Overlapped refill |
|---|---:|---:|
| Aggregate operation cycles, all 92 cases | 378,517 | 326,833 |
| Accepted external weight words | 48,956 | 49,044 |
| Cycles with both accepted fill and arithmetic issue | 0 | 6,127 |

That is 1.1581x speedup, or 13.65% lower aggregate latency, for this specific
corpus/service configuration. Speculative filling costs 88 additional words
across its fault-containing cases. The remaining auxiliary request serialization
limits issue rate; this result is not the final architectural throughput, Qwen
end-to-end speedup, or routed clock closure. The new join alone contains 576 data
register bits at eight lanes; the four-entry weight FIFO holds 812 data/identity
bits, in addition to control. Final area accounting must include these buffers
and the real auxiliary storage/service.

The join's focused Icarus test covers stale generations, weight and enabled-scale
address mismatch, partial readiness, disabled scales, no consumption before
issue, consecutive-cycle delivery, and clear with a delivery pending. All 13
focused join/prefetch/ownership/bundle/staging tests pass; standalone join
Verilator lint is clean. The full new integration corpus has Verilator evidence,
not a second-simulator claim.

Next required integration work is bounded activation and scale delivery with an
independent future cursor, a synthesizable local tile scheduler, immutable
operation admission and coordinated fault flush in G2, then retained multi-row
reuse. The testbench scheduler is deliberately identified as testbench logic;
G2 still has its original loader gate and staging connections. Keep physical
component tuning deferred until the selected runtime architecture is integrated
and its complete service budget is established.

## Independent auxiliary prefetch and capacity selection

`ot_a3_lq8_operand_cursor` now generates future activation and scale addresses
independently of arithmetic issue. It captures admitted geometry, traverses
row/pass/K/column order with counters and additions, and advances only when a
service request reserves a slot. Scale strides and groups-per-scale come from
admission; there is no division in its per-word datapath. The integration bench
still calculates that admitted geometry behaviorally and starts the cursor only
after LQ8 first requests operands, avoiding speculation for refused shapes.
Production admission must supply and capture the same validated geometry.

`ot_a3_lq8_auxiliary_prefetch` stores both identity and complete response data in
a bounded ring. Requests reserve capacity before entering the external service;
separate request, response and consumption pointers permit queued and in-flight
work simultaneously. Responses must be in order and echo generation plus stream
address. Unexpected, stale or misordered responses are refused and surfaced.
Reset/clear revokes local reservations, and the external producer must cancel or
drain that generation. It remains the containing scheduler's responsibility to
handle mismatches and cancellation without deadlock.

Each entry holds 160 identity bits and 160 activation/scale data bits at eight
lanes. This is finite response staging, not a reusable activation scratchpad.
The external backing arrays and one-outstanding variable-delay service are still
behavioral; full SRAM-backed activation reuse and the G2 runtime port remain
open. The implementation supports multiple outstanding ordered responses, but
the integrated backing model does not yet exploit that capability.

Matched Verilator corpus results, with identical backing-service rules:

| Auxiliary organization | Operation cycles | Queue entry storage |
|---|---:|---:|
| Current-issue producer | 326,833 | No prefetch ring |
| Independent cursor, eight entries | 320,212 | 2,560 bits |
| Independent cursor, two entries | 320,692 | 640 bits |

Two entries are the selected default for this one-outstanding service budget:
75% fewer ring storage bits than eight entries at a 0.15% aggregate latency cost.
The selected implementation improves aggregate latency by 1.88% relative to the
current-issue producer. These storage figures exclude cursor/control registers,
external storage, the existing weight FIFO and final operand delivery registers;
they are not a mapped whole-design area reduction.

All modes pass the same 92 cases, 17,103 output identities and 115,748 checks.
Faster speculative issue can send extra bundles before fault detection; the
comparison requires equal issued work in nonfault cases and records the fault
case differences rather than equating speculative work with useful arithmetic.
Source-bound results are in `a3_lq8_future_auxiliary.json`,
`a3_lq8_auxiliary_capacity.json`, and `a3_lq8_selected_auxiliary.json` under
`results/rtl/`. The earlier refill-only artifact remains historical evidence for
its recorded tool/source snapshot after this checker extension.

Focused tests compare cursor addresses against direct tensor indexing at
interleave widths 1, 3 and 5, including partial column passes, row/scale wraps,
configuration capture, arbitrary request stalls and abort. Queue tests exercise
depths 1, 2, 3 and 8, full capacity, independent response/consumer stalls,
non-power-of-two wrap, generation refusal, clear with outstanding requests and
fresh-generation restart. Both new RTL modules pass standalone Verilator lint.
The selected path still requires a production tile scheduler, bounded reusable
activation/scale memories, G2 operation lifetime and fault integration, and then
physical characterization before frequency or final area claims.

## Captured RTL geometry admission

`ot_a3_lq8_operand_admission` replaces the future cursor test's combinational
geometry divisions with captured RTL state. The command handshake captures
operation generation, dimensions, grouping, scale geometry and all four bases.
Two restoring dividers share a shifted numerator and compute depth/block in
16 steps. A seventeenth edge publishes either a validated geometry record or
an error; the record is held until accepted. External configuration changes
after the handshake cannot alter that calculation or its result.

The record checks nonzero dimensions, lane-aligned columns, groups 1/2/4 and
scale-block divisibility. It is a geometry validator, not the full format or
numeric admission policy. Integration still waits for LQ8's successful first
operand request before launching the cursor. The existing lane admission and
G2 command lifetime have not yet been consolidated into this block; duplicate
admission logic must be included in area accounting until that work is done.
Reset/clear cancels a partial division or unconsumed record.

The directed/random Icarus test covers 91 records, mutates every configuration
input immediately after acceptance, stalls record consumption, and checks
cancellation during division. It includes the maximum 16-bit depth and invalid
scale geometry. Standalone Verilator lint is clean.

This review found a pre-existing grouped-depth overflow in the compute lane:
K=65535, g=2 rounded to zero words because K+1 was evaluated in 16 bits.
`ot_a3_lane_pipelined` now preserves the carry before shifting. A regression
failed on the original implementation with `got words=0 expected=32768` and now
passes all 15 combinations of K=65531..65535 and groups 1,2,4. This test verifies
admitted iteration geometry, not full-length arithmetic at each boundary.
The source-bound integrated admission run is retained separately in
`results/rtl/a3_lq8_operand_admission.json`; earlier comparison records remain
historical snapshots rather than being rebound to changed lane sources.

## Synthesizable weight-tile scheduling

`ot_a3_weight_tile_scheduler` captures generation, stream base and word count,
then independently walks refill and acquisition across alternating banks. It
reserves SRAM before issuing an external burst. Responses must echo the tile
tag and sequential beat index; only an accepted matching write advances refill.
The last tile uses its remaining word count. Bank ownership supplies reservation
and acquisition backpressure; the scheduler does not bypass it. Zero lengths
and address ranges that wrap beyond the 32-bit word space are rejected.

Its `scheduled` pulse means all words have been filled and tiles acquired, not
that compute has completed or the last bank is free. The containing operation
must hold its generation and manage final reads, compute/writeback completion
and fault cancellation. Clear revokes local requests; banks and external
transport must cancel/drain that operation together. Misordered/stale responses
are refused and reported for the containing fault controller.

The runtime corpus can select this controller with `--rtl-weight-scheduler`.
Only the external burst producer remains behavioral for the weight path; it
inserts request and beat stalls. The complete stream word count is still formed
by testbench geometry arithmetic and must move into checked production
admission. The scheduler currently supports overlapped streaming without
multi-row retained reuse. G2 integration remains open.

Icarus directed tests cover 1,031-word streams with tile sizes 1, 32 and 512,
including a short final tile, alternating bank identities, independent stalls,
configuration mutation after admission, stale tags, wrong indices, zero/overflow
rejection and clear. Standalone Verilator lint is clean. Current integrated
results are recorded in `results/rtl/a3_lq8_weight_scheduler.json` for the verified source snapshot. All 92 cases passed with 17,103 matching
outputs, 18 fault cases and 115,748 checks. Aggregate operation latency was
320824 cycles with external burst request/beat stalls. This is functional
RTL evidence, not routed timing. All 25 focused regression tests passed.


## Checked stream extent admission

Admission now produces `stream_words` from captured rows, lane-local columns
and grouped depth. A 32-bit rows-by-columns product and a 48-bit product with
depth are separated by register edges. The full extent is checked for zero and
32-bit count overflow, and the base-plus-extent sum is checked against the
exclusive 2^32 word-address limit before publishing a valid geometry record.
The highest word address may be used; crossing it is rejected. Record latency
is now 19 edges after acceptance (16 divider steps, two product steps, publish).

The integrated RTL scheduler takes generation, base and count from this record,
after LQ8 also requests operands. Its selected generated top no longer calculates
`stream_end` behaviorally or starts weight fetches before geometry validation.
The full 92-case run passes 17,103 matching outputs and 115,748 checks in
322,385 aggregate operation cycles, with the extra admission startup included.
This is not an additional performance improvement claim; it replaces unchecked
testbench arithmetic and establishes an implementable operation boundary.

All 25 focused tests pass. Admission covers 95 records, including wide products,
word-count overflow, an exact exclusive-end boundary, crossing that boundary,
input mutation, stalled record consumption and abort. Standalone admission lint
is clean. Source-bound evidence is `results/rtl/a3_lq8_checked_extent.json`.
Full format admission, G2 lifetime/fault integration and reusable activation
storage remain open. Product-stage routed timing and area are unmeasured.


## Immutable LQ8 configuration capture

LQ8 now captures its operation configuration on an idle start edge, before its
registered `lane_start` reaches the lanes. Lane admission, scale read enables
and output geometry use the captured fields. Block-level column/stream-format
checks still inspect the incoming command on that same acceptance edge; the
weight pointer captures its base directly, avoiding a redundant base register.
Starts while busy cannot overwrite the current record. This adds 251 explicit
configuration register bits with no new launch pipeline stage. Physical area
and timing require recharacterization; this is not an area reduction claim.

The G2 adapter currently keeps these signals stable, but future queued command
preparation must not change a running operation through live input wires.
Capturing at LQ8 makes that boundary explicit while preserving its interface.
The standalone lane retains its existing stable-configuration requirement;
LQ8 now provides that stability to every lane throughout admission and execution.

`tools/check_lq8_runtime_operands.py --mutate-array-config` complements every
external DUT configuration field whenever start is low, while the backing service
and independent references retain the accepted command. Comparing this with the
stable-input run checks dimensions, formats, scales, addresses and completion
against the same corpus. Evidence is retained in
`results/rtl/a3_lq8_configuration_capture.json`. This does not yet constitute
G2 runtime transport, cancellation or writeback integration.


## Synthesizable runtime operand service boundary

`ot_a3_lq8_runtime_operands` now assembles captured admission, checked stream
extent, the weight burst scheduler, two SRAM banks and weight FIFO, the future
auxiliary cursor/queue, and the complete-bundle join in synthesizable RTL.
`--integrated-service` selects this module in the numerical checker; the testbench
then implements only external backing services, generation selection, operation
start/clear and verification. No production arithmetic is performed by its
backing arrays. The service is currently explicitly eight-lane, matching its
128-bit weight SRAM path; other array widths need their own validated adaptation.

The public boundary provides command ready/valid, captured scale-enable outputs,
tagged weight burst/beat transport, tagged auxiliary request/response transport,
compute previews and operand credit/data. Command ownership persists until clear,
not until prefetch has merely scheduled its final tile. A record launches only
when geometry validates, compute confirms admission and the scheduler is ready.
Protocol faults remain sticky until clear and suppress new operand credits.
Unexpected responses are refused; the containing controller must handle the
fault, cancel/drain external requests and abort compute. This wrapper does not
silently manufacture completion or implement that parent policy.

Clear revokes bank and queue state together using a local reset expression;
physical reset-tree implementation and safe reset release remain engineering
requirements. Parents must coordinate clear with compute and external transport.
The G2 instance still uses its original staging block: wiring this service into
G2 and implementing cancellation/final-write completion is the next boundary.

The integrated Verilator run, with external LQ8 configuration disturbed after
start, passes 92 cases, 17,103 matching outputs, 18 fault cases and 115,748 checks.
Every per-operation count/cycle record matches the preceding testbench-wired
configuration-capture run (322,385 aggregate cycles). The service accepted 49,040
weight beats across 1,562 tile acquisitions; 6,654 cycles overlapped refill and
arithmetic issue. All 26 focused tests pass. The new lifecycle test covers no
external launch before compute admission, configuration capture, busy overwrite
refusal, sticky malformed-response fault, clear, invalid geometry and restart.
Top-level service lint with the behavioral SRAM model passes. Source-bound
evidence is `results/rtl/a3_lq8_runtime_service.json`. Routed timing, area and
whole-target coverage remain open.

## Explicit operation completion barrier

G2's issue adapter currently retires an operation directly on `array_done`;
its partial outputs have no write-acknowledgement input. That boundary must
change for runtime transport. `ot_a3_runtime_operation_lifetime` implements a
single-operation ownership state machine for the integration: RUN, DRAIN,
held COMPLETE, then IDLE. It captures the operation generation, records the
compute result or runtime fault, clears local operand service state, and issues
an external cancellation/drain request before allowing completion.

`transport_ack` is a handshake in response to `transport_cancel`, promising no
future response from that generation. An idle-looking acknowledgement during
RUN is ignored. `writes_drained` must account for every accepted output write;
both conditions are required, in either order, before completion. A service
fault or explicit abort additionally holds `compute_abort`. Errors use local
controller codes FE (service fault) and FF (explicit abort); parent integration
must map these to architectural engine errors. Abort does not roll back writes
already committed. Global reset requires coordinated transport reset.

The controller's completion record remains stable until accepted, and starts
while busy cannot replace its generation. Directed Icarus tests cover opposite
acknowledgement orders, stale early acknowledgements, delayed completion
acceptance, busy starts, service-fault priority, explicit abort and reset.
Standalone controller lint passes. The runtime numerical checker can enable
`--completion-barrier` to delay final completion beyond compute completion with
separate behavioral transport and write acknowledgements. This models final
write acknowledgement timing; the checker still captures output data in its
existing result memory and is not a production writeback queue.

This controller is not yet wired into G2. Required G2 changes are a separate
runtime transport/cancel interface, a final-write acknowledgement interface,
registered architectural error mapping, and the actual compute-abort connection.
The corpus tests normal completion and core faults; the controller unit test
covers abort requests. They do not establish integrated arithmetic abort or
rollback semantics.

The initial barrier integration also exposed an admission error-mapping rule:
when LQ8 itself refuses a shape, preserve its existing error rather than
converting the auxiliary geometry refusal to a generic service abort. The
corpus bridge signals a geometry service fault only if compute tries to issue
against that refusal. Production integration must retain this distinction while
handling extra runtime-only limits (for example stream-address overflow).

The corrected completion-barrier corpus passes all 92 cases, 17,103 output
identities, 18 fault cases and 115,748 checks. Aggregate operation latency is
323,397 cycles versus 322,385
without the barrier (1,012 additional cycles
for the selected acknowledgement delays). Useful issued work is equal per case;
4 additional speculative weight beats were accepted before service clear.
All 27 focused tests pass. Source-bound results are recorded in
`results/rtl/a3_lq8_completion_barrier.json`. These delays are test conditions,
not measured production transport or memory latency.

## G2 runtime-mode connection

`ot_a3_g2_cluster` now has an opt-in `RUNTIME_OPERANDS=1` generate branch.
It instantiates the runtime operand service and operation lifetime controller,
connects LQ8 previews/credits/data, and exposes weight and auxiliary transport
ports independently of the existing idle-only program/descriptor loader. The
legacy preloaded branch remains the default comparison configuration. Runtime
mode explicitly requires eight lanes and replaces the preloaded staging block;
staging host writes are refused in this mode rather than silently populating
unused memory. Activation/scales still arrive through the external auxiliary
service; reusable activation SRAM remains open.

Adapter completion observes the lifetime barrier rather than raw core done.
External `runtime_transport_ack` responds to the generation-tagged cancellation
request and guarantees no later response from that generation.
`runtime_writes_drained` covers all accepted partial writes. These inputs must
be driven by a real transport/writeback implementation, not tied to optimistic
constants in a deployed system. The partial port remains a fixed-throughput
sink contract with no per-beat ready; backpressured output buffering is a
remaining integration requirement.

Runtime service faults or explicit abort reset the core and suppress partial
write enables, then wait for transport/write drain before engine-error
completion. Already-committed writes are not rolled back. FE/FF local runtime
error codes propagate as nonzero array errors through the existing adapter's
engine-trap mapping. Global reset must coordinate with transport; generations
are incremented on each operation and must not alias undrained traffic.

`tools/check_g2_runtime_boundary.py` elaborates the actual G2 module with
behavioral SRAM and forces the issue adapter's array-configuration outputs.
It checks BF16 80-term contractions across three weight tiles, delayed transport
and write acknowledgement, explicit abort after arithmetic issue, output
suppression and restart with a fresh generation. Program fetch, descriptors and
sequencer issue are deliberately bypassed: this is an actual cluster-boundary
integration test, not end-to-end ABI program qualification. Source-bound output
is `results/rtl/a3_g2_runtime_boundary.json`. Both runtime and legacy branches
elaborate in pinned Verilator with existing repository width/pin warnings;
this is not warning-free lint or routed closure. All 27 focused tests pass.

Next gates are program-driven cluster regressions (including runtime-only
geometry failure and transport faults), output buffering/acknowledgement,
reusable auxiliary SRAM and multi-row reuse, followed by configuration-specific
physical characterization. Existing G2 physical records are historical after
these RTL edits; do not attribute their closure to the new runtime branch.


## Program-driven G2 dispatch qualification

`tools/check_g2_runtime_program.py` builds and verifies a real ABI BF16
contraction (`M=1,N=8,K=80`) and runs the functional Device for its expected
output. It host-loads the program and descriptor images into G2's behavioral
SRAM macros; no internal RTL signals are forced. Activations vary across K and
weights vary across lanes and K, including signs and zeros. The external
fixture service repacks ABI N-major weights into eight-lane words; that packing
is explicit test infrastructure, not a general hardware address translator.

This test exposed two defects hidden by the earlier boundary test:

- G2 captured slots 0/1/2, but ABI inputs occupy slots 0..3 and outputs 4..5.
  The contraction now captures slots 0/1/4 into its three local view records.
- G2 checked B as `[K,N]`; ABI weights are `[N,K]`. Admission now checks B's
  second dimension against K and derives columns from its first dimension.

The regression checks numerical outputs and lane-local output addresses,
completion after transport and final-write drain, explicit abort, a corrupt
transport tag, ENGINE-trap propagation and successful restart after each fault.
Already committed writes remain outside rollback semantics. A separate
Icarus test covers eight adapter contract/refusal cases, including stale view
sets on recycled IRS slots and a third input that cannot replace an output.
The focused suite now has 28 passing tests. Source-bound program evidence is
`results/rtl/a3_g2_runtime_program.json`.

This is one bounded, unscaled BF16 shape with modeled transport, not complete
ABI/deployment or all-target qualification. Nonzero view-offset translation,
partial column groups, additional formats and real output backpressure remain
open. Both G2 branches elaborate with existing warnings; new physical evidence
is still required before assigning a clock or area to these changes.


## Bounded output backpressure and reservations

The subsequent runtime implementation replaces the fixed-throughput partial
sink with `part_valid`/`part_ready`. `part_we` is a held lane mask, not a pulse:
consumers write only on the ready/valid handshake. The mask, lane-local addresses,
results and accumulator codes transfer atomically and stay stable during stalls.
The legacy generate branch retains its old pulse behavior and ignores ready.

`ot_a3_reserved_output_queue` defaults to four entries. Its capacity includes
both queued results and outstanding result reservations. LQ8 publishes
`operand_last` from the first requesting live lane; lockstep live lanes share
that final-K position. G2 reserves one beat when such a bundle actually issues.
Only final groups require output credit, so earlier products can accumulate
while output storage is full. Downstream ready is absent from the credit
combinational path. The output queue supports simultaneous insertion and drain;
a full reservation budget returns credit on the following cycle.

The completion barrier now requires the local queue to be empty AND the
external `runtime_writes_drained` acknowledgement. Producer stop releases
reservations for faulted/flushed results. On explicit abort or service fault,
new results are suppressed and the core stops; already queued outputs retain
their ready/valid contract and drain before error completion. Such writes are
not rolled back. Global reset must reset the downstream transaction as well.
An unreserved/overflowing core result raises a sticky internal protocol error;
it indicates a hardware invariant violation, and global reset is required.

Reproduce the loaded-program stress with:

```
python3 tools/check_g2_runtime_program.py --output-backpressure
python3 -m pytest -q tests/test_reserved_output_queue.py
```

The stress uses `M=6,N=8,K=80`, deliberately fills the queue, varies sink ready,
holds the final result beyond compute completion and external acknowledgements,
and aborts with a valid beat queued. It reports 1,031 output-stall cycles,
17 final-group reservation stalls and 152 correct accepted outputs. Numerical
expectations come from the functional Device. Evidence resides in
`results/rtl/a3_g2_runtime_output.json`; the original single-row always-ready
program remains a separate regression. The five queue tests include non-power-
of-two depth, delayed producers, random simultaneous traffic, reservation
cancellation and protocol-fault detection. Area/timing remain uncharacterized;
this closes the modeled output-backpressure integration gap, not real memory
write service, numerical format coverage or whole-system physical closure.


## Reusable auxiliary SRAM windows

`ot_a3_runtime_auxiliary_windows` serves the existing G2 auxiliary ready/valid
interface. It holds independent 256-word activation64, activation-scale32 and
weight-scale64 SRAM windows. A window descriptor supplies plane, generation,
full service-word base and exact length (1..256); base+length may equal 2^32
but cannot exceed it. The parent must bound that descriptor to the source object.
The module does not invent padding reads or interpret deployment byte strides.

Window install invalidates only its selected plane. Ordered, generation-matched
fill beats advance a per-plane count; only the final accepted beat publishes
residency. The service reports a missing-plane mask for a pending request and
accepts it only when all enabled planes match the generation and bounds.
Address subtraction precedes SRAM indexing; high addresses cannot alias low
windows. Disabled scale planes return zero. One complete response is held, with
synchronous SRAM reads supporting consecutive requests when the receiver is
ready. Window installs/fills wait until any held response drains. Simultaneous
window install and fill gives install priority, and input ready signals make
that choice explicit. This first implementation serializes filling against
reading; independently overlapped fills and bank ownership are later tuning
choices, not assumed free bandwidth.

Protocol errors stop new requests and remain sticky until coordinated clear.
Clear invalidates windows and the response; the parent must cancel/drain the
fill transport as well. The integrated test clears this service on G2's
transport cancellation and supplies no late fill responses. The SRAM RTL is
external to G2's core wrapper, attached through its existing auxiliary ports;
the fixture's miss-to-window scheduler is behavioral. A deployed parent must
implement window scheduling, transport fault propagation and object addressing.

Reproduce with:

```
python3 tools/check_g2_runtime_program.py --output-backpressure --auxiliary-windows
python3 -m pytest -q tests/test_runtime_auxiliary_windows.py
```

The loaded, admitted BF16 program uses M=6,N=24,K=80. Three lane-local columns
reuse each activation word. Its first successful operation accepts 1,440 SRAM
reads from 480 filled words in two exact windows, saving 960 external activation
word deliveries compared with direct per-request service. The full campaign
checks 440 accepted outputs, output stalls, delayed completion, aborts, transport
fault and restart against the functional Device. Numerical input/outputs and
sources are hashed in `results/rtl/a3_g2_runtime_auxiliary.json`. This does not
qualify scaled formats through a loaded program or general deployment memory
mapping; the focused test separately verifies both scale planes and their reuse.
Physical characterization and multi-row weight reuse remain pending.


## Synthesizable auxiliary refill scheduler

The current `--auxiliary-windows` campaign uses
`ot_a3_auxiliary_window_scheduler` instead of its earlier behavioral manager.
The scheduler captures one generation and three 32-bit base/word-count pairs
at command acceptance. Zero-length unused planes are legal; attempting to fill
one faults. For the lowest missing plane, registered stages check bounds,
subtract its base, align the offset to a 256-word page, compute the remaining
extent and publish the exact base/length. A plane ending exactly at 2^32 is
legal. Immutable captured bounds survive live command-input changes.

One burst is outstanding. Its tag combines operation generation and a monotonic
burst serial; every accepted response must echo that tag and the next index.
The scheduler installs the window before issuing fetch, forwards only matching
responses into SRAM, and advances the serial after the last accepted fill.
Wrong, duplicate, stale or unsolicited responses raise sticky protocol_error
and cannot publish data. Window/fetch/fill outputs obey ready/valid stalls.
Clear cancels scheduler state and must coincide with coordinated cancellation
of external transport and SRAM residency. The caller must not reuse generation
identity while an older response can still return.

The parent connects scheduler/window faults to G2's new
`runtime_service_fault` input. This reports local FE through the existing ENGINE
trap path, resets arithmetic, drains queued writes and waits for transport
acknowledgement. Integrators with no external service fault source must tie the
input low. Legacy mode ignores it. The program test corrupts an auxiliary burst
tag and verifies no output before error completion and successful restart.

`results/rtl/a3_g2_runtime_auxiliary_scheduler.json` records eight transactions,
584 accepted matching outputs, and 480 activation fill words serving 1,440 reads
in the first successful operation. External request and response stalls are
explicit. `results/rtl/a3_auxiliary_window_scheduler.json` records focused tests
for all planes, unaligned bases, 256-word and partial tails, address-space end,
invalid bounds, input mutation, handshake stalls, tag/index faults and clear.
The focused suite has 35 passing tests; standalone scheduler lint is clean.
This remains service-word addressing. The production deployment mapper and
external burst transport are not implemented by this scheduler, and no routed
frequency or area claim follows from these simulations.


## Object-relative contiguous byte mapping

The current `--auxiliary-windows` regression inserts
`ot_a3_operand_byte_mapper` between the refill scheduler and external transport.
Its operation record contains generation, three object IDs, service-word bases,
64-bit byte bases, 64-bit object sizes and two-bit word-size shifts. Mapping is:
`byte_offset = byte_base + ((request_address - word_base) << shift)`;
`byte_length = request_words << shift`. Only contiguous 1/2/4/8-byte words are
represented. Packed nibbles and strided/tiled layouts require another mapping
contract and are not silently treated as this layout.

Request capture rejects invalid planes, wrong generation, zero/overlong bursts,
addresses below the service base and a service end beyond 2^32. Separate pipeline
stages scale the offset, add the byte base, form the byte end and validate against
the object extent. Arithmetic retains carry through 65 bits; byte overflow cannot
wrap into an apparently valid low address. Only after validation is burst_valid
asserted, and all fields remain held until burst_ready. One mapping is in flight.
Clear must accompany scheduler/transport cancellation and drops the mapping record.

The BF16 fixture exports raw bytes from the actual activation memory object in
the functional Device, not a prepacked service-word array. RTL requests that
object ID and byte range; the transport reads two bytes per word, forms the
little-endian BF16 code, and zero-extends the response to 64 bits. The fixture
still supplies admitted mapping configuration and implements the byte transport.
Mapper errors join scheduler/window errors on `runtime_service_fault`.

`results/rtl/a3_g2_runtime_byte_transport.json` records this integrated path;
`results/rtl/a3_operand_byte_mapper.json` records 106 randomized/boundary mappings,
input mutation, backpressure, generation/plane refusal and clear, plus clean
standalone lint. The total focused suite has 36 passing tests. The earlier
scheduler-only evidence remains a historical prepacked-transport checkpoint.

Next deployment gates include constructing mapping records from actual ABI view
and memory-object descriptors, preserving full view offsets, implementing packed
weight/scale addressing and output-object writes, then removing the modeled
transport. This primitive alone does not qualify those missing paths or establish
frequency, area or energy results.


## Reject high view offsets before narrowing

G2 now preserves whether each required ABI view offset has nonzero high 32 bits.
It refuses that issue with CAPABILITY before requesting descriptors or starting
arithmetic. Previously offset 2^32 silently became zero. Per-view overflow state
tracks replacement, IRS ownership, issue consumption and clear alongside the
existing view-valid set; unused slots do not affect it. The focused adapter test
now has 12 checks and includes each required operand plus valid recovery.
`results/rtl/a3_g2_issue_contract.json` binds evidence to the correction.

This is a checked limitation of the existing 32-bit service-word interface.
Supporting wider deployment offsets requires constructing object-relative byte
mapping records while preserving the full ABI offset; merely truncating that
offset into a service base is no longer accepted. General low nonzero offsets
also remain unqualified for packed operands and lane-local output mapping.
