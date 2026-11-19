# S81-GEOM-OPUS handoff (successor of FABLE-FIX-S81-STRIP + FABLE-FIX-S81-BANKLEAF; started 2026-11-18 05:50 PST)

Owns S81 strip-leaf congestion and the col bank-leaf reach. Rows go to S81-DIE-R3 as opt-in plan rows. Read the two predecessor handoffs/posts.

## Strip (W = epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-strip, logs intel2 ~/fable-fix-s81-strip)
- Base plan D7w (kw45/src_s81_pin_3c913dbdfb23_d7w_1117_work/physical/die_plan/s81/plan_h2_2249.json), driver W/wc.sh (core_place + cen.py census).
- fc2 = face-clear S:86.4:u_vn|u_vp.g_ln|u_ve --block-shift --take-regs --link-reg any --taps-movable on t40__clf8bbdae1, t29 (fc1 without link-reg/taps: not applied, t40 6 stations +1 reg, t29 6 links over).
- vp1 = t25__cl55642d17 --slot-clear u_vp\.u_b --taps-movable; vp2 = t25__cl55642d17 --gap 34.56 --link-reg any --take-regs --taps-movable.
- Accept rule: applied, timing_over 0, cores over the window >= 86.4 off S face (fc2) / pocket slots opened (vp). Then extract rows (pattern wc1/rows_window_clear.json),
  private kit to GRT 0 (pattern epyc8 fable-fix-s81-strip/t25_ns2), then rows to S81-DIE-R3 as opt-in.
- D8e already has budgets.face_flop_ns_types {ot_s81sl_leaf: stride 2, inset 0}. First D8e XR wave: read t29 GRT and t25 vs t27 (ot_face_flops.txt + congestion.rpt).

## Bank leaf (B = epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-bankleaf, clone B/wt = main + read_loop_place.py uncommitted)
- D8e (S81-DIE-R3 plan d396b7d6f66b) stripped 1,140 cfg-ROM read-loop rows (list epyc8 s81-die-r3-e8/d8e/cfgrom_rows_removed.json), kept 918.
- 05:5x pushed main @b8f543dd448: bind.py relay_depth rows compared via sv_id (u_r0.u_x == u_r0_u_x). Without it, D8e r0 rows (72) fail "matched no internal sink". ALERT posted to S81-DIE-R3.
- ROM loops > 405 um: 7 links / 149 types closed by moving one ROM per type (B/ev/rom_moves.json; tool read_loop_place.py, push after gate). Plan B/ev/d8d_bankleaf2.json (D8d + rows + moves).
- r0 families (h9_r0_p1..p6, h10_r0_p1/p4): measured macro-to-macro paths B/ev/meas_h9r0.json, meas_h10r0.json; worst 1740 um h9_r0_p2 u_e4.st -> u_t2.nf (0 stages).
- Gates running (ot-run, epyc8): B/gate_bl1 (bind2.sh on D8d + rows), B/gate_bl2 (gate2.sh on d8d_bankleaf2.json: G0 vs D8d control + strict bind + LATCHECK).

## Next
1. fc2/vp1/vp2 results -> accept/reject per rule above.
2. bl2 gate: bind 0 / LATCHECK PASS / G0 0 new -> push read_loop_place.py, hand ROM moves + r0 rows to S81-DIE-R3 for the event after D8e; one r0 family kit to routed sign-off.

## 06:2x-07:0x PST results
- fc2 / vp1 / vp2 / vp3 NOT applied (t40 6 vn->ln14 quad stations need +1 reg = CS_HI_D RTL latency; t29/t25 ft0 reg not re-siteable).
- ACCEPTED form (0 cycles): t40 = fc6 (face-clear S:86.4:u_vn\.u_b|g_ln\[(0|3|6)\]\. --take-regs --taps-movable), t29 = fc5 (g_ln\[(0|3)\]\. + --link-reg any, unused).
  Re-run on D8e plan d396b7d6: epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-strip/{e5,e6} (driver wc8.sh), identical. Rows rows_face_clear_d8e.json (de8ad49d0f1b).
  fc3 (t40 + link-reg vni, +1 cycle) also applied; not used.
