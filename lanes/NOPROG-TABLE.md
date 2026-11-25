# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 17:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 5, 'UNSIGNABLE': 1, 'GRT-LABEL': 5, 'YOUNG': 169, 'NO-DATA': 18, 'PROGRESS': 23}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 8.1 | last meaningful line 6.8 h ago (48/133 lines) | NO-PROGRESS: no new non-iteration log line for 6.8 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc10 | dpkit-sle_st_b_v2__clfde1249e-689859 | sle_st_b_v2 | pregrt_ff_hold | 5.4 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-856398 | slw_st_b_v1 | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 11.4 | last meaningful line 7.8 h ago (48/190 lines) | NO-PROGRESS: no new non-iteration log line for 7.8 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 3.6 | repair_TNS best 827598 last 827598 rows 1 | before-window best 827598, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 5_1_grt | 10.3 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 5_1_grt | 8.4 | grt rounds 1 overflow 5:42234 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv_v2n-1048434 | kv3_pv_v2n | 5_1_grt | 8.1 | grt rounds 2 overflow 5:64147 -> 10:49031 | GRT-LABEL: DESIGN-FAIL: overflow 49031 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v6-908877 | kv3_pv_v6 | 5_1_grt | 8.2 | grt rounds 2 overflow 5:56449 -> 10:44954 | GRT-LABEL: DESIGN-FAIL: overflow 44954 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | 5_1_grt | 5.8 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 5_1_grt | 9.9 | grt rounds 1 overflow 5:83232 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-kv3-hgi-grt-163073 | kv3-hgi-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | ap-ageom-kw-kv3-hgi-grt-67652 | kv3-hgi-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | ap-ageom-kw-kv3-hgi-v2--cl2862d491-grt-163432 | kv3-hgi-v2--cl2862d491-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | ap-ageom-kw-kv3-hgi-v2--cl2862d491-grt-237741 | kv3-hgi-v2--cl2862d491-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-glue-3579966 | glue | 3_3_place_gp | 0.6 | overflow best 0.3721 last 0.3721 rows 30 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | 5_2_route | 4.9 | drt_violations best 4220 last 4220 rows 5 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r889141819-3256830 | kv3_hg_v1__r889141819 | 3_3_place_gp | 0.7 | overflow best 0.3074 last 0.3074 rows 28 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-kv3_hg_v1__r88f4bfb40-3256090 | kv3_hg_v1__r88f4bfb40 | 3_3_place_gp | 0.7 | overflow best 0.4331 last 0.4331 rows 22 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-kv3_hg_v1__r8dffc461a-3274501 | kv3_hg_v1__r8dffc461a | 3_3_place_gp | 0.7 | overflow best 0.4728 last 0.4728 rows 18 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-kv3_hg_v1p2-3246486 | kv3_hg_v1p2 | 3_3_place_gp | 0.7 | overflow best 0.544 last 0.544 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_hg_v1p3__r81da466fe-3244974 | kv3_hg_v1p3__r81da466fe | 3_3_place_gp | 0.7 | overflow best 0.5593 last 0.5702 rows 4 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_hg_v1p3__r838481cd7-3239592 | kv3_hg_v1p3__r838481cd7 | 3_3_place_gp | 0.7 | overflow best 0.5377 last 0.545 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_hub_Wo-579995 | kv3_hub_Wo | 3_5_place_dp | 2.5 | last meaningful line 0.1 h ago (116/116 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl7f648944__r8422a4b86-167807 | kv3_pc_v1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (528/528 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | 5_1_grt | 8.2 | last meaningful line 0.3 h ago (270/1274 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | pregrt_ff_hold | 3.4 | repair_TNS best 46556.5 last 46556.5 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v7e-1156836 | kv3_pv_v7e | postcts_gate_TT | 8.0 | last meaningful line 0.3 h ago (2891/2891 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-native59-3512619 | native59 | 2_1_floorplan | 0.6 | last meaningful line 0.2 h ago (1360/1360 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | tt_setup_repair_grt | 7.2 | repair_Violations best 187 last 1023 rows 32 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | pregrt_ff_hold | 4.1 | repair_TNS best 18689 last 18689 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | 5_1_grt | 5.0 | last meaningful line 0.3 h ago (2188/2205 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2793057 | sle_stm_v1 | 5_2_route | 6.8 | last meaningful line 0.3 h ago (274/275 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_1_grt | 6.2 | last meaningful line 0.2 h ago (2444/2457 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 5_1_grt | 6.2 | last meaningful line 0.2 h ago (1281/1883 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | hold_gate | 4.8 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | 5_1_grt | 4.0 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3681869 | slw_st_b_v2 | 3_3_place_gp | 0.5 | overflow best 0.2161 last 0.2161 rows 39 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | tt_setup_measure | 2.9 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_stm_v1__cle34a73c3-4063338 | slw_stm_v1 | 5_2_route | 6.0 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-276187-2853 | 276187 | signoff | 0.0 | last meaningful line 0.0 h ago (3/3 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-901577-23707 | 901577 | signoff | 2.3 | last meaningful line 2.3 h ago (3/3 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | qc-colls-lec-h3 | qc-colls-lec-h3 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc10 | qc-hc3-lec-r8-nearest | qc-hc3-lec-r8-nearest | - | 2.0 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R8_hc3_pvcca | relec-r2-R8_hc3_pvcca | - | 6.0 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-U3_pv97423966 | relec-r2-U3_pv97423966 | - | 3.9 |  | NO-DATA: no log found |  |
| epyc10 | smp-280712 | smp | - | 0.0 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | postcts_gate_TT | 7.7 | last meaningful line 0.1 h ago (911/911 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 4_1_cts | 3.3 | last meaningful line 0.1 h ago (5994/5994 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 5_1_grt | 4.3 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | postcts_gate_FF | 7.8 | last meaningful line 0.1 h ago (770/770 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 4_1_cts | 3.0 | last meaningful line 0.1 h ago (5881/5881 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | postcts_gate_FF | 7.6 | last meaningful line 0.1 h ago (514/514 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | postcts_gate_FF | 7.7 | last meaningful line 0.1 h ago (1146/1146 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc2__cl6bcaba89-3858415 | slw_hc2 | 5_2_route | 8.1 | drt_violations best 99617 last 99617 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2533872 | slw_hc3 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (5074/5074 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | 5_2_route | 7.5 | last meaningful line 0.1 h ago (129/129 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-320042 | slw_st_b_v2 | 5_2_route | 7.5 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 6.7 |  | NO-DATA: no log found |  |
| epyc11 | otc-3389445-25127 | 3389445 | signoff | 0.3 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | prd-count-p1_tc-3648808 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i1-3176761 | eco_20261124_190641_1260390-i1 | 5_1_grt | 0.6 | last meaningful line 0.2 h ago (240/1257 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i1-3660942 | eco_20261124_200101_1087713-i1 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (89/89 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | prd-fin-3808110 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (1069/1069 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-hd_host_w-3495503 | hd_host_w | 5_1_grt | 1.2 | last meaningful line 0.0 h ago (164/164 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-1457043 | kv3_hroot | 5_2_route | 2.4 | last meaningful line 0.1 h ago (254/255 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Wo-1888444 | kv3_hub_Wo | 3_4_place_resized | 2.1 | last meaningful line 0.2 h ago (399/399 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-491987 | sle_hc0 | 5_1_grt | 6.2 | last meaningful line 0.1 h ago (1039/1056 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-1254949 | sle_hc2 | postcts_gate_TT | 5.7 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3414126 | sle_hc2 | 5_2_route | 7.1 | last meaningful line 0.2 h ago (261/262 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__clcc5e3e61-3434617 | sle_hc2 | 5_2_route | 7.1 | last meaningful line 0.0 h ago (264/264 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-1784944 | sle_st_a_v1 | 5_2_route | 8.2 | drt_violations best 72 last 72 rows 54 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-1826228 | sle_st_a_v1 | 5_2_route | 8.2 | drt_violations best 72 last 72 rows 54 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-1538145 | sle_st_a_v2 | generate_abstract | 8.4 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3668964 | sle_st_b_v2 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (5156/5156 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-4153401 | sle_stm_v2 | 5_2_route | 6.6 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1101031 | slw_hc3 | 5_2_route | 5.8 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3626034 | slw_hc3 | 5_2_route | 7.0 | drt_violations best 84827 last 84827 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1494307 | slw_st_a_v1 | 5_2_route | 8.4 | drt_violations best 72 last 72 rows 53 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-1494646 | slw_st_a_v2 | 5_2_route | 8.4 | drt_violations best 72 last 72 rows 50 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3657462 | slw_stm_v2 | 5_2_route | 6.9 | last meaningful line 0.2 h ago (262/263 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_165709_1862160-i1t-580795 | eco_20261124_165709_1862160-i1t | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (173/173 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 5.9 |  | NO-DATA: no log found |  |
| epyc2 | so_4037665_ff_28537 | so_4037665_ff_28537 | generate_abstract | 0.8 | last meaningful line 0.7 h ago (1034/1034 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | so_4037665_tt_28537 | so_4037665_tt_28537 | generate_abstract | 0.8 | last meaningful line 0.7 h ago (1034/1034 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-cbf-q00-s2-grt-2259454 | cbf-q00-s2-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-1559108 | cbn_q01 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (7503/7503 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (10681/10682 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 12.4 | last meaningful line 0.5 h ago (277/278 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 7.8 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | postcts_gate_TT | 8.1 | last meaningful line -0.0 h ago (66334/66334 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | postcts_gate_TT | 7.9 | last meaningful line 0.0 h ago (833/833 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | postcts_gate_TT | 8.0 | last meaningful line 0.1 h ago (388/388 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-2253577 | slw_hc2 | postcts_gate_FF | 7.9 | last meaningful line -0.0 h ago (48608/48608 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-1524868 | slw_sc_v1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4482/4482 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 12.2 | last meaningful line 0.5 h ago (284/285 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-2092169 | slw_sc_v1 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (5138/5138 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | postcts_gate_FF | 8.0 | last meaningful line -0.0 h ago (84849/84849 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | 5_2_route | 12.3 | drt_violations best 122101 last 122101 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | 6_report | 14.0 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | 5_2_route | 7.9 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | otc-1581254-7202 | 1581254 | asbuilt.yosys | 0.5 | last meaningful line 0.1 h ago (242290/242290 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_145005_2036075-i2-1496134 | eco_20261124_145005_2036075-i2 | 5_1_grt | 0.5 | last meaningful line 0.0 h ago (295/329 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i2t-864737 | eco_20261124_175441_992552-i2t | 5_2_route | 0.9 | last meaningful line 0.1 h ago (254/255 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i1-2124005 | eco_20261124_192157_3493836-i1 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (144/144 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i1t-231566 | eco_20261124_235631_1843084-i1t | 5_2_route | 1.3 | last meaningful line 0.1 h ago (260/261 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795561668594539576-i1-3034100 | eco_retry_1795561668594539576-i1 | 5_2_route | 2.1 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | prd-fin-3392092 | fin | 6_report | 0.4 | last meaningful line 0.1 h ago (1068/1068 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | so_1626022_ff_68154 | so_1626022_ff_68154 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc7 | so_1626022_tt_68154 | so_1626022_tt_68154 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 5_2_route | 9.1 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | postcts_gate_FF | 9.1 | last meaningful line 0.1 h ago (367/367 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | postcts_gate_TT | 9.1 | last meaningful line 0.3 h ago (829/829 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | 5_2_route | 9.2 | last meaningful line 0.1 h ago (136/136 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | 5_2_route | 9.2 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 9.1 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-4063882 | sle_st_a_v2 | 6_1_fill | 9.1 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | postcts_gate_TT | 9.1 | last meaningful line 0.2 h ago (1179/1179 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | postcts_gate_FF | 9.1 | last meaningful line 0.0 h ago (1074/1074 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | postcts_gate_FF | 9.1 | last meaningful line 0.2 h ago (1031/1031 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | 5_2_route | 9.1 | drt_violations best 160491 last 160491 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | postcts_gate_TT | 9.1 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | postcts_gate_FF | 9.1 | last meaningful line 0.3 h ago (387/387 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | postcts_gate_TT | 9.1 | last meaningful line 0.2 h ago (838/838 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | postcts_gate_FF | 9.1 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | 5_2_route | 12.4 | drt_violations best 235 last 235 rows 4 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | 5_2_route | 9.2 | last meaningful line 0.0 h ago (265/266 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3909116 | slw_hc3 | 5_2_route | 9.2 | drt_violations best 88102 last 88102 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-3949912 | slw_hc3 | 5_2_route | 9.1 | drt_violations best 4550 last 4550 rows 3 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 9.1 | last meaningful line 0.5 h ago (273/274 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 9.0 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | 5_2_route | 9.1 | drt_violations best 1995 last 1995 rows 9 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | postcts_gate_FF | 9.1 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-2900322-1356 | 2900322 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3t-2289287 | eco_20261123_164145_1995767-i3t | 5_2_route | 6.6 | drt_violations best 4032 last 4032 rows 2 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261124_225649_3846510-i1-114505 | eco_20261124_225649_3846510-i1 | 5_2_route | 2.3 | drt_violations best 29 last 29 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 6.0 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R9_hc3_d5fde | relec-r2-R9_hc3_d5fde | - | 5.9 |  | NO-DATA: no log found |  |
| epyc8 | so_1481074_ff_4979 | so_1481074_ff_4979 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc8 | so_1481074_tt_4979 | so_1481074_tt_4979 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv6882e5ea-3887067 | col_h9_r0_p2__t1 | 3_1_place_gp_skip_io | 0.2 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b-3581353 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8527 last 0.8621 rows 17 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-270204 | col_h9_r0_p3__t1 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (290/290 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 5.8 | drt_violations best 7501 last 7501 rows 3 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | 4_1_cts | 5.5 | last meaningful line 0.1 h ago (11435/11435 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_1_grt | 6.0 | last meaningful line 0.1 h ago (1933/1946 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-1010348 | sle_fw_v1 | tt_setup_repair_grt | 5.9 | repair_Viol best 47 last 47 rows 7 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-sle_fw_v1__clf58b4dfb-733846 | sle_fw_v1 | tt_setup_repair_grt | 6.1 | repair_Viol best 47 last 47 rows 31 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-667540 | sle_hc1 | postcts_gate_FF | 6.1 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t38-3886271 | slice_station__t38 | 3_3_place_gp | 0.2 | overflow best 0.2515 last 0.2515 rows 3 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slice_station__t42__clcf44e680-3847773 | slice_station__t42 | 3_3_place_gp | 0.2 | overflow best 0.2319 last 0.234 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slice_station__t43-3839150 | slice_station__t43 | 3_3_place_gp | 0.2 | overflow best 0.3071 last 0.3071 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_1_grt | 6.2 | last meaningful line 0.2 h ago (2498/2514 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-551472 | slw_fw_v1 | 5_1_grt | 6.2 | last meaningful line 0.0 h ago (1948/1952 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v2__cl8537f156-601723 | slw_fw_v2 | postcts_gate_TT | 6.2 | last meaningful line 0.0 h ago (1817/1817 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i3-3801930 | eco_20261123_224216_149959-i3 | 5_2_route | 3.9 | drt_violations best 24 last 24 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | ap-ageom-kw-kv3-hgi-v6-grt-3526117 | kv3-hgi-v6-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-coll_core-3813096 | coll_core | 5_1_grt | 7.4 | repair_TNS best 528.016 last 528.016 rows 8 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Eo-371567 | kv3_hub_Eo | 3_3_place_gp | 1.4 | overflow best 0.5916 last 0.5916 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-1090401 | kv3_pc_v1 | 3_3_place_gp | 1.1 | last meaningful line -0.0 h ago (15/15 lines) | YOUNG: evidence -0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | postcts_gate_FF | 12.5 | last meaningful line 0.2 h ago (1946/1946 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v3-1442734 | sle_fw_v3 | 5_1_grt | 6.2 | last meaningful line 0.7 h ago (1283/2781 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | postcts_gate_TT | 8.1 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 3_3_place_gp | 0.2 | overflow best 0.7713 last 0.7713 rows 27 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-3662089 | sle_sc_v1 | postcts_gate_FF | 7.5 | last meaningful line 0.2 h ago (2145/2145 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | pregrt_ff_hold | 4.5 | repair_TNS best 22328.5 last 22328.5 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | postcts_gate_FF | 6.2 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 4.4 | last meaningful line 0.3 h ago (254/254 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 4_1_cts | 1.9 | last meaningful line 0.1 h ago (5560/5560 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3325358 | slw_fw_v1 | 4_1_cts | 1.9 | last meaningful line 0.3 h ago (5379/5379 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 12.4 | last meaningful line 0.5 h ago (271/272 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v3-1399930 | slw_fw_v3 | postcts_gate_FF | 6.2 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 4_1_cts | 3.0 | last meaningful line 0.2 h ago (5307/5307 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 4_1_cts | 4.2 | last meaningful line 0.1 h ago (5235/5235 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3890746 | slw_sc_v1 | 5_1_grt | 4.5 | last meaningful line 0.5 h ago (1300/1991 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | tt_setup_repair_grt | 8.1 | repair_Viol best 11 last 11 rows 13 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 4_1_cts | 2.7 | last meaningful line 0.0 h ago (5137/5137 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | 5_2_route | 12.4 | last meaningful line 0.5 h ago (278/279 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | postcts_gate_FF | 8.1 | last meaningful line 0.0 h ago (1484/1484 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1e5219ea-4177722 | slw_su_l0 | 5_2_route | 4.3 | last meaningful line 0.3 h ago (254/254 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-3090069 | slw_su_l0 | 5_1_grt | 2.0 | last meaningful line 0.1 h ago (1290/1606 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-tt_ctlm-3234028 | tt_ctlm | 5_1_grt | 2.0 | last meaningful line 0.1 h ago (1289/1337 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 6.3 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 6.3 |  | NO-DATA: no log found |  |
| intel1 | otc-2434312-2110 | 2434312 | flow | 0.5 | last meaningful line 0.0 h ago (2705/2705 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | otc-3192080-15624 | 3192080 | eq10 | 0.3 | last meaningful line 0.2 h ago (517751/517751 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i2-2930338 | eco_20261123_191853_2879776-i2 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (142/142 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-hd_ctl-2153206 | hd_ctl | pregrt_ff_hold | 0.8 | repair_TNS best 34059.6 last 34059.6 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-3065431 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_hgi_v8-2986000 | kv3_hgi_v8 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (492/492 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-2239522 | kv3_io_ft | 5_2_route | 0.7 | last meaningful line 0.0 h ago (216/217 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-sle_st_a_v2__pv4242de79-3433356 | sle_st_a_v2 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-2271710 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (225/226 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_1_grt | 7.6 | last meaningful line 0.5 h ago (1285/1902 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 5_2_route | 7.8 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3215525 | slw_sc_v1 | 3_2_place_iop | 0.1 | last meaningful line 0.0 h ago (7/7 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-2390236 | slw_st_b_v1 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (60/60 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | ffx-3424961 | ffx | generate_abstract | 0.0 | last meaningful line 0.0 h ago (1019/1019 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v1__clf58b4dfb-461721 | sle_fw_v1 | 5_1_grt | 5.6 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-660000 | sle_hc0 | pregrt_ff_hold | 5.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | 5_1_grt | 4.5 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1583204 | sle_st_b_v1 | pregrt_ff_hold | 4.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_1_grt | 6.2 | repair_TNS best 0 last 0 rows 14 | PROGRESS: repair_TNS reached 0 |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 20.2 | drt_violations best 15812 last 15812 rows 15 | before-window best 22940, window best 15812 | PROGRESS: drt_violations improved 31.1 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 12.6 | drt_violations best 1743 last 5229 rows 18 | before-window best 2057, window best 1743 | PROGRESS: drt_violations improved 15.3 % in window |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 12.5 | drt_violations best 123388 last 123388 rows 2 | before-window best 521993, window best 123388 | PROGRESS: drt_violations improved 76.4 % in window |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-4191516 | slw_fw_v2 | 5_1_grt | 6.6 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 39.6 | drt_violations best 10129 last 48097 rows 18 | before-window best 13426, window best 10129 | PROGRESS: drt_violations improved 24.6 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 32.9 | drt_violations best 7726 last 31531 rows 18 | before-window best 15355, window best 7726 | PROGRESS: drt_violations improved 49.7 % in window |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-2222980 | sle_fw_v2 | 5_1_grt | 7.9 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 17.6 | drt_violations best 8628 last 8628 rows 9 | before-window best 490378, window best 8628 | PROGRESS: drt_violations improved 98.2 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 13.8 | drt_violations best 504597 last 504597 rows 1 | before-window best 504597, window best 504597 | PROGRESS: drt_violations: active iteration at 185837 < best completed total 504597 (in-ite |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 17.8 | drt_violations best 67058 last 67058 rows 7 | before-window best 141373, window best 67058 | PROGRESS: drt_violations improved 52.6 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 13.9 | drt_violations best 102681 last 102681 rows 3 | before-window best 400194, window best 102681 | PROGRESS: drt_violations improved 74.3 % in window |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_1_grt | 9.1 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 5_2_route | 9.1 | drt_violations best 72 last 72 rows 42 | before-window best 146485, window best 72 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 9.1 | drt_violations best 24952 last 24952 rows 7 | before-window best 274214, window best 24952 | PROGRESS: drt_violations improved 90.9 % in window |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | 5_2_route | 10.5 | drt_violations best 234054 last 234054 rows 1 | before-window best 234054, window best 234054 | PROGRESS: drt_violations: active iteration at 86807 < best completed total 234054 (in-iter |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2360221 | slw_hc2 | pregrt_ff_hold | 5.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2160450 | slw_hc3 | pregrt_ff_hold | 5.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-coll_ftm-2240258 | coll_ftm | 5_1_grt | 0.7 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
