# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-26 00:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'GRT-STUCK': 1, 'NO-PROGRESS': 3, 'GRT-LABEL': 2, 'YOUNG': 80, 'NO-DATA': 19, 'KEEP': 2, 'EXCLUDED': 3, 'PROGRESS': 23}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | 5_1_grt | 10.0 | grt rounds 9 overflow 20:894 -> 25:15 -> 30:4 -> 35:8 -> 40:1 -> 45:2 | UNSIGNABLE: GRT overflow flat: overflow 1 at iteration 40 -> 2 at iteration 45: flat for 5 i | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 5_1_grt | 14.7 | grt rounds 8 overflow 15:2262 -> 20:2305 -> 25:2156 -> 30:1933 -> 35:1923 -> 40:2127 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (30:1933 -> 35:1923 -> 40:2127; best 1923 | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 12889.8 last 12889.8 rows 1 | before-window best 12889.8, window best 12889.8 | NO-PROGRESS: repair_TNS best 12889.8 vs 12889.8 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 19.1 | repair_Viol best 968 last 968 rows 30 | before-window best 968, window best 968 | NO-PROGRESS: repair_Viol best 968 vs 968 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 35.1 | drt_violations best 1 last 1 rows 49 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 12.6 | grt rounds 7 overflow 10:3237 -> 15:2296 -> 20:2337 -> 25:2143 -> 30:1999 -> 35:1942 | GRT-LABEL: DESIGN-FAIL: overflow 3237 at round 10 > 1000 |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-479268 | sle_su_l1 | 5_1_grt | 1.9 | grt rounds 2 overflow 5:6669 -> 10:2241 | GRT-LABEL: DESIGN-FAIL: overflow 2241 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-2708094 | dsdv_slice_c1x_C__t5 | 4_1_cts | 1.9 | last meaningful line 0.0 h ago (7273/7273 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-3108241 | hd_lep0N | 1_synth | 0.1 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_serdes-2411968 | hd_serdes | 3_2_place_iop | 0.3 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_sys_c-2360826 | kv3_sys_c | 3_3_place_gp | 0.4 | overflow best 0.5936 last 0.5954 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl431c660f-2663764 | ot_s81sl_leaf__t25 | 3_3_place_gp | 0.2 | overflow best 0.5519 last 0.5519 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | lecaf-colls-73016a-ctl-e10 | lecaf-colls-73016a-ctl-e10 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-full | lecaf-hdm-full | - | 4.7 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-p1-pointer-cohorts-r2 | lecaf-hdm-p1-pointer-cohorts-r2 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-p1-retained-relays | lecaf-hdm-p1-retained-relays | - | 2.3 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-p6-pointer-cohorts-r2 | lecaf-hdm-p6-pointer-cohorts-r2 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-p6-retained-relays | lecaf-hdm-p6-retained-relays | - | 2.1 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-rxsb-sq-stage-map-1125 | lecaf-rxsb-sq-stage-map | bb.ys | 0.8 | last meaningful line 0.8 h ago (983/983 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | lecq9-d7634e345491 | lecq9-d7634e345491 | - | 2.9 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-d7634e345491-standalone-twins | lecq9-d7634e345491-standalone-twins | - | 0.3 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-hd-ctl-whole-guarded-1125 | lecq9-hd-ctl-whole-guarded | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | otc-2344799-31865 | 2344799 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 5.3 | last meaningful line 3.3 h ago (33/34 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc10 | otc-2468758-16348 | 2468758 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-2911101 | col_h9_r0_p4__t1 | 1_synth | 0.0 | last meaningful line 0.0 h ago (9/9 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_2_route | 14.8 | last meaningful line 0.2 h ago (289/290 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-2909147 | col_h9_r0_p5__t1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (274/274 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p6__t1__pvde240d6d-2252288 | col_h9_r0_p6__t1 | 3_3_place_gp | 0.2 | overflow best 0.4646 last 0.4672 rows 6 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bab1162-1921964 | col_h9_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.2591 last 0.2591 rows 34 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4108910d-2279844 | col_h9_r1__t1 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49636389-2601744 | col_h9_r1__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvcf44b14c-2769223 | col_h9_r2__t1 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (1542/1542 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r2__t1__clce45cab5__pv40e9fb5a-2599544 | col_h9_r2__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-2444725 | col_h9_r2__t1 | 3_2_place_iop | 0.2 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r2__t1__clce45cab5__pvb7e88dd2-2066684 | col_h9_r2__t1 | 3_4_place_resized | 0.3 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_c1x_C__t3-3965387 | dsdv_slice_c1x_C__t3 | sdc_lint | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_c1x_C__t7-2765401 | dsdv_slice_c1x_C__t7 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_iq_C__t1-3149121 | dsdv_slice_iq_C__t1 | 3_5_place_dp | 2.1 | last meaningful line 0.3 h ago (36/36 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1450190 | dsdv_slice_lepe_nh_mus_C__t1 | 1_1_yosys_canonicalize | 1.5 | last meaningful line 0.3 h ago (133/133 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | dpkit-dsdv_slice_lepw_mus_C__t1-3987621 | dsdv_slice_lepw_mus_C__t1 | sdc_lint | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | dpkit-ot_s81sl_leaf__t15-2770109 | ot_s81sl_leaf__t15 | 2_1_floorplan | 0.1 | repair_Viol best 277 last 277 rows 206 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-ot_s81sl_leaf__t24__cl81374cd8-2115967 | ot_s81sl_leaf__t24 | 3_2_place_iop | 0.3 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | otc-3974694-31064 | 3974694 | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (11/11 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | prd-eco_20261126_075602_478638-i1t-3937565 | eco_20261126_075602_478638-i1t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-2967544 | sle_hc0 | 5_2_route | 6.2 | drt_violations best 15326 last 15326 rows 2 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1991043 | sle_stm_v2 | 5_2_route | 4.4 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-1997619 | sle_stm_v2 | postcts_gate_FF | 4.4 | last meaningful line 0.1 h ago (87919/87919 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_2_route | 6.1 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261125_200405_3323313-i1-2828164 | eco_20261125_200405_3323313-i1 | 5_2_route | 1.6 | drt_violations best 14 last 14 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261125_211504_2977850-i1-3586116 | eco_20261125_211504_2977850-i1 | 5_2_route | 1.1 | drt_violations best 8734 last 8734 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc7 | dpkit-gunit__t1-1078622 | gunit__t1 | 3_5_place_dp | 1.5 | last meaningful line 0.0 h ago (55/55 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | 6_report | 13.5 | last meaningful line 0.1 h ago (72/72 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-3611843 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 2.1 | last meaningful line 1.3 h ago (700/700 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | otc-2739402-5290 | 2739402 | - | 6.6 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261126_070642_282464-i1t-2943130 | eco_20261126_070642_282464-i1t | 5_2_route | 0.8 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t10-3190993 | dsdv_slice_c1x_C__t10 | 3_5_place_dp | 2.9 | last meaningful line 0.2 h ago (38/38 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t6-4113643 | dsdv_slice_c1x_C__t6 | 3_5_place_dp | 2.7 | last meaningful line 0.1 h ago (37/37 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c3x_C__t1-3731856 | dsdv_slice_c3x_C__t1 | 3_5_place_dp | 2.8 | last meaningful line 0.2 h ago (37/37 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-hd_lep0N_w-1738505 | hd_lep0N_w | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | lecaf-hc3-afda1e-standalone-twins | lecaf-hc3-afda1e-standalone-twins | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | lecaf-hc3-afda1e-twins | lecaf-hc3-afda1e-twins | - | 2.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-2693994-26282 | 2693994 | - | 3.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-3731784-29079 | 3731784 | - | 7.3 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261126_033711_2888564-i1-671626 | eco_20261126_033711_2888564-i1 | 5_2_route | 1.4 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | so_1204073_ff_99440 | so_1204073_ff_99440 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (33/33 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | so_1204073_tt_99440 | so_1204073_tt_99440 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (33/33 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-bk_sel__t2-1028644 | bk_sel__t2 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-1418379 | col_h10_r0_p1__t1 | 4_2_tapbal_grt | 1.7 | last meaningful line 0.5 h ago (62/69 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | pregrt_ff_hold | 2.6 | repair_TNS best 110094 last 110094 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | 5_2_route | 12.1 | drt_violations best 13292 last 13292 rows 2 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | pregrt_ff_hold | 2.9 | repair_TNS best 13231.2 last 13231.2 rows 1 | YOUNG: evidence 1.4 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 12.7 | drt_violations best 486708 last 486708 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.6 | repair_TNS best 122813 last 122813 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-2823500 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.2 | last meaningful line 1.5 h ago (61/86 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2325128 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.4 | last meaningful line 1.8 h ago (61/88 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-3901907 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.0 | last meaningful line 1.3 h ago (61/84 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2382304 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.3 | last meaningful line 1.8 h ago (61/88 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-2530599 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.3 | last meaningful line 1.6 h ago (61/88 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-3673013 | col_h9_r2__t1 | pregrt_ff_hold | 2.1 | repair_TNS best 124234 last 124234 rows 1 | YOUNG: evidence 1.4 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-4156698 | col_h9_r2__t1 | pregrt_ff_hold | 1.1 | repair_TNS best 52456.7 last 52456.7 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 5_1_grt | 13.1 | last meaningful line 2.8 h ago (284/1292 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mus_C__t1-1648329 | dsdv_slice_lepw_mus_C__t1 | 1_2_yosys | 2.5 | last meaningful line 0.0 h ago (215/215 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-2575809 | ot_s81sl_leaf__t53 | 5_1_grt | 2.3 | last meaningful line 0.0 h ago (156/156 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t23-1100978 | slice_station__t23 | 5_2_route | 1.7 | drt_violations best 4138 last 4138 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-slice_station__t45-1580954 | slice_station__t45 | 5_2_route | 2.5 | last meaningful line 0.3 h ago (251/252 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 5_1_grt | 2.4 | last meaningful line 0.0 h ago (164/164 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_072708_1527702-i1-3266022 | eco_20261126_072708_1527702-i1 | 5_1_grt | 0.5 | last meaningful line 0.1 h ago (1306/2139 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | prd-eco_retry_1795673019361579887-i1t-300819 | eco_retry_1795673019361579887-i1t | 5_2_route | 1.9 | last meaningful line 0.3 h ago (272/273 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-1625008 | kv3_pc_v1 | 3_5_place_dp | 2.7 | last meaningful line 1.0 h ago (32/32 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | lecq9-1e4ed353bf9a | lecq9-1e4ed353bf9a | - | 3.8 |  | NO-DATA: no log found |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 3.7 |  | NO-DATA: no log found |  |
| intel1 | lecq9-963f0492a10e | lecq9-963f0492a10e | - | 3.8 |  | NO-DATA: no log found |  |
| intel1 | lecq9-abc37a821c70 | lecq9-abc37a821c70 | - | 3.8 |  | NO-DATA: no log found |  |
| intel1 | lecq9-c8be6220489b | lecq9-c8be6220489b | - | 2.9 |  | NO-DATA: no log found |  |
| intel1 | otc-2860019-3888 | 2860019 | grt_it0 | 5.2 | last meaningful line 1.5 h ago (33/34 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | otc-3878162-6060 | 3878162 | signoff | 2.4 | last meaningful line 2.3 h ago (3/3 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i2-559996 | eco_20261125_050013_1448739-i2 | 5_2_route | 1.6 | last meaningful line 0.3 h ago (267/268 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | 5_2_route | 2.7 | drt_violations best 13721 last 13721 rows 2 | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-hd_mesh-3056327 | hd_mesh | pregrt_ff_hold | 2.2 | repair_TNS best 576579 last 576579 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| intel2 | dpkit-kv3_io_ft-2251165 | kv3_io_ft | 5_2_route | 1.2 | drt_violations best 5443 last 5443 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-kv3_pv_v6n-1232246 | kv3_pv_v6n | 3_5_place_dp | 1.4 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-3404510 | slice_station__t12 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (66/66 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | otc-3836076-29553 | 3836076 | asbuilt.yosys | 0.4 | last meaningful line 0.1 h ago (242584/242584 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | otc-4164407-11341 | 4164407 | gold_b.ys | 1.8 | last meaningful line 1.5 h ago (96320/96320 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | prd-eco_20261125_231441_1318253-i1-1184578 | eco_20261125_231441_1318253-i1 | 5_2_route | 0.7 | drt_violations best 148 last 148 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc11 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-2914742 | col_h10_r2__t1 | 1_synth | 0.0 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 18.4 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 18.4 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 18.4 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-454895 | col_h9_r1__t1 | 4_1_cts | 0.2 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 37.2 | drt_violations best 200 last 204 rows 58 | before-window best 212, window best 200 | PROGRESS: drt_violations improved 5.7 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 22.5 | drt_violations best 3665 last 21095 rows 18 | before-window best 5720, window best 3665 | PROGRESS: drt_violations improved 35.9 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 22.5 | drt_violations best 13518 last 13518 rows 14 | before-window best 21571, window best 13518 | PROGRESS: drt_violations improved 37.3 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 22.9 | drt_violations best 446 last 446 rows 31 | before-window best 1145, window best 446 | PROGRESS: drt_violations improved 61.0 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 15.7 | drt_violations best 11088 last 19300 rows 19 | before-window best 15556, window best 11088 | PROGRESS: drt_violations improved 28.7 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 13.6 | drt_violations best 1886 last 1886 rows 15 | before-window best 224764, window best 1886 | PROGRESS: drt_violations improved 99.2 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 39.9 | drt_violations best 11 last 11 rows 55 | before-window best 13, window best 11 | PROGRESS: drt_violations improved 15.4 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 12.6 | drt_violations best 7 last 8 rows 49 | before-window best 174634, window best 7 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 14.7 | drt_violations best 13 last 14 rows 51 | before-window best 174806, window best 13 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 16.3 | drt_violations best 545016 last 545016 rows 1 | before-window best 545016, window best 545016 | PROGRESS: drt_violations: active iteration at 203365 < best completed total 545016 (in-ite |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 22.4 | drt_violations best 5589 last 5589 rows 10 | before-window best 118691, window best 5589 | PROGRESS: drt_violations improved 95.3 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 13.2 | drt_violations best 103874 last 103874 rows 2 | before-window best 380531, window best 103874 | PROGRESS: drt_violations improved 72.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 13.4 | drt_violations best 3017 last 3017 rows 12 | before-window best 171015, window best 3017 | PROGRESS: drt_violations improved 98.2 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 14.2 | drt_violations best 5523 last 5523 rows 11 | before-window best 176573, window best 5523 | PROGRESS: drt_violations improved 96.9 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 16.2 | drt_violations best 1022 last 4107 rows 18 | before-window best 178781, window best 1022 | PROGRESS: drt_violations improved 99.4 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 27.1 | drt_violations best 390 last 408 rows 58 | before-window best 392, window best 390 | PROGRESS: drt_violations: falling inside the active iteration (408 -> 395) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 14.7 | drt_violations best 3932 last 3932 rows 12 | before-window best 178567, window best 3932 | PROGRESS: drt_violations improved 97.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 12.7 | drt_violations best 421 last 421 rows 19 | before-window best 162182, window best 421 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 14.8 | drt_violations best 391 last 391 rows 37 | before-window best 35075, window best 391 | PROGRESS: drt_violations improved 98.9 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfd79e8b6-2469832 | col_h9_r2__t1 | 4_2_tapbal_grt | 0.7 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 13.5 | drt_violations best 5692 last 5692 rows 10 | before-window best 167111, window best 5692 | PROGRESS: drt_violations improved 96.6 % in window |  |
| intel1 | prd-eco_20261125_233248_2287605-i1-397034 | eco_20261125_233248_2287605-i1 | 5_1_grt | 0.4 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 13.5 | drt_violations best 28 last 28 rows 20 | before-window best 211273, window best 28 | PROGRESS: drt_violations improved 100.0 % in window |  |
