# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 17:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 6, 'GRT-LABEL': 5, 'YOUNG': 73, 'NO-DATA': 10, 'PROGRESS': 18}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc12 | dpkit-native59-478901 | native59 | pregrt_ff_hold | 5.1 | repair_TNS best 45620.6 last 45620.6 rows 1 | before-window best 45620.6, window best 45620.6 | NO-PROGRESS: repair_TNS best 45620.6 vs 45620.6 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (QC-GLUE-IMAGES decides; |
| epyc12 | otc-3501458-13012 | 3501458 | run | 13.9 | last meaningful line 13.9 h ago (1/1 lines) | NO-PROGRESS: no new non-iteration log line for 13.9 h | REPORT-ONLY: lane-own kit (abstract-exact decides; |
| epyc12 | otc-351743-16220 | 351743 | hcpg_run | 11.7 | last meaningful line 11.3 h ago (13/13 lines) | NO-PROGRESS: no new non-iteration log line for 11.3 h | REPORT-ONLY: lane-own kit (abstract-exact decides; |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | pregrt_ff_hold | 6.7 | repair_TNS best 2.44591e+06 last 2.44591e+06 rows 1 | before-window best 2.44591e+06, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (QC-C1O-COMPOSE decides; |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 30.2 | drt_violations best 4 last 4 rows 57 | before-window best 4, window best 4 | NO-PROGRESS: drt_violations best 4 vs 4 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 28.4 | drt_violations best 1 last 1 rows 45 | before-window best 1, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | 5_1_grt | 11.8 | grt rounds 2 overflow 5:32105 -> 10:5327 | GRT-LABEL: DESIGN-FAIL: overflow 5327 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | 5_1_grt | 9.4 | grt rounds 5 overflow 5:120028 -> 10:2188 -> 15:1369 -> 20:1502 -> 25:1102 | GRT-LABEL: DESIGN-FAIL: overflow 2188 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 5_1_grt | 12.3 | grt rounds 3 overflow 5:121909 -> 10:2158 -> 15:1367 | GRT-LABEL: DESIGN-FAIL: overflow 2158 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 5_1_grt | 12.2 | grt rounds 5 overflow 5:123883 -> 10:2244 -> 15:1394 -> 20:1584 -> 25:1212 | GRT-LABEL: DESIGN-FAIL: overflow 2244 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 5_1_grt | 12.4 | grt rounds 5 overflow 5:119162 -> 10:2290 -> 15:1427 -> 20:1597 -> 25:1148 | GRT-LABEL: DESIGN-FAIL: overflow 2290 at round 10 > 1000 |  |
| epyc10 | dpkit-sle_stm_v2__cl55be2264-3032309 | sle_stm_v2 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (253/253 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v2__cl7b3062fa-2889141 | sle_stm_v2 | lec | 0.1 | LEC last write 0.0 h ago | YOUNG: evidence 0.1 h < 6 h |  |
| epyc10 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2254323 | slw_sc_v1 | 3_3_place_gp | 0.3 | overflow best 0.1612 last 0.1958 rows 43 | YOUNG: stage 0.2 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-1395551 | col_h9_r0_p5__t1 | 5_2_route | 7.9 | last meaningful line 0.3 h ago (286/287 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_1_grt | 8.0 | repair_TNS best 8415.8 last 8415.8 rows 5 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | 5_2_route | 8.0 | drt_violations best 255884 last 255884 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-1130830 | col_h9_r0_p5__t1 | 5_2_route | 8.0 | drt_violations best 77306 last 77306 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc93af856-1168215 | col_h9_r0_p5__t1 | 5_2_route | 8.0 | drt_violations best 70154 last 70154 rows 2 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-1072222 | col_h9_r0_p5__t1 | 5_2_route | 8.1 | drt_violations best 73182 last 73182 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i3-2829259 | eco_20261124_200101_1087713-i3 | 5_1_grt | 0.4 | last meaningful line 0.1 h ago (145/145 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | pregrt_ff_hold | 3.2 | repair_TNS best 121568 last 121568 rows 1 | YOUNG: evidence 1.5 h < 2.5 h |  |
| epyc12 | dpkit-hd_st_n4-1311294 | hd_st_n4 | 5_2_route | 1.4 | last meaningful line 0.1 h ago (245/246 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc12 | dpkit-kv3_hg_v1p4__ret4_es_4-2549283 | kv3_hg_v1p4__ret4_es_4 | 3_3_place_gp | 0.4 | overflow best 0.5822 last 0.5822 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-ot_s81sl_leaf__t70-2429563 | ot_s81sl_leaf__t70 | 3_3_place_gp | 0.5 | overflow best 0.3015 last 0.3015 rows 37 | YOUNG: stage 0.3 h < 1 h |  |
| epyc12 | dpkit-sle_ctl__cla4f6f12f-254756 | sle_ctl | 5_1_grt | 5.3 | last meaningful line 0.3 h ago (296/1302 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t24__cl64811a5d-1102657 | slice_station__t24 | 5_2_route | 1.6 | drt_violations best 7536 last 7536 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc12 | dpkit-slice_station__t50__cld84c9e24-650458 | slice_station__t50 | 5_2_route | 2.0 | last meaningful line 0.1 h ago (253/254 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 13.9 |  | NO-DATA: no log found |  |
| epyc12 | otc-3090390-13757 | 3090390 | signoff | 0.0 | last meaningful line 0.0 h ago (3/3 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | prd-eco_20261126_000257_709121-i1-1559361 | eco_20261126_000257_709121-i1 | 5_3_fillcell | 1.2 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | 5_2_route | 8.1 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 11.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 11.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 11.7 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-kv3_pv_v12e-1804185 | kv3_pv_v12e | postcts_gate_TT | 9.3 | last meaningful line 0.3 h ago (2956/2956 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 5_2_route | 11.5 | drt_violations best 33248 last 33248 rows 2 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-362758 | slw_hc2 | 5_2_route | 6.8 | drt_violations best 81161 last 81161 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc7 | otc-2152091-6999 | 2152091 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | otc-639211-10962 | 639211 | - | 8.2 |  | NO-DATA: no log found |  |
| epyc7 | otc-728591-15662 | 728591 | signoff | 2.8 | last meaningful line 2.8 h ago (3/3 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | so_1398184_ff_69679 | so_1398184_ff_69679 | generate_abstract | 0.5 | last meaningful line 0.3 h ago (33/33 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | so_1398184_tt_69679 | so_1398184_tt_69679 | generate_abstract | 0.5 | last meaningful line 0.3 h ago (33/33 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-native59-2892451 | native59 | 5_2_route | 6.3 | drt_violations best 158884 last 158884 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 6.9 | last meaningful line 0.1 h ago (264/265 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v3-4131858 | sle_sc_v3 | generate_abstract | 7.2 | last meaningful line 0.1 h ago (30/30 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | eco-abs-746390 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.1 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-1609200-26446 | 1609200 | - | 9.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-1616827-18813 | 1616827 | - | 9.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-3731784-29079 | 3731784 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-816499-29893 | 816499 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3804990 | col_h10_r0_p1__t1 | 5_1_grt | 7.5 | last meaningful line 0.2 h ago (275/1280 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 5.9 | last meaningful line 0.4 h ago (269/270 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 7.9 | last meaningful line 0.5 h ago (279/280 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 5_2_route | 9.5 | drt_violations best 176025 last 176025 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-870318 | col_h9_r0_p3__t1 | 5_1_grt | 7.3 | last meaningful line 1.0 h ago (271/1296 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | 5_1_grt | 5.4 | last meaningful line 0.0 h ago (158/158 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv8995e794-2664422 | col_h9_r0_p5__t1 | 5_1_grt | 9.3 | repair_TNS best 37679.3 last 37679.3 rows 6 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 9.5 | last meaningful line 0.0 h ago (270/270 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 6.5 | last meaningful line 0.5 h ago (271/272 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 5_1_grt | 8.0 | last meaningful line 0.2 h ago (268/1276 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | pregrt_ff_hold | 5.8 | repair_TNS best 85658.9 last 85658.9 rows 1 | YOUNG: evidence 2.2 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 6.7 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 7.5 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 9.5 | drt_violations best 178781 last 178781 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-138946 | col_h9_r2__t1 | 5_2_route | 5.9 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 8.0 | last meaningful line 0.4 h ago (278/279 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 6.0 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-2945122 | col_h9_r2__t1 | 5_2_route | 9.2 | drt_violations best 746 last 746 rows 11 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | 5_2_route | 9.3 | drt_violations best 7329 last 7329 rows 4 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 5_2_route | 8.8 | drt_violations best 159056 last 159056 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 8.0 | drt_violations best 157970 last 157970 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 4_1_cts | 6.4 | last meaningful line 0.2 h ago (8589/8589 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | pregrt_ff_hold | 8.0 | repair_TNS best 496091 last 496091 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-slice_station__t31-407252 | slice_station__t31 | 6_report | 5.9 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 12.4 | repair_TNS best 14642 last 14642 rows 7 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | 5_2_route | 12.4 | drt_violations best 41659 last 41659 rows 2 | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | 5_2_route | 12.3 | drt_violations best 21385 last 21385 rows 3 | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 6.8 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-3824626 | coll_ftc | 5_2_route | 6.9 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | postcts_gate_TT | 7.4 | last meaningful line 0.3 h ago (735/735 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-4035353 | slw_hc3 | 5_2_route | 6.8 | last meaningful line 0.1 h ago (128/128 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-178621-11182 | 178621 | - | 1.4 |  | NO-DATA: no log found |  |
| intel1 | otc-2021095-31410 | 2021095 | signoff | 4.4 | last meaningful line 4.3 h ago (3/3 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | otc-207040-3394 | 207040 | signoff | 1.4 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | otc-2908840-11609 | 2908840 | grt_it0 | 7.2 | last meaningful line 3.5 h ago (33/34 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | otc-3479258-28963 | 3479258 | - | 1.8 |  | NO-DATA: no log found |  |
| intel1 | otc-957737-21247 | 957737 | signoff | 1.1 | last meaningful line 1.0 h ago (3/3 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i3-3236766 | eco_20261123_191853_2879776-i3 | 5_2_route | 3.8 | last meaningful line 0.2 h ago (294/295 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1-1093733 | eco_20261125_002226_1452841-i1 | 5_2_route | 6.3 | drt_violations best 7 last 7 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i2t-515416 | eco_20261125_050013_1448739-i2t | 5_2_route | 1.3 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | prd-eco_20261125_070347_2847958-i2-1134837 | eco_20261125_070347_2847958-i2 | 5_1_grt | 1.0 | last meaningful line 0.3 h ago (295/322 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-925629 | coll_ftm | 5_2_route | 1.7 | drt_violations best 9847 last 9847 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 6.7 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 30.4 | drt_violations best 212 last 212 rows 51 | before-window best 232, window best 212 | PROGRESS: drt_violations improved 8.6 % in window |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 15.5 | drt_violations best 1 last 1 rows 54 | before-window best 2, window best 1 | PROGRESS: drt_violations improved 50.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 15.7 | drt_violations best 9935 last 9935 rows 10 | before-window best 477402, window best 9935 | PROGRESS: drt_violations improved 97.9 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 15.7 | drt_violations best 23481 last 23481 rows 7 | before-window best 493451, window best 23481 | PROGRESS: drt_violations improved 95.2 % in window |  |
| epyc7 | dpkit-sle_sc_v2-22145 | sle_sc_v2 | 5_2_route | 10.0 | drt_violations best 68573 last 68573 rows 7 | before-window best 412199, window best 68573 | PROGRESS: drt_violations improved 83.4 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 16.1 | drt_violations best 1784 last 1784 rows 15 | before-window best 468535, window best 1784 | PROGRESS: drt_violations improved 99.6 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 18.8 | drt_violations best 1387 last 1387 rows 20 | before-window best 76101, window best 1387 | PROGRESS: drt_violations improved 98.2 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 8.9 | drt_violations best 20275 last 20275 rows 12 | before-window best 284474, window best 20275 | PROGRESS: drt_violations improved 92.9 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 33.1 | drt_violations best 13 last 13 rows 53 | before-window best 18, window best 13 | PROGRESS: drt_violations improved 27.8 % in window |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-1427167 | col_h10_r0_p1__t1 | 5_1_grt | 8.7 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 5_2_route | 18.5 | drt_violations best 8965 last 8965 rows 3 | before-window best 91231, window best 8965 | PROGRESS: drt_violations improved 90.2 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 18.5 | drt_violations best 23659 last 23659 rows 4 | before-window best 535484, window best 23659 | PROGRESS: drt_violations improved 95.6 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_1_grt | 5.9 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 15.7 | drt_violations best 470122 last 470122 rows 1 | before-window best 470122, window best 470122 | PROGRESS: drt_violations: active iteration at 161763 < best completed total 470122 (in-ite |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 20.4 | drt_violations best 392 last 392 rows 51 | before-window best 553, window best 392 | PROGRESS: drt_violations improved 29.1 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_2_route | 12.3 | drt_violations best 22777 last 22777 rows 3 | before-window best 159806, window best 22777 | PROGRESS: drt_violations improved 85.7 % in window |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 25.9 | drt_violations best 10584 last 10584 rows 5 | before-window best 278493, window best 10584 | PROGRESS: drt_violations improved 96.2 % in window |  |
| intel1 | prd-eco_20261125_131510_2862538-i2-1638905 | eco_20261125_131510_2862538-i2 | 5_2_route | 0.8 | drt_violations best 0 last 0 rows 1 | PROGRESS: drt_violations reached 0 |  |
