# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 18:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'GRT-LABEL': 2, 'YOUNG': 51, 'NO-DATA': 14, 'PROGRESS': 16}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 14.3 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (OPUS-FIX-KV-PV-R7 decid |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | 5_1_grt | 19.1 | grt rounds 2 overflow 5:13730 -> 10:13037 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | 5_1_grt | 17.9 | grt rounds 2 overflow 5:13850 -> 10:12903 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | prd-fin-222551 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q01-3915852 | cbf_q01 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5098/5098 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-3883814 | cbn_q11 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5344/5344 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 3_5_place_dp | 13.2 | last meaningful line 2.5 h ago (130/130 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-3917086 | slw_st_a_v2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (6213/6213 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | eco-abs-3907059 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-count-p1_bc-1254909 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (1019/1019 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i2-635372 | eco_20261122_190506_3875261-i2 | 5_2_route | 3.6 | drt_violations best 59 last 59 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i1-1373161 | eco_20261123_102841_2122262-i1 | 5_2_route | 2.9 | drt_violations best 42 last 42 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i1-1081003 | eco_20261123_103136_2028090-i1 | 5_2_route | 3.2 | drt_violations best 658 last 658 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 16.3 | drt_violations best 681573 last 681573 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 9.6 | last meaningful line 0.3 h ago (283/284 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-2781664 | dsdv_slice_kv512_C__t1 | 3_3_place_gp | 1.9 | overflow best 0.1977 last 0.1977 rows 80 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N-3976658 | hd_lep0N | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (184/184 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i1-2638994 | eco_20261123_171023_3055226-i1 | 5_2_route | 2.0 | last meaningful line 0.0 h ago (264/265 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795467809896538497-i1t-60038 | eco_retry_1795467809896538497-i1t | 5_2_route | 4.9 | last meaningful line 0.1 h ago (281/281 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | so_224480_ff_53442 | so_224480_ff_53442 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | so_224480_tt_53442 | so_224480_tt_53442 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-cbn-q01--clab6e67f2-grt-235276 | cbn-q01--clab6e67f2-grt | 3_5_place_dp | 0.2 | last meaningful line 0.2 h ago (144/144 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q01_s2-3852085 | cbf_q01_s2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (6804/6804 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q11__cl5cc92dfe-3437183 | cbn_q11 | 3_3_place_gp | 0.6 | overflow best 0.2123 last 0.2123 rows 34 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | pregrt_ff_hold | 12.5 | repair_TNS best 495634 last 495634 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-3963772 | sle_su_l1 | 3_3_place_gp | 0.4 | overflow best 0.4166 last 0.4166 rows 21 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slice_station__t37-196363 | slice_station__t37 | generate_abstract | 8.6 | last meaningful line 0.2 h ago (29/29 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t43-157875 | slice_station__t43 | generate_abstract | 8.6 | last meaningful line 0.2 h ago (29/29 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | otc-3510357-11704 | 3510357 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-3510838-21456 | 3510838 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-3683951-2218 | 3683951 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-3684795-23117 | 3684795 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-561267-20992 | 561267 | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (944/944 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i2t-3217904 | eco_20261123_120225_75582-i2t | 5_2_route | 2.8 | drt_violations best 35926 last 35926 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_140713_549985-i2t-3481758 | eco_20261123_140713_549985-i2t | 5_2_route | 2.7 | drt_violations best 2867 last 2867 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i2t-991032 | eco_20261123_163717_2005956-i2t | 5_2_route | 1.8 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_2_route | 9.3 | drt_violations best 107978 last 107978 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_233239_167282-i1-4008532 | eco_20261123_233239_167282-i1 | 5_2_route | 2.4 | drt_violations best 67 last 67 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | relec1122-ml-r6_afda1e9d | relec1122-ml-r6_afda1e9d | - | 1.8 |  | NO-DATA: no log found |  |
| epyc8 | relec1122-ml-r6_d5fde81d | relec1122-ml-r6_d5fde81d | - | 1.8 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-kv3_pc_v3-3969538 | kv3_pc_v3 | 2_1_floorplan | 0.3 | last meaningful line 0.0 h ago (1383/1383 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | pregrt_ff_hold | 11.8 | repair_TNS best 188478 last 188478 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_2_route | 21.0 | drt_violations best 99917 last 99917 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | otc-2424455-10223 | 2424455 | - | 2.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-3835478-23036 | 3835478 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc9 | otc-3835958-25037 | 3835958 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc9 | otc-3886321-7368 | 3886321 | route | 0.4 | last meaningful line 0.0 h ago (378/378 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | otc-3986451-19990 | 3986451 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-4018510-13029 | 4018510 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-4018784-22630 | 4018784 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-4152428-20565 | 4152428 | find | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-count-p1_bc-961257 | count-p1_bc | prd_count_p1_bc | 0.1 | last meaningful line 0.0 h ago (1019/1019 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-count-p1_tc-1096522 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i1t-1190624 | eco_20261123_224647_4153453-i1t | 5_2_route | 3.2 | drt_violations best 12218 last 12218 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i1t-3365017 | eco_20261124_010152_2867084-i1t | 5_2_route | 0.9 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | relec1122-ml-r6_00112d4e | relec1122-ml-r6_00112d4e | - | 1.8 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-rxsb_mp | relec1122-ml-rxsb_mp | gold.ys | 0.2 | last meaningful line 0.2 h ago (24933/24933 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-native59-203599 | native59 | pregrt_ff_hold | 3.1 | repair_TNS best 12876.5 last 12876.5 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | generate_abstract | 21.4 | last meaningful line 0.2 h ago (869/869 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 6.4 | last meaningful line 1.8 h ago (5/5 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 1.9 | last meaningful line 1.8 h ago (5/5 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | otc-1882360-28079 | 1882360 | - | 1.5 |  | NO-DATA: no log found |  |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 5.7 | last meaningful line 1.8 h ago (5/5 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | otc-2771016-25736 | 2771016 | w18_sta_ff | 0.4 | last meaningful line 0.2 h ago (142/142 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | prd-eco_20261123_152917_1693191-i1-910286 | eco_20261123_152917_1693191-i1 | 5_2_route | 2.5 | drt_violations best 715 last 715 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2524463 | coll_ftm | 5_2_route | 2.0 | drt_violations best 10172 last 10172 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i2t-245032 | eco_20261123_051704_3678821-i2t | 5_1_grt | 0.6 | last meaningful line 0.2 h ago (290/1331 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2t-2973514 | eco_20261123_063813_234645-i2t | 5_2_route | 1.8 | last meaningful line 0.1 h ago (285/286 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 21.1 | drt_violations best 7483 last 7483 rows 17 | before-window best 15220, window best 7483 | PROGRESS: drt_violations improved 50.8 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 23.8 | drt_violations best 1708 last 1708 rows 23 | before-window best 1794, window best 1708 | PROGRESS: drt_violations improved 4.8 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 26.0 | drt_violations best 8261 last 28775 rows 18 | before-window best 9239, window best 8261 | PROGRESS: drt_violations improved 10.6 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 22.6 | drt_violations best 40073 last 40073 rows 15 | before-window best 44158, window best 40073 | PROGRESS: drt_violations improved 9.3 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 23.0 | drt_violations best 47319 last 47319 rows 15 | before-window best 50150, window best 47319 | PROGRESS: drt_violations improved 5.6 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 23.7 | drt_violations best 50945 last 50945 rows 15 | before-window best 57558, window best 50945 | PROGRESS: drt_violations improved 11.5 % in window |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 51.0 | last meaningful line 0.2 h ago (646/646 lines) | PROGRESS: log still growing |  |
| epyc7 | prd-eco_20261123_184706_2375049-i2t-2475885 | eco_20261123_184706_2375049-i2t | 5_2_route | 2.2 | drt_violations best 0 last 0 rows 9 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 34.4 | drt_violations best 18 last 18 rows 56 | before-window best 21, window best 18 | PROGRESS: drt_violations improved 14.3 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 37.8 | drt_violations best 5551 last 5551 rows 24 | before-window best 6907, window best 5551 | PROGRESS: drt_violations improved 19.6 % in window |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 14.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 10.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 5_1_grt | 14.2 | repair_TNS best 588.046 last 588.046 rows 6 | before-window best 820.427, window best 588.046 | PROGRESS: repair_TNS improved 28.3 % in window |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 21.9 | drt_violations best 15 last 15 rows 55 | before-window best 205, window best 15 | PROGRESS: drt_violations improved 92.7 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 37.2 | drt_violations best 18221 last 18221 rows 14 | before-window best 31217, window best 18221 | PROGRESS: drt_violations improved 41.6 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 23.9 | drt_violations best 83289 last 83289 rows 11 | before-window best 90552, window best 83289 | PROGRESS: drt_violations improved 8.0 % in window |  |
