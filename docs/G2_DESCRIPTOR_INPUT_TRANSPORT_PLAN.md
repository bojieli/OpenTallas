# G2 descriptor-driven input transport

Status: implementation in progress, 2026-09-22. Optional BF16 weight-object
transport is integrated; general input transport and pass-first execution remain
open. The sections below retain the original plan and successive checkpoints;
later checkpoints supersede earlier status statements. See the
[current architecture summary](ARCHITECTURE_REVIEW_SUMMARY.md).

## Observed boundary

`ot_a3_g2_array_issue_adapter` reads three beats each for A/B: dtype, scale
binding and shape, but not their strides or object capacities. It uses resolved
element offsets as service-word bases. `ot_a3_lq8_runtime_operands` requests
128-bit packed weight words in the array's issue order. The loaded campaign
constructs those words in Python, repeating the stream for each output row.
Activation byte mapping and auxiliary SRAM windows are instantiated by the test
bench; their object identity, bounds and layout are fixture inputs.

Consequently, the current loaded test verifies arithmetic, queueing and output
transport, but does not establish arbitrary descriptor-driven input transport.

## Required architecture

1. Capture A/B rank-two element strides and object identities alongside their
   dtype and resolved offsets. Resolve their MEMORY_OBJECT descriptors and
   permissions before launch. Read four descriptor beats for each tensor view;
   the existing short/long descriptor-store protocol can support this. Resolve
   scale and numeric bindings explicitly; host scale geometry cannot be treated
   as descriptor-derived coverage. Keep the full admission record immutable
   until cancellation/drain completes.
2. Separate the monotonically increasing service-word identifier from logical
   tensor coordinates and object byte addresses. Preserve existing bank and
   operand-join tags. A layout cursor generates physical gather work; transport
   responses assemble the packed word expected by the arithmetic lanes.
3. Walk the actual weight order: output row, groups of up to INTERLEAVE local
   columns, K word, local column, lane. For BF16, lane `l` of local column `c`
   reads element `B_offset + (LANES*c+l)*B_stride0 + k*B_stride1`. Mask columns
   beyond logical N and supply zero without a memory request. Activation reads
   `A_offset + row*A_stride0 + k*A_stride1`. These formulas define a reference
   oracle; per-word hardware uses registered increments and wrap/reset state,
   not a variable divider/multiplier chain.
4. Coalesce gathers into bounded memory-line requests and retain fetched lines.
   ABI N-major weights place adjacent K values together, while the array consumes
   adjacent output columns together. Eight independent scalar reads per issue
   word would close the functional gap but waste bandwidth and is not the
   performance target. Banked line storage and an explicit transpose/assembly
   stage must expose useful bytes, transferred bytes and bank-conflict counters.
5. Reserve assembly capacity before issuing reads. Track operation generation,
   response identity and destination slots until all accepted reads retire.
   Cancellation stops new reads, drains accepted responses and revokes partial
   words. Do not release a bank or reuse a generation while responses can still
   target it. Backpressure must retain every published request unchanged.
6. Preserve resident-row replay: retained packed words need no repeated object
   reads. For rows beyond 1,024 words, tile reuse across output rows requires a
   separate accumulator-capacity design. Changing the memory layout alone must
   not silently reorder sequential FP32 accumulation.

Sub-byte formats require bit offsets, boundary-spanning extraction and their
actual group/scale semantics; extending the byte mapper's shift field alone is
insufficient. Unsupported layouts must be refused before reads, with explicit
coverage gaps until those formats are implemented.

## Integration and acceptance order

First implement immutable descriptor records and the logical layout cursor,
including overflow and tail handling. Next integrate bounded line fetch,
transpose/assembly and response ownership into the synthesizable cluster.
Replace the fixture's packed `weight.hex` input with actual deployment object
bytes; the fixture should model external memory timing and errors only. Then
extend formats and scale transport, followed by reuse beyond resident rows.

Functional acceptance includes nonzero input offsets, independent row/column
strides, logical tails, K boundaries, objects ending inside a final element,
read-permission failure, response stalls, cancellation and late responses.
Compare against the independent Device model and protect output gap bytes.
Replay-enabled and streaming runs must produce identical numerical results.

Performance acceptance records memory bytes per useful output, line reuse,
assembly occupancy, bank conflicts, operand starvation, compute utilization and
whole-operation latency. Compare with the existing packed-stream baseline under
the same external bandwidth/latency assumptions. Report packing costs explicitly.
Physical acceptance requires current-source containing-block synthesis with the
actual SRAM macros, followed by setup/hold and physical-rule closure. A standalone
cursor frequency cannot qualify the integrated transport.

## Implemented coordinate cursor checkpoint

`rtl/abi3/ot_a3_weight_layout_cursor.sv` now implements the logical weight walk
with descriptor-relative element base, lane stride, tail mask, row/K/column
coordinates and generation. Three admission stages compute a maximum element
address and refuse overflow before publication. The per-coordinate path uses
registered additions and wrap state; products occur only during admission.
Payload registers use state ownership rather than a global reset tree.

The standalone regression checks 73,972 coordinates at each of INTERLEAVE=1/3/5
(221,916 total), including 65,535-column and 65,535-depth cases, zero/nonunit
strides, exact 64-bit address limit, overflow, stalls, cancellation and recovery.
Verilator strict lint passes. Evidence: `results/rtl/weight_layout_cursor.json`.

The initial 1 ns pre-layout probe measures 1,177.847 um² and -1.022568 ns setup
slack; its critical path starts in clear and reaches a payload-register enable.
The initial source snapshot is retained with the record. A subsequent lint-only
cleanup stores only the overflow bit of the bound, and that source is now in an
ASAP7 TT 1 ns CTS8 routed characterization with fanout limit 16. No routed result
is yet claimed.

This cursor is not connected to the cluster yet. Descriptor capture, permissions,
object-capacity checks, dtype conversion, line reuse, packed-word assembly and
response ownership remain mandatory integration work. Its coordinates do not
authorize physical reads. No workload speedup is claimed from this checkpoint.

## Descriptor-record integration and routed cursor checkpoint

The adapter and cluster now expose optional `RESOLVE_INPUT_OBJECTS=1`. This
reads four beats for each A/B tensor view, captures object identity and both
strides, resolves two readable nonempty MEMORY_OBJECT descriptors, and publishes
immutable 64-bit capacities through completion/drain. The default remains zero
while downstream weight assembly is unfinished. With output object resolution
also enabled, admission uses 21 auxiliary beats rather than 13.

