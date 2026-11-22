# FAM-S81-COL-H10-R4 handoff (LIVE MEMORY, lane continues; OWNER 20:4x: no stand-down for context)
Family: S81 col_h10 (r0_p1, r0_p4, r1, r2). Older: lanes/handoff/FAM-S81-COL-H10-R3.md (levers, proofs), -R2, FAM-S81-COL-H10.md.
Lane dirs: hub intel2 /srv/opentallas-scratch2/claude/fam-s81-col-h10-r4 (specs, run logs, tmp/); epyc7 same path (srcA, bindA, tmp/); epyc7 /srv/opentallas-scratch2/claude/fam-s81-col-h10-r3/srcJ7L1e7 (lever-1 tree).

## View check (FABLE-CLOSURE-1320 note) - DONE, no regen
srcJ7L1e7 u_cf LEF dsfd_cfifo_crs4.lef sha daea3c41: every derived via-shadow rect is >= 0.30 um inside. All OBS within 0.30 of W/S/N edges is the RAW signed export (M2-M5 identical to provenance/raw; the M4 W rect and the M5 S/N full-width edge strips are only re-split around pins). Plan halo_um 0.27 on u_cf + u_t0 (ot_s81_sstn_base566) for col_h10_r0_p4__t1__pvcc166a6d. Per FABLE strategy lever 1 item 2 (signed metal stays, halo covers it). Scripts: scratch obsedge.py / obsadd.py (epyc7 fam-s81-col-h10-r3/tmp).

## LIVE (re-arm waiters)
1. LEVER 1 kit col_h10_r0_p4__t1__pvcc166a6d (J7 col volume HELD on it). spec intel2 fam-s81-col-h10-r4/specL1d/spec.json (wave env = Codex spec, --rt a9ed808a98d5 bind-era rt because current rt fails BIND-GEN-TOOLSKEW, src_manifest off = private proof). Orchestrator: intel2 PID 2620793 kit_wave run-item (rt 2095d6a53df2), log runL1d.log. Gen PASS 19:4x; kit = epyc7 /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/a9ed808a98d/private/FAM-S81-COL-H10-R4/col_h10_r0_p4__t1__pvcc166a6d_1121190309/gen/col_h10_r0_p4__t1__pvcc166a6d. Kit has macro_halo_carve (POST_TAPCELL), relay_mid.tcl = rt/current (FIT fix ae660e1299). config.mk vs J5 wave attempt_5 diff: +halo carve, MAX_FANOUT 32->64, MAXWIRE_POST_SKIP dropped (current wave env). Waiter: until test -f specL1d/result.json. Then route: ot-run --mem 48 --threads 8 --hosts epyc7 --dir <work> -- bash <work>/gen/run_kit.sh <K> route 48 8 (OT_LANE set). Accept on route DRC 0 vs u_cf/u_t0 -> hand view+halo rows to S81-J6-ASSEMBLY (J8 entry). If it signs, rebuild from a manifest tree (src_manifest off now).
   Tree fixes made: ot-deleted Codex sibling srcJ7L1e7_stn_keepout (was hardlinked 1:1; tree now nlink 1); installed main@a9ed physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl (sha 7df42ae1) into srcJ7L1e7; ot-deleted stale launch tree rt_tools_launch/srcJ7L1e7@a9ed808a98d5; copied ds85-child dsfd_node_LLfd/LLfu_d85/lec/lec.json intel2->epyc7 (restore worker: no export row; kit_snap_refs only searched epyc10/2/9).
2. PROOF A rebuild col_h10_r2__t1__cl99efd374__pv1619ecc6 from fresh place: tree epyc7 fam-s81-col-h10-r4/srcA + bindA (real copies of epyc10 fam-s81-col-h10/src1 + bind2), spec intel2 specA7/spec.json (tools cd2cd11c4e7e, has FIT), orchestrator intel2 PID 212032, log runA7.log. intel2 gen refused (KW-FIX-45 hub guard), so gen host epyc7. GRT-0116 read of the failed run: 11 vertical GCells x498-523 y11-13 (south face), nets frame_int_i0 lpad r[2], bout/bin frame_int, ist_frame_int_o0_4 = face-pad stack, not a macro corner; FIT may not move it (lpad is ot_dp_dly). After place: route via ot-run on epyc7 as above, then TT A/B vs J5 (-99.84; ROM-PVAL bn e_r class 7 endpoints, worst -81.7). Max one A/B.
3. cld01bb4ae (col_h10_r1) J5: DONE/DROPPED 21:3x. 5_1_grt TT -32.01 (inside gate, internal hold clean) but its route gave DRC 0 / TT -107.65 (RDX xs_q 150 + ROM-PVAL bn8 e_r 27) / internal hold -20.45. TT-only ECO reached only -71.08 after 13 h -> cancelled (oth-ubuntu-1969380-1795229887, AP_RC=143). No rerun from GRT (same placement, same gap; 650916ebb262 acts before GRT). Sealed J7 already has both row sets (ROM-PVAL u_bn6..9 e_r + RDX D=1 on u_e6..9_u_w xs_*). This type continues on J7 = COLROM-R5 kit on epyc9. No new J8 rows from it.
4. pv1619ecc6 J5 internal hold -4.2 -> small ECO after J7.

