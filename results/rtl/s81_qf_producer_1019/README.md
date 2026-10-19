# Actual S81 QF configuration source and runtime producer model

Source base `58fc3dbc1aa63cb27a6bd3b3117ac2c04e13f3dc`. This packet adds an
opt-in compiler component and a real paired source/consumer proof. It does
not qualify the runtime Q/OWN_ROW producer, a layer, or SU/MU token execution.
No engine RTL, original programme, golden value, deadline or failure is changed.

`compile_headers.py` derives CFG/WIN_LOAD/GO words from actual configured job
fields. Its CTLs write twelve existing VP SRAM rows, then issue real RDOUT and
SEND-B commands. The bench instantiates original XR HB1, original VP including
both real SRAM models and arithmetic, original DL4 glue each way, and the actual
`ot_s81_svc_job` used by the entry. No data is injected at q or at XR lo. The
only data stimuli are legitimate target5 configuration writes. The job consumes
the actual B output through its original entry pin capture. This scope has no
RSTOP before the XR CTL inputs and no parent q landing after B; their ages,
phase and physical timing are not qualified by this proof.

Fleet Verilator 5.050, ep4 unit `3583232-1792439749`, `out_v5`, passed all eight
tags (0/1/53/127/128/213/254/255), 24 complete configured headers, original
source/consumer faults low. Six causal witnesses fail: corrupt word, wrong tag,
wrong slice owner, missing consumer word, one edge early and one edge late.
Witness 7 additionally retains a genuine unchanged II1 expectation: the real
packer emits the two adjacent words at 112/114, so expecting their qualified
consumer edges at 113/114 fails. The correct component schedule 113/115 passes.
This diagnostic never changes the existing layer's one-word-per-edge schedule.

Measured edge ledger (same streaming clock, 833 ps period): CTL RDOUT at92,
XR command94, VP command98, VP lo103..106, XR lo pins107..110, B112/114,
qualified job consumer113/115. First-word RDOUT-input-to-B is20 edges, to
consumer21. `failures/initial_age_guess_fail.log` preserves an initial incorrect
15/16-edge prediction; output values already matched, only that component age
guess failed. Source and original source consumer RTL remain byte-identical.
Build dependency failures are preserved separately.

Costs before hardware: zero new FF, zero new macro, zero new clock loads;
1536 bits in twelve already-existing SRAM rows480..491 and sixteen CTLs per
three configured headers (12 writes, two SEND configs, two RDOUTs). Those rows
overlap the final-FFN scratch convention, so production lifetime/port admission
is explicitly false. The component changes no pin contract or reset tree.
Cold reset is exercised in every tag case; warm/arbitrary-phase reset and
native CTS/FF-hold/TT-setup are not claimed.

The model was refined after the immutable `out_v5` run. Its original compiler
is preserved as `out_v5/compile_headers.pinned.py` with the exact run hash.
The final model emitter's hash is
`093edfbb98cfa7224f695e40a609b1ea596d1b48e9d849d79431b9e5fff2eca6`.
Fleet byte comparison proved all eight final CTL and golden files identical to
the actual passing run. This is a model-only refinement, not an RTL rerun.

## Runtime producer obligations remain open

The actual source programs disagree on ownership. `xs_place.op_groups(wq_b)`
assigns head h to slice h, across eight real frames. `xs_calendar.cmd_cap`
allocates first wq_b output at word base0; dimension d goes to leaf
`(d//64)%5`, word `64*((d//64)//5)+d%64`. The last64 dimensions are therefore
leaf2 words64..127 (rows16..31) of each head's slice. In contrast,
`lower_vs.shares` maps RoPE head h to slice h//5, leaf h%5. No existing emitted
producer programme joins those states.

`model/model.json` contains both ownership choices and all sixteen source maps.
Head-local RoPE on leaf2 of slice h is the preferred **model**: no remote tail
transfer, versus15 remote tails and one local cross-leaf tail for old ownership
(six require a tier crossing). Both need256 real runtime row permutations:
tail rows must occupy even rows512..542, with16 coefficient rows at513..543;
RoPE writes rows544..559. There is no existing source-bound permutation path.
The lower bound is16 runtime SRAM write edges per head, plus presently unproved
copy pipeline/gather/port contention. Existing SRAM reservation for the16 QR
windows is98304 bits, not a new macro allocation. Added copy state/logic area
are NULL until an actual mechanism is selected and sized.