The loaded campaign's `--input-layout` mode checks the descriptor-derived records
and feeds A's identity/capacity into the actual activation byte mapper. It passes
2,234 matching outputs and 295 writes/acknowledgements in 42,776 campaign cycles,
versus 42,561 before input resolution. This extra admission work is not a
performance improvement. Stride-aware input fetch and weight assembly are still
required; the campaign's weights remain prepacked. Focused adapter tests cover
input resolution independently of output resolution, invalid type/header/payload
offset, read permission, empty objects, descriptor service faults and cancellation
in both new states.

The first cursor route is physically clean but misses setup: 1,301.800 um²,
-0.191066 ns setup and +0.051554 ns hold at 1 ns. Its actual critical path is
command_cols through the admission extent multiplication. The next implementation
splits each 16x32 product into two registered 8x32 products and a registered
combine. This adds two admission cycles, with no additional coordinate cycles.
The full cursor corpus passes and strict lint passes; its matched route is now
running. Selection remains subject to timing/area results. The original routed
source is retained as `weight_layout_cursor/before_admission_pipeline.sv`.

The G2 physical run launched before this descriptor change is now a historical
baseline. Its changed adapter/cluster sources are retained under
`a3_g2_runtime_writer/descriptor_bounds_handoff_launch_sources/`. It cannot prove
physical timing for input resolution.

## Admission-pipeline physical comparison

The matched CTS8 route confirms the admission pipeline removes the 1 ns setup
failure: setup slack improves from -0.191066 to +0.0537158 ns. Hold slack is
+0.051455 ns, with zero slew, capacitance, DRC and antenna violations. Cell area
increases from 1,301.800 to 1,375.970 um² (5.70%). Admission takes five cycles
after acceptance instead of three; streaming still supports one coordinate per
cycle when ready. This is a local timing/latency/area tradeoff, not a workload
speedup measurement.

Full physical acceptance still fails: two clock-tree nets have 18 and 17 loads
against the unchanged fanout limit of 16. A CTS12 run is active using the same
RTL and target period to repair the clock distribution. No fully closed 1 GHz
cursor configuration is claimed yet. Source and retained artifact hashes were
verified for both CTS8 records; comparison evidence is in
`results/physical_abi3/asap7/weight_layout_cursor/admission_pipeline_comparison.json`.

The strengthened functional corpus now checks 73,976 coordinates in each of
three interleave configurations (221,928 total), plus simultaneous maximal
column/K admission bounds and cancellation at every admission stage. All pass.

## Bounded BF16 line gather and closed cursor checkpoint

`ot_a3_bf16_weight_gather` now assembles eight BF16 lanes from byte-addressed
object memory. It reserves one coordinate at a time, checks all active lane
bounds before reading, masks tail lanes, and retains a 16-byte line for each
lane/interleaved column slot. The default three slots hold 384 bytes of data,
plus 24 line tags and validity bits. Cache data has no reset tree. All hit lanes
assemble together; misses share one outstanding tagged read. Partial final
lines use a bounded byte count.

Published reads remain stable through backpressure and later faults. A foreign
response does not retire the expected read; the expected response must still
drain. Clear requires external cancellation acknowledgement or completed drain.
Both same-edge and delayed read responses are covered. Input object permission
admission remains the parent's responsibility; this module checks byte capacity.

With three slots and a two-row N53/K80 BF16 stream, retention reduces measured
reads from 8,480 to 1,060 and transferred bytes from 135,680 to 16,960 (87.5%).
Delayed-response workload cycles fall from 56,853 to 12,013; immediate-response
cycles fall from 22,933 to 7,773. These compare retention enabled/disabled in the
same bounded service and traversal, not against the old prepacked G2 interface.
Eight standalone regressions pass, each checking 1,123 assembled words plus
fault/cancellation cases. Evidence: `results/rtl/bf16_weight_gather.json`.
A 1 ns CTS12 physical run is active; no gather physical closure is claimed.

The cursor's revised CTS12 route now passes every reported timing and physical
check at 1 ns: area 1,359.880 um², setup +0.0561202 ns, hold +0.0514614 ns, zero
fanout/slew/capacitance/DRC/antenna violations. Current RTL and retained artifacts
pass the audit in `weight_layout_cursor/admission_pipeline_cts12_audit.json`.
This supersedes the earlier pending cursor repair. CTS8 remains a failed record.

The gather and cursor still require a shared wrapper tied to G2's weight request
tags and bank reservations. The loaded G2 fixture still supplies prepacked
weights. Format coverage beyond BF16, multiple outstanding misses, line-storage
implementation/area, and integrated service-rate qualification remain open.

## Composed burst transport checkpoint

`ot_a3_bf16_weight_transport` now composes the actual layout cursor and cached
gather behind the G2 scheduler's burst contract. Service addresses are checked
separately from object element offsets. Each assembled word retains its burst
generation/address tag and zero-based bank-fill index. A slot counter follows
the actual partial/full interleaved column passes without a per-word divider.
Resident replay can stop requests after the first row while the transport keeps
operation ownership until clear.

Six composed regressions compare 5,040 words with an independently generated
strided tensor-index oracle, using burst sizes 1/32/512 in full-stream and
resident-first-row modes. They cover tail padding, high service bases, stalled
responses, invalid generation/address/extent, range overflow and a burst that
extends beyond the cursor's logical shape. The last case faults instead of
hanging. Strict Verilator lint passes. Evidence: `results/rtl/bf16_weight_transport.json`.

A containing-transport 1 ns CTS12 route is now active, alongside the standalone
gather route. Neither has a physical acceptance result at this checkpoint.
G2 cluster integration remains next. Its operation lifetime asserts service
clear as soon as it enters drain; the memory-facing transport must instead
retain ownership until the external cancellation acknowledgement. The existing
packed bank service and the new external read owner therefore require distinct
clear timing. The loaded program test must exercise this boundary, rather than
assuming the current compute-service clear is safe for pending memory requests.

## Loaded G2 weight-object integration

The synthesizable cluster now contains the composed transport when
`RUNTIME_WEIGHT_OBJECT_READS=1`, requiring runtime operands and input object
resolution. `RUNTIME_WEIGHT_LINE_REUSE=1` enables its line retention. Unsupported
weight dtype/group combinations refuse at admission; this first transport mode
requires BF16 weights and group size one. The default prepacked mode is unchanged.

