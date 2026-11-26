# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 23:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'GRT-STUCK': 1, 'NO-PROGRESS': 2, 'GRT-LABEL': 1, 'YOUNG': 79, 'NO-DATA': 23, 'EXCLUDED': 3, 'PROGRESS': 28}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | 5_1_grt | 9.7 | grt rounds 9 overflow 20:894 -> 25:15 -> 30:4 -> 35:8 -> 40:1 -> 45:2 | UNSIGNABLE: GRT overflow flat: overflow 1 at iteration 40 -> 2 at iteration 45: flat for 5 i | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-hd_lep0N-2958360 | hd_lep0N | 4_2_tapbal_grt | 3.6 | last meaningful line 0.0 h ago (231/231 lines) | UNSIGNABLE: 4_1_cts.json latest setup WNS -320.71 ps (< -300, gate TT >= -42); job age 3.6 h | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 5_1_grt | 14.5 | grt rounds 8 overflow 15:2262 -> 20:2305 -> 25:2156 -> 30:1933 -> 35:1923 -> 40:2127 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (30:1933 -> 35:1923 -> 40:2127; best 1923 | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 18.9 | repair_Viol best 968 last 968 rows 20 | before-window best 968, window best 968 | NO-PROGRESS: repair_Viol best 968 vs 968 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 34.9 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 12.3 | grt rounds 7 overflow 10:3237 -> 15:2296 -> 20:2337 -> 25:2143 -> 30:1999 -> 35:1942 | GRT-LABEL: DESIGN-FAIL: overflow 3237 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-2708094 | dsdv_slice_c1x_C__t5 | 4_1_cts | 1.6 | last meaningful line 0.2 h ago (44/44 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-hd_serdes-2411968 | hd_serdes | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (280/280 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-2237515 | hd_spn | 3_3_place_gp | 0.1 | overflow best 0.1967 last 0.1971 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_io_cor-1236068 | kv3_io_cor | 3_5_place_dp | 0.5 | last meaningful line 0.1 h ago (113/113 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_sys_c-2360826 | kv3_sys_c | 2_1_floorplan | 0.1 | repair_Viol best 684 last 684 rows 754 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-slice_station__t51-1561504 | slice_station__t51 | 3_5_place_dp | 0.4 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | lecaf-colls-73016a-ctl-e10 | lecaf-colls-73016a-ctl-e10 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-full | lecaf-hdm-full | - | 4.4 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-p1-pointer-cohorts-r2 | lecaf-hdm-p1-pointer-cohorts-r2 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-p1-retained-relays | lecaf-hdm-p1-retained-relays | - | 2.1 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-p6-pointer-cohorts-r2 | lecaf-hdm-p6-pointer-cohorts-r2 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-p6-retained-relays | lecaf-hdm-p6-retained-relays | - | 1.9 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-rxsb-sq-stage-map-1125 | lecaf-rxsb-sq-stage-map | bb.ys | 0.5 | last meaningful line 0.5 h ago (983/983 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | lecq9-d7634e345491 | lecq9-d7634e345491 | - | 2.6 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-d7634e345491-q-bad-relays | lecq9-d7634e345491-q-bad-relays | - | 0.6 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-d7634e345491-standalone-twins | lecq9-d7634e345491-standalone-twins | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-hd-ctl-seq-guarded-discovery-r3-1125 | lecq9-hd-ctl-seq-guarded-discovery-r3 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc10 | otc-2344799-31865 | 2344799 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 5.0 | last meaningful line 3.0 h ago (33/34 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | otc-2468758-16348 | 2468758 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | ppr-kv-iocor-r1-1125-2477923 | ppr-kv-iocor-r1-1125 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-2455280 | col_h10_r0_p1__t1 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3588922 | col_h9_r0_p2__t1 | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-3696138 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.7 | overflow best 0.1988 last 0.1988 rows 37 | YOUNG: stage 0.2 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv4cfde03b-3327088 | col_h9_r0_p3__t1 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvcd8810ba-3099665 | col_h9_r0_p3__t1 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-182354 | col_h9_r0_p4__t1 | 3_3_place_gp | 0.5 | overflow best 0.3405 last 0.3405 rows 32 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_2_route | 14.5 | last meaningful line 0.5 h ago (285/286 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p6__t1__pv6398a5b7-4179111 | col_h9_r0_p6__t1 | 3_5_place_dp | 0.5 | repair_Violations best 107716 last 107716 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bab1162-1921964 | col_h9_r1__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3589 last 3589 rows 735 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h9_r2__t1__clce45cab5__pvb7e88dd2-2066684 | col_h9_r2__t1 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_c1x_C__t3-3965387 | dsdv_slice_c1x_C__t3 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_iq_C__t1-3149121 | dsdv_slice_iq_C__t1 | 3_5_place_dp | 1.8 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1450190 | dsdv_slice_lepe_nh_mus_C__t1 | 1_1_yosys_canonicalize | 1.2 | last meaningful line 0.2 h ago (133/133 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_lepw_mus_C__t1-3987621 | dsdv_slice_lepw_mus_C__t1 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | dpkit-ot_s81sl_leaf__t24__cl81374cd8-2115967 | ot_s81sl_leaf__t24 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (286/286 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | so_1789175_ff_71179 | so_1789175_ff_71179 | signoff | 0.8 |  | NO-DATA: empty log |  |
| epyc12 | so_1789175_tt_71179 | so_1789175_tt_71179 | signoff | 0.8 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-2967544 | sle_hc0 | 5_2_route | 5.9 | drt_violations best 113905 last 113905 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1991043 | sle_stm_v2 | 5_2_route | 4.1 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-1997619 | sle_stm_v2 | postcts_gate_FF | 4.1 | last meaningful line 0.0 h ago (1673/1673 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_2_route | 5.9 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261125_200405_3323313-i1-2828164 | eco_20261125_200405_3323313-i1 | 5_2_route | 1.3 | drt_violations best 14 last 14 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc2 | prd-eco_20261125_211504_2977850-i1-3586116 | eco_20261125_211504_2977850-i1 | 5_2_route | 0.9 | last meaningful line 0.0 h ago (265/266 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p1__t1__cl911743eb-3891022 | col_h10_r0_p1__t1 | 3_3_place_gp | 0.2 | overflow best 0.4331 last 0.4331 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-gunit__t1-1078622 | gunit__t1 | 3_5_place_dp | 1.2 | last meaningful line 0.5 h ago (39/39 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 1.8 | last meaningful line 1.0 h ago (700/700 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | otc-2739402-5290 | 2739402 | - | 6.3 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (293/343 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t10-3190993 | dsdv_slice_c1x_C__t10 | 3_4_place_resized | 2.7 | last meaningful line 0.0 h ago (415/415 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t6-4113643 | dsdv_slice_c1x_C__t6 | 3_3_place_gp | 2.5 | overflow best 0.1986 last 0.1986 rows 82 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_c3x_C__t1-3731856 | dsdv_slice_c3x_C__t1 | 3_4_place_resized | 2.6 | repair_Remaining best 330717 last 330717 rows 66 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | eco-abs-178481 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.1 h ago (29/29 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | lecaf-hc3-afda1e-leaf7-native | lecaf-hc3-afda1e-leaf7-native | - | 0.4 |  | NO-DATA: no log found |  |
| epyc8 | lecaf-hc3-afda1e-twins | lecaf-hc3-afda1e-twins | - | 2.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-2693994-26282 | 2693994 | - | 2.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-3731784-29079 | 3731784 | - | 7.0 |  | NO-DATA: no log found |  |
| epyc8 | ppr-kvallfix-r7-pc_es4-986663 | ppr-kvallfix-r7-pc_es4 | tcl | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261126_033711_2888564-i1-671626 | eco_20261126_033711_2888564-i1 | 5_2_route | 1.2 | last meaningful line 0.0 h ago (261/262 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-bk_sel__t2-1028644 | bk_sel__t2 | 3_3_place_gp | 0.7 | overflow best 0.2037 last 0.2207 rows 8 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | 4_2_tapbal_grt | 1.4 | last meaningful line 0.3 h ago (62/66 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | pregrt_ff_hold | 2.4 | repair_TNS best 110094 last 110094 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | 5_2_route | 11.9 | drt_violations best 89851 last 89851 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | pregrt_ff_hold | 2.7 | repair_TNS best 13231.2 last 13231.2 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 12.4 | drt_violations best 486708 last 486708 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 122813 last 122813 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-2823500 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.0 | last meaningful line 1.3 h ago (61/84 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2325128 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.1 | last meaningful line 1.5 h ago (61/86 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-3901907 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.8 | last meaningful line 1.0 h ago (61/82 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2382304 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.1 | last meaningful line 1.5 h ago (61/85 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-2530599 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.1 | last meaningful line 1.3 h ago (61/85 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | pregrt_ff_hold | 1.8 | repair_TNS best 124234 last 124234 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-4156698 | col_h9_r2__t1 | pregrt_ff_hold | 0.9 | repair_TNS best 52456.7 last 52456.7 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 12889.8 last 12889.8 rows 1 | YOUNG: evidence 1.8 h < 2.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 5_1_grt | 12.9 | last meaningful line 2.5 h ago (284/1292 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mus_C__t1-1648329 | dsdv_slice_lepw_mus_C__t1 | 1_1_yosys_canonicalize | 2.3 | last meaningful line 1.0 h ago (133/133 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-2575809 | ot_s81sl_leaf__t53 | pregrt_ff_hold | 2.0 | repair_Violations best 29017 last 29017 rows 2 | YOUNG: evidence 1.0 h < 2.5 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-479268 | sle_su_l1 | 5_1_grt | 1.6 | last meaningful line 0.2 h ago (246/1253 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t23-1100978 | slice_station__t23 | 5_2_route | 1.5 | last meaningful line 0.1 h ago (232/233 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t45-1580954 | slice_station__t45 | 5_2_route | 2.3 | last meaningful line 0.2 h ago (249/250 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_retry_1795673019361579887-i1t-300819 | eco_retry_1795673019361579887-i1t | 5_2_route | 1.6 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-1625008 | kv3_pc_v1 | 3_5_place_dp | 2.5 | last meaningful line 0.8 h ago (32/32 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | lecq9-1e4ed353bf9a | lecq9-1e4ed353bf9a | - | 3.6 |  | NO-DATA: no log found |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 3.4 |  | NO-DATA: no log found |  |
| intel1 | lecq9-963f0492a10e | lecq9-963f0492a10e | - | 3.5 |  | NO-DATA: no log found |  |
| intel1 | lecq9-abc37a821c70 | lecq9-abc37a821c70 | - | 3.5 |  | NO-DATA: no log found |  |
| intel1 | lecq9-c8be6220489b | lecq9-c8be6220489b | - | 2.6 |  | NO-DATA: no log found |  |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 5.0 | last meaningful line 1.2 h ago (33/34 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | otc-3878162-6060 | 3878162 | signoff | 2.1 | last meaningful line 2.0 h ago (3/3 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i2-559996 | eco_20261125_050013_1448739-i2 | 5_2_route | 1.4 | last meaningful line 0.1 h ago (265/266 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | prd-eco_20261125_233248_2287605-i1-397034 | eco_20261125_233248_2287605-i1 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-626876 | coll_ftm | abstract_exact | 2.7 | last meaningful line 0.2 h ago (4/4 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | 5_2_route | 2.5 | drt_violations best 51310 last 51310 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel2 | dpkit-hd_mesh-3056327 | hd_mesh | pregrt_ff_hold | 1.9 | repair_TNS best 576579 last 576579 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-3272504 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (214/215 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-2251165 | kv3_io_ft | 5_2_route | 1.0 | last meaningful line 0.0 h ago (229/230 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v2-1217990 | kv3_pv_v2 | 3_5_place_dp | 1.1 | last meaningful line 0.1 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v6n-1232246 | kv3_pv_v6n | 3_4_place_resized | 1.1 | last meaningful line 0.1 h ago (293/293 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | otc-3836076-29553 | 3836076 | asbuilt.yosys | 0.1 | last meaningful line 0.0 h ago (136405/136405 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | otc-4164407-11341 | 4164407 | gold_b.ys | 1.6 | last meaningful line 1.3 h ago (96320/96320 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | prd-eco_20261125_231441_1318253-i1-1184578 | eco_20261125_231441_1318253-i1 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (240/241 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 18.2 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 18.2 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 18.2 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 36.9 | drt_violations best 200 last 204 rows 58 | before-window best 212, window best 200 | PROGRESS: drt_violations improved 5.7 % in window |  |
| epyc10 | otc-3652144-28954 | 3652144 | flow | 1.2 | repair_Violations best 0 last 0 rows 38 | PROGRESS: repair_Violations reached 0 |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | 5_2_route | 14.5 | drt_violations best 414 last 416 rows 39 | before-window best 255884, window best 414 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 22.2 | drt_violations best 3665 last 21095 rows 18 | before-window best 5720, window best 3665 | PROGRESS: drt_violations improved 35.9 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 22.2 | drt_violations best 13518 last 13518 rows 14 | before-window best 21571, window best 13518 | PROGRESS: drt_violations improved 37.3 % in window |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | 5_2_route | 13.2 | drt_violations best 0 last 0 rows 8 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 22.6 | drt_violations best 446 last 446 rows 31 | before-window best 1501, window best 446 | PROGRESS: drt_violations improved 70.3 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 15.4 | drt_violations best 11088 last 44179 rows 18 | before-window best 15556, window best 11088 | PROGRESS: drt_violations improved 28.7 % in window |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv7466df46-4060382 | col_h9_r1__t1 | 3_5_place_dp | 0.3 | repair_Violations best 0 last 0 rows 24 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 13.4 | drt_violations best 2075 last 2075 rows 14 | before-window best 224764, window best 2075 | PROGRESS: drt_violations improved 99.1 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 39.6 | drt_violations best 13 last 13 rows 53 | before-window best 13, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 12.4 | drt_violations best 7 last 8 rows 44 | before-window best 174634, window best 7 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 14.4 | drt_violations best 13 last 14 rows 51 | before-window best 174806, window best 13 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 16.0 | drt_violations best 545016 last 545016 rows 1 | before-window best 545016, window best 545016 | PROGRESS: drt_violations: active iteration at 203365 < best completed total 545016 (in-ite |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 22.2 | drt_violations best 5589 last 5589 rows 10 | before-window best 118691, window best 5589 | PROGRESS: drt_violations improved 95.3 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 13.0 | drt_violations best 103874 last 103874 rows 2 | before-window best 380531, window best 103874 | PROGRESS: drt_violations improved 72.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 13.2 | drt_violations best 3230 last 3230 rows 11 | before-window best 171015, window best 3230 | PROGRESS: drt_violations improved 98.1 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 14.0 | drt_violations best 5523 last 5523 rows 11 | before-window best 176573, window best 5523 | PROGRESS: drt_violations improved 96.9 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 16.0 | drt_violations best 1022 last 4107 rows 18 | before-window best 178781, window best 1022 | PROGRESS: drt_violations improved 99.4 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 26.9 | drt_violations best 390 last 408 rows 58 | before-window best 392, window best 390 | PROGRESS: drt_violations: falling inside the active iteration (408 -> 395) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 14.5 | drt_violations best 4541 last 4541 rows 11 | before-window best 178567, window best 4541 | PROGRESS: drt_violations improved 97.5 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 12.5 | drt_violations best 430 last 430 rows 17 | before-window best 162182, window best 430 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 14.5 | drt_violations best 391 last 391 rows 37 | before-window best 35075, window best 391 | PROGRESS: drt_violations improved 98.9 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfd79e8b6-2469832 | col_h9_r2__t1 | 4_1_cts | 0.4 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | prd-eco_20261126_072708_1527702-i1-3266022 | eco_20261126_072708_1527702-i1 | 5_1_grt | 0.3 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 13.3 | drt_violations best 5692 last 5692 rows 10 | before-window best 167111, window best 5692 | PROGRESS: drt_violations improved 96.6 % in window |  |
| intel2 | dpkit-slice_station__t12-3404510 | slice_station__t12 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 13.2 | drt_violations best 33 last 33 rows 17 | before-window best 211273, window best 33 | PROGRESS: drt_violations improved 100.0 % in window |  |
