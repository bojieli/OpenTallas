# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-26 08:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 8, 'GRT-LABEL': 6, 'NO-DATA': 5, 'YOUNG': 19, 'EXCLUDED': 3, 'KEEP': 1, 'PROGRESS': 19}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 13.8 | last meaningful line 11.8 h ago (33/36 lines) | NO-PROGRESS: no new non-iteration log line for 11.8 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc11 | dpkit-svc_lo_dsdv_svc_rs_w__t1-1738997 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 7.3 | last meaningful line 6.5 h ago (626/626 lines) | NO-PROGRESS: no new non-iteration log line for 6.5 h | REPORT-ONLY: lane-own kit (FAM-S81-SVC-OWN decides |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 31.0 | drt_violations best 3665 last 5106 rows 23 | before-window best 3665, window best 5106 | NO-PROGRESS: drt_violations best 5106 vs 3665 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 10.6 | last meaningful line 9.8 h ago (700/700 lines) | NO-PROGRESS: no new non-iteration log line for 9.8 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 23.3 | drt_violations best 377 last 377 rows 58 | before-window best 384, window best 377 | NO-PROGRESS: drt_violations best 377 vs 384 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 27.6 | repair_Viol best 968 last 968 rows 385 | before-window best 968, window best 968 | NO-PROGRESS: repair_Viol best 968 vs 968 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 43.6 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 13.7 | last meaningful line 10.0 h ago (33/35 lines) | NO-PROGRESS: no new non-iteration log line for 10.0 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-2823500 | col_h9_r1__t1 | 5_1_grt | 10.7 | grt rounds 6 overflow 5:130146 -> 10:3228 -> 15:2332 -> 20:2387 -> 25:2108 -> 30:2029 | GRT-LABEL: DESIGN-FAIL: overflow 3228 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2325128 | col_h9_r1__t1 | 5_1_grt | 10.9 | grt rounds 6 overflow 5:130007 -> 10:3179 -> 15:2255 -> 20:2262 -> 25:2234 -> 30:1936 | GRT-LABEL: DESIGN-FAIL: overflow 3179 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8aaf8508-3602152 | col_h9_r1__t1 | 5_1_grt | 7.2 | grt rounds 2 overflow 5:130266 -> 10:3229 | GRT-LABEL: DESIGN-FAIL: overflow 3229 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-3901907 | col_h9_r1__t1 | 5_1_grt | 10.5 | grt rounds 6 overflow 5:130096 -> 10:3228 -> 15:2328 -> 20:2341 -> 25:2179 -> 30:1984 | GRT-LABEL: DESIGN-FAIL: overflow 3228 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2382304 | col_h9_r1__t1 | 5_1_grt | 10.8 | grt rounds 6 overflow 5:131089 -> 10:3213 -> 15:2290 -> 20:2318 -> 25:2158 -> 30:1951 | GRT-LABEL: DESIGN-FAIL: overflow 3213 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-2530599 | col_h9_r1__t1 | 5_1_grt | 10.8 | grt rounds 7 overflow 10:3145 -> 15:2226 -> 20:2321 -> 25:2149 -> 30:1883 -> 35:1834 | GRT-LABEL: DESIGN-FAIL: overflow 3145 at round 10 > 1000 |  |
| epyc10 | lecaf-hdm-la52-base | lecaf-hdm-la52-base | - | 1.4 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261126_033735_1990069-i1-820044 | eco_20261126_033735_1990069-i1 | 5_2_route | 1.4 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_045746_1995760-i1-4043582 | eco_20261126_045746_1995760-i1 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | lecq9r2b-85bb03258568 | lecq9r2b-85bb03258568 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261126_090542_621054-i2t-1127779 | eco_20261126_090542_621054-i2t | 5_2_route | 1.3 | last meaningful line 0.1 h ago (280/281 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-col-h10-r0-p1--t1--cl911743eb-grt-3077143 | col-h10-r0-p1--t1--cl911743eb-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | 5_1_grt | 11.1 | last meaningful line 0.8 h ago (270/1286 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | 5_2_route | 11.4 | drt_violations best 107508 last 107508 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | 5_2_route | 11.1 | last meaningful line 0.5 h ago (284/285 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvfef7c177-3709744 | col_h9_r2__t1 | 5_2_route | 8.1 | last meaningful line 0.3 h ago (280/281 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 6_report | 35.6 | last meaningful line 0.0 h ago (80/80 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | 5_2_route | 10.6 | drt_violations best 30207 last 30207 rows 3 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-4156698 | col_h9_r2__t1 | 5_2_route | 9.6 | drt_violations best 3187 last 3187 rows 6 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfd79e8b6-2469832 | col_h9_r2__t1 | 5_2_route | 9.2 | drt_violations best 173166 last 173166 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-4056356 | dsdv_slice_c1x_C__t8 | 4_1_cts | 7.1 | last meaningful line 0.3 h ago (7548/7548 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc9 | otc-2238112-23469 | 2238112 | signoff | 0.4 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_072708_1527702-i2t-914930 | eco_20261126_072708_1527702-i2t | 5_2_route | 3.8 | drt_violations best 57268 last 57268 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_091926_2909746-i1t-3764749 | eco_20261126_091926_2909746-i1t | 5_2_route | 7.1 | drt_violations best 119753 last 119753 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_110525_292982-i1-2906749 | eco_20261126_110525_292982-i1 | 5_2_route | 5.4 | drt_violations best 56525 last 56525 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_124723_1617778-i1-1533755 | eco_20261126_124723_1617778-i1 | 5_2_route | 3.7 | drt_violations best 54127 last 54127 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_130006_3956471-i1-2427528 | eco_20261126_130006_3956471-i1 | 5_2_route | 3.5 | drt_violations best 1 last 1 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | 3_3_place_gp | 0.4 | overflow best 0.3451 last 0.3451 rows 3 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 12.2 |  | NO-DATA: no log found |  |
| intel1 | otc-2895210-24702 | 2895210 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 26.9 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 26.9 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 26.9 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-454895 | col_h9_r1__t1 | 5_1_grt | 8.7 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 45.7 | drt_violations best 200 last 204 rows 58 | before-window best 200, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_2_route | 14.6 | drt_violations best 3 last 3 rows 54 | before-window best 46175, window best 3 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 31.0 | drt_violations best 11774 last 45275 rows 18 | before-window best 12441, window best 11774 | PROGRESS: drt_violations improved 5.4 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 31.4 | drt_violations best 387 last 387 rows 44 | before-window best 421, window best 387 | PROGRESS: drt_violations improved 8.1 % in window |  |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 9.3 | drt_violations best 7 last 28 rows 36 | before-window best 95, window best 7 | PROGRESS: drt_violations improved 92.6 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 48.4 | drt_violations best 9 last 9 rows 58 | before-window best 11, window best 9 | PROGRESS: drt_violations improved 18.2 % in window |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | 5_1_grt | 10.2 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 24.8 | drt_violations best 12349 last 12349 rows 9 | before-window best 97668, window best 12349 | PROGRESS: drt_violations improved 87.4 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 21.2 | drt_violations best 1169 last 1169 rows 12 | before-window best 120549, window best 1169 | PROGRESS: drt_violations improved 99.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 21.7 | drt_violations best 9056 last 9056 rows 12 | before-window best 20574, window best 9056 | PROGRESS: drt_violations improved 56.0 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 22.7 | drt_violations best 806 last 820 rows 29 | before-window best 1822, window best 806 | PROGRESS: drt_violations improved 55.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 24.7 | drt_violations best 858 last 3318 rows 34 | before-window best 995, window best 858 | PROGRESS: drt_violations improved 13.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 23.2 | drt_violations best 421 last 423 rows 44 | before-window best 477, window best 421 | PROGRESS: drt_violations improved 11.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | 5_2_route | 11.3 | drt_violations best 5290 last 5290 rows 9 | before-window best 167283, window best 5290 | PROGRESS: drt_violations improved 96.8 % in window |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-479268 | sle_su_l1 | 5_2_route | 10.4 | drt_violations best 17398 last 17398 rows 5 | before-window best 346595, window best 17398 | PROGRESS: drt_violations improved 95.0 % in window |  |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 5_1_grt | 10.9 | repair_TNS best 76352.2 last 76352.2 rows 10 | before-window best 79374.1, window best 76352.2 | PROGRESS: repair_TNS improved 3.8 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 22.0 | drt_violations best 774 last 835 rows 28 | before-window best 1467, window best 774 | PROGRESS: drt_violations improved 47.2 % in window |  |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | 5_2_route | 11.2 | drt_violations best 3 last 3 rows 48 | before-window best 4, window best 3 | PROGRESS: drt_violations improved 25.0 % in window |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 22.0 | drt_violations best 4 last 4 rows 50 | before-window best 6, window best 4 | PROGRESS: drt_violations improved 33.3 % in window |  |
