# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 11:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 6, 'GRT-LABEL': 2, 'YOUNG': 179, 'NO-DATA': 25, 'PROGRESS': 23}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| intel1 | dpkit-native59-1320092 | native59 | pregrt_ff_hold | 7.0 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1387403 | slw_hc0 | pregrt_ff_hold | 6.9 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| intel1 | dpkit-slw_hc1__cl3449ea95-1389354 | slw_hc1 | pregrt_ff_hold | 6.9 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 19.7 | last meaningful line 8.9 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 8.9 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1797391-24144 | 1797391 | flow3 | 6.6 | last meaningful line 6.2 h ago (208/209 lines) | NO-PROGRESS: no new non-iteration log line for 6.2 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 23.4 | last meaningful line 8.9 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 8.9 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3602061 | sle_su_l1 | 5_1_grt | 1.5 | grt rounds 2 overflow 5:6669 -> 10:2241 | GRT-LABEL: DESIGN-FAIL: overflow 2241 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_pv_v3ne-3760907 | kv3_pv_v3ne | 5_1_grt | 4.8 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-kv3-hgi-v2--cl2862d491-grt-823705 | kv3-hgi-v2--cl2862d491-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 2.8 | last meaningful line 1.5 h ago (48/53 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | pregrt_ff_hold | 3.1 | repair_TNS best 468304 last 468304 rows 1 | YOUNG: evidence 1.5 h < 2.5 h |  |
| epyc10 | dpkit-kv3_hg_v3-1126078 | kv3_hg_v3 | pregrt_ff_hold | 2.8 | repair_TNS best 29851.2 last 29851.2 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc10 | dpkit-kv3_hgi_v5-331504 | kv3_hgi_v5 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5682/5682 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | pregrt_ff_hold | 3.0 | repair_TNS best 149411 last 149411 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc10 | dpkit-kv3_pv_v2-1075302 | kv3_pv_v2 | pregrt_ff_hold | 2.8 | repair_TNS best 37107.5 last 37107.5 rows 1 | YOUNG: evidence 1.4 h < 2.5 h |  |
| epyc10 | dpkit-kv3_pv_v2n-1048434 | kv3_pv_v2n | pregrt_ff_hold | 2.9 | repair_TNS best 46298.2 last 46298.2 rows 1 | YOUNG: evidence 1.5 h < 2.5 h |  |
| epyc10 | dpkit-kv3_pv_v4-680976 | kv3_pv_v4 | pregrt_ff_hold | 3.2 | repair_Violations best 702 last 939 rows 35 | YOUNG: evidence 2.2 h < 2.5 h |  |
| epyc10 | dpkit-kv3_pv_v4e-1194094 | kv3_pv_v4e | 5_1_grt | 2.7 | last meaningful line 0.3 h ago (271/1275 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v5e-402621 | kv3_pv_v5e | pregrt_ff_hold | 3.4 | repair_TNS best 845383 last 845383 rows 1 | YOUNG: evidence 1.5 h < 2.5 h |  |
| epyc10 | dpkit-kv3_pv_v5n-698511 | kv3_pv_v5n | pregrt_ff_hold | 3.2 | repair_TNS best 32592.1 last 32592.1 rows 1 | YOUNG: evidence 1.4 h < 2.5 h |  |
| epyc10 | dpkit-kv3_pv_v6-908877 | kv3_pv_v6 | pregrt_ff_hold | 3.0 | repair_TNS best 26222.1 last 26222.1 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v6e-760052 | kv3_pv_v6e | 5_1_grt | 3.1 | last meaningful line 1.3 h ago (268/1278 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v6n-1030440 | kv3_pv_v6n | pregrt_ff_hold | 2.9 | repair_TNS best 40271.4 last 40271.4 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc10 | dpkit-kv3_pv_v6ne-1050153 | kv3_pv_v6ne | 5_1_grt | 2.9 | last meaningful line 1.0 h ago (272/1280 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v7-1199684 | kv3_pv_v7 | pregrt_ff_hold | 2.7 | repair_TNS best 133545 last 133545 rows 1 | YOUNG: evidence 1.4 h < 2.5 h |  |
| epyc10 | dpkit-kv3_pv_v7e-1156836 | kv3_pv_v7e | 4_1_cts | 2.8 | last meaningful line 0.2 h ago (11439/11439 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v1__clf58b4dfb-461721 | sle_fw_v1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5070/5070 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 4_1_cts | 2.0 | last meaningful line 0.1 h ago (6732/6732 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-660000 | sle_hc0 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (96/96 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-830331 | sle_hc2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (310/310 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-223677 | sle_st_b_v1 | 3_3_place_gp | 0.5 | overflow best 0.4217 last 0.4217 rows 32 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3963118 | sle_st_b_v1 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (478/478 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__clfde1249e-689859 | sle_st_b_v2 | 3_3_place_gp | 0.1 | overflow best 0.7678 last 0.7678 rows 17 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (5160/5160 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (5204/5204 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (8368/8368 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-3446125 | slw_hc1 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-2082988 | slw_hc3 | 5_2_route | 5.6 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-856398 | slw_st_b_v1 | 3_1_place_gp_skip_io | 0.0 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-519492 | slw_st_b_v1 | 2_2_floorplan_macro | 0.3 | last meaningful line 0.0 h ago (83/83 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_stm_v1__cle34a73c3-4063338 | slw_stm_v1 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (4955/4955 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | otc-3605853-9611 | 3605853 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R1_coll_a | relec-r2-R1_coll_a | - | 0.7 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R2_coll_eco | relec-r2-R2_coll_eco | - | 0.7 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R3_coll_hint | relec-r2-R3_coll_hint | - | 0.7 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R8_hc3_pvcca | relec-r2-R8_hc3_pvcca | - | 0.7 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 5.9 | last meaningful line 2.3 h ago (48/61 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | pregrt_ff_hold | 0.2 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.2 h < 2.5 h |  |
| epyc11 | dpkit-kv3_hgi_v7-1276815 | kv3_hgi_v7 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (6778/6778 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hgi_v7-2589813 | kv3_hgi_v7 | lec | 0.0 | LEC last write 0.0 h ago | YOUNG: evidence 0.0 h < 6 h |  |
| epyc11 | dpkit-kv3_hgi_v8-2088531 | kv3_hgi_v8 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (5015/5015 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Eo-614287 | kv3_hub_Eo | 3_4_place_resized | 1.8 | last meaningful line 0.2 h ago (381/381 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-kv3_io_cor-3977350 | kv3_io_cor | 5_2_route | 5.4 | drt_violations best 7556 last 7556 rows 5 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v3e-3783354 | kv3_pv_v3e | 4_1_cts | 2.6 | last meaningful line 0.1 h ago (12626/12626 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v4ne-3869988 | kv3_pv_v4ne | 5_1_grt | 2.6 | last meaningful line 0.2 h ago (154/154 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 4_1_cts | 2.2 | last meaningful line 0.2 h ago (5944/5944 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_fw_v1__cl9d029624-56648 | sle_fw_v1 | 4_1_cts | 2.2 | last meaningful line 0.1 h ago (5213/5213 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | 4_1_cts | 2.3 | last meaningful line 0.1 h ago (5752/5752 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | pregrt_ff_hold | 2.2 | repair_TNS best 21336.9 last 21336.9 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-1187645 | slw_fw_v1 | generate_abstract | 14.4 | last meaningful line 0.4 h ago (1030/1030 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_fw_v3-263804 | slw_fw_v3 | tt_setup_measure | 2.1 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc2__cl6bcaba89-3858415 | slw_hc2 | pregrt_ff_hold | 2.6 | repair_TNS best 5041.48 last 5041.48 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3838177 | slw_hc3 | pregrt_ff_hold | 2.6 | repair_TNS best 336172 last 336172 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | pregrt_ff_hold | 2.0 | repair_TNS best 18565.1 last 18565.1 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc11 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-320042 | slw_st_b_v2 | pregrt_ff_hold | 2.0 | repair_TNS best 15218.4 last 15218.4 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc11 | lecautofill-hd_mesh | lecautofill-hd_mesh | - | 16.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc11 | prd-eco_20261124_154417_1016084-i1t-3435586 | eco_20261124_154417_1016084-i1t | 5_2_route | 2.9 | drt_violations best 8982 last 8982 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i1t-2053304 | eco_20261124_190641_1260390-i1t | 5_1_grt | 0.6 | last meaningful line 0.2 h ago (236/440 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | so_2110869_ff_24850 | so_2110869_ff_24850 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc11 | so_2110869_tt_24850 | so_2110869_tt_24850 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-cbn_q00__cl622f65d2-3557026 | cbn_q00 | pregrt_ff_hold | 1.5 | repair_Violations best 6092 last 6092 rows 22 | YOUNG: evidence 1.5 h < 2.5 h |  |
| epyc2 | dpkit-coll_ftm-1783743 | coll_ftm | 5_2_route | 2.7 | drt_violations best 15738 last 15738 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-glue-3558834 | glue | pregrt_ff_hold | 1.5 | repair_TNS best 7078.31 last 7078.31 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-kv3_hgi_v8-2448463 | kv3_hgi_v8 | 5_1_grt | 5.0 | last meaningful line 2.0 h ago (300/1310 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v5ne-2612763 | kv3_pv_v5ne | pregrt_ff_hold | 4.8 | repair_TNS best 827598 last 827598 rows 1 | YOUNG: evidence 1.7 h < 2.5 h |  |
| epyc2 | dpkit-kv3_sys_SD_v1-3451438 | kv3_sys_SD_v1 | generate_abstract | 1.6 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-1772768 | sle_hc0 | 4_1_cts | 2.7 | last meaningful line 0.3 h ago (5799/5799 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-491987 | sle_hc0 | 4_1_cts | 0.7 | last meaningful line 0.2 h ago (5570/5570 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-1254949 | sle_hc2 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (253/253 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3414126 | sle_hc2 | 4_1_cts | 1.6 | last meaningful line 0.1 h ago (4868/4868 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__clcc5e3e61-3434617 | sle_hc2 | 4_1_cts | 1.6 | last meaningful line 0.1 h ago (5136/5136 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 7.0 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-1186805 | sle_sc_v3 | 5_2_route | 6.0 | drt_violations best 233440 last 233440 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-1784944 | sle_st_a_v1 | postcts_gate_FF | 2.7 | last meaningful line 0.1 h ago (31/31 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-1826228 | sle_st_a_v1 | postcts_gate_FF | 2.7 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-1538145 | sle_st_a_v2 | 5_2_route | 2.9 | last meaningful line 0.1 h ago (275/276 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-4153401 | sle_stm_v2 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (4884/4884 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v3-1868496 | sle_stm_v3 | tt_setup_repair_grt | 2.6 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l0__cl7a55c676-4027948 | sle_su_l0 | 5_2_route | 6.9 | drt_violations best 70 last 70 rows 10 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-4191516 | slw_fw_v2 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (5844/5844 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1101031 | slw_hc3 | 3_3_place_gp | 0.3 | overflow best 0.1969 last 0.1969 rows 48 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3626034 | slw_hc3 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (4827/4827 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1494307 | slw_st_a_v1 | 5_2_route | 2.9 | last meaningful line 0.1 h ago (258/259 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-1494646 | slw_st_a_v2 | 5_2_route | 2.9 | last meaningful line 0.0 h ago (249/249 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3657462 | slw_stm_v2 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (6402/6402 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i3-451477 | eco_20261123_103136_2028090-i3 | 5_1_grt | 0.7 | last meaningful line 0.2 h ago (239/547 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 0.4 |  | NO-DATA: no log found |  |
| epyc2 | relec-r2-R7_reform_mapped | relec-r2-R7_reform_mapped | gate_b.ys | 0.4 | last meaningful line 0.2 h ago (94179/94179 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-1850782 | hd_lep0N_w | 5_2_route | 2.6 | last meaningful line 0.2 h ago (244/245 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-2222980 | sle_fw_v2 | 4_1_cts | 2.4 | last meaningful line 0.2 h ago (6822/6822 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 8.3 | last meaningful line 0.5 h ago (268/269 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | postcts_gate_FF | 6.9 | last meaningful line 0.0 h ago (2138/2138 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_1_grt | 2.3 | last meaningful line 0.0 h ago (258/259 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | pregrt_ff_hold | 2.6 | repair_TNS best 18114.5 last 18114.5 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | 5_2_route | 8.1 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl1bc59e1c-2061343 | slw_hc0 | 4_1_cts | 2.5 | last meaningful line 0.2 h ago (5619/5619 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | 4_1_cts | 2.4 | last meaningful line 0.2 h ago (5674/5674 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 4_1_cts | 2.5 | last meaningful line 0.1 h ago (5782/5782 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-2253577 | slw_hc2 | 4_1_cts | 2.4 | last meaningful line 0.2 h ago (5190/5190 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | postcts_gate_FF | 6.7 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 8.4 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | postcts_gate_TT | 6.8 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | 5_2_route | 8.5 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | pregrt_ff_hold | 2.4 | repair_TNS best 25807.7 last 25807.7 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | otc-1243059-2161 | 1243059 | asbuilt.yosys | 0.3 | last meaningful line 0.0 h ago (136607/136607 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i3t-3392092 | eco_20261123_171023_3055226-i3t | 5_2_route | 1.7 | last meaningful line 0.2 h ago (131/131 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_145005_2036075-i2t-1611651 | eco_20261124_145005_2036075-i2t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i1t-3184147 | eco_20261124_175441_992552-i1t | 5_2_route | 1.8 | drt_violations best 184185 last 184185 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | so_1320267_ff_99691 | so_1320267_ff_99691 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc7 | so_1320267_tt_99691 | so_1320267_tt_99691 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc7 | so_1455738_ff_64131 | so_1455738_ff_64131 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc7 | so_1455738_tt_64131 | so_1455738_tt_64131 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-coll_s-3875643 | coll_s | 5_2_route | 3.7 | drt_violations best 65079 last 65079 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 4_1_cts | 3.6 | last meaningful line 0.3 h ago (6187/6187 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | pregrt_ff_hold | 3.6 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | tt_setup_repair | 3.6 | repair_Remaining best 321602 last 321602 rows 70 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-sle_hc1__cl22c1ff36__pve230954c-3918742 | sle_hc1 | tt_setup_repair | 3.6 | last meaningful line 0.0 h ago (440/440 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 4_1_cts | 3.6 | last meaningful line 0.3 h ago (5845/5845 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_1_grt | 3.6 | last meaningful line 0.1 h ago (1939/1955 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-4063882 | sle_st_a_v2 | 5_2_route | 3.6 | drt_violations best 142170 last 142170 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | pregrt_ff_hold | 3.6 | repair_TNS best 165269 last 165269 rows 1 | YOUNG: evidence 1.4 h < 2.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | pregrt_ff_hold | 3.6 | repair_TNS best 176517 last 176517 rows 1 | YOUNG: evidence 1.5 h < 2.5 h |  |
| epyc8 | dpkit-sle_stm_v1__clbe630b9c-4072662 | sle_stm_v1 | 5_1_grt | 3.6 | last meaningful line 0.3 h ago (1321/1906 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | 5_1_grt | 3.6 | last meaningful line 0.3 h ago (279/869 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l0__cl7a55c676-4020210 | sle_su_l0 | 5_2_route | 3.6 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | pregrt_ff_hold | 3.6 | repair_TNS best 41408.7 last 41408.7 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | tt_setup_repair | 3.6 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 4_1_cts | 3.6 | last meaningful line 0.2 h ago (5796/5796 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 4_1_cts | 3.6 | last meaningful line 0.1 h ago (5488/5488 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | postcts_gate_FF | 6.9 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | pregrt_ff_hold | 3.7 | repair_TNS best 62810.5 last 62810.5 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3909116 | slw_hc3 | 5_1_grt | 3.7 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-3949912 | slw_hc3 | pregrt_ff_hold | 3.6 | repair_TNS best 337726 last 337726 rows 1 | YOUNG: evidence 1.4 h < 2.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_1_grt | 3.6 | last meaningful line 0.0 h ago (2010/2010 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_1_grt | 3.5 | last meaningful line 0.1 h ago (1941/1958 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | postcts_gate_FF | 3.6 | last meaningful line 0.0 h ago (523/523 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 5_2_route | 3.6 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | pregrt_ff_hold | 3.6 | repair_TNS best 158726 last 158726 rows 1 | YOUNG: evidence 1.4 h < 2.5 h |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-3848540 | slw_su_l0 | 5_2_route | 3.7 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 3.6 | drt_violations best 274214 last 274214 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3t-2289287 | eco_20261123_164145_1995767-i3t | 5_2_route | 1.1 | last meaningful line 0.0 h ago (154/154 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 0.5 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R1b_coll_old | relec-r2-R1b_coll_old | - | 0.4 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R4_coll_guard | relec-r2-R4_coll_guard | - | 0.5 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R9_hc3_d5fde | relec-r2-R9_hc3_d5fde | - | 0.4 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (4361/4361 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hub_Wo-2104173 | kv3_hub_Wo | 3_4_place_resized | 2.3 | last meaningful line 0.3 h ago (400/400 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5078/5078 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-1010348 | sle_fw_v1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4730/4730 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__clf58b4dfb-733846 | sle_fw_v1 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (5222/5222 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-667540 | sle_hc1 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (5507/5507 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 4_1_cts | 0.7 | last meaningful line 0.2 h ago (5800/5800 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-551472 | slw_fw_v1 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (5277/5277 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v2__cl8537f156-601723 | slw_fw_v2 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (4760/4760 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l0_wfb17da-849937 | qfd_qc_su_lane_w_l0_wfb17da | 5_1_grt | 5.8 | last meaningful line 0.0 h ago (2531/2531 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l1_w460927-787688 | qfd_qc_su_lane_w_l1_w460927 | 5_1_grt | 5.8 | last meaningful line 0.0 h ago (2515/2519 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l4_w285325-818329 | qfd_qc_su_lane_w_l4_w285325 | 5_1_grt | 5.8 | last meaningful line 0.3 h ago (2480/2759 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l5_wf949e1-824935 | qfd_qc_su_lane_w_l5_wf949e1 | 5_1_grt | 5.8 | last meaningful line 0.3 h ago (2480/2764 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l6_wb51d05-853896 | qfd_qc_su_lane_w_l6_wb51d05 | 5_1_grt | 5.8 | last meaningful line 0.0 h ago (2543/2549 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l7_wd4f14d-862251 | qfd_qc_su_lane_w_l7_wd4f14d | 5_1_grt | 5.7 | last meaningful line 0.0 h ago (2540/2540 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc9 | otc-1814577-31530 | 1814577 | - | 5.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-29732-24624 | 29732 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-29851-10135 | 29851 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-30219-7096 | 30219 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261123_224216_149959-i3t-3891967 | eco_20261123_224216_149959-i3t | 5_2_route | 3.7 | drt_violations best 19 last 19 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i2-1242463 | eco_20261124_010152_2867084-i2 | 5_2_route | 5.5 | drt_violations best 40 last 40 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-coll_core-3813096 | coll_core | 4_1_cts | 1.9 | last meaningful line 0.0 h ago (7587/7587 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-coll_ft__cla4a25d77-56057 | coll_ft | 5_2_route | 1.6 | last meaningful line 0.1 h ago (242/243 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-coll_ucie-4183666 | coll_ucie | 5_1_grt | 1.7 | last meaningful line 0.0 h ago (3239/3272 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v4-521791 | kv3_hgi_v4 | 3_5_place_dp | 1.3 | last meaningful line 0.0 h ago (89/89 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 4_1_cts | 4.4 | last meaningful line 0.3 h ago (12723/12723 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v5-1046392 | kv3_pv_v5 | pregrt_ff_hold | 3.8 | repair_TNS best 169718 last 169718 rows 1 | YOUNG: evidence 1.6 h < 2.5 h |  |
| intel1 | dpkit-kv3_pv_v8-3837707 | kv3_pv_v8 | 5_1_grt | 4.7 | last meaningful line 0.0 h ago (274/275 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v3-1442734 | sle_fw_v3 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (4705/4705 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 4_1_cts | 2.6 | last meaningful line 0.3 h ago (5833/5833 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3458150 | sle_hc2 | 4_1_cts | 2.2 | last meaningful line 0.1 h ago (5305/5305 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-1449506 | sle_st_b_v1 | 3_3_place_gp | 0.7 | overflow best 0.6344 last 0.6344 rows 23 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (4808/4808 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | 5_2_route | 5.0 | last meaningful line 0.1 h ago (134/134 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_1_grt | 6.9 | last meaningful line 0.2 h ago (142/142 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v3-1399930 | slw_fw_v3 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (4793/4793 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3463031 | slw_hc1 | 4_1_cts | 2.2 | last meaningful line 0.0 h ago (5819/5819 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-2314631 | slw_hc2 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2160450 | slw_hc3 | 3_3_place_gp | 0.1 | overflow best 0.9564 last 0.9564 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2973163 | slw_hc3 | 4_1_cts | 2.5 | last meaningful line 0.0 h ago (5125/5125 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-1726642 | slw_sc_v1 | 3_3_place_gp | 0.5 | overflow best 0.3263 last 0.3263 rows 20 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | pregrt_ff_hold | 2.6 | repair_TNS best 34417.5 last 34417.5 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | tt_setup_repair_grt | 6.9 | repair_Violations best 15 last 16 rows 7 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | pregrt_ff_hold | 2.6 | repair_TNS best 22724.7 last 22724.7 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 0.8 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 0.8 |  | NO-DATA: no log found |  |
| intel1 | otc-3854277-21865 | 3854277 | - | 4.7 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261123_191853_2879776-i2t-2852283 | eco_20261123_191853_2879776-i2t | 5_2_route | 2.6 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3102716 | coll_ftm | 5_1_grt | 0.5 | repair_Remaining best 29798 last 29798 rows 20 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-kv3_hub_C-524420 | kv3_hub_C | 2_1_floorplan | 2.2 | last meaningful line 1.8 h ago (1424/1424 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_Wi-487140 | kv3_hub_Wi | 3_3_place_gp | 2.2 | last meaningful line 0.1 h ago (512/512 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-2016810 | kv3_io_ft | 5_2_route | 1.2 | drt_violations best 5442 last 5442 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-60615 | sle_st_b_v2 | pregrt_ff_hold | 2.4 | repair_TNS best 21609.5 last 21609.5 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-2045071 | slice_station__t12 | generate_abstract | 1.2 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 4_1_cts | 2.1 | last meaningful line 0.0 h ago (5281/5281 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 4_1_cts | 2.3 | last meaningful line 0.1 h ago (4927/4927 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v2__cle0015330-180086 | kv3_hgi_v2 | pregrt_ff_hold | 0.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2793057 | sle_stm_v1 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 14.7 | drt_violations best 21399 last 21399 rows 11 | before-window best 186583, window best 21399 | PROGRESS: drt_violations improved 88.5 % in window |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | tt_setup_repair | 2.1 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | pregrt_ff_hold | 4.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 7.1 | drt_violations best 1983 last 1983 rows 13 | before-window best 112571, window best 1983 | PROGRESS: drt_violations improved 98.2 % in window |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-248626 | sle_st_b_v2 | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_sc_v3-3708441 | slw_sc_v3 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 34.1 | drt_violations best 13426 last 13426 rows 15 | before-window best 19595, window best 13426 | PROGRESS: drt_violations improved 31.5 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 27.4 | drt_violations best 15355 last 15355 rows 14 | before-window best 32431, window best 15355 | PROGRESS: drt_violations improved 52.7 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 12.1 | drt_violations best 490378 last 490378 rows 1 | before-window best 490378, window best 490378 | PROGRESS: drt_violations: active iteration at 178888 < best completed total 490378 (in-ite |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 12.3 | drt_violations best 141373 last 141373 rows 2 | before-window best 407677, window best 141373 | PROGRESS: drt_violations improved 65.3 % in window |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | prd-eco_20261124_192157_3493836-i1t-1220925 | eco_20261124_192157_3493836-i1t | 5_1_grt | 0.3 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-cbf_q00__cl1b5a6458-4114232 | cbf_q00 | pregrt_ff_hold | 1.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-cbn_q11__cl5cc92dfe-4036084 | cbn_q11 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | pregrt_ff_hold | 7.0 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-sle_hc1__cl7d360508__pv97423966-1341249 | sle_hc1 | pregrt_ff_hold | 7.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-3662089 | sle_sc_v1 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 10.9 | drt_violations best 2 last 2 rows 52 | before-window best 98, window best 2 | PROGRESS: drt_violations improved 98.0 % in window |  |
