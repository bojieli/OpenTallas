# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 10:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 3, 'GRT-LABEL': 3, 'YOUNG': 150, 'NO-DATA': 37, 'EXCLUDED': 1, 'PROGRESS': 18}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_hgi_v4-4881 | kv3_hgi_v4 | tt_setup_repair_grt | 6.2 | repair_Violations best 0 last 0 rows 24 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -350.63 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-cbn_q01__cldd6ea846-3439533 | cbn_q01 | 5_1_grt | 3.8 | grt rounds 2 overflow 5:81921 -> 10:75607 | UNSIGNABLE: 5_1_grt.log latest setup WNS -347.34 ps (< -300, gate TT >= -42); job age 3.8 h  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2686622 | col_h10_r0_p4__t1 | pregrt_ff_hold | 5.9 | repair_TNS best 96462.2 last 96462.2 rows 1 | before-window best 96462.2, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | pregrt_ff_hold | 5.9 | repair_TNS best 71771.6 last 71771.6 rows 1 | before-window best 71771.6, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 21.9 | drt_violations best 1 last 1 rows 45 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_hg_v1p3__r838481cd7-1149343 | kv3_hg_v1p3__r838481cd7 | 5_1_grt | 1.0 | grt rounds 2 overflow 5:40256 -> 10:36108 | GRT-LABEL: DESIGN-FAIL: overflow 36108 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_hg_v1p5-1187885 | kv3_hg_v1p5 | 5_1_grt | 1.0 | grt rounds 2 overflow 5:48965 -> 10:43054 | GRT-LABEL: DESIGN-FAIL: overflow 43054 at round 10 > 1000 |  |
| epyc7 | dpkit-cbf_q00_s2-1045407 | cbf_q00_s2 | 5_1_grt | 3.1 | grt rounds 2 overflow 5:87022 -> 10:54031 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-491862 | cbf_q00 | 2_1_floorplan | 0.1 | repair_Viol best 6140 last 6140 rows 980 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-cbf_q00_s2-1666095 | cbf_q00_s2 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-cbf_q01_s2-311731 | cbf_q01_s2 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (1181/1181 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-cbf_q11-488524 | cbf_q11 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (1181/1181 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-cbn_q01__clab6e67f2-1936182 | cbn_q01 | 3_4_place_resized | 0.8 | last meaningful line 0.1 h ago (20/20 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-cbn_q01__cld9ff4c40-769504 | cbn_q01 | 1_synth | 0.1 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-cbn_q11__cl5cc92dfe-3776050 | cbn_q11 | 3_3_place_gp | 0.4 | overflow best 0.196 last 0.196 rows 39 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-cbx_q10__cl89936551-4134347 | cbx_q10 | 3_3_place_gp | 0.3 | overflow best 0.195 last 0.195 rows 34 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-hd_serdes-1677065 | hd_serdes | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-706683 | sle_st_b_v1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (378/378 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-2864357 | sle_st_b_v1 | 3_3_place_gp | 0.6 | overflow best 0.1067 last 0.1067 rows 45 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-sle_stm_v2__cl7b3062fa-3992678 | sle_stm_v2 | 3_3_place_gp | 0.3 | overflow best 0.1966 last 0.1966 rows 37 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-slw_st_b_v1__cle6023ec2-3100899 | slw_st_b_v1 | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (452/452 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-771314 | slw_st_b_v2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (324/324 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_stm_v1__cle34a73c3-3142551 | slw_stm_v1 | 3_3_place_gp | 0.6 | overflow best 0.5118 last 0.5118 rows 4 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-slw_stm_v2__cl1ca9c415-2888579 | slw_stm_v2 | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (368/368 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | eco-abs-3877704 | eco-abs | generate_abstract | 0.4 | last meaningful line 0.3 h ago (29/29 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | otc-4067299-15490 | 4067299 | - | 2.5 |  | NO-DATA: no log found |  |
| epyc10 | otc-4188785-25915 | 4188785 | signoff | 2.5 | last meaningful line 2.3 h ago (3/3 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_174256_3687300-i1-1643366 | eco_20261125_174256_3687300-i1 | 5_1_grt | 0.9 | last meaningful line 0.5 h ago (287/374 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_180222_3379404-i1t-2905775 | eco_20261125_180222_3379404-i1t | 5_1_grt | 0.6 | last meaningful line 0.4 h ago (289/460 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | dpkit-cbn_q00__cl622f65d2-3214950 | cbn_q00 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5475/5475 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-1395551 | col_h9_r0_p5__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 154542 last 154542 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 102568 last 102568 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 201336 last 201336 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-1130830 | col_h9_r0_p5__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 130048 last 130048 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc93af856-1168215 | col_h9_r0_p5__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 24080.8 last 24080.8 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-1072222 | col_h9_r0_p5__t1 | pregrt_ff_hold | 1.6 | repair_TNS best 170995 last 170995 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc11 | dpkit-kv3_hub_Eo-1420436 | kv3_hub_Eo | 5_1_grt | 3.2 | last meaningful line 0.0 h ago (159/159 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Wi-2642655 | kv3_hub_Wi | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Wo-1632470 | kv3_hub_Wo | 5_1_grt | 3.2 | last meaningful line 0.0 h ago (47/47 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_su_c-2149031 | sle_su_c | 5_1_grt | 2.9 | last meaningful line 0.2 h ago (1322/2256 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl19bb38ef-40900 | slw_su_c | 5_1_grt | 3.9 | last meaningful line 0.3 h ago (285/1292 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | otc-1616228-26288 | 1616228 | - | 5.1 |  | NO-DATA: no log found |  |
| epyc11 | otc-2018500-5230 | 2018500 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc11 | otc-381902-2867 | 381902 | - | 9.7 |  | NO-DATA: no log found |  |
| epyc11 | prd-eco_20261124_190641_1260390-i2-3864714 | eco_20261124_190641_1260390-i2 | 5_2_route | 2.2 | last meaningful line 0.2 h ago (284/285 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i2-3847060 | eco_20261124_200101_1087713-i2 | 5_2_route | 2.2 | last meaningful line 0.1 h ago (288/289 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_174711_1456062-i1-2307917 | eco_20261125_174711_1456062-i1 | 5_2_route | 0.9 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | so_3994145_ff_627 | so_3994145_ff_627 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc11 | so_3994145_tt_627 | so_3994145_tt_627 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc12 | dproto-qc-v13-kit | dproto-qc-v13-kit | head.otrun | 0.9 | last meaningful line 0.6 h ago (5/5 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 7.1 |  | NO-DATA: no log found |  |
| epyc12 | otc-1058929-2819 | 1058929 | asbuilt.yosys | 0.6 | last meaningful line 0.0 h ago (243003/243003 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc12 | otc-1151939-895 | 1151939 | asbuilt.yosys | 0.6 | last meaningful line 0.0 h ago (243003/243003 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc12 | otc-1172272-27297 | 1172272 | asbuilt.yosys | 0.5 | last meaningful line 0.0 h ago (229029/229029 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc12 | otc-1267541-535 | 1267541 | flow | 0.5 | last meaningful line 0.0 h ago (2868/2868 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc12 | otc-1460135-77 | 1460135 | - | 6.2 |  | NO-DATA: no log found |  |
| epyc12 | otc-1539240-11776 | 1539240 | asbuilt.yosys | 0.4 | last meaningful line -0.0 h ago (136797/136797 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc12 | otc-1602579-22724 | 1602579 | asbuilt.yosys | 0.3 | last meaningful line 0.0 h ago (137156/137156 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | otc-167973-28965 | 167973 | flow | 1.1 | last meaningful line 0.0 h ago (2954/2954 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc12 | otc-1784815-17268 | 1784815 | asbuilt.yosys | 0.3 | last meaningful line -0.0 h ago (136953/136953 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | otc-1796907-24376 | 1796907 | asbuilt.yosys | 0.2 | last meaningful line 0.0 h ago (136952/136952 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | otc-1994529-22240 | 1994529 | flow | 4.3 | repair_Violations best 97612 last 97612 rows 93 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc12 | otc-351743-16220 | 351743 | hcpg_run | 5.0 | last meaningful line 4.6 h ago (13/13 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc12 | otc-975504-31834 | 975504 | flow | 0.6 | last meaningful line -0.0 h ago (2891/2891 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | adoring_nobel | adoring_nobel | drc | 0.4 | last meaningful line 0.3 h ago (129/129 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | cranky_ganguly | cranky_ganguly | drc | 0.2 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dazzling_diffie | dazzling_diffie | - | 0.7 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | 4_1_cts | 1.6 | last meaningful line 0.0 h ago (6651/6651 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3621669 | slw_fw_v2 | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (396/396 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | elastic_shamir | elastic_shamir | - | 0.3 |  | NO-DATA: no log found |  |
| epyc2 | epic_mclean | epic_mclean | drc | 0.0 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | gifted_germain | gifted_germain | drc | 0.5 | last meaningful line 0.3 h ago (129/129 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | otc-2072908-20868 | 2072908 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc2 | otc-2073510-26058 | 2073510 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc2 | otc-2074501-27593 | 2074501 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc2 | otc-2342049-23133 | 2342049 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc2 | otc-2344331-13980 | 2344331 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc2 | otc-2786014-9554 | 2786014 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261124_204708_4151707-i2-961159 | eco_20261124_204708_4151707-i2 | 5_2_route | 1.9 | last meaningful line 0.1 h ago (281/282 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 5.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 5.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 5.2 |  | NO-DATA: no log found |  |
| epyc2 | sad_wing | sad_wing | drc | 0.4 | last meaningful line 0.3 h ago (129/129 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | serene_blackwell | serene_blackwell | drc | 0.9 | last meaningful line 0.8 h ago (126/126 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | serene_goodall | serene_goodall | drc | 1.4 | last meaningful line 1.3 h ago (124/124 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | upbeat_noyce | upbeat_noyce | drc | 1.4 | last meaningful line 1.3 h ago (121/121 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-coll_ft__cl78c7b300-2883792 | coll_ft | tt_setup_repair_grt | 0.9 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-coll_ftm-2399818 | coll_ftm | 5_1_grt | 1.1 | last meaningful line 0.1 h ago (280/342 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-coll_s-1906595 | coll_s | 5_1_grt | 1.3 | last meaningful line 0.0 h ago (2577/2585 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12e-1804185 | kv3_pv_v12e | 4_1_cts | 2.8 | last meaningful line 0.1 h ago (12085/12085 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | 4_1_cts | 5.3 | last meaningful line 0.3 h ago (11003/11003 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 5_1_grt | 5.0 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | 5_2_route | 12.4 | drt_violations best 177714 last 177714 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 9.2 | last meaningful line 0.5 h ago (273/274 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 9.2 | last meaningful line 0.5 h ago (272/273 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-22145 | sle_sc_v2 | 5_2_route | 3.5 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__clc6d66f5b-2521917 | sle_su_l1 | 6_report | 9.7 | last meaningful line 0.2 h ago (24/24 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v2__cl8537f156-215605 | slw_fw_v2 | 2_1_floorplan | 0.4 | last meaningful line 0.1 h ago (85/85 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-624448 | slw_hc1 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (6736/6736 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-362758 | slw_hc2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5136/5137 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3806800 | slw_hc3 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (5093/5093 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 9.6 | last meaningful line 0.5 h ago (279/280 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l0__cl1a1c1f8f-3953315 | slw_su_l0 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (3642/3642 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 2.4 | drt_violations best 284474 last 284474 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | otc-131491-13694 | 131491 | - | 1.9 |  | NO-DATA: no log found |  |
| epyc7 | otc-2938337-22499 | 2938337 | - | 5.7 |  | NO-DATA: no log found |  |
| epyc7 | otc-3693543-29719 | 3693543 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc7 | otc-639211-10962 | 639211 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc8 | ap-ageom-kw-kv3-sys-SD-grt-2202023 | kv3-sys-SD-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-918588 | col_h10_r0_p1__t1 | 5_1_grt | 6.5 | last meaningful line 0.2 h ago (164/164 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-coll_ft__cla4a25d77-1326788 | coll_ft | 5_2_route | 1.5 | last meaningful line 0.1 h ago (232/232 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-native59-3301533 | native59 | 3_5_place_dp | 2.0 | last meaningful line 0.2 h ago (111/111 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-1199968 | sle_sc_v1 | 3_3_place_gp | 0.4 | overflow best 0.2365 last 0.2365 rows 27 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-sle_sc_v3-4131858 | sle_sc_v3 | 4_1_cts | 0.7 | last meaningful line 0.2 h ago (4009/4009 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-287710 | slw_hc3 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (7049/7049 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-tt_ctlm-548365 | tt_ctlm | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3800/3800 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | otc-1220115-969 | 1220115 | - | 2.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-1288521-5795 | 1288521 | - | 2.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-132122-8685 | 132122 | - | 6.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-1467259-21054 | 1467259 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc8 | otc-1609200-26446 | 1609200 | - | 2.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-1616827-18813 | 1616827 | - | 2.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-1633866-27286 | 1633866 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-192475-3213 | 192475 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-2113939-31863 | 2113939 | - | 2.3 |  | NO-DATA: no log found |  |
| epyc8 | otc-3569473-6282 | 3569473 | - | 2.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-3579536-7216 | 3579536 | - | 1.9 |  | NO-DATA: no log found |  |
| epyc8 | prd-count-p1_bc-1098320 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_123952_3914547-i2-1265285 | eco_20261125_123952_3914547-i2 | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_182230_4100536-i1-1439446 | eco_20261125_182230_4100536-i1 | 5_1_grt | 0.3 | last meaningful line 0.2 h ago (141/141 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | prd-fin-65595 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (66/66 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | so_1500975_ff_22076 | so_1500975_ff_22076 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (35/35 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | so_1500975_tt_22076 | so_1500975_tt_22076 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (35/35 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | tt_setup_repair_grt | 12.0 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3804990 | col_h10_r0_p1__t1 | 4_2_tapbal_grt | 1.0 | last meaningful line 0.0 h ago (62/64 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvc9270d09-1494595 | col_h10_r0_p4__t1 | pregrt_ff_hold | 3.0 | repair_TNS best 113133 last 113133 rows 1 | YOUNG: evidence 1.5 h < 2.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2175059 | col_h10_r0_p4__t1 | pregrt_ff_hold | 2.1 | repair_TNS best 53228.6 last 53228.6 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvd8c0565f-1181305 | col_h10_r0_p4__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 53512.7 last 53512.7 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 5_2_route | 12.0 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-1620868 | col_h10_r2__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 44947.6 last 44947.6 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-268067 | col_h9_r0_p2__t1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3466/3467 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-870318 | col_h9_r0_p3__t1 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (4382/4382 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 12.0 | drt_violations best 535484 last 535484 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv8995e794-2664422 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 168816 last 168816 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | pregrt_ff_hold | 3.0 | repair_TNS best 151565 last 151565 rows 1 | YOUNG: evidence 1.4 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 9.2 | last meaningful line 0.5 h ago (286/287 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-1327698 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.5 | last meaningful line 0.8 h ago (61/84 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.9 | last meaningful line 2.3 h ago (61/106 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-324754 | col_h9_r2__t1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3909/3909 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-3967773 | col_h9_r2__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 47285.9 last 47285.9 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-1434878 | col_h9_r2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 100484 last 100484 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-2945122 | col_h9_r2__t1 | 5_1_grt | 2.7 | last meaningful line 0.0 h ago (182/182 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 41307.4 last 41307.4 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-1920080 | dsdv_slice_c3x_C__t1 | sdc_lint | 1.4 | last meaningful line 1.4 h ago (1/1 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | selrange | 1.5 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-ot_s81sl_leaf__t32-2058978 | ot_s81sl_leaf__t32 | tt_setup_measure | 1.3 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t51-134311 | ot_s81sl_leaf__t51 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t30__cl6a190133-1093777 | slice_station__t30 | 5_2_route | 1.5 | drt_violations best 16518 last 16518 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-slice_station__t40__clc8fb2c8c-2653854 | slice_station__t40 | 5_2_route | 2.8 | last meaningful line 0.2 h ago (247/248 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t46-1382971 | slice_station__t46 | 5_2_route | 1.5 | drt_violations best 4103 last 4103 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-slice_station__t6__cl54a9ceeb-2644120 | slice_station__t6 | 5_2_route | 2.0 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-1865534-29853 | 1865534 | - | 4.3 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 4_2_tapbal_grt | 5.8 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | pregrt_ff_hold | 5.7 | repair_TNS best 80867.4 last 80867.4 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | pregrt_ff_hold | 5.9 | repair_TNS best 86468.6 last 86468.6 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | 5_1_grt | 5.9 | last meaningful line 0.2 h ago (1308/2329 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | tt_setup_repair_grt | 5.8 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | postcts_gate_FF | 5.8 | last meaningful line -0.0 h ago (28765/28765 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-4085689 | col_h9_r2__t1 | pregrt_ff_hold | 0.3 | repair_TNS best 118766 last 118766 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-coll_ftc-3824626 | coll_ftc | 4_1_cts | 0.4 | last meaningful line 0.2 h ago (5835/5835 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-coll_n-2865002 | coll_n | 5_1_grt | 0.7 | last meaningful line 0.0 h ago (1603/1620 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-hd_serdes-2069857 | hd_serdes | 3_1_place_gp_skip_io | 1.0 | overflow best 0.9749 last 0.9749 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-hd_spn-3243487 | hd_spn | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (106/106 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-hd_spn_end-3501292 | hd_spn_end | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 5_2_route | 17.7 | drt_violations best 147106 last 147106 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 6_report | 22.0 | last meaningful line 0.1 h ago (69/69 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 19.4 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2291579 | slw_hc2 | 4_1_cts | 0.9 | last meaningful line 0.2 h ago (5174/5174 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-4035353 | slw_hc3 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (6438/6438 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v3-99093 | slw_sc_v3 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (4974/4974 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 5_2_route | 20.2 | drt_violations best 131284 last 131284 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | otc-2908840-11609 | 2908840 | flow | 0.7 | last meaningful line 0.0 h ago (3900/3900 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | otc-574655-9239 | 574655 | drc_merged | 4.9 | last meaningful line 0.0 h ago (929/929 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | otc-578793-24959 | 578793 | drc_merged | 4.9 | last meaningful line 0.0 h ago (1148/1148 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | otc-582965-3828 | 582965 | drc_merged | 4.9 | last meaningful line 0.0 h ago (1208/1208 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | otc-589045-16647 | 589045 | drc_merged | 4.9 | last meaningful line 0.1 h ago (1310/1310 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i3t-2681077 | eco_20261123_191853_2879776-i3t | 5_2_route | 7.9 | drt_violations best 2583 last 2583 rows 1 | YOUNG: evidence 5.9 h < 7.5 h |  |
| intel1 | prd-eco_20261125_040243_2843749-i1-851245 | eco_20261125_040243_2843749-i1 | 5_2_route | 6.6 | drt_violations best 457 last 457 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i1-3109373 | eco_20261125_050013_1448739-i1 | 5_2_route | 5.7 | drt_violations best 139 last 139 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | prd-eco_20261125_070347_2847958-i1-3642895 | eco_20261125_070347_2847958-i1 | 5_2_route | 3.6 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | prd-eco_20261125_072849_2847456-i1-527377 | eco_20261125_072849_2847456-i1 | 5_2_route | 3.2 | last meaningful line 0.2 h ago (259/260 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | prd-eco_20261125_082621_46745-i1-2873810 | eco_20261125_082621_46745-i1 | 5_2_route | 2.3 | last meaningful line 0.2 h ago (128/128 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | prd-fin-3347319 | fin | 6_report | 0.4 | last meaningful line 0.1 h ago (69/69 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-892840 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5443 last 5443 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3353479 | slw_sc_v1 | 3_3_place_gp | 0.2 | overflow best 0.2168 last 0.2168 rows 23 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | otc-90874-10851 | 90874 | - | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 23.9 | drt_violations best 236 last 236 rows 42 | before-window best 3807, window best 236 | PROGRESS: drt_violations improved 93.8 % in window |  |
| epyc12 | otc-3501458-13012 | 3501458 | drc_parent_only | 7.2 | last meaningful line 0.2 h ago (646/646 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 9.0 | drt_violations best 2 last 2 rows 48 | before-window best 156586, window best 2 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-serdes__t2-2603266 | serdes__t2 | 4_1_cts | 1.0 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 12.3 | drt_violations best 76101 last 76101 rows 3 | before-window best 456468, window best 76101 | PROGRESS: drt_violations improved 83.3 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 26.6 | drt_violations best 18 last 18 rows 44 | before-window best 47086, window best 18 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-1427167 | col_h10_r0_p1__t1 | 4_2_tapbal_grt | 2.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 5_1_grt | 3.0 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | pregrt_ff_hold | 3.0 | repair_Violations best 122337 last 122337 rows 9 | before-window best 482010, window best 122337 | PROGRESS: repair_Violations improved 74.6 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 13.9 | drt_violations best 553 last 2096 rows 26 | before-window best 25498, window best 553 | PROGRESS: drt_violations improved 97.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | 5_2_route | 13.0 | drt_violations best 373 last 373 rows 43 | before-window best 37137, window best 373 | PROGRESS: drt_violations improved 99.0 % in window |  |
| epyc9 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2186209 | dsdv_slice_lepe_nh_mus_LP__t1 | 5_1_grt | 2.9 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-phy__t1-448804 | phy__t1 | 4_1_cts | 0.1 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 23.7 | drt_violations best 4 last 4 rows 53 | before-window best 5, window best 4 | PROGRESS: drt_violations improved 20.0 % in window |  |
| intel2 | dpkit-coll_ftm-1730453 | coll_ftm | 5_1_grt | 0.7 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel2 | dpkit-slice_station__t12-3431711 | slice_station__t12 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
