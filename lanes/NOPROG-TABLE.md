# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 06:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 2, 'GRT-LABEL': 13, 'YOUNG': 116, 'NO-DATA': 11, 'PROGRESS': 34}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | tt_setup_repair_grt | 22.4 | repair_Violations best 180 last 180 rows 13 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -958.63 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 39.0 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel1 | dpkit-hd_lep0N-1545648 | hd_lep0N | 4_2_tapbal_grt | 10.2 | last meaningful line 8.0 h ago (48/61 lines) | NO-PROGRESS: no new non-iteration log line for 8.0 h | REPORT-ONLY: lane-own kit (FABLE-FIX-HEAD-LEP0N de |
| epyc10 | dpkit-hd_lep0N_w-827145 | hd_lep0N_w | 5_1_grt | 5.0 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | 5_1_grt | 22.4 | grt rounds 2 overflow 5:14057 -> 10:13400 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-1820678 | col_h10_r0_p1__t1 | 5_1_grt | 11.8 | grt rounds 2 overflow 5:66325 -> 10:332 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-dsdv_slice_lepe_mu_C__t1-3116985 | dsdv_slice_lepe_mu_C__t1 | 5_1_grt | 11.1 | grt rounds 2 overflow 5:73744 -> 10:60760 | GRT-LABEL: DESIGN-FAIL: overflow 60760 at round 10 > 1000 |  |
| epyc2 | dpkit-kv3_hgi_v4-1845670 | kv3_hgi_v4 | 5_1_grt | 4.7 | grt rounds 2 overflow 5:17703 -> 10:15924 | GRT-LABEL: DESIGN-FAIL: overflow 15924 at round 10 > 1000 |  |
| epyc2 | dpkit-kv3_hgi_v5-1464049 | kv3_hgi_v5 | 5_1_grt | 7.4 | grt rounds 2 overflow 5:8810 -> 10:2851 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2378761 | col_h10_r2__t1 | 5_1_grt | 1.9 | grt rounds 1 overflow 5:8235 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-slw_st_a_v2__cl9f076a5c-3050099 | slw_st_a_v2 | 5_1_grt | 1.4 | grt rounds 2 overflow 5:6512 -> 10:1487 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hg-374537 | kv3_hg | 5_1_grt | 5.2 | grt rounds 2 overflow 5:50766 -> 10:35686 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_pc_v1__cl7f648944-2054469 | kv3_pc_v1 | 5_1_grt | 2.8 | grt rounds 1 overflow 5:34385 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_pc_v1__cl7f648944-628689 | kv3_pc_v1 | 5_1_grt | 3.4 | grt rounds 1 overflow 5:34385 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-3009482 | slw_fe_v2 | 5_1_grt | 9.8 | grt rounds 2 overflow 5:50921 -> 10:4569 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2916065 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 9.4 | grt rounds 2 overflow 5:53 -> 10:3 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-2755880 | coll_core | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (7186/7186 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-3843742 | coll_core | 4_1_cts | 0.1 | last meaningful line -0.0 h ago (4370/4370 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-2013982 | dsdv_slice_c1x_C__t5 | 1_1_yosys_canonicalize | 1.6 | last meaningful line 0.7 h ago (129/129 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-2955109 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-776600 | hd_lep0N_w | 5_1_grt | 5.0 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-908756 | hd_lep0N_w | 5_1_grt | 4.9 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-972414 | hd_lep0N_w | pregrt_ff_hold | 2.2 | repair_TNS best 1.67794e+06 last 1.67794e+06 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-hd_st_n4-158454 | hd_st_n4 | 5_2_route | 2.8 | drt_violations best 20698 last 20698 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hroot-740108 | kv3_hroot | 5_2_route | 5.0 | drt_violations best 4 last 4 rows 27 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | 4_1_cts | 2.2 | last meaningful line 0.1 h ago (6587/6587 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | 4_1_cts | 2.3 | last meaningful line 0.1 h ago (6817/6817 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t14-3747062 | ot_s81sl_leaf__t14 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (55/55 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t14-3857880 | ot_s81sl_leaf__t14 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t43-3642617 | ot_s81sl_leaf__t43 | 5_1_grt | 3.2 | last meaningful line 1.2 h ago (211/219 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3447267 | sle_hc2 | 5_1_grt | 5.8 | last meaningful line 0.2 h ago (955/982 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-3135509 | sle_stm_v1 | 5_2_route | 6.1 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | otc-1479473-28803 | 1479473 | 4_1_cts | 1.9 | last meaningful line 0.1 h ago (6817/6817 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | otc-3660088-27839 | 3660088 | 4_1_cts | 0.3 | last meaningful line -0.0 h ago (4381/4381 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i2t-933314 | eco_20261122_223531_3628570-i2t | 5_2_route | 2.3 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_130918_3027414-i1t-3090789 | eco_20261123_130918_3027414-i1t | 5_1_grt | 0.8 | last meaningful line 0.4 h ago (293/1426 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-kv3-pv-v4-grt-3369389 | kv3-pv-v4-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3789030 | col_h10_r0_p1__t1 | 5_1_grt | 6.1 | last meaningful line 0.0 h ago (162/162 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-3069419 | dsdv_slice_c1x_C__t3 | 3_5_place_dp | 3.8 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 11.8 | repair_Violations best 1339 last 1339 rows 43 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 10.7 | last meaningful line 0.3 h ago (211/213 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-hd_turn_a-3322258 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (203/203 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_2_route | 7.4 | drt_violations best 1674 last 1674 rows 12 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-3921528 | kv3_hroot | 5_2_route | 6.0 | drt_violations best 28 last 28 rows 14 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 2_1_floorplan | 1.2 | last meaningful line 0.5 h ago (1424/1424 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v3n-1352817 | kv3_pv_v3n | 3_5_place_dp | 7.4 | last meaningful line 0.2 h ago (142/142 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4n-420301 | kv3_pv_v4n | 3_5_place_dp | 7.9 | last meaningful line 0.3 h ago (141/141 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_sys_c-3141298 | kv3_sys_c | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3403/3403 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 11.8 | drt_violations best 112571 last 112571 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | 5_2_route | 14.1 | drt_violations best 133507 last 133507 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | 5_2_route | 14.0 | drt_violations best 116694 last 116694 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | 5_2_route | 14.0 | last meaningful line 0.2 h ago (281/282 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | 5_2_route | 14.0 | drt_violations best 136566 last 136566 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | postcts_gate_TT | 11.8 | last meaningful line -0.0 h ago (44729/44729 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | postcts_gate_TT | 11.6 | last meaningful line 0.2 h ago (844/844 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | eco-abs-3439078 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.0 h ago (556/556 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164248_3895049-i1-2533130 | eco_20261122_164248_3895049-i1 | 5_2_route | 6.8 | drt_violations best 520 last 520 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i1-2037456 | eco_20261122_181101_3945375-i1 | 5_2_route | 4.6 | last meaningful line 0.3 h ago (280/281 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i1-2840670 | eco_20261122_190506_3875261-i1 | 5_2_route | 4.0 | last meaningful line 0.3 h ago (281/282 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-3719549 | col_h10_r2__t1 | 5_2_route | 0.8 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2684878 | col_h10_r2__t1 | 5_2_route | 1.7 | drt_violations best 59992 last 59992 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | pregrt_ff_hold | 4.3 | repair_TNS best 325624 last 325624 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-4013616 | col_h9_r1__t1 | pregrt_ff_hold | 0.6 | repair_TNS best 41003 last 41003 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | postcts_gate_TT | 4.4 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3134610 | dsdv_slice_kv512_C__t1 | 5_1_grt | 4.3 | last meaningful line 0.2 h ago (211/212 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-3305132 | hd_lep0N_w | pregrt_ff_hold | 4.2 | repair_TNS best 280411 last 280411 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-3723533 | hd_lep0N_w | 4_2_tapbal_grt | 0.8 | last meaningful line 0.5 h ago (46/75 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12-2749349 | kv3_pv_v12 | 2_4_floorplan_pdn | 1.7 | last meaningful line 0.0 h ago (105/105 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t47-3969309 | ot_s81sl_leaf__t47 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (4444/4444 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | 5_2_route | 15.8 | drt_violations best 19791 last 19791 rows 3 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__cl5ea486db-3692640 | sle_su_l1 | pregrt_ff_hold | 0.9 | repair_TNS best 1.23426e+06 last 1.23426e+06 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-slice_station__t12-3876359 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (224/225 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | otc-1839228-30982 | 1839228 | signoff_20261123_103406_1530301 | 2.3 | last meaningful line 2.3 h ago (3/3 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | otc-4110793-30116 | 4110793 | - | 3.6 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261123_080018_715668-i1t-847605 | eco_20261123_080018_715668-i1t | 5_2_route | 5.9 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_124118_879330-i1t-3256093 | eco_20261123_124118_879330-i1t | 5_2_route | 1.3 | last meaningful line 0.1 h ago (264/264 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_135114_3991595-i1-291376 | eco_20261123_135114_3991595-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | so_4165023_ff_40280 | so_4165023_ff_40280 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc7 | so_4165023_tt_40280 | so_4165023_tt_40280 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2000675 | col_h9_r0_p2__t1 | 5_2_route | 11.9 | drt_violations best 23400 last 23400 rows 2 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t1-2480825 | dsdv_slice_c1x_C__t1 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-1930297 | dsdv_slice_kv512_C__t1 | 5_1_grt | 6.3 | last meaningful line 3.0 h ago (210/217 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2088472 | dsdv_slice_lepe_nh_mus_C__t1 | 5_1_grt | 11.8 | last meaningful line 1.8 h ago (211/216 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 2.5 | repair_TNS best 651175 last 651175 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc8 | dpkit-kv3_hub_Ei-494270 | kv3_hub_Ei | generate_abstract | 14.3 | last meaningful line 0.2 h ago (1027/1027 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 4_1_cts | 2.2 | last meaningful line 0.0 h ago (6692/6692 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v12-2069688 | kv3_pv_v12 | 4_1_cts | 2.8 | last meaningful line 0.0 h ago (9547/9547 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (9439/9439 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-2008589 | sle_su_l1 | 5_2_route | 6.3 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | otc-2806500-6764 | 2806500 | gen_lint_yosys | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i1t-50076 | eco_20261123_120225_75582-i1t | 5_2_route | 1.9 | last meaningful line 0.2 h ago (285/286 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | relec1122-ml-slw_hc3_cld86_mainlec | relec1122-ml-slw_hc3_cld86_mainlec | - | 3.4 |  | NO-DATA: no log found |  |
| epyc8 | so_3166296_ff_29518 | so_3166296_ff_29518 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc8 | so_3166296_tt_29518 | so_3166296_tt_29518 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 9.9 | last meaningful line 0.3 h ago (282/283 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | 5_1_grt | 11.8 | last meaningful line 1.8 h ago (216/219 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc9 | dpkit-kv3_io_ft-3613880 | kv3_io_ft | 5_2_route | 0.7 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v5n-250741 | kv3_pv_v5n | 3_5_place_dp | 5.9 | last meaningful line 0.1 h ago (57/57 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v6n-2406851 | kv3_pv_v6n | pregrt_ff_hold | 7.3 | repair_TNS best 421499 last 421499 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t2-3529641 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 0.8 | last meaningful line 0.0 h ago (59/59 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-184640 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 6.0 | repair_Remaining best 353925 last 353925 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 9.8 | repair_TNS best 14009.3 last 14009.3 rows 9 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | 5_1_grt | 7.0 | last meaningful line 0.7 h ago (257/1097 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | 5_1_grt | 9.8 | last meaningful line 0.2 h ago (214/973 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_1_grt | 9.0 | repair_TNS best 63808.9 last 63808.9 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | 5_1_grt | 6.0 | repair_TNS best 2018.77 last 2018.77 rows 9 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | 5_1_grt | 9.0 | last meaningful line 0.1 h ago (1131/1144 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v3-3096266 | slw_fw_v3 | 5_2_route | 9.7 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | 5_1_grt | 9.8 | last meaningful line 0.1 h ago (1021/1027 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-tt_ctlm-3940590 | tt_ctlm | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 7.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-3778865-25787 | 3778865 | - | 3.7 |  | NO-DATA: no log found |  |
| epyc9 | prd-count-p1_tc-454593 | count-p1_tc | prd_count_p1_tc | 0.3 | last meaningful line 0.0 h ago (259/259 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i3-411680 | eco_20261122_180231_342380-i3 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | relec1122-ml-coll_s_base_mainlec | relec1122-ml-coll_s_base_mainlec | - | 3.6 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-coll_s_eco_mainlec | relec1122-ml-coll_s_eco_mainlec | - | 3.6 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3522355 | col_h9_r2__t1 | 5_2_route | 11.8 | drt_violations best 56749 last 56749 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-coll_ftm-625194 | coll_ftm | 5_2_route | 1.7 | last meaningful line 0.0 h ago (227/228 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-hd_lep0N-571931 | hd_lep0N | 3_3_place_gp | 1.7 | overflow best 0.3534 last 0.3582 rows 23 | YOUNG: stage 1.0 h < 1 h |  |
| intel1 | dpkit-kv3_hg_v3-419971 | kv3_hg_v3 | 3_3_place_gp | 1.8 | overflow best 0.2089 last 0.2089 rows 36 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-kv3_hgi_v1__cl141fc26e-3953955 | kv3_hgi_v1 | 5_1_grt | 2.4 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v8-589744 | kv3_hgi_v8 | tt_setup_repair | 1.7 | last meaningful line 0.0 h ago (293/293 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-1958034 | kv3_hroot | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3123/3123 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3e-280312 | kv3_pv_v3e | 4_1_cts | 1.9 | last meaningful line 0.3 h ago (7041/7041 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v7-3747893 | kv3_pv_v7 | 3_4_place_resized | 8.8 | last meaningful line 1.7 h ago (655/655 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-468236 | ot_s81sl_kv_leaf__t4 | 3_4_place_resized | 1.8 | last meaningful line 0.0 h ago (355/355 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | 5_1_grt | 9.4 | last meaningful line 1.2 h ago (224/1067 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t52-3521993 | slice_station__t52 | 5_2_route | 11.8 | drt_violations best 31401 last 31401 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | postcts_gate_FF | 10.6 | last meaningful line -0.0 h ago (77902/77902 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | postcts_gate_TT | 10.1 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-2284446-22092 | 2284446 | orfs_synth | 0.2 | last meaningful line 0.2 h ago (308/308 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i2t-304945 | eco_20261122_165619_1517073-i2t | 5_2_route | 1.9 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | so_2369062_ff_13933 | so_2369062_ff_13933 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (66/66 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | so_2369062_tt_13933 | so_2369062_tt_13933 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (66/66 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p1__t1__cl911743eb-1964442 | col_h10_r0_p1__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 102070 last 102070 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3384117 | col_h9_r1__t1 | 5_1_grt | 5.8 | last meaningful line 0.2 h ago (1314/2397 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_C-1760664 | kv3_hub_C | 2_4_floorplan_pdn | 4.4 | last meaningful line 0.7 h ago (175/175 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t2-1999785 | ot_s81sl_leaf__t2 | 5_1_grt | 2.3 | last meaningful line 0.1 h ago (157/157 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t66-2007143 | ot_s81sl_leaf__t66 | 5_1_grt | 2.3 | last meaningful line 0.3 h ago (207/210 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-sle_ctl__cla4f6f12f-2733138 | sle_ctl | 5_1_grt | 6.2 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | ot-ucfvf-probe-2672355 | ot-ucfvf-probe | otrun | 2.0 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel2 | otc-1366248-15461 | 1366248 | build_s81_srx7_m2_ns3_hc_xs | 0.2 | last meaningful line 0.2 h ago (737/737 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i1t-694865 | eco_20261123_051704_3678821-i1t | 5_1_grt | 0.7 | last meaningful line 0.1 h ago (290/321 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2518163 | cbf_q00 | pregrt_ff_hold | 1.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-hd_lep0N_w-891099 | hd_lep0N_w | pregrt_ff_hold | 4.9 | repair_Violations best 0 last 0 rows 14 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 9.1 | drt_violations best 23327 last 23327 rows 7 | before-window best 154752, window best 23327 | PROGRESS: drt_violations improved 84.9 % in window |  |
| epyc10 | prd-eco_20261123_075519_12410-i1-1416585 | eco_20261123_075519_12410-i1 | 5_2_route | 2.0 | drt_violations best 0 last 0 rows 1 | PROGRESS: drt_violations reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 75.2 | last meaningful line 0.9 h ago (1620/1620 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1379295 | col_h10_r0_p4__t1 | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-775509 | sle_ctl | pregrt_ff_hold | 7.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 14.0 | drt_violations best 12416 last 12416 rows 10 | before-window best 16338, window best 12416 | PROGRESS: drt_violations improved 24.0 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 10.6 | drt_violations best 52441 last 52441 rows 7 | before-window best 167955, window best 52441 | PROGRESS: drt_violations improved 68.8 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 11.0 | drt_violations best 56852 last 56852 rows 8 | before-window best 168344, window best 56852 | PROGRESS: drt_violations improved 66.2 % in window |  |
| epyc7 | dpkit-kv3_hroot-3875194 | kv3_hroot | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 16.7 | drt_violations best 54811 last 54811 rows 3 | before-window best 409476, window best 54811 | PROGRESS: drt_violations improved 86.6 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 11.7 | drt_violations best 66623 last 66623 rows 8 | before-window best 311954, window best 66623 | PROGRESS: drt_violations improved 78.6 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 22.4 | drt_violations best 39 last 39 rows 31 | before-window best 115, window best 39 | PROGRESS: drt_violations improved 66.1 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 25.8 | drt_violations best 7732 last 18575 rows 18 | before-window best 13260, window best 7732 | PROGRESS: drt_violations improved 41.7 % in window |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 13.3 | drt_violations best 15104 last 15104 rows 16 | before-window best 24545, window best 15104 | PROGRESS: drt_violations improved 38.5 % in window |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 9.2 | last meaningful line 0.3 h ago (12338/12338 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-hd_ctl-3178195 | hd_ctl | 5_2_route | 6.8 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 7.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 5.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-native59-274714 | native59 | pregrt_ff_hold | 5.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_2_route | 25.2 | drt_violations best 22 last 23 rows 31 | before-window best 195281, window best 22 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3534091 | col_h10_r2__t1 | 5_2_route | 11.8 | drt_violations best 5921 last 5921 rows 3 | before-window best 52562, window best 5921 | PROGRESS: drt_violations improved 88.7 % in window |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 25.5 | drt_violations best 175829 last 175829 rows 1 | before-window best 175829, window best 175829 | PROGRESS: drt_violations: active iteration at 134949 < best completed total 175829 (in-ite |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 25.2 | drt_violations best 38016 last 38016 rows 6 | before-window best 210671, window best 38016 | PROGRESS: drt_violations improved 82.0 % in window |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_2_route | 23.7 | drt_violations best 109763 last 109763 rows 1 | before-window best 109763, window best 109763 | PROGRESS: drt_violations: active iteration at 71179 < best completed total 109763 (in-iter |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 11.9 | drt_violations best 132000 last 132000 rows 3 | before-window best 344103, window best 132000 | PROGRESS: drt_violations improved 61.6 % in window |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 32.7 | drt_violations best 1027 last 1232 rows 29 | before-window best 1064, window best 1027 | PROGRESS: drt_violations improved 3.5 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 9.2 | drt_violations best 90237 last 90237 rows 1 | before-window best 90237, window best 90237 | PROGRESS: drt_violations: active iteration at 49755 < best completed total 90237 (in-itera |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | 5_2_route | 17.2 | drt_violations best 0 last 0 rows 43 | PROGRESS: drt_violations reached 0 |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2731145 | col_h10_r1__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-coll_core-3588522 | coll_core | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-kv3_hgi_v3-1994888 | kv3_hgi_v3 | pregrt_ff_hold | 2.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 19.2 | drt_violations best 7994 last 7994 rows 7 | before-window best 327883, window best 7994 | PROGRESS: drt_violations improved 97.6 % in window |  |
