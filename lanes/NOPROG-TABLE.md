# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-26 03:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 8, 'GRT-LABEL': 1, 'YOUNG': 37, 'NO-DATA': 2, 'EXCLUDED': 3, 'KEEP': 1, 'PROGRESS': 22}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 9.0 | last meaningful line 7.0 h ago (33/35 lines) | NO-PROGRESS: no new non-iteration log line for 7.0 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | pregrt_ff_hold | 5.4 | repair_TNS best 35372.7 last 35372.7 rows 1 | before-window best 35372.7, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2325128 | col_h9_r1__t1 | pregrt_ff_hold | 6.1 | repair_TNS best 261.535 last 261.535 rows 1 | before-window best 261.535, window best 261.535 | NO-PROGRESS: repair_TNS best 261.535 vs 261.535 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-3901907 | col_h9_r1__t1 | pregrt_ff_hold | 5.8 | repair_TNS best 99737.1 last 99737.1 rows 1 | before-window best 99737.1, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2382304 | col_h9_r1__t1 | pregrt_ff_hold | 6.1 | repair_TNS best 177431 last 177431 rows 1 | before-window best 177431, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 30.9 | drt_violations best 390 last 408 rows 58 | before-window best 390, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 22.9 | repair_Viol best 968 last 968 rows 187 | before-window best 968, window best 968 | NO-PROGRESS: repair_Viol best 968 vs 968 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 38.9 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 16.3 | grt rounds 9 overflow 20:2337 -> 25:2143 -> 30:1999 -> 35:1942 -> 40:2129 -> 45:2042 | GRT-LABEL: DESIGN-FAIL: overflow 3237 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-2708094 | dsdv_slice_c1x_C__t5 | 5_1_grt | 5.6 | last meaningful line 0.5 h ago (277/1282 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | lecaf-hdm-whole-exact-cohorts | lecaf-hdm-whole-exact-cohorts | - | 2.8 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_2_route | 18.5 | drt_violations best 393 last 393 rows 14 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc11 | dpkit-svc_lo_dsdv_svc_rs_w__t1-1738997 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 2.6 | last meaningful line 1.8 h ago (626/626 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-1997619 | sle_stm_v2 | 6_report | 8.1 | last meaningful line 0.1 h ago (68/68 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_2_route | 9.9 | drt_violations best 89 last 89 rows 15 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_015555_2965752-i1t-7345 | eco_20261126_015555_2965752-i1t | 5_2_route | 1.8 | drt_violations best 921 last 921 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_033735_1990069-i1t-128004 | eco_20261126_033735_1990069-i1t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2514586 | hd_lep0N | 3_1_place_gp_skip_io | 0.3 | overflow best 0.1997 last 0.1997 rows 43 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N_w-2954506 | hd_lep0N_w | 3_1_place_gp_skip_io | 0.1 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 5.8 | last meaningful line 5.0 h ago (700/700 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 4.5 | drt_violations best 45 last 45 rows 19 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | prd-fin-2265448 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261126_033711_2888564-i2-136808 | eco_20261126_033711_2888564-i2 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | 5_2_route | 6.7 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | 5_1_grt | 6.3 | last meaningful line 0.5 h ago (1311/2405 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8aaf8508-3602152 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.4 | last meaningful line 1.8 h ago (61/88 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-2530599 | col_h9_r1__t1 | 5_1_grt | 6.1 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | 5_2_route | 5.8 | last meaningful line 0.2 h ago (265/266 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-4156698 | col_h9_r2__t1 | 5_2_route | 4.9 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | 5_2_route | 6.5 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfd79e8b6-2469832 | col_h9_r2__t1 | postcts_gate_FF | 4.4 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-4056356 | dsdv_slice_c1x_C__t8 | synth_odb_v | 2.3 | last meaningful line 0.6 h ago (4/4 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t1-3555509 | ot_s81sl_leaf__t1 | pregrt_ff_hold | 2.4 | repair_TNS best 683593 last 683593 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-479268 | sle_su_l1 | 5_2_route | 5.6 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t26-3959180 | slice_station__t26 | 5_2_route | 3.3 | drt_violations best 12931 last 12931 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t29__cl2e5c855a-3827558 | slice_station__t29 | 5_2_route | 2.4 | last meaningful line 0.2 h ago (246/247 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t29__clc7772371-1992482 | slice_station__t29 | 5_2_route | 2.8 | last meaningful line 0.1 h ago (248/249 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__cl1ea9de02-813226 | slice_station__t40 | 5_2_route | 3.0 | last meaningful line 0.2 h ago (253/254 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 5_1_grt | 6.2 | repair_TNS best 105144 last 105144 rows 7 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_072708_1527702-i1-3266022 | eco_20261126_072708_1527702-i1 | 5_2_route | 4.3 | drt_violations best 6 last 6 rows 7 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_091926_2909746-i1t-3764749 | eco_20261126_091926_2909746-i1t | 5_2_route | 2.4 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_110525_292982-i1-2906749 | eco_20261126_110525_292982-i1 | 5_2_route | 0.6 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 7.4 |  | NO-DATA: no log found |  |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 9.0 | last meaningful line 5.3 h ago (33/34 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | so_2806680_ff_28414 | so_2806680_ff_28414 | generate_abstract | 0.5 | last meaningful line 0.5 h ago (35/35 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | so_2806680_tt_28414 | so_2806680_tt_28414 | generate_abstract | 0.5 | last meaningful line 0.5 h ago (35/35 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | 5_2_route | 6.5 | drt_violations best 3 last 3 rows 42 | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t5-331755 | dsdv_slice_c1x_C__t5 | 3_5_place_dp | 3.4 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 22.2 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 22.2 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 22.2 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-454895 | col_h9_r1__t1 | pregrt_ff_hold | 4.0 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 40.9 | drt_violations best 200 last 204 rows 58 | before-window best 200, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| epyc2 | prd-eco_20261125_200405_3323313-i2-2794007 | eco_20261125_200405_3323313-i2 | 5_2_route | 1.1 | drt_violations best 0 last 0 rows 1 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 26.2 | drt_violations best 3665 last 6082 rows 21 | before-window best 3792, window best 3665 | PROGRESS: drt_violations improved 3.3 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 26.2 | drt_violations best 12170 last 12170 rows 16 | before-window best 14890, window best 12170 | PROGRESS: drt_violations improved 18.3 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 26.6 | drt_violations best 391 last 391 rows 40 | before-window best 544, window best 391 | PROGRESS: drt_violations improved 28.1 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 17.4 | drt_violations best 1752 last 4912 rows 19 | before-window best 4425, window best 1752 | PROGRESS: drt_violations improved 60.4 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 43.6 | drt_violations best 11 last 11 rows 55 | before-window best 13, window best 11 | PROGRESS: drt_violations improved 15.4 % in window |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | pregrt_ff_hold | 6.4 | repair_Violations best 63242 last 63261 rows 23 | before-window best 384759, window best 63242 | PROGRESS: repair_Violations improved 83.6 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 18.4 | drt_violations best 9 last 9 rows 55 | before-window best 36, window best 9 | PROGRESS: drt_violations improved 75.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 20.0 | drt_violations best 33445 last 33445 rows 4 | before-window best 545016, window best 33445 | PROGRESS: drt_violations improved 93.9 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 16.4 | drt_violations best 81088 last 81088 rows 3 | before-window best 486708, window best 81088 | PROGRESS: drt_violations improved 83.3 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 26.2 | drt_violations best 427 last 428 rows 36 | before-window best 13859, window best 427 | PROGRESS: drt_violations improved 96.9 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 17.0 | drt_violations best 15952 last 15952 rows 7 | before-window best 380531, window best 15952 | PROGRESS: drt_violations improved 95.8 % in window |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-2823500 | col_h9_r1__t1 | pregrt_ff_hold | 6.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 17.2 | drt_violations best 401 last 401 rows 30 | before-window best 25575, window best 401 | PROGRESS: drt_violations improved 98.4 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 18.0 | drt_violations best 1435 last 5055 rows 18 | before-window best 11491, window best 1435 | PROGRESS: drt_violations improved 87.5 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 20.0 | drt_violations best 858 last 3220 rows 26 | before-window best 3028, window best 858 | PROGRESS: drt_violations improved 71.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvfef7c177-3709744 | col_h9_r2__t1 | pregrt_ff_hold | 3.3 | repair_Violations best 9907 last 9925 rows 31 | before-window best 411219, window best 9907 | PROGRESS: repair_Violations improved 97.6 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 18.5 | drt_violations best 439 last 439 rows 29 | before-window best 8561, window best 439 | PROGRESS: drt_violations improved 94.9 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 18.5 | drt_violations best 384 last 384 rows 51 | before-window best 510, window best 384 | PROGRESS: drt_violations improved 24.7 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 17.3 | drt_violations best 1176 last 2921 rows 18 | before-window best 40191, window best 1176 | PROGRESS: drt_violations improved 97.1 % in window |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 17.2 | drt_violations best 6 last 6 rows 45 | before-window best 51122, window best 6 | PROGRESS: drt_violations improved 100.0 % in window |  |
