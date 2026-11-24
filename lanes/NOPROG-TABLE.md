# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 15:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 6, 'GRT-LABEL': 7, 'NO-DATA': 19, 'YOUNG': 156, 'PROGRESS': 21}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | pregrt_ff_hold | 4.2 | repair_TNS best 100323 last 100323 rows 1 | before-window best 100323, window best 100323 | NO-PROGRESS: repair_TNS best 100323 vs 100323 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-HG-CAP decides; neve |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3458150 | sle_hc2 | pregrt_ff_hold | 6.2 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 23.7 | last meaningful line 12.9 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 12.9 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1797391-24144 | 1797391 | flow3 | 10.6 | last meaningful line 10.2 h ago (208/209 lines) | NO-PROGRESS: no new non-iteration log line for 10.2 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 27.4 | last meaningful line 12.9 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 12.9 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 14.9 | drt_violations best 2 last 47 rows 54 | before-window best 2, window best 2 | NO-PROGRESS: drt_violations best 2 vs 2 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 5_1_grt | 7.1 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv_v2n-1048434 | kv3_pv_v2n | 5_1_grt | 6.9 | grt rounds 2 overflow 5:64147 -> 10:49031 | GRT-LABEL: DESIGN-FAIL: overflow 49031 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v6-908877 | kv3_pv_v6 | 5_1_grt | 7.0 | grt rounds 2 overflow 5:56449 -> 10:44954 | GRT-LABEL: DESIGN-FAIL: overflow 44954 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v7e-1156836 | kv3_pv_v7e | 5_1_grt | 6.8 | grt rounds 2 overflow 5:101255 -> 10:76491 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc11 | dpkit-kv3_pv_v3ne-2121576 | kv3_pv_v3ne | 5_1_grt | 0.2 | grt rounds 2 overflow 5:47095 -> 10:34560 | GRT-LABEL: DESIGN-FAIL: overflow 34560 at round 10 > 1000 |  |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 5_1_grt | 8.8 | grt rounds 1 overflow 5:41695 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 5_1_grt | 8.4 | grt rounds 1 overflow 5:83232 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-kv3-pv-v3-grt-2229651 | kv3-pv-v3-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 6.8 | last meaningful line 5.5 h ago (48/63 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | 5_2_route | 3.7 | drt_violations best 33912 last 33912 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1479488 | hd_spn | 5_2_route | 3.5 | drt_violations best 24108 last 24108 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-579995 | kv3_hub_Wo | 3_3_place_gp | 1.2 | overflow best 0.6537 last 0.6537 rows 18 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r85c02c25c-1305082 | kv3_pc | 3_1_place_gp_skip_io | 0.7 | overflow best 0.2049 last 0.2049 rows 42 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | 4_1_cts | 2.2 | last meaningful line 0.0 h ago (9418/9418 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v1__clf58b4dfb-461721 | sle_fw_v1 | 5_1_grt | 4.3 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_1_grt | 6.0 | last meaningful line 0.8 h ago (1286/2020 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-660000 | sle_hc0 | tt_setup_repair | 4.2 | repair_Remaining best 258866 last 258866 rows 136 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | 4_1_cts | 2.8 | last meaningful line 0.1 h ago (5094/5094 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | pregrt_ff_hold | 3.2 | repair_TNS best 22304.1 last 22304.1 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1583204 | sle_st_b_v1 | pregrt_ff_hold | 3.5 | repair_TNS best 19705 last 19705 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | 5_1_grt | 3.8 | last meaningful line 0.2 h ago (266/1270 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2793057 | sle_stm_v1 | postcts_gate_FF | 5.5 | last meaningful line 0.0 h ago (1662/1662 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_1_grt | 4.9 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_1_grt | 4.9 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | pregrt_ff_hold | 5.0 | repair_TNS best 169942 last 169942 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | 4_1_cts | 3.6 | last meaningful line 0.2 h ago (5488/5488 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | 4_1_cts | 2.7 | last meaningful line 0.0 h ago (5635/5635 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-1320764 | slw_st_b_v2 | 3_3_place_gp | 0.7 | overflow best 0.454 last 0.454 rows 31 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | 4_1_cts | 1.7 | last meaningful line 0.0 h ago (4776/4776 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_stm_v1__cle34a73c3-4063338 | slw_stm_v1 | postcts_gate_TT | 4.7 | last meaningful line 0.0 h ago (1567/1567 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | otc-901577-23707 | 901577 | signoff | 1.0 | last meaningful line 1.0 h ago (3/3 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | qc-colls-lec-h1 | qc-colls-lec-h1 | - | 2.3 |  | NO-DATA: no log found |  |
| epyc10 | qc-colls-lec-h2 | qc-colls-lec-h2 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc10 | qc-hc3-lec-r8-nearest | qc-hc3-lec-r8-nearest | - | 0.7 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R2_coll_eco | relec-r2-R2_coll_eco | - | 4.7 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R3_coll_hint | relec-r2-R3_coll_hint | - | 4.7 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R8_hc3_pvcca | relec-r2-R8_hc3_pvcca | - | 4.7 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-U3_pv97423966 | relec-r2-U3_pv97423966 | - | 2.7 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-kv3_hgi_v8-2088531 | kv3_hgi_v8 | 5_1_grt | 4.5 | last meaningful line 1.5 h ago (300/1310 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 2.1 | repair_TNS best 827598 last 827598 rows 1 | YOUNG: evidence 2.1 h < 2.5 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 4_1_cts | 1.8 | last meaningful line 0.1 h ago (5920/5920 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 4_1_cts | 2.8 | last meaningful line 0.2 h ago (5450/5450 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | tt_setup_repair_grt | 6.3 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (5382/5382 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | 5_1_grt | 6.1 | last meaningful line 0.1 h ago (1226/1232 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | 5_1_grt | 6.2 | last meaningful line 0.2 h ago (1227/1281 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc2__cl6bcaba89-3858415 | slw_hc2 | 5_2_route | 6.6 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-1745229 | slw_hc3 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3838177 | slw_hc3 | 5_2_route | 6.6 | drt_violations best 82961 last 82961 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | postcts_gate_TT | 6.0 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-320042 | slw_st_b_v2 | postcts_gate_FF | 6.0 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 5.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-2078919-10849 | 2078919 | asbuilt.yosys | 0.3 | last meaningful line -0.0 h ago (135503/135503 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | otc-2136782-11303 | 2136782 | asbuilt.yosys | 0.2 | last meaningful line -0.0 h ago (135815/135815 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_154417_1016084-i1-3808110 | eco_20261124_154417_1016084-i1 | 5_2_route | 2.8 | drt_violations best 80 last 80 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i1t-2053304 | eco_20261124_190641_1260390-i1t | 5_3_fillcell | 4.6 | last meaningful line -0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i1t-3010529 | eco_20261124_200101_1087713-i1t | 5_2_route | 3.7 | drt_violations best 18110 last 18110 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_204246_1187010-i1t-3648808 | eco_20261124_204246_1187010-i1t | 5_2_route | 3.0 | last meaningful line 0.2 h ago (284/285 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-glue-3558834 | glue | postcts_gate_FF | 5.5 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v2__cle0015330-2015173 | kv3_hgi_v2 | pregrt_ff_hold | 0.5 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc2 | dpkit-kv3_hub_Wo-1888444 | kv3_hub_Wo | 3_1_place_gp_skip_io | 0.6 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-491987 | sle_hc0 | 5_1_grt | 4.7 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-1254949 | sle_hc2 | pregrt_ff_hold | 4.2 | repair_TNS best 6194.91 last 6194.91 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3414126 | sle_hc2 | postcts_gate_TT | 5.6 | last meaningful line 0.0 h ago (763/763 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__clcc5e3e61-3434617 | sle_hc2 | postcts_gate_TT | 5.6 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 11.0 | drt_violations best 521993 last 521993 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-1186805 | sle_sc_v3 | 6_report | 10.0 | last meaningful line 0.1 h ago (67/67 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-1784944 | sle_st_a_v1 | 5_2_route | 6.7 | drt_violations best 105 last 113 rows 29 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-1826228 | sle_st_a_v1 | 5_2_route | 6.7 | drt_violations best 89 last 114 rows 28 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-1538145 | sle_st_a_v2 | 5_2_route | 6.9 | drt_violations best 72 last 72 rows 45 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1751534 | sle_st_b_v2 | 3_3_place_gp | 0.7 | overflow best 0.0992 last 0.0992 rows 46 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-4153401 | sle_stm_v2 | 5_2_route | 5.1 | last meaningful line 0.2 h ago (262/263 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v3-1868496 | sle_stm_v3 | 5_2_route | 6.6 | drt_violations best 11611 last 11611 rows 2 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-4191516 | slw_fw_v2 | pregrt_ff_hold | 5.1 | repair_TNS best 41393.8 last 41393.8 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1101031 | slw_hc3 | 5_1_grt | 4.3 | last meaningful line 0.0 h ago (979/985 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3626034 | slw_hc3 | 5_2_route | 5.5 | last meaningful line 0.0 h ago (254/254 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1494307 | slw_st_a_v1 | 5_2_route | 6.9 | drt_violations best 128 last 128 rows 23 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-1494646 | slw_st_a_v2 | 5_2_route | 6.9 | drt_violations best 133 last 133 rows 21 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-2708297 | slw_st_b_v1 | reg_fanout | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3657462 | slw_stm_v2 | postcts_gate_TT | 5.4 | last meaningful line 0.0 h ago (1505/1505 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | eco-abs-2411647 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-fin-3855103 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 4.4 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-hd_lep0N_w-1850782 | hd_lep0N_w | 6_report | 6.6 | last meaningful line 0.0 h ago (72/72 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-2222980 | sle_fw_v2 | 5_1_grt | 6.4 | repair_Remaining best 368466 last 368466 rows 42 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 12.3 | drt_violations best 504597 last 504597 rows 1 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 10.9 | last meaningful line 0.7 h ago (271/272 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 6.3 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | 5_1_grt | 6.6 | last meaningful line 0.2 h ago (2203/2220 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | 5_2_route | 12.1 | drt_violations best 14021 last 14021 rows 3 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | 5_1_grt | 6.4 | last meaningful line 0.1 h ago (955/968 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 5_1_grt | 6.5 | last meaningful line 0.1 h ago (952/965 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-2253577 | slw_hc2 | postcts_gate_TT | 6.4 | last meaningful line 0.1 h ago (31/31 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 10.7 | last meaningful line 0.5 h ago (276/277 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | postcts_gate_TT | 6.5 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | 5_2_route | 10.8 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | 5_2_route | 12.5 | drt_violations best 126854 last 126854 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | postcts_gate_FF | 6.4 | last meaningful line -0.0 h ago (22197/22197 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i3t-3392092 | eco_20261123_171023_3055226-i3t | 5_2_route | 5.7 | drt_violations best 835 last 835 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_145005_2036075-i2t-1611651 | eco_20261124_145005_2036075-i2t | 5_2_route | 4.1 | drt_violations best 5275 last 5275 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i1-3895101 | eco_20261124_175441_992552-i1 | 5_2_route | 2.6 | drt_violations best 10 last 10 rows 5 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i1t-1220925 | eco_20261124_192157_3493836-i1t | 5_2_route | 4.3 | drt_violations best 5844 last 5844 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795561668594539576-i1-3034100 | eco_retry_1795561668594539576-i1 | 5_1_grt | 0.6 | last meaningful line 0.1 h ago (296/312 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_1_grt | 7.6 | last meaningful line 0.4 h ago (2466/2479 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | postcts_gate_TT | 7.6 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | postcts_gate_FF | 7.6 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl22c1ff36__pve230954c-3918742 | sle_hc1 | tt_setup_measure_grt | 7.6 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | tt_setup_repair_grt | 7.6 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | postcts_gate_FF | 7.7 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | postcts_gate_TT | 7.7 | last meaningful line -0.0 h ago (54261/54261 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 7.6 | last meaningful line 0.2 h ago (261/262 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-4063882 | sle_st_a_v2 | 5_2_route | 7.6 | drt_violations best 72 last 72 rows 48 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 5_1_grt | 7.6 | last meaningful line 0.1 h ago (2233/2287 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | postcts_gate_TT | 7.6 | last meaningful line 0.1 h ago (504/504 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | postcts_gate_TT | 7.6 | last meaningful line 0.0 h ago (472/472 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | 5_2_route | 7.6 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l0__cl7a55c676-4020210 | sle_su_l0 | 5_2_route | 7.6 | drt_violations best 34 last 34 rows 10 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | postcts_gate_TT | 7.6 | last meaningful line 0.1 h ago (406/406 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 5_1_grt | 7.6 | last meaningful line 0.1 h ago (1137/1154 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | postcts_gate_TT | 7.6 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | 5_2_route | 10.9 | drt_violations best 100793 last 100793 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | postcts_gate_FF | 7.7 | last meaningful line 0.1 h ago (714/714 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3909116 | slw_hc3 | 5_2_route | 7.7 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-3949912 | slw_hc3 | 5_2_route | 7.6 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 7.6 | last meaningful line 0.2 h ago (266/266 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 7.5 | last meaningful line 0.5 h ago (273/274 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | 5_2_route | 7.6 | drt_violations best 149425 last 149425 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 5_2_route | 7.6 | drt_violations best 140 last 140 rows 17 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 7.6 | drt_violations best 28746 last 28746 rows 5 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc8 | otc-2103320-31020 | 2103320 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3t-2289287 | eco_20261123_164145_1995767-i3t | 5_2_route | 5.1 | drt_violations best 35664 last 35664 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261124_225649_3846510-i1-114505 | eco_20261124_225649_3846510-i1 | 5_2_route | 0.8 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-fin-235182 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 4.5 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R1b_coll_old | relec-r2-R1b_coll_old | - | 4.4 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R4_coll_guard | relec-r2-R4_coll_guard | - | 4.5 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R9_hc3_d5fde | relec-r2-R9_hc3_d5fde | - | 4.4 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 4.3 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc_v1__cl4ea58a5c__r84d0332e1-2724994 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.3421 last 0.3421 rows 38 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | 4_1_cts | 4.0 | last meaningful line 0.5 h ago (11126/11126 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_1_grt | 4.5 | repair_Remaining best 221809 last 221809 rows 157 | YOUNG: stage 1.0 h < 1 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-1010348 | sle_fw_v1 | 5_1_grt | 4.4 | repair_Remaining best 316696 last 316696 rows 95 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-sle_fw_v1__clf58b4dfb-733846 | sle_fw_v1 | 5_1_grt | 4.6 | repair_Remaining best 336319 last 336319 rows 80 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-667540 | sle_hc1 | 5_1_grt | 4.6 | repair_Remaining best 435786 last 435786 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_1_grt | 4.7 | last meaningful line 0.0 h ago (161/161 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-551472 | slw_fw_v1 | 5_1_grt | 4.7 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | otc-1893022-28497 | 1893022 | signoff | 1.3 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | otc-2115495-15878 | 2115495 | signoff | 1.1 | last meaningful line 1.0 h ago (3/3 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | otc-2119148-18648 | 2119148 | signoff | 1.1 | last meaningful line 1.0 h ago (3/3 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | otc-2126591-20932 | 2126591 | signoff | 1.1 | last meaningful line 1.0 h ago (3/3 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | otc-2136971-27474 | 2136971 | signoff | 1.1 | last meaningful line 1.0 h ago (3/3 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i3-3801930 | eco_20261123_224216_149959-i3 | 5_2_route | 2.4 | last meaningful line 0.2 h ago (286/287 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-coll_core-3813096 | coll_core | 5_1_grt | 5.9 | repair_Remaining best 204526 last 204526 rows 187 | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v4-3072149 | kv3_hgi_v4 | 5_1_grt | 3.5 | last meaningful line 0.3 h ago (292/1298 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | postcts_gate_TT | 11.0 | last meaningful line 0.2 h ago (1957/1957 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v3-1442734 | sle_fw_v3 | 5_1_grt | 4.7 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 5_1_grt | 6.6 | last meaningful line 0.5 h ago (273/883 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-3662089 | sle_sc_v1 | postcts_gate_TT | 6.0 | last meaningful line 0.1 h ago (2139/2139 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 4_1_cts | 3.0 | last meaningful line 0.0 h ago (5599/5599 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 5_1_grt | 4.7 | last meaningful line 0.1 h ago (969/986 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_1_grt | 2.9 | last meaningful line 0.1 h ago (1838/1855 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 4_1_cts | 0.4 | last meaningful line 0.2 h ago (5158/5158 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | 5_2_route | 9.0 | drt_violations best 234054 last 234054 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3325358 | slw_fw_v1 | 4_1_cts | 0.4 | last meaningful line 0.2 h ago (4944/4944 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 10.9 | last meaningful line 0.1 h ago (264/264 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v3-1399930 | slw_fw_v3 | 5_1_grt | 4.7 | last meaningful line 0.5 h ago (286/1712 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 4_1_cts | 1.5 | last meaningful line 0.2 h ago (5165/5165 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2360221 | slw_hc2 | 4_1_cts | 4.0 | last meaningful line 0.0 h ago (5296/5296 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 4_1_cts | 2.7 | last meaningful line 0.1 h ago (5064/5064 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3890746 | slw_sc_v1 | pregrt_ff_hold | 3.0 | last meaningful line 0.0 h ago (47/47 lines) | YOUNG: evidence 0.1 h < 2.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 5_1_grt | 6.6 | last meaningful line 0.1 h ago (1094/1107 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (4591/4591 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | 5_2_route | 10.9 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | postcts_gate_FF | 6.6 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1e5219ea-4177722 | slw_su_l0 | 5_1_grt | 2.8 | last meaningful line 0.0 h ago (1859/1896 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-3090069 | slw_su_l0 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (2670/2670 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-tt_ctlm-3234028 | tt_ctlm | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3827/3827 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 4.8 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 4.8 |  | NO-DATA: no log found |  |
| intel1 | otc-3854277-21865 | 3854277 | - | 8.7 |  | NO-DATA: no log found |  |
| intel2 | dpkit-coll_ftm-2194683 | coll_ftm | 5_2_route | 2.0 | drt_violations best 10288 last 10288 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | tt_setup_measure_grt | 6.3 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | pregrt_ff_hold | 7.0 | repair_Violations best 49621 last 49621 rows 27 | before-window best 314357, window best 49621 | PROGRESS: repair_Violations improved 84.2 % in window |  |
| epyc10 | dpkit-sle_st_b_v2__clfde1249e-689859 | sle_st_b_v2 | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-856398 | slw_st_b_v1 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 9.9 | last meaningful line 6.3 h ago (48/187 lines) | PROGRESS: log still growing |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_1_grt | 6.2 | repair_TNS best 0 last 0 rows 10 | PROGRESS: repair_TNS reached 0 |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 18.7 | drt_violations best 16673 last 16673 rows 14 | before-window best 27162, window best 16673 | PROGRESS: drt_violations improved 38.6 % in window |  |
| epyc2 | dpkit-kv3_hroot-1457043 | kv3_hroot | 5_1_grt | 0.9 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 11.1 | drt_violations best 1743 last 5229 rows 18 | before-window best 3088, window best 1743 | PROGRESS: drt_violations improved 43.6 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 38.1 | drt_violations best 10129 last 10129 rows 17 | before-window best 14975, window best 10129 | PROGRESS: drt_violations improved 32.4 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 31.4 | drt_violations best 9091 last 9091 rows 16 | before-window best 20899, window best 9091 | PROGRESS: drt_violations improved 56.5 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 16.1 | drt_violations best 13722 last 13722 rows 5 | before-window best 490378, window best 13722 | PROGRESS: drt_violations improved 97.2 % in window |  |
| epyc7 | dpkit-slw_hc0__cl1bc59e1c-2061343 | slw_hc0 | 5_1_grt | 6.5 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 16.3 | drt_violations best 69686 last 69686 rows 5 | before-window best 407677, window best 69686 | PROGRESS: drt_violations improved 82.9 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 12.4 | drt_violations best 123176 last 123176 rows 2 | before-window best 400194, window best 123176 | PROGRESS: drt_violations improved 69.2 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_1_grt | 7.6 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | tt_setup_repair_grt | 7.6 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-slw_fw_v2__cl8537f156-601723 | slw_fw_v2 | 5_1_grt | 4.7 | repair_TNS best 0 last 0 rows 4 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3463031 | slw_hc1 | pregrt_ff_hold | 6.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2160450 | slw_hc3 | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261123_191853_2879776-i2t-2852283 | eco_20261123_191853_2879776-i2t | 5_2_route | 6.6 | drt_violations best 0 last 0 rows 4 | PROGRESS: drt_violations reached 0 |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | pregrt_ff_hold | 6.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
