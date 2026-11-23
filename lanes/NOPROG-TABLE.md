# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 03:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'UNSIGNABLE': 1, 'GRT-LABEL': 17, 'YOUNG': 147, 'NO-DATA': 30, 'EXCLUDED': 4, 'PROGRESS': 34}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 36.0 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc9 | dpkit-ot_s81sl_leaf__t6-4011314 | ot_s81sl_leaf__t6 | tt_setup_repair_grt | 22.1 | repair_Violations best 102 last 102 rows 30 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -431.84 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | 5_1_grt | 19.4 | grt rounds 2 overflow 5:14057 -> 10:13400 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | 5_1_grt | 19.4 | grt rounds 2 overflow 5:13717 -> 10:12993 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2115818 | dsdv_slice_c1x_C__t10 | 5_1_grt | 11.0 | grt rounds 2 overflow 5:46621 -> 10:43275 | GRT-LABEL: DESIGN-FAIL: overflow 43275 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t11-3893305 | ot_s81sl_leaf__t11 | 5_1_grt | 3.0 | grt rounds 2 overflow 5:20442 -> 10:19023 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t25__cl55642d17-3247888 | ot_s81sl_leaf__t25 | 5_1_grt | 8.0 | grt rounds 2 overflow 5:32072 -> 10:20314 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t30-1023895 | ot_s81sl_leaf__t30 | 5_1_grt | 2.2 | grt rounds 2 overflow 5:30533 -> 10:27226 | GRT-LABEL: DESIGN-FAIL: overflow 27226 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t22-4105867 | ot_s81sl_leaf__t22 | 5_1_grt | 3.7 | grt rounds 2 overflow 5:59196 -> 10:57997 | GRT-LABEL: DESIGN-FAIL: overflow 57997 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t3-56823 | ot_s81sl_leaf__t3 | 5_1_grt | 9.6 | grt rounds 2 overflow 5:1586 -> 10:260 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hg-374537 | kv3_hg | 5_1_grt | 2.2 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t14-2320204 | ot_s81sl_leaf__t14 | 5_1_grt | 3.2 | grt rounds 2 overflow 5:22910 -> 10:19881 | GRT-LABEL: DESIGN-FAIL: overflow 19881 at round 10 > 1000 |  |
| epyc8 | dpkit-ot_s81sl_leaf__t23-1888361 | ot_s81sl_leaf__t23 | 5_1_grt | 3.3 | grt rounds 2 overflow 5:11109 -> 10:210 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t15-153595 | ot_s81sl_leaf__t15 | 5_1_grt | 3.0 | grt rounds 2 overflow 5:31474 -> 10:17162 | GRT-LABEL: DESIGN-FAIL: overflow 17162 at round 10 > 1000 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t17-450077 | ot_s81sl_leaf__t17 | 5_1_grt | 2.8 | grt rounds 2 overflow 5:32509 -> 10:25627 | GRT-LABEL: DESIGN-FAIL: overflow 25627 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 22.2 | grt rounds 6 overflow 5:805 -> 10:203 -> 15:132 -> 20:64 -> 25:77 -> 30:61 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 22.2 | grt rounds 6 overflow 5:2533 -> 10:1498 -> 15:842 -> 20:584 -> 25:584 -> 30:139 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-3520587 | ot_s81sl_leaf__t53 | 5_1_grt | 8.8 | grt rounds 2 overflow 5:29437 -> 10:25353 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 18.4 | grt rounds 3 overflow 5:88799 -> 10:83085 -> 15:86608 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-bk_sel__t2-2787287 | bk_sel__t2 | 3_3_place_gp | 0.8 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-cbx_q10__cl89936551_h-2845733 | cbx_q10 | 3_3_place_gp | 0.7 | overflow best 0.1393 last 0.1393 rows 37 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-hd_lep0N_w-776600 | hd_lep0N_w | pregrt_ff_hold | 2.0 | repair_TNS best 1.6027e+06 last 1.6027e+06 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-hd_lep0N_w-827145 | hd_lep0N_w | pregrt_ff_hold | 2.0 | repair_TNS best 1.62065e+06 last 1.62065e+06 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-hd_lep0N_w-891099 | hd_lep0N_w | pregrt_ff_hold | 1.9 | repair_TNS best 1.62065e+06 last 1.62065e+06 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-hd_lep0N_w-908756 | hd_lep0N_w | pregrt_ff_hold | 1.9 | repair_TNS best 1.6027e+06 last 1.6027e+06 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-hd_st_n4-3814785 | hd_st_n4 | 5_2_route | 2.6 | drt_violations best 18611 last 18611 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-hd_st_n4-3877061 | hd_st_n4 | 5_2_route | 2.6 | drt_violations best 20355 last 20355 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hroot-740108 | kv3_hroot | postcts_gate_TT | 2.0 | last meaningful line 0.0 h ago (1161/1161 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-3882608 | kv3_pv_v3 | 3_5_place_dp | 2.6 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3e-3821788 | kv3_pv_v3e | 3_5_place_dp | 2.6 | last meaningful line 0.3 h ago (55/55 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 2_4_floorplan_pdn | 20.7 | last meaningful line 0.0 h ago (206/206 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t43-3642617 | ot_s81sl_leaf__t43 | 4_1_cts | 0.2 | last meaningful line 0.2 h ago (53/53 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t73-3464910 | ot_s81sl_leaf__t73 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3745/3745 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-3135509 | sle_stm_v1 | 5_1_grt | 3.1 | last meaningful line 0.0 h ago (170/170 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v2__cl7b3062fa-3029892 | sle_stm_v2 | 5_2_route | 11.1 | drt_violations best 32420 last 32420 rows 2 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc10 | eco-abs-1958616 | eco-abs | generate_abstract | 1.3 | last meaningful line 0.4 h ago (623/623 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | otc-3082835-5546 | 3082835 | - | 3.1 |  | NO-DATA: no log found |  |
| epyc10 | otc-3599933-4057 | 3599933 | build_bcast_mut_srx0 | 0.2 | last meaningful line 0.1 h ago (612/612 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-3599934-783 | 3599934 | build_bcast_mut_srx0 | 0.2 | last meaningful line 0.1 h ago (612/612 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-3599935-15987 | 3599935 | build_bcast_mut_srx0 | 0.2 | last meaningful line 0.1 h ago (612/612 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-3639623-31519 | 3639623 | build_bcast_mut_srx0_hc | 0.2 | last meaningful line 0.1 h ago (699/699 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-3639625-21000 | 3639625 | build_bcast_mut_srx0_hc | 0.2 | last meaningful line 0.1 h ago (699/699 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-3639626-8531 | 3639626 | build_bcast_mut_srx0_hc | 0.2 | last meaningful line 0.1 h ago (699/699 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-3874152-20216 | 3874152 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 6.1 | drt_violations best 28584 last 28584 rows 3 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_075519_12410-i1t-3218186 | eco_20261123_075519_12410-i1t | 5_2_route | 3.0 | drt_violations best 1077 last 1077 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | so_3632401_ff_5796 | so_3632401_ff_5796 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | so_3632401_tt_5796 | so_3632401_tt_5796 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-1820678 | col_h10_r0_p1__t1 | 5_1_grt | 8.8 | last meaningful line 0.0 h ago (214/215 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1379295 | col_h10_r0_p4__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 144649 last 144649 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-2056070 | col_h10_r1__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 108409 last 108409 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-1483343 | col_h9_r0_p4__t1 | 5_1_grt | 4.4 | last meaningful line 0.8 h ago (215/223 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-2470572 | col_h9_r1__t1 | 5_2_route | 8.5 | drt_violations best 85064 last 85064 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2108278 | dsdv_slice_c1x_C__t1 | 5_1_grt | 11.0 | last meaningful line 5.3 h ago (208/215 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-3069419 | dsdv_slice_c1x_C__t3 | sdc_lint | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_mu_C__t1-3116985 | dsdv_slice_lepe_mu_C__t1 | 5_1_grt | 8.1 | last meaningful line 3.0 h ago (207/213 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 7.7 | repair_TNS best 975.165 last 975.165 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-hd_lep0N_w-3963146 | hd_lep0N_w | pregrt_ff_hold | 7.6 | repair_TNS best 5432.86 last 5432.86 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v4-1845670 | kv3_hgi_v4 | pregrt_ff_hold | 1.7 | repair_TNS best 98684.5 last 98684.5 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-kv3_hgi_v4-724077 | kv3_hgi_v4 | 5_1_grt | 4.8 | last meaningful line 0.5 h ago (291/1298 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_2_route | 4.4 | drt_violations best 87459 last 87459 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-3921528 | kv3_hroot | 5_2_route | 3.0 | last meaningful line 0.3 h ago (250/251 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v3n-1352817 | kv3_pv_v3n | 3_3_place_gp | 4.4 | overflow best 0.0996 last 0.0996 rows 41 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4n-420301 | kv3_pv_v4n | 3_4_place_resized | 4.9 | last meaningful line 0.2 h ago (740/740 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t1-3941275 | ot_s81sl_leaf__t1 | pregrt_ff_hold | 3.0 | repair_Violations best 591 last 599 rows 127 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 8.8 | last meaningful line 0.3 h ago (270/271 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-1430945 | ot_s81sl_leaf__t36 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (205/208 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t7-3842605 | ot_s81sl_leaf__t7 | 5_1_grt | 3.0 | last meaningful line 0.5 h ago (204/211 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-775509 | sle_ctl | 4_1_cts | 4.7 | last meaningful line 0.1 h ago (9342/9342 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | 5_2_route | 11.1 | last meaningful line 0.3 h ago (283/284 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | postcts_gate_FF | 11.0 | last meaningful line 0.2 h ago (393/393 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | postcts_gate_FF | 11.0 | last meaningful line 0.2 h ago (376/376 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | 5_2_route | 11.0 | last meaningful line 0.3 h ago (279/280 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | 5_1_grt | 8.8 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 7.6 | drt_violations best 78520 last 78520 rows 2 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 8.0 | drt_violations best 75867 last 75867 rows 3 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | otc-2186430-24000 | 2186430 | - | 4.0 |  | NO-DATA: no log found |  |
| epyc2 | otc-2436152-11731 | 2436152 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc2 | otc-2438095-32195 | 2438095 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261122_164248_3895049-i1-2533130 | eco_20261122_164248_3895049-i1 | 5_2_route | 3.8 | last meaningful line 0.3 h ago (271/272 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164521_3948325-i1-2180646 | eco_20261122_164521_3948325-i1 | 5_2_route | 4.0 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i1-2037456 | eco_20261122_181101_3945375-i1 | 5_1_grt | 1.6 | last meaningful line 0.8 h ago (237/1318 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i1-2840670 | eco_20261122_190506_3875261-i1 | 5_1_grt | 1.0 | last meaningful line 0.2 h ago (239/381 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 4_2_tapbal_grt | 1.3 | last meaningful line 0.5 h ago (63/72 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-836163 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.9 | last meaningful line 0.1 h ago (65/65 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 155482 last 155482 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3134610 | dsdv_slice_kv512_C__t1 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (3307/3307 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3565523 | dsdv_slice_lepe_nh_mus_C__t1 | 4_1_cts | 4.1 | last meaningful line 0.2 h ago (6444/6444 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-3305132 | hd_lep0N_w | 4_2_tapbal_grt | 1.2 | last meaningful line 0.8 h ago (46/105 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-hd_st_n4-1251911 | hd_st_n4 | 5_2_route | 2.6 | drt_violations best 18611 last 18611 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_st_n4-2829569 | hd_st_n4 | 5_2_route | 1.5 | last meaningful line 0.0 h ago (118/118 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v1-1064320 | kv3_pv_v1 | 3_3_place_gp | 2.7 | overflow best 0.0991 last 0.0991 rows 42 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2-603007 | kv3_pv_v2 | 3_3_place_gp | 3.1 | overflow best 0.0984 last 0.0984 rows 43 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | 5_2_route | 12.8 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | 5_2_route | 13.7 | drt_violations best 144858 last 144858 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-881903 | sle_stm_v1 | 6_report | 13.8 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 13.7 | drt_violations best 409476 last 409476 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl9beb65e6-3994155 | slw_stm_v2 | 5_2_route | 12.3 | drt_violations best 72487 last 72487 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 8.7 | drt_violations best 76194 last 76194 rows 4 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc7 | otc-2287405-27505 | 2287405 | signoff | 1.9 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | otc-254531-30458 | 254531 | - | 3.4 |  | NO-DATA: no log found |  |
| epyc7 | otc-3970901-4095 | 3970901 | - | 3.8 |  | NO-DATA: no log found |  |
| epyc7 | otc-4110793-30116 | 4110793 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261122_215654_330309-i2-3585488 | eco_20261122_215654_330309-i2 | 5_1_grt | 1.0 | last meaningful line 0.7 h ago (230/1366 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_220050_168828-i2-2223567 | eco_20261122_220050_168828-i2 | 5_2_route | 2.0 | last meaningful line 0.2 h ago (285/286 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_080018_715668-i1t-847605 | eco_20261123_080018_715668-i1t | 5_1_grt | 2.9 | repair_Viol best 2444 last 2444 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | so_159924_ff_71985 | so_159924_ff_71985 | signoff_20261123_103406_1530301 | 0.4 |  | NO-DATA: empty log |  |
| epyc7 | so_159924_tt_71985 | so_159924_tt_71985 | signoff_20261123_103406_1530301 | 0.4 |  | NO-DATA: empty log |  |
| epyc7 | unc-sta61-785501 | unc-sta61 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | unc-sta61-800687 | unc-sta61 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-cbf_q00__cl1b5a6458-757482 | cbf_q00 | 2_3_floorplan_tapcell | 0.4 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q11-815128 | cbf_q11 | 2_1_floorplan | 0.3 | last meaningful line 0.0 h ago (1191/1191 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-663458 | col_h10_r2__t1 | 3_3_place_gp | 0.4 | overflow best 0.3829 last 0.3829 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2000675 | col_h9_r0_p2__t1 | 5_2_route | 8.9 | last meaningful line 0.3 h ago (294/295 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-2217964 | col_h9_r2__t1 | 5_2_route | 8.8 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t1-2205610 | dsdv_slice_c1x_C__t1 | 2_4_floorplan_pdn | 3.2 | last meaningful line 0.0 h ago (73/73 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t8-1783469 | dsdv_slice_c1x_C__t8 | 2_4_floorplan_pdn | 3.4 | last meaningful line 0.0 h ago (72/72 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-1930297 | dsdv_slice_kv512_C__t1 | 5_1_grt | 3.3 | last meaningful line 0.1 h ago (196/209 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2088472 | dsdv_slice_lepe_nh_mus_C__t1 | pregrt_ff_hold | 8.8 | repair_TNS best 24080.1 last 24080.1 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc8 | dpkit-glue-555250 | glue | 5_2_route | 11.3 | last meaningful line 0.3 h ago (272/273 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hgi_v2__cle0015330-3763428 | kv3_hgi_v2 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (167/167 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hgi_v8-3855514 | kv3_hgi_v8 | 3_2_place_iop | 0.8 | last meaningful line 0.1 h ago (40/40 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-494270 | kv3_hub_Ei | 5_2_route | 11.3 | drt_violations best 91531 last 91531 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-2296613 | kv3_hub_Eo | 3_5_place_dp | 3.2 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-2343024 | kv3_hub_Wo | 3_5_place_dp | 3.2 | last meaningful line 0.3 h ago (117/117 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-619668 | kv3_io_cor_v1 | 5_2_route | 5.6 | drt_violations best 53187 last 53187 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pc_v1__cl7f648944-628689 | kv3_pc_v1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5187/5187 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-164511 | kv3_pv_v6 | 3_4_place_resized | 5.7 | last meaningful line 1.3 h ago (644/644 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-2008589 | sle_su_l1 | 5_1_grt | 3.3 | last meaningful line 0.4 h ago (222/681 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clb036e152-662184 | slw_st_a_v1 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-682069 | slw_st_a_v2 | 3_2_place_iop | 0.4 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-2514615-8132 | 2514615 | lec | 3.1 | LEC last write 3.1 h ago | YOUNG: evidence 3.1 h < 6 h |  |
| epyc8 | otc-3641731-29356 | 3641731 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc8 | relec1122-ml-slw_hc3_cld86_mainlec | relec1122-ml-slw_hc3_cld86_mainlec | - | 0.4 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2109433 | col_h10_r0_p4__t1 | 5_1_grt | 4.5 | last meaningful line 0.1 h ago (1507/1538 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2103226 | col_h10_r2__t1 | 5_2_route | 4.5 | drt_violations best 51230 last 51230 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_1_grt | 6.9 | repair_Remaining best 133446 last 133446 rows 181 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | 5_1_grt | 8.8 | last meaningful line 0.0 h ago (164/164 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-3178195 | hd_ctl | 5_1_grt | 3.8 | last meaningful line 0.1 h ago (133/133 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 4.1 | repair_TNS best 236158 last 236158 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 2.9 | repair_TNS best 309828 last 309828 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-kv3_pv-146967 | kv3_pv | 3_5_place_dp | 3.0 | last meaningful line 0.0 h ago (105/105 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v2n-2681030 | kv3_pv_v2n | 3_5_place_dp | 4.1 | last meaningful line 0.1 h ago (57/57 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v4-2911509 | kv3_pv_v4 | 3_4_place_resized | 4.0 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v5n-250741 | kv3_pv_v5n | 3_3_place_gp | 2.9 | last meaningful line 0.0 h ago (745/745 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v6n-2406851 | kv3_pv_v6n | tt_setup_repair | 4.3 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 6.8 | repair_Remaining best 354110 last 354110 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t33-1533302 | ot_s81sl_leaf__t33 | pregrt_ff_hold | 2.1 | repair_Violations best 563 last 563 rows 151 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t68-124972 | ot_s81sl_leaf__t68 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3444/3444 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl69f5e854-2970240 | sle_fw_v2 | 5_1_grt | 6.8 | repair_Remaining best 290028 last 290028 rows 152 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t6__cl0755c26e-2749197 | slice_station__t6 | 5_2_route | 4.1 | drt_violations best 14680 last 14680 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | fableunc-ctl-550859 | fableunc-ctl | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | lrc-qgrt-3979888 | lrc-qgrt | qgrt | 3.2 | last meaningful line 3.0 h ago (44/58 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 4.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-1631796-31019 | 1631796 | - | 4.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-1661483-30301 | 1661483 | - | 4.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-1916796-12156 | 1916796 | - | 4.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-2062537-15369 | 2062537 | - | 1.9 |  | NO-DATA: no log found |  |
| epyc9 | otc-2908826-5237 | 2908826 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc9 | otc-2909264-658 | 2909264 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc9 | otc-3778865-25787 | 3778865 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-3879808-1968 | 3879808 | gate.ys | 0.7 | last meaningful line 0.5 h ago (22052/22052 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | prd-eco-i1-454593 | eco-i1 | 5_2_route | 2.8 | last meaningful line 0.3 h ago (292/293 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i3t-3335435 | eco_20261122_180231_342380-i3t | 5_2_route | 1.0 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-residual-i4r-2209462 | residual-i4r | 5_2_route | 1.8 | last meaningful line 0.2 h ago (259/260 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | pvr7-pv8-hifo-3975570 | pvr7-pv8-hifo | - | 0.6 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-coll_s_base_mainlec | relec1122-ml-coll_s_base_mainlec | - | 0.6 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-coll_s_eco_mainlec | relec1122-ml-coll_s_eco_mainlec | - | 0.6 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-slw_hc3_clccfc_mainlec | relec1122-ml-slw_hc3_clccfc_mainlec | - | 0.6 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-kv3-hgi-v1--cl141fc26e-grt-3172612 | kv3-hgi-v1--cl141fc26e-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3534091 | col_h10_r2__t1 | 5_2_route | 8.8 | drt_violations best 52562 last 52562 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 22.5 | last meaningful line 1.0 h ago (292/293 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3522355 | col_h9_r2__t1 | postcts_gate_TT | 8.8 | last meaningful line 0.0 h ago (675/675 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2916065 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 6.4 | last meaningful line 0.3 h ago (196/205 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-hd_lep0N-1545648 | hd_lep0N | 4_2_tapbal_grt | 7.2 | last meaningful line 5.0 h ago (48/57 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_2_route | 20.7 | last meaningful line 1.0 h ago (289/290 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v7-3747893 | kv3_pv_v7 | 3_3_place_gp | 5.8 | overflow best 0.0999 last 0.0999 rows 43 | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1209290 | ot_s81sl_kv_leaf__t3 | 3_4_place_resized | 1.7 | last meaningful line 0.0 h ago (375/375 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t14-656158 | ot_s81sl_leaf__t14 | 3_5_place_dp | 2.0 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t15-2887177 | ot_s81sl_leaf__t15 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (2598/2598 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t52-3521993 | slice_station__t52 | 5_2_route | 8.8 | last meaningful line 0.5 h ago (261/262 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | 5_1_grt | 7.6 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | 5_1_grt | 7.1 | last meaningful line 0.1 h ago (175/175 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 8.9 | drt_violations best 344103 last 344103 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel1 | otc-589898-30912 | 589898 | - | 5.0 |  | NO-DATA: no log found |  |
| intel1 | otc-590329-1688 | 590329 | - | 5.0 |  | NO-DATA: no log found |  |
| intel1 | otc-910747-1220 | 910747 | - | 4.8 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 6.2 | last meaningful line 0.5 h ago (293/294 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i1-1606115 | eco_20261122_143408_943433-i1 | 5_2_route | 4.4 | drt_violations best 7877 last 7877 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i1-380897 | eco_20261122_165619_1517073-i1 | 5_2_route | 5.2 | drt_violations best 2914 last 2914 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | 5_2_route | 14.2 | drt_violations best 10074 last 10074 rows 3 | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3384117 | col_h9_r1__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 186769 last 186769 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-1679354 | coll_ftm | 5_2_route | 1.5 | last meaningful line 0.1 h ago (238/239 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_C-1760664 | kv3_hub_C | 2_1_floorplan | 1.4 | last meaningful line 1.0 h ago (1424/1424 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-sle_ctl__cla4f6f12f-2733138 | sle_ctl | 4_1_cts | 3.2 | last meaningful line 0.3 h ago (9176/9176 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 16.2 | drt_violations best 88165 last 88165 rows 2 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc7 | otc-450336-16169 | 450336 | asbuilt.yosys | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | otc-566817-28757 | 566817 | plan_gate_pre | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | otc-72070-30500 | 72070 | asbuilt.yosys | 0.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | otc-813840-7015 | 813840 | ot_bind_native_19ab48db7bec75f37243dabb | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-117687 | col_h9_r0_p6__t1 | 5_2_route | 19.4 | drt_violations best 1645 last 1645 rows 39 | before-window best 5155, window best 1645 | PROGRESS: drt_violations improved 68.1 % in window |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3447267 | sle_hc2 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 72.2 | last meaningful line 1.1 h ago (1616/1616 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3789030 | col_h10_r0_p1__t1 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 8.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_hgi_v5-1464049 | kv3_hgi_v5 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | pregrt_ff_hold | 8.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 11.0 | drt_violations best 13388 last 13388 rows 7 | before-window best 154966, window best 13388 | PROGRESS: drt_violations improved 91.4 % in window |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-78592 | col_h10_r0_p4__t1 | 5_2_route | 18.9 | drt_violations best 1 last 1 rows 51 | before-window best 2121, window best 1 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1919292 | col_h9_r0_p2__t1 | 5_1_grt | 3.3 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 19.4 | drt_violations best 56 last 56 rows 24 | before-window best 34114, window best 56 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 22.8 | drt_violations best 12904 last 12904 rows 15 | before-window best 14242, window best 12904 | PROGRESS: drt_violations improved 9.4 % in window |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 10.3 | drt_violations best 15880 last 15880 rows 14 | before-window best 132034, window best 15880 | PROGRESS: drt_violations improved 88.0 % in window |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 6.2 | last meaningful line 0.6 h ago (12235/12235 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-1144307 | serdes__t1 | 5_1_grt | 3.7 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-native59-274714 | native59 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-184640 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | pregrt_ff_hold | 6.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | pregrt_ff_hold | 6.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-3009482 | slw_fe_v2 | pregrt_ff_hold | 6.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | pregrt_ff_hold | 6.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fw_v3-3096266 | slw_fw_v3 | 5_1_grt | 6.7 | repair_TNS best 0 last 0 rows 19 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | pregrt_ff_hold | 6.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 14.8 | drt_violations best 20 last 71 rows 30 | before-window best 25, window best 20 | PROGRESS: drt_violations improved 20.0 % in window |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_2_route | 22.2 | drt_violations best 24731 last 24731 rows 3 | before-window best 195281, window best 24731 | PROGRESS: drt_violations improved 87.3 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 22.2 | drt_violations best 60023 last 60023 rows 3 | before-window best 210671, window best 60023 | PROGRESS: drt_violations improved 71.5 % in window |  |
| intel1 | dpkit-glue-1559836 | glue | pregrt_ff_hold | 7.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | pregrt_ff_hold | 6.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-tt_ctlm-1686138 | tt_ctlm | pregrt_ff_hold | 7.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 29.7 | drt_violations best 1027 last 2630 rows 26 | before-window best 1120, window best 1027 | PROGRESS: drt_violations improved 8.3 % in window |  |
| intel2 | dpkit-coll_core-3588522 | coll_core | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | 5_2_route | 16.3 | drt_violations best 0 last 0 rows 41 | PROGRESS: drt_violations reached 0 |  |