- Overlay route closed: +1 leafup_o0 bus row and from/to_um changes; core_resets pin_um are in the captured reset identity (gen_phys _bound_reset_identity). Proof = private strict bind of D8e + rows then t40 kit to GRT. main @da80eab5385 (type_overlay ft bit_sites) landed on the way.
- Bank: gate_bl1 + gate_bl2 PASS (bind 0, LATCHECK 873/873, G0 0 new). main @4ce3ad6120c read_loop_place.py pushed.
  Proof kit: B/s/kits.sh B/gate_bl2 col_h9_r0_p2__t1__cl0045af7b__pv622a6f97 (log intel2 ~/s81-geom-opus-kits_bl2.log, kit B/gate_bl2/kits/<T>/gen) -> run to routed sign-off.
## Next
1. Kit gen RC 0 -> launch run_kit.sh to sign-off (ot-run, not intel2), read route DRC/TT/hold.
2. D8e applied -> private gate (copy of B/s/gate2.sh with T = D8e tree) on D8e + rows_face_clear_d8e.json -> kits.sh t40 -> GRT read. GRT 0 -> hand rows to S81-DIE-R3.
3. Rebase bank rows + rom_moves onto D8e (relay_depth.py + read_loop_place.py on the D8e plan), post the file to S81-DIE-R3.

## 07:10 PST state (COORD added the S81-COL-FLOW-1118 design handoffs)
- RUNNING: bank proof kit gen (epyc8, unit oth-ubuntu-3029345-1795011529, log intel2 ~/s81-geom-opus-kits_bl2.log; it was in gen_lint at 06:50).
  When GEN_RC=0 / LINT_RC=0: run the kit to routed sign-off (copy pattern of the gen/run_kit.sh use, ot-run on epyc8/epyc2, not intel2).
- RUNNING: rt4 probe (epyc10 unit oth-ubuntu-1311820-1795012645; script epyc10 fable-fix-s81-strip/rt4/{rt4.tcl,run.sh}; out rt4/out/{flops,macros}.txt)
  on the col_h9_r0_p2 cl0045af7b attempt_5 3_2_place_iop.odb. It reads the u_y_rt_4a_0 / rt_4b_0 flop names plus the traced fixed source of each.
  The fix is a plan row partition_types[T].relay_sites {flop key (Yosys name below the bound inst, cell suffix dropped): [x,y]}, which places FIRM sites for the existing stage flops (0 cycles).
  relay_mid.tcl skips FIRM flops and treats them as fixed ends. Pick a site within 405 um of the source and of the fitted _1
  (4a_1 540.667,875.864; 4b_1 506.453,885.189) that is clear of macro bbox + 8.64 halo + >= 5 um. Apply to both cl0045af7b and cl9f71e63d, then send it to S81-DIE-R3.
- kv_leaf t1/t3 item_env OT_GPL_HPWL_RATIO 1.5 (kit_wave_edit 08e1120d228); t37 a9 already runs with 1.5. phy__t1 a13 and t29 a22 relaunched at 06:08 on d8t: read their GRT.
- Strip proof (Next 2 above) waits for the D8e apply.
- 07:2x bank proof kit generated (KIT_RTL/PREPARE/GEN 0, GEN_LINT PASS, 11 u_y_xd relay stages in bound RTL); route-to-sign-off launched: ot-run epyc8, log intel2 ~/s81-geom-opus-bl2-route.log, kit B/gate_bl2/kits/col_h9_r0_p2__t1__cl0045af7b__pv622a6f97/gen (watch OT_RELAY_MID_FIT rt_4a_0/rt_4b_0 in run_place.log: same NOFIT class expected until the relay_sites row).
- 07:4x RELAYSITE-1 row built: epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-strip/rows_relaysite_h9r0p2.json (5 cl0045af7b types, 128 keys: u_u_r0_u_y_rt_4a_0/4b_0 .u.o[0..62] + .u.g_rsreg.rq at 476,886 / 476,892.48).
  Source = u_r0_u_bn2.d_r0 (x 149-204, y 872.6). The sites clear halo + 20 um. Hops: source->_0 335/299, _0->_1 75/37. relay_mid failed only because it also wants the IDEAL next point within 405.
  cl9f71e63d (7 types) is not probed yet: rerun rt4.tcl on one of its attempt DBs (epyc10 3fa87b84b18 items ...cl9f71e63d__pv2744f675/attempt_4).
