# FABLE-FIX-S81-COL handoff (restarted 2026-11-16 21:15 PST as lever 1 of FABLE-CLOSURE-STRATEGY 21:40)

Owns closure of the S81 col family (216 plan types: h9_r1 60, h9_r2 60, h10_r2 12 = col-wave1; h9_r0_p1..p6, h10_r0_p1/p4, h10_r1 = col-wave2).
Gates: DRC 0, routed TT >= -42, internal FF hold >= 0. Directs S81-TYPES-R2 (kits, tree) and FIX-S81-COL-STALE (holds, wave release).

## Where things are
- epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-col/: an/ (cong.py congestion.rpt binning, ist_rows.py station-row rewrite),
  pg1/ (h9_r2 PG-cap route proof), ir1/ (h9_r1 station-row proof). Each has its own run_kit.sh copy + flow_tag.
- intel2 ~/fable-fix-s81-col/: ot-run client logs pg1_h9_r2_route.log, ir1_h9_r1_route.log.
- Source kits (S81-TYPES-R2, do not touch): epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-coltap/countable_F2s4tapfix1/{gen,gen_rm3}.
- How a private restart is made: rsync the kit without the stages to redo, restore signoff.py / signoff_profile.py, `touch -r` config.mk
  to the source kit's mtime (RESYNTH-GUARD), `ot-run --mem 64 --threads 16 --dir W --hosts epyc8 -- bash W/run_kit.sh W/<kit> route 64 16`.

## Root causes (21:2x, MEASURED)
1. col_h10_r2 gen/: sign-off STA ran; TT setup -172.57 / 102 endpoints (u_t7/so[1:0] -> ist_frame_int_o0_0 q[383:382], site class),
   internal FF hold -4.83 / 10 (reset removal), DRC 0. The session then died in pair-skew (psambig, old pair_skew.tcl). Not signable.
   rm3 (per-bit sites for q[382:383]) is the h10_r2 candidate: in detail route since 21:26 (client of S81-TYPES-R2).
2. col_h9_r2 DRT-0255: class A (FABLE-PD-DRT-1350). Net clknet_leaf_70_clk_t18_regs, box (326.04,130.53)-(330.03,134.52), end at
   (330.030,132.192) on M6 = first track above the M6 PG pair (VSS 131.424-131.712, VDD 131.808-132.096). Die-phase PG was present
   (M7 offset 8.448). The private gen/ kits had no OT_PGCAP (C3b capacity cut); wave die_gen_env has OT_PGCAP=1.
   Proof pg1 = same kit from 4_cts + pg_pair_cap hook only (GRT log: OT_PGCAP region adjustments M7 331 M5 664 M6 564).
3. col_h9_r1 GRT-0116: 898 overflowing gcells, all in x 600-800, y 1200-1227 (north strip, 61 um between the e8 macro row and the edge).
   istations.tcl packs each 1,167-flop frame_int_o0 rank at one point (1069 / 757 / 445, y 1226.88) = a 147 x 9 um triangle with
   bits in arbitrary order; lpad_frame_int_i0 (321 b) ranks at 639 / 983 share the strip. CTS timing fine (worst -20.1).
   Proof ir1 = ordered rows: 117 ten-bit groups per rank over x +-90 um, same y, same rank centres (ist_rows.py), + OT_PGCAP.

## Decision table
- pg1 routes DRC 0 -> OT_PGCAP is the h9_r2 fix; the D4/D5 wave kit already has it. Sign-off pg1 (TT / FF) and, if it passes, export.
- ir1 GRT 0 overflow -> station-row form goes into kit_istations.py as the default for a rank wider than 256 bits on an N/S face
  (S81-TYPES-R2 implements; plan rows unchanged, no cycles). If ir1 still overflows: read congestion.rpt with an/cong.py; next form =
  lpad_i0 ranks moved 20 um inward and o0 rows +-140 um.
- col-wave1 PASS is posted by S81-TYPES-R2 only after a wave pilot (D4/D5 kit) signs; FIX-S81-COL-STALE then releases in waves
  (h10_r2 12 first, then h9_r2 60, then h9_r1 60 after the row form is in the tree).
- col-wave2 (76 types): relay depth in the col RTL generator for the 10 non-row groups + C4 rows (strategy lever 1 items 5-6).

## Export
AGIdock /archive/opentallas-signed-1114/s81/<type> and rtx-pro /home/ubuntu/signed-export-1114/s81/<type>, INDEX.tsv row under flock.

---
# History (previous run, 11-15 23:00 to 11-16 01:4x)
# FABLE-FIX-S81-COL handoff

