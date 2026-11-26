# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-26 06:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 7, 'UNSIGNABLE': 3, 'GRT-LABEL': 4, 'NO-DATA': 5, 'YOUNG': 30, 'EXCLUDED': 3, 'KEEP': 1, 'PROGRESS': 20}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 11.5 | last meaningful line 9.5 h ago (33/35 lines) | NO-PROGRESS: no new non-iteration log line for 9.5 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 28.7 | drt_violations best 3665 last 5106 rows 23 | before-window best 3665, window best 5106 | NO-PROGRESS: drt_violations best 5106 vs 3665 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 8.3 | last meaningful line 7.5 h ago (700/700 lines) | NO-PROGRESS: no new non-iteration log line for 7.5 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-2823500 | col_h9_r1__t1 | 5_1_grt | 8.5 | grt rounds 4 overflow 5:130146 -> 10:3228 -> 15:2332 -> 20:2387 | UNSIGNABLE: GRT overflow flat: overflow 2332 at iteration 15 -> 2387 at iteration 20: flat f | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2325128 | col_h9_r1__t1 | 5_1_grt | 8.6 | grt rounds 4 overflow 5:130007 -> 10:3179 -> 15:2255 -> 20:2262 | UNSIGNABLE: GRT overflow flat: overflow 2255 at iteration 15 -> 2262 at iteration 20: flat f | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 18.8 | grt rounds 10 overflow 25:2143 -> 30:1999 -> 35:1942 -> 40:2129 -> 45:2042 -> 50:2028 | UNSIGNABLE: GRT overflow flat: overflow 2042 at iteration 45 -> 2028 at iteration 50: flat f | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 5_1_grt | 8.7 | repair_TNS best 89824.7 last 89824.7 rows 3 | before-window best 90520.4, window best 89824.7 | NO-PROGRESS: repair_TNS best 89824.7 vs 90520.4 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 25.4 | repair_Viol best 968 last 968 rows 291 | before-window best 968, window best 968 | NO-PROGRESS: repair_Viol best 968 vs 968 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 41.4 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 11.5 | last meaningful line 7.8 h ago (33/34 lines) | NO-PROGRESS: no new non-iteration log line for 7.8 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-2708094 | dsdv_slice_c1x_C__t5 | 5_1_grt | 8.1 | grt rounds 2 overflow 5:72678 -> 10:62292 | GRT-LABEL: DESIGN-FAIL: overflow 62292 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-3901907 | col_h9_r1__t1 | 5_1_grt | 8.3 | grt rounds 3 overflow 5:130096 -> 10:3228 -> 15:2328 | GRT-LABEL: DESIGN-FAIL: overflow 3228 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2382304 | col_h9_r1__t1 | 5_1_grt | 8.6 | grt rounds 3 overflow 5:131089 -> 10:3213 -> 15:2290 | GRT-LABEL: DESIGN-FAIL: overflow 3213 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-2530599 | col_h9_r1__t1 | 5_1_grt | 8.6 | grt rounds 5 overflow 5:129661 -> 10:3145 -> 15:2226 -> 20:2321 -> 25:2149 | GRT-LABEL: DESIGN-FAIL: overflow 3145 at round 10 > 1000 |  |
| epyc10 | lecaf-hdm-whole-exact-cohorts | lecaf-hdm-whole-exact-cohorts | - | 5.3 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-svc_lo_dsdv_svc_rs_w__t1-1738997 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 5.1 | last meaningful line 4.3 h ago (626/626 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261125_200405_3323313-i3-2880998 | eco_20261125_200405_3323313-i3 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_015555_2965752-i1-1101489 | eco_20261126_015555_2965752-i1 | 5_2_route | 1.7 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_033735_1990069-i1t-128004 | eco_20261126_033735_1990069-i1t | 5_2_route | 2.6 | drt_violations best 4617 last 4617 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_045746_1995760-i1t-1567307 | eco_20261126_045746_1995760-i1t | 5_2_route | 1.3 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepw_mus_C__t1-1684006 | dsdv_slice_lepw_mus_C__t1 | 3_1_place_gp_skip_io | 1.0 | overflow best 0.8601 last 0.8745 rows 21 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N_w-3212441 | hd_lep0N_w | 3_3_place_gp | 0.2 | overflow best 0.6377 last 0.6377 rows 12 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | otc-3234188-15425 | 3234188 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | prd-fin-3379796 | fin | 6_report | 0.1 | last meaningful line 0.1 h ago (68/68 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261126_033711_2888564-i3t-2010921 | eco_20261126_033711_2888564-i3t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | 5_1_grt | 7.9 | last meaningful line 0.1 h ago (166/166 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | 5_1_grt | 8.9 | last meaningful line 1.5 h ago (269/1291 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | 5_2_route | 9.2 | last meaningful line 0.5 h ago (282/283 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | 5_2_route | 8.8 | last meaningful line 0.5 h ago (276/277 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8aaf8508-3602152 | col_h9_r1__t1 | pregrt_ff_hold | 4.9 | repair_TNS best 63268.8 last 63268.8 rows 1 | YOUNG: evidence 1.5 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvfef7c177-3709744 | col_h9_r2__t1 | 5_2_route | 5.8 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | 5_2_route | 8.3 | drt_violations best 185285 last 185285 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-4156698 | col_h9_r2__t1 | 5_2_route | 7.4 | drt_violations best 158380 last 158380 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | 5_2_route | 9.0 | drt_violations best 167283 last 167283 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfd79e8b6-2469832 | col_h9_r2__t1 | 5_2_route | 6.9 | last meaningful line 0.5 h ago (274/275 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-4056356 | dsdv_slice_c1x_C__t8 | 4_1_cts | 4.8 | last meaningful line 0.0 h ago (7386/7386 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-479268 | sle_su_l1 | 5_2_route | 8.1 | drt_violations best 346595 last 346595 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t29__cl2e5c855a-3827558 | slice_station__t29 | 5_2_route | 4.9 | drt_violations best 25203 last 25203 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t29__clc7772371-1992482 | slice_station__t29 | 6_report | 5.3 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__cl1ea9de02-813226 | slice_station__t40 | 5_2_route | 5.5 | drt_violations best 20952 last 20952 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_072708_1527702-i2t-914930 | eco_20261126_072708_1527702-i2t | 5_2_route | 1.6 | last meaningful line 0.3 h ago (268/269 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_091926_2909746-i1t-3764749 | eco_20261126_091926_2909746-i1t | 5_2_route | 4.9 | drt_violations best 119753 last 119753 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_110525_292982-i1-2906749 | eco_20261126_110525_292982-i1 | 5_2_route | 3.1 | last meaningful line 0.5 h ago (284/285 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_124723_1617778-i1-1533755 | eco_20261126_124723_1617778-i1 | 5_2_route | 1.4 | last meaningful line 0.0 h ago (267/267 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_130006_3956471-i1-2427528 | eco_20261126_130006_3956471-i1 | 5_2_route | 1.2 | last meaningful line 0.1 h ago (239/240 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 9.9 |  | NO-DATA: no log found |  |
| intel1 | otc-2382295-27501 | 2382295 | - | 0.9 |  | NO-DATA: no log found |  |
| intel1 | otc-2383864-12042 | 2383864 | - | 0.9 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261125_050013_1448739-i3-4082278 | eco_20261125_050013_1448739-i3 | 5_2_route | 2.3 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 24.7 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 24.7 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 24.7 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-454895 | col_h9_r1__t1 | 5_1_grt | 6.5 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 43.4 | drt_violations best 200 last 204 rows 58 | before-window best 200, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_2_route | 12.4 | drt_violations best 3 last 3 rows 52 | before-window best 179686, window best 3 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 28.7 | drt_violations best 11774 last 45275 rows 18 | before-window best 13518, window best 11774 | PROGRESS: drt_violations improved 12.9 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 29.1 | drt_violations best 387 last 387 rows 43 | before-window best 446, window best 387 | PROGRESS: drt_violations improved 13.2 % in window |  |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 7.0 | drt_violations best 7 last 7 rows 31 | before-window best 11483, window best 7 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 19.9 | drt_violations best 1752 last 3225 rows 22 | before-window best 1886, window best 1752 | PROGRESS: drt_violations improved 7.1 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 46.1 | drt_violations best 9 last 9 rows 58 | before-window best 11, window best 9 | PROGRESS: drt_violations improved 18.2 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 22.5 | drt_violations best 15827 last 15827 rows 7 | before-window best 147781, window best 15827 | PROGRESS: drt_violations improved 89.3 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 18.9 | drt_violations best 12352 last 12352 rows 5 | before-window best 486708, window best 12352 | PROGRESS: drt_violations improved 97.5 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 19.5 | drt_violations best 12365 last 12365 rows 10 | before-window best 103874, window best 12365 | PROGRESS: drt_violations improved 88.1 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 19.7 | drt_violations best 396 last 396 rows 41 | before-window best 1551, window best 396 | PROGRESS: drt_violations improved 74.5 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 20.5 | drt_violations best 838 last 838 rows 23 | before-window best 5161, window best 838 | PROGRESS: drt_violations improved 83.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 22.5 | drt_violations best 858 last 1028 rows 29 | before-window best 1022, window best 858 | PROGRESS: drt_violations improved 16.0 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 33.4 | drt_violations best 390 last 408 rows 58 | before-window best 390, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 21.0 | drt_violations best 422 last 424 rows 37 | before-window best 3932, window best 422 | PROGRESS: drt_violations improved 89.3 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 21.0 | drt_violations best 377 last 377 rows 58 | before-window best 391, window best 377 | PROGRESS: drt_violations improved 3.6 % in window |  |
| epyc9 | dpkit-ot_s81sl_leaf__t1-3555509 | ot_s81sl_leaf__t1 | 5_1_grt | 4.9 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 19.8 | drt_violations best 829 last 829 rows 23 | before-window best 4786, window best 829 | PROGRESS: drt_violations improved 82.7 % in window |  |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | 5_2_route | 9.0 | drt_violations best 3 last 3 rows 45 | before-window best 994, window best 3 | PROGRESS: drt_violations improved 99.7 % in window |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 19.7 | drt_violations best 5 last 5 rows 48 | before-window best 10, window best 5 | PROGRESS: drt_violations improved 50.0 % in window |  |
