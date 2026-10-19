# Repeatable native landing/pair leaf

`ot_hbm_svg_landing_pair_native #(.J(j))`, j0..3, is an opt-in four-macro leaf.
Current source is48fa0a785; pre-RTL processing/copy model isbf543d3fb. Legacy
masters remain unchanged. Functional and recursively collapsed fanout proofs
pass; physical qualification remains OPEN. No gate/REVIEW/submit is included.

## Storage, roots and integration

Each leaf composes two `ot_hbm_svc_sm8_landing_boundary_safe` banks J/J+4,
local pair selection, a group-alignment ring, and the ENTIRE selected return
ring including local receiver pointer/read mux/output Q. Its actual storage
macros are two256x256 landing SRAMs and two8x285 dual-clock response SRAMs,
22577.762304um2 total. Each landing macro packs four64-row landing blocks.
Reference masters in the testbench are not part of this inventory.

Three physical clock/reset roots are explicit: pair_hbm, pair stream, and
forwarded cache-phase return. Both native banks in a pair use the same HBM and
stream roots. The old g/4 bank clock mapping must be remapped for J and J+4.
Across four leaves plus cache, this gives four HBM and nine stream trees.
The entire return ring stays inside its source pair; only registered output
Q crosses to the cache input capture. No select feedback is exported.

Production shapes remain LBANKS4, RESPONSE_DEPTH8, packet285. Native ingress
uses a three-slot285b ring plus pin capture (1140bits/bank), with registered
ready and explicit queued+pending reservations. The new stream processing
stage has one285b packet Q, twenty real11b local field Q copies and aligned
reserve/read/control Q (at most544source bits/bank). Local copies capture
reserve-valid/LB and packet LB/row at the SAME new stream edge. Epoch/count/
seen storage is ownership-gated: reserve initializes all fields before valid
permits identity acceptance. Only validity/sticky/control resets.

The processing stage preserves reservation/packet ordering. A pending invalid
stage inhibits the next FIFO pop before sticky updates, preserving the prior
fatal-packet admission behavior. No new SM credits or ready pins are added.
The actual four-slot return ring is1052bits (263b tagged words);44six-bit
slices, last5bits, bound receiver-pointer loads. Its data carries256payload,
ordinal3,valid1,phase3. Group metadata is an actual four-slot4b ring (16bits),
not a delay chain. No runtime-indexed flop object exceeds2kb.

## Ports and validity

The leaf has632inputs and273outputs (905total). Bank b0/1 means J/J+4.
HBM pins are in_data[b*285+:285], in_v[b], in_ready[b], overflow[b]. Pair pins
are shared reserve_v/bank/epoch/total and stop, separate read_v[b],
read_bank[b*2+:2],read_row[b*6+:6], ordinal3 and group_valid. Completion-valid,
completion-bank and fault are exported separately from each bank's native Q.
Return-root output Q is data256+ordinal3+valid1+phasefault1=261bits. All273
output bits trace through optional INV/BUF cells to actual FF Q.

Group valid remains INDEPENDENT of both read enables, stop and selected bank.
Partial/final groups can leave unused lane data held while all pair envelopes
agree. The parent metadata ring carries the mask and ignores unused data.

## Exact latency and compiler price

The new processing stage is an explicit extra stream edge. It is distinct
from the existing native read-output register.

| Capture edge after external launch E0 | Event |
|---|---|
| E1 | Native pin capture; group metadata ring write |
| E2 | Real processing packet/selector/control Q |
| E3 | Actual landing SRAM read |
| E4 | Native data-output Q and four-edge group metadata Q |
| E5 | Pair captures both native outputs and ordinal |
| E6 | Registered local selection |
| E7 | Write tagged selected data into actual return ring |
| E8 | Local forwarded return-root output Q |

Measured request-to-leaf-return delay is exactly8edges, previously7. Cache
capture/rotate2/rotate1 adds3, so request-to-final-cache is11edges. Earliest
valid after balanced raw reset is10, previously9. HBM ingress timing is
unchanged. Relative to the original bare landing master, reserve takes2extra
stream edges, completion-consumer visibility2, and read data3. FIFO stop
admission retains the existing pin edge; accepted work/read stop is aligned
through the processing stage.

The accepted CONSERVATIVE compiler allowance is native11 = ceilHBM4 +reserve2
+completion2 +read3. Regional return remains7 =pair2+ring2+cache3. Whole
prefetch is therefore18, priced ONCE in the shared compiler/model. Earlier
native9/whole16 estimates counted only the extra output-path edge and are
superseded. Reducing18 requires a causal whole-schedule overlap proof. Parent
owns compiler, mask/group metadata, OPEN labels and whole-service integration.

Bench clocks are HBM1024ps, pair834ps phase30ps, return834ps phase10ps. The
pair-to-return ordinary setup interval is814ps with20ps next-launch offset.
No ring phase/epoch argument authorizes MCP or false-path exceptions. Actual
logic depth, wire delay, root insertion, TT setup and FF hold remain OPEN.

