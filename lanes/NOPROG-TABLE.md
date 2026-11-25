# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 07:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'GRT-LABEL': 5, 'YOUNG': 142, 'NO-DATA': 37, 'KEEP': 1, 'EXCLUDED': 1, 'PROGRESS': 17}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 27.0 | drt_violations best 6215 last 14152 rows 19 | before-window best 6298, window best 6215 | NO-PROGRESS: drt_violations best 6215 vs 6298 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-kv3_hgi_v4-4881 | kv3_hgi_v4 | 5_1_grt | 3.2 | grt rounds 2 overflow 5:45451 -> 10:32436 | GRT-LABEL: DESIGN-FAIL: overflow 32436 at round 10 > 1000 |  |
| epyc11 | dpkit-slw_su_c__cl92142dac-2960548 | slw_su_c | 5_1_grt | 8.8 | grt rounds 2 overflow 5:21500 -> 10:14785 | GRT-LABEL: DESIGN-FAIL: overflow 14785 at round 10 > 1000 |  |
| epyc7 | dpkit-cbf_q00_s2-1045407 | cbf_q00_s2 | 5_1_grt | 0.1 | grt rounds 2 overflow 5:87022 -> 10:54031 | GRT-LABEL: DESIGN-FAIL: overflow 54031 at round 10 > 1000 |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-3439533 | cbn_q01 | 5_1_grt | 0.8 | grt rounds 2 overflow 5:81921 -> 10:75607 | GRT-LABEL: DESIGN-FAIL: overflow 75607 at round 10 > 1000 |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | 5_1_grt | 15.1 | grt rounds 2 overflow 5:17977 -> 10:2858 | GRT-LABEL: DESIGN-FAIL: overflow 2858 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_hg_v1p5-970860 | kv3_hg_v1p5 | 5_1_grt | 6.1 | last meaningful line 2.0 h ago (306/1314 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1049351 | kv3_hub_Wo | 5_1_grt | 14.3 | repair_TNS best 21.292 last 21.292 rows 10 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc10 | dpkit-native59-3384403 | native59 | 5_2_route | 13.2 | drt_violations best 35428 last 35428 rows 2 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | dpkit-phy_serdes_b-1327978 | phy_serdes_b | 5_1_grt | 0.7 | last meaningful line 0.3 h ago (2233/3242 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | generate_abstract | 21.0 | last meaningful line 0.2 h ago (27/27 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2082061 | slw_st_a_v1 | 5_2_route | 5.9 | drt_violations best 157351 last 157351 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc10 | otc-2025541-6828 | 2025541 | signoff | 2.3 | last meaningful line 2.3 h ago (3/3 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | otc-2424957-5022 | 2424957 | signoff | 2.1 | last meaningful line 2.0 h ago (3/3 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_073109_4058437-i1-634237 | eco_20261125_073109_4058437-i1 | 5_2_route | 2.9 | last meaningful line 0.1 h ago (281/282 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_153001_3155820-i1t-2575664 | eco_20261125_153001_3155820-i1t | 5_1_grt | 0.2 | last meaningful line 0.2 h ago (290/1403 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | so_2984461_ff_37200 | so_2984461_ff_37200 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc10 | so_2984461_tt_37200 | so_2984461_tt_37200 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc10 | so_3047961_ff_75669 | so_3047961_ff_75669 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | so_3047961_tt_75669 | so_3047961_tt_75669 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | ap-ageom-kw-sle-su-c-grt-1601387 | sle-su-c-grt | 3_5_place_dp | 0.2 | last meaningful line 0.2 h ago (128/128 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Eo-1420436 | kv3_hub_Eo | 4_1_cts | 0.2 | last meaningful line 0.2 h ago (47/47 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Wo-1632470 | kv3_hub_Wo | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (47/47 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v5-1052229 | kv3_pv_v5 | 5_1_grt | 6.4 | last meaningful line 1.3 h ago (272/1280 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | 5_2_route | 12.5 | drt_violations best 21736 last 21736 rows 2 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl19bb38ef-40900 | slw_su_c | 4_1_cts | 0.9 | last meaningful line 0.2 h ago (8435/8435 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | otc-1109607-10581 | 1109607 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc11 | otc-1616228-26288 | 1616228 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc11 | otc-1830932-23851 | 1830932 | - | 2.0 |  | NO-DATA: no log found |  |
| epyc11 | otc-336507-16010 | 336507 | - | 0.7 |  | NO-DATA: no log found |  |
| epyc11 | otc-381902-2867 | 381902 | - | 6.7 |  | NO-DATA: no log found |  |
| epyc11 | otc-608716-5618 | 608716 | signoff | 0.6 | last meaningful line 0.5 h ago (3/3 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i2t-2255468 | eco_20261124_190641_1260390-i2t | 5_2_route | 5.8 | drt_violations best 10 last 10 rows 7 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i2t-96653 | eco_20261124_200101_1087713-i2t | 5_2_route | 4.8 | drt_violations best 4960 last 4960 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_141555_518460-i1-2852121 | eco_20261125_141555_518460-i1 | 5_2_route | 1.5 | last meaningful line 0.0 h ago (259/259 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | prd-fin-2887287 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | so_1381634_ff_39591 | so_1381634_ff_39591 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | so_1381634_tt_39591 | so_1381634_tt_39591 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | so_576324_ff_36564 | so_576324_ff_36564 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (35/35 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | so_576324_tt_36564 | so_576324_tt_36564 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (35/35 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 4.4 |  | NO-DATA: no log found |  |
| epyc12 | otc-1273822-29690 | 1273822 | drc_parent_only | 1.9 | last meaningful line 0.0 h ago (380/380 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc12 | otc-1275997-12067 | 1275997 | drc_parent_only | 1.9 | last meaningful line -0.0 h ago (800/800 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc12 | otc-1278426-9051 | 1278426 | drc_parent_only | 1.9 | last meaningful line 0.0 h ago (380/380 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc12 | otc-1291490-1984 | 1291490 | drc_parent_only | 1.9 | last meaningful line 0.0 h ago (383/383 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc12 | otc-1294027-30241 | 1294027 | drc_parent_only | 1.9 | last meaningful line 0.0 h ago (515/515 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc12 | otc-1305696-4661 | 1305696 | drc_parent_only | 1.9 | last meaningful line 0.0 h ago (725/725 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc12 | otc-1308959-15081 | 1308959 | drc_merged | 1.9 | last meaningful line 0.0 h ago (287/287 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc12 | otc-1312023-14782 | 1312023 | drc_merged | 1.9 | last meaningful line 0.0 h ago (305/305 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc12 | otc-1314683-28749 | 1314683 | drc_parent_only | 1.9 | last meaningful line -0.0 h ago (1277/1277 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc12 | otc-1319124-12976 | 1319124 | drc_merged | 1.9 | last meaningful line 0.0 h ago (488/488 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc12 | otc-1321394-11555 | 1321394 | drc_merged | 1.9 | last meaningful line 0.0 h ago (743/743 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc12 | otc-1324644-27944 | 1324644 | drc_merged | 1.9 | last meaningful line 0.0 h ago (554/554 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc12 | otc-1338915-16694 | 1338915 | drc_parent_only | 1.9 | last meaningful line 0.0 h ago (1301/1301 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc12 | otc-1460135-77 | 1460135 | - | 3.5 |  | NO-DATA: no log found |  |
| epyc12 | otc-1994529-22240 | 1994529 | flow | 1.5 | last meaningful line 0.0 h ago (2987/2987 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc12 | otc-1995249-22339 | 1995249 | flow | 1.5 | last meaningful line 0.0 h ago (2950/2950 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc12 | otc-3293317-27322 | 3293317 | - | 2.7 |  | NO-DATA: no log found |  |
| epyc12 | otc-3501458-13012 | 3501458 | drc_merged | 4.4 | last meaningful line 1.3 h ago (334/334 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc12 | otc-351743-16220 | 351743 | hcpg_run | 2.2 | last meaningful line 1.8 h ago (13/13 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc12 | otc-4177864-31266 | 4177864 | asbuilt.yosys | 0.4 | last meaningful line 0.0 h ago (229029/229029 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Wi-3068909 | kv3_hub_Wi | 3_5_place_dp | 3.9 | last meaningful line 0.0 h ago (93/93 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 6.0 | drt_violations best 5 last 5 rows 27 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | otc-2770137-14837 | 2770137 | signoff | 1.9 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261124_204708_4151707-i2t-1352759 | eco_20261124_204708_4151707-i2t | 5_2_route | 2.7 | drt_violations best 376 last 376 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 2.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 2.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 2.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-A | qcdrt-sc-A | - | 2.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-B | qcdrt-sc-B | - | 2.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-C | qcdrt-sc-C | - | 2.2 |  | NO-DATA: no log found |  |
| epyc2 | so_2844687_ff_55409 | so_2844687_ff_55409 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | so_2844687_tt_55409 | so_2844687_tt_55409 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc7 | ap-ageom-kw-kv3-pv-v12e-grt-1226135 | kv3-pv-v12e-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-coll_core-3493022 | coll_core | 5_1_grt | 6.2 | last meaningful line 1.0 h ago (1298/2914 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-490219 | hd_lep0N_w | 3_3_place_gp | 0.3 | overflow best 0.6096 last 0.6096 rows 20 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v6e-646291 | kv3_pv_v6e | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (8119/8119 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t2-1380541 | serdes__t2 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | 4_1_cts | 2.3 | last meaningful line 0.3 h ago (10879/10879 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 4_1_cts | 2.0 | last meaningful line 0.1 h ago (5172/5172 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | postcts_gate_FF | 9.4 | last meaningful line -0.0 h ago (3731/3731 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | postcts_gate_FF | 6.2 | last meaningful line 0.1 h ago (2150/2150 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | postcts_gate_FF | 6.2 | last meaningful line 0.2 h ago (973/973 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-22145 | sle_sc_v2 | postcts_gate_TT | 0.5 | last meaningful line 0.0 h ago (894/894 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3817081 | sle_st_a_v2 | 5_2_route | 7.7 | drt_violations best 72 last 72 rows 45 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__clc6d66f5b-2521917 | sle_su_l1 | 5_2_route | 6.7 | drt_violations best 237032 last 237032 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | postcts_gate_FF | 6.6 | last meaningful line 0.0 h ago (2201/2201 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 9.3 | drt_violations best 456468 last 456468 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | eco-abs-1206405 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | otc-2858837-8104 | 2858837 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc7 | otc-2916017-13620 | 2916017 | - | 2.7 |  | NO-DATA: no log found |  |
| epyc7 | otc-2938337-22499 | 2938337 | - | 2.7 |  | NO-DATA: no log found |  |
| epyc7 | otc-2958007-4014 | 2958007 | - | 2.7 |  | NO-DATA: no log found |  |
| epyc7 | otc-740568-7161 | 740568 | drc_parent_only | 1.8 | last meaningful line 0.0 h ago (677/677 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | otc-830728-15409 | 830728 | drc_merged | 1.8 | last meaningful line 0.0 h ago (320/320 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | otc-831702-28906 | 831702 | drc_parent_only | 1.8 | last meaningful line 0.0 h ago (611/611 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | otc-833865-16155 | 833865 | drc_merged | 1.8 | last meaningful line 0.0 h ago (344/344 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | otc-835730-18044 | 835730 | drc_merged | 1.8 | last meaningful line 0.0 h ago (521/521 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | otc-838804-29233 | 838804 | drc_merged | 1.8 | last meaningful line 0.0 h ago (554/554 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | prd-fin-1995832 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (68/68 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-fin-2551803 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (66/66 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-fin-3230821 | fin | 6_report | 0.3 | last meaningful line 0.1 h ago (66/66 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | so_1343591_ff_66716 | so_1343591_ff_66716 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | so_1343591_tt_66716 | so_1343591_tt_66716 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | so_30106_ff_9441 | so_30106_ff_9441 | generate_abstract | 0.5 | last meaningful line 0.3 h ago (35/35 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | so_30106_tt_9441 | so_30106_tt_9441 | generate_abstract | 0.5 | last meaningful line 0.3 h ago (35/35 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-918588 | col_h10_r0_p1__t1 | pregrt_ff_hold | 3.5 | repair_TNS best 75222.8 last 75222.8 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_mu_C__t1-730122 | dsdv_slice_lepe_mu_C__t1 | 3_3_place_gp | 3.6 | overflow best 0.6043 last 0.6874 rows 54 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-kv3_pv_v3n-2522162 | kv3_pv_v3n | 5_1_grt | 3.0 | last meaningful line 0.1 h ago (160/160 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | generate_abstract | 23.6 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t51-3913394 | slice_station__t51 | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | eco-abs-2985366 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.2 h ago (29/29 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | lecaf-uc-03bd0ee623f9 | lecaf-uc-03bd0ee623f9 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | lecaf-uc-c01b49be73a8 | lecaf-uc-c01b49be73a8 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | lecaf-uc-d5f3d7812269 | lecaf-uc-d5f3d7812269 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-132122-8685 | 132122 | - | 3.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-1982827-8639 | 1982827 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc8 | prd-count-p1_tc-2528575 | count-p1_tc | prd_count_p1_tc | 0.2 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-count-p1_tc-3977758 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-count-p1_tc-420704 | count-p1_tc | prd_count_p1_tc | 0.2 | last meaningful line 0.0 h ago (50/50 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_104318_3955073-i1-65595 | eco_20261125_104318_3955073-i1 | 5_1_grt | 1.2 | repair_TNS best 34.791 last 34.791 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_122258_3982108-i1-1582033 | eco_20261125_122258_3982108-i1 | 5_2_route | 3.3 | drt_violations best 2 last 2 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | prd-fin-1143996 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (71/71 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-fin-1985482 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-fin-3640861 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | so_3220542_ff_89411 | so_3220542_ff_89411 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (33/33 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | so_3220542_tt_89411 | so_3220542_tt_89411 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (33/33 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | so_3674333_ff_26891 | so_3674333_ff_26891 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | so_3674333_tt_26891 | so_3674333_tt_26891 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-col-h9-r1--t1--cl49d7a23e--pv2f96c04f-grt-1195550 | col-h9-r1--t1--cl49d7a23e--pv2f96c04f-grt | lec | 0.1 | LEC last write 0.1 h ago | YOUNG: evidence 0.1 h < 6 h |  |
| epyc9 | ap-ageom-kw-dsdv-slice-c1x-C--t10-grt-1271931 | dsdv-slice-c1x-C--t10-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-dsdv-slice-kv512-C--t1-grt-1229089 | dsdv-slice-kv512-C--t1-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-kv-leaf--t5-grt-1387415 | ot-s81sl-kv-leaf--t5-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t26-grt-1058718 | ot-s81sl-leaf--t26-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | 5_1_grt | 9.0 | last meaningful line 0.2 h ago (167/167 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvc9270d09-1494595 | col_h10_r0_p4__t1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 5_1_grt | 9.0 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3698869 | col_h9_r0_p4__t1 | postcts_gate_FF | 6.9 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 9.0 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_1_grt | 6.2 | last meaningful line 0.0 h ago (2493/2524 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t7-3863913 | dsdv_slice_c1x_C__t7 | 3_1_place_gp_skip_io | 3.3 | overflow best 0.2052 last 0.2052 rows 45 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-slice_station__t37-3479533 | slice_station__t37 | 5_2_route | 6.9 | drt_violations best 34873 last 34873 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t41-1123489 | slice_station__t41 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3647/3647 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t43-3486441 | slice_station__t43 | 5_2_route | 6.9 | drt_violations best 34635 last 34635 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t44-2657480 | slice_station__t44 | 5_2_route | 1.9 | last meaningful line 0.0 h ago (241/242 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-2620358 | slice_station__t52 | 5_2_route | 5.7 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | otc-1865534-29853 | 1865534 | - | 1.3 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2686622 | col_h10_r0_p4__t1 | pregrt_ff_hold | 2.9 | repair_TNS best 96462.2 last 96462.2 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | pregrt_ff_hold | 2.9 | repair_TNS best 71771.6 last 71771.6 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.8 | last meaningful line 2.0 h ago (61/88 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.7 | last meaningful line 2.0 h ago (61/82 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 4_2_tapbal_grt | 2.9 | last meaningful line 2.0 h ago (61/84 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | pregrt_ff_hold | 2.9 | repair_TNS best 63490.2 last 63490.2 rows 1 | YOUNG: evidence 1.9 h < 2.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 51207.7 last 51207.7 rows 1 | YOUNG: evidence 1.7 h < 2.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 60746.9 last 60746.9 rows 1 | YOUNG: evidence 1.9 h < 2.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-2360794 | col_h9_r2__t1 | pregrt_ff_hold | 3.0 | repair_TNS best 118766 last 118766 rows 1 | YOUNG: evidence 2.0 h < 2.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pva119e808-2308652 | col_h9_r2__t1 | pregrt_ff_hold | 3.0 | repair_TNS best 79800.3 last 79800.3 rows 1 | YOUNG: evidence 2.0 h < 2.5 h |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1177242 | kv3_hg_v1p3__r838481cd7 | 5_1_grt | 8.1 | last meaningful line 3.5 h ago (288/1298 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_sys_c-4063347 | kv3_sys_c | tt_setup_repair_grt | 4.7 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 5_2_route | 14.7 | last meaningful line 0.7 h ago (267/268 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t27-4040446 | slice_station__t27 | 5_2_route | 4.7 | last meaningful line 0.5 h ago (249/250 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 16.4 | last meaningful line 0.5 h ago (262/263 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 5_2_route | 17.2 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | otc-2590726-12039 | 2590726 | - | 1.1 |  | NO-DATA: no log found |  |
| intel1 | otc-3018992-28537 | 3018992 | - | 0.9 |  | NO-DATA: no log found |  |
| intel1 | otc-3504566-18256 | 3504566 | grt_it0 | 4.8 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | otc-574655-9239 | 574655 | drc_parent_only | 1.9 | last meaningful line 0.1 h ago (266/266 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | otc-578793-24959 | 578793 | drc_merged | 1.9 | last meaningful line 0.0 h ago (194/194 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | otc-582965-3828 | 582965 | drc_merged | 1.9 | last meaningful line 0.0 h ago (194/194 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | otc-586189-14994 | 586189 | drc_parent_only | 1.9 | last meaningful line 0.1 h ago (266/266 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | otc-589045-16647 | 589045 | drc_merged | 1.9 | last meaningful line 0.0 h ago (215/215 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i3t-2681077 | eco_20261123_191853_2879776-i3t | 5_2_route | 4.9 | last meaningful line 0.5 h ago (287/288 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | prd-eco_20261125_002226_1452841-i1t-3347319 | eco_20261125_002226_1452841-i1t | 5_2_route | 7.3 | drt_violations best 9407 last 9407 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | prd-eco_20261125_040243_2843749-i1-851245 | eco_20261125_040243_2843749-i1 | 5_2_route | 3.6 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i1-3109373 | eco_20261125_050013_1448739-i1 | 5_2_route | 2.7 | last meaningful line 0.2 h ago (263/263 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | prd-eco_20261125_070347_2847958-i1-3642895 | eco_20261125_070347_2847958-i1 | 5_1_grt | 0.6 | last meaningful line 0.3 h ago (143/143 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | prd-eco_20261125_072849_2847456-i1-527377 | eco_20261125_072849_2847456-i1 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | so_3239057_ff_21478 | so_3239057_ff_21478 | signoff | 0.8 |  | NO-DATA: empty log |  |
| intel1 | so_3239057_tt_21478 | so_3239057_tt_21478 | signoff | 0.8 |  | NO-DATA: empty log |  |
| intel2 | dpkit-coll_ftm-1141936 | coll_ftm | 5_1_grt | 0.5 | repair_Remaining best 29798 last 29798 rows 20 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-1822840 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-3008115 | kv3_io_ft | abstract_exact | 1.5 | last meaningful line 0.1 h ago (4/4 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | otc-2407048-21046 | 2407048 | signoff | 2.5 | last meaningful line 2.5 h ago (3/3 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-1955823 | kv3_hgi | 5_2_route | 5.9 |  | KEEP: kv3_hgi_1124155644	KV-OWN-RSTREACH	combined HEADLEG2+HGI-LEAF ship form; noprog  |  |
| intel1 | eco-abs-3679279 | eco-abs | generate_abstract | 0.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 20.9 | drt_violations best 368 last 368 rows 25 | before-window best 272423, window best 368 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 22.2 | drt_violations best 71 last 71 rows 26 | before-window best 58968, window best 71 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 32.1 | drt_violations best 2761 last 4468 rows 20 | before-window best 2761, window best 4468 | PROGRESS: drt_violations: falling inside the active iteration (4468 -> 4357) |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 28.3 | drt_violations best 5073 last 5073 rows 15 | before-window best 6764, window best 5073 | PROGRESS: drt_violations improved 25.0 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_2_route | 26.9 | drt_violations best 12935 last 12935 rows 12 | before-window best 20612, window best 12935 | PROGRESS: drt_violations improved 37.2 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_2_route | 26.7 | drt_violations best 5853 last 5853 rows 15 | before-window best 11873, window best 5853 | PROGRESS: drt_violations improved 50.7 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 23.6 | drt_violations best 136 last 136 rows 23 | before-window best 266434, window best 136 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_2_route | 23.6 | drt_violations best 5896 last 5896 rows 13 | before-window best 105634, window best 5896 | PROGRESS: drt_violations improved 94.4 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 10.9 | drt_violations best 1090 last 1090 rows 15 | before-window best 162909, window best 1090 | PROGRESS: drt_violations improved 99.3 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | 5_2_route | 10.0 | drt_violations best 565 last 565 rows 16 | before-window best 163283, window best 565 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 20.7 | drt_violations best 4 last 4 rows 53 | before-window best 1221, window best 4 | PROGRESS: drt_violations improved 99.7 % in window |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 5_2_route | 19.0 | drt_violations best 138407 last 138407 rows 1 | before-window best 138407, window best 138407 | PROGRESS: drt_violations: active iteration at 47003 < best completed total 138407 (in-iter |  |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 18.9 | drt_violations best 1 last 1 rows 42 | before-window best 38, window best 1 | PROGRESS: drt_violations improved 97.4 % in window |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 26.9 | drt_violations best 4712 last 4712 rows 11 | before-window best 104690, window best 4712 | PROGRESS: drt_violations improved 95.5 % in window |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 5_2_route | 17.5 | drt_violations best 26476 last 26476 rows 2 | before-window best 174940, window best 26476 | PROGRESS: drt_violations improved 84.9 % in window |  |
| intel2 | dpkit-slice_station__t12-1887004 | slice_station__t12 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 22.1 | drt_violations best 870 last 870 rows 21 | before-window best 68885, window best 870 | PROGRESS: drt_violations improved 98.7 % in window |  |
