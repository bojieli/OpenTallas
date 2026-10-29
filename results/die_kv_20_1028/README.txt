DIE-KV-20 2026-10-28 (KV die owner; successor of DIE-KV-19 a9d89ec385).  Runs: intel1:/srv/opentallas-scratch2/claude/die-kv-20-1028.
CHECKED-own = my run / my arithmetic on raw JSON; nothing NUMBER-CHECKed independently.  Gate tools = main 6a56d5811 (git archive).

(A) FF hold -97.29 ps on the 9,600 real-view intra pairs (DIE-KV-19 view-mode gate) -- ROOT CAUSE [CHECKED-own]
  Worst pair: hg_WS_7 t8 (launch = signed core kv3_head_eighth_e6 view) -> t3 (capture = 'budget').  t3 clocks only head1_e1
  (kv3_head_eighth_e1, NO signed view yet), so the gate puts the declared register there: tap + 202.5 FF common latency +
  DFFHQNx1 hold 17.44 = 219.94 ps.  Decomposition (FF, clock-cal spice, record proofF_fb):
     e6 out_min 288.90 - budget capture 219.94 - unc_h 25 - clock damage 104.77 - clock OCV table 36.5 = -97.29
     damage 104.77 = nominal late skew t3 vs t8 49.6 (t3/t2 = subtree 'h...110' latest in the region) + pin-cap late/early range
     below the LCA 55.2 (liberty range, not a derate; CA-OCV-1 NUMBER-CHECK: no double count).
  (1) clock calibration: with --clock-cal spice_edge (NUMBER-CHECK-INV-1 passed; COORD: freeze-gate number for inverter trees)
      the same pair: damage 64.32 -> real-view FF hold -57.92 (neg 3501), BOTH-REAL +46.08 (neg 0), intra kit-contract -6.80
      (need 86.80, 8 pairs, pv_S_6), all-pairs budget FF hold -126.36 (HB4 plan model 0.0).  spice: -97.29 / +7.65 / -62.78.
  (2) the remaining -57.92 is the MIXED model, not a physical path: the signed e-family views require in_hold 124.6-129.8 ps
      FF at the core clock pin (ETM, insertion included) vs the 219.94 budget -> the budget capture is ~90 ps more pessimistic
      than any signed head_eighth core.  Estimate with an e-family view on t3: -57.92 + 90.2..95.3 = +32..+37 ps (UNCHECKED,
      proxy = e2/e5/e6 in_hold).  Every negative real-view pair has a budget end (both-real neg 0).  -> NOT a freeze blocker
      by itself; it closes when the e0/e1/e3/e4/e7 (+ ectlk) views land (KV-KITS).  No hold ECO, no pad (12.16).
  (3) the residual STRUCTURAL item: intra kit contract -6.80 (W 80) on 8 pv_S_6 pairs (damage 86.8, p99 55.8) = region-tree
      in-region spread; CLK-MODEL-SWEEP-1 shows pv_S_6/pv_S_7 are model-limited (geometric builder, cal residual 68.8 TT).
      Fix by design = region builder on the fitted KV stage model (n*d0 + k1 L + k2 sum Ls^2 + kf(fo-1)) -> next lane.

(B) KV phy-tap pads re-derived from the CURRENT tree (CLK-MODEL-SWEEP-1 finding) [CHECKED-own, routed GRT]
  pad_rederive.py: per phy tap, unpadded arrival = routed tap - measured pad chain; per-pad stage TT 24.4 / FF 18.9 ps (BUF pad
  FF/TT 0.77 vs inverter tree 0.88, so one count serves both corners); n = argmin max-corner region spread (ties -> fewer).
  Old (DIE-KV-5 pad_it2) 136 pads -> new 89 (31/32 changed).  Rebuilt tree (kit2/grt/chain2 = DIE-KV-15 recipe, only --tap-pad
  changed; tree nodes byte-identical): GRT0 incl clock TT/FF overflow 0, usage 2.37 %; duty TT 47.8-52.3 / FF 47.7-51.3 %,
  0 outside 45-55.  Measured on the rebuilt tree: worst phy-region spread TT 99.1 -> 58.9 ps (= the pc taps alone; the phy tap
  no longer sets it), phy tap later than its region max: 30 -> 2 regions, worst +56.1 -> +3.1 TT.
  Does it feed the -97?  NO: every phy partition has exactly 1 tap (no intra pairs) and no signed view (no real-view pairs);
  intra numbers are byte-equal record vs p20.  It feeds SEAM: FF seam hold (spice_edge) -124.34 -> -100.89, seam kit contract
  -3.39 (neg 1) -> +18.31 PASS; TT seam -152.22 -> -101.82.
  Count-aligned bind of record (DIE-KV-15 st_fall_bind_parts, unchanged RTL) verified on the new tree: CA TT/FF fail 0,
  start-skew 0/156, worst lo spice 107.0/116.0 (record 106.5/108.4), spice_edge 143.2/262.6 (record same) -> PASS, NO rebind.
  Proposed KV gate tree of record: die-kv-20-1028 proofF_p20 (kit_p20).

(C) test_r8_write_groups: FAILS on clean main 6a56d5811 (test_bindview_raw_asbuilt_same_landing n 0 != 2) [CHECKED].  Cause:
  r8.py ebe645af6 (COORD 10-28 ruling (3)) now writes asbuilt = raw lane depth + asbuilt_group, so bindview on a new table has
  nothing to convert.  KV-owned test (DIE-KV-13) -> fixed here: new-table bindview is idempotent (n 0, fields asserted) + the old
  table form still converts (n 2).  5/5 PASS.

(D) pv_pair LEAF_LC benches (DIE-KV-19): still in the Verilator C++ compile at 22:1x (started 20:48) -> successor collects
  intel2:/tmp/dk19_bench_lc.log (must PASS) / dk19_bench_lcm.log (must FAIL).
