# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 00:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'GRT-LABEL': 16, 'YOUNG': 164, 'NO-DATA': 42, 'EXCLUDED': 3, 'PROGRESS': 37}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | prd-eco_20261122_123708_2624415-i1t-3236939 | eco_20261122_123708_2624415-i1t | 5_2_route | 11.8 | drt_violations best 1 last 1 rows 55 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 33.5 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc10 | dpkit-ot_s81sl_leaf__t21-1070163 | ot_s81sl_leaf__t21 | 5_1_grt | 7.0 | grt rounds 3 overflow 5:63924 -> 10:62220 -> 15:58764 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t25__cl55642d17-3247888 | ot_s81sl_leaf__t25 | 5_1_grt | 5.5 | grt rounds 2 overflow 5:32072 -> 10:20314 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_1_grt | 6.3 | grt rounds 2 overflow 5:18611 -> 10:8682 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t43-562324 | ot_s81sl_leaf__t43 | 5_1_grt | 4.6 | grt rounds 2 overflow 5:97661 -> 10:93648 | GRT-LABEL: DESIGN-FAIL: overflow 93648 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t67-3630815 | ot_s81sl_leaf__t67 | 5_1_grt | 0.7 | grt rounds 2 overflow 5:42145 -> 10:31930 | GRT-LABEL: DESIGN-FAIL: overflow 31930 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t1-4049223 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 9.7 | grt rounds 2 overflow 5:1776 -> 10:344 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t3-56823 | ot_s81sl_leaf__t3 | 5_1_grt | 7.1 | grt rounds 2 overflow 5:1586 -> 10:260 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-2217964 | col_h9_r2__t1 | 5_1_grt | 6.3 | grt rounds 2 overflow 5:2844 -> 10:292 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 19.6 | grt rounds 6 overflow 5:1893 -> 10:1268 -> 15:872 -> 20:551 -> 25:191 -> 30:43 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-3359910 | col_h10_r0_p4__t1 | 5_1_grt | 6.4 | grt rounds 2 overflow 5:62054 -> 10:304 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-coll_core-180674 | coll_core | 5_1_grt | 18.0 | grt rounds 2 overflow 5:14446 -> 10:2584 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 19.7 | grt rounds 6 overflow 5:805 -> 10:203 -> 15:132 -> 20:64 -> 25:77 -> 30:61 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 19.7 | grt rounds 6 overflow 5:2533 -> 10:1498 -> 15:842 -> 20:584 -> 25:584 -> 30:139 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-3520587 | ot_s81sl_leaf__t53 | 5_1_grt | 6.3 | grt rounds 2 overflow 5:29437 -> 10:25353 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-serdes__t1__clb45db5be-633399 | serdes__t1 | 5_1_grt | 7.9 | grt rounds 1 overflow 5:291 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 15.9 | grt rounds 3 overflow 5:88896 -> 10:83085 -> 15:86608 | GRT-LABEL: DESIGN-FAIL: overflow 83085 at round 10 > 1000 |  |
| epyc10 | dpkit-hd_st_n4-3814785 | hd_st_n4 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (1684/1684 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_st_n4-3874931 | hd_st_n4 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (1596/1596 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_st_n4-3877061 | hd_st_n4 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (1596/1596 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-3882608 | kv3_pv_v3 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (193/193 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3e-3821788 | kv3_pv_v3e | port_bind | 0.1 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | synth_odb_v | 18.2 | last meaningful line 0.3 h ago (4/4 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3447267 | sle_hc2 | pregrt_ff_hold | 0.3 | repair_TNS best 10857 last 10857 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-3135509 | sle_stm_v1 | pregrt_ff_hold | 0.6 | repair_TNS best 28788.4 last 28788.4 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | dpkit-sle_stm_v2__cl7b3062fa-3029892 | sle_stm_v2 | 5_2_route | 8.6 | last meaningful line 0.5 h ago (276/277 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | otc-1668180-3684 | 1668180 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc10 | otc-3082835-5546 | 3082835 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc10 | otc-3377424-4079 | 3377424 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc10 | otc-3397414-6968 | 3397414 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc10 | otc-3773901-7934 | 3773901 | asbuilt.yosys | 0.1 | last meaningful line 0.0 h ago (134296/134296 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 3.6 | drt_violations best 154752 last 154752 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i1-42727 | eco_20261122_223531_3628570-i1 | 5_3_fillcell | 5.4 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_040953_1214866-i1-1617727 | eco_20261123_040953_1214866-i1 | 5_2_route | 4.3 | drt_violations best 178 last 178 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_075519_12410-i1t-3218186 | eco_20261123_075519_12410-i1t | 5_1_grt | 0.5 | last meaningful line 0.3 h ago (229/1373 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-bk_sel__t2-3621944 | bk_sel__t2 | 3_3_place_gp | 0.7 | overflow best 0.2169 last 0.2415 rows 9 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-1820678 | col_h10_r0_p1__t1 | 5_1_grt | 6.3 | last meaningful line 0.0 h ago (98/98 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3789030 | col_h10_r0_p1__t1 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (3763/3763 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-1815940 | col_h10_r0_p1__t1 | 5_1_grt | 6.3 | last meaningful line 1.0 h ago (211/221 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-1483343 | col_h9_r0_p4__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 94532.8 last 94532.8 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-2470572 | col_h9_r1__t1 | 5_2_route | 6.0 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2108278 | dsdv_slice_c1x_C__t1 | 5_1_grt | 8.5 | last meaningful line 2.8 h ago (208/212 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2115818 | dsdv_slice_c1x_C__t10 | 5_1_grt | 8.5 | last meaningful line 2.5 h ago (211/218 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t8-1544833 | dsdv_slice_c1x_C__t8 | selrange | 1.9 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-dsdv_slice_lepe_mu_C__t1-3116985 | dsdv_slice_lepe_mu_C__t1 | 5_1_grt | 5.6 | last meaningful line 0.5 h ago (207/210 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1565179 | dsdv_slice_lepe_nh_mus_C__t1 | selrange | 1.9 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 6.3 | repair_TNS best 865782 last 865782 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 5.2 | repair_TNS best 988470 last 988470 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-hd_lep0N_w-3963146 | hd_lep0N_w | pregrt_ff_hold | 5.1 | repair_TNS best 285132 last 285132 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | postcts_gate_TT | 1.9 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-3921528 | kv3_hroot | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (3158/3158 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_io_cor_v1-3748922 | kv3_io_cor_v1 | 5_2_route | 5.2 | drt_violations best 60486 last 60486 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v3n-1352817 | kv3_pv_v3n | 3_1_place_gp_skip_io | 1.9 | overflow best 0.8909 last 0.8909 rows 5 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-kv3_pv_v4n-420301 | kv3_pv_v4n | 3_3_place_gp | 2.4 | overflow best 0.6994 last 0.701 rows 5 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t1-3941275 | ot_s81sl_leaf__t1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4842/4843 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t11-3893305 | ot_s81sl_leaf__t11 | pregrt_ff_hold | 0.5 | last meaningful line -0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t41-3837047 | ot_s81sl_leaf__t41 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3199/3199 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t7-3842605 | ot_s81sl_leaf__t7 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3205/3206 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-775509 | sle_ctl | 4_1_cts | 2.2 | last meaningful line 0.3 h ago (9083/9083 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | 5_2_route | 8.6 | last meaningful line -0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | 5_1_grt | 8.5 | last meaningful line 0.1 h ago (1003/1020 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | 5_1_grt | 8.5 | last meaningful line 0.3 h ago (213/974 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 8.5 | drt_violations best 16338 last 16338 rows 4 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 5.1 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 5.5 | drt_violations best 168344 last 168344 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | eco-abs-4084562 | eco-abs | generate_abstract | 0.4 | last meaningful line 0.3 h ago (704/704 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | otc-2114902-19881 | 2114902 | - | 3.8 |  | NO-DATA: no log found |  |
| epyc2 | otc-2186430-24000 | 2186430 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc2 | otc-271425-6325 | 271425 | - | 2.5 |  | NO-DATA: no log found |  |
| epyc2 | otc-3531681-14090 | 3531681 | - | 2.9 |  | NO-DATA: no log found |  |
| epyc2 | otc-3553860-12060 | 3553860 | - | 2.9 |  | NO-DATA: no log found |  |
| epyc2 | otc-3704474-1214 | 3704474 | - | 2.8 |  | NO-DATA: no log found |  |
| epyc2 | prd-count-p1_tc-1909174 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164248_3895049-i1-2533130 | eco_20261122_164248_3895049-i1 | 5_1_grt | 1.3 | last meaningful line 0.6 h ago (240/1395 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164521_3948325-i1-2180646 | eco_20261122_164521_3948325-i1 | 5_1_grt | 1.5 | last meaningful line 0.8 h ago (237/1363 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i1t-3508652 | eco_20261122_190506_3875261-i1t | 5_2_route | 5.4 | drt_violations best 25875 last 25875 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | vis-head-3176835 | vis-head | - | 0.9 |  | NO-DATA: no log found |  |
| epyc2 | vis-head-3276080 | vis-head | - | 0.9 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-836163 | col_h9_r0_p5__t1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3309/3309 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t9-4069286 | dsdv_slice_c1x_C__t9 | 1_1_yosys_canonicalize | 1.2 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3565523 | dsdv_slice_lepe_nh_mus_C__t1 | selrange | 1.6 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-hd_ctl-1922947 | hd_ctl | 5_2_route | 6.1 | drt_violations best 145 last 145 rows 4 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_st_n4-1251911 | hd_st_n4 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (1629/1629 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v1-1064320 | kv3_pv_v1 | 2_1_floorplan | 0.2 | repair_Viol best 1311 last 1311 rows 96 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v2-603007 | kv3_pv_v2 | 2_1_floorplan | 0.6 | last meaningful line 0.2 h ago (388/388 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t22-4105867 | ot_s81sl_leaf__t22 | hold_gate | 1.2 | last meaningful line -0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1181364 | ot_s81sl_leaf__t39 | 5_1_grt | 6.4 | last meaningful line 1.2 h ago (264/1288 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | 5_2_route | 10.3 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-1530301 | sle_hc0 | 5_2_route | 6.2 | drt_violations best 99839 last 99839 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | 5_2_route | 11.2 | last meaningful line 0.3 h ago (132/132 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-881903 | sle_stm_v1 | 5_2_route | 11.3 | drt_violations best 194338 last 194338 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t40__cl1ea9de02-1928775 | slice_station__t40 | 6_report | 6.1 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 11.2 | last meaningful line 0.5 h ago (264/265 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl9beb65e6-3994155 | slw_stm_v2 | 5_2_route | 9.8 | last meaningful line 0.3 h ago (264/265 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 6.2 | drt_violations best 311954 last 311954 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | otc-254531-30458 | 254531 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc7 | otc-2707491-20991 | 2707491 | - | 2.3 |  | NO-DATA: no log found |  |
| epyc7 | otc-2974334-11732 | 2974334 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc7 | otc-3346487-26799 | 3346487 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc7 | otc-3562518-20801 | 3562518 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc7 | otc-3815737-1746 | 3815737 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc7 | otc-3970901-4095 | 3970901 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261122_215654_330309-i2t-1668391 | eco_20261122_215654_330309-i2t | 5_2_route | 3.1 | drt_violations best 101 last 101 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_080018_715668-i1t-847605 | eco_20261123_080018_715668-i1t | 5_1_grt | 0.4 | last meaningful line 0.1 h ago (153/153 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-2034515 | col_h10_r1__t1 | 5_1_grt | 2.6 | last meaningful line 0.3 h ago (205/208 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1919292 | col_h9_r0_p2__t1 | pregrt_ff_hold | 0.8 | repair_TNS best 55821.6 last 55821.6 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2000675 | col_h9_r0_p2__t1 | 5_2_route | 6.4 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t1-2205610 | dsdv_slice_c1x_C__t1 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t8-1783469 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-1930297 | dsdv_slice_kv512_C__t1 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (3307/3307 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-glue-555250 | glue | postcts_gate_FF | 8.8 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p6-2039106 | kv3_hg_v1p6 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.7793 last 0.8195 rows 20 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_hgi_v2__cle0015330-3274473 | kv3_hgi_v2 | 5_1_grt | 2.1 | last meaningful line 0.2 h ago (287/1293 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hgi_v2__cle0015330-3323577 | kv3_hgi_v2 | 5_1_grt | 2.1 | last meaningful line 0.2 h ago (287/1293 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hgi_v4-2007136 | kv3_hgi_v4 | 3_3_place_gp | 0.8 | overflow best 0.2222 last 0.2803 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 7.8 | drt_violations best 20426 last 20426 rows 11 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 3.7 | last meaningful line 3.0 h ago (11728/11728 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-494270 | kv3_hub_Ei | 5_2_route | 8.8 | last meaningful line 0.5 h ago (285/286 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-2296613 | kv3_hub_Eo | 2_4_floorplan_pdn | 0.7 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-2343024 | kv3_hub_Wo | 2_4_floorplan_pdn | 0.7 | last meaningful line 0.1 h ago (34/34 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-619668 | kv3_io_cor_v1 | 5_2_route | 3.1 | last meaningful line 0.0 h ago (244/245 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pc_v1__cl7f648944-2346761 | kv3_pc_v1 | 2_4_floorplan_pdn | 0.7 | last meaningful line 0.0 h ago (63/63 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pc_v1__cl7f648944-2365284 | kv3_pc_v1 | 2_4_floorplan_pdn | 0.7 | last meaningful line 0.0 h ago (63/63 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v12-2115834 | kv3_pv_v12 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.1808 last 0.1808 rows 38 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v6-164511 | kv3_pv_v6 | 3_3_place_gp | 3.2 | overflow best 0.0997 last 0.0997 rows 42 | YOUNG: stage 0.8 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t14-2320204 | ot_s81sl_leaf__t14 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (4250/4250 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t23-1888361 | ot_s81sl_leaf__t23 | 5_1_grt | 0.8 | last meaningful line 0.1 h ago (214/217 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t32-1902400 | ot_s81sl_leaf__t32 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (3778/3778 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t36-1897305 | ot_s81sl_leaf__t36 | 3_5_place_dp | 0.8 | last meaningful line 0.1 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t61-1869131 | ot_s81sl_leaf__t61 | 5_1_grt | 0.8 | last meaningful line 0.3 h ago (210/213 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-1144307 | serdes__t1 | pregrt_ff_hold | 1.2 | repair_TNS best 499561 last 499561 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-2008589 | sle_su_l1 | pregrt_ff_hold | 0.8 | repair_TNS best 1.23426e+06 last 1.23426e+06 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | otc-1173846-21068 | 1173846 | - | 2.9 |  | NO-DATA: no log found |  |
| epyc8 | otc-1174520-11483 | 1174520 | - | 2.9 |  | NO-DATA: no log found |  |
| epyc8 | otc-1910005-4834 | 1910005 | - | 2.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-2514615-8132 | 2514615 | lec | 0.6 | LEC last write 0.6 h ago | YOUNG: evidence 0.6 h < 6 h |  |
| epyc8 | otc-2593908-9338 | 2593908 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl911743eb-4131559 | col_h10_r0_p1__t1 | 5_1_grt | 3.5 | last meaningful line 0.5 h ago (210/219 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2109433 | col_h10_r0_p4__t1 | 5_1_grt | 2.0 | last meaningful line 0.1 h ago (158/158 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-4076788 | col_h10_r1__t1 | 5_1_grt | 3.5 | last meaningful line 0.8 h ago (210/220 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 6_report | 19.9 | last meaningful line 0.0 h ago (215/215 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_1_grt | 4.4 | last meaningful line 0.5 h ago (211/220 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv40e9fb5a-287653 | col_h9_r2__t1 | 5_2_route | 6.3 | drt_violations best 69579 last 69579 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t7-2862427 | dsdv_slice_c1x_C__t7 | selrange | 1.5 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-hd_ctl-3178195 | hd_ctl | pregrt_ff_hold | 1.3 | repair_TNS best 368538 last 368538 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-hd_ctl-53400 | hd_ctl | 3_3_place_gp | 0.6 | overflow best 0.2999 last 0.5494 rows 158 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-hd_lep0N_w-430653 | hd_lep0N_w | 3_3_place_gp | 0.3 | overflow best 0.6459 last 0.6459 rows 4 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-hd_lep0N_w-448517 | hd_lep0N_w | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_lep0N_w-553716 | hd_lep0N_w | 3_2_place_iop | 0.3 | last meaningful line -0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_lep0N_w-577040 | hd_lep0N_w | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hgi_v1__cl42bc8b12-2545242 | kv3_hgi_v1 | pregrt_ff_hold | 1.7 | repair_Violations best 241 last 241 rows 14 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | 4_1_cts | 1.6 | last meaningful line 0.1 h ago (3858/3858 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3472/3472 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv-146967 | kv3_pv | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v2n-2681030 | kv3_pv_v2n | 3_1_place_gp_skip_io | 1.6 | overflow best 0.2285 last 0.2285 rows 35 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v4-2911509 | kv3_pv_v4 | 2_4_floorplan_pdn | 1.5 | last meaningful line 0.0 h ago (94/94 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v5n-250741 | kv3_pv_v5n | 2_1_floorplan | 0.4 | repair_Viol best 1809 last 1809 rows 605 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v6n-2406851 | kv3_pv_v6n | 4_1_cts | 1.8 | last meaningful line 0.2 h ago (7882/7882 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-native59-274714 | native59 | pregrt_ff_hold | 0.4 | repair_TNS best 12876.5 last 12876.5 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-184640 | ot_s81sl_kv_leaf__t5 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (4621/4621 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 4.3 | repair_TNS best 7175.62 last 7175.62 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t15-153595 | ot_s81sl_leaf__t15 | 3_4_place_resized | 0.5 | last meaningful line 0.0 h ago (154/154 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t17-450077 | ot_s81sl_leaf__t17 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3666/3666 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-461535 | ot_s81sl_leaf__t44 | 5_1_grt | 3.1 | last meaningful line 1.0 h ago (204/212 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t46-204188 | ot_s81sl_leaf__t46 | 5_1_grt | 0.5 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t56-866545 | ot_s81sl_leaf__t56 | 5_1_grt | 2.8 | last meaningful line 0.3 h ago (209/216 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-phy__t1-2625032 | phy__t1 | 5_1_grt | 1.7 | last meaningful line 0.3 h ago (189/198 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (5096/5096 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-570014 | slice_station__t51 | generate_abstract | 10.6 | last meaningful line 0.1 h ago (308/308 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t6__cl0755c26e-2749197 | slice_station__t6 | 5_2_route | 1.6 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | pregrt_ff_hold | 3.5 | repair_TNS best 111790 last 111790 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | pregrt_ff_hold | 0.5 | repair_TNS best 56193.1 last 56193.1 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | pregrt_ff_hold | 3.5 | repair_TNS best 9370.06 last 9370.06 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slw_fw_v3-3096266 | slw_fw_v3 | 5_1_grt | 4.2 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | lrc-qgrt-12404 | lrc-qgrt | qgrt | 0.6 | last meaningful line 0.5 h ago (42/50 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | lrc-qgrt-3979888 | lrc-qgrt | qgrt | 0.7 | last meaningful line 0.5 h ago (44/51 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | otc-1108174-15457 | 1108174 | - | 2.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-1631796-31019 | 1631796 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-1661483-30301 | 1661483 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-1916796-12156 | 1916796 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-3850737-30319 | 3850737 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc9 | otc-652060-4614 | 652060 | signoff | 0.2 | last meaningful line 0.2 h ago (3/3 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-664483-8927 | 664483 | - | 2.9 |  | NO-DATA: no log found |  |
| epyc9 | otc-664799-872 | 664799 | - | 2.9 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261122_180231_342380-i2-1306615 | eco_20261122_180231_342380-i2 | 5_3_fillcell | 2.5 | last meaningful line -0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | so_223047_ff_71273 | so_223047_ff_71273 | generate_abstract | 0.5 | last meaningful line 0.3 h ago (532/532 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | so_223047_tt_71273 | so_223047_tt_71273 | generate_abstract | 0.5 | last meaningful line 0.3 h ago (532/532 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3534091 | col_h10_r2__t1 | 5_2_route | 6.3 | last meaningful line 0.3 h ago (264/265 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 20.0 | last meaningful line 0.5 h ago (284/285 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-3535177 | col_h9_r0_p5__t1 | 5_1_grt | 6.3 | last meaningful line 1.5 h ago (210/219 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvc1b82625-3531236 | col_h9_r0_p5__t1 | 5_1_grt | 6.3 | last meaningful line 1.0 h ago (210/219 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3522355 | col_h9_r2__t1 | 5_1_grt | 6.3 | grt_hold_TNS best 6961 last 6961 rows 2 | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvcf44b14c-1664216 | col_h9_r2__t1 | 5_2_route | 9.7 | drt_violations best 52013 last 52013 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | dpkit-hd_lep0N-1545648 | hd_lep0N | 4_2_tapbal_grt | 4.7 | last meaningful line 2.5 h ago (48/53 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_2_route | 18.2 | last meaningful line 0.5 h ago (281/282 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v7-3747893 | kv3_pv_v7 | 3_1_place_gp_skip_io | 3.3 | overflow best 0.9958 last 0.9958 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-serdes__t4-2914107 | serdes__t4 | 5_1_grt | 3.9 | last meaningful line 0.2 h ago (205/208 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | pregrt_ff_hold | 3.9 | repair_TNS best 15332.2 last 15332.2 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-sle_su_c-645555 | sle_su_c | 5_1_grt | 7.9 | last meaningful line 1.8 h ago (281/1291 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t28-3353995 | slice_station__t28 | 6_report | 6.4 | last meaningful line -0.0 h ago (7/7 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t52-3521993 | slice_station__t52 | 5_2_route | 6.3 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 6.4 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | otc-3831680-4014 | 3831680 | - | 0.2 |  | NO-DATA: no log found |  |
| intel1 | otc-589898-30912 | 589898 | - | 2.5 |  | NO-DATA: no log found |  |
| intel1 | otc-590329-1688 | 590329 | - | 2.5 |  | NO-DATA: no log found |  |
| intel1 | otc-591591-991 | 591591 | - | 2.5 |  | NO-DATA: no log found |  |
| intel1 | otc-910747-1220 | 910747 | - | 2.3 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 3.7 | last meaningful line 0.3 h ago (281/282 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i1-1606115 | eco_20261122_143408_943433-i1 | 5_2_route | 1.9 | last meaningful line 0.3 h ago (262/263 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i1-380897 | eco_20261122_165619_1517073-i1 | 5_2_route | 2.7 | last meaningful line 0.1 h ago (281/282 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | 5_2_route | 11.7 | drt_violations best 105374 last 105374 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel2 | dpkit-coll_core-3588522 | coll_core | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (6632/6632 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-495457 | coll_ftm | 5_2_route | 2.0 | drt_violations best 10172 last 10172 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-gunit__t1-2233417 | gunit__t1 | 3_5_place_dp | 1.0 | last meaningful line 0.5 h ago (39/39 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-3527760 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (214/215 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v5-3790571 | kv3_pv_v5 | 3_3_place_gp | 2.5 | overflow best 0.6156 last 0.6376 rows 15 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-sle_ctl__cla4f6f12f-2733138 | sle_ctl | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (8939/8940 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 13.7 | last meaningful line 0.5 h ago (282/283 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-2267874 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 2964 last 2964 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-slice_station__t24__cl66b71008-3595740 | slice_station__t24 | 3_3_place_gp | 0.2 | overflow best 0.6908 last 0.6908 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | so_3535964_ff_8248 | so_3535964_ff_8248 | signoff | 0.2 |  | NO-DATA: empty log |  |
| intel2 | so_3535964_tt_8248 | so_3535964_tt_8248 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc7 | otc-1111810-12159 | 1111810 | asbuilt.yosys | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | otc-1306192-4832 | 1306192 | asbuilt.yosys | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | otc-3834239-14188 | 3834239 | asbuilt.yosys | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_2_route | 16.9 | drt_violations best 1670 last 1670 rows 23 | before-window best 17830, window best 1670 | PROGRESS: drt_violations improved 90.6 % in window |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 16.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 16.9 | repair_Violations best 54 last 54 rows 14 | before-window best 24983, window best 54 | PROGRESS: repair_Violations improved 99.8 % in window |  |
| epyc2 | ap-ageom-kw-ot-s81sl-leaf--t30-grt-497915 | ot-s81sl-leaf--t30-grt | 3_5_place_dp | 0.0 | repair_Violations best 0 last 0 rows 16 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 69.7 | last meaningful line 0.1 h ago (1614/1614 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r1__t1__cld01bb4ae-1062709 | col_h10_r1__t1 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_hgi_v4-724077 | kv3_hgi_v4 | pregrt_ff_hold | 2.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_hgi_v5-1464049 | kv3_hgi_v5 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | tt_setup_repair_grt | 8.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | pregrt_ff_hold | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | pregrt_ff_hold | 6.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | prd-eco_20261122_220050_168828-i2t-1232517 | eco_20261122_220050_168828-i2t | 5_2_route | 3.5 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_2_route | 16.4 | drt_violations best 1 last 1 rows 51 | before-window best 110424, window best 1 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 16.9 | drt_violations best 95 last 95 rows 21 | before-window best 180834, window best 95 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 20.3 | drt_violations best 12904 last 12904 rows 15 | before-window best 15336, window best 12904 | PROGRESS: drt_violations improved 15.9 % in window |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2088472 | dsdv_slice_lepe_nh_mus_C__t1 | pregrt_ff_hold | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2093461 | col_h10_r1__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2103226 | col_h10_r2__t1 | 5_1_grt | 2.0 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | pregrt_ff_hold | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_hgi_v3-2875910 | kv3_hgi_v3 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_fw_v2__cl69f5e854-2970240 | sle_fw_v2 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-3009482 | slw_fe_v2 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | prd-eco-i1-454593 | eco-i1 | 5_1_grt | 0.3 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 12.3 | drt_violations best 20 last 54 rows 27 | before-window best 53, window best 20 | PROGRESS: drt_violations improved 62.3 % in window |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_2_route | 19.7 | drt_violations best 195281 last 195281 rows 1 | before-window best 195281, window best 195281 | PROGRESS: drt_violations: active iteration at 68650 < best completed total 195281 (in-iter |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 19.7 | drt_violations best 71586 last 71586 rows 2 | before-window best 210671, window best 71586 | PROGRESS: drt_violations improved 66.0 % in window |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2916065 | dsdv_slice_lepe_nh_mus_LP__t1 | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-glue-1559836 | glue | pregrt_ff_hold | 4.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | pregrt_ff_hold | 5.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-tt_ctlm-1686138 | tt_ctlm | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 27.2 | drt_violations best 1060 last 1060 rows 24 | before-window best 1202, window best 1060 | PROGRESS: drt_violations improved 11.8 % in window |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3384117 | col_h9_r1__t1 | 4_1_cts | 0.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | 5_1_grt | 15.9 | last meaningful line 5.3 h ago (211/220 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | 5_2_route | 13.8 | drt_violations best 46361 last 46361 rows 3 | before-window best 305042, window best 46361 | PROGRESS: drt_violations improved 84.8 % in window |  |
