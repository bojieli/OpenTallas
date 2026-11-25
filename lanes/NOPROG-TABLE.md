# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 05:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 2, 'GRT-LABEL': 9, 'YOUNG': 141, 'NO-DATA': 38, 'KEEP': 3, 'EXCLUDED': 1, 'PROGRESS': 32}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-phy_serdes-3657780 | phy_serdes | 5_1_grt | 3.3 | grt rounds 2 overflow 5:196122 -> 10:219751 | UNSIGNABLE: GRT overflow flat: overflow 196122 at iteration 5 -> 219751 at iteration 10: fla | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-cbn_q01__cldd6ea846-3490222 | cbn_q01 | tt_setup_repair_grt | 4.2 | repair_Viol best 661 last 661 rows 21 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -614.38 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-kv3_hg_v1p5-3496343 | kv3_hg_v1p5 | pregrt_ff_hold | 3.3 | repair_TNS best 809467 last 809467 rows 1 | before-window best 809467, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-D29 decides; never a |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | pregrt_ff_hold | 7.0 | repair_TNS best 127105 last 127105 rows 1 | before-window best 127105, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r877307f5d-1492582 | kv3_pc_v1 | 5_1_grt | 4.0 | grt rounds 2 overflow 5:24098 -> 10:14475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r8c9cba7ae-3297443 | kv3_pc_v1 | 5_1_grt | 3.4 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-kv3_pv-3805339 | kv3_pv | 5_1_grt | 1.4 | grt rounds 2 overflow 5:55206 -> 10:46293 | GRT-LABEL: DESIGN-FAIL: overflow 46293 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v3e-640390 | kv3_pv_v3e | 5_1_grt | 0.6 | grt rounds 2 overflow 5:86034 -> 10:53939 | GRT-LABEL: DESIGN-FAIL: overflow 53939 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v4n-2809393 | kv3_pv_v4n | 5_1_grt | 1.6 | grt rounds 2 overflow 5:24020 -> 10:16743 | GRT-LABEL: DESIGN-FAIL: overflow 16743 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | 5_1_grt | 16.1 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc11 | dpkit-kv3_pv_v8e-579863 | kv3_pv_v8e | 5_1_grt | 0.7 | grt rounds 2 overflow 5:88213 -> 10:73755 | GRT-LABEL: DESIGN-FAIL: overflow 73755 at round 10 > 1000 |  |
| epyc7 | dpkit-cbf_q00_s2-3518685 | cbf_q00_s2 | 5_1_grt | 7.4 | grt rounds 2 overflow 5:87022 -> 10:54031 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 5_1_grt | 13.1 | grt rounds 2 overflow 5:17977 -> 10:2858 | GRT-LABEL: DESIGN-FAIL: overflow 2858 at round 10 > 1000 |  |
| epyc10 | dpkit-hd_lep0N_w-3160116 | hd_lep0N_w | 5_2_route | 3.5 | drt_violations best 115480 last 115480 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p5-970860 | kv3_hg_v1p5 | 5_1_grt | 4.1 | last meaningful line 0.1 h ago (306/307 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v4-4881 | kv3_hgi_v4 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (4887/4887 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | 5_1_grt | 12.3 | repair_TNS best 2512.23 last 2512.23 rows 3 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-103808 | kv3_pc_v1 | 4_1_cts | 1.2 | last meaningful line 0.2 h ago (6464/6464 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl7f648944__r8e7d31598-4153558 | kv3_pc_v1 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (6668/6668 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-native59-3384403 | native59 | 5_2_route | 11.2 | last meaningful line 0.2 h ago (257/258 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 5_2_route | 19.0 | drt_violations best 30867 last 30867 rows 2 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | 5_2_route | 17.6 | drt_violations best 132028 last 132028 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2082061 | slw_st_a_v1 | 5_2_route | 3.9 | last meaningful line 0.1 h ago (258/259 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | otc-1191841-12698 | 1191841 | signoff | 2.6 | last meaningful line 2.5 h ago (3/3 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | otc-1471300-23748 | 1471300 | signoff | 2.5 | last meaningful line 2.3 h ago (3/3 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | otc-1762308-21603 | 1762308 | signoff | 2.4 | last meaningful line 2.3 h ago (3/3 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc10 | otc-2025541-6828 | 2025541 | signoff | 0.3 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | otc-2424957-5022 | 2424957 | signoff | 0.1 | last meaningful line 0.1 h ago (3/3 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_073109_4058437-i1-634237 | eco_20261125_073109_4058437-i1 | 5_1_grt | 0.9 | last meaningful line 0.3 h ago (296/360 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_112234_1159095-i1-1820297 | eco_20261125_112234_1159095-i1 | 5_2_route | 2.3 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Eo-871015 | kv3_hub_Eo | lec | 0.5 | LEC last write 0.1 h ago | YOUNG: evidence 0.5 h < 6 h |  |
| epyc11 | dpkit-kv3_hub_Wo-954396 | kv3_hub_Wo | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.1 h ago (41/41 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v5n-798731 | kv3_pv_v5n | lec | 0.5 | LEC last write 0.1 h ago | YOUNG: evidence 0.5 h < 6 h |  |
| epyc11 | dpkit-kv3_pv_v6n-721471 | kv3_pv_v6n | lec | 0.6 | LEC last write 0.1 h ago | YOUNG: evidence 0.6 h < 6 h |  |
| epyc11 | dpkit-sle_hc1__cl7d360508__pv97423966-915788 | sle_hc1 | 6_report | 15.5 | last meaningful line 0.1 h ago (71/71 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | 5_2_route | 10.5 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl19bb38ef-959635 | slw_su_c | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (275/275 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl92142dac-2960548 | slw_su_c | 5_1_grt | 6.8 | last meaningful line 0.5 h ago (286/1295 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | otc-141162-25188 | 141162 | lec | 2.8 | LEC last write 2.8 h ago | YOUNG: evidence 2.8 h < 6 h |  |
| epyc11 | otc-1616228-26288 | 1616228 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc11 | otc-3124125-30954 | 3124125 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc11 | otc-381902-2867 | 381902 | - | 4.7 |  | NO-DATA: no log found |  |
| epyc11 | prd-count-p1_tc-3146788 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_154417_1016084-i2-2211039 | eco_20261124_154417_1016084-i2 | 5_2_route | 3.8 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i2t-2255468 | eco_20261124_190641_1260390-i2t | 5_2_route | 3.8 | last meaningful line 0.1 h ago (282/283 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i2t-96653 | eco_20261124_200101_1087713-i2t | 5_2_route | 2.8 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_092112_274675-i1-1256057 | eco_20261125_092112_274675-i1 | 5_2_route | 4.3 | drt_violations best 11 last 11 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_120946_3832190-i1t-2887287 | eco_20261125_120946_3832190-i1t | 5_2_route | 1.6 | last meaningful line 0.2 h ago (130/130 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | prd-fin-2097287 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (70/70 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | so_1143382_ff_25251 | so_1143382_ff_25251 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc11 | so_1143382_tt_25251 | so_1143382_tt_25251 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc11 | so_1195349_ff_6915 | so_1195349_ff_6915 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (33/33 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | so_1195349_tt_6915 | so_1195349_tt_6915 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (33/33 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1520876 | col_h10_r0_p4__t1 | 5_1_grt | 1.4 | repair_Remaining best 113138 last 113138 rows 89 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc12 | dpkit-hd_lep0N-2152952 | hd_lep0N | 4_2_tapbal_grt | 3.2 | last meaningful line 1.8 h ago (48/51 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc12 | dpkit-kv3_hgi_v7-2529031 | kv3_hgi_v7 | 5_1_grt | 3.0 | last meaningful line 0.3 h ago (295/1299 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-4135984 | kv3_pc | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.1 h ago (61/61 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc_v1__cl4ea58a5c__r877307f5d-3969743 | kv3_pc_v1 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pv_v12-2339543 | kv3_pv_v12 | pregrt_ff_hold | 3.1 | repair_TNS best 33373.7 last 33373.7 rows 1 | YOUNG: evidence 1.0 h < 2.5 h |  |
| epyc12 | dpkit-sle_ctl__cla4f6f12f-2847382 | sle_ctl | 3_5_place_dp | 2.8 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc12 | dpkit-sle_st_a_v1__cl67389ecd-849428 | sle_st_a_v1 | postcts_gate_TT | 1.7 | last meaningful line -0.0 h ago (557/557 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-slw_st_a_v2__clf4365a62-2414803 | slw_st_a_v2 | postcts_gate_FF | 3.1 | last meaningful line 0.0 h ago (888/888 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | dpkit-slw_st_a_v2__clf4365a62-3737452 | slw_st_a_v2 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (6375/6375 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc12 | otc-1460135-77 | 1460135 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc12 | otc-1563210-13665 | 1563210 | tcl | 1.4 | last meaningful line 1.3 h ago (6/6 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc12 | otc-1748836-5524 | 1748836 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc12 | otc-2317128-10372 | 2317128 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc12 | otc-3293317-27322 | 3293317 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc12 | otc-3501458-13012 | 3501458 | drc_merged | 2.4 | last meaningful line 0.1 h ago (268/268 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc12 | otc-3513712-10766 | 3513712 | drc_merged | 0.6 | last meaningful line -0.0 h ago (959/959 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc12 | otc-351743-16220 | 351743 | hcpg_run | 0.2 | last meaningful line 0.2 h ago (10/10 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | otc-44157-16866 | 44157 | asbuilt.yosys | 0.3 | last meaningful line 0.0 h ago (136721/136721 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | otc-909449-8205 | 909449 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc12 | otc-911086-32202 | 911086 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc12 | otc-912039-17230 | 912039 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc12 | otc-913991-25740 | 913991 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc12 | otc-915219-290 | 915219 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc12 | otc-935018-3761 | 935018 | asbuilt.yosys | 0.0 | last meaningful line -0.0 h ago (374/374 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | otc-966902-13513 | 966902 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc12 | otc-967819-30046 | 967819 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc12 | otc-969893-28630 | 969893 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-kv3_hub_Wi-3068909 | kv3_hub_Wi | 3_3_place_gp | 1.9 | last meaningful line 0.2 h ago (511/511 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 4.0 | drt_violations best 156586 last 156586 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-3286653 | sle_st_a_v2 | 5_2_route | 4.0 | drt_violations best 21238 last 21238 rows 3 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2601551 | slw_st_a_v1 | 5_2_route | 4.3 | drt_violations best 33686 last 33686 rows 2 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | kqc-qfd_dv_s8_station_tail1_h15_n9_s11_bt3_synth0-668989 | qfd_dv_s8_station_tail1_h15_n9_s11_bt3_synth0 | generate_abstract | 1.0 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | kqc-qfd_dv_s8_station_tail1_h16_n9_s11_bt3_synth0-674332 | qfd_dv_s8_station_tail1_h16_n9_s11_bt3_synth0 | 6_report | 1.0 | last meaningful line 0.0 h ago (58/58 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | kqc-qfd_dv_s8_station_tail1_h17_n7_s8_bt3_synth0-673208 | qfd_dv_s8_station_tail1_h17_n7_s8_bt3_synth0 | 6_report | 1.0 | last meaningful line 0.0 h ago (58/58 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | kqc-qfd_dv_s8_station_tail1_h17_n9_s10_bt3_synth0-672122 | qfd_dv_s8_station_tail1_h17_n9_s10_bt3_synth0 | 6_report | 1.0 | last meaningful line 0.0 h ago (57/57 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_204708_4151707-i2t-1352759 | eco_20261124_204708_4151707-i2t | 5_2_route | 0.7 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-A | qcdrt-sc-A | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-B | qcdrt-sc-B | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-C | qcdrt-sc-C | - | 0.2 |  | NO-DATA: no log found |  |
| epyc2 | so_1649833_ff_96432 | so_1649833_ff_96432 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc2 | so_1649833_tt_96432 | so_1649833_tt_96432 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-coll_core-3493022 | coll_core | 5_1_grt | 4.2 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t2-3977371 | serdes__t2 | 1_2_yosys | 0.3 | last meaningful line 0.2 h ago (312/312 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | postcts_gate_TT | 7.4 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_1_grt | 4.2 | last meaningful line 0.1 h ago (2030/2065 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_1_grt | 4.2 | last meaningful line 0.0 h ago (2030/2036 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3817081 | sle_st_a_v2 | 5_2_route | 5.7 | drt_violations best 23860 last 23860 rows 2 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__clc6d66f5b-2521917 | sle_su_l1 | 5_2_route | 4.7 | last meaningful line 0.2 h ago (265/266 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_1_grt | 4.6 | last meaningful line 0.1 h ago (2042/2077 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 7.3 | last meaningful line 0.5 h ago (275/276 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-3807127 | slw_su_l1 | 5_2_route | 7.3 | drt_violations best 78889 last 78889 rows 3 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc7 | eco-abs-4054458 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.1 h ago (31/31 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | otc-2916017-13620 | 2916017 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc7 | otc-2938337-22499 | 2938337 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc7 | otc-2958007-4014 | 2958007 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc7 | otc-328889-26488 | 328889 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261124_192157_3493836-i2-1995832 | eco_20261124_192157_3493836-i2 | 5_2_route | 1.1 | last meaningful line 0.1 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_073945_2252980-i1-3230821 | eco_20261125_073945_2252980-i1 | 5_2_route | 2.4 | last meaningful line 0.1 h ago (259/260 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_094206_1890550-i1-4068402 | eco_20261125_094206_1890550-i1 | 5_2_route | 4.0 | drt_violations best 65 last 65 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_103149_2129512-i1-1443376 | eco_20261125_103149_2129512-i1 | 5_2_route | 3.2 | drt_violations best 36 last 36 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_110124_1979736-i1-2551803 | eco_20261125_110124_1979736-i1 | 5_2_route | 2.7 | drt_violations best 265 last 265 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | prd-fin-2944509 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-918588 | col_h10_r0_p1__t1 | 4_2_tapbal_grt | 1.5 | last meaningful line 0.5 h ago (62/70 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_mu_C__t1-730122 | dsdv_slice_lepe_mu_C__t1 | 1_1_yosys_canonicalize | 1.6 | last meaningful line 0.3 h ago (130/130 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v3n-2522162 | kv3_pv_v3n | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (8543/8543 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | otc-132122-8685 | 132122 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-1321249-29104 | 1321249 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_025941_3548303-i2t-3977758 | eco_20261125_025941_3548303-i2t | 5_1_grt | 0.6 | last meaningful line 0.1 h ago (292/361 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_082653_3900765-i2-3480940 | eco_20261125_082653_3900765-i2 | 5_1_grt | 0.8 | last meaningful line 0.3 h ago (291/516 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_110931_3969969-i1-1922478 | eco_20261125_110931_3969969-i1 | 5_2_route | 2.6 | drt_violations best 39 last 39 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_114101_3990791-i1-3640861 | eco_20261125_114101_3990791-i1 | 5_2_route | 2.0 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_114445_3946237-i1-3788521 | eco_20261125_114445_3946237-i1 | 5_2_route | 2.0 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_120022_4021525-i1-420704 | eco_20261125_120022_4021525-i1 | 5_2_route | 1.7 | last meaningful line 0.0 h ago (260/260 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_121517_3981660-i1-1143996 | eco_20261125_121517_3981660-i1 | 5_2_route | 1.5 | last meaningful line 0.2 h ago (128/128 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_122258_3982108-i1-1582033 | eco_20261125_122258_3982108-i1 | 5_2_route | 1.3 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_123046_4033426-i1-1985482 | eco_20261125_123046_4033426-i1 | 5_2_route | 1.2 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_123952_3914547-i1-2528575 | eco_20261125_123952_3914547-i1 | 5_2_route | 1.0 | last meaningful line 0.0 h ago (118/118 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-fin-378808 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | relec-r2-U1_hc3_pv39aac7a1 | relec-r2-U1_hc3_pv39aac7a1 | - | 3.5 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-col-h9-r2--t1--clce45cab5--pv8b5a5980-grt-2162168 | col-h9-r2--t1--clce45cab5--pv8b5a5980-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t32-grt-1790755 | ot-s81sl-leaf--t32-grt | lec | 0.1 | LEC last write 0.0 h ago | YOUNG: evidence 0.1 h < 6 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 5_1_grt | 7.0 | last meaningful line 0.7 h ago (269/1282 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-296584 | col_h9_r0_p3__t1 | 5_1_grt | 9.6 | last meaningful line 1.0 h ago (272/1299 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3698869 | col_h9_r0_p4__t1 | 5_1_grt | 4.9 | last meaningful line 0.2 h ago (273/1279 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-3032686 | col_h9_r0_p4__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 46921.2 last 46921.2 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | postcts_gate_TT | 7.0 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-4053150 | col_h9_r1__t1 | pregrt_ff_hold | 4.2 | repair_TNS best 53812.2 last 53812.2 rows 1 | YOUNG: evidence 1.1 h < 2.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv31e47bd5-4047516 | col_h9_r2__t1 | lec | 4.2 | LEC last write 0.0 h ago | YOUNG: evidence 4.2 h < 6 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 8.9 | drt_violations best 5145 last 5145 rows 8 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-3394850 | col_h9_r2__t1 | 5_2_route | 7.1 | drt_violations best 157585 last 157585 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-3707756 | col_h9_r2__t1 | 5_2_route | 7.0 | drt_violations best 159317 last 159317 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve0486b40-3725060 | col_h9_r2__t1 | 5_2_route | 4.9 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | 5_2_route | 8.0 | drt_violations best 5620 last 5620 rows 5 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t7-3863913 | dsdv_slice_c1x_C__t7 | 1_1_yosys_canonicalize | 1.3 | last meaningful line 0.2 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_kv512_C__t1-4058196 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 4.2 | last meaningful line 1.8 h ago (37/37 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-3479533 | slice_station__t37 | 5_2_route | 4.9 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t42__clcf44e680-3472830 | slice_station__t42 | 5_2_route | 4.9 | drt_violations best 19242 last 19242 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t43-3486441 | slice_station__t43 | lec | 4.9 | LEC last write 0.0 h ago | YOUNG: evidence 4.9 h < 6 h |  |
| epyc9 | dpkit-slice_station__t52-2620358 | slice_station__t52 | postcts_gate_FF | 3.7 | last meaningful line 0.0 h ago (1350/1350 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | so_2848329_ff_36721 | so_2848329_ff_36721 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | so_2848329_tt_36721 | so_2848329_tt_36721 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2686622 | col_h10_r0_p4__t1 | 4_2_tapbal_grt | 0.9 | last meaningful line 0.0 h ago (63/65 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 4_2_tapbal_grt | 0.9 | last meaningful line 0.0 h ago (63/65 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 4_2_tapbal_grt | 0.8 | last meaningful line 0.1 h ago (61/64 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 4_2_tapbal_grt | 0.7 | last meaningful line 0.0 h ago (61/64 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 4_2_tapbal_grt | 0.9 | last meaningful line 0.1 h ago (61/65 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-2360794 | col_h9_r2__t1 | tt_setup_measure | 1.0 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pva119e808-2308652 | col_h9_r2__t1 | hold_gate | 1.0 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1177242 | kv3_hg_v1p3__r838481cd7 | 5_1_grt | 6.1 | last meaningful line 1.5 h ago (288/1295 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_sys_c-4063347 | kv3_sys_c | 5_1_grt | 2.7 | last meaningful line 0.0 h ago (1143/1143 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | generate_abstract | 20.6 | last meaningful line 0.2 h ago (29/29 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 5_2_route | 12.7 | last meaningful line 0.2 h ago (131/131 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 5_2_route | 17.0 | drt_violations best 138407 last 138407 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t27-4040446 | slice_station__t27 | 5_1_grt | 2.7 | last meaningful line 0.1 h ago (634/664 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | postcts_gate_FF | 14.4 | last meaningful line 0.3 h ago (1805/1805 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 5_2_route | 15.5 | drt_violations best 174940 last 174940 rows 1 | YOUNG: evidence 6.2 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 5_2_route | 15.2 | last meaningful line 0.2 h ago (129/129 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | otc-3504566-18256 | 3504566 | flow | 2.8 | last meaningful line 0.1 h ago (3137/3137 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i3t-2681077 | eco_20261123_191853_2879776-i3t | 5_2_route | 2.9 | last meaningful line 0.2 h ago (135/135 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1t-3347319 | eco_20261125_002226_1452841-i1t | 5_2_route | 5.3 | drt_violations best 9407 last 9407 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | prd-eco_20261125_040243_2843749-i1-851245 | eco_20261125_040243_2843749-i1 | 5_2_route | 1.6 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | so_163869_ff_29754 | so_163869_ff_29754 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | so_163869_tt_29754 | so_163869_tt_29754 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | so_78775_ff_69145 | so_78775_ff_69145 | signoff | 0.2 |  | NO-DATA: empty log |  |
| intel1 | so_78775_tt_69145 | so_78775_tt_69145 | signoff | 0.2 |  | NO-DATA: empty log |  |
| intel2 | dpkit-coll_ftm-2001265 | coll_ftm | 5_2_route | 1.2 | last meaningful line 0.1 h ago (230/231 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-hd_serdes-3275033 | hd_serdes | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4394/4394 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-2000314 | kv3_io_ft | 5_2_route | 1.2 | drt_violations best 5442 last 5442 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | dpkit-kv3_pv_v12e-1190106 | kv3_pv_v12e | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v6e-3555492 | kv3_pv_v6e | 3_1_place_gp_skip_io | 0.3 | overflow best 0.5297 last 0.5297 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-2092944 | slice_station__t12 | abstract_exact | 1.2 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | otc-2407048-21046 | 2407048 | signoff | 0.5 | last meaningful line 0.5 h ago (3/3 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-1955823 | kv3_hgi | 5_2_route | 3.9 |  | KEEP: kv3_hgi_1124155644	KV-OWN-RSTREACH	combined HEADLEG2+HGI-LEAF ship form; noprog  |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-436421 | kv3_hgi_v2 | 5_1_grt | 4.2 |  | KEEP: kv3_hgi_v2__cl2862d491_1124155702	KV-OWN-RSTREACH	combined hgi_v2 ship form (COO |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pvb2cd22a7-3043152 | col_h9_r2__t1 | pregrt_ff_hold | 2.8 |  | KEEP: col_h9_r2__t1__clb8d86cd5__pvb2cd22a7	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-eco_qcgu_1125-i1-3514577 | eco_qcgu_1125-i1 | 5_2_route | 5.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_2_route | 20.0 | drt_violations best 121450 last 121450 rows 3 | before-window best 416066, window best 121450 | PROGRESS: drt_violations improved 70.8 % in window |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 18.9 | drt_violations best 1499 last 1499 rows 15 | before-window best 272423, window best 1499 | PROGRESS: drt_violations improved 99.4 % in window |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_2_route | 18.9 | drt_violations best 109612 last 109612 rows 2 | before-window best 378938, window best 109612 | PROGRESS: drt_violations improved 71.1 % in window |  |
| epyc11 | dpkit-kv3_hg_v3-561930 | kv3_hg_v3 | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc11 | dpkit-kv3_pv_v5-1052229 | kv3_pv_v5 | pregrt_ff_hold | 4.4 | repair_Violations best 21900 last 21906 rows 129 | before-window best 240292, window best 21900 | PROGRESS: repair_Violations improved 90.9 % in window |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 20.2 | drt_violations best 76 last 76 rows 20 | before-window best 329677, window best 76 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 25.0 | drt_violations best 6215 last 33693 rows 18 | before-window best 7058, window best 6215 | PROGRESS: drt_violations improved 11.9 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 45.4 | drt_violations best 5263 last 5263 rows 24 | before-window best 7726, window best 5263 | PROGRESS: drt_violations improved 31.9 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 30.1 | drt_violations best 2761 last 5839 rows 19 | before-window best 2818, window best 2761 | PROGRESS: drt_violations improved 2.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 26.3 | drt_violations best 5691 last 5691 rows 14 | before-window best 12303, window best 5691 | PROGRESS: drt_violations improved 53.7 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 24.9 | drt_violations best 15333 last 15333 rows 11 | before-window best 90589, window best 15333 | PROGRESS: drt_violations improved 83.1 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 24.7 | drt_violations best 7139 last 7139 rows 13 | before-window best 23191, window best 7139 | PROGRESS: drt_violations improved 69.2 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-534954 | slw_su_l1 | tt_setup_repair_grt | 6.9 | repair_Violations best 0 last 0 rows 46 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_2_route | 21.6 | drt_violations best 7391 last 7391 rows 10 | before-window best 320246, window best 7391 | PROGRESS: drt_violations improved 97.7 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 21.6 | drt_violations best 24770 last 24770 rows 9 | before-window best 122835, window best 24770 | PROGRESS: drt_violations improved 79.8 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 21.6 | drt_violations best 3421 last 3421 rows 10 | before-window best 266434, window best 3421 | PROGRESS: drt_violations improved 98.7 % in window |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 21.6 | drt_violations best 12797 last 12797 rows 10 | before-window best 450083, window best 12797 | PROGRESS: drt_violations improved 97.2 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 21.6 | drt_violations best 8519 last 40739 rows 18 | before-window best 10226, window best 8519 | PROGRESS: drt_violations improved 16.7 % in window |  |
| epyc8 | prd-eco_20261125_104318_3955073-i1t-474220 | eco_20261125_104318_3955073-i1t | 5_2_route | 3.0 | drt_violations best 0 last 0 rows 4 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pvf1445dce-2628247 | col_h9_r2__t1 | 5_1_grt | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_2_route | 18.5 | drt_violations best 36163 last 36163 rows 11 | before-window best 162913, window best 36163 | PROGRESS: drt_violations improved 77.8 % in window |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 18.7 | drt_violations best 4 last 4 rows 48 | before-window best 65686, window best 4 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | 4_2_tapbal_grt | 0.9 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | 4_2_tapbal_grt | 0.8 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 4_2_tapbal_grt | 0.8 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 16.9 | drt_violations best 1 last 1 rows 40 | before-window best 58, window best 1 | PROGRESS: drt_violations improved 98.3 % in window |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 24.9 | drt_violations best 8323 last 8323 rows 8 | before-window best 398476, window best 8323 | PROGRESS: drt_violations improved 97.9 % in window |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | 5_2_route | 16.7 | drt_violations best 8981 last 8981 rows 3 | before-window best 104717, window best 8981 | PROGRESS: drt_violations improved 91.4 % in window |  |
| intel1 | prd-eco_20261125_020407_3088231-i1-2998029 | eco_20261125_020407_3088231-i1 | 5_2_route | 3.6 | drt_violations best 0 last 0 rows 4 | PROGRESS: drt_violations reached 0 |  |
| intel1 | prd-eco_20261125_050013_1448739-i1-3109373 | eco_20261125_050013_1448739-i1 | 5_1_grt | 0.7 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 20.1 | drt_violations best 901 last 901 rows 17 | before-window best 367946, window best 901 | PROGRESS: drt_violations improved 99.8 % in window |  |
