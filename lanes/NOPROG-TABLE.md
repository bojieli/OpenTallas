# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 07:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'GRT-LABEL': 2, 'YOUNG': 78, 'NO-DATA': 7, 'EXCLUDED': 1, 'PROGRESS': 33}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair_grt | 13.6 | repair_Violations best 0 last 0 rows 93 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -743.27 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | tt_setup_repair_grt | 13.3 | repair_Violations best 0 last 0 rows 62 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -773.59 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 5_1_grt | 13.5 | grt rounds 2 overflow 5:13977 -> 10:10981 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | 5_1_grt | 6.8 | grt rounds 2 overflow 5:25842 -> 10:3973 | GRT-LABEL: DESIGN-FAIL: overflow 3973 at round 10 > 1000 |  |
| epyc10 | dpkit-coll_ft__cla4a25d77-1296583 | coll_ft | 5_3_fillcell | 2.2 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-2159263 | slw_hc1 | pregrt_ff_hold | 1.5 | repair_TNS best 22856.8 last 22856.8 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (7159/7159 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v7-2608982 | kv3_hgi_v7 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (6522/6522 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v8-2448463 | kv3_hgi_v8 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (5186/5186 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-kv3_io_cor_v1-2455343 | kv3_io_cor_v1 | 5_1_grt | 1.0 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v5ne-2612763 | kv3_pv_v5ne | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (8587/8587 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pve-2456771 | kv3_pve | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (10873/10873 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_sys_c-2605096 | kv3_sys_c | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (5368/5368 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_sys_c-3236960 | kv3_sys_c | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 3.1 | drt_violations best 112571 last 112571 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_1_grt | 3.0 | last meaningful line 0.3 h ago (1291/1940 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-1186805 | sle_sc_v3 | 5_1_grt | 2.0 | last meaningful line 0.2 h ago (245/1255 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l0__cl7a55c676-4027948 | sle_su_l0 | 5_2_route | 2.9 | last meaningful line 0.1 h ago (255/256 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l0__cl1a1c1f8f-4150554 | slw_su_l0 | 5_2_route | 2.9 | last meaningful line 0.0 h ago (255/256 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i3t-1317564 | eco_20261123_103136_2028090-i3t | 5_2_route | 1.9 | last meaningful line 0.2 h ago (282/283 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | so_3706423_ff_34466 | so_3706423_ff_34466 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | so_3706423_tt_34466 | so_3706423_tt_34466 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-coll_ft__cla4a25d77-3263737 | coll_ft | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (94/94 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-coll_n-3172293 | coll_n | 2_4_floorplan_pdn | 0.1 | last meaningful line -0.0 h ago (9/9 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-2448802 | hd_lep0N_w | 3_3_place_gp | 0.4 | overflow best 0.5818 last 0.5818 rows 17 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N_w-995501 | hd_lep0N_w | 5_2_route | 3.5 | drt_violations best 90953 last 90953 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_fw_v1__clf58b4dfb-3165565 | sle_fw_v1 | 2_1_floorplan | 0.1 | last meaningful line -0.0 h ago (9/9 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 8.1 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | postcts_gate_TT | 4.3 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl67389ecd-2555735 | sle_st_a_v1 | postcts_gate_FF | 2.6 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-2595387 | sle_st_a_v1 | postcts_gate_FF | 2.6 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v1__pv0e7b1dcc-2157611 | sle_st_b_v1 | pregrt_ff_hold | 2.8 | repair_TNS best 22304.1 last 22304.1 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3262037 | sle_st_b_v1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (157/157 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3272378 | sle_st_b_v2 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | 5_2_route | 8.2 | last meaningful line 0.2 h ago (284/285 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-3494601 | sle_stm_v3 | 5_2_route | 4.7 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | postcts_gate_TT | 8.5 | last meaningful line 0.2 h ago (397/397 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 8.3 | last meaningful line 0.5 h ago (281/282 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | postcts_gate_TT | 4.4 | last meaningful line 0.0 h ago (2064/2064 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-2594734 | slw_st_a_v1 | postcts_gate_TT | 2.6 | last meaningful line 0.1 h ago (514/514 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2581554 | slw_st_a_v1 | postcts_gate_TT | 2.6 | last meaningful line 0.1 h ago (521/521 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v2__clf4365a62-2648278 | slw_st_a_v2 | postcts_gate_FF | 2.6 | last meaningful line 0.0 h ago (466/466 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-3162191 | slw_st_b_v1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (310/310 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | 5_2_route | 8.5 | last meaningful line 0.4 h ago (277/278 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | pregrt_ff_hold | 2.8 | repair_TNS best 20875.5 last 20875.5 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | otc-3312012-17262 | 3312012 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261124_145005_2036075-i1-1498701 | eco_20261124_145005_2036075-i1 | 5_2_route | 0.9 | last meaningful line 0.1 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-fin-4134013 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (1068/1068 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | tt_setup_repair_grt | 13.2 | repair_Violations best 5 last 8 rows 64 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i2-2385296 | eco_20261123_164145_1995767-i2 | 5_2_route | 2.0 | last meaningful line 0.2 h ago (297/298 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_sc_v1__cl63e5a7a2-3279007 | slw_sc_v1 | 5_1_grt | 2.9 | last meaningful line 0.2 h ago (266/1276 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | eco-abs-3097968 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l0_wfb17da-849937 | qfd_qc_su_lane_w_l0_wfb17da | 5_1_grt | 1.8 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l1_w460927-787688 | qfd_qc_su_lane_w_l1_w460927 | 5_1_grt | 1.8 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l4_w285325-818329 | qfd_qc_su_lane_w_l4_w285325 | 5_1_grt | 1.8 | last meaningful line 0.0 h ago (178/181 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l5_wf949e1-824935 | qfd_qc_su_lane_w_l5_wf949e1 | lec | 1.8 | LEC last write 0.0 h ago | YOUNG: evidence 1.8 h < 6 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l6_wb51d05-853896 | qfd_qc_su_lane_w_l6_wb51d05 | 5_1_grt | 1.8 | last meaningful line 0.1 h ago (135/135 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l7_wd4f14d-862251 | qfd_qc_su_lane_w_l7_wd4f14d | 5_1_grt | 1.7 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-1814577-31530 | 1814577 | - | 1.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-1939028-17446 | 1939028 | gold_b.ys | 1.1 | last meaningful line 0.7 h ago (84693/84693 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | otc-2103773-27089 | 2103773 | gold_b.ys | 1.0 | last meaningful line 0.7 h ago (67868/67868 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | otc-2468382-9194 | 2468382 | gate.ys | 0.7 | last meaningful line 0.5 h ago (22052/22052 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i3-368978 | eco_20261123_190031_3093983-i3 | 5_2_route | 2.1 | last meaningful line 0.1 h ago (284/285 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i2-1242463 | eco_20261124_010152_2867084-i2 | 5_1_grt | 1.5 | last meaningful line 1.0 h ago (242/1579 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | so_2550577_ff_66664 | so_2550577_ff_66664 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (695/695 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | so_2550577_tt_66664 | so_2550577_tt_66664 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (695/695 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12e-36378 | kv3_pv_v12e | 4_1_cts | 0.4 | last meaningful line 0.2 h ago (12029/12029 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3ne-3760907 | kv3_pv_v3ne | 4_1_cts | 0.8 | last meaningful line 0.3 h ago (9643/9643 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v8-3837707 | kv3_pv_v8 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (9124/9124 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v8e-3858104 | kv3_pv_v8e | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (10300/10300 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-native59-1320092 | native59 | pregrt_ff_hold | 3.0 | repair_TNS best 5962.38 last 5962.38 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 4_1_cts | 3.0 | last meaningful line 0.2 h ago (6010/6010 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-sle_hc1__cl7d360508__pv97423966-1341249 | sle_hc1 | 4_1_cts | 3.0 | last meaningful line 0.1 h ago (5908/5908 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-1345836 | sle_hc2 | 4_1_cts | 3.0 | last meaningful line 0.2 h ago (5099/5099 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1365381 | sle_st_b_v1 | pregrt_ff_hold | 2.9 | repair_TNS best 19705 last 19705 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | postcts_gate_TT | 1.0 | last meaningful line 0.2 h ago (796/796 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 4_1_cts | 2.9 | last meaningful line 0.1 h ago (5929/5929 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1387403 | slw_hc0 | 4_1_cts | 2.9 | last meaningful line 0.2 h ago (5360/5360 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-slw_hc1__cl3449ea95-1389354 | slw_hc1 | 4_1_cts | 2.9 | last meaningful line 0.1 h ago (5824/5824 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-1401912 | slw_hc2 | 4_1_cts | 2.9 | last meaningful line 0.2 h ago (5109/5109 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | eco-abs-3571988 | eco-abs | generate_abstract | 1.0 | last meaningful line 0.1 h ago (873/873 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | otc-1670752-16443 | 1670752 | - | 7.0 |  | NO-DATA: no log found |  |
| intel1 | otc-1797391-24144 | 1797391 | flow3 | 2.6 | last meaningful line 2.3 h ago (208/209 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | otc-3818878-18115 | 3818878 | - | 0.8 |  | NO-DATA: no log found |  |
| intel1 | otc-3854277-21865 | 3854277 | - | 0.7 |  | NO-DATA: no log found |  |
| intel2 | dpkit-kv3_pv_v1-152951 | kv3_pv_v1 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v2-351905 | kv3_pv_v2 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v7-122568 | kv3_pv_v7 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 6.9 | drt_violations best 8 last 16 rows 31 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc9 | otc-3420116-22717 | 3420116 | - | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-2082988 | slw_hc3 | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 34.8 | drt_violations best 779 last 1212 rows 39 | before-window best 954, window best 779 | PROGRESS: drt_violations improved 18.3 % in window |  |
| epyc2 | dpkit-kv3_hgi_v2__cl2862d491-2611569 | kv3_hgi_v2 | pregrt_ff_hold | 0.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc0__cl05696ed1-3966951 | sle_hc0 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-3970782 | sle_hc0 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-3979294 | sle_hc0 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3987964 | sle_hc2 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-4024927 | sle_st_b_v1 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3951031 | sle_st_b_v2 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc2__cl6bcaba89-4049393 | slw_hc2 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-4062944 | slw_hc3 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-4102152 | slw_st_b_v1 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4111701 | slw_st_b_v1 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4115743 | slw_st_b_v2 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v2__pvc2ec5bfb-4120782 | slw_st_b_v2 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 30.1 | drt_violations best 17065 last 17065 rows 13 | before-window best 28844, window best 17065 | PROGRESS: drt_violations improved 40.8 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 23.4 | drt_violations best 27940 last 27940 rows 12 | before-window best 40914, window best 27940 | PROGRESS: drt_violations improved 31.7 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | 5_1_grt | 4.1 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-2333813 | slw_sc_v1 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | 5_1_grt | 4.5 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 37.4 | drt_violations best 48746 last 160916 rows 18 | before-window best 48746, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | prd-eco_20261123_120225_75582-i3t-3968210 | eco_20261123_120225_75582-i3t | 5_2_route | 6.9 | drt_violations best 11 last 124 rows 42 | before-window best 36109, window best 11 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-sle_st_b_v2__clfde1249e-2879520 | sle_st_b_v2 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3249798 | slw_hc3 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1439197 | slw_st_b_v1 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-1446982 | slw_st_b_v2 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 37.6 | drt_violations best 74496 last 74496 rows 15 | before-window best 76746, window best 74496 | PROGRESS: drt_violations improved 2.9 % in window |  |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 15.7 | last meaningful line 4.9 h ago (107/107 lines) | PROGRESS: log still growing |  |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 19.4 | last meaningful line 4.9 h ago (107/107 lines) | PROGRESS: log still growing |  |
