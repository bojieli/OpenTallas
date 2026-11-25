# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 11:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 3, 'GRT-LABEL': 4, 'YOUNG': 142, 'NO-DATA': 33, 'PROGRESS': 18}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc11 | dpkit-kv3_hub_Wo-1632470 | kv3_hub_Wo | 5_1_grt | 3.7 | last meaningful line 0.2 h ago (1376/1382 lines) | UNSIGNABLE: GRT overflow flat: overflow 1 at iteration 5 -> 1 at iteration 10: flat for 5 it | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2686622 | col_h10_r0_p4__t1 | pregrt_ff_hold | 6.4 | repair_TNS best 96462.2 last 96462.2 rows 1 | before-window best 96462.2, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | pregrt_ff_hold | 6.4 | repair_TNS best 71771.6 last 71771.6 rows 1 | before-window best 71771.6, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 22.4 | drt_violations best 1 last 1 rows 45 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_hg_v1p3__r838481cd7-1149343 | kv3_hg_v1p3__r838481cd7 | 5_1_grt | 1.5 | grt rounds 2 overflow 5:39999 -> 10:36108 | GRT-LABEL: DESIGN-FAIL: overflow 36108 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_hg_v1p5-1187885 | kv3_hg_v1p5 | 5_1_grt | 1.5 | grt rounds 2 overflow 5:49289 -> 10:43054 | GRT-LABEL: DESIGN-FAIL: overflow 43054 at round 10 > 1000 |  |
| epyc11 | dpkit-slw_su_c__cl19bb38ef-40900 | slw_su_c | 5_1_grt | 4.4 | grt rounds 2 overflow 5:28383 -> 10:18754 | GRT-LABEL: DESIGN-FAIL: overflow 18754 at round 10 > 1000 |  |
| epyc7 | dpkit-cbf_q00_s2-1045407 | cbf_q00_s2 | 5_1_grt | 3.6 | grt rounds 2 overflow 5:87022 -> 10:54031 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-491862 | cbf_q00 | 3_3_place_gp | 0.6 | overflow best 0.3357 last 0.3395 rows 21 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-cbf_q01-1552504 | cbf_q01 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8991 last 0.8991 rows 8 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-cbf_q01_s2-311731 | cbf_q01_s2 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (101/101 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-cbn_q00__cld7bf7197-1624647 | cbn_q00 | 2_1_floorplan | 0.3 | repair_Viol best 6148 last 6148 rows 591 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-cbn_q01__cld9ff4c40-769504 | cbn_q01 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.199 last 0.199 rows 40 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-cbn_q11__cl49ae4555-2224224 | cbn_q11 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (301/301 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-706683 | sle_st_b_v1 | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2340010 | sle_st_b_v2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (324/324 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1334162 | sle_st_b_v2 | 1_2_yosys | 0.4 | last meaningful line 0.1 h ago (3610/3610 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2197948 | sle_stm_v1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (490/490 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v2__cl55be2264-1366673 | sle_stm_v2 | 3_3_place_gp | 0.4 | overflow best 0.5058 last 0.5077 rows 6 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-sle_su_l1__clc6d66f5b-2194729 | sle_su_l1 | 1_synth | 0.1 | last meaningful line 0.0 h ago (7/7 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-1303300 | slw_st_b_v1 | 1_synth | 0.4 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-771314 | slw_st_b_v2 | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | eco-abs-3877704 | eco-abs | generate_abstract | 0.9 | last meaningful line 0.4 h ago (31/31 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_174256_3687300-i1-1643366 | eco_20261125_174256_3687300-i1 | 5_2_route | 1.4 | last meaningful line 0.0 h ago (266/267 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_180222_3379404-i1t-2905775 | eco_20261125_180222_3379404-i1t | 5_2_route | 1.1 | last meaningful line 0.0 h ago (259/260 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-1395551 | col_h9_r0_p5__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 154542 last 154542 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 102568 last 102568 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 201336 last 201336 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-1130830 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 130048 last 130048 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc93af856-1168215 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 24080.8 last 24080.8 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-1072222 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.1 | repair_TNS best 170995 last 170995 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc11 | dpkit-kv3_hub_Eo-1420436 | kv3_hub_Eo | 5_1_grt | 3.7 | last meaningful line 0.3 h ago (1316/2408 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Wi-2642655 | kv3_hub_Wi | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (11296/11296 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_su_c-2149031 | sle_su_c | 5_1_grt | 3.4 | repair_Viol best 16 last 16 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc11 | otc-1616228-26288 | 1616228 | - | 5.6 |  | NO-DATA: no log found |  |
| epyc11 | otc-2018500-5230 | 2018500 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc11 | otc-381902-2867 | 381902 | - | 10.2 |  | NO-DATA: no log found |  |
| epyc11 | prd-eco_20261125_174711_1456062-i1-2307917 | eco_20261125_174711_1456062-i1 | 5_2_route | 1.4 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_190538_59803-i1-918389 | eco_20261125_190538_59803-i1 | 5_1_grt | 0.1 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | prd-fin-3847060 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (1068/1068 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | prd-fin-3864714 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | ap-ageom-kw-kv3-pc-v1--cl7f648944--r8422a4b86-grt-3056758 | kv3-pc-v1--cl7f648944--r8422a4b86-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc12 | ap-ageom-kw-sle-ctl--cla4f6f12f-grt-2956954 | sle-ctl--cla4f6f12f-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 7.9 |  | NO-DATA: no log found |  |
| epyc12 | otc-1267541-535 | 1267541 | flow | 1.3 | last meaningful line 0.0 h ago (3082/3082 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc12 | otc-1460135-77 | 1460135 | - | 7.0 |  | NO-DATA: no log found |  |
| epyc12 | otc-167973-28965 | 167973 | flow | 1.8 | repair_Violations best 283853 last 283853 rows 19 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc12 | otc-1994529-22240 | 1994529 | flow | 5.0 | repair_Violations best 90738 last 90738 rows 127 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc12 | otc-2833359-24228 | 2833359 | asbuilt.yosys | 0.3 | last meaningful line -0.0 h ago (135633/135633 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | otc-2869937-32180 | 2869937 | asbuilt.yosys | 0.2 | last meaningful line 0.0 h ago (135952/135952 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | otc-351743-16220 | 351743 | hcpg_run | 5.7 | last meaningful line 5.3 h ago (13/13 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc12 | otc-975504-31834 | 975504 | grt_it0 | 1.4 | last meaningful line 0.0 h ago (12/12 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | adoring_nobel | adoring_nobel | drc | 0.9 | last meaningful line 0.8 h ago (129/129 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | cranky_ganguly | cranky_ganguly | drc | 0.7 | last meaningful line 0.5 h ago (132/132 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (6724/6724 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | epic_mclean | epic_mclean | drc | 0.5 | last meaningful line 0.3 h ago (129/129 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | gifted_germain | gifted_germain | drc | 1.0 | last meaningful line 0.8 h ago (129/129 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | nifty_lalande | nifty_lalande | drc | 0.3 | last meaningful line 0.3 h ago (129/129 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | optimistic_feynman | optimistic_feynman | drc | 0.4 | last meaningful line 0.3 h ago (132/132 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | otc-2072908-20868 | 2072908 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc2 | otc-2073510-26058 | 2073510 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc2 | otc-2074501-27593 | 2074501 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc2 | otc-2342049-23133 | 2342049 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc2 | otc-2344331-13980 | 2344331 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc2 | otc-2786014-9554 | 2786014 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc2 | prd-count-p1_tc-961159 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (51/51 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 5.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 5.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 5.7 |  | NO-DATA: no log found |  |
| epyc2 | sad_wing | sad_wing | drc | 0.9 | last meaningful line 0.8 h ago (129/129 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | serene_goodall | serene_goodall | drc | 1.9 | last meaningful line 1.8 h ago (124/124 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | upbeat_noyce | upbeat_noyce | drc | 1.9 | last meaningful line 1.8 h ago (121/121 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-coll_ft__cl78c7b300-2883792 | coll_ft | 5_2_route | 1.4 | last meaningful line 0.0 h ago (232/233 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-coll_ftm-2399818 | coll_ftm | tt_setup_measure_grt | 1.6 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-coll_s-1906595 | coll_s | postcts_gate_TT | 1.8 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12e-1804185 | kv3_pv_v12e | 4_1_cts | 3.3 | last meaningful line 0.2 h ago (12112/12112 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | 4_1_cts | 5.8 | last meaningful line 0.7 h ago (11004/11004 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | 5_2_route | 12.9 | drt_violations best 32790 last 32790 rows 2 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 9.7 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 9.7 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-22145 | sle_sc_v2 | 5_2_route | 4.0 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__clc6d66f5b-2521917 | sle_su_l1 | generate_abstract | 10.2 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v2__cl8537f156-215605 | slw_fw_v2 | 3_3_place_gp | 0.9 | overflow best 0.4354 last 0.4354 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (7056/7056 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-362758 | slw_hc2 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (5211/5211 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3806800 | slw_hc3 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (5122/5122 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 10.1 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l0__cl1a1c1f8f-3953315 | slw_su_l0 | 5_1_grt | 1.1 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 2.9 | drt_violations best 284474 last 284474 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | otc-131491-13694 | 131491 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc7 | otc-2938337-22499 | 2938337 | - | 6.2 |  | NO-DATA: no log found |  |
| epyc7 | otc-3693543-29719 | 3693543 | - | 2.6 |  | NO-DATA: no log found |  |
| epyc7 | otc-639211-10962 | 639211 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-918588 | col_h10_r0_p1__t1 | 5_1_grt | 7.0 | last meaningful line 0.3 h ago (275/1282 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-coll_ft__cla4a25d77-1326788 | coll_ft | 5_2_route | 2.0 | drt_violations best 11526 last 11526 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc8 | dpkit-kv3_sys_SD-2811148 | kv3_sys_SD | 5_1_grt | 0.3 | repair_TNS best 12.486 last 12.486 rows 8 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-native59-2892451 | native59 | 4_1_cts | 0.3 | last meaningful line 0.2 h ago (5088/5088 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-287710 | slw_hc3 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (7107/7107 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-tt_ctlm-548365 | tt_ctlm | tt_setup_repair | 1.0 | repair_Viol best 225 last 225 rows 35 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | otc-1220115-969 | 1220115 | - | 3.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-1288521-5795 | 1288521 | - | 3.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-132122-8685 | 132122 | - | 7.3 |  | NO-DATA: no log found |  |
| epyc8 | otc-1467259-21054 | 1467259 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-1609200-26446 | 1609200 | - | 3.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-1616827-18813 | 1616827 | - | 3.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-1633866-27286 | 1633866 | - | 1.9 |  | NO-DATA: no log found |  |
| epyc8 | otc-192475-3213 | 192475 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-2113939-31863 | 2113939 | - | 2.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-3569473-6282 | 3569473 | - | 2.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-3579536-7216 | 3579536 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_123952_3914547-i2-1265285 | eco_20261125_123952_3914547-i2 | 5_1_grt | 0.8 | last meaningful line 0.3 h ago (292/489 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_182230_4100536-i1-1439446 | eco_20261125_182230_4100536-i1 | 5_1_grt | 0.8 | last meaningful line 0.2 h ago (293/316 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | so_1500975_ff_22076 | so_1500975_ff_22076 | generate_abstract | 0.8 | last meaningful line 0.8 h ago (35/35 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | so_1500975_tt_22076 | so_1500975_tt_22076 | generate_abstract | 0.8 | last meaningful line 0.8 h ago (35/35 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | so_3880836_ff_73278 | so_3880836_ff_73278 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | so_3880836_tt_73278 | so_3880836_tt_73278 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | so_3891588_ff_55118 | so_3891588_ff_55118 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | so_3891588_tt_55118 | so_3891588_tt_55118 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | tt_setup_measure_grt | 12.5 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3804990 | col_h10_r0_p1__t1 | 4_2_tapbal_grt | 1.5 | last meaningful line 0.5 h ago (62/69 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-1427167 | col_h10_r0_p1__t1 | pregrt_ff_hold | 2.7 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvc9270d09-1494595 | col_h10_r0_p4__t1 | pregrt_ff_hold | 3.5 | repair_TNS best 113133 last 113133 rows 1 | YOUNG: evidence 2.0 h < 2.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2175059 | col_h10_r0_p4__t1 | pregrt_ff_hold | 2.6 | repair_TNS best 53228.6 last 53228.6 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvd8c0565f-1181305 | col_h10_r0_p4__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 53512.7 last 53512.7 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 5_2_route | 12.5 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 44947.6 last 44947.6 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | postcts_gate_TT | 3.5 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-268067 | col_h9_r0_p2__t1 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (3916/3916 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-870318 | col_h9_r0_p3__t1 | 4_2_tapbal_grt | 1.3 | last meaningful line 0.3 h ago (62/68 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 12.5 | drt_violations best 535484 last 535484 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv8995e794-2664422 | col_h9_r0_p5__t1 | pregrt_ff_hold | 3.3 | repair_TNS best 168816 last 168816 rows 1 | YOUNG: evidence 1.6 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | pregrt_ff_hold | 3.5 | repair_TNS best 151565 last 151565 rows 1 | YOUNG: evidence 1.9 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 9.7 | last meaningful line 0.2 h ago (290/291 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.0 | last meaningful line 1.3 h ago (61/94 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pve3f8a86c-3965488 | col_h9_r1__t1 | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 47285.9 last 47285.9 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 5_1_grt | 3.5 | last meaningful line 0.2 h ago (265/1275 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 100484 last 100484 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-2945122 | col_h9_r2__t1 | tt_setup_repair_grt | 3.2 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | 5_1_grt | 3.3 | last meaningful line 0.2 h ago (266/1278 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 5_1_grt | 2.8 | last meaningful line 0.0 h ago (210/210 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 41307.4 last 41307.4 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | sdc_lint | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-1920080 | dsdv_slice_c3x_C__t1 | 1_1_yosys_canonicalize | 1.9 | last meaningful line 0.3 h ago (133/133 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | selrange | 2.0 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-ot_s81sl_leaf__t32-2058978 | ot_s81sl_leaf__t32 | pregrt_ff_hold | 1.8 | repair_TNS best 462874 last 462874 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-phy__t1-448804 | phy__t1 | pregrt_ff_hold | 0.6 | repair_TNS best 535620 last 535620 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slice_station__t30__cl6a190133-1093777 | slice_station__t30 | 5_2_route | 2.0 | drt_violations best 1553 last 1553 rows 3 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__clc8fb2c8c-2653854 | slice_station__t40 | 5_2_route | 3.3 | last meaningful line 0.1 h ago (255/256 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t46-1382971 | slice_station__t46 | 5_3_fillcell | 2.0 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t6__cl54a9ceeb-2644120 | slice_station__t6 | 5_2_route | 2.5 | last meaningful line 0.2 h ago (244/245 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | otc-1865534-29853 | 1865534 | - | 4.8 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 4_2_tapbal_grt | 6.3 | repair_Violations best 384 last 514 rows 11 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | pregrt_ff_hold | 6.2 | repair_TNS best 80867.4 last 80867.4 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | pregrt_ff_hold | 6.4 | repair_TNS best 86468.6 last 86468.6 rows 1 | YOUNG: evidence 1.4 h < 2.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | tt_setup_measure_grt | 6.4 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | 5_2_route | 6.3 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_2_route | 6.3 | last meaningful line 0.1 h ago (263/263 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | pregrt_ff_hold | 0.8 | repair_TNS best 118766 last 118766 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel1 | dpkit-coll_ftc-3824626 | coll_ftc | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (6171/6171 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-coll_n-2865002 | coll_n | 5_2_route | 1.2 | last meaningful line 0.1 h ago (232/232 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-hd_serdes-2069857 | hd_serdes | 3_3_place_gp | 1.5 | overflow best 0.6435 last 0.6435 rows 29 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | generate_abstract | 22.5 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 19.9 | last meaningful line 0.7 h ago (276/277 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | 4_1_cts | 1.4 | last meaningful line 0.2 h ago (5232/5232 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-4035353 | slw_hc3 | 4_1_cts | 0.8 | last meaningful line 0.2 h ago (6466/6466 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v3-99093 | slw_sc_v3 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (5325/5325 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 5_2_route | 20.7 | drt_violations best 131284 last 131284 rows 1 | YOUNG: evidence 6.0 h < 7.5 h |  |
| intel1 | otc-2908840-11609 | 2908840 | flow | 1.2 | last meaningful line 0.1 h ago (4079/4079 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | otc-574655-9239 | 574655 | drc_merged | 5.4 | last meaningful line 0.0 h ago (1316/1316 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1-1093733 | eco_20261125_002226_1452841-i1 | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (144/144 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | prd-eco_20261125_040243_2843749-i1-851245 | eco_20261125_040243_2843749-i1 | 5_2_route | 7.1 | drt_violations best 457 last 457 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i1-3109373 | eco_20261125_050013_1448739-i1 | 5_2_route | 6.2 | drt_violations best 139 last 139 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel1 | prd-eco_20261125_070347_2847958-i1-3642895 | eco_20261125_070347_2847958-i1 | 5_2_route | 4.1 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | prd-eco_20261125_072849_2847456-i1-527377 | eco_20261125_072849_2847456-i1 | 5_2_route | 3.7 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | prd-eco_20261125_082621_46745-i1-2873810 | eco_20261125_082621_46745-i1 | 5_2_route | 2.8 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-1730453 | coll_ftm | 5_2_route | 1.2 | last meaningful line 0.1 h ago (230/231 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-hd_ctl-1246411 | hd_ctl | 2_1_floorplan | 0.1 | repair_Viol best 947 last 947 rows 139 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-685143 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-892840 | kv3_io_ft | abstract_exact | 1.5 | last meaningful line 0.1 h ago (4/4 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-3431711 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (225/226 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (5256/5256 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 24.4 | drt_violations best 232 last 232 rows 44 | before-window best 3031, window best 232 | PROGRESS: drt_violations improved 92.3 % in window |  |
| epyc12 | otc-3501458-13012 | 3501458 | drc_merged | 7.9 | last meaningful line 0.3 h ago (646/646 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 9.5 | drt_violations best 2 last 2 rows 48 | before-window best 156586, window best 2 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-serdes__t2-2603266 | serdes__t2 | pregrt_ff_hold | 1.5 | repair_Violations best 0 last 0 rows 6 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 5_1_grt | 5.5 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 12.8 | drt_violations best 76101 last 76101 rows 3 | before-window best 456468, window best 76101 | PROGRESS: drt_violations improved 83.3 % in window |  |
| epyc8 | dpkit-kv3_sys_SD-2544893 | kv3_sys_SD | 5_1_grt | 0.4 | repair_TNS best 0 last 0 rows 21 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc8 | dpkit-sle_sc_v3-4131858 | sle_sc_v3 | pregrt_ff_hold | 1.2 | repair_Violations best 0 last 0 rows 5 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 27.1 | drt_violations best 18 last 18 rows 44 | before-window best 6413, window best 18 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 4_1_cts | 0.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | 4_2_tapbal_grt | 3.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 4_2_tapbal_grt | 0.7 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 14.4 | drt_violations best 553 last 863 rows 27 | before-window best 6695, window best 553 | PROGRESS: drt_violations improved 91.7 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | 5_2_route | 13.5 | drt_violations best 372 last 372 rows 44 | before-window best 24944, window best 372 | PROGRESS: drt_violations improved 98.5 % in window |  |
| epyc9 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2186209 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 3.4 | repair_TNS best 0 last 0 rows 4 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 24.2 | drt_violations best 4 last 4 rows 53 | before-window best 5, window best 4 | PROGRESS: drt_violations improved 20.0 % in window |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 5_2_route | 18.2 | drt_violations best 147106 last 147106 rows 1 | before-window best 147106, window best 147106 | PROGRESS: drt_violations: active iteration at 80111 < best completed total 147106 (in-iter |  |
| intel1 | prd-eco_20261123_191853_2879776-i3t-2681077 | eco_20261123_191853_2879776-i3t | 5_2_route | 8.4 | drt_violations best 2583 last 2583 rows 1 | before-window best 2583, window best 2583 | PROGRESS: drt_violations: active iteration at 1288 < best completed total 2583 (in-iterati |  |
