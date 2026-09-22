# G2 descriptor-driven input transport

Status: implementation plan, 2026-09-22. This document does not claim the input
transport is implemented. It defines the next integration change following the
bounded output writer.

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
