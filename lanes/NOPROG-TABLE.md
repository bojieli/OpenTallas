# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 00:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 5, 'GRT-LABEL': 3, 'YOUNG': 41, 'NO-DATA': 4, 'PROGRESS': 17}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-hd_lep0N-2158649 | hd_lep0N | 4_2_tapbal_grt | 4.2 | last meaningful line 3.0 h ago (48/54 lines) | UNSIGNABLE: 4_1_cts.json latest setup WNS -2236.42 ps (< -300, gate TT >= -42); job age 4.2  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-hd_lep0N-2864139 | hd_lep0N | 4_2_tapbal_grt | 3.5 | last meaningful line 2.3 h ago (48/58 lines) | UNSIGNABLE: 4_1_cts.json latest setup WNS -626.82 ps (< -300, gate TT >= -42); job age 3.5 h | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 57.0 | last meaningful line 6.0 h ago (646/646 lines) | NO-PROGRESS: no new non-iteration log line for 6.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc8 | dpkit-slw_hc0__cl1bc59e1c-85806 | slw_hc0 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 12.4 | last meaningful line 7.8 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 7.8 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 7.9 | last meaningful line 7.8 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 7.8 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 11.7 | last meaningful line 7.8 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 7.8 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc2 | dpkit-cbn_q11__cl49ae4555-3883814 | cbn_q11 | 5_1_grt | 6.3 | grt rounds 2 overflow 5:166101 -> 10:149070 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2194343 | cbx_q10 | 5_1_grt | 4.0 | grt rounds 2 overflow 5:29571 -> 10:27022 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | 5_1_grt | 20.5 | grt rounds 2 overflow 5:72617 -> 10:48604 | GRT-LABEL: DESIGN-FAIL: overflow 48604 at round 10 > 1000 |  |
| epyc10 | otc-2920169-12201 | 2920169 | signoff | 0.0 | last meaningful line 0.0 h ago (3/3 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | 5_1_grt | 5.9 | last meaningful line 0.2 h ago (280/1286 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-cbx_q10__cl89936551_h-2205260 | cbx_q10 | 5_1_grt | 4.0 | last meaningful line 0.2 h ago (267/1273 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 5.7 | last meaningful line 0.3 h ago (13632/13632 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-3016874 | slw_st_b_v1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (247/247 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pvc2ec5bfb-3040978 | slw_st_b_v2 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-3081708-30705 | 3081708 | ot_bind_native_65880f83d3582120795cb765 | 0.0 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i2t-3790618 | eco_20261123_102841_2122262-i2t | 5_2_route | 2.9 | drt_violations best 108 last 108 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | prd-fin-2487500 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-cbf-q00--cl1b5a6458-grt-3045641 | cbf-q00--cl1b5a6458-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-2841416 | cbn_q00 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (6564/6564 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-glue-2294683 | glue | pregrt_ff_hold | 0.8 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc7 | dpkit-native59-960093 | native59 | 3_5_place_dp | 1.7 | last meaningful line 0.1 h ago (110/110 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc2__clcc5e3e61-1959134 | sle_hc2 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (4862/4862 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5831/5831 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (4761/4761 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (5706/5706 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | tt_setup_repair | 0.6 | last meaningful line 0.0 h ago (399/399 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | pregrt_ff_hold | 0.8 | repair_TNS best 25094.5 last 25094.5 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | otc-3256351-22852 | 3256351 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261123_171023_3055226-i2t-1608228 | eco_20261123_171023_3055226-i2t | 5_2_route | 1.3 | last meaningful line 0.1 h ago (131/131 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-kv3-hgi-v4-grt-1949321 | kv3-hgi-v4-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q01__clab6e67f2-1043557 | cbn_q01 | 5_1_grt | 5.8 | last meaningful line 0.0 h ago (280/282 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | 5_1_grt | 5.6 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p5-206562 | kv3_hg_v1p5 | pregrt_ff_hold | 2.8 | repair_TNS best 809467 last 809467 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc8 | dpkit-kv3_hroot-1480922 | kv3_hroot | pregrt_ff_hold | 0.3 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-1531184 | sle_ctl | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (10349/10349 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-3737398 | slw_su_l1 | tt_setup_repair_grt | 4.8 | repair_Violations best 12 last 16 rows 55 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i2-3929535 | eco_20261123_120225_75582-i2 | 5_2_route | 3.0 | drt_violations best 174 last 174 rows 8 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i3t-3571186 | eco_20261123_163717_2005956-i3t | 5_2_route | 1.3 | drt_violations best 27752 last 27752 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1-1021701 | eco_20261123_164145_1995767-i1 | 5_2_route | 2.5 | drt_violations best 14491 last 14491 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | relec1122-ml-r6_afda1e9d | relec1122-ml-r6_afda1e9d | - | 7.8 |  | NO-DATA: no log found |  |
| epyc9 | eco-abs-1232466 | eco-abs | generate_abstract | 0.8 | last meaningful line 0.4 h ago (1030/1030 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | eco-abs-1815350 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.1 h ago (639/639 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco-i3-707330 | eco-i3 | 5_2_route | 1.4 | last meaningful line 0.1 h ago (302/303 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i2-860558 | eco_20261123_190031_3093983-i2 | 5_2_route | 1.2 | last meaningful line 0.0 h ago (266/267 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i2t-1506838 | eco_20261123_224216_149959-i2t | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (235/1284 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i1-3056982 | eco_20261124_010152_2867084-i1 | 5_2_route | 3.0 | drt_violations best 174 last 174 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t29__clc7772371-3101070 | slice_station__t29 | 5_2_route | 2.1 | last meaningful line 0.1 h ago (247/248 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3079865 | slice_station__t40 | 5_2_route | 2.1 | last meaningful line 0.1 h ago (255/256 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | otc-1882360-28079 | 1882360 | - | 7.5 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261123_191853_2879776-i1t-119447 | eco_20261123_191853_2879776-i1t | 5_2_route | 4.7 | drt_violations best 28 last 28 rows 5 | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-1560983 | kv3_io_ft | 5_2_route | 0.7 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-1610349 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (227/228 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i2-3270561 | eco_20261123_051704_3678821-i2 | 5_2_route | 2.1 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-714159 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 27.1 | drt_violations best 954 last 2403 rows 26 | before-window best 7483, window best 954 | PROGRESS: drt_violations improved 87.3 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 29.8 | drt_violations best 1617 last 2784 rows 28 | before-window best 1708, window best 1617 | PROGRESS: drt_violations improved 5.3 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 22.3 | drt_violations best 32761 last 32761 rows 7 | before-window best 681573, window best 32761 | PROGRESS: drt_violations improved 95.2 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 15.6 | drt_violations best 43810 last 43810 rows 7 | before-window best 391102, window best 43810 | PROGRESS: drt_violations improved 88.8 % in window |  |
| epyc7 | dpkit-sle_sc_v3-2137984 | sle_sc_v3 | pregrt_ff_hold | 0.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_stm_v3-2036429 | sle_stm_v3 | pregrt_ff_hold | 0.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 29.7 | drt_violations best 48746 last 48746 rows 17 | before-window best 50945, window best 48746 | PROGRESS: drt_violations improved 4.3 % in window |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | pregrt_ff_hold | 5.5 | repair_Violations best 50151 last 50151 rows 33 | before-window best 407310, window best 50151 | PROGRESS: repair_Violations improved 87.7 % in window |  |
| epyc8 | dpkit-cbx_q10__cl89936551-1293593 | cbx_q10 | pregrt_ff_hold | 4.1 | repair_Violations best 40555 last 40571 rows 124 | before-window best 417467, window best 40555 | PROGRESS: repair_Violations improved 90.3 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 40.4 | drt_violations best 17 last 19 rows 58 | before-window best 18, window best 17 | PROGRESS: drt_violations improved 5.6 % in window |  |
| epyc8 | dpkit-coll_core-1578986 | coll_core | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-197119 | sle_ctl | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-1287720 | slw_fe_v2 | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 43.2 | drt_violations best 7378 last 37623 rows 18 | before-window best 18221, window best 7378 | PROGRESS: drt_violations improved 59.5 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 29.9 | drt_violations best 78971 last 78971 rows 13 | before-window best 83289, window best 78971 | PROGRESS: drt_violations improved 5.2 % in window |  |
| intel2 | prd-eco_20261123_063813_234645-i2t-2973514 | eco_20261123_063813_234645-i2t | 5_2_route | 7.8 | drt_violations best 2 last 2 rows 42 | before-window best 38098, window best 2 | PROGRESS: drt_violations improved 100.0 % in window |  |
