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
