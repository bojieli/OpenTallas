# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 21:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 3, 'NO-PROGRESS': 2, 'GRT-LABEL': 4, 'YOUNG': 99, 'NO-DATA': 39, 'KEEP': 2, 'PROGRESS': 27}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | 5_1_grt | 7.2 | grt rounds 7 overflow 10:2178 -> 15:1693 -> 20:894 -> 25:15 -> 30:4 -> 35:8 | UNSIGNABLE: GRT overflow flat: overflow 4 at iteration 30 -> 8 at iteration 35: flat for 5 i | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 37.1 | drt_violations best 13 last 13 rows 53 | before-window best 13, window best 13 | NO-PROGRESS: drt_violations best 13 vs 13 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 5_1_grt | 12.0 | grt rounds 7 overflow 10:3224 -> 15:2262 -> 20:2305 -> 25:2156 -> 30:1933 -> 35:1923 | UNSIGNABLE: GRT overflow flat: overflow 1933 at iteration 30 -> 1923 at iteration 35: flat f | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 5_1_grt | 16.3 | grt rounds 8 overflow 15:1367 -> 20:1472 -> 25:1063 -> 30:774 -> 35:659 -> 40:652 | UNSIGNABLE: GRT overflow flat: overflow 659 at iteration 35 -> 652 at iteration 40: flat for | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 32.4 | drt_violations best 1 last 1 rows 47 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 9.8 | grt rounds 5 overflow 5:128855 -> 10:3237 -> 15:2296 -> 20:2337 -> 25:2143 | GRT-LABEL: DESIGN-FAIL: overflow 3237 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | 5_1_grt | 13.4 | grt rounds 10 overflow 25:1102 -> 30:804 -> 35:688 -> 40:714 -> 45:641 -> 50:596 | GRT-LABEL: DESIGN-FAIL: overflow 2188 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 5_1_grt | 16.2 | grt rounds 9 overflow 20:1584 -> 25:1212 -> 30:970 -> 35:768 -> 40:889 -> 45:735 | GRT-LABEL: DESIGN-FAIL: overflow 2244 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 5_1_grt | 16.4 | grt rounds 9 overflow 20:1597 -> 25:1148 -> 30:913 -> 35:770 -> 40:787 -> 45:655 | GRT-LABEL: DESIGN-FAIL: overflow 2290 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-3140082 | dsdv_slice_c1x_C__t5 | 3_5_place_dp | 2.2 | last meaningful line 0.1 h ago (37/37 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-3152819 | dsdv_slice_c1x_C__t5 | 3_5_place_dp | 2.2 | last meaningful line 0.1 h ago (37/37 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-3157172 | dsdv_slice_c1x_C__t5 | 3_5_place_dp | 2.2 | last meaningful line 0.1 h ago (37/37 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-3854423 | dsdv_slice_c1x_C__t8 | 1_1_yosys_canonicalize | 0.5 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p6-4011229 | kv3_hg_v1p6 | 3_3_place_gp | 0.4 | overflow best 0.534 last 0.544 rows 5 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_io_cor-363026 | kv3_io_cor | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t3-4051614 | ot_s81sl_leaf__t3 | 3_3_place_gp | 0.4 | overflow best 0.6148 last 0.6148 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slw_st_a_v2__clf4365a62-199111 | slw_st_a_v2 | postcts_gate_TT | 1.7 | last meaningful line 0.0 h ago (878/878 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | lecaf-hdm-full | lecaf-hdm-full | - | 1.9 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-16147f31a235 | lecq9-16147f31a235 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-32da6c3b9dec | lecq9-32da6c3b9dec | - | 1.1 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-c351666358dc | lecq9-c351666358dc | - | 1.0 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-d7634e345491 | lecq9-d7634e345491 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 2.5 | last meaningful line 0.5 h ago (33/34 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | otc-648169-1843 | 648169 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (9/9 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-native59-478901 | native59 | 5_2_route | 9.1 | drt_violations best 35216 last 35216 rows 2 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc12 | dpkit-sle_ctl__cla4f6f12f-1558951 | sle_ctl | postcts_gate_TT | 0.4 | last meaningful line 0.3 h ago (71/71 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc12 | otc-2164334-7793 | 2164334 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-kv3_hg_v1p4__ret4_es_4-3437284 | kv3_hg_v1p4__ret4_es_4 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (97/97 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-4027604 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.278 last 0.278 rows 40 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | 5_2_route | 12.1 | drt_violations best 24235 last 24235 rows 7 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-2967544 | sle_hc0 | tt_setup_repair_grt | 3.4 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1991043 | sle_stm_v2 | pregrt_ff_hold | 1.6 | repair_TNS best 6606.94 last 6606.94 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-1997619 | sle_stm_v2 | pregrt_ff_hold | 1.6 | repair_TNS best 1838.48 last 1838.48 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slice_station__t21-778921 | slice_station__t21 | 3_3_place_gp | 0.1 | overflow best 0.2964 last 0.2964 rows 29 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slice_station__t22-809530 | slice_station__t22 | 3_3_place_gp | 0.1 | overflow best 0.406 last 0.406 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-slice_station__t25-820854 | slice_station__t25 | 3_3_place_gp | 0.1 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t28-682956 | slice_station__t28 | 3_3_place_gp | 0.1 | overflow best 0.3437 last 0.3533 rows 29 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slice_station__t42__cl4bd1432c-804341 | slice_station__t42 | 3_3_place_gp | 0.1 | overflow best 0.2632 last 0.2632 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | prd-eco_20261125_200405_3323313-i1t-2801726 | eco_20261125_200405_3323313-i1t | 5_2_route | 1.2 | last meaningful line 0.1 h ago (277/278 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 15.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 15.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 15.7 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-4039941 | col_h9_r0_p1__t1 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3768357 | col_h9_r0_p3__t1 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (97/97 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pvcb7f0079-4137527 | col_h9_r0_p3__t1 | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t4-1017259 | dsdv_slice_c1x_C__t4 | sdc_lint | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3327555 | dsdv_slice_kv512_C__t1 | 3_3_place_gp | 0.8 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_kv_leaf__t5-684015 | ot_s81sl_kv_leaf__t5 | 3_5_place_dp | 0.4 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | generate_abstract | 15.5 | last meaningful line 0.2 h ago (27/27 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t29__cl2e5c855a-1563369 | slice_station__t29 | 2_4_floorplan_pdn | 0.0 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | postcts_gate_TT | 10.7 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-677883 | tt_ctlm | 3_5_place_dp | 0.4 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | lecaf-colls-ctl | lecaf-colls-ctl | - | 1.4 |  | NO-DATA: no log found |  |
| epyc7 | lecq9-09fe297654d7 | lecq9-09fe297654d7 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | lecq9-0ce42cbdc4b0 | lecq9-0ce42cbdc4b0 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc7 | lecq9-1b3200859cc9 | lecq9-1b3200859cc9 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc7 | lecq9-59017ec270a7 | lecq9-59017ec270a7 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc7 | otc-1572699-31485 | 1572699 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc7 | otc-1634017-16068 | 1634017 | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-2739402-5290 | 2739402 | - | 3.8 |  | NO-DATA: no log found |  |
| epyc8 | ap-render-dpkit-sle_sc_v1__cl7479a5ec-1199968-3889986 | ap-render-dpkit-sle_sc_v1 | 5_2_route | 0.0 | drt_violations best 5244 last 5244 rows 7 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-2886348 | col_h10_r0_p1__t1 | 2_3_floorplan_tapcell | 0.3 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvd8c0565f-3312328 | col_h10_r0_p4__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (388/388 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-2986818 | col_h10_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.3704 last 0.3971 rows 29 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-382371 | col_h9_r0_p1__t1 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pvef55eb84-2279972 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.4 | overflow best 0.4505 last 0.4505 rows 4 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b-3911862 | col_h9_r0_p3__t1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (207/207 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-1476523 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.6 | overflow best 0.5204 last 0.5204 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvee6f8140-3305848 | col_h9_r0_p5__t1 | 2_2_floorplan_macro | 0.2 | last meaningful line -0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv47efee8f-2913710 | col_h9_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.4725 last 0.4775 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4ef1b59c-2692826 | col_h9_r1__t1 | 3_4_place_resized | 0.3 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv70f04488-2406899 | col_h9_r1__t1 | 3_5_place_dp | 0.4 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8aaf8508-2950405 | col_h9_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.4725 last 0.4779 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pva2370bfd-2650767 | col_h9_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.1998 last 0.1998 rows 37 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-2653004 | col_h9_r2__t1 | 3_4_place_resized | 0.3 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-3656096 | col_h9_r2__t1 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (1534/1534 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv37074264-2886847 | col_h9_r2__t1 | 3_3_place_gp | 0.3 | overflow best 0.3998 last 0.4077 rows 29 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t10-3190993 | dsdv_slice_c1x_C__t10 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c3x_C__t1-3731856 | dsdv_slice_c3x_C__t1 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-hd_lep0N-2958360 | hd_lep0N | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (8644/8644 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t3-1774923 | ot_s81sl_kv_leaf__t3 | 3_3_place_gp | 0.5 | overflow best 0.6484 last 0.6484 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t2-2056355 | ot_s81sl_leaf__t2 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 10.9 | drt_violations best 5244 last 5244 rows 7 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc8 | lecaf-hc0-6e8 | lecaf-hc0-6e8 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc8 | lecaf-hc3-afda1e-twins | lecaf-hc3-afda1e-twins | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | lecq9-125656921876 | lecq9 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc8 | lecq9-b821dc8b6fe0 | lecq9-b821dc8b6fe0 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | lecq9-c8c740c6d798 | lecq9-c8c740c6d798 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-1530472-10583 | 1530472 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-1589750-5019 | 1589750 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-2693994-26282 | 2693994 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc8 | otc-3438426-20778 | 3438426 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-3660326-25272 | 3660326 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-3731784-29079 | 3731784 | - | 4.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-4174262-4961 | 4174262 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc8 | otc-877014-30307 | 877014 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc8 | otc-941401-14145 | 941401 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_104318_3955073-i3-312208 | eco_20261125_104318_3955073-i3 | 5_1_grt | 0.8 | last meaningful line 0.3 h ago (290/353 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | prd-eco_20261126_033711_2888564-i1t-928710 | eco_20261126_033711_2888564-i1t | 5_2_route | 1.6 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 9.9 | drt_violations best 37095 last 37095 rows 2 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | 5_2_route | 9.4 | last meaningful line 0.2 h ago (282/283 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3198/3198 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 13.5 | drt_violations best 545016 last 545016 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 9.9 | last meaningful line 0.7 h ago (282/283 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 10.5 | drt_violations best 380531 last 380531 rows 1 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-3826216 | col_h9_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.4725 last 0.4774 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 10.0 | drt_violations best 35414 last 35414 rows 2 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | 4_1_cts | 0.0 | repair_Violations best 1232 last 1232 rows 12 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 5_1_grt | 10.4 | last meaningful line 0.2 h ago (284/285 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 12.0 | last meaningful line 1.8 h ago (277/1284 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t26-501697 | slice_station__t26 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_020316_3686099-i1t-150182 | eco_20261126_020316_3686099-i1t | 5_2_route | 3.2 | drt_violations best 80636 last 80636 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 10.8 | drt_violations best 40191 last 40191 rows 2 | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel1 | dpkit-coll_ft__cl78c7b300-773126 | coll_ft | 3_4_place_resized | 0.3 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-3824626 | coll_ftc | 5_2_route | 10.9 | drt_violations best 8733 last 8733 rows 2 | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p4-646455 | kv3_hg_v1p4 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.1 h ago (526/526 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_phy-3158276 | kv3_phy | abstract_exact | 2.3 | last meaningful line 0.1 h ago (4/4 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v2-172554 | kv3_pv_v2 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.3155 last 0.3155 rows 32 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v5ne-135837 | kv3_pv_v5ne | 3_1_place_gp_skip_io | 0.5 | overflow best 0.7628 last 0.7628 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v6-285159 | kv3_pv_v6 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.8529 last 0.8529 rows 6 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-kv3_sys_SD_v1-3706384 | kv3_sys_SD_v1 | 5_2_route | 2.1 | drt_violations best 1782 last 1782 rows 2 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-3994132 | slw_hc0 | 3_3_place_gp | 0.6 | overflow best 0.4464 last 0.4464 rows 37 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | 5_2_route | 11.4 | drt_violations best 75122 last 75122 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3756903 | slw_hc3 | 3_4_place_resized | 0.7 | repair_Remaining best 297714 last 297714 rows 58 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | lecq9-1e4ed353bf9a | lecq9-1e4ed353bf9a | - | 1.1 |  | NO-DATA: no log found |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 0.9 |  | NO-DATA: no log found |  |
| intel1 | lecq9-963f0492a10e | lecq9-963f0492a10e | - | 1.0 |  | NO-DATA: no log found |  |
| intel1 | lecq9-abc37a821c70 | lecq9-abc37a821c70 | - | 1.0 |  | NO-DATA: no log found |  |
| intel1 | lecq9-c8be6220489b | lecq9-c8be6220489b | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | otc-178621-11182 | 178621 | - | 5.4 |  | NO-DATA: no log found |  |
| intel1 | otc-2860019-3888 | 2860019 | flow | 2.5 | repair_Violations best 1246 last 1246 rows 19 | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | otc-3479258-28963 | 3479258 | - | 5.8 |  | NO-DATA: no log found |  |
| intel1 | otc-957737-21247 | 957737 | signoff | 5.1 | last meaningful line 5.0 h ago (3/3 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i2t-515416 | eco_20261125_050013_1448739-i2t | 5_2_route | 5.3 | drt_violations best 10221 last 10221 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel1 | so_765087_ff_68209 | so_765087_ff_68209 | signoff | 0.3 |  | NO-DATA: empty log |  |
| intel1 | so_765087_tt_68209 | so_765087_tt_68209 | signoff | 0.3 |  | NO-DATA: empty log |  |
| intel1 | so_966964_ff_70293 | so_966964_ff_70293 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (35/35 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | so_966964_tt_70293 | so_966964_tt_70293 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (35/35 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-626876 | coll_ftm | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (119/119 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6__ret4_wn_6-2758773 | kv3_hg_v1p6__ret4_wn_6 | 3_5_place_dp | 0.9 | last meaningful line 0.1 h ago (46/46 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_Wi-2160767 | kv3_hub_Wi | 3_4_place_resized | 3.6 | last meaningful line 0.3 h ago (640/640 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-1558093 | kv3_io_ft | 5_2_route | 1.2 | drt_violations best 5443 last 5443 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8e7d31598-3690925 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.7 | overflow best 0.7862 last 0.7862 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-3488734 | sle_hc0 | 3_4_place_resized | 0.7 | repair_Remaining best 155663 last 155663 rows 217 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-717052 | slice_station__t12 | abstract_exact | 1.5 | last meaningful line 0.3 h ago (4/4 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3633925 | slw_hc0 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (58/58 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 10.7 | drt_violations best 51122 last 51122 rows 2 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clb8d86cd5__pvb2cd22a7-3370025 | col_h9_r2__t1 | 2_4_floorplan_pdn | 0.1 |  | KEEP: col_h9_r2__t1__clb8d86cd5__pvb2cd22a7	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-203526 | col_h10_r2__t1 | 2_4_floorplan_pdn | 0.1 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 34.4 | drt_violations best 200 last 204 rows 58 | before-window best 212, window best 200 | PROGRESS: drt_violations improved 5.7 % in window |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_1_grt | 12.0 | repair_TNS best 0 last 0 rows 14 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | 5_2_route | 12.0 | drt_violations best 2149 last 2149 rows 10 | before-window best 255884, window best 2149 | PROGRESS: drt_violations improved 99.2 % in window |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_1_grt | 3.4 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 19.7 | drt_violations best 3792 last 3792 rows 16 | before-window best 78321, window best 3792 | PROGRESS: drt_violations improved 95.2 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 19.7 | drt_violations best 16003 last 16003 rows 12 | before-window best 89585, window best 16003 | PROGRESS: drt_violations improved 82.1 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 20.1 | drt_violations best 721 last 721 rows 24 | before-window best 12540, window best 721 | PROGRESS: drt_violations improved 94.3 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 12.9 | drt_violations best 11088 last 11088 rows 17 | before-window best 31895, window best 11088 | PROGRESS: drt_violations improved 65.2 % in window |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvadbd1880-2013817 | col_h9_r1__t1 | 3_5_place_dp | 0.5 | repair_Violations best 0 last 0 rows 24 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pvaa9a1324-2631579 | col_h9_r2__t1 | 3_5_place_dp | 0.3 | repair_Violations best 0 last 0 rows 14 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 11.9 | drt_violations best 2255 last 2255 rows 5 | before-window best 174806, window best 2255 | PROGRESS: drt_violations improved 98.7 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 5_2_route | 13.5 | drt_violations best 6 last 8 rows 48 | before-window best 176025, window best 6 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 22.5 | drt_violations best 394 last 398 rows 32 | before-window best 135197, window best 394 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 19.7 | drt_violations best 21608 last 21608 rows 4 | before-window best 470122, window best 21608 | PROGRESS: drt_violations improved 95.4 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 10.7 | drt_violations best 39863 last 39863 rows 2 | before-window best 171015, window best 39863 | PROGRESS: drt_violations improved 76.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 11.5 | drt_violations best 28437 last 28437 rows 3 | before-window best 176573, window best 28437 | PROGRESS: drt_violations improved 83.9 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 13.5 | drt_violations best 3597 last 3597 rows 11 | before-window best 178781, window best 3597 | PROGRESS: drt_violations improved 98.0 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-138946 | col_h9_r2__t1 | 5_2_route | 9.9 | drt_violations best 489 last 489 rows 15 | before-window best 151829, window best 489 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 24.4 | drt_violations best 390 last 408 rows 58 | before-window best 411, window best 390 | PROGRESS: drt_violations improved 5.1 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 12.0 | drt_violations best 28562 last 28562 rows 3 | before-window best 178567, window best 28562 | PROGRESS: drt_violations improved 84.0 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | 5_2_route | 13.3 | drt_violations best 375 last 375 rows 32 | before-window best 158828, window best 375 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 5_2_route | 12.8 | drt_violations best 379 last 379 rows 17 | before-window best 159056, window best 379 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 12.0 | drt_violations best 539 last 1068 rows 18 | before-window best 157970, window best 539 | PROGRESS: drt_violations improved 99.7 % in window |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 16.4 | repair_TNS best 1707.1 last 1707.1 rows 8 | before-window best 2063.49, window best 1707.1 | PROGRESS: repair_TNS improved 17.3 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | 5_2_route | 16.4 | drt_violations best 6118 last 6118 rows 10 | before-window best 178263, window best 6118 | PROGRESS: drt_violations improved 96.6 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | 5_2_route | 16.3 | drt_violations best 369 last 370 rows 31 | before-window best 159843, window best 369 | PROGRESS: drt_violations improved 99.8 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_2_route | 16.3 | drt_violations best 376 last 378 rows 27 | before-window best 159806, window best 376 | PROGRESS: drt_violations improved 99.8 % in window |  |
