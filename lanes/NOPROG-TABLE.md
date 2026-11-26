# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-26 08:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 7, 'GRT-LABEL': 5, 'NO-DATA': 5, 'YOUNG': 24, 'EXCLUDED': 3, 'KEEP': 1, 'PROGRESS': 19}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 13.3 | last meaningful line 11.3 h ago (33/35 lines) | NO-PROGRESS: no new non-iteration log line for 11.3 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc11 | dpkit-svc_lo_dsdv_svc_rs_w__t1-1738997 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 6.8 | last meaningful line 6.0 h ago (626/626 lines) | NO-PROGRESS: no new non-iteration log line for 6.0 h | REPORT-ONLY: lane-own kit (FAM-S81-SVC-OWN decides |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 30.5 | drt_violations best 3665 last 5106 rows 23 | before-window best 3665, window best 5106 | NO-PROGRESS: drt_violations best 5106 vs 3665 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 10.1 | last meaningful line 9.3 h ago (700/700 lines) | NO-PROGRESS: no new non-iteration log line for 9.3 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 27.1 | repair_Viol best 968 last 968 rows 364 | before-window best 968, window best 968 | NO-PROGRESS: repair_Viol best 968 vs 968 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 43.1 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 13.2 | last meaningful line 9.5 h ago (33/35 lines) | NO-PROGRESS: no new non-iteration log line for 9.5 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-2823500 | col_h9_r1__t1 | 5_1_grt | 10.2 | grt rounds 6 overflow 5:130146 -> 10:3228 -> 15:2332 -> 20:2387 -> 25:2108 -> 30:2029 | GRT-LABEL: DESIGN-FAIL: overflow 3228 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2325128 | col_h9_r1__t1 | 5_1_grt | 10.4 | grt rounds 6 overflow 5:130007 -> 10:3179 -> 15:2255 -> 20:2262 -> 25:2234 -> 30:1936 | GRT-LABEL: DESIGN-FAIL: overflow 3179 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-3901907 | col_h9_r1__t1 | 5_1_grt | 10.0 | grt rounds 5 overflow 5:130096 -> 10:3228 -> 15:2328 -> 20:2341 -> 25:2179 | GRT-LABEL: DESIGN-FAIL: overflow 3228 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2382304 | col_h9_r1__t1 | 5_1_grt | 10.3 | grt rounds 5 overflow 5:131089 -> 10:3213 -> 15:2290 -> 20:2318 -> 25:2158 | GRT-LABEL: DESIGN-FAIL: overflow 3213 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-2530599 | col_h9_r1__t1 | 5_1_grt | 10.3 | grt rounds 6 overflow 5:129661 -> 10:3145 -> 15:2226 -> 20:2321 -> 25:2149 -> 30:1883 | GRT-LABEL: DESIGN-FAIL: overflow 3145 at round 10 > 1000 |  |
| epyc10 | lecaf-hdm-la52-base | lecaf-hdm-la52-base | - | 0.9 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261126_033735_1990069-i1-820044 | eco_20261126_033735_1990069-i1 | 5_2_route | 0.9 | last meaningful line 0.0 h ago (80/80 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | so_3003352_ff_56989 | so_3003352_ff_56989 | generate_abstract | 0.5 | last meaningful line 0.3 h ago (33/33 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | so_3003352_tt_56989 | so_3003352_tt_56989 | generate_abstract | 0.5 | last meaningful line 0.3 h ago (33/33 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261126_090542_621054-i2t-1127779 | eco_20261126_090542_621054-i2t | 5_2_route | 0.8 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | 5_1_grt | 9.7 | repair_Remaining best 210843 last 210843 rows 192 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | 5_1_grt | 10.6 | last meaningful line 0.3 h ago (270/1277 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | 5_2_route | 10.9 | drt_violations best 107508 last 107508 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | 5_2_route | 10.6 | last meaningful line 0.5 h ago (282/283 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8aaf8508-3602152 | col_h9_r1__t1 | 5_1_grt | 6.7 | last meaningful line 0.0 h ago (153/153 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvfef7c177-3709744 | col_h9_r2__t1 | 5_2_route | 7.6 | last meaningful line 0.3 h ago (276/277 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | 5_2_route | 10.1 | drt_violations best 46145 last 46145 rows 2 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-4156698 | col_h9_r2__t1 | 5_2_route | 9.1 | drt_violations best 22496 last 22496 rows 3 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | 5_2_route | 10.8 | drt_violations best 5835 last 5835 rows 7 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfd79e8b6-2469832 | col_h9_r2__t1 | 5_2_route | 8.7 | drt_violations best 173166 last 173166 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-4056356 | dsdv_slice_c1x_C__t8 | 4_1_cts | 6.6 | last meaningful line 0.3 h ago (7521/7521 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t1-3555509 | ot_s81sl_leaf__t1 | postcts_gate_FF | 6.7 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-479268 | sle_su_l1 | 5_2_route | 9.9 | drt_violations best 60597 last 60597 rows 3 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_072708_1527702-i2t-914930 | eco_20261126_072708_1527702-i2t | 5_2_route | 3.3 | last meaningful line 0.3 h ago (284/285 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_091926_2909746-i1t-3764749 | eco_20261126_091926_2909746-i1t | 5_2_route | 6.6 | drt_violations best 119753 last 119753 rows 1 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_110525_292982-i1-2906749 | eco_20261126_110525_292982-i1 | 5_2_route | 4.9 | drt_violations best 56525 last 56525 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_124723_1617778-i1-1533755 | eco_20261126_124723_1617778-i1 | 5_2_route | 3.2 | last meaningful line 0.2 h ago (282/283 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_130006_3956471-i1-2427528 | eco_20261126_130006_3956471-i1 | 5_2_route | 3.0 | drt_violations best 1 last 1 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | so_967055_ff_66165 | so_967055_ff_66165 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc9 | so_967055_tt_66165 | so_967055_tt_66165 | signoff | 0.2 |  | NO-DATA: empty log |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 11.7 |  | NO-DATA: no log found |  |
| intel1 | otc-2382295-27501 | 2382295 | - | 2.6 |  | NO-DATA: no log found |  |
| intel1 | so_1658072_ff_638 | so_1658072_ff_638 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (35/35 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | so_1658072_tt_638 | so_1658072_tt_638 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (35/35 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 26.4 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 26.4 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 26.4 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-454895 | col_h9_r1__t1 | 5_1_grt | 8.2 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 45.2 | drt_violations best 200 last 204 rows 58 | before-window best 200, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_2_route | 14.1 | drt_violations best 3 last 3 rows 54 | before-window best 179686, window best 3 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc2 | prd-eco_20261126_045746_1995760-i1t-1567307 | eco_20261126_045746_1995760-i1t | 5_2_route | 3.0 | drt_violations best 0 last 0 rows 4 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 30.5 | drt_violations best 11774 last 45275 rows 18 | before-window best 12441, window best 11774 | PROGRESS: drt_violations improved 5.4 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 30.9 | drt_violations best 387 last 387 rows 44 | before-window best 421, window best 387 | PROGRESS: drt_violations improved 8.1 % in window |  |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 8.8 | drt_violations best 7 last 28 rows 36 | before-window best 320, window best 7 | PROGRESS: drt_violations improved 97.8 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 47.9 | drt_violations best 9 last 9 rows 58 | before-window best 11, window best 9 | PROGRESS: drt_violations improved 18.2 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 24.3 | drt_violations best 12349 last 12349 rows 9 | before-window best 97668, window best 12349 | PROGRESS: drt_violations improved 87.4 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 20.7 | drt_violations best 3970 last 3970 rows 10 | before-window best 120549, window best 3970 | PROGRESS: drt_violations improved 96.7 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 21.2 | drt_violations best 9056 last 9056 rows 12 | before-window best 27440, window best 9056 | PROGRESS: drt_violations improved 67.0 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 22.2 | drt_violations best 806 last 1280 rows 27 | before-window best 2346, window best 806 | PROGRESS: drt_violations improved 65.6 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 24.2 | drt_violations best 858 last 985 rows 32 | before-window best 1013, window best 858 | PROGRESS: drt_violations improved 15.3 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 35.1 | drt_violations best 382 last 382 rows 64 | before-window best 390, window best 382 | PROGRESS: drt_violations improved 2.1 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 22.7 | drt_violations best 421 last 424 rows 42 | before-window best 545, window best 421 | PROGRESS: drt_violations improved 22.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 22.8 | drt_violations best 377 last 377 rows 58 | before-window best 386, window best 377 | PROGRESS: drt_violations improved 2.3 % in window |  |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 5_1_grt | 10.4 | grt_hold_TNS best 79374.1 last 79374.1 rows 12 | before-window best 122094, window best 79374.1 | PROGRESS: grt_hold_TNS improved 35.0 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 21.5 | drt_violations best 774 last 1133 rows 27 | before-window best 1774, window best 774 | PROGRESS: drt_violations improved 56.4 % in window |  |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | 5_2_route | 10.7 | drt_violations best 3 last 3 rows 48 | before-window best 31, window best 3 | PROGRESS: drt_violations improved 90.3 % in window |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 21.5 | drt_violations best 4 last 4 rows 50 | before-window best 6, window best 4 | PROGRESS: drt_violations improved 33.3 % in window |  |
