# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 13:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 9, 'GRT-LABEL': 4, 'YOUNG': 166, 'NO-DATA': 21, 'PROGRESS': 23}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | pregrt_ff_hold | 5.1 | repair_TNS best 110979 last 110979 rows 1 | before-window best 110979, window best 110979 | NO-PROGRESS: repair_TNS best 110979 vs 110979 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | pregrt_ff_hold | 5.0 | repair_TNS best 149411 last 149411 rows 1 | before-window best 149411, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_pv_v6-908877 | kv3_pv_v6 | pregrt_ff_hold | 5.0 | repair_TNS best 37559.2 last 37559.2 rows 1 | before-window best 37559.2, window best 37559.2 | NO-PROGRESS: repair_TNS best 37559.2 vs 37559.2 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | pregrt_ff_hold | 2.2 | repair_TNS best 758714 last 758714 rows 1 | before-window best 758714, window best 758714 | NO-PROGRESS: repair_TNS best 758714 vs 758714 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-HG-CAP decides; neve |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | pregrt_ff_hold | 6.8 | repair_TNS best 100323 last 100323 rows 1 | before-window best 100323, window best 100323 | NO-PROGRESS: repair_TNS best 100323 vs 100323 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-HG-CAP decides; neve |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | pregrt_ff_hold | 4.6 | repair_TNS best 165765 last 165765 rows 1 | before-window best 165765, window best 165765 | NO-PROGRESS: repair_TNS best 165765 vs 165765 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 21.7 | last meaningful line 10.9 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 10.9 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1797391-24144 | 1797391 | flow3 | 8.6 | last meaningful line 8.2 h ago (208/209 lines) | NO-PROGRESS: no new non-iteration log line for 8.2 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 25.4 | last meaningful line 10.9 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 10.9 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc10 | dpkit-kv3_pv_v7e-1156836 | kv3_pv_v7e | 5_1_grt | 4.8 | grt rounds 1 overflow 5:101255 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc11 | dpkit-kv3_pv_v4ne-3869988 | kv3_pv_v4ne | 5_1_grt | 4.6 | grt rounds 1 overflow 5:114063 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_1_grt | 2.3 | grt rounds 2 overflow 5:4370 -> 10:2422 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pv_v3ne-3760907 | kv3_pv_v3ne | 5_1_grt | 6.8 | grt rounds 1 overflow 5:47095 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 4.8 | last meaningful line 3.5 h ago (48/58 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | tt_setup_measure_grt | 1.7 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1479488 | hd_spn | postcts_gate_TT | 1.5 | last meaningful line -0.0 h ago (27888/27888 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v3-1126078 | kv3_hg_v3 | 5_1_grt | 4.8 | last meaningful line 0.8 h ago (303/1310 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-1226895 | kv3_hgi_v2 | 5_1_grt | 1.7 | last meaningful line 0.5 h ago (288/1297 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v5-331504 | kv3_hgi_v5 | 5_1_grt | 2.4 | last meaningful line 0.2 h ago (287/1292 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (8467/8467 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v2-1075302 | kv3_pv_v2 | 5_1_grt | 4.8 | last meaningful line 1.0 h ago (266/1276 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v2n-1048434 | kv3_pv_v2n | 5_1_grt | 4.9 | last meaningful line 0.5 h ago (265/1272 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-2704273 | kv3_pv_v3 | 3_3_place_gp | 0.6 | last meaningful line 0.0 h ago (86/86 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v4e-1194094 | kv3_pv_v4e | 5_1_grt | 4.7 | last meaningful line 2.3 h ago (271/1281 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v6n-1030440 | kv3_pv_v6n | 5_1_grt | 4.9 | last meaningful line 0.8 h ago (264/1273 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v1__clf58b4dfb-461721 | sle_fw_v1 | 4_1_cts | 2.3 | last meaningful line 0.0 h ago (5542/5542 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-660000 | sle_hc0 | 4_1_cts | 2.2 | last meaningful line 0.1 h ago (5788/5788 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (4656/4656 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (5569/5569 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1583204 | sle_st_b_v1 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (5463/5463 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | 4_1_cts | 1.8 | last meaningful line 0.0 h ago (5546/5546 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__clfde1249e-689859 | sle_st_b_v2 | 4_1_cts | 2.1 | last meaningful line 0.0 h ago (5694/5694 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2793057 | sle_stm_v1 | 5_1_grt | 3.5 | repair_TNS best 15.477 last 15.477 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | pregrt_ff_hold | 2.9 | repair_TNS best 50016.7 last 50016.7 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | pregrt_ff_hold | 2.9 | repair_TNS best 56261.8 last 56261.8 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 4_1_cts | 3.0 | last meaningful line 0.2 h ago (8508/8508 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | 4_1_cts | 1.6 | last meaningful line 0.0 h ago (60/60 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-2082988 | slw_hc3 | 5_2_route | 7.6 | drt_violations best 8426 last 8426 rows 2 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-856398 | slw_st_b_v1 | 4_1_cts | 2.0 | last meaningful line 0.1 h ago (5464/5464 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2178798 | slw_st_b_v2 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | qc-colls-lec-h1 | qc-colls-lec-h1 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc10 | qc-colls-lec-h2 | qc-colls-lec-h2 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R1_coll_a | relec-r2-R1_coll_a | - | 2.7 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R2_coll_eco | relec-r2-R2_coll_eco | - | 2.7 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R3_coll_hint | relec-r2-R3_coll_hint | - | 2.7 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R8_hc3_pvcca | relec-r2-R8_hc3_pvcca | - | 2.7 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-U3_pv97423966 | relec-r2-U3_pv97423966 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 7.9 | last meaningful line 4.3 h ago (48/63 lines) | YOUNG: evidence 6.7 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hgi_v7-1276815 | kv3_hgi_v7 | 5_1_grt | 3.2 | last meaningful line 0.2 h ago (295/1299 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hgi_v8-2088531 | kv3_hgi_v8 | 5_1_grt | 2.5 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v3e-3783354 | kv3_pv_v3e | 5_1_grt | 4.6 | last meaningful line 1.2 h ago (270/1279 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | tt_setup_repair | 0.1 | last meaningful line 0.0 h ago (405/405 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_1_grt | 4.2 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_fw_v1__cl9d029624-56648 | sle_fw_v1 | 5_1_grt | 4.2 | last meaningful line 0.2 h ago (317/1118 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (5166/5167 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | pregrt_ff_hold | 4.3 | repair_TNS best 101814 last 101814 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-3613474 | sle_hc1 | 3_4_place_resized | 1.0 | repair_Remaining best 217980 last 217980 rows 172 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | 5_1_grt | 4.1 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | 5_1_grt | 4.2 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_fw_v3-263804 | slw_fw_v3 | postcts_gate_FF | 4.1 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc2__cl6bcaba89-3858415 | slw_hc2 | 5_1_grt | 4.6 | last meaningful line 0.1 h ago (1081/1098 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3838177 | slw_hc3 | postcts_gate_FF | 4.6 | last meaningful line 0.0 h ago (354/354 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | 5_1_grt | 4.0 | last meaningful line 0.2 h ago (281/1016 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-320042 | slw_st_b_v2 | 5_1_grt | 4.0 | last meaningful line 0.2 h ago (1014/1027 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc11 | lecautofill-hd_mesh | lecautofill-hd_mesh | - | 18.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 3.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-316081-19031 | 316081 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_154417_1016084-i1-3808110 | eco_20261124_154417_1016084-i1 | 5_1_grt | 0.8 | last meaningful line 0.5 h ago (243/1351 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i1t-2053304 | eco_20261124_190641_1260390-i1t | 5_2_route | 2.6 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i1t-3010529 | eco_20261124_200101_1087713-i1t | 5_2_route | 1.7 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_204246_1187010-i1t-3648808 | eco_20261124_204246_1187010-i1t | 5_1_grt | 1.0 | last meaningful line 0.5 h ago (235/1397 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-glue-3558834 | glue | 5_1_grt | 3.5 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-491987 | sle_hc0 | 4_1_cts | 2.7 | last meaningful line 0.2 h ago (5747/5747 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-1254949 | sle_hc2 | 4_1_cts | 2.2 | last meaningful line 0.2 h ago (5452/5452 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__clcc5e3e61-3434617 | sle_hc2 | pregrt_ff_hold | 3.6 | repair_TNS best 138735 last 138735 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 9.0 | drt_violations best 521993 last 521993 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-1186805 | sle_sc_v3 | 5_2_route | 8.0 | drt_violations best 40033 last 40033 rows 2 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-1784944 | sle_st_a_v1 | 5_2_route | 4.7 | drt_violations best 102586 last 102586 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-1826228 | sle_st_a_v1 | 5_2_route | 4.7 | drt_violations best 104942 last 104942 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-1538145 | sle_st_a_v2 | 5_2_route | 4.9 | drt_violations best 16498 last 16498 rows 3 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-4153401 | sle_stm_v2 | 5_1_grt | 3.1 | last meaningful line 0.3 h ago (1283/1876 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v3-1868496 | sle_stm_v3 | 5_2_route | 4.6 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-4191516 | slw_fw_v2 | 4_1_cts | 3.1 | last meaningful line 0.3 h ago (5957/5957 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1101031 | slw_hc3 | 4_1_cts | 2.3 | last meaningful line 0.0 h ago (5192/5192 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3626034 | slw_hc3 | 5_1_grt | 3.5 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v3-3708441 | slw_sc_v3 | postcts_gate_TT | 3.4 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1494307 | slw_st_a_v1 | 5_2_route | 4.9 | drt_violations best 133674 last 133674 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-1494646 | slw_st_a_v2 | 5_2_route | 4.9 | drt_violations best 99922 last 99922 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3657462 | slw_stm_v2 | 5_1_grt | 3.4 | last meaningful line 0.1 h ago (171/171 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | kqc-qc_cland_w1575_ew_078a8_synth0-3417634 | qc_cland_w1575_ew_078a8_synth0 | 5_2_route | 0.5 | drt_violations best 912 last 912 rows 2 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i3-451477 | eco_20261123_103136_2028090-i3 | 5_2_route | 2.7 | last meaningful line 0.2 h ago (292/293 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_130140_1782962-i1-3164922 | eco_20261124_130140_1782962-i1 | 5_2_route | 0.7 | last meaningful line 0.1 h ago (243/244 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_133404_4027156-i1-3855103 | eco_20261124_133404_4027156-i1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 2.4 |  | NO-DATA: no log found |  |
| epyc2 | relec-r2-R7_reform_mapped | relec-r2-R7_reform_mapped | gate_b.ys | 2.4 | last meaningful line 2.2 h ago (94179/94179 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-1850782 | hd_lep0N_w | 5_2_route | 4.6 | drt_violations best 121308 last 121308 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-2222980 | sle_fw_v2 | pregrt_ff_hold | 4.4 | repair_TNS best 1226.69 last 1226.69 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 10.3 | last meaningful line 0.5 h ago (278/279 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 8.9 | last meaningful line 0.5 h ago (263/264 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | postcts_gate_TT | 4.3 | last meaningful line 0.1 h ago (894/894 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | 5_1_grt | 4.6 | last meaningful line 0.2 h ago (143/143 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | 5_2_route | 10.1 | drt_violations best 147028 last 147028 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-2253577 | slw_hc2 | 5_1_grt | 4.4 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 8.7 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 10.4 | drt_violations best 400194 last 400194 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | 5_1_grt | 4.5 | last meaningful line 0.2 h ago (280/969 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | 5_2_route | 8.8 | last meaningful line 0.2 h ago (132/132 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | 5_2_route | 10.5 | drt_violations best 126854 last 126854 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i3t-3392092 | eco_20261123_171023_3055226-i3t | 5_2_route | 3.7 | last meaningful line 0.2 h ago (286/287 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_145005_2036075-i2t-1611651 | eco_20261124_145005_2036075-i2t | 5_2_route | 2.1 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i1-3895101 | eco_20261124_175441_992552-i1 | 5_2_route | 0.6 | last meaningful line 0.0 h ago (239/239 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i1t-1220925 | eco_20261124_192157_3493836-i1t | 5_2_route | 2.3 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_201304_2675397-i1-2517921 | eco_20261124_201304_2675397-i1 | 5_2_route | 1.5 | last meaningful line 0.0 h ago (264/264 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_1_grt | 5.6 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 5_1_grt | 5.6 | repair_Remaining best 268561 last 268561 rows 158 | YOUNG: stage 0.8 h < 1 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 5_1_grt | 5.6 | last meaningful line 0.2 h ago (138/138 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl22c1ff36__pve230954c-3918742 | sle_hc1 | 5_1_grt | 5.6 | last meaningful line 0.2 h ago (137/137 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 5_1_grt | 5.6 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | 5_1_grt | 5.7 | last meaningful line 0.1 h ago (927/939 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | postcts_gate_TT | 5.6 | last meaningful line -0.0 h ago (60800/60800 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-4063882 | sle_st_a_v2 | 5_2_route | 5.6 | drt_violations best 163 last 163 rows 15 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 5_1_grt | 5.6 | repair_Remaining best 430284 last 430284 rows 57 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 5_1_grt | 5.6 | last meaningful line 0.1 h ago (1053/1066 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | 5_1_grt | 5.6 | last meaningful line 0.1 h ago (2075/2088 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | postcts_gate_TT | 5.6 | last meaningful line 0.0 h ago (776/776 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l0__cl7a55c676-4020210 | sle_su_l0 | 5_2_route | 5.6 | drt_violations best 37418 last 37418 rows 2 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_1_grt | 5.6 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 5_1_grt | 5.6 | last meaningful line 0.2 h ago (273/859 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 5_1_grt | 5.6 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 5_1_grt | 5.6 | last meaningful line 0.2 h ago (138/138 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | 5_2_route | 8.9 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | tt_setup_repair_grt | 5.7 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3909116 | slw_hc3 | postcts_gate_FF | 5.7 | last meaningful line 0.0 h ago (471/471 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-3949912 | slw_hc3 | postcts_gate_FF | 5.6 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | postcts_gate_TT | 5.6 | last meaningful line -0.0 h ago (41439/41439 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 5.5 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | 5_2_route | 5.6 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 5_2_route | 5.6 | drt_violations best 146485 last 146485 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 5_1_grt | 5.6 | last meaningful line 0.1 h ago (1046/1059 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-3848540 | slw_su_l0 | 5_2_route | 5.7 | drt_violations best 18693 last 18693 rows 3 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 5.6 | drt_violations best 89614 last 89614 rows 2 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3t-2289287 | eco_20261123_164145_1995767-i3t | 5_2_route | 3.1 | last meaningful line 0.2 h ago (293/294 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261124_211939_3874698-i1-235182 | eco_20261124_211939_3874698-i1 | 5_1_grt | 0.4 | last meaningful line 0.1 h ago (288/374 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 2.5 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R1b_coll_old | relec-r2-R1b_coll_old | - | 2.4 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R4_coll_guard | relec-r2-R4_coll_guard | - | 2.5 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R9_hc3_d5fde | relec-r2-R9_hc3_d5fde | - | 2.4 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | 4_1_cts | 2.0 | last meaningful line 0.3 h ago (11041/11041 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | pregrt_ff_hold | 2.5 | repair_TNS best 77850.6 last 77850.6 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-1010348 | sle_fw_v1 | pregrt_ff_hold | 2.4 | repair_TNS best 33183.3 last 33183.3 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-sle_fw_v1__clf58b4dfb-733846 | sle_fw_v1 | pregrt_ff_hold | 2.6 | repair_TNS best 36659.2 last 36659.2 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-667540 | sle_hc1 | 4_1_cts | 2.6 | last meaningful line 0.0 h ago (5838/5838 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | pregrt_ff_hold | 2.7 | repair_TNS best 57997.5 last 57997.5 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-551472 | slw_fw_v1 | pregrt_ff_hold | 2.7 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc9 | dpkit-slw_fw_v2__cl8537f156-601723 | slw_fw_v2 | pregrt_ff_hold | 2.7 | repair_TNS best 41345.2 last 41345.2 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l0_wfb17da-849937 | qfd_qc_su_lane_w_l0_wfb17da | 5_2_route | 7.8 | drt_violations best 48120 last 48120 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l1_w460927-787688 | qfd_qc_su_lane_w_l1_w460927 | 5_2_route | 7.8 | drt_violations best 47004 last 47004 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l4_w285325-818329 | qfd_qc_su_lane_w_l4_w285325 | 5_2_route | 7.8 | drt_violations best 47451 last 47451 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l5_wf949e1-824935 | qfd_qc_su_lane_w_l5_wf949e1 | 5_2_route | 7.8 | drt_violations best 4414 last 4414 rows 2 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l6_wb51d05-853896 | qfd_qc_su_lane_w_l6_wb51d05 | 5_2_route | 7.8 | drt_violations best 47801 last 47801 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l7_wd4f14d-862251 | qfd_qc_su_lane_w_l7_wd4f14d | 5_2_route | 7.7 | drt_violations best 46809 last 46809 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | otc-1814577-31530 | 1814577 | - | 7.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-29732-24624 | 29732 | - | 3.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-29851-10135 | 29851 | - | 3.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-30219-7096 | 30219 | - | 3.1 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261123_224216_149959-i3-3801930 | eco_20261123_224216_149959-i3 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (143/143 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | so_4137838_ff_91211 | so_4137838_ff_91211 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | so_4137838_tt_91211 | so_4137838_tt_91211 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl1b5a6458-4114232 | cbf_q00 | 5_1_grt | 3.7 | last meaningful line 0.2 h ago (266/1273 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-coll_core-3813096 | coll_core | pregrt_ff_hold | 3.9 | repair_TNS best 67769.2 last 67769.2 rows 1 | YOUNG: evidence 1.7 h < 2.5 h |  |
| intel1 | dpkit-kv3_hgi_v4-3072149 | kv3_hgi_v4 | pregrt_ff_hold | 1.5 | repair_TNS best 12034.1 last 12034.1 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-native59-2938294 | native59 | 3_3_place_gp | 1.6 | overflow best 0.2985 last 0.5757 rows 194 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 5_1_grt | 9.0 | last meaningful line 0.2 h ago (2503/2564 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v3-1442734 | sle_fw_v3 | 4_1_cts | 2.7 | last meaningful line 0.1 h ago (4887/4887 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | pregrt_ff_hold | 4.6 | repair_TNS best 7788.12 last 7788.12 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | pregrt_ff_hold | 2.7 | last meaningful line 0.0 h ago (78/78 lines) | YOUNG: evidence 0.6 h < 2.5 h |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | pregrt_ff_hold | 0.9 | last meaningful line 0.0 h ago (58/58 lines) | YOUNG: evidence 0.2 h < 2.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3498094 | slw_fe_v1 | 3_5_place_dp | 1.2 | last meaningful line 0.0 h ago (59/59 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | 5_2_route | 7.0 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3282256 | slw_fw_v1 | 3_4_place_resized | 1.4 | repair_Remaining best 41852 last 41852 rows 259 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | tt_setup_repair_grt | 8.9 | last meaningful line 0.0 h ago (804/804 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v3-1399930 | slw_fw_v3 | 4_1_cts | 2.7 | last meaningful line 0.2 h ago (5084/5084 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3463031 | slw_hc1 | pregrt_ff_hold | 4.2 | repair_TNS best 23928.5 last 23928.5 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2360221 | slw_hc2 | 4_1_cts | 2.0 | last meaningful line 0.0 h ago (5080/5080 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | postplace_setup | 0.7 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2160450 | slw_hc3 | 4_1_cts | 2.1 | last meaningful line 0.2 h ago (4766/4766 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3890746 | slw_sc_v1 | 3_5_place_dp | 1.0 | last meaningful line 0.1 h ago (111/111 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | postcts_gate_FF | 8.9 | last meaningful line 0.0 h ago (1566/1566 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 5_1_grt | 4.6 | repair_TNS best 87.572 last 87.572 rows 2 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1e5219ea-4177722 | slw_su_l0 | pregrt_ff_hold | 0.8 | repair_TNS best 43215.8 last 43215.8 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 2.8 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 2.8 |  | NO-DATA: no log found |  |
| intel1 | otc-3854277-21865 | 3854277 | - | 6.7 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261123_191853_2879776-i2t-2852283 | eco_20261123_191853_2879776-i2t | 5_2_route | 4.6 | drt_violations best 3711 last 3711 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-1884094 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_C-524420 | kv3_hub_C | 2_4_floorplan_pdn | 4.2 | last meaningful line 0.5 h ago (175/175 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_Wi-487140 | kv3_hub_Wi | 3_4_place_resized | 4.2 | last meaningful line 0.5 h ago (643/643 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | pregrt_ff_hold | 4.1 | repair_TNS best 58949 last 58949 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_stm_v1__cle34a73c3-4063338 | slw_stm_v1 | 5_1_grt | 2.7 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 16.7 | drt_violations best 18158 last 18158 rows 13 | before-window best 186583, window best 18158 | PROGRESS: drt_violations improved 90.3 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 9.1 | drt_violations best 1814 last 1814 rows 15 | before-window best 112571, window best 1814 | PROGRESS: drt_violations improved 98.4 % in window |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-1772768 | sle_hc0 | pregrt_ff_hold | 4.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3414126 | sle_hc2 | pregrt_ff_hold | 3.6 | repair_Violations best 0 last 0 rows 3 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 36.1 | drt_violations best 11554 last 11554 rows 16 | before-window best 17065, window best 11554 | PROGRESS: drt_violations improved 32.3 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 29.4 | drt_violations best 11933 last 11933 rows 15 | before-window best 27940, window best 11933 | PROGRESS: drt_violations improved 57.3 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 14.1 | drt_violations best 109083 last 109083 rows 2 | before-window best 490378, window best 109083 | PROGRESS: drt_violations improved 77.8 % in window |  |
| epyc7 | dpkit-slw_hc0__cl1bc59e1c-2061343 | slw_hc0 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 14.3 | drt_violations best 74091 last 74091 rows 4 | before-window best 407677, window best 74091 | PROGRESS: drt_violations improved 81.8 % in window |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | 5_1_grt | 4.4 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | 5_1_grt | 5.7 | repair_TNS best 0 last 0 rows 4 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 4_1_cts | 6.4 | last meaningful line 0.3 h ago (13059/13059 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3458150 | sle_hc2 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-3662089 | sle_sc_v1 | 5_1_grt | 4.0 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2973163 | slw_hc3 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-60615 | sle_st_b_v2 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slice_station__t12-1909702 | slice_station__t12 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 12.9 | drt_violations best 2 last 47 rows 54 | before-window best 8, window best 2 | PROGRESS: drt_violations improved 75.0 % in window |  |
