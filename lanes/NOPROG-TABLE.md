# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 18:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 6, 'UNSIGNABLE': 2, 'GRT-LABEL': 4, 'YOUNG': 181, 'NO-DATA': 15, 'PROGRESS': 20}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 9.3 | last meaningful line 8.0 h ago (48/135 lines) | NO-PROGRESS: no new non-iteration log line for 8.0 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 5_1_grt | 9.6 | grt rounds 2 overflow 5:42234 -> 10:42876 | UNSIGNABLE: GRT overflow flat: overflow 42234 at iteration 5 -> 42876 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-660000 | sle_hc0 | pregrt_ff_hold | 6.7 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1583204 | sle_st_b_v1 | pregrt_ff_hold | 6.0 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 12.6 | last meaningful line 9.1 h ago (48/192 lines) | NO-PROGRESS: no new non-iteration log line for 9.1 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 4.8 | repair_TNS best 827598 last 827598 rows 1 | before-window best 827598, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 5_1_grt | 11.6 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2360221 | slw_hc2 | pregrt_ff_hold | 6.7 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-kv3_pv_v2n-1048434 | kv3_pv_v2n | 5_1_grt | 9.4 | grt rounds 2 overflow 5:64147 -> 10:49031 | GRT-LABEL: DESIGN-FAIL: overflow 49031 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v6-908877 | kv3_pv_v6 | 5_1_grt | 9.5 | grt rounds 2 overflow 5:56449 -> 10:44954 | GRT-LABEL: DESIGN-FAIL: overflow 44954 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | 5_1_grt | 7.0 | grt rounds 1 overflow 5:41695 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 5_1_grt | 11.1 | grt rounds 2 overflow 5:83232 -> 10:63283 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-glue-1294589 | glue | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (5757/5757 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | 5_2_route | 6.2 | drt_violations best 3411 last 3411 rows 11 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r889141819-1619104 | kv3_hg_v1__r889141819 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (7287/7288 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r88f4bfb40-1671162 | kv3_hg_v1__r88f4bfb40 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (7289/7290 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r8dffc461a-1676050 | kv3_hg_v1__r8dffc461a | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (7341/7342 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p2-1802854 | kv3_hg_v1p2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (6641/6641 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p3__r81da466fe-1840159 | kv3_hg_v1p3__r81da466fe | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-373156 | kv3_hgi | 5_1_grt | 1.2 | last meaningful line 0.5 h ago (296/298 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-477047 | kv3_hgi | 5_1_grt | 1.1 | last meaningful line 0.3 h ago (287/1293 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-477535 | kv3_hgi_v2 | 5_1_grt | 1.1 | last meaningful line 0.2 h ago (288/1293 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-560078 | kv3_hgi_v2 | 5_1_grt | 1.1 | last meaningful line 0.2 h ago (288/1292 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | 4_1_cts | 0.8 | last meaningful line 0.8 h ago (46/46 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-1076148 | kv3_pc | 3_3_place_gp | 0.8 | overflow best 0.7721 last 0.7823 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r8b421e514-1086873 | kv3_pc | 3_3_place_gp | 0.8 | overflow best 0.7332 last 0.7332 rows 21 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r85c02c25c-1098684 | kv3_pc | 3_3_place_gp | 0.8 | overflow best 0.7707 last 0.7784 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r882954158-1102222 | kv3_pc | 3_3_place_gp | 0.8 | overflow best 0.7699 last 0.7801 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | 5_1_grt | 9.5 | last meaningful line 1.5 h ago (270/1279 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | pregrt_ff_hold | 4.7 | repair_TNS best 35673.3 last 35673.3 rows 1 | YOUNG: evidence 2.1 h < 2.5 h |  |
| epyc10 | dpkit-native59-3512619 | native59 | 3_5_place_dp | 1.9 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | postcts_gate_TT | 8.5 | last meaningful line 0.1 h ago (1863/1863 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | 5_1_grt | 5.3 | last meaningful line 0.1 h ago (932/943 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | 5_1_grt | 5.7 | last meaningful line 0.1 h ago (1223/1277 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | postcts_gate_TT | 6.3 | last meaningful line -0.0 h ago (11080/11080 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2793057 | sle_stm_v1 | 5_2_route | 8.0 | drt_violations best 145941 last 145941 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_1_grt | 7.4 | last meaningful line 0.1 h ago (2583/2600 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 5_1_grt | 7.5 | last meaningful line 0.2 h ago (1963/1976 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | 5_1_grt | 5.2 | last meaningful line 0.2 h ago (1192/1209 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3681869 | slw_st_b_v2 | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (4815/4815 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | 5_1_grt | 4.2 | repair_Remaining best 280039 last 280039 rows 203 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | dpkit-slw_stm_v1__cle34a73c3-4063338 | slw_stm_v1 | 5_2_route | 7.2 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | otc-901577-23707 | 901577 | signoff | 3.5 | last meaningful line 3.5 h ago (3/3 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc10 | qc-colls-lec-h3 | qc-colls-lec-h3 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc10 | qc-hc3-lec-r8-nearest | qc-hc3-lec-r8-nearest | - | 3.2 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R8_hc3_pvcca | relec-r2-R8_hc3_pvcca | - | 7.2 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | postcts_gate_FF | 9.0 | last meaningful line 0.2 h ago (1927/1927 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 5_1_grt | 4.6 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | tt_setup_repair_grt | 5.6 | last meaningful line 0.0 h ago (623/623 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | 5_2_route | 9.0 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 4_1_cts | 4.3 | last meaningful line 0.1 h ago (6059/6059 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | 5_2_route | 8.8 | last meaningful line 0.2 h ago (268/268 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | 5_2_route | 9.0 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc2__cl6bcaba89-3858415 | slw_hc2 | 6_report | 9.3 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2533872 | slw_hc3 | pregrt_ff_hold | 2.6 | repair_TNS best 183193 last 183193 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4075873 | slw_st_b_v1 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | 5_2_route | 8.8 | last meaningful line 0.1 h ago (275/276 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-320042 | slw_st_b_v2 | 5_2_route | 8.8 | drt_violations best 128395 last 128395 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl92142dac-136142 | slw_su_c | 3_3_place_gp | 0.5 | overflow best 0.5769 last 0.5769 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 8.0 |  | NO-DATA: no log found |  |
| epyc11 | otc-3389445-25127 | 3389445 | signoff | 1.6 | last meaningful line 1.5 h ago (3/3 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i1-3176761 | eco_20261124_190641_1260390-i1 | 5_2_route | 1.9 | last meaningful line 0.2 h ago (134/134 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i1-3660942 | eco_20261124_200101_1087713-i1 | 5_1_grt | 1.3 | last meaningful line 0.9 h ago (246/1511 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_204246_1187010-i1-249436 | eco_20261124_204246_1187010-i1 | 5_1_grt | 0.4 | last meaningful line 0.1 h ago (143/143 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | so_535127_ff_93189 | so_535127_ff_93189 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (1034/1034 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | so_535127_tt_93189 | so_535127_tt_93189 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (1034/1034 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-hd_host_w-2612050 | hd_host_w | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3730/3730 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v8-2737550 | kv3_hgi_v8 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (73/73 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-1457043 | kv3_hroot | 5_2_route | 3.6 | drt_violations best 40861 last 40861 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-491987 | sle_hc0 | postcts_gate_FF | 7.4 | last meaningful line 0.1 h ago (366/366 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-1254949 | sle_hc2 | 5_2_route | 7.0 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3414126 | sle_hc2 | 5_2_route | 8.4 | drt_violations best 97304 last 97304 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__clcc5e3e61-3434617 | sle_hc2 | 5_2_route | 8.4 | drt_violations best 104718 last 104718 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3668964 | sle_st_b_v2 | 4_1_cts | 2.3 | last meaningful line 0.0 h ago (5725/5725 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-4153401 | sle_stm_v2 | 5_2_route | 7.9 | drt_violations best 159333 last 159333 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-4191516 | slw_fw_v2 | postcts_gate_TT | 7.8 | last meaningful line 0.1 h ago (839/839 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1101031 | slw_hc3 | 5_2_route | 7.0 | drt_violations best 88807 last 88807 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3626034 | slw_hc3 | generate_abstract | 8.2 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3657462 | slw_stm_v2 | 5_2_route | 8.2 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | kqc-sta_region_nb0_h15_n9_s11_bt2_synth0-2010758 | sta_region_nb0_h15_n9_s11_bt2_synth0 | 1_2_yosys | 0.5 | last meaningful line -0.0 h ago (11706/11706 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | kqc-sta_region_nb0_h17_n7_s8_bt2_synth0-2004899 | sta_region_nb0_h17_n7_s8_bt2_synth0 | 1_2_yosys | 0.5 | last meaningful line -0.0 h ago (9026/9026 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | kqc-sta_region_nb0_h18_n7_s8_bt2_synth0-2007798 | sta_region_nb0_h18_n7_s8_bt2_synth0 | 1_2_yosys | 0.5 | last meaningful line 0.0 h ago (1092/1092 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_165709_1862160-i1t-580795 | eco_20261124_165709_1862160-i1t | 5_2_route | 1.5 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 7.2 |  | NO-DATA: no log found |  |
| epyc2 | so_2534655_ff_50101 | so_2534655_ff_50101 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | so_2534655_tt_50101 | so_2534655_tt_50101 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | so_2631454_ff_15134 | so_2631454_ff_15134 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_2631454_tt_15134 | so_2631454_tt_15134 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-1559108 | cbn_q01 | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (7732/7732 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 4_1_cts | 1.9 | last meaningful line 0.1 h ago (10765/10765 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-2222980 | sle_fw_v2 | 5_1_grt | 9.1 | last meaningful line 0.3 h ago (2215/2232 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 9.1 | last meaningful line 0.5 h ago (283/284 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | 5_2_route | 9.3 | last meaningful line 0.1 h ago (135/135 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | postcts_gate_FF | 9.2 | last meaningful line 0.1 h ago (824/824 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | postcts_gate_FF | 9.3 | last meaningful line 0.0 h ago (839/839 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-2253577 | slw_hc2 | 5_2_route | 9.1 | last meaningful line 0.3 h ago (273/274 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-1524868 | slw_sc_v1 | tt_setup_measure | 1.7 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 13.5 | drt_violations best 457993 last 457993 rows 1 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-2092169 | slw_sc_v1 | 4_1_cts | 1.4 | last meaningful line 0.2 h ago (5579/5579 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | 5_2_route | 9.2 | last meaningful line 0.3 h ago (265/266 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | 5_2_route | 13.5 | drt_violations best 122101 last 122101 rows 1 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | 5_2_route | 9.1 | last meaningful line 0.5 h ago (276/277 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | otc-82892-20311 | 82892 | signoff | 0.2 | last meaningful line 0.2 h ago (3/3 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i3-2609460 | eco_20261123_171023_3055226-i3 | 5_1_grt | 1.1 | last meaningful line 0.3 h ago (236/1286 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_145005_2036075-i2-1496134 | eco_20261124_145005_2036075-i2 | 5_2_route | 1.8 | last meaningful line 0.1 h ago (266/267 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i2t-864737 | eco_20261124_175441_992552-i2t | 5_2_route | 2.1 | drt_violations best 39965 last 39965 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i1-2124005 | eco_20261124_192157_3493836-i1 | 5_2_route | 1.4 | last meaningful line 0.1 h ago (257/257 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i1t-231566 | eco_20261124_235631_1843084-i1t | 5_2_route | 2.5 | drt_violations best 201478 last 201478 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | postcts_gate_FF | 10.4 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 5_2_route | 10.4 | last meaningful line 0.3 h ago (280/281 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 5_2_route | 10.4 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | postcts_gate_FF | 10.4 | last meaningful line 0.2 h ago (828/828 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | 5_2_route | 10.4 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | 5_2_route | 10.4 | last meaningful line 0.3 h ago (268/269 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 10.3 | last meaningful line 0.5 h ago (275/276 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | postcts_gate_FF | 10.4 | last meaningful line 0.3 h ago (1168/1168 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 5_2_route | 10.4 | last meaningful line 0.1 h ago (266/266 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | 5_2_route | 10.4 | last meaningful line 0.2 h ago (268/268 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | 5_2_route | 10.4 | drt_violations best 160491 last 160491 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | postcts_gate_TT | 10.4 | last meaningful line -0.0 h ago (43650/43650 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 5_2_route | 10.4 | last meaningful line 0.1 h ago (129/129 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | postcts_gate_FF | 10.4 | last meaningful line 0.0 h ago (825/825 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 5_2_route | 10.4 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | 5_2_route | 10.4 | last meaningful line 0.3 h ago (281/282 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3909116 | slw_hc3 | 6_report | 10.4 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 10.3 | last meaningful line 0.5 h ago (279/280 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 10.3 | drt_violations best 379431 last 379431 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 5_2_route | 10.4 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | otc-120424-12773 | 120424 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-2900322-1356 | 2900322 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_012701_4018610-i1-2166955 | eco_20261125_012701_4018610-i1 | 5_2_route | 1.0 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 7.3 |  | NO-DATA: no log found |  |
| epyc8 | so_3550330_ff_69082 | so_3550330_ff_69082 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc8 | so_3550330_tt_69082 | so_3550330_tt_69082 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc8 | so_4188598_ff_56549 | so_4188598_ff_56549 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (30/30 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | so_4188598_tt_56549 | so_4188598_tt_56549 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (30/30 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3738475 | col_h10_r0_p1__t1 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3008582 | col_h10_r0_p4__t1 | 3_3_place_gp | 0.4 | overflow best 0.4661 last 0.4661 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2935394 | col_h9_r0_p1__t1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.3739 last 0.3739 rows 33 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-519508 | col_h9_r0_p2__t1 | synth_odb_v | 0.1 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pvd86cb19a-2144122 | col_h9_r0_p2__t1 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (97/97 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-3752229 | col_h9_r0_p2__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8273 last 0.8348 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-3067702 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.4 | last meaningful line -0.0 h ago (275/275 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-1649671 | col_h9_r0_p2__t1 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3010673 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (235/235 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pvef55eb84-1795459 | col_h9_r0_p2__t1 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2843926 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.8409 last 0.8409 rows 20 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-3480830 | col_h9_r0_p4__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.6617 last 0.6617 rows 24 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-1612646 | col_h9_r0_p5__t1 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-4146180 | col_h9_r2__t1 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-3633253 | col_h9_r2__t1 | 3_4_place_resized | 0.3 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 7.1 | drt_violations best 1673 last 1673 rows 11 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t13-1595964 | serdes__t13 | 3_1_place_gp_skip_io | 0.9 | overflow best 0.7976 last 0.7976 rows 28 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-serdes__t4-3729546 | serdes__t4 | synth_odb_v | 0.3 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | pregrt_ff_hold | 6.7 | repair_TNS best 303873 last 303873 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | postcts_gate_TT | 7.3 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-667540 | sle_hc1 | postcts_gate_FF | 7.4 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t25-3667812 | slice_station__t25 | 3_3_place_gp | 0.3 | overflow best 0.456 last 0.456 rows 4 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slice_station__t37-4018856 | slice_station__t37 | 3_3_place_gp | 0.2 | overflow best 0.3816 last 0.3816 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slice_station__t40__clc8fb2c8c-2937252 | slice_station__t40 | 3_3_place_gp | 0.5 | overflow best 0.211 last 0.2236 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slice_station__t49-4075886 | slice_station__t49 | 3_3_place_gp | 0.2 | overflow best 0.3046 last 0.3046 rows 3 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slice_station__t51-3276752 | slice_station__t51 | lec | 0.4 | LEC last write 0.0 h ago | YOUNG: evidence 0.4 h < 6 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_1_grt | 7.4 | last meaningful line 0.3 h ago (2637/2666 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v2__cl8537f156-601723 | slw_fw_v2 | postcts_gate_FF | 7.4 | last meaningful line -0.0 h ago (73585/73585 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | otc-1399673-10074 | 1399673 | gen_lint_yosys | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | otc-1420782-26237 | 1420782 | gen_lint_yosys | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | otc-1560357-22328 | 1560357 | gen_lint_yosys | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | otc-3045448-2377 | 3045448 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-fin-3801930 | fin | 6_report | 0.3 | last meaningful line 0.1 h ago (728/728 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-coll_core-3813096 | coll_core | 5_1_grt | 8.7 | last meaningful line 0.2 h ago (3058/3064 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1102342 | kv3_hg_v1p3__r838481cd7 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (6385/6385 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v6-102352 | kv3_hgi_v6 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (6211/6211 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Eo-371567 | kv3_hub_Eo | 3_4_place_resized | 2.6 | last meaningful line 0.2 h ago (382/382 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_pc_v1__cl4ea58a5c__r877307f5d-453397 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.9 | overflow best 0.8562 last 0.8992 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 5_2_route | 13.7 | last meaningful line 0.3 h ago (133/133 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v3-1442734 | sle_fw_v3 | tt_setup_repair_grt | 7.4 | repair_Remaining best 24349 last 24349 rows 414 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | postcts_gate_TT | 9.4 | last meaningful line 0.1 h ago (778/778 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (5271/5271 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 5_1_grt | 5.7 | last meaningful line 0.1 h ago (146/146 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 5_2_route | 7.4 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 5.6 | last meaningful line 0.3 h ago (269/270 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 4_1_cts | 3.2 | last meaningful line 0.2 h ago (5642/5642 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3325358 | slw_fw_v1 | 4_1_cts | 3.2 | last meaningful line 0.3 h ago (5456/5456 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 13.7 | last meaningful line 0.5 h ago (277/278 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v3-1399930 | slw_fw_v3 | postcts_gate_FF | 7.5 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 4_1_cts | 4.2 | last meaningful line 0.2 h ago (5364/5364 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 5_1_grt | 5.5 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3890746 | slw_sc_v1 | postcts_gate_TT | 5.7 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | postcts_gate_TT | 9.4 | last meaningful line 0.1 h ago (1241/1241 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | pregrt_ff_hold | 3.9 | repair_TNS best 18052.5 last 18052.5 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | 5_2_route | 13.6 | drt_violations best 156960 last 156960 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 5_2_route | 9.4 | last meaningful line 0.3 h ago (262/263 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1e5219ea-4177722 | slw_su_l0 | 5_2_route | 5.5 | last meaningful line 0.3 h ago (269/270 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-3090069 | slw_su_l0 | postcts_gate_FF | 3.3 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 7.5 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 7.5 |  | NO-DATA: no log found |  |
| intel1 | otc-2434312-2110 | 2434312 | flow | 1.8 | last meaningful line 0.0 h ago (3012/3012 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | otc-3192080-15624 | 3192080 | eq10 | 1.5 | last meaningful line 1.2 h ago (517751/517751 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i2-2930338 | eco_20261123_191853_2879776-i2 | 5_1_grt | 1.6 | last meaningful line 0.8 h ago (239/1445 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2240258 | coll_ftm | 5_2_route | 2.0 | drt_violations best 10288 last 10288 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-hd_ctl-2153206 | hd_ctl | 5_2_route | 2.0 | last meaningful line 0.0 h ago (119/119 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p4-531223 | kv3_hg_v1p4 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (62/62 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8422a4b86-973415 | kv3_pc_v1 | 2_1_floorplan | 0.3 | last meaningful line 0.0 h ago (1383/1383 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v12-977044 | kv3_pv_v12 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8177 last 0.8177 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-579857 | slice_station__t12 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (108/108 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | postcts_gate_TT | 8.9 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 5_2_route | 9.1 | last meaningful line 0.3 h ago (268/269 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-2390236 | slw_st_b_v1 | 4_1_cts | 1.9 | last meaningful line 0.0 h ago (5357/5357 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_1_grt | 7.4 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | pregrt_ff_hold | 6.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 21.4 | drt_violations best 15812 last 15812 rows 15 | before-window best 19250, window best 15812 | PROGRESS: drt_violations improved 17.9 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 13.8 | drt_violations best 1743 last 2528 rows 19 | before-window best 1879, window best 1743 | PROGRESS: drt_violations improved 7.2 % in window |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 13.7 | drt_violations best 21818 last 21818 rows 5 | before-window best 521993, window best 21818 | PROGRESS: drt_violations improved 95.8 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 40.8 | drt_violations best 10129 last 48097 rows 18 | before-window best 13426, window best 10129 | PROGRESS: drt_violations improved 24.6 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 34.1 | drt_violations best 7726 last 31531 rows 18 | before-window best 11933, window best 7726 | PROGRESS: drt_violations improved 35.3 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 18.9 | drt_violations best 5099 last 5099 rows 11 | before-window best 109083, window best 5099 | PROGRESS: drt_violations improved 95.3 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 15.0 | drt_violations best 116309 last 116309 rows 2 | before-window best 504597, window best 116309 | PROGRESS: drt_violations improved 77.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 13.7 | drt_violations best 510309 last 510309 rows 1 | before-window best 510309, window best 510309 | PROGRESS: drt_violations: active iteration at 387230 < best completed total 510309 (in-ite |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 19.1 | drt_violations best 66691 last 66691 rows 8 | before-window best 116989, window best 66691 | PROGRESS: drt_violations improved 43.0 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 15.2 | drt_violations best 59441 last 59441 rows 4 | before-window best 400194, window best 59441 | PROGRESS: drt_violations improved 85.1 % in window |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | 5_2_route | 10.4 | drt_violations best 122 last 122 rows 23 | before-window best 149425, window best 122 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 5_2_route | 10.4 | drt_violations best 72 last 72 rows 54 | before-window best 146485, window best 72 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 10.4 | drt_violations best 22483 last 22483 rows 9 | before-window best 274214, window best 22483 | PROGRESS: drt_violations improved 91.8 % in window |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3t-2289287 | eco_20261123_164145_1995767-i3t | 5_2_route | 7.8 | drt_violations best 5 last 5 rows 26 | before-window best 35664, window best 5 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7b8853b5-3023518 | col_h9_r2__t1 | 3_5_place_dp | 0.4 | repair_Violations best 0 last 0 rows 25 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-3029535 | col_h9_r2__t1 | 3_5_place_dp | 0.4 | repair_Violations best 0 last 0 rows 25 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | 5_2_route | 11.8 | drt_violations best 32830 last 32830 rows 2 | before-window best 234054, window best 32830 | PROGRESS: drt_violations improved 86.0 % in window |  |
| intel2 | dpkit-kv3_io_ft-1076451 | kv3_io_ft | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
