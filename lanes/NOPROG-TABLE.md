# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 09:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'GRT-LABEL': 5, 'YOUNG': 161, 'NO-DATA': 35, 'KEEP': 1, 'PROGRESS': 22}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc8 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-918588 | col_h10_r0_p1__t1 | pregrt_ff_hold | 5.0 | repair_TNS best 75222.8 last 75222.8 rows 1 | before-window best 75222.8, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-2360794 | col_h9_r2__t1 | pregrt_ff_hold | 4.5 | repair_TNS best 12785.1 last 12785.1 rows 1 | before-window best 12785.1, window best 12785.1 | NO-PROGRESS: repair_TNS best 12785.1 vs 12785.1 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 20.4 | drt_violations best 1 last 1 rows 45 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_hg_v1p5-970860 | kv3_hg_v1p5 | 5_1_grt | 7.6 | grt rounds 2 overflow 5:48965 -> 10:43054 | GRT-LABEL: DESIGN-FAIL: overflow 43054 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_hgi_v4-4881 | kv3_hgi_v4 | 5_1_grt | 4.7 | grt rounds 2 overflow 5:45451 -> 10:32436 | GRT-LABEL: DESIGN-FAIL: overflow 32436 at round 10 > 1000 |  |
| epyc7 | dpkit-cbf_q00_s2-1045407 | cbf_q00_s2 | 5_1_grt | 1.6 | grt rounds 2 overflow 5:87022 -> 10:54031 | GRT-LABEL: DESIGN-FAIL: overflow 54031 at round 10 > 1000 |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-3439533 | cbn_q01 | 5_1_grt | 2.3 | grt rounds 2 overflow 5:81921 -> 10:75607 | GRT-LABEL: DESIGN-FAIL: overflow 75607 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1177242 | kv3_hg_v1p3__r838481cd7 | 5_1_grt | 9.6 | grt rounds 2 overflow 5:40256 -> 10:36108 | GRT-LABEL: DESIGN-FAIL: overflow 36108 at round 10 > 1000 |  |
| epyc10 | dpkit-hd_serdes-1185661 | hd_serdes | 3_3_place_gp | 0.5 | overflow best 0.6294 last 0.6294 rows 29 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-hd_serdes-1187866 | hd_serdes | 3_3_place_gp | 0.5 | overflow best 0.1914 last 0.1914 rows 24 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-native59-3384403 | native59 | 6_report | 14.7 | last meaningful line 0.2 h ago (66/66 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_sc_v2-1968115 | sle_sc_v2 | 3_3_place_gp | 0.2 | overflow best 0.4036 last 0.4036 rows 17 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-sle_stm_v1__clbe630b9c-2603232 | sle_stm_v1 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (604/604 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2082061 | slw_st_a_v1 | generate_abstract | 7.4 | last meaningful line 0.1 h ago (53/53 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-3182147-1635 | 3182147 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-3186113-21272 | 3186113 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-4067299-15490 | 4067299 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc10 | otc-4188785-25915 | 4188785 | signoff | 1.0 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_153001_3155820-i1t-2575664 | eco_20261125_153001_3155820-i1t | 5_2_route | 1.7 | drt_violations best 361 last 361 rows 4 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | prd-fin-634237 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | so_1752275_ff_6808 | so_1752275_ff_6808 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc10 | so_1752275_tt_6808 | so_1752275_tt_6808 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc11 | ap-ageom-kw-col-h9-r0-p5--t1--pv5c8f2166-dump-1195202 | col-h9-r0-p5--t1--pv5c8f2166-dump | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | ap-ageom-kw-col-h9-r0-p5--t1--pv5c8f2166-grt-1195202 | col-h9-r0-p5--t1--pv5c8f2166-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-1109695 | col_h9_r0_p5__t1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (2645/2645 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-1168882 | col_h9_r0_p5__t1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-1130830 | col_h9_r0_p5__t1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (64/64 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc93af856-1168215 | col_h9_r0_p5__t1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-1072222 | col_h9_r0_p5__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2747/2747 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-hd_lep0N-2989918 | hd_lep0N | 5_1_grt | 1.0 | last meaningful line 0.3 h ago (262/1266 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Eo-1420436 | kv3_hub_Eo | 4_1_cts | 1.7 | last meaningful line 0.0 h ago (9294/9294 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Wo-1632470 | kv3_hub_Wo | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (10761/10761 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc11 | dpkit-sle_su_c-2149031 | sle_su_c | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (8882/8882 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | generate_abstract | 14.0 | last meaningful line 0.1 h ago (31/31 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl19bb38ef-40900 | slw_su_c | tt_setup_measure | 2.4 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | otc-1109607-10581 | 1109607 | - | 1.9 |  | NO-DATA: no log found |  |
| epyc11 | otc-1616228-26288 | 1616228 | - | 3.6 |  | NO-DATA: no log found |  |
| epyc11 | otc-2255400-11827 | 2255400 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc11 | otc-336507-16010 | 336507 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-381902-2867 | 381902 | - | 8.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-608716-5618 | 608716 | signoff | 2.1 | last meaningful line 2.0 h ago (3/3 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i2-3864714 | eco_20261124_190641_1260390-i2 | 5_1_grt | 0.7 | last meaningful line 0.3 h ago (240/1451 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i2-3847060 | eco_20261124_200101_1087713-i2 | 5_1_grt | 0.7 | last meaningful line 0.3 h ago (245/1486 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_120946_3832190-i1-2448133 | eco_20261125_120946_3832190-i1 | 5_2_route | 1.3 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | so_992417_ff_50322 | so_992417_ff_50322 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | so_992417_tt_50322 | so_992417_tt_50322 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dclk-eco5-otclk-3866417 | dclk-eco5-otclk | - | 0.1 |  | NO-DATA: no log found |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 5.9 |  | NO-DATA: no log found |  |
| epyc12 | otc-1273822-29690 | 1273822 | drc_merged | 3.4 | last meaningful line 0.0 h ago (914/914 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc12 | otc-1275997-12067 | 1275997 | drc_merged | 3.4 | last meaningful line 0.0 h ago (1298/1298 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc12 | otc-1278426-9051 | 1278426 | drc_merged | 3.4 | last meaningful line 0.0 h ago (1277/1277 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc12 | otc-1291490-1984 | 1291490 | drc_merged | 3.4 | last meaningful line 0.0 h ago (1028/1028 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc12 | otc-1294027-30241 | 1294027 | drc_merged | 3.4 | last meaningful line 0.1 h ago (1310/1310 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc12 | otc-1308959-15081 | 1308959 | drc_merged | 3.4 | last meaningful line 0.0 h ago (1112/1112 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc12 | otc-1460135-77 | 1460135 | - | 5.0 |  | NO-DATA: no log found |  |
| epyc12 | otc-1994529-22240 | 1994529 | flow | 3.0 | repair_Violations best 115566 last 115566 rows 47 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc12 | otc-1995249-22339 | 1995249 | flow | 3.0 | repair_Violations best 152401 last 152401 rows 30 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc12 | otc-3501458-13012 | 3501458 | drc_merged | 5.9 | last meaningful line 2.8 h ago (334/334 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc12 | otc-351743-16220 | 351743 | hcpg_run | 3.7 | last meaningful line 3.3 h ago (13/13 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc12 | otc-4062793-23362 | 4062793 | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (453/453 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | otc-4069659-13335 | 4069659 | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (453/453 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-1555405 | sle_fw_v2 | 3_3_place_gp | 0.1 | overflow best 0.4441 last 0.4441 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 7.5 | drt_violations best 2 last 2 rows 46 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1436404 | slw_st_a_v1 | 3_3_place_gp | 0.1 | overflow best 0.3683 last 0.3842 rows 9 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | prd-eco_20261124_204708_4151707-i2-961159 | eco_20261124_204708_4151707-i2 | 5_1_grt | 0.4 | last meaningful line 0.1 h ago (297/331 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261125_075050_2599201-i1-3410249 | eco_20261125_075050_2599201-i1 | 5_2_route | 1.4 | drt_violations best 1 last 1 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 3.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 3.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 3.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-A | qcdrt-sc-A | - | 3.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-B | qcdrt-sc-B | - | 3.7 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-C | qcdrt-sc-C | - | 3.7 |  | NO-DATA: no log found |  |
| epyc2 | thirsty_kirch | thirsty_kirch | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | xenodochial_stonebraker | xenodochial_stonebraker | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-coll_core-3493022 | coll_core | postcts_gate_TT | 7.7 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v12e-1804185 | kv3_pv_v12e | 4_1_cts | 1.3 | last meaningful line 0.3 h ago (11884/11884 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v6e-646291 | kv3_pv_v6e | 4_1_cts | 1.8 | last meaningful line 0.0 h ago (8552/8552 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | postcts_gate_FF | 16.6 | last meaningful line -0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | 4_1_cts | 3.8 | last meaningful line 0.3 h ago (10943/10943 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 4_1_cts | 3.5 | last meaningful line 0.0 h ago (5343/5343 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | 5_2_route | 10.9 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 7.7 | last meaningful line 0.2 h ago (263/264 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 7.7 | last meaningful line 0.2 h ago (262/263 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-22145 | sle_sc_v2 | postcts_gate_FF | 2.0 | last meaningful line 0.2 h ago (71695/71695 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3817081 | sle_st_a_v2 | 6_report | 9.2 | last meaningful line 0.0 h ago (55/55 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__clc6d66f5b-2521917 | sle_su_l1 | 5_2_route | 8.2 | drt_violations best 619 last 619 rows 10 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-585532 | slw_hc2 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9986 last 0.9986 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-408753 | slw_hc3 | 3_3_place_gp | 0.3 | overflow best 0.9563 last 0.9564 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 8.1 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 10.8 | drt_violations best 456468 last 456468 rows 1 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l0__cl1a1c1f8f-587333 | slw_su_l0 | 3_3_place_gp | 0.3 | overflow best 0.2925 last 0.295 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 0.9 | last meaningful line 0.1 h ago (264/265 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | otc-131491-13694 | 131491 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc7 | otc-1370625-9083 | 1370625 | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (353/353 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-1371862-8753 | 1371862 | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (353/353 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-2858837-8104 | 2858837 | - | 2.5 |  | NO-DATA: no log found |  |
| epyc7 | otc-2938337-22499 | 2938337 | - | 4.2 |  | NO-DATA: no log found |  |
| epyc7 | otc-2958007-4014 | 2958007 | - | 4.2 |  | NO-DATA: no log found |  |
| epyc7 | otc-3693543-29719 | 3693543 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc7 | otc-639211-10962 | 639211 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261125_073945_2252980-i2t-488714 | eco_20261125_073945_2252980-i2t | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-coll_ftn-1310614 | coll_ftn | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v3n-2522162 | kv3_pv_v3n | 5_1_grt | 4.5 | last meaningful line 1.3 h ago (275/1281 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-kv3_sys_SD-513287 | kv3_sys_SD | pregrt_ff_hold | 0.2 | repair_TNS best 14990 last 14990 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-native59-3301533 | native59 | 2_1_floorplan | 0.5 | last meaningful line 0.1 h ago (1360/1360 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | generate_abstract | 25.1 | last meaningful line 0.4 h ago (29/29 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3426543 | sle_hc2 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl115da35f-2926018 | sle_sc_v1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.1733 last 0.1733 rows 41 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-2731639 | sle_sc_v1 | 3_3_place_gp | 0.7 | overflow best 0.1621 last 0.2116 rows 45 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-sle_sc_v3-3730601 | sle_sc_v3 | 3_3_place_gp | 0.4 | overflow best 0.3873 last 0.3873 rows 20 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slice_station__t24__cl66b71008-210233 | slice_station__t24 | 3_5_place_dp | 0.3 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t42__cl4bd1432c-4193630 | slice_station__t42 | 3_3_place_gp | 0.3 | overflow best 0.2326 last 0.2326 rows 5 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-388358 | slw_hc1 | synth_odb_v | 0.2 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-192007 | slw_hc3 | 3_2_place_iop | 0.3 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2782083 | slw_sc_v1 | 3_3_place_gp | 0.6 | overflow best 0.3615 last 0.362 rows 10 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-1112114 | slw_sc_v1 | synth_odb_v | 0.1 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-tt_ctlm-1136296 | tt_ctlm | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (107/107 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-1220115-969 | 1220115 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-1288521-5795 | 1288521 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-132122-8685 | 132122 | - | 5.3 |  | NO-DATA: no log found |  |
| epyc8 | otc-1609200-26446 | 1609200 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-1616827-18813 | 1616827 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-1982827-8639 | 1982827 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc8 | otc-2113939-31863 | 2113939 | - | 0.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-3569473-6282 | 3569473 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-3579536-7216 | 3579536 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc8 | otc-3842582-23701 | 3842582 | asbuilt.yosys | 0.4 | last meaningful line 0.0 h ago (227147/227147 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_025941_3548303-i2-1098320 | eco_20261125_025941_3548303-i2 | 5_2_route | 1.1 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_104318_3955073-i1-65595 | eco_20261125_104318_3955073-i1 | 5_2_route | 2.7 | drt_violations best 8928 last 8928 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | prd-fin-1582033 | fin | 6_report | 1.0 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | so_2135476_ff_4699 | so_2135476_ff_4699 | generate_abstract | 0.8 | last meaningful line 0.8 h ago (33/33 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | so_2135476_tt_4699 | so_2135476_tt_4699 | generate_abstract | 0.8 | last meaningful line 0.8 h ago (33/33 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | so_3257503_ff_52185 | so_3257503_ff_52185 | generate_abstract | 0.5 | last meaningful line 0.5 h ago (35/35 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | so_3257503_tt_52185 | so_3257503_tt_52185 | generate_abstract | 0.5 | last meaningful line 0.5 h ago (35/35 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | so_3260279_ff_68275 | so_3260279_ff_68275 | generate_abstract | 0.5 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | so_3260279_tt_68275 | so_3260279_tt_68275 | generate_abstract | 0.5 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | so_811441_ff_11512 | so_811441_ff_11512 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (35/35 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | so_811441_tt_11512 | so_811441_tt_11512 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (35/35 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-dsdv-slice-c1x-C--t7-grt-893190 | dsdv-slice-c1x-C--t7-grt | lec | 0.1 | LEC last write 0.0 h ago | YOUNG: evidence 0.1 h < 6 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | 5_1_grt | 10.5 | last meaningful line 0.7 h ago (1318/2578 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-1427167 | col_h10_r0_p1__t1 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (3913/3913 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvc9270d09-1494595 | col_h10_r0_p4__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 113133 last 113133 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2175059 | col_h10_r0_p4__t1 | 4_2_tapbal_grt | 0.6 | last meaningful line 0.0 h ago (62/64 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvd8c0565f-1181305 | col_h10_r0_p4__t1 | 4_2_tapbal_grt | 0.8 | last meaningful line 0.1 h ago (62/68 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 5_1_grt | 10.5 | last meaningful line 0.2 h ago (1319/1361 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 32975.8 last 32975.8 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3698869 | col_h9_r0_p4__t1 | 5_2_route | 8.4 | last meaningful line 0.1 h ago (280/281 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 10.5 | last meaningful line 0.5 h ago (291/292 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | tt_setup_repair | 1.5 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 7.7 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | 4_2_tapbal_grt | 1.4 | last meaningful line 0.8 h ago (61/85 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | pregrt_ff_hold | 1.5 | repair_TNS best 89205.9 last 89205.9 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-2945122 | col_h9_r2__t1 | pregrt_ff_hold | 1.2 | repair_TNS best 38086.1 last 38086.1 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 61797 last 61797 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | pregrt_ff_hold | 0.8 | repair_TNS best 51854.9 last 51854.9 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1145127 | col_h9_r2__t1 | 4_1_cts | 0.0 | repair_Violations best 1222 last 1222 rows 12 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve0486b40-965586 | col_h9_r2__t1 | tt_setup_repair_grt | 0.1 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2186209 | dsdv_slice_lepe_nh_mus_LP__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 15862.5 last 15862.5 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-1205777 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t30__cl6a190133-1093777 | slice_station__t30 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (1171/1171 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t41-1123489 | slice_station__t41 | tt_setup_repair | 1.6 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t43-3486441 | slice_station__t43 | generate_abstract | 8.4 | last meaningful line 0.1 h ago (29/29 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t44-2657480 | slice_station__t44 | 5_3_fillcell | 3.4 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-2620358 | slice_station__t52 | 5_2_route | 7.2 | drt_violations best 33724 last 33724 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t6__cl54a9ceeb-2644120 | slice_station__t6 | tt_setup_measure | 0.5 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-1865534-29853 | 1865534 | - | 2.8 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2686622 | col_h10_r0_p4__t1 | pregrt_ff_hold | 4.4 | repair_TNS best 96462.2 last 96462.2 rows 1 | YOUNG: evidence 1.8 h < 2.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | pregrt_ff_hold | 4.4 | repair_TNS best 71771.6 last 71771.6 rows 1 | YOUNG: evidence 1.8 h < 2.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 4_2_tapbal_grt | 4.3 | last meaningful line 3.5 h ago (61/103 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 4_2_tapbal_grt | 4.2 | last meaningful line 0.0 h ago (117/117 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | 5_1_grt | 4.3 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 5_2_route | 16.2 | last meaningful line 0.4 h ago (277/278 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t27-4040446 | slice_station__t27 | 5_2_route | 6.2 | last meaningful line 0.5 h ago (257/258 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 17.9 | last meaningful line 0.5 h ago (268/269 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 5_2_route | 18.7 | last meaningful line 0.5 h ago (275/276 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | otc-1343902-2148 | 1343902 | flow | 1.4 | last meaningful line 0.0 h ago (2937/2937 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | otc-1750914-12376 | 1750914 | flow | 1.2 | last meaningful line 0.0 h ago (2950/2950 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | otc-2284893-4545 | 2284893 | flow | 1.0 | last meaningful line 0.0 h ago (2921/2921 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | otc-574655-9239 | 574655 | drc_parent_only | 3.4 | last meaningful line 0.0 h ago (1274/1274 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | otc-578793-24959 | 578793 | drc_parent_only | 3.4 | last meaningful line 0.0 h ago (806/806 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | otc-582965-3828 | 582965 | drc_merged | 3.4 | last meaningful line 0.0 h ago (398/398 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | otc-586189-14994 | 586189 | drc_merged | 3.4 | last meaningful line 0.0 h ago (560/560 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | otc-589045-16647 | 589045 | drc_merged | 3.4 | last meaningful line 0.0 h ago (554/554 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i3t-2681077 | eco_20261123_191853_2879776-i3t | 5_2_route | 6.4 | last meaningful line 0.5 h ago (295/296 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | prd-eco_20261125_040243_2843749-i1-851245 | eco_20261125_040243_2843749-i1 | 5_2_route | 5.1 | last meaningful line 0.5 h ago (278/279 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i1-3109373 | eco_20261125_050013_1448739-i1 | 5_2_route | 4.2 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | prd-eco_20261125_070347_2847958-i1-3642895 | eco_20261125_070347_2847958-i1 | 5_1_grt | 2.1 | last meaningful line 0.8 h ago (295/372 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | prd-eco_20261125_072849_2847456-i1-527377 | eco_20261125_072849_2847456-i1 | 5_1_grt | 1.7 | last meaningful line 0.4 h ago (290/359 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | prd-eco_20261125_082621_46745-i1-2873810 | eco_20261125_082621_46745-i1 | 5_1_grt | 0.8 | last meaningful line 0.2 h ago (139/139 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | so_2067287_ff_39738 | so_2067287_ff_39738 | generate_abstract | 1.1 | last meaningful line 1.0 h ago (34/34 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | so_2067287_tt_39738 | so_2067287_tt_39738 | generate_abstract | 1.1 | last meaningful line 1.0 h ago (34/34 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-coll_ftc-2805680 | coll_ftc | 2_2_floorplan_macro | 0.1 | last meaningful line 0.0 h ago (7/7 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-1141936 | coll_ftm | 5_2_route | 2.0 | drt_violations best 10288 last 10288 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-hd_host_w-413405 | hd_host_w | pregrt_ff_hold | 0.8 | repair_TNS best 32080.4 last 32080.4 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-hd_lep0N-1613711 | hd_lep0N | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-3387973 | kv3_io_ft | 5_2_route | 1.2 | drt_violations best 5443 last 5443 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2250090 | sle_hc1 | 3_3_place_gp | 0.3 | overflow best 0.8837 last 0.8839 rows 8 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1634062 | sle_hc1 | 3_3_place_gp | 0.4 | overflow best 0.6442 last 0.6442 rows 29 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-2399337 | sle_hc2 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (268/268 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-sle_hc2__clcc5e3e61-1716233 | sle_hc2 | 3_4_place_resized | 0.4 | repair_Remaining best 183320 last 183320 rows 173 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-slw_hc1__cl3449ea95-2186510 | slw_hc1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.859 last 0.859 rows 28 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slw_hc2__cl6bcaba89-2548443 | slw_hc2 | 3_1_place_gp_skip_io | 0.2 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-2764542 | slw_hc3 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v3-2889642 | slw_sc_v3 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-1955823 | kv3_hgi | 5_2_route | 7.4 |  | KEEP: kv3_hgi_1124155644	KV-OWN-RSTREACH	combined HEADLEG2+HGI-LEAF ship form; noprog  |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 22.4 | drt_violations best 277 last 277 rows 34 | before-window best 16227, window best 277 | PROGRESS: drt_violations improved 98.3 % in window |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 23.7 | drt_violations best 1 last 1 rows 46 | before-window best 7302, window best 1 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-serdes__t4-2700198 | serdes__t4 | 4_1_cts | 1.0 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 25.1 | drt_violations best 22 last 22 rows 40 | before-window best 266434, window best 22 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv8995e794-2664422 | col_h9_r0_p5__t1 | 4_2_tapbal_grt | 1.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49636389-2391990 | col_h9_r1__t1 | 3_5_place_dp | 0.5 | repair_Violations best 0 last 0 rows 24 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 12.4 | drt_violations best 650 last 650 rows 21 | before-window best 162909, window best 650 | PROGRESS: drt_violations improved 99.6 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | 5_2_route | 11.5 | drt_violations best 379 last 379 rows 30 | before-window best 163283, window best 379 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2726055 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 1.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc9 | dpkit-slice_station__t37-3479533 | slice_station__t37 | 5_2_route | 8.4 | drt_violations best 0 last 0 rows 8 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | dpkit-slice_station__t40__clc8fb2c8c-2653854 | slice_station__t40 | 5_1_grt | 1.3 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 22.2 | drt_violations best 4 last 4 rows 53 | before-window best 46, window best 4 | PROGRESS: drt_violations improved 91.3 % in window |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 4_2_tapbal_grt | 4.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pva119e808-2308652 | col_h9_r2__t1 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 5_2_route | 20.5 | drt_violations best 19233 last 19233 rows 2 | before-window best 138407, window best 19233 | PROGRESS: drt_violations improved 86.1 % in window |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 28.4 | drt_violations best 1860 last 1860 rows 13 | before-window best 71761, window best 1860 | PROGRESS: drt_violations improved 97.4 % in window |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 5_2_route | 19.0 | drt_violations best 18062 last 18062 rows 3 | before-window best 174940, window best 18062 | PROGRESS: drt_violations improved 89.7 % in window |  |
| intel1 | prd-eco_20261125_002226_1452841-i1t-3347319 | eco_20261125_002226_1452841-i1t | 5_2_route | 8.8 | drt_violations best 9407 last 9407 rows 1 | before-window best 9407, window best 9407 | PROGRESS: drt_violations: active iteration at 1186 < best completed total 9407 (in-iterati |  |
| intel2 | dpkit-slice_station__t12-2473457 | slice_station__t12 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 23.6 | drt_violations best 674 last 674 rows 23 | before-window best 6887, window best 674 | PROGRESS: drt_violations improved 90.2 % in window |  |
