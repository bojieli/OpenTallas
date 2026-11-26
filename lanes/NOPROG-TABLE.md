# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 19:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'UNSIGNABLE': 3, 'GRT-LABEL': 5, 'YOUNG': 71, 'NO-DATA': 14, 'KEEP': 1, 'PROGRESS': 25}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 35.6 | drt_violations best 13 last 13 rows 53 | before-window best 13, window best 13 | NO-PROGRESS: drt_violations best 13 vs 13 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | 5_1_grt | 11.9 | grt rounds 8 overflow 15:1369 -> 20:1502 -> 25:1102 -> 30:804 -> 35:688 -> 40:714 | UNSIGNABLE: GRT overflow flat: overflow 688 at iteration 35 -> 714 at iteration 40: flat for | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 32.7 | drt_violations best 4 last 4 rows 57 | before-window best 4, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 5_1_grt | 14.7 | grt rounds 8 overflow 15:1394 -> 20:1584 -> 25:1212 -> 30:970 -> 35:768 -> 40:889 | UNSIGNABLE: GRT overflow flat: overflow 768 at iteration 35 -> 889 at iteration 40: flat for | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 5_1_grt | 14.9 | grt rounds 8 overflow 15:1427 -> 20:1597 -> 25:1148 -> 30:913 -> 35:770 -> 40:787 | UNSIGNABLE: GRT overflow flat: overflow 770 at iteration 35 -> 787 at iteration 40: flat for | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 30.9 | drt_violations best 1 last 1 rows 47 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:3923 -> 10:2178 -> 15:1693 | GRT-LABEL: DESIGN-FAIL: overflow 2178 at round 10 > 1000 |  |
| epyc12 | dpkit-sle_ctl__cla4f6f12f-254756 | sle_ctl | 5_1_grt | 7.8 | grt rounds 2 overflow 5:58301 -> 10:29756 | GRT-LABEL: DESIGN-FAIL: overflow 29756 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 5_1_grt | 10.5 | grt rounds 5 overflow 5:130016 -> 10:3224 -> 15:2262 -> 20:2305 -> 25:2156 | GRT-LABEL: DESIGN-FAIL: overflow 3224 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 8.3 | grt rounds 3 overflow 5:128855 -> 10:3237 -> 15:2296 | GRT-LABEL: DESIGN-FAIL: overflow 3237 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 5_1_grt | 14.8 | grt rounds 7 overflow 10:2158 -> 15:1367 -> 20:1472 -> 25:1063 -> 30:774 -> 35:659 | GRT-LABEL: DESIGN-FAIL: overflow 2158 at round 10 > 1000 |  |
| epyc10 | dpkit-col_h10_r0_p4__t1__pv5b623e07-549929 | col_h10_r0_p4__t1 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.803 last 0.803 rows 8 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-236605 | col_h10_r1__t1 | 3_4_place_resized | 0.2 | repair_Remaining best 55248 last 55248 rows 59 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-492237 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9951 last 0.9951 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-398291 | col_h9_r0_p3__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (322/322 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-3140082 | dsdv_slice_c1x_C__t5 | 1_1_yosys_canonicalize | 0.7 | last meaningful line 0.2 h ago (133/133 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-3152819 | dsdv_slice_c1x_C__t5 | 1_1_yosys_canonicalize | 0.7 | last meaningful line 0.2 h ago (133/133 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-3157172 | dsdv_slice_c1x_C__t5 | 1_1_yosys_canonicalize | 0.7 | last meaningful line 0.2 h ago (133/133 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-hd_serdes-79886 | hd_serdes | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl7f648944__r8e7d31598-3801299 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.787 last 0.787 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slw_hc2__cla3497502__cldc737267-713682 | slw_hc2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (406/406 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_a_v2__clf4365a62-199111 | slw_st_a_v2 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (6037/6037 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | lecaf-hdm-full | lecaf-hdm-full | - | 0.4 |  | NO-DATA: no log found |  |
| epyc10 | otc-2394688-5831 | 2394688 | flow | 1.0 | last meaningful line 0.0 h ago (3524/3524 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-1395551 | col_h9_r0_p5__t1 | 5_2_route | 10.4 | drt_violations best 14696 last 14696 rows 2 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | 5_2_route | 10.5 | drt_violations best 45158 last 45158 rows 3 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-1072222 | col_h9_r0_p5__t1 | 5_2_route | 10.6 | drt_violations best 391 last 400 rows 26 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc11 | lecaf-hc0-487 | lecaf-hc0 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc11 | prd-eco_20261124_200101_1087713-i3-2829259 | eco_20261124_200101_1087713-i3 | 5_2_route | 2.9 | last meaningful line 0.2 h ago (298/299 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc12 | dclk-eco10A-otclk-3619416 | dclk-eco10A-otclk | - | 0.1 |  | NO-DATA: no log found |  |
| epyc12 | dpkit-native59-478901 | native59 | 5_2_route | 7.6 | last meaningful line 0.1 h ago (264/265 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc12 | dproto-qc-c1p_r6-kit | dproto-qc-c1p_r6-kit | kv_a5t9_r6.otrun | 1.8 | last meaningful line 1.0 h ago (5/5 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc12 | otc-3320844-14338 | 3320844 | asbuilt.yosys | 0.2 | last meaningful line 0.0 h ago (136805/136805 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | prd-eco_20261126_031548_650250-i1-2936422 | eco_20261126_031548_650250-i1 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (242/242 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-hd_ctl-2980421 | hd_ctl | 5_2_route | 1.9 | last meaningful line 0.0 h ago (246/247 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | 5_2_route | 10.6 | drt_violations best 61430 last 61430 rows 3 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-2967544 | sle_hc0 | 4_1_cts | 1.9 | last meaningful line 0.0 h ago (5607/5607 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | generate_abstract | 18.0 | last meaningful line 0.0 h ago (57/57 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1991043 | sle_stm_v2 | 3_3_place_gp | 0.1 | overflow best 0.5047 last 0.5066 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-1997619 | sle_stm_v2 | 3_3_place_gp | 0.1 | overflow best 0.4791 last 0.4813 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 4_1_cts | 1.9 | last meaningful line 0.1 h ago (5900/5900 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 14.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 14.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 14.2 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-bk_sel__t2-3189044 | bk_sel__t2 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.3178 last 0.3178 rows 34 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-3753484 | col_h10_r2__t1 | 3_3_place_gp | 0.3 | overflow best 0.3717 last 0.3975 rows 25 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-3922647 | col_h9_r0_p2__t1 | 2_2_floorplan_macro | 0.2 | last meaningful line 0.0 h ago (211/211 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | 5_1_grt | 9.2 | last meaningful line 0.2 h ago (1292/2032 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | otc-1892608-7747 | 1892608 | signoff | 0.9 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | otc-2739402-5290 | 2739402 | - | 2.3 |  | NO-DATA: no log found |  |
| epyc7 | otc-639211-10962 | 639211 | - | 10.7 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-2186887 | kv3_pc | 3_3_place_gp | 0.8 | overflow best 0.1872 last 0.1872 rows 41 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-kv3_pc__cl254f2e73__r8b421e514-2311416 | kv3_pc | 3_3_place_gp | 0.8 | overflow best 0.2036 last 0.2036 rows 40 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-kv3_pc__cl5a95b461__r85c02c25c-2210605 | kv3_pc | 3_3_place_gp | 0.8 | overflow best 0.2047 last 0.2047 rows 40 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-kv3_pc__cl5a95b461__r882954158-2200126 | kv3_pc | 3_3_place_gp | 0.8 | overflow best 0.2026 last 0.2026 rows 40 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 9.4 | drt_violations best 57907 last 57907 rows 2 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | otc-3731784-29079 | 3731784 | - | 3.0 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261126_033711_2888564-i1t-928710 | eco_20261126_033711_2888564-i1t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-col-h9-r1--t1--cl49d7a23e--pv11dcdcd2-grt-983395 | col-h9-r1--t1--cl49d7a23e--pv11dcdcd2-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-dsdv-slice-c3x-C--t1-grt-677402 | dsdv-slice-c3x-C--t1-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 8.4 | drt_violations best 174634 last 174634 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 10.4 | drt_violations best 174806 last 174806 rows 1 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-870318 | col_h9_r0_p3__t1 | 5_1_grt | 9.8 | last meaningful line 1.0 h ago (272/1299 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | postcts_gate_TT | 7.9 | last meaningful line 0.0 h ago (378/378 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 12.0 | last meaningful line 0.5 h ago (289/290 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 8.4 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 9.0 | last meaningful line 0.5 h ago (283/284 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 9.2 | drt_violations best 171015 last 171015 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 10.0 | drt_violations best 176573 last 176573 rows 1 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-138946 | col_h9_r2__t1 | 5_2_route | 8.4 | drt_violations best 4595 last 4595 rows 4 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 10.5 | drt_violations best 178567 last 178567 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 8.5 | drt_violations best 162182 last 162182 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | pregrt_ff_hold | 8.9 | repair_TNS best 236897 last 236897 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 10.5 | last meaningful line 0.3 h ago (277/279 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_020316_3686099-i1t-150182 | eco_20261126_020316_3686099-i1t | 5_2_route | 1.7 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 14.9 | repair_TNS best 5117.86 last 5117.86 rows 17 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 9.3 | drt_violations best 167111 last 167111 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-3824626 | coll_ftc | 5_2_route | 9.4 | drt_violations best 59568 last 59568 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Wo-190641 | kv3_hub_Wo | 3_3_place_gp | 2.0 | overflow best 0.0987 last 0.0998 rows 175 | YOUNG: stage 1.0 h < 1 h |  |
| intel1 | dpkit-kv3_phy-3158276 | kv3_phy | 5_2_route | 0.8 | last meaningful line 0.0 h ago (221/222 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_phy_v1-3335698 | kv3_phy_v1 | 5_2_route | 0.8 | last meaningful line 0.1 h ago (222/223 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | 5_2_route | 9.9 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-4035353 | slw_hc3 | 5_2_route | 9.3 | drt_violations best 4918 last 4918 rows 2 | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | eco-abs-416296 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.2 h ago (870/870 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-178621-11182 | 178621 | - | 3.9 |  | NO-DATA: no log found |  |
| intel1 | otc-207040-3394 | 207040 | signoff | 3.9 | last meaningful line 3.8 h ago (3/3 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | otc-2860019-3888 | 2860019 | flow | 1.0 | last meaningful line 0.1 h ago (4064/4064 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | otc-3479258-28963 | 3479258 | - | 4.3 |  | NO-DATA: no log found |  |
| intel1 | otc-681953-5114 | 681953 | - | 0.2 |  | NO-DATA: no log found |  |
| intel1 | otc-957737-21247 | 957737 | signoff | 3.6 | last meaningful line 3.5 h ago (3/3 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i2t-515416 | eco_20261125_050013_1448739-i2t | 5_2_route | 3.8 | drt_violations best 10221 last 10221 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | prd-eco_20261125_131510_2862538-i3-3762728 | eco_20261125_131510_2862538-i3 | 5_2_route | 0.6 | last meaningful line 0.1 h ago (242/243 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3900738 | coll_ftm | 5_2_route | 1.5 | last meaningful line 0.1 h ago (240/241 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_Wi-2160767 | kv3_hub_Wi | 3_3_place_gp | 2.1 | overflow best 0.6683 last 0.669 rows 11 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-kv3_io_ft-3901304 | kv3_io_ft | abstract_exact | 1.5 | last meaningful line 0.1 h ago (4/4 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 9.2 | drt_violations best 211273 last 211273 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-414504 | col_h10_r2__t1 | 3_3_place_gp | 0.2 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc10 | dpkit-serdes__t4-2124781 | serdes__t4 | 3_5_place_dp | 1.1 | repair_Violations best 0 last 0 rows 11 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 32.9 | drt_violations best 208 last 208 rows 53 | before-window best 214, window best 208 | PROGRESS: drt_violations improved 2.8 % in window |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_1_grt | 10.5 | repair_TNS best 1138.22 last 1138.22 rows 19 | before-window best 1938.01, window best 1138.22 | PROGRESS: repair_TNS improved 41.3 % in window |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc93af856-1168215 | col_h9_r0_p5__t1 | 5_2_route | 10.5 | drt_violations best 395 last 395 rows 23 | before-window best 260066, window best 395 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc7 | dpkit-serdes__t4-2077568 | serdes__t4 | 4_1_cts | 0.8 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 5_2_route | 14.0 | drt_violations best 16 last 16 rows 22 | before-window best 192025, window best 16 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 18.2 | drt_violations best 4336 last 4336 rows 14 | before-window best 477402, window best 4336 | PROGRESS: drt_violations improved 99.1 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 18.2 | drt_violations best 18390 last 18390 rows 11 | before-window best 493451, window best 18390 | PROGRESS: drt_violations improved 96.3 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 18.6 | drt_violations best 724 last 724 rows 23 | before-window best 105509, window best 724 | PROGRESS: drt_violations improved 99.3 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 11.4 | drt_violations best 11831 last 11831 rows 15 | before-window best 36694, window best 11831 | PROGRESS: drt_violations improved 67.8 % in window |  |
| epyc8 | prd-eco_20261125_104318_3955073-i3t-2865255 | eco_20261125_104318_3955073-i3t | 5_2_route | 1.9 | drt_violations best 0 last 0 rows 15 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 5_2_route | 12.0 | drt_violations best 769 last 769 rows 10 | before-window best 176025, window best 769 | PROGRESS: drt_violations improved 99.6 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 21.0 | drt_violations best 1948 last 1948 rows 11 | before-window best 135197, window best 1948 | PROGRESS: drt_violations improved 98.6 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 18.2 | drt_violations best 77076 last 77076 rows 3 | before-window best 470122, window best 77076 | PROGRESS: drt_violations improved 83.6 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 12.0 | drt_violations best 10497 last 10497 rows 4 | before-window best 178781, window best 10497 | PROGRESS: drt_violations improved 94.1 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 22.9 | drt_violations best 392 last 392 rows 51 | before-window best 454, window best 392 | PROGRESS: drt_violations improved 13.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | 5_2_route | 11.8 | drt_violations best 453 last 453 rows 17 | before-window best 158828, window best 453 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 5_2_route | 11.3 | drt_violations best 6264 last 6264 rows 4 | before-window best 159056, window best 6264 | PROGRESS: drt_violations improved 96.1 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 10.5 | drt_violations best 3361 last 3361 rows 10 | before-window best 157970, window best 3361 | PROGRESS: drt_violations improved 97.9 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | 5_2_route | 14.9 | drt_violations best 7930 last 7930 rows 6 | before-window best 178263, window best 7930 | PROGRESS: drt_violations improved 95.6 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | 5_2_route | 14.8 | drt_violations best 372 last 372 rows 20 | before-window best 159843, window best 372 | PROGRESS: drt_violations improved 99.8 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_2_route | 14.8 | drt_violations best 422 last 422 rows 15 | before-window best 159806, window best 422 | PROGRESS: drt_violations improved 99.7 % in window |  |
| intel1 | dpkit-kv3_sys_SD_v1-3706384 | kv3_sys_SD_v1 | 5_1_grt | 0.6 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 28.4 | drt_violations best 956 last 956 rows 14 | before-window best 278493, window best 956 | PROGRESS: drt_violations improved 99.7 % in window |  |
| intel1 | prd-eco_20261125_070347_2847958-i2-1134837 | eco_20261125_070347_2847958-i2 | 5_2_route | 3.5 | drt_violations best 0 last 0 rows 1 | PROGRESS: drt_violations reached 0 |  |
