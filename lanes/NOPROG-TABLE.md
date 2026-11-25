# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 00:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 5, 'UNSIGNABLE': 9, 'GRT-LABEL': 4, 'YOUNG': 130, 'NO-DATA': 21, 'PROGRESS': 38}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 15.8 | last meaningful line 14.5 h ago (48/142 lines) | NO-PROGRESS: no new non-iteration log line for 14.5 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc10 | dpkit-kv3_hg_v1__r889141819-1619104 | kv3_hg_v1__r889141819 | 5_1_grt | 7.0 | grt rounds 2 overflow 5:43060 -> 10:43108 | UNSIGNABLE: GRT overflow flat: overflow 43060 at iteration 5 -> 43108 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_hg_v1__r8dffc461a-1676050 | kv3_hg_v1__r8dffc461a | 5_1_grt | 7.0 | grt rounds 2 overflow 5:42503 -> 10:42107 | UNSIGNABLE: GRT overflow flat: overflow 42503 at iteration 5 -> 42107 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 5_1_grt | 16.1 | grt rounds 2 overflow 5:42234 -> 10:42876 | UNSIGNABLE: GRT overflow flat: overflow 42234 at iteration 5 -> 42876 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-2844240 | kv3_pc | 5_1_grt | 5.2 | grt rounds 2 overflow 5:7078 -> 10:4367 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -436.54 ps (< -300, gate TT >= -42); job age 5. | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_pc__cl254f2e73__r8b421e514-2986767 | kv3_pc | tt_setup_repair_grt | 5.1 | repair_Viol best 2102 last 2102 rows 6 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -915.28 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r882954158-3053902 | kv3_pc | 5_1_grt | 5.1 | grt rounds 2 overflow 5:6934 -> 10:4576 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -521.67 ps (< -300, gate TT >= -42); job age 5. | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 18.9 | last meaningful line 15.3 h ago (48/212 lines) | NO-PROGRESS: no new non-iteration log line for 15.3 h | REPORT-ONLY: lane-own kit (HEAD-EAST-REPLAN decide |
| epyc11 | dpkit-kv3_hg_v1p5-2367108 | kv3_hg_v1p5 | 5_1_grt | 13.2 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 11.1 | repair_TNS best 145595 last 145595 rows 1 | before-window best 145595, window best 145595 | NO-PROGRESS: repair_TNS best 145595 vs 145595 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc11 | otc-3389445-25127 | 3389445 | signoff | 7.8 | last meaningful line 7.8 h ago (3/3 lines) | NO-PROGRESS: no new non-iteration log line for 7.8 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 5_1_grt | 17.8 | grt rounds 2 overflow 5:41695 -> 10:42884 | UNSIGNABLE: GRT overflow flat: overflow 41695 at iteration 5 -> 42884 at iteration 10: flat  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-cbn_q01__cldd6ea846-1559108 | cbn_q01 | 5_1_grt | 8.0 | grt rounds 2 overflow 5:81921 -> 10:75607 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -347.34 ps (< -300, gate TT >= -42); job age 8. | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | otc-120424-12773 | 120424 | signoff | 6.4 | last meaningful line 6.3 h ago (3/3 lines) | NO-PROGRESS: no new non-iteration log line for 6.3 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | 5_1_grt | 11.2 | grt rounds 2 overflow 5:94600 -> 10:59159 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v8-2737550 | kv3_hgi_v8 | 5_1_grt | 6.3 | grt rounds 2 overflow 5:54135 -> 10:40850 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | 5_1_grt | 13.0 | grt rounds 2 overflow 5:34556 -> 10:3532 | GRT-LABEL: DESIGN-FAIL: overflow 3532 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi_v6-102352 | kv3_hgi_v6 | 5_1_grt | 7.1 | grt rounds 2 overflow 5:53849 -> 10:29026 | GRT-LABEL: DESIGN-FAIL: overflow 29026 at round 10 > 1000 |  |
| epyc10 | dpkit-glue-1294589 | glue | postcts_gate_FF | 7.2 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p2-1802854 | kv3_hg_v1p2 | 5_1_grt | 6.9 | last meaningful line 1.3 h ago (305/1313 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p3__r81da466fe-1840159 | kv3_hg_v1p3__r81da466fe | 5_1_grt | 6.9 | last meaningful line 1.8 h ago (287/1296 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc__cl5a95b461__r85c02c25c-3151820 | kv3_pc | postcts_gate_FF | 5.1 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v12-1535838 | kv3_pv_v12 | 5_1_grt | 5.5 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v3-4187490 | kv3_pv_v3 | pregrt_ff_hold | 4.7 | repair_TNS best 169360 last 169360 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_2_route | 15.0 | last meaningful line 0.8 h ago (280/281 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-2392801 | sle_hc2 | 5_2_route | 11.8 | drt_violations best 104126 last 104126 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | 5_2_route | 12.2 | drt_violations best 149411 last 149411 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1160769 | sle_st_b_v2 | 5_2_route | 12.8 | drt_violations best 12439 last 12439 rows 3 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 13.9 | drt_violations best 272423 last 272423 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_2_route | 13.9 | last meaningful line 0.8 h ago (270/271 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 5_2_route | 14.0 | last meaningful line 0.3 h ago (133/133 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | postcts_gate_TT | 12.6 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2504205 | slw_st_b_v1 | 5_2_route | 11.7 | drt_violations best 19575 last 19575 rows 2 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3681869 | slw_st_b_v2 | 5_2_route | 8.2 | last meaningful line 0.3 h ago (263/264 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4041620 | slw_st_b_v2 | 5_2_route | 10.7 | drt_violations best 130780 last 130780 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_055922_2792445-i1-2623359 | eco_20261125_055922_2792445-i1 | 5_2_route | 2.7 | last meaningful line 0.3 h ago (271/272 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_073109_4058437-i1t-725979 | eco_20261125_073109_4058437-i1t | 5_2_route | 1.2 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | smp-1114852 | smp | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | smp-1160117 | smp | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | smp-1210639 | smp | - | 0.0 |  | NO-DATA: no log found |  |
| epyc11 | ap-ageom-kw-cbn-q00--cl622f65d2-grt-3266226 | cbn-q00--cl622f65d2-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 15.2 | drt_violations best 329677 last 329677 rows 1 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 5_2_route | 10.8 | last meaningful line 0.3 h ago (279/280 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 5_2_route | 11.8 | drt_violations best 25003 last 25003 rows 2 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 5_2_route | 10.5 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2533872 | slw_hc3 | 6_report | 8.9 | last meaningful line 0.1 h ago (69/69 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | 5_1_grt | 5.5 | last meaningful line 0.1 h ago (1121/1135 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl92142dac-2960548 | slw_su_c | 4_1_cts | 1.8 | last meaningful line 0.1 h ago (8435/8435 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc11 | eco-abs-3419890 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.0 h ago (1024/1024 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | eco-abs-864576 | eco-abs | generate_abstract | 1.1 | last meaningful line 0.4 h ago (904/904 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 14.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-3195182-24200 | 3195182 | asbuilt.yosys | 0.2 | last meaningful line -0.0 h ago (135201/135201 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | otc-3196606-31436 | 3196606 | asbuilt.yosys | 0.2 | last meaningful line -0.0 h ago (135446/135446 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | otc-3296346-10242 | 3296346 | asbuilt.yosys | 0.1 | last meaningful line -0.0 h ago (135470/135470 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | otc-3324407-6321 | 3324407 | asbuilt.yosys | 0.1 | last meaningful line 0.0 h ago (135445/135445 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | otc-701258-11435 | 701258 | lec | 1.1 | LEC last write 1.1 h ago | YOUNG: evidence 1.1 h < 6 h |  |
| epyc11 | otc-701492-14947 | 701492 | lec | 1.1 | LEC last write 1.1 h ago | YOUNG: evidence 1.1 h < 6 h |  |
| epyc11 | prd-eco_20261124_204246_1187010-i1-249436 | eco_20261124_204246_1187010-i1 | 5_2_route | 6.6 | drt_violations best 1 last 1 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_054540_316017-i1-897106 | eco_20261125_054540_316017-i1 | 5_2_route | 2.9 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_080242_341091-i1-2097287 | eco_20261125_080242_341091-i1 | 5_1_grt | 0.6 | last meaningful line 0.0 h ago (175/175 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_080337_31727-i1-2053095 | eco_20261125_080337_31727-i1 | 5_1_grt | 0.6 | last meaningful line 0.3 h ago (139/139 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_082938_54055-i1-3146788 | eco_20261125_082938_54055-i1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | smp-3213555 | smp | - | 0.2 |  | NO-DATA: no log found |  |
| epyc11 | smp-3478320 | smp | - | 0.0 |  | NO-DATA: no log found |  |
| epyc11 | smp-3580143 | smp | - | 0.0 |  | NO-DATA: no log found |  |
| epyc11 | so_1785500_ff_25434 | so_1785500_ff_25434 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | so_1785500_tt_25434 | so_1785500_tt_25434 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | so_2564279_ff_84503 | so_2564279_ff_84503 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc11 | so_2564279_tt_84503 | so_2564279_tt_84503 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1216203 | sle_st_b_v1 | postcts_gate_TT | 4.8 | last meaningful line -0.0 h ago (60696/60696 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-360401 | sle_st_b_v2 | 5_1_grt | 3.8 | last meaningful line 0.0 h ago (2165/2180 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3668964 | sle_st_b_v2 | 5_2_route | 8.5 | drt_violations best 20907 last 20907 rows 2 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | kqc-sta_region_nb0_h15_n9_s11_bt3_synth0-453315 | sta_region_nb0_h15_n9_s11_bt3_synth0 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (190/190 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | kqc-sta_region_nb0_h17_n7_s8_bt3_synth0-454974 | sta_region_nb0_h17_n7_s8_bt3_synth0 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (204/204 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | kqc-sta_region_nb0_h18_n7_s8_bt3_synth0-454093 | sta_region_nb0_h18_n7_s8_bt3_synth0 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (189/189 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | otc-2040585-24869 | 2040585 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc2 | otc-2459734-26514 | 2459734 | signoff | 4.3 | last meaningful line 4.3 h ago (3/3 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | otc-2882933-23086 | 2882933 | signoff | 2.4 | last meaningful line 2.3 h ago (3/3 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | otc-3544630-5805 | 3544630 | signoff | 5.9 | last meaningful line 5.8 h ago (3/3 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc2 | otc-785042-5629 | 785042 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261124_204708_4151707-i1-226978 | eco_20261124_204708_4151707-i1 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (297/331 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_215436_3656110-i1-2033351 | eco_20261124_215436_3656110-i1 | 5_2_route | 2.8 | drt_violations best 22 last 22 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_230804_491597-i1-1072574 | eco_20261124_230804_491597-i1 | 5_2_route | 1.6 | drt_violations best 28 last 28 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 13.4 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbf_q00_s2-3518685 | cbf_q00_s2 | tt_setup_repair | 2.4 | repair_Violations best 226 last 292 rows 43 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | pregrt_ff_hold | 8.1 | repair_TNS best 260322 last 260322 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-4031555 | sle_ctl | 3_5_place_dp | 2.2 | last meaningful line 0.2 h ago (128/128 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | 4_1_cts | 2.4 | last meaningful line 0.1 h ago (5230/5230 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3817081 | sle_st_a_v2 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (6237/6237 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | generate_abstract | 15.6 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 5_2_route | 15.5 | drt_violations best 78 last 78 rows 6 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-577851 | slw_sc_v1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4437/4437 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_1_grt | 2.3 | last meaningful line 0.1 h ago (144/144 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-3807127 | slw_su_l1 | postcts_gate_TT | 2.3 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-534954 | slw_su_l1 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (1712/1716 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i3t-4028039 | eco_20261124_175441_992552-i3t | 5_2_route | 2.3 | drt_violations best 59 last 59 rows 4 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i2t-2177999 | eco_20261124_192157_3493836-i2t | 5_2_route | 1.4 | last meaningful line 0.1 h ago (260/261 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i2t-915490 | eco_20261124_235631_1843084-i2t | 5_2_route | 1.8 | drt_violations best 39345 last 39345 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_073745_2194631-i1-2944509 | eco_20261125_073745_2194631-i1 | 5_1_grt | 1.1 | last meaningful line 0.5 h ago (296/399 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_073945_2252980-i1t-3004488 | eco_20261125_073945_2252980-i1t | 5_2_route | 1.1 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_081621_2016666-i1-599553 | eco_20261125_081621_2016666-i1 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (144/144 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | so_112736_ff_12662 | so_112736_ff_12662 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (1034/1034 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | so_112736_tt_12662 | so_112736_tt_12662 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (1034/1034 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | so_791367_ff_33464 | so_791367_ff_33464 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (27/27 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | so_791367_tt_33464 | so_791367_tt_33464 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (27/27 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_2_route | 16.6 | drt_violations best 320246 last 320246 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 5_2_route | 16.6 | drt_violations best 129389 last 129389 rows 1 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 5_2_route | 16.6 | drt_violations best 131388 last 131388 rows 1 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 16.6 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 5_2_route | 16.6 | drt_violations best 146375 last 146375 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc8 | otc-3678186-167 | 3678186 | - | 2.0 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3-32256 | eco_20261123_164145_1995767-i3 | 5_2_route | 4.8 | drt_violations best 16767 last 16767 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_065854_3885412-i1-521874 | eco_20261125_065854_3885412-i1 | 5_2_route | 1.7 | last meaningful line 0.2 h ago (127/127 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_071225_3873455-i1-1532615 | eco_20261125_071225_3873455-i1 | 5_2_route | 1.5 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_082653_3900765-i1-1572735 | eco_20261125_082653_3900765-i1 | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | prd-fin-1829547 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 13.5 |  | NO-DATA: no log found |  |
| epyc8 | so_1547311_ff_10462 | so_1547311_ff_10462 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc8 | so_1547311_tt_10462 | so_1547311_tt_10462 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | 4_2_tapbal_grt | 2.0 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pv07945c1e-55623 | col_h10_r0_p4__t1 | lec | 2.5 | LEC last write 0.0 h ago | YOUNG: evidence 2.5 h < 6 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-4079818 | col_h9_r0_p2__t1 | 5_1_grt | 3.9 | last meaningful line 0.1 h ago (1379/1410 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-296584 | col_h9_r0_p3__t1 | lec | 4.6 | LEC last write 0.1 h ago | YOUNG: evidence 4.6 h < 6 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 150413 last 150413 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p6__t1__pv082a7609-1003900 | col_h9_r0_p6__t1 | 3_3_place_gp | 0.3 | overflow best 0.4646 last 0.4661 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 3.9 | last meaningful line 0.0 h ago (263/263 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-3394850 | col_h9_r2__t1 | pregrt_ff_hold | 2.1 | repair_TNS best 72521.9 last 72521.9 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-3707756 | col_h9_r2__t1 | lec | 2.0 | LEC last write 0.0 h ago | YOUNG: evidence 2.0 h < 6 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | 5_1_grt | 3.0 | last meaningful line 0.0 h ago (2499/2514 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t10-3695203 | dsdv_slice_c1x_C__t10 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-578982 | dsdv_slice_c1x_C__t8 | sdc_lint | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-3691225 | dsdv_slice_c1x_C__t9 | sdc_lint | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t1-107375 | ot_s81sl_leaf__t1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.8267 last 0.8267 rows 21 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t36-3727117 | ot_s81sl_leaf__t36 | pregrt_ff_hold | 2.0 | repair_TNS best 713920 last 713920 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t54__cl706d9749-3650154 | ot_s81sl_leaf__t54 | 3_3_place_gp | 0.5 | overflow best 0.4129 last 0.4129 rows 30 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_2_route | 13.5 | drt_violations best 125492 last 125492 rows 3 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t21-3663770 | slice_station__t21 | 5_2_route | 2.0 | drt_violations best 10510 last 10510 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t31-266306 | slice_station__t31 | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 13.7 | drt_violations best 4850 last 4850 rows 8 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc9 | so_1866284_ff_63309 | so_1866284_ff_63309 | signoff | 1.3 |  | NO-DATA: empty log |  |
| epyc9 | so_1866284_tt_63309 | so_1866284_tt_63309 | signoff | 1.3 |  | NO-DATA: empty log |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1177242 | kv3_hg_v1p3__r838481cd7 | pregrt_ff_hold | 0.8 | repair_TNS best 208493 last 208493 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 5_2_route | 15.4 | drt_violations best 163425 last 163425 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 5_1_grt | 7.5 | repair_Remaining best 399922 last 399922 rows 71 | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | postcts_gate_FF | 11.7 | last meaningful line 0.1 h ago (1186/1186 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 5_2_route | 10.2 | last meaningful line 0.5 h ago (132/132 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 5_2_route | 11.5 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 5_2_route | 15.4 | drt_violations best 138053 last 138053 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 5_1_grt | 9.9 | last meaningful line 0.3 h ago (146/146 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl76fb247e-3090069 | slw_su_l0 | 5_2_route | 9.3 | drt_violations best 51 last 51 rows 7 | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | eco-abs-1867199 | eco-abs | generate_abstract | 0.6 | last meaningful line 0.3 h ago (870/870 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | otc-1307078-2494 | 1307078 | - | 13.5 |  | NO-DATA: no log found |  |
| intel1 | otc-1308800-28898 | 1308800 | - | 13.5 |  | NO-DATA: no log found |  |
| intel1 | otc-1948440-31269 | 1948440 | flow | 2.3 | last meaningful line 1.3 h ago (1897/1897 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | otc-2098914-19313 | 2098914 | flow | 2.2 | last meaningful line 0.0 h ago (3015/3015 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | otc-4000256-29997 | 4000256 | eq11 | 5.5 | last meaningful line -0.0 h ago (796109/796109 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | otc-4001240-3461 | 4001240 | eq11 | 5.5 | last meaningful line -0.0 h ago (796109/796109 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1t-3347319 | eco_20261125_002226_1452841-i1t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-2942460 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (214/215 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-4044677 | kv3_io_ft | 5_2_route | 1.2 | drt_violations best 5442 last 5442 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-kv3_pv_v1e-2379368 | kv3_pv_v1e | 3_3_place_gp | 0.4 | overflow best 0.6505 last 0.6505 rows 20 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-kv3_pv_v7-2379649 | kv3_pv_v7 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v7e-3092815 | kv3_pv_v7e | 2_1_floorplan | 0.2 | last meaningful line 0.1 h ago (484/484 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v8-2379151 | kv3_pv_v8 | 3_3_place_gp | 0.4 | overflow best 0.3086 last 0.3086 rows 33 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-kv3_pv_v8e-2355447 | kv3_pv_v8e | 3_3_place_gp | 0.4 | overflow best 0.431 last 0.431 rows 25 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-kv3_pve-3092926 | kv3_pve | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8467 last 0.8561 rows 8 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-1249478 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (221/222 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 15.1 | drt_violations best 96187 last 96187 rows 2 | YOUNG: evidence 6.0 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-2390236 | slw_st_b_v1 | 5_2_route | 8.1 | last meaningful line 0.1 h ago (279/280 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-1292775 | hd_spn | 5_2_route | 12.7 | drt_violations best 1820 last 1895 rows 25 | before-window best 2879, window best 1820 | PROGRESS: drt_violations improved 36.8 % in window |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | 4_1_cts | 7.3 | last meaningful line 0.2 h ago (11606/11606 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-native59-3384403 | native59 | pregrt_ff_hold | 6.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 27.7 | drt_violations best 14980 last 63558 rows 18 | before-window best 15279, window best 14980 | PROGRESS: drt_violations: falling inside the active iteration (63558 -> 53045) |  |
| epyc11 | prd-eco_20261124_154417_1016084-i2t-1425156 | eco_20261124_154417_1016084-i2t | 5_2_route | 5.6 | drt_violations best 0 last 0 rows 4 | PROGRESS: drt_violations reached 0 |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 20.0 | drt_violations best 6824 last 6824 rows 15 | before-window best 21818, window best 6824 | PROGRESS: drt_violations improved 68.7 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 40.4 | drt_violations best 6858 last 6858 rows 21 | before-window best 7726, window best 6858 | PROGRESS: drt_violations improved 11.2 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 25.1 | drt_violations best 2818 last 2818 rows 16 | before-window best 5099, window best 2818 | PROGRESS: drt_violations improved 44.7 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 21.3 | drt_violations best 11325 last 11325 rows 10 | before-window best 116309, window best 11325 | PROGRESS: drt_violations improved 90.3 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 19.9 | drt_violations best 23801 last 23801 rows 5 | before-window best 510309, window best 23801 | PROGRESS: drt_violations improved 95.3 % in window |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 15.3 | drt_violations best 75027 last 75027 rows 4 | before-window best 412199, window best 75027 | PROGRESS: drt_violations improved 81.8 % in window |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | 5_2_route | 15.4 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 19.7 | drt_violations best 15427 last 15427 rows 6 | before-window best 457993, window best 15427 | PROGRESS: drt_violations improved 96.6 % in window |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 25.3 | drt_violations best 65547 last 65547 rows 10 | before-window best 66691, window best 65547 | PROGRESS: drt_violations: active iteration at 63447 < best completed total 65547 (in-itera |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 21.4 | drt_violations best 52514 last 52514 rows 9 | before-window best 59441, window best 52514 | PROGRESS: drt_violations improved 11.7 % in window |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 5_2_route | 16.6 | drt_violations best 88 last 88 rows 8 | before-window best 162445, window best 88 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 5_2_route | 16.6 | drt_violations best 11324 last 11324 rows 3 | before-window best 146067, window best 11324 | PROGRESS: drt_violations improved 92.2 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 16.6 | drt_violations best 93397 last 93397 rows 3 | before-window best 478667, window best 93397 | PROGRESS: drt_violations improved 80.5 % in window |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 5_2_route | 16.6 | drt_violations best 17958 last 17958 rows 2 | before-window best 127432, window best 17958 | PROGRESS: drt_violations improved 85.9 % in window |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 5_2_route | 16.6 | drt_violations best 19013 last 19013 rows 2 | before-window best 152943, window best 19013 | PROGRESS: drt_violations improved 87.6 % in window |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 5_2_route | 16.6 | drt_violations best 138449 last 138449 rows 1 | before-window best 138449, window best 138449 | PROGRESS: drt_violations: active iteration at 33027 < best completed total 138449 (in-iter |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 16.6 | drt_violations best 450083 last 450083 rows 1 | before-window best 450083, window best 450083 | PROGRESS: drt_violations: active iteration at 169515 < best completed total 450083 (in-ite |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 16.5 | drt_violations best 53734 last 53734 rows 5 | before-window best 379431, window best 53734 | PROGRESS: drt_violations improved 85.8 % in window |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 5_2_route | 16.6 | drt_violations best 20955 last 20955 rows 2 | before-window best 141263, window best 20955 | PROGRESS: drt_violations improved 85.2 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 16.6 | drt_violations best 9525 last 9525 rows 15 | before-window best 22483, window best 9525 | PROGRESS: drt_violations improved 57.6 % in window |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 4_2_tapbal_grt | 2.0 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3378330 | col_h9_r0_p1__t1 | 4_2_tapbal_grt | 2.1 | repair_Violations best 0 last 0 rows 9 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b-3679007 | col_h9_r0_p3__t1 | 4_2_tapbal_grt | 2.0 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 13.3 | drt_violations best 1371 last 1838 rows 28 | before-window best 1673, window best 1371 | PROGRESS: drt_violations improved 18.1 % in window |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 5_2_route | 19.7 | drt_violations best 317907 last 317907 rows 1 | before-window best 317907, window best 317907 | PROGRESS: drt_violations: active iteration at 250872 < best completed total 317907 (in-ite |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 5_2_route | 13.4 | drt_violations best 144494 last 144494 rows 1 | before-window best 144494, window best 144494 | PROGRESS: drt_violations: active iteration at 46549 < best completed total 144494 (in-iter |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 11.6 | drt_violations best 39 last 39 rows 14 | before-window best 187976, window best 39 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_1_grt | 9.2 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3325358 | slw_fw_v1 | 5_1_grt | 9.2 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 19.7 | drt_violations best 104690 last 104690 rows 2 | before-window best 398476, window best 104690 | PROGRESS: drt_violations improved 73.7 % in window |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 5_2_route | 15.4 | drt_violations best 17734 last 17734 rows 2 | before-window best 125787, window best 17734 | PROGRESS: drt_violations improved 85.9 % in window |  |
| intel1 | prd-eco_20261124_235251_4176465-i1-1838007 | eco_20261124_235251_4176465-i1 | 5_1_grt | 0.6 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 5_2_route | 15.3 | drt_violations best 13563 last 13563 rows 5 | before-window best 406352, window best 13563 | PROGRESS: drt_violations improved 96.7 % in window |  |
