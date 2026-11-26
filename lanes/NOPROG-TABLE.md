# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-26 05:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 6, 'GRT-LABEL': 3, 'YOUNG': 33, 'NO-DATA': 2, 'EXCLUDED': 3, 'KEEP': 1, 'PROGRESS': 19}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 10.3 | last meaningful line 8.3 h ago (33/35 lines) | NO-PROGRESS: no new non-iteration log line for 8.3 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 27.5 | drt_violations best 3665 last 5480 rows 22 | before-window best 3665, window best 5480 | NO-PROGRESS: drt_violations best 5480 vs 3665 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 7.1 | last meaningful line 6.3 h ago (700/700 lines) | NO-PROGRESS: no new non-iteration log line for 6.3 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 24.1 | repair_Viol best 968 last 968 rows 240 | before-window best 968, window best 968 | NO-PROGRESS: repair_Viol best 968 vs 968 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 40.1 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 10.2 | last meaningful line 6.5 h ago (33/34 lines) | NO-PROGRESS: no new non-iteration log line for 6.5 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-2823500 | col_h9_r1__t1 | 5_1_grt | 7.2 | grt rounds 2 overflow 5:130146 -> 10:3228 | GRT-LABEL: DESIGN-FAIL: overflow 3228 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 17.6 | grt rounds 9 overflow 20:2337 -> 25:2143 -> 30:1999 -> 35:1942 -> 40:2129 -> 45:2042 | GRT-LABEL: DESIGN-FAIL: overflow 3237 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-2530599 | col_h9_r1__t1 | 5_1_grt | 7.3 | grt rounds 3 overflow 5:129661 -> 10:3145 -> 15:2226 | GRT-LABEL: DESIGN-FAIL: overflow 3145 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-2708094 | dsdv_slice_c1x_C__t5 | 5_1_grt | 6.9 | last meaningful line 1.8 h ago (277/1286 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc10 | lecaf-hdm-whole-exact-cohorts | lecaf-hdm-whole-exact-cohorts | - | 4.1 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-svc_lo_dsdv_svc_rs_w__t1-1738997 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 3.8 | last meaningful line 3.0 h ago (626/626 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261125_200405_3323313-i3t-976868 | eco_20261125_200405_3323313-i3t | 5_2_route | 0.6 | last meaningful line 0.0 h ago (265/266 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_015555_2965752-i1-1101489 | eco_20261126_015555_2965752-i1 | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (295/514 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_033735_1990069-i1t-128004 | eco_20261126_033735_1990069-i1t | 5_2_route | 1.3 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_045746_1995760-i1t-1567307 | eco_20261126_045746_1995760-i1t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 5.8 | drt_violations best 14 last 14 rows 24 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261126_090542_621054-i1-3379796 | eco_20261126_090542_621054-i1 | 5_2_route | 1.1 | last meaningful line 0.0 h ago (264/264 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261126_033711_2888564-i2-136808 | eco_20261126_033711_2888564-i2 | 5_2_route | 1.3 | last meaningful line 0.1 h ago (279/280 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | 5_1_grt | 7.6 | last meaningful line 0.3 h ago (269/1275 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | 5_2_route | 7.9 | last meaningful line 0.3 h ago (276/277 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | 5_2_route | 7.6 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2325128 | col_h9_r1__t1 | 5_1_grt | 7.4 | last meaningful line 0.2 h ago (268/1275 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8aaf8508-3602152 | col_h9_r1__t1 | pregrt_ff_hold | 3.7 | repair_TNS best 63268.8 last 63268.8 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-3901907 | col_h9_r1__t1 | 5_1_grt | 7.0 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvfef7c177-3709744 | col_h9_r2__t1 | 5_1_grt | 4.6 | last meaningful line 0.0 h ago (2480/2511 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | 5_2_route | 7.1 | last meaningful line 0.3 h ago (275/276 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-4156698 | col_h9_r2__t1 | 5_2_route | 6.1 | last meaningful line 0.3 h ago (276/277 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | 5_2_route | 7.8 | drt_violations best 167283 last 167283 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfd79e8b6-2469832 | col_h9_r2__t1 | 5_2_route | 5.7 | last meaningful line 0.3 h ago (268/269 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-4056356 | dsdv_slice_c1x_C__t8 | 4_1_cts | 3.6 | last meaningful line 0.0 h ago (7114/7115 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t1-3555509 | ot_s81sl_leaf__t1 | 5_1_grt | 3.7 | last meaningful line 0.1 h ago (162/162 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-479268 | sle_su_l1 | 5_2_route | 6.9 | drt_violations best 346595 last 346595 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t29__cl2e5c855a-3827558 | slice_station__t29 | 5_2_route | 3.6 | last meaningful line 0.3 h ago (260/261 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t29__clc7772371-1992482 | slice_station__t29 | 5_2_route | 4.0 | drt_violations best 12448 last 12448 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__cl1ea9de02-813226 | slice_station__t40 | 5_2_route | 4.3 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 5_1_grt | 7.4 | repair_TNS best 96231.6 last 96231.6 rows 6 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_072708_1527702-i2t-914930 | eco_20261126_072708_1527702-i2t | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (154/154 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_091926_2909746-i1t-3764749 | eco_20261126_091926_2909746-i1t | 5_2_route | 3.6 | last meaningful line 0.5 h ago (287/288 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_110525_292982-i1-2906749 | eco_20261126_110525_292982-i1 | 5_2_route | 1.9 | last meaningful line 0.3 h ago (276/277 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_124723_1617778-i1-1533755 | eco_20261126_124723_1617778-i1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (153/153 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 8.7 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261125_050013_1448739-i3-4082278 | eco_20261125_050013_1448739-i3 | 5_2_route | 1.1 | last meaningful line 0.0 h ago (266/266 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | 5_2_route | 7.7 | drt_violations best 3 last 3 rows 45 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 23.4 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 23.4 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 23.4 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-454895 | col_h9_r1__t1 | pregrt_ff_hold | 5.2 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 42.2 | drt_violations best 200 last 204 rows 58 | before-window best 200, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_2_route | 11.1 | drt_violations best 4 last 4 rows 46 | before-window best 179686, window best 4 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 27.5 | drt_violations best 11774 last 11774 rows 17 | before-window best 14890, window best 11774 | PROGRESS: drt_violations improved 20.9 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 27.9 | drt_violations best 388 last 389 rows 42 | before-window best 448, window best 388 | PROGRESS: drt_violations improved 13.4 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 18.6 | drt_violations best 1752 last 3348 rows 21 | before-window best 2253, window best 1752 | PROGRESS: drt_violations improved 22.2 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 44.9 | drt_violations best 11 last 11 rows 55 | before-window best 13, window best 11 | PROGRESS: drt_violations improved 15.4 % in window |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | pregrt_ff_hold | 6.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 21.3 | drt_violations best 22898 last 22898 rows 5 | before-window best 545016, window best 22898 | PROGRESS: drt_violations improved 95.8 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 17.7 | drt_violations best 20637 last 20637 rows 4 | before-window best 486708, window best 20637 | PROGRESS: drt_violations improved 95.8 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 18.2 | drt_violations best 13403 last 13403 rows 9 | before-window best 380531, window best 13403 | PROGRESS: drt_violations improved 96.5 % in window |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2382304 | col_h9_r1__t1 | pregrt_ff_hold | 7.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 18.4 | drt_violations best 396 last 396 rows 33 | before-window best 4007, window best 396 | PROGRESS: drt_violations improved 90.1 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 19.2 | drt_violations best 1310 last 1310 rows 20 | before-window best 6723, window best 1310 | PROGRESS: drt_violations improved 80.5 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 21.2 | drt_violations best 858 last 1610 rows 27 | before-window best 1249, window best 858 | PROGRESS: drt_violations improved 31.3 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 32.1 | drt_violations best 390 last 408 rows 58 | before-window best 390, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 19.7 | drt_violations best 426 last 426 rows 32 | before-window best 5613, window best 426 | PROGRESS: drt_violations improved 92.4 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 19.8 | drt_violations best 384 last 384 rows 51 | before-window best 400, window best 384 | PROGRESS: drt_violations improved 4.0 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 18.5 | drt_violations best 1137 last 1137 rows 20 | before-window best 6446, window best 1137 | PROGRESS: drt_violations improved 82.4 % in window |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 18.5 | drt_violations best 5 last 5 rows 48 | before-window best 428, window best 5 | PROGRESS: drt_violations improved 98.8 % in window |  |
