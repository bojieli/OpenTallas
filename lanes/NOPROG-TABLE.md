# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 12:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 8, 'GRT-LABEL': 2, 'YOUNG': 114, 'NO-DATA': 21, 'PROGRESS': 22}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc12 | otc-351743-16220 | 351743 | hcpg_run | 7.2 | last meaningful line 6.8 h ago (13/13 lines) | NO-PROGRESS: no new non-iteration log line for 6.8 h | REPORT-ONLY: lane-own kit (abstract-exact decides; |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2175059 | col_h10_r0_p4__t1 | pregrt_ff_hold | 4.1 | repair_TNS best 53228.6 last 53228.6 rows 1 | before-window best 53228.6, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv8995e794-2664422 | col_h9_r0_p5__t1 | pregrt_ff_hold | 4.8 | repair_TNS best 19790.6 last 19790.6 rows 1 | before-window best 19790.6, window best 19790.6 | NO-PROGRESS: repair_TNS best 19790.6 vs 19790.6 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 25.7 | drt_violations best 4 last 4 rows 57 | before-window best 4, window best 4 | NO-PROGRESS: drt_violations best 4 vs 4 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | pregrt_ff_hold | 7.9 | repair_TNS best 385.164 last 385.164 rows 1 | before-window best 385.164, window best 385.164 | NO-PROGRESS: repair_TNS best 385.164 vs 385.164 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | pregrt_ff_hold | 7.7 | repair_TNS best 80867.4 last 80867.4 rows 1 | before-window best 80867.4, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | pregrt_ff_hold | 7.9 | repair_TNS best 86468.6 last 86468.6 rows 1 | before-window best 86468.6, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 23.9 | drt_violations best 1 last 1 rows 45 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_hg_v1p3__r838481cd7-1149343 | kv3_hg_v1p3__r838481cd7 | 5_1_grt | 3.0 | grt rounds 2 overflow 5:39999 -> 10:36574 | GRT-LABEL: DESIGN-FAIL: overflow 36574 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_hg_v1p5-1187885 | kv3_hg_v1p5 | 5_1_grt | 3.0 | grt rounds 2 overflow 5:49289 -> 10:42235 | GRT-LABEL: DESIGN-FAIL: overflow 42235 at round 10 > 1000 |  |
| epyc10 | prd-fin-1643366 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-1395551 | col_h9_r0_p5__t1 | 5_1_grt | 3.4 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_1_grt | 3.5 | last meaningful line 0.2 h ago (271/1286 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | 5_1_grt | 3.5 | last meaningful line 0.0 h ago (162/162 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-1130830 | col_h9_r0_p5__t1 | 5_1_grt | 3.5 | repair_Remaining best 168222 last 168222 rows 86 | YOUNG: stage 0.7 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc93af856-1168215 | col_h9_r0_p5__t1 | postcts_gate_FF | 3.5 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Eo-1420436 | kv3_hub_Eo | 5_1_grt | 5.2 | repair_Viol best 87 last 87 rows 19 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Wi-2642655 | kv3_hub_Wi | 4_1_cts | 2.7 | last meaningful line 0.0 h ago (11890/11890 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc11 | otc-1616228-26288 | 1616228 | - | 7.1 |  | NO-DATA: no log found |  |
| epyc11 | prd-eco_20261124_200101_1087713-i3t-3678404 | eco_20261124_200101_1087713-i3t | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | prd-eco_retry_1795638640553422888-i1-3577989 | eco_retry_1795638640553422888-i1 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | so_3801569_ff_39973 | so_3801569_ff_39973 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (35/35 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | so_3801569_tt_39973 | so_3801569_tt_39973 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (35/35 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-gunit__t1-327777 | gunit__t1 | 3_5_place_dp | 0.7 | last meaningful line 0.3 h ago (39/39 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc12 | dpkit-kv3_hg_v1p5-1290843 | kv3_hg_v1p5 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (526/526 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-kv3_hgi_v2__cle0015330-1168489 | kv3_hgi_v2 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.147 last 0.147 rows 38 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-3889249 | kv3_pc | pregrt_ff_hold | 1.1 | last meaningful line 0.0 h ago (78/78 lines) | YOUNG: evidence 0.3 h < 2.5 h |  |
| epyc12 | dpkit-native59-478901 | native59 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (5583/5583 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc12 | dpkit-sle_ctl__cla4f6f12f-254756 | sle_ctl | 4_1_cts | 0.8 | last meaningful line 0.2 h ago (11120/11120 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t21-1090377 | slice_station__t21 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (509/527 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t22-709728 | slice_station__t22 | 5_1_grt | 0.5 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t28-478906 | slice_station__t28 | postcts_gate_FF | 0.6 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t48-1463399 | slice_station__t48 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t50__cl39451317-406569 | slice_station__t50 | 5_1_grt | 0.7 | repair_Remaining best 145828 last 145828 rows 71 | YOUNG: stage 0.2 h < 1 h |  |
| epyc12 | dpkit-slice_station__t50__cld84c9e24-1340513 | slice_station__t50 | 3_3_place_gp | 0.1 | overflow best 0.2346 last 0.2354 rows 6 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-slice_station__t6__cl0755c26e-1163211 | slice_station__t6 | 3_5_place_dp | 0.2 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 9.4 |  | NO-DATA: no log found |  |
| epyc12 | otc-1087770-15013 | 1087770 | asbuilt.yosys | 0.3 | last meaningful line 0.0 h ago (229432/229432 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | otc-1096617-27639 | 1096617 | asbuilt.yosys | 0.3 | last meaningful line 0.0 h ago (229432/229432 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | otc-1267541-535 | 1267541 | grt_it0 | 2.8 | last meaningful line 0.3 h ago (31/32 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc12 | otc-1460135-77 | 1460135 | - | 8.5 |  | NO-DATA: no log found |  |
| epyc12 | otc-167973-28965 | 167973 | flow | 3.3 | repair_Violations best 166966 last 166966 rows 71 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | cranky_ganguly | cranky_ganguly | drc | 2.2 | last meaningful line 2.0 h ago (132/132 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | 5_1_grt | 3.6 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t28-3987037 | slice_station__t28 | 2_4_floorplan_pdn | 0.0 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | nifty_lalande | nifty_lalande | drc | 1.8 | last meaningful line 1.8 h ago (129/129 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | optimistic_feynman | optimistic_feynman | drc | 1.9 | last meaningful line 1.8 h ago (132/132 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | otc-2344331-13980 | 2344331 | - | 3.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 7.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 7.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 7.2 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbf_q00_s2-1045407 | cbf_q00_s2 | tt_setup_repair_grt | 5.1 | repair_Violations best 12 last 12 rows 53 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc7 | dpkit-coll_ftm-2399818 | coll_ftm | 5_2_route | 3.1 | drt_violations best 14690 last 14690 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-coll_s-1906595 | coll_s | 5_2_route | 3.3 | drt_violations best 43756 last 43756 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12e-1804185 | kv3_pv_v12e | 4_1_cts | 4.8 | last meaningful line 0.1 h ago (12453/12453 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | pregrt_ff_hold | 7.3 | repair_TNS best 298453 last 298453 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | tt_setup_repair_grt | 7.0 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | 6_report | 14.4 | last meaningful line 0.2 h ago (68/68 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 11.2 | drt_violations best 477402 last 477402 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 11.2 | drt_violations best 493451 last 493451 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-22145 | sle_sc_v2 | 5_2_route | 5.5 | drt_violations best 412199 last 412199 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | 4_1_cts | 2.2 | last meaningful line 0.1 h ago (7201/7201 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-362758 | slw_hc2 | 4_1_cts | 2.3 | last meaningful line 0.1 h ago (5325/5325 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3806800 | slw_hc3 | pregrt_ff_hold | 2.6 | repair_TNS best 250989 last 250989 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 11.6 | drt_violations best 468535 last 468535 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l0__cl1a1c1f8f-3953315 | slw_su_l0 | 5_2_route | 2.6 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 4.4 | drt_violations best 44762 last 44762 rows 4 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | otc-2938337-22499 | 2938337 | - | 7.7 |  | NO-DATA: no log found |  |
| epyc7 | otc-3693543-29719 | 3693543 | - | 4.1 |  | NO-DATA: no log found |  |
| epyc7 | otc-639211-10962 | 639211 | - | 3.7 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | pregrt_ff_hold | 2.4 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc8 | dpkit-sle_sc_v3-4131858 | sle_sc_v3 | postcts_gate_TT | 2.7 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-287710 | slw_hc3 | 4_1_cts | 2.6 | last meaningful line 0.1 h ago (7194/7194 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-tt_ctlm-548365 | tt_ctlm | tt_setup_measure_grt | 2.5 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-132122-8685 | 132122 | - | 8.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-1467259-21054 | 1467259 | - | 2.3 |  | NO-DATA: no log found |  |
| epyc8 | otc-1609200-26446 | 1609200 | - | 4.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-1616827-18813 | 1616827 | - | 4.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-1633866-27286 | 1633866 | - | 3.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-192475-3213 | 192475 | - | 2.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-3569473-6282 | 3569473 | - | 4.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-3579536-7216 | 3579536 | - | 3.9 |  | NO-DATA: no log found |  |
| epyc8 | prd-count-p1_bc-1265285 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_025941_3548303-i3t-2012963 | eco_20261125_025941_3548303-i3t | 5_1_grt | 0.7 | last meaningful line 0.3 h ago (292/504 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_104318_3955073-i2t-2392383 | eco_20261125_104318_3955073-i2t | 5_1_grt | 0.6 | last meaningful line 0.1 h ago (288/387 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_122258_3982108-i2-1278157 | eco_20261125_122258_3982108-i2 | 5_2_route | 1.0 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_182230_4100536-i1-1439446 | eco_20261125_182230_4100536-i1 | 5_2_route | 2.3 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_203005_2544011-i1-3615701 | eco_20261125_203005_2544011-i1 | 5_2_route | 0.2 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3804990 | col_h10_r0_p1__t1 | pregrt_ff_hold | 3.0 | repair_TNS best 65094.3 last 65094.3 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-1427167 | col_h10_r0_p1__t1 | pregrt_ff_hold | 4.2 | repair_TNS best 37858.4 last 37858.4 rows 1 | YOUNG: evidence 1.5 h < 2.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvc9270d09-1494595 | col_h10_r0_p4__t1 | 5_1_grt | 5.0 | last meaningful line 0.0 h ago (157/157 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 5_2_route | 14.0 | drt_violations best 91231 last 91231 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 57363.5 last 57363.5 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_1_grt | 3.4 | last meaningful line 0.1 h ago (1297/2227 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 5_2_route | 5.0 | last meaningful line 0.5 h ago (271/272 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-870318 | col_h9_r0_p3__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 51108.9 last 51108.9 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | 4_2_tapbal_grt | 0.9 | last meaningful line 0.1 h ago (62/69 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 11.2 | drt_violations best 470122 last 470122 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 60506.6 last 60506.6 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.3 | last meaningful line 0.5 h ago (61/75 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | pregrt_ff_hold | 4.9 | repair_TNS best 48858.5 last 48858.5 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | pregrt_ff_hold | 2.2 | repair_TNS best 62577.4 last 62577.4 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 5.0 | last meaningful line 0.3 h ago (264/265 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-138946 | col_h9_r2__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 22910.6 last 22910.6 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 5_1_grt | 3.5 | last meaningful line 0.1 h ago (152/152 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 64056.3 last 64056.3 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-2945122 | col_h9_r2__t1 | 5_2_route | 4.7 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | 5_2_route | 4.8 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 5_2_route | 4.3 | last meaningful line 0.3 h ago (264/265 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_1_grt | 3.5 | last meaningful line 0.2 h ago (1304/2357 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | selrange | 1.9 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-1920080 | dsdv_slice_c3x_C__t1 | 3_1_place_gp_skip_io | 3.4 | overflow best 0.7814 last 0.7814 rows 27 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2186209 | dsdv_slice_lepe_nh_mus_LP__t1 | postcts_gate_FF | 4.9 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | 4_1_cts | 3.5 | last meaningful line 0.0 h ago (5842/5842 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t11-1456626 | ot_s81sl_leaf__t11 | 5_1_grt | 1.1 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t32-2058978 | ot_s81sl_leaf__t32 | 5_1_grt | 3.3 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t31-407252 | slice_station__t31 | postcts_gate_TT | 1.4 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__clc8fb2c8c-2653854 | slice_station__t40 | 5_2_route | 4.8 | drt_violations best 18201 last 18201 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t6__cl54a9ceeb-2644120 | slice_station__t6 | 5_2_route | 4.0 | drt_violations best 20110 last 20110 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2686622 | col_h10_r0_p4__t1 | 5_1_grt | 7.9 | last meaningful line 0.0 h ago (98/98 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | pregrt_ff_hold | 7.8 | repair_TNS best 50339.8 last 50339.8 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | 5_2_route | 7.9 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | 5_2_route | 7.8 | last meaningful line 0.5 h ago (268/269 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_2_route | 7.8 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 118766 last 118766 rows 1 | YOUNG: evidence 2.3 h < 2.5 h |  |
| intel1 | dpkit-coll_ftc-3824626 | coll_ftc | 4_1_cts | 2.4 | last meaningful line 0.0 h ago (6313/6313 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-coll_n-2865002 | coll_n | 5_2_route | 2.7 | drt_violations best 1907 last 1907 rows 2 | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-hd_serdes-1497056 | hd_serdes | synth_odb_v | 0.1 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-hd_spn-1381962 | hd_spn | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2356/2357 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-hd_spn_end-1256266 | hd_spn_end | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3071/3071 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | 4_1_cts | 2.9 | last meaningful line 0.3 h ago (5338/5338 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-4035353 | slw_hc3 | 4_1_cts | 2.3 | last meaningful line 0.0 h ago (6691/6691 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v3-99093 | slw_sc_v3 | 4_1_cts | 2.2 | last meaningful line 0.0 h ago (5595/5595 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | otc-2908840-11609 | 2908840 | flow | 2.7 | last meaningful line 0.0 h ago (4330/4330 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | prd-count-p1_bc-2681077 | count-p1_bc | prd_count_p1_bc | 0.1 | last meaningful line 0.0 h ago (861/861 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1-1093733 | eco_20261125_002226_1452841-i1 | 5_1_grt | 1.8 | last meaningful line 0.8 h ago (296/363 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | prd-eco_20261125_070347_2847958-i1-3642895 | eco_20261125_070347_2847958-i1 | 5_2_route | 5.6 | drt_violations best 2 last 2 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | prd-eco_20261125_072849_2847456-i1-527377 | eco_20261125_072849_2847456-i1 | 5_2_route | 5.2 | drt_violations best 30 last 30 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | prd-eco_20261125_082621_46745-i1-2873810 | eco_20261125_082621_46745-i1 | 5_2_route | 4.3 | drt_violations best 4 last 4 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | so_2200105_ff_6493 | so_2200105_ff_6493 | signoff | 1.4 |  | NO-DATA: empty log |  |
| intel1 | so_2200105_tt_6493 | so_2200105_tt_6493 | signoff | 1.4 |  | NO-DATA: empty log |  |
| intel2 | dpkit-kv3_io_ft-2159590 | kv3_io_ft | 5_2_route | 1.2 | drt_violations best 5443 last 5443 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-sle_ctl__cla4f6f12f-1437376 | sle_ctl | 3_4_place_resized | 1.5 | last meaningful line 0.1 h ago (435/435 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-3663167 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (225/226 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | pregrt_ff_hold | 2.2 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.1 h < 2.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 25.9 | drt_violations best 228 last 228 rows 46 | before-window best 620, window best 228 | PROGRESS: drt_violations improved 63.2 % in window |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-1072222 | col_h9_r0_p5__t1 | 5_1_grt | 3.6 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-973347 | col_h10_r1__t1 | 3_5_place_dp | 0.4 | repair_Violations best 0 last 0 rows 45 | PROGRESS: repair_Violations reached 0 |  |
| epyc12 | otc-3501458-13012 | 3501458 | drc_macros_only | 9.4 | last meaningful line 1.0 h ago (670/670 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 11.0 | drt_violations best 1 last 1 rows 50 | before-window best 2904, window best 1 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 14.3 | drt_violations best 10277 last 10277 rows 9 | before-window best 456468, window best 10277 | PROGRESS: drt_violations improved 97.7 % in window |  |
| epyc8 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-918588 | col_h10_r0_p1__t1 | 5_1_grt | 8.5 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc8 | dpkit-native59-2892451 | native59 | tt_setup_repair | 1.8 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 28.6 | drt_violations best 14 last 14 rows 48 | before-window best 360, window best 14 | PROGRESS: drt_violations improved 96.1 % in window |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvd8c0565f-1181305 | col_h10_r0_p4__t1 | pregrt_ff_hold | 4.3 | repair_Violations best 0 last 0 rows 19 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-268067 | col_h9_r0_p2__t1 | 4_2_tapbal_grt | 2.2 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 14.0 | drt_violations best 535484 last 535484 rows 1 | before-window best 535484, window best 535484 | PROGRESS: drt_violations: active iteration at 223041 < best completed total 535484 (in-ite |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | tt_setup_repair | 1.4 | repair_Violations best 0 last 0 rows 15 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 4_2_tapbal_grt | 3.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | pregrt_ff_hold | 3.0 | repair_Violations best 73742 last 73742 rows 11 | before-window best 355070, window best 73742 | PROGRESS: repair_Violations improved 79.2 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 15.9 | drt_violations best 530 last 530 rows 32 | before-window best 2540, window best 530 | PROGRESS: drt_violations improved 79.1 % in window |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 5_2_route | 19.7 | drt_violations best 18263 last 18263 rows 2 | before-window best 147106, window best 18263 | PROGRESS: drt_violations improved 87.6 % in window |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 21.4 | drt_violations best 278493 last 278493 rows 1 | before-window best 278493, window best 278493 | PROGRESS: drt_violations: active iteration at 227021 < best completed total 278493 (in-ite |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 5_2_route | 22.2 | drt_violations best 19160 last 19160 rows 2 | before-window best 131284, window best 19160 | PROGRESS: drt_violations improved 85.4 % in window |  |
| intel1 | prd-eco_20261125_040243_2843749-i1-851245 | eco_20261125_040243_2843749-i1 | 5_2_route | 8.6 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
| intel1 | prd-eco_20261125_050013_1448739-i1-3109373 | eco_20261125_050013_1448739-i1 | 5_2_route | 7.7 | drt_violations best 139 last 139 rows 1 | before-window best 139, window best 139 | PROGRESS: drt_violations: active iteration at 1 < best completed total 139 (in-iteration D |  |
