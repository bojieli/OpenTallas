# FABLE-FIX-S81-SERDES2 handoff (Fable; owner of the 11 S81 SerDes types, pilot serdes__t13)
Started 2026-11-17 07:25 PST, took serdes over from S81-TYPES-R3. Gate R-MINIMAL: DRC 0, routed TT >= -42, internal FF hold >= 0.
Logs: intel2 ~/fable-fix-s81-serdes2/. Lane dirs: epyc2 + epyc9 /srv/opentallas-scratch2/claude/fable-fix-s81-serdes2/.

## State 07:45
- H12 (lead; epyc2 scratch3 .../fable-fix-s81-serdes/H12, container dpkit-serdes__t13-153484, log intel2 ~/s81-serdes-r2/h12-route-1117.out):
  CTS done 07:04 (428 INV pairs, span 214), TT repair +0.71, in pre-GRT FF hold repair since 07:11 (H5 took 25 min there), GRT read ~08:15.
- H13 / H14 (epyc2, brackets): in CTS.  H7 (density 0.40, stock DRT) still in DRT iteration 0: free control for finding 1.
- FINDING 1 (new blocker, all forms): H5 detailed route died 05:56 with DRT-0255 in iteration 1 (net _218581_, routeBox x 892.62-896.61,
  y 653.22-657.21, boundary pin M4 at (896.610, 654.504)). H3p (density 0.5) died with DRT-0255 in the SAME box column
  (x 892.62-896.61, y 709.08-713.07). H12 keeps H5 placement, so it inherits this.
  Geometry (probe epyc2 .../fable-fix-s81-serdes2/probes/H5_drt255/box.log): PG M5 pair VSS x 896.244-896.364 / VDD 896.436-896.556
  (pitch 4.32), M2-M5 stack pads on every rail; the iteration-1 worker edge (offset -2, 7 gcells of 0.57) is 54 nm right of the VDD M5
  stripe, so the M4 boundary pin has no M5 track and one M3 track between the edge and the stack. gcell 0.57 and stripe pitch 4.32
  share 0.03, so this exact alignment recurs every 144 gcells (82.08 um): x 896.61, 978.69 (both in the u_enc XOR plate),
  1307.01 (u_syn plate); stock offsets -2, -5, -3 make them worker edges. Hypothesis, not proven.
- Experiment (epyc9 .../fable-fix-s81-serdes2/drtx, input H5 5_1_grt.odb sha 886605288fe7, step-DR with the stock cost table):
  X1 size 7 offsets -1/-4/-6 (unit oth-ubuntu-50410-1794929701, log ~/fable-fix-s81-serdes2/drtx-X1.out),
  X2 size 8 offsets without -3 (unit oth-ubuntu-50396-1794929700, drtx-X2.out). 32 threads each. Reads: OT_STEP lines in <tag>/drt.log.
## Next
1. H12 GRT TT by class (grt_policy.json + pair census). Skew class under -42 -> new kit H15 = H12 + OT_STB_ROUNDS=16 (config.mk export).
2. DRT: if X1/X2 pass iteration 1-2 and converge, the offset schedule goes into the kit route step (flow branch + gate + READY) and H12/H15
   route with it. If both die: single-worker debug dump on the failing box.
3. Sign-off -> exports (AGIdock + rtx-pro, INDEX rows) -> other 10 types through the wave.

## State 08:45 (supersedes FINDING 1 hypothesis and the Next list above)
- Worker-edge hypothesis WITHDRAWN: X1 (size 7, other offsets) died on the same net _218581_, X2 (size 8) on 5 more nets, all x 874-897.
- DRT-0255 cause = FABLE-PD-DRT-1350 class A: every failing net has a one-gcell-high M6 guide in a gcell row under an M6 VSS/VDD pair
  (probe epyc2 .../fable-fix-s81-serdes2/probes/col/col.log). The kits ran pg_track_truth in the obstruction form. Fix = config.mk
  `export OT_PG_TRACK_TRUTH_MODE = region` (on main, opt-in).
