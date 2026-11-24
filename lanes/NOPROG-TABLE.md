# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 21:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'UNSIGNABLE': 2, 'GRT-LABEL': 3, 'YOUNG': 82, 'NO-DATA': 10, 'PROGRESS': 16}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (OPUS-FIX-QC-V4-R2 decid |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 29.5 | drt_violations best 8261 last 12332 rows 19 | before-window best 8281, window best 8261 | NO-PROGRESS: drt_violations best 8261 vs 8281 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc8 | dpkit-cbn_q01__clab6e67f2-1043557 | cbn_q01 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (OPUS-FIX-QC-V4-R2 decid |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | tt_setup_repair_grt | 21.7 | repair_Viol best 2799 last 2799 rows 26 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -885.79 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | prd-eco-i3t-51485 | eco-i3t | 5_2_route | 3.7 | drt_violations best 0 last 0 rows 4 | UNSIGNABLE: ECO-FLAT: TT setup -104.66 -> -132.71 ps (gate -42); FF hold -1.83 -> -1.83 ps ( | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc2 | dpkit-cbf_q00__cl870de686-181856 | cbf_q00 | 5_1_grt | 3.4 | grt rounds 2 overflow 5:4939 -> 10:4225 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-3883814 | cbn_q11 | 5_1_grt | 3.8 | grt rounds 1 overflow 5:166101 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | 5_1_grt | 22.8 | grt rounds 2 overflow 5:13730 -> 10:13037 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-3938823 | dsdv_slice_lepw_mu_LP__t2 | 3_3_place_gp | 0.4 | overflow best 0.7301 last 0.7317 rows 11 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3279433 | sle_st_b_v2 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (65/65 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t24__cl64811a5d-226587 | slice_station__t24 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (1946/1946 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t25-3822510 | slice_station__t25 | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (271/271 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t30__cl6a190133-140494 | slice_station__t30 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (71/71 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t7__cl362204c4-174378 | slice_station__t7 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t8-64059 | slice_station__t8 | 3_3_place_gp | 0.2 | overflow best 0.3442 last 0.3465 rows 24 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-2978404 | slw_hc1 | 3_3_place_gp | 0.8 | overflow best 0.0999 last 0.0999 rows 258 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | otc-280835-32015 | 280835 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | so_67550_ff_73206 | so_67550_ff_73206 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | so_67550_tt_73206 | so_67550_tt_73206 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-cbx_q10__cl89936551_h-2205260 | cbx_q10 | pregrt_ff_hold | 1.5 | repair_TNS best 128.103 last 128.103 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2194343 | cbx_q10 | pregrt_ff_hold | 1.5 | repair_TNS best 137.274 last 137.274 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 3.2 | last meaningful line 2.5 h ago (13035/13035 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-3302313 | sle_hc0 | 3_3_place_gp | 0.6 | overflow best 0.0991 last 0.0991 rows 52 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3431075 | sle_hc2 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-3632152 | sle_sc_v1 | 3_3_place_gp | 0.5 | overflow best 0.3442 last 0.3442 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-3657868 | sle_st_b_v1 | 3_3_place_gp | 0.4 | overflow best 0.5318 last 0.5334 rows 29 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-slice_station__t24__cl66b71008-4162798 | slice_station__t24 | 3_4_place_resized | 0.1 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc2__cl6bcaba89-3452494 | slw_hc2 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3401594 | slw_hc3 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i2t-3790618 | eco_20261123_102841_2122262-i2t | 5_1_grt | 0.4 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i2t-2487500 | eco_20261123_103136_2028090-i2t | 5_2_route | 1.2 | last meaningful line 0.0 h ago (269/269 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | so_74475_ff_76873 | so_74475_ff_76873 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | so_74475_tt_76873 | so_74475_tt_76873 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 13.4 | drt_violations best 95242 last 95242 rows 3 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-2781664 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 5.6 | last meaningful line 3.3 h ago (37/37 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-1324433 | hd_lep0N | 4_2_tapbal_grt | 2.9 | last meaningful line 1.3 h ago (48/55 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2158649 | hd_lep0N | 4_2_tapbal_grt | 1.9 | last meaningful line 0.8 h ago (48/50 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2864139 | hd_lep0N | 4_2_tapbal_grt | 1.2 | last meaningful line 0.1 h ago (48/49 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-3258726 | hd_lep0N_w | 5_2_route | 0.9 | last meaningful line 0.1 h ago (258/259 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3500860 | sle_sc_v1 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v1__pv0e7b1dcc-3612319 | sle_st_b_v1 | 3_3_place_gp | 0.7 | overflow best 0.3186 last 0.3186 rows 36 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-slice_station__t22-4072498 | slice_station__t22 | 3_3_place_gp | 0.3 | overflow best 0.1991 last 0.1991 rows 43 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3550640 | slw_sc_v1 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3492600 | slw_sc_v1 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3544661 | slw_stm_v2 | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (379/379 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | eco-abs-3503634 | eco-abs | generate_abstract | 0.8 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | nostalgic_satoshi | nostalgic_satoshi | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (104/104 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795467809896538497-i1t-60038 | eco_retry_1795467809896538497-i1t | 5_2_route | 8.6 | drt_violations best 105749 last 105749 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-coll-core-grt-1217751 | coll-core-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q01_s2-3852085 | cbf_q01_s2 | 5_1_grt | 4.2 | last meaningful line 0.2 h ago (268/1272 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-cbx_q10__cl89936551-1293593 | cbx_q10 | pregrt_ff_hold | 1.8 | repair_TNS best 900991 last 900991 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | 5_1_grt | 18.3 | last meaningful line 2.0 h ago (307/1316 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p5-206562 | kv3_hg_v1p5 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (6734/6734 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-197119 | sle_ctl | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (10788/10788 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v1__cl67389ecd-892590 | sle_st_a_v1 | postcts_gate_TT | 2.0 | last meaningful line 0.1 h ago (29/29 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-848919 | sle_st_a_v1 | postcts_gate_TT | 2.0 | last meaningful line 0.0 h ago (543/543 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-4038462 | sle_st_a_v1 | postcts_gate_FF | 2.4 | last meaningful line 0.0 h ago (1006/1006 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-1287720 | slw_fe_v2 | 4_1_cts | 1.8 | last meaningful line 0.2 h ago (8315/8315 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl1bc59e1c-85806 | slw_hc0 | pregrt_ff_hold | 2.3 | repair_TNS best 5984.52 last 5984.52 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slw_st_a_v1__clb036e152-920083 | slw_st_a_v1 | postcts_gate_TT | 2.0 | last meaningful line 0.0 h ago (553/553 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-975156 | slw_st_a_v1 | postcts_gate_TT | 2.0 | last meaningful line 0.0 h ago (993/993 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-4164052 | slw_st_a_v2 | postcts_gate_FF | 2.3 | last meaningful line 0.0 h ago (964/964 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-3737398 | slw_su_l1 | tt_setup_repair_grt | 2.5 | repair_Violations best 12 last 16 rows 55 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | eco-abs-1471297 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i2-3929535 | eco_20261123_120225_75582-i2 | 5_2_route | 0.8 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i2-382519 | eco_20261123_163717_2005956-i2 | 5_2_route | 2.2 | drt_violations best 17262 last 17262 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1-1021701 | eco_20261123_164145_1995767-i1 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (197/197 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | relec1122-ml-r6_afda1e9d | relec1122-ml-r6_afda1e9d | - | 5.6 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-sle_st_b_v2__clfde1249e-3058067 | sle_st_b_v2 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_sc_v1__cl63e5a7a2-3029036 | slw_sc_v1 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-2068133-23421 | 2068133 | - | 1.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-3735048-19624 | 3735048 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-3853150-11828 | 3853150 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261123_190031_3093983-i2t-1439699 | eco_20261123_190031_3093983-i2t | 5_2_route | 2.4 | drt_violations best 537 last 537 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i1-456858 | eco_20261123_224216_149959-i1 | 5_2_route | 3.3 | drt_violations best 693 last 693 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i1-914398 | eco_20261123_224647_4153453-i1 | 5_2_route | 2.9 | drt_violations best 57 last 57 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i1-3056982 | eco_20261124_010152_2867084-i1 | 5_1_grt | 0.7 | last meaningful line 0.4 h ago (242/1553 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_041946_4081528-i1-2378518 | eco_20261124_041946_4081528-i1 | 5_2_route | 1.4 | last meaningful line 0.0 h ago (262/263 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | relec1122-ml-r6_00112d4e | relec1122-ml-r6_00112d4e | - | 5.6 |  | NO-DATA: no log found |  |
| intel1 | dpkit-native59-2248842 | native59 | 2_1_floorplan | 0.4 | last meaningful line 0.0 h ago (1359/1359 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1670658 | sle_fe_v1 | 3_3_place_gp | 0.8 | overflow best 0.2021 last 0.2021 rows 36 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-sle_hc1__cl7d360508__pv97423966-1517328 | sle_hc1 | 3_3_place_gp | 0.8 | overflow best 0.2995 last 0.3994 rows 210 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-1646542 | sle_hc2 | 3_5_place_dp | 0.8 | last meaningful line 0.1 h ago (113/113 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1860359 | sle_st_b_v1 | 3_3_place_gp | 0.7 | overflow best 0.2138 last 0.2138 rows 40 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-slice_station__t29__cl2e5c855a-2514057 | slice_station__t29 | 3_4_place_resized | 0.3 | repair_Remaining best 84184 last 84184 rows 5 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-slice_station__t29__clc7772371-2600129 | slice_station__t29 | 3_3_place_gp | 0.2 | overflow best 0.2724 last 0.2724 rows 43 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-2493862 | slice_station__t40 | 3_4_place_resized | 0.3 | last meaningful line 0.0 h ago (179/179 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t51-2514527 | slice_station__t51 | 3_3_place_gp | 0.3 | overflow best 0.2454 last 0.256 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_hc1__cl3449ea95-1637128 | slw_hc1 | 3_5_place_dp | 0.8 | last meaningful line 0.1 h ago (113/113 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1860873 | slw_st_b_v1 | 3_3_place_gp | 0.7 | overflow best 0.2103 last 0.2103 rows 40 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1785954 | slw_stm_v1 | 3_3_place_gp | 0.7 | overflow best 0.1207 last 0.1207 rows 42 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 10.1 | last meaningful line 5.5 h ago (5/5 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 5.7 | last meaningful line 5.5 h ago (5/5 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | otc-1882360-28079 | 1882360 | - | 5.2 |  | NO-DATA: no log found |  |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 9.4 | last meaningful line 5.5 h ago (5/5 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | otc-2635241-3041 | 2635241 | - | 0.2 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261123_191853_2879776-i1t-119447 | eco_20261123_191853_2879776-i1t | 5_2_route | 2.4 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-2729761 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2t-2973514 | eco_20261123_063813_234645-i2t | 5_2_route | 5.5 | drt_violations best 6 last 20 rows 27 | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel2 | prd-fin-245032 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (1067/1067 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 24.8 | drt_violations best 2455 last 2455 rows 21 | before-window best 11282, window best 2455 | PROGRESS: drt_violations improved 78.2 % in window |  |
| epyc2 | dpkit-cbf_q11-2451203 | cbf_q11 | pregrt_ff_hold | 1.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 27.3 | drt_violations best 1617 last 7736 rows 26 | before-window best 1743, window best 1617 | PROGRESS: drt_violations improved 7.2 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 26.1 | drt_violations best 39818 last 39818 rows 16 | before-window best 41866, window best 39818 | PROGRESS: drt_violations improved 4.9 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 26.5 | drt_violations best 47053 last 47053 rows 16 | before-window best 48840, window best 47053 | PROGRESS: drt_violations improved 3.7 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 20.1 | drt_violations best 49689 last 49689 rows 4 | before-window best 681573, window best 49689 | PROGRESS: drt_violations improved 92.7 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 27.4 | drt_violations best 49778 last 49778 rows 16 | before-window best 54432, window best 49778 | PROGRESS: drt_violations improved 8.6 % in window |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 54.7 | last meaningful line 3.8 h ago (646/646 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbn_q11__cl5cc92dfe-1712022 | cbn_q11 | pregrt_ff_hold | 3.3 | repair_Violations best 13523 last 13523 rows 104 | before-window best 192059, window best 13523 | PROGRESS: repair_Violations improved 93.0 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 38.1 | drt_violations best 17 last 19 rows 58 | before-window best 20, window best 17 | PROGRESS: drt_violations improved 15.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 25.7 | drt_violations best 15 last 15 rows 60 | before-window best 16, window best 15 | PROGRESS: drt_violations improved 6.2 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 41.0 | drt_violations best 7378 last 7378 rows 17 | before-window best 24596, window best 7378 | PROGRESS: drt_violations improved 70.0 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 27.6 | drt_violations best 78971 last 78971 rows 13 | before-window best 88174, window best 78971 | PROGRESS: drt_violations improved 10.4 % in window |  |
| intel2 | dpkit-coll_ftm-2729897 | coll_ftm | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
