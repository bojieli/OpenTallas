# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 20:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'UNSIGNABLE': 3, 'GRT-LABEL': 1, 'NO-DATA': 13, 'YOUNG': 149, 'PROGRESS': 20}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 11.1 | last meaningful line 9.8 h ago (48/137 lines) | NO-PROGRESS: no new non-iteration log line for 9.8 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 5_1_grt | 11.4 | grt rounds 2 overflow 5:42234 -> 10:42876 | UNSIGNABLE: GRT overflow flat: overflow 42234 at iteration 5 -> 42876 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 14.1 | last meaningful line 10.6 h ago (48/194 lines) | NO-PROGRESS: no new non-iteration log line for 10.6 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | 5_1_grt | 8.5 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 6.3 | repair_TNS best 827598 last 827598 rows 1 | before-window best 827598, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 5_1_grt | 13.1 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | pregrt_ff_hold | 8.2 | repair_TNS best 315444 last 315444 rows 1 | before-window best 315444, window best 315444 | NO-PROGRESS: repair_TNS best 315444 vs 315444 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | 5_1_grt | 11.2 | grt rounds 2 overflow 5:52829 -> 10:36669 | GRT-LABEL: DESIGN-FAIL: overflow 36669 at round 10 > 1000 |  |
| epyc10 | ap-ageom-kw-kv3-pv-v3-grt-3682645 | kv3-pv-v3-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-glue-1294589 | glue | pregrt_ff_hold | 2.5 | repair_TNS best 4981.3 last 4981.3 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | 5_2_route | 7.9 | drt_violations best 1820 last 7048 rows 18 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r889141819-1619104 | kv3_hg_v1__r889141819 | tt_setup_repair | 2.3 | last meaningful line 0.0 h ago (351/351 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r88f4bfb40-1671162 | kv3_hg_v1__r88f4bfb40 | tt_setup_repair | 2.2 | repair_Viol best 2237 last 2237 rows 22 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-kv3_hg_v1__r8dffc461a-1676050 | kv3_hg_v1__r8dffc461a | tt_setup_repair | 2.2 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p2-1802854 | kv3_hg_v1p2 | 4_1_cts | 2.2 | last meaningful line 0.1 h ago (7189/7189 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p3__r81da466fe-1840159 | kv3_hg_v1p3__r81da466fe | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (7196/7196 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-373156 | kv3_hgi | 5_1_grt | 3.0 | last meaningful line 2.3 h ago (296/1304 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-3860531 | kv3_hgi | tt_setup_measure | 0.0 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | 4_1_cts | 2.6 | last meaningful line 0.1 h ago (11167/11167 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-2844240 | kv3_pc | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4063/4064 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r8b421e514-2986767 | kv3_pc | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4043/4044 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r85c02c25c-3151820 | kv3_pc | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (4054/4054 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r882954158-3053902 | kv3_pc | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4063/4064 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-3561929 | kv3_pc_v1 | 2_1_floorplan | 0.2 | repair_Viol best 8511 last 8511 rows 399 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r84d0332e1-3581607 | kv3_pc_v1 | 2_1_floorplan | 0.2 | repair_Viol best 8514 last 8514 rows 252 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r884969661-3601103 | kv3_pc_v1 | 2_1_floorplan | 0.1 | repair_Viol best 8514 last 8514 rows 233 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8afe1e027-3618066 | kv3_pc_v1 | 2_1_floorplan | 0.1 | repair_Viol best 8514 last 8514 rows 155 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8c9cba7ae-3633962 | kv3_pc_v1 | 2_1_floorplan | 0.1 | repair_Viol best 8514 last 8514 rows 121 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-3669242 | kv3_pc_v1 | 2_1_floorplan | 0.1 | repair_Viol best 8516 last 8516 rows 78 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v12-1535838 | kv3_pv_v12 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (9040/9040 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-3355795 | kv3_pv_v12 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (8567/8567 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | 5_1_grt | 6.4 | last meaningful line 0.8 h ago (267/1274 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-native59-3384403 | native59 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (5511/5511 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | postcts_gate_FF | 10.2 | last meaningful line -0.0 h ago (70767/70767 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | postcts_gate_FF | 7.1 | last meaningful line 0.0 h ago (392/392 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | postcts_gate_FF | 7.5 | last meaningful line 0.1 h ago (524/524 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | 5_2_route | 8.0 | last meaningful line 0.1 h ago (268/268 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2793057 | sle_stm_v1 | 5_2_route | 9.8 | drt_violations best 21613 last 21613 rows 2 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | postcts_gate_FF | 9.2 | last meaningful line 0.1 h ago (741/741 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | postcts_gate_TT | 9.2 | last meaningful line 0.1 h ago (1663/1663 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | postcts_gate_TT | 9.2 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | postcts_gate_FF | 7.0 | last meaningful line 0.0 h ago (555/555 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3681869 | slw_st_b_v2 | pregrt_ff_hold | 3.5 | repair_TNS best 15780.3 last 15780.3 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | postcts_gate_TT | 5.9 | last meaningful line 0.0 h ago (1086/1086 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_stm_v1__cle34a73c3-4063338 | slw_stm_v1 | 5_2_route | 9.0 | drt_violations best 156777 last 156777 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc10 | otc-901577-23707 | 901577 | signoff | 5.3 | last meaningful line 5.3 h ago (3/3 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc10 | qc-hc3-lec-r8-nearest | qc-hc3-lec-r8-nearest | - | 5.0 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 10.5 | last meaningful line 0.3 h ago (270/271 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 5_1_grt | 6.1 | last meaningful line 0.1 h ago (1091/1125 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 5_2_route | 7.1 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | 5_2_route | 10.5 | drt_violations best 146067 last 146067 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 5_1_grt | 5.8 | last meaningful line 0.3 h ago (140/140 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | 5_2_route | 10.3 | last meaningful line 0.3 h ago (283/284 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | 5_2_route | 10.5 | drt_violations best 138497 last 138497 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2533872 | slw_hc3 | postcts_gate_TT | 4.1 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (66/66 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | 5_2_route | 10.3 | drt_violations best 152868 last 152868 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-320042 | slw_st_b_v2 | 5_2_route | 10.3 | drt_violations best 12837 last 12837 rows 3 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 9.5 |  | NO-DATA: no log found |  |
| epyc11 | otc-3389445-25127 | 3389445 | signoff | 3.1 | last meaningful line 3.0 h ago (3/3 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_154417_1016084-i2t-1425156 | eco_20261124_154417_1016084-i2t | 5_1_grt | 0.8 | last meaningful line 0.3 h ago (241/1323 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i1-3176761 | eco_20261124_190641_1260390-i1 | 5_2_route | 3.4 | last meaningful line 0.1 h ago (280/281 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i1-3660942 | eco_20261124_200101_1087713-i1 | 5_2_route | 2.8 | last meaningful line 0.3 h ago (271/272 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_204246_1187010-i1-249436 | eco_20261124_204246_1187010-i1 | 5_1_grt | 1.9 | last meaningful line 1.2 h ago (237/1404 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_034700_3857841-i1-2214083 | eco_20261125_034700_3857841-i1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v8-2737550 | kv3_hgi_v8 | pregrt_ff_hold | 1.6 | repair_TNS best 115.718 last 115.718 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-491987 | sle_hc0 | 5_2_route | 8.9 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-1254949 | sle_hc2 | 5_2_route | 8.5 | drt_violations best 102042 last 102042 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__clcc5e3e61-3434617 | sle_hc2 | 6_report | 9.9 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1216203 | sle_st_b_v1 | 3_3_place_gp | 0.0 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3668964 | sle_st_b_v2 | 5_1_grt | 3.8 | last meaningful line 0.2 h ago (266/1270 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-4153401 | sle_stm_v2 | 6_report | 9.4 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1101031 | slw_hc3 | 6_report | 8.5 | last meaningful line 0.1 h ago (69/69 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3657462 | slw_stm_v2 | 5_2_route | 9.7 | drt_violations best 124000 last 124000 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | otc-3544630-5805 | 3544630 | signoff | 1.2 | last meaningful line 1.1 h ago (3/3 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_165709_1862160-i1t-580795 | eco_20261124_165709_1862160-i1t | 5_2_route | 3.0 | drt_violations best 5855 last 5855 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 8.7 |  | NO-DATA: no log found |  |
| epyc2 | so_952237_ff_27997 | so_952237_ff_27997 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | so_952237_tt_27997 | so_952237_tt_27997 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-1559108 | cbn_q01 | pregrt_ff_hold | 3.2 | repair_TNS best 14062.5 last 14062.5 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 4_1_cts | 3.4 | last meaningful line 0.3 h ago (10798/10798 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-2222980 | sle_fw_v2 | postcts_gate_TT | 10.6 | last meaningful line 0.2 h ago (1821/1821 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 10.6 | drt_violations best 412199 last 412199 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | 5_2_route | 10.8 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | 5_2_route | 10.7 | last meaningful line 0.1 h ago (260/261 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 5_2_route | 10.8 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-2253577 | slw_hc2 | 5_2_route | 10.6 | drt_violations best 101260 last 101260 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-1524868 | slw_sc_v1 | 5_1_grt | 3.2 | last meaningful line 0.3 h ago (1299/1866 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-2092169 | slw_sc_v1 | 5_1_grt | 2.9 | last meaningful line 0.1 h ago (143/143 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | 5_2_route | 10.7 | drt_violations best 128832 last 128832 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | 5_2_route | 10.6 | drt_violations best 121792 last 121792 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i3-2609460 | eco_20261123_171023_3055226-i3 | 5_2_route | 2.6 | last meaningful line 0.0 h ago (275/275 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i2-1757367 | eco_20261124_175441_992552-i2 | 5_2_route | 0.7 | last meaningful line 0.1 h ago (247/247 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i1-2124005 | eco_20261124_192157_3493836-i1 | 5_2_route | 2.9 | last meaningful line 0.3 h ago (272/273 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i1-2232939 | eco_20261124_235631_1843084-i1 | 5_1_grt | 0.5 | last meaningful line 0.4 h ago (297/1397 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-fin-1496134 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | postcts_gate_FF | 11.9 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 5_2_route | 11.9 | drt_violations best 162445 last 162445 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 5_2_route | 11.9 | last meaningful line 0.5 h ago (262/263 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 5_2_route | 11.9 | last meaningful line 0.0 h ago (260/260 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | 5_2_route | 11.9 | drt_violations best 105806 last 105806 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | 5_2_route | 11.9 | drt_violations best 103684 last 103684 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 11.8 | drt_violations best 478667 last 478667 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 5_2_route | 11.9 | last meaningful line 0.0 h ago (207/207 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 5_2_route | 11.9 | last meaningful line 0.4 h ago (275/276 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | 5_2_route | 11.9 | last meaningful line 0.1 h ago (283/284 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 11.9 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 5_2_route | 11.9 | last meaningful line 0.4 h ago (264/265 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 5_2_route | 11.9 | last meaningful line 0.4 h ago (137/137 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 5_2_route | 11.9 | last meaningful line 0.5 h ago (268/269 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | 5_2_route | 11.9 | drt_violations best 98742 last 98742 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 11.8 | last meaningful line 1.0 h ago (283/284 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 6_report | 11.9 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 5_2_route | 11.9 | last meaningful line 0.5 h ago (261/262 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | otc-120424-12773 | 120424 | signoff | 1.6 | last meaningful line 1.5 h ago (3/3 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | otc-2900322-1356 | 2900322 | - | 3.9 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3-32256 | eco_20261123_164145_1995767-i3 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_012701_4018610-i1-2166955 | eco_20261125_012701_4018610-i1 | 5_2_route | 2.5 | drt_violations best 172 last 172 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_025941_3548303-i1t-1829547 | eco_20261125_025941_3548303-i1t | 5_1_grt | 1.0 | last meaningful line 0.3 h ago (141/141 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_030756_3907869-i1-2163277 | eco_20261125_030756_3907869-i1 | 5_1_grt | 0.8 | last meaningful line 0.0 h ago (289/312 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 8.8 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-col-h10-r0-p1--t1--cl574cc59d--pv3d0d4d97-grt-3106610 | col-h10-r0-p1--t1--cl574cc59d--pv3d0d4d97-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-col-h9-r0-p3--t1--cl8ce97bcb--pv1489a898-grt-3268720 | col-h9-r0-p3--t1--cl8ce97bcb--pv1489a898-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-col-h9-r0-p3--t1--cl8ce97bcb--pvcd8810ba-grt-3260599 | col-h9-r0-p3--t1--cl8ce97bcb--pvcd8810ba-grt | lec | 0.1 | LEC last write 0.1 h ago | YOUNG: evidence 0.1 h < 6 h |  |
| epyc9 | ap-ageom-kw-col-h9-r0-p5--t1--pv35382794-grt-3391882 | col-h9-r0-p5--t1--pv35382794-grt | lec | 0.1 | LEC last write 0.0 h ago | YOUNG: evidence 0.1 h < 6 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3746069 | col_h10_r0_p1__t1 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (272/272 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-2954633 | col_h10_r0_p1__t1 | 3_3_place_gp | 1.0 | overflow best 0.5047 last 0.5074 rows 9 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 8.6 | drt_violations best 1557 last 1557 rows 15 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_2_route | 8.8 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-667540 | sle_hc1 | 5_2_route | 8.9 | last meaningful line 0.1 h ago (128/128 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t30__clcedefe91-1240625 | slice_station__t30 | 5_3_fillcell | 1.4 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 8.9 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | otc-1674265-30050 | 1674265 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | otc-1821029-25913 | 1821029 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | so_1805604_ff_8597 | so_1805604_ff_8597 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (695/695 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | so_1805604_tt_8597 | so_1805604_tt_8597 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (695/695 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | ap-ageom-kw-kv3-hub-Eo-grt-1856966 | kv3-hub-Eo-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-cbn_q00__cldbcda913-2913832 | cbn_q00 | 3_5_place_dp | 1.2 | last meaningful line 0.0 h ago (106/106 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1102342 | kv3_hg_v1p3__r838481cd7 | 4_1_cts | 1.9 | last meaningful line 0.0 h ago (6925/6925 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v6-102352 | kv3_hgi_v6 | pregrt_ff_hold | 2.3 | repair_TNS best 29247.6 last 29247.6 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | postcts_gate_TT | 12.4 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 5_2_route | 15.0 | last meaningful line 0.5 h ago (266/267 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v3-1442734 | sle_fw_v3 | postcts_gate_TT | 8.7 | last meaningful line 0.1 h ago (1822/1822 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | postcts_gate_FF | 10.6 | last meaningful line 0.2 h ago (768/768 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 4_1_cts | 2.7 | last meaningful line 0.0 h ago (5718/5718 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 5_1_grt | 7.0 | last meaningful line 0.5 h ago (296/1117 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 5_2_route | 8.7 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 6.9 | drt_violations best 187976 last 187976 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 4_1_cts | 4.4 | last meaningful line 0.3 h ago (5773/5773 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3325358 | slw_fw_v1 | 4_1_cts | 4.4 | last meaningful line 0.1 h ago (5584/5584 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 14.9 | last meaningful line 0.7 h ago (281/282 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | pregrt_ff_hold | 5.5 | repair_TNS best 8823.1 last 8823.1 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 5_1_grt | 6.7 | last meaningful line 0.1 h ago (1078/1095 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | postcts_gate_FF | 10.6 | last meaningful line -0.0 h ago (1217/1217 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | 5_2_route | 14.9 | drt_violations best 156960 last 156960 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 5_2_route | 10.6 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1e5219ea-4177722 | slw_su_l0 | 5_2_route | 6.8 | drt_violations best 133698 last 133698 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-3090069 | slw_su_l0 | 5_2_route | 4.5 | last meaningful line 0.2 h ago (255/255 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 8.8 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 8.8 |  | NO-DATA: no log found |  |
| intel1 | otc-2434312-2110 | 2434312 | flow | 3.0 | repair_Violations best 303 last 307 rows 17 | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | otc-4000256-29997 | 4000256 | eq11 | 0.7 | last meaningful line -0.0 h ago (543347/543347 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | otc-4001240-3461 | 4001240 | eq11 | 0.7 | last meaningful line 0.0 h ago (543152/543152 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i2-2930338 | eco_20261123_191853_2879776-i2 | 5_2_route | 2.9 | last meaningful line 0.2 h ago (135/135 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-hd_ctl-2153206 | hd_ctl | 5_2_route | 3.5 | drt_violations best 8186 last 8186 rows 2 | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8422a4b86-973415 | kv3_pc_v1 | 3_5_place_dp | 1.8 | last meaningful line 0.3 h ago (32/32 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-877532 | slice_station__t12 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (109/109 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 10.4 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 5_2_route | 10.6 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-2390236 | slw_st_b_v1 | 5_1_grt | 3.4 | last meaningful line 0.1 h ago (143/143 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | pregrt_ff_hold | 7.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 22.9 | drt_violations best 15279 last 15279 rows 16 | before-window best 18158, window best 15279 | PROGRESS: drt_violations improved 15.9 % in window |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 15.2 | drt_violations best 16679 last 16679 rows 9 | before-window best 521993, window best 16679 | PROGRESS: drt_violations improved 96.8 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 42.3 | drt_violations best 10129 last 21070 rows 19 | before-window best 11554, window best 10129 | PROGRESS: drt_violations improved 12.3 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 35.6 | drt_violations best 7726 last 31531 rows 18 | before-window best 11933, window best 7726 | PROGRESS: drt_violations improved 35.3 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 20.4 | drt_violations best 3524 last 3524 rows 13 | before-window best 78233, window best 3524 | PROGRESS: drt_violations improved 95.5 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 16.5 | drt_violations best 84872 last 84872 rows 3 | before-window best 504597, window best 84872 | PROGRESS: drt_violations improved 83.2 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 15.2 | drt_violations best 510309 last 510309 rows 1 | before-window best 510309, window best 510309 | PROGRESS: drt_violations: active iteration at 280794 < best completed total 510309 (in-ite |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 15.0 | drt_violations best 457993 last 457993 rows 1 | before-window best 457993, window best 457993 | PROGRESS: drt_violations: active iteration at 250195 < best completed total 457993 (in-ite |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 20.6 | drt_violations best 66691 last 66691 rows 8 | before-window best 74091, window best 66691 | PROGRESS: drt_violations improved 10.0 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 16.7 | drt_violations best 55677 last 55677 rows 5 | before-window best 400194, window best 55677 | PROGRESS: drt_violations improved 86.1 % in window |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | 5_2_route | 15.0 | drt_violations best 11246 last 11246 rows 3 | before-window best 122101, window best 11246 | PROGRESS: drt_violations improved 90.8 % in window |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | 5_2_route | 11.9 | drt_violations best 27225 last 27225 rows 2 | before-window best 160491, window best 27225 | PROGRESS: drt_violations improved 83.0 % in window |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 11.8 | drt_violations best 379431 last 379431 rows 1 | before-window best 379431, window best 379431 | PROGRESS: drt_violations: active iteration at 193058 < best completed total 379431 (in-ite |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | 5_2_route | 11.9 | drt_violations best 72 last 72 rows 45 | before-window best 149425, window best 72 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 11.9 | drt_violations best 15345 last 15345 rows 11 | before-window best 89614, window best 15345 | PROGRESS: drt_violations improved 82.9 % in window |  |
| epyc9 | dpkit-serdes__t4-3729546 | serdes__t4 | 3_5_place_dp | 1.8 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | 5_2_route | 13.0 | drt_violations best 20184 last 20184 rows 3 | before-window best 234054, window best 20184 | PROGRESS: drt_violations improved 91.4 % in window |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | pregrt_ff_hold | 5.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel2 | dpkit-coll_ftm-98785 | coll_ftm | 5_1_grt | 0.7 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
