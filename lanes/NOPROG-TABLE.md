# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 18:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'GRT-LABEL': 2, 'YOUNG': 54, 'NO-DATA': 10, 'PROGRESS': 21}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 15.0 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (OPUS-FIX-KV-PV-R7 decid |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | 5_1_grt | 19.8 | grt rounds 2 overflow 5:13730 -> 10:13037 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | 5_1_grt | 18.7 | grt rounds 2 overflow 5:13850 -> 10:12903 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | prd-eco_20261122_223531_3628570-i3-52746 | eco_20261122_223531_3628570-i3 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (235/1266 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl870de686-181856 | cbf_q00 | pregrt_ff_hold | 0.6 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (7922/7922 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 0.5 | last meaningful line 0.2 h ago (40/40 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_io_ft-64810 | kv3_io_ft | 5_2_route | 0.7 | last meaningful line 0.0 h ago (228/229 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-3917086 | slw_st_a_v2 | postcts_gate_TT | 1.0 | last meaningful line 0.0 h ago (467/467 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | eco-abs-399330 | eco-abs | generate_abstract | 0.4 | last meaningful line 0.3 h ago (1028/1028 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | eco-abs-789501 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.1 h ago (970/970 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i1-1373161 | eco_20261123_102841_2122262-i1 | 5_2_route | 3.6 | drt_violations best 42 last 42 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | prd-fin-1081003 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_684865_ff_72441 | so_684865_ff_72441 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | so_684865_tt_72441 | so_684865_tt_72441 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-hd-lep0N-grt-1055578 | hd-lep0N-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-hd-lep0N-w-grt-1130196 | hd-lep0N-w-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 17.1 | drt_violations best 681573 last 681573 rows 1 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 10.4 | drt_violations best 391102 last 391102 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-2781664 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 2.6 | last meaningful line 0.3 h ago (37/37 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-374468 | hd_lep0N | 3_3_place_gp | 0.6 | last meaningful line 0.1 h ago (47/47 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-1023502 | hd_lep0N_w | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2783/2783 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i1-2638994 | eco_20261123_171023_3055226-i1 | 5_2_route | 2.7 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_184706_2375049-i2-1000308 | eco_20261123_184706_2375049-i2 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795467809896538497-i1t-60038 | eco_retry_1795467809896538497-i1t | 5_2_route | 5.6 | last meaningful line 0.3 h ago (288/289 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (7488/7489 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q01__clab6e67f2-1043557 | cbn_q01 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (6630/6630 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (7603/7603 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q11__cl5cc92dfe-1712022 | cbn_q11 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (4962/4962 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | pregrt_ff_hold | 13.2 | repair_TNS best 495634 last 495634 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-2390497 | sle_su_l1 | postplace_setup | 0.0 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-2047894 | slw_fe_v2 | 2_1_floorplan | 0.2 | last meaningful line 0.1 h ago (85/85 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl1bc59e1c-2142625 | slw_hc0 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (420/420 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-1565165-12570 | 1565165 | signoff | 0.3 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | otc-1734118-12137 | 1734118 | signoff | 0.3 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i2t-3217904 | eco_20261123_120225_75582-i2t | 5_2_route | 3.5 | drt_violations best 35926 last 35926 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i2t-991032 | eco_20261123_163717_2005956-i2t | 5_2_route | 2.6 | drt_violations best 36131 last 36131 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_2_route | 10.0 | drt_violations best 107978 last 107978 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc8 | prd-fin-3481758 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-fin-4008532 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (47/47 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | relec1122-ml-r6_afda1e9d | relec1122-ml-r6_afda1e9d | - | 2.6 |  | NO-DATA: no log found |  |
| epyc8 | relec1122-ml-r6_d5fde81d | relec1122-ml-r6_d5fde81d | - | 2.6 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | pregrt_ff_hold | 12.6 | repair_TNS best 188478 last 188478 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | eco-abs-311412 | eco-abs | generate_abstract | 0.5 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | otc-2424455-10223 | 2424455 | - | 2.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-3986451-19990 | 3986451 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-503609-19427 | 503609 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (4062/4062 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | otc-694182-22270 | 694182 | route | 0.1 | last meaningful line 0.0 h ago (204/204 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-790184-14153 | 790184 | route | 0.0 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco-i3t-51485 | eco-i3t | 5_2_route | 0.7 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i1t-3365017 | eco_20261124_010152_2867084-i1t | 5_2_route | 1.7 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | prd-fin-1190624 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (1068/1068 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | relec1122-ml-r6_00112d4e | relec1122-ml-r6_00112d4e | - | 2.6 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-rxsb_fill | relec1122-ml-rxsb_fill | gate.ys | 0.1 | last meaningful line 0.1 h ago (22052/22052 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | s81kvt2_xd_eq | s81kvt2_xd_eq | pre_old_0 | 0.1 | last meaningful line 0.1 h ago (435/435 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t12-3094848 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (227/228 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 7.1 | last meaningful line 2.5 h ago (5/5 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 2.7 | last meaningful line 2.5 h ago (5/5 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | otc-1882360-28079 | 1882360 | - | 2.2 |  | NO-DATA: no log found |  |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 6.4 | last meaningful line 2.5 h ago (5/5 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | prd-eco_20261123_152917_1693191-i1-910286 | eco_20261123_152917_1693191-i1 | 5_2_route | 3.2 | drt_violations best 715 last 715 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | so_3630241_ff_60152 | so_3630241_ff_60152 | signoff | 0.2 |  | NO-DATA: empty log |  |
| intel1 | so_3630241_tt_60152 | so_3630241_tt_60152 | signoff | 0.2 |  | NO-DATA: empty log |  |
| intel2 | dpkit-coll_ftm-2001372 | coll_ftm | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-1999756 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (216/217 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i2t-245032 | eco_20261123_051704_3678821-i2t | 5_2_route | 1.4 | last meaningful line 0.0 h ago (263/263 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2t-2973514 | eco_20261123_063813_234645-i2t | 5_2_route | 2.5 | drt_violations best 38098 last 38098 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 21.8 | drt_violations best 7483 last 10181 rows 18 | before-window best 15220, window best 7483 | PROGRESS: drt_violations improved 50.8 % in window |  |
| epyc2 | dpkit-cbf_q01-3915852 | cbf_q01 | pregrt_ff_hold | 1.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-3883814 | cbn_q11 | pregrt_ff_hold | 1.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 24.5 | drt_violations best 1708 last 1708 rows 23 | before-window best 1743, window best 1708 | PROGRESS: drt_violations improved 2.0 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 26.8 | drt_violations best 8261 last 28775 rows 18 | before-window best 9239, window best 8261 | PROGRESS: drt_violations improved 10.6 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 23.4 | drt_violations best 40073 last 40073 rows 15 | before-window best 44158, window best 40073 | PROGRESS: drt_violations improved 9.3 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 23.8 | drt_violations best 47319 last 47319 rows 15 | before-window best 50150, window best 47319 | PROGRESS: drt_violations improved 5.6 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 24.4 | drt_violations best 50945 last 50945 rows 15 | before-window best 56454, window best 50945 | PROGRESS: drt_violations improved 9.8 % in window |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 51.7 | last meaningful line 0.8 h ago (646/646 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-cbf_q01_s2-3852085 | cbf_q01_s2 | tt_setup_repair | 1.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 35.1 | drt_violations best 18 last 18 rows 56 | before-window best 20, window best 18 | PROGRESS: drt_violations improved 10.0 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 38.5 | drt_violations best 5268 last 5268 rows 25 | before-window best 6907, window best 5268 | PROGRESS: drt_violations improved 23.7 % in window |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 15.3 | repair_Violations best 13009 last 13009 rows 89 | before-window best 146313, window best 13009 | PROGRESS: repair_Violations improved 91.1 % in window |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 11.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 5_1_grt | 14.9 | repair_TNS best 225.923 last 225.923 rows 6 | before-window best 371.372, window best 225.923 | PROGRESS: repair_TNS improved 39.2 % in window |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 22.7 | drt_violations best 15 last 18 rows 57 | before-window best 36, window best 15 | PROGRESS: drt_violations improved 58.3 % in window |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_2_route | 21.8 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | prd-eco_20261123_224216_149959-i1-456858 | eco_20261123_224216_149959-i1 | 5_1_grt | 0.3 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 38.0 | drt_violations best 15723 last 15723 rows 15 | before-window best 31217, window best 15723 | PROGRESS: drt_violations improved 49.6 % in window |  |
| intel1 | dpkit-native59-203599 | native59 | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 24.6 | drt_violations best 83289 last 83289 rows 11 | before-window best 89667, window best 83289 | PROGRESS: drt_violations improved 7.1 % in window |  |
