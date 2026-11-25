# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 22:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'UNSIGNABLE': 3, 'GRT-LABEL': 11, 'YOUNG': 153, 'NO-DATA': 24, 'PROGRESS': 30}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 13.8 | last meaningful line 12.5 h ago (48/140 lines) | NO-PROGRESS: no new non-iteration log line for 12.5 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 5_1_grt | 14.1 | grt rounds 2 overflow 5:42234 -> 10:42876 | UNSIGNABLE: GRT overflow flat: overflow 42234 at iteration 5 -> 42876 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 16.9 | last meaningful line 13.3 h ago (48/208 lines) | NO-PROGRESS: no new non-iteration log line for 13.3 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | 5_1_grt | 11.2 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 9.1 | repair_TNS best 121785 last 121785 rows 1 | before-window best 121785, window best 121785 | NO-PROGRESS: repair_TNS best 121785 vs 121785 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 5_1_grt | 15.8 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 38.4 | drt_violations best 7726 last 8463 rows 20 | before-window best 7726, window best 8463 | NO-PROGRESS: drt_violations best 8463 vs 7726 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (OPUS-FIX-S81-COL-RANKSE |
| epyc10 | dpkit-kv3_hg_v1__r889141819-1619104 | kv3_hg_v1__r889141819 | 5_1_grt | 5.0 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_hg_v1__r88f4bfb40-1671162 | kv3_hg_v1__r88f4bfb40 | 5_1_grt | 5.0 | grt rounds 1 overflow 5:42362 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_hgi-373156 | kv3_hgi | 5_1_grt | 5.7 | grt rounds 2 overflow 5:32028 -> 10:31100 | GRT-LABEL: DESIGN-FAIL: overflow 31100 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r8b421e514-2986767 | kv3_pc | 5_1_grt | 3.1 | grt rounds 2 overflow 5:7207 -> 10:4296 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r85c02c25c-3151820 | kv3_pc | 5_1_grt | 3.1 | grt rounds 2 overflow 5:7303 -> 10:4851 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r882954158-3053902 | kv3_pc | 5_1_grt | 3.1 | grt rounds 2 overflow 5:6934 -> 10:4576 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | 5_1_grt | 14.0 | grt rounds 2 overflow 5:52829 -> 10:36669 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | 5_1_grt | 9.2 | grt rounds 2 overflow 5:94600 -> 10:59159 | GRT-LABEL: DESIGN-FAIL: overflow 59159 at round 10 > 1000 |  |
| epyc2 | dpkit-kv3_hgi_v8-2737550 | kv3_hgi_v8 | 5_1_grt | 4.3 | grt rounds 2 overflow 5:54135 -> 10:40850 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-1559108 | cbn_q01 | 5_1_grt | 6.0 | grt rounds 2 overflow 5:81921 -> 10:75607 | GRT-LABEL: DESIGN-FAIL: overflow 75607 at round 10 > 1000 |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | 5_1_grt | 11.0 | grt rounds 2 overflow 5:34556 -> 10:3532 | GRT-LABEL: DESIGN-FAIL: overflow 3532 at round 10 > 1000 |  |
| epyc10 | dpkit-glue-1294589 | glue | 5_1_grt | 5.2 | last meaningful line 0.4 h ago (278/862 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1__r8dffc461a-1676050 | kv3_hg_v1__r8dffc461a | 5_1_grt | 5.0 | last meaningful line 0.3 h ago (287/1292 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p3__r81da466fe-1840159 | kv3_hg_v1p3__r81da466fe | 5_1_grt | 4.9 | last meaningful line 0.0 h ago (218/224 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | 4_1_cts | 5.3 | last meaningful line 0.2 h ago (11295/11295 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-2844240 | kv3_pc | 5_1_grt | 3.2 | last meaningful line 0.0 h ago (181/181 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-3561929 | kv3_pc_v1 | 3_5_place_dp | 2.9 | last meaningful line 1.0 h ago (32/32 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r84d0332e1-3581607 | kv3_pc_v1 | 3_5_place_dp | 2.9 | last meaningful line 0.8 h ago (32/32 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r884969661-3601103 | kv3_pc_v1 | 3_5_place_dp | 2.9 | last meaningful line 0.8 h ago (32/32 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8afe1e027-3618066 | kv3_pc_v1 | 3_5_place_dp | 2.9 | last meaningful line 1.0 h ago (32/32 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8c9cba7ae-3633962 | kv3_pc_v1 | 3_5_place_dp | 2.9 | last meaningful line 1.0 h ago (32/32 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-3669242 | kv3_pc_v1 | 3_5_place_dp | 2.9 | last meaningful line 1.0 h ago (32/32 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-1535838 | kv3_pv_v12 | pregrt_ff_hold | 3.5 | repair_TNS best 42717.5 last 42717.5 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-4187490 | kv3_pv_v3 | 4_1_cts | 2.7 | last meaningful line 0.2 h ago (12071/12071 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-native59-3384403 | native59 | pregrt_ff_hold | 4.2 | repair_TNS best 6612.64 last 6612.64 rows 1 | YOUNG: evidence 1.9 h < 2.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_2_route | 13.0 | last meaningful line 0.5 h ago (272/273 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | 5_2_route | 9.8 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | 5_2_route | 10.2 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | 5_2_route | 10.8 | drt_violations best 127354 last 127354 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 11.9 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_2_route | 11.9 | last meaningful line 0.5 h ago (133/133 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | postcts_gate_FF | 12.0 | last meaningful line 0.3 h ago (776/776 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | 5_1_grt | 10.6 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | 5_2_route | 9.7 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3681869 | slw_st_b_v2 | postcts_gate_TT | 6.2 | last meaningful line 0.0 h ago (1088/1088 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | 5_2_route | 8.7 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_stm_v1__cle34a73c3-4063338 | slw_stm_v1 | generate_abstract | 11.7 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | qc-hc3-lec-r8-nearest | qc-hc3-lec-r8-nearest | - | 7.7 |  | NO-DATA: no log found |  |
| epyc10 | qccollslec_h4 | qccollslec_h4 | - | 2.7 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 13.2 | drt_violations best 329677 last 329677 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 5_2_route | 8.8 | last meaningful line 0.1 h ago (131/131 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 5_2_route | 9.8 | drt_violations best 168194 last 168194 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | generate_abstract | 13.3 | last meaningful line 0.1 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | postcts_gate_FF | 8.5 | last meaningful line 0.1 h ago (386/386 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | 5_2_route | 13.1 | drt_violations best 20042 last 20042 rows 2 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2533872 | slw_hc3 | 5_2_route | 6.9 | drt_violations best 87718 last 87718 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | pregrt_ff_hold | 3.5 | repair_TNS best 20547.1 last 20547.1 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | 6_report | 13.0 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 12.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-2569403-29272 | 2569403 | ot_bind_native_79ef55e72a0edb8e46a95203 | 0.0 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | otc-3389445-25127 | 3389445 | signoff | 5.8 | last meaningful line 5.8 h ago (3/3 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_154417_1016084-i2t-1425156 | eco_20261124_154417_1016084-i2t | 5_2_route | 3.6 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i1-3660942 | eco_20261124_200101_1087713-i1 | 5_2_route | 5.5 | drt_violations best 37 last 37 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_204246_1187010-i1-249436 | eco_20261124_204246_1187010-i1 | 5_2_route | 4.6 | last meaningful line 0.2 h ago (282/283 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_034700_3857841-i1-2214083 | eco_20261125_034700_3857841-i1 | 5_2_route | 2.9 | drt_violations best 15 last 15 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_054540_316017-i1-897106 | eco_20261125_054540_316017-i1 | 5_1_grt | 0.9 | last meaningful line 0.3 h ago (295/319 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1216203 | sle_st_b_v1 | pregrt_ff_hold | 2.8 | repair_TNS best 7036.13 last 7036.13 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3668964 | sle_st_b_v2 | 5_2_route | 6.5 | last meaningful line 0.1 h ago (275/276 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | otc-2459734-26514 | 2459734 | signoff | 2.3 | last meaningful line 2.3 h ago (3/3 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | otc-2882933-23086 | 2882933 | signoff | 0.4 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | otc-3544630-5805 | 3544630 | signoff | 3.9 | last meaningful line 3.8 h ago (3/3 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | prd-count-p1_bc-3663711 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_165709_1862160-i1-2284188 | eco_20261124_165709_1862160-i1 | 5_2_route | 2.4 | drt_violations best 46 last 46 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_204708_4151707-i1t-4056582 | eco_20261124_204708_4151707-i1t | 5_2_route | 1.9 | last meaningful line 0.1 h ago (281/282 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_215436_3656110-i1-2033351 | eco_20261124_215436_3656110-i1 | 5_2_route | 0.8 | last meaningful line 0.1 h ago (133/133 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 11.4 |  | NO-DATA: no log found |  |
| epyc2 | so_3717984_ff_86272 | so_3717984_ff_86272 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_3717984_tt_86272 | so_3717984_tt_86272 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_3721496_ff_199 | so_3721496_ff_199 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_3721496_tt_199 | so_3721496_tt_199 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-slw-su-l1--cla2a78701-grt-309948 | slw-su-l1--cla2a78701-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | colh10cen_k1_310455 | colh10cen_k1_310455 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | colh10cen_k2_309548 | colh10cen_k2_309548 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | colh10cen_k3_308917 | colh10cen_k3_308917 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbf_q00_s2-3518685 | cbf_q00_s2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (7989/7989 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-coll_core-4024971 | coll_core | 2_1_floorplan | 0.3 | repair_Viol best 1485 last 1485 rows 896 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 4_1_cts | 6.1 | last meaningful line 0.7 h ago (10884/10884 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-4031555 | sle_ctl | 2_1_floorplan | 0.2 | repair_Viol best 2599 last 2599 rows 751 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4774/4774 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv4242de79-3812382 | sle_st_a_v2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5760/5760 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | 5_2_route | 13.6 | drt_violations best 136857 last 136857 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | 5_2_route | 13.4 | drt_violations best 155414 last 155414 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 5_2_route | 13.5 | drt_violations best 150654 last 150654 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-4008698 | slw_sc_v1 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (404/404 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5371/5371 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | 5_2_route | 13.5 | drt_violations best 15 last 15 rows 5 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | 6_report | 13.4 | last meaningful line 0.0 h ago (73/73 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-3807127 | slw_su_l1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (2544/2544 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | eco-abs-332782 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | eco-abs-355056 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_145005_2036075-i3-424023 | eco_20261124_145005_2036075-i3 | 5_2_route | 2.0 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i3t-4028039 | eco_20261124_175441_992552-i3t | 5_1_grt | 0.3 | last meaningful line 0.2 h ago (295/1315 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-fin-2609460 | fin | 6_1_fill | 0.0 | last meaningful line 0.0 h ago (9/9 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | so_343482_ff_51512 | so_343482_ff_51512 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | so_343482_tt_51512 | so_343482_tt_51512 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_2_route | 14.6 | last meaningful line 0.5 h ago (268/269 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 5_2_route | 14.6 | drt_violations best 146067 last 146067 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 5_2_route | 14.6 | last meaningful line 0.5 h ago (277/278 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 5_2_route | 14.6 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 5_2_route | 14.6 | drt_violations best 127432 last 127432 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | 5_2_route | 14.6 | drt_violations best 31424 last 31424 rows 2 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 14.6 | last meaningful line 0.5 h ago (266/267 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 5_2_route | 14.6 | drt_violations best 152943 last 152943 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 5_2_route | 14.6 | last meaningful line 0.4 h ago (282/283 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 5_2_route | 14.6 | drt_violations best 138449 last 138449 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 5_2_route | 14.6 | drt_violations best 141263 last 141263 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc8 | otc-120424-12773 | 120424 | signoff | 4.4 | last meaningful line 4.3 h ago (3/3 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc8 | otc-3257752-22204 | 3257752 | signoff | 0.2 | last meaningful line 0.2 h ago (3/3 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | otc-3678186-167 | 3678186 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3-32256 | eco_20261123_164145_1995767-i3 | 5_2_route | 2.8 | last meaningful line 0.2 h ago (289/290 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_025941_3548303-i1t-1829547 | eco_20261125_025941_3548303-i1t | 5_2_route | 3.7 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 11.5 |  | NO-DATA: no log found |  |
| epyc8 | so_1310884_ff_11169 | so_1310884_ff_11169 | signoff | 0.8 |  | NO-DATA: empty log |  |
| epyc8 | so_1310884_tt_11169 | so_1310884_tt_11169 | signoff | 0.8 |  | NO-DATA: empty log |  |
| epyc8 | so_1766798_ff_96500 | so_1766798_ff_96500 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc8 | so_1766798_tt_96500 | so_1766798_tt_96500 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc9 | ap-ageom-kw-col-h10-r0-p4--t1--pvcc166a6d-grt-3610025 | col-h10-r0-p4--t1--pvcc166a6d-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pv07945c1e-55623 | col_h10_r0_p4__t1 | 4_2_tapbal_grt | 0.5 | last meaningful line 0.0 h ago (62/68 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (64/64 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-3387092 | col_h10_r1__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3559 last 3559 rows 751 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3378330 | col_h9_r0_p1__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3875/3875 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-3647546 | col_h9_r0_p1__t1 | reg_fanout | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-3684533 | col_h9_r0_p2__t1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3716359 | col_h9_r0_p2__t1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-4079818 | col_h9_r0_p2__t1 | tt_setup_repair | 1.9 | repair_Viol best 26 last 26 rows 4 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b-3679007 | col_h9_r0_p3__t1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (59/59 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv8d734760-3617215 | col_h9_r0_p3__t1 | 2_1_floorplan | 0.0 | last meaningful line -0.0 h ago (58/58 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-3757021 | col_h9_r0_p3__t1 | 1_synth | 0.0 | last meaningful line 0.0 h ago (58/58 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-296584 | col_h9_r0_p3__t1 | lec | 2.6 | LEC last write 0.2 h ago | YOUNG: evidence 2.6 h < 6 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3720064 | col_h9_r0_p3__t1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (298/298 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-3710863 | col_h9_r0_p5__t1 | 1_synth | 0.0 | last meaningful line 0.0 h ago (9/9 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 9911.61 last 9911.61 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-3707756 | col_h9_r2__t1 | 4_1_cts | 0.0 | last meaningful line -0.0 h ago (3390/3390 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-3381669 | col_h9_r2__t1 | lec | 0.1 | LEC last write 0.0 h ago | YOUNG: evidence 0.1 h < 6 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-3631804 | col_h9_r2__t1 | 2_1_floorplan | 0.0 | repair_Viol best 2770 last 2770 rows 101 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | lec | 1.0 | LEC last write 0.1 h ago | YOUNG: evidence 1.0 h < 6 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t5-284167 | dsdv_slice_c1x_C__t5 | 3_4_place_resized | 2.6 | last meaningful line 0.1 h ago (404/404 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-4170435 | dsdv_slice_lepw_mu_C__t1 | 3_1_place_gp_skip_io | 1.9 | overflow best 0.8429 last 0.8539 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t24__cl2456157b-3731067 | ot_s81sl_leaf__t24 | 1_synth | 0.0 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t24__cl81374cd8-3637985 | ot_s81sl_leaf__t24 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t36-3727117 | ot_s81sl_leaf__t36 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (51/51 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3-3771398 | ot_s81sl_leaf__t40 | 1_synth | 0.0 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-12029 | ot_s81sl_leaf__t53 | lec | 0.5 | LEC last write 0.0 h ago | YOUNG: evidence 0.5 h < 6 h |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_2_route | 11.5 | drt_violations best 474459 last 474459 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-667540 | sle_hc1 | 6_report | 11.6 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t21-3663770 | slice_station__t21 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (1054/1054 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 11.7 | drt_violations best 274895 last 274895 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1102342 | kv3_hg_v1p3__r838481cd7 | pregrt_ff_hold | 4.6 | repair_TNS best 208493 last 208493 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| intel1 | dpkit-kv3_hgi_v6-102352 | kv3_hgi_v6 | 5_1_grt | 5.1 | last meaningful line 1.8 h ago (297/1306 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 5_2_route | 17.7 | last meaningful line 0.5 h ago (280/281 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 5_2_route | 13.4 | last meaningful line 0.3 h ago (271/272 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | pregrt_ff_hold | 5.5 | last meaningful line -0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | postcts_gate_TT | 9.7 | last meaningful line 0.0 h ago (1038/1038 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 5_2_route | 11.4 | drt_violations best 144494 last 144494 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_1_grt | 7.2 | last meaningful line 0.3 h ago (139/139 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3325358 | slw_fw_v1 | 5_1_grt | 7.2 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | tt_setup_measure_grt | 8.2 | last meaningful line -0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | postcts_gate_FF | 9.5 | last meaningful line 0.1 h ago (697/697 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 5_2_route | 13.4 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | 6_report | 17.6 | last meaningful line -0.0 h ago (45/45 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 5_2_route | 13.4 | drt_violations best 125787 last 125787 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-3090069 | slw_su_l0 | 5_2_route | 7.3 | drt_violations best 128742 last 128742 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 11.5 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 11.5 |  | NO-DATA: no log found |  |
| intel1 | otc-1948440-31269 | 1948440 | flow | 0.3 | last meaningful line 0.2 h ago (214/214 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-2098914-19313 | 2098914 | flow | 0.2 | last meaningful line 0.0 h ago (1559/1559 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-3190981-22207 | 3190981 | grt | 2.1 | last meaningful line 1.8 h ago (33/34 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | otc-4000256-29997 | 4000256 | eq11 | 3.5 | last meaningful line 0.0 h ago (792554/792554 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | otc-4001240-3461 | 4001240 | eq11 | 3.5 | last meaningful line 0.0 h ago (792554/792554 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i2-2930338 | eco_20261123_191853_2879776-i2 | 5_2_route | 5.6 | last meaningful line 0.3 h ago (290/291 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | so_1436874_ff_48011 | so_1436874_ff_48011 | signoff | 0.5 |  | NO-DATA: empty log |  |
| intel1 | so_1436874_tt_48011 | so_1436874_tt_48011 | signoff | 0.5 |  | NO-DATA: empty log |  |
| intel2 | dpkit-kv3_hgi_v2__cle0015330-3208477 | kv3_hgi_v2 | 5_1_grt | 1.5 | last meaningful line 0.7 h ago (288/1298 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-867671 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5442 last 5442 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-kv3_pc_v1__cl4ea58a5c__r877307f5d-3039255 | kv3_pc_v1 | 3_5_place_dp | 2.6 | last meaningful line 1.0 h ago (32/32 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8e7d31598-634629 | kv3_pc_v1 | 2_1_floorplan | 0.1 | repair_Viol best 8517 last 8517 rows 32 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-native59-1418182 | native59 | 3_5_place_dp | 1.9 | last meaningful line 0.1 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-4092661 | sle_sc_v1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.7621 last 0.7621 rows 27 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-3497131 | sle_sc_v1 | 3_3_place_gp | 0.4 | overflow best 0.2438 last 0.2438 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-sle_sc_v3-3238013 | sle_sc_v3 | 3_3_place_gp | 0.4 | overflow best 0.215 last 0.2156 rows 43 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-sle_su_l1__clc6d66f5b-3392952 | sle_su_l1 | 3_5_place_dp | 0.4 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 13.1 | drt_violations best 367946 last 367946 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 5_2_route | 13.3 | drt_violations best 406352 last 406352 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3248329 | slw_sc_v1 | 3_3_place_gp | 0.4 | overflow best 0.2317 last 0.2317 rows 24 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-2390236 | slw_st_b_v1 | postcts_gate_FF | 6.1 | last meaningful line 0.1 h ago (1109/1109 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | otc-560426-5193 | 560426 | signoff | 2.1 | last meaningful line 2.0 h ago (3/3 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | 5_2_route | 10.7 | drt_violations best 1820 last 2152 rows 22 | before-window best 8716, window best 1820 | PROGRESS: drt_violations improved 79.1 % in window |  |
| epyc10 | dpkit-kv3_hg_v1p2-1802854 | kv3_hg_v1p2 | pregrt_ff_hold | 4.9 | repair_Violations best 1340 last 1340 rows 125 | before-window best 52598, window best 1340 | PROGRESS: repair_Violations improved 97.5 % in window |  |
| epyc10 | prd-eco_20261125_055922_2792445-i1-2623359 | eco_20261125_055922_2792445-i1 | 5_1_grt | 0.7 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 25.7 | drt_violations best 14980 last 63558 rows 18 | before-window best 15812, window best 14980 | PROGRESS: drt_violations improved 5.3 % in window |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | 5_2_route | 13.2 | drt_violations best 0 last 0 rows 9 | PROGRESS: drt_violations reached 0 |  |
| epyc11 | prd-eco_20261124_190641_1260390-i1-3176761 | eco_20261124_190641_1260390-i1 | 5_2_route | 6.1 | drt_violations best 0 last 0 rows 4 | PROGRESS: drt_violations reached 0 |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 18.0 | drt_violations best 8379 last 8379 rows 13 | before-window best 123388, window best 8379 | PROGRESS: drt_violations improved 93.2 % in window |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-360401 | sle_st_b_v2 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 45.1 | drt_violations best 10129 last 21070 rows 19 | before-window best 10129, window best 21070 | PROGRESS: drt_violations: falling inside the active iteration (21070 -> 16343) |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 23.1 | drt_violations best 2937 last 2937 rows 15 | before-window best 9763, window best 2937 | PROGRESS: drt_violations improved 69.9 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 19.3 | drt_violations best 14082 last 14082 rows 7 | before-window best 504597, window best 14082 | PROGRESS: drt_violations improved 97.2 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 17.9 | drt_violations best 122131 last 122131 rows 2 | before-window best 510309, window best 122131 | PROGRESS: drt_violations improved 76.1 % in window |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 13.3 | drt_violations best 136685 last 136685 rows 2 | before-window best 412199, window best 136685 | PROGRESS: drt_violations improved 66.8 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 17.7 | drt_violations best 78434 last 78434 rows 3 | before-window best 457993, window best 78434 | PROGRESS: drt_violations improved 82.9 % in window |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 23.3 | drt_violations best 65547 last 65547 rows 10 | before-window best 68064, window best 65547 | PROGRESS: drt_violations improved 3.7 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 19.4 | drt_violations best 53197 last 53197 rows 8 | before-window best 123176, window best 53197 | PROGRESS: drt_violations improved 56.8 % in window |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 5_2_route | 14.6 | drt_violations best 23313 last 23313 rows 2 | before-window best 162445, window best 23313 | PROGRESS: drt_violations improved 85.6 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 14.6 | drt_violations best 122835 last 122835 rows 2 | before-window best 478667, window best 122835 | PROGRESS: drt_violations improved 74.3 % in window |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | 5_2_route | 14.7 | drt_violations best 0 last 0 rows 8 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 14.6 | drt_violations best 450083 last 450083 rows 1 | before-window best 450083, window best 450083 | PROGRESS: drt_violations: active iteration at 344145 < best completed total 450083 (in-ite |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 14.5 | drt_violations best 97102 last 97102 rows 3 | before-window best 379431, window best 97102 | PROGRESS: drt_violations improved 74.4 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 14.6 | drt_violations best 11145 last 11145 rows 13 | before-window best 26414, window best 11145 | PROGRESS: drt_violations improved 57.8 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-3394850 | col_h9_r2__t1 | 4_1_cts | 0.1 | repair_Violations best 0 last 0 rows 28 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 11.3 | drt_violations best 1406 last 1406 rows 24 | before-window best 84487, window best 1406 | PROGRESS: drt_violations improved 98.3 % in window |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 9.6 | drt_violations best 1964 last 1964 rows 8 | before-window best 187976, window best 1964 | PROGRESS: drt_violations improved 99.0 % in window |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 17.7 | drt_violations best 398476 last 398476 rows 1 | before-window best 398476, window best 398476 | PROGRESS: drt_violations: active iteration at 231612 < best completed total 398476 (in-ite |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | pregrt_ff_hold | 7.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-slw_su_l0__cl1e5219ea-4177722 | slw_su_l0 | 5_2_route | 9.5 | drt_violations best 6 last 6 rows 16 | before-window best 133698, window best 6 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel2 | dpkit-coll_ftm-1842242 | coll_ftm | 5_1_grt | 0.7 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel2 | dpkit-slice_station__t12-195391 | slice_station__t12 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