The new object-read port carries object identity, byte offset, bounded byte count
and generation/sequence tag. The prior packed request outputs are monitors in
this mode; external packed responses are ignored. Weight element offsets and
strides come from the descriptor record, with the adapter's existing 32-bit
resolved-base capability limit still enforced.

The loaded program's `--weight-object-reads` mode now supplies actual deployment
weight bytes. It passes 2,234 matching outputs and 295 writes/acknowledgements,
including wrong read generation, queued abort, late write failure, binding failure
and recovery. Abort is explicitly exercised with an outstanding weight read.
The transport retains its read ownership until cancellation acknowledgement;
mutating its clear to the compute service's early clear causes the new assertion
to fail. The negative result is retained in
`results/rtl/g2_weight_object_early_clear_mutation.json`.

Matched retention-disabled/enabled loaded runs use identical source manifests,
golden outputs and external memory timing. First-operation weight reads drop
from 4,240 to 530 and bytes from 67,840 to 8,480 (87.5%). Full fault/recovery
campaign cycles drop from 269,291 to 82,676 (69.30%). These are not model inference
latencies. The previous prepacked-service campaign still passes at 42,561 cycles;
it omits the new gather work and is not the fair retention baseline. Comparison:
`results/rtl/g2_weight_object_line_retention_comparison.json`.

The initial standalone gather route is not accepted: area 4,816.740 um², setup
-0.0131266 ns, hold +0.0336196 ns, 15 slew and three capacitance violations at
1 ns. Fanout, DRC and antenna checks pass. The critical path runs from slot
selection to read byte-count generation. Source/artifact binding is verified;
the containing transport route remains live and must guide the next pipeline
change. No physical closure for the integrated weight path is claimed.

Remaining architecture work includes strided/nonzero-base loaded weight fixtures,
activation stride transport, non-BF16 formats/scales, multiple outstanding line
misses, deep-row accumulator/reuse architecture, and all-target engine balance.
The current line cache is a bounded register implementation; its area must be
accounted for when evaluating the integrated SRAM and control organization.

## Containing bounds-path optimization

The containing transport's baseline global-route path runs from a lane address
through end-address addition and bounds comparison into gather control, missing
the 1 ns target by 150 ps at that intermediate stage. This differs from the
standalone gather's worst path. The new implementation captures the final legal
BF16 starting offset (`object_bytes - 2`) at command admission and compares
addresses directly. It also captures the final reachable line's byte count,
including the special case where the object ends with one unusable byte.
No per-coordinate cycle was added.

Fourteen standalone/composed tests pass. Gather tests now check 1,128 words per
configuration and cover object remainders 1/2/3, minimum capacity and the maximum
valid BF16 address. Both loaded G2 modes pass with exactly unchanged campaign
cycles (82,676 retained; 269,291 unretained), traffic and matching outputs.
Strict containing-transport lint passes.

A matched CTS12 1 ns containing route is running as
`bf16_weight_transport/pnr_invariant_bound_cts12_1ns.json`. Timing and area benefit
remain unproven. The baseline source, global-route diagnostic and experiment
manifest are retained in `bf16_weight_gather/invariant_bound/`; that intermediate
report is not final physical acceptance.

## Loaded strided-weight and row-wrap qualification

The fixture builder now creates actual BF16 weight objects with explicit element
offset and strides, filling gaps with poison values. `--strided-weights` selects
base 11, column stride 165 and K stride 2 for the N53/K80 campaign, producing a
17,500-byte object. The Device model and RTL consume that same descriptor and
object. The external test service supplies bytes only, without repacking.

Both six-row streaming and resident-row replay pass 2,234 matching outputs and
295 writes/acknowledgements through the full fault/recovery campaign. Streaming
uses 6,600 first-operation reads / 105,576 bytes and 387,169 campaign cycles;
resident replay uses 1,100 reads / 17,596 bytes and 110,614 cycles. That is
83.33% less first-operation weight traffic and 71.43% fewer campaign cycles in
this matched strided configuration. The line cache remains enabled in both.
Traffic can exceed object size because separate lane cache entries may fetch a
shared boundary line; every individual read remains within the object.
Evidence: `results/rtl/g2_strided_weight_row_reuse_comparison.json`.

This exercises a nonzero service base distinct from byte offsets, partial lane
groups, K/column strides, complete row wrapping and bounded final-line reads
through the actual cluster. The original packed mode still passes at 42,561
cycles. The test watchdog was extended for real object-memory campaigns so
slower valid streaming cases can complete; no hardware timing was relaxed.

The pre-invariant-bound containing transport route is now terminal: area
6,295.850 um², setup -0.107403 ns, hold +0.0265599 ns at 1 ns. Slew, capacitance,
fanout, DRC and antenna checks pass. Its worst path confirms the repeated
end-address bounds bottleneck. The historical source binding and retained
artifacts are verified in `bf16_weight_transport/baseline_source_audit.json`.
The invariant-bound candidate route remains active; no current transport clock
closure is claimed. Activation-stride transport, other formats, deep-row reuse
and all-target balancing remain unfinished.

## Command-owned lane-offset optimization

The invariant-bound transport's global-route worst path moved to column-stride
multiplication followed by lane-address addition (-51 ps at the intermediate
1 ns stage). The next implementation captures eight 35-bit lane element offsets
from the descriptor stride at command admission. Each coordinate now adds its
base to those retained offsets without repeating the stride multiplication.
The gather interface takes the stride with the command, matching its immutable
operation ownership. No coordinate or admission cycle was added.

Fourteen gather/transport configurations pass, including a maximum 32-bit stride
and an oracle that depends on high address bits. Changing the command stride
after admission leaves live addresses unchanged. Both loaded strided G2 campaigns
pass with identical counters: resident replay 110,614 cycles, streaming 387,169,
2,234 matching outputs and 295 write acknowledgements each. Strict lint passes.

The matched containing CTS12 1 ns route is active as
`bf16_weight_transport/pnr_command_lane_offsets_cts12_1ns.json`. The invariant-bound
route also remains live and is retained as a separate baseline. Neither this
intermediate path report nor functional results prove a routed timing/area gain.
Snapshots and the decision manifest are in `bf16_weight_transport/command_lane_offsets/`.

## Invariant-bound routed result

The matched containing transport route confirms an area and setup improvement:
standard-cell area falls from 6,295.850 to 6,094.540 um² (3.20%), and setup slack
improves from -0.107403 to -0.0237331 ns at 1 ns. Hold slack is +0.0296842 ns.
There is no transaction-cycle change. Both historical source snapshots and all
retained artifacts have verified hashes in
`bf16_weight_transport/invariant_bound_routed_comparison.json`.

