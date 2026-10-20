# AHUB6 measured redesign admission, 2026-10-20

The original g4 gates remain active and are not approved. Their source revision is
6feabc28437514b815f6954cbf2351335a50ad77. No gate result is fabricated here.

Read-only clock replay completed on ot-epyc9, unit oth-ubuntu-655021-1792476664,
from g4a 4_1_cts.odb. The copied per-flop TT census proves the late tail:

| Core-clock component | Flops | TT arrival ps |
| --- | ---: | ---: |
| u_rx | 33 | 607.96–800.17 |
| u_ry | 68 | 631.56–841.58 |
| u_core | 2535 | 562.93–594.85 |
| u_io | 386 | 563.03–600.70 |

All 101 late relay flops are missing from the core fence prefix table. The
LP region record explicitly assigns u_rx and u_ry to c. The reciprocal child
flop reference adds 238.7 ps to its 298.47 ps raw pin arrival, giving 537.17 ps.
The remaining core soft mass spans 37.77 ps; fixing fence membership alone
would address the observed clock tail, but does not satisfy native admission.

Native replay on the exact mapped 1_2_yosys.v completed on ot-epyc9 unit
oth-ubuntu-3896271-1792481779 using the original snapshot textbook_lint parser,
collapsing BUF/INV trees and excluding clocks/constants. native_over32.json
contains ALL 265 driver violations, not a thresholded top-eight summary.
Worst: u_io.start 549, u_core.start_b 293, u_io.em_w 292,
u_core.u_rr.rst_n[1] 168, rst_n[4] 128. Most remaining violations are
landing-writer rq roots (CHUNK_BITS=8), with 56 loads per writer chunk.

## Structural successor requirements

1. Include u_rx/u_ry and every LP-record-owned soft child in its regional fence;
   compare fence ownership against measured mapped sequential instances.
2. Split landing chunks from eight to two data bits, regenerate ALL reset-leaf
   counts/slices and valid-vector dimensions; preserve D4/K2 and all edges.
   A writer contains data and epoch/reset consumers, so CHUNK4 is insufficient.
3. Replicate command-start and export enables as kept, uniquely parameterized
   same-edge copies, distributing consumers in groups at most 16 bits to allow
   mapped enable logic. Do not add an unpriced start stage.
4. Replace the five broad core reset roots with same-depth local leaves;
   reset_n[1]/[4] are actual violations, never README waivers.
5. Partition zseen clears and decode consumers, then remeasure ALL mapped
   combinational roots, not only flop drivers. Anonymous roots currently reach67.
6. Run native census BEFORE a layout gate, and prove behavioral PASS plus mutant
   witnesses using Verilator5.050. No successor is admitted until all violations
   are resolved. No new kit gate or route was launched by this evidence packet.

SAFE checklist: pins/reach/depth/storage/schedule inherit g3 only as hypotheses;
fanout FAIL measured265, clock FAIL measured304.4 ps child-inclusive spread,
floorplan ownership FAIL measured101 missing soft flops. Reset fanout FAIL.
A full kit review and current measured evidence remain mandatory.

## Partial source implementation (not admitted)

`tools/qwen_kv_die/ahub6/mk_source.py` generates the opt-in
`qkd_ahub_static_dw_g6_lp` parent. Its thirty landing writer/reader chunks
are two bits. ALL associated valid-vector widths, reset-leaf counts and slices
change together; D4/K2 and the data/command/reset schedule remain unchanged.

The first synthesis-only probe rejected the enlarged aggregate reset-root fanout
at elaboration. The corrected source uses seven uniquely parameterized kept
same-edge root copies, one per region. `rst_n` drives seven D pins. Each root
then drives only that region's forest branch count (core <=32). No depth was
added and no shared helper was relaxed. This correction is an implemented source
change, but command/export enables, core internal resets and combinational roots
still require work. Do not submit this partial candidate or cite it as qualified.

Fleet synth-only probe v2 uses the original source snapshot mounted read-only,
with ONLY the generated parent file overlaid under its old module name for
compatibility with the baseline synthesis config. The top rename is recorded
in the scratch overlay. No live Claude file was modified. Output is ep9
`/srv/opentallas-scratch/codex/kv-ahub6/chunk2_work_v2`. Collect the new mapped
netlist, count every driver, and complete the remaining source fixes before any
gate. Exactness benches and mutant witnesses remain owed on the changed source.

