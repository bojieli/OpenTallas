# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 15:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'GRT-LABEL': 3, 'YOUNG': 61, 'NO-DATA': 10, 'EXCLUDED': 2, 'PROGRESS': 21}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 25.7 | drt_violations best 5 last 5 rows 49 | before-window best 5, window best 5 | NO-PROGRESS: drt_violations best 5 vs 5 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 48.0 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 16.1 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 14.9 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc10 | dpkit-coll_core-2755880 | coll_core | 5_1_grt | 10.0 | grt rounds 2 overflow 5:6694 -> 10:735 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-3843742 | coll_core | 5_1_grt | 9.1 | grt rounds 2 overflow 5:353 -> 10:29 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pv_v3e-280312 | kv3_pv_v3e | 5_1_grt | 10.9 | grt rounds 1 overflow 5:174039 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-2130490 | coll_core | 5_1_grt | 7.2 | last meaningful line 0.5 h ago (1297/2967 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-2955109 | dsdv_slice_c1x_C__t8 | 5_1_grt | 9.9 | last meaningful line 0.3 h ago (211/214 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | otc-137942-9686 | 137942 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | otc-3829055-7004 | 3829055 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc10 | s81-svc3-mon-ttff-1123 | s81-svc3-mon-ttff | native_ttff.otrun | 0.0 | last meaningful line 0.0 h ago (98/98 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 3_4_place_resized | 10.2 | last meaningful line 2.0 h ago (449/449 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | otc-2072262-2525 | 2072262 | signoff | 3.3 | last meaningful line 3.3 h ago (3/3 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | otc-2508762-7926 | 2508762 | signoff | 3.0 | last meaningful line 2.8 h ago (3/3 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | otc-3577275-393 | 3577275 | - | 1.9 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261122_164248_3895049-i2-3950771 | eco_20261122_164248_3895049-i2 | 5_2_route | 1.5 | last meaningful line 0.1 h ago (271/271 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i2-635372 | eco_20261122_190506_3875261-i2 | 5_1_grt | 0.6 | last meaningful line 0.2 h ago (238/1395 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i1-1081003 | eco_20261123_103136_2028090-i1 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (144/144 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-fin-1118869 | fin | 6_report | 0.3 | last meaningful line 0.0 h ago (1075/1075 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-fin-768660 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (1070/1070 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 13.3 | last meaningful line 0.4 h ago (289/290 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-935860 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 5.0 | last meaningful line 0.0 h ago (73/73 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-hd_ctl-1292473 | hd_ctl | 5_2_route | 0.4 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-1586702 | hd_lep0N | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (60/60 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-1289562 | hd_lep0N_w | 4_2_tapbal_grt | 0.4 | last meaningful line 0.0 h ago (46/57 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_160238_2681508-i2t-772332 | eco_20261123_160238_2681508-i2t | 5_2_route | 1.0 | last meaningful line 0.1 h ago (279/280 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i1t-127041 | eco_20261123_171023_3055226-i1t | 5_2_route | 5.8 | drt_violations best 1 last 8 rows 53 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_184706_2375049-i1-526927 | eco_20261123_184706_2375049-i1 | 5_2_route | 1.3 | drt_violations best 79 last 79 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795467809896538497-i1t-60038 | eco_retry_1795467809896538497-i1t | 5_1_grt | 1.9 | repair_Viol best 2444 last 2444 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | prd-fin-3800902 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (57/57 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | so_1415096_ff_38463 | so_1415096_ff_38463 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (791/791 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | so_1415096_tt_38463 | so_1415096_tt_38463 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (791/791 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 5_1_grt | 11.2 | repair_TNS best 3842.57 last 3842.57 rows 5 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t27-3500785 | slice_station__t27 | 5_3_fillcell | 6.0 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-196363 | slice_station__t37 | 5_2_route | 5.6 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t42__clcf44e680-182679 | slice_station__t42 | 6_report | 5.6 | last meaningful line 0.1 h ago (66/66 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t43-157875 | slice_station__t43 | 5_2_route | 5.6 | drt_violations best 34560 last 34560 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t49-194878 | slice_station__t49 | 5_2_route | 5.6 | drt_violations best 18812 last 18812 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cl39451317-3753261 | slice_station__t50 | 5_2_route | 5.9 | drt_violations best 19853 last 19853 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cld84c9e24-169001 | slice_station__t50 | 6_report | 5.6 | last meaningful line 0.0 h ago (66/66 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | eco-abs-2696307 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (119/119 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i1-1884148 | eco_20261123_163717_2005956-i1 | 5_2_route | 2.8 | drt_violations best 17841 last 17841 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_2_route | 6.3 | last meaningful line 0.0 h ago (155/155 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | so_2298150_ff_86450 | so_2298150_ff_86450 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (1030/1030 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | so_2298150_tt_86450 | so_2298150_tt_86450 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (1030/1030 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | 6_report | 16.0 | last meaningful line 0.0 h ago (47/47 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | postcts_gate_FF | 18.0 | last meaningful line 0.0 h ago (1830/1830 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | otc-1100102-32114 | 1100102 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc9 | otc-1180901-15214 | 1180901 | 3_3_place_gp | 0.2 | overflow best 0.0994 last 0.0994 rows 44 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | otc-1258723-4618 | 1258723 | 3_3_place_gp | 0.1 | overflow best 0.2629 last 0.2629 rows 38 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | otc-1353161-11569 | 1353161 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-142944-22790 | 142944 | signoff | 1.5 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | prd-eco-i2-3887394 | eco-i2 | 5_2_route | 2.0 | last meaningful line 0.1 h ago (300/301 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i1-961257 | eco_20261123_190031_3093983-i1 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (241/1304 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i1t-1096522 | eco_20261123_224216_149959-i1t | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i1t-1190624 | eco_20261123_224647_4153453-i1t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-fin-3778492 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-459624 | dsdv_slice_c1x_C__t6 | 3_5_place_dp | 4.1 | last meaningful line 0.0 h ago (117/117 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t7-1834998 | dsdv_slice_c1x_C__t7 | 3_1_place_gp_skip_io | 2.9 | overflow best 0.5312 last 0.5312 rows 32 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_c3x_C__t1-142746 | dsdv_slice_c3x_C__t1 | 3_5_place_dp | 4.4 | last meaningful line 0.2 h ago (37/37 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-2396125 | dsdv_slice_lepw_mu_C__t1 | 1_1_yosys_canonicalize | 2.3 | last meaningful line 1.0 h ago (144/144 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-native59-203599 | native59 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5055/5055 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | 5_2_route | 18.4 | drt_violations best 139912 last 139912 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts.otrun | 3.4 | last meaningful line 2.5 h ago (5/5 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | otc-137422-21832 | 137422 | - | 0.2 |  | NO-DATA: no log found |  |
| intel1 | otc-189587-7840 | 189587 | 3_3_place_gp | 0.2 | overflow best 0.5202 last 0.752 rows 52 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts.otrun | 2.7 | last meaningful line 2.5 h ago (5/5 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | prd-eco_20261123_090657_914087-i1t-2682219 | eco_20261123_090657_914087-i1t | 5_1_grt | 5.8 | repair_Viol best 1637 last 1637 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel1 | prd-eco_20261123_130527_1956436-i1t-2772907 | eco_20261123_130527_1956436-i1t | 5_2_route | 1.9 | drt_violations best 1139 last 1139 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | so_3108762_ff_81254 | so_3108762_ff_81254 | signoff | 1.6 |  | NO-DATA: empty log |  |
| intel1 | so_3108762_tt_81254 | so_3108762_tt_81254 | signoff | 1.6 |  | NO-DATA: empty log |  |
| intel1 | so_67214_ff_7189 | so_67214_ff_7189 | signoff | 0.3 |  | NO-DATA: empty log |  |
| intel1 | so_67214_tt_7189 | so_67214_tt_7189 | signoff | 0.3 |  | NO-DATA: empty log |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2731145 | col_h10_r1__t1 | 5_2_route | 11.0 | drt_violations best 72613 last 72613 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3102614 | coll_ftm | 5_2_route | 1.5 | last meaningful line 0.1 h ago (240/241 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i1-811516 | eco_20261123_051704_3678821-i1 | 5_2_route | 3.7 | drt_violations best 8 last 8 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i1-995418 | eco_20261123_063813_234645-i1 | 5_2_route | 3.5 | drt_violations best 15706 last 15706 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | otc-3954198-28432 | 3954198 | - | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | otc-4173474-32326 | 4173474 | - | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | 5_1_grt | 11.2 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 11.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 18.1 | drt_violations best 11282 last 11282 rows 15 | before-window best 19416, window best 11282 | PROGRESS: drt_violations improved 41.9 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 20.8 | drt_violations best 1743 last 2528 rows 19 | before-window best 2057, window best 1743 | PROGRESS: drt_violations improved 15.3 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 23.0 | drt_violations best 8936 last 8936 rows 15 | before-window best 10583, window best 8936 | PROGRESS: drt_violations improved 15.6 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 19.6 | drt_violations best 41866 last 41866 rows 14 | before-window best 50311, window best 41866 | PROGRESS: drt_violations improved 16.8 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 20.0 | drt_violations best 48840 last 48840 rows 14 | before-window best 52820, window best 48840 | PROGRESS: drt_violations improved 7.5 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_1_grt | 6.6 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 20.7 | drt_violations best 54432 last 54432 rows 14 | before-window best 65161, window best 54432 | PROGRESS: drt_violations improved 16.5 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 31.4 | drt_violations best 20 last 20 rows 54 | before-window best 25, window best 20 | PROGRESS: drt_violations improved 20.0 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 34.8 | drt_violations best 5582 last 5582 rows 23 | before-window best 7732, window best 5582 | PROGRESS: drt_violations improved 27.8 % in window |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 11.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 7.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | 4_1_cts | 9.5 | last meaningful line 0.3 h ago (10349/10349 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-slice_station__t38-3922551 | slice_station__t38 | 5_2_route | 5.8 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 18.9 | drt_violations best 16 last 18 rows 53 | before-window best 183055, window best 16 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | 4_1_cts | 8.8 | last meaningful line 0.3 h ago (11491/11491 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 34.2 | drt_violations best 29547 last 29547 rows 12 | before-window best 37187, window best 29547 | PROGRESS: drt_violations improved 20.5 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 20.9 | drt_violations best 88174 last 88174 rows 10 | before-window best 93635, window best 88174 | PROGRESS: drt_violations improved 5.8 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 18.2 | drt_violations best 37 last 37 rows 22 | before-window best 2611, window best 37 | PROGRESS: drt_violations improved 98.6 % in window |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 28.2 | drt_violations best 2178 last 3234 rows 20 | before-window best 2944, window best 2178 | PROGRESS: drt_violations improved 26.0 % in window |  |
