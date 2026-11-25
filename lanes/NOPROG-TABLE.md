# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 02:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'GRT-LABEL': 7, 'YOUNG': 141, 'NO-DATA': 31, 'KEEP': 2, 'EXCLUDED': 1, 'PROGRESS': 38}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pv_v3-4187490 | kv3_pv_v3 | pregrt_ff_hold | 6.7 | repair_TNS best 169360 last 169360 rows 1 | before-window best 169360, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | pregrt_ff_hold | 13.1 | repair_TNS best 145595 last 145595 rows 1 | before-window best 145595, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc8 | otc-120424-12773 | 120424 | signoff | 8.4 | last meaningful line 8.3 h ago (3/3 lines) | NO-PROGRESS: no new non-iteration log line for 8.3 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | pregrt_ff_hold | 4.0 | repair_TNS best 150413 last 150413 rows 1 | before-window best 150413, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc10 | dpkit-kv3_hg_v1p3__r81da466fe-1840159 | kv3_hg_v1p3__r81da466fe | 5_1_grt | 8.9 | grt rounds 2 overflow 5:40256 -> 10:36108 | GRT-LABEL: DESIGN-FAIL: overflow 36108 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | 5_1_grt | 13.2 | grt rounds 2 overflow 5:94600 -> 10:59159 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc11 | dpkit-kv3_pv_v2e-1156839 | kv3_pv_v2e | 5_1_grt | 1.3 | grt rounds 2 overflow 5:54763 -> 10:39326 | GRT-LABEL: DESIGN-FAIL: overflow 39326 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v4e-1100418 | kv3_pv_v4e | 5_1_grt | 1.3 | grt rounds 2 overflow 5:112464 -> 10:88021 | GRT-LABEL: DESIGN-FAIL: overflow 88021 at round 10 > 1000 |  |
| epyc2 | dpkit-kv3_hgi_v8-2737550 | kv3_hgi_v8 | 5_1_grt | 8.3 | grt rounds 2 overflow 5:54135 -> 10:40850 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-3490222 | cbn_q01 | 5_1_grt | 1.2 | grt rounds 2 overflow 5:81921 -> 10:75607 | GRT-LABEL: DESIGN-FAIL: overflow 75607 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi_v6-102352 | kv3_hgi_v6 | 5_1_grt | 9.3 | grt rounds 2 overflow 5:53849 -> 10:29026 | GRT-LABEL: DESIGN-FAIL: overflow 29026 at round 10 > 1000 |  |
| epyc10 | dpkit-hd_lep0N_w-3160116 | hd_lep0N_w | 4_2_tapbal_grt | 0.5 | last meaningful line 0.0 h ago (46/52 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p5-970860 | kv3_hg_v1p5 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (7212/7213 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v4-2996257 | kv3_hgi_v4 | 3_3_place_gp | 0.6 | overflow best 0.2689 last 0.2689 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | pregrt_ff_hold | 9.3 | repair_TNS best 31879.7 last 31879.7 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-961899 | kv3_pc_v1 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (6509/6509 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r877307f5d-1492582 | kv3_pc_v1 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (6408/6408 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8c9cba7ae-3297443 | kv3_pc_v1 | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (6073/6073 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-19761 | kv3_pc_v1 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (6500/6500 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl7f648944__r8f64f1de3-2041438 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.9 | overflow best 0.149 last 0.149 rows 45 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v12-1535838 | kv3_pv_v12 | 5_1_grt | 7.5 | last meaningful line 1.5 h ago (268/1277 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-native59-3384403 | native59 | 5_1_grt | 8.2 | last meaningful line 0.1 h ago (177/190 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-phy_serdes-3657780 | phy_serdes | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (2212/2212 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | 5_2_route | 14.2 | drt_violations best 15870 last 15870 rows 3 | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_su_l1__cl5ea486db-3304485 | sle_su_l1 | 3_3_place_gp | 0.4 | overflow best 0.1161 last 0.1161 rows 45 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 15.9 | drt_violations best 71235 last 71235 rows 2 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_2_route | 15.9 | drt_violations best 378938 last 378938 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 5_2_route | 16.0 | last meaningful line 0.5 h ago (276/277 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | postcts_gate_FF | 14.6 | last meaningful line -0.0 h ago (24613/24613 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2082061 | slw_st_a_v1 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (6176/6176 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3681869 | slw_st_b_v2 | 5_2_route | 10.2 | drt_violations best 129849 last 129849 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_055922_2792445-i1-2623359 | eco_20261125_055922_2792445-i1 | 5_2_route | 4.7 | drt_violations best 137 last 137 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_073109_4058437-i1t-725979 | eco_20261125_073109_4058437-i1t | 5_2_route | 3.2 | drt_violations best 9324 last 9324 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | so_3366613_ff_62366 | so_3366613_ff_62366 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc10 | so_3366613_tt_62366 | so_3366613_tt_62366 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc10 | so_3744863_ff_51676 | so_3744863_ff_51676 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc10 | so_3744863_tt_51676 | so_3744863_tt_51676 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc10 | so_3882612_ff_76498 | so_3882612_ff_76498 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc10 | so_3882612_tt_76498 | so_3882612_tt_76498 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc10 | so_3977924_ff_1264 | so_3977924_ff_1264 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc10 | so_3977924_tt_1264 | so_3977924_tt_1264 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc11 | dpkit-kv3_pv_v3ne-1144152 | kv3_pv_v3ne | lec | 1.3 | LEC last write 0.1 h ago | YOUNG: evidence 1.3 h < 6 h |  |
| epyc11 | dpkit-kv3_pv_v4-1052719 | kv3_pv_v4 | lec | 1.4 | LEC last write 0.1 h ago | YOUNG: evidence 1.4 h < 6 h |  |
| epyc11 | dpkit-kv3_pv_v4ne-1191938 | kv3_pv_v4ne | lec | 1.3 | LEC last write 0.1 h ago | YOUNG: evidence 1.3 h < 6 h |  |
| epyc11 | dpkit-kv3_pv_v5-1052229 | kv3_pv_v5 | lec | 1.4 | LEC last write 0.1 h ago | YOUNG: evidence 1.4 h < 6 h |  |
| epyc11 | dpkit-kv3_pv_v5e-1092206 | kv3_pv_v5e | lec | 1.3 | LEC last write 0.1 h ago | YOUNG: evidence 1.3 h < 6 h |  |
| epyc11 | dpkit-kv3_pv_v6e-864517 | kv3_pv_v6e | lec | 1.5 | LEC last write 0.1 h ago | YOUNG: evidence 1.5 h < 6 h |  |
| epyc11 | dpkit-kv3_pv_v7-1078343 | kv3_pv_v7 | lec | 1.3 | LEC last write 0.1 h ago | YOUNG: evidence 1.3 h < 6 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 5_2_route | 12.8 | drt_violations best 24275 last 24275 rows 2 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl38badc56-3834531 | sle_hc0 | 6_report | 13.8 | last meaningful line 0.0 h ago (77/77 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 5_2_route | 12.5 | drt_violations best 134998 last 134998 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | postcts_gate_FF | 7.5 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl92142dac-2960548 | slw_su_c | 4_1_cts | 3.8 | last meaningful line 0.5 h ago (8522/8522 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc11 | eco-abs-2791981 | eco-abs | generate_abstract | 0.5 | last meaningful line 0.3 h ago (1028/1028 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 16.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-381902-2867 | 381902 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc11 | otc-701492-14947 | 701492 | lec | 3.1 | LEC last write 3.1 h ago | YOUNG: evidence 3.1 h < 6 h |  |
| epyc11 | prd-count-p1_tc-897106 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_154417_1016084-i2-2211039 | eco_20261124_154417_1016084-i2 | 5_1_grt | 0.8 | last meaningful line 0.5 h ago (141/141 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i2t-2255468 | eco_20261124_190641_1260390-i2t | 5_1_grt | 0.8 | last meaningful line 0.2 h ago (141/141 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_080242_341091-i1-2097287 | eco_20261125_080242_341091-i1 | 5_2_route | 2.6 | last meaningful line 0.1 h ago (265/265 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_080337_31727-i1-2053095 | eco_20261125_080337_31727-i1 | 5_2_route | 2.6 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_082938_54055-i1-3146788 | eco_20261125_082938_54055-i1 | 5_2_route | 2.2 | last meaningful line 0.5 h ago (133/133 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_092112_274675-i1-1256057 | eco_20261125_092112_274675-i1 | 5_1_grt | 1.3 | last meaningful line 0.1 h ago (295/312 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_092728_2532622-i1-1376598 | eco_20261125_092728_2532622-i1 | 5_2_route | 1.2 | last meaningful line 0.0 h ago (118/118 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | so_2186946_ff_58433 | so_2186946_ff_58433 | generate_abstract | 0.8 | last meaningful line 0.8 h ago (1034/1034 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | so_2186946_tt_58433 | so_2186946_tt_58433 | generate_abstract | 0.8 | last meaningful line 0.8 h ago (1034/1034 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc12 | dpkit-hd_lep0N-2152952 | hd_lep0N | 4_1_cts | 0.2 | last meaningful line 0.2 h ago (24/24 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl7f648944__r8422a4b86-1394259 | kv3_pc_v1 | 3_3_place_gp | 0.9 | overflow best 0.0992 last 0.0992 rows 46 | YOUNG: stage 0.3 h < 1 h |  |
| epyc12 | dpkit-kv3_pv_v12-2339543 | kv3_pv_v12 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (8132/8132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pv_v1n-1216451 | kv3_pv_v1n | 3_1_place_gp_skip_io | 1.0 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-native59-1179753 | native59 | 3_4_place_resized | 1.1 | last meaningful line 0.0 h ago (328/328 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-slw_st_a_v2__clf4365a62-2414803 | slw_st_a_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (6342/6343 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | otc-2510638-12477 | 2510638 | x | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | otc-2510639-18810 | 2510639 | x | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | otc-2510640-11975 | 2510640 | x | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | otc-2510643-24003 | 2510643 | x | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | otc-2510651-1569 | 2510651 | x | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_sys_c-3635023 | kv3_sys_c | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_1_grt | 1.0 | repair_Remaining best 54715 last 54715 rows 95 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1216203 | sle_st_b_v1 | 5_2_route | 6.8 | last meaningful line 0.2 h ago (285/286 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-360401 | sle_st_b_v2 | 5_2_route | 5.8 | last meaningful line 0.2 h ago (281/282 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2601551 | slw_st_a_v1 | 5_1_grt | 1.3 | last meaningful line 0.0 h ago (2069/2086 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | otc-146801-7119 | 146801 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc2 | otc-317763-1040 | 317763 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc2 | otc-3847527-9693 | 3847527 | signoff | 0.7 | last meaningful line 0.6 h ago (3/3 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_204708_4151707-i1-226978 | eco_20261124_204708_4151707-i1 | 5_2_route | 2.3 | drt_violations best 477 last 477 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | relec-r2-R11_hdmesh_auto | relec-r2-R11_hdmesh_auto | - | 15.4 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbf_q00_s2-3518685 | cbf_q00_s2 | 5_1_grt | 4.4 | last meaningful line 0.1 h ago (146/146 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-coll_core-3493022 | coll_core | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (11338/11338 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 5_1_grt | 10.1 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (5913/5913 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (5783/5783 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v3-2521918 | sle_sc_v3 | 5_1_grt | 1.7 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3817081 | sle_st_a_v2 | 5_2_route | 2.7 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-577851 | slw_sc_v1 | 5_1_grt | 2.4 | last meaningful line 0.2 h ago (145/145 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 4_1_cts | 1.6 | last meaningful line 0.2 h ago (5790/5790 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | postcts_gate_TT | 4.3 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-3807127 | slw_su_l1 | 5_2_route | 4.3 | last meaningful line 0.4 h ago (274/275 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | otc-975787-22428 | 975787 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261124_175441_992552-i3-2994934 | eco_20261124_175441_992552-i3 | 5_2_route | 1.4 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i2t-2177999 | eco_20261124_192157_3493836-i2t | 5_2_route | 3.4 | drt_violations best 499 last 499 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i2-3644612 | eco_20261124_235631_1843084-i2 | 5_2_route | 1.2 | last meaningful line 0.2 h ago (254/255 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_073745_2194631-i1-2944509 | eco_20261125_073745_2194631-i1 | 5_2_route | 3.1 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_081621_2016666-i1-599553 | eco_20261125_081621_2016666-i1 | 5_2_route | 2.4 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_094206_1890550-i1-4068402 | eco_20261125_094206_1890550-i1 | 5_1_grt | 1.0 | last meaningful line 0.1 h ago (295/321 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_103149_2129512-i1-1443376 | eco_20261125_103149_2129512-i1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | so_296151_ff_37610 | so_296151_ff_37610 | signoff | 0.8 |  | NO-DATA: empty log |  |
| epyc7 | so_296151_tt_37610 | so_296151_tt_37610 | signoff | 0.8 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv2833ee2b-3715623 | col_h9_r2__t1 | 3_3_place_gp | 0.3 | overflow best 0.4137 last 0.4364 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_hg_v1p5-3496343 | kv3_hg_v1p5 | hold_gate | 0.3 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v3n-3977907 | kv3_pv_v3n | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (245/245 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_kv_leaf__t1-3593475 | ot_s81sl_kv_leaf__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8342 last 0.8342 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_2_route | 18.6 | drt_violations best 320246 last 320246 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 6_report | 18.6 | last meaningful line 0.2 h ago (69/69 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 6_report | 18.6 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 6_report | 18.6 | last meaningful line 0.1 h ago (68/68 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | eco-abs-4094970 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | otc-3678186-167 | 3678186 | - | 4.0 |  | NO-DATA: no log found |  |
| epyc8 | prd-count-p1_tc-521874 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3-32256 | eco_20261123_164145_1995767-i3 | 5_3_fillcell | 6.8 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_025941_3548303-i1-3306668 | eco_20261125_025941_3548303-i1 | 5_2_route | 1.8 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_082653_3900765-i1-1572735 | eco_20261125_082653_3900765-i1 | 5_2_route | 2.3 | drt_violations best 4 last 4 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_091937_4000900-i1-378808 | eco_20261125_091937_4000900-i1 | 5_1_grt | 1.4 | last meaningful line 0.6 h ago (295/429 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | relec-r2-R10_hdmesh_ak | relec-r2-R10_hdmesh_ak | - | 15.5 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-U1_hc3_pv39aac7a1 | relec-r2-U1_hc3_pv39aac7a1 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc8 | relec-r2-U2_t40 | relec-r2-U2_t40 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc8 | so_2176134_ff_15012 | so_2176134_ff_15012 | signoff | 0.8 |  | NO-DATA: empty log |  |
| epyc8 | so_2176134_tt_15012 | so_2176134_tt_15012 | signoff | 0.8 |  | NO-DATA: empty log |  |
| epyc8 | so_3649097_ff_73003 | so_3649097_ff_73003 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc8 | so_3649097_tt_73003 | so_3649097_tt_73003 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc8 | so_406720_ff_62401 | so_406720_ff_62401 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc8 | so_406720_tt_62401 | so_406720_tt_62401 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | pregrt_ff_hold | 4.0 | repair_TNS best 127105 last 127105 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pv07945c1e-55623 | col_h10_r0_p4__t1 | 5_1_grt | 4.5 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | lec | 4.0 | LEC last write 0.0 h ago | YOUNG: evidence 4.0 h < 6 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b-3679007 | col_h9_r0_p3__t1 | 5_1_grt | 4.0 | last meaningful line 1.3 h ago (274/1308 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-296584 | col_h9_r0_p3__t1 | 5_1_grt | 6.6 | last meaningful line 1.7 h ago (271/1307 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3698869 | col_h9_r0_p4__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 47200.4 last 47200.4 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-4053150 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.2 | last meaningful line 0.5 h ago (61/77 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv31e47bd5-4047516 | col_h9_r2__t1 | lec | 1.2 | LEC last write 0.2 h ago | YOUNG: evidence 1.2 h < 6 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | lec | 5.9 | LEC last write 0.0 h ago | YOUNG: evidence 5.9 h < 6 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-3394850 | col_h9_r2__t1 | postcts_gate_TT | 4.1 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-3707756 | col_h9_r2__t1 | 5_2_route | 4.0 | last meaningful line 0.0 h ago (264/265 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve0486b40-3725060 | col_h9_r2__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 29815.1 last 29815.1 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | 5_2_route | 5.0 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t10-3695203 | dsdv_slice_c1x_C__t10 | 3_3_place_gp | 3.0 | last meaningful line 0.1 h ago (50/50 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-578982 | dsdv_slice_c1x_C__t8 | 3_1_place_gp_skip_io | 2.9 | overflow best 0.2281 last 0.2281 rows 41 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-3691225 | dsdv_slice_c1x_C__t9 | 3_1_place_gp_skip_io | 3.0 | overflow best 0.2589 last 0.2589 rows 38 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_kv512_C__t1-4058196 | dsdv_slice_kv512_C__t1 | 3_3_place_gp | 1.2 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t25__cl55642d17-3495886 | ot_s81sl_leaf__t25 | 5_1_grt | 1.9 | last meaningful line 0.5 h ago (266/1276 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-1607161 | sle_ctl | postcts_gate_TT | 15.0 | last meaningful line 0.5 h ago (23/23 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-3479533 | slice_station__t37 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t42__clcf44e680-3472830 | slice_station__t42 | postcts_gate_FF | 1.9 | last meaningful line 0.0 h ago (438/438 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-2620358 | slice_station__t52 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (3774/3774 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | otc-3780674-20608 | 3780674 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | otc-3814206-23240 | 3814206 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261125_090100_666856-i1-787277 | eco_20261125_090100_666856-i1 | 5_2_route | 1.7 | last meaningful line 0.1 h ago (261/262 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | ap-ageom-kw-slice-station--t30--cl1653104c-grt-1919859 | slice-station--t30--cl1653104c-grt | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t5-2902751 | ot_s81sl_kv_leaf__t5 | 3_3_place_gp | 0.7 | overflow best 0.1992 last 0.1992 rows 40 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-serdes__t15__cla3d02796-2608833 | serdes__t15 | 2_4_floorplan_pdn | 0.8 | last meaningful line 0.1 h ago (92/92 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | postcts_gate_TT | 9.7 | last meaningful line 0.2 h ago (371/371 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 5_2_route | 14.0 | last meaningful line 0.5 h ago (271/272 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | postcts_gate_FF | 11.4 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 5_2_route | 12.5 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 5_2_route | 13.7 | drt_violations best 104717 last 104717 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | postcts_gate_FF | 12.2 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | generate_abstract | 17.6 | last meaningful line 0.1 h ago (24/24 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-1906930-22563 | 1906930 | eq16 | 0.0 | last meaningful line 0.0 h ago (557903/557903 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-2020602-13294 | 2020602 | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | otc-2034160-21999 | 2034160 | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261124_235251_4176465-i1-1838007 | eco_20261124_235251_4176465-i1 | 5_2_route | 2.8 | drt_violations best 77 last 77 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1t-3347319 | eco_20261125_002226_1452841-i1t | 5_2_route | 2.3 | last meaningful line 0.2 h ago (136/136 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | prd-eco_20261125_020407_3088231-i1-2998029 | eco_20261125_020407_3088231-i1 | 5_1_grt | 0.6 | last meaningful line 0.2 h ago (142/142 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | so_1094763_ff_89367 | so_1094763_ff_89367 | generate_abstract | 1.6 | last meaningful line 1.5 h ago (876/876 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3587886 | coll_ftm | 5_2_route | 2.0 | drt_violations best 10288 last 10288 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-862971 | kv3_io_ft | generate_abstract | 1.4 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-705307 | kv3_pc_v1 | 3_5_place_dp | 1.5 | last meaningful line 0.1 h ago (32/32 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8e7d31598-707215 | kv3_pc_v1 | 3_5_place_dp | 1.5 | last meaningful line 0.1 h ago (32/32 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-2390236 | slw_st_b_v1 | 5_2_route | 10.1 | drt_violations best 24159 last 24159 rows 2 | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel2 | otc-594090-20209 | 594090 | otrun16 | 1.5 | last meaningful line 0.5 h ago (2/2 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | so_296115_ff_49711 | so_296115_ff_49711 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_296115_tt_49711 | so_296115_tt_49711 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | dpkit-kv3_hgi-1955823 | kv3_hgi | 5_1_grt | 0.9 |  | KEEP: kv3_hgi_1124155644	KV-OWN-RSTREACH	combined HEADLEG2+HGI-LEAF ship form; noprog  |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-436421 | kv3_hgi_v2 | 5_1_grt | 1.2 |  | KEEP: kv3_hgi_v2__cl2862d491_1124155702	KV-OWN-RSTREACH	combined hgi_v2 ship form (COO |  |
| intel1 | prd-eco_qcgu_1125-i1-3514577 | eco_qcgu_1125-i1 | 5_2_route | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_2_route | 17.0 | drt_violations best 416066 last 416066 rows 1 | before-window best 416066, window best 416066 | PROGRESS: drt_violations: active iteration at 259507 < best completed total 416066 (in-ite |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 17.2 | drt_violations best 15970 last 15970 rows 4 | before-window best 329677, window best 15970 | PROGRESS: drt_violations improved 95.2 % in window |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 29.7 | drt_violations best 14980 last 63558 rows 18 | before-window best 15279, window best 14980 | PROGRESS: drt_violations: falling inside the active iteration (63558 -> 44681) |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 22.0 | drt_violations best 6298 last 6298 rows 16 | before-window best 11997, window best 6298 | PROGRESS: drt_violations improved 47.5 % in window |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-3286653 | sle_st_a_v2 | 5_1_grt | 1.0 | repair_TNS best 0 last 0 rows 16 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 42.4 | drt_violations best 5300 last 5300 rows 23 | before-window best 7726, window best 5300 | PROGRESS: drt_violations improved 31.4 % in window |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 27.1 | drt_violations best 2761 last 13398 rows 18 | before-window best 3168, window best 2761 | PROGRESS: drt_violations improved 12.8 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 23.3 | drt_violations best 6764 last 6764 rows 12 | before-window best 84872, window best 6764 | PROGRESS: drt_violations improved 92.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 21.9 | drt_violations best 19336 last 19336 rows 9 | before-window best 510309, window best 19336 | PROGRESS: drt_violations improved 96.2 % in window |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 17.3 | drt_violations best 69907 last 69907 rows 6 | before-window best 412199, window best 69907 | PROGRESS: drt_violations improved 83.0 % in window |  |
| epyc7 | dpkit-sle_su_l1__clc6d66f5b-2521917 | sle_su_l1 | 5_1_grt | 1.7 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 21.7 | drt_violations best 10869 last 10869 rows 10 | before-window best 457993, window best 10869 | PROGRESS: drt_violations improved 97.6 % in window |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 27.3 | drt_violations best 62636 last 62636 rows 11 | before-window best 66304, window best 62636 | PROGRESS: drt_violations improved 5.5 % in window |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 23.4 | drt_violations best 51610 last 51610 rows 10 | before-window best 54030, window best 51610 | PROGRESS: drt_violations improved 4.5 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-534954 | slw_su_l1 | tt_setup_repair_grt | 3.9 | repair_Violations best 0 last 0 rows 46 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | prd-eco_20261125_073945_2252980-i1t-3004488 | eco_20261125_073945_2252980-i1t | 5_2_route | 3.1 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 18.6 | drt_violations best 30420 last 30420 rows 5 | before-window best 478667, window best 30420 | PROGRESS: drt_violations improved 93.6 % in window |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 5_2_route | 18.6 | drt_violations best 0 last 0 rows 8 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 18.6 | drt_violations best 266434 last 266434 rows 1 | before-window best 266434, window best 266434 | PROGRESS: drt_violations: active iteration at 164055 < best completed total 266434 (in-ite |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 5_2_route | 18.6 | drt_violations best 0 last 0 rows 9 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 18.6 | drt_violations best 105634 last 105634 rows 2 | before-window best 450083, window best 105634 | PROGRESS: drt_violations improved 76.5 % in window |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_2_route | 18.5 | drt_violations best 51861 last 51861 rows 7 | before-window best 119058, window best 51861 | PROGRESS: drt_violations improved 56.4 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 18.6 | drt_violations best 8666 last 8666 rows 16 | before-window best 15345, window best 8666 | PROGRESS: drt_violations improved 43.5 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 4_2_tapbal_grt | 1.2 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pvf1445dce-2628247 | col_h9_r2__t1 | 4_2_tapbal_grt | 0.6 | repair_Violations best 0 last 0 rows 3 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-hd_serdes-1072573 | hd_serdes | 5_2_route | 15.3 | drt_violations best 1371 last 1538 rows 31 | before-window best 1536, window best 1371 | PROGRESS: drt_violations improved 10.7 % in window |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_2_route | 15.5 | drt_violations best 48902 last 48902 rows 7 | before-window best 474459, window best 48902 | PROGRESS: drt_violations improved 89.7 % in window |  |
| epyc9 | dpkit-slice_station__t43-3486441 | slice_station__t43 | 5_1_grt | 1.9 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 15.7 | drt_violations best 56 last 56 rows 21 | before-window best 274895, window best 56 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1177242 | kv3_hg_v1p3__r838481cd7 | pregrt_ff_hold | 3.1 | repair_Violations best 909 last 933 rows 91 | before-window best 41019, window best 909 | PROGRESS: repair_Violations improved 97.8 % in window |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 5_2_route | 22.0 | drt_violations best 317907 last 317907 rows 1 | before-window best 317907, window best 317907 | PROGRESS: drt_violations: active iteration at 86370 < best completed total 317907 (in-iter |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 5_2_route | 17.6 | drt_violations best 23446 last 23446 rows 2 | before-window best 163425, window best 23446 | PROGRESS: drt_violations improved 85.7 % in window |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-1451177 | sle_stm_v1 | 5_2_route | 15.7 | drt_violations best 534 last 534 rows 4 | before-window best 144494, window best 534 | PROGRESS: drt_violations improved 99.6 % in window |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 13.9 | drt_violations best 1 last 1 rows 22 | before-window best 41642, window best 1 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 21.9 | drt_violations best 71761 last 71761 rows 3 | before-window best 398476, window best 71761 | PROGRESS: drt_violations improved 82.0 % in window |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 5_2_route | 17.6 | drt_violations best 138053 last 138053 rows 1 | before-window best 138053, window best 138053 | PROGRESS: drt_violations: active iteration at 22972 < best completed total 138053 (in-iter |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 17.1 | drt_violations best 9186 last 9186 rows 8 | before-window best 367946, window best 9186 | PROGRESS: drt_violations improved 97.5 % in window |  |
