# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 06:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'GRT-LABEL': 10, 'YOUNG': 150, 'NO-DATA': 33, 'KEEP': 3, 'EXCLUDED': 1, 'PROGRESS': 34}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc8 | dpkit-kv3_hg_v1p5-3496343 | kv3_hg_v1p5 | pregrt_ff_hold | 4.3 | repair_TNS best 809467 last 809467 rows 1 | before-window best 809467, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (KV-D29 decides; never a |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-3032686 | col_h9_r0_p4__t1 | pregrt_ff_hold | 3.8 | repair_TNS best 46921.2 last 46921.2 rows 1 | before-window best 46921.2, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv3a0a8b60-4053150 | col_h9_r1__t1 | pregrt_ff_hold | 5.2 | repair_TNS best 53812.2 last 53812.2 rows 1 | before-window best 53812.2, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| epyc11 | dpkit-kv3_hg_v3-561930 | kv3_hg_v3 | 5_1_grt | 1.7 | grt rounds 2 overflow 5:48439 -> 10:42500 | GRT-LABEL: DESIGN-FAIL: overflow 42500 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v2-1828900 | kv3_pv_v2 | 5_1_grt | 1.0 | grt rounds 2 overflow 5:63965 -> 10:48975 | GRT-LABEL: DESIGN-FAIL: overflow 48975 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v3e-640390 | kv3_pv_v3e | 5_1_grt | 1.6 | grt rounds 2 overflow 5:86034 -> 10:53939 | GRT-LABEL: DESIGN-FAIL: overflow 53939 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v5ne-271864 | kv3_pv_v5ne | 5_1_grt | 17.1 | grt rounds 1 overflow 5:74746 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc11 | dpkit-kv3_pv_v6n-721471 | kv3_pv_v6n | 5_1_grt | 1.6 | grt rounds 2 overflow 5:45246 -> 10:35967 | GRT-LABEL: DESIGN-FAIL: overflow 35967 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v8-2209532 | kv3_pv_v8 | 5_1_grt | 0.8 | grt rounds 2 overflow 5:37272 -> 10:15899 | GRT-LABEL: DESIGN-FAIL: overflow 15899 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v8e-579863 | kv3_pv_v8e | 5_1_grt | 1.7 | grt rounds 2 overflow 5:88213 -> 10:73755 | GRT-LABEL: DESIGN-FAIL: overflow 73755 at round 10 > 1000 |  |
| epyc11 | dpkit-slw_su_c__cl92142dac-2960548 | slw_su_c | 5_1_grt | 7.8 | grt rounds 2 overflow 5:21500 -> 10:14785 | GRT-LABEL: DESIGN-FAIL: overflow 14785 at round 10 > 1000 |  |
| epyc7 | dpkit-cbf_q00_s2-3518685 | cbf_q00_s2 | 5_1_grt | 8.4 | grt rounds 2 overflow 5:87022 -> 10:54031 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 5_1_grt | 14.1 | grt rounds 2 overflow 5:17977 -> 10:2858 | GRT-LABEL: DESIGN-FAIL: overflow 2858 at round 10 > 1000 |  |
| epyc10 | ap-ageom-kw-phy-ucie-kv-grt-672098 | phy-ucie-kv-grt | 3_5_place_dp | 0.0 | repair_Violations best 96836 last 96836 rows 6 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-hd_lep0N_w-3160116 | hd_lep0N_w | 5_2_route | 4.5 | drt_violations best 17831 last 17831 rows 2 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p5-970860 | kv3_hg_v1p5 | 5_1_grt | 5.1 | last meaningful line 1.0 h ago (306/1312 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v4-4881 | kv3_hgi_v4 | 5_1_grt | 2.2 | last meaningful line 0.1 h ago (293/295 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | 5_1_grt | 13.3 | repair_TNS best 1043.07 last 1043.07 rows 2 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl4ea58a5c__r828e1c2a5-103808 | kv3_pc_v1 | 4_1_cts | 2.2 | last meaningful line 0.0 h ago (6686/6686 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pc_v1__cl7f648944__r8e7d31598-4153558 | kv3_pc_v1 | 4_1_cts | 2.2 | last meaningful line 0.1 h ago (6780/6780 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv-3805339 | kv3_pv | postcts_gate_TT | 2.4 | last meaningful line 0.0 h ago (610/610 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-native59-3384403 | native59 | 5_2_route | 12.2 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc10 | dpkit-phy_serdes_b-634198 | phy_serdes_b | 3_3_place_gp | 0.0 | overflow best 0.9955 last 0.9955 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-1456796 | slw_hc1 | 5_2_route | 18.6 | drt_violations best 13600 last 13600 rows 3 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2082061 | slw_st_a_v1 | 5_2_route | 4.9 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | otc-1762308-21603 | 1762308 | signoff | 3.4 | last meaningful line 3.3 h ago (3/3 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc10 | otc-2025541-6828 | 2025541 | signoff | 1.3 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | otc-2424957-5022 | 2424957 | signoff | 1.1 | last meaningful line 1.0 h ago (3/3 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_073109_4058437-i1-634237 | eco_20261125_073109_4058437-i1 | 5_2_route | 1.9 | last meaningful line 0.0 h ago (264/264 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_112234_1159095-i1-1820297 | eco_20261125_112234_1159095-i1 | 5_2_route | 3.3 | drt_violations best 10 last 10 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc11 | ap-ageom-kw-slw-su-c--cl19bb38ef-grt-3773382 | slw-su-c--cl19bb38ef-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-cbn_q00__cl622f65d2-2378800 | cbn_q00 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (5366/5366 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Eo-871015 | kv3_hub_Eo | 3_3_place_gp | 1.5 | overflow best 0.0994 last 0.0994 rows 46 | YOUNG: stage 0.6 h < 1 h |  |
| epyc11 | dpkit-kv3_hub_Wo-954396 | kv3_hub_Wo | 3_3_place_gp | 1.4 | overflow best 0.0987 last 0.0995 rows 95 | YOUNG: stage 0.6 h < 1 h |  |
| epyc11 | dpkit-kv3_pv_v5-1052229 | kv3_pv_v5 | 5_1_grt | 5.4 | last meaningful line 0.3 h ago (272/1276 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v5n-798731 | kv3_pv_v5n | lec | 1.5 | LEC last write 0.9 h ago | YOUNG: evidence 1.5 h < 6 h |  |
| epyc11 | dpkit-sle_su_c-2485454 | sle_su_c | 3_3_place_gp | 0.6 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | 5_2_route | 11.5 | drt_violations best 141406 last 141406 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc11 | eco-abs-3833269 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (1024/1024 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | otc-1616228-26288 | 1616228 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc11 | otc-1830932-23851 | 1830932 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc11 | otc-3124125-30954 | 3124125 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc11 | otc-381902-2867 | 381902 | - | 5.7 |  | NO-DATA: no log found |  |
| epyc11 | prd-eco_20261124_190641_1260390-i2t-2255468 | eco_20261124_190641_1260390-i2t | 5_2_route | 4.8 | drt_violations best 5541 last 5541 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i2t-96653 | eco_20261124_200101_1087713-i2t | 5_2_route | 3.8 | drt_violations best 4960 last 4960 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_120946_3832190-i1t-2887287 | eco_20261125_120946_3832190-i1t | 5_2_route | 2.6 | drt_violations best 1170 last 1170 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_141555_518460-i1-2852121 | eco_20261125_141555_518460-i1 | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (141/141 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | prd-fin-1256057 | fin | 6_report | 0.3 | last meaningful line 0.0 h ago (76/76 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | so_2769490_ff_50881 | so_2769490_ff_50881 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc11 | so_2769490_tt_50881 | so_2769490_tt_50881 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc11 | so_2943995_ff_32901 | so_2943995_ff_32901 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (35/35 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | so_2943995_tt_32901 | so_2943995_tt_32901 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (35/35 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc11 | so_3691111_ff_59809 | so_3691111_ff_59809 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (35/35 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | so_3691111_tt_59809 | so_3691111_tt_59809 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (35/35 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dpkit-hd_lep0N-2152952 | hd_lep0N | 4_2_tapbal_grt | 4.2 | last meaningful line 2.8 h ago (48/53 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc12 | dpkit-kv3_hgi_v7-2529031 | kv3_hgi_v7 | 5_1_grt | 4.0 | last meaningful line 1.3 h ago (295/1302 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-4135984 | kv3_pc | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | dpkit-kv3_pv_v12-2339543 | kv3_pv_v12 | 5_1_grt | 4.1 | last meaningful line 0.2 h ago (157/157 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc12 | dpkit-sle_st_a_v1__cl67389ecd-849428 | sle_st_a_v1 | postcts_gate_FF | 2.7 | last meaningful line 0.0 h ago (1075/1075 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc12 | dpkit-slw_st_a_v2__clf4365a62-2414803 | slw_st_a_v2 | 5_2_route | 4.1 | last meaningful line 0.2 h ago (258/259 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 3.4 |  | NO-DATA: no log found |  |
| epyc12 | otc-1273822-29690 | 1273822 | drc_merged | 0.9 | last meaningful line 0.0 h ago (164/164 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc12 | otc-1275997-12067 | 1275997 | drc_macros_only | 0.9 | last meaningful line 0.0 h ago (320/320 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc12 | otc-1278426-9051 | 1278426 | drc_parent_only | 0.9 | last meaningful line 0.0 h ago (176/176 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc12 | otc-1291490-1984 | 1291490 | drc_parent_only | 0.9 | last meaningful line 0.0 h ago (176/176 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc12 | otc-1294027-30241 | 1294027 | drc_parent_only | 0.9 | last meaningful line 0.1 h ago (176/176 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc12 | otc-1305696-4661 | 1305696 | drc_parent_only | 0.9 | last meaningful line 0.0 h ago (188/188 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc12 | otc-1308959-15081 | 1308959 | drc_macros_only | 0.9 | last meaningful line 0.0 h ago (215/215 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc12 | otc-1312023-14782 | 1312023 | drc_macros_only | 0.9 | last meaningful line 0.0 h ago (209/209 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc12 | otc-1314683-28749 | 1314683 | drc_macros_only | 0.9 | last meaningful line 0.0 h ago (209/209 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc12 | otc-1319124-12976 | 1319124 | drc_parent_only | 0.9 | last meaningful line 0.0 h ago (347/347 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc12 | otc-1321394-11555 | 1321394 | drc_parent_only | 0.9 | last meaningful line 0.0 h ago (572/572 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc12 | otc-1324644-27944 | 1324644 | drc_parent_only | 0.9 | last meaningful line 0.0 h ago (494/494 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc12 | otc-1338915-16694 | 1338915 | drc_macros_only | 0.9 | last meaningful line 0.0 h ago (209/209 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc12 | otc-1460135-77 | 1460135 | - | 2.5 |  | NO-DATA: no log found |  |
| epyc12 | otc-1994529-22240 | 1994529 | flow | 0.5 | last meaningful line 0.0 h ago (2713/2713 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc12 | otc-1995249-22339 | 1995249 | flow | 0.5 | last meaningful line 0.0 h ago (2709/2709 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc12 | otc-3293317-27322 | 3293317 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc12 | otc-3501458-13012 | 3501458 | drc_merged | 3.4 | last meaningful line 0.3 h ago (334/334 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc12 | otc-351743-16220 | 351743 | hcpg_run | 1.2 | last meaningful line 0.8 h ago (13/13 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Wi-3068909 | kv3_hub_Wi | 3_3_place_gp | 2.9 | overflow best 0.0983 last 0.0983 rows 49 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 5.0 | drt_violations best 2904 last 2904 rows 4 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2601551 | slw_st_a_v1 | 5_2_route | 5.3 | drt_violations best 513 last 513 rows 11 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | otc-2770137-14837 | 2770137 | signoff | 0.9 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_204708_4151707-i2t-1352759 | eco_20261124_204708_4151707-i2t | 5_2_route | 1.7 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 1.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 1.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 1.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-A | qcdrt-sc-A | - | 1.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-B | qcdrt-sc-B | - | 1.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-C | qcdrt-sc-C | - | 1.2 |  | NO-DATA: no log found |  |
| epyc2 | so_3264258_ff_69507 | so_3264258_ff_69507 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_3264258_tt_69507 | so_3264258_tt_69507 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-serdes__t2-3977371 | serdes__t2 | lec | 1.3 | LEC last write 0.1 h ago | YOUNG: evidence 1.3 h < 6 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | 4_1_cts | 1.3 | last meaningful line 0.5 h ago (10800/10800 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 4_1_cts | 1.0 | last meaningful line 0.2 h ago (5067/5067 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | postcts_gate_TT | 8.4 | last meaningful line 0.2 h ago (824/824 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | postcts_gate_TT | 5.2 | last meaningful line 0.0 h ago (1920/1920 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | postcts_gate_TT | 5.2 | last meaningful line 0.1 h ago (964/964 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3817081 | sle_st_a_v2 | 5_2_route | 6.7 | drt_violations best 141 last 141 rows 16 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__clc6d66f5b-2521917 | sle_su_l1 | 5_2_route | 5.7 | drt_violations best 237032 last 237032 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | postcts_gate_TT | 5.6 | last meaningful line 0.0 h ago (2195/2195 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 8.3 | last meaningful line 0.5 h ago (281/282 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-3807127 | slw_su_l1 | 5_2_route | 8.3 | drt_violations best 45479 last 45479 rows 4 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc7 | eco-abs-718120 | eco-abs | generate_abstract | 0.8 | last meaningful line 0.4 h ago (31/31 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | otc-2858837-8104 | 2858837 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | otc-2916017-13620 | 2916017 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc7 | otc-2938337-22499 | 2938337 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc7 | otc-2958007-4014 | 2958007 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc7 | otc-740568-7161 | 740568 | drc_parent_only | 0.8 | last meaningful line 0.1 h ago (176/176 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | otc-830728-15409 | 830728 | drc_parent_only | 0.8 | last meaningful line 0.0 h ago (176/176 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | otc-831702-28906 | 831702 | drc_parent_only | 0.8 | last meaningful line 0.1 h ago (176/176 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | otc-833865-16155 | 833865 | drc_parent_only | 0.8 | last meaningful line 0.1 h ago (176/176 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | otc-835730-18044 | 835730 | drc_parent_only | 0.8 | last meaningful line 0.0 h ago (266/266 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | otc-838804-29233 | 838804 | drc_macros_only | 0.8 | last meaningful line 0.0 h ago (272/272 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | prd-count-p1_tc-1443376 | count-p1_tc | prd_count_p1_tc | 0.3 | last meaningful line 0.1 h ago (46/46 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-count-p1_tc-4068402 | count-p1_tc | prd_count_p1_tc | 0.2 | last meaningful line 0.1 h ago (45/45 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_192157_3493836-i2-1995832 | eco_20261124_192157_3493836-i2 | 5_2_route | 2.1 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_073945_2252980-i1-3230821 | eco_20261125_073945_2252980-i1 | 5_2_route | 3.4 | drt_violations best 6509 last 6509 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261125_110124_1979736-i1-2551803 | eco_20261125_110124_1979736-i1 | 5_2_route | 3.7 | drt_violations best 39 last 39 rows 3 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_mu_C__t1-730122 | dsdv_slice_lepe_mu_C__t1 | 1_2_yosys | 2.6 | last meaningful line 0.0 h ago (411/411 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v3n-2522162 | kv3_pv_v3n | 4_1_cts | 2.0 | last meaningful line 0.1 h ago (8646/8646 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | otc-132122-8685 | 132122 | - | 2.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-1321249-29104 | 1321249 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_025941_3548303-i2t-3977758 | eco_20261125_025941_3548303-i2t | 5_2_route | 1.6 | last meaningful line 0.0 h ago (270/271 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_082653_3900765-i2-3480940 | eco_20261125_082653_3900765-i2 | 5_2_route | 1.8 | last meaningful line 0.1 h ago (271/272 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_104318_3955073-i1-65595 | eco_20261125_104318_3955073-i1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_114101_3990791-i1-3640861 | eco_20261125_114101_3990791-i1 | 5_2_route | 3.0 | drt_violations best 1 last 1 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_114445_3946237-i1-3788521 | eco_20261125_114445_3946237-i1 | 5_3_fillcell | 3.0 | last meaningful line 0.1 h ago (21/21 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_120022_4021525-i1-420704 | eco_20261125_120022_4021525-i1 | 5_2_route | 2.7 | drt_violations best 11 last 11 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_121517_3981660-i1-1143996 | eco_20261125_121517_3981660-i1 | 5_2_route | 2.5 | drt_violations best 27 last 27 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_122258_3982108-i1-1582033 | eco_20261125_122258_3982108-i1 | 5_2_route | 2.3 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_123046_4033426-i1-1985482 | eco_20261125_123046_4033426-i1 | 5_2_route | 2.2 | drt_violations best 18 last 18 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_123952_3914547-i1-2528575 | eco_20261125_123952_3914547-i1 | 5_2_route | 2.0 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | prd-fin-1922478 | fin | 6_report | 0.3 | last meaningful line 0.2 h ago (20/20 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | so_3837205_ff_7995 | so_3837205_ff_7995 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (35/35 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | so_3837205_tt_7995 | so_3837205_tt_7995 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (35/35 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 5_1_grt | 8.0 | repair_Remaining best 145033 last 145033 rows 58 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-296584 | col_h9_r0_p3__t1 | 5_1_grt | 10.6 | last meaningful line 2.0 h ago (272/1316 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3698869 | col_h9_r0_p4__t1 | 5_1_grt | 5.9 | last meaningful line 0.0 h ago (160/160 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 8.0 | last meaningful line 0.0 h ago (271/271 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pvf1445dce-2628247 | col_h9_r2__t1 | 5_2_route | 4.6 | last meaningful line 0.1 h ago (263/263 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv31e47bd5-4047516 | col_h9_r2__t1 | 5_2_route | 5.2 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-3394850 | col_h9_r2__t1 | 5_2_route | 8.1 | drt_violations best 33177 last 33177 rows 2 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-3707756 | col_h9_r2__t1 | 5_2_route | 8.0 | drt_violations best 21314 last 21314 rows 3 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve0486b40-3725060 | col_h9_r2__t1 | 5_2_route | 5.9 | drt_violations best 155476 last 155476 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | 5_2_route | 9.0 | drt_violations best 2982 last 2982 rows 10 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t7-3863913 | dsdv_slice_c1x_C__t7 | 1_1_yosys_canonicalize | 2.3 | last meaningful line 1.0 h ago (131/131 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_kv512_C__t1-4058196 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 5.2 | last meaningful line 2.8 h ago (37/37 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-3479533 | slice_station__t37 | 5_2_route | 5.9 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t43-3486441 | slice_station__t43 | 5_2_route | 5.9 | drt_violations best 34635 last 34635 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-2620358 | slice_station__t52 | 5_2_route | 4.7 | last meaningful line 0.1 h ago (256/257 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | otc-1865534-29853 | 1865534 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc9 | so_3668847_ff_18933 | so_3668847_ff_18933 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | so_3668847_tt_18933 | so_3668847_tt_18933 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2686622 | col_h10_r0_p4__t1 | 4_2_tapbal_grt | 1.9 | last meaningful line 0.0 h ago (175/175 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.8 | last meaningful line 1.0 h ago (61/76 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.7 | last meaningful line 1.0 h ago (61/75 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.9 | last meaningful line 1.0 h ago (61/76 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | pregrt_ff_hold | 1.9 | repair_TNS best 63490.2 last 63490.2 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | pregrt_ff_hold | 1.8 | repair_TNS best 51207.7 last 51207.7 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | pregrt_ff_hold | 1.8 | repair_TNS best 60746.9 last 60746.9 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-2360794 | col_h9_r2__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 118766 last 118766 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pva119e808-2308652 | col_h9_r2__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 79800.3 last 79800.3 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1177242 | kv3_hg_v1p3__r838481cd7 | 5_1_grt | 7.1 | last meaningful line 2.5 h ago (288/1296 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_sys_c-4063347 | kv3_sys_c | 5_1_grt | 3.7 | last meaningful line 0.5 h ago (2292/2908 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 5_2_route | 13.7 | last meaningful line 0.5 h ago (263/264 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 5_2_route | 18.0 | drt_violations best 138407 last 138407 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t27-4040446 | slice_station__t27 | 5_2_route | 3.7 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 15.4 | last meaningful line 0.3 h ago (132/132 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-48184 | slw_hc2 | generate_abstract | 17.7 | last meaningful line 0.1 h ago (27/27 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 5_2_route | 16.2 | last meaningful line 0.3 h ago (262/262 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | otc-2590726-12039 | 2590726 | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | otc-394619-19736 | 394619 | - | 1.0 |  | NO-DATA: no log found |  |
| intel1 | otc-395802-17368 | 395802 | - | 1.0 |  | NO-DATA: no log found |  |
| intel1 | otc-574655-9239 | 574655 | drc_macros_only | 0.9 | last meaningful line 0.1 h ago (194/194 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | otc-578793-24959 | 578793 | drc_macros_only | 0.9 | last meaningful line 0.0 h ago (668/668 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | otc-582965-3828 | 582965 | drc_macros_only | 0.9 | last meaningful line 0.0 h ago (677/677 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | otc-586189-14994 | 586189 | drc_macros_only | 0.9 | last meaningful line 0.0 h ago (743/743 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | otc-589045-16647 | 589045 | drc_macros_only | 0.9 | last meaningful line 0.0 h ago (209/209 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | otc-591807-6566 | 591807 | drc_merged | 0.9 | last meaningful line 0.0 h ago (506/506 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i3t-2681077 | eco_20261123_191853_2879776-i3t | 5_2_route | 3.9 | last meaningful line 0.5 h ago (281/282 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1t-3347319 | eco_20261125_002226_1452841-i1t | 5_2_route | 6.3 | drt_violations best 9407 last 9407 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | prd-eco_20261125_040243_2843749-i1-851245 | eco_20261125_040243_2843749-i1 | 5_2_route | 2.6 | last meaningful line 0.3 h ago (265/265 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i1-3109373 | eco_20261125_050013_1448739-i1 | 5_2_route | 1.7 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | so_2073985_ff_3880 | so_2073985_ff_3880 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (45/45 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | so_2073985_tt_3880 | so_2073985_tt_3880 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (45/45 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | so_445807_ff_5944 | so_445807_ff_5944 | signoff | 0.9 |  | NO-DATA: empty log |  |
| intel1 | so_445807_tt_5944 | so_445807_tt_5944 | signoff | 0.9 |  | NO-DATA: empty log |  |
| intel1 | so_78775_ff_69145 | so_78775_ff_69145 | signoff | 1.2 |  | NO-DATA: empty log |  |
| intel1 | so_78775_tt_69145 | so_78775_tt_69145 | signoff | 1.2 |  | NO-DATA: empty log |  |
| intel2 | dpkit-coll_ftm-2001265 | coll_ftm | 5_2_route | 2.2 | drt_violations best 385 last 385 rows 2 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-3596641 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (216/217 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v12e-1190106 | kv3_pv_v12e | 3_3_place_gp | 1.0 | overflow best 0.0995 last 0.0995 rows 45 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-2526787 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (225/226 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | otc-2407048-21046 | 2407048 | signoff | 1.5 | last meaningful line 1.5 h ago (3/3 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-1955823 | kv3_hgi | 5_2_route | 4.9 |  | KEEP: kv3_hgi_1124155644	KV-OWN-RSTREACH	combined HEADLEG2+HGI-LEAF ship form; noprog  |  |
| epyc10 | dpkit-kv3_hgi_v2__cl2862d491-436421 | kv3_hgi_v2 | tt_setup_repair_grt | 5.2 |  | KEEP: kv3_hgi_v2__cl2862d491_1124155702	KV-OWN-RSTREACH	combined hgi_v2 ship form (COO |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pvb2cd22a7-3043152 | col_h9_r2__t1 | tt_setup_repair_grt | 3.8 |  | KEEP: col_h9_r2__t1__clb8d86cd5__pvb2cd22a7	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-fin-3514577 | fin | 6_report | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 5_2_route | 21.0 | drt_violations best 70805 last 70805 rows 4 | before-window best 416066, window best 70805 | PROGRESS: drt_violations improved 83.0 % in window |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 19.9 | drt_violations best 620 last 620 rows 19 | before-window best 272423, window best 620 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-3750591 | slw_fe_v2 | 5_2_route | 19.9 | drt_violations best 24222 last 24222 rows 5 | before-window best 378938, window best 24222 | PROGRESS: drt_violations improved 93.6 % in window |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | 5_2_route | 20.0 | drt_violations best 36 last 36 rows 6 | before-window best 227744, window best 36 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc11 | dpkit-hd_lep0N-2184208 | hd_lep0N | pregrt_ff_hold | 0.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 21.2 | drt_violations best 71 last 71 rows 23 | before-window best 329677, window best 71 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc12 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1520876 | col_h10_r0_p4__t1 | 5_1_grt | 2.4 | repair_TNS best 0 last 0 rows 19 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 26.0 | drt_violations best 6215 last 33693 rows 18 | before-window best 6824, window best 6215 | PROGRESS: drt_violations improved 8.9 % in window |  |
| epyc7 | dpkit-coll_core-3493022 | coll_core | 5_1_grt | 5.2 | grt_overflow best 0 last 17 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 31.1 | drt_violations best 2761 last 5839 rows 19 | before-window best 2818, window best 2761 | PROGRESS: drt_violations improved 2.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 27.3 | drt_violations best 5073 last 5073 rows 15 | before-window best 11325, window best 5073 | PROGRESS: drt_violations improved 55.2 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 25.9 | drt_violations best 12935 last 12935 rows 12 | before-window best 23801, window best 12935 | PROGRESS: drt_violations improved 45.7 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 25.7 | drt_violations best 6879 last 6879 rows 14 | before-window best 15427, window best 6879 | PROGRESS: drt_violations improved 55.4 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-534954 | slw_su_l1 | tt_setup_repair_grt | 7.9 | repair_Violations best 0 last 0 rows 46 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-918588 | col_h10_r0_p1__t1 | 4_2_tapbal_grt | 2.5 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 5_2_route | 22.6 | drt_violations best 97 last 97 rows 18 | before-window best 320246, window best 97 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_2_route | 22.6 | drt_violations best 23437 last 23437 rows 10 | before-window best 93397, window best 23437 | PROGRESS: drt_violations improved 74.9 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 22.6 | drt_violations best 360 last 360 rows 16 | before-window best 266434, window best 360 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 22.6 | drt_violations best 8974 last 8974 rows 11 | before-window best 450083, window best 8974 | PROGRESS: drt_violations improved 98.0 % in window |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 22.6 | drt_violations best 8519 last 40739 rows 18 | before-window best 9525, window best 8519 | PROGRESS: drt_violations improved 10.6 % in window |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | pregrt_ff_hold | 8.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_1_grt | 5.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 9.9 | drt_violations best 2540 last 2540 rows 12 | before-window best 162909, window best 2540 | PROGRESS: drt_violations improved 98.4 % in window |  |
| epyc9 | dpkit-sle_fe_v2-820705 | sle_fe_v2 | 5_2_route | 19.5 | drt_violations best 30892 last 30892 rows 12 | before-window best 125492, window best 30892 | PROGRESS: drt_violations improved 75.4 % in window |  |
| epyc9 | dpkit-slice_station__t44-2657480 | slice_station__t44 | 5_1_grt | 0.9 | repair_TNS best 0 last 0 rows 19 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 19.7 | drt_violations best 4 last 4 rows 53 | before-window best 4850, window best 4 | PROGRESS: drt_violations improved 99.9 % in window |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | 4_2_tapbal_grt | 1.9 | repair_Violations best 0 last 0 rows 11 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 17.9 | drt_violations best 1 last 1 rows 40 | before-window best 39, window best 1 | PROGRESS: drt_violations improved 97.4 % in window |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 25.9 | drt_violations best 7268 last 7268 rows 10 | before-window best 104690, window best 7268 | PROGRESS: drt_violations improved 93.1 % in window |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 5_2_route | 16.5 | drt_violations best 26476 last 26476 rows 2 | before-window best 174940, window best 26476 | PROGRESS: drt_violations improved 84.9 % in window |  |
| intel1 | otc-3504566-18256 | 3504566 | flow | 3.8 | repair_Violations best 0 last 0 rows 17 | PROGRESS: repair_Violations reached 0 |  |
| intel2 | dpkit-hd_serdes-3275033 | hd_serdes | 4_2_tapbal_grt | 1.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel2 | dpkit-kv3_io_ft-3008115 | kv3_io_ft | 5_1_grt | 0.5 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 21.1 | drt_violations best 901 last 1410 rows 19 | before-window best 96187, window best 901 | PROGRESS: drt_violations improved 99.1 % in window |  |
