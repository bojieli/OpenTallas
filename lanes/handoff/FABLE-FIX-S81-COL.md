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