## Control/state structural successor, staged v3 through v9

Private qkd_ahub6_controls.sv is generated from the unchanged g3 safe source.
All new register copies capture on the existing edge. It distributes command,
identity, calendar, export enables, core clears, and same-depth reset leaves.
Z seen/write storage is split into sixteen-bit local components. LM and RZ
capture words are split into eight-bit kept components. Decoder arithmetic is
partitioned into nine semantic groups, with eight same-edge age copies.
No added data/control cycle or timing-constraint relaxation is implemented.

Source inspection found that ot_rst_pipe has two asynchronous-assert/release
synchronizer stages PLUS two plain regional stages. The initial private v4-v6
reset implementation had only the plain stages and is NOT eligible for adoption,
even though its late-command miter passed. v7 restores all four stages. The
stronger test drives commands during reset release and covers T=1/128/513/1024/
4096/8192. It passes 11991 comparisons and rejects both a bad command copy and
a mutant removing the synchronizer stages. This reset correction precedes any
layout gate. The final v9 source additionally passes the ordinary core miter;
full die-calendar exactness is running separately.

Mandatory census tool source94de8573f reads the seven exact std/child Liberty
files extracted from actual Yosys Executing Liberty frontend lines. It uses
Liberty functional BUF/INV transparency and checks every dynamic driver/reset/
macro data contact, without exceptions. v7 remains FAIL42/max133. All broad
reset violations are gone; remaining mapped fanout is in control/arithmetic and
wide capture cones. The133 root was traced to RZ128 capture and67 roots to LM32
capture. v8/v9 partition these actual endpoint groups, rather than relabeling
buffers. Native summaries preserve ALL violations, exact source/Liberty hashes,
and full remote receipt hashes; driver_counts is omitted only to avoid a22MB
inline file. The admission hook itself consumes full receipts.

Measured cost: baseline mapped20527 flops/82607 cells; partial v5 mapped44389
flops/168423 cells. Much of the increase is independent epoch/reset state for
narrow landing chunks. These are intermediate measured counts, not final area
or a closed view. Macro count, payload widths, D4/K2, seven clock regions and all
compiler latency deltas remain inherited. Model cycle delta is0 at this stage.

No source in this packet is approved for a layout gate until native count0,
complete exactness witnesses, reset binding, and a new physical checklist.


Final structural source and provenance (01:46 PT)

The actual g6 top now passes mandatory full native admission: max32, zero
violations, all seven loaded std/child Liberty identities pinned. The explicit
same-edge reset roots are u_lpr_root_r0..6, included individually in the c fence.
Exact receipt: receipts/native_actual_final2_g6_summary.json, source hashes beside
it. The full report remains on ep9 with a pinned SHA256; no partial direct-net
census is accepted. Existing lp.py actual-source audit reports15 landings,
42 reset hops and no crossing failure.

Canonical LP is really regenerated from immutable flat inputs, not relabeled:
canonical_lp/qkd_ahub_static_dw_g6_lp.sv and its complete record. CHUNK2 canonical
LP correctly refuses its original aggregate reset root61 loads. mk_source.py
postprocesses the genuine CHUNK8 artifact into CHUNK2, seven same-edge root
copies, and private IO/core controls. Its derivative record truthfully identifies
the postprocessor. The typed validation profile replays canonical RTL+record,
checks the full record against an explicit implementation delta, compares every
actual parent instance/parameter/connection and assignment, runs actual lp.audit,
and verifies all source/generator/effective parameter hashes. Full unchanged
compiler/landing/timing fields remain immutable; implementation metadata is not
claimed unchanged. Canonical-generator relabeling of declared derivatives fails.
The helper is isolated for coordinator review on codex/ahub6-derived-lp-review-1020.

Outer implementation cost is38824 landing FF and1954 reset FF. The latter
includes the original52 scalar pad stages, plus21 for four copies of the IO's
seven-stage pad,1813 forest leaves,61 branches and7 roots. Private controller
state and logic are additionally measured in the final mapped census/area
receipt. The same-depth forest incremental_FFs is1860 vs its14 regional baseline
stages; the six extra root copies and IO pad copies are separately included in
the total. No reset or datapath edge is added. Macro count, payload widths,
D4/K2 and seven region roots remain fixed.

