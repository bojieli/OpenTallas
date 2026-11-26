# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 16:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 6, 'GRT-LABEL': 5, 'YOUNG': 77, 'NO-DATA': 15, 'PROGRESS': 19}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_hg_v1p3__r838481cd7-1149343 | kv3_hg_v1p3__r838481cd7 | 5_1_grt | 6.5 | grt rounds 2 overflow 5:39999 -> 10:36574 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -641.12 ps (< -300, gate TT >= -42); job age 6. | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc11 | dpkit-kv3_hub_Wi-2642655 | kv3_hub_Wi | tt_setup_repair | 6.2 | repair_Viol best 11509 last 11509 rows 20 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -3298.84 ps (< -300, gate TT >= -42); job a | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc12 | otc-3501458-13012 | 3501458 | run | 12.9 | last meaningful line 12.9 h ago (1/1 lines) | NO-PROGRESS: no new non-iteration log line for 12.9 h | REPORT-ONLY: lane-own kit (abstract-exact decides; |
| epyc12 | otc-351743-16220 | 351743 | hcpg_run | 10.7 | last meaningful line 10.3 h ago (13/13 lines) | NO-PROGRESS: no new non-iteration log line for 10.3 h | REPORT-ONLY: lane-own kit (abstract-exact decides; |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | pregrt_ff_hold | 4.4 | repair_TNS best 3446.33 last 3446.33 rows 1 | before-window best 3446.33, window best 3446.33 | NO-PROGRESS: repair_TNS best 3446.33 vs 3446.33 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | pregrt_ff_hold | 7.0 | repair_TNS best 115.834 last 115.834 rows 1 | before-window best 115.834, window best 115.834 | NO-PROGRESS: repair_TNS best 115.834 vs 115.834 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 29.2 | drt_violations best 4 last 4 rows 57 | before-window best 4, window best 4 | NO-PROGRESS: drt_violations best 4 vs 4 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 27.4 | drt_violations best 1 last 1 rows 45 | before-window best 1, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc7 | dpkit-kv3_pv_v12e-1804185 | kv3_pv_v12e | 5_1_grt | 8.3 | grt rounds 2 overflow 5:81061 -> 10:61082 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | 5_1_grt | 10.8 | grt rounds 2 overflow 5:32105 -> 10:5327 | GRT-LABEL: DESIGN-FAIL: overflow 5327 at round 10 > 1000 |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | 5_1_grt | 8.4 | grt rounds 3 overflow 5:120028 -> 10:2188 -> 15:1369 | GRT-LABEL: DESIGN-FAIL: overflow 2188 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 5_1_grt | 11.2 | grt rounds 3 overflow 5:123883 -> 10:2244 -> 15:1394 | GRT-LABEL: DESIGN-FAIL: overflow 2244 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 5_1_grt | 11.4 | grt rounds 3 overflow 5:119162 -> 10:2290 -> 15:1427 | GRT-LABEL: DESIGN-FAIL: overflow 2290 at round 10 > 1000 |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-1395551 | col_h9_r0_p5__t1 | 5_2_route | 6.9 | last meaningful line 0.3 h ago (276/277 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_1_grt | 7.0 | repair_TNS best 11433.6 last 11433.6 rows 5 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | 5_2_route | 7.0 | last meaningful line 0.3 h ago (289/290 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-1130830 | col_h9_r0_p5__t1 | 5_2_route | 7.0 | last meaningful line 0.4 h ago (288/289 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc93af856-1168215 | col_h9_r0_p5__t1 | 5_2_route | 7.0 | drt_violations best 260066 last 260066 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-1072222 | col_h9_r0_p5__t1 | 5_2_route | 7.1 | last meaningful line 0.2 h ago (282/283 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc11 | prd-count-p1_tc-3678404 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (47/47 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | so_1304500_ff_83931 | so_1304500_ff_83931 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (35/35 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | so_1304500_tt_83931 | so_1304500_tt_83931 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (35/35 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | ap-ageom-kw-hd-serdes-grt-1690296 | hd-serdes-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | pregrt_ff_hold | 2.2 | repair_TNS best 121568 last 121568 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc12 | dpkit-hd_serdes-1714034 | hd_serdes | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (191/191 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-sle_ctl__cla4f6f12f-254756 | sle_ctl | pregrt_ff_hold | 4.3 | repair_TNS best 267752 last 267752 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc12 | dpkit-slice_station__t24__cl64811a5d-1102657 | slice_station__t24 | tt_setup_repair_grt | 0.6 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t50__cl39451317-406569 | slice_station__t50 | 5_2_route | 4.2 | drt_violations best 18328 last 18328 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t50__cld84c9e24-650458 | slice_station__t50 | tt_setup_repair_grt | 1.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t7__cl362204c4-639423 | slice_station__t7 | 5_2_route | 1.0 | drt_violations best 4120 last 4120 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 12.9 |  | NO-DATA: no log found |  |
| epyc12 | so_1653512_ff_22738 | so_1653512_ff_22738 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc12 | so_1653512_tt_22738 | so_1653512_tt_22738 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | 5_2_route | 7.1 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 10.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 10.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 10.7 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 5_2_route | 10.5 | drt_violations best 192025 last 192025 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | pregrt_ff_hold | 5.7 | repair_TNS best 2.44591e+06 last 2.44591e+06 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-362758 | slw_hc2 | postcts_gate_FF | 5.8 | last meaningful line 0.0 h ago (90179/90179 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3806800 | slw_hc3 | 5_2_route | 6.1 | drt_violations best 5176 last 5176 rows 2 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | otc-639211-10962 | 639211 | - | 7.2 |  | NO-DATA: no log found |  |
| epyc7 | otc-728591-15662 | 728591 | signoff | 1.8 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | prd-count-p1_tc-3840527 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-hd-lep0N-grt-2107491 | hd-lep0N-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (126/126 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-native59-2892451 | native59 | 5_2_route | 5.3 | last meaningful line 0.1 h ago (251/251 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | postcts_gate_FF | 5.9 | last meaningful line 0.1 h ago (74032/74032 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v3-4131858 | sle_sc_v3 | 5_2_route | 6.2 | drt_violations best 13691 last 13691 rows 3 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-287710 | slw_hc3 | 5_2_route | 6.1 | drt_violations best 65914 last 65914 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | eco-abs-2278421 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-1609200-26446 | 1609200 | - | 8.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-1616827-18813 | 1616827 | - | 8.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-1633866-27286 | 1633866 | - | 6.9 |  | NO-DATA: no log found |  |
| epyc8 | otc-46863-5563 | 46863 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_104318_3955073-i2-1868164 | eco_20261125_104318_3955073-i2 | 5_2_route | 1.5 | drt_violations best 175 last 175 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | so_797683_ff_7360 | so_797683_ff_7360 | generate_abstract | 0.5 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | so_797683_tt_7360 | so_797683_tt_7360 | generate_abstract | 0.5 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-1427167 | col_h10_r0_p1__t1 | 5_1_grt | 7.7 | last meaningful line 0.7 h ago (275/1288 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 5_2_route | 17.5 | drt_violations best 14354 last 14354 rows 2 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 4.9 | last meaningful line 0.1 h ago (264/264 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 6.9 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 5_2_route | 8.5 | drt_violations best 176025 last 176025 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-870318 | col_h9_r0_p3__t1 | 5_1_grt | 6.3 | last meaningful line 0.2 h ago (162/162 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv8995e794-2664422 | col_h9_r0_p5__t1 | 5_1_grt | 8.3 | repair_TNS best 50898 last 50898 rows 4 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | postcts_gate_TT | 8.5 | last meaningful line -0.0 h ago (662/662 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_2_route | 5.5 | last meaningful line 0.1 h ago (143/143 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | pregrt_ff_hold | 4.8 | repair_TNS best 85658.9 last 85658.9 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 5.7 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 6.5 | last meaningful line 0.5 h ago (270/271 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 8.5 | drt_violations best 178781 last 178781 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-138946 | col_h9_r2__t1 | 5_2_route | 4.9 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 7.0 | last meaningful line 0.5 h ago (272/273 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 5.0 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-2945122 | col_h9_r2__t1 | 5_2_route | 8.2 | drt_violations best 19521 last 19521 rows 3 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | 5_2_route | 8.3 | drt_violations best 36329 last 36329 rows 2 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 5_2_route | 7.8 | drt_violations best 159056 last 159056 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 7.0 | drt_violations best 157970 last 157970 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 4_1_cts | 5.4 | last meaningful line 0.2 h ago (8482/8482 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-1920080 | dsdv_slice_c3x_C__t1 | 3_5_place_dp | 6.9 | last meaningful line 2.0 h ago (38/38 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | 4_1_cts | 7.0 | last meaningful line 0.0 h ago (6388/6388 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t31-407252 | slice_station__t31 | 5_2_route | 4.9 | drt_violations best 26978 last 26978 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 11.4 | repair_TNS best 20736.3 last 20736.3 rows 9 | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 5_1_grt | 11.3 | last meaningful line 0.0 h ago (269/271 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | 5_2_route | 11.4 | drt_violations best 178263 last 178263 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | 5_2_route | 11.3 | drt_violations best 159843 last 159843 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_2_route | 11.3 | drt_violations best 35793 last 35793 rows 2 | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | postcts_gate_FF | 5.8 | last meaningful line 0.0 h ago (411/411 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-3824626 | coll_ftc | postcts_gate_FF | 5.9 | last meaningful line 0.0 h ago (1353/1353 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | postcts_gate_FF | 6.4 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-4035353 | slw_hc3 | postcts_gate_TT | 5.8 | last meaningful line 0.1 h ago (364/364 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v3-99093 | slw_sc_v3 | postcts_gate_FF | 5.7 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-178621-11182 | 178621 | - | 0.4 |  | NO-DATA: no log found |  |
| intel1 | otc-2021095-31410 | 2021095 | signoff | 3.4 | last meaningful line 3.3 h ago (3/3 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | otc-207040-3394 | 207040 | signoff | 0.4 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | otc-2908840-11609 | 2908840 | grt_it0 | 6.2 | last meaningful line 2.5 h ago (33/34 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | otc-3338929-32249 | 3338929 | - | 0.9 |  | NO-DATA: no log found |  |
| intel1 | otc-3479258-28963 | 3479258 | - | 0.8 |  | NO-DATA: no log found |  |
| intel1 | otc-957737-21247 | 957737 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i3-3236766 | eco_20261123_191853_2879776-i3 | 5_2_route | 2.8 | last meaningful line 0.2 h ago (134/134 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1-1093733 | eco_20261125_002226_1452841-i1 | 5_2_route | 5.3 | drt_violations best 7 last 7 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i2t-515416 | eco_20261125_050013_1448739-i2t | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | prd-eco_20261125_070347_2847958-i2-1134837 | eco_20261125_070347_2847958-i2 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco_20261125_131510_2862538-i2t-2565729 | eco_20261125_131510_2862538-i2t | 5_2_route | 1.2 | drt_violations best 716 last 716 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-3246389 | kv3_io_ft | abstract_exact | 1.5 | last meaningful line 0.1 h ago (4/4 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | postcts_gate_FF | 5.7 | last meaningful line -0.0 h ago (11608/11608 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 29.4 | drt_violations best 212 last 212 rows 51 | before-window best 236, window best 212 | PROGRESS: drt_violations improved 10.2 % in window |  |
| epyc12 | dpkit-hd_st_n4-1311294 | hd_st_n4 | 5_1_grt | 0.4 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc12 | dpkit-native59-478901 | native59 | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc12 | prd-eco_20261126_000257_709121-i1-1559361 | eco_20261126_000257_709121-i1 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 14.5 | drt_violations best 1 last 1 rows 54 | before-window best 2, window best 1 | PROGRESS: drt_violations improved 50.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 14.7 | drt_violations best 11934 last 11934 rows 8 | before-window best 477402, window best 11934 | PROGRESS: drt_violations improved 97.5 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 14.7 | drt_violations best 31352 last 31352 rows 4 | before-window best 493451, window best 31352 | PROGRESS: drt_violations improved 93.6 % in window |  |
| epyc7 | dpkit-sle_sc_v2-22145 | sle_sc_v2 | 5_2_route | 9.0 | drt_violations best 71668 last 71668 rows 5 | before-window best 412199, window best 71668 | PROGRESS: drt_violations improved 82.6 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 15.1 | drt_violations best 5120 last 5120 rows 11 | before-window best 468535, window best 5120 | PROGRESS: drt_violations improved 98.9 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 17.8 | drt_violations best 1702 last 2837 rows 18 | before-window best 105054, window best 1702 | PROGRESS: drt_violations improved 98.4 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 7.9 | drt_violations best 29482 last 29482 rows 10 | before-window best 284474, window best 29482 | PROGRESS: drt_violations improved 89.6 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 32.1 | drt_violations best 13 last 13 rows 51 | before-window best 22, window best 13 | PROGRESS: drt_violations improved 40.9 % in window |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3804990 | col_h10_r0_p1__t1 | pregrt_ff_hold | 6.5 | repair_Violations best 559 last 559 rows 17 | before-window best 102530, window best 559 | PROGRESS: repair_Violations improved 99.5 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 17.5 | drt_violations best 91585 last 91585 rows 3 | before-window best 535484, window best 91585 | PROGRESS: drt_violations improved 82.9 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 14.7 | drt_violations best 470122 last 470122 rows 1 | before-window best 470122, window best 470122 | PROGRESS: drt_violations: active iteration at 224633 < best completed total 470122 (in-ite |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 19.4 | drt_violations best 393 last 397 rows 50 | before-window best 610, window best 393 | PROGRESS: drt_violations improved 35.6 % in window |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 24.9 | drt_violations best 69292 last 69292 rows 2 | before-window best 278493, window best 69292 | PROGRESS: drt_violations improved 75.1 % in window |  |
| intel2 | dpkit-coll_ftm-925629 | coll_ftm | 5_1_grt | 0.7 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
