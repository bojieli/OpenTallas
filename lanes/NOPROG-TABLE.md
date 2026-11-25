# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 22:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'UNSIGNABLE': 3, 'GRT-LABEL': 10, 'YOUNG': 129, 'NO-DATA': 21, 'PROGRESS': 25}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 13.3 | last meaningful line 12.0 h ago (48/140 lines) | NO-PROGRESS: no new non-iteration log line for 12.0 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 5_1_grt | 13.6 | grt rounds 2 overflow 5:42234 -> 10:42876 | UNSIGNABLE: GRT overflow flat: overflow 42234 at iteration 5 -> 42876 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 16.4 | last meaningful line 12.8 h ago (48/206 lines) | NO-PROGRESS: no new non-iteration log line for 12.8 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | 5_1_grt | 10.7 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 8.6 | repair_TNS best 827598 last 827598 rows 1 | before-window best 827598, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 5_1_grt | 15.3 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_hg_v1__r889141819-1619104 | kv3_hg_v1__r889141819 | 5_1_grt | 4.5 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_hg_v1__r88f4bfb40-1671162 | kv3_hg_v1__r88f4bfb40 | 5_1_grt | 4.5 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_hgi-373156 | kv3_hgi | 5_1_grt | 5.2 | grt rounds 2 overflow 5:32028 -> 10:31100 | GRT-LABEL: DESIGN-FAIL: overflow 31100 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_hgi-3860531 | kv3_hgi | 5_1_grt | 2.3 | grt rounds 2 overflow 5:28316 -> 10:12348 | GRT-LABEL: DESIGN-FAIL: overflow 12348 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-514739 | kv3_hgi_v2 | 5_1_grt | 2.0 | grt rounds 2 overflow 5:17858 -> 10:8709 | GRT-LABEL: DESIGN-FAIL: overflow 8709 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r85c02c25c-3151820 | kv3_pc | 5_1_grt | 2.6 | grt rounds 1 overflow 5:7303 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | 5_1_grt | 13.5 | grt rounds 2 overflow 5:52829 -> 10:36669 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | 5_1_grt | 8.7 | grt rounds 2 overflow 5:94600 -> 10:59159 | GRT-LABEL: DESIGN-FAIL: overflow 59159 at round 10 > 1000 |  |
| epyc2 | dpkit-kv3_hgi_v8-2737550 | kv3_hgi_v8 | 5_1_grt | 3.8 | grt rounds 2 overflow 5:54135 -> 10:40850 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | 5_1_grt | 10.5 | grt rounds 2 overflow 5:34556 -> 10:3532 | GRT-LABEL: DESIGN-FAIL: overflow 3532 at round 10 > 1000 |  |
| epyc10 | dpkit-glue-1294589 | glue | 5_1_grt | 4.7 | last meaningful line 0.2 h ago (142/142 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r8dffc461a-1676050 | kv3_hg_v1__r8dffc461a | 5_1_grt | 4.5 | last meaningful line 0.0 h ago (186/186 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p2-1802854 | kv3_hg_v1p2 | pregrt_ff_hold | 4.4 | repair_Violations best 3573 last 3573 rows 31 | YOUNG: evidence 1.8 h < 2.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p3__r81da466fe-1840159 | kv3_hg_v1p3__r81da466fe | pregrt_ff_hold | 4.4 | repair_Violations best 693 last 727 rows 138 | YOUNG: evidence 1.9 h < 2.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | 4_1_cts | 4.8 | last meaningful line 0.2 h ago (11293/11293 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-2844240 | kv3_pc | 5_1_grt | 2.7 | last meaningful line 0.0 h ago (87/87 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r8b421e514-2986767 | kv3_pc | 5_1_grt | 2.6 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r882954158-3053902 | kv3_pc | 5_1_grt | 2.6 | last meaningful line 0.1 h ago (152/152 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-3561929 | kv3_pc_v1 | 3_5_place_dp | 2.4 | last meaningful line 0.5 h ago (32/32 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r84d0332e1-3581607 | kv3_pc_v1 | 3_5_place_dp | 2.4 | last meaningful line 0.3 h ago (32/32 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r884969661-3601103 | kv3_pc_v1 | 3_5_place_dp | 2.4 | last meaningful line 0.3 h ago (32/32 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8afe1e027-3618066 | kv3_pc_v1 | 3_5_place_dp | 2.4 | last meaningful line 0.5 h ago (32/32 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8c9cba7ae-3633962 | kv3_pc_v1 | 3_5_place_dp | 2.4 | last meaningful line 0.5 h ago (32/32 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-3669242 | kv3_pc_v1 | 3_5_place_dp | 2.4 | last meaningful line 0.5 h ago (32/32 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-1535838 | kv3_pv_v12 | pregrt_ff_hold | 3.0 | repair_TNS best 42717.5 last 42717.5 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v12-3355795 | kv3_pv_v12 | 4_1_cts | 2.5 | last meaningful line 0.1 h ago (9308/9308 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-4187490 | kv3_pv_v3 | 4_1_cts | 2.2 | last meaningful line 0.2 h ago (12040/12040 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-native59-3384403 | native59 | pregrt_ff_hold | 3.7 | repair_TNS best 6612.64 last 6612.64 rows 1 | YOUNG: evidence 1.4 h < 2.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_2_route | 12.5 | last meaningful line 0.5 h ago (270/271 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | 5_2_route | 9.3 | last meaningful line 0.4 h ago (264/265 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | 5_2_route | 9.7 | last meaningful line 0.4 h ago (275/276 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | 5_2_route | 10.3 | drt_violations best 127354 last 127354 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 11.4 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_2_route | 11.4 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | postcts_gate_FF | 11.5 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | 5_2_route | 9.2 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3681869 | slw_st_b_v2 | postcts_gate_TT | 5.7 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | 5_2_route | 8.2 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_stm_v1__cle34a73c3-4063338 | slw_stm_v1 | 6_report | 11.2 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_055922_2792445-i1-2623359 | eco_20261125_055922_2792445-i1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | qc-hc3-lec-r8-nearest | qc-hc3-lec-r8-nearest | - | 7.2 |  | NO-DATA: no log found |  |
| epyc10 | qccollslec_h4 | qccollslec_h4 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 12.7 | drt_violations best 329677 last 329677 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | postcts_gate_FF | 8.3 | last meaningful line 0.2 h ago (765/765 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 5_2_route | 9.3 | drt_violations best 168194 last 168194 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | 6_report | 12.8 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | postcts_gate_TT | 8.0 | last meaningful line 0.1 h ago (833/833 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | 5_2_route | 12.6 | drt_violations best 20042 last 20042 rows 2 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | 5_2_route | 12.7 | drt_violations best 13168 last 13168 rows 3 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2533872 | slw_hc3 | 5_2_route | 6.4 | last meaningful line 0.1 h ago (266/267 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | 4_1_cts | 3.0 | last meaningful line 0.0 h ago (5492/5492 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | 5_2_route | 12.5 | drt_violations best 9 last 9 rows 12 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 11.7 |  | NO-DATA: no log found |  |
| epyc11 | otc-3389445-25127 | 3389445 | signoff | 5.3 | last meaningful line 5.3 h ago (3/3 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_154417_1016084-i2t-1425156 | eco_20261124_154417_1016084-i2t | 5_2_route | 3.1 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i1-3176761 | eco_20261124_190641_1260390-i1 | 5_2_route | 5.6 | drt_violations best 247 last 247 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i1-3660942 | eco_20261124_200101_1087713-i1 | 5_2_route | 5.0 | drt_violations best 37 last 37 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_204246_1187010-i1-249436 | eco_20261124_204246_1187010-i1 | 5_2_route | 4.1 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_034700_3857841-i1-2214083 | eco_20261125_034700_3857841-i1 | 5_2_route | 2.4 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_054540_316017-i1-897106 | eco_20261125_054540_316017-i1 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (144/144 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-491987 | sle_hc0 | 6_report | 11.2 | last meaningful line 0.1 h ago (69/69 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1216203 | sle_st_b_v1 | pregrt_ff_hold | 2.3 | repair_TNS best 19705 last 19705 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-360401 | sle_st_b_v2 | pregrt_ff_hold | 1.3 | repair_TNS best 67066.7 last 67066.7 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3668964 | sle_st_b_v2 | 5_2_route | 6.0 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | otc-2459734-26514 | 2459734 | signoff | 1.8 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | otc-3544630-5805 | 3544630 | signoff | 3.4 | last meaningful line 3.3 h ago (3/3 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | prd-count-p1_bc-1739609 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_165709_1862160-i1-2284188 | eco_20261124_165709_1862160-i1 | 5_2_route | 1.9 | drt_violations best 46 last 46 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_204127_3434498-i1-3663711 | eco_20261124_204127_3434498-i1 | 5_2_route | 1.5 | drt_violations best 6 last 6 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc2 | prd-eco_20261124_204708_4151707-i1t-4056582 | eco_20261124_204708_4151707-i1t | 5_2_route | 1.4 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 10.9 |  | NO-DATA: no log found |  |
| epyc2 | so_1780430_ff_10700 | so_1780430_ff_10700 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc2 | so_1780430_tt_10700 | so_1780430_tt_10700 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc7 | ap-ageom-kw-sle-st-a-v2--pv4242de79-grt-3291601 | sle-st-a-v2--pv4242de79-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-1559108 | cbn_q01 | 5_1_grt | 5.5 | last meaningful line 0.2 h ago (267/1273 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 4_1_cts | 5.6 | last meaningful line 1.0 h ago (10883/10883 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | 5_2_route | 13.1 | drt_violations best 136857 last 136857 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | 5_2_route | 12.9 | drt_violations best 155414 last 155414 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 5_2_route | 13.0 | drt_violations best 150654 last 150654 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-2253577 | slw_hc2 | 6_report | 12.9 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | 5_2_route | 13.0 | drt_violations best 18207 last 18207 rows 2 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc7 | otc-2231715-16661 | 2231715 | signoff | 0.5 | last meaningful line 0.5 h ago (3/3 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i3-2609460 | eco_20261123_171023_3055226-i3 | 5_2_route | 4.9 | last meaningful line 0.2 h ago (299/300 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_145005_2036075-i3-424023 | eco_20261124_145005_2036075-i3 | 5_2_route | 1.5 | last meaningful line 0.2 h ago (260/261 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i1-2232939 | eco_20261124_235631_1843084-i1 | 5_2_route | 2.7 | drt_violations best 246 last 246 rows 3 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | prd-fin-1757367 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (65/65 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_2_route | 14.1 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 5_2_route | 14.1 | drt_violations best 162445 last 162445 rows 1 | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 5_2_route | 14.1 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 5_2_route | 14.1 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 5_2_route | 14.1 | last meaningful line 0.5 h ago (279/280 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 5_2_route | 14.1 | drt_violations best 127432 last 127432 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | 5_2_route | 14.1 | drt_violations best 31424 last 31424 rows 2 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 14.1 | last meaningful line 0.7 h ago (264/265 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 5_2_route | 14.1 | last meaningful line 0.7 h ago (276/277 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 5_2_route | 14.1 | last meaningful line 0.5 h ago (278/279 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 5_2_route | 14.1 | last meaningful line 0.5 h ago (282/283 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | 5_2_route | 14.2 | drt_violations best 7737 last 7737 rows 3 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 5_2_route | 14.1 | last meaningful line 0.5 h ago (273/274 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | eco-abs-1816407 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-120424-12773 | 120424 | signoff | 3.9 | last meaningful line 3.8 h ago (3/3 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3-32256 | eco_20261123_164145_1995767-i3 | 5_2_route | 2.3 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_025941_3548303-i1t-1829547 | eco_20261125_025941_3548303-i1t | 5_2_route | 3.2 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 11.0 |  | NO-DATA: no log found |  |
| epyc8 | so_1310884_ff_11169 | so_1310884_ff_11169 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc8 | so_1310884_tt_11169 | so_1310884_tt_11169 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc8 | so_1356407_ff_86387 | so_1356407_ff_86387 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc8 | so_1356407_tt_86387 | so_1356407_tt_86387 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc8 | so_1766798_ff_96500 | so_1766798_ff_96500 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | so_1766798_tt_96500 | so_1766798_tt_96500 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | so_429798_ff_14513 | so_429798_ff_14513 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc8 | so_429798_tt_14513 | so_429798_tt_14513 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc9 | ap-ageom-kw-col-h9-r1--t1--cl49d7a23e--pv3a0a8b60-grt-4107465 | col-h9-r1--t1--cl49d7a23e--pv3a0a8b60-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pv07945c1e-55623 | col_h10_r0_p4__t1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-4079818 | col_h9_r0_p2__t1 | 4_2_tapbal_grt | 1.4 | last meaningful line 0.0 h ago (100/100 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-296584 | col_h9_r0_p3__t1 | lec | 2.1 | LEC last write 0.2 h ago | YOUNG: evidence 2.1 h < 6 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | lec | 1.4 | LEC last write 0.6 h ago | YOUNG: evidence 1.4 h < 6 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | pregrt_ff_hold | 0.5 | repair_TNS best 80115.6 last 80115.6 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t5-284167 | dsdv_slice_c1x_C__t5 | lec | 2.1 | LEC last write 0.1 h ago | YOUNG: evidence 2.1 h < 6 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-4170435 | dsdv_slice_lepw_mu_C__t1 | 1_1_yosys_canonicalize | 1.4 | last meaningful line 0.5 h ago (146/146 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-12029 | ot_s81sl_leaf__t53 | 1_synth | 0.0 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_2_route | 11.0 | drt_violations best 474459 last 474459 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-667540 | sle_hc1 | 5_2_route | 11.1 | drt_violations best 18198 last 18198 rows 2 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 11.2 | drt_violations best 274895 last 274895 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | otc-153621-1032 | 153621 | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (452/452 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1102342 | kv3_hg_v1p3__r838481cd7 | pregrt_ff_hold | 4.1 | repair_TNS best 208493 last 208493 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-kv3_hgi_v6-102352 | kv3_hgi_v6 | 5_1_grt | 4.6 | last meaningful line 1.3 h ago (297/1305 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 5_2_route | 17.2 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 5_2_route | 12.9 | last meaningful line 0.3 h ago (267/268 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 4_1_cts | 5.0 | last meaningful line 0.2 h ago (5803/5803 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | postcts_gate_TT | 9.2 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 5_2_route | 10.9 | drt_violations best 144494 last 144494 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 9.1 | drt_violations best 3502 last 3502 rows 5 | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_1_grt | 6.7 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | generate_abstract | 15.3 | last meaningful line 0.1 h ago (32/32 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3325358 | slw_fw_v1 | pregrt_ff_hold | 6.7 | repair_TNS best 29926.8 last 29926.8 rows 1 | YOUNG: evidence 1.8 h < 2.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 5_1_grt | 7.7 | last meaningful line 0.1 h ago (1089/1106 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | postcts_gate_FF | 9.0 | last meaningful line 0.1 h ago (345/345 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 5_2_route | 12.9 | last meaningful line 0.1 h ago (265/266 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 5_2_route | 12.9 | drt_violations best 125787 last 125787 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1e5219ea-4177722 | slw_su_l0 | 5_2_route | 9.0 | drt_violations best 18 last 18 rows 13 | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-3090069 | slw_su_l0 | 5_2_route | 6.8 | drt_violations best 128742 last 128742 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 11.0 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 11.0 |  | NO-DATA: no log found |  |
| intel1 | otc-2434312-2110 | 2434312 | flow | 5.3 | last meaningful line 2.0 h ago (5516/5516 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel1 | otc-3190981-22207 | 3190981 | grt | 1.6 | last meaningful line 1.3 h ago (33/34 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | otc-4000256-29997 | 4000256 | eq11 | 3.0 | last meaningful line 0.0 h ago (791477/791477 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | otc-4001240-3461 | 4001240 | eq11 | 3.0 | last meaningful line 0.0 h ago (791477/791477 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | otc-562237-16869 | 562237 | grt | 0.6 | last meaningful line 0.5 h ago (31/32 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i2-2930338 | eco_20261123_191853_2879776-i2 | 5_2_route | 5.1 | last meaningful line 0.3 h ago (286/287 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel2 | dpkit-kv3_hgi_v2__cle0015330-3208477 | kv3_hgi_v2 | 5_1_grt | 1.0 | last meaningful line 0.2 h ago (288/1292 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-867671 | kv3_io_ft | 5_1_grt | 0.5 | last meaningful line 0.1 h ago (243/379 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl4ea58a5c__r877307f5d-3039255 | kv3_pc_v1 | 3_5_place_dp | 2.1 | last meaningful line 0.5 h ago (32/32 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-native59-1418182 | native59 | 3_3_place_gp | 1.4 | overflow best 0.099 last 0.099 rows 284 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 12.6 | drt_violations best 367946 last 367946 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 5_2_route | 12.8 | drt_violations best 406352 last 406352 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-2390236 | slw_st_b_v1 | postcts_gate_TT | 5.6 | last meaningful line -0.0 h ago (83862/83862 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | otc-560426-5193 | 560426 | signoff | 1.6 | last meaningful line 1.5 h ago (3/3 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | so_2914960_ff_52510 | so_2914960_ff_52510 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_2914960_tt_52510 | so_2914960_tt_52510 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | 5_2_route | 10.2 | drt_violations best 1820 last 2437 rows 21 | before-window best 33912, window best 1820 | PROGRESS: drt_violations improved 94.6 % in window |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | pregrt_ff_hold | 10.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 25.2 | drt_violations best 14980 last 63558 rows 18 | before-window best 16673, window best 14980 | PROGRESS: drt_violations improved 10.2 % in window |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 17.5 | drt_violations best 8379 last 8379 rows 13 | before-window best 123388, window best 8379 | PROGRESS: drt_violations improved 93.2 % in window |  |
| epyc2 | prd-eco_20261124_215436_3656110-i1-2033351 | eco_20261124_215436_3656110-i1 | 5_1_grt | 0.3 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 44.6 | drt_violations best 10129 last 21070 rows 19 | before-window best 10129, window best 21070 | PROGRESS: drt_violations: falling inside the active iteration (21070 -> 18562) |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 37.9 | drt_violations best 7726 last 11676 rows 19 | before-window best 7726, window best 11676 | PROGRESS: drt_violations: falling inside the active iteration (11676 -> 9304) |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 22.6 | drt_violations best 2937 last 2937 rows 15 | before-window best 11728, window best 2937 | PROGRESS: drt_violations improved 75.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 18.8 | drt_violations best 15295 last 15295 rows 6 | before-window best 504597, window best 15295 | PROGRESS: drt_violations improved 97.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 17.4 | drt_violations best 122131 last 122131 rows 2 | before-window best 510309, window best 122131 | PROGRESS: drt_violations improved 76.1 % in window |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 12.8 | drt_violations best 136685 last 136685 rows 2 | before-window best 412199, window best 136685 | PROGRESS: drt_violations improved 66.8 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 17.2 | drt_violations best 106839 last 106839 rows 2 | before-window best 457993, window best 106839 | PROGRESS: drt_violations improved 76.7 % in window |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 22.8 | drt_violations best 66304 last 66304 rows 9 | before-window best 68064, window best 66304 | PROGRESS: drt_violations improved 2.6 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 18.9 | drt_violations best 53466 last 53466 rows 7 | before-window best 123176, window best 53466 | PROGRESS: drt_violations improved 56.6 % in window |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | 5_2_route | 12.9 | drt_violations best 10589 last 10589 rows 3 | before-window best 121792, window best 10589 | PROGRESS: drt_violations improved 91.3 % in window |  |
| epyc7 | prd-eco_20261124_192157_3493836-i1-2124005 | eco_20261124_192157_3493836-i1 | 5_2_route | 5.2 | drt_violations best 0 last 0 rows 4 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 14.1 | drt_violations best 478667 last 478667 rows 1 | before-window best 478667, window best 478667 | PROGRESS: drt_violations: active iteration at 189772 < best completed total 478667 (in-ite |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 14.1 | drt_violations best 450083 last 450083 rows 1 | before-window best 450083, window best 450083 | PROGRESS: drt_violations: active iteration at 376305 < best completed total 450083 (in-ite |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 14.0 | drt_violations best 97102 last 97102 rows 3 | before-window best 379431, window best 97102 | PROGRESS: drt_violations improved 74.4 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 14.1 | drt_violations best 11145 last 11145 rows 13 | before-window best 26414, window best 11145 | PROGRESS: drt_violations improved 57.8 % in window |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 10.8 | drt_violations best 1431 last 1431 rows 22 | before-window best 84487, window best 1431 | PROGRESS: drt_violations improved 98.3 % in window |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 17.2 | drt_violations best 398476 last 398476 rows 1 | before-window best 398476, window best 398476 | PROGRESS: drt_violations: active iteration at 252577 < best completed total 398476 (in-ite |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | pregrt_ff_hold | 7.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | 5_2_route | 17.1 | drt_violations best 1106 last 1106 rows 4 | before-window best 156960, window best 1106 | PROGRESS: drt_violations improved 99.3 % in window |  |
| intel2 | dpkit-coll_ftm-1842242 | coll_ftm | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
