# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 21:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 1, 'GRT-LABEL': 19, 'YOUNG': 56, 'NO-DATA': 5, 'KEEP': 1, 'EXCLUDED': 2, 'PROGRESS': 16}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 51.1 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 51 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 18.6 | drt_violations best 1 last 1 rows 56 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 36.2 | grt rounds 4 overflow 5:62755 -> 10:60390 -> 15:49088 -> 20:49999 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 36.1 | grt rounds 5 overflow 5:56489 -> 10:43484 -> 15:40478 -> 20:43412 -> 25:50457 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 50.6 | grt rounds 6 overflow 5:9510 -> 10:5086 -> 15:3245 -> 20:2874 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 29.7 | grt rounds 3 overflow 5:77484 -> 10:71484 -> 15:58855 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 34.7 | grt rounds 3 overflow 5:61525 -> 10:63713 -> 15:69180 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 24.1 | grt rounds 3 overflow 5:51174 -> 10:48756 -> 15:39411 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 24.1 | grt rounds 3 overflow 5:49711 -> 10:49628 -> 15:39714 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 33.8 | grt rounds 3 overflow 5:45659 -> 10:49338 -> 15:43227 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 21.5 | grt rounds 4 overflow 5:110533 -> 10:75296 -> 15:54463 -> 20:62289 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 29.8 | grt rounds 4 overflow 5:95535 -> 10:71407 -> 15:50563 -> 20:56554 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 23.6 | grt rounds 4 overflow 5:97308 -> 10:70056 -> 15:50304 -> 20:58440 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 25.3 | grt rounds 4 overflow 5:44451 -> 10:38859 -> 15:36410 -> 20:37714 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 25.3 | grt rounds 6 overflow 5:41833 -> 10:36208 -> 15:31830 -> 20:31076 -> 25:35283 -> 30:32085 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | 5_1_grt | 7.4 | grt rounds 2 overflow 5:39369 -> 10:31446 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 24.9 | grt rounds 4 overflow 5:18628 -> 10:12430 -> 15:11108 -> 20:10187 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 37.8 | grt rounds 4 overflow 5:32844 -> 10:12056 -> 15:8164 -> 20:7612 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 48.5 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10171 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 31.3 | grt rounds 6 overflow 5:18843 -> 10:14920 -> 15:12366 -> 20:11039 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 42.8 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-2216313 | sle_st_b_v1 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (3612/3612 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2218630 | slw_fe_v1 | 2_2_floorplan_macro | 0.2 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-2215543 | slw_fw_v2 | 2_2_floorplan_macro | 0.2 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2215364 | slw_st_b_v2 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (3649/3649 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-1452780-18337 | 1452780 | cut_equiv | 1.1 | last meaningful line 0.0 h ago (858341/858341 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | otc-1610195-24003 | 1610195 | cut_equiv | 0.9 | last meaningful line 0.0 h ago (1043548/1043548 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1-396779 | eco_20261121_154936_3396612-i1 | 5_2_route | 2.0 | drt_violations best 71294 last 71294 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_203102_3392434-i1-2229259 | eco_20261121_203102_3392434-i1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (160/160 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_021210_171272-i1-1528590 | eco_20261122_021210_171272-i1 | 5_2_route | 0.9 | last meaningful line 0.1 h ago (262/263 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | so_2186686_ff_5485 | so_2186686_ff_5485 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc10 | so_2186686_tt_5485 | so_2186686_tt_5485 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-cbf_q00__cl1b5a6458-557330 | cbf_q00 | pregrt_ff_hold | 2.1 | repair_Violations best 737 last 737 rows 43 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 3_5_place_dp | 12.9 | last meaningful line 0.1 h ago (122/122 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | tt_setup_measure_grt | 9.9 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv-767971 | kv3_pv | 3_5_place_dp | 2.0 | last meaningful line 0.3 h ago (52/52 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t14-2503693 | serdes__t14 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.8503 last 0.8503 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | 5_2_route | 14.5 | drt_violations best 14745 last 14745 rows 2 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-1019838 | slw_sc_v1 | 5_2_route | 8.2 | drt_violations best 139030 last 139030 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q11-3840796 | cbf_q11 | 5_1_grt | 8.1 | last meaningful line 5.0 h ago (25/25 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hg_v1p2-672395 | kv3_hg_v1p2 | 5_1_grt | 3.1 | last meaningful line 0.0 h ago (169/169 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2969215 | sle_hc0 | postcts_gate_FF | 8.8 | last meaningful line -0.0 h ago (59202/59202 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-3504337 | sle_hc1 | postcts_gate_FF | 8.4 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3695652 | slw_sc_v2 | postcts_gate_TT | 8.3 | last meaningful line -0.0 h ago (26340/26340 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3669665 | slw_st_b_v1 | 5_1_grt | 8.3 | last meaningful line 0.1 h ago (1329/1383 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 9.1 | drt_violations best 59812 last 59812 rows 10 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc7 | otc-2109716-1750 | 2109716 | - | 2.3 |  | NO-DATA: no log found |  |
| epyc7 | otc-2367330-7554 | 2367330 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc7 | otc-3453949-32696 | 3453949 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-fin-2542120 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (12/12 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-fin-3373883 | fin | 6_1_fill | 0.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q00__cld7bf7197-3404310 | cbn_q00 | 5_1_grt | 7.3 | last meaningful line 1.8 h ago (25/25 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1220988 | col_h9_r0_p2__t1 | pregrt_ff_hold | 1.1 | repair_TNS best 45191.2 last 45191.2 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1220915 | col_h9_r0_p2__t1 | pregrt_ff_hold | 1.1 | repair_TNS best 119483 last 119483 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | tt_setup_repair_grt | 9.2 | last meaningful line 0.2 h ago (18/18 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_1_grt | 9.2 | last meaningful line 1.5 h ago (40/40 lines) | YOUNG: evidence 1.7 h < 6 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-3144441 | kv3_hg_v1p2 | 5_1_grt | 3.0 | last meaningful line 0.0 h ago (167/167 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 8.6 | drt_violations best 1561 last 1561 rows 9 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-187481 | slw_st_a_v2 | 5_1_grt | 2.1 | last meaningful line 0.0 h ago (1166/1168 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 8.4 | drt_violations best 55180 last 55180 rows 7 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261122_024317_3271969-i1t-3547037 | eco_20261122_024317_3271969-i1t | 5_2_route | 2.7 | last meaningful line 0.3 h ago (293/294 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261122_041149_1964199-i1-1023260 | eco_20261122_041149_1964199-i1 | 5_2_route | 1.3 | drt_violations best 1433 last 1433 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v6-1440068 | kv3_pv_v6 | 3_3_place_gp | 1.9 | overflow best 0.1232 last 0.1232 rows 39 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v8-1614044 | kv3_pv_v8 | 3_5_place_dp | 1.8 | last meaningful line 0.1 h ago (136/136 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3008659 | sle_st_b_v1 | 3_3_place_gp | 0.5 | overflow best 0.0995 last 0.0995 rows 46 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3120937 | sle_st_b_v2 | 3_3_place_gp | 0.4 | overflow best 0.2681 last 0.2681 rows 38 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3239813 | slw_hc3 | 3_4_place_resized | 0.3 | last meaningful line 0.0 h ago (399/399 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-1732719-5782 | 1732719 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc9 | otc-1758840-26581 | 1758840 | orfs_synth | 1.7 | last meaningful line 1.5 h ago (421/421 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | otc-2096666-11448 | 2096666 | 3_2_place_iop | 1.5 | last meaningful line 1.3 h ago (34/34 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i2-745368 | eco_20261121_070035_1645318-i2 | 5_2_route | 2.4 | drt_violations best 14377 last 14377 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | prd-eco_r3_residual-i1-799917 | eco_r3_residual-i1 | 5_2_route | 2.3 | drt_violations best 164 last 164 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-207847 | slw_hc3 | 3_4_place_resized | 0.5 | last meaningful line 0.0 h ago (400/400 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-216407 | slw_st_b_v1 | 3_3_place_gp | 0.4 | overflow best 0.6431 last 0.6431 rows 24 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i3t-3010955 | eco_20261120_192428_3309571-i3t | 5_2_route | 1.9 | drt_violations best 19107 last 19107 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1t-203702 | eco_20261121_161716_4143584-i1t | 5_2_route | 5.2 | drt_violations best 92 last 92 rows 13 | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_1_grt | 3.6 | repair_Viol best 886 last 886 rows 2 | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4007898 | col_h9_r1__t1 | 5_1_grt | 6.2 | last meaningful line 0.1 h ago (202/208 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2222604 | coll_ftm | 5_1_grt | 0.5 | repair_Remaining best 27817 last 27817 rows 22 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-2227944 | hd_turn_a | 5_2_route | 0.5 | drt_violations best 4894 last 4894 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2776273 | ot_s81sl_kv_leaf__t5 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (702/702 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 38.4 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel2 | otc-2574367-13183 | 2574367 | - | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | otc-2744092-20141 | 2744092 | - | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 42.7 | last meaningful line 1.1 h ago (1550/1550 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-cbf_q01_s2-557381 | cbf_q01_s2 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | 5_1_grt | 8.0 | repair_TNS best 0 last 0 rows 10 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 6.5 | last meaningful line 4.8 h ago (622/622 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1722167 | col_h9_r1__t1 | pregrt_ff_hold | 0.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-3022331 | sle_ctl | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | otc-431765-18007 | 431765 | tt_setup_repair_grt | 1.9 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | otc-451257-8041 | 451257 | tt_setup_repair_grt | 1.9 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | otc-709044-23442 | 709044 | tt_setup_repair_grt | 1.7 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2289240 | col_h10_r1__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-hd_ctl-1585232 | hd_ctl | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-hd_mesh-3170867 | hd_mesh | pregrt_ff_hold | 4.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | otc-1453349-16601 | 1453349 | tt_setup_repair_grt | 1.9 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | otc-1458714-4592 | 1458714 | tt_setup_repair_grt | 1.9 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 10.5 | drt_violations best 571 last 649 rows 31 | before-window best 1965, window best 571 | PROGRESS: drt_violations improved 70.9 % in window |  |
| intel2 | dpkit-kv3_io_ft-2215245 | kv3_io_ft | 5_1_grt | 0.5 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
