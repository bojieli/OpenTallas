# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 01:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 6, 'UNSIGNABLE': 7, 'GRT-LABEL': 4, 'YOUNG': 127, 'NO-DATA': 19, 'EXCLUDED': 1, 'PROGRESS': 36}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 16.1 | last meaningful line 14.8 h ago (48/142 lines) | NO-PROGRESS: no new non-iteration log line for 14.8 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 5_1_grt | 16.4 | grt rounds 2 overflow 5:42234 -> 10:42876 | UNSIGNABLE: GRT overflow flat: overflow 42234 at iteration 5 -> 42876 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-2844240 | kv3_pc | 5_1_grt | 5.4 | grt rounds 2 overflow 5:7078 -> 10:4367 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -436.54 ps (< -300, gate TT >= -42); job age 5. | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r8b421e514-2986767 | kv3_pc | tt_setup_repair_grt | 5.4 | repair_Violations best 22 last 22 rows 28 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -915.28 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r882954158-3053902 | kv3_pc | tt_setup_repair_grt | 5.4 | last meaningful line 0.0 h ago (21/21 lines) | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -846.36 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-native59-3384403 | native59 | pregrt_ff_hold | 6.5 | repair_TNS best 40160.3 last 40160.3 rows 1 | before-window best 40160.3, window best 40160.3 | NO-PROGRESS: repair_TNS best 40160.3 vs 40160.3 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (QC-GLUE-IMAGES decides; |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 19.1 | last meaningful line 15.6 h ago (48/212 lines) | NO-PROGRESS: no new non-iteration log line for 15.6 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | 5_1_grt | 13.5 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 11.3 | repair_TNS best 145595 last 145595 rows 1 | before-window best 145595, window best 145595 | NO-PROGRESS: repair_TNS best 145595 vs 145595 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc11 | otc-3389445-25127 | 3389445 | signoff | 8.1 | last meaningful line 8.0 h ago (3/3 lines) | NO-PROGRESS: no new non-iteration log line for 8.0 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 5_1_grt | 18.1 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-cbn_q01__cldd6ea846-1559108 | cbn_q01 | 5_1_grt | 8.2 | grt rounds 2 overflow 5:81921 -> 10:75607 | UNSIGNABLE: 5_1_grt.log latest setup WNS -347.34 ps (< -300, gate TT >= -42); job age 8.2 h  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | otc-120424-12773 | 120424 | signoff | 6.6 | last meaningful line 6.5 h ago (3/3 lines) | NO-PROGRESS: no new non-iteration log line for 6.5 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | 5_1_grt | 11.4 | grt rounds 2 overflow 5:94600 -> 10:59159 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v8-2737550 | kv3_hgi_v8 | 5_1_grt | 6.6 | grt rounds 2 overflow 5:54135 -> 10:40850 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | 5_1_grt | 13.2 | grt rounds 2 overflow 5:34556 -> 10:3532 | GRT-LABEL: DESIGN-FAIL: overflow 3532 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi_v6-102352 | kv3_hgi_v6 | 5_1_grt | 7.3 | grt rounds 2 overflow 5:53849 -> 10:29026 | GRT-LABEL: DESIGN-FAIL: overflow 29026 at round 10 > 1000 |  |
| epyc10 | dpkit-glue-1294589 | glue | postcts_gate_TT | 7.5 | last meaningful line 0.0 h ago (1507/1507 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p2-1802854 | kv3_hg_v1p2 | 5_1_grt | 7.2 | last meaningful line 1.5 h ago (305/1314 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p3__r81da466fe-1840159 | kv3_hg_v1p3__r81da466fe | 5_1_grt | 7.1 | last meaningful line 2.0 h ago (287/1297 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-1535838 | kv3_pv_v12 | 5_1_grt | 5.8 | last meaningful line 0.2 h ago (155/155 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-4187490 | kv3_pv_v3 | pregrt_ff_hold | 4.9 | repair_TNS best 169360 last 169360 rows 1 | YOUNG: evidence 1.0 h < 2.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_2_route | 15.2 | drt_violations best 416066 last 416066 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | 5_2_route | 12.1 | drt_violations best 13130 last 13130 rows 2 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | 5_2_route | 12.5 | drt_violations best 149411 last 149411 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | 5_2_route | 13.0 | drt_violations best 490 last 490 rows 5 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 14.2 | drt_violations best 272423 last 272423 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_2_route | 14.2 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 5_2_route | 14.2 | last meaningful line 0.1 h ago (263/263 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | postcts_gate_TT | 12.8 | last meaningful line 0.2 h ago (408/408 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | 5_2_route | 12.0 | drt_violations best 19575 last 19575 rows 2 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3681869 | slw_st_b_v2 | 5_2_route | 8.5 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | 5_2_route | 10.9 | drt_violations best 18820 last 18820 rows 2 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_055922_2792445-i1-2623359 | eco_20261125_055922_2792445-i1 | 5_2_route | 3.0 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_073109_4058437-i1t-725979 | eco_20261125_073109_4058437-i1t | 5_2_route | 1.4 | last meaningful line 0.1 h ago (134/134 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 15.5 | drt_violations best 84312 last 84312 rows 2 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 5_2_route | 11.1 | drt_violations best 166686 last 166686 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 5_2_route | 12.1 | drt_violations best 16914 last 16914 rows 3 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 5_2_route | 10.8 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2533872 | slw_hc3 | generate_abstract | 9.1 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | 5_1_grt | 5.8 | last meaningful line 0.1 h ago (1188/1205 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl92142dac-2960548 | slw_su_c | 4_1_cts | 2.1 | last meaningful line 0.4 h ago (8435/8435 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc11 | eco-abs-3419890 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 14.5 |  | NO-DATA: no log found |  |
| epyc11 | otc-3195182-24200 | 3195182 | asbuilt.yosys | 0.4 | last meaningful line -0.0 h ago (136098/136098 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | otc-3196606-31436 | 3196606 | asbuilt.yosys | 0.4 | last meaningful line -0.0 h ago (226562/226562 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | otc-3296346-10242 | 3296346 | asbuilt.yosys | 0.4 | last meaningful line -0.0 h ago (136096/136096 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | otc-3324407-6321 | 3324407 | asbuilt.yosys | 0.4 | last meaningful line 0.0 h ago (136057/136057 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | otc-701258-11435 | 701258 | lec | 1.4 | LEC last write 1.4 h ago | YOUNG: evidence 1.4 h < 6 h |  |
| epyc11 | otc-701492-14947 | 701492 | lec | 1.4 | LEC last write 1.4 h ago | YOUNG: evidence 1.4 h < 6 h |  |
| epyc11 | prd-count-p1_tc-1425156 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (1051/1051 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_204246_1187010-i1-249436 | eco_20261124_204246_1187010-i1 | 5_2_route | 6.9 | drt_violations best 1 last 1 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_054540_316017-i1-897106 | eco_20261125_054540_316017-i1 | 5_2_route | 3.2 | last meaningful line 0.1 h ago (280/281 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_080242_341091-i1-2097287 | eco_20261125_080242_341091-i1 | 5_1_grt | 0.9 | last meaningful line 0.1 h ago (295/328 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_080337_31727-i1-2053095 | eco_20261125_080337_31727-i1 | 5_1_grt | 0.9 | last meaningful line 0.0 h ago (289/308 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_082938_54055-i1-3146788 | eco_20261125_082938_54055-i1 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (144/144 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | smp-134918 | smp | - | 0.0 |  | NO-DATA: no log found |  |
| epyc11 | so_1785500_ff_25434 | so_1785500_ff_25434 | generate_abstract | 1.0 | last meaningful line 0.8 h ago (33/33 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | so_1785500_tt_25434 | so_1785500_tt_25434 | generate_abstract | 1.0 | last meaningful line 0.8 h ago (33/33 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | so_2564279_ff_84503 | so_2564279_ff_84503 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc11 | so_2564279_tt_84503 | so_2564279_tt_84503 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc11 | so_3752716_ff_56220 | so_3752716_ff_56220 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (908/908 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | so_3752716_tt_56220 | so_3752716_tt_56220 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (908/908 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1216203 | sle_st_b_v1 | postcts_gate_FF | 5.0 | last meaningful line 0.0 h ago (1017/1017 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-360401 | sle_st_b_v2 | postcts_gate_TT | 4.0 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3668964 | sle_st_b_v2 | 5_2_route | 8.8 | drt_violations best 15426 last 15426 rows 3 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1335192 | slw_st_a_v1 | 3_3_place_gp | 0.1 | last meaningful line 0.0 h ago (83/83 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | kqc-sta_region_nb0_h15_n9_s11_bt3_synth0-453315 | sta_region_nb0_h15_n9_s11_bt3_synth0 | 1_2_yosys | 0.5 | last meaningful line -0.0 h ago (17016/17016 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | kqc-sta_region_nb0_h17_n7_s8_bt3_synth0-454974 | sta_region_nb0_h17_n7_s8_bt3_synth0 | 1_2_yosys | 0.5 | last meaningful line 0.0 h ago (17879/17879 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | kqc-sta_region_nb0_h18_n7_s8_bt3_synth0-454093 | sta_region_nb0_h18_n7_s8_bt3_synth0 | 1_2_yosys | 0.5 | last meaningful line -0.0 h ago (15963/15963 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | otc-2040585-24869 | 2040585 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc2 | otc-2882933-23086 | 2882933 | signoff | 2.7 | last meaningful line 2.6 h ago (3/3 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | otc-3544630-5805 | 3544630 | signoff | 6.2 | last meaningful line 6.1 h ago (3/3 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc2 | otc-785042-5629 | 785042 | - | 1.9 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261124_204708_4151707-i1-226978 | eco_20261124_204708_4151707-i1 | 5_1_grt | 0.6 | last meaningful line 0.3 h ago (297/370 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_230804_491597-i1-1072574 | eco_20261124_230804_491597-i1 | 5_2_route | 1.8 | drt_violations best 28 last 28 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 13.7 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | pregrt_ff_hold | 8.4 | repair_TNS best 260322 last 260322 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | 4_1_cts | 2.6 | last meaningful line 0.1 h ago (5257/5257 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3817081 | sle_st_a_v2 | 5_1_grt | 1.0 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | 6_report | 15.7 | last meaningful line 0.0 h ago (70/70 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 5_2_route | 15.8 | drt_violations best 17 last 17 rows 7 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-577851 | slw_sc_v1 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (4490/4490 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_1_grt | 2.6 | last meaningful line 0.0 h ago (266/268 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-3807127 | slw_su_l1 | 5_2_route | 2.6 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-534954 | slw_su_l1 | tt_setup_repair_grt | 2.2 | repair_Viol best 118 last 118 rows 52 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i2t-2177999 | eco_20261124_192157_3493836-i2t | 5_2_route | 1.6 | last meaningful line 0.1 h ago (264/265 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i2t-915490 | eco_20261124_235631_1843084-i2t | 5_2_route | 2.1 | drt_violations best 1258 last 1258 rows 2 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_073745_2194631-i1-2944509 | eco_20261125_073745_2194631-i1 | 5_2_route | 1.3 | last meaningful line 0.1 h ago (133/133 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_073945_2252980-i1t-3004488 | eco_20261125_073945_2252980-i1t | 5_2_route | 1.3 | last meaningful line 0.1 h ago (129/129 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | so_2070661_ff_89885 | so_2070661_ff_89885 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | so_2070661_tt_89885 | so_2070661_tt_89885 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_2_route | 16.9 | drt_violations best 320246 last 320246 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 6_1_fill | 16.9 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 5_2_route | 16.9 | drt_violations best 129389 last 129389 rows 1 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 5_2_route | 16.9 | drt_violations best 131388 last 131388 rows 1 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 16.9 | last meaningful line 0.5 h ago (276/277 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 5_2_route | 16.9 | drt_violations best 146375 last 146375 rows 1 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc8 | otc-3678186-167 | 3678186 | - | 2.3 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3-32256 | eco_20261123_164145_1995767-i3 | 5_2_route | 5.1 | drt_violations best 16767 last 16767 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_025941_3548303-i1-3306668 | eco_20261125_025941_3548303-i1 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_065854_3885412-i1-521874 | eco_20261125_065854_3885412-i1 | 5_2_route | 2.0 | last meaningful line 0.2 h ago (128/128 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_071225_3873455-i1-1532615 | eco_20261125_071225_3873455-i1 | 5_2_route | 1.7 | last meaningful line 0.2 h ago (127/127 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_082653_3900765-i1-1572735 | eco_20261125_082653_3900765-i1 | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (140/140 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 13.8 |  | NO-DATA: no log found |  |
| epyc8 | so_1547311_ff_10462 | so_1547311_ff_10462 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc8 | so_1547311_tt_10462 | so_1547311_tt_10462 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc9 | ap-ageom-kw-col-h10-r0-p4--t1--pvc9270d09-grt-3719734 | col-h10-r0-p4--t1--pvc9270d09-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pv07945c1e-55623 | col_h10_r0_p4__t1 | lec | 2.8 | LEC last write 0.1 h ago | YOUNG: evidence 2.8 h < 6 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3378330 | col_h9_r0_p1__t1 | tt_setup_repair | 2.3 | repair_Viol best 52 last 52 rows 39 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b-3679007 | col_h9_r0_p3__t1 | 5_1_grt | 2.3 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-296584 | col_h9_r0_p3__t1 | 5_1_grt | 4.8 | last meaningful line 0.0 h ago (154/154 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3698869 | col_h9_r0_p4__t1 | 4_1_cts | 0.1 | last meaningful line -0.0 h ago (3133/3133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 150413 last 150413 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | lec | 4.1 | LEC last write 0.1 h ago | YOUNG: evidence 4.1 h < 6 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-3394850 | col_h9_r2__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 72521.9 last 72521.9 rows 1 | YOUNG: evidence 1.5 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-3707756 | col_h9_r2__t1 | lec | 2.3 | LEC last write 0.2 h ago | YOUNG: evidence 2.3 h < 6 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | postcts_gate_TT | 3.3 | last meaningful line -0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t10-3695203 | dsdv_slice_c1x_C__t10 | 1_1_yosys_canonicalize | 1.3 | last meaningful line 0.2 h ago (136/136 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-578982 | dsdv_slice_c1x_C__t8 | 1_1_yosys_canonicalize | 1.1 | last meaningful line 0.1 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-3691225 | dsdv_slice_c1x_C__t9 | 1_1_yosys_canonicalize | 1.3 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t1-107375 | ot_s81sl_leaf__t1 | 3_3_place_gp | 0.7 | last meaningful line 0.1 h ago (429/429 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t23-3736910 | ot_s81sl_leaf__t23 | 2_1_floorplan | 0.1 | repair_Viol best 1959 last 1959 rows 524 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t25__cl55642d17-3495886 | ot_s81sl_leaf__t25 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (73/73 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t32-3466782 | ot_s81sl_leaf__t32 | 2_1_floorplan | 0.2 | repair_Viol best 1775 last 1775 rows 921 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t36-3727117 | ot_s81sl_leaf__t36 | pregrt_ff_hold | 2.3 | repair_TNS best 713920 last 713920 rows 1 | YOUNG: evidence 1.0 h < 2.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t74-3440768 | ot_s81sl_leaf__t74 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (1054/1054 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-3479533 | slice_station__t37 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3684/3684 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t42__clcf44e680-3472830 | slice_station__t42 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (2898/2898 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t43-3486441 | slice_station__t43 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (3259/3259 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 13.9 | drt_violations best 3669 last 3669 rows 10 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc9 | so_1866284_ff_63309 | so_1866284_ff_63309 | signoff | 1.5 |  | NO-DATA: empty log |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1177242 | kv3_hg_v1p3__r838481cd7 | pregrt_ff_hold | 1.1 | repair_TNS best 208493 last 208493 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 5_2_route | 15.6 | drt_violations best 163425 last 163425 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 5_1_grt | 7.7 | last meaningful line 0.4 h ago (277/980 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | postcts_gate_FF | 12.0 | last meaningful line 0.3 h ago (1186/1186 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_1_grt | 9.4 | last meaningful line 0.1 h ago (2441/2448 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 5_2_route | 10.5 | last meaningful line 0.0 h ago (262/262 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 5_2_route | 11.7 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 5_2_route | 15.6 | drt_violations best 138053 last 138053 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 5_1_grt | 10.2 | last meaningful line 0.0 h ago (1284/1341 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-3090069 | slw_su_l0 | 5_2_route | 9.5 | drt_violations best 51 last 51 rows 7 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | eco-abs-1867199 | eco-abs | generate_abstract | 0.8 | last meaningful line 0.2 h ago (872/872 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 13.8 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 13.8 |  | NO-DATA: no log found |  |
| intel1 | otc-1948440-31269 | 1948440 | flow | 2.5 | last meaningful line 1.5 h ago (1897/1897 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | otc-2098914-19313 | 2098914 | flow | 2.4 | last meaningful line 0.0 h ago (3503/3503 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | otc-4000256-29997 | 4000256 | eq11 | 5.7 | last meaningful line 0.0 h ago (796522/796522 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | otc-4001240-3461 | 4001240 | eq11 | 5.7 | last meaningful line 0.0 h ago (796475/796475 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | prd-eco_20261124_235251_4176465-i1-1838007 | eco_20261124_235251_4176465-i1 | 5_1_grt | 0.8 | last meaningful line 0.1 h ago (285/309 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1t-3347319 | eco_20261125_002226_1452841-i1t | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3587886 | coll_ftm | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (118/118 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v1e-2379368 | kv3_pv_v1e | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (281/281 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v7-2379649 | kv3_pv_v7 | 3_3_place_gp | 0.7 | overflow best 0.207 last 0.207 rows 37 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-kv3_pv_v7e-3092815 | kv3_pv_v7e | 3_1_place_gp_skip_io | 0.4 | overflow best 0.9392 last 0.9392 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-kv3_pv_v8-2379151 | kv3_pv_v8 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v8e-2355447 | kv3_pv_v8e | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pve-3092926 | kv3_pve | 3_3_place_gp | 0.4 | overflow best 0.5714 last 0.5814 rows 17 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-1249478 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 3039 last 3039 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 15.4 | drt_violations best 96187 last 96187 rows 2 | YOUNG: evidence 6.2 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-2390236 | slw_st_b_v1 | 5_2_route | 8.4 | last meaningful line 0.4 h ago (279/280 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | so_4171351_ff_30505 | so_4171351_ff_30505 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_4171351_tt_30505 | so_4171351_tt_30505 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel1 | prd-eco_qcgu_1125-i1-3514577 | eco_qcgu_1125-i1 | 5_1_grt | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | 4_1_cts | 7.6 | last meaningful line 0.3 h ago (11606/11606 lines) | PROGRESS: log still growing |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 27.9 | drt_violations best 14980 last 63558 rows 18 | before-window best 15279, window best 14980 | PROGRESS: drt_violations: falling inside the active iteration (63558 -> 53045) |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 20.2 | drt_violations best 6824 last 6824 rows 15 | before-window best 19783, window best 6824 | PROGRESS: drt_violations improved 65.5 % in window |  |
| epyc2 | prd-eco_20261124_215436_3656110-i1-2033351 | eco_20261124_215436_3656110-i1 | 5_2_route | 3.1 | drt_violations best 0 last 0 rows 4 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-cbf_q00_s2-3518685 | cbf_q00_s2 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 40.6 | drt_violations best 6858 last 6858 rows 21 | before-window best 7726, window best 6858 | PROGRESS: drt_violations improved 11.2 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 25.4 | drt_violations best 2818 last 2818 rows 16 | before-window best 4070, window best 2818 | PROGRESS: drt_violations improved 30.8 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 21.5 | drt_violations best 8422 last 8422 rows 11 | before-window best 116309, window best 8422 | PROGRESS: drt_violations improved 92.8 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 20.2 | drt_violations best 21738 last 21738 rows 6 | before-window best 510309, window best 21738 | PROGRESS: drt_violations improved 95.7 % in window |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 15.6 | drt_violations best 75027 last 75027 rows 4 | before-window best 412199, window best 75027 | PROGRESS: drt_violations improved 81.8 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 20.0 | drt_violations best 13916 last 13916 rows 7 | before-window best 457993, window best 13916 | PROGRESS: drt_violations improved 97.0 % in window |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 25.6 | drt_violations best 62636 last 62636 rows 11 | before-window best 66691, window best 62636 | PROGRESS: drt_violations improved 6.1 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 21.7 | drt_violations best 52514 last 52514 rows 9 | before-window best 59441, window best 52514 | PROGRESS: drt_violations improved 11.7 % in window |  |
| epyc7 | prd-eco_20261125_081621_2016666-i1-599553 | eco_20261125_081621_2016666-i1 | 5_1_grt | 0.6 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 5_2_route | 16.9 | drt_violations best 287 last 287 rows 4 | before-window best 146067, window best 287 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 16.8 | drt_violations best 93397 last 93397 rows 3 | before-window best 478667, window best 93397 | PROGRESS: drt_violations improved 80.5 % in window |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 5_2_route | 16.9 | drt_violations best 12588 last 12588 rows 3 | before-window best 127432, window best 12588 | PROGRESS: drt_violations improved 90.1 % in window |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 5_2_route | 16.9 | drt_violations best 19013 last 19013 rows 2 | before-window best 152943, window best 19013 | PROGRESS: drt_violations improved 87.6 % in window |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 5_2_route | 16.9 | drt_violations best 22164 last 22164 rows 2 | before-window best 138449, window best 22164 | PROGRESS: drt_violations improved 84.0 % in window |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 16.8 | drt_violations best 450083 last 450083 rows 1 | before-window best 450083, window best 450083 | PROGRESS: drt_violations: active iteration at 169515 < best completed total 450083 (in-ite |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 16.8 | drt_violations best 53734 last 53734 rows 5 | before-window best 379431, window best 53734 | PROGRESS: drt_violations improved 85.8 % in window |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 5_2_route | 16.9 | drt_violations best 20955 last 20955 rows 2 | before-window best 141263, window best 20955 | PROGRESS: drt_violations improved 85.2 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 16.9 | drt_violations best 9525 last 9525 rows 15 | before-window best 20520, window best 9525 | PROGRESS: drt_violations improved 53.6 % in window |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | 4_2_tapbal_grt | 2.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 4_2_tapbal_grt | 2.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve0486b40-3725060 | col_h9_r2__t1 | 4_1_cts | 0.1 | repair_Violations best 0 last 0 rows 3 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 13.6 | drt_violations best 1371 last 1577 rows 29 | before-window best 1638, window best 1371 | PROGRESS: drt_violations improved 16.3 % in window |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_2_route | 13.8 | drt_violations best 125492 last 125492 rows 3 | before-window best 474459, window best 125492 | PROGRESS: drt_violations improved 73.6 % in window |  |
| epyc9 | dpkit-slice_station__t21-3663770 | slice_station__t21 | 5_2_route | 2.3 | drt_violations best 0 last 0 rows 8 | PROGRESS: drt_violations reached 0 |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 5_2_route | 20.0 | drt_violations best 317907 last 317907 rows 1 | before-window best 317907, window best 317907 | PROGRESS: drt_violations: active iteration at 202856 < best completed total 317907 (in-ite |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 5_2_route | 13.7 | drt_violations best 144494 last 144494 rows 1 | before-window best 144494, window best 144494 | PROGRESS: drt_violations: active iteration at 46549 < best completed total 144494 (in-iter |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 11.9 | drt_violations best 39 last 39 rows 14 | before-window best 187976, window best 39 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3325358 | slw_fw_v1 | 5_1_grt | 9.4 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 19.9 | drt_violations best 104690 last 104690 rows 2 | before-window best 398476, window best 104690 | PROGRESS: drt_violations improved 73.7 % in window |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 5_2_route | 15.6 | drt_violations best 17734 last 17734 rows 2 | before-window best 125787, window best 17734 | PROGRESS: drt_violations improved 85.9 % in window |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 5_2_route | 15.6 | drt_violations best 11332 last 11332 rows 6 | before-window best 406352, window best 11332 | PROGRESS: drt_violations improved 97.2 % in window |  |
