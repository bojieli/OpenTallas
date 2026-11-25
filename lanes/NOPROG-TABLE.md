# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 15:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 7, 'GRT-LABEL': 3, 'YOUNG': 88, 'NO-DATA': 20, 'PROGRESS': 23}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc12 | otc-3501458-13012 | 3501458 | run | 11.7 | last meaningful line 11.7 h ago (1/1 lines) | NO-PROGRESS: no new non-iteration log line for 11.7 h | REPORT-ONLY: lane-own kit (abstract-exact decides; |
| epyc12 | otc-351743-16220 | 351743 | hcpg_run | 9.5 | last meaningful line 9.1 h ago (13/13 lines) | NO-PROGRESS: no new non-iteration log line for 9.1 h | REPORT-ONLY: lane-own kit (abstract-exact decides; |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3804990 | col_h10_r0_p1__t1 | pregrt_ff_hold | 5.5 | repair_TNS best 65094.3 last 65094.3 rows 1 | before-window best 65094.3, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | pregrt_ff_hold | 3.9 | repair_TNS best 116626 last 116626 rows 1 | before-window best 116626, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | pregrt_ff_hold | 6.0 | repair_TNS best 100486 last 100486 rows 1 | before-window best 100486, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 28.2 | drt_violations best 4 last 4 rows 57 | before-window best 4, window best 4 | NO-PROGRESS: drt_violations best 4 vs 4 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 26.4 | drt_violations best 1 last 1 rows 45 | before-window best 1, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_hg_v1p3__r838481cd7-1149343 | kv3_hg_v1p3__r838481cd7 | 5_1_grt | 5.5 | grt rounds 2 overflow 5:39999 -> 10:36574 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_pv_v12e-1804185 | kv3_pv_v12e | 5_1_grt | 7.3 | grt rounds 1 overflow 5:81061 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | 5_1_grt | 9.8 | grt rounds 2 overflow 5:32105 -> 10:5327 | GRT-LABEL: DESIGN-FAIL: overflow 5327 at round 10 > 1000 |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-1395551 | col_h9_r0_p5__t1 | postcts_gate_FF | 5.9 | last meaningful line 0.0 h ago (308/308 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_1_grt | 6.0 | repair_TNS best 15342.7 last 15342.7 rows 4 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | 5_2_route | 6.0 | last meaningful line 0.3 h ago (281/282 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-1130830 | col_h9_r0_p5__t1 | 5_2_route | 6.0 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc93af856-1168215 | col_h9_r0_p5__t1 | 5_2_route | 6.0 | drt_violations best 260066 last 260066 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-1072222 | col_h9_r0_p5__t1 | 5_2_route | 6.1 | last meaningful line 0.0 h ago (271/271 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Wi-2642655 | kv3_hub_Wi | tt_setup_repair | 5.2 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | prd-count-p1_bc-512241 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i3t-3678404 | eco_20261124_200101_1087713-i3t | 5_2_route | 2.7 | drt_violations best 3004 last 3004 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc12 | dpkit-bk_sel__t2-1831108 | bk_sel__t2 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (182/182 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | 4_2_tapbal_grt | 1.0 | last meaningful line 0.3 h ago (60/71 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pv_v12e-3248811 | kv3_pv_v12e | 3_3_place_gp | 1.0 | overflow best 0.0993 last 0.0993 rows 45 | YOUNG: stage 0.4 h < 1 h |  |
| epyc12 | dpkit-ot_s81sl_leaf__t70-4126904 | ot_s81sl_leaf__t70 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.7877 last 0.7877 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-sle_ctl__cla4f6f12f-254756 | sle_ctl | 4_1_cts | 3.0 | last meaningful line 0.0 h ago (11322/11322 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t22-709728 | slice_station__t22 | 5_2_route | 2.8 | drt_violations best 19079 last 19079 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t48-2631378 | slice_station__t48 | 5_2_route | 1.4 | drt_violations best 8090 last 8090 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc12 | dpkit-slice_station__t50__cl39451317-406569 | slice_station__t50 | 5_2_route | 2.9 | last meaningful line 0.1 h ago (264/265 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t6__cl0755c26e-1719577 | slice_station__t6 | 5_2_route | 2.1 | drt_violations best 15207 last 15207 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 11.6 |  | NO-DATA: no log found |  |
| epyc12 | otc-1460135-77 | 1460135 | - | 10.7 |  | NO-DATA: no log found |  |
| epyc12 | otc-167973-28965 | 167973 | flow | 5.6 | repair_Violations best 83182 last 83182 rows 146 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | postcts_gate_FF | 6.1 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 9.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 9.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 9.7 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 5_2_route | 9.5 | last meaningful line 0.2 h ago (285/286 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | pregrt_ff_hold | 4.7 | repair_TNS best 2.44591e+06 last 2.44591e+06 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-362758 | slw_hc2 | postcts_gate_TT | 4.8 | last meaningful line 0.0 h ago (361/361 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3806800 | slw_hc3 | 5_2_route | 5.1 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | otc-639211-10962 | 639211 | - | 6.2 |  | NO-DATA: no log found |  |
| epyc7 | otc-728591-15662 | 728591 | signoff | 0.8 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_215257_3586371-i1-3840527 | eco_20261125_215257_3586371-i1 | 5_2_route | 1.3 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | so_2373794_ff_69512 | so_2373794_ff_69512 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | so_2373794_tt_69512 | so_2373794_tt_69512 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-native59-2892451 | native59 | 5_1_grt | 4.3 | last meaningful line 0.3 h ago (1894/1911 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | postcts_gate_TT | 4.9 | last meaningful line 0.2 h ago (74030/74030 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v3-4131858 | sle_sc_v3 | 5_2_route | 5.2 | drt_violations best 113297 last 113297 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-287710 | slw_hc3 | 5_2_route | 5.1 | last meaningful line 0.0 h ago (259/259 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | eco-abs-1921307 | eco-abs | generate_abstract | 0.5 | last meaningful line 0.2 h ago (29/29 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | otc-1609200-26446 | 1609200 | - | 7.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-1616827-18813 | 1616827 | - | 7.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-1633866-27286 | 1633866 | - | 5.9 |  | NO-DATA: no log found |  |
| epyc8 | otc-46863-5563 | 46863 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_025941_3548303-i3-1109607 | eco_20261125_025941_3548303-i3 | 5_2_route | 0.8 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_104318_3955073-i2-1868164 | eco_20261125_104318_3955073-i2 | 5_1_grt | 0.5 | last meaningful line 0.3 h ago (290/353 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | so_2035882_ff_57817 | so_2035882_ff_57817 | generate_abstract | 0.5 | last meaningful line 0.3 h ago (35/35 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | so_2035882_tt_57817 | so_2035882_tt_57817 | generate_abstract | 0.5 | last meaningful line 0.3 h ago (35/35 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-1427167 | col_h10_r0_p1__t1 | 5_1_grt | 6.7 | last meaningful line 0.0 h ago (164/164 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvd8c0565f-1181305 | col_h10_r0_p4__t1 | tt_setup_repair_grt | 6.8 | repair_Violations best 57 last 57 rows 17 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 5_2_route | 16.5 | drt_violations best 91231 last 91231 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | tt_setup_repair_grt | 3.9 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 5.9 | last meaningful line 0.5 h ago (269/270 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 5_2_route | 7.5 | drt_violations best 176025 last 176025 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | pregrt_ff_hold | 3.4 | repair_TNS best 117151 last 117151 rows 1 | YOUNG: evidence 1.7 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv8995e794-2664422 | col_h9_r0_p5__t1 | 5_1_grt | 7.3 | repair_TNS best 66642.8 last 66642.8 rows 2 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | pregrt_ff_hold | 3.8 | repair_TNS best 85658.9 last 85658.9 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | 5_1_grt | 7.4 | last meaningful line 0.1 h ago (154/154 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 4.7 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 5.5 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 7.5 | last meaningful line 0.5 h ago (278/279 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-138946 | col_h9_r2__t1 | 5_2_route | 3.9 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 6.0 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | tt_setup_measure_grt | 4.0 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-2945122 | col_h9_r2__t1 | 5_2_route | 7.2 | drt_violations best 154176 last 154176 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | 5_2_route | 7.3 | drt_violations best 158828 last 158828 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 5_2_route | 6.8 | last meaningful line 0.6 h ago (278/279 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 6.0 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 4_1_cts | 4.4 | last meaningful line 0.2 h ago (8336/8336 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-1920080 | dsdv_slice_c3x_C__t1 | 3_5_place_dp | 5.9 | last meaningful line 1.0 h ago (38/38 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | 4_1_cts | 6.0 | last meaningful line 0.2 h ago (6279/6279 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t32-2058978 | ot_s81sl_leaf__t32 | 5_1_grt | 5.8 | last meaningful line 0.0 h ago (2064/2070 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t31-407252 | slice_station__t31 | 5_2_route | 3.9 | drt_violations best 26978 last 26978 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__clc8fb2c8c-2653854 | slice_station__t40 | 6_report | 7.3 | last meaningful line 0.0 h ago (77/77 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | so_317257_ff_59591 | so_317257_ff_59591 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | so_317257_tt_59591 | so_317257_tt_59591 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 10.4 | repair_Remaining best 119573 last 119573 rows 96 | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 5_1_grt | 10.2 | last meaningful line 0.2 h ago (269/1275 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 5_1_grt | 10.4 | last meaningful line 0.2 h ago (269/1276 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | 5_2_route | 10.4 | drt_violations best 178263 last 178263 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | 5_2_route | 10.3 | drt_violations best 159843 last 159843 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_2_route | 10.3 | drt_violations best 159806 last 159806 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_1_grt | 4.8 | last meaningful line 0.0 h ago (153/153 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-3824626 | coll_ftc | postcts_gate_TT | 4.9 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | 5_1_grt | 5.4 | last meaningful line 0.2 h ago (287/910 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-4035353 | slw_hc3 | 5_1_grt | 4.8 | last meaningful line 0.1 h ago (976/993 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | otc-2021095-31410 | 2021095 | signoff | 2.4 | last meaningful line 2.3 h ago (3/3 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | otc-2908840-11609 | 2908840 | grt_it0 | 5.2 | last meaningful line 1.5 h ago (33/34 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i3-3236766 | eco_20261123_191853_2879776-i3 | 5_1_grt | 1.8 | last meaningful line 1.0 h ago (239/1438 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1-1093733 | eco_20261125_002226_1452841-i1 | 5_2_route | 4.3 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | prd-eco_20261125_131510_2862538-i2t-2565729 | eco_20261125_131510_2862538-i2t | 5_2_route | 0.2 | last meaningful line 0.0 h ago (66/66 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | so_1238368_ff_87251 | so_1238368_ff_87251 | generate_abstract | 0.8 | last meaningful line 0.8 h ago (33/33 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | so_1238368_tt_87251 | so_1238368_tt_87251 | generate_abstract | 0.8 | last meaningful line 0.8 h ago (33/33 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | so_2163261_ff_5038 | so_2163261_ff_5038 | signoff | 0.4 |  | NO-DATA: empty log |  |
| intel1 | so_2163261_tt_5038 | so_2163261_tt_5038 | signoff | 0.4 |  | NO-DATA: empty log |  |
| intel1 | so_2316520_ff_24876 | so_2316520_ff_24876 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (36/36 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | so_2316520_tt_24876 | so_2316520_tt_24876 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (36/36 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | so_2537576_ff_94266 | so_2537576_ff_94266 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (35/35 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | so_2537576_tt_94266 | so_2537576_tt_94266 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (35/35 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | so_2604707_ff_47321 | so_2604707_ff_47321 | signoff | 0.2 |  | NO-DATA: empty log |  |
| intel1 | so_2604707_tt_47321 | so_2604707_tt_47321 | signoff | 0.2 |  | NO-DATA: empty log |  |
| intel1 | so_832543_ff_52681 | so_832543_ff_52681 | generate_abstract | 1.0 | last meaningful line 1.0 h ago (33/33 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | so_832543_tt_52681 | so_832543_tt_52681 | generate_abstract | 1.0 | last meaningful line 1.0 h ago (33/33 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | so_958946_ff_59183 | so_958946_ff_59183 | generate_abstract | 1.0 | last meaningful line 0.8 h ago (36/36 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | so_958946_tt_59183 | so_958946_tt_59183 | generate_abstract | 1.0 | last meaningful line 0.8 h ago (36/36 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-3286118 | slice_station__t12 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (200/200 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | postcts_gate_TT | 4.7 | last meaningful line 0.0 h ago (2182/2182 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | so_216061_ff_47811 | so_216061_ff_47811 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_216061_tt_47811 | so_216061_tt_47811 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 28.4 | drt_violations best 212 last 212 rows 51 | before-window best 277, window best 212 | PROGRESS: drt_violations improved 23.5 % in window |  |
| epyc12 | dpkit-native59-478901 | native59 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 13.5 | drt_violations best 1 last 1 rows 54 | before-window best 2, window best 1 | PROGRESS: drt_violations improved 50.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 13.7 | drt_violations best 78321 last 78321 rows 3 | before-window best 477402, window best 78321 | PROGRESS: drt_violations improved 83.6 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 13.7 | drt_violations best 89585 last 89585 rows 3 | before-window best 493451, window best 89585 | PROGRESS: drt_violations improved 81.8 % in window |  |
| epyc7 | dpkit-sle_sc_v2-22145 | sle_sc_v2 | 5_2_route | 8.0 | drt_violations best 113083 last 113083 rows 3 | before-window best 412199, window best 113083 | PROGRESS: drt_violations improved 72.6 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 14.1 | drt_violations best 12540 last 12540 rows 6 | before-window best 468535, window best 12540 | PROGRESS: drt_violations improved 97.3 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 16.8 | drt_violations best 2283 last 2283 rows 15 | before-window best 456468, window best 2283 | PROGRESS: drt_violations improved 99.5 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 6.9 | drt_violations best 31895 last 31895 rows 9 | before-window best 284474, window best 31895 | PROGRESS: drt_violations improved 88.8 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 31.1 | drt_violations best 13 last 13 rows 51 | before-window best 22, window best 13 | PROGRESS: drt_violations improved 40.9 % in window |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvc9270d09-1494595 | col_h10_r0_p4__t1 | tt_setup_repair_grt | 7.5 | repair_Violations best 0 last 0 rows 17 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2175059 | col_h10_r0_p4__t1 | 5_1_grt | 6.6 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-870318 | col_h9_r0_p3__t1 | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 16.5 | drt_violations best 135197 last 135197 rows 2 | before-window best 535484, window best 135197 | PROGRESS: drt_violations improved 74.8 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_1_grt | 7.5 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 13.7 | drt_violations best 470122 last 470122 rows 1 | before-window best 470122, window best 470122 | PROGRESS: drt_violations: active iteration at 275940 < best completed total 470122 (in-ite |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_1_grt | 4.5 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 18.4 | drt_violations best 411 last 411 rows 44 | before-window best 650, window best 411 | PROGRESS: drt_violations improved 36.8 % in window |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2686622 | col_h10_r0_p4__t1 | 5_1_grt | 10.4 | repair_TNS best 0 last 0 rows 20 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | pregrt_ff_hold | 10.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 23.9 | drt_violations best 69292 last 69292 rows 2 | before-window best 278493, window best 69292 | PROGRESS: drt_violations improved 75.1 % in window |  |
| intel1 | dpkit-slw_sc_v3-99093 | slw_sc_v3 | 5_1_grt | 4.7 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel2 | dpkit-kv3_io_ft-3246389 | kv3_io_ft | 5_1_grt | 0.5 | repair_TNS best 0 last 0 rows 20 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
