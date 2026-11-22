# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 20:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'CANCEL-NOW': 2, 'GRT-LABEL': 14, 'NO-DATA': 7, 'YOUNG': 47, 'KEEP': 1, 'EXCLUDED': 1, 'PROGRESS': 16}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 50.3 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 50 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-590838 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 3_3_place_gp | 0.2 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-590838-lec | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | lec | 0.1 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 35.4 | grt rounds 4 overflow 5:62755 -> 10:62005 -> 15:49088 -> 20:49999 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 35.4 | grt rounds 5 overflow 5:56489 -> 10:43484 -> 15:40478 -> 20:43412 -> 25:50457 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 49.8 | grt rounds 6 overflow 5:9510 -> 10:5086 -> 15:3245 -> 20:2874 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 39.1 | grt rounds 4 overflow 5:54036 -> 10:38366 -> 15:34625 -> 20:37819 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 24.2 | grt rounds 4 overflow 5:18628 -> 10:12430 -> 15:11108 -> 20:10187 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 37.0 | grt rounds 4 overflow 5:32844 -> 10:12056 -> 15:8164 -> 20:7612 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 47.8 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10171 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 48.0 | grt rounds 5 overflow 5:32681 -> 10:30734 -> 15:25360 -> 20:23105 -> 25:31808 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 30.3 | grt rounds 6 overflow 5:19221 -> 10:14920 -> 15:12366 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 25.3 | grt rounds 4 overflow 5:35977 -> 10:30237 -> 15:24172 -> 20:20900 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 46.6 | grt rounds 4 overflow 5:67513 -> 10:54044 -> 15:50242 -> 20:55216 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 41.9 | grt rounds 3 overflow 5:59246 -> 10:46138 -> 15:41146 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 41.9 | grt rounds 3 overflow 5:60515 -> 10:47029 -> 15:41606 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 42.1 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-kv3-hg-v1p4-grt-1504132 | kv3-hg-v1p4-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-serdes__t4-293755 | serdes__t4 | 6_report | 10.5 | last meaningful line -0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_su_c-988292 | sle_su_c | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (416/416 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-1452780-18337 | 1452780 | cut_equiv | 0.3 | last meaningful line 0.1 h ago (854881/854881 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | otc-1610195-24003 | 1610195 | cut_equiv | 0.1 | last meaningful line 0.0 h ago (156519/156519 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-count-p1_tc-646001 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (214/214 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1-396779 | eco_20261121_154936_3396612-i1 | 5_2_route | 1.2 | last meaningful line 0.2 h ago (282/283 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-kv3-hg-v1-grt-2182946 | kv3-hg-v1-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-kv3-hg-v1p2-grt-2271217 | kv3-hg-v1p2-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1p5-328056 | kv3_hg_v1p5 | 3_5_place_dp | 1.5 | last meaningful line 0.1 h ago (129/129 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 3_4_place_resized | 12.2 | last meaningful line 2.3 h ago (519/519 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | 5_1_grt | 9.1 | last meaningful line 0.0 h ago (1112/1118 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv-767971 | kv3_pv | 3_3_place_gp | 1.3 | overflow best 0.1 last 0.1 rows 40 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | 5_2_route | 13.8 | drt_violations best 95161 last 95161 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-1019838 | slw_sc_v1 | 5_2_route | 7.4 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | so_2154701_ff_47476 | so_2154701_ff_47476 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | so_2154701_tt_47476 | so_2154701_tt_47476 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-cbn_q00__cld7bf7197-3404310 | cbn_q00 | 5_1_grt | 6.5 | last meaningful line 1.0 h ago (25/25 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1220988 | col_h9_r0_p2__t1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3452/3452 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1220915 | col_h9_r0_p2__t1 | tt_setup_repair | 0.3 | last meaningful line 0.0 h ago (301/301 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_1_grt | 8.4 | last meaningful line 0.8 h ago (40/40 lines) | YOUNG: evidence 0.9 h < 6 h |  |
| epyc8 | dpkit-coll_ftc-964552 | coll_ftc | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (3420/3420 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-3144441 | kv3_hg_v1p2 | 5_1_grt | 2.3 | last meaningful line 0.3 h ago (43/43 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-3022331 | sle_ctl | 4_1_cts | 2.4 | last meaningful line 0.1 h ago (8735/8735 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-850569 | slw_fe_v1 | generate_abstract | 15.5 | last meaningful line 0.1 h ago (724/724 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 7.9 | drt_violations best 5832 last 5832 rows 3 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 7.7 | drt_violations best 60545 last 60545 rows 4 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261122_024317_3271969-i1t-3547037 | eco_20261122_024317_3271969-i1t | 5_2_route | 1.9 | last meaningful line 0.1 h ago (287/288 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | prd-eco_20261122_041149_1964199-i1-1023260 | eco_20261122_041149_1964199-i1 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | so_1155096_ff_59777 | so_1155096_ff_59777 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc8 | so_1155096_tt_59777 | so_1155096_tt_59777 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2289240 | col_h10_r1__t1 | pregrt_ff_hold | 0.6 | repair_TNS best 69202.3 last 69202.3 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v6-1440068 | kv3_pv_v6 | 2_4_floorplan_pdn | 1.2 | last meaningful line 0.0 h ago (91/91 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v8-1614044 | kv3_pv_v8 | 3_3_place_gp | 1.1 | overflow best 0.1582 last 0.1582 rows 36 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | otc-1732719-5782 | 1732719 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-1758840-26581 | 1758840 | orfs_synth | 1.0 | last meaningful line 0.8 h ago (421/421 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | otc-2096666-11448 | 2096666 | 3_2_place_iop | 0.7 | last meaningful line 0.5 h ago (34/34 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i2-745368 | eco_20261121_070035_1645318-i2 | 5_2_route | 1.6 | last meaningful line 0.2 h ago (282/283 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | prd-eco_r3_residual-i1-799917 | eco_r3_residual-i1 | 5_2_route | 1.6 | last meaningful line 0.1 h ago (271/272 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | ap-ageom-kw-sle-st-a-v1--cl989804f6--cl18eece69-grt-3773778 | sle-st-a-v1--cl989804f6--cl18eece69-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_io_cor_v1-3312033 | kv3_io_cor_v1 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_io_ft-2751771 | kv3_io_ft | 5_2_route | 1.1 | drt_violations best 5406 last 5406 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3631586 | sle_st_b_v2 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t12-3454375 | slice_station__t12 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (207/207 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-3224056 | slw_st_b_v1 | 3_3_place_gp | 0.7 | overflow best 0.0989 last 0.0989 rows 46 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | ot-canary-3905247 | ot-canary | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261120_192428_3309571-i3t-3010955 | eco_20261120_192428_3309571-i3t | 5_2_route | 0.9 | last meaningful line 0.1 h ago (264/265 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i1-1189865 | eco_20261121_082001_3216437-i1 | 5_2_route | 3.0 | drt_violations best 43516 last 43516 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1t-203702 | eco_20261121_161716_4143584-i1t | 5_2_route | 4.2 | drt_violations best 3348 last 3348 rows 9 | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_1_grt | 2.6 | repair_Viol best 886 last 886 rows 2 | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4007898 | col_h9_r1__t1 | 5_1_grt | 5.5 | last meaningful line 3.5 h ago (40/40 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3132815 | coll_ftm | 6_report | 2.5 | last meaningful line 0.0 h ago (65/65 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-196126 | hd_turn_a | 5_2_route | 0.5 | drt_violations best 4894 last 4894 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-268502 | ot_s81sl_kv_leaf__t5 | 2_1_floorplan | 0.4 | repair_Viol best 1304 last 1304 rows 1287 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 37.6 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel2 | otc-1005060-6027 | 1005060 | - | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | prd-eco_20261122_021210_171272-i1-1528590 | eco_20261122_021210_171272-i1 | 5_1_grt | 0.1 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 42.0 | last meaningful line 0.4 h ago (1550/1550 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-cbf_q00__cl1b5a6458-557330 | cbf_q00 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-cbf_q01_s2-557381 | cbf_q01_s2 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 17.9 | drt_violations best 1 last 2 rows 54 | before-window best 2, window best 1 | PROGRESS: drt_violations improved 50.0 % in window |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | 5_1_grt | 8.4 | repair_TNS best 0 last 0 rows 14 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-187481 | slw_st_a_v2 | 5_1_grt | 1.4 | repair_TNS best 0 last 0 rows 4 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | otc-431765-18007 | 431765 | tt_setup_repair_grt | 1.1 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | otc-451257-8041 | 451257 | tt_setup_repair_grt | 1.1 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | otc-709044-23442 | 709044 | tt_setup_repair_grt | 0.9 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-hd_ctl-1585232 | hd_ctl | pregrt_ff_hold | 1.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-hd_mesh-3170867 | hd_mesh | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | otc-1453349-16601 | 1453349 | tt_setup_repair_grt | 1.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | otc-1458714-4592 | 1458714 | tt_setup_repair_grt | 1.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 9.7 | drt_violations best 571 last 650 rows 30 | before-window best 3922, window best 571 | PROGRESS: drt_violations improved 85.4 % in window |  |
| intel1 | prd-eco_20261121_075836_1991905-i1t-1821063 | eco_20261121_075836_1991905-i1t | 5_2_route | 12.5 | drt_violations best 91 last 91 rows 14 | before-window best 16417, window best 91 | PROGRESS: drt_violations improved 99.4 % in window |  |
