# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 01:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 4, 'GRT-LABEL': 10, 'YOUNG': 138, 'NO-DATA': 17, 'KEEP': 1, 'EXCLUDED': 1, 'PROGRESS': 40}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_hg_v1p2-1802854 | kv3_hg_v1p2 | 5_1_grt | 7.9 | grt rounds 2 overflow 5:44471 -> 10:45255 | UNSIGNABLE: GRT overflow flat: overflow 44471 at iteration 5 -> 45255 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-native59-3384403 | native59 | pregrt_ff_hold | 7.2 | repair_TNS best 40160.3 last 40160.3 rows 1 | before-window best 40160.3, window best 40160.3 | NO-PROGRESS: repair_TNS best 40160.3 vs 40160.3 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (QC-GLUE-IMAGES decides; |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 12.1 | repair_TNS best 145595 last 145595 rows 1 | before-window best 145595, window best 145595 | NO-PROGRESS: repair_TNS best 145595 vs 145595 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc11 | otc-3389445-25127 | 3389445 | signoff | 8.8 | last meaningful line 8.8 h ago (3/3 lines) | NO-PROGRESS: no new non-iteration log line for 8.8 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc8 | otc-120424-12773 | 120424 | signoff | 7.4 | last meaningful line 7.3 h ago (3/3 lines) | NO-PROGRESS: no new non-iteration log line for 7.3 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_hg_v1p3__r81da466fe-1840159 | kv3_hg_v1p3__r81da466fe | 5_1_grt | 7.9 | grt rounds 2 overflow 5:40256 -> 10:36108 | GRT-LABEL: DESIGN-FAIL: overflow 36108 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | 5_1_grt | 12.2 | grt rounds 2 overflow 5:94600 -> 10:59159 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc11 | dpkit-kv3_pv_v2e-1156839 | kv3_pv_v2e | 5_1_grt | 0.3 | grt rounds 2 overflow 5:54763 -> 10:39326 | GRT-LABEL: DESIGN-FAIL: overflow 39326 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v3ne-1144152 | kv3_pv_v3ne | 5_1_grt | 0.3 | grt rounds 2 overflow 5:47095 -> 10:34560 | GRT-LABEL: DESIGN-FAIL: overflow 34560 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v4-1052719 | kv3_pv_v4 | 5_1_grt | 0.4 | grt rounds 2 overflow 5:93111 -> 10:84388 | GRT-LABEL: DESIGN-FAIL: overflow 84388 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v4e-1100418 | kv3_pv_v4e | 5_1_grt | 0.3 | grt rounds 2 overflow 5:112464 -> 10:88021 | GRT-LABEL: DESIGN-FAIL: overflow 88021 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v6e-864517 | kv3_pv_v6e | 5_1_grt | 0.5 | grt rounds 2 overflow 5:59143 -> 10:37875 | GRT-LABEL: DESIGN-FAIL: overflow 37875 at round 10 > 1000 |  |
| epyc2 | dpkit-kv3_hgi_v8-2737550 | kv3_hgi_v8 | 5_1_grt | 7.3 | grt rounds 2 overflow 5:54135 -> 10:40850 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-3490222 | cbn_q01 | 5_1_grt | 0.2 | grt rounds 2 overflow 5:81921 -> 10:75607 | GRT-LABEL: DESIGN-FAIL: overflow 75607 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi_v6-102352 | kv3_hgi_v6 | 5_1_grt | 8.3 | grt rounds 2 overflow 5:53849 -> 10:29026 | GRT-LABEL: DESIGN-FAIL: overflow 29026 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_hg_v1p5-970860 | kv3_hg_v1p5 | 4_1_cts | 0.1 | last meaningful line 0.1 h ago (86/86 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | pregrt_ff_hold | 8.3 | repair_TNS best 293385 last 293385 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-961899 | kv3_pc_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r884969661-974669 | kv3_pc_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-19761 | kv3_pc_v1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5982/5982 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-1535838 | kv3_pv_v12 | 5_1_grt | 6.5 | last meaningful line 0.5 h ago (268/1273 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-4187490 | kv3_pv_v3 | pregrt_ff_hold | 5.7 | repair_TNS best 169360 last 169360 rows 1 | YOUNG: evidence 1.8 h < 2.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_2_route | 16.0 | drt_violations best 416066 last 416066 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | 5_2_route | 12.8 | drt_violations best 8146 last 8146 rows 3 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | 5_2_route | 13.2 | drt_violations best 149411 last 149411 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 14.9 | drt_violations best 272423 last 272423 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_2_route | 14.9 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 5_2_route | 15.0 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | postcts_gate_TT | 13.6 | last meaningful line -0.0 h ago (74251/74251 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | 6_report | 12.7 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3681869 | slw_st_b_v2 | 5_2_route | 9.2 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | 5_2_route | 11.7 | drt_violations best 449 last 449 rows 4 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_055922_2792445-i1-2623359 | eco_20261125_055922_2792445-i1 | 5_2_route | 3.7 | last meaningful line 0.2 h ago (281/282 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_073109_4058437-i1t-725979 | eco_20261125_073109_4058437-i1t | 5_2_route | 2.2 | last meaningful line 0.1 h ago (271/272 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v4ne-1191938 | kv3_pv_v4ne | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v5-1052229 | kv3_pv_v5 | pregrt_ff_hold | 0.4 | repair_TNS best 169718 last 169718 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc11 | dpkit-kv3_pv_v5e-1092206 | kv3_pv_v5e | pregrt_ff_hold | 0.3 | repair_TNS best 845383 last 845383 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc11 | dpkit-kv3_pv_v7-1078343 | kv3_pv_v7 | pregrt_ff_hold | 0.3 | repair_TNS best 133545 last 133545 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 5_2_route | 11.8 | drt_violations best 166686 last 166686 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 5_2_route | 11.5 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | postcts_gate_TT | 6.5 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl92142dac-2960548 | slw_su_c | 4_1_cts | 2.8 | last meaningful line 0.0 h ago (8520/8520 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc11 | eco-abs-3419890 | eco-abs | generate_abstract | 1.1 | last meaningful line 0.4 h ago (1030/1030 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 15.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-381902-2867 | 381902 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc11 | otc-701258-11435 | 701258 | lec | 2.1 | LEC last write 2.1 h ago | YOUNG: evidence 2.1 h < 6 h |  |
| epyc11 | otc-701492-14947 | 701492 | lec | 2.1 | LEC last write 2.1 h ago | YOUNG: evidence 2.1 h < 6 h |  |
| epyc11 | prd-eco_20261125_054540_316017-i1-897106 | eco_20261125_054540_316017-i1 | 5_2_route | 3.9 | drt_violations best 18 last 18 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_080242_341091-i1-2097287 | eco_20261125_080242_341091-i1 | 5_2_route | 1.6 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_080337_31727-i1-2053095 | eco_20261125_080337_31727-i1 | 5_2_route | 1.6 | last meaningful line 0.1 h ago (127/127 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_082938_54055-i1-3146788 | eco_20261125_082938_54055-i1 | 5_1_grt | 1.2 | last meaningful line 0.4 h ago (295/374 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_092112_274675-i1-1256057 | eco_20261125_092112_274675-i1 | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (143/143 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_092728_2532622-i1-1376598 | eco_20261125_092728_2532622-i1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | prd-fin-1425156 | fin | 6_report | 0.6 | last meaningful line 0.0 h ago (1078/1078 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | prd-fin-249436 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (12/12 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | so_3752716_ff_56220 | so_3752716_ff_56220 | generate_abstract | 1.0 | last meaningful line 0.8 h ago (908/908 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | so_3752716_tt_56220 | so_3752716_tt_56220 | generate_abstract | 1.0 | last meaningful line 0.8 h ago (908/908 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc12 | dpkit-hd_lep0N-914468 | hd_lep0N | 3_1_place_gp_skip_io | 0.2 | overflow best 0.2361 last 0.2361 rows 40 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-kv3_pv_v12-1045687 | kv3_pv_v12 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (1029/1029 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pv_v1n-1216451 | kv3_pv_v1n | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-native59-1179753 | native59 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (442/442 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-sle-st-a-v1--cl67389ecd-grt-3142757 | sle-st-a-v1--cl67389ecd-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-3226126 | sle_hc0 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1216203 | sle_st_b_v1 | 5_2_route | 5.8 | last meaningful line 0.1 h ago (270/270 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-360401 | sle_st_b_v2 | postcts_gate_FF | 4.8 | last meaningful line 0.1 h ago (865/865 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2601551 | slw_st_a_v1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (6112/6112 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | eco-abs-2519923 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.2 h ago (31/31 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | eco-abs-2963317 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.1 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | otc-2040585-24869 | 2040585 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc2 | otc-2864129-1602 | 2864129 | eq15 | 0.2 | last meaningful line 0.0 h ago (574209/574209 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | otc-785042-5629 | 785042 | - | 2.7 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261124_204708_4151707-i1-226978 | eco_20261124_204708_4151707-i1 | 5_2_route | 1.3 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 14.4 |  | NO-DATA: no log found |  |
| epyc2 | so_2928260_ff_72863 | so_2928260_ff_72863 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_2928260_tt_72863 | so_2928260_tt_72863 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-cbf_q00_s2-3518685 | cbf_q00_s2 | pregrt_ff_hold | 3.4 | repair_TNS best 4464.71 last 4464.71 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc7 | dpkit-coll_core-3493022 | coll_core | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (10749/10749 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | pregrt_ff_hold | 9.1 | repair_TNS best 275514 last 275514 rows 1 | YOUNG: evidence 1.4 h < 2.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | 4_1_cts | 3.4 | last meaningful line 0.1 h ago (5265/5265 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5643/5644 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5536/5537 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v3-2521918 | sle_sc_v3 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (3933/3933 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3817081 | sle_st_a_v2 | 5_1_grt | 1.7 | last meaningful line 0.1 h ago (2013/2030 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__clc6d66f5b-2521917 | sle_su_l1 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (3981/3981 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | generate_abstract | 16.5 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-577851 | slw_sc_v1 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (4673/4673 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (5672/5672 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-3807127 | slw_su_l1 | 5_2_route | 3.3 | last meaningful line 0.4 h ago (264/265 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i3-2994934 | eco_20261124_175441_992552-i3 | 5_2_route | 0.4 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i2t-2177999 | eco_20261124_192157_3493836-i2t | 5_2_route | 2.4 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i2-3644612 | eco_20261124_235631_1843084-i2 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (297/1297 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_073745_2194631-i1-2944509 | eco_20261125_073745_2194631-i1 | 5_2_route | 2.1 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_073945_2252980-i1t-3004488 | eco_20261125_073945_2252980-i1t | 5_2_route | 2.1 | drt_violations best 544 last 544 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_081621_2016666-i1-599553 | eco_20261125_081621_2016666-i1 | 5_2_route | 1.4 | last meaningful line 0.2 h ago (132/132 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | so_3546323_ff_14786 | so_3546323_ff_14786 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc7 | so_3546323_tt_14786 | so_3546323_tt_14786 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_2_route | 17.6 | drt_violations best 320246 last 320246 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | generate_abstract | 17.6 | last meaningful line 0.1 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 17.6 | drt_violations best 266434 last 266434 rows 1 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 6_1_fill | 17.6 | last meaningful line -0.0 h ago (9/9 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-3678186-167 | 3678186 | - | 3.0 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3-32256 | eco_20261123_164145_1995767-i3 | 5_2_route | 5.8 | drt_violations best 16767 last 16767 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_025941_3548303-i1-3306668 | eco_20261125_025941_3548303-i1 | 5_1_grt | 0.8 | last meaningful line 0.1 h ago (294/363 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_065854_3885412-i1-521874 | eco_20261125_065854_3885412-i1 | 5_2_route | 2.7 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_071225_3873455-i1-1532615 | eco_20261125_071225_3873455-i1 | 5_2_route | 2.5 | last meaningful line 0.1 h ago (266/267 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_082653_3900765-i1-1572735 | eco_20261125_082653_3900765-i1 | 5_2_route | 1.3 | last meaningful line 0.1 h ago (128/128 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_091937_4000900-i1-378808 | eco_20261125_091937_4000900-i1 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (143/143 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 14.5 |  | NO-DATA: no log found |  |
| epyc8 | so_1571712_ff_42723 | so_1571712_ff_42723 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc8 | so_1571712_tt_42723 | so_1571712_tt_42723 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | ap-ageom-kw-dsdv-slice-lepw-mu-C--t1-grt-4059673 | dsdv-slice-lepw-mu-C--t1-grt | lec | 0.2 | LEC last write 0.2 h ago | YOUNG: evidence 0.2 h < 6 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pv07945c1e-55623 | col_h10_r0_p4__t1 | lec | 3.5 | LEC last write 0.1 h ago | YOUNG: evidence 3.5 h < 6 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | lec | 3.0 | LEC last write 0.0 h ago | YOUNG: evidence 3.0 h < 6 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3378330 | col_h9_r0_p1__t1 | 5_1_grt | 3.1 | last meaningful line 0.5 h ago (273/1277 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b-3679007 | col_h9_r0_p3__t1 | 5_1_grt | 3.0 | last meaningful line 0.3 h ago (274/1281 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-296584 | col_h9_r0_p3__t1 | 5_1_grt | 5.6 | last meaningful line 0.7 h ago (271/1279 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3698869 | col_h9_r0_p4__t1 | 4_2_tapbal_grt | 0.9 | last meaningful line 0.0 h ago (62/70 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | pregrt_ff_hold | 3.0 | repair_TNS best 150413 last 150413 rows 1 | YOUNG: evidence 1.5 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (2919/2919 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-4053150 | col_h9_r1__t1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (4005/4005 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49f0ba38-4029031 | col_h9_r1__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (218/218 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 4.9 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-3707756 | col_h9_r2__t1 | 5_1_grt | 3.0 | last meaningful line 0.1 h ago (1301/2371 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve0486b40-3725060 | col_h9_r2__t1 | pregrt_ff_hold | 0.9 | repair_TNS best 29815.1 last 29815.1 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | 5_2_route | 4.0 | last meaningful line 0.1 h ago (266/267 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t10-3695203 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 2.0 | last meaningful line 0.7 h ago (137/137 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-578982 | dsdv_slice_c1x_C__t8 | 1_1_yosys_canonicalize | 1.9 | last meaningful line 0.8 h ago (129/129 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-3691225 | dsdv_slice_c1x_C__t9 | 1_1_yosys_canonicalize | 2.0 | last meaningful line 0.8 h ago (132/132 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_kv512_C__t1-4058196 | dsdv_slice_kv512_C__t1 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (401/401 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t4-4027540 | ot_s81sl_kv_leaf__t4 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (1422/1422 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t1-107375 | ot_s81sl_leaf__t1 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (119/119 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t23-3736910 | ot_s81sl_leaf__t23 | 3_3_place_gp | 0.9 | overflow best 0.2478 last 0.2478 rows 40 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t25__cl55642d17-3495886 | ot_s81sl_leaf__t25 | lec | 0.9 | LEC last write 0.1 h ago | YOUNG: evidence 0.9 h < 6 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t32-3466782 | ot_s81sl_leaf__t32 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (261/261 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t36-3727117 | ot_s81sl_leaf__t36 | 5_1_grt | 3.0 | last meaningful line 0.2 h ago (264/1269 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | tt_setup_repair_grt | 14.0 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-3479533 | slice_station__t37 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (4101/4101 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t43-3486441 | slice_station__t43 | lec | 0.9 | LEC last write 0.0 h ago | YOUNG: evidence 0.9 h < 6 h |  |
| epyc9 | prd-eco_20261125_090100_666856-i1-787277 | eco_20261125_090100_666856-i1 | 5_1_grt | 0.7 | last meaningful line 0.0 h ago (290/308 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1177242 | kv3_hg_v1p3__r838481cd7 | pregrt_ff_hold | 2.1 | repair_TNS best 208493 last 208493 rows 1 | YOUNG: evidence 2.1 h < 2.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 5_2_route | 16.6 | drt_violations best 163425 last 163425 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | tt_setup_measure_grt | 8.7 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 5_2_route | 13.0 | last meaningful line 0.3 h ago (138/138 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t27-2240821 | slice_station__t27 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t30__cl1653104c-2235281 | slice_station__t30 | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_1_grt | 10.4 | last meaningful line 0.2 h ago (2537/2543 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3325358 | slw_fw_v1 | tt_setup_repair_grt | 10.4 | last meaningful line 0.0 h ago (1614/1614 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 5_2_route | 11.5 | last meaningful line 0.4 h ago (267/268 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 5_2_route | 12.7 | last meaningful line 0.3 h ago (281/282 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 5_2_route | 16.6 | drt_violations best 138053 last 138053 rows 1 | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 5_1_grt | 11.2 | last meaningful line 0.1 h ago (2142/2148 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 14.8 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 14.8 |  | NO-DATA: no log found |  |
| intel1 | otc-2098914-19313 | 2098914 | grt_it0 | 3.4 | last meaningful line 0.5 h ago (31/32 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | prd-eco_20261124_235251_4176465-i1-1838007 | eco_20261124_235251_4176465-i1 | 5_2_route | 1.8 | last meaningful line 0.1 h ago (252/252 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1t-3347319 | eco_20261125_002226_1452841-i1t | 5_1_grt | 1.3 | last meaningful line 0.5 h ago (294/345 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | so_1094763_ff_89367 | so_1094763_ff_89367 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (876/876 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | so_1094763_tt_89367 | so_1094763_tt_89367 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (876/876 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | so_2251454_ff_71744 | so_2251454_ff_71744 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel1 | so_2251454_tt_71744 | so_2251454_tt_71744 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | dpkit-coll_ftm-3587886 | coll_ftm | 5_2_route | 1.0 | last meaningful line -0.0 h ago (222/222 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_lep0N_w-1357897 | hd_lep0N_w | 3_3_place_gp | 0.2 | overflow best 0.64 last 0.64 rows 3 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-1309813 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-862971 | kv3_io_ft | 5_1_grt | 0.4 | last meaningful line 0.1 h ago (243/336 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-705307 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.5 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8e7d31598-707215 | kv3_pc_v1 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.0 h ago (57/57 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v7e-3092815 | kv3_pv_v7e | 3_4_place_resized | 1.2 | last meaningful line 0.0 h ago (299/299 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v1__cl9d029624-1206811 | sle_fw_v1 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-2390236 | slw_st_b_v1 | 5_2_route | 9.1 | drt_violations best 154733 last 154733 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel2 | otc-594090-20209 | 594090 | eq13_out | 0.5 | last meaningful line 0.0 h ago (700135/700135 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-436421 | kv3_hgi_v2 | 5_1_grt | 0.2 |  | KEEP: kv3_hgi_v2__cl2862d491_1124155702	KV-OWN-RSTREACH	combined hgi_v2 ship form (COO |  |
| intel1 | prd-eco_qcgu_1125-i1-3514577 | eco_qcgu_1125-i1 | 5_1_grt | 1.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | 5_2_route | 13.8 | drt_violations best 0 last 0 rows 22 | PROGRESS: drt_violations reached 0 |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 16.2 | drt_violations best 58968 last 58968 rows 3 | before-window best 329677, window best 58968 | PROGRESS: drt_violations improved 82.1 % in window |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 28.7 | drt_violations best 14980 last 63558 rows 18 | before-window best 15279, window best 14980 | PROGRESS: drt_violations: falling inside the active iteration (63558 -> 53045) |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 5_2_route | 12.8 | drt_violations best 18 last 18 rows 16 | before-window best 168194, window best 18 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 21.0 | drt_violations best 6298 last 6298 rows 16 | before-window best 16679, window best 6298 | PROGRESS: drt_violations improved 62.2 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 41.4 | drt_violations best 5806 last 5806 rows 22 | before-window best 7726, window best 5806 | PROGRESS: drt_violations improved 24.9 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 26.1 | drt_violations best 2761 last 13398 rows 18 | before-window best 3524, window best 2761 | PROGRESS: drt_violations improved 21.7 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 22.3 | drt_violations best 6764 last 6764 rows 12 | before-window best 84872, window best 6764 | PROGRESS: drt_violations improved 92.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 20.9 | drt_violations best 20612 last 20612 rows 7 | before-window best 510309, window best 20612 | PROGRESS: drt_violations improved 96.0 % in window |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 16.3 | drt_violations best 71668 last 71668 rows 5 | before-window best 412199, window best 71668 | PROGRESS: drt_violations improved 82.6 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 20.7 | drt_violations best 11873 last 11873 rows 9 | before-window best 457993, window best 11873 | PROGRESS: drt_violations improved 97.4 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_1_grt | 3.3 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 26.3 | drt_violations best 62636 last 62636 rows 11 | before-window best 66691, window best 62636 | PROGRESS: drt_violations improved 6.1 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 22.4 | drt_violations best 51610 last 51610 rows 10 | before-window best 55677, window best 51610 | PROGRESS: drt_violations improved 7.3 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-534954 | slw_su_l1 | tt_setup_repair_grt | 2.9 | repair_Violations best 0 last 0 rows 46 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 5_2_route | 17.6 | drt_violations best 17758 last 17758 rows 2 | before-window best 129389, window best 17758 | PROGRESS: drt_violations improved 86.3 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 17.6 | drt_violations best 35768 last 35768 rows 4 | before-window best 478667, window best 35768 | PROGRESS: drt_violations improved 92.5 % in window |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 5_2_route | 17.6 | drt_violations best 18101 last 18101 rows 2 | before-window best 131388, window best 18101 | PROGRESS: drt_violations improved 86.2 % in window |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 5_2_route | 17.6 | drt_violations best 3 last 3 rows 16 | before-window best 127432, window best 3 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 5_2_route | 17.6 | drt_violations best 25161 last 25161 rows 2 | before-window best 146375, window best 25161 | PROGRESS: drt_violations improved 82.8 % in window |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 5_2_route | 17.6 | drt_violations best 22164 last 22164 rows 2 | before-window best 138449, window best 22164 | PROGRESS: drt_violations improved 84.0 % in window |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 17.6 | drt_violations best 105634 last 105634 rows 2 | before-window best 450083, window best 105634 | PROGRESS: drt_violations improved 76.5 % in window |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 17.5 | drt_violations best 52545 last 52545 rows 6 | before-window best 379431, window best 52545 | PROGRESS: drt_violations improved 86.2 % in window |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 5_2_route | 17.6 | drt_violations best 68 last 68 rows 6 | before-window best 141263, window best 68 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 17.6 | drt_violations best 8666 last 8666 rows 16 | before-window best 20520, window best 8666 | PROGRESS: drt_violations improved 57.8 % in window |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | 4_2_tapbal_grt | 3.0 | repair_Violations best 0 last 0 rows 4 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv31e47bd5-4047516 | col_h9_r2__t1 | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 6 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-3394850 | col_h9_r2__t1 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 14.3 | drt_violations best 1371 last 1548 rows 30 | before-window best 1589, window best 1371 | PROGRESS: drt_violations improved 13.7 % in window |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_2_route | 14.5 | drt_violations best 55115 last 55115 rows 5 | before-window best 474459, window best 55115 | PROGRESS: drt_violations improved 88.4 % in window |  |
| epyc9 | dpkit-slice_station__t42__clcf44e680-3472830 | slice_station__t42 | 5_1_grt | 0.9 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 14.7 | drt_violations best 1221 last 1221 rows 13 | before-window best 274895, window best 1221 | PROGRESS: drt_violations improved 99.6 % in window |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 5_2_route | 21.0 | drt_violations best 317907 last 317907 rows 1 | before-window best 317907, window best 317907 | PROGRESS: drt_violations: active iteration at 141639 < best completed total 317907 (in-ite |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 5_2_route | 14.7 | drt_violations best 21522 last 21522 rows 2 | before-window best 144494, window best 21522 | PROGRESS: drt_violations improved 85.1 % in window |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 12.9 | drt_violations best 38 last 38 rows 15 | before-window best 187976, window best 38 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 20.9 | drt_violations best 104690 last 104690 rows 2 | before-window best 398476, window best 104690 | PROGRESS: drt_violations improved 73.7 % in window |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 5_2_route | 16.6 | drt_violations best 73 last 73 rows 5 | before-window best 125787, window best 73 | PROGRESS: drt_violations improved 99.9 % in window |  |
| intel2 | dpkit-slice_station__t12-1350166 | slice_station__t12 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 16.1 | drt_violations best 68885 last 68885 rows 3 | before-window best 367946, window best 68885 | PROGRESS: drt_violations improved 81.3 % in window |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 5_2_route | 16.3 | drt_violations best 7814 last 7814 rows 9 | before-window best 406352, window best 7814 | PROGRESS: drt_violations improved 98.1 % in window |  |