Projection and QR outputs are BF16 stored in FP32 words. Raw RDOUT does not
compact them into32 BF16 values per512-bit Q word. Existing VQ compacts64 into
XB1024 but has no bound VQ-to-XR-lo/B route. Neither path is free hardware.
Even with already-packed source rows the unchanged two-pair B packer has II2:
258 words for both original ATTN_Q header+128-word frames span at least515
edges, versus258 originally, a lower-bound +257 edges before startup, gather,
CTL collisions, compaction, routes or reset phase. Two payload-only half spans
each add127 edges; that narrower +254 count excludes their headers/join.
No +257 token claim is possible because these paths are not yet built/priced.

Actual OWN_ROW additionally needs a source-bound runtime FP8 code/scale encoder;
`lower_svc.Job._frames` computes `fp8_row_codes` in reference Python. It is not
an on-die producer. The sixteen actual SM output targets and G9/G9b return path
remain with the SVC storage owner. Full Q buffering, if chosen, is131072 bits
and must use a real SRAM family; it cannot be introduced as an indexed FF bank.

Next implementation must first select and price a real row permutation or
independent coefficient-read mechanism on head-local storage, build actual
BF16 compaction and central gather with static identities, reserve the real
ports/rows, and compose clock/reset/fault/edge ages into the original compiler.
Then the smallest real wq_b-return→capture→QR→SEND→actual attention consumer
must pass original gold and deadlines plus causal payload/owner/age mutants.
Original strict 1324-failure evidence and the QF_PRODUCER_GAP remain unchanged.

## Selected-source replay and priced compaction follow-up

The historical selected MU3 source `ceaed19c4` does not contain this current
layer compiler. Its VP/VS differ from main58fc in unrelated POST/NORMR and
runtime SwiGLU-weight support. `selected_source/` preserves exact historical
VP/VS bytes. The bounded header proof was replayed with that exact VP and the
current compiler, explicitly separately pinned; XR/CAP/job are unchanged.
`out_selected_cea` (ep4 unit3611360-1792440343) passes the same24 headers and
seven negatives at identical measured edges. This is still a minimum component,
not a claim that the historical GEN embeds the newer compiler/functional fixes.

`model_compaction.py` extracts the original VS `bf16` and CAP `fmt_d` functions
verbatim into a formal miter. Fleet Yosys SAT proves, for all2^32 source bit
patterns including NaN/Inf/subnormals/ties, equality to the pinned original
`hdc_golden.to_bf16` arithmetic and zero lower16 output bits. The selected VS
function and main VS function are byte-identical. A raw-truncation negative
produces a counterexample. Thus a proposed compacting source may select the
upper16 bits only after these genuine producer writes; it may not silently
truncate arbitrary FP32. This isolates the rounding boundary; the actual
whole projection/QR write→SRAM read path still needs a composed proof.

`uniform_model_final/` contains that source ledger, proofs and the
explicit candidate cost. In-XR mode:64 eight-bit select groups, four mode-data
copies and four enable copies (72 FF),512 three-NAND data muxes,512 zero-format
ANDs,64 shared select inverters and72 enable muxes. Actual TT cells charge
221.84928um² per entry, two-entry443.69856um², +34.180992fF clock per entry.
Four resettable enable copies are additional reset loads; other mode state is
unreset and requires proof that every SEND config precedes all valid payload
after cold/warm reset. New select load bound25 is modeled, not a native census.
Output remains the original pin register; no added pipeline edge or SRAM.
This is a priced cell network, not a bound on routed/sized/clock-tree area.

