# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 07:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'GRT-LABEL': 2, 'YOUNG': 90, 'NO-DATA': 4, 'EXCLUDED': 1, 'PROGRESS': 34}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair_grt | 13.4 | repair_Violations best 0 last 0 rows 93 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -743.27 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | tt_setup_repair_grt | 13.1 | repair_Violations best 0 last 0 rows 62 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -773.59 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 5_1_grt | 13.2 | grt rounds 2 overflow 5:13977 -> 10:10981 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | 5_1_grt | 6.5 | grt rounds 2 overflow 5:25842 -> 10:3973 | GRT-LABEL: DESIGN-FAIL: overflow 3973 at round 10 > 1000 |  |
| epyc10 | dpkit-coll_ft__cla4a25d77-1296583 | coll_ft | 5_2_route | 1.9 | drt_violations best 12509 last 12509 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2032997 | sle_hc0 | 4_1_cts | 1.4 | last meaningful line 0.1 h ago (5802/5802 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-2226501 | slw_fw_v2 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (5037/5037 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-2159263 | slw_hc1 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (5523/5523 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-2082988 | slw_hc3 | pregrt_ff_hold | 1.4 | repair_TNS best 89067.5 last 89067.5 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (6760/6760 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v7-2608982 | kv3_hgi_v7 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (6472/6472 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v8-2448463 | kv3_hgi_v8 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (5126/5126 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v5ne-2612763 | kv3_pv_v5ne | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (8560/8560 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pve-2456771 | kv3_pve | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (10843/10843 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_sys_c-2605096 | kv3_sys_c | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (5313/5313 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_sys_c-3236960 | kv3_sys_c | 2_1_floorplan | 0.1 | repair_Viol best 684 last 684 rows 627 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 2.8 | drt_violations best 112571 last 112571 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_1_grt | 2.7 | repair_Remaining best 249464 last 249464 rows 188 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-sle_sc_v3-1186805 | sle_sc_v3 | 5_1_grt | 1.8 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l0__cl7a55c676-4027948 | sle_su_l0 | 5_2_route | 2.7 | last meaningful line 0.0 h ago (247/247 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l0__cl1a1c1f8f-4150554 | slw_su_l0 | 5_2_route | 2.6 | last meaningful line 0.1 h ago (133/133 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i3t-1317564 | eco_20261123_103136_2028090-i3t | 5_2_route | 1.7 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | so_3348723_ff_5583 | so_3348723_ff_5583 | sta | 0.0 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | so_3384923_ff_19849 | so_3384923_ff_19849 | sta | 0.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | so_3384923_tt_19849 | so_3384923_tt_19849 | sta | 0.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-2448802 | hd_lep0N_w | 3_1_place_gp_skip_io | 0.1 | overflow best 0.7302 last 0.8124 rows 10 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N_w-995501 | hd_lep0N_w | 5_2_route | 3.2 | last meaningful line 0.2 h ago (258/259 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 7.9 | last meaningful line 0.5 h ago (265/266 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | tt_setup_measure_grt | 4.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl67389ecd-2555735 | sle_st_a_v1 | 5_1_grt | 2.4 | last meaningful line 0.0 h ago (2109/2158 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-2492812 | sle_st_a_v1 | postcts_gate_TT | 2.4 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-2595387 | sle_st_a_v1 | 5_1_grt | 2.3 | last meaningful line 0.1 h ago (2091/2133 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-2355490 | sle_st_a_v2 | postcts_gate_FF | 2.5 | last meaningful line 0.0 h ago (938/938 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-2354216 | sle_st_a_v2 | postcts_gate_FF | 2.5 | last meaningful line 0.0 h ago (964/964 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv4242de79-2374002 | sle_st_a_v2 | postcts_gate_FF | 2.5 | last meaningful line 0.0 h ago (958/958 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v1__pv0e7b1dcc-2157611 | sle_st_b_v1 | pregrt_ff_hold | 2.6 | repair_TNS best 22304.1 last 22304.1 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | 5_2_route | 8.0 | last meaningful line 0.3 h ago (282/283 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-3494601 | sle_stm_v3 | 5_2_route | 4.4 | last meaningful line 0.3 h ago (263/264 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | postcts_gate_TT | 8.3 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 8.1 | last meaningful line 0.3 h ago (281/282 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | postcts_gate_TT | 4.2 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clb036e152-2495581 | slw_st_a_v1 | postcts_gate_TT | 2.4 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-2594734 | slw_st_a_v1 | postcts_gate_TT | 2.3 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2581554 | slw_st_a_v1 | postcts_gate_FF | 2.3 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v2__clf4365a62-2648278 | slw_st_a_v2 | postcts_gate_TT | 2.3 | last meaningful line 0.0 h ago (928/928 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | 5_2_route | 8.3 | last meaningful line 0.1 h ago (277/278 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | pregrt_ff_hold | 2.5 | repair_TNS best 20875.5 last 20875.5 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | 5_1_grt | 4.2 | last meaningful line 0.3 h ago (282/920 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | prd-count-p1_bc-4134013 | count-p1_bc | prd_count_p1_bc | 0.1 | last meaningful line 0.1 h ago (1019/1019 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261124_145005_2036075-i1-1498701 | eco_20261124_145005_2036075-i1 | 5_1_grt | 0.6 | last meaningful line 0.3 h ago (295/380 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | tt_setup_repair_grt | 13.0 | repair_Violations best 5 last 8 rows 64 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i3t-3968210 | eco_20261123_120225_75582-i3t | 5_2_route | 6.7 | drt_violations best 11 last 125 rows 41 | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i2-2385296 | eco_20261123_164145_1995767-i2 | 5_2_route | 1.7 | last meaningful line 0.1 h ago (293/294 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-slw_sc_v1__cl63e5a7a2-3279007 | slw_sc_v1 | 5_1_grt | 2.6 | last meaningful line 0.1 h ago (145/145 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | eco-abs-3097968 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (1024/1024 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l0_wfb17da-849937-lec | qfd_qc_su_lane_w_l0_wfb17da | lec | 1.5 | LEC last write 0.0 h ago | YOUNG: evidence 1.5 h < 6 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l4_w285325-818329 | qfd_qc_su_lane_w_l4_w285325 | 5_1_grt | 1.5 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l4_w285325-818329-lec | qfd_qc_su_lane_w_l4_w285325 | lec | 1.5 | LEC last write 0.0 h ago | YOUNG: evidence 1.5 h < 6 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l5_wf949e1-824935 | qfd_qc_su_lane_w_l5_wf949e1 | 5_1_grt | 1.5 | last meaningful line -0.0 h ago (122/122 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l5_wf949e1-824935-lec | qfd_qc_su_lane_w_l5_wf949e1 | lec | 1.5 | LEC last write -0.0 h ago | YOUNG: evidence 1.5 h < 6 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l6_wb51d05-853896-lec | qfd_qc_su_lane_w_l6_wb51d05 | lec | 1.5 | LEC last write 0.0 h ago | YOUNG: evidence 1.5 h < 6 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l7_wd4f14d-862251-lec | qfd_qc_su_lane_w_l7_wd4f14d | lec | 1.5 | LEC last write 0.0 h ago | YOUNG: evidence 1.5 h < 6 h |  |
| epyc9 | otc-1814577-31530 | 1814577 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc9 | otc-1939028-17446 | 1939028 | gold_b.ys | 0.8 | last meaningful line 0.5 h ago (84693/84693 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | otc-2103773-27089 | 2103773 | gold_b.ys | 0.7 | last meaningful line 0.5 h ago (67868/67868 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | otc-2468382-9194 | 2468382 | gate.ys | 0.5 | last meaningful line 0.3 h ago (22052/22052 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | otc-3132819-11963 | 3132819 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (3/3 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i3-368978 | eco_20261123_190031_3093983-i3 | 5_2_route | 1.8 | last meaningful line 0.3 h ago (280/281 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i2-1242463 | eco_20261124_010152_2867084-i2 | 5_1_grt | 1.2 | last meaningful line 0.7 h ago (242/1553 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | so_2550577_ff_66664 | so_2550577_ff_66664 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (695/695 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | so_2550577_tt_66664 | so_2550577_tt_66664 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (695/695 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (11964/11964 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3ne-3760907 | kv3_pv_v3ne | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (9643/9643 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v8-3837707 | kv3_pv_v8 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (9047/9047 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v8e-3858104 | kv3_pv_v8e | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (10260/10260 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-native59-1320092 | native59 | pregrt_ff_hold | 2.7 | repair_TNS best 5962.38 last 5962.38 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 4_1_cts | 2.7 | last meaningful line 0.3 h ago (5983/5983 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-sle_hc1__cl7d360508__pv97423966-1341249 | sle_hc1 | 4_1_cts | 2.7 | last meaningful line 0.2 h ago (5881/5881 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-1345836 | sle_hc2 | 4_1_cts | 2.7 | last meaningful line 0.2 h ago (5096/5096 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1365381 | sle_st_b_v1 | hold_gate | 2.7 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | postcts_gate_TT | 0.8 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 4_1_cts | 2.7 | last meaningful line 0.1 h ago (5927/5927 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1387403 | slw_hc0 | 4_1_cts | 2.7 | last meaningful line 0.3 h ago (5333/5333 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-slw_hc1__cl3449ea95-1389354 | slw_hc1 | 4_1_cts | 2.7 | last meaningful line 0.2 h ago (5797/5797 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-1401912 | slw_hc2 | 4_1_cts | 2.7 | last meaningful line 0.3 h ago (5107/5107 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1439197 | slw_st_b_v1 | pregrt_ff_hold | 2.6 | repair_TNS best 20547.1 last 20547.1 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | pregrt_ff_hold | 2.6 | repair_TNS best 14328.4 last 14328.4 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | eco-abs-3571988 | eco-abs | generate_abstract | 0.8 | last meaningful line 0.2 h ago (871/871 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | otc-1670752-16443 | 1670752 | - | 6.8 |  | NO-DATA: no log found |  |
| intel1 | otc-1797391-24144 | 1797391 | flow3 | 2.3 | last meaningful line 2.0 h ago (208/209 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | otc-3818878-18115 | 3818878 | - | 0.5 |  | NO-DATA: no log found |  |
| intel1 | otc-3854277-21865 | 3854277 | - | 0.5 |  | NO-DATA: no log found |  |
| intel2 | dpkit-coll_ftm-1873477 | coll_ftm | 5_3_fillcell | 2.2 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl23f6a148-151203 | kv3_pc_v1 | 3_1_place_gp_skip_io | 0.7 | overflow best 0.1957 last 0.1957 rows 43 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-kv3_pv_v1-152951 | kv3_pv_v1 | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (272/272 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v2-351905 | kv3_pv_v2 | 3_3_place_gp | 0.6 | overflow best 0.0971 last 0.0971 rows 41 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-kv3_pv_v7-122568 | kv3_pv_v7 | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 6.7 | drt_violations best 8 last 38 rows 27 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc9 | otc-2292915-30071 | 2292915 | - | 0.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 34.6 | drt_violations best 779 last 1386 rows 38 | before-window best 954, window best 779 | PROGRESS: drt_violations improved 18.3 % in window |  |
| epyc2 | dpkit-hd_st_n4-4161241 | hd_st_n4 | 5_2_route | 2.6 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
| epyc2 | dpkit-kv3_hgi_v2__cl2862d491-2611569 | kv3_hgi_v2 | pregrt_ff_hold | 0.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-kv3_io_cor_v1-2455343 | kv3_io_cor_v1 | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc0__cl05696ed1-3966951 | sle_hc0 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-3970782 | sle_hc0 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-3979294 | sle_hc0 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3987964 | sle_hc2 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-4024927 | sle_st_b_v1 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3951031 | sle_st_b_v2 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc2__cl6bcaba89-4049393 | slw_hc2 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-4062944 | slw_hc3 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-4102152 | slw_st_b_v1 | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4111701 | slw_st_b_v1 | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4115743 | slw_st_b_v2 | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v2__pvc2ec5bfb-4120782 | slw_st_b_v2 | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 29.8 | drt_violations best 17065 last 17065 rows 13 | before-window best 28844, window best 17065 | PROGRESS: drt_violations improved 40.8 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 23.1 | drt_violations best 27940 last 27940 rows 12 | before-window best 40914, window best 27940 | PROGRESS: drt_violations improved 31.7 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | 5_1_grt | 3.9 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-2333813 | slw_sc_v1 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 37.2 | drt_violations best 48746 last 160916 rows 18 | before-window best 48746, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_st_b_v2__clfde1249e-2879520 | sle_st_b_v2 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3249798 | slw_hc3 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l0_wfb17da-849937 | qfd_qc_su_lane_w_l0_wfb17da | 4_1_cts | 1.5 | repair_TNS best 0 last 0 rows 240 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l1_w460927-787688 | qfd_qc_su_lane_w_l1_w460927 | 4_1_cts | 1.5 | repair_TNS best 0 last 0 rows 227 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l6_wb51d05-853896 | qfd_qc_su_lane_w_l6_wb51d05 | 4_1_cts | 1.5 | repair_Violations best 0 last 0 rows 9 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l7_wd4f14d-862251 | qfd_qc_su_lane_w_l7_wd4f14d | 4_1_cts | 1.5 | repair_TNS best 0 last 0 rows 193 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-1446982 | slw_st_b_v2 | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 37.4 | drt_violations best 74496 last 74496 rows 15 | before-window best 76746, window best 74496 | PROGRESS: drt_violations improved 2.9 % in window |  |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 15.4 | last meaningful line 4.6 h ago (107/107 lines) | PROGRESS: log still growing |  |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 19.2 | last meaningful line 4.6 h ago (107/107 lines) | PROGRESS: log still growing |  |
