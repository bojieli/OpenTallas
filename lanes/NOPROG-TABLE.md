# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 09:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 14, 'GRT-LABEL': 2, 'YOUNG': 188, 'NO-DATA': 6, 'PROGRESS': 34}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair_grt | 15.1 | repair_Violations best 0 last 0 rows 93 | before-window best 0, window best - | NO-PROGRESS: no new repair_Violations row in 6 h | REPORT-ONLY: lane-own kit (OPUS-FIX-QC-V4-R2 decid |
| epyc2 | dpkit-sle_hc0__cl05696ed1-3966951 | sle_hc0 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-3970782 | sle_hc0 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-3979294 | sle_hc0 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3987964 | sle_hc2 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-4024927 | sle_st_b_v1 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3951031 | sle_st_b_v2 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | CANCELLED |
| epyc2 | dpkit-slw_hc2__cl6bcaba89-4049393 | slw_hc2 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-4102152 | slw_st_b_v1 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | CANCELLED |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4111701 | slw_st_b_v1 | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | CANCELLED |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | tt_setup_repair_grt | 15.1 | repair_Violations best 0 last 0 rows 62 | before-window best 0, window best - | NO-PROGRESS: no new repair_Violations row in 6 h | REPORT-ONLY: lane-own kit (OPUS-FIX-QC-V4-R2 decid |
| intel1 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-1446982 | slw_st_b_v2 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 17.4 | last meaningful line 6.6 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 6.6 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 21.2 | last meaningful line 6.6 h ago (107/107 lines) | NO-PROGRESS: no new non-iteration log line for 6.6 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc2 | dpkit-kv3_hgi_v2__cl2862d491-2611569 | kv3_hgi_v2 | 5_1_grt | 2.3 | grt rounds 2 overflow 5:8290 -> 10:2912 | GRT-LABEL: DESIGN-FAIL: overflow 2912 at round 10 > 1000 |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | 5_1_grt | 8.3 | grt rounds 2 overflow 5:25842 -> 10:3973 | GRT-LABEL: DESIGN-FAIL: overflow 3973 at round 10 > 1000 |  |
| epyc10 | ap-ageom-kw-sle-fw-v2--cl6740750e-grt-1720145 | sle-fw-v2--cl6740750e-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (126/126 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-cbn_q00__cl622f65d2-404046 | cbn_q00 | pregrt_ff_hold | 1.1 | repair_TNS best 64860.7 last 64860.7 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-coll_ft__cla4a25d77-90691 | coll_ft | 6_report | 1.4 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-coll_n-91668 | coll_n | generate_abstract | 1.4 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-1066361 | hd_lep0N | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (8216/8216 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (7134/7134 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v3-1126078 | kv3_hg_v3 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5929/5929 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v2__cle0015330-630449 | kv3_hgi_v2 | 5_1_grt | 1.0 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv-1051314 | kv3_pv | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (11014/11014 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v1-929811 | kv3_pv_v1 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (10093/10093 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v1e-1282383 | kv3_pv_v1e | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (7329/7329 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v2-1075302 | kv3_pv_v2 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (7230/7230 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v2e-252410 | kv3_pv_v2e | 5_1_grt | 1.2 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v2n-1048434 | kv3_pv_v2n | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (5560/5560 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v4-680976 | kv3_pv_v4 | tt_setup_repair | 0.9 | repair_Viol best 1546 last 1546 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_pv_v4e-1194094 | kv3_pv_v4e | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (7379/7379 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v5e-402621 | kv3_pv_v5e | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (8127/8127 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v5n-698511 | kv3_pv_v5n | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (7892/7892 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v6-908877 | kv3_pv_v6 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (8430/8430 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v6e-760052 | kv3_pv_v6e | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (8446/8446 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v6n-1030440 | kv3_pv_v6n | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (6714/6714 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v6ne-1050153 | kv3_pv_v6ne | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (7319/7319 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v7-1199684 | kv3_pv_v7 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (6685/6685 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v7e-1156836 | kv3_pv_v7e | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (10857/10858 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-225022 | sle_ctl | 3_4_place_resized | 1.3 | last meaningful line 0.1 h ago (433/433 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v1__cl27746664-935112 | sle_stm_v1 | 3_3_place_gp | 0.7 | overflow best 0.4048 last 0.4048 rows 22 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-slw_st_a_v1__clb036e152-315416 | slw_st_a_v1 | 5_1_grt | 1.2 | last meaningful line 0.1 h ago (2080/2097 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-slw-fw-v2--cl8537f156-grt-2036575 | slw-fw-v2--cl8537f156-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-coll_ftm-1783743 | coll_ftm | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3201/3202 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | pregrt_ff_hold | 2.3 | repair_TNS best 758714 last 758714 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-kv3_hgi_v7-2608982 | kv3_hgi_v7 | pregrt_ff_hold | 2.3 | repair_TNS best 2446.48 last 2446.48 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc2 | dpkit-kv3_phy-1115318 | kv3_phy | 5_2_route | 0.7 | last meaningful line 0.0 h ago (226/227 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v5ne-2612763 | kv3_pv_v5ne | 4_1_cts | 2.3 | last meaningful line 0.0 h ago (8809/8809 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pve-2456771 | kv3_pve | 5_1_grt | 2.5 | last meaningful line 0.5 h ago (265/1273 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-kv3_sys_c-2082087 | kv3_sys_c | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_sys_c-2605096 | kv3_sys_c | 5_1_grt | 2.3 | repair_Remaining best 727 last 727 rows 264 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 4.6 | drt_violations best 5882 last 5882 rows 4 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-1772768 | sle_hc0 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | postcts_gate_TT | 4.5 | last meaningful line 0.1 h ago (2160/2160 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-1186805 | sle_sc_v3 | postcts_gate_FF | 3.5 | last meaningful line 0.0 h ago (2059/2059 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl67389ecd-1784944 | sle_st_a_v1 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (8202/8202 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-1826228 | sle_st_a_v1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (8471/8471 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-1538145 | sle_st_a_v2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5948/5948 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-248626 | sle_st_b_v2 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (5673/5673 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v3-1868496 | sle_stm_v3 | 4_1_cts | 0.1 | last meaningful line 0.1 h ago (4240/4240 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l0__cl7a55c676-4027948 | sle_su_l0 | 5_2_route | 4.4 | drt_violations best 189860 last 189860 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-67943 | slw_fe_v2 | 3_5_place_dp | 1.3 | last meaningful line 0.1 h ago (114/114 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1494307 | slw_st_a_v1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (8197/8197 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-1494646 | slw_st_a_v2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (6520/6520 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l0__cl1a1c1f8f-4150554 | slw_su_l0 | 5_2_route | 4.4 | drt_violations best 147934 last 147934 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | hpf_proof_2016468 | hpf_proof_2016468 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | htr_eco_1448298 | htr_eco_1448298 | lec | 0.5 | LEC last write 0.3 h ago | YOUNG: evidence 0.5 h < 6 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i3t-1317564 | eco_20261123_103136_2028090-i3t | 5_2_route | 3.4 | drt_violations best 2067 last 2067 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00__cl1b5a6458-3769028 | cbf_q00 | 3_5_place_dp | 1.6 | last meaningful line 0.0 h ago (87/87 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q01_s2-2130215 | cbf_q01_s2 | 4_1_cts | 0.2 | last meaningful line -0.0 h ago (6444/6444 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-1986727 | cbn_q00 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (6278/6278 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-4105682 | cbn_q01 | 3_4_place_resized | 1.4 | last meaningful line 0.0 h ago (300/300 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-cbx_q10__cl89936551_h-2018516 | cbx_q10 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5054/5054 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-1850782 | hd_lep0N_w | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3186/3186 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-995501 | hd_lep0N_w | 6_report | 5.2 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__clf58b4dfb-3165565 | sle_fw_v1 | 3_5_place_dp | 1.8 | last meaningful line 0.2 h ago (114/114 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-2222980 | sle_fw_v2 | 4_1_cts | 0.1 | last meaningful line -0.0 h ago (6304/6304 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 9.9 | last meaningful line 0.3 h ago (277/278 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | postcts_gate_FF | 6.0 | last meaningful line 0.2 h ago (2156/2156 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_1_grt | 4.7 | last meaningful line 0.1 h ago (2016/2022 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v2-2310968 | sle_sc_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3910/3910 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1893640 | sle_st_b_v2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5280/5280 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | 5_2_route | 10.0 | drt_violations best 145769 last 145769 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | postcts_gate_FF | 5.9 | last meaningful line 0.0 h ago (1520/1520 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-3494601 | sle_stm_v3 | 5_2_route | 6.4 | drt_violations best 89680 last 89680 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl1bc59e1c-2061343 | slw_hc0 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5132/5132 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-2131271 | slw_hc0 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5182/5182 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | postcts_gate_FF | 10.3 | last meaningful line -0.0 h ago (56066/56066 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1982265 | slw_hc1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5216/5216 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cldc737267-2253577 | slw_hc2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_1_grt | 4.5 | last meaningful line 0.5 h ago (1301/1952 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-2333813 | slw_sc_v1 | 5_1_grt | 4.5 | last meaningful line 0.3 h ago (1302/1984 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 10.1 | drt_violations best 407677 last 407677 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_2_route | 6.2 | last meaningful line 0.3 h ago (267/268 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2020300 | slw_st_b_v2 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (4429/4429 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | 5_2_route | 10.3 | drt_violations best 121446 last 121446 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | postcts_gate_FF | 6.2 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v3-2196883 | slw_stm_v3 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (4430/4430 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | otc-2405659-20932 | 2405659 | postcts_gate_FF | 0.0 | last meaningful line 0.0 h ago (1520/1520 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-3312012-17262 | 3312012 | - | 1.8 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261124_145005_2036075-i1-1498701 | eco_20261124_145005_2036075-i1 | 5_2_route | 2.6 | drt_violations best 46 last 46 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | so_2039923_ff_97609 | so_2039923_ff_97609 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | so_2039923_tt_97609 | so_2039923_tt_97609 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | postcts_gate_TT | 15.0 | last meaningful line 0.2 h ago (687/687 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-coll_ftc-3942021 | coll_ftc | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (6247/6247 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v4n-177384 | kv3_pv_v4n | tt_setup_repair | 1.3 | last meaningful line 0.0 h ago (380/380 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (6092/6092 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v3-3927550 | sle_fe_v3 | 5_2_route | 1.4 | last meaningful line 0.0 h ago (239/240 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 4_1_cts | 1.4 | last meaningful line 0.2 h ago (5519/5519 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (5667/5667 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl22c1ff36__pve230954c-3918742 | sle_hc1 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (5686/5686 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (5764/5764 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | 4_1_cts | 1.4 | last meaningful line 0.2 h ago (5533/5533 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | 4_1_cts | 1.4 | last meaningful line 0.2 h ago (5217/5217 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (5882/5882 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-4020071 | sle_st_a_v1 | 5_1_grt | 1.4 | repair_Remaining best 114142 last 114142 rows 37 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (5570/5570 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (5479/5479 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (5683/5683 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v1__clbe630b9c-4072662 | sle_stm_v1 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (6026/6026 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (6275/6275 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l0__cl7a55c676-4020210 | sle_su_l0 | 5_1_grt | 1.4 | last meaningful line 0.2 h ago (258/1267 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (5524/5524 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 4_1_cts | 1.4 | last meaningful line 0.3 h ago (5623/5623 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 4_1_cts | 1.4 | last meaningful line 0.2 h ago (5680/5680 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (5278/5278 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | 5_1_grt | 4.7 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (5343/5343 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3909116 | slw_hc3 | 4_1_cts | 1.4 | last meaningful line 0.2 h ago (5176/5176 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-3949912 | slw_hc3 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (4891/4891 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (5829/5829 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | tt_setup_repair | 1.3 | repair_Remaining best 119738 last 119738 rows 257 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | 5_1_grt | 1.4 | repair_Remaining best 53216 last 53216 rows 102 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 5_1_grt | 1.4 | last meaningful line 0.1 h ago (1302/2067 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (5483/5483 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-3848540 | slw_su_l0 | 5_1_grt | 1.4 | last meaningful line 0.1 h ago (1290/1603 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i2-2385296 | eco_20261123_164145_1995767-i2 | 5_2_route | 3.7 | drt_violations best 5 last 5 rows 36 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc9 | dpkit-coll_ucie-2281251 | coll_ucie | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hub_Wo-2104173 | kv3_hub_Wo | lec | 0.1 | LEC last write -0.0 h ago | YOUNG: evidence 0.1 h < 6 h |  |
| epyc9 | dpkit-kv3_sys_SD_v1-2269512 | kv3_sys_SD_v1 | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__clf58b4dfb-1918057 | sle_fw_v1 | 2_1_floorplan | 0.2 | last meaningful line 0.1 h ago (85/85 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv97423966-2104596 | sle_hc1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (389/389 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_stm_v2__cl55be2264-2182782 | sle_stm_v2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (619/619 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-2013804 | sle_su_l1 | 3_3_place_gp | 0.1 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v3-2229849 | slw_fw_v3 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-1223324-6056 | 1223324 | asbuilt.yosys | 0.6 | last meaningful line 0.1 h ago (242290/242290 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | otc-1814577-31530 | 1814577 | - | 2.9 |  | NO-DATA: no log found |  |
| epyc9 | otc-1939028-17446 | 1939028 | gold_b.ys | 2.8 | last meaningful line 2.5 h ago (84693/84693 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i3t-3891967 | eco_20261123_224216_149959-i3t | 5_2_route | 1.5 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i2-1242463 | eco_20261124_010152_2867084-i2 | 5_2_route | 3.2 | last meaningful line 0.2 h ago (281/282 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | prd-fin-368978 | fin | 6_report | 0.3 | last meaningful line 0.1 h ago (1069/1069 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | so_848114_ff_44379 | so_848114_ff_44379 | generate_abstract | 0.8 | last meaningful line 0.8 h ago (1034/1034 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | so_848114_tt_44379 | so_848114_tt_44379 | generate_abstract | 0.8 | last meaningful line 0.8 h ago (1034/1034 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-coll_ft__cl78c7b300-2325645 | coll_ft | postcts_gate_TT | 0.8 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-hd_lep0N-2597425 | hd_lep0N | 3_3_place_gp | 0.6 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v8-2295582 | kv3_hgi_v8 | 3_3_place_gp | 0.8 | overflow best 0.1949 last 0.1949 rows 12 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 4_1_cts | 2.1 | last meaningful line 0.2 h ago (12602/12602 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3ne-3760907 | kv3_pv_v3ne | 4_1_cts | 2.6 | last meaningful line 0.3 h ago (9910/9910 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v5-1046392 | kv3_pv_v5 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (7328/7328 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v8-3837707 | kv3_pv_v8 | pregrt_ff_hold | 2.5 | repair_TNS best 150051 last 150051 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v8e-3858104 | kv3_pv_v8e | 5_1_grt | 2.5 | last meaningful line 0.2 h ago (265/1269 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-native59-635922 | native59 | 3_3_place_gp | 1.7 | overflow best 0.2985 last 0.558 rows 234 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-sle_ctl__cla4f6f12f-668891 | sle_ctl | 3_3_place_gp | 1.6 | overflow best 0.2101 last 0.2101 rows 31 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | pregrt_ff_hold | 4.7 | repair_TNS best 40812.4 last 40812.4 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-2854694 | sle_hc0 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5506/5507 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-sle_hc1__cl22c1ff36__pve289215f-698914 | sle_hc1 | 3_3_place_gp | 1.6 | overflow best 0.0999 last 0.0999 rows 319 | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-sle_hc1__cl7d360508__pv97423966-1341249 | sle_hc1 | pregrt_ff_hold | 4.7 | repair_TNS best 23871.1 last 23871.1 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | postcts_gate_FF | 2.8 | last meaningful line 0.2 h ago (792/792 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1387403 | slw_hc0 | pregrt_ff_hold | 4.7 | repair_TNS best 8823.1 last 8823.1 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-slw_hc1__cl3449ea95-1389354 | slw_hc1 | pregrt_ff_hold | 4.7 | repair_TNS best 20575.5 last 20575.5 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2973163 | slw_hc3 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (4702/4703 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-2856011 | slw_st_b_v1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5139/5140 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2852353 | slw_stm_v2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4699/4699 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-1670752-16443 | 1670752 | - | 8.8 |  | NO-DATA: no log found |  |
| intel1 | otc-1797391-24144 | 1797391 | flow3 | 4.3 | last meaningful line 4.0 h ago (208/209 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel1 | otc-3818878-18115 | 3818878 | - | 2.5 |  | NO-DATA: no log found |  |
| intel1 | otc-3854277-21865 | 3854277 | - | 2.5 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261123_191853_2879776-i2t-2852283 | eco_20261123_191853_2879776-i2t | 5_1_grt | 0.4 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-cbf_q00_s2-3236123 | cbf_q00_s2 | 3_3_place_gp | 0.7 | overflow best 0.216 last 0.216 rows 34 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-cbn_q11__cl5cc92dfe-3230852 | cbn_q11 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2905950 | coll_ftm | 5_2_route | 1.0 | last meaningful line 0.0 h ago (218/218 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-glue-3754562 | glue | 3_3_place_gp | 0.4 | overflow best 0.6389 last 0.6389 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-kv3_io_ft-2905832 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5442 last 5442 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-kv3_pc__cl254f2e73__r872e39b5a-3971598 | kv3_pc | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc__cl254f2e73__r8b421e514-142304 | kv3_pc | 2_1_floorplan | 0.1 | repair_Viol best 7558 last 7558 rows 7 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-kv3_pc__cl5a95b461__r85c02c25c-3970568 | kv3_pc | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc__cl5a95b461__r882954158-3964582 | kv3_pc | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-sle_fe_v2-13810 | sle_fe_v2 | 2_1_floorplan | 0.2 | last meaningful line 0.1 h ago (85/85 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v3-158839 | sle_fw_v3 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-261611 | sle_hc0 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (275/275 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3766219 | sle_hc2 | 3_3_place_gp | 0.4 | overflow best 0.6613 last 0.6613 rows 30 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-sle_hc2__clcc5e3e61-4178870 | sle_hc2 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (86/86 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-60615 | sle_st_b_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (83/83 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v1__cl27746664-3977275 | sle_stm_v1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9729 last 0.9729 rows 6 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-2929686 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 3039 last 3039 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-320673 | slw_fe_v1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (244/244 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-147855 | slw_fe_v1 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v2__cle312294d-4052196 | slw_fe_v2 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9986 last 0.9986 rows 4 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-slw_fe_v2__clf110fab2-159072 | slw_fe_v2 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4019330 | slw_fw_v1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9988 last 0.9988 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-159197 | slw_fw_v2 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8537f156-217740 | slw_fw_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v2__cl8f84514c-3936002 | slw_fw_v2 | 3_3_place_gp | 0.3 | overflow best 0.4473 last 0.4473 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-221568 | slw_hc3 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (352/352 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl63e5a7a2-3977615 | slw_sc_v1 | 3_3_place_gp | 0.3 | overflow best 0.3888 last 0.3888 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3973955 | slw_sc_v1 | 3_3_place_gp | 0.3 | overflow best 0.3888 last 0.3888 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slw_sc_v3-4104776 | slw_sc_v3 | 3_3_place_gp | 0.2 | overflow best 0.3883 last 0.3883 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slw_stm_v2__cl9beb65e6-4016387 | slw_stm_v2 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_su_l1__cla2a78701-4064101 | slw_su_l1 | 3_3_place_gp | 0.2 | overflow best 0.157 last 0.157 rows 42 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-cbn_q01__clab6e67f2-167412 | cbn_q01 | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_hgi_v4-677838 | kv3_hgi_v4 | pregrt_ff_hold | 0.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_hgi_v5-772924 | kv3_hgi_v5 | tt_setup_repair | 0.8 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-2159263 | slw_hc1 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-2082988 | slw_hc3 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_hgi_v8-2448463 | kv3_hgi_v8 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 31.8 | drt_violations best 14975 last 14975 rows 14 | before-window best 22423, window best 14975 | PROGRESS: drt_violations improved 33.2 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 25.1 | drt_violations best 20899 last 20899 rows 13 | before-window best 39072, window best 20899 | PROGRESS: drt_violations improved 46.5 % in window |  |
| epyc7 | dpkit-sle_st_b_v1__pv0e7b1dcc-2157611 | sle_st_b_v1 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbf_q01-243499 | cbf_q01 | pregrt_ff_hold | 1.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbf_q11-255079 | cbf_q11 | pregrt_ff_hold | 1.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbx_q10__cl89936551-4175651 | cbx_q10 | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-coll_s-3875643 | coll_s | 5_1_grt | 1.4 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_sc_v3-4127450 | sle_sc_v3 | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-4075646 | sle_st_a_v2 | 5_1_grt | 1.4 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-4063882 | sle_st_a_v2 | 5_1_grt | 1.4 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_1_grt | 1.4 | repair_TNS best 0 last 0 rows 10 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | prd-eco_20261123_120225_75582-i3t-3968210 | eco_20261123_120225_75582-i3t | 5_2_route | 8.7 | drt_violations best 11 last 78 rows 44 | before-window best 827, window best 11 | PROGRESS: drt_violations improved 98.7 % in window |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l0_wfb17da-849937 | qfd_qc_su_lane_w_l0_wfb17da | 5_1_grt | 3.5 | repair_TNS best 0 last 0 rows 57 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l1_w460927-787688 | qfd_qc_su_lane_w_l1_w460927 | 5_1_grt | 3.5 | repair_TNS best 0 last 0 rows 60 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l4_w285325-818329 | qfd_qc_su_lane_w_l4_w285325 | 5_1_grt | 3.5 | repair_TNS best 0 last 0 rows 80 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l5_wf949e1-824935 | qfd_qc_su_lane_w_l5_wf949e1 | 5_1_grt | 3.5 | repair_TNS best 0 last 0 rows 69 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l6_wb51d05-853896 | qfd_qc_su_lane_w_l6_wb51d05 | 5_1_grt | 3.5 | repair_TNS best 0 last 0 rows 61 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l7_wd4f14d-862251 | qfd_qc_su_lane_w_l7_wd4f14d | 5_1_grt | 3.5 | repair_TNS best 0 last 0 rows 54 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-native59-1320092 | native59 | pregrt_ff_hold | 4.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-1345836 | sle_hc2 | pregrt_ff_hold | 4.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1365381 | sle_st_b_v1 | pregrt_ff_hold | 4.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | pregrt_ff_hold | 4.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-1401912 | slw_hc2 | pregrt_ff_hold | 4.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1439197 | slw_st_b_v1 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 39.4 | drt_violations best 74496 last 74496 rows 15 | before-window best 76746, window best 74496 | PROGRESS: drt_violations improved 2.9 % in window |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 8.7 | drt_violations best 2 last 2 rows 50 | before-window best 20278, window best 2 | PROGRESS: drt_violations improved 100.0 % in window |  |
