DIE-KV-21 2026-10-28 (KV die owner; successor of DIE-KV-20 b555bf16af).  Runs: intel1:/srv/opentallas-scratch2/claude/die-kv-21-1028.
CHECKED-own = my run / my arithmetic on raw JSON; no independent NUMBER-CHECK.  Builder = MAIN die_trial 8b172e6b98 (no fork; kit_a
= DIE-KV-20 recipe on main reproduces kit_p20 ctree.v byte-identical); fitter = tools/die_plan/fit_dme_stage_cal.py from DIE-S81-18
(READY 9e0f2cfb03, not yet on main; used read-only).  Gate = DIE-KV-20 gate_p20 recipe (main 6a56d5811 die_sta_related, count-align
bind of record DIE-KV-15 st_fall_bind_parts, 3 signed views), gate number --clock-cal spice_edge.

(1) Benches (DIE-KV-19 LEAF_LC): lc PASS T=1/129/2049/8192 (errors 0, exit 0); lcm FAIL T=129 errors 32 (exit 1) -> READY posted.

(2) pv_S_6/pv_S_7 region trees on the fitted KV stage model (ESTIMATE.txt first).
  Trees (all: GRT0 incl clock TT/FF overflow 0, usage 2.37 %; duty 0 outside 45-55, MPW est fail 0):
   b = DME delay pv_S_6+7 on the htree-leg fit (CLK-MODEL-SWEEP-1 cal_est_kv): built model rms on its own DME legs 22.6 ps TT
       (the htree-leg fit does NOT transfer to DME legs) -> refit (kv_cal_fit_b.json, 94 legs, rms 6.0).
   c = DME pv_S_6+7 on kv_cal_fit_b: refit on c legs rms 6.8 vs built 7.3 TT (self-consistent, converged).
   d/e = DME pv_S_6 only (sweep cal / refit cal); e self-consistent (fit 7.3 vs built 7.8).
  In-region late spread FF (TT):   p20 pv_S_6 70.9 (80.5)  pv_S_7 63.6 (73.0)
                                   c   pv_S_6 43.1 (43.5)  pv_S_7 46.0 (46.6)   e pv_S_6 43.1 (43.5), pv_S_7 = p20
  FF intra kit contract (W 80, spice_edge):  p20 -6.80 (8 neg) | c +6.64 (0 neg; worst = htree region pv_S_1, damage 73.36)
                                             | e -0.05 (1 neg: pv_S_7 t10->t6, damage 80.05)
  Other gate numbers c vs p20 (spice_edge): intra TT setup 328.33/328.53, FF hold -112.29/-126.36, seam FF -101.20/-100.89,
  seam kit contract +18.07/+18.31; CA TT/FF fail 0 (lo 143.2/262.6 unchanged); real-view FF hold e -57.92 = p20.
  BLOCKER for c: count-aligned START-SKEW fail 2/156 (TT and FF), reason no taps: the bind of record puts the hub_C->pv_S_7
  start retime at clock-tree node st:h3000400 (the 2nd sub-root of the pv_S_7 htree, 4 taps incl t10).  The DME region tree has
  one root, so that node no longer exists.  Same node is why pv_S_7 limits e: the h3000400 sub-root arrives 28 ps TT / 27.6 FF
  earlier than its sibling h3000300 (geometric equal-length feed of the two sub-roots).
  => kit contract >= 0 BY DESIGN needs tree c + a count-align re-bind of the one start crossing hub_C->pv_S_7 onto the DME tree
     (count_align_plan start tree on tree c; RTL count unchanged expected, UNCHECKED).  Not done here.
  Render render_pvS67.png (viewed): DME trees reach all 48 taps with L legs, compact; no stray legs.

(3) gate_views: no new signed KV views since DIE-KV-19 (only e2/e5/e6); priority message to KV-KITS-16 posted (e0/e1/e3/e4/e7).
