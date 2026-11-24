# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 23:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 5, 'UNSIGNABLE': 2, 'GRT-LABEL': 2, 'YOUNG': 52, 'NO-DATA': 7, 'PROGRESS': 17}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 27.8 | drt_violations best 46606 last 144890 rows 18 | before-window best 47319, window best 46606 | NO-PROGRESS: drt_violations best 46606 vs 47319 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc7 | dpkit-hd_lep0N-2158649 | hd_lep0N | 4_2_tapbal_grt | 3.2 | last meaningful line 2.0 h ago (48/52 lines) | UNSIGNABLE: 4_1_cts.json latest setup WNS -2236.42 ps (< -300, gate TT >= -42); job age 3.2  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (OPUS-FIX-QC-V4-R2 decid |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | tt_setup_repair_grt | 24.1 | repair_Violations best 219 last 274 rows 14 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -926.64 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 11.4 | last meaningful line 6.8 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 6.8 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 6.9 | last meaningful line 6.8 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 6.8 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 10.7 | last meaningful line 6.8 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 6.8 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc2 | dpkit-cbn_q11__cl49ae4555-3883814 | cbn_q11 | 5_1_grt | 5.1 | grt rounds 2 overflow 5:166101 -> 10:149070 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | 5_1_grt | 19.5 | grt rounds 2 overflow 5:72617 -> 10:48604 | GRT-LABEL: DESIGN-FAIL: overflow 48604 at round 10 > 1000 |  |
| epyc10 | dpkit-slice_station__t24__cl64811a5d-226587 | slice_station__t24 | 5_2_route | 1.3 | last meaningful line 0.0 h ago (248/249 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t30__cl6a190133-140494 | slice_station__t30 | 6_report | 1.4 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-1388574 | slw_fw_v2 | 3_3_place_gp | 0.4 | overflow best 0.2031 last 0.2031 rows 36 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-cbf_q00__cl870de686-181856 | cbf_q00 | postcts_gate_FF | 4.6 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q11-2451203 | cbf_q11 | pregrt_ff_hold | 2.5 | repair_Violations best 9153 last 9153 rows 95 | YOUNG: evidence 2.1 h < 2.5 h |  |
| epyc2 | dpkit-cbx_q10__cl89936551_h-2205260 | cbx_q10 | pregrt_ff_hold | 2.7 | repair_Violations best 52766 last 52766 rows 18 | YOUNG: evidence 2.0 h < 2.5 h |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2194343 | cbx_q10 | pregrt_ff_hold | 2.7 | repair_Violations best 49764 last 49778 rows 80 | YOUNG: evidence 2.1 h < 2.5 h |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 4.5 | last meaningful line 0.3 h ago (13576/13576 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i2t-3790618 | eco_20261123_102841_2122262-i2t | 5_2_route | 1.6 | last meaningful line 0.0 h ago (272/273 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i2t-2487500 | eco_20261123_103136_2028090-i2t | 5_2_route | 2.5 | drt_violations best 4874 last 4874 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00__cl1b5a6458-1537791 | cbf_q00 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9509 last 0.9509 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-1537434 | cbn_q00 | 3_1_place_gp_skip_io | 0.3 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-glue-1099230 | glue | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (275/275 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2864139 | hd_lep0N | 4_2_tapbal_grt | 2.5 | last meaningful line 1.3 h ago (48/55 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-3258726 | hd_lep0N_w | 5_2_route | 2.1 | drt_violations best 2 last 2 rows 49 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-native59-960093 | native59 | 3_3_place_gp | 0.7 | overflow best 0.6893 last 0.6893 rows 10 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-1094191 | sle_sc_v1 | 3_3_place_gp | 0.7 | overflow best 0.3747 last 0.3747 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_sc_v3-961457 | sle_sc_v3 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-1029395 | sle_stm_v1 | 3_3_place_gp | 0.7 | overflow best 0.509 last 0.509 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-941214 | slw_hc1 | 3_4_place_resized | 0.7 | last meaningful line 0.1 h ago (446/446 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-969711 | slw_sc_v2 | 3_3_place_gp | 0.7 | overflow best 0.0987 last 0.0987 rows 49 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-997269 | slw_stm_v2 | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (376/376 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i2t-1608228 | eco_20261123_171023_3055226-i2t | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795467809896538497-i1t-60038 | eco_retry_1795467809896538497-i1t | 5_2_route | 9.9 | drt_violations best 4 last 4 rows 49 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p5-206562 | kv3_hg_v1p5 | pregrt_ff_hold | 1.8 | repair_TNS best 809467 last 809467 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-1928525 | sle_ctl | 3_4_place_resized | 1.0 | repair_Remaining best 60012 last 60012 rows 316 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-197119 | sle_ctl | 4_1_cts | 1.8 | last meaningful line 0.1 h ago (11150/11150 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-3737398 | slw_su_l1 | tt_setup_repair_grt | 3.8 | repair_Violations best 12 last 16 rows 55 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i2-3929535 | eco_20261123_120225_75582-i2 | 5_2_route | 2.0 | drt_violations best 19727 last 19727 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i3t-3571186 | eco_20261123_163717_2005956-i3t | 5_1_grt | 0.3 | last meaningful line 0.2 h ago (235/732 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1-1021701 | eco_20261123_164145_1995767-i1 | 5_2_route | 1.5 | last meaningful line 0.2 h ago (289/290 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | relec1122-ml-r6_afda1e9d | relec1122-ml-r6_afda1e9d | - | 6.8 |  | NO-DATA: no log found |  |
| epyc9 | otc-946105-10952 | 946105 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-970914-26238 | 970914 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i3-707330 | eco-i3 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (245/844 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i2-860558 | eco_20261123_190031_3093983-i2 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i1-3056982 | eco_20261124_010152_2867084-i1 | 5_2_route | 2.0 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_041946_4081528-i1-2378518 | eco_20261124_041946_4081528-i1 | 5_2_route | 2.6 | drt_violations best 159 last 159 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | prd-fin-914398 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (1068/1068 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | s81kvt2_ident_a64d7d7813de | s81kvt2_ident_a64d7d7813de | eq_0 | 0.4 | last meaningful line 0.0 h ago (553130/553130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | so_963028_ff_72027 | so_963028_ff_72027 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (695/695 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | so_963028_tt_72027 | so_963028_tt_72027 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (695/695 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-native59-2248842 | native59 | 3_5_place_dp | 1.7 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t29__clc7772371-3101070 | slice_station__t29 | postcts_gate_FF | 1.1 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t30__clcedefe91-2946391 | slice_station__t30 | 5_2_route | 1.2 | drt_violations best 3 last 3 rows 4 | YOUNG: stage 0.8 h < 1 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3079865 | slice_station__t40 | 5_1_grt | 1.1 | last meaningful line 0.0 h ago (677/681 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-3847752 | slw_fw_v2 | 3_3_place_gp | 0.4 | overflow best 0.3666 last 0.3666 rows 3 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-4010271 | slw_st_b_v2 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | fwcap_ab_base200 | fwcap_ab_base200 | 3_3_place_gp | 0.6 | overflow best 0.4208 last 0.4208 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | fwcap_ab_pf | fwcap_ab_pf | 3_3_place_gp | 0.6 | overflow best 0.4315 last 0.4315 rows 17 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | otc-1882360-28079 | 1882360 | - | 6.5 |  | NO-DATA: no log found |  |
| intel1 | otc-19628-30910 | 19628 | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261123_191853_2879776-i1t-119447 | eco_20261123_191853_2879776-i1t | 5_2_route | 3.7 | drt_violations best 17014 last 17014 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2729897 | coll_ftm | 5_2_route | 1.5 | last meaningful line 0.1 h ago (240/241 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-3092223 | kv3_io_ft | 5_2_route | 1.2 | drt_violations best 193 last 193 rows 2 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i2-3270561 | eco_20261123_051704_3678821-i2 | 5_1_grt | 1.1 | last meaningful line 0.7 h ago (292/1421 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2t-2973514 | eco_20261123_063813_234645-i2t | 5_2_route | 6.8 | drt_violations best 2 last 61 rows 37 | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel2 | so_946964_ff_21029 | so_946964_ff_21029 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_946964_tt_21029 | so_946964_tt_21029 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-714159 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 0.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 26.1 | drt_violations best 1392 last 1392 rows 23 | before-window best 9298, window best 1392 | PROGRESS: drt_violations improved 85.0 % in window |  |
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | pregrt_ff_hold | 4.6 | repair_Violations best 43292 last 43320 rows 64 | before-window best 469327, window best 43292 | PROGRESS: repair_Violations improved 90.8 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 28.5 | drt_violations best 1617 last 3457 rows 27 | before-window best 1743, window best 1617 | PROGRESS: drt_violations improved 7.2 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 21.3 | drt_violations best 39904 last 39904 rows 5 | before-window best 681573, window best 39904 | PROGRESS: drt_violations improved 94.1 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 14.6 | drt_violations best 49025 last 49025 rows 5 | before-window best 391102, window best 49025 | PROGRESS: drt_violations improved 87.5 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 28.7 | drt_violations best 49778 last 49778 rows 16 | before-window best 54432, window best 49778 | PROGRESS: drt_violations improved 8.6 % in window |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 56.0 | last meaningful line 5.0 h ago (646/646 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-cbn_q01__clab6e67f2-1043557 | cbn_q01 | pregrt_ff_hold | 4.8 | repair_Violations best 41033 last 41067 rows 63 | before-window best 400746, window best 41033 | PROGRESS: repair_Violations improved 89.8 % in window |  |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | pregrt_ff_hold | 4.6 | repair_Violations best 37908 last 37908 rows 33 | before-window best 389181, window best 37908 | PROGRESS: repair_Violations improved 90.3 % in window |  |
| epyc8 | dpkit-cbx_q10__cl89936551-1293593 | cbx_q10 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 39.4 | drt_violations best 17 last 19 rows 58 | before-window best 18, window best 17 | PROGRESS: drt_violations improved 5.6 % in window |  |
| epyc8 | dpkit-coll_core-1578986 | coll_core | pregrt_ff_hold | 1.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-1287720 | slw_fe_v2 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_hc0__cl1bc59e1c-85806 | slw_hc0 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 42.2 | drt_violations best 7378 last 37623 rows 18 | before-window best 18221, window best 7378 | PROGRESS: drt_violations improved 59.5 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 28.9 | drt_violations best 78971 last 78971 rows 13 | before-window best 88174, window best 78971 | PROGRESS: drt_violations improved 10.4 % in window |  |
