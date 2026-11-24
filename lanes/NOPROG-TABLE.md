# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 08:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'GRT-LABEL': 2, 'YOUNG': 106, 'NO-DATA': 5, 'EXCLUDED': 1, 'PROGRESS': 35}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair_grt | 13.9 | repair_Violations best 0 last 0 rows 93 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -743.27 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | tt_setup_repair_grt | 13.6 | repair_Violations best 0 last 0 rows 62 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -773.59 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 5_1_grt | 13.7 | grt rounds 2 overflow 5:13977 -> 10:10981 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | 5_1_grt | 7.0 | grt rounds 2 overflow 5:25842 -> 10:3973 | GRT-LABEL: DESIGN-FAIL: overflow 3973 at round 10 > 1000 |  |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (7189/7189 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v7-2608982 | kv3_hgi_v7 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (6742/6742 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v8-2448463 | kv3_hgi_v8 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (5336/5336 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v5ne-2612763 | kv3_pv_v5ne | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (8684/8684 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pve-2456771 | kv3_pve | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (10892/10892 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_sys_c-2605096 | kv3_sys_c | pregrt_ff_hold | 1.1 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 3.3 | drt_violations best 112571 last 112571 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-4164928 | sle_hc0 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (317/317 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_1_grt | 3.2 | last meaningful line 0.1 h ago (1957/1970 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-1186805 | sle_sc_v3 | 5_1_grt | 2.3 | last meaningful line 0.2 h ago (1279/1854 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l0__cl7a55c676-4027948 | sle_su_l0 | 5_2_route | 3.2 | last meaningful line 0.2 h ago (259/260 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-67943 | slw_fe_v2 | 1_synth | 0.0 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-90784 | slw_fw_v2 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (241/241 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l0__cl1a1c1f8f-4150554 | slw_su_l0 | 5_2_route | 3.1 | last meaningful line 0.2 h ago (259/260 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | otc-3845971-26562 | 3845971 | signoff | 0.2 | last meaningful line 0.2 h ago (3/3 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i3t-1317564 | eco_20261123_103136_2028090-i3t | 5_2_route | 2.2 | last meaningful line 0.1 h ago (286/287 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00__cl1b5a6458-3769028 | cbf_q00 | 2_1_floorplan | 0.1 | repair_Viol best 6140 last 6140 rows 217 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-coll_ft__cla4a25d77-3263737 | coll_ft | 3_5_place_dp | 0.3 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-995501 | hd_lep0N_w | 5_2_route | 3.7 | drt_violations best 90953 last 90953 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl1cbb7497-3539262 | sle_fe_v1 | 2_1_floorplan | 0.2 | last meaningful line 0.1 h ago (85/85 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__cl9d029624-3547062 | sle_fw_v1 | 2_1_floorplan | 0.2 | last meaningful line 0.1 h ago (85/85 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__clf58b4dfb-3165565 | sle_fw_v1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9984 last 0.9984 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_fw_v2__cl6740750e-3684775 | sle_fw_v2 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-3685349 | sle_hc0 | 1_synth | 0.1 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 8.4 | last meaningful line 0.3 h ago (269/270 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | postcts_gate_TT | 4.5 | last meaningful line 0.1 h ago (977/977 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 5_1_grt | 3.2 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl67389ecd-2555735 | sle_st_a_v1 | postcts_gate_TT | 2.9 | last meaningful line 0.1 h ago (546/546 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-2595387 | sle_st_a_v1 | postcts_gate_TT | 2.8 | last meaningful line 0.1 h ago (525/525 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v1__pv0e7b1dcc-2157611 | sle_st_b_v1 | pregrt_ff_hold | 3.1 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.7 h < 2.5 h |  |
| epyc7 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3262037 | sle_st_b_v1 | 2_1_floorplan | 0.3 | last meaningful line 0.0 h ago (95/95 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3272378 | sle_st_b_v2 | 2_1_floorplan | 0.3 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | 5_2_route | 8.5 | drt_violations best 145769 last 145769 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | 5_1_grt | 4.4 | last meaningful line 0.1 h ago (1002/1008 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-3494601 | sle_stm_v3 | 5_2_route | 4.9 | last meaningful line 0.3 h ago (269/270 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | postcts_gate_TT | 8.8 | last meaningful line 0.1 h ago (834/834 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cl6bcaba89-3749440 | slw_hc2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (403/403 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 8.6 | last meaningful line 0.5 h ago (283/284 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | postcts_gate_TT | 4.7 | last meaningful line -0.0 h ago (42522/42522 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clb036e152-3548028 | slw_st_a_v1 | 3_3_place_gp | 0.2 | overflow best 0.5728 last 0.5728 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-2594734 | slw_st_a_v1 | postcts_gate_TT | 2.8 | last meaningful line 0.1 h ago (995/995 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2581554 | slw_st_a_v1 | postcts_gate_TT | 2.8 | last meaningful line -0.0 h ago (3273/3273 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v2__clf4365a62-2648278 | slw_st_a_v2 | postcts_gate_FF | 2.8 | last meaningful line -0.0 h ago (7027/7027 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-3162191 | slw_st_b_v1 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3410045 | slw_st_b_v2 | synth_odb_v | 0.2 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | 5_2_route | 8.8 | last meaningful line 0.5 h ago (279/280 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3545065 | slw_stm_v2 | 2_1_floorplan | 0.2 | repair_Viol best 467 last 467 rows 483 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | 5_1_grt | 4.7 | last meaningful line 0.0 h ago (1014/1014 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | eco-abs-3857460 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.0 h ago (1024/1024 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | otc-3312012-17262 | 3312012 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261124_145005_2036075-i1-1498701 | eco_20261124_145005_2036075-i1 | 5_2_route | 1.1 | last meaningful line 0.1 h ago (257/257 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | tt_setup_repair_grt | 13.5 | repair_Violations best 5 last 8 rows 64 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i2-2385296 | eco_20261123_164145_1995767-i2 | 5_2_route | 2.2 | drt_violations best 14428 last 14428 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-hd_serdes-3604295 | hd_serdes | 1_2_yosys | 0.2 | last meaningful line 0.1 h ago (280/280 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_sc_v1__cl63e5a7a2-3279007 | slw_sc_v1 | 5_1_grt | 3.1 | last meaningful line 0.2 h ago (1304/1940 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | eco-abs-3097968 | eco-abs | generate_abstract | 0.5 | last meaningful line 0.3 h ago (1028/1028 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l0_wfb17da-849937 | qfd_qc_su_lane_w_l0_wfb17da | 5_1_grt | 2.0 | repair_Remaining best 111159 last 111159 rows 165 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l1_w460927-787688 | qfd_qc_su_lane_w_l1_w460927 | 5_1_grt | 2.0 | repair_Remaining best 135641 last 135641 rows 139 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l4_w285325-818329 | qfd_qc_su_lane_w_l4_w285325 | 5_1_grt | 2.0 | last meaningful line 0.2 h ago (202/1544 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l5_wf949e1-824935 | qfd_qc_su_lane_w_l5_wf949e1 | 5_1_grt | 2.0 | last meaningful line 0.5 h ago (202/1544 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l6_wb51d05-853896 | qfd_qc_su_lane_w_l6_wb51d05 | 5_1_grt | 2.0 | last meaningful line 0.2 h ago (202/1546 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | otc-1814577-31530 | 1814577 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc9 | otc-1939028-17446 | 1939028 | gold_b.ys | 1.3 | last meaningful line 1.0 h ago (84693/84693 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | otc-2103773-27089 | 2103773 | gold_b.ys | 1.2 | last meaningful line 1.0 h ago (67868/67868 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | otc-2468382-9194 | 2468382 | gate.ys | 1.0 | last meaningful line 0.7 h ago (22052/22052 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i3-368978 | eco_20261123_190031_3093983-i3 | 5_2_route | 2.3 | last meaningful line 0.3 h ago (286/287 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i2-1242463 | eco_20261124_010152_2867084-i2 | 5_1_grt | 1.7 | last meaningful line 1.2 h ago (242/1870 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-coll_core-709203 | coll_core | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (576/576 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-coll_ftm-653917 | coll_ftm | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (12367/12368 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3ne-3760907 | kv3_pv_v3ne | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (9763/9763 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v5-1046392 | kv3_pv_v5 | rtl_lint | 0.0 | last meaningful line 0.0 h ago (12/12 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v8-3837707 | kv3_pv_v8 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (9180/9180 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v8e-3858104 | kv3_pv_v8e | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (10385/10385 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-native59-1320092 | native59 | pregrt_ff_hold | 3.2 | repair_TNS best 5962.38 last 5962.38 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel1 | dpkit-native59-635922 | native59 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (498/498 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cla4f6f12f-668891 | sle_ctl | synth_odb_v | 0.1 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 4_1_cts | 3.2 | last meaningful line 0.2 h ago (6012/6012 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-695475 | sle_hc0 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (400/400 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_hc1__cl22c1ff36__pve289215f-698914 | sle_hc1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (408/408 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_hc1__cl7d360508__pv97423966-1341249 | sle_hc1 | 4_1_cts | 3.2 | last meaningful line 0.2 h ago (5909/5909 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-1345836 | sle_hc2 | 4_1_cts | 3.2 | last meaningful line 0.2 h ago (5103/5103 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-sle_sc_v1__cl115da35f-708325 | sle_sc_v1 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_sc_v2-662172 | sle_sc_v2 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_st_a_v1__cl67389ecd-642159 | sle_st_a_v1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-676867 | sle_st_a_v1 | 2_2_floorplan_macro | 0.1 | last meaningful line 0.0 h ago (65/65 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-686366 | sle_st_a_v2 | 2_3_floorplan_tapcell | 0.1 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pv0e7b1dcc-656937 | sle_st_b_v1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (383/383 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1365381 | sle_st_b_v1 | pregrt_ff_hold | 3.2 | repair_TNS best 19705 last 19705 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-sle_stm_v3-655110 | sle_stm_v3 | 2_1_floorplan | 0.2 | repair_Viol best 288 last 288 rows 51 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | postcts_gate_TT | 1.3 | last meaningful line 0.0 h ago (1700/1700 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 4_1_cts | 3.2 | last meaningful line 0.1 h ago (5932/5932 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v3-667805 | slw_fw_v3 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1387403 | slw_hc0 | 4_1_cts | 3.2 | last meaningful line 0.2 h ago (5361/5361 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-709430 | slw_hc0 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (400/400 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-683053 | slw_hc0 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (406/406 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc1__cl3449ea95-1389354 | slw_hc1 | 4_1_cts | 3.2 | last meaningful line 0.2 h ago (5825/5825 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-667937 | slw_hc1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (411/411 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-1401912 | slw_hc2 | 4_1_cts | 3.2 | last meaningful line 0.1 h ago (5116/5116 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-664249 | slw_hc2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (406/406 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-664248 | slw_hc3 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (365/365 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-671925 | slw_st_a_v1 | 2_3_floorplan_tapcell | 0.1 | last meaningful line 0.0 h ago (7/7 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_a_v2__clf4365a62-706428 | slw_st_a_v2 | 2_3_floorplan_tapcell | 0.1 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pvc2ec5bfb-658036 | slw_st_b_v2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (380/380 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v3-709804 | slw_stm_v3 | 1_synth | 0.1 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-1670752-16443 | 1670752 | - | 7.3 |  | NO-DATA: no log found |  |
| intel1 | otc-1797391-24144 | 1797391 | flow3 | 2.8 | last meaningful line 2.5 h ago (208/209 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | otc-3818878-18115 | 3818878 | - | 1.0 |  | NO-DATA: no log found |  |
| intel1 | otc-3854277-21865 | 3854277 | - | 1.0 |  | NO-DATA: no log found |  |
| intel1 | so_555245_ff_31306 | so_555245_ff_31306 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (875/875 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | so_555245_tt_31306 | so_555245_tt_31306 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (875/875 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-3420116-22717 | 3420116 | - | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-2159263 | slw_hc1 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-2082988 | slw_hc3 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 35.1 | drt_violations best 779 last 1212 rows 39 | before-window best 912, window best 779 | PROGRESS: drt_violations improved 14.6 % in window |  |
| epyc2 | dpkit-kv3_hgi_v2__cl2862d491-2611569 | kv3_hgi_v2 | pregrt_ff_hold | 1.1 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-kv3_io_cor_v1-2455343 | kv3_io_cor_v1 | 5_1_grt | 1.2 | repair_TNS best 0 last 0 rows 4 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc0__cl05696ed1-3966951 | sle_hc0 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-3970782 | sle_hc0 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-3979294 | sle_hc0 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3987964 | sle_hc2 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-4024927 | sle_st_b_v1 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3951031 | sle_st_b_v2 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc2__cl6bcaba89-4049393 | slw_hc2 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-4062944 | slw_hc3 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-4102152 | slw_st_b_v1 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4111701 | slw_st_b_v1 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4115743 | slw_st_b_v2 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v2__pvc2ec5bfb-4120782 | slw_st_b_v2 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 30.3 | drt_violations best 17065 last 17065 rows 13 | before-window best 28844, window best 17065 | PROGRESS: drt_violations improved 40.8 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 23.6 | drt_violations best 20899 last 20899 rows 13 | before-window best 40914, window best 20899 | PROGRESS: drt_violations improved 48.9 % in window |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-2333813 | slw_sc_v1 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 37.7 | drt_violations best 48746 last 160916 rows 18 | before-window best 48746, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | prd-eco_20261123_120225_75582-i3t-3968210 | eco_20261123_120225_75582-i3t | 5_2_route | 7.2 | drt_violations best 11 last 124 rows 42 | before-window best 36109, window best 11 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-sle_st_b_v2__clfde1249e-2879520 | sle_st_b_v2 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3249798 | slw_hc3 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l7_wd4f14d-862251 | qfd_qc_su_lane_w_l7_wd4f14d | 5_1_grt | 2.0 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1439197 | slw_st_b_v1 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-1446982 | slw_st_b_v2 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 37.9 | drt_violations best 74496 last 74496 rows 15 | before-window best 76746, window best 74496 | PROGRESS: drt_violations improved 2.9 % in window |  |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 15.9 | last meaningful line 5.1 h ago (107/107 lines) | PROGRESS: log still growing |  |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 19.7 | last meaningful line 5.1 h ago (107/107 lines) | PROGRESS: log still growing |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 7.2 | drt_violations best 6 last 70 rows 34 | before-window best 20278, window best 6 | PROGRESS: drt_violations improved 100.0 % in window |  |
