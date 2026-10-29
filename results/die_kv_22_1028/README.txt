DIE-KV-22 2026-10-28 23:10 PDT (KV die owner; successor of DIE-KV-21 efa98a0ee3).  Runs: intel1:/srv/opentallas-scratch2/claude/die-kv-22-1028.
CHECKED-own = my run / my arithmetic on raw JSON; no independent NUMBER-CHECK.  Tools: count_align_bind + die_sta_related = DIE-KV-20
gate tools (main 6a56d5811); die_trial + fit_dme_stage_cal = DIE-KV-21 main copy (no fork).  Gate number = --clock-cal spice_edge.

(1) Count-align re-bind on DIE-KV-21 tree c (pv_S_6/7 DME, rest htree) - bind.sh / gate.sh.
  a = repro of the bind of record (DIE-KV-15 st2.sh fall recipe on proofF_fb): 3595 ports / regions / start ports IDENTICAL [CHECKED cmp].
  b = same recipe on proofF_c with --start-prev record (c = without; b == c byte-identical).  CA verify 3595 cycles, 0 loop errors,
      0 window violations, sim min 105.2/128.3 ps.
  Gate (b on tree c, spice_edge): CA TT/FF fail 0 on 3595 crossings, worst lo 143.2/262.6, START-SKEW 0/161 TT and FF -> COUNT-ALIGN
      PASS, landed PASS; intra TT setup 328.33, FF kit contract +6.64 (worst pv_S_1 htree 73.36), HB4 0.0, real-view FF hold -58.23;
      seam kit contract +18.07.  spice (record comparison): CA lo 107.0/116.0 PASS, start-skew 0/161.   [CHECKED-own]
  NOT an RTL no-op (expected unchanged was wrong): the start tree follows clock-tree nodes and tree c moves pv_S_7/pv_S_6 roots
      (+100/+80 ps FF), so the south start chain re-plans: hub_C->st:h3->st:h3000->... replaces hub_C->st:h3000400->pv_S_7->pv_S_6...
      362 ports change K, 25 ports DEPTH 4->8 (depth-8 total 25->50), 14 ports sched_lat +1 (total 9730->9742), 54 regions
      n_region_frame +1..+2, start ports 156->161, max origin cycles 28->30 (bind_diff_b_vs_record.txt) [CHECKED-own].
      => tree c + bind b needs a KV RTL event (compose/bind/LEC/image regen/peer link) before freeze.
(2) ESTIMATE (ESTIMATE.txt, written before the build): all-region fitted DME -> worst part ~46 FF, kit contract ~+17.  BUILT (cheap,
  ~15 min/tree) and MEASURED: estimate does NOT close.
    f = all-region DME, KV-21 cal (c), with KV-20 phy pads: intra kit contract -95.91 (hub_C 175.9), seam -52.21 (pads overshoot).
    h = same, no pads: intra -95.91, seam +18.38.  Own-leg refit on 3712 legs: rms 8.06 vs built 8.78 TT but max resid 117.6
        (KV-21 cal had k2 < 0, fitted on 94 short pv_S legs; long legs under-priced -> hub_C rows 150 ps apart).
    i = all-region DME on the h refit (k2 > 0), no pads: converged (rms 7.26 vs built 7.40 TT), GRT0 TT/FF overflow 0 (2.37 %),
        duty 0 outside 45-55, clock wire 1.71M -> 1.15M um; CA PASS 0/204 start-skew; seam kit contract +43.3, real-view -49.18,
        BUT intra kit contract -37.91 (pv_N_4 damage 117.9; in-part FF spread pv_N_4 102.7 vs 30.6 htree, hub_C 101.4 vs 39.7,
        pv_N_7 98.8 vs 42.8; medians hg/hgi ~32 = htree, pv 57.0 vs 46.0).  [CHECKED-own, part_spread_FF.tsv]
    Root cause (UNCHECKED, one region read): pv_N_4 DME root branch ...30 costs 409 ps on its first leg vs 138 for sibling ...31,
        taps end 2815..2918 ps; the per-leg model is fine on average (rms 7) but the delay-mode DME balances one long elongated
        leg against many short legs and the error on that leg (+~100) is not averaged out.  The htree is better where the region
        is a symmetric tap grid (most KV regions).
  => All-region DME rejected on measurement.  Record proposal = tree c + bind b (intra +6.64, seam +18.07, CA/start-skew PASS).
(3) gate_views: no new signed KV views (e0/e1 still in KV-KITS-16).  Views are passed per TYPE (--core-view type=dir), so e4 (type e6 at
  MX) and e7 (type e5) already use the e6/e5 views; MX pin mirroring inside die_sta_related UNCHECKED.