The candidate is not physically accepted: 26 slew violations remain, although
capacitance, fanout, DRC and antenna checks pass. Its worst routed path is now
column-stride multiplication into gather address capture, matching the path
targeted by the subsequent command-owned lane offsets. That later route remains
active. This result establishes neither current-source closure nor a system clock.

## Integrated memory-capacity audit

The historical descriptor-bounds/handoff G2 run remains live. Its intermediate
flattened synthesis checkpoint retains five 256x128, two 2048x128 and two
512x128 SRAM macros. The inventory checker now derives the capacity from these
observed macro geometries and counts, instead of merely echoing the configured
bit total. It verifies 819,200 macro bits and rejects mismatched or unknown
capacities. Six checker regressions pass. The remaining 2,304 inferred bits are
ROM, with no writable inferred memories or unresolved hierarchy at this stage.

Evidence is retained in
`a3_g2_runtime_writer/descriptor_bounds_handoff_synthesis_inventory.json`. This
checkpoint predates integrated weight-object reads and is not final placed SRAM
or current integrated timing evidence. The command-lane-offset transport route
remains active; no new timing result is claimed here.

## Gather word handoff implementation

The gather can now capture a successor coordinate on the same edge that its
published output word is accepted. `WORD_HANDOFF=1` is forwarded through the
transport and cluster (`RUNTIME_WEIGHT_WORD_HANDOFF`); disabling it provides a
matched comparison. Stalled output data and identity remain stable. A same-edge
unexpected response blocks successor acceptance, while the published output
still retires. The burst adapter suppresses handoff on the final response beat
and accounts for the retiring predecessor when validating the final coordinate.

Sixteen focused cases pass, including continuous-word handoff and fault priority.
Eight ready words take 25 cycles versus 32 without handoff. The matched loaded
strided-weight G2 campaign drops from 110,614 to 105,552 cycles (4.58%) with
unchanged traffic, 2,234 matching outputs and 295 write acknowledgements. Source
manifests and golden outputs match across the two configurations. Evidence:
`results/rtl/g2_weight_word_handoff_comparison.json`. This is a campaign-cycle
improvement, not an inference-latency measurement.

The containing handoff CTS12 1 ns route is active; timing/area impact remains
unproven. Previous pre-handoff gather/transport snapshots are retained in
`bf16_weight_transport/gather_handoff/` for the still-running lane-offset route.

## Streaming handoff and fault-priority qualification

The handoff now also passes a matched loaded campaign with resident-row replay
disabled, repeatedly filling banks across six complete strided rows. Cycles drop
from 387,169 to 361,689 (6.58%) with unchanged first-operation reads (6,600),
bytes (105,576), 2,234 matching outputs and 295 writes/acknowledgements. This
complements the resident-row comparison and exercises handoff across full row
and bank-refill boundaries. The source manifests and golden outputs match.
Evidence: `results/rtl/g2_streamed_weight_handoff_comparison.json`.

Removing the same-edge unexpected-response guard from coordinate readiness
causes the targeted test to fail with “fault admitted successor.” That negative
mutation is retained in `results/rtl/bf16_gather_handoff_fault_mutation.json`.
The production guard was restored. Initial loaded checks overlapped this brief
mutation and were rejected by source-hash validation; the retained campaign
records come from subsequent stable-source reruns. Physical jobs were not
restarted. Lane-offset and handoff routes remain active, so no new clock
closure or area comparison is claimed at this checkpoint.

## Command lane-offset final route

The pre-handoff command-lane-offset route completed at 1 ns with 6,159.820 um²
cell area, -0.0151573 ns setup and +0.0402148 ns hold slack. Eleven slew
violations remain; capacitance, fanout, DRC and antenna checks pass. Relative
to the invariant-bound route, setup improves by 8.58 ps and slew violations
fall from 26 to 11, while area rises 1.07%. The worst path now runs from cache
slot selection into read-byte-count generation. This is not physical closure.
The historical sources and retained artifacts are verified in
`bf16_weight_transport/command_lane_offsets_route_audit.json`. The newer handoff
route remains active and must be assessed before selecting the next pipeline.

## Per-lane final-line flags

To shorten the measured cache-slot-to-read-byte-count path, the gather now
registers whether each lane addresses the final reachable object line during
the existing BOUNDS stage. Miss selection chooses a single flag instead of
selecting a 60-bit address followed by a wide comparison. This adds eight
payload bits and zero pipeline cycles. Sixteen focused tests and strict lint
pass. Loaded strided campaigns retain exactly 105,552 resident and 361,689
streaming cycles, with unchanged traffic, outputs and acknowledgements.

The matched containing route is active as
`bf16_weight_transport/pnr_lane_line_extent_cts12_1ns.json`. Area/timing benefit
remains unproven. The previous handoff route continues separately. The baseline
gather source and source-bound functional evidence are retained in
`bf16_weight_transport/lane_line_extent/`. Earlier matched handoff campaign
records were archived before their current-path refresh so their comparison
hashes remain valid.

## Measured whole-row capacity boundary and schedule dependencies

Loaded real-object campaigns on either side of the existing 1,024-word replay
limit pass 2,234 outputs and 295 writes/acknowledgements each:

| M/N/K | Packed words per weight row | First-operation weight fills | Object bytes read | Activation fills | Campaign cycles |
|---|---:|---:|---:|---:|---:|
| 6/53/144 | 1,008 | 1,008 | 31,164 | 2,400 | 196,707 |
| 6/53/160 | 1,120 | 6,720 | 207,336 | 2,496 | 708,336 |

These are different workloads, so their cycle ratio is not an optimization
speedup. They expose the capacity discontinuity: the larger row streams six
times, despite a three-column-group K160 pass occupying only 480 packed words.
Evidence: `results/rtl/g2_weight_replay_capacity_boundary.json`.

A column-pass-first traversal could retain a complete pass and reuse it across
output rows before advancing to the next pass. Each output's K accumulation
would still be sequential, and no cross-row partial accumulator spill is needed
when the full K pass fits. However, implementation must change these together:

- Lane issue control currently walks row, column pass, K, interleaved column.
  Its activation bases, output addresses, slot reuse and scale cursors must
  follow the new pass, row, K, column order.
