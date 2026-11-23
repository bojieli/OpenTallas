# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 04:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 2, 'GRT-LABEL': 9, 'YOUNG': 151, 'NO-DATA': 22, 'EXCLUDED': 2, 'PROGRESS': 34}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-3565523 | dsdv_slice_lepe_nh_mus_C__t1 | tt_setup_repair | 5.6 | repair_Violations best 3859 last 3859 rows 70 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -555.29 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 37.5 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc9 | prd-residual-i4r-2209462 | residual-i4r | 5_2_route | 3.3 | drt_violations best 41 last 41 rows 1 | UNSIGNABLE: ECO-FLAT: FF hold -160.51 -> -160.57 ps (gate +0) over the last 2 of 3 sign-off  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-hd_lep0N-1545648 | hd_lep0N | 4_2_tapbal_grt | 8.7 | last meaningful line 6.5 h ago (48/59 lines) | NO-PROGRESS: no new non-iteration log line for 6.5 h | REPORT-ONLY: lane-own kit (FABLE-FIX-HEAD-LEP0N de |
| epyc10 | dpkit-kv3_pc_v3-252670 | kv3_pc_v3 | 5_1_grt | 20.9 | grt rounds 2 overflow 5:14057 -> 10:13400 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc_v3-90293 | kv3_pc_v3 | 5_1_grt | 20.9 | grt rounds 2 overflow 5:13717 -> 10:12993 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-1820678 | col_h10_r0_p1__t1 | 5_1_grt | 10.3 | grt rounds 2 overflow 5:66325 -> 10:332 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v5-1464049 | kv3_hgi_v5 | 5_1_grt | 5.9 | grt rounds 2 overflow 5:8810 -> 10:2851 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-1247578 | sle_st_a_v2 | 5_1_grt | 0.5 | grt rounds 2 overflow 5:12031 -> 10:4878 | GRT-LABEL: DESIGN-FAIL: overflow 4878 at round 10 > 1000 |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-2580453 | sle_st_a_v2 | 5_1_grt | 0.3 | grt rounds 2 overflow 5:13907 -> 10:5441 | GRT-LABEL: DESIGN-FAIL: overflow 5441 at round 10 > 1000 |  |
| epyc7 | dpkit-slw_st_a_v2__clf4365a62-2579716 | slw_st_a_v2 | 5_1_grt | 0.3 | grt rounds 2 overflow 5:21080 -> 10:15696 | GRT-LABEL: DESIGN-FAIL: overflow 15696 at round 10 > 1000 |  |
| epyc8 | dpkit-kv3_hg-374537 | kv3_hg | 5_1_grt | 3.7 | grt rounds 1 overflow 5:50766 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_fw_v2__cl69f5e854-2970240 | sle_fw_v2 | 5_1_grt | 8.3 | grt rounds 1 overflow 5:26610 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-388109 | coll_core | 3_3_place_gp | 1.1 | overflow best 0.0996 last 0.0996 rows 46 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-2013982 | dsdv_slice_c1x_C__t5 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-776600 | hd_lep0N_w | pregrt_ff_hold | 3.5 | repair_TNS best 271687 last 271687 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-827145 | hd_lep0N_w | pregrt_ff_hold | 3.5 | repair_TNS best 278529 last 278529 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-891099 | hd_lep0N_w | pregrt_ff_hold | 3.4 | repair_TNS best 278529 last 278529 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-908756 | hd_lep0N_w | pregrt_ff_hold | 3.4 | repair_TNS best 271687 last 271687 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-972414 | hd_lep0N_w | 4_2_tapbal_grt | 0.7 | last meaningful line 0.3 h ago (46/59 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-hd_st_n4-158454 | hd_st_n4 | postcts_gate_TT | 1.3 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hroot-740108 | kv3_hroot | 5_2_route | 3.5 | drt_violations best 88466 last 88466 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (6211/6211 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (6583/6583 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_sys_c-2134137 | kv3_sys_c | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (372/372 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t14-1920992 | ot_s81sl_leaf__t14 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (1472/1472 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t14-1945276 | ot_s81sl_leaf__t14 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (1472/1472 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t43-3642617 | ot_s81sl_leaf__t43 | 5_1_grt | 1.7 | last meaningful line 0.0 h ago (87/87 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t73-3464910 | ot_s81sl_leaf__t73 | 5_1_grt | 1.8 | last meaningful line 0.1 h ago (156/156 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-3135509 | sle_stm_v1 | 5_1_grt | 4.6 | last meaningful line 0.1 h ago (917/934 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v2__cl7b3062fa-3029892 | sle_stm_v2 | generate_abstract | 12.6 | last meaningful line 0.2 h ago (397/397 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t12-4037092 | slice_station__t12 | 5_3_fillcell | 1.5 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-1141980-12932 | 1141980 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc10 | otc-1479473-28803 | 1479473 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (6583/6583 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | otc-1750712-14036 | 1750712 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc10 | otc-2045430-9455 | 2045430 | asbuilt.yosys | 0.1 | last meaningful line -0.0 h ago (134216/134216 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_223531_3628570-i2t-933314 | eco_20261122_223531_3628570-i2t | 5_1_grt | 0.8 | last meaningful line 0.2 h ago (233/1264 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_075519_12410-i1-1416585 | eco_20261123_075519_12410-i1 | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (230/1302 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3789030 | col_h10_r0_p1__t1 | 5_1_grt | 4.6 | last meaningful line 0.0 h ago (219/220 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1379295 | col_h10_r0_p4__t1 | pregrt_ff_hold | 3.5 | repair_TNS best 144649 last 144649 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-3069419 | dsdv_slice_c1x_C__t3 | 1_2_yosys | 2.3 | last meaningful line 0.0 h ago (288/288 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_mu_C__t1-3116985 | dsdv_slice_lepe_mu_C__t1 | 5_1_grt | 9.6 | last meaningful line 4.5 h ago (207/215 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-3769495 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 9.2 | repair_Violations best 1389 last 1414 rows 41 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_2_route | 5.9 | drt_violations best 16255 last 16255 rows 3 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-3921528 | kv3_hroot | 5_2_route | 4.5 | drt_violations best 88466 last 88466 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v3n-1352817 | kv3_pv_v3n | 3_5_place_dp | 5.9 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4n-420301 | kv3_pv_v4n | 3_5_place_dp | 6.4 | last meaningful line 0.3 h ago (58/58 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 10.3 | drt_violations best 112571 last 112571 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2029056 | sle_fw_v1 | 5_2_route | 12.6 | last meaningful line 0.5 h ago (291/292 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2079569 | sle_hc1 | 5_2_route | 12.5 | last meaningful line 0.1 h ago (266/266 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2087895 | sle_hc1 | 5_2_route | 12.5 | last meaningful line 0.3 h ago (132/132 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-2124945 | slw_fw_v1 | 5_2_route | 12.5 | last meaningful line 0.3 h ago (291/292 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1813230 | slw_hc0 | 5_1_grt | 10.3 | last meaningful line 0.3 h ago (1100/1117 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2294717 | slw_hc0 | 5_1_grt | 10.1 | last meaningful line 0.1 h ago (1052/1069 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 9.1 | drt_violations best 56731 last 56731 rows 4 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 9.5 | drt_violations best 59302 last 59302 rows 5 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc2 | otc-2186430-24000 | 2186430 | - | 5.5 |  | NO-DATA: no log found |  |
| epyc2 | otc-2438095-32195 | 2438095 | - | 2.8 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261122_164248_3895049-i1-2533130 | eco_20261122_164248_3895049-i1 | 5_2_route | 5.3 | last meaningful line 0.3 h ago (283/284 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_164521_3948325-i1-2180646 | eco_20261122_164521_3948325-i1 | 5_2_route | 5.5 | drt_violations best 735 last 735 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i1-2037456 | eco_20261122_181101_3945375-i1 | 5_2_route | 3.1 | last meaningful line 0.1 h ago (267/267 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i1-2840670 | eco_20261122_190506_3875261-i1 | 5_2_route | 2.5 | last meaningful line 0.3 h ago (134/134 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2378761 | col_h10_r2__t1 | pregrt_ff_hold | 0.4 | repair_TNS best 7513.19 last 7513.19 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2684878 | col_h10_r2__t1 | postcts_gate_TT | 0.2 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 325624 last 325624 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-836163 | col_h9_r0_p5__t1 | 5_1_grt | 4.4 | last meaningful line 0.8 h ago (210/219 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | pregrt_ff_hold | 2.9 | repair_TNS best 35674.2 last 35674.2 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3134610 | dsdv_slice_kv512_C__t1 | tt_setup_repair | 2.8 | repair_Violations best 31294 last 31412 rows 53 | YOUNG: stage 0.6 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N_w-3305132 | hd_lep0N_w | pregrt_ff_hold | 2.7 | repair_TNS best 1.67794e+06 last 1.67794e+06 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-hd_st_n4-2829569 | hd_st_n4 | 5_2_route | 3.0 | drt_violations best 20698 last 20698 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v1-1064320 | kv3_pv_v1 | 3_5_place_dp | 4.2 | last meaningful line 0.2 h ago (140/140 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12-2749349 | kv3_pv_v12 | port_bind | 0.2 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2-603007 | kv3_pv_v2 | 3_5_place_dp | 4.6 | last meaningful line 0.3 h ago (55/55 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t47-2809230 | ot_s81sl_leaf__t47 | 3_1_place_gp_skip_io | 0.1 | last meaningful line 0.0 h ago (7/7 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3059053 | sle_fw_v2 | 5_2_route | 14.3 | drt_violations best 135433 last 135433 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1049163 | sle_hc1 | 5_2_route | 15.2 | drt_violations best 15038 last 15038 rows 3 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 15.2 | drt_violations best 409476 last 409476 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc7 | otc-1839228-30982 | 1839228 | signoff_20261123_103406_1530301 | 0.8 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | otc-2058048-13390 | 2058048 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc7 | otc-2287405-27505 | 2287405 | signoff | 3.4 | last meaningful line 3.3 h ago (3/3 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | otc-2699582-1144 | 2699582 | signoff | 0.2 | last meaningful line 0.2 h ago (3/3 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | otc-2730116-9858 | 2730116 | qkd_hr_core_tx__ctl_ofsm | 0.2 | last meaningful line 0.0 h ago (286/286 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | otc-2993777-14089 | 2993777 | ot_bind_native_d2cca58fa2a2355c9791557c | 0.0 | last meaningful line -0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-3970901-4095 | 3970901 | - | 5.3 |  | NO-DATA: no log found |  |
| epyc7 | otc-4110793-30116 | 4110793 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261122_215654_330309-i2-3585488 | eco_20261122_215654_330309-i2 | 5_2_route | 2.5 | last meaningful line 0.2 h ago (262/263 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_080018_715668-i1t-847605 | eco_20261123_080018_715668-i1t | 5_1_grt | 4.4 | repair_Viol best 2444 last 2444 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | prd-fin-2223567 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | so_2063480_ff_38282 | so_2063480_ff_38282 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc7 | so_2063480_tt_38282 | so_2063480_tt_38282 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-cbf_q00__cl1b5a6458-757482 | cbf_q00 | 3_5_place_dp | 1.9 | last meaningful line 0.0 h ago (119/119 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2000675 | col_h9_r0_p2__t1 | 5_2_route | 10.4 | drt_violations best 136200 last 136200 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-2217964 | col_h9_r2__t1 | 5_2_route | 10.3 | drt_violations best 52429 last 52429 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t1-2205610 | dsdv_slice_c1x_C__t1 | 3_5_place_dp | 4.7 | last meaningful line 0.1 h ago (37/37 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t8-1783469 | dsdv_slice_c1x_C__t8 | 3_4_place_resized | 4.9 | last meaningful line 0.0 h ago (440/440 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_kv512_C__t1-1930297 | dsdv_slice_kv512_C__t1 | 5_1_grt | 4.8 | last meaningful line 1.5 h ago (210/214 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2088472 | dsdv_slice_lepe_nh_mus_C__t1 | 5_1_grt | 10.3 | last meaningful line 0.3 h ago (211/213 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-glue-555250 | glue | 5_2_route | 12.8 | drt_violations best 82647 last 82647 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (4092/4092 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hgi_v5-2058350 | kv3_hgi_v5 | 3_5_place_dp | 1.3 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-494270 | kv3_hub_Ei | 5_2_route | 12.8 | drt_violations best 12553 last 12553 rows 2 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (6152/6152 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pc_v1__cl7f648944-2054469 | kv3_pc_v1 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (5437/5437 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pc_v1__cl7f648944-628689 | kv3_pc_v1 | tt_setup_repair | 1.9 | repair_Viol best 9885 last 9885 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v12-2069688 | kv3_pv_v12 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (9225/9225 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v6-164511 | kv3_pv_v6 | 3_5_place_dp | 7.2 | last meaningful line 0.8 h ago (141/141 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-1144307 | serdes__t1 | tt_setup_measure_grt | 5.2 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l1__cl5ea486db-2008589 | sle_su_l1 | 5_1_grt | 4.8 | last meaningful line 0.1 h ago (883/900 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | otc-733421-2120 | 733421 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i1t-50076 | eco_20261123_120225_75582-i1t | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (261/1131 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | relec1122-ml-slw_hc3_cld86_mainlec | relec1122-ml-slw_hc3_cld86_mainlec | - | 1.9 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2103226 | col_h10_r2__t1 | 5_2_route | 6.0 | drt_violations best 7676 last 7676 rows 2 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-401605 | dsdv_slice_iq_C__t1 | 5_1_grt | 10.3 | last meaningful line 0.3 h ago (216/217 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-3178195 | hd_ctl | 5_2_route | 5.3 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 4.4 | repair_TNS best 309828 last 309828 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v2n-2681030 | kv3_pv_v2n | 3_5_place_dp | 5.6 | last meaningful line 1.5 h ago (57/57 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v4-2911509 | kv3_pv_v4 | 3_5_place_dp | 5.5 | last meaningful line 0.3 h ago (57/57 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v5n-250741 | kv3_pv_v5n | 3_3_place_gp | 4.4 | overflow best 0.1 last 0.1 rows 42 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v6n-2406851 | kv3_pv_v6n | pregrt_ff_hold | 5.8 | repair_TNS best 421499 last 421499 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-184640 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 4.5 | last meaningful line 0.0 h ago (211/214 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2882536 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 8.3 | repair_Remaining best 354110 last 354110 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t33-1533302 | ot_s81sl_leaf__t33 | 5_1_grt | 3.6 | last meaningful line 1.0 h ago (206/214 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t68-124972 | ot_s81sl_leaf__t68 | 5_1_grt | 1.9 | last meaningful line 0.2 h ago (1303/1365 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_1_grt | 7.5 | last meaningful line 0.0 h ago (190/196 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | 5_1_grt | 4.5 | last meaningful line 0.0 h ago (166/166 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-3009482 | slw_fe_v2 | 5_1_grt | 8.3 | last meaningful line 0.0 h ago (190/194 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | 5_1_grt | 7.5 | last meaningful line 0.0 h ago (197/198 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v3-3096266 | slw_fw_v3 | postcts_gate_TT | 8.2 | last meaningful line 0.0 h ago (2018/2018 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 6.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-2062537-15369 | 2062537 | - | 3.4 |  | NO-DATA: no log found |  |
| epyc9 | otc-2709063-15078 | 2709063 | asbuilt.yosys | 0.1 | last meaningful line 0.0 h ago (2847/2847 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-2908826-5237 | 2908826 | - | 2.8 |  | NO-DATA: no log found |  |
| epyc9 | otc-2909264-658 | 2909264 | - | 2.8 |  | NO-DATA: no log found |  |
| epyc9 | otc-3778865-25787 | 3778865 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i1-454593 | eco-i1 | 5_2_route | 4.3 | drt_violations best 3399 last 3399 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261122_180231_342380-i3t-3335435 | eco_20261122_180231_342380-i3t | 5_2_route | 2.5 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | relec1122-ml-coll_s_base_mainlec | relec1122-ml-coll_s_base_mainlec | - | 2.1 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-coll_s_eco_mainlec | relec1122-ml-coll_s_eco_mainlec | - | 2.1 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-slw_hc3_clccfc_mainlec | relec1122-ml-slw_hc3_clccfc_mainlec | - | 2.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3534091 | col_h10_r2__t1 | 5_2_route | 10.3 | drt_violations best 52562 last 52562 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 24.0 | drt_violations best 175829 last 175829 rows 1 | YOUNG: evidence 6.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-3522355 | col_h9_r2__t1 | 5_2_route | 10.3 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2916065 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 7.9 | repair_Remaining best 139132 last 139132 rows 108 | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-hd_lep0N-571931 | hd_lep0N | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (63/63 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-hd_lep0N_w-549280 | hd_lep0N_w | 3_1_place_gp_skip_io | 0.2 | overflow best 0.2087 last 0.2087 rows 37 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-hd_turn_a-281998 | hd_turn_a | 5_2_route | 0.5 | drt_violations best 3137 last 3137 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-kv3_hg_v3-419971 | kv3_hg_v3 | 2_1_floorplan | 0.3 | repair_Viol best 7320 last 7320 rows 340 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_hgi_v1__cl141fc26e-3953955 | kv3_hgi_v1 | pregrt_ff_hold | 0.9 | repair_TNS best 92451.4 last 92451.4 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-kv3_hgi_v8-589744 | kv3_hgi_v8 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (4667/4667 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-257843 | kv3_hroot | 3_3_place_gp | 0.5 | overflow best 0.6727 last 0.6733 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v3e-280312 | kv3_pv_v3e | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (6678/6678 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v7-3747893 | kv3_pv_v7 | 3_4_place_resized | 7.3 | last meaningful line 0.2 h ago (655/655 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-468236 | ot_s81sl_kv_leaf__t4 | 1_2_yosys | 0.3 | last meaningful line 0.0 h ago (732/732 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t15-2887177 | ot_s81sl_leaf__t15 | 5_1_grt | 1.9 | last meaningful line 0.5 h ago (262/1269 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | 5_1_grt | 7.9 | last meaningful line 0.3 h ago (193/199 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l1__cl5ea486db-385423 | sle_su_l1 | 3_3_place_gp | 0.4 | overflow best 0.4573 last 0.4704 rows 12 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slice_station__t52-3521993 | slice_station__t52 | 5_2_route | 10.3 | drt_violations best 31401 last 31401 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-981236 | slw_hc3 | postcts_gate_TT | 9.1 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l1__cla2a78701-413436 | slw_su_l1 | 3_3_place_gp | 0.3 | overflow best 0.2496 last 0.2496 rows 34 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 10.4 | drt_violations best 151194 last 151194 rows 2 | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel1 | otc-3494356-28288 | 3494356 | gen_lint_yosys | 1.3 | last meaningful line 1.3 h ago (1/1 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | otc-586875-1941 | 586875 | orfs_synth | 0.2 | last meaningful line 0.2 h ago (4254/4254 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-859118-24642 | 859118 | build_s81_srx7_m2_ns3_hc | 0.0 | last meaningful line 0.0 h ago (719/719 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-910747-1220 | 910747 | - | 6.3 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 7.7 | drt_violations best 90237 last 90237 rows 1 | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i1-1606115 | eco_20261122_143408_943433-i1 | 5_2_route | 5.9 | drt_violations best 51 last 51 rows 10 | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | prd-eco_20261122_165619_1517073-i2t-304945 | eco_20261122_165619_1517073-i2t | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (251/511 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r0_p1__t1__cl911743eb-1964442 | col_h10_r0_p1__t1 | pregrt_ff_hold | 0.8 | repair_TNS best 102070 last 102070 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2731145 | col_h10_r1__t1 | 4_1_cts | 0.5 | repair_Violations best 27 last 36 rows 12 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-kv3_hgi_v3-1994888 | kv3_hgi_v3 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (5914/5914 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-kv3_hroot-2911825 | kv3_hroot | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_C-1760664 | kv3_hub_C | 2_1_floorplan | 2.9 | last meaningful line 2.5 h ago (1424/1424 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-673287 | kv3_io_ft | 5_2_route | 1.5 | drt_violations best 2 last 2 rows 5 | YOUNG: stage 0.9 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t2-1999785 | ot_s81sl_leaf__t2 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (4323/4323 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t66-2007143 | ot_s81sl_leaf__t66 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (4120/4120 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-sle_su_c-2423739 | sle_su_c | 3_1_place_gp_skip_io | 0.6 | overflow best 0.187 last 0.187 rows 40 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | ot-ucfvf-probe-2672355 | ot-ucfvf-probe | otrun | 0.5 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | otc-3031694-21857 | 3031694 | yosys | 0.3 | last meaningful line 0.3 h ago (6307/6307 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | otc-3470700-8061 | 3470700 | build_s81_srx7_m2_xs | 0.1 | last meaningful line 0.0 h ago (641/641 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | otc-3470702-28057 | 3470702 | build_s81_srx7_m2_xs | 0.1 | last meaningful line 0.0 h ago (641/641 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | otc-3470704-981 | 3470704 | build_s81_srx7_m2_xs | 0.1 | last meaningful line 0.0 h ago (641/641 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | otc-3470706-19476 | 3470706 | build_s81_srx7_m2_xs | 0.1 | last meaningful line 0.0 h ago (641/641 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | otc-3470707-11111 | 3470707 | build_s81_srx7_m2_xs | 0.1 | last meaningful line 0.0 h ago (641/641 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | s81kvt2arch_synth1 | s81kvt2arch_synth1 | - | 0.2 |  | NO-DATA: no log found |  |
| intel2 | so_3468167_ff_94007 | so_3468167_ff_94007 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel2 | so_3468167_tt_94007 | so_3468167_tt_94007 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc10 | otc-1533686-9605 | 1533686 | asbuilt.yosys | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | otc-1677765-27528 | 1677765 | asbuilt.yosys | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3447267 | sle_hc2 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 7.6 | drt_violations best 25044 last 25044 rows 5 | before-window best 154752, window best 25044 | PROGRESS: drt_violations improved 83.8 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 73.7 | last meaningful line 1.1 h ago (1618/1618 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 10.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_hgi_v4-1845670 | kv3_hgi_v4 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-775509 | sle_ctl | pregrt_ff_hold | 6.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 12.5 | drt_violations best 12793 last 12793 rows 9 | before-window best 154966, window best 12793 | PROGRESS: drt_violations improved 91.7 % in window |  |
| epyc7 | dpkit-slw_stm_v2__cl9beb65e6-3994155 | slw_stm_v2 | 5_2_route | 13.8 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 10.2 | drt_violations best 69042 last 69042 rows 6 | before-window best 311954, window best 69042 | PROGRESS: drt_violations improved 77.9 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 20.9 | drt_violations best 43 last 43 rows 29 | before-window best 932, window best 43 | PROGRESS: drt_violations improved 95.4 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 24.3 | drt_violations best 9545 last 9545 rows 16 | before-window best 13260, window best 9545 | PROGRESS: drt_violations improved 28.0 % in window |  |
| epyc8 | dpkit-kv3_hgi_v2__cle0015330-3042686 | kv3_hgi_v2 | pregrt_ff_hold | 0.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 11.8 | drt_violations best 15247 last 15247 rows 15 | before-window best 30242, window best 15247 | PROGRESS: drt_violations improved 49.6 % in window |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 4_1_cts | 7.7 | last meaningful line 0.2 h ago (12265/12265 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_1_grt | 8.4 | repair_TNS best 0 last 0 rows 20 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 5.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-native59-274714 | native59 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | pregrt_ff_hold | 5.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2894435 | sle_hc1 | pregrt_ff_hold | 8.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-3009490 | slw_hc1 | pregrt_ff_hold | 8.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3-922063 | eco_20261121_070035_1645318-i3 | 5_2_route | 16.3 | drt_violations best 20 last 43 rows 31 | before-window best 21, window best 20 | PROGRESS: drt_violations improved 4.8 % in window |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-917385 | col_h10_r0_p1__t1 | 5_2_route | 23.7 | drt_violations best 43 last 43 rows 8 | before-window best 195281, window best 43 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 23.7 | drt_violations best 40912 last 40912 rows 4 | before-window best 210671, window best 40912 | PROGRESS: drt_violations improved 80.6 % in window |  |
| intel1 | dpkit-coll_ftm-625194 | coll_ftm | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-glue-1559836 | glue | pregrt_ff_hold | 8.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | 5_2_route | 22.2 | drt_violations best 109763 last 109763 rows 1 | before-window best 109763, window best 109763 | PROGRESS: drt_violations: active iteration at 96134 < best completed total 109763 (in-iter |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | 5_1_grt | 8.6 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 31.2 | drt_violations best 1027 last 1402 rows 28 | before-window best 1064, window best 1027 | PROGRESS: drt_violations improved 3.5 % in window |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-237868 | col_h10_r0_p4__t1 | 5_2_route | 15.7 | drt_violations best 806 last 806 rows 12 | before-window best 105374, window best 806 | PROGRESS: drt_violations improved 99.2 % in window |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3384117 | col_h9_r1__t1 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-coll_core-3588522 | coll_core | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_ctl__cla4f6f12f-2733138 | sle_ctl | pregrt_ff_hold | 4.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 17.7 | drt_violations best 64401 last 64401 rows 3 | before-window best 327883, window best 64401 | PROGRESS: drt_violations improved 80.4 % in window |  |
| intel2 | dpkit-slw_su_l1__clcc9d0155-2150277 | slw_su_l1 | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
