# DLY-SPREAD handoff (2026-11-15), brief 4.3 (G8, G12)

READY: branch claude/dly-spread-1115-1 @47010b3510 (parent claude/fable-genbug-1115-1 @4e7f20bccb), epyc9 /srv/opentallas-scratch2/claude/dly-spread/wt (own clone, not pushed to origin; GENBUG-IMPL installs by `git fetch` from that path).

Files (tools/die_plan): dly_spread.tcl (new, G8), test_dly_spread.py (4 tests, docker), forest_recluster.tcl + test_forest.py (G12 `q` alias), gen_phys.py + schema.py + die_plan.schema.json (opt-in `budgets.r_dly_spread`; hook appended to face_flops_release.tcl after chain_even).

G8: every zero-logic register pipe (name only discovers `<inst>.[g_reg.]r[k][b]` / `.q[b]`; stage identity = D of k is Q of k-1 through BUF/INV/HB, fanout 1) with no plan site is spread on a Manhattan route around the hard cores (core_input_chain.tcl route form) from its driver flop/port/core pin to the centroid of its loads. FIRM / ot_face_flops.txt stages are anchors; chains inside 405 um untouched; chains driven by logic skipped. Log `OT_DLY_SPREAD chains/stages/moved/max_hop/worst-ideal/fail`; fails closed (worst hop > 1.5 x route-length/(n+1), over 405 um, at least one movable stage); OT_DLY_SPREAD=warn downgrades. OT_DLY_SPREAD_DEBUG=<glob> prints one line per chain.
G12: forest_recluster.tcl accepts `<inst>.q` / `.q[0]` as the last reset-chain stage (renumbered max r + 1). Latent: S81 slice netlists have no such flops (0 chains stays correct there).

What-if (place-only form: hook applied to the kit's 3_place.odb, hop_census.py before/after; true re-place not run, DPL legalisation not included):
- cbf_q01: over-reach hops 3583 -> 408, crossing a core 556 -> 0 (zero-logic hops 49157). 12,858 chains.
- c1x_C__t1: over-reach 17826 -> 14136, crossing a core 2696 -> 1539. u_d1_*_lp_*_Y worst hop q50 709-854 -> 399-469 um. Remainder = ring->u_bin (G2), last pad stage (G1), stage shortfall (plan). 58 chains would FAIL the gate (stage-count shortfall): use warn there.
- col_h9_r1: over-reach 4493 -> 4242, crossing 0 -> 6. NOT the brief's cause: u_d10_6_Y is a 1-bit pipe whose last stage fans out to 1,317 loads; the 1,268 um is stage -> farthest load, not a chain hop (chain hops 302 um). See FABLE-TRIAGE-S81.md. Not fixed by a chain spreader.
Tests: test_dly_spread.py, test_forest.py pass on epyc9.
Next: GENBUG-IMPL to install, set budgets.r_dly_spread in QC cb / S81 plans; a full re-place of one kit to confirm DPL keeps the spread.

11-15 update: branch pushed to hub:OpenTallas claude/dly-spread-1115-1 @47010b3510. Messages sent: GENBUG-IMPL (install on 4 trees after merge), DIE-QC-103 (r_dly_spread on cbf_q01 family, S4k/S4k2), DIE-S81-92 (r_dly_spread on c1x + OT_DLY_SPREAD=warn for the 58 short chains).
