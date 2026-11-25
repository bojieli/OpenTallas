# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 12:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 8, 'GRT-LABEL': 2, 'YOUNG': 108, 'NO-DATA': 25, 'PROGRESS': 25}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc11 | dpkit-slw_su_c__cl19bb38ef-40900 | slw_su_c | postcts_gate_TT | 5.6 | last meaningful line 0.0 h ago (45/45 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -433.58 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc12 | otc-351743-16220 | 351743 | hcpg_run | 7.0 | last meaningful line 6.6 h ago (13/13 lines) | NO-PROGRESS: no new non-iteration log line for 6.6 h | REPORT-ONLY: lane-own kit (abstract-exact decides; |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv8995e794-2664422 | col_h9_r0_p5__t1 | pregrt_ff_hold | 4.5 | repair_TNS best 168816 last 168816 rows 1 | before-window best 168816, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | pregrt_ff_hold | 4.8 | repair_TNS best 4684.26 last 4684.26 rows 1 | before-window best 4684.26, window best 4684.26 | NO-PROGRESS: repair_TNS best 4684.26 vs 4684.26 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 25.4 | drt_violations best 4 last 4 rows 57 | before-window best 4, window best 4 | NO-PROGRESS: drt_violations best 4 vs 4 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | pregrt_ff_hold | 7.6 | repair_TNS best 71771.6 last 71771.6 rows 1 | before-window best 71771.6, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | pregrt_ff_hold | 7.5 | repair_TNS best 80867.4 last 80867.4 rows 1 | before-window best 80867.4, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | pregrt_ff_hold | 7.6 | repair_TNS best 86468.6 last 86468.6 rows 1 | before-window best 86468.6, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 23.6 | drt_violations best 1 last 1 rows 45 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_hg_v1p3__r838481cd7-1149343 | kv3_hg_v1p3__r838481cd7 | 5_1_grt | 2.8 | grt rounds 2 overflow 5:39999 -> 10:36574 | GRT-LABEL: DESIGN-FAIL: overflow 36574 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_hg_v1p5-1187885 | kv3_hg_v1p5 | 5_1_grt | 2.8 | grt rounds 2 overflow 5:49289 -> 10:43054 | GRT-LABEL: DESIGN-FAIL: overflow 43054 at round 10 > 1000 |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 5_1_grt | 3.3 | last meaningful line 0.1 h ago (162/162 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-1130830 | col_h9_r0_p5__t1 | 5_1_grt | 3.3 | last meaningful line 0.2 h ago (273/1282 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc93af856-1168215 | col_h9_r0_p5__t1 | 5_1_grt | 3.3 | last meaningful line 0.0 h ago (2497/2503 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Eo-1420436 | kv3_hub_Eo | 5_1_grt | 5.0 | repair_Viol best 87 last 87 rows 7 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Wi-2642655 | kv3_hub_Wi | 4_1_cts | 2.5 | last meaningful line 0.1 h ago (11854/11854 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc11 | eco-abs-3350019 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.1 h ago (29/29 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | otc-1616228-26288 | 1616228 | - | 6.9 |  | NO-DATA: no log found |  |
| epyc11 | otc-381902-2867 | 381902 | - | 11.4 |  | NO-DATA: no log found |  |
| epyc11 | prd-eco_20261125_190538_59803-i1-918389 | eco_20261125_190538_59803-i1 | 5_2_route | 1.4 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | so_2736994_ff_31614 | so_2736994_ff_31614 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (1034/1034 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | so_2736994_tt_31614 | so_2736994_tt_31614 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (1034/1034 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | so_2942128_ff_44723 | so_2942128_ff_44723 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (908/908 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | so_2942128_tt_44723 | so_2942128_tt_44723 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (908/908 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | ap-ageom-kw-bk-sel--t2-grt-975756 | bk-sel--t2-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc12 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-973347 | col_h10_r1__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (322/322 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-gunit__t1-327777 | gunit__t1 | 3_5_place_dp | 0.5 | last meaningful line 0.2 h ago (39/39 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-3889249 | kv3_pc | pregrt_ff_hold | 0.9 | repair_TNS best 8596.61 last 8596.61 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-native59-478901 | native59 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5416/5416 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | dpkit-sle_ctl__cla4f6f12f-254756 | sle_ctl | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (11092/11092 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t21-1090377 | slice_station__t21 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (1187/1188 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t22-709728 | slice_station__t22 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (2919/2919 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t50__cl39451317-406569 | slice_station__t50 | pregrt_ff_hold | 0.4 | repair_TNS best 43428.1 last 43428.1 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 9.1 |  | NO-DATA: no log found |  |
| epyc12 | otc-1087770-15013 | 1087770 | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (11/11 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | otc-1096617-27639 | 1096617 | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (11/11 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | otc-1267541-535 | 1267541 | grt_it0 | 2.5 | last meaningful line 0.2 h ago (31/32 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | otc-1460135-77 | 1460135 | - | 8.2 |  | NO-DATA: no log found |  |
| epyc12 | otc-167973-28965 | 167973 | flow | 3.1 | repair_Violations best 183221 last 183221 rows 63 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | cranky_ganguly | cranky_ganguly | drc | 1.9 | last meaningful line 1.8 h ago (132/132 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | 5_1_grt | 3.3 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | epic_mclean | epic_mclean | drc | 1.8 | last meaningful line 1.5 h ago (129/129 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | nifty_lalande | nifty_lalande | drc | 1.5 | last meaningful line 1.5 h ago (129/129 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | optimistic_feynman | optimistic_feynman | drc | 1.7 | last meaningful line 1.5 h ago (132/132 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | otc-2344331-13980 | 2344331 | - | 2.9 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 6.9 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 6.9 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 6.9 |  | NO-DATA: no log found |  |
| epyc2 | serene_goodall | serene_goodall | drc | 3.1 | last meaningful line 3.0 h ago (124/124 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | upbeat_noyce | upbeat_noyce | drc | 3.2 | last meaningful line 3.0 h ago (121/121 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00_s2-1045407 | cbf_q00_s2 | tt_setup_repair_grt | 4.9 | repair_Violations best 508 last 4191 rows 21 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc7 | dpkit-coll_ftm-2399818 | coll_ftm | 5_2_route | 2.9 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-coll_s-1906595 | coll_s | 5_2_route | 3.0 | drt_violations best 43756 last 43756 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v12e-1804185 | kv3_pv_v12e | 4_1_cts | 4.6 | last meaningful line 0.2 h ago (12142/12142 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | tt_setup_repair | 7.0 | repair_Viol best 235 last 235 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 5_1_grt | 6.8 | last meaningful line 0.1 h ago (1914/1920 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | 6_report | 14.1 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 11.0 | drt_violations best 477402 last 477402 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 11.0 | drt_violations best 493451 last 493451 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-22145 | sle_sc_v2 | 5_2_route | 5.2 | drt_violations best 412199 last 412199 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | 4_1_cts | 2.0 | last meaningful line 0.2 h ago (7174/7174 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-362758 | slw_hc2 | 4_1_cts | 2.1 | last meaningful line 0.2 h ago (5321/5321 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3806800 | slw_hc3 | pregrt_ff_hold | 2.4 | repair_TNS best 250989 last 250989 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 11.4 | drt_violations best 468535 last 468535 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l0__cl1a1c1f8f-3953315 | slw_su_l0 | postcts_gate_FF | 2.3 | last meaningful line -0.0 h ago (19299/19299 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 4.2 | drt_violations best 78477 last 78477 rows 3 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc7 | otc-2938337-22499 | 2938337 | - | 7.5 |  | NO-DATA: no log found |  |
| epyc7 | otc-3693543-29719 | 3693543 | - | 3.8 |  | NO-DATA: no log found |  |
| epyc7 | otc-639211-10962 | 639211 | - | 3.5 |  | NO-DATA: no log found |  |
| epyc7 | otc-668380-26147 | 668380 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-native59-2892451 | native59 | 4_1_cts | 1.6 | last meaningful line 0.0 h ago (5634/5634 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 4_1_cts | 2.1 | last meaningful line 0.0 h ago (5775/5775 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v3-4131858 | sle_sc_v3 | 5_1_grt | 2.5 | last meaningful line 0.1 h ago (1892/1916 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-287710 | slw_hc3 | 4_1_cts | 2.4 | last meaningful line 0.2 h ago (7190/7190 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-tt_ctlm-548365 | tt_ctlm | 5_1_grt | 2.3 | last meaningful line 0.1 h ago (2705/2754 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | otc-132122-8685 | 132122 | - | 8.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-1467259-21054 | 1467259 | - | 2.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-1609200-26446 | 1609200 | - | 4.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-1616827-18813 | 1616827 | - | 4.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-1633866-27286 | 1633866 | - | 3.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-192475-3213 | 192475 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-2113939-31863 | 2113939 | - | 4.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-3513890-1914 | 3513890 | clk_freeze_post | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-3569473-6282 | 3569473 | - | 3.7 |  | NO-DATA: no log found |  |
| epyc8 | otc-3579536-7216 | 3579536 | - | 3.7 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_025941_3548303-i3t-2012963 | eco_20261125_025941_3548303-i3t | 5_1_grt | 0.5 | last meaningful line 0.1 h ago (292/360 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_104318_3955073-i2t-2392383 | eco_20261125_104318_3955073-i2t | 5_1_grt | 0.4 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_122258_3982108-i2-1278157 | eco_20261125_122258_3982108-i2 | 5_1_grt | 0.7 | last meaningful line 0.1 h ago (295/325 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_182230_4100536-i1-1439446 | eco_20261125_182230_4100536-i1 | 5_2_route | 2.0 | last meaningful line 0.1 h ago (266/267 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-1427167 | col_h10_r0_p1__t1 | pregrt_ff_hold | 4.0 | repair_TNS best 37858.4 last 37858.4 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvc9270d09-1494595 | col_h10_r0_p4__t1 | 5_1_grt | 4.8 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2175059 | col_h10_r0_p4__t1 | pregrt_ff_hold | 3.8 | repair_TNS best 53228.6 last 53228.6 rows 1 | YOUNG: evidence 2.2 h < 2.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 5_2_route | 13.8 | drt_violations best 91231 last 91231 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | pregrt_ff_hold | 1.1 | repair_TNS best 57363.5 last 57363.5 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 5_1_grt | 3.2 | last meaningful line 0.0 h ago (154/154 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 5_2_route | 4.8 | last meaningful line 0.4 h ago (269/270 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-870318 | col_h9_r0_p3__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 51108.9 last 51108.9 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-2913060 | col_h9_r0_p4__t1 | 4_2_tapbal_grt | 0.6 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 10.9 | drt_violations best 470122 last 470122 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | pregrt_ff_hold | 1.7 | repair_TNS best 60506.6 last 60506.6 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 4_2_tapbal_grt | 3.2 | last meaningful line 2.5 h ago (61/109 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.1 | last meaningful line 0.3 h ago (61/70 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | pregrt_ff_hold | 4.7 | repair_TNS best 48858.5 last 48858.5 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 62577.4 last 62577.4 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_2_route | 4.7 | last meaningful line 0.1 h ago (263/263 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-138946 | col_h9_r2__t1 | pregrt_ff_hold | 1.2 | repair_TNS best 22910.6 last 22910.6 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | pregrt_ff_hold | 1.2 | repair_TNS best 64056.3 last 64056.3 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-2945122 | col_h9_r2__t1 | 5_2_route | 4.4 | last meaningful line 0.3 h ago (270/271 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | 5_2_route | 4.6 | last meaningful line 0.0 h ago (264/265 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 5_2_route | 4.0 | last meaningful line 0.0 h ago (263/263 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 5_1_grt | 3.3 | last meaningful line 0.2 h ago (266/1230 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | selrange | 1.6 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-1920080 | dsdv_slice_c3x_C__t1 | 3_1_place_gp_skip_io | 3.1 | overflow best 0.9107 last 0.9107 rows 4 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2186209 | dsdv_slice_lepe_nh_mus_LP__t1 | tt_setup_repair_grt | 4.6 | repair_Viol best 877 last 877 rows 63 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | 4_1_cts | 3.3 | last meaningful line 0.1 h ago (44/44 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t11-1456626 | ot_s81sl_leaf__t11 | pregrt_ff_hold | 0.9 | repair_TNS best 303657 last 303657 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t32-2058978 | ot_s81sl_leaf__t32 | 5_1_grt | 3.1 | last meaningful line 0.3 h ago (269/1278 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t31-407252 | slice_station__t31 | tt_setup_repair_grt | 1.1 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__clc8fb2c8c-2653854 | slice_station__t40 | 5_2_route | 4.5 | drt_violations best 18201 last 18201 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t6__cl54a9ceeb-2644120 | slice_station__t6 | 5_2_route | 3.7 | drt_violations best 20110 last 20110 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | ap-ageom-kw-hd-serdes-grt-1030854 | hd-serdes-grt | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | pregrt_ff_hold | 7.5 | repair_TNS best 50339.8 last 50339.8 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | 5_2_route | 7.7 | last meaningful line 0.3 h ago (264/265 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | 5_2_route | 7.5 | last meaningful line 0.3 h ago (268/269 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_2_route | 7.5 | last meaningful line 0.5 h ago (270/271 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 118766 last 118766 rows 1 | YOUNG: evidence 2.0 h < 2.5 h |  |
| intel1 | dpkit-coll_ftc-3824626 | coll_ftc | 4_1_cts | 2.2 | last meaningful line 0.3 h ago (6306/6306 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-coll_n-2865002 | coll_n | 5_2_route | 2.5 | drt_violations best 13929 last 13929 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | 4_1_cts | 2.6 | last meaningful line 0.0 h ago (5338/5338 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-4035353 | slw_hc3 | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (6502/6502 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v3-99093 | slw_sc_v3 | 4_1_cts | 2.0 | last meaningful line 0.1 h ago (5459/5459 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | otc-2908840-11609 | 2908840 | flow | 2.5 | last meaningful line 0.0 h ago (4286/4286 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | prd-count-p1_tc-2681077 | count-p1_tc | prd_count_p1_tc | 0.2 | last meaningful line 0.0 h ago (759/759 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1-1093733 | eco_20261125_002226_1452841-i1 | 5_1_grt | 1.5 | last meaningful line 0.6 h ago (296/363 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | prd-eco_20261125_070347_2847958-i1-3642895 | eco_20261125_070347_2847958-i1 | 5_2_route | 5.4 | drt_violations best 2 last 2 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | prd-eco_20261125_072849_2847456-i1-527377 | eco_20261125_072849_2847456-i1 | 5_2_route | 5.0 | drt_violations best 30 last 30 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | prd-eco_20261125_082621_46745-i1-2873810 | eco_20261125_082621_46745-i1 | 5_2_route | 4.0 | drt_violations best 4 last 4 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | so_2200105_ff_6493 | so_2200105_ff_6493 | signoff | 1.2 |  | NO-DATA: empty log |  |
| intel1 | so_2200105_tt_6493 | so_2200105_tt_6493 | signoff | 1.2 |  | NO-DATA: empty log |  |
| intel2 | dpkit-coll_ftm-1730453 | coll_ftm | abstract_exact | 2.5 | last meaningful line 0.1 h ago (4/4 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-2159590 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5443 last 5443 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-sle_ctl__cla4f6f12f-1437376 | sle_ctl | 3_3_place_gp | 1.2 | overflow best 0.0979 last 0.099 rows 92 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-3663167 | slice_station__t12 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (200/200 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 4_1_cts | 2.0 | last meaningful line 0.0 h ago (5869/5869 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 25.7 | drt_violations best 232 last 232 rows 45 | before-window best 956, window best 232 | PROGRESS: drt_violations improved 75.7 % in window |  |
| epyc10 | prd-eco_20261125_174256_3687300-i1-1643366 | eco_20261125_174256_3687300-i1 | 5_2_route | 2.6 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-1395551 | col_h9_r0_p5__t1 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | pregrt_ff_hold | 3.3 | last meaningful line 0.1 h ago (128/128 lines) | PROGRESS: log still growing |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-1072222 | col_h9_r0_p5__t1 | pregrt_ff_hold | 3.3 | repair_Violations best 98 last 102 rows 21 | before-window best 240263, window best 98 | PROGRESS: repair_Violations improved 100.0 % in window |  |
| epyc12 | dpkit-slice_station__t28-478906 | slice_station__t28 | 5_1_grt | 0.4 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc12 | otc-3501458-13012 | 3501458 | drc_macros_only | 9.2 | last meaningful line 0.8 h ago (670/670 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 10.7 | drt_violations best 1 last 1 rows 50 | before-window best 23119, window best 1 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 14.1 | drt_violations best 11585 last 11585 rows 8 | before-window best 456468, window best 11585 | PROGRESS: drt_violations improved 97.5 % in window |  |
| epyc8 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-918588 | col_h10_r0_p1__t1 | 5_1_grt | 8.3 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 28.4 | drt_violations best 18 last 18 rows 46 | before-window best 445, window best 18 | PROGRESS: drt_violations improved 96.0 % in window |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3804990 | col_h10_r0_p1__t1 | 4_2_tapbal_grt | 2.8 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvd8c0565f-1181305 | col_h10_r0_p4__t1 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-268067 | col_h9_r0_p2__t1 | 4_2_tapbal_grt | 1.9 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 13.8 | drt_violations best 535484 last 535484 rows 1 | before-window best 535484, window best 535484 | PROGRESS: drt_violations: active iteration at 264277 < best completed total 535484 (in-ite |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 4_2_tapbal_grt | 1.2 | repair_Violations best 0 last 0 rows 18 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 15.6 | drt_violations best 532 last 532 rows 31 | before-window best 2838, window best 532 | PROGRESS: drt_violations improved 81.3 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | pregrt_ff_hold | 3.2 | repair_Violations best 26065 last 26065 rows 21 | before-window best 465849, window best 26065 | PROGRESS: repair_Violations improved 94.4 % in window |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2686622 | col_h10_r0_p4__t1 | pregrt_ff_hold | 7.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 5_2_route | 19.5 | drt_violations best 18263 last 18263 rows 2 | before-window best 147106, window best 18263 | PROGRESS: drt_violations improved 87.6 % in window |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 21.2 | drt_violations best 278493 last 278493 rows 1 | before-window best 278493, window best 278493 | PROGRESS: drt_violations: active iteration at 272784 < best completed total 278493 (in-ite |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 5_2_route | 21.9 | drt_violations best 131284 last 131284 rows 1 | before-window best 131284, window best 131284 | PROGRESS: drt_violations: active iteration at 21581 < best completed total 131284 (in-iter |  |
| intel1 | prd-eco_20261125_040243_2843749-i1-851245 | eco_20261125_040243_2843749-i1 | 5_2_route | 8.4 | drt_violations best 457 last 457 rows 1 | before-window best 457, window best 457 | PROGRESS: drt_violations: active iteration at 71 < best completed total 457 (in-iteration  |  |
| intel1 | prd-eco_20261125_050013_1448739-i1-3109373 | eco_20261125_050013_1448739-i1 | 5_2_route | 7.4 | drt_violations best 139 last 139 rows 1 | before-window best 139, window best 139 | PROGRESS: drt_violations: active iteration at 1 < best completed total 139 (in-iteration D |  |
