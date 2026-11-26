# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-26 10:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 7, 'GRT-LABEL': 6, 'YOUNG': 46, 'NO-DATA': 3, 'KEEP': 1, 'PROGRESS': 11}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 15.8 | last meaningful line 13.8 h ago (33/36 lines) | NO-PROGRESS: no new non-iteration log line for 13.8 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc11 | dpkit-svc_lo_dsdv_svc_rs_w__t1-1738997 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 9.3 | last meaningful line 8.5 h ago (626/626 lines) | NO-PROGRESS: no new non-iteration log line for 8.5 h | REPORT-ONLY: lane-own kit (FAM-S81-SVC-OWN decides |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 33.4 | drt_violations best 387 last 387 rows 44 | before-window best 388, window best 387 | NO-PROGRESS: drt_violations best 387 vs 388 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 12.6 | last meaningful line 11.8 h ago (700/700 lines) | NO-PROGRESS: no new non-iteration log line for 11.8 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 29.6 | repair_Viol best 968 last 968 rows 466 | before-window best 968, window best 968 | NO-PROGRESS: repair_Viol best 968 vs 968 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 45.6 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 15.7 | last meaningful line 12.0 h ago (33/35 lines) | NO-PROGRESS: no new non-iteration log line for 12.0 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3256841 | col_h9_r1__t1 | 5_1_grt | 0.9 | grt rounds 7 overflow 10:3228 -> 15:2332 -> 20:2387 -> 25:2108 -> 30:2029 -> 35:1940 | GRT-LABEL: DESIGN-FAIL: overflow 3228 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-3553036 | col_h9_r1__t1 | 5_1_grt | 0.7 | grt rounds 7 overflow 10:3179 -> 15:2255 -> 20:2262 -> 25:2234 -> 30:1936 -> 35:1955 | GRT-LABEL: DESIGN-FAIL: overflow 3179 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8aaf8508-3602152 | col_h9_r1__t1 | 5_1_grt | 9.2 | grt rounds 5 overflow 5:130266 -> 10:3229 -> 15:2333 -> 20:2377 -> 25:2233 | GRT-LABEL: DESIGN-FAIL: overflow 3229 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-3543915 | col_h9_r1__t1 | 5_1_grt | 0.7 | grt rounds 6 overflow 5:130096 -> 10:3228 -> 15:2328 -> 20:2341 -> 25:2179 -> 30:1984 | GRT-LABEL: DESIGN-FAIL: overflow 3228 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2895251 | col_h9_r1__t1 | 5_1_grt | 1.0 | grt rounds 6 overflow 5:131089 -> 10:3213 -> 15:2290 -> 20:2318 -> 25:2158 -> 30:1951 | GRT-LABEL: DESIGN-FAIL: overflow 3213 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-3637056 | col_h9_r1__t1 | 5_1_grt | 0.6 | grt rounds 7 overflow 10:3145 -> 15:2226 -> 20:2321 -> 25:2149 -> 30:1883 -> 35:1834 | GRT-LABEL: DESIGN-FAIL: overflow 3145 at round 10 > 1000 |  |
| epyc12 | dpkit-kv3_hub_Ei-3781587 | kv3_hub_Ei | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl23f6a148-3982341 | kv3_pc_v1 | 3_3_place_gp | 0.8 | overflow best 0.2033 last 0.2033 rows 40 | YOUNG: stage 0.3 h < 1 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl23f6a148-649446 | kv3_pc_v1 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (58/58 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-197708 | kv3_pc_v1 | 3_3_place_gp | 0.6 | overflow best 0.787 last 0.787 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-214101 | kv3_pc_v1 | 3_3_place_gp | 0.6 | last meaningful line 0.0 h ago (204/204 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl4ea58a5c__r84d0332e1-567798 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.9065 last 0.9176 rows 5 | YOUNG: stage 0.0 h < 1 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl4ea58a5c__r877307f5d-4111264 | kv3_pc_v1 | 3_3_place_gp | 0.8 | overflow best 0.2661 last 0.2661 rows 35 | YOUNG: stage 0.2 h < 1 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl4ea58a5c__r884969661-358744 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.3422 last 0.3422 rows 38 | YOUNG: stage 0.2 h < 1 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl7f648944__r817e6c402-652325 | kv3_pc_v1 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.1 h ago (58/58 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl7f648944__r8c6505067-261251 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.1719 last 0.1719 rows 44 | YOUNG: stage 0.2 h < 1 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl7f648944__r8c6505067-357611 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.4361 last 0.4361 rows 36 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl7f648944__r8d9b5d53e-10230 | kv3_pc_v1 | 3_3_place_gp | 0.7 | overflow best 0.6605 last 0.6605 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl7f648944__r8d9b5d53e-448008 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.8556 last 0.9027 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-kv3_pc_v3-275897 | kv3_pc_v3 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.5383 last 0.5383 rows 32 | YOUNG: stage 0.2 h < 1 h |  |
| epyc12 | dpkit-kv3_pc_v3-449637 | kv3_pc_v3 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.8467 last 0.8479 rows 9 | YOUNG: stage 0.0 h < 1 h |  |
| epyc12 | dpkit-kv3_pv_v3e-20065 | kv3_pv_v3e | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (317/317 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pv_v5ne-825000 | kv3_pv_v5ne | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (65/65 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_045746_1995760-i1-4043582 | eco_20261126_045746_1995760-i1 | 5_2_route | 2.0 | last meaningful line 0.2 h ago (281/282 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | prd-fin-820044 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepw_mus_C__t1-3958079 | dsdv_slice_lepw_mus_C__t1 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-3958093 | hd_lep0N | 3_1_place_gp_skip_io | 0.1 | overflow best 0.6123 last 0.6123 rows 27 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N_w-3958102 | hd_lep0N_w | 3_3_place_gp | 0.1 | overflow best 0.6665 last 0.6665 rows 9 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | lecr2-cf1-l5f | lecr2-cf1-l5f | gold.ys | 0.2 | last meaningful line 0.2 h ago (25768/25768 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | lecr2-hc0-1120 | lecr2-hc0 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | otc-4091059-27023 | 4091059 | gen_lint_check | 0.0 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261126_090542_621054-i2-3168523 | eco_20261126_090542_621054-i2 | 5_1_grt | 0.8 | last meaningful line 0.4 h ago (304/1389 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-bk_sel__t2-2622147 | bk_sel__t2 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (6147/6147 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv0012ba28-3031597 | col_h9_r0_p6__t1 | tt_setup_repair | 1.0 | last meaningful line -0.0 h ago (227/227 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49f0ba38-2484033 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.2 | last meaningful line 0.5 h ago (61/75 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-352648 | col_h9_r2__t1 | pregrt_ff_hold | 1.8 | repair_TNS best 29130.8 last 29130.8 rows 1 | YOUNG: evidence 1.0 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvfef7c177-3709744 | col_h9_r2__t1 | 5_2_route | 10.1 | drt_violations best 40152 last 40152 rows 2 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-3472955 | col_h9_r2__t1 | 5_2_route | 0.7 | last meaningful line 0.1 h ago (263/263 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvb3258867-556022 | col_h9_r2__t1 | pregrt_ff_hold | 1.7 | repair_TNS best 60328.8 last 60328.8 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfb42a1ad-350001 | col_h9_r2__t1 | pregrt_ff_hold | 1.8 | repair_TNS best 26160.6 last 26160.6 rows 1 | YOUNG: evidence 1.0 h < 2.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-4056356 | dsdv_slice_c1x_C__t8 | pregrt_ff_hold | 9.1 | repair_TNS best 155160 last 155160 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-gunit__t1-645727 | gunit__t1 | 3_5_place_dp | 1.7 | last meaningful line 1.0 h ago (39/39 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t54__cl706d9749-3015386 | ot_s81sl_leaf__t54 | pregrt_ff_hold | 1.0 | repair_TNS best 166708 last 166708 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-serdes__t14-2764791 | serdes__t14 | 3_3_place_gp | 1.1 | overflow best 0.4506 last 0.4506 rows 84 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-serdes__t3-3336445 | serdes__t3 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.6485 last 0.6485 rows 33 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-3465321 | sle_su_l1 | postcts_gate_FF | 0.8 | last meaningful line -0.0 h ago (52536/52536 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t24__cleece78ec-2317934 | slice_station__t24 | 5_2_route | 1.3 | last meaningful line 0.1 h ago (232/233 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t38-739500 | slice_station__t38 | 5_1_grt | 1.7 | last meaningful line 0.0 h ago (704/735 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_072708_1527702-i2-249891 | eco_20261126_072708_1527702-i2 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_retry_1795711573796550375-i1t-740519 | eco_retry_1795711573796550375-i1t | 5_2_route | 1.7 | last meaningful line 0.0 h ago (274/274 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | so_308335_ff_58930 | so_308335_ff_58930 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | so_308335_tt_58930 | so_308335_tt_58930 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-2843629 | sle_sc_v1 | pregrt_ff_hold | 2.4 | last meaningful line 0.0 h ago (50/50 lines) | YOUNG: evidence 0.1 h < 2.5 h |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 14.2 |  | NO-DATA: no log found |  |
| intel1 | otc-2895210-24702 | 2895210 | - | 2.3 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-454895 | col_h9_r1__t1 | 5_1_grt | 10.7 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_2_route | 16.6 | drt_violations best 3 last 3 rows 56 | before-window best 6, window best 3 | PROGRESS: drt_violations improved 50.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 33.0 | drt_violations best 11774 last 20077 rows 19 | before-window best 12170, window best 11774 | PROGRESS: drt_violations improved 3.3 % in window |  |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 11.3 | drt_violations best 7 last 28 rows 38 | before-window best 14, window best 7 | PROGRESS: drt_violations improved 50.0 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 50.4 | drt_violations best 9 last 9 rows 58 | before-window best 11, window best 9 | PROGRESS: drt_violations improved 18.2 % in window |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | 5_2_route | 13.4 | drt_violations best 9437 last 9437 rows 3 | before-window best 107508, window best 9437 | PROGRESS: drt_violations improved 91.2 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 24.7 | drt_violations best 806 last 2523 rows 34 | before-window best 1435, window best 806 | PROGRESS: drt_violations improved 43.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | 5_2_route | 12.6 | drt_violations best 5720 last 5720 rows 11 | before-window best 185285, window best 5720 | PROGRESS: drt_violations improved 96.9 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-4156698 | col_h9_r2__t1 | 5_2_route | 11.6 | drt_violations best 364 last 366 rows 32 | before-window best 158380, window best 364 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | 5_2_route | 13.3 | drt_violations best 959 last 959 rows 15 | before-window best 167283, window best 959 | PROGRESS: drt_violations improved 99.4 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 24.0 | drt_violations best 757 last 757 rows 32 | before-window best 1176, window best 757 | PROGRESS: drt_violations improved 35.6 % in window |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 24.0 | drt_violations best 4 last 4 rows 50 | before-window best 6, window best 4 | PROGRESS: drt_violations improved 33.3 % in window |  |
