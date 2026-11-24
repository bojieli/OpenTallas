# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 23:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 3, 'GRT-LABEL': 4, 'YOUNG': 45, 'NO-DATA': 2, 'PROGRESS': 18}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-hd_lep0N-2158649 | hd_lep0N | 4_2_tapbal_grt | 3.9 | last meaningful line 2.8 h ago (48/54 lines) | UNSIGNABLE: 4_1_cts.json latest setup WNS -2236.42 ps (< -300, gate TT >= -42); job age 3.9  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-hd_lep0N-2864139 | hd_lep0N | 4_2_tapbal_grt | 3.2 | last meaningful line 2.0 h ago (48/57 lines) | UNSIGNABLE: 4_1_cts.json latest setup WNS -626.82 ps (< -300, gate TT >= -42); job age 3.2 h | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 12.1 | last meaningful line 7.5 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 7.5 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 7.7 | last meaningful line 7.5 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 7.5 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 11.4 | last meaningful line 7.5 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 7.5 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc2 | dpkit-cbf_q11-2451203 | cbf_q11 | 5_1_grt | 3.5 | grt rounds 2 overflow 5:6370 -> 10:6108 | GRT-LABEL: DESIGN-FAIL: overflow 6108 at round 10 > 1000 |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-3883814 | cbn_q11 | 5_1_grt | 6.1 | grt rounds 2 overflow 5:166101 -> 10:149070 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2194343 | cbx_q10 | 5_1_grt | 3.7 | grt rounds 2 overflow 5:29571 -> 10:27022 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | 5_1_grt | 20.3 | grt rounds 2 overflow 5:72617 -> 10:48604 | GRT-LABEL: DESIGN-FAIL: overflow 48604 at round 10 > 1000 |  |
| epyc10 | dpkit-slice_station__t24__cl64811a5d-226587 | slice_station__t24 | 6_report | 2.1 | last meaningful line 0.0 h ago (76/76 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | 5_1_grt | 5.6 | last meaningful line 0.2 h ago (146/146 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-cbx_q10__cl89936551_h-2205260 | cbx_q10 | 5_1_grt | 3.7 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 5.5 | last meaningful line 0.2 h ago (13632/13632 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i2t-3790618 | eco_20261123_102841_2122262-i2t | 5_2_route | 2.6 | drt_violations best 108 last 108 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i2t-2487500 | eco_20261123_103136_2028090-i2t | 5_3_fillcell | 3.5 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00__cl1b5a6458-1537791 | cbf_q00 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (87/87 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-2841416 | cbn_q00 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5916/5916 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-glue-2294683 | glue | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5890/5890 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-native59-960093 | native59 | 3_4_place_resized | 1.5 | last meaningful line 0.1 h ago (334/334 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc2__clcc5e3e61-1959134 | sle_hc2 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (4856/4856 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5497/5497 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v3-2137984 | sle_sc_v3 | tt_setup_repair | 0.6 | last meaningful line 0.0 h ago (359/359 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (4573/4574 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (5678/5678 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (4320/4320 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4807/4807 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i2t-1608228 | eco_20261123_171023_3055226-i2t | 5_2_route | 1.0 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q01__clab6e67f2-1043557 | cbn_q01 | 5_1_grt | 5.6 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p5-206562 | kv3_hg_v1p5 | pregrt_ff_hold | 2.6 | repair_TNS best 809467 last 809467 rows 1 | YOUNG: evidence 1.0 h < 2.5 h |  |
| epyc8 | dpkit-kv3_hgi_v4-328592 | kv3_hgi_v4 | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (235/235 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hroot-1480922 | kv3_hroot | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (3090/3090 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-1531184 | sle_ctl | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-197119 | sle_ctl | pregrt_ff_hold | 2.6 | repair_TNS best 222728 last 222728 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-3737398 | slw_su_l1 | tt_setup_repair_grt | 4.5 | repair_Violations best 12 last 16 rows 55 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i2-3929535 | eco_20261123_120225_75582-i2 | 5_2_route | 2.8 | drt_violations best 19727 last 19727 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i3t-3571186 | eco_20261123_163717_2005956-i3t | 5_2_route | 1.0 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1-1021701 | eco_20261123_164145_1995767-i1 | 5_2_route | 2.2 | drt_violations best 14491 last 14491 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | relec1122-ml-r6_afda1e9d | relec1122-ml-r6_afda1e9d | - | 7.6 |  | NO-DATA: no log found |  |
| epyc9 | eco-abs-1232466 | eco-abs | generate_abstract | 0.6 | last meaningful line 0.1 h ago (1030/1030 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | otc-1574724-26329 | 1574724 | asbuilt.yosys | 0.2 | last meaningful line -0.0 h ago (135423/135423 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco-i3-707330 | eco-i3 | 5_2_route | 1.1 | last meaningful line 0.1 h ago (297/297 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i2-860558 | eco_20261123_190031_3093983-i2 | 5_2_route | 1.0 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i2t-1506838 | eco_20261123_224216_149959-i2t | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (172/172 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i1-3056982 | eco_20261124_010152_2867084-i1 | 5_2_route | 2.7 | drt_violations best 174 last 174 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | prd-fin-2378518 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (678/678 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t29__clc7772371-3101070 | slice_station__t29 | 5_2_route | 1.8 | last meaningful line 0.2 h ago (241/242 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3079865 | slice_station__t40 | 5_2_route | 1.9 | last meaningful line 0.0 h ago (252/252 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | fwcap_ab_base200 | fwcap_ab_base200 | 3_5_place_dp | 1.3 | last meaningful line 0.1 h ago (114/114 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | fwcap_ab_pf | fwcap_ab_pf | 3_5_place_dp | 1.3 | last meaningful line 0.2 h ago (114/114 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-1882360-28079 | 1882360 | - | 7.2 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261123_191853_2879776-i1t-119447 | eco_20261123_191853_2879776-i1t | 5_2_route | 4.4 | drt_violations best 17014 last 17014 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2729897 | coll_ftm | 5_3_fillcell | 2.2 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-2102787 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-1560983 | kv3_io_ft | 5_1_grt | 0.5 | last meaningful line 0.0 h ago (381/397 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-1610349 | slice_station__t12 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (202/202 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i2-3270561 | eco_20261123_051704_3678821-i2 | 5_2_route | 1.9 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-714159 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 1.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 26.8 | drt_violations best 1342 last 1342 rows 24 | before-window best 9298, window best 1342 | PROGRESS: drt_violations improved 85.6 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 29.5 | drt_violations best 1617 last 2784 rows 28 | before-window best 1708, window best 1617 | PROGRESS: drt_violations improved 5.3 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 22.1 | drt_violations best 32761 last 32761 rows 7 | before-window best 681573, window best 32761 | PROGRESS: drt_violations improved 95.2 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 15.4 | drt_violations best 43810 last 43810 rows 7 | before-window best 391102, window best 43810 | PROGRESS: drt_violations improved 88.8 % in window |  |
| epyc7 | dpkit-sle_stm_v3-2036429 | sle_stm_v3 | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 29.4 | drt_violations best 48746 last 48746 rows 17 | before-window best 50945, window best 48746 | PROGRESS: drt_violations improved 4.3 % in window |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 56.7 | last meaningful line 5.8 h ago (646/646 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | pregrt_ff_hold | 5.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | pregrt_ff_hold | 5.3 | repair_Violations best 36703 last 36719 rows 134 | before-window best 389181, window best 36703 | PROGRESS: repair_Violations improved 90.6 % in window |  |
| epyc8 | dpkit-cbx_q10__cl89936551-1293593 | cbx_q10 | pregrt_ff_hold | 3.8 | repair_Violations best 40568 last 40588 rows 85 | before-window best 417467, window best 40568 | PROGRESS: repair_Violations improved 90.3 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 40.1 | drt_violations best 17 last 19 rows 58 | before-window best 18, window best 17 | PROGRESS: drt_violations improved 5.6 % in window |  |
| epyc8 | dpkit-coll_core-1578986 | coll_core | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-1287720 | slw_fe_v2 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_hc0__cl1bc59e1c-85806 | slw_hc0 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 43.0 | drt_violations best 7378 last 37623 rows 18 | before-window best 18221, window best 7378 | PROGRESS: drt_violations improved 59.5 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 29.6 | drt_violations best 78971 last 78971 rows 13 | before-window best 83289, window best 78971 | PROGRESS: drt_violations improved 5.2 % in window |  |
| intel2 | prd-eco_20261123_063813_234645-i2t-2973514 | eco_20261123_063813_234645-i2t | 5_2_route | 7.5 | drt_violations best 2 last 9 rows 39 | before-window best 38098, window best 2 | PROGRESS: drt_violations improved 100.0 % in window |  |
