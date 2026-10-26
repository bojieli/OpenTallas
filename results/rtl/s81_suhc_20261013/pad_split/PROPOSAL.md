CPAD / CCR return-alignment physical split — proposal only

The present HALF1/RLY2/RF5 CPAD is not closed: own d71bc15c1 job reports 36,317 flops, 54.37% std utilization at 155.52 square and 66.0% with hold-buffer allowance (>65%). The earlier HALF0 CLOSED alias is not valid production evidence. RET_EXTRA1 adds two return stages and takes the unsplit production count to 40,629, before any CTS/ECO growth. An unchanged 155.52 square pad cannot be assumed to pass.

The supplied pad-split.patch adds rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_pad_split.sv and changes only the comb's two selected module names to ot_s81_hc_ccr_align and ot_s81_hc_cpad_split. Do not apply until ctnl helper proves the common alignment fix and parent coordinates the shared comb update. Add the new file to hc_gate RTL source list and parent physical assembly. No shared file has been edited by this helper.

Production tuple: NG256, NCOL3, GS8, S_RD2, S_RT4, HALF1, RLY2, RF5, RT1, DW6, RET_EXTRA1. NP11, L1=10, PAD8, FP15, RP13, FSW1128, FVW7, RDW2156. The forward bus is 1135 bits; the return pin-access budget reserves 2164 bits although CPAD itself carries only RDW2156 (its RVW8 is already independently carried by CCR metadata).

| Leaf | Exact data stages | Clock sinks | Estimated std area | Outline um | Estimated std/core utilization |
|---|---:|---:|---:|---|---:|
| pad_f8 | forward8 | 9082 | 3108 | 138.24 x 49.68 | 51.2% |
| pad_f5r1 | forward5 + return input1 | 7833 | 2681 | 138.24 x 99.36 | 21.1% |
| pad_r6 | return6 | 12936 | 4426 | 138.24 x 114.48 | 30.3% |
| pad_r5 | return5 | 10780 | 3688 | 138.24 x 99.36 | 29.0% |
| pad_meta2 | metadata2 (RVW8 + PI8 + exports512) | 1058 | 362 | 138.24 x 15.12 | 25.0% |

Std estimates are derived from the measured RF5 CPAD's per-flop area, not signoff measurements. Replace with actual leaf synthesis areas and enforce the standard <=60% std / <=65% with hold-buffer allowance gates. At the own job's observed ~0.073 BUFx2 area per sink, even f8 is about62.1% with allowance; other leaves are below that. Low std utilization on return leaves is deliberate pin-access reservation, not a guessed undersized outline. Synthesis/CTS/margin gates decide whether these estimates survive.

There is no extra seam register. cpad_split is wires only. Each leaf's first and last flops are the capture/output boundary. The two independent pipelines in f5r1 share a <=7833-sink clock root; no combinational data logic connects them. Counts are forward8+5=13 (=FP-2) and return1+6+5=12 (=RP-1). f8/f5r1/meta2 contain the original two-cycle reset relay locally; all valid flops retain their reset timing. Return rows remain unreset. Reduced shapes retain computed widths/depths; the hard-path elaboration guard requires the exact production defaults. OT_S81_HC_PAD_HARD instantiates all hard children without parameter overrides, preventing parameterized blackbox fold mismatches.

CCR alignment is an outer wrapper: instantiate the existing core with RET_EXTRA0, HALF1/RLY2 and its original RF4 tuple; append only two metadata stages, preserving the current aligned RET_EXTRA1 behavior. Its raw crd_o capture output bypasses this new metadata leaf and feeds CPAD's first input stage. Current production metadata width528 =>1056 data flops +2 reset flops. This leaves the original ~14718-sink core unchanged. The new wrapper has no data/valid flop and adds only direct child seams. RF4 in the preserved core is intentional: its unused forward FP formula has no return function, and using the exact historical core tuple avoids claiming a new core closure.

