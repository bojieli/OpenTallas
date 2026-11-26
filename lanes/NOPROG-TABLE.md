# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-26 02:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'UNSIGNABLE': 2, 'GRT-STUCK': 1, 'GRT-LABEL': 1, 'YOUNG': 43, 'NO-DATA': 4, 'EXCLUDED': 3, 'KEEP': 1, 'PROGRESS': 20}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 8.0 | last meaningful line 6.0 h ago (33/34 lines) | NO-PROGRESS: no new non-iteration log line for 6.0 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | 5_1_grt | 12.7 | grt rounds 9 overflow 20:894 -> 25:15 -> 30:4 -> 35:8 -> 40:1 -> 45:2 | UNSIGNABLE: GRT overflow flat: overflow 1 at iteration 40 -> 2 at iteration 45: flat for 5 i | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | pregrt_ff_hold | 5.4 | repair_TNS best 18063.2 last 18063.2 rows 1 | before-window best 18063.2, window best 18063.2 | NO-PROGRESS: repair_TNS best 18063.2 vs 18063.2 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 5_1_grt | 17.5 | grt rounds 9 overflow 20:2305 -> 25:2156 -> 30:1933 -> 35:1923 -> 40:2127 -> 45:2007 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (35:1923 -> 40:2127 -> 45:2007; best 2007 | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 15.3 | grt rounds 8 overflow 15:2296 -> 20:2337 -> 25:2143 -> 30:1999 -> 35:1942 -> 40:2129 | UNSIGNABLE: GRT overflow flat: overflow 1942 at iteration 35 -> 2129 at iteration 40: flat f | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 21.9 | repair_Viol best 968 last 968 rows 145 | before-window best 968, window best 968 | NO-PROGRESS: repair_Viol best 968 vs 968 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 37.9 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 5_1_grt | 15.9 | grt rounds 2 overflow 5:77168 -> 10:41977 | GRT-LABEL: DESIGN-FAIL: overflow 41977 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-2708094 | dsdv_slice_c1x_C__t5 | 5_1_grt | 4.6 | last meaningful line 0.0 h ago (161/161 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-712515 | hd_lep0N | 4_2_tapbal_grt | 2.0 | last meaningful line 1.0 h ago (48/52 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | lecaf-hdm-whole-exact-cohorts | lecaf-hdm-whole-exact-cohorts | - | 1.8 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-q9-stb-e1d-archive-elab | lecaf-q9-stb-e1d-archive-elab | gate.ys | 1.0 | last meaningful line 0.7 h ago (211823/211823 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_2_route | 17.5 | drt_violations best 70301 last 70301 rows 2 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc11 | dpkit-svc_lo_dsdv_svc_rs_w__t1-1738997 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 1.6 | last meaningful line 0.8 h ago (626/626 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1991043 | sle_stm_v2 | generate_abstract | 7.1 | last meaningful line 0.1 h ago (29/29 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-1997619 | sle_stm_v2 | 5_2_route | 7.1 | drt_violations best 96273 last 96273 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_2_route | 8.9 | drt_violations best 46175 last 46175 rows 2 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261125_200405_3323313-i2-2794007 | eco_20261125_200405_3323313-i2 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_015555_2965752-i1t-7345 | eco_20261126_015555_2965752-i1t | 5_2_route | 0.8 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 4.8 | last meaningful line 4.0 h ago (700/700 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 3.5 | drt_violations best 58 last 58 rows 14 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261126_090542_621054-i1t-2265448 | eco_20261126_090542_621054-i1t | 5_2_route | 1.6 | drt_violations best 38251 last 38251 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | prd-eco_20261126_033711_2888564-i2t-1658020 | eco_20261126_033711_2888564-i2t | 5_2_route | 1.4 | drt_violations best 3583 last 3583 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | pregrt_ff_hold | 4.4 | repair_TNS best 35372.7 last 35372.7 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 6_report | 15.4 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | 5_1_grt | 5.7 | last meaningful line 0.2 h ago (274/1280 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | 5_1_grt | 5.3 | last meaningful line 0.0 h ago (154/154 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-2823500 | col_h9_r1__t1 | pregrt_ff_hold | 5.0 | repair_TNS best 71970 last 71970 rows 1 | YOUNG: evidence 1.7 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2325128 | col_h9_r1__t1 | pregrt_ff_hold | 5.1 | repair_TNS best 110976 last 110976 rows 1 | YOUNG: evidence 1.8 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8aaf8508-3602152 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.4 | last meaningful line 0.8 h ago (61/77 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-3901907 | col_h9_r1__t1 | pregrt_ff_hold | 4.8 | repair_TNS best 99737.1 last 99737.1 rows 1 | YOUNG: evidence 1.4 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2382304 | col_h9_r1__t1 | pregrt_ff_hold | 5.1 | repair_TNS best 177431 last 177431 rows 1 | YOUNG: evidence 1.8 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-2530599 | col_h9_r1__t1 | pregrt_ff_hold | 5.1 | repair_TNS best 47356.8 last 47356.8 rows 1 | YOUNG: evidence 1.9 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvfef7c177-3709744 | col_h9_r2__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 35172.1 last 35172.1 rows 1 | YOUNG: evidence 1.5 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | tt_setup_repair_grt | 4.8 | last meaningful line 0.0 h ago (1026/1026 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-4156698 | col_h9_r2__t1 | postcts_gate_FF | 3.9 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | 5_2_route | 5.5 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfd79e8b6-2469832 | col_h9_r2__t1 | 5_1_grt | 3.4 | last meaningful line 0.0 h ago (264/266 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-4056356 | dsdv_slice_c1x_C__t8 | selrange | 1.3 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-ot_s81sl_leaf__t1-3555509 | ot_s81sl_leaf__t1 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (8357/8357 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-479268 | sle_su_l1 | 5_2_route | 4.6 | last meaningful line 0.1 h ago (259/260 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t26-3959180 | slice_station__t26 | 5_2_route | 2.3 | last meaningful line 0.1 h ago (255/256 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t29__cl2e5c855a-3827558 | slice_station__t29 | tt_setup_repair_grt | 1.4 | last meaningful line 0.0 h ago (234/234 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t29__clc7772371-1992482 | slice_station__t29 | 5_2_route | 1.8 | last meaningful line 0.1 h ago (235/235 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__cl1ea9de02-813226 | slice_station__t40 | postcts_gate_TT | 2.0 | last meaningful line 0.1 h ago (41318/41318 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 5_1_grt | 5.2 | grt_hold_TNS best 113064 last 113064 rows 4 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | otc-903470-4134 | 903470 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_072708_1527702-i1-3266022 | eco_20261126_072708_1527702-i1 | 5_2_route | 3.3 | drt_violations best 57150 last 57150 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_091926_2909746-i1t-3764749 | eco_20261126_091926_2909746-i1t | 5_2_route | 1.4 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | eco-abs-1749184 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.1 h ago (29/29 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 6.4 |  | NO-DATA: no log found |  |
| intel1 | lecq9-963f0492a10e | lecq9-963f0492a10e | - | 6.5 |  | NO-DATA: no log found |  |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 8.0 | last meaningful line 4.3 h ago (33/34 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | 5_2_route | 5.5 | drt_violations best 3 last 3 rows 36 | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t5-331755 | dsdv_slice_c1x_C__t5 | 3_3_place_gp | 2.4 | overflow best 0.6192 last 0.6192 rows 42 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 21.2 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 21.2 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 21.2 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-454895 | col_h9_r1__t1 | 4_2_tapbal_grt | 3.0 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 39.9 | drt_violations best 200 last 204 rows 58 | before-window best 200, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 25.2 | drt_violations best 3665 last 6896 rows 20 | before-window best 3875, window best 3665 | PROGRESS: drt_violations improved 5.4 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 25.2 | drt_violations best 12441 last 12441 rows 15 | before-window best 16003, window best 12441 | PROGRESS: drt_violations improved 22.3 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 25.6 | drt_violations best 421 last 421 rows 37 | before-window best 724, window best 421 | PROGRESS: drt_violations improved 41.9 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 16.4 | drt_violations best 1752 last 10932 rows 18 | before-window best 9504, window best 1752 | PROGRESS: drt_violations improved 81.6 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 42.6 | drt_violations best 11 last 11 rows 55 | before-window best 13, window best 11 | PROGRESS: drt_violations improved 15.4 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 17.4 | drt_violations best 9 last 9 rows 53 | before-window best 22097, window best 9 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 19.0 | drt_violations best 97668 last 97668 rows 3 | before-window best 545016, window best 97668 | PROGRESS: drt_violations improved 82.1 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 15.4 | drt_violations best 120549 last 120549 rows 2 | before-window best 486708, window best 120549 | PROGRESS: drt_violations improved 75.2 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 25.2 | drt_violations best 446 last 449 rows 26 | before-window best 77076, window best 446 | PROGRESS: drt_violations improved 99.4 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 16.0 | drt_violations best 20574 last 20574 rows 5 | before-window best 380531, window best 20574 | PROGRESS: drt_violations improved 94.6 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 16.2 | drt_violations best 453 last 453 rows 23 | before-window best 171015, window best 453 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 17.0 | drt_violations best 1822 last 1822 rows 16 | before-window best 43234, window best 1822 | PROGRESS: drt_violations improved 95.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 19.0 | drt_violations best 995 last 995 rows 23 | before-window best 5497, window best 995 | PROGRESS: drt_violations improved 81.9 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 29.9 | drt_violations best 390 last 408 rows 58 | before-window best 390, window best 390 | PROGRESS: drt_violations: falling inside the active iteration (408 -> 395) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 17.5 | drt_violations best 477 last 477 rows 23 | before-window best 44089, window best 477 | PROGRESS: drt_violations improved 98.9 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 15.5 | drt_violations best 370 last 370 rows 43 | before-window best 162182, window best 370 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 17.5 | drt_violations best 384 last 384 rows 51 | before-window best 882, window best 384 | PROGRESS: drt_violations improved 56.5 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 16.3 | drt_violations best 1467 last 1467 rows 16 | before-window best 167111, window best 1467 | PROGRESS: drt_violations improved 99.1 % in window |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 16.2 | drt_violations best 6 last 6 rows 43 | before-window best 211273, window best 6 | PROGRESS: drt_violations improved 100.0 % in window |  |
