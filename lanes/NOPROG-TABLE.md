# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 03:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'UNSIGNABLE': 1, 'GRT-LABEL': 6, 'YOUNG': 147, 'NO-DATA': 29, 'KEEP': 3, 'EXCLUDED': 1, 'PROGRESS': 32}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pv_v3-4187490 | kv3_pv_v3 | pregrt_ff_hold | 7.7 | repair_TNS best 117231 last 117231 rows 1 | before-window best 117231, window best 117231 | NO-PROGRESS: repair_TNS best 117231 vs 117231 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc8 | otc-120424-12773 | 120424 | signoff | 9.4 | last meaningful line 9.3 h ago (3/3 lines) | NO-PROGRESS: no new non-iteration log line for 9.3 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b-3679007 | col_h9_r0_p3__t1 | 5_1_grt | 5.0 | grt rounds 8 overflow 15:71 -> 20:44 -> 25:34 -> 30:4 -> 35:2 -> 40:3 | UNSIGNABLE: GRT overflow flat: overflow 2 at iteration 35 -> 3 at iteration 40: flat for 5 i | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_hg_v1p3__r81da466fe-1840159 | kv3_hg_v1p3__r81da466fe | 5_1_grt | 9.9 | grt rounds 2 overflow 5:40256 -> 10:36108 | GRT-LABEL: DESIGN-FAIL: overflow 36108 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v12-1535838 | kv3_pv_v12 | 5_1_grt | 8.5 | grt rounds 2 overflow 5:92646 -> 10:58944 | GRT-LABEL: DESIGN-FAIL: overflow 58944 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | 5_1_grt | 14.2 | grt rounds 2 overflow 5:94600 -> 10:59159 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc11 | dpkit-kv3_pv_v4-1052719 | kv3_pv_v4 | 5_1_grt | 2.4 | grt rounds 2 overflow 5:93111 -> 10:84388 | GRT-LABEL: DESIGN-FAIL: overflow 84388 at round 10 > 1000 |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-3490222 | cbn_q01 | 5_1_grt | 2.2 | grt rounds 2 overflow 5:81921 -> 10:75607 | GRT-LABEL: DESIGN-FAIL: overflow 75607 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi_v6-102352 | kv3_hgi_v6 | 5_1_grt | 10.3 | grt rounds 2 overflow 5:53849 -> 10:29026 | GRT-LABEL: DESIGN-FAIL: overflow 29026 at round 10 > 1000 |  |
| epyc10 | dpkit-hd_lep0N_w-3160116 | hd_lep0N_w | 5_1_grt | 1.5 | last meaningful line 0.0 h ago (1849/1860 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p5-970860 | kv3_hg_v1p5 | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (7309/7309 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | pregrt_ff_hold | 10.3 | repair_TNS best 89874.3 last 89874.3 rows 1 | YOUNG: evidence 2.2 h < 2.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-961899 | kv3_pc_v1 | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (6689/6689 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r877307f5d-1492582 | kv3_pc_v1 | 4_1_cts | 2.0 | last meaningful line 0.2 h ago (6597/6597 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8c9cba7ae-3297443 | kv3_pc_v1 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (6570/6570 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-19761 | kv3_pc_v1 | 4_1_cts | 2.3 | last meaningful line 0.1 h ago (6615/6615 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-native59-3384403 | native59 | 5_1_grt | 9.2 | last meaningful line 0.3 h ago (1870/1876 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-phy_serdes-3657780 | phy_serdes | 5_1_grt | 1.3 | last meaningful line 0.8 h ago (2233/3238 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_2_route | 16.9 | drt_violations best 378938 last 378938 rows 1 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 5_2_route | 17.0 | drt_violations best 227744 last 227744 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | 5_2_route | 15.6 | last meaningful line 0.1 h ago (277/278 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3681869 | slw_st_b_v2 | 5_2_route | 11.2 | drt_violations best 18594 last 18594 rows 2 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc10 | otc-1191841-12698 | 1191841 | signoff | 0.6 | last meaningful line 0.5 h ago (3/3 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | otc-1471300-23748 | 1471300 | signoff | 0.5 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | otc-1762308-21603 | 1762308 | signoff | 0.4 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_073109_4058437-i1t-725979 | eco_20261125_073109_4058437-i1t | 5_2_route | 4.2 | drt_violations best 9324 last 9324 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_112234_1159095-i1-1820297 | eco_20261125_112234_1159095-i1 | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (144/144 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | prd-fin-2623359 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v2e-1156839 | kv3_pv_v2e | lec | 2.3 | LEC last write 0.1 h ago | YOUNG: evidence 2.3 h < 6 h |  |
| epyc11 | dpkit-kv3_pv_v3ne-1144152 | kv3_pv_v3ne | lec | 2.3 | LEC last write 0.1 h ago | YOUNG: evidence 2.3 h < 6 h |  |
| epyc11 | dpkit-kv3_pv_v4e-1100418 | kv3_pv_v4e | lec | 2.3 | LEC last write 0.1 h ago | YOUNG: evidence 2.3 h < 6 h |  |
| epyc11 | dpkit-kv3_pv_v4ne-1191938 | kv3_pv_v4ne | lec | 2.3 | LEC last write 0.1 h ago | YOUNG: evidence 2.3 h < 6 h |  |
| epyc11 | dpkit-kv3_pv_v5-1052229 | kv3_pv_v5 | lec | 2.4 | LEC last write 0.1 h ago | YOUNG: evidence 2.4 h < 6 h |  |
| epyc11 | dpkit-kv3_pv_v5e-1092206 | kv3_pv_v5e | lec | 2.3 | LEC last write 0.1 h ago | YOUNG: evidence 2.3 h < 6 h |  |
| epyc11 | dpkit-kv3_pv_v6e-864517 | kv3_pv_v6e | lec | 2.5 | LEC last write 0.1 h ago | YOUNG: evidence 2.5 h < 6 h |  |
| epyc11 | dpkit-kv3_pv_v7-1078343 | kv3_pv_v7 | lec | 2.3 | LEC last write 0.1 h ago | YOUNG: evidence 2.3 h < 6 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 5_2_route | 13.8 | drt_violations best 16862 last 16862 rows 3 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 5_2_route | 13.5 | drt_violations best 134998 last 134998 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | 5_2_route | 8.5 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl92142dac-2960548 | slw_su_c | tt_setup_repair | 4.8 | repair_Viol best 19 last 19 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | otc-141162-25188 | 141162 | lec | 0.8 | LEC last write 0.8 h ago | YOUNG: evidence 0.8 h < 6 h |  |
| epyc11 | otc-381902-2867 | 381902 | - | 2.7 |  | NO-DATA: no log found |  |
| epyc11 | prd-eco_20261124_154417_1016084-i2-2211039 | eco_20261124_154417_1016084-i2 | 5_1_grt | 1.8 | last meaningful line 0.8 h ago (243/1425 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i2t-2255468 | eco_20261124_190641_1260390-i2t | 5_1_grt | 1.8 | last meaningful line 0.7 h ago (238/1704 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i2t-96653 | eco_20261124_200101_1087713-i2t | 5_1_grt | 0.8 | last meaningful line 0.2 h ago (244/481 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_080242_341091-i1-2097287 | eco_20261125_080242_341091-i1 | 5_2_route | 3.6 | last meaningful line 0.3 h ago (276/277 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_080337_31727-i1-2053095 | eco_20261125_080337_31727-i1 | 5_2_route | 3.6 | drt_violations best 39 last 39 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_082938_54055-i1-3146788 | eco_20261125_082938_54055-i1 | 5_2_route | 3.2 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_092112_274675-i1-1256057 | eco_20261125_092112_274675-i1 | 5_2_route | 2.3 | last meaningful line 0.3 h ago (133/133 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_092728_2532622-i1-1376598 | eco_20261125_092728_2532622-i1 | 5_2_route | 2.2 | last meaningful line 0.1 h ago (264/265 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc11 | so_1252901_ff_18611 | so_1252901_ff_18611 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (1034/1034 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | so_1252901_tt_18611 | so_1252901_tt_18611 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (1034/1034 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | so_1697458_ff_33860 | so_1697458_ff_33860 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (35/35 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | so_1697458_tt_33860 | so_1697458_tt_33860 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (35/35 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | so_485644_ff_59961 | so_485644_ff_59961 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc11 | so_485644_tt_59961 | so_485644_tt_59961 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc12 | c3w7-grt-FF-3838652 | c3w7-grt-FF | combo_FF | 0.0 | last meaningful line 0.0 h ago (1105/1105 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | c3w7-grt-TT-3838652 | c3w7-grt-TT | combo_TT | 0.0 | last meaningful line 0.0 h ago (1094/1094 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-4185661 | col_h10_r0_p4__t1 | 2_1_floorplan | 0.1 | repair_Viol best 6050 last 6050 rows 831 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-dsdv_slice_lepe_mu_LP__t2-4185515 | dsdv_slice_lepe_mu_LP__t2 | 2_2_floorplan_macro | 0.1 | last meaningful line -0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-hd_lep0N-2152952 | hd_lep0N | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (8457/8457 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc12 | dpkit-kv3_hgi_v7-2529031 | kv3_hgi_v7 | 4_1_cts | 1.0 | last meaningful line 0.2 h ago (6491/6491 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl7f648944__r8422a4b86-1394259 | kv3_pc_v1 | 3_5_place_dp | 1.9 | last meaningful line 0.8 h ago (32/32 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pv_v12-2339543 | kv3_pv_v12 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (8758/8758 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pv_v1n-1216451 | kv3_pv_v1n | 3_4_place_resized | 2.0 | last meaningful line 0.1 h ago (488/488 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | dpkit-sle_ctl__cla4f6f12f-2847382 | sle_ctl | 3_1_place_gp_skip_io | 0.8 | overflow best 0.3853 last 0.3853 rows 32 | YOUNG: stage 0.3 h < 1 h |  |
| epyc12 | dpkit-sle_st_a_v1__cl67389ecd-95324 | sle_st_a_v1 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-slw_st_a_v2__clf4365a62-2414803 | slw_st_a_v2 | 5_1_grt | 1.1 | repair_Remaining best 19009 last 19009 rows 120 | YOUNG: stage 0.4 h < 1 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc12 | leccsp-prof | leccsp-prof | - | 0.2 |  | NO-DATA: no log found |  |
| epyc12 | otc-3501458-13012 | 3501458 | drc_merged | 0.4 | last meaningful line 0.1 h ago (193/193 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc12 | otc-4081706-8020 | 4081706 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc12 | qcdrt-fw-A | qcdrt-fw-A | - | 0.8 |  | NO-DATA: no log found |  |
| epyc12 | qcdrt-fw-B | qcdrt-fw-B | - | 0.8 |  | NO-DATA: no log found |  |
| epyc12 | qcdrt-fw-C | qcdrt-fw-C | - | 0.8 |  | NO-DATA: no log found |  |
| epyc12 | qcdrt-sc-A | qcdrt-sc-A | - | 0.8 |  | NO-DATA: no log found |  |
| epyc12 | qcdrt-sc-B | qcdrt-sc-B | - | 0.8 |  | NO-DATA: no log found |  |
| epyc12 | qcdrt-sc-C | qcdrt-sc-C | - | 0.8 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | postcts_gate_FF | 2.0 | last meaningful line 0.1 h ago (545/545 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-3286653 | sle_st_a_v2 | 5_2_route | 2.0 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1216203 | sle_st_b_v1 | 5_2_route | 7.8 | drt_violations best 138255 last 138255 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-360401 | sle_st_b_v2 | 5_2_route | 6.8 | drt_violations best 100895 last 100895 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2601551 | slw_st_a_v1 | 5_2_route | 2.3 | last meaningful line 0.1 h ago (258/259 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | otc-146801-7119 | 146801 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc2 | otc-2861341-10638 | 2861341 | clk_freeze_post | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-3847527-9693 | 3847527 | signoff | 1.7 | last meaningful line 1.6 h ago (3/3 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | so_2698565_ff_45520 | so_2698565_ff_45520 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | so_2698565_tt_45520 | so_2698565_tt_45520 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbf_q00_s2-3518685 | cbf_q00_s2 | 5_1_grt | 5.4 | last meaningful line 0.5 h ago (256/1262 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-coll_core-3493022 | coll_core | 4_1_cts | 2.2 | last meaningful line 0.0 h ago (11480/11480 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_serdes-2729222 | hd_serdes | 3_1_place_gp_skip_io | 0.6 | overflow best 0.4225 last 0.4225 rows 32 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 5_1_grt | 11.1 | last meaningful line 0.0 h ago (282/295 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | 5_1_grt | 5.4 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3817081 | sle_st_a_v2 | 5_2_route | 3.7 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__clc6d66f5b-2521917 | sle_su_l1 | postcts_gate_TT | 2.7 | last meaningful line -0.0 h ago (1034/1034 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_1_grt | 2.6 | last meaningful line 0.2 h ago (143/143 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 5.3 | last meaningful line 0.2 h ago (135/135 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-3807127 | slw_su_l1 | 5_2_route | 5.3 | drt_violations best 279991 last 279991 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i3-2994934 | eco_20261124_175441_992552-i3 | 5_2_route | 2.4 | drt_violations best 5536 last 5536 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i2t-2177999 | eco_20261124_192157_3493836-i2t | 5_2_route | 4.4 | drt_violations best 499 last 499 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i2-3644612 | eco_20261124_235631_1843084-i2 | 5_2_route | 2.2 | drt_violations best 5315 last 5315 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_073745_2194631-i1-2944509 | eco_20261125_073745_2194631-i1 | 5_2_route | 4.1 | drt_violations best 41 last 41 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_073945_2252980-i1-3230821 | eco_20261125_073945_2252980-i1 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (139/139 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_081621_2016666-i1-599553 | eco_20261125_081621_2016666-i1 | 5_2_route | 3.4 | drt_violations best 23 last 23 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_094206_1890550-i1-4068402 | eco_20261125_094206_1890550-i1 | 5_2_route | 2.0 | last meaningful line 0.2 h ago (133/133 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_103149_2129512-i1-1443376 | eco_20261125_103149_2129512-i1 | 5_1_grt | 1.2 | last meaningful line 0.3 h ago (289/318 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_110124_1979736-i1-2551803 | eco_20261125_110124_1979736-i1 | 5_1_grt | 0.7 | last meaningful line 0.2 h ago (139/139 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-625563 | col_h10_r0_p1__t1 | 3_3_place_gp | 0.9 | overflow best 0.1977 last 0.1977 rows 39 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2067862 | col_h10_r0_p4__t1 | 3_3_place_gp | 0.5 | overflow best 0.4902 last 0.5086 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-2484689 | col_h9_r1__t1 | 3_5_place_dp | 0.4 | last meaningful line 0.0 h ago (119/119 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2655952 | col_h9_r1__t1 | 3_4_place_resized | 0.3 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p5-3496343 | kv3_hg_v1p5 | pregrt_ff_hold | 1.3 | repair_TNS best 809467 last 809467 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc8 | dpkit-kv3_pv_v3n-3977907 | kv3_pv_v3n | 3_5_place_dp | 1.2 | last meaningful line 0.1 h ago (57/57 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-3678186-167 | 3678186 | - | 5.0 |  | NO-DATA: no log found |  |
| epyc8 | prd-count-p1_bc-3306668 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_091937_4000900-i1-378808 | eco_20261125_091937_4000900-i1 | 5_2_route | 2.4 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_104318_3955073-i1t-474220 | eco_20261125_104318_3955073-i1t | 5_2_route | 1.0 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_110931_3969969-i1-1922478 | eco_20261125_110931_3969969-i1 | 5_1_grt | 0.6 | last meaningful line 0.1 h ago (289/300 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_114101_3990791-i1-3640861 | eco_20261125_114101_3990791-i1 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-fin-1572735 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (65/65 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | relec-r2-U1_hc3_pv39aac7a1 | relec-r2-U1_hc3_pv39aac7a1 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc8 | so_1448940_ff_59178 | so_1448940_ff_59178 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc8 | so_1448940_tt_59178 | so_1448940_tt_59178 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc8 | so_1744126_ff_3823 | so_1744126_ff_3823 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc8 | so_1744126_tt_3823 | so_1744126_tt_3823 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc8 | so_2538522_ff_61132 | so_2538522_ff_61132 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc8 | so_2538522_tt_61132 | so_2538522_tt_61132 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc8 | so_2850906_ff_7710 | so_2850906_ff_7710 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc8 | so_2850906_tt_7710 | so_2850906_tt_7710 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc8 | so_2955095_ff_78989 | so_2955095_ff_78989 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (33/33 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | so_2955095_tt_78989 | so_2955095_tt_78989 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (33/33 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | so_2990013_ff_70537 | so_2990013_ff_70537 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc8 | so_2990013_tt_70537 | so_2990013_tt_70537 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc8 | so_680819_ff_17461 | so_680819_ff_17461 | generate_abstract | 0.9 | last meaningful line 0.8 h ago (33/33 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | so_680819_tt_17461 | so_680819_tt_17461 | generate_abstract | 0.9 | last meaningful line 0.8 h ago (33/33 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | pregrt_ff_hold | 5.0 | repair_TNS best 127105 last 127105 rows 1 | YOUNG: evidence 1.6 h < 2.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pv07945c1e-55623 | col_h10_r0_p4__t1 | 5_1_grt | 5.5 | repair_Remaining best 136050 last 136050 rows 88 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | lec | 5.0 | LEC last write 0.1 h ago | YOUNG: evidence 5.0 h < 6 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-296584 | col_h9_r0_p3__t1 | 5_1_grt | 7.6 | repair_Remaining best 219143 last 219143 rows 65 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3698869 | col_h9_r0_p4__t1 | pregrt_ff_hold | 2.9 | repair_TNS best 47200.4 last 47200.4 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-3032686 | col_h9_r0_p4__t1 | 4_2_tapbal_grt | 0.8 | last meaningful line 0.1 h ago (62/68 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | lec | 2.2 | LEC last write 0.3 h ago | YOUNG: evidence 2.2 h < 6 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-4053150 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.2 | last meaningful line 1.5 h ago (61/88 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pvf1445dce-2628247 | col_h9_r2__t1 | lec | 1.6 | LEC last write 0.0 h ago | YOUNG: evidence 1.6 h < 6 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv31e47bd5-4047516 | col_h9_r2__t1 | lec | 2.2 | LEC last write 0.2 h ago | YOUNG: evidence 2.2 h < 6 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 6.9 | drt_violations best 162909 last 162909 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-3394850 | col_h9_r2__t1 | 5_2_route | 5.1 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-3707756 | col_h9_r2__t1 | 5_2_route | 5.0 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | 5_2_route | 6.0 | drt_violations best 163283 last 163283 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t10-3695203 | dsdv_slice_c1x_C__t10 | 3_5_place_dp | 4.0 | last meaningful line 0.1 h ago (38/38 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-578982 | dsdv_slice_c1x_C__t8 | 3_4_place_resized | 3.9 | last meaningful line 0.0 h ago (455/455 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-3691225 | dsdv_slice_c1x_C__t9 | 3_4_place_resized | 4.0 | repair_Remaining best 1251 last 1251 rows 378 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_kv512_C__t1-4058196 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 2.2 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t25__cl55642d17-3495886 | ot_s81sl_leaf__t25 | tt_setup_repair_grt | 2.9 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-3479533 | slice_station__t37 | 5_1_grt | 2.9 | last meaningful line 0.1 h ago (732/757 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t42__clcf44e680-3472830 | slice_station__t42 | 5_2_route | 2.9 | last meaningful line 0.1 h ago (261/262 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t43-3486441 | slice_station__t43 | postcts_gate_TT | 2.9 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-2620358 | slice_station__t52 | pregrt_ff_hold | 1.7 | repair_TNS best 1095.94 last 1095.94 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | prd-eco_20261125_090100_666856-i1-787277 | eco_20261125_090100_666856-i1 | 5_2_route | 2.7 | drt_violations best 9 last 9 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-559858 | col_h10_r0_p4__t1 | 3_3_place_gp | 0.6 | last meaningful line 0.0 h ago (244/244 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1177242 | kv3_hg_v1p3__r838481cd7 | 5_1_grt | 4.1 | last meaningful line 0.2 h ago (169/169 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_sys_c-4063347 | kv3_sys_c | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (5273/5273 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-serdes__t15__cla3d02796-2608833 | serdes__t15 | 3_3_place_gp | 1.8 | overflow best 0.5157 last 0.5157 rows 84 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | postcts_gate_FF | 10.7 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 5_2_route | 15.0 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | generate_abstract | 16.7 | last meaningful line 0.1 h ago (24/24 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t27-4040446 | slice_station__t27 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (3244/3244 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t30__cl1653104c-2603170 | slice_station__t30 | postcts_gate_FF | 0.9 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | postcts_gate_TT | 12.4 | last meaningful line 0.1 h ago (1793/1793 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 5_2_route | 13.5 | drt_violations best 174940 last 174940 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 5_2_route | 14.7 | drt_violations best 104717 last 104717 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | postcts_gate_TT | 13.2 | last meaningful line 0.1 h ago (1103/1103 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | otc-3504566-18256 | 3504566 | flow | 0.8 | last meaningful line 0.0 h ago (2854/2854 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | prd-count-p1_tc-1838007 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i3t-2681077 | eco_20261123_191853_2879776-i3t | 5_1_grt | 0.9 | last meaningful line 0.2 h ago (142/142 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1t-3347319 | eco_20261125_002226_1452841-i1t | 5_2_route | 3.3 | last meaningful line 0.5 h ago (268/269 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | prd-eco_20261125_020407_3088231-i1-2998029 | eco_20261125_020407_3088231-i1 | 5_2_route | 1.6 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | so_3133510_ff_2944 | so_3133510_ff_2944 | signoff | 0.8 |  | NO-DATA: empty log |  |
| intel1 | so_3133510_tt_2944 | so_3133510_tt_2944 | signoff | 0.8 |  | NO-DATA: empty log |  |
| intel2 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-705307 | kv3_pc_v1 | 3_5_place_dp | 2.5 | last meaningful line 1.0 h ago (32/32 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8e7d31598-707215 | kv3_pc_v1 | 3_5_place_dp | 2.5 | last meaningful line 1.0 h ago (32/32 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-2390236 | slw_st_b_v1 | 5_2_route | 11.1 | drt_violations best 56 last 56 rows 9 | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel2 | otc-594090-20209 | 594090 | eq13_out | 2.5 | last meaningful line 0.0 h ago (706248/706248 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-1955823 | kv3_hgi | 5_1_grt | 1.9 |  | KEEP: kv3_hgi_1124155644	KV-OWN-RSTREACH	combined HEADLEG2+HGI-LEAF ship form; noprog  |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-436421 | kv3_hgi_v2 | 5_1_grt | 2.2 |  | KEEP: kv3_hgi_v2__cl2862d491_1124155702	KV-OWN-RSTREACH	combined hgi_v2 ship form (COO |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pvb2cd22a7-3043152 | col_h9_r2__t1 | pregrt_ff_hold | 0.8 |  | KEEP: col_h9_r2__t1__clb8d86cd5__pvb2cd22a7	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-eco_qcgu_1125-i1-3514577 | eco_qcgu_1125-i1 | 5_2_route | 3.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_2_route | 18.0 | drt_violations best 152884 last 152884 rows 2 | before-window best 416066, window best 152884 | PROGRESS: drt_violations improved 63.3 % in window |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | 5_2_route | 15.2 | drt_violations best 18 last 18 rows 12 | before-window best 149411, window best 18 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 16.9 | drt_violations best 9570 last 9570 rows 7 | before-window best 272423, window best 9570 | PROGRESS: drt_violations improved 96.5 % in window |  |
| epyc10 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2082061 | slw_st_a_v1 | 5_1_grt | 1.9 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 14.1 | repair_Violations best 29472 last 29483 rows 47 | before-window best 295079, window best 29472 | PROGRESS: repair_Violations improved 90.0 % in window |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 18.2 | drt_violations best 5558 last 5558 rows 10 | before-window best 329677, window best 5558 | PROGRESS: drt_violations improved 98.3 % in window |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 30.7 | drt_violations best 14980 last 63558 rows 18 | before-window best 14980, window best 63558 | PROGRESS: drt_violations: falling inside the active iteration (63558 -> 36856) |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 23.0 | drt_violations best 6215 last 33693 rows 18 | before-window best 9570, window best 6215 | PROGRESS: drt_violations improved 35.1 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 43.4 | drt_violations best 5300 last 5300 rows 23 | before-window best 7726, window best 5300 | PROGRESS: drt_violations improved 31.4 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 28.1 | drt_violations best 2761 last 13398 rows 18 | before-window best 2937, window best 2761 | PROGRESS: drt_violations improved 6.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 24.3 | drt_violations best 6306 last 6306 rows 13 | before-window best 17236, window best 6306 | PROGRESS: drt_violations improved 63.4 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 22.9 | drt_violations best 18111 last 18111 rows 10 | before-window best 122131, window best 18111 | PROGRESS: drt_violations improved 85.2 % in window |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 18.3 | drt_violations best 68573 last 68573 rows 7 | before-window best 136685, window best 68573 | PROGRESS: drt_violations improved 49.8 % in window |  |
| epyc7 | dpkit-sle_sc_v3-2521918 | sle_sc_v3 | 5_1_grt | 2.7 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-577851 | slw_sc_v1 | 5_1_grt | 3.4 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 22.7 | drt_violations best 8850 last 8850 rows 11 | before-window best 106839, window best 8850 | PROGRESS: drt_violations improved 91.7 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-534954 | slw_su_l1 | tt_setup_repair_grt | 4.9 | repair_Violations best 0 last 0 rows 46 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_2_route | 19.6 | drt_violations best 83164 last 83164 rows 2 | before-window best 320246, window best 83164 | PROGRESS: drt_violations improved 74.0 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 19.6 | drt_violations best 27006 last 27006 rows 7 | before-window best 478667, window best 27006 | PROGRESS: drt_violations improved 94.4 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 19.6 | drt_violations best 266434 last 266434 rows 1 | before-window best 266434, window best 266434 | PROGRESS: drt_violations: active iteration at 72283 < best completed total 266434 (in-iter |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 19.6 | drt_violations best 25364 last 25364 rows 4 | before-window best 450083, window best 25364 | PROGRESS: drt_violations improved 94.4 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 19.6 | drt_violations best 8519 last 40739 rows 18 | before-window best 12823, window best 8519 | PROGRESS: drt_violations improved 33.6 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve0486b40-3725060 | col_h9_r2__t1 | 5_1_grt | 2.9 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_2_route | 16.5 | drt_violations best 47387 last 47387 rows 8 | before-window best 474459, window best 47387 | PROGRESS: drt_violations improved 90.0 % in window |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 16.7 | drt_violations best 6 last 6 rows 37 | before-window best 274895, window best 6 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 5_2_route | 23.0 | drt_violations best 76432 last 76432 rows 2 | before-window best 317907, window best 76432 | PROGRESS: drt_violations improved 76.0 % in window |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 5_2_route | 18.6 | drt_violations best 15907 last 15907 rows 3 | before-window best 163425, window best 15907 | PROGRESS: drt_violations improved 90.3 % in window |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 14.9 | drt_violations best 1 last 1 rows 33 | before-window best 5498, window best 1 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 22.9 | drt_violations best 16353 last 16353 rows 4 | before-window best 398476, window best 16353 | PROGRESS: drt_violations improved 95.9 % in window |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 5_2_route | 18.6 | drt_violations best 19262 last 19262 rows 2 | before-window best 138053, window best 19262 | PROGRESS: drt_violations improved 86.0 % in window |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 18.1 | drt_violations best 3272 last 3272 rows 12 | before-window best 367946, window best 3272 | PROGRESS: drt_violations improved 99.1 % in window |  |
