# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 06:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'GRT-LABEL': 10, 'YOUNG': 172, 'NO-DATA': 29, 'KEEP': 3, 'EXCLUDED': 1, 'PROGRESS': 28}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc8 | dpkit-kv3_hg_v1p5-3496343 | kv3_hg_v1p5 | pregrt_ff_hold | 3.8 | repair_TNS best 809467 last 809467 rows 1 | before-window best 809467, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-D29 decides; never a |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8c9cba7ae-3297443 | kv3_pc_v1 | 5_1_grt | 3.9 | grt rounds 2 overflow 5:24385 -> 10:14707 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv-3805339 | kv3_pv | 5_1_grt | 1.9 | grt rounds 2 overflow 5:55206 -> 10:46293 | GRT-LABEL: DESIGN-FAIL: overflow 46293 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v2-1828900 | kv3_pv_v2 | 5_1_grt | 0.5 | grt rounds 2 overflow 5:63965 -> 10:48975 | GRT-LABEL: DESIGN-FAIL: overflow 48975 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v3e-640390 | kv3_pv_v3e | 5_1_grt | 1.1 | grt rounds 2 overflow 5:86034 -> 10:53939 | GRT-LABEL: DESIGN-FAIL: overflow 53939 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v4n-2809393 | kv3_pv_v4n | 5_1_grt | 2.1 | grt rounds 2 overflow 5:24020 -> 10:16743 | GRT-LABEL: DESIGN-FAIL: overflow 16743 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | 5_1_grt | 16.6 | grt rounds 1 overflow 5:74746 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc11 | dpkit-kv3_pv_v6n-721471 | kv3_pv_v6n | 5_1_grt | 1.1 | grt rounds 2 overflow 5:45246 -> 10:35967 | GRT-LABEL: DESIGN-FAIL: overflow 35967 at round 10 > 1000 |  |
| epyc11 | dpkit-slw_su_c__cl92142dac-2960548 | slw_su_c | 5_1_grt | 7.3 | grt rounds 2 overflow 5:21500 -> 10:14785 | GRT-LABEL: DESIGN-FAIL: overflow 14785 at round 10 > 1000 |  |
| epyc7 | dpkit-cbf_q00_s2-3518685 | cbf_q00_s2 | 5_1_grt | 7.9 | grt rounds 2 overflow 5:87022 -> 10:54031 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 5_1_grt | 13.6 | grt rounds 2 overflow 5:17977 -> 10:2858 | GRT-LABEL: DESIGN-FAIL: overflow 2858 at round 10 > 1000 |  |
| epyc10 | dpkit-hd_lep0N_w-3160116 | hd_lep0N_w | 5_2_route | 4.0 | drt_violations best 115480 last 115480 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p5-970860 | kv3_hg_v1p5 | 5_1_grt | 4.6 | last meaningful line 0.5 h ago (306/1310 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | 5_1_grt | 12.8 | last meaningful line 0.2 h ago (2217/2230 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-103808 | kv3_pc_v1 | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (6616/6616 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r877307f5d-1492582 | kv3_pc_v1 | postcts_gate_TT | 4.5 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl7f648944__r8e7d31598-4153558 | kv3_pc_v1 | 4_1_cts | 1.7 | last meaningful line 0.0 h ago (6760/6760 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-native59-3384403 | native59 | 5_2_route | 11.7 | last meaningful line 0.2 h ago (263/264 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 5_2_route | 19.5 | drt_violations best 19624 last 19624 rows 3 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | 5_2_route | 18.1 | drt_violations best 19543 last 19543 rows 2 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2082061 | slw_st_a_v1 | 5_2_route | 4.4 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | otc-1191841-12698 | 1191841 | signoff | 3.1 | last meaningful line 3.0 h ago (3/3 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | otc-1471300-23748 | 1471300 | signoff | 3.0 | last meaningful line 2.8 h ago (3/3 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc10 | otc-1762308-21603 | 1762308 | signoff | 2.9 | last meaningful line 2.8 h ago (3/3 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | otc-2025541-6828 | 2025541 | signoff | 0.8 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | otc-2424957-5022 | 2424957 | signoff | 0.6 | last meaningful line 0.5 h ago (3/3 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_073109_4058437-i1-634237 | eco_20261125_073109_4058437-i1 | 5_1_grt | 1.4 | last meaningful line 0.8 h ago (296/438 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_112234_1159095-i1-1820297 | eco_20261125_112234_1159095-i1 | 5_2_route | 2.8 | drt_violations best 10 last 10 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc11 | dpkit-cbn_q00__cl622f65d2-2378800 | cbn_q00 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-hd_lep0N-2184208 | hd_lep0N | pregrt_ff_hold | 0.3 | repair_TNS best 2802.88 last 2802.88 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-kv3_hg_v3-561930 | kv3_hg_v3 | pregrt_ff_hold | 1.2 | repair_Violations best 811 last 848 rows 32 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc11 | dpkit-kv3_hub_Eo-871015 | kv3_hub_Eo | 3_3_place_gp | 1.0 | overflow best 0.6753 last 0.6753 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-kv3_hub_Wo-954396 | kv3_hub_Wo | 3_3_place_gp | 0.9 | last meaningful line 0.1 h ago (67/67 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v5-1052229 | kv3_pv_v5 | 5_1_grt | 4.9 | last meaningful line 0.2 h ago (158/158 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v5n-798731 | kv3_pv_v5n | lec | 1.0 | LEC last write 0.4 h ago | YOUNG: evidence 1.0 h < 6 h |  |
| epyc11 | dpkit-kv3_pv_v8-2209532 | kv3_pv_v8 | pregrt_ff_hold | 0.3 | repair_Violations best 4 last 4 rows 8 | YOUNG: stage 0.3 h < 1 h |  |
| epyc11 | dpkit-kv3_pv_v8e-579863 | kv3_pv_v8e | lec | 1.2 | LEC last write 0.1 h ago | YOUNG: evidence 1.2 h < 6 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | generate_abstract | 16.0 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_su_c-2485454 | sle_su_c | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (96/96 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | 5_2_route | 11.0 | drt_violations best 141406 last 141406 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl19bb38ef-959635 | slw_su_c | 3_3_place_gp | 0.9 | overflow best 0.0995 last 0.0995 rows 48 | YOUNG: stage 0.7 h < 1 h |  |
| epyc11 | eco-abs-2120635 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.1 h ago (31/31 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | otc-141162-25188 | 141162 | lec | 3.3 | LEC last write 3.3 h ago | YOUNG: evidence 3.3 h < 6 h |  |
| epyc11 | otc-1616228-26288 | 1616228 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc11 | otc-1830932-23851 | 1830932 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc11 | otc-3124125-30954 | 3124125 | - | 1.9 |  | NO-DATA: no log found |  |
| epyc11 | otc-381902-2867 | 381902 | - | 5.2 |  | NO-DATA: no log found |  |
| epyc11 | prd-count-p1_tc-1256057 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | prd-count-p1_tc-2211039 | count-p1_tc | prd_count_p1_tc | 0.2 | last meaningful line 0.1 h ago (1051/1051 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i2t-2255468 | eco_20261124_190641_1260390-i2t | 5_2_route | 4.3 | drt_violations best 5541 last 5541 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i2t-96653 | eco_20261124_200101_1087713-i2t | 5_2_route | 3.3 | last meaningful line 0.1 h ago (284/285 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_120946_3832190-i1t-2887287 | eco_20261125_120946_3832190-i1t | 5_2_route | 2.1 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc11 | prd-fin-3146788 | fin | 6_report | 0.4 | last meaningful line 0.1 h ago (77/77 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | so_1143382_ff_25251 | so_1143382_ff_25251 | signoff | 0.9 |  | NO-DATA: empty log |  |
| epyc12 | dpkit-hd_lep0N-2152952 | hd_lep0N | 4_2_tapbal_grt | 3.7 | last meaningful line 2.3 h ago (48/52 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc12 | dpkit-kv3_hgi_v7-2529031 | kv3_hgi_v7 | 5_1_grt | 3.5 | last meaningful line 0.8 h ago (295/1301 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-4135984 | kv3_pc | 3_3_place_gp | 0.9 | overflow best 0.7674 last 0.7783 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl4ea58a5c__r877307f5d-3969743 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.9 | overflow best 0.1474 last 0.1474 rows 45 | YOUNG: stage 0.4 h < 1 h |  |
| epyc12 | dpkit-kv3_pv_v12-2339543 | kv3_pv_v12 | 5_1_grt | 3.6 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | dpkit-sle_st_a_v1__cl67389ecd-849428 | sle_st_a_v1 | postcts_gate_TT | 2.2 | last meaningful line -0.0 h ago (9100/9100 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc12 | dpkit-slw_st_a_v2__clf4365a62-2414803 | slw_st_a_v2 | 5_2_route | 3.6 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | dpkit-slw_st_a_v2__clf4365a62-3737452 | slw_st_a_v2 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (6507/6507 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 2.9 |  | NO-DATA: no log found |  |
| epyc12 | leccsp-pA | leccsp-pA | - | 0.1 |  | NO-DATA: no log found |  |
| epyc12 | otc-1273822-29690 | 1273822 | drc_parent_only | 0.4 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | otc-1275997-12067 | 1275997 | drc_parent_only | 0.4 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | otc-1278426-9051 | 1278426 | drc_macros_only | 0.4 | last meaningful line 0.0 h ago (194/194 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | otc-1291490-1984 | 1291490 | drc_merged | 0.4 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | otc-1294027-30241 | 1294027 | drc_macros_only | 0.4 | last meaningful line 0.0 h ago (188/188 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | otc-1305696-4661 | 1305696 | drc_macros_only | 0.4 | last meaningful line 0.0 h ago (194/194 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | otc-1308959-15081 | 1308959 | drc_macros_only | 0.4 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | otc-1312023-14782 | 1312023 | drc_parent_only | 0.4 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | otc-1314683-28749 | 1314683 | drc_macros_only | 0.4 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | otc-1319124-12976 | 1319124 | drc_macros_only | 0.4 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | otc-1321394-11555 | 1321394 | drc_macros_only | 0.4 | last meaningful line 0.0 h ago (161/161 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | otc-1324644-27944 | 1324644 | drc_parent_only | 0.4 | last meaningful line 0.0 h ago (176/176 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | otc-1338915-16694 | 1338915 | drc_macros_only | 0.4 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | otc-1380654-9644 | 1380654 | asbuilt.yosys | 0.3 | last meaningful line -0.0 h ago (135523/135523 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | otc-1460135-77 | 1460135 | - | 2.0 |  | NO-DATA: no log found |  |
| epyc12 | otc-1467770-21234 | 1467770 | asbuilt.yosys | 0.3 | last meaningful line -0.0 h ago (135842/135842 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | otc-1994529-22240 | 1994529 | flow | 0.0 | last meaningful line -0.0 h ago (318/318 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | otc-1995249-22339 | 1995249 | flow | 0.0 | last meaningful line -0.0 h ago (304/304 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | otc-3293317-27322 | 3293317 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc12 | otc-3501458-13012 | 3501458 | drc_merged | 2.9 | last meaningful line 0.1 h ago (313/313 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc12 | otc-351743-16220 | 351743 | hcpg_run | 0.7 | last meaningful line 0.3 h ago (13/13 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Wi-3068909 | kv3_hub_Wi | 3_3_place_gp | 2.4 | overflow best 0.2095 last 0.2095 rows 43 | YOUNG: stage 0.8 h < 1 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 4.5 | drt_violations best 34998 last 34998 rows 2 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-3286653 | sle_st_a_v2 | 5_2_route | 4.5 | drt_violations best 31 last 31 rows 14 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2601551 | slw_st_a_v1 | 5_2_route | 4.8 | drt_violations best 4283 last 4283 rows 4 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | otc-2770137-14837 | 2770137 | signoff | 0.4 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_204708_4151707-i2t-1352759 | eco_20261124_204708_4151707-i2t | 5_2_route | 1.2 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 0.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 0.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 0.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-A | qcdrt-sc-A | - | 0.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-B | qcdrt-sc-B | - | 0.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-C | qcdrt-sc-C | - | 0.7 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-coll_core-3493022 | coll_core | 5_1_grt | 4.7 | last meaningful line 0.2 h ago (260/580 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t2-3977371 | serdes__t2 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.937 last 0.9497 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (10800/10800 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4983/4984 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | postcts_gate_TT | 7.9 | last meaningful line 0.2 h ago (380/380 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | postcts_gate_FF | 4.7 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | tt_setup_repair_grt | 4.7 | last meaningful line 0.0 h ago (696/696 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3817081 | sle_st_a_v2 | 5_2_route | 6.2 | drt_violations best 1506 last 1506 rows 4 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__clc6d66f5b-2521917 | sle_su_l1 | 5_2_route | 5.2 | last meaningful line 0.4 h ago (269/270 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | postcts_gate_FF | 5.1 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 7.8 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-3807127 | slw_su_l1 | 5_2_route | 7.8 | drt_violations best 78889 last 78889 rows 3 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc7 | eco-abs-718120 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.3 h ago (29/29 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | otc-2916017-13620 | 2916017 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc7 | otc-2938337-22499 | 2938337 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc7 | otc-2958007-4014 | 2958007 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc7 | otc-593045-3980 | 593045 | drc_parent_only | 0.4 | last meaningful line 0.0 h ago (614/614 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | otc-596415-29356 | 596415 | drc_merged | 0.4 | last meaningful line 0.0 h ago (506/506 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | otc-740568-7161 | 740568 | drc_macros_only | 0.3 | last meaningful line 0.0 h ago (176/176 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | otc-830728-15409 | 830728 | drc_merged | 0.3 | last meaningful line 0.0 h ago (107/107 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | otc-831702-28906 | 831702 | drc_merged | 0.3 | last meaningful line 0.0 h ago (107/107 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | otc-833865-16155 | 833865 | drc_merged | 0.3 | last meaningful line 0.0 h ago (107/107 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | otc-835730-18044 | 835730 | drc_parent_only | 0.3 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | otc-838804-29233 | 838804 | drc_merged | 0.3 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i2-1995832 | eco_20261124_192157_3493836-i2 | 5_2_route | 1.6 | last meaningful line 0.2 h ago (262/263 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_073945_2252980-i1-3230821 | eco_20261125_073945_2252980-i1 | 5_2_route | 2.9 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_094206_1890550-i1-4068402 | eco_20261125_094206_1890550-i1 | 5_2_route | 4.5 | drt_violations best 65 last 65 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_103149_2129512-i1-1443376 | eco_20261125_103149_2129512-i1 | 5_2_route | 3.7 | drt_violations best 36 last 36 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_110124_1979736-i1-2551803 | eco_20261125_110124_1979736-i1 | 5_2_route | 3.2 | drt_violations best 265 last 265 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | so_907831_ff_40346 | so_907831_ff_40346 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (35/35 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | so_907831_tt_40346 | so_907831_tt_40346 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (35/35 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-918588 | col_h10_r0_p1__t1 | 4_2_tapbal_grt | 2.0 | last meaningful line 0.0 h ago (102/102 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_mu_C__t1-730122 | dsdv_slice_lepe_mu_C__t1 | 1_1_yosys_canonicalize | 2.1 | last meaningful line 0.7 h ago (131/131 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v3n-2522162 | kv3_pv_v3n | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (8621/8621 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | eco-abs-2624464 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.1 h ago (29/29 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-132122-8685 | 132122 | - | 2.3 |  | NO-DATA: no log found |  |
| epyc8 | otc-1321249-29104 | 1321249 | - | 1.9 |  | NO-DATA: no log found |  |
| epyc8 | prd-count-p1_tc-1922478 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_025941_3548303-i2t-3977758 | eco_20261125_025941_3548303-i2t | 5_2_route | 1.1 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_082653_3900765-i2-3480940 | eco_20261125_082653_3900765-i2 | 5_2_route | 1.3 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_114101_3990791-i1-3640861 | eco_20261125_114101_3990791-i1 | 5_2_route | 2.5 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_114445_3946237-i1-3788521 | eco_20261125_114445_3946237-i1 | 5_2_route | 2.5 | drt_violations best 19 last 19 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_120022_4021525-i1-420704 | eco_20261125_120022_4021525-i1 | 5_2_route | 2.2 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_121517_3981660-i1-1143996 | eco_20261125_121517_3981660-i1 | 5_2_route | 2.0 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_122258_3982108-i1-1582033 | eco_20261125_122258_3982108-i1 | 5_2_route | 1.8 | last meaningful line 0.0 h ago (265/265 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_123046_4033426-i1-1985482 | eco_20261125_123046_4033426-i1 | 5_2_route | 1.7 | last meaningful line 0.0 h ago (262/263 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_123952_3914547-i1-2528575 | eco_20261125_123952_3914547-i1 | 5_2_route | 1.5 | last meaningful line 0.0 h ago (259/259 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | prd-fin-474220 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 5_1_grt | 7.5 | last meaningful line 1.2 h ago (269/1289 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3698869 | col_h9_r0_p4__t1 | 5_1_grt | 5.4 | repair_Remaining best 198488 last 198488 rows 30 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-3032686 | col_h9_r0_p4__t1 | pregrt_ff_hold | 3.3 | repair_TNS best 46921.2 last 46921.2 rows 1 | YOUNG: evidence 1.7 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 7.5 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_1_grt | 4.7 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-4053150 | col_h9_r1__t1 | pregrt_ff_hold | 4.7 | repair_TNS best 53812.2 last 53812.2 rows 1 | YOUNG: evidence 1.6 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pvf1445dce-2628247 | col_h9_r2__t1 | postcts_gate_FF | 4.1 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv31e47bd5-4047516 | col_h9_r2__t1 | lec | 4.7 | LEC last write 0.0 h ago | YOUNG: evidence 4.7 h < 6 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-3394850 | col_h9_r2__t1 | 5_2_route | 7.6 | drt_violations best 157585 last 157585 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-3707756 | col_h9_r2__t1 | 5_2_route | 7.5 | drt_violations best 35024 last 35024 rows 2 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve0486b40-3725060 | col_h9_r2__t1 | 5_2_route | 5.4 | last meaningful line 0.4 h ago (278/279 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | 5_2_route | 8.5 | drt_violations best 3658 last 3658 rows 8 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t7-3863913 | dsdv_slice_c1x_C__t7 | 1_1_yosys_canonicalize | 1.8 | last meaningful line 0.5 h ago (130/130 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_kv512_C__t1-4058196 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 4.7 | last meaningful line 2.3 h ago (37/37 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t26-2443746 | ot_s81sl_leaf__t26 | 3_3_place_gp | 0.4 | last meaningful line 0.1 h ago (284/284 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-3479533 | slice_station__t37 | lec | 5.4 | LEC last write 0.0 h ago | YOUNG: evidence 5.4 h < 6 h |  |
| epyc9 | dpkit-slice_station__t42__clcf44e680-3472830 | slice_station__t42 | 6_report | 5.4 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t43-3486441 | slice_station__t43 | lec | 5.4 | LEC last write 0.0 h ago | YOUNG: evidence 5.4 h < 6 h |  |
| epyc9 | dpkit-slice_station__t44-2657480 | slice_station__t44 | tt_setup_repair | 0.4 | last meaningful line 0.0 h ago (166/167 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-2620358 | slice_station__t52 | 5_2_route | 4.2 | last meaningful line 0.1 h ago (251/251 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | so_215815_ff_77208 | so_215815_ff_77208 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | so_215815_tt_77208 | so_215815_tt_77208 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | so_2848329_ff_36721 | so_2848329_ff_36721 | generate_abstract | 1.2 | last meaningful line 1.0 h ago (33/33 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | so_2848329_tt_36721 | so_2848329_tt_36721 | generate_abstract | 1.2 | last meaningful line 1.0 h ago (33/33 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2686622 | col_h10_r0_p4__t1 | 4_2_tapbal_grt | 1.4 | last meaningful line 0.5 h ago (63/72 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 4_2_tapbal_grt | 1.4 | last meaningful line 0.5 h ago (63/72 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.3 | last meaningful line 0.5 h ago (61/70 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.2 | last meaningful line 0.5 h ago (61/70 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.4 | last meaningful line 0.5 h ago (61/72 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 63490.2 last 63490.2 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 51207.7 last 51207.7 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 60746.9 last 60746.9 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-2360794 | col_h9_r2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 118766 last 118766 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pva119e808-2308652 | col_h9_r2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 79800.3 last 79800.3 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1177242 | kv3_hg_v1p3__r838481cd7 | 5_1_grt | 6.6 | last meaningful line 2.0 h ago (288/1296 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_sys_c-4063347 | kv3_sys_c | 5_1_grt | 3.2 | last meaningful line 0.2 h ago (1262/2267 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 5_2_route | 13.2 | last meaningful line 0.1 h ago (262/262 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 5_2_route | 17.5 | drt_violations best 138407 last 138407 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t27-4040446 | slice_station__t27 | postcts_gate_TT | 3.2 | last meaningful line 0.0 h ago (603/603 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 14.9 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 6_report | 17.2 | last meaningful line 0.1 h ago (68/68 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 5_2_route | 15.7 | last meaningful line 0.0 h ago (255/255 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | otc-3504566-18256 | 3504566 | flow | 3.3 | last meaningful line 0.1 h ago (3199/3199 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | otc-394619-19736 | 394619 | - | 0.5 |  | NO-DATA: no log found |  |
| intel1 | otc-395802-17368 | 395802 | - | 0.5 |  | NO-DATA: no log found |  |
| intel1 | otc-396637-17834 | 396637 | - | 0.5 |  | NO-DATA: no log found |  |
| intel1 | otc-574655-9239 | 574655 | drc_parent_only | 0.4 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-578793-24959 | 578793 | drc_merged | 0.4 | last meaningful line 0.0 h ago (91/91 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-582965-3828 | 582965 | drc_merged | 0.4 | last meaningful line 0.0 h ago (107/107 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-586189-14994 | 586189 | drc_parent_only | 0.4 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-589045-16647 | 589045 | drc_merged | 0.4 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-591807-6566 | 591807 | drc_macros_only | 0.4 | last meaningful line 0.0 h ago (365/365 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i3t-2681077 | eco_20261123_191853_2879776-i3t | 5_2_route | 3.4 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1t-3347319 | eco_20261125_002226_1452841-i1t | 5_2_route | 5.8 | drt_violations best 9407 last 9407 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | prd-eco_20261125_040243_2843749-i1-851245 | eco_20261125_040243_2843749-i1 | 5_2_route | 2.1 | last meaningful line 0.0 h ago (258/258 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i1-3109373 | eco_20261125_050013_1448739-i1 | 5_1_grt | 1.2 | last meaningful line 0.5 h ago (294/381 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | prd-fin-2998029 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (67/67 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | so_445807_ff_5944 | so_445807_ff_5944 | signoff | 0.4 |  | NO-DATA: empty log |  |
| intel1 | so_445807_tt_5944 | so_445807_tt_5944 | signoff | 0.4 |  | NO-DATA: empty log |  |
| intel1 | so_78775_ff_69145 | so_78775_ff_69145 | signoff | 0.7 |  | NO-DATA: empty log |  |
| intel1 | so_78775_tt_69145 | so_78775_tt_69145 | signoff | 0.7 |  | NO-DATA: empty log |  |
| intel2 | dpkit-coll_ftm-2001265 | coll_ftm | 5_2_route | 1.7 | drt_violations best 10294 last 10294 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | dpkit-hd_serdes-3275033 | hd_serdes | 4_2_tapbal_grt | 0.9 | last meaningful line 0.3 h ago (48/103 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-2473436 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v12e-1190106 | kv3_pv_v12e | 3_1_place_gp_skip_io | 0.5 | overflow best 0.2645 last 0.2645 rows 35 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-kv3_pv_v6e-3555492 | kv3_pv_v6e | 3_4_place_resized | 0.8 | last meaningful line 0.1 h ago (271/271 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | otc-2407048-21046 | 2407048 | signoff | 1.0 | last meaningful line 1.0 h ago (3/3 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-1955823 | kv3_hgi | 5_2_route | 4.4 |  | KEEP: kv3_hgi_1124155644	KV-OWN-RSTREACH	combined HEADLEG2+HGI-LEAF ship form; noprog  |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-436421 | kv3_hgi_v2 | 5_1_grt | 4.7 |  | KEEP: kv3_hgi_v2__cl2862d491_1124155702	KV-OWN-RSTREACH	combined hgi_v2 ship form (COO |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pvb2cd22a7-3043152 | col_h9_r2__t1 | 5_1_grt | 3.3 |  | KEEP: col_h9_r2__t1__clb8d86cd5__pvb2cd22a7	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-count-p1_tc-3514577 | count-p1_tc | prd_count_p1_tc | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-kv3_hgi_v4-4881 | kv3_hgi_v4 | pregrt_ff_hold | 1.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_2_route | 20.5 | drt_violations best 70805 last 70805 rows 4 | before-window best 416066, window best 70805 | PROGRESS: drt_violations improved 83.0 % in window |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 19.4 | drt_violations best 958 last 958 rows 17 | before-window best 272423, window best 958 | PROGRESS: drt_violations improved 99.6 % in window |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_2_route | 19.4 | drt_violations best 81665 last 81665 rows 3 | before-window best 378938, window best 81665 | PROGRESS: drt_violations improved 78.4 % in window |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 20.7 | drt_violations best 71 last 71 rows 22 | before-window best 329677, window best 71 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc12 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1520876 | col_h10_r0_p4__t1 | 5_1_grt | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 25.5 | drt_violations best 6215 last 33693 rows 18 | before-window best 7058, window best 6215 | PROGRESS: drt_violations improved 11.9 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 30.6 | drt_violations best 2761 last 5839 rows 19 | before-window best 2818, window best 2761 | PROGRESS: drt_violations improved 2.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 26.8 | drt_violations best 5691 last 5691 rows 14 | before-window best 11325, window best 5691 | PROGRESS: drt_violations improved 49.7 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 25.4 | drt_violations best 12935 last 12935 rows 12 | before-window best 29127, window best 12935 | PROGRESS: drt_violations improved 55.6 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 25.2 | drt_violations best 7139 last 7139 rows 13 | before-window best 17648, window best 7139 | PROGRESS: drt_violations improved 59.5 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-534954 | slw_su_l1 | tt_setup_repair_grt | 7.4 | repair_Violations best 0 last 0 rows 46 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_2_route | 22.1 | drt_violations best 533 last 533 rows 14 | before-window best 320246, window best 533 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 22.1 | drt_violations best 23437 last 23437 rows 10 | before-window best 93397, window best 23437 | PROGRESS: drt_violations improved 74.9 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 22.1 | drt_violations best 703 last 703 rows 13 | before-window best 266434, window best 703 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 22.1 | drt_violations best 8974 last 8974 rows 11 | before-window best 450083, window best 8974 | PROGRESS: drt_violations improved 98.0 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 22.1 | drt_violations best 8519 last 40739 rows 18 | before-window best 9525, window best 8519 | PROGRESS: drt_violations improved 10.6 % in window |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | pregrt_ff_hold | 7.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-296584 | col_h9_r0_p3__t1 | lec | 10.1 | LEC last write 0.0 h ago | PROGRESS: LEC still writing |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | lec | 9.4 | LEC last write 0.0 h ago | PROGRESS: LEC still writing |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvfd79e8b6-2442139 | col_h9_r2__t1 | 3_5_place_dp | 0.4 | repair_Violations best 0 last 0 rows 26 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_2_route | 19.0 | drt_violations best 36163 last 36163 rows 11 | before-window best 125492, window best 36163 | PROGRESS: drt_violations improved 71.2 % in window |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 19.2 | drt_violations best 4 last 4 rows 53 | before-window best 10533, window best 4 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 17.4 | drt_violations best 1 last 1 rows 40 | before-window best 39, window best 1 | PROGRESS: drt_violations improved 97.4 % in window |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 25.4 | drt_violations best 7704 last 7704 rows 9 | before-window best 104690, window best 7704 | PROGRESS: drt_violations improved 92.6 % in window |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 5_2_route | 16.0 | drt_violations best 174940 last 174940 rows 1 | before-window best 174940, window best 174940 | PROGRESS: drt_violations: active iteration at 39931 < best completed total 174940 (in-iter |  |
| intel2 | dpkit-slice_station__t12-2526787 | slice_station__t12 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 20.6 | drt_violations best 901 last 5090 rows 18 | before-window best 367946, window best 901 | PROGRESS: drt_violations improved 99.8 % in window |  |
