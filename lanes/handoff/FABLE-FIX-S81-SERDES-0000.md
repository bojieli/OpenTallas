# FABLE-FIX-S81-SERDES-0000 handoff (Fable; owner of the 11 S81 serdes types from 2026-11-19 23:27 PST)
Gate R-MINIMAL: route DRC 0, TT >= -42, hold >= 0, bind + LATCHECK, hops <= 405 um. V = I opened it, R = reported by a lane, I = inferred.
Dirs: intel2 ~/fable-fix-s81-serdes-0000 (client logs, scripts), intel2 /srv/opentallas-scratch2/claude/fable-fix-s81-serdes-0000/{wt,rows,sim},
epyc7 .../fable-fix-s81-serdes-0000/R1, epyc9 + epyc10 + intel1 .../fable-fix-s81-serdes-0000/{sta,geo}. Lane clone wt = main + cone tools rtl physical/common_flow.

## State 2026-11-19 23:55 PST
NO serdes type is signed off. Nothing was exported to rtx-pro ~/signed-export-1114 or AGIdock /archive. No plan row is applied yet.

### Live units (mine: one)
- R1 = serdes__t13 proof of the family fix: H25 kit inputs (H23 rck form: hub at pad, 200 um hops, 14 sub-hubs; AMPIPE) + RM_LOCAL_EMPTY8 + RM_WPL8,
  fresh synth -> route. epyc7 /srv/opentallas-scratch2/claude/fable-fix-s81-serdes-0000/R1/serdes__t13/gen/serdes__t13, unit oth-ubuntu-564596-1795161073,
  client log intel2 ~/fable-fix-s81-serdes-0000/R1-route-1120.out, kit log R1_run_route.out. Waiter intel2 ~/fable-fix-s81-serdes-0000/wait.sh posts at the end.
  Built by epyc7 .../fable-fix-s81-serdes-0000/r1_mk.sh (rsync of the H25 inputs from epyc9, stale result logs excluded; patch_rm.py on the kit copy of
  dedup/ot_pdie_serdes_col.sv). lec_async.sh was excluded by mistake, so async LEC is skipped in R1 (advisory). Stop only with ot-run --cancel on that unit.
- Not mine, kept as data points (serdes lane, waiters armed by it): H23 epyc9 oth-ubuntu-509933-1795140762 (in GRT hold repair), H25 epyc9
  oth-ubuntu-1203239-1795153255 (AMPIPE, in global place), T15P epyc10 oth-ubuntu-1444535-1795153600 (t15 on the H23 rck form, post-CTS TT repair).
- Wave rows of event b05c98f7919 (11 types) belong to the wave; 247 errors there are OOM kills (infra).

### Root causes (per limiter)
1. CORRECTION (V): the "H23 GRT TT -73.5" is the H21 log. H23/H25 kit tt_setup_repair_grt.log = H21 file (same md5, mtime 11-19 10:49 UTC, copied by
   h23_mk.sh). H23 real: rck span 89.0 PASS, post-CTS TT -47.77 (TT repair crashed rc 139, 4_cts unrepaired), GRT not finished.
   Ladder at GRT on t13: H21 one-hub star -73.51 in the kit repair log, -30.4 / hold +10.7 by my STA on its final 5_1_grt.odb (plain TT libs + kit SDC + setRC,
   global-routing RC; the 43 ps gap to the kit number is NOT explained: derates or a later DB state), DRT-0255 at the hub; H22 two-level 31 stages -179; H23 pending. Read any tt_setup*/hold_gate log in an H kit only if its mtime is after
   the kit's own run start.
2. Reset anchor (serdes__t16, V): pads io_pma_lock has no sites_um on any of the 11 types (plan_h2_2249.json of the D8h tree), ORFS auto-places the pin.
   t16 got N (1416.96,1222.29) inside u_ptx; t14/t15/t1 got S and pass. The 11-19 03:11 rows were never applied and their site (PHY east end, north edge)
   fails the boot path: 1865 um = 4 x 466 um on t16. Fix = S-edge site at the x of the rs sync centroid (rows, READY).
3. clk u_rm read side (t13, V H22 h22sta.out + my H23 STA): wp_g2 (clk_t43) -> g2b -> compare -> enable -> mux -> g_rd q (clk_t41): tap window 53 ps on
   setup and 4 HB4 hold cells (297 ps) on the shared start. H22 GRT -76, H23 CTS -37 (29 ends). Fix = RTL OT_S81_SERDES_RM_WPL8 + RM_LOCAL_EMPTY8
   (main 315cc722d68): the only cross-tap hop is flop-to-flop. RX +1 clk.
