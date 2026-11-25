# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 16:01 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 8, 'GRT-LABEL': 6, 'YOUNG': 159, 'NO-DATA': 14, 'PROGRESS': 24}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 10.1 | last meaningful line 6.6 h ago (48/188 lines) | NO-PROGRESS: no new non-iteration log line for 6.6 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | pregrt_ff_hold | 4.5 | repair_TNS best 100323 last 100323 rows 1 | before-window best 100323, window best 100323 | NO-PROGRESS: repair_TNS best 100323 vs 100323 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-HG-CAP decides; neve |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3458150 | sle_hc2 | pregrt_ff_hold | 6.4 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| intel1 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3463031 | slw_hc1 | pregrt_ff_hold | 6.4 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 23.9 | last meaningful line 13.1 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 13.1 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1797391-24144 | 1797391 | flow3 | 10.8 | last meaningful line 10.5 h ago (208/209 lines) | NO-PROGRESS: no new non-iteration log line for 10.5 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 27.7 | last meaningful line 13.1 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 13.1 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 15.2 | drt_violations best 2 last 47 rows 54 | before-window best 2, window best 2 | NO-PROGRESS: drt_violations best 2 vs 2 before window: < 2 % in 6 h | CANCELLED |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 5_1_grt | 7.4 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv_v2n-1048434 | kv3_pv_v2n | 5_1_grt | 7.1 | grt rounds 2 overflow 5:64147 -> 10:49031 | GRT-LABEL: DESIGN-FAIL: overflow 49031 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v6-908877 | kv3_pv_v6 | 5_1_grt | 7.2 | grt rounds 2 overflow 5:56449 -> 10:44954 | GRT-LABEL: DESIGN-FAIL: overflow 44954 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v7e-1156836 | kv3_pv_v7e | 5_1_grt | 7.0 | grt rounds 2 overflow 5:101255 -> 10:76491 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 5_1_grt | 9.1 | grt rounds 1 overflow 5:41695 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 5_1_grt | 8.6 | grt rounds 1 overflow 5:83232 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 7.1 | last meaningful line 5.8 h ago (48/63 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | 5_2_route | 3.9 | drt_violations best 33912 last 33912 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1479488 | hd_spn | 5_2_route | 3.8 | drt_violations best 24108 last 24108 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-579995 | kv3_hub_Wo | 3_3_place_gp | 1.5 | overflow best 0.0994 last 0.0994 rows 46 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8afe1e027-2684889 | kv3_pc_v1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-2695537 | kv3_pc_v1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | tt_setup_repair | 2.4 | last meaningful line 0.0 h ago (428/428 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-660000 | sle_hc0 | pregrt_ff_hold | 4.4 | repair_TNS best 13841 last 13841 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | 4_1_cts | 3.1 | last meaningful line 0.2 h ago (5096/5096 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | pregrt_ff_hold | 3.5 | repair_TNS best 22304.1 last 22304.1 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | 5_1_grt | 4.0 | last meaningful line 0.2 h ago (1295/1361 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2793057 | sle_stm_v1 | 5_2_route | 5.8 | last meaningful line -0.0 h ago (9/9 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_1_grt | 5.2 | last meaningful line 0.2 h ago (248/1257 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | pregrt_ff_hold | 5.2 | repair_TNS best 169942 last 169942 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | 4_1_cts | 3.8 | last meaningful line 0.0 h ago (5516/5516 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | hold_gate | 3.0 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-1320764 | slw_st_b_v2 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | 4_1_cts | 1.9 | last meaningful line 0.1 h ago (4824/4824 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_stm_v1__cle34a73c3-4063338 | slw_stm_v1 | postcts_gate_TT | 5.0 | last meaningful line -0.0 h ago (87524/87524 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | otc-2505291-18420 | 2505291 | asbuilt.yosys | 0.1 | last meaningful line 0.1 h ago (369/369 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-901577-23707 | 901577 | signoff | 1.3 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | qc-colls-lec-h1 | qc-colls-lec-h1 | - | 2.6 |  | NO-DATA: no log found |  |
| epyc10 | qc-colls-lec-h2 | qc-colls-lec-h2 | - | 2.5 |  | NO-DATA: no log found |  |
| epyc10 | qc-hc3-lec-r8-nearest | qc-hc3-lec-r8-nearest | - | 1.0 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R8_hc3_pvcca | relec-r2-R8_hc3_pvcca | - | 5.0 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-U3_pv97423966 | relec-r2-U3_pv97423966 | - | 2.9 |  | NO-DATA: no log found |  |
| epyc10 | smp-2743475 | smp | tt_setup_repair | 0.0 | last meaningful line 0.0 h ago (428/428 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hgi_v8-2088531 | kv3_hgi_v8 | 5_1_grt | 4.8 | last meaningful line 1.8 h ago (300/1310 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 2.3 | repair_TNS best 827598 last 827598 rows 1 | YOUNG: evidence 2.3 h < 2.5 h |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_1_grt | 6.5 | last meaningful line 0.2 h ago (2564/2577 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (5923/5923 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 4_1_cts | 3.1 | last meaningful line 0.2 h ago (5477/5477 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | postcts_gate_FF | 6.5 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 4_1_cts | 1.8 | last meaningful line 0.0 h ago (5731/5731 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | 5_1_grt | 6.3 | last meaningful line 0.2 h ago (1226/1280 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | postcts_gate_TT | 6.5 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc2__cl6bcaba89-3858415 | slw_hc2 | 5_2_route | 6.8 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2533872 | slw_hc3 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3838177 | slw_hc3 | 5_2_route | 6.8 | drt_violations best 8674 last 8674 rows 2 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | postcts_gate_TT | 6.3 | last meaningful line 0.0 h ago (497/497 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-320042 | slw_st_b_v2 | postcts_gate_FF | 6.3 | last meaningful line 0.1 h ago (1063/1063 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 5.5 |  | NO-DATA: no log found |  |
| epyc11 | otc-2078919-10849 | 2078919 | asbuilt.yosys | 0.5 | last meaningful line 0.1 h ago (240970/240970 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | otc-2136782-11303 | 2136782 | asbuilt.yosys | 0.5 | last meaningful line 0.1 h ago (241389/241389 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | prd-count-p1_tc-2053304 | count-p1_tc | prd_count_p1_tc | 0.2 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_154417_1016084-i1-3808110 | eco_20261124_154417_1016084-i1 | 5_2_route | 3.1 | drt_violations best 80 last 80 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i1t-3010529 | eco_20261124_200101_1087713-i1t | 5_2_route | 3.9 | drt_violations best 18110 last 18110 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_204246_1187010-i1t-3648808 | eco_20261124_204246_1187010-i1t | 5_2_route | 3.2 | drt_violations best 15305 last 15305 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-glue-3558834 | glue | postcts_gate_TT | 5.8 | last meaningful line 0.1 h ago (1493/1493 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v2__cle0015330-2015173 | kv3_hgi_v2 | 5_1_grt | 0.8 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v6-3286735 | kv3_hgi_v6 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-1457043 | kv3_hroot | tt_setup_repair_grt | 1.1 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Wo-1888444 | kv3_hub_Wo | 3_1_place_gp_skip_io | 0.9 | overflow best 0.1676 last 0.1676 rows 43 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3272034 | sle_hc0 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (291/291 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-491987 | sle_hc0 | 5_1_grt | 4.9 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-1254949 | sle_hc2 | 5_1_grt | 4.5 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3414126 | sle_hc2 | postcts_gate_FF | 5.9 | last meaningful line 0.0 h ago (369/369 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__clcc5e3e61-3434617 | sle_hc2 | postcts_gate_TT | 5.9 | last meaningful line 0.0 h ago (703/703 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 11.2 | drt_violations best 123388 last 123388 rows 2 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-1186805 | sle_sc_v3 | generate_abstract | 10.3 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-1784944 | sle_st_a_v1 | 5_2_route | 6.9 | drt_violations best 72 last 72 rows 35 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-1826228 | sle_st_a_v1 | 5_2_route | 6.9 | drt_violations best 72 last 72 rows 32 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-1538145 | sle_st_a_v2 | 5_2_route | 7.1 | drt_violations best 72 last 72 rows 50 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1751534 | sle_st_b_v2 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-4153401 | sle_stm_v2 | 5_2_route | 5.4 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v3-1868496 | sle_stm_v3 | 5_2_route | 6.9 | drt_violations best 8209 last 8209 rows 3 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-4191516 | slw_fw_v2 | 5_1_grt | 5.3 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1101031 | slw_hc3 | tt_setup_repair_grt | 4.5 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3626034 | slw_hc3 | 5_2_route | 5.7 | last meaningful line 0.1 h ago (259/260 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1494307 | slw_st_a_v1 | 5_2_route | 7.2 | drt_violations best 108 last 108 rows 29 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-1494646 | slw_st_a_v2 | 5_2_route | 7.2 | drt_violations best 90 last 105 rows 28 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-2708297 | slw_st_b_v1 | 3_3_place_gp | 0.4 | overflow best 0.6504 last 0.6504 rows 24 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3657462 | slw_stm_v2 | postcts_gate_FF | 5.7 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | eco-abs-2411647 | eco-abs | generate_abstract | 0.5 | last meaningful line 0.3 h ago (1028/1028 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 4.7 |  | NO-DATA: no log found |  |
| epyc2 | so_3310841_ff_57530 | so_3310841_ff_57530 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | so_3310841_tt_57530 | so_3310841_tt_57530 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-2222980 | sle_fw_v2 | 5_1_grt | 6.6 | last meaningful line 0.5 h ago (1283/2030 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 11.2 | last meaningful line 1.0 h ago (271/272 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 6.6 | last meaningful line 0.5 h ago (267/268 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | tt_setup_repair_grt | 6.8 | repair_Remaining best 336430 last 336430 rows 154 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_hc0__cl1bc59e1c-2061343 | slw_hc0 | 5_1_grt | 6.7 | last meaningful line 0.2 h ago (998/1011 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | 5_1_grt | 6.7 | last meaningful line 0.0 h ago (1003/1006 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 5_1_grt | 6.8 | last meaningful line 0.1 h ago (998/1011 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-2253577 | slw_hc2 | postcts_gate_TT | 6.6 | last meaningful line 0.0 h ago (719/719 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 11.0 | last meaningful line 0.5 h ago (278/279 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | postcts_gate_TT | 6.7 | last meaningful line 0.0 h ago (949/949 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | 5_2_route | 11.0 | last meaningful line 0.5 h ago (274/275 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | 5_2_route | 12.7 | drt_violations best 18131 last 18131 rows 2 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | 5_2_route | 6.6 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-count-p1_bc-3895101 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i3t-3392092 | eco_20261123_171023_3055226-i3t | 5_2_route | 5.9 | drt_violations best 835 last 835 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_145005_2036075-i2t-1611651 | eco_20261124_145005_2036075-i2t | 5_2_route | 4.3 | drt_violations best 5275 last 5275 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i1t-1220925 | eco_20261124_192157_3493836-i1t | 5_2_route | 4.6 | drt_violations best 5844 last 5844 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i1t-231566 | eco_20261124_235631_1843084-i1t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795561668594539576-i1-3034100 | eco_retry_1795561668594539576-i1 | 5_1_grt | 0.8 | last meaningful line 0.3 h ago (296/391 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | postcts_gate_TT | 7.9 | last meaningful line 0.2 h ago (370/370 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | postcts_gate_TT | 7.9 | last meaningful line 0.0 h ago (371/371 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl22c1ff36__pve230954c-3918742 | sle_hc1 | postcts_gate_FF | 7.9 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | postcts_gate_TT | 7.9 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | postcts_gate_FF | 7.9 | last meaningful line 0.2 h ago (394/394 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | postcts_gate_FF | 7.9 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 7.8 | last meaningful line 0.5 h ago (261/262 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-4063882 | sle_st_a_v2 | 5_2_route | 7.9 | drt_violations best 72 last 72 rows 50 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | tt_setup_measure_grt | 7.9 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | postcts_gate_TT | 7.9 | last meaningful line 0.1 h ago (1093/1093 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | postcts_gate_TT | 7.9 | last meaningful line 0.0 h ago (1018/1018 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | 5_2_route | 7.9 | last meaningful line 0.3 h ago (273/274 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l0__cl7a55c676-4020210 | sle_su_l0 | 5_2_route | 7.9 | drt_violations best 34 last 34 rows 10 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_1_grt | 7.9 | last meaningful line 0.2 h ago (2498/2511 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | postcts_gate_TT | 7.9 | last meaningful line 0.0 h ago (773/773 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | tt_setup_repair_grt | 7.9 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | postcts_gate_TT | 7.9 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | 5_2_route | 11.2 | drt_violations best 100793 last 100793 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | postcts_gate_FF | 7.9 | last meaningful line 0.2 h ago (720/720 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3909116 | slw_hc3 | 5_2_route | 7.9 | drt_violations best 88102 last 88102 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-3949912 | slw_hc3 | 5_2_route | 7.9 | drt_violations best 80626 last 80626 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 7.8 | last meaningful line 0.3 h ago (267/268 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 7.8 | last meaningful line 0.3 h ago (275/276 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | 5_2_route | 7.9 | drt_violations best 30201 last 30201 rows 2 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 5_2_route | 7.9 | drt_violations best 134 last 134 rows 21 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | postcts_gate_FF | 7.9 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 7.9 | drt_violations best 28746 last 28746 rows 5 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3t-2289287 | eco_20261123_164145_1995767-i3t | 5_2_route | 5.3 | drt_violations best 35664 last 35664 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261124_225649_3846510-i1-114505 | eco_20261124_225649_3846510-i1 | 5_2_route | 1.0 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 4.8 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R1b_coll_old | relec-r2-R1b_coll_old | - | 4.7 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R4_coll_guard | relec-r2-R4_coll_guard | - | 4.7 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R9_hc3_d5fde | relec-r2-R9_hc3_d5fde | - | 4.6 |  | NO-DATA: no log found |  |
| epyc8 | so_2515398_ff_78023 | so_2515398_ff_78023 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (28/28 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | so_2515398_tt_78023 | so_2515398_tt_78023 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (28/28 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 4.6 | drt_violations best 84487 last 84487 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | 4_1_cts | 4.2 | last meaningful line 0.8 h ago (11126/11126 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_1_grt | 4.8 | repair_Remaining best 89809 last 89809 rows 289 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-1010348 | sle_fw_v1 | 5_1_grt | 4.6 | last meaningful line 0.5 h ago (315/1843 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__clf58b4dfb-733846 | sle_fw_v1 | 5_1_grt | 4.8 | last meaningful line 0.5 h ago (277/1812 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_1_grt | 4.9 | last meaningful line 0.1 h ago (167/167 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-551472 | slw_fw_v1 | 5_1_grt | 5.0 | last meaningful line 0.1 h ago (290/350 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | otc-1893022-28497 | 1893022 | signoff | 1.5 | last meaningful line 1.5 h ago (3/3 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | otc-2115495-15878 | 2115495 | signoff | 1.4 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | otc-2119148-18648 | 2119148 | signoff | 1.4 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | otc-2126591-20932 | 2126591 | signoff | 1.4 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | otc-2136971-27474 | 2136971 | signoff | 1.4 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i3-3801930 | eco_20261123_224216_149959-i3 | 5_2_route | 2.7 | last meaningful line 0.2 h ago (290/291 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
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
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_1_grt | 6.4 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | postcts_gate_TT | 6.6 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | pregrt_ff_hold | 7.2 | repair_Violations best 47647 last 47647 rows 125 | before-window best 314357, window best 47647 | PROGRESS: repair_Violations improved 84.8 % in window |  |
| epyc10 | dpkit-sle_fw_v1__clf58b4dfb-461721 | sle_fw_v1 | 5_1_grt | 4.6 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_1_grt | 6.2 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1583204 | sle_st_b_v1 | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_st_b_v2__clfde1249e-689859 | sle_st_b_v2 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_1_grt | 5.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-856398 | slw_st_b_v1 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 18.9 | drt_violations best 16673 last 16673 rows 14 | before-window best 24397, window best 16673 | PROGRESS: drt_violations improved 31.7 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 11.3 | drt_violations best 1743 last 5229 rows 18 | before-window best 2694, window best 1743 | PROGRESS: drt_violations improved 35.3 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 38.3 | drt_violations best 10129 last 48097 rows 18 | before-window best 14975, window best 10129 | PROGRESS: drt_violations improved 32.4 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 31.6 | drt_violations best 9091 last 9091 rows 16 | before-window best 20899, window best 9091 | PROGRESS: drt_violations improved 56.5 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 16.4 | drt_violations best 11728 last 11728 rows 6 | before-window best 490378, window best 11728 | PROGRESS: drt_violations improved 97.6 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 12.5 | drt_violations best 504597 last 504597 rows 1 | before-window best 504597, window best 504597 | PROGRESS: drt_violations: active iteration at 346306 < best completed total 504597 (in-ite |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | 5_2_route | 12.4 | drt_violations best 3 last 3 rows 8 | before-window best 147028, window best 3 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 16.6 | drt_violations best 69686 last 69686 rows 5 | before-window best 407677, window best 69686 | PROGRESS: drt_violations improved 82.9 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 12.7 | drt_violations best 123176 last 123176 rows 2 | before-window best 400194, window best 123176 | PROGRESS: drt_violations improved 69.2 % in window |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_1_grt | 7.9 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-667540 | sle_hc1 | 5_1_grt | 4.9 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_fw_v2__cl8537f156-601723 | slw_fw_v2 | 5_1_grt | 4.9 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | tt_setup_repair_grt | 4.9 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-slw_fw_v3-1399930 | slw_fw_v3 | 5_1_grt | 5.0 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2160450 | slw_hc3 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 5_1_grt | 6.9 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-coll_ftm-2194683 | coll_ftm | 5_2_route | 2.2 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
