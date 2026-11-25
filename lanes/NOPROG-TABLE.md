# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 18:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 7, 'UNSIGNABLE': 2, 'GRT-LABEL': 4, 'NO-DATA': 17, 'YOUNG': 177, 'PROGRESS': 23}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 9.6 | last meaningful line 8.3 h ago (48/135 lines) | NO-PROGRESS: no new non-iteration log line for 8.3 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 5_1_grt | 9.9 | grt rounds 2 overflow 5:42234 -> 10:42876 | UNSIGNABLE: GRT overflow flat: overflow 42234 at iteration 5 -> 42876 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | pregrt_ff_hold | 4.9 | repair_TNS best 35673.3 last 35673.3 rows 1 | before-window best 35673.3, window best 35673.3 | NO-PROGRESS: repair_TNS best 35673.3 vs 35673.3 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-SENDER-SKEW decides; |
| epyc10 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-660000 | sle_hc0 | pregrt_ff_hold | 6.9 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1583204 | sle_st_b_v1 | pregrt_ff_hold | 6.2 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | CANCELLED |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 12.9 | last meaningful line 9.3 h ago (48/192 lines) | NO-PROGRESS: no new non-iteration log line for 9.3 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 5.1 | repair_TNS best 827598 last 827598 rows 1 | before-window best 827598, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 5_1_grt | 11.8 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2360221 | slw_hc2 | pregrt_ff_hold | 7.0 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-kv3_pv_v2n-1048434 | kv3_pv_v2n | 5_1_grt | 9.6 | grt rounds 2 overflow 5:64147 -> 10:49031 | GRT-LABEL: DESIGN-FAIL: overflow 49031 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v6-908877 | kv3_pv_v6 | 5_1_grt | 9.7 | grt rounds 2 overflow 5:56449 -> 10:44954 | GRT-LABEL: DESIGN-FAIL: overflow 44954 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | 5_1_grt | 7.2 | grt rounds 1 overflow 5:41695 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 5_1_grt | 11.4 | grt rounds 2 overflow 5:83232 -> 10:63283 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-native59-grt-3116749 | native59-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-glue-1294589 | glue | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (5796/5796 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | 5_2_route | 6.4 | drt_violations best 2879 last 2879 rows 12 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r889141819-1619104 | kv3_hg_v1__r889141819 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (7371/7371 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r88f4bfb40-1671162 | kv3_hg_v1__r88f4bfb40 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (7425/7425 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r8dffc461a-1676050 | kv3_hg_v1__r8dffc461a | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (7477/7477 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p2-1802854 | kv3_hg_v1p2 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (6980/6980 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p3__r81da466fe-1840159 | kv3_hg_v1p3__r81da466fe | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (6758/6759 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-373156 | kv3_hgi | 5_1_grt | 1.5 | last meaningful line 0.8 h ago (296/1300 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-477047 | kv3_hgi | 5_1_grt | 1.4 | last meaningful line 0.5 h ago (287/1296 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-477535 | kv3_hgi_v2 | 5_1_grt | 1.4 | last meaningful line 0.5 h ago (288/1295 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-560078 | kv3_hgi_v2 | 5_1_grt | 1.3 | last meaningful line 0.5 h ago (288/1295 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (10625/10625 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-1076148 | kv3_pc | 3_3_place_gp | 1.1 | overflow best 0.2033 last 0.2033 rows 40 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r8b421e514-1086873 | kv3_pc | 3_3_place_gp | 1.1 | overflow best 0.0987 last 0.0987 rows 46 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r85c02c25c-1098684 | kv3_pc | 3_3_place_gp | 1.1 | overflow best 0.2045 last 0.2045 rows 40 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r882954158-1102222 | kv3_pc | 3_3_place_gp | 1.1 | overflow best 0.203 last 0.203 rows 40 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | 5_1_grt | 9.7 | last meaningful line 1.8 h ago (270/1280 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | postcts_gate_TT | 8.7 | last meaningful line -0.0 h ago (33810/33810 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | 5_1_grt | 5.6 | last meaningful line 0.1 h ago (992/1009 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | tt_setup_measure_grt | 6.0 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | postcts_gate_FF | 6.5 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2793057 | sle_stm_v1 | 5_2_route | 8.3 | drt_violations best 145941 last 145941 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | tt_setup_repair_grt | 7.7 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_1_grt | 7.7 | last meaningful line 0.1 h ago (2033/2039 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 5_1_grt | 7.7 | last meaningful line 0.4 h ago (1963/1976 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | tt_setup_repair_grt | 5.5 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3681869 | slw_st_b_v2 | 4_1_cts | 2.0 | last meaningful line 0.0 h ago (4867/4867 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | 5_1_grt | 4.4 | last meaningful line 0.4 h ago (281/1025 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_stm_v1__cle34a73c3-4063338 | slw_stm_v1 | 5_2_route | 7.5 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | otc-901577-23707 | 901577 | signoff | 3.8 | last meaningful line 3.8 h ago (3/3 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc10 | qc-colls-lec-h3 | qc-colls-lec-h3 | - | 1.9 |  | NO-DATA: no log found |  |
| epyc10 | qc-hc3-lec-r8-nearest | qc-hc3-lec-r8-nearest | - | 3.5 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R8_hc3_pvcca | relec-r2-R8_hc3_pvcca | - | 7.5 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | postcts_gate_FF | 9.2 | last meaningful line -0.0 h ago (102344/102344 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 5_1_grt | 4.8 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | postcts_gate_TT | 5.8 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | 5_2_route | 9.3 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | pregrt_ff_hold | 4.5 | repair_TNS best 23871.1 last 23871.1 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | 5_2_route | 9.1 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | 5_2_route | 9.2 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc2__cl6bcaba89-3858415 | slw_hc2 | generate_abstract | 9.6 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2533872 | slw_hc3 | 5_1_grt | 2.9 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4075873 | slw_st_b_v1 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | 5_2_route | 9.0 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-320042 | slw_st_b_v2 | 5_2_route | 9.0 | drt_violations best 128395 last 128395 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl92142dac-136142 | slw_su_c | 3_3_place_gp | 0.8 | overflow best 0.2504 last 0.2674 rows 32 | YOUNG: stage 0.5 h < 1 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 8.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-3389445-25127 | 3389445 | signoff | 1.8 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i1-3176761 | eco_20261124_190641_1260390-i1 | 5_2_route | 2.1 | last meaningful line 0.2 h ago (267/267 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i1-3660942 | eco_20261124_200101_1087713-i1 | 5_2_route | 1.5 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | so_535127_ff_93189 | so_535127_ff_93189 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (1034/1034 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | so_535127_tt_93189 | so_535127_tt_93189 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (1034/1034 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-hd_host_w-2612050 | hd_host_w | pregrt_ff_hold | 0.4 | repair_TNS best 42745.5 last 42745.5 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-kv3_hgi_v8-2737550 | kv3_hgi_v8 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (5440/5440 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-1457043 | kv3_hroot | 5_2_route | 3.9 | drt_violations best 5166 last 5166 rows 3 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-491987 | sle_hc0 | postcts_gate_FF | 7.7 | last meaningful line 0.0 h ago (759/759 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-1254949 | sle_hc2 | 5_2_route | 7.2 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3414126 | sle_hc2 | 5_2_route | 8.6 | drt_violations best 97304 last 97304 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__clcc5e3e61-3434617 | sle_hc2 | 5_2_route | 8.6 | drt_violations best 104718 last 104718 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3668964 | sle_st_b_v2 | 4_1_cts | 2.5 | last meaningful line 0.1 h ago (5845/5845 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-4153401 | sle_stm_v2 | 5_2_route | 8.1 | drt_violations best 159333 last 159333 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1101031 | slw_hc3 | 5_2_route | 7.3 | drt_violations best 88807 last 88807 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3657462 | slw_stm_v2 | 5_2_route | 8.4 | drt_violations best 124000 last 124000 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | kqc-sta_region_nb0_h15_n9_s11_bt2_synth0-2010758 | sta_region_nb0_h15_n9_s11_bt2_synth0 | 5_1_grt | 0.8 | last meaningful line 0.0 h ago (116/116 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | kqc-sta_region_nb0_h18_n7_s8_bt2_synth0-2007798-lec | sta_region_nb0_h18_n7_s8_bt2_synth0 | lec | 0.1 | LEC last write 0.0 h ago | YOUNG: evidence 0.1 h < 6 h |  |
| epyc2 | prd-eco_20261124_165709_1862160-i1t-580795 | eco_20261124_165709_1862160-i1t | 5_2_route | 1.8 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 7.4 |  | NO-DATA: no log found |  |
| epyc2 | so_3009822_ff_91101 | so_3009822_ff_91101 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | so_3009822_tt_91101 | so_3009822_tt_91101 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-1559108 | cbn_q01 | tt_setup_repair | 2.0 | repair_Viol best 563 last 563 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 4_1_cts | 2.1 | last meaningful line 0.3 h ago (10765/10765 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-2222980 | sle_fw_v2 | tt_setup_repair_grt | 9.4 | repair_Violations best 14 last 103 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 9.3 | drt_violations best 412199 last 412199 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | 5_2_route | 9.6 | last meaningful line 0.2 h ago (136/136 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | postcts_gate_FF | 9.4 | last meaningful line 0.2 h ago (830/830 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | postcts_gate_FF | 9.5 | last meaningful line 0.1 h ago (845/845 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-2253577 | slw_hc2 | 5_2_route | 9.4 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 13.7 | drt_violations best 457993 last 457993 rows 1 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-2092169 | slw_sc_v1 | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (5588/5588 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | 5_2_route | 9.5 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | 5_2_route | 13.8 | drt_violations best 122101 last 122101 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | 5_2_route | 9.4 | drt_violations best 121792 last 121792 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | otc-82892-20311 | 82892 | signoff | 0.4 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i3-2609460 | eco_20261123_171023_3055226-i3 | 5_1_grt | 1.4 | last meaningful line 0.6 h ago (236/1306 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_145005_2036075-i2-1496134 | eco_20261124_145005_2036075-i2 | 5_2_route | 2.0 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i2t-864737 | eco_20261124_175441_992552-i2t | 5_2_route | 2.4 | drt_violations best 90 last 90 rows 5 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i1-2124005 | eco_20261124_192157_3493836-i1 | 5_2_route | 1.7 | last meaningful line 0.2 h ago (258/259 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i1t-231566 | eco_20261124_235631_1843084-i1t | 5_2_route | 2.8 | drt_violations best 7296 last 7296 rows 2 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | postcts_gate_TT | 10.6 | last meaningful line 0.0 h ago (888/888 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 5_2_route | 10.6 | last meaningful line 0.5 h ago (280/281 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 5_2_route | 10.6 | last meaningful line 0.2 h ago (129/129 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | postcts_gate_FF | 10.6 | last meaningful line -0.0 h ago (71069/71069 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | 5_2_route | 10.7 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | 5_2_route | 10.7 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 10.6 | last meaningful line 0.7 h ago (275/276 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | postcts_gate_FF | 10.6 | last meaningful line -0.0 h ago (91427/91427 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 5_2_route | 10.6 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | 5_2_route | 10.6 | last meaningful line 0.1 h ago (271/272 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | 5_2_route | 10.6 | drt_violations best 160491 last 160491 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | postcts_gate_FF | 10.6 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 5_2_route | 10.6 | last meaningful line 0.2 h ago (130/130 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | postcts_gate_FF | 10.6 | last meaningful line -0.0 h ago (3839/3839 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 5_2_route | 10.6 | last meaningful line 0.1 h ago (136/136 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | 5_2_route | 10.7 | drt_violations best 98742 last 98742 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 10.6 | last meaningful line 0.7 h ago (279/280 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 10.5 | drt_violations best 379431 last 379431 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 5_2_route | 10.6 | last meaningful line 0.2 h ago (129/129 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | otc-120424-12773 | 120424 | signoff | 0.4 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | otc-2900322-1356 | 2900322 | - | 2.7 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_012701_4018610-i1-2166955 | eco_20261125_012701_4018610-i1 | 5_2_route | 1.3 | last meaningful line 0.1 h ago (252/252 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 7.5 |  | NO-DATA: no log found |  |
| epyc8 | so_1059905_ff_44154 | so_1059905_ff_44154 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc8 | so_1059905_tt_44154 | so_1059905_tt_44154 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc8 | so_3550330_ff_69082 | so_3550330_ff_69082 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc8 | so_3550330_tt_69082 | so_3550330_tt_69082 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc9 | ap-ageom-kw-col-h9-r0-p2--t1--cl0045af7b--pv6882e5ea-grt-1499386 | col-h9-r0-p2--t1--cl0045af7b--pv6882e5ea-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-col-h9-r0-p2--t1--cl0045af7b--pva2793873-grt-1237989 | col-h9-r0-p2--t1--cl0045af7b--pva2793873-grt | lec | 0.2 | LEC last write 0.0 h ago | YOUNG: evidence 0.2 h < 6 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3738475 | col_h10_r0_p1__t1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.7963 last 0.7963 rows 25 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2935394 | col_h9_r0_p1__t1 | 3_3_place_gp | 0.7 | overflow best 0.3437 last 0.3437 rows 32 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-519508 | col_h9_r0_p2__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8149 last 0.8473 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-1567415 | col_h9_r0_p2__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 572 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-3752229 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.5 | overflow best 0.4411 last 0.4411 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-3067702 | col_h9_r0_p2__t1 | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3010673 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.7 | overflow best 0.1989 last 0.1989 rows 36 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pvcb7f0079-1236189 | col_h9_r0_p3__t1 | 2_1_floorplan | 0.2 | repair_Viol best 3023 last 3023 rows 647 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2843926 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.7 | overflow best 0.5166 last 0.5166 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvcd8810ba-1306563 | col_h9_r0_p3__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 983 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-3480830 | col_h9_r0_p4__t1 | 3_3_place_gp | 0.6 | overflow best 0.2331 last 0.2331 rows 36 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-1408553 | col_h9_r0_p4__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 1124 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-4146180 | col_h9_r2__t1 | 3_5_place_dp | 0.5 | repair_Violations best 65 last 109 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-1309837 | col_h9_r2__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (95/95 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1240410 | col_h9_r2__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (208/208 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvb3f647ea-1648920 | col_h9_r2__t1 | 2_1_floorplan | 0.1 | repair_Viol best 2770 last 2770 rows 839 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve0486b40-1406801 | col_h9_r2__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (207/207 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 7.3 | drt_violations best 1673 last 1673 rows 11 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t25__cl55642d17-1415816 | ot_s81sl_leaf__t25 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.9933 last 0.9933 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t27-1229712 | ot_s81sl_leaf__t27 | 3_3_place_gp | 0.2 | overflow best 0.5711 last 0.5711 rows 5 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-serdes__t13-1595964 | serdes__t13 | 3_3_place_gp | 1.1 | last meaningful line 0.0 h ago (79/79 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t4-3729546 | serdes__t4 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | postcts_gate_TT | 7.5 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-667540 | sle_hc1 | postcts_gate_FF | 7.6 | last meaningful line 0.1 h ago (381/381 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t25-3667812 | slice_station__t25 | 3_3_place_gp | 0.6 | overflow best 0.2856 last 0.2856 rows 37 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-slice_station__t29__clc7772371-1419703 | slice_station__t29 | 3_3_place_gp | 0.1 | overflow best 0.3652 last 0.3652 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-slice_station__t30__clcedefe91-1240625 | slice_station__t30 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (118/118 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-4018856 | slice_station__t37 | 3_3_place_gp | 0.5 | overflow best 0.3162 last 0.3204 rows 36 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-slice_station__t49-4075886 | slice_station__t49 | 3_4_place_resized | 0.5 | last meaningful line -0.0 h ago (12/12 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-3276752 | slice_station__t51 | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (233/233 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | tt_setup_measure_grt | 7.7 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | eco-abs-1458375 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.1 h ago (689/689 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-1399673-10074 | 1399673 | gen_lint_yosys | 1.2 | last meaningful line 1.2 h ago (1/1 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | otc-1420782-26237 | 1420782 | gen_lint_yosys | 1.2 | last meaningful line 1.2 h ago (1/1 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | otc-1560357-22328 | 1560357 | gen_lint_yosys | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | otc-3045448-2377 | 3045448 | gen_lint_yosys | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-cbn_q00__cldbcda913-2913832 | cbn_q00 | 2_1_floorplan | 0.2 | repair_Viol best 6754 last 6754 rows 245 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-coll_core-3813096 | coll_core | tt_setup_repair_grt | 8.9 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1102342 | kv3_hg_v1p3__r838481cd7 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (6627/6628 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v6-102352 | kv3_hgi_v6 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (6261/6261 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Eo-371567 | kv3_hub_Eo | 3_4_place_resized | 2.9 | last meaningful line 0.3 h ago (382/382 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_pc_v1__cl4ea58a5c__r877307f5d-453397 | kv3_pc_v1 | 3_3_place_gp | 1.2 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 5_2_route | 14.0 | last meaningful line 0.2 h ago (134/134 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v3-1442734 | sle_fw_v3 | postcts_gate_TT | 7.7 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | postcts_gate_TT | 9.6 | last meaningful line 0.3 h ago (778/778 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 4_1_cts | 1.7 | last meaningful line 0.0 h ago (5562/5563 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 5_1_grt | 6.0 | last meaningful line 0.2 h ago (147/147 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 5_2_route | 7.7 | last meaningful line 0.2 h ago (264/264 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 5.9 | drt_violations best 187976 last 187976 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 4_1_cts | 3.4 | last meaningful line 0.1 h ago (5645/5645 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3325358 | slw_fw_v1 | 4_1_cts | 3.4 | last meaningful line 0.5 h ago (5457/5457 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 13.9 | last meaningful line 0.7 h ago (277/278 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v3-1399930 | slw_fw_v3 | postcts_gate_FF | 7.7 | last meaningful line 0.2 h ago (896/896 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 4_1_cts | 4.5 | last meaningful line 0.1 h ago (5368/5368 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 5_1_grt | 5.7 | last meaningful line 0.2 h ago (138/138 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3890746 | slw_sc_v1 | postcts_gate_FF | 6.0 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | postcts_gate_TT | 9.6 | last meaningful line 0.2 h ago (1247/1247 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | 5_2_route | 13.9 | drt_violations best 156960 last 156960 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 5_2_route | 9.6 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1e5219ea-4177722 | slw_su_l0 | 5_2_route | 5.8 | drt_violations best 133698 last 133698 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-3090069 | slw_su_l0 | postcts_gate_TT | 3.5 | last meaningful line 0.0 h ago (800/800 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 7.8 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 7.8 |  | NO-DATA: no log found |  |
| intel1 | otc-2434312-2110 | 2434312 | flow | 2.0 | repair_Remaining best 170307 last 170307 rows 214 | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | otc-3192080-15624 | 3192080 | eq10 | 1.8 | last meaningful line 1.5 h ago (517751/517751 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i2-2930338 | eco_20261123_191853_2879776-i2 | 5_1_grt | 1.9 | last meaningful line 1.0 h ago (239/1446 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2240258 | coll_ftm | 5_2_route | 2.2 | drt_violations best 387 last 387 rows 2 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-hd_ctl-2153206 | hd_ctl | 5_2_route | 2.3 | last meaningful line 0.1 h ago (244/245 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p4-531223 | kv3_hg_v1p4 | 3_3_place_gp | 0.7 | overflow best 0.2128 last 0.2389 rows 37 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8422a4b86-973415 | kv3_pc_v1 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.0 h ago (58/58 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v12-977044 | kv3_pv_v12 | 3_3_place_gp | 0.5 | overflow best 0.5267 last 0.5267 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-579857 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (223/224 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | postcts_gate_TT | 9.1 | last meaningful line 0.2 h ago (808/808 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 5_2_route | 9.3 | last meaningful line 0.3 h ago (270/271 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-2390236 | slw_st_b_v1 | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (5382/5382 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | ffx-2396189 | ffx | generate_abstract | 0.1 | last meaningful line 0.0 h ago (914/914 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | pregrt_ff_hold | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 21.7 | drt_violations best 15279 last 15279 rows 16 | before-window best 19250, window best 15279 | PROGRESS: drt_violations improved 20.6 % in window |  |
| epyc11 | prd-eco_20261124_204246_1187010-i1-249436 | eco_20261124_204246_1187010-i1 | 5_1_grt | 0.6 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 14.1 | drt_violations best 1743 last 2528 rows 19 | before-window best 1879, window best 1743 | PROGRESS: drt_violations improved 7.2 % in window |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 14.0 | drt_violations best 21818 last 21818 rows 5 | before-window best 521993, window best 21818 | PROGRESS: drt_violations improved 95.8 % in window |  |
| epyc2 | kqc-sta_region_nb0_h17_n7_s8_bt2_synth0-2004899 | sta_region_nb0_h17_n7_s8_bt2_synth0 | 4_1_cts | 0.8 | repair_TNS best 0 last 0 rows 91 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | kqc-sta_region_nb0_h18_n7_s8_bt2_synth0-2007798 | sta_region_nb0_h18_n7_s8_bt2_synth0 | 3_5_place_dp | 0.8 | repair_Violations best 0 last 0 rows 3 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 41.1 | drt_violations best 10129 last 48097 rows 18 | before-window best 11554, window best 10129 | PROGRESS: drt_violations improved 12.3 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 34.4 | drt_violations best 7726 last 31531 rows 18 | before-window best 11933, window best 7726 | PROGRESS: drt_violations improved 35.3 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 19.1 | drt_violations best 5099 last 5099 rows 11 | before-window best 109083, window best 5099 | PROGRESS: drt_violations improved 95.3 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 15.3 | drt_violations best 116309 last 116309 rows 2 | before-window best 504597, window best 116309 | PROGRESS: drt_violations improved 77.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 13.9 | drt_violations best 510309 last 510309 rows 1 | before-window best 510309, window best 510309 | PROGRESS: drt_violations: active iteration at 387230 < best completed total 510309 (in-ite |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-1524868 | slw_sc_v1 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 19.3 | drt_violations best 66691 last 66691 rows 8 | before-window best 116989, window best 66691 | PROGRESS: drt_violations improved 43.0 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 15.4 | drt_violations best 59441 last 59441 rows 4 | before-window best 400194, window best 59441 | PROGRESS: drt_violations improved 85.1 % in window |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | 5_2_route | 10.6 | drt_violations best 111 last 111 rows 28 | before-window best 149425, window best 111 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 5_2_route | 10.6 | drt_violations best 72 last 72 rows 54 | before-window best 146485, window best 72 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 10.6 | drt_violations best 22483 last 22483 rows 9 | before-window best 274214, window best 22483 | PROGRESS: drt_violations improved 91.8 % in window |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3t-2289287 | eco_20261123_164145_1995767-i3t | 5_2_route | 8.1 | drt_violations best 5 last 5 rows 42 | before-window best 35664, window best 5 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | pregrt_ff_hold | 7.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | 5_2_route | 12.0 | drt_violations best 32830 last 32830 rows 2 | before-window best 234054, window best 32830 | PROGRESS: drt_violations improved 86.0 % in window |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-kv3_io_ft-1076451 | kv3_io_ft | 5_1_grt | 0.5 | repair_TNS best 0 last 0 rows 14 | PROGRESS: repair_TNS reached 0 |  |
