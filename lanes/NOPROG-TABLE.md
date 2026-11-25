# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 16:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 9, 'GRT-LABEL': 6, 'YOUNG': 147, 'NO-DATA': 18, 'PROGRESS': 25}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 7.3 | last meaningful line 6.0 h ago (48/131 lines) | NO-PROGRESS: no new non-iteration log line for 6.0 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 10.4 | last meaningful line 6.8 h ago (48/188 lines) | NO-PROGRESS: no new non-iteration log line for 6.8 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | pregrt_ff_hold | 4.7 | repair_TNS best 100323 last 100323 rows 1 | before-window best 100323, window best 100323 | NO-PROGRESS: repair_TNS best 100323 vs 100323 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-HG-CAP decides; neve |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 2.6 | repair_TNS best 827598 last 827598 rows 1 | before-window best 827598, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3458150 | sle_hc2 | pregrt_ff_hold | 6.4 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| intel1 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3463031 | slw_hc1 | pregrt_ff_hold | 6.4 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 23.9 | last meaningful line 13.1 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 13.1 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1797391-24144 | 1797391 | flow3 | 10.8 | last meaningful line 10.5 h ago (208/209 lines) | NO-PROGRESS: no new non-iteration log line for 10.5 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 27.7 | last meaningful line 13.1 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 13.1 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 5_1_grt | 7.6 | grt rounds 1 overflow 5:42234 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv_v2n-1048434 | kv3_pv_v2n | 5_1_grt | 7.4 | grt rounds 2 overflow 5:64147 -> 10:49031 | GRT-LABEL: DESIGN-FAIL: overflow 49031 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v6-908877 | kv3_pv_v6 | 5_1_grt | 7.5 | grt rounds 2 overflow 5:56449 -> 10:44954 | GRT-LABEL: DESIGN-FAIL: overflow 44954 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_hgi_v8-2088531 | kv3_hgi_v8 | 5_1_grt | 5.0 | grt rounds 2 overflow 5:53252 -> 10:40184 | GRT-LABEL: DESIGN-FAIL: overflow 40184 at round 10 > 1000 |  |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 5_1_grt | 9.3 | grt rounds 1 overflow 5:41695 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 5_1_grt | 8.6 | grt rounds 1 overflow 5:83232 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | 5_2_route | 4.2 | drt_violations best 33912 last 33912 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1479488 | hd_spn | 5_2_route | 4.0 | drt_violations best 3152 last 3152 rows 3 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-3028627 | kv3_hgi | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-3075963 | kv3_hgi | 2_1_floorplan | 0.1 | repair_Viol best 1094 last 1094 rows 1158 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-3077015 | kv3_hgi_v2 | 2_1_floorplan | 0.1 | repair_Viol best 1094 last 1094 rows 741 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-3111420 | kv3_hgi_v2 | 2_1_floorplan | 0.1 | repair_Viol best 1094 last 1094 rows 548 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-kv3_hub_Wo-579995 | kv3_hub_Wo | 3_3_place_gp | 1.7 | overflow best 0.0994 last 0.0994 rows 46 | YOUNG: stage 0.7 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8afe1e027-2684889 | kv3_pc_v1 | 2_1_floorplan | 0.3 | repair_Viol best 8514 last 8514 rows 1070 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-2695537 | kv3_pc_v1 | 2_1_floorplan | 0.3 | repair_Viol best 8516 last 8516 rows 1054 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | 5_1_grt | 7.5 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | pregrt_ff_hold | 2.7 | repair_TNS best 46556.5 last 46556.5 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v7e-1156836 | kv3_pv_v7e | postcts_gate_TT | 7.3 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v1__clf58b4dfb-461721 | sle_fw_v1 | 5_1_grt | 4.8 | last meaningful line 0.2 h ago (277/1082 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | 4_1_cts | 3.3 | last meaningful line 0.2 h ago (5099/5099 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | pregrt_ff_hold | 3.7 | repair_TNS best 22304.1 last 22304.1 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | 5_1_grt | 4.3 | last meaningful line 0.4 h ago (1295/2074 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2793057 | sle_stm_v1 | 5_2_route | 6.0 | last meaningful line 0.0 h ago (259/259 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_1_grt | 5.4 | repair_Remaining best 138472 last 138472 rows 267 | YOUNG: stage 0.9 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_1_grt | 5.4 | repair_Remaining best 237058 last 237058 rows 183 | YOUNG: stage 0.8 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 5_1_grt | 5.5 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | 4_1_cts | 4.1 | last meaningful line 0.1 h ago (5519/5519 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | pregrt_ff_hold | 3.2 | repair_TNS best 25913.4 last 25913.4 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | 4_1_cts | 2.2 | last meaningful line 0.0 h ago (4878/4878 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_stm_v1__cle34a73c3-4063338 | slw_stm_v1 | postcts_gate_FF | 5.2 | last meaningful line 0.0 h ago (1403/1403 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-901577-23707 | 901577 | signoff | 1.5 | last meaningful line 1.5 h ago (3/3 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | qc-colls-lec-h1 | qc-colls-lec-h1 | - | 2.8 |  | NO-DATA: no log found |  |
| epyc10 | qc-colls-lec-h2 | qc-colls-lec-h2 | - | 2.7 |  | NO-DATA: no log found |  |
| epyc10 | qc-hc3-lec-r8-nearest | qc-hc3-lec-r8-nearest | - | 1.2 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R8_hc3_pvcca | relec-r2-R8_hc3_pvcca | - | 5.2 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-U3_pv97423966 | relec-r2-U3_pv97423966 | - | 3.2 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-kv3_pc_v1__cl4ea58a5c__r8c9cba7ae-2727555 | kv3_pc_v1 | 2_1_floorplan | 0.2 | repair_Viol best 8514 last 8514 rows 766 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 4_1_cts | 2.3 | last meaningful line 0.0 h ago (5950/5950 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 4_1_cts | 3.3 | last meaningful line 0.1 h ago (5481/5481 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | postcts_gate_TT | 6.8 | last meaningful line 0.1 h ago (371/371 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 4_1_cts | 2.0 | last meaningful line 0.1 h ago (5759/5759 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | postcts_gate_TT | 6.6 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | postcts_gate_TT | 6.7 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc2__cl6bcaba89-3858415 | slw_hc2 | 5_2_route | 7.1 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2533872 | slw_hc3 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4903/4903 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3838177 | slw_hc3 | 6_report | 7.1 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | postcts_gate_TT | 6.5 | last meaningful line 0.1 h ago (1094/1094 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-320042 | slw_st_b_v2 | 5_2_route | 6.5 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 5.7 |  | NO-DATA: no log found |  |
| epyc11 | prd-eco_20261124_154417_1016084-i1-3808110 | eco_20261124_154417_1016084-i1 | 5_2_route | 3.3 | drt_violations best 80 last 80 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i1t-3010529 | eco_20261124_200101_1087713-i1t | 5_2_route | 4.2 | drt_violations best 18110 last 18110 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_204246_1187010-i1t-3648808 | eco_20261124_204246_1187010-i1t | 5_2_route | 3.5 | drt_violations best 15305 last 15305 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc11 | prd-fin-2053304 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-hd_host_w-3495503 | hd_host_w | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3716/3717 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v2__cle0015330-2015173 | kv3_hgi_v2 | 5_1_grt | 1.0 | last meaningful line 0.2 h ago (288/1293 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v6-3286735 | kv3_hgi_v6 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (488/488 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-1457043 | kv3_hroot | postcts_gate_TT | 1.4 | last meaningful line 0.0 h ago (2219/2219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Wo-1888444 | kv3_hub_Wo | 3_3_place_gp | 1.1 | overflow best 0.6412 last 0.6412 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3272034 | sle_hc0 | 3_3_place_gp | 0.3 | overflow best 0.8924 last 0.8924 rows 21 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-491987 | sle_hc0 | 5_1_grt | 5.2 | last meaningful line 0.2 h ago (273/817 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-1254949 | sle_hc2 | 5_1_grt | 4.7 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3414126 | sle_hc2 | postcts_gate_FF | 6.1 | last meaningful line 0.1 h ago (759/759 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__clcc5e3e61-3434617 | sle_hc2 | postcts_gate_TT | 6.1 | last meaningful line -0.0 h ago (77650/77650 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 11.5 | drt_violations best 123388 last 123388 rows 2 | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-1784944 | sle_st_a_v1 | 5_2_route | 7.2 | drt_violations best 72 last 72 rows 45 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-1826228 | sle_st_a_v1 | 5_2_route | 7.2 | drt_violations best 72 last 72 rows 38 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-1538145 | sle_st_a_v2 | 5_2_route | 7.4 | drt_violations best 72 last 72 rows 52 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3668964 | sle_st_b_v2 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-4153401 | sle_stm_v2 | 5_2_route | 5.6 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v3-1868496 | sle_stm_v3 | 6_report | 7.1 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1101031 | slw_hc3 | postcts_gate_FF | 4.8 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3626034 | slw_hc3 | 5_2_route | 6.0 | last meaningful line 0.2 h ago (263/264 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1494307 | slw_st_a_v1 | 5_2_route | 7.4 | drt_violations best 72 last 72 rows 37 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-1494646 | slw_st_a_v2 | 5_2_route | 7.4 | drt_violations best 72 last 72 rows 34 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-2708297 | slw_st_b_v1 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (65/65 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3657462 | slw_stm_v2 | postcts_gate_FF | 5.9 | last meaningful line 0.0 h ago (1355/1355 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | eco-abs-2411647 | eco-abs | generate_abstract | 0.8 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | otc-3650595-12014 | 3650595 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 4.9 |  | NO-DATA: no log found |  |
| epyc2 | so_3449097_ff_26399 | so_3449097_ff_26399 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | so_3449097_tt_26399 | so_3449097_tt_26399 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-2222980 | sle_fw_v2 | 5_1_grt | 6.9 | last meaningful line 0.7 h ago (1283/2043 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 11.4 | last meaningful line 0.5 h ago (273/274 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 6.8 | last meaningful line 0.5 h ago (269/270 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | postcts_gate_FF | 7.1 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | 6_report | 12.6 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl1bc59e1c-2061343 | slw_hc0 | 5_1_grt | 7.0 | last meaningful line 0.1 h ago (1101/1118 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | 5_1_grt | 6.9 | last meaningful line 0.1 h ago (1049/1066 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 5_1_grt | 7.0 | last meaningful line 0.0 h ago (1090/1096 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-2253577 | slw_hc2 | postcts_gate_TT | 6.9 | last meaningful line 0.2 h ago (725/725 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 11.2 | last meaningful line 0.7 h ago (278/279 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | postcts_gate_TT | 7.0 | last meaningful line 0.1 h ago (1086/1086 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | 5_2_route | 11.3 | last meaningful line 0.5 h ago (276/277 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | 5_2_route | 13.0 | drt_violations best 18131 last 18131 rows 2 | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | 5_2_route | 6.9 | last meaningful line 0.0 h ago (251/251 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | otc-696059-22167 | 696059 | clk_freeze_post | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i3t-3392092 | eco_20261123_171023_3055226-i3t | 5_2_route | 6.2 | drt_violations best 835 last 835 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i1t-1220925 | eco_20261124_192157_3493836-i1t | 5_2_route | 4.8 | drt_violations best 5844 last 5844 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i1t-231566 | eco_20261124_235631_1843084-i1t | 5_1_grt | 0.3 | repair_Remaining best 144654 last 144654 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | prd-eco_retry_1795561668594539576-i1-3034100 | eco_retry_1795561668594539576-i1 | 5_2_route | 1.1 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | so_626784_ff_36262 | so_626784_ff_36262 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | so_626784_tt_36262 | so_626784_tt_36262 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_1_grt | 8.1 | last meaningful line 0.2 h ago (2515/2528 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 5_2_route | 8.1 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | postcts_gate_TT | 8.1 | last meaningful line 0.0 h ago (380/380 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | postcts_gate_TT | 8.1 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | postcts_gate_FF | 8.2 | last meaningful line 0.1 h ago (783/783 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | postcts_gate_FF | 8.2 | last meaningful line 0.2 h ago (369/369 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 8.1 | last meaningful line 0.5 h ago (263/264 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | postcts_gate_FF | 8.1 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | postcts_gate_TT | 8.1 | last meaningful line 0.1 h ago (1099/1099 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | postcts_gate_TT | 8.1 | last meaningful line 0.2 h ago (1024/1024 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | 5_2_route | 8.1 | last meaningful line 0.3 h ago (275/276 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l0__cl7a55c676-4020210 | sle_su_l0 | 5_2_route | 8.1 | drt_violations best 6 last 6 rows 12 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | postcts_gate_TT | 8.1 | last meaningful line 0.0 h ago (843/843 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | postcts_gate_TT | 8.1 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | postcts_gate_TT | 8.1 | last meaningful line 0.1 h ago (386/386 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | 5_2_route | 11.4 | drt_violations best 12852 last 12852 rows 2 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | postcts_gate_FF | 8.2 | last meaningful line -0.0 h ago (26564/26564 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3909116 | slw_hc3 | 5_2_route | 8.2 | drt_violations best 88102 last 88102 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-3949912 | slw_hc3 | 5_2_route | 8.1 | drt_violations best 80626 last 80626 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 8.1 | last meaningful line 0.3 h ago (269/270 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 8.0 | last meaningful line 0.3 h ago (277/278 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | 5_2_route | 8.1 | drt_violations best 30201 last 30201 rows 2 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 5_2_route | 8.1 | drt_violations best 108 last 108 rows 24 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | postcts_gate_TT | 8.1 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-2900322-1356 | 2900322 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3t-2289287 | eco_20261123_164145_1995767-i3t | 5_2_route | 5.6 | drt_violations best 35664 last 35664 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261124_225649_3846510-i1-114505 | eco_20261124_225649_3846510-i1 | 5_2_route | 1.3 | last meaningful line 0.1 h ago (252/252 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 5.0 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R1b_coll_old | relec-r2-R1b_coll_old | - | 4.9 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R4_coll_guard | relec-r2-R4_coll_guard | - | 5.0 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R9_hc3_d5fde | relec-r2-R9_hc3_d5fde | - | 4.9 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 4.8 | drt_violations best 84487 last 84487 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | 4_1_cts | 4.5 | last meaningful line 0.1 h ago (11146/11146 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_1_grt | 5.0 | last meaningful line 0.7 h ago (1294/1849 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_1_grt | 5.2 | last meaningful line 0.2 h ago (288/1296 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-551472 | slw_fw_v1 | 5_1_grt | 5.2 | repair_Remaining best 257539 last 257539 rows 177 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-slw_fw_v2__cl8537f156-601723 | slw_fw_v2 | 5_1_grt | 5.2 | last meaningful line 0.0 h ago (2895/2901 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | otc-1893022-28497 | 1893022 | signoff | 1.8 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | otc-2119148-18648 | 2119148 | signoff | 1.6 | last meaningful line 1.5 h ago (3/3 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i3-3801930 | eco_20261123_224216_149959-i3 | 5_2_route | 2.9 | last meaningful line 0.2 h ago (294/295 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-coll_core-3813096 | coll_core | 5_1_grt | 6.2 | last meaningful line 0.7 h ago (1298/2856 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v4-3072149 | kv3_hgi_v4 | 5_1_grt | 3.7 | last meaningful line 0.5 h ago (292/1300 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Eo-371567 | kv3_hub_Eo | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (109/109 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | postcts_gate_TT | 11.2 | last meaningful line 0.2 h ago (1963/1963 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v3-1442734 | sle_fw_v3 | 5_1_grt | 4.9 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 5_1_grt | 6.9 | last meaningful line 0.2 h ago (915/928 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-3662089 | sle_sc_v1 | postcts_gate_TT | 6.2 | last meaningful line 0.2 h ago (2145/2145 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 4_1_cts | 3.2 | last meaningful line 0.1 h ago (5645/5645 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | postcts_gate_FF | 3.1 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (5439/5440 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | 5_2_route | 9.3 | drt_violations best 234054 last 234054 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3325358 | slw_fw_v1 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (5221/5222 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 11.2 | last meaningful line 0.3 h ago (265/266 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (5193/5193 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2360221 | slw_hc2 | tt_setup_measure | 4.2 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 4_1_cts | 3.0 | last meaningful line 0.1 h ago (5080/5080 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3890746 | slw_sc_v1 | 5_1_grt | 3.2 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (4935/4936 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | 5_2_route | 11.1 | last meaningful line 0.3 h ago (270/271 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | postcts_gate_TT | 6.9 | last meaningful line 0.1 h ago (697/697 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1e5219ea-4177722 | slw_su_l0 | postcts_gate_TT | 3.0 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-3090069 | slw_su_l0 | pregrt_ff_hold | 0.8 | repair_TNS best 39885.7 last 39885.7 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-tt_ctlm-3234028 | tt_ctlm | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (3921/3921 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 5.0 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 5.0 |  | NO-DATA: no log found |  |
| intel1 | otc-3854277-21865 | 3854277 | - | 9.0 |  | NO-DATA: no log found |  |
| intel1 | prd-count-p1_tc-2852283 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_1_grt | 6.6 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | postcts_gate_TT | 6.8 | last meaningful line 0.0 h ago (1645/1645 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_1_grt | 6.5 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-660000 | sle_hc0 | pregrt_ff_hold | 4.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1583204 | sle_st_b_v1 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_st_b_v2__clfde1249e-689859 | sle_st_b_v2 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-856398 | slw_st_b_v1 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_1_grt | 6.7 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS reached 0 |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 19.2 | drt_violations best 16673 last 16673 rows 14 | before-window best 23959, window best 16673 | PROGRESS: drt_violations improved 30.4 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 11.6 | drt_violations best 1743 last 5229 rows 18 | before-window best 2657, window best 1743 | PROGRESS: drt_violations improved 34.4 % in window |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-4191516 | slw_fw_v2 | 5_1_grt | 5.6 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 38.6 | drt_violations best 10129 last 48097 rows 18 | before-window best 14975, window best 10129 | PROGRESS: drt_violations improved 32.4 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 31.9 | drt_violations best 7726 last 7726 rows 17 | before-window best 20899, window best 7726 | PROGRESS: drt_violations improved 63.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 16.6 | drt_violations best 11728 last 11728 rows 6 | before-window best 490378, window best 11728 | PROGRESS: drt_violations improved 97.6 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 12.8 | drt_violations best 504597 last 504597 rows 1 | before-window best 504597, window best 504597 | PROGRESS: drt_violations: active iteration at 322643 < best completed total 504597 (in-ite |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 16.8 | drt_violations best 68064 last 68064 rows 6 | before-window best 407677, window best 68064 | PROGRESS: drt_violations improved 83.3 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 12.9 | drt_violations best 123176 last 123176 rows 2 | before-window best 400194, window best 123176 | PROGRESS: drt_violations improved 69.2 % in window |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-4063882 | sle_st_a_v2 | 5_2_route | 8.1 | drt_violations best 72 last 72 rows 52 | before-window best 142170, window best 72 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_1_grt | 8.1 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 8.1 | drt_violations best 26414 last 26414 rows 6 | before-window best 274214, window best 26414 | PROGRESS: drt_violations improved 90.4 % in window |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-1010348 | sle_fw_v1 | 5_1_grt | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_fw_v1__clf58b4dfb-733846 | sle_fw_v1 | 5_1_grt | 5.1 | repair_TNS best 0 last 0 rows 4 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-667540 | sle_hc1 | 5_1_grt | 5.1 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | tt_setup_repair_grt | 4.9 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-slw_fw_v3-1399930 | slw_fw_v3 | 5_1_grt | 5.0 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2160450 | slw_hc3 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 5_1_grt | 6.9 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS reached 0 |  |
