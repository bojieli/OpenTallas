# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 01:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 3, 'NO-PROGRESS': 5, 'GRT-LABEL': 4, 'YOUNG': 31, 'NO-DATA': 2, 'PROGRESS': 20}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-hd_lep0N-2158649 | hd_lep0N | 4_2_tapbal_grt | 5.4 | last meaningful line 4.3 h ago (48/55 lines) | UNSIGNABLE: 4_1_cts.json latest setup WNS -2236.42 ps (< -300, gate TT >= -42); job age 5.4  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-hd_lep0N-2864139 | hd_lep0N | 4_2_tapbal_grt | 4.7 | last meaningful line 3.5 h ago (48/60 lines) | UNSIGNABLE: 4_1_cts.json latest setup WNS -626.82 ps (< -300, gate TT >= -42); job age 4.7 h | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 58.2 | last meaningful line 7.3 h ago (646/646 lines) | NO-PROGRESS: no new non-iteration log line for 7.3 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc8 | dpkit-cbx_q10__cl89936551-1293593 | cbx_q10 | 5_1_grt | 5.3 | grt rounds 2 overflow 5:17738 -> 10:17579 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -486.85 ps (< -300, gate TT >= -42); job age 5. | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-coll_core-1578986 | coll_core | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (QC-OPEN-COLL decides; n |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 13.6 | last meaningful line 9.0 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 9.0 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 9.2 | last meaningful line 9.0 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 9.0 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 12.9 | last meaningful line 9.0 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 9.0 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | 5_1_grt | 7.1 | grt rounds 2 overflow 5:92167 -> 10:84774 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-cbn_q01__clab6e67f2-1043557 | cbn_q01 | 5_1_grt | 7.1 | grt rounds 2 overflow 5:90242 -> 10:85145 | GRT-LABEL: DESIGN-FAIL: overflow 85145 at round 10 > 1000 |  |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | 5_1_grt | 6.8 | grt rounds 2 overflow 5:87660 -> 10:82099 | GRT-LABEL: DESIGN-FAIL: overflow 82099 at round 10 > 1000 |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | 5_1_grt | 21.8 | grt rounds 2 overflow 5:72617 -> 10:48604 | GRT-LABEL: DESIGN-FAIL: overflow 48604 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-714159 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 3.2 | last meaningful line 0.5 h ago (1295/2704 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (10256/10256 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i2-3480472 | eco_20261123_103136_2028090-i2 | 5_1_grt | 0.9 | last meaningful line 0.7 h ago (239/1931 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | prd-fin-3790618 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (1070/1070 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-native59-3518897 | native59 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (5542/5542 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v3-2137984 | sle_sc_v3 | 5_1_grt | 2.1 | last meaningful line 0.1 h ago (1280/1840 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-2036429 | sle_stm_v3 | 5_1_grt | 2.2 | last meaningful line 0.1 h ago (856/867 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | tt_setup_repair | 2.0 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i2t-1608228 | eco_20261123_171023_3055226-i2t | 5_2_route | 2.5 | drt_violations best 2043 last 2043 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | 5_1_grt | 6.7 | last meaningful line 0.1 h ago (147/147 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-1531184 | sle_ctl | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (10894/10894 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl1bc59e1c-85806 | slw_hc0 | 5_1_grt | 5.8 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-3737398 | slw_su_l1 | tt_setup_repair_grt | 6.0 | repair_Violations best 12 last 16 rows 55 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc8 | prd-count-p1_tc-1021701 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (62/62 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i3t-3968210 | eco_20261123_120225_75582-i3t | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (259/849 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | eco-abs-2836023 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | eco-abs-3043228 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.0 h ago (1028/1028 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco-i3-707330 | eco-i3 | 5_2_route | 2.6 | drt_violations best 2 last 2 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i2t-1506838 | eco_20261123_224216_149959-i2t | 5_2_route | 1.8 | last meaningful line 0.1 h ago (280/281 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i2t-2658135 | eco_20261123_224647_4153453-i2t | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (235/1299 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | relec1122-ml-r6_22ee41ca | relec1122-ml-r6_22ee41ca | - | 0.6 |  | NO-DATA: no log found |  |
| intel1 | dpkit-slice_station__t29__clc7772371-3101070 | slice_station__t29 | 5_2_route | 3.3 | drt_violations best 12491 last 12491 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3079865 | slice_station__t40 | 5_2_route | 3.4 | drt_violations best 21249 last 21249 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | otc-1670752-16443 | 1670752 | - | 0.5 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261123_191853_2879776-i1-1832688 | eco_20261123_191853_2879776-i1 | 5_1_grt | 0.4 | last meaningful line 0.1 h ago (143/143 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3177651 | coll_ftm | 5_2_route | 1.2 | last meaningful line 0.1 h ago (230/231 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-1152393 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-687411 | kv3_io_ft | 5_1_grt | 0.5 | last meaningful line 0.0 h ago (381/418 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-730523 | slice_station__t12 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (202/202 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | otc-450886-3386 | 450886 | grt | 0.6 | last meaningful line 0.5 h ago (35/38 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | otc-453881-4382 | 453881 | grt | 0.6 | last meaningful line 0.5 h ago (35/38 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (256/527 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | prd-fin-3270561 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (1067/1067 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 28.3 | drt_violations best 954 last 1081 rows 27 | before-window best 7483, window best 954 | PROGRESS: drt_violations improved 87.3 % in window |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 7.0 | last meaningful line 0.2 h ago (13707/13707 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 31.0 | drt_violations best 1617 last 2562 rows 29 | before-window best 1708, window best 1617 | PROGRESS: drt_violations improved 5.3 % in window |  |
| epyc7 | dpkit-cbf_q00__cl1b5a6458-3305635 | cbf_q00 | pregrt_ff_hold | 1.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-2841416 | cbn_q00 | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 23.6 | drt_violations best 28844 last 28844 rows 9 | before-window best 186589, window best 28844 | PROGRESS: drt_violations improved 84.5 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 16.9 | drt_violations best 42803 last 42803 rows 8 | before-window best 391102, window best 42803 | PROGRESS: drt_violations improved 89.1 % in window |  |
| epyc7 | dpkit-glue-2294683 | glue | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc2__clcc5e3e61-1959134 | sle_hc2 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | pregrt_ff_hold | 1.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | pregrt_ff_hold | 1.8 | repair_Violations best 0 last 0 rows 17 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 30.9 | drt_violations best 48746 last 160916 rows 18 | before-window best 50945, window best 48746 | PROGRESS: drt_violations improved 4.3 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 41.6 | drt_violations best 17 last 19 rows 58 | before-window best 18, window best 17 | PROGRESS: drt_violations improved 5.6 % in window |  |
| epyc8 | dpkit-kv3_hgi_v4-2330527 | kv3_hgi_v4 | pregrt_ff_hold | 1.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-197119 | sle_ctl | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-1287720 | slw_fe_v2 | 5_1_grt | 5.3 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 44.5 | drt_violations best 7378 last 37623 rows 18 | before-window best 15723, window best 7378 | PROGRESS: drt_violations improved 53.1 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 31.1 | drt_violations best 76746 last 76746 rows 14 | before-window best 80382, window best 76746 | PROGRESS: drt_violations improved 4.5 % in window |  |
