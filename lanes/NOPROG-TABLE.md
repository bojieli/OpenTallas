# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 10:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 8, 'GRT-LABEL': 2, 'YOUNG': 181, 'NO-DATA': 9, 'PROGRESS': 32}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-2159263 | slw_hc1 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair_grt | 16.4 | repair_Violations best 0 last 0 rows 93 | before-window best 0, window best - | NO-PROGRESS: no new repair_Violations row in 6 h | REPORT-ONLY: lane-own kit (OPUS-FIX-QC-V4-R2 decid |
| epyc7 | dpkit-sle_st_b_v1__pv0e7b1dcc-2157611 | sle_st_b_v1 | pregrt_ff_hold | 5.6 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | tt_setup_repair_grt | 15.8 | repair_Violations best 0 last 0 rows 62 | before-window best 0, window best - | NO-PROGRESS: no new repair_Violations row in 6 h | REPORT-ONLY: lane-own kit (OPUS-FIX-QC-V4-R2 decid |
| epyc8 | prd-eco_20261123_120225_75582-i3t-3968210 | eco_20261123_120225_75582-i3t | 5_2_route | 9.4 | drt_violations best 11 last 78 rows 44 | before-window best 11, window best 22 | NO-PROGRESS: drt_violations best 22 vs 11 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1365381 | sle_st_b_v1 | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 18.4 | last meaningful line 7.6 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 7.6 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 22.2 | last meaningful line 7.6 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 7.6 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc10 | dpkit-kv3_hgi_v2__cle0015330-630449 | kv3_hgi_v2 | 5_1_grt | 1.7 | grt rounds 2 overflow 5:8510 -> 10:2831 | GRT-LABEL: DESIGN-FAIL: overflow 2831 at round 10 > 1000 |  |
| epyc11 | dpkit-kv3_pv_v2ne-269596 | kv3_pv_v2ne | 5_1_grt | 3.9 | grt rounds 1 overflow 5:64721 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-kv3-hgi-v8-grt-2669100 | kv3-hgi-v8-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (136/136 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 1.3 | last meaningful line 0.1 h ago (48/49 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | tt_setup_measure | 1.6 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v3-1126078 | kv3_hg_v3 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (6305/6305 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v4-677838 | kv3_hgi_v4 | 5_1_grt | 1.7 | last meaningful line -0.0 h ago (13/13 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v5-2589918 | kv3_hgi_v5 | 2_1_floorplan | 0.2 | last meaningful line 0.1 h ago (1306/1306 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v5-772924 | kv3_hgi_v5 | pregrt_ff_hold | 1.6 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.7 h < 2.5 h |  |
| epyc10 | dpkit-kv3_pv-1051314 | kv3_pv | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (10205/10205 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v1e-1282383 | kv3_pv_v1e | 5_1_grt | 1.2 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v2-1075302 | kv3_pv_v2 | tt_setup_repair | 1.3 | last meaningful line 0.0 h ago (349/349 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v2e-252410 | kv3_pv_v2e | 5_1_grt | 2.0 | last meaningful line 0.5 h ago (269/1275 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v2n-1048434 | kv3_pv_v2n | pregrt_ff_hold | 1.4 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc10 | dpkit-kv3_pv_v4-680976 | kv3_pv_v4 | pregrt_ff_hold | 1.7 | repair_TNS best 43273.9 last 43273.9 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v4e-1194094 | kv3_pv_v4e | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (7600/7600 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v5n-698511 | kv3_pv_v5n | tt_setup_repair | 1.7 | last meaningful line 0.0 h ago (437/437 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v6-908877 | kv3_pv_v6 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (8546/8546 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v6e-760052 | kv3_pv_v6e | 5_1_grt | 1.6 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v6n-1030440 | kv3_pv_v6n | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (6968/6968 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v7-1199684 | kv3_pv_v7 | tt_setup_repair | 1.2 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v7e-1156836 | kv3_pv_v7e | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (11047/11047 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_sys_c-2055961 | kv3_sys_c | 3_3_place_gp | 0.6 | overflow best 0.1926 last 0.1926 rows 43 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (6562/6562 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2793057 | sle_stm_v1 | reg_fanout | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-2082988 | slw_hc3 | 5_1_grt | 4.1 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-1941362-12113 | 1941362 | signoff | 0.7 | last meaningful line 0.6 h ago (3/3 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | otc-2821279-12652 | 2821279 | sta | 0.0 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-2821929-15962 | 2821929 | sta | 0.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | ap-ageom-kw-kv3-hgi-v7-grt-987905 | kv3-hgi-v7-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 4.6 | last meaningful line 1.1 h ago (48/59 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hgi_v8-395293 | kv3_hgi_v8 | 3_3_place_gp | 0.7 | overflow best 0.1328 last 0.1328 rows 44 | YOUNG: stage 0.2 h < 1 h |  |
| epyc11 | dpkit-kv3_hub_Eo-614287 | kv3_hub_Eo | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.1 h ago (52/52 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc11 | dpkit-kv3_io_cor-3977350 | kv3_io_cor | 5_2_route | 4.1 | drt_violations best 126627 last 126627 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v3e-3783354 | kv3_pv_v3e | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (12222/12222 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v4ne-3869988 | kv3_pv_v4ne | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (7633/7633 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (5868/5868 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_fw_v1__cl9d029624-1087895 | sle_fw_v1 | generate_abstract | 13.3 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_fw_v1__cl9d029624-56648 | sle_fw_v1 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (5130/5130 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 13.4 | drt_violations best 23959 last 23959 rows 9 | YOUNG: evidence 7.1 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | 4_1_cts | 1.0 | last meaningful line 0.2 h ago (5640/5640 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (5566/5566 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (5584/5584 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-1187645 | slw_fw_v1 | 6_report | 13.2 | last meaningful line 0.1 h ago (1073/1073 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc11 | dpkit-slw_fw_v3-263804 | slw_fw_v3 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (4838/4838 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc2__cl6bcaba89-3858415 | slw_hc2 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (4983/4983 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3838177 | slw_hc3 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (4991/4991 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (5309/5309 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-320042 | slw_st_b_v2 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (4834/4834 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc11 | lecautofill-hd_mesh | lecautofill-hd_mesh | - | 15.0 |  | NO-DATA: no log found |  |
| epyc11 | prd-eco_20261124_154417_1016084-i1t-3435586 | eco_20261124_154417_1016084-i1t | 5_2_route | 1.7 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | so_1073972_ff_36075 | so_1073972_ff_36075 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc11 | so_1073972_tt_36075 | so_1073972_tt_36075 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-cbn_q00__cl622f65d2-3557026 | cbn_q00 | pregrt_ff_hold | 0.3 | repair_TNS best 64860.7 last 64860.7 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-coll_ftm-1783743 | coll_ftm | postcts_gate_FF | 1.5 | last meaningful line 0.0 h ago (2235/2235 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-glue-3558834 | glue | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5654/5654 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | pregrt_ff_hold | 3.6 | repair_TNS best 758714 last 758714 rows 1 | YOUNG: evidence 1.8 h < 2.5 h |  |
| epyc2 | dpkit-kv3_hgi_v7-2608982 | kv3_hgi_v7 | 5_1_grt | 3.6 | last meaningful line 0.8 h ago (295/1303 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v8-2448463 | kv3_hgi_v8 | 5_1_grt | 3.7 | last meaningful line 0.8 h ago (300/1307 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v5ne-2612763 | kv3_pv_v5ne | pregrt_ff_hold | 3.6 | repair_TNS best 827598 last 827598 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 5.8 | drt_violations best 2657 last 2657 rows 10 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | postcts_gate_FF | 9.5 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-1772768 | sle_hc0 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (5723/5723 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3414126 | sle_hc2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4711/4711 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__clcc5e3e61-3434617 | sle_hc2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4926/4927 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 5.7 | last meaningful line 0.0 h ago (253/253 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-1186805 | sle_sc_v3 | 5_2_route | 4.8 | last meaningful line 0.1 h ago (266/267 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-1784944 | sle_st_a_v1 | 5_1_grt | 1.4 | last meaningful line 0.1 h ago (1308/2077 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-1826228 | sle_st_a_v1 | 5_1_grt | 1.4 | last meaningful line 0.1 h ago (1305/2063 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-1538145 | sle_st_a_v2 | tt_setup_repair_grt | 1.6 | repair_Viol best 53 last 53 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_su_l0__cl7a55c676-4027948 | sle_su_l0 | 5_2_route | 5.7 | drt_violations best 729 last 729 rows 5 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3602061 | sle_su_l1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3785/3785 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3626034 | slw_hc3 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (4395/4395 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v3-3708441 | slw_sc_v3 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (3769/3769 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3657462 | slw_stm_v2 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (6022/6023 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l0__cl1a1c1f8f-4150554 | slw_su_l0 | 5_2_route | 5.6 | drt_violations best 10 last 10 rows 12 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | prd-count-p1_tc-1317564 | count-p1_tc | prd_count_p1_tc | 0.2 | last meaningful line 0.1 h ago (1051/1051 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-1850782 | hd_lep0N_w | pregrt_ff_hold | 1.3 | repair_TNS best 27212.1 last 27212.1 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-2222980 | sle_fw_v2 | 4_1_cts | 1.1 | last meaningful line 0.3 h ago (6721/6721 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 10.9 | drt_violations best 490378 last 490378 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_2_route | 7.0 | last meaningful line 0.2 h ago (261/261 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | postcts_gate_TT | 5.7 | last meaningful line 0.1 h ago (961/961 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (4394/4394 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (5548/5548 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | 5_2_route | 11.0 | drt_violations best 14619 last 14619 rows 3 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | 5_2_route | 6.9 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl1bc59e1c-2061343 | slw_hc0 | 4_1_cts | 1.2 | last meaningful line 0.2 h ago (5511/5511 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | 4_1_cts | 1.2 | last meaningful line 0.2 h ago (5557/5557 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (5671/5671 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-2253577 | slw_hc2 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (5082/5082 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | tt_setup_measure_grt | 5.5 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-2333813 | slw_sc_v1 | tt_setup_repair_grt | 5.5 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 11.1 | drt_violations best 407677 last 407677 rows 1 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 7.2 | last meaningful line 0.3 h ago (275/276 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (4903/4903 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | 5_2_route | 11.3 | drt_violations best 17304 last 17304 rows 2 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | 5_1_grt | 5.5 | last meaningful line 0.1 h ago (282/350 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | 5_2_route | 7.2 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (4933/4933 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i3t-3392092 | eco_20261123_171023_3055226-i3t | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (139/139 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_175441_992552-i1t-3184147 | eco_20261124_175441_992552-i1t | 5_2_route | 0.5 | last meaningful line 0.0 h ago (247/247 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-coll_ftc-3942021 | coll_ftc | 5_1_grt | 2.1 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-coll_s-3875643 | coll_s | 5_2_route | 2.2 | last meaningful line 0.0 h ago (244/245 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v4n-177384 | kv3_pv_v4n | 5_1_grt | 2.0 | last meaningful line 0.2 h ago (264/1268 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 4_1_cts | 2.1 | last meaningful line 0.3 h ago (6125/6125 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v3-3927550 | sle_fe_v3 | 5_2_route | 2.1 | drt_violations best 23202 last 23202 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 4_1_cts | 2.1 | last meaningful line 0.2 h ago (5565/5565 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (5725/5725 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl22c1ff36__pve230954c-3918742 | sle_hc1 | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (5737/5737 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 4_1_cts | 2.1 | last meaningful line 0.0 h ago (5809/5809 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | 4_1_cts | 2.2 | last meaningful line 0.2 h ago (5610/5610 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | 4_1_cts | 2.2 | last meaningful line 0.2 h ago (5284/5284 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_1_grt | 2.1 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v3-4127450 | sle_sc_v3 | 5_1_grt | 2.1 | last meaningful line 0.2 h ago (1279/1824 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-4063882 | sle_st_a_v2 | 5_2_route | 2.1 | last meaningful line 0.0 h ago (263/264 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (5676/5676 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | tt_setup_repair | 2.1 | last meaningful line 0.0 h ago (459/459 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | hold_gate | 2.1 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v1__clbe630b9c-4072662 | sle_stm_v1 | pregrt_ff_hold | 2.1 | repair_TNS best 4271.2 last 4271.2 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | pregrt_ff_hold | 2.1 | repair_TNS best 2098.62 last 2098.62 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-sle_su_l0__cl7a55c676-4020210 | sle_su_l0 | 5_1_grt | 2.1 | last meaningful line 0.0 h ago (1847/1885 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (5605/5605 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 4_1_cts | 2.1 | last meaningful line 0.2 h ago (5678/5678 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 4_1_cts | 2.1 | last meaningful line 0.2 h ago (5738/5738 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (5323/5323 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | tt_setup_repair_grt | 5.4 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | 4_1_cts | 2.2 | last meaningful line 0.2 h ago (5390/5390 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3909116 | slw_hc3 | 4_1_cts | 2.2 | last meaningful line 0.1 h ago (5227/5227 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-3949912 | slw_hc3 | tt_setup_repair | 2.1 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_1_grt | 2.1 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_1_grt | 2.0 | last meaningful line 0.2 h ago (141/141 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | postcts_gate_TT | 2.1 | last meaningful line 0.1 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | tt_setup_repair | 2.1 | last meaningful line 0.0 h ago (468/468 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-3848540 | slw_su_l0 | tt_setup_repair_grt | 2.2 | last meaningful line 0.0 h ago (329/329 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 2.1 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-fin-2385296 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (246/246 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hub_Wo-2104173 | kv3_hub_Wo | 3_1_place_gp_skip_io | 1.1 | overflow best 0.1199 last 0.1199 rows 46 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-kv3_sys_SD-3260212 | kv3_sys_SD | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (156/156 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__clf58b4dfb-1918057 | sle_fw_v1 | 3_3_place_gp | 1.2 | overflow best 0.0998 last 0.0998 rows 41 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-2104596 | sle_hc1 | 3_3_place_gp | 1.1 | overflow best 0.0999 last 0.0999 rows 176 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-slw_fw_v3-2229849 | slw_fw_v3 | 3_4_place_resized | 1.0 | last meaningful line 0.2 h ago (339/339 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_stm_v1__cle34a73c3-2386039 | slw_stm_v1 | 3_3_place_gp | 1.0 | overflow best 0.0989 last 0.0989 rows 44 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | eco-abs-2496718 | eco-abs | generate_abstract | 0.9 | last meaningful line 0.1 h ago (1032/1032 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | otc-1814577-31530 | 1814577 | - | 3.9 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261123_224216_149959-i3t-3891967 | eco_20261123_224216_149959-i3t | 5_2_route | 2.5 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i2-1242463 | eco_20261124_010152_2867084-i2 | 5_2_route | 4.2 | drt_violations best 40 last 40 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl1b5a6458-4114232 | cbf_q00 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (6406/6406 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-cbn_q11__cl5cc92dfe-4036084 | cbn_q11 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (4952/4952 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-coll_core-3813096 | coll_core | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (7253/7253 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-coll_ft__cl78c7b300-2325645 | coll_ft | 5_2_route | 1.8 | drt_violations best 11693 last 11693 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel1 | dpkit-hd_lep0N-2597425 | hd_lep0N | 3_5_place_dp | 1.6 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v4-521791 | kv3_hgi_v4 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 4_1_cts | 3.1 | last meaningful line 0.3 h ago (12640/12640 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3ne-3760907 | kv3_pv_v3ne | 5_1_grt | 3.6 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v5-1046392 | kv3_pv_v5 | pregrt_ff_hold | 2.5 | repair_TNS best 169718 last 169718 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v8-3837707 | kv3_pv_v8 | pregrt_ff_hold | 3.5 | repair_TNS best 14924.2 last 14924.2 rows 1 | YOUNG: evidence 1.6 h < 2.5 h |  |
| intel1 | dpkit-kv3_pv_v8e-3858104 | kv3_pv_v8e | 5_1_grt | 3.5 | last meaningful line 1.2 h ago (265/1274 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-native59-635922 | native59 | 3_5_place_dp | 2.7 | last meaningful line 0.2 h ago (111/111 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 4_1_cts | 1.4 | last meaningful line 0.3 h ago (5762/5762 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3458150 | sle_hc2 | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (5189/5189 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-3662089 | sle_sc_v1 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (5858/5858 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t25-3792073 | slice_station__t25 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t26-252081 | slice_station__t26 | 3_3_place_gp | 0.2 | overflow best 0.2121 last 0.2329 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slice_station__t30__cl1653104c-258733 | slice_station__t30 | 3_3_place_gp | 0.2 | overflow best 0.2371 last 0.2424 rows 38 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slice_station__t51-24069 | slice_station__t51 | 3_3_place_gp | 0.4 | overflow best 0.2334 last 0.2334 rows 29 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | postcts_gate_FF | 3.8 | last meaningful line 0.3 h ago (1693/1693 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3463031 | slw_hc1 | 4_1_cts | 0.9 | last meaningful line 0.2 h ago (5673/5673 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2973163 | slw_hc3 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (4949/4949 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (5315/5315 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | 5_1_grt | 5.6 | last meaningful line 0.2 h ago (283/912 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (4895/4895 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | otc-1797391-24144 | 1797391 | flow3 | 5.3 | last meaningful line 5.0 h ago (208/209 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel1 | otc-3854277-21865 | 3854277 | - | 3.5 |  | NO-DATA: no log found |  |
| intel1 | otc-530910-29147 | 530910 | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | otc-532079-5545 | 532079 | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261123_191853_2879776-i2t-2852283 | eco_20261123_191853_2879776-i2t | 5_2_route | 1.4 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2905950 | coll_ftm | 5_2_route | 2.0 | drt_violations best 10288 last 10288 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_C-524420 | kv3_hub_C | 2_1_floorplan | 0.9 | last meaningful line 0.5 h ago (1424/1424 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_Wi-487140 | kv3_hub_Wi | 2_1_floorplan | 0.9 | last meaningful line 0.1 h ago (335/335 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-sle_ctl__cla4f6f12f-578782 | sle_ctl | 3_1_place_gp_skip_io | 0.9 | overflow best 0.1438 last 0.1438 rows 47 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-sle_fw_v1__cl9d029624-1286736 | sle_fw_v1 | 3_3_place_gp | 0.5 | overflow best 0.408 last 0.4119 rows 15 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-sle_fw_v3-158839 | sle_fw_v3 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-60615 | sle_st_b_v2 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (5615/5615 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-320673 | slw_fe_v1 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-147855 | slw_fe_v1 | 3_5_place_dp | 1.1 | last meaningful line 0.1 h ago (114/114 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-4052196 | slw_fe_v2 | 3_5_place_dp | 1.2 | last meaningful line 0.1 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (5158/5158 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__clf110fab2-159072 | slw_fe_v2 | 3_5_place_dp | 1.1 | last meaningful line 0.1 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4019330 | slw_fw_v1 | 3_5_place_dp | 1.3 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-159197 | slw_fw_v2 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (4849/4849 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v5e-402621 | kv3_pv_v5e | tt_setup_repair | 1.9 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | dpkit-kv3_pv_v6ne-1050153 | kv3_pv_v6ne | tt_setup_repair | 1.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-kv3_sys_SD_v1-3451438 | kv3_sys_SD_v1 | 5_1_grt | 0.4 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-248626 | sle_st_b_v2 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_stm_v3-1868496 | sle_stm_v3 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1494307 | slw_st_a_v1 | 5_1_grt | 1.7 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-1494646 | slw_st_a_v2 | 5_1_grt | 1.7 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 32.8 | drt_violations best 14975 last 14975 rows 14 | before-window best 22423, window best 14975 | PROGRESS: drt_violations improved 33.2 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 26.1 | drt_violations best 15355 last 15355 rows 14 | before-window best 32431, window best 15355 | PROGRESS: drt_violations improved 52.7 % in window |  |
| epyc7 | dpkit-sle_stm_v3-3494601 | sle_stm_v3 | 5_2_route | 7.4 | drt_violations best 0 last 0 rows 7 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | prd-eco_20261124_145005_2036075-i1-1498701 | eco_20261124_145005_2036075-i1 | 5_2_route | 3.6 | drt_violations best 0 last 0 rows 2 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-4020071 | sle_st_a_v1 | 5_1_grt | 2.1 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | 5_1_grt | 2.1 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l0_wfb17da-849937 | qfd_qc_su_lane_w_l0_wfb17da | 5_1_grt | 4.5 | repair_TNS best 0 last 0 rows 19 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l1_w460927-787688 | qfd_qc_su_lane_w_l1_w460927 | 5_1_grt | 4.5 | repair_TNS best 0 last 0 rows 23 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l4_w285325-818329 | qfd_qc_su_lane_w_l4_w285325 | 5_1_grt | 4.5 | repair_TNS best 0 last 0 rows 51 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l5_wf949e1-824935 | qfd_qc_su_lane_w_l5_wf949e1 | 5_1_grt | 4.5 | repair_TNS best 0 last 0 rows 50 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l6_wb51d05-853896 | qfd_qc_su_lane_w_l6_wb51d05 | 5_1_grt | 4.5 | repair_TNS best 0 last 0 rows 33 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l7_wd4f14d-862251 | qfd_qc_su_lane_w_l7_wd4f14d | 5_1_grt | 4.5 | repair_TNS best 0 last 0 rows 21 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | prd-eco_20261123_224647_4153453-i3t-2877611 | eco_20261123_224647_4153453-i3t | 5_1_grt | 0.6 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-coll_ft__cla4a25d77-56057 | coll_ft | pregrt_ff_hold | 0.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-coll_ucie-4183666 | coll_ucie | 5_1_grt | 0.4 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-native59-1320092 | native59 | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_hc1__cl7d360508__pv97423966-1341249 | sle_hc1 | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-1345836 | sle_hc2 | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1387403 | slw_hc0 | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc1__cl3449ea95-1389354 | slw_hc1 | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-1401912 | slw_hc2 | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 40.4 | drt_violations best 74496 last 74496 rows 15 | before-window best 76746, window best 74496 | PROGRESS: drt_violations improved 2.9 % in window |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 9.7 | drt_violations best 2 last 2 rows 52 | before-window best 20278, window best 2 | PROGRESS: drt_violations improved 100.0 % in window |  |
