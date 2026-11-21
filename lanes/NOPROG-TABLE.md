# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 01:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'GRT-LABEL': 46, 'YOUNG': 205, 'NO-DATA': 18, 'KEEP': 2, 'EXCLUDED': 4, 'PROGRESS': 15}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-2086479 | hd_lep0N | pregrt_ff_hold | 5.9 | repair_TNS best 193787 last 193787 rows 1 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -454.73 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub cancels after the report hour) |
| epyc10 | dpkit-tt_ctlm-4105966 | tt_ctlm | tt_setup_repair_grt | 7.2 | repair_Viol best 5512 last 5512 rows 1 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -351.68 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub cancels after the report hour) |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-2994465 | col_h9_r0_p5__t1 | 5_1_grt | 7.8 | grt rounds 3 overflow 5:4784 -> 10:1838 -> 15:1520 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_lep0N-2362622 | hd_lep0N | 5_1_grt | 17.1 | grt rounds 2 overflow 5:95762 -> 10:93332 | GRT-LABEL: DESIGN-FAIL: overflow 93332 at round 10 > 1000 |  |
| epyc10 | dpkit-hd_lep0N-304519 | hd_lep0N | 5_1_grt | 28.3 | grt rounds 3 overflow 5:52450 -> 10:47147 -> 15:43051 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | 5_1_grt | 28.5 | grt rounds 3 overflow 5:77669 -> 10:64592 -> 15:70550 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 17.4 | grt rounds 6 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 27.0 | grt rounds 4 overflow 5:27938 -> 10:20130 -> 15:12231 -> 20:10781 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 15.9 | grt rounds 3 overflow 5:62592 -> 10:60195 -> 15:50065 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2132807 | ot_s81sl_leaf__t44 | 5_1_grt | 5.9 | grt rounds 3 overflow 5:62900 -> 10:59002 -> 15:49395 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 15.9 | grt rounds 3 overflow 5:50202 -> 10:43383 -> 15:40589 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 36.2 | grt rounds 4 overflow 5:55847 -> 10:40235 -> 15:37035 -> 20:39027 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 30.3 | grt rounds 4 overflow 5:9414 -> 10:5163 -> 15:3337 -> 20:3104 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 30.8 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 19.6 | grt rounds 3 overflow 5:50575 -> 10:40510 -> 15:34585 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | 5_1_grt | 19.8 | grt rounds 6 overflow 5:6798 -> 10:4941 -> 15:2610 -> 20:2287 -> 25:3051 -> 30:2207 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbf_q11-283336 | cbf_q11 | 5_1_grt | 4.7 | grt rounds 2 overflow 5:6375 -> 10:5827 | GRT-LABEL: DESIGN-FAIL: overflow 5827 at round 10 > 1000 |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-645545 | col_h9_r0_p5__t1 | 5_1_grt | 4.5 | grt rounds 2 overflow 5:32301 -> 10:22118 | GRT-LABEL: DESIGN-FAIL: overflow 22118 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 9.5 | grt rounds 2 overflow 5:94966 -> 10:134399 | GRT-LABEL: DESIGN-FAIL: overflow 134399 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 14.4 | grt rounds 2 overflow 5:83767 -> 10:75075 | GRT-LABEL: DESIGN-FAIL: overflow 75075 at round 10 > 1000 |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 3.8 | grt rounds 2 overflow 5:56566 -> 10:49891 | GRT-LABEL: DESIGN-FAIL: overflow 49891 at round 10 > 1000 |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 3.8 | grt rounds 2 overflow 5:57966 -> 10:49002 | GRT-LABEL: DESIGN-FAIL: overflow 49002 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 13.6 | grt rounds 3 overflow 5:46084 -> 10:49107 -> 15:43557 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2178470 | ot_s81sl_leaf__t39 | 5_1_grt | 3.5 | grt rounds 2 overflow 5:59009 -> 10:41457 | GRT-LABEL: DESIGN-FAIL: overflow 41457 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 9.5 | grt rounds 2 overflow 5:92389 -> 10:72264 | GRT-LABEL: DESIGN-FAIL: overflow 72264 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 5.1 | grt rounds 3 overflow 5:38551 -> 10:38976 -> 15:36671 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 5.0 | grt rounds 3 overflow 5:35093 -> 10:37699 -> 15:33847 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-478083 | col_h9_r0_p2__t1 | 5_1_grt | 25.5 | grt rounds 5 overflow 5:707 -> 10:519 -> 15:231 -> 20:93 -> 25:3 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pvef55eb84-4139703 | col_h9_r0_p2__t1 | 5_1_grt | 4.7 | grt rounds 3 overflow 5:597 -> 10:874 -> 15:319 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 4.7 | grt rounds 3 overflow 5:18016 -> 10:14391 -> 15:13113 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 26.8 | grt rounds 5 overflow 5:38322 -> 10:24729 -> 15:20068 -> 20:18920 -> 25:36016 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-3619477 | col_h9_r0_p5__t1 | 5_1_grt | 5.9 | grt rounds 3 overflow 5:3874 -> 10:1838 -> 15:1534 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-hd_lep0N-579160 | hd_lep0N | 5_1_grt | 66.4 | grt rounds 3 overflow 5:50257 -> 10:47564 -> 15:42444 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 17.5 | grt rounds 3 overflow 5:26957 -> 10:13844 -> 15:10455 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 28.3 | grt rounds 4 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 28.5 | grt rounds 3 overflow 5:30207 -> 10:30821 -> 15:26039 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | 5_1_grt | 9.6 | grt rounds 2 overflow 5:54696 -> 10:6171 | GRT-LABEL: DESIGN-FAIL: overflow 6171 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-2942763 | col_h9_r0_p5__t1 | 5_1_grt | 5.5 | grt rounds 2 overflow 5:45133 -> 10:28997 | GRT-LABEL: DESIGN-FAIL: overflow 28997 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 10.8 | grt rounds 4 overflow 5:18843 -> 10:13916 -> 15:11809 -> 20:11039 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 5.8 | grt rounds 3 overflow 5:33037 -> 10:33315 -> 15:25641 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 27.8 | grt rounds 4 overflow 5:50603 -> 10:40835 -> 15:38869 -> 20:43366 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 27.1 | grt rounds 3 overflow 5:55450 -> 10:53941 -> 15:50262 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | 5_1_grt | 8.8 | grt rounds 4 overflow 5:35006 -> 10:2129 -> 15:845 -> 20:1134 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 22.4 | grt rounds 2 overflow 5:60387 -> 10:47822 | GRT-LABEL: DESIGN-FAIL: overflow 47822 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 22.4 | grt rounds 2 overflow 5:61726 -> 10:48832 | GRT-LABEL: DESIGN-FAIL: overflow 48832 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 22.6 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | 5_1_grt | 26.0 | grt rounds 3 overflow 5:74897 -> 10:74300 -> 15:66169 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-279781 | ot_s81sl_leaf__t9 | 5_1_grt | 8.8 | grt rounds 3 overflow 5:41481 -> 10:46672 -> 15:39210 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3401748 | col_h9_r0_p2__t1 | 5_2_route | 5.1 | last meaningful line 0.1 h ago (279/280 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-3397522 | col_h9_r0_p2__t1 | 5_2_route | 5.1 | last meaningful line 0.2 h ago (285/286 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Ei-2127701 | kv3_hub_Ei | 4_1_cts | 5.9 | last meaningful line 0.1 h ago (7471/7471 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | 5_1_grt | 27.4 | last meaningful line 1.0 h ago (214/220 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc2__cla3497502__cl16607c7a-2442091 | slw_hc2 | 5_1_grt | 5.7 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_2_route | 5.9 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | phscan-3156354 | phscan | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | prd-eco_20261120_233525_2680444-i2t-1482642 | eco_20261120_233525_2680444-i2t | 5_2_route | 1.1 | drt_violations best 41881 last 41881 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc10 | prd-eco_20261121_014354_2681516-i1-2427560 | eco_20261121_014354_2681516-i1 | 5_2_route | 3.3 | drt_violations best 18 last 31 rows 18 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | so_2760836_ff_49367 | so_2760836_ff_49367 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (706/706 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | so_2760836_tt_49367 | so_2760836_tt_49367 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (706/706 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | tg2130-t60_conv-2667653 | tg2130-t60_conv | 4_1_cts | 0.3 | repair_Violations best 5312 last 5312 rows 20 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | tg2130-t60_convR-2644207 | tg2130-t60_convR | tg_cts | 0.3 | repair_Violations best 3845 last 3845 rows 26 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-coll_ftc-1206090 | coll_ftc | 5_2_route | 6.8 | drt_violations best 72742 last 72742 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | 5_1_grt | 8.1 | last meaningful line 0.2 h ago (1312/1318 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | tt_setup_repair_grt | 8.1 | repair_Viol best 1 last 1 rows 2 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_sc_v2-3023909 | sle_sc_v2 | 5_2_route | 10.6 | drt_violations best 106154 last 106154 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-2275472 | sle_sc_v3 | 5_2_route | 8.1 | drt_violations best 89507 last 89507 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | 5_1_grt | 7.9 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | postcts_gate_FF | 10.2 | last meaningful line -0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | 5_2_route | 10.8 | last meaningful line 0.1 h ago (283/284 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | postcts_gate_FF | 8.7 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | 5_2_route | 10.2 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | postcts_gate_FF | 8.7 | last meaningful line 0.1 h ago (1841/1841 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | 5_2_route | 10.5 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | 5_2_route | 10.8 | last meaningful line 0.1 h ago (261/262 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | 5_2_route | 10.6 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | 5_2_route | 10.2 | drt_violations best 143968 last 143968 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-400280 | slw_st_a_v1 | 2_1_floorplan | 0.1 | repair_Viol best 2328 last 2328 rows 510 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | tt_setup_repair_grt | 9.3 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-401138 | slw_st_b_v2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (233/233 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | 5_2_route | 10.6 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | tt_setup_repair_grt | 8.7 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | 5_2_route | 11.9 | drt_violations best 16082 last 16082 rows 9 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_2_route | 8.1 | drt_violations best 116798 last 116798 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-3141066 | svc_hi_dsdv_svc_pvso_entry__t2 | 3_4_place_resized | 10.5 | repair_Remaining best 2.04036e+06 last 2.04036e+06 rows 1385 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t5-801765 | svc_hi_dsdv_svc_rs__t5 | 3_1_place_gp_skip_io | 7.0 | overflow best 0.214 last 0.3552 rows 203 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-508253 | svc_lo_dsdv_svc_rs__t1 | port_bind | 7.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t3-473545 | svc_lo_dsdv_svc_rs__t3 | port_bind | 7.1 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i2t-458842 | eco_20261120_134605_3273412-i2t | 5_2_route | 2.7 | drt_violations best 16158 last 16158 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i1-1137379 | eco_20261120_170022_4017640-i1 | 5_2_route | 2.3 | last meaningful line 0.1 h ago (282/283 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1t-3059556 | eco_20261120_192837_2855950-i1t | 5_2_route | 5.7 | drt_violations best 3231 last 3231 rows 9 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i2t-1141280 | eco_recover1120-i2t | 5_2_route | 2.3 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-dsdv-slice-c1x-C--t1-grt-3410141 | dsdv-slice-c1x-C--t1-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-bk_sel__t2-1782532 | bk_sel__t2 | 3_3_place_gp | 1.2 | last meaningful line 0.0 h ago (116/116 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2503658 | col_h10_r0_p4__t1 | postplace_setup | 0.7 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-3137478 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_host_w-3583928 | hd_host_w | postplace_setup | 0.0 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-3433822 | hd_lep0N | synth_odb_v | 0.1 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_mesh-2844408 | hd_mesh | 3_3_place_gp | 0.5 | overflow best 0.3055 last 0.4052 rows 42 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-hd_serdes-2333832 | hd_serdes | 3_3_place_gp | 0.8 | overflow best 0.9439 last 0.9445 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-kv3_hgi_v1__cl141fc26e-3409100 | kv3_hgi_v1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (476/476 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pc_v3-3463607 | kv3_pc_v3 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-197680 | kv3_pv_v8 | 4_1_cts | 4.8 | last meaningful line 0.8 h ago (15546/15546 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (3201/3202 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1938916 | ot_s81sl_leaf__t39 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (3193/3194 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3897522 | ot_s81sl_leaf__t39 | 5_1_grt | 2.5 | last meaningful line 0.3 h ago (202/206 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t52-2149380 | ot_s81sl_leaf__t52 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t1__clb45db5be-2606808 | serdes__t1 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.2 h ago (92/92 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t4-2629795 | serdes__t4 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.2 h ago (130/130 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-4021915 | sle_fe_v1 | 5_1_grt | 5.0 | last meaningful line 0.5 h ago (213/1383 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-2646906 | sle_hc2 | 3_3_place_gp | 0.6 | overflow best 0.2975 last 0.4833 rows 64 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl67389ecd-3606936 | sle_st_a_v1 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-3426094 | sle_st_a_v1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-3426855 | sle_st_a_v1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-3460537 | sle_st_a_v2 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-3988031 | sle_stm_v1 | postcts_gate_FF | 5.0 | last meaningful line -0.0 h ago (23742/23742 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t25-501299 | slice_station__t25 | 5_2_route | 4.6 | last meaningful line 0.1 h ago (134/134 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t40__clc8fb2c8c-3403236 | slice_station__t40 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.998 last 0.998 rows 6 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-slice_station__t6__cl0755c26e-3419222 | slice_station__t6 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.9978 last 0.9978 rows 13 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3248657 | slw_fw_v1 | postcts_gate_TT | 8.7 | last meaningful line 0.0 h ago (944/944 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-3255088 | slw_fw_v1 | tt_setup_repair_grt | 8.7 | last meaningful line 0.0 h ago (862/862 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-118433 | slw_hc0 | 5_1_grt | 4.8 | last meaningful line 0.2 h ago (210/861 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-443851 | slw_sc_v1 | 5_2_route | 10.9 | drt_violations best 2 last 2 rows 7 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v2__clf4365a62-3581730 | slw_st_a_v2 | 2_1_floorplan | 0.0 | repair_Viol best 2348 last 2348 rows 34 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-4010968 | slw_stm_v1 | postcts_gate_TT | 5.0 | last meaningful line 0.2 h ago (707/707 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3259392 | slw_stm_v1 | postcts_gate_TT | 8.7 | last meaningful line 0.1 h ago (1515/1515 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_c__cl92142dac-3094393 | slw_su_c | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (192/192 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l0__cl1a1c1f8f-3425537 | slw_su_l0 | 3_3_place_gp | 0.1 | overflow best 0.5026 last 0.5026 rows 3 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_2_route | 9.0 | drt_violations best 21735 last 21735 rows 7 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t6-2568141 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 3.2 | last meaningful line 0.0 h ago (648/648 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 15.8 |  | NO-DATA: no log found |  |
| epyc7 | fv0030-head_lep0N_tr1-2515251 | fv0030-head_lep0N_tr1 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | otc-3621382-14232 | 3621382 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | so_3403556_ff_26390 | so_3403556_ff_26390 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | so_3403556_tt_26390 | so_3403556_tt_26390 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-cbf_q01-4192371 | cbf_q01 | 5_1_grt | 4.7 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-591220 | col_h10_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.421 last 0.421 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-4140201 | col_h9_r0_p2__t1 | tt_setup_repair_grt | 4.7 | repair_Viol best 497 last 497 rows 236 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-4171287 | col_h9_r0_p2__t1 | 5_1_grt | 14.4 | last meaningful line 5.0 h ago (207/234 lines) | YOUNG: evidence 5.6 h < 6 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | 5_2_route | 4.7 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | 5_2_route | 4.7 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bab1162-4136986 | col_h9_r1__t1 | 5_2_route | 4.7 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-4137431 | col_h9_r1__t1 | 5_2_route | 4.7 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv534ef85e-4134713 | col_h9_r1__t1 | 5_2_route | 4.7 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvf0f1ccb2-4137352 | col_h9_r1__t1 | 5_2_route | 4.7 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-4140136 | col_h9_r1__t1 | 5_2_route | 4.7 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hgi-769960 | kv3_hgi | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.1 h ago (476/476 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hgi_v7-3713215 | kv3_hgi_v7 | 3_3_place_gp | 1.0 | overflow best 0.3302 last 0.3331 rows 21 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-kv3_hgi_v8-3715561 | kv3_hgi_v8 | 3_3_place_gp | 1.0 | overflow best 0.297 last 0.297 rows 9 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-kv3_pv-807714 | kv3_pv | postplace_setup | 0.2 | last meaningful line 0.1 h ago (15/15 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v1-3737021 | kv3_pv_v1 | 2_4_floorplan_pdn | 1.0 | last meaningful line 0.3 h ago (92/92 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v2-3742293 | kv3_pv_v2 | 2_4_floorplan_pdn | 1.0 | last meaningful line 0.2 h ago (91/91 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v2n-3736265 | kv3_pv_v2n | 2_4_floorplan_pdn | 1.0 | last meaningful line 0.2 h ago (110/110 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v3-3744611 | kv3_pv_v3 | 2_4_floorplan_pdn | 1.0 | last meaningful line 0.2 h ago (88/88 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v3n-3743971 | kv3_pv_v3n | 2_1_floorplan | 1.0 | last meaningful line 0.5 h ago (1262/1262 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v4-3749853 | kv3_pv_v4 | 2_4_floorplan_pdn | 1.0 | last meaningful line 0.1 h ago (91/91 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v4n-3749196 | kv3_pv_v4n | 2_4_floorplan_pdn | 1.0 | last meaningful line 0.0 h ago (90/90 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v5-3751877 | kv3_pv_v5 | 2_1_floorplan | 1.0 | last meaningful line 0.5 h ago (1416/1416 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v5n-3751077 | kv3_pv_v5n | 2_1_floorplan | 1.0 | last meaningful line 0.5 h ago (1418/1418 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v7-3753752 | kv3_pv_v7 | 2_1_floorplan | 1.0 | last meaningful line 0.5 h ago (1298/1298 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t28-716455 | ot_s81sl_leaf__t28 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9344 last 0.9365 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-phy__t1-684629 | phy__t1 | 3_3_place_gp | 0.2 | overflow best 0.3412 last 0.3412 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-serdes__t15__cla2127225-214628 | serdes__t15 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.1 h ago (92/92 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-3990175 | serdes__t1 | 3_1_place_gp_skip_io | 0.9 | overflow best 0.9228 last 0.9228 rows 5 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-serdes__t2-3210518 | serdes__t2 | 3_4_place_resized | 1.4 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v3-383732 | sle_sc_v3 | 3_3_place_gp | 0.5 | overflow best 0.4152 last 0.4152 rows 17 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-slice_station__t27-4170423 | slice_station__t27 | 5_2_route | 4.7 | drt_violations best 21502 last 21502 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t49-4183263 | slice_station__t49 | 5_2_route | 4.7 | drt_violations best 19055 last 19055 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-4021993 | slw_fe_v1 | 3_3_place_gp | 0.9 | overflow best 0.0991 last 0.0991 rows 42 | YOUNG: stage 0.7 h < 1 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-314683 | slw_hc3 | 3_3_place_gp | 0.5 | overflow best 0.206 last 0.206 rows 47 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-slw_st_a_v1__clb036e152-280086 | slw_st_a_v1 | postplace_setup | 0.5 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-281218 | slw_st_a_v1 | postplace_setup | 0.5 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cle6023ec2-3925892 | slw_st_b_v1 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (79/79 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 44.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-4136921-3314 | 4136921 | - | 4.7 |  | NO-DATA: no log found |  |
| epyc8 | otc-4136953-11523 | 4136953 | - | 4.7 |  | NO-DATA: no log found |  |
| epyc8 | otc-4137215-10978 | 4137215 | - | 4.7 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | 5_2_route | 16.1 | drt_violations best 219997 last 219997 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3331047 | col_h10_r2__t1 | 5_2_route | 6.1 | drt_violations best 73438 last 73438 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv697f40c9-2412903 | col_h9_r0_p1__t1 | 3_4_place_resized | 1.3 | last meaningful line 0.0 h ago (222/222 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-coll_core-2715822 | coll_core | 3_3_place_gp | 1.1 | overflow best 0.1134 last 0.1134 rows 43 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-2939391 | dsdv_slice_c1x_C__t9 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-3000844 | dsdv_slice_c3x_C__t1 | sdc_lint | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_C__t1-2944273 | dsdv_slice_lepe_mu_C__t1 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-2673936 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 3.7 | repair_TNS best 587996 last 587996 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-744074 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 2.3 | repair_TNS best 768551 last 768551 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2950877 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-1952006 | hd_ctl | 5_2_route | 9.7 | drt_violations best 50637 last 50637 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-hd_mesh-3444928 | hd_mesh | pregrt_ff_hold | 6.1 | repair_TNS best 554575 last 554575 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_serdes-3042541 | hd_serdes | 3_1_place_gp_skip_io | 0.9 | overflow best 0.9799 last 0.991 rows 17 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-kv3_hgi_v3-2824977 | kv3_hgi_v3 | 3_3_place_gp | 1.0 | overflow best 0.0976 last 0.0976 rows 54 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-kv3_hgi_v5-2829058 | kv3_hgi_v5 | 3_3_place_gp | 1.0 | overflow best 0.1444 last 0.1444 rows 51 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-kv3_hgi_v6-2832834 | kv3_hgi_v6 | 3_3_place_gp | 1.0 | overflow best 0.3464 last 0.3464 rows 33 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-kv3_hub_Eo-3105101 | kv3_hub_Eo | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (6299/6299 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hub_Wo-2840584 | kv3_hub_Wo | 3_1_place_gp_skip_io | 1.0 | overflow best 0.97 last 0.97 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v12-2850495 | kv3_pv_v12 | 2_1_floorplan | 1.0 | last meaningful line 0.8 h ago (144/144 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v1n-2894902 | kv3_pv_v1n | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (7926/7926 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-1366470 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 7.7 | repair_Remaining best 130290 last 130290 rows 219 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t31-2959974 | ot_s81sl_leaf__t31 | 3_3_place_gp | 0.9 | overflow best 0.4818 last 0.4818 rows 29 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-4078805 | ot_s81sl_leaf__t39 | 5_1_grt | 8.8 | repair_Viol best 78 last 78 rows 42 | YOUNG: evidence 3.1 h < 6 h |  |
| epyc9 | dpkit-serdes__t14-2543182 | serdes__t14 | 3_3_place_gp | 1.2 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t15__cla3d02796-2601962 | serdes__t15 | 3_1_place_gp_skip_io | 1.1 | overflow best 0.9096 last 0.9132 rows 10 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-2886708 | sle_ctl | 3_1_place_gp_skip_io | 1.0 | overflow best 0.5155 last 0.5155 rows 30 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2433248 | sle_hc0 | 3_4_place_resized | 1.2 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2867389 | sle_hc1 | 3_3_place_gp | 1.0 | overflow best 0.3035 last 0.5788 rows 73 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-2237995 | sle_hc1 | 3_3_place_gp | 1.3 | overflow best 0.3004 last 0.4209 rows 88 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_sc_v2-2664497 | sle_sc_v2 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_su_c-2738922 | sle_su_c | 3_1_place_gp_skip_io | 1.1 | overflow best 0.1593 last 0.1726 rows 47 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-3958490 | sle_su_l1 | 3_3_place_gp | 0.4 | overflow best 0.2056 last 0.2056 rows 41 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-slice_station__t37-4074295 | slice_station__t37 | 5_2_route | 8.8 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-2126924 | slice_station__t52 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (3417/3417 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-3091447 | slw_fe_v1 | 3_3_place_gp | 0.9 | overflow best 0.2058 last 0.2058 rows 35 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-80410 | slw_fe_v1 | 5_2_route | 8.7 | last meaningful line 0.2 h ago (265/266 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-2003480 | slw_fe_v2 | postcts_gate_TT | 9.6 | last meaningful line 0.1 h ago (1659/1659 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2349988 | slw_fw_v1 | 3_4_place_resized | 1.3 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3221813 | slw_hc3 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_su_c__cl19bb38ef-2932395 | slw_su_c | 3_3_place_gp | 1.0 | overflow best 0.2035 last 0.2035 rows 41 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs__t2-3396484 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 3.2 | last meaningful line 0.0 h ago (522/522 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs_w__t1-4075465 | svc_lo_dsdv_svc_rs_w__t1 | 3_3_place_gp | 10.5 | overflow best 0.6442 last 0.6442 rows 47 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | kv102-face-qkd_hr_core_peer-1116 | kv102-face-qkd_hr_core_peer | s81-die-r3-c-rsync | 109.4 |  | NO-DATA: empty log |  |
| epyc9 | otc-3085280-30126 | 3085280 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc9 | otc-4082288-6387 | 4082288 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261120_185716_1464729-i1-1722084 | eco_20261120_185716_1464729-i1 | 5_2_route | 4.3 | drt_violations best 5965 last 5965 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i1t-803747 | eco_20261121_070035_1645318-i1t | 5_1_grt | 2.2 | repair_Viol best 1541 last 1541 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | ap-ageom-kw-dsdv-slice-c1x-C--t3-grt-4078591 | dsdv-slice-c1x-C--t3-grt | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3216520 | col_h10_r0_p1__t1 | 5_1_grt | 5.3 | last meaningful line 0.0 h ago (187/187 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3218543 | col_h10_r0_p4__t1 | postcts_gate_FF | 5.3 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-3219217 | col_h10_r1__t1 | 5_2_route | 5.3 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3220432 | col_h10_r1__t1 | 5_1_grt | 5.3 | last meaningful line 1.0 h ago (201/217 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-1995133 | col_h10_r1__t1 | 5_2_route | 6.0 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3793362 | col_h10_r2__t1 | 5_2_route | 5.1 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 5_1_grt | 5.3 | last meaningful line 0.1 h ago (194/207 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-3224057 | col_h9_r0_p1__t1 | pregrt_ff_hold | 5.3 | repair_TNS best 213044 last 213044 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3779183 | col_h9_r0_p2__t1 | 5_1_grt | 5.1 | last meaningful line 1.0 h ago (209/218 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | 5_1_grt | 5.1 | last meaningful line 0.1 h ago (158/158 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-3785724 | col_h9_r0_p3__t1 | 5_1_grt | 5.1 | last meaningful line 0.0 h ago (189/189 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-3790077 | col_h9_r0_p3__t1 | 5_1_grt | 5.1 | last meaningful line 0.3 h ago (209/212 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3005235 | dsdv_slice_c1x_C__t5 | 3_4_place_resized | 5.5 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-297032 | dsdv_slice_c1x_C__t6 | 1_1_yosys_canonicalize | 2.2 | last meaningful line 0.2 h ago (132/132 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t22-2407667 | slice_station__t22 | 5_2_route | 5.8 | last meaningful line 0.2 h ago (254/255 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_pvso_entry__t1-18505 | svc_hi_dsdv_svc_pvso_entry__t1 | 2_4_floorplan_pdn | 7.1 | last meaningful line 0.0 h ago (310/310 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t2-996017 | svc_hi_dsdv_svc_rs__t2 | 3_3_place_gp | 6.6 | last meaningful line 0.0 h ago (108/108 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t3-432817 | svc_hi_dsdv_svc_rs__t3 | 3_3_place_gp | 6.9 | last meaningful line 0.0 h ago (90/90 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t4-4054912 | svc_hi_dsdv_svc_rs__t4 | 3_3_place_gp | 7.2 | overflow best 0.9326 last 0.9326 rows 27 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t6-1410020 | svc_hi_dsdv_svc_rs__t6 | 3_1_place_gp_skip_io | 10.3 | overflow best 0.2108 last 0.348 rows 320 | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t4-1991847 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 6.0 | last meaningful line 1.1 h ago (674/674 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t5-28461 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 2.4 | last meaningful line 0.3 h ago (463/463 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t7-1446461 | svc_lo_dsdv_svc_rs__t7 | 2_1_floorplan | 10.2 | last meaningful line 0.0 h ago (96/96 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | fv0030-s81_c1x_C_t3-4077166 | fv0030-s81_c1x_C_t3 | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261120_192428_3309571-i1t-2831293 | eco_20261120_192428_3309571-i1t | 5_2_route | 5.5 | drt_violations best 1449 last 1449 rows 7 | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel1 | prd-eco_20261120_211023_313122-i1t-1859870 | eco_20261120_211023_313122-i1t | 5_2_route | 3.8 | drt_violations best 3038 last 3038 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-171983 | sle_sc_v1 | postcts_gate_FF | 8.9 | last meaningful line 0.2 h ago (2164/2164 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-169076 | sle_sc_v1 | 5_2_route | 8.9 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | 5_1_grt | 8.8 | last meaningful line 0.5 h ago (217/1023 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | 5_1_grt | 8.9 | last meaningful line 0.2 h ago (140/140 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t27-184972 | slice_station__t27 | 5_2_route | 8.9 | drt_violations best 21814 last 21814 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t41-218779 | slice_station__t41 | 5_2_route | 8.8 | last meaningful line 0.5 h ago (268/269 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t43-189037 | slice_station__t43 | 5_2_route | 8.9 | last meaningful line 0.2 h ago (262/263 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t49-221823 | slice_station__t49 | 5_2_route | 8.8 | drt_violations best 18972 last 18972 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t51-283223 | slice_station__t51 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | 5_1_grt | 8.9 | last meaningful line 4.6 h ago (219/1470 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-195191 | slw_sc_v1 | 5_2_route | 8.8 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v2-195133 | slw_sc_v2 | 5_2_route | 8.8 | last meaningful line 0.2 h ago (267/267 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | 5_1_grt | 8.8 | last meaningful line 0.3 h ago (217/1014 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-320845 | svc_hi_dsdv_svc_rs__t1 | 3_1_place_gp_skip_io | 8.8 | overflow best 0.2105 last 0.2743 rows 248 | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel2 | prd-eco_20261120_155439_476619-i1-1392033 | eco_20261120_155439_476619-i1 | 5_1_grt | 1.5 | last meaningful line 0.7 h ago (235/1387 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162132_484876-i1-1499386 | eco_20261120_162132_484876-i1 | 5_1_grt | 1.4 | last meaningful line 0.7 h ago (234/1302 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162140_2433056-i1-3186007 | eco_20261120_162140_2433056-i1 | 5_2_route | 3.6 | drt_violations best 1 last 1 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel2 | prd-eco_20261120_182729_483429-i1t-3309803 | eco_20261120_182729_483429-i1t | 5_2_route | 6.7 | drt_violations best 6951 last 6951 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel2 | prd-fin-2273142 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 25.4 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-297976 | sle_ctl | 2_1_floorplan | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 18.1 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-eco1-i1t-1664760 | eco1-i1t | 5_1_grt | 1.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1671443 | eco1-i1t | 5_1_grt | 1.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1673812 | eco1-i1t | 5_1_grt | 1.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3393842 | col_h9_r0_p3__t1 | 5_1_grt | 5.1 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-4047305 | sle_fw_v2 | 5_1_grt | 7.3 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 12.0 | drt_violations best 87 last 426 rows 42 | before-window best 1065, window best 87 | PROGRESS: drt_violations improved 91.8 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 22.5 | last meaningful line 0.6 h ago (1434/1434 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 14.1 | last meaningful line 1.3 h ago (1166/1166 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-299390 | cbn_q01 | pregrt_ff_hold | 4.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-cbx_q10__cl94a12200_h-1923109 | cbx_q10 | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-kv3_pv_v8-561953 | kv3_pv_v8 | 4_1_cts | 10.9 | last meaningful line 0.8 h ago (15751/15751 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-native59-304297 | native59 | pregrt_ff_hold | 4.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | tg2130-v8c_conv-3155764 | tg2130-v8c_conv | tg_cts | 2.9 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-4168631 | col_h9_r0_p2__t1 | 5_2_route | 14.4 | drt_violations best 23 last 23 rows 17 | before-window best 134377, window best 23 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-glue-3352856 | glue | pregrt_ff_hold | 7.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t2-1333460 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 10.3 | last meaningful line 0.1 h ago (814/814 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
