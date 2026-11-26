# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-26 00:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'GRT-STUCK': 1, 'NO-PROGRESS': 3, 'GRT-LABEL': 2, 'YOUNG': 81, 'NO-DATA': 18, 'EXCLUDED': 3, 'KEEP': 1, 'PROGRESS': 27}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | 5_1_grt | 10.5 | grt rounds 9 overflow 20:894 -> 25:15 -> 30:4 -> 35:8 -> 40:1 -> 45:2 | UNSIGNABLE: GRT overflow flat: overflow 1 at iteration 40 -> 2 at iteration 45: flat for 5 i | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 5_1_grt | 15.2 | grt rounds 9 overflow 20:2305 -> 25:2156 -> 30:1933 -> 35:1923 -> 40:2127 -> 45:2007 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (35:1923 -> 40:2127 -> 45:2007; best 2007 | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | pregrt_ff_hold | 3.3 | repair_TNS best 70.316 last 70.316 rows 1 | before-window best 70.316, window best 70.316 | NO-PROGRESS: repair_TNS best 70.316 vs 70.316 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 19.6 | repair_Viol best 968 last 968 rows 51 | before-window best 968, window best 968 | NO-PROGRESS: repair_Viol best 968 vs 968 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 35.6 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 13.1 | grt rounds 7 overflow 10:3237 -> 15:2296 -> 20:2337 -> 25:2143 -> 30:1999 -> 35:1942 | GRT-LABEL: DESIGN-FAIL: overflow 3237 at round 10 > 1000 |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-479268 | sle_su_l1 | 5_1_grt | 2.4 | grt rounds 2 overflow 5:6669 -> 10:2241 | GRT-LABEL: DESIGN-FAIL: overflow 2241 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-2708094 | dsdv_slice_c1x_C__t5 | 4_1_cts | 2.4 | last meaningful line 0.0 h ago (7406/7406 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_C__t1-3949489 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-3108241 | hd_lep0N | 3_3_place_gp | 0.6 | overflow best 0.3058 last 0.3058 rows 34 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-sle_sc_v2-3764865 | sle_sc_v2 | 3_3_place_gp | 0.3 | overflow best 0.2133 last 0.2133 rows 24 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | lecaf-hdm-full | lecaf-hdm-full | - | 5.2 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-p1-pointer-cohorts-r2 | lecaf-hdm-p1-pointer-cohorts-r2 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-p1-retained-relays | lecaf-hdm-p1-retained-relays | - | 2.8 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-p6-pointer-cohorts-r2 | lecaf-hdm-p6-pointer-cohorts-r2 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-p6-retained-relays | lecaf-hdm-p6-retained-relays | - | 2.6 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-rxsb-sq-remainder-layout-1126 | lecaf-rxsb-sq-remainder-layout | bb.ys | 0.0 | last meaningful line 0.0 h ago (983/983 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | lecq9-d7634e345491-standalone-twins | lecq9-d7634e345491-standalone-twins | - | 0.8 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-hd-ctl-whole-guarded-1125 | lecq9-hd-ctl-whole-guarded | - | 0.5 |  | NO-DATA: no log found |  |
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 5.8 | last meaningful line 3.8 h ago (33/34 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc11 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3889710 | col_h10_r0_p1__t1 | 2_3_floorplan_tapcell | 0.2 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h10_r1__t1__cl95b37463__pv74ebbc00-3491104 | col_h10_r1__t1 | 3_4_place_resized | 0.3 | repair_Remaining best 94279 last 94279 rows 20 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-3979905 | col_h10_r1__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h10_r2__t1__cl99efd374__pv9ae398c2-3972201 | col_h10_r2__t1 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-3423622 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.4 | overflow best 0.4399 last 0.4399 rows 3 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-3185311 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.4 | overflow best 0.3993 last 0.3998 rows 27 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-3434540 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (96/96 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv110cabb8-3439633 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.3462 last 0.3462 rows 33 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv8d734760-3286907 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-3503421 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.5661 last 0.5661 rows 28 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-2911101 | col_h9_r0_p4__t1 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (97/97 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pv35382794-3176956 | col_h9_r0_p5__t1 | 3_3_place_gp | 0.4 | overflow best 0.4809 last 0.4809 rows 4 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pv8995e794-3135078 | col_h9_r0_p5__t1 | 3_3_place_gp | 0.4 | overflow best 0.4794 last 0.4801 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_2_route | 15.3 | last meaningful line 0.2 h ago (293/294 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-2909147 | col_h9_r0_p5__t1 | 3_3_place_gp | 0.5 | overflow best 0.1997 last 0.1997 rows 38 | YOUNG: stage 0.2 h < 1 h |  |
| epyc11 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-3715134 | col_h9_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.5365 last 0.5365 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc25aad1b-47797 | col_h9_r1__t1 | lec | 0.1 | LEC last write 0.0 h ago | YOUNG: evidence 0.1 h < 6 h |  |
| epyc11 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-4025872 | col_h9_r2__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (207/207 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3729483 | col_h9_r2__t1 | 3_3_place_gp | 0.3 | overflow best 0.399 last 0.4303 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-3734604 | col_h9_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.368 last 0.3788 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-73389 | col_h9_r2__t1 | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r2__t1__clce45cab5__pvfb42a1ad-3981276 | col_h9_r2__t1 | 3_1_place_gp_skip_io | 0.2 | last meaningful line -0.0 h ago (5/5 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_c1x_C__t3-3965387 | dsdv_slice_c1x_C__t3 | 1_1_yosys_canonicalize | 1.3 | last meaningful line 0.3 h ago (134/134 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_c1x_C__t7-2765401 | dsdv_slice_c1x_C__t7 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_iq_C__t1-3149121 | dsdv_slice_iq_C__t1 | 3_5_place_dp | 2.6 | last meaningful line 0.8 h ago (36/36 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1450190 | dsdv_slice_lepe_nh_mus_C__t1 | 3_1_place_gp_skip_io | 2.0 | last meaningful line 0.0 h ago (60/60 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_lepw_mus_C__t1-3987621 | dsdv_slice_lepw_mus_C__t1 | 1_1_yosys_canonicalize | 1.3 | last meaningful line 0.3 h ago (133/133 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | dpkit-iqf__t1-3689347 | iqf__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.231 last 0.231 rows 45 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-ot_s81sl_leaf__t15-2770109 | ot_s81sl_leaf__t15 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-ot_s81sl_leaf__t30-51553 | ot_s81sl_leaf__t30 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (1054/1054 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | prd-eco_20261126_075602_478638-i1t-3937565 | eco_20261126_075602_478638-i1t | 5_1_grt | 0.5 | last meaningful line 0.4 h ago (293/599 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-2967544 | sle_hc0 | 5_2_route | 6.7 | drt_violations best 9863 last 9863 rows 3 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1991043 | sle_stm_v2 | 5_2_route | 4.9 | drt_violations best 94499 last 94499 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-1997619 | sle_stm_v2 | 5_2_route | 4.9 | last meaningful line 0.1 h ago (262/263 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_2_route | 6.6 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | so_1630876_ff_13243 | so_1630876_ff_13243 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (34/34 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_1630876_tt_13243 | so_1630876_tt_13243 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (34/34 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_1696336_ff_52854 | so_1696336_ff_52854 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (59/59 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | so_1696336_tt_52854 | so_1696336_tt_52854 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (59/59 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 2.6 | last meaningful line 1.8 h ago (700/700 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | otc-2739402-5290 | 2739402 | - | 7.1 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 1.3 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | so_1114742_ff_3349 | so_1114742_ff_3349 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | so_1114742_tt_3349 | so_1114742_tt_3349 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t10-3190993 | dsdv_slice_c1x_C__t10 | 3_5_place_dp | 3.4 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c3x_C__t1-3731856 | dsdv_slice_c3x_C__t1 | 3_5_place_dp | 3.3 | last meaningful line 0.5 h ago (37/37 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-hd_lep0N_w-1738505 | hd_lep0N_w | 4_2_tapbal_grt | 0.5 | last meaningful line 0.3 h ago (46/55 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | lecaf-hc3-afda1e-standalone-twins | lecaf-hc3-afda1e-standalone-twins | - | 0.6 |  | NO-DATA: no log found |  |
| epyc8 | lecaf-hc3-afda1e-twins | lecaf-hc3-afda1e-twins | - | 3.3 |  | NO-DATA: no log found |  |
| epyc8 | otc-3731784-29079 | 3731784 | - | 7.8 |  | NO-DATA: no log found |  |
| epyc8 | prd-fin-671626 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (67/67 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | pregrt_ff_hold | 3.1 | repair_TNS best 110094 last 110094 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | 5_2_route | 12.6 | drt_violations best 7935 last 7935 rows 3 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | pregrt_ff_hold | 3.4 | repair_TNS best 13231.2 last 13231.2 rows 1 | YOUNG: evidence 1.9 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 13.2 | drt_violations best 486708 last 486708 rows 1 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | pregrt_ff_hold | 3.1 | repair_TNS best 122813 last 122813 rows 1 | YOUNG: evidence 1.7 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-2823500 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.7 | last meaningful line 2.0 h ago (61/91 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvadbd1880-3530008 | col_h9_r1__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3589 last 3589 rows 1115 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-3901907 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.5 | last meaningful line 1.8 h ago (61/89 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvfef7c177-3709744 | col_h9_r2__t1 | 4_1_cts | 0.1 | repair_Violations best 56 last 56 rows 19 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | pregrt_ff_hold | 2.6 | repair_TNS best 11997.6 last 11997.6 rows 1 | YOUNG: evidence 1.9 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-4156698 | col_h9_r2__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 52456.7 last 52456.7 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfd79e8b6-2469832 | col_h9_r2__t1 | pregrt_ff_hold | 1.2 | repair_TNS best 26509.4 last 26509.4 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 5_1_grt | 13.6 | last meaningful line 3.3 h ago (284/1293 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mus_C__t1-1648329 | dsdv_slice_lepw_mus_C__t1 | 3_1_place_gp_skip_io | 3.0 | overflow best 0.7498 last 0.7498 rows 28 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-2575809 | ot_s81sl_leaf__t53 | 5_1_grt | 2.8 | last meaningful line 0.5 h ago (269/1279 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t23-1100978 | slice_station__t23 | 6_1_fill | 2.2 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t26-3959180 | slice_station__t26 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t45-1580954 | slice_station__t45 | 5_2_route | 3.0 | drt_violations best 69970 last 69970 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 5_1_grt | 2.9 | repair_TNS best 130753 last 130753 rows 4 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | prd-eco_20261126_072708_1527702-i1-3266022 | eco_20261126_072708_1527702-i1 | 5_2_route | 1.0 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-eco_retry_1795673019361579887-i1t-300819 | eco_retry_1795673019361579887-i1t | 5_2_route | 2.4 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 4.2 |  | NO-DATA: no log found |  |
| intel1 | lecq9-963f0492a10e | lecq9-963f0492a10e | - | 4.3 |  | NO-DATA: no log found |  |
| intel1 | lecq9-abc37a821c70 | lecq9-abc37a821c70 | - | 4.3 |  | NO-DATA: no log found |  |
| intel1 | lecq9-c8be6220489b | lecq9-c8be6220489b | - | 3.4 |  | NO-DATA: no log found |  |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 5.7 | last meaningful line 2.0 h ago (33/34 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i2-559996 | eco_20261125_050013_1448739-i2 | 5_2_route | 2.1 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | prd-eco_20261125_233248_2287605-i1-397034 | eco_20261125_233248_2287605-i1 | 5_2_route | 0.9 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | 5_2_route | 3.2 | drt_violations best 473 last 473 rows 10 | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t5-331755 | dsdv_slice_c1x_C__t5 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_mesh-3056327 | hd_mesh | pregrt_ff_hold | 2.7 | repair_TNS best 576579 last 576579 rows 1 | YOUNG: evidence 1.6 h < 2.5 h |  |
| intel2 | dpkit-kv3_io_ft-2251165 | kv3_io_ft | abstract_exact | 1.7 | last meaningful line 0.2 h ago (4/4 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-3404510 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 2986 last 2986 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | otc-371135-2464 | 371135 | - | 0.1 |  | NO-DATA: no log found |  |
| intel2 | otc-4164407-11341 | 4164407 | gold_b.ys | 2.3 | last meaningful line 2.0 h ago (96320/96320 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 18.9 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 18.9 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 18.9 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-454895 | col_h9_r1__t1 | 4_2_tapbal_grt | 0.7 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-serdes__t4-4068722 | serdes__t4 | 4_1_cts | 0.1 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 37.7 | drt_violations best 200 last 204 rows 58 | before-window best 212, window best 200 | PROGRESS: drt_violations improved 5.7 % in window |  |
| epyc11 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-3219817 | col_h9_r1__t1 | 3_5_place_dp | 0.4 | repair_Violations best 0 last 0 rows 24 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 23.0 | drt_violations best 3665 last 21095 rows 18 | before-window best 4967, window best 3665 | PROGRESS: drt_violations improved 26.2 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 23.0 | drt_violations best 13518 last 13518 rows 14 | before-window best 20628, window best 13518 | PROGRESS: drt_violations improved 34.5 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 23.4 | drt_violations best 438 last 438 rows 32 | before-window best 920, window best 438 | PROGRESS: drt_violations improved 52.4 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 16.2 | drt_violations best 11088 last 19300 rows 19 | before-window best 13227, window best 11088 | PROGRESS: drt_violations improved 16.2 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 14.1 | drt_violations best 1883 last 1883 rows 16 | before-window best 224764, window best 1883 | PROGRESS: drt_violations improved 99.2 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 40.4 | drt_violations best 11 last 11 rows 55 | before-window best 13, window best 11 | PROGRESS: drt_violations improved 15.4 % in window |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | 4_2_tapbal_grt | 2.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 13.1 | drt_violations best 7 last 11 rows 53 | before-window best 174634, window best 7 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 15.2 | drt_violations best 13 last 14 rows 51 | before-window best 174806, window best 13 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 16.8 | drt_violations best 147781 last 147781 rows 2 | before-window best 545016, window best 147781 | PROGRESS: drt_violations improved 72.9 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 22.9 | drt_violations best 2160 last 2160 rows 12 | before-window best 118691, window best 2160 | PROGRESS: drt_violations improved 98.2 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 13.7 | drt_violations best 103874 last 103874 rows 2 | before-window best 380531, window best 103874 | PROGRESS: drt_violations improved 72.7 % in window |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2325128 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.9 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2382304 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.8 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-2530599 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.8 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 13.9 | drt_violations best 1551 last 1551 rows 13 | before-window best 171015, window best 1551 | PROGRESS: drt_violations improved 99.1 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 14.7 | drt_violations best 5161 last 5161 rows 12 | before-window best 176573, window best 5161 | PROGRESS: drt_violations improved 97.1 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 16.7 | drt_violations best 1022 last 1775 rows 19 | before-window best 42293, window best 1022 | PROGRESS: drt_violations improved 97.6 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 27.6 | drt_violations best 390 last 408 rows 58 | before-window best 392, window best 390 | PROGRESS: drt_violations: falling inside the active iteration (408 -> 395) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 15.2 | drt_violations best 2325 last 2325 rows 13 | before-window best 178567, window best 2325 | PROGRESS: drt_violations improved 98.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 13.2 | drt_violations best 405 last 405 rows 23 | before-window best 162182, window best 405 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 15.3 | drt_violations best 389 last 389 rows 42 | before-window best 6664, window best 389 | PROGRESS: drt_violations improved 94.2 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 14.0 | drt_violations best 4107 last 4107 rows 12 | before-window best 167111, window best 4107 | PROGRESS: drt_violations improved 97.5 % in window |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 14.0 | drt_violations best 7 last 7 rows 28 | before-window best 211273, window best 7 | PROGRESS: drt_violations improved 100.0 % in window |  |
