# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 15:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 7, 'GRT-LABEL': 5, 'YOUNG': 90, 'NO-DATA': 19, 'PROGRESS': 18}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc11 | dpkit-kv3_hub_Wi-2642655 | kv3_hub_Wi | tt_setup_repair | 5.7 | repair_Viol best 11506 last 11506 rows 21 | UNSIGNABLE: tt_setup_repair.log latest setup WNS -3298.84 ps (< -300, gate TT >= -42); job a | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc12 | otc-3501458-13012 | 3501458 | run | 12.4 | last meaningful line 12.4 h ago (1/1 lines) | NO-PROGRESS: no new non-iteration log line for 12.4 h | REPORT-ONLY: lane-own kit (abstract-exact decides; |
| epyc12 | otc-351743-16220 | 351743 | hcpg_run | 10.2 | last meaningful line 9.8 h ago (13/13 lines) | NO-PROGRESS: no new non-iteration log line for 9.8 h | REPORT-ONLY: lane-own kit (abstract-exact decides; |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | pregrt_ff_hold | 3.9 | repair_TNS best 117151 last 117151 rows 1 | before-window best 117151, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | pregrt_ff_hold | 4.4 | repair_TNS best 3036.46 last 3036.46 rows 1 | before-window best 3036.46, window best 3036.46 | NO-PROGRESS: repair_TNS best 3036.46 vs 3036.46 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | pregrt_ff_hold | 6.5 | repair_TNS best 8307.16 last 8307.16 rows 1 | before-window best 8307.16, window best 8307.16 | NO-PROGRESS: repair_TNS best 8307.16 vs 8307.16 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 28.7 | drt_violations best 4 last 4 rows 57 | before-window best 4, window best 4 | NO-PROGRESS: drt_violations best 4 vs 4 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 26.9 | drt_violations best 1 last 1 rows 45 | before-window best 1, window best - | NO-PROGRESS: no new drt_violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_hg_v1p3__r838481cd7-1149343 | kv3_hg_v1p3__r838481cd7 | 5_1_grt | 6.0 | grt rounds 2 overflow 5:39999 -> 10:36574 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_pv_v12e-1804185 | kv3_pv_v12e | 5_1_grt | 7.8 | grt rounds 2 overflow 5:81061 -> 10:61082 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | 5_1_grt | 10.3 | grt rounds 2 overflow 5:32105 -> 10:5327 | GRT-LABEL: DESIGN-FAIL: overflow 5327 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 5_1_grt | 10.7 | grt rounds 2 overflow 5:123883 -> 10:2244 | GRT-LABEL: DESIGN-FAIL: overflow 2244 at round 10 > 1000 |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 5_1_grt | 10.9 | grt rounds 2 overflow 5:119162 -> 10:2290 | GRT-LABEL: DESIGN-FAIL: overflow 2290 at round 10 > 1000 |  |
| epyc10 | dpkit-sle_stm_v2__cl55be2264-3753717 | sle_stm_v2 | 2_1_floorplan | 0.1 | repair_Viol best 467 last 467 rows 155 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-sle_stm_v2__cl7b3062fa-3646895 | sle_stm_v2 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (604/604 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2917583 | slw_sc_v1 | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (383/383 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-1395551 | col_h9_r0_p5__t1 | 5_2_route | 6.4 | last meaningful line 0.1 h ago (148/148 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_1_grt | 6.5 | repair_TNS best 13168.8 last 13168.8 rows 5 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | 5_2_route | 6.5 | last meaningful line 0.3 h ago (285/286 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-1130830 | col_h9_r0_p5__t1 | 5_2_route | 6.5 | last meaningful line 0.3 h ago (284/285 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc93af856-1168215 | col_h9_r0_p5__t1 | 5_2_route | 6.5 | drt_violations best 260066 last 260066 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-1072222 | col_h9_r0_p5__t1 | 5_2_route | 6.6 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | eco-abs-696646 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i3t-3678404 | eco_20261124_200101_1087713-i3t | 5_2_route | 3.2 | drt_violations best 3004 last 3004 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc12 | ap-ageom-kw-hd-lep0N-w-grt-1081860 | hd-lep0N-w-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc12 | ap-ageom-kw-kv3-pv-v12e-grt-1213664 | kv3-pv-v12e-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3276156 | col_h10_r1__t1 | tt_setup_measure | 1.7 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-gunit__t1-465395 | gunit__t1 | 5_1_grt | 0.6 | last meaningful line 0.3 h ago (261/1270 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc12 | dpkit-hd_serdes-902289 | hd_serdes | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-hd_spn_wshim_rx-1217902 | hd_spn_wshim_rx | lec | 0.0 | LEC last write -0.0 h ago | YOUNG: evidence 0.0 h < 6 h |  |
| epyc12 | dpkit-slice_station__t22-709728 | slice_station__t22 | 6_report | 3.5 | last meaningful line 0.0 h ago (77/77 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t24__cl64811a5d-1102657 | slice_station__t24 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2023/2023 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t50__cl39451317-406569 | slice_station__t50 | 5_2_route | 3.7 | drt_violations best 18328 last 18328 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t50__cld84c9e24-650458 | slice_station__t50 | pregrt_ff_hold | 0.5 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc12 | dpkit-slice_station__t6__cl0755c26e-1719577 | slice_station__t6 | 5_2_route | 2.9 | drt_violations best 15207 last 15207 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t7__cl362204c4-639423 | slice_station__t7 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 12.4 |  | NO-DATA: no log found |  |
| epyc12 | otc-1460135-77 | 1460135 | - | 11.5 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | 5_2_route | 6.6 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 10.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 10.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 10.2 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 5_2_route | 10.0 | drt_violations best 192025 last 192025 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | pregrt_ff_hold | 5.2 | repair_TNS best 2.44591e+06 last 2.44591e+06 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-362758 | slw_hc2 | postcts_gate_FF | 5.3 | last meaningful line 0.0 h ago (355/355 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3806800 | slw_hc3 | 5_2_route | 5.6 | drt_violations best 64194 last 64194 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc7 | otc-639211-10962 | 639211 | - | 6.7 |  | NO-DATA: no log found |  |
| epyc7 | otc-728591-15662 | 728591 | signoff | 1.3 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_215257_3586371-i1-3840527 | eco_20261125_215257_3586371-i1 | 5_2_route | 1.8 | drt_violations best 9 last 9 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-hd_lep0N-4038431 | hd_lep0N | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-native59-2892451 | native59 | postcts_gate_TT | 4.8 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | postcts_gate_FF | 5.4 | last meaningful line 0.1 h ago (964/964 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v3-4131858 | sle_sc_v3 | 5_2_route | 5.7 | drt_violations best 113297 last 113297 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t30__cl1653104c-560055 | slice_station__t30 | 3_3_place_gp | 0.1 | overflow best 0.2528 last 0.2546 rows 12 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-slice_station__t42__cl4bd1432c-666375 | slice_station__t42 | 3_1_place_gp_skip_io | 0.1 | last meaningful line 0.0 h ago (10/10 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-287710 | slw_hc3 | 5_2_route | 5.6 | drt_violations best 65914 last 65914 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc8 | otc-1609200-26446 | 1609200 | - | 7.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-1616827-18813 | 1616827 | - | 7.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-1633866-27286 | 1633866 | - | 6.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-46863-5563 | 46863 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_104318_3955073-i2-1868164 | eco_20261125_104318_3955073-i2 | 5_2_route | 1.0 | last meaningful line 0.0 h ago (264/265 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | so_797683_ff_7360 | so_797683_ff_7360 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | so_797683_tt_7360 | so_797683_tt_7360 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-1427167 | col_h10_r0_p1__t1 | 5_1_grt | 7.2 | last meaningful line 0.2 h ago (275/1279 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2175059 | col_h10_r0_p4__t1 | 5_1_grt | 7.1 | last meaningful line 0.1 h ago (2500/2515 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 5_2_route | 17.0 | drt_violations best 91231 last 91231 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 5_2_route | 4.4 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 6.4 | last meaningful line 0.7 h ago (271/272 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 5_2_route | 8.0 | drt_violations best 176025 last 176025 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv8995e794-2664422 | col_h9_r0_p5__t1 | 5_1_grt | 7.8 | repair_TNS best 59441 last 59441 rows 3 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | tt_setup_repair_grt | 8.0 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | tt_setup_repair_grt | 5.0 | last meaningful line 0.0 h ago (1004/1004 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | pregrt_ff_hold | 4.3 | repair_TNS best 85658.9 last 85658.9 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | 5_1_grt | 7.9 | last meaningful line 0.2 h ago (269/1277 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_2_route | 5.2 | last meaningful line 0.2 h ago (263/263 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_2_route | 6.0 | last meaningful line 0.3 h ago (268/269 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 8.0 | drt_violations best 178781 last 178781 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-138946 | col_h9_r2__t1 | 5_2_route | 4.4 | last meaningful line 0.3 h ago (264/265 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_2_route | 6.5 | last meaningful line 0.5 h ago (270/271 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 5_2_route | 4.5 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-2945122 | col_h9_r2__t1 | 5_2_route | 7.7 | drt_violations best 32173 last 32173 rows 2 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | 5_2_route | 7.8 | drt_violations best 158828 last 158828 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 5_2_route | 7.3 | drt_violations best 159056 last 159056 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 6.5 | last meaningful line 0.4 h ago (278/279 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 4_1_cts | 4.9 | last meaningful line 0.2 h ago (8445/8445 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-1920080 | dsdv_slice_c3x_C__t1 | 3_5_place_dp | 6.4 | last meaningful line 1.5 h ago (38/38 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | 4_1_cts | 6.5 | last meaningful line 0.2 h ago (6339/6339 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t32-2058978 | ot_s81sl_leaf__t32 | tt_setup_measure_grt | 6.3 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t31-407252 | slice_station__t31 | 5_2_route | 4.4 | drt_violations best 26978 last 26978 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | so_2542283_ff_75307 | so_2542283_ff_75307 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc9 | so_2542283_tt_75307 | so_2542283_tt_75307 | signoff | 0.2 |  | NO-DATA: empty log |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2686622 | col_h10_r0_p4__t1 | postcts_gate_TT | 10.9 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 5_1_grt | 10.9 | last meaningful line 0.7 h ago (1312/2420 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 5_1_grt | 10.8 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | 5_2_route | 10.9 | drt_violations best 178263 last 178263 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | 5_2_route | 10.8 | drt_violations best 159843 last 159843 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_2_route | 10.8 | drt_violations best 159806 last 159806 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | 5_1_grt | 5.3 | last meaningful line 0.0 h ago (2443/2458 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-3824626 | coll_ftc | postcts_gate_TT | 5.4 | last meaningful line 0.1 h ago (2850/2850 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | 5_1_grt | 5.9 | last meaningful line 0.1 h ago (1013/1030 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-4035353 | slw_hc3 | postcts_gate_FF | 5.3 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v3-99093 | slw_sc_v3 | 5_1_grt | 5.2 | last meaningful line 0.2 h ago (1994/2011 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | otc-2021095-31410 | 2021095 | signoff | 2.9 | last meaningful line 2.8 h ago (3/3 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | otc-2908840-11609 | 2908840 | grt_it0 | 5.7 | last meaningful line 2.0 h ago (33/34 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | otc-3338929-32249 | 3338929 | - | 0.4 |  | NO-DATA: no log found |  |
| intel1 | otc-3479258-28963 | 3479258 | - | 0.3 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261123_191853_2879776-i3-3236766 | eco_20261123_191853_2879776-i3 | 5_2_route | 2.3 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1-1093733 | eco_20261125_002226_1452841-i1 | 5_2_route | 4.8 | drt_violations best 7 last 7 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | prd-eco_20261125_131510_2862538-i2t-2565729 | eco_20261125_131510_2862538-i2t | 5_2_route | 0.7 | last meaningful line 0.1 h ago (246/247 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | so_1238368_tt_87251 | so_1238368_tt_87251 | generate_abstract | 1.3 | last meaningful line 1.3 h ago (33/33 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | so_2163261_ff_5038 | so_2163261_ff_5038 | signoff | 0.9 |  | NO-DATA: empty log |  |
| intel1 | so_2316520_ff_24876 | so_2316520_ff_24876 | generate_abstract | 0.9 | last meaningful line 0.8 h ago (36/36 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | so_2316520_tt_24876 | so_2316520_tt_24876 | generate_abstract | 0.9 | last meaningful line 0.8 h ago (36/36 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | so_2537576_ff_94266 | so_2537576_ff_94266 | generate_abstract | 0.8 | last meaningful line 0.7 h ago (35/35 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | so_2537576_tt_94266 | so_2537576_tt_94266 | generate_abstract | 0.8 | last meaningful line 0.7 h ago (35/35 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | so_2604707_ff_47321 | so_2604707_ff_47321 | signoff | 0.7 |  | NO-DATA: empty log |  |
| intel1 | so_2604707_tt_47321 | so_2604707_tt_47321 | signoff | 0.7 |  | NO-DATA: empty log |  |
| intel2 | dpkit-coll_ftm-925629 | coll_ftm | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_mesh_e-1274438 | hd_mesh_e | 5_2_route | 0.1 | drt_violations best 738 last 738 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-kv3_io_ft-3246389 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5443 last 5443 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-3286118 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 2986 last 2986 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | postcts_gate_FF | 5.2 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 28.9 | drt_violations best 212 last 212 rows 51 | before-window best 255, window best 212 | PROGRESS: drt_violations improved 16.9 % in window |  |
| epyc12 | dpkit-native59-478901 | native59 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc12 | dpkit-sle_ctl__cla4f6f12f-254756 | sle_ctl | tt_setup_repair | 3.8 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 14.0 | drt_violations best 1 last 1 rows 54 | before-window best 2, window best 1 | PROGRESS: drt_violations improved 50.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 14.2 | drt_violations best 15298 last 15298 rows 5 | before-window best 477402, window best 15298 | PROGRESS: drt_violations improved 96.8 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 14.2 | drt_violations best 89585 last 89585 rows 3 | before-window best 493451, window best 89585 | PROGRESS: drt_violations improved 81.8 % in window |  |
| epyc7 | dpkit-sle_sc_v2-22145 | sle_sc_v2 | 5_2_route | 8.5 | drt_violations best 75027 last 75027 rows 4 | before-window best 412199, window best 75027 | PROGRESS: drt_violations improved 81.8 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 14.6 | drt_violations best 8753 last 8753 rows 9 | before-window best 468535, window best 8753 | PROGRESS: drt_violations improved 98.1 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 17.3 | drt_violations best 2019 last 2019 rows 16 | before-window best 105054, window best 2019 | PROGRESS: drt_violations improved 98.1 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 7.4 | drt_violations best 29482 last 29482 rows 10 | before-window best 284474, window best 29482 | PROGRESS: drt_violations improved 89.6 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 31.6 | drt_violations best 13 last 13 rows 51 | before-window best 22, window best 13 | PROGRESS: drt_violations improved 40.9 % in window |  |
| epyc8 | prd-eco_20261125_025941_3548303-i3-1109607 | eco_20261125_025941_3548303-i3 | 5_2_route | 1.3 | drt_violations best 0 last 0 rows 1 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3804990 | col_h10_r0_p1__t1 | pregrt_ff_hold | 6.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-870318 | col_h9_r0_p3__t1 | pregrt_ff_hold | 5.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 17.0 | drt_violations best 91585 last 91585 rows 3 | before-window best 535484, window best 91585 | PROGRESS: drt_violations improved 82.9 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 14.2 | drt_violations best 470122 last 470122 rows 1 | before-window best 470122, window best 470122 | PROGRESS: drt_violations: active iteration at 275940 < best completed total 470122 (in-ite |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 18.9 | drt_violations best 400 last 400 rows 46 | before-window best 611, window best 400 | PROGRESS: drt_violations improved 34.5 % in window |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 24.4 | drt_violations best 69292 last 69292 rows 2 | before-window best 278493, window best 69292 | PROGRESS: drt_violations improved 75.1 % in window |  |
