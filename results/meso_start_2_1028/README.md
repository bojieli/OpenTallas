# MESO-START-2 (10-28): start-skew-clean start edges (PAD+1) + start-edge override for unbound QC pairs

Branch claude/meso-start-2-1028 (off main 387e0d0112; carries DIE-QC-5's die_sta_related commits 9632aa0111 +
8f50ee83e5 cherry-picked: spice scale of tree nodes + opt-in --count-align-key region, COORD 03:4x "required for gate
runs").  All numbers OWN runs (CHECKED-own = read from my run outputs), not NUMBER-CHECKed by an independent lane.

## Code (shared tools/die_plan, all opt-in; default byte path unchanged)
* `count_align_plan.py --start-skew-clean` (needs `--start-skew LO,HI`; also on `count_align_bind.py --from-ocv`):
  on the UNCHANGED min-ambiguity start tree, a tree edge is CLEAN only if its static sync distance >= sync aperture +
  max|skew| (QC 26.5 + 87.5 = 114 ps; S81 26.5 + 79.4 = 105.9; HEAD 26.5 + 89.7 = 116.2), i.e. die_sta_related's clean
  start row (|skew| <= dist - sap) holds.  Otherwise the edge is AMBIGUOUS: its tree crossing takes the plan sync window,
  its J deviation covers the skewed sampled phase [lo - s_hi - sap, hi - s_lo + sap] (path ambiguity of every crossing
  whose tree path uses it), DEPTH is chosen so margin_hi >= 100 + |skew|, and PAD + 1 is put on the edge when its tree
  crossing's margin_lo < 100 + |skew| (OWNER 12.15b), so die_sta_related's ambiguous start row (margin - 100 >= |skew|)
  holds.  The plan MC and the bind start-up sim then sample d - skew (`bind.start_skew_ps`, only when the plan asked).
  Summary block `start_skew_clean` records the edges re-read, the PAD+1 edges and the added latency (12.15c, record only).
  A first variant that re-read the edges BEFORE building the tree (tree avoids them) measured worse on QC (30 FAIL) and
  was dropped.
* `count_align_plan.py --tree-parent REGION=PORT` (also on bind --from-ocv): start-edge override after the tree is
  built; the region (with its subtree) takes PORT (a crossing into it from a reached region) as its start edge; a loop
  or a foreign port is refused.  COORD 03:4x: binds region pairs that have no bound crossing via a different start edge.
* `count_align_bind.py --sta-proof/--sta-plan/--sta-clock-cal/--sta-cppr-lca`: the DIE-HEAD-5 one-interval hull in the
  in-process (--from-ocv) plan, as count_align_plan has.
* Tests `tools/die_plan/test_count_align_skewclean.py` (6): default unchanged; MUTANT clean-looking edge at 113 ps (<114)
  becomes ambiguous, gets PAD 1 when its low margin is short (250 ps wander) and its start row limit >= 87.5; 115 ps
  stays clean, no PAD; bind start-up check: flagged plan 0 violations / unflagged 113-ps plan VIOLATES once the skew is
  simulated / stripping the PAD from the flagged plan is refused by bind; MC samples the skew; --tree-parent override,
  loop and foreign-port refusal.  count_align*/die_sta_related suites 69 PASS (epyc2).
* Byte check (CHECKED-own): QC K2 rows, main 387e0d0112 vs this branch without the new flags: plan.json + plan log and
  bind json byte-identical (only plan_source path text differs when the path is given differently).

## Proof coverage
No new RTL form.  The ring form is unchanged, so the MESO-COUNT-2 k-induction proof (0af33ccde0, safe + no-fault for L in
[5/8 T, (D - 5/8) T], fail-closed outside) covers every crossing: the plan keeps every lag inside that window (ap kept).
PAD is a parameter of ot_dp_landing_origin: a PAD-deep plain shift register after the 3-flop synchroniser (no CDC), so it
adds exactly PAD counts; the origin step a_c - a_p = PAD + 2 + J is the MESO-INTEG-1 / MESO-COUNT-2 formal_origin
identity, re-checked per edge by count_align_bind (integ_step == count2_step == plan step) and simulated with the skew.
PAD 1 per edge was already used on HEAD (MESO-RECONCILE-2, 6 edges).  In strap form the PAD value is a strap tie
(MESO-STRAP-1 strap_ca_pad), covered by its per-variant LEC + tie-value audit; PAD now differs per edge.  No k-induction
rerun needed.

## (1) QC K2 (DIE-QC-4 K2/CA_2w2s rows grp_spice_xing_lpo, spice; die STA = main + DIE-QC-5 fixes, --clock-cal spice
--cppr-lca --count-align-key region; start skew 55.2,87.5 = the STA's TT clk->Q; epyc2 .../meso-start-2/qc_k2)
| run | plan CA FAIL (unbound region pairs) | lag lo TT/FF | start-skew FAIL TT / FF | PAD+1 edges | added latency |
|---|---|---|---|---|---|
| base (min-amb tree) | 6 (3) | 121.7 / 116.8 | 34/312 / 21/312 | 0 | - |
| --tree-parent x3 | **0 (0)**, bind sim 0 viol | 121.7 / 116.8 | 37/312 / 24/312 | 0 | sum lat 6737 vs 6727 (base has 6 unbound) |
| --start-skew-clean | 19 (10) | 182.7 / 116.8 | **0/312** / 11/312 | 2 | +54 cyc |
| --start-skew-clean + --tree-parent x3 | 14 (7) | 182.7 / 116.8 | **0/312** / 11/312 | 5 | +58 cyc |
| --start-skew-clean + --sta-proof hull | 82 | 182.7 / 189.9 | **0/312 / 0/312** | 2 | +75 cyc |
| base + --sta-proof hull | 64 | 121.7 / 121.7 | 32/312 / 2/312 | 0 | - |
(lag/slot/guard 0 FAIL on every bound crossing in every row.)  Tree-parent overrides (round-greedy search,
scripts tp_search.py): c_W0_tn_10=c_W0_tn_00__a22__0, c_E4_tn_10=c_E4_tn_00__a22__0, c_W0_bn_10=c_W0_bn_00__a22__0: the
three tn_10/bn_10 subtrees leave the long sl_*_hc2 -> c_*_10 start edge (d ~5.8 ns, J dev [-1, 1]) for the local a22
crossing, so the 3 pairs bind with no old ring (COORD 03:4x (1) met in the default skew reading).
FINDINGS: (a) The 114-ps rule is right for the start rows (TT 0/312) but costs CA: 32 tree edges miss 114 ps, and 11 of
them are J-FREE under the 87.5 ps skew (the skewed phase really crosses a sampling boundary: their nearest boundary lies
BELOW the interval).  For those the base plan's "clean" J is not chip-invariant, so the base plan under-counts path
ambiguity there; PAD cannot fix it (PAD shifts, it does not remove J freedom).  (b) FF 11/312 left = clean edges whose
STA FF interval sits nearer the boundary than the plan interval (sta_sync_dist 12-25 < 26.5); the one-interval hull fixes
them (FF 0/312) but the hull widens 2,300+ rows and raises CA FAIL to 64-82 (DIE-HEAD-5 saw the same on HEAD before the
LCA-CPPR fix; QC's K2 proof has no tree_path, so CPPR stays at the root).

## (2) S81 kit F (DIE-S81-6 data intel2 die-s81-5: lpo_F, proof_F, plan_s5; start skew 46.9,79.4 = its STA TT clk->Q)
| run | plan CA FAIL | die STA lag fail (lo TT/FF) | start-skew TT / FF | added latency |
|---|---|---|---|---|
| base x1.0485 | 0 | 1 (93.2 fi_E2_p2_r1r0__0) / 0 | 1/397 / 0/397 | - |
| base x1.0552 | 0 | 0 (166.9 / 103.3) | 2/397 / 1/397 | - |
| skew-clean x1.0552 | 0 | 0 (166.9 / 103.3) | 1/397 / 0/397 | +5 cyc |
| skew-clean + hull x1.0552 | 0 | 0 (166.9 / 121.9) | **0/397 / 0/397** | +3 cyc |
| skew-clean + hull x1.0485 | 0 (plan lo 116.4) | 0 (167.4 / 122.3) | **0/397 / 0/397** | +3 cyc |
| base + hull x1.0552 | 0 | 0 (166.9 / 121.9) | 3/397 / 0/397 | - |
No CA regression (0 FAIL everywhere).  S81 closes with --start-skew-clean + the one-interval hull at both spice scales:
CA 0, lag >= 100, start-skew 0/397 TT+FF, +3 cycles.  NOTE for DIE-S81-7 / NUMBER-CHECK: without the hull, x1.0485 has 1
die-STA lag FAIL (93.2 ps < 100, fi_E2_p2_r1r0__0; plan said 105.4) with or without --start-skew-clean; the hull plan
fixes it (167.4).
--count-align-key region does not apply to S81/HEAD binds (one origin per partition, no bind parts: die_sta_related
refuses it), so they run with the default key, which is the same thing there.

## (3) HEAD sp5 (DIE-HEAD-5 ival uni_lca form, proof_lca, start skew 40.9,89.7)
Base and --start-skew-clean are identical (0 tree edges below 116.2 ps, 0 PAD, 0 added cycles; plan crossings/regions
equal): CA 427 D4 0 FAIL, lo 134.7; die STA TT lo 249.6 / FF 264.2, start-skew 0/325 TT + FF PASS (= DIE-HEAD-5).

## Scripts
run_qc.sh / run_s81.sh / run_head.sh (chains), tp_search.py (greedy --tree-parent search).
