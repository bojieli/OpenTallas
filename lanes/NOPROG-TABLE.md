# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 13:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 5, 'GRT-LABEL': 5, 'YOUNG': 65, 'NO-DATA': 9, 'EXCLUDED': 1, 'PROGRESS': 24}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 19.3 | last meaningful line 6.3 h ago (211/219 lines) | NO-PROGRESS: no new non-iteration log line for 6.3 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_2_route | 14.9 | drt_violations best 1269 last 2007 rows 29 | before-window best 1269, window best 1489 | NO-PROGRESS: drt_violations best 1489 vs 1269 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 46.5 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 14.6 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 13.4 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc10 | dpkit-coll_core-2755880 | coll_core | 5_1_grt | 8.5 | grt rounds 2 overflow 5:6694 -> 10:735 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-3843742 | coll_core | 5_1_grt | 7.6 | grt rounds 2 overflow 5:353 -> 10:29 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3134610 | dsdv_slice_kv512_C__t1 | 5_1_grt | 11.8 | grt rounds 2 overflow 5:166212 -> 10:139687 | GRT-LABEL: DESIGN-FAIL: overflow 139687 at round 10 > 1000 |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 5_1_grt | 16.7 | grt rounds 2 overflow 5:13375 -> 10:10994 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pv_v3e-280312 | kv3_pv_v3e | 5_1_grt | 9.4 | grt rounds 1 overflow 5:174039 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-2955109 | dsdv_slice_c1x_C__t8 | pregrt_ff_hold | 8.4 | repair_Violations best 15575 last 15575 rows 18 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_C__t1-439143 | dsdv_slice_lepw_mus_C__t1 | 3_4_place_resized | 3.9 | repair_Remaining best 291098 last 291098 rows 58 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | 5_1_grt | 9.7 | repair_TNS best 478.535 last 478.535 rows 4 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | eco-abs-2876970 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-1692786-27381 | 1692786 | signoff | 1.2 | last meaningful line 1.1 h ago (3/3 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | otc-274226-16996 | 274226 | 4_1_cts | 4.0 | last meaningful line 0.0 h ago (8936/8936 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc10 | otc-2875858-25745 | 2875858 | clk_freeze_post | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 3_4_place_resized | 8.7 | last meaningful line 0.5 h ago (449/449 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | otc-2072262-2525 | 2072262 | signoff | 1.8 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | otc-2508762-7926 | 2508762 | signoff | 1.5 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | otc-356178-19590 | 356178 | signoff | 3.3 | last meaningful line 3.3 h ago (3/3 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | otc-3577275-393 | 3577275 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261122_164248_3895049-i2-3950771 | eco_20261122_164248_3895049-i2 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i2t-1118869 | eco_20261122_181101_3945375-i2t | 5_2_route | 2.7 | drt_violations best 338 last 338 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i2t-153753 | eco_20261122_190506_3875261-i2t | 5_2_route | 3.5 | drt_violations best 8883 last 8883 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i1t-768660 | eco_20261123_102841_2122262-i1t | 5_2_route | 3.0 | drt_violations best 9789 last 9789 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i1t-830727 | eco_20261123_103136_2028090-i1t | 5_2_route | 2.9 | drt_violations best 20886 last 20886 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 11.8 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | pregrt_ff_hold | 5.1 | repair_TNS best 275302 last 275302 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-935860 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 3.5 | last meaningful line 1.3 h ago (36/36 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | otc-3723552-11009 | 3723552 | - | 4.8 |  | NO-DATA: no log found |  |
| epyc7 | prd-count-p1_bc-1905995 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_124118_879330-i1-896574 | eco_20261123_124118_879330-i1 | 5_2_route | 3.6 | drt_violations best 364 last 364 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_160238_2681508-i1-2430323 | eco_20261123_160238_2681508-i1 | 5_2_route | 2.2 | drt_violations best 22 last 22 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i1t-127041 | eco_20261123_171023_3055226-i1t | 5_2_route | 4.3 | drt_violations best 15147 last 15147 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171842_3718765-i1-3800902 | eco_20261123_171842_3718765-i1 | 5_2_route | 0.9 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795467809896538497-i1t-60038 | eco_retry_1795467809896538497-i1t | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (212/212 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 6.4 | repair_TNS best 449968 last 449968 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 5_1_grt | 9.7 | repair_TNS best 6423.01 last 6423.01 rows 4 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t27-3500785 | slice_station__t27 | 5_2_route | 4.5 | drt_violations best 22601 last 22601 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-196363 | slice_station__t37 | 5_2_route | 4.1 | last meaningful line 0.1 h ago (259/259 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t38-3922551 | slice_station__t38 | 5_2_route | 4.3 | drt_violations best 41090 last 41090 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t42__clcf44e680-182679 | slice_station__t42 | 5_2_route | 4.1 | drt_violations best 19399 last 19399 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t43-157875 | slice_station__t43 | 5_2_route | 4.1 | last meaningful line 0.1 h ago (260/261 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t49-194878 | slice_station__t49 | 5_2_route | 4.1 | last meaningful line 0.3 h ago (256/257 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cl39451317-3753261 | slice_station__t50 | 5_2_route | 4.4 | last meaningful line 0.3 h ago (264/265 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cld84c9e24-169001 | slice_station__t50 | 5_2_route | 4.1 | drt_violations best 20332 last 20332 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t6__cl0755c26e-3930284 | slice_station__t6 | 6_1_fill | 4.3 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t6__cl54a9ceeb-3927462 | slice_station__t6 | 6_report | 4.3 | last meaningful line 0.1 h ago (68/68 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i1-805274 | eco_20261123_120225_75582-i1 | 5_2_route | 3.9 | drt_violations best 15245 last 15245 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_140713_549985-i1-1751532 | eco_20261123_140713_549985-i1 | 5_2_route | 3.4 | drt_violations best 3 last 3 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i1-1884148 | eco_20261123_163717_2005956-i1 | 5_2_route | 1.3 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_1_grt | 4.8 | repair_Viol best 2085 last 2085 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | 5_2_route | 14.5 | drt_violations best 137762 last 137762 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | 6_report | 13.5 | last meaningful line 0.1 h ago (732/732 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | generate_abstract | 16.5 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-123351-27321 | 123351 | ot_bind_native_fe29765083b15acb633a19d9 | 0.0 | last meaningful line -0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 15.2 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i2-3887394 | eco-i2 | 5_1_grt | 0.5 | last meaningful line 0.4 h ago (245/1276 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i1t-2251452 | eco_20261123_190031_3093983-i1t | 5_2_route | 2.5 | drt_violations best 8882 last 8882 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_205006_3008284-i1-3778492 | eco_20261123_205006_3008284-i1 | 5_1_grt | 0.6 | last meaningful line 0.4 h ago (238/1521 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | relec1122-ml-hdctl_r8_fsmhint | relec1122-ml-hdctl_r8_fsmhint | - | 2.4 |  | NO-DATA: no log found |  |
| epyc9 | so_3829600_tt_86335 | so_3829600_tt_86335 | signoff | 0.6 |  | NO-DATA: empty log |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t4-19056 | dsdv_slice_c1x_C__t4 | 3_1_place_gp_skip_io | 3.0 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-459624 | dsdv_slice_c1x_C__t6 | 1_2_yosys | 2.6 | last meaningful line 0.0 h ago (224/224 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t7-1834998 | dsdv_slice_c1x_C__t7 | 1_1_yosys_canonicalize | 1.4 | last meaningful line 0.2 h ago (127/127 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c3x_C__t1-142746 | dsdv_slice_c3x_C__t1 | 3_1_place_gp_skip_io | 2.9 | overflow best 0.9952 last 0.9952 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-2396125 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | 5_2_route | 16.9 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | 5_2_route | 17.6 | drt_violations best 71799 last 71799 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts.otrun | 1.9 | last meaningful line 1.0 h ago (5/5 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts.otrun | 1.2 | last meaningful line 1.0 h ago (5/5 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | otc-571036-12201 | 571036 | signoff | 2.5 | last meaningful line 2.3 h ago (3/3 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i2-876871 | eco_20261122_143408_943433-i2 | 5_2_route | 2.3 | drt_violations best 7151 last 7151 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | prd-eco_20261123_090657_914087-i1t-2682219 | eco_20261123_090657_914087-i1t | 5_1_grt | 4.3 | repair_Viol best 1637 last 1637 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel1 | prd-eco_20261123_130527_1956436-i1t-2772907 | eco_20261123_130527_1956436-i1t | 5_1_grt | 0.4 | last meaningful line 0.1 h ago (285/399 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | so_3108762_ff_81254 | so_3108762_ff_81254 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | so_3108762_tt_81254 | so_3108762_tt_81254 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2731145 | col_h10_r1__t1 | 5_2_route | 9.5 | last meaningful line 0.3 h ago (291/292 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-2409011 | kv3_io_ft | 5_2_route | 0.7 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i1-811516 | eco_20261123_051704_3678821-i1 | 5_2_route | 2.2 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i1-995418 | eco_20261123_063813_234645-i1 | 5_2_route | 2.0 | last meaningful line 0.2 h ago (285/286 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | so_3077807_ff_54522 | so_3077807_ff_54522 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_3077807_tt_54522 | so_3077807_tt_54522 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | otc-2879855-15452 | 2879855 | ot_bind_native_94fb3121d89a024ad3313eef | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-coll_core-2130490 | coll_core | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 9.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 16.6 | drt_violations best 13554 last 13554 rows 14 | before-window best 21163, window best 13554 | PROGRESS: drt_violations improved 36.0 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 19.3 | drt_violations best 1743 last 5229 rows 18 | before-window best 5882, window best 1743 | PROGRESS: drt_violations improved 70.4 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 21.5 | drt_violations best 8936 last 8936 rows 15 | before-window best 11209, window best 8936 | PROGRESS: drt_violations improved 20.3 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 18.1 | drt_violations best 44158 last 44158 rows 13 | before-window best 51167, window best 44158 | PROGRESS: drt_violations improved 13.7 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 18.5 | drt_violations best 50150 last 50150 rows 13 | before-window best 56276, window best 50150 | PROGRESS: drt_violations improved 10.9 % in window |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | 5_2_route | 11.9 | drt_violations best 1396 last 1403 rows 29 | before-window best 172065, window best 1396 | PROGRESS: drt_violations improved 99.2 % in window |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 24.2 | drt_violations best 5 last 5 rows 49 | before-window best 75, window best 5 | PROGRESS: drt_violations improved 93.3 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 19.2 | drt_violations best 56454 last 56454 rows 13 | before-window best 65161, window best 56454 | PROGRESS: drt_violations improved 13.4 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 29.9 | drt_violations best 20 last 20 rows 54 | before-window best 33, window best 20 | PROGRESS: drt_violations improved 39.4 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 33.3 | drt_violations best 6073 last 6073 rows 22 | before-window best 7732, window best 6073 | PROGRESS: drt_violations improved 21.5 % in window |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 10.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 20.8 | drt_violations best 14710 last 31045 rows 19 | before-window best 14710, window best 31045 | PROGRESS: drt_violations: falling inside the active iteration (31045 -> 25831) |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | 4_1_cts | 8.0 | last meaningful line 0.1 h ago (10038/10038 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 17.4 | drt_violations best 22 last 22 rows 39 | before-window best 183055, window best 22 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | 4_1_cts | 7.3 | last meaningful line 1.0 h ago (11137/11137 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_1_grt | 16.5 | repair_TNS best 323.706 last 323.706 rows 5 | before-window best 796.618, window best 323.706 | PROGRESS: repair_TNS improved 59.4 % in window |  |
| epyc9 | prd-eco_20261123_142403_3177550-i2-3394943 | eco_20261123_142403_3177550-i2 | 5_2_route | 1.1 | drt_violations best 0 last 0 rows 4 | PROGRESS: drt_violations reached 0 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 33.0 | drt_violations best 28 last 28 rows 60 | before-window best 175829, window best 28 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 32.7 | drt_violations best 29547 last 29547 rows 12 | before-window best 37704, window best 29547 | PROGRESS: drt_violations improved 21.6 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 19.4 | drt_violations best 88977 last 88977 rows 9 | before-window best 132000, window best 88977 | PROGRESS: drt_violations improved 32.6 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 16.7 | drt_violations best 84 last 84 rows 20 | before-window best 10507, window best 84 | PROGRESS: drt_violations improved 99.2 % in window |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 26.7 | drt_violations best 2178 last 4340 rows 19 | before-window best 4565, window best 2178 | PROGRESS: drt_violations improved 52.3 % in window |  |
