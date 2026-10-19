# Independent MERGE pointer rings: MODEL, implementation blocked

ROOT selected 320 genuinely independent rings: NT4 × MLEV5 × H16,
each eight entries of **33 bits, 264 bits total**. Source is
`rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv`, `ot_hdc_v41x_attn_merge_x`,
SHA recorded in model.json, inherited from storage decision83c2428ca.
No public parameter, default, arithmetic, source RTL or physical kit changed.

## Exact transition and arithmetic boundary

Original `head=ring[0]` is sampled BEFORE the active edge. If `v`, the
shift advances, appending `{fault,value}` when
`store=v&&live&&!fin&&!blk[level]`; otherwise it appends the OLD head.
If `!v`, every entry retains its value. Pointer equivalent is asynchronous
OLD `mem[ptr]`, overwrite that same entry only on store, then advance
`ptr=(ptr+1)%8` only on v. Recirculation performs no payload write.
It needs one asynchronous 33-bit read and one synchronous 33-bit write,
with OLD-on-collision semantics. No SRAM, payload reset, extra data stage,
credits, cancellation, or backpressure is introduced.

The exact existing `qaddf` LAT/F12 instance, `use_?head:0`, input b,
fault OR, tag stages and reduction tree stay untouched in a future
default-off implementation. This gives intended added data edges0,
not a measured whole-token improvement or new FP32 RTL result.

## Bounded local implementation and explicit costs

Each head has three kept one-hot pointer copies of8 bits, each serving
11 payload bits. They rotate identically and share original per-head v.
Per-copy selection Q drives11 read-AND pins and one write-enable-AND;
write-enable drives11 hold muxes; store drives24 enables; v drives24
pointer hold muxes plus its store predicate. Data input bit drives8
entry muxes. Analytical local maxima are therefore12/11/24/25/8,
before exact synthesis/native pin counting. Equal copies require kept
hierarchy and mapped proof that synthesis did not merge them.

Across320 rings:84480 payload FF stay;7680 pointer FF are added.
Read logic:84480 AND2 +73920 OR2, four simple-cell levels
(one AND +three balanced OR). Payload retention:84480 mux2;
pointer retention:7680 mux2; decoded write enables:7680 AND2.
There are320 four-input store predicates (up to960 AND2 plus inversion),
and per-head fin/use inversions. Count all these in mapped area, not just
the pointer FF. Clock load rises from84480 to92160 FF pins for this
storage portion, before reset distribution. No clock-gating savings claimed.
Read output still feeds existing operand selection/FP32 first stage;
four mux-tree levels alone do NOT certify the complete stage <=600ps.
Actual TT/FF cell arcs, reset census, mapping area, synthesis depth,
wire reach, floorplan and parent fit are NULL, not estimated PASS.

For the new7680 reset loads alone a32-way balanced logical tree needs
at least240+8+1=249 distribution FF; this is a LOWER BOUND, not a
proposed safe reset implementation. It neither proves raw async-reset
fanout nor preserves the inherited two-stage release. Replicating async
FFs can move the violation to raw reset. A real source-bound reset
scheme with matched assertion/release must be selected and priced before
RTL. No slot fit or reset-stage waiver is inferred from264-bit locality.

## Executable abstract lifetime proof and its limits

### Cheaper binary-pointer alternative for ROOT review

Three kept3-bit binary pointer copies per head can serve the same three
11-bit groups:9FF/head,2880 pointer FF/clock pins total versus7680.
Each copy decodes8 three-input slot predicates. Without Boolean sharing,
that costs16 AND2 and3 INV per copy:15360 AND2/2880 INV total.
Three-bit increment adds up to960 AND2 and1920 XOR2 total (bit0
inversion already counted), and2880 pointer hold mux2. Read/write data
mux counts stay unchanged. A pointer bit drives8 decoder literal pins
(count through inversion), <=2 increment pins and its hold mux: model
upper bound11. Decoded slot drives11 read-ANDs +one write-enable gate;
store still drives24 enable gates, v only9 pointer muxes +store=10.
Every actual clone and decoder must survive mapping with these bounds.

