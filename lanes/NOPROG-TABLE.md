# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 09:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 14, 'GRT-LABEL': 3, 'YOUNG': 163, 'NO-DATA': 10, 'EXCLUDED': 1, 'PROGRESS': 35}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair_grt | 14.9 | repair_Violations best 0 last 0 rows 93 | before-window best 0, window best - | NO-PROGRESS: no new repair_Violations row in 6 h | REPORT-ONLY: lane-own kit (OPUS-FIX-QC-V4-R2 decid |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3987964 | sle_hc2 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-4024927 | sle_st_b_v1 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3951031 | sle_st_b_v2 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-slw_hc2__cl6bcaba89-4049393 | slw_hc2 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-4062944 | slw_hc3 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | CANCELLED |
| epyc2 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-4102152 | slw_st_b_v1 | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4111701 | slw_st_b_v1 | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4115743 | slw_st_b_v2 | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | CANCELLED |
| epyc2 | dpkit-slw_st_b_v2__pvc2ec5bfb-4120782 | slw_st_b_v2 | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | CANCELLED |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | tt_setup_repair_grt | 14.8 | repair_Violations best 0 last 0 rows 62 | before-window best 0, window best - | NO-PROGRESS: no new repair_Violations row in 6 h | REPORT-ONLY: lane-own kit (OPUS-FIX-QC-V4-R2 decid |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3249798 | slw_hc3 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 17.2 | last meaningful line 6.4 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 6.4 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 20.9 | last meaningful line 6.4 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 6.4 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc2 | dpkit-kv3_hgi_v2__cl2862d491-2611569 | kv3_hgi_v2 | 5_1_grt | 2.1 | grt rounds 2 overflow 5:8290 -> 10:2912 | GRT-LABEL: DESIGN-FAIL: overflow 2912 at round 10 > 1000 |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 5_1_grt | 14.7 | grt rounds 2 overflow 5:13977 -> 10:10981 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | 5_1_grt | 8.0 | grt rounds 2 overflow 5:25842 -> 10:3973 | GRT-LABEL: DESIGN-FAIL: overflow 3973 at round 10 > 1000 |  |
| epyc10 | dpkit-cbn_q00__cl622f65d2-404046 | cbn_q00 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (5702/5702 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-cbn_q01__clab6e67f2-167412 | cbn_q01 | pregrt_ff_hold | 1.1 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc10 | dpkit-cbn_q01__clab6e67f2-265684 | cbn_q01 | 3_4_place_resized | 1.0 | last meaningful line 0.0 h ago (286/286 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-coll_ft__cla4a25d77-90691 | coll_ft | 5_2_route | 1.1 | drt_violations best 12124 last 12124 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | dpkit-coll_n-91668 | coll_n | 5_2_route | 1.1 | drt_violations best 3700 last 3700 rows 2 | YOUNG: stage 0.7 h < 1 h |  |
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (7075/7075 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v3-1126078 | kv3_hg_v3 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (109/109 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v4-677838 | kv3_hgi_v4 | tt_setup_repair | 0.7 | repair_Viol best 257 last 257 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-kv3_hgi_v5-772924 | kv3_hgi_v5 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (5760/5760 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv-1051314 | kv3_pv | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (10930/10930 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (10004/10004 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v1e-1282383 | kv3_pv_v1e | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (6879/6879 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v2-1075302 | kv3_pv_v2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (7132/7132 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v2e-252410 | kv3_pv_v2e | pregrt_ff_hold | 1.0 | last meaningful line -0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc10 | dpkit-kv3_pv_v2n-1048434 | kv3_pv_v2n | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5484/5484 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v4-680976 | kv3_pv_v4 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (6661/6661 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v4e-1194094 | kv3_pv_v4e | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (7062/7062 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v5e-402621 | kv3_pv_v5e | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (8096/8096 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v5n-698511 | kv3_pv_v5n | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (7860/7860 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v6-908877 | kv3_pv_v6 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (8341/8341 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v6e-760052 | kv3_pv_v6e | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (8354/8354 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v6n-1030440 | kv3_pv_v6n | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (6606/6606 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v6ne-1050153 | kv3_pv_v6ne | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (7207/7207 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v7-1199684 | kv3_pv_v7 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (6381/6381 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v7e-1156836 | kv3_pv_v7e | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (10535/10535 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-225022 | sle_ctl | 3_3_place_gp | 1.0 | overflow best 0.0997 last 0.0997 rows 55 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-577528 | sle_fw_v2 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-935112 | sle_stm_v1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.3475 last 0.3475 rows 39 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-slw_st_a_v1__clb036e152-315416 | slw_st_a_v1 | 5_1_grt | 0.9 | last meaningful line 0.2 h ago (1295/2050 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | pregrt_ff_hold | 2.1 | repair_TNS best 758714 last 758714 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-kv3_phy-1115318 | kv3_phy | 5_2_route | 0.5 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v5ne-2612763 | kv3_pv_v5ne | 4_1_cts | 2.1 | last meaningful line 0.1 h ago (8786/8786 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pve-2456771 | kv3_pve | 5_1_grt | 2.2 | last meaningful line 0.2 h ago (265/1271 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_sys_c-2605096 | kv3_sys_c | 5_1_grt | 2.1 | last meaningful line 0.2 h ago (1259/2267 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 4.3 | drt_violations best 22046 last 22046 rows 3 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | postcts_gate_TT | 4.2 | last meaningful line 0.0 h ago (1911/1911 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-1186805 | sle_sc_v3 | postcts_gate_TT | 3.3 | last meaningful line -0.0 h ago (4078/4078 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-1538145 | sle_st_a_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5804/5804 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-248626 | sle_st_b_v2 | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (5615/5615 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-265811 | sle_st_b_v2 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l0__cl7a55c676-4027948 | sle_su_l0 | 5_2_route | 4.2 | drt_violations best 189860 last 189860 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-67943 | slw_fe_v2 | 3_4_place_resized | 1.0 | last meaningful line 0.1 h ago (372/372 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-90784 | slw_fw_v2 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (83/83 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1494307 | slw_st_a_v1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (8074/8074 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-1494646 | slw_st_a_v2 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (6439/6439 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l0__cl1a1c1f8f-4150554 | slw_su_l0 | 5_2_route | 4.1 | drt_violations best 147934 last 147934 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | htr_eco_1448298 | htr_eco_1448298 | lec | 0.2 | LEC last write 0.1 h ago | YOUNG: evidence 0.2 h < 6 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i3t-1317564 | eco_20261123_103136_2028090-i3t | 5_2_route | 3.2 | drt_violations best 2067 last 2067 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-cbf-q01-s2-grt-1650805 | cbf-q01-s2-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-sle-fw-v2--cl6740750e-grt-1869409 | sle-fw-v2--cl6740750e-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-sle-sc-v2-grt-1805834 | sle-sc-v2-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-slw-hc0--cl4f54b7a3--pvde134a90-grt-1917397 | slw-hc0--cl4f54b7a3--pvde134a90-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbf_q00__cl1b5a6458-3769028 | cbf_q00 | 3_4_place_resized | 1.4 | last meaningful line 0.1 h ago (21/21 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-1986727 | cbn_q00 | selrange | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-4105682 | cbn_q01 | 3_4_place_resized | 1.2 | last meaningful line 0.2 h ago (20/20 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-1850782 | hd_lep0N_w | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-995501 | hd_lep0N_w | 5_2_route | 5.0 | drt_violations best 9854 last 9854 rows 3 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl1cbb7497-3539262 | sle_fe_v1 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-3547062 | sle_fw_v1 | 3_5_place_dp | 1.4 | last meaningful line 0.1 h ago (114/114 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__clf58b4dfb-3165565 | sle_fw_v1 | 3_4_place_resized | 1.6 | last meaningful line 0.0 h ago (422/422 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 9.6 | last meaningful line 0.5 h ago (275/276 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | postcts_gate_FF | 5.8 | last meaningful line 0.0 h ago (2150/2150 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | 5_2_route | 9.7 | drt_violations best 145769 last 145769 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | postcts_gate_TT | 5.6 | last meaningful line -0.0 h ago (81923/81923 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-3494601 | sle_stm_v3 | 5_2_route | 6.2 | drt_violations best 89680 last 89680 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | postcts_gate_FF | 10.0 | last meaningful line 0.1 h ago (844/844 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_1_grt | 4.2 | repair_Remaining best 334862 last 334862 rows 105 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 9.8 | drt_violations best 407677 last 407677 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 5.9 | last meaningful line 0.0 h ago (266/266 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | 5_2_route | 10.0 | drt_violations best 121446 last 121446 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | postcts_gate_TT | 6.0 | last meaningful line -0.0 h ago (13121/13121 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | eco-abs-3857460 | eco-abs | generate_abstract | 1.3 | last meaningful line 0.1 h ago (1032/1032 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | otc-3312012-17262 | 3312012 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261124_145005_2036075-i1-1498701 | eco_20261124_145005_2036075-i1 | 5_2_route | 2.4 | drt_violations best 46 last 46 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | postcts_gate_TT | 14.7 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-coll_ftc-3942021 | coll_ftc | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (6243/6243 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v4n-177384 | kv3_pv_v4n | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (6298/6298 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (6065/6065 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v3-3927550 | sle_fe_v3 | postcts_gate_FF | 1.1 | last meaningful line 0.0 h ago (405/405 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 4_1_cts | 1.1 | last meaningful line 0.2 h ago (5492/5492 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (5640/5640 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl22c1ff36__pve230954c-3918742 | sle_hc1 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (5659/5659 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (5737/5737 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | 4_1_cts | 1.2 | last meaningful line 0.2 h ago (5527/5527 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (5215/5215 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (5740/5740 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v3-4127450 | sle_sc_v3 | tt_setup_repair | 1.1 | repair_Viol best 48 last 48 rows 47 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-4020071 | sle_st_a_v1 | 5_1_grt | 1.1 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-4075646 | sle_st_a_v2 | 5_1_grt | 1.1 | last meaningful line 0.2 h ago (1303/1904 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-4063882 | sle_st_a_v2 | 5_1_grt | 1.1 | repair_Remaining best 172914 last 172914 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (5550/5550 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (5451/5451 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (5654/5654 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v1__clbe630b9c-4072662 | sle_stm_v1 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (5999/5999 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (6246/6246 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l0__cl7a55c676-4020210 | sle_su_l0 | 5_1_grt | 1.1 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 4_1_cts | 1.1 | last meaningful line 0.2 h ago (5497/5497 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (5623/5623 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 4_1_cts | 1.1 | last meaningful line 0.3 h ago (5632/5632 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (5251/5251 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | 5_1_grt | 4.4 | last meaningful line -0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (5316/5316 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3909116 | slw_hc3 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (5149/5149 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-3949912 | slw_hc3 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (4857/4857 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (5691/5691 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (4375/4375 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | 5_1_grt | 1.1 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 5_1_grt | 1.1 | last meaningful line 0.0 h ago (270/272 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (5455/5455 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-3848540 | slw_su_l0 | 5_1_grt | 1.2 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_1_grt | 1.1 | repair_TNS best 5.73 last 5.73 rows 3 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i2-2385296 | eco_20261123_164145_1995767-i2 | 5_2_route | 3.5 | drt_violations best 14428 last 14428 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | dpkit-hd_serdes-3604295 | hd_serdes | 3_3_place_gp | 1.2 | overflow best 0.2153 last 0.2153 rows 44 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | otc-1223324-6056 | 1223324 | asbuilt.yosys | 0.1 | last meaningful line 0.1 h ago (11/11 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-1275753-28000 | 1275753 | gen_lint_check | 0.0 | last meaningful line 0.0 h ago (167/167 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-1814577-31530 | 1814577 | - | 2.4 |  | NO-DATA: no log found |  |
| epyc9 | otc-1939028-17446 | 1939028 | gold_b.ys | 2.3 | last meaningful line 2.0 h ago (84693/84693 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | otc-2103773-27089 | 2103773 | gold_b.ys | 2.2 | last meaningful line 2.0 h ago (67868/67868 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | prd-count-p1_tc-368978 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i3t-3891967 | eco_20261123_224216_149959-i3t | 5_1_grt | 1.0 | last meaningful line 0.3 h ago (235/1284 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i2-1242463 | eco_20261124_010152_2867084-i2 | 5_2_route | 2.7 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | so_848114_ff_44379 | so_848114_ff_44379 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (1034/1034 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | so_848114_tt_44379 | so_848114_tt_44379 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (1034/1034 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-coll_core-709203 | coll_core | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (83/83 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-coll_ft__cl78c7b300-2325645 | coll_ft | 5_1_grt | 0.5 | repair_TNS best 7.482 last 7.482 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-hd_lep0N-2597425 | hd_lep0N | 3_1_place_gp_skip_io | 0.3 | overflow best 0.732 last 0.7795 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_hgi_v8-2295582 | kv3_hgi_v8 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.6657 last 0.7003 rows 21 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_hroot-2106033 | kv3_hroot | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 4_1_cts | 1.9 | last meaningful line 0.3 h ago (12575/12575 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3ne-3760907 | kv3_pv_v3ne | 4_1_cts | 2.3 | last meaningful line 0.0 h ago (9909/9909 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v5-1046392 | kv3_pv_v5 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (7323/7323 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v8-3837707 | kv3_pv_v8 | pregrt_ff_hold | 2.2 | repair_TNS best 150051 last 150051 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v8e-3858104 | kv3_pv_v8e | 5_1_grt | 2.2 | grt_overflow best 227 last 227 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-native59-1320092 | native59 | pregrt_ff_hold | 4.5 | repair_TNS best 5962.38 last 5962.38 rows 1 | YOUNG: evidence 2.2 h < 2.5 h |  |
| intel1 | dpkit-native59-635922 | native59 | 3_3_place_gp | 1.4 | overflow best 0.315 last 0.3385 rows 125 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-sle_ctl__cla4f6f12f-668891 | sle_ctl | 3_3_place_gp | 1.4 | overflow best 0.5669 last 0.5669 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | pregrt_ff_hold | 4.5 | repair_TNS best 40812.4 last 40812.4 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_hc1__cl22c1ff36__pve289215f-698914 | sle_hc1 | 3_3_place_gp | 1.4 | overflow best 0.2985 last 0.4862 rows 281 | YOUNG: stage 1.0 h < 1 h |  |
| intel1 | dpkit-sle_hc1__cl7d360508__pv97423966-1341249 | sle_hc1 | pregrt_ff_hold | 4.5 | repair_TNS best 23871.1 last 23871.1 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-708325 | sle_sc_v1 | 3_4_place_resized | 1.4 | last meaningful line 0.0 h ago (394/394 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pv0e7b1dcc-656937 | sle_st_b_v1 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (79/79 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | postcts_gate_FF | 2.5 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | pregrt_ff_hold | 4.4 | repair_TNS best 4556.18 last 4556.18 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-slw_fw_v3-667805 | slw_fw_v3 | 3_5_place_dp | 1.4 | last meaningful line 0.1 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1387403 | slw_hc0 | pregrt_ff_hold | 4.4 | repair_TNS best 8823.1 last 8823.1 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_hc1__cl3449ea95-1389354 | slw_hc1 | pregrt_ff_hold | 4.4 | repair_TNS best 20575.5 last 20575.5 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2973163 | slw_hc3 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (57/57 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-658036 | slw_st_b_v2 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (86/86 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-1670752-16443 | 1670752 | - | 8.5 |  | NO-DATA: no log found |  |
| intel1 | otc-1797391-24144 | 1797391 | flow3 | 4.1 | last meaningful line 3.7 h ago (208/209 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel1 | otc-3818878-18115 | 3818878 | - | 2.3 |  | NO-DATA: no log found |  |
| intel1 | otc-3854277-21865 | 3854277 | - | 2.2 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261123_191853_2879776-i2t-2852283 | eco_20261123_191853_2879776-i2t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-cbf_q00_s2-3236123 | cbf_q00_s2 | 3_3_place_gp | 0.5 | overflow best 0.517 last 0.517 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-cbn_q11__cl5cc92dfe-3230852 | cbn_q11 | 3_3_place_gp | 0.5 | overflow best 0.2111 last 0.2111 rows 34 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-glue-3754562 | glue | 1_2_yosys | 0.1 | last meaningful line -0.0 h ago (2725/2725 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-2905832 | kv3_io_ft | 5_2_route | 0.7 | last meaningful line 0.0 h ago (216/217 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-3971598 | kv3_pc | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (302/302 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc__cl5a95b461__r85c02c25c-3970568 | kv3_pc | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (302/302 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc__cl5a95b461__r882954158-3964582 | kv3_pc | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (313/313 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3766219 | sle_hc2 | port_bind | 0.1 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v1__cl27746664-3977275 | sle_stm_v1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (70/70 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-2929686 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (225/226 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8f84514c-3936002 | slw_fw_v2 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl63e5a7a2-3977615 | slw_sc_v1 | 1_synth | 0.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3973955 | slw_sc_v1 | 1_synth | 0.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_stm_v2__cl9beb65e6-4016387 | slw_stm_v2 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-365424-10454 | 365424 | - | 0.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-kv3_hgi_v2__cle0015330-630449 | kv3_hgi_v2 | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-2159263 | slw_hc1 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-2082988 | slw_hc3 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_hgi_v7-2608982 | kv3_hgi_v7 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_hgi_v8-2448463 | kv3_hgi_v8 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc0__cl05696ed1-3966951 | sle_hc0 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-3970782 | sle_hc0 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-3979294 | sle_hc0 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 31.6 | drt_violations best 14975 last 14975 rows 14 | before-window best 26552, window best 14975 | PROGRESS: drt_violations improved 43.6 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 24.9 | drt_violations best 20899 last 20899 rows 13 | before-window best 39072, window best 20899 | PROGRESS: drt_violations improved 46.5 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_1_grt | 4.4 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_st_b_v1__pv0e7b1dcc-2157611 | sle_st_b_v1 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-2333813 | slw_sc_v1 | 5_1_grt | 4.2 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbf_q01-243499 | cbf_q01 | pregrt_ff_hold | 1.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbf_q11-255079 | cbf_q11 | pregrt_ff_hold | 1.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbx_q10__cl89936551-4175651 | cbx_q10 | pregrt_ff_hold | 1.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-coll_s-3875643 | coll_s | 5_1_grt | 1.2 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | prd-eco_20261123_120225_75582-i3t-3968210 | eco_20261123_120225_75582-i3t | 5_2_route | 8.4 | drt_violations best 11 last 78 rows 44 | before-window best 36109, window best 11 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-slw_sc_v1__cl63e5a7a2-3279007 | slw_sc_v1 | tt_setup_repair_grt | 4.1 | repair_Violations best 0 last 0 rows 4 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l0_wfb17da-849937 | qfd_qc_su_lane_w_l0_wfb17da | 5_1_grt | 3.0 | repair_TNS best 0 last 0 rows 208 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l1_w460927-787688 | qfd_qc_su_lane_w_l1_w460927 | 5_1_grt | 3.0 | repair_TNS best 0 last 0 rows 205 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l4_w285325-818329 | qfd_qc_su_lane_w_l4_w285325 | 5_1_grt | 3.0 | repair_TNS best 0 last 0 rows 227 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l5_wf949e1-824935 | qfd_qc_su_lane_w_l5_wf949e1 | 5_1_grt | 3.0 | repair_TNS best 0 last 0 rows 216 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l6_wb51d05-853896 | qfd_qc_su_lane_w_l6_wb51d05 | 5_1_grt | 3.0 | repair_TNS best 0 last 0 rows 210 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l7_wd4f14d-862251 | qfd_qc_su_lane_w_l7_wd4f14d | 5_1_grt | 3.0 | repair_TNS best 0 last 0 rows 201 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-1345836 | sle_hc2 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1365381 | sle_st_b_v1 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-1401912 | slw_hc2 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1439197 | slw_st_b_v1 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-1446982 | slw_st_b_v2 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 39.1 | drt_violations best 74496 last 74496 rows 15 | before-window best 76746, window best 74496 | PROGRESS: drt_violations improved 2.9 % in window |  |
| intel2 | dpkit-coll_ftm-2905950 | coll_ftm | 5_1_grt | 0.7 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 8.4 | drt_violations best 6 last 14 rows 46 | before-window best 20278, window best 6 | PROGRESS: drt_violations improved 100.0 % in window |  |
