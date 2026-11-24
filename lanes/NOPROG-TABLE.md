# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 07:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'GRT-LABEL': 1, 'YOUNG': 94, 'NO-DATA': 5, 'EXCLUDED': 2, 'PROGRESS': 36}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair_grt | 13.1 | repair_Violations best 0 last 0 rows 93 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -743.27 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | tt_setup_repair_grt | 12.8 | repair_Violations best 0 last 0 rows 62 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -773.59 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 5_1_grt | 13.0 | grt rounds 2 overflow 5:13977 -> 10:10981 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_ft__cl78c7b300-1240042 | coll_ft | 5_2_route | 1.7 | drt_violations best 11693 last 11693 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-coll_ft__cla4a25d77-1296583 | coll_ft | 5_2_route | 1.7 | last meaningful line 0.0 h ago (237/238 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-hd_spn-2761182 | hd_spn | 3_3_place_gp | 0.5 | overflow best 0.0994 last 0.0994 rows 46 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-hd_st_n4-2760809 | hd_st_n4 | 3_3_place_gp | 0.5 | overflow best 0.0992 last 0.0992 rows 45 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2032997 | sle_hc0 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (5795/5795 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-1908980 | sle_hc2 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (5479/5479 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-2356638 | sle_st_b_v2 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (5843/5843 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-2226501 | slw_fw_v2 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (4920/4920 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2106973 | slw_hc1 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (5850/5850 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-2159263 | slw_hc1 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (5515/5515 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2142862 | slw_hc3 | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (5134/5134 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | otc-3078354-19227 | 3078354 | asbuilt.yosys | 0.3 | last meaningful line 0.3 h ago (369/369 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-hd_st_n4-4161241 | hd_st_n4 | 5_2_route | 2.4 | drt_violations best 20361 last 20361 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1p5-2606530 | kv3_hg_v1p5 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (103/103 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v2__cl2862d491-2611569 | kv3_hgi_v2 | tt_setup_repair | 0.3 | last meaningful line 0.0 h ago (172/172 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v7-2608982 | kv3_hgi_v7 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (6411/6411 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v8-2448463 | kv3_hgi_v8 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5079/5079 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_io_cor_v1-2455343 | kv3_io_cor_v1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3668/3668 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v5ne-2612763 | kv3_pv_v5ne | 4_1_cts | 0.3 | last meaningful line 0.2 h ago (8149/8149 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pve-2456771 | kv3_pve | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (10781/10781 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_sys_c-2605096 | kv3_sys_c | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5221/5221 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 2.6 | drt_violations best 112571 last 112571 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | 5_1_grt | 6.3 | last meaningful line 0.7 h ago (294/1304 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-1186805 | sle_sc_v3 | pregrt_ff_hold | 1.5 | last meaningful line 0.0 h ago (64/64 lines) | YOUNG: evidence 0.7 h < 2.5 h |  |
| epyc2 | dpkit-sle_su_l0__cl7a55c676-4027948 | sle_su_l0 | 5_2_route | 2.4 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l0__cl1a1c1f8f-4150554 | slw_su_l0 | 5_2_route | 2.4 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i3t-1317564 | eco_20261123_103136_2028090-i3t | 5_2_route | 1.4 | last meaningful line 0.1 h ago (277/277 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-995501 | hd_lep0N_w | 5_2_route | 3.0 | last meaningful line 0.2 h ago (254/255 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_2_route | 7.6 | last meaningful line 0.5 h ago (263/264 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | 5_1_grt | 3.8 | last meaningful line 0.3 h ago (2021/2038 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-2492812 | sle_st_a_v1 | 5_1_grt | 2.1 | last meaningful line 0.1 h ago (2078/2095 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-2355490 | sle_st_a_v2 | postcts_gate_TT | 2.2 | last meaningful line 0.0 h ago (945/945 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-2354216 | sle_st_a_v2 | postcts_gate_TT | 2.2 | last meaningful line -0.0 h ago (7598/7598 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv4242de79-2374002 | sle_st_a_v2 | postcts_gate_TT | 2.2 | last meaningful line 0.1 h ago (968/968 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v1__pv0e7b1dcc-2157611 | sle_st_b_v1 | tt_setup_repair | 2.3 | last meaningful line 0.0 h ago (487/487 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | 5_2_route | 7.7 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | 5_1_grt | 3.6 | repair_Remaining best 236366 last 236366 rows 168 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-sle_stm_v3-3494601 | sle_stm_v3 | 5_2_route | 4.2 | last meaningful line 0.1 h ago (261/262 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | postcts_gate_TT | 8.0 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 7.8 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | tt_setup_measure_grt | 3.9 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clb036e152-2495581 | slw_st_a_v1 | 5_1_grt | 2.1 | last meaningful line 0.0 h ago (2148/2165 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-2594734 | slw_st_a_v1 | 5_1_grt | 2.1 | last meaningful line 0.1 h ago (2065/2082 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2581554 | slw_st_a_v1 | 5_1_grt | 2.1 | last meaningful line 0.1 h ago (2069/2086 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v2__clf4365a62-2648278 | slw_st_a_v2 | postcts_gate_FF | 2.1 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | 5_2_route | 8.0 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | tt_setup_repair | 2.3 | last meaningful line 0.0 h ago (418/419 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | 5_1_grt | 4.0 | last meaningful line 0.1 h ago (282/348 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-count-p1_tc-4134013 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | tt_setup_repair_grt | 12.7 | repair_Violations best 5 last 8 rows 64 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc8 | dpkit-coll_ft__cl78c7b300-2577534 | coll_ft | generate_abstract | 1.4 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-330317 | slw_st_a_v2 | postcts_gate_TT | 2.0 | last meaningful line -0.0 h ago (29632/29632 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i3t-3968210 | eco_20261123_120225_75582-i3t | 5_2_route | 6.4 | drt_violations best 11 last 125 rows 41 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i2-2385296 | eco_20261123_164145_1995767-i2 | 5_2_route | 1.5 | last meaningful line 0.1 h ago (287/288 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_sc_v1__cl63e5a7a2-3279007 | slw_sc_v1 | 5_1_grt | 2.4 | last meaningful line 0.0 h ago (143/143 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l0_wfb17da-849937-lec | qfd_qc_su_lane_w_l0_wfb17da | lec | 1.2 | LEC last write -0.0 h ago | YOUNG: evidence 1.2 h < 6 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l1_w460927-787688-lec | qfd_qc_su_lane_w_l1_w460927 | lec | 1.3 | LEC last write -0.0 h ago | YOUNG: evidence 1.3 h < 6 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l4_w285325-818329-lec | qfd_qc_su_lane_w_l4_w285325 | lec | 1.3 | LEC last write -0.0 h ago | YOUNG: evidence 1.3 h < 6 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l5_wf949e1-824935-lec | qfd_qc_su_lane_w_l5_wf949e1 | lec | 1.3 | LEC last write -0.0 h ago | YOUNG: evidence 1.3 h < 6 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l6_wb51d05-853896-lec | qfd_qc_su_lane_w_l6_wb51d05 | lec | 1.2 | LEC last write -0.0 h ago | YOUNG: evidence 1.2 h < 6 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l7_wd4f14d-862251-lec | qfd_qc_su_lane_w_l7_wd4f14d | lec | 1.2 | LEC last write 0.0 h ago | YOUNG: evidence 1.2 h < 6 h |  |
| epyc9 | otc-1814577-31530 | 1814577 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-1871258-8946 | 1871258 | asbuilt.yosys | 0.6 | last meaningful line 0.1 h ago (241095/241095 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | otc-1939028-17446 | 1939028 | gold_b.ys | 0.6 | last meaningful line 0.2 h ago (84693/84693 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | otc-2040757-2457 | 2040757 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc9 | otc-2103773-27089 | 2103773 | gold_b.ys | 0.5 | last meaningful line 0.2 h ago (67868/67868 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | otc-2468382-9194 | 2468382 | gate.ys | 0.2 | last meaningful line 0.2 h ago (22052/22052 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i3-368978 | eco_20261123_190031_3093983-i3 | 5_2_route | 1.6 | last meaningful line 0.1 h ago (279/279 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i2-1242463 | eco_20261124_010152_2867084-i2 | 5_1_grt | 1.0 | last meaningful line 0.5 h ago (242/1536 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | prd-fin-2527977 | fin | 6_report | 0.3 | last meaningful line 0.0 h ago (1068/1068 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | so_2550577_ff_66664 | so_2550577_ff_66664 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (695/695 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | so_2550577_tt_66664 | so_2550577_tt_66664 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (695/695 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3ne-3760907 | kv3_pv_v3ne | 4_1_cts | 0.3 | last meaningful line 0.2 h ago (9228/9228 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v8-3837707 | kv3_pv_v8 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (8990/8991 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v8e-3858104 | kv3_pv_v8e | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (10167/10167 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-native59-1320092 | native59 | pregrt_ff_hold | 2.5 | repair_TNS best 5962.38 last 5962.38 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 4_1_cts | 2.5 | last meaningful line 0.1 h ago (5983/5983 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-sle_hc1__cl7d360508__pv97423966-1341249 | sle_hc1 | 4_1_cts | 2.5 | last meaningful line 0.3 h ago (5859/5859 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-1345836 | sle_hc2 | 4_1_cts | 2.5 | last meaningful line 0.2 h ago (5094/5094 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1365381 | sle_st_b_v1 | 4_1_cts | 2.4 | last meaningful line 0.2 h ago (5618/5618 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-3548172 | slw_fe_v2 | postcts_gate_FF | 0.5 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 4_1_cts | 2.4 | last meaningful line 0.2 h ago (5900/5900 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1387403 | slw_hc0 | 4_1_cts | 2.4 | last meaningful line 0.0 h ago (5333/5333 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc1__cl3449ea95-1389354 | slw_hc1 | 4_1_cts | 2.4 | last meaningful line 0.2 h ago (5774/5774 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-1401912 | slw_hc2 | 4_1_cts | 2.4 | last meaningful line 0.0 h ago (5107/5107 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1439197 | slw_st_b_v1 | pregrt_ff_hold | 2.4 | repair_TNS best 20547.1 last 20547.1 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-1446982 | slw_st_b_v2 | pregrt_ff_hold | 2.4 | repair_TNS best 15780.3 last 15780.3 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | pregrt_ff_hold | 2.4 | repair_TNS best 14328.4 last 14328.4 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | eco-abs-3571988 | eco-abs | generate_abstract | 0.5 | last meaningful line 0.3 h ago (869/869 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | otc-1670752-16443 | 1670752 | - | 6.5 |  | NO-DATA: no log found |  |
| intel1 | otc-1797391-24144 | 1797391 | flow3 | 2.1 | last meaningful line 1.7 h ago (208/209 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | otc-3818878-18115 | 3818878 | - | 0.3 |  | NO-DATA: no log found |  |
| intel1 | otc-3854277-21865 | 3854277 | - | 0.2 |  | NO-DATA: no log found |  |
| intel2 | dpkit-coll_ftm-1873477 | coll_ftm | 5_2_route | 2.0 | drt_violations best 10288 last 10288 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pc_v1__cl23f6a148-151203 | kv3_pc_v1 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.0 h ago (57/57 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v1-152951 | kv3_pv_v1 | 3_3_place_gp | 0.5 | overflow best 0.5123 last 0.5246 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-kv3_pv_v2-351905 | kv3_pv_v2 | 3_2_place_iop | 0.3 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v7-122568 | kv3_pv_v7 | 3_3_place_gp | 0.5 | overflow best 0.5335 last 0.5335 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 6.4 | drt_violations best 13 last 13 rows 22 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc9 | otc-2234223-27205 | 2234223 | - | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | otc-2292915-30071 | 2292915 | - | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-2082988 | slw_hc3 | tt_setup_repair | 1.1 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 34.3 | drt_violations best 779 last 1386 rows 38 | before-window best 954, window best 779 | PROGRESS: drt_violations improved 18.3 % in window |  |
| epyc2 | dpkit-sle_hc0__cl05696ed1-3966951 | sle_hc0 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-3970782 | sle_hc0 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-3979294 | sle_hc0 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3987964 | sle_hc2 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 5_1_grt | 2.5 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-4024927 | sle_st_b_v1 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3951031 | sle_st_b_v2 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc2__cl6bcaba89-4049393 | slw_hc2 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-4062944 | slw_hc3 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-4102152 | slw_st_b_v1 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4111701 | slw_st_b_v1 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4115743 | slw_st_b_v2 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v2__pvc2ec5bfb-4120782 | slw_st_b_v2 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 29.6 | drt_violations best 17065 last 17065 rows 13 | before-window best 28844, window best 17065 | PROGRESS: drt_violations improved 40.8 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 22.9 | drt_violations best 27940 last 27940 rows 12 | before-window best 42803, window best 27940 | PROGRESS: drt_violations improved 34.7 % in window |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_st_a_v1__cl67389ecd-2555735 | sle_st_a_v1 | 5_1_grt | 2.1 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-2595387 | sle_st_a_v1 | 5_1_grt | 2.1 | repair_TNS best 0 last 0 rows 10 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-2333813 | slw_sc_v1 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 36.9 | drt_violations best 48746 last 160916 rows 18 | before-window best 48746, window best - | PROGRESS: no new drt_violations row, but other log lines are new |  |
| epyc7 | prd-eco_20261124_145005_2036075-i1-1498701 | eco_20261124_145005_2036075-i1 | 5_1_grt | 0.4 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_st_b_v2__clfde1249e-2879520 | sle_st_b_v2 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3249798 | slw_hc3 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l0_wfb17da-849937 | qfd_qc_su_lane_w_l0_wfb17da | 4_1_cts | 1.3 | repair_TNS best 0 last 0 rows 94 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l1_w460927-787688 | qfd_qc_su_lane_w_l1_w460927 | 4_1_cts | 1.3 | repair_TNS best 0 last 0 rows 71 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l4_w285325-818329 | qfd_qc_su_lane_w_l4_w285325 | 4_1_cts | 1.3 | repair_TNS best 0 last 0 rows 140 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l5_wf949e1-824935 | qfd_qc_su_lane_w_l5_wf949e1 | 4_1_cts | 1.3 | repair_TNS best 0 last 0 rows 134 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l6_wb51d05-853896 | qfd_qc_su_lane_w_l6_wb51d05 | 4_1_cts | 1.3 | repair_TNS best 0 last 0 rows 127 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l7_wd4f14d-862251 | qfd_qc_su_lane_w_l7_wd4f14d | 4_1_cts | 1.2 | repair_TNS best 0 last 0 rows 49 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 37.1 | drt_violations best 74496 last 74496 rows 15 | before-window best 76746, window best 74496 | PROGRESS: drt_violations improved 2.9 % in window |  |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 15.2 | last meaningful line 4.4 h ago (107/107 lines) | PROGRESS: log still growing |  |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 18.9 | last meaningful line 4.4 h ago (107/107 lines) | PROGRESS: log still growing |  |