- The future operand cursor, weight layout cursor and resident bank scheduler
  must share the same traversal contract. Changing only fetch addresses would
  silently pair weights and activations incorrectly.
- Tail masking currently tracks row-tail addresses incrementally; pass-first
  output order needs explicit coordinates or a matching ordered cursor.
- The output-object writer validates the old row-major beat sequence. Either
  a bounded reorder stage restores that order or the writer and its validation
  adopt the admitted pass-first schedule. Reorder storage must be budgeted,
  not hidden in the test fixture.
- Activation reuse must be measured again: changing traversal can increase
  activation refills across rows and negate some weight-traffic savings.

For K passes exceeding bank capacity, full-pass retention is insufficient.
Depth tiling then requires preserving per-output FP32 accumulator state across
tiles, with a quantified register/SRAM budget and unchanged addition order.
The new schedule is not yet implemented; these measurements constrain the next
architecture change while the current transport physical runs continue.
# Pass-first cursor implementation checkpoint

The weight layout cursor now exposes `PASS_FIRST=1` to walk column pass, row,
K, group, with the original row-first order retained at the default value zero.
The implementation resets the row index when advancing a pass and reuses its
captured pass base for subsequent rows. It adds no admission or coordinate
cycles. Execution, operand scheduling, weight-bank reuse and output sequence
validation still need coordinated integration; this cursor change alone does
not reduce loaded traffic.

Both orders pass independent tensor-coordinate checks at interleave 1/3/5:
80,696 coordinates each, 484,176 total. Coverage includes M6/N53/K160 above
whole-row capacity, partial passes, strided views, stalls, cancellation, maximal
extents and overflow refusal. Six existing composed transport tests also pass;
strict Verilator 5.050 lint passes with pass-first enabled. Evidence:
`results/rtl/weight_layout_pass_first.json`.

The pre-final-line handoff containing route completed at 1 ns with 6,160.300 um²
cell area, -0.00156786 ns setup slack, +0.0398271 ns hold slack and 11 slew
violations. It remains unclosed. The critical path is gather slot selection to
read-byte count. Launch-source bindings and seven retained artifacts are verified
in `bf16_weight_transport/word_handoff_route_audit.json`. The original cursor
source is retained under `pass_first_cursor/before.sv` for this and other earlier
routes. The final-line route remains active and predates this cursor change.

## Pass-first future operand schedule

The future operand cursor now supports the same pass/row/K/column walk as the
weight layout cursor. It retains activation and scale origins at admission,
restores them for each pass, and replays the weight-scale pass origin for each
row. Its sequential stream address remains monotonic. The depth-one transition
includes the final same-edge column-scale increment. No request bubbles or
additional admission cycles are introduced.

The 96 cursor configurations cover both schedules, interleave 1/3/5, scaled and
unscaled weight groups, wrapping scale addresses, one-row and depth-one shapes,
and M6/local-N7/K160. They verify every address against independent tensor
indexing with stalls, input mutation, clear/reset and restart. Together with
runtime ownership and auxiliary reservation tests, 113 tests pass. Strict
Verilator lint passes for both schedule parameters. Evidence is retained in
`results/rtl/lq8_operand_cursor_pass_first.json`.

The pass-first operand cursor is under physical characterization at 1 ns,
ASAP7 TT, CTS12 with fanout 16 and the library transition limit. No physical
benefit is claimed before completion. The pre-change source is retained at
`results/physical_abi3/asap7/runtime_operand_cursor/pass_first/before.sv`.
The lane issue order, bank reuse and output sequencing still require coordinated
changes before enabling this mode in the runtime service or claiming loaded
traffic reduction.

## Pass-first arithmetic lane and physical outcomes

The arithmetic lane now supports pass-first issue, preserving per-output K
association and physical row-major output addresses while publishing in pass/row
order. Captured pass origins restore weight and scale cursors for each row;
activation/output origins restore the first row on pass advance. The depth-one,
one-column boundary bypasses the simultaneously captured pass origin. Existing
accumulator slots and recurrence scheduling are retained; no partial spill store
or extra issue cycle is introduced. Runtime G2 has not enabled this schedule.

Nineteen focused tests pass: both schedule orders with adder depths 1/2/3 at
K1/K4/K160, three rows and seven local columns, plus rejection of unsupported
depth five. They compare every
operand address and exact FP32 output, exercise signed BF16 values with large
magnitude differences, both row-block scale streams, nonzero output bases,
credit stalls and reset/recovery. Evidence: `results/rtl/lane_pass_first.json`.
Testing also exposed the old unsupported-adder-depth problem: arithmetic uses
at most three stages while tokens used the requested depth. Invalid depths now
fail explicitly. The default-lane campaign source list now includes the two
FP32 pipeline modules required by its current sequential reference.

The pass-first operand cursor route passes all recorded physical checks at
ASAP7 TT 1 ns, CTS12: 645.573 um² cells, setup +0.177739 ns, hold +0.0506798 ns.
Source and seven retained artifact hashes are verified in
`runtime_operand_cursor/pass_first_route_audit.json`. This is standalone cursor
closure; it does not qualify the lane or integrated schedule.

The containing final-line transport route also completes: 6,175.290 um² cells,
setup +0.0547659 ns, hold +0.0395379 ns at 1 ns. Nine slew violations keep its
verdict NOT_MET; other reported checks pass. The previous handoff route had
6,160.300 um² and -0.00156786 ns setup slack with eleven slew violations. The
new critical path is gather slot selection to assembled word data. Verified
historical source bindings and seven artifacts are retained in
`bf16_weight_transport/lane_line_extent_route_audit.json`.
A current-source transport route with 10% slew repair margin is active, keeping
the same 1 ns target, fanout limit and library transition limit. Its outcome is
pending; no relaxed-limit closure or extrapolated frequency is claimed.

The broader two-simulator default-lane quick D1 campaign at adder depths 3/2/1
now passes, including deterministic quick-profile manifest checks. Both simulators
report 56,992 checks at L3 and L2 and 56,996 at L1, with matching markers and
14 exercised fault cases per depth. All recorded source hashes were checked.
Evidence: `results/rtl/abi3_lane_pass_first_default_regression.json` and its
companion source-binding audit.

