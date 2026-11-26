# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-26 02:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 3, 'NO-PROGRESS': 3, 'GRT-STUCK': 1, 'GRT-LABEL': 2, 'YOUNG': 48, 'NO-DATA': 7, 'EXCLUDED': 3, 'KEEP': 1, 'PROGRESS': 24}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-2708094 | dsdv_slice_c1x_C__t5 | tt_setup_repair | 3.9 | repair_Violations best 355 last 432 rows 151 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -659.60 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | 5_1_grt | 12.0 | grt rounds 9 overflow 20:894 -> 25:15 -> 30:4 -> 35:8 -> 40:1 -> 45:2 | UNSIGNABLE: GRT overflow flat: overflow 1 at iteration 40 -> 2 at iteration 45: flat for 5 i | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | pregrt_ff_hold | 4.6 | repair_TNS best 110094 last 110094 rows 1 | before-window best 110094, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 5_1_grt | 16.7 | grt rounds 9 overflow 20:2305 -> 25:2156 -> 30:1933 -> 35:1923 -> 40:2127 -> 45:2007 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (35:1923 -> 40:2127 -> 45:2007; best 2007 | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 14.6 | grt rounds 8 overflow 15:2296 -> 20:2337 -> 25:2143 -> 30:1999 -> 35:1942 -> 40:2129 | UNSIGNABLE: GRT overflow flat: overflow 1942 at iteration 35 -> 2129 at iteration 40: flat f | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 21.1 | repair_Viol best 968 last 968 rows 114 | before-window best 968, window best 968 | NO-PROGRESS: repair_Viol best 968 vs 968 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 37.1 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 5_1_grt | 15.1 | grt rounds 2 overflow 5:77168 -> 10:41977 | GRT-LABEL: DESIGN-FAIL: overflow 41977 at round 10 > 1000 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-2575809 | ot_s81sl_leaf__t53 | 5_1_grt | 4.3 | grt rounds 2 overflow 5:18541 -> 10:3468 | GRT-LABEL: DESIGN-FAIL: overflow 3468 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_C__t1-3949489 | dsdv_slice_lepw_mu_C__t1 | 3_3_place_gp | 1.7 | overflow best 0.5729 last 0.5729 rows 56 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-hd_lep0N-712515 | hd_lep0N | 4_2_tapbal_grt | 1.3 | last meaningful line 0.3 h ago (48/50 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | lecaf-hdm-p6-retained-relays | lecaf-hdm-p6-retained-relays | - | 4.1 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-whole-exact-cohorts | lecaf-hdm-whole-exact-cohorts | - | 1.1 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-q9-stb-e1d-archive-elab | lecaf-q9-stb-e1d-archive-elab | gate.ys | 0.2 | last meaningful line 0.1 h ago (211823/211823 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 7.3 | last meaningful line 5.3 h ago (33/34 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_2_route | 16.8 | drt_violations best 276288 last 276288 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_c1x_C__t3-3965387 | dsdv_slice_c1x_C__t3 | 3_5_place_dp | 2.8 | last meaningful line 0.1 h ago (37/37 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_c1x_C__t7-2765401 | dsdv_slice_c1x_C__t7 | 3_3_place_gp | 2.1 | overflow best 0.2757 last 0.2757 rows 74 | YOUNG: stage 0.4 h < 1 h |  |
| epyc11 | dpkit-dsdv_slice_lepw_mus_C__t1-3987621 | dsdv_slice_lepw_mus_C__t1 | 3_5_place_dp | 2.8 | last meaningful line 0.0 h ago (88/88 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-svc_lo_dsdv_svc_rs_w__t1-1738997 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 0.8 | last meaningful line 0.2 h ago (626/626 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1991043 | sle_stm_v2 | 5_2_route | 6.4 | drt_violations best 14604 last 14604 rows 2 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-1997619 | sle_stm_v2 | 5_2_route | 6.4 | drt_violations best 96273 last 96273 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_2_route | 8.1 | drt_violations best 179686 last 179686 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261125_200405_3323313-i2t-2216991 | eco_20261125_200405_3323313-i2t | 5_2_route | 1.1 | drt_violations best 3704 last 3704 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc2 | prd-eco_20261126_015555_2965752-i1t-7345 | eco_20261126_015555_2965752-i1t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 4.1 | last meaningful line 3.3 h ago (700/700 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | otc-2739402-5290 | 2739402 | - | 8.6 |  | NO-DATA: no log found |  |
| epyc7 | otc-3624028-31520 | 3624028 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 2.8 | drt_violations best 320 last 320 rows 8 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261126_090542_621054-i1t-2265448 | eco_20261126_090542_621054-i1t | 5_2_route | 0.9 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | lecaf-hc3-afda1e-twins | lecaf-hc3-afda1e-twins | - | 4.8 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261126_033711_2888564-i2t-1658020 | eco_20261126_033711_2888564-i2t | 5_2_route | 0.7 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | pregrt_ff_hold | 3.7 | repair_TNS best 35372.7 last 35372.7 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl911743eb-3766630 | col_h10_r0_p1__t1 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | 5_1_grt | 4.9 | repair_Remaining best 172593 last 172593 rows 53 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-2823500 | col_h9_r1__t1 | pregrt_ff_hold | 4.2 | repair_TNS best 71970 last 71970 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2325128 | col_h9_r1__t1 | pregrt_ff_hold | 4.4 | repair_TNS best 110976 last 110976 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8aaf8508-3602152 | col_h9_r1__t1 | 4_2_tapbal_grt | 0.7 | last meaningful line 0.0 h ago (61/64 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-3901907 | col_h9_r1__t1 | pregrt_ff_hold | 4.0 | repair_TNS best 99737.1 last 99737.1 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2382304 | col_h9_r1__t1 | pregrt_ff_hold | 4.3 | repair_TNS best 177431 last 177431 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-2530599 | col_h9_r1__t1 | pregrt_ff_hold | 4.3 | repair_TNS best 47356.8 last 47356.8 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvfef7c177-3709744 | col_h9_r2__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 142578 last 142578 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | 5_1_grt | 4.1 | last meaningful line 0.0 h ago (154/154 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-4156698 | col_h9_r2__t1 | 5_1_grt | 3.1 | last meaningful line 0.0 h ago (184/184 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | 5_2_route | 4.8 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-4056356 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mus_C__t1-1648329 | dsdv_slice_lepw_mus_C__t1 | 3_5_place_dp | 4.5 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t1-3555509 | ot_s81sl_leaf__t1 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (8139/8139 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-479268 | sle_su_l1 | 5_2_route | 3.9 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t26-3959180 | slice_station__t26 | 5_2_route | 1.5 | last meaningful line 0.0 h ago (236/236 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t29__cl2e5c855a-3827558 | slice_station__t29 | 5_1_grt | 0.6 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t29__clc7772371-1992482 | slice_station__t29 | 5_1_grt | 1.0 | last meaningful line 0.1 h ago (584/615 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t45-1580954 | slice_station__t45 | 5_2_route | 4.5 | drt_violations best 8 last 8 rows 11 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 5_1_grt | 4.4 | repair_TNS best 118462 last 118462 rows 9 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_072708_1527702-i1-3266022 | eco_20261126_072708_1527702-i1 | 5_2_route | 2.5 | drt_violations best 57150 last 57150 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_091926_2909746-i1t-3764749 | eco_20261126_091926_2909746-i1t | 5_1_grt | 0.6 | repair_Remaining best 230193 last 230193 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | prd-eco_retry_1795673019361579887-i1t-300819 | eco_retry_1795673019361579887-i1t | 5_2_route | 3.9 | drt_violations best 80636 last 80636 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 5.7 |  | NO-DATA: no log found |  |
| intel1 | lecq9-963f0492a10e | lecq9-963f0492a10e | - | 5.8 |  | NO-DATA: no log found |  |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 7.2 | last meaningful line 3.5 h ago (33/34 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i2-559996 | eco_20261125_050013_1448739-i2 | 5_2_route | 3.6 | drt_violations best 116 last 116 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | prd-eco_retry_1795682851269662019-i1-2716571 | eco_retry_1795682851269662019-i1 | 5_2_route | 1.2 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | 5_2_route | 4.7 | drt_violations best 31 last 31 rows 22 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t5-331755 | dsdv_slice_c1x_C__t5 | 2_3_floorplan_tapcell | 1.6 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 20.4 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 20.4 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 20.4 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-454895 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.2 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 39.2 | drt_violations best 200 last 204 rows 58 | before-window best 206, window best 200 | PROGRESS: drt_violations improved 2.9 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 24.5 | drt_violations best 3665 last 9066 rows 19 | before-window best 3875, window best 3665 | PROGRESS: drt_violations improved 5.4 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 24.5 | drt_violations best 12441 last 12441 rows 15 | before-window best 18390, window best 12441 | PROGRESS: drt_violations improved 32.3 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 24.9 | drt_violations best 421 last 421 rows 37 | before-window best 724, window best 421 | PROGRESS: drt_violations improved 41.9 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 15.6 | drt_violations best 1752 last 10932 rows 18 | before-window best 57907, window best 1752 | PROGRESS: drt_violations improved 97.0 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 41.9 | drt_violations best 11 last 11 rows 55 | before-window best 13, window best 11 | PROGRESS: drt_violations improved 15.4 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 14.6 | drt_violations best 7 last 11 rows 53 | before-window best 174634, window best 7 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 16.7 | drt_violations best 9 last 9 rows 53 | before-window best 174806, window best 9 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 18.3 | drt_violations best 97668 last 97668 rows 3 | before-window best 545016, window best 97668 | PROGRESS: drt_violations improved 82.1 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 14.7 | drt_violations best 120549 last 120549 rows 2 | before-window best 486708, window best 120549 | PROGRESS: drt_violations improved 75.2 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 24.4 | drt_violations best 462 last 462 rows 20 | before-window best 77076, window best 462 | PROGRESS: drt_violations improved 99.4 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 15.2 | drt_violations best 27440 last 27440 rows 4 | before-window best 380531, window best 27440 | PROGRESS: drt_violations improved 92.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 15.4 | drt_violations best 495 last 495 rows 21 | before-window best 171015, window best 495 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 16.2 | drt_violations best 2346 last 2346 rows 15 | before-window best 176573, window best 2346 | PROGRESS: drt_violations improved 98.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 18.2 | drt_violations best 1013 last 1013 rows 22 | before-window best 7891, window best 1013 | PROGRESS: drt_violations improved 87.2 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 29.1 | drt_violations best 390 last 408 rows 58 | before-window best 392, window best 390 | PROGRESS: drt_violations: falling inside the active iteration (408 -> 395) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 16.7 | drt_violations best 545 last 545 rows 19 | before-window best 178567, window best 545 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 14.7 | drt_violations best 371 last 371 rows 36 | before-window best 162182, window best 371 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 16.8 | drt_violations best 386 last 386 rows 47 | before-window best 2573, window best 386 | PROGRESS: drt_violations improved 85.0 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfd79e8b6-2469832 | col_h9_r2__t1 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-slice_station__t40__cl1ea9de02-813226 | slice_station__t40 | 5_1_grt | 1.3 | repair_TNS best 0 last 0 rows 16 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 15.5 | drt_violations best 1774 last 1774 rows 15 | before-window best 167111, window best 1774 | PROGRESS: drt_violations improved 98.9 % in window |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 15.5 | drt_violations best 6 last 6 rows 42 | before-window best 211273, window best 6 | PROGRESS: drt_violations improved 100.0 % in window |  |
