# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 14:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 6, 'UNSIGNABLE': 1, 'GRT-LABEL': 5, 'YOUNG': 176, 'NO-DATA': 24, 'PROGRESS': 29}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | pregrt_ff_hold | 6.0 | repair_TNS best 59596.4 last 59596.4 rows 1 | before-window best 59596.4, window best 59596.4 | NO-PROGRESS: repair_TNS best 59596.4 vs 59596.4 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| intel1 | dpkit-cbf_q00__cl1b5a6458-4114232 | cbf_q00 | 5_1_grt | 4.7 | grt rounds 2 overflow 5:6528 -> 10:6453 | UNSIGNABLE: GRT overflow flat: overflow 6528 at iteration 5 -> 6453 at iteration 10: flat fo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2973163 | slw_hc3 | pregrt_ff_hold | 5.5 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 22.7 | last meaningful line 11.9 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 11.9 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1797391-24144 | 1797391 | flow3 | 9.6 | last meaningful line 9.2 h ago (208/209 lines) | NO-PROGRESS: no new non-iteration log line for 9.2 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 26.4 | last meaningful line 11.9 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 11.9 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-60615 | sle_st_b_v2 | pregrt_ff_hold | 5.4 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | CANCELLED |
| epyc10 | dpkit-kv3_hg_v3-1126078 | kv3_hg_v3 | 5_1_grt | 5.8 | grt rounds 2 overflow 5:48439 -> 10:42500 | GRT-LABEL: DESIGN-FAIL: overflow 42500 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v2n-1048434 | kv3_pv_v2n | 5_1_grt | 5.9 | grt rounds 2 overflow 5:64147 -> 10:49031 | GRT-LABEL: DESIGN-FAIL: overflow 49031 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v7e-1156836 | kv3_pv_v7e | 5_1_grt | 5.8 | grt rounds 2 overflow 5:101255 -> 10:76491 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc11 | dpkit-kv3_pv_v4ne-3869988 | kv3_pv_v4ne | 5_1_grt | 5.6 | grt rounds 1 overflow 5:114063 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pv_v3ne-3760907 | kv3_pv_v3ne | 5_1_grt | 7.8 | grt rounds 1 overflow 5:47095 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 5.8 | last meaningful line 4.5 h ago (48/61 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | 5_2_route | 2.7 | last meaningful line 0.2 h ago (253/254 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1479488 | hd_spn | 5_2_route | 2.5 | last meaningful line 0.2 h ago (256/257 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-579995 | kv3_hub_Wo | 2_1_floorplan | 0.2 | last meaningful line 0.1 h ago (108/108 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r8b421e514-312614 | kv3_pc | 3_1_place_gp_skip_io | 0.4 | overflow best 0.874 last 0.8871 rows 5 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r884969661-245905 | kv3_pc_v1 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.1 h ago (56/56 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl7f648944__r8422a4b86-811055 | kv3_pc_v1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (528/528 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (9089/9089 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-3644344 | kv3_pv_v12 | 3_4_place_resized | 1.0 | last meaningful line 0.0 h ago (343/343 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-3757611 | kv3_pv_v3 | 3_3_place_gp | 0.9 | overflow best 0.4353 last 0.4353 rows 5 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v6-908877 | kv3_pv_v6 | 5_1_grt | 6.0 | last meaningful line 0.2 h ago (265/1269 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_1_grt | 5.0 | last meaningful line 0.2 h ago (250/1254 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-660000 | sle_hc0 | 4_1_cts | 3.2 | last meaningful line 0.5 h ago (5832/5832 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | 4_1_cts | 1.8 | last meaningful line 0.2 h ago (5023/5023 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | 4_1_cts | 2.2 | last meaningful line 0.2 h ago (5736/5736 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1583204 | sle_st_b_v1 | 4_1_cts | 2.5 | last meaningful line 0.1 h ago (5614/5614 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | pregrt_ff_hold | 2.8 | repair_TNS best 20636.6 last 20636.6 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2793057 | sle_stm_v1 | postcts_gate_FF | 4.5 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | pregrt_ff_hold | 3.9 | repair_TNS best 266902 last 266902 rows 1 | YOUNG: evidence 1.5 h < 2.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | pregrt_ff_hold | 3.9 | repair_TNS best 269355 last 269355 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | pregrt_ff_hold | 4.0 | repair_TNS best 15024.3 last 15024.3 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | 4_1_cts | 2.6 | last meaningful line 0.2 h ago (5413/5413 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (5415/5415 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_stm_v1__cle34a73c3-4063338 | slw_stm_v1 | 5_1_grt | 3.7 | last meaningful line 0.1 h ago (985/1002 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | otc-702138-28635 | 702138 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | otc-703975-17959 | 703975 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | otc-879195-32457 | 879195 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | otc-901577-23707 | 901577 | signoff | 0.0 | last meaningful line 0.0 h ago (3/3 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | qc-colls-lec-h1 | qc-colls-lec-h1 | - | 1.3 |  | NO-DATA: no log found |  |
| epyc10 | qc-colls-lec-h2 | qc-colls-lec-h2 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R1_coll_a | relec-r2-R1_coll_a | - | 3.7 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R2_coll_eco | relec-r2-R2_coll_eco | - | 3.7 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R3_coll_hint | relec-r2-R3_coll_hint | - | 3.7 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R8_hc3_pvcca | relec-r2-R8_hc3_pvcca | - | 3.7 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-U3_pv97423966 | relec-r2-U3_pv97423966 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-hd_ctl-1357698 | hd_ctl | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (416/416 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-hd_host_w-1353951 | hd_host_w | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (719/719 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hg_v1p3__r8c662a835-919135 | kv3_hg_v1p3__r8c662a835 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.1501 last 0.1501 rows 40 | YOUNG: stage 0.2 h < 1 h |  |
| epyc11 | dpkit-kv3_hg_v1p4-868995 | kv3_hg_v1p4 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (60/60 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hgi_v2__cle0015330-787797 | kv3_hgi_v2 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hgi_v6-774432 | kv3_hgi_v6 | 3_3_place_gp | 0.6 | overflow best 0.1978 last 0.1978 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-kv3_hgi_v7-1276815 | kv3_hgi_v7 | 5_1_grt | 4.2 | last meaningful line 1.2 h ago (295/1305 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hgi_v8-2088531 | kv3_hgi_v8 | 5_1_grt | 3.5 | last meaningful line 0.5 h ago (300/1306 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pc_v1__cl4ea58a5c__r8c9cba7ae-750675 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.8562 last 0.9011 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 1.1 | repair_TNS best 827598 last 827598 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc11 | dpkit-sle_fw_v1__cl9d029624-56648 | sle_fw_v1 | 5_1_grt | 5.2 | last meaningful line 0.1 h ago (1221/1256 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (5527/5527 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 4_1_cts | 1.8 | last meaningful line 0.0 h ago (5403/5403 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | 5_1_grt | 5.3 | last meaningful line 0.3 h ago (274/924 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 3_3_place_gp | 0.5 | overflow best 0.3181 last 0.3967 rows 96 | YOUNG: stage 0.4 h < 1 h |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | 5_1_grt | 5.2 | last meaningful line 0.2 h ago (1087/1100 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_fw_v3-263804 | slw_fw_v3 | postcts_gate_FF | 5.1 | last meaningful line 0.0 h ago (1765/1765 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc2__cl6bcaba89-3858415 | slw_hc2 | postcts_gate_TT | 5.6 | last meaningful line 0.1 h ago (730/730 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3838177 | slw_hc3 | 5_2_route | 5.6 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | 5_1_grt | 5.0 | last meaningful line 0.2 h ago (1107/1120 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-320042 | slw_st_b_v2 | tt_setup_repair_grt | 5.0 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 4.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-1398324-27795 | 1398324 | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (232/232 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_154417_1016084-i1-3808110 | eco_20261124_154417_1016084-i1 | 5_2_route | 1.8 | last meaningful line 0.3 h ago (262/263 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i1t-2053304 | eco_20261124_190641_1260390-i1t | 5_2_route | 3.6 | drt_violations best 21244 last 21244 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i1t-3010529 | eco_20261124_200101_1087713-i1t | 5_2_route | 2.7 | last meaningful line 0.1 h ago (282/283 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_204246_1187010-i1t-3648808 | eco_20261124_204246_1187010-i1t | 5_2_route | 2.0 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1__r889141819-836868 | kv3_hg_v1__r889141819 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (530/530 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1__r88f4bfb40-834231 | kv3_hg_v1__r88f4bfb40 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (530/530 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1__r8dffc461a-832568 | kv3_hg_v1__r8dffc461a | 3_1_place_gp_skip_io | 0.3 | last meaningful line -0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1p2-833187 | kv3_hg_v1p2 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (529/529 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1p3__r81da466fe-835610 | kv3_hg_v1p3__r81da466fe | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (529/529 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 5_1_grt | 7.8 | last meaningful line 0.0 h ago (169/169 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_io_ft-213562 | kv3_io_ft | 5_2_route | 0.7 | last meaningful line 0.0 h ago (212/212 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-655644 | kv3_pc | 3_1_place_gp_skip_io | 0.4 | overflow best 0.826 last 0.826 rows 7 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-491987 | sle_hc0 | pregrt_ff_hold | 3.7 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-1254949 | sle_hc2 | 4_1_cts | 3.2 | last meaningful line 0.2 h ago (5536/5536 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3414126 | sle_hc2 | 5_1_grt | 4.6 | last meaningful line 0.1 h ago (983/996 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__clcc5e3e61-3434617 | sle_hc2 | 5_1_grt | 4.6 | last meaningful line 0.2 h ago (286/864 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 10.0 | drt_violations best 521993 last 521993 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-1186805 | sle_sc_v3 | 5_2_route | 9.0 | drt_violations best 1247 last 1247 rows 10 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-1784944 | sle_st_a_v1 | 5_2_route | 5.7 | drt_violations best 17291 last 17291 rows 2 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-1826228 | sle_st_a_v1 | 5_2_route | 5.7 | drt_violations best 16955 last 16955 rows 2 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-1538145 | sle_st_a_v2 | 5_2_route | 5.9 | drt_violations best 102 last 138 rows 26 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-4153401 | sle_stm_v2 | postcts_gate_TT | 4.1 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v3-1868496 | sle_stm_v3 | 5_2_route | 5.6 | drt_violations best 87662 last 87662 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-4191516 | slw_fw_v2 | pregrt_ff_hold | 4.1 | repair_TNS best 35084 last 35084 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1101031 | slw_hc3 | 4_1_cts | 3.3 | last meaningful line 0.1 h ago (5351/5351 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3626034 | slw_hc3 | postcts_gate_FF | 4.5 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v3-3708441 | slw_sc_v3 | postcts_gate_FF | 4.4 | last meaningful line -0.0 h ago (48640/48640 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1494307 | slw_st_a_v1 | 5_2_route | 5.9 | drt_violations best 17446 last 17446 rows 3 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-1494646 | slw_st_a_v2 | 5_2_route | 5.9 | drt_violations best 1342 last 1342 rows 6 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3657462 | slw_stm_v2 | 5_1_grt | 4.4 | last meaningful line 0.0 h ago (1008/1008 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_133404_4027156-i1-3855103 | eco_20261124_133404_4027156-i1 | 5_2_route | 1.2 | last meaningful line 0.0 h ago (255/256 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 3.4 |  | NO-DATA: no log found |  |
| epyc2 | relec-r2-R7_reform_mapped | relec-r2-R7_reform_mapped | gate_b.ys | 3.4 | last meaningful line 3.2 h ago (94179/94179 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | so_1245389_ff_13279 | so_1245389_ff_13279 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | so_1245389_tt_13279 | so_1245389_tt_13279 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-1850782 | hd_lep0N_w | 5_2_route | 5.6 | drt_violations best 18548 last 18548 rows 2 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-2222980 | sle_fw_v2 | 5_1_grt | 5.4 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 11.3 | drt_violations best 504597 last 504597 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 9.9 | last meaningful line 0.5 h ago (267/268 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | postcts_gate_FF | 5.3 | last meaningful line -0.0 h ago (14830/14830 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | 5_1_grt | 5.6 | last meaningful line 0.0 h ago (2063/2067 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | 5_2_route | 11.1 | drt_violations best 147028 last 147028 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl1bc59e1c-2061343 | slw_hc0 | 5_1_grt | 5.5 | last meaningful line 0.2 h ago (137/137 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | 5_1_grt | 5.4 | last meaningful line 0.2 h ago (138/138 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 5_1_grt | 5.5 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-2253577 | slw_hc2 | 5_1_grt | 5.4 | last meaningful line 0.1 h ago (950/963 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 9.7 | last meaningful line 0.5 h ago (272/273 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 11.4 | drt_violations best 400194 last 400194 rows 1 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | 5_2_route | 9.8 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | 5_2_route | 11.5 | drt_violations best 126854 last 126854 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | postcts_gate_TT | 5.4 | last meaningful line 0.1 h ago (699/699 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i3t-3392092 | eco_20261123_171023_3055226-i3t | 5_2_route | 4.7 | drt_violations best 835 last 835 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_145005_2036075-i2t-1611651 | eco_20261124_145005_2036075-i2t | 5_2_route | 3.1 | drt_violations best 5275 last 5275 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i1-3895101 | eco_20261124_175441_992552-i1 | 5_2_route | 1.6 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i1t-1220925 | eco_20261124_192157_3493836-i1t | 5_2_route | 3.3 | drt_violations best 5844 last 5844 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_201304_2675397-i1-2517921 | eco_20261124_201304_2675397-i1 | 5_2_route | 2.5 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_1_grt | 6.6 | repair_Remaining best 194337 last 194337 rows 204 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 5_1_grt | 6.6 | last meaningful line 0.2 h ago (1002/1015 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl22c1ff36__pve230954c-3918742 | sle_hc1 | 5_1_grt | 6.6 | last meaningful line 0.2 h ago (979/992 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 5_1_grt | 6.6 | last meaningful line 0.2 h ago (933/946 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | postcts_gate_TT | 6.7 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | postcts_gate_FF | 6.7 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | postcts_gate_FF | 6.6 | last meaningful line -0.0 h ago (47460/47460 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-4063882 | sle_st_a_v2 | 5_2_route | 6.6 | drt_violations best 107 last 107 rows 29 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 5_1_grt | 6.6 | last meaningful line 0.1 h ago (1193/1210 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | 5_1_grt | 6.6 | last meaningful line 0.2 h ago (2213/2230 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | 5_2_route | 6.6 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l0__cl7a55c676-4020210 | sle_su_l0 | 5_2_route | 6.6 | drt_violations best 354 last 354 rows 6 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_1_grt | 6.6 | last meaningful line 0.4 h ago (1282/2412 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 5_1_grt | 6.6 | last meaningful line 0.1 h ago (1035/1041 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 5_1_grt | 6.6 | last meaningful line 0.3 h ago (287/970 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 5_1_grt | 6.6 | last meaningful line 0.1 h ago (984/997 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | 5_2_route | 9.9 | last meaningful line 0.2 h ago (286/287 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | postcts_gate_TT | 6.7 | last meaningful line 0.1 h ago (720/720 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3909116 | slw_hc3 | 5_2_route | 6.7 | last meaningful line 0.0 h ago (257/258 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-3949912 | slw_hc3 | 5_2_route | 6.6 | last meaningful line 0.0 h ago (259/259 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | postcts_gate_FF | 6.6 | last meaningful line -0.0 h ago (6754/6754 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 6.5 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | 5_2_route | 6.6 | drt_violations best 149425 last 149425 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 5_2_route | 6.6 | drt_violations best 1984 last 1984 rows 5 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 5_1_grt | 6.6 | last meaningful line 0.2 h ago (1142/1155 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 6.6 | drt_violations best 68683 last 68683 rows 3 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3t-2289287 | eco_20261123_164145_1995767-i3t | 5_2_route | 4.1 | drt_violations best 35664 last 35664 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261124_211939_3874698-i1-235182 | eco_20261124_211939_3874698-i1 | 5_2_route | 1.4 | drt_violations best 37 last 37 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 3.5 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R1b_coll_old | relec-r2-R1b_coll_old | - | 3.4 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R4_coll_guard | relec-r2-R4_coll_guard | - | 3.5 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R9_hc3_d5fde | relec-r2-R9_hc3_d5fde | - | 3.4 |  | NO-DATA: no log found |  |
| epyc8 | so_3669409_ff_99364 | so_3669409_ff_99364 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc8 | so_3669409_tt_99364 | so_3669409_tt_99364 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | postcts_gate_FF | 3.3 | last meaningful line 0.0 h ago (861/861 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hg_v1p3__r838481cd7-1789131 | kv3_hg_v1p3__r838481cd7 | 2_4_floorplan_pdn | 0.3 | last meaningful line -0.0 h ago (537/537 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-1421312 | kv3_pc_v1 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.0 h ago (66/66 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v1__cl4ea58a5c__r877307f5d-1422816 | kv3_pc_v1 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.0 h ago (62/62 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v1__cl4ea58a5c__r8afe1e027-1470772 | kv3_pc_v1 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-748558 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.7 | overflow best 0.5418 last 0.5418 rows 33 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | 4_1_cts | 3.0 | last meaningful line 0.1 h ago (11123/11123 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__clf58b4dfb-733846 | sle_fw_v1 | pregrt_ff_hold | 3.6 | repair_TNS best 42786.7 last 42786.7 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | pregrt_ff_hold | 3.7 | repair_TNS best 277372 last 277372 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc9 | dpkit-slw_fw_v2__cl8537f156-601723 | slw_fw_v2 | 5_1_grt | 3.7 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-1780870-30140 | 1780870 | signoff | 0.3 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | otc-1814577-31530 | 1814577 | - | 8.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-1893022-28497 | 1893022 | signoff | 0.3 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | otc-2115495-15878 | 2115495 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-2119148-18648 | 2119148 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-2119788-20319 | 2119788 | asbuilt.yosys | 0.1 | last meaningful line -0.0 h ago (135320/135320 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-2126591-20932 | 2126591 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-2136971-27474 | 2136971 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-2170026-14801 | 2170026 | asbuilt.yosys | 0.1 | last meaningful line 0.0 h ago (135318/135318 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i3-3801930 | eco_20261123_224216_149959-i3 | 5_2_route | 1.4 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-coll_core-3813096 | coll_core | 5_1_grt | 4.9 | last meaningful line 0.0 h ago (260/262 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v4-3072149 | kv3_hgi_v4 | pregrt_ff_hold | 2.5 | repair_TNS best 3199.42 last 3199.42 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 5_1_grt | 7.4 | last meaningful line 0.3 h ago (156/156 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-native59-2938294 | native59 | 3_5_place_dp | 2.6 | last meaningful line 0.0 h ago (65/65 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | postcts_gate_FF | 10.0 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v3-1442734 | sle_fw_v3 | pregrt_ff_hold | 3.7 | repair_TNS best 34138.8 last 34138.8 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 5_1_grt | 5.6 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-3662089 | sle_sc_v1 | tt_setup_measure_grt | 5.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 4_1_cts | 2.0 | last meaningful line 0.1 h ago (5485/5485 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 5_1_grt | 3.7 | repair_Remaining best 272425 last 272425 rows 105 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_1_grt | 1.9 | last meaningful line 0.2 h ago (258/1267 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | 5_2_route | 8.0 | last meaningful line 0.7 h ago (278/279 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | postcts_gate_TT | 9.9 | last meaningful line 0.2 h ago (859/859 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v3-1399930 | slw_fw_v3 | 5_1_grt | 3.7 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 3_4_place_resized | 0.5 | last meaningful line 0.0 h ago (429/429 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2360221 | slw_hc2 | 4_1_cts | 3.0 | last meaningful line 0.0 h ago (5156/5156 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (4972/4972 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2160450 | slw_hc3 | 4_1_cts | 3.1 | last meaningful line 0.1 h ago (4831/4831 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3890746 | slw_sc_v1 | 4_1_cts | 2.0 | last meaningful line 0.0 h ago (5694/5694 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 5_1_grt | 5.6 | last meaningful line 0.1 h ago (281/343 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 3_3_place_gp | 0.2 | overflow best 0.7747 last 0.7747 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | 5_2_route | 9.9 | last meaningful line 0.2 h ago (261/261 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1e5219ea-4177722 | slw_su_l0 | 5_1_grt | 1.8 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 3.8 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 3.8 |  | NO-DATA: no log found |  |
| intel1 | otc-3854277-21865 | 3854277 | - | 7.7 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261123_191853_2879776-i2t-2852283 | eco_20261123_191853_2879776-i2t | 5_2_route | 5.6 | drt_violations best 3711 last 3711 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2194683 | coll_ftm | 5_2_route | 1.0 | last meaningful line 0.0 h ago (225/225 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 5_1_grt | 5.3 | last meaningful line 0.2 h ago (1283/2088 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | so_3871975_ff_38125 | so_3871975_ff_38125 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_3871975_tt_38125 | so_3871975_tt_38125 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | pregrt_ff_hold | 6.1 | repair_Violations best 1124 last 1127 rows 59 | before-window best 50443, window best 1124 | PROGRESS: repair_Violations improved 97.8 % in window |  |
| epyc10 | dpkit-sle_fw_v1__clf58b4dfb-461721 | sle_fw_v1 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_st_b_v2__clfde1249e-689859 | sle_st_b_v2 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-856398 | slw_st_b_v1 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 8.9 | last meaningful line 5.3 h ago (48/184 lines) | PROGRESS: log still growing |  |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_1_grt | 5.2 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS reached 0 |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 17.7 | drt_violations best 16673 last 16673 rows 14 | before-window best 52270, window best 16673 | PROGRESS: drt_violations improved 68.1 % in window |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | 5_1_grt | 5.1 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-glue-3558834 | glue | 5_1_grt | 4.5 | repair_TNS best 0 last 0 rows 20 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 10.1 | drt_violations best 1794 last 1794 rows 16 | before-window best 22046, window best 1794 | PROGRESS: drt_violations improved 91.9 % in window |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-1772768 | sle_hc0 | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | prd-eco_20261123_103136_2028090-i3-451477 | eco_20261123_103136_2028090-i3 | 5_2_route | 3.7 | drt_violations best 0 last 0 rows 1 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 37.1 | drt_violations best 10129 last 10129 rows 17 | before-window best 14975, window best 10129 | PROGRESS: drt_violations improved 32.4 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 30.4 | drt_violations best 9091 last 9091 rows 16 | before-window best 20899, window best 9091 | PROGRESS: drt_violations improved 56.5 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 15.1 | drt_violations best 78233 last 78233 rows 3 | before-window best 490378, window best 78233 | PROGRESS: drt_violations improved 84.0 % in window |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 15.3 | drt_violations best 74091 last 74091 rows 4 | before-window best 407677, window best 74091 | PROGRESS: drt_violations improved 81.8 % in window |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | 5_1_grt | 5.5 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 5_1_grt | 6.6 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 5_1_grt | 6.6 | repair_TNS best 0 last 0 rows 19 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | pregrt_ff_hold | 3.5 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-1010348 | sle_fw_v1 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-667540 | sle_hc1 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-551472 | slw_fw_v1 | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3458150 | sle_hc2 | pregrt_ff_hold | 5.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3463031 | slw_hc1 | pregrt_ff_hold | 5.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 5_1_grt | 5.6 | repair_TNS best 0 last 0 rows 16 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | pregrt_ff_hold | 5.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 13.9 | drt_violations best 2 last 47 rows 54 | before-window best 6, window best 2 | PROGRESS: drt_violations improved 66.7 % in window |  |