- LEAD FORMS, epyc9 /srv/opentallas-scratch2/claude/fable-fix-s81-serdes2/H15 and H16 (kit = <H>/serdes__t13/gen/serdes__t13):
  H15 = H5 placement + OT_S81_RCK_BALANCE=1 + OT_STB_ROUNDS=16 + region mode. CTS: 840 INV pairs, span 70.4 PASS, p1..p99 14.
        unit oth-ubuntu-75658-1794929876, log intel2 ~/fable-fix-s81-serdes2/H15-route-1117.out
  H16 = H15 + OT_CLK_LEAF_SLEW_PS=165. CTS: 769 pairs, span 75.0 PASS. unit oth-ubuntu-75639-1794929876, H16-route-1117.out
  Region mode was appended to config.mk (copy+mv) after CTS, before GRT. CHECK in 5_1_grt log: "OT_PG_TRACK_TRUTH region N GRT capacity cuts";
  if it says "add 5038 temporary GRT obstructions" the patch did not take and the form must restart from GRT.
- H12/H13/H14 (epyc2): obstruction form, GRT TT reads only. Kit dirs hold a STALE H5 grt_policy.json (04:40, -64.25): read only a newer file.
- epyc9 scratch2 dipped to 14 GB free 08:2x (other lanes), back to 110 GB; ALERT posted.
- Lane worktree for the default-change branch: epyc9 .../fable-fix-s81-serdes2/wt (main f6095f5e0f, cone tools/die_plan), nothing edited yet.
- Fleet DRT-0255 scan (COORD ask): kit_wave_state.json has 40 rows whose last failure is DRT-0255, ALL on superseded events (none on a
  current event). 28 still have a route log: 17 kits have most failing points in the M6 pair row, 1 mixed, 10 elsewhere
  (43 of 77 points in the row; chance 18 %). Data intel2 ~/fable-fix-s81-serdes2/drt255_scan.json.
## Next
1. H15/H16: GRT congestion + TT by class -> DRT (must pass iteration 1) -> sign-off gates -> exports + INDEX rows.
2. COORD order 08:4x: if GRT shows no new congestion and DRT passes, one branch makes region mode + OT_STB_ROUNDS=16 the generated default
   for all 11 serdes types (gen_phys.py near the OT_S81_RCK_BALANCE line ~5545), ot-gate-remote, READY post with full sha.
3. Then the other 10 types through the wave.

## State 09:35
- H15 (epyc9, unit 75658): flow scripts restored 09:11 while still in GRT; GRT TT repair running; continues to DRT. Only the post-CTS TT repair pass was skipped.
- H16 (epyc9): first run exit 6 = missing postcts_gate.tcl (my rsync excludes), not design. RESUMED 09:3x from its own 4_cts.odb/5_1_grt.odb
  (COORD lever 6; no new CTS/GRT; done list do-cts,do-grt). Resume-only edits, see kit RESUME_NOTE_H16.txt: OT_PREGRT_FF_HOLD 1->0,
  tt_setup_repair.on both->grt, FAIL_POSTCTS renamed. Log intel2 ~/fable-fix-s81-serdes2/H16-route-1117-r2.out. H16 GRT: overflow 0, hold +0.12.
- H17 (epyc9, unit 718229): clean rerun of the H16 config from placement with all scripts; backup form. Log H17-route-1117.out.
- H12 GRT (fresh 09:15): TT -28.28 / 29 ends, no class under -42; goes to DRT in obstruction form (expect DRT-0255). H13/H14 same role.
- COORD lever 4 (09:2x): once H16 or H15 passes DRT iteration 1 -> ONE branch: region mode the fleet GRT default + serdes OT_STB_ROUNDS 16 +
  rck balance default for serdes, and a check that ft_channel_tracks and alloc_r4 capacity models account for the region cut. Worktree epyc9 .../wt.
  Hook points read: gen_phys.py pg_drt0255_cfg() (~2421, env opt-in today), RFLOW pg_track_truth (~2330), txl_mid_exports (~5501, serdes lines),
  rck_balance.tcl (rounds via OT_STB_ROUNDS env), test_drt0255_pg_rows.py, test_subtree_balance.py.

