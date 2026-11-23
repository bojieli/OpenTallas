# OPUS-FIX-S81-COLROM-R6 handoff (started 11-21 23:1x PST; successor of FABLE-FIX-S81-COLROM-R5, Fable 429 until 11-28)
History: lanes/handoff/FABLE-FIX-S81-COLROM-R5.md. Lane dirs: intel2 /srv/opentallas-scratch2/claude/fable-fix-s81-colrom-r5 (runitem_*.pid/.log, plans, tmp/);
new dir /srv/opentallas-scratch2/claude/opus-fix-s81-colrom-r6 (epyc9: srcJ8G fork).
GOAL: J8 col form. Rule: first col proof with final 5_1_grt.odb TT >= -42 and overflow 0 by 11-22 14:00. COORD RULING 23:3x: FAM-S81-COL-H9R0-R4 files the
single combined col set (seat fix + RELAY_MID_RE + keep rq + STAGGER [+ F seats if F closes]); I post my part to H9R0-R4 (done 23:4x), run D/E/F/G/H and
report their GRT. No separate col hand-off.

## Kits (all epyc9, work root .../kit-wave/s81/a9ed808a98d/private/<lane>/col_h10_r1__t1__cld01bb4ae_<stamp>)
- D _1121214130 (planD per-flop xd seats, J7 tools, 10 iters): post-hook CTS setup -81.07 (xd e7 xs_q -> u_u_e7_u_w ROM pin). runitem_d.pid.
- E _1121220326 (env OT_RELAY_MID_RE excl xd ROM stations, J7 seats, 10 iters): post-hook CTS setup +22.23, hold -63.79 pre-repair. runitem_e.pid.
- F _1121223001 (planD + 1212 south seats + 50 iters): placing 22:49. runitem_f.pid.
- H _1121231802 spec private_specs/OPUS-FIX-S81-COLROM-R6/..._1121231802 (planH = J7 plan + F 1212 seats; E RE; 50 iters). runitem_h.pid (intel2 3338988).
- G (COORD combined): fork J7 tree -> epyc9 opus-fix-s81-colrom-r6/srcJ8G (forkG.pid/log), then ot-build s81 col_h10_r1__t1__cld01bb4ae --tree srcJ8G
  (rebind on rt current) --ab OT_RELAY_MID_RE=<E> --ab OT_KEEP_WIRES="<wave list> ot_s81_rly:rq" --ab OT_RELAY_MID_STAGGER=1 --ab OT_GRT_CONG_ITERS=50.
- Cancelled: first G try spec _1121231436 (planF + E RE on J7 tools; inherits D -81 seats) at kit_rtl, ot-run unit oth-ubuntu-1270086-1795331713.
## Reads: CTS = 4_cts_post_hook.rpt; GRT = final 5_1_grt.odb only.

## UPDATE 01:3x 11-22
- D: GRT-0116 ovf 1725 (10 it) DEAD. E: GRT-0116 ovf 2039 (10 it) DEAD; E CTS +22.23 (timing row OK). F: CTS -72.14, GRT 50 it running. H: CTS +19.20, GRT pending.
- G try1 bind FAILED: dead_inputs resolve() vs ot-build launch-tree symlinks -> fixed main 06b2ca5293 (LAUNCH-LINK-1122). G try2 on rt 06b2ca5293cd: elab BUILT, bind running (driver intel2 opus-fix-s81-colrom-r6/buildG.pid/log; try1 log buildG.try1.log).
- ROOT CAUSE south hotspot: lpad_frame_int_i1 ranks keyed with 5 sample bits; 6300 unseated pad flops at y<100 (census epyc9 opus-fix-s81-colrom-r6/tmp/hotE/hot_cells.tsv; tools tmp/hot.sh hot.tcl cong.py).
- Kits P (planP = planH + all lpad bits at rank sites) work _1122012035, P2 (+ r[1] at 600,170) work _1122012102; specs private_specs/OPUS-FIX-S81-COLROM-R6/..._1122012055/_1122012120; runitem_p/p2.pid in fable-fix-s81-colrom-r5.
- Systemic: col_h10_r2 (520 keys i0), col_h9_r0_p4/p5 (4 keys) same sample-bit lpad keys. Posted to H9R0-R4/H10-R4/ASSEMBLY.

## UPDATE 03:5x 11-22 -- J8 COL PROOF MET (kit H)
- H final 5_1_grt.odb: overflow 0, TT WNS -40.79 (KEEP repaired from -80.13), GRT hold guard ws +30.13. Posted to ASSEMBLY-R5 + H9R0-R4 (14d6bd9497).
  Rows: planH south seats (1212 keys) + item_env OT_RELAY_MID_RE (E) + OT_GRT_CONG_ITERS=50. H continues to route/sign-off (runitem_h.pid in fable-fix-s81-colrom-r5).
