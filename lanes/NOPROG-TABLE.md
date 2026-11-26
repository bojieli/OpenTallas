# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 17:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'UNSIGNABLE': 1, 'GRT-LABEL': 5, 'YOUNG': 66, 'NO-DATA': 14, 'PROGRESS': 23}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc12 | otc-351743-16220 | 351743 | hcpg_run | 12.2 | last meaningful line 11.8 h ago (13/13 lines) | NO-PROGRESS: no new non-iteration log line for 11.8 h | REPORT-ONLY: lane-own kit (abstract-exact decides; |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | pregrt_ff_hold | 7.2 | repair_TNS best 2.44591e+06 last 2.44591e+06 rows 1 | before-window best 2.44591e+06, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (QC-C1O-COMPOSE decides; |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 30.7 | drt_violations best 4 last 4 rows 57 | before-window best 4, window best 4 | NO-PROGRESS: drt_violations best 4 vs 4 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 5_1_grt | 12.8 | grt rounds 4 overflow 5:121909 -> 10:2158 -> 15:1367 -> 20:1472 | UNSIGNABLE: GRT overflow flat: overflow 1367 at iteration 15 -> 1472 at iteration 20: flat f | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 28.9 | drt_violations best 1 last 1 rows 45 | before-window best 1, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc12 | dpkit-sle_ctl__cla4f6f12f-254756 | sle_ctl | 5_1_grt | 5.8 | grt rounds 2 overflow 5:58301 -> 10:29756 | GRT-LABEL: DESIGN-FAIL: overflow 29756 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 5_1_grt | 8.5 | grt rounds 3 overflow 5:130016 -> 10:3224 -> 15:2262 | GRT-LABEL: DESIGN-FAIL: overflow 3224 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | 5_1_grt | 9.9 | grt rounds 6 overflow 5:120028 -> 10:2188 -> 15:1369 -> 20:1502 -> 25:1102 -> 30:804 | GRT-LABEL: DESIGN-FAIL: overflow 2188 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 5_1_grt | 12.7 | grt rounds 6 overflow 5:123883 -> 10:2244 -> 15:1394 -> 20:1584 -> 25:1212 -> 30:970 | GRT-LABEL: DESIGN-FAIL: overflow 2244 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 5_1_grt | 12.9 | grt rounds 6 overflow 5:119162 -> 10:2290 -> 15:1427 -> 20:1597 -> 25:1148 -> 30:913 | GRT-LABEL: DESIGN-FAIL: overflow 2290 at round 10 > 1000 |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-1395551 | col_h9_r0_p5__t1 | 5_2_route | 8.4 | drt_violations best 93339 last 93339 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_1_grt | 8.5 | repair_TNS best 6611.29 last 6611.29 rows 8 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | 5_2_route | 8.5 | drt_violations best 255884 last 255884 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-1130830 | col_h9_r0_p5__t1 | 5_2_route | 8.5 | drt_violations best 77306 last 77306 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc93af856-1168215 | col_h9_r0_p5__t1 | 5_2_route | 8.5 | drt_violations best 70154 last 70154 rows 2 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-1072222 | col_h9_r0_p5__t1 | 5_2_route | 8.6 | drt_violations best 73182 last 73182 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i3-2829259 | eco_20261124_200101_1087713-i3 | 5_1_grt | 0.9 | last meaningful line 0.4 h ago (244/1476 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | pregrt_ff_hold | 3.7 | repair_TNS best 4.053 last 4.053 rows 1 | YOUNG: evidence 2.0 h < 2.5 h |  |
| epyc12 | dpkit-hd_lep0N-3673788 | hd_lep0N | 3_1_place_gp_skip_io | 0.2 | overflow best 0.7804 last 0.7844 rows 10 | YOUNG: stage 0.0 h < 1 h |  |
| epyc12 | dpkit-hd_lep0N_w-3830091 | hd_lep0N_w | 2_4_floorplan_pdn | 0.0 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-hd_serdes-3754625 | hd_serdes | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (280/280 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-hd_st_n4-1311294 | hd_st_n4 | 5_2_route | 1.9 | drt_violations best 16718 last 16718 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc12 | dpkit-kv3_hg_v1p6__ret4_wn_6-3762504 | kv3_hg_v1p6__ret4_wn_6 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (583/583 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-3214015 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.7095 last 0.7095 rows 28 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl7f648944__r8e7d31598-3661363 | kv3_pc_v1 | 2_1_floorplan | 0.2 | repair_Viol best 8517 last 8517 rows 1244 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-ot_s81sl_leaf__t35-3680562 | ot_s81sl_leaf__t35 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (165/165 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t50__cld84c9e24-650458 | slice_station__t50 | 5_2_route | 2.5 | drt_violations best 18660 last 18660 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 14.4 |  | NO-DATA: no log found |  |
| epyc12 | so_3688077_tt_63706 | so_3688077_tt_63706 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | 5_2_route | 8.6 | drt_violations best 211004 last 211004 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 12.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 12.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 12.2 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | postcts_gate_TT | 12.3 | last meaningful line 0.2 h ago (23/23 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 5_2_route | 12.0 | drt_violations best 2810 last 2810 rows 6 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-362758 | slw_hc2 | 5_2_route | 7.3 | drt_violations best 9330 last 9330 rows 2 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | otc-2152091-6999 | 2152091 | signoff | 0.6 | last meaningful line 0.5 h ago (3/3 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | otc-2739402-5290 | 2739402 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc7 | otc-639211-10962 | 639211 | - | 8.7 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-kv3_hub_Eo-1982614 | kv3_hub_Eo | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-native59-2892451 | native59 | 5_2_route | 6.8 | drt_violations best 24988 last 24988 rows 2 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 7.4 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | otc-1616827-18813 | 1616827 | - | 9.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-3731784-29079 | 3731784 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-816499-29893 | 816499 | signoff | 0.6 | last meaningful line 0.5 h ago (3/3 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | so_1475891_tt_49989 | so_1475891_tt_49989 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (33/33 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | so_2100829_ff_24922 | so_2100829_ff_24922 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc8 | so_2100829_tt_24922 | so_2100829_tt_24922 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3804990 | col_h10_r0_p1__t1 | 5_1_grt | 8.0 | last meaningful line 0.7 h ago (275/1289 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-1427167 | col_h10_r0_p1__t1 | 5_1_grt | 9.2 | last meaningful line 0.2 h ago (2549/2609 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 6_report | 19.0 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 6.4 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 8.4 | drt_violations best 174806 last 174806 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-870318 | col_h9_r0_p3__t1 | 5_1_grt | 7.8 | repair_Remaining best 111382 last 111382 rows 171 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 10.0 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 7.0 | last meaningful line 0.7 h ago (273/274 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 7.2 | last meaningful line 0.5 h ago (274/275 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 8.0 | last meaningful line 0.5 h ago (278/279 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 10.0 | drt_violations best 178781 last 178781 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-138946 | col_h9_r2__t1 | 5_2_route | 6.4 | drt_violations best 151829 last 151829 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 8.5 | last meaningful line 0.7 h ago (280/281 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 6.5 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | 5_2_route | 9.8 | drt_violations best 3962 last 3962 rows 7 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 5_2_route | 9.3 | drt_violations best 159056 last 159056 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 8.5 | drt_violations best 35075 last 35075 rows 2 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 4_1_cts | 6.9 | last meaningful line 0.2 h ago (8616/8616 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 8.5 | repair_TNS best 496091 last 496091 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | so_1356878_ff_25678 | so_1356878_ff_25678 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc9 | so_1356878_tt_25678 | so_1356878_tt_25678 | signoff | 0.2 |  | NO-DATA: empty log |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 12.9 | repair_TNS best 11768.4 last 11768.4 rows 8 | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | 5_2_route | 12.9 | drt_violations best 28063 last 28063 rows 3 | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 7.3 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-3824626 | coll_ftc | 5_2_route | 7.4 | last meaningful line 0.2 h ago (257/258 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Wo-190641 | kv3_hub_Wo | 1_synth | 0.0 | last meaningful line 0.0 h ago (10/10 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | postcts_gate_FF | 7.9 | last meaningful line 0.0 h ago (652/652 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-4035353 | slw_hc3 | 5_2_route | 7.3 | last meaningful line 0.0 h ago (264/265 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | otc-178621-11182 | 178621 | - | 1.9 |  | NO-DATA: no log found |  |
| intel1 | otc-2021095-31410 | 2021095 | signoff | 4.9 | last meaningful line 4.8 h ago (3/3 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel1 | otc-207040-3394 | 207040 | signoff | 1.9 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | otc-2908840-11609 | 2908840 | grt_it0 | 7.7 | last meaningful line 4.0 h ago (33/34 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | otc-3479258-28963 | 3479258 | - | 2.3 |  | NO-DATA: no log found |  |
| intel1 | otc-957737-21247 | 957737 | signoff | 1.6 | last meaningful line 1.5 h ago (3/3 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | prd-count-p1_tc-1093733 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (50/50 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i3-3236766 | eco_20261123_191853_2879776-i3 | 5_2_route | 4.3 | last meaningful line 0.1 h ago (300/301 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i2t-515416 | eco_20261125_050013_1448739-i2t | 5_2_route | 1.8 | last meaningful line 0.2 h ago (263/264 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | prd-eco_20261125_070347_2847958-i2-1134837 | eco_20261125_070347_2847958-i2 | 5_2_route | 1.5 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | prd-eco_20261125_131510_2862538-i3t-4003777 | eco_20261125_131510_2862538-i3t | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (280/425 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-925629 | coll_ftm | 6_1_fill | 2.2 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_Wi-2160767 | kv3_hub_Wi | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 7.2 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 30.9 | drt_violations best 212 last 212 rows 51 | before-window best 232, window best 212 | PROGRESS: drt_violations improved 8.6 % in window |  |
| epyc12 | dpkit-native59-478901 | native59 | 5_1_grt | 5.6 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc12 | dpkit-slice_station__t24__cl64811a5d-1102657 | slice_station__t24 | 5_2_route | 2.1 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
| epyc12 | otc-3501458-13012 | 3501458 | drc_macros_only | 14.4 | last meaningful line 0.3 h ago (697/697 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 16.0 | drt_violations best 1 last 1 rows 54 | before-window best 2, window best 1 | PROGRESS: drt_violations improved 50.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 16.2 | drt_violations best 5720 last 5720 rows 12 | before-window best 477402, window best 5720 | PROGRESS: drt_violations improved 98.8 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 16.2 | drt_violations best 21571 last 21571 rows 9 | before-window best 493451, window best 21571 | PROGRESS: drt_violations improved 95.6 % in window |  |
| epyc7 | dpkit-sle_sc_v2-22145 | sle_sc_v2 | 5_2_route | 10.5 | drt_violations best 68058 last 68058 rows 8 | before-window best 412199, window best 68058 | PROGRESS: drt_violations improved 83.5 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 16.6 | drt_violations best 1501 last 1501 rows 16 | before-window best 468535, window best 1501 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 19.3 | drt_violations best 1357 last 1357 rows 21 | before-window best 15877, window best 1357 | PROGRESS: drt_violations improved 91.5 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 9.4 | drt_violations best 15556 last 15556 rows 13 | before-window best 102693, window best 15556 | PROGRESS: drt_violations improved 84.9 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 33.6 | drt_violations best 13 last 13 rows 53 | before-window best 18, window best 13 | PROGRESS: drt_violations improved 27.8 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 5_2_route | 10.0 | drt_violations best 176025 last 176025 rows 1 | before-window best 176025, window best 176025 | PROGRESS: drt_violations: active iteration at 48388 < best completed total 176025 (in-iter |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | 5_1_grt | 5.9 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 19.0 | drt_violations best 13885 last 13885 rows 5 | before-window best 535484, window best 13885 | PROGRESS: drt_violations improved 97.4 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_1_grt | 6.4 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 16.2 | drt_violations best 118691 last 118691 rows 2 | before-window best 470122, window best 118691 | PROGRESS: drt_violations improved 74.8 % in window |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | pregrt_ff_hold | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 20.9 | drt_violations best 392 last 392 rows 51 | before-window best 553, window best 392 | PROGRESS: drt_violations improved 29.1 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-2945122 | col_h9_r2__t1 | 5_2_route | 9.7 | drt_violations best 384 last 384 rows 17 | before-window best 154176, window best 384 | PROGRESS: drt_violations improved 99.8 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | 5_2_route | 12.8 | drt_violations best 4529 last 4529 rows 4 | before-window best 159843, window best 4529 | PROGRESS: drt_violations improved 97.2 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_2_route | 12.8 | drt_violations best 4050 last 4050 rows 5 | before-window best 159806, window best 4050 | PROGRESS: drt_violations improved 97.5 % in window |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 26.4 | drt_violations best 6603 last 6603 rows 8 | before-window best 278493, window best 6603 | PROGRESS: drt_violations improved 97.6 % in window |  |
