# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 23:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'UNSIGNABLE': 1, 'GRT-LABEL': 20, 'NO-DATA': 49, 'YOUNG': 152, 'PROGRESS': 33}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 16.1 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 16.2 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | tt_setup_repair | 5.5 | repair_Violations best 40 last 40 rows 80 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -902.41 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 32.7 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel2 | dpkit-native59-3804419 | native59 | pregrt_ff_hold | 13.0 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-ot_s81sl_leaf__t15-1140501 | ot_s81sl_leaf__t15 | 5_1_grt | 6.2 | grt rounds 3 overflow 5:27473 -> 10:15254 -> 15:6617 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t21-1070163 | ot_s81sl_leaf__t21 | 5_1_grt | 6.3 | grt rounds 3 overflow 5:63924 -> 10:62220 -> 15:58764 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t27-1512680 | ot_s81sl_leaf__t27 | 5_1_grt | 6.1 | grt rounds 2 overflow 5:28580 -> 10:8107 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t67-3226431 | ot_s81sl_leaf__t67 | 5_1_grt | 5.2 | grt rounds 2 overflow 5:42145 -> 10:31930 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t25__cl55642d17-3247888 | ot_s81sl_leaf__t25 | 5_1_grt | 4.8 | grt rounds 2 overflow 5:32072 -> 10:20314 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_1_grt | 5.5 | grt rounds 2 overflow 5:18611 -> 10:8682 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-3655640 | ot_s81sl_leaf__t65 | 5_1_grt | 9.1 | grt rounds 3 overflow 5:40772 -> 10:33760 -> 15:28118 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t1-4049223 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 9.0 | grt rounds 2 overflow 5:1776 -> 10:344 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t3-56823 | ot_s81sl_leaf__t3 | 5_1_grt | 6.3 | grt rounds 2 overflow 5:1586 -> 10:260 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2000675 | col_h9_r0_p2__t1 | 5_1_grt | 5.6 | grt rounds 3 overflow 5:91555 -> 10:41 -> 15:14 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-2217964 | col_h9_r2__t1 | 5_1_grt | 5.5 | grt rounds 2 overflow 5:2844 -> 10:292 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t73-2566685 | ot_s81sl_leaf__t73 | 5_1_grt | 3.2 | grt rounds 2 overflow 5:42658 -> 10:22679 | GRT-LABEL: DESIGN-FAIL: overflow 22679 at round 10 > 1000 |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-3353467 | slw_st_a_v2 | 5_1_grt | 2.8 | grt rounds 2 overflow 5:6556 -> 10:1348 | GRT-LABEL: DESIGN-FAIL: overflow 1348 at round 10 > 1000 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 18.9 | grt rounds 6 overflow 5:1893 -> 10:1268 -> 15:872 -> 20:551 -> 25:191 -> 30:43 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-coll_core-180674 | coll_core | 5_1_grt | 17.3 | grt rounds 2 overflow 5:14446 -> 10:2584 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 18.9 | grt rounds 6 overflow 5:2533 -> 10:1498 -> 15:842 -> 20:584 -> 25:584 -> 30:139 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 18.9 | grt rounds 3 overflow 5:23666 -> 10:2753 -> 15:2123 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-3520587 | ot_s81sl_leaf__t53 | 5_1_grt | 5.5 | grt rounds 2 overflow 5:29437 -> 10:25353 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-serdes__t1__clb45db5be-633399 | serdes__t1 | 5_1_grt | 7.1 | grt rounds 1 overflow 5:291 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 15.1 | grt rounds 2 overflow 5:88896 -> 10:83085 | GRT-LABEL: DESIGN-FAIL: overflow 83085 at round 10 > 1000 |  |
| epyc10 | ap-ageom-kw-ot-s81sl-leaf--t11-grt-2646329 | ot-s81sl-leaf--t11-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-2664155 | col_h9_r0_p5__t1 | 5_1_grt | 2.9 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t3-886705 | dsdv_slice_c1x_C__t3 | 5_1_grt | 6.4 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_mu_LP__t2-1472079 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 6.1 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_LP__t2-2617721 | dsdv_slice_lepw_mus_LP__t2 | 5_1_grt | 5.5 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-native59-2585588 | native59 | 5_1_grt | 2.9 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | port_bind | 17.5 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2569171 | sle_hc1 | 5_1_grt | 2.9 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v2__cl7b3062fa-3029892 | sle_stm_v2 | 5_2_route | 7.8 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | otc-1668180-3684 | 1668180 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 2.8 | last meaningful line 0.2 h ago (288/289 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i1-42727 | eco_20261122_223531_3628570-i1 | 5_2_route | 4.6 | drt_violations best 649 last 649 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_040953_1214866-i1-1617727 | eco_20261123_040953_1214866-i1 | 5_2_route | 3.5 | drt_violations best 178 last 178 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | so_2563286_ff_95668 | so_2563286_ff_95668 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc10 | so_2563286_tt_95668 | so_2563286_tt_95668 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc10 | so_2737382_ff_93478 | so_2737382_ff_93478 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc10 | so_2737382_tt_93478 | so_2737382_tt_93478 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | ap-ageom-kw-col-h10-r0-p1--t1--cl574cc59d--pv67036687-grt-3228793 | col-h10-r0-p1--t1--cl574cc59d--pv67036687-grt | 3_5_place_dp | 0.2 | last meaningful line 0.2 h ago (140/140 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-ot-s81sl-leaf--t41-grt-3289598 | ot-s81sl-leaf--t41-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-1815940 | col_h10_r0_p1__t1 | 5_1_grt | 5.5 | last meaningful line 0.3 h ago (211/214 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cld01bb4ae-1062709 | col_h10_r1__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 28541.7 last 28541.7 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-1483343 | col_h9_r0_p4__t1 | pregrt_ff_hold | 1.1 | repair_TNS best 94532.8 last 94532.8 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-2470572 | col_h9_r1__t1 | 5_1_grt | 5.3 | repair_Viol best 426 last 426 rows 2 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2108278 | dsdv_slice_c1x_C__t1 | 5_1_grt | 7.8 | last meaningful line 2.0 h ago (208/211 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2115818 | dsdv_slice_c1x_C__t10 | 5_1_grt | 7.8 | last meaningful line 1.8 h ago (211/217 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t8-1544833 | dsdv_slice_c1x_C__t8 | selrange | 1.1 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-dsdv_slice_lepe_mu_C__t1-3116985 | dsdv_slice_lepe_mu_C__t1 | 5_1_grt | 4.9 | last meaningful line 0.1 h ago (157/157 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1565179 | dsdv_slice_lepe_nh_mus_C__t1 | selrange | 1.1 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 4.4 | repair_TNS best 988470 last 988470 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-hd_lep0N_w-3963146 | hd_lep0N_w | pregrt_ff_hold | 4.3 | repair_TNS best 1.78947e+06 last 1.78947e+06 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1p2-1100885 | kv3_hg_v1p2 | 3_3_place_gp | 1.3 | overflow best 0.2245 last 0.2245 rows 36 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-kv3_hgi_v4-724077 | kv3_hgi_v4 | pregrt_ff_hold | 1.5 | repair_TNS best 74840.7 last 74840.7 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-kv3_hgi_v5-1464049 | kv3_hgi_v5 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (5821/5821 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_io_cor_v1-3748922 | kv3_io_cor_v1 | 5_2_route | 4.5 | drt_violations best 60486 last 60486 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v3n-1352817 | kv3_pv_v3n | 2_1_floorplan | 1.2 | last meaningful line 0.3 h ago (1553/1553 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4n-420301 | kv3_pv_v4n | 2_4_floorplan_pdn | 1.7 | last meaningful line 0.1 h ago (92/92 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t1-1193270 | ot_s81sl_leaf__t1 | 3_5_place_dp | 1.3 | last meaningful line 0.0 h ago (104/104 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t43-562324 | ot_s81sl_leaf__t43 | 5_1_grt | 3.9 | last meaningful line 1.3 h ago (205/213 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-775509 | sle_ctl | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (9056/9056 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | tt_setup_repair_grt | 7.8 | repair_Viol best 46 last 46 rows 17 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | 5_1_grt | 7.8 | last meaningful line 0.2 h ago (138/138 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | 5_1_grt | 7.8 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | 5_1_grt | 7.8 | last meaningful line 0.1 h ago (1155/1162 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 7.8 | drt_violations best 35724 last 35724 rows 3 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 4.4 | last meaningful line 0.1 h ago (258/259 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 4.8 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | otc-2114902-19881 | 2114902 | - | 3.0 |  | NO-DATA: no log found |  |
| epyc2 | otc-2186430-24000 | 2186430 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc2 | otc-271425-6325 | 271425 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc2 | otc-3516090-17893 | 3516090 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | otc-3531681-14090 | 3531681 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc2 | otc-3553860-12060 | 3553860 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc2 | otc-3704474-1214 | 3704474 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261122_164248_3895049-i1-2533130 | eco_20261122_164248_3895049-i1 | 5_1_grt | 0.6 | last meaningful line 0.1 h ago (146/146 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164521_3948325-i1-2180646 | eco_20261122_164521_3948325-i1 | 5_1_grt | 0.8 | last meaningful line 0.1 h ago (237/269 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i1t-1909174 | eco_20261122_181101_3945375-i1t | 5_2_route | 5.5 | drt_violations best 9568 last 9568 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i1t-3508652 | eco_20261122_190506_3875261-i1t | 5_2_route | 4.6 | drt_violations best 25875 last 25875 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | prd-fin-1443078 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | vis-head-3176835 | vis-head | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | vis-head-3276080 | vis-head | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-4118481 | col_h10_r0_p4__t1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.1994 last 0.1994 rows 36 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t9-4069286 | dsdv_slice_c1x_C__t9 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3565523 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-hd_ctl-1922947 | hd_ctl | 5_2_route | 5.3 | drt_violations best 53701 last 53701 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t22-4105867 | ot_s81sl_leaf__t22 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3924/3924 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1181364 | ot_s81sl_leaf__t39 | 5_1_grt | 5.6 | last meaningful line 0.5 h ago (264/1276 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | postcts_gate_TT | 9.5 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-1530301 | sle_hc0 | 5_2_route | 5.5 | drt_violations best 99839 last 99839 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | postcts_gate_FF | 10.5 | last meaningful line -0.0 h ago (4907/4907 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-881903 | sle_stm_v1 | 5_2_route | 10.5 | drt_violations best 194338 last 194338 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t18-1919126 | slice_station__t18 | 6_report | 5.3 | last meaningful line 0.0 h ago (213/213 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t40__cl1ea9de02-1928775 | slice_station__t40 | 5_2_route | 5.3 | drt_violations best 21015 last 21015 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t6__cl54a9ceeb-1772119 | slice_station__t6 | 6_report | 5.4 | last meaningful line 0.0 h ago (237/237 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 10.4 | last meaningful line 0.3 h ago (133/133 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl9beb65e6-3994155 | slw_stm_v2 | 5_2_route | 9.0 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 5.4 | drt_violations best 311954 last 311954 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | otc-254531-30458 | 254531 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | otc-2707491-20991 | 2707491 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc7 | otc-2974334-11732 | 2974334 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc7 | otc-3346487-26799 | 3346487 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc7 | otc-3562518-20801 | 3562518 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc7 | otc-3815737-1746 | 3815737 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc7 | otc-3970901-4095 | 3970901 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261122_215654_330309-i2t-1668391 | eco_20261122_215654_330309-i2t | 5_2_route | 2.4 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_220050_168828-i2t-1232517 | eco_20261122_220050_168828-i2t | 5_2_route | 2.7 | drt_violations best 21782 last 21782 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | so_191173_ff_98643 | so_191173_ff_98643 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc7 | so_191173_tt_98643 | so_191173_tt_98643 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc8 | ap-ageom-kw-ot-s81sl-kv-leaf--t3-grt-1816728 | ot-s81sl-kv-leaf--t3-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-ot-s81sl-leaf--t14-grt-1817533 | ot-s81sl-leaf--t14-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1919292 | col_h9_r0_p2__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2875/2875 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t8-1783469 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-1930297 | dsdv_slice_kv512_C__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2088472 | dsdv_slice_lepe_nh_mus_C__t1 | pregrt_ff_hold | 5.6 | repair_TNS best 80460.1 last 80460.1 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-glue-555250 | glue | postcts_gate_TT | 8.0 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg-3089265 | kv3_hg | 3_4_place_resized | 1.4 | last meaningful line 0.1 h ago (343/343 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p6-2039106 | kv3_hg_v1p6 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hgi_v4-2007136 | kv3_hgi_v4 | stage_odb_guard | 0.0 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 7.0 | drt_violations best 26167 last 26167 rows 9 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 3.0 | last meaningful line 2.2 h ago (11728/11728 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-494270 | kv3_hub_Ei | 5_2_route | 8.1 | last meaningful line 0.1 h ago (281/282 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-619668 | kv3_io_cor_v1 | postcts_gate_TT | 2.3 | last meaningful line -0.0 h ago (234/234 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v12-2115834 | kv3_pv_v12 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-164511 | kv3_pv_v6 | 3_3_place_gp | 2.5 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t32-1902400 | ot_s81sl_leaf__t32 | 4_1_cts | 0.1 | last meaningful line 0.1 h ago (53/53 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t36-1897305 | ot_s81sl_leaf__t36 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t61-1869131 | ot_s81sl_leaf__t61 | tt_setup_measure | 0.1 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-2055827 | sle_st_a_v2 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-2008589 | sle_su_l1 | lec | 0.0 | LEC last write -0.0 h ago | YOUNG: evidence 0.0 h < 6 h |  |
| epyc8 | otc-1173846-21068 | 1173846 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-1174520-11483 | 1174520 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-1747196-2419 | 1747196 | lec | 0.2 | LEC last write 0.2 h ago | YOUNG: evidence 0.2 h < 6 h |  |
| epyc8 | otc-1910005-4834 | 1910005 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-2063990-12280 | 2063990 | lec | 0.0 | LEC last write 0.0 h ago | YOUNG: evidence 0.0 h < 6 h |  |
| epyc8 | otc-2150702-32101 | 2150702 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (8/8 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-2152170-30308 | 2152170 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (5/5 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-2593908-9338 | 2593908 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t17-grt-3868351 | ot-s81sl-leaf--t17-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl911743eb-4131559 | col_h10_r0_p1__t1 | 5_1_grt | 2.7 | last meaningful line 0.1 h ago (160/160 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2109433 | col_h10_r0_p4__t1 | pregrt_ff_hold | 1.2 | repair_TNS best 56684.3 last 56684.3 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2093461 | col_h10_r1__t1 | pregrt_ff_hold | 1.2 | repair_TNS best 28473.2 last 28473.2 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-4076788 | col_h10_r1__t1 | 5_1_grt | 2.8 | last meaningful line 0.0 h ago (210/211 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2103226 | col_h10_r2__t1 | 5_1_grt | 1.2 | repair_Remaining best 60835 last 60835 rows 48 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2653831 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.9 | overflow best 0.5059 last 0.5123 rows 8 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_1_grt | 3.7 | last meaningful line 0.0 h ago (190/190 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv40e9fb5a-287653 | col_h9_r2__t1 | 5_2_route | 5.6 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t10-4186865 | dsdv_slice_c1x_C__t10 | selrange | 2.7 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t7-2862427 | dsdv_slice_c1x_C__t7 | sdc_lint | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_kv512_C__t1-288662 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 5.6 | last meaningful line 3.0 h ago (37/37 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-3178195 | hd_ctl | tt_setup_repair | 0.6 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hgi_v3-2875910 | kv3_hgi_v3 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (5910/5910 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hroot-2456475 | kv3_hroot | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hroot-2622210 | kv3_hroot | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (3709/3709 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v2n-2681030 | kv3_pv_v2n | 2_1_floorplan | 0.9 | last meaningful line 0.5 h ago (389/389 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v4-2911509 | kv3_pv_v4 | 2_1_floorplan | 0.7 | last meaningful line 0.3 h ago (397/397 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v6n-2406851 | kv3_pv_v6n | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (7828/7828 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v8-3739898 | kv3_pv_v8 | 3_5_place_dp | 3.0 | last meaningful line 0.1 h ago (136/136 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-1792430 | ot_s81sl_kv_leaf__t5 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (89/89 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t33-2546296 | ot_s81sl_leaf__t33 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-461535 | ot_s81sl_leaf__t44 | 5_1_grt | 2.3 | last meaningful line 0.3 h ago (204/207 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t56-866545 | ot_s81sl_leaf__t56 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-phy__t1-2625032 | phy__t1 | 5_1_grt | 0.9 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (5039/5039 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | pregrt_ff_hold | 3.6 | repair_TNS best 148202 last 148202 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-slice_station__t22-239981 | slice_station__t22 | 6_report | 5.6 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-570014 | slice_station__t51 | 5_3_fillcell | 9.8 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | pregrt_ff_hold | 2.8 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-3009482 | slw_fe_v2 | pregrt_ff_hold | 3.5 | repair_TNS best 158126 last 158126 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | 4_1_cts | 2.7 | last meaningful line 0.1 h ago (5237/5237 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | pregrt_ff_hold | 3.5 | repair_TNS best 226962 last 226962 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | eco-abs-2785968 | eco-abs | generate_abstract | 0.8 | last meaningful line 0.2 h ago (528/528 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | otc-1108174-15457 | 1108174 | - | 1.9 |  | NO-DATA: no log found |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc9 | otc-1631796-31019 | 1631796 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc9 | otc-1661483-30301 | 1661483 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc9 | otc-1916796-12156 | 1916796 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc9 | otc-3850737-30319 | 3850737 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-664483-8927 | 664483 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-664799-872 | 664799 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-682537-13250 | 682537 | - | 5.4 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261122_180231_342380-i2-1306615 | eco_20261122_180231_342380-i2 | 5_2_route | 1.7 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | prd-fin-3504713 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-3359910 | col_h10_r0_p4__t1 | 5_1_grt | 5.6 | last meaningful line 0.1 h ago (208/211 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3365642 | col_h10_r1__t1 | 5_1_grt | 5.6 | last meaningful line 0.8 h ago (203/212 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3534091 | col_h10_r2__t1 | postcts_gate_TT | 5.5 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 19.2 | last meaningful line 0.5 h ago (280/281 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-3535177 | col_h9_r0_p5__t1 | 5_1_grt | 5.5 | last meaningful line 0.8 h ago (210/216 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvc1b82625-3531236 | col_h9_r0_p5__t1 | 5_1_grt | 5.5 | last meaningful line 0.3 h ago (210/213 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3522355 | col_h9_r2__t1 | 5_1_grt | 5.5 | repair_TNS best 6580.79 last 6580.79 rows 2 | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvcf44b14c-1664216 | col_h9_r2__t1 | 5_2_route | 8.9 | drt_violations best 52013 last 52013 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-3365034 | dsdv_slice_c1x_C__t3 | 3_5_place_dp | 5.6 | last meaningful line 0.2 h ago (37/37 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-hd_lep0N-1545648 | hd_lep0N | 4_2_tapbal_grt | 3.9 | last meaningful line 1.8 h ago (48/51 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_2_route | 17.5 | last meaningful line 0.7 h ago (277/278 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v7-3747893 | kv3_pv_v7 | 2_1_floorplan | 2.5 | last meaningful line 1.5 h ago (1547/1547 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 19.0 | last meaningful line 0.3 h ago (264/352 lines) | YOUNG: evidence 5.5 h < 6 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-3536309 | ot_s81sl_leaf__t2 | 5_1_grt | 5.5 | last meaningful line 2.3 h ago (207/216 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t71-2773215 | ot_s81sl_leaf__t71 | 5_1_grt | 3.2 | last meaningful line 1.3 h ago (210/219 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-serdes__t4-2914107 | serdes__t4 | 5_1_grt | 3.1 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | 4_1_cts | 3.1 | last meaningful line 0.0 h ago (5358/5358 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-sle_su_c-645555 | sle_su_c | 5_1_grt | 7.1 | last meaningful line 1.0 h ago (281/1289 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t28-3353995 | slice_station__t28 | 5_2_route | 5.6 | drt_violations best 13901 last 13901 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t52-3521993 | slice_station__t52 | postcts_gate_TT | 5.5 | last meaningful line 0.0 h ago (1330/1330 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 5.6 | last meaningful line 0.2 h ago (263/264 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | otc-589898-30912 | 589898 | - | 1.8 |  | NO-DATA: no log found |  |
| intel1 | otc-590329-1688 | 590329 | - | 1.8 |  | NO-DATA: no log found |  |
| intel1 | otc-591591-991 | 591591 | - | 1.8 |  | NO-DATA: no log found |  |
| intel1 | otc-910747-1220 | 910747 | - | 1.6 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 2.9 | last meaningful line 0.1 h ago (152/152 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i1-1606115 | eco_20261122_143408_943433-i1 | 5_2_route | 1.1 | last meaningful line 0.1 h ago (257/257 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i1-380897 | eco_20261122_165619_1517073-i1 | 5_2_route | 1.9 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | 5_2_route | 11.0 | last meaningful line 0.3 h ago (286/287 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2864182 | coll_ftm | 5_2_route | 2.4 | drt_violations best 10172 last 10172 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-495457 | coll_ftm | 5_2_route | 1.2 | last meaningful line 0.1 h ago (227/228 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | 5_1_grt | 15.1 | last meaningful line 4.5 h ago (211/219 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel2 | dpkit-gunit__t1-2233417 | gunit__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.5427 last 0.5427 rows 25 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-2230183 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (208/209 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-483181 | kv3_io_ft | 5_2_route | 1.2 | drt_violations best 5487 last 5487 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-kv3_pv_v5-3790571 | kv3_pv_v5 | 2_4_floorplan_pdn | 1.8 | last meaningful line 0.1 h ago (96/96 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 13.0 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl55be2264-3685080 | sle_stm_v2 | 6_report | 13.1 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | 5_2_route | 13.1 | drt_violations best 66861 last 66861 rows 2 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_2_route | 16.2 | drt_violations best 1721 last 1721 rows 19 | before-window best 29667, window best 1721 | PROGRESS: drt_violations improved 94.2 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 69.0 | last meaningful line 0.9 h ago (1612/1612 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-1820678 | col_h10_r0_p1__t1 | pregrt_ff_hold | 5.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_1_grt | 1.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | pregrt_ff_hold | 5.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | pregrt_ff_hold | 5.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | prd-eco_20261122_123708_2624415-i1t-3236939 | eco_20261122_123708_2624415-i1t | 5_2_route | 11.1 | drt_violations best 1 last 1 rows 55 | before-window best 362, window best 1 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_2_route | 15.6 | drt_violations best 2 last 2 rows 35 | before-window best 110424, window best 2 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-2034515 | col_h10_r1__t1 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 16.1 | drt_violations best 234 last 315 rows 18 | before-window best 180834, window best 234 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 19.5 | drt_violations best 13260 last 13260 rows 14 | before-window best 16565, window best 13260 | PROGRESS: drt_violations improved 20.0 % in window |  |
| epyc8 | dpkit-kv3_hgi_v2__cle0015330-3274473 | kv3_hgi_v2 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hgi_v2__cle0015330-3323577 | kv3_hgi_v2 | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-ot_s81sl_leaf__t23-1888361 | ot_s81sl_leaf__t23 | tt_setup_repair | 0.1 | repair_Violations best 0 last 0 rows 15 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-1144307 | serdes__t1 | 4_1_cts | 0.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_2_route | 19.1 | drt_violations best 24 last 24 rows 53 | before-window best 178849, window best 24 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | pregrt_ff_hold | 5.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_hgi_v1__cl42bc8b12-2545242 | kv3_hgi_v1 | pregrt_ff_hold | 0.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_fw_v2__cl69f5e854-2970240 | sle_fw_v2 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slice_station__t6__cl0755c26e-2749197 | slice_station__t6 | 5_1_grt | 0.8 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fw_v3-3096266 | slw_fw_v3 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 11.5 | drt_violations best 20 last 101 rows 25 | before-window best 71, window best 20 | PROGRESS: drt_violations improved 71.8 % in window |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_2_route | 19.0 | drt_violations best 195281 last 195281 rows 1 | before-window best 195281, window best 195281 | PROGRESS: drt_violations: active iteration at 87069 < best completed total 195281 (in-iter |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 19.0 | drt_violations best 210671 last 210671 rows 1 | before-window best 210671, window best 210671 | PROGRESS: drt_violations: active iteration at 83161 < best completed total 210671 (in-iter |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2916065 | dsdv_slice_lepe_nh_mus_LP__t1 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-glue-1559836 | glue | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-tt_ctlm-1686138 | tt_ctlm | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 26.4 | drt_violations best 1064 last 1064 rows 23 | before-window best 1452, window best 1064 | PROGRESS: drt_violations improved 26.7 % in window |  |
| intel2 | dpkit-hd_turn_a-2243143 | hd_turn_a | 5_1_grt | 0.2 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slice_station__t12-2267874 | slice_station__t12 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
