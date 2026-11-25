# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 04:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'UNSIGNABLE': 1, 'GRT-LABEL': 4, 'NO-DATA': 27, 'YOUNG': 149, 'KEEP': 3, 'EXCLUDED': 1, 'PROGRESS': 33}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_pv_v3-4187490 | kv3_pv_v3 | pregrt_ff_hold | 8.2 | repair_TNS best 117231 last 117231 rows 1 | before-window best 117231, window best 117231 | NO-PROGRESS: repair_TNS best 117231 vs 117231 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (KV-ALLFIX decides; neve |
| epyc8 | otc-120424-12773 | 120424 | signoff | 9.9 | last meaningful line 9.8 h ago (3/3 lines) | NO-PROGRESS: no new non-iteration log line for 9.8 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| intel1 | dpkit-kv3_hgi_v6-102352 | kv3_hgi_v6 | tt_setup_repair_grt | 10.8 | last meaningful line 0.0 h ago (808/808 lines) | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -407.72 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc10 | dpkit-kv3_hg_v1p3__r81da466fe-1840159 | kv3_hg_v1p3__r81da466fe | 5_1_grt | 10.4 | grt rounds 2 overflow 5:40256 -> 10:36108 | GRT-LABEL: DESIGN-FAIL: overflow 36108 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v12-1535838 | kv3_pv_v12 | 5_1_grt | 9.0 | grt rounds 2 overflow 5:92646 -> 10:58944 | GRT-LABEL: DESIGN-FAIL: overflow 58944 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_pv_v12-3368835 | kv3_pv_v12 | 5_1_grt | 14.7 | grt rounds 2 overflow 5:94600 -> 10:59159 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-3490222 | cbn_q01 | 5_1_grt | 2.7 | grt rounds 2 overflow 5:81921 -> 10:75607 | GRT-LABEL: DESIGN-FAIL: overflow 75607 at round 10 > 1000 |  |
| epyc10 | ap-ageom-kw-kv3-pc-v1--cl4ea58a5c--r828e1c2a5-grt-3390130 | kv3-pc-v1--cl4ea58a5c--r828e1c2a5-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | ap-ageom-kw-kv3-pc-v1--cl7f648944--r8e7d31598-grt-3233442 | kv3-pc-v1--cl7f648944--r8e7d31598-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-hd_lep0N_w-3160116 | hd_lep0N_w | 5_2_route | 2.0 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p5-970860 | kv3_hg_v1p5 | tt_setup_repair | 2.6 | repair_Violations best 7007 last 7007 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | 5_1_grt | 10.8 | last meaningful line 0.1 h ago (159/159 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-961899 | kv3_pc_v1 | tt_setup_repair | 2.6 | repair_Viol best 9606 last 9606 rows 30 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r877307f5d-1492582 | kv3_pc_v1 | tt_setup_repair | 2.5 | last meaningful line 0.0 h ago (401/401 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8c9cba7ae-3297443 | kv3_pc_v1 | 4_1_cts | 1.9 | last meaningful line 0.0 h ago (6665/6665 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8ef700d7c-19761 | kv3_pc_v1 | tt_setup_repair | 2.8 | repair_Violations best 450 last 474 rows 25 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-native59-3384403 | native59 | tt_setup_measure_grt | 9.7 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-phy_serdes-3657780 | phy_serdes | 5_1_grt | 1.8 | last meaningful line 1.3 h ago (2233/3239 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pv0e7b1dcc-1843092 | sle_st_b_v1 | 6_report | 15.7 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 5_2_route | 17.5 | drt_violations best 227744 last 227744 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | 5_2_route | 16.1 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2082061 | slw_st_a_v1 | postcts_gate_FF | 2.4 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3681869 | slw_st_b_v2 | 6_report | 11.7 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | eco-abs-3144660 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-1191841-12698 | 1191841 | signoff | 1.1 | last meaningful line 1.0 h ago (3/3 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | otc-1471300-23748 | 1471300 | signoff | 1.0 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | otc-1762308-21603 | 1762308 | signoff | 0.9 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | practical_noyce | practical_noyce | etm | 0.1 | last meaningful line 0.0 h ago (389/389 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-count-p1_tc-725979 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_112234_1159095-i1-1820297 | eco_20261125_112234_1159095-i1 | 5_1_grt | 0.8 | last meaningful line 0.3 h ago (295/322 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v4n-2809393 | kv3_pv_v4n | tt_setup_repair | 0.1 | repair_Viol best 2126 last 2126 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-kv3_pv_v5-1052229 | kv3_pv_v5 | lec | 2.9 | LEC last write 0.4 h ago | YOUNG: evidence 2.9 h < 6 h |  |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | 5_1_grt | 14.6 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl05696ed1-519611 | sle_hc0 | 5_2_route | 14.3 | drt_violations best 32 last 32 rows 12 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 5_2_route | 14.0 | drt_violations best 19457 last 19457 rows 2 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | 5_2_route | 9.0 | last meaningful line 0.1 h ago (262/262 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl92142dac-2960548 | slw_su_c | pregrt_ff_hold | 5.3 | repair_TNS best 64727.5 last 64727.5 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc11 | otc-141162-25188 | 141162 | lec | 1.3 | LEC last write 1.3 h ago | YOUNG: evidence 1.3 h < 6 h |  |
| epyc11 | otc-381902-2867 | 381902 | - | 3.2 |  | NO-DATA: no log found |  |
| epyc11 | prd-eco_20261124_154417_1016084-i2-2211039 | eco_20261124_154417_1016084-i2 | 5_2_route | 2.3 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i2t-2255468 | eco_20261124_190641_1260390-i2t | 5_2_route | 2.3 | last meaningful line 0.2 h ago (133/133 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i2t-96653 | eco_20261124_200101_1087713-i2t | 5_2_route | 1.3 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_080242_341091-i1-2097287 | eco_20261125_080242_341091-i1 | 5_2_route | 4.1 | drt_violations best 33 last 33 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_082938_54055-i1-3146788 | eco_20261125_082938_54055-i1 | 5_2_route | 3.7 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_092112_274675-i1-1256057 | eco_20261125_092112_274675-i1 | 5_2_route | 2.8 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_092728_2532622-i1-1376598 | eco_20261125_092728_2532622-i1 | 5_2_route | 2.7 | drt_violations best 12 last 12 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_120946_3832190-i1t-2887287 | eco_20261125_120946_3832190-i1t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | prd-fin-2053095 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | so_1252901_ff_18611 | so_1252901_ff_18611 | generate_abstract | 0.8 | last meaningful line 0.8 h ago (1034/1034 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | so_1252901_tt_18611 | so_1252901_tt_18611 | generate_abstract | 0.8 | last meaningful line 0.8 h ago (1034/1034 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | so_1697458_ff_33860 | so_1697458_ff_33860 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (35/35 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | so_1697458_tt_33860 | so_1697458_tt_33860 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (35/35 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc12 | dpkit-dsdv_slice_lepe_mu_LP__t2-1093988 | dsdv_slice_lepe_mu_LP__t2 | tt_setup_repair | 0.1 | repair_Viol best 16 last 16 rows 21 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-hd_lep0N-2152952 | hd_lep0N | 4_2_tapbal_grt | 1.7 | last meaningful line 0.3 h ago (48/49 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc12 | dpkit-kv3_hgi_v7-2529031 | kv3_hgi_v7 | tt_setup_repair | 1.5 | repair_Viol best 75 last 75 rows 37 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl7f648944__r8422a4b86-1394259 | kv3_pc_v1 | 3_5_place_dp | 2.4 | last meaningful line 0.0 h ago (59/59 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pv_v12-2339543 | kv3_pv_v12 | 4_1_cts | 1.6 | last meaningful line 0.0 h ago (9046/9046 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pv_v1n-1216451 | kv3_pv_v1n | 3_5_place_dp | 2.5 | last meaningful line 0.2 h ago (59/59 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | dpkit-sle_ctl__cla4f6f12f-2847382 | sle_ctl | 3_3_place_gp | 1.3 | overflow best 0.2441 last 0.8233 rows 20 | YOUNG: stage 0.3 h < 1 h |  |
| epyc12 | dpkit-sle_st_a_v1__cl67389ecd-849428 | sle_st_a_v1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-slw_st_a_v2__clf4365a62-2414803 | slw_st_a_v2 | 5_1_grt | 1.6 | last meaningful line 0.0 h ago (2064/2064 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc12 | dpkit-slw_st_a_v2__clf4365a62-969497 | slw_st_a_v2 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dproto-kv-fpkv_it0_A5t7-kit | dproto-kv-fpkv_it0_A5t7-kit | launch_fw_B | 0.1 | last meaningful line 0.0 h ago (1343/1343 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dproto-s81-c9s-kit | dproto-s81-c9s-kit | - | 0.5 |  | NO-DATA: no log found |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc12 | leccsp-new | leccsp-new | - | 0.2 |  | NO-DATA: no log found |  |
| epyc12 | otc-1142303-19657 | 1142303 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc12 | otc-1345345-29885 | 1345345 | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (232/232 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | otc-3501458-13012 | 3501458 | drc_merged | 0.9 | last meaningful line 0.0 h ago (244/244 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc12 | otc-583026-15829 | 583026 | asbuilt.yosys | 0.3 | last meaningful line -0.0 h ago (135471/135471 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | otc-681372-16932 | 681372 | asbuilt.yosys | 0.3 | last meaningful line -0.0 h ago (135733/135733 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | qcdrt-fw-A | qcdrt-fw-A | - | 1.3 |  | NO-DATA: no log found |  |
| epyc12 | qcdrt-fw-B | qcdrt-fw-B | - | 1.3 |  | NO-DATA: no log found |  |
| epyc12 | qcdrt-fw-C | qcdrt-fw-C | - | 1.3 |  | NO-DATA: no log found |  |
| epyc12 | qcdrt-sc-A | qcdrt-sc-A | - | 1.3 |  | NO-DATA: no log found |  |
| epyc12 | qcdrt-sc-B | qcdrt-sc-B | - | 1.3 |  | NO-DATA: no log found |  |
| epyc12 | qcdrt-sc-C | qcdrt-sc-C | - | 1.3 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-kv3_hub_Wi-3068909 | kv3_hub_Wi | 2_1_floorplan | 0.4 | repair_Viol best 4941 last 4941 rows 124 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 2.5 | last meaningful line 0.1 h ago (264/265 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-3286653 | sle_st_a_v2 | 5_2_route | 2.5 | last meaningful line 0.1 h ago (277/278 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1216203 | sle_st_b_v1 | 5_2_route | 8.3 | drt_violations best 19315 last 19315 rows 2 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-360401 | sle_st_b_v2 | 5_2_route | 7.3 | drt_violations best 10161 last 10161 rows 3 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t21-3729063 | slice_station__t21 | 3_3_place_gp | 0.1 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t29__cl2e5c855a-3725263 | slice_station__t29 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t30__cl1653104c-3734230 | slice_station__t30 | 3_3_place_gp | 0.1 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t51-3820129 | slice_station__t51 | lec | 0.0 | LEC last write 0.0 h ago | YOUNG: evidence 0.0 h < 6 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2601551 | slw_st_a_v1 | 5_2_route | 2.8 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | eco-abs-3551485 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.1 h ago (29/29 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | gracious_zhukovsky | gracious_zhukovsky | etm | 0.0 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-146801-7119 | 146801 | - | 1.9 |  | NO-DATA: no log found |  |
| epyc2 | pedantic_wescoff | pedantic_wescoff | etm | 0.1 | last meaningful line 0.0 h ago (436/436 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00_s2-3518685 | cbf_q00_s2 | 5_1_grt | 5.9 | last meaningful line 1.0 h ago (256/1266 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-coll_core-3493022 | coll_core | 4_1_cts | 2.7 | last meaningful line 0.2 h ago (11507/11507 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-hd_serdes-2729222 | hd_serdes | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 5_1_grt | 11.6 | last meaningful line 0.5 h ago (296/1305 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | 5_1_grt | 5.9 | last meaningful line 0.2 h ago (274/939 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_1_grt | 2.7 | last meaningful line 0.3 h ago (143/143 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v3-2521918 | sle_sc_v3 | 5_1_grt | 3.2 | last meaningful line 0.2 h ago (1899/1927 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3817081 | sle_st_a_v2 | 5_2_route | 4.2 | last meaningful line 0.1 h ago (280/281 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__clc6d66f5b-2521917 | sle_su_l1 | 5_2_route | 3.2 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-577851 | slw_sc_v1 | 5_1_grt | 3.9 | last meaningful line 0.1 h ago (2059/2065 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_1_grt | 3.1 | last meaningful line 0.2 h ago (265/1271 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 5.8 | last meaningful line 0.2 h ago (266/266 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-3807127 | slw_su_l1 | 5_2_route | 5.8 | drt_violations best 279991 last 279991 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc7 | prd-count-p1_tc-2177999 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i3-2994934 | eco_20261124_175441_992552-i3 | 5_3_fillcell | 2.9 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_235631_1843084-i2-3644612 | eco_20261124_235631_1843084-i2 | 5_2_route | 2.7 | drt_violations best 5315 last 5315 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_073745_2194631-i1-2944509 | eco_20261125_073745_2194631-i1 | 5_2_route | 4.6 | drt_violations best 41 last 41 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_073945_2252980-i1-3230821 | eco_20261125_073945_2252980-i1 | 5_1_grt | 0.9 | last meaningful line 0.1 h ago (290/345 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_081621_2016666-i1-599553 | eco_20261125_081621_2016666-i1 | 5_2_route | 3.9 | drt_violations best 23 last 23 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_094206_1890550-i1-4068402 | eco_20261125_094206_1890550-i1 | 5_2_route | 2.5 | last meaningful line 0.2 h ago (263/263 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_103149_2129512-i1-1443376 | eco_20261125_103149_2129512-i1 | 5_2_route | 1.7 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_110124_1979736-i1-2551803 | eco_20261125_110124_1979736-i1 | 5_1_grt | 1.2 | last meaningful line 0.3 h ago (290/386 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | admiring_franklin | admiring_franklin | etm | 0.0 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-918588 | col_h10_r0_p1__t1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-958439 | col_h9_r2__t1 | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-794020 | col_h9_r2__t1 | 2_1_floorplan | 0.1 | repair_Viol best 2770 last 2770 rows 1357 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r2__t1__clce45cab5__pva119e808-402535 | col_h9_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.4825 last 0.4905 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_mu_C__t1-730122 | dsdv_slice_lepe_mu_C__t1 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p5-3496343 | kv3_hg_v1p5 | pregrt_ff_hold | 1.8 | repair_TNS best 809467 last 809467 rows 1 | YOUNG: evidence 1.8 h < 2.5 h |  |
| epyc8 | dpkit-kv3_pv_v3n-3977907 | kv3_pv_v3n | 3_5_place_dp | 1.7 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | eco-abs-469861 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.1 h ago (29/29 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | otc-132122-8685 | 132122 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc8 | otc-3678186-167 | 3678186 | - | 5.5 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_091937_4000900-i1-378808 | eco_20261125_091937_4000900-i1 | 5_2_route | 2.9 | drt_violations best 16 last 16 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_104318_3955073-i1t-474220 | eco_20261125_104318_3955073-i1t | 5_2_route | 1.5 | last meaningful line 0.0 h ago (257/257 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_110931_3969969-i1-1922478 | eco_20261125_110931_3969969-i1 | 5_2_route | 1.1 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_120022_4021525-i1-420704 | eco_20261125_120022_4021525-i1 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (143/143 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | relec-r2-U1_hc3_pv39aac7a1 | relec-r2-U1_hc3_pv39aac7a1 | - | 2.0 |  | NO-DATA: no log found |  |
| epyc8 | so_2538522_ff_61132 | so_2538522_ff_61132 | signoff | 0.9 |  | NO-DATA: empty log |  |
| epyc8 | so_2538522_tt_61132 | so_2538522_tt_61132 | signoff | 0.9 |  | NO-DATA: empty log |  |
| epyc8 | so_260353_ff_83997 | so_260353_ff_83997 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (33/33 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | so_260353_tt_83997 | so_260353_tt_83997 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (33/33 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | so_2850906_ff_7710 | so_2850906_ff_7710 | signoff | 0.8 |  | NO-DATA: empty log |  |
| epyc8 | so_2850906_tt_7710 | so_2850906_tt_7710 | signoff | 0.8 |  | NO-DATA: empty log |  |
| epyc8 | so_2955095_ff_78989 | so_2955095_ff_78989 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | so_2955095_tt_78989 | so_2955095_tt_78989 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | so_2990013_ff_70537 | so_2990013_ff_70537 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc8 | so_2990013_tt_70537 | so_2990013_tt_70537 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t54--cl706d9749-grt-2242274 | ot-s81sl-leaf--t54--cl706d9749-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | pregrt_ff_hold | 5.5 | repair_TNS best 127105 last 127105 rows 1 | YOUNG: evidence 2.1 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3698869 | col_h9_r0_p4__t1 | pregrt_ff_hold | 3.4 | repair_TNS best 47200.4 last 47200.4 rows 1 | YOUNG: evidence 1.8 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_1_grt | 5.5 | last meaningful line 0.0 h ago (162/162 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | lec | 2.7 | LEC last write 0.2 h ago | YOUNG: evidence 2.7 h < 6 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pvf1445dce-2628247 | col_h9_r2__t1 | pregrt_ff_hold | 2.1 | repair_TNS best 1867.28 last 1867.28 rows 1 | YOUNG: evidence 1.4 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv31e47bd5-4047516 | col_h9_r2__t1 | 5_1_grt | 2.7 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 7.4 | drt_violations best 38346 last 38346 rows 2 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-3394850 | col_h9_r2__t1 | 5_2_route | 5.6 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-3707756 | col_h9_r2__t1 | 5_2_route | 5.5 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve0486b40-3725060 | col_h9_r2__t1 | tt_setup_measure_grt | 3.4 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | 5_2_route | 6.5 | drt_violations best 163283 last 163283 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t10-3695203 | dsdv_slice_c1x_C__t10 | lec | 4.5 | LEC last write 0.2 h ago | YOUNG: evidence 4.5 h < 6 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t8-578982 | dsdv_slice_c1x_C__t8 | 3_5_place_dp | 4.4 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-3691225 | dsdv_slice_c1x_C__t9 | lec | 4.5 | LEC last write 0.3 h ago | YOUNG: evidence 4.5 h < 6 h |  |
| epyc9 | dpkit-dsdv_slice_kv512_C__t1-4058196 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 2.7 | last meaningful line 0.3 h ago (37/37 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-3479533 | slice_station__t37 | postcts_gate_TT | 3.4 | last meaningful line 0.0 h ago (1272/1272 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t42__clcf44e680-3472830 | slice_station__t42 | 5_2_route | 3.4 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t43-3486441 | slice_station__t43 | postcts_gate_FF | 3.4 | last meaningful line 0.0 h ago (685/685 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-2620358 | slice_station__t52 | 5_1_grt | 2.2 | last meaningful line 0.2 h ago (269/645 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | prd-count-p1_tc-787277 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | ap-ageom-kw-col-h9-r1--t1--clf32cde8d--pv63f488e9-grt-894859 | col-h9-r1--t1--clf32cde8d--pv63f488e9-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-559858 | col_h10_r0_p4__t1 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1177242 | kv3_hg_v1p3__r838481cd7 | 5_1_grt | 4.6 | last meaningful line 0.1 h ago (288/289 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_sys_c-4063347 | kv3_sys_c | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (5389/5389 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-serdes__t15__cla3d02796-2608833 | serdes__t15 | 3_4_place_resized | 2.3 | repair_Remaining best 113388 last 113388 rows 277 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | postcts_gate_FF | 11.2 | last meaningful line 0.3 h ago (373/373 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 5_2_route | 15.5 | last meaningful line 0.5 h ago (281/282 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t27-4040446 | slice_station__t27 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (3381/3381 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t30__cl1653104c-2603170 | slice_station__t30 | 5_2_route | 1.4 | last meaningful line 0.2 h ago (229/230 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | postcts_gate_TT | 12.9 | last meaningful line 0.3 h ago (1799/1799 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 5_2_route | 14.0 | drt_violations best 174940 last 174940 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 5_2_route | 15.2 | drt_violations best 104717 last 104717 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | postcts_gate_FF | 13.7 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | eco-abs-848076 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-3504566-18256 | 3504566 | flow | 1.3 | last meaningful line 0.0 h ago (2913/2913 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i3t-2681077 | eco_20261123_191853_2879776-i3t | 5_1_grt | 1.4 | last meaningful line 0.3 h ago (237/404 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1t-3347319 | eco_20261125_002226_1452841-i1t | 5_2_route | 3.8 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | prd-eco_20261125_020407_3088231-i1-2998029 | eco_20261125_020407_3088231-i1 | 5_2_route | 2.1 | last meaningful line 0.1 h ago (255/256 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | prd-eco_20261125_040243_2843749-i1-851245 | eco_20261125_040243_2843749-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | so_553427_ff_253 | so_553427_ff_253 | signoff | 0.3 |  | NO-DATA: empty log |  |
| intel1 | so_553427_tt_253 | so_553427_tt_253 | signoff | 0.3 |  | NO-DATA: empty log |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-2390236 | slw_st_b_v1 | 6_report | 11.6 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | otc-594090-20209 | 594090 | eq13_out | 3.0 | last meaningful line 0.0 h ago (706756/706756 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-1955823 | kv3_hgi | 5_1_grt | 2.4 |  | KEEP: kv3_hgi_1124155644	KV-OWN-RSTREACH	combined HEADLEG2+HGI-LEAF ship form; noprog  |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-436421 | kv3_hgi_v2 | 5_1_grt | 2.7 |  | KEEP: kv3_hgi_v2__cl2862d491_1124155702	KV-OWN-RSTREACH	combined hgi_v2 ship form (COO |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pvb2cd22a7-3043152 | col_h9_r2__t1 | pregrt_ff_hold | 1.3 |  | KEEP: col_h9_r2__t1__clb8d86cd5__pvb2cd22a7	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-eco_qcgu_1125-i1-3514577 | eco_qcgu_1125-i1 | 5_2_route | 3.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_2_route | 18.5 | drt_violations best 152884 last 152884 rows 2 | before-window best 416066, window best 152884 | PROGRESS: drt_violations improved 63.3 % in window |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 17.4 | drt_violations best 6946 last 6946 rows 10 | before-window best 272423, window best 6946 | PROGRESS: drt_violations improved 97.5 % in window |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_2_route | 17.4 | drt_violations best 378938 last 378938 rows 1 | before-window best 378938, window best 378938 | PROGRESS: drt_violations: active iteration at 171965 < best completed total 378938 (in-ite |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 18.7 | drt_violations best 840 last 840 rows 13 | before-window best 329677, window best 840 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 23.5 | drt_violations best 6215 last 33693 rows 18 | before-window best 8379, window best 6215 | PROGRESS: drt_violations improved 25.8 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 43.9 | drt_violations best 5300 last 5300 rows 23 | before-window best 7726, window best 5300 | PROGRESS: drt_violations improved 31.4 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 28.6 | drt_violations best 2761 last 13398 rows 18 | before-window best 2937, window best 2761 | PROGRESS: drt_violations improved 6.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_1_grt | 2.7 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 24.8 | drt_violations best 6306 last 6306 rows 13 | before-window best 15295, window best 6306 | PROGRESS: drt_violations improved 58.8 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 23.4 | drt_violations best 18111 last 18111 rows 10 | before-window best 122131, window best 18111 | PROGRESS: drt_violations improved 85.2 % in window |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 5_2_route | 18.8 | drt_violations best 68573 last 68573 rows 7 | before-window best 136685, window best 68573 | PROGRESS: drt_violations improved 49.8 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 23.2 | drt_violations best 7754 last 7754 rows 12 | before-window best 106839, window best 7754 | PROGRESS: drt_violations improved 92.7 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-534954 | slw_su_l1 | tt_setup_repair_grt | 5.4 | repair_Violations best 0 last 0 rows 46 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_2_route | 20.1 | drt_violations best 59399 last 59399 rows 3 | before-window best 320246, window best 59399 | PROGRESS: drt_violations improved 81.5 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 20.1 | drt_violations best 26244 last 26244 rows 8 | before-window best 478667, window best 26244 | PROGRESS: drt_violations improved 94.5 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 20.1 | drt_violations best 65063 last 65063 rows 2 | before-window best 266434, window best 65063 | PROGRESS: drt_violations improved 75.6 % in window |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 20.1 | drt_violations best 18428 last 18428 rows 6 | before-window best 450083, window best 18428 | PROGRESS: drt_violations improved 95.9 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 20.1 | drt_violations best 8519 last 40739 rows 18 | before-window best 11145, window best 8519 | PROGRESS: drt_violations improved 23.6 % in window |  |
| epyc8 | prd-eco_20261125_114101_3990791-i1-3640861 | eco_20261125_114101_3990791-i1 | 5_1_grt | 0.5 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc8 | prd-eco_20261125_114445_3946237-i1-3788521 | eco_20261125_114445_3946237-i1 | 5_1_grt | 0.5 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pv07945c1e-55623 | col_h10_r0_p4__t1 | 5_1_grt | 6.0 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | pregrt_ff_hold | 5.5 | repair_Violations best 53771 last 53771 rows 8 | before-window best 210376, window best 53771 | PROGRESS: repair_Violations improved 74.4 % in window |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-296584 | col_h9_r0_p3__t1 | lec | 8.1 | LEC last write 0.1 h ago | PROGRESS: LEC still writing |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-3032686 | col_h9_r0_p4__t1 | 4_2_tapbal_grt | 1.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-4053150 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.7 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_2_route | 17.0 | drt_violations best 45768 last 45768 rows 9 | before-window best 474459, window best 45768 | PROGRESS: drt_violations improved 90.4 % in window |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 17.2 | drt_violations best 6 last 6 rows 43 | before-window best 274895, window best 6 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 5_2_route | 23.5 | drt_violations best 76432 last 76432 rows 2 | before-window best 317907, window best 76432 | PROGRESS: drt_violations improved 76.0 % in window |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 5_2_route | 19.1 | drt_violations best 106 last 106 rows 8 | before-window best 163425, window best 106 | PROGRESS: drt_violations improved 99.9 % in window |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 15.4 | drt_violations best 1 last 1 rows 39 | before-window best 2947, window best 1 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 23.4 | drt_violations best 11640 last 11640 rows 5 | before-window best 398476, window best 11640 | PROGRESS: drt_violations improved 97.1 % in window |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 5_2_route | 19.1 | drt_violations best 13753 last 13753 rows 3 | before-window best 138053, window best 13753 | PROGRESS: drt_violations improved 90.0 % in window |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 18.6 | drt_violations best 2586 last 2586 rows 13 | before-window best 367946, window best 2586 | PROGRESS: drt_violations improved 99.3 % in window |  |