## Native reset graph and FIFO qualification

Kept real one-FF asynchronous-clear/D=1 phase modules form two native release
levels, with balanced first-stage copies shared by local branches. Raw paths
have no buffer/inverter cells before the first FF. Actual mapped profiles:

| Root | Raw-reset FFs | Max first-Q branch FFs | Max branch-Q owned FFs |
|---|---:|---:|---:|
| HBM | 4 | 19 | 6 |
| Pair | 2 | 24 | 13 |
| Return | 2 | 23 | 9 |

All first and second stages have D=1 and the actual native root clock. Raw
assertion clears first Q, branch Q, then owned controls asynchronously. E1
raises first Q while branch stays0; E2 raises branch Q; control starts E3.
The bench independently witnesses all74/47/45 branches with0/0/0errors and
exercises each domain releasing first. Feed raw resets to the leaf, and its
phase0 signals to the bank/slice second stages; never cascade another landed
reset into phase0. Assertion is balanced across participating roots.

The COMPLETE leaf is not uniformly two-level. Each unchanged response FIFO
retains both_reset=hreset&&sreset. That AND asynchronously clears both FFs of
its write and read reset synchronizers (four internal FFs/bank). Their q1
clears18 FIFO functional FFs/domain. Release adds two local synchronizer edges
after both native resets release, then the existing online/Gray CDC
qualification. Both AND roots, internal clocks/D/clear pins and final consumers
are explicitly enumerated in the complete mapped reset audit. Canonical tool/
root acceptance, reset-clear slew/reach and clock spread remain OPEN.

## Actual-SRAM and recursive-load evidence

Fleet Verilator5.050 final source48fa0a785 passes J0..3 independently: each has
3264payload groups+24masked groups,829admitted packets,12completions/bank,
1032group-valid cases with selected read disabled, exact8/8edges,firstvalid10,
and twelve64group/64edge windows (32payload bytes/edge). It covers all
ordinals0..271, four landing blocks, bubbles, full/stopped bursts, wraps,
occupied resets and three unequal release orders. Correct-epoch duplicate,
unowned block, bad epoch, out-of-count row and wrong ordinal guards pass.

The original-master miter independently scores externally admitted packets
and compares core ready/order, completion/fault and actual SRAM read data. Its
outputs are aligned by the explicitly priced one processing edge; ALL active
comparisons remain. Held payload Q captures unconditionally through reset,
matching native data behavior. Final miter errors are0/0 for every case.

| Mutant | Mechanism | Errors (miter remains0/0) |
|---|---|---:|
| 1 | Wrong pair selection | 3263 |
| 2 | Metadata one edge early | 4276 |
| 3 | Wrong return ring phase/slot | 6653 |
| 4 | Metadata one edge late | 4264 |

Full Yosys+dfflibmap+ABC833.333ps mapping retains local hierarchy during mapping,
then removes module AND cell keep_hierarchy and flattens WITHOUT opt_merge.
The audit recursively traverses actual BUF/INV cells, including FFQN→INV→Q,
and counts unique terminal(cell,type,input-pin) loads. It exempts only declared
clocks or actual sequential clock pins; a combinational C pin is not a clock.
Maximum loads are SRAMQ21, FFQ28, combinational25, input ports11, resets24.
Only the three clocks exceed32. Every driver, source hash, sink and reset
equation is retained in the evidence. There are no unknown cells or unresolved
paramods. Actual FF count7695 =6845unreset+850resettable.

The earlier direct-only max27 claim was withdrawn: its immutable327ef3481
netlist collapses to SRAMQ329, reserve-control FFQ91 and return-pointer FFQ34.
Inverse helper cells were not state replication. A same-edge232b shadow array
plus179read-copy bits/bank was considered, but it adds HBM-flop-to-stream-Q
walking-phase soft CDC paths with no permitted timing exception. The selected
real processing stage adds no new CDC path and prices its edge explicitly.

Witnesses are under `native_pair_evidence/functional_48fa0a785`: final bench,
full census/all-driver collapsed audit, strict reset audit, immutable baseline
failure and initial reference-warmup diagnostic. Older evidence is historical.

## Physical checklist

Measured standard-cell area is3502.30554um2. Within the proposed380.16x198.72
outline, the four macros remain at43.2-lattice origins (43.2/259.2 columns,
43.2/129.6 rows). A full-width16.2um band y99.9..116.1 has56.87% cell density;
the remainder of the43.176um macro gap is real routing/clock/PG access space.
No arbitrary padding or canonical macro/contact edits were made.

Before any physical gate: canonical strict-reset tool/root acceptance; actual
pin-to-Q/macro placement and<=405um reach; ordinary directed TT setup/FF hold;
clock/pin-flop spread and reset-clear slew; canonical macro face/PG/via audit;
and parent whole-service causal early/late metadata tests/shared prefetch18
integration remain required. This leaf does not imply whole-SVG closure. Legacy packed-row assembly is outside this leaf; the current native cache
component is qualified separately by its owner.
