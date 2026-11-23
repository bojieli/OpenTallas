# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 21:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'UNSIGNABLE': 1, 'GRT-LABEL': 44, 'YOUNG': 184, 'NO-DATA': 8, 'EXCLUDED': 1, 'PROGRESS': 30}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 13.4 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 13.4 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc10 | dpkit-ot_s81sl_leaf__t67-1482469 | ot_s81sl_leaf__t67 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -793.08 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 30.0 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc10 | dpkit-bk_sel__t2-2991761 | bk_sel__t2 | 5_1_grt | 5.1 | grt rounds 2 overflow 5:14401 -> 10:1199 | GRT-LABEL: DESIGN-FAIL: overflow 1199 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t15-1140501 | ot_s81sl_leaf__t15 | 5_1_grt | 3.5 | grt rounds 3 overflow 5:31474 -> 10:17162 -> 15:6617 | GRT-LABEL: DESIGN-FAIL: overflow 17162 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t21-1070163 | ot_s81sl_leaf__t21 | 5_1_grt | 3.5 | grt rounds 3 overflow 5:64990 -> 10:59539 -> 15:58701 | GRT-LABEL: DESIGN-FAIL: overflow 59539 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t27-1512680 | ot_s81sl_leaf__t27 | 5_1_grt | 3.3 | grt rounds 2 overflow 5:28580 -> 10:8107 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 59.7 | grt rounds 4 overflow 5:102138 -> 10:62187 -> 15:49076 -> 20:50054 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 74.1 | grt rounds 6 overflow 5:8939 -> 10:4958 -> 15:3337 -> 20:2951 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-1903434 | col_h9_r2__t1 | 5_1_grt | 2.8 | grt rounds 2 overflow 5:3567 -> 10:316 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_1_grt | 2.8 | grt rounds 2 overflow 5:18611 -> 10:8682 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-2032513 | ot_s81sl_leaf__t30 | 5_1_grt | 5.1 | grt rounds 4 overflow 5:32003 -> 10:27757 -> 15:23027 -> 20:21566 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t35-2852968 | ot_s81sl_leaf__t35 | 5_1_grt | 16.2 | grt rounds 4 overflow 5:7049 -> 10:4695 -> 15:3416 -> 20:3335 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-2882107 | ot_s81sl_leaf__t46 | 5_1_grt | 16.2 | grt rounds 3 overflow 5:24185 -> 10:16775 -> 15:14263 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t60-696062 | ot_s81sl_leaf__t60 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:36651 -> 10:36233 -> 15:29664 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-3655640 | ot_s81sl_leaf__t65 | 5_1_grt | 6.3 | grt rounds 3 overflow 5:40772 -> 10:33554 -> 15:29110 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_1_grt | 1.6 | grt rounds 2 overflow 5:3095 -> 10:2559 | GRT-LABEL: DESIGN-FAIL: overflow 2559 at round 10 > 1000 |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_1_grt | 2.0 | grt rounds 2 overflow 5:4299 -> 10:3706 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984485 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 14.3 | grt rounds 2 overflow 5:149 -> 10:62 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 53.2 | grt rounds 3 overflow 5:76937 -> 10:70297 -> 15:59251 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 58.2 | grt rounds 3 overflow 5:61116 -> 10:63134 -> 15:53833 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 47.6 | grt rounds 4 overflow 5:58312 -> 10:48779 -> 15:39348 -> 20:42347 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 47.6 | grt rounds 4 overflow 5:60910 -> 10:48673 -> 15:39385 -> 20:42269 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t1-4049223 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 6.2 | grt rounds 2 overflow 5:1776 -> 10:344 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t21-1786623 | ot_s81sl_leaf__t21 | 5_1_grt | 2.6 | grt rounds 2 overflow 5:59171 -> 10:48750 | GRT-LABEL: DESIGN-FAIL: overflow 48750 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 57.3 | grt rounds 4 overflow 5:77624 -> 10:49527 -> 15:42727 -> 20:44053 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 47.1 | grt rounds 4 overflow 5:113020 -> 10:70115 -> 15:50222 -> 20:58309 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 21.9 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-1983201 | sle_st_a_v2 | 5_1_grt | 2.5 | grt rounds 2 overflow 5:8952 -> 10:4401 | GRT-LABEL: DESIGN-FAIL: overflow 4401 at round 10 > 1000 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_1_grt | 2.7 | grt rounds 2 overflow 5:3279 -> 10:2978 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-2217964 | col_h9_r2__t1 | 5_1_grt | 2.8 | grt rounds 2 overflow 5:2844 -> 10:292 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t36-2215632 | ot_s81sl_leaf__t36 | 5_1_grt | 2.8 | grt rounds 2 overflow 5:8739 -> 10:2535 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv40e9fb5a-287653 | col_h9_r2__t1 | 5_1_grt | 2.8 | grt rounds 2 overflow 5:5132 -> 10:428 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-426492 | ot_s81sl_leaf__t39 | 5_1_grt | 2.8 | grt rounds 2 overflow 5:50229 -> 10:41154 | GRT-LABEL: DESIGN-FAIL: overflow 41154 at round 10 > 1000 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t42-283577 | ot_s81sl_leaf__t42 | 5_1_grt | 2.9 | grt rounds 2 overflow 5:44899 -> 10:41746 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-306943 | ot_s81sl_leaf__t44 | 5_1_grt | 2.8 | grt rounds 2 overflow 5:69626 -> 10:62831 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 16.1 | grt rounds 6 overflow 5:1893 -> 10:1268 -> 15:872 -> 20:551 -> 25:191 -> 30:43 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t74-577800 | ot_s81sl_leaf__t74 | 5_1_grt | 7.1 | grt rounds 3 overflow 5:36002 -> 10:35339 -> 15:33217 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-937455 | col_h9_r0_p4__t1 | 5_1_grt | 16.2 | grt rounds 6 overflow 5:47882 -> 10:2931 -> 15:1264 -> 20:847 -> 25:413 -> 30:140 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-coll_core-180674 | coll_core | 5_1_grt | 14.5 | grt rounds 2 overflow 5:14446 -> 10:2584 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 16.2 | grt rounds 3 overflow 5:40 -> 10:24 -> 15:5 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 16.2 | grt rounds 6 overflow 5:2533 -> 10:1498 -> 15:842 -> 20:584 -> 25:584 -> 30:139 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 16.2 | grt rounds 3 overflow 5:23666 -> 10:2822 -> 15:2123 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_1_grt | 2.9 | grt rounds 2 overflow 5:5303 -> 10:4175 | GRT-LABEL: DESIGN-FAIL: overflow 4175 at round 10 > 1000 |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | 5_1_grt | 8.2 | grt rounds 2 overflow 5:60853 -> 10:337 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 12.4 | grt rounds 2 overflow 5:88896 -> 10:83085 | GRT-LABEL: DESIGN-FAIL: overflow 83085 at round 10 > 1000 |  |
| intel2 | dpkit-ot_s81sl_leaf__t11-599830 | ot_s81sl_leaf__t11 | 5_1_grt | 8.1 | grt rounds 2 overflow 5:20442 -> 10:19023 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2379537 | col_h10_r0_p4__t1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3348/3348 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-2396922 | col_h10_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.3429 last 0.3432 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2844492 | col_h10_r1__t1 | pregrt_ff_hold | 2.7 | repair_TNS best 1071.3 last 1071.3 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-2664155 | col_h9_r0_p5__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2816/2816 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-1299090 | coll_core | 3_4_place_resized | 1.0 | repair_Remaining best 165988 last 165988 rows 160 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t3-886705 | dsdv_slice_c1x_C__t3 | 3_5_place_dp | 3.7 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t7-880876 | dsdv_slice_c1x_C__t7 | 3_5_place_dp | 3.7 | last meaningful line 0.0 h ago (119/119 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_kv512_C__t1-3997844 | dsdv_slice_kv512_C__t1 | 3_4_place_resized | 2.0 | repair_Remaining best 325178 last 325178 rows 46 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-iqf__t1-13421 | iqf__t1 | 5_2_route | 4.2 | drt_violations best 27295 last 27295 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v3-2699466 | kv3_hgi_v3 | 2_1_floorplan | 0.1 | repair_Viol best 2147 last 2147 rows 716 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c-2604770 | kv3_pc_v1 | 2_1_floorplan | 0.2 | repair_Viol best 8514 last 8514 rows 125 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl7f648944-1941007 | kv3_pc_v1 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.0 h ago (58/58 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-2446788 | kv3_pv_v3 | synth_odb_v | 0.2 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_sys_c-1070279 | kv3_sys_c | 5_1_grt | 3.5 | last meaningful line 0.1 h ago (2934/2954 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-native59-2585588 | native59 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5055/5055 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t23-2663094 | ot_s81sl_leaf__t23 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t28-1070507 | ot_s81sl_leaf__t28 | 5_1_grt | 3.5 | last meaningful line 0.1 h ago (157/157 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t29-2063028 | ot_s81sl_leaf__t29 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3466/3466 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t46-2731436 | ot_s81sl_leaf__t46 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t61-2696700 | ot_s81sl_leaf__t61 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (57/57 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t67-3226431 | ot_s81sl_leaf__t67 | 5_1_grt | 2.5 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-1401150 | sle_ctl | 3_1_place_gp_skip_io | 0.9 | overflow best 0.1807 last 0.1807 rows 39 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2569171 | sle_hc1 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-1351532 | sle_hc2 | 4_1_cts | 1.0 | last meaningful line 0.2 h ago (5425/5425 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-1325606 | sle_stm_v1 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (5948/5948 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v2__cl7b3062fa-3029892 | sle_stm_v2 | 5_1_grt | 5.1 | last meaningful line 0.1 h ago (2023/2040 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t25-3118247 | slice_station__t25 | 5_2_route | 5.0 | drt_violations best 57515 last 57515 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2619979 | slw_fe_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5449/5449 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-2598673-6856 | 2598673 | - | 2.8 |  | NO-DATA: no log found |  |
| epyc10 | otc-2600316-20386 | 2600316 | - | 2.8 |  | NO-DATA: no log found |  |
| epyc10 | otc-2647602-21117 | 2647602 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i1-42727 | eco_20261122_223531_3628570-i1 | 5_2_route | 1.9 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_040953_1214866-i1-1617727 | eco_20261123_040953_1214866-i1 | 5_1_grt | 0.8 | last meaningful line 0.2 h ago (235/837 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-1820678 | col_h10_r0_p1__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 103959 last 103959 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-2022266 | col_h10_r0_p1__t1 | 5_1_grt | 5.1 | last meaningful line 0.3 h ago (211/215 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-1815940 | col_h10_r0_p1__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 110284 last 110284 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2108278 | dsdv_slice_c1x_C__t1 | 5_1_grt | 5.0 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2115818 | dsdv_slice_c1x_C__t10 | 5_1_grt | 5.0 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t4-1830876 | dsdv_slice_c1x_C__t4 | 3_3_place_gp | 2.8 | last meaningful line -0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t8-1830466 | dsdv_slice_c1x_C__t8 | 3_1_place_gp_skip_io | 2.8 | overflow best 0.28 last 0.28 rows 39 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_mu_C__t1-3116985 | dsdv_slice_lepe_mu_C__t1 | 4_1_cts | 2.1 | last meaningful line 0.0 h ago (47/47 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1835310 | dsdv_slice_lepe_nh_mus_C__t1 | 3_1_place_gp_skip_io | 2.8 | overflow best 0.2528 last 0.2528 rows 40 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | 3_3_place_gp | 2.8 | overflow best 0.649 last 0.649 rows 25 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | selrange | 1.7 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-gunit__t1-3244008 | gunit__t1 | 3_5_place_dp | 2.0 | last meaningful line 1.5 h ago (39/39 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-hd_lep0N_w-3963146 | hd_lep0N_w | 4_2_tapbal_grt | 1.6 | last meaningful line 1.0 h ago (46/122 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t17-1828917 | ot_s81sl_leaf__t17 | 5_1_grt | 2.8 | last meaningful line 0.0 h ago (203/206 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t25__cl55642d17-3247888 | ot_s81sl_leaf__t25 | 5_1_grt | 2.0 | last meaningful line 0.3 h ago (200/206 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t41-1816190 | ot_s81sl_leaf__t41 | 5_1_grt | 2.8 | last meaningful line 0.3 h ago (203/209 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t43-562324 | ot_s81sl_leaf__t43 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (4006/4006 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t47-1932405 | ot_s81sl_leaf__t47 | 5_1_grt | 2.8 | last meaningful line 0.3 h ago (213/217 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t62-1866677 | ot_s81sl_leaf__t62 | 5_1_grt | 2.8 | last meaningful line 0.0 h ago (153/153 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t66-552390 | ot_s81sl_leaf__t66 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (4260/4260 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-217266 | sle_ctl | 3_3_place_gp | 1.3 | overflow best 0.466 last 0.466 rows 21 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | 5_1_grt | 5.1 | last meaningful line 0.1 h ago (189/189 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t29__clc7772371-2336581 | slice_station__t29 | 5_2_route | 2.6 | last meaningful line 0.2 h ago (244/245 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | 4_1_cts | 2.8 | last meaningful line 0.2 h ago (5560/5560 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | 4_1_cts | 2.6 | last meaningful line 0.4 h ago (5588/5588 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 5.0 | drt_violations best 154966 last 154966 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | otc-1481339-18431 | 1481339 | signoff | 5.3 | last meaningful line 5.3 h ago (3/3 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | otc-2114902-19881 | 2114902 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261122_164248_3895049-i1t-3385034 | eco_20261122_164248_3895049-i1t | 5_2_route | 4.3 | drt_violations best 16734 last 16734 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164521_3948325-i1t-3466592 | eco_20261122_164521_3948325-i1t | 5_2_route | 4.2 | drt_violations best 6008 last 6008 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_180145_3931237-i1-1443078 | eco_20261122_180145_3931237-i1 | 5_2_route | 2.9 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i1t-1909174 | eco_20261122_181101_3945375-i1t | 5_2_route | 2.8 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i1t-3508652 | eco_20261122_190506_3875261-i1t | 5_2_route | 1.9 | last meaningful line 0.3 h ago (134/134 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-3759481 | col_h9_r2__t1 | 5_2_route | 6.4 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-8352 | dsdv_slice_lepe_nh_mus_C__t1 | 3_4_place_resized | 3.6 | repair_Remaining best 150999 last 150999 rows 217 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t3-56823 | ot_s81sl_leaf__t3 | 5_1_grt | 3.6 | last meaningful line 0.5 h ago (209/215 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1181364 | ot_s81sl_leaf__t39 | 5_1_grt | 2.9 | last meaningful line 0.5 h ago (262/1276 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 5_2_route | 16.1 | drt_violations best 107202 last 107202 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | 5_1_grt | 6.8 | repair_Remaining best 181652 last 181652 rows 261 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-1530301 | sle_hc0 | postcts_gate_FF | 2.7 | last meaningful line -0.0 h ago (95879/95879 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | 5_1_grt | 7.7 | last meaningful line 0.1 h ago (1103/1120 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-881903 | sle_stm_v1 | 5_2_route | 7.8 | last meaningful line 0.3 h ago (277/278 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t18-1919126 | slice_station__t18 | 5_2_route | 2.6 | last meaningful line 0.2 h ago (254/255 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t40__cl1ea9de02-1928775 | slice_station__t40 | 5_2_route | 2.6 | last meaningful line 0.1 h ago (252/252 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t45-1870760 | slice_station__t45 | 5_2_route | 2.6 | drt_violations best 17359 last 17359 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t6__cl54a9ceeb-1772119 | slice_station__t6 | 5_2_route | 2.6 | last meaningful line 0.2 h ago (246/247 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_1_grt | 7.7 | last meaningful line 0.1 h ago (1994/2000 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl9beb65e6-3994155 | slw_stm_v2 | 5_1_grt | 6.3 | last meaningful line 0.1 h ago (1022/1039 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | eco-abs-951556 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.1 h ago (369/369 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | otc-1216938-8417 | 1216938 | qwen_compute.t.slw_hc3__clccfc3e6b | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-1220869-27656 | 1220869 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_2_route | 12.9 | drt_violations best 2121 last 2121 rows 5 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-4104970 | col_h10_r2__t1 | 5_1_grt | 1.8 | last meaningful line 0.0 h ago (201/207 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2000675 | col_h9_r0_p2__t1 | 5_1_grt | 2.9 | last meaningful line 0.1 h ago (210/213 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 13.4 | drt_violations best 34114 last 34114 rows 2 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-3175015 | col_h9_r0_p4__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (313/313 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2088472 | dsdv_slice_lepe_nh_mus_C__t1 | 4_1_cts | 2.8 | last meaningful line 0.0 h ago (5908/5908 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepw_mu_LP__t2-2830715 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 4.3 | repair_Violations best 1601 last 1601 rows 11 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hgi_v2__cle0015330-2999779 | kv3_hgi_v2 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9964 last 0.9964 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-kv3_hgi_v2__cle0015330-3420881 | kv3_hgi_v2 | 2_1_floorplan | 0.1 | repair_Viol best 1094 last 1094 rows 521 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-kv3_hgi_v3-3501492 | kv3_hgi_v3 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hgi_v5-2146105 | kv3_hgi_v5 | 3_3_place_gp | 0.6 | overflow best 0.2215 last 0.2215 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 4.3 | drt_violations best 132034 last 132034 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (39/39 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-494270 | kv3_hub_Ei | 5_1_grt | 5.3 | last meaningful line 0.5 h ago (2123/2129 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-2778952 | kv3_io_cor_v1 | 5_2_route | 4.3 | drt_violations best 53338 last 53338 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6n-4024718 | kv3_pv_v6n | 3_4_place_resized | 1.9 | last meaningful line 0.0 h ago (435/435 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t52-2261818 | ot_s81sl_leaf__t52 | 5_1_grt | 2.8 | last meaningful line 1.0 h ago (204/210 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t54__cl501e5681-2532249 | ot_s81sl_leaf__t54 | pregrt_ff_hold | 0.4 | repair_TNS best 7823.76 last 7823.76 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t58-3445802 | ot_s81sl_leaf__t58 | 5_1_grt | 2.2 | last meaningful line 0.3 h ago (210/213 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t73-2566685 | ot_s81sl_leaf__t73 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3859/3859 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-3100063 | serdes__t1 | 1_2_yosys | 0.2 | last meaningful line 0.1 h ago (316/316 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-1804559 | slw_st_a_v2 | hold_gate | 0.8 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-3353467 | slw_st_a_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (8607/8607 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | kvcore-qkd_ectlk_q0__216x172.8_-159237-lec | kvcore-qkd_ectlk_q0__216x172.8_ | lec | 1.7 | LEC last write 0.1 h ago | YOUNG: evidence 1.7 h < 6 h |  |
| epyc8 | kvcore-qkd_ectlk_q0__216x172.8_-3106818-lec | kvcore-qkd_ectlk_q0__216x172.8_ | lec | 2.3 | LEC last write 0.1 h ago | YOUNG: evidence 2.3 h < 6 h |  |
| epyc8 | kvcore-qkd_ectlk_q2__243.648x172.8_-157778 | kvcore-qkd_ectlk_q2__243.648x172.8_ | 5_1_grt | 1.7 | last meaningful line 1.4 h ago (206/1490 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | so_3300246_ff_12098 | so_3300246_ff_12098 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | so_3300246_tt_12098 | so_3300246_tt_12098 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-4076788 | col_h10_r1__t1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_2_route | 16.4 | drt_violations best 32279 last 32279 rows 2 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | pregrt_ff_hold | 0.9 | repair_TNS best 96178 last 96178 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-238701 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.9 | repair_TNS best 109251 last 109251 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t6-401942 | dsdv_slice_c1x_C__t6 | 2_4_floorplan_pdn | 2.8 | last meaningful line 0.0 h ago (71/71 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-405849 | dsdv_slice_c1x_C__t8 | 2_1_floorplan | 2.8 | last meaningful line 0.0 h ago (90/90 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | tt_setup_repair | 2.8 | repair_Violations best 4753 last 4753 rows 40 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_kv512_C__t1-288662 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 2.8 | last meaningful line 0.3 h ago (37/37 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mus_C__t1-426957 | dsdv_slice_lepw_mus_C__t1 | 3_1_place_gp_skip_io | 2.8 | overflow best 0.9953 last 0.9953 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-kv3_hgi_v4-3402463 | kv3_hgi_v4 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.5771 last 0.5771 rows 27 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-kv3_hroot-3814545 | kv3_hroot | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.1 h ago (22/22 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-3044355 | kv3_pc_v3 | 3_1_place_gp_skip_io | 0.7 | overflow best 0.8086 last 0.8086 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-kv3_pc_v3-3112935 | kv3_pc_v3 | 3_1_place_gp_skip_io | 0.7 | overflow best 0.8991 last 0.8991 rows 4 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v8-3739898 | kv3_pv_v8 | 2_1_floorplan | 0.3 | repair_Viol best 258 last 258 rows 212 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-kv3_sys_c-2832325 | kv3_sys_c | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (258/258 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (2839/2839 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-457556 | ot_s81sl_leaf__t22 | 5_1_grt | 2.8 | last meaningful line 0.8 h ago (203/210 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2878610 | ot_s81sl_leaf__t44 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t45-3067284 | ot_s81sl_leaf__t45 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t56-2935638 | ot_s81sl_leaf__t56 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t7-2999385 | ot_s81sl_leaf__t7 | 3_3_place_gp | 0.8 | overflow best 0.3127 last 0.3127 rows 37 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-sle_fw_v2__cl69f5e854-2970240 | sle_fw_v2 | 4_1_cts | 0.8 | last meaningful line 0.2 h ago (5165/5165 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | 4_1_cts | 0.8 | last meaningful line 0.2 h ago (5849/5849 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t22-239981 | slice_station__t22 | 5_2_route | 2.9 | last meaningful line 0.0 h ago (245/245 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-570014 | slice_station__t51 | 5_2_route | 7.1 | drt_violations best 48586 last 48586 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-567108 | slice_station__t52 | 5_3_fillcell | 7.1 | last meaningful line -0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | postplace_setup | 0.0 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-3009482 | slw_fe_v2 | 4_1_cts | 0.8 | last meaningful line 0.2 h ago (4342/4342 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v3-3096266 | slw_fw_v3 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (4833/4833 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (5306/5306 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_a_v1__clb036e152-429176 | slw_st_a_v1 | postcts_gate_FF | 2.8 | last meaningful line 0.1 h ago (57/57 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-3335036-14223 | 3335036 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc9 | otc-682537-13250 | 682537 | - | 2.7 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i1t-3504713 | eco-i1t | 5_2_route | 3.3 | drt_violations best 3383 last 3383 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | prd-eco-i3-2776988 | eco-i3 | 5_2_route | 3.7 | drt_violations best 84109 last 84109 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i2t-3854167 | eco_20261122_180231_342380-i2t | 5_2_route | 3.1 | drt_violations best 1999 last 1999 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_214447_3988541-i1-1254579 | eco_20261122_214447_3988541-i1 | 5_2_route | 2.3 | last meaningful line 0.0 h ago (267/267 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_2_route | 16.2 | drt_violations best 195281 last 195281 rows 1 | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3365642 | col_h10_r1__t1 | pregrt_ff_hold | 2.9 | repair_TNS best 108409 last 108409 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-3367083 | col_h10_r2__t1 | 5_1_grt | 2.9 | last meaningful line 0.1 h ago (147/147 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3534091 | col_h10_r2__t1 | 5_1_grt | 2.8 | last meaningful line 0.1 h ago (188/201 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__clac068e56-3522831 | col_h10_r2__t1 | 5_1_grt | 2.8 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 16.2 | drt_violations best 210671 last 210671 rows 1 | YOUNG: evidence 6.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-3535177 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 74162.8 last 74162.8 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvc1b82625-3531236 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 170706 last 170706 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-3367117 | col_h9_r1__t1 | 5_1_grt | 2.9 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3522355 | col_h9_r2__t1 | 5_1_grt | 2.8 | last meaningful line 0.0 h ago (183/183 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvcf44b14c-1664216 | col_h9_r2__t1 | 5_2_route | 6.2 | last meaningful line 0.2 h ago (263/264 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-3365034 | dsdv_slice_c1x_C__t3 | 1_1_yosys_canonicalize | 2.9 | last meaningful line 1.0 h ago (131/131 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2916065 | dsdv_slice_lepe_nh_mus_LP__t1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3083/3084 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mus_C__t1-1667594 | dsdv_slice_lepw_mus_C__t1 | 4_1_cts | 6.2 | last meaningful line 0.1 h ago (3458/3458 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-glue-1559836 | glue | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (4909/4909 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-hd_lep0N-1545648 | hd_lep0N | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (8049/8049 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | postcts_gate_TT | 14.7 | last meaningful line 0.5 h ago (3450/3450 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_io_cor_v1-1914571 | kv3_io_cor_v1 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 16.2 | last meaningful line 2.0 h ago (209/227 lines) | YOUNG: evidence 2.7 h < 6 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-3536309 | ot_s81sl_leaf__t2 | 5_1_grt | 2.8 | last meaningful line 0.1 h ago (153/153 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t32-3518438 | ot_s81sl_leaf__t32 | 5_1_grt | 2.8 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-3520587 | ot_s81sl_leaf__t53 | 5_1_grt | 2.8 | last meaningful line 0.3 h ago (205/209 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t71-2773215 | ot_s81sl_leaf__t71 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3129/3130 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (4891/4891 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t28-3353995 | slice_station__t28 | 5_2_route | 2.9 | last meaningful line 0.2 h ago (241/242 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t52-3521993 | slice_station__t52 | 5_1_grt | 2.8 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | 4_1_cts | 1.6 | last meaningful line 0.2 h ago (4899/4899 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | 4_1_cts | 1.1 | last meaningful line 0.2 h ago (6214/6214 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-tt_ctlm-1686138 | tt_ctlm | tt_setup_repair | 1.1 | repair_Viol best 790 last 790 rows 2 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | otc-105520-18563 | 105520 | signoff | 2.3 | last meaningful line 2.2 h ago (3/3 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | otc-2998450-18208 | 2998450 | signoff | 3.0 | last meaningful line 3.0 h ago (3/3 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | otc-3412049-32057 | 3412049 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (5/5 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i1t-1168015 | eco_20261122_143408_943433-i1t | 5_2_route | 6.4 | drt_violations best 1162 last 1162 rows 12 | YOUNG: evidence 6.0 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i1t-1135156 | eco_20261122_165619_1517073-i1t | 5_2_route | 4.0 | drt_violations best 36312 last 36312 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | 5_1_grt | 12.4 | last meaningful line 1.8 h ago (211/216 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-4133103 | kv3_io_ft | 6_report | 1.5 | last meaningful line 0.0 h ago (64/64 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t1-283252 | ot_s81sl_leaf__t1 | 5_1_grt | 8.2 | repair_TNS best 184155 last 184155 rows 4 | YOUNG: evidence 4.4 h < 6 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | postcts_gate_FF | 10.2 | last meaningful line 0.1 h ago (1846/1846 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl55be2264-3685080 | sle_stm_v2 | 5_2_route | 10.3 | drt_violations best 173511 last 173511 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t24__cl66b71008-1567905 | slice_station__t24 | hold_gate | 0.4 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | 5_2_route | 10.3 | last meaningful line 0.5 h ago (286/287 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel2 | otc-2264137-19710 | 2264137 | ot_bind_native_c2c8fa68db0e1061157e772a | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pvce76611c-2806984 | col_h10_r1__t1 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_2_route | 13.4 | drt_violations best 5155 last 5155 rows 11 | before-window best 363722, window best 5155 | PROGRESS: drt_violations improved 98.6 % in window |  |
| epyc10 | dpkit-dsdv_slice_lepe_mu_LP__t2-1472079 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_LP__t2-2617721 | dsdv_slice_lepw_mus_LP__t2 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_sys_c-1472961 | kv3_sys_c | 5_1_grt | 3.3 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 14.7 | last meaningful line 0.5 h ago (1395/1395 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 66.2 | last meaningful line 1.4 h ago (1608/1608 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-2470572 | col_h9_r1__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2510614 | col_h9_r1__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_io_cor_v1-3748922 | kv3_io_cor_v1 | 5_1_grt | 1.7 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-tt_ctlm-2035057 | tt_ctlm | pregrt_ff_hold | 5.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | prd-eco_20261122_123708_2624415-i1t-3236939 | eco_20261122_123708_2624415-i1t | 5_2_route | 8.3 | drt_violations best 1 last 1 rows 50 | before-window best 84758, window best 1 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-hd_ctl-1922947 | hd_ctl | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 16.8 | drt_violations best 14242 last 14242 rows 13 | before-window best 19428, window best 14242 | PROGRESS: drt_violations improved 26.7 % in window |  |
| epyc8 | dpkit-glue-555250 | glue | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-237532 | col_h10_r1__t1 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 8.8 | drt_violations best 25 last 25 rows 19 | before-window best 15272, window best 25 | PROGRESS: drt_violations improved 99.8 % in window |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-3359910 | col_h10_r0_p4__t1 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_1_grt | 16.5 | grt_hold_TNS best 0 last 0 rows 4 | PROGRESS: grt_hold_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3518851 | col_h9_r0_p4__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3522410 | col_h9_r1__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-serdes__t1__clb45db5be-633399 | serdes__t1 | pregrt_ff_hold | 4.4 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-serdes__t4-2914107 | serdes__t4 | 4_1_cts | 0.4 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-sle_su_c-645555 | sle_su_c | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 23.7 | drt_violations best 1120 last 1120 rows 22 | before-window best 1719, window best 1120 | PROGRESS: drt_violations improved 34.8 % in window |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 5_2_route | 16.6 | drt_violations best 1420 last 1420 rows 4 | before-window best 156124, window best 1420 | PROGRESS: drt_violations improved 99.1 % in window |  |
| intel2 | dpkit-native59-3804419 | native59 | pregrt_ff_hold | 10.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
