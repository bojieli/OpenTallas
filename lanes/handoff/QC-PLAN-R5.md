# QC-PLAN-R5 handoff (2026-11-20 ~10:45 PST)

## Live state
- QC live event s29q103S4Q9N46R4A4 (applied 09:35, R4). Sealed bind kw45/snap_qwen_compute/qwen_compute_n46r4_a4_bind_1120085722.
- Wave: 100 A4 rows (event s29q103S4Q9N46R4A4) all RUNNING at 10:3x (stages start/gen/kit_rtl/kit_topology); no failure yet. Check ~/coord/autopilot/kit_wave_state.json items[*].event == s29q103S4Q9N46R4A4.
- coll_core proofs on epyc9 (OPUS-FIX-QC-COLLCORE dead, owned here): pkw3 CANCELLED (14.2 h, post-CTS -628; CANCEL-UNSIGNABLE-1120). Kept pkw2b (container dpkit-coll_core-1096606, GRT repair WNS -240) and pkw4 (dpkit-coll_core-987854, read-register class proof, post-CTS -479 rdq->out_data; Fable fix 8 waits on its GRT TT class read). Cancel either only if >3 h and a measured setup < -300 after GRT repair.

## V1 (cut ~11-21 09:30 PST, target strict 0). Work dir epyc9:/srv/opentallas-scratch2/claude/qc-plan-r3-n41p/n46/v1_cbc/r5
- Fabric option (a) PRICED + POSTED 10:2x: fabric_level_price.json (r5_fabric_level_price.py; view-only, uses the binder's qc_fabric_transport.derive). Key fact: A4 balances the CB16 tree with R8 landing pads (landed-bound up to 12 at root n_a); price on BOUND stages keeping A4 R8 pads. Level max increase L3 +4, L4 +4, column entry +3. 264 legs (216 lanes +2..+4, 48 L3 u_t_1_2.n_a intra legs as INNER pads), 395k flops above V1A minimum; region E +15 cycles vs A4.
- Built: v1a_r5_fabric_a_plan.json (216 lanes fixed_cycles raised; r5_apply_option_a.py) + zz_extra_r5_fabric_a.json (48 INNER members, asbuilt 16 -> landed 20).
- EMIT cbf_q00 y_o11: fixed in v1a_r5_fabric_a_raw_plan.json (r5_cbf_raw_relay.py, generalised Codex rule): rr_t102 -> non-port rr_t94, same depth 14, <=220 um. Report cbf_raw_relay_report.json.
- Strict script r5/v1a_complete_strict_r5.sh = R4 a5 script pointed at the LIVE A4 tree (snapshot n46r4_a4, asbuilt_n46r4_final_preview.json + appended land_r8_extra zz_extra_r5_fabric_a.json); arg 6 = predicted bus_groups.
- Launcher intel2 ~/qc-plan-r5/strict_r5_launch.sh <tag> <predicted bus_groups> [plan name in r5/]. Pass 1 (tag p1, fabric plan without the relay, R8 from A4 sealed bind) launched 10:3x; result r5/strict_p1, log ~/qc-plan-r5/strict_p1.log/.rc.
- NEXT: pass 2 = `bash strict_r5_launch.sh p2 <w>/r5/strict_p1/bind/bus_groups.json v1a_r5_fabric_a_raw_plan.json` (R8 from pass-1 bind + relay). Expect R8_STALE gone and PARAM_REGEN clean; if the INNER table is rejected (R8_STALE "no such"), check the id/source of the 48 u_t_1_2.n_a<-u_t_1_3@16 members against bind_sinks.json. Then LATCHECK (in script) and G0 separately; post token impact from LATCHECK.

## Then (COORD order, Fable PD-QC-0945 ranking folded in)
1. st_a rs_s0/rs_s1 two stages on all 11 st_a types (+1 cycle), disjoint banks, legs <=300 (owner rows QC-SUST-MACRO-1119; compose here).
2. sle_ctl: move u_ctl east (>=60 um channel beside u_tap, move only), four b_hw_hc*_o stage-0 banks on four sides, b_tw_data_st_a_o south of y 328, cws1 FT window off the u_tap column.
3. Re-bin from newest placed kits for the 25 STALE-BINS types, then retap (take V1A retap draft); sle_ctl first.
4. First-rank seating FIRM at port window on fe/fw/su_c/sc/stm (slw_fe_v1 attempt_5 form), re-scan.
5. cb bc_i00/10/30 two more stations; stm flt_o one.
6. Launch-side lockup rows, su_l0/su_l1 first.
7. Station hops to 300 globally.
- coll_core: no V1 row until pkw4 class reads >= -42 at GRT TT. Honour Fable section 8 stop list. stm_v2 retap+lockup and cbn density taps fold into 3 and 6.

## Rules in force
- 833 ps; one plan event per 24 h; apply via publish_apply bind-first seal + OUT-SYNC (intel2 ~/qc-plan-r3/apply_n46r4_a4.sh pattern).
- Post every 2 h; next due ~12:15.

## UPDATE ~11:05 PST (supersedes the pass-1/pass-2 lines above)
- Pass 1 (tag p1) FAILED in bind elaboration, class NATIVE-STATION ACCOUNTING: "native stations sl_W5_hc0__cwn0: fixed_cycles must equal source 3 + destination 2". Column-entry lanes sl_<s>_hc0/hc2__cw[ns]0/2 (+2) carry native station chains, so fixed_cycles alone cannot carry the raise. Column pads cannot absorb it either (re-priced r5/fabric_level_price_b.json: no pad <=9 balances; near and far share one pad per column).
- Fix in r5_apply_option_a.py: for those lanes the source type internal_stations row bus:cw_n0/cw_n2 gets +2 stations, chain re-spaced evenly from launch to face (11 sle/slw hc0/hc2 types; cw_s* have no native row). Plan regenerated (216 lanes, 48 INNER, 11 chains).
- Round 2 chain running on intel2: ~/qc-plan-r5/chain_r2.sh (cbf relay, then strict q1 with R8 from A4, then strict q2 with R8 from q1). Results: chain_r2.out, strict_q1/q2.log/.rc, epyc9 v1_cbc/r5/strict_q{1,2}. Old p1 dir and chain_p2.sh are dead ends.
- If q2 is clean: run G0 on r5/strict_q2 tree, read LATCHECK token impact, post. If another class appears, classify and fix the plan the same way (no unchanged retries).

## UPDATE ~11:15 PST
- COORD accepted the fabric price (395k flops, +15 fabric cycles within owner pre-approval). Record the LATCHECK token impact in the post once q2 binds clean.
- Waiter: QC-PLAN-R5 armed a background until-loop on intel2 ~/qc-plan-r5/chain_r2.out. A successor re-arms it if this lane is gone: `until test -s ~/qc-plan-r5/chain_r2.out; do sleep 60; done` (on intel2), then read strict_q1/q2.log and epyc9 v1_cbc/r5/strict_q2/bind/bind_report.json + latcheck.json.
- Next V1 rows to BUILD on top of r5/v1a_r5_fabric_a_raw_plan.json, in order (COORD 11:1x): (1) st_a rs_s0/rs_s1 two stages on all 11 st_a types (+1 cycle, legs <=300, disjoint exact banks; input epyc7 .../r4_direct/gen_representative_a3_retry/sust_e3_s1_reseat_evidence + Fable 0945 sec 6); (2) sle_ctl u_tap channel >=60 um (move u_ctl east, move only) + hc*_o bank sides + b_tw_data_st_a_o south + cws1 window; (3) re-bin from newest placed kits for the 25 STALE-BINS types and retap (V1A retap draft); (4) first-rank seating FIRM at port windows (slw_fe_v1 attempt_5 form). Each as a separate script in v1_cbc/r5 producing a new plan file, then one combined strict (strict_r5_launch.sh tag pred plan).
- Not started by R5: items (1)-(4). Context ran out at the fabric step.

## UPDATE ~11:45 PST
- q1 (round 2 pass 1) ELAB PASSED (native-station fix took); fabric PARAM_REGEN W5 S is GONE. q1 bind 36 errors: R8_STALE 30 (expected, R8 from A4), TYPE_SPLIT 4 (cbn_q00__cl622f65d2, cbn_q00__cldbcda913, cbx_q10__cl89936551_h, cbx_q10__cl94a12200_h: bn vs tn instances differ on ibus bc_i00/bc_i20), PARAM_REGEN 1 (coll_regen SC_X3: seam members shift by [6, 7]), EMIT 1 (cbf_q00__cl870de686 y_o11 rr_t104).
- EMIT fixed: r5_cbf_raw_relay.py now takes the type as arg 4; cbf_q00__cl870de686 y_o11 rr_t104 -> rr_t92 (depth 14, <=194 um) in r5/v1a_r5_fabric_a_raw2_plan.json (contains both relay fixes + fabric).
- q2 (R8 from q1) is running with raw_plan (without the 870 relay). Read it for whether TYPE_SPLIT and SC_X3 clear once R8 is re-derived (likely stale-R8 effects of the X0f bcf2 column-entry raise on bn/tn). If they persist: TYPE_SPLIT = bn and tn instances of one type need identical bcf2 raises/pads (check c_<s>_bn_11__bcf2 vs c_<s>_tn_11__bcf2 and their R8 pads); SC_X3 = a seam group mixing raised and unraised members (find members in coll_regen.py SC_X3 and raise the 6-shift members by 1 or drop the extra one).
- Then q3: `bash strict_r5_launch.sh q3 <w>/r5/strict_q2/bind/bus_groups.json v1a_r5_fabric_a_raw2_plan.json`.

## UPDATE ~14:1x PST (latest; read this first)
### Fabric strict state
- q1/q2 pass elaboration; fabric PARAM_REGEN W5 S gone. The 30 R8_STALE came from the A4 CB16 tree-align extra table zz_extra_s29q103S4Q9N46V0EBQ_0.json (authoritative over derived R8): re-bound by r5/r5_extra_rebound.py to the q2 bind (124 members, pads kept) -> r5/zz_extra_*_{0,1}_r5.json. The strict script now swaps them in (r5/patch_strict.py applied).
- Plan r5/v1a_r5_fabric_a_raw2_plan.json = fabric (a) + both cbf_q00 y_o11 relays (cl1b5a6458 rr_t102->rr_t94, cl870de686 rr_t104->rr_t92).
- q3 launched 14:0x: intel2 ~/qc-plan-r5/strict_q3.log/.rc, epyc9 v1_cbc/r5/strict_q3. Expect R8_STALE 0 and EMIT 0. Open from q2: TYPE_SPLIT x4 (cbn_q00__cl622f65d2, cbn_q00__cldbcda913, cbx_q10__cl89936551_h, cbx_q10__cl94a12200_h: bn vs tn instance ibus bc_i00/bc_i20 differ; suspect the X0f raise on c_<s>_bn_11__bcf2 and c_<s>_tn_11__bcf2 landing differently, or the INNER/R8 pads per instance) and PARAM_REGEN SC_X3 "seam members shift by [6, 7]" (coll_regen.py: one seam group mixes a raised and an unraised member; give the group a uniform shift).
- After strict 0: G0, LATCHECK token impact in the post (COORD accepted price 395k flops / +15 fabric cycles).
### Wave holds (kit_wave hold_items, commit c621d9845ad)
- PACKED-BANK 11 st_a rows, STATION-KNEE 5 rows (sle_ctl x2, su_c x3), CORE-CONTRACT 3 su rows. Release each class when its V1 fix lands. Not held: sle_hc0__cl929603c0__cl4baa7c9c (PARAM-CLASS, needs param_class_split in V1). Posted unblock for slw_st_b_v2__pva66d0f22__pvb80e2003 (bwrap infra).
- NOPROG-KEEP: keep lines for coll_core pkw4 (read-register proof) and pkw2b (only while > -300 ps; remove the pkw2b lines if it drops below -300).
### V1 content still to build (COORD + FABLE-CLOSURE-1515 + FABLE-PD-QC-1600 order)
1. fabric strict 0 (above).
2. cb* reset reach rows from RESET-RELAY-GEN-1530's generic tool (A4 cb* 9 of 9 have reset paths down to -1,746); take its keys.
3. st_a rs_s0/rs_s1 two stages on all 11 st_a types, both buses on ONE occupancy map, +1 cycle (neither raw2 nor ph6/plan_rs fixes it). Do not post V1 while overlaps remain.
4. UNIFY-TOOLS-R3 pad hoist + merged-class rows.
5. su_c x_sc_o 3 stations (269.8 um) on all three su_c types through the ph6 compose (ph6 has 2). Do not post V1 with 2-station x_sc_o.
6. sle_ctl b_hw_hc2_o 4 -> 6 stations (+2), plus the u_tap channel/spread rows (Fable 0945 fix 2).
7. su_l0/l1 three types (sle_su_l0__cl7a55c676, slw_su_l0__cl1a1c1f8f, sle_su_l1__cl5ea486db): core taps -> parent_budget.
8. coll_ftc: pin-side register rows on the 20 unregistered pins (<300 um), details lanes/GEOM-REVIEW.md.
9. Re-bin/retap (25 STALE-BINS), first-rank seating, lockup rows, cb bc_i stations, global 300 station hops (Fable 0945 ranking).
- CORE-LIB-LIMITS-1330 is fixing the dly_spread step that pushed cbf_q01_s2 t_out onto core edges (hop 141 -> 902 um); take its fix.
- Stop list: no slew-limit regen of held cb kits; no relaunch of the 15 rows on A4 inputs; no loosening of the 403 limit; no leaf_um nudge; no 405-form reseat as the V1 form.
