# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 21:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'UNSIGNABLE': 1, 'GRT-LABEL': 4, 'YOUNG': 79, 'NO-DATA': 8, 'PROGRESS': 26}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 29.3 | drt_violations best 8261 last 12332 rows 19 | before-window best 8281, window best 8261 | NO-PROGRESS: drt_violations best 8261 vs 8281 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc9 | prd-eco-i3t-51485 | eco-i3t | 5_2_route | 3.2 | drt_violations best 1161 last 1161 rows 1 | UNSIGNABLE: ECO-FLAT: TT setup -104.66 -> -132.71 ps (gate -42); FF hold -1.83 -> -1.83 ps ( | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc2 | dpkit-cbf_q00__cl870de686-181856 | cbf_q00 | 5_1_grt | 3.1 | grt rounds 2 overflow 5:4939 -> 10:4225 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-3883814 | cbn_q11 | 5_1_grt | 3.6 | grt rounds 1 overflow 5:166101 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | 5_1_grt | 22.3 | grt rounds 2 overflow 5:13730 -> 10:13037 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | 5_1_grt | 21.2 | grt rounds 2 overflow 5:13850 -> 10:12903 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3097260 | sle_hc0 | 3_3_place_gp | 0.3 | overflow best 0.6725 last 0.6725 rows 30 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-2965321 | sle_hc2 | 3_3_place_gp | 0.3 | overflow best 0.1948 last 0.1948 rows 45 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3279433 | sle_st_b_v2 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3109353 | slw_hc1 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-2978404 | slw_hc1 | 3_3_place_gp | 0.3 | overflow best 0.6541 last 0.6541 rows 29 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-3026128 | slw_hc3 | 3_3_place_gp | 0.3 | overflow best 0.0995 last 0.0995 rows 54 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2892048 | slw_hc3 | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_su_l0__cl1a1c1f8f-3149910 | slw_su_l0 | 3_5_place_dp | 0.3 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | eco-abs-2718629 | eco-abs | generate_abstract | 0.5 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | otc-3614996-606 | 3614996 | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (374/374 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-3638453-30606 | 3638453 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-cbx_q10__cl89936551_h-2205260 | cbx_q10 | pregrt_ff_hold | 1.2 | repair_TNS best 128.103 last 128.103 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2194343 | cbx_q10 | pregrt_ff_hold | 1.2 | repair_TNS best 137.274 last 137.274 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 3.0 | last meaningful line 2.3 h ago (13035/13035 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_io_ft-2466327 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5487 last 5487 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-sle_hc0__cl05696ed1-3440438 | sle_hc0 | 3_3_place_gp | 0.3 | overflow best 0.2133 last 0.2133 rows 44 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-3431735 | sle_hc0 | 3_3_place_gp | 0.3 | overflow best 0.1308 last 0.1308 rows 48 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-3302313 | sle_hc0 | 3_3_place_gp | 0.3 | overflow best 0.9251 last 0.9251 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3431075 | sle_hc2 | 3_3_place_gp | 0.3 | overflow best 0.9141 last 0.9141 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-3632152 | sle_sc_v1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.931 last 0.931 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3657868 | sle_st_b_v1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l0__cl7a55c676-3376106 | sle_su_l0 | 3_5_place_dp | 0.3 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc2__cl6bcaba89-3452494 | slw_hc2 | 3_3_place_gp | 0.3 | overflow best 0.8862 last 0.8862 rows 6 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3401594 | slw_hc3 | 3_3_place_gp | 0.3 | overflow best 0.2084 last 0.2084 rows 48 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i2t-3790618 | eco_20261123_102841_2122262-i2t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i2t-2487500 | eco_20261123_103136_2028090-i2t | 5_2_route | 1.0 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 12.9 | drt_violations best 95242 last 95242 rows 3 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-2781664 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 5.1 | last meaningful line 2.8 h ago (37/37 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-1324433 | hd_lep0N | 4_2_tapbal_grt | 2.4 | last meaningful line 0.8 h ago (48/54 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2158649 | hd_lep0N | 4_2_tapbal_grt | 1.4 | last meaningful line 0.3 h ago (48/49 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2864139 | hd_lep0N | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (8346/8346 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-3258726 | hd_lep0N_w | 5_2_route | 0.4 | last meaningful line 0.0 h ago (244/245 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3500860 | sle_sc_v1 | 3_3_place_gp | 0.3 | overflow best 0.3727 last 0.3727 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_st_b_v1__pv0e7b1dcc-3612319 | sle_st_b_v1 | 1_synth | 0.2 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3550640 | slw_sc_v1 | 3_3_place_gp | 0.2 | overflow best 0.389 last 0.389 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3492600 | slw_sc_v1 | 3_3_place_gp | 0.3 | overflow best 0.388 last 0.388 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3544661 | slw_stm_v2 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | eco-abs-3503634 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795467809896538497-i1t-60038 | eco_retry_1795467809896538497-i1t | 5_2_route | 8.1 | drt_violations best 105749 last 105749 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-cbx_q10__cl89936551-1293593 | cbx_q10 | pregrt_ff_hold | 1.3 | repair_TNS best 900991 last 900991 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-coll_core-2695309 | coll_core | 3_3_place_gp | 0.8 | overflow best 0.2006 last 0.2006 rows 40 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | 5_1_grt | 17.8 | last meaningful line 1.5 h ago (307/1315 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p5-206562 | kv3_hg_v1p5 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | postcts_gate_FF | 17.4 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-197119 | sle_ctl | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-4038462 | sle_st_a_v1 | postcts_gate_FF | 1.9 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-802071 | sle_st_a_v2 | postcts_gate_FF | 1.5 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-907165 | sle_st_a_v2 | tt_setup_repair_grt | 1.5 | repair_Viol best 51 last 51 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-1287720 | slw_fe_v2 | 4_1_cts | 1.3 | last meaningful line 0.2 h ago (8311/8311 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl1bc59e1c-85806 | slw_hc0 | 4_1_cts | 1.8 | last meaningful line 0.2 h ago (5493/5493 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4164052 | slw_st_a_v2 | postcts_gate_TT | 1.8 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__clf4365a62-843584 | slw_st_a_v2 | postcts_gate_FF | 1.5 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-3737398 | slw_su_l1 | tt_setup_repair_grt | 2.0 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-count-p1_tc-2762092 | count-p1_tc | prd_count_p1_tc | 0.2 | last meaningful line 0.0 h ago (254/254 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i2-382519 | eco_20261123_163717_2005956-i2 | 5_2_route | 1.7 | last meaningful line 0.1 h ago (275/276 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | relec1122-ml-r6_afda1e9d | relec1122-ml-r6_afda1e9d | - | 5.1 |  | NO-DATA: no log found |  |
| epyc8 | relec1122-ml-r6_d5fde81d | relec1122-ml-r6_d5fde81d | - | 5.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-sle_st_b_v2__clfde1249e-3058067 | sle_st_b_v2 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-2918038 | slw_hc3 | 3_3_place_gp | 0.3 | overflow best 0.34 last 0.34 rows 41 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slw_sc_v1__cl63e5a7a2-3029036 | slw_sc_v1 | 3_3_place_gp | 0.2 | overflow best 0.3904 last 0.3904 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | otc-2068133-23421 | 2068133 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-3019105-6365 | 3019105 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261123_190031_3093983-i2t-1439699 | eco_20261123_190031_3093983-i2t | 5_2_route | 1.9 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i1-456858 | eco_20261123_224216_149959-i1 | 5_2_route | 2.8 | drt_violations best 693 last 693 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i1-914398 | eco_20261123_224647_4153453-i1 | 5_2_route | 2.4 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i1-3056982 | eco_20261124_010152_2867084-i1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_041946_4081528-i1-2378518 | eco_20261124_041946_4081528-i1 | 5_2_route | 0.9 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | relec1122-ml-r6_00112d4e | relec1122-ml-r6_00112d4e | - | 5.1 |  | NO-DATA: no log found |  |
| epyc9 | s81kvt2_xd_eq4 | s81kvt2_xd_eq4 | eq_2 | 1.2 | last meaningful line 0.0 h ago (549326/549326 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1670658 | sle_fe_v1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9985 last 0.9985 rows 8 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-sle_hc1__cl7d360508__pv97423966-1517328 | sle_hc1 | 3_3_place_gp | 0.3 | overflow best 0.6524 last 0.6524 rows 29 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-1646542 | sle_hc2 | 3_3_place_gp | 0.3 | overflow best 0.8348 last 0.8348 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1860359 | sle_st_b_v1 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (3601/3601 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t12-917685 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 2964 last 2964 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1561640 | slw_hc0 | 3_3_place_gp | 0.3 | overflow best 0.865 last 0.865 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_hc1__cl3449ea95-1637128 | slw_hc1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8605 last 0.8605 rows 28 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-1545452 | slw_hc2 | 3_2_place_iop | 0.3 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1860873 | slw_st_b_v1 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (3594/3594 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1785954 | slw_stm_v1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-1236838-2718 | 1236838 | - | 0.5 |  | NO-DATA: no log found |  |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 9.6 | last meaningful line 5.0 h ago (5/5 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 5.2 | last meaningful line 5.0 h ago (5/5 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | otc-1882360-28079 | 1882360 | - | 4.7 |  | NO-DATA: no log found |  |
| intel1 | otc-1935516-28651 | 1935516 | w18_sta_ff | 0.1 | last meaningful line 0.1 h ago (146/146 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 8.9 | last meaningful line 5.0 h ago (5/5 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i1t-119447 | eco_20261123_191853_2879776-i1t | 5_2_route | 1.9 | last meaningful line 0.3 h ago (268/269 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2t-2973514 | eco_20261123_063813_234645-i2t | 5_2_route | 5.0 | drt_violations best 28 last 28 rows 14 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 24.3 | drt_violations best 2455 last 2455 rows 21 | before-window best 11282, window best 2455 | PROGRESS: drt_violations improved 78.2 % in window |  |
| epyc2 | dpkit-cbf_q11-2451203 | cbf_q11 | pregrt_ff_hold | 1.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 27.0 | drt_violations best 1617 last 7736 rows 26 | before-window best 1743, window best 1617 | PROGRESS: drt_violations improved 7.2 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 25.9 | drt_violations best 39818 last 39818 rows 16 | before-window best 41866, window best 39818 | PROGRESS: drt_violations improved 4.9 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 26.3 | drt_violations best 47053 last 47053 rows 16 | before-window best 48840, window best 47053 | PROGRESS: drt_violations improved 3.7 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 19.6 | drt_violations best 131336 last 131336 rows 3 | before-window best 681573, window best 131336 | PROGRESS: drt_violations improved 80.7 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 26.9 | drt_violations best 49778 last 49778 rows 16 | before-window best 54432, window best 49778 | PROGRESS: drt_violations improved 8.6 % in window |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 54.2 | last meaningful line 3.3 h ago (646/646 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbf_q01_s2-3852085 | cbf_q01_s2 | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbn_q01__clab6e67f2-1043557 | cbn_q01 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbn_q11__cl5cc92dfe-1712022 | cbn_q11 | pregrt_ff_hold | 2.8 | repair_Violations best 14387 last 14387 rows 30 | before-window best 192059, window best 14387 | PROGRESS: repair_Violations improved 92.5 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 37.6 | drt_violations best 17 last 19 rows 58 | before-window best 20, window best 17 | PROGRESS: drt_violations improved 15.0 % in window |  |
| epyc8 | dpkit-sle_st_a_v1__cl67389ecd-892590 | sle_st_a_v1 | 5_1_grt | 1.5 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-848919 | sle_st_a_v1 | 5_1_grt | 1.5 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v1__clb036e152-920083 | slw_st_a_v1 | 5_1_grt | 1.5 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-975156 | slw_st_a_v1 | 5_1_grt | 1.5 | repair_TNS best 0 last 0 rows 20 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-929975 | slw_st_a_v1 | 5_1_grt | 1.5 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | prd-eco_20261123_120225_75582-i2-3929535 | eco_20261123_120225_75582-i2 | 5_1_grt | 0.3 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc8 | prd-eco_20261123_140713_549985-i2-3337112 | eco_20261123_140713_549985-i2 | 5_2_route | 2.2 | drt_violations best 0 last 0 rows 1 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 25.2 | drt_violations best 15 last 15 rows 60 | before-window best 16, window best 15 | PROGRESS: drt_violations improved 6.2 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 40.5 | drt_violations best 10495 last 10495 rows 16 | before-window best 29547, window best 10495 | PROGRESS: drt_violations improved 64.5 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 27.1 | drt_violations best 78971 last 78971 rows 13 | before-window best 88174, window best 78971 | PROGRESS: drt_violations improved 10.4 % in window |  |
| intel2 | prd-eco_20261123_051704_3678821-i2t-245032 | eco_20261123_051704_3678821-i2t | 5_2_route | 3.9 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
