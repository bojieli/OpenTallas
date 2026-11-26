# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-26 04:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 6, 'GRT-LABEL': 1, 'YOUNG': 34, 'NO-DATA': 2, 'EXCLUDED': 3, 'KEEP': 1, 'PROGRESS': 24}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 9.5 | last meaningful line 7.5 h ago (33/35 lines) | NO-PROGRESS: no new non-iteration log line for 7.5 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | pregrt_ff_hold | 5.9 | repair_TNS best 35372.7 last 35372.7 rows 1 | before-window best 35372.7, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2325128 | col_h9_r1__t1 | pregrt_ff_hold | 6.6 | repair_TNS best 261.535 last 261.535 rows 1 | before-window best 261.535, window best 261.535 | NO-PROGRESS: repair_TNS best 261.535 vs 261.535 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2382304 | col_h9_r1__t1 | pregrt_ff_hold | 6.6 | repair_TNS best 15731.2 last 15731.2 rows 1 | before-window best 15731.2, window best 15731.2 | NO-PROGRESS: repair_TNS best 15731.2 vs 15731.2 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 23.4 | repair_Viol best 968 last 968 rows 208 | before-window best 968, window best 968 | NO-PROGRESS: repair_Viol best 968 vs 968 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 39.4 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 16.8 | grt rounds 9 overflow 20:2337 -> 25:2143 -> 30:1999 -> 35:1942 -> 40:2129 -> 45:2042 | GRT-LABEL: DESIGN-FAIL: overflow 3237 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-2708094 | dsdv_slice_c1x_C__t5 | 5_1_grt | 6.1 | last meaningful line 1.0 h ago (277/1284 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | lecaf-hdm-whole-exact-cohorts | lecaf-hdm-whole-exact-cohorts | - | 3.3 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-svc_lo_dsdv_svc_rs_w__t1-1738997 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 3.1 | last meaningful line 2.3 h ago (626/626 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-1997619 | sle_stm_v2 | generate_abstract | 8.6 | last meaningful line 0.2 h ago (31/31 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_2_route | 10.4 | drt_violations best 6 last 6 rows 42 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | prd-count-p1_tc-7345 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_033735_1990069-i1t-128004 | eco_20261126_033735_1990069-i1t | 5_1_grt | 0.6 | last meaningful line 0.3 h ago (295/505 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | so_603829_ff_89189 | so_603829_ff_89189 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (59/59 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | so_603829_tt_89189 | so_603829_tt_89189 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (59/59 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 5.0 | drt_violations best 14 last 14 rows 23 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261126_090542_621054-i1-3379796 | eco_20261126_090542_621054-i1 | 5_1_grt | 0.3 | last meaningful line 0.2 h ago (300/872 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261126_033711_2888564-i2-136808 | eco_20261126_033711_2888564-i2 | 5_1_grt | 0.5 | repair_Remaining best 359038 last 359038 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | 5_1_grt | 6.9 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | 5_2_route | 7.2 | last meaningful line 0.2 h ago (271/271 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | 5_1_grt | 6.8 | last meaningful line 0.0 h ago (2552/2571 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-2823500 | col_h9_r1__t1 | 5_1_grt | 6.5 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-2530599 | col_h9_r1__t1 | 5_1_grt | 6.6 | last meaningful line 0.2 h ago (268/1275 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvfef7c177-3709744 | col_h9_r2__t1 | 5_1_grt | 3.8 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | 5_2_route | 6.3 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-4156698 | col_h9_r2__t1 | 5_2_route | 5.4 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | 5_2_route | 7.0 | last meaningful line 0.5 h ago (280/281 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfd79e8b6-2469832 | col_h9_r2__t1 | 5_2_route | 4.9 | last meaningful line 0.1 h ago (263/263 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-4056356 | dsdv_slice_c1x_C__t8 | 4_1_cts | 2.8 | last meaningful line 0.2 h ago (43/43 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t1-3555509 | ot_s81sl_leaf__t1 | pregrt_ff_hold | 2.9 | repair_TNS best 683593 last 683593 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-479268 | sle_su_l1 | 5_2_route | 6.1 | drt_violations best 346595 last 346595 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t26-3959180 | slice_station__t26 | 5_2_route | 3.8 | drt_violations best 1281 last 1281 rows 2 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t29__cl2e5c855a-3827558 | slice_station__t29 | 5_2_route | 2.9 | last meaningful line 0.2 h ago (252/253 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t29__clc7772371-1992482 | slice_station__t29 | 5_2_route | 3.3 | drt_violations best 12448 last 12448 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__cl1ea9de02-813226 | slice_station__t40 | 5_2_route | 3.5 | last meaningful line 0.2 h ago (259/260 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 5_1_grt | 6.7 | repair_TNS best 102294 last 102294 rows 4 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc9 | prd-count-p1_bc-3266022 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_091926_2909746-i1t-3764749 | eco_20261126_091926_2909746-i1t | 5_2_route | 2.9 | last meaningful line 0.5 h ago (281/282 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_110525_292982-i1-2906749 | eco_20261126_110525_292982-i1 | 5_2_route | 1.1 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 7.9 |  | NO-DATA: no log found |  |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 9.5 | last meaningful line 5.8 h ago (33/34 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | 5_2_route | 7.0 | drt_violations best 3 last 3 rows 42 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 22.7 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 22.7 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 22.7 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-454895 | col_h9_r1__t1 | pregrt_ff_hold | 4.5 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 41.4 | drt_violations best 200 last 204 rows 58 | before-window best 200, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_2_route | 19.0 | drt_violations best 392 last 405 rows 34 | before-window best 276288, window best 392 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 26.7 | drt_violations best 3665 last 6082 rows 21 | before-window best 3792, window best 3665 | PROGRESS: drt_violations improved 3.3 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 26.7 | drt_violations best 12170 last 12170 rows 16 | before-window best 14890, window best 12170 | PROGRESS: drt_violations improved 18.3 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 27.1 | drt_violations best 391 last 391 rows 40 | before-window best 448, window best 391 | PROGRESS: drt_violations improved 12.7 % in window |  |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 6.3 | last meaningful line 5.5 h ago (700/700 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 17.9 | drt_violations best 1752 last 3686 rows 20 | before-window best 3225, window best 1752 | PROGRESS: drt_violations improved 45.7 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 44.1 | drt_violations best 11 last 11 rows 55 | before-window best 13, window best 11 | PROGRESS: drt_violations improved 15.4 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 18.9 | drt_violations best 9 last 9 rows 58 | before-window best 15, window best 9 | PROGRESS: drt_violations improved 40.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 20.5 | drt_violations best 22898 last 22898 rows 5 | before-window best 545016, window best 22898 | PROGRESS: drt_violations improved 95.8 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 16.9 | drt_violations best 81088 last 81088 rows 3 | before-window best 486708, window best 81088 | PROGRESS: drt_violations improved 83.3 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 26.7 | drt_violations best 427 last 427 rows 39 | before-window best 10626, window best 427 | PROGRESS: drt_violations improved 96.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 17.5 | drt_violations best 14907 last 14907 rows 8 | before-window best 380531, window best 14907 | PROGRESS: drt_violations improved 96.1 % in window |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8aaf8508-3602152 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.9 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-3901907 | col_h9_r1__t1 | pregrt_ff_hold | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 17.7 | drt_violations best 401 last 401 rows 31 | before-window best 6584, window best 401 | PROGRESS: drt_violations improved 93.9 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 18.5 | drt_violations best 1435 last 1789 rows 19 | before-window best 8266, window best 1435 | PROGRESS: drt_violations improved 82.6 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 20.5 | drt_violations best 858 last 3220 rows 26 | before-window best 1894, window best 858 | PROGRESS: drt_violations improved 54.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 31.4 | drt_violations best 390 last 408 rows 58 | before-window best 390, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 19.0 | drt_violations best 426 last 426 rows 30 | before-window best 6497, window best 426 | PROGRESS: drt_violations improved 93.4 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 19.0 | drt_violations best 384 last 384 rows 51 | before-window best 459, window best 384 | PROGRESS: drt_violations improved 16.3 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 17.8 | drt_violations best 1176 last 1487 rows 19 | before-window best 10102, window best 1176 | PROGRESS: drt_violations improved 88.4 % in window |  |
| intel1 | prd-eco_20261125_050013_1448739-i3-4082278 | eco_20261125_050013_1448739-i3 | 5_1_grt | 0.3 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 17.7 | drt_violations best 6 last 6 rows 45 | before-window best 36164, window best 6 | PROGRESS: drt_violations improved 100.0 % in window |  |
