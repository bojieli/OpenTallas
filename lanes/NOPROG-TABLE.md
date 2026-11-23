# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 05:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'GRT-LABEL': 8, 'NO-DATA': 19, 'YOUNG': 134, 'PROGRESS': 31}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 38.2 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 17.0 | drt_violations best 20 last 43 rows 31 | before-window best 20, window best 20 | NO-PROGRESS: drt_violations best 20 vs 20 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-glue-1559836 | glue | pregrt_ff_hold | 9.2 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-hd_lep0N-1545648 | hd_lep0N | 4_2_tapbal_grt | 9.2 | last meaningful line 7.0 h ago (48/60 lines) | NO-PROGRESS: no new non-iteration log line for 7.0 h | REPORT-ONLY: lane-own kit (FABLE-FIX-HEAD-LEP0N de |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | 5_1_grt | 21.4 | grt rounds 2 overflow 5:14057 -> 10:13400 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | 5_1_grt | 21.4 | grt rounds 2 overflow 5:13717 -> 10:12993 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-1820678 | col_h10_r0_p1__t1 | 5_1_grt | 11.0 | grt rounds 2 overflow 5:66325 -> 10:332 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v5-1464049 | kv3_hgi_v5 | 5_1_grt | 6.7 | grt rounds 2 overflow 5:8810 -> 10:2851 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hg-374537 | kv3_hg | 5_1_grt | 4.5 | grt rounds 1 overflow 5:50766 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_pc_v1__cl7f648944-628689 | kv3_pc_v1 | 5_1_grt | 2.7 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_fw_v2__cl69f5e854-2970240 | sle_fw_v2 | 5_1_grt | 9.0 | grt rounds 1 overflow 5:26610 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-3009482 | slw_fe_v2 | 5_1_grt | 9.0 | grt rounds 2 overflow 5:50921 -> 10:4569 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-dsdv-slice-c1x-C--t8-grt-2688608 | dsdv-slice-c1x-C--t8-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2518163 | cbf_q00 | 4_1_cts | 0.2 | last meaningful line -0.0 h ago (5560/5560 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-2347400 | coll_core | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (382/382 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-2755880 | coll_core | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-2013982 | dsdv_slice_c1x_C__t5 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-827145 | hd_lep0N_w | pregrt_ff_hold | 4.0 | repair_TNS best 20.349 last 20.349 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-891099 | hd_lep0N_w | pregrt_ff_hold | 3.9 | repair_TNS best 20.349 last 20.349 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-972414 | hd_lep0N_w | 4_2_tapbal_grt | 1.2 | last meaningful line 0.8 h ago (46/117 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-hd_st_n4-158454 | hd_st_n4 | 5_2_route | 1.8 | last meaningful line 0.1 h ago (236/237 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hroot-740108 | kv3_hroot | 5_2_route | 4.0 | drt_violations best 88466 last 88466 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (6479/6480 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | 4_1_cts | 1.3 | last meaningful line 0.2 h ago (6637/6637 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_sys_c-2134137 | kv3_sys_c | 3_3_place_gp | 0.5 | overflow best 0.4024 last 0.4024 rows 35 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t14-1920992 | ot_s81sl_leaf__t14 | 3_3_place_gp | 0.7 | last meaningful line 0.2 h ago (86/86 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t14-1945276 | ot_s81sl_leaf__t14 | 3_3_place_gp | 0.7 | last meaningful line 0.2 h ago (86/86 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t43-3642617 | ot_s81sl_leaf__t43 | 5_1_grt | 2.2 | last meaningful line 0.2 h ago (211/214 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t73-3464910 | ot_s81sl_leaf__t73 | 5_1_grt | 2.3 | last meaningful line 0.3 h ago (213/219 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-3135509 | sle_stm_v1 | postcts_gate_TT | 5.1 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-1479473-28803 | 1479473 | 4_1_cts | 0.9 | last meaningful line 0.2 h ago (6637/6637 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | otc-2561382-26273 | 2561382 | port_bind | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i2t-933314 | eco_20261122_223531_3628570-i2t | 5_2_route | 1.3 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_075519_12410-i1-1416585 | eco_20261123_075519_12410-i1 | 5_2_route | 1.0 | last meaningful line 0.1 h ago (248/249 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | so_2272376_ff_77902 | so_2272376_ff_77902 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc10 | so_2272376_tt_77902 | so_2272376_tt_77902 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3789030 | col_h10_r0_p1__t1 | 5_1_grt | 5.3 | last meaningful line 0.8 h ago (219/225 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1379295 | col_h10_r0_p4__t1 | pregrt_ff_hold | 4.3 | repair_TNS best 144649 last 144649 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-3069419 | dsdv_slice_c1x_C__t3 | 3_3_place_gp | 3.1 | overflow best 0.7191 last 0.7217 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_mu_C__t1-3116985 | dsdv_slice_lepe_mu_C__t1 | 5_1_grt | 10.4 | last meaningful line 5.3 h ago (207/216 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 9.9 | last meaningful line 0.2 h ago (159/159 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v4-1845670 | kv3_hgi_v4 | 5_1_grt | 4.0 | last meaningful line 0.0 h ago (213/219 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_2_route | 6.7 | drt_violations best 2013 last 2013 rows 10 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-3921528 | kv3_hroot | 5_2_route | 5.2 | drt_violations best 20504 last 20504 rows 2 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 2_1_floorplan | 0.4 | repair_Viol best 1787 last 1787 rows 1315 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-kv3_pv_v3n-1352817 | kv3_pv_v3n | 3_5_place_dp | 6.7 | last meaningful line 0.5 h ago (59/59 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4n-420301 | kv3_pv_v4n | 3_5_place_dp | 7.2 | last meaningful line 1.0 h ago (58/58 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 11.0 | drt_violations best 112571 last 112571 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | 5_2_route | 13.3 | drt_violations best 133507 last 133507 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | 5_2_route | 13.3 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | 5_2_route | 13.3 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | 5_2_route | 13.3 | drt_violations best 136566 last 136566 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | postcts_gate_TT | 11.1 | last meaningful line 0.0 h ago (417/417 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | postcts_gate_TT | 10.9 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 9.9 | drt_violations best 54860 last 54860 rows 5 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc2 | otc-2438095-32195 | 2438095 | - | 3.6 |  | NO-DATA: no log found |  |
| epyc2 | prd-count-p1_tc-2180646 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (551/551 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164248_3895049-i1-2533130 | eco_20261122_164248_3895049-i1 | 5_2_route | 6.1 | drt_violations best 520 last 520 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i1-2037456 | eco_20261122_181101_3945375-i1 | 5_2_route | 3.9 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i1-2840670 | eco_20261122_190506_3875261-i1 | 5_2_route | 3.2 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-col-h9-r1--t1--cl49d7a23e--pv4bd36c74-grt-3818436 | col-h9-r1--t1--cl49d7a23e--pv4bd36c74-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-ot-s81sl-leaf--t47-grt-3767611 | ot-s81sl-leaf--t47-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-3719549 | col_h10_r2__t1 | tt_setup_repair_grt | 0.1 | repair_Viol best 2100 last 2100 rows 90 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2378761 | col_h10_r2__t1 | 5_1_grt | 1.2 | repair_Remaining best 70183 last 70183 rows 39 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2684878 | col_h10_r2__t1 | 5_2_route | 1.0 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | pregrt_ff_hold | 3.6 | repair_TNS best 325624 last 325624 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | 5_1_grt | 3.7 | last meaningful line 0.2 h ago (261/1272 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3134610 | dsdv_slice_kv512_C__t1 | 5_1_grt | 3.5 | last meaningful line 0.0 h ago (158/158 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-3305132 | hd_lep0N_w | pregrt_ff_hold | 3.4 | repair_TNS best 1.67794e+06 last 1.67794e+06 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-3723533 | hd_lep0N_w | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2815/2815 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12-2749349 | kv3_pv_v12 | 2_1_floorplan | 0.9 | last meaningful line 0.5 h ago (431/431 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2-603007 | kv3_pv_v2 | 3_5_place_dp | 5.3 | last meaningful line 0.3 h ago (138/138 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | 5_2_route | 15.0 | drt_violations best 135433 last 135433 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | 6_report | 16.0 | last meaningful line 0.2 h ago (1073/1073 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__cl5ea486db-3692640 | sle_su_l1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3536/3536 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 15.9 | drt_violations best 85945 last 85945 rows 2 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v2__cl9f076a5c-3050099 | slw_st_a_v2 | pregrt_ff_hold | 0.7 | repair_Violations best 3050 last 3050 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | eco-abs-3750647 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.0 h ago (367/367 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | otc-1839228-30982 | 1839228 | signoff_20261123_103406_1530301 | 1.6 | last meaningful line 1.5 h ago (3/3 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | otc-2287405-27505 | 2287405 | signoff | 4.2 | last meaningful line 4.1 h ago (3/3 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc7 | otc-3692928-8394 | 3692928 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | otc-4110793-30116 | 4110793 | - | 2.9 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261123_080018_715668-i1t-847605 | eco_20261123_080018_715668-i1t | 5_1_grt | 5.1 | repair_Viol best 2444 last 2444 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_124118_879330-i1t-3256093 | eco_20261123_124118_879330-i1t | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (297/982 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | so_3698103_ff_29934 | so_3698103_ff_29934 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | so_3698103_tt_29934 | so_3698103_tt_29934 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | ap-ageom-kw-kv3-pv-v6-grt-2260034 | kv3-pv-v6-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2000675 | col_h9_r0_p2__t1 | 5_2_route | 11.1 | drt_violations best 136200 last 136200 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-2217964 | col_h9_r2__t1 | 5_2_route | 11.0 | drt_violations best 52429 last 52429 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-1930297 | dsdv_slice_kv512_C__t1 | 5_1_grt | 5.6 | last meaningful line 2.2 h ago (210/216 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2088472 | dsdv_slice_lepe_nh_mus_C__t1 | 5_1_grt | 11.1 | last meaningful line 1.0 h ago (211/215 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-glue-555250 | glue | 6_report | 13.5 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hgi_v2__cle0015330-3042686 | kv3_hgi_v2 | 5_1_grt | 1.7 | last meaningful line 0.2 h ago (287/1293 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-494270 | kv3_hub_Ei | 6_report | 13.6 | last meaningful line 0.1 h ago (1073/1073 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (6524/6524 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pc_v1__cl7f648944-2054469 | kv3_pc_v1 | 5_1_grt | 2.1 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v12-2069688 | kv3_pv_v12 | 4_1_cts | 2.1 | last meaningful line 0.2 h ago (9255/9255 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-2008589 | sle_su_l1 | 5_2_route | 5.5 | last meaningful line 0.1 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i1t-50076 | eco_20261123_120225_75582-i1t | 5_2_route | 1.2 | last meaningful line 0.1 h ago (274/274 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | relec1122-ml-slw_hc3_cld86_mainlec | relec1122-ml-slw_hc3_cld86_mainlec | - | 2.7 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 9.2 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | 5_1_grt | 11.0 | last meaningful line 1.0 h ago (216/218 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-3178195 | hd_ctl | 5_2_route | 6.1 | drt_violations best 57207 last 57207 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 5.2 | repair_TNS best 309828 last 309828 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v2n-2681030 | kv3_pv_v2n | 3_5_place_dp | 6.4 | last meaningful line 0.5 h ago (140/140 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v4-2911509 | kv3_pv_v4 | 3_5_place_dp | 6.2 | last meaningful line 0.3 h ago (140/140 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v5n-250741 | kv3_pv_v5n | 3_4_place_resized | 5.2 | last meaningful line 0.3 h ago (730/730 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v6n-2406851 | kv3_pv_v6n | pregrt_ff_hold | 6.5 | repair_TNS best 421499 last 421499 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t2-3529641 | ot_s81sl_kv_leaf__t2 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-184640 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 5.2 | repair_Remaining best 237925 last 237925 rows 117 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 9.1 | last meaningful line 2.8 h ago (240/284 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t68-124972 | ot_s81sl_leaf__t68 | 5_1_grt | 2.7 | last meaningful line 0.0 h ago (1844/1859 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | 5_1_grt | 6.3 | last meaningful line 0.2 h ago (226/232 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_1_grt | 8.3 | last meaningful line 0.7 h ago (221/1386 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | 5_1_grt | 5.3 | repair_Remaining best 198382 last 198382 rows 242 | YOUNG: stage 1.0 h < 1 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | 5_1_grt | 8.2 | last meaningful line 0.5 h ago (227/1102 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v3-3096266 | slw_fw_v3 | postcts_gate_FF | 8.9 | last meaningful line -0.0 h ago (50103/50103 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | 5_1_grt | 9.0 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 7.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-2062537-15369 | 2062537 | - | 4.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-2908826-5237 | 2908826 | - | 3.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-3778865-25787 | 3778865 | - | 3.0 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i1-454593 | eco-i1 | 5_2_route | 5.1 | drt_violations best 3399 last 3399 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i3t-3335435 | eco_20261122_180231_342380-i3t | 5_2_route | 3.3 | drt_violations best 1119 last 1119 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | relec1122-ml-coll_s_base_mainlec | relec1122-ml-coll_s_base_mainlec | - | 2.9 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-coll_s_eco_mainlec | relec1122-ml-coll_s_eco_mainlec | - | 2.9 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3534091 | col_h10_r2__t1 | 5_2_route | 10.8 | drt_violations best 52562 last 52562 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3522355 | col_h9_r2__t1 | 5_2_route | 10.8 | last meaningful line 0.3 h ago (274/275 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-coll_ftm-625194 | coll_ftm | 5_1_grt | 0.7 | repair_Remaining best 27817 last 27817 rows 22 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2916065 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 8.4 | last meaningful line 0.8 h ago (299/1200 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-hd_lep0N-571931 | hd_lep0N | 3_1_place_gp_skip_io | 0.7 | overflow best 0.1131 last 0.1131 rows 47 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-hd_lep0N_w-549280 | hd_lep0N_w | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (66/66 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v3-419971 | kv3_hg_v3 | 2_4_floorplan_pdn | 0.8 | last meaningful line 0.0 h ago (537/537 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v8-589744 | kv3_hgi_v8 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (5022/5022 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-257843 | kv3_hroot | 3_3_place_gp | 1.0 | overflow best 0.0995 last 0.0995 rows 50 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v3e-280312 | kv3_pv_v3e | 4_1_cts | 0.9 | last meaningful line 0.3 h ago (6701/6701 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v7-3747893 | kv3_pv_v7 | 3_4_place_resized | 7.8 | last meaningful line 0.7 h ago (655/655 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-468236 | ot_s81sl_kv_leaf__t4 | 2_1_floorplan | 0.8 | repair_Viol best 1304 last 1304 rows 1203 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t15-2887177 | ot_s81sl_leaf__t15 | 5_1_grt | 2.4 | last meaningful line 1.0 h ago (262/1272 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | 5_1_grt | 8.4 | repair_Remaining best 363944 last 363944 rows 101 | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l1__cl5ea486db-385423 | sle_su_l1 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t52-3521993 | slice_station__t52 | 5_2_route | 10.8 | drt_violations best 31401 last 31401 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | postcts_gate_TT | 9.6 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | 5_1_grt | 9.1 | last meaningful line 0.2 h ago (986/1001 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | otc-1203716-17036 | 1203716 | build_s81_srx0_m0_hc | 0.2 | last meaningful line 0.0 h ago (704/704 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-1203721-7697 | 1203721 | build_s81_srx0_m0_hc | 0.2 | last meaningful line 0.0 h ago (704/704 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-1203725-25567 | 1203725 | build_s81_srx0_m0_hc | 0.2 | last meaningful line 0.0 h ago (704/704 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-1227372-31463 | 1227372 | build_bcast_mut_srx7_hc_t | 0.2 | last meaningful line 0.2 h ago (721/721 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-1282470-7526 | 1282470 | build_s81_srx0_m0_hc | 0.2 | last meaningful line 0.2 h ago (704/704 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-1283467-9734 | 1283467 | build_s81_srx7_m3_hc_xs_bc | 0.2 | last meaningful line 0.2 h ago (729/729 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-586875-1941 | 586875 | orfs_synth | 0.7 | last meaningful line 0.5 h ago (4254/4254 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 8.2 | drt_violations best 90237 last 90237 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i1-1606115 | eco_20261122_143408_943433-i1 | 5_2_route | 6.4 | drt_violations best 32 last 32 rows 11 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i2t-304945 | eco_20261122_165619_1517073-i2t | 5_2_route | 0.9 | last meaningful line 0.0 h ago (259/259 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p1__t1__cl911743eb-1964442 | col_h10_r0_p1__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 102070 last 102070 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2731145 | col_h10_r1__t1 | pregrt_ff_hold | 1.2 | repair_TNS best 49096.2 last 49096.2 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3384117 | col_h9_r1__t1 | 5_1_grt | 5.1 | last meaningful line 0.2 h ago (265/1270 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_C-1760664 | kv3_hub_C | 2_4_floorplan_pdn | 3.7 | last meaningful line 0.0 h ago (174/174 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t66-2007143 | ot_s81sl_leaf__t66 | pregrt_ff_hold | 1.5 | repair_TNS best 6978.38 last 6978.38 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-sle_su_c-2423739 | sle_su_c | 3_3_place_gp | 1.3 | overflow best 0.0992 last 0.0992 rows 50 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | ot-ucfvf-probe-2672355 | ot-ucfvf-probe | otrun | 1.2 | last meaningful line 1.1 h ago (3/3 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | otc-462241-3564 | 462241 | build_s81_srx0_m0_hc | 0.1 | last meaningful line 0.0 h ago (212/212 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | otc-462242-2943 | 462242 | build_s81_srx0_m0_hc | 0.1 | last meaningful line 0.0 h ago (211/211 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | so_3468167_ff_94007 | so_3468167_ff_94007 | signoff | 0.9 |  | NO-DATA: empty log |  |
| intel2 | so_3468167_tt_94007 | so_3468167_tt_94007 | signoff | 0.9 |  | NO-DATA: empty log |  |
| epyc10 | dpkit-hd_lep0N_w-776600 | hd_lep0N_w | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-hd_lep0N_w-908756 | hd_lep0N_w | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3447267 | sle_hc2 | pregrt_ff_hold | 4.8 | repair_Violations best 0 last 0 rows 7 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 8.1 | drt_violations best 24490 last 24490 rows 6 | before-window best 154752, window best 24490 | PROGRESS: drt_violations improved 84.2 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 74.5 | last meaningful line 0.2 h ago (1620/1620 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 11.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-775509 | sle_ctl | pregrt_ff_hold | 7.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 13.3 | drt_violations best 12793 last 12793 rows 9 | before-window best 35724, window best 12793 | PROGRESS: drt_violations improved 64.2 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 10.3 | drt_violations best 58202 last 58202 rows 6 | before-window best 168344, window best 58202 | PROGRESS: drt_violations improved 65.4 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 10.9 | drt_violations best 67502 last 67502 rows 7 | before-window best 311954, window best 67502 | PROGRESS: drt_violations improved 78.4 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 21.6 | drt_violations best 40 last 40 rows 30 | before-window best 315, window best 40 | PROGRESS: drt_violations improved 87.3 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 25.0 | drt_violations best 9545 last 9545 rows 16 | before-window best 13260, window best 9545 | PROGRESS: drt_violations improved 28.0 % in window |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | tt_setup_repair | 1.8 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 12.5 | drt_violations best 15104 last 15104 rows 16 | before-window best 26889, window best 15104 | PROGRESS: drt_violations improved 43.8 % in window |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 8.5 | last meaningful line 0.8 h ago (12266/12266 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-native59-274714 | native59 | pregrt_ff_hold | 5.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | pregrt_ff_hold | 9.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_2_route | 24.2 | drt_violations best 39 last 39 rows 12 | before-window best 195281, window best 39 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 24.5 | drt_violations best 175829 last 175829 rows 1 | before-window best 175829, window best 175829 | PROGRESS: drt_violations: active iteration at 167714 < best completed total 175829 (in-ite |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 24.2 | drt_violations best 39043 last 39043 rows 5 | before-window best 210671, window best 39043 | PROGRESS: drt_violations improved 81.5 % in window |  |
| intel1 | dpkit-kv3_hgi_v1__cl141fc26e-3953955 | kv3_hgi_v1 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_2_route | 22.7 | drt_violations best 109763 last 109763 rows 1 | before-window best 109763, window best 109763 | PROGRESS: drt_violations: active iteration at 91150 < best completed total 109763 (in-iter |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 10.9 | drt_violations best 151194 last 151194 rows 2 | before-window best 344103, window best 151194 | PROGRESS: drt_violations improved 56.1 % in window |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 31.7 | drt_violations best 1027 last 1402 rows 28 | before-window best 1064, window best 1027 | PROGRESS: drt_violations improved 3.5 % in window |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | 5_2_route | 16.5 | drt_violations best 386 last 386 rows 15 | before-window best 105374, window best 386 | PROGRESS: drt_violations improved 99.6 % in window |  |
| intel2 | dpkit-coll_core-3588522 | coll_core | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-kv3_hgi_v3-1994888 | kv3_hgi_v3 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_leaf__t2-1999785 | ot_s81sl_leaf__t2 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_ctl__cla4f6f12f-2733138 | sle_ctl | pregrt_ff_hold | 5.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 18.5 | drt_violations best 11060 last 11060 rows 5 | before-window best 327883, window best 11060 | PROGRESS: drt_violations improved 96.6 % in window |  |
