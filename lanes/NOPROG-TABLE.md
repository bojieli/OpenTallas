# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 16:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'GRT-LABEL': 1, 'YOUNG': 61, 'NO-DATA': 20, 'EXCLUDED': 2, 'PROGRESS': 17}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 49.7 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 13.3 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FABLE-FIX-KV-HG decides |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 30.0 | drt_violations best 2178 last 2640 rows 22 | before-window best 2178, window best 2640 | NO-PROGRESS: drt_violations best 2640 vs 2178 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | 5_1_grt | 17.8 | grt rounds 1 overflow 5:13730 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-2955109 | dsdv_slice_c1x_C__t8 | 5_1_grt | 11.4 | last meaningful line 1.8 h ago (211/219 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | otc-2238705-11711 | 2238705 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | prd-eco_20261122_223531_3628570-i3t-222551 | eco_20261122_223531_3628570-i3t | 5_2_route | 1.5 | last meaningful line 0.1 h ago (282/283 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl870de686-2748151 | cbf_q00 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 625 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-cbf_q00_s2-2865588 | cbf_q00_s2 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 96 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-cbf_q01-2745639 | cbf_q01 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 650 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-cbf_q01_s2-2756201 | cbf_q01_s2 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 479 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-cbn_q01__clab6e67f2-2756653 | cbn_q01 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 499 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-cbn_q01__cld9ff4c40-2752567 | cbn_q01 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 446 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-cbn_q01__cldd6ea846-2762595 | cbn_q01 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 427 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-2751622 | cbn_q11 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 578 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 3_5_place_dp | 11.9 | last meaningful line 1.3 h ago (130/130 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164248_3895049-i2-3950771 | eco_20261122_164248_3895049-i2 | 5_2_route | 3.3 | drt_violations best 24 last 24 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i2-1254909 | eco_20261122_181101_3945375-i2 | 5_2_route | 1.7 | last meaningful line 0.0 h ago (272/273 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i2-635372 | eco_20261122_190506_3875261-i2 | 5_2_route | 2.4 | last meaningful line 0.2 h ago (286/287 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i1-1373161 | eco_20261123_102841_2122262-i1 | 5_2_route | 1.6 | last meaningful line 0.0 h ago (259/259 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i1-1081003 | eco_20261123_103136_2028090-i1 | 5_2_route | 1.9 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 15.1 | drt_violations best 681573 last 681573 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 8.4 | last meaningful line 0.1 h ago (268/268 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-2781664 | dsdv_slice_kv512_C__t1 | 2_3_floorplan_tapcell | 0.6 | last meaningful line 0.1 h ago (32/32 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-1289562 | hd_lep0N_w | 5_1_grt | 2.1 | last meaningful line 0.1 h ago (251/1256 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | flowops-r3-ab-on | flowops-r3-ab-on | 3_5_place_dp | 0.7 | last meaningful line 0.1 h ago (120/120 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_160238_2681508-i2-2958749 | eco_20261123_160238_2681508-i2 | 5_1_grt | 0.4 | last meaningful line 0.4 h ago (255/1311 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i1-2638994 | eco_20261123_171023_3055226-i1 | 5_1_grt | 0.7 | last meaningful line 0.3 h ago (236/1278 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171842_3718765-i2t-1856110 | eco_20261123_171842_3718765-i2t | 5_2_route | 1.6 | drt_violations best 20200 last 20200 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_184706_2375049-i2t-2475885 | eco_20261123_184706_2375049-i2t | 5_2_route | 0.9 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795467809896538497-i1t-60038 | eco_retry_1795467809896538497-i1t | 5_1_grt | 3.6 | repair_Viol best 2444 last 2444 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | so_3323117_ff_10190 | so_3323117_ff_10190 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | so_3323117_tt_10190 | so_3323117_tt_10190 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 5_1_grt | 12.9 | grt_hold_TNS best 1479.7 last 1479.7 rows 5 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | pregrt_ff_hold | 11.2 | repair_TNS best 495634 last 495634 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-slice_station__t37-196363 | slice_station__t37 | 5_2_route | 7.3 | drt_violations best 32522 last 32522 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t49-194878 | slice_station__t49 | 6_report | 7.3 | last meaningful line 0.2 h ago (53/53 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | otc-1340688-20491 | 1340688 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-1713761-23608 | 1713761 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-1715296-6280 | 1715296 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-1757616-19459 | 1757616 | signoff | 0.2 | last meaningful line 0.2 h ago (3/3 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | otc-1907264-29655 | 1907264 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-1908543-16556 | 1908543 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261123_120225_75582-i2t-3217904 | eco_20261123_120225_75582-i2t | 5_2_route | 1.5 | last meaningful line 0.1 h ago (283/284 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_140713_549985-i2t-3481758 | eco_20261123_140713_549985-i2t | 5_2_route | 1.4 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i2t-991032 | eco_20261123_163717_2005956-i2t | 5_1_grt | 0.6 | last meaningful line 0.5 h ago (236/1769 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_2_route | 8.0 | last meaningful line 0.2 h ago (297/298 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_233239_167282-i1-4008532 | eco_20261123_233239_167282-i1 | 5_2_route | 1.2 | last meaningful line 0.2 h ago (250/251 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | relec1122-ml-r6_afda1e9d | relec1122-ml-r6_afda1e9d | - | 0.6 |  | NO-DATA: no log found |  |
| epyc8 | relec1122-ml-r6_d5fde81d | relec1122-ml-r6_d5fde81d | - | 0.6 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | pregrt_ff_hold | 10.6 | repair_TNS best 188478 last 188478 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_2_route | 19.8 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | otc-142944-22790 | 142944 | signoff | 3.2 | last meaningful line 3.1 h ago (3/3 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | otc-1679825-19413 | 1679825 | 5_2_route | 1.5 | drt_violations best 5161 last 5161 rows 2 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | otc-2109753-27146 | 2109753 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-2424455-10223 | 2424455 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-2552258-678 | 2552258 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-2552347-24357 | 2552347 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-2631760-16966 | 2631760 | route | 0.6 | last meaningful line 0.0 h ago (495/495 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | otc-3057555-12642 | 3057555 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-3094467-4568 | 3094467 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-3122549-17475 | 3122549 | extract | 0.0 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco-i2-3887394 | eco-i2 | 5_3_fillcell | 3.8 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i1-961257 | eco_20261123_190031_3093983-i1 | 5_2_route | 2.2 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i1t-1096522 | eco_20261123_224216_149959-i1t | 5_2_route | 2.0 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i1t-1190624 | eco_20261123_224647_4153453-i1t | 5_2_route | 1.9 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | relec1122-ml-r6_00112d4e | relec1122-ml-r6_00112d4e | - | 0.6 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-rxsb_goldslang | relec1122-ml-rxsb_goldslang | gate.ys | 0.7 | last meaningful line 0.5 h ago (22052/22052 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | so_2739001_ff_29711 | so_2739001_ff_29711 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc9 | so_2739001_tt_29711 | so_2739001_tt_29711 | signoff | 0.5 |  | NO-DATA: empty log |  |
| intel1 | dpkit-dsdv_slice_c3x_C__t1-142746 | dsdv_slice_c3x_C__t1 | 3_5_place_dp | 6.1 | last meaningful line 1.8 h ago (37/37 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-native59-203599 | native59 | pregrt_ff_hold | 1.9 | repair_TNS best 12876.5 last 12876.5 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | 5_2_route | 20.1 | drt_violations best 18737 last 18737 rows 3 | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 5.1 | last meaningful line 0.5 h ago (5/5 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 0.7 | last meaningful line 0.5 h ago (5/5 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | otc-1882360-28079 | 1882360 | - | 0.2 |  | NO-DATA: no log found |  |
| intel1 | otc-1945982-4115 | 1945982 | asbuilt.yosys | 0.2 | last meaningful line 0.0 h ago (135132/135132 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 4.4 | last meaningful line 0.5 h ago (5/5 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | prd-eco_20261123_130527_1956436-i1-1218759 | eco_20261123_130527_1956436-i1 | 5_2_route | 0.9 | last meaningful line 0.1 h ago (247/248 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | prd-eco_20261123_152917_1693191-i1-910286 | eco_20261123_152917_1693191-i1 | 5_2_route | 1.2 | last meaningful line 0.0 h ago (264/264 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2524463 | coll_ftm | 5_1_grt | 0.7 | repair_TNS best 17.396 last 17.396 rows 9 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-3559333 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (214/215 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-3482354 | kv3_io_ft | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | eco-abs-2733086 | eco-abs | generate_abstract | 0.6 | last meaningful line 0.4 h ago (1030/1030 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2t-2973514 | eco_20261123_063813_234645-i2t | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (255/689 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | otc-2254560-3315 | 2254560 | ot_bind_native_7d4bc5882447b2d9cdf93e3b | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | otc-2874939-25936 | 2874939 | asbuilt.yosys | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 12.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-serdes__t2-1856235 | serdes__t2 | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 19.6 | drt_violations best 9298 last 9298 rows 16 | before-window best 17052, window best 9298 | PROGRESS: drt_violations improved 45.5 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 22.5 | drt_violations best 1743 last 1888 rows 21 | before-window best 1814, window best 1743 | PROGRESS: drt_violations improved 3.9 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 24.8 | drt_violations best 8281 last 8281 rows 16 | before-window best 9667, window best 8281 | PROGRESS: drt_violations improved 14.3 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 21.4 | drt_violations best 40073 last 40073 rows 15 | before-window best 45446, window best 40073 | PROGRESS: drt_violations improved 11.8 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 21.8 | drt_violations best 47319 last 47319 rows 15 | before-window best 51322, window best 47319 | PROGRESS: drt_violations improved 7.8 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 22.4 | drt_violations best 54432 last 54432 rows 14 | before-window best 60407, window best 54432 | PROGRESS: drt_violations improved 9.9 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 33.1 | drt_violations best 20 last 20 rows 54 | before-window best 21, window best 20 | PROGRESS: drt_violations improved 4.8 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 36.5 | drt_violations best 5582 last 5582 rows 23 | before-window best 7590, window best 5582 | PROGRESS: drt_violations improved 26.5 % in window |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 9.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slice_station__t43-157875 | slice_station__t43 | 5_2_route | 7.4 | drt_violations best 0 last 0 rows 8 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 20.7 | drt_violations best 15 last 15 rows 55 | before-window best 2323, window best 15 | PROGRESS: drt_violations improved 99.4 % in window |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 16.7 | repair_Violations best 0 last 0 rows 18 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 36.0 | drt_violations best 18221 last 18221 rows 14 | before-window best 34800, window best 18221 | PROGRESS: drt_violations improved 47.6 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 22.6 | drt_violations best 88174 last 88174 rows 10 | before-window best 91811, window best 88174 | PROGRESS: drt_violations improved 4.0 % in window |  |
| intel2 | dpkit-slice_station__t12-3588285 | slice_station__t12 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
