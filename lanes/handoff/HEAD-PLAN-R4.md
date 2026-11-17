# HEAD-PLAN-R4 handoff (Opus), successor of HEAD-R3 (Fable). s81_head ASAP7 833 ps. Started 2026-11-17 ~07:30 PST.
Read lanes/handoff/HEAD-R3.md for the NF15e -> NF15f decision (hop halving + corridor +181.44, die 17737.92).

## (1) u_lep RX-head rank RTL (RXH)
- Branch claude/head-lep-rxh-rank-1117, worktree epyc9 /srv/opentallas-scratch2/claude/head-plan-r4/wt (ot-lane-clone, cone tools rtl
  + physical/die_plan/s81/bind/source_modules/portfix178).
- Generator tools/s81_head/head_lep_nr_sources.py: opt-in core param RXH (default 0). RXH 0: g_rxm reads *_h aliases (no flop,
  no added cycle). RXH 1: kept leaves u_core.u.u_lep.u.g_rxh.g_l[0..3].u_st (552 data FF each = 2,208) + g_rxh.u_ctl (44 control
  FF on rnx): rhd + every ring-side term of g_rxm (rne/relp/rpb, ring_meta_regions, rhk, look-ahead rnex/rringx/rhkx/rtagx,
  rne_return) delayed one edge; ri / mu_rt / ml_w all +1 together; replay ml_rd/ml_rv, pops, credits, perr unchanged.
- ot_s81hd_lep0N_core / noidx_core: RXH param pass-through. lep_calendar: Stages.rxh (0/1), leg 'rx_head.ri+mu_rt+ml_w',
  state bits +2,252, params() adds RXH only when 1 (old tuples byte-same), NF15F constant. check_calendar PASS.
- Bench tb_head_lepk_stages + head_lepk_stages_bench.sh: RXH_DUT, cases nf15f / nf15f_norxh / rxh_only, mutants
  MUT_RXHBIT / MUT_RXHSKEW (must FAIL). Runs: epyc9 head-plan-r4/b_<case>, bench1 (plan zero mut_dbit). Default equiv
  (RXH 0 vs main) head-plan-r4/equiv0.
- Die LATCHECK unaffected (provider leg inside hd_lep0N; external lane fixed_cycles unchanged).
- RESULTS: RXH 0 default equivalence vs main PASS (yosys equiv_induct, E9 unit oth-ubuntu-4014994-1794927585, equiv0/out).

## (2) NF15f geometry event g1 (E10 /srv/opentallas-scratch2/claude/head-die-r/nf15e_e10/hr4)
- code_r4 = private copy of nf15e_e10/code (tools real copy; rtl now a REAL copy of the kw45 src rtl, old symlink renamed
  rtl.kw45link) + RXH files. kw45 src tree untouched (read-only, write was refused).
- compose_g1.py on prep_f1 (3210bf1f): type cut y>=665.28 +181.44 (415 coords; 2 W/E collector bands stretched), outline
  1892.16 x 1408.32, upper pair cores at 846.72; model corridor-word groups (rxbank/txread/rop, krx1 re-site) in the
  allocator frame; chains renumbered with 28 REAL relay anchors at the allocator columns (max offset 60.48 um) + RXH
  lanes/ctl; RXH 1. Parent: die 17712 x 17737.92, 6 north hd_serdes + 6 PHY domains/bumps/IO + 3 channels +181.44,
  W/E full-height channels stretched, no overlap / outside. landing_remap (all types) re-picks reset relay names by site.
- run_g1.sh RUN: compose -> landing_remap -> republish (provider calendar nf15f_g1) -> receipt, kit RTL, strict bind,
  cohort, LATCHECK, G0.  run_alloc_g1.sh RUN: edges_g1.py splits every relayed hop at its real anchor, alloc_r4 (no
  virtual relays, band 490..851.44).
- g1/g1b failed in republish GEN (reset relay names renumbered: hd_lep0N, then hd_st_turn) -> g1c remaps all types.

## (3) 11-17 status (after g1c + a2)
- RXH benches: rxh_only PASS, mut_rxhbit / mut_rxhskew CAUGHT, plan (vF) PASS, RXH0 equiv vs main PASS.
- BLOCKER: the NF15f tuple (KTX 1111 KRX 2660 TXI 2442 PIN 6 POUT 8) fails tb_head_lepk_stages with and WITHOUT RXH:
  perr=1 at cyc 4053 phase 2, hang ri 1018/1040 lw 6/80.  The 3210bf1f gates never simulated the tuple.
  Bisect on E9 head-plan-r4/x_{dbg,krx,ktx,io} (bisect.sh): KRX-only / KTX-only / PIN+POUT+TXI-only.
- Geometry g1c (E10 hr4): compose/remap/republish/receipt/kit RTL PASS; G0 10 abutment errors (5 north hd_serdes not above
  lep0N moved +181.44).  compose_g1.py fixed: only the lep0N column moves (not yet rerun).  bind.log: --out must be
  repo-relative (run_g1.sh fixed).
- Corridor model: column-centre anchors 3244 unassigned / 8345 reach-bad; reach-optimal re-site (place_anchors.py,
  hr4/anchor_a2) 2387 unassigned / 3275 reach-bad (g_kl 1106, g_pin 1104, g_tx 1065), worst cut 1.17, krx3_r0 > 405 um.
  NOT < 90 % / 0 unassigned.
- Lever 7(a) relay access (vert_access.py, anchor_a2/relay_access.json): pin access 0.02-0.03, FF util 0.21-0.27 fine;
  vertical M5+M7 drops exceed 0.9 of supply at 22/27 anchors (worst pout_r4 2.19).  Anchors must be wider (span along x,
  h 12 -> w x2) or split per source column; growth alone does not fix it.
- Lever 7(b) uarch_model.s81_head_lep_nf15f_stage_calendar_model added (ring legs lane0..3 = 18/26/26/20 vs NF15e 9/13/13/10);
  production calendar rerun still owed.  7(c) die_clock.face_pin_keepouts (opt-in die.clock.face_pin_keepout_um) + 3 tests PASS.
- Branch not yet committed: wait for the tuple bisect (RTL may need a credit-depth change with the tuple).

## (4) 11-17 late: integration + credit root cause
- g1e (column-only growth + all-type republish), plan c291c4a4: compose/receipt/kit/bind/cohort/LATCHECK 329/329/G0 PASS.
- rs-series = g1e + r564 rows (old-clock) + strap_rst_ph sites, tree code_rs2 (main tools incl r564 + event rtl + RXH overlays):
  rs2 validate invocation (-I relative import), rs3 republish used code_r4 (old schema), rs4 code_rs2 rtl was a main snapshot
  (XO_HOP missing) -> rtl replaced by event rtl; rs5 running.  All harness, no gate finding.
- Tuple root cause: perr = pair A/B release collision; KRX lane 6 alone fails, KTX 1 alone fails, PIN/POUT/TXI pass; K-link
  credit depth 16 fails, 24 passes (ri/rt/lw exact, gap 4).  Isolation of which credit end (lep DR/CRED vs lane CORE_CRED;
  the lane CRED12 view is CLOSED) running x_c24k / x_c24L / x_c24kr (RXH 1).
- Evidence: ~/coord/lanes/evidence/head_plan_r4_1117/.
