# R6 four-quarter parallel reduction: source model, build HOLD

Identity is image6 / k_layer6 / price4 / q_norm.ss occurrence0. Original
A[46336..47615] has1280 FP32 words shaped8x160; authentic R[49920]
is0x40a2a1ed. Preserve1479.31→1661.49 stream edges, base165 and every original
operand. No RTL, compiler, numerical replay, synthesis or gate was run or changed.
Pinned baseline04423a7d8; pretree inspected at1dad69123 through this own worktree.

## Actual producer/receiver coverage

Four independent quarter control words are necessary per issue group. Each of
four groups delivers128/32/128/32 live words to quarters0/1/2/3 respectively.
Full quarters use native VM ports0..7, short quarters0..3:24 genuinely touched
bank identities and160 A sectors. The four groups together cover all1280 words.
Physical production graph has512 lanes, including192 inactive for this record;
retaining them is conservative. A320-lane/24-bank cut is NOT demonstrated.

Baseline pgslice captures1742-bit control separately into32 lane replicas; the
LEAF uses emit/offset-bank/vb/liveness while backend cp/cm/ca/ci/cs/ce/co fields
are consumed at different edges. Therefore four adjacent complete issue words
are not automatically legal. The candidate control compiler must lower a
per-edge/per-stage ledger, preserving each group's fields until its last real
consumer. Two offset banks require explicit bank-load/reuse proof. Group0
controls cannot be held as a substitute for groups1..3. Backend idle signatures
must not replace an older live group's AA/mul selection.

The source square path exists as M1_AA=2 in static_lane; current R6 lowering
leaves BYP and reducer has no multiply. Candidate uses cp_m1=AA at PRE and
matching cm_m1 through M1 output, all later stages BYP, dst NONE and no output
rounding. It must prove identical mul(A,A) rounding and original absent-reader
identity treatment on every physical lane. This is source availability, NOT a
numerical proof or implemented lowering.

Pinned pgslice outputs only selected slice_x and qcore selects one of four
slice_x through two command stages. Existing pretree source instead accepts
all32 local ro_x/ro_v and emits only TWO fixed16-word subtrees per slice. Its
quarter join emits one128-word subtree. It has NO fragment/chunk export port.
Neither source therefore currently implements the exact parallel R6 path.

## Candidate parallel path requiring ROOT approval

Use four live square lanesets in parallel; split pretree before its irreversible
fixed quarter collapse. Keep original sequential chunk8 FP32 chains. Export
only canonical aligned dyadic fragments, tapping the4/8/16-chunk subtree levels
with registered, command-tagged outputs. Quarter2's middle8-chunk fragment
uses local chunks4:12: it is NOT an existing quarter-local balanced subtree.
It needs a real extra node combining local4:8 with8:12, plus explicit
4-chunk tap ports. Existing halves0:8/8:16 cannot substitute. Full quarter0 in odd groups must emit
TWO8-chunk fragments instead of an invalid16-chunk sum. Quarter2 must emit
three fragments. Unused candidates remain invalid, never substituted zeros.
The following half-open chunk ranges are canonical:

|group|quarter0|quarter1|quarter2|quarter3|
|---|---|---|---|---|
|0|0:16|16:20|20:24,24:32,32:36|36:40|
|1|40:48,48:56|56:60|60:64,64:72,72:76|76:80|
|2|80:96|96:100|100:104,104:112,112:116|116:120|
|3|120:128,128:136|136:140|140:144,144:152,152:156|156:160|

This is26 fragments:2x16+8x8+16x4=160 chunks. Append canonical +0 subtrees
160:192 and192:256. A dedicated static global join connects ONLY siblings of
equal size and aligned base;28 fragment/zero leaves require27 joins. Carry
exact group/base/size identity; reject missing/duplicate/wrong epoch entries.
Do not use the one-operand reducer as an unpriced multi-input collector.

One finite26-entry holding bank can retain the fragments without storing all
160 chunks. Reservation at48 bits/entry (FP32, valid, group2, chunkbase8,
size5)=1248 bits, plus separately priced launch/reset/fault state. The48-bit
bound is a MODEL assumption; actual identity protocol may enlarge it. No
unpriced indexed5120-bit chunk array is allowed. No new hardware user-context
multiplexing is assumed. Fixed starts and valid checks replace readiness.