## State 10:50 (clock times in the 08:45 / 09:35 blocks were ~20 min ahead; epyc9 date prints UTC = PST + 8)
- REGION MODE IS NOT A CURE: H15 (region active) died DRT-0255 in iteration 1 (_018686_, net110119; M6 guides still in pair rows y 494.19 / 597.93).
  M6 pair-row guide segments >= 5 um: H5 obs 216, H15 region 286, H16 region 306 (awk epyc9 drtx/m6row.awk on route.guide). Lever 4 on hold.
- GRT TT without post-CTS repair: H15 -118.23, H16 -136.92 -> -92.05. Neither is a timing candidate. H16 resume is in DRT iteration 0 (expect 0255).
- TIMING CANDIDATE = H17 (epyc9 .../H17, unit 718229-1794935531): post-CTS repair -77.35 -> -0.37, span 75.0, in GRT. Its config.mk now has
  PRE_DETAIL_ROUTE_TCL = /work/pg_row_guides.tcl (installed before DRT).
- NEW FIX pg_row_guides.tcl (source: epyc9 drtx/pg_row_guides.tcl; the local scratchpad copy is not durable): PRE_DETAIL_ROUTE hook, moves M6 guides
  >= 2 gcells out of rows with <= 1 legal M6 track to the nearest stripe-free row + connector guides. H15 DB: 236 bad rows, 105 guides / 98 nets.
  Proof runs on epyc9 drtx/G1 (first version, target = any non-bad row) and drtx/G2 (stripe-free target = the kit version): full DRT, 64 iterations,
  step-DR harness with the stock table (dr_exp.tcl). Logs intel2 ~/fable-fix-s81-serdes2/drtx-G[12].out, epyc9 drtx/G[12]/drt.log (OT_STEP lines).
## Next
1. G1/G2 pass iteration 1 (and converge)? yes -> branch: pg_row_guides.tcl into tools/die_plan + gen_phys copies it and sets PRE_DETAIL_ROUTE_TCL
   (serdes first; the fleet default is a COORD call after the proof), OT_STB_ROUNDS 16 + rck balance default for serdes, test, ot-gate-remote, READY.
   no -> single-worker debug dump (detailed_route_debug -dr -worker ... -dump_dr) on the failing box to find the hard edge.
2. H17 GRT TT by class. Under -42 on an rck pair class -> structural call (centre trunk / AM cycle) with numbers to S81-DIE-R3.
3. H17 DRT -> sign-off gates -> exports. If H17 dies in DRT for another reason, rerun only do-5_2_route from its 5_1_grt.odb.

## State 14:55 PST (epyc9 date prints UTC = PST + 8)
DONE
- Branch 1 READY + approved r598: claude/s81-serdes-pg-row-guides-1117 @39c0d49c9809f9882ba42e2dde92d97bb28723f7 (guide move + rck 16 rounds default), gate GREEN 62/62.
- G1/G2 stopped (ot-heavy-stop). H17 guide-only route stopped by exact unit; H17 GRT DB intact: epyc9 .../H17/serdes__t13/gen/serdes__t13/run/results/asap7/dp_serdes__t13/base/5_1_grt.odb
  (GRT TT -27.17 / 39 ends policy PASS; internal FF hold +0.12, 0 negative).
- Guide move alone: route converges to 607 = 544 PMA RX pad shorts (input buffer chain between die pin and macro pin) + 63 at dchn
  (36 short + 21 EOL at cw_q top-edge pins beside the M5 VDD strap; 6 M6 spacing at clk / rst_n interior pins under the M6 pair).
HOOKS (durable source: epyc9 .../fable-fix-s81-serdes2/drtx/eco/{pad_in_direct.tcl,pg_pin_notch.tcl,pg_row_guides.tcl,serdes_pre_drt.tcl})
- pad_in_direct.tcl: walks single-fanout BUF chains from any INPUT BTerm whose pin lies on a block pin; 544 pads, 1557 buffers removed on H15 DB.
- pg_pin_notch.tcl v2: v1 removed every PG via overlapping a notched box incl. the M1-M2 via row of a std rail -> new floating row at y 499.
  v2 removes only vias landing on the notched layer with centre in the removed part. 44 boxes notched.
