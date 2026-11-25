# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 23:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'UNSIGNABLE': 3, 'GRT-LABEL': 11, 'YOUNG': 138, 'NO-DATA': 23, 'PROGRESS': 32}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 14.3 | last meaningful line 13.0 h ago (48/141 lines) | NO-PROGRESS: no new non-iteration log line for 13.0 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 5_1_grt | 14.6 | grt rounds 2 overflow 5:42234 -> 10:42876 | UNSIGNABLE: GRT overflow flat: overflow 42234 at iteration 5 -> 42876 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 17.4 | last meaningful line 13.8 h ago (48/209 lines) | NO-PROGRESS: no new non-iteration log line for 13.8 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | 5_1_grt | 11.7 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 9.6 | repair_TNS best 121785 last 121785 rows 1 | before-window best 121785, window best 121785 | NO-PROGRESS: repair_TNS best 121785 vs 121785 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc11 | otc-3389445-25127 | 3389445 | signoff | 6.3 | last meaningful line 6.3 h ago (3/3 lines) | NO-PROGRESS: no new non-iteration log line for 6.3 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 5_1_grt | 16.3 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_hg_v1__r889141819-1619104 | kv3_hg_v1__r889141819 | 5_1_grt | 5.5 | grt rounds 1 overflow 5:43060 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_hg_v1__r88f4bfb40-1671162 | kv3_hg_v1__r88f4bfb40 | 5_1_grt | 5.5 | grt rounds 1 overflow 5:42362 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-2844240 | kv3_pc | 5_1_grt | 3.7 | grt rounds 2 overflow 5:7078 -> 10:4367 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r8b421e514-2986767 | kv3_pc | 5_1_grt | 3.6 | grt rounds 2 overflow 5:7207 -> 10:4296 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r85c02c25c-3151820 | kv3_pc | 5_1_grt | 3.6 | grt rounds 2 overflow 5:7303 -> 10:4851 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r882954158-3053902 | kv3_pc | 5_1_grt | 3.6 | grt rounds 2 overflow 5:6934 -> 10:4576 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | 5_1_grt | 9.7 | grt rounds 2 overflow 5:94600 -> 10:59159 | GRT-LABEL: DESIGN-FAIL: overflow 59159 at round 10 > 1000 |  |
| epyc2 | dpkit-kv3_hgi_v8-2737550 | kv3_hgi_v8 | 5_1_grt | 4.8 | grt rounds 2 overflow 5:54135 -> 10:40850 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-1559108 | cbn_q01 | 5_1_grt | 6.5 | grt rounds 2 overflow 5:81921 -> 10:75607 | GRT-LABEL: DESIGN-FAIL: overflow 75607 at round 10 > 1000 |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | 5_1_grt | 11.5 | grt rounds 2 overflow 5:34556 -> 10:3532 | GRT-LABEL: DESIGN-FAIL: overflow 3532 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v2__cle0015330-3208477 | kv3_hgi_v2 | 5_1_grt | 2.0 | grt rounds 2 overflow 5:8261 -> 10:2784 | GRT-LABEL: DESIGN-FAIL: overflow 2784 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_hg_v1__r8dffc461a-1676050 | kv3_hg_v1__r8dffc461a | 5_1_grt | 5.5 | last meaningful line 0.8 h ago (287/1294 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p2-1802854 | kv3_hg_v1p2 | 5_1_grt | 5.4 | last meaningful line 0.1 h ago (170/170 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p3__r81da466fe-1840159 | kv3_hg_v1p3__r81da466fe | 5_1_grt | 5.4 | last meaningful line 0.3 h ago (287/1291 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | 4_1_cts | 5.8 | last meaningful line 0.5 h ago (11296/11296 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-3561929 | kv3_pc_v1 | 3_5_place_dp | 3.4 | last meaningful line 1.5 h ago (32/32 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r84d0332e1-3581607 | kv3_pc_v1 | 3_5_place_dp | 3.4 | last meaningful line 1.3 h ago (32/32 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r884969661-3601103 | kv3_pc_v1 | 3_5_place_dp | 3.4 | last meaningful line 1.3 h ago (32/32 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8afe1e027-3618066 | kv3_pc_v1 | 3_5_place_dp | 3.4 | last meaningful line 1.5 h ago (32/32 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8c9cba7ae-3633962 | kv3_pc_v1 | 3_5_place_dp | 3.4 | last meaningful line 0.0 h ago (115/115 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-3669242 | kv3_pc_v1 | 3_5_place_dp | 3.4 | last meaningful line 0.1 h ago (115/115 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-1535838 | kv3_pv_v12 | pregrt_ff_hold | 4.0 | repair_TNS best 42717.5 last 42717.5 rows 1 | YOUNG: evidence 1.7 h < 2.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-4187490 | kv3_pv_v3 | 4_1_cts | 3.2 | last meaningful line 0.1 h ago (12091/12091 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_2_route | 13.5 | last meaningful line 0.5 h ago (274/275 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | 5_2_route | 10.3 | last meaningful line 0.3 h ago (274/275 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | 5_2_route | 10.7 | last meaningful line 0.3 h ago (283/284 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | 5_2_route | 11.3 | drt_violations best 127354 last 127354 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 12.4 | last meaningful line 0.5 h ago (276/277 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_2_route | 12.4 | last meaningful line 0.2 h ago (263/263 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | postcts_gate_FF | 12.5 | last meaningful line 0.2 h ago (1656/1656 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | 5_2_route | 10.2 | drt_violations best 138401 last 138401 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3681869 | slw_st_b_v2 | postcts_gate_FF | 6.7 | last meaningful line 0.1 h ago (473/473 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | 5_2_route | 9.2 | last meaningful line 0.3 h ago (275/276 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_055922_2792445-i1-2623359 | eco_20261125_055922_2792445-i1 | 5_1_grt | 1.2 | last meaningful line 0.3 h ago (296/395 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | qc-hc3-lec-r8-nearest | qc-hc3-lec-r8-nearest | - | 8.2 |  | NO-DATA: no log found |  |
| epyc10 | qccollslec_h4 | qccollslec_h4 | - | 3.2 |  | NO-DATA: no log found |  |
| epyc10 | so_1909583_ff_45461 | so_1909583_ff_45461 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc10 | so_1909583_tt_45461 | so_1909583_tt_45461 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 13.7 | drt_violations best 329677 last 329677 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 5_2_route | 9.3 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 5_2_route | 10.3 | drt_violations best 168194 last 168194 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | postcts_gate_FF | 9.0 | last meaningful line 0.1 h ago (839/839 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | 5_2_route | 13.6 | drt_violations best 13836 last 13836 rows 3 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | 6_report | 13.7 | last meaningful line 0.1 h ago (76/76 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2533872 | slw_hc3 | 5_2_route | 7.4 | drt_violations best 87718 last 87718 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | pregrt_ff_hold | 4.0 | repair_TNS best 6155.91 last 6155.91 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc11 | dpkit-slw_su_c__cl92142dac-2960548 | slw_su_c | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (7901/7901 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 12.7 |  | NO-DATA: no log found |  |
| epyc11 | otc-3935105-17300 | 3935105 | clk_freeze_post | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | otc-3979213-13043 | 3979213 | ot_bind_native_3c9bd54727c5a0b7ad763ae5 | 0.0 | last meaningful line -0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_154417_1016084-i2t-1425156 | eco_20261124_154417_1016084-i2t | 5_2_route | 4.1 | drt_violations best 917 last 917 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i1-3660942 | eco_20261124_200101_1087713-i1 | 5_2_route | 6.0 | drt_violations best 37 last 37 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_204246_1187010-i1-249436 | eco_20261124_204246_1187010-i1 | 5_2_route | 5.1 | drt_violations best 1 last 1 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_054540_316017-i1-897106 | eco_20261125_054540_316017-i1 | 5_2_route | 1.4 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | prd-fin-3176761 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | so_3098882_ff_50641 | so_3098882_ff_50641 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc11 | so_3098882_tt_50641 | so_3098882_tt_50641 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc11 | so_3632485_ff_17702 | so_3632485_ff_17702 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc11 | so_3632485_tt_17702 | so_3632485_tt_17702 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1216203 | sle_st_b_v1 | 5_1_grt | 3.3 | last meaningful line 0.0 h ago (266/268 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-360401 | sle_st_b_v2 | pregrt_ff_hold | 2.3 | repair_TNS best 164972 last 164972 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3668964 | sle_st_b_v2 | 5_2_route | 7.0 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | otc-2459734-26514 | 2459734 | signoff | 2.8 | last meaningful line 2.8 h ago (3/3 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | otc-2882933-23086 | 2882933 | signoff | 0.9 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | otc-3544630-5805 | 3544630 | signoff | 4.4 | last meaningful line 4.3 h ago (3/3 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | otc-785042-5629 | 785042 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261124_204708_4151707-i1t-4056582 | eco_20261124_204708_4151707-i1t | 5_2_route | 2.4 | drt_violations best 10225 last 10225 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_215436_3656110-i1-2033351 | eco_20261124_215436_3656110-i1 | 5_2_route | 1.3 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_230804_491597-i1-1072574 | eco_20261124_230804_491597-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-fin-2284188 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 11.9 |  | NO-DATA: no log found |  |
| epyc2 | so_888669_ff_74236 | so_888669_ff_74236 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (33/33 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | so_888669_tt_74236 | so_888669_tt_74236 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (33/33 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00_s2-3518685 | cbf_q00_s2 | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (8079/8079 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-coll_core-4024971 | coll_core | 3_3_place_gp | 0.8 | overflow best 0.1995 last 0.1995 rows 40 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-coll_ftn-485651 | coll_ftn | 5_2_route | 0.4 | last meaningful line 0.0 h ago (221/221 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-4031555 | sle_ctl | 3_1_place_gp_skip_io | 0.7 | overflow best 0.8043 last 0.8168 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | 4_1_cts | 0.9 | last meaningful line 0.2 h ago (5086/5086 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv4242de79-3812382 | sle_st_a_v2 | 5_1_grt | 0.8 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | 5_2_route | 14.1 | drt_violations best 20228 last 20228 rows 2 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | 5_2_route | 13.9 | drt_violations best 155414 last 155414 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 5_2_route | 14.0 | drt_violations best 26702 last 26702 rows 2 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-4008698 | slw_sc_v1 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (385/385 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (5489/5489 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | 6_report | 14.0 | last meaningful line 0.1 h ago (67/67 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-3807127 | slw_su_l1 | 5_1_grt | 0.8 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-534954 | slw_su_l1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (2632/2632 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | eco-abs-1654772 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.1 h ago (1024/1024 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_145005_2036075-i3-424023 | eco_20261124_145005_2036075-i3 | 5_2_route | 2.5 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i3t-4028039 | eco_20261124_175441_992552-i3t | 5_2_route | 0.8 | last meaningful line 0.1 h ago (254/255 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i2t-915490 | eco_20261124_235631_1843084-i2t | 5_1_grt | 0.3 | last meaningful line 0.2 h ago (295/1389 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | so_1168156_ff_43800 | so_1168156_ff_43800 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc7 | so_1168156_tt_43800 | so_1168156_tt_43800 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc7 | so_343482_ff_51512 | so_343482_ff_51512 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc7 | so_343482_tt_51512 | so_343482_tt_51512 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc7 | so_855332_ff_63949 | so_855332_ff_63949 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (27/27 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | so_855332_tt_63949 | so_855332_tt_63949 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (27/27 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_2_route | 15.1 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 5_2_route | 15.1 | drt_violations best 146067 last 146067 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 5_2_route | 15.1 | drt_violations best 129389 last 129389 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 5_2_route | 15.1 | drt_violations best 131388 last 131388 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 5_2_route | 15.1 | drt_violations best 127432 last 127432 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | 5_2_route | 15.1 | drt_violations best 23529 last 23529 rows 3 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 15.1 | last meaningful line 0.7 h ago (268/269 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 5_2_route | 15.1 | drt_violations best 152943 last 152943 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 5_2_route | 15.1 | drt_violations best 146375 last 146375 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 5_2_route | 15.1 | drt_violations best 138449 last 138449 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | generate_abstract | 15.2 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 5_2_route | 15.1 | drt_violations best 141263 last 141263 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc8 | otc-120424-12773 | 120424 | signoff | 4.9 | last meaningful line 4.8 h ago (3/3 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc8 | otc-3257752-22204 | 3257752 | signoff | 0.7 | last meaningful line 0.6 h ago (3/3 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | otc-3678186-167 | 3678186 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3-32256 | eco_20261123_164145_1995767-i3 | 5_2_route | 3.3 | last meaningful line 0.2 h ago (293/294 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_025941_3548303-i1t-1829547 | eco_20261125_025941_3548303-i1t | 5_2_route | 4.2 | drt_violations best 495 last 495 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_065854_3885412-i1-521874 | eco_20261125_065854_3885412-i1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 12.0 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3551/3551 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 4_2_tapbal_grt | 0.5 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3378330 | col_h9_r0_p1__t1 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (4308/4308 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-3647546 | col_h9_r0_p1__t1 | 3_3_place_gp | 0.5 | overflow best 0.4885 last 0.4885 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-3684533 | col_h9_r0_p2__t1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3859/3859 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3716359 | col_h9_r0_p2__t1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3716/3716 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b-3679007 | col_h9_r0_p3__t1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4062/4062 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv8d734760-3617215 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-3757021 | col_h9_r0_p3__t1 | lec | 0.5 | LEC last write 0.0 h ago | YOUNG: evidence 0.5 h < 6 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-296584 | col_h9_r0_p3__t1 | lec | 3.1 | LEC last write 0.0 h ago | YOUNG: evidence 3.1 h < 6 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3720064 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.7926 last 0.7926 rows 22 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3186/3186 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvee6f8140-3710863 | col_h9_r0_p5__t1 | 3_3_place_gp | 0.5 | overflow best 0.4645 last 0.4645 rows 20 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf71da13a-3999510 | col_h9_r0_p5__t1 | 3_2_place_iop | 0.5 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | lec | 2.4 | LEC last write 0.1 h ago | YOUNG: evidence 2.4 h < 6 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-3707756 | col_h9_r2__t1 | 4_2_tapbal_grt | 0.5 | last meaningful line 0.0 h ago (91/91 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | lec | 1.5 | LEC last write 0.2 h ago | YOUNG: evidence 1.5 h < 6 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t5-284167 | dsdv_slice_c1x_C__t5 | lec | 3.1 | LEC last write 0.1 h ago | YOUNG: evidence 3.1 h < 6 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-4170435 | dsdv_slice_lepw_mu_C__t1 | 3_3_place_gp | 2.4 | last meaningful line 0.1 h ago (43/43 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t36-3727117 | ot_s81sl_leaf__t36 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (6329/6329 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3-3771398 | ot_s81sl_leaf__t40 | 3_4_place_resized | 0.5 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_2_route | 12.0 | drt_violations best 162913 last 162913 rows 2 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-667540 | sle_hc1 | generate_abstract | 12.1 | last meaningful line 0.1 h ago (27/27 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 12.2 | drt_violations best 65686 last 65686 rows 2 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc9 | otc-115840-2964 | 115840 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | otc-3987944-19968 | 3987944 | gen_lint_yosys | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v6-102352 | kv3_hgi_v6 | 5_1_grt | 5.6 | last meaningful line 2.3 h ago (297/1307 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 5_2_route | 18.2 | drt_violations best 317907 last 317907 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 5_2_route | 13.9 | last meaningful line 0.3 h ago (275/276 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | pregrt_ff_hold | 6.0 | repair_TNS best 14144 last 14144 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | postcts_gate_TT | 10.2 | last meaningful line 0.2 h ago (1188/1188 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 5_2_route | 11.9 | drt_violations best 144494 last 144494 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_1_grt | 7.7 | last meaningful line 0.2 h ago (249/1258 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | postcts_gate_TT | 8.7 | last meaningful line -0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 5_2_route | 10.0 | last meaningful line -0.0 h ago (20/20 lines) | YOUNG: evidence -0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 5_2_route | 13.9 | last meaningful line 0.5 h ago (271/272 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | generate_abstract | 18.1 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 5_2_route | 13.9 | drt_violations best 125787 last 125787 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-3090069 | slw_su_l0 | 5_2_route | 7.8 | drt_violations best 22483 last 22483 rows 2 | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 12.0 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 12.0 |  | NO-DATA: no log found |  |
| intel1 | otc-1948440-31269 | 1948440 | flow | 0.8 | repair_Viol best 34015 last 34015 rows 8 | YOUNG: stage 0.8 h < 1 h |  |
| intel1 | otc-2098914-19313 | 2098914 | flow | 0.7 | last meaningful line 0.0 h ago (2847/2847 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | otc-4000256-29997 | 4000256 | eq11 | 4.0 | last meaningful line 0.0 h ago (793031/793031 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | otc-4001240-3461 | 4001240 | eq11 | 4.0 | last meaningful line 0.0 h ago (793026/793026 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | prd-count-p1_tc-2930338 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | so_1436874_ff_48011 | so_1436874_ff_48011 | signoff | 1.0 |  | NO-DATA: empty log |  |
| intel1 | so_1436874_tt_48011 | so_1436874_tt_48011 | signoff | 1.0 |  | NO-DATA: empty log |  |
| intel2 | dpkit-coll_ftm-1842242 | coll_ftm | 5_2_route | 1.2 | last meaningful line 0.1 h ago (230/231 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8e7d31598-634629 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.8556 last 0.9131 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-4092661 | sle_sc_v1 | 3_3_place_gp | 0.8 | overflow best 0.0997 last 0.0997 rows 53 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-195391 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (222/223 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 13.6 | drt_violations best 367946 last 367946 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-2390236 | slw_st_b_v1 | 5_2_route | 6.6 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | so_3170874_ff_29390 | so_3170874_ff_29390 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_3170874_tt_29390 | so_3170874_tt_29390 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | dpkit-glue-1294589 | glue | 5_1_grt | 5.7 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | 5_2_route | 11.2 | drt_violations best 1820 last 2009 rows 23 | before-window best 4058, window best 1820 | PROGRESS: drt_violations improved 55.2 % in window |  |
| epyc10 | dpkit-native59-3384403 | native59 | pregrt_ff_hold | 4.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | 5_1_grt | 11.1 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 26.2 | drt_violations best 14980 last 63558 rows 18 | before-window best 15812, window best 14980 | PROGRESS: drt_violations improved 5.3 % in window |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 18.5 | drt_violations best 7058 last 7058 rows 14 | before-window best 123388, window best 7058 | PROGRESS: drt_violations improved 94.3 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 38.9 | drt_violations best 7726 last 8463 rows 20 | before-window best 7726, window best 8463 | PROGRESS: drt_violations: falling inside the active iteration (8463 -> 7800) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 4_1_cts | 6.6 | last meaningful line 0.1 h ago (10908/10908 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 23.6 | drt_violations best 2937 last 2937 rows 15 | before-window best 8628, window best 2937 | PROGRESS: drt_violations improved 66.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 19.8 | drt_violations best 12303 last 12303 rows 9 | before-window best 504597, window best 12303 | PROGRESS: drt_violations improved 97.6 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 18.4 | drt_violations best 90589 last 90589 rows 3 | before-window best 510309, window best 90589 | PROGRESS: drt_violations improved 82.2 % in window |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 13.8 | drt_violations best 113083 last 113083 rows 3 | before-window best 412199, window best 113083 | PROGRESS: drt_violations improved 72.6 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 18.2 | drt_violations best 78434 last 78434 rows 3 | before-window best 457993, window best 78434 | PROGRESS: drt_violations improved 82.9 % in window |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 23.8 | drt_violations best 65547 last 65547 rows 10 | before-window best 67058, window best 65547 | PROGRESS: drt_violations improved 2.3 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 19.9 | drt_violations best 53197 last 53197 rows 8 | before-window best 102681, window best 53197 | PROGRESS: drt_violations improved 48.2 % in window |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 5_2_route | 15.1 | drt_violations best 23313 last 23313 rows 2 | before-window best 162445, window best 23313 | PROGRESS: drt_violations improved 85.6 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 15.1 | drt_violations best 122835 last 122835 rows 2 | before-window best 478667, window best 122835 | PROGRESS: drt_violations improved 74.3 % in window |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 15.1 | drt_violations best 450083 last 450083 rows 1 | before-window best 450083, window best 450083 | PROGRESS: drt_violations: active iteration at 287558 < best completed total 450083 (in-ite |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 15.0 | drt_violations best 97102 last 97102 rows 3 | before-window best 379431, window best 97102 | PROGRESS: drt_violations improved 74.4 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 15.1 | drt_violations best 10226 last 10226 rows 14 | before-window best 24952, window best 10226 | PROGRESS: drt_violations improved 59.0 % in window |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pv07945c1e-55623 | col_h10_r0_p4__t1 | 4_2_tapbal_grt | 1.0 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-4079818 | col_h9_r0_p2__t1 | 5_1_grt | 2.4 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-3394850 | col_h9_r2__t1 | 4_2_tapbal_grt | 0.6 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-3631804 | col_h9_r2__t1 | 3_5_place_dp | 0.5 | repair_Violations best 0 last 0 rows 26 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 11.8 | drt_violations best 1371 last 3385 rows 26 | before-window best 7501, window best 1371 | PROGRESS: drt_violations improved 81.7 % in window |  |
| epyc9 | dpkit-slice_station__t21-3663770 | slice_station__t21 | 5_1_grt | 0.5 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 10.1 | drt_violations best 323 last 323 rows 11 | before-window best 187976, window best 323 | PROGRESS: drt_violations improved 99.8 % in window |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3325358 | slw_fw_v1 | 5_1_grt | 7.7 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 18.2 | drt_violations best 398476 last 398476 rows 1 | before-window best 398476, window best 398476 | PROGRESS: drt_violations: active iteration at 185181 < best completed total 398476 (in-ite |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | pregrt_ff_hold | 8.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-slw_su_l0__cl1e5219ea-4177722 | slw_su_l0 | 5_2_route | 10.0 | drt_violations best 3 last 3 rows 26 | before-window best 133698, window best 3 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 5_2_route | 13.8 | drt_violations best 105657 last 105657 rows 2 | before-window best 406352, window best 105657 | PROGRESS: drt_violations improved 74.0 % in window |  |
