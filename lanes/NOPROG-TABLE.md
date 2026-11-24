# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 12:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 10, 'GRT-LABEL': 4, 'NO-DATA': 21, 'YOUNG': 168, 'PROGRESS': 33}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pv_v5e-402621 | kv3_pv_v5e | pregrt_ff_hold | 4.4 | repair_TNS best 845383 last 845383 rows 1 | before-window best 845383, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_pv_v5n-698511 | kv3_pv_v5n | pregrt_ff_hold | 4.2 | repair_TNS best 21703.3 last 21703.3 rows 1 | before-window best 21703.3, window best 21703.3 | NO-PROGRESS: repair_TNS best 21703.3 vs 21703.3 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_pv_v7-1199684 | kv3_pv_v7 | pregrt_ff_hold | 3.7 | repair_TNS best 24452.9 last 24452.9 rows 1 | before-window best 24452.9, window best 24452.9 | NO-PROGRESS: repair_TNS best 24452.9 vs 24452.9 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | pregrt_ff_hold | 5.8 | repair_TNS best 100323 last 100323 rows 1 | before-window best 100323, window best 100323 | NO-PROGRESS: repair_TNS best 100323 vs 100323 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-HG-CAP decides; neve |
| epyc2 | dpkit-kv3_pv_v5ne-2612763 | kv3_pv_v5ne | pregrt_ff_hold | 5.8 | repair_TNS best 827598 last 827598 rows 1 | before-window best 827598, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-248626 | sle_st_b_v2 | pregrt_ff_hold | 4.7 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (QC-GEOM-UNITS decides;  |
| intel1 | dpkit-kv3_pv_v5-1046392 | kv3_pv_v5 | pregrt_ff_hold | 4.8 | repair_TNS best 169718 last 169718 rows 1 | before-window best 169718, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 20.7 | last meaningful line 9.9 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 9.9 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1797391-24144 | 1797391 | flow3 | 7.6 | last meaningful line 7.2 h ago (208/209 lines) | NO-PROGRESS: no new non-iteration log line for 7.2 h | REPORT-ONLY: lane-own kit (s81-kvleaf-t2-arch deci |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 24.4 | last meaningful line 9.9 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 9.9 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc10 | dpkit-kv3_pv_v6ne-1050153 | kv3_pv_v6ne | 5_1_grt | 3.9 | grt rounds 2 overflow 5:67490 -> 10:53325 | GRT-LABEL: DESIGN-FAIL: overflow 53325 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v7e-1156836 | kv3_pv_v7e | 5_1_grt | 3.8 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc11 | dpkit-kv3_pv_v4ne-3869988 | kv3_pv_v4ne | 5_1_grt | 3.6 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pv_v3ne-3760907 | kv3_pv_v3ne | 5_1_grt | 5.8 | grt rounds 1 overflow 5:47095 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-slw-st-b-v1--cl6357f1cc--pvffd43fdc-dump-2136243 | slw-st-b-v1--cl6357f1cc--pvffd43fdc-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | ap-ageom-kw-slw-st-b-v1--cl6357f1cc--pvffd43fdc-grt-2136243 | slw-st-b-v1--cl6357f1cc--pvffd43fdc-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 3.8 | last meaningful line 2.5 h ago (48/55 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (2541/2541 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1479488 | hd_spn | pregrt_ff_hold | 0.5 | repair_TNS best 61416.9 last 61416.9 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-kv3_hg_v3-1126078 | kv3_hg_v3 | 5_1_grt | 3.8 | last meaningful line 0.0 h ago (167/167 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v2__cle0015330-180086 | kv3_hgi_v2 | 5_1_grt | 1.5 | last meaningful line 0.5 h ago (288/1296 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | pregrt_ff_hold | 4.0 | repair_TNS best 149411 last 149411 rows 1 | YOUNG: evidence 2.2 h < 2.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-1289798 | kv3_pv_v12 | 3_3_place_gp | 0.7 | overflow best 0.2368 last 0.2368 rows 37 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v2-1075302 | kv3_pv_v2 | 5_1_grt | 3.8 | last meaningful line 0.1 h ago (266/268 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v2n-1048434 | kv3_pv_v2n | 5_1_grt | 3.9 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v4-680976 | kv3_pv_v4 | 5_1_grt | 4.2 | last meaningful line 0.5 h ago (266/1272 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v4e-1194094 | kv3_pv_v4e | 5_1_grt | 3.7 | last meaningful line 1.3 h ago (271/1278 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v6-908877 | kv3_pv_v6 | pregrt_ff_hold | 4.0 | repair_TNS best 26222.1 last 26222.1 rows 1 | YOUNG: evidence 1.9 h < 2.5 h |  |
| epyc10 | dpkit-kv3_pv_v6n-1030440 | kv3_pv_v6n | 5_1_grt | 3.9 | last meaningful line 0.0 h ago (153/153 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v1__clf58b4dfb-461721 | sle_fw_v1 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (5387/5387 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-660000 | sle_hc0 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (5652/5652 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | 3_3_place_gp | 0.2 | overflow best 0.7242 last 0.7242 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1583204 | sle_st_b_v1 | 3_3_place_gp | 0.5 | overflow best 0.1654 last 0.1654 rows 42 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__clfde1249e-689859 | sle_st_b_v2 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (5500/5500 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 4_1_cts | 1.9 | last meaningful line 0.2 h ago (5211/5211 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 4_1_cts | 1.9 | last meaningful line 0.5 h ago (5283/5283 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 4_1_cts | 2.0 | last meaningful line 0.3 h ago (8431/8431 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | 3_3_place_gp | 0.6 | overflow best 0.2998 last 0.4693 rows 75 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-2082988 | slw_hc3 | 5_2_route | 6.6 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-856398 | slw_st_b_v1 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (4976/4976 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_stm_v1__cle34a73c3-4063338 | slw_stm_v1 | pregrt_ff_hold | 1.7 | repair_TNS best 14113.9 last 14113.9 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | otc-3605853-9611 | 3605853 | - | 2.0 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R1_coll_a | relec-r2-R1_coll_a | - | 1.7 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R2_coll_eco | relec-r2-R2_coll_eco | - | 1.7 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R3_coll_hint | relec-r2-R3_coll_hint | - | 1.7 |  | NO-DATA: no log found |  |
| epyc10 | relec-r2-R8_hc3_pvcca | relec-r2-R8_hc3_pvcca | - | 1.7 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 6.9 | last meaningful line 3.3 h ago (48/62 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | pregrt_ff_hold | 1.2 | repair_TNS best 758714 last 758714 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc11 | dpkit-kv3_hgi_v8-2088531 | kv3_hgi_v8 | pregrt_ff_hold | 1.5 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc11 | dpkit-kv3_io_cor-3977350 | kv3_io_cor | 5_2_route | 6.4 | drt_violations best 416 last 416 rows 12 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v3e-3783354 | kv3_pv_v3e | 5_1_grt | 3.6 | last meaningful line 0.2 h ago (270/1274 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | pregrt_ff_hold | 3.2 | repair_TNS best 31275.4 last 31275.4 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | 4_1_cts | 3.3 | last meaningful line 0.0 h ago (5898/5898 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-3613474 | sle_hc1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (163/163 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | pregrt_ff_hold | 3.1 | last meaningful line 0.0 h ago (77/77 lines) | YOUNG: evidence 0.9 h < 2.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | pregrt_ff_hold | 3.2 | repair_TNS best 165760 last 165760 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc11 | dpkit-slw_fw_v3-263804 | slw_fw_v3 | 5_1_grt | 3.1 | last meaningful line 0.2 h ago (286/1749 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc2__cl6bcaba89-3858415 | slw_hc2 | 5_1_grt | 3.6 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3838177 | slw_hc3 | 5_1_grt | 3.6 | last meaningful line 0.2 h ago (272/840 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | pregrt_ff_hold | 3.0 | repair_TNS best 162778 last 162778 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc11 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-320042 | slw_st_b_v2 | pregrt_ff_hold | 3.0 | repair_TNS best 137179 last 137179 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc11 | lecautofill-hd_mesh | lecautofill-hd_mesh | - | 17.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc11 | prd-eco_20261124_190641_1260390-i1t-2053304 | eco_20261124_190641_1260390-i1t | 5_2_route | 1.6 | last meaningful line 0.0 h ago (267/267 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i1t-3010529 | eco_20261124_200101_1087713-i1t | 5_1_grt | 0.7 | last meaningful line 0.2 h ago (243/1425 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | prd-fin-3435586 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (1069/1069 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q00__cl622f65d2-3557026 | cbn_q00 | 5_1_grt | 2.5 | last meaningful line 0.2 h ago (275/1285 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-coll_ftm-1783743 | coll_ftm | generate_abstract | 3.7 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-1772768 | sle_hc0 | pregrt_ff_hold | 3.7 | repair_TNS best 14144 last 14144 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-491987 | sle_hc0 | 4_1_cts | 1.7 | last meaningful line 0.2 h ago (5674/5674 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-1254949 | sle_hc2 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (5345/5345 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3414126 | sle_hc2 | pregrt_ff_hold | 2.6 | repair_TNS best 21181.5 last 21181.5 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_hc2__clcc5e3e61-3434617 | sle_hc2 | 4_1_cts | 2.6 | last meaningful line 0.0 h ago (5294/5294 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 8.0 | last meaningful line 0.5 h ago (273/274 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-1186805 | sle_sc_v3 | 5_2_route | 7.0 | drt_violations best 233440 last 233440 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-1784944 | sle_st_a_v1 | 5_2_route | 3.7 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-1826228 | sle_st_a_v1 | 5_2_route | 3.7 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-1538145 | sle_st_a_v2 | 5_2_route | 3.9 | drt_violations best 143253 last 143253 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v3-1868496 | sle_stm_v3 | 5_2_route | 3.6 | last meaningful line 0.1 h ago (255/256 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l0__cl7a55c676-4027948 | sle_su_l0 | 5_2_route | 7.9 | drt_violations best 3 last 6 rows 18 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-4191516 | slw_fw_v2 | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (5926/5926 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1101031 | slw_hc3 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (5068/5068 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3626034 | slw_hc3 | pregrt_ff_hold | 2.5 | repair_TNS best 18293.8 last 18293.8 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-slw_sc_v3-3708441 | slw_sc_v3 | 5_1_grt | 2.4 | last meaningful line 0.3 h ago (1299/1892 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1494307 | slw_st_a_v1 | 5_2_route | 3.9 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-1494646 | slw_st_a_v2 | 5_2_route | 3.9 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3657462 | slw_stm_v2 | pregrt_ff_hold | 2.4 | repair_TNS best 7509.45 last 7509.45 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i3-451477 | eco_20261123_103136_2028090-i3 | 5_2_route | 1.7 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-fin-1677588 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 1.4 |  | NO-DATA: no log found |  |
| epyc2 | relec-r2-R7_reform_mapped | relec-r2-R7_reform_mapped | gate_b.ys | 1.4 | last meaningful line 1.2 h ago (94179/94179 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-1850782 | hd_lep0N_w | 5_2_route | 3.6 | last meaningful line 0.1 h ago (260/261 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-2222980 | sle_fw_v2 | 4_1_cts | 3.4 | last meaningful line 0.2 h ago (6853/6853 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 9.3 | last meaningful line 0.5 h ago (274/275 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 7.9 | last meaningful line 0.0 h ago (253/253 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | pregrt_ff_hold | 3.6 | repair_TNS best 170276 last 170276 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | 5_2_route | 9.1 | drt_violations best 147028 last 147028 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl1bc59e1c-2061343 | slw_hc0 | 4_1_cts | 3.5 | last meaningful line 0.3 h ago (5627/5627 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | 4_1_cts | 3.4 | last meaningful line 0.0 h ago (5822/5822 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 4_1_cts | 3.5 | last meaningful line 0.2 h ago (5790/5790 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-2253577 | slw_hc2 | pregrt_ff_hold | 3.4 | repair_TNS best 21131.1 last 21131.1 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 7.7 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 9.4 | drt_violations best 400194 last 400194 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | pregrt_ff_hold | 3.5 | repair_TNS best 139134 last 139134 rows 1 | YOUNG: evidence 1.5 h < 2.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | postcts_gate_FF | 7.8 | last meaningful line 0.1 h ago (687/687 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | 5_2_route | 9.5 | drt_violations best 126854 last 126854 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | 5_1_grt | 3.4 | last meaningful line 0.1 h ago (143/143 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | otc-2299999-28515 | 2299999 | signoff | 0.6 | last meaningful line 0.5 h ago (3/3 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i3t-3392092 | eco_20261123_171023_3055226-i3t | 5_2_route | 2.7 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_145005_2036075-i2t-1611651 | eco_20261124_145005_2036075-i2t | 5_2_route | 1.1 | last meaningful line 0.0 h ago (250/250 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i1t-3184147 | eco_20261124_175441_992552-i1t | 5_2_route | 2.8 | drt_violations best 30 last 30 rows 8 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i1t-1220925 | eco_20261124_192157_3493836-i1t | 5_2_route | 1.3 | last meaningful line 0.1 h ago (258/259 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-coll_s-3875643 | coll_s | 5_2_route | 4.7 | drt_violations best 25 last 25 rows 14 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | pregrt_ff_hold | 4.6 | repair_TNS best 104019 last 104019 rows 1 | YOUNG: evidence 1.0 h < 2.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | pregrt_ff_hold | 4.6 | repair_TNS best 101814 last 101814 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | 5_1_grt | 4.7 | last meaningful line 0.2 h ago (138/138 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | 5_1_grt | 4.7 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | postcts_gate_FF | 4.6 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-4063882 | sle_st_a_v2 | 5_2_route | 4.6 | drt_violations best 25198 last 25198 rows 2 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | pregrt_ff_hold | 4.6 | repair_TNS best 168371 last 168371 rows 1 | YOUNG: evidence 2.0 h < 2.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 5_1_grt | 4.6 | last meaningful line 0.2 h ago (145/145 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | 5_1_grt | 4.6 | last meaningful line 0.0 h ago (162/162 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v1__clbe630b9c-4072662 | sle_stm_v1 | tt_setup_repair_grt | 4.6 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | 5_1_grt | 4.6 | last meaningful line 0.3 h ago (957/974 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l0__cl7a55c676-4020210 | sle_su_l0 | 5_2_route | 4.6 | drt_violations best 189218 last 189218 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | pregrt_ff_hold | 4.6 | repair_TNS best 242152 last 242152 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | pregrt_ff_hold | 4.6 | repair_TNS best 68063.7 last 68063.7 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | pregrt_ff_hold | 4.6 | repair_TNS best 112221 last 112221 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | 5_2_route | 7.9 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | 5_1_grt | 4.7 | last meaningful line 0.2 h ago (285/854 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-3949912 | slw_hc3 | 5_1_grt | 4.6 | last meaningful line 0.1 h ago (940/957 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | postcts_gate_TT | 4.6 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | postcts_gate_TT | 4.5 | last meaningful line 0.1 h ago (2047/2047 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | 5_2_route | 4.6 | last meaningful line 0.2 h ago (260/261 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 5_2_route | 4.6 | drt_violations best 146485 last 146485 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 5_1_grt | 4.6 | last meaningful line 0.2 h ago (144/144 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-3848540 | slw_su_l0 | 5_2_route | 4.7 | drt_violations best 139516 last 139516 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 4.6 | drt_violations best 274214 last 274214 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3t-2289287 | eco_20261123_164145_1995767-i3t | 5_2_route | 2.1 | last meaningful line 0.2 h ago (287/288 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 1.5 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R1b_coll_old | relec-r2-R1b_coll_old | - | 1.4 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R4_coll_guard | relec-r2-R4_coll_guard | - | 1.5 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-R9_hc3_d5fde | relec-r2-R9_hc3_d5fde | - | 1.4 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-kv3_hub_Wo-2769758 | kv3_hub_Wo | 4_1_cts | 0.2 | last meaningful line 0.2 h ago (45/45 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (10948/10948 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (5255/5255 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-1010348 | sle_fw_v1 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (5219/5220 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__clf58b4dfb-733846 | sle_fw_v1 | 4_1_cts | 1.6 | last meaningful line 0.1 h ago (5397/5397 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-667540 | sle_hc1 | 4_1_cts | 1.6 | last meaningful line 0.1 h ago (5655/5655 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (5986/5986 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-551472 | slw_fw_v1 | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (5456/5456 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v2__cl8537f156-601723 | slw_fw_v2 | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (4905/4905 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | eco-abs-2832271 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.1 h ago (1028/1028 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l0_wfb17da-849937 | qfd_qc_su_lane_w_l0_wfb17da | 5_1_grt | 6.8 | last meaningful line 1.0 h ago (2531/3313 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l1_w460927-787688 | qfd_qc_su_lane_w_l1_w460927 | 5_1_grt | 6.8 | repair_TNS best 23.758 last 23.758 rows 2 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l5_wf949e1-824935 | qfd_qc_su_lane_w_l5_wf949e1 | 5_1_grt | 6.8 | last meaningful line 1.3 h ago (2480/3295 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l6_wb51d05-853896 | qfd_qc_su_lane_w_l6_wb51d05 | 5_1_grt | 6.8 | last meaningful line 1.0 h ago (2543/3248 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc9 | otc-1814577-31530 | 1814577 | - | 6.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-29732-24624 | 29732 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-29851-10135 | 29851 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-30219-7096 | 30219 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc9 | prd-count-p1_tc-3891967 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl1b5a6458-4114232 | cbf_q00 | pregrt_ff_hold | 2.7 | repair_Violations best 321 last 321 rows 41 | YOUNG: evidence 1.3 h < 2.5 h |  |
| intel1 | dpkit-cbn_q11__cl5cc92dfe-4036084 | cbn_q11 | 5_1_grt | 2.8 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-coll_ft__cla4a25d77-56057 | coll_ft | 5_2_route | 2.6 | drt_violations best 12509 last 12509 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v4-3072149 | kv3_hgi_v4 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4659/4659 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 4_1_cts | 5.4 | last meaningful line 0.3 h ago (12744/12744 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v8-3837707 | kv3_pv_v8 | 5_1_grt | 5.7 | last meaningful line 1.0 h ago (274/1282 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-native59-2938294 | native59 | 2_1_floorplan | 0.6 | repair_Viol best 18801 last 18801 rows 1164 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 5_1_grt | 8.0 | last meaningful line 0.2 h ago (251/1257 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v3-1442734 | sle_fw_v3 | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (4833/4833 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2838838 | sle_hc0 | 3_4_place_resized | 0.6 | repair_Remaining best 204090 last 204090 rows 179 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 4_1_cts | 3.6 | last meaningful line 0.1 h ago (5868/5868 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3458150 | sle_hc2 | 4_1_cts | 3.2 | last meaningful line 0.1 h ago (5341/5341 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (4948/4948 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-2919543 | sle_su_l0 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3498094 | slw_fe_v1 | 2_1_floorplan | 0.2 | last meaningful line 0.2 h ago (85/85 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | 5_2_route | 6.0 | last meaningful line 0.3 h ago (268/269 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3282256 | slw_fw_v1 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_1_grt | 7.9 | last meaningful line 0.7 h ago (1285/2092 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v3-1399930 | slw_fw_v3 | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (4934/4934 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-3550607 | slw_hc0 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3463031 | slw_hc1 | 4_1_cts | 3.2 | last meaningful line 0.2 h ago (5850/5850 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-2360221 | slw_hc2 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (4713/4713 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-2314631 | slw_hc2 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2160450 | slw_hc3 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (4529/4530 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-3385979 | slw_st_b_v2 | synth_odb_v | 0.3 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | postcts_gate_TT | 7.9 | last meaningful line 0.1 h ago (1586/1586 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 5_1_grt | 3.6 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1e5219ea-3151439 | slw_su_l0 | 3_3_place_gp | 0.4 | overflow best 0.0998 last 0.0998 rows 48 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-3181498 | slw_su_l0 | 3_3_place_gp | 0.4 | overflow best 0.1205 last 0.1205 rows 46 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-tt_ctlm-3437468 | tt_ctlm | 2_1_floorplan | 0.3 | repair_Viol best 591 last 591 rows 661 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 1.8 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 1.8 |  | NO-DATA: no log found |  |
| intel1 | otc-3854277-21865 | 3854277 | - | 5.7 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261123_191853_2879776-i2t-2852283 | eco_20261123_191853_2879776-i2t | 5_2_route | 3.6 | last meaningful line 0.3 h ago (281/282 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3102716 | coll_ftm | 5_2_route | 1.5 | last meaningful line 0.1 h ago (238/239 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_C-524420 | kv3_hub_C | 2_1_floorplan | 3.2 | last meaningful line 2.8 h ago (1424/1424 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_Wi-487140 | kv3_hub_Wi | 3_3_place_gp | 3.2 | overflow best 0.0983 last 0.0983 rows 49 | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8422a4b86-755770 | kv3_pc_v1 | 2_1_floorplan | 0.1 | repair_Viol best 8518 last 8518 rows 143 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-4094727 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (225/226 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 4_1_cts | 3.1 | last meaningful line 0.2 h ago (5312/5312 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-1226895 | kv3_hgi_v2 | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_hgi_v5-331504 | kv3_hgi_v5 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2793057 | sle_stm_v1 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc11 | dpkit-kv3_hgi_v7-1276815 | kv3_hgi_v7 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc11 | dpkit-sle_fw_v1__cl9d029624-56648 | sle_fw_v1 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 15.7 | drt_violations best 19250 last 19250 rows 12 | before-window best 186583, window best 19250 | PROGRESS: drt_violations improved 89.7 % in window |  |
| epyc2 | dpkit-glue-3558834 | glue | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 8.1 | drt_violations best 1879 last 1879 rows 14 | before-window best 112571, window best 1879 | PROGRESS: drt_violations improved 98.3 % in window |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-4153401 | sle_stm_v2 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 35.1 | drt_violations best 11554 last 11554 rows 16 | before-window best 17065, window best 11554 | PROGRESS: drt_violations improved 32.3 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 28.4 | drt_violations best 11933 last 11933 rows 15 | before-window best 27940, window best 11933 | PROGRESS: drt_violations improved 57.3 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 13.1 | drt_violations best 109083 last 109083 rows 2 | before-window best 490378, window best 109083 | PROGRESS: drt_violations improved 77.8 % in window |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_1_grt | 3.3 | repair_TNS best 0 last 0 rows 14 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 13.3 | drt_violations best 116989 last 116989 rows 3 | before-window best 407677, window best 116989 | PROGRESS: drt_violations improved 71.3 % in window |  |
| epyc7 | prd-eco_20261124_201304_2675397-i1-2517921 | eco_20261124_201304_2675397-i1 | 5_1_grt | 0.5 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_hc1__cl22c1ff36__pve230954c-3918742 | sle_hc1 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3909116 | slw_hc3 | tt_setup_repair_grt | 4.7 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 4_2_tapbal_grt | 1.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l4_w285325-818329 | qfd_qc_su_lane_w_l4_w285325 | 5_1_grt | 6.8 | repair_TNS best 0 last 0 rows 58 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l7_wd4f14d-862251 | qfd_qc_su_lane_w_l7_wd4f14d | 5_1_grt | 6.7 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-coll_core-3813096 | coll_core | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-3662089 | sle_sc_v1 | 5_1_grt | 3.0 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2973163 | slw_hc3 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-kv3_io_ft-265620 | kv3_io_ft | 5_1_grt | 0.5 | repair_TNS best 0 last 0 rows 16 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-60615 | sle_st_b_v2 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 11.9 | drt_violations best 2 last 2 rows 52 | before-window best 58, window best 2 | PROGRESS: drt_violations improved 96.6 % in window |  |
