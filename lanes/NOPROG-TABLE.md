# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 23:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 4, 'GRT-LABEL': 2, 'YOUNG': 44, 'NO-DATA': 6, 'PROGRESS': 19}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-hd_lep0N-2158649 | hd_lep0N | 4_2_tapbal_grt | 3.7 | last meaningful line 2.5 h ago (48/53 lines) | UNSIGNABLE: 4_1_cts.json latest setup WNS -2236.42 ps (< -300, gate TT >= -42); job age 3.7  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (OPUS-FIX-QC-V4-R2 decid |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 11.9 | last meaningful line 7.3 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 7.3 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 7.4 | last meaningful line 7.3 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 7.3 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 11.2 | last meaningful line 7.3 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 7.3 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc2 | dpkit-cbn_q11__cl49ae4555-3883814 | cbn_q11 | 5_1_grt | 5.8 | grt rounds 2 overflow 5:166101 -> 10:149070 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | 5_1_grt | 20.0 | grt rounds 2 overflow 5:72617 -> 10:48604 | GRT-LABEL: DESIGN-FAIL: overflow 48604 at round 10 > 1000 |  |
| epyc10 | dpkit-slice_station__t24__cl64811a5d-226587 | slice_station__t24 | 5_2_route | 1.8 | drt_violations best 8225 last 8225 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc2 | ap-ageom-kw-slw-st-b-v2--pva66d0f22--pvb80e2003-dump-2468220 | slw-st-b-v2--pva66d0f22--pvb80e2003-dump | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q11-2451203 | cbf_q11 | 5_1_grt | 3.2 | last meaningful line 0.2 h ago (277/1287 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | 5_1_grt | 5.4 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2194343 | cbx_q10 | 5_1_grt | 3.5 | last meaningful line 0.0 h ago (195/204 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 5.2 | last meaningful line 0.3 h ago (13604/13604 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i2t-3790618 | eco_20261123_102841_2122262-i2t | 5_2_route | 2.4 | last meaningful line 0.2 h ago (284/285 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i2t-2487500 | eco_20261123_103136_2028090-i2t | 5_2_route | 3.2 | drt_violations best 4874 last 4874 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-cbn-q00--cld7bf7197-dump-2616857 | cbn-q00--cld7bf7197-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-cbn-q00--cld7bf7197-grt-2616857 | cbn-q00--cld7bf7197-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-sle-stm-v1--cl27746664-grt-2573967 | sle-stm-v1--cl27746664-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbf_q00__cl1b5a6458-1537791 | cbf_q00 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-glue-2294683 | glue | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5682/5682 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2864139 | hd_lep0N | 4_2_tapbal_grt | 3.0 | last meaningful line 1.8 h ago (48/57 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-native59-960093 | native59 | 3_3_place_gp | 1.2 | overflow best 0.0991 last 0.0991 rows 255 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-sle_hc2__clcc5e3e61-1959134 | sle_hc2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4827/4827 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v3-2137984 | sle_sc_v3 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3943/3943 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-2036429 | sle_stm_v3 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4750/4750 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (5405/5405 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (89/89 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (4740/4740 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i2t-1608228 | eco_20261123_171023_3055226-i2t | 5_1_grt | 0.8 | last meaningful line 0.3 h ago (234/1303 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p5-206562 | kv3_hg_v1p5 | pregrt_ff_hold | 2.3 | repair_TNS best 809467 last 809467 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc8 | dpkit-kv3_hgi_v4-328592 | kv3_hgi_v4 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hroot-45149 | kv3_hroot | 3_3_place_gp | 0.5 | overflow best 0.0995 last 0.0995 rows 47 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-197119 | sle_ctl | pregrt_ff_hold | 2.3 | repair_TNS best 222728 last 222728 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-3737398 | slw_su_l1 | tt_setup_repair_grt | 4.3 | repair_Violations best 12 last 16 rows 55 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i2-3929535 | eco_20261123_120225_75582-i2 | 5_2_route | 2.5 | drt_violations best 19727 last 19727 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i3t-3571186 | eco_20261123_163717_2005956-i3t | 5_2_route | 0.8 | last meaningful line 0.0 h ago (266/267 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1-1021701 | eco_20261123_164145_1995767-i1 | 5_2_route | 2.0 | last meaningful line 0.2 h ago (299/300 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | relec1122-ml-r6_afda1e9d | relec1122-ml-r6_afda1e9d | - | 7.3 |  | NO-DATA: no log found |  |
| epyc9 | eco-abs-1232466 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | otc-946105-10952 | 946105 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc9 | prd-count-p1_tc-2378518 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco-i3-707330 | eco-i3 | 5_2_route | 0.9 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i2-860558 | eco_20261123_190031_3093983-i2 | 5_1_grt | 0.7 | last meaningful line 0.5 h ago (241/1328 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i2t-1506838 | eco_20261123_224216_149959-i2t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i1-3056982 | eco_20261124_010152_2867084-i1 | 5_2_route | 2.5 | last meaningful line 0.2 h ago (284/285 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | s81kvt2_ident_a64d7d7813de | s81kvt2_ident_a64d7d7813de | eq_2 | 0.9 | last meaningful line -0.0 h ago (256251/256251 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t29__clc7772371-3101070 | slice_station__t29 | 5_2_route | 1.6 | last meaningful line 0.0 h ago (237/238 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3079865 | slice_station__t40 | postcts_gate_FF | 1.6 | last meaningful line 0.0 h ago (870/870 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-3847752 | slw_fw_v2 | 3_4_place_resized | 0.9 | last meaningful line 0.1 h ago (396/396 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-4010271 | slw_st_b_v2 | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (432/432 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | fwcap_ab_base200 | fwcap_ab_base200 | 3_4_place_resized | 1.1 | last meaningful line 0.2 h ago (394/394 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | fwcap_ab_pf | fwcap_ab_pf | 3_4_place_resized | 1.1 | last meaningful line 0.2 h ago (366/366 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-1882360-28079 | 1882360 | - | 7.0 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261123_191853_2879776-i1t-119447 | eco_20261123_191853_2879776-i1t | 5_2_route | 4.2 | drt_violations best 17014 last 17014 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2729897 | coll_ftm | 5_2_route | 2.0 | drt_violations best 10172 last 10172 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-1560983 | kv3_io_ft | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i2-3270561 | eco_20261123_051704_3678821-i2 | 5_2_route | 1.6 | last meaningful line 0.0 h ago (258/258 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-714159 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 26.6 | drt_violations best 1342 last 1342 rows 24 | before-window best 9298, window best 1342 | PROGRESS: drt_violations improved 85.6 % in window |  |
| epyc2 | dpkit-cbx_q10__cl89936551_h-2205260 | cbx_q10 | pregrt_ff_hold | 3.5 | repair_Violations best 39994 last 40006 rows 132 | before-window best 340851, window best 39994 | PROGRESS: repair_Violations improved 88.3 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 29.3 | drt_violations best 1617 last 2784 rows 28 | before-window best 1743, window best 1617 | PROGRESS: drt_violations improved 7.2 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 21.8 | drt_violations best 35975 last 35975 rows 6 | before-window best 681573, window best 35975 | PROGRESS: drt_violations improved 94.7 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 15.1 | drt_violations best 45998 last 45998 rows 6 | before-window best 391102, window best 45998 | PROGRESS: drt_violations improved 88.2 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 29.2 | drt_violations best 48746 last 48746 rows 17 | before-window best 50945, window best 48746 | PROGRESS: drt_violations improved 4.3 % in window |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 56.5 | last meaningful line 5.5 h ago (646/646 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-cbn_q01__clab6e67f2-1043557 | cbn_q01 | pregrt_ff_hold | 5.3 | repair_Violations best 40620 last 40634 rows 136 | before-window best 400746, window best 40620 | PROGRESS: repair_Violations improved 89.9 % in window |  |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | pregrt_ff_hold | 5.1 | repair_Violations best 36736 last 36736 rows 101 | before-window best 389181, window best 36736 | PROGRESS: repair_Violations improved 90.6 % in window |  |
| epyc8 | dpkit-cbx_q10__cl89936551-1293593 | cbx_q10 | pregrt_ff_hold | 3.6 | repair_Violations best 40894 last 40894 rows 49 | before-window best 417467, window best 40894 | PROGRESS: repair_Violations improved 90.2 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 39.9 | drt_violations best 17 last 19 rows 58 | before-window best 18, window best 17 | PROGRESS: drt_violations improved 5.6 % in window |  |
| epyc8 | dpkit-coll_core-1578986 | coll_core | pregrt_ff_hold | 1.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-1287720 | slw_fe_v2 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_hc0__cl1bc59e1c-85806 | slw_hc0 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 42.7 | drt_violations best 7378 last 37623 rows 18 | before-window best 18221, window best 7378 | PROGRESS: drt_violations improved 59.5 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 29.4 | drt_violations best 78971 last 78971 rows 13 | before-window best 83289, window best 78971 | PROGRESS: drt_violations improved 5.2 % in window |  |
| intel2 | dpkit-slice_station__t12-1610349 | slice_station__t12 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | prd-eco_20261123_063813_234645-i2t-2973514 | eco_20261123_063813_234645-i2t | 5_2_route | 7.3 | drt_violations best 2 last 16 rows 38 | before-window best 38098, window best 2 | PROGRESS: drt_violations improved 100.0 % in window |  |
