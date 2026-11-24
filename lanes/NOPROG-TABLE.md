# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 17:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'GRT-LABEL': 2, 'YOUNG': 55, 'NO-DATA': 15, 'EXCLUDED': 1, 'PROGRESS': 13}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 13.8 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (OPUS-FIX-KV-PV-R7 decid |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 50.5 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 14.0 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FABLE-FIX-KV-HG decides |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | 5_1_grt | 18.6 | grt rounds 2 overflow 5:13730 -> 10:13037 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | 5_1_grt | 17.4 | grt rounds 1 overflow 5:13850 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-2955109 | dsdv_slice_c1x_C__t8 | 5_1_grt | 12.4 | last meaningful line 2.8 h ago (211/220 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc10 | otc-3235278-4374 | 3235278 | 4_1_cts | 0.0 | last meaningful line -0.0 h ago (1144/1144 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-3288198-1257 | 3288198 | pg.otrun | 0.0 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i3t-222551 | eco_20261122_223531_3628570-i3t | 5_2_route | 2.5 | drt_violations best 641 last 641 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl870de686-2748151 | cbf_q00 | 3_4_place_resized | 0.9 | last meaningful line 0.1 h ago (21/21 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00_s2-2865588 | cbf_q00_s2 | 3_4_place_resized | 0.8 | last meaningful line 0.1 h ago (21/21 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q01__clab6e67f2-2756653 | cbn_q01 | 3_4_place_resized | 0.9 | last meaningful line 0.1 h ago (20/20 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q01__cld9ff4c40-2752567 | cbn_q01 | 3_4_place_resized | 0.9 | last meaningful line 0.1 h ago (20/20 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q01__cldd6ea846-2762595 | cbn_q01 | 3_4_place_resized | 0.9 | last meaningful line 0.3 h ago (20/20 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 3_5_place_dp | 12.7 | last meaningful line 2.0 h ago (130/130 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i2-1254909 | eco_20261122_181101_3945375-i2 | 5_2_route | 2.5 | last meaningful line 0.2 h ago (284/285 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i2-635372 | eco_20261122_190506_3875261-i2 | 5_2_route | 3.1 | drt_violations best 59 last 59 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i1-1373161 | eco_20261123_102841_2122262-i1 | 5_2_route | 2.4 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i1-1081003 | eco_20261123_103136_2028090-i1 | 5_2_route | 2.7 | drt_violations best 658 last 658 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | prd-fin-3950771 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (1047/1047 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 15.8 | drt_violations best 681573 last 681573 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 9.1 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-2781664 | dsdv_slice_kv512_C__t1 | 3_3_place_gp | 1.4 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_160238_2681508-i2-2958749 | eco_20261123_160238_2681508-i2 | 5_2_route | 1.2 | last meaningful line 0.1 h ago (281/282 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i1-2638994 | eco_20261123_171023_3055226-i1 | 5_1_grt | 1.5 | last meaningful line 1.1 h ago (236/1386 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171842_3718765-i2t-1856110 | eco_20261123_171842_3718765-i2t | 5_3_fillcell | 2.3 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_184706_2375049-i2t-2475885 | eco_20261123_184706_2375049-i2t | 5_2_route | 1.7 | drt_violations best 47019 last 47019 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795467809896538497-i1t-60038 | eco_retry_1795467809896538497-i1t | 5_1_grt | 4.4 | repair_Viol best 2444 last 2444 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-cbf-q01-dump-3652694 | cbf-q01-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-cbf-q01-grt-3652694 | cbf-q01-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-cbf-q01-s2-grt-3446654 | cbf-q01-s2-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-cbn-q11--cl49ae4555-grt-3612126 | cbn-q11--cl49ae4555-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q11__cl5cc92dfe-3437183 | cbn_q11 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 410 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | pregrt_ff_hold | 12.0 | repair_TNS best 495634 last 495634 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-196363 | slice_station__t37 | generate_abstract | 8.1 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t43-157875 | slice_station__t43 | generate_abstract | 8.1 | last meaningful line 0.1 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__clf4365a62-3165840 | slw_st_a_v2 | 3_5_place_dp | 0.2 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-3510357-11704 | 3510357 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-3510838-21456 | 3510838 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261123_120225_75582-i2t-3217904 | eco_20261123_120225_75582-i2t | 5_2_route | 2.3 | last meaningful line 0.2 h ago (293/294 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_140713_549985-i2t-3481758 | eco_20261123_140713_549985-i2t | 5_2_route | 2.2 | drt_violations best 2867 last 2867 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i2t-991032 | eco_20261123_163717_2005956-i2t | 5_2_route | 1.3 | last meaningful line 0.1 h ago (264/265 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_2_route | 8.8 | drt_violations best 107978 last 107978 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_233239_167282-i1-4008532 | eco_20261123_233239_167282-i1 | 5_2_route | 1.9 | drt_violations best 67 last 67 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | relec1122-ml-mp_c01b49be73a8 | relec1122-ml-mp_c01b49be73a8 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | relec1122-ml-r6_afda1e9d | relec1122-ml-r6_afda1e9d | - | 1.3 |  | NO-DATA: no log found |  |
| epyc8 | relec1122-ml-r6_d5fde81d | relec1122-ml-r6_d5fde81d | - | 1.3 |  | NO-DATA: no log found |  |
| epyc8 | so_3260433_ff_77684 | so_3260433_ff_77684 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc8 | so_3260433_tt_77684 | so_3260433_tt_77684 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | pregrt_ff_hold | 11.3 | repair_TNS best 188478 last 188478 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_2_route | 20.5 | drt_violations best 99917 last 99917 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | otc-2424455-10223 | 2424455 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc9 | otc-2552258-678 | 2552258 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc9 | otc-3094467-4568 | 3094467 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc9 | otc-3183936-13858 | 3183936 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261123_190031_3093983-i1-961257 | eco_20261123_190031_3093983-i1 | 5_2_route | 2.9 | drt_violations best 191 last 191 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i1t-1096522 | eco_20261123_224216_149959-i1t | 5_2_route | 2.8 | drt_violations best 10066 last 10066 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i1t-1190624 | eco_20261123_224647_4153453-i1t | 5_2_route | 2.7 | drt_violations best 12218 last 12218 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i1t-3365017 | eco_20261124_010152_2867084-i1t | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (240/532 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-fin-3887394 | fin | 6_report | 0.3 | last meaningful line 0.0 h ago (285/285 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | relec1122-ml-r6_00112d4e | relec1122-ml-r6_00112d4e | - | 1.3 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-rxsb_goldslang | relec1122-ml-rxsb_goldslang | gold.ys | 1.5 | last meaningful line 0.3 h ago (24437/24437 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-native59-203599 | native59 | pregrt_ff_hold | 2.6 | repair_TNS best 12876.5 last 12876.5 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | 6_report | 20.9 | last meaningful line 0.1 h ago (912/912 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 5.9 | last meaningful line 1.3 h ago (5/5 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 1.4 | last meaningful line 1.3 h ago (5/5 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | otc-1882360-28079 | 1882360 | - | 1.0 |  | NO-DATA: no log found |  |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 5.2 | last meaningful line 1.3 h ago (5/5 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | prd-eco_20261123_152917_1693191-i1-910286 | eco_20261123_152917_1693191-i1 | 5_2_route | 2.0 | last meaningful line 0.1 h ago (275/276 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | prd-fin-1218759 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2524463 | coll_ftm | 5_2_route | 1.5 | last meaningful line 0.1 h ago (240/241 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-3482354 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5487 last 5487 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-3588285 | slice_station__t12 | 5_2_route | 0.9 | drt_violations best 2964 last 2964 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i2t-245032 | eco_20261123_051704_3678821-i2t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2t-2973514 | eco_20261123_063813_234645-i2t | 5_2_route | 1.3 | last meaningful line 0.1 h ago (279/280 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | otc-2874939-25936 | 2874939 | asbuilt.yosys | 1.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 20.6 | drt_violations best 9298 last 9298 rows 16 | before-window best 17052, window best 9298 | PROGRESS: drt_violations improved 45.5 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 23.3 | drt_violations best 1743 last 1784 rows 22 | before-window best 1794, window best 1743 | PROGRESS: drt_violations improved 2.8 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 25.5 | drt_violations best 8261 last 8261 rows 17 | before-window best 9667, window best 8261 | PROGRESS: drt_violations improved 14.5 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 22.1 | drt_violations best 40073 last 40073 rows 15 | before-window best 45446, window best 40073 | PROGRESS: drt_violations improved 11.8 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 22.5 | drt_violations best 47319 last 47319 rows 15 | before-window best 51322, window best 47319 | PROGRESS: drt_violations improved 7.8 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 23.2 | drt_violations best 50945 last 50945 rows 15 | before-window best 57558, window best 50945 | PROGRESS: drt_violations improved 11.5 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 33.9 | drt_violations best 18 last 18 rows 56 | before-window best 21, window best 18 | PROGRESS: drt_violations improved 14.3 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 37.3 | drt_violations best 5551 last 5551 rows 24 | before-window best 7590, window best 5551 | PROGRESS: drt_violations improved 26.9 % in window |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 10.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 5_1_grt | 13.7 | grt_hold_TNS best 820.4 last 820.4 rows 6 | before-window best 5429.3, window best 820.4 | PROGRESS: grt_hold_TNS improved 84.9 % in window |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 21.4 | drt_violations best 15 last 15 rows 55 | before-window best 382, window best 15 | PROGRESS: drt_violations improved 96.1 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 36.7 | drt_violations best 18221 last 18221 rows 14 | before-window best 31217, window best 18221 | PROGRESS: drt_violations improved 41.6 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 23.4 | drt_violations best 83289 last 83289 rows 11 | before-window best 90552, window best 83289 | PROGRESS: drt_violations improved 8.0 % in window |  |