4. rck u_syn am_ok -> xs (V): t13 H22 -138, H23 CTS -47.8 (34 ends, 536 ps of wire buffers). Placed distance am_ok -> loads: t15 1040 um, t1__clb45
   1214 um, t13/t14 local. Fix = OT_S81_KP4_AMOK_PIPE (serdes lane, main d4d59679470), +1 rck; H25 and R1 measure it.
5. RM -> coll_o0 face hop (V geometry probes): rm.mem to u_bout_coll_o0 is 1180 um on t15, 1073 um on t1, 450..580 um on t13, one cycle, no station;
   GPL drags the 512 q flops to the face (t15) or stretches them (t1). T15P TT at CTS -673 (913 ends) is this. serdes__t14 already has
   internal_stations bus:coll_o0 (3 stations) and is clean there. Fix = internal_stations rows (t15 x2 and t1 x2: 2 stations, t13: 1), lane coll_o0 +cycles.
   Not measured: t12, t16, t2, t3, t4 (no placed DB on the current event).
6. t15 other classes at CTS before repair (V, epyc10 sta/t15p_cts): u_syn g_bm -285 (850 ends, ldr fanout chain 450 ps), u_rm mem -196 (1959, rp_g2 ->
   fill -> push -> we: the RM write side; the RM_WFULL8 form exists only under RM_STAGED), xs -188, u_enc rem_q -108 (encoder split over clk_t30 322 ps /
   clk_t42 247 ps with a -99 window; tap means 188..436, clk_t46/t47 at 436). T15P's own TT repair is still running: re-read these after it.
7. Wave kits of b05c98f7919 carry the H22 rck form (HOP_UM 92, SUB_HUBS 14, HUB_AT_PAD 0) and no AMPIPE: expect the H22 result (-179) where they survive place.

### Done
- main 315cc722d68: opt-in OT_S81_SERDES_RM_WPL8 (ot_s81_rate_match_rt LOCAL_WP), bench rtl/dsrom_sys/s81_link/tb_s81_rate_match_rt_wpl.sv +
  tools/s81_link/run_rm_wpl_bench.sh (PASS x2, mutant FAIL), gen_phys source contract + test (test_txl_mid_exports.py 14 pass).
- Rows: lanes/handoff/FABLE-FIX-S81-SERDES-0000-j4-rows.json (= intel2 .../fable-fix-s81-serdes-0000/rows/serdes-j4-rows.json, made by mk_rows.py):
  11 io_pma_lock sites READY; 11 RM define rows + 11 clock.tap_group rows (one clk tap per RM read bank) and 11 AMPIPE rows (proof running); 5 internal_stations asks (bit sites by S81-DIE-R3's tool).
- Tools: sta_census.tcl + sta_run.sh (class census + worst-path reports; note sta::worst_slack prints raw units, class lines are ps),
  geo.py + geo_run.sh (placed group geometry), in intel2 ~/fable-fix-s81-serdes-0000 and on the hosts.

### Next (in order)
1. R1 GRT: read OT_TT_SETUP_REPAIR / OT_POSTCTS_GATE lines of R1_run_route.out, then sta_run.sh on its 5_1_grt.odb (global_routing tt and ff).
   Expect the u_rm clk class and the xs class gone. If TT >= -42 and hold >= 0 at GRT, let it route; DRC 0 -> r708 sign-off -> export -> any-plan count.
2. H23 GRT TT and DRT (does hub-at-pad route?). If it routes: rck star row (hub_at_pad 1, hop_um 200, sub_hubs 14) for all 11 types into J4 and the
   generator default; if DRT-0255 again: M8 trunk form (H24).
3. S81-DIE-R3 J4: lock sites now; define rows + stations after R1 (bind + LATCHECK reprices coll_o0 and the RX lane: +1 clk RM, +1 rck AMPIPE, +1/+2 stations).
4. Worst type proof (r712): one private serdes__t15 kit from the J4 bind (stations + defines + lock site + H23 rck form) to GRT TT/FF. t15 cannot be
   proven before the stations exist in the bound RTL.
5. Remaining types through the wave on J4; placed_hops_or.py on the first 3_place.odb of t12/t16/t2/t3/t4 for their coll_o0 rows.
6. Open question to the serdes lane (asked 23:27): are the uncommitted kp4 eq bench edits in the localhost owner checkout its work? Not touched.
