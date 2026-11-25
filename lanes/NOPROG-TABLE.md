# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 19:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'UNSIGNABLE': 2, 'GRT-LABEL': 5, 'YOUNG': 158, 'NO-DATA': 16, 'PROGRESS': 21}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 10.3 | last meaningful line 9.0 h ago (48/136 lines) | NO-PROGRESS: no new non-iteration log line for 9.0 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 5_1_grt | 10.6 | grt rounds 2 overflow 5:42234 -> 10:42876 | UNSIGNABLE: GRT overflow flat: overflow 42234 at iteration 5 -> 42876 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 13.4 | last meaningful line 9.8 h ago (48/193 lines) | NO-PROGRESS: no new non-iteration log line for 9.8 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 5.6 | repair_TNS best 827598 last 827598 rows 1 | before-window best 827598, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 5_1_grt | 12.3 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2360221 | slw_hc2 | pregrt_ff_hold | 7.2 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | CANCELLED |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-477535 | kv3_hgi_v2 | 5_1_grt | 2.1 | grt rounds 2 overflow 5:25885 -> 10:10162 | GRT-LABEL: DESIGN-FAIL: overflow 10162 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-560078 | kv3_hgi_v2 | 5_1_grt | 2.1 | grt rounds 2 overflow 5:18053 -> 10:8644 | GRT-LABEL: DESIGN-FAIL: overflow 8644 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | 5_1_grt | 10.5 | grt rounds 2 overflow 5:52829 -> 10:36669 | GRT-LABEL: DESIGN-FAIL: overflow 36669 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | 5_1_grt | 7.7 | grt rounds 1 overflow 5:41695 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 5_1_grt | 11.6 | grt rounds 2 overflow 5:83232 -> 10:63283 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-glue-1294589 | glue | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (5879/5879 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | 5_2_route | 7.2 | drt_violations best 2241 last 2241 rows 14 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r889141819-1619104 | kv3_hg_v1__r889141819 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (7515/7515 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r88f4bfb40-1671162 | kv3_hg_v1__r88f4bfb40 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (7566/7566 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r8dffc461a-1676050 | kv3_hg_v1__r8dffc461a | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (7627/7627 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p2-1802854 | kv3_hg_v1p2 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (7078/7078 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p3__r81da466fe-1840159 | kv3_hg_v1p3__r81da466fe | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (6926/6926 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-373156 | kv3_hgi | 5_1_grt | 2.2 | last meaningful line 1.5 h ago (296/1302 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | 4_1_cts | 1.8 | last meaningful line 0.2 h ago (11073/11073 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-1076148 | kv3_pc | 3_5_place_dp | 1.8 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r8b421e514-1086873 | kv3_pc | 3_5_place_dp | 1.8 | last meaningful line 0.0 h ago (55/55 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r85c02c25c-1098684 | kv3_pc | 3_5_place_dp | 1.8 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r882954158-1102222 | kv3_pc | 3_5_place_dp | 1.8 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-1535838 | kv3_pv_v12 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-native59-3384403 | native59 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (5363/5363 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | postcts_gate_FF | 9.5 | last meaningful line 0.3 h ago (860/860 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | postcts_gate_TT | 6.3 | last meaningful line 0.1 h ago (394/394 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | postcts_gate_TT | 6.7 | last meaningful line 0.0 h ago (1186/1186 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | postcts_gate_FF | 7.3 | last meaningful line 0.2 h ago (1092/1092 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2793057 | sle_stm_v1 | 5_2_route | 9.0 | drt_violations best 145941 last 145941 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | postcts_gate_TT | 8.4 | last meaningful line 0.2 h ago (743/743 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | postcts_gate_FF | 8.4 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 5_1_grt | 8.5 | last meaningful line 0.3 h ago (2057/2079 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | postcts_gate_TT | 6.2 | last meaningful line 0.1 h ago (580/580 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3681869 | slw_st_b_v2 | 4_1_cts | 2.7 | last meaningful line 0.1 h ago (4946/4946 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | 5_1_grt | 5.2 | last meaningful line 0.2 h ago (1149/1203 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-slw_stm_v1__cle34a73c3-4063338 | slw_stm_v1 | 5_2_route | 8.2 | drt_violations best 156777 last 156777 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | nice_bhabha | nice_bhabha | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (104/104 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-901577-23707 | 901577 | signoff | 4.5 | last meaningful line 4.5 h ago (3/3 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc10 | qc-colls-lec-h3 | qc-colls-lec-h3 | - | 2.6 |  | NO-DATA: no log found |  |
| epyc10 | qc-hc3-lec-r8-nearest | qc-hc3-lec-r8-nearest | - | 4.2 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R8_hc3_pvcca | relec-r2-R8_hc3_pvcca | - | 8.2 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 9.7 | last meaningful line 0.2 h ago (139/139 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 5_1_grt | 5.3 | last meaningful line 0.1 h ago (278/342 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | postcts_gate_TT | 6.3 | last meaningful line 0.1 h ago (370/370 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | 5_2_route | 9.8 | last meaningful line 0.4 h ago (273/274 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | pregrt_ff_hold | 5.0 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.6 h < 2.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | 5_2_route | 9.6 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | 5_2_route | 9.7 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | reg_fanout | 0.0 |  | NO-DATA: empty log |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | 5_2_route | 9.5 | drt_violations best 152868 last 152868 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-320042 | slw_st_b_v2 | 5_2_route | 9.5 | drt_violations best 17771 last 17771 rows 2 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl92142dac-136142 | slw_su_c | 3_5_place_dp | 1.3 | last meaningful line 0.0 h ago (78/78 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 8.7 |  | NO-DATA: no log found |  |
| epyc11 | otc-3389445-25127 | 3389445 | signoff | 2.3 | last meaningful line 2.3 h ago (3/3 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_154417_1016084-i2t-1425156 | eco_20261124_154417_1016084-i2t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i1-3176761 | eco_20261124_190641_1260390-i1 | 5_2_route | 2.6 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i1-3660942 | eco_20261124_200101_1087713-i1 | 5_2_route | 2.0 | last meaningful line 0.2 h ago (134/134 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_204246_1187010-i1-249436 | eco_20261124_204246_1187010-i1 | 5_1_grt | 1.1 | last meaningful line 0.4 h ago (237/1298 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc11 | so_1086046_ff_71982 | so_1086046_ff_71982 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc11 | so_1086046_tt_71982 | so_1086046_tt_71982 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-hd_host_w-2612050 | hd_host_w | pregrt_ff_hold | 0.9 | repair_TNS best 37184.7 last 37184.7 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-kv3_hgi_v8-2737550 | kv3_hgi_v8 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (5891/5891 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-1457043 | kv3_hroot | generate_abstract | 4.4 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-491987 | sle_hc0 | 5_2_route | 8.2 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-1254949 | sle_hc2 | 5_2_route | 7.7 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3414126 | sle_hc2 | 5_2_route | 9.1 | drt_violations best 7035 last 7035 rows 3 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__clcc5e3e61-3434617 | sle_hc2 | 5_2_route | 9.1 | drt_violations best 14740 last 14740 rows 2 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3568552 | sle_st_b_v1 | 3_3_place_gp | 0.4 | overflow best 0.7236 last 0.7236 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3668964 | sle_st_b_v2 | pregrt_ff_hold | 3.0 | repair_TNS best 21609.5 last 21609.5 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-4153401 | sle_stm_v2 | 5_2_route | 8.6 | drt_violations best 26656 last 26656 rows 2 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1101031 | slw_hc3 | 5_2_route | 7.8 | drt_violations best 9724 last 9724 rows 2 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3657462 | slw_stm_v2 | 5_2_route | 8.9 | drt_violations best 124000 last 124000 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | kqc-sta_region_nb0_h18_n7_s8_bt2_synth0-2007798 | sta_region_nb0_h18_n7_s8_bt2_synth0 | 6_report | 1.3 | last meaningful line 0.0 h ago (57/57 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-3544630-5805 | 3544630 | signoff | 0.4 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_165709_1862160-i1t-580795 | eco_20261124_165709_1862160-i1t | 5_2_route | 2.3 | drt_violations best 5855 last 5855 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 7.9 |  | NO-DATA: no log found |  |
| epyc2 | so_4184631_ff_26038 | so_4184631_ff_26038 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | so_4184631_tt_26038 | so_4184631_tt_26038 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-1559108 | cbn_q01 | pregrt_ff_hold | 2.5 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 4_1_cts | 2.6 | last meaningful line 0.3 h ago (10792/10792 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-2222980 | sle_fw_v2 | postcts_gate_FF | 9.9 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 9.8 | drt_violations best 412199 last 412199 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | 5_2_route | 10.1 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | 5_2_route | 9.9 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 5_2_route | 10.0 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-2253577 | slw_hc2 | 5_2_route | 9.9 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-1524868 | slw_sc_v1 | 5_1_grt | 2.5 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | 5_2_route | 10.0 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | 5_2_route | 14.3 | drt_violations best 16327 last 16327 rows 2 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | 5_2_route | 9.9 | drt_violations best 121792 last 121792 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | otc-82892-20311 | 82892 | signoff | 0.9 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | prd-count-p1_tc-231566 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i3-2609460 | eco_20261123_171023_3055226-i3 | 5_2_route | 1.9 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_145005_2036075-i2-1496134 | eco_20261124_145005_2036075-i2 | 5_2_route | 2.5 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i1-2124005 | eco_20261124_192157_3493836-i1 | 5_2_route | 2.2 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | prd-fin-864737 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (72/72 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | postcts_gate_TT | 11.1 | last meaningful line 0.1 h ago (1934/1934 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 5_2_route | 11.1 | drt_violations best 162445 last 162445 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 5_2_route | 11.1 | last meaningful line 0.1 h ago (259/259 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 5_2_route | 11.1 | last meaningful line 0.1 h ago (129/129 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | 5_2_route | 11.2 | drt_violations best 105806 last 105806 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | 5_2_route | 11.2 | drt_violations best 103684 last 103684 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 11.1 | last meaningful line 0.7 h ago (277/278 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 5_2_route | 11.1 | last meaningful line 0.2 h ago (135/135 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 5_2_route | 11.1 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | 5_2_route | 11.1 | last meaningful line 0.1 h ago (277/278 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | 5_2_route | 11.1 | drt_violations best 160491 last 160491 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | postcts_gate_FF | 11.1 | last meaningful line 0.1 h ago (1803/1803 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 5_2_route | 11.1 | last meaningful line 0.2 h ago (260/261 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 5_2_route | 11.1 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 5_2_route | 11.1 | last meaningful line 0.5 h ago (137/137 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | 5_2_route | 11.2 | drt_violations best 98742 last 98742 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 11.1 | last meaningful line 0.7 h ago (281/282 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 11.0 | drt_violations best 379431 last 379431 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 5_2_route | 11.1 | last meaningful line 0.5 h ago (130/130 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | otc-120424-12773 | 120424 | signoff | 0.9 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | otc-2900322-1356 | 2900322 | - | 3.2 |  | NO-DATA: no log found |  |
| epyc8 | prd-count-p1_tc-2289287 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_012701_4018610-i1-2166955 | eco_20261125_012701_4018610-i1 | 5_2_route | 1.8 | last meaningful line 0.1 h ago (265/266 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_025941_3548303-i1t-1829547 | eco_20261125_025941_3548303-i1t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_030756_3907869-i1-2163277 | eco_20261125_030756_3907869-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 8.0 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-col-h9-r0-p2--t1--cl9f71e63d--pvef55eb84-grt-3351077 | col-h9-r0-p2--t1--cl9f71e63d--pvef55eb84-grt | lec | 0.2 | LEC last write 0.2 h ago | YOUNG: evidence 0.2 h < 6 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3738475 | col_h10_r0_p1__t1 | 3_3_place_gp | 1.0 | overflow best 0.5106 last 0.5106 rows 2 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3746069 | col_h10_r0_p1__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3306 last 3306 rows 565 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-2954633 | col_h10_r0_p1__t1 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3192741 | col_h10_r1__t1 | 3_3_place_gp | 0.2 | overflow best 0.4754 last 0.4754 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-2956272 | col_h9_r0_p1__t1 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (262/262 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-519508 | col_h9_r0_p2__t1 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-1567415 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.6 | overflow best 0.1998 last 0.1998 rows 36 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pvcb7f0079-1236189 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.7 | last meaningful line 0.0 h ago (279/279 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvcd8810ba-1306563 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.6 | overflow best 0.3361 last 0.3361 rows 32 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-1408553 | col_h9_r0_p4__t1 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (97/97 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 7.8 | drt_violations best 1594 last 1594 rows 13 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t36-2961386 | ot_s81sl_leaf__t36 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.7045 last 0.7045 rows 21 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t75-3530149 | ot_s81sl_leaf__t75 | 2_1_floorplan | 0.1 | repair_Viol best 3998 last 3998 rows 689 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-serdes__t13-1595964 | serdes__t13 | 3_4_place_resized | 1.6 | repair_Remaining best 76196 last 76196 rows 272 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-serdes__t4-3729546 | serdes__t4 | 3_3_place_gp | 1.0 | overflow best 0.9258 last 0.9258 rows 6 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | pregrt_ff_hold | 7.5 | repair_TNS best 315444 last 315444 rows 1 | YOUNG: evidence 1.6 h < 2.5 h |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_2_route | 8.0 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-667540 | sle_hc1 | postcts_gate_FF | 8.1 | last meaningful line 0.1 h ago (818/818 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t30__clcedefe91-1240625 | slice_station__t30 | postcts_gate_FF | 0.7 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t41-2957781 | slice_station__t41 | 3_3_place_gp | 0.3 | overflow best 0.2657 last 0.2657 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | postcts_gate_TT | 8.2 | last meaningful line 0.1 h ago (761/761 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | eco-abs-1458375 | eco-abs | generate_abstract | 0.6 | last meaningful line 0.2 h ago (691/691 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | otc-3045448-2377 | 3045448 | gen_lint_yosys | 1.2 | last meaningful line 0.0 h ago (7/7 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-cbn_q00__cldbcda913-2913832 | cbn_q00 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (218/218 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-coll_core-3813096 | coll_core | tt_setup_repair_grt | 9.2 | repair_Viol best 1080 last 1080 rows 7 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1102342 | kv3_hg_v1p3__r838481cd7 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (6787/6787 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v6-102352 | kv3_hgi_v6 | 4_1_cts | 1.6 | last meaningful line 0.2 h ago (6263/6263 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Eo-371567 | kv3_hub_Eo | 3_5_place_dp | 3.1 | last meaningful line 0.0 h ago (118/118 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 5_2_route | 14.2 | last meaningful line 0.1 h ago (263/263 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v3-1442734 | sle_fw_v3 | postcts_gate_FF | 7.9 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | postcts_gate_FF | 9.9 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 4_1_cts | 2.0 | last meaningful line 0.2 h ago (5618/5618 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 5_1_grt | 6.2 | last meaningful line 0.3 h ago (148/148 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 5_2_route | 7.9 | last meaningful line 0.3 h ago (265/266 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 6.1 | drt_violations best 187976 last 187976 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 4_1_cts | 3.7 | last meaningful line 0.3 h ago (5645/5645 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3325358 | slw_fw_v1 | 4_1_cts | 3.7 | last meaningful line 0.2 h ago (5460/5460 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 14.2 | last meaningful line 0.5 h ago (279/280 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v3-1399930 | slw_fw_v3 | postcts_gate_FF | 8.0 | last meaningful line 0.0 h ago (1951/1951 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 4_1_cts | 4.7 | last meaningful line 0.3 h ago (5368/5368 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | postcts_gate_TT | 9.9 | last meaningful line -0.0 h ago (45033/45033 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | 5_2_route | 14.1 | drt_violations best 156960 last 156960 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 5_2_route | 9.9 | last meaningful line 0.3 h ago (266/267 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1e5219ea-4177722 | slw_su_l0 | 5_2_route | 6.0 | drt_violations best 133698 last 133698 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-3090069 | slw_su_l0 | postcts_gate_FF | 3.8 | last meaningful line 0.0 h ago (779/779 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 8.0 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 8.0 |  | NO-DATA: no log found |  |
| intel1 | otc-3192080-15624 | 3192080 | eq10 | 2.0 | last meaningful line 1.7 h ago (517751/517751 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i2-2930338 | eco_20261123_191853_2879776-i2 | 5_1_grt | 2.1 | last meaningful line 1.3 h ago (239/1479 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | ap-ageom-kw-kv3-hg-v1p4-grt-4049867 | kv3-hg-v1p4-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_ctl-2153206 | hd_ctl | 5_2_route | 2.8 | last meaningful line 0.1 h ago (260/261 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p3__r8c662a835-2676319 | kv3_hg_v1p3__r8c662a835 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (57/57 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-1076451 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5442 last 5442 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8422a4b86-973415 | kv3_pc_v1 | 3_3_place_gp | 1.0 | overflow best 0.6583 last 0.6583 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-kv3_pv_v12-977044 | kv3_pv_v12 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 9.6 | last meaningful line 0.2 h ago (133/133 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 5_2_route | 9.8 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-2390236 | slw_st_b_v1 | pregrt_ff_hold | 2.6 | repair_TNS best 15507.5 last 15507.5 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | so_67427_ff_43314 | so_67427_ff_43314 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_67427_tt_43314 | so_67427_tt_43314 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | 5_1_grt | 5.7 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | pregrt_ff_hold | 7.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 22.2 | drt_violations best 15279 last 15279 rows 16 | before-window best 19250, window best 15279 | PROGRESS: drt_violations improved 20.6 % in window |  |
| epyc11 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2533872 | slw_hc3 | 5_1_grt | 3.4 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 14.5 | drt_violations best 18538 last 18538 rows 7 | before-window best 521993, window best 18538 | PROGRESS: drt_violations improved 96.4 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 41.6 | drt_violations best 10129 last 48097 rows 18 | before-window best 11554, window best 10129 | PROGRESS: drt_violations improved 12.3 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 34.9 | drt_violations best 7726 last 31531 rows 18 | before-window best 11933, window best 7726 | PROGRESS: drt_violations improved 35.3 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 19.6 | drt_violations best 4070 last 4070 rows 12 | before-window best 109083, window best 4070 | PROGRESS: drt_violations improved 96.3 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 15.8 | drt_violations best 116309 last 116309 rows 2 | before-window best 504597, window best 116309 | PROGRESS: drt_violations improved 77.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 14.4 | drt_violations best 510309 last 510309 rows 1 | before-window best 510309, window best 510309 | PROGRESS: drt_violations: active iteration at 327089 < best completed total 510309 (in-ite |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 14.2 | drt_violations best 457993 last 457993 rows 1 | before-window best 457993, window best 457993 | PROGRESS: drt_violations: active iteration at 290756 < best completed total 457993 (in-ite |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-2092169 | slw_sc_v1 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 19.8 | drt_violations best 66691 last 66691 rows 8 | before-window best 116989, window best 66691 | PROGRESS: drt_violations improved 43.0 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 15.9 | drt_violations best 59441 last 59441 rows 4 | before-window best 400194, window best 59441 | PROGRESS: drt_violations improved 85.1 % in window |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | 5_2_route | 11.1 | drt_violations best 72 last 72 rows 35 | before-window best 149425, window best 72 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 5_2_route | 11.1 | drt_violations best 72 last 72 rows 54 | before-window best 146485, window best 72 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 11.1 | drt_violations best 20520 last 20520 rows 10 | before-window best 274214, window best 20520 | PROGRESS: drt_violations improved 92.5 % in window |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | 5_2_route | 12.3 | drt_violations best 32830 last 32830 rows 2 | before-window best 234054, window best 32830 | PROGRESS: drt_violations improved 86.0 % in window |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 5_1_grt | 6.0 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | otc-2434312-2110 | 2434312 | flow | 2.3 | repair_Violations best 0 last 0 rows 19 | PROGRESS: repair_Violations reached 0 |  |
