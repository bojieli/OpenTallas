# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-26 02:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'UNSIGNABLE': 2, 'GRT-STUCK': 1, 'GRT-LABEL': 1, 'YOUNG': 46, 'NO-DATA': 6, 'EXCLUDED': 3, 'KEEP': 1, 'PROGRESS': 24}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 39.4 | drt_violations best 200 last 204 rows 58 | before-window best 202, window best 200 | NO-PROGRESS: drt_violations best 200 vs 202 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | 5_1_grt | 12.2 | grt rounds 9 overflow 20:894 -> 25:15 -> 30:4 -> 35:8 -> 40:1 -> 45:2 | UNSIGNABLE: GRT overflow flat: overflow 1 at iteration 40 -> 2 at iteration 45: flat for 5 i | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | pregrt_ff_hold | 4.9 | repair_TNS best 110094 last 110094 rows 1 | before-window best 110094, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 5_1_grt | 17.0 | grt rounds 9 overflow 20:2305 -> 25:2156 -> 30:1933 -> 35:1923 -> 40:2127 -> 45:2007 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (35:1923 -> 40:2127 -> 45:2007; best 2007 | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 14.8 | grt rounds 8 overflow 15:2296 -> 20:2337 -> 25:2143 -> 30:1999 -> 35:1942 -> 40:2129 | UNSIGNABLE: GRT overflow flat: overflow 1942 at iteration 35 -> 2129 at iteration 40: flat f | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 21.4 | repair_Viol best 968 last 968 rows 124 | before-window best 968, window best 968 | NO-PROGRESS: repair_Viol best 968 vs 968 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 37.4 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 5_1_grt | 15.4 | grt rounds 2 overflow 5:77168 -> 10:41977 | GRT-LABEL: DESIGN-FAIL: overflow 41977 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-2708094 | dsdv_slice_c1x_C__t5 | pregrt_ff_hold | 4.1 | repair_TNS best 354935 last 354935 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_C__t1-3949489 | dsdv_slice_lepw_mu_C__t1 | 3_5_place_dp | 1.9 | last meaningful line 0.1 h ago (37/37 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-712515 | hd_lep0N | 4_2_tapbal_grt | 1.5 | last meaningful line 0.5 h ago (48/51 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | lecaf-hdm-whole-exact-cohorts | lecaf-hdm-whole-exact-cohorts | - | 1.3 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-q9-stb-e1d-archive-elab | lecaf-q9-stb-e1d-archive-elab | gate.ys | 0.5 | last meaningful line 0.2 h ago (211823/211823 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 7.5 | last meaningful line 5.5 h ago (33/34 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc10 | otc-3747798-23978 | 3747798 | BOUND_READY | 0.0 | last meaningful line 0.0 h ago (4758/4758 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_2_route | 17.0 | drt_violations best 276288 last 276288 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_c1x_C__t7-2765401 | dsdv_slice_c1x_C__t7 | 3_5_place_dp | 2.3 | last meaningful line 0.0 h ago (88/88 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-svc_lo_dsdv_svc_rs_w__t1-1738997 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 1.1 | last meaningful line 0.3 h ago (626/626 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-1997619 | sle_stm_v2 | 5_2_route | 6.6 | drt_violations best 96273 last 96273 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_2_route | 8.4 | drt_violations best 179686 last 179686 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261125_200405_3323313-i2t-2216991 | eco_20261125_200405_3323313-i2t | 5_2_route | 1.4 | drt_violations best 3704 last 3704 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261126_015555_2965752-i1t-7345 | eco_20261126_015555_2965752-i1t | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 4.3 | last meaningful line 3.5 h ago (700/700 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc7 | otc-2739402-5290 | 2739402 | - | 8.8 |  | NO-DATA: no log found |  |
| epyc7 | otc-4045538-6308 | 4045538 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 3.0 | drt_violations best 95 last 95 rows 13 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261126_090542_621054-i1t-2265448 | eco_20261126_090542_621054-i1t | 5_2_route | 1.1 | last meaningful line 0.0 h ago (266/267 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-hd_spn-3715078 | hd_spn | 3_3_place_gp | 0.2 | overflow best 0.0992 last 0.0992 rows 46 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | lecaf-hc3-afda1e-twins | lecaf-hc3-afda1e-twins | - | 5.0 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261126_033711_2888564-i2t-1658020 | eco_20261126_033711_2888564-i2t | 5_2_route | 0.9 | last meaningful line 0.0 h ago (261/262 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | pregrt_ff_hold | 3.9 | repair_TNS best 35372.7 last 35372.7 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | 5_1_grt | 5.2 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-2823500 | col_h9_r1__t1 | pregrt_ff_hold | 4.5 | repair_TNS best 71970 last 71970 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2325128 | col_h9_r1__t1 | pregrt_ff_hold | 4.6 | repair_TNS best 110976 last 110976 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8aaf8508-3602152 | col_h9_r1__t1 | 4_2_tapbal_grt | 0.9 | last meaningful line 0.3 h ago (61/69 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-3901907 | col_h9_r1__t1 | pregrt_ff_hold | 4.3 | repair_TNS best 99737.1 last 99737.1 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2382304 | col_h9_r1__t1 | pregrt_ff_hold | 4.6 | repair_TNS best 177431 last 177431 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-2530599 | col_h9_r1__t1 | pregrt_ff_hold | 4.6 | repair_TNS best 47356.8 last 47356.8 rows 1 | YOUNG: evidence 1.4 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvfef7c177-3709744 | col_h9_r2__t1 | pregrt_ff_hold | 1.8 | repair_TNS best 142578 last 142578 rows 1 | YOUNG: evidence 1.0 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | 5_1_grt | 4.3 | repair_Remaining best 144706 last 144706 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-4156698 | col_h9_r2__t1 | 5_1_grt | 3.4 | last meaningful line 0.1 h ago (1304/2349 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | 5_2_route | 5.0 | last meaningful line 0.0 h ago (264/265 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-4056356 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t1-3555509 | ot_s81sl_leaf__t1 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (8239/8239 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-2575809 | ot_s81sl_leaf__t53 | tt_setup_repair_grt | 4.5 | repair_Viol best 310 last 310 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-479268 | sle_su_l1 | 5_2_route | 4.1 | last meaningful line 0.0 h ago (253/254 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t26-3959180 | slice_station__t26 | 5_2_route | 1.8 | last meaningful line 0.1 h ago (245/246 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t29__clc7772371-1992482 | slice_station__t29 | postcts_gate_TT | 1.3 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__cl1ea9de02-813226 | slice_station__t40 | 5_1_grt | 1.5 | last meaningful line 0.1 h ago (1676/1707 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t45-1580954 | slice_station__t45 | 6_report | 4.8 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 5_1_grt | 4.7 | repair_TNS best 117112 last 117112 rows 2 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_072708_1527702-i1-3266022 | eco_20261126_072708_1527702-i1 | 5_2_route | 2.8 | drt_violations best 57150 last 57150 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_091926_2909746-i1t-3764749 | eco_20261126_091926_2909746-i1t | 5_1_grt | 0.9 | last meaningful line 0.3 h ago (310/475 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | prd-eco_retry_1795673019361579887-i1t-300819 | eco_retry_1795673019361579887-i1t | 5_2_route | 4.1 | drt_violations best 80636 last 80636 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 5.9 |  | NO-DATA: no log found |  |
| intel1 | lecq9-963f0492a10e | lecq9-963f0492a10e | - | 6.0 |  | NO-DATA: no log found |  |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 7.5 | last meaningful line 3.7 h ago (33/34 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | prd-count-p1_tc-559996 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | 5_2_route | 5.0 | drt_violations best 26 last 26 rows 25 | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t5-331755 | dsdv_slice_c1x_C__t5 | 3_1_place_gp_skip_io | 1.9 | overflow best 0.5387 last 0.5387 rows 32 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 20.7 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 20.7 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 20.7 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-454895 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.5 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1991043 | sle_stm_v2 | 5_2_route | 6.6 | drt_violations best 0 last 0 rows 7 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 24.7 | drt_violations best 3665 last 9066 rows 19 | before-window best 3875, window best 3665 | PROGRESS: drt_violations improved 5.4 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 24.7 | drt_violations best 12441 last 12441 rows 15 | before-window best 16003, window best 12441 | PROGRESS: drt_violations improved 22.3 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 25.1 | drt_violations best 421 last 421 rows 37 | before-window best 724, window best 421 | PROGRESS: drt_violations improved 41.9 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 15.9 | drt_violations best 1752 last 10932 rows 18 | before-window best 57907, window best 1752 | PROGRESS: drt_violations improved 97.0 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 42.1 | drt_violations best 11 last 11 rows 55 | before-window best 13, window best 11 | PROGRESS: drt_violations improved 15.4 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 14.9 | drt_violations best 7 last 11 rows 53 | before-window best 174634, window best 7 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 16.9 | drt_violations best 9 last 9 rows 53 | before-window best 34773, window best 9 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 18.5 | drt_violations best 97668 last 97668 rows 3 | before-window best 545016, window best 97668 | PROGRESS: drt_violations improved 82.1 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 14.9 | drt_violations best 120549 last 120549 rows 2 | before-window best 486708, window best 120549 | PROGRESS: drt_violations improved 75.2 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | pregrt_ff_hold | 4.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 24.7 | drt_violations best 453 last 453 rows 23 | before-window best 77076, window best 453 | PROGRESS: drt_violations improved 99.4 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 15.5 | drt_violations best 20574 last 20574 rows 5 | before-window best 380531, window best 20574 | PROGRESS: drt_violations improved 94.6 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 15.7 | drt_violations best 453 last 453 rows 23 | before-window best 171015, window best 453 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 16.5 | drt_violations best 2346 last 2346 rows 15 | before-window best 176573, window best 2346 | PROGRESS: drt_violations improved 98.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 18.5 | drt_violations best 1013 last 1013 rows 22 | before-window best 6715, window best 1013 | PROGRESS: drt_violations improved 84.9 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 29.4 | drt_violations best 390 last 408 rows 58 | before-window best 392, window best 390 | PROGRESS: drt_violations: falling inside the active iteration (408 -> 395) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 17.0 | drt_violations best 494 last 494 rows 21 | before-window best 44089, window best 494 | PROGRESS: drt_violations improved 98.9 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 15.0 | drt_violations best 371 last 371 rows 37 | before-window best 162182, window best 371 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 17.0 | drt_violations best 386 last 386 rows 50 | before-window best 2258, window best 386 | PROGRESS: drt_violations improved 82.9 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfd79e8b6-2469832 | col_h9_r2__t1 | pregrt_ff_hold | 2.9 | repair_Violations best 3198 last 3208 rows 91 | before-window best 252171, window best 3198 | PROGRESS: repair_Violations improved 98.7 % in window |  |
| epyc9 | dpkit-slice_station__t29__cl2e5c855a-3827558 | slice_station__t29 | 5_1_grt | 0.9 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 15.8 | drt_violations best 1774 last 1774 rows 15 | before-window best 167111, window best 1774 | PROGRESS: drt_violations improved 98.9 % in window |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 15.7 | drt_violations best 6 last 6 rows 42 | before-window best 211273, window best 6 | PROGRESS: drt_violations improved 100.0 % in window |  |
