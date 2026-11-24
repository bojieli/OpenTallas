# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 00:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 3, 'NO-PROGRESS': 5, 'GRT-LABEL': 4, 'YOUNG': 30, 'NO-DATA': 2, 'PROGRESS': 22}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-hd_lep0N-2158649 | hd_lep0N | 4_2_tapbal_grt | 5.0 | last meaningful line 3.8 h ago (48/55 lines) | UNSIGNABLE: 4_1_cts.json latest setup WNS -2236.42 ps (< -300, gate TT >= -42); job age 5.0  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-hd_lep0N-2864139 | hd_lep0N | 4_2_tapbal_grt | 4.2 | last meaningful line 3.0 h ago (48/59 lines) | UNSIGNABLE: 4_1_cts.json latest setup WNS -626.82 ps (< -300, gate TT >= -42); job age 4.2 h | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 57.7 | last meaningful line 6.8 h ago (646/646 lines) | NO-PROGRESS: no new non-iteration log line for 6.8 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc8 | dpkit-cbx_q10__cl89936551-1293593 | cbx_q10 | 5_1_grt | 4.8 | grt rounds 2 overflow 5:17738 -> 10:17579 | UNSIGNABLE: GRT overflow flat: overflow 17738 at iteration 5 -> 17579 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-slw_hc0__cl1bc59e1c-85806 | slw_hc0 | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 13.1 | last meaningful line 8.5 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 8.5 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 8.7 | last meaningful line 8.5 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 8.5 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 12.4 | last meaningful line 8.5 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 8.5 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | 5_1_grt | 6.6 | grt rounds 2 overflow 5:92167 -> 10:84774 | GRT-LABEL: DESIGN-FAIL: overflow 84774 at round 10 > 1000 |  |
| epyc8 | dpkit-cbn_q01__clab6e67f2-1043557 | cbn_q01 | 5_1_grt | 6.6 | grt rounds 2 overflow 5:90242 -> 10:85145 | GRT-LABEL: DESIGN-FAIL: overflow 85145 at round 10 > 1000 |  |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | 5_1_grt | 6.3 | grt rounds 2 overflow 5:87660 -> 10:82099 | GRT-LABEL: DESIGN-FAIL: overflow 82099 at round 10 > 1000 |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | 5_1_grt | 21.3 | grt rounds 2 overflow 5:72617 -> 10:48604 | GRT-LABEL: DESIGN-FAIL: overflow 48604 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-714159 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 2.7 | last meaningful line 0.2 h ago (257/1261 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2194343 | cbx_q10 | tt_setup_repair_grt | 4.7 | repair_Violations best 180 last 1719 rows 44 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i2-3480472 | eco_20261123_103136_2028090-i2 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (239/547 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00__cl1b5a6458-3305635 | cbf_q00 | pregrt_ff_hold | 0.7 | repair_TNS best 4963.76 last 4963.76 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-2841416 | cbn_q00 | tt_setup_repair | 1.1 | repair_Violations best 144 last 371 rows 24 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-native59-3518897 | native59 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (5396/5396 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | pregrt_ff_hold | 1.1 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | pregrt_ff_hold | 1.2 | repair_TNS best 7576.87 last 7576.87 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_stm_v3-2036429 | sle_stm_v3 | 5_1_grt | 1.7 | last meaningful line 0.0 h ago (278/280 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | 4_1_cts | 1.5 | last meaningful line 0.2 h ago (5737/5737 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i2t-1608228 | eco_20261123_171023_3055226-i2t | 5_2_route | 2.0 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p5-206562 | kv3_hg_v1p5 | pregrt_ff_hold | 3.6 | repair_TNS best 809467 last 809467 rows 1 | YOUNG: evidence 2.0 h < 2.5 h |  |
| epyc8 | dpkit-kv3_hgi_v4-2330527 | kv3_hgi_v4 | pregrt_ff_hold | 0.6 | repair_TNS best 18086.9 last 18086.9 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-1531184 | sle_ctl | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (10874/10874 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-3737398 | slw_su_l1 | tt_setup_repair_grt | 5.5 | repair_Violations best 12 last 16 rows 55 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1-1021701 | eco_20261123_164145_1995767-i1 | 5_2_route | 3.2 | drt_violations best 7 last 7 rows 10 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | prd-eco-i3-707330 | eco-i3 | 5_2_route | 2.1 | drt_violations best 2 last 2 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i2t-1506838 | eco_20261123_224216_149959-i2t | 5_2_route | 1.3 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i2t-2658135 | eco_20261123_224647_4153453-i2t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-fin-3056982 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | relec1122-ml-r6_22ee41ca | relec1122-ml-r6_22ee41ca | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | so_2422150_ff_11606 | so_2422150_ff_11606 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (645/645 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | so_2422150_tt_11606 | so_2422150_tt_11606 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (645/645 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t29__clc7772371-3101070 | slice_station__t29 | 5_2_route | 2.8 | drt_violations best 12491 last 12491 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3079865 | slice_station__t40 | 5_2_route | 2.9 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | otc-1670752-16443 | 1670752 | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | prd-fin-119447 | fin | 6_report | 0.3 | last meaningful line 0.1 h ago (908/908 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3177651 | coll_ftm | 5_1_grt | 0.7 | repair_TNS best 17.396 last 17.396 rows 6 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-123366 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | otc-450886-3386 | 450886 | grt | 0.1 | last meaningful line 0.1 h ago (35/36 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | otc-453881-4382 | 453881 | grt | 0.1 | last meaningful line 0.0 h ago (35/36 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | prd-fin-2973514 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 27.8 | drt_violations best 954 last 1081 rows 27 | before-window best 7483, window best 954 | PROGRESS: drt_violations improved 87.3 % in window |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 6.5 | last meaningful line 0.5 h ago (13635/13635 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 30.5 | drt_violations best 1617 last 2562 rows 29 | before-window best 1708, window best 1617 | PROGRESS: drt_violations improved 5.3 % in window |  |
| epyc2 | prd-eco_20261123_102841_2122262-i2t-3790618 | eco_20261123_102841_2122262-i2t | 5_2_route | 3.6 | drt_violations best 0 last 0 rows 4 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 23.1 | drt_violations best 30930 last 30930 rows 8 | before-window best 681573, window best 30930 | PROGRESS: drt_violations improved 95.5 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 16.4 | drt_violations best 42803 last 42803 rows 8 | before-window best 391102, window best 42803 | PROGRESS: drt_violations improved 89.1 % in window |  |
| epyc7 | dpkit-glue-2294683 | glue | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc2__clcc5e3e61-1959134 | sle_hc2 | pregrt_ff_hold | 1.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_sc_v3-2137984 | sle_sc_v3 | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 30.4 | drt_violations best 48746 last 160916 rows 18 | before-window best 50945, window best 48746 | PROGRESS: drt_violations improved 4.3 % in window |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | pregrt_ff_hold | 6.2 | repair_Violations best 48169 last 48187 rows 135 | before-window best 407310, window best 48169 | PROGRESS: repair_Violations improved 88.2 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 41.1 | drt_violations best 17 last 19 rows 58 | before-window best 18, window best 17 | PROGRESS: drt_violations improved 5.6 % in window |  |
| epyc8 | dpkit-coll_core-1578986 | coll_core | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-197119 | sle_ctl | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-1287720 | slw_fe_v2 | pregrt_ff_hold | 4.8 | repair_Violations best 0 last 0 rows 4 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | prd-eco_20261123_163717_2005956-i3t-3571186 | eco_20261123_163717_2005956-i3t | 5_2_route | 2.0 | drt_violations best 0 last 0 rows 8 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | prd-eco_20261123_190031_3093983-i2-860558 | eco_20261123_190031_3093983-i2 | 5_2_route | 2.0 | drt_violations best 0 last 0 rows 1 | PROGRESS: drt_violations reached 0 |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 44.0 | drt_violations best 7378 last 37623 rows 18 | before-window best 15723, window best 7378 | PROGRESS: drt_violations improved 53.1 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 30.6 | drt_violations best 76746 last 76746 rows 14 | before-window best 83289, window best 76746 | PROGRESS: drt_violations improved 7.9 % in window |  |
| intel2 | prd-eco_20261123_051704_3678821-i2-3270561 | eco_20261123_051704_3678821-i2 | 5_2_route | 2.9 | drt_violations best 0 last 0 rows 1 | PROGRESS: drt_violations reached 0 |  |
