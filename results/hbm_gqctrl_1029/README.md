# GQ issue format-control reset

The `gq_issue` kit LEC differs at 1024 AQ output-register bits because the
format pin is tied to FP8 while the format pipeline has no reset. Synthesis
folds this control to zero; the RTL comparison retains arbitrary power-up
values at s8/s10. The candidate resets the format-control pipeline to FP8
alongside its existing valid pipeline. Ports and latency do not change.

Source before change: main ac2ad01a82a6ed2841435bb93c3e33f274eafd0a,
`physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv` (identical to the
KITS-6 old source). No datapath arithmetic or rounding expression changes.

The smallest source-derived miter adds observation ports to copies of the
actual before/after source and removes unobserved arithmetic with Yosys.
At s0/s1/s2a/s2/s7/s8/s9/s10 it checks identical valid flags and identical
format whenever that checkpoint is valid. Format and input valid stay free;
reset can reassert. Positive 20-edge replay PASS; temporal induction PASS;
inverting the s8 format bit is CAUGHT. Logs are new.log, induct.log, mut.log.
`build.py` performs only observation-port insertion plus the mutant.
`replay.sh REPO OLD_COMMIT NEW_COMMIT OUT` reads repository-relative source
at the supplied commits; run via ot-run in the ORFS image.

Full arithmetic source equivalence at fp4 tied0 was also collected from the
KITS-6 candidate (intel2 codex-hbm-gqlec-1029/inspect.log): 19000/19001 points
PROVEN; the only unproven point is internal u.s7_fp4, whose unreset/reset
invalid-cycle values differ. The discharged output cells are compositional and may use internal
cutpoints, so they are not standalone whole-module equivalence while this
point remains open. Its valid condition is proved by the tiny miter. This
is not a 19001/19001 pass.

The inherited new-gold/old-gate kit LEC probe is still running at intel2
hbm-cores-kits-6/gq/lecprobe (k6gq-lecprobe). The source change is ready for
shared RTL review; kit adoption waits for that result, geometry and normal
physical gates. No physical sign-off or token-pass claim is made here.

## Full retained-AIG proof collected 2026-10-29

The candidate now has the full new-gold/old-gate comparison: 1347/1347
joint obligations and 41039/41039 compare points PROVED, zero differences
or undecided. The original 802 proposals were re-proved; absent old names
were dropped, and the explicit reset-zero format registers were proposed
as zero and proved. No state/format assumption was imported as a waiver.

`gq_retained_receipt.json` pins the source and repository-relative input
archive. The compressed archive retains the exact AIGs, maps, old proposals
and proof engine used. `replay_retained.py --out SCRATCH_OUT` repeats the
proof in the ORFS image through ot-run; no physical build is needed. The
collected ABC output is `gq_retained_proof.log`. The preceding source-only
19000/19001 compositional result remains historical; this full comparison
satisfies the candidate's RTL/gate proof condition. Physical sign-off and
current plan compatibility remain separate.
