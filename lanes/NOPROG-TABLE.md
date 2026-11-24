# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 20:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'GRT-LABEL': 3, 'YOUNG': 54, 'NO-DATA': 10, 'PROGRESS': 27}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 16.3 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (OPUS-FIX-KV-PV-R7 decid |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | pregrt_ff_hold | 14.1 | repair_TNS best 188478 last 188478 rows 1 | before-window best 188478, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-cbf_q01-3915852 | cbf_q01 | 5_1_grt | 2.6 | grt rounds 2 overflow 5:10680 -> 10:1919 | GRT-LABEL: DESIGN-FAIL: overflow 1919 at round 10 > 1000 |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | 5_1_grt | 21.3 | grt rounds 2 overflow 5:13730 -> 10:13037 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | 5_1_grt | 20.2 | grt rounds 2 overflow 5:13850 -> 10:12903 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | prd-eco_20261122_223531_3628570-i3-52746 | eco_20261122_223531_3628570-i3 | 5_2_route | 1.7 | last meaningful line 0.1 h ago (294/295 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-3883814 | cbn_q11 | 5_1_grt | 2.6 | last meaningful line 0.1 h ago (147/147 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-cbx_q10__cl89936551_h-2205260 | cbx_q10 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5379/5379 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2194343 | cbx_q10 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5354/5354 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 2.0 | last meaningful line 1.3 h ago (13035/13035 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | eco-abs-1848939 | eco-abs | generate_abstract | 0.6 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | so_1948545_tt_5272 | so_1948545_tt_5272 | generate_abstract | 0.5 | last meaningful line 0.3 h ago (1034/1034 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 11.9 | drt_violations best 391102 last 391102 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-2781664 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 4.1 | last meaningful line 1.8 h ago (37/37 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-1324433 | hd_lep0N | 4_2_tapbal_grt | 1.4 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2158649 | hd_lep0N | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (7824/7824 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795467809896538497-i1t-60038 | eco_retry_1795467809896538497-i1t | 5_2_route | 7.1 | drt_violations best 105749 last 105749 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | prd-fin-1000308 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-cbf-q11-grt-1731968 | cbf-q11-grt | 3_5_place_dp | 0.2 | last meaningful line 0.2 h ago (145/145 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | tt_setup_repair | 1.7 | repair_Violations best 209 last 1032 rows 48 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-cbn_q11__cl5cc92dfe-1712022 | cbn_q11 | pregrt_ff_hold | 1.8 | repair_TNS best 13.133 last 13.133 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-cbx_q10__cl89936551-1293593 | cbx_q10 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5079/5079 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | 5_1_grt | 16.8 | last meaningful line 0.5 h ago (307/1312 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p5-2887155 | kv3_hg_v1p5 | 3_3_place_gp | 1.3 | overflow best 0.0986 last 0.0986 rows 43 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | pregrt_ff_hold | 14.7 | repair_TNS best 495634 last 495634 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-2748514 | sle_ctl | 3_3_place_gp | 1.4 | overflow best 0.1966 last 0.2013 rows 40 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-sle_st_a_v1__cl67389ecd-892590 | sle_st_a_v1 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (8285/8285 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-848919 | sle_st_a_v1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (8132/8132 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-907165 | sle_st_a_v2 | tt_setup_measure | 0.5 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-717305 | sle_st_a_v2 | 5_1_grt | 0.5 | last meaningful line -0.0 h ago (85/85 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-2390497 | sle_su_l1 | 5_1_grt | 1.5 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-1287720 | slw_fe_v2 | 4_1_cts | 0.3 | last meaningful line 0.2 h ago (7847/7847 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl1bc59e1c-85806 | slw_hc0 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (5458/5458 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clb036e152-920083 | slw_st_a_v1 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (8024/8024 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-975156 | slw_st_a_v1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (7953/7953 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-929975 | slw_st_a_v1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (8175/8175 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4164052 | slw_st_a_v2 | 5_1_grt | 0.8 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__clf4365a62-843584 | slw_st_a_v2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (6514/6514 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-3737398 | slw_su_l1 | 5_1_grt | 1.0 | last meaningful line 0.0 h ago (262/263 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | otc-1767006-5828 | 1767006 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-1774837-19001 | 1774837 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261123_140713_549985-i2-3337112 | eco_20261123_140713_549985-i2 | 5_2_route | 1.2 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i2-382519 | eco_20261123_163717_2005956-i2 | 5_1_grt | 0.7 | last meaningful line 0.5 h ago (238/1793 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_2_route | 11.5 | drt_violations best 18 last 18 rows 31 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc8 | relec1122-ml-r6_afda1e9d | relec1122-ml-r6_afda1e9d | - | 4.1 |  | NO-DATA: no log found |  |
| epyc8 | relec1122-ml-r6_d5fde81d | relec1122-ml-r6_d5fde81d | - | 4.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-2068133-23421 | 2068133 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-2247276-32579 | 2247276 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i3t-51485 | eco-i3t | 5_2_route | 2.2 | last meaningful line 0.2 h ago (306/307 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i2t-1439699 | eco_20261123_190031_3093983-i2t | 5_2_route | 0.9 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i1-456858 | eco_20261123_224216_149959-i1 | 5_2_route | 1.8 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i1-914398 | eco_20261123_224647_4153453-i1 | 5_2_route | 1.4 | last meaningful line 0.1 h ago (134/134 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i1t-3365017 | eco_20261124_010152_2867084-i1t | 5_2_route | 3.2 | drt_violations best 355 last 355 rows 2 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | relec1122-ml-r6_00112d4e | relec1122-ml-r6_00112d4e | - | 4.1 |  | NO-DATA: no log found |  |
| epyc9 | s81kvt2_xd_eq3 | s81kvt2_xd_eq3 | eq_2 | 1.0 | last meaningful line -0.0 h ago (4761/4761 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | s81kvt2_xd_eq4 | s81kvt2_xd_eq4 | pre_old_0 | 0.2 | last meaningful line 0.0 h ago (7354/7354 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | so_1772922_ff_57381 | so_1772922_ff_57381 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc9 | so_1772922_tt_57381 | so_1772922_tt_57381 | signoff | 0.5 |  | NO-DATA: empty log |  |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 8.6 | last meaningful line 4.0 h ago (5/5 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 4.2 | last meaningful line 4.0 h ago (5/5 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | otc-1882360-28079 | 1882360 | - | 3.7 |  | NO-DATA: no log found |  |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 7.9 | last meaningful line 4.0 h ago (5/5 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | otc-561767-3725 | 561767 | orfs_synth | 0.4 | last meaningful line 0.3 h ago (483/483 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i1t-119447 | eco_20261123_191853_2879776-i1t | 5_1_grt | 0.9 | last meaningful line 0.4 h ago (235/1476 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | so_741495_ff_96860 | so_741495_ff_96860 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (845/845 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | so_741495_tt_96860 | so_741495_tt_96860 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (845/845 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2001372 | coll_ftm | 5_2_route | 1.7 | drt_violations best 10172 last 10172 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i2t-245032 | eco_20261123_051704_3678821-i2t | 5_2_route | 2.9 | drt_violations best 1664 last 1664 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2t-2973514 | eco_20261123_063813_234645-i2t | 5_2_route | 4.0 | drt_violations best 1459 last 1459 rows 3 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 23.1 | drt_violations best 4252 last 4252 rows 19 | before-window best 13554, window best 4252 | PROGRESS: drt_violations improved 68.6 % in window |  |
| epyc2 | dpkit-cbf_q00__cl870de686-181856 | cbf_q00 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 26.0 | drt_violations best 1617 last 7736 rows 26 | before-window best 1743, window best 1617 | PROGRESS: drt_violations improved 7.2 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 28.3 | drt_violations best 8261 last 28775 rows 18 | before-window best 8936, window best 8261 | PROGRESS: drt_violations improved 7.6 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 24.9 | drt_violations best 39818 last 39818 rows 16 | before-window best 41866, window best 39818 | PROGRESS: drt_violations improved 4.9 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 25.3 | drt_violations best 47053 last 47053 rows 16 | before-window best 48840, window best 47053 | PROGRESS: drt_violations improved 3.7 % in window |  |
| epyc2 | prd-eco_20261122_181101_3945375-i3t-2000832 | eco_20261122_181101_3945375-i3t | 5_1_grt | 0.4 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 18.6 | drt_violations best 186589 last 186589 rows 2 | before-window best 681573, window best 186589 | PROGRESS: drt_violations improved 72.6 % in window |  |
| epyc7 | dpkit-hd_lep0N_w-1023502 | hd_lep0N_w | 5_1_grt | 1.6 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-hd_lep0N_w-1242720 | hd_lep0N_w | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 25.9 | drt_violations best 49778 last 49778 rows 16 | before-window best 56454, window best 49778 | PROGRESS: drt_violations improved 11.8 % in window |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 53.2 | last meaningful line 2.3 h ago (646/646 lines) | PROGRESS: log still growing |  |
| epyc7 | prd-eco_20261123_171023_3055226-i1-2638994 | eco_20261123_171023_3055226-i1 | 5_2_route | 4.2 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-cbf_q01_s2-3852085 | cbf_q01_s2 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbn_q01__clab6e67f2-1043557 | cbn_q01 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 36.6 | drt_violations best 18 last 18 rows 56 | before-window best 20, window best 18 | PROGRESS: drt_violations improved 10.0 % in window |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 13.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 5_1_grt | 16.4 | last meaningful line 0.3 h ago (2477/2483 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-4038462 | sle_st_a_v1 | 5_1_grt | 0.9 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc8 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-802071 | sle_st_a_v2 | pregrt_ff_hold | 0.5 | repair_Violations best 0 last 0 rows 10 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | prd-eco_20261123_120225_75582-i2t-3217904 | eco_20261123_120225_75582-i2t | 5_2_route | 5.0 | drt_violations best 0 last 0 rows 17 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 24.2 | drt_violations best 15 last 16 rows 58 | before-window best 16, window best 15 | PROGRESS: drt_violations improved 6.2 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 39.5 | drt_violations best 10495 last 10495 rows 16 | before-window best 29547, window best 10495 | PROGRESS: drt_violations improved 64.5 % in window |  |
| intel1 | dpkit-native59-203599 | native59 | pregrt_ff_hold | 5.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 26.1 | drt_violations best 80382 last 80382 rows 12 | before-window best 88977, window best 80382 | PROGRESS: drt_violations improved 9.7 % in window |  |