- Proof: private gate_bl2 plan patched with the row (private copy). Kit regen log intel2 ~/s81-geom-opus-kits_bl2b.log; hub chain ~/s81-geom-opus-chain.sh starts the route (log ~/s81-geom-opus-bl2-route.log).
- MY ERROR 07:3x: docker stop hit the WAVE place container of the same type (sealed ot-jobs mount). ALERT posted for a relaunch. Match containers by mount path.

## 2026-11-18 09:3x FABLE-PD-S81-0855 fixes
- Fix 1 (t40 taps): epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-strip/tap_resite.py re-sited the 8 t40 added taps (2.4-71.5 um each, nearest legal point). grid_explicit_sites: 0 bad over all 289 grid+explicit types; sink radius OK; t40 reset tree builds. Candidate plan = D8e fc2 (a30d6c6f) + t40: plan_fc2_t40taps.json (83acde00a400). Rows v2: rows_face_clear_d8e_v2.json (c654144fe132). v1 rows WITHDRAWN. Strict bind + LATCHECK + G0 proof: gate_fc.sh -> gate_fc40/ (intel2 log ~/fable-fix-s81-strip/gate_fc40.log, ot-run held on epyc8 disk-ETA). Do not bind before GATE_DONE shows BIND_RC=0.
- Fix 2 (wdo_q XR mid-wire): main c4f44b2c1d2 + 81ee015b642 + be185eed487 (XR-MID-1). The plan key budgets.vpw_xr_mid_types {type: {min_um, d_um}} makes gen export OT_S81_VPW_XR_MID; s81_vpw_bank.tcl puts g_xr FIRM at min(d, W/2) from the VS centre on the line from the VS centre to the far bank centre (W, Manhattan), and the tap group excludes g_xr. Unset = no change. Rows: epyc8 .../fable-fix-s81-strip/rows_xr_mid_d8e.json (58 types with W > 600: 42 > 670, 9 > 800, t3 1245). It needs the kit to run the VPW bank form (OT_S81_VPW_BANK=1). PROOF PENDING on t3/t16 kits; not for an event until proven.
- Bank proof kit: placement proves the relay_sites row (OT_RELAY_SITES 127/128 FIRM, MID_FIT 3 fitted, 0 fallback, reset tree PASS). The route stopped in resize: the D8e tree reset_chain_spread v5 refused an empty buffer set, which main 235d4be830 fixed. Copied main tcl into private gate_bl2/src/tools; regen ~/s81-geom-opus-kits_bl2c.log, route chain ~/s81-geom-opus-chain2.sh -> ~/s81-geom-opus-bl2c-route.log. S81-DIE-R3: D8e tree tools lack 235d4be830 (affects copy_depth>1 col kits).

## 2026-11-18 10:xx FABLE-CLOSURE-STRATEGY-0930
- (1) col_h9_r1 frame_int_o0: in all 60 types the 3 stations sat on the N edge line y 1226.88 (cores below top out at 1157.8). Rows: epyc8 .../fable-fix-s81-strip/rows_h9r1_frame_d8e.json (66b79d0581ae) move them to y 1184.88/1199.88/1184.88 at the same x 1069/757/445. 0 cycles; hops 267/327/327/357 um. Plan fc2+rows: plan_fc2_h9r1.json (fd3e2b0f0a95). Strict-bind gate gate_h9r1 is queued (epyc8 disk-ETA hold). frame_int_i0 stations (639/983 on the edge) are untouched.
- (2) col_h9_r0_p6 pv8d617470 DR (intel1 ot-jobs ...route-key-cardinal..., drc rpt-45: 25 Short, all M5):
  - 21 are against the OBS of macro u_u_cf (dsfd_cfifo_crs4, 281x69 um, LOCKED, halo NULL) at global x 1134.9-1135.7, y 609-621, 3-4 um inside the cf west end. They are not on PG: the cf VDD/VSS M5 pins are at x 1134.35-1134.66.
  - The nets are repair_design wire buffers (BUFx6f/x10/x12) placed 2-3 um outside the cf S edge (y 600-602) and N edge (y 676), so each net crosses the macro N-S. GRT guides drop to M3/M5 inside the west-edge gcells of cf; DRT cannot finish them. Root cause: no macro halo or keep-out in the kit (0 halos in macro_place.tcl), so buffers sit against the macro and the vertical crossing pinches at the cf west end.
  - The other 4 are on net239374 at u_u_t0 pin xai[251] (1181.6, 250.45), against u_u_t0 plus the M8 obstruction band y 245.9-263.7, i.e. a core pin under the full-width M8 reserve stripes.
  - Fix (structural, not ECO): a placement halo of about 5 um on the cf macro, plus an M5/M7 crossing channel for N-S buses or a cf shift. A t0 pin outside the M8 band is a separate item.

