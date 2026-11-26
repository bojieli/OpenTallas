# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-26 09:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 9, 'UNSIGNABLE': 1, 'GRT-LABEL': 5, 'NO-DATA': 5, 'YOUNG': 26, 'EXCLUDED': 3, 'KEEP': 1, 'PROGRESS': 20}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 14.3 | last meaningful line 12.3 h ago (33/36 lines) | NO-PROGRESS: no new non-iteration log line for 12.3 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc11 | dpkit-svc_lo_dsdv_svc_rs_w__t1-1738997 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 7.8 | last meaningful line 7.0 h ago (626/626 lines) | NO-PROGRESS: no new non-iteration log line for 7.0 h | REPORT-ONLY: lane-own kit (FAM-S81-SVC-OWN decides |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 31.5 | drt_violations best 3665 last 5105 rows 24 | before-window best 3665, window best 5105 | NO-PROGRESS: drt_violations best 5105 vs 3665 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 11.1 | last meaningful line 10.3 h ago (700/700 lines) | NO-PROGRESS: no new non-iteration log line for 10.3 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2325128 | col_h9_r1__t1 | 5_1_grt | 11.4 | grt rounds 7 overflow 10:3179 -> 15:2255 -> 20:2262 -> 25:2234 -> 30:1936 -> 35:1955 | UNSIGNABLE: GRT overflow flat: overflow 1936 at iteration 30 -> 1955 at iteration 35: flat f | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 23.8 | drt_violations best 377 last 377 rows 58 | before-window best 384, window best 377 | NO-PROGRESS: drt_violations best 377 vs 384 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 28.1 | repair_Viol best 968 last 968 rows 405 | before-window best 968, window best 968 | NO-PROGRESS: repair_Viol best 968 vs 968 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 44.1 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 14.2 | last meaningful line 10.5 h ago (33/35 lines) | NO-PROGRESS: no new non-iteration log line for 10.5 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | 5_2_route | 11.7 | drt_violations best 3 last 3 rows 48 | before-window best 3, window best 3 | NO-PROGRESS: drt_violations best 3 vs 3 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-2823500 | col_h9_r1__t1 | 5_1_grt | 11.2 | grt rounds 7 overflow 10:3228 -> 15:2332 -> 20:2387 -> 25:2108 -> 30:2029 -> 35:1940 | GRT-LABEL: DESIGN-FAIL: overflow 3228 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8aaf8508-3602152 | col_h9_r1__t1 | 5_1_grt | 7.7 | grt rounds 3 overflow 5:130266 -> 10:3229 -> 15:2333 | GRT-LABEL: DESIGN-FAIL: overflow 3229 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-3901907 | col_h9_r1__t1 | 5_1_grt | 11.0 | grt rounds 6 overflow 5:130096 -> 10:3228 -> 15:2328 -> 20:2341 -> 25:2179 -> 30:1984 | GRT-LABEL: DESIGN-FAIL: overflow 3228 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2382304 | col_h9_r1__t1 | 5_1_grt | 11.3 | grt rounds 6 overflow 5:131089 -> 10:3213 -> 15:2290 -> 20:2318 -> 25:2158 -> 30:1951 | GRT-LABEL: DESIGN-FAIL: overflow 3213 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-2530599 | col_h9_r1__t1 | 5_1_grt | 11.3 | grt rounds 7 overflow 10:3145 -> 15:2226 -> 20:2321 -> 25:2149 -> 30:1883 -> 35:1834 | GRT-LABEL: DESIGN-FAIL: overflow 3145 at round 10 > 1000 |  |
| epyc10 | lecaf-hdm-la52-base | lecaf-hdm-la52-base | - | 1.9 |  | NO-DATA: no log found |  |
| epyc10 | qchold_cone | qchold_cone | otrun4 | 0.0 | last meaningful line 0.0 h ago (5/5 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_033735_1990069-i1-820044 | eco_20261126_033735_1990069-i1 | 5_2_route | 1.9 | last meaningful line 0.1 h ago (279/280 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_045746_1995760-i1-4043582 | eco_20261126_045746_1995760-i1 | 5_1_grt | 0.5 | last meaningful line 0.3 h ago (297/369 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-coll_ft__cla4a25d77-2002732 | coll_ft | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (1396/1396 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_st_n3_turn-1858109 | hd_st_n3_turn | 3_4_place_resized | 0.1 | last meaningful line 0.0 h ago (83/83 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | lecq9r2c-832216391936 | lecq9r2c | gold.ys | 0.0 | last meaningful line 0.0 h ago (25830/25830 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261126_090542_621054-i2t-1127779 | eco_20261126_090542_621054-i2t | 5_2_route | 1.8 | drt_violations best 28961 last 28961 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | lecr2-hc3-d5fde-standalone-twins | lecr2-hc3-d5fde-standalone-twins | - | 0.4 |  | NO-DATA: no log found |  |
| epyc8 | lecr2-tw1-l2 | lecr2-tw1-l2 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | 5_1_grt | 10.7 | last meaningful line 0.0 h ago (2723/2727 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | 5_1_grt | 11.6 | last meaningful line 1.3 h ago (270/1292 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | 5_2_route | 11.9 | drt_violations best 107508 last 107508 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | 5_2_route | 11.6 | last meaningful line 0.5 h ago (286/287 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-352648 | col_h9_r2__t1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (4184/4184 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvfef7c177-3709744 | col_h9_r2__t1 | 5_2_route | 8.6 | drt_violations best 167856 last 167856 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | 5_2_route | 11.1 | drt_violations best 9734 last 9734 rows 5 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvb3f647ea-1347531 | col_h9_r2__t1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (3357/3357 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfd79e8b6-2469832 | col_h9_r2__t1 | 5_2_route | 9.7 | drt_violations best 173166 last 173166 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-4056356 | dsdv_slice_c1x_C__t8 | 4_1_cts | 7.6 | last meaningful line 0.2 h ago (7570/7570 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc9 | dpkit-gunit__t1-645727 | gunit__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.7023 last 0.7023 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slice_station__t38-739500 | slice_station__t38 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3042/3043 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-1469952-15965 | 1469952 | clk_freeze_post | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_072708_1527702-i2t-914930 | eco_20261126_072708_1527702-i2t | 5_2_route | 4.3 | drt_violations best 57268 last 57268 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_124723_1617778-i1-1533755 | eco_20261126_124723_1617778-i1 | 5_2_route | 4.2 | drt_violations best 54127 last 54127 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc9 | prd-eco_retry_1795711573796550375-i1t-740519 | eco_retry_1795711573796550375-i1t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (155/155 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-fin-2427528 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (70/70 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | 3_5_place_dp | 0.9 | last meaningful line 0.1 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 12.7 |  | NO-DATA: no log found |  |
| intel1 | otc-2895210-24702 | 2895210 | - | 0.8 |  | NO-DATA: no log found |  |
| intel2 | dpkit-hd_host_w-1217328 | hd_host_w | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3840/3840 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 27.4 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 27.4 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 27.4 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-454895 | col_h9_r1__t1 | 5_1_grt | 9.2 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 46.2 | drt_violations best 200 last 204 rows 58 | before-window best 200, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_2_route | 15.1 | drt_violations best 3 last 3 rows 56 | before-window best 30796, window best 3 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 31.5 | drt_violations best 11774 last 45275 rows 18 | before-window best 12170, window best 11774 | PROGRESS: drt_violations improved 3.3 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 31.9 | drt_violations best 387 last 387 rows 44 | before-window best 420, window best 387 | PROGRESS: drt_violations improved 7.9 % in window |  |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 9.8 | drt_violations best 7 last 28 rows 37 | before-window best 58, window best 7 | PROGRESS: drt_violations improved 87.9 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 48.9 | drt_violations best 9 last 9 rows 58 | before-window best 11, window best 9 | PROGRESS: drt_violations improved 18.2 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 25.3 | drt_violations best 9761 last 9761 rows 10 | before-window best 97668, window best 9761 | PROGRESS: drt_violations improved 90.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 21.7 | drt_violations best 431 last 431 rows 16 | before-window best 120549, window best 431 | PROGRESS: drt_violations improved 99.6 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 22.2 | drt_violations best 9056 last 9056 rows 12 | before-window best 17848, window best 9056 | PROGRESS: drt_violations improved 49.3 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 23.2 | drt_violations best 806 last 820 rows 30 | before-window best 1435, window best 806 | PROGRESS: drt_violations improved 43.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 25.2 | drt_violations best 858 last 3318 rows 34 | before-window best 995, window best 858 | PROGRESS: drt_violations improved 13.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 23.7 | drt_violations best 421 last 423 rows 44 | before-window best 477, window best 421 | PROGRESS: drt_violations improved 11.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvb3258867-556022 | col_h9_r2__t1 | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 4 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-4156698 | col_h9_r2__t1 | 5_2_route | 10.1 | drt_violations best 1072 last 1072 rows 11 | before-window best 158380, window best 1072 | PROGRESS: drt_violations improved 99.3 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | 5_2_route | 11.8 | drt_violations best 4800 last 4800 rows 10 | before-window best 167283, window best 4800 | PROGRESS: drt_violations improved 97.1 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfb42a1ad-350001 | col_h9_r2__t1 | 4_1_cts | 0.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-479268 | sle_su_l1 | 5_2_route | 10.9 | drt_violations best 14708 last 14708 rows 8 | before-window best 346595, window best 14708 | PROGRESS: drt_violations improved 95.8 % in window |  |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 5_1_grt | 11.4 | repair_TNS best 73642.4 last 73642.4 rows 8 | before-window best 75948.5, window best 73642.4 | PROGRESS: repair_TNS improved 3.0 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 22.5 | drt_violations best 774 last 802 rows 29 | before-window best 1176, window best 774 | PROGRESS: drt_violations improved 34.2 % in window |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 22.5 | drt_violations best 4 last 4 rows 50 | before-window best 6, window best 4 | PROGRESS: drt_violations improved 33.3 % in window |  |