The alternative standalone packer needs640 new data FF plus control and
header/bypass logic, at least186.624um² in data FF alone, and adds2 edges.
Both choices consume four FP32 row pairs per compact512 word, hence II4.
The two original headers remain raw and consume two pairs each;256 compact
payload words consume1024 pairs. Those1028 source-lo edges yield an output
span of at least1027 edges, +769 over258, ignoring all mode-switch, gather and
start/control overhead. Current config/lo exclusion also needs at least three
mode-switch bubbles. An all-compact258-word diagnostic span1029 is recorded
separately and is not the favorable mixed-format bound. No finite full mixed
calendar is implemented or admitted, and none of these partial counts is an
exact end-to-end token delta. The unchanged source schedule still fails.

The upper512-zero rule belongs only to a new genuine compact32-BF16 packet
after format/mode/pair-count and original gold prove every occupied value
preserved. It is not an unread-payload exemption for existing generic SEND
packets. ROOT is reviewing this model before any compaction hardware is built.

## Preferred uniform static wire profile (model and component proof only)

A simpler profile needs **zero new data/control FF, gates, reset/clock loads,
or pins**: keep the complete existing XR1024-bit B payload and NP4. At the
existing q binding, wire source `bo[52+32*i+16 +:16]` to target q-data
`[16*i +:16]`, for i0..31. No output register is bypassed or added. Each
selected source bit still has one consumer. All32 FP32 source words contribute
their already-rounded BF16 payload, including meaningful data from the upper
512 B-payload bits. The16 zero low bits of each real producer word are format
redundancy proven at the actual producer rounding boundary, not tied outputs
or a blanket unused-payload waiver.

Every actual configured512-bit header is stored as32 real SRAM words
`{header[16*i+:16],16'b0}`. The same static wire permutation reconstructs all
512 original bits, so original type/tag/user/length/position and payload
interpretation remain unchanged. Header storage becomes24 existing128-bit
rows480..503 (3072bits); it is not a new FF array or macro. This still needs
production reservation because of shared final-FFN scratch lifetime.

`out_uniform_cea` is a paired **model prototype**, not a production GEN edit:
exact historical selected VP, untouched XR/SRAM/DL4/job RTL, expanded genuine
configured headers, and the proposed constant wiring only in the bench.
Verilator5.050 ep4 unit3620710-1792440701 passes24 headers/eight tags and all
seven causal negatives. B words are at114/118 and qualified consumer115/119,
with original header512 gold unchanged. No final runtime Q payload was
injected. The formal uniform-header proof covers all2^512 header bit patterns;
using the existing contiguous lower512 binding instead produces a counterexample.

An exact new production source/profile fingerprint and q-binding representation
are mandatory before any implementation/adoption. Existing bindings remain
untouched. Inherited registered pins, clock/reset behavior and macro area are
unchanged by the proposed wire permutation; actual gather geometry and native
route/contact/electrical results are not qualified by this statement.

All258 Q-header/payload words now use the same four-pair representation, giving
the valid uniform lower bound1029 edges versus258, +771, with no format-mode
switches. The mixed in-XR alternative's data-only bound1027 requires at least
three config/lo-exclusion bubbles, so is not better before further constraints.
None meets the original unchanged one-word-per-edge schedule. New calendar
admission and the full runtime producer path remain open.

The other bounded alternative compacts at the SVC receiver into the already
prototyped QMEM8 native banks (`4cf0651b8`), with no new data buffer or macro.
Each raw512 word is16 FP32 values →256 BF16 bits: half0 writes banks0..3,
half1 banks4..7, and `q_have` advances only on a matched completed head. Actual
query stripe addressing changes from tile=`f_idx[3:0]`, head=
`{f_hdr[448],f_idx[6:4]}` to tile=`f_idx[4:1]`, head=
`{f_hdr[448],f_idx[7:5]}`, phase=`f_idx[0]`. The job gate currently counts
physical q words, so a proposed raw version requires type1 length256 instead
of128, and an explicit new profile/controller; merely changing bank enables
would silently corrupt addressing/counts. GO with incomplete query, missing or
mismatched first half, active read/write collisions, unsupported lengths and
identity all need fault and reset/lifetime proofs. Native OLD read and engine
read address remain unchanged only once both halves are valid. Its514 raw
words at II2 span at least1027 edges, +769; source phase, all control/identity
state, native fanout and full area remain unpriced. This is less simple than
the uniform wire profile and is not implemented.
