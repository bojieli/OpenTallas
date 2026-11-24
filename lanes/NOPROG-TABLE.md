# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 02:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 3, 'NO-PROGRESS': 3, 'GRT-LABEL': 2, 'YOUNG': 42, 'NO-DATA': 5, 'PROGRESS': 16}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair_grt | 8.1 | repair_Violations best 854 last 854 rows 58 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -743.27 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-sle_sc_v3-2137984 | sle_sc_v3 | tt_setup_repair_grt | 3.1 | last meaningful line 0.0 h ago (21/21 lines) | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -372.75 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | tt_setup_repair_grt | 7.8 | repair_Viol best 962 last 962 rows 9 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -773.59 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 14.6 | last meaningful line 10.0 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 10.0 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 10.2 | last meaningful line 10.0 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 10.0 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 13.9 | last meaningful line 10.0 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 10.0 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | 5_1_grt | 7.7 | grt rounds 2 overflow 5:91995 -> 10:83281 | GRT-LABEL: DESIGN-FAIL: overflow 83281 at round 10 > 1000 |  |
| epyc8 | dpkit-kv3_hgi_v4-2330527 | kv3_hgi_v4 | 5_1_grt | 2.1 | grt rounds 2 overflow 5:29428 -> 10:18921 | GRT-LABEL: DESIGN-FAIL: overflow 18921 at round 10 > 1000 |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | 4_1_cts | 1.3 | last meaningful line 0.2 h ago (10752/10752 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i2-336844 | eco_20261123_102841_2122262-i2 | 5_1_grt | 0.9 | last meaningful line 0.5 h ago (237/1322 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i2-3480472 | eco_20261123_103136_2028090-i2 | 5_2_route | 1.9 | last meaningful line 0.1 h ago (280/281 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00__cl1b5a6458-3305635 | cbf_q00 | pregrt_ff_hold | 2.2 | repair_Violations best 13548 last 13548 rows 14 | YOUNG: evidence 1.5 h < 2.5 h |  |
| epyc7 | dpkit-native59-3518897 | native59 | pregrt_ff_hold | 2.1 | repair_TNS best 5344.07 last 5344.07 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-1550300 | sle_sc_v1 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v3-1547847 | sle_sc_v3 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-1592356 | sle_stm_v1 | synth_odb_v | 0.4 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-1611503 | sle_stm_v3 | 2_1_floorplan | 0.3 | last meaningful line 0.0 h ago (417/417 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-2036429 | sle_stm_v3 | tt_setup_measure_grt | 3.2 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__cl5ea486db-1547678 | sle_su_l1 | 3_2_place_iop | 0.4 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-1549720 | slw_sc_v2 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-1552958 | slw_stm_v2 | synth_odb_v | 0.4 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | 5_1_grt | 3.0 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | happy_carver | happy_carver | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (104/104 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-1668089 | kv3_hg_v1p2 | pregrt_ff_hold | 0.5 | repair_Violations best 325 last 412 rows 13 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-1531184 | sle_ctl | pregrt_ff_hold | 2.5 | repair_TNS best 234906 last 234906 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-197119 | sle_ctl | 5_1_grt | 5.1 | last meaningful line 0.0 h ago (163/163 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-1287720 | slw_fe_v2 | postcts_gate_TT | 6.3 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-3737398 | slw_su_l1 | tt_setup_repair_grt | 7.0 | repair_Violations best 12 last 16 rows 55 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i3t-3968210 | eco_20261123_120225_75582-i3t | 5_2_route | 1.4 | last meaningful line 0.1 h ago (291/292 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i3-662867 | eco_20261123_163717_2005956-i3 | 5_2_route | 1.0 | last meaningful line 0.0 h ago (276/277 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i2t-1761120 | eco_20261123_164145_1995767-i2t | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (261/936 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v3-3937139 | kv3_pv_v3 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8098 last 0.8098 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | otc-16187-7415 | 16187 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-3997058-32401 | 3997058 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-4081870-29819 | 4081870 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-4163095-26958 | 4163095 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-4170469-11881 | 4170469 | 4_1_cts | 0.1 | repair_Violations best 35903 last 35903 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | prd-count-p1_tc-1506838 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i3t-46390 | eco_20261123_190031_3093983-i3t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i2t-2658135 | eco_20261123_224647_4153453-i2t | 5_2_route | 1.5 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | relec1122-ml-r6_22ee41ca | relec1122-ml-r6_22ee41ca | - | 1.6 |  | NO-DATA: no log found |  |
| epyc9 | romdrc-T-4024674 | romdrc-T | split_T | 0.2 | last meaningful line 0.0 h ago (3863/3863 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | so_3761956_ff_99226 | so_3761956_ff_99226 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (1034/1034 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | so_3761956_tt_99226 | so_3761956_tt_99226 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (1034/1034 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3079865 | slice_station__t40 | 5_2_route | 4.4 | drt_violations best 2525 last 2525 rows 2 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | fwcap_ab_pfqn | fwcap_ab_pfqn | 3_3_place_gp | 0.6 | overflow best 0.3363 last 0.3363 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | otc-1670752-16443 | 1670752 | - | 1.5 |  | NO-DATA: no log found |  |
| intel1 | otc-2194855-5583 | 2194855 | flow | 0.9 | last meaningful line 0.0 h ago (2595/2595 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | otc-2414738-28743 | 2414738 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (3819/3819 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i1-1832688 | eco_20261123_191853_2879776-i1 | 5_1_grt | 1.4 | last meaningful line 0.9 h ago (239/1495 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-3364200 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | otc-3924124-23451 | 3924124 | signoff | 0.0 | last meaningful line 0.0 h ago (3/3 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 1.4 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | so_3656574_ff_30061 | so_3656574_ff_30061 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (1034/1034 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | so_3656574_tt_30061 | so_3656574_tt_30061 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (1034/1034 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 29.3 | drt_violations best 784 last 784 rows 30 | before-window best 2939, window best 784 | PROGRESS: drt_violations improved 73.3 % in window |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 8.0 | last meaningful line 0.1 h ago (13932/13932 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-2841416 | cbn_q00 | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 24.6 | drt_violations best 26552 last 26552 rows 10 | before-window best 186589, window best 26552 | PROGRESS: drt_violations improved 85.8 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 17.9 | drt_violations best 39072 last 39072 rows 10 | before-window best 391102, window best 39072 | PROGRESS: drt_violations improved 90.0 % in window |  |
| epyc7 | dpkit-glue-2294683 | glue | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc2__clcc5e3e61-1959134 | sle_hc2 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_1_grt | 2.6 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | pregrt_ff_hold | 2.7 | repair_Violations best 0 last 0 rows 11 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_1_grt | 2.8 | grt_overflow best 0 last 23 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 31.9 | drt_violations best 48746 last 160916 rows 18 | before-window best 49778, window best 48746 | PROGRESS: drt_violations improved 2.1 % in window |  |
| epyc7 | prd-eco_20261123_171023_3055226-i2t-1608228 | eco_20261123_171023_3055226-i2t | 5_2_route | 3.5 | drt_violations best 0 last 0 rows 4 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-coll_core-1578986 | coll_core | 5_1_grt | 4.5 | grt_overflow best 0 last 9 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 32.1 | drt_violations best 76746 last 76746 rows 14 | before-window best 80382, window best 76746 | PROGRESS: drt_violations improved 4.5 % in window |  |
| intel2 | dpkit-coll_ftm-3177651 | coll_ftm | 5_2_route | 2.2 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
