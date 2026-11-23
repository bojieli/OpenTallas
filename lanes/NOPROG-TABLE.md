# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 04:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'UNSIGNABLE': 2, 'GRT-LABEL': 12, 'NO-DATA': 32, 'YOUNG': 136, 'EXCLUDED': 1, 'PROGRESS': 36}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-dsdv_slice_c1x_C__t1-2108278 | dsdv_slice_c1x_C__t1 | 5_1_grt | 12.0 | last meaningful line 6.3 h ago (208/217 lines) | NO-PROGRESS: no new non-iteration log line for 6.3 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-hd_lep0N_w-3963146 | hd_lep0N_w | tt_setup_repair_grt | 8.6 | repair_Remaining best 84220 last 84220 rows 103 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -428.22 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3565523 | dsdv_slice_lepe_nh_mus_C__t1 | tt_setup_repair | 5.1 | last meaningful line 0.0 h ago (16/16 lines) | UNSIGNABLE: tt_setup_repair.log latest setup WNS -555.29 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 37.0 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_2_route | 21.5 | drt_violations best 109763 last 109763 rows 1 | before-window best 109763, window best 109763 | NO-PROGRESS: drt_violations best 109763 vs 109763 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-tt_ctlm-1686138 | tt_ctlm | pregrt_ff_hold | 7.8 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | 5_1_grt | 20.4 | grt rounds 2 overflow 5:14057 -> 10:13400 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | 5_1_grt | 20.4 | grt rounds 2 overflow 5:13717 -> 10:12993 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v5-1464049 | kv3_hgi_v5 | 5_1_grt | 5.4 | grt rounds 1 overflow 5:8810 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t25__cl55642d17-3247888 | ot_s81sl_leaf__t25 | 5_1_grt | 9.0 | grt rounds 2 overflow 5:32072 -> 10:20314 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-1430945 | ot_s81sl_leaf__t36 | 5_1_grt | 3.0 | grt rounds 2 overflow 5:8739 -> 10:2535 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t3-56823 | ot_s81sl_leaf__t3 | 5_1_grt | 10.6 | grt rounds 2 overflow 5:1586 -> 10:260 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hg-374537 | kv3_hg | 5_1_grt | 3.2 | grt rounds 1 overflow 5:50766 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_fw_v2__cl69f5e854-2970240 | sle_fw_v2 | 5_1_grt | 7.8 | grt rounds 1 overflow 5:26610 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t3-1028300 | ot_s81sl_kv_leaf__t3 | 5_1_grt | 23.0 | grt rounds 6 overflow 5:805 -> 10:203 -> 15:132 -> 20:64 -> 25:77 -> 30:61 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-1087646 | ot_s81sl_kv_leaf__t4 | 5_1_grt | 22.9 | grt rounds 6 overflow 5:2533 -> 10:1498 -> 15:842 -> 20:584 -> 25:584 -> 30:139 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-3520587 | ot_s81sl_leaf__t53 | 5_1_grt | 9.5 | grt rounds 2 overflow 5:29437 -> 10:25353 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t4-2627853 | dsdv_slice_c1x_C__t4 | 5_1_grt | 19.4 | grt rounds 3 overflow 5:88799 -> 10:83085 -> 15:86608 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-bk-sel--t2-grt-1182863 | bk-sel--t2-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-coll_core-388109 | coll_core | 2_3_floorplan_tapcell | 0.6 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-776600 | hd_lep0N_w | pregrt_ff_hold | 3.0 | repair_TNS best 1.6027e+06 last 1.6027e+06 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-827145 | hd_lep0N_w | pregrt_ff_hold | 3.0 | repair_TNS best 1.62065e+06 last 1.62065e+06 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-891099 | hd_lep0N_w | pregrt_ff_hold | 2.9 | repair_TNS best 1.62065e+06 last 1.62065e+06 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-908756 | hd_lep0N_w | pregrt_ff_hold | 2.9 | repair_TNS best 1.6027e+06 last 1.6027e+06 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-972414 | hd_lep0N_w | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3154/3154 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-hd_st_n4-3814785 | hd_st_n4 | generate_abstract | 3.6 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_st_n4-3877061 | hd_st_n4 | generate_abstract | 3.6 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hroot-740108 | kv3_hroot | 5_2_route | 3.0 | last meaningful line 0.2 h ago (258/259 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | 4_1_cts | 0.3 | last meaningful line -0.0 h ago (4902/4902 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t2-1804332 | ot_s81sl_kv_leaf__t2 | 3_1_place_gp_skip_io | 21.7 | overflow best 0.5054 last 0.5054 rows 76 | YOUNG: stage 0.9 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t43-3642617 | ot_s81sl_leaf__t43 | tt_setup_repair | 1.2 | repair_Violations best 97 last 669 rows 38 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-sle_stm_v2__cl7b3062fa-3029892 | sle_stm_v2 | 6_report | 12.1 | last meaningful line 0.0 h ago (55/55 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t12-4037092 | slice_station__t12 | 5_2_route | 1.0 | last meaningful line 0.0 h ago (213/214 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-1064457-7071 | 1064457 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc10 | otc-1141980-12932 | 1141980 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | otc-1148560-18012 | 1148560 | build_bcast_ref_srx2_hc | 0.1 | last meaningful line 0.0 h ago (713/713 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-1148562-28803 | 1148562 | build_bcast_ref_srx2_hc | 0.1 | last meaningful line 0.0 h ago (713/713 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-1148563-17453 | 1148563 | build_bcast_ref_srx2_hc | 0.1 | last meaningful line 0.0 h ago (713/713 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-1307594-11557 | 1307594 | build_bcast_bcast_srx0_hc | 0.0 | last meaningful line 0.0 h ago (709/709 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-1334497-12738 | 1334497 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | otc-3082835-5546 | 3082835 | - | 4.1 |  | NO-DATA: no log found |  |
| epyc10 | otc-4116113-30783 | 4116113 | gen_lint_yosys | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | otc-965544-27736 | 965544 | asbuilt.yosys | 0.3 | last meaningful line -0.0 h ago (134541/134541 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i2t-933314 | eco_20261122_223531_3628570-i2t | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | so_223643_ff_4634 | so_223643_ff_4634 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (627/627 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | so_223643_tt_4634 | so_223643_tt_4634 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (627/627 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-1820678 | col_h10_r0_p1__t1 | 5_1_grt | 9.8 | last meaningful line 1.0 h ago (214/223 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3789030 | col_h10_r0_p1__t1 | 5_1_grt | 4.1 | last meaningful line 0.0 h ago (159/159 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1379295 | col_h10_r0_p4__t1 | pregrt_ff_hold | 3.0 | repair_TNS best 144649 last 144649 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-2470572 | col_h9_r1__t1 | 5_2_route | 9.5 | drt_violations best 85064 last 85064 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-3069419 | dsdv_slice_c1x_C__t3 | 1_1_yosys_canonicalize | 1.8 | last meaningful line 0.5 h ago (131/131 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_mu_C__t1-3116985 | dsdv_slice_lepe_mu_C__t1 | 5_1_grt | 9.1 | last meaningful line 4.0 h ago (207/215 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 8.7 | repair_TNS best 16226.9 last 16226.9 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_2_route | 5.4 | drt_violations best 22132 last 22132 rows 2 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-3921528 | kv3_hroot | 5_2_route | 4.0 | drt_violations best 88466 last 88466 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v3n-1352817 | kv3_pv_v3n | 3_4_place_resized | 5.4 | last meaningful line 0.5 h ago (779/779 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4n-420301 | kv3_pv_v4n | 3_5_place_dp | 5.9 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 9.8 | last meaningful line 0.3 h ago (280/281 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | 5_2_route | 12.1 | last meaningful line 0.3 h ago (289/290 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | 5_2_route | 12.0 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | 5_2_route | 12.0 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-1247578 | sle_st_a_v2 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | 5_2_route | 12.0 | last meaningful line 0.3 h ago (287/288 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | 5_1_grt | 9.6 | last meaningful line 0.2 h ago (274/952 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 8.6 | drt_violations best 71122 last 71122 rows 3 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 9.0 | drt_violations best 62246 last 62246 rows 4 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | fixqcstabtw-cled_w3 | fixqcstabtw-cled_w3 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | otc-2186430-24000 | 2186430 | - | 5.0 |  | NO-DATA: no log found |  |
| epyc2 | otc-2438095-32195 | 2438095 | - | 2.3 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261122_164248_3895049-i1-2533130 | eco_20261122_164248_3895049-i1 | 5_2_route | 4.8 | last meaningful line 0.3 h ago (279/280 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164521_3948325-i1-2180646 | eco_20261122_164521_3948325-i1 | 5_2_route | 5.0 | drt_violations best 735 last 735 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i1-2037456 | eco_20261122_181101_3945375-i1 | 5_2_route | 2.6 | last meaningful line 0.3 h ago (133/133 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i1-2840670 | eco_20261122_190506_3875261-i1 | 5_2_route | 2.0 | last meaningful line 0.0 h ago (12/12 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-slw-st-a-v2--cl9f076a5c-grt-2202551 | slw-st-a-v2--cl9f076a5c-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | tt_setup_repair | 2.3 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-836163 | col_h9_r0_p5__t1 | 5_1_grt | 3.9 | last meaningful line 0.3 h ago (210/214 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | pregrt_ff_hold | 2.4 | repair_TNS best 155482 last 155482 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3134610 | dsdv_slice_kv512_C__t1 | tt_setup_repair | 2.3 | last meaningful line 0.0 h ago (610/610 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_st_n4-1251911 | hd_st_n4 | 6_report | 3.6 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_st_n4-2829569 | hd_st_n4 | 5_2_route | 2.5 | drt_violations best 20698 last 20698 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v1-1064320 | kv3_pv_v1 | 3_5_place_dp | 3.7 | last meaningful line 0.3 h ago (57/57 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2-603007 | kv3_pv_v2 | 3_5_place_dp | 4.1 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | 5_2_route | 13.8 | drt_violations best 135433 last 135433 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | 5_2_route | 14.7 | drt_violations best 21393 last 21393 rows 2 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv4242de79-2254069 | sle_st_a_v2 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 14.7 | drt_violations best 409476 last 409476 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl9beb65e6-3994155 | slw_stm_v2 | 5_2_route | 13.3 | drt_violations best 8184 last 8184 rows 2 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | otc-1330851-9544 | 1330851 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc7 | otc-1839228-30982 | 1839228 | signoff_20261123_103406_1530301 | 0.3 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | otc-2058048-13390 | 2058048 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | otc-2208645-12245 | 2208645 | qwen_compute.t.slw_hc0__cl4f54b7a3__pvd0aa3ddc | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | otc-2268556-32067 | 2268556 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | otc-2287405-27505 | 2287405 | signoff | 2.9 | last meaningful line 2.8 h ago (3/3 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | otc-3970901-4095 | 3970901 | - | 4.8 |  | NO-DATA: no log found |  |
| epyc7 | otc-4110793-30116 | 4110793 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261122_215654_330309-i2-3585488 | eco_20261122_215654_330309-i2 | 5_2_route | 2.0 | last meaningful line 0.1 h ago (256/257 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_220050_168828-i2-2223567 | eco_20261122_220050_168828-i2 | 5_2_route | 3.0 | drt_violations best 4066 last 4066 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_080018_715668-i1t-847605 | eco_20261123_080018_715668-i1t | 5_1_grt | 3.9 | repair_Viol best 2444 last 2444 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc7 | so_2063480_ff_38282 | so_2063480_ff_38282 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | so_2063480_tt_38282 | so_2063480_tt_38282 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-cbf_q00__cl1b5a6458-757482 | cbf_q00 | 3_4_place_resized | 1.4 | last meaningful line 0.1 h ago (20/20 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q11-815128 | cbf_q11 | 3_5_place_dp | 1.3 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1919292 | col_h9_r0_p2__t1 | tt_setup_repair_grt | 4.3 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2000675 | col_h9_r0_p2__t1 | 5_2_route | 9.9 | drt_violations best 136200 last 136200 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-2217964 | col_h9_r2__t1 | 5_2_route | 9.8 | last meaningful line 0.3 h ago (277/278 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t1-2205610 | dsdv_slice_c1x_C__t1 | 3_3_place_gp | 4.2 | overflow best 0.634 last 0.634 rows 24 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t8-1783469 | dsdv_slice_c1x_C__t8 | 3_3_place_gp | 4.4 | overflow best 0.6532 last 0.6532 rows 24 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-1930297 | dsdv_slice_kv512_C__t1 | 5_1_grt | 4.3 | last meaningful line 1.0 h ago (210/213 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2088472 | dsdv_slice_lepe_nh_mus_C__t1 | 5_1_grt | 9.8 | last meaningful line 0.1 h ago (160/160 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-glue-555250 | glue | 5_2_route | 12.3 | drt_violations best 82647 last 82647 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (3779/3779 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hgi_v2__cle0015330-3042686 | kv3_hgi_v2 | tt_setup_repair | 0.4 | repair_Violations best 631 last 631 rows 6 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_hgi_v5-2058350 | kv3_hgi_v5 | 3_3_place_gp | 0.8 | overflow best 0.2723 last 0.3424 rows 24 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-kv3_hub_Ei-494270 | kv3_hub_Ei | 5_2_route | 12.3 | drt_violations best 91531 last 91531 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-619668 | kv3_io_cor_v1 | generate_abstract | 6.6 | last meaningful line 0.1 h ago (1028/1028 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pc_v1__cl7f648944-2054469 | kv3_pc_v1 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (5417/5417 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pc_v1__cl7f648944-628689 | kv3_pc_v1 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (5436/5436 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v12-2069688 | kv3_pv_v12 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (9194/9195 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-164511 | kv3_pv_v6 | 3_5_place_dp | 6.7 | last meaningful line 0.3 h ago (141/141 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-1144307 | serdes__t1 | tt_setup_repair_grt | 4.7 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | relec1122-ml-slw_hc3_cld86_mainlec | relec1122-ml-slw_hc3_cld86_mainlec | - | 1.4 |  | NO-DATA: no log found |  |
| epyc8 | so_3702310_ff_54404 | so_3702310_ff_54404 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc8 | so_3702310_tt_54404 | so_3702310_tt_54404 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2103226 | col_h10_r2__t1 | 5_2_route | 5.5 | drt_violations best 51230 last 51230 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | 5_1_grt | 9.8 | last meaningful line 0.0 h ago (195/195 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-3178195 | hd_ctl | postcts_gate_TT | 4.8 | last meaningful line 0.0 h ago (490/490 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 3.9 | repair_TNS best 309828 last 309828 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v2n-2681030 | kv3_pv_v2n | 3_5_place_dp | 5.1 | last meaningful line 1.0 h ago (57/57 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v4-2911509 | kv3_pv_v4 | 3_4_place_resized | 5.0 | last meaningful line 0.8 h ago (714/714 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v5n-250741 | kv3_pv_v5n | 3_3_place_gp | 3.9 | overflow best 0.1 last 0.1 rows 42 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v6n-2406851 | kv3_pv_v6n | pregrt_ff_hold | 5.3 | repair_TNS best 421499 last 421499 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-184640 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 4.0 | repair_TNS best 11631.3 last 11631.3 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 7.8 | repair_Remaining best 354110 last 354110 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t33-1533302 | ot_s81sl_leaf__t33 | 5_1_grt | 3.1 | last meaningful line 0.5 h ago (206/211 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t68-124972 | ot_s81sl_leaf__t68 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (153/153 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t6__cl0755c26e-2749197 | slice_station__t6 | generate_abstract | 5.1 | last meaningful line 0.0 h ago (188/188 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_1_grt | 7.0 | last meaningful line 0.2 h ago (139/139 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-3009482 | slw_fe_v2 | 5_1_grt | 7.8 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | 5_1_grt | 7.0 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v3-3096266 | slw_fw_v3 | postcts_gate_FF | 7.7 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | lrc-qgrt-1761852 | lrc-qgrt | - | 0.3 |  | NO-DATA: no log found |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 5.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-2062537-15369 | 2062537 | - | 2.9 |  | NO-DATA: no log found |  |
| epyc9 | otc-2908826-5237 | 2908826 | - | 2.3 |  | NO-DATA: no log found |  |
| epyc9 | otc-2909264-658 | 2909264 | - | 2.3 |  | NO-DATA: no log found |  |
| epyc9 | otc-3778865-25787 | 3778865 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i1-454593 | eco-i1 | 5_2_route | 3.8 | drt_violations best 3399 last 3399 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i3t-3335435 | eco_20261122_180231_342380-i3t | 5_2_route | 2.0 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | prd-residual-i4r-2209462 | residual-i4r | 5_2_route | 2.8 | drt_violations best 41 last 41 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | pvr7-pv8-hifo-3975570 | pvr7-pv8-hifo | - | 1.6 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-coll_s_base_mainlec | relec1122-ml-coll_s_base_mainlec | - | 1.6 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-coll_s_eco_mainlec | relec1122-ml-coll_s_eco_mainlec | - | 1.6 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-slw_hc3_clccfc_mainlec | relec1122-ml-slw_hc3_clccfc_mainlec | - | 1.6 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3408616 | col_h10_r0_p1__t1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.3393 last 0.3393 rows 34 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3534091 | col_h10_r2__t1 | 5_2_route | 9.5 | drt_violations best 52562 last 52562 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 23.2 | last meaningful line 0.5 h ago (296/297 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3522355 | col_h9_r2__t1 | 5_2_route | 9.5 | last meaningful line 0.1 h ago (263/263 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2916065 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 7.1 | last meaningful line 0.0 h ago (197/201 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-hd_lep0N-1545648 | hd_lep0N | 4_2_tapbal_grt | 7.9 | last meaningful line 5.8 h ago (48/58 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v1__cl141fc26e-3953955 | kv3_hgi_v1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (2376/2376 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v7-3747893 | kv3_pv_v7 | 3_3_place_gp | 6.5 | overflow best 0.0999 last 0.0999 rows 43 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t15-2887177 | ot_s81sl_leaf__t15 | 5_1_grt | 1.1 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | 5_1_grt | 7.1 | last meaningful line 0.2 h ago (141/141 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t52-3521993 | slice_station__t52 | 5_2_route | 9.5 | last meaningful line 0.5 h ago (265/266 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | 5_1_grt | 8.3 | last meaningful line 0.2 h ago (211/864 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | 5_1_grt | 7.8 | last meaningful line 0.6 h ago (250/892 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 9.6 | drt_violations best 344103 last 344103 rows 1 | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel1 | otc-3494356-28288 | 3494356 | gen_lint_yosys | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | otc-589898-30912 | 589898 | - | 5.8 |  | NO-DATA: no log found |  |
| intel1 | otc-590329-1688 | 590329 | - | 5.8 |  | NO-DATA: no log found |  |
| intel1 | otc-910747-1220 | 910747 | - | 5.6 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 6.9 | last meaningful line 0.2 h ago (297/298 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i1-1606115 | eco_20261122_143408_943433-i1 | 5_2_route | 5.1 | drt_violations best 7877 last 7877 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | prd-fin-380897 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (86/86 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p1__t1__cl911743eb-1964442 | col_h10_r0_p1__t1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3465/3465 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-1679354 | coll_ftm | generate_abstract | 2.5 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_hgi_v3-1994888 | kv3_hgi_v3 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5826/5826 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_C-1760664 | kv3_hub_C | 2_1_floorplan | 2.4 | last meaningful line 2.0 h ago (1424/1424 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-673287 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5487 last 5487 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t2-1999785 | ot_s81sl_leaf__t2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3992/3992 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t66-2007143 | ot_s81sl_leaf__t66 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3721/3721 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-sle_su_c-2423739 | sle_su_c | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (87/87 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-3681497 | slw_fw_v3 | generate_abstract | 17.3 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-slw_su_l1__clcc9d0155-2150277 | slw_su_l1 | 3_5_place_dp | 0.2 | last meaningful line 0.0 h ago (119/119 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-2335892-7062 | 2335892 | asbuilt.yosys | 0.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-hd_st_n4-158454 | hd_st_n4 | 5_1_grt | 0.8 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t73-3464910 | ot_s81sl_leaf__t73 | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3447267 | sle_hc2 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-3135509 | sle_stm_v1 | 5_1_grt | 4.1 | repair_TNS best 0 last 0 rows 10 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 7.1 | drt_violations best 25896 last 25896 rows 4 | before-window best 154752, window best 25896 | PROGRESS: drt_violations improved 83.3 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 73.2 | last meaningful line 0.6 h ago (1618/1618 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 9.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_hgi_v4-1845670 | kv3_hgi_v4 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-775509 | sle_ctl | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | 5_1_grt | 9.8 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 12.0 | drt_violations best 12997 last 12997 rows 8 | before-window best 154966, window best 12997 | PROGRESS: drt_violations improved 91.6 % in window |  |
| epyc7 | dpkit-hd_lep0N_w-3305132 | hd_lep0N_w | tt_setup_repair | 2.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 9.7 | drt_violations best 71216 last 71216 rows 5 | before-window best 311954, window best 71216 | PROGRESS: drt_violations improved 77.2 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 20.4 | drt_violations best 53 last 53 rows 27 | before-window best 2512, window best 53 | PROGRESS: drt_violations improved 97.9 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 23.8 | drt_violations best 9545 last 9545 rows 16 | before-window best 14242, window best 9545 | PROGRESS: drt_violations improved 33.0 % in window |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 11.3 | drt_violations best 15247 last 15247 rows 15 | before-window best 49073, window best 15247 | PROGRESS: drt_violations improved 68.9 % in window |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 7.2 | last meaningful line 0.8 h ago (12263/12263 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-2008589 | sle_su_l1 | 5_1_grt | 4.3 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_1_grt | 7.9 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 5.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-native59-274714 | native59 | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | pregrt_ff_hold | 7.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | pregrt_ff_hold | 7.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 15.8 | drt_violations best 20 last 71 rows 30 | before-window best 21, window best 20 | PROGRESS: drt_violations improved 4.8 % in window |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_2_route | 23.0 | drt_violations best 24731 last 24731 rows 3 | before-window best 195281, window best 24731 | PROGRESS: drt_violations improved 87.3 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 23.0 | drt_violations best 40912 last 40912 rows 4 | before-window best 210671, window best 40912 | PROGRESS: drt_violations improved 80.6 % in window |  |
| intel1 | dpkit-glue-1559836 | glue | pregrt_ff_hold | 7.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 30.4 | drt_violations best 1027 last 1512 rows 27 | before-window best 1120, window best 1027 | PROGRESS: drt_violations improved 8.3 % in window |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | 5_2_route | 15.2 | drt_violations best 950 last 950 rows 11 | before-window best 105374, window best 950 | PROGRESS: drt_violations improved 99.1 % in window |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3384117 | col_h9_r1__t1 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-coll_core-3588522 | coll_core | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_ctl__cla4f6f12f-2733138 | sle_ctl | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 17.2 | drt_violations best 64401 last 64401 rows 3 | before-window best 327883, window best 64401 | PROGRESS: drt_violations improved 80.4 % in window |  |
| intel2 | dpkit-slw_su_l1__clcc9d0155-1330098 | slw_su_l1 | pregrt_ff_hold | 0.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