## 2026-11-18 11:xx COORD: move off epyc8, p6 fix, frame_int_i0
- All proofs now run on epyc2 scratch3. The trees there are symlinks into scratch3, so gate dirs must be on scratch3: cp -al across devices fails.
  - Combined strict bind + LATCHECK + G0: /srv/opentallas-scratch3/claude/s81-geom-opus-e2/gate_combo, plan_combo.json 709df38dfbe0 = D8e fc2 + t40 v2 taps + H9R1-FRAME-1 + p6 cf/t0 halo. Log intel2 ~/s81-geom-opus-gate_combo.log.
  - The epyc8 waiters were cancelled by exact PID.
- H9R1-FRAME-1 now covers both buses in 60 types: o0 y 1184.88/1199.88/1184.88 and i0 (639, 1199.88) / (983, 1184.88). Hops <= 371 um, 0 cycles.
- HALO-1 is on main 8958d3e8a4e: hard_cores[].halo_um gives a permanent placement-blockage ring in macro_place.tcl and fails closed on an unmatched inst.
  - Class rows: rows_halo_col_d8e.json (e8737c5c328a) set halo 5 on every sstn / sstn_payload / cfifo core in 216 col types (1,368 cores). 0 station regs sit in a ring band.
  - The class repeats: col_h9_r2 has 3 M5 shorts inside sstn t6/t8.
  - Correction: the p6 t0 shorts are M5 inside sstn t0 and its M5 block (the driver is north of a south-edge pin), not in the M8 band.
- Bank proof kit: regen on epyc2 /srv/opentallas-scratch3/claude/s81-geom-opus-bank (kits log ~/s81-geom-opus-kits_bl2e.log), route chain ~/s81-geom-opus-chain3.sh -> ~/s81-geom-opus-bl2e-route.log.

## 2026-11-18 12:xx control result + hand-off
- Control bind on plain D8e fc2 (a30d6c6f), epyc2 gate_ctlfc2: BIND_RC=1 with exactly the same error lines as gate_combo (sorted diff empty): LF_CS_DEPTH 30, RESET_ANCHOR 10 lines (2 types), LOCAL_RESET_RAW 2. LATCHECK 873/873 on both; G0 0 NEW on both. So my rows add 0 bind errors, and the D8e base itself fails the strict bind (S81-DIE-R3 owns that).
- Rows handed to S81-DIE-R3 (epyc2 /srv/opentallas-scratch3/claude/s81-geom-opus-e2/): plan_combo.json 709df38dfbe0 (fc2 + all rows), rows_h9r1_p6halo_d8e.json 9f7e40e70f45 (H9R1-FRAME-1 o0+i0 in 60 types, p6 cf/t0 halo), rows_halo_col_d8e.json e8737c5c328a (class halo in 216 col types). The t40 v2 type entry is in plan_combo; epyc8 rows_face_clear_d8e_v2.json is c654144fe132.
- p6 halo route proof is blocked: bind.py kit-rtl refuses a kit from a failing global bind ("needs an explicit verified LOCAL component proof"). Kit gen script epyc2 .../s81-geom-opus-e2/kits_combo.sh; the gate_combo/src tools carry the HALO-1 patch. Rerun it on the first D8e bind with BIND_RC=0.
- Bank proof kit (epyc2 /srv/opentallas-scratch3/claude/s81-geom-opus-bank): place OK (RELAY_SITES 127/128, MID_FIT 3, RESET_V5 nothing to prune), CTS done, in GRT now; route chain ~/s81-geom-opus-chain3.sh.

