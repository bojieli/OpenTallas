# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 16:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 3, 'GRT-LABEL': 1, 'YOUNG': 59, 'NO-DATA': 16, 'EXCLUDED': 1, 'PROGRESS': 18}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-coll_core-2130490 | coll_core | tt_setup_repair_grt | 8.4 | repair_Violations best 0 last 0 rows 15 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -393.86 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 49.0 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 12.8 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FABLE-FIX-KV-HG decides |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | tt_setup_repair | 10.7 | repair_Viol best 5967 last 5967 rows 18 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -542.96 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 16.2 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | 5_1_grt | 17.3 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-2955109 | dsdv_slice_c1x_C__t8 | 5_1_grt | 11.1 | last meaningful line 1.5 h ago (211/218 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i3t-222551 | eco_20261122_223531_3628570-i3t | 5_2_route | 1.2 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 3_5_place_dp | 11.2 | last meaningful line 0.5 h ago (130/130 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | otc-3577275-393 | 3577275 | - | 2.9 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261122_164248_3895049-i2-3950771 | eco_20261122_164248_3895049-i2 | 5_2_route | 2.5 | drt_violations best 24 last 24 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i2-1254909 | eco_20261122_181101_3945375-i2 | 5_1_grt | 1.0 | last meaningful line 0.6 h ago (237/1318 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i2-635372 | eco_20261122_190506_3875261-i2 | 5_2_route | 1.6 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i1-1373161 | eco_20261123_102841_2122262-i1 | 5_1_grt | 0.9 | last meaningful line 0.5 h ago (237/1321 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i1-1081003 | eco_20261123_103136_2028090-i1 | 5_2_route | 1.2 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 14.3 | last meaningful line 0.2 h ago (297/298 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_1_grt | 7.6 | last meaningful line 0.2 h ago (1314/2332 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_ctl-1292473 | hd_ctl | 5_2_route | 1.4 | drt_violations best 57352 last 57352 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | ndrx_h100_2614947 | ndrx_h100_2614947 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | ndrx_h60_2614739 | ndrx_h60_2614739 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171842_3718765-i2t-1856110 | eco_20261123_171842_3718765-i2t | 5_2_route | 0.8 | last meaningful line 0.1 h ago (275/276 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_184706_2375049-i2t-2475885 | eco_20261123_184706_2375049-i2t | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (254/733 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795467809896538497-i1t-60038 | eco_retry_1795467809896538497-i1t | 5_1_grt | 2.9 | repair_Viol best 2444 last 2444 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | relec1122-trx-cap20k | relec1122-trx-cap20k | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 5_1_grt | 12.4 | grt_hold_TNS best 2272.8 last 2272.8 rows 4 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-1128907 | sle_st_a_v1 | 1_synth | 0.0 | last meaningful line -0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-196363 | slice_station__t37 | 5_2_route | 6.8 | drt_violations best 32522 last 32522 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t43-157875 | slice_station__t43 | 5_2_route | 6.9 | drt_violations best 34560 last 34560 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t49-194878 | slice_station__t49 | 5_2_route | 6.8 | drt_violations best 1511 last 1511 rows 2 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cl39451317-3753261 | slice_station__t50 | generate_abstract | 7.1 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_fw_v3-3682147 | slw_fw_v3 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (351/351 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__clf4365a62-1075560 | slw_st_a_v2 | 2_1_floorplan | 0.0 | repair_Viol best 2348 last 2348 rows 78 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i2t-3217904 | eco_20261123_120225_75582-i2t | 5_2_route | 1.0 | last meaningful line 0.1 h ago (276/276 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_140713_549985-i2t-3481758 | eco_20261123_140713_549985-i2t | 5_2_route | 0.9 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i2t-991032 | eco_20261123_163717_2005956-i2t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_2_route | 7.5 | last meaningful line 0.2 h ago (293/294 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_233239_167282-i1-4008532 | eco_20261123_233239_167282-i1 | 5_2_route | 0.7 | last meaningful line 0.1 h ago (243/243 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | relec1122-ml-r6_afda1e9d | relec1122-ml-r6_afda1e9d | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | relec1122-ml-r6_d5fde81d | relec1122-ml-r6_d5fde81d | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | pregrt_ff_hold | 10.1 | repair_TNS best 188478 last 188478 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | generate_abstract | 17.3 | last meaningful line 0.4 h ago (1030/1030 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_2_route | 19.3 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | otc-142944-22790 | 142944 | signoff | 2.7 | last meaningful line 2.6 h ago (3/3 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | otc-1679825-19413 | 1679825 | 5_2_route | 1.0 | drt_violations best 38413 last 38413 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | otc-2109753-27146 | 2109753 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-2380387-5943 | 2380387 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc9 | otc-2424455-10223 | 2424455 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-2473991-12876 | 2473991 | insert | 0.2 | last meaningful line 0.2 h ago (20/20 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-2552105-4198 | 2552105 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-2552184-12839 | 2552184 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-2552258-678 | 2552258 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-2552347-24357 | 2552347 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-2552440-145 | 2552440 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-2607462-17665 | 2607462 | route | 0.1 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-2608734-28532 | 2608734 | route | 0.1 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-2608833-14438 | 2608833 | route | 0.1 | last meaningful line 0.0 h ago (115/115 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-2631760-16966 | 2631760 | route | 0.1 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco-i2-3887394 | eco-i2 | 5_2_route | 3.3 | drt_violations best 43 last 43 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i1-961257 | eco_20261123_190031_3093983-i1 | 5_2_route | 1.7 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i1t-1096522 | eco_20261123_224216_149959-i1t | 5_2_route | 1.5 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i1t-1190624 | eco_20261123_224647_4153453-i1t | 5_2_route | 1.4 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | relec1122-ml-r6_00112d4e | relec1122-ml-r6_00112d4e | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-rxsb_goldslang | relec1122-ml-rxsb_goldslang | gate.ys | 0.2 | last meaningful line 0.2 h ago (22052/22052 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c3x_C__t1-142746 | dsdv_slice_c3x_C__t1 | 3_5_place_dp | 5.6 | last meaningful line 1.3 h ago (37/37 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-2396125 | dsdv_slice_lepw_mu_C__t1 | 3_4_place_resized | 3.6 | last meaningful line 0.1 h ago (403/403 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-native59-203599 | native59 | 4_1_cts | 1.4 | last meaningful line 0.3 h ago (5516/5516 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | 5_2_route | 19.6 | drt_violations best 24944 last 24944 rows 2 | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel1 | dpkit-sle_hc1__cl22c1ff36__pve230954c-649220 | sle_hc1 | 3_3_place_gp | 1.0 | overflow best 0.1008 last 0.1008 rows 231 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-sle_hc1__cl22c1ff36__pve289215f-651145 | sle_hc1 | 3_3_place_gp | 1.0 | overflow best 0.2017 last 0.2017 rows 245 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | otc-1337536-28537 | 1337536 | - | 0.3 |  | NO-DATA: no log found |  |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 4.6 | last meaningful line 0.2 h ago (5/5 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 0.2 | last meaningful line 0.2 h ago (5/5 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 3.9 | last meaningful line 0.2 h ago (5/5 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_20261123_130527_1956436-i1-1218759 | eco_20261123_130527_1956436-i1 | 5_2_route | 0.4 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco_20261123_152917_1693191-i1-910286 | eco_20261123_152917_1693191-i1 | 5_1_grt | 0.7 | last meaningful line 0.3 h ago (242/1398 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-2523453 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-647484 | kv3_io_ft | 5_2_route | 1.2 | drt_violations best 5487 last 5487 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | eco-abs-2733086 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.1 h ago (1028/1028 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2t-2973514 | eco_20261123_063813_234645-i2t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | so_2889028_ff_53389 | so_2889028_ff_53389 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_2889028_tt_53389 | so_2889028_tt_53389 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | otc-1962159-6527 | 1962159 | ot_bind_native_f41170a9129d83b12aaad702 | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 12.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 19.3 | drt_violations best 9298 last 9298 rows 16 | before-window best 17052, window best 9298 | PROGRESS: drt_violations improved 45.5 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 21.8 | drt_violations best 1743 last 1888 rows 21 | before-window best 1983, window best 1743 | PROGRESS: drt_violations improved 12.1 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 24.0 | drt_violations best 8281 last 8281 rows 16 | before-window best 10583, window best 8281 | PROGRESS: drt_violations improved 21.8 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 20.6 | drt_violations best 40073 last 40073 rows 15 | before-window best 48060, window best 40073 | PROGRESS: drt_violations improved 16.6 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 21.0 | drt_violations best 48840 last 48840 rows 14 | before-window best 52820, window best 48840 | PROGRESS: drt_violations improved 7.5 % in window |  |
| epyc7 | dpkit-hd_lep0N_w-1289562 | hd_lep0N_w | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 21.7 | drt_violations best 54432 last 54432 rows 14 | before-window best 60407, window best 54432 | PROGRESS: drt_violations improved 9.9 % in window |  |
| epyc7 | prd-eco_20261123_160238_2681508-i2t-772332 | eco_20261123_160238_2681508-i2t | 5_2_route | 2.0 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 32.6 | drt_violations best 20 last 20 rows 54 | before-window best 21, window best 20 | PROGRESS: drt_violations improved 4.8 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 36.0 | drt_violations best 5582 last 5582 rows 23 | before-window best 7590, window best 5582 | PROGRESS: drt_violations improved 26.5 % in window |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 9.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 20.2 | drt_violations best 16 last 18 rows 53 | before-window best 33830, window best 16 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 35.5 | drt_violations best 24596 last 24596 rows 13 | before-window best 34800, window best 24596 | PROGRESS: drt_violations improved 29.3 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 22.1 | drt_violations best 88174 last 88174 rows 10 | before-window best 91811, window best 88174 | PROGRESS: drt_violations improved 4.0 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 19.4 | drt_violations best 37 last 37 rows 23 | before-window best 1960, window best 37 | PROGRESS: drt_violations improved 98.1 % in window |  |
| intel2 | dpkit-coll_ftm-2524463 | coll_ftm | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 29.5 | drt_violations best 2178 last 2967 rows 21 | before-window best 2223, window best 2178 | PROGRESS: drt_violations improved 2.0 % in window |  |