RUNNING on epyc9 (logs intel2 ~/fable-fix-s81-serdes2/)
- drtx/E1: proof route, H15 DB + three hooks (notch v1). 97585 -> 18313 after iteration 1. Read OT_STEP lines in drtx/E1/drt.log; target DRC 0.
- drtx/pgchk3_E2: check_power_grid VDD with full error file on the E2 DB (hooks with notch v2). Diff its VDD.rpt bbox lines against
  drtx/pgchk_base/VDD.rpt: there must be no entry outside y 921.24-1205.82 (base has only the north band). pgchk2-{base,E1} still doing VSS.
- drtx/ttsk_H17 (v2): TT census (violating ends with q-side slack, p_d / txl rows, per-clock insertion). v1 crashed.
- F1 (.../F1, unit 3281425-1794955725): floorplan-only kit with PRE_TAPCELL_TCL = phy_region_rows.tcl (region blockage before row cut).
  Check with drtx/eco/north2.tcl on F1 2_floorplan.odb (run_north2.sh <dir>): W-north VDD M1/M2 rails must be > 31 (base: 31, all above y 1206).
PG DEFECT (all serdes types with a PHY supply region): rows W/E of the PHY region overlap it (317.25 vs 314.928; 2567.70 vs 2575.69) -> no CORE
followpin rails on 2108 rows, ~16k cells (15.7k taps, ~480 logic incl. 56 DFF). Straps are fine. H17 carries it; IR not run.
NEXT
1. E1 DRC 0? -> H17 route-only: copy the 4 hook files into the H17 kit, config.mk PRE_DETAIL_ROUTE_TCL = /work/serdes_pre_drt.tcl (replace the
   pg_row_guides line), resume-only edits as in RESUME_NOTE_H16.txt (OT_PREGRT_FF_HOLD 0; tt_setup_repair.on -> off so 5_1_grt.odb is not re-repaired),
   relaunch H17_run_route.sh via ot-run. Then sign-off gates, exports (AGIdock + rtx-pro, INDEX rows), IR sidecar (meaningless until PG fix).
2. Branch 2 (from main): the two new hooks + serdes_pre_drt chain in gen_phys; pad_bump_dt.tcl rows for INPUT macro_pin pads (dont_touch before
   buffer_ports) for every family; PHY-REGION-ROWS-1 in phy_pg_pdn (after F1 proves it); tests; ot-gate-remote; READY.
3. COORD lever 5b: split clk_t42 (6528 sinks, tap insertion spread 163-554 vs target 250) into 2-3 taps in the serdes plan; decide on census v2.
4. COORD lever 5c: CAPSKEW-ECO lane owns tools/die_plan/capskew_eco_run.py; give it census v2; no second tool.
5. Other 10 types (and t13 again) from the fixed generator through the wave.

## State 15:15 PST
DONE since 14:55
- DRC 0 route: epyc9 drtx/E1 (H15 DB + 3 hooks, notch v1): 97585 -> 18313 -> 11706 -> 171 -> 6 -> 0 at iteration 5.
- Branch 2 READY, gate GREEN 62/62 on main 48ab33e1375: claude/s81-serdes-pad-pg-rails-1117 @c8ce59b7a01ead0a6dec691dfdc416fc4b5be2bd
  (PHY-REGION-ROWS-1 row cut, PG-RAIL-CHECK-1 on every kit, input macro_pin pads dont_touch, PG face/island cut default for macro_pin pad
  types, ECO hooks pad_in_direct.tcl + pg_pin_notch.tcl v2 as tools). Worktree epyc9 .../wt on that branch.
- Rail fix proof: kit F2 floorplan: OT_PHY_REGION_ROWS 1054 rows -> 2108 pieces; OT_PG_RAIL_CHECK rows 6726 bad 0 (H17 floorplan: 6664 / 2046 bad).
  F1 (blockage before tapcell) did not work. Rail check sample on other dies (drtx/rail_sample/summary.txt): 11 of 19 done, all PASS.