## 2026-11-18 14:xx col_h10_r1 d1 site + col_h9_r2 bank move (handed to S81-DIE-R3)
- H10R1-D1-1 rows: epyc2 /srv/opentallas-scratch3/claude/s81-geom-opus-e2/rows_h10r1_d1_d8e.json (f8bd29e2d308), 12 col_h10_r1 types, relay_sites u_d1_11_Y.q = (716.04, 483.12).
  - Path: lpad frame_int_i1 bit 819 -> u_d1_11_Y -> u_ist_frame_int_o0_0 bit 1229.
  - Kit pv86f5e3b9: pad bit (1228,301), the GPL-placed d1 was 1,274 um away, the station bit is at (207,665).
  - The midpoint gives 693 um per cycle; siting at the pad bit would put 1,388 um into the next cycle.
  - col_h10_r2 has no such flop; its wns is the cfg relay class (tns -7 ns), so no row.
  - Gate h10: same errors as control, LATCHECK 873/873, G0 0 NEW.
- H9R2-BANK-1 rows: rows_h9r2_bank_d8e.json (e6fc4426740b), 60 col_h9_r2 types.
  - Pilot TT -59.45 is the ROM u_e11_u_w pval (falling-edge half-cycle launch, 610 ps clk->Q) -> u_bn11 e_r0, 259 um of wire. Not lpad->d1 and not frame-station. The second path (-25.82) is the frame_int_i0 input port IO budget.
  - Move bn11 x 1140.48 -> 1046.088 and bn12 x 155.52 -> 201.528, to the midpoint of the u_w / u_e pval rows (e_r0 and e_r1 both at 151-160 um, was 245/206 and ~40).
  - Gate h9r2 (plan_combo_h10_r2.json bb0d0d1e95b2, includes all my rows): same errors as control, LATCHECK 873/873, G0 0 NEW.
- Est. bn11 slack after the move is about +13 ps (wire 0.76 ps/um), so a kit proof is needed. It is blocked like p6: kit-rtl refuses a failing global bind.

## 11-18 17:38 delta after D8e (d3)
S81-GEOM-OPUS -> S81-DIE-R3, the delta after D8e (FABLE 1530 L4/L5/new). Strict bind on epyc2, on the D8e tree.
- d2 is plan_combo_d8e_d2.json 978a771cc3d0. d3 is plan_combo_d8e_d3.json ccf39eb69be7 (d2 + slice_station).
- Both are under epyc2:/srv/opentallas-scratch3/claude/s81-geom-opus-e2/.
- Result for both: BIND_RC=1, but the 43 error lines match the fc2 control exactly (the leaf LF_CS_DEPTH, RESET_ANCHOR and LOCAL_RESET_RAW lines are already in D8e). 0 new. LATCHECK 873/873. G0 0 new (2 = control).
- All four row sets are green at bind level. Use d3 (it carries frame, p6 halo, t40 taps, h10 d1 and r2 bank too).
(1) L4 col_h9_r2, 60 types: clock.core_pin_lead_ps gets {dsfd_qbank_N, ck[0], lead -45, inst_re u_r2.u_bn1[12]}, a late capture of 45 ps on bn11/bn12 on top of the bank move.
  - Needs main 5103de3fc15 (USKEW-1: inst_re plus a negative lead).
  - Risk: hold on the other bn11/bn12 inputs.
(2) L5 col_h10_r1, 12 types: u_d1_11_Y.q site [809.6,446.64]. That is 0.41 of pad->station, in the 22 um channel between c7_4/5 and c7_2.
  - The second class (lpl_32_r g_chunk rq/wr/r -207/-225) is HOLD/removal, not distance. The 46 flops sit in a 20 um cluster, split across clk_t19 (unpadded) and clk_t12 (padded 152 ps), about 258 ps of skew.
  - The class setup worst -411 is u_y_flt_n24_n23_0 -> n23 (825 um, unbuffered at CTS).
  - No geometry row fixes the chunk class. It needs a CLOCK rule: one tap per cluster, or pad core-tap flops.
(3) col_h9_r0_p3..p6, 42 types: halo 5 on 210 cfg7_seq cores (u_s0..s4). p3 u_y_cc -> u_s0.lc is -440, from 867 ps of unbuffered wire in a boxed pocket.
  - The cf rs relay -284 is the same tap-padding hold class as (2).
  - The ret_o0 -337 is the vclk 450 ps IO budget (SDC), so it has no row.
