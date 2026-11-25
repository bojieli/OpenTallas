# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 14:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 7, 'GRT-LABEL': 3, 'NO-DATA': 12, 'YOUNG': 93, 'PROGRESS': 24}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc12 | otc-3501458-13012 | 3501458 | run | 11.2 | last meaningful line 11.2 h ago (1/1 lines) | NO-PROGRESS: no new non-iteration log line for 11.2 h | REPORT-ONLY: lane-own kit (abstract-exact decides; |
| epyc12 | otc-351743-16220 | 351743 | hcpg_run | 9.0 | last meaningful line 8.6 h ago (13/13 lines) | NO-PROGRESS: no new non-iteration log line for 8.6 h | REPORT-ONLY: lane-own kit (abstract-exact decides; |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-870318 | col_h9_r0_p3__t1 | pregrt_ff_hold | 4.5 | repair_TNS best 51108.9 last 51108.9 rows 1 | before-window best 51108.9, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 27.4 | drt_violations best 4 last 4 rows 57 | before-window best 4, window best 4 | NO-PROGRESS: drt_violations best 4 vs 4 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | pregrt_ff_hold | 9.5 | repair_TNS best 649.337 last 649.337 rows 1 | before-window best 649.337, window best 649.337 | NO-PROGRESS: repair_TNS best 649.337 vs 649.337 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | pregrt_ff_hold | 4.0 | repair_TNS best 468.21 last 468.21 rows 1 | before-window best 468.21, window best 468.21 | NO-PROGRESS: repair_TNS best 468.21 vs 468.21 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 25.6 | drt_violations best 1 last 1 rows 45 | before-window best 1, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_hg_v1p3__r838481cd7-1149343 | kv3_hg_v1p3__r838481cd7 | 5_1_grt | 4.8 | grt rounds 2 overflow 5:39999 -> 10:36574 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc12 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-3889249 | kv3_pc | 5_1_grt | 2.9 | grt rounds 2 overflow 5:6676 -> 10:3940 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_pv_v12e-1804185 | kv3_pv_v12e | 5_1_grt | 6.6 | grt rounds 1 overflow 5:81061 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | otc-976121-25594 | 976121 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-1395551 | col_h9_r0_p5__t1 | 5_1_grt | 5.1 | last meaningful line 0.3 h ago (273/1286 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_1_grt | 5.3 | repair_TNS best 18940.2 last 18940.2 rows 8 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | 5_2_route | 5.3 | last meaningful line 0.1 h ago (274/274 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-1130830 | col_h9_r0_p5__t1 | 5_2_route | 5.3 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc93af856-1168215 | col_h9_r0_p5__t1 | 5_2_route | 5.3 | last meaningful line 0.2 h ago (289/290 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-1072222 | col_h9_r0_p5__t1 | tt_setup_repair_grt | 5.3 | repair_Remaining best 103258 last 103258 rows 154 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-kv3_hub_Wi-2642655 | kv3_hub_Wi | 4_1_cts | 4.5 | last meaningful line 0.1 h ago (12276/12276 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i3t-3678404 | eco_20261124_200101_1087713-i3t | 5_2_route | 1.9 | last meaningful line 0.2 h ago (290/291 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_174711_1456062-i2-512241 | eco_20261125_174711_1456062-i2 | 5_2_route | 1.3 | last meaningful line 0.0 h ago (272/273 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc12 | dpkit-bk_sel__t2-1831108 | bk_sel__t2 | pregrt_ff_hold | 1.5 | repair_TNS best 77073.8 last 77073.8 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc12 | dpkit-hd_st_n4-3701516 | hd_st_n4 | 3_3_place_gp | 0.1 | overflow best 0.4251 last 0.4251 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-kv3_pv_v12e-3248811 | kv3_pv_v12e | 3_1_place_gp_skip_io | 0.5 | overflow best 0.7728 last 0.7728 rows 20 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-native59-478901 | native59 | pregrt_ff_hold | 2.4 | repair_TNS best 9035.23 last 9035.23 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc12 | dpkit-sle_ctl__cla4f6f12f-254756 | sle_ctl | 4_1_cts | 2.5 | last meaningful line 0.2 h ago (11301/11301 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t22-709728 | slice_station__t22 | 5_2_route | 2.3 | last meaningful line 0.2 h ago (259/260 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t28-478906 | slice_station__t28 | 6_report | 2.4 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t48-2631378 | slice_station__t48 | 5_2_route | 0.9 | last meaningful line 0.1 h ago (232/233 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t50__cl39451317-406569 | slice_station__t50 | 5_2_route | 2.4 | last meaningful line 0.2 h ago (256/257 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t6__cl0755c26e-1719577 | slice_station__t6 | 5_2_route | 1.6 | last meaningful line 0.1 h ago (250/251 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 11.1 |  | NO-DATA: no log found |  |
| epyc12 | otc-1460135-77 | 1460135 | - | 10.2 |  | NO-DATA: no log found |  |
| epyc12 | otc-167973-28965 | 167973 | flow | 5.1 | repair_Violations best 94027 last 94027 rows 129 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc2 | otc-2344331-13980 | 2344331 | - | 4.9 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 8.9 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 8.9 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 8.9 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | 5_1_grt | 9.0 | last meaningful line 0.2 h ago (296/1302 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 5_2_route | 8.8 | last meaningful line 0.1 h ago (277/278 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 13.0 | drt_violations best 121225 last 121225 rows 2 | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-22145 | sle_sc_v2 | 5_2_route | 7.2 | drt_violations best 136685 last 136685 rows 2 | YOUNG: evidence 7.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | 4_1_cts | 4.0 | last meaningful line 0.1 h ago (7265/7265 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-362758 | slw_hc2 | 5_1_grt | 4.1 | last meaningful line 0.2 h ago (288/984 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3806800 | slw_hc3 | postcts_gate_TT | 4.4 | last meaningful line 0.1 h ago (363/363 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l0__cl1a1c1f8f-3953315 | slw_su_l0 | 5_2_route | 4.3 | drt_violations best 10206 last 10206 rows 3 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 6.2 | drt_violations best 34628 last 34628 rows 7 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc7 | otc-639211-10962 | 639211 | - | 5.5 |  | NO-DATA: no log found |  |
| epyc7 | otc-728591-15662 | 728591 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_215257_3586371-i1-3840527 | eco_20261125_215257_3586371-i1 | 5_1_grt | 0.6 | last meaningful line 0.0 h ago (290/321 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-native59-2892451 | native59 | 5_1_grt | 3.6 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | tt_setup_measure_grt | 4.1 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v3-4131858 | sle_sc_v3 | 5_2_route | 4.5 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-287710 | slw_hc3 | postcts_gate_TT | 4.4 | last meaningful line 0.0 h ago (491/491 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | eco-abs-1070898 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-1609200-26446 | 1609200 | - | 6.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-1616827-18813 | 1616827 | - | 6.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-1633866-27286 | 1633866 | - | 5.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-46863-5563 | 46863 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc8 | prd-count-p1_bc-2392383 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_025941_3548303-i3-1109607 | eco_20261125_025941_3548303-i3 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_203005_2544011-i3-51023 | eco_20261125_203005_2544011-i3 | 5_2_route | 0.4 | drt_violations best 16 last 16 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | prd-fin-1439446 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3804990 | col_h10_r0_p1__t1 | pregrt_ff_hold | 4.8 | repair_TNS best 65094.3 last 65094.3 rows 1 | YOUNG: evidence 1.9 h < 2.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2175059 | col_h10_r0_p4__t1 | 5_1_grt | 5.8 | repair_Remaining best 198040 last 198040 rows 31 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 5_2_route | 15.8 | drt_violations best 91231 last 91231 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 5.2 | last meaningful line 0.3 h ago (265/266 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 5_2_route | 6.8 | last meaningful line 0.8 h ago (281/282 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-268067 | col_h9_r0_p2__t1 | 5_1_grt | 3.9 | last meaningful line 0.0 h ago (1380/1380 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | pregrt_ff_hold | 2.6 | repair_TNS best 117151 last 117151 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_1_grt | 6.8 | last meaningful line 0.0 h ago (1307/1364 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | pregrt_ff_hold | 3.2 | repair_TNS best 116626 last 116626 rows 1 | YOUNG: evidence 1.7 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 5_1_grt | 3.7 | last meaningful line 0.2 h ago (267/1276 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | pregrt_ff_hold | 5.2 | repair_TNS best 100486 last 100486 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_1_grt | 3.9 | last meaningful line 0.0 h ago (2404/2410 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 4.7 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 6.7 | last meaningful line 0.5 h ago (274/275 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-138946 | col_h9_r2__t1 | 5_1_grt | 3.2 | last meaningful line 0.1 h ago (1302/2302 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 5.2 | last meaningful line 0.1 h ago (263/263 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_1_grt | 3.2 | last meaningful line 0.1 h ago (153/153 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-2945122 | col_h9_r2__t1 | 5_2_route | 6.4 | drt_violations best 154176 last 154176 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | 5_2_route | 6.6 | drt_violations best 158828 last 158828 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 5_2_route | 6.0 | last meaningful line 0.5 h ago (274/275 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 5.3 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 4_1_cts | 3.6 | last meaningful line 0.0 h ago (8183/8183 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-1920080 | dsdv_slice_c3x_C__t1 | 3_5_place_dp | 5.1 | last meaningful line 0.3 h ago (38/38 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | 4_1_cts | 5.3 | last meaningful line 0.3 h ago (6226/6226 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t32-2058978 | ot_s81sl_leaf__t32 | 5_1_grt | 5.1 | repair_TNS best 560.816 last 560.816 rows 7 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t31-407252 | slice_station__t31 | 5_2_route | 3.1 | last meaningful line 0.2 h ago (260/261 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__clc8fb2c8c-2653854 | slice_station__t40 | 5_2_route | 6.5 | drt_violations best 18201 last 18201 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t6__cl54a9ceeb-2644120 | slice_station__t6 | 5_2_route | 5.7 | drt_violations best 57 last 57 rows 4 | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | codex-w9-c5-place-1313053 | codex-w9-c5-place | 3_3_place_gp | 0.1 | overflow best 0.683 last 0.6842 rows 3 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2686622 | col_h10_r0_p4__t1 | 5_1_grt | 9.6 | last meaningful line 0.5 h ago (1313/2359 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | 5_2_route | 9.7 | last meaningful line 0.4 h ago (278/279 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | 5_2_route | 9.5 | drt_violations best 159843 last 159843 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_2_route | 9.5 | drt_violations best 159806 last 159806 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 6_report | 21.5 | last meaningful line 0.2 h ago (69/69 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | 5_1_grt | 4.6 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-4035353 | slw_hc3 | 5_1_grt | 4.1 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v3-99093 | slw_sc_v3 | 5_1_grt | 4.0 | repair_Remaining best 253503 last 253503 rows 168 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 6_report | 23.9 | last meaningful line 0.0 h ago (74/74 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | eco-abs-643590 | eco-abs | generate_abstract | 0.4 | last meaningful line 0.3 h ago (30/30 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | otc-2021095-31410 | 2021095 | signoff | 1.6 | last meaningful line 1.5 h ago (3/3 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | otc-2908840-11609 | 2908840 | grt_it0 | 4.5 | last meaningful line 0.8 h ago (33/34 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i3-3236766 | eco_20261123_191853_2879776-i3 | 5_1_grt | 1.1 | last meaningful line 0.2 h ago (239/398 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1-1093733 | eco_20261125_002226_1452841-i1 | 5_2_route | 3.5 | last meaningful line 0.3 h ago (270/271 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | prd-eco_20261125_131510_2862538-i1-2893878 | eco_20261125_131510_2862538-i1 | 5_2_route | 1.2 | drt_violations best 148 last 148 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| intel1 | prd-fin-3642895 | fin | 6_report | 0.4 | last meaningful line 0.0 h ago (73/73 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | so_1238368_ff_87251 | so_1238368_ff_87251 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | so_1238368_tt_87251 | so_1238368_tt_87251 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | so_832543_ff_52681 | so_832543_ff_52681 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (33/33 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | so_832543_tt_52681 | so_832543_tt_52681 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (33/33 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | so_958946_ff_59183 | so_958946_ff_59183 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (36/36 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | so_958946_tt_59183 | so_958946_tt_59183 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (36/36 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-1528239 | coll_ftm | 5_2_route | 1.7 | drt_violations best 9847 last 9847 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_1_grt | 4.0 | last meaningful line 0.1 h ago (2035/2052 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 27.7 | drt_violations best 212 last 212 rows 51 | before-window best 297, window best 212 | PROGRESS: drt_violations improved 28.6 % in window |  |
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | 4_1_cts | 0.5 | repair_Violations best 0 last 0 rows 3 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | 5_1_grt | 5.3 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 12.7 | drt_violations best 1 last 1 rows 52 | before-window best 3, window best 1 | PROGRESS: drt_violations improved 66.7 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 13.0 | drt_violations best 110610 last 110610 rows 2 | before-window best 477402, window best 110610 | PROGRESS: drt_violations improved 76.8 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 13.4 | drt_violations best 77096 last 77096 rows 3 | before-window best 468535, window best 77096 | PROGRESS: drt_violations improved 83.5 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 16.1 | drt_violations best 2918 last 2918 rows 14 | before-window best 456468, window best 2918 | PROGRESS: drt_violations improved 99.4 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 30.4 | drt_violations best 13 last 13 rows 51 | before-window best 65, window best 13 | PROGRESS: drt_violations improved 80.0 % in window |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-1427167 | col_h10_r0_p1__t1 | pregrt_ff_hold | 6.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvc9270d09-1494595 | col_h10_r0_p4__t1 | 5_1_grt | 6.8 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvd8c0565f-1181305 | col_h10_r0_p4__t1 | 5_1_grt | 6.0 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_1_grt | 3.1 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 15.8 | drt_violations best 135197 last 135197 rows 2 | before-window best 535484, window best 135197 | PROGRESS: drt_violations improved 74.8 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv8995e794-2664422 | col_h9_r0_p5__t1 | 5_1_grt | 6.5 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 12.9 | drt_violations best 470122 last 470122 rows 1 | before-window best 470122, window best 470122 | PROGRESS: drt_violations: active iteration at 337347 < best completed total 470122 (in-ite |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 4_2_tapbal_grt | 3.1 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | pregrt_ff_hold | 6.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 17.6 | drt_violations best 450 last 450 rows 40 | before-window best 659, window best 450 | PROGRESS: drt_violations improved 31.7 % in window |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 9.6 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | pregrt_ff_hold | 9.5 | repair_Violations best 34563 last 34563 rows 11 | before-window best 264512, window best 34563 | PROGRESS: repair_Violations improved 86.9 % in window |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | pregrt_ff_hold | 9.6 | repair_Violations best 5641 last 5641 rows 23 | before-window best 298033, window best 5641 | PROGRESS: repair_Violations improved 98.1 % in window |  |
| intel1 | dpkit-coll_ftc-3824626 | coll_ftc | 5_1_grt | 4.1 | repair_TNS best 0 last 0 rows 21 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-hd_serdes-1497056 | hd_serdes | 4_2_tapbal_grt | 1.8 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 23.2 | drt_violations best 278493 last 278493 rows 1 | before-window best 278493, window best 278493 | PROGRESS: drt_violations: active iteration at 123189 < best completed total 278493 (in-ite |  |