- PG cause: missing M1/M2 rails on rows overlapping the PHY region (NOT missing straps). VSS fails the same way (north band only).
- Tap insertion (H17 4_1_cts.log OT_TAP_BALANCE it3): clk_t42 554 ps / 6502 sinks; taps <= 1650 sinks sit at ~255. Recommendation posted:
  split clk_t42 into 4 taps (plan row, S81-DIE-R3). North taps t17/18/22/27/28/29/30 at 390-417.
- TT census (drtx/eco/ttsk.tcl) crashes OpenSTA with signal 11 right after the endpoint count, twice. Not fixed. Use kit pair_skew.tsv.
RUNNING (epyc9)
- H17 route-only rerun with the 3 hooks (notch v2): unit oth-ubuntu-3409413-1794956321, log intel2 ~/fable-fix-s81-serdes2/H17-route-1117-r2.out,
  kit note RESUME_NOTE_H17.txt. MEASUREMENT ONLY (rail defect): read routed TT / FF hold, never export. Expect ~2 h. The 5_2_route.tmp.log
  with mtime before RESUME_NOTE_H17.txt is the OLD stopped run.
- drtx/pgchk3_E2: check_power_grid VDD on the notch-v2 DB; diff VDD.rpt bbox lines against drtx/pgchk_base/VDD.rpt (expect no entry outside
  y 921.24-1205.82; the 10000+10000 cap makes line-level diffs noisy, judge by y range).
- drtx/rail_sample: remaining 8 kits.
OPEN, NOT MINE TO FINISH ALONE (posted 15:1x as STRUCTURAL)
(A) clk_t42 split into 4 taps: plan row, S81-DIE-R3.
(B) The H form (H3p -> H5 -> H17) is a hand-kit lineage (about 40 H_* stage files, h4_meta_reflow.tcl, PLACE_DENSITY 0.30): not in gen_phys.
    The other 10 types cannot be released on it through the wave until a lane ports it; a generator rebuild of t13 is not this placement.
HOLD: S81-TYPES-R3 was asked to hold the 11 serdes items on result:FABLE-FIX-S81-SERDES2:rail-gen; post that result only after branch 2 is merged.
NO SIGN-OFF EXISTS for any serdes type; nothing was exported to AGIdock or rtx-pro.

## For S81-SERDES-GEN (written 15:3x PST; V = I opened it, R = from another lane handoff, ? = not found)
I took the H lineage over at H12 and never generated the base kit, so (1) and (2) are what the records show, not my own run.
(1) Plan JSON path and sha
- ? The plan file the H base kit was generated from is NOT recorded in the kit or next to it (epyc8/epyc2 L/H, H2, H3, H3p hold only gen/; no
  gen.log, no kit_rtl.log kept).
