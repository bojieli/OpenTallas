# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 07:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'GRT-LABEL': 11, 'YOUNG': 151, 'NO-DATA': 37, 'KEEP': 2, 'EXCLUDED': 1, 'PROGRESS': 24}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 31.6 | drt_violations best 2761 last 4468 rows 20 | before-window best 2761, window best 4468 | NO-PROGRESS: drt_violations best 4468 vs 2761 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-OPEN-SU decides; nev |
| epyc7 | dpkit-slw_su_l1__cla2a78701-534954 | slw_su_l1 | tt_setup_repair_grt | 8.4 | repair_Violations best 0 last 0 rows 46 | before-window best 0, window best - | NO-PROGRESS: no new repair_Violations row in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc8 | dpkit-kv3_hg_v1p5-3496343 | kv3_hg_v1p5 | pregrt_ff_hold | 4.8 | repair_TNS best 809467 last 809467 rows 1 | before-window best 809467, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-D29 decides; never a |
| epyc11 | dpkit-kv3_hg_v3-561930 | kv3_hg_v3 | 5_1_grt | 2.2 | grt rounds 2 overflow 5:48439 -> 10:42500 | GRT-LABEL: DESIGN-FAIL: overflow 42500 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v2-1828900 | kv3_pv_v2 | 5_1_grt | 1.5 | grt rounds 2 overflow 5:63965 -> 10:48975 | GRT-LABEL: DESIGN-FAIL: overflow 48975 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v3e-640390 | kv3_pv_v3e | 5_1_grt | 2.1 | grt rounds 2 overflow 5:86034 -> 10:53939 | GRT-LABEL: DESIGN-FAIL: overflow 53939 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | 5_1_grt | 17.6 | grt rounds 1 overflow 5:74746 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc11 | dpkit-kv3_pv_v6n-721471 | kv3_pv_v6n | 5_1_grt | 2.1 | grt rounds 2 overflow 5:45246 -> 10:35967 | GRT-LABEL: DESIGN-FAIL: overflow 35967 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v8-2209532 | kv3_pv_v8 | 5_1_grt | 1.3 | grt rounds 2 overflow 5:37272 -> 10:15899 | GRT-LABEL: DESIGN-FAIL: overflow 15899 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v8e-579863 | kv3_pv_v8e | 5_1_grt | 2.2 | grt rounds 2 overflow 5:88213 -> 10:73755 | GRT-LABEL: DESIGN-FAIL: overflow 73755 at round 10 > 1000 |  |
| epyc11 | dpkit-slw_su_c__cl92142dac-2960548 | slw_su_c | 5_1_grt | 8.3 | grt rounds 2 overflow 5:21500 -> 10:14785 | GRT-LABEL: DESIGN-FAIL: overflow 14785 at round 10 > 1000 |  |
| epyc7 | dpkit-cbf_q00_s2-3518685 | cbf_q00_s2 | 5_1_grt | 8.9 | grt rounds 2 overflow 5:87022 -> 10:54031 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-3439533 | cbn_q01 | 5_1_grt | 0.3 | grt rounds 2 overflow 5:81921 -> 10:75607 | GRT-LABEL: DESIGN-FAIL: overflow 75607 at round 10 > 1000 |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 5_1_grt | 14.6 | grt rounds 2 overflow 5:17977 -> 10:2858 | GRT-LABEL: DESIGN-FAIL: overflow 2858 at round 10 > 1000 |  |
| epyc10 | dpkit-hd_lep0N_w-3160116 | hd_lep0N_w | 6_report | 5.0 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p5-970860 | kv3_hg_v1p5 | 5_1_grt | 5.6 | last meaningful line 1.5 h ago (306/1313 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v4-4881 | kv3_hgi_v4 | 5_1_grt | 2.7 | last meaningful line 0.5 h ago (293/1300 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | 5_1_grt | 13.8 | last meaningful line 0.2 h ago (2258/2263 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | dpkit-native59-3384403 | native59 | 5_2_route | 12.7 | drt_violations best 234004 last 234004 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc10 | dpkit-phy_serdes_b-1327978 | phy_serdes_b | tt_setup_measure | 0.2 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 6_report | 20.5 | last meaningful line 0.0 h ago (70/70 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | 6_report | 19.1 | last meaningful line 0.0 h ago (71/71 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2082061 | slw_st_a_v1 | 5_2_route | 5.4 | drt_violations best 157351 last 157351 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | otc-1762308-21603 | 1762308 | signoff | 3.9 | last meaningful line 3.8 h ago (3/3 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc10 | otc-2025541-6828 | 2025541 | signoff | 1.8 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | otc-2424957-5022 | 2424957 | signoff | 1.6 | last meaningful line 1.5 h ago (3/3 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | prd-count-p1_bc-1820297 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_073109_4058437-i1-634237 | eco_20261125_073109_4058437-i1 | 5_2_route | 2.4 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-cbn_q00__cl622f65d2-2378800 | cbn_q00 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (5511/5511 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc11 | dpkit-hd_lep0N-2184208 | hd_lep0N | 5_1_grt | 1.3 | last meaningful line 0.0 h ago (176/176 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Eo-871015 | kv3_hub_Eo | 3_5_place_dp | 2.0 | last meaningful line 0.1 h ago (117/117 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Wo-954396 | kv3_hub_Wo | 3_5_place_dp | 1.9 | last meaningful line 0.0 h ago (119/119 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v5-1052229 | kv3_pv_v5 | 5_1_grt | 5.9 | last meaningful line 0.8 h ago (272/1278 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v5n-798731 | kv3_pv_v5n | lec | 2.0 | LEC last write 1.4 h ago | YOUNG: evidence 2.0 h < 6 h |  |
| epyc11 | dpkit-sle_su_c-2485454 | sle_su_c | 3_3_place_gp | 1.1 | overflow best 0.0981 last 0.0981 rows 48 | YOUNG: stage 0.6 h < 1 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | 5_2_route | 12.0 | drt_violations best 141406 last 141406 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl19bb38ef-40900 | slw_su_c | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (8299/8300 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | eco-abs-3833269 | eco-abs | generate_abstract | 0.5 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | otc-1616228-26288 | 1616228 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc11 | otc-1830932-23851 | 1830932 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc11 | otc-3124125-30954 | 3124125 | - | 2.9 |  | NO-DATA: no log found |  |
| epyc11 | otc-336507-16010 | 336507 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-381902-2867 | 381902 | - | 6.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-608716-5618 | 608716 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i2t-2255468 | eco_20261124_190641_1260390-i2t | 5_2_route | 5.3 | drt_violations best 5541 last 5541 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i2t-96653 | eco_20261124_200101_1087713-i2t | 5_2_route | 4.3 | drt_violations best 4960 last 4960 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_120946_3832190-i1t-2887287 | eco_20261125_120946_3832190-i1t | 5_2_route | 3.1 | drt_violations best 1170 last 1170 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_141555_518460-i1-2852121 | eco_20261125_141555_518460-i1 | 5_1_grt | 1.0 | last meaningful line 0.4 h ago (292/538 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | so_3691111_ff_59809 | so_3691111_ff_59809 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (35/35 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | so_3691111_tt_59809 | so_3691111_tt_59809 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (35/35 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | so_576324_ff_36564 | so_576324_ff_36564 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (35/35 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | so_576324_tt_36564 | so_576324_tt_36564 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (35/35 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1520876 | col_h10_r0_p4__t1 | 5_1_grt | 2.9 | last meaningful line 0.1 h ago (1510/1525 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc12 | dpkit-hd_lep0N-2152952 | hd_lep0N | 4_2_tapbal_grt | 4.7 | last meaningful line 3.3 h ago (48/53 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc12 | dpkit-kv3_hgi_v7-2529031 | kv3_hgi_v7 | 5_1_grt | 4.5 | last meaningful line 1.8 h ago (295/1303 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-4135984 | kv3_pc | 3_5_place_dp | 1.9 | last meaningful line 0.0 h ago (70/70 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pv_v12-2339543 | kv3_pv_v12 | 5_1_grt | 4.6 | last meaningful line 0.0 h ago (189/189 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc12 | dpkit-slw_st_a_v2__clf4365a62-2414803 | slw_st_a_v2 | 5_2_route | 4.6 | last meaningful line 0.5 h ago (260/261 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 3.9 |  | NO-DATA: no log found |  |
| epyc12 | otc-1273822-29690 | 1273822 | drc_merged | 1.4 | last meaningful line 0.0 h ago (212/212 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc12 | otc-1275997-12067 | 1275997 | drc_parent_only | 1.4 | last meaningful line 0.0 h ago (347/347 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc12 | otc-1278426-9051 | 1278426 | drc_parent_only | 1.4 | last meaningful line 0.1 h ago (209/209 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc12 | otc-1291490-1984 | 1291490 | drc_merged | 1.4 | last meaningful line 0.0 h ago (194/194 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc12 | otc-1294027-30241 | 1294027 | drc_parent_only | 1.4 | last meaningful line 0.0 h ago (260/260 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc12 | otc-1305696-4661 | 1305696 | drc_parent_only | 1.4 | last meaningful line 0.0 h ago (320/320 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc12 | otc-1308959-15081 | 1308959 | drc_macros_only | 1.4 | last meaningful line -0.0 h ago (800/800 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc12 | otc-1312023-14782 | 1312023 | drc_macros_only | 1.4 | last meaningful line 0.0 h ago (602/602 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc12 | otc-1314683-28749 | 1314683 | drc_parent_only | 1.4 | last meaningful line 0.0 h ago (398/398 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc12 | otc-1319124-12976 | 1319124 | drc_macros_only | 1.4 | last meaningful line -0.0 h ago (611/611 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc12 | otc-1321394-11555 | 1321394 | drc_merged | 1.4 | last meaningful line 0.0 h ago (308/308 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc12 | otc-1324644-27944 | 1324644 | drc_merged | 1.4 | last meaningful line 0.1 h ago (215/215 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc12 | otc-1338915-16694 | 1338915 | drc_macros_only | 1.4 | last meaningful line -0.0 h ago (701/701 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc12 | otc-1460135-77 | 1460135 | - | 3.0 |  | NO-DATA: no log found |  |
| epyc12 | otc-1994529-22240 | 1994529 | flow | 1.0 | last meaningful line 0.0 h ago (2892/2892 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc12 | otc-1995249-22339 | 1995249 | flow | 1.0 | last meaningful line 0.0 h ago (2877/2877 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc12 | otc-3293317-27322 | 3293317 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc12 | otc-3501458-13012 | 3501458 | drc_merged | 3.9 | last meaningful line 0.8 h ago (334/334 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc12 | otc-351743-16220 | 351743 | hcpg_run | 1.7 | last meaningful line 1.3 h ago (13/13 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc12 | otc-3657232-15878 | 3657232 | asbuilt.yosys | 0.2 | last meaningful line -0.0 h ago (136439/136439 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | otc-3800224-11206 | 3800224 | asbuilt.yosys | 0.1 | last meaningful line -0.0 h ago (136630/136630 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Wi-3068909 | kv3_hub_Wi | 3_4_place_resized | 3.4 | last meaningful line 0.2 h ago (643/643 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 5.5 | drt_violations best 86 last 86 rows 12 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2601551 | slw_st_a_v1 | 5_3_fillcell | 5.8 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-2770137-14837 | 2770137 | signoff | 1.4 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_204708_4151707-i2t-1352759 | eco_20261124_204708_4151707-i2t | 5_2_route | 2.2 | drt_violations best 376 last 376 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 1.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 1.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 1.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-A | qcdrt-sc-A | - | 1.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-B | qcdrt-sc-B | - | 1.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-C | qcdrt-sc-C | - | 1.7 |  | NO-DATA: no log found |  |
| epyc2 | so_2207232_ff_52111 | so_2207232_ff_52111 | signoff2 | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | so_2207232_tt_52111 | so_2207232_tt_52111 | signoff2 | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | so_2208500_ff_76314 | so_2208500_ff_76314 | signoff2 | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | so_2208500_tt_76314 | so_2208500_tt_76314 | signoff2 | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | so_2209408_ff_99909 | so_2209408_ff_99909 | signoff2 | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | so_2209408_tt_99909 | so_2209408_tt_99909 | signoff2 | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | so_2210093_ff_39019 | so_2210093_ff_39019 | signoff2 | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | so_2210093_tt_39019 | so_2210093_tt_39019 | signoff2 | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | ap-ageom-kw-kv3-pv-v6e-grt-3949476 | kv3-pv-v6e-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-coll_core-3493022 | coll_core | 5_1_grt | 5.7 | repair_Remaining best 255811 last 255811 rows 165 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t2-3977371 | serdes__t2 | 3_4_place_resized | 1.8 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | 4_1_cts | 1.8 | last meaningful line 0.3 h ago (10828/10828 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (5142/5142 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | postcts_gate_FF | 8.9 | last meaningful line 0.1 h ago (384/384 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | postcts_gate_TT | 5.7 | last meaningful line -0.0 h ago (69029/69029 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | postcts_gate_TT | 5.7 | last meaningful line 0.2 h ago (2140/2140 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3817081 | sle_st_a_v2 | 5_2_route | 7.2 | drt_violations best 72 last 72 rows 33 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__clc6d66f5b-2521917 | sle_su_l1 | 5_2_route | 6.2 | drt_violations best 237032 last 237032 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | postcts_gate_TT | 6.1 | last meaningful line -0.0 h ago (69884/69884 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 8.8 | drt_violations best 456468 last 456468 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc7 | eco-abs-718120 | eco-abs | generate_abstract | 1.3 | last meaningful line 0.1 h ago (33/33 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | otc-2858837-8104 | 2858837 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc7 | otc-2916017-13620 | 2916017 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc7 | otc-2938337-22499 | 2938337 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc7 | otc-2958007-4014 | 2958007 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc7 | otc-740568-7161 | 740568 | drc_parent_only | 1.3 | last meaningful line 0.0 h ago (269/269 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | otc-830728-15409 | 830728 | drc_parent_only | 1.3 | last meaningful line 0.0 h ago (260/260 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | otc-831702-28906 | 831702 | drc_parent_only | 1.3 | last meaningful line 0.0 h ago (266/266 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | otc-833865-16155 | 833865 | drc_parent_only | 1.3 | last meaningful line 0.0 h ago (278/278 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | otc-835730-18044 | 835730 | drc_parent_only | 1.3 | last meaningful line 0.0 h ago (1298/1298 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | otc-838804-29233 | 838804 | drc_merged | 1.3 | last meaningful line 0.0 h ago (260/260 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | prd-count-p1_tc-2551803 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-count-p1_tc-3230821 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i2-1995832 | eco_20261124_192157_3493836-i2 | 5_3_fillcell | 2.6 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-fin-1443376 | fin | 6_report | 0.3 | last meaningful line 0.0 h ago (51/51 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-fin-4068402 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-918588 | col_h10_r0_p1__t1 | pregrt_ff_hold | 3.0 | repair_TNS best 75222.8 last 75222.8 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_mu_C__t1-730122 | dsdv_slice_lepe_mu_C__t1 | 3_1_place_gp_skip_io | 3.1 | overflow best 0.8572 last 0.8734 rows 23 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v3n-2522162 | kv3_pv_v3n | tt_setup_repair | 2.5 | repair_Violations best 1459 last 1766 rows 26 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_3_fillcell | 23.1 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | eco-abs-2030101 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-132122-8685 | 132122 | - | 3.3 |  | NO-DATA: no log found |  |
| epyc8 | otc-1321249-29104 | 1321249 | - | 2.9 |  | NO-DATA: no log found |  |
| epyc8 | otc-1982827-8639 | 1982827 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_025941_3548303-i2t-3977758 | eco_20261125_025941_3548303-i2t | 5_2_route | 2.1 | drt_violations best 213 last 213 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_104318_3955073-i1-65595 | eco_20261125_104318_3955073-i1 | 5_1_grt | 0.7 | last meaningful line 0.1 h ago (289/324 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_120022_4021525-i1-420704 | eco_20261125_120022_4021525-i1 | 5_2_route | 3.2 | drt_violations best 11 last 11 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_122258_3982108-i1-1582033 | eco_20261125_122258_3982108-i1 | 5_2_route | 2.8 | drt_violations best 2 last 2 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_123046_4033426-i1-1985482 | eco_20261125_123046_4033426-i1 | 5_2_route | 2.7 | drt_violations best 18 last 18 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_123952_3914547-i1-2528575 | eco_20261125_123952_3914547-i1 | 5_2_route | 2.5 | drt_violations best 131 last 131 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | prd-fin-3480940 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-fin-3788521 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | 5_1_grt | 8.5 | last meaningful line 0.0 h ago (156/156 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 5_1_grt | 8.5 | repair_Remaining best 107033 last 107033 rows 96 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-296584 | col_h9_r0_p3__t1 | 5_1_grt | 11.1 | last meaningful line 2.5 h ago (272/1322 lines) | YOUNG: evidence 3.0 h < 6 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3698869 | col_h9_r0_p4__t1 | 5_1_grt | 6.4 | last meaningful line 0.1 h ago (1315/1354 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 8.5 | last meaningful line 0.3 h ago (279/280 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_1_grt | 5.7 | last meaningful line 0.3 h ago (1310/2400 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pvf1445dce-2628247 | col_h9_r2__t1 | 5_2_route | 5.1 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv31e47bd5-4047516 | col_h9_r2__t1 | 5_2_route | 5.7 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-3394850 | col_h9_r2__t1 | 5_2_route | 8.6 | drt_violations best 21832 last 21832 rows 3 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-3707756 | col_h9_r2__t1 | 5_2_route | 8.5 | drt_violations best 2419 last 2419 rows 6 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve0486b40-3725060 | col_h9_r2__t1 | 5_2_route | 6.4 | drt_violations best 155476 last 155476 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | 5_2_route | 9.5 | drt_violations best 1068 last 1068 rows 13 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t7-3863913 | dsdv_slice_c1x_C__t7 | 2_4_floorplan_pdn | 2.8 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-3479533 | slice_station__t37 | 5_2_route | 6.4 | drt_violations best 34873 last 34873 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t43-3486441 | slice_station__t43 | 5_2_route | 6.4 | drt_violations best 34635 last 34635 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t44-2657480 | slice_station__t44 | postcts_gate_TT | 1.4 | last meaningful line 0.0 h ago (23725/23725 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-2620358 | slice_station__t52 | 5_2_route | 5.2 | last meaningful line 0.2 h ago (260/261 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | otc-1865534-29853 | 1865534 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc9 | otc-840152-30448 | 840152 | signoff | 0.3 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | tt_setup_repair | 2.4 | repair_Viol best 1106 last 1106 rows 15 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.3 | last meaningful line 1.5 h ago (61/80 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.2 | last meaningful line 1.5 h ago (61/79 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.4 | last meaningful line 1.5 h ago (61/80 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | pregrt_ff_hold | 2.4 | repair_TNS best 63490.2 last 63490.2 rows 1 | YOUNG: evidence 1.4 h < 2.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 51207.7 last 51207.7 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | pregrt_ff_hold | 2.3 | repair_TNS best 60746.9 last 60746.9 rows 1 | YOUNG: evidence 1.4 h < 2.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-2360794 | col_h9_r2__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 118766 last 118766 rows 1 | YOUNG: evidence 1.5 h < 2.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pva119e808-2308652 | col_h9_r2__t1 | pregrt_ff_hold | 2.5 | repair_TNS best 79800.3 last 79800.3 rows 1 | YOUNG: evidence 1.5 h < 2.5 h |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1177242 | kv3_hg_v1p3__r838481cd7 | 5_1_grt | 7.6 | last meaningful line 3.0 h ago (288/1297 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_sys_c-4063347 | kv3_sys_c | 5_1_grt | 4.2 | last meaningful line 0.0 h ago (2947/2950 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 5_2_route | 14.2 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 5_2_route | 18.5 | drt_violations best 138407 last 138407 rows 1 | YOUNG: evidence 6.2 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t27-4040446 | slice_station__t27 | 5_2_route | 4.2 | last meaningful line 0.1 h ago (248/248 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 15.9 | last meaningful line 0.1 h ago (261/261 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 5_2_route | 16.7 | last meaningful line 0.7 h ago (263/264 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | otc-2590726-12039 | 2590726 | - | 0.6 |  | NO-DATA: no log found |  |
| intel1 | otc-3018992-28537 | 3018992 | - | 0.4 |  | NO-DATA: no log found |  |
| intel1 | otc-3504566-18256 | 3504566 | grt_it0 | 4.3 | last meaningful line 0.3 h ago (31/32 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | otc-574655-9239 | 574655 | drc_macros_only | 1.4 | last meaningful line 0.0 h ago (488/488 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | otc-578793-24959 | 578793 | drc_parent_only | 1.4 | last meaningful line 0.0 h ago (185/185 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | otc-582965-3828 | 582965 | drc_parent_only | 1.4 | last meaningful line 0.0 h ago (188/188 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | otc-586189-14994 | 586189 | drc_merged | 1.4 | last meaningful line 0.1 h ago (176/176 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | otc-589045-16647 | 589045 | drc_macros_only | 1.4 | last meaningful line 0.0 h ago (620/620 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | otc-591807-6566 | 591807 | drc_merged | 1.4 | last meaningful line 0.0 h ago (1004/1004 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i3t-2681077 | eco_20261123_191853_2879776-i3t | 5_2_route | 4.4 | last meaningful line 0.2 h ago (285/286 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1t-3347319 | eco_20261125_002226_1452841-i1t | 5_2_route | 6.8 | drt_violations best 9407 last 9407 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | prd-eco_20261125_040243_2843749-i1-851245 | eco_20261125_040243_2843749-i1 | 5_2_route | 3.1 | last meaningful line 0.7 h ago (266/267 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i1-3109373 | eco_20261125_050013_1448739-i1 | 5_2_route | 2.2 | last meaningful line 0.5 h ago (133/133 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | prd-eco_20261125_070347_2847958-i1-3642895 | eco_20261125_070347_2847958-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | so_3239057_ff_21478 | so_3239057_ff_21478 | signoff | 0.3 |  | NO-DATA: empty log |  |
| intel1 | so_3239057_tt_21478 | so_3239057_tt_21478 | signoff | 0.3 |  | NO-DATA: empty log |  |
| intel1 | so_445807_ff_5944 | so_445807_ff_5944 | signoff | 1.4 |  | NO-DATA: empty log |  |
| intel1 | so_445807_tt_5944 | so_445807_tt_5944 | signoff | 1.4 |  | NO-DATA: empty log |  |
| intel2 | dpkit-hd_serdes-3275033 | hd_serdes | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-505107 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-3008115 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5442 last 5442 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-kv3_pv_v12e-1190106 | kv3_pv_v12e | 3_5_place_dp | 1.5 | last meaningful line 0.0 h ago (83/83 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-2526787 | slice_station__t12 | abstract_exact | 1.2 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | otc-2407048-21046 | 2407048 | signoff | 2.0 | last meaningful line 2.0 h ago (3/3 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-1955823 | kv3_hgi | 5_2_route | 5.4 |  | KEEP: kv3_hgi_1124155644	KV-OWN-RSTREACH	combined HEADLEG2+HGI-LEAF ship form; noprog  |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pvb2cd22a7-3043152 | col_h9_r2__t1 | 5_2_route | 4.3 |  | KEEP: col_h9_r2__t1__clb8d86cd5__pvb2cd22a7	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | eco-abs-3679279 | eco-abs | generate_abstract | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_2_route | 21.5 | drt_violations best 63562 last 63562 rows 5 | before-window best 416066, window best 63562 | PROGRESS: drt_violations improved 84.7 % in window |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 20.4 | drt_violations best 398 last 398 rows 23 | before-window best 272423, window best 398 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_2_route | 20.4 | drt_violations best 18029 last 18029 rows 8 | before-window best 378938, window best 18029 | PROGRESS: drt_violations improved 95.2 % in window |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 21.7 | drt_violations best 71 last 71 rows 23 | before-window best 84312, window best 71 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 26.5 | drt_violations best 6215 last 33693 rows 18 | before-window best 6824, window best 6215 | PROGRESS: drt_violations improved 8.9 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 27.8 | drt_violations best 5073 last 5073 rows 15 | before-window best 8422, window best 5073 | PROGRESS: drt_violations improved 39.8 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 26.4 | drt_violations best 12935 last 12935 rows 12 | before-window best 21738, window best 12935 | PROGRESS: drt_violations improved 40.5 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 26.2 | drt_violations best 6879 last 6879 rows 14 | before-window best 13313, window best 6879 | PROGRESS: drt_violations improved 48.3 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-3807127 | slw_su_l1 | 5_2_route | 8.8 | drt_violations best 39810 last 39810 rows 5 | before-window best 279991, window best 39810 | PROGRESS: drt_violations improved 85.8 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 23.1 | drt_violations best 23437 last 23437 rows 10 | before-window best 93397, window best 23437 | PROGRESS: drt_violations improved 74.9 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 23.1 | drt_violations best 205 last 205 rows 20 | before-window best 266434, window best 205 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 23.1 | drt_violations best 7256 last 7256 rows 12 | before-window best 450083, window best 7256 | PROGRESS: drt_violations improved 98.4 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 23.1 | drt_violations best 8519 last 16569 rows 19 | before-window best 9525, window best 8519 | PROGRESS: drt_violations improved 10.6 % in window |  |
| epyc8 | prd-eco_20261125_114101_3990791-i1-3640861 | eco_20261125_114101_3990791-i1 | 5_2_route | 3.5 | drt_violations best 0 last 0 rows 2 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-3032686 | col_h9_r0_p4__t1 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-4053150 | col_h9_r1__t1 | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 10.4 | drt_violations best 1475 last 1475 rows 14 | before-window best 162909, window best 1475 | PROGRESS: drt_violations improved 99.1 % in window |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_2_route | 20.0 | drt_violations best 30892 last 30892 rows 12 | before-window best 62620, window best 30892 | PROGRESS: drt_violations improved 50.7 % in window |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 20.2 | drt_violations best 4 last 4 rows 53 | before-window best 2440, window best 4 | PROGRESS: drt_violations improved 99.8 % in window |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2686622 | col_h10_r0_p4__t1 | 4_2_tapbal_grt | 2.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 18.4 | drt_violations best 1 last 1 rows 42 | before-window best 38, window best 1 | PROGRESS: drt_violations improved 97.4 % in window |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 26.4 | drt_violations best 7268 last 7268 rows 10 | before-window best 104690, window best 7268 | PROGRESS: drt_violations improved 93.1 % in window |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 5_2_route | 17.0 | drt_violations best 26476 last 26476 rows 2 | before-window best 174940, window best 26476 | PROGRESS: drt_violations improved 84.9 % in window |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 21.6 | drt_violations best 901 last 1060 rows 20 | before-window best 96187, window best 901 | PROGRESS: drt_violations improved 99.1 % in window |  |