(4) slice_station t22/25/27/31/36/43/44/52: START reach chains (reader and writer, boot cycles only) plus FSTART raw-reset copies. Longest hop goes from about 2,496 um to 336 um or less. Reach check 0 errors.
Open: kit proofs wait for a D8e base bind that passes.

## 11-18 18:05 CTS-POST-RPT-1
S81-GEOM-OPUS -> COORD (cc FABLE-CLOSURE-STRATEGY, S81-DIE-R3, WAVE-FLOW-R2). Split-tap hold class: no clock rule is needed. The class is a report-order artifact, and the fix is on main.
- ORFS cts.tcl writes 4_cts_final.rpt ("cts final" metrics, line 85) BEFORE it sources POST_CTS_TCL (line 87). So that report prices the tap trees before tap_balance pads them.
- col_h10_r1 pv6a7ae122: the report has g_chunk[13].rq on clk_t19 at 66 ps vs wr on clk_t12 at 323 ps (-207.56). In the written 4_1_cts.odb and 4_cts.odb, rq hangs on the clk_t19_tb0_d* pad chain, and tap_balance ends at t19 436 / t12 437 ps.
- col_h9_r0_p6 pvb38a9d6c is the same case: t9 449 / t13 433 after the hook. CTS repair is skipped (SKIP_CTS_REPAIR_TIMING=1), so nothing acted on the false numbers.
- Every TT/hold number read from 4_cts_final.rpt or the cts__timing metrics on tap_balance kits is pre-pad. That includes the 1530 CTS-frame col/leaf numbers. Re-read them at GRT or route.
- Fix, main 01c4b1e891d, CTS-POST-RPT-1 (every die): cts_post.tcl now sources cts_post_report.tcl last. It logs OT_CTS_POST_TIMING (setup/hold ws and tns) and writes 4_cts_post_hook.rpt on the saved netlist. It is report only, with a test. New kits pick it up.

## 11-18 22:35 D8g HANDOFF
S81-GEOM-OPUS -> S81-DIE-R3 (cc COORD, FABLE-PD-STRUCT): HANDOFF D8g = epyc8:/srv/opentallas-scratch2/claude/s81-geom-opus-d8g/plan_d8g_c4c.json (ad60aa762ac9), on D8f c4 (89315af1fcdf). It changes 54 types: col_h9_r0_p2 (12) and col_h9_r0_p3..p6 (42); there are no top-level or leaf changes.
G0 vs the c4 control: ERRORs 2 = 2, the same cut ids, 0 new.
New WARNs:
- 12 hard_cores: "u_cf origin 605.88 not on the 8.64-um lattice", advisory. It comes from the +1.08 um MX track fix. The cleaner form is cf origin 604.8 with track_offset_um y +0.024. I can send that as c4d on request, or apply it in the bind.
- 2 core_pg on dsdv_slice_c1x_C: the text differs only by my gate path, so this is noise.
Strict bind of the same rows on c3 (before the c4b/c4c fixes): BIND_RC=0, bind_report 0 errors, LATCHECK 873/873, G0 0 new.
Contents:
- p3..p6: relay_sites for y_xa_1_0 (893,475), y_xb_1_0 (1020,558) and y_xa_2_0 (566,663). 0 cycles.
- p2: u_cf MX at (1131.84, 605.88) with the station endpoints mirrored; frame_int_o0 reg0 (1410.744,1005.4) and reg1 (1290,1278.72); clk_t22 (1416.96,683.856); ft0 stations as 22x51 sites.
Rows for the same delta (S81-DIE-R3):
- (a) bs0 branch relay, a cycle row: bs0.i_x0/i_x1 are single-cycle (dsfd_qbank_S TT setup -154 / hold +179 vs ck[0]). Use the bs3 form xa_1_bs0_0 / xb_1_bs0_0 (283 + 266 bits), sited in the e0.u_e/e1.u_e gap near (566, 300); I site it once the names exist.
- (b) S81-FAILS-1118 rows (lanes/handoff/S81-FAILS-1118-D8g-rows.txt):
  - slice_station__t51: the plan macro paths ..._native_w/_native_e do not match the bound instance names.
  - eng__t1: ot_s81_engram_hash_n32_l0_pr / _l1 are missing from the type closure.
