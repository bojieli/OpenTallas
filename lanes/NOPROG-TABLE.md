# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 08:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'UNSIGNABLE': 2, 'GRT-LABEL': 2, 'YOUNG': 148, 'NO-DATA': 6, 'EXCLUDED': 1, 'PROGRESS': 39}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 35.3 | drt_violations best 779 last 1029 rows 40 | before-window best 784, window best 779 | NO-PROGRESS: drt_violations best 779 vs 784 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair_grt | 14.1 | repair_Violations best 0 last 0 rows 93 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -743.27 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | tt_setup_repair_grt | 13.8 | repair_Violations best 0 last 0 rows 62 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -773.59 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | dpkit-sle_st_b_v2__clfde1249e-2879520 | sle_st_b_v2 | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 5_1_grt | 14.0 | grt rounds 2 overflow 5:13977 -> 10:10981 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | 5_1_grt | 7.3 | grt rounds 2 overflow 5:25842 -> 10:3973 | GRT-LABEL: DESIGN-FAIL: overflow 3973 at round 10 > 1000 |  |
| epyc10 | dpkit-cbn_q01__clab6e67f2-167412 | cbn_q01 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5658/5658 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-coll_ft__cla4a25d77-90691 | coll_ft | tt_setup_measure | 0.1 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-coll_n-91668 | coll_n | pregrt_ff_hold | 0.1 | repair_TNS best 19142.7 last 19142.7 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-225022 | sle_ctl | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-coll_ft__cl78c7b300-481807 | coll_ft | 3_3_place_gp | 0.1 | overflow best 0.3485 last 0.3486 rows 8 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (7224/7224 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v2__cl2862d491-2611569 | kv3_hgi_v2 | 5_1_grt | 1.3 | last meaningful line 0.0 h ago (288/289 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v7-2608982 | kv3_hgi_v7 | tt_setup_repair | 1.3 | repair_Viol best 88 last 88 rows 50 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-kv3_hgi_v8-2448463 | kv3_hgi_v8 | hold_gate | 1.5 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_io_cor_v1-2455343 | kv3_io_cor_v1 | 5_1_grt | 1.5 | last meaningful line 0.0 h ago (1770/1789 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v5ne-2612763 | kv3_pv_v5ne | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (8692/8692 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pve-2456771 | kv3_pve | tt_setup_repair | 1.5 | repair_Viol best 2899 last 2899 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 3.6 | drt_violations best 28705 last 28705 rows 2 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-4164928 | sle_hc0 | 3_3_place_gp | 0.3 | overflow best 0.9255 last 0.9255 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_1_grt | 3.5 | last meaningful line 0.1 h ago (2013/2030 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-1186805 | sle_sc_v3 | 5_1_grt | 2.5 | last meaningful line 0.1 h ago (1933/1939 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-248626 | sle_st_b_v2 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5126/5126 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-265811 | sle_st_b_v2 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (3607/3607 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l0__cl7a55c676-4027948 | sle_su_l0 | 5_2_route | 3.4 | last meaningful line 0.2 h ago (263/264 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-67943 | slw_fe_v2 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9986 last 0.9986 rows 4 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-90784 | slw_fw_v2 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l0__cl1a1c1f8f-4150554 | slw_su_l0 | 5_2_route | 3.4 | last meaningful line 0.2 h ago (263/264 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i3t-1317564 | eco_20261123_103136_2028090-i3t | 5_2_route | 2.4 | last meaningful line 0.3 h ago (288/289 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-slw-st-a-v1--clb036e152-grt-209747 | slw-st-a-v1--clb036e152-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbf_q00__cl1b5a6458-3769028 | cbf_q00 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.9975 last 0.9975 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-4105682 | cbn_q01 | 2_1_floorplan | 0.2 | repair_Viol best 6148 last 6148 rows 402 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-cbx_q10__cl89936551_h-4106114 | cbx_q10 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (161/161 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-995501 | hd_lep0N_w | 5_2_route | 4.0 | drt_violations best 90953 last 90953 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl1cbb7497-3539262 | sle_fe_v1 | 3_3_place_gp | 0.4 | overflow best 0.4887 last 0.4887 rows 3 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-3547062 | sle_fw_v1 | 3_3_place_gp | 0.4 | overflow best 0.3854 last 0.3854 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-sle_fw_v1__clf58b4dfb-3165565 | sle_fw_v1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.1969 last 0.1969 rows 46 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3684775 | sle_fw_v2 | 3_3_place_gp | 0.4 | overflow best 0.3828 last 0.3828 rows 6 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-3685349 | sle_hc0 | 3_3_place_gp | 0.4 | overflow best 0.8482 last 0.8482 rows 24 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 8.6 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | postcts_gate_TT | 4.8 | last meaningful line 0.1 h ago (2151/2151 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_1_grt | 3.4 | last meaningful line 0.2 h ago (143/143 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl67389ecd-2555735 | sle_st_a_v1 | postcts_gate_TT | 3.1 | last meaningful line 0.1 h ago (1068/1068 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-2595387 | sle_st_a_v1 | postcts_gate_TT | 3.1 | last meaningful line 0.1 h ago (1018/1018 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3262037 | sle_st_b_v1 | 3_3_place_gp | 0.5 | overflow best 0.7309 last 0.7309 rows 18 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3272378 | sle_st_b_v2 | 3_3_place_gp | 0.5 | overflow best 0.7274 last 0.7274 rows 20 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | 5_2_route | 8.7 | drt_violations best 145769 last 145769 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | tt_setup_repair_grt | 4.6 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-3494601 | sle_stm_v3 | 5_2_route | 5.2 | drt_violations best 89680 last 89680 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | postcts_gate_TT | 9.0 | last meaningful line 0.2 h ago (840/840 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cl6bcaba89-3749440 | slw_hc2 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.5449 last 0.5449 rows 38 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 5_1_grt | 3.2 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 8.8 | drt_violations best 407677 last 407677 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | postcts_gate_FF | 4.9 | last meaningful line 0.1 h ago (920/920 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-2594734 | slw_st_a_v1 | postcts_gate_FF | 3.1 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2581554 | slw_st_a_v1 | postcts_gate_FF | 3.1 | last meaningful line 0.0 h ago (515/515 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-3162191 | slw_st_b_v1 | 3_3_place_gp | 0.6 | overflow best 0.643 last 0.643 rows 24 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3410045 | slw_st_b_v2 | 3_3_place_gp | 0.5 | overflow best 0.7559 last 0.7559 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | 5_2_route | 9.0 | drt_violations best 121446 last 121446 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3545065 | slw_stm_v2 | 3_3_place_gp | 0.4 | overflow best 0.5017 last 0.5017 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | 5_1_grt | 5.0 | last meaningful line 0.3 h ago (1014/1040 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | eco-abs-3857460 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | otc-3312012-17262 | 3312012 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261124_145005_2036075-i1-1498701 | eco_20261124_145005_2036075-i1 | 5_2_route | 1.4 | last meaningful line 0.2 h ago (260/261 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | tt_setup_repair_grt | 13.7 | repair_Violations best 5 last 8 rows 64 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | dpkit-cbx_q10__cl89936551-4175651 | cbx_q10 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (4627/4628 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-coll_ftc-3942021 | coll_ftc | 4_1_cts | 0.1 | last meaningful line 0.1 h ago (5830/5830 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-coll_s-3875643 | coll_s | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (2611/2611 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pv_v4n-177384 | kv3_pv_v4n | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v1__cl8210183c-4103788 | sle_fe_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5611/5611 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_fe_v3-3927550 | sle_fe_v3 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (1508/1508 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl38badc56-3957610 | sle_hc0 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5035/5035 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-3972789 | sle_hc0 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (74/74 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl22c1ff36__pve230954c-3918742 | sle_hc1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3983308 | sle_hc1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (50/50 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3886701 | sle_hc2 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (5108/5108 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3875441 | sle_hc2 | 4_1_cts | 0.2 | last meaningful line -0.0 h ago (4833/4833 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl7479a5ec-50506 | sle_sc_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5240/5240 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v3-4127450 | sle_sc_v3 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3585/3585 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-4020071 | sle_st_a_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (8026/8026 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-4075646 | sle_st_a_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5582/5582 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v2__pv4242de79-4063882 | sle_st_a_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5568/5568 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3987189 | sle_st_b_v1 | 4_1_cts | 0.1 | last meaningful line -0.0 h ago (5085/5085 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3995293 | sle_st_b_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5023/5023 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_b_v2__clfde1249e-4005575 | sle_st_b_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5168/5168 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v1__clbe630b9c-4072662 | sle_stm_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5507/5507 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_stm_v2__cl7b3062fa-4057463 | sle_stm_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5739/5739 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_su_l0__cl7a55c676-4020210 | sle_su_l0 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3270/3270 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-4042590 | slw_fe_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5075/5075 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-3949238 | slw_hc0 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5198/5198 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl3449ea95-3916969 | slw_hc1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-4034779 | slw_hc1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3901898 | slw_hc2 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (4901/4901 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3909116 | slw_hc3 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (4708/4708 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-3949912 | slw_hc3 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (4457/4457 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4167447 | slw_sc_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5277/5277 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_sc_v2-113236 | slw_sc_v2 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-4004670 | slw_st_a_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (7874/7874 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4005900 | slw_st_a_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (8008/8008 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-4024716 | slw_st_b_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5021/5021 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v1__cle6023ec2-3866937 | slw_st_b_v1 | 1_synth | 0.2 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-3890287 | slw_st_b_v2 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (3649/3649 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-3848540 | slw_su_l0 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3526/3526 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__clcc9d0155-3981970 | slw_su_l1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2501/2501 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i2-2385296 | eco_20261123_164145_1995767-i2 | 5_2_route | 2.5 | drt_violations best 14428 last 14428 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | dpkit-hd_serdes-3604295 | hd_serdes | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | eco-abs-3097968 | eco-abs | generate_abstract | 0.8 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | otc-1814577-31530 | 1814577 | - | 1.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-1939028-17446 | 1939028 | gold_b.ys | 1.6 | last meaningful line 1.2 h ago (84693/84693 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | otc-2103773-27089 | 2103773 | gold_b.ys | 1.5 | last meaningful line 1.2 h ago (67868/67868 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | otc-2468382-9194 | 2468382 | gate.ys | 1.2 | last meaningful line 1.0 h ago (22052/22052 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i3-368978 | eco_20261123_190031_3093983-i3 | 5_2_route | 2.6 | last meaningful line 0.2 h ago (290/291 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i3t-3891967 | eco_20261123_224216_149959-i3t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i2-1242463 | eco_20261124_010152_2867084-i2 | 5_2_route | 2.0 | last meaningful line 0.1 h ago (133/133 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-coll_core-709203 | coll_core | 2_1_floorplan | 0.4 | repair_Viol best 1485 last 1485 rows 1036 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-coll_ftm-653917 | coll_ftm | 3_3_place_gp | 0.4 | overflow best 0.2894 last 0.3184 rows 36 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 4_1_cts | 0.9 | last meaningful line 0.2 h ago (12449/12449 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3ne-3760907 | kv3_pv_v3ne | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (9790/9790 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v5-1046392 | kv3_pv_v5 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (6821/6821 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v8-3837707 | kv3_pv_v8 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (9210/9210 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v8e-3858104 | kv3_pv_v8e | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (10390/10390 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-native59-1320092 | native59 | pregrt_ff_hold | 3.5 | repair_TNS best 5962.38 last 5962.38 rows 1 | YOUNG: evidence 1.2 h < 2.5 h |  |
| intel1 | dpkit-native59-635922 | native59 | 2_1_floorplan | 0.4 | repair_Viol best 18801 last 18801 rows 72 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_ctl__cla4f6f12f-668891 | sle_ctl | 2_1_floorplan | 0.4 | repair_Viol best 2599 last 2599 rows 990 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 4_1_cts | 3.5 | last meaningful line 0.2 h ago (6015/6015 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-695475 | sle_hc0 | 3_3_place_gp | 0.4 | last meaningful line -0.0 h ago (9/9 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_hc1__cl22c1ff36__pve289215f-698914 | sle_hc1 | 2_3_floorplan_tapcell | 0.4 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_hc1__cl7d360508__pv97423966-1341249 | sle_hc1 | 4_1_cts | 3.5 | last meaningful line 0.1 h ago (5912/5912 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-1345836 | sle_hc2 | tt_setup_repair | 3.5 | last meaningful line 0.0 h ago (384/384 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-1610016 | sle_hc2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (266/266 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-708325 | sle_sc_v1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.9646 last 0.9646 rows 20 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_sc_v2-662172 | sle_sc_v2 | 3_3_place_gp | 0.4 | overflow best 0.443 last 0.443 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-sle_st_a_v1__cl67389ecd-642159 | sle_st_a_v1 | 3_5_place_dp | 0.4 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-676867 | sle_st_a_v1 | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-686366 | sle_st_a_v2 | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (158/158 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pv0e7b1dcc-656937 | sle_st_b_v1 | 2_1_floorplan | 0.4 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v3-655110 | sle_stm_v3 | 3_3_place_gp | 0.4 | overflow best 0.5482 last 0.5482 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | postcts_gate_TT | 1.5 | last meaningful line 0.3 h ago (1700/1700 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 4_1_cts | 3.4 | last meaningful line 0.1 h ago (5936/5936 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v3-667805 | slw_fw_v3 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1387403 | slw_hc0 | 4_1_cts | 3.4 | last meaningful line 0.1 h ago (5364/5364 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-709430 | slw_hc0 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-683053 | slw_hc0 | 3_1_place_gp_skip_io | 0.4 | last meaningful line -0.0 h ago (11/11 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc1__cl3449ea95-1389354 | slw_hc1 | 4_1_cts | 3.4 | last meaningful line 0.1 h ago (5828/5828 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-1495669 | slw_hc1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (411/411 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-667937 | slw_hc1 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-1401912 | slw_hc2 | 4_1_cts | 3.4 | last meaningful line 0.0 h ago (5235/5235 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-664249 | slw_hc2 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.9985 last 0.9985 rows 8 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-1525148 | slw_hc3 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (351/351 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-664248 | slw_hc3 | 3_3_place_gp | 0.4 | overflow best 0.6802 last 0.6802 rows 32 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-671925 | slw_st_a_v1 | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_a_v2__clf4365a62-706428 | slw_st_a_v2 | 3_5_place_dp | 0.4 | last meaningful line 0.0 h ago (86/86 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-658036 | slw_st_b_v2 | 2_1_floorplan | 0.4 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v3-709804 | slw_stm_v3 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-1670752-16443 | 1670752 | - | 7.5 |  | NO-DATA: no log found |  |
| intel1 | otc-1797391-24144 | 1797391 | flow3 | 3.1 | last meaningful line 2.7 h ago (208/209 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | otc-3818878-18115 | 3818878 | - | 1.3 |  | NO-DATA: no log found |  |
| intel1 | otc-3854277-21865 | 3854277 | - | 1.2 |  | NO-DATA: no log found |  |
| intel1 | so_555245_ff_31306 | so_555245_ff_31306 | generate_abstract | 0.5 | last meaningful line 0.3 h ago (875/875 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | so_555245_tt_31306 | so_555245_tt_31306 | generate_abstract | 0.5 | last meaningful line 0.3 h ago (875/875 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | otc-3420116-22717 | 3420116 | - | 0.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-2159263 | slw_hc1 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-2082988 | slw_hc3 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_sys_c-2605096 | kv3_sys_c | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc0__cl05696ed1-3966951 | sle_hc0 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-3970782 | sle_hc0 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-3979294 | sle_hc0 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3987964 | sle_hc2 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-4024927 | sle_st_b_v1 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3951031 | sle_st_b_v2 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc2__cl6bcaba89-4049393 | slw_hc2 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-4062944 | slw_hc3 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-4102152 | slw_st_b_v1 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4111701 | slw_st_b_v1 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4115743 | slw_st_b_v2 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v2__pvc2ec5bfb-4120782 | slw_st_b_v2 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 30.6 | drt_violations best 17065 last 17065 rows 13 | before-window best 26552, window best 17065 | PROGRESS: drt_violations improved 35.7 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 23.9 | drt_violations best 20899 last 20899 rows 13 | before-window best 39072, window best 20899 | PROGRESS: drt_violations improved 46.5 % in window |  |
| epyc7 | dpkit-sle_st_b_v1__pv0e7b1dcc-2157611 | sle_st_b_v1 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-2333813 | slw_sc_v1 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 37.9 | drt_violations best 48746 last 160916 rows 18 | before-window best 48746, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | prd-eco_20261123_120225_75582-i3t-3968210 | eco_20261123_120225_75582-i3t | 5_2_route | 7.4 | drt_violations best 11 last 83 rows 43 | before-window best 36109, window best 11 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3249798 | slw_hc3 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_sc_v1__cl63e5a7a2-3279007 | slw_sc_v1 | 5_1_grt | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l0_wfb17da-849937 | qfd_qc_su_lane_w_l0_wfb17da | 5_1_grt | 2.3 | repair_TNS best 0 last 0 rows 33 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l1_w460927-787688 | qfd_qc_su_lane_w_l1_w460927 | 5_1_grt | 2.3 | repair_TNS best 0 last 0 rows 29 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l4_w285325-818329 | qfd_qc_su_lane_w_l4_w285325 | 5_1_grt | 2.3 | repair_TNS best 0 last 0 rows 52 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l5_wf949e1-824935 | qfd_qc_su_lane_w_l5_wf949e1 | 5_1_grt | 2.3 | repair_TNS best 0 last 0 rows 51 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l6_wb51d05-853896 | qfd_qc_su_lane_w_l6_wb51d05 | 5_1_grt | 2.3 | repair_TNS best 0 last 0 rows 49 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l7_wd4f14d-862251 | qfd_qc_su_lane_w_l7_wd4f14d | 5_1_grt | 2.2 | repair_TNS best 0 last 0 rows 21 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1365381 | sle_st_b_v1 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1439197 | slw_st_b_v1 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-1446982 | slw_st_b_v2 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 38.1 | drt_violations best 74496 last 74496 rows 15 | before-window best 76746, window best 74496 | PROGRESS: drt_violations improved 2.9 % in window |  |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 16.2 | last meaningful line 5.4 h ago (107/107 lines) | PROGRESS: log still growing |  |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 19.9 | last meaningful line 5.4 h ago (107/107 lines) | PROGRESS: log still growing |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 7.4 | drt_violations best 6 last 127 rows 41 | before-window best 20278, window best 6 | PROGRESS: drt_violations improved 100.0 % in window |  |
