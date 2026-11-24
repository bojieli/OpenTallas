# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 10:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 6, 'GRT-LABEL': 1, 'YOUNG': 189, 'NO-DATA': 15, 'PROGRESS': 31}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair_grt | 16.6 | repair_Violations best 0 last 0 rows 93 | before-window best 0, window best - | NO-PROGRESS: no new repair_Violations row in 6 h | REPORT-ONLY: lane-own kit (OPUS-FIX-QC-V4-R2 decid |
| epyc7 | dpkit-sle_st_b_v1__pv0e7b1dcc-2157611 | sle_st_b_v1 | pregrt_ff_hold | 5.6 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | tt_setup_repair_grt | 16.3 | repair_Violations best 0 last 0 rows 62 | before-window best 0, window best - | NO-PROGRESS: no new repair_Violations row in 6 h | REPORT-ONLY: lane-own kit (OPUS-FIX-QC-V4-R2 decid |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1365381 | sle_st_b_v1 | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 18.4 | last meaningful line 7.6 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 7.6 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 22.2 | last meaningful line 7.6 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 7.6 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc11 | dpkit-kv3_pv_v2ne-269596 | kv3_pv_v2ne | 5_1_grt | 4.1 | grt rounds 2 overflow 5:64721 -> 10:51671 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_2_tapbal_grt | 1.8 | last meaningful line 0.5 h ago (48/50 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | pregrt_ff_hold | 2.1 | repair_TNS best 468304 last 468304 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-kv3_hg_v3-1126078 | kv3_hg_v3 | pregrt_ff_hold | 1.8 | repair_TNS best 48765.4 last 48765.4 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-kv3_hgi_v2__cle0015330-3033361 | kv3_hgi_v2 | 3_3_place_gp | 0.3 | overflow best 0.1489 last 0.1489 rows 17 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_hgi_v4-677838 | kv3_hgi_v4 | 5_1_grt | 2.2 | last meaningful line 0.3 h ago (292/1299 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v5-2589918 | kv3_hgi_v5 | 3_3_place_gp | 0.7 | overflow best 0.0989 last 0.0989 rows 48 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-kv3_hgi_v5-772924 | kv3_hgi_v5 | 5_1_grt | 2.1 | last meaningful line 0.0 h ago (287/289 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv-1051314 | kv3_pv | 5_1_grt | 1.9 | last meaningful line 0.5 h ago (263/1270 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | pregrt_ff_hold | 2.0 | repair_TNS best 149411 last 149411 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v2-1075302 | kv3_pv_v2 | pregrt_ff_hold | 1.8 | repair_TNS best 61304.5 last 61304.5 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v2e-252410 | kv3_pv_v2e | 5_1_grt | 2.5 | last meaningful line 1.0 h ago (269/1278 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v2n-1048434 | kv3_pv_v2n | pregrt_ff_hold | 1.9 | repair_TNS best 34496.4 last 34496.4 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v4-680976 | kv3_pv_v4 | pregrt_ff_hold | 2.2 | repair_TNS best 43273.9 last 43273.9 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| epyc10 | dpkit-kv3_pv_v4e-1194094 | kv3_pv_v4e | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (7843/7843 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v5e-402621 | kv3_pv_v5e | pregrt_ff_hold | 2.4 | repair_TNS best 845383 last 845383 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v5n-698511 | kv3_pv_v5n | pregrt_ff_hold | 2.2 | repair_TNS best 32592.1 last 32592.1 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v6-908877 | kv3_pv_v6 | tt_setup_repair | 2.0 | last meaningful line 0.0 h ago (345/345 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v6e-760052 | kv3_pv_v6e | 5_1_grt | 2.1 | last meaningful line 0.3 h ago (268/1272 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v6n-1030440 | kv3_pv_v6n | pregrt_ff_hold | 1.9 | repair_TNS best 30680.7 last 30680.7 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v6ne-1050153 | kv3_pv_v6ne | 5_1_grt | 1.9 | grt_overflow best 2689 last 2689 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v7-1199684 | kv3_pv_v7 | pregrt_ff_hold | 1.7 | repair_TNS best 133545 last 133545 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v7e-1156836 | kv3_pv_v7e | 4_1_cts | 1.8 | last meaningful line 0.1 h ago (11117/11117 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-2208687 | sle_fw_v2 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (6647/6647 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-3227025 | sle_hc0 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9953 last 0.9953 rows 19 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3605780 | sle_st_b_v2 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (109/109 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__clfde1249e-3336251 | sle_st_b_v2 | port_bind | 0.1 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-2793057 | sle_stm_v1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4817/4817 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-3446125 | slw_hc1 | 1_synth | 0.1 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-2082988 | slw_hc3 | 5_1_grt | 4.6 | last meaningful line 0.0 h ago (999/1005 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-3359908 | slw_st_b_v1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (3605/3605 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-3605853-9611 | 3605853 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc11 | dpkit-hd_lep0N-3115110 | hd_lep0N | 4_2_tapbal_grt | 4.9 | last meaningful line 1.3 h ago (48/59 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hgi_v7-1276815 | kv3_hgi_v7 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (6084/6084 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hgi_v8-395293 | kv3_hgi_v8 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (78/78 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-kv3_hub_Eo-614287 | kv3_hub_Eo | 3_1_place_gp_skip_io | 0.8 | overflow best 0.335 last 0.335 rows 36 | YOUNG: stage 0.2 h < 1 h |  |
| epyc11 | dpkit-kv3_io_cor-3977350 | kv3_io_cor | 5_2_route | 4.4 | drt_violations best 30995 last 30995 rows 2 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v3e-3783354 | kv3_pv_v3e | 4_1_cts | 1.6 | last meaningful line 0.2 h ago (12249/12249 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pv_v4ne-3869988 | kv3_pv_v4ne | 4_1_cts | 1.6 | last meaningful line 0.1 h ago (7656/7656 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc11 | dpkit-kv3_pve-1450371 | kv3_pve | postcts_gate_TT | 0.1 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_fe_v1__cl1cbb7497-61367 | sle_fe_v1 | 4_1_cts | 1.2 | last meaningful line 0.2 h ago (5871/5871 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_fw_v1__cl9d029624-1087895 | sle_fw_v1 | generate_abstract | 13.6 | last meaningful line 0.1 h ago (1030/1030 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc11 | dpkit-sle_fw_v1__cl9d029624-56648 | sle_fw_v1 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (5157/5157 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_fw_v2__cl6740750e-1028676 | sle_fw_v2 | 5_2_route | 13.7 | drt_violations best 22940 last 22940 rows 10 | YOUNG: evidence 7.3 h < 7.5 h |  |
| epyc11 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-33523 | sle_hc0 | 4_1_cts | 1.3 | last meaningful line 0.2 h ago (5667/5667 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pv0e7b1dcc-275932 | sle_st_b_v1 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (5610/5610 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-62912 | sle_st_b_v1 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (5612/5612 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc11 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-1187645 | slw_fw_v1 | 6_report | 13.4 | last meaningful line 0.1 h ago (1080/1080 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc11 | dpkit-slw_fw_v3-263804 | slw_fw_v3 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (4881/4881 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc2__cl6bcaba89-3858415 | slw_hc2 | 4_1_cts | 1.6 | last meaningful line 0.2 h ago (5010/5010 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc11 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3838177 | slw_hc3 | 4_1_cts | 1.6 | last meaningful line 0.0 h ago (5123/5123 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v1__cle6023ec2-342632 | slw_st_b_v1 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (5337/5337 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-320042 | slw_st_b_v2 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (4887/4887 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc11 | lecautofill-hd_mesh | lecautofill-hd_mesh | - | 15.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-1237717-1487 | 1237717 | asbuilt.yosys | 0.2 | last meaningful line -0.0 h ago (135274/135274 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | otc-1260420-29535 | 1260420 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc11 | otc-1278604-6905 | 1278604 | asbuilt.yosys | 0.2 | last meaningful line 0.0 h ago (135590/135590 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc11 | prd-eco_20261124_154417_1016084-i1t-3435586 | eco_20261124_154417_1016084-i1t | 5_2_route | 1.9 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc11 | so_1073972_ff_36075 | so_1073972_ff_36075 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc11 | so_1073972_tt_36075 | so_1073972_tt_36075 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-coll_ftm-1783743 | coll_ftm | 5_2_route | 1.7 | last meaningful line 0.0 h ago (248/249 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-glue-3558834 | glue | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5747/5747 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | pregrt_ff_hold | 3.8 | repair_TNS best 758714 last 758714 rows 1 | YOUNG: evidence 2.0 h < 2.5 h |  |
| epyc2 | dpkit-kv3_hgi_v7-2608982 | kv3_hgi_v7 | 5_1_grt | 3.8 | last meaningful line 1.0 h ago (295/1305 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v8-2448463 | kv3_hgi_v8 | 5_1_grt | 4.0 | last meaningful line 1.0 h ago (300/1308 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v5ne-2612763 | kv3_pv_v5ne | pregrt_ff_hold | 3.8 | repair_TNS best 827598 last 827598 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-kv3_sys_SD_v1-3451438 | kv3_sys_SD_v1 | postcts_gate_TT | 0.6 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 6.1 | drt_violations best 2347 last 2347 rows 11 | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | postcts_gate_FF | 9.8 | last meaningful line 0.3 h ago (23/23 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-1772768 | sle_hc0 | 4_1_cts | 1.7 | last meaningful line 0.2 h ago (5750/5750 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-4026959 | sle_hc2 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9987 last 0.9987 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3414126 | sle_hc2 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (4739/4739 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__clcc5e3e61-3434617 | sle_hc2 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (5009/5009 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_2_route | 6.0 | last meaningful line 0.1 h ago (261/262 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-1186805 | sle_sc_v3 | 5_2_route | 5.0 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-1538145 | sle_st_a_v2 | 5_2_route | 1.9 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-4153401 | sle_stm_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (4371/4371 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v3-1868496 | sle_stm_v3 | 5_1_grt | 1.6 | last meaningful line 0.0 h ago (160/160 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l0__cl7a55c676-4027948 | sle_su_l0 | 5_2_route | 5.9 | drt_violations best 73 last 73 rows 9 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3602061 | sle_su_l1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3900/3900 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-4191516 | slw_fw_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (76/76 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-4026650 | slw_hc3 | 3_3_place_gp | 0.2 | overflow best 0.9553 last 0.9553 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3626034 | slw_hc3 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4691/4691 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v3-3708441 | slw_sc_v3 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4112/4112 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-1494646 | slw_st_a_v2 | 5_1_grt | 1.9 | last meaningful line 0.1 h ago (2169/2186 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3657462 | slw_stm_v2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (6252/6252 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l0__cl1a1c1f8f-4150554 | slw_su_l0 | 6_report | 5.9 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-fin-1317564 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (1053/1053 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
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
| epyc8 | dpkit-coll_s-3875643 | coll_s | 5_2_route | 2.7 | last meaningful line 0.1 h ago (256/257 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v4n-177384 | kv3_pv_v4n | 5_1_grt | 2.5 | last meaningful line 0.7 h ago (264/1273 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 4_1_cts | 2.6 | last meaningful line 0.2 h ago (6179/6179 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v3-3927550 | sle_fe_v3 | 5_2_route | 2.6 | drt_violations best 2870 last 2870 rows 2 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 4_1_cts | 2.6 | last meaningful line 0.2 h ago (5593/5593 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 4_1_cts | 2.6 | last meaningful line 0.2 h ago (5753/5753 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl22c1ff36__pve230954c-3918742 | sle_hc1 | 4_1_cts | 2.6 | last meaningful line 0.2 h ago (5765/5765 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 4_1_cts | 2.6 | last meaningful line 0.2 h ago (5837/5837 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | 4_1_cts | 2.7 | last meaningful line 0.1 h ago (5617/5617 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | 4_1_cts | 2.7 | last meaningful line 0.2 h ago (5288/5288 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 5_1_grt | 2.6 | repair_Remaining best 322449 last 322449 rows 83 | YOUNG: stage 0.7 h < 1 h |  |
| epyc8 | dpkit-sle_sc_v3-4127450 | sle_sc_v3 | 5_1_grt | 2.6 | repair_Viol best 35 last 35 rows 3 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-4020071 | sle_st_a_v1 | postcts_gate_FF | 2.6 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-4063882 | sle_st_a_v2 | 5_2_route | 2.6 | last meaningful line 0.1 h ago (271/272 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | pregrt_ff_hold | 2.6 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | pregrt_ff_hold | 2.6 | repair_TNS best 16843.8 last 16843.8 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | pregrt_ff_hold | 2.6 | repair_TNS best 14398.6 last 14398.6 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-sle_stm_v1__clbe630b9c-4072662 | sle_stm_v1 | pregrt_ff_hold | 2.6 | repair_TNS best 38569 last 38569 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | pregrt_ff_hold | 2.6 | repair_TNS best 36493.7 last 36493.7 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc8 | dpkit-sle_su_l0__cl7a55c676-4020210 | sle_su_l0 | postcts_gate_FF | 2.6 | last meaningful line 0.0 h ago (846/846 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 4_1_cts | 2.6 | last meaningful line 0.1 h ago (5609/5609 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 4_1_cts | 2.6 | last meaningful line 0.2 h ago (5706/5706 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 4_1_cts | 2.6 | last meaningful line 0.1 h ago (5788/5788 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 4_1_cts | 2.6 | last meaningful line 0.2 h ago (5351/5351 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | postcts_gate_TT | 5.9 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | 4_1_cts | 2.7 | last meaningful line 0.2 h ago (5397/5397 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3909116 | slw_hc3 | pregrt_ff_hold | 2.7 | repair_TNS best 11037.5 last 11037.5 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-3949912 | slw_hc3 | pregrt_ff_hold | 2.6 | repair_TNS best 89067.5 last 89067.5 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 5_1_grt | 2.5 | repair_Remaining best 161598 last 161598 rows 224 | YOUNG: stage 0.8 h < 1 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | tt_setup_repair_grt | 2.6 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 5_2_route | 2.6 | last meaningful line 0.0 h ago (262/262 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | pregrt_ff_hold | 2.6 | repair_TNS best 21743.5 last 21743.5 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-3848540 | slw_su_l0 | 5_2_route | 2.7 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_2_route | 2.6 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i3t-2289287 | eco_20261123_164145_1995767-i3t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-slw-fe-v1--clfe325744--cldb4efe33-grt-30572 | slw-fe-v1--clfe325744--cldb4efe33-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-slw-fe-v2--cle312294d-grt-32494 | slw-fe-v2--cle312294d-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-slw-fe-v2--clf110fab2-grt-32127 | slw-fe-v2--clf110fab2-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-kv3_hub_Wo-2104173 | kv3_hub_Wo | 3_3_place_gp | 1.3 | overflow best 0.6412 last 0.6412 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-kv3_sys_SD-3260212 | kv3_sys_SD | tt_setup_repair_grt | 0.6 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__clf58b4dfb-1918057 | sle_fw_v1 | 3_4_place_resized | 1.4 | last meaningful line 0.1 h ago (377/377 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-2104596 | sle_hc1 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v3-2229849 | slw_fw_v3 | 3_5_place_dp | 1.3 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_stm_v1__cle34a73c3-2386039 | slw_stm_v1 | 3_5_place_dp | 1.2 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-1814577-31530 | 1814577 | - | 4.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-29732-24624 | 29732 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-29851-10135 | 29851 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-30219-7096 | 30219 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261123_224216_149959-i3t-3891967 | eco_20261123_224216_149959-i3t | 5_2_route | 2.7 | last meaningful line 0.1 h ago (282/283 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i3t-2877611 | eco_20261123_224647_4153453-i3t | 5_1_grt | 0.9 | last meaningful line 0.3 h ago (235/1293 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i2-1242463 | eco_20261124_010152_2867084-i2 | 5_2_route | 4.5 | drt_violations best 40 last 40 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | so_3931561_ff_78192 | so_3931561_ff_78192 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | so_3931561_tt_78192 | so_3931561_tt_78192 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
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
| intel2 | dpkit-coll_ftm-2905950 | coll_ftm | 5_2_route | 2.2 | drt_violations best 10288 last 10288 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-2015229 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (214/215 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_C-524420 | kv3_hub_C | 2_1_floorplan | 1.2 | last meaningful line 0.8 h ago (1424/1424 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_hub_Wi-487140 | kv3_hub_Wi | 2_1_floorplan | 1.2 | last meaningful line 0.3 h ago (335/335 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl7f648944__r8422a4b86-2106104 | kv3_pc_v1 | 2_1_floorplan | 0.2 | repair_Viol best 8518 last 8518 rows 512 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-sle_ctl__cla4f6f12f-578782 | sle_ctl | 3_3_place_gp | 1.1 | overflow best 0.2826 last 0.2996 rows 16 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-sle_fw_v1__cl9d029624-1286736 | sle_fw_v1 | 3_3_place_gp | 0.7 | overflow best 0.0995 last 0.0995 rows 41 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-60615 | sle_st_b_v2 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (5671/5671 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-549200 | slw_fe_v2 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (5206/5206 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 4_1_cts | 1.3 | last meaningful line 0.2 h ago (4851/4851 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q00__cl622f65d2-3557026 | cbn_q00 | pregrt_ff_hold | 0.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-1784944 | sle_st_a_v1 | 5_1_grt | 1.7 | repair_TNS best 0 last 0 rows 16 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-1826228 | sle_st_a_v1 | 5_1_grt | 1.7 | repair_TNS best 0 last 0 rows 14 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-248626 | sle_st_b_v2 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1494307 | slw_st_a_v1 | 5_1_grt | 1.9 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 32.8 | drt_violations best 14975 last 14975 rows 14 | before-window best 22423, window best 14975 | PROGRESS: drt_violations improved 33.2 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 26.1 | drt_violations best 15355 last 15355 rows 14 | before-window best 32431, window best 15355 | PROGRESS: drt_violations improved 52.7 % in window |  |
| epyc7 | dpkit-sle_stm_v3-3494601 | sle_stm_v3 | 5_2_route | 7.4 | drt_violations best 0 last 0 rows 7 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | prd-eco_20261124_145005_2036075-i1-1498701 | eco_20261124_145005_2036075-i1 | 5_2_route | 3.6 | drt_violations best 0 last 0 rows 2 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-coll_ftc-3942021 | coll_ftc | 5_1_grt | 2.6 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 5_1_grt | 2.6 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l0_wfb17da-849937 | qfd_qc_su_lane_w_l0_wfb17da | 5_1_grt | 4.8 | repair_TNS best 0 last 0 rows 80 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l1_w460927-787688 | qfd_qc_su_lane_w_l1_w460927 | 5_1_grt | 4.8 | repair_TNS best 0 last 0 rows 81 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l4_w285325-818329 | qfd_qc_su_lane_w_l4_w285325 | 5_1_grt | 4.8 | repair_TNS best 0 last 0 rows 111 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l5_wf949e1-824935 | qfd_qc_su_lane_w_l5_wf949e1 | 5_1_grt | 4.8 | repair_TNS best 0 last 0 rows 111 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l6_wb51d05-853896 | qfd_qc_su_lane_w_l6_wb51d05 | 5_1_grt | 4.8 | repair_TNS best 0 last 0 rows 91 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l7_wd4f14d-862251 | qfd_qc_su_lane_w_l7_wd4f14d | 5_1_grt | 4.7 | repair_TNS best 0 last 0 rows 81 | PROGRESS: repair_TNS reached 0 |  |
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
| intel2 | dpkit-kv3_io_ft-2016810 | kv3_io_ft | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel2 | dpkit-slice_station__t12-2045071 | slice_station__t12 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 9.9 | drt_violations best 2 last 2 rows 52 | before-window best 20278, window best 2 | PROGRESS: drt_violations improved 100.0 % in window |  |
