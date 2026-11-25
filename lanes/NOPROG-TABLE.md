# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 21:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 5, 'UNSIGNABLE': 3, 'GRT-LABEL': 5, 'YOUNG': 155, 'NO-DATA': 8, 'EXCLUDED': 1, 'KEEP': 1, 'PROGRESS': 18}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 12.1 | last meaningful line 10.8 h ago (48/139 lines) | NO-PROGRESS: no new non-iteration log line for 10.8 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 5_1_grt | 12.4 | grt rounds 2 overflow 5:42234 -> 10:42876 | UNSIGNABLE: GRT overflow flat: overflow 42234 at iteration 5 -> 42876 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | otc-901577-23707 | 901577 | signoff | 6.3 | last meaningful line 6.3 h ago (3/3 lines) | NO-PROGRESS: no new non-iteration log line for 6.3 h | REPORTED (cancel next pass) |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 15.1 | last meaningful line 11.6 h ago (48/195 lines) | NO-PROGRESS: no new non-iteration log line for 11.6 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | 5_1_grt | 9.5 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 7.3 | repair_TNS best 827598 last 827598 rows 1 | before-window best 827598, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 5_1_grt | 14.1 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 43.3 | drt_violations best 10129 last 21070 rows 19 | before-window best 10129, window best 21070 | NO-PROGRESS: drt_violations best 21070 vs 10129 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (FABLE-FIX-S81-COL-RANKS |
| epyc10 | dpkit-kv3_hgi-3860531 | kv3_hgi | 5_1_grt | 1.0 | grt rounds 2 overflow 5:28316 -> 10:12166 | GRT-LABEL: DESIGN-FAIL: overflow 12166 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-514739 | kv3_hgi_v2 | 5_1_grt | 0.7 | grt rounds 2 overflow 5:18053 -> 10:8644 | GRT-LABEL: DESIGN-FAIL: overflow 8644 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | 5_1_grt | 12.2 | grt rounds 2 overflow 5:52829 -> 10:36669 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | 5_1_grt | 7.4 | grt rounds 2 overflow 5:94600 -> 10:59159 | GRT-LABEL: DESIGN-FAIL: overflow 59159 at round 10 > 1000 |  |
| epyc2 | dpkit-kv3_hgi_v8-2737550 | kv3_hgi_v8 | 5_1_grt | 2.6 | grt rounds 1 overflow 5:54135 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-glue-1294589 | glue | pregrt_ff_hold | 3.5 | repair_TNS best 56966.4 last 56966.4 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r889141819-1619104 | kv3_hg_v1__r889141819 | pregrt_ff_hold | 3.3 | repair_Violations best 3433 last 3456 rows 49 | YOUNG: stage 0.8 h < 1 h |  |
| epyc10 | dpkit-kv3_hg_v1__r88f4bfb40-1671162 | kv3_hg_v1__r88f4bfb40 | pregrt_ff_hold | 3.2 | repair_Violations best 2664 last 2665 rows 102 | YOUNG: stage 0.9 h < 1 h |  |
| epyc10 | dpkit-kv3_hg_v1__r8dffc461a-1676050 | kv3_hg_v1__r8dffc461a | pregrt_ff_hold | 3.2 | repair_Violations best 6089 last 6089 rows 29 | YOUNG: stage 0.8 h < 1 h |  |
| epyc10 | dpkit-kv3_hg_v1p2-1802854 | kv3_hg_v1p2 | pregrt_ff_hold | 3.2 | repair_TNS best 197892 last 197892 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-kv3_hg_v1p3__r81da466fe-1840159 | kv3_hg_v1p3__r81da466fe | pregrt_ff_hold | 3.1 | repair_TNS best 208493 last 208493 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc10 | dpkit-kv3_hg_v1p5-2355527 | kv3_hg_v1p5 | 2_1_floorplan | 0.2 | last meaningful line 0.1 h ago (583/583 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-373156 | kv3_hgi | 5_1_grt | 4.0 | last meaningful line 3.3 h ago (296/1305 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | 4_1_cts | 3.6 | last meaningful line 0.3 h ago (11204/11204 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-2844240 | kv3_pc | tt_setup_repair | 1.4 | repair_Viol best 1009 last 1009 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r8b421e514-2986767 | kv3_pc | tt_setup_repair | 1.4 | repair_Violations best 152 last 163 rows 62 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r85c02c25c-3151820 | kv3_pc | pregrt_ff_hold | 1.3 | repair_TNS best 7778.2 last 7778.2 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r882954158-3053902 | kv3_pc | tt_setup_repair | 1.4 | repair_Violations best 391 last 395 rows 62 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-3561929 | kv3_pc_v1 | 3_3_place_gp | 1.2 | overflow best 0.6634 last 0.6634 rows 27 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r84d0332e1-3581607 | kv3_pc_v1 | 3_3_place_gp | 1.2 | overflow best 0.7751 last 0.7757 rows 9 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r884969661-3601103 | kv3_pc_v1 | 3_3_place_gp | 1.1 | overflow best 0.7696 last 0.7696 rows 4 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8afe1e027-3618066 | kv3_pc_v1 | 3_3_place_gp | 1.1 | overflow best 0.7626 last 0.7626 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8c9cba7ae-3633962 | kv3_pc_v1 | 3_3_place_gp | 1.1 | overflow best 0.6532 last 0.6532 rows 27 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-3669242 | kv3_pc_v1 | 3_3_place_gp | 1.1 | overflow best 0.647 last 0.647 rows 27 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v12-1535838 | kv3_pv_v12 | 4_1_cts | 1.8 | last meaningful line 0.1 h ago (9165/9165 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-3355795 | kv3_pv_v12 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (9158/9158 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-4187490 | kv3_pv_v3 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (11943/11943 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-native59-3384403 | native59 | pregrt_ff_hold | 2.5 | repair_TNS best 6612.64 last 6612.64 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_2_route | 11.2 | last meaningful line 0.3 h ago (264/265 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | 5_2_route | 8.1 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | 5_2_route | 8.5 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | 5_2_route | 9.0 | last meaningful line 0.2 h ago (281/282 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2793057 | sle_stm_v1 | 6_report | 10.8 | last meaningful line 0.1 h ago (68/68 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 10.2 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | postcts_gate_FF | 10.2 | last meaningful line 0.0 h ago (1662/1662 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | postcts_gate_TT | 10.2 | last meaningful line 0.2 h ago (1658/1658 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | 5_2_route | 8.0 | last meaningful line 0.1 h ago (129/129 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3681869 | slw_st_b_v2 | 5_1_grt | 4.5 | last meaningful line 0.2 h ago (281/1022 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | postcts_gate_FF | 6.9 | last meaningful line 0.1 h ago (1075/1075 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_stm_v1__cle34a73c3-4063338 | slw_stm_v1 | 5_2_route | 10.0 | drt_violations best 26612 last 26612 rows 2 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc10 | qc-hc3-lec-r8-nearest | qc-hc3-lec-r8-nearest | - | 6.0 |  | NO-DATA: no log found |  |
| epyc10 | qccollslec_h4 | qccollslec_h4 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc11 | ap-ageom-kw-slw-su-c--cl92142dac-grt-3717814 | slw-su-c--cl92142dac-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 11.5 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | postcts_gate_TT | 7.1 | last meaningful line 0.0 h ago (774/774 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 5_2_route | 8.1 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | 5_2_route | 11.5 | drt_violations best 18551 last 18551 rows 2 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 5_1_grt | 6.8 | last meaningful line 0.3 h ago (1113/1130 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | 5_2_route | 11.3 | drt_violations best 141847 last 141847 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | 5_2_route | 11.5 | drt_violations best 138497 last 138497 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2533872 | slw_hc3 | 5_2_route | 5.1 | last meaningful line 0.0 h ago (119/119 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | 4_1_cts | 1.8 | last meaningful line 0.0 h ago (5356/5356 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | 5_2_route | 11.3 | drt_violations best 24459 last 24459 rows 2 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-320042 | slw_st_b_v2 | generate_abstract | 11.3 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 10.5 |  | NO-DATA: no log found |  |
| epyc11 | otc-3389445-25127 | 3389445 | signoff | 4.1 | last meaningful line 4.0 h ago (3/3 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_154417_1016084-i2t-1425156 | eco_20261124_154417_1016084-i2t | 5_2_route | 1.8 | last meaningful line 0.1 h ago (263/263 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i1-3176761 | eco_20261124_190641_1260390-i1 | 5_2_route | 4.4 | drt_violations best 247 last 247 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i1-3660942 | eco_20261124_200101_1087713-i1 | 5_2_route | 3.8 | last meaningful line 0.2 h ago (281/282 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_204246_1187010-i1-249436 | eco_20261124_204246_1187010-i1 | 5_2_route | 2.9 | last meaningful line 0.1 h ago (267/267 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_034700_3857841-i1-2214083 | eco_20261125_034700_3857841-i1 | 5_2_route | 1.2 | last meaningful line 0.0 h ago (119/119 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-491987 | sle_hc0 | 5_2_route | 9.9 | drt_violations best 139148 last 139148 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-1254949 | sle_hc2 | 5_2_route | 9.5 | drt_violations best 12750 last 12750 rows 2 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1216203 | sle_st_b_v1 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (5436/5436 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-360401 | sle_st_b_v2 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3668964 | sle_st_b_v2 | postcts_gate_TT | 4.8 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3657462 | slw_stm_v2 | 6_report | 10.7 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-2459734-26514 | 2459734 | signoff | 0.6 | last meaningful line 0.5 h ago (3/3 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | otc-3544630-5805 | 3544630 | signoff | 2.2 | last meaningful line 2.1 h ago (3/3 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_165709_1862160-i1-2284188 | eco_20261124_165709_1862160-i1 | 5_2_route | 0.6 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_201339_3412955-i1-1739609 | eco_20261124_201339_3412955-i1 | 5_2_route | 0.8 | last meaningful line 0.1 h ago (127/127 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_204708_4151707-i1t-4056582 | eco_20261124_204708_4151707-i1t | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (143/143 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 9.7 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-1559108 | cbn_q01 | pregrt_ff_hold | 4.2 | repair_Violations best 1266 last 1276 rows 124 | YOUNG: evidence 1.8 h < 2.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 4_1_cts | 4.4 | last meaningful line 0.3 h ago (10855/10855 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-2222980 | sle_fw_v2 | postcts_gate_FF | 11.6 | last meaningful line 0.2 h ago (834/834 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 11.6 | drt_violations best 412199 last 412199 rows 1 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | 5_2_route | 11.8 | last meaningful line 0.3 h ago (283/284 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | 5_2_route | 11.7 | last meaningful line 0.3 h ago (270/271 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 5_2_route | 11.8 | last meaningful line 0.3 h ago (277/278 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-2253577 | slw_hc2 | 5_2_route | 11.6 | drt_violations best 12930 last 12930 rows 2 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-1524868 | slw_sc_v1 | 5_1_grt | 4.2 | last meaningful line 0.3 h ago (1971/1999 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | 5_2_route | 11.7 | drt_violations best 128832 last 128832 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | generate_abstract | 16.0 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | 5_2_route | 11.6 | drt_violations best 121792 last 121792 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i3-2609460 | eco_20261123_171023_3055226-i3 | 5_2_route | 3.6 | last meaningful line 0.3 h ago (289/290 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_145005_2036075-i3-424023 | eco_20261124_145005_2036075-i3 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (144/144 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i2-1757367 | eco_20261124_175441_992552-i2 | 5_2_route | 1.7 | drt_violations best 5576 last 5576 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i1-2124005 | eco_20261124_192157_3493836-i1 | 5_2_route | 3.9 | drt_violations best 16 last 16 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i1-2232939 | eco_20261124_235631_1843084-i1 | 5_2_route | 1.5 | last meaningful line 0.2 h ago (260/261 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | postcts_gate_FF | 12.9 | last meaningful line -0.0 h ago (65081/65081 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 5_2_route | 12.9 | drt_violations best 162445 last 162445 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 5_2_route | 12.9 | last meaningful line 0.3 h ago (268/269 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 5_2_route | 12.9 | last meaningful line 0.4 h ago (265/266 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | 5_2_route | 12.9 | drt_violations best 8892 last 8892 rows 3 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | 5_2_route | 12.9 | drt_violations best 13429 last 13429 rows 2 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 12.8 | drt_violations best 478667 last 478667 rows 1 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 5_2_route | 12.9 | last meaningful line 0.3 h ago (271/272 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 5_2_route | 12.9 | last meaningful line 0.3 h ago (281/282 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | 5_2_route | 12.9 | drt_violations best 176085 last 176085 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | 6_report | 12.9 | last meaningful line 0.0 h ago (13/13 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 12.9 | last meaningful line 0.3 h ago (134/134 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 5_2_route | 12.9 | last meaningful line 0.3 h ago (270/271 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 5_2_route | 12.9 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 5_2_route | 12.9 | last meaningful line 0.5 h ago (274/275 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | 5_2_route | 12.9 | drt_violations best 98742 last 98742 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 12.8 | drt_violations best 450083 last 450083 rows 1 | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 5_2_route | 12.9 | last meaningful line 0.6 h ago (265/266 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc8 | eco-abs-2516034 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | otc-120424-12773 | 120424 | signoff | 2.6 | last meaningful line 2.5 h ago (3/3 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3-32256 | eco_20261123_164145_1995767-i3 | 5_1_grt | 1.1 | last meaningful line 0.2 h ago (258/672 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_025941_3548303-i1t-1829547 | eco_20261125_025941_3548303-i1t | 5_2_route | 2.0 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_030756_3907869-i1-2163277 | eco_20261125_030756_3907869-i1 | 5_2_route | 1.8 | last meaningful line 0.0 h ago (258/259 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 9.8 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-4079824 | col_h10_r0_p1__t1 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (1536/1536 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-4181949 | col_h10_r0_p4__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl8b686b3e-4180491 | col_h10_r2__t1 | 3_3_place_gp | 0.1 | last meaningful line 0.0 h ago (192/192 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-4081688 | col_h10_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.458 last 0.4581 rows 9 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-4079818 | col_h9_r0_p2__t1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3602/3602 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv291547b4-4168936 | col_h9_r0_p2__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-296584 | col_h9_r0_p3__t1 | 4_2_tapbal_grt | 0.8 | last meaningful line 0.3 h ago (62/69 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-4169454 | col_h9_r0_p5__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 1424 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-4083596 | col_h9_r1__t1 | 3_3_place_gp | 0.2 | overflow best 0.5402 last 0.5402 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 4_1_cts | 0.1 | repair_Violations best 19 last 28 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t5-284167 | dsdv_slice_c1x_C__t5 | 1_1_yosys_canonicalize | 0.9 | last meaningful line 0.2 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-4170435 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 9.6 | drt_violations best 1536 last 1792 rows 19 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | 5_1_grt | 9.2 | last meaningful line 0.2 h ago (294/1298 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_2_route | 9.8 | last meaningful line 0.3 h ago (283/284 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-667540 | sle_hc1 | 5_2_route | 9.9 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 9.9 | last meaningful line 0.1 h ago (284/285 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1102342 | kv3_hg_v1p3__r838481cd7 | 4_1_cts | 2.9 | last meaningful line 0.2 h ago (7010/7010 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v6-102352 | kv3_hgi_v6 | 5_1_grt | 3.3 | last meaningful line 0.1 h ago (297/298 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 5_2_route | 16.0 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v3-1442734 | sle_fw_v3 | postcts_gate_FF | 9.7 | last meaningful line 0.2 h ago (827/827 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 5_2_route | 11.6 | last meaningful line 0.1 h ago (129/129 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 4_1_cts | 3.7 | last meaningful line 0.1 h ago (5768/5768 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 5_1_grt | 8.0 | last meaningful line 0.1 h ago (1259/1265 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 5_2_route | 9.7 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 7.9 | drt_violations best 41642 last 41642 rows 2 | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | pregrt_ff_hold | 5.4 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.8 h < 2.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | 6_report | 14.0 | last meaningful line 0.2 h ago (70/70 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3325358 | slw_fw_v1 | pregrt_ff_hold | 5.4 | repair_TNS best 40105.9 last 40105.9 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 15.9 | drt_violations best 398476 last 398476 rows 1 | YOUNG: evidence 5.9 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 5_1_grt | 6.5 | last meaningful line 0.2 h ago (140/140 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | postcts_gate_TT | 7.7 | last meaningful line 0.0 h ago (361/361 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 5_2_route | 11.6 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 5_2_route | 11.6 | last meaningful line 0.5 h ago (276/277 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1e5219ea-4177722 | slw_su_l0 | 5_2_route | 7.8 | drt_violations best 19339 last 19339 rows 3 | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-3090069 | slw_su_l0 | 5_2_route | 5.5 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 9.8 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 9.8 |  | NO-DATA: no log found |  |
| intel1 | otc-2434312-2110 | 2434312 | flow | 4.0 | last meaningful line 0.7 h ago (5516/5516 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | otc-3190981-22207 | 3190981 | grt | 0.3 | last meaningful line 0.2 h ago (31/32 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-4000256-29997 | 4000256 | eq11 | 1.7 | last meaningful line 0.0 h ago (789769/789769 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | otc-4001240-3461 | 4001240 | eq11 | 1.7 | last meaningful line 0.0 h ago (789769/789769 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i2-2930338 | eco_20261123_191853_2879776-i2 | 5_2_route | 3.9 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | ap-ageom-kw-kv3-hgi-v2--cle0015330-grt-1747094 | kv3-hgi-v2--cle0015330-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-98785 | coll_ftm | 5_2_route | 1.7 | drt_violations best 10288 last 10288 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | dpkit-kv3_hgi_v7-3807426 | kv3_hgi_v7 | 3_3_place_gp | 0.6 | overflow best 0.2184 last 0.2184 rows 32 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-kv3_io_ft-2778217 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5442 last 5442 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-kv3_pc_v1__cl4ea58a5c__r877307f5d-3039255 | kv3_pc_v1 | 3_3_place_gp | 0.9 | overflow best 0.7644 last 0.7644 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8422a4b86-973415 | kv3_pc_v1 | 3_5_place_dp | 2.8 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-native59-1418182 | native59 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (442/442 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 11.4 | last meaningful line 0.3 h ago (274/275 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 5_2_route | 11.6 | drt_violations best 406352 last 406352 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-2390236 | slw_st_b_v1 | 5_1_grt | 4.4 | last meaningful line 0.1 h ago (1196/1202 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | otc-560426-5193 | 560426 | signoff | 0.3 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | otc-3928927-26455 | 3928927 | ot_bind_native_7d4bc5882447b2d9cdf93e3b | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-4184672 | col_h9_r1__t1 | 3_1_place_gp_skip_io | 0.1 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | 5_2_route | 8.9 | drt_violations best 1820 last 3607 rows 19 | before-window best 33912, window best 1820 | PROGRESS: drt_violations improved 94.6 % in window |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | pregrt_ff_hold | 8.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 23.9 | drt_violations best 15279 last 15279 rows 16 | before-window best 16673, window best 15279 | PROGRESS: drt_violations improved 8.4 % in window |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 16.2 | drt_violations best 11997 last 11997 rows 11 | before-window best 521993, window best 11997 | PROGRESS: drt_violations improved 97.7 % in window |  |
| epyc2 | prd-eco_20261124_204127_3434498-i1-3663711 | eco_20261124_204127_3434498-i1 | 5_1_grt | 0.3 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 36.6 | drt_violations best 7726 last 11676 rows 19 | before-window best 9091, window best 7726 | PROGRESS: drt_violations improved 15.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 21.4 | drt_violations best 3168 last 3168 rows 14 | before-window best 78233, window best 3168 | PROGRESS: drt_violations improved 96.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 17.5 | drt_violations best 22894 last 22894 rows 4 | before-window best 504597, window best 22894 | PROGRESS: drt_violations improved 95.5 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 16.2 | drt_violations best 510309 last 510309 rows 1 | before-window best 510309, window best 510309 | PROGRESS: drt_violations: active iteration at 145621 < best completed total 510309 (in-ite |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 16.0 | drt_violations best 457993 last 457993 rows 1 | before-window best 457993, window best 457993 | PROGRESS: drt_violations: active iteration at 126195 < best completed total 457993 (in-ite |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-2092169 | slw_sc_v1 | 5_1_grt | 3.9 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 21.6 | drt_violations best 66304 last 66304 rows 9 | before-window best 74091, window best 66304 | PROGRESS: drt_violations improved 10.5 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 17.7 | drt_violations best 54030 last 54030 rows 6 | before-window best 400194, window best 54030 | PROGRESS: drt_violations improved 86.5 % in window |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 12.8 | drt_violations best 119058 last 119058 rows 2 | before-window best 379431, window best 119058 | PROGRESS: drt_violations improved 68.6 % in window |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | 5_2_route | 12.9 | drt_violations best 72 last 72 rows 54 | before-window best 149425, window best 72 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 12.9 | drt_violations best 12823 last 12823 rows 12 | before-window best 68683, window best 12823 | PROGRESS: drt_violations improved 81.3 % in window |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | pregrt_ff_hold | 6.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | 5_2_route | 15.9 | drt_violations best 27105 last 27105 rows 2 | before-window best 156960, window best 27105 | PROGRESS: drt_violations improved 82.7 % in window |  |
