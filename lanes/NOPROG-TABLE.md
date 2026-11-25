# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 11:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 6, 'GRT-LABEL': 4, 'YOUNG': 138, 'NO-DATA': 30, 'PROGRESS': 24}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc9 | dpkit-col_h10_r0_p4__t1__pvc9270d09-1494595 | col_h10_r0_p4__t1 | pregrt_ff_hold | 4.0 | repair_TNS best 113133 last 113133 rows 1 | before-window best 113133, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | pregrt_ff_hold | 4.0 | repair_TNS best 151565 last 151565 rows 1 | before-window best 151565, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 24.7 | drt_violations best 4 last 4 rows 53 | before-window best 4, window best 4 | NO-PROGRESS: drt_violations best 4 vs 4 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2686622 | col_h10_r0_p4__t1 | pregrt_ff_hold | 6.9 | repair_TNS best 21.608 last 21.608 rows 1 | before-window best 21.608, window best 21.608 | NO-PROGRESS: repair_TNS best 21.608 vs 21.608 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | pregrt_ff_hold | 6.9 | repair_TNS best 71771.6 last 71771.6 rows 1 | before-window best 71771.6, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 22.9 | drt_violations best 1 last 1 rows 45 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_hg_v1p3__r838481cd7-1149343 | kv3_hg_v1p3__r838481cd7 | 5_1_grt | 2.0 | grt rounds 2 overflow 5:39999 -> 10:36108 | GRT-LABEL: DESIGN-FAIL: overflow 36108 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_hg_v1p5-1187885 | kv3_hg_v1p5 | 5_1_grt | 2.0 | grt rounds 2 overflow 5:49289 -> 10:43054 | GRT-LABEL: DESIGN-FAIL: overflow 43054 at round 10 > 1000 |  |
| epyc11 | dpkit-slw_su_c__cl19bb38ef-40900 | slw_su_c | 5_1_grt | 4.9 | grt rounds 2 overflow 5:28383 -> 10:18754 | GRT-LABEL: DESIGN-FAIL: overflow 18754 at round 10 > 1000 |  |
| epyc7 | dpkit-cbf_q00_s2-1045407 | cbf_q00_s2 | 5_1_grt | 4.1 | grt rounds 2 overflow 5:87022 -> 10:54031 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-cbf_q00__cl870de686-2958238 | cbf_q00 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9084 last 0.9084 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-cbf_q01-1552504 | cbf_q01 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (101/101 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-cbn_q00__cld7bf7197-1624647 | cbn_q00 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (285/285 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-cbn_q00__cldbcda913-3500320 | cbn_q00 | 2_1_floorplan | 0.1 | repair_Viol best 6754 last 6754 rows 180 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-cbn_q01__cld9ff4c40-769504 | cbn_q01 | 3_4_place_resized | 1.1 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-cbn_q11__cl49ae4555-2224224 | cbn_q11 | 3_3_place_gp | 0.6 | overflow best 0.5169 last 0.5169 rows 21 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-sle_sc_v1__cl7479a5ec-2717977 | sle_sc_v1 | 3_3_place_gp | 0.4 | overflow best 0.1294 last 0.1294 rows 51 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3049936 | sle_st_b_v1 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2340010 | sle_st_b_v2 | 3_3_place_gp | 0.6 | overflow best 0.0996 last 0.0996 rows 46 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1334162 | sle_st_b_v2 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2197948 | sle_stm_v1 | 3_3_place_gp | 0.6 | overflow best 0.4856 last 0.4857 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-sle_stm_v3-2545680 | sle_stm_v3 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (79/79 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3133312 | slw_sc_v1 | 3_3_place_gp | 0.2 | overflow best 0.3522 last 0.3522 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-1303300 | slw_st_b_v1 | 3_3_place_gp | 0.9 | overflow best 0.099 last 0.099 rows 46 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2892336 | slw_st_b_v2 | 3_3_place_gp | 0.3 | overflow best 0.653 last 0.653 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slw_st_b_v2__pvc2ec5bfb-3323454 | slw_st_b_v2 | synth_odb_v | 0.1 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_stm_v3-3634390 | slw_stm_v3 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_174256_3687300-i1-1643366 | eco_20261125_174256_3687300-i1 | 5_2_route | 1.9 | last meaningful line 0.1 h ago (280/281 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | prd-eco_retry_1795634165612607153-i1t-2640794 | eco_retry_1795634165612607153-i1t | 5_1_grt | 0.4 | last meaningful line 0.3 h ago (289/450 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | so_2762470_tt_95065 | so_2762470_tt_95065 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (35/35 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-1395551 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.4 | repair_TNS best 154542 last 154542 rows 1 | YOUNG: evidence 1.4 h < 2.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 102568 last 102568 rows 1 | YOUNG: evidence 1.6 h < 2.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 201336 last 201336 rows 1 | YOUNG: evidence 1.7 h < 2.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-1130830 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 4203.53 last 4203.53 rows 1 | YOUNG: evidence 1.8 h < 2.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc93af856-1168215 | col_h9_r0_p5__t1 | 5_1_grt | 2.5 | last meaningful line 0.0 h ago (162/162 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-1072222 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.6 | repair_TNS best 170995 last 170995 rows 1 | YOUNG: evidence 1.7 h < 2.5 h |  |
| epyc11 | dpkit-kv3_hub_Eo-1420436 | kv3_hub_Eo | 5_1_grt | 4.2 | last meaningful line 0.1 h ago (2437/2450 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Wi-2642655 | kv3_hub_Wi | 4_1_cts | 1.7 | last meaningful line 0.5 h ago (11296/11296 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Wo-1632470 | kv3_hub_Wo | postcts_gate_TT | 4.2 | last meaningful line 0.3 h ago (2608/2608 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | dpkit-sle_su_c-2149031 | sle_su_c | postcts_gate_TT | 3.9 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | eco-abs-1300974 | eco-abs | generate_abstract | 0.4 | last meaningful line 0.1 h ago (1030/1030 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | eco-abs-1481336 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.2 h ago (902/902 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | otc-1616228-26288 | 1616228 | - | 6.1 |  | NO-DATA: no log found |  |
| epyc11 | otc-2018500-5230 | 2018500 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc11 | otc-381902-2867 | 381902 | - | 10.7 |  | NO-DATA: no log found |  |
| epyc11 | prd-eco_20261125_174711_1456062-i1-2307917 | eco_20261125_174711_1456062-i1 | 5_2_route | 1.9 | drt_violations best 1 last 1 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_190538_59803-i1-918389 | eco_20261125_190538_59803-i1 | 5_2_route | 0.6 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-3889249 | kv3_pc | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3744/3744 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t17-3946927 | slice_station__t17 | 3_3_place_gp | 0.1 | overflow best 0.2751 last 0.2751 rows 25 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-slice_station__t21-3960674 | slice_station__t21 | 3_3_place_gp | 0.1 | overflow best 0.2985 last 0.2989 rows 11 | YOUNG: stage 0.0 h < 1 h |  |
| epyc12 | dpkit-slice_station__t28-4049873 | slice_station__t28 | 2_4_floorplan_pdn | 0.0 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-slice_station__t7__cl362204c4-4034091 | slice_station__t7 | 2_4_floorplan_pdn | 0.0 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 8.4 |  | NO-DATA: no log found |  |
| epyc12 | otc-1267541-535 | 1267541 | flow | 1.8 | last meaningful line 0.0 h ago (3253/3253 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc12 | otc-1460135-77 | 1460135 | - | 7.5 |  | NO-DATA: no log found |  |
| epyc12 | otc-167973-28965 | 167973 | flow | 2.3 | repair_Violations best 246195 last 246195 rows 36 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc12 | otc-1994529-22240 | 1994529 | flow | 5.5 | repair_Violations best 86914 last 86914 rows 151 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | adoring_nobel | adoring_nobel | drc | 1.4 | last meaningful line 1.3 h ago (129/129 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | cranky_ganguly | cranky_ganguly | drc | 1.2 | last meaningful line 1.0 h ago (132/132 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | 4_1_cts | 2.6 | last meaningful line 0.1 h ago (6732/6732 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | eco-abs-2002232 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.1 h ago (29/29 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | epic_mclean | epic_mclean | drc | 1.0 | last meaningful line 0.8 h ago (129/129 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | gifted_germain | gifted_germain | drc | 1.5 | last meaningful line 1.3 h ago (129/129 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | nifty_lalande | nifty_lalande | drc | 0.8 | last meaningful line 0.7 h ago (129/129 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | optimistic_feynman | optimistic_feynman | drc | 0.9 | last meaningful line 0.8 h ago (132/132 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | otc-2072908-20868 | 2072908 | - | 2.3 |  | NO-DATA: no log found |  |
| epyc2 | otc-2074501-27593 | 2074501 | - | 2.3 |  | NO-DATA: no log found |  |
| epyc2 | otc-2344331-13980 | 2344331 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc2 | otc-2786014-9554 | 2786014 | - | 2.0 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 6.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 6.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 6.2 |  | NO-DATA: no log found |  |
| epyc2 | sad_wing | sad_wing | drc | 1.4 | last meaningful line 1.3 h ago (129/129 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | serene_goodall | serene_goodall | drc | 2.4 | last meaningful line 2.3 h ago (124/124 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | upbeat_noyce | upbeat_noyce | drc | 2.4 | last meaningful line 2.3 h ago (121/121 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-coll_ft__cl78c7b300-2883792 | coll_ft | 5_2_route | 1.9 | drt_violations best 11359 last 11359 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc7 | dpkit-coll_ftm-2399818 | coll_ftm | 5_2_route | 2.1 | last meaningful line 0.0 h ago (242/242 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-coll_s-1906595 | coll_s | 5_2_route | 2.3 | last meaningful line 0.1 h ago (243/243 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12e-1804185 | kv3_pv_v12e | 4_1_cts | 3.8 | last meaningful line 0.3 h ago (12115/12115 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t2-2603266 | serdes__t2 | 5_1_grt | 2.0 | last meaningful line 0.2 h ago (265/1269 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 5_1_grt | 6.0 | last meaningful line 0.5 h ago (317/1819 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | 5_2_route | 13.4 | drt_violations best 32790 last 32790 rows 2 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 10.2 | drt_violations best 477402 last 477402 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 10.2 | last meaningful line 0.5 h ago (278/279 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-22145 | sle_sc_v2 | 5_2_route | 4.5 | last meaningful line 0.5 h ago (281/282 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v2__cl8537f156-215605 | slw_fw_v2 | 3_4_place_resized | 1.4 | last meaningful line 0.0 h ago (365/365 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | 4_1_cts | 1.2 | last meaningful line 0.3 h ago (7084/7084 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-362758 | slw_hc2 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (5242/5242 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3806800 | slw_hc3 | 4_1_cts | 1.6 | last meaningful line 0.2 h ago (5150/5150 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 10.6 | drt_violations best 468535 last 468535 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 3.4 | drt_violations best 102693 last 102693 rows 2 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | otc-131491-13694 | 131491 | - | 2.9 |  | NO-DATA: no log found |  |
| epyc7 | otc-2804287-17722 | 2804287 | signoff | 0.2 | last meaningful line 0.2 h ago (3/3 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | otc-2938337-22499 | 2938337 | - | 6.7 |  | NO-DATA: no log found |  |
| epyc7 | otc-3693543-29719 | 3693543 | - | 3.1 |  | NO-DATA: no log found |  |
| epyc7 | otc-639211-10962 | 639211 | - | 2.7 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-918588 | col_h10_r0_p1__t1 | 5_1_grt | 7.5 | last meaningful line 0.0 h ago (1297/1297 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-coll_ft__cla4a25d77-1326788 | coll_ft | 6_report | 2.5 | last meaningful line 0.0 h ago (47/47 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_sys_SD-2544893 | kv3_sys_SD | 5_2_route | 0.9 | last meaningful line 0.0 h ago (229/230 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_sys_SD-2811148 | kv3_sys_SD | tt_setup_repair_grt | 0.8 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-native59-2892451 | native59 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (5435/5435 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (5639/5639 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-287710 | slw_hc3 | 4_1_cts | 1.6 | last meaningful line 0.2 h ago (7113/7113 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-tt_ctlm-548365 | tt_ctlm | 5_1_grt | 1.5 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-1220115-969 | 1220115 | - | 3.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-1288521-5795 | 1288521 | - | 3.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-132122-8685 | 132122 | - | 7.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-1467259-21054 | 1467259 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc8 | otc-1609200-26446 | 1609200 | - | 3.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-1616827-18813 | 1616827 | - | 3.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-1633866-27286 | 1633866 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-192475-3213 | 192475 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-2113939-31863 | 2113939 | - | 3.3 |  | NO-DATA: no log found |  |
| epyc8 | otc-3569473-6282 | 3569473 | - | 3.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-3579536-7216 | 3579536 | - | 2.9 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_123952_3914547-i2-1265285 | eco_20261125_123952_3914547-i2 | 5_2_route | 1.3 | last meaningful line 0.0 h ago (254/254 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_182230_4100536-i1-1439446 | eco_20261125_182230_4100536-i1 | 5_2_route | 1.3 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | so_3880836_ff_73278 | so_3880836_ff_73278 | generate_abstract | 0.5 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | so_3880836_tt_73278 | so_3880836_tt_73278 | generate_abstract | 0.5 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | so_3891588_ff_55118 | so_3891588_ff_55118 | generate_abstract | 0.5 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | so_3891588_tt_55118 | so_3891588_tt_55118 | generate_abstract | 0.5 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3804990 | col_h10_r0_p1__t1 | 4_2_tapbal_grt | 2.0 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-1427167 | col_h10_r0_p1__t1 | pregrt_ff_hold | 3.2 | repair_TNS best 37858.4 last 37858.4 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2175059 | col_h10_r0_p4__t1 | pregrt_ff_hold | 3.1 | repair_TNS best 53228.6 last 53228.6 rows 1 | YOUNG: evidence 1.4 h < 2.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvd8c0565f-1181305 | col_h10_r0_p4__t1 | pregrt_ff_hold | 3.3 | repair_TNS best 53512.7 last 53512.7 rows 1 | YOUNG: evidence 1.7 h < 2.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 5_2_route | 13.0 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-295818 | col_h10_r2__t1 | 4_2_tapbal_grt | 0.4 | last meaningful line 0.0 h ago (61/66 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 5_2_route | 4.0 | last meaningful line 0.0 h ago (264/264 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-268067 | col_h9_r0_p2__t1 | 4_2_tapbal_grt | 1.2 | last meaningful line 0.3 h ago (62/68 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 13.0 | drt_violations best 535484 last 535484 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv8995e794-2664422 | col_h9_r0_p5__t1 | pregrt_ff_hold | 3.8 | repair_TNS best 168816 last 168816 rows 1 | YOUNG: evidence 2.1 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-218289 | col_h9_r0_p5__t1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3116/3116 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 10.2 | last meaningful line 0.5 h ago (292/293 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-317186 | col_h9_r1__t1 | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.5 | last meaningful line 1.8 h ago (61/101 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | pregrt_ff_hold | 1.2 | repair_TNS best 62577.4 last 62577.4 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 47285.9 last 47285.9 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | tt_setup_repair_grt | 4.0 | last meaningful line 0.0 h ago (997/997 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-138946 | col_h9_r2__t1 | 4_2_tapbal_grt | 0.4 | last meaningful line 0.0 h ago (86/86 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 20285.9 last 20285.9 rows 1 | YOUNG: evidence 1.6 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-2945122 | col_h9_r2__t1 | 5_2_route | 3.7 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | tt_setup_repair_grt | 3.8 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | tt_setup_repair_grt | 3.3 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-1926303 | dsdv_slice_c1x_C__t9 | sdc_lint | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-1920080 | dsdv_slice_c3x_C__t1 | 1_1_yosys_canonicalize | 2.4 | last meaningful line 0.8 h ago (133/133 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2186209 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 3.9 | repair_Viol best 122 last 122 rows 5 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | 4_1_cts | 2.5 | last meaningful line 0.2 h ago (39/39 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t11-1456626 | ot_s81sl_leaf__t11 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (78/78 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t32-2058978 | ot_s81sl_leaf__t32 | pregrt_ff_hold | 2.3 | repair_Violations best 5676 last 5676 rows 11 | YOUNG: stage 1.0 h < 1 h |  |
| epyc9 | dpkit-slice_station__t31-407252 | slice_station__t31 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (2189/2189 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__clc8fb2c8c-2653854 | slice_station__t40 | 5_2_route | 3.8 | last meaningful line 0.2 h ago (261/262 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t6__cl54a9ceeb-2644120 | slice_station__t6 | 5_2_route | 3.0 | last meaningful line 0.2 h ago (252/253 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | otc-1865534-29853 | 1865534 | - | 5.3 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | pregrt_ff_hold | 6.8 | repair_TNS best 50339.8 last 50339.8 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | pregrt_ff_hold | 6.7 | repair_TNS best 80867.4 last 80867.4 rows 1 | YOUNG: evidence 1.8 h < 2.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | pregrt_ff_hold | 6.9 | repair_TNS best 86468.6 last 86468.6 rows 1 | YOUNG: evidence 1.9 h < 2.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | 5_2_route | 6.9 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | 5_2_route | 6.8 | last meaningful line 0.1 h ago (263/263 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_2_route | 6.8 | last meaningful line 0.5 h ago (264/265 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 118766 last 118766 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| intel1 | dpkit-coll_ftc-3824626 | coll_ftc | 4_1_cts | 1.4 | last meaningful line 0.2 h ago (6230/6230 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-coll_n-2865002 | coll_n | 5_2_route | 1.7 | last meaningful line 0.2 h ago (245/246 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 20.4 | last meaningful line 1.0 h ago (278/279 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | 4_1_cts | 1.9 | last meaningful line 0.1 h ago (5267/5267 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-4035353 | slw_hc3 | 4_1_cts | 1.3 | last meaningful line 0.2 h ago (6495/6495 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v3-99093 | slw_sc_v3 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (5408/5408 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | otc-2908840-11609 | 2908840 | flow | 1.7 | last meaningful line 0.0 h ago (4175/4175 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i1-3109373 | eco_20261125_050013_1448739-i1 | 5_2_route | 6.7 | drt_violations best 139 last 139 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel1 | prd-eco_20261125_070347_2847958-i1-3642895 | eco_20261125_070347_2847958-i1 | 5_2_route | 4.6 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | prd-eco_20261125_072849_2847456-i1-527377 | eco_20261125_072849_2847456-i1 | 5_2_route | 4.2 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | prd-eco_20261125_082621_46745-i1-2873810 | eco_20261125_082621_46745-i1 | 5_2_route | 3.3 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | so_2200105_ff_6493 | so_2200105_ff_6493 | signoff | 0.4 |  | NO-DATA: empty log |  |
| intel1 | so_2200105_tt_6493 | so_2200105_tt_6493 | signoff | 0.4 |  | NO-DATA: empty log |  |
| intel2 | dpkit-coll_ftm-1730453 | coll_ftm | 5_2_route | 1.7 | drt_violations best 9847 last 9847 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-2159087 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (216/217 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-sle_ctl__cla4f6f12f-1437376 | sle_ctl | 3_1_place_gp_skip_io | 0.5 | overflow best 0.8967 last 0.8967 rows 5 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-3431711 | slice_station__t12 | abstract_exact | 1.2 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (5647/5647 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 24.9 | drt_violations best 232 last 232 rows 44 | before-window best 1499, window best 232 | PROGRESS: drt_violations improved 84.5 % in window |  |
| epyc12 | otc-3501458-13012 | 3501458 | drc_macros_only | 8.4 | last meaningful line 0.1 h ago (670/670 lines) | PROGRESS: log still growing |  |
| epyc12 | otc-351743-16220 | 351743 | hcpg_run | 6.2 | last meaningful line 5.8 h ago (13/13 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 10.0 | drt_violations best 2 last 2 rows 48 | before-window best 156586, window best 2 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | 4_1_cts | 6.3 | last meaningful line 0.3 h ago (11024/11024 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 13.3 | drt_violations best 15877 last 15877 rows 5 | before-window best 456468, window best 15877 | PROGRESS: drt_violations improved 96.5 % in window |  |
| epyc7 | dpkit-slw_su_l0__cl1a1c1f8f-3953315 | slw_su_l0 | 5_1_grt | 1.6 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc8 | dpkit-sle_sc_v3-4131858 | sle_sc_v3 | 5_1_grt | 1.7 | grt_overflow best 0 last 20 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 27.6 | drt_violations best 18 last 18 rows 46 | before-window best 3421, window best 18 | PROGRESS: drt_violations improved 99.5 % in window |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-870318 | col_h9_r0_p3__t1 | 4_2_tapbal_grt | 1.8 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1416748 | col_h9_r0_p6__t1 | 4_2_tapbal_grt | 1.0 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-505890 | col_h9_r1__t1 | 4_1_cts | 0.3 | repair_Violations best 0 last 0 rows 9 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | 4_2_tapbal_grt | 3.9 | repair_Violations best 0 last 0 rows 15 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 14.9 | drt_violations best 553 last 677 rows 28 | before-window best 5145, window best 553 | PROGRESS: drt_violations improved 89.3 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-4131917 | col_h9_r2__t1 | 4_2_tapbal_grt | 0.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-phy__t1-448804 | phy__t1 | 5_1_grt | 1.1 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 5_2_route | 18.7 | drt_violations best 147106 last 147106 rows 1 | before-window best 147106, window best 147106 | PROGRESS: drt_violations: active iteration at 47665 < best completed total 147106 (in-iter |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 5_2_route | 21.2 | drt_violations best 131284 last 131284 rows 1 | before-window best 131284, window best 131284 | PROGRESS: drt_violations: active iteration at 64410 < best completed total 131284 (in-iter |  |
| intel1 | prd-eco_20261123_191853_2879776-i3t-2681077 | eco_20261123_191853_2879776-i3t | 5_2_route | 8.9 | drt_violations best 2583 last 2583 rows 1 | before-window best 2583, window best 2583 | PROGRESS: drt_violations: active iteration at 634 < best completed total 2583 (in-iteratio |  |
| intel1 | prd-eco_20261125_002226_1452841-i1-1093733 | eco_20261125_002226_1452841-i1 | 5_1_grt | 0.8 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | prd-eco_20261125_040243_2843749-i1-851245 | eco_20261125_040243_2843749-i1 | 5_2_route | 7.6 | drt_violations best 457 last 457 rows 1 | before-window best 457, window best 457 | PROGRESS: drt_violations: active iteration at 208 < best completed total 457 (in-iteration |  |
| intel2 | dpkit-kv3_io_ft-2159590 | kv3_io_ft | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
