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
