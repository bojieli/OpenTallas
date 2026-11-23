# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 05:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 3, 'GRT-LABEL': 12, 'YOUNG': 125, 'NO-DATA': 12, 'EXCLUDED': 1, 'PROGRESS': 35}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | 5_1_grt | 21.9 | grt rounds 2 overflow 5:13717 -> 10:12993 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -594.76 ps (< -300, gate TT >= -42); job age 21 | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 38.5 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 17.3 | drt_violations best 20 last 43 rows 31 | before-window best 20, window best 20 | NO-PROGRESS: drt_violations best 20 vs 20 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-hd_lep0N-1545648 | hd_lep0N | 4_2_tapbal_grt | 9.7 | last meaningful line 7.5 h ago (48/60 lines) | NO-PROGRESS: no new non-iteration log line for 7.5 h | REPORT-ONLY: lane-own kit (FABLE-FIX-HEAD-LEP0N de |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | 5_1_grt | 21.9 | grt rounds 2 overflow 5:14057 -> 10:13400 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-1820678 | col_h10_r0_p1__t1 | 5_1_grt | 11.5 | grt rounds 2 overflow 5:66325 -> 10:332 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3789030 | col_h10_r0_p1__t1 | 5_1_grt | 5.8 | grt rounds 2 overflow 5:89117 -> 10:282 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v5-1464049 | kv3_hgi_v5 | 5_1_grt | 7.2 | grt rounds 2 overflow 5:8810 -> 10:2851 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2378761 | col_h10_r2__t1 | 5_1_grt | 1.4 | grt rounds 1 overflow 5:8235 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hg-374537 | kv3_hg | 5_1_grt | 5.0 | grt rounds 2 overflow 5:50766 -> 10:35686 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_pc_v1__cl7f648944-2054469 | kv3_pc_v1 | 5_1_grt | 2.6 | grt rounds 1 overflow 5:34385 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_pc_v1__cl7f648944-628689 | kv3_pc_v1 | 5_1_grt | 3.2 | grt rounds 1 overflow 5:34385 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_fw_v2__cl69f5e854-2970240 | sle_fw_v2 | 5_1_grt | 9.3 | grt rounds 1 overflow 5:26610 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-3009482 | slw_fe_v2 | 5_1_grt | 9.3 | grt rounds 2 overflow 5:50921 -> 10:4569 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2916065 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 8.9 | grt rounds 2 overflow 5:53 -> 10:3 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t15-2887177 | ot_s81sl_leaf__t15 | 5_1_grt | 2.9 | grt rounds 2 overflow 5:9830 -> 10:1497 | GRT-LABEL: DESIGN-FAIL: overflow 1497 at round 10 > 1000 |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2518163 | cbf_q00 | pregrt_ff_hold | 0.7 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-2347400 | coll_core | 3_4_place_resized | 0.9 | last meaningful line 0.1 h ago (371/371 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-2755880 | coll_core | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (7064/7064 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-2013982 | dsdv_slice_c1x_C__t5 | 1_1_yosys_canonicalize | 1.1 | last meaningful line 0.2 h ago (128/128 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-2955109 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-827145 | hd_lep0N_w | pregrt_ff_hold | 4.5 | repair_TNS best 20.349 last 20.349 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-891099 | hd_lep0N_w | pregrt_ff_hold | 4.4 | repair_TNS best 20.349 last 20.349 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-972414 | hd_lep0N_w | 4_2_tapbal_grt | 1.7 | last meaningful line 0.0 h ago (162/162 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-hd_st_n4-158454 | hd_st_n4 | 5_2_route | 2.3 | drt_violations best 20698 last 20698 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc10 | dpkit-kv3_hroot-740108 | kv3_hroot | 5_2_route | 4.5 | drt_violations best 13291 last 13291 rows 3 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | 4_1_cts | 1.7 | last meaningful line 0.0 h ago (6566/6566 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | 4_1_cts | 1.8 | last meaningful line 0.2 h ago (6640/6640 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t14-1920992 | ot_s81sl_leaf__t14 | 3_5_place_dp | 1.2 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t14-1945276 | ot_s81sl_leaf__t14 | 3_5_place_dp | 1.2 | last meaningful line 0.1 h ago (38/38 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t43-3642617 | ot_s81sl_leaf__t43 | 5_1_grt | 2.7 | last meaningful line 0.7 h ago (211/217 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t73-3464910 | ot_s81sl_leaf__t73 | 5_1_grt | 2.8 | last meaningful line 0.8 h ago (213/222 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3447267 | sle_hc2 | 5_1_grt | 5.3 | last meaningful line 0.2 h ago (220/857 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-3135509 | sle_stm_v1 | 5_2_route | 5.6 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-1479473-28803 | 1479473 | 4_1_cts | 1.4 | last meaningful line 0.2 h ago (6640/6640 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i2t-933314 | eco_20261122_223531_3628570-i2t | 5_2_route | 1.8 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_075519_12410-i1-1416585 | eco_20261123_075519_12410-i1 | 5_2_route | 1.5 | last meaningful line 0.1 h ago (258/259 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_130918_3027414-i1t-3090789 | eco_20261123_130918_3027414-i1t | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (174/174 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1379295 | col_h10_r0_p4__t1 | pregrt_ff_hold | 4.8 | repair_TNS best 144649 last 144649 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-3069419 | dsdv_slice_c1x_C__t3 | 3_3_place_gp | 3.6 | overflow best 0.1991 last 0.1991 rows 42 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 11.5 | last meaningful line 0.1 h ago (1507/1507 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 10.4 | last meaningful line 0.1 h ago (211/212 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v4-1845670 | kv3_hgi_v4 | 5_1_grt | 4.5 | last meaningful line 0.5 h ago (291/1301 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_2_route | 7.2 | drt_violations best 1717 last 1717 rows 11 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-3921528 | kv3_hroot | 5_2_route | 5.7 | drt_violations best 2331 last 2331 rows 4 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 2_1_floorplan | 0.9 | last meaningful line 0.3 h ago (1424/1424 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v3n-1352817 | kv3_pv_v3n | 3_5_place_dp | 7.2 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4n-420301 | kv3_pv_v4n | 3_5_place_dp | 7.7 | last meaningful line 0.2 h ago (141/141 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_sys_c-3141298 | kv3_sys_c | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 11.5 | drt_violations best 112571 last 112571 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | 5_2_route | 13.8 | drt_violations best 133507 last 133507 rows 1 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | 5_2_route | 13.8 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | 5_2_route | 13.8 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | 5_2_route | 13.8 | drt_violations best 136566 last 136566 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | postcts_gate_TT | 11.6 | last meaningful line 0.0 h ago (863/863 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | postcts_gate_TT | 11.4 | last meaningful line 0.1 h ago (838/838 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164248_3895049-i1-2533130 | eco_20261122_164248_3895049-i1 | 5_2_route | 6.6 | drt_violations best 520 last 520 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i1-2037456 | eco_20261122_181101_3945375-i1 | 5_2_route | 4.4 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i1-2840670 | eco_20261122_190506_3875261-i1 | 5_2_route | 3.7 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | prd-fin-2180646 | fin | 6_report | 0.4 | last meaningful line 0.1 h ago (595/595 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-3719549 | col_h10_r2__t1 | 5_2_route | 0.3 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2684878 | col_h10_r2__t1 | 5_2_route | 1.2 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | pregrt_ff_hold | 3.8 | repair_TNS best 325624 last 325624 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-4013616 | col_h9_r1__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2033/2033 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | 5_1_grt | 3.9 | last meaningful line 0.2 h ago (1306/2340 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3134610 | dsdv_slice_kv512_C__t1 | 5_1_grt | 3.8 | last meaningful line 0.3 h ago (159/159 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-3305132 | hd_lep0N_w | pregrt_ff_hold | 3.7 | repair_TNS best 1.67794e+06 last 1.67794e+06 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-3723533 | hd_lep0N_w | 4_2_tapbal_grt | 0.3 | last meaningful line 0.0 h ago (46/50 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hroot-3875194 | kv3_hroot | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3017/3017 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12-2749349 | kv3_pv_v12 | 2_1_floorplan | 1.2 | last meaningful line 0.7 h ago (431/431 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t47-3969309 | ot_s81sl_leaf__t47 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | 5_2_route | 15.3 | drt_violations best 26419 last 26419 rows 2 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | generate_abstract | 16.2 | last meaningful line 0.1 h ago (1030/1030 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__cl5ea486db-3692640 | sle_su_l1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3727/3727 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v2__cl9f076a5c-3050099 | slw_st_a_v2 | 5_1_grt | 0.9 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | otc-1839228-30982 | 1839228 | signoff_20261123_103406_1530301 | 1.8 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | otc-2287405-27505 | 2287405 | signoff | 4.4 | last meaningful line 4.3 h ago (3/3 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | otc-4110793-30116 | 4110793 | - | 3.1 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261123_080018_715668-i1t-847605 | eco_20261123_080018_715668-i1t | 5_1_grt | 5.4 | repair_Viol best 2444 last 2444 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_124118_879330-i1t-3256093 | eco_20261123_124118_879330-i1t | 5_1_grt | 0.8 | last meaningful line 0.5 h ago (297/1478 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | so_3698103_ff_29934 | so_3698103_ff_29934 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc7 | so_3698103_tt_29934 | so_3698103_tt_29934 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc7 | so_4041677_ff_49038 | so_4041677_ff_49038 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (373/373 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | so_4041677_tt_49038 | so_4041677_tt_49038 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (373/373 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-sle-su-c-grt-3302495 | sle-su-c-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2000675 | col_h9_r0_p2__t1 | 5_2_route | 11.6 | drt_violations best 136200 last 136200 rows 1 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-2217964 | col_h9_r2__t1 | 5_2_route | 11.5 | drt_violations best 1393 last 1393 rows 7 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t1-2480825 | dsdv_slice_c1x_C__t1 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-1930297 | dsdv_slice_kv512_C__t1 | 5_1_grt | 6.1 | last meaningful line 2.7 h ago (210/217 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2088472 | dsdv_slice_lepe_nh_mus_C__t1 | 5_1_grt | 11.6 | last meaningful line 1.5 h ago (211/216 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 2.3 | repair_TNS best 651175 last 651175 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-kv3_hub_Ei-494270 | kv3_hub_Ei | generate_abstract | 14.1 | last meaningful line 0.0 h ago (1023/1023 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 4_1_cts | 1.9 | last meaningful line 0.1 h ago (6541/6541 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v12-2069688 | kv3_pv_v12 | 4_1_cts | 2.6 | last meaningful line 0.1 h ago (9275/9275 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (116/116 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-2008589 | sle_su_l1 | 5_2_route | 6.0 | last meaningful line 0.1 h ago (266/267 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | otc-2806500-6764 | 2806500 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i1t-50076 | eco_20261123_120225_75582-i1t | 5_2_route | 1.7 | last meaningful line 0.2 h ago (281/282 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | relec1122-ml-slw_hc3_cld86_mainlec | relec1122-ml-slw_hc3_cld86_mainlec | - | 3.2 |  | NO-DATA: no log found |  |
| epyc8 | so_3166296_ff_29518 | so_3166296_ff_29518 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | so_3166296_tt_29518 | so_3166296_tt_29518 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 9.4 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | 5_1_grt | 11.3 | last meaningful line 1.3 h ago (216/218 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-3178195 | hd_ctl | 5_2_route | 6.3 | drt_violations best 57207 last 57207 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-hd_turn_a-3616336 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (208/209 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v4-2911509 | kv3_pv_v4 | 3_5_place_dp | 6.5 | last meaningful line 0.5 h ago (140/140 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v5n-250741 | kv3_pv_v5n | 3_4_place_resized | 5.4 | last meaningful line 0.5 h ago (730/730 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v6n-2406851 | kv3_pv_v6n | pregrt_ff_hold | 6.8 | repair_TNS best 421499 last 421499 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t2-3529641 | ot_s81sl_kv_leaf__t2 | sdc_lint | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-184640 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 5.5 | last meaningful line 0.0 h ago (157/157 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 9.3 | repair_TNS best 16965.2 last 16965.2 rows 2 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | 5_1_grt | 6.5 | repair_Remaining best 403132 last 403132 rows 61 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | 5_1_grt | 9.3 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_1_grt | 8.5 | repair_TNS best 70917.8 last 70917.8 rows 2 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | 5_1_grt | 5.5 | last meaningful line 0.5 h ago (256/1438 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | 5_1_grt | 8.5 | repair_TNS best 414.387 last 414.387 rows 2 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v3-3096266 | slw_fw_v3 | 5_2_route | 9.2 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | 5_1_grt | 9.3 | repair_Remaining best 440222 last 440222 rows 67 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 7.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-2908826-5237 | 2908826 | - | 3.8 |  | NO-DATA: no log found |  |
| epyc9 | otc-3778865-25787 | 3778865 | - | 3.2 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i1-454593 | eco-i1 | 5_2_route | 5.3 | drt_violations best 3399 last 3399 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i3t-3335435 | eco_20261122_180231_342380-i3t | 5_3_fillcell | 3.5 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | relec1122-ml-coll_s_base_mainlec | relec1122-ml-coll_s_base_mainlec | - | 3.1 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-coll_s_eco_mainlec | relec1122-ml-coll_s_eco_mainlec | - | 3.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3534091 | col_h10_r2__t1 | 5_2_route | 11.3 | drt_violations best 8919 last 8919 rows 2 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3522355 | col_h9_r2__t1 | 5_2_route | 11.3 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-coll_ftm-625194 | coll_ftm | 5_1_grt | 1.2 | last meaningful line 0.1 h ago (398/434 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-hd_lep0N-571931 | hd_lep0N | 3_3_place_gp | 1.2 | last meaningful line 0.2 h ago (196/196 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v3-419971 | kv3_hg_v3 | 3_3_place_gp | 1.3 | last meaningful line 0.0 h ago (50/50 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v8-589744 | kv3_hgi_v8 | 4_1_cts | 1.2 | last meaningful line 0.3 h ago (5053/5053 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3e-280312 | kv3_pv_v3e | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (7011/7012 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v7-3747893 | kv3_pv_v7 | 3_4_place_resized | 8.3 | last meaningful line 1.2 h ago (655/655 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-468236 | ot_s81sl_kv_leaf__t4 | 3_3_place_gp | 1.3 | last meaningful line 0.1 h ago (97/97 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | 5_1_grt | 8.9 | repair_Remaining best 944 last 944 rows 464 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t52-3521993 | slice_station__t52 | 5_2_route | 11.3 | drt_violations best 31401 last 31401 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | postcts_gate_FF | 10.1 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | tt_setup_measure_grt | 9.6 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-1878560-22034 | 1878560 | build_s81_srx7_m2_hc | 0.1 | last meaningful line 0.1 h ago (717/717 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-586875-1941 | 586875 | orfs_synth | 1.2 | last meaningful line 1.0 h ago (4254/4254 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i2t-304945 | eco_20261122_165619_1517073-i2t | 5_2_route | 1.4 | last meaningful line 0.3 h ago (269/270 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p1__t1__cl911743eb-1964442 | col_h10_r0_p1__t1 | pregrt_ff_hold | 2.1 | repair_TNS best 102070 last 102070 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2731145 | col_h10_r1__t1 | pregrt_ff_hold | 1.7 | repair_TNS best 49096.2 last 49096.2 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3384117 | col_h9_r1__t1 | 5_1_grt | 5.6 | last meaningful line 0.7 h ago (265/1289 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_C-1760664 | kv3_hub_C | 2_4_floorplan_pdn | 4.2 | last meaningful line 0.5 h ago (175/175 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t2-1999785 | ot_s81sl_leaf__t2 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t66-2007143 | ot_s81sl_leaf__t66 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (207/208 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | ot-ucfvf-probe-2672355 | ot-ucfvf-probe | otrun | 1.7 | last meaningful line 1.6 h ago (3/3 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | otc-1065664-16963 | 1065664 | build_s81_srx7_m0_ns3_hc_xs | 0.2 | last meaningful line 0.1 h ago (728/728 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | otc-1065666-27373 | 1065666 | build_s81_srx7_m0_ns3_hc_xs | 0.2 | last meaningful line 0.1 h ago (728/728 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | otc-1065668-31905 | 1065668 | build_s81_srx7_m0_ns3_hc_xs | 0.2 | last meaningful line 0.1 h ago (728/728 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | otc-1065669-23446 | 1065669 | build_s81_srx7_m0_ns3_hc_xs | 0.2 | last meaningful line 0.1 h ago (728/728 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i1t-694865 | eco_20261123_051704_3678821-i1t | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (159/159 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | otc-3035397-27334 | 3035397 | - | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-hd_lep0N_w-776600 | hd_lep0N_w | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-hd_lep0N_w-908756 | hd_lep0N_w | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 8.6 | drt_violations best 24490 last 24490 rows 6 | before-window best 154752, window best 24490 | PROGRESS: drt_violations improved 84.2 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 75.0 | last meaningful line 0.6 h ago (1620/1620 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-dsdv_slice_lepe_mu_C__t1-3116985 | dsdv_slice_lepe_mu_C__t1 | 5_1_grt | 10.9 | last meaningful line 5.8 h ago (207/216 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-775509 | sle_ctl | pregrt_ff_hold | 7.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 13.8 | drt_violations best 12416 last 12416 rows 10 | before-window best 35724, window best 12416 | PROGRESS: drt_violations improved 65.2 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 10.4 | drt_violations best 53530 last 53530 rows 6 | before-window best 167955, window best 53530 | PROGRESS: drt_violations improved 68.1 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 10.8 | drt_violations best 57442 last 57442 rows 7 | before-window best 168344, window best 57442 | PROGRESS: drt_violations improved 65.9 % in window |  |
| epyc7 | dpkit-slice_station__t12-3876359 | slice_station__t12 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 16.2 | drt_violations best 85945 last 85945 rows 2 | before-window best 409476, window best 85945 | PROGRESS: drt_violations improved 79.0 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 11.2 | drt_violations best 66623 last 66623 rows 8 | before-window best 311954, window best 66623 | PROGRESS: drt_violations improved 78.6 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 22.1 | drt_violations best 40 last 40 rows 30 | before-window best 234, window best 40 | PROGRESS: drt_violations improved 82.9 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 25.5 | drt_violations best 7732 last 18575 rows 18 | before-window best 13260, window best 7732 | PROGRESS: drt_violations improved 41.7 % in window |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 13.0 | drt_violations best 15104 last 15104 rows 16 | before-window best 26167, window best 15104 | PROGRESS: drt_violations improved 42.3 % in window |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 9.0 | last meaningful line 0.2 h ago (12338/12338 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-kv3_io_ft-3613880 | kv3_io_ft | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 6.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 5.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-native59-274714 | native59 | pregrt_ff_hold | 5.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t68-124972 | ot_s81sl_leaf__t68 | tt_setup_repair_grt | 2.9 | repair_Violations best 0 last 0 rows 20 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_2_route | 24.7 | drt_violations best 25 last 25 rows 16 | before-window best 195281, window best 25 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 25.0 | drt_violations best 175829 last 175829 rows 1 | before-window best 175829, window best 175829 | PROGRESS: drt_violations: active iteration at 153512 < best completed total 175829 (in-ite |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 24.7 | drt_violations best 39043 last 39043 rows 5 | before-window best 210671, window best 39043 | PROGRESS: drt_violations improved 81.5 % in window |  |
| intel1 | dpkit-kv3_hgi_v1__cl141fc26e-3953955 | kv3_hgi_v1 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_2_route | 23.2 | drt_violations best 109763 last 109763 rows 1 | before-window best 109763, window best 109763 | PROGRESS: drt_violations: active iteration at 74899 < best completed total 109763 (in-iter |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 11.4 | drt_violations best 151194 last 151194 rows 2 | before-window best 344103, window best 151194 | PROGRESS: drt_violations improved 56.1 % in window |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 32.2 | drt_violations best 1027 last 1402 rows 28 | before-window best 1064, window best 1027 | PROGRESS: drt_violations improved 3.5 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 8.7 | drt_violations best 90237 last 90237 rows 1 | before-window best 90237, window best 90237 | PROGRESS: drt_violations: active iteration at 62326 < best completed total 90237 (in-itera |  |
| intel1 | prd-eco_20261122_143408_943433-i1-1606115 | eco_20261122_143408_943433-i1 | 5_2_route | 6.9 | drt_violations best 0 last 0 rows 28 | PROGRESS: drt_violations reached 0 |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | 5_2_route | 17.0 | drt_violations best 12 last 12 rows 21 | before-window best 105374, window best 12 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel2 | dpkit-coll_core-3588522 | coll_core | pregrt_ff_hold | 5.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-kv3_hgi_v3-1994888 | kv3_hgi_v3 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_ctl__cla4f6f12f-2733138 | sle_ctl | pregrt_ff_hold | 5.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 19.0 | drt_violations best 9148 last 9148 rows 6 | before-window best 327883, window best 9148 | PROGRESS: drt_violations improved 97.2 % in window |  |
