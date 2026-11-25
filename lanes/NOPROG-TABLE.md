# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 02:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 5, 'GRT-LABEL': 9, 'YOUNG': 143, 'NO-DATA': 21, 'KEEP': 2, 'EXCLUDED': 1, 'PROGRESS': 36}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_hg_v1p2-1802854 | kv3_hg_v1p2 | 5_1_grt | 8.2 | grt rounds 2 overflow 5:44471 -> 10:45255 | UNSIGNABLE: GRT overflow flat: overflow 44471 at iteration 5 -> 45255 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_pv_v3-4187490 | kv3_pv_v3 | pregrt_ff_hold | 5.9 | repair_TNS best 169360 last 169360 rows 1 | before-window best 169360, window best 169360 | NO-PROGRESS: repair_TNS best 169360 vs 169360 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc10 | dpkit-native59-3384403 | native59 | pregrt_ff_hold | 7.5 | repair_TNS best 40160.3 last 40160.3 rows 1 | before-window best 40160.3, window best 40160.3 | NO-PROGRESS: repair_TNS best 40160.3 vs 40160.3 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (QC-GLUE-IMAGES decides; |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 12.3 | repair_TNS best 145595 last 145595 rows 1 | before-window best 145595, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc11 | otc-3389445-25127 | 3389445 | signoff | 9.1 | last meaningful line 9.0 h ago (3/3 lines) | NO-PROGRESS: no new non-iteration log line for 9.0 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc8 | otc-120424-12773 | 120424 | signoff | 7.6 | last meaningful line 7.5 h ago (3/3 lines) | NO-PROGRESS: no new non-iteration log line for 7.5 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | tt_setup_repair_grt | 14.2 | repair_Violations best 25 last 257 rows 29 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -492.14 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_hg_v1p3__r81da466fe-1840159 | kv3_hg_v1p3__r81da466fe | 5_1_grt | 8.1 | grt rounds 2 overflow 5:40256 -> 10:36108 | GRT-LABEL: DESIGN-FAIL: overflow 36108 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | 5_1_grt | 12.4 | grt rounds 2 overflow 5:94600 -> 10:59159 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc11 | dpkit-kv3_pv_v3ne-1144152 | kv3_pv_v3ne | 5_1_grt | 0.6 | grt rounds 2 overflow 5:47095 -> 10:34560 | GRT-LABEL: DESIGN-FAIL: overflow 34560 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v4-1052719 | kv3_pv_v4 | 5_1_grt | 0.6 | grt rounds 2 overflow 5:93111 -> 10:84388 | GRT-LABEL: DESIGN-FAIL: overflow 84388 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v4e-1100418 | kv3_pv_v4e | 5_1_grt | 0.6 | grt rounds 2 overflow 5:112464 -> 10:88021 | GRT-LABEL: DESIGN-FAIL: overflow 88021 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v6e-864517 | kv3_pv_v6e | 5_1_grt | 0.7 | grt rounds 2 overflow 5:59143 -> 10:37875 | GRT-LABEL: DESIGN-FAIL: overflow 37875 at round 10 > 1000 |  |
| epyc2 | dpkit-kv3_hgi_v8-2737550 | kv3_hgi_v8 | 5_1_grt | 7.6 | grt rounds 2 overflow 5:54135 -> 10:40850 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-3490222 | cbn_q01 | 5_1_grt | 0.5 | grt rounds 2 overflow 5:81921 -> 10:75607 | GRT-LABEL: DESIGN-FAIL: overflow 75607 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi_v6-102352 | kv3_hgi_v6 | 5_1_grt | 8.6 | grt rounds 2 overflow 5:53849 -> 10:29026 | GRT-LABEL: DESIGN-FAIL: overflow 29026 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_hg_v1p5-970860 | kv3_hg_v1p5 | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (6746/6746 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | pregrt_ff_hold | 8.6 | repair_TNS best 293385 last 293385 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-961899 | kv3_pc_v1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (6055/6055 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r877307f5d-1492582 | kv3_pc_v1 | 4_1_cts | 0.2 | last meaningful line 0.2 h ago (37/37 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-19761 | kv3_pc_v1 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (6200/6200 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl7f648944__r8f64f1de3-2041438 | kv3_pc_v1 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-1535838 | kv3_pv_v12 | 5_1_grt | 6.8 | last meaningful line 0.7 h ago (268/1275 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_2_route | 16.2 | drt_violations best 416066 last 416066 rows 1 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | 5_3_fillcell | 13.1 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | 5_2_route | 13.5 | drt_violations best 23137 last 23137 rows 2 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | 6_report | 14.0 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 15.2 | drt_violations best 272423 last 272423 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_2_route | 15.2 | last meaningful line 0.4 h ago (278/279 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 5_2_route | 15.2 | last meaningful line 0.3 h ago (270/271 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | postcts_gate_FF | 13.8 | last meaningful line 0.0 h ago (391/391 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2082061 | slw_st_a_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5928/5929 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | 6_report | 13.0 | last meaningful line 0.1 h ago (69/69 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3681869 | slw_st_b_v2 | 5_2_route | 9.5 | drt_violations best 129849 last 129849 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | 5_3_fillcell | 11.9 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_055922_2792445-i1-2623359 | eco_20261125_055922_2792445-i1 | 5_2_route | 4.0 | drt_violations best 137 last 137 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_073109_4058437-i1t-725979 | eco_20261125_073109_4058437-i1t | 5_2_route | 2.4 | last meaningful line 0.3 h ago (273/274 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v2e-1156839 | kv3_pv_v2e | lec | 0.6 | LEC last write 0.0 h ago | YOUNG: evidence 0.6 h < 6 h |  |
| epyc11 | dpkit-kv3_pv_v4ne-1191938 | kv3_pv_v4ne | lec | 0.6 | LEC last write 0.0 h ago | YOUNG: evidence 0.6 h < 6 h |  |
| epyc11 | dpkit-kv3_pv_v5-1052229 | kv3_pv_v5 | lec | 0.6 | LEC last write 0.1 h ago | YOUNG: evidence 0.6 h < 6 h |  |
| epyc11 | dpkit-kv3_pv_v5e-1092206 | kv3_pv_v5e | lec | 0.6 | LEC last write 0.0 h ago | YOUNG: evidence 0.6 h < 6 h |  |
| epyc11 | dpkit-kv3_pv_v7-1078343 | kv3_pv_v7 | lec | 0.6 | LEC last write 0.0 h ago | YOUNG: evidence 0.6 h < 6 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 5_2_route | 12.1 | drt_violations best 166686 last 166686 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 5_2_route | 11.8 | last meaningful line 0.5 h ago (279/280 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | postcts_gate_TT | 6.8 | last meaningful line 0.1 h ago (575/575 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl92142dac-2960548 | slw_su_c | 4_1_cts | 3.1 | last meaningful line 0.3 h ago (8520/8520 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 15.5 |  | NO-DATA: no log found |  |
| epyc11 | otc-381902-2867 | 381902 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc11 | otc-701258-11435 | 701258 | lec | 2.4 | LEC last write 2.4 h ago | YOUNG: evidence 2.4 h < 6 h |  |
| epyc11 | otc-701492-14947 | 701492 | lec | 2.4 | LEC last write 2.4 h ago | YOUNG: evidence 2.4 h < 6 h |  |
| epyc11 | prd-eco_20261124_154417_1016084-i2-2211039 | eco_20261124_154417_1016084-i2 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i2t-2255468 | eco_20261124_190641_1260390-i2t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_054540_316017-i1-897106 | eco_20261125_054540_316017-i1 | 5_2_route | 4.2 | drt_violations best 18 last 18 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_080242_341091-i1-2097287 | eco_20261125_080242_341091-i1 | 5_2_route | 1.9 | last meaningful line 0.3 h ago (133/133 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_080337_31727-i1-2053095 | eco_20261125_080337_31727-i1 | 5_2_route | 1.9 | last meaningful line 0.3 h ago (128/128 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_082938_54055-i1-3146788 | eco_20261125_082938_54055-i1 | 5_2_route | 1.4 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_092112_274675-i1-1256057 | eco_20261125_092112_274675-i1 | 5_1_grt | 0.5 | last meaningful line 0.3 h ago (144/144 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_092728_2532622-i1-1376598 | eco_20261125_092728_2532622-i1 | 5_1_grt | 0.5 | last meaningful line 0.3 h ago (139/139 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | prd-fin-249436 | fin | 6_report | 0.3 | last meaningful line 0.0 h ago (1069/1069 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | so_2186946_ff_58433 | so_2186946_ff_58433 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (1034/1034 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | so_2186946_tt_58433 | so_2186946_tt_58433 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (1034/1034 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-hd_lep0N-914468 | hd_lep0N | 3_3_place_gp | 0.5 | overflow best 0.3419 last 0.3482 rows 34 | YOUNG: stage 0.2 h < 1 h |  |
| epyc12 | dpkit-kv3_hgi_v7-1411551 | kv3_hgi_v7 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (1307/1307 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl7f648944__r8422a4b86-1394259 | kv3_pc_v1 | 2_1_floorplan | 0.1 | repair_Viol best 8518 last 8518 rows 619 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-kv3_pv_v12-1045687 | kv3_pv_v12 | 3_3_place_gp | 0.4 | overflow best 0.5308 last 0.5379 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-kv3_pv_v1n-1216451 | kv3_pv_v1n | 2_1_floorplan | 0.3 | repair_Viol best 6468 last 6468 rows 1657 | YOUNG: stage 0.2 h < 1 h |  |
| epyc12 | dpkit-native59-1179753 | native59 | 2_1_floorplan | 0.3 | last meaningful line 0.1 h ago (1360/1360 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_sys_c-3635023 | kv3_sys_c | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-3226126 | sle_hc0 | 3_3_place_gp | 0.3 | overflow best 0.6725 last 0.6725 rows 30 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (6917/6917 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-3286653 | sle_st_a_v2 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5355/5355 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1216203 | sle_st_b_v1 | 5_2_route | 6.0 | last meaningful line 0.1 h ago (275/276 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-360401 | sle_st_b_v2 | 5_2_route | 5.0 | last meaningful line 0.1 h ago (144/144 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2601551 | slw_st_a_v1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (6198/6198 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | otc-2040585-24869 | 2040585 | - | 2.5 |  | NO-DATA: no log found |  |
| epyc2 | otc-2864129-1602 | 2864129 | eq15 | 0.4 | last meaningful line 0.1 h ago (792009/792009 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | otc-785042-5629 | 785042 | - | 2.9 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261124_204708_4151707-i1-226978 | eco_20261124_204708_4151707-i1 | 5_2_route | 1.6 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 14.7 |  | NO-DATA: no log found |  |
| epyc2 | so_2928260_ff_72863 | so_2928260_ff_72863 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc2 | so_2928260_tt_72863 | so_2928260_tt_72863 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc2 | so_3507221_ff_28342 | so_3507221_ff_28342 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_3507221_tt_28342 | so_3507221_tt_28342 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_3555422_ff_62694 | so_3555422_ff_62694 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (35/35 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_3555422_tt_62694 | so_3555422_tt_62694 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (35/35 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00_s2-3518685 | cbf_q00_s2 | pregrt_ff_hold | 3.7 | repair_Violations best 1579 last 1579 rows 36 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc7 | dpkit-coll_core-3493022 | coll_core | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (11171/11171 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | pregrt_ff_hold | 9.4 | repair_TNS best 275514 last 275514 rows 1 | YOUNG: evidence 1.7 h < 2.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | 4_1_cts | 3.6 | last meaningful line 0.0 h ago (5390/5390 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (5779/5779 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (5646/5646 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v3-2521918 | sle_sc_v3 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (3968/3968 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3817081 | sle_st_a_v2 | postcts_gate_TT | 2.0 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__clc6d66f5b-2521917 | sle_su_l1 | pregrt_ff_hold | 0.9 | repair_TNS best 5119.53 last 5119.53 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-577851 | slw_sc_v1 | hold_gate | 1.7 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (5706/5706 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_1_grt | 3.6 | last meaningful line 0.8 h ago (1301/2024 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-3807127 | slw_su_l1 | 5_2_route | 3.6 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i3-2994934 | eco_20261124_175441_992552-i3 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (252/253 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i2t-2177999 | eco_20261124_192157_3493836-i2t | 5_2_route | 2.6 | drt_violations best 499 last 499 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i2-3644612 | eco_20261124_235631_1843084-i2 | 5_1_grt | 0.4 | last meaningful line 0.4 h ago (297/1388 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_073745_2194631-i1-2944509 | eco_20261125_073745_2194631-i1 | 5_2_route | 2.3 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_073945_2252980-i1t-3004488 | eco_20261125_073945_2252980-i1t | 5_2_route | 2.3 | drt_violations best 544 last 544 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_081621_2016666-i1-599553 | eco_20261125_081621_2016666-i1 | 5_2_route | 1.6 | last meaningful line 0.0 h ago (255/255 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_094206_1890550-i1-4068402 | eco_20261125_094206_1890550-i1 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (143/143 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | so_296151_ff_37610 | so_296151_ff_37610 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | so_296151_tt_37610 | so_296151_tt_37610 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | so_3546323_ff_14786 | so_3546323_ff_14786 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc7 | so_3546323_tt_14786 | so_3546323_tt_14786 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_2_route | 17.9 | drt_violations best 320246 last 320246 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 17.9 | drt_violations best 266434 last 266434 rows 1 | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 6_report | 17.9 | last meaningful line 0.1 h ago (69/69 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | otc-3678186-167 | 3678186 | - | 3.3 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3-32256 | eco_20261123_164145_1995767-i3 | 5_2_route | 6.1 | drt_violations best 16767 last 16767 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_025941_3548303-i1-3306668 | eco_20261125_025941_3548303-i1 | 5_1_grt | 1.0 | last meaningful line 0.3 h ago (294/402 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_065854_3885412-i1-521874 | eco_20261125_065854_3885412-i1 | 5_2_route | 3.0 | drt_violations best 18 last 18 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_082653_3900765-i1-1572735 | eco_20261125_082653_3900765-i1 | 5_2_route | 1.5 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_091937_4000900-i1-378808 | eco_20261125_091937_4000900-i1 | 5_1_grt | 0.6 | last meaningful line 0.3 h ago (144/144 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 14.8 |  | NO-DATA: no log found |  |
| epyc8 | so_1571712_ff_42723 | so_1571712_ff_42723 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc8 | so_1571712_tt_42723 | so_1571712_tt_42723 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc8 | so_2176134_ff_15012 | so_2176134_ff_15012 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc8 | so_2176134_tt_15012 | so_2176134_tt_15012 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | tt_setup_repair | 3.3 | repair_Viol best 252 last 252 rows 25 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pv07945c1e-55623 | col_h10_r0_p4__t1 | lec | 3.8 | LEC last write 0.0 h ago | YOUNG: evidence 3.8 h < 6 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | lec | 3.3 | LEC last write 0.1 h ago | YOUNG: evidence 3.3 h < 6 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3378330 | col_h9_r0_p1__t1 | 5_1_grt | 3.3 | last meaningful line 0.7 h ago (273/1282 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b-3679007 | col_h9_r0_p3__t1 | 5_1_grt | 3.3 | last meaningful line 0.5 h ago (274/1290 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-296584 | col_h9_r0_p3__t1 | 5_1_grt | 5.8 | last meaningful line 0.9 h ago (271/1289 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | pregrt_ff_hold | 3.3 | repair_TNS best 150413 last 150413 rows 1 | YOUNG: evidence 1.7 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3184/3184 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-4053150 | col_h9_r1__t1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4401/4401 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49f0ba38-4029031 | col_h9_r1__t1 | 3_5_place_dp | 0.4 | repair_Violations best 122 last 122 rows 19 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv31e47bd5-4047516 | col_h9_r2__t1 | 4_2_tapbal_grt | 0.4 | last meaningful line 0.0 h ago (61/64 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 5.1 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-3394850 | col_h9_r2__t1 | 5_1_grt | 3.3 | last meaningful line 0.0 h ago (153/153 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-3707756 | col_h9_r2__t1 | tt_setup_repair_grt | 3.3 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve0486b40-3725060 | col_h9_r2__t1 | pregrt_ff_hold | 1.1 | repair_TNS best 29815.1 last 29815.1 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | lec | 4.3 | LEC last write 0.1 h ago | YOUNG: evidence 4.3 h < 6 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t10-3695203 | dsdv_slice_c1x_C__t10 | port_bind | 2.3 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-578982 | dsdv_slice_c1x_C__t8 | selrange | 2.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-3691225 | dsdv_slice_c1x_C__t9 | selrange | 2.3 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_kv512_C__t1-4058196 | dsdv_slice_kv512_C__t1 | 2_1_floorplan | 0.4 | repair_Viol best 2812 last 2812 rows 1041 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t4-4027540 | ot_s81sl_kv_leaf__t4 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (265/265 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t25__cl55642d17-3495886 | ot_s81sl_leaf__t25 | pregrt_ff_hold | 1.2 | repair_Violations best 540 last 545 rows 106 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t36-3727117 | ot_s81sl_leaf__t36 | 5_1_grt | 3.3 | last meaningful line 0.5 h ago (264/1272 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-3479533 | slice_station__t37 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (4130/4130 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t43-3486441 | slice_station__t43 | lec | 1.2 | LEC last write 0.0 h ago | YOUNG: evidence 1.2 h < 6 h |  |
| epyc9 | prd-eco_20261125_090100_666856-i1-787277 | eco_20261125_090100_666856-i1 | 5_1_grt | 0.9 | last meaningful line 0.3 h ago (290/365 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-2627901 | col_h9_r1__t1 | 2_1_floorplan | 0.0 | repair_Viol best 3589 last 3589 rows 143 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1177242 | kv3_hg_v1p3__r838481cd7 | pregrt_ff_hold | 2.3 | repair_TNS best 5295.85 last 5295.85 rows 1 | YOUNG: evidence 2.3 h < 2.5 h |  |
| intel1 | dpkit-serdes__t15__cla3d02796-2608833 | serdes__t15 | 1_2_yosys | 0.1 | last meaningful line -0.0 h ago (159/159 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 5_2_route | 16.9 | drt_violations best 23446 last 23446 rows 2 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | postcts_gate_TT | 9.0 | last meaningful line 0.2 h ago (17/17 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 5_2_route | 13.2 | last meaningful line 0.3 h ago (139/139 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t27-2240821 | slice_station__t27 | 3_3_place_gp | 0.3 | overflow best 0.3866 last 0.3866 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slice_station__t30__cl1653104c-2235281 | slice_station__t30 | 3_3_place_gp | 0.3 | overflow best 0.2371 last 0.2486 rows 29 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_1_grt | 10.7 | last meaningful line 0.4 h ago (2537/2554 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3325358 | slw_fw_v1 | postcts_gate_TT | 10.7 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 5_2_route | 11.7 | last meaningful line 0.5 h ago (269/270 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 5_2_route | 13.0 | last meaningful line 0.3 h ago (283/284 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 5_2_route | 16.9 | drt_violations best 138053 last 138053 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 5_1_grt | 11.4 | last meaningful line 0.1 h ago (2142/2195 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 15.0 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 15.0 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261124_235251_4176465-i1-1838007 | eco_20261124_235251_4176465-i1 | 5_2_route | 2.1 | last meaningful line 0.1 h ago (257/258 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1t-3347319 | eco_20261125_002226_1452841-i1t | 5_1_grt | 1.6 | last meaningful line 0.7 h ago (294/447 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | so_1094763_ff_89367 | so_1094763_ff_89367 | generate_abstract | 0.9 | last meaningful line 0.8 h ago (876/876 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | so_1094763_tt_89367 | so_1094763_tt_89367 | generate_abstract | 0.9 | last meaningful line 0.8 h ago (876/876 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | so_2251454_ff_71744 | so_2251454_ff_71744 | signoff | 0.3 |  | NO-DATA: empty log |  |
| intel1 | so_2251454_tt_71744 | so_2251454_tt_71744 | signoff | 0.3 |  | NO-DATA: empty log |  |
| intel2 | dpkit-coll_ftm-3587886 | coll_ftm | 5_2_route | 1.2 | last meaningful line 0.1 h ago (230/231 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-862971 | kv3_io_ft | 5_2_route | 0.7 | last meaningful line 0.0 h ago (211/211 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-705307 | kv3_pc_v1 | 3_3_place_gp | 0.8 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8e7d31598-707215 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.1492 last 0.1492 rows 45 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-kv3_pv_v7e-3092815 | kv3_pv_v7e | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v1__cl9d029624-1206811 | sle_fw_v1 | 3_3_place_gp | 0.5 | overflow best 0.1956 last 0.1956 rows 36 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-1350166 | slice_station__t12 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (66/66 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-2390236 | slw_st_b_v1 | 5_2_route | 9.4 | drt_violations best 154733 last 154733 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel2 | otc-594090-20209 | 594090 | eq13_out | 0.8 | last meaningful line 0.2 h ago (705676/705676 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-1955823 | kv3_hgi | 5_1_grt | 0.1 |  | KEEP: kv3_hgi_1124155644	KV-OWN-RSTREACH	combined HEADLEG2+HGI-LEAF ship form; noprog  |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-436421 | kv3_hgi_v2 | 5_1_grt | 0.5 |  | KEEP: kv3_hgi_v2__cl2862d491_1124155702	KV-OWN-RSTREACH	combined hgi_v2 ship form (COO |  |
| intel1 | prd-eco_qcgu_1125-i1-3514577 | eco_qcgu_1125-i1 | 5_1_grt | 1.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 16.5 | drt_violations best 58968 last 58968 rows 3 | before-window best 329677, window best 58968 | PROGRESS: drt_violations improved 82.1 % in window |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 28.9 | drt_violations best 14980 last 63558 rows 18 | before-window best 15279, window best 14980 | PROGRESS: drt_violations: falling inside the active iteration (63558 -> 44681) |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 5_2_route | 13.1 | drt_violations best 1 last 1 rows 26 | before-window best 168194, window best 1 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 21.2 | drt_violations best 6298 last 6298 rows 16 | before-window best 16679, window best 6298 | PROGRESS: drt_violations improved 62.2 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 41.6 | drt_violations best 5806 last 5806 rows 22 | before-window best 7726, window best 5806 | PROGRESS: drt_violations improved 24.9 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 26.4 | drt_violations best 2761 last 13398 rows 18 | before-window best 3524, window best 2761 | PROGRESS: drt_violations improved 21.7 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 22.5 | drt_violations best 6764 last 6764 rows 12 | before-window best 84872, window best 6764 | PROGRESS: drt_violations improved 92.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 21.2 | drt_violations best 19919 last 19919 rows 8 | before-window best 510309, window best 19919 | PROGRESS: drt_violations improved 96.1 % in window |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 16.6 | drt_violations best 71668 last 71668 rows 5 | before-window best 412199, window best 71668 | PROGRESS: drt_violations improved 82.6 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 21.0 | drt_violations best 11873 last 11873 rows 9 | before-window best 457993, window best 11873 | PROGRESS: drt_violations improved 97.4 % in window |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 26.6 | drt_violations best 62636 last 62636 rows 11 | before-window best 66691, window best 62636 | PROGRESS: drt_violations improved 6.1 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 22.7 | drt_violations best 51610 last 51610 rows 10 | before-window best 55677, window best 51610 | PROGRESS: drt_violations improved 7.3 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-534954 | slw_su_l1 | tt_setup_repair_grt | 3.2 | repair_Violations best 0 last 0 rows 46 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 5_2_route | 17.9 | drt_violations best 11608 last 11608 rows 3 | before-window best 129389, window best 11608 | PROGRESS: drt_violations improved 91.0 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 17.8 | drt_violations best 35768 last 35768 rows 4 | before-window best 478667, window best 35768 | PROGRESS: drt_violations improved 92.5 % in window |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 5_2_route | 17.9 | drt_violations best 18101 last 18101 rows 2 | before-window best 131388, window best 18101 | PROGRESS: drt_violations improved 86.2 % in window |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 5_2_route | 17.9 | drt_violations best 0 last 0 rows 20 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 5_2_route | 17.9 | drt_violations best 25161 last 25161 rows 2 | before-window best 146375, window best 25161 | PROGRESS: drt_violations improved 82.8 % in window |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 5_2_route | 17.9 | drt_violations best 22164 last 22164 rows 2 | before-window best 138449, window best 22164 | PROGRESS: drt_violations improved 84.0 % in window |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 17.8 | drt_violations best 105634 last 105634 rows 2 | before-window best 450083, window best 105634 | PROGRESS: drt_violations improved 76.5 % in window |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 17.8 | drt_violations best 52545 last 52545 rows 6 | before-window best 379431, window best 52545 | PROGRESS: drt_violations improved 86.2 % in window |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 5_2_route | 17.9 | drt_violations best 31 last 31 rows 7 | before-window best 141263, window best 31 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 17.9 | drt_violations best 8666 last 8666 rows 16 | before-window best 15345, window best 8666 | PROGRESS: drt_violations improved 43.5 % in window |  |
| epyc8 | prd-eco_20261125_071225_3873455-i1-1532615 | eco_20261125_071225_3873455-i1 | 5_2_route | 2.7 | drt_violations best 0 last 0 rows 1 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3698869 | col_h9_r0_p4__t1 | 4_2_tapbal_grt | 1.1 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 14.6 | drt_violations best 1371 last 1548 rows 30 | before-window best 1557, window best 1371 | PROGRESS: drt_violations improved 11.9 % in window |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_2_route | 14.8 | drt_violations best 55115 last 55115 rows 5 | before-window best 474459, window best 55115 | PROGRESS: drt_violations improved 88.4 % in window |  |
| epyc9 | dpkit-slice_station__t42__clcf44e680-3472830 | slice_station__t42 | 5_1_grt | 1.2 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 14.9 | drt_violations best 799 last 799 rows 14 | before-window best 274895, window best 799 | PROGRESS: drt_violations improved 99.7 % in window |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 5_2_route | 21.2 | drt_violations best 317907 last 317907 rows 1 | before-window best 317907, window best 317907 | PROGRESS: drt_violations: active iteration at 141639 < best completed total 317907 (in-ite |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 5_2_route | 14.9 | drt_violations best 21522 last 21522 rows 2 | before-window best 144494, window best 21522 | PROGRESS: drt_violations improved 85.1 % in window |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 13.1 | drt_violations best 38 last 38 rows 15 | before-window best 187976, window best 38 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 21.2 | drt_violations best 104690 last 104690 rows 2 | before-window best 398476, window best 104690 | PROGRESS: drt_violations improved 73.7 % in window |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 5_2_route | 16.9 | drt_violations best 0 last 0 rows 9 | PROGRESS: drt_violations reached 0 |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 16.4 | drt_violations best 20493 last 20493 rows 4 | before-window best 367946, window best 20493 | PROGRESS: drt_violations improved 94.4 % in window |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 5_2_route | 16.6 | drt_violations best 6548 last 6548 rows 10 | before-window best 406352, window best 6548 | PROGRESS: drt_violations improved 98.4 % in window |  |
