# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 17:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'UNSIGNABLE': 1, 'GRT-LABEL': 5, 'YOUNG': 173, 'NO-DATA': 18, 'PROGRESS': 28}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 8.8 | last meaningful line 7.5 h ago (48/134 lines) | NO-PROGRESS: no new non-iteration log line for 7.5 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 11.9 | last meaningful line 8.3 h ago (48/191 lines) | NO-PROGRESS: no new non-iteration log line for 8.3 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 4.1 | repair_TNS best 827598 last 827598 rows 1 | before-window best 827598, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 5_1_grt | 10.8 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2160450 | slw_hc3 | pregrt_ff_hold | 6.1 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 5_1_grt | 9.1 | grt rounds 1 overflow 5:42234 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv_v2n-1048434 | kv3_pv_v2n | 5_1_grt | 8.9 | grt rounds 2 overflow 5:64147 -> 10:49031 | GRT-LABEL: DESIGN-FAIL: overflow 49031 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v6-908877 | kv3_pv_v6 | 5_1_grt | 9.0 | grt rounds 2 overflow 5:56449 -> 10:44954 | GRT-LABEL: DESIGN-FAIL: overflow 44954 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | 5_1_grt | 6.2 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 5_1_grt | 10.4 | grt rounds 2 overflow 5:83232 -> 10:63283 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-kv3-hg-v1p2-grt-1436471 | kv3-hg-v1p2-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | ap-ageom-kw-kv3-hg-v1p3--r81da466fe-grt-1498584 | kv3-hg-v1p3--r81da466fe-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | ap-ageom-kw-kv3-hg-v1p3--r838481cd7-grt-1401251 | kv3-hg-v1p3--r838481cd7-grt | 3_5_place_dp | 0.2 | last meaningful line 0.2 h ago (141/141 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-glue-1294589 | glue | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (5403/5403 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | 5_2_route | 5.7 | drt_violations best 3764 last 3764 rows 10 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r889141819-1619104 | kv3_hg_v1__r889141819 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-373156 | kv3_hgi | 5_1_grt | 0.7 | last meaningful line 0.0 h ago (282/295 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-477047 | kv3_hgi | 5_1_grt | 0.6 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-477535 | kv3_hgi_v2 | pregrt_ff_hold | 0.6 | repair_TNS best 101.71 last 101.71 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-560078 | kv3_hgi_v2 | pregrt_ff_hold | 0.6 | repair_TNS best 22982.5 last 22982.5 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | 4_1_cts | 0.3 | last meaningful line 0.3 h ago (46/46 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-1076148 | kv3_pc | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (61/61 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r8b421e514-1086873 | kv3_pc | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (61/61 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r85c02c25c-1098684 | kv3_pc | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r882954158-1102222 | kv3_pc | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r884969661-565445 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.8675 last 0.8675 rows 7 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl7f648944__r8422a4b86-167807 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.3918 last 0.3918 rows 37 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | 5_1_grt | 9.0 | last meaningful line 1.0 h ago (270/1278 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | pregrt_ff_hold | 4.2 | repair_TNS best 46556.5 last 46556.5 rows 1 | YOUNG: evidence 1.6 h < 2.5 h |  |
| epyc10 | dpkit-native59-3512619 | native59 | 3_3_place_gp | 1.4 | overflow best 0.0992 last 0.0992 rows 152 | YOUNG: stage 0.7 h < 1 h |  |
| epyc10 | dpkit-sle_fw_v1__clf58b4dfb-461721 | sle_fw_v1 | tt_setup_repair_grt | 6.3 | last meaningful line 0.0 h ago (773/773 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | postcts_gate_TT | 8.0 | last meaningful line 0.1 h ago (861/861 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | 5_1_grt | 4.8 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | 5_1_grt | 5.2 | last meaningful line 0.0 h ago (1163/1166 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | postcts_gate_TT | 5.8 | last meaningful line 0.0 h ago (504/504 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2793057 | sle_stm_v1 | 5_2_route | 7.5 | last meaningful line 0.2 h ago (282/283 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_1_grt | 6.9 | last meaningful line 0.1 h ago (1939/1951 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 5_1_grt | 7.0 | last meaningful line 0.3 h ago (1915/1928 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3681869 | slw_st_b_v2 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (4707/4707 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | 5_1_grt | 3.7 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_stm_v1__cle34a73c3-4063338 | slw_stm_v1 | 5_2_route | 6.7 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | otc-901577-23707 | 901577 | signoff | 3.0 | last meaningful line 3.0 h ago (3/3 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc10 | qc-colls-lec-h3 | qc-colls-lec-h3 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc10 | qc-hc3-lec-r8-nearest | qc-hc3-lec-r8-nearest | - | 2.7 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R8_hc3_pvcca | relec-r2-R8_hc3_pvcca | - | 6.7 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | postcts_gate_TT | 8.2 | last meaningful line -0.0 h ago (90768/90768 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 4_1_cts | 3.8 | last meaningful line 0.0 h ago (6141/6141 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 5_1_grt | 4.8 | repair_Remaining best 258 last 258 rows 484 | YOUNG: stage 0.5 h < 1 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | 5_2_route | 8.3 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 4_1_cts | 3.5 | last meaningful line 0.2 h ago (5909/5909 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | postcts_gate_FF | 8.1 | last meaningful line -0.0 h ago (63241/63241 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | 5_2_route | 8.2 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc2__cl6bcaba89-3858415 | slw_hc2 | 5_2_route | 8.6 | drt_violations best 12765 last 12765 rows 2 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2533872 | slw_hc3 | pregrt_ff_hold | 1.9 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4075873 | slw_st_b_v1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (228/228 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | 5_2_route | 8.0 | last meaningful line 0.1 h ago (265/266 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-320042 | slw_st_b_v2 | 5_2_route | 8.0 | drt_violations best 128395 last 128395 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc11 | eco-abs-3915629 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 7.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-3389445-25127 | 3389445 | signoff | 0.8 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i1-3176761 | eco_20261124_190641_1260390-i1 | 5_1_grt | 1.1 | last meaningful line 0.7 h ago (240/1472 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i1-3660942 | eco_20261124_200101_1087713-i1 | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (246/471 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | prd-fin-3648808 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (51/51 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-1457043 | kv3_hroot | 5_2_route | 2.9 | drt_violations best 40861 last 40861 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Wo-1888444 | kv3_hub_Wo | 3_5_place_dp | 2.6 | last meaningful line 0.3 h ago (117/117 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-491987 | sle_hc0 | postcts_gate_FF | 6.7 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-1254949 | sle_hc2 | postcts_gate_TT | 6.2 | last meaningful line 0.1 h ago (776/776 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3414126 | sle_hc2 | 5_2_route | 7.6 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__clcc5e3e61-3434617 | sle_hc2 | 5_2_route | 7.6 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-1784944 | sle_st_a_v1 | generate_abstract | 8.7 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-1826228 | sle_st_a_v1 | 5_2_route | 8.7 | drt_violations best 72 last 72 rows 54 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3668964 | sle_st_b_v2 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (5587/5587 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-4153401 | sle_stm_v2 | 5_2_route | 7.1 | drt_violations best 159333 last 159333 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-4191516 | slw_fw_v2 | 5_1_grt | 7.1 | last meaningful line 0.1 h ago (2840/2857 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1101031 | slw_hc3 | 5_2_route | 6.3 | last meaningful line 0.2 h ago (265/266 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3626034 | slw_hc3 | 5_2_route | 7.5 | drt_violations best 9124 last 9124 rows 2 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3657462 | slw_stm_v2 | 5_2_route | 7.4 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_165709_1862160-i1t-580795 | eco_20261124_165709_1862160-i1t | 5_2_route | 0.8 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 6.4 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-1559108 | cbn_q01 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (7641/7641 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 4_1_cts | 1.1 | last meaningful line 0.3 h ago (10685/10685 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-2222980 | sle_fw_v2 | 5_1_grt | 8.4 | last meaningful line 0.4 h ago (2123/2136 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 12.9 | drt_violations best 510309 last 510309 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 8.3 | last meaningful line 0.5 h ago (279/280 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | postcts_gate_FF | 8.6 | last meaningful line 0.0 h ago (1078/1078 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | postcts_gate_TT | 8.4 | last meaningful line -0.0 h ago (51191/51191 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | postcts_gate_TT | 8.5 | last meaningful line 0.2 h ago (840/840 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-2253577 | slw_hc2 | 5_2_route | 8.4 | last meaningful line 0.2 h ago (137/137 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-1524868 | slw_sc_v1 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (4583/4583 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 12.7 | drt_violations best 457993 last 457993 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-2092169 | slw_sc_v1 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (5494/5494 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | 5_2_route | 8.5 | last meaningful line 0.1 h ago (131/131 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | 5_2_route | 12.8 | drt_violations best 122101 last 122101 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | 5_2_route | 8.4 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | otc-2728966-29287 | 2728966 | signoff | 0.3 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i3-2609460 | eco_20261123_171023_3055226-i3 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (140/140 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_145005_2036075-i2-1496134 | eco_20261124_145005_2036075-i2 | 5_2_route | 1.0 | last meaningful line 0.0 h ago (251/251 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i2t-864737 | eco_20261124_175441_992552-i2t | 5_2_route | 1.4 | drt_violations best 39965 last 39965 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i1-2124005 | eco_20261124_192157_3493836-i1 | 5_1_grt | 0.7 | last meaningful line 0.3 h ago (295/345 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i1t-231566 | eco_20261124_235631_1843084-i1t | 5_2_route | 1.8 | drt_violations best 201478 last 201478 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | so_3154245_ff_50484 | so_3154245_ff_50484 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | so_3154245_tt_50484 | so_3154245_tt_50484 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_1_grt | 9.6 | last meaningful line 0.3 h ago (2659/2676 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 5_2_route | 9.6 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | postcts_gate_FF | 9.6 | last meaningful line 0.1 h ago (770/770 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | postcts_gate_FF | 9.6 | last meaningful line 0.0 h ago (389/389 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | 5_2_route | 9.7 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | 5_2_route | 9.7 | last meaningful line 0.2 h ago (258/259 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 9.6 | last meaningful line 0.5 h ago (271/272 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | postcts_gate_FF | 9.6 | last meaningful line 0.0 h ago (524/524 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 5_2_route | 9.6 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | 5_2_route | 9.6 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | 5_2_route | 9.6 | drt_violations best 160491 last 160491 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | postcts_gate_TT | 9.6 | last meaningful line 0.1 h ago (852/852 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | postcts_gate_FF | 9.6 | last meaningful line 0.2 h ago (824/824 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | postcts_gate_TT | 9.6 | last meaningful line -0.0 h ago (79551/79551 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | postcts_gate_FF | 9.6 | last meaningful line 0.1 h ago (835/835 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | 6_report | 12.9 | last meaningful line 0.2 h ago (71/71 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | 5_2_route | 9.7 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3909116 | slw_hc3 | 5_2_route | 9.7 | drt_violations best 9503 last 9503 rows 2 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-3949912 | slw_hc3 | 6_report | 9.6 | last meaningful line 0.2 h ago (71/71 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 9.6 | last meaningful line 0.5 h ago (275/276 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 9.5 | drt_violations best 379431 last 379431 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | 5_2_route | 9.6 | drt_violations best 383 last 383 rows 13 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | postcts_gate_FF | 9.6 | last meaningful line 0.1 h ago (1213/1213 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | otc-2900322-1356 | 2900322 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_012701_4018610-i1-2166955 | eco_20261125_012701_4018610-i1 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 6.5 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R9_hc3_d5fde | relec-r2-R9_hc3_d5fde | - | 6.4 |  | NO-DATA: no log found |  |
| epyc8 | so_2294744_ff_47180 | so_2294744_ff_47180 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc8 | so_2294744_tt_47180 | so_2294744_tt_47180 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc9 | ap-ageom-kw-slice-station--t38-grt-1881033 | slice-station--t38-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvd8c0565f-1822200 | col_h10_r0_p4__t1 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv6882e5ea-3887067 | col_h9_r0_p2__t1 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1420478 | col_h9_r0_p2__t1 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (1536/1536 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-1649671 | col_h9_r0_p2__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 663 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pvef55eb84-1795459 | col_h9_r0_p2__t1 | 2_1_floorplan | 0.1 | last meaningful line -0.0 h ago (7/7 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv4cfde03b-503899 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.4 | last meaningful line -0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b-3581353 | col_h9_r0_p3__t1 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-270204 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.5 | overflow best 0.4507 last 0.4507 rows 5 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-948912 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8644 last 0.8695 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-1091008 | col_h9_r0_p4__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.7205 last 0.7205 rows 20 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-1118770 | col_h9_r0_p4__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.7882 last 0.8304 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-944417 | col_h9_r0_p4__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.2504 last 0.2504 rows 34 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-1612646 | col_h9_r0_p5__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 447 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-823228 | col_h9_r0_p5__t1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.4284 last 0.4284 rows 30 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-820075 | col_h9_r2__t1 | 3_5_place_dp | 0.4 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv7c30fd4e-1812218 | col_h9_r2__t1 | 2_1_floorplan | 0.0 | repair_Viol best 2770 last 2770 rows 186 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 6.3 | drt_violations best 1917 last 1917 rows 6 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t13-1595964 | serdes__t13 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (315/315 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | pregrt_ff_hold | 6.0 | repair_TNS best 303873 last 303873 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-667540 | sle_hc1 | postcts_gate_TT | 6.6 | last meaningful line 0.0 h ago (818/818 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t44-1088426 | slice_station__t44 | 3_3_place_gp | 0.3 | overflow best 0.256 last 0.2688 rows 39 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slice_station__t52-1509646 | slice_station__t52 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-551472 | slw_fw_v1 | tt_setup_repair_grt | 6.7 | repair_Viol best 51 last 51 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slw_fw_v2__cl8537f156-601723 | slw_fw_v2 | postcts_gate_FF | 6.7 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-1399673-10074 | 1399673 | gen_lint_yosys | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-1420782-26237 | 1420782 | gen_lint_yosys | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-1560357-22328 | 1560357 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-442459-15670 | 442459 | gen_lint_yosys | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i3-3801930 | eco_20261123_224216_149959-i3 | 5_2_route | 4.4 | drt_violations best 24 last 24 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v6-102352 | kv3_hgi_v6 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5932/5932 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Eo-371567 | kv3_hub_Eo | 3_3_place_gp | 1.9 | overflow best 0.0994 last 0.0994 rows 44 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-kv3_pc_v1__cl4ea58a5c__r877307f5d-453397 | kv3_pc_v1 | 2_1_floorplan | 0.2 | repair_Viol best 8517 last 8517 rows 74 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | postcts_gate_FF | 13.0 | last meaningful line -0.0 h ago (30086/30086 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | postcts_gate_TT | 8.6 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (414/414 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | pregrt_ff_hold | 5.0 | repair_TNS best 22328.5 last 22328.5 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | postcts_gate_FF | 6.7 | last meaningful line 0.1 h ago (1673/1673 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 4.9 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 4_1_cts | 2.4 | last meaningful line 0.3 h ago (5587/5587 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3325358 | slw_fw_v1 | 4_1_cts | 2.4 | last meaningful line 0.1 h ago (5408/5408 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 12.9 | last meaningful line 0.5 h ago (273/274 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v3-1399930 | slw_fw_v3 | postcts_gate_TT | 6.7 | last meaningful line 0.2 h ago (903/903 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 4_1_cts | 3.5 | last meaningful line 0.0 h ago (5360/5360 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | pregrt_ff_hold | 4.7 | repair_TNS best 27413.8 last 27413.8 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3890746 | slw_sc_v1 | 5_1_grt | 5.0 | last meaningful line 0.2 h ago (2021/2071 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | postcts_gate_TT | 8.6 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 4_1_cts | 3.2 | last meaningful line 0.1 h ago (5166/5166 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | 5_2_route | 12.9 | drt_violations best 156960 last 156960 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 5_2_route | 8.6 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1e5219ea-4177722 | slw_su_l0 | 5_2_route | 4.8 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 6.8 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 6.8 |  | NO-DATA: no log found |  |
| intel1 | otc-2434312-2110 | 2434312 | flow | 1.0 | last meaningful line 0.1 h ago (2885/2885 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | otc-3192080-15624 | 3192080 | eq10 | 0.8 | last meaningful line 0.5 h ago (517751/517751 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2240258 | coll_ftm | 5_2_route | 1.2 | last meaningful line 0.1 h ago (230/231 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-hd_ctl-2153206 | hd_ctl | 5_1_grt | 1.3 | last meaningful line 0.2 h ago (274/1196 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-hd_host_w-4051042 | hd_host_w | 3_3_place_gp | 0.2 | overflow best 0.7349 last 0.7349 rows 7 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-3912254 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (214/215 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_hgi_v8-2986000 | kv3_hgi_v8 | 3_3_place_gp | 0.8 | overflow best 0.1 last 0.1 rows 48 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-kv3_io_ft-2239522 | kv3_io_ft | 5_2_route | 1.2 | drt_violations best 5442 last 5442 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_1_grt | 8.1 | last meaningful line 0.1 h ago (2007/2013 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 5_2_route | 8.3 | last meaningful line 0.0 h ago (263/263 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3215525 | slw_sc_v1 | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (384/384 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-2390236 | slw_st_b_v1 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (5224/5224 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | ffx-4094762 | ffx | generate_abstract | 0.1 | last meaningful line 0.1 h ago (605/605 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | ffx-4116728 | ffx | generate_abstract | 0.1 | last meaningful line 0.0 h ago (528/528 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | ffx-4127189 | ffx | generate_abstract | 0.1 | last meaningful line 0.1 h ago (349/349 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | so_113868_ff_91764 | so_113868_ff_91764 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_113868_tt_91764 | so_113868_tt_91764 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-660000 | sle_hc0 | pregrt_ff_hold | 6.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1583204 | sle_st_b_v1 | pregrt_ff_hold | 5.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_1_grt | 6.9 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | pregrt_ff_hold | 5.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | 5_1_grt | 4.7 | repair_TNS best 0 last 0 rows 4 | PROGRESS: repair_TNS reached 0 |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 20.7 | drt_violations best 15812 last 15812 rows 15 | before-window best 21399, window best 15812 | PROGRESS: drt_violations improved 26.1 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 13.1 | drt_violations best 1743 last 2528 rows 19 | before-window best 1983, window best 1743 | PROGRESS: drt_violations improved 12.1 % in window |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 13.0 | drt_violations best 88579 last 88579 rows 3 | before-window best 521993, window best 88579 | PROGRESS: drt_violations improved 83.0 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1494307 | slw_st_a_v1 | 5_2_route | 8.9 | drt_violations best 72 last 72 rows 55 | before-window best 133674, window best 72 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-1494646 | slw_st_a_v2 | 5_2_route | 8.9 | drt_violations best 72 last 72 rows 54 | before-window best 99922, window best 72 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 40.1 | drt_violations best 10129 last 48097 rows 18 | before-window best 13426, window best 10129 | PROGRESS: drt_violations improved 24.6 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 33.4 | drt_violations best 7726 last 31531 rows 18 | before-window best 15355, window best 7726 | PROGRESS: drt_violations improved 49.7 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 18.1 | drt_violations best 7491 last 7491 rows 10 | before-window best 490378, window best 7491 | PROGRESS: drt_violations improved 98.5 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 14.3 | drt_violations best 504597 last 504597 rows 1 | before-window best 504597, window best 504597 | PROGRESS: drt_violations: active iteration at 141415 < best completed total 504597 (in-ite |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 18.3 | drt_violations best 67058 last 67058 rows 7 | before-window best 141373, window best 67058 | PROGRESS: drt_violations improved 52.6 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 14.4 | drt_violations best 102681 last 102681 rows 3 | before-window best 400194, window best 102681 | PROGRESS: drt_violations improved 74.3 % in window |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 5_2_route | 9.6 | drt_violations best 72 last 72 rows 50 | before-window best 146485, window best 72 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 9.6 | drt_violations best 23879 last 23879 rows 8 | before-window best 274214, window best 23879 | PROGRESS: drt_violations improved 91.3 % in window |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3t-2289287 | eco_20261123_164145_1995767-i3t | 5_2_route | 7.1 | drt_violations best 42 last 42 rows 8 | before-window best 35664, window best 42 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc8 | prd-eco_20261124_225649_3846510-i1-114505 | eco_20261124_225649_3846510-i1 | 5_2_route | 2.8 | drt_violations best 0 last 0 rows 4 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_1_grt | 6.5 | repair_TNS best 0 last 0 rows 20 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_1_grt | 6.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-coll_core-3813096 | coll_core | 5_1_grt | 7.9 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_fw_v3-1442734 | sle_fw_v3 | 5_1_grt | 6.7 | repair_TNS best 0 last 0 rows 14 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | 5_2_route | 11.0 | drt_violations best 234054 last 234054 rows 1 | before-window best 234054, window best 234054 | PROGRESS: drt_violations: active iteration at 78239 < best completed total 234054 (in-iter |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2360221 | slw_hc2 | pregrt_ff_hold | 6.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-3090069 | slw_su_l0 | 5_1_grt | 2.5 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261123_191853_2879776-i2-2930338 | eco_20261123_191853_2879776-i2 | 5_1_grt | 0.9 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
