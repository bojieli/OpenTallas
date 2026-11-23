# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 23:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 3, 'GRT-LABEL': 23, 'YOUNG': 159, 'NO-DATA': 39, 'EXCLUDED': 1, 'PROGRESS': 41}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-dsdv_slice_c1x_C__t3-886705 | dsdv_slice_c1x_C__t3 | tt_setup_repair | 5.9 | repair_Violations best 35463 last 35463 rows 7 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -748.83 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | pregrt_ff_hold | 15.6 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | pregrt_ff_hold | 15.7 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 32.2 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel1 | dpkit-dsdv_slice_lepw_mu_LP__t2-1012815 | dsdv_slice_lepw_mu_LP__t2 | tt_setup_repair_grt | 18.5 | last meaningful line 0.0 h ago (21/21 lines) | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -711.57 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-ot_s81sl_leaf__t15-1140501 | ot_s81sl_leaf__t15 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:27473 -> 10:15254 -> 15:6617 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t21-1070163 | ot_s81sl_leaf__t21 | 5_1_grt | 5.8 | grt rounds 3 overflow 5:63924 -> 10:62220 -> 15:58764 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t27-1512680 | ot_s81sl_leaf__t27 | 5_1_grt | 5.6 | grt rounds 2 overflow 5:28580 -> 10:8107 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t28-1070507 | ot_s81sl_leaf__t28 | 5_1_grt | 5.8 | grt rounds 2 overflow 5:88987 -> 10:67649 | GRT-LABEL: DESIGN-FAIL: overflow 67649 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t25__cl55642d17-3247888 | ot_s81sl_leaf__t25 | 5_1_grt | 4.3 | grt rounds 2 overflow 5:32072 -> 10:20314 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_1_grt | 5.0 | grt rounds 2 overflow 5:18611 -> 10:8682 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t62-1866677 | ot_s81sl_leaf__t62 | 5_1_grt | 5.0 | grt rounds 2 overflow 5:52232 -> 10:24586 | GRT-LABEL: DESIGN-FAIL: overflow 24586 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-3655640 | ot_s81sl_leaf__t65 | 5_1_grt | 8.6 | grt rounds 3 overflow 5:40772 -> 10:33760 -> 15:28118 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t1-4049223 | ot_s81sl_kv_leaf__t1 | 5_1_grt | 8.5 | grt rounds 2 overflow 5:1776 -> 10:344 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2000675 | col_h9_r0_p2__t1 | 5_1_grt | 5.1 | grt rounds 3 overflow 5:91555 -> 10:41 -> 15:14 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-2217964 | col_h9_r2__t1 | 5_1_grt | 5.0 | grt rounds 2 overflow 5:2844 -> 10:292 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-dsdv_slice_lepw_mu_LP__t2-2830715 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 6.5 | grt rounds 2 overflow 5:99 -> 10:39 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-1804559 | slw_st_a_v2 | 5_1_grt | 3.0 | grt rounds 2 overflow 5:6556 -> 10:1348 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-3353467 | slw_st_a_v2 | 5_1_grt | 2.3 | grt rounds 2 overflow 5:6556 -> 10:1348 | GRT-LABEL: DESIGN-FAIL: overflow 1348 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-238701 | col_h9_r0_p5__t1 | 5_1_grt | 5.1 | grt rounds 2 overflow 5:61125 -> 10:4177 | GRT-LABEL: DESIGN-FAIL: overflow 4177 at round 10 > 1000 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | 5_1_grt | 18.4 | grt rounds 6 overflow 5:1893 -> 10:1268 -> 15:872 -> 20:551 -> 25:191 -> 30:43 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3534091 | col_h10_r2__t1 | 5_1_grt | 5.0 | grt rounds 2 overflow 5:9856 -> 10:274 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-coll_core-180674 | coll_core | 5_1_grt | 16.8 | grt rounds 2 overflow 5:14446 -> 10:2584 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 18.4 | grt rounds 6 overflow 5:2533 -> 10:1498 -> 15:842 -> 20:584 -> 25:584 -> 30:139 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t33-1091917 | ot_s81sl_leaf__t33 | 5_1_grt | 18.4 | grt rounds 3 overflow 5:23666 -> 10:2753 -> 15:2123 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-3520587 | ot_s81sl_leaf__t53 | 5_1_grt | 5.0 | grt rounds 2 overflow 5:29437 -> 10:25353 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-serdes__t1__clb45db5be-633399 | serdes__t1 | 5_1_grt | 6.6 | grt rounds 1 overflow 5:291 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 14.6 | grt rounds 2 overflow 5:88896 -> 10:83085 | GRT-LABEL: DESIGN-FAIL: overflow 83085 at round 10 > 1000 |  |
| epyc10 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2379537 | col_h10_r0_p4__t1 | 5_1_grt | 2.5 | last meaningful line 0.0 h ago (154/154 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-3347917 | col_h10_r0_p4__t1 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (154/154 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-2664155 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.4 | repair_TNS best 131142 last 131142 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_mu_LP__t2-1472079 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 5.6 | repair_Violations best 1140 last 1146 rows 64 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc10 | dpkit-iqf__t1-13421 | iqf__t1 | 6_report | 6.5 | last meaningful line 0.1 h ago (408/408 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_C-3334849 | kv3_hub_C | 2_1_floorplan | 1.9 | last meaningful line 1.3 h ago (1424/1424 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-native59-2585588 | native59 | pregrt_ff_hold | 2.4 | repair_TNS best 12876.5 last 12876.5 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 1_synth | 17.0 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t23-2663094 | ot_s81sl_leaf__t23 | 5_1_grt | 2.4 | last meaningful line 0.3 h ago (213/218 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t29-2063028 | ot_s81sl_leaf__t29 | 5_1_grt | 2.7 | last meaningful line 1.0 h ago (210/219 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t46-2731436 | ot_s81sl_leaf__t46 | 5_1_grt | 2.3 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t61-2696700 | ot_s81sl_leaf__t61 | 5_1_grt | 2.3 | last meaningful line 0.3 h ago (210/214 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t67-3226431 | ot_s81sl_leaf__t67 | 5_1_grt | 4.7 | last meaningful line 1.8 h ago (213/222 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2569171 | sle_hc1 | 4_1_cts | 2.4 | last meaningful line 0.1 h ago (5345/5345 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v2__cl7b3062fa-3029892 | sle_stm_v2 | 5_2_route | 7.3 | last meaningful line 0.3 h ago (266/267 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t25-3118247 | slice_station__t25 | generate_abstract | 7.3 | last meaningful line 0.0 h ago (262/262 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2619979 | slw_fe_v1 | 4_1_cts | 2.4 | last meaningful line 0.3 h ago (5883/5883 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | otc-1668180-3684 | 1668180 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc10 | otc-1668723-5553 | 1668723 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc10 | otc-1675861-16997 | 1675861 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc10 | otc-1677398-28960 | 1677398 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 2.3 | last meaningful line 0.1 h ago (284/285 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i1-42727 | eco_20261122_223531_3628570-i1 | 5_2_route | 4.1 | drt_violations best 649 last 649 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_040953_1214866-i1-1617727 | eco_20261123_040953_1214866-i1 | 5_2_route | 3.0 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-serdes--t1--clfe1f0815-grt-2456652 | serdes--t1--clfe1f0815-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-1820678 | col_h10_r0_p1__t1 | pregrt_ff_hold | 5.0 | repair_TNS best 14583 last 14583 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-1573253 | col_h10_r0_p1__t1 | 3_3_place_gp | 0.6 | overflow best 0.3938 last 0.3938 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-1815940 | col_h10_r0_p1__t1 | 5_1_grt | 5.0 | last meaningful line 0.0 h ago (161/161 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cld01bb4ae-1062709 | col_h10_r1__t1 | pregrt_ff_hold | 0.8 | repair_TNS best 28541.7 last 28541.7 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-1483343 | col_h9_r0_p4__t1 | pregrt_ff_hold | 0.6 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2108278 | dsdv_slice_c1x_C__t1 | 5_1_grt | 7.3 | last meaningful line 1.5 h ago (208/211 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2115818 | dsdv_slice_c1x_C__t10 | 5_1_grt | 7.3 | last meaningful line 1.3 h ago (211/216 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t8-1544833 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_mu_C__t1-3116985 | dsdv_slice_lepe_mu_C__t1 | pregrt_ff_hold | 4.4 | last meaningful line 0.0 h ago (1451/1451 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1565179 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | tt_setup_repair | 5.0 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | tt_setup_measure | 3.9 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-hd_lep0N_w-3963146 | hd_lep0N_w | pregrt_ff_hold | 3.8 | repair_TNS best 1.78947e+06 last 1.78947e+06 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1p2-1100885 | kv3_hg_v1p2 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.5428 last 0.5428 rows 30 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-kv3_hgi_v4-724077 | kv3_hgi_v4 | tt_setup_measure | 1.0 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v5-1464049 | kv3_hgi_v5 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (5575/5575 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_io_cor_v1-3748922 | kv3_io_cor_v1 | 5_2_route | 4.0 | last meaningful line 0.1 h ago (260/261 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v3n-1352817 | kv3_pv_v3n | 2_1_floorplan | 0.7 | repair_Viol best 1314 last 1314 rows 1216 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-kv3_pv_v4n-420301 | kv3_pv_v4n | 2_1_floorplan | 1.2 | last meaningful line 0.7 h ago (396/396 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t1-1193270 | ot_s81sl_leaf__t1 | 3_3_place_gp | 0.8 | overflow best 0.6406 last 0.6406 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t41-1654868 | ot_s81sl_leaf__t41 | 3_3_place_gp | 0.6 | last meaningful line 0.2 h ago (181/181 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t43-562324 | ot_s81sl_leaf__t43 | 5_1_grt | 3.4 | last meaningful line 0.8 h ago (205/211 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t66-552390 | ot_s81sl_leaf__t66 | 5_1_grt | 3.4 | last meaningful line 1.0 h ago (207/216 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t7-1385962 | ot_s81sl_leaf__t7 | 3_3_place_gp | 0.7 | overflow best 0.4413 last 0.4565 rows 29 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-775509 | sle_ctl | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (9028/9028 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | 5_1_grt | 7.3 | last meaningful line 0.2 h ago (1211/1282 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t29__clc7772371-2336581 | slice_station__t29 | 6_report | 4.9 | last meaningful line 0.0 h ago (189/189 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 7.3 | drt_violations best 35724 last 35724 rows 3 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | postcts_gate_FF | 3.9 | last meaningful line 0.0 h ago (971/971 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 4.3 | last meaningful line 0.1 h ago (262/263 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-tt_ctlm-2035057 | tt_ctlm | tt_setup_repair_grt | 7.3 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-2114902-19881 | 2114902 | - | 2.5 |  | NO-DATA: no log found |  |
| epyc2 | otc-2186430-24000 | 2186430 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc2 | otc-271425-6325 | 271425 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc2 | otc-3531681-14090 | 3531681 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc2 | otc-3553860-12060 | 3553860 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc2 | otc-3704474-1214 | 3704474 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261122_164248_3895049-i1-2533130 | eco_20261122_164248_3895049-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164521_3948325-i1-2180646 | eco_20261122_164521_3948325-i1 | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_180145_3931237-i1-1443078 | eco_20261122_180145_3931237-i1 | 5_2_route | 5.2 | drt_violations best 423 last 423 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i1t-1909174 | eco_20261122_181101_3945375-i1t | 5_2_route | 5.0 | drt_violations best 9568 last 9568 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i1t-3508652 | eco_20261122_190506_3875261-i1t | 5_2_route | 4.1 | drt_violations best 25875 last 25875 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | vis-head-2525547 | vis-head | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3816468 | col_h9_r1__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3565523 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-hd_ctl-1922947 | hd_ctl | 5_2_route | 4.8 | last meaningful line 0.1 h ago (258/259 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t3-56823 | ot_s81sl_leaf__t3 | 5_1_grt | 5.8 | last meaningful line 1.0 h ago (211/220 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1181364 | ot_s81sl_leaf__t39 | 5_1_grt | 5.1 | last meaningful line 0.1 h ago (156/156 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-718661 | serdes__t13 | 6_report | 18.4 | last meaningful line 0.0 h ago (455/455 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | 5_1_grt | 9.0 | last meaningful line 0.1 h ago (1178/1212 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-1530301 | sle_hc0 | 5_2_route | 5.0 | drt_violations best 99839 last 99839 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | postcts_gate_FF | 10.0 | last meaningful line 0.0 h ago (727/727 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-881903 | sle_stm_v1 | 5_2_route | 10.0 | drt_violations best 194338 last 194338 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t18-1919126 | slice_station__t18 | 5_2_route | 4.8 | drt_violations best 2362 last 2362 rows 3 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t40__cl1ea9de02-1928775 | slice_station__t40 | 5_2_route | 4.8 | drt_violations best 21015 last 21015 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t6__cl54a9ceeb-1772119 | slice_station__t6 | 5_2_route | 4.9 | drt_violations best 1541 last 1541 rows 2 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | postcts_gate_FF | 9.9 | last meaningful line -0.0 h ago (70082/70082 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl9beb65e6-3994155 | slw_stm_v2 | postcts_gate_FF | 8.5 | last meaningful line 0.1 h ago (1514/1514 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 4.9 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | otc-2707491-20991 | 2707491 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc7 | otc-2974334-11732 | 2974334 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc7 | otc-3346487-26799 | 3346487 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc7 | otc-3562518-20801 | 3562518 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc7 | otc-3814881-8013 | 3814881 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | otc-3815737-1746 | 3815737 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | otc-3816790-24593 | 3816790 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | otc-3970901-4095 | 3970901 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261122_215654_330309-i2t-1668391 | eco_20261122_215654_330309-i2t | 5_2_route | 1.9 | last meaningful line 0.1 h ago (260/261 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_220050_168828-i2t-1232517 | eco_20261122_220050_168828-i2t | 5_2_route | 2.2 | drt_violations best 21782 last 21782 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-2034515 | col_h10_r1__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 32760.6 last 32760.6 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 15.6 | drt_violations best 315 last 315 rows 15 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2088472 | dsdv_slice_lepe_nh_mus_C__t1 | tt_setup_repair | 5.1 | repair_Viol best 2198 last 2198 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-glue-555250 | glue | tt_setup_repair_grt | 7.5 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg-3089265 | kv3_hg | 3_1_place_gp_skip_io | 0.9 | overflow best 0.1452 last 0.1452 rows 41 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 6.5 | drt_violations best 26889 last 26889 rows 8 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 2.5 | last meaningful line 1.8 h ago (11728/11728 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-494270 | kv3_hub_Ei | 5_2_route | 7.6 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-164511 | kv3_pv_v6 | 2_4_floorplan_pdn | 2.0 | last meaningful line 0.1 h ago (91/91 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t3-701590 | ot_s81sl_kv_leaf__t3 | 3_5_place_dp | 1.8 | last meaningful line 0.0 h ago (89/89 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t13-2561906 | ot_s81sl_leaf__t13 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t14-2612009 | ot_s81sl_leaf__t14 | 3_4_place_resized | 1.1 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t73-2566685 | ot_s81sl_leaf__t73 | 5_1_grt | 2.7 | last meaningful line 0.5 h ago (207/214 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | otc-1173846-21068 | 1173846 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-1174520-11483 | 1174520 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-1910005-4834 | 1910005 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc8 | otc-2593908-9338 | 2593908 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc8 | so_837982_ff_21173 | so_837982_ff_21173 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | so_837982_tt_21173 | so_837982_tt_21173 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2109433 | col_h10_r0_p4__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 56684.3 last 56684.3 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2093461 | col_h10_r1__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 28473.2 last 28473.2 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2653831 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.912 last 0.912 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | pregrt_ff_hold | 3.2 | repair_Violations best 58 last 104 rows 17 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv40e9fb5a-287653 | col_h9_r2__t1 | 5_2_route | 5.1 | last meaningful line 0.3 h ago (270/271 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t10-4186865 | dsdv_slice_c1x_C__t10 | selrange | 2.2 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t7-2862427 | dsdv_slice_c1x_C__t7 | sdc_lint | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_kv512_C__t1-288662 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 5.1 | last meaningful line 2.5 h ago (37/37 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-3178195 | hd_ctl | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2783/2783 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hgi_v1__cl42bc8b12-2545242 | kv3_hgi_v1 | tt_setup_repair | 0.4 | repair_Viol best 344 last 344 rows 75 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-kv3_hgi_v3-2875910 | kv3_hgi_v3 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5752/5752 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hroot-2456475 | kv3_hroot | 3_3_place_gp | 0.5 | overflow best 0.6535 last 0.6544 rows 14 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-kv3_hroot-2622210 | kv3_hroot | 3_3_place_gp | 0.4 | overflow best 0.6832 last 0.6832 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3368/3368 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-491594 | kv3_pc_v3 | 3_4_place_resized | 1.8 | last meaningful line 0.1 h ago (395/395 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v2n-2681030 | kv3_pv_v2n | 2_1_floorplan | 0.4 | last meaningful line 0.0 h ago (389/389 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v3-2877961 | kv3_pv_v3 | 2_1_floorplan | 0.3 | last meaningful line 0.0 h ago (245/245 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v4-2911509 | kv3_pv_v4 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v6n-2406851 | kv3_pv_v6n | 4_1_cts | 0.5 | last meaningful line 0.3 h ago (7490/7490 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v8-3739898 | kv3_pv_v8 | 3_5_place_dp | 2.5 | last meaningful line 0.2 h ago (53/53 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-1792430 | ot_s81sl_kv_leaf__t5 | 3_3_place_gp | 0.9 | last meaningful line 0.0 h ago (108/108 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t17-2585029 | ot_s81sl_leaf__t17 | 3_3_place_gp | 0.4 | overflow best 0.6135 last 0.6135 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t33-2546296 | ot_s81sl_leaf__t33 | 3_3_place_gp | 0.4 | overflow best 0.5874 last 0.5874 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-461535 | ot_s81sl_leaf__t44 | 5_1_grt | 1.8 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-phy__t1-2625032 | phy__t1 | tt_setup_measure | 0.4 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (4713/4713 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t22-239981 | slice_station__t22 | 5_2_route | 5.1 | drt_violations best 18976 last 18976 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-570014 | slice_station__t51 | 5_2_route | 9.3 | drt_violations best 5868 last 5868 rows 2 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t6__cl0755c26e-2749197 | slice_station__t6 | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (205/451 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 4_1_cts | 2.3 | last meaningful line 0.2 h ago (5462/5462 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-3009482 | slw_fe_v2 | pregrt_ff_hold | 3.0 | repair_TNS best 158126 last 158126 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | 4_1_cts | 2.2 | last meaningful line 0.2 h ago (5233/5233 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | pregrt_ff_hold | 3.0 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | eco-abs-2785968 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.3 h ago (526/526 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | otc-1108174-15457 | 1108174 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-1631796-31019 | 1631796 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-1661483-30301 | 1661483 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-1916796-12156 | 1916796 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc9 | otc-664483-8927 | 664483 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-664799-872 | 664799 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-682537-13250 | 682537 | - | 4.9 |  | NO-DATA: no log found |  |
| epyc9 | prd-count-p1_tc-3504713 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i2-1306615 | eco_20261122_180231_342380-i2 | 5_2_route | 1.2 | last meaningful line 0.1 h ago (134/134 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | so_2745858_ff_14298 | so_2745858_ff_14298 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (488/488 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | so_2745858_tt_14298 | so_2745858_tt_14298 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (488/488 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-3359910 | col_h10_r0_p4__t1 | 5_1_grt | 5.1 | last meaningful line 0.1 h ago (152/152 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3365642 | col_h10_r1__t1 | 5_1_grt | 5.1 | last meaningful line 0.3 h ago (203/206 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 18.7 | last meaningful line 0.1 h ago (279/279 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3518851 | col_h9_r0_p4__t1 | 5_1_grt | 5.0 | last meaningful line 1.0 h ago (207/216 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-3535177 | col_h9_r0_p5__t1 | 5_1_grt | 5.0 | last meaningful line 0.3 h ago (210/213 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvc1b82625-3531236 | col_h9_r0_p5__t1 | 5_1_grt | 5.0 | last meaningful line 0.1 h ago (160/160 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3522355 | col_h9_r2__t1 | 5_1_grt | 5.0 | repair_TNS best 9296.79 last 9296.79 rows 6 | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvcf44b14c-1664216 | col_h9_r2__t1 | 5_2_route | 8.4 | drt_violations best 52013 last 52013 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-3365034 | dsdv_slice_c1x_C__t3 | 3_3_place_gp | 5.1 | overflow best 0.1991 last 0.1991 rows 42 | YOUNG: stage 0.9 h < 1 h |  |
| intel1 | dpkit-hd_lep0N-1545648 | hd_lep0N | 4_2_tapbal_grt | 3.4 | last meaningful line 1.3 h ago (48/51 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_2_route | 17.0 | last meaningful line 0.7 h ago (275/276 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v7-3747893 | kv3_pv_v7 | 2_1_floorplan | 2.0 | last meaningful line 1.0 h ago (1547/1547 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 18.5 | last meaningful line 4.3 h ago (209/239 lines) | YOUNG: evidence 5.0 h < 6 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-3536309 | ot_s81sl_leaf__t2 | 5_1_grt | 5.0 | last meaningful line 1.8 h ago (207/215 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t71-2773215 | ot_s81sl_leaf__t71 | 5_1_grt | 2.7 | last meaningful line 0.8 h ago (210/217 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | 4_1_cts | 2.6 | last meaningful line 0.4 h ago (5231/5231 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-sle_su_c-645555 | sle_su_c | 5_1_grt | 6.6 | last meaningful line 0.5 h ago (281/1287 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t28-3353995 | slice_station__t28 | 5_2_route | 5.1 | drt_violations best 13901 last 13901 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t52-3521993 | slice_station__t52 | tt_setup_repair_grt | 5.0 | last meaningful line 0.0 h ago (367/367 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 5.1 | last meaningful line 0.2 h ago (259/260 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | otc-2998450-18208 | 2998450 | signoff | 5.3 | last meaningful line 5.3 h ago (3/3 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel1 | otc-589898-30912 | 589898 | - | 1.3 |  | NO-DATA: no log found |  |
| intel1 | otc-590329-1688 | 590329 | - | 1.3 |  | NO-DATA: no log found |  |
| intel1 | otc-591591-991 | 591591 | - | 1.3 |  | NO-DATA: no log found |  |
| intel1 | otc-910747-1220 | 910747 | - | 1.1 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 2.4 | last meaningful line 0.0 h ago (47/47 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i1-1606115 | eco_20261122_143408_943433-i1 | 5_1_grt | 0.6 | last meaningful line 0.3 h ago (243/1451 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i1-380897 | eco_20261122_165619_1517073-i1 | 5_2_route | 1.4 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | 5_2_route | 10.5 | last meaningful line 0.2 h ago (282/283 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2864182 | coll_ftm | 5_2_route | 1.9 | drt_violations best 10172 last 10172 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| intel2 | dpkit-coll_ftm-495457 | coll_ftm | 5_1_grt | 0.7 | last meaningful line 0.3 h ago (244/363 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2645851 | dsdv_slice_lepe_nh_mus_C__t1 | 5_1_grt | 14.6 | last meaningful line 4.0 h ago (211/219 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-483181 | kv3_io_ft | 5_2_route | 0.7 | last meaningful line 0.0 h ago (211/211 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v5-3790571 | kv3_pv_v5 | 2_1_floorplan | 1.3 | last meaningful line 0.5 h ago (1420/1420 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t11-599830 | ot_s81sl_leaf__t11 | tt_setup_repair_grt | 10.3 | repair_Violations best 156 last 210 rows 18 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 12.5 | last meaningful line 0.4 h ago (274/275 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl55be2264-3685080 | sle_stm_v2 | 5_2_route | 12.6 | drt_violations best 838 last 838 rows 4 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | 5_2_route | 12.6 | drt_violations best 305042 last 305042 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel2 | otc-1716416-27789 | 1716416 | signoff | 0.0 | last meaningful line 0.0 h ago (3/3 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-2036577-617 | 2036577 | asbuilt.yosys | 1.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_2_route | 15.7 | drt_violations best 1722 last 1722 rows 17 | before-window best 73151, window best 1722 | PROGRESS: drt_violations improved 97.6 % in window |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_LP__t2-2617721 | dsdv_slice_lepw_mus_LP__t2 | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-1351532 | sle_hc2 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-1325606 | sle_stm_v1 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 68.5 | last meaningful line 0.4 h ago (1612/1612 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-2470572 | col_h9_r1__t1 | 5_1_grt | 4.8 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | pregrt_ff_hold | 7.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | pregrt_ff_hold | 7.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | 5_1_grt | 7.3 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | pregrt_ff_hold | 5.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | prd-eco_20261122_123708_2624415-i1t-3236939 | eco_20261122_123708_2624415-i1t | 5_2_route | 10.6 | drt_violations best 1 last 1 rows 55 | before-window best 1403, window best 1 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_2_route | 15.1 | drt_violations best 205 last 205 rows 16 | before-window best 110424, window best 205 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 19.0 | drt_violations best 13260 last 13260 rows 14 | before-window best 16565, window best 13260 | PROGRESS: drt_violations improved 20.0 % in window |  |
| epyc8 | dpkit-kv3_hgi_v2__cle0015330-3274473 | kv3_hgi_v2 | pregrt_ff_hold | 0.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hgi_v2__cle0015330-3323577 | kv3_hgi_v2 | pregrt_ff_hold | 0.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_io_cor_v1-619668 | kv3_io_cor_v1 | 5_1_grt | 1.8 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | kvcore-qkd_ectlk_q2__243.648x172.8_-2536831 | kvcore-qkd_ectlk_q2__243.648x172.8_ | 5_1_grt | 1.1 | repair_TNS best 0 last 0 rows 63 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl911743eb-4131559 | col_h10_r0_p1__t1 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-4076788 | col_h10_r1__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2103226 | col_h10_r2__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3665094 | col_h9_r0_p3__t1 | 5_2_route | 18.6 | drt_violations best 28 last 28 rows 43 | before-window best 178849, window best 28 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t56-866545 | ot_s81sl_leaf__t56 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_fw_v2__cl69f5e854-2970240 | sle_fw_v2 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | tt_setup_repair | 3.1 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-slw_fw_v3-3096266 | slw_fw_v3 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 11.0 | drt_violations best 20 last 20 rows 23 | before-window best 71, window best 20 | PROGRESS: drt_violations improved 71.8 % in window |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_2_route | 18.5 | drt_violations best 195281 last 195281 rows 1 | before-window best 195281, window best 195281 | PROGRESS: drt_violations: active iteration at 103273 < best completed total 195281 (in-ite |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 18.5 | drt_violations best 210671 last 210671 rows 1 | before-window best 210671, window best 210671 | PROGRESS: drt_violations: active iteration at 100655 < best completed total 210671 (in-ite |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2916065 | dsdv_slice_lepe_nh_mus_LP__t1 | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-glue-1559836 | glue | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-serdes__t4-2914107 | serdes__t4 | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-tt_ctlm-1686138 | tt_ctlm | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 25.9 | drt_violations best 1064 last 1064 rows 23 | before-window best 1452, window best 1064 | PROGRESS: drt_violations improved 26.7 % in window |  |
| intel2 | dpkit-native59-3804419 | native59 | pregrt_ff_hold | 12.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_leaf__t1-283252 | ot_s81sl_leaf__t1 | 5_1_grt | 10.5 | repair_TNS best 153369 last 153369 rows 6 | before-window best 159911, window best 153369 | PROGRESS: repair_TNS improved 4.1 % in window |  |
