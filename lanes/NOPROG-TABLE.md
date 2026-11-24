# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 00:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 5, 'GRT-LABEL': 4, 'YOUNG': 42, 'NO-DATA': 1, 'PROGRESS': 16}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-hd_lep0N-2158649 | hd_lep0N | 4_2_tapbal_grt | 4.5 | last meaningful line 3.3 h ago (48/54 lines) | UNSIGNABLE: 4_1_cts.json latest setup WNS -2236.42 ps (< -300, gate TT >= -42); job age 4.5  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-hd_lep0N-2864139 | hd_lep0N | 4_2_tapbal_grt | 3.7 | last meaningful line 2.5 h ago (48/58 lines) | UNSIGNABLE: 4_1_cts.json latest setup WNS -626.82 ps (< -300, gate TT >= -42); job age 3.7 h | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 57.2 | last meaningful line 6.3 h ago (646/646 lines) | NO-PROGRESS: no new non-iteration log line for 6.3 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc8 | dpkit-slw_hc0__cl1bc59e1c-85806 | slw_hc0 | pregrt_ff_hold | 4.8 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 12.6 | last meaningful line 8.0 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 8.0 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 8.2 | last meaningful line 8.0 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 8.0 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 11.9 | last meaningful line 8.0 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 8.0 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | 5_1_grt | 6.1 | grt rounds 2 overflow 5:92167 -> 10:84774 | GRT-LABEL: DESIGN-FAIL: overflow 84774 at round 10 > 1000 |  |
| epyc2 | dpkit-cbx_q10__cl89936551_h-2205260 | cbx_q10 | 5_1_grt | 4.2 | grt rounds 2 overflow 5:27566 -> 10:24464 | GRT-LABEL: DESIGN-FAIL: overflow 24464 at round 10 > 1000 |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2194343 | cbx_q10 | 5_1_grt | 4.2 | grt rounds 2 overflow 5:29571 -> 10:27022 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | 5_1_grt | 20.8 | grt rounds 2 overflow 5:72617 -> 10:48604 | GRT-LABEL: DESIGN-FAIL: overflow 48604 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-714159 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 2.2 | repair_TNS best 7205.55 last 7205.55 rows 1 | YOUNG: evidence 1.8 h < 2.5 h |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 6.0 | last meaningful line 0.2 h ago (13634/13634 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-3016874 | slw_st_b_v1 | 3_3_place_gp | 0.3 | overflow best 0.7627 last 0.7627 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_st_b_v2__pvc2ec5bfb-3040978 | slw_st_b_v2 | 3_3_place_gp | 0.3 | overflow best 0.7697 last 0.7697 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i2t-3790618 | eco_20261123_102841_2122262-i2t | 5_2_route | 3.1 | drt_violations best 108 last 108 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | prd-fin-2487500 | fin | 6_report | 0.3 | last meaningful line 0.1 h ago (1068/1068 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00__cl1b5a6458-3305635 | cbf_q00 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (6451/6451 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-2841416 | cbn_q00 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (6594/6594 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-glue-2294683 | glue | pregrt_ff_hold | 1.0 | repair_TNS best 6921.57 last 6921.57 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-native59-3518897 | native59 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5055/5055 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc2__clcc5e3e61-1959134 | sle_hc2 | tt_setup_measure | 1.2 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (5861/5861 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (4817/4817 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (5733/5733 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | pregrt_ff_hold | 1.0 | repair_TNS best 25094.5 last 25094.5 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i2t-1608228 | eco_20261123_171023_3055226-i2t | 5_2_route | 1.5 | last meaningful line 0.0 h ago (264/265 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q01__clab6e67f2-1043557 | cbn_q01 | 5_1_grt | 6.1 | last meaningful line 0.3 h ago (280/1290 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | 5_1_grt | 5.8 | grt_overflow best 524 last 524 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-cbx_q10__cl89936551-1293593 | cbx_q10 | 5_1_grt | 4.3 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p5-206562 | kv3_hg_v1p5 | pregrt_ff_hold | 3.1 | repair_TNS best 809467 last 809467 rows 1 | YOUNG: evidence 1.5 h < 2.5 h |  |
| epyc8 | dpkit-kv3_hgi_v4-2330527 | kv3_hgi_v4 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (4516/4517 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hroot-1480922 | kv3_hroot | 5_1_grt | 0.5 | last meaningful line 0.1 h ago (273/567 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-1531184 | sle_ctl | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (10817/10817 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-3737398 | slw_su_l1 | tt_setup_repair_grt | 5.0 | repair_Violations best 12 last 16 rows 55 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc8 | prd-count-p1_tc-3929535 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (62/62 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i3t-3571186 | eco_20261123_163717_2005956-i3t | 5_2_route | 1.5 | drt_violations best 27752 last 27752 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1-1021701 | eco_20261123_164145_1995767-i1 | 5_2_route | 2.7 | drt_violations best 14491 last 14491 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | eco-abs-1815350 | eco-abs | generate_abstract | 0.4 | last meaningful line 0.2 h ago (641/641 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-eco-i3-707330 | eco-i3 | 5_2_route | 1.6 | last meaningful line 0.2 h ago (306/307 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i2-860558 | eco_20261123_190031_3093983-i2 | 5_2_route | 1.5 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i2t-1506838 | eco_20261123_224216_149959-i2t | 5_2_route | 0.8 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i1-3056982 | eco_20261124_010152_2867084-i1 | 5_2_route | 3.2 | drt_violations best 174 last 174 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | so_2142964_ff_48255 | so_2142964_ff_48255 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (1034/1034 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | so_2142964_tt_48255 | so_2142964_tt_48255 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (1034/1034 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t29__clc7772371-3101070 | slice_station__t29 | 5_2_route | 2.3 | last meaningful line 0.2 h ago (251/252 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3079865 | slice_station__t40 | 5_2_route | 2.4 | last meaningful line 0.1 h ago (259/260 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | otc-1882360-28079 | 1882360 | - | 7.7 |  | NO-DATA: no log found |  |
| intel1 | prd-count-p1_tc-119447 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3177651 | coll_ftm | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-3176243 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (216/217 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-1560983 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5487 last 5487 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-1610349 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 2964 last 2964 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i2-3270561 | eco_20261123_051704_3678821-i2 | 5_2_route | 2.4 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 27.3 | drt_violations best 954 last 2403 rows 26 | before-window best 7483, window best 954 | PROGRESS: drt_violations improved 87.3 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 30.0 | drt_violations best 1617 last 2784 rows 28 | before-window best 1708, window best 1617 | PROGRESS: drt_violations improved 5.3 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 22.6 | drt_violations best 32761 last 32761 rows 7 | before-window best 681573, window best 32761 | PROGRESS: drt_violations improved 95.2 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 15.9 | drt_violations best 43810 last 43810 rows 7 | before-window best 391102, window best 43810 | PROGRESS: drt_violations improved 88.8 % in window |  |
| epyc7 | dpkit-sle_sc_v3-2137984 | sle_sc_v3 | pregrt_ff_hold | 1.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_stm_v3-2036429 | sle_stm_v3 | pregrt_ff_hold | 1.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | pregrt_ff_hold | 0.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 29.9 | drt_violations best 48746 last 160916 rows 18 | before-window best 50945, window best 48746 | PROGRESS: drt_violations improved 4.3 % in window |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | pregrt_ff_hold | 5.7 | repair_Violations best 48285 last 48307 rows 68 | before-window best 407310, window best 48285 | PROGRESS: repair_Violations improved 88.1 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 40.6 | drt_violations best 17 last 19 rows 58 | before-window best 18, window best 17 | PROGRESS: drt_violations improved 5.6 % in window |  |
| epyc8 | dpkit-coll_core-1578986 | coll_core | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-197119 | sle_ctl | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-1287720 | slw_fe_v2 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 43.5 | drt_violations best 7378 last 37623 rows 18 | before-window best 15723, window best 7378 | PROGRESS: drt_violations improved 53.1 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 30.1 | drt_violations best 78971 last 78971 rows 13 | before-window best 83289, window best 78971 | PROGRESS: drt_violations improved 5.2 % in window |  |
| intel2 | prd-eco_20261123_063813_234645-i2t-2973514 | eco_20261123_063813_234645-i2t | 5_2_route | 8.0 | drt_violations best 2 last 2 rows 42 | before-window best 38098, window best 2 | PROGRESS: drt_violations improved 100.0 % in window |  |
