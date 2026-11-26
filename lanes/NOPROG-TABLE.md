# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 23:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'GRT-STUCK': 1, 'NO-PROGRESS': 2, 'GRT-LABEL': 2, 'YOUNG': 89, 'NO-DATA': 26, 'KEEP': 2, 'EXCLUDED': 3, 'PROGRESS': 27}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | 5_1_grt | 9.2 | grt rounds 9 overflow 20:894 -> 25:15 -> 30:4 -> 35:8 -> 40:1 -> 45:2 | UNSIGNABLE: GRT overflow flat: overflow 1 at iteration 40 -> 2 at iteration 45: flat for 5 i | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-hd_lep0N-2958360 | hd_lep0N | 4_2_tapbal_grt | 3.1 | last meaningful line 1.5 h ago (48/52 lines) | UNSIGNABLE: 4_1_cts.json latest setup WNS -320.71 ps (< -300, gate TT >= -42); job age 3.1 h | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 5_1_grt | 14.0 | grt rounds 8 overflow 15:2262 -> 20:2305 -> 25:2156 -> 30:1933 -> 35:1923 -> 40:2127 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (30:1933 -> 35:1923 -> 40:2127; best 1923 | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 18.4 | repair_Viol best 968 last 968 rows 1 | before-window best 968, window best 968 | NO-PROGRESS: repair_Viol best 968 vs 968 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 34.4 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 11.8 | grt rounds 7 overflow 10:3237 -> 15:2296 -> 20:2337 -> 25:2143 -> 30:1999 -> 35:1942 | GRT-LABEL: DESIGN-FAIL: overflow 3237 at round 10 > 1000 |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 14.0 | grt rounds 2 overflow 5:78485 -> 10:36690 | GRT-LABEL: DESIGN-FAIL: overflow 36690 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-2708094 | dsdv_slice_c1x_C__t5 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (42/42 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-hd_serdes-6683 | hd_serdes | 4_2_tapbal_grt | 0.5 | last meaningful line 0.2 h ago (48/97 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_a_v2__clf4365a62-199111 | slw_st_a_v2 | generate_abstract | 3.7 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | lecaf-colls-73016a-ctl-e10 | lecaf-colls-73016a-ctl-e10 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-full | lecaf-hdm-full | - | 3.9 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-p1-retained-relays | lecaf-hdm-p1-retained-relays | - | 1.6 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-p6-retained-relays | lecaf-hdm-p6-retained-relays | - | 1.4 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-rxsb-sq-stage-map-1125 | lecaf-rxsb-sq-stage-map | bb.ys | 0.0 | last meaningful line 0.0 h ago (983/983 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | lecq9-d7634e345491 | lecq9-d7634e345491 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-d7634e345491-proved-twins | lecq9-d7634e345491-proved-twins | - | 0.2 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-d7634e345491-q-bad-relays | lecq9-d7634e345491-q-bad-relays | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 4.5 | last meaningful line 2.5 h ago (33/34 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | otc-3652144-28954 | 3652144 | flow | 0.7 | last meaningful line 0.0 h ago (4172/4172 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-2456208 | col_h10_r0_p1__t1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.5176 last 0.5176 rows 31 | YOUNG: stage 0.2 h < 1 h |  |
| epyc11 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-2455280 | col_h10_r0_p1__t1 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (302/302 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2088775 | col_h10_r0_p4__t1 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-3246648 | col_h10_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.3859 last 0.4008 rows 27 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-2555808 | col_h10_r1__t1 | 3_5_place_dp | 0.5 | repair_Violations best 855042 last 855046 rows 38 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h10_r1__t1__cl95b37463__pvce76611c-3341045 | col_h10_r1__t1 | 3_3_place_gp | 0.2 | overflow best 0.442 last 0.4461 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3588922 | col_h9_r0_p2__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (115/115 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-3696138 | col_h9_r0_p2__t1 | 2_3_floorplan_tapcell | 0.2 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv4cfde03b-3327088 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8736 last 0.8736 rows 7 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvcd8810ba-3099665 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8259 last 0.8259 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-2910190 | col_h9_r0_p4__t1 | 3_3_place_gp | 0.4 | overflow best 0.4584 last 0.4775 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_2_route | 14.0 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvbca8d846-2656882 | col_h9_r0_p5__t1 | 3_3_place_gp | 0.4 | overflow best 0.5257 last 0.5257 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p6__t1__pv6398a5b7-4179111 | col_h9_r0_p6__t1 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r1__t1__cl49d7a23e__pv534ef85e-3096310 | col_h9_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.2284 last 0.2284 rows 35 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r1__t1__clf32cde8d__pvd9381c1d-3673017 | col_h9_r1__t1 | 3_2_place_iop | 0.2 | last meaningful line 0.0 h ago (7/7 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_c1x_C__t3-3965387 | dsdv_slice_c1x_C__t3 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_iq_C__t1-3149121 | dsdv_slice_iq_C__t1 | 3_3_place_gp | 1.3 | overflow best 0.6341 last 0.6356 rows 44 | YOUNG: stage 0.5 h < 1 h |  |
| epyc11 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1450190 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_lepw_mus_C__t1-3987621 | dsdv_slice_lepw_mus_C__t1 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-ot_s81sl_leaf__t11-1486156 | ot_s81sl_leaf__t11 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (89/89 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | otc-2376318-26230 | 2376318 | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (453/453 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | so_1789175_ff_71179 | so_1789175_ff_71179 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc12 | so_1789175_tt_71179 | so_1789175_tt_71179 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-2967544 | sle_hc0 | 5_2_route | 5.4 | drt_violations best 113905 last 113905 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1991043 | sle_stm_v2 | 5_2_route | 3.6 | last meaningful line 0.0 h ago (262/263 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-1997619 | sle_stm_v2 | postcts_gate_TT | 3.6 | last meaningful line -0.0 h ago (17193/17193 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_2_route | 5.4 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261125_200405_3323313-i1-2828164 | eco_20261125_200405_3323313-i1 | 5_2_route | 0.8 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261125_211504_2977850-i1-3586116 | eco_20261125_211504_2977850-i1 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (287/1403 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t4-1017259 | dsdv_slice_c1x_C__t4 | 3_5_place_dp | 2.3 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3327555 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 2.8 | last meaningful line 1.3 h ago (36/36 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-gunit__t1-1078622 | gunit__t1 | 3_5_place_dp | 0.7 | last meaningful line 0.2 h ago (39/39 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t45-1891450 | ot_s81sl_leaf__t45 | 3_3_place_gp | 0.4 | last meaningful line 0.1 h ago (53/53 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t51-1607646 | slice_station__t51 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | 5_2_route | 12.7 | drt_violations best 18146 last 18146 rows 2 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 1.3 | last meaningful line 0.5 h ago (700/700 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | lecq9-hd-ctl-seq-guarded-discovery-r2-1125 | lecq9-hd-ctl-seq-guarded-discovery-r2 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc7 | otc-2739402-5290 | 2739402 | - | 5.8 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p1__t1__pva2e3974f-1993401 | col_h9_r0_p1__t1 | 3_3_place_gp | 0.3 | overflow best 0.4758 last 0.4758 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t10-3190993 | dsdv_slice_c1x_C__t10 | 3_3_place_gp | 2.2 | last meaningful line 0.0 h ago (50/50 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t6-4113643 | dsdv_slice_c1x_C__t6 | 3_1_place_gp_skip_io | 2.0 | overflow best 0.5011 last 0.5011 rows 34 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_c3x_C__t1-3731856 | dsdv_slice_c3x_C__t1 | 3_3_place_gp | 2.1 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-hd_lep0N_w-3187026 | hd_lep0N_w | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (257/257 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v3e-3103773 | kv3_pv_v3e | 3_5_place_dp | 1.1 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v7e-2857250 | kv3_pv_v7e | 3_5_place_dp | 1.2 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-seqhost__t1-556663 | seqhost__t1 | 3_3_place_gp | 0.7 | overflow best 0.467 last 0.467 rows 34 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | lecaf-hc3-afda1e-twins | lecaf-hc3-afda1e-twins | - | 2.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-1530472-10583 | 1530472 | - | 2.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-1589750-5019 | 1589750 | - | 2.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-2693994-26282 | 2693994 | - | 2.3 |  | NO-DATA: no log found |  |
| epyc8 | otc-3222460-28392 | 3222460 | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-3731784-29079 | 3731784 | - | 6.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-941401-14145 | 941401 | - | 2.7 |  | NO-DATA: no log found |  |
| epyc8 | prd-count-p1_tc-312208 | count-p1_tc | prd_count_p1_tc | 0.2 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261126_033711_2888564-i1-671626 | eco_20261126_033711_2888564-i1 | 5_1_grt | 0.7 | last meaningful line 0.4 h ago (293/624 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-bk_sel__t2-1028644 | bk_sel__t2 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (3894/3894 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | generate_abstract | 15.5 | last meaningful line 0.0 h ago (71/71 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | 5_2_route | 11.4 | drt_violations best 89851 last 89851 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | pregrt_ff_hold | 2.2 | repair_TNS best 13231.2 last 13231.2 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 11.9 | drt_violations best 486708 last 486708 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | pregrt_ff_hold | 1.8 | repair_TNS best 122813 last 122813 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-2823500 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.5 | last meaningful line 0.8 h ago (61/79 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2325128 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.6 | last meaningful line 1.0 h ago (61/80 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-3901907 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.3 | last meaningful line 0.5 h ago (61/76 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2382304 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.6 | last meaningful line 1.0 h ago (61/80 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-2530599 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.6 | last meaningful line 0.8 h ago (61/80 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 124234 last 124234 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 124624 last 124624 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 5_1_grt | 12.4 | last meaningful line 2.0 h ago (284/1291 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mus_C__t1-1648329 | dsdv_slice_lepw_mus_C__t1 | 1_1_yosys_canonicalize | 1.8 | last meaningful line 0.5 h ago (132/132 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-2575809 | ot_s81sl_leaf__t53 | pregrt_ff_hold | 1.5 | repair_TNS best 816256 last 816256 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-479268 | sle_su_l1 | pregrt_ff_hold | 1.1 | repair_TNS best 63501.9 last 63501.9 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-slice_station__t23-1100978 | slice_station__t23 | 5_2_route | 1.0 | last meaningful line 0.1 h ago (217/217 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t45-1580954 | slice_station__t45 | 5_2_route | 1.8 | last meaningful line 0.2 h ago (241/242 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | pregrt_ff_hold | 1.7 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc9 | prd-eco_retry_1795673019361579887-i1t-300819 | eco_retry_1795673019361579887-i1t | 5_2_route | 1.1 | last meaningful line 0.1 h ago (267/267 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-1625008 | kv3_pc_v1 | 3_5_place_dp | 2.0 | last meaningful line 0.3 h ago (32/32 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | lecq9-1e4ed353bf9a | lecq9-1e4ed353bf9a | - | 3.1 |  | NO-DATA: no log found |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 2.9 |  | NO-DATA: no log found |  |
| intel1 | lecq9-963f0492a10e | lecq9-963f0492a10e | - | 3.0 |  | NO-DATA: no log found |  |
| intel1 | lecq9-abc37a821c70 | lecq9-abc37a821c70 | - | 3.0 |  | NO-DATA: no log found |  |
| intel1 | lecq9-c8be6220489b | lecq9-c8be6220489b | - | 2.1 |  | NO-DATA: no log found |  |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 4.5 | last meaningful line 0.8 h ago (33/34 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | otc-3637178-17557 | 3637178 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-3878162-6060 | 3878162 | signoff | 1.6 | last meaningful line 1.5 h ago (3/3 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i2-559996 | eco_20261125_050013_1448739-i2 | 5_2_route | 0.9 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | so_2859609_ff_52956 | so_2859609_ff_52956 | signoff | 0.4 |  | NO-DATA: empty log |  |
| intel1 | so_2859609_tt_52956 | so_2859609_tt_52956 | signoff | 0.4 |  | NO-DATA: empty log |  |
| intel2 | dpkit-coll_ftm-626876 | coll_ftm | 5_2_route | 2.2 | drt_violations best 9847 last 9847 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | 5_2_route | 2.0 | last meaningful line 0.1 h ago (249/250 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-hd_mesh-3056327 | hd_mesh | pregrt_ff_hold | 1.4 | repair_TNS best 576579 last 576579 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-hd_spn_wshim_rx-3049643 | hd_spn_wshim_rx | abstract_exact | 1.4 | last meaningful line 0.3 h ago (4/4 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-2250279 | hd_turn_a | abstract_exact | 0.5 | last meaningful line 0.1 h ago (4/4 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8e7d31598-3690925 | kv3_pc_v1 | 3_5_place_dp | 2.7 | last meaningful line 1.0 h ago (32/32 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v2-1217990 | kv3_pv_v2 | 3_3_place_gp | 0.6 | overflow best 0.1939 last 0.1939 rows 38 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-kv3_pv_v6n-1232246 | kv3_pv_v6n | 3_3_place_gp | 0.6 | overflow best 0.4994 last 0.5058 rows 18 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | otc-4164407-11341 | 4164407 | gold_b.ys | 1.1 | last meaningful line 0.8 h ago (96320/96320 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | so_748319_ff_3843 | so_748319_ff_3843 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel2 | so_748319_tt_3843 | so_748319_tt_3843 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc11 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-3023209 | col_h10_r1__t1 | 3_4_place_resized | 0.3 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc11 | dpkit-col_h9_r1__t1__cl49d7a23e__pv62bca836-2833919 | col_h9_r1__t1 | 3_5_place_dp | 0.4 |  | KEEP: col_h9_r1__t1__cl49d7a23e__pv62bca836	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 17.7 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 17.7 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 17.7 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 36.4 | drt_violations best 200 last 204 rows 58 | before-window best 212, window best 200 | PROGRESS: drt_violations improved 5.7 % in window |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | 5_2_route | 14.0 | drt_violations best 414 last 416 rows 33 | before-window best 255884, window best 414 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc7 | dpkit-serdes__t4-1793881 | serdes__t4 | 4_1_cts | 0.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 21.7 | drt_violations best 3665 last 21095 rows 18 | before-window best 9935, window best 3665 | PROGRESS: drt_violations improved 63.1 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 21.7 | drt_violations best 13518 last 13518 rows 14 | before-window best 23481, window best 13518 | PROGRESS: drt_violations improved 42.4 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 22.1 | drt_violations best 448 last 448 rows 30 | before-window best 1784, window best 448 | PROGRESS: drt_violations improved 74.9 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 14.9 | drt_violations best 11088 last 44179 rows 18 | before-window best 20275, window best 11088 | PROGRESS: drt_violations improved 45.3 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 12.9 | drt_violations best 2253 last 2253 rows 13 | before-window best 224764, window best 2253 | PROGRESS: drt_violations improved 99.0 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 39.1 | drt_violations best 13 last 13 rows 53 | before-window best 13, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | 4_2_tapbal_grt | 1.9 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 11.9 | drt_violations best 18 last 19 rows 23 | before-window best 174634, window best 18 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 13.9 | drt_violations best 13 last 14 rows 51 | before-window best 174806, window best 13 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 15.5 | drt_violations best 545016 last 545016 rows 1 | before-window best 545016, window best 545016 | PROGRESS: drt_violations: active iteration at 279773 < best completed total 545016 (in-ite |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 21.7 | drt_violations best 7277 last 7277 rows 9 | before-window best 470122, window best 7277 | PROGRESS: drt_violations improved 98.5 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 12.5 | drt_violations best 380531 last 380531 rows 1 | before-window best 380531, window best 380531 | PROGRESS: drt_violations: active iteration at 132622 < best completed total 380531 (in-ite |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 12.7 | drt_violations best 3768 last 3768 rows 10 | before-window best 171015, window best 3768 | PROGRESS: drt_violations improved 97.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 13.5 | drt_violations best 6475 last 6475 rows 10 | before-window best 176573, window best 6475 | PROGRESS: drt_violations improved 96.3 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 15.5 | drt_violations best 1249 last 1249 rows 16 | before-window best 178781, window best 1249 | PROGRESS: drt_violations improved 99.3 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 26.4 | drt_violations best 390 last 408 rows 58 | before-window best 392, window best 390 | PROGRESS: drt_violations: falling inside the active iteration (408 -> 395) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 14.0 | drt_violations best 5417 last 5417 rows 10 | before-window best 178567, window best 5417 | PROGRESS: drt_violations improved 97.0 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 12.0 | drt_violations best 668 last 668 rows 14 | before-window best 162182, window best 668 | PROGRESS: drt_violations improved 99.6 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 5_2_route | 14.8 | drt_violations best 368 last 371 rows 42 | before-window best 159056, window best 368 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 14.0 | drt_violations best 399 last 399 rows 31 | before-window best 157970, window best 399 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-4156698 | col_h9_r2__t1 | 4_1_cts | 0.4 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 12.8 | drt_violations best 6143 last 6143 rows 8 | before-window best 167111, window best 6143 | PROGRESS: drt_violations improved 96.3 % in window |  |
| intel2 | dpkit-kv3_io_ft-2251165 | kv3_io_ft | 5_1_grt | 0.5 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 12.7 | drt_violations best 95 last 95 rows 14 | before-window best 211273, window best 95 | PROGRESS: drt_violations improved 100.0 % in window |  |
