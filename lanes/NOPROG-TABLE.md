# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 00:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'GRT-LABEL': 16, 'YOUNG': 163, 'NO-DATA': 46, 'PROGRESS': 31}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 16.4 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 16.4 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 33.0 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel2 | dpkit-native59-3804419 | native59 | pregrt_ff_hold | 13.2 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-ot_s81sl_leaf__t21-1070163 | ot_s81sl_leaf__t21 | 5_1_grt | 6.5 | grt rounds 3 overflow 5:63924 -> 10:62220 -> 15:58764 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t25__cl55642d17-3247888 | ot_s81sl_leaf__t25 | 5_1_grt | 5.0 | grt rounds 2 overflow 5:32072 -> 10:20314 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_1_grt | 5.8 | grt rounds 2 overflow 5:18611 -> 10:8682 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-3655640 | ot_s81sl_leaf__t65 | 5_1_grt | 9.3 | grt rounds 3 overflow 5:40772 -> 10:33760 -> 15:28118 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t1-4049223 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 9.2 | grt rounds 2 overflow 5:1776 -> 10:344 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t3-56823 | ot_s81sl_leaf__t3 | 5_1_grt | 6.6 | grt rounds 2 overflow 5:1586 -> 10:260 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-2217964 | col_h9_r2__t1 | 5_1_grt | 5.8 | grt rounds 2 overflow 5:2844 -> 10:292 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 19.1 | grt rounds 6 overflow 5:1893 -> 10:1268 -> 15:872 -> 20:551 -> 25:191 -> 30:43 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-coll_core-180674 | coll_core | 5_1_grt | 17.5 | grt rounds 2 overflow 5:14446 -> 10:2584 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 19.2 | grt rounds 6 overflow 5:805 -> 10:203 -> 15:132 -> 20:64 -> 25:77 -> 30:61 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 19.2 | grt rounds 6 overflow 5:2533 -> 10:1498 -> 15:842 -> 20:584 -> 25:584 -> 30:139 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-3536309 | ot_s81sl_leaf__t2 | 5_1_grt | 5.8 | grt rounds 2 overflow 5:42057 -> 10:49116 | GRT-LABEL: DESIGN-FAIL: overflow 49116 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-3520587 | ot_s81sl_leaf__t53 | 5_1_grt | 5.8 | grt rounds 2 overflow 5:29437 -> 10:25353 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t71-2773215 | ot_s81sl_leaf__t71 | 5_1_grt | 3.4 | grt rounds 2 overflow 5:13081 -> 10:7099 | GRT-LABEL: DESIGN-FAIL: overflow 7099 at round 10 > 1000 |  |
| intel1 | dpkit-serdes__t1__clb45db5be-633399 | serdes__t1 | 5_1_grt | 7.4 | grt rounds 1 overflow 5:291 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 15.4 | grt rounds 2 overflow 5:88896 -> 10:83085 | GRT-LABEL: DESIGN-FAIL: overflow 83085 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_LP__t2-2617721 | dsdv_slice_lepw_mus_LP__t2 | 5_1_grt | 5.8 | last meaningful line 0.1 h ago (145/145 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | reg_fanout | 17.7 |  | NO-DATA: empty log |  |
| epyc10 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2569171 | sle_hc1 | 5_1_grt | 3.2 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-3135509 | sle_stm_v1 | postplace_setup | 0.1 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v2__cl7b3062fa-3029892 | sle_stm_v2 | 5_2_route | 8.1 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | otc-1668180-3684 | 1668180 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc10 | otc-3054257-22938 | 3054257 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | otc-3080970-10021 | 3080970 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-3082835-5546 | 3082835 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | otc-3085148-20039 | 3085148 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | otc-3087131-13276 | 3087131 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | otc-3123037-10651 | 3123037 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | otc-3138311-23060 | 3138311 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 3.1 | last meaningful line 0.3 h ago (290/291 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i1-42727 | eco_20261122_223531_3628570-i1 | 5_2_route | 4.9 | drt_violations best 649 last 649 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_040953_1214866-i1-1617727 | eco_20261123_040953_1214866-i1 | 5_2_route | 3.8 | drt_violations best 178 last 178 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_075519_12410-i1t-3218186 | eco_20261123_075519_12410-i1t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-bk_sel__t2-3621944 | bk_sel__t2 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3789030 | col_h10_r0_p1__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (70/70 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-1815940 | col_h10_r0_p1__t1 | 5_1_grt | 5.8 | last meaningful line 0.5 h ago (211/217 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cld01bb4ae-1062709 | col_h10_r1__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 28541.7 last 28541.7 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-1483343 | col_h9_r0_p4__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 94532.8 last 94532.8 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-2470572 | col_h9_r1__t1 | tt_setup_repair_grt | 5.5 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2108278 | dsdv_slice_c1x_C__t1 | 5_1_grt | 8.0 | last meaningful line 2.3 h ago (208/212 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2115818 | dsdv_slice_c1x_C__t10 | 5_1_grt | 8.0 | last meaningful line 2.0 h ago (211/217 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t8-1544833 | dsdv_slice_c1x_C__t8 | selrange | 1.4 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-dsdv_slice_lepe_mu_C__t1-3116985 | dsdv_slice_lepe_mu_C__t1 | 5_1_grt | 5.1 | last meaningful line 0.1 h ago (207/208 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1565179 | dsdv_slice_lepe_nh_mus_C__t1 | selrange | 1.4 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 5.8 | repair_TNS best 865782 last 865782 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 4.7 | repair_TNS best 988470 last 988470 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-hd_lep0N_w-3963146 | hd_lep0N_w | pregrt_ff_hold | 4.6 | repair_TNS best 1.78947e+06 last 1.78947e+06 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-hd_st_n4-3773474 | hd_st_n4 | 3_3_place_gp | 0.1 | overflow best 0.535 last 0.535 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-hd_st_n4-3832545 | hd_st_n4 | 2_4_floorplan_pdn | 0.0 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-hd_st_n4-3835728 | hd_st_n4 | 2_4_floorplan_pdn | 0.0 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-hd_st_n4-3887286 | hd_st_n4 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1p2-1100885 | kv3_hg_v1p2 | 3_4_place_resized | 1.6 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v5-1464049 | kv3_hgi_v5 | pregrt_ff_hold | 1.4 | repair_TNS best 16724.2 last 16724.2 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-kv3_io_cor_v1-3748922 | kv3_io_cor_v1 | 5_2_route | 4.7 | drt_violations best 60486 last 60486 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v3n-1352817 | kv3_pv_v3n | 2_1_floorplan | 1.4 | last meaningful line 0.5 h ago (1553/1553 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4n-420301 | kv3_pv_v4n | 3_1_place_gp_skip_io | 1.9 | overflow best 0.7205 last 0.7205 rows 22 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t3-3850759 | ot_s81sl_kv_leaf__t3 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t11-3893305 | ot_s81sl_leaf__t11 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t41-3837047 | ot_s81sl_leaf__t41 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t43-562324 | ot_s81sl_leaf__t43 | 5_1_grt | 4.1 | last meaningful line 1.5 h ago (205/214 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t67-3630815 | ot_s81sl_leaf__t67 | hold_gate | 0.2 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t7-3842605 | ot_s81sl_leaf__t7 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-775509 | sle_ctl | 4_1_cts | 1.7 | last meaningful line 0.3 h ago (9056/9056 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | postcts_gate_TT | 8.1 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | 5_1_grt | 8.0 | last meaningful line 0.1 h ago (214/275 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | 5_1_grt | 8.0 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | 5_1_grt | 8.0 | last meaningful line 0.1 h ago (1242/1248 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 8.0 | drt_violations best 16338 last 16338 rows 4 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 4.6 | last meaningful line 0.1 h ago (264/265 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 5.0 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | otc-2114902-19881 | 2114902 | - | 3.3 |  | NO-DATA: no log found |  |
| epyc2 | otc-2186430-24000 | 2186430 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc2 | otc-271425-6325 | 271425 | - | 2.0 |  | NO-DATA: no log found |  |
| epyc2 | otc-3531681-14090 | 3531681 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc2 | otc-3553860-12060 | 3553860 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc2 | otc-3704474-1214 | 3704474 | - | 2.3 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261122_164248_3895049-i1-2533130 | eco_20261122_164248_3895049-i1 | 5_1_grt | 0.8 | last meaningful line 0.2 h ago (240/358 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164521_3948325-i1-2180646 | eco_20261122_164521_3948325-i1 | 5_1_grt | 1.0 | last meaningful line 0.3 h ago (237/1290 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i1t-1909174 | eco_20261122_181101_3945375-i1t | 5_2_route | 5.8 | drt_violations best 9568 last 9568 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i1t-3508652 | eco_20261122_190506_3875261-i1t | 5_2_route | 4.9 | drt_violations best 25875 last 25875 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | prd-fin-1443078 | fin | 6_report | 0.3 | last meaningful line 0.1 h ago (742/742 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | vis-head-3176835 | vis-head | - | 0.4 |  | NO-DATA: no log found |  |
| epyc2 | vis-head-3276080 | vis-head | - | 0.4 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-col-h9-r1--t1--cl49d7a23e--pv0a45e191-grt-707624 | col-h9-r1--t1--cl49d7a23e--pv0a45e191-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-4118481 | col_h10_r0_p4__t1 | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (189/189 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t9-4069286 | dsdv_slice_c1x_C__t9 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3565523 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_ctl-1922947 | hd_ctl | 5_2_route | 5.6 | drt_violations best 53701 last 53701 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2-603007 | kv3_pv_v2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (93/93 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t22-4105867 | ot_s81sl_leaf__t22 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (4195/4195 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1181364 | ot_s81sl_leaf__t39 | 5_1_grt | 5.9 | last meaningful line 0.7 h ago (264/1281 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | postcts_gate_TT | 9.8 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-1530301 | sle_hc0 | 5_2_route | 5.7 | drt_violations best 99839 last 99839 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | postcts_gate_FF | 10.7 | last meaningful line -0.0 h ago (97134/97134 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-881903 | sle_stm_v1 | 5_2_route | 10.8 | drt_violations best 194338 last 194338 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t18-1919126 | slice_station__t18 | generate_abstract | 5.6 | last meaningful line 0.0 h ago (177/177 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t40__cl1ea9de02-1928775 | slice_station__t40 | 5_2_route | 5.6 | drt_violations best 21015 last 21015 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t6__cl54a9ceeb-1772119 | slice_station__t6 | generate_abstract | 5.6 | last meaningful line 0.1 h ago (198/198 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 10.7 | last meaningful line 0.1 h ago (263/263 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl9beb65e6-3994155 | slw_stm_v2 | 5_2_route | 9.3 | last meaningful line 0.0 h ago (254/254 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 5.7 | drt_violations best 311954 last 311954 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | otc-254531-30458 | 254531 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc7 | otc-2707491-20991 | 2707491 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc7 | otc-2974334-11732 | 2974334 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc7 | otc-3346487-26799 | 3346487 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc7 | otc-3562518-20801 | 3562518 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc7 | otc-3815737-1746 | 3815737 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc7 | otc-3970901-4095 | 3970901 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261122_215654_330309-i2t-1668391 | eco_20261122_215654_330309-i2t | 5_2_route | 2.6 | drt_violations best 101 last 101 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_220050_168828-i2t-1232517 | eco_20261122_220050_168828-i2t | 5_2_route | 3.0 | drt_violations best 21782 last 21782 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-2034515 | col_h10_r1__t1 | 5_1_grt | 2.1 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1919292 | col_h9_r0_p2__t1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3275/3275 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2000675 | col_h9_r0_p2__t1 | tt_setup_repair_grt | 5.9 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t1-2205610 | dsdv_slice_c1x_C__t1 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t8-1783469 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-1930297 | dsdv_slice_kv512_C__t1 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (2984/2984 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2088472 | dsdv_slice_lepe_nh_mus_C__t1 | pregrt_ff_hold | 5.8 | repair_TNS best 80460.1 last 80460.1 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-glue-555250 | glue | postcts_gate_TT | 8.3 | last meaningful line 0.0 h ago (3004/3004 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg-3089265 | kv3_hg | 3_5_place_dp | 1.7 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p6-2039106 | kv3_hg_v1p6 | 2_1_floorplan | 0.3 | repair_Viol best 7321 last 7321 rows 656 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_hgi_v4-2007136 | kv3_hgi_v4 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.1 h ago (483/483 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 7.3 | drt_violations best 24545 last 24545 rows 10 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 3.2 | last meaningful line 2.5 h ago (11728/11728 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-494270 | kv3_hub_Ei | 5_2_route | 8.3 | last meaningful line 0.3 h ago (283/284 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-2296613 | kv3_hub_Eo | 2_1_floorplan | 0.2 | last meaningful line 0.1 h ago (105/105 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-2343024 | kv3_hub_Wo | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (105/105 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-619668 | kv3_io_cor_v1 | postcts_gate_FF | 2.6 | last meaningful line 0.0 h ago (1173/1173 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pc_v1__cl7f648944-2346761 | kv3_pc_v1 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pc_v1__cl7f648944-2365284 | kv3_pc_v1 | synth_odb_v | 0.2 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v12-2115834 | kv3_pv_v12 | 2_1_floorplan | 0.3 | last meaningful line 0.1 h ago (241/241 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-164511 | kv3_pv_v6 | 3_3_place_gp | 2.7 | overflow best 0.6397 last 0.6397 rows 17 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t14-2320204 | ot_s81sl_leaf__t14 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (55/55 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t23-1888361 | ot_s81sl_leaf__t23 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t32-1902400 | ot_s81sl_leaf__t32 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (3324/3324 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t36-1897305 | ot_s81sl_leaf__t36 | 3_3_place_gp | 0.3 | last meaningful line 0.1 h ago (164/164 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t61-1869131 | ot_s81sl_leaf__t61 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-2008589 | sle_su_l1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3717/3717 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-3353467 | slw_st_a_v2 | tt_setup_repair_grt | 3.1 | repair_Violations best 590 last 590 rows 76 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | otc-1173846-21068 | 1173846 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-1174520-11483 | 1174520 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-1910005-4834 | 1910005 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-2514615-8132 | 2514615 | lec | 0.1 | LEC last write 0.1 h ago | YOUNG: evidence 0.1 h < 6 h |  |
| epyc8 | otc-2593908-9338 | 2593908 | - | 1.9 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-kv3-pc-v3-grt-4171511 | kv3-pc-v3-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t33-grt-4177537 | ot-s81sl-leaf--t33-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl911743eb-4131559 | col_h10_r0_p1__t1 | 5_1_grt | 3.0 | last meaningful line 0.1 h ago (210/213 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2093461 | col_h10_r1__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 28473.2 last 28473.2 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-4076788 | col_h10_r1__t1 | 5_1_grt | 3.0 | last meaningful line 0.3 h ago (210/213 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2103226 | col_h10_r2__t1 | 5_1_grt | 1.5 | repair_TNS best 2050.16 last 2050.16 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2653831 | col_h9_r0_p3__t1 | 3_4_place_resized | 1.1 | repair_Remaining best 164006 last 164006 rows 57 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_1_grt | 3.9 | last meaningful line 0.1 h ago (211/215 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv40e9fb5a-287653 | col_h9_r2__t1 | 5_2_route | 5.8 | last meaningful line 0.1 h ago (280/281 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t7-2862427 | dsdv_slice_c1x_C__t7 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_kv512_C__t1-288662 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 5.8 | last meaningful line 3.3 h ago (37/37 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-3178195 | hd_ctl | pregrt_ff_hold | 0.8 | repair_TNS best 368538 last 368538 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-hd_ctl-53400 | hd_ctl | lec | 0.1 | LEC last write -0.0 h ago | YOUNG: evidence 0.1 h < 6 h |  |
| epyc9 | dpkit-kv3_hgi_v3-2875910 | kv3_hgi_v3 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (6135/6135 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (3760/3760 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v2n-2681030 | kv3_pv_v2n | 2_4_floorplan_pdn | 1.1 | last meaningful line 0.0 h ago (110/110 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v4-2911509 | kv3_pv_v4 | lec | 1.0 | LEC last write 0.1 h ago | YOUNG: evidence 1.0 h < 6 h |  |
| epyc9 | dpkit-kv3_pv_v6n-2406851 | kv3_pv_v6n | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (7855/7855 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t15-153595 | ot_s81sl_leaf__t15 | selrange | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-461535 | ot_s81sl_leaf__t44 | 5_1_grt | 2.6 | last meaningful line 0.5 h ago (204/209 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t56-866545 | ot_s81sl_leaf__t56 | 5_1_grt | 2.3 | last meaningful line 0.0 h ago (159/159 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-phy__t1-2625032 | phy__t1 | 5_1_grt | 1.2 | last meaningful line 0.1 h ago (167/167 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (5067/5067 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | pregrt_ff_hold | 3.8 | repair_TNS best 148202 last 148202 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-slice_station__t22-239981 | slice_station__t22 | generate_abstract | 5.9 | last meaningful line 0.1 h ago (280/280 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-570014 | slice_station__t51 | 6_report | 10.1 | last meaningful line 0.1 h ago (348/348 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t6__cl0755c26e-2749197 | slice_station__t6 | 5_1_grt | 1.1 | last meaningful line 0.1 h ago (545/576 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | pregrt_ff_hold | 3.0 | repair_TNS best 111790 last 111790 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | selrange | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-3009482 | slw_fe_v2 | pregrt_ff_hold | 3.8 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | 4_1_cts | 3.0 | last meaningful line 0.0 h ago (5354/5354 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | eco-abs-2785968 | eco-abs | generate_abstract | 1.1 | last meaningful line 0.4 h ago (528/528 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | lrc-qgrt-12404 | lrc-qgrt | qgrt | 0.1 | last meaningful line 0.0 h ago (42/44 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | lrc-qgrt-3979888 | lrc-qgrt | qgrt | 0.2 | last meaningful line 0.1 h ago (44/47 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-1108174-15457 | 1108174 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-1631796-31019 | 1631796 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-1661483-30301 | 1661483 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-1916796-12156 | 1916796 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-3850737-30319 | 3850737 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc9 | otc-664483-8927 | 664483 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc9 | otc-664799-872 | 664799 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261122_180231_342380-i2-1306615 | eco_20261122_180231_342380-i2 | 5_2_route | 2.0 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | prd-fin-3504713 | fin | 6_report | 0.3 | last meaningful line 0.1 h ago (279/279 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-3359910 | col_h10_r0_p4__t1 | 5_1_grt | 5.9 | last meaningful line 0.3 h ago (208/214 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3534091 | col_h10_r2__t1 | 5_2_route | 5.8 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 19.5 | last meaningful line 0.5 h ago (282/283 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-3535177 | col_h9_r0_p5__t1 | 5_1_grt | 5.8 | last meaningful line 1.0 h ago (210/217 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvc1b82625-3531236 | col_h9_r0_p5__t1 | 5_1_grt | 5.8 | last meaningful line 0.5 h ago (210/216 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3522355 | col_h9_r2__t1 | 5_1_grt | 5.8 | repair_TNS best 5400.22 last 5400.22 rows 5 | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvcf44b14c-1664216 | col_h9_r2__t1 | 5_2_route | 9.2 | drt_violations best 52013 last 52013 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-3365034 | dsdv_slice_c1x_C__t3 | 3_5_place_dp | 5.9 | last meaningful line 0.1 h ago (120/120 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-hd_lep0N-1545648 | hd_lep0N | 4_2_tapbal_grt | 4.2 | last meaningful line 2.0 h ago (48/52 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_2_route | 17.7 | last meaningful line 0.5 h ago (279/280 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v7-3747893 | kv3_pv_v7 | 2_1_floorplan | 2.8 | last meaningful line 1.8 h ago (1547/1547 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-serdes__t4-2914107 | serdes__t4 | 5_1_grt | 3.4 | last meaningful line 0.1 h ago (153/153 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | 4_1_cts | 3.4 | last meaningful line 0.3 h ago (5358/5358 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-sle_su_c-645555 | sle_su_c | 5_1_grt | 7.4 | last meaningful line 1.3 h ago (281/1290 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t28-3353995 | slice_station__t28 | 5_2_route | 5.9 | drt_violations best 13901 last 13901 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t52-3521993 | slice_station__t52 | postcts_gate_FF | 5.8 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 5.9 | last meaningful line 0.3 h ago (265/266 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | otc-589898-30912 | 589898 | - | 2.0 |  | NO-DATA: no log found |  |
| intel1 | otc-590329-1688 | 590329 | - | 2.0 |  | NO-DATA: no log found |  |
| intel1 | otc-591591-991 | 591591 | - | 2.0 |  | NO-DATA: no log found |  |
| intel1 | otc-910747-1220 | 910747 | - | 1.8 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 3.2 | last meaningful line 0.3 h ago (153/153 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i1-1606115 | eco_20261122_143408_943433-i1 | 5_2_route | 1.4 | last meaningful line 0.3 h ago (258/259 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i1-380897 | eco_20261122_165619_1517073-i1 | 5_2_route | 2.2 | last meaningful line 0.3 h ago (275/276 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | 5_2_route | 11.2 | last meaningful line 0.3 h ago (288/289 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2864182 | coll_ftm | generate_abstract | 2.7 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-495457 | coll_ftm | 5_2_route | 1.5 | last meaningful line 0.1 h ago (235/236 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | 5_1_grt | 15.4 | last meaningful line 4.8 h ago (211/220 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel2 | dpkit-gunit__t1-2233417 | gunit__t1 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-2230183 | hd_turn_a | 6_report | 0.5 | last meaningful line 0.0 h ago (63/63 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-2243143 | hd_turn_a | 5_2_route | 0.5 | drt_violations best 5463 last 5463 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-kv3_io_ft-483181 | kv3_io_ft | 5_2_route | 1.5 | drt_violations best 5487 last 5487 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | dpkit-kv3_pv_v5-3790571 | kv3_pv_v5 | 3_1_place_gp_skip_io | 2.0 | overflow best 0.517 last 0.517 rows 25 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-sle_ctl__cla4f6f12f-2733138 | sle_ctl | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (68/68 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 13.2 | last meaningful line 0.3 h ago (280/281 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl55be2264-3685080 | sle_stm_v2 | 6_report | 13.3 | last meaningful line 0.0 h ago (735/735 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-2267874 | slice_station__t12 | postcts_gate_TT | 0.5 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | 5_2_route | 13.3 | drt_violations best 66861 last 66861 rows 2 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_2_route | 16.4 | drt_violations best 1677 last 1677 rows 21 | before-window best 29667, window best 1677 | PROGRESS: drt_violations improved 94.3 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 69.2 | last meaningful line 1.1 h ago (1612/1612 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-1820678 | col_h10_r0_p1__t1 | pregrt_ff_hold | 5.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_hgi_v4-724077 | kv3_hgi_v4 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_1_grt | 1.4 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | pregrt_ff_hold | 5.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | pregrt_ff_hold | 5.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | prd-eco_20261122_123708_2624415-i1t-3236939 | eco_20261122_123708_2624415-i1t | 5_2_route | 11.3 | drt_violations best 1 last 1 rows 55 | before-window best 57, window best 1 | PROGRESS: drt_violations improved 98.2 % in window |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_2_route | 15.9 | drt_violations best 1 last 1 rows 43 | before-window best 110424, window best 1 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 16.4 | drt_violations best 115 last 115 rows 20 | before-window best 180834, window best 115 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 19.8 | drt_violations best 13260 last 13260 rows 14 | before-window best 16565, window best 13260 | PROGRESS: drt_violations improved 20.0 % in window |  |
| epyc8 | dpkit-kv3_hgi_v2__cle0015330-3274473 | kv3_hgi_v2 | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hgi_v2__cle0015330-3323577 | kv3_hgi_v2 | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-1144307 | serdes__t1 | 4_1_cts | 0.7 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2109433 | col_h10_r0_p4__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_2_route | 19.4 | drt_violations best 22 last 22 rows 59 | before-window best 178849, window best 22 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | pregrt_ff_hold | 5.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_hgi_v1__cl42bc8b12-2545242 | kv3_hgi_v1 | pregrt_ff_hold | 1.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_fw_v2__cl69f5e854-2970240 | sle_fw_v2 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fw_v3-3096266 | slw_fw_v3 | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 11.8 | drt_violations best 20 last 57 rows 26 | before-window best 71, window best 20 | PROGRESS: drt_violations improved 71.8 % in window |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_2_route | 19.2 | drt_violations best 195281 last 195281 rows 1 | before-window best 195281, window best 195281 | PROGRESS: drt_violations: active iteration at 68650 < best completed total 195281 (in-iter |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 19.2 | drt_violations best 210671 last 210671 rows 1 | before-window best 210671, window best 210671 | PROGRESS: drt_violations: active iteration at 83161 < best completed total 210671 (in-iter |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2916065 | dsdv_slice_lepe_nh_mus_LP__t1 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-glue-1559836 | glue | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-tt_ctlm-1686138 | tt_ctlm | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 26.7 | drt_violations best 1064 last 1064 rows 23 | before-window best 1452, window best 1064 | PROGRESS: drt_violations improved 26.7 % in window |  |
