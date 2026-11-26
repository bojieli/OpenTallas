# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 19:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'UNSIGNABLE': 1, 'GRT-LABEL': 6, 'YOUNG': 70, 'NO-DATA': 14, 'PROGRESS': 23}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 17.5 | drt_violations best 1 last 1 rows 54 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-STA-PROBE decides; n |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | 5_1_grt | 11.4 | grt rounds 8 overflow 15:1369 -> 20:1502 -> 25:1102 -> 30:804 -> 35:688 -> 40:714 | UNSIGNABLE: GRT overflow flat: overflow 688 at iteration 35 -> 714 at iteration 40: flat for | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 32.2 | drt_violations best 4 last 4 rows 57 | before-window best 4, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 30.4 | drt_violations best 1 last 1 rows 45 | before-window best 1, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | 5_1_grt | 5.2 | grt rounds 2 overflow 5:3923 -> 10:2178 | GRT-LABEL: DESIGN-FAIL: overflow 2178 at round 10 > 1000 |  |
| epyc12 | dpkit-sle_ctl__cla4f6f12f-254756 | sle_ctl | 5_1_grt | 7.3 | grt rounds 2 overflow 5:58301 -> 10:29756 | GRT-LABEL: DESIGN-FAIL: overflow 29756 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 5_1_grt | 10.0 | grt rounds 5 overflow 5:130016 -> 10:3224 -> 15:2262 -> 20:2305 -> 25:2156 | GRT-LABEL: DESIGN-FAIL: overflow 3224 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 5_1_grt | 14.3 | grt rounds 6 overflow 5:121909 -> 10:2158 -> 15:1367 -> 20:1472 -> 25:1063 -> 30:774 | GRT-LABEL: DESIGN-FAIL: overflow 2158 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 5_1_grt | 14.2 | grt rounds 7 overflow 10:2244 -> 15:1394 -> 20:1584 -> 25:1212 -> 30:970 -> 35:768 | GRT-LABEL: DESIGN-FAIL: overflow 2244 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 5_1_grt | 14.4 | grt rounds 7 overflow 10:2290 -> 15:1427 -> 20:1597 -> 25:1148 -> 30:913 -> 35:770 | GRT-LABEL: DESIGN-FAIL: overflow 2290 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-3140082 | dsdv_slice_c1x_C__t5 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-3152819 | dsdv_slice_c1x_C__t5 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t5-3157172 | dsdv_slice_c1x_C__t5 | sdc_lint | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t4-2124781 | serdes__t4 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.4653 last 0.4653 rows 38 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | lecaf-hdm-lbfifo | lecaf-hdm-lbfifo | - | 1.1 |  | NO-DATA: no log found |  |
| epyc10 | otc-2394688-5831 | 2394688 | flow | 0.5 | last meaningful line 0.0 h ago (3359/3359 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-1395551 | col_h9_r0_p5__t1 | 5_2_route | 9.9 | drt_violations best 93339 last 93339 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | 5_2_route | 10.0 | drt_violations best 69825 last 69825 rows 2 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-1130830 | col_h9_r0_p5__t1 | 5_2_route | 10.0 | drt_violations best 391 last 396 rows 29 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-1072222 | col_h9_r0_p5__t1 | 5_2_route | 10.1 | drt_violations best 5669 last 5669 rows 3 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc11 | lecaf-hc0-487 | lecaf-hc0 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc11 | prd-eco_20261124_200101_1087713-i3-2829259 | eco_20261124_200101_1087713-i3 | 5_2_route | 2.4 | last meaningful line 0.1 h ago (290/291 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc12 | dpkit-hd_lep0N_w-2669380 | hd_lep0N_w | 3_3_place_gp | 0.2 | overflow best 0.6828 last 0.6828 rows 10 | YOUNG: stage 0.0 h < 1 h |  |
| epyc12 | dpkit-native59-478901 | native59 | 5_2_route | 7.1 | last meaningful line 0.0 h ago (256/257 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc12 | dproto-qc-c1p_r6-kit | dproto-qc-c1p_r6-kit | kv_a5t9_r6.otrun | 1.3 | last meaningful line 0.5 h ago (5/5 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 15.9 |  | NO-DATA: no log found |  |
| epyc12 | otc-2314321-27797 | 2314321 | asbuilt.yosys | 0.3 | last meaningful line 0.1 h ago (242584/242584 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | otc-2694973-18651 | 2694973 | asbuilt.yosys | 0.1 | last meaningful line 0.0 h ago (136516/136516 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | so_2691857_tt_91396 | so_2691857_tt_91396 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-hd_ctl-2980421 | hd_ctl | postcts_gate_TT | 1.4 | last meaningful line 0.0 h ago (487/487 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | 5_2_route | 10.1 | drt_violations best 73628 last 73628 rows 2 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-2967544 | sle_hc0 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (5450/5450 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t25-945390 | slice_station__t25 | 3_3_place_gp | 0.2 | overflow best 0.4567 last 0.4574 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (5820/5820 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 13.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 13.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 13.7 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 5_2_route | 13.5 | drt_violations best 38 last 38 rows 16 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-4138629 | sle_sc_v2 | 5_2_route | 1.2 | last meaningful line 0.1 h ago (135/135 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t42__cl4bd1432c-2510250 | slice_station__t42 | 3_4_place_resized | 0.2 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | 5_1_grt | 8.7 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | otc-1892608-7747 | 1892608 | signoff | 0.4 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | otc-2739402-5290 | 2739402 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc7 | otc-639211-10962 | 639211 | - | 10.2 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-hd_lep0N-1428251 | hd_lep0N | 3_3_place_gp | 0.6 | overflow best 0.3246 last 0.3246 rows 32 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-2186887 | kv3_pc | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8078 last 0.8465 rows 10 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-kv3_pc__cl254f2e73__r8b421e514-2311416 | kv3_pc | 3_1_place_gp_skip_io | 0.3 | overflow best 0.948 last 0.948 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-kv3_pc__cl5a95b461__r85c02c25c-2210605 | kv3_pc | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8731 last 0.8731 rows 4 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-kv3_pc__cl5a95b461__r882954158-2200126 | kv3_pc | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8656 last 0.8656 rows 6 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 8.9 | drt_violations best 224764 last 224764 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | otc-3731784-29079 | 3731784 | - | 2.5 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_104318_3955073-i3t-2865255 | eco_20261125_104318_3955073-i3t | 5_2_route | 1.4 | drt_violations best 90 last 90 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | so_2137418_ff_64208 | so_2137418_ff_64208 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc8 | so_2137418_tt_64208 | so_2137418_tt_64208 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 7.9 | drt_violations best 174634 last 174634 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 9.9 | drt_violations best 174806 last 174806 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-870318 | col_h9_r0_p3__t1 | 5_1_grt | 9.3 | last meaningful line 0.5 h ago (272/1283 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | 5_1_grt | 7.4 | last meaningful line 0.0 h ago (1443/1443 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 11.5 | last meaningful line 0.5 h ago (287/288 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 7.9 | last meaningful line 0.0 h ago (268/268 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 8.5 | last meaningful line 0.2 h ago (281/282 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 7.8 | last meaningful line 0.3 h ago (266/1276 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 8.7 | drt_violations best 171015 last 171015 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 9.5 | drt_violations best 176573 last 176573 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-138946 | col_h9_r2__t1 | 5_2_route | 7.9 | drt_violations best 30302 last 30302 rows 2 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 10.0 | drt_violations best 178567 last 178567 rows 1 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 8.0 | drt_violations best 162182 last 162182 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 10.0 | drt_violations best 3747 last 3747 rows 8 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | hold_gate | 8.4 | last meaningful line 0.0 h ago (964/964 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 10.0 | last meaningful line 0.0 h ago (180/180 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_020316_3686099-i1t-150182 | eco_20261126_020316_3686099-i1t | 5_2_route | 1.2 | last meaningful line 0.0 h ago (267/267 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 14.4 | grt_hold_TNS best 6595.6 last 6595.6 rows 5 | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 8.8 | drt_violations best 167111 last 167111 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-3824626 | coll_ftc | 5_2_route | 8.9 | drt_violations best 59568 last 59568 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Wo-190641 | kv3_hub_Wo | 3_3_place_gp | 1.5 | overflow best 0.2909 last 0.7091 rows 108 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-kv3_phy_v1-3335698 | kv3_phy_v1 | tt_setup_repair_grt | 0.3 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_sys_SD_v1-3706384 | kv3_sys_SD_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (1592/1592 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | 5_2_route | 9.4 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-4035353 | slw_hc3 | 5_2_route | 8.8 | drt_violations best 64077 last 64077 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | otc-178621-11182 | 178621 | - | 3.4 |  | NO-DATA: no log found |  |
| intel1 | otc-207040-3394 | 207040 | signoff | 3.4 | last meaningful line 3.3 h ago (3/3 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | otc-2860019-3888 | 2860019 | flow | 0.5 | last meaningful line 0.0 h ago (3876/3876 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | otc-3479258-28963 | 3479258 | - | 3.8 |  | NO-DATA: no log found |  |
| intel1 | otc-957737-21247 | 957737 | signoff | 3.1 | last meaningful line 3.0 h ago (3/3 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i2t-515416 | eco_20261125_050013_1448739-i2t | 5_2_route | 3.3 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | prd-eco_20261125_070347_2847958-i2-1134837 | eco_20261125_070347_2847958-i2 | 5_2_route | 3.0 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | prd-fin-3236766 | fin | 6_report | 0.3 | last meaningful line 0.0 h ago (909/909 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | so_2598673_ff_45841 | so_2598673_ff_45841 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (28/28 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | so_2598673_tt_45841 | so_2598673_tt_45841 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (28/28 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3900738 | coll_ftm | 5_2_route | 1.0 | last meaningful line 0.0 h ago (225/225 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_Wi-2160767 | kv3_hub_Wi | 3_1_place_gp_skip_io | 1.6 | overflow best 0.2286 last 0.2286 rows 39 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-kv3_io_ft-3901304 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5443 last 5443 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-3945642 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 2986 last 2986 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 8.7 | drt_violations best 211273 last 211273 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 32.4 | drt_violations best 212 last 212 rows 51 | before-window best 228, window best 212 | PROGRESS: drt_violations improved 7.0 % in window |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_1_grt | 10.0 | repair_TNS best 2202.79 last 2202.79 rows 15 | before-window best 3005.49, window best 2202.79 | PROGRESS: repair_TNS improved 26.7 % in window |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc93af856-1168215 | col_h9_r0_p5__t1 | 5_2_route | 10.0 | drt_violations best 403 last 403 rows 12 | before-window best 260066, window best 403 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc7 | dpkit-serdes__t4-2077568 | serdes__t4 | 4_1_cts | 0.3 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 17.7 | drt_violations best 4336 last 4336 rows 14 | before-window best 477402, window best 4336 | PROGRESS: drt_violations improved 99.1 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 17.7 | drt_violations best 18390 last 18390 rows 11 | before-window best 493451, window best 18390 | PROGRESS: drt_violations improved 96.3 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 18.1 | drt_violations best 783 last 783 rows 22 | before-window best 468535, window best 783 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 10.9 | drt_violations best 11831 last 11831 rows 15 | before-window best 39674, window best 11831 | PROGRESS: drt_violations improved 70.2 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 35.1 | drt_violations best 13 last 13 rows 53 | before-window best 14, window best 13 | PROGRESS: drt_violations improved 7.1 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 5_2_route | 11.5 | drt_violations best 5148 last 5148 rows 4 | before-window best 176025, window best 5148 | PROGRESS: drt_violations improved 97.1 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 20.5 | drt_violations best 6113 last 6113 rows 9 | before-window best 535484, window best 6113 | PROGRESS: drt_violations improved 98.9 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 17.7 | drt_violations best 118691 last 118691 rows 2 | before-window best 470122, window best 118691 | PROGRESS: drt_violations improved 74.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 11.5 | drt_violations best 42293 last 42293 rows 2 | before-window best 178781, window best 42293 | PROGRESS: drt_violations improved 76.3 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 22.4 | drt_violations best 392 last 392 rows 51 | before-window best 509, window best 392 | PROGRESS: drt_violations improved 23.0 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-2945122 | col_h9_r2__t1 | 5_2_route | 11.2 | drt_violations best 368 last 368 rows 37 | before-window best 154176, window best 368 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | 5_2_route | 11.3 | drt_violations best 1048 last 1048 rows 14 | before-window best 158828, window best 1048 | PROGRESS: drt_violations improved 99.3 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 5_2_route | 10.8 | drt_violations best 22034 last 22034 rows 3 | before-window best 159056, window best 22034 | PROGRESS: drt_violations improved 86.1 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | 5_2_route | 14.4 | drt_violations best 9209 last 9209 rows 5 | before-window best 178263, window best 9209 | PROGRESS: drt_violations improved 94.8 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | 5_2_route | 14.3 | drt_violations best 382 last 382 rows 15 | before-window best 159843, window best 382 | PROGRESS: drt_violations improved 99.8 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_2_route | 14.3 | drt_violations best 486 last 486 rows 13 | before-window best 159806, window best 486 | PROGRESS: drt_violations improved 99.7 % in window |  |
| intel1 | dpkit-kv3_phy-3158276 | kv3_phy | 5_1_grt | 0.3 | repair_TNS best 0 last 0 rows 16 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 27.9 | drt_violations best 1588 last 1588 rows 13 | before-window best 278493, window best 1588 | PROGRESS: drt_violations improved 99.4 % in window |  |
| intel1 | prd-eco_20261125_131510_2862538-i3-3762728 | eco_20261125_131510_2862538-i3 | 5_1_grt | 0.1 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
