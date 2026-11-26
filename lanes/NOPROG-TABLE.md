# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 18:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'UNSIGNABLE': 2, 'GRT-LABEL': 5, 'YOUNG': 65, 'NO-DATA': 12, 'PROGRESS': 23}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 17.0 | drt_violations best 1 last 1 rows 54 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-STA-PROBE decides; n |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | pregrt_ff_hold | 8.2 | repair_TNS best 43306.7 last 43306.7 rows 1 | before-window best 43306.7, window best 43306.7 | NO-PROGRESS: repair_TNS best 43306.7 vs 43306.7 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (QC-C1O-COMPOSE decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 5_1_grt | 9.5 | grt rounds 4 overflow 5:130016 -> 10:3224 -> 15:2262 -> 20:2305 | UNSIGNABLE: GRT overflow flat: overflow 2262 at iteration 15 -> 2305 at iteration 20: flat f | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | tt_setup_repair | 7.9 | repair_Violations best 1899 last 1955 rows 49 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -649.96 ps (< -300, gate TT >= -42); job ag | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 31.7 | drt_violations best 4 last 4 rows 57 | before-window best 4, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 29.9 | drt_violations best 1 last 1 rows 45 | before-window best 1, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc12 | dpkit-sle_ctl__cla4f6f12f-254756 | sle_ctl | 5_1_grt | 6.8 | grt rounds 2 overflow 5:58301 -> 10:29756 | GRT-LABEL: DESIGN-FAIL: overflow 29756 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | 5_1_grt | 10.9 | grt rounds 7 overflow 10:2188 -> 15:1369 -> 20:1502 -> 25:1102 -> 30:804 -> 35:688 | GRT-LABEL: DESIGN-FAIL: overflow 2188 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 5_1_grt | 13.8 | grt rounds 6 overflow 5:121909 -> 10:2158 -> 15:1367 -> 20:1472 -> 25:1063 -> 30:774 | GRT-LABEL: DESIGN-FAIL: overflow 2158 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 5_1_grt | 13.7 | grt rounds 7 overflow 10:2244 -> 15:1394 -> 20:1584 -> 25:1212 -> 30:970 -> 35:768 | GRT-LABEL: DESIGN-FAIL: overflow 2244 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 5_1_grt | 13.9 | grt rounds 7 overflow 10:2290 -> 15:1427 -> 20:1597 -> 25:1148 -> 30:913 -> 35:770 | GRT-LABEL: DESIGN-FAIL: overflow 2290 at round 10 > 1000 |  |
| epyc10 | dpkit-serdes__t4-2124781 | serdes__t4 | 1_2_yosys | 0.1 | last meaningful line 0.1 h ago (315/315 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | lecaf-hdm-lbfifo | lecaf-hdm-lbfifo | - | 0.6 |  | NO-DATA: no log found |  |
| epyc10 | otc-1740051-27539 | 1740051 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | otc-1749574-29529 | 1749574 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | otc-1752802-15329 | 1752802 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | otc-2394688-5831 | 2394688 | flow | 0.0 | last meaningful line 0.0 h ago (565/565 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-1395551 | col_h9_r0_p5__t1 | 5_2_route | 9.4 | drt_violations best 93339 last 93339 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | 5_2_route | 9.5 | drt_violations best 255884 last 255884 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-1130830 | col_h9_r0_p5__t1 | 5_2_route | 9.5 | drt_violations best 392 last 392 rows 13 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc93af856-1168215 | col_h9_r0_p5__t1 | 5_2_route | 9.5 | drt_violations best 2595 last 2595 rows 5 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-1072222 | col_h9_r0_p5__t1 | 5_2_route | 9.6 | drt_violations best 73182 last 73182 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i3-2829259 | eco_20261124_200101_1087713-i3 | 5_2_route | 1.9 | last meaningful line 0.2 h ago (133/133 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | 5_1_grt | 4.7 | last meaningful line 0.0 h ago (268/270 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc12 | dpkit-native59-478901 | native59 | postcts_gate_TT | 6.6 | last meaningful line 0.1 h ago (21/21 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dproto-qc-c1p_r6-kit | dproto-qc-c1p_r6-kit | qc_c1p_r6_proto | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc12 | dproto-s81-c10b_r10-kit | dproto-s81-c10b_r10-kit | qc_c1p_r6_proto | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 15.4 |  | NO-DATA: no log found |  |
| epyc12 | otc-1018093-23130 | 1018093 | asbuilt.yosys | 0.2 | last meaningful line 0.0 h ago (135444/135444 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | otc-1036482-13287 | 1036482 | asbuilt.yosys | 0.2 | last meaningful line 0.0 h ago (135778/135778 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | otc-662226-14462 | 662226 | asbuilt.yosys | 0.4 | last meaningful line 0.1 h ago (242584/242584 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-hd_ctl-2980421 | hd_ctl | 5_1_grt | 0.9 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | 5_2_route | 9.6 | drt_violations best 211004 last 211004 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-2967544 | sle_hc0 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (5376/5376 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2980426 | slw_fw_v2 | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (5474/5474 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 13.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 13.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 13.2 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-serdes__t4-1494095 | serdes__t4 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (250/250 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 5_2_route | 13.0 | drt_violations best 45 last 45 rows 15 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-4138629 | sle_sc_v2 | postcts_gate_FF | 0.7 | last meaningful line 0.0 h ago (904/904 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | otc-2739402-5290 | 2739402 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc7 | otc-639211-10962 | 639211 | - | 9.7 |  | NO-DATA: no log found |  |
| epyc7 | so_722968_ff_45150 | so_722968_ff_45150 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-hd_lep0N-1428251 | hd_lep0N | reg_fanout | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-kv3_hub_Eo-1982614 | kv3_hub_Eo | 3_5_place_dp | 1.2 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-native59-2892451 | native59 | generate_abstract | 7.8 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_2_route | 8.4 | drt_violations best 224764 last 224764 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | otc-3731784-29079 | 3731784 | - | 2.0 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_104318_3955073-i3t-2865255 | eco_20261125_104318_3955073-i3t | 5_2_route | 0.9 | last meaningful line 0.0 h ago (275/276 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 7.4 | last meaningful line 0.5 h ago (279/280 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 9.4 | drt_violations best 174806 last 174806 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | 5_1_grt | 6.9 | last meaningful line 0.1 h ago (163/163 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_2_route | 11.0 | last meaningful line 0.5 h ago (285/286 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 5_2_route | 7.4 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 8.0 | last meaningful line 0.8 h ago (277/278 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 5_1_grt | 7.3 | last meaningful line 0.0 h ago (153/153 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 8.2 | drt_violations best 171015 last 171015 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 9.0 | drt_violations best 176573 last 176573 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-138946 | col_h9_r2__t1 | 5_2_route | 7.4 | drt_violations best 151829 last 151829 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 9.5 | drt_violations best 178567 last 178567 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 7.5 | last meaningful line 0.5 h ago (280/281 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 9.5 | drt_violations best 4807 last 4807 rows 5 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 9.5 | last meaningful line 0.0 h ago (160/160 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261126_020316_3686099-i1t-150182 | eco_20261126_020316_3686099-i1t | 5_1_grt | 0.7 | last meaningful line 0.2 h ago (320/1068 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 13.9 | repair_TNS best 7949.85 last 7949.85 rows 3 | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_2_route | 8.3 | last meaningful line 0.5 h ago (280/281 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-3824626 | coll_ftc | 5_2_route | 8.4 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Wo-190641 | kv3_hub_Wo | 3_1_place_gp_skip_io | 1.0 | overflow best 0.1548 last 0.1548 rows 44 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-kv3_phy-2319611 | kv3_phy | 3_3_place_gp | 0.2 | overflow best 0.2134 last 0.2312 rows 9 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-kv3_phy_v1-2455518 | kv3_phy_v1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_sys_SD_v1-2316647 | kv3_sys_SD_v1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9974 last 0.9974 rows 11 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | 5_2_route | 8.9 | last meaningful line 0.1 h ago (136/136 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-4035353 | slw_hc3 | 5_2_route | 8.3 | drt_violations best 64077 last 64077 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | otc-178621-11182 | 178621 | - | 2.9 |  | NO-DATA: no log found |  |
| intel1 | otc-207040-3394 | 207040 | signoff | 2.9 | last meaningful line 2.8 h ago (3/3 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | otc-3479258-28963 | 3479258 | - | 3.3 |  | NO-DATA: no log found |  |
| intel1 | otc-957737-21247 | 957737 | signoff | 2.6 | last meaningful line 2.5 h ago (3/3 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | prd-count-p1_tc-3236766 | count-p1_tc | prd_count_p1_tc | 0.2 | last meaningful line 0.0 h ago (806/806 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i2t-515416 | eco_20261125_050013_1448739-i2t | 5_2_route | 2.8 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | prd-eco_20261125_070347_2847958-i2-1134837 | eco_20261125_070347_2847958-i2 | 5_2_route | 2.5 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | prd-eco_20261125_131510_2862538-i3t-4003777 | eco_20261125_131510_2862538-i3t | 5_2_route | 1.2 | drt_violations best 36 last 36 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| intel1 | so_2598673_ff_45841 | so_2598673_ff_45841 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (28/28 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | so_2598673_tt_45841 | so_2598673_tt_45841 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (28/28 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3900738 | coll_ftm | 5_1_grt | 0.5 | repair_Remaining best 29798 last 29798 rows 20 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-kv3_hub_Wi-2160767 | kv3_hub_Wi | 2_1_floorplan | 1.1 | last meaningful line 0.3 h ago (342/342 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-3945642 | slice_station__t12 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (200/200 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_2_route | 8.2 | last meaningful line 0.2 h ago (281/282 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 31.9 | drt_violations best 212 last 212 rows 51 | before-window best 228, window best 212 | PROGRESS: drt_violations improved 7.0 % in window |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_1_grt | 9.5 | repair_TNS best 3347.59 last 3347.59 rows 14 | before-window best 4276.56, window best 3347.59 | PROGRESS: repair_TNS improved 21.7 % in window |  |
| epyc12 | dpkit-slice_station__t50__cld84c9e24-650458 | slice_station__t50 | 5_2_route | 3.5 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 17.2 | drt_violations best 4967 last 4967 rows 13 | before-window best 477402, window best 4967 | PROGRESS: drt_violations improved 99.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 17.2 | drt_violations best 20628 last 20628 rows 10 | before-window best 493451, window best 20628 | PROGRESS: drt_violations improved 95.8 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 17.6 | drt_violations best 852 last 852 rows 20 | before-window best 468535, window best 852 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 10.4 | drt_violations best 13227 last 13227 rows 14 | before-window best 44762, window best 13227 | PROGRESS: drt_violations improved 70.5 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 34.6 | drt_violations best 13 last 13 rows 53 | before-window best 14, window best 13 | PROGRESS: drt_violations improved 7.1 % in window |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3804990 | col_h10_r0_p1__t1 | 5_1_grt | 9.0 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 5_2_route | 11.0 | drt_violations best 22620 last 22620 rows 3 | before-window best 176025, window best 22620 | PROGRESS: drt_violations improved 87.1 % in window |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-870318 | col_h9_r0_p3__t1 | 5_1_grt | 8.8 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 20.0 | drt_violations best 7395 last 7395 rows 8 | before-window best 535484, window best 7395 | PROGRESS: drt_violations improved 98.6 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 17.2 | drt_violations best 118691 last 118691 rows 2 | before-window best 470122, window best 118691 | PROGRESS: drt_violations improved 74.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 11.0 | drt_violations best 42293 last 42293 rows 2 | before-window best 178781, window best 42293 | PROGRESS: drt_violations improved 76.3 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 21.9 | drt_violations best 392 last 392 rows 51 | before-window best 530, window best 392 | PROGRESS: drt_violations improved 26.0 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-2945122 | col_h9_r2__t1 | 5_2_route | 10.7 | drt_violations best 371 last 375 rows 30 | before-window best 154176, window best 371 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | 5_2_route | 10.8 | drt_violations best 2069 last 2069 rows 12 | before-window best 158828, window best 2069 | PROGRESS: drt_violations improved 98.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 5_2_route | 10.3 | drt_violations best 36012 last 36012 rows 2 | before-window best 159056, window best 36012 | PROGRESS: drt_violations improved 77.4 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | 5_2_route | 13.9 | drt_violations best 12039 last 12039 rows 4 | before-window best 178263, window best 12039 | PROGRESS: drt_violations improved 93.2 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | 5_2_route | 13.8 | drt_violations best 582 last 582 rows 11 | before-window best 159843, window best 582 | PROGRESS: drt_violations improved 99.6 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_2_route | 13.8 | drt_violations best 1306 last 1306 rows 10 | before-window best 159806, window best 1306 | PROGRESS: drt_violations improved 99.2 % in window |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 27.4 | drt_violations best 3448 last 3448 rows 11 | before-window best 278493, window best 3448 | PROGRESS: drt_violations improved 98.8 % in window |  |
| intel2 | dpkit-kv3_io_ft-3901304 | kv3_io_ft | 5_1_grt | 0.5 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