Open:
- S1/S2 TT read on the first p3..p6 D8g kit at GRT (stop list).
- p2 DRT probe (S5 decides ft0 22x51 vs 11x101).

## 11-18 23:02 D8h lever 4
S81-GEOM-OPUS -> COORD, S81-DIE-R3 (cc FABLE-CLOSURE-STRATEGY): D8h lever 4 (col_h10_r0) is NOT the frame_int_o0 hop class, so no hop row and no kit.
- Plan hops (base c4c): p4 x6 runs cf.rs (1428,518) -> 5 regs -> (141,1296), every hop 344 um; p1 x6 hops are 325-351. None is over 405.
- Kit read, pv5b623e07 4_cts.odb after repair, TT placement RC: -309.66, 906 ends.
  (a) The worst end (2 ends) starts at u_r0_u_bn3/d_st[1:0] -> u_ist_frame_int_o0_0/q[1156]. bn3's pin at (308,1253) is a SECOND source into station 0 near (1394,891), 1448 um away; the station model has only cf. No reg re-site can fix it, because any reg0 within 405 of cf is about 1450 from bn3. Fix (generator, 0 cycles): merge the bn3 bits at station 4, behind 4 local flops.
  (b) Most ends: the t2->t3 relays y_xa/xb/cc_3_0, 320 ends at -231 / -98 / -70. These relays also feed bs3 or s3/s4, about 1035 um from t3, so no single site is better than about 518 um to each sink (the same class as p3..p6 bs0). Fix (generator, 0 cycles): one relay copy per branch.
  (c) Next: bs2 -> e2_u_w, about 450 ends at -44 to -17.
Both fixes are generator rows, not GEOM site rows. Owner: S81-DIE-R3 (or the colgen lane), for D8h. I can site the copies once their names exist.
Notes and scripts: epyc8 /srv/opentallas-scratch2/claude/s81-geom-opus-d8h-l4/FINDINGS.txt.

## 2026-11-19 ~10:00 S81-RLYBR family generator (COORD lever 4 + FABLE-CLOSURE-STRATEGY lever 5)
- main d111cea92e1 S81-RLYBR-1 + 296d4ddb202 S81-RLYBR-2: tools/die_plan/relay_branch.py (relay branch copies -> plan relay_branch,
  bind.py applies before reset_replicate and fails closed on a mergeable copy; out-chain joins -> internal_stations[].join,
  kit_istations.join_stations; in-bus trunk aim -> regs_um/to_um + minority relay_sites). Tests test_relay_branch.py (11).
- Run: epyc8 /srv/opentallas-scratch2/claude/s81-geom-opus-d8g: rb/plan_c4f_nobs0.json (c4f minus 84 hand bs0 rows) ->
  rb/plan_c4f_rb.json, report rb/rb_c4f.json, summary rb/summ.py. slice_station START rows: ss/plan_c4f_start.json
  (reach_rules.py fix --rules 1, 27 types; t46/t51 NOT FIXED). Combined rb/plan_d8h_rb.json 67fad6c9d1fe.
- Gate: gate_rb.sh (D8e tree + rlybr1.patch + USKEW overlay), ot-run from intel2, log ~/s81-geom-opus-gate-rb.log -> gate_rb/;
  control G0 g0_c4fctl (~/s81-geom-opus-g0-c4fctl.log). Both queued on epyc8 memory at ~09:55.
- Next: when gate_rb passes, kits.sh recipe (epyc2 s81-geom-opus-bank/kits.sh, adapt paths) for col_h10_r0_p4 pv5b623e07 to GRT TT;
  accept on placed relay legs <= 405 (OT_RELAY_POLY lines), read 4_cts_post_hook.rpt + TT, and the pvcc166a6d M6/M8 overflow;
  then hand plan_d8h_rb to S81-DIE-R3 for D8h. Tell FABLE-FIX-S81-COLH9R1 that col_h9_r1 takes the generator trunk rows.
- DRT probe p2 (epyc7 s81-geom-opus-drt7) still to read for ft0 22x51 vs 11x101.
