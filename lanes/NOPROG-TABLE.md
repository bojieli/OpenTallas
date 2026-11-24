# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 16:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'YOUNG': 65, 'NO-DATA': 9, 'EXCLUDED': 1, 'PROGRESS': 18}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 49.0 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 12.5 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FABLE-FIX-KV-HG decides |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 15.9 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| intel1 | prd-eco_20261123_090657_914087-i1t-2682219 | eco_20261123_090657_914087-i1t | 5_1_grt | 6.6 | repair_Viol best 1637 last 1637 rows 1 | before-window best 1637, window best 1637 | NO-PROGRESS: repair_Viol best 1637 vs 1637 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-coll_core-2130490 | coll_core | tt_setup_repair_grt | 8.2 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-2955109 | dsdv_slice_c1x_C__t8 | 5_1_grt | 10.9 | last meaningful line 1.3 h ago (211/217 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | postcts_gate_FF | 12.2 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i3t-222551 | eco_20261122_223531_3628570-i3t | 5_2_route | 1.0 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
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
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 5_1_grt | 12.2 | grt_hold_TNS best 2272.8 last 2272.8 rows 4 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-196363 | slice_station__t37 | 5_2_route | 6.6 | drt_violations best 32522 last 32522 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t43-157875 | slice_station__t43 | 5_2_route | 6.6 | drt_violations best 34560 last 34560 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t49-194878 | slice_station__t49 | 5_2_route | 6.6 | drt_violations best 18812 last 18812 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cl39451317-3753261 | slice_station__t50 | 6_report | 6.9 | last meaningful line 0.0 h ago (77/77 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_fw_v3-3682147 | slw_fw_v3 | 3_3_place_gp | 0.6 | overflow best 0.1951 last 0.1951 rows 36 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | otc-314231-32281 | 314231 | signoff | 0.2 | last meaningful line 0.2 h ago (3/3 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | otc-334608-21385 | 334608 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i2t-3217904 | eco_20261123_120225_75582-i2t | 5_2_route | 0.8 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_140713_549985-i2t-3481758 | eco_20261123_140713_549985-i2t | 5_1_grt | 0.7 | last meaningful line 0.4 h ago (297/2027 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_2_route | 7.3 | last meaningful line 0.1 h ago (291/292 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_233239_167282-i1-4008532 | eco_20261123_233239_167282-i1 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (283/383 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | so_385414_ff_33327 | so_385414_ff_33327 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (559/559 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | so_385414_tt_33327 | so_385414_tt_33327 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (559/559 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | 5_1_grt | 17.1 | last meaningful line 0.0 h ago (155/155 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | pregrt_ff_hold | 9.8 | repair_TNS best 188478 last 188478 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | generate_abstract | 17.0 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_2_route | 19.0 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | otc-142944-22790 | 142944 | signoff | 2.5 | last meaningful line 2.3 h ago (3/3 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | otc-1679825-19413 | 1679825 | 5_2_route | 0.7 | last meaningful line 0.1 h ago (253/254 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | otc-1956063-24831 | 1956063 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (119/119 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-2109753-27146 | 2109753 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc9 | otc-2231168-20215 | 2231168 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-2374457-7366 | 2374457 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-2380387-5943 | 2380387 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-2388929-11075 | 2388929 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i2-3887394 | eco-i2 | 5_2_route | 3.0 | drt_violations best 43 last 43 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i1-961257 | eco_20261123_190031_3093983-i1 | 5_2_route | 1.4 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i1t-1096522 | eco_20261123_224216_149959-i1t | 5_2_route | 1.3 | last meaningful line 0.1 h ago (262/263 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i1t-1190624 | eco_20261123_224647_4153453-i1t | 5_2_route | 1.2 | last meaningful line 0.0 h ago (260/260 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | so_1839590_ff_86855 | so_1839590_ff_86855 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (779/779 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | so_1839590_tt_86855 | so_1839590_tt_86855 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (779/779 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
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
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2731145 | col_h10_r1__t1 | 5_2_route | 12.0 | drt_violations best 1472 last 1472 rows 11 | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-647484 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5487 last 5487 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-667796 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 2964 last 2964 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | eco-abs-2403328 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | prd-fin-811516 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (1067/1067 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | unruffled_grothendieck | unruffled_grothendieck | lec | 0.0 | LEC last write 0.0 h ago | YOUNG: evidence 0.0 h < 6 h |  |
| intel1 | otc-957965-24344 | 957965 | asbuilt.yosys | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 12.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 19.1 | drt_violations best 11282 last 11282 rows 15 | before-window best 17052, window best 11282 | PROGRESS: drt_violations improved 33.8 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 21.8 | drt_violations best 1743 last 1888 rows 21 | before-window best 1983, window best 1743 | PROGRESS: drt_violations improved 12.1 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 24.0 | drt_violations best 8281 last 8281 rows 16 | before-window best 10583, window best 8281 | PROGRESS: drt_violations improved 21.8 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 20.6 | drt_violations best 40073 last 40073 rows 15 | before-window best 48060, window best 40073 | PROGRESS: drt_violations improved 16.6 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 21.0 | drt_violations best 48840 last 48840 rows 14 | before-window best 52820, window best 48840 | PROGRESS: drt_violations improved 7.5 % in window |  |
| epyc7 | dpkit-hd_lep0N_w-1289562 | hd_lep0N_w | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 21.7 | drt_violations best 54432 last 54432 rows 14 | before-window best 60407, window best 54432 | PROGRESS: drt_violations improved 9.9 % in window |  |
| epyc7 | prd-eco_20261123_160238_2681508-i2t-772332 | eco_20261123_160238_2681508-i2t | 5_2_route | 2.0 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 32.4 | drt_violations best 20 last 20 rows 54 | before-window best 21, window best 20 | PROGRESS: drt_violations improved 4.8 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 35.8 | drt_violations best 5582 last 5582 rows 23 | before-window best 7732, window best 5582 | PROGRESS: drt_violations improved 27.8 % in window |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 8.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | 4_1_cts | 10.5 | last meaningful line 1.3 h ago (10349/10349 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 19.9 | drt_violations best 16 last 18 rows 53 | before-window best 33830, window best 16 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 35.0 | drt_violations best 24596 last 24596 rows 13 | before-window best 36675, window best 24596 | PROGRESS: drt_violations improved 32.9 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 21.6 | drt_violations best 88174 last 88174 rows 10 | before-window best 93635, window best 88174 | PROGRESS: drt_violations improved 5.8 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 18.9 | drt_violations best 37 last 37 rows 23 | before-window best 2273, window best 37 | PROGRESS: drt_violations improved 98.4 % in window |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 29.2 | drt_violations best 2178 last 2967 rows 21 | before-window best 2223, window best 2178 | PROGRESS: drt_violations improved 2.0 % in window |  |
