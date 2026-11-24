# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 00:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 5, 'GRT-LABEL': 3, 'YOUNG': 42, 'NO-DATA': 8, 'PROGRESS': 17}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-hd_lep0N-2158649 | hd_lep0N | 4_2_tapbal_grt | 4.7 | last meaningful line 3.5 h ago (48/54 lines) | UNSIGNABLE: 4_1_cts.json latest setup WNS -2236.42 ps (< -300, gate TT >= -42); job age 4.7  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-hd_lep0N-2864139 | hd_lep0N | 4_2_tapbal_grt | 4.0 | last meaningful line 2.8 h ago (48/59 lines) | UNSIGNABLE: 4_1_cts.json latest setup WNS -626.82 ps (< -300, gate TT >= -42); job age 4.0 h | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 57.5 | last meaningful line 6.5 h ago (646/646 lines) | NO-PROGRESS: no new non-iteration log line for 6.5 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc8 | dpkit-slw_hc0__cl1bc59e1c-85806 | slw_hc0 | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 12.9 | last meaningful line 8.3 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 8.3 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 8.4 | last meaningful line 8.3 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 8.3 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 12.2 | last meaningful line 8.3 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 8.3 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | 5_1_grt | 6.4 | grt rounds 2 overflow 5:92167 -> 10:84774 | GRT-LABEL: DESIGN-FAIL: overflow 84774 at round 10 > 1000 |  |
| epyc8 | dpkit-cbn_q01__clab6e67f2-1043557 | cbn_q01 | 5_1_grt | 6.3 | grt rounds 2 overflow 5:90242 -> 10:85145 | GRT-LABEL: DESIGN-FAIL: overflow 85145 at round 10 > 1000 |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | 5_1_grt | 21.0 | grt rounds 2 overflow 5:72617 -> 10:48604 | GRT-LABEL: DESIGN-FAIL: overflow 48604 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-714159 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 2.4 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-3648206-13958 | 3648206 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | otc-3694318-2496 | 3694318 | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (369/369 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | qib_io2_fw2.kit | qib_io2_fw2.kit | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | qib_io2_stm2.kit | qib_io2_stm2.kit | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | qib_io2_stm2.plat | qib_io2_stm2.plat | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2194343 | cbx_q10 | tt_setup_repair_grt | 4.5 | repair_Viol best 651 last 651 rows 161 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 6.2 | last meaningful line 0.4 h ago (13634/13634 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-3016874 | slw_st_b_v1 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (79/79 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pvc2ec5bfb-3040978 | slw_st_b_v2 | 3_4_place_resized | 0.5 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-3659671-24678 | 3659671 | probe | 0.0 | last meaningful line 0.0 h ago (13/13 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i2t-3790618 | eco_20261123_102841_2122262-i2t | 5_2_route | 3.4 | drt_violations best 108 last 108 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i2-3480472 | eco_20261123_103136_2028090-i2 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00__cl1b5a6458-3305635 | cbf_q00 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (6518/6518 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-2841416 | cbn_q00 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (6788/6788 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-native59-3518897 | native59 | 4_1_cts | 0.3 | last meaningful line 0.2 h ago (5055/5055 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc2__clcc5e3e61-1959134 | sle_hc2 | pregrt_ff_hold | 1.5 | repair_TNS best 21158.5 last 21158.5 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (5869/5869 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (4940/4940 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | 4_1_cts | 1.3 | last meaningful line 0.2 h ago (5735/5735 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | hwest_wi_ff | hwest_wi_ff | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | hwest_wi_tt | hwest_wi_tt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | musing_newton | musing_newton | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (104/104 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i2t-1608228 | eco_20261123_171023_3055226-i2t | 5_2_route | 1.8 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | 5_1_grt | 6.1 | last meaningful line 0.2 h ago (280/1289 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-cbx_q10__cl89936551-1293593 | cbx_q10 | 5_1_grt | 4.6 | last meaningful line 0.2 h ago (267/1273 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p5-206562 | kv3_hg_v1p5 | pregrt_ff_hold | 3.3 | repair_TNS best 809467 last 809467 rows 1 | YOUNG: evidence 1.8 h < 2.5 h |  |
| epyc8 | dpkit-kv3_hgi_v4-2330527 | kv3_hgi_v4 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4822/4822 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hroot-1480922 | kv3_hroot | 5_1_grt | 0.8 | last meaningful line 0.1 h ago (677/701 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-1531184 | sle_ctl | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (10845/10845 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-3737398 | slw_su_l1 | tt_setup_repair_grt | 5.3 | repair_Violations best 12 last 16 rows 55 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i3t-3571186 | eco_20261123_163717_2005956-i3t | 5_2_route | 1.8 | drt_violations best 2308 last 2308 rows 2 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1-1021701 | eco_20261123_164145_1995767-i1 | 5_2_route | 3.0 | drt_violations best 14491 last 14491 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | prd-fin-3929535 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (168/168 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | eco-abs-1815350 | eco-abs | generate_abstract | 0.7 | last meaningful line 0.1 h ago (643/643 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | prd-eco-i3-707330 | eco-i3 | 5_2_route | 1.9 | last meaningful line 0.1 h ago (310/311 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i2-860558 | eco_20261123_190031_3093983-i2 | 5_2_route | 1.7 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i2t-1506838 | eco_20261123_224216_149959-i2t | 5_2_route | 1.0 | last meaningful line 0.0 h ago (263/263 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i1-3056982 | eco_20261124_010152_2867084-i1 | 5_3_fillcell | 3.5 | last meaningful line 0.0 h ago (12/12 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | so_2142964_ff_48255 | so_2142964_ff_48255 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | so_2142964_tt_48255 | so_2142964_tt_48255 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t29__clc7772371-3101070 | slice_station__t29 | 5_2_route | 2.6 | drt_violations best 12491 last 12491 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3079865 | slice_station__t40 | 5_2_route | 2.6 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | prd-fin-119447 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3177651 | coll_ftm | 5_1_grt | 0.5 | repair_Remaining best 27817 last 27817 rows 22 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-kv3_io_ft-1560983 | kv3_io_ft | 5_2_route | 1.2 | drt_violations best 5487 last 5487 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | prd-count-p1_tc-2973514 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i2-3270561 | eco_20261123_051704_3678821-i2 | 5_2_route | 2.6 | last meaningful line 0.1 h ago (280/281 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | so_4142336_ff_49295 | so_4142336_ff_49295 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_4142336_tt_49295 | so_4142336_tt_49295 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 27.6 | drt_violations best 954 last 2403 rows 26 | before-window best 7483, window best 954 | PROGRESS: drt_violations improved 87.3 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 30.3 | drt_violations best 1617 last 2562 rows 29 | before-window best 1708, window best 1617 | PROGRESS: drt_violations improved 5.3 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 22.8 | drt_violations best 30930 last 30930 rows 8 | before-window best 681573, window best 30930 | PROGRESS: drt_violations improved 95.5 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 16.1 | drt_violations best 42803 last 42803 rows 8 | before-window best 391102, window best 42803 | PROGRESS: drt_violations improved 89.1 % in window |  |
| epyc7 | dpkit-glue-2294683 | glue | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_sc_v3-2137984 | sle_sc_v3 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_stm_v3-2036429 | sle_stm_v3 | pregrt_ff_hold | 1.4 | repair_Violations best 0 last 0 rows 8 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | pregrt_ff_hold | 1.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 30.2 | drt_violations best 48746 last 160916 rows 18 | before-window best 50945, window best 48746 | PROGRESS: drt_violations improved 4.3 % in window |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | pregrt_ff_hold | 6.0 | repair_Violations best 48177 last 48200 rows 100 | before-window best 407310, window best 48177 | PROGRESS: repair_Violations improved 88.2 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 40.9 | drt_violations best 17 last 19 rows 58 | before-window best 18, window best 17 | PROGRESS: drt_violations improved 5.6 % in window |  |
| epyc8 | dpkit-coll_core-1578986 | coll_core | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-197119 | sle_ctl | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-1287720 | slw_fe_v2 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 43.7 | drt_violations best 7378 last 37623 rows 18 | before-window best 15723, window best 7378 | PROGRESS: drt_violations improved 53.1 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 30.4 | drt_violations best 76746 last 76746 rows 14 | before-window best 83289, window best 76746 | PROGRESS: drt_violations improved 7.9 % in window |  |