- V kit record: H17 kit budget.json io_hold.plan_sha256 = cd773b61a1a79877534cf1f0595c5b503ada0fa035d62b5360dc5b0dbbbd28e0.
  No *.json > 100 kB under epyc8 /srv/opentallas-scratch2/claude/s81-b3-clk/{ev,run/b/*} has that raw sha256 (so it is either a canonical-form
  hash or a plan outside that tree). Recompute with the Plan loader of the tree below before trusting any candidate.
- V kit record: kit_rtl_paths.json src_tree = /srv/opentallas-scratch2/claude/s81-b3-clk/run/b/B6gF2s4strip3/src  (so the bind/RTL side is the
  B6gF2s4strip3 event tree; the plan is most likely that event, on base physical/die_plan/s81/plan_h2_2249.json).
- R form name: plan_h2_2249 (clock.keepouts_um classes), FABLE-FIX-S81-SERDES handoff line 144.
(2) gen command line and environment
- V the recipe file exists: epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-serdes/gen2.sh (gen.sh = same without PREP_PLAN), usage
  `gen2.sh FORM TYPE [extra gen args]`, env PLAN/BIND/ASB/SIDE/SRC/ITEM_ENV/PREP_PLAN override. Its defaults are the G3b plan of record
  (PLAN=$M/ev/B6gG3b.json, SRC=kw45/src_s81_pin_eb1e73448bd0), which is NOT what the H kit used (see src_tree above); the overrides used for H
  are ? (not recorded). Steps, in $SRC:
    OT_NATIVE_RESET_SCOPE=selected python3 tools/die_plan/bind.py kit-rtl $PLAN --out $BIND --asbuilt $ASB --type T --src-tree $SRC --kit $W/rtl
    python3 -I tools/die_plan/kit_topology.py prepare-stations $PLAN T $W/rtl --native-plan $PLAN --asbuilt $ASB
    python3 tools/die_plan/gen.py phys $PLAN --out $W/gen --types T --rtl-root $SRC --kit-rtl T=$W/rtl/kit_rtl.f --hold-ff-margin 0
        --max-wire-um 100 --clock-landing $SIDE
  env for gen.py phys: OT_FLOW_TAG=flow-20261108-eg-s81 OT_SIGNED_VIEW_SHA=/srv/opentallas-scratch2/claude/kit-ops-6/signed_view_sha_s81.json
    OT_PLACE_MAX_FANOUT=64 OT_GRT_NONPORT_HOLD=1 OT_CORE_TAP_REACH_UM=0 OT_PREGRT_FF_HOLD_AUTO=-1 OT_MAX_BUFFER_PERCENT=100 OT_GRT_POST_MAX_S=0
    OT_HOLD_STOP_PS=-1000000 OT_GRT_ALLOW_CONGESTION=1 OT_CONS_MAX_LAYER=M9 OT_CLAND_STRIP_DENS=1.0 OT_TT_SETUP_REPAIR=both OT_PG_DIE_PHASE=1
    OT_PG_TRACK_TRUTH=1 OT_PG_TRACK_TRUTH_WIDE_SPACING=1 OT_PG_CELL_KEEPOUT=0 OT_PG_PIN_CHECK=1 OT_PGCAP=1 OT_GEN_M8_GRANT=1 OT_CONS_KIT=1
    OT_CONS_UTIL=0.25 OT_CONS_STRIP_ROWS=1  (+ ITEM_ENV = the item_env of kit_wave.json s81 11-16 for the type)
  Cross-check against the H17 config.mk (epyc9 .../fable-fix-s81-serdes2/H17/serdes__t13/gen/serdes__t13/config.mk): it has OT_PG_TRACK_TRUTH = 1,
  OT_GRT_NONPORT_HOLD = 1, OT_PLACE_MAX_FANOUT = 64, OT_TT_SETUP_REPAIR = both, -allow_congestion; it has NO ref_tile trace: the kit is gen.py phys.
- V everything after generation is hand work on the kit copy; the saved config.mk.H_before_north / .H_before_family / .H_before_corrective_dpl /
  .H_dpl_source and clock_taps.tcl.H_before_north / clock_taps.H_before_family.tcl in the kit are the checkpoints between the hand steps
  (diff them in that order to get each step as a delta); the last hand lines are in config.mk from "# S81-SERDES-R H2: north-strip tap rows" down.
(3) The 90 plain relays
- R (S81-SERDES-R2 handoff lines 45-48, 66): H3p = H2 kit + tools/die_plan/bound_reset_edit.py --plain on the kit bound RTL: all 90 ot_dp_rrelay_nl
  -> ot_dp_rrelay, relay_lockup removed, depth map unchanged (134 taps). V the record is in the kit: H3p_plain_edit.json (plain true,
  relays_to_plain 90, bound_rtl_sha256 e55e8d12e239bd943a4dc1cf16f597c957090c074f75d5e87615e6ec9e06ec93).
- R S81-DIE-R2 confirmed 11-16 20:09 that B6gF2s5f (plan C3 c20ec9e4c3c4) drops all 11 serdes types from reset.relay_lockup.types, so the bind
  emits plain relays for them. So: it is a PLAN change and it is already in B6gF2s5f; no generator rule and no bound_reset_edit are needed for a
  kit generated from an s5f-or-later bind. I did not open the s5f plan myself: check reset.relay_lockup.types there, and check that the generated
  bound RTL sha equals e55e8d12... (or differs only by the later events) before placing.

## State 15:35 PST
- Branch 2 final tip READY: claude/s81-serdes-pad-pg-rails-1117 @0b5eafc9c4b70307df969daaa57ab699c2497d46, gate GREEN 62/62 on main 329e30c85ae
  (supersedes c8ce59b7a01 and e7b3e941690). Rail check: FAIL on PHY-supply-region kits, ADVISORY elsewhere (pg_rail_check.json in the kit).
- Samples (epyc9 drtx/rail_sample/summary.txt, drtx/phy_sample_*/summary.txt): 17 kits without a PHY region PASS; every PHY-region kit FAILS as
  built with bad rows == region-overlapping rows: serdes t13/t4 2000, t2/t3/t14/t1__clfe 2004 of 6656; HEAD hd_serdes 3047 of 5672; KV kv3_sys_c
  5840 of 7818. Not sampled: serdes t12, t15 x2, t16, t1__clb45 (no floorplan left), QC coll_ucie (QC-TYPES-R3).
