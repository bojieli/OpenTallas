# FABLE-PLAN-HEAD-NF15D2 (Fable PD review, 2026-11-17 ~08:55 UTC) -- to HEAD-DIE-R

## A. NF15d2 plan event (post-adoption review; adopted as NF15d2r1) -- no blocking finding
Verdict: ADOPT stands. Nothing to block with numbers.
- In-tree plan NF15d2 vs NF15c: 44 leaf diffs = 1 note, 13 tree-path rebases (sink_bins_file / census_file / lib / budget_owner),
  u_chn origin 1900.8,250.56 -> 1548.0,109.44 (+ its note), 12 reset_start_raw_exports fields + xy of row 5, and the 12 matching
  landing_contract pins[9..14] source fields. No outline / pin / cycle / other-type delta.
- Reset rows: 5 of 6 are the SAME relay renumbered (u_rrl_42/12/41/9/10 -> 40/10/39/7/8, depths d6/d4/d5/d1/d2, xy unchanged);
  only rst_start_raw_5 moved (u_rrl_80 -> u_rrl_14, d3, xy 1623.57,32.11 -> 1646.19,16.79, 31.1 um to the pin). Longest relay
  to pin is raw_0 at 320.9 um (unchanged, < 405 um). landing_contract and exports agree row by row.
- G0: 0 errors; warnings 231 -> 228. Removed: 4 u_chn "perpendicular face" warnings. New, all ADVISORY:
  (1) R-REACH-3 window_far hd_serdes coll_i0 512 b x 210 um from its consumer (163 bit-mm, ~1085 face-net buffers);
  (2) u_chn origin 1548.0,109.44 is off the 8.64-um lattice; (3) u_cmem r_addr_in / w_addr_in face-away cos -1.00 -> -0.79.
  Seam reach: worst cut 0.0579 and worst partition segment 0.3587 are identical to NF15c; the move is internal to hd_serdes.
- Not checked by me: the republished hd_serdes wrapper text itself (relied on cohort 26/26 + bind PASS + LATCHECK 329/329),
  and the corrected-receipt re-publish (bdd769) made after my inputs were written.

## B. Die STA landing-ring hold (nf15c_real4, TT -2023.6 / FF -1518.8) -- REAL VIEW DEFECT, confirmed
Not a modelling artifact (no double-counted landing latency, clocks are propagated, ILM = full view within 0.1 ps on this path).
- Signed view hd_st_n3_turn (nf15_pin_pg_1116): clk_t9 -> fclk_out_u1_o and clk_t13 -> fclk_out_d1_o each pass 96
  delaybuf_otstb BUFx4 between clk_tN_tb0_d5/d7 and clkbuf_0_clk_tN (192 cells, every chain net fanout 1).
  TT: clk_t9 -> fclk_out_u1_o = 2724 ps, of which ~2460 ps is the chain; the launch flop u_ft_u1_s5 clock is 435 ps.
  nst4's own fclk_in_u1_i tree to the face flop is only 137 ps. So fclk reaches nst4's face ~2.1 ns after the data launch clock.
- Cause: tools/die_plan/subtree_balance.tcl padded a forwarded-clock branch that has no local sequential sink: hi = -1e9
  sentinel read as "early", 12 buffers (cap) x 8 rounds = 96 per branch. Fixed in the tool (skip hi == -1e9; 68c5f9608d /
  main 47a7685132a per COORD).
- Scope: scanned all 21 real views in nf15c_real4/views (38 cland_fwd_* buffers): ONLY hd_st_n3_turn has otstb cells on a
  forward branch (2 of 2). The 5 stand-in types (hd_ctl, hd_host_w, hd_lep0N, hd_mesh, hd_serdes) are not covered: scan each
  new view (fwdscan.py below) before it enters the die STA.
- Fix: remove the 192 pads (clkbuf_0_clk_t9.A <- clk_t9_tb0_tree, clkbuf_0_clk_t13.A <- clk_t13_tb0_tree) = the recovery
  route HEAD-DIE-R already runs; re-sign the view with the fixed tool.
- What-if proof (minimal pair nst3_turn -> nst4/u1_i, full real views + SPEF, die tap latencies, 25 ps hold uncertainty,
  chains bypassed in the netlist only, original SPEF, die net RC not included):
  | corner | form | setup worst | hold worst | neg |
  | TT | as signed | +2623.1 | -1997.4 | 515/515 |
  | TT | pads bypassed | +474.2 | +180.8 | 0 |
  | FF | as signed | +2177.2 | -1493.3 | 515/515 |
  | FF | pads bypassed | +572.2 | +132.2 | 0 |
  The as-signed pair reproduces the die run within 26 ps. The bypass numbers are an estimate until the re-routed view exists.
  I did NOT rerun the full die STA (2 x 18 min); rerun it on the recovered view.
- What stays after this fix in the same die run (not caused by the pads):
  (a) tile ring landings, capture u_cland_i/u_ring.dch[*].sd_c (rising-fclk write): TT 239 seams worst -56 (skew 185),
      FF 271 seams worst -70 (skew 157), ~22k TT / ~64k FF endpoints, almost all one type (hd_tile). The falling-write rings
      (st types, s_d DFFE_NP) have +380. Fix in the hd_tile kit: input hold on the cland d pins vs fclk (data hold cells per
      12.4a a1, ~+80 ps at FF incl. the 25 ps uncertainty) at its next re-sign; not looked into further.
  (b) arst_n / start_i wavefront seams: 240 + 240 seams at TT, worst real-view -1013 (skew ~1.2 ns between clock regions),
      stand-in -1626. HEAD-DIE-R already owns this as the regional root-phase item; not diagnosed here.
  (c) 22 stand-in seams untimed; real-view setup TT -396.2 at sp4->sp3/start_i (24 endpoints) not looked into.

Files (epyc7): /srv/opentallas-scratch2/claude/fable-plan-head-nf15d2/ -- fwdscan.py (view scan + bypass netlist), pair.py,
pair_{TT,FF}_{base,bypass}.log, mini4_{ilm,full}.log (expanded fclk_out path), whatif/hd_st_n3_turn/6_final.v.