The next bank/transport integration must separate the logical issue stream from
the unique fetched weight stream. Replaying a pass across rows advances issue
addresses without reading those repeated weights again. The current transport
requires sequential external request addresses and its coordinate cursor still
walks every row; simply launching per-pass scheduler commands would violate
that contract at the second pass. Use explicit pass ownership and distinct
fetch/issue bases (or an equally checked schedule-aware skip), release retained
banks only after the final row of each pass, and keep compute admission and the
future operand cursor alive across pass boundaries. This is in addition to
schedule-aware output validation and tail masking. Above-bank-size passes still
need a defined fallback and accumulator budget; no unlimited retention is assumed.

## Pass ownership and compact fetch scheduling

`ot_a3_weight_pass_scheduler` now schedules each column pass across all rows
using the existing two-bank tile scheduler. A separate issue-base register
preserves contiguous logical operand identities while the fetch base advances
only over fetched data. Eligible passes of at most 1,024 words are retained and
replayed; larger passes stream every row. Tail eligibility is checked separately.
Banks are released on the final row of each pass through the existing ownership
contract. Compute must remain admitted across these scheduler subcommands.
The wrapper does not equate scheduling completion with drained memory or compute;
the parent must revoke banks and drain/cancel external traffic on cancellation.

Thirteen focused tests pass through real bank ownership, FIFO and SRAM models,
with reference data checked word by word; three existing scheduler regressions
also pass. Tests cover reuse enabled/disabled, one row, one-word depths,
1,023/1,024/1,026-word pass boundaries, partial tails, high address bases,
command payload mutation after acceptance, independent stalls, reset/restart,
zero/overflow refusal and cancellation in admission/reservation states.
Strict Verilator 5.050 lint passes. Assertion-backed traffic results:

| Rows / local columns / K | Streaming fills | Pass-reuse fills | Issue words |
|---|---:|---:|---:|
| 6 / 7 / 160 | 6,720 | 1,120 | 6,720 |
| 3 / 3 / 1024, interleave 1 | 9,216 | 3,072 | 9,216 |
| 3 / 7 / 341 | 7,161 | 2,387 | 7,161 |
| 3 / 7 / 342 | 7,182 | 6,498 | 7,182 |

The last row streams the two oversized passes but reuses the smaller tail.
These are bank-service results, not loaded G2 latency or traffic claims.
Evidence: `results/rtl/weight_pass_reuse.json`. A 1 ns ASAP7 TT CTS12 route is
active for this wrapper plus inner scheduler, with fanout 16 and library slew
limits. Area and timing remain unqualified until that run completes.
The compact/fallback coordinate sequence, runtime-service integration, output
order validation and tail masking remain required before enabling pass reuse
in G2. No additional SRAM has been introduced.

## Compact descriptor fetch sequence

The descriptor cursor and composed BF16 weight transport now expose
`PASS_FIRST` and `COMPACT_PASS_REUSE`. Compact mode emits one copy of a pass
when its packed size is at most 1,024 words; otherwise it emits one copy per row.
Each tail pass is checked separately, matching the pass scheduler's mixed
reuse/streaming policy. Compact mode requires pass-first order. Generation,
sequential external fetch addresses and burst indices keep their existing checks.

The cursor captures total remaining weight words and full-pass size during
existing admission stages. Full-pass eligibility uses a constant depth bound;
tail eligibility uses the remaining-word count. Advancing a pass subtracts its
size. No per-coordinate division, multiplication, or extra cycle is introduced.
The arithmetic/future operand cursors continue to visit every output row;
only the fetched-weight cursor omits retained copies.

Nine cursor configurations and 24 composed transport configurations pass,
along with 13 bank-scheduler regressions. Transport coverage includes N53,
K80/K160/K342, bursts of 1/32/512, stalls, malformed requests, strided byte
addresses, masked lanes and mixed oversized passes with a reusable tail. The
byte oracle now depends on higher address bits as well as low bits. Strict
Verilator lint passes with compact mode enabled. Evidence:
`results/rtl/compact_pass_weight_transport.json`. A current compact-mode 1 ns
ASAP7 TT CTS12 route is active, using 10% slew repair margin with unchanged
fanout and library transition limits. Runtime and output integration remain open.

The preceding containing transport route with 10% slew margin now passes all
reported checks at 1 ns: 6,141.480 um² cell area, +0.0169131 ns setup and
+0.0361992 ns hold slack, zero slew/cap/fanout/DRC/antenna violations. This
qualifies the pre-compact transport configuration only. Source snapshots are
retained in `bf16_weight_transport/compact_fetch/`; all source and seven artifact
hashes match `line_extent_slew10_route_audit.json`. No extrapolated frequency or
current compact-mode closure is claimed.

## Initial pass scheduler route identifies handoff path

The wrapper plus inner scheduler completes its first 1 ns ASAP7 TT CTS12 route
at 1,377.010 um² cell area, setup -0.129225 ns, hold +0.0524116 ns and one fanout
violation. This fails acceptance. Current-source and seven retained artifact
hashes are verified in `weight_pass_scheduler/initial_route_audit.json`.
The critical path runs from inner replay selection through tile extent to
`issue_base[19]`. Next work is a registered tile handoff to separate extent
selection from logical issue-address advancement, including correct stall,
pass-transition and final-completion ownership. The target remains 1 ns.

## Registered pass-tile handoff

The pass scheduler now captures tile bank, ownership tag, retain flag and word
count in a one-entry elastic register before logical issue-address advancement.
That separates the measured replay/extent selection path from the issue-base
adder. The stage accepts a replacement on the same edge as consumption. Payload
registers use ownership validity rather than a reset tree. A pass-drain state
holds command ownership until the final staged tile is accepted, before moving
to the next pass or publishing scheduling completion.

Fourteen focused tests pass, including a new final-tile stall, exact completion
count, clear of a held tile and restart. A deliberate early-completion mutation
is rejected with `lost stalled final ownership`; evidence is retained in
`results/rtl/weight_pass_early_completion_mutation.json`. Strict Verilator lint
passes. Matched before/after simulations of all twelve bank-service workload/
reuse configurations preserve fill counts, outputs and total cycles under the
same stalls. The counters include the final restarted operation and fixed drain
check, not inference latency. Evidence: `results/rtl/weight_pass_tile_handoff.json`.

A new 1 ns ASAP7 TT CTS12 route is active with unchanged transition/fanout limits.
No timing or area improvement is claimed pending that result. The failing
baseline's source is retained under `weight_pass_scheduler/tile_handoff/before.sv`
and its audit now binds to that snapshot. Runtime/output integration and loaded
G2 measurements remain required.

## Runtime pass-service composition

