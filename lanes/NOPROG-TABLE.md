# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-26 05:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 5, 'UNSIGNABLE': 1, 'GRT-LABEL': 3, 'YOUNG': 30, 'NO-DATA': 3, 'EXCLUDED': 3, 'KEEP': 1, 'PROGRESS': 23}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 10.5 | last meaningful line 8.5 h ago (33/35 lines) | NO-PROGRESS: no new non-iteration log line for 8.5 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 7.3 | last meaningful line 6.5 h ago (700/700 lines) | NO-PROGRESS: no new non-iteration log line for 6.5 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-2530599 | col_h9_r1__t1 | 5_1_grt | 7.6 | grt rounds 4 overflow 5:129661 -> 10:3145 -> 15:2226 -> 20:2321 | UNSIGNABLE: GRT overflow flat: overflow 2226 at iteration 15 -> 2321 at iteration 20: flat f | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 24.4 | repair_Viol best 968 last 968 rows 251 | before-window best 968, window best 968 | NO-PROGRESS: repair_Viol best 968 vs 968 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 40.4 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 10.5 | last meaningful line 6.8 h ago (33/34 lines) | NO-PROGRESS: no new non-iteration log line for 6.8 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-2823500 | col_h9_r1__t1 | 5_1_grt | 7.5 | grt rounds 3 overflow 5:130146 -> 10:3228 -> 15:2332 | GRT-LABEL: DESIGN-FAIL: overflow 3228 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2325128 | col_h9_r1__t1 | 5_1_grt | 7.6 | grt rounds 2 overflow 5:130007 -> 10:3179 | GRT-LABEL: DESIGN-FAIL: overflow 3179 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 17.8 | grt rounds 9 overflow 20:2337 -> 25:2143 -> 30:1999 -> 35:1942 -> 40:2129 -> 45:2042 | GRT-LABEL: DESIGN-FAIL: overflow 3237 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-2708094 | dsdv_slice_c1x_C__t5 | 5_1_grt | 7.1 | last meaningful line 2.0 h ago (277/1286 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc10 | lecaf-hdm-whole-exact-cohorts | lecaf-hdm-whole-exact-cohorts | - | 4.3 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-svc_lo_dsdv_svc_rs_w__t1-1738997 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 4.1 | last meaningful line 3.3 h ago (626/626 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261125_200405_3323313-i3t-976868 | eco_20261125_200405_3323313-i3t | 5_2_route | 0.8 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_015555_2965752-i1-1101489 | eco_20261126_015555_2965752-i1 | 5_1_grt | 0.7 | last meaningful line 0.4 h ago (295/554 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_033735_1990069-i1t-128004 | eco_20261126_033735_1990069-i1t | 5_2_route | 1.6 | last meaningful line 0.1 h ago (277/278 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 6.0 | drt_violations best 14 last 31 rows 26 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261126_090542_621054-i1-3379796 | eco_20261126_090542_621054-i1 | 5_2_route | 1.3 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | prd-count-p1_tc-136808 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | 5_1_grt | 7.9 | last meaningful line 0.5 h ago (269/1279 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | 5_2_route | 8.2 | last meaningful line 0.5 h ago (276/277 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | 5_2_route | 7.8 | last meaningful line 0.1 h ago (150/150 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8aaf8508-3602152 | col_h9_r1__t1 | pregrt_ff_hold | 3.9 | repair_TNS best 63268.8 last 63268.8 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-3901907 | col_h9_r1__t1 | 5_1_grt | 7.3 | last meaningful line 0.0 h ago (155/155 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2382304 | col_h9_r1__t1 | 5_1_grt | 7.6 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvfef7c177-3709744 | col_h9_r2__t1 | postcts_gate_FF | 4.8 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | 5_2_route | 7.3 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-4156698 | col_h9_r2__t1 | 5_2_route | 6.4 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | 5_2_route | 8.0 | drt_violations best 167283 last 167283 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfd79e8b6-2469832 | col_h9_r2__t1 | 5_2_route | 5.9 | last meaningful line 0.5 h ago (268/269 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-4056356 | dsdv_slice_c1x_C__t8 | 4_1_cts | 3.8 | last meaningful line 0.0 h ago (7226/7226 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t1-3555509 | ot_s81sl_leaf__t1 | 5_1_grt | 3.9 | last meaningful line 0.0 h ago (271/272 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-479268 | sle_su_l1 | 5_2_route | 7.1 | drt_violations best 346595 last 346595 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t29__cl2e5c855a-3827558 | slice_station__t29 | 5_2_route | 3.9 | drt_violations best 25203 last 25203 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t29__clc7772371-1992482 | slice_station__t29 | 5_2_route | 4.3 | drt_violations best 12448 last 12448 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__cl1ea9de02-813226 | slice_station__t40 | 5_2_route | 4.5 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 5_1_grt | 7.7 | repair_TNS best 94359.5 last 94359.5 rows 11 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_091926_2909746-i1t-3764749 | eco_20261126_091926_2909746-i1t | 5_2_route | 3.9 | last meaningful line 0.2 h ago (289/290 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_110525_292982-i1-2906749 | eco_20261126_110525_292982-i1 | 5_2_route | 2.1 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_124723_1617778-i1-1533755 | eco_20261126_124723_1617778-i1 | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (159/159 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 8.9 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261125_050013_1448739-i3-4082278 | eco_20261125_050013_1448739-i3 | 5_2_route | 1.3 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | reverent_neumann | reverent_neumann | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 23.7 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 23.7 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 23.7 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-454895 | col_h9_r1__t1 | pregrt_ff_hold | 5.5 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 42.4 | drt_violations best 200 last 204 rows 58 | before-window best 200, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_2_route | 11.4 | drt_violations best 3 last 3 rows 50 | before-window best 179686, window best 3 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc2 | prd-eco_20261126_045746_1995760-i1t-1567307 | eco_20261126_045746_1995760-i1t | 5_1_grt | 0.3 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 27.7 | drt_violations best 3665 last 5480 rows 22 | before-window best 3665, window best 5480 | PROGRESS: drt_violations: falling inside the active iteration (5480 -> 5202) |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 27.7 | drt_violations best 11774 last 45275 rows 18 | before-window best 13518, window best 11774 | PROGRESS: drt_violations improved 12.9 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 28.1 | drt_violations best 388 last 389 rows 42 | before-window best 448, window best 388 | PROGRESS: drt_violations improved 13.4 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 18.9 | drt_violations best 1752 last 3348 rows 21 | before-window best 2253, window best 1752 | PROGRESS: drt_violations improved 22.2 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 45.1 | drt_violations best 11 last 11 rows 55 | before-window best 13, window best 11 | PROGRESS: drt_violations improved 15.4 % in window |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | pregrt_ff_hold | 6.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 21.5 | drt_violations best 18010 last 18010 rows 6 | before-window best 545016, window best 18010 | PROGRESS: drt_violations improved 96.7 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 17.9 | drt_violations best 20637 last 20637 rows 4 | before-window best 486708, window best 20637 | PROGRESS: drt_violations improved 95.8 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 18.5 | drt_violations best 13403 last 13403 rows 9 | before-window best 380531, window best 13403 | PROGRESS: drt_violations improved 96.5 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 18.7 | drt_violations best 396 last 396 rows 36 | before-window best 3768, window best 396 | PROGRESS: drt_violations improved 89.5 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 19.5 | drt_violations best 1310 last 1310 rows 20 | before-window best 6475, window best 1310 | PROGRESS: drt_violations improved 79.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 21.5 | drt_violations best 858 last 1610 rows 27 | before-window best 1249, window best 858 | PROGRESS: drt_violations improved 31.3 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 32.4 | drt_violations best 390 last 408 rows 58 | before-window best 390, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 20.0 | drt_violations best 422 last 422 rows 33 | before-window best 5417, window best 422 | PROGRESS: drt_violations improved 92.2 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 20.0 | drt_violations best 377 last 377 rows 53 | before-window best 399, window best 377 | PROGRESS: drt_violations improved 5.5 % in window |  |
| epyc9 | prd-eco_20261126_072708_1527702-i2t-914930 | eco_20261126_072708_1527702-i2t | 5_1_grt | 0.6 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc9 | prd-eco_20261126_130006_3956471-i1-2427528 | eco_20261126_130006_3956471-i1 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 18.8 | drt_violations best 1037 last 1037 rows 21 | before-window best 6143, window best 1037 | PROGRESS: drt_violations improved 83.1 % in window |  |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | 5_2_route | 8.0 | drt_violations best 3 last 3 rows 45 | before-window best 51310, window best 3 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 18.7 | drt_violations best 5 last 5 rows 48 | before-window best 95, window best 5 | PROGRESS: drt_violations improved 94.7 % in window |  |
