# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 21:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'UNSIGNABLE': 2, 'GRT-LABEL': 4, 'YOUNG': 98, 'NO-DATA': 33, 'EXCLUDED': 3, 'PROGRESS': 28}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 37.6 | drt_violations best 13 last 13 rows 53 | before-window best 13, window best 13 | NO-PROGRESS: drt_violations best 13 vs 13 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 5_1_grt | 12.5 | grt rounds 7 overflow 10:3224 -> 15:2262 -> 20:2305 -> 25:2156 -> 30:1933 -> 35:1923 | UNSIGNABLE: GRT overflow flat: overflow 1933 at iteration 30 -> 1923 at iteration 35: flat f | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 5_1_grt | 16.8 | grt rounds 8 overflow 15:1367 -> 20:1472 -> 25:1063 -> 30:774 -> 35:659 -> 40:652 | UNSIGNABLE: GRT overflow flat: overflow 659 at iteration 35 -> 652 at iteration 40: flat for | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 32.9 | drt_violations best 1 last 1 rows 47 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | 5_1_grt | 7.7 | grt rounds 8 overflow 15:1693 -> 20:894 -> 25:15 -> 30:4 -> 35:8 -> 40:1 | GRT-LABEL: DESIGN-FAIL: overflow 2178 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 10.3 | grt rounds 5 overflow 5:128855 -> 10:3237 -> 15:2296 -> 20:2337 -> 25:2143 | GRT-LABEL: DESIGN-FAIL: overflow 3237 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 5_1_grt | 16.7 | grt rounds 9 overflow 20:1584 -> 25:1212 -> 30:970 -> 35:768 -> 40:889 -> 45:735 | GRT-LABEL: DESIGN-FAIL: overflow 2244 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 5_1_grt | 16.9 | grt rounds 9 overflow 20:1597 -> 25:1148 -> 30:913 -> 35:770 -> 40:787 -> 45:655 | GRT-LABEL: DESIGN-FAIL: overflow 2290 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-3140082 | dsdv_slice_c1x_C__t5 | 3_5_place_dp | 2.7 | last meaningful line 0.5 h ago (37/37 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-3152819 | dsdv_slice_c1x_C__t5 | 3_5_place_dp | 2.7 | last meaningful line 0.0 h ago (65/65 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-3157172 | dsdv_slice_c1x_C__t5 | 3_5_place_dp | 2.7 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-3854423 | dsdv_slice_c1x_C__t8 | 1_2_yosys | 1.0 | last meaningful line 0.0 h ago (199/199 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_serdes-1642801 | hd_serdes | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_a_v2__clf4365a62-199111 | slw_st_a_v2 | 5_2_route | 2.2 | last meaningful line 0.0 h ago (263/264 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | lecaf-hdm-full | lecaf-hdm-full | - | 2.4 |  | NO-DATA: no log found |  |
| epyc10 | lecaf-hdm-p1-retained-relays | lecaf-hdm-p1-retained-relays | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-16147f31a235 | lecq9-16147f31a235 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-32da6c3b9dec | lecq9-32da6c3b9dec | - | 1.6 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-d7634e345491 | lecq9-d7634e345491 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 3.0 | last meaningful line 1.0 h ago (33/34 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | s81-bmng12-1605080 | s81-bmng12 | dsyn_ng12 | 0.0 | last meaningful line 0.0 h ago (9488/9488 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h10_r2__t1__cl8b686b3e-1948886 | col_h10_r2__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-2240909 | col_h9_r0_p3__t1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (202/202 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | tt_setup_measure_grt | 12.5 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11c696bc-2130622 | col_h9_r1__t1 | 2_1_floorplan | 0.0 | repair_Viol best 3589 last 3589 rows 339 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | otc-1154289-24691 | 1154289 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | otc-1157491-1702 | 1157491 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | otc-1584409-16633 | 1584409 | gen_lint_yosys | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | otc-1868011-19214 | 1868011 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-native59-478901 | native59 | 5_2_route | 9.6 | drt_violations best 25197 last 25197 rows 3 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc12 | dpkit-sle_ctl__cla4f6f12f-1558951 | sle_ctl | postcts_gate_FF | 0.9 | last meaningful line 0.3 h ago (71/71 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc12 | otc-2968974-5119 | 2968974 | asbuilt.yosys | 0.2 | last meaningful line 0.0 h ago (136412/136412 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-4027604 | kv3_pc_v1 | 3_4_place_resized | 1.1 | last meaningful line 0.0 h ago (375/375 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-2967544 | sle_hc0 | postcts_gate_TT | 3.9 | last meaningful line 0.1 h ago (370/370 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1991043 | sle_stm_v2 | 5_1_grt | 2.1 | repair_Remaining best 98458 last 98458 rows 305 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-1997619 | sle_stm_v2 | 5_1_grt | 2.1 | repair_Remaining best 283399 last 283399 rows 112 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_1_grt | 3.9 | last meaningful line 0.3 h ago (1286/2089 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261125_200405_3323313-i1t-2801726 | eco_20261125_200405_3323313-i1t | 5_2_route | 1.7 | drt_violations best 52874 last 52874 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261125_211504_2977850-i1t-1003964 | eco_20261125_211504_2977850-i1t | 5_2_route | 0.5 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-slice-station--t30--cl1653104c-grt-2903430 | slice-station--t30--cl1653104c-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-coll_ft__cla4a25d77-2719659 | coll_ft | 3_3_place_gp | 0.1 | overflow best 0.333 last 0.3337 rows 15 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t4-1017259 | dsdv_slice_c1x_C__t4 | 1_1_yosys_canonicalize | 0.8 | last meaningful line 0.2 h ago (127/127 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3327555 | dsdv_slice_kv512_C__t1 | 3_4_place_resized | 1.3 | repair_Remaining best 291494 last 291494 rows 98 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N-1892837 | hd_lep0N | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | generate_abstract | 16.0 | last meaningful line 0.4 h ago (29/29 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t51-2606916 | slice_station__t51 | 3_3_place_gp | 0.1 | overflow best 0.3091 last 0.3091 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | 5_2_route | 11.2 | last meaningful line 0.0 h ago (272/272 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | lecq9-09fe297654d7 | lecq9-09fe297654d7 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc7 | lecq9-0ce42cbdc4b0 | lecq9-0ce42cbdc4b0 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc7 | lecq9-1b3200859cc9 | lecq9-1b3200859cc9 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc7 | lecq9-59017ec270a7 | lecq9-59017ec270a7 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc7 | otc-1572699-31485 | 1572699 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc7 | otc-2739402-5290 | 2739402 | - | 4.3 |  | NO-DATA: no log found |  |
| epyc7 | otc-2870572-10922 | 2870572 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-2886348 | col_h10_r0_p1__t1 | 3_3_place_gp | 0.8 | last meaningful line 0.0 h ago (300/300 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvd8c0565f-3312328 | col_h10_r0_p4__t1 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (97/97 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-4054935 | col_h10_r1__t1 | 3_4_place_resized | 0.5 | last meaningful line 0.0 h ago (174/174 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-4187149 | col_h10_r2__t1 | 3_5_place_dp | 0.4 | repair_Violations best 96 last 96 rows 32 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b-3911862 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.5 | overflow best 0.4864 last 0.4864 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-751615 | col_h9_r0_p4__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.7193 last 0.7193 rows 20 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvee6f8140-3305848 | col_h9_r0_p5__t1 | 3_4_place_resized | 0.7 | repair_Remaining best 93961 last 93961 rows 57 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pvbdbd69f2-320365 | col_h9_r0_p6__t1 | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__cl87f3ff59-380205 | col_h9_r2__t1 | 3_4_place_resized | 0.3 | repair_Remaining best 40085 last 40085 rows 41 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv4937edd4-332941 | col_h9_r2__t1 | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-686944 | col_h9_r2__t1 | 3_3_place_gp | 0.3 | overflow best 0.3972 last 0.4187 rows 27 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pvf9c773d5-576715 | col_h9_r2__t1 | 3_3_place_gp | 0.3 | overflow best 0.3802 last 0.3802 rows 31 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t10-3190993 | dsdv_slice_c1x_C__t10 | sdc_lint | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t6-4113643 | dsdv_slice_c1x_C__t6 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c3x_C__t1-3731856 | dsdv_slice_c3x_C__t1 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-gunit__t1-342903 | gunit__t1 | 3_3_place_gp | 0.4 | overflow best 0.3368 last 0.3431 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-hd_lep0N-2958360 | hd_lep0N | 4_2_tapbal_grt | 1.6 | last meaningful line 0.0 h ago (46/47 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t14-377632 | ot_s81sl_leaf__t14 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.8583 last 0.8917 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t2-2056355 | ot_s81sl_leaf__t2 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (119/119 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t26-128578 | ot_s81sl_leaf__t26 | 3_3_place_gp | 0.4 | last meaningful line 0.1 h ago (116/116 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t37-116748 | ot_s81sl_leaf__t37 | 3_3_place_gp | 0.4 | overflow best 0.7061 last 0.7061 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 11.4 | drt_violations best 4425 last 4425 rows 9 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc8 | lecaf-hc0-6e8 | lecaf-hc0-6e8 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc8 | lecaf-hc3-afda1e-twins | lecaf-hc3-afda1e-twins | - | 0.5 |  | NO-DATA: no log found |  |
| epyc8 | lecq9-125656921876 | lecq9 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc8 | lecq9-b821dc8b6fe0 | lecq9-b821dc8b6fe0 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc8 | lecq9-c8c740c6d798 | lecq9-c8c740c6d798 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-1530472-10583 | 1530472 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-1589750-5019 | 1589750 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-2693994-26282 | 2693994 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-3731784-29079 | 3731784 | - | 5.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-4174262-4961 | 4174262 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-877014-30307 | 877014 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-941401-14145 | 941401 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_104318_3955073-i3-312208 | eco_20261125_104318_3955073-i3 | 5_2_route | 1.3 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261126_033711_2888564-i1t-928710 | eco_20261126_033711_2888564-i1t | 5_2_route | 2.1 | drt_violations best 7315 last 7315 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3724/3724 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 10.4 | drt_violations best 22716 last 22716 rows 3 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | 5_2_route | 9.9 | last meaningful line 0.1 h ago (288/289 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | 4_2_tapbal_grt | 0.7 | last meaningful line 0.1 h ago (62/65 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 14.0 | drt_violations best 545016 last 545016 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 10.4 | last meaningful line 0.2 h ago (286/287 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3074/3074 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1568817 | col_h9_r0_p6__t1 | 3_3_place_gp | 0.3 | overflow best 0.4151 last 0.4402 rows 29 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 11.0 | drt_violations best 380531 last 380531 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2325128 | col_h9_r1__t1 | 4_1_cts | 0.1 | repair_Violations best 39 last 39 rows 3 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-2530599 | col_h9_r1__t1 | 4_1_cts | 0.1 | repair_Violations best 669 last 669 rows 14 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 10.5 | drt_violations best 6530 last 6530 rows 4 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 5_1_grt | 10.9 | last meaningful line 0.5 h ago (284/1288 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 12.5 | last meaningful line 2.3 h ago (277/1285 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mus_C__t1-1648329 | dsdv_slice_lepw_mus_C__t1 | sdc_lint | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-2575809 | ot_s81sl_leaf__t53 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t45-1580954 | slice_station__t45 | pregrt_ff_hold | 0.3 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc9 | dpkit-slice_station__t51-2134708 | slice_station__t51 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (3552/3552 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_020316_3686099-i1t-150182 | eco_20261126_020316_3686099-i1t | 5_2_route | 3.7 | drt_violations best 80636 last 80636 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 11.3 | drt_violations best 40191 last 40191 rows 2 | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-3824626 | coll_ftc | 6_report | 11.4 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p4-646455 | kv3_hg_v1p4 | 3_3_place_gp | 0.8 | overflow best 0.4883 last 0.4883 rows 18 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-1625008 | kv3_pc_v1 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.0 h ago (58/58 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_phy-3158276 | kv3_phy | abstract_exact | 2.8 | last meaningful line 0.5 h ago (4/4 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v2-172554 | kv3_pv_v2 | 3_3_place_gp | 1.0 | overflow best 0.0998 last 0.0998 rows 46 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v6-285159 | kv3_pv_v6 | 3_3_place_gp | 0.9 | overflow best 0.2033 last 0.2033 rows 37 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-3994132 | slw_hc0 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | 5_2_route | 11.9 | drt_violations best 75122 last 75122 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | lecq9-1e4ed353bf9a | lecq9-1e4ed353bf9a | - | 1.6 |  | NO-DATA: no log found |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 1.4 |  | NO-DATA: no log found |  |
| intel1 | lecq9-963f0492a10e | lecq9-963f0492a10e | - | 1.5 |  | NO-DATA: no log found |  |
| intel1 | lecq9-abc37a821c70 | lecq9-abc37a821c70 | - | 1.5 |  | NO-DATA: no log found |  |
| intel1 | lecq9-c8be6220489b | lecq9-c8be6220489b | - | 0.6 |  | NO-DATA: no log found |  |
| intel1 | otc-178621-11182 | 178621 | - | 5.9 |  | NO-DATA: no log found |  |
| intel1 | otc-2860019-3888 | 2860019 | grt_i0 | 3.0 | last meaningful line 0.0 h ago (31/32 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-3479258-28963 | 3479258 | - | 6.3 |  | NO-DATA: no log found |  |
| intel1 | otc-3878162-6060 | 3878162 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | so_163257_ff_12111 | so_163257_ff_12111 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | so_163257_tt_12111 | so_163257_tt_12111 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | so_966964_ff_70293 | so_966964_ff_70293 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (35/35 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | so_966964_tt_70293 | so_966964_tt_70293 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (35/35 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-coll_n-1319177 | coll_n | tt_setup_repair_grt | 0.5 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | 5_1_grt | 0.5 | last meaningful line 0.1 h ago (2006/3169 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-hd_mesh-1361156 | hd_mesh | 3_4_place_resized | 0.5 | last meaningful line 0.0 h ago (270/270 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-1998989 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_Wi-2160767 | kv3_hub_Wi | 3_5_place_dp | 4.1 | last meaningful line 0.1 h ago (126/126 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-1558093 | kv3_io_ft | abstract_exact | 1.7 | last meaningful line 0.3 h ago (4/4 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8e7d31598-3690925 | kv3_pc_v1 | 3_3_place_gp | 1.2 | overflow best 0.1048 last 0.1048 rows 45 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 11.2 | drt_violations best 51122 last 51122 rows 2 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 16.2 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 16.2 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 16.2 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 34.9 | drt_violations best 200 last 204 rows 58 | before-window best 212, window best 200 | PROGRESS: drt_violations improved 5.7 % in window |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | 5_2_route | 12.5 | drt_violations best 1062 last 1062 rows 13 | before-window best 255884, window best 1062 | PROGRESS: drt_violations improved 99.6 % in window |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | 5_2_route | 12.6 | drt_violations best 23696 last 23696 rows 8 | before-window best 211004, window best 23696 | PROGRESS: drt_violations improved 88.8 % in window |  |
| epyc7 | dpkit-serdes__t4-2238679 | serdes__t4 | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 20.2 | drt_violations best 3792 last 3792 rows 16 | before-window best 15298, window best 3792 | PROGRESS: drt_violations improved 75.2 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 20.2 | drt_violations best 14890 last 14890 rows 13 | before-window best 89585, window best 14890 | PROGRESS: drt_violations improved 83.4 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 20.6 | drt_violations best 544 last 544 rows 27 | before-window best 8753, window best 544 | PROGRESS: drt_violations improved 93.8 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 13.4 | drt_violations best 11088 last 44179 rows 18 | before-window best 29482, window best 11088 | PROGRESS: drt_violations improved 62.4 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 12.4 | drt_violations best 36 last 36 rows 14 | before-window best 174806, window best 36 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 5_2_route | 14.0 | drt_violations best 6 last 8 rows 51 | before-window best 176025, window best 6 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 20.2 | drt_violations best 13859 last 13859 rows 5 | before-window best 470122, window best 13859 | PROGRESS: drt_violations improved 97.1 % in window |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc382fb14-2382304 | col_h9_r1__t1 | 4_1_cts | 0.1 | repair_Violations best 0 last 0 rows 24 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 11.2 | drt_violations best 25575 last 25575 rows 3 | before-window best 171015, window best 25575 | PROGRESS: drt_violations improved 85.0 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 12.0 | drt_violations best 11491 last 11491 rows 4 | before-window best 176573, window best 11491 | PROGRESS: drt_violations improved 93.5 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 14.0 | drt_violations best 3028 last 3028 rows 12 | before-window best 178781, window best 3028 | PROGRESS: drt_violations improved 98.3 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-138946 | col_h9_r2__t1 | 5_2_route | 10.4 | drt_violations best 378 last 378 rows 21 | before-window best 151829, window best 378 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 24.9 | drt_violations best 390 last 408 rows 58 | before-window best 400, window best 390 | PROGRESS: drt_violations improved 2.5 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 12.5 | drt_violations best 8561 last 8561 rows 5 | before-window best 178567, window best 8561 | PROGRESS: drt_violations improved 95.2 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | 5_2_route | 13.8 | drt_violations best 375 last 376 rows 37 | before-window best 158828, window best 375 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 5_2_route | 13.3 | drt_violations best 373 last 373 rows 23 | before-window best 159056, window best 373 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 12.5 | drt_violations best 510 last 510 rows 21 | before-window best 157970, window best 510 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | 4_2_tapbal_grt | 0.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 16.9 | repair_TNS best 959.299 last 959.299 rows 5 | before-window best 1110.68, window best 959.299 | PROGRESS: repair_TNS improved 13.6 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | 5_2_route | 16.8 | drt_violations best 367 last 367 rows 37 | before-window best 159843, window best 367 | PROGRESS: drt_violations improved 99.8 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_2_route | 16.8 | drt_violations best 376 last 378 rows 31 | before-window best 159806, window best 376 | PROGRESS: drt_violations improved 99.8 % in window |  |
| intel1 | prd-eco_20261125_050013_1448739-i2t-515416 | eco_20261125_050013_1448739-i2t | 5_2_route | 5.8 | drt_violations best 0 last 0 rows 8 | PROGRESS: drt_violations reached 0 |  |
| intel2 | dpkit-coll_ftm-626876 | coll_ftm | 5_1_grt | 0.7 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel2 | dpkit-slice_station__t12-2056022 | slice_station__t12 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