Select→head worst structural estimate is INV+two AND decode+one data
AND+three OR=7 simple-cell levels, versus4 for one-hot. This is a
depth estimate, not600ps qualification; real first qaddf stage still
needs mapped timing. Binary reduces added pointer FF by4800 and the
new reset distribution lower bound from249 to90+3+1=94 FF. It does
not solve async reset ownership/lifetime. Nominal reset+pointer costs
2974FF versus7929FF remain LOWER BOUNDS, excluding source reset
restructuring. Mapped combinational area and TT/FF delay are NULL;
no MHz, parent-fit or token gain is claimed. Lane lead requested this
comparison; ROOT selection and blockers below remain pending.

An **unreset binary pointer** removes all new pointer reset loads:
three bits have no illegal encoding. Advance only on v, whose source
control resets; freeze while invalid/reset. Arbitrary initial pointer
offset0..7 is permitted, not assumed0. Each of the three11-bit groups
may have a different offset because each independently writes/reads its
own ring with that same offset. The eight cases in model.json prove
the fresh-fill property for every offset, including occupied aborts at
all eight dimension phases. This is a per-group separable storage
argument, not a four-state X-initialized Verilator simulation or a
power-up implementation certificate. It does not require reset copies
to converge to equal state. Kept hierarchy and actual native mapping
still must preserve the intended copies and <=32 loads.

Bounded source-control trace in the same hash: reset clears iss_blk
and iss_c (lines452–463); ILV `hand` resets both for the back job
(479–483); nonILV job_go resets both; pv_go increments iss_c and
advances iss_blk only after DPT issues (534–546). Thus block0 emits
eight dimension beats before block1. e_iss_* travels through the
ILV/XD tag paths into e_blk/e_fin/e_c (811–813), TLAT u_tag
(917–918), then merge_x iv=`t_ov[gk]&&t_pv` (972–975).
e_iv/e_pv reset0 (790–795), while merge control valid resets
via kreg/vdly. Remaining proof is that real tile valid and delayed
tags flush/align across interrupted reset and every selected ILV/XD/
F12 profile; no source-bound actual RTL trace was run. This candidate
avoids inventing new pointer reset release stages, but cannot claim
the complete producer-to-merge lifetime until that trace is supplied.

`model.py` ran through unpinned ot-run, real unit
`oth-ubuntu-1658821-1792440209` on ot-epyc8, exit0. Payload arrays start
with unrelated arbitrary33-bit data; there is no zero-init assumption.
Each of320 independent rings sees five jobs, eight dimensions per block,
random bubbles, valid-only wrap, and occupied abort/restart. The modeled
level-live predicate is the source binary-counter recurrence:
all lower level block bits are1. It compares every qualified live/use OLD
head and preserves all33 bits. The original arithmetic is outside this
abstract proof; **no Verilator5.050 RTL bench has run**.

Off-by-one read, advance-on-bubble, wrong-head payload, and recirculation
clobber mutants each fail the OLD-head check. Counts are in model.json.
This does not prove actual producer/controller follows the modeled sequence.

Critical reset counterexample is preserved: an occupied original ring
whose physical pointer was3 has logical OLD head3; resetting the new
pointer to0 changes stale head to0. Thus unrestricted arbitrary occupied
reset equivalence is FALSE. The modeled fresh block-0 programme writes
all eight dimensions before a live/use read at every level, making stale
orientation unobservable. Exact production reset/job restart must prove
this lifetime, including interrupted jobs and no mid-block restart.
An early post-reset use is rejected by the initialized-entry assertion;
it cannot be repaired by pretending stale payload is0. A reset/wrong-head
RTL negative remains required after an implementation exists.

## Next bounded step and safe-design status

Resolve reset distribution and source-bind the real post-reset block0
restart/lifetime first. Then add a private default-off helper and parameter,
retaining unchanged defaults and exact qaddf rounding, and run the smallest
actual RTL comparator on pinned Verilator5.050 with original controls,
bubbles, reset and causal mutants. Only then collect all-driver uncapped
mapped pin census, actual delay/area and whole-SVC delta. No whole-array
arithmetic build or physical gate is justified by this model.

Checklist: registered external pins/inherited ages unchanged (no tile built);
reach OPEN; fanout LOCAL MODEL ONLY; complete depth OPEN; storage is
genuine264-bit local ring, no shift chain; floorplan OPEN; clock/reset
OPEN; static schedule intended delta0, production proof OPEN. Single-user
and multi-user token qualification stay OPEN.
