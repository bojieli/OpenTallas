# C199 FOREP: kept fan-out copies (kit s81sf_bfcol_c199rr), S81-C199-FRAME 10-19

Source: claude/c199-fanout-1019 @94b17b213 (= c199rq FREECLK + RSTPART v2 + opt-in OT_BF_FOREP).
Change: same-edge KEPT copies so no register drives more than ~32 loads (counted through BUF/INV). Examples: one-hot
slot copies for the chain acc reads, first/fwd slice copies, cut-field copies for fadd/fadd2/bmul, staged log
shifters with per-range select copies, segtree one-hot tree-id port, bterm4 fp4/sub/sign copies, and pair-both /
BF-valid byte copies. 0 added data edges, 0 added reset edges.

## Bench (Verilator 5.050, ot-epyc6, bench.sh tag b3, SOURCE_COMMIT 94b17b213)
- baseline (RSPLIT+TAGREP) and forep (+FREECLK+RSTPART+FOREP): both TXN MATCH, compared=456, lag 5.831/14.994/9.090 ns.
- forep per-cycle trace == default column: 124,422 lines, sha c6cf9839... (forep_exact.json).
- Mutants: each has a committed fail witness in fail_witness/, and each fails with `%Fatal: .*DIFF TXN lane=`.
  - fe_mut_add: first trace mismatch at line 2701.
  - fe_mut_chain: first trace mismatch at line 5582.
  - fe_mut_tree: first trace mismatch at line 2689.

## Synthesis census (data_census.tcl, loads per driver through BUF/INV)
- Before (c199rq synth, census_rq_synth.txt.gz): u_tag line[200] drove 1,060 loads, line[201] 532, p0_fp4 442,
  first_r 309, and BF t_lr 267 (x16).
- After (c199rr gate synth, census_rr_synth.txt): MAX 36. Only 30 drivers are above 32, and all of them are the
  bits of one register, u_ot_pr_core.g_l3.u_l0.p1_sqb (33-36 loads).

## SAFE-DESIGN checklist (kit s81sf_bfcol_c199rr)
1 Pins: PASS. The RTL registers every pin; reset_landing is enabled with 2 stages; io_hold_margin is 0.03.
2 Reach: PASS. The tile is 432x216 um, so no single-cycle wire is longer than 405 um.
3 Fanout: fixed (1,060 -> 36). p1_sqb at 33-36 loads is waived as "~32": it is one leaf multiplier operand, and it is
  not in the worst-setup or hold cone of the c199rq CTS report.
4 Depth: PASS. The c199r lint measured 493.4 ps; FOREP adds 0 logic levels on the data paths.
5 Storage: PASS. Both ROMs are macros. The flop->flop hold groups in the rq CTS report are u_add u_c* pipeline
  cuts, not delay lines.
6 Floorplan: PASS. Same as c199r: ROMs on the 43.2 lattice, a 23.45 um pin channel, E-face pins at 3.6/um,
  aspect 2:1, util 60%.
7 Clock: PASS on the rq readout (same floorplan). Pin-flop spread is TT 22.6 / FF 20 ps, and the boundary is
  399-422 ps at TT. Clock root is centre-fed, same as c199r.
8 Schedule: PASS. 0 edges added; the c199r/rq reset landing (+2) was already handed to MU-DIE-S81.
CRITICAL prefix ot_v41_bf_: COORD-REVIEW-QUEUE only, no REVIEW.json, no submit.
