# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-26 10:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 10, 'GRT-LABEL': 6, 'YOUNG': 44, 'NO-DATA': 4, 'KEEP': 1, 'PROGRESS': 13}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 15.3 | last meaningful line 13.3 h ago (33/36 lines) | NO-PROGRESS: no new non-iteration log line for 13.3 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc11 | dpkit-svc_lo_dsdv_svc_rs_w__t1-1738997 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 8.8 | last meaningful line 8.0 h ago (626/626 lines) | NO-PROGRESS: no new non-iteration log line for 8.0 h | REPORT-ONLY: lane-own kit (FAM-S81-SVC-OWN decides |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 32.9 | drt_violations best 387 last 387 rows 44 | before-window best 391, window best 387 | NO-PROGRESS: drt_violations best 387 vs 391 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 12.1 | last meaningful line 11.3 h ago (700/700 lines) | NO-PROGRESS: no new non-iteration log line for 11.3 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 26.2 | drt_violations best 858 last 989 rows 36 | before-window best 858, window best 882 | NO-PROGRESS: drt_violations best 882 vs 858 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 24.8 | drt_violations best 377 last 377 rows 58 | before-window best 384, window best 377 | NO-PROGRESS: drt_violations best 377 vs 384 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 5_1_grt | 12.4 | repair_TNS best 68544 last 68544 rows 3 | before-window best 69154.6, window best 68544 | NO-PROGRESS: repair_TNS best 68544 vs 69154.6 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 29.1 | repair_Viol best 968 last 968 rows 446 | before-window best 968, window best 968 | NO-PROGRESS: repair_Viol best 968 vs 968 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 45.1 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 15.2 | last meaningful line 11.5 h ago (33/35 lines) | NO-PROGRESS: no new non-iteration log line for 11.5 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3256841 | col_h9_r1__t1 | 5_1_grt | 0.4 | grt rounds 7 overflow 10:3228 -> 15:2332 -> 20:2387 -> 25:2108 -> 30:2029 -> 35:1940 | GRT-LABEL: DESIGN-FAIL: overflow 3228 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-3553036 | col_h9_r1__t1 | 5_1_grt | 0.2 | grt rounds 7 overflow 10:3179 -> 15:2255 -> 20:2262 -> 25:2234 -> 30:1936 -> 35:1955 | GRT-LABEL: DESIGN-FAIL: overflow 3179 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8aaf8508-3602152 | col_h9_r1__t1 | 5_1_grt | 8.7 | grt rounds 5 overflow 5:130266 -> 10:3229 -> 15:2333 -> 20:2377 -> 25:2233 | GRT-LABEL: DESIGN-FAIL: overflow 3229 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-3543915 | col_h9_r1__t1 | 5_1_grt | 0.2 | grt rounds 6 overflow 5:130096 -> 10:3228 -> 15:2328 -> 20:2341 -> 25:2179 -> 30:1984 | GRT-LABEL: DESIGN-FAIL: overflow 3228 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2895251 | col_h9_r1__t1 | 5_1_grt | 0.5 | grt rounds 6 overflow 5:131089 -> 10:3213 -> 15:2290 -> 20:2318 -> 25:2158 -> 30:1951 | GRT-LABEL: DESIGN-FAIL: overflow 3213 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-3637056 | col_h9_r1__t1 | 5_1_grt | 0.1 | grt rounds 7 overflow 10:3145 -> 15:2226 -> 20:2321 -> 25:2149 -> 30:1883 -> 35:1834 | GRT-LABEL: DESIGN-FAIL: overflow 3145 at round 10 > 1000 |  |
| epyc12 | dpkit-kv3_hgi_v5-4108530 | kv3_hgi_v5 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.6632 last 0.6776 rows 25 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-kv3_hub_Ei-3781587 | kv3_hub_Ei | 3_3_place_gp | 0.5 | overflow best 0.2831 last 0.2831 rows 39 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl23f6a148-3982341 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9965 last 0.9965 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-197708 | kv3_pc_v1 | 2_1_floorplan | 0.1 | repair_Viol best 8510 last 8510 rows 411 | YOUNG: stage 0.0 h < 1 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-214101 | kv3_pc_v1 | 2_1_floorplan | 0.1 | repair_Viol best 8510 last 8510 rows 214 | YOUNG: stage 0.0 h < 1 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl4ea58a5c__r877307f5d-4111264 | kv3_pc_v1 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl7f648944__r8c6505067-261251 | kv3_pc_v1 | synth_odb_v | 0.1 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl7f648944__r8d9b5d53e-10230 | kv3_pc_v1 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (1383/1383 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc_v3-275897 | kv3_pc_v3 | 1_synth | 0.1 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pv_v3e-20065 | kv3_pv_v3e | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (62/62 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pv_v4-11558 | kv3_pv_v4 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.3302 last 0.3302 rows 32 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | prd-eco_20261126_033735_1990069-i1-820044 | eco_20261126_033735_1990069-i1 | 5_2_route | 2.9 | drt_violations best 45 last 45 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_045746_1995760-i1-4043582 | eco_20261126_045746_1995760-i1 | 5_2_route | 1.5 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-hd_serdes-3132909 | hd_serdes | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | lecq9r2c-0033e091829a | lecq9r2c-0033e091829a | gold.ys | 0.7 | last meaningful line 0.2 h ago (26309/26309 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261126_090542_621054-i2-3168523 | eco_20261126_090542_621054-i2 | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (144/144 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | lecr2-hc3-d5fde-standalone-twins | lecr2-hc3-d5fde-standalone-twins | - | 1.4 |  | NO-DATA: no log found |  |
| epyc8 | lecr2-tw3-l2 | lecr2-tw3-l2 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-bk_sel__t2-2622147 | bk_sel__t2 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (6075/6075 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | postcts_gate_TT | 11.7 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-2052684 | col_h9_r0_p4__t1 | 4_2_tapbal_grt | 0.8 | last meaningful line 0.3 h ago (62/74 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv0012ba28-3031597 | col_h9_r0_p6__t1 | 4_2_tapbal_grt | 0.5 | last meaningful line 0.0 h ago (60/61 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-1637829 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.0 | last meaningful line 0.3 h ago (61/70 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49f0ba38-2484033 | col_h9_r1__t1 | 4_2_tapbal_grt | 0.7 | last meaningful line 0.1 h ago (61/64 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvf0f1ccb2-2216088 | col_h9_r1__t1 | 4_2_tapbal_grt | 0.8 | last meaningful line 0.3 h ago (61/69 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-352648 | col_h9_r2__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 29130.8 last 29130.8 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvfef7c177-3709744 | col_h9_r2__t1 | 5_2_route | 9.6 | drt_violations best 167856 last 167856 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-3472955 | col_h9_r2__t1 | postcts_gate_TT | 0.2 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvb3258867-556022 | col_h9_r2__t1 | pregrt_ff_hold | 1.2 | repair_TNS best 60328.8 last 60328.8 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvb3f647ea-1347531 | col_h9_r2__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 70700.8 last 70700.8 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfb42a1ad-350001 | col_h9_r2__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 26160.6 last 26160.6 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfd79e8b6-2469832 | col_h9_r2__t1 | 5_2_route | 10.7 | drt_violations best 23042 last 23042 rows 3 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-4056356 | dsdv_slice_c1x_C__t8 | pregrt_ff_hold | 8.6 | repair_TNS best 155160 last 155160 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_C__t1-2355590 | dsdv_slice_lepe_mu_C__t1 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-eng__t1-3293665 | eng__t1 | 3_3_place_gp | 0.4 | overflow best 0.2908 last 0.2915 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-gunit__t1-645727 | gunit__t1 | 3_5_place_dp | 1.2 | last meaningful line 0.5 h ago (39/39 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t51-2448564 | ot_s81sl_leaf__t51 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (4688/4688 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t54__cl706d9749-3015386 | ot_s81sl_leaf__t54 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (73/73 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t14-2764791 | serdes__t14 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.9387 last 0.9389 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-serdes__t3-3336445 | serdes__t3 | 2_1_floorplan | 0.3 | repair_Viol best 142 last 142 rows 60 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-3465321 | sle_su_l1 | postcts_gate_TT | 0.3 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t24__cleece78ec-2317934 | slice_station__t24 | postcts_gate_TT | 0.8 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_072708_1527702-i2t-914930 | eco_20261126_072708_1527702-i2t | 5_2_route | 5.3 | drt_violations best 1 last 2 rows 44 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_124723_1617778-i1-1533755 | eco_20261126_124723_1617778-i1 | 5_2_route | 5.2 | drt_violations best 206 last 206 rows 4 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc9 | prd-eco_retry_1795711573796550375-i1t-740519 | eco_retry_1795711573796550375-i1t | 5_1_grt | 1.2 | last meaningful line 0.7 h ago (310/588 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | 4_1_cts | 1.9 | last meaningful line 0.1 h ago (5939/5939 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 13.7 |  | NO-DATA: no log found |  |
| intel1 | otc-2895210-24702 | 2895210 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-454895 | col_h9_r1__t1 | 5_1_grt | 10.2 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_2_route | 16.1 | drt_violations best 3 last 3 rows 56 | before-window best 10, window best 3 | PROGRESS: drt_violations improved 70.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 32.5 | drt_violations best 11774 last 20077 rows 19 | before-window best 12170, window best 11774 | PROGRESS: drt_violations improved 3.3 % in window |  |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 10.8 | drt_violations best 7 last 28 rows 37 | before-window best 28, window best 7 | PROGRESS: drt_violations improved 75.0 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 49.9 | drt_violations best 9 last 9 rows 58 | before-window best 11, window best 9 | PROGRESS: drt_violations improved 18.2 % in window |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | 5_2_route | 12.9 | drt_violations best 107508 last 107508 rows 1 | before-window best 107508, window best 107508 | PROGRESS: drt_violations: active iteration at 14963 < best completed total 107508 (in-iter |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 23.2 | drt_violations best 7794 last 7794 rows 13 | before-window best 14907, window best 7794 | PROGRESS: drt_violations improved 47.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 24.2 | drt_violations best 806 last 818 rows 33 | before-window best 1435, window best 806 | PROGRESS: drt_violations improved 43.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | 5_2_route | 12.1 | drt_violations best 7390 last 7390 rows 9 | before-window best 185285, window best 7390 | PROGRESS: drt_violations improved 96.0 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-4156698 | col_h9_r2__t1 | 5_2_route | 11.1 | drt_violations best 365 last 365 rows 21 | before-window best 158380, window best 365 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | 5_2_route | 12.8 | drt_violations best 2326 last 2326 rows 13 | before-window best 167283, window best 2326 | PROGRESS: drt_violations improved 98.6 % in window |  |
| epyc9 | dpkit-slice_station__t38-739500 | slice_station__t38 | 5_1_grt | 1.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 23.5 | drt_violations best 765 last 765 rows 31 | before-window best 1176, window best 765 | PROGRESS: drt_violations improved 34.9 % in window |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 23.5 | drt_violations best 4 last 4 rows 50 | before-window best 6, window best 4 | PROGRESS: drt_violations improved 33.3 % in window |  |
