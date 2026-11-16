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