## Cleanup owed (ot-delete)
COORD-approved: when run-items specA7 (PID 212032) and specL1d (PID 2620793) exit, ot-delete intel2 fam-s81-col-h10-r4/srcA (55 GB), specA, specL1 (guard holds them: live cmdline prefix + host-scoped protection of srcA). specL1b/specL1c DONE. If still refused then -> CLEAN-AGGR-R3 with exact paths. epyc7 fam-s81-col-h10-r3/rt_tools_launch/srcJ7L1e7@2095d6a53df2 (failed specL1c cache).
## Posts: RESUMED, 19:1x launch, 19:4x gen pass, STATUS line for COORD sweep (rows dropped listed there).

## Adopted 21:5x (COORD sweep)
col_h10_r2__t1__* (18 variants, ex S81-GEOM-OPUS): COORD-ROUTED-OWNERS.tsv prefix row (top). Under J7 col hold; J8 readiness only (rows + proofs via lever-1/proof-A). No relaunch on J7 tools. J8 col-entry rule and deadline 11-22 14:00 GRT read: intel2 /srv/opentallas-scratch2/claude/s81-j6-r5/j8_intake.txt.

## 22:1x proof A route
place+geom PASS-COND. route ot-run oth-ubuntu-2998350-1795329265 epyc7 (resumed from place), log epyc7 /srv/opentallas-scratch2/claude/fam-s81-col-h10-r4/routeA7_otrun.log, kit epyc7 .../private/FAM-S81-COL-H10-R4/col_h10_r2__t1__cl99efd374__pv1619ecc6_1121201647/gen/<T>. Waiter: ot-wait --kit K --stage grt --also unit. Read final 5_1_grt.odb (grt_policy/tt ep_tt.tsv + overflow) -> J8 term (a) by 11-22 14:00.

## 22:1x lever-1 route + cleanup
lever-1 place+geom PASS-COND (76,109 cells). route ot-run oth-ubuntu-3023440-1795329345 epyc7, log epyc7 fam-s81-col-h10-r4/routeL1_otrun.log, kit epyc7 .../private/FAM-S81-COL-H10-R4/col_h10_r0_p4__t1__pvcc166a6d_1121190309/gen/col_h10_r0_p4__t1__pvcc166a6d. Accept: route DRC 0 vs u_cf/u_t0 (count DRT violations by owner macro). Cleanup: specA/specL1/L1b/L1c deleted; intel2 srcA handed to CLEAN-AGGR-R3 (guard host-scope).

## 23:4x PROOF A RESULT: GRT-0116 FAIL (done, no more A/B)
Congestion 483->154; south frame_int hotspot gone (FIT worked there). New: 84 V gcells x700-900 y950-1100 over u_r2.u_e15e.u_view.u_c (ot_v41_bf_col3_c MY) + bf16_half; nets = repair buffers (netNNN). J8 term (a) NOT met. Needs a bf_col3_c corridor/halo row for col_h10_r2 (owner COLROM / col plan lane). Kit results kept on epyc7. Renders: run/layout_review/grt/{congestion,density}.png.