- Notch v2 PG diff (drtx/pgchk3_E2 vs pgchk_base, VDD): all unconnected entries still in the north band, none south (report capped 10000+10000).
- H17 route-only rerun reached the PRE_DETAIL_ROUTE hooks at 15:31: OT_PAD_IN_DIRECT 544 pads / 1557 buffers; notch + guide move + DRT follow.
  Read: K/run/logs/asap7/dp_serdes__t13/base/5_2_route*.log (violations per iteration), then the kit sign-off lines in H17_run_route.out.
  MEASUREMENT ONLY. If it ends DRC 0: post routed TT (gate -42) and internal FF hold (gate 0) by class for levers 5b/5c; run the IR sidecar only
  after a rail-clean rebuild.
- After branch 2 merges: post `RESULT result:FABLE-FIX-S81-SERDES2:rail-gen` so S81-TYPES-R3 can release the hold on the 11 serdes items
  (they still need the generated H form from S81-SERDES-GEN before they are worth launching).
- COORD decisions 15:2x: clk_t42 -> four taps = plan row to S81-DIE-R3 after D6z/D7z; H-form port = lane S81-SERDES-GEN (answers in the
  section above).

## State 17:15 PST
- Branch 2 MERGED: main fdce0e6ec4 (r620 @0b5eafc9c4b). RESULT [FABLE-FIX-S81-SERDES2] rail-gen PASS posted 17:1x.
- Before posting I added a second release term (S81-TYPES-R3 silent since 15:11): dies/s81 hold_records s81-serdes-rail-gen-1117 (11) and
  s81-serdes-source-1116-codex (6) now release on [result:FABLE-FIX-S81-SERDES2:rail-gen, result:S81-SERDES-GEN:h-form]. Backup
  autopilot/kit_wave.json.bak-serdes-hform-1117. The 11 serdes release only when S81-SERDES-GEN posts `RESULT [S81-SERDES-GEN] h-form PASS`.
- S81-SERDES-GEN silent since 15:20 (branch claude/s81-serdes-gen-1117, clone epyc9 /srv/opentallas-scratch2/claude/s81-serdes-gen/wt).
- H17 route-only rerun (3 hooks, notch v2: 544 pads, 44 boxes / 42 vias, 97 guides): iteration 0 = 98632 violations, in iteration 1 at 17:10,
  16 threads. MEASUREMENT ONLY. Next reader: violations per iteration, then routed TT / internal FF hold from the kit sign-off lines.

## State 18:05 PST
- H17 route-only r2 (3 hooks, notch v2, kit flow): DRC 0 at iteration 5 (98632, 17862, 11810, 191, 2, 0), antenna 0, then ORFS
  "Design has unrouted nets" (exit 2; no routed DB). Cause: 1089 pad-on-macro-pin nets (rx 544, tx 544, tck 1) have no wire.
- Branch 3 READY, gate GREEN 61/61 on main a248cf63d83: claude/s81-serdes-pad-abut-wire-1117 @63b5676fe5352312cd642a1402269e1920445d4c
  (pad_abut_wire.tcl POST_DETAIL_ROUTE; gen_phys for every macro_pin pad kit). Proof: H15 routed DB design_is_routed 0 -> 1 (drtx/paw).
