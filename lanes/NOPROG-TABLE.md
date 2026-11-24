# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 20:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'GRT-LABEL': 3, 'NO-DATA': 13, 'YOUNG': 59, 'EXCLUDED': 1, 'PROGRESS': 22}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 16.8 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (OPUS-FIX-KV-PV-R7 decid |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 13.4 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FABLE-FIX-KV-HG decides |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | pregrt_ff_hold | 14.1 | repair_TNS best 188478 last 188478 rows 1 | before-window best 188478, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| intel1 | dpkit-native59-203599 | native59 | pregrt_ff_hold | 5.6 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-cbn_q11__cl49ae4555-3883814 | cbn_q11 | 5_1_grt | 2.8 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | 5_1_grt | 21.3 | grt rounds 2 overflow 5:13730 -> 10:13037 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | 5_1_grt | 20.2 | grt rounds 2 overflow 5:13850 -> 10:12903 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-2272595-3856 | 2272595 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc10 | prd-count-p1_bc-52746 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (1019/1019 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl870de686-181856 | cbf_q00 | pregrt_ff_hold | 2.4 | repair_Violations best 13358 last 13358 rows 13 | YOUNG: evidence 1.8 h < 2.5 h |  |
| epyc2 | dpkit-cbf_q11-2451203 | cbf_q11 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5075/5075 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-cbx_q10__cl89936551_h-2205260 | cbx_q10 | tt_setup_repair | 0.5 | repair_Violations best 52 last 320 rows 20 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2194343 | cbx_q10 | tt_setup_repair | 0.5 | repair_Violations best 54 last 1090 rows 28 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 2.2 | last meaningful line 1.5 h ago (13035/13035 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_io_ft-2466327 | kv3_io_ft | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | eco-abs-1848939 | eco-abs | generate_abstract | 0.8 | last meaningful line 0.1 h ago (1032/1032 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i3t-2000832 | eco_20261122_181101_3945375-i3t | 5_1_grt | 0.7 | last meaningful line 0.3 h ago (235/1294 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i2t-2487500 | eco_20261123_103136_2028090-i2t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-hd-lep0N-grt-2659899 | hd-lep0N-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 12.1 | drt_violations best 129916 last 129916 rows 2 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-2781664 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 4.4 | last meaningful line 2.0 h ago (37/37 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-1324433 | hd_lep0N | 4_2_tapbal_grt | 1.6 | last meaningful line 0.1 h ago (48/50 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2158649 | hd_lep0N | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (8395/8395 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-1023502 | hd_lep0N_w | 5_1_grt | 1.8 | last meaningful line 0.0 h ago (1846/1852 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | eco-abs-2835681 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-2835076-7594 | 2835076 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | prd-count-p1_tc-2638994 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795467809896538497-i1t-60038 | eco_retry_1795467809896538497-i1t | 5_2_route | 7.4 | drt_violations best 105749 last 105749 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | tt_setup_repair | 2.0 | repair_Violations best 10 last 113 rows 80 | YOUNG: stage 0.7 h < 1 h |  |
| epyc8 | dpkit-cbn_q11__cl5cc92dfe-1712022 | cbn_q11 | pregrt_ff_hold | 2.0 | repair_TNS best 13.133 last 13.133 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-cbx_q10__cl89936551-1293593 | cbx_q10 | tt_setup_repair | 0.6 | repair_Violations best 79 last 143 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-coll_core-2695309 | coll_core | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (223/223 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | 5_1_grt | 17.0 | last meaningful line 0.8 h ago (307/1312 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p5-2887155 | kv3_hg_v1p5 | 3_5_place_dp | 1.6 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | pregrt_ff_hold | 15.0 | repair_TNS best 495634 last 495634 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-2748514 | sle_ctl | 3_4_place_resized | 1.6 | repair_Remaining best 333026 last 333026 rows 43 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-848919 | sle_st_a_v1 | pregrt_ff_hold | 0.7 | last meaningful line 0.0 h ago (60/60 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-4038462 | sle_st_a_v1 | 5_1_grt | 1.1 | last meaningful line 0.1 h ago (1305/2068 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-802071 | sle_st_a_v2 | 5_1_grt | 0.8 | last meaningful line 0.0 h ago (1306/1363 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-907165 | sle_st_a_v2 | 5_1_grt | 0.7 | last meaningful line 0.0 h ago (273/275 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-717305 | sle_st_a_v2 | 5_1_grt | 0.8 | repair_Remaining best 108683 last 108683 rows 38 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-2390497 | sle_su_l1 | 5_1_grt | 1.8 | last meaningful line 0.2 h ago (248/1255 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-1287720 | slw_fe_v2 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (8256/8256 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl1bc59e1c-85806 | slw_hc0 | 4_1_cts | 1.0 | last meaningful line 0.2 h ago (5485/5485 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-975156 | slw_st_a_v1 | pregrt_ff_hold | 0.7 | last meaningful line 0.0 h ago (60/60 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4164052 | slw_st_a_v2 | 5_1_grt | 1.1 | repair_Remaining best 170704 last 170704 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-slw_st_a_v2__clf4365a62-843584 | slw_st_a_v2 | 5_1_grt | 0.8 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-3737398 | slw_su_l1 | 5_1_grt | 1.3 | last meaningful line 0.1 h ago (1299/1610 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | otc-1767006-5828 | 1767006 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-1774837-19001 | 1774837 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc8 | prd-count-p1_tc-3217904 | count-p1_tc | prd_count_p1_tc | 0.2 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_140713_549985-i2-3337112 | eco_20261123_140713_549985-i2 | 5_2_route | 1.4 | last meaningful line 0.0 h ago (265/266 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i2-382519 | eco_20261123_163717_2005956-i2 | 5_1_grt | 0.9 | last meaningful line 0.7 h ago (238/2341 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_2_route | 11.8 | drt_violations best 10 last 10 rows 52 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc8 | relec1122-ml-r6_afda1e9d | relec1122-ml-r6_afda1e9d | - | 4.3 |  | NO-DATA: no log found |  |
| epyc8 | relec1122-ml-r6_d5fde81d | relec1122-ml-r6_d5fde81d | - | 4.3 |  | NO-DATA: no log found |  |
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
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 8.9 | last meaningful line 4.3 h ago (5/5 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 4.4 | last meaningful line 4.3 h ago (5/5 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | otc-1882360-28079 | 1882360 | - | 4.0 |  | NO-DATA: no log found |  |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 8.2 | last meaningful line 4.3 h ago (5/5 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | otc-561767-3725 | 561767 | orfs_synth | 0.7 | last meaningful line 0.5 h ago (483/483 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i1t-119447 | eco_20261123_191853_2879776-i1t | 5_2_route | 1.2 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | so_741495_ff_96860 | so_741495_ff_96860 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (845/845 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | so_741495_tt_96860 | so_741495_tt_96860 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (845/845 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2001372 | coll_ftm | 5_2_route | 2.0 | drt_violations best 10172 last 10172 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i2t-245032 | eco_20261123_051704_3678821-i2t | 5_2_route | 3.1 | drt_violations best 1664 last 1664 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2t-2973514 | eco_20261123_063813_234645-i2t | 5_2_route | 4.3 | drt_violations best 259 last 259 rows 7 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | otc-2838041-22529 | 2838041 | ot_bind_native_442ac0130787276840af0197 | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 23.6 | drt_violations best 2939 last 2939 rows 20 | before-window best 13554, window best 2939 | PROGRESS: drt_violations improved 78.3 % in window |  |
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 26.3 | drt_violations best 1617 last 7736 rows 26 | before-window best 1743, window best 1617 | PROGRESS: drt_violations improved 7.2 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 28.5 | drt_violations best 8261 last 28775 rows 18 | before-window best 8936, window best 8261 | PROGRESS: drt_violations improved 7.6 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 25.1 | drt_violations best 39818 last 39818 rows 16 | before-window best 41866, window best 39818 | PROGRESS: drt_violations improved 4.9 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 25.5 | drt_violations best 47053 last 47053 rows 16 | before-window best 48840, window best 47053 | PROGRESS: drt_violations improved 3.7 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 18.8 | drt_violations best 131336 last 131336 rows 3 | before-window best 681573, window best 131336 | PROGRESS: drt_violations improved 80.7 % in window |  |
| epyc7 | dpkit-hd_lep0N_w-1242720 | hd_lep0N_w | pregrt_ff_hold | 1.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 26.2 | drt_violations best 49778 last 49778 rows 16 | before-window best 54432, window best 49778 | PROGRESS: drt_violations improved 8.6 % in window |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 53.5 | last meaningful line 2.5 h ago (646/646 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-cbf_q01_s2-3852085 | cbf_q01_s2 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbn_q01__clab6e67f2-1043557 | cbn_q01 | pregrt_ff_hold | 2.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 36.9 | drt_violations best 18 last 18 rows 56 | before-window best 20, window best 18 | PROGRESS: drt_violations improved 10.0 % in window |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 5_1_grt | 16.7 | last meaningful line 0.1 h ago (2477/2508 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-sle_st_a_v1__cl67389ecd-892590 | sle_st_a_v1 | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v1__clb036e152-920083 | slw_st_a_v1 | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-929975 | slw_st_a_v1 | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 24.2 | drt_violations best 15 last 16 rows 58 | before-window best 16, window best 15 | PROGRESS: drt_violations improved 6.2 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 39.7 | drt_violations best 10495 last 10495 rows 16 | before-window best 29547, window best 10495 | PROGRESS: drt_violations improved 64.5 % in window |  |
| intel1 | dpkit-slice_station__t12-917685 | slice_station__t12 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 26.4 | drt_violations best 80382 last 80382 rows 12 | before-window best 88977, window best 80382 | PROGRESS: drt_violations improved 9.7 % in window |  |