## 23:5x COL-E15E-CHAN row (COORD: write row, proof A2 on epyc8/9, 50 GRT iters, family scope, post to FAM-S81-COL-H9R0-R4 by 11-22 14:00; J8 row cut 16:00)
Root cause (proof A 5_1_grt-failed.odb): all 156 congested nets = u_t9__payload.o (top edge y 916, x 762-845) -> xb_data relay station u_y_xd_u_e15_xb_data_0_0 (492 flops) -> u_e15 dsfd_bf_front_roots xb_data pins (TOP edge y 1158, x 520-633). relay_mid FIT seated the station at 815,1187 (ABOVE the bf view), so 492 nets + repair buffers run N-S over ot_v41_bf_col3_c (OBS M1-M6) at x700-900. The 56-um u_e15/u_c gap was unused.
Row (script intel2 fam-s81-col-h10-r4/e15e_row.py PLAN [--apply OUT] [--ops OPS]): per type of col_h9_r1 (u_r1.u_e8e, 60), col_h9_r2 (u_r2.u_e13e, 60), col_h10_r2 (u_r2.u_e15e, 12) = same placement: (1) move view u_c/u_ha/u_hb +25.92 um east (gap 56 -> 82 um; halves end 1166.4, nodes at 1183.68), (2) halo_um 2.16 on the 3 view macros, (3) core clock taps of the 3 macros shift with them, other clock/reset xy inside the new footprint go just above it (col_h9_r1 clk_t30 + reset relays 1144.8 -> 1166.4), (4) relay_polylines for the xb_data station through the channel (types with the xb_data D=1 row: h9_r2, h10_r2). No outline growth, no re-shape; overlap check clean; same geometry in sealed J7 plan (epyc9 kw45 d8j7).
Proof A2: srcA + bindA copying epyc7 -> epyc9 fam-s81-col-h10-r4/srcA2 + bindA2 (rsync pid 4142475 on epyc7, log epyc7 tmp/sync_A2.log). Then apply row in srcA2, private-spec --host epyc9 --ab OT_GRT_CONG_ITERS=50, run-item, route.

## 01:1x proof A2 LIVE
spec intel2 fam-s81-col-h10-r4/specA2 (tree epyc9 srcA2 + bindA2, host epyc9, --ab OT_GRT_CONG_ITERS=50, rt a699139ec4bc, goal auto = signoff chain), run-item intel2 PID 2939493, log runA2.log. Try 1 died at kit_rtl: the row first moved col_h9_r1 clk_t30 to y1166.4 = illegal (tap clear 8.64 + halo) -> fixed to top+halo+8.64+2.16 = 1170.72, verified with taps.grid_explicit_sites on all 132 family types (0 bad). Try 2 died at kit_topology KIT_TOPOLOGY_BIND_STALE: shifted core-tap xy changes the selected native reset context. So the proof tree applies the row to the proof type only with --keep-clock (taps unchanged, 26-um core-tap error; bind_matches True). The J8 row keeps the clock part (J8 re-binds anyway).
Row files: script intel2 fam-s81-col-h10-r4/e15e_row.py; ops on J6 plan epyc9 fam-s81-col-h10-r4/tmp/row_A2_ops.json (full, 336 ops).

## 01:3x COORD ruling: bind-prove the FULL row (clock incl.) on J7, parallel with A2
- Fork: epyc9 fam-s81-col-h10-r4/treeJ7r (ot-tree-fork of sealed J7 kw45 d8j7, manifest 12af64d4, nlink 1). Full row applied (132 types, 336 ops; ops file epyc9 fam-s81-col-h10-r4/rows_COL-E15E-CHAN_J7.json; plan sha b60a529b1a37). tools/ replaced by rt a8ade98de24a (has 33fe1ccf07 parallel emit).
- Gate: epyc9 fam-s81-col-h10-r4/bind_row.sh (strict --all-gaps, one r8_refresh+rebind if R8_STALE-only, LATCHECK+latcmp vs J7 candJ7eL6, G0+g0cmp, PRE), ot-run unit oth-ubuntu-3587548-1795338787, log bind_row.otrun.log, gate dir gateJ7r/.
- Outcome rule (COORD): green by 14:00 -> whole row to H9R0-R4 as bind-proven; else row w/o clock-tap part only if moves leave all taps legal; else J9. Post bind result to H9R0-R4 + J6-ASSEMBLY-R5.
- A2 try 3 died at gen: relay_polylines entry had an unknown key note (schema) -> removed from script; try 4 run-item PID 3080932.

