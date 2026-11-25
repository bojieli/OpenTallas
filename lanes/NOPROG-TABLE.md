# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 08:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 6, 'GRT-LABEL': 5, 'YOUNG': 146, 'NO-DATA': 33, 'KEEP': 1, 'PROGRESS': 19}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | 5_1_grt | 14.8 | last meaningful line 0.3 h ago (2350/2356 lines) | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -353.01 ps (< -300, gate TT >= -42); job age 14 | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 27.5 | drt_violations best 6215 last 14152 rows 19 | before-window best 6298, window best 6215 | NO-PROGRESS: drt_violations best 6215 vs 6298 before window: < 2 % in 6 h | CANCELLED |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | pregrt_ff_hold | 3.4 | repair_TNS best 63490.2 last 63490.2 rows 1 | before-window best 63490.2, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | pregrt_ff_hold | 3.3 | repair_TNS best 51207.7 last 51207.7 rows 1 | before-window best 51207.7, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | pregrt_ff_hold | 3.3 | repair_TNS best 10620.8 last 10620.8 rows 1 | before-window best 10620.8, window best 10620.8 | NO-PROGRESS: repair_TNS best 10620.8 vs 10620.8 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-2360794 | col_h9_r2__t1 | pregrt_ff_hold | 3.5 | repair_TNS best 118766 last 118766 rows 1 | before-window best 118766, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pva119e808-2308652 | col_h9_r2__t1 | pregrt_ff_hold | 3.5 | repair_TNS best 79800.3 last 79800.3 rows 1 | before-window best 79800.3, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc10 | dpkit-kv3_hgi_v4-4881 | kv3_hgi_v4 | 5_1_grt | 3.7 | grt rounds 2 overflow 5:45451 -> 10:32436 | GRT-LABEL: DESIGN-FAIL: overflow 32436 at round 10 > 1000 |  |
| epyc10 | dpkit-phy_serdes_b-1327978 | phy_serdes_b | 5_1_grt | 1.2 | grt rounds 2 overflow 5:43654 -> 10:30355 | GRT-LABEL: DESIGN-FAIL: overflow 30355 at round 10 > 1000 |  |
| epyc7 | dpkit-cbf_q00_s2-1045407 | cbf_q00_s2 | 5_1_grt | 0.6 | grt rounds 2 overflow 5:87022 -> 10:54031 | GRT-LABEL: DESIGN-FAIL: overflow 54031 at round 10 > 1000 |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-3439533 | cbn_q01 | 5_1_grt | 1.3 | grt rounds 2 overflow 5:81921 -> 10:75607 | GRT-LABEL: DESIGN-FAIL: overflow 75607 at round 10 > 1000 |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 5_1_grt | 15.6 | grt rounds 2 overflow 5:17977 -> 10:2858 | GRT-LABEL: DESIGN-FAIL: overflow 2858 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_hg_v1p5-970860 | kv3_hg_v1p5 | 5_1_grt | 6.6 | last meaningful line 2.5 h ago (306/1316 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | dpkit-native59-3384403 | native59 | 5_2_route | 13.7 | drt_violations best 26264 last 26264 rows 3 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | generate_abstract | 21.5 | last meaningful line 0.4 h ago (29/29 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2082061 | slw_st_a_v1 | 5_2_route | 6.4 | drt_violations best 23292 last 23292 rows 3 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | otc-2424957-5022 | 2424957 | signoff | 2.6 | last meaningful line 2.5 h ago (3/3 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | otc-4067299-15490 | 4067299 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | prd-eco_20261125_073109_4058437-i1-634237 | eco_20261125_073109_4058437-i1 | 5_2_route | 3.4 | drt_violations best 470 last 470 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_153001_3155820-i1t-2575664 | eco_20261125_153001_3155820-i1t | 5_2_route | 0.7 | last meaningful line 0.1 h ago (255/256 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | so_2984461_ff_37200 | so_2984461_ff_37200 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc11 | dpkit-hd_lep0N-2989918 | hd_lep0N | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Eo-1420436 | kv3_hub_Eo | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (8702/8702 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Wo-1632470 | kv3_hub_Wo | 4_1_cts | 0.7 | last meaningful line 0.3 h ago (50/50 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | dpkit-sle_su_c-2149031 | sle_su_c | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (8661/8661 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | 5_2_route | 13.0 | drt_violations best 100 last 100 rows 6 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl19bb38ef-40900 | slw_su_c | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (8558/8558 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl92142dac-2960548 | slw_su_c | postcts_gate_FF | 9.3 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | otc-1109607-10581 | 1109607 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc11 | otc-1616228-26288 | 1616228 | - | 2.6 |  | NO-DATA: no log found |  |
| epyc11 | otc-1830932-23851 | 1830932 | - | 2.5 |  | NO-DATA: no log found |  |
| epyc11 | otc-2255400-11827 | 2255400 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc11 | otc-336507-16010 | 336507 | - | 1.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-381902-2867 | 381902 | - | 7.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-608716-5618 | 608716 | signoff | 1.1 | last meaningful line 1.0 h ago (3/3 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_120946_3832190-i1-2448133 | eco_20261125_120946_3832190-i1 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_141555_518460-i1-2852121 | eco_20261125_141555_518460-i1 | 5_2_route | 2.0 | last meaningful line 0.1 h ago (277/278 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | prd-fin-2255468 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | prd-fin-96653 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 4.9 |  | NO-DATA: no log found |  |
| epyc12 | otc-1273822-29690 | 1273822 | drc_merged | 2.4 | last meaningful line 0.0 h ago (512/512 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc12 | otc-1275997-12067 | 1275997 | drc_merged | 2.4 | last meaningful line 0.0 h ago (500/500 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc12 | otc-1278426-9051 | 1278426 | drc_parent_only | 2.4 | last meaningful line 0.0 h ago (779/779 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc12 | otc-1291490-1984 | 1291490 | drc_merged | 2.4 | last meaningful line 0.0 h ago (389/389 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc12 | otc-1294027-30241 | 1294027 | drc_parent_only | 2.4 | last meaningful line 0.0 h ago (959/959 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc12 | otc-1305696-4661 | 1305696 | drc_parent_only | 2.4 | last meaningful line 0.0 h ago (1326/1326 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc12 | otc-1308959-15081 | 1308959 | drc_merged | 2.4 | last meaningful line 0.0 h ago (494/494 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc12 | otc-1312023-14782 | 1312023 | drc_merged | 2.4 | last meaningful line 0.0 h ago (605/605 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc12 | otc-1314683-28749 | 1314683 | drc_merged | 2.4 | last meaningful line 0.0 h ago (527/527 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc12 | otc-1319124-12976 | 1319124 | drc_merged | 2.4 | last meaningful line 0.0 h ago (872/872 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc12 | otc-1338915-16694 | 1338915 | drc_merged | 2.4 | last meaningful line 0.0 h ago (488/488 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc12 | otc-1460135-77 | 1460135 | - | 4.0 |  | NO-DATA: no log found |  |
| epyc12 | otc-1994529-22240 | 1994529 | flow | 2.0 | repair_Violations best 155217 last 155217 rows 14 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc12 | otc-1995249-22339 | 1995249 | flow | 2.0 | last meaningful line 0.1 h ago (3029/3029 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc12 | otc-3501458-13012 | 3501458 | drc_merged | 4.9 | last meaningful line 1.8 h ago (334/334 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc12 | otc-351743-16220 | 351743 | hcpg_run | 2.7 | last meaningful line 2.3 h ago (13/13 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Wi-3068909 | kv3_hub_Wi | 3_5_place_dp | 4.4 | last meaningful line 0.3 h ago (125/125 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-3309425 | sle_fw_v2 | 3_3_place_gp | 0.5 | overflow best 0.0988 last 0.0988 rows 42 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 6.5 | drt_violations best 4 last 4 rows 40 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | otc-2770137-14837 | 2770137 | signoff | 2.4 | last meaningful line 2.3 h ago (3/3 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_204708_4151707-i2t-1352759 | eco_20261124_204708_4151707-i2t | 5_2_route | 3.2 | drt_violations best 376 last 376 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261125_075050_2599201-i1-3410249 | eco_20261125_075050_2599201-i1 | 5_2_route | 0.4 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 2.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 2.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 2.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-A | qcdrt-sc-A | - | 2.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-B | qcdrt-sc-B | - | 2.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-C | qcdrt-sc-C | - | 2.7 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-serdes--t2-grt-2276596 | serdes--t2-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-coll_core-3493022 | coll_core | 5_1_grt | 6.7 | last meaningful line 0.1 h ago (2965/2976 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-hd_host_w-1658816 | hd_host_w | 3_3_place_gp | 0.4 | overflow best 0.3014 last 0.4034 rows 173 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-hd_mesh-1705919 | hd_mesh | 3_3_place_gp | 0.4 | overflow best 0.6695 last 0.6695 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v12e-1804185 | kv3_pv_v12e | 4_1_cts | 0.3 | last meaningful line 0.2 h ago (11382/11382 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v6e-646291 | kv3_pv_v6e | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (8417/8417 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | 4_1_cts | 2.8 | last meaningful line 0.3 h ago (10906/10906 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 4_1_cts | 2.5 | last meaningful line 0.1 h ago (5217/5217 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | 5_2_route | 9.9 | last meaningful line 0.1 h ago (129/129 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 6.7 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | postcts_gate_FF | 6.7 | last meaningful line -0.0 h ago (29043/29043 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-22145 | sle_sc_v2 | postcts_gate_TT | 1.0 | last meaningful line 0.1 h ago (71683/71683 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__clc6d66f5b-2521917 | sle_su_l1 | 5_2_route | 7.2 | drt_violations best 54514 last 54514 rows 2 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 7.1 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 9.8 | drt_violations best 456468 last 456468 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc7 | otc-1526635-14441 | 1526635 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc7 | otc-2615318-31399 | 2615318 | 5_2_route | 0.0 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-2858837-8104 | 2858837 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc7 | otc-2938337-22499 | 2938337 | - | 3.2 |  | NO-DATA: no log found |  |
| epyc7 | otc-2958007-4014 | 2958007 | - | 3.2 |  | NO-DATA: no log found |  |
| epyc7 | otc-740568-7161 | 740568 | drc_merged | 2.3 | last meaningful line 0.0 h ago (596/596 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | otc-830728-15409 | 830728 | drc_parent_only | 2.3 | last meaningful line 0.0 h ago (1175/1175 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | otc-831702-28906 | 831702 | drc_merged | 2.3 | last meaningful line 0.0 h ago (569/569 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | otc-833865-16155 | 833865 | drc_parent_only | 2.3 | last meaningful line 0.0 h ago (1326/1326 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | otc-835730-18044 | 835730 | drc_merged | 2.3 | last meaningful line 0.0 h ago (929/929 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | otc-838804-29233 | 838804 | drc_merged | 2.3 | last meaningful line 0.0 h ago (1031/1031 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | so_1343591_ff_66716 | so_1343591_ff_66716 | generate_abstract | 0.5 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | so_1343591_tt_66716 | so_1343591_tt_66716 | generate_abstract | 0.5 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | so_1885005_ff_49255 | so_1885005_ff_49255 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (33/33 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | so_1885005_tt_49255 | so_1885005_tt_49255 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (33/33 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | so_1959400_ff_75488 | so_1959400_ff_75488 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (27/27 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | so_1959400_tt_75488 | so_1959400_tt_75488 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (27/27 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | so_2056694_ff_86739 | so_2056694_ff_86739 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (35/35 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | so_2056694_tt_86739 | so_2056694_tt_86739 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (35/35 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | so_2217724_ff_55845 | so_2217724_ff_55845 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | so_2217724_tt_55845 | so_2217724_tt_55845 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-slice-station--t30--cl1653104c-grt-1570169 | slice-station--t30--cl1653104c-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-918588 | col_h10_r0_p1__t1 | pregrt_ff_hold | 4.0 | repair_TNS best 75222.8 last 75222.8 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_mu_C__t1-730122 | dsdv_slice_lepe_mu_C__t1 | 3_5_place_dp | 4.1 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-hd_lep0N-331993 | hd_lep0N | 3_1_place_gp_skip_io | 0.4 | overflow best 0.099 last 0.099 rows 49 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-hd_tile-764931 | hd_tile | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (2179/2179 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v3n-2522162 | kv3_pv_v3n | 5_1_grt | 3.5 | last meaningful line 0.3 h ago (275/277 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | generate_abstract | 24.1 | last meaningful line 0.3 h ago (27/27 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t24__cl66b71008-1491953 | slice_station__t24 | 2_3_floorplan_tapcell | 0.0 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t51-3913394 | slice_station__t51 | 3_4_place_resized | 0.5 | last meaningful line 0.1 h ago (244/244 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | eco-abs-275695 | eco-abs | generate_abstract | 0.4 | last meaningful line 0.2 h ago (31/31 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | eco-abs-632750 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.1 h ago (29/29 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | eco-abs-913604 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.1 h ago (27/27 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | eco-abs-983313 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.1 h ago (29/29 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | otc-1220115-969 | 1220115 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-1288521-5795 | 1288521 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-132122-8685 | 132122 | - | 4.3 |  | NO-DATA: no log found |  |
| epyc8 | otc-1982827-8639 | 1982827 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc8 | prd-count-p1_bc-1582033 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_025941_3548303-i2-1098320 | eco_20261125_025941_3548303-i2 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_104318_3955073-i1-65595 | eco_20261125_104318_3955073-i1 | 5_2_route | 1.7 | last meaningful line 0.0 h ago (261/262 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | so_73079_ff_51781 | so_73079_ff_51781 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (33/33 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | so_73079_tt_51781 | so_73079_tt_51781 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (33/33 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | so_773309_ff_5523 | so_773309_ff_5523 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (33/33 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | so_773309_tt_5523 | so_773309_tt_5523 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (33/33 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-col-h10-r0-p1--t1--cl574cc59d--pvf60ac9dc-grt-3042276 | col-h10-r0-p1--t1--cl574cc59d--pvf60ac9dc-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t53--cl958451dd-grt-3019643 | ot-s81sl-leaf--t53--cl958451dd-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | 5_1_grt | 9.5 | last meaningful line 0.5 h ago (278/1285 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvc9270d09-1494595 | col_h10_r0_p4__t1 | 4_2_tapbal_grt | 0.5 | last meaningful line 0.0 h ago (60/61 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 5_1_grt | 9.5 | last meaningful line 0.5 h ago (270/1282 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | 4_2_tapbal_grt | 0.5 | last meaningful line 0.0 h ago (248/248 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3698869 | col_h9_r0_p4__t1 | 5_2_route | 7.4 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 9.5 | last meaningful line 0.5 h ago (285/286 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv8995e794-2664422 | col_h9_r0_p5__t1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (2981/2981 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3332/3332 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 6.7 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pvf0f1ccb2-2415711 | col_h9_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.4114 last 0.4127 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4356/4356 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvb3258867-2178566 | col_h9_r2__t1 | 3_5_place_dp | 0.4 | repair_Violations best 1081 last 1081 rows 12 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t7-3863913 | dsdv_slice_c1x_C__t7 | 3_3_place_gp | 3.8 | overflow best 0.5928 last 0.7594 rows 54 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2186209 | dsdv_slice_lepe_nh_mus_LP__t1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3163/3163 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2726055 | ot_s81sl_kv_leaf__t5 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (2338/2338 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t11-2006269 | ot_s81sl_leaf__t11 | 3_3_place_gp | 0.4 | last meaningful line 0.1 h ago (69/69 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t52-2064181 | ot_s81sl_leaf__t52 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.2416 last 0.2416 rows 33 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slice_station__t37-3479533 | slice_station__t37 | 5_2_route | 7.4 | drt_violations best 34873 last 34873 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__clc8fb2c8c-2653854 | slice_station__t40 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (2894/2894 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t41-1123489 | slice_station__t41 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (4041/4041 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t43-3486441 | slice_station__t43 | 5_2_route | 7.4 | drt_violations best 3860 last 3860 rows 2 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t44-2657480 | slice_station__t44 | 5_2_route | 2.4 | last meaningful line 0.1 h ago (255/256 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-2620358 | slice_station__t52 | 5_2_route | 6.2 | drt_violations best 33724 last 33724 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | otc-1865534-29853 | 1865534 | - | 1.8 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2686622 | col_h10_r0_p4__t1 | pregrt_ff_hold | 3.4 | repair_TNS best 96462.2 last 96462.2 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | pregrt_ff_hold | 3.4 | repair_TNS best 71771.6 last 71771.6 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 4_2_tapbal_grt | 3.3 | last meaningful line 2.5 h ago (61/94 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 4_2_tapbal_grt | 3.2 | last meaningful line 2.5 h ago (61/86 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 4_2_tapbal_grt | 3.4 | last meaningful line 2.5 h ago (61/87 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1177242 | kv3_hg_v1p3__r838481cd7 | 5_1_grt | 8.6 | last meaningful line 4.0 h ago (288/1298 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_sys_c-4063347 | kv3_sys_c | postcts_gate_TT | 5.2 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 5_2_route | 15.2 | last meaningful line 0.4 h ago (271/272 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t27-4040446 | slice_station__t27 | 5_2_route | 5.2 | last meaningful line 0.5 h ago (251/252 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 16.9 | last meaningful line 0.7 h ago (264/265 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 5_2_route | 17.7 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | otc-1343902-2148 | 1343902 | flow | 0.4 | last meaningful line 0.0 h ago (2684/2684 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | otc-1750914-12376 | 1750914 | flow | 0.2 | last meaningful line 0.0 h ago (1856/1856 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-2284893-4545 | 2284893 | flow | 0.0 | last meaningful line 0.0 h ago (240/240 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-2590726-12039 | 2590726 | - | 1.6 |  | NO-DATA: no log found |  |
| intel1 | otc-3018992-28537 | 3018992 | - | 1.4 |  | NO-DATA: no log found |  |
| intel1 | otc-574655-9239 | 574655 | drc_parent_only | 2.4 | last meaningful line 0.0 h ago (488/488 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | otc-578793-24959 | 578793 | drc_parent_only | 2.4 | last meaningful line 0.0 h ago (326/326 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | otc-582965-3828 | 582965 | drc_parent_only | 2.4 | last meaningful line 0.0 h ago (338/338 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | otc-586189-14994 | 586189 | drc_parent_only | 2.4 | last meaningful line 0.0 h ago (497/497 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | otc-589045-16647 | 589045 | drc_parent_only | 2.4 | last meaningful line 0.0 h ago (1094/1094 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i3t-2681077 | eco_20261123_191853_2879776-i3t | 5_2_route | 5.4 | last meaningful line 0.5 h ago (289/290 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1t-3347319 | eco_20261125_002226_1452841-i1t | 5_2_route | 7.8 | drt_violations best 9407 last 9407 rows 1 | YOUNG: evidence 6.2 h < 7.5 h |  |
| intel1 | prd-eco_20261125_040243_2843749-i1-851245 | eco_20261125_040243_2843749-i1 | 5_2_route | 4.1 | last meaningful line 0.5 h ago (272/273 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i1-3109373 | eco_20261125_050013_1448739-i1 | 5_2_route | 3.2 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | prd-eco_20261125_070347_2847958-i1-3642895 | eco_20261125_070347_2847958-i1 | 5_1_grt | 1.1 | last meaningful line 0.2 h ago (145/145 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | prd-eco_20261125_072849_2847456-i1-527377 | eco_20261125_072849_2847456-i1 | 5_1_grt | 0.7 | last meaningful line 0.2 h ago (138/138 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | so_2067287_ff_39738 | so_2067287_ff_39738 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (34/34 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | so_2067287_tt_39738 | so_2067287_tt_39738 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (34/34 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | so_3239057_ff_21478 | so_3239057_ff_21478 | signoff | 1.3 |  | NO-DATA: empty log |  |
| intel1 | so_3239057_tt_21478 | so_3239057_tt_21478 | signoff | 1.3 |  | NO-DATA: empty log |  |
| intel2 | dpkit-coll_ftm-1141936 | coll_ftm | 5_2_route | 1.0 | last meaningful line 0.0 h ago (225/225 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_ctl-3068348 | hd_ctl | 3_5_place_dp | 0.3 | last meaningful line 0.0 h ago (109/109 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-hd_lep0N-3299955 | hd_lep0N | 3_1_place_gp_skip_io | 0.3 | overflow best 0.773 last 0.7957 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-hd_mesh-2983606 | hd_mesh | 3_3_place_gp | 0.4 | overflow best 0.5695 last 0.5695 rows 28 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-3382317 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-1887004 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (225/226 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-1955823 | kv3_hgi | 5_2_route | 6.4 |  | KEEP: kv3_hgi_1124155644	KV-OWN-RSTREACH	combined HEADLEG2+HGI-LEAF ship form; noprog  |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 21.4 | drt_violations best 297 last 297 rows 30 | before-window best 71235, window best 297 | PROGRESS: drt_violations improved 99.6 % in window |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 22.7 | drt_violations best 21 last 21 rows 30 | before-window best 58968, window best 21 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 27.4 | drt_violations best 11895 last 11895 rows 13 | before-window best 19919, window best 11895 | PROGRESS: drt_violations improved 40.3 % in window |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3817081 | sle_st_a_v2 | 5_2_route | 8.2 | drt_violations best 72 last 72 rows 52 | before-window best 143821, window best 72 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 27.2 | drt_violations best 5853 last 5853 rows 15 | before-window best 11873, window best 5853 | PROGRESS: drt_violations improved 50.7 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 24.1 | drt_violations best 68 last 68 rows 30 | before-window best 266434, window best 68 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-1637048 | col_h9_r1__t1 | 3_5_place_dp | 0.5 | repair_Violations best 0 last 0 rows 24 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | 4_2_tapbal_grt | 0.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 11.4 | drt_violations best 659 last 2629 rows 18 | before-window best 162909, window best 659 | PROGRESS: drt_violations improved 99.6 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-2945122 | col_h9_r2__t1 | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 3 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | 4_1_cts | 0.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | 5_2_route | 10.5 | drt_violations best 432 last 432 rows 19 | before-window best 163283, window best 432 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 21.2 | drt_violations best 4 last 4 rows 53 | before-window best 282, window best 4 | PROGRESS: drt_violations improved 98.6 % in window |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 5_2_route | 19.5 | drt_violations best 138407 last 138407 rows 1 | before-window best 138407, window best 138407 | PROGRESS: drt_violations: active iteration at 40451 < best completed total 138407 (in-iter |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 19.4 | drt_violations best 1 last 1 rows 45 | before-window best 38, window best 1 | PROGRESS: drt_violations improved 97.4 % in window |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 27.4 | drt_violations best 4712 last 4712 rows 11 | before-window best 71761, window best 4712 | PROGRESS: drt_violations improved 93.4 % in window |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 5_2_route | 18.0 | drt_violations best 26476 last 26476 rows 2 | before-window best 174940, window best 26476 | PROGRESS: drt_violations improved 84.9 % in window |  |
| intel2 | dpkit-kv3_io_ft-3387973 | kv3_io_ft | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 22.6 | drt_violations best 805 last 805 rows 22 | before-window best 14540, window best 805 | PROGRESS: drt_violations improved 94.5 % in window |  |
