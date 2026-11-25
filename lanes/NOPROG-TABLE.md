# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 10:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'GRT-LABEL': 3, 'YOUNG': 130, 'NO-DATA': 47, 'PROGRESS': 26}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2686622 | col_h10_r0_p4__t1 | pregrt_ff_hold | 5.1 | repair_TNS best 96462.2 last 96462.2 rows 1 | before-window best 96462.2, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | pregrt_ff_hold | 5.1 | repair_TNS best 71771.6 last 71771.6 rows 1 | before-window best 71771.6, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 21.1 | drt_violations best 1 last 1 rows 45 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_hgi_v4-4881 | kv3_hgi_v4 | 5_1_grt | 5.5 | grt rounds 2 overflow 5:45451 -> 10:32436 | GRT-LABEL: DESIGN-FAIL: overflow 32436 at round 10 > 1000 |  |
| epyc7 | dpkit-cbf_q00_s2-1045407 | cbf_q00_s2 | 5_1_grt | 2.4 | grt rounds 2 overflow 5:87022 -> 10:54031 | GRT-LABEL: DESIGN-FAIL: overflow 54031 at round 10 > 1000 |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-3439533 | cbn_q01 | 5_1_grt | 3.0 | grt rounds 2 overflow 5:81921 -> 10:75607 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-cbf_q00_s2-1666095 | cbf_q00_s2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (309/309 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-cbn_q01__clab6e67f2-1936182 | cbn_q01 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 293 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-cbn_q01__cldd6ea846-556782 | cbn_q01 | 3_3_place_gp | 0.4 | overflow best 0.18 last 0.18 rows 29 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-cbx_q10__cl94a12200_h-2176517 | cbx_q10 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_serdes-1677065 | hd_serdes | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (280/280 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p3__r838481cd7-1149343 | kv3_hg_v1p3__r838481cd7 | pregrt_ff_hold | 0.3 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.3 h < 2.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p5-1187885 | kv3_hg_v1p5 | hold_gate | 0.3 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_sc_v1__cl115da35f-3373545 | sle_sc_v1 | 3_3_place_gp | 0.7 | overflow best 0.1594 last 0.1981 rows 37 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v2__clfde1249e-468252 | sle_st_b_v2 | 1_2_yosys | 0.4 | last meaningful line 0.1 h ago (3603/3603 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc2__cla3497502__cl16607c7a-471253 | slw_hc2 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.6747 last 0.6747 rows 34 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slw_stm_v2__cl9beb65e6-1414288 | slw_stm_v2 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (617/617 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-4067299-15490 | 4067299 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc10 | otc-4188785-25915 | 4188785 | signoff | 1.7 | last meaningful line 1.6 h ago (3/3 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_174256_3687300-i1-1643366 | eco_20261125_174256_3687300-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-fin-634237 | fin | 6_report | 0.8 | last meaningful line 0.8 h ago (21/21 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | so_585369_ff_76703 | so_585369_ff_76703 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc10 | so_585369_tt_76703 | so_585369_tt_76703 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc11 | dpkit-cbn_q00__cl622f65d2-1341377 | cbn_q00 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | tt_setup_repair | 0.8 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-1130830 | col_h9_r0_p5__t1 | pregrt_ff_hold | 0.8 | repair_TNS best 130048 last 130048 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-1072222 | col_h9_r0_p5__t1 | tt_setup_repair | 0.8 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Eo-1420436 | kv3_hub_Eo | tt_setup_measure | 2.5 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Wo-1632470 | kv3_hub_Wo | 4_1_cts | 2.4 | last meaningful line 0.0 h ago (10914/10914 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | generate_abstract | 24.5 | last meaningful line 0.1 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-sle_su_c-2149031 | sle_su_c | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (157/157 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | otc-1109607-10581 | 1109607 | - | 2.6 |  | NO-DATA: no log found |  |
| epyc11 | otc-1616228-26288 | 1616228 | - | 4.4 |  | NO-DATA: no log found |  |
| epyc11 | otc-2018500-5230 | 2018500 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc11 | otc-2255400-11827 | 2255400 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc11 | otc-381902-2867 | 381902 | - | 8.9 |  | NO-DATA: no log found |  |
| epyc11 | otc-608716-5618 | 608716 | signoff | 2.8 | last meaningful line 2.8 h ago (3/3 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i2-3864714 | eco_20261124_190641_1260390-i2 | 5_2_route | 1.4 | last meaningful line 0.0 h ago (271/271 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i2-3847060 | eco_20261124_200101_1087713-i2 | 5_2_route | 1.4 | last meaningful line 0.1 h ago (271/271 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_174711_1456062-i1-2307917 | eco_20261125_174711_1456062-i1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | dproto-head-otclk-537771 | dproto-head-otclk | - | 0.1 |  | NO-DATA: no log found |  |
| epyc12 | dproto-kv-a5t8-kit | dproto-kv-a5t8-kit | kv_proto | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dproto-qc-v13-kit | dproto-qc-v13-kit | kv_proto | 0.1 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 6.4 |  | NO-DATA: no log found |  |
| epyc12 | otc-106625-31299 | 106625 | asbuilt.yosys | 0.4 | last meaningful line 0.0 h ago (229029/229029 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc12 | otc-1460135-77 | 1460135 | - | 5.5 |  | NO-DATA: no log found |  |
| epyc12 | otc-167973-28965 | 167973 | flow | 0.3 | last meaningful line 0.0 h ago (2705/2705 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | otc-1994529-22240 | 1994529 | flow | 3.5 | repair_Violations best 108012 last 108012 rows 68 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc12 | otc-351743-16220 | 351743 | hcpg_run | 4.2 | last meaningful line 3.8 h ago (13/13 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc12 | otc-444940-4599 | 444940 | asbuilt.yosys | 0.2 | last meaningful line 0.0 h ago (136374/136374 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | otc-728270-17256 | 728270 | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (11/11 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | otc-757963-1895 | 757963 | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (11/11 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | busy_haibt | busy_haibt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | determined_yalow | determined_yalow | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (6284/6284 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 8.2 | drt_violations best 2 last 2 rows 48 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc2 | eager_blackburn | eager_blackburn | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | focused_joliot | focused_joliot | - | 0.7 |  | NO-DATA: no log found |  |
| epyc2 | interesting_raman | interesting_raman | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | otc-2072908-20868 | 2072908 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc2 | otc-2073510-26058 | 2073510 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc2 | otc-2074501-27593 | 2074501 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc2 | otc-2342049-23133 | 2342049 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc2 | otc-2344331-13980 | 2344331 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc2 | otc-2786014-9554 | 2786014 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261124_204708_4151707-i2-961159 | eco_20261124_204708_4151707-i2 | 5_2_route | 1.1 | last meaningful line 0.0 h ago (268/268 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 4.4 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 4.4 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 4.4 |  | NO-DATA: no log found |  |
| epyc2 | quizzical_benz | quizzical_benz | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | serene_blackwell | serene_blackwell | drc | 0.2 | last meaningful line 0.2 h ago (126/126 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | serene_goodall | serene_goodall | drc | 0.6 | last meaningful line 0.5 h ago (124/124 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | trusting_darwin | trusting_darwin | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | upbeat_noyce | upbeat_noyce | drc | 0.7 | last meaningful line 0.5 h ago (121/121 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-coll_ft__cl78c7b300-2883792 | coll_ft | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (1597/1597 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-coll_ftm-2399818 | coll_ftm | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (2872/2872 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-coll_s-1906595 | coll_s | pregrt_ff_hold | 0.5 | repair_TNS best 2752.34 last 2752.34 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-hd_mesh-2555655 | hd_mesh | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (6032/6032 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12e-1804185 | kv3_pv_v12e | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (12004/12004 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | 4_1_cts | 4.5 | last meaningful line 0.2 h ago (11000/11000 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | pregrt_ff_hold | 4.3 | repair_TNS best 41652.6 last 41652.6 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | 5_2_route | 11.6 | drt_violations best 177714 last 177714 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 8.5 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 8.5 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-22145 | sle_sc_v2 | 5_2_route | 2.7 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 8.9 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 1.7 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | otc-131491-13694 | 131491 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc7 | otc-2748052-9004 | 2748052 | asbuilt.yosys | 0.2 | last meaningful line 0.2 h ago (369/369 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | otc-2858837-8104 | 2858837 | - | 3.3 |  | NO-DATA: no log found |  |
| epyc7 | otc-2938337-22499 | 2938337 | - | 5.0 |  | NO-DATA: no log found |  |
| epyc7 | otc-3693543-29719 | 3693543 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc7 | otc-639211-10962 | 639211 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-sle-sc-v1--cl7479a5ec-grt-3763334 | sle-sc-v1--cl7479a5ec-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-sle-sc-v3-grt-3716879 | sle-sc-v3-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-coll_ftn-1310614 | coll_ftn | 5_2_route | 0.8 | drt_violations best 5718 last 5718 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-kv3_sys_SD-513287 | kv3_sys_SD | tt_setup_repair_grt | 0.9 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-native59-3301533 | native59 | 3_3_place_gp | 1.3 | overflow best 0.1975 last 0.1975 rows 175 | YOUNG: stage 0.6 h < 1 h |  |
| epyc8 | dpkit-sle_sc_v1__cl115da35f-2926018 | sle_sc_v1 | 3_4_place_resized | 1.4 | last meaningful line 0.0 h ago (380/380 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2782083 | slw_sc_v1 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-1112114 | slw_sc_v1 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (397/397 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | eco-abs-2360458 | eco-abs | generate_abstract | 0.4 | last meaningful line 0.3 h ago (29/29 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | otc-1220115-969 | 1220115 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-1288521-5795 | 1288521 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-132122-8685 | 132122 | - | 6.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-1609200-26446 | 1609200 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc8 | otc-1616827-18813 | 1616827 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc8 | otc-1633866-27286 | 1633866 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc8 | otc-2113939-31863 | 2113939 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-3569473-6282 | 3569473 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-3579536-7216 | 3579536 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc8 | prd-count-p1_tc-65595 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_025941_3548303-i2-1098320 | eco_20261125_025941_3548303-i2 | 5_2_route | 1.9 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | so_1616094_ff_83410 | so_1616094_ff_83410 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc8 | so_1616094_tt_83410 | so_1616094_tt_83410 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc8 | so_3257503_ff_52185 | so_3257503_ff_52185 | generate_abstract | 1.3 | last meaningful line 1.3 h ago (35/35 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | so_3260279_ff_68275 | so_3260279_ff_68275 | generate_abstract | 1.3 | last meaningful line 1.3 h ago (33/33 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | so_811441_ff_11512 | so_811441_ff_11512 | generate_abstract | 0.9 | last meaningful line 0.8 h ago (35/35 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | so_811441_tt_11512 | so_811441_tt_11512 | generate_abstract | 0.9 | last meaningful line 0.8 h ago (35/35 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-col-h9-r2--t1--clce45cab5--pvfb42a1ad-grt-932424 | col-h9-r2--t1--clce45cab5--pvfb42a1ad-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3804990 | col_h10_r0_p1__t1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3558/3558 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-1427167 | col_h10_r0_p1__t1 | 4_2_tapbal_grt | 1.5 | last meaningful line 0.5 h ago (62/71 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvc9270d09-1494595 | col_h10_r0_p4__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 113133 last 113133 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | postcts_gate_FF | 11.3 | last meaningful line 0.0 h ago (564/564 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-870318 | col_h9_r0_p3__t1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (58/58 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3698869 | col_h9_r0_p4__t1 | 5_2_route | 9.1 | last meaningful line 0.1 h ago (288/289 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 11.3 | last meaningful line 0.5 h ago (295/296 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv8995e794-2664422 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 168816 last 168816 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 151565 last 151565 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 8.4 | last meaningful line 0.5 h ago (282/283 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 4_2_tapbal_grt | 0.7 | last meaningful line 0.1 h ago (61/67 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-4115290 | col_h9_r1__t1 | 3_3_place_gp | 0.2 | overflow best 0.5451 last 0.5451 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.2 | last meaningful line 1.5 h ago (61/98 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | 4_1_cts | 0.2 | last meaningful line -0.0 h ago (3956/3956 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | pregrt_ff_hold | 2.2 | repair_TNS best 89205.9 last 89205.9 rows 1 | YOUNG: evidence 1.4 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-2945122 | col_h9_r2__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 2951.73 last 2951.73 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | pregrt_ff_hold | 2.1 | repair_TNS best 61797 last 61797 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 51854.9 last 51854.9 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 4_2_tapbal_grt | 0.8 | repair_Violations best 4 last 15 rows 11 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-1920080 | dsdv_slice_c3x_C__t1 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2186209 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 2.1 | last meaningful line 0.2 h ago (1289/2217 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t32-2058978 | ot_s81sl_leaf__t32 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (4667/4667 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t51-134311 | ot_s81sl_leaf__t51 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (1191/1191 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t30__cl6a190133-1093777 | slice_station__t30 | 5_2_route | 0.8 | last meaningful line 0.0 h ago (66/66 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-3479533 | slice_station__t37 | generate_abstract | 9.2 | last meaningful line 0.3 h ago (27/27 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__clc8fb2c8c-2653854 | slice_station__t40 | postcts_gate_FF | 2.0 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t41-1123489 | slice_station__t41 | 5_1_grt | 2.3 | last meaningful line 0.2 h ago (1274/1680 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t46-1382971 | slice_station__t46 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t6__cl54a9ceeb-2644120 | slice_station__t6 | 5_1_grt | 1.2 | last meaningful line 0.1 h ago (553/577 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | otc-1865534-29853 | 1865534 | - | 3.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-187108-19499 | 187108 | signoff | 0.2 | last meaningful line 0.2 h ago (3/3 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-473645-26540 | 473645 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | ap-ageom-kw-slw-sc-v3-grt-2447914 | slw-sc-v3-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (122/122 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 4_2_tapbal_grt | 5.0 | last meaningful line 4.3 h ago (61/108 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | pregrt_ff_hold | 5.0 | repair_TNS best 80867.4 last 80867.4 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | pregrt_ff_hold | 5.1 | repair_TNS best 86468.6 last 86468.6 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | 5_1_grt | 5.2 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-hd_serdes-2069857 | hd_serdes | 1_2_yosys | 0.2 | last meaningful line 0.1 h ago (280/280 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 5_2_route | 17.0 | drt_violations best 147106 last 147106 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t27-4040446 | slice_station__t27 | 5_2_route | 6.9 | last meaningful line 0.3 h ago (263/264 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 18.7 | last meaningful line 0.3 h ago (272/273 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 5_2_route | 19.4 | drt_violations best 131284 last 131284 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | otc-2370646-23107 | 2370646 | flow | 0.1 | last meaningful line 0.0 h ago (636/636 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-574655-9239 | 574655 | drc_merged | 4.1 | last meaningful line 0.0 h ago (602/602 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | otc-578793-24959 | 578793 | drc_merged | 4.1 | last meaningful line 0.1 h ago (689/689 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | otc-582965-3828 | 582965 | drc_merged | 4.1 | last meaningful line 0.0 h ago (704/704 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | otc-586189-14994 | 586189 | drc_merged | 4.1 | last meaningful line 0.0 h ago (878/878 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | otc-589045-16647 | 589045 | drc_merged | 4.1 | last meaningful line 0.0 h ago (812/812 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i3t-2681077 | eco_20261123_191853_2879776-i3t | 5_2_route | 7.2 | drt_violations best 2583 last 2583 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1t-3347319 | eco_20261125_002226_1452841-i1t | 5_3_fillcell | 9.6 | last meaningful line 0.0 h ago (13/13 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco_20261125_040243_2843749-i1-851245 | eco_20261125_040243_2843749-i1 | 5_2_route | 5.9 | drt_violations best 457 last 457 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i1-3109373 | eco_20261125_050013_1448739-i1 | 5_2_route | 4.9 | last meaningful line 0.5 h ago (276/277 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | prd-eco_20261125_070347_2847958-i1-3642895 | eco_20261125_070347_2847958-i1 | 5_2_route | 2.9 | last meaningful line 0.3 h ago (133/133 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | prd-eco_20261125_072849_2847456-i1-527377 | eco_20261125_072849_2847456-i1 | 5_2_route | 2.5 | last meaningful line 0.1 h ago (127/127 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | prd-eco_20261125_082621_46745-i1-2873810 | eco_20261125_082621_46745-i1 | 5_1_grt | 1.5 | last meaningful line 0.6 h ago (292/602 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | so_2067287_ff_39738 | so_2067287_ff_39738 | generate_abstract | 1.8 | last meaningful line 1.8 h ago (34/34 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | so_2067287_tt_39738 | so_2067287_tt_39738 | generate_abstract | 1.8 | last meaningful line 1.8 h ago (34/34 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-coll_ftc-2805680 | coll_ftc | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-891904 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-2473457 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 2986 last 2986 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-520706 | slw_fe_v1 | 3_3_place_gp | 0.4 | overflow best 0.4719 last 0.4719 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 23.2 | drt_violations best 251 last 251 rows 39 | before-window best 7671, window best 251 | PROGRESS: drt_violations improved 96.7 % in window |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-1395551 | col_h9_r0_p5__t1 | 4_2_tapbal_grt | 0.6 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 4_2_tapbal_grt | 0.8 | repair_Violations best 0 last 0 rows 17 | PROGRESS: repair_Violations reached 0 |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc93af856-1168215 | col_h9_r0_p5__t1 | 4_2_tapbal_grt | 0.8 | repair_Violations best 0 last 0 rows 14 | PROGRESS: repair_Violations reached 0 |  |
| epyc11 | dpkit-slw_su_c__cl19bb38ef-40900 | slw_su_c | pregrt_ff_hold | 3.1 | repair_Violations best 0 last 0 rows 19 | PROGRESS: repair_Violations reached 0 |  |
| epyc12 | otc-3501458-13012 | 3501458 | drc_merged | 6.4 | last meaningful line 3.3 h ago (334/334 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-serdes__t2-2603266 | serdes__t2 | 4_1_cts | 0.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-sle_su_l1__clc6d66f5b-2521917 | sle_su_l1 | 5_2_route | 8.9 | drt_violations best 0 last 0 rows 28 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 11.6 | drt_violations best 105054 last 105054 rows 2 | before-window best 456468, window best 105054 | PROGRESS: drt_violations improved 77.0 % in window |  |
| epyc8 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-918588 | col_h10_r0_p1__t1 | pregrt_ff_hold | 5.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc8 | dpkit-coll_ft__cla4a25d77-1326788 | coll_ft | 5_1_grt | 0.7 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 25.9 | drt_violations best 22 last 22 rows 43 | before-window best 65063, window best 22 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | 5_1_grt | 11.3 | repair_TNS best 0 last 0 rows 28 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2175059 | col_h10_r0_p4__t1 | 4_2_tapbal_grt | 1.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvd8c0565f-1181305 | col_h10_r0_p4__t1 | tt_setup_repair | 1.5 | repair_Violations best 0 last 0 rows 15 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | 4_2_tapbal_grt | 0.7 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 13.1 | drt_violations best 611 last 611 rows 23 | before-window best 162909, window best 611 | PROGRESS: drt_violations improved 99.6 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | 4_2_tapbal_grt | 0.7 | repair_Violations best 0 last 0 rows 3 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | 5_2_route | 12.3 | drt_violations best 375 last 377 rows 37 | before-window best 163283, window best 375 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-slice_station__t52-2620358 | slice_station__t52 | 5_2_route | 7.9 | drt_violations best 0 last 0 rows 7 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 22.9 | drt_violations best 4 last 4 rows 53 | before-window best 6, window best 4 | PROGRESS: drt_violations improved 33.3 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | 5_1_grt | 5.0 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_1_grt | 5.0 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 5_2_route | 21.2 | drt_violations best 13906 last 13906 rows 3 | before-window best 138407, window best 13906 | PROGRESS: drt_violations improved 90.0 % in window |  |
| intel2 | dpkit-kv3_io_ft-892840 | kv3_io_ft | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