## 02:2x RESUMED after weekly limit
- J7 row bind gate still running (oth-ubuntu-3587548-1795338787, epyc9 gateJ7r/bind1.log); waiter: until GATE_DONE in epyc9 fam-s81-col-h10-r4/bind_row.otrun.log.
- A2: gen PASS 01:31 (kit epyc9 .../col_h10_r2__t1__cl99efd374__pv1619ecc6_1122005516/gen/<T>, config has macro_halo_carve + OT_RELAY_POLY_FILE). run-item place NOT-RUN (sealed place on intel2, disk-ETA hold, rc 78). Relaunched by hand: ot-run --hosts epyc9 run_kit.sh <K> route 48 8 = oth-ubuntu-907207-1795342870, log epyc9 fam-s81-col-h10-r4/routeA2_otrun.log. Waiter ot-wait --kit K --stage grt.
- lever-1: GRT hold repair running on epyc7 (unit oth-ubuntu-3023440-1795329345), waiter b6xr6o6s0 equivalent: ot-wait unit.
- Fallback (if bind not green by 14:00): no-clock row legal only for col_h9_r2 + col_h10_r2 (72); col_h9_r1 -> J9.

## 04:2x
- J7 row bind: alive 3 h (parallel emit, 2 workers x ~50 GB at a time, ~1 min each); ~850 rtl files re-emitted, rate slowing (66 / 30 min). Waiter re-armed on bind_row.otrun.log GATE_DONE / OT_RUN_EXIT.
- A2 place: relay_mid seated u_y_xd_u_e15_xb_data_0_0 at 675.0, 1186.4 (path 561 um through the channel; was 815, 1187 over the view in proof A); halo blockages on the 3 view macros in; carve OK. Waiting on GRT (50 iters).

## 05:2x
- A2 GRT (50 iters): overflow 0 on every layer; station 675,1186 (channel); internal hold +30.04. run_kit route continuing (post-GRT gate / DRT). Waiting for OT_POSTCTS_GATE TT line in kit run_route.log.
- LEVER-1 DONE/FAIL: exit 6 post-GRT gate; GRT overflow 2475 at x1200-1300 y300 + y800 (u_t0/u_cf views); TT pinreg est -162.76 triage FAIL. DRC term unproven. Posted 05:2x. No relaunch without COORD (kit config change would be needed for 50 iters = new private-spec).

## 05:3x COORD: lever-1 rerun + channel variant, fold A2 row into J8
- Lever-1 congestion cause (5_1_grt nets): u_t0 (ot_s81_sstn_base566, xbi in on bottom y294, xb out top) boxed: u_n6 node 2 um east of it; 266 xbi drivers packed in that 2-um slot (x1224 y337); payload_i station (536b) seated at 1230,261 below u_t0 feeding u_t0_payload bottom pins y380; xbi station at 1325,384. Second hotspot x1300-1437 y770-875 = u_lpad_x_i0 228 regs next to u_n10/u_n11.
- specL1e (intel2 fam-s81-col-h10-r4/specL1e, run log runL1e.log): same plan + OT_GRT_CONG_ITERS=50, rt a9ed808a98d5 (--rt-floor-exempt, bind stamp), host epyc7, kit .../s81/18a2688b741/private/FAM-S81-COL-H10-R4/col_h10_r0_p4__t1__pvcc166a6d_1122051024.
- specL1f: COL-T0-CHAN row (t0chan_row.py 1754bdf4ea97; ops rows_COL-T0-CHAN_J7L1.json c2a1c6c2194f, 6 family types): u_r0.u_n6 1226.88,319.68 -> 1373.76,319.68 halo 0.27 (free pocket x1339-1442 y260-449), opens 71-um channel east of u_t0; no clock refs to u_n6, taps legal. Plan file srcJ7L1e7/physical/die_plan/s81/plan_h2_2249_t0chan.json + 50 iters. Kit ..._1122051847. Waiter on both run logs reaching place/fail.
- J8 fold-in posted 05:2x (PUSHED 5c07bb50adc): row file intel2 fam-s81-col-h10-r4/rows_COL-E15E-CHAN_J7.json c88f0eb10156.
- 07:2x PST push 2: 21 fixed LEFs staged epyc7 fam-s81-col-h10-r4/push2_stage (manifest dc5875600ff7), ROW posted 2850e6228c0 to J6-ASSEMBLY-R5 (provisional). Per-view probes xrt3/xrt1/cfg7_seq_bfp on intel1 vprobe2/ (units oth-ubuntu-1368708/1369198/1368692-1795360135); CLEAN by 14:00 -> J8 else J9. KV sweep: 139 LEFs, 3 FIX (posted). QC sweep epyc10 running. C1 place queued as service kwp-fb0be99d79f60e114675 (log intel2 specC1/place.live.log).
