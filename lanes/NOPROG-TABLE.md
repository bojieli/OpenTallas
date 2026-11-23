# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 14:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'GRT-LABEL': 4, 'YOUNG': 61, 'NO-DATA': 9, 'PROGRESS': 20}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 47.0 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 15.3 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 14.2 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc10 | dpkit-coll_core-2755880 | coll_core | 5_1_grt | 9.0 | grt rounds 2 overflow 5:6694 -> 10:735 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-3843742 | coll_core | 5_1_grt | 8.1 | grt rounds 2 overflow 5:353 -> 10:29 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 5_1_grt | 17.5 | grt rounds 2 overflow 5:13375 -> 10:10994 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pv_v3e-280312 | kv3_pv_v3e | 5_1_grt | 9.9 | grt rounds 1 overflow 5:174039 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-2130490 | coll_core | pregrt_ff_hold | 6.2 | repair_Violations best 8 last 8 rows 15 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-2955109 | dsdv_slice_c1x_C__t8 | pregrt_ff_hold | 8.9 | repair_Violations best 517 last 517 rows 79 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | 5_1_grt | 10.2 | last meaningful line 0.2 h ago (2079/2092 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | eco-abs-2876970 | eco-abs | generate_abstract | 0.5 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | eco-abs-3282125 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (397/397 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-1692786-27381 | 1692786 | signoff | 1.7 | last meaningful line 1.6 h ago (3/3 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 3_4_place_resized | 9.2 | last meaningful line 1.0 h ago (449/449 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | otc-2072262-2525 | 2072262 | signoff | 2.3 | last meaningful line 2.3 h ago (3/3 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | otc-2508762-7926 | 2508762 | signoff | 2.0 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | otc-356178-19590 | 356178 | signoff | 3.8 | last meaningful line 3.8 h ago (3/3 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | otc-3577275-393 | 3577275 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc2 | prd-count-p1_bc-153753 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (784/784 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164248_3895049-i2-3950771 | eco_20261122_164248_3895049-i2 | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (239/1361 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i2t-1118869 | eco_20261122_181101_3945375-i2t | 5_2_route | 3.2 | drt_violations best 338 last 338 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i1t-768660 | eco_20261123_102841_2122262-i1t | 5_2_route | 3.5 | drt_violations best 9789 last 9789 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i1t-830727 | eco_20261123_103136_2028090-i1t | 5_2_route | 3.4 | drt_violations best 20886 last 20886 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 12.3 | last meaningful line 0.0 h ago (283/284 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | pregrt_ff_hold | 5.6 | repair_TNS best 275302 last 275302 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-935860 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 4.0 | last meaningful line 1.8 h ago (36/36 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | otc-3723552-11009 | 3723552 | - | 5.3 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261123_124118_879330-i1-896574 | eco_20261123_124118_879330-i1 | 5_2_route | 4.1 | drt_violations best 364 last 364 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_160238_2681508-i2t-772332 | eco_20261123_160238_2681508-i2t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i1t-127041 | eco_20261123_171023_3055226-i1t | 5_2_route | 4.8 | drt_violations best 30 last 30 rows 13 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171842_3718765-i1-3800902 | eco_20261123_171842_3718765-i1 | 5_2_route | 1.4 | last meaningful line 0.1 h ago (282/283 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_184706_2375049-i1-526927 | eco_20261123_184706_2375049-i1 | 5_2_route | 0.3 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795467809896538497-i1t-60038 | eco_retry_1795467809896538497-i1t | 5_1_grt | 0.9 | repair_Viol best 2444 last 2444 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 7.1 | repair_TNS best 19310.5 last 19310.5 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 5_1_grt | 10.4 | repair_TNS best 5322.05 last 5322.05 rows 2 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t27-3500785 | slice_station__t27 | 5_2_route | 5.2 | drt_violations best 22601 last 22601 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-196363 | slice_station__t37 | 5_2_route | 4.8 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t38-3922551 | slice_station__t38 | 5_2_route | 5.0 | drt_violations best 41090 last 41090 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t42__clcf44e680-182679 | slice_station__t42 | 5_2_route | 4.9 | drt_violations best 19399 last 19399 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t43-157875 | slice_station__t43 | 5_2_route | 4.9 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t49-194878 | slice_station__t49 | 5_2_route | 4.8 | last meaningful line 0.1 h ago (264/265 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cl39451317-3753261 | slice_station__t50 | 5_2_route | 5.1 | drt_violations best 19853 last 19853 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cld84c9e24-169001 | slice_station__t50 | 5_2_route | 4.9 | drt_violations best 20332 last 20332 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc8 | prd-count-p1_bc-1751532 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (1022/1022 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i1-805274 | eco_20261123_120225_75582-i1 | 5_2_route | 4.6 | drt_violations best 756 last 756 rows 2 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i1-1884148 | eco_20261123_163717_2005956-i1 | 5_2_route | 2.1 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_1_grt | 5.5 | repair_Viol best 2085 last 2085 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | 5_2_route | 15.3 | drt_violations best 25844 last 25844 rows 2 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | postcts_gate_FF | 17.3 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-142944-22790 | 142944 | signoff | 0.7 | last meaningful line 0.6 h ago (3/3 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 16.0 |  | NO-DATA: no log found |  |
| epyc9 | prd-count-p1_tc-2251452 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco-i2-3887394 | eco-i2 | 5_2_route | 1.3 | last meaningful line 0.1 h ago (288/289 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_205006_3008284-i1-3778492 | eco_20261123_205006_3008284-i1 | 5_2_route | 1.4 | last meaningful line 0.1 h ago (281/282 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | so_700632_ff_17438 | so_700632_ff_17438 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | so_700632_tt_17438 | so_700632_tt_17438 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | so_715099_ff_38501 | so_715099_ff_38501 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | so_715099_tt_38501 | so_715099_tt_38501 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t4-19056 | dsdv_slice_c1x_C__t4 | 3_3_place_gp | 3.5 | overflow best 0.7444 last 0.7444 rows 22 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-459624 | dsdv_slice_c1x_C__t6 | 3_1_place_gp_skip_io | 3.1 | overflow best 0.4426 last 0.4426 rows 35 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t7-1834998 | dsdv_slice_c1x_C__t7 | 1_1_yosys_canonicalize | 1.9 | last meaningful line 0.5 h ago (127/127 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c3x_C__t1-142746 | dsdv_slice_c3x_C__t1 | 3_3_place_gp | 3.4 | last meaningful line 0.1 h ago (45/45 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-2396125 | dsdv_slice_lepw_mu_C__t1 | 1_1_yosys_canonicalize | 1.3 | last meaningful line 0.1 h ago (143/143 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | 5_2_route | 17.4 | drt_violations best 139912 last 139912 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | 5_2_route | 18.1 | drt_violations best 5494 last 5494 rows 3 | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts.otrun | 2.4 | last meaningful line 1.5 h ago (5/5 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts.otrun | 1.7 | last meaningful line 1.5 h ago (5/5 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | otc-571036-12201 | 571036 | signoff | 3.0 | last meaningful line 2.8 h ago (3/3 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i2-876871 | eco_20261122_143408_943433-i2 | 5_2_route | 2.8 | drt_violations best 7151 last 7151 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | prd-eco_20261123_090657_914087-i1t-2682219 | eco_20261123_090657_914087-i1t | 5_1_grt | 4.8 | repair_Viol best 1637 last 1637 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel1 | prd-eco_20261123_130527_1956436-i1t-2772907 | eco_20261123_130527_1956436-i1t | 5_2_route | 0.9 | last meaningful line 0.1 h ago (247/248 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | so_3108762_ff_81254 | so_3108762_ff_81254 | signoff | 0.6 |  | NO-DATA: empty log |  |
| intel1 | so_3108762_tt_81254 | so_3108762_tt_81254 | signoff | 0.6 |  | NO-DATA: empty log |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2731145 | col_h10_r1__t1 | 5_2_route | 10.2 | drt_violations best 72613 last 72613 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3102614 | coll_ftm | 5_1_grt | 0.7 | repair_TNS best 17.396 last 17.396 rows 9 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i1-811516 | eco_20261123_051704_3678821-i1 | 5_2_route | 2.9 | drt_violations best 8 last 8 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i1-995418 | eco_20261123_063813_234645-i1 | 5_2_route | 2.8 | drt_violations best 15706 last 15706 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 10.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 17.1 | drt_violations best 13554 last 13554 rows 14 | before-window best 21163, window best 13554 | PROGRESS: drt_violations improved 36.0 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 19.8 | drt_violations best 1743 last 2528 rows 19 | before-window best 3088, window best 1743 | PROGRESS: drt_violations improved 43.6 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 22.0 | drt_violations best 8936 last 8936 rows 15 | before-window best 11209, window best 8936 | PROGRESS: drt_violations improved 20.3 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 18.6 | drt_violations best 41866 last 41866 rows 14 | before-window best 51167, window best 41866 | PROGRESS: drt_violations improved 18.2 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 19.0 | drt_violations best 48840 last 48840 rows 14 | before-window best 55792, window best 48840 | PROGRESS: drt_violations improved 12.5 % in window |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | 5_2_route | 12.4 | drt_violations best 1396 last 1403 rows 34 | before-window best 172065, window best 1396 | PROGRESS: drt_violations improved 99.2 % in window |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 24.7 | drt_violations best 5 last 5 rows 49 | before-window best 36, window best 5 | PROGRESS: drt_violations improved 86.1 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 19.7 | drt_violations best 56454 last 56454 rows 13 | before-window best 65161, window best 56454 | PROGRESS: drt_violations improved 13.4 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 30.6 | drt_violations best 20 last 20 rows 54 | before-window best 25, window best 20 | PROGRESS: drt_violations improved 20.0 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 34.0 | drt_violations best 6073 last 6073 rows 22 | before-window best 7732, window best 6073 | PROGRESS: drt_violations improved 21.5 % in window |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 10.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 21.5 | drt_violations best 14710 last 31045 rows 19 | before-window best 14710, window best 31045 | PROGRESS: drt_violations: falling inside the active iteration (31045 -> 24848) |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | 4_1_cts | 8.7 | last meaningful line 0.8 h ago (10038/10038 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 18.2 | drt_violations best 16 last 18 rows 51 | before-window best 183055, window best 16 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | 4_1_cts | 8.1 | last meaningful line 0.2 h ago (11179/11179 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 33.2 | drt_violations best 29547 last 29547 rows 12 | before-window best 37187, window best 29547 | PROGRESS: drt_violations improved 20.5 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 19.9 | drt_violations best 88977 last 88977 rows 9 | before-window best 98568, window best 88977 | PROGRESS: drt_violations improved 9.7 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 17.2 | drt_violations best 84 last 84 rows 20 | before-window best 6392, window best 84 | PROGRESS: drt_violations improved 98.7 % in window |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 27.5 | drt_violations best 2178 last 4340 rows 19 | before-window best 3303, window best 2178 | PROGRESS: drt_violations improved 34.1 % in window |  |