The portable final full calendar bench passed all seven contexts, including8192,
and mutations1/19 failed at concrete interface behavior (source pinned in
receipts/source_m*.sha256). Following canonical-comment/root-instance unrolling,
an exact final2 source rerun is active rather than claiming the earlier byte
hashes match. The private IO/core miter and production reset evidence also remain
in receipts. Full gate, area/fill, current PNG and eight-point physical review
are still required before any closure submission.


Measured final native size (actual source e95402bc netlist)

The final native source maps to44680 sequential cells and172617 standard cells,
24875.959um2 in the actual loaded Liberty areas; every master is priced. The
three repeated area-coupon attempts are diagnostic history only; the accepted
receipt is receipts/area_model_final2.json with missing_masters empty. Named
region areas are c15511.662, w1564.624, e1038.038 and each Z1504.773um2;
742.545um2 of unnamed logic remains for the physical fence walk to allocate.
At the prepared fence sizes, these named areas occupy c32.12%, w22.69%,
e16.15% and each Z23.04%. Assigning all unnamed logic to c conservatively raises
its source estimate to33.65%. These are pre-CTS source estimates, not current
placed fill. Whole-outline macro+standard fill is41.1%; the fixed734.4x540 die
slot and existing face locations determine this vehicle, and the gate must
still validate reach and actual stage density.

The 0.024um macro-origin warnings arise because the inherited child LEFs need
small per-instance track alignment shifts. The current generator checks every
signal pin and chooses the nearest on-track origin; it emits a lattice WARN
when a child requires the shift, rather than hiding off-track pins. The new
parent does not alter child abstracts or waive physical pin checks. Current
PNG, measured clock spread and route quality remain required.


The final classified packet is based directly on main8608a236c and contains the
complete committed paired fixture, so all AHUB6 tests execute in a clean checkout.
The only shared-tool hunks are the typed record dispatch, its validator/tests,
and bounded _materialise support: artifact paths must stay in the source root,
commit bytes must match every identity, and complete replay/source audit runs
before kit regeneration. New tests materialize the real fixture in an isolated
git repository and reject stale committed source and escaped paths. Dynamic LP
and helper paths are explicit in the job archive. No clock-measurement or
source-binding dispatch is changed in this packet.

Exact final2 full benchmark is now terminal PASS (unit oth-ubuntu-510393-1792485569):
M0 passes all seven contexts, M1 and M19 return expected nonzero status with
matching interface failure evidence. Final2 source hashes and transcript are
committed alongside exact native evidence. The normal log's printed g3 tag is
inherited display text in the original test; its DUT module is the private g6
and the source hashes identify that source. No old g3 physical closure is claimed.


Coordinator semantic gate HOLD (01:58 PT)

The earlier individual-vector storage statement is superseded by the complete
family inventory in SEMANTIC_AUDIT.md and logical_storage_audit.json. Core-c
D4 payload storage is5444bits; its replicated indexed epoch/valid history adds
8172/2724bits, for16340 physical history bits in that same writer family.
Implementation partitioning does not waive the2kb SRAM requirement, and the
current FF-based g6 source is diagnostic only. No physical gate is authorized.
A real backend must address both data and metadata history, actual source-bound
writer/reader phase, arbitrary initial SRAM contents, first-valid/reset behavior,
read-before-write and no-same-address-collision witnesses.

The inherited24nm placement shifts are actual changes of macro bbox origins,
which violate the required43.2um origin lattice. They are not accepted merely
because the physical pin-track audit passes. r0_lattice_proposal.json proves a
source-preserving physical alternative: leave every immutable LEF/pin shape and
all requested43.2*k origins unchanged and use R0 orientations. It lists each
actual global pin rectangle before/after, all logical pin→net connections,
LEF hashes and per-layer track results. Mirrored Z0/Z1/Z3 have2/338/336 off-track
signal pin-layer contacts at the requested lattice origins; all five R0 children
have zero. The proposal changes physical pin locations through reorientation
and has not been applied to a kit or routed. No origin/track rule is waived.
