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
