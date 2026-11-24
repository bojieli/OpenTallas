# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 14:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 7, 'UNSIGNABLE': 1, 'GRT-LABEL': 3, 'YOUNG': 173, 'NO-DATA': 29, 'PROGRESS': 27}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | pregrt_ff_hold | 5.9 | repair_TNS best 110979 last 110979 rows 1 | before-window best 110979, window best 110979 | NO-PROGRESS: repair_TNS best 110979 vs 110979 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | pregrt_ff_hold | 5.7 | repair_TNS best 149411 last 149411 rows 1 | before-window best 149411, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| intel1 | dpkit-cbf_q00__cl1b5a6458-4114232 | cbf_q00 | 5_1_grt | 4.5 | grt rounds 2 overflow 5:6528 -> 10:6453 | UNSIGNABLE: GRT overflow flat: overflow 6528 at iteration 5 -> 6453 at iteration 10: flat fo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2973163 | slw_hc3 | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 22.4 | last meaningful line 11.6 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 11.6 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1797391-24144 | 1797391 | flow3 | 9.3 | last meaningful line 9.0 h ago (208/209 lines) | NO-PROGRESS: no new non-iteration log line for 9.0 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 26.2 | last meaningful line 11.6 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 11.6 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-60615 | sle_st_b_v2 | pregrt_ff_hold | 5.1 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-kv3_pv_v7e-1156836 | kv3_pv_v7e | 5_1_grt | 5.5 | grt rounds 1 overflow 5:101255 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc11 | dpkit-kv3_pv_v4ne-3869988 | kv3_pv_v4ne | 5_1_grt | 5.3 | grt rounds 1 overflow 5:114063 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pv_v3ne-3760907 | kv3_pv_v3ne | 5_1_grt | 7.6 | grt rounds 1 overflow 5:47095 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 5.6 | last meaningful line 4.3 h ago (48/60 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | 5_2_route | 2.4 | last meaningful line 0.1 h ago (249/250 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1479488 | hd_spn | 5_2_route | 2.3 | last meaningful line 0.1 h ago (252/253 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v3-1126078 | kv3_hg_v3 | 5_1_grt | 5.5 | last meaningful line 1.5 h ago (303/1313 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r8b421e514-312614 | kv3_pc | 2_1_floorplan | 0.2 | repair_Viol best 7558 last 7558 rows 733 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r884969661-245905 | kv3_pc_v1 | 2_1_floorplan | 0.2 | repair_Viol best 8514 last 8514 rows 752 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (9025/9025 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-3644344 | kv3_pv_v12 | 3_3_place_gp | 0.7 | overflow best 0.2571 last 0.2571 rows 35 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v2n-1048434 | kv3_pv_v2n | 5_1_grt | 5.6 | last meaningful line 1.3 h ago (265/1275 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-2704273 | kv3_pv_v3 | 3_5_place_dp | 1.3 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-3757611 | kv3_pv_v3 | 3_3_place_gp | 0.6 | last meaningful line 0.0 h ago (76/76 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v6-908877 | kv3_pv_v6 | 5_1_grt | 5.7 | last meaningful line 0.0 h ago (183/183 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v1__clf58b4dfb-461721 | sle_fw_v1 | pregrt_ff_hold | 3.1 | repair_TNS best 25810.6 last 25810.6 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_1_grt | 4.7 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-660000 | sle_hc0 | 4_1_cts | 2.9 | last meaningful line 0.3 h ago (5831/5831 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | 4_1_cts | 1.6 | last meaningful line 0.1 h ago (4996/4996 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | 4_1_cts | 2.0 | last meaningful line 0.0 h ago (5733/5733 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1583204 | sle_st_b_v1 | 4_1_cts | 2.2 | last meaningful line 0.1 h ago (5589/5589 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | pregrt_ff_hold | 2.5 | repair_TNS best 20636.6 last 20636.6 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v2__clfde1249e-689859 | sle_st_b_v2 | pregrt_ff_hold | 2.9 | repair_TNS best 18694 last 18694 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2793057 | sle_stm_v1 | tt_setup_repair_grt | 4.3 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | pregrt_ff_hold | 3.7 | repair_TNS best 266902 last 266902 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | pregrt_ff_hold | 3.7 | repair_TNS best 269355 last 269355 rows 1 | YOUNG: evidence 1.0 h < 2.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 4_1_cts | 3.7 | last meaningful line 0.1 h ago (8711/8711 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | 4_1_cts | 2.3 | last meaningful line 0.2 h ago (5375/5375 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-856398 | slw_st_b_v1 | pregrt_ff_hold | 2.8 | repair_TNS best 20547.1 last 20547.1 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (5386/5386 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | 3_3_place_gp | 0.4 | overflow best 0.2155 last 0.2155 rows 39 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | qc-colls-lec-h1 | qc-colls-lec-h1 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc10 | qc-colls-lec-h2 | qc-colls-lec-h2 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R1_coll_a | relec-r2-R1_coll_a | - | 3.5 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R2_coll_eco | relec-r2-R2_coll_eco | - | 3.5 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R3_coll_hint | relec-r2-R3_coll_hint | - | 3.4 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R8_hc3_pvcca | relec-r2-R8_hc3_pvcca | - | 3.5 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-U3_pv97423966 | relec-r2-U3_pv97423966 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc10 | so_473393_ff_87746 | so_473393_ff_87746 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc10 | so_473393_tt_87746 | so_473393_tt_87746 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 8.6 | last meaningful line 5.1 h ago (48/183 lines) | YOUNG: evidence 7.4 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hg_v1p3__r8c662a835-919135 | kv3_hg_v1p3__r8c662a835 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (526/526 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hg_v1p4-868995 | kv3_hg_v1p4 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (528/528 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hgi_v2__cle0015330-787797 | kv3_hgi_v2 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (242/242 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hgi_v6-774432 | kv3_hgi_v6 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.8938 last 0.8938 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-kv3_hgi_v7-1276815 | kv3_hgi_v7 | 5_1_grt | 4.0 | last meaningful line 1.0 h ago (295/1304 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hgi_v8-2088531 | kv3_hgi_v8 | 5_1_grt | 3.3 | last meaningful line 0.3 h ago (300/1305 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pc_v1__cl4ea58a5c__r8c9cba7ae-750675 | kv3_pc_v1 | 2_4_floorplan_pdn | 0.4 | last meaningful line -0.0 h ago (5/5 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 0.8 | repair_TNS best 827598 last 827598 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_1_grt | 5.0 | last meaningful line 0.5 h ago (1292/2431 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_fw_v1__cl9d029624-56648 | sle_fw_v1 | 5_1_grt | 5.0 | last meaningful line 0.1 h ago (1221/1227 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 4_1_cts | 1.6 | last meaningful line 0.1 h ago (5376/5376 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | 5_1_grt | 5.0 | last meaningful line 0.1 h ago (274/331 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 3_3_place_gp | 0.3 | overflow best 0.6524 last 0.6524 rows 29 | YOUNG: stage 0.2 h < 1 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | 5_1_grt | 4.8 | last meaningful line 0.3 h ago (293/1054 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | dpkit-slw_fw_v3-263804 | slw_fw_v3 | postcts_gate_FF | 4.8 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc2__cl6bcaba89-3858415 | slw_hc2 | postcts_gate_TT | 5.3 | last meaningful line 0.0 h ago (664/664 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3838177 | slw_hc3 | 5_2_route | 5.3 | last meaningful line 0.0 h ago (262/263 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-320042 | slw_st_b_v2 | 5_1_grt | 4.8 | last meaningful line 0.1 h ago (1156/1173 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 4.0 |  | NO-DATA: no log found |  |
| epyc11 | prd-eco_20261124_154417_1016084-i1-3808110 | eco_20261124_154417_1016084-i1 | 5_2_route | 1.6 | last meaningful line 0.0 h ago (261/261 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i1t-2053304 | eco_20261124_190641_1260390-i1t | 5_2_route | 3.3 | drt_violations best 21244 last 21244 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i1t-3010529 | eco_20261124_200101_1087713-i1t | 5_2_route | 2.4 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_204246_1187010-i1t-3648808 | eco_20261124_204246_1187010-i1t | 5_2_route | 1.7 | last meaningful line 0.1 h ago (267/267 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-glue-3558834 | glue | 5_1_grt | 4.3 | last meaningful line 0.1 h ago (895/908 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1__r889141819-836868 | kv3_hg_v1__r889141819 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1__r88f4bfb40-834231 | kv3_hg_v1__r88f4bfb40 | reg_fanout | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-kv3_hg_v1__r8dffc461a-832568 | kv3_hg_v1__r8dffc461a | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1p2-833187 | kv3_hg_v1p2 | synth_odb_v | 0.0 | last meaningful line -0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1p3__r81da466fe-835610 | kv3_hg_v1p3__r81da466fe | reg_fanout | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-kv3_hub_Eo-220828 | kv3_hub_Eo | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Wo-244209 | kv3_hub_Wo | 2_1_floorplan | 0.5 | last meaningful line 0.3 h ago (108/108 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_io_ft-213562 | kv3_io_ft | 5_1_grt | 0.5 | repair_TNS best 50.01 last 50.01 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-655644 | kv3_pc | 2_1_floorplan | 0.2 | repair_Viol best 7558 last 7558 rows 885 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-491987 | sle_hc0 | 4_1_cts | 3.4 | last meaningful line 0.0 h ago (5893/5893 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-1254949 | sle_hc2 | 4_1_cts | 3.0 | last meaningful line 0.2 h ago (5534/5534 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3414126 | sle_hc2 | 5_1_grt | 4.4 | last meaningful line 0.0 h ago (935/947 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__clcc5e3e61-3434617 | sle_hc2 | 5_1_grt | 4.4 | last meaningful line 0.0 h ago (156/156 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 9.7 | drt_violations best 521993 last 521993 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-1186805 | sle_sc_v3 | 5_2_route | 8.8 | drt_violations best 1718 last 1718 rows 6 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-1784944 | sle_st_a_v1 | 5_2_route | 5.4 | drt_violations best 102586 last 102586 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-1826228 | sle_st_a_v1 | 5_2_route | 5.4 | drt_violations best 104942 last 104942 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-1538145 | sle_st_a_v2 | 5_2_route | 5.6 | drt_violations best 135 last 135 rows 22 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-4153401 | sle_stm_v2 | 5_1_grt | 3.9 | last meaningful line 0.0 h ago (1965/2002 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v3-1868496 | sle_stm_v3 | 5_2_route | 5.4 | drt_violations best 87662 last 87662 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-4191516 | slw_fw_v2 | pregrt_ff_hold | 3.8 | repair_TNS best 35084 last 35084 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1101031 | slw_hc3 | 4_1_cts | 3.0 | last meaningful line 0.1 h ago (5227/5227 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3626034 | slw_hc3 | 5_1_grt | 4.2 | last meaningful line 0.0 h ago (1021/1054 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v3-3708441 | slw_sc_v3 | postcts_gate_FF | 4.2 | last meaningful line 0.1 h ago (908/908 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1494307 | slw_st_a_v1 | 5_2_route | 5.7 | drt_violations best 25282 last 25282 rows 2 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-1494646 | slw_st_a_v2 | 5_2_route | 5.7 | drt_violations best 13168 last 13168 rows 3 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i3-451477 | eco_20261123_103136_2028090-i3 | 5_2_route | 3.5 | last meaningful line 0.2 h ago (302/303 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_133404_4027156-i1-3855103 | eco_20261124_133404_4027156-i1 | 5_2_route | 0.9 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-fin-3164922 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 3.2 |  | NO-DATA: no log found |  |
| epyc2 | relec-r2-R7_reform_mapped | relec-r2-R7_reform_mapped | gate_b.ys | 3.2 | last meaningful line 3.0 h ago (94179/94179 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-1850782 | hd_lep0N_w | 5_2_route | 5.3 | drt_violations best 18548 last 18548 rows 2 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-2222980 | sle_fw_v2 | pregrt_ff_hold | 5.1 | repair_TNS best 44718.3 last 44718.3 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 11.0 | drt_violations best 504597 last 504597 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 9.7 | last meaningful line 0.8 h ago (265/266 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | postcts_gate_FF | 5.1 | last meaningful line 0.0 h ago (1795/1795 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | 5_1_grt | 5.3 | last meaningful line 0.3 h ago (1296/2032 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | 5_2_route | 10.9 | drt_violations best 147028 last 147028 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl1bc59e1c-2061343 | slw_hc0 | 5_1_grt | 5.2 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | 5_1_grt | 5.2 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 5_1_grt | 5.3 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-2253577 | slw_hc2 | 5_1_grt | 5.1 | last meaningful line 0.1 h ago (904/917 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 9.5 | last meaningful line 0.8 h ago (270/271 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 11.2 | drt_violations best 400194 last 400194 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | 5_2_route | 9.5 | last meaningful line 0.3 h ago (264/265 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | 5_2_route | 11.2 | drt_violations best 126854 last 126854 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | postcts_gate_FF | 5.1 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i3t-3392092 | eco_20261123_171023_3055226-i3t | 5_2_route | 4.4 | drt_violations best 835 last 835 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_145005_2036075-i2t-1611651 | eco_20261124_145005_2036075-i2t | 5_2_route | 2.8 | drt_violations best 5275 last 5275 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i1-3895101 | eco_20261124_175441_992552-i1 | 5_2_route | 1.4 | last meaningful line 0.2 h ago (260/261 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i1t-1220925 | eco_20261124_192157_3493836-i1t | 5_2_route | 3.1 | last meaningful line 0.3 h ago (274/275 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_201304_2675397-i1-2517921 | eco_20261124_201304_2675397-i1 | 5_2_route | 2.2 | last meaningful line 0.3 h ago (269/270 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_1_grt | 6.4 | last meaningful line 0.2 h ago (248/1253 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 5_1_grt | 6.4 | last meaningful line 0.1 h ago (1017/1030 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 5_1_grt | 6.4 | last meaningful line 0.2 h ago (956/969 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 5_1_grt | 6.4 | last meaningful line 0.5 h ago (274/902 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | postcts_gate_FF | 6.4 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | tt_setup_measure_grt | 6.4 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | postcts_gate_FF | 6.3 | last meaningful line 0.1 h ago (2134/2134 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-4063882 | sle_st_a_v2 | 5_2_route | 6.4 | drt_violations best 125 last 125 rows 24 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 5_1_grt | 6.4 | last meaningful line 0.2 h ago (2092/2105 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 5_1_grt | 6.4 | last meaningful line 0.1 h ago (1147/1160 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | 5_1_grt | 6.4 | last meaningful line 0.1 h ago (2167/2205 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | 5_2_route | 6.4 | last meaningful line 0.2 h ago (260/260 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l0__cl7a55c676-4020210 | sle_su_l0 | 5_2_route | 6.4 | drt_violations best 27974 last 27974 rows 3 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_1_grt | 6.4 | last meaningful line 0.2 h ago (1282/1347 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 5_1_grt | 6.4 | last meaningful line 0.2 h ago (942/955 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 5_1_grt | 6.4 | last meaningful line 0.1 h ago (287/344 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 5_1_grt | 6.4 | last meaningful line 0.2 h ago (938/951 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | 5_2_route | 9.7 | last meaningful line 0.2 h ago (284/285 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | postcts_gate_TT | 6.4 | last meaningful line 0.1 h ago (373/373 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3909116 | slw_hc3 | 5_2_route | 6.4 | last meaningful line 0.1 h ago (129/129 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-3949912 | slw_hc3 | 5_2_route | 6.4 | last meaningful line 0.1 h ago (129/129 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | postcts_gate_FF | 6.3 | last meaningful line 0.0 h ago (2172/2172 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 6.3 | last meaningful line 0.1 h ago (266/266 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | 5_2_route | 6.4 | drt_violations best 149425 last 149425 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 5_2_route | 6.4 | drt_violations best 19970 last 19970 rows 3 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-3848540 | slw_su_l0 | 6_report | 6.4 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 6.4 | drt_violations best 68683 last 68683 rows 3 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3t-2289287 | eco_20261123_164145_1995767-i3t | 5_2_route | 3.8 | last meaningful line 0.3 h ago (299/300 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261124_211939_3874698-i1-235182 | eco_20261124_211939_3874698-i1 | 5_2_route | 1.1 | last meaningful line 0.1 h ago (258/259 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 3.3 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R1b_coll_old | relec-r2-R1b_coll_old | - | 3.2 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R4_coll_guard | relec-r2-R4_coll_guard | - | 3.2 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R9_hc3_d5fde | relec-r2-R9_hc3_d5fde | - | 3.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | postcts_gate_TT | 3.1 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hg_v1p3__r838481cd7-1789131 | kv3_hg_v1p3__r838481cd7 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (448/448 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-1421312 | kv3_pc_v1 | 2_1_floorplan | 0.2 | repair_Viol best 8511 last 8511 rows 1015 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-kv3_pc_v1__cl4ea58a5c__r877307f5d-1422816 | kv3_pc_v1 | 2_1_floorplan | 0.2 | repair_Viol best 8517 last 8517 rows 1041 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-kv3_pc_v1__cl4ea58a5c__r8afe1e027-1470772 | kv3_pc_v1 | 2_1_floorplan | 0.2 | repair_Viol best 8514 last 8514 rows 18 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-748558 | kv3_pc_v1 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | 4_1_cts | 2.7 | last meaningful line 0.2 h ago (11096/11096 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | pregrt_ff_hold | 3.3 | repair_TNS best 117272 last 117272 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-551472 | slw_fw_v1 | pregrt_ff_hold | 3.5 | repair_TNS best 40105.9 last 40105.9 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-slw_fw_v2__cl8537f156-601723 | slw_fw_v2 | pregrt_ff_hold | 3.4 | repair_Violations best 115 last 115 rows 13 | YOUNG: evidence 1.4 h < 2.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l6_wb51d05-853896 | qfd_qc_su_lane_w_l6_wb51d05 | sta_FF | 8.5 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l7_wd4f14d-862251 | qfd_qc_su_lane_w_l7_wd4f14d | sta_FF | 8.5 | last meaningful line 0.1 h ago (25/25 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-1780870-30140 | 1780870 | signoff | 0.0 | last meaningful line 0.0 h ago (3/3 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-1814577-31530 | 1814577 | - | 7.9 |  | NO-DATA: no log found |  |
| epyc9 | otc-1893022-28497 | 1893022 | signoff | 0.0 | last meaningful line 0.0 h ago (3/3 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-274901-18541 | 274901 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-325480-18988 | 325480 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-327815-30892 | 327815 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-329709-29264 | 329709 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261123_224216_149959-i3-3801930 | eco_20261123_224216_149959-i3 | 5_1_grt | 1.2 | last meaningful line 0.6 h ago (237/1345 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | so_1884197_ff_10282 | so_1884197_ff_10282 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | so_1884197_tt_10282 | so_1884197_tt_10282 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | so_1888093_ff_11093 | so_1888093_ff_11093 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | so_1888093_tt_11093 | so_1888093_tt_11093 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel1 | dpkit-coll_core-3813096 | coll_core | 5_1_grt | 4.7 | last meaningful line 0.1 h ago (151/151 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 5_1_grt | 7.1 | last meaningful line 0.2 h ago (156/156 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-native59-2938294 | native59 | 3_4_place_resized | 2.3 | last meaningful line 0.1 h ago (335/335 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | postcts_gate_TT | 9.7 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v3-1442734 | sle_fw_v3 | pregrt_ff_hold | 3.4 | repair_TNS best 34138.8 last 34138.8 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | pregrt_ff_hold | 5.4 | repair_TNS best 82649.3 last 82649.3 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-3662089 | sle_sc_v1 | tt_setup_repair_grt | 4.7 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (5443/5443 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 5_1_grt | 3.4 | last meaningful line 0.0 h ago (172/172 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_1_grt | 1.6 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | 5_2_route | 7.8 | last meaningful line 0.5 h ago (278/279 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | postcts_gate_TT | 9.7 | last meaningful line 0.1 h ago (859/859 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v3-1399930 | slw_fw_v3 | pregrt_ff_hold | 3.5 | repair_TNS best 22203 last 22203 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 3_3_place_gp | 0.2 | overflow best 0.672 last 0.672 rows 30 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2360221 | slw_hc2 | 4_1_cts | 2.7 | last meaningful line 0.1 h ago (5129/5129 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (4944/4944 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2160450 | slw_hc3 | 4_1_cts | 2.9 | last meaningful line 0.3 h ago (4828/4828 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3890746 | slw_sc_v1 | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (5649/5649 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 5_1_grt | 5.4 | last meaningful line 0.3 h ago (144/144 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | 5_2_route | 9.6 | last meaningful line 0.0 h ago (254/254 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1e5219ea-4177722 | slw_su_l0 | 5_1_grt | 1.5 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 3.5 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 3.5 |  | NO-DATA: no log found |  |
| intel1 | otc-3854277-21865 | 3854277 | - | 7.5 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261123_191853_2879776-i2t-2852283 | eco_20261123_191853_2879776-i2t | 5_2_route | 5.4 | drt_violations best 3711 last 3711 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_hroot-2490806 | kv3_hroot | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_C-524420 | kv3_hub_C | 3_3_place_gp | 4.9 | overflow best 0.2008 last 0.2008 rows 76 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-kv3_hub_Wi-487140 | kv3_hub_Wi | 3_5_place_dp | 4.9 | last meaningful line 0.5 h ago (126/126 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-1909702 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 3039 last 3039 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 5_1_grt | 5.1 | last meaningful line 0.2 h ago (251/1256 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-slw_stm_v1__cle34a73c3-4063338 | slw_stm_v1 | 5_1_grt | 3.5 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 17.4 | drt_violations best 18158 last 18158 rows 13 | before-window best 52270, window best 18158 | PROGRESS: drt_violations improved 65.3 % in window |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | 5_1_grt | 5.0 | repair_TNS best 0 last 0 rows 10 | PROGRESS: repair_TNS reached 0 |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | 5_1_grt | 4.8 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | pregrt_ff_hold | 7.6 | repair_Violations best 485 last 487 rows 143 | before-window best 50245, window best 485 | PROGRESS: repair_Violations improved 99.0 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 9.8 | drt_violations best 1794 last 1794 rows 16 | before-window best 28705, window best 1794 | PROGRESS: drt_violations improved 93.8 % in window |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-1772768 | sle_hc0 | pregrt_ff_hold | 5.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3657462 | slw_stm_v2 | 5_1_grt | 4.2 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 36.8 | drt_violations best 11554 last 11554 rows 16 | before-window best 17065, window best 11554 | PROGRESS: drt_violations improved 32.3 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 30.1 | drt_violations best 9091 last 9091 rows 16 | before-window best 20899, window best 9091 | PROGRESS: drt_violations improved 56.5 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 14.9 | drt_violations best 78233 last 78233 rows 3 | before-window best 490378, window best 78233 | PROGRESS: drt_violations improved 84.0 % in window |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 15.1 | drt_violations best 74091 last 74091 rows 4 | before-window best 407677, window best 74091 | PROGRESS: drt_violations improved 81.8 % in window |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | 5_1_grt | 5.2 | repair_TNS best 0 last 0 rows 22 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_hc1__cl22c1ff36__pve230954c-3918742 | sle_hc1 | 5_1_grt | 6.4 | repair_TNS best 0 last 0 rows 10 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 5_1_grt | 6.4 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-1010348 | sle_fw_v1 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_fw_v1__clf58b4dfb-733846 | sle_fw_v1 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-667540 | sle_hc1 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_hgi_v4-3072149 | kv3_hgi_v4 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3458150 | sle_hc2 | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3463031 | slw_hc1 | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 5_1_grt | 5.4 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-coll_ftm-2194683 | coll_ftm | 5_1_grt | 0.7 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 13.7 | drt_violations best 2 last 47 rows 54 | before-window best 6, window best 2 | PROGRESS: drt_violations improved 66.7 % in window |  |
