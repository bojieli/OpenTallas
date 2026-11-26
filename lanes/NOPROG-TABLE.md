# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 18:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'GRT-LABEL': 6, 'YOUNG': 73, 'NO-DATA': 21, 'PROGRESS': 17}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 16.2 | drt_violations best 1 last 1 rows 54 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-STA-PROBE decides; n |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | pregrt_ff_hold | 7.5 | repair_TNS best 2.44591e+06 last 2.44591e+06 rows 1 | before-window best 2.44591e+06, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (QC-C1O-COMPOSE decides; |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 30.9 | drt_violations best 4 last 4 rows 57 | before-window best 4, window best 4 | NO-PROGRESS: drt_violations best 4 vs 4 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 29.1 | drt_violations best 1 last 1 rows 45 | before-window best 1, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc12 | dpkit-sle_ctl__cla4f6f12f-254756 | sle_ctl | 5_1_grt | 6.0 | grt rounds 2 overflow 5:58301 -> 10:29756 | GRT-LABEL: DESIGN-FAIL: overflow 29756 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 5_1_grt | 8.7 | grt rounds 3 overflow 5:130016 -> 10:3224 -> 15:2262 | GRT-LABEL: DESIGN-FAIL: overflow 3224 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | 5_1_grt | 10.2 | grt rounds 6 overflow 5:120028 -> 10:2188 -> 15:1369 -> 20:1502 -> 25:1102 -> 30:804 | GRT-LABEL: DESIGN-FAIL: overflow 2188 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 5_1_grt | 13.0 | grt rounds 5 overflow 5:121909 -> 10:2158 -> 15:1367 -> 20:1472 -> 25:1063 | GRT-LABEL: DESIGN-FAIL: overflow 2158 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 5_1_grt | 13.0 | grt rounds 6 overflow 5:123883 -> 10:2244 -> 15:1394 -> 20:1584 -> 25:1212 -> 30:970 | GRT-LABEL: DESIGN-FAIL: overflow 2244 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 5_1_grt | 13.1 | grt rounds 6 overflow 5:119162 -> 10:2290 -> 15:1427 -> 20:1597 -> 25:1148 -> 30:913 | GRT-LABEL: DESIGN-FAIL: overflow 2290 at round 10 > 1000 |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-1395551 | col_h9_r0_p5__t1 | 5_2_route | 8.6 | drt_violations best 93339 last 93339 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_1_grt | 8.8 | repair_TNS best 5859.48 last 5859.48 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | 5_2_route | 8.8 | drt_violations best 255884 last 255884 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-1130830 | col_h9_r0_p5__t1 | 5_2_route | 8.8 | drt_violations best 77306 last 77306 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc93af856-1168215 | col_h9_r0_p5__t1 | 5_2_route | 8.8 | drt_violations best 46130 last 46130 rows 3 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-1072222 | col_h9_r0_p5__t1 | 5_2_route | 8.8 | drt_violations best 73182 last 73182 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc11 | ppr-dpkit-col_h9_r0_p5__t1__pveda1ecc9-10722-601954 | ppr-dpkit-col_h9_r0_p5__t1 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc11 | prd-eco_20261124_200101_1087713-i3-2829259 | eco_20261124_200101_1087713-i3 | 5_1_grt | 1.1 | last meaningful line 0.7 h ago (244/1497 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc12 | ap-render-otc-3889847-14103-17612 | ap-render-otc-3889847-14103 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | pregrt_ff_hold | 4.0 | repair_TNS best 4.053 last 4.053 rows 1 | YOUNG: evidence 2.2 h < 2.5 h |  |
| epyc12 | dpkit-hd_lep0N-3673788 | hd_lep0N | 3_3_place_gp | 0.4 | overflow best 0.5643 last 0.5643 rows 4 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-hd_lep0N_w-3830091 | hd_lep0N_w | 3_5_place_dp | 0.3 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-hd_serdes-3754625 | hd_serdes | 3_3_place_gp | 0.4 | overflow best 0.0875 last 0.9162 rows 17 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-hd_st_n4-1311294 | hd_st_n4 | generate_abstract | 2.2 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-kv3_hg_v1p6__ret4_wn_6-3762504 | kv3_hg_v1p6__ret4_wn_6 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (60/60 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-3214015 | kv3_pc_v1 | 3_3_place_gp | 0.7 | overflow best 0.641 last 0.641 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl7f648944__r8e7d31598-3661363 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.8682 last 0.9018 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-native59-478901 | native59 | 5_1_grt | 5.9 | last meaningful line 0.0 h ago (1864/1870 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t24__cl64811a5d-1102657 | slice_station__t24 | generate_abstract | 2.4 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t50__cld84c9e24-650458 | slice_station__t50 | 5_2_route | 2.7 | drt_violations best 18660 last 18660 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc12 | dproto-kv-a5t9_r6-kit | dproto-kv-a5t9_r6-kit | qc_c1p_r6_proto | 0.1 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dproto-qc-c1p_r6-kit | dproto-qc-c1p_r6-kit | qc_c1p_r6_proto | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dproto-s81-c10b_r10-kit | dproto-s81-c10b_r10-kit | qc_c1p_r6_proto | 0.1 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 14.6 |  | NO-DATA: no log found |  |
| epyc12 | otc-14795-12361 | 14795 | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (11/11 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | otc-3889847-14103 | 3889847 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-hd_ctl-2980421 | hd_ctl | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3023/3023 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | 5_2_route | 8.8 | drt_violations best 211004 last 211004 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-2967544 | sle_hc0 | 3_3_place_gp | 0.2 | overflow best 0.0997 last 0.0997 rows 50 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 3_3_place_gp | 0.1 | overflow best 0.3656 last 0.3661 rows 5 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 12.4 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 12.4 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 12.4 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | postcts_gate_FF | 12.5 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 5_2_route | 12.3 | drt_violations best 1182 last 1182 rows 10 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-362758 | slw_hc2 | 6_1_fill | 7.6 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-2152091-6999 | 2152091 | signoff | 0.9 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | otc-2739402-5290 | 2739402 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc7 | otc-639211-10962 | 639211 | - | 9.0 |  | NO-DATA: no log found |  |
| epyc7 | ppr-otc-2739402-5290-3964600 | ppr-otc-2739402-5290 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-kv3_hub_Eo-1982614 | kv3_hub_Eo | 3_1_place_gp_skip_io | 0.5 | overflow best 0.2541 last 0.2541 rows 40 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-native59-2892451 | native59 | 5_2_route | 7.1 | drt_violations best 24988 last 24988 rows 2 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 7.6 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | otc-1616827-18813 | 1616827 | - | 9.7 |  | NO-DATA: no log found |  |
| epyc8 | otc-3731784-29079 | 3731784 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc8 | otc-816499-29893 | 816499 | signoff | 0.9 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_104318_3955073-i3t-2865255 | eco_20261125_104318_3955073-i3t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | so_2100829_ff_24922 | so_2100829_ff_24922 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc8 | so_2100829_tt_24922 | so_2100829_tt_24922 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc9 | ap-render-so_3309064_tt_9660-3735768 | ap-render-so_3309064_tt_9660 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3804990 | col_h10_r0_p1__t1 | 5_1_grt | 8.3 | last meaningful line 0.1 h ago (1318/1358 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-1427167 | col_h10_r0_p1__t1 | 5_1_grt | 9.5 | last meaningful line 0.2 h ago (2621/2646 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 6.6 | last meaningful line 0.3 h ago (275/276 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 8.7 | drt_violations best 174806 last 174806 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-870318 | col_h9_r0_p3__t1 | 5_1_grt | 8.0 | repair_Remaining best 111382 last 111382 rows 171 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | 5_1_grt | 6.1 | repair_Remaining best 202109 last 202109 rows 29 | YOUNG: stage 1.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 10.3 | last meaningful line 0.3 h ago (281/282 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_1_grt | 6.7 | last meaningful line 0.0 h ago (2499/2530 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 7.2 | last meaningful line 0.3 h ago (275/276 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 7.4 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 8.2 | last meaningful line 0.5 h ago (280/281 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 10.2 | drt_violations best 178781 last 178781 rows 1 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-138946 | col_h9_r2__t1 | 5_2_route | 6.7 | drt_violations best 151829 last 151829 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 8.7 | drt_violations best 178567 last 178567 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 6.7 | last meaningful line 0.3 h ago (276/277 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | 5_2_route | 10.1 | drt_violations best 3481 last 3481 rows 9 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 5_2_route | 9.5 | drt_violations best 159056 last 159056 rows 1 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 8.8 | drt_violations best 35075 last 35075 rows 2 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 4_1_cts | 7.1 | last meaningful line 0.0 h ago (8638/8638 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 8.8 | repair_TNS best 496091 last 496091 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc9 | otc-2673571-2660 | 2673571 | signoff | 0.2 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | so_3309064_ff_9660 | so_3309064_ff_9660 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | so_3309064_tt_9660 | so_3309064_tt_9660 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 13.1 | grt_hold_TNS best 10372.2 last 10372.2 rows 3 | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 7.5 | last meaningful line 0.3 h ago (274/275 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-3824626 | coll_ftc | 5_2_route | 7.7 | last meaningful line 0.1 h ago (261/262 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Wo-190641 | kv3_hub_Wo | 2_1_floorplan | 0.3 | last meaningful line 0.0 h ago (107/107 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | postcts_gate_FF | 8.1 | last meaningful line 0.0 h ago (718/718 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-4035353 | slw_hc3 | 5_2_route | 7.6 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | otc-178621-11182 | 178621 | - | 2.2 |  | NO-DATA: no log found |  |
| intel1 | otc-207040-3394 | 207040 | signoff | 2.2 | last meaningful line 2.1 h ago (3/3 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | otc-2908840-11609 | 2908840 | grt_i0 | 8.0 | last meaningful line 0.0 h ago (12/12 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-3479258-28963 | 3479258 | - | 2.6 |  | NO-DATA: no log found |  |
| intel1 | otc-675865-696 | 675865 | grt_i0 | 0.1 | last meaningful line 0.0 h ago (12/12 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-957737-21247 | 957737 | signoff | 1.8 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i3-3236766 | eco_20261123_191853_2879776-i3 | 5_2_route | 4.6 | last meaningful line 0.3 h ago (302/303 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i2t-515416 | eco_20261125_050013_1448739-i2t | 5_2_route | 2.0 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | prd-eco_20261125_070347_2847958-i2-1134837 | eco_20261125_070347_2847958-i2 | 5_2_route | 1.8 | last meaningful line 0.3 h ago (133/133 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | prd-eco_20261125_131510_2862538-i3t-4003777 | eco_20261125_131510_2862538-i3t | 5_2_route | 0.5 | last meaningful line 0.0 h ago (238/239 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-fin-1093733 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_Wi-2160767 | kv3_hub_Wi | 2_1_floorplan | 0.4 | repair_Viol best 4933 last 4933 rows 107 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 7.5 | last meaningful line 0.3 h ago (275/276 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | so_3018410_ff_28432 | so_3018410_ff_28432 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_3018410_tt_28432 | so_3018410_tt_28432 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 31.2 | drt_violations best 212 last 212 rows 51 | before-window best 232, window best 212 | PROGRESS: drt_violations improved 8.6 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 16.5 | drt_violations best 5720 last 5720 rows 12 | before-window best 477402, window best 5720 | PROGRESS: drt_violations improved 98.8 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 16.5 | drt_violations best 21571 last 21571 rows 9 | before-window best 493451, window best 21571 | PROGRESS: drt_violations improved 95.6 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 16.9 | drt_violations best 1145 last 1145 rows 17 | before-window best 468535, window best 1145 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 19.6 | drt_violations best 1357 last 1357 rows 21 | before-window best 13897, window best 1357 | PROGRESS: drt_violations improved 90.2 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 9.7 | drt_violations best 15556 last 15556 rows 13 | before-window best 78477, window best 15556 | PROGRESS: drt_violations improved 80.2 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 33.9 | drt_violations best 13 last 13 rows 53 | before-window best 18, window best 13 | PROGRESS: drt_violations improved 27.8 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 5_2_route | 10.3 | drt_violations best 36885 last 36885 rows 2 | before-window best 176025, window best 36885 | PROGRESS: drt_violations improved 79.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 19.3 | drt_violations best 10099 last 10099 rows 6 | before-window best 535484, window best 10099 | PROGRESS: drt_violations improved 98.1 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 16.4 | drt_violations best 118691 last 118691 rows 2 | before-window best 470122, window best 118691 | PROGRESS: drt_violations improved 74.8 % in window |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | pregrt_ff_hold | 6.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 21.1 | drt_violations best 392 last 392 rows 51 | before-window best 553, window best 392 | PROGRESS: drt_violations improved 29.1 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-2945122 | col_h9_r2__t1 | 5_2_route | 9.9 | drt_violations best 375 last 375 rows 20 | before-window best 154176, window best 375 | PROGRESS: drt_violations improved 99.8 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | 5_2_route | 13.2 | drt_violations best 28063 last 28063 rows 3 | before-window best 178263, window best 28063 | PROGRESS: drt_violations improved 84.3 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | 5_2_route | 13.0 | drt_violations best 1981 last 1981 rows 6 | before-window best 159843, window best 1981 | PROGRESS: drt_violations improved 98.8 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_2_route | 13.0 | drt_violations best 3088 last 3088 rows 6 | before-window best 159806, window best 3088 | PROGRESS: drt_violations improved 98.1 % in window |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 26.7 | drt_violations best 5844 last 5844 rows 9 | before-window best 278493, window best 5844 | PROGRESS: drt_violations improved 97.9 % in window |  |
