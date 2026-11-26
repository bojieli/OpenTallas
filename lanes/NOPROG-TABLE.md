# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-26 09:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 11, 'UNSIGNABLE': 2, 'NO-DATA': 4, 'YOUNG': 24, 'KEEP': 1, 'PROGRESS': 19}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 14.5 | last meaningful line 12.5 h ago (33/36 lines) | NO-PROGRESS: no new non-iteration log line for 12.5 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc11 | dpkit-svc_lo_dsdv_svc_rs_w__t1-1738997 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 8.1 | last meaningful line 7.3 h ago (626/626 lines) | NO-PROGRESS: no new non-iteration log line for 7.3 h | REPORT-ONLY: lane-own kit (FAM-S81-SVC-OWN decides |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 31.7 | drt_violations best 3665 last 5105 rows 24 | before-window best 3665, window best 5105 | NO-PROGRESS: drt_violations best 5105 vs 3665 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 32.1 | drt_violations best 387 last 387 rows 44 | before-window best 394, window best 387 | NO-PROGRESS: drt_violations best 387 vs 394 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 11.3 | last meaningful line 10.5 h ago (700/700 lines) | NO-PROGRESS: no new non-iteration log line for 10.5 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8aaf8508-3602152 | col_h9_r1__t1 | 5_1_grt | 7.9 | grt rounds 4 overflow 5:130266 -> 10:3229 -> 15:2333 -> 20:2377 | UNSIGNABLE: GRT overflow flat: overflow 2333 at iteration 15 -> 2377 at iteration 20: flat f | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 24.0 | drt_violations best 377 last 377 rows 58 | before-window best 384, window best 377 | NO-PROGRESS: drt_violations best 377 vs 384 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-4056356 | dsdv_slice_c1x_C__t8 | tt_setup_repair | 7.8 | repair_Remaining best 425185 last 425185 rows 175 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -436.65 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 5_1_grt | 11.7 | repair_TNS best 72585.9 last 72585.9 rows 1 | before-window best 72585.9, window best 72585.9 | NO-PROGRESS: repair_TNS best 72585.9 vs 72585.9 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 28.4 | repair_Viol best 968 last 968 rows 416 | before-window best 968, window best 968 | NO-PROGRESS: repair_Viol best 968 vs 968 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 44.4 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 14.5 | last meaningful line 10.8 h ago (33/35 lines) | NO-PROGRESS: no new non-iteration log line for 10.8 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | 5_2_route | 12.0 | drt_violations best 3 last 3 rows 48 | before-window best 3, window best 3 | NO-PROGRESS: drt_violations best 3 vs 3 before window: < 2 % in 6 h | CANCELLED |
| epyc10 | lecaf-hdm-la52-base | lecaf-hdm-la52-base | - | 2.2 |  | NO-DATA: no log found |  |
| epyc12 | otc-3276374-19844 | 3276374 | ot_bind_native_c2c8fa68db0e1061157e772a | 0.0 | last meaningful line -0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_033735_1990069-i1-820044 | eco_20261126_033735_1990069-i1 | 5_2_route | 2.1 | drt_violations best 45 last 45 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_045746_1995760-i1-4043582 | eco_20261126_045746_1995760-i1 | 5_1_grt | 0.8 | last meaningful line 0.5 h ago (297/442 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-coll_ft__cla4a25d77-2472612 | coll_ft | 3_3_place_gp | 0.1 | overflow best 0.3617 last 0.3617 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | lecr2-hc3-d5fde-standalone-twins | lecr2-hc3-d5fde-standalone-twins | - | 0.7 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | tt_setup_repair_grt | 10.9 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | 5_1_grt | 11.9 | last meaningful line 0.2 h ago (1319/1368 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-2052684 | col_h9_r0_p4__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3077/3077 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | 5_2_route | 12.2 | drt_violations best 107508 last 107508 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | 5_2_route | 11.8 | last meaningful line 0.5 h ago (288/289 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-1637829 | col_h9_r1__t1 | 4_1_cts | 0.2 | repair_Violations best 8 last 163 rows 21 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvf0f1ccb2-2216088 | col_h9_r1__t1 | 4_1_cts | 0.1 | repair_Violations best 495 last 495 rows 15 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvfef7c177-3709744 | col_h9_r2__t1 | 5_2_route | 8.8 | drt_violations best 167856 last 167856 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | 5_2_route | 11.3 | drt_violations best 8936 last 8936 rows 6 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvb3258867-556022 | col_h9_r2__t1 | 4_2_tapbal_grt | 0.5 | last meaningful line 0.0 h ago (61/63 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfd79e8b6-2469832 | col_h9_r2__t1 | 5_2_route | 9.9 | drt_violations best 173166 last 173166 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc9 | dpkit-gunit__t1-645727 | gunit__t1 | 3_4_place_resized | 0.5 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t24__cleece78ec-2317934 | slice_station__t24 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (1103/1103 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t38-739500 | slice_station__t38 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3115/3115 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_072708_1527702-i2t-914930 | eco_20261126_072708_1527702-i2t | 5_2_route | 4.6 | drt_violations best 57268 last 57268 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_124723_1617778-i1-1533755 | eco_20261126_124723_1617778-i1 | 5_2_route | 4.4 | drt_violations best 54127 last 54127 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc9 | prd-fin-2906749 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | so_2103877_ff_26587 | so_2103877_ff_26587 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | so_2103877_tt_26587 | so_2103877_tt_26587 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (5755/5756 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 12.9 |  | NO-DATA: no log found |  |
| intel1 | otc-2895210-24702 | 2895210 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-454895 | col_h9_r1__t1 | 5_1_grt | 9.5 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_2_route | 15.4 | drt_violations best 3 last 3 rows 56 | before-window best 1442, window best 3 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 31.7 | drt_violations best 11774 last 20077 rows 19 | before-window best 12170, window best 11774 | PROGRESS: drt_violations improved 3.3 % in window |  |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 10.0 | drt_violations best 7 last 28 rows 37 | before-window best 56, window best 7 | PROGRESS: drt_violations improved 87.5 % in window |  |
| epyc7 | prd-eco_20261126_090542_621054-i2t-1127779 | eco_20261126_090542_621054-i2t | 5_2_route | 2.0 | drt_violations best 0 last 0 rows 19 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 49.1 | drt_violations best 9 last 9 rows 58 | before-window best 11, window best 9 | PROGRESS: drt_violations improved 18.2 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 25.5 | drt_violations best 9761 last 9761 rows 10 | before-window best 33445, window best 9761 | PROGRESS: drt_violations improved 70.8 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 21.9 | drt_violations best 405 last 405 rows 17 | before-window best 120549, window best 405 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 22.5 | drt_violations best 7794 last 7794 rows 13 | before-window best 17848, window best 7794 | PROGRESS: drt_violations improved 56.3 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-352648 | col_h9_r2__t1 | 4_2_tapbal_grt | 0.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 23.5 | drt_violations best 806 last 820 rows 31 | before-window best 1435, window best 806 | PROGRESS: drt_violations improved 43.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 25.5 | drt_violations best 858 last 1374 rows 35 | before-window best 994, window best 858 | PROGRESS: drt_violations improved 13.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvb3f647ea-1347531 | col_h9_r2__t1 | 4_1_cts | 0.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-4156698 | col_h9_r2__t1 | 5_2_route | 10.4 | drt_violations best 566 last 566 rows 13 | before-window best 158380, window best 566 | PROGRESS: drt_violations improved 99.6 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | 5_2_route | 12.0 | drt_violations best 3961 last 3961 rows 11 | before-window best 167283, window best 3961 | PROGRESS: drt_violations improved 97.6 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfb42a1ad-350001 | col_h9_r2__t1 | 4_2_tapbal_grt | 0.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-479268 | sle_su_l1 | 5_2_route | 11.1 | drt_violations best 14708 last 14708 rows 8 | before-window best 346595, window best 14708 | PROGRESS: drt_violations improved 95.8 % in window |  |
| epyc9 | prd-eco_retry_1795711573796550375-i1t-740519 | eco_retry_1795711573796550375-i1t | 5_1_grt | 0.4 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 22.8 | drt_violations best 766 last 766 rows 30 | before-window best 1176, window best 766 | PROGRESS: drt_violations improved 34.9 % in window |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 22.7 | drt_violations best 4 last 4 rows 50 | before-window best 6, window best 4 | PROGRESS: drt_violations improved 33.3 % in window |  |
