# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 08:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 11, 'GRT-LABEL': 2, 'YOUNG': 164, 'NO-DATA': 9, 'EXCLUDED': 1, 'PROGRESS': 35}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair_grt | 14.6 | repair_Violations best 0 last 0 rows 93 | before-window best 0, window best - | NO-PROGRESS: no new repair_Violations row in 6 h | REPORT-ONLY: lane-own kit (OPUS-FIX-QC-V4-R2 decid |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3951031 | sle_st_b_v2 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-4062944 | slw_hc3 | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-4102152 | slw_st_b_v1 | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4111701 | slw_st_b_v1 | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4115743 | slw_st_b_v2 | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-slw_st_b_v2__pvc2ec5bfb-4120782 | slw_st_b_v2 | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 38.4 | drt_violations best 48746 last 76207 rows 19 | before-window best 48746, window best 76207 | NO-PROGRESS: drt_violations best 76207 vs 48746 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | tt_setup_repair_grt | 14.3 | repair_Violations best 0 last 0 rows 62 | before-window best 0, window best - | NO-PROGRESS: no new repair_Violations row in 6 h | REPORT-ONLY: lane-own kit (OPUS-FIX-QC-V4-R2 decid |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc9 | dpkit-sle_st_b_v2__clfde1249e-2879520 | sle_st_b_v2 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 5_1_grt | 14.5 | grt rounds 2 overflow 5:13977 -> 10:10981 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | 5_1_grt | 7.8 | grt rounds 2 overflow 5:25842 -> 10:3973 | GRT-LABEL: DESIGN-FAIL: overflow 3973 at round 10 > 1000 |  |
| epyc10 | dpkit-cbf_q01_s2-261237 | cbf_q01_s2 | 3_4_place_resized | 0.5 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-cbn_q00__cl622f65d2-404046 | cbn_q00 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5116/5117 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-cbn_q00__cld7bf7197-260424 | cbn_q00 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-cbn_q01__clab6e67f2-167412 | cbn_q01 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (6745/6745 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-cbn_q01__clab6e67f2-265684 | cbn_q01 | 3_3_place_gp | 0.5 | overflow best 0.5209 last 0.5209 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-coll_ft__cla4a25d77-90691 | coll_ft | 5_2_route | 0.6 | last meaningful line 0.0 h ago (234/235 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-coll_n-91668 | coll_n | 5_2_route | 0.6 | last meaningful line 0.0 h ago (234/235 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p6-706840 | kv3_hg_v1p6 | 4_1_cts | 0.1 | last meaningful line 0.1 h ago (86/86 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v2__cle0015330-630449 | kv3_hgi_v2 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3117/3117 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v4-677838 | kv3_hgi_v4 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (4592/4592 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v5-772924 | kv3_hgi_v5 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5249/5249 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v2e-252410 | kv3_pv_v2e | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (7181/7181 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v4-680976 | kv3_pv_v4 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (6407/6408 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v5e-402621 | kv3_pv_v5e | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (7948/7948 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v5n-698511 | kv3_pv_v5n | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (7440/7440 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_pv_v6e-760052 | kv3_pv_v6e | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (7863/7863 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-225022 | sle_ctl | 3_1_place_gp_skip_io | 0.5 | overflow best 0.1717 last 0.1717 rows 41 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-577528 | sle_fw_v2 | 3_3_place_gp | 0.2 | overflow best 0.4024 last 0.4024 rows 4 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slw_st_a_v1__clb036e152-315416 | slw_st_a_v1 | hold_gate | 0.4 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-884966-9875 | 884966 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (2/2 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | pregrt_ff_hold | 1.8 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc2 | dpkit-kv3_hgi_v2__cl2862d491-2611569 | kv3_hgi_v2 | 5_1_grt | 1.8 | last meaningful line 0.5 h ago (288/1297 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v5ne-2612763 | kv3_pv_v5ne | 4_1_cts | 1.8 | last meaningful line 0.2 h ago (8756/8756 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pve-2456771 | kv3_pve | 5_1_grt | 2.0 | grt_overflow best 758 last 758 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-kv3_sys_c-2605096 | kv3_sys_c | 5_1_grt | 1.8 | last meaningful line 0.0 h ago (1139/1139 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 4.1 | drt_violations best 22046 last 22046 rows 3 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-4164928 | sle_hc0 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | postcts_gate_TT | 4.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-1186805 | sle_sc_v3 | postcts_gate_TT | 3.0 | last meaningful line 0.0 h ago (922/922 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-248626 | sle_st_b_v2 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (5559/5559 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-265811 | sle_st_b_v2 | 3_3_place_gp | 0.7 | overflow best 0.1943 last 0.1943 rows 41 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-sle_su_l0__cl7a55c676-4027948 | sle_su_l0 | 5_2_route | 3.9 | drt_violations best 189860 last 189860 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-67943 | slw_fe_v2 | 3_3_place_gp | 0.8 | overflow best 0.0987 last 0.0987 rows 42 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-90784 | slw_fw_v2 | 3_3_place_gp | 0.8 | overflow best 0.0986 last 0.0986 rows 43 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-slw_su_l0__cl1a1c1f8f-4150554 | slw_su_l0 | 5_2_route | 3.9 | drt_violations best 147934 last 147934 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | htr_eco_1288781 | htr_eco_1288781 | so_base0 | 0.1 | last meaningful line 0.1 h ago (10/10 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | htr_lec_1291366 | htr_lec_1291366 | lec | 0.1 | LEC last write -0.0 h ago | YOUNG: evidence 0.1 h < 6 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i3t-1317564 | eco_20261123_103136_2028090-i3t | 5_2_route | 2.9 | drt_violations best 2067 last 2067 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-sle-st-a-v2--pv30dda31f--pvd2ec7769-grt-1082583 | sle-st-a-v2--pv30dda31f--pvd2ec7769-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-slw-st-a-v1--clfc5867a6--pvf82a6c28-dump-1085323 | slw-st-a-v1--clfc5867a6--pvf82a6c28-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-slw-st-a-v1--clfc5867a6--pvf82a6c28-grt-1085323 | slw-st-a-v1--clfc5867a6--pvf82a6c28-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-slw-st-a-v2--clf4365a62-grt-1084719 | slw-st-a-v2--clf4365a62-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbf_q00__cl1b5a6458-3769028 | cbf_q00 | 3_3_place_gp | 0.9 | overflow best 0.5096 last 0.5096 rows 13 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-4105682 | cbn_q01 | 3_3_place_gp | 0.7 | overflow best 0.3762 last 0.3762 rows 25 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-cbx_q10__cl89936551_h-4106114 | cbx_q10 | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (200/200 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-995501 | hd_lep0N_w | 5_2_route | 4.5 | drt_violations best 14084 last 14084 rows 2 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl1cbb7497-3539262 | sle_fe_v1 | 3_4_place_resized | 0.9 | repair_Remaining best 5399 last 5399 rows 322 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-3547062 | sle_fw_v1 | 3_3_place_gp | 0.9 | overflow best 0.0998 last 0.0998 rows 42 | YOUNG: stage 0.7 h < 1 h |  |
| epyc7 | dpkit-sle_fw_v1__clf58b4dfb-3165565 | sle_fw_v1 | 3_3_place_gp | 1.1 | overflow best 0.2025 last 0.2025 rows 35 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3684775 | sle_fw_v2 | 3_4_place_resized | 0.9 | last meaningful line 0.1 h ago (364/364 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-3685349 | sle_hc0 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (58/58 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 9.1 | last meaningful line 0.5 h ago (273/274 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | postcts_gate_TT | 5.3 | last meaningful line -0.0 h ago (52105/52105 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_1_grt | 3.9 | repair_Remaining best 226490 last 226490 rows 210 | YOUNG: stage 0.9 h < 1 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl67389ecd-2555735 | sle_st_a_v1 | postcts_gate_FF | 3.6 | last meaningful line 0.0 h ago (1061/1061 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-2595387 | sle_st_a_v1 | postcts_gate_FF | 3.6 | last meaningful line 0.0 h ago (1013/1013 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3262037 | sle_st_b_v1 | 3_4_place_resized | 1.0 | last meaningful line 0.0 h ago (470/470 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3272378 | sle_st_b_v2 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (65/65 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | 5_2_route | 9.2 | drt_violations best 145769 last 145769 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | postcts_gate_TT | 5.1 | last meaningful line 0.1 h ago (793/793 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-3494601 | sle_stm_v3 | 5_2_route | 5.7 | drt_violations best 89680 last 89680 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | postcts_gate_FF | 9.5 | last meaningful line 0.1 h ago (398/398 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cl6bcaba89-3749440 | slw_hc2 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-2333813 | slw_sc_v1 | 5_1_grt | 3.7 | last meaningful line 0.1 h ago (144/144 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 9.3 | drt_violations best 407677 last 407677 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | postcts_gate_FF | 5.4 | last meaningful line -0.0 h ago (68907/68907 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-2594734 | slw_st_a_v1 | postcts_gate_FF | 3.6 | last meaningful line -0.0 h ago (21223/21223 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-3162191 | slw_st_b_v1 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (79/79 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3410045 | slw_st_b_v2 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | 5_2_route | 9.5 | drt_violations best 121446 last 121446 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3545065 | slw_stm_v2 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (65/65 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | postcts_gate_TT | 5.5 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | eco-abs-3857460 | eco-abs | generate_abstract | 0.8 | last meaningful line 0.4 h ago (1030/1030 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | otc-3312012-17262 | 3312012 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261124_145005_2036075-i1-1498701 | eco_20261124_145005_2036075-i1 | 5_2_route | 1.9 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | tt_setup_measure_grt | 14.2 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q01-243499 | cbf_q01 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5183/5183 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q11-255079 | cbf_q11 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5208/5208 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-cbx_q10__cl89936551-4175651 | cbx_q10 | tt_setup_repair | 0.6 | repair_Violations best 69 last 86 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-coll_ftc-3942021 | coll_ftc | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (6140/6140 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-coll_s-3875643 | coll_s | pregrt_ff_hold | 0.7 | last meaningful line 0.0 h ago (88/88 lines) | YOUNG: evidence 0.4 h < 2.5 h |  |
| epyc8 | dpkit-kv3_pv_v4n-177384 | kv3_pv_v4n | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (6197/6197 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (5991/5991 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 4_1_cts | 0.6 | last meaningful line 0.2 h ago (5420/5420 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 4_1_cts | 0.6 | last meaningful line 0.2 h ago (5567/5567 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl22c1ff36__pve230954c-3918742 | sle_hc1 | 4_1_cts | 0.6 | last meaningful line 0.2 h ago (5581/5581 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (5666/5666 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (5459/5459 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (5149/5149 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (5659/5659 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v3-4127450 | sle_sc_v3 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (3994/3994 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-4020071 | sle_st_a_v1 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (8209/8209 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-4075646 | sle_st_a_v2 | tt_setup_measure | 0.6 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-4063882 | sle_st_a_v2 | tt_setup_measure | 0.6 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (5445/5445 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (5369/5369 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (5578/5578 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v1__clbe630b9c-4072662 | sle_stm_v1 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (5896/5896 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (6162/6162 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l0__cl7a55c676-4020210 | sle_su_l0 | pregrt_ff_hold | 0.6 | repair_TNS best 10050.2 last 10050.2 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (5414/5414 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (5550/5550 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (5604/5604 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (5185/5185 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (5245/5245 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3909116 | slw_hc3 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (5068/5068 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-3949912 | slw_hc3 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (4803/4803 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (5614/5614 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4299/4299 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (8084/8084 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (8173/8173 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (5377/5377 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cle6023ec2-3866937 | slw_st_b_v1 | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-3890287 | slw_st_b_v2 | 3_3_place_gp | 0.7 | overflow best 0.2145 last 0.2145 rows 39 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-3848540 | slw_su_l0 | pregrt_ff_hold | 0.7 | repair_TNS best 12156.7 last 12156.7 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 5_1_grt | 0.6 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i2-2385296 | eco_20261123_164145_1995767-i2 | 5_2_route | 3.0 | drt_violations best 14428 last 14428 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-hd_serdes-3604295 | hd_serdes | 3_1_place_gp_skip_io | 0.7 | overflow best 0.9781 last 0.9941 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-slw_sc_v1__cl63e5a7a2-3279007 | slw_sc_v1 | 5_1_grt | 3.6 | last meaningful line 0.0 h ago (2042/2042 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | eco-abs-3097968 | eco-abs | generate_abstract | 1.0 | last meaningful line 0.4 h ago (1030/1030 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | otc-1814577-31530 | 1814577 | - | 1.9 |  | NO-DATA: no log found |  |
| epyc9 | otc-1939028-17446 | 1939028 | gold_b.ys | 1.8 | last meaningful line 1.5 h ago (84693/84693 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | otc-2103773-27089 | 2103773 | gold_b.ys | 1.7 | last meaningful line 1.5 h ago (67868/67868 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i3-368978 | eco_20261123_190031_3093983-i3 | 5_2_route | 2.8 | last meaningful line 0.2 h ago (294/295 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i3t-3891967 | eco_20261123_224216_149959-i3t | 5_1_grt | 0.5 | last meaningful line 0.3 h ago (141/141 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i2-1242463 | eco_20261124_010152_2867084-i2 | 5_2_route | 2.2 | last meaningful line 0.1 h ago (135/135 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-coll_core-709203 | coll_core | 3_3_place_gp | 0.9 | overflow best 0.2752 last 0.2792 rows 26 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-coll_ft__cl78c7b300-2325645 | coll_ft | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (1275/1275 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v8-2295582 | kv3_hgi_v8 | synth_odb_v | 0.1 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-2106033 | kv3_hroot | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.1 h ago (26/26 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 4_1_cts | 1.4 | last meaningful line 0.3 h ago (12476/12476 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3ne-3760907 | kv3_pv_v3ne | 4_1_cts | 1.8 | last meaningful line 0.2 h ago (9829/9829 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v5-1046392 | kv3_pv_v5 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (7204/7204 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v8-3837707 | kv3_pv_v8 | tt_setup_repair | 1.7 | repair_Viol best 2301 last 2301 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v8e-3858104 | kv3_pv_v8e | 5_1_grt | 1.7 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-native59-1320092 | native59 | pregrt_ff_hold | 4.0 | repair_TNS best 5962.38 last 5962.38 rows 1 | YOUNG: evidence 1.7 h < 2.5 h |  |
| intel1 | dpkit-native59-635922 | native59 | 2_4_floorplan_pdn | 0.9 | last meaningful line -0.0 h ago (9/9 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cla4f6f12f-668891 | sle_ctl | 3_1_place_gp_skip_io | 0.9 | overflow best 0.8278 last 0.8278 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 4_1_cts | 4.0 | last meaningful line 0.1 h ago (6156/6156 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-695475 | sle_hc0 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_hc1__cl22c1ff36__pve289215f-698914 | sle_hc1 | 3_3_place_gp | 0.9 | overflow best 0.2986 last 0.5376 rows 95 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-sle_hc1__cl7d360508__pv97423966-1341249 | sle_hc1 | 4_1_cts | 4.0 | last meaningful line 0.2 h ago (5916/5916 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-1345836 | sle_hc2 | pregrt_ff_hold | 4.0 | repair_TNS best 18689 last 18689 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-1610016 | sle_hc2 | 3_3_place_gp | 0.6 | overflow best 0.1948 last 0.1948 rows 45 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-708325 | sle_sc_v1 | 3_3_place_gp | 0.9 | overflow best 0.3421 last 0.3421 rows 21 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-sle_sc_v2-662172 | sle_sc_v2 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (368/368 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pv0e7b1dcc-656937 | sle_st_b_v1 | 3_3_place_gp | 0.9 | overflow best 0.5336 last 0.5336 rows 29 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-sle_stm_v3-655110 | sle_stm_v3 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | postcts_gate_TT | 2.0 | last meaningful line 0.3 h ago (1706/1706 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 4_1_cts | 3.9 | last meaningful line 0.2 h ago (6079/6079 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v3-667805 | slw_fw_v3 | 3_3_place_gp | 0.9 | overflow best 0.0986 last 0.0986 rows 42 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1387403 | slw_hc0 | 4_1_cts | 3.9 | last meaningful line 0.2 h ago (5368/5368 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-709430 | slw_hc0 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-683053 | slw_hc0 | 3_3_place_gp | 0.9 | overflow best 0.0999 last 0.0999 rows 51 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-slw_hc1__cl3449ea95-1389354 | slw_hc1 | 4_1_cts | 3.9 | last meaningful line 0.3 h ago (5832/5832 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1495669 | slw_hc1 | 3_3_place_gp | 0.6 | overflow best 0.4415 last 0.4415 rows 35 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-667937 | slw_hc1 | 3_4_place_resized | 0.9 | repair_Remaining best 148792 last 148792 rows 249 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-1401912 | slw_hc2 | pregrt_ff_hold | 3.9 | repair_TNS best 27413.8 last 27413.8 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-664249 | slw_hc2 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (409/409 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-1525148 | slw_hc3 | 3_3_place_gp | 0.6 | overflow best 0.0995 last 0.0995 rows 54 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-664248 | slw_hc3 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-658036 | slw_st_b_v2 | 3_3_place_gp | 0.9 | overflow best 0.3871 last 0.3871 rows 33 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-slw_stm_v3-709804 | slw_stm_v3 | 3_3_place_gp | 0.9 | overflow best 0.1511 last 0.1511 rows 39 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | heast_rne_lec | heast_rne_lec | SELF_2 | 0.4 | last meaningful line -0.0 h ago (4733/4733 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-1670752-16443 | 1670752 | - | 8.0 |  | NO-DATA: no log found |  |
| intel1 | otc-1797391-24144 | 1797391 | flow3 | 3.6 | last meaningful line 3.2 h ago (208/209 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | otc-3818878-18115 | 3818878 | - | 1.8 |  | NO-DATA: no log found |  |
| intel1 | otc-3854277-21865 | 3854277 | - | 1.7 |  | NO-DATA: no log found |  |
| intel1 | so_555245_ff_31306 | so_555245_ff_31306 | generate_abstract | 1.0 | last meaningful line 0.7 h ago (875/875 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | so_555245_tt_31306 | so_555245_tt_31306 | generate_abstract | 1.0 | last meaningful line 0.7 h ago (875/875 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2905950 | coll_ftm | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (118/118 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-hd_ctl-2783542 | hd_ctl | 3_3_place_gp | 0.3 | overflow best 0.3013 last 0.503 rows 135 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-2905765 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-365424-10454 | 365424 | - | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-2159263 | slw_hc1 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-2082988 | slw_hc3 | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_hgi_v7-2608982 | kv3_hgi_v7 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_hgi_v8-2448463 | kv3_hgi_v8 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_phy-1115318 | kv3_phy | 5_1_grt | 0.2 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc0__cl05696ed1-3966951 | sle_hc0 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-3970782 | sle_hc0 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-3979294 | sle_hc0 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3987964 | sle_hc2 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-4024927 | sle_st_b_v1 | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc2__cl6bcaba89-4049393 | slw_hc2 | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 31.1 | drt_violations best 14975 last 14975 rows 14 | before-window best 26552, window best 14975 | PROGRESS: drt_violations improved 43.6 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 24.4 | drt_violations best 20899 last 20899 rows 13 | before-window best 39072, window best 20899 | PROGRESS: drt_violations improved 46.5 % in window |  |
| epyc7 | dpkit-sle_st_b_v1__pv0e7b1dcc-2157611 | sle_st_b_v1 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_1_grt | 3.7 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_fe_v3-3927550 | sle_fe_v3 | 5_1_grt | 0.6 | repair_TNS best 0 last 0 rows 10 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | prd-eco_20261123_120225_75582-i3t-3968210 | eco_20261123_120225_75582-i3t | 5_2_route | 7.9 | drt_violations best 11 last 83 rows 43 | before-window best 36109, window best 11 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3249798 | slw_hc3 | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l0_wfb17da-849937 | qfd_qc_su_lane_w_l0_wfb17da | 5_1_grt | 2.5 | repair_TNS best 0 last 0 rows 95 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l1_w460927-787688 | qfd_qc_su_lane_w_l1_w460927 | 5_1_grt | 2.5 | repair_TNS best 0 last 0 rows 89 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l4_w285325-818329 | qfd_qc_su_lane_w_l4_w285325 | 5_1_grt | 2.5 | repair_TNS best 0 last 0 rows 111 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l5_wf949e1-824935 | qfd_qc_su_lane_w_l5_wf949e1 | 5_1_grt | 2.5 | repair_TNS best 0 last 0 rows 105 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l6_wb51d05-853896 | qfd_qc_su_lane_w_l6_wb51d05 | 5_1_grt | 2.5 | repair_TNS best 0 last 0 rows 103 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l7_wd4f14d-862251 | qfd_qc_su_lane_w_l7_wd4f14d | 5_1_grt | 2.5 | repair_TNS best 0 last 0 rows 83 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1365381 | sle_st_b_v1 | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1439197 | slw_st_b_v1 | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-1446982 | slw_st_b_v2 | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 38.6 | drt_violations best 74496 last 74496 rows 15 | before-window best 76746, window best 74496 | PROGRESS: drt_violations improved 2.9 % in window |  |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 16.7 | last meaningful line 5.9 h ago (107/107 lines) | PROGRESS: log still growing |  |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 20.4 | last meaningful line 5.9 h ago (107/107 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_io_ft-2905832 | kv3_io_ft | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel2 | dpkit-slice_station__t12-2929686 | slice_station__t12 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 7.9 | drt_violations best 6 last 27 rows 43 | before-window best 20278, window best 6 | PROGRESS: drt_violations improved 100.0 % in window |  |
