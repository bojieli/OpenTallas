# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-26 01:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 5, 'GRT-STUCK': 1, 'GRT-LABEL': 1, 'YOUNG': 56, 'NO-DATA': 14, 'EXCLUDED': 3, 'KEEP': 1, 'PROGRESS': 29}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | 5_1_grt | 11.2 | grt rounds 9 overflow 20:894 -> 25:15 -> 30:4 -> 35:8 -> 40:1 -> 45:2 | UNSIGNABLE: GRT overflow flat: overflow 1 at iteration 40 -> 2 at iteration 45: flat for 5 i | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | pregrt_ff_hold | 3.8 | repair_TNS best 122813 last 122813 rows 1 | before-window best 122813, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 5_1_grt | 16.0 | grt rounds 9 overflow 20:2305 -> 25:2156 -> 30:1933 -> 35:1923 -> 40:2127 -> 45:2007 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (35:1923 -> 40:2127 -> 45:2007; best 2007 | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 13.8 | grt rounds 8 overflow 15:2296 -> 20:2337 -> 25:2143 -> 30:1999 -> 35:1942 -> 40:2129 | UNSIGNABLE: GRT overflow flat: overflow 1942 at iteration 35 -> 2129 at iteration 40: flat f | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | pregrt_ff_hold | 3.3 | repair_TNS best 256.046 last 256.046 rows 1 | before-window best 256.046, window best 256.046 | NO-PROGRESS: repair_TNS best 256.046 vs 256.046 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 20.4 | repair_Viol best 968 last 968 rows 82 | before-window best 968, window best 968 | NO-PROGRESS: repair_Viol best 968 vs 968 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 36.4 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel2 | dpkit-hd_mesh-3056327 | hd_mesh | pregrt_ff_hold | 3.4 | repair_TNS best 576579 last 576579 rows 1 | before-window best 576579, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc9 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-2575809 | ot_s81sl_leaf__t53 | 5_1_grt | 3.5 | grt rounds 2 overflow 5:18541 -> 10:3468 | GRT-LABEL: DESIGN-FAIL: overflow 3468 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-2708094 | dsdv_slice_c1x_C__t5 | 4_1_cts | 3.1 | last meaningful line 0.1 h ago (7671/7671 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_C__t1-3949489 | dsdv_slice_lepw_mu_C__t1 | 1_2_yosys | 0.9 | last meaningful line 0.0 h ago (227/227 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-712515 | hd_lep0N | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (8299/8299 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | lecaf-hdm-p6-retained-relays | lecaf-hdm-p6-retained-relays | - | 3.4 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-whole-exact-cohorts | lecaf-hdm-whole-exact-cohorts | - | 0.3 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-q9-sfw-archive-elab | lecaf-q9-sfw-archive-elab | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-d7634e345491-standalone-twins | lecq9-d7634e345491-standalone-twins | - | 1.5 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-hd-ctl-whole-guarded-1125 | lecq9-hd-ctl-whole-guarded | - | 1.3 |  | NO-DATA: no log found |  |
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 6.5 | last meaningful line 4.5 h ago (33/34 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc11 | dpkit-col_h10_r0_p4__t1__pv07945c1e-1752682 | col_h10_r0_p4__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3842 last 3842 rows 930 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p1__t1__pva2e3974f-1676548 | col_h9_r0_p1__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 1046 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-1727387 | col_h9_r0_p1__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 627 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_2_route | 16.0 | drt_violations best 276288 last 276288 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1877449 | col_h9_r0_p5__t1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (251/251 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1742492 | col_h9_r0_p6__t1 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (1534/1534 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p6__t1__pv8241ebb8-1880576 | col_h9_r0_p6__t1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (178/178 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_c1x_C__t3-3965387 | dsdv_slice_c1x_C__t3 | 3_1_place_gp_skip_io | 2.1 | overflow best 0.7004 last 0.7004 rows 29 | YOUNG: stage 0.2 h < 1 h |  |
| epyc11 | dpkit-dsdv_slice_c1x_C__t7-2765401 | dsdv_slice_c1x_C__t7 | 1_synth | 1.3 | last meaningful line 0.0 h ago (1463/1463 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_lepw_mus_C__t1-3987621 | dsdv_slice_lepw_mus_C__t1 | 3_1_place_gp_skip_io | 2.1 | overflow best 0.2606 last 0.2606 rows 38 | YOUNG: stage 0.2 h < 1 h |  |
| epyc11 | dpkit-hd_lep0N_w-1753275 | hd_lep0N_w | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-hd_lep0N_w-1880920 | hd_lep0N_w | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (185/185 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-ot_s81sl_leaf__t21-1673234 | ot_s81sl_leaf__t21 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (1085/1085 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-ot_s81sl_leaf__t68-1709870 | ot_s81sl_leaf__t68 | 2_1_floorplan | 0.1 | repair_Viol best 1225 last 1225 rows 1257 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-svc_lo_dsdv_svc_rs_w__t1-1738997 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | prd-eco_retry_1795683784229614074-i1t-1592674 | eco_retry_1795683784229614074-i1t | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (293/599 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-2967544 | sle_hc0 | generate_abstract | 7.4 | last meaningful line 0.1 h ago (29/29 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1991043 | sle_stm_v2 | 5_2_route | 5.6 | drt_violations best 94499 last 94499 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-1997619 | sle_stm_v2 | 5_2_route | 5.6 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_2_route | 7.4 | drt_violations best 179686 last 179686 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | otc-1826332-19196 | 1826332 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261125_200405_3323313-i2t-2216991 | eco_20261125_200405_3323313-i2t | 5_2_route | 0.4 | last meaningful line 0.0 h ago (253/253 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 3.3 | last meaningful line 2.5 h ago (700/700 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | otc-2739402-5290 | 2739402 | - | 7.8 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 2.0 | drt_violations best 11483 last 11483 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261126_090542_621054-i1t-2265448 | eco_20261126_090542_621054-i1t | 5_1_grt | 0.1 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | lecaf-hc3-afda1e-standalone-twins | lecaf-hc3-afda1e-standalone-twins | - | 1.4 |  | NO-DATA: no log found |  |
| epyc8 | lecaf-hc3-afda1e-twins | lecaf-hc3-afda1e-twins | - | 4.0 |  | NO-DATA: no log found |  |
| epyc8 | so_260689_ff_21944 | so_260689_ff_21944 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (35/35 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | so_260689_tt_21944 | so_260689_tt_21944 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (35/35 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | tt_setup_repair | 2.9 | last meaningful line 0.0 h ago (409/409 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | pregrt_ff_hold | 3.9 | repair_TNS best 110094 last 110094 rows 1 | YOUNG: evidence 1.6 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | 5_1_grt | 4.2 | last meaningful line 0.1 h ago (162/162 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-2823500 | col_h9_r1__t1 | pregrt_ff_hold | 3.5 | repair_TNS best 71970 last 71970 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv15cef3f7-1548753 | col_h9_r1__t1 | 3_4_place_resized | 0.4 | last meaningful line -0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2325128 | col_h9_r1__t1 | pregrt_ff_hold | 3.6 | repair_TNS best 110976 last 110976 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2382304 | col_h9_r1__t1 | pregrt_ff_hold | 3.6 | repair_TNS best 177431 last 177431 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-2530599 | col_h9_r1__t1 | pregrt_ff_hold | 3.6 | repair_TNS best 47356.8 last 47356.8 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvfef7c177-3709744 | col_h9_r2__t1 | pregrt_ff_hold | 0.8 | repair_TNS best 142578 last 142578 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | 5_1_grt | 4.0 | last meaningful line 0.0 h ago (2390/2405 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfd79e8b6-2469832 | col_h9_r2__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 26509.4 last 26509.4 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 5_1_grt | 14.4 | last meaningful line 4.0 h ago (284/1294 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mus_C__t1-1648329 | dsdv_slice_lepw_mus_C__t1 | 3_3_place_gp | 3.8 | overflow best 0.5114 last 0.5114 rows 50 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-479268 | sle_su_l1 | postcts_gate_TT | 3.1 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t29__clc7772371-1992482 | slice_station__t29 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (2202/2202 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__cl1ea9de02-813226 | slice_station__t40 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (2823/2823 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t45-1580954 | slice_station__t45 | 5_2_route | 3.8 | drt_violations best 15658 last 15658 rows 2 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 5_1_grt | 3.7 | repair_TNS best 124514 last 124514 rows 6 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_072708_1527702-i1-3266022 | eco_20261126_072708_1527702-i1 | 5_2_route | 1.8 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | prd-eco_retry_1795673019361579887-i1t-300819 | eco_retry_1795673019361579887-i1t | 5_2_route | 3.1 | drt_violations best 80636 last 80636 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | so_2526820_ff_26847 | so_2526820_ff_26847 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc9 | so_2526820_tt_26847 | so_2526820_tt_26847 | signoff | 0.2 |  | NO-DATA: empty log |  |
| intel1 | ap-ageom-__cl05696ed1-dump-3482562 | ap-ageom- | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 4.9 |  | NO-DATA: no log found |  |
| intel1 | lecq9-963f0492a10e | lecq9-963f0492a10e | - | 5.0 |  | NO-DATA: no log found |  |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 6.5 | last meaningful line 2.8 h ago (33/34 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i2-559996 | eco_20261125_050013_1448739-i2 | 5_2_route | 2.9 | drt_violations best 116 last 116 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv1c15776f-444391 | col_h9_r1__t1 | 3_3_place_gp | 0.2 | overflow best 0.4761 last 0.4783 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | 5_2_route | 4.0 | drt_violations best 169 last 169 rows 16 | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t5-331755 | dsdv_slice_c1x_C__t5 | 1_1_yosys_canonicalize | 0.9 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-2251165 | kv3_io_ft | abstract_exact | 2.5 | last meaningful line 0.8 h ago (4/4 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 19.7 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 19.7 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 19.7 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-454895 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.5 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 38.4 | drt_violations best 200 last 204 rows 58 | before-window best 212, window best 200 | PROGRESS: drt_violations improved 5.7 % in window |  |
| epyc11 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-1350900 | col_h10_r2__t1 | 3_5_place_dp | 0.3 | repair_Violations best 0 last 0 rows 45 | PROGRESS: repair_Violations reached 0 |  |
| epyc11 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-1341317 | col_h9_r1__t1 | 3_5_place_dp | 0.3 | repair_Violations best 0 last 0 rows 24 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 23.7 | drt_violations best 3665 last 9066 rows 19 | before-window best 4336, window best 3665 | PROGRESS: drt_violations improved 15.5 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 23.7 | drt_violations best 12441 last 12441 rows 15 | before-window best 18390, window best 12441 | PROGRESS: drt_violations improved 32.3 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 24.1 | drt_violations best 426 last 426 rows 35 | before-window best 783, window best 426 | PROGRESS: drt_violations improved 45.6 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 16.9 | drt_violations best 11088 last 19300 rows 19 | before-window best 11831, window best 11088 | PROGRESS: drt_violations improved 6.3 % in window |  |
| epyc8 | dpkit-hd_lep0N_w-1738505 | hd_lep0N_w | 4_2_tapbal_grt | 1.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 14.9 | drt_violations best 1752 last 10932 rows 18 | before-window best 224764, window best 1752 | PROGRESS: drt_violations improved 99.2 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 41.1 | drt_violations best 11 last 11 rows 55 | before-window best 13, window best 11 | PROGRESS: drt_violations improved 15.4 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 13.9 | drt_violations best 7 last 11 rows 53 | before-window best 174634, window best 7 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 15.9 | drt_violations best 9 last 9 rows 53 | before-window best 174806, window best 9 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 17.5 | drt_violations best 147781 last 147781 rows 2 | before-window best 545016, window best 147781 | PROGRESS: drt_violations improved 72.9 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 13.9 | drt_violations best 486708 last 486708 rows 1 | before-window best 486708, window best 486708 | PROGRESS: drt_violations: active iteration at 228534 < best completed total 486708 (in-ite |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 23.7 | drt_violations best 1108 last 1108 rows 15 | before-window best 118691, window best 1108 | PROGRESS: drt_violations improved 99.1 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 14.5 | drt_violations best 73160 last 73160 rows 3 | before-window best 380531, window best 73160 | PROGRESS: drt_violations improved 80.8 % in window |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-3901907 | col_h9_r1__t1 | 4_2_tapbal_grt | 3.3 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 14.7 | drt_violations best 554 last 554 rows 17 | before-window best 171015, window best 554 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 15.5 | drt_violations best 4404 last 4404 rows 13 | before-window best 176573, window best 4404 | PROGRESS: drt_violations improved 97.5 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 17.5 | drt_violations best 1022 last 1276 rows 20 | before-window best 42293, window best 1022 | PROGRESS: drt_violations improved 97.6 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 28.4 | drt_violations best 390 last 408 rows 58 | before-window best 392, window best 390 | PROGRESS: drt_violations: falling inside the active iteration (408 -> 395) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 16.0 | drt_violations best 913 last 913 rows 16 | before-window best 178567, window best 913 | PROGRESS: drt_violations improved 99.5 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 14.0 | drt_violations best 377 last 377 rows 30 | before-window best 162182, window best 377 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 16.0 | drt_violations best 388 last 388 rows 44 | before-window best 3747, window best 388 | PROGRESS: drt_violations improved 89.6 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-4156698 | col_h9_r2__t1 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-slice_station__t26-3959180 | slice_station__t26 | 5_1_grt | 0.8 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 14.8 | drt_violations best 3480 last 3480 rows 13 | before-window best 167111, window best 3480 | PROGRESS: drt_violations improved 97.9 % in window |  |
| intel1 | prd-eco_retry_1795682851269662019-i1-2716571 | eco_retry_1795682851269662019-i1 | 5_1_grt | 0.4 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 14.7 | drt_violations best 6 last 6 rows 41 | before-window best 211273, window best 6 | PROGRESS: drt_violations improved 100.0 % in window |  |
