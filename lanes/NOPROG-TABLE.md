# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 00:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 5, 'UNSIGNABLE': 4, 'GRT-LABEL': 10, 'YOUNG': 127, 'NO-DATA': 31, 'PROGRESS': 33}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 15.1 | last meaningful line 13.8 h ago (48/141 lines) | NO-PROGRESS: no new non-iteration log line for 13.8 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc10 | dpkit-kv3_hg_v1__r88f4bfb40-1671162 | kv3_hg_v1__r88f4bfb40 | 5_1_grt | 6.2 | grt rounds 2 overflow 5:42362 -> 10:41975 | UNSIGNABLE: GRT overflow flat: overflow 42362 at iteration 5 -> 41975 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 5_1_grt | 15.4 | grt rounds 2 overflow 5:42234 -> 10:42876 | UNSIGNABLE: GRT overflow flat: overflow 42234 at iteration 5 -> 42876 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_pv_v12-1535838 | kv3_pv_v12 | pregrt_ff_hold | 4.8 | repair_TNS best 30428.6 last 30428.6 rows 1 | before-window best 30428.6, window best 30428.6 | NO-PROGRESS: repair_TNS best 30428.6 vs 30428.6 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 18.1 | last meaningful line 14.6 h ago (48/211 lines) | NO-PROGRESS: no new non-iteration log line for 14.6 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | 5_1_grt | 12.5 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 10.3 | repair_TNS best 145595 last 145595 rows 1 | before-window best 145595, window best 145595 | NO-PROGRESS: repair_TNS best 145595 vs 145595 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc11 | otc-3389445-25127 | 3389445 | signoff | 7.1 | last meaningful line 7.0 h ago (3/3 lines) | NO-PROGRESS: no new non-iteration log line for 7.0 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 5_1_grt | 17.1 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_hg_v1__r889141819-1619104 | kv3_hg_v1__r889141819 | 5_1_grt | 6.3 | grt rounds 1 overflow 5:43060 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-2844240 | kv3_pc | 5_1_grt | 4.4 | grt rounds 2 overflow 5:7078 -> 10:4367 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r8b421e514-2986767 | kv3_pc | 5_1_grt | 4.4 | grt rounds 2 overflow 5:7207 -> 10:4296 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r85c02c25c-3151820 | kv3_pc | 5_1_grt | 4.3 | grt rounds 2 overflow 5:7303 -> 10:4851 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r882954158-3053902 | kv3_pc | 5_1_grt | 4.4 | grt rounds 2 overflow 5:6934 -> 10:4576 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | 5_1_grt | 10.4 | grt rounds 2 overflow 5:94600 -> 10:59159 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v8-2737550 | kv3_hgi_v8 | 5_1_grt | 5.6 | grt rounds 2 overflow 5:54135 -> 10:40850 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-1559108 | cbn_q01 | 5_1_grt | 7.2 | grt rounds 2 overflow 5:81921 -> 10:75607 | GRT-LABEL: DESIGN-FAIL: overflow 75607 at round 10 > 1000 |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | 5_1_grt | 12.2 | grt rounds 2 overflow 5:34556 -> 10:3532 | GRT-LABEL: DESIGN-FAIL: overflow 3532 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi_v6-102352 | kv3_hgi_v6 | 5_1_grt | 6.3 | grt rounds 2 overflow 5:53849 -> 10:29026 | GRT-LABEL: DESIGN-FAIL: overflow 29026 at round 10 > 1000 |  |
| epyc10 | dpkit-glue-1294589 | glue | 5_1_grt | 6.5 | last meaningful line 0.2 h ago (1050/1056 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r8dffc461a-1676050 | kv3_hg_v1__r8dffc461a | 5_1_grt | 6.2 | last meaningful line 1.5 h ago (287/1296 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p2-1802854 | kv3_hg_v1p2 | 5_1_grt | 6.2 | last meaningful line 0.5 h ago (305/1310 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p3__r81da466fe-1840159 | kv3_hg_v1p3__r81da466fe | 5_1_grt | 6.1 | last meaningful line 1.0 h ago (287/1294 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-4187490 | kv3_pv_v3 | pregrt_ff_hold | 3.9 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_2_route | 14.2 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | 5_2_route | 11.1 | drt_violations best 104126 last 104126 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | 5_2_route | 11.5 | drt_violations best 149411 last 149411 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | 5_2_route | 12.0 | drt_violations best 17925 last 17925 rows 2 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 13.2 | drt_violations best 272423 last 272423 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_2_route | 13.2 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | postcts_gate_FF | 13.2 | last meaningful line -0.0 h ago (66500/66500 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | 5_1_grt | 11.8 | last meaningful line 0.2 h ago (1134/1151 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | 5_2_route | 11.0 | drt_violations best 138401 last 138401 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3681869 | slw_st_b_v2 | 5_2_route | 7.5 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | 5_2_route | 9.9 | drt_violations best 130780 last 130780 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_055922_2792445-i1-2623359 | eco_20261125_055922_2792445-i1 | 5_2_route | 2.0 | last meaningful line 0.2 h ago (264/264 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | qc-hc3-lec-r8-nearest | qc-hc3-lec-r8-nearest | - | 9.0 |  | NO-DATA: no log found |  |
| epyc10 | qccollslec_h4 | qccollslec_h4 | - | 4.0 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-cbn_q00__cl622f65d2-483597 | cbn_q00 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.7486 last 0.7486 rows 24 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 14.5 | drt_violations best 329677 last 329677 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 5_2_route | 10.1 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 5_2_route | 11.1 | drt_violations best 25003 last 25003 rows 2 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 5_2_route | 9.8 | last meaningful line 0.3 h ago (132/132 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | 6_report | 14.3 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2533872 | slw_hc3 | 5_2_route | 8.1 | drt_violations best 10011 last 10011 rows 2 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | 5_1_grt | 4.8 | last meaningful line 0.3 h ago (145/145 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl92142dac-2960548 | slw_su_c | 4_1_cts | 1.1 | last meaningful line 0.2 h ago (8332/8332 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | eco-abs-1174114 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.1 h ago (29/29 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | eco-abs-864576 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.2 h ago (902/902 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 13.5 |  | NO-DATA: no log found |  |
| epyc11 | otc-701258-11435 | 701258 | lec | 0.4 | LEC last write 0.4 h ago | YOUNG: evidence 0.4 h < 6 h |  |
| epyc11 | otc-701492-14947 | 701492 | lec | 0.4 | LEC last write 0.4 h ago | YOUNG: evidence 0.4 h < 6 h |  |
| epyc11 | prd-count-p1_tc-3660942 | count-p1_tc | prd_count_p1_tc | 0.2 | last meaningful line 0.0 h ago (1047/1047 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_154417_1016084-i2t-1425156 | eco_20261124_154417_1016084-i2t | 5_2_route | 4.8 | drt_violations best 917 last 917 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_204246_1187010-i1-249436 | eco_20261124_204246_1187010-i1 | 5_2_route | 5.9 | drt_violations best 1 last 1 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_054540_316017-i1-897106 | eco_20261125_054540_316017-i1 | 5_2_route | 2.2 | last meaningful line 0.3 h ago (264/265 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | smp-1618822 | smp | - | 0.0 |  | NO-DATA: no log found |  |
| epyc11 | smp-1620642 | smp | - | 0.0 |  | NO-DATA: no log found |  |
| epyc11 | smp-1623032 | smp | - | 0.0 |  | NO-DATA: no log found |  |
| epyc11 | so_3098882_tt_50641 | so_3098882_tt_50641 | signoff | 1.0 |  | NO-DATA: empty log |  |
| epyc11 | so_3632485_ff_17702 | so_3632485_ff_17702 | signoff | 0.9 |  | NO-DATA: empty log |  |
| epyc11 | so_3632485_tt_17702 | so_3632485_tt_17702 | signoff | 0.9 |  | NO-DATA: empty log |  |
| epyc11 | so_428963_ff_46412 | so_428963_ff_46412 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc11 | so_428963_tt_46412 | so_428963_tt_46412 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1216203 | sle_st_b_v1 | tt_setup_repair_grt | 4.0 | repair_Remaining best 407639 last 407639 rows 150 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-360401 | sle_st_b_v2 | 5_1_grt | 3.0 | repair_TNS best 29.859 last 29.859 rows 14 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3668964 | sle_st_b_v2 | 5_2_route | 7.8 | drt_violations best 137987 last 137987 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | otc-2040585-24869 | 2040585 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc2 | otc-2459734-26514 | 2459734 | signoff | 3.6 | last meaningful line 3.5 h ago (3/3 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | otc-2632246-1358 | 2632246 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | otc-2882933-23086 | 2882933 | signoff | 1.7 | last meaningful line 1.6 h ago (3/3 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | otc-3544630-5805 | 3544630 | signoff | 5.2 | last meaningful line 5.1 h ago (3/3 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | otc-785042-5629 | 785042 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261124_215436_3656110-i1-2033351 | eco_20261124_215436_3656110-i1 | 5_2_route | 2.1 | drt_violations best 22 last 22 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_230804_491597-i1-1072574 | eco_20261124_230804_491597-i1 | 5_2_route | 0.9 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 12.7 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbf_q00_s2-3518685 | cbf_q00_s2 | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (8170/8170 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-coll_ftn-485651 | coll_ftn | 6_report | 1.2 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-4031555 | sle_ctl | 3_3_place_gp | 1.5 | overflow best 0.1934 last 0.2076 rows 33 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | 4_1_cts | 1.6 | last meaningful line 0.2 h ago (5180/5180 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | 5_2_route | 14.8 | drt_violations best 32 last 32 rows 5 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | 5_2_route | 14.7 | drt_violations best 19210 last 19210 rows 2 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 5_2_route | 14.8 | drt_violations best 26702 last 26702 rows 2 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 4_1_cts | 1.6 | last meaningful line 0.1 h ago (5550/5550 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-534954 | slw_su_l1 | 5_1_grt | 1.2 | last meaningful line 0.2 h ago (262/1269 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | eco-abs-1654772 | eco-abs | generate_abstract | 0.8 | last meaningful line 0.4 h ago (1030/1030 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i3t-4028039 | eco_20261124_175441_992552-i3t | 5_2_route | 1.5 | drt_violations best 18510 last 18510 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i2t-2177999 | eco_20261124_192157_3493836-i2t | 5_1_grt | 0.6 | last meaningful line 0.2 h ago (293/327 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i2t-915490 | eco_20261124_235631_1843084-i2t | 5_2_route | 1.1 | last meaningful line 0.1 h ago (256/257 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_073745_2194631-i1-2944509 | eco_20261125_073745_2194631-i1 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_073945_2252980-i1t-3004488 | eco_20261125_073945_2252980-i1t | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-fin-424023 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | so_2689799_ff_51821 | so_2689799_ff_51821 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc7 | so_2689799_tt_51821 | so_2689799_tt_51821 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_2_route | 15.9 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 5_2_route | 15.9 | drt_violations best 18551 last 18551 rows 2 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 5_2_route | 15.9 | drt_violations best 129389 last 129389 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 5_2_route | 15.9 | drt_violations best 131388 last 131388 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | 6_report | 15.9 | last meaningful line 0.0 h ago (55/55 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 15.9 | last meaningful line 0.5 h ago (272/273 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 5_2_route | 15.9 | drt_violations best 152943 last 152943 rows 1 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 5_2_route | 15.9 | drt_violations best 146375 last 146375 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 5_2_route | 15.9 | drt_violations best 138449 last 138449 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 5_2_route | 15.9 | drt_violations best 141263 last 141263 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc8 | otc-120424-12773 | 120424 | signoff | 5.6 | last meaningful line 5.5 h ago (3/3 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc8 | otc-3678186-167 | 3678186 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3-32256 | eco_20261123_164145_1995767-i3 | 5_2_route | 4.1 | last meaningful line 0.3 h ago (299/300 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_025941_3548303-i1t-1829547 | eco_20261125_025941_3548303-i1t | 5_2_route | 5.0 | drt_violations best 495 last 495 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_065854_3885412-i1-521874 | eco_20261125_065854_3885412-i1 | 5_1_grt | 1.0 | last meaningful line 0.1 h ago (290/329 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_071225_3873455-i1-1532615 | eco_20261125_071225_3873455-i1 | 5_1_grt | 0.7 | last meaningful line 0.3 h ago (139/139 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 12.8 |  | NO-DATA: no log found |  |
| epyc8 | so_1983234_ff_82328 | so_1983234_ff_82328 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc8 | so_1983234_tt_82328 | so_1983234_tt_82328 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | 4_2_tapbal_grt | 1.3 | last meaningful line 0.1 h ago (62/65 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pv07945c1e-55623 | col_h10_r0_p4__t1 | lec | 1.8 | LEC last write 0.2 h ago | YOUNG: evidence 1.8 h < 6 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | lec | 1.3 | LEC last write 0.0 h ago | YOUNG: evidence 1.3 h < 6 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3378330 | col_h9_r0_p1__t1 | 4_2_tapbal_grt | 1.3 | last meaningful line 0.1 h ago (62/69 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-3684533 | col_h9_r0_p2__t1 | lec | 1.3 | LEC last write 0.0 h ago | YOUNG: evidence 1.3 h < 6 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3716359 | col_h9_r0_p2__t1 | 4_2_tapbal_grt | 1.3 | last meaningful line 0.5 h ago (62/69 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-4079818 | col_h9_r0_p2__t1 | 5_1_grt | 3.2 | last meaningful line 0.7 h ago (274/1284 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b-3679007 | col_h9_r0_p3__t1 | 4_2_tapbal_grt | 1.3 | last meaningful line 0.5 h ago (62/71 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-296584 | col_h9_r0_p3__t1 | lec | 3.8 | LEC last write 0.2 h ago | YOUNG: evidence 3.8 h < 6 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv8995e794-1162680 | col_h9_r0_p5__t1 | 3_3_place_gp | 0.6 | overflow best 0.4988 last 0.5141 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pvf8d9f9e5-2905198 | col_h9_r2__t1 | 3_5_place_dp | 0.4 | last meaningful line 0.0 h ago (95/95 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pvf1445dce-2868488 | col_h9_r2__t1 | 3_5_place_dp | 0.4 | last meaningful line 0.0 h ago (96/96 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv31e47bd5-2877462 | col_h9_r2__t1 | 3_5_place_dp | 0.4 | repair_Violations best 850 last 850 rows 13 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_1_grt | 3.1 | last meaningful line 0.0 h ago (2415/2425 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-3394850 | col_h9_r2__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 72521.9 last 72521.9 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-3707756 | col_h9_r2__t1 | lec | 1.3 | LEC last write 0.1 h ago | YOUNG: evidence 1.3 h < 6 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | lec | 2.3 | LEC last write 0.1 h ago | YOUNG: evidence 2.3 h < 6 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t10-3695203 | dsdv_slice_c1x_C__t10 | sdc_lint | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t5-284167 | dsdv_slice_c1x_C__t5 | 3_5_place_dp | 3.9 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-578982 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-3691225 | dsdv_slice_c1x_C__t9 | sdc_lint | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-4170435 | dsdv_slice_lepw_mu_C__t1 | 3_4_place_resized | 3.1 | last meaningful line 0.1 h ago (412/412 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t36-3727117 | ot_s81sl_leaf__t36 | pregrt_ff_hold | 1.3 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t53__cl958451dd-1174037 | ot_s81sl_leaf__t53 | 3_3_place_gp | 0.6 | overflow best 0.5143 last 0.5143 rows 22 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_2_route | 12.8 | drt_violations best 162913 last 162913 rows 2 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t21-3663770 | slice_station__t21 | 5_2_route | 1.3 | last meaningful line 0.0 h ago (227/228 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t6__cl54a9ceeb-3699444 | slice_station__t6 | 3_3_place_gp | 0.3 | overflow best 0.2577 last 0.2577 rows 43 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 12.9 | drt_violations best 47547 last 47547 rows 3 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc9 | otc-115840-2964 | 115840 | gen_lint_yosys | 1.2 | last meaningful line 1.2 h ago (1/1 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | otc-3987944-19968 | 3987944 | gen_lint_yosys | 1.2 | last meaningful line 1.2 h ago (1/1 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | so_1866284_ff_63309 | so_1866284_ff_63309 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc9 | so_1866284_tt_63309 | so_1866284_tt_63309 | signoff | 0.5 |  | NO-DATA: empty log |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1177242 | kv3_hg_v1p3__r838481cd7 | tt_setup_repair | 0.1 | last meaningful line 0.0 h ago (356/356 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 5_2_route | 19.0 | drt_violations best 317907 last 317907 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 5_2_route | 14.6 | drt_violations best 163425 last 163425 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 5_1_grt | 6.7 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | postcts_gate_FF | 11.0 | last meaningful line 0.1 h ago (536/536 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 5_2_route | 12.7 | drt_violations best 144494 last 144494 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3325358 | slw_fw_v1 | 5_1_grt | 8.4 | last meaningful line 0.7 h ago (291/1833 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 5_2_route | 9.5 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 5_2_route | 10.7 | last meaningful line 0.2 h ago (137/137 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 5_2_route | 14.6 | last meaningful line 0.6 h ago (275/276 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 5_1_grt | 9.2 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-3090069 | slw_su_l0 | 5_2_route | 8.5 | drt_violations best 77 last 77 rows 6 | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 12.8 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 12.8 |  | NO-DATA: no log found |  |
| intel1 | otc-1409945-13294 | 1409945 | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (453/453 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-1948440-31269 | 1948440 | flow | 1.5 | last meaningful line 0.5 h ago (1897/1897 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | otc-2098914-19313 | 2098914 | flow | 1.4 | last meaningful line 0.1 h ago (2917/2917 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | otc-4000256-29997 | 4000256 | eq11 | 4.7 | last meaningful line 0.0 h ago (793973/793973 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | otc-4001240-3461 | 4001240 | eq11 | 4.7 | last meaningful line 0.0 h ago (793973/793973 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | prd-fin-2930338 | fin | 6_report | 0.5 | last meaningful line 0.1 h ago (910/910 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | so_1436874_ff_48011 | so_1436874_ff_48011 | signoff | 1.7 |  | NO-DATA: empty log |  |
| intel1 | so_1436874_tt_48011 | so_1436874_tt_48011 | signoff | 1.7 |  | NO-DATA: empty log |  |
| intel1 | so_16092_ff_52647 | so_16092_ff_52647 | signoff | 0.6 |  | NO-DATA: empty log |  |
| intel1 | so_16092_tt_52647 | so_16092_tt_52647 | signoff | 0.6 |  | NO-DATA: empty log |  |
| intel1 | so_962160_ff_33092 | so_962160_ff_33092 | signoff | 0.2 |  | NO-DATA: empty log |  |
| intel1 | so_962160_tt_33092 | so_962160_tt_33092 | signoff | 0.2 |  | NO-DATA: empty log |  |
| intel2 | dpkit-coll_ftm-1842242 | coll_ftm | 5_2_route | 2.0 | drt_violations best 10288 last 10288 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_hgi_v2__cle0015330-3208477 | kv3_hgi_v2 | tt_setup_repair_grt | 2.7 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8e08b358d-871622 | kv3_pc_v1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (519/519 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 14.4 | drt_violations best 367946 last 367946 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-2390236 | slw_st_b_v1 | 5_2_route | 7.4 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | otc-1057487-1207 | 1057487 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (7/7 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | 5_2_route | 11.9 | drt_violations best 1820 last 2009 rows 23 | before-window best 3764, window best 1820 | PROGRESS: drt_violations improved 51.6 % in window |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | 4_1_cts | 6.6 | last meaningful line 0.3 h ago (11311/11311 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-native59-3384403 | native59 | pregrt_ff_hold | 5.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc10 | prd-eco_20261125_073109_4058437-i1t-725979 | eco_20261125_073109_4058437-i1t | 5_1_grt | 0.4 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 26.9 | drt_violations best 14980 last 63558 rows 18 | before-window best 15812, window best 14980 | PROGRESS: drt_violations improved 5.3 % in window |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 19.2 | drt_violations best 7058 last 7058 rows 14 | before-window best 88579, window best 7058 | PROGRESS: drt_violations improved 92.0 % in window |  |
| epyc2 | prd-eco_20261124_204708_4151707-i1t-4056582 | eco_20261124_204708_4151707-i1t | 5_2_route | 3.2 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 39.6 | drt_violations best 7726 last 8463 rows 20 | before-window best 7726, window best 8463 | PROGRESS: drt_violations: active iteration at 7318 < best completed total 7726 (in-iterati |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 4_1_cts | 7.4 | last meaningful line 0.2 h ago (11188/11188 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 24.4 | drt_violations best 2818 last 2818 rows 16 | before-window best 7491, window best 2818 | PROGRESS: drt_violations improved 62.4 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 20.5 | drt_violations best 11325 last 11325 rows 10 | before-window best 116309, window best 11325 | PROGRESS: drt_violations improved 90.3 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 19.2 | drt_violations best 29127 last 29127 rows 4 | before-window best 510309, window best 29127 | PROGRESS: drt_violations improved 94.3 % in window |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 14.6 | drt_violations best 113083 last 113083 rows 3 | before-window best 412199, window best 113083 | PROGRESS: drt_violations improved 72.6 % in window |  |
| epyc7 | dpkit-sle_st_a_v2__pv4242de79-3812382 | sle_st_a_v2 | 5_1_grt | 1.6 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 19.0 | drt_violations best 23191 last 23191 rows 4 | before-window best 457993, window best 23191 | PROGRESS: drt_violations improved 94.9 % in window |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 24.6 | drt_violations best 65547 last 65547 rows 10 | before-window best 67058, window best 65547 | PROGRESS: drt_violations improved 2.3 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 20.7 | drt_violations best 52514 last 52514 rows 9 | before-window best 102681, window best 52514 | PROGRESS: drt_violations improved 48.9 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-3807127 | slw_su_l1 | 5_1_grt | 1.6 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 5_2_route | 15.9 | drt_violations best 14831 last 14831 rows 3 | before-window best 162445, window best 14831 | PROGRESS: drt_violations improved 90.9 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 15.8 | drt_violations best 122835 last 122835 rows 2 | before-window best 478667, window best 122835 | PROGRESS: drt_violations improved 74.3 % in window |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 5_2_route | 15.9 | drt_violations best 127432 last 127432 rows 1 | before-window best 127432, window best 127432 | PROGRESS: drt_violations: active iteration at 36593 < best completed total 127432 (in-iter |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 15.8 | drt_violations best 450083 last 450083 rows 1 | before-window best 450083, window best 450083 | PROGRESS: drt_violations: active iteration at 248142 < best completed total 450083 (in-ite |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 15.8 | drt_violations best 56713 last 56713 rows 4 | before-window best 379431, window best 56713 | PROGRESS: drt_violations improved 85.1 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 15.9 | drt_violations best 10226 last 10226 rows 14 | before-window best 23879, window best 10226 | PROGRESS: drt_violations improved 57.2 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 4_2_tapbal_grt | 1.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-2437290 | col_h9_r2__t1 | 3_5_place_dp | 0.4 | repair_Violations best 0 last 0 rows 25 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 12.6 | drt_violations best 1371 last 2044 rows 27 | before-window best 1846, window best 1371 | PROGRESS: drt_violations improved 25.7 % in window |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 10.9 | drt_violations best 58 last 58 rows 13 | before-window best 187976, window best 58 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_1_grt | 8.4 | repair_TNS best 0 last 0 rows 4 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 18.9 | drt_violations best 398476 last 398476 rows 1 | before-window best 398476, window best 398476 | PROGRESS: drt_violations: active iteration at 121808 < best completed total 398476 (in-ite |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 5_2_route | 14.6 | drt_violations best 125787 last 125787 rows 1 | before-window best 125787, window best 125787 | PROGRESS: drt_violations: active iteration at 40036 < best completed total 125787 (in-iter |  |
| intel2 | dpkit-kv3_io_ft-4044677 | kv3_io_ft | 5_1_grt | 0.5 | repair_TNS best 0 last 0 rows 16 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 5_2_route | 14.6 | drt_violations best 74892 last 74892 rows 3 | before-window best 406352, window best 74892 | PROGRESS: drt_violations improved 81.6 % in window |  |