The runtime operand service now selects the pass scheduler and pass-first future
cursor together with `PASS_FIRST=1`; row-first scheduling remains the default.
Its existing `REUSE_WEIGHT_ROWS` switch selects pass reuse in this mode. The
LQ8 array exposes a matching `PASS_FIRST` parameter to all lanes. Cluster-level
activation is deferred until output validation and tail-mask schedule agree.

Four composed runtime tests plus the existing service lifetime regression pass.
The tests connect the real object-memory transport, both SRAM banks, auxiliary
queue and operand join. An independent issue-address oracle verifies every
returned activation, scale and weight bundle. At three rows/N53/K160, pass reuse
fetches 1,120 words for 3,360 issues versus 3,360 fetched words when disabled.
At K342, mixed streaming and tail reuse fetches 6,498 rather than 7,182 words
for 7,182 issues. Independent stalls, strided object bytes, tail masks, retained
command ownership, cancellation and restart are covered. Evidence:
`results/rtl/runtime_pass_transport.json`. This is a composed input-service test;
it does not run pass-first loaded G2 arithmetic or its output writer.

The default loaded G2 strided-object regression still passes with 2,234 outputs,
295 writes/acknowledgements, 105,552 campaign cycles and 17,596 first-operation
weight bytes. Source hashes match. Pre-change loaded evidence and RTL snapshots
are retained under `results/rtl/before_runtime_pass_integration/`.
Verilator 5.050 elaborates the enabled runtime service without warnings; array
elaboration succeeds with existing width warnings in the arithmetic sources.
Neither result is a new physical qualification. The pass-scheduler handoff and
compact transport physical runs remain active.

## Loaded pass-first G2 integration

`RUNTIME_PASS_FIRST=1` now selects pass order consistently in the array, runtime
service, compact weight transport and output writer. It requires runtime object
reads and writes. The writer retains pass/row address and byte-offset origins,
checks each lane-local address against pass/row order, and maps to descriptor
strides. Existing unique row-tail addresses remain valid: final-column outputs
arrive in row order during the final pass. Legacy defaults remain unchanged.

The loaded M6/N53/K160 strided-input/output campaign now passes with 2,234 exact
outputs and 295 writes/acknowledgements in both schedules. Matched current-source
results: row-first 708,336 campaign cycles versus pass-first 203,111 (71.33% fewer).
First-operation weight fills drop 6,720 to 1,120; object bytes drop 207,336 to
34,556 (83.33%). Activation fills rise 2,496 to 2,880 (15.38%), exposing the
loop-order locality tradeoff. These are fault/recovery campaigns, not model
inference latency. Evidence: `results/rtl/g2_pass_first_comparison.json`.

The bench independently computes residency in the selected order and checks
exact weight-fill counts. Its final-output stall now selects the penultimate
scheduled result; the old row-major address arrived before the final pass and
caused a testbench deadlock. Numerical results, output gaps and tail masks,
queued abort, pending-read abort ownership, wrong-generation responses,
auxiliary faults, final-write error, object-binding failure and recovery pass.
Ten standalone writer tests cover both orders and BF16/FP32 output, bounded
strides and acknowledgement faults. Pass-first writer and complete current G2
1 ns physical characterization runs are active. The integrated launch config is
`configs/hardware/g2_pass_first_physical.json`; all launch source hashes are
retained. Broader shape/format qualification and all-target optimization remain.

The registered pass-scheduler route completes at 1,424.520 um², setup -0.105825 ns,
hold +0.0528268 ns with one fanout violation at 1 ns. It remains unclosed. Compared
with the initial route, setup improves 23.4 ps while area rises 3.45%. The critical
path now runs from inner replay to inner tile-base advancement. Source/artifact
verification is retained in `weight_pass_scheduler/tile_handoff_route_audit.json`.

## Compact transport closure and bounded tile increment

The compact-pass containing weight transport now passes all reported checks at
ASAP7 TT 1 ns, CTS12 with 10% slew margin: 6,324.760 um² cell area, setup
+0.0728253 ns and hold +0.0320716 ns. Source and seven retained artifact hashes
are verified in `bf16_weight_transport/compact_pass_route_audit.json`.
This qualifies the compact input transport block, not integrated G2.

The next scheduler candidate applies bounded carry splitting to tile-base
advancement: a ten-bit low sum and parallel upper increment replace the full
32-bit adder after replay extent selection. It adds no cycles. Ninety-three
bank, replay and runtime-composition tests pass, with strict Verilator lint.
The 1 ns CTS12 route is active. The pre-change tile scheduler is retained in
`weight_pass_scheduler/split_tile_address/before.sv`, also binding the integrated
G2 launch and the earlier scheduler routes. Timing benefit remains unproven.

Matched current-source M6/N53/K80 loaded campaigns also pass both schedules,
with 2,234 outputs and 295 write acknowledgements each. Weight bytes remain
17,596; activation fills rise from 720 to 1,440 with pass-first order. Campaign
cycles change from 105,552 to 99,777 (5.47% fewer), while the cumulative first
successful completion counters are 13,734 and 13,600. These are bench counters;
abort positions and resulting work differ, so the aggregate reduction is not
an inference-speedup claim. Evidence:
`results/rtl/g2_pass_first_resident_shape_comparison.json`.
This confirms the need to qualify locality across shapes and memory-service
rates before selecting a default policy. Larger-than-pass-capacity behavior,
broader formats/targets and complete current-source physical qualification remain.

## Loaded oversized-pass qualification and operation timing

The loaded M6/N53/K342 strided-object campaigns now pass in both schedules,
including 2,234 exact outputs and 295 write acknowledgements each. The full
three-column passes occupy 1,026 packed words and therefore stream each row;
the one-column 342-word tail replays. This verifies mixed reuse/fallback through
real dispatch, arithmetic, output writes, faults and recovery, beyond isolated
bank/transport tests.

| Measurement | Row-first | Pass-first |
|---|---:|---:|
| First-operation weight fills | 14,364 | 12,654 |
| First-operation weight bytes | 438,840 | 404,340 |
| First-operation activation fills | 7,512 | 6,156 |
| Median successful-phase cycles | 211,545.5 | 200,641.5 |
| Full fault/recovery campaign cycles | 1,498,279 | 1,421,966 |

The median successful-phase reduction is 5.15%. New counters measure each phase
from kick to program done, including modeled memory stalls, output backpressure
and explicit drain acknowledgements. They separate successful operations from
abort/fault work, but do not represent whole-model inference latency. Source
manifests match and all current hashes verify. Evidence:
`results/rtl/g2_pass_first_oversized_comparison.json`.