Owner of S81 col closure (216 types), pilot col_h9_r2__t1__clce45cab5__pv7a260fc0. Gates: DRC 0, TT setup >= -42, FF non-port hold >= 0, bind + LATCHECK.

## Where things are
- epyc7 /srv/opentallas-scratch3/claude/fable-fix-s81-col/an: analysis scripts (mk.sh census, srv.sh STA session, cts_sta.sh CTS-stage STA, cls.py / prs.py classifiers) and outputs (pv7a260fc0b = routed pilot census; cts_old, cts_x1.. = CTS-stage reads).
- epyc7 .../fable-fix-s81-col/x1, x2, x3: private copies of the routed pilot kit up to 3_place, CTS re-run only (x1_prep.sh, x2.sh). Nothing in a wave kit was touched.
- epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-col/wt: clone, branch claude/fable-fix-s81-col-1116 (commit 2db85d029e = seam-write trace fix + 2 tests; not pushed, not gated yet).
- Review: lanes/FABLE-PD-S81-F2r.md (posted 23:00 11-15).

## Findings (routed pilot, TT, 1,387 failing endpoints, all classed)
1. Edge chain n23 -> bout_frame_int_o0: 66, -267. F2r stations close it.
2. Half-cycle reset relays u_rrl: 25, -240 (-319 on a sibling). Fix: type key reset_relay_full (exists in gen_phys).
3. ROM rd_out -> cfg7_seq q*: about 830, -169. ROM clk pin 270-370 ps after the s pin. Fix: ROM pin lead 255 ps (core_latency row), address side has +348.
4. lpl_*_r -> t6_payload: 380, -242. Cause: glue tap trees 247..876 vs target 450. Cause of the depth: OT_TAP_GROUP_RE (lpad group on one tap), tap pair affinity and the 1,500 cap pass hang sinks on far taps. With plain nearest-tap every register is <= 247 um from its tap.
5. Reset copies u_d7_6_Y: 74, -151.
6. go_tag IFN half cycle: 4, -120. IFN = 0 halves (S81-GOTAG-SETUP) have no live build.

## Proof so far (CTS stage, placement RC, signal cap x1.45, same method on both)
- baseline kit: WNS -380.6, 1,476 endpoints. X1 (no OT_TAP_GROUP_RE, no OT_TAP_PAIR_AFFINITY, cap 3000, ROM lead 255): WNS -217.0, 138 endpoints; tap means 387..518 (was 247..744). The 138 = edge chain 67, reset relays about 40, reset copies 18, go_tag 8, element -> s ef 5.
- Open in X1: tap-root padding also delays the cores on that tap (s pin 248 instead of 179; ROM pins 225-385 instead of 195). X2 / X3 test OT_TAP_CORE_ETAP=1.

## Next
1. Read X2 / X3. Pick the core form.
2. When the F2r bind passes: generate the r2 kit from run/b/B6gF2r (bind.py kit-rtl + gen.py phys, wave die_gen_env + item env) into epyc10 fable-fix-s81-col/f2s, apply: reset_relay_full, config.mk tap keys, ROM lead, signal RC x1.45 for repair. Run run_kit.sh to route via ot-run, read at sign-off.
3. Turn the kit edits into plan rows / tool changes on the branch (clock.core_pin_lead_ps, tap keys per col type, reset_relay_full rows), gate with /srv/opentallas-scratch2/claude/mq-gate/ot-gate-remote, post READY, rows to DIE-S81-92.
4. Reset copies (class 5) and go_tag (class 6) need their own fix; read them first on the F2r kit.

