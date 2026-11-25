# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 13:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 9, 'GRT-LABEL': 4, 'YOUNG': 102, 'NO-DATA': 18, 'PROGRESS': 17}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc12 | otc-3501458-13012 | 3501458 | run | 10.4 | last meaningful line 10.4 h ago (1/1 lines) | NO-PROGRESS: no new non-iteration log line for 10.4 h | REPORT-ONLY: lane-own kit (abstract-exact decides; |
| epyc12 | otc-351743-16220 | 351743 | hcpg_run | 8.2 | last meaningful line 7.8 h ago (13/13 lines) | NO-PROGRESS: no new non-iteration log line for 7.8 h | REPORT-ONLY: lane-own kit (abstract-exact decides; |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-1427167 | col_h10_r0_p1__t1 | pregrt_ff_hold | 5.2 | repair_TNS best 37858.4 last 37858.4 rows 1 | before-window best 37858.4, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 26.7 | drt_violations best 4 last 4 rows 57 | before-window best 4, window best 4 | NO-PROGRESS: drt_violations best 4 vs 4 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | pregrt_ff_hold | 8.8 | repair_TNS best 50339.8 last 50339.8 rows 1 | before-window best 50339.8, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | pregrt_ff_hold | 8.7 | repair_TNS best 2929.43 last 2929.43 rows 1 | before-window best 2929.43, window best 2929.43 | NO-PROGRESS: repair_TNS best 2929.43 vs 2929.43 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | pregrt_ff_hold | 8.9 | repair_TNS best 4086.05 last 4086.05 rows 1 | before-window best 4086.05, window best 4086.05 | NO-PROGRESS: repair_TNS best 4086.05 vs 4086.05 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | pregrt_ff_hold | 3.3 | repair_TNS best 12785.1 last 12785.1 rows 1 | before-window best 12785.1, window best 12785.1 | NO-PROGRESS: repair_TNS best 12785.1 vs 12785.1 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 24.9 | drt_violations best 1 last 1 rows 45 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_hg_v1p3__r838481cd7-1149343 | kv3_hg_v1p3__r838481cd7 | 5_1_grt | 4.0 | grt rounds 2 overflow 5:39999 -> 10:36574 | GRT-LABEL: DESIGN-FAIL: overflow 36574 at round 10 > 1000 |  |
| epyc12 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-3889249 | kv3_pc | 5_1_grt | 2.1 | grt rounds 2 overflow 5:6676 -> 10:3940 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_pv_v12e-1804185 | kv3_pv_v12e | 5_1_grt | 5.8 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t11-1456626 | ot_s81sl_leaf__t11 | 5_1_grt | 2.1 | grt rounds 2 overflow 5:10852 -> 10:3546 | GRT-LABEL: DESIGN-FAIL: overflow 3546 at round 10 > 1000 |  |
| epyc10 | dpkit-sle_su_c-3015576 | sle_su_c | 3_1_place_gp_skip_io | 0.4 | overflow best 0.1131 last 0.1131 rows 49 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-3029117 | slw_su_c | 3_3_place_gp | 0.3 | overflow best 0.3845 last 0.3845 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | so_3355562_ff_43366 | so_3355562_ff_43366 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (33/33 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | so_3355562_tt_43366 | so_3355562_tt_43366 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (33/33 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-1395551 | col_h9_r0_p5__t1 | 5_1_grt | 4.4 | repair_Remaining best 192309 last 192309 rows 93 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_1_grt | 4.5 | repair_TNS best 23746.8 last 23746.8 rows 11 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | 5_1_grt | 4.5 | last meaningful line 0.0 h ago (2520/2526 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc93af856-1168215 | col_h9_r0_p5__t1 | 5_2_route | 4.5 | last meaningful line 0.3 h ago (281/282 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-1072222 | col_h9_r0_p5__t1 | 5_1_grt | 4.6 | last meaningful line 0.0 h ago (161/161 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Wi-2642655 | kv3_hub_Wi | 4_1_cts | 3.7 | last meaningful line 0.3 h ago (11969/11969 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc11 | otc-1616228-26288 | 1616228 | - | 8.1 |  | NO-DATA: no log found |  |
| epyc11 | prd-eco_20261124_200101_1087713-i3t-3678404 | eco_20261124_200101_1087713-i3t | 5_2_route | 1.2 | last meaningful line 0.1 h ago (277/277 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_174711_1456062-i2-512241 | eco_20261125_174711_1456062-i2 | 5_1_grt | 0.6 | last meaningful line 0.1 h ago (294/329 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | prd-eco_retry_1795638640553422888-i1-3577989 | eco_retry_1795638640553422888-i1 | 5_2_route | 1.2 | last meaningful line 0.1 h ago (266/267 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc12 | ap-ageom-kw-kv3-hgi-v6-grt-2697020 | kv3-hgi-v6-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc12 | dpkit-bk_sel__t2-1831108 | bk_sel__t2 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (6324/6324 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc12 | dpkit-native59-478901 | native59 | pregrt_ff_hold | 1.6 | repair_TNS best 9035.23 last 9035.23 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc12 | dpkit-sle_ctl__cla4f6f12f-254756 | sle_ctl | 4_1_cts | 1.8 | last meaningful line 0.2 h ago (11238/11238 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t21-1090377 | slice_station__t21 | 5_2_route | 1.3 | drt_violations best 8531 last 8531 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc12 | dpkit-slice_station__t22-709728 | slice_station__t22 | 5_2_route | 1.5 | last meaningful line 0.0 h ago (244/244 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t28-478906 | slice_station__t28 | 5_2_route | 1.6 | drt_violations best 15234 last 15234 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc12 | dpkit-slice_station__t48-2631378 | slice_station__t48 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t50__cl39451317-406569 | slice_station__t50 | 5_2_route | 1.7 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t6__cl0755c26e-1719577 | slice_station__t6 | tt_setup_repair_grt | 0.9 | last meaningful line 0.0 h ago (200/200 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t7__cl503f4913-1636821 | slice_station__t7 | 5_2_route | 0.9 | drt_violations best 4294 last 4294 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 10.4 |  | NO-DATA: no log found |  |
| epyc12 | otc-1460135-77 | 1460135 | - | 9.5 |  | NO-DATA: no log found |  |
| epyc12 | otc-167973-28965 | 167973 | flow | 4.3 | repair_Violations best 135908 last 135908 rows 106 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | 5_1_grt | 4.6 | last meaningful line 0.0 h ago (2009/2023 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | otc-2344331-13980 | 2344331 | - | 4.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 8.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 8.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 8.2 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-coll_s-1906595 | coll_s | 5_2_route | 4.3 | drt_violations best 51 last 51 rows 12 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | 5_1_grt | 8.3 | last meaningful line 0.0 h ago (164/164 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 5_2_route | 8.0 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 12.2 | drt_violations best 477402 last 477402 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 12.2 | drt_violations best 493451 last 493451 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-22145 | sle_sc_v2 | 5_2_route | 6.5 | drt_violations best 412199 last 412199 rows 1 | YOUNG: evidence 6.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | 4_1_cts | 3.2 | last meaningful line 0.2 h ago (7258/7258 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-362758 | slw_hc2 | pregrt_ff_hold | 3.3 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.3 h < 2.5 h |  |
| epyc7 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3806800 | slw_hc3 | 5_1_grt | 3.6 | last meaningful line 0.0 h ago (969/975 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 12.6 | drt_violations best 105509 last 105509 rows 2 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l0__cl1a1c1f8f-3953315 | slw_su_l0 | 5_2_route | 3.6 | drt_violations best 82528 last 82528 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 5.4 | drt_violations best 36694 last 36694 rows 6 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc7 | otc-639211-10962 | 639211 | - | 4.7 |  | NO-DATA: no log found |  |
| epyc7 | so_2090550_ff_61411 | so_2090550_ff_61411 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc7 | so_2090550_tt_61411 | so_2090550_tt_61411 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc7 | so_3453901_ff_7618 | so_3453901_ff_7618 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | so_3453901_tt_7618 | so_3453901_tt_7618 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-native59-2892451 | native59 | pregrt_ff_hold | 2.8 | repair_TNS best 9465.21 last 9465.21 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 5_1_grt | 3.4 | last meaningful line 0.3 h ago (1291/1938 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v3-4131858 | sle_sc_v3 | postcts_gate_FF | 3.7 | last meaningful line -0.0 h ago (15208/15208 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-287710 | slw_hc3 | 5_1_grt | 3.6 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | otc-1467259-21054 | 1467259 | - | 3.3 |  | NO-DATA: no log found |  |
| epyc8 | otc-1609200-26446 | 1609200 | - | 5.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-1616827-18813 | 1616827 | - | 5.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-1633866-27286 | 1633866 | - | 4.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-3569473-6282 | 3569473 | - | 5.0 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_025941_3548303-i3t-2012963 | eco_20261125_025941_3548303-i3t | 5_2_route | 1.7 | drt_violations best 82 last 82 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc8 | prd-eco_20261125_104318_3955073-i2t-2392383 | eco_20261125_104318_3955073-i2t | 5_2_route | 1.6 | drt_violations best 147 last 147 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | prd-eco_20261125_122258_3982108-i2-1278157 | eco_20261125_122258_3982108-i2 | 5_2_route | 2.0 | last meaningful line 0.1 h ago (282/283 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_182230_4100536-i1-1439446 | eco_20261125_182230_4100536-i1 | 5_2_route | 3.3 | drt_violations best 45 last 45 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_203005_2544011-i2-1988887 | eco_20261125_203005_2544011-i2 | 5_2_route | 0.4 | last meaningful line 0.0 h ago (244/245 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | so_1945911_ff_80596 | so_1945911_ff_80596 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (33/33 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | so_1945911_tt_80596 | so_1945911_tt_80596 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (33/33 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3804990 | col_h10_r0_p1__t1 | pregrt_ff_hold | 4.0 | repair_TNS best 65094.3 last 65094.3 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvc9270d09-1494595 | col_h10_r0_p4__t1 | 5_1_grt | 6.0 | repair_Remaining best 124487 last 124487 rows 102 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2175059 | col_h10_r0_p4__t1 | 5_1_grt | 5.1 | last meaningful line 0.1 h ago (161/161 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvd8c0565f-1181305 | col_h10_r0_p4__t1 | 5_1_grt | 5.3 | last meaningful line 0.2 h ago (1312/1373 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 5_2_route | 15.0 | drt_violations best 91231 last 91231 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | pregrt_ff_hold | 2.4 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 1.7 h < 2.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_2_route | 4.4 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 5_2_route | 6.0 | last meaningful line 0.1 h ago (279/280 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-268067 | col_h9_r0_p2__t1 | 5_1_grt | 3.2 | last meaningful line 0.0 h ago (274/276 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-870318 | col_h9_r0_p3__t1 | pregrt_ff_hold | 3.8 | repair_TNS best 51108.9 last 51108.9 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 117151 last 117151 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 5_1_grt | 6.0 | last meaningful line 0.1 h ago (157/157 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.4 | repair_TNS best 116626 last 116626 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 12.2 | drt_violations best 470122 last 470122 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | pregrt_ff_hold | 4.5 | repair_TNS best 100486 last 100486 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.3 | last meaningful line 1.5 h ago (61/86 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | pregrt_ff_hold | 5.9 | repair_TNS best 48858.5 last 48858.5 rows 1 | YOUNG: evidence 1.9 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 5_1_grt | 3.2 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 6.0 | last meaningful line 0.5 h ago (270/271 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | postcts_gate_TT | 4.5 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-2945122 | col_h9_r2__t1 | 5_2_route | 5.7 | drt_violations best 154176 last 154176 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | 5_2_route | 5.8 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 5_2_route | 5.3 | last meaningful line 0.5 h ago (270/271 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_2_route | 4.5 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | 4_1_cts | 2.9 | last meaningful line 0.2 h ago (42/42 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-1920080 | dsdv_slice_c3x_C__t1 | 3_3_place_gp | 4.4 | overflow best 0.443 last 0.443 rows 58 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | 4_1_cts | 4.5 | last meaningful line 0.1 h ago (6137/6137 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t32-2058978 | ot_s81sl_leaf__t32 | 5_1_grt | 4.3 | repair_Remaining best 72748 last 72748 rows 229 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t31-407252 | slice_station__t31 | 5_2_route | 2.4 | last meaningful line 0.2 h ago (250/251 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__clc8fb2c8c-2653854 | slice_station__t40 | 5_2_route | 5.8 | drt_violations best 18201 last 18201 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t6__cl54a9ceeb-2644120 | slice_station__t6 | 5_2_route | 5.0 | drt_violations best 20110 last 20110 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2686622 | col_h10_r0_p4__t1 | 5_1_grt | 8.9 | last meaningful line 0.5 h ago (273/1282 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | 5_2_route | 8.9 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | 5_2_route | 8.8 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_2_route | 8.8 | last meaningful line 0.5 h ago (278/279 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-3824626 | coll_ftc | 5_1_grt | 3.4 | last meaningful line 0.1 h ago (136/136 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-hd_serdes-1497056 | hd_serdes | 4_2_tapbal_grt | 1.1 | last meaningful line 0.3 h ago (49/86 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | tt_setup_repair | 3.9 | repair_Remaining best 261484 last 261484 rows 117 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-4035353 | slw_hc3 | pregrt_ff_hold | 3.3 | repair_TNS best 259833 last 259833 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-slw_sc_v3-99093 | slw_sc_v3 | 5_1_grt | 3.2 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | eco-abs-3535570 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.1 h ago (30/30 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-2021095-31410 | 2021095 | signoff | 0.9 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | otc-2908840-11609 | 2908840 | grt_it0 | 3.7 | last meaningful line 0.1 h ago (31/32 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i3-3236766 | eco_20261123_191853_2879776-i3 | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1-1093733 | eco_20261125_002226_1452841-i1 | 5_2_route | 2.8 | last meaningful line 0.0 h ago (265/265 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | prd-eco_20261125_131510_2862538-i1-2893878 | eco_20261125_131510_2862538-i1 | 5_2_route | 0.5 | last meaningful line 0.1 h ago (230/230 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-fin-2873810 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-fin-3109373 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-fin-527377 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-1528239 | coll_ftm | 5_2_route | 1.0 | last meaningful line 0.0 h ago (225/225 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_host_w-317037 | hd_host_w | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (199/199 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-hd_mesh-281389 | hd_mesh | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (303/303 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-hd_spn_wshim_rx-253185 | hd_spn_wshim_rx | 2_4_floorplan_pdn | 0.0 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 5_1_grt | 3.2 | last meaningful line 0.3 h ago (1303/1942 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 26.9 | drt_violations best 214 last 214 rows 50 | before-window best 368, window best 214 | PROGRESS: drt_violations improved 41.8 % in window |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-1130830 | col_h9_r0_p5__t1 | 5_1_grt | 4.5 | repair_TNS best 0 last 0 rows 4 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 12.0 | drt_violations best 1 last 1 rows 50 | before-window best 5, window best 1 | PROGRESS: drt_violations improved 80.0 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 15.3 | drt_violations best 4512 last 4512 rows 12 | before-window best 456468, window best 4512 | PROGRESS: drt_violations improved 99.0 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 29.6 | drt_violations best 13 last 13 rows 51 | before-window best 136, window best 13 | PROGRESS: drt_violations improved 90.4 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 15.0 | drt_violations best 135197 last 135197 rows 2 | before-window best 535484, window best 135197 | PROGRESS: drt_violations improved 74.8 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv8995e794-2664422 | col_h9_r0_p5__t1 | pregrt_ff_hold | 5.8 | repair_Violations best 128115 last 128115 rows 4 | before-window best 326580, window best 128115 | PROGRESS: repair_Violations improved 60.8 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 5_1_grt | 4.0 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-138946 | col_h9_r2__t1 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 16.9 | drt_violations best 454 last 454 rows 37 | before-window best 1090, window best 454 | PROGRESS: drt_violations improved 58.3 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | pregrt_ff_hold | 8.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 5_2_route | 20.7 | drt_violations best 11953 last 11953 rows 3 | before-window best 147106, window best 11953 | PROGRESS: drt_violations improved 91.9 % in window |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 22.4 | drt_violations best 278493 last 278493 rows 1 | before-window best 278493, window best 278493 | PROGRESS: drt_violations: active iteration at 169586 < best completed total 278493 (in-ite |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 5_2_route | 23.2 | drt_violations best 13257 last 13257 rows 3 | before-window best 131284, window best 13257 | PROGRESS: drt_violations improved 89.9 % in window |  |
| intel1 | prd-eco_20261125_070347_2847958-i1-3642895 | eco_20261125_070347_2847958-i1 | 5_2_route | 6.6 | drt_violations best 0 last 0 rows 2 | PROGRESS: drt_violations reached 0 |  |
