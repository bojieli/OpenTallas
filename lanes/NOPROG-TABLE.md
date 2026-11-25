# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 19:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'UNSIGNABLE': 3, 'GRT-LABEL': 2, 'YOUNG': 145, 'NO-DATA': 13, 'PROGRESS': 23}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 10.8 | last meaningful line 9.5 h ago (48/137 lines) | NO-PROGRESS: no new non-iteration log line for 9.5 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 5_1_grt | 11.1 | grt rounds 2 overflow 5:42234 -> 10:42876 | UNSIGNABLE: GRT overflow flat: overflow 42234 at iteration 5 -> 42876 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 13.9 | last meaningful line 10.3 h ago (48/193 lines) | NO-PROGRESS: no new non-iteration log line for 10.3 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | 5_1_grt | 8.2 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 6.1 | repair_TNS best 827598 last 827598 rows 1 | before-window best 827598, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 5_1_grt | 12.8 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | pregrt_ff_hold | 8.0 | repair_TNS best 315444 last 315444 rows 1 | before-window best 315444, window best 315444 | NO-PROGRESS: repair_TNS best 315444 vs 315444 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | 5_1_grt | 11.0 | grt rounds 2 overflow 5:52829 -> 10:36669 | GRT-LABEL: DESIGN-FAIL: overflow 36669 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 5_1_grt | 12.1 | grt rounds 2 overflow 5:83232 -> 10:63283 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-glue-1294589 | glue | pregrt_ff_hold | 2.2 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | 5_2_route | 7.7 | drt_violations best 1936 last 1936 rows 16 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r889141819-1619104 | kv3_hg_v1__r889141819 | 4_1_cts | 2.0 | last meaningful line 0.0 h ago (7587/7587 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r88f4bfb40-1671162 | kv3_hg_v1__r88f4bfb40 | 4_1_cts | 2.0 | last meaningful line 0.1 h ago (7636/7636 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r8dffc461a-1676050 | kv3_hg_v1__r8dffc461a | 4_1_cts | 2.0 | last meaningful line 0.1 h ago (7694/7694 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p2-1802854 | kv3_hg_v1p2 | 4_1_cts | 1.9 | last meaningful line 0.1 h ago (7150/7150 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p3__r81da466fe-1840159 | kv3_hg_v1p3__r81da466fe | 4_1_cts | 1.9 | last meaningful line 0.0 h ago (7007/7007 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-373156 | kv3_hgi | 5_1_grt | 2.7 | last meaningful line 2.0 h ago (296/1303 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | 4_1_cts | 2.3 | last meaningful line 0.3 h ago (11103/11103 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-2844240 | kv3_pc | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3765/3765 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r8b421e514-2986767 | kv3_pc | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3693/3693 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r85c02c25c-3151820 | kv3_pc | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r882954158-3053902 | kv3_pc | 4_1_cts | 0.1 | last meaningful line 0.1 h ago (38/38 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-1535838 | kv3_pv_v12 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (8931/8931 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | 5_1_grt | 6.2 | last meaningful line 0.5 h ago (267/1273 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-native59-3384403 | native59 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (5480/5480 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | postcts_gate_FF | 10.0 | last meaningful line 0.3 h ago (1861/1861 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | postcts_gate_TT | 6.8 | last meaningful line -0.0 h ago (42750/42750 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | postcts_gate_TT | 7.2 | last meaningful line -0.0 h ago (93113/93113 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | 5_2_route | 7.8 | last meaningful line 0.1 h ago (136/136 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2793057 | sle_stm_v1 | 5_2_route | 9.5 | drt_violations best 145941 last 145941 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | postcts_gate_TT | 8.9 | last meaningful line -0.0 h ago (98540/98540 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | postcts_gate_TT | 8.9 | last meaningful line 0.0 h ago (1533/1533 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | postcts_gate_FF | 9.0 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | postcts_gate_TT | 6.7 | last meaningful line -0.0 h ago (38699/38699 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3681869 | slw_st_b_v2 | pregrt_ff_hold | 3.2 | repair_TNS best 15780.3 last 15780.3 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | postcts_gate_TT | 5.7 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_stm_v1__cle34a73c3-4063338 | slw_stm_v1 | 5_2_route | 8.7 | drt_violations best 156777 last 156777 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc10 | otc-3368288-2826 | 3368288 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (8/8 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-901577-23707 | 901577 | signoff | 5.0 | last meaningful line 5.0 h ago (3/3 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc10 | qc-colls-lec-h3 | qc-colls-lec-h3 | - | 3.1 |  | NO-DATA: no log found |  |
| epyc10 | qc-hc3-lec-r8-nearest | qc-hc3-lec-r8-nearest | - | 4.7 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 10.2 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 5_1_grt | 5.8 | last meaningful line 0.0 h ago (1091/1097 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 5_2_route | 6.8 | last meaningful line 0.2 h ago (138/138 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | 5_2_route | 10.3 | drt_violations best 146067 last 146067 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 5_1_grt | 5.5 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | 5_2_route | 10.1 | last meaningful line 0.2 h ago (281/282 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | 5_2_route | 10.2 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2533872 | slw_hc3 | 5_1_grt | 3.9 | last meaningful line 0.1 h ago (1029/1046 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | 3_3_place_gp | 0.5 | overflow best 0.2103 last 0.2103 rows 40 | YOUNG: stage 0.5 h < 1 h |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | 5_2_route | 10.0 | drt_violations best 152868 last 152868 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-320042 | slw_st_b_v2 | 5_2_route | 10.0 | drt_violations best 17771 last 17771 rows 2 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 9.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-3389445-25127 | 3389445 | signoff | 2.8 | last meaningful line 2.8 h ago (3/3 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i1-3176761 | eco_20261124_190641_1260390-i1 | 5_2_route | 3.1 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i1-3660942 | eco_20261124_200101_1087713-i1 | 5_2_route | 2.5 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_204246_1187010-i1-249436 | eco_20261124_204246_1187010-i1 | 5_1_grt | 1.6 | last meaningful line 0.9 h ago (237/1314 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc11 | so_1086046_ff_71982 | so_1086046_ff_71982 | signoff | 0.9 |  | NO-DATA: empty log |  |
| epyc11 | so_1086046_tt_71982 | so_1086046_tt_71982 | signoff | 0.9 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-kv3_hgi_v8-2737550 | kv3_hgi_v8 | tt_setup_repair | 1.3 | repair_Viol best 105 last 105 rows 11 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-491987 | sle_hc0 | 5_2_route | 8.7 | last meaningful line 0.0 h ago (266/267 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-1254949 | sle_hc2 | 5_2_route | 8.2 | last meaningful line 0.2 h ago (281/282 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3414126 | sle_hc2 | generate_abstract | 9.6 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__clcc5e3e61-3434617 | sle_hc2 | 5_2_route | 9.6 | drt_violations best 9578 last 9578 rows 3 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3568552 | sle_st_b_v1 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3668964 | sle_st_b_v2 | 5_1_grt | 3.5 | last meaningful line 0.1 h ago (143/143 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-4153401 | sle_stm_v2 | 5_2_route | 9.1 | drt_violations best 17969 last 17969 rows 3 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3657462 | slw_stm_v2 | 5_2_route | 9.4 | drt_violations best 124000 last 124000 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | otc-3544630-5805 | 3544630 | signoff | 0.9 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_165709_1862160-i1t-580795 | eco_20261124_165709_1862160-i1t | 5_2_route | 2.8 | drt_violations best 5855 last 5855 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 8.4 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 4_1_cts | 3.1 | last meaningful line 0.2 h ago (10798/10798 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-2222980 | sle_fw_v2 | postcts_gate_TT | 10.4 | last meaningful line 0.1 h ago (836/836 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 10.3 | drt_violations best 412199 last 412199 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | 5_2_route | 10.6 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | 5_2_route | 10.4 | last meaningful line 0.0 h ago (251/251 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 5_2_route | 10.5 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-2253577 | slw_hc2 | 5_2_route | 10.4 | drt_violations best 101260 last 101260 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-1524868 | slw_sc_v1 | 5_1_grt | 3.0 | repair_Remaining best 370109 last 370109 rows 36 | YOUNG: stage 0.8 h < 1 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-2092169 | slw_sc_v1 | 5_1_grt | 2.7 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | 5_2_route | 10.5 | drt_violations best 128832 last 128832 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | 5_2_route | 10.4 | drt_violations best 121792 last 121792 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc7 | prd-count-p1_tc-1496134 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i3-2609460 | eco_20261123_171023_3055226-i3 | 5_2_route | 2.4 | last meaningful line 0.2 h ago (132/132 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i2-1757367 | eco_20261124_175441_992552-i2 | 5_1_grt | 0.5 | last meaningful line 0.4 h ago (297/1395 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i1-2124005 | eco_20261124_192157_3493836-i1 | 5_2_route | 2.7 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i1-2232939 | eco_20261124_235631_1843084-i1 | 5_1_grt | 0.2 | last meaningful line 0.2 h ago (297/1297 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | postcts_gate_TT | 11.6 | last meaningful line -0.0 h ago (65451/65451 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 5_2_route | 11.6 | drt_violations best 162445 last 162445 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 5_2_route | 11.6 | last meaningful line 0.5 h ago (260/261 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 5_2_route | 11.6 | last meaningful line 0.5 h ago (130/130 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | 5_2_route | 11.7 | drt_violations best 105806 last 105806 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | 5_2_route | 11.7 | drt_violations best 103684 last 103684 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 11.6 | drt_violations best 478667 last 478667 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 5_2_route | 11.6 | last meaningful line 0.5 h ago (136/136 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 5_2_route | 11.6 | last meaningful line 0.1 h ago (275/276 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | 5_2_route | 11.6 | last meaningful line 0.5 h ago (279/280 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | 5_2_route | 11.6 | drt_violations best 27225 last 27225 rows 2 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | postcts_gate_FF | 11.6 | last meaningful line -0.0 h ago (71521/71521 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 5_2_route | 11.6 | last meaningful line 0.1 h ago (264/265 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 5_2_route | 11.6 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 5_2_route | 11.6 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | 5_2_route | 11.7 | drt_violations best 98742 last 98742 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 11.6 | last meaningful line 1.2 h ago (281/282 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 5_2_route | 11.6 | last meaningful line 0.3 h ago (260/260 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | otc-120424-12773 | 120424 | signoff | 1.4 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | otc-2900322-1356 | 2900322 | - | 3.7 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_012701_4018610-i1-2166955 | eco_20261125_012701_4018610-i1 | 5_2_route | 2.3 | drt_violations best 172 last 172 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_025941_3548303-i1t-1829547 | eco_20261125_025941_3548303-i1t | 5_1_grt | 0.7 | last meaningful line 0.2 h ago (140/140 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_030756_3907869-i1-2163277 | eco_20261125_030756_3907869-i1 | 5_1_grt | 0.6 | last meaningful line 0.0 h ago (169/169 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | prd-fin-2289287 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (65/65 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 8.5 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-col-h9-r0-p2--t1--cl0045af7b--pvd86cb19a-grt-1619439 | col-h9-r0-p2--t1--cl0045af7b--pvd86cb19a-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-col-h9-r0-p3--t1--cl8ce97bcb--pvc11684b5-grt-1920509 | col-h9-r0-p3--t1--cl8ce97bcb--pvc11684b5-grt | lec | 0.1 | LEC last write 0.1 h ago | YOUNG: evidence 0.1 h < 6 h |  |
| epyc9 | ap-ageom-kw-slice-station--t51-grt-2135369 | slice-station--t51-grt | lec | 0.1 | LEC last write 0.1 h ago | YOUNG: evidence 0.1 h < 6 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3746069 | col_h10_r0_p1__t1 | 3_3_place_gp | 0.6 | overflow best 0.461 last 0.461 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-2954633 | col_h10_r0_p1__t1 | 3_3_place_gp | 0.8 | last meaningful line 0.0 h ago (284/284 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-2956272 | col_h9_r0_p1__t1 | 3_3_place_gp | 0.8 | overflow best 0.266 last 0.266 rows 35 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pvcb7f0079-1236189 | col_h9_r0_p3__t1 | 3_5_place_dp | 1.2 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 8.3 | drt_violations best 1589 last 1589 rows 14 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t36-2961386 | ot_s81sl_leaf__t36 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (221/221 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t4-3729546 | serdes__t4 | 3_4_place_resized | 1.5 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_2_route | 8.5 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-667540 | sle_hc1 | postcts_gate_FF | 8.6 | last meaningful line -0.0 h ago (66534/66534 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t30__clcedefe91-1240625 | slice_station__t30 | 5_2_route | 1.2 | drt_violations best 2627 last 2627 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 8.7 | last meaningful line 0.0 h ago (269/269 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | otc-1674265-30050 | 1674265 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-1821029-25913 | 1821029 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | so_1805604_ff_8597 | so_1805604_ff_8597 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (695/695 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | so_1805604_tt_8597 | so_1805604_tt_8597 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (695/695 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-cbn_q00__cldbcda913-2913832 | cbn_q00 | 3_3_place_gp | 0.9 | overflow best 0.167 last 0.167 rows 37 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-coll_core-3813096 | coll_core | postcts_gate_FF | 9.7 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1102342 | kv3_hg_v1p3__r838481cd7 | 4_1_cts | 1.6 | last meaningful line 0.1 h ago (6893/6893 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v6-102352 | kv3_hgi_v6 | tt_setup_repair | 2.1 | repair_Viol best 120 last 120 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_hub_Eo-371567 | kv3_hub_Eo | 3_5_place_dp | 3.6 | last meaningful line 0.5 h ago (118/118 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 5_2_route | 14.7 | last meaningful line 0.5 h ago (264/265 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v3-1442734 | sle_fw_v3 | postcts_gate_TT | 8.4 | last meaningful line 0.3 h ago (829/829 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | postcts_gate_FF | 10.4 | last meaningful line 0.0 h ago (701/701 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 4_1_cts | 2.5 | last meaningful line 0.1 h ago (5691/5691 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 5_1_grt | 6.7 | last meaningful line 0.3 h ago (296/1108 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 5_2_route | 8.4 | last meaningful line 0.3 h ago (269/270 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 6.6 | drt_violations best 187976 last 187976 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 4_1_cts | 4.2 | last meaningful line 0.0 h ago (5773/5773 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3325358 | slw_fw_v1 | 4_1_cts | 4.2 | last meaningful line 0.3 h ago (5464/5464 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 14.7 | last meaningful line 0.5 h ago (281/282 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v3-1399930 | slw_fw_v3 | postcts_gate_FF | 8.5 | last meaningful line -0.0 h ago (67846/67846 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | pregrt_ff_hold | 5.2 | last meaningful line -0.0 h ago (34/34 lines) | YOUNG: evidence 0.1 h < 2.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 5_1_grt | 6.5 | last meaningful line 0.1 h ago (1018/1036 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | postcts_gate_FF | 10.4 | last meaningful line 0.2 h ago (545/545 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | 5_2_route | 14.6 | drt_violations best 156960 last 156960 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 5_2_route | 10.4 | last meaningful line 0.5 h ago (268/269 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1e5219ea-4177722 | slw_su_l0 | 5_2_route | 6.5 | drt_violations best 133698 last 133698 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-3090069 | slw_su_l0 | 5_2_route | 4.3 | last meaningful line 0.1 h ago (134/134 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 8.5 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 8.5 |  | NO-DATA: no log found |  |
| intel1 | otc-4000256-29997 | 4000256 | eq11 | 0.5 | last meaningful line -0.0 h ago (537477/537477 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | otc-4001240-3461 | 4001240 | eq11 | 0.5 | last meaningful line 0.0 h ago (537281/537281 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i2-2930338 | eco_20261123_191853_2879776-i2 | 5_2_route | 2.6 | last meaningful line 0.1 h ago (134/134 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-98785 | coll_ftm | 5_1_grt | 0.5 | repair_Remaining best 29798 last 29798 rows 20 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-hd_ctl-2153206 | hd_ctl | 5_2_route | 3.3 | drt_violations best 55663 last 55663 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-824722 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (216/217 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8422a4b86-973415 | kv3_pc_v1 | 3_5_place_dp | 1.5 | last meaningful line 0.1 h ago (32/32 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 10.1 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 5_2_route | 10.3 | last meaningful line 0.5 h ago (276/277 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-2390236 | slw_st_b_v1 | 5_1_grt | 3.1 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | so_1605288_ff_97095 | so_1605288_ff_97095 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_1605288_tt_97095 | so_1605288_tt_97095 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | pregrt_ff_hold | 7.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 22.7 | drt_violations best 15279 last 15279 rows 16 | before-window best 18158, window best 15279 | PROGRESS: drt_violations improved 15.9 % in window |  |
| epyc11 | prd-eco_20261124_154417_1016084-i2t-1425156 | eco_20261124_154417_1016084-i2t | 5_1_grt | 0.6 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 15.0 | drt_violations best 16679 last 16679 rows 9 | before-window best 521993, window best 16679 | PROGRESS: drt_violations improved 96.8 % in window |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1101031 | slw_hc3 | 5_2_route | 8.3 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-1559108 | cbn_q01 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 42.1 | drt_violations best 10129 last 48097 rows 18 | before-window best 11554, window best 10129 | PROGRESS: drt_violations improved 12.3 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 35.4 | drt_violations best 7726 last 31531 rows 18 | before-window best 11933, window best 7726 | PROGRESS: drt_violations improved 35.3 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 20.1 | drt_violations best 3524 last 3524 rows 13 | before-window best 109083, window best 3524 | PROGRESS: drt_violations improved 96.8 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 16.3 | drt_violations best 84872 last 84872 rows 3 | before-window best 504597, window best 84872 | PROGRESS: drt_violations improved 83.2 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 14.9 | drt_violations best 510309 last 510309 rows 1 | before-window best 510309, window best 510309 | PROGRESS: drt_violations: active iteration at 280794 < best completed total 510309 (in-ite |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 14.7 | drt_violations best 457993 last 457993 rows 1 | before-window best 457993, window best 457993 | PROGRESS: drt_violations: active iteration at 250195 < best completed total 457993 (in-ite |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 20.3 | drt_violations best 66691 last 66691 rows 8 | before-window best 74091, window best 66691 | PROGRESS: drt_violations improved 10.0 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 16.4 | drt_violations best 55677 last 55677 rows 5 | before-window best 400194, window best 55677 | PROGRESS: drt_violations improved 86.1 % in window |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | 5_2_route | 14.8 | drt_violations best 16327 last 16327 rows 2 | before-window best 122101, window best 16327 | PROGRESS: drt_violations improved 86.6 % in window |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 11.5 | drt_violations best 379431 last 379431 rows 1 | before-window best 379431, window best 379431 | PROGRESS: drt_violations: active iteration at 225522 < best completed total 379431 (in-ite |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | 5_2_route | 11.6 | drt_violations best 72 last 72 rows 42 | before-window best 149425, window best 72 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 5_2_route | 11.6 | drt_violations best 72 last 72 rows 54 | before-window best 146485, window best 72 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 11.6 | drt_violations best 20520 last 20520 rows 10 | before-window best 89614, window best 20520 | PROGRESS: drt_violations improved 77.1 % in window |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | 5_2_route | 12.8 | drt_violations best 20184 last 20184 rows 3 | before-window best 234054, window best 20184 | PROGRESS: drt_violations improved 91.4 % in window |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | otc-2434312-2110 | 2434312 | flow | 2.8 | repair_Violations best 0 last 0 rows 19 | PROGRESS: repair_Violations reached 0 |  |
| intel2 | dpkit-slice_station__t12-877532 | slice_station__t12 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
