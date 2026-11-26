# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-26 09:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 10, 'UNSIGNABLE': 1, 'GRT-LABEL': 1, 'YOUNG': 38, 'NO-DATA': 4, 'KEEP': 1, 'PROGRESS': 17}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 15.0 | last meaningful line 13.0 h ago (33/36 lines) | NO-PROGRESS: no new non-iteration log line for 13.0 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc11 | dpkit-svc_lo_dsdv_svc_rs_w__t1-1738997 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 8.6 | last meaningful line 7.8 h ago (626/626 lines) | NO-PROGRESS: no new non-iteration log line for 7.8 h | REPORT-ONLY: lane-own kit (FAM-S81-SVC-OWN decides |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 32.2 | drt_violations best 3665 last 4885 rows 25 | before-window best 3665, window best 4885 | NO-PROGRESS: drt_violations best 4885 vs 3665 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 32.6 | drt_violations best 387 last 387 rows 44 | before-window best 391, window best 387 | NO-PROGRESS: drt_violations best 387 vs 391 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 11.8 | last meaningful line 11.0 h ago (700/700 lines) | NO-PROGRESS: no new non-iteration log line for 11.0 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8aaf8508-3602152 | col_h9_r1__t1 | 5_1_grt | 8.4 | grt rounds 4 overflow 5:130266 -> 10:3229 -> 15:2333 -> 20:2377 | UNSIGNABLE: GRT overflow flat: overflow 2333 at iteration 15 -> 2377 at iteration 20: flat f | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 26.0 | drt_violations best 858 last 989 rows 36 | before-window best 858, window best 882 | NO-PROGRESS: drt_violations best 882 vs 858 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 24.5 | drt_violations best 377 last 377 rows 58 | before-window best 384, window best 377 | NO-PROGRESS: drt_violations best 377 vs 384 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 28.9 | repair_Viol best 968 last 968 rows 436 | before-window best 968, window best 968 | NO-PROGRESS: repair_Viol best 968 vs 968 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 44.9 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 15.0 | last meaningful line 11.2 h ago (33/35 lines) | NO-PROGRESS: no new non-iteration log line for 11.2 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2895251 | col_h9_r1__t1 | 5_1_grt | 0.3 | grt rounds 6 overflow 5:131089 -> 10:3213 -> 15:2290 -> 20:2318 -> 25:2158 -> 30:1951 | GRT-LABEL: DESIGN-FAIL: overflow 3213 at round 10 > 1000 |  |
| epyc12 | dpkit-kv3_hgi_v5-4108530 | kv3_hgi_v5 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (252/252 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-kv3_hub_Ei-3781587 | kv3_hub_Ei | 2_3_floorplan_tapcell | 0.2 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl23f6a148-3982341 | kv3_pc_v1 | 2_1_floorplan | 0.1 | repair_Viol best 8508 last 8508 rows 253 | YOUNG: stage 0.0 h < 1 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl4ea58a5c__r877307f5d-4111264 | kv3_pc_v1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-kv3_phy_v1-4109298 | kv3_phy_v1 | 2_4_floorplan_pdn | 0.0 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | otc-3665431-5035 | 3665431 | asbuilt.yosys | 0.3 | last meaningful line 0.1 h ago (242584/242584 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_033735_1990069-i1-820044 | eco_20261126_033735_1990069-i1 | 5_2_route | 2.6 | drt_violations best 45 last 45 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_045746_1995760-i1-4043582 | eco_20261126_045746_1995760-i1 | 5_2_route | 1.3 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-hd_serdes-3132909 | hd_serdes | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (182/182 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | lecq9r2c-0033e091829a | lecq9r2c-0033e091829a | gold.ys | 0.4 | last meaningful line 0.0 h ago (26309/26309 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261126_090542_621054-i2-3168523 | eco_20261126_090542_621054-i2 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | lecr2-hc3-d5fde-standalone-twins | lecr2-hc3-d5fde-standalone-twins | - | 1.2 |  | NO-DATA: no log found |  |
| epyc8 | lecr2-tw2-l2 | lecr2-tw2-l2 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-bk_sel__t2-2622147 | bk_sel__t2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (6029/6029 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | tt_setup_repair_grt | 11.4 | repair_Violations best 181 last 181 rows 47 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-2052684 | col_h9_r0_p4__t1 | 4_2_tapbal_grt | 0.6 | last meaningful line 0.0 h ago (62/65 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-1637829 | col_h9_r1__t1 | 4_2_tapbal_grt | 0.7 | last meaningful line 0.0 h ago (61/64 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvf0f1ccb2-2216088 | col_h9_r1__t1 | 4_2_tapbal_grt | 0.6 | last meaningful line 0.0 h ago (61/62 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-352648 | col_h9_r2__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 29130.8 last 29130.8 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pvf0595d0f-3171495 | col_h9_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.5383 last 0.5383 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvfef7c177-3709744 | col_h9_r2__t1 | 5_2_route | 9.3 | drt_violations best 167856 last 167856 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvb3258867-556022 | col_h9_r2__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 60328.8 last 60328.8 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvb3f647ea-1347531 | col_h9_r2__t1 | pregrt_ff_hold | 0.8 | repair_TNS best 70700.8 last 70700.8 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfb42a1ad-350001 | col_h9_r2__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 26160.6 last 26160.6 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfd79e8b6-2469832 | col_h9_r2__t1 | 5_2_route | 10.4 | drt_violations best 23042 last 23042 rows 3 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t5-2762817 | dsdv_slice_c1x_C__t5 | sdc_lint | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-4056356 | dsdv_slice_c1x_C__t8 | hold_gate | 8.3 | last meaningful line 0.0 h ago (964/964 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_C__t1-2355590 | dsdv_slice_lepe_mu_C__t1 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-eng__t1-3293665 | eng__t1 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.9771 last 0.9771 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-gunit__t1-645727 | gunit__t1 | 3_5_place_dp | 1.0 | last meaningful line 0.3 h ago (39/39 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t51-2448564 | ot_s81sl_leaf__t51 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (86/86 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t54__cl706d9749-3015386 | ot_s81sl_leaf__t54 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (54/54 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t14-2764791 | serdes__t14 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t3-3336445 | serdes__t3 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (194/194 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-3465321 | sle_su_l1 | selrange | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t38-739500 | slice_station__t38 | pregrt_ff_hold | 0.9 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc9 | prd-eco_20261126_072708_1527702-i2t-914930 | eco_20261126_072708_1527702-i2t | 5_2_route | 5.1 | drt_violations best 5783 last 5783 rows 3 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_124723_1617778-i1-1533755 | eco_20261126_124723_1617778-i1 | 5_2_route | 4.9 | drt_violations best 8233 last 8233 rows 2 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc9 | prd-eco_retry_1795711573796550375-i1t-740519 | eco_retry_1795711573796550375-i1t | 5_1_grt | 0.9 | last meaningful line 0.5 h ago (310/484 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | 4_1_cts | 1.6 | last meaningful line 0.1 h ago (5910/5910 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 13.4 |  | NO-DATA: no log found |  |
| intel1 | otc-2895210-24702 | 2895210 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-454895 | col_h9_r1__t1 | 5_1_grt | 10.0 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_2_route | 15.9 | drt_violations best 3 last 3 rows 56 | before-window best 89, window best 3 | PROGRESS: drt_violations improved 96.6 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 32.2 | drt_violations best 11774 last 20077 rows 19 | before-window best 12170, window best 11774 | PROGRESS: drt_violations improved 3.3 % in window |  |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 10.5 | drt_violations best 7 last 28 rows 37 | before-window best 45, window best 7 | PROGRESS: drt_violations improved 84.4 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 49.6 | drt_violations best 9 last 9 rows 58 | before-window best 11, window best 9 | PROGRESS: drt_violations improved 18.2 % in window |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | 5_2_route | 12.7 | drt_violations best 107508 last 107508 rows 1 | before-window best 107508, window best 107508 | PROGRESS: drt_violations: active iteration at 33422 < best completed total 107508 (in-iter |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv0012ba28-3031597 | col_h9_r0_p6__t1 | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 11 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 23.0 | drt_violations best 7794 last 7794 rows 13 | before-window best 15952, window best 7794 | PROGRESS: drt_violations improved 51.1 % in window |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3256841 | col_h9_r1__t1 | pregrt_ff_hold | 0.1 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49f0ba38-2484033 | col_h9_r1__t1 | 4_1_cts | 0.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 24.0 | drt_violations best 806 last 818 rows 32 | before-window best 1435, window best 806 | PROGRESS: drt_violations improved 43.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | 5_2_route | 11.8 | drt_violations best 7390 last 7390 rows 9 | before-window best 185285, window best 7390 | PROGRESS: drt_violations improved 96.0 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-4156698 | col_h9_r2__t1 | 5_2_route | 10.9 | drt_violations best 406 last 406 rows 17 | before-window best 158380, window best 406 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | 5_2_route | 12.5 | drt_violations best 3232 last 3232 rows 12 | before-window best 167283, window best 3232 | PROGRESS: drt_violations improved 98.1 % in window |  |
| epyc9 | dpkit-slice_station__t24__cleece78ec-2317934 | slice_station__t24 | 5_1_grt | 0.5 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 5_1_grt | 12.2 | repair_TNS best 69509.2 last 69509.2 rows 10 | before-window best 72585.9, window best 69509.2 | PROGRESS: repair_TNS improved 4.2 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 23.3 | drt_violations best 766 last 766 rows 30 | before-window best 1176, window best 766 | PROGRESS: drt_violations improved 34.9 % in window |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 23.2 | drt_violations best 4 last 4 rows 50 | before-window best 6, window best 4 | PROGRESS: drt_violations improved 33.3 % in window |  |
