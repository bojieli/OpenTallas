# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 23:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'UNSIGNABLE': 3, 'GRT-LABEL': 12, 'NO-DATA': 34, 'YOUNG': 136, 'KEEP': 1, 'PROGRESS': 25}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 14.6 | last meaningful line 13.3 h ago (48/141 lines) | NO-PROGRESS: no new non-iteration log line for 13.3 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 5_1_grt | 14.9 | grt rounds 2 overflow 5:42234 -> 10:42876 | UNSIGNABLE: GRT overflow flat: overflow 42234 at iteration 5 -> 42876 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 17.6 | last meaningful line 14.1 h ago (48/209 lines) | NO-PROGRESS: no new non-iteration log line for 14.1 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | 5_1_grt | 12.0 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 9.8 | repair_TNS best 121785 last 121785 rows 1 | before-window best 121785, window best 121785 | NO-PROGRESS: repair_TNS best 121785 vs 121785 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc11 | otc-3389445-25127 | 3389445 | signoff | 6.6 | last meaningful line 6.5 h ago (3/3 lines) | NO-PROGRESS: no new non-iteration log line for 6.5 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 5_1_grt | 16.6 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_hg_v1__r889141819-1619104 | kv3_hg_v1__r889141819 | 5_1_grt | 5.8 | grt rounds 1 overflow 5:43060 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_hg_v1__r88f4bfb40-1671162 | kv3_hg_v1__r88f4bfb40 | 5_1_grt | 5.7 | grt rounds 1 overflow 5:42362 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-2844240 | kv3_pc | 5_1_grt | 3.9 | grt rounds 2 overflow 5:7078 -> 10:4367 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r8b421e514-2986767 | kv3_pc | 5_1_grt | 3.9 | grt rounds 2 overflow 5:7207 -> 10:4296 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r85c02c25c-3151820 | kv3_pc | 5_1_grt | 3.8 | grt rounds 2 overflow 5:7303 -> 10:4851 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r882954158-3053902 | kv3_pc | 5_1_grt | 3.9 | grt rounds 2 overflow 5:6934 -> 10:4576 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | 5_1_grt | 9.9 | grt rounds 2 overflow 5:94600 -> 10:59159 | GRT-LABEL: DESIGN-FAIL: overflow 59159 at round 10 > 1000 |  |
| epyc2 | dpkit-kv3_hgi_v8-2737550 | kv3_hgi_v8 | 5_1_grt | 5.1 | grt rounds 2 overflow 5:54135 -> 10:40850 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-1559108 | cbn_q01 | 5_1_grt | 6.7 | grt rounds 2 overflow 5:81921 -> 10:75607 | GRT-LABEL: DESIGN-FAIL: overflow 75607 at round 10 > 1000 |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | 5_1_grt | 11.7 | grt rounds 2 overflow 5:34556 -> 10:3532 | GRT-LABEL: DESIGN-FAIL: overflow 3532 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi_v6-102352 | kv3_hgi_v6 | 5_1_grt | 5.8 | grt rounds 2 overflow 5:53849 -> 10:29026 | GRT-LABEL: DESIGN-FAIL: overflow 29026 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v2__cle0015330-3208477 | kv3_hgi_v2 | 5_1_grt | 2.2 | grt rounds 2 overflow 5:8261 -> 10:2784 | GRT-LABEL: DESIGN-FAIL: overflow 2784 at round 10 > 1000 |  |
| epyc10 | ap-ageom-kw-kv3-hg-v1p5-grt-3902699 | kv3-hg-v1p5-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc10 | ap-ageom-kw-kv3-pc-v1--cl4ea58a5c--r8ef700d7c-grt-3912917 | kv3-pc-v1--cl4ea58a5c--r8ef700d7c-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-glue-1294589 | glue | 5_1_grt | 6.0 | last meaningful line 0.2 h ago (945/958 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r8dffc461a-1676050 | kv3_hg_v1__r8dffc461a | 5_1_grt | 5.7 | last meaningful line 1.0 h ago (287/1295 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p2-1802854 | kv3_hg_v1p2 | 5_1_grt | 5.7 | last meaningful line 0.1 h ago (305/306 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p3__r81da466fe-1840159 | kv3_hg_v1p3__r81da466fe | 5_1_grt | 5.6 | last meaningful line 0.5 h ago (287/1292 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | 4_1_cts | 6.1 | last meaningful line 0.8 h ago (11296/11296 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-3561929 | kv3_pc_v1 | 3_5_place_dp | 3.7 | last meaningful line 0.1 h ago (115/115 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r84d0332e1-3581607 | kv3_pc_v1 | 3_5_place_dp | 3.7 | last meaningful line 1.5 h ago (32/32 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r884969661-3601103 | kv3_pc_v1 | 3_5_place_dp | 3.6 | last meaningful line 1.5 h ago (32/32 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8afe1e027-3618066 | kv3_pc_v1 | 3_5_place_dp | 3.6 | last meaningful line 0.0 h ago (115/115 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-1535838 | kv3_pv_v12 | pregrt_ff_hold | 4.3 | repair_TNS best 42717.5 last 42717.5 rows 1 | YOUNG: evidence 1.9 h < 2.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-4187490 | kv3_pv_v3 | 4_1_cts | 3.4 | last meaningful line 0.1 h ago (12095/12095 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_2_route | 13.7 | last meaningful line 0.8 h ago (274/275 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | 5_2_route | 10.6 | drt_violations best 104126 last 104126 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | 5_2_route | 11.0 | last meaningful line 0.2 h ago (285/286 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | 5_2_route | 11.5 | drt_violations best 127354 last 127354 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 12.7 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_2_route | 12.7 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | postcts_gate_FF | 12.7 | last meaningful line 0.2 h ago (1662/1662 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | 5_1_grt | 11.3 | last meaningful line 0.3 h ago (288/1041 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | 5_2_route | 10.5 | drt_violations best 138401 last 138401 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3681869 | slw_st_b_v2 | postcts_gate_FF | 7.0 | last meaningful line 0.1 h ago (1056/1056 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | 5_2_route | 9.4 | drt_violations best 130780 last 130780 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_055922_2792445-i1-2623359 | eco_20261125_055922_2792445-i1 | 5_2_route | 1.5 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | qc-hc3-lec-r8-nearest | qc-hc3-lec-r8-nearest | - | 8.5 |  | NO-DATA: no log found |  |
| epyc10 | qccollslec_h4 | qccollslec_h4 | - | 3.5 |  | NO-DATA: no log found |  |
| epyc10 | smp-410402 | smp | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | so_1909583_ff_45461 | so_1909583_ff_45461 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc10 | so_1909583_tt_45461 | so_1909583_tt_45461 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 14.0 | drt_violations best 329677 last 329677 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 5_2_route | 9.6 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 5_2_route | 10.6 | drt_violations best 168194 last 168194 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | postcts_gate_FF | 9.3 | last meaningful line -0.0 h ago (77544/77544 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2533872 | slw_hc3 | 5_2_route | 7.6 | drt_violations best 87718 last 87718 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | 5_1_grt | 4.3 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl92142dac-2960548 | slw_su_c | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (8304/8304 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 13.0 |  | NO-DATA: no log found |  |
| epyc11 | prd-eco_20261124_154417_1016084-i2t-1425156 | eco_20261124_154417_1016084-i2t | 5_2_route | 4.3 | drt_violations best 917 last 917 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i1-3660942 | eco_20261124_200101_1087713-i1 | 5_2_route | 6.3 | drt_violations best 37 last 37 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_204246_1187010-i1-249436 | eco_20261124_204246_1187010-i1 | 5_2_route | 5.4 | drt_violations best 1 last 1 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_054540_316017-i1-897106 | eco_20261125_054540_316017-i1 | 5_2_route | 1.7 | last meaningful line 0.2 h ago (133/133 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | prd-fin-2214083 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | prd-fin-3176761 | fin | 6_report | 0.4 | last meaningful line 0.1 h ago (942/942 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | so_3098882_ff_50641 | so_3098882_ff_50641 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc11 | so_3098882_tt_50641 | so_3098882_tt_50641 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc11 | so_3632485_ff_17702 | so_3632485_ff_17702 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc11 | so_3632485_tt_17702 | so_3632485_tt_17702 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc11 | so_428963_ff_46412 | so_428963_ff_46412 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc11 | so_428963_tt_46412 | so_428963_tt_46412 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1216203 | sle_st_b_v1 | 5_1_grt | 3.5 | last meaningful line 0.2 h ago (293/1103 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-360401 | sle_st_b_v2 | 5_1_grt | 2.5 | last meaningful line 0.0 h ago (153/153 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3668964 | sle_st_b_v2 | 5_2_route | 7.3 | drt_violations best 137987 last 137987 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | otc-2459734-26514 | 2459734 | signoff | 3.1 | last meaningful line 3.0 h ago (3/3 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | otc-2882933-23086 | 2882933 | signoff | 1.2 | last meaningful line 1.1 h ago (3/3 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | otc-3544630-5805 | 3544630 | signoff | 4.7 | last meaningful line 4.6 h ago (3/3 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | otc-785042-5629 | 785042 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261124_204708_4151707-i1t-4056582 | eco_20261124_204708_4151707-i1t | 5_2_route | 2.7 | drt_violations best 10225 last 10225 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_215436_3656110-i1-2033351 | eco_20261124_215436_3656110-i1 | 5_2_route | 1.6 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 12.2 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbf_q00_s2-3518685 | cbf_q00_s2 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (8139/8139 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-coll_core-4024971 | coll_core | 3_4_place_resized | 1.0 | last meaningful line 0.1 h ago (371/371 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-coll_ftn-485651 | coll_ftn | 5_2_route | 0.7 | last meaningful line 0.0 h ago (236/237 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-4031555 | sle_ctl | 3_1_place_gp_skip_io | 1.0 | overflow best 0.1438 last 0.1438 rows 47 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | 4_1_cts | 1.1 | last meaningful line 0.2 h ago (5114/5114 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv4242de79-3812382 | sle_st_a_v2 | 5_1_grt | 1.1 | last meaningful line 0.2 h ago (271/1279 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | 5_2_route | 14.3 | drt_violations best 20228 last 20228 rows 2 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | 5_2_route | 14.2 | drt_violations best 19210 last 19210 rows 2 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 5_2_route | 14.3 | drt_violations best 26702 last 26702 rows 2 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (5539/5539 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | generate_abstract | 14.2 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-3807127 | slw_su_l1 | 5_1_grt | 1.1 | last meaningful line 0.2 h ago (262/1272 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-534954 | slw_su_l1 | pregrt_ff_hold | 0.7 | repair_Violations best 38 last 38 rows 52 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | eco-abs-1654772 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.3 h ago (1028/1028 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_145005_2036075-i3-424023 | eco_20261124_145005_2036075-i3 | 5_2_route | 2.7 | last meaningful line 0.3 h ago (276/277 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i3t-4028039 | eco_20261124_175441_992552-i3t | 5_2_route | 1.0 | last meaningful line 0.2 h ago (258/259 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i2t-2177999 | eco_20261124_192157_3493836-i2t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i2t-915490 | eco_20261124_235631_1843084-i2t | 5_2_route | 0.6 | last meaningful line 0.0 h ago (247/247 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | so_1168156_ff_43800 | so_1168156_ff_43800 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc7 | so_1168156_tt_43800 | so_1168156_tt_43800 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc7 | so_343482_ff_51512 | so_343482_ff_51512 | signoff | 0.8 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_2_route | 15.4 | last meaningful line 0.4 h ago (274/275 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 5_2_route | 15.4 | drt_violations best 146067 last 146067 rows 1 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 5_2_route | 15.4 | drt_violations best 129389 last 129389 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 5_2_route | 15.4 | drt_violations best 131388 last 131388 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 5_2_route | 15.4 | drt_violations best 127432 last 127432 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | 5_2_route | 15.4 | drt_violations best 14 last 14 rows 7 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 15.4 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 5_2_route | 15.4 | drt_violations best 152943 last 152943 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 5_2_route | 15.4 | drt_violations best 146375 last 146375 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 5_2_route | 15.4 | drt_violations best 138449 last 138449 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 5_2_route | 15.4 | drt_violations best 141263 last 141263 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc8 | otc-120424-12773 | 120424 | signoff | 5.1 | last meaningful line 5.0 h ago (3/3 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc8 | otc-3678186-167 | 3678186 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3-32256 | eco_20261123_164145_1995767-i3 | 5_2_route | 3.6 | last meaningful line 0.2 h ago (295/296 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_025941_3548303-i1t-1829547 | eco_20261125_025941_3548303-i1t | 5_2_route | 4.5 | drt_violations best 495 last 495 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_065854_3885412-i1-521874 | eco_20261125_065854_3885412-i1 | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (138/138 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_071225_3873455-i1-1532615 | eco_20261125_071225_3873455-i1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 12.3 |  | NO-DATA: no log found |  |
| epyc8 | so_1983234_ff_82328 | so_1983234_ff_82328 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | so_1983234_tt_82328 | so_1983234_tt_82328 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (3680/3680 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pv07945c1e-55623 | col_h10_r0_p4__t1 | 4_2_tapbal_grt | 1.3 | repair_Violations best 20 last 59 rows 11 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvc9270d09-115129 | col_h10_r0_p4__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.7043 last 0.7043 rows 9 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 4_2_tapbal_grt | 0.8 | last meaningful line 0.1 h ago (60/65 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-141622 | col_h10_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.4497 last 0.4497 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3378330 | col_h9_r0_p1__t1 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (4573/4573 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-3647546 | col_h9_r0_p1__t1 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-3684533 | col_h9_r0_p2__t1 | 4_2_tapbal_grt | 0.8 | last meaningful line 0.0 h ago (60/61 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3716359 | col_h9_r0_p2__t1 | 4_2_tapbal_grt | 0.8 | last meaningful line 0.0 h ago (62/63 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-4079818 | col_h9_r0_p2__t1 | 5_1_grt | 2.7 | last meaningful line 0.2 h ago (274/1279 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b-3679007 | col_h9_r0_p3__t1 | 4_2_tapbal_grt | 0.8 | last meaningful line 0.0 h ago (60/61 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv8d734760-3617215 | col_h9_r0_p3__t1 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-3757021 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.8 | overflow best 0.1978 last 0.1978 rows 39 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-296584 | col_h9_r0_p3__t1 | lec | 3.3 | LEC last write 0.3 h ago | YOUNG: evidence 3.3 h < 6 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3720064 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.8 | overflow best 0.4886 last 0.4886 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 4_2_tapbal_grt | 0.8 | last meaningful line 0.0 h ago (62/65 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv8995e794-1162680 | col_h9_r0_p5__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 357 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-3710863 | col_h9_r0_p5__t1 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-3999510 | col_h9_r0_p5__t1 | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (211/211 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl87f3ff59-1171886 | col_h9_r2__t1 | 2_1_floorplan | 0.1 | repair_Viol best 2770 last 2770 rows 1286 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_1_grt | 2.6 | last meaningful line 0.0 h ago (153/153 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-3394850 | col_h9_r2__t1 | pregrt_ff_hold | 0.8 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7a260fc0-119590 | col_h9_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.4913 last 0.4967 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-3707756 | col_h9_r2__t1 | pregrt_ff_hold | 0.8 | repair_TNS best 57283.8 last 57283.8 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | lec | 1.8 | LEC last write 0.0 h ago | YOUNG: evidence 1.8 h < 6 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t5-284167 | dsdv_slice_c1x_C__t5 | lec | 3.4 | LEC last write 0.4 h ago | YOUNG: evidence 3.4 h < 6 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-4170435 | dsdv_slice_lepw_mu_C__t1 | 3_3_place_gp | 2.6 | overflow best 0.7707 last 0.8643 rows 16 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t36-3727117 | ot_s81sl_leaf__t36 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (6550/6550 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t53__cl958451dd-1174037 | ot_s81sl_leaf__t53 | 2_1_floorplan | 0.1 | repair_Viol best 1338 last 1338 rows 543 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_2_route | 12.3 | drt_violations best 162913 last 162913 rows 2 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t21-3663770 | slice_station__t21 | tt_setup_repair_grt | 0.8 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__cl1ea9de02-165124 | slice_station__t40 | 3_3_place_gp | 0.2 | overflow best 0.2298 last 0.2311 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 12.4 | drt_violations best 65686 last 65686 rows 2 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | otc-115840-2964 | 115840 | gen_lint_yosys | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | otc-3987944-19968 | 3987944 | gen_lint_yosys | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | so_1866284_ff_63309 | so_1866284_ff_63309 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | so_1866284_tt_63309 | so_1866284_tt_63309 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel1 | colh10cen_k6n_4039899 | colh10cen_k6n_4039899 | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | colh10hld_k6n_94191 | colh10hld_k6n_94191 | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | colh10hld_k8n_95444 | colh10hld_k8n_95444 | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 5_2_route | 18.5 | drt_violations best 317907 last 317907 rows 1 | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 5_2_route | 14.1 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | pregrt_ff_hold | 6.2 | last meaningful line 0.0 h ago (59/59 lines) | YOUNG: evidence 0.8 h < 2.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | postcts_gate_TT | 10.5 | last meaningful line -0.0 h ago (13168/13168 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 5_2_route | 12.2 | drt_violations best 144494 last 144494 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_1_grt | 7.9 | last meaningful line 0.2 h ago (1283/2343 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3325358 | slw_fw_v1 | 5_1_grt | 7.9 | repair_Remaining best 387539 last 387539 rows 47 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | postcts_gate_TT | 9.0 | last meaningful line 0.1 h ago (409/409 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 5_2_route | 10.2 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 5_2_route | 14.1 | last meaningful line 0.1 h ago (275/276 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 5_2_route | 14.1 | drt_violations best 125787 last 125787 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1e5219ea-4177722 | slw_su_l0 | 6_report | 10.3 | last meaningful line -0.0 h ago (48/48 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-3090069 | slw_su_l0 | 5_2_route | 8.0 | drt_violations best 16873 last 16873 rows 3 | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 12.3 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 12.3 |  | NO-DATA: no log found |  |
| intel1 | otc-1948440-31269 | 1948440 | flow | 1.0 | last meaningful line 0.2 h ago (1897/1897 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | otc-2098914-19313 | 2098914 | flow | 0.9 | last meaningful line 0.0 h ago (2877/2877 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | otc-4000256-29997 | 4000256 | eq11 | 4.2 | last meaningful line -0.0 h ago (793294/793294 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | otc-4001240-3461 | 4001240 | eq11 | 4.2 | last meaningful line 0.0 h ago (793287/793287 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | prd-count-p1_bc-2930338 | count-p1_bc | prd_count_p1_bc | 0.1 | last meaningful line 0.0 h ago (842/842 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | so_1436874_ff_48011 | so_1436874_ff_48011 | signoff | 1.2 |  | NO-DATA: empty log |  |
| intel1 | so_1436874_tt_48011 | so_1436874_tt_48011 | signoff | 1.2 |  | NO-DATA: empty log |  |
| intel1 | so_16092_ff_52647 | so_16092_ff_52647 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | so_16092_tt_52647 | so_16092_tt_52647 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel2 | dpkit-coll_ftm-1842242 | coll_ftm | 5_2_route | 1.5 | last meaningful line 0.1 h ago (238/239 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-4092661 | sle_sc_v1 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-195391 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 3039 last 3039 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 13.9 | drt_violations best 367946 last 367946 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-2390236 | slw_st_b_v1 | 5_2_route | 6.9 | last meaningful line 0.0 h ago (261/261 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | ap-ageom-kw-kv3-hgi-grt-3910308 | kv3-hgi-grt | - | 0.2 |  | KEEP: kv3_hgi_1124155644	KV-OWN-RSTREACH	combined HEADLEG2+HGI-LEAF ship form; noprog  |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | 5_2_route | 11.4 | drt_violations best 1820 last 2009 rows 23 | before-window best 3898, window best 1820 | PROGRESS: drt_violations improved 53.3 % in window |  |
| epyc10 | dpkit-native59-3384403 | native59 | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 26.4 | drt_violations best 14980 last 63558 rows 18 | before-window best 15812, window best 14980 | PROGRESS: drt_violations improved 5.3 % in window |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | 5_2_route | 13.8 | drt_violations best 0 last 0 rows 8 | PROGRESS: drt_violations reached 0 |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 18.7 | drt_violations best 7058 last 7058 rows 14 | before-window best 88579, window best 7058 | PROGRESS: drt_violations improved 92.0 % in window |  |
| epyc2 | prd-eco_20261124_230804_491597-i1-1072574 | eco_20261124_230804_491597-i1 | 5_1_grt | 0.4 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 39.1 | drt_violations best 7726 last 8463 rows 20 | before-window best 7726, window best 8463 | PROGRESS: drt_violations: falling inside the active iteration (8463 -> 7800) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 4_1_cts | 6.9 | last meaningful line 0.3 h ago (10908/10908 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 23.9 | drt_violations best 2818 last 2818 rows 16 | before-window best 8628, window best 2818 | PROGRESS: drt_violations improved 67.3 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 20.0 | drt_violations best 12303 last 12303 rows 9 | before-window best 504597, window best 12303 | PROGRESS: drt_violations improved 97.6 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 18.7 | drt_violations best 90589 last 90589 rows 3 | before-window best 510309, window best 90589 | PROGRESS: drt_violations improved 82.2 % in window |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 14.1 | drt_violations best 113083 last 113083 rows 3 | before-window best 412199, window best 113083 | PROGRESS: drt_violations improved 72.6 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 18.5 | drt_violations best 78434 last 78434 rows 3 | before-window best 457993, window best 78434 | PROGRESS: drt_violations improved 82.9 % in window |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 24.1 | drt_violations best 65547 last 65547 rows 10 | before-window best 67058, window best 65547 | PROGRESS: drt_violations improved 2.3 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 20.2 | drt_violations best 53197 last 53197 rows 8 | before-window best 102681, window best 53197 | PROGRESS: drt_violations improved 48.2 % in window |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 5_2_route | 15.4 | drt_violations best 23313 last 23313 rows 2 | before-window best 162445, window best 23313 | PROGRESS: drt_violations improved 85.6 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 15.3 | drt_violations best 122835 last 122835 rows 2 | before-window best 478667, window best 122835 | PROGRESS: drt_violations improved 74.3 % in window |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 15.3 | drt_violations best 450083 last 450083 rows 1 | before-window best 450083, window best 450083 | PROGRESS: drt_violations: active iteration at 287558 < best completed total 450083 (in-ite |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 15.3 | drt_violations best 56713 last 56713 rows 4 | before-window best 379431, window best 56713 | PROGRESS: drt_violations improved 85.1 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 15.4 | drt_violations best 10226 last 10226 rows 14 | before-window best 23879, window best 10226 | PROGRESS: drt_violations improved 57.2 % in window |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 12.1 | drt_violations best 1371 last 3385 rows 26 | before-window best 2181, window best 1371 | PROGRESS: drt_violations improved 37.1 % in window |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 10.4 | drt_violations best 58 last 58 rows 13 | before-window best 187976, window best 58 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 18.4 | drt_violations best 398476 last 398476 rows 1 | before-window best 398476, window best 398476 | PROGRESS: drt_violations: active iteration at 167328 < best completed total 398476 (in-ite |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | pregrt_ff_hold | 8.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 5_2_route | 14.1 | drt_violations best 105657 last 105657 rows 2 | before-window best 406352, window best 105657 | PROGRESS: drt_violations improved 74.0 % in window |  |
