# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 16:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 8, 'GRT-LABEL': 5, 'YOUNG': 151, 'NO-DATA': 18, 'PROGRESS': 29}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 7.6 | last meaningful line 6.3 h ago (48/132 lines) | NO-PROGRESS: no new non-iteration log line for 6.3 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 10.6 | last meaningful line 7.1 h ago (48/189 lines) | NO-PROGRESS: no new non-iteration log line for 7.1 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 2.8 | repair_TNS best 827598 last 827598 rows 1 | before-window best 827598, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3458150 | sle_hc2 | pregrt_ff_hold | 6.7 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | CANCELLED |
| intel1 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3463031 | slw_hc1 | pregrt_ff_hold | 6.7 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 24.2 | last meaningful line 13.4 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 13.4 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1797391-24144 | 1797391 | flow3 | 11.1 | last meaningful line 10.7 h ago (208/209 lines) | NO-PROGRESS: no new non-iteration log line for 10.7 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 27.9 | last meaningful line 13.4 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 13.4 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 5_1_grt | 7.9 | grt rounds 1 overflow 5:42234 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv_v2n-1048434 | kv3_pv_v2n | 5_1_grt | 7.6 | grt rounds 2 overflow 5:64147 -> 10:49031 | GRT-LABEL: DESIGN-FAIL: overflow 49031 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v6-908877 | kv3_pv_v6 | 5_1_grt | 7.7 | grt rounds 2 overflow 5:56449 -> 10:44954 | GRT-LABEL: DESIGN-FAIL: overflow 44954 at round 10 > 1000 |  |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 5_1_grt | 9.6 | grt rounds 1 overflow 5:41695 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 5_1_grt | 8.9 | grt rounds 1 overflow 5:83232 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-glue-3579966 | glue | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (220/220 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | 5_2_route | 4.4 | drt_violations best 10214 last 10214 rows 2 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1479488 | hd_spn | 6_report | 4.3 | last meaningful line 0.0 h ago (47/47 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r889141819-3256830 | kv3_hg_v1__r889141819 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (103/103 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r88f4bfb40-3256090 | kv3_hg_v1__r88f4bfb40 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (66/66 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r8dffc461a-3274501 | kv3_hg_v1__r8dffc461a | 2_3_floorplan_tapcell | 0.2 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p2-3246486 | kv3_hg_v1p2 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p3__r81da466fe-3244974 | kv3_hg_v1p3__r81da466fe | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p3__r838481cd7-3239592 | kv3_hg_v1p3__r838481cd7 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (103/103 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-3028627 | kv3_hgi | 3_1_place_gp_skip_io | 0.3 | overflow best 0.2731 last 0.2731 rows 35 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_hgi-3075963 | kv3_hgi | 3_1_place_gp_skip_io | 0.3 | overflow best 0.4295 last 0.4295 rows 30 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-3077015 | kv3_hgi_v2 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.6583 last 0.6835 rows 20 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-3111420 | kv3_hgi_v2 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.6583 last 0.6769 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_hub_Wo-579995 | kv3_hub_Wo | 3_4_place_resized | 2.0 | last meaningful line 0.1 h ago (399/399 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8afe1e027-2684889 | kv3_pc_v1 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.1 h ago (56/56 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-2695537 | kv3_pc_v1 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.1 h ago (56/56 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | 5_1_grt | 7.7 | last meaningful line 0.1 h ago (155/155 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | pregrt_ff_hold | 2.9 | repair_TNS best 46556.5 last 46556.5 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v7e-1156836 | kv3_pv_v7e | postcts_gate_TT | 7.5 | last meaningful line 0.3 h ago (17/17 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-native59-3512619 | native59 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (210/210 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v1__clf58b4dfb-461721 | sle_fw_v1 | 5_1_grt | 5.1 | last meaningful line 0.5 h ago (277/1095 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_1_grt | 6.7 | last meaningful line 0.1 h ago (2114/2120 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | 4_1_cts | 3.6 | last meaningful line 0.2 h ago (5103/5103 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2793057 | sle_stm_v1 | 5_2_route | 6.3 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_1_grt | 5.7 | last meaningful line 0.5 h ago (1282/2411 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_1_grt | 5.7 | last meaningful line 0.3 h ago (1283/1859 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 5_1_grt | 5.7 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | 4_1_cts | 4.3 | last meaningful line 0.1 h ago (5523/5523 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | pregrt_ff_hold | 3.5 | repair_TNS best 25913.4 last 25913.4 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | 4_1_cts | 2.4 | last meaningful line 0.0 h ago (4903/4903 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-slw_stm_v1__cle34a73c3-4063338 | slw_stm_v1 | postcts_gate_FF | 5.5 | last meaningful line 0.1 h ago (1552/1552 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | otc-901577-23707 | 901577 | signoff | 1.8 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | qc-colls-lec-h2 | qc-colls-lec-h2 | - | 3.0 |  | NO-DATA: no log found |  |
| epyc10 | qc-hc3-lec-r8-nearest | qc-hc3-lec-r8-nearest | - | 1.5 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R8_hc3_pvcca | relec-r2-R8_hc3_pvcca | - | 5.5 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-U3_pv97423966 | relec-r2-U3_pv97423966 | - | 3.4 |  | NO-DATA: no log found |  |
| epyc10 | smp-3633409 | smp | - | 0.0 |  | NO-DATA: no log found |  |
| epyc11 | ap-ageom-kw-kv3-hg-v1p3--r8c662a835-grt-2958608 | kv3-hg-v1p3--r8c662a835-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-kv3_pc_v1__cl4ea58a5c__r8c9cba7ae-2727555 | kv3_pc_v1 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.1 h ago (56/56 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_1_grt | 7.0 | last meaningful line 0.1 h ago (2659/2665 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 4_1_cts | 2.6 | last meaningful line 0.0 h ago (5963/5963 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 4_1_cts | 3.6 | last meaningful line 0.2 h ago (5485/5485 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | postcts_gate_TT | 7.0 | last meaningful line 0.0 h ago (774/774 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 4_1_cts | 2.3 | last meaningful line 0.2 h ago (5803/5803 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | postcts_gate_TT | 6.8 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | postcts_gate_TT | 7.0 | last meaningful line 0.0 h ago (1173/1173 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc2__cl6bcaba89-3858415 | slw_hc2 | 5_2_route | 7.3 | last meaningful line 0.1 h ago (275/276 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2533872 | slw_hc3 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (4973/4973 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3838177 | slw_hc3 | generate_abstract | 7.3 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | postcts_gate_TT | 6.8 | last meaningful line -0.0 h ago (83282/83282 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-320042 | slw_st_b_v2 | 5_2_route | 6.8 | last meaningful line 0.1 h ago (129/129 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 6.0 |  | NO-DATA: no log found |  |
| epyc11 | prd-eco_20261124_154417_1016084-i1-3808110 | eco_20261124_154417_1016084-i1 | 5_2_route | 3.6 | drt_violations best 80 last 80 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i1t-3010529 | eco_20261124_200101_1087713-i1t | 5_3_fillcell | 4.4 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_204246_1187010-i1t-3648808 | eco_20261124_204246_1187010-i1t | 5_2_route | 3.7 | drt_violations best 15305 last 15305 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc11 | prd-fin-2053304 | fin | 6_report | 0.3 | last meaningful line 0.1 h ago (942/942 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-hd_host_w-3495503 | hd_host_w | pregrt_ff_hold | 0.4 | repair_TNS best 39432.2 last 39432.2 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-kv3_hgi_v2__cle0015330-2015173 | kv3_hgi_v2 | 5_1_grt | 1.3 | last meaningful line 0.5 h ago (288/1296 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v6-3286735 | kv3_hgi_v6 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (400/400 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-1457043 | kv3_hroot | 5_2_route | 1.6 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Wo-1888444 | kv3_hub_Wo | 3_3_place_gp | 1.4 | overflow best 0.0994 last 0.0994 rows 46 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3272034 | sle_hc0 | 3_3_place_gp | 0.6 | overflow best 0.0994 last 0.0994 rows 52 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-491987 | sle_hc0 | 5_1_grt | 5.4 | last meaningful line 0.0 h ago (902/906 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-1254949 | sle_hc2 | 5_1_grt | 5.0 | last meaningful line 0.2 h ago (286/980 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3414126 | sle_hc2 | 5_2_route | 6.4 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__clcc5e3e61-3434617 | sle_hc2 | postcts_gate_FF | 6.4 | last meaningful line 0.0 h ago (710/710 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-1784944 | sle_st_a_v1 | 5_2_route | 7.4 | drt_violations best 72 last 72 rows 50 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-1826228 | sle_st_a_v1 | 5_2_route | 7.4 | drt_violations best 72 last 72 rows 45 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-1538145 | sle_st_a_v2 | 5_2_route | 7.6 | drt_violations best 72 last 72 rows 54 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3668964 | sle_st_b_v2 | 3_3_place_gp | 0.3 | overflow best 0.5987 last 0.5987 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-4153401 | sle_stm_v2 | 5_2_route | 5.9 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v3-1868496 | sle_stm_v3 | generate_abstract | 7.4 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-4191516 | slw_fw_v2 | 5_1_grt | 5.8 | repair_Remaining best 334464 last 334464 rows 63 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1101031 | slw_hc3 | postcts_gate_TT | 5.0 | last meaningful line 0.1 h ago (477/477 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3626034 | slw_hc3 | 5_2_route | 6.2 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1494307 | slw_st_a_v1 | 5_2_route | 7.7 | drt_violations best 72 last 72 rows 43 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-1494646 | slw_st_a_v2 | 5_2_route | 7.7 | drt_violations best 72 last 72 rows 40 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3657462 | slw_stm_v2 | postcts_gate_FF | 6.2 | last meaningful line -0.0 h ago (28803/28803 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 5.2 |  | NO-DATA: no log found |  |
| epyc2 | so_4037665_ff_28537 | so_4037665_ff_28537 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (1034/1034 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | so_4037665_tt_28537 | so_4037665_tt_28537 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (1034/1034 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 11.7 | last meaningful line 0.8 h ago (273/274 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 7.1 | last meaningful line 0.3 h ago (271/272 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | postcts_gate_TT | 7.3 | last meaningful line 0.0 h ago (498/498 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | 6_report | 12.9 | last meaningful line 0.0 h ago (75/75 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl1bc59e1c-2061343 | slw_hc0 | tt_setup_repair_grt | 7.2 | last meaningful line 0.0 h ago (554/554 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | postcts_gate_TT | 7.2 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 5_1_grt | 7.3 | last meaningful line 0.1 h ago (1090/1124 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-2253577 | slw_hc2 | postcts_gate_FF | 7.1 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 11.5 | last meaningful line 0.5 h ago (280/281 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | postcts_gate_FF | 7.2 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | 5_2_route | 11.5 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | 5_2_route | 7.1 | last meaningful line 0.1 h ago (260/261 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i2t-864737 | eco_20261124_175441_992552-i2t | 5_1_grt | 0.1 | last meaningful line 0.1 h ago (294/1294 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i1t-1220925 | eco_20261124_192157_3493836-i1t | 5_2_route | 5.1 | drt_violations best 1 last 1 rows 4 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i1t-231566 | eco_20261124_235631_1843084-i1t | 5_2_route | 0.5 | last meaningful line 0.0 h ago (247/247 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795561668594539576-i1-3034100 | eco_retry_1795561668594539576-i1 | 5_2_route | 1.3 | last meaningful line 0.0 h ago (264/264 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-fin-1611651 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 5_2_route | 8.4 | last meaningful line 0.1 h ago (135/135 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | postcts_gate_TT | 8.4 | last meaningful line 0.2 h ago (768/768 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | postcts_gate_TT | 8.4 | last meaningful line 0.1 h ago (391/391 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | postcts_gate_FF | 8.4 | last meaningful line 0.2 h ago (789/789 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | postcts_gate_FF | 8.4 | last meaningful line 0.2 h ago (762/762 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 8.3 | last meaningful line 0.3 h ago (265/266 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | postcts_gate_TT | 8.4 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | postcts_gate_TT | 8.4 | last meaningful line -0.0 h ago (40177/40177 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | postcts_gate_TT | 8.4 | last meaningful line -0.0 h ago (62964/62964 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | 5_2_route | 8.4 | last meaningful line 0.5 h ago (275/276 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l0__cl7a55c676-4020210 | sle_su_l0 | 5_2_route | 8.4 | drt_violations best 5 last 5 rows 15 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_1_grt | 8.4 | last meaningful line 0.0 h ago (2594/2594 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | postcts_gate_TT | 8.4 | last meaningful line 0.3 h ago (843/843 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | postcts_gate_FF | 8.4 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | postcts_gate_TT | 8.4 | last meaningful line 0.0 h ago (829/829 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | 5_2_route | 11.7 | drt_violations best 12852 last 12852 rows 2 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | 5_2_route | 8.4 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3909116 | slw_hc3 | 5_2_route | 8.4 | drt_violations best 88102 last 88102 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-3949912 | slw_hc3 | 5_2_route | 8.4 | drt_violations best 80626 last 80626 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 8.3 | last meaningful line 0.5 h ago (269/270 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 8.3 | last meaningful line 0.3 h ago (279/280 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | 5_2_route | 8.4 | drt_violations best 21189 last 21189 rows 3 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 5_2_route | 8.4 | drt_violations best 74 last 74 rows 32 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | postcts_gate_TT | 8.4 | last meaningful line 0.2 h ago (561/561 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | otc-2900322-1356 | 2900322 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3t-2289287 | eco_20261123_164145_1995767-i3t | 5_2_route | 5.8 | drt_violations best 35664 last 35664 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261124_225649_3846510-i1-114505 | eco_20261124_225649_3846510-i1 | 5_2_route | 1.5 | last meaningful line 0.1 h ago (257/258 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 5.3 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R1b_coll_old | relec-r2-R1b_coll_old | - | 5.2 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R4_coll_guard | relec-r2-R4_coll_guard | - | 5.2 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R9_hc3_d5fde | relec-r2-R9_hc3_d5fde | - | 5.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 5.1 | drt_violations best 84487 last 84487 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | 4_1_cts | 4.7 | last meaningful line 0.3 h ago (11146/11146 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_1_grt | 5.4 | repair_Remaining best 92532 last 92532 rows 314 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-551472 | slw_fw_v1 | 5_1_grt | 5.5 | last meaningful line 0.6 h ago (290/1845 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v2__cl8537f156-601723 | slw_fw_v2 | 5_1_grt | 5.4 | last meaningful line 0.3 h ago (2895/2923 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | otc-2479768-4454 | 2479768 | ot_bind_native_2cf149e0c3b5ae6ac78c6a97 | 0.0 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-2479830-17406 | 2479830 | gen_lint_yosys | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | prd-eco_20261123_224216_149959-i3-3801930 | eco_20261123_224216_149959-i3 | 5_2_route | 3.2 | drt_violations best 24 last 24 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-coll_core-3813096 | coll_core | 5_1_grt | 6.4 | last meaningful line 1.0 h ago (1298/2890 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v4-3072149 | kv3_hgi_v4 | 5_1_grt | 4.0 | last meaningful line 0.8 h ago (292/1301 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Eo-371567 | kv3_hub_Eo | 2_1_floorplan | 0.4 | last meaningful line 0.3 h ago (109/109 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-1090401 | kv3_pc_v1 | synth_odb_v | 0.1 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | postcts_gate_TT | 11.5 | last meaningful line -0.0 h ago (78010/78010 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 5_1_grt | 7.1 | last meaningful line 0.1 h ago (961/974 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-3662089 | sle_sc_v1 | postcts_gate_TT | 6.5 | last meaningful line -0.0 h ago (47719/47719 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 4_1_cts | 3.5 | last meaningful line 0.3 h ago (5646/5646 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | postcts_gate_FF | 5.2 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | postcts_gate_FF | 3.4 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 4_1_cts | 0.9 | last meaningful line 0.2 h ago (5443/5443 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | 5_2_route | 9.5 | drt_violations best 234054 last 234054 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3325358 | slw_fw_v1 | 4_1_cts | 0.9 | last meaningful line 0.2 h ago (5277/5277 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 11.4 | last meaningful line 0.5 h ago (265/266 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 4_1_cts | 2.0 | last meaningful line 0.1 h ago (5248/5248 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2360221 | slw_hc2 | pregrt_ff_hold | 4.5 | repair_TNS best 6157.41 last 6157.41 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 4_1_cts | 3.2 | last meaningful line 0.1 h ago (5107/5107 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3890746 | slw_sc_v1 | 5_1_grt | 3.5 | last meaningful line 0.2 h ago (145/145 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 5_1_grt | 7.1 | last meaningful line 0.2 h ago (1142/1155 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (4967/4967 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | 5_2_route | 11.4 | last meaningful line 0.3 h ago (272/273 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | postcts_gate_TT | 7.1 | last meaningful line 0.1 h ago (1498/1498 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1e5219ea-4177722 | slw_su_l0 | postcts_gate_FF | 3.3 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-3090069 | slw_su_l0 | pregrt_ff_hold | 1.0 | repair_TNS best 222530 last 222530 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-tt_ctlm-3234028 | tt_ctlm | tt_setup_repair | 1.0 | repair_Remaining best 132990 last 132990 rows 175 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 5.3 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 5.3 |  | NO-DATA: no log found |  |
| intel1 | otc-3854277-21865 | 3854277 | - | 9.2 |  | NO-DATA: no log found |  |
| intel1 | prd-count-p1_bc-2852283 | count-p1_bc | prd_count_p1_bc | 0.1 | last meaningful line 0.0 h ago (842/842 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_ctl-2153206 | hd_ctl | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_1_grt | 6.9 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | postcts_gate_TT | 7.1 | last meaningful line 0.1 h ago (1852/1852 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-660000 | sle_hc0 | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | pregrt_ff_hold | 4.0 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1583204 | sle_st_b_v1 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | 5_1_grt | 4.5 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_st_b_v2__clfde1249e-689859 | sle_st_b_v2 | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-856398 | slw_st_b_v1 | pregrt_ff_hold | 4.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | pregrt_ff_hold | 5.0 | repair_Violations best 1778 last 1778 rows 19 | before-window best 50245, window best 1778 | PROGRESS: repair_Violations improved 96.5 % in window |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 19.4 | drt_violations best 16673 last 16673 rows 14 | before-window best 23959, window best 16673 | PROGRESS: drt_violations improved 30.4 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 11.8 | drt_violations best 1743 last 5229 rows 18 | before-window best 2657, window best 1743 | PROGRESS: drt_violations improved 34.4 % in window |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 11.7 | drt_violations best 123388 last 123388 rows 2 | before-window best 521993, window best 123388 | PROGRESS: drt_violations improved 76.4 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 38.8 | drt_violations best 10129 last 48097 rows 18 | before-window best 14975, window best 10129 | PROGRESS: drt_violations improved 32.4 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 32.1 | drt_violations best 7726 last 7726 rows 17 | before-window best 15355, window best 7726 | PROGRESS: drt_violations improved 49.7 % in window |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-2222980 | sle_fw_v2 | 5_1_grt | 7.1 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 16.9 | drt_violations best 10524 last 10524 rows 7 | before-window best 490378, window best 10524 | PROGRESS: drt_violations improved 97.9 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 13.0 | drt_violations best 504597 last 504597 rows 1 | before-window best 504597, window best 504597 | PROGRESS: drt_violations: active iteration at 278306 < best completed total 504597 (in-ite |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 17.1 | drt_violations best 68064 last 68064 rows 6 | before-window best 407677, window best 68064 | PROGRESS: drt_violations improved 83.3 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 13.2 | drt_violations best 123176 last 123176 rows 2 | before-window best 400194, window best 123176 | PROGRESS: drt_violations improved 69.2 % in window |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | 5_2_route | 13.2 | drt_violations best 12062 last 12062 rows 3 | before-window best 126854, window best 12062 | PROGRESS: drt_violations improved 90.5 % in window |  |
| epyc7 | prd-eco_20261123_171023_3055226-i3t-3392092 | eco_20261123_171023_3055226-i3t | 5_2_route | 6.4 | drt_violations best 0 last 0 rows 3 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_1_grt | 8.4 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-4063882 | sle_st_a_v2 | 5_2_route | 8.4 | drt_violations best 72 last 72 rows 54 | before-window best 142170, window best 72 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 8.4 | drt_violations best 26414 last 26414 rows 6 | before-window best 274214, window best 26414 | PROGRESS: drt_violations improved 90.4 % in window |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_1_grt | 5.3 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-1010348 | sle_fw_v1 | 5_1_grt | 5.1 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_fw_v1__clf58b4dfb-733846 | sle_fw_v1 | 5_1_grt | 5.3 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-667540 | sle_hc1 | 5_1_grt | 5.4 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_fw_v3-1442734 | sle_fw_v3 | 5_1_grt | 5.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-slw_fw_v3-1399930 | slw_fw_v3 | 5_1_grt | 5.2 | repair_TNS best 0 last 0 rows 14 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2160450 | slw_hc3 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