Standalone reference specs and explicit pin plans are supplied for all five new leaves. All N/S forward and metadata banks use M5; the return input/output banks use alternate halves on W/E M4 and M6, under the existing grant for children of the hardened sp_hc_s cluster. Each return face has1078 bits per layer, uniformly distributed over the actual face excluding2.16um corners. r5/f5r1 worst density is about11.35b/um/layer, r6 about9.88, below12. Forward bank1135 over133.92um has~8.48b/um, below12. Metadata528 over133.92um is~3.94b/um. Pin sizes and coordinates match the existing explicit ASAP7 lattice (.012+.048n); clock/reset occupy reserved low W/M4 tracks. This is a recorded cluster grant, not a new die routing-layer exception. No power-grid or timing constraint relaxation is proposed.

strip-fit.proposed.json is a REQUEST, not adopted top geometry: preserve comb outer575.992x640 and ccf410.4x542.16, propose new leaves x432..570.24 with21.6um channel from ccf edge, stacked y0..464.40 with21.6um gaps. Width138.24 fits within the right-strip usable145.592um. The longest inside-leaf diagonal is178.83um and the adjacent registered leaf seam is under200um. Every proposed new child boundary hop is below500um. Placement of the existing151.2-square CCR core must be independently reconciled: it does not fit the145.592um usable strip width. The supplied strip request proves only new-relay fit; it does not prove that the entire current comb inventory fits. No die outline, origin, pin contract, or shared top generator has been changed.

The leaf ref_tile specs can be synthesized/routed as proposed budgets before inner placement approval. Integration needs the die writer's explicit inner-remap acceptance and legal placement of every retained child. Parent should not advertise these views as an adopted CPAD cluster until that layout is recorded.

View and fold proof required:

- Use separate leaf masters and view paths s81hc_pad_{f8,f5r1,r6,r5,meta2}_ref. Never reuse CPAD HALF0/HALF1 old closure aliases or change their immutable verdicts.
- Reuse only the actual CCR HALF1/RLY2/RET_EXTRA0 closed core view after its source/parameter/corner/child_lint hash matches. Do not reroute/relabel the unchanged core merely because the wrapper has changed. No view equivalence is asserted by this proposal.
- Parent hard synthesis must define OT_S81_HC_PAD_HARD, include proper blackbox .v/LEF/TT/FF/SS models for the four pad children, metadata child and the core. New wrappers have production defaults matching their stubs and instantiate children without overrides. No disconnected or tied return/metadata ports.
- Build the wires-only wrappers with hardened stubs and assert synthesized master/count census exactly f8=1,f5r1=1,r6=1,r5=1,meta2=1,ccr=1; no $paramod duplicates or accidental flattening. Parent's existing OT_S81_HC_COMB_HARD guard still describes a legacy tuple and must be corrected separately during coordinated production assembly.
- Proof of folding also needs each actual child source/tuple hash and parent pin-to-pin connectivity; a generic module name or old alias is not proof.

Validation required before adoption:

1. Targeted delay bench tb_pad_equiv.sv compares legacy RET_EXTRA1 CPAD with split CPAD on changing forward/return data and valid bubbles: same edge, forward13/return12. Negative mutant changes r5 depth5->4 and must fail. This bench is independent of FP.
2. Compare CCR legacy RET_EXTRA1 metadata to the preserved RET_EXTRA0 core followed by2 stages, including subtree fault and PI/exports; new wrapper uses the actual core arithmetic.
3. Parent's aligned reduced NG64 HIER3 m0 passes all cases and m3 fails; production NG256 HIER3 m0 passes every golden row/fault/tag/cadence and m1 fails. Do not require the earlier6018 baseline once the separately justified RET_EXTRA fix changes the common schedule; compare to the newly pinned unsplit RET_EXTRA1 alignment proof instead.
4. ref_tile generate and CTS pre-route/ingest gate on each production-default leaf: margins pass, boundary pure flops, root counts<15k, no stage exceeds700ps. One source-pinned new route each after duplicate check. TT setup>=0, FF hold>=0, DRC0, above-only access/child_lint clean and actual layer-cap clean.
5. Parent post-fold synthesis/route/checks only after accepted inner remap; no child closure means parent closure, and no placeholder/alias qualifies any view.

Parent lattice correction: r6 height114.48 (53x2.16um), r5 origin328.32/meta2 origin449.28; proposed envelope464.40, same pending fit limits.
