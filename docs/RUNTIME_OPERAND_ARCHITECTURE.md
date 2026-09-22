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