The test watchdog now scales with admitted weight issue count for deeper
campaigns; small workloads retain the previous limit. The K342 runs require
14–15 million simulated ns for the complete fault/recovery sequence, exceeding
the old fixed 10-million-ns cutoff. Exact output, traffic, fault and recovery
assertions remain in force. The pre-instrumentation bench is retained at
`results/rtl/before_phase_latency/tb_a3_g2_runtime_program.sv`.

The pass-first output writer now passes all reported ASAP7 TT checks at 1 ns,
CTS8: 1,682.200 um² cells, setup +0.0263588 ns, hold +0.0508038 ns and zero
slew/capacitance/fanout/DRC/antenna violations. Current source and seven artifact
hashes verify in `output_writer_handoff/pass_first_route_audit.json`. Compared
with the recorded row-first writer's 1,491.180 um², pass scheduling costs about
12.81% additional cell area. Both configurations meet the tested period; this
is a quantified schedule-support cost, not an area reduction. The scheduler
split-increment route and integrated G2 characterization remain active.

The K342 outcome also bounds the current architecture: most full-pass traffic
still repeats once a pass exceeds bank capacity. Future improvements must
consider narrower adaptive passes or explicit depth tiling/accumulator budgets,
including lane utilization and activation traffic, rather than treating this
fallback as an efficiency endpoint.

## Independent pass width preserves reuse without shortening arithmetic

`PASS_COLUMNS` now controls the lane's column interleave independently of
`ADDER_STAGES`. The array and cluster propagate it consistently to execution,
future operands, bank scheduling, object transport and the output writer. The
default remains the adder depth; the loaded runner exposes pass widths 1/2/3
for pass-first mode. Accumulator recurrence wait remains tied to actual adder
latency. Narrower passes can insert issue bubbles but fit deeper whole-K passes
into the existing banks without a partial-accumulator spill or extra SRAM.
This is static configuration, not an automatic per-command selection policy.

Forty-three lane tests pass, covering both orders, K1/K4/K160, pass/adder pairs
1/1, 2/2, 3/3, 1/3, 2/3, 5/3 and 7/3, with exact signed FP32 accumulation,
scales, stalls and reset recovery. Evidence:
`results/rtl/lane_independent_pass_width.json`.

Matched loaded M6/N53/K342 pass-first campaigns, both with the unchanged
three-stage arithmetic pipeline, show:

| Measurement | Three-column pass | Two-column pass |
|---|---:|---:|
| Median successful-operation cycles | 200,641.5 | 67,785.5 |
| Full fault/recovery campaign cycles | 1,421,966 | 489,896 |
| First-operation weight fills | 12,654 | 2,394 |
| First-operation weight bytes | 404,340 | 73,140 |
| First-operation activation fills | 6,156 | 8,208 |

The two-column 684-word passes fit retention capacity. Median successful-phase
cycles fall 66.22% despite 33.33% more activation fills. Both runs pass 2,234 exact
outputs and 295 write acknowledgements with identical source manifests, including
abort, fault and recovery coverage. Phase cycles include modeled memory/stalls
and drain, not whole-model inference. Evidence:
`results/rtl/g2_independent_pass_width_comparison.json`. Earlier K342 evidence is
archived under `before_independent_pass_width/` and its comparison rebound.

Current-source two-column integrated G2 characterization at 1 ns is active via
`configs/hardware/g2_pass_columns2_physical.json`. Existing three-column runs
remain historical launch baselines after these RTL changes; snapshots retain
source binding. All-target closure and adaptive policy remain outstanding.

The split tile increment route also completes: 1,429.280 um² cells, setup
-0.0565655 ns, hold +0.0517601 ns, zero slew/cap/fanout/DRC/antenna violations at
1 ns. It still fails setup, but improves the preceding handoff route's -105.825 ps
by 49.26 ps at 0.33% more area and no added cycles. The critical path remains
inner replay/extent to tile-base advancement. Source and seven artifact hashes
verify in `weight_pass_scheduler/split_tile_address_route_audit.json`; no
extrapolated Fmax is accepted as closure.

## Parallel extent selection candidate and explicit partial-row limit

The scheduler's measured replay-to-tile-address path still traversed two serial
minimum selections. The candidate now compares stream remainder, row remainder
and bank capacity in parallel, then selects their minimum with mutually exclusive
masks. Bank extents are ten bits; high stream bits only qualify the narrow
comparisons. No registers, issue bubbles or extra admission cycles are added.
Ninety-three bank/runtime regressions pass, strict Verilator lint passes, and
3,664 independent integer-minimum cases cover equalities, zero, large stream
counts and partial remainders. Evidence: `results/rtl/weight_parallel_extent.json`.
The 1 ns ASAP7 TT CTS12 route is active; no timing/area benefit is claimed yet.

An additional generic partial-row experiment exposed an existing unsupported
composition: 92 issue words with a 31-word resident row stalls on the shortened
last tile because prefetch requires tile extent equal to stored bank extent.
The same failure is reproduced with both the pre-change scheduler and candidate.
Bench and failure evidence are retained in `results/rtl/partial_replay_extent_gap/`.
Current G2 admission and pass scheduling issue complete rows/passes, and their
loaded/composed regressions pass; this does not qualify arbitrary partial-row
replay. Supporting that generic case requires prefix acquisition and correct
release of unused retained banks, or an explicit admission refusal. The limit
remains open rather than silently widening the bank contract during timing work.
The original failing expansion was stopped; its failure is not counted as a pass.

## Parallel extent scheduler closes its 1 ns block target

The completed ASAP7 TT CTS12 route reports 1,380.650 um² standard cells,
+0.0296942 ns setup and +0.0516658 ns hold slack. Setup, hold, slew,
capacitance, fanout, DRC and antenna checks all pass. Against the preceding
split-increment route, setup improves 86.26 ps and cell area falls 3.40%;
RTL adds no cycles. Both current source hashes and all seven retained
artifact hashes verify in `weight_pass_scheduler/parallel_extent_route_audit.json`.
This establishes the tested 1 ns block target, not an extrapolated operating
frequency or integrated accelerator closure. The partial-row limitation remains
open. Existing integrated G2 jobs retain their historical launch sources.

A current-source loaded M6/N53/K512 two-column pass campaign is running to
exercise exact 1,024-word retention capacity, with real strided weight reads,
strided output writes, output backpressure and fault/recovery coverage.
