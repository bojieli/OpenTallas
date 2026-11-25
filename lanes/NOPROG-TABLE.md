# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-25 08:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'GRT-LABEL': 5, 'YOUNG': 158, 'NO-DATA': 36, 'KEEP': 3, 'PROGRESS': 23}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-2859592 | col_h9_r2__t1 | pregrt_ff_hold | 3.8 | repair_TNS best 888.042 last 888.042 rows 1 | before-window best 888.042, window best 888.042 | NO-PROGRESS: repair_TNS best 888.042 vs 888.042 before window: < 2 % in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-2360794 | col_h9_r2__t1 | pregrt_ff_hold | 4.0 | repair_TNS best 118766 last 118766 rows 1 | before-window best 118766, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (S81-ALLFIX-INT decides; |
| intel1 | dpkit-sle_su_l0__cl086d85ba-4034229 | sle_su_l0 | 5_2_route | 19.9 | drt_violations best 1 last 1 rows 45 | before-window best 1, window best 1 | NO-PROGRESS: drt_violations best 1 vs 1 before window: < 2 % in 6 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc10 | dpkit-kv3_hg_v1p5-970860 | kv3_hg_v1p5 | 5_1_grt | 7.1 | grt rounds 2 overflow 5:48965 -> 10:43054 | GRT-LABEL: DESIGN-FAIL: overflow 43054 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_hgi_v4-4881 | kv3_hgi_v4 | 5_1_grt | 4.2 | grt rounds 2 overflow 5:45451 -> 10:32436 | GRT-LABEL: DESIGN-FAIL: overflow 32436 at round 10 > 1000 |  |
| epyc7 | dpkit-cbf_q00_s2-1045407 | cbf_q00_s2 | 5_1_grt | 1.1 | grt rounds 2 overflow 5:87022 -> 10:54031 | GRT-LABEL: DESIGN-FAIL: overflow 54031 at round 10 > 1000 |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-3439533 | cbn_q01 | 5_1_grt | 1.8 | grt rounds 2 overflow 5:81921 -> 10:75607 | GRT-LABEL: DESIGN-FAIL: overflow 75607 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hg_v1p3__r838481cd7-1177242 | kv3_hg_v1p3__r838481cd7 | 5_1_grt | 9.1 | grt rounds 2 overflow 5:40256 -> 10:36108 | GRT-LABEL: DESIGN-FAIL: overflow 36108 at round 10 > 1000 |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-3688565 | slw_fe_v2 | generate_abstract | 22.0 | last meaningful line 0.9 h ago (29/29 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2082061 | slw_st_a_v1 | 5_2_route | 6.9 | drt_violations best 612 last 612 rows 11 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc10 | otc-4067299-15490 | 4067299 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc10 | otc-4188785-25915 | 4188785 | signoff | 0.5 | last meaningful line 0.3 h ago (3/3 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261125_153001_3155820-i1t-2575664 | eco_20261125_153001_3155820-i1t | 5_2_route | 1.2 | drt_violations best 209150 last 209150 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-4005800 | col_h9_r0_p5__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 795 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvb22875c0-3520091 | col_h9_r0_p5__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.4052 last 0.4052 rows 32 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc1b82625-3816329 | col_h9_r0_p5__t1 | 3_1_place_gp_skip_io | 0.2 | last meaningful line 0.0 h ago (7/7 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-3668436 | col_h9_r0_p5__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.7501 last 0.7501 rows 21 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pvc93af856-3805063 | col_h9_r0_p5__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9467 last 0.9467 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-3603346 | col_h9_r0_p5__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.2934 last 0.2934 rows 34 | YOUNG: stage 0.1 h < 1 h |  |
| epyc11 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-3660757 | col_h9_r2__t1 | 3_5_place_dp | 0.2 | repair_Violations best 85441 last 85441 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-3816723 | col_h9_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.4861 last 0.4888 rows 9 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvcf44b14c-4018815 | col_h9_r2__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (105/105 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r2__t1__clc9ad8f7e__pvf079625b-3876934 | col_h9_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.4776 last 0.4885 rows 6 | YOUNG: stage 0.0 h < 1 h |  |
| epyc11 | dpkit-col_h9_r2__t1__clce45cab5__pv14626557-3661926 | col_h9_r2__t1 | 3_5_place_dp | 0.2 | last meaningful line -0.0 h ago (61/61 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-col_h9_r2__t1__clce45cab5__pv22267ca0-4000552 | col_h9_r2__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (207/207 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-hd_lep0N-2989918 | hd_lep0N | 5_1_grt | 0.5 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Eo-1420436 | kv3_hub_Eo | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (9193/9193 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Wo-1632470 | kv3_hub_Wo | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (10292/10292 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc11 | dpkit-sle_su_c-2149031 | sle_su_c | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (8837/8837 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1459740 | slw_st_b_v1 | 6_report | 13.5 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_su_c__cl19bb38ef-40900 | slw_su_c | 4_1_cts | 1.9 | last meaningful line 0.1 h ago (8630/8630 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc11 | otc-1109607-10581 | 1109607 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc11 | otc-1616228-26288 | 1616228 | - | 3.1 |  | NO-DATA: no log found |  |
| epyc11 | otc-1830932-23851 | 1830932 | - | 3.0 |  | NO-DATA: no log found |  |
| epyc11 | otc-2255400-11827 | 2255400 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc11 | otc-336507-16010 | 336507 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc11 | otc-381902-2867 | 381902 | - | 7.7 |  | NO-DATA: no log found |  |
| epyc11 | otc-608716-5618 | 608716 | signoff | 1.6 | last meaningful line 1.5 h ago (3/3 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_190641_1260390-i2-3864714 | eco_20261124_190641_1260390-i2 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_200101_1087713-i2-3847060 | eco_20261124_200101_1087713-i2 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (144/144 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | prd-eco_20261125_120946_3832190-i1-2448133 | eco_20261125_120946_3832190-i1 | 5_1_grt | 0.8 | last meaningful line 0.4 h ago (294/542 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | prd-fin-2852121 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (51/51 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc12 | dclk-eco2-otclk-2896808 | dclk-eco2-otclk | - | 0.1 |  | NO-DATA: no log found |  |
| epyc12 | dclk-eco3-otclk-3006836 | dclk-eco3-otclk | - | 0.0 |  | NO-DATA: no log found |  |
| epyc12 | hdmesh-lec-C_relay_e12 | hdmesh-lec-C_relay_e12 | - | 5.4 |  | NO-DATA: no log found |  |
| epyc12 | otc-1273822-29690 | 1273822 | drc_parent_only | 2.9 | last meaningful line -0.0 h ago (974/974 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc12 | otc-1275997-12067 | 1275997 | drc_merged | 2.9 | last meaningful line -0.0 h ago (761/761 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc12 | otc-1278426-9051 | 1278426 | drc_merged | 2.9 | last meaningful line 0.0 h ago (749/749 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc12 | otc-1291490-1984 | 1291490 | drc_merged | 2.9 | last meaningful line 0.0 h ago (689/689 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc12 | otc-1294027-30241 | 1294027 | drc_merged | 2.9 | last meaningful line 0.0 h ago (785/785 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc12 | otc-1305696-4661 | 1305696 | drc_merged | 2.9 | last meaningful line 0.0 h ago (1100/1100 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc12 | otc-1308959-15081 | 1308959 | drc_merged | 2.9 | last meaningful line 0.0 h ago (743/743 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc12 | otc-1312023-14782 | 1312023 | drc_merged | 2.9 | last meaningful line -0.0 h ago (1148/1148 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc12 | otc-1314683-28749 | 1314683 | drc_merged | 2.9 | last meaningful line 0.0 h ago (872/872 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc12 | otc-1338915-16694 | 1338915 | drc_merged | 2.9 | last meaningful line 0.0 h ago (800/800 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc12 | otc-1460135-77 | 1460135 | - | 4.5 |  | NO-DATA: no log found |  |
| epyc12 | otc-1994529-22240 | 1994529 | flow | 2.5 | repair_Violations best 126015 last 126015 rows 31 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc12 | otc-1995249-22339 | 1995249 | flow | 2.5 | repair_Violations best 170848 last 170848 rows 18 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc12 | otc-2211978-2670 | 2211978 | asbuilt.yosys | 0.4 | last meaningful line -0.0 h ago (136685/136685 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc12 | otc-2349462-31924 | 2349462 | asbuilt.yosys | 0.3 | last meaningful line -0.0 h ago (136494/136494 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc12 | otc-2513776-9699 | 2513776 | asbuilt.yosys | 0.2 | last meaningful line -0.0 h ago (135225/135225 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | otc-2611045-8525 | 2611045 | asbuilt.yosys | 0.2 | last meaningful line 0.0 h ago (135527/135527 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc12 | otc-3040450-28203 | 3040450 | ot_bind_native_394b18b76348cdec349b86c8 | 0.0 | last meaningful line -0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc12 | otc-3501458-13012 | 3501458 | drc_merged | 5.4 | last meaningful line 2.3 h ago (334/334 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc12 | otc-351743-16220 | 351743 | hcpg_run | 3.2 | last meaningful line 2.8 h ago (13/13 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-sle-fw-v2--cl6740750e-dump-742373 | sle-fw-v2--cl6740750e-dump | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-sle-fw-v2--cl6740750e-grt-742373 | sle-fw-v2--cl6740750e-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-3326732 | sle_st_a_v1 | 5_2_route | 7.0 | drt_violations best 3 last 3 rows 43 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261125_075050_2599201-i1-3410249 | eco_20261125_075050_2599201-i1 | 5_2_route | 0.9 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-fin-1352759 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | qcdrt-fw-A | qcdrt-fw-A | - | 3.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-B | qcdrt-fw-B | - | 3.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-fw-C | qcdrt-fw-C | - | 3.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-A | qcdrt-sc-A | - | 3.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-B | qcdrt-sc-B | - | 3.2 |  | NO-DATA: no log found |  |
| epyc2 | qcdrt-sc-C | qcdrt-sc-C | - | 3.2 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-coll_core-3493022 | coll_core | 5_1_grt | 7.2 | last meaningful line 0.3 h ago (3038/3055 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_mesh-1705919 | hd_mesh | 3_3_place_gp | 0.9 | overflow best 0.2998 last 0.3569 rows 143 | YOUNG: stage 0.6 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v12e-1804185 | kv3_pv_v12e | 4_1_cts | 0.8 | last meaningful line 0.2 h ago (11857/11857 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v6e-646291 | kv3_pv_v6e | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (8496/8496 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-1311150 | sle_ctl | postcts_gate_TT | 16.1 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-3829314 | sle_ctl | 4_1_cts | 3.3 | last meaningful line 0.3 h ago (10916/10916 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-284995 | sle_fw_v1 | 4_1_cts | 3.0 | last meaningful line 0.1 h ago (5222/5222 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3588855 | sle_hc1 | 5_2_route | 10.4 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-3492718 | sle_sc_v1 | 5_2_route | 7.2 | last meaningful line 0.1 h ago (260/260 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3489531 | sle_sc_v1 | 5_2_route | 7.2 | last meaningful line 0.2 h ago (131/131 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-22145 | sle_sc_v2 | postcts_gate_FF | 1.5 | last meaningful line 0.0 h ago (2031/2031 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__clc6d66f5b-2521917 | sle_su_l1 | 5_2_route | 7.7 | drt_violations best 6149 last 6149 rows 4 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2604222 | slw_sc_v1 | 5_2_route | 7.6 | last meaningful line 0.1 h ago (266/266 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3879530 | slw_sc_v1 | 5_2_route | 10.3 | drt_violations best 456468 last 456468 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-2861168 | slw_su_l1 | 5_2_route | 0.4 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | otc-2858837-8104 | 2858837 | - | 2.0 |  | NO-DATA: no log found |  |
| epyc7 | otc-2938337-22499 | 2938337 | - | 3.7 |  | NO-DATA: no log found |  |
| epyc7 | otc-2958007-4014 | 2958007 | - | 3.7 |  | NO-DATA: no log found |  |
| epyc7 | otc-3693543-29719 | 3693543 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | otc-3961608-5046 | 3961608 | gen_lint_yosys | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | otc-740568-7161 | 740568 | drc_merged | 2.8 | last meaningful line 0.0 h ago (938/938 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | otc-830728-15409 | 830728 | drc_merged | 2.8 | last meaningful line 0.0 h ago (821/821 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | otc-831702-28906 | 831702 | drc_merged | 2.8 | last meaningful line 0.0 h ago (872/872 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | otc-833865-16155 | 833865 | drc_merged | 2.8 | last meaningful line 0.0 h ago (995/995 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | so_1885005_ff_49255 | so_1885005_ff_49255 | generate_abstract | 0.8 | last meaningful line 0.8 h ago (33/33 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | so_2056694_ff_86739 | so_2056694_ff_86739 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (35/35 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | so_2056694_tt_86739 | so_2056694_tt_86739 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (35/35 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | so_2217724_ff_55845 | so_2217724_ff_55845 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | so_2217724_tt_55845 | so_2217724_tt_55845 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-918588 | col_h10_r0_p1__t1 | pregrt_ff_hold | 4.5 | repair_TNS best 75222.8 last 75222.8 rows 1 | YOUNG: evidence 1.7 h < 2.5 h |  |
| epyc8 | dpkit-coll_ftn-3113784 | coll_ftn | 3_3_place_gp | 0.1 | last meaningful line -0.0 h ago (141/141 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v3n-2522162 | kv3_pv_v3n | 5_1_grt | 4.0 | last meaningful line 0.8 h ago (275/1280 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_sys_SD-2387234 | kv3_sys_SD | 3_3_place_gp | 0.3 | overflow best 0.6713 last 0.6925 rows 12 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-native59-3301533 | native59 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | generate_abstract | 24.6 | last meaningful line 0.8 h ago (27/27 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl115da35f-2926018 | sle_sc_v1 | 1_synth | 0.1 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-2731639 | sle_sc_v1 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t26-1760165 | slice_station__t26 | 3_4_place_resized | 0.5 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2782083 | slw_sc_v1 | reg_fanout | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | eco-abs-983313 | eco-abs | generate_abstract | 0.7 | last meaningful line 0.1 h ago (31/31 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | otc-1220115-969 | 1220115 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-1288521-5795 | 1288521 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-132122-8685 | 132122 | - | 4.8 |  | NO-DATA: no log found |  |
| epyc8 | otc-1609200-26446 | 1609200 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-1616827-18813 | 1616827 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc8 | otc-1982827-8639 | 1982827 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc8 | otc-2113939-31863 | 2113939 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261125_025941_3548303-i2-1098320 | eco_20261125_025941_3548303-i2 | 5_1_grt | 0.6 | last meaningful line 0.3 h ago (293/379 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | prd-eco_20261125_104318_3955073-i1-65595 | eco_20261125_104318_3955073-i1 | 5_2_route | 2.2 | drt_violations best 8928 last 8928 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | prd-fin-1582033 | fin | 6_report | 0.5 | last meaningful line 0.2 h ago (21/21 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | so_2135476_ff_4699 | so_2135476_ff_4699 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (33/33 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | so_2135476_tt_4699 | so_2135476_tt_4699 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (33/33 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | so_3257503_ff_52185 | so_3257503_ff_52185 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | so_3257503_tt_52185 | so_3257503_tt_52185 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | so_3260279_ff_68275 | so_3260279_ff_68275 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | so_3260279_tt_68275 | so_3260279_tt_68275 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | so_73079_ff_51781 | so_73079_ff_51781 | generate_abstract | 0.9 | last meaningful line 0.8 h ago (33/33 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | so_73079_tt_51781 | so_73079_tt_51781 | generate_abstract | 0.9 | last meaningful line 0.8 h ago (33/33 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | so_773309_ff_5523 | so_773309_ff_5523 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | so_773309_tt_5523 | so_773309_tt_5523 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (33/33 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-dsdv-slice-lepe-mu-C--t1-grt-1906965 | dsdv-slice-lepe-mu-C--t1-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-kv-leaf--t1-grt-1774870 | ot-s81sl-kv-leaf--t1-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-serdes--t12-grt-2253594 | serdes--t12-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-3686543 | col_h10_r0_p1__t1 | 5_1_grt | 10.0 | last meaningful line 0.2 h ago (1318/1378 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvf60ac9dc-1427167 | col_h10_r0_p1__t1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3489/3489 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2175059 | col_h10_r0_p4__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2753/2753 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvd8c0565f-1181305 | col_h10_r0_p4__t1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3079/3079 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3693676 | col_h10_r1__t1 | 5_1_grt | 10.0 | last meaningful line 1.0 h ago (270/1290 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__clac068e56-1529649 | col_h10_r2__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 32975.8 last 32975.8 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3698869 | col_h9_r0_p4__t1 | 5_2_route | 7.9 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv35382794-3629045 | col_h9_r0_p5__t1 | 5_2_route | 10.0 | last meaningful line 0.2 h ago (289/290 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pv8995e794-2664422 | col_h9_r0_p5__t1 | 4_2_tapbal_grt | 0.8 | last meaningful line 0.0 h ago (62/65 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-4058305 | col_h9_r0_p5__t1 | 5_2_route | 7.2 | last meaningful line 0.2 h ago (275/275 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49636389-2391990 | col_h9_r1__t1 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-1864527 | col_h9_r1__t1 | 4_2_tapbal_grt | 0.9 | last meaningful line 0.3 h ago (61/73 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clb8d86cd5__pv8d57997d-1762039 | col_h9_r2__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 89205.9 last 89205.9 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-2945122 | col_h9_r2__t1 | tt_setup_repair | 0.7 | repair_Remaining best 34862 last 34862 rows 89 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-2312220 | col_h9_r2__t1 | tt_setup_repair | 0.8 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pvc6132d1e-1657557 | col_h9_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.4768 last 0.4768 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t7-3863913 | dsdv_slice_c1x_C__t7 | 3_5_place_dp | 4.3 | last meaningful line 0.1 h ago (38/38 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-2186209 | dsdv_slice_lepe_nh_mus_LP__t1 | pregrt_ff_hold | 0.9 | repair_TNS best 81200.7 last 81200.7 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-2726055 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 0.7 | repair_TNS best 52006.2 last 52006.2 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t11-2006269 | ot_s81sl_leaf__t11 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t52-2064181 | ot_s81sl_leaf__t52 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (89/89 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-3479533 | slice_station__t37 | 5_2_route | 7.9 | drt_violations best 34873 last 34873 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t40__clc8fb2c8c-2653854 | slice_station__t40 | pregrt_ff_hold | 0.8 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc9 | dpkit-slice_station__t41-1123489 | slice_station__t41 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (4141/4141 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t43-3486441 | slice_station__t43 | 6_report | 7.9 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t44-2657480 | slice_station__t44 | 5_2_route | 2.9 | drt_violations best 17335 last 17335 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-2620358 | slice_station__t52 | 5_2_route | 6.7 | drt_violations best 33724 last 33724 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | otc-1865534-29853 | 1865534 | - | 2.3 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2686622 | col_h10_r0_p4__t1 | pregrt_ff_hold | 3.9 | repair_TNS best 96462.2 last 96462.2 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-2667844 | col_h10_r0_p4__t1 | pregrt_ff_hold | 3.9 | repair_TNS best 71771.6 last 71771.6 rows 1 | YOUNG: evidence 1.3 h < 2.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2862987 | col_h9_r1__t1 | 4_2_tapbal_grt | 3.8 | last meaningful line 3.0 h ago (61/99 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv387d6579-3017646 | col_h9_r1__t1 | 4_2_tapbal_grt | 3.7 | last meaningful line 3.0 h ago (61/89 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-2684020 | col_h9_r1__t1 | 4_2_tapbal_grt | 3.9 | last meaningful line 3.0 h ago (61/90 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_sys_c-4063347 | kv3_sys_c | postcts_gate_TT | 5.7 | last meaningful line 0.1 h ago (1176/1176 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3315217 | sle_hc0 | 5_2_route | 15.7 | last meaningful line 0.8 h ago (273/274 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t27-4040446 | slice_station__t27 | 5_2_route | 5.7 | last meaningful line 0.2 h ago (255/256 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3426610 | slw_fe_v1 | 5_2_route | 17.4 | last meaningful line 0.5 h ago (266/267 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-2258671 | slw_st_b_v2 | 5_2_route | 18.2 | last meaningful line 0.5 h ago (273/274 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | otc-1343902-2148 | 1343902 | flow | 0.9 | last meaningful line 0.0 h ago (2872/2872 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | otc-1750914-12376 | 1750914 | flow | 0.7 | last meaningful line 0.0 h ago (2889/2889 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | otc-2284893-4545 | 2284893 | flow | 0.5 | last meaningful line 0.0 h ago (2736/2736 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | otc-3454190-17235 | 3454190 | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | otc-3455270-20805 | 3455270 | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | otc-574655-9239 | 574655 | drc_parent_only | 2.9 | last meaningful line 0.0 h ago (800/800 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | otc-578793-24959 | 578793 | drc_parent_only | 2.9 | last meaningful line 0.0 h ago (545/545 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | otc-582965-3828 | 582965 | drc_merged | 2.9 | last meaningful line 0.0 h ago (284/284 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | otc-586189-14994 | 586189 | drc_parent_only | 2.9 | last meaningful line 0.0 h ago (794/794 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | otc-589045-16647 | 589045 | drc_merged | 2.9 | last meaningful line 0.0 h ago (377/377 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i3t-2681077 | eco_20261123_191853_2879776-i3t | 5_2_route | 5.9 | last meaningful line 0.2 h ago (293/294 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | prd-eco_20261125_040243_2843749-i1-851245 | eco_20261125_040243_2843749-i1 | 5_2_route | 4.6 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | prd-eco_20261125_050013_1448739-i1-3109373 | eco_20261125_050013_1448739-i1 | 5_2_route | 3.7 | last meaningful line 0.5 h ago (268/269 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | prd-eco_20261125_070347_2847958-i1-3642895 | eco_20261125_070347_2847958-i1 | 5_1_grt | 1.6 | last meaningful line 0.3 h ago (295/304 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | prd-eco_20261125_082621_46745-i1-2873810 | eco_20261125_082621_46745-i1 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | so_2067287_ff_39738 | so_2067287_ff_39738 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (34/34 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | so_2067287_tt_39738 | so_2067287_tt_39738 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (34/34 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-coll_ft__cl78c7b300-1300712 | coll_ft | 2_4_floorplan_pdn | 0.0 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-1141936 | coll_ftm | 5_2_route | 1.5 | last meaningful line 0.1 h ago (240/241 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-1333904 | coll_ftm | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-hd_ctl-1014894 | hd_ctl | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-hd_host_w-413405 | hd_host_w | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3930/3930 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-762822 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-3387973 | kv3_io_ft | 5_2_route | 0.7 | last meaningful line 0.0 h ago (216/217 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-1887004 | slice_station__t12 | abstract_exact | 1.2 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi-1955823 | kv3_hgi | 5_2_route | 6.9 |  | KEEP: kv3_hgi_1124155644	KV-OWN-RSTREACH	combined HEADLEG2+HGI-LEAF ship form; noprog  |  |
| epyc11 | dpkit-col_h9_r2__t1__cl774acf45__pvea45273b-3843867 | col_h9_r2__t1 | 3_3_place_gp | 0.2 |  | KEEP: col_h9_r2__t1__cl774acf45__pvea45273b	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc11 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv45d0c698-3806678 | col_h9_r2__t1 | 3_3_place_gp | 0.2 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-native59-3384403 | native59 | 5_2_route | 14.2 | drt_violations best 0 last 0 rows 10 | PROGRESS: drt_violations reached 0 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3727977 | slw_fe_v1 | 5_2_route | 21.9 | drt_violations best 289 last 289 rows 31 | before-window best 71235, window best 289 | PROGRESS: drt_violations improved 99.6 % in window |  |
| epyc10 | prd-eco_20261125_073109_4058437-i1-634237 | eco_20261125_073109_4058437-i1 | 5_2_route | 3.9 | drt_violations best 0 last 0 rows 4 | PROGRESS: drt_violations reached 0 |  |
| epyc11 | dpkit-col_h9_r2__t1__cl774acf45__pve3ab90e7-3528722 | col_h9_r2__t1 | 3_5_place_dp | 0.3 | repair_Violations best 0 last 0 rows 25 | PROGRESS: repair_Violations reached 0 |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 5_2_route | 23.2 | drt_violations best 20 last 20 rows 32 | before-window best 15970, window best 20 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc7 | dpkit-serdes__t4-2700198 | serdes__t4 | 4_1_cts | 0.5 | repair_Violations best 0 last 0 rows 4 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3817081 | sle_st_a_v2 | 5_2_route | 8.7 | drt_violations best 72 last 72 rows 54 | before-window best 143821, window best 72 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 5_2_route | 24.6 | drt_violations best 42 last 42 rows 35 | before-window best 266434, window best 42 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvc9270d09-1494595 | col_h10_r0_p4__t1 | 4_2_tapbal_grt | 1.0 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvbca8d846-1384417 | col_h9_r0_p5__t1 | 4_2_tapbal_grt | 1.0 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pv467913cc-4189655 | col_h9_r2__t1 | 5_2_route | 11.9 | drt_violations best 659 last 961 rows 19 | before-window best 162909, window best 659 | PROGRESS: drt_violations improved 99.6 % in window |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pva8c07948-1151424 | col_h9_r2__t1 | 4_1_cts | 0.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-691174 | col_h9_r2__t1 | 5_2_route | 11.0 | drt_violations best 386 last 386 rows 23 | before-window best 163283, window best 386 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-628088 | slw_fe_v1 | 5_2_route | 21.7 | drt_violations best 4 last 4 rows 53 | before-window best 56, window best 4 | PROGRESS: drt_violations improved 92.9 % in window |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-2511530 | col_h9_r2__t1 | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9a22736e-2872121 | col_h9_r2__t1 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pva119e808-2308652 | col_h9_r2__t1 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS last 0 (TNS >= 0: converged/done, not stalled; never cancelled) |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3889285 | sle_st_b_v1 | 5_2_route | 20.0 | drt_violations best 19233 last 19233 rows 2 | before-window best 138407, window best 19233 | PROGRESS: drt_violations improved 86.1 % in window |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 5_2_route | 27.9 | drt_violations best 2876 last 2876 rows 12 | before-window best 71761, window best 2876 | PROGRESS: drt_violations improved 96.0 % in window |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1869475 | slw_hc0 | 5_2_route | 18.5 | drt_violations best 18062 last 18062 rows 3 | before-window best 174940, window best 18062 | PROGRESS: drt_violations improved 89.7 % in window |  |
| intel1 | prd-eco_20261125_002226_1452841-i1t-3347319 | eco_20261125_002226_1452841-i1t | 5_2_route | 8.3 | drt_violations best 9407 last 9407 rows 1 | before-window best 9407, window best 9407 | PROGRESS: drt_violations: active iteration at 2810 < best completed total 9407 (in-iterati |  |
| intel1 | prd-eco_20261125_072849_2847456-i1-527377 | eco_20261125_072849_2847456-i1 | 5_1_grt | 1.2 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 5_2_route | 23.1 | drt_violations best 674 last 674 rows 23 | before-window best 9186, window best 674 | PROGRESS: drt_violations improved 92.7 % in window |  |
