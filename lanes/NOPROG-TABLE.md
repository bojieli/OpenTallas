# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 07:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 1, 'GRT-LABEL': 8, 'YOUNG': 110, 'NO-DATA': 10, 'PROGRESS': 32}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N_w-891099 | hd_lep0N_w | tt_setup_repair_grt | 5.9 | repair_Viol best 4372 last 4372 rows 26 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -343.30 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 40.0 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc10 | dpkit-hd_lep0N_w-776600 | hd_lep0N_w | 5_1_grt | 6.0 | grt rounds 2 overflow 5:3636 -> 10:1908 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_lep0N_w-908756 | hd_lep0N_w | 5_1_grt | 5.9 | grt rounds 2 overflow 5:3636 -> 10:1908 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | 5_1_grt | 23.4 | grt rounds 2 overflow 5:14057 -> 10:13400 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-slw_st_a_v2__cl9f076a5c-3050099 | slw_st_a_v2 | 5_1_grt | 2.4 | grt rounds 2 overflow 5:6512 -> 10:1487 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_pc_v1__cl7f648944-2054469 | kv3_pc_v1 | 5_1_grt | 3.8 | grt rounds 2 overflow 5:34385 -> 10:29676 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-3009482 | slw_fe_v2 | 5_1_grt | 10.8 | grt rounds 2 overflow 5:50921 -> 10:4569 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2916065 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 10.4 | grt rounds 2 overflow 5:53 -> 10:3 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl141fc26e-3953955 | kv3_hgi_v1 | 5_1_grt | 3.4 | grt rounds 2 overflow 5:6611 -> 10:4392 | GRT-LABEL: DESIGN-FAIL: overflow 4392 at round 10 > 1000 |  |
| epyc10 | dpkit-coll_core-2755880 | coll_core | pregrt_ff_hold | 2.0 | last meaningful line 0.1 h ago (43/43 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-3843742 | coll_core | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (7369/7369 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-552955 | coll_core | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (182/182 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-2013982 | dsdv_slice_c1x_C__t5 | 3_3_place_gp | 2.6 | overflow best 0.6546 last 0.6546 rows 26 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-2955109 | dsdv_slice_c1x_C__t8 | 4_1_cts | 1.9 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-972414 | hd_lep0N_w | pregrt_ff_hold | 3.2 | repair_TNS best 1.67794e+06 last 1.67794e+06 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hroot-740108 | kv3_hroot | 6_report | 6.0 | last meaningful line 0.0 h ago (74/74 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | pregrt_ff_hold | 3.2 | repair_TNS best 144781 last 144781 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 3.3 | repair_TNS best 351658 last 351658 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t14-3747062 | ot_s81sl_leaf__t14 | pregrt_ff_hold | 1.2 | repair_TNS best 148206 last 148206 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t14-3857880 | ot_s81sl_leaf__t14 | pregrt_ff_hold | 1.1 | repair_TNS best 202607 last 202607 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3447267 | sle_hc2 | postcts_gate_TT | 6.8 | last meaningful line 0.0 h ago (780/780 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-3135509 | sle_stm_v1 | 5_2_route | 7.1 | drt_violations best 80958 last 80958 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | otc-1479473-28803 | 1479473 | pregrt_ff_hold | 2.9 | repair_TNS best 351658 last 351658 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i2t-933314 | eco_20261122_223531_3628570-i2t | 5_2_route | 3.3 | drt_violations best 1436 last 1436 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_130918_3027414-i1t-3090789 | eco_20261123_130918_3027414-i1t | 5_2_route | 1.8 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | so_922033_ff_31091 | so_922033_ff_31091 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (373/373 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | so_922033_tt_31091 | so_922033_tt_31091 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (373/373 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-kv3-pv-v3n-grt-433964 | kv3-pv-v3n-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3789030 | col_h10_r0_p1__t1 | 5_1_grt | 7.1 | last meaningful line 0.8 h ago (219/226 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1379295 | col_h10_r0_p4__t1 | 5_1_grt | 6.0 | last meaningful line 0.1 h ago (162/162 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-204646 | dsdv_slice_c1x_C__t3 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 12.8 | last meaningful line 0.1 h ago (161/161 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 11.7 | last meaningful line 1.3 h ago (211/215 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-3921528 | kv3_hroot | 6_report | 7.0 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 2_1_floorplan | 2.2 | last meaningful line 1.5 h ago (1424/1424 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 12.8 | drt_violations best 22046 last 22046 rows 3 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-775509 | sle_ctl | 5_1_grt | 8.7 | last meaningful line 0.3 h ago (170/170 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | 5_2_route | 15.0 | drt_violations best 116694 last 116694 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | 5_2_route | 15.0 | drt_violations best 110443 last 110443 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | 5_2_route | 15.0 | drt_violations best 136566 last 136566 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | postcts_gate_FF | 12.8 | last meaningful line -0.0 h ago (94747/94747 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | 5_2_route | 12.6 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-count-p1_tc-2533130 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i1-2037456 | eco_20261122_181101_3945375-i1 | 5_2_route | 5.6 | drt_violations best 32 last 32 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i1-2840670 | eco_20261122_190506_3875261-i1 | 5_2_route | 5.0 | drt_violations best 312 last 312 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | so_218733_ff_54147 | so_218733_ff_54147 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (562/562 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | so_218733_tt_54147 | so_218733_tt_54147 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (562/562 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-3719549 | col_h10_r2__t1 | 5_2_route | 1.8 | drt_violations best 57589 last 57589 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2378761 | col_h10_r2__t1 | 5_2_route | 2.9 | last meaningful line 0.0 h ago (262/262 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2684878 | col_h10_r2__t1 | 5_2_route | 2.7 | drt_violations best 9949 last 9949 rows 2 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | pregrt_ff_hold | 5.3 | repair_TNS best 325624 last 325624 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | 5_2_route | 5.4 | last meaningful line 0.3 h ago (270/271 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3134610 | dsdv_slice_kv512_C__t1 | 5_1_grt | 5.3 | last meaningful line 1.2 h ago (211/214 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-1246550 | hd_lep0N | 4_1_cts | 0.3 | last meaningful line 0.2 h ago (24/24 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-3305132 | hd_lep0N_w | pregrt_ff_hold | 5.2 | repair_TNS best 351.902 last 351.902 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-3723533 | hd_lep0N_w | pregrt_ff_hold | 1.8 | repair_Violations best 145 last 145 rows 6 | YOUNG: stage 0.8 h < 1 h |  |
| epyc7 | dpkit-kv3_hroot-3875194 | kv3_hroot | postcts_gate_TT | 1.7 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12-2749349 | kv3_pv_v12 | 3_3_place_gp | 2.7 | overflow best 0.6567 last 0.6567 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | 6_report | 16.8 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | otc-4110793-30116 | 4110793 | - | 4.6 |  | NO-DATA: no log found |  |
| epyc7 | otc-935421-7658 | 935421 | signoff | 0.5 | last meaningful line 0.5 h ago (3/3 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_080018_715668-i1t-847605 | eco_20261123_080018_715668-i1t | 5_2_route | 6.9 | last meaningful line 0.2 h ago (286/287 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_124118_879330-i1t-3256093 | eco_20261123_124118_879330-i1t | 5_2_route | 2.3 | last meaningful line 0.1 h ago (279/280 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_135114_3991595-i1-291376 | eco_20261123_135114_3991595-i1 | 5_2_route | 1.1 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-kv3-hg-v3-grt-1612955 | kv3-hg-v3-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t1-2480825 | dsdv_slice_c1x_C__t1 | postplace_setup | 1.7 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t10-871345 | dsdv_slice_c1x_C__t10 | sdc_lint | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-1930297 | dsdv_slice_kv512_C__t1 | 5_1_grt | 7.3 | last meaningful line 4.0 h ago (210/218 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2088472 | dsdv_slice_lepe_nh_mus_C__t1 | 5_1_grt | 12.8 | last meaningful line 2.8 h ago (211/218 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 3.5 | repair_TNS best 651175 last 651175 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | pregrt_ff_hold | 3.2 | repair_TNS best 360716 last 360716 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-kv3_pc_v1__cl7f648944-628689 | kv3_pc_v1 | postcts_gate_TT | 4.4 | last meaningful line 0.1 h ago (1545/1545 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pc_v3-1745589 | kv3_pc_v3 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v12-2069688 | kv3_pv_v12 | pregrt_ff_hold | 3.8 | repair_TNS best 122362 last 122362 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | 4_1_cts | 1.5 | last meaningful line 1.0 h ago (9439/9439 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-2008589 | sle_su_l1 | 5_2_route | 7.3 | drt_violations best 83643 last 83643 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | otc-1655156-14041 | 1655156 | build_s81_srx8_m0_hc | 0.1 | last meaningful line 0.1 h ago (719/719 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-1660600-6187 | 1660600 | build_s81_srx6_m0_hc_xs_bc | 0.1 | last meaningful line 0.1 h ago (734/734 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-1694738-17551 | 1694738 | build_s81_srx7_m1_ns3_xs_bc | 0.0 | last meaningful line 0.0 h ago (650/650 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-1699467-686 | 1699467 | build_s81_srx7_m3_xs_bc | 0.0 | last meaningful line 0.0 h ago (648/648 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i1t-50076 | eco_20261123_120225_75582-i1t | 5_2_route | 2.9 | drt_violations best 47255 last 47255 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_140713_549985-i1t-81578 | eco_20261123_140713_549985-i1t | 5_2_route | 0.9 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | so_4114470_ff_31805 | so_4114470_ff_31805 | signoff | 0.9 |  | NO-DATA: empty log |  |
| epyc8 | so_4114470_tt_31805 | so_4114470_tt_31805 | signoff | 0.9 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 10.9 | last meaningful line 0.3 h ago (292/293 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | 5_1_grt | 12.8 | last meaningful line 2.8 h ago (216/220 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | 4_1_cts | 0.8 | last meaningful line 0.3 h ago (10548/10548 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v5n-250741 | kv3_pv_v5n | 3_5_place_dp | 6.9 | last meaningful line 0.3 h ago (140/140 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v6n-2406851 | kv3_pv_v6n | pregrt_ff_hold | 8.3 | repair_TNS best 421499 last 421499 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-184640 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 7.0 | repair_Remaining best 353925 last 353925 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 10.8 | last meaningful line 0.1 h ago (416/421 lines) | YOUNG: evidence 5.1 h < 6 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | 5_1_grt | 8.0 | repair_TNS best 2433.47 last 2433.47 rows 5 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | postcts_gate_FF | 10.8 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_1_grt | 10.0 | repair_TNS best 49329.6 last 49329.6 rows 5 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | 5_1_grt | 7.0 | repair_TNS best 172.524 last 172.524 rows 5 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | 5_1_grt | 10.0 | last meaningful line 0.1 h ago (1231/1248 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v3-3096266 | slw_fw_v3 | 5_2_route | 10.7 | last meaningful line 0.1 h ago (288/289 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | postcts_gate_TT | 10.8 | last meaningful line 0.0 h ago (856/856 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-tt_ctlm-889513 | tt_ctlm | tt_setup_repair | 0.7 | repair_Viol best 794 last 794 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 8.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-3778865-25787 | 3778865 | - | 4.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-928970-21237 | 928970 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261122_180231_342380-i3-411680 | eco_20261122_180231_342380-i3 | 5_2_route | 1.0 | last meaningful line 0.0 h ago (266/266 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_142403_3177550-i1t-1010219 | eco_20261123_142403_3177550-i1t | 5_2_route | 0.6 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | relec1122-ml-coll_s_base_mainlec | relec1122-ml-coll_s_base_mainlec | - | 4.6 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-coll_s_eco_mainlec | relec1122-ml-coll_s_eco_mainlec | - | 4.6 |  | NO-DATA: no log found |  |
| epyc9 | so_1559917_ff_25689 | so_1559917_ff_25689 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (235/235 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | so_1559917_tt_25689 | so_1559917_tt_25689 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (235/235 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3522355 | col_h9_r2__t1 | 5_2_route | 12.8 | drt_violations best 56749 last 56749 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-coll_ftm-625194 | coll_ftm | 5_2_route | 2.7 | drt_violations best 10172 last 10172 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-1958034 | kv3_hroot | 5_1_grt | 1.5 | repair_Remaining best 102971 last 102971 rows 17 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v3e-280312 | kv3_pv_v3e | 4_1_cts | 2.9 | last meaningful line 0.3 h ago (7095/7095 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | 5_1_grt | 10.4 | last meaningful line 0.1 h ago (1160/1166 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | 5_2_route | 11.6 | last meaningful line 0.1 h ago (261/262 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | postcts_gate_TT | 11.1 | last meaningful line 0.2 h ago (1529/1529 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | otc-3063185-17309 | 3063185 | orfs_synth | 0.4 | last meaningful line 0.3 h ago (307/307 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i2t-2539626 | eco_20261122_143408_943433-i2t | 5_2_route | 0.9 | last meaningful line 0.0 h ago (249/249 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i2t-304945 | eco_20261122_165619_1517073-i2t | 5_2_route | 2.9 | drt_violations best 15957 last 15957 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p1__t1__cl911743eb-1964442 | col_h10_r0_p1__t1 | 5_1_grt | 3.3 | last meaningful line 0.1 h ago (216/218 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2731145 | col_h10_r1__t1 | 5_1_grt | 3.0 | last meaningful line 0.0 h ago (211/212 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-coll_core-3588522 | coll_core | 5_1_grt | 6.7 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-kv3_hgi_v3-1994888 | kv3_hgi_v3 | 5_1_grt | 3.3 | last meaningful line 0.5 h ago (290/1298 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_C-1760664 | kv3_hub_C | 3_3_place_gp | 5.4 | overflow best 0.5605 last 0.5605 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t2-1999785 | ot_s81sl_leaf__t2 | 5_1_grt | 3.3 | last meaningful line 0.8 h ago (214/220 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t66-2007143 | ot_s81sl_leaf__t66 | 5_1_grt | 3.3 | last meaningful line 1.3 h ago (207/216 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | dpkit-sle_ctl__cla4f6f12f-2733138 | sle_ctl | 5_1_grt | 7.2 | last meaningful line 0.2 h ago (293/1297 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | ot-ucfvf-probe-2672355 | ot-ucfvf-probe | otrun | 3.0 | last meaningful line 2.8 h ago (3/3 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i1t-694865 | eco_20261123_051704_3678821-i1t | 5_2_route | 1.7 | last meaningful line 0.0 h ago (261/261 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i1t-2859676 | eco_20261123_063813_234645-i1t | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (159/159 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2518163 | cbf_q00 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 10.1 | drt_violations best 21706 last 21706 rows 9 | before-window best 154752, window best 21706 | PROGRESS: drt_violations improved 86.0 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 76.2 | last meaningful line 0.6 h ago (1622/1622 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_2_route | 8.4 | drt_violations best 1269 last 1269 rows 16 | before-window best 87459, window best 1269 | PROGRESS: drt_violations improved 98.5 % in window |  |
| epyc2 | dpkit-kv3_sys_c-3141298 | kv3_sys_c | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | 5_2_route | 15.1 | drt_violations best 133507 last 133507 rows 1 | before-window best 133507, window best 133507 | PROGRESS: drt_violations: active iteration at 42248 < best completed total 133507 (in-iter |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 15.0 | drt_violations best 12416 last 12416 rows 10 | before-window best 14532, window best 12416 | PROGRESS: drt_violations improved 14.6 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 11.6 | drt_violations best 51596 last 51596 rows 8 | before-window best 167955, window best 51596 | PROGRESS: drt_violations improved 69.3 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 12.0 | drt_violations best 56276 last 56276 rows 9 | before-window best 168344, window best 56276 | PROGRESS: drt_violations improved 66.6 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-4013616 | col_h9_r1__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t47-3969309 | ot_s81sl_leaf__t47 | pregrt_ff_hold | 1.6 | repair_Violations best 0 last 0 rows 15 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-sle_su_l1__cl5ea486db-3692640 | sle_su_l1 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 17.7 | drt_violations best 259 last 259 rows 13 | before-window best 409476, window best 259 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 12.7 | drt_violations best 65992 last 65992 rows 9 | before-window best 311954, window best 65992 | PROGRESS: drt_violations improved 78.8 % in window |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2000675 | col_h9_r0_p2__t1 | 5_2_route | 12.9 | drt_violations best 25 last 25 rows 15 | before-window best 136200, window best 25 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 23.4 | drt_violations best 38 last 38 rows 35 | before-window best 75, window best 38 | PROGRESS: drt_violations improved 49.3 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 26.8 | drt_violations best 7732 last 18575 rows 18 | before-window best 12904, window best 7732 | PROGRESS: drt_violations improved 40.1 % in window |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 14.3 | drt_violations best 14710 last 63695 rows 18 | before-window best 18065, window best 14710 | PROGRESS: drt_violations improved 18.6 % in window |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 10.2 | last meaningful line 0.3 h ago (12529/12529 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 8.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 6.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-native59-274714 | native59 | pregrt_ff_hold | 6.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_2_route | 26.2 | drt_violations best 11 last 11 rows 56 | before-window best 195281, window best 11 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 26.5 | drt_violations best 175829 last 175829 rows 1 | before-window best 175829, window best 175829 | PROGRESS: drt_violations: active iteration at 102111 < best completed total 175829 (in-ite |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 26.2 | drt_violations best 37704 last 37704 rows 7 | before-window best 71586, window best 37704 | PROGRESS: drt_violations improved 47.3 % in window |  |
| intel1 | dpkit-kv3_hgi_v8-589744 | kv3_hgi_v8 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_2_route | 24.7 | drt_violations best 109763 last 109763 rows 1 | before-window best 109763, window best 109763 | PROGRESS: drt_violations: active iteration at 50296 < best completed total 109763 (in-iter |  |
| intel1 | dpkit-slice_station__t52-3521993 | slice_station__t52 | 5_2_route | 12.8 | drt_violations best 31401 last 31401 rows 1 | before-window best 31401, window best 31401 | PROGRESS: drt_violations: active iteration at 6879 < best completed total 31401 (in-iterat |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 12.9 | drt_violations best 132000 last 132000 rows 3 | before-window best 344103, window best 132000 | PROGRESS: drt_violations improved 61.6 % in window |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 33.7 | drt_violations best 1027 last 1170 rows 30 | before-window best 1060, window best 1027 | PROGRESS: drt_violations improved 3.1 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 10.2 | drt_violations best 90237 last 90237 rows 1 | before-window best 90237, window best 90237 | PROGRESS: drt_violations: active iteration at 29205 < best completed total 90237 (in-itera |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 20.2 | drt_violations best 5930 last 5930 rows 10 | before-window best 327883, window best 5930 | PROGRESS: drt_violations improved 98.2 % in window |  |
