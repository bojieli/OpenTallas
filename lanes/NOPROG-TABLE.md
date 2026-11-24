# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 19:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'GRT-LABEL': 2, 'YOUNG': 67, 'NO-DATA': 8, 'PROGRESS': 21}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 15.8 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (OPUS-FIX-KV-PV-R7 decid |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | 5_1_grt | 20.6 | grt rounds 2 overflow 5:13730 -> 10:13037 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | 5_1_grt | 19.4 | grt rounds 2 overflow 5:13850 -> 10:12903 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | prd-eco_20261122_223531_3628570-i3-52746 | eco_20261122_223531_3628570-i3 | 5_2_route | 1.2 | last meaningful line 0.0 h ago (276/276 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-3883814 | cbn_q11 | pregrt_ff_hold | 1.8 | repair_Violations best 11665 last 11665 rows 58 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 1.2 | last meaningful line 0.5 h ago (13035/13035 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | eco-abs-1201405 | eco-abs | generate_abstract | 0.5 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-fin-1373161 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (1070/1070 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_1418307_ff_38662 | so_1418307_ff_38662 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | so_1418307_tt_38662 | so_1418307_tt_38662 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | so_1665007_ff_5468 | so_1665007_ff_5468 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (976/976 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | so_1665007_tt_5468 | so_1665007_tt_5468 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (976/976 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 17.8 | drt_violations best 186589 last 186589 rows 2 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 11.1 | drt_violations best 391102 last 391102 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-2781664 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 3.4 | last meaningful line 1.0 h ago (37/37 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-1324433 | hd_lep0N | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (8006/8006 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-1365803 | hd_lep0N | 3_3_place_gp | 0.6 | last meaningful line 0.1 h ago (47/47 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-374468 | hd_lep0N | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-1242720 | hd_lep0N_w | 4_2_tapbal_grt | 0.7 | last meaningful line 0.3 h ago (46/69 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i1-2638994 | eco_20261123_171023_3055226-i1 | 5_2_route | 3.5 | drt_violations best 136 last 136 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_184706_2375049-i2-1000308 | eco_20261123_184706_2375049-i2 | 5_2_route | 0.8 | last meaningful line 0.1 h ago (271/272 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795467809896538497-i1t-60038 | eco_retry_1795467809896538497-i1t | 5_2_route | 6.4 | last meaningful line 0.1 h ago (296/297 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (7916/7916 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q11-3330272 | cbf_q11 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.3436 last 0.3436 rows 31 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (7866/7866 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q11__cl5cc92dfe-1712022 | cbn_q11 | pregrt_ff_hold | 1.0 | repair_TNS best 13.133 last 13.133 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-cbx_q10__cl89936551-3184720 | cbx_q10 | 3_3_place_gp | 0.5 | overflow best 0.2143 last 0.2143 rows 33 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-cbx_q10__cl89936551_h-3216687 | cbx_q10 | 3_3_place_gp | 0.5 | overflow best 0.2155 last 0.2155 rows 33 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-cbx_q10__cl94a12200_h-3332645 | cbx_q10 | 3_3_place_gp | 0.4 | overflow best 0.2783 last 0.2783 rows 29 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | 5_1_grt | 16.0 | last meaningful line 0.1 h ago (172/172 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p5-2887155 | kv3_hg_v1p5 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.0 h ago (527/527 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | pregrt_ff_hold | 14.0 | repair_TNS best 495634 last 495634 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-2748514 | sle_ctl | 3_1_place_gp_skip_io | 0.6 | overflow best 0.8903 last 0.8903 rows 6 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-sle_st_a_v1__cl67389ecd-3848108 | sle_st_a_v1 | 3_3_place_gp | 0.2 | overflow best 0.464 last 0.464 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-3841272 | sle_st_a_v1 | 3_3_place_gp | 0.2 | overflow best 0.3708 last 0.3708 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-4038462 | sle_st_a_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (8469/8469 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-3769563 | sle_st_a_v2 | 3_3_place_gp | 0.3 | overflow best 0.197 last 0.197 rows 39 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3815086 | sle_st_a_v2 | 3_3_place_gp | 0.2 | overflow best 0.2835 last 0.2896 rows 32 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-3824760 | sle_st_a_v2 | 3_3_place_gp | 0.2 | overflow best 0.1787 last 0.1787 rows 40 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-2047894 | slw_fe_v2 | 3_4_place_resized | 0.9 | last meaningful line 0.1 h ago (385/385 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl1bc59e1c-85806 | slw_hc0 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clb036e152-3914429 | slw_st_a_v1 | 3_3_place_gp | 0.2 | overflow best 0.5637 last 0.569 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-3920528 | slw_st_a_v1 | 3_3_place_gp | 0.2 | overflow best 0.558 last 0.5689 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-3937378 | slw_st_a_v1 | 3_3_place_gp | 0.2 | overflow best 0.5561 last 0.5561 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4164052 | slw_st_a_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (7927/7928 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__clf4365a62-3923475 | slw_st_a_v2 | 3_3_place_gp | 0.2 | overflow best 0.5283 last 0.5516 rows 17 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-3737398 | slw_su_l1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (2556/2556 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | otc-3810992-19929 | 3810992 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-3817062-3329 | 3817062 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-3901614-10450 | 3901614 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261123_120225_75582-i2t-3217904 | eco_20261123_120225_75582-i2t | 5_2_route | 4.3 | drt_violations best 85 last 85 rows 7 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_140713_549985-i2-3337112 | eco_20261123_140713_549985-i2 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (299/620 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_2_route | 10.8 | drt_violations best 16670 last 16670 rows 2 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | prd-fin-991032 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (596/596 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | relec1122-ml-r6_afda1e9d | relec1122-ml-r6_afda1e9d | - | 3.3 |  | NO-DATA: no log found |  |
| epyc8 | relec1122-ml-r6_d5fde81d | relec1122-ml-r6_d5fde81d | - | 3.3 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | pregrt_ff_hold | 13.3 | repair_TNS best 188478 last 188478 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | generate_abstract | 22.5 | last meaningful line 0.2 h ago (641/641 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | otc-1270989-13116 | 1270989 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i3t-51485 | eco-i3t | 5_2_route | 1.5 | last meaningful line 0.2 h ago (294/295 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i2t-1439699 | eco_20261123_190031_3093983-i2t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i1-456858 | eco_20261123_224216_149959-i1 | 5_2_route | 1.1 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i1-914398 | eco_20261123_224647_4153453-i1 | 5_1_grt | 0.6 | last meaningful line 0.3 h ago (237/1320 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i1t-3365017 | eco_20261124_010152_2867084-i1t | 5_2_route | 2.4 | drt_violations best 14465 last 14465 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | relec1122-ml-r6_00112d4e | relec1122-ml-r6_00112d4e | - | 3.3 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-rxsb_autofill | relec1122-ml-rxsb_autofill | gate.ys | 0.2 | last meaningful line 0.2 h ago (22052/22052 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | s81kvt2_xd_eq | s81kvt2_xd_eq | pre_new_2 | 0.9 | last meaningful line 0.2 h ago (4941/4941 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | s81kvt2_xd_eq3 | s81kvt2_xd_eq3 | pre_new_0 | 0.2 | last meaningful line 0.1 h ago (439/439 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 7.9 | last meaningful line 3.3 h ago (5/5 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 3.4 | last meaningful line 3.3 h ago (5/5 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | otc-1882360-28079 | 1882360 | - | 3.0 |  | NO-DATA: no log found |  |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 7.2 | last meaningful line 3.3 h ago (5/5 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | otc-219542-18186 | 219542 | orfs_synth | 0.0 | last meaningful line 0.0 h ago (483/483 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-count-p1_bc-910286 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i1t-119447 | eco_20261123_191853_2879776-i1t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2001372 | coll_ftm | 5_2_route | 1.0 | last meaningful line 0.0 h ago (225/225 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i2t-245032 | eco_20261123_051704_3678821-i2t | 5_2_route | 2.1 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2t-2973514 | eco_20261123_063813_234645-i2t | 5_2_route | 3.3 | drt_violations best 38098 last 38098 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 22.6 | drt_violations best 4252 last 4252 rows 19 | before-window best 13554, window best 4252 | PROGRESS: drt_violations improved 68.6 % in window |  |
| epyc2 | dpkit-cbf_q00__cl870de686-181856 | cbf_q00 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-cbf_q01-3915852 | cbf_q01 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 25.3 | drt_violations best 1692 last 1692 rows 24 | before-window best 1743, window best 1692 | PROGRESS: drt_violations improved 2.9 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 27.5 | drt_violations best 8261 last 28775 rows 18 | before-window best 8936, window best 8261 | PROGRESS: drt_violations improved 7.6 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 24.1 | drt_violations best 39818 last 39818 rows 16 | before-window best 44158, window best 39818 | PROGRESS: drt_violations improved 9.8 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 24.5 | drt_violations best 47053 last 47053 rows 16 | before-window best 50150, window best 47053 | PROGRESS: drt_violations improved 6.2 % in window |  |
| epyc7 | dpkit-hd_lep0N_w-1023502 | hd_lep0N_w | pregrt_ff_hold | 0.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 25.2 | drt_violations best 50945 last 50945 rows 15 | before-window best 56454, window best 50945 | PROGRESS: drt_violations improved 9.8 % in window |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 52.5 | last meaningful line 1.5 h ago (646/646 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-cbf_q01_s2-3852085 | cbf_q01_s2 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbn_q01__clab6e67f2-1043557 | cbn_q01 | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 35.9 | drt_violations best 18 last 18 rows 56 | before-window best 20, window best 18 | PROGRESS: drt_violations improved 10.0 % in window |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 12.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 5_1_grt | 15.7 | repair_TNS best 12.115 last 12.115 rows 8 | before-window best 92.672, window best 12.115 | PROGRESS: repair_TNS improved 86.9 % in window |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-2390497 | sle_su_l1 | pregrt_ff_hold | 0.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 23.4 | drt_violations best 15 last 18 rows 57 | before-window best 22, window best 15 | PROGRESS: drt_violations improved 31.8 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 38.7 | drt_violations best 15723 last 15723 rows 15 | before-window best 29547, window best 15723 | PROGRESS: drt_violations improved 46.8 % in window |  |
| intel1 | dpkit-native59-203599 | native59 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 25.4 | drt_violations best 80382 last 80382 rows 12 | before-window best 88977, window best 80382 | PROGRESS: drt_violations improved 9.7 % in window |  |
