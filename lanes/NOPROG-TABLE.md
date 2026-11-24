# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 18:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'GRT-LABEL': 2, 'YOUNG': 50, 'NO-DATA': 7, 'PROGRESS': 18}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 14.8 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (OPUS-FIX-KV-PV-R7 decid |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | 5_1_grt | 19.6 | grt rounds 2 overflow 5:13730 -> 10:13037 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | 5_1_grt | 18.4 | grt rounds 2 overflow 5:13850 -> 10:12903 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | prd-eco_20261122_223531_3628570-i3-52746 | eco_20261122_223531_3628570-i3 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl870de686-181856 | cbf_q00 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5976/5976 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (7722/7722 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 0.2 | last meaningful line 0.2 h ago (38/38 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_io_ft-64810 | kv3_io_ft | 5_2_route | 0.5 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-3917086 | slw_st_a_v2 | 5_1_grt | 0.8 | last meaningful line 0.0 h ago (2108/2125 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | eco-abs-3907059 | eco-abs | generate_abstract | 0.8 | last meaningful line 0.4 h ago (1030/1030 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | eco-abs-399330 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.1 h ago (1028/1028 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-count-p1_tc-1081003 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i1-1373161 | eco_20261123_102841_2122262-i1 | 5_2_route | 3.4 | drt_violations best 42 last 42 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | prd-fin-635372 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (1009/1009 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 16.8 | drt_violations best 681573 last 681573 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 10.1 | drt_violations best 391102 last 391102 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-2781664 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 2.4 | last meaningful line 0.2 h ago (37/37 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-374468 | hd_lep0N | 3_1_place_gp_skip_io | 0.4 | overflow best 0.7487 last 0.7706 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N-3976658 | hd_lep0N | 3_3_place_gp | 0.9 | overflow best 0.0965 last 0.0965 rows 44 | YOUNG: stage 0.6 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N_w-391422 | hd_lep0N_w | 3_3_place_gp | 0.4 | overflow best 0.1331 last 0.1331 rows 39 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N_w-394036 | hd_lep0N_w | 3_3_place_gp | 0.4 | overflow best 0.6379 last 0.6379 rows 3 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i1-2638994 | eco_20261123_171023_3055226-i1 | 5_2_route | 2.5 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795467809896538497-i1t-60038 | eco_retry_1795467809896538497-i1t | 5_2_route | 5.4 | last meaningful line 0.2 h ago (286/287 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | prd-fin-2475885 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (34/34 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q01_s2-3852085 | cbf_q01_s2 | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (6845/6845 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q01__clab6e67f2-1043557 | cbn_q01 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (6573/6573 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q11__cl5cc92dfe-1712022 | cbn_q11 | postplace_setup | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | pregrt_ff_hold | 13.0 | repair_TNS best 495634 last 495634 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | otc-1565165-12570 | 1565165 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-1734118-12137 | 1734118 | signoff | 0.0 | last meaningful line 0.0 h ago (3/3 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-count-p1_tc-3481758 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-count-p1_tc-4008532 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i2t-3217904 | eco_20261123_120225_75582-i2t | 5_2_route | 3.3 | drt_violations best 35926 last 35926 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i2t-991032 | eco_20261123_163717_2005956-i2t | 5_2_route | 2.3 | drt_violations best 36131 last 36131 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_2_route | 9.8 | drt_violations best 107978 last 107978 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc8 | relec1122-ml-r6_afda1e9d | relec1122-ml-r6_afda1e9d | - | 2.3 |  | NO-DATA: no log found |  |
| epyc8 | relec1122-ml-r6_d5fde81d | relec1122-ml-r6_d5fde81d | - | 2.3 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | pregrt_ff_hold | 12.3 | repair_TNS best 188478 last 188478 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_2_route | 21.5 | drt_violations best 14340 last 14340 rows 2 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc9 | eco-abs-311412 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-2424455-10223 | 2424455 | - | 2.5 |  | NO-DATA: no log found |  |
| epyc9 | otc-3986451-19990 | 3986451 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-4018510-13029 | 4018510 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-503609-19427 | 503609 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (3610/3610 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-count-p1_bc-1190624 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco-i3t-51485 | eco-i3t | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (244/1272 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i1-456858 | eco_20261123_224216_149959-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i1t-3365017 | eco_20261124_010152_2867084-i1t | 5_2_route | 1.4 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | relec1122-ml-r6_00112d4e | relec1122-ml-r6_00112d4e | - | 2.3 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-rxsb_mp | relec1122-ml-rxsb_mp | gold.ys | 0.7 | last meaningful line 0.5 h ago (24933/24933 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | generate_abstract | 21.9 | last meaningful line 0.4 h ago (871/871 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t12-3094848 | slice_station__t12 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (202/202 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 6.9 | last meaningful line 2.3 h ago (5/5 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 2.4 | last meaningful line 2.3 h ago (5/5 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | otc-1882360-28079 | 1882360 | - | 2.0 |  | NO-DATA: no log found |  |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 6.2 | last meaningful line 2.3 h ago (5/5 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | prd-eco_20261123_152917_1693191-i1-910286 | eco_20261123_152917_1693191-i1 | 5_2_route | 3.0 | drt_violations best 715 last 715 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i2t-245032 | eco_20261123_051704_3678821-i2t | 5_2_route | 1.1 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2t-2973514 | eco_20261123_063813_234645-i2t | 5_2_route | 2.3 | last meaningful line 0.3 h ago (291/292 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 21.6 | drt_violations best 7483 last 10181 rows 18 | before-window best 15220, window best 7483 | PROGRESS: drt_violations improved 50.8 % in window |  |
| epyc2 | dpkit-cbf_q01-3915852 | cbf_q01 | pregrt_ff_hold | 0.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-3883814 | cbn_q11 | pregrt_ff_hold | 0.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 24.3 | drt_violations best 1708 last 1708 rows 23 | before-window best 1743, window best 1708 | PROGRESS: drt_violations improved 2.0 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 26.5 | drt_violations best 8261 last 28775 rows 18 | before-window best 9239, window best 8261 | PROGRESS: drt_violations improved 10.6 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 23.1 | drt_violations best 40073 last 40073 rows 15 | before-window best 44158, window best 40073 | PROGRESS: drt_violations improved 9.3 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 23.5 | drt_violations best 47319 last 47319 rows 15 | before-window best 50150, window best 47319 | PROGRESS: drt_violations improved 5.6 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 24.2 | drt_violations best 50945 last 50945 rows 15 | before-window best 56454, window best 50945 | PROGRESS: drt_violations improved 9.8 % in window |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 51.5 | last meaningful line 0.5 h ago (646/646 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 34.9 | drt_violations best 18 last 18 rows 56 | before-window best 20, window best 18 | PROGRESS: drt_violations improved 10.0 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 38.3 | drt_violations best 5551 last 5551 rows 24 | before-window best 6907, window best 5551 | PROGRESS: drt_violations improved 19.6 % in window |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 15.0 | repair_Violations best 14283 last 14283 rows 52 | before-window best 146313, window best 14283 | PROGRESS: repair_Violations improved 90.2 % in window |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 11.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 5_1_grt | 14.7 | grt_hold_TNS best 371.4 last 371.4 rows 7 | before-window best 5429.3, window best 371.4 | PROGRESS: grt_hold_TNS improved 93.2 % in window |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 22.4 | drt_violations best 15 last 15 rows 55 | before-window best 72, window best 15 | PROGRESS: drt_violations improved 79.2 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 37.7 | drt_violations best 15723 last 15723 rows 15 | before-window best 31217, window best 15723 | PROGRESS: drt_violations improved 49.6 % in window |  |
| intel1 | dpkit-native59-203599 | native59 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 24.4 | drt_violations best 83289 last 83289 rows 11 | before-window best 89667, window best 83289 | PROGRESS: drt_violations improved 7.1 % in window |  |
