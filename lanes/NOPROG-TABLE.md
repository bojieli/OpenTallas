# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 21:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 3, 'NO-PROGRESS': 2, 'GRT-LABEL': 3, 'YOUNG': 96, 'NO-DATA': 34, 'EXCLUDED': 3, 'KEEP': 2, 'PROGRESS': 30}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | 5_1_grt | 7.5 | grt rounds 7 overflow 10:2178 -> 15:1693 -> 20:894 -> 25:15 -> 30:4 -> 35:8 | UNSIGNABLE: GRT overflow flat: overflow 4 at iteration 30 -> 8 at iteration 35: flat for 5 i | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 37.4 | drt_violations best 13 last 13 rows 53 | before-window best 13, window best 13 | NO-PROGRESS: drt_violations best 13 vs 13 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 5_1_grt | 12.2 | grt rounds 7 overflow 10:3224 -> 15:2262 -> 20:2305 -> 25:2156 -> 30:1933 -> 35:1923 | UNSIGNABLE: GRT overflow flat: overflow 1933 at iteration 30 -> 1923 at iteration 35: flat f | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 5_1_grt | 16.5 | grt rounds 8 overflow 15:1367 -> 20:1472 -> 25:1063 -> 30:774 -> 35:659 -> 40:652 | UNSIGNABLE: GRT overflow flat: overflow 659 at iteration 35 -> 652 at iteration 40: flat for | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 32.6 | drt_violations best 1 last 1 rows 47 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 10.1 | grt rounds 5 overflow 5:128855 -> 10:3237 -> 15:2296 -> 20:2337 -> 25:2143 | GRT-LABEL: DESIGN-FAIL: overflow 3237 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 5_1_grt | 16.5 | grt rounds 9 overflow 20:1584 -> 25:1212 -> 30:970 -> 35:768 -> 40:889 -> 45:735 | GRT-LABEL: DESIGN-FAIL: overflow 2244 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 5_1_grt | 16.6 | grt rounds 9 overflow 20:1597 -> 25:1148 -> 30:913 -> 35:770 -> 40:787 -> 45:655 | GRT-LABEL: DESIGN-FAIL: overflow 2290 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-3140082 | dsdv_slice_c1x_C__t5 | 3_5_place_dp | 2.5 | last meaningful line 0.3 h ago (37/37 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-3152819 | dsdv_slice_c1x_C__t5 | 3_5_place_dp | 2.5 | last meaningful line 0.3 h ago (37/37 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-3157172 | dsdv_slice_c1x_C__t5 | 3_5_place_dp | 2.5 | last meaningful line 0.3 h ago (37/37 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-3854423 | dsdv_slice_c1x_C__t8 | 1_1_yosys_canonicalize | 0.7 | last meaningful line 0.2 h ago (130/130 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p6-4011229 | kv3_hg_v1p6 | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (319/319 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_io_cor-363026 | kv3_io_cor | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (177/177 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t3-4051614 | ot_s81sl_leaf__t3 | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (374/374 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_a_v2__clf4365a62-199111 | slw_st_a_v2 | 5_2_route | 2.0 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | hd-host-e-exact-pg-audit-1125 | hd-host-e-exact-pg-audit | form_exact_owned | 0.1 | last meaningful line 0.0 h ago (10/10 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | lecaf-hdm-full | lecaf-hdm-full | - | 2.2 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-16147f31a235 | lecq9-16147f31a235 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-32da6c3b9dec | lecq9-32da6c3b9dec | - | 1.3 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-c351666358dc | lecq9-c351666358dc | - | 1.3 |  | NO-DATA: no log found |  |
| epyc10 | lecq9-d7634e345491 | lecq9-d7634e345491 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc10 | otc-2394688-5831 | 2394688 | grt_it0 | 2.8 | last meaningful line 0.8 h ago (33/34 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | ppr-s81-t5gp-1125181218-1110912 | ppr-s81-t5gp-1125181218 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | ppr-s81-t5gp-1125181245-1110594 | ppr-s81-t5gp-1125181245 | tcl | 0.0 | last meaningful line 0.0 h ago (6/6 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | otc-1154289-24691 | 1154289 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | otc-1157491-1702 | 1157491 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-native59-478901 | native59 | 5_2_route | 9.4 | drt_violations best 35216 last 35216 rows 2 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc12 | dpkit-sle_ctl__cla4f6f12f-1558951 | sle_ctl | postcts_gate_FF | 0.6 | last meaningful line 0.0 h ago (71/71 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc12 | otc-2360461-22068 | 2360461 | asbuilt.yosys | 0.2 | last meaningful line 0.0 h ago (136476/136476 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-slice-station--t22-grt-1388493 | slice-station--t22-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-hd_host_e-1217627 | hd_host_e | 3_5_place_dp | 0.1 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-4027604 | kv3_pc_v1 | 3_3_place_gp | 0.8 | overflow best 0.5934 last 0.5934 rows 28 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | 5_2_route | 12.3 | drt_violations best 23696 last 23696 rows 8 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-2967544 | sle_hc0 | postcts_gate_TT | 3.7 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1991043 | sle_stm_v2 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-1997619 | sle_stm_v2 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t25-820854 | slice_station__t25 | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (260/260 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261125_200405_3323313-i1t-2801726 | eco_20261125_200405_3323313-i1t | 5_2_route | 1.4 | drt_violations best 52874 last 52874 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261125_211504_2977850-i1t-1003964 | eco_20261125_211504_2977850-i1t | 5_1_grt | 0.2 | last meaningful line 0.2 h ago (285/900 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t4-1017259 | dsdv_slice_c1x_C__t4 | sdc_lint | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3327555 | dsdv_slice_kv512_C__t1 | 3_3_place_gp | 1.0 | overflow best 0.6291 last 0.6291 rows 48 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N-1892837 | hd_lep0N | 2_3_floorplan_tapcell | 0.2 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | generate_abstract | 15.8 | last meaningful line 0.1 h ago (29/29 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | 5_2_route | 11.0 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | lecq9-09fe297654d7 | lecq9-09fe297654d7 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc7 | lecq9-0ce42cbdc4b0 | lecq9-0ce42cbdc4b0 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc7 | lecq9-1b3200859cc9 | lecq9-1b3200859cc9 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc7 | lecq9-59017ec270a7 | lecq9-59017ec270a7 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc7 | otc-1572699-31485 | 1572699 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc7 | otc-2739402-5290 | 2739402 | - | 4.1 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-2886348 | col_h10_r0_p1__t1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.7545 last 0.7545 rows 26 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvd8c0565f-3312328 | col_h10_r0_p4__t1 | 3_2_place_iop | 0.4 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-4054935 | col_h10_r1__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (327/327 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-4187149 | col_h10_r2__t1 | 3_1_place_gp_skip_io | 0.2 | last meaningful line -0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pvef55eb84-2279972 | col_h9_r0_p2__t1 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b-3911862 | col_h9_r0_p3__t1 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (314/314 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-1476523 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.8 | overflow best 0.1986 last 0.1986 rows 40 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvee6f8140-3305848 | col_h9_r0_p5__t1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.1979 last 0.1979 rows 38 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pvbdbd69f2-320365 | col_h9_r0_p6__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 987 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-col_h9_r2__t1__cl87f3ff59-380205 | col_h9_r2__t1 | 2_1_floorplan | 0.1 | repair_Viol best 2770 last 2770 rows 1361 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-3656096 | col_h9_r2__t1 | 3_3_place_gp | 0.3 | overflow best 0.1991 last 0.1991 rows 37 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv4937edd4-332941 | col_h9_r2__t1 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (1542/1542 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-686944 | col_h9_r2__t1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (251/251 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pvf9c773d5-576715 | col_h9_r2__t1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (236/236 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t10-3190993 | dsdv_slice_c1x_C__t10 | sdc_lint | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t6-4113643 | dsdv_slice_c1x_C__t6 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c3x_C__t1-3731856 | dsdv_slice_c3x_C__t1 | sdc_lint | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-gunit__t1-342903 | gunit__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (109/109 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-hd_lep0N-2958360 | hd_lep0N | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (8675/8675 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t3-1774923 | ot_s81sl_kv_leaf__t3 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t14-377632 | ot_s81sl_leaf__t14 | 1_synth | 0.1 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t2-2056355 | ot_s81sl_leaf__t2 | 3_3_place_gp | 0.7 | overflow best 0.3434 last 0.3557 rows 27 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t26-128578 | ot_s81sl_leaf__t26 | 2_3_floorplan_tapcell | 0.2 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t37-116748 | ot_s81sl_leaf__t37 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (1054/1054 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 11.1 | drt_violations best 4917 last 4917 rows 8 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc8 | lecaf-hc0-6e8 | lecaf-hc0-6e8 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc8 | lecaf-hc3-afda1e-twins | lecaf-hc3-afda1e-twins | - | 0.3 |  | NO-DATA: no log found |  |
| epyc8 | lecq9-125656921876 | lecq9 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc8 | lecq9-b821dc8b6fe0 | lecq9-b821dc8b6fe0 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc8 | lecq9-c8c740c6d798 | lecq9-c8c740c6d798 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-1530472-10583 | 1530472 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-1589750-5019 | 1589750 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-2693994-26282 | 2693994 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-3731784-29079 | 3731784 | - | 4.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-4174262-4961 | 4174262 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-877014-30307 | 877014 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-941401-14145 | 941401 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_104318_3955073-i3-312208 | eco_20261125_104318_3955073-i3 | 5_1_grt | 1.1 | last meaningful line 0.6 h ago (290/418 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261126_033711_2888564-i1t-928710 | eco_20261126_033711_2888564-i1t | 5_2_route | 1.9 | drt_violations best 7315 last 7315 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1193242 | col_h10_r1__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3470/3470 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 10.1 | drt_violations best 37095 last 37095 rows 2 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | 5_2_route | 9.6 | last meaningful line 0.3 h ago (284/285 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-21596 | col_h9_r0_p4__t1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3427/3427 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 13.8 | drt_violations best 545016 last 545016 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 10.2 | last meaningful line 0.5 h ago (284/285 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-1395873 | col_h9_r0_p5__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2727/2727 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1568817 | col_h9_r0_p6__t1 | 2_1_floorplan | 0.0 | repair_Viol best 3023 last 3023 rows 193 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 10.7 | drt_violations best 380531 last 380531 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 10.2 | drt_violations best 22392 last 22392 rows 3 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 5_1_grt | 10.6 | last meaningful line 0.3 h ago (284/286 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 12.3 | last meaningful line 2.0 h ago (277/1285 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mus_C__t1-1648329 | dsdv_slice_lepw_mus_C__t1 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t26-501697 | slice_station__t26 | 3_4_place_resized | 0.3 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t45-1580954 | slice_station__t45 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (963/963 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_020316_3686099-i1t-150182 | eco_20261126_020316_3686099-i1t | 5_2_route | 3.4 | drt_violations best 80636 last 80636 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 11.0 | drt_violations best 40191 last 40191 rows 2 | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p4-646455 | kv3_hg_v1p4 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.5071 last 0.5071 rows 29 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-1625008 | kv3_pc_v1 | 2_1_floorplan | 0.2 | repair_Viol best 8516 last 8516 rows 549 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_phy-3158276 | kv3_phy | abstract_exact | 2.6 | last meaningful line 0.3 h ago (4/4 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v2-172554 | kv3_pv_v2 | 3_3_place_gp | 0.7 | overflow best 0.4977 last 0.4977 rows 11 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v6-285159 | kv3_pv_v6 | 3_3_place_gp | 0.7 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_sys_SD_v1-3706384 | kv3_sys_SD_v1 | 6_1_fill | 2.4 | last meaningful line 0.0 h ago (13/13 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-3994132 | slw_hc0 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | 5_2_route | 11.6 | drt_violations best 75122 last 75122 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | lecq9-1e4ed353bf9a | lecq9-1e4ed353bf9a | - | 1.3 |  | NO-DATA: no log found |  |
| intel1 | lecq9-22dcfc2fafbf | lecq9-22dcfc2fafbf | - | 1.2 |  | NO-DATA: no log found |  |
| intel1 | lecq9-963f0492a10e | lecq9-963f0492a10e | - | 1.3 |  | NO-DATA: no log found |  |
| intel1 | lecq9-abc37a821c70 | lecq9-abc37a821c70 | - | 1.3 |  | NO-DATA: no log found |  |
| intel1 | lecq9-c8be6220489b | lecq9-c8be6220489b | - | 0.4 |  | NO-DATA: no log found |  |
| intel1 | otc-178621-11182 | 178621 | - | 5.7 |  | NO-DATA: no log found |  |
| intel1 | otc-2860019-3888 | 2860019 | flow | 2.7 | repair_Violations best 383 last 383 rows 30 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | otc-3479258-28963 | 3479258 | - | 6.1 |  | NO-DATA: no log found |  |
| intel1 | ppr-kvallfix-r7-hg_wn6-2887388 | ppr-kvallfix-r7-hg_wn6 | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261125_050013_1448739-i2t-515416 | eco_20261125_050013_1448739-i2t | 5_2_route | 5.5 | drt_violations best 10221 last 10221 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel1 | so_765087_ff_68209 | so_765087_ff_68209 | signoff | 0.5 |  | NO-DATA: empty log |  |
| intel1 | so_765087_tt_68209 | so_765087_tt_68209 | signoff | 0.5 |  | NO-DATA: empty log |  |
| intel1 | so_966964_ff_70293 | so_966964_ff_70293 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (35/35 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | so_966964_tt_70293 | so_966964_tt_70293 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (35/35 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-626876 | coll_ftm | 5_1_grt | 0.5 | repair_Remaining best 29798 last 29798 rows 20 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-coll_n-1319177 | coll_n | pregrt_ff_hold | 0.2 | repair_TNS best 11184 last 11184 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-coll_ucie-1323976 | coll_ucie | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_host_w-1348396 | hd_host_w | 3_3_place_gp | 0.2 | overflow best 0.0997 last 0.0997 rows 41 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-hd_mesh-1361156 | hd_mesh | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_Wi-2160767 | kv3_hub_Wi | 3_4_place_resized | 3.9 | last meaningful line 0.5 h ago (640/640 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-1558093 | kv3_io_ft | abstract_exact | 1.5 | last meaningful line 0.1 h ago (4/4 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8e7d31598-3690925 | kv3_pc_v1 | 3_3_place_gp | 0.9 | overflow best 0.7564 last 0.7564 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 11.0 | drt_violations best 51122 last 51122 rows 2 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 15.9 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 15.9 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 15.9 |  | EXCLUDED: experiment container (qcdrt-* / exp.log): no stage log by design, never judged ( |  |
| epyc8 | dpkit-col_h9_r2__t1__clb8d86cd5__pvb2cd22a7-3370025 | col_h9_r2__t1 | 3_5_place_dp | 0.4 |  | KEEP: col_h9_r2__t1__clb8d86cd5__pvb2cd22a7	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-203526 | col_h10_r2__t1 | 3_5_place_dp | 0.4 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 34.7 | drt_violations best 200 last 204 rows 58 | before-window best 212, window best 200 | PROGRESS: drt_violations improved 5.7 % in window |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_1_grt | 12.3 | last meaningful line 0.1 h ago (3115/3146 lines) | PROGRESS: log still growing |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | 5_2_route | 12.3 | drt_violations best 1688 last 1688 rows 11 | before-window best 255884, window best 1688 | PROGRESS: drt_violations improved 99.3 % in window |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 5_1_grt | 3.6 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 20.0 | drt_violations best 3792 last 3792 rows 16 | before-window best 20475, window best 3792 | PROGRESS: drt_violations improved 81.5 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 20.0 | drt_violations best 16003 last 16003 rows 12 | before-window best 89585, window best 16003 | PROGRESS: drt_violations improved 82.1 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 20.4 | drt_violations best 658 last 658 rows 26 | before-window best 10924, window best 658 | PROGRESS: drt_violations improved 94.0 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 13.2 | drt_violations best 11088 last 11088 rows 17 | before-window best 31895, window best 11088 | PROGRESS: drt_violations improved 65.2 % in window |  |
| epyc8 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-2986818 | col_h10_r2__t1 | 3_5_place_dp | 0.5 | repair_Violations best 0 last 0 rows 33 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv47efee8f-2913710 | col_h9_r1__t1 | 3_5_place_dp | 0.5 | repair_Violations best 0 last 0 rows 24 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8aaf8508-2950405 | col_h9_r1__t1 | 3_5_place_dp | 0.5 | repair_Violations best 0 last 0 rows 24 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 12.2 | drt_violations best 701 last 701 rows 9 | before-window best 174806, window best 701 | PROGRESS: drt_violations improved 99.6 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 5_2_route | 13.8 | drt_violations best 6 last 8 rows 48 | before-window best 176025, window best 6 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 22.8 | drt_violations best 394 last 398 rows 37 | before-window best 91585, window best 394 | PROGRESS: drt_violations improved 99.6 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 19.9 | drt_violations best 13859 last 13859 rows 5 | before-window best 470122, window best 13859 | PROGRESS: drt_violations improved 97.1 % in window |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-3826216 | col_h9_r1__t1 | 3_5_place_dp | 0.5 | repair_Violations best 0 last 0 rows 24 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 10.9 | drt_violations best 25575 last 25575 rows 3 | before-window best 171015, window best 25575 | PROGRESS: drt_violations improved 85.0 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 11.7 | drt_violations best 11491 last 11491 rows 4 | before-window best 176573, window best 11491 | PROGRESS: drt_violations improved 93.5 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 13.7 | drt_violations best 3597 last 3597 rows 11 | before-window best 178781, window best 3597 | PROGRESS: drt_violations improved 98.0 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-138946 | col_h9_r2__t1 | 5_2_route | 10.2 | drt_violations best 434 last 434 rows 17 | before-window best 151829, window best 434 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 24.6 | drt_violations best 390 last 408 rows 58 | before-window best 411, window best 390 | PROGRESS: drt_violations improved 5.1 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 12.2 | drt_violations best 11171 last 11171 rows 4 | before-window best 178567, window best 11171 | PROGRESS: drt_violations improved 93.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | 5_2_route | 13.6 | drt_violations best 375 last 376 rows 36 | before-window best 158828, window best 375 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 5_2_route | 13.0 | drt_violations best 374 last 374 rows 20 | before-window best 159056, window best 374 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 12.3 | drt_violations best 539 last 591 rows 19 | before-window best 157970, window best 539 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-543132 | col_h9_r2__t1 | 4_1_cts | 0.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 16.6 | repair_TNS best 1290.97 last 1290.97 rows 17 | before-window best 2063.49, window best 1290.97 | PROGRESS: repair_TNS improved 37.4 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | 5_2_route | 16.5 | drt_violations best 367 last 367 rows 34 | before-window best 159843, window best 367 | PROGRESS: drt_violations improved 99.8 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_2_route | 16.5 | drt_violations best 376 last 378 rows 30 | before-window best 159806, window best 376 | PROGRESS: drt_violations improved 99.8 % in window |  |
| intel1 | dpkit-coll_ftc-3824626 | coll_ftc | 5_2_route | 11.1 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
