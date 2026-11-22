# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 22:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 1, 'CANCEL-NOW': 2, 'GRT-LABEL': 18, 'YOUNG': 66, 'NO-DATA': 4, 'EXCLUDED': 3, 'KEEP': 1, 'PROGRESS': 12}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 51.3 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 51 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 18.9 | drt_violations best 1 last 1 rows 56 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-3080706 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 6_1_merge | 0.5 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-3092454 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 3_5_place_dp | 0.5 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 36.4 | grt rounds 4 overflow 5:62755 -> 10:60390 -> 15:49088 -> 20:49999 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 36.4 | grt rounds 5 overflow 5:56489 -> 10:43484 -> 15:40478 -> 20:43412 -> 25:50457 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 50.8 | grt rounds 6 overflow 5:9510 -> 10:5086 -> 15:3245 -> 20:2874 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 30.2 | grt rounds 3 overflow 5:77484 -> 10:71484 -> 15:58855 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 35.2 | grt rounds 3 overflow 5:61525 -> 10:63713 -> 15:55011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 24.6 | grt rounds 3 overflow 5:51174 -> 10:49018 -> 15:39411 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 24.6 | grt rounds 3 overflow 5:49711 -> 10:49628 -> 15:39714 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 34.3 | grt rounds 3 overflow 5:45659 -> 10:49338 -> 15:43227 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 22.0 | grt rounds 4 overflow 5:110533 -> 10:75296 -> 15:54463 -> 20:62289 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 30.3 | grt rounds 4 overflow 5:95535 -> 10:71407 -> 15:50563 -> 20:56554 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 24.1 | grt rounds 4 overflow 5:97308 -> 10:70056 -> 15:50304 -> 20:58440 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 25.8 | grt rounds 4 overflow 5:44451 -> 10:38859 -> 15:36410 -> 20:37714 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | 5_1_grt | 7.9 | grt rounds 2 overflow 5:39369 -> 10:31446 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 25.4 | grt rounds 4 overflow 5:20337 -> 10:12430 -> 15:11108 -> 20:10187 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 38.3 | grt rounds 4 overflow 5:32844 -> 10:12056 -> 15:8164 -> 20:7612 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 49.0 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 31.8 | grt rounds 6 overflow 5:18843 -> 10:13916 -> 15:12366 -> 20:11039 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 43.3 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-2602583 | coll_core | 2_1_floorplan | 0.1 | repair_Viol best 1485 last 1485 rows 74 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-coll_ftc-2553210 | coll_ftc | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hroot-2497950 | kv3_hroot | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-2216313 | sle_st_b_v1 | 2_1_floorplan | 0.5 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2218630 | slw_fe_v1 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (296/296 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-2215543 | slw_fw_v2 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (255/255 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2215364 | slw_st_b_v2 | 2_1_floorplan | 0.5 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-1452780-18337 | 1452780 | cut_equiv | 1.3 | last meaningful line 0.0 h ago (858727/858727 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | otc-1610195-24003 | 1610195 | cut_equiv | 1.1 | last meaningful line 0.0 h ago (1104809/1104809 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1-396779 | eco_20261121_154936_3396612-i1 | 5_2_route | 2.2 | drt_violations best 71294 last 71294 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_203102_3392434-i1-2229259 | eco_20261121_203102_3392434-i1 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (253/444 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_021210_171272-i1-1528590 | eco_20261122_021210_171272-i1 | 5_2_route | 1.1 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl1b5a6458-557330 | cbf_q00 | 5_1_grt | 2.4 | last meaningful line 0.1 h ago (25/25 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 3_5_place_dp | 13.2 | last meaningful line 0.3 h ago (122/122 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | postcts_gate_FF | 10.1 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv-767971 | kv3_pv | 3_5_place_dp | 2.3 | last meaningful line 0.1 h ago (135/135 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t14-2503693 | serdes__t14 | 3_3_place_gp | 0.8 | overflow best 0.6677 last 0.6677 rows 31 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3100134 | sle_su_l1 | 3_3_place_gp | 0.2 | overflow best 0.2608 last 0.2608 rows 28 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | 5_2_route | 14.8 | drt_violations best 9248 last 9248 rows 3 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-1019838 | slw_sc_v1 | 5_2_route | 8.4 | drt_violations best 139030 last 139030 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q11-3840796 | cbf_q11 | 5_1_grt | 8.6 | last meaningful line 5.5 h ago (25/25 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2277324 | col_h10_r0_p4__t1 | 2_1_floorplan | 0.1 | repair_Viol best 6050 last 6050 rows 1392 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-iqf__t1-2289342 | iqf__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hg_v1p2-672395 | kv3_hg_v1p2 | 5_1_grt | 3.6 | last meaningful line 0.3 h ago (307/1311 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | tt_setup_repair_grt | 8.5 | repair_Remaining best 54442 last 54442 rows 417 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2969215 | sle_hc0 | 5_2_route | 9.3 | last meaningful line 0.0 h ago (264/265 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-3504337 | sle_hc1 | postcts_gate_FF | 8.9 | last meaningful line -0.0 h ago (34397/34397 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3695652 | slw_sc_v2 | 5_2_route | 8.8 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3669665 | slw_st_b_v1 | postcts_gate_TT | 8.8 | last meaningful line 0.0 h ago (969/969 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | eco-abs-1967534 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | eco-abs-2008631 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.1 h ago (1028/1028 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | otc-2277411-9957 | 2277411 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-cbn_q00__cld7bf7197-3404310 | cbn_q00 | 5_1_grt | 7.8 | last meaningful line 2.3 h ago (25/25 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1220988 | col_h9_r0_p2__t1 | 5_1_grt | 1.6 | last meaningful line 0.0 h ago (155/155 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | tt_setup_repair_grt | 9.7 | last meaningful line 0.5 h ago (18/18 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_1_grt | 9.7 | last meaningful line 2.0 h ago (40/40 lines) | YOUNG: evidence 2.2 h < 6 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1722167 | col_h9_r1__t1 | 5_1_grt | 1.1 | last meaningful line 0.1 h ago (202/208 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-3144441 | kv3_hg_v1p2 | 5_1_grt | 3.5 | last meaningful line 0.3 h ago (307/309 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-3022331 | sle_ctl | 5_1_grt | 3.7 | last meaningful line 0.0 h ago (166/166 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 9.1 | drt_violations best 1470 last 1470 rows 11 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 8.9 | drt_violations best 54158 last 54158 rows 8 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261122_024317_3271969-i1t-3547037 | eco_20261122_024317_3271969-i1t | 5_2_route | 3.2 | last meaningful line 0.4 h ago (297/298 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | prd-fin-1023260 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2289240 | col_h10_r1__t1 | 5_1_grt | 1.8 | last meaningful line 0.1 h ago (203/209 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-4042439 | col_h10_r1__t1 | 2_1_floorplan | 0.0 | repair_Viol best 3559 last 3559 rows 826 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-hd_ctl-1585232 | hd_ctl | 5_1_grt | 2.4 | last meaningful line 0.0 h ago (204/262 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v6-1440068 | kv3_pv_v6 | 3_3_place_gp | 2.4 | overflow best 0.0988 last 0.0988 rows 42 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5499/5499 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3696149 | slw_hc3 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (4872/4872 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | otc-1732719-5782 | 1732719 | - | 2.3 |  | NO-DATA: no log found |  |
| epyc9 | otc-1758840-26581 | 1758840 | orfs_synth | 2.2 | last meaningful line 2.0 h ago (421/421 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | otc-4019702-12021 | 4019702 | orfs_synth | 0.1 | last meaningful line 0.1 h ago (418/418 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i2-745368 | eco_20261121_070035_1645318-i2 | 5_2_route | 2.9 | drt_violations best 2178 last 2178 rows 6 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | prd-fin-799917 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | ap-ageom-kw-slw-st-b-v1--cl6357f1cc--pv6ace3e48-grt-1116515 | slw-st-b-v1--cl6357f1cc--pv6ace3e48-grt | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | dpkit-kv3_hroot-1194403 | kv3_hroot | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1018623 | sle_st_b_v2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (417/417 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-838976 | slw_hc3 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (4685/4685 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | ot-canary-1197469 | ot-canary | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261120_192428_3309571-i3t-3010955 | eco_20261120_192428_3309571-i3t | 5_2_route | 2.4 | drt_violations best 19 last 19 rows 6 | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 0.7 | last meaningful line 0.0 h ago (257/257 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1t-203702 | eco_20261121_161716_4143584-i1t | 5_2_route | 5.7 | drt_violations best 62 last 62 rows 14 | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_2_route | 4.1 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2222604 | coll_ftm | 5_2_route | 1.0 | last meaningful line 0.0 h ago (225/225 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-4069341 | hd_turn_a | postcts_gate_FF | 0.2 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-4082903 | hd_turn_a | postcts_gate_TT | 0.2 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-4082983 | hd_turn_a | postcts_gate_TT | 0.2 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-2215245 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5406 last 5406 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-3121192 | slice_station__t12 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (210/210 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-2473542-30530 | 2473542 | asbuilt.yosys | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc8 | otc-2889465-30687 | 2889465 | asbuilt.yosys | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 38.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel2 | otc-4077401-21786 | 4077401 | asbuilt.yosys | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 43.0 | last meaningful line 1.4 h ago (1550/1550 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-cbf_q01_s2-557381 | cbf_q01_s2 | pregrt_ff_hold | 2.4 | repair_Violations best 0 last 0 rows 21 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 9.6 | drt_violations best 55390 last 55390 rows 11 | before-window best 181727, window best 55390 | PROGRESS: drt_violations improved 69.5 % in window |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 7.0 | last meaningful line 5.3 h ago (622/622 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1220915 | col_h9_r0_p2__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | otc-2471981-17038 | 2471981 | tt_setup_repair_grt | 0.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | otc-451257-8041 | 451257 | tt_setup_repair_grt | 2.4 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | otc-709044-23442 | 709044 | tt_setup_repair_grt | 2.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-3670266 | col_h10_r1__t1 | 3_5_place_dp | 0.4 | repair_Violations best 0 last 0 rows 38 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-hd_mesh-3170867 | hd_mesh | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | otc-3997493-16991 | 3997493 | tt_setup_repair_grt | 0.1 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 11.0 | drt_violations best 571 last 3267 rows 34 | before-window best 1428, window best 571 | PROGRESS: drt_violations improved 60.0 % in window |  |
