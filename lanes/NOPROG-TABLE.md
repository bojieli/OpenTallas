# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 02:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 3, 'NO-PROGRESS': 5, 'GRT-LABEL': 2, 'YOUNG': 42, 'NO-DATA': 4, 'PROGRESS': 11}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair_grt | 8.6 | repair_Violations best 0 last 0 rows 93 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -743.27 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-glue-2294683 | glue | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc7 | dpkit-sle_hc2__clcc5e3e61-1959134 | sle_hc2 | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc7 | dpkit-sle_sc_v3-2137984 | sle_sc_v3 | postcts_gate_FF | 3.6 | last meaningful line 0.0 h ago (23/23 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -322.20 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | tt_setup_repair_grt | 8.3 | repair_Violations best 0 last 0 rows 62 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -773.59 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 15.1 | last meaningful line 10.5 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 10.5 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 10.7 | last meaningful line 10.5 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 10.5 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 14.4 | last meaningful line 10.5 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 10.5 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | 5_1_grt | 8.2 | grt rounds 2 overflow 5:91995 -> 10:83281 | GRT-LABEL: DESIGN-FAIL: overflow 83281 at round 10 > 1000 |  |
| epyc8 | dpkit-kv3_hg_v1p2-1668089 | kv3_hg_v1p2 | 5_1_grt | 1.0 | grt rounds 2 overflow 5:72617 -> 10:48604 | GRT-LABEL: DESIGN-FAIL: overflow 48604 at round 10 > 1000 |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | 4_1_cts | 1.8 | last meaningful line 0.1 h ago (10776/10776 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i2-336844 | eco_20261123_102841_2122262-i2 | 5_2_route | 1.4 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i2-3480472 | eco_20261123_103136_2028090-i2 | 5_2_route | 2.4 | drt_violations best 130 last 130 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | admiring_tu | admiring_tu | ot_bind_native_9871385b1cff6b1af8552fdc | 0.0 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00__cl1b5a6458-3305635 | cbf_q00 | 5_1_grt | 2.7 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-native59-3518897 | native59 | pregrt_ff_hold | 2.6 | repair_TNS best 5344.07 last 5344.07 rows 1 | YOUNG: evidence 1.0 h < 2.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-1550300 | sle_sc_v1 | 3_3_place_gp | 0.9 | overflow best 0.3689 last 0.3689 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_1_grt | 3.1 | repair_Remaining best 141665 last 141665 rows 294 | YOUNG: stage 0.8 h < 1 h |  |
| epyc7 | dpkit-sle_sc_v3-1547847 | sle_sc_v3 | 3_3_place_gp | 0.9 | overflow best 0.2153 last 0.2153 rows 43 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-1592356 | sle_stm_v1 | 3_1_place_gp_skip_io | 0.9 | overflow best 0.4796 last 0.4796 rows 34 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-sle_stm_v3-1611503 | sle_stm_v3 | 3_3_place_gp | 0.8 | overflow best 0.2844 last 0.2979 rows 32 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-sle_stm_v3-2036429 | sle_stm_v3 | 5_2_route | 3.7 | last meaningful line 0.0 h ago (246/246 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__cl5ea486db-1547678 | sle_su_l1 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-1549720 | slw_sc_v2 | 3_3_place_gp | 0.9 | overflow best 0.4133 last 0.4133 rows 17 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_1_grt | 3.3 | last meaningful line 0.7 h ago (1300/1879 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-1552958 | slw_stm_v2 | 3_3_place_gp | 0.9 | overflow best 0.4921 last 0.4921 rows 11 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | 5_1_grt | 3.5 | last meaningful line 0.2 h ago (282/910 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | prd-count-p1_tc-1608228 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | trusting_germain | trusting_germain | native | 0.0 | last meaningful line 0.0 h ago (387/387 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-coll_core-1578986 | coll_core | 5_1_grt | 5.0 | last meaningful line 0.5 h ago (1298/2905 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-197119 | sle_ctl | 5_1_grt | 5.6 | last meaningful line 0.2 h ago (296/1302 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-1287720 | slw_fe_v2 | postcts_gate_TT | 6.8 | last meaningful line 0.0 h ago (1700/1700 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-3737398 | slw_su_l1 | tt_setup_repair_grt | 7.5 | repair_Violations best 12 last 16 rows 55 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i3t-3968210 | eco_20261123_120225_75582-i3t | 5_2_route | 1.9 | drt_violations best 36109 last 36109 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i3-662867 | eco_20261123_163717_2005956-i3 | 5_2_route | 1.5 | drt_violations best 19271 last 19271 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i2t-1761120 | eco_20261123_164145_1995767-i2t | 5_2_route | 1.0 | last meaningful line 0.0 h ago (283/284 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v3-3937139 | kv3_pv_v3 | 3_3_place_gp | 0.7 | overflow best 0.192 last 0.192 rows 42 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | otc-4170469-11881 | 4170469 | 4_1_cts | 0.6 | repair_Violations best 460 last 2981 rows 24 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | otc-588565-4626 | 588565 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-681048-17622 | 681048 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-684576-12290 | 684576 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261123_190031_3093983-i3t-46390 | eco_20261123_190031_3093983-i3t | 5_1_grt | 0.5 | last meaningful line 0.3 h ago (239/1408 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i2-702588 | eco_20261123_224216_149959-i2 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i2t-2658135 | eco_20261123_224647_4153453-i2t | 5_2_route | 2.0 | drt_violations best 559 last 559 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i2t-283529 | eco_20261124_010152_2867084-i2t | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (240/514 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | romwband-T-714059 | romwband-T | split_T | 0.1 | last meaningful line 0.0 h ago (1147/1147 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3079865 | slice_station__t40 | generate_abstract | 4.9 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | fwcap_ab_pfqn | fwcap_ab_pfqn | 3_4_place_resized | 1.1 | last meaningful line 0.2 h ago (346/346 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-1670752-16443 | 1670752 | - | 2.0 |  | NO-DATA: no log found |  |
| intel1 | otc-2194855-5583 | 2194855 | flow | 1.4 | repair_Violations best 4792 last 4792 rows 14 | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | otc-3467627-16977 | 3467627 | 3_3_place_gp | 0.2 | overflow best 0.6459 last 0.6459 rows 27 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | otc-3620687-32261 | 3620687 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (491/491 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-3657120-29357 | 3657120 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (223/223 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i1-1832688 | eco_20261123_191853_2879776-i1 | 5_2_route | 1.9 | last meaningful line 0.1 h ago (133/133 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-4018505 | slice_station__t12 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (109/109 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 1.9 | last meaningful line 0.2 h ago (285/286 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 29.8 | drt_violations best 784 last 784 rows 30 | before-window best 2939, window best 784 | PROGRESS: drt_violations improved 73.3 % in window |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 8.5 | last meaningful line 0.5 h ago (13932/13932 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-2841416 | cbn_q00 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 25.1 | drt_violations best 26552 last 26552 rows 10 | before-window best 131336, window best 26552 | PROGRESS: drt_violations improved 79.8 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 18.4 | drt_violations best 39072 last 39072 rows 10 | before-window best 129916, window best 39072 | PROGRESS: drt_violations improved 69.9 % in window |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | 5_1_grt | 3.2 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 32.4 | drt_violations best 48746 last 160916 rows 18 | before-window best 49778, window best 48746 | PROGRESS: drt_violations improved 2.1 % in window |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-1531184 | sle_ctl | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | otc-16187-7415 | 16187 | 4_1_cts | 0.6 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 32.6 | drt_violations best 76746 last 76746 rows 14 | before-window best 80382, window best 76746 | PROGRESS: drt_violations improved 4.5 % in window |  |
