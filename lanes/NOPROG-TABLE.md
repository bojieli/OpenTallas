# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 22:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 6, 'GRT-LABEL': 2, 'YOUNG': 58, 'NO-DATA': 2, 'PROGRESS': 16}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 27.8 | drt_violations best 46606 last 144890 rows 18 | before-window best 47319, window best 46606 | NO-PROGRESS: drt_violations best 46606 vs 47319 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (OPUS-FIX-QC-V4-R2 decid |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 26.7 | drt_violations best 15 last 15 rows 60 | before-window best 15, window best 15 | NO-PROGRESS: drt_violations best 15 vs 15 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (FAM-S81-COL-H9R0-R4 dec |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 11.1 | last meaningful line 6.5 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 6.5 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 6.7 | last meaningful line 6.5 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 6.5 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 10.4 | last meaningful line 6.5 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 6.5 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc2 | dpkit-cbn_q11__cl49ae4555-3883814 | cbn_q11 | 5_1_grt | 5.1 | grt rounds 2 overflow 5:166101 -> 10:149070 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | 5_1_grt | 19.3 | grt rounds 2 overflow 5:72617 -> 10:48604 | GRT-LABEL: DESIGN-FAIL: overflow 48604 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-714159 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 0.7 | last meaningful line 0.1 h ago (44/44 lines) | YOUNG: evidence 0.3 h < 2.5 h |  |
| epyc10 | dpkit-slice_station__t24__cl64811a5d-226587 | slice_station__t24 | 5_2_route | 1.1 | last meaningful line 0.0 h ago (236/237 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t30__cl6a190133-140494 | slice_station__t30 | 5_2_route | 1.1 | drt_violations best 3406 last 3406 rows 2 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | dpkit-slice_station__t7__cl362204c4-174378 | slice_station__t7 | 6_report | 1.1 | last meaningful line 0.0 h ago (77/77 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-1388574 | slw_fw_v2 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl870de686-181856 | cbf_q00 | postcts_gate_FF | 4.6 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q11-2451203 | cbf_q11 | pregrt_ff_hold | 2.5 | repair_Violations best 9153 last 9153 rows 95 | YOUNG: evidence 2.1 h < 2.5 h |  |
| epyc2 | dpkit-cbx_q10__cl89936551_h-2205260 | cbx_q10 | pregrt_ff_hold | 2.7 | repair_Violations best 52766 last 52766 rows 18 | YOUNG: evidence 2.0 h < 2.5 h |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2194343 | cbx_q10 | pregrt_ff_hold | 2.7 | repair_Violations best 49764 last 49778 rows 80 | YOUNG: evidence 2.1 h < 2.5 h |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 4.5 | last meaningful line 0.3 h ago (13576/13576 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i2t-3790618 | eco_20261123_102841_2122262-i2t | 5_2_route | 1.6 | last meaningful line 0.0 h ago (272/273 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i2t-2487500 | eco_20261123_103136_2028090-i2t | 5_2_route | 2.5 | drt_violations best 4874 last 4874 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00__cl1b5a6458-1537791 | cbf_q00 | 2_1_floorplan | 0.1 | repair_Viol best 6140 last 6140 rows 192 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-1537434 | cbn_q00 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 125 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-glue-1099230 | glue | 3_3_place_gp | 0.4 | overflow best 0.5934 last 0.5934 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N-2158649 | hd_lep0N | 4_2_tapbal_grt | 2.9 | last meaningful line 1.8 h ago (48/52 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2864139 | hd_lep0N | 4_2_tapbal_grt | 2.2 | last meaningful line 1.0 h ago (48/54 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-3258726 | hd_lep0N_w | 5_2_route | 1.9 | drt_violations best 8773 last 8773 rows 3 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-native59-960093 | native59 | 2_1_floorplan | 0.5 | last meaningful line 0.1 h ago (1359/1359 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc2__clcc5e3e61-945436 | sle_hc2 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-1094191 | sle_sc_v1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.1726 last 0.1863 rows 49 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-sle_sc_v3-961457 | sle_sc_v3 | 3_4_place_resized | 0.5 | last meaningful line 0.0 h ago (341/341 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-1029395 | sle_stm_v1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.4282 last 0.4282 rows 36 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-sle_stm_v3-1004956 | sle_stm_v3 | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (276/276 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-941214 | slw_hc1 | 3_3_place_gp | 0.5 | overflow best 0.1349 last 0.1349 rows 47 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-slw_sc_v2-969711 | slw_sc_v2 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (291/291 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-997269 | slw_stm_v2 | 3_3_place_gp | 0.4 | overflow best 0.1991 last 0.1991 rows 36 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i2t-1608228 | eco_20261123_171023_3055226-i2t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795467809896538497-i1t-60038 | eco_retry_1795467809896538497-i1t | 5_2_route | 9.6 | drt_violations best 7 last 7 rows 7 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc8 | dpkit-coll_core-1578986 | coll_core | pregrt_ff_hold | 1.0 | repair_TNS best 62167.7 last 62167.7 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_hg_v1p5-206562 | kv3_hg_v1p5 | pregrt_ff_hold | 1.6 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-1928525 | sle_ctl | 3_3_place_gp | 0.8 | overflow best 0.5485 last 0.5485 rows 18 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-197119 | sle_ctl | 4_1_cts | 1.6 | last meaningful line 0.1 h ago (10869/10869 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-3737398 | slw_su_l1 | tt_setup_repair_grt | 3.5 | repair_Violations best 12 last 16 rows 55 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i2-3929535 | eco_20261123_120225_75582-i2 | 5_2_route | 1.8 | last meaningful line 0.1 h ago (291/292 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i3t-3571186 | eco_20261123_163717_2005956-i3t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1-1021701 | eco_20261123_164145_1995767-i1 | 5_2_route | 1.2 | last meaningful line 0.2 h ago (285/286 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | relec1122-ml-r6_afda1e9d | relec1122-ml-r6_afda1e9d | - | 6.6 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | tt_setup_repair_grt | 23.8 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | eco-abs-371999 | eco-abs | generate_abstract | 0.5 | last meaningful line 0.2 h ago (691/691 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | prd-count-p1_tc-914398 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (1051/1051 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco-i3-707330 | eco-i3 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i1-3056982 | eco_20261124_010152_2867084-i1 | 5_2_route | 1.7 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_041946_4081528-i1-2378518 | eco_20261124_041946_4081528-i1 | 5_2_route | 2.4 | drt_violations best 159 last 159 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | prd-fin-1439699 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (1075/1075 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | s81kvt2_ident_a64d7d7813de | s81kvt2_ident_a64d7d7813de | pre_new_0 | 0.2 | last meaningful line 0.0 h ago (444/444 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-native59-2248842 | native59 | 3_4_place_resized | 1.4 | last meaningful line 0.1 h ago (334/334 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t30__clcedefe91-2946391 | slice_station__t30 | 5_2_route | 1.0 | drt_violations best 2627 last 2627 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3079865 | slice_station__t40 | 5_1_grt | 0.9 | last meaningful line 0.2 h ago (281/584 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-3847752 | slw_fw_v2 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | fwcap_ab_base200 | fwcap_ab_base200 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9693 last 0.9693 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | fwcap_ab_pf | fwcap_ab_pf | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9217 last 0.9217 rows 24 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | otc-1882360-28079 | 1882360 | - | 6.2 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261123_191853_2879776-i1t-119447 | eco_20261123_191853_2879776-i1t | 5_2_route | 3.4 | drt_violations best 17014 last 17014 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2729897 | coll_ftm | 5_2_route | 1.2 | last meaningful line 0.1 h ago (232/233 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-136777 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-3092223 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5487 last 5487 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-3132010 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 2964 last 2964 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i2-3270561 | eco_20261123_051704_3678821-i2 | 5_1_grt | 0.9 | last meaningful line 0.5 h ago (292/1360 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2t-2973514 | eco_20261123_063813_234645-i2t | 5_2_route | 6.5 | drt_violations best 2 last 61 rows 37 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 25.8 | drt_violations best 1392 last 1392 rows 23 | before-window best 9298, window best 1392 | PROGRESS: drt_violations improved 85.0 % in window |  |
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | pregrt_ff_hold | 4.6 | repair_Violations best 43292 last 43320 rows 64 | before-window best 469327, window best 43292 | PROGRESS: repair_Violations improved 90.8 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 28.5 | drt_violations best 1617 last 3457 rows 27 | before-window best 1743, window best 1617 | PROGRESS: drt_violations improved 7.2 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 21.1 | drt_violations best 39904 last 39904 rows 5 | before-window best 681573, window best 39904 | PROGRESS: drt_violations improved 94.1 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 14.4 | drt_violations best 49025 last 49025 rows 5 | before-window best 391102, window best 49025 | PROGRESS: drt_violations improved 87.5 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 28.4 | drt_violations best 49778 last 49778 rows 16 | before-window best 54432, window best 49778 | PROGRESS: drt_violations improved 8.6 % in window |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 55.7 | last meaningful line 4.8 h ago (646/646 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbn_q01__clab6e67f2-1043557 | cbn_q01 | pregrt_ff_hold | 4.6 | repair_Violations best 41691 last 41712 rows 26 | before-window best 400746, window best 41691 | PROGRESS: repair_Violations improved 89.6 % in window |  |
| epyc8 | dpkit-cbx_q10__cl89936551-1293593 | cbx_q10 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 39.1 | drt_violations best 17 last 19 rows 58 | before-window best 20, window best 17 | PROGRESS: drt_violations improved 15.0 % in window |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-1287720 | slw_fe_v2 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_hc0__cl1bc59e1c-85806 | slw_hc0 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 42.0 | drt_violations best 7378 last 37623 rows 18 | before-window best 18221, window best 7378 | PROGRESS: drt_violations improved 59.5 % in window |  |
| intel1 | dpkit-slice_station__t29__clc7772371-3101070 | slice_station__t29 | 5_1_grt | 0.8 | repair_TNS best 0 last 0 rows 20 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 28.6 | drt_violations best 78971 last 78971 rows 13 | before-window best 88174, window best 78971 | PROGRESS: drt_violations improved 10.4 % in window |  |