The final scalar must enter an actual source-defined R path, RF write/tag,
class5 RF drain and native VM write to49920, then descriptor retirement AFTER
visible commit. Existing reduce_static EXPORT alone does not perform that
whole chain. Exact commands, tag convention, RF relay length and host bridge
calendar remain NULL; no O descriptor or invented direct scalar VM write.

## Latency and bandwidth ledger

Original182.18 stream edges equal136.635 serial edges at3:4 (834/1112ps).
Serialized512-selection ingress costs682.667 stream edges and is rejected
ONLY as that fallback. Parallel delivery removes that particular bound.

At existing pretree LAT6+OPR1, canonical chunk recurrence7 adds costs49 serial
edges; padded256-chunk tree has8 levels costing56. Thus final squared word to
root has105 serial arithmetic edges before pin/output/global landings. Different
fragments may arrive early, but last nonzero leaf still traverses its canonical
8 levels. This leaves31.635 serial edges for ALL paid fill/fetch/square/R/host
work under the original deadline. Native18/15 FILL commits+21 serial; linear
MLAT4 lane comment prices25 edges after emit, with actual fetch/pin options
requiring source calibration. If FILL begins at paid start and those25 edges
are disjoint after readability, even optimistic21+25+105=151 serial =201.333
stream exceeds182.18 BEFORE R retirement. This is a CONDITIONAL rejection of
this specific non-prefetched LAT7-node implementation, not universal
infeasibility. Actual source may prefetch in a legitimately priced preceding
window, or a separately closed faster arithmetic path may change the bound.
Neither is assumed. Current schedule/deadline feasibility is UNPROVED.

At least64 sectors in each full quarter occupy8 native port rounds; short
quarters require16 sectors/4ports=4 rounds. Per-bank exact addresses, native
READ_RETURN18/WRITE_RETURN15 overlap and3:4 bridge phase must be enumerated
before any schedule claim. Count all160 original A sectors, actual RF export
and scalar native write; forbid fill/lane-write and inject/drain collisions.
These are functional source edge counts, not physical SRAM CQ/hold bounds.
No nominal Elmore/FO4 value supplies a validated earliest CQ; native
same-corner clock/slew and full setup/hold qualification remain open.
Host install/config and descriptor rearm must retain true phase; no cached
R23 model or arbitrary additional launch episodes.

## Hardware cost and physical admission

Conservative full512-lane path reuses the512 existing multipliers; no new
square multiplier is assumed, but actual source activation/control has cost.
64 chunk chains need448 FP32 adder nodes; quarter local tree60 nodes gives
508 existing-style nodes. Quarter2 middle8 needs one extra node; global static join adds27 nodes,
for536 total if all fixed nodes retained. Arithmetic pipelines, errors, modes,
valids, clock contacts and source cells must be counted from generated source;
no area is inferred from node count. Global27 plus quarter2 one added node are NOT zero-cost.

Each chunk's six nonzero skew delays are7,14,21,28,35,42 edges. Existing ring
source uses D-1 entries of33 bits:141x33=4653 bits/chunk,297792 bits across64
chunks, plus12672 delay-output FF bits (64x6x33),16896 input payload/valid
capture bits and node pipelines. This indexed storage needs real SRAM banking,
read latency/masks/OLD semantics and reset-pointer proof; many individually
small rings do not establish an admissible parent. Physical bits/area/clock
of SRAM replacement are NULL until a port-exact legal macro mapping exists.
Fragment1248-bit storage is extra, as are taps/registration/routing landings,
identity checks, controls and reset trees. Existing pretree route does not
qualify this changed graph or these memories.

Source FF count, SRAM inventory, synthesized area, clock load, all-driver
BUF/INV-transparent fanout, stage depths, full-face<=6/um geometry,405um reach,
PG/contact coverage, parent slot fit and neighbour TT/FF clock contract are
NULL. All new pins register; reset preserves the actual inherited lifetime
and2-stage face boundary; no functional ties or data timing exceptions.

ROOT decision requested: retain this as MODEL-ONLY. First resolve the legitimate
prefetch/start accounting and faster-node feasibility, exact stage-control
ledger, fragment-export mechanism and authentic R retirement. Then map real
ring SRAMs and price full clocks/area/host calendar. No build until a concrete
schedule meets or honestly reprices the original182.18-edge record window.