- H17 route-only r3 with that hook, 32 threads: unit oth-ubuntu-1440356-1794966603, log intel2 ~/fable-fix-s81-serdes2/H17-route-1117-r3.out.
  This is the first run that can reach the kit finish / sign-off steps: expect further latent blockers there. MEASUREMENT ONLY.
- S81-SERDES-GEN is alive: r638 (part 1) merged, part 2 READY claude/s81-serdes-gen2-1117 @e5e787f0642d; it has NOT posted h-form PASS.
  Asked it to wait for branch 3.

## State 23:55 PST 11-17 (resumed 22:26 after the Fable limit; S81-FIX-OPUS covered 20:00-22:27 and keeps svc/strip)
- H17 r3: DRC 0, antenna 0, 5_2_route + 6_final written; RCX passes with pad_abut_strip.tcl (PRE_FINAL_REPORT; r678 =
  claude/s81-pad-abut-strip-1118 @146e658a9e20, same file as the kit copy). 6_report then stops in the inline PSM check (rail defect, expected).
- H17 ROUTED STA (kit signoff.py, epyc9 H17 kit signoff_meas_072023/): NOT SIGNED. TT setup -117.47 / 430 ends / TNS -24248;
  FF hold -55.85, 258 internal reg-to-reg + 33 ports; TT hold -42.15 / 134. Worst: setup u_dec.u_out.u_cmem -> u_out.bsrc[0][476];
  hold u_dec.u_lpl_2_w.wc[1] -> b[2][32]. GRT had said -27.17 / +0.12: the GRT read was 90 ps / 56 ps optimistic. Cause NOT known.
- SPEF: 204 pin-not-found = 4 forwarded-clock output nets aliased to ports by assign in 6_final.v; not the strip; port timing only.
- SPCYC/SYN_LOCAL: not set in H17, the wave kits or the D6z kit; D8d plan file not opened.
- h-form FAILs on D6z (4 defines + 17 RTL files missing in the plan tree); S81-DIE-R3 carries them in D8d. 11 serdes stay held on
  result:S81-SERDES-GEN:h-form.
NEXT
1. Endpoint census on H17 6_final.odb + spef (my ttsk.tcl crashed OpenSTA twice on the GRT DB: use report_checks -group_path_count N
   -format json or the signoff session.tcl frame instead): classes, counts, launch/capture clock arrivals; compare the same paths at GRT.
2. Per class: capture-skew ECO (CAPSKEW-ECO tools/die_plan/capskew_eco_run.py), GRT hold margin, or plan (D8d t42 split).
3. Rebuild t13 from D8d generated kits (rail clean), then the other 10; sign-off, export AGIdock + rtx-pro + INDEX. Nothing exported so far.

## State 00:55 PST 11-18: census + decisions posted
- Census files: epyc9 /srv/opentallas-scratch2/claude/fable-fix-s81-serdes2/drtx/census/{tt,ff}_{spef,grt}.{tsv,log}, aggregator drtx/cen.py.
- Cause of GRT optimism: rck clock tree. Data nets routed-GRT median -14 ps; rck sink arrivals in u_dec spread 1848..2051 routed
  (GRT read them balanced); lpl_0_r.rc vs .o 144 ps, lpl_2_w.wc vs .b 179 ps. Balance pads were sized on placement RC.
- Routed TT setup < 0: 408 ends (343 lpl_r.rc->o, 29 enc.rem_q, 22 rm, 11 syn, 3 cmem->bsrc). FF hold < 0: 258 internal + 1273 ports.
- Decisions: register stage after u_cmem read (+1 cycle, LATCHECK); rck: post-route clock ECO on extracted arrivals (CAPSKEW-ECO tool)
  + centre-root trunk plan row with the t42 four-tap split; r692 hold repair after; SRAM-write hold open.
- Pilot rebuild only after the S81 event carries: cmem register, centre trunk, t42 split, the 4 defines + RTL files (D8d).