- F: ovf 1186 at 50/50 (planD seats) -> residual retry; D/E dead.
- Tool fixes pushed: 06b2ca5293 (dead_inputs lexical repo-rel, LAUNCH-LINK-1122), 5c6c4945c8 (env_provenance GEN-CONSUMED-1122 OT_GRT_CONG_ITERS).
- P/P2 (lpad whole-rank seats; root cause census tmp/hotE) in CTS on epyc9 (runitem_p/p2.pid). P/P2 try1 died: sealed place landed on intel2 disk-ETA hold.
- G: bind BUILT b_dd5cd9250db5 (rt 06b2ca5293cd). G3 (goal finish) refused: "resume: goal finish unsupported" -> G4 = same work dir, --goal route,
  --rt-floor-exempt (floor 6d2e187f0d; reset_anchor.py differs -> toolskew), spec _1122035554, runitem_g4.pid in opus-fix-s81-colrom-r6.
- NEXT: H route/DRC/TT (J5 history: GRT -32 -> route -107; watch), P/P2/G4 GRT reads, post each; cleanup after J8: epyc9 opus-fix-s81-colrom-r6/srcJ8G (54 GB), ot-build out, D/E kits.

## UPDATE 08:3x 11-22
- F CANCELLED 04:2x (residual ovf 1186 > 500; unit oth-ubuntu-1499928-1795332575). D/E kit dirs: ot-delete SKIP protected -> asked CLEAN-AGGR.
- G4 died (private-spec --work on an existing kit rm -rf'd its gen) -> G5 spec _1122040212, work _1122040139, runitem_g5.pid (opus-fix-s81-colrom-r6).
  G5 CTS post-hook setup -82.50 (H +19.20): STAGGER + keep rq suspect; COORD: drop them from J8 rows if G5 GRT confirms.
- Spills: P/P2 run on intel1, G5 on intel2 (kit dirs copied back to epyc9 after). Read logs on the spill host (same path).
  08:0x: P/P2 GRT extra iter 9/50 (~15 min/iter), G5 GRT iter 4/50; P/P2 CTS +19.34/+16.88.
- H: detail route on epyc9 (DRC iter 2, violations falling). Durable waiter f522513b on intel2 pid 3338988.
- J8 STATION ROWS (COORD 05:1x/05:4x): record epyc9 opus-fix-s81-colrom-r6/tmp/j8_stn_rows.json; plan srcJ8G/physical/die_plan/s81/plan_h2_2249_stnD.json.
  11 relay rows + 3 sink raises + 4 lpad-reader sink rows + istation_respace (o0 3->4, o1 2->3, i0 6->9) + c8_3 move (648,881.28)->(578.88,604.8).
  Gate try3 (stnC) bind FAILED: names must be rel (u_X not u_u_X); relay_depth needs a LEAF sink (lpl_*_w -> ist dropped). Try4 stnD running:
  intel2 opus-fix-s81-colrom-r6/bindS.pid / bindS.log (ot_build_hub --goal bind), ETA 10:4x-11:1x. On PASS: hand set to S81-J6-ASSEMBLY-R5.
- KNOWN-OPEN (mine, J9): u_d1_11_Y 1-bit hops 613/758 um (plan in the rows record known_open).

## UPDATE 17:3x 11-22 (after weekly limit 11:1x-17:2x)
- Gates PASSED: stnD b_72a25708e674, stnE (stnD + u_y_x2_4_0.o D1) b_91bf277e4ffa (epyc9 OPUS-FIX-S81-COLROM-R6/ot-build/s81/srcJ8G). ASSEMBLY took stnE into J8.
- H NOT SIGNED: TT -147.75 (37 ep x2_4_0 -> t4_payload), FF hold port-only (hold_ff PASS, parent), drv slew (post_route_drv ECO eco_20261122_174935, pass1 253->134), unconstrained 204 = UNCONST-IN-HARDVIEW (posted to FLOW-OPS-R2).
- G5 cancelled (GRT TT -133.74). srcJ8G plans have NO Kit H seats (166 relay_sites vs planH 1378). P died OOM 17:24, P2 cancelled 09:1x.
- NOW: plan stnEH = stnE + planH 1212 seats (srcJ8G/physical/die_plan/s81/plan_h2_2249_stnEH.json), gate bindEH.pid/log (intel2 opus-fix-s81-colrom-r6).
  On PASS: kits S1 (OT_TT_SETUP_MARGIN=90) + S0 via kit_wave private-spec --bind-out <EH bind> --goal route, H env: E RE + OT_GRT_CONG_ITERS=50 (no STAGGER/keep-rq). Template specG5.sh (scratch).
- KNOWN-OPEN J9: u_d1_11_Y hops (rows record known_open).