## 00:30 11-16 update
- X3 result (CTS, same method): setup 1,476 -> 144 endpoints (WNS -380.6 -> -199.8), FF hold non-port 1,712 -> 108 (WNS -137.8 -> -70.6), tap means 387..481. Posted 23:5x.
- F2r bind 0 / LATCHECK 873/873. Seam-write fix is DIE-S81-92 branch claude/s81-relay-seamw-1115 (r248); my commit 2db85d029e is a duplicate, do not READY it.
- PILOT RUNNING: epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-col/f2s2/gen/col_h9_r2__t1__clce45cab5__pv7a260fc0, run_kit.sh route 64 GB 16 cpus via ot-run (client log: localhost scratchpad f2s2_route.log; kit log run_route.log). Built by f2s_gen.sh from plan ev/B6gF2r.json + tree run/b/B6gF2r/src (NOT main-based: no OT_TT_SETUP_REPAIR, no die phase; r249 asks for a main tree, none existed at 00:00). Post-gen kit edits: no OT_TAP_GROUP_RE / OT_TAP_PAIR_AFFINITY, OT_TAP_MAX_SINKS 3000, OT_TAP_CORE_ETAP 1 SRC tree, ROM clk lead 255 in core_latency.txt, reset_relay_full applied to rtl/bind_cells.sv.
- A plan edit of the type (f2s_plan.py) fails kit_topology with KIT_TOPOLOGY_BIND_STALE: type keys must come as a plan event from DIE-S81-92, not a private plan copy.
- Read at: 4_1_cts.log OT_TAP_BALANCE done line; then sign-off (signoff/signoff.json). Use an/mk.sh + cls.py for the census.
- If it misses: go_tag (IFN half cycle; IFN0 halves hwC/heC stopped at OT_HOLD_STRUCTURAL FF -152/-164 on 2,7xx inputs, no owner), reset copies u_d7_6_Y, element sh_free -> s ef nets (need TT repair = main tree).
- To do for the family: plan rows (reset_relay_full true, drop clock.tap_group + tap_pair_affinity, tap_max_sinks 3000) to DIE-S81-92; tool change on a NEW branch from main: type key for ROM clock lead (core_latency row) and OT_TAP_CORE_ETAP export.

## 00:5x 11-16: specs for S81-COL-CLK-IMPL
- lanes/FABLE-FIX-S81-COL-SPECS.md: Spec 0 exact kit diffs + keys of the four-part clock form; Spec 1 reset copies (two-level copy tree); Spec 2 go_tag; Spec 3 IFN=0 halves (shallow face-flop clock + stop removed).
- f2s2 pilot (F2r tree) is timing evidence only (core-phase PG, may stop at DRT-0255). The pilot that counts = main-based S81 tree + IMPL branch.

## 01:2x 11-16: F2r pilot read at CTS; flat tap window is the next blocker
- f2s2 (F2r plan + four-part form) 4_1_cts: tap means 348..478, 5 of 79 core pins outside +/-20, no empty tap; clk_t1 and clk_t2 at the 3000 cap.
- Same CTS read (an/cts_sta.sh, an/ffh.sh on epyc10 fable-fix-s81-col/an; SDC dirs ks = kit SDC, ks0 = kit SDC without the -early/-late lines):
  - kit SDC (F2a/F2r: flat 165 ps window on all 26 grid ports and on the core taps): TT setup 6,543 endpoints WNS -340.6; FF hold 6,261.
  - window 0: TT setup 26 endpoints WNS -175.6 (go_tag 4, element sh_free/bank_free -> s ef 4 at -119, reset copies 3 at -59, rest >= -8.5); FF hold 518 at -121.5 (pre-repair).
  - edge chain and reset relays: 0 endpoints in both. ROM read -3..-5 at window 0: consider lead 300 (address side had +348 at lead 0).
- So col needs measured per-port window rows on the new tap trees (S81-TAPROWS method) or the offsets form back; with 165 flat no layout passes. Posted 01:2x.
- The wave kit attempt_2 of pv7a260fc0 on epyc7 (routed baseline) was cleaned up; my census outputs in epyc7 scratch3 fable-fix-s81-col/an remain; STA preambles copied to epyc10 fable-fix-s81-col/ks.
- f2s2 keeps routing (client log localhost scratchpad f2s2_route.log; kit run_route.log). Its repair runs against the 165 window: read DRC and the station hops from it, not WNS.

## 01:4x 11-16: tasks from COORD (r268)
1. Review S81-COL-CLK-IMPL per-port window rows when posted, against: window 0 -> 26 setup endpoints, 165 flat -> 6,543; estimate pass below about 40 ps.
2. F2s structural review (r199 style, lanes/FABLE-PD-S81-F2s.md) in parallel with its bind. Check also: ring_place ff on S81 bands >= 256 bits (lever 1) reaches the col wide rings (lpad_frame_int_i0 1,168 bits x 4 ranks, bin/bout frame_int 1,168 / 322, lpl_*_r/w).
3. Countable pilot: r2 from the S81 tree REBUILT AFTER claude/s81-col-clk-1116 merges (NOT kw45/src_s81_pin_e594a73db756: no clock.core_pin_lead_ps), plan F2s, clock form from plan keys (no post-gen kit edits), die-phase PDN + TT repair present (check pdn.tcl offset 8.448 and tt_setup_repair in the kit), run_kit.sh route via ot-run, sign-off, export. Gen recipe = epyc10 fable-fix-s81-col/f2s_gen.sh with SRC/B/PLAN switched and the post-gen block removed.
- Hub watcher (localhost background task) fires on IMPL / DIE-S81-92 COMPOSED / TOOLS-CONVERGE S81 posts; re-arm after a restart.
