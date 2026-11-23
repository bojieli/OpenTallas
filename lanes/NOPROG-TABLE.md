# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 15:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'UNSIGNABLE': 1, 'GRT-LABEL': 1, 'YOUNG': 64, 'NO-DATA': 12, 'EXCLUDED': 1, 'PROGRESS': 23}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 48.7 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 15.7 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | tt_setup_repair | 9.6 | repair_Viol best 1715 last 1715 rows 38 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -368.67 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | prd-eco_20261123_090657_914087-i1t-2682219 | eco_20261123_090657_914087-i1t | 5_1_grt | 6.6 | repair_Viol best 1637 last 1637 rows 1 | before-window best 1637, window best 1637 | NO-PROGRESS: repair_Viol best 1637 vs 1637 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-coll_core-3843742 | coll_core | 5_1_grt | 9.6 | grt rounds 2 overflow 5:353 -> 10:29 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-2955109 | dsdv_slice_c1x_C__t8 | 5_1_grt | 10.4 | last meaningful line 0.8 h ago (211/215 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | 5_1_grt | 11.7 | last meaningful line 0.3 h ago (2220/2226 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t2-490320 | serdes__t2 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-390565-5084 | 390565 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (7140/7140 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i3t-222551 | eco_20261122_223531_3628570-i3t | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (233/1266 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 3_5_place_dp | 10.7 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | otc-1381699-3941 | 1381699 | 3_3_place_gp | 0.3 | overflow best 0.1407 last 0.1407 rows 47 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | otc-3577275-393 | 3577275 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261122_164248_3895049-i2-3950771 | eco_20261122_164248_3895049-i2 | 5_2_route | 2.0 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i2-1254909 | eco_20261122_181101_3945375-i2 | 5_1_grt | 0.5 | last meaningful line 0.1 h ago (237/277 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i2-635372 | eco_20261122_190506_3875261-i2 | 5_2_route | 1.1 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i1-1373161 | eco_20261123_102841_2122262-i1 | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (174/174 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i1-1081003 | eco_20261123_103136_2028090-i1 | 5_1_grt | 0.7 | last meaningful line 0.4 h ago (239/1585 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 14.1 | last meaningful line 0.3 h ago (295/296 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_1_grt | 7.4 | last meaningful line 0.8 h ago (264/1288 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_ctl-1292473 | hd_ctl | 5_2_route | 1.1 | drt_violations best 57352 last 57352 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N-1586702 | hd_lep0N | 3_3_place_gp | 0.8 | overflow best 0.0971 last 0.0971 rows 43 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | otc-1909908-3003 | 1909908 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261123_160238_2681508-i2t-772332 | eco_20261123_160238_2681508-i2t | 5_2_route | 1.8 | drt_violations best 46463 last 46463 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171842_3718765-i2t-1856110 | eco_20261123_171842_3718765-i2t | 5_2_route | 0.6 | last meaningful line 0.0 h ago (269/270 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795467809896538497-i1t-60038 | eco_retry_1795467809896538497-i1t | 5_1_grt | 2.6 | repair_Viol best 2444 last 2444 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | prd-fin-127041 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | so_2396545_ff_85930 | so_2396545_ff_85930 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | so_2396545_tt_85930 | so_2396545_tt_85930 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 5_1_grt | 11.9 | repair_TNS best 2826.92 last 2826.92 rows 5 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-196363 | slice_station__t37 | 5_2_route | 6.3 | drt_violations best 32522 last 32522 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t43-157875 | slice_station__t43 | 5_2_route | 6.4 | drt_violations best 34560 last 34560 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t49-194878 | slice_station__t49 | 5_2_route | 6.3 | drt_violations best 18812 last 18812 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_fw_v3-3682147 | slw_fw_v3 | 3_3_place_gp | 0.3 | overflow best 0.414 last 0.414 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | otc-3666676-4874 | 3666676 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3678/3678 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | otc-3896264-30868 | 3896264 | signoff | 0.2 | last meaningful line 0.2 h ago (3/3 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i2t-3217904 | eco_20261123_120225_75582-i2t | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (260/843 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_140713_549985-i2t-3481758 | eco_20261123_140713_549985-i2t | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (297/624 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_2_route | 7.0 | last meaningful line 0.3 h ago (287/288 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | prd-fin-1884148 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (604/604 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | so_4073621_ff_6530 | so_4073621_ff_6530 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | so_4073621_tt_6530 | so_4073621_tt_6530 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | so_4087233_ff_81296 | so_4087233_ff_81296 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | so_4087233_tt_81296 | so_4087233_tt_81296 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | generate_abstract | 16.8 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_2_route | 18.8 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | otc-142944-22790 | 142944 | signoff | 2.2 | last meaningful line 2.1 h ago (3/3 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | otc-1679825-19413 | 1679825 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (242/242 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-1779329-26040 | 1779329 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc9 | otc-1948315-28115 | 1948315 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-1956063-24831 | 1956063 | 3_3_place_gp | 0.2 | overflow best 0.0258 last 0.7015 rows 258 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | otc-2109753-27146 | 2109753 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-2110516-11873 | 2110516 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i2-3887394 | eco-i2 | 5_2_route | 2.8 | drt_violations best 43 last 43 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i1-961257 | eco_20261123_190031_3093983-i1 | 5_2_route | 1.2 | last meaningful line 0.0 h ago (261/261 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i1t-1096522 | eco_20261123_224216_149959-i1t | 5_2_route | 1.0 | last meaningful line 0.1 h ago (131/131 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i1t-1190624 | eco_20261123_224647_4153453-i1t | 5_2_route | 0.9 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | so_1839590_ff_86855 | so_1839590_ff_86855 | generate_abstract | 0.4 | last meaningful line 0.2 h ago (779/779 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | so_1839590_tt_86855 | so_1839590_tt_86855 | generate_abstract | 0.4 | last meaningful line 0.2 h ago (779/779 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t7-1834998 | dsdv_slice_c1x_C__t7 | 3_5_place_dp | 3.7 | last meaningful line 0.0 h ago (73/73 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c3x_C__t1-142746 | dsdv_slice_c3x_C__t1 | 3_5_place_dp | 5.1 | last meaningful line 0.8 h ago (37/37 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-2396125 | dsdv_slice_lepw_mu_C__t1 | 3_3_place_gp | 3.1 | overflow best 0.7433 last 0.7731 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-native59-203599 | native59 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (5401/5401 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | 5_2_route | 19.1 | drt_violations best 139912 last 139912 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel1 | dpkit-sle_hc1__cl22c1ff36__pve230954c-649220 | sle_hc1 | 3_3_place_gp | 0.5 | overflow best 0.3136 last 0.4314 rows 45 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-sle_hc1__cl22c1ff36__pve289215f-651145 | sle_hc1 | 3_3_place_gp | 0.5 | overflow best 0.326 last 0.5894 rows 39 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | otc-1008104-13618 | 1008104 | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | otc-1091948-17553 | 1091948 | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts.otrun | 4.1 | last meaningful line 3.3 h ago (5/5 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | otc-189587-7840 | 189587 | 3_5_place_dp | 0.9 | last meaningful line 0.1 h ago (29/29 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts.otrun | 3.4 | last meaningful line 3.3 h ago (5/5 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | otc-549055-30027 | 549055 | signoff | 0.6 | last meaningful line 0.5 h ago (3/3 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | otc-910675-18621 | 910675 | w18_sta_ff | 0.2 | last meaningful line 0.2 h ago (116/116 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_20261123_152917_1693191-i1-910286 | eco_20261123_152917_1693191-i1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-fin-2772907 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2731145 | col_h10_r1__t1 | 5_2_route | 11.7 | drt_violations best 6742 last 6742 rows 3 | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3102614 | coll_ftm | 5_3_fillcell | 2.2 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-647484 | kv3_io_ft | 5_2_route | 0.7 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-667796 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (227/228 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | prd-count-p1_bc-811516 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (1019/1019 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | prd-count-p1_bc-995418 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (91/91 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-957965-24344 | 957965 | asbuilt.yosys | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-coll_core-2130490 | coll_core | 5_1_grt | 7.7 | repair_TNS best 0 last 0 rows 4 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 11.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 18.6 | drt_violations best 11282 last 11282 rows 15 | before-window best 19416, window best 11282 | PROGRESS: drt_violations improved 41.9 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 21.3 | drt_violations best 1743 last 1932 rows 20 | before-window best 1983, window best 1743 | PROGRESS: drt_violations improved 12.1 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 23.5 | drt_violations best 8281 last 8281 rows 16 | before-window best 10583, window best 8281 | PROGRESS: drt_violations improved 21.8 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 20.1 | drt_violations best 41866 last 41866 rows 14 | before-window best 48060, window best 41866 | PROGRESS: drt_violations improved 12.9 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 20.5 | drt_violations best 48840 last 48840 rows 14 | before-window best 52820, window best 48840 | PROGRESS: drt_violations improved 7.5 % in window |  |
| epyc7 | dpkit-hd_lep0N_w-1289562 | hd_lep0N_w | 4_2_tapbal_grt | 1.1 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 21.4 | drt_violations best 54432 last 54432 rows 14 | before-window best 60407, window best 54432 | PROGRESS: drt_violations improved 9.9 % in window |  |
| epyc7 | otc-2005282-104 | 2005282 | 4_1_cts | 0.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 32.1 | drt_violations best 20 last 20 rows 54 | before-window best 21, window best 20 | PROGRESS: drt_violations improved 4.8 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 35.5 | drt_violations best 5582 last 5582 rows 23 | before-window best 7732, window best 5582 | PROGRESS: drt_violations improved 27.8 % in window |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 12.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 8.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | 4_1_cts | 10.2 | last meaningful line 1.0 h ago (10349/10349 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-slice_station__t50__cl39451317-3753261 | slice_station__t50 | 5_2_route | 6.6 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | prd-eco_20261123_233239_167282-i1-4008532 | eco_20261123_233239_167282-i1 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 19.7 | drt_violations best 16 last 18 rows 53 | before-window best 33830, window best 16 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 16.8 | repair_Violations best 0 last 0 rows 15 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 35.0 | drt_violations best 24596 last 24596 rows 13 | before-window best 36675, window best 24596 | PROGRESS: drt_violations improved 32.9 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 21.6 | drt_violations best 88174 last 88174 rows 10 | before-window best 93635, window best 88174 | PROGRESS: drt_violations improved 5.8 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 18.9 | drt_violations best 37 last 37 rows 23 | before-window best 2273, window best 37 | PROGRESS: drt_violations improved 98.4 % in window |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 29.0 | drt_violations best 2178 last 2967 rows 21 | before-window best 2425, window best 2178 | PROGRESS: drt_violations improved 10.2 % in window |  |
