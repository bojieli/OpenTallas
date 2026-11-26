# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-26 01:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 3, 'NO-PROGRESS': 4, 'GRT-STUCK': 1, 'GRT-LABEL': 1, 'YOUNG': 62, 'NO-DATA': 10, 'EXCLUDED': 3, 'KEEP': 1, 'PROGRESS': 23}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-2708094 | dsdv_slice_c1x_C__t5 | tt_setup_repair | 3.4 | last meaningful line -0.0 h ago (574/574 lines) | UNSIGNABLE: tt_setup_repair.log latest setup WNS -591.03 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | 5_1_grt | 11.5 | grt rounds 9 overflow 20:894 -> 25:15 -> 30:4 -> 35:8 -> 40:1 -> 45:2 | UNSIGNABLE: GRT overflow flat: overflow 1 at iteration 40 -> 2 at iteration 45: flat for 5 i | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | pregrt_ff_hold | 4.1 | repair_TNS best 122813 last 122813 rows 1 | before-window best 122813, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 5_1_grt | 16.2 | grt rounds 9 overflow 20:2305 -> 25:2156 -> 30:1933 -> 35:1923 -> 40:2127 -> 45:2007 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (35:1923 -> 40:2127 -> 45:2007; best 2007 | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 14.1 | grt rounds 8 overflow 15:2296 -> 20:2337 -> 25:2143 -> 30:1999 -> 35:1942 -> 40:2129 | UNSIGNABLE: GRT overflow flat: overflow 1942 at iteration 35 -> 2129 at iteration 40: flat f | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 20.6 | repair_Viol best 968 last 968 rows 93 | before-window best 968, window best 968 | NO-PROGRESS: repair_Viol best 968 vs 968 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 36.6 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel2 | dpkit-hd_mesh-3056327 | hd_mesh | pregrt_ff_hold | 3.7 | repair_TNS best 576579 last 576579 rows 1 | before-window best 576579, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | CANCELLED |
| epyc9 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-2575809 | ot_s81sl_leaf__t53 | 5_1_grt | 3.8 | grt rounds 2 overflow 5:18541 -> 10:3468 | GRT-LABEL: DESIGN-FAIL: overflow 3468 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_C__t1-3949489 | dsdv_slice_lepw_mu_C__t1 | 3_1_place_gp_skip_io | 1.2 | overflow best 0.8465 last 0.8611 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-hd_lep0N-712515 | hd_lep0N | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (8527/8527 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | lecaf-hdm-p6-retained-relays | lecaf-hdm-p6-retained-relays | - | 3.6 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-whole-exact-cohorts | lecaf-hdm-whole-exact-cohorts | - | 0.6 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-q9-sfw-f25e-archive-elab | lecaf-q9-sfw-f25e-archive-elab | gate.ys | 0.1 | last meaningful line 0.0 h ago (206959/206959 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | lecaf-rxsb-whole-mapped-1126 | lecaf-rxsb-whole-mapped | gate.ys | 0.2 | last meaningful line 0.2 h ago (22052/22052 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 6.8 | last meaningful line 4.8 h ago (33/34 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc10 | stoic_zhukovsky | stoic_zhukovsky | read.otrun | 0.0 | last meaningful line 0.0 h ago (5/5 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h10_r0_p4__t1__pv07945c1e-1752682 | col_h10_r0_p4__t1 | 3_3_place_gp | 0.3 | overflow best 0.3591 last 0.3591 rows 32 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p1__t1__pva2e3974f-1676548 | col_h9_r0_p1__t1 | 3_3_place_gp | 0.3 | overflow best 0.4718 last 0.4718 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-1727387 | col_h9_r0_p1__t1 | 3_3_place_gp | 0.3 | overflow best 0.4759 last 0.4759 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_2_route | 16.3 | drt_violations best 276288 last 276288 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1877449 | col_h9_r0_p5__t1 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (59/59 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p6__t1__pv082a7609-1907870 | col_h9_r0_p6__t1 | 3_5_place_dp | 0.2 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p6__t1__pv8241ebb8-1880576 | col_h9_r0_p6__t1 | 3_5_place_dp | 0.3 | repair_Violations best 5240 last 5240 rows 7 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-dsdv_slice_c1x_C__t3-3965387 | dsdv_slice_c1x_C__t3 | 3_3_place_gp | 2.3 | last meaningful line 0.1 h ago (49/49 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_c1x_C__t7-2765401 | dsdv_slice_c1x_C__t7 | 3_1_place_gp_skip_io | 1.6 | overflow best 0.8409 last 0.8409 rows 25 | YOUNG: stage 0.2 h < 1 h |  |
| epyc11 | dpkit-dsdv_slice_lepw_mus_C__t1-3987621 | dsdv_slice_lepw_mus_C__t1 | 3_3_place_gp | 2.3 | overflow best 0.7317 last 0.8247 rows 14 | YOUNG: stage 0.2 h < 1 h |  |
| epyc11 | dpkit-hd_lep0N_w-1753275 | hd_lep0N_w | 3_5_place_dp | 0.3 | last meaningful line 0.0 h ago (65/65 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-hd_lep0N_w-1880920 | hd_lep0N_w | 3_3_place_gp | 0.3 | overflow best 0.2205 last 0.2205 rows 35 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-ot_s81sl_leaf__t21-1673234 | ot_s81sl_leaf__t21 | 3_4_place_resized | 0.3 | repair_Remaining best 118003 last 118003 rows 24 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-ot_s81sl_leaf__t68-1709870 | ot_s81sl_leaf__t68 | 3_3_place_gp | 0.3 | overflow best 0.3443 last 0.3443 rows 35 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-svc_lo_dsdv_svc_rs_w__t1-1738997 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 0.3 | last meaningful line 0.0 h ago (395/395 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | prd-eco_retry_1795683784229614074-i1t-1592674 | eco_retry_1795683784229614074-i1t | 5_1_grt | 0.4 | last meaningful line 0.3 h ago (293/599 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1991043 | sle_stm_v2 | 5_2_route | 5.9 | drt_violations best 94499 last 94499 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-1997619 | sle_stm_v2 | 5_2_route | 5.9 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_2_route | 7.6 | drt_violations best 179686 last 179686 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | otc-1826332-19196 | 1826332 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261125_200405_3323313-i2t-2216991 | eco_20261125_200405_3323313-i2t | 5_2_route | 0.6 | last meaningful line 0.0 h ago (267/268 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | so_2744575_ff_9074 | so_2744575_ff_9074 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | so_2744575_tt_9074 | so_2744575_tt_9074 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 3.6 | last meaningful line 2.8 h ago (700/700 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc7 | otc-2739402-5290 | 2739402 | - | 8.1 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 2.3 | drt_violations best 11483 last 11483 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261126_090542_621054-i1t-2265448 | eco_20261126_090542_621054-i1t | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (299/946 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | lecaf-hc3-afda1e-twins | lecaf-hc3-afda1e-twins | - | 4.3 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261126_033711_2888564-i2t-1658020 | eco_20261126_033711_2888564-i2t | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (291/582 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-col-h9-r1--t1--cl49d7a23e--pv15cef3f7-grt-124727 | col-h9-r1--t1--cl49d7a23e--pv15cef3f7-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | tt_setup_measure | 3.2 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl911743eb-3766630 | col_h10_r0_p1__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3306 last 3306 rows 1290 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | pregrt_ff_hold | 4.1 | repair_TNS best 110094 last 110094 rows 1 | YOUNG: evidence 1.9 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | 5_1_grt | 4.4 | last meaningful line 0.2 h ago (273/1283 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-2823500 | col_h9_r1__t1 | pregrt_ff_hold | 3.7 | repair_TNS best 71970 last 71970 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2325128 | col_h9_r1__t1 | pregrt_ff_hold | 3.9 | repair_TNS best 110976 last 110976 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8aaf8508-3602152 | col_h9_r1__t1 | 4_1_cts | 0.2 | repair_Violations best 8 last 83 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-3901907 | col_h9_r1__t1 | pregrt_ff_hold | 3.5 | repair_TNS best 99737.1 last 99737.1 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2382304 | col_h9_r1__t1 | pregrt_ff_hold | 3.8 | repair_TNS best 177431 last 177431 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-2530599 | col_h9_r1__t1 | pregrt_ff_hold | 3.8 | repair_TNS best 47356.8 last 47356.8 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvfef7c177-3709744 | col_h9_r2__t1 | pregrt_ff_hold | 1.1 | repair_TNS best 142578 last 142578 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | tt_setup_repair_grt | 4.3 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfd79e8b6-2469832 | col_h9_r2__t1 | pregrt_ff_hold | 2.2 | repair_TNS best 26509.4 last 26509.4 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-4056356 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 5_1_grt | 14.6 | last meaningful line 4.3 h ago (284/1294 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mus_C__t1-1648329 | dsdv_slice_lepw_mus_C__t1 | 3_4_place_resized | 4.0 | repair_Remaining best 38742 last 38742 rows 329 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t1-3555509 | ot_s81sl_leaf__t1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (6584/6584 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-479268 | sle_su_l1 | postcts_gate_TT | 3.4 | last meaningful line 0.0 h ago (52698/52698 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t26-3959180 | slice_station__t26 | tt_setup_repair_grt | 1.0 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t29__cl2e5c855a-3827558 | slice_station__t29 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2232/2232 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t29__clc7772371-1992482 | slice_station__t29 | 5_1_grt | 0.5 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__cl1ea9de02-813226 | slice_station__t40 | 5_1_grt | 0.8 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t45-1580954 | slice_station__t45 | 5_2_route | 4.0 | drt_violations best 8397 last 8397 rows 3 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 5_1_grt | 3.9 | grt_hold_TNS best 122094 last 122094 rows 2 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_072708_1527702-i1-3266022 | eco_20261126_072708_1527702-i1 | 5_2_route | 2.0 | last meaningful line 0.3 h ago (282/283 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_091926_2909746-i1t-3764749 | eco_20261126_091926_2909746-i1t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (154/154 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_retry_1795673019361579887-i1t-300819 | eco_retry_1795673019361579887-i1t | 5_2_route | 3.4 | drt_violations best 80636 last 80636 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 5.2 |  | NO-DATA: no log found |  |
| intel1 | lecq9-963f0492a10e | lecq9-963f0492a10e | - | 5.3 |  | NO-DATA: no log found |  |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 6.7 | last meaningful line 3.0 h ago (33/34 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i2-559996 | eco_20261125_050013_1448739-i2 | 5_2_route | 3.1 | drt_violations best 116 last 116 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | prd-eco_retry_1795682851269662019-i1-2716571 | eco_retry_1795682851269662019-i1 | 5_1_grt | 0.7 | repair_Remaining best 455732 last 455732 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | 5_2_route | 4.2 | drt_violations best 149 last 149 rows 17 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t5-331755 | dsdv_slice_c1x_C__t5 | 1_1_yosys_canonicalize | 1.1 | last meaningful line 0.3 h ago (132/132 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 19.9 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 19.9 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 19.9 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-454895 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.7 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 38.7 | drt_violations best 200 last 204 rows 58 | before-window best 212, window best 200 | PROGRESS: drt_violations improved 5.7 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 24.0 | drt_violations best 3665 last 9066 rows 19 | before-window best 4336, window best 3665 | PROGRESS: drt_violations improved 15.5 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 24.0 | drt_violations best 12441 last 12441 rows 15 | before-window best 18390, window best 12441 | PROGRESS: drt_violations improved 32.3 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 24.4 | drt_violations best 426 last 426 rows 36 | before-window best 724, window best 426 | PROGRESS: drt_violations improved 41.2 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 15.1 | drt_violations best 1752 last 10932 rows 18 | before-window best 224764, window best 1752 | PROGRESS: drt_violations improved 99.2 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 41.4 | drt_violations best 11 last 11 rows 55 | before-window best 13, window best 11 | PROGRESS: drt_violations improved 15.4 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 14.1 | drt_violations best 7 last 11 rows 53 | before-window best 174634, window best 7 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 16.2 | drt_violations best 9 last 9 rows 53 | before-window best 174806, window best 9 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 17.8 | drt_violations best 97668 last 97668 rows 3 | before-window best 545016, window best 97668 | PROGRESS: drt_violations improved 82.1 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 14.2 | drt_violations best 486708 last 486708 rows 1 | before-window best 486708, window best 486708 | PROGRESS: drt_violations: active iteration at 202051 < best completed total 486708 (in-ite |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 23.9 | drt_violations best 541 last 541 rows 17 | before-window best 118691, window best 541 | PROGRESS: drt_violations improved 99.5 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 14.7 | drt_violations best 73160 last 73160 rows 3 | before-window best 380531, window best 73160 | PROGRESS: drt_violations improved 80.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 14.9 | drt_violations best 554 last 1723 rows 18 | before-window best 171015, window best 554 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 15.7 | drt_violations best 3157 last 3157 rows 14 | before-window best 176573, window best 3157 | PROGRESS: drt_violations improved 98.2 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 17.7 | drt_violations best 1022 last 1276 rows 20 | before-window best 28283, window best 1022 | PROGRESS: drt_violations improved 96.4 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 28.6 | drt_violations best 390 last 408 rows 58 | before-window best 392, window best 390 | PROGRESS: drt_violations: falling inside the active iteration (408 -> 395) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 16.2 | drt_violations best 681 last 681 rows 17 | before-window best 178567, window best 681 | PROGRESS: drt_violations improved 99.6 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 14.2 | drt_violations best 377 last 377 rows 31 | before-window best 162182, window best 377 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | pregrt_ff_hold | 3.6 | repair_Violations best 70275 last 70300 rows 47 | before-window best 506664, window best 70275 | PROGRESS: repair_Violations improved 86.1 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 16.3 | drt_violations best 386 last 386 rows 45 | before-window best 3486, window best 386 | PROGRESS: drt_violations improved 88.9 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-4156698 | col_h9_r2__t1 | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 15.0 | drt_violations best 2509 last 2509 rows 14 | before-window best 167111, window best 2509 | PROGRESS: drt_violations improved 98.5 % in window |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 15.0 | drt_violations best 6 last 6 rows 42 | before-window best 211273, window best 6 | PROGRESS: drt_violations improved 100.0 % in window |  |
