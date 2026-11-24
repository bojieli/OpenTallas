# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 19:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'GRT-LABEL': 2, 'YOUNG': 59, 'NO-DATA': 6, 'PROGRESS': 19}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 15.3 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (OPUS-FIX-KV-PV-R7 decid |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | 5_1_grt | 20.1 | grt rounds 2 overflow 5:13730 -> 10:13037 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | 5_1_grt | 18.9 | grt rounds 2 overflow 5:13850 -> 10:12903 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | prd-eco_20261122_223531_3628570-i3-52746 | eco_20261122_223531_3628570-i3 | 5_1_grt | 0.7 | last meaningful line 0.5 h ago (235/1294 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair | 0.9 | repair_Violations best 66 last 2663 rows 29 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (13035/13035 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_io_ft-64810 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5487 last 5487 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | eco-abs-1201405 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (1021/1021 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | eco-abs-399330 | eco-abs | generate_abstract | 0.7 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | eco-abs-789501 | eco-abs | generate_abstract | 0.4 | last meaningful line 0.2 h ago (970/970 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i1-1373161 | eco_20261123_102841_2122262-i1 | 5_2_route | 3.9 | drt_violations best 42 last 42 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | so_684865_ff_72441 | so_684865_ff_72441 | generate_abstract | 0.5 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | so_684865_tt_72441 | so_684865_tt_72441 | generate_abstract | 0.5 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 17.3 | drt_violations best 186589 last 186589 rows 2 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 10.6 | drt_violations best 391102 last 391102 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-2781664 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 2.9 | last meaningful line 0.5 h ago (37/37 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-1324433 | hd_lep0N | 4_1_cts | 0.1 | last meaningful line 0.1 h ago (24/24 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-1365803 | hd_lep0N | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (375/375 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-374468 | hd_lep0N | 3_3_place_gp | 0.9 | last meaningful line 0.2 h ago (201/201 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-1023502 | hd_lep0N_w | 4_2_tapbal_grt | 0.3 | last meaningful line 0.0 h ago (46/49 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-1242720 | hd_lep0N_w | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3097/3097 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i1-2638994 | eco_20261123_171023_3055226-i1 | 5_2_route | 3.0 | last meaningful line 0.3 h ago (280/281 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_184706_2375049-i2-1000308 | eco_20261123_184706_2375049-i2 | 5_2_route | 0.3 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795467809896538497-i1t-60038 | eco_retry_1795467809896538497-i1t | 5_2_route | 5.9 | last meaningful line 0.3 h ago (290/291 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (7879/7879 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q01__clab6e67f2-1043557 | cbn_q01 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (6642/6642 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (7658/7658 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q11__cl5cc92dfe-1712022 | cbn_q11 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5126/5126 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p5-2887155 | kv3_hg_v1p5 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (254/254 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | pregrt_ff_hold | 13.5 | repair_TNS best 495634 last 495634 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-2748514 | sle_ctl | 2_1_floorplan | 0.1 | repair_Viol best 2599 last 2599 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-2793240 | sle_st_a_v1 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (1419/1419 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-2390497 | sle_su_l1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3727/3727 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-2047894 | slw_fe_v2 | 3_3_place_gp | 0.4 | overflow best 0.5635 last 0.5635 rows 4 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slw_hc0__cl1bc59e1c-2142625 | slw_hc0 | 3_3_place_gp | 0.4 | overflow best 0.7236 last 0.7236 rows 29 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-2776104 | slw_st_a_v2 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (1418/1418 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2465278 | slw_su_l1 | 3_3_place_gp | 0.2 | overflow best 0.2109 last 0.2109 rows 35 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | eco-abs-2657632 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i2t-3217904 | eco_20261123_120225_75582-i2t | 5_2_route | 3.8 | drt_violations best 35926 last 35926 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i2t-991032 | eco_20261123_163717_2005956-i2t | 5_3_fillcell | 2.8 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_2_route | 10.3 | drt_violations best 107978 last 107978 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc8 | prd-fin-3481758 | fin | 6_report | 0.3 | last meaningful line 0.2 h ago (1072/1072 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | relec1122-ml-r6_afda1e9d | relec1122-ml-r6_afda1e9d | - | 2.8 |  | NO-DATA: no log found |  |
| epyc8 | relec1122-ml-r6_d5fde81d | relec1122-ml-r6_d5fde81d | - | 2.8 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | pregrt_ff_hold | 12.8 | repair_TNS best 188478 last 188478 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 6_report | 22.0 | last meaningful line 0.1 h ago (682/682 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-694182-22270 | 694182 | route | 0.4 | last meaningful line -0.0 h ago (445/445 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | otc-790184-14153 | 790184 | route | 0.3 | last meaningful line 0.0 h ago (405/405 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco-i3t-51485 | eco-i3t | 5_2_route | 1.0 | last meaningful line 0.1 h ago (289/289 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i1-456858 | eco_20261123_224216_149959-i1 | 5_1_grt | 0.6 | last meaningful line 0.3 h ago (237/1303 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i1-914398 | eco_20261123_224647_4153453-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i1t-3365017 | eco_20261124_010152_2867084-i1t | 5_2_route | 1.9 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | relec1122-ml-r6_00112d4e | relec1122-ml-r6_00112d4e | - | 2.8 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-rxsb_fill | relec1122-ml-rxsb_fill | gate.ys | 0.4 | last meaningful line 0.3 h ago (22052/22052 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | s81kvt2_xd_eq | s81kvt2_xd_eq | eq_0 | 0.4 | last meaningful line 0.0 h ago (546546/546547 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | so_1012971_ff_77334 | so_1012971_ff_77334 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (1034/1034 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | so_1012971_tt_77334 | so_1012971_tt_77334 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (1034/1034 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t12-3094848 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 2964 last 2964 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 7.4 | last meaningful line 2.8 h ago (5/5 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 2.9 | last meaningful line 2.8 h ago (5/5 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | otc-1882360-28079 | 1882360 | - | 2.5 |  | NO-DATA: no log found |  |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 6.7 | last meaningful line 2.8 h ago (5/5 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | prd-eco_20261123_152917_1693191-i1-910286 | eco_20261123_152917_1693191-i1 | 5_2_route | 3.5 | drt_violations best 715 last 715 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | so_3630241_ff_60152 | so_3630241_ff_60152 | signoff | 0.4 |  | NO-DATA: empty log |  |
| intel1 | so_3630241_tt_60152 | so_3630241_tt_60152 | signoff | 0.4 |  | NO-DATA: empty log |  |
| intel2 | dpkit-coll_ftm-2001372 | coll_ftm | 5_1_grt | 0.5 | repair_Remaining best 27817 last 27817 rows 22 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i2t-245032 | eco_20261123_051704_3678821-i2t | 5_2_route | 1.6 | last meaningful line 0.1 h ago (266/267 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2t-2973514 | eco_20261123_063813_234645-i2t | 5_2_route | 2.8 | drt_violations best 38098 last 38098 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 22.1 | drt_violations best 7483 last 10181 rows 18 | before-window best 15220, window best 7483 | PROGRESS: drt_violations improved 50.8 % in window |  |
| epyc2 | dpkit-cbf_q00__cl870de686-181856 | cbf_q00 | pregrt_ff_hold | 0.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-cbf_q01-3915852 | cbf_q01 | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-3883814 | cbn_q11 | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 24.8 | drt_violations best 1708 last 1708 rows 23 | before-window best 1743, window best 1708 | PROGRESS: drt_violations improved 2.0 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 27.0 | drt_violations best 8261 last 28775 rows 18 | before-window best 9239, window best 8261 | PROGRESS: drt_violations improved 10.6 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 23.6 | drt_violations best 39818 last 39818 rows 16 | before-window best 44158, window best 39818 | PROGRESS: drt_violations improved 9.8 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 24.0 | drt_violations best 47319 last 47319 rows 15 | before-window best 50150, window best 47319 | PROGRESS: drt_violations improved 5.6 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 24.7 | drt_violations best 50945 last 50945 rows 15 | before-window best 56454, window best 50945 | PROGRESS: drt_violations improved 9.8 % in window |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 52.0 | last meaningful line 1.0 h ago (646/646 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-cbf_q01_s2-3852085 | cbf_q01_s2 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 35.4 | drt_violations best 18 last 18 rows 56 | before-window best 20, window best 18 | PROGRESS: drt_violations improved 10.0 % in window |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 15.5 | repair_Violations best 12243 last 12243 rows 127 | before-window best 146313, window best 12243 | PROGRESS: repair_Violations improved 91.6 % in window |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 11.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 5_1_grt | 15.2 | grt_hold_TNS best 92.7 last 92.7 rows 8 | before-window best 5429.3, window best 92.7 | PROGRESS: grt_hold_TNS improved 98.3 % in window |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 22.9 | drt_violations best 15 last 18 rows 57 | before-window best 33, window best 15 | PROGRESS: drt_violations improved 54.5 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 38.2 | drt_violations best 15723 last 15723 rows 15 | before-window best 29547, window best 15723 | PROGRESS: drt_violations improved 46.8 % in window |  |
| intel1 | dpkit-native59-203599 | native59 | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 24.9 | drt_violations best 80382 last 80382 rows 12 | before-window best 89667, window best 80382 | PROGRESS: drt_violations improved 10.4 % in window |  |
