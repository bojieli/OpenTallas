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
