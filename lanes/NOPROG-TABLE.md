# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 05:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 1, 'GRT-LABEL': 1, 'YOUNG': 91, 'NO-DATA': 4, 'PROGRESS': 14}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair_grt | 11.1 | repair_Violations best 0 last 0 rows 93 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -743.27 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | pregrt_ff_hold | 6.0 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | tt_setup_repair_grt | 10.8 | repair_Violations best 0 last 0 rows 62 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -773.59 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-1531184 | sle_ctl | 5_1_grt | 5.5 | grt rounds 2 overflow 5:25440 -> 10:4386 | GRT-LABEL: DESIGN-FAIL: overflow 4386 at round 10 > 1000 |  |
| epyc10 | otc-3703000-1555 | 3703000 | bbcnt | 0.7 | last meaningful line -0.0 h ago (158565/158565 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-381238-10081 | 381238 | bbcnt | 0.0 | last meaningful line -0.0 h ago (155764/155764 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-382076-13183 | 382076 | bbcnt | 0.0 | last meaningful line -0.0 h ago (129627/129627 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-390939-15248 | 390939 | gen_lint_check | 0.0 | last meaningful line 0.0 h ago (97/97 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-4085056-26666 | 4085056 | bbcnt | 0.4 | last meaningful line -0.0 h ago (132247/132247 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-hd_host_n-4152325 | hd_host_n | 5_2_route | 0.4 | last meaningful line 0.0 h ago (215/216 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-hd_st_n4-4161241 | hd_st_n4 | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-3829056 | ot_s81sl_leaf__t26 | 5_2_route | 0.6 | last meaningful line 0.1 h ago (265/265 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl05696ed1-3966951 | sle_hc0 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5848/5848 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl38badc56-3970782 | sle_hc0 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5328/5328 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-3979294 | sle_hc0 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (5652/5652 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc2__cl9c4c4509__cl3edce1b8-3987964 | sle_hc2 | 4_1_cts | 0.5 | last meaningful line 0.1 h ago (5373/5373 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-4001738 | sle_sc_v1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5895/5895 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv7b7fafb4-4024927 | sle_st_b_v1 | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (5443/5443 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3951031 | sle_st_b_v2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5468/5468 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l0__cl7a55c676-4027948 | sle_su_l0 | tt_setup_repair | 0.4 | last meaningful line 0.0 h ago (243/244 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc2__cl6bcaba89-4049393 | slw_hc2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5031/5031 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-4062944 | slw_hc3 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4691/4691 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-4102152 | slw_st_b_v1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5308/5308 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4111701 | slw_st_b_v1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5177/5177 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-4115743 | slw_st_b_v2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4745/4745 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pvc2ec5bfb-4120782 | slw_st_b_v2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4966/4966 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l0__cl1a1c1f8f-4150554 | slw_su_l0 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3661/3661 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | eco-abs-3806152 | eco-abs | generate_abstract | 0.6 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | so_338545_ff_24236 | so_338545_ff_24236 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (1034/1034 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_338545_tt_24236 | so_338545_tt_24236 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (1034/1034 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-2841416 | cbn_q00 | 5_1_grt | 5.6 | last meaningful line 0.5 h ago (279/1289 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-glue-2294683 | glue | tt_setup_repair_grt | 6.0 | repair_Viol best 1337 last 1337 rows 43 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-hd_lep0N_w-995501 | hd_lep0N_w | pregrt_ff_hold | 1.0 | repair_TNS best 22010.5 last 22010.5 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-sle_hc2__clcc5e3e61-1959134 | sle_hc2 | postcts_gate_TT | 6.2 | last meaningful line 0.0 h ago (731/731 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | postcts_gate_FF | 5.6 | last meaningful line 0.2 h ago (2156/2156 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-1976266 | sle_sc_v1 | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (5639/5639 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v3-3573304 | sle_sc_v3 | 5_1_grt | 2.1 | last meaningful line 0.1 h ago (1280/1802 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl67389ecd-2555735 | sle_st_a_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (6801/6801 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-2492812 | sle_st_a_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (6600/6600 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-2595387 | sle_st_a_v1 | 4_1_cts | 0.1 | last meaningful line -0.0 h ago (6718/6718 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-2355490 | sle_st_a_v2 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5272/5272 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-2354216 | sle_st_a_v2 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5261/5261 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv4242de79-2374002 | sle_st_a_v2 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5349/5349 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v1__pv0e7b1dcc-2157611 | sle_st_b_v1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5459/5460 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | 5_2_route | 5.7 | last meaningful line 0.1 h ago (136/136 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-2036429 | sle_stm_v3 | 5_2_route | 6.2 | drt_violations best 11728 last 11728 rows 2 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2330098 | slw_sc_v1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5451/5452 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-2333813 | slw_sc_v1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5461/5462 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_2_route | 5.8 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3829486 | slw_sc_v2 | 5_1_grt | 1.9 | last meaningful line -0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clb036e152-2495581 | slw_st_a_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (6321/6321 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-2594734 | slw_st_a_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5910/5911 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2581554 | slw_st_a_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (5905/5905 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v2__clf4365a62-2648278 | slw_st_a_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (6065/6065 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | 5_2_route | 6.0 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2273272 | slw_stm_v2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (4416/4416 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2626529 | slw_stm_v2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i2-4134013 | eco_20261123_171023_3055226-i2 | 5_2_route | 1.7 | last meaningful line 0.2 h ago (131/131 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | tt_setup_repair_grt | 10.7 | repair_Violations best 5 last 8 rows 64 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc2__cla3497502__cl16607c7a-3549237 | slw_hc2 | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (5251/5251 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | fwdrep-sle_st_a_v1__cl67389ecd-p2-227130 | fwdrep-sle_st_a_v1 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | fwdrep-sle_su_l1__cl5ea486db-p0-271523 | fwdrep-sle_su_l1 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | fwdrep-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-p3-205428 | fwdrep-slw_st_a_v1 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-221065-3459 | 221065 | ins | 0.0 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-count-p1_tc-1761120 | count-p1_tc | prd_count_p1_tc | 0.2 | last meaningful line 0.1 h ago (62/62 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i3t-3968210 | eco_20261123_120225_75582-i3t | 5_2_route | 4.4 | drt_violations best 11 last 118 rows 33 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc9 | dpkit-hd_spn-3438721 | hd_spn | 3_4_place_resized | 0.3 | last meaningful line 0.0 h ago (165/165 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_sc_v3-3259684 | sle_sc_v3 | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (340/340 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__clfde1249e-2879520 | sle_st_b_v2 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (5694/5694 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-3249798 | slw_hc3 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5068/5068 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-slw_sc_v1__cl63e5a7a2-3279007 | slw_sc_v1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4583/4583 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l0_wfb17da-3833504 | qfd_qc_su_lane_w_l0_wfb17da | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l1_w460927-3833565 | qfd_qc_su_lane_w_l1_w460927 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l4_w285325-3836716 | qfd_qc_su_lane_w_l4_w285325 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l5_wf949e1-3841804 | qfd_qc_su_lane_w_l5_wf949e1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l6_wb51d05-3846832 | qfd_qc_su_lane_w_l6_wb51d05 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | kqc-qfd_qc_su_lane_w_l7_wd4f14d-3854495 | qfd_qc_su_lane_w_l7_wd4f14d | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224216_149959-i2-702588 | eco_20261123_224216_149959-i2 | 5_2_route | 2.6 | drt_violations best 93 last 93 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i2-2527977 | eco_20261123_224647_4153453-i2 | 5_2_route | 1.1 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i2t-283529 | eco_20261124_010152_2867084-i2t | 5_2_route | 2.9 | drt_violations best 3161 last 3161 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | prd-fin-46390 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-native59-1320092 | native59 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5384/5385 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1325351 | sle_fe_v1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5833/5834 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-sle_hc1__cl7d360508__pv97423966-1341249 | sle_hc1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5675/5676 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-1345836 | sle_hc2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4937/4937 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-1365381 | sle_st_b_v1 | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (5364/5364 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t12-1482120 | slice_station__t12 | postcts_gate_FF | 0.4 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8f84514c-1387851 | slw_fw_v2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5747/5748 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl1bc59e1c-1387403 | slw_hc0 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5165/5165 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc1__cl3449ea95-1389354 | slw_hc1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5358/5358 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cla3497502__cldc737267-1401912 | slw_hc2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4862/4863 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1439197 | slw_st_b_v1 | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (5253/5253 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-1446982 | slw_st_b_v2 | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (4707/4707 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v1__cle34a73c3-1454142 | slw_stm_v1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4766/4766 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-1670752-16443 | 1670752 | - | 4.5 |  | NO-DATA: no log found |  |
| intel1 | otc-1797391-24144 | 1797391 | flow3 | 0.1 | last meaningful line 0.0 h ago (157/157 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i1-1832688 | eco_20261123_191853_2879776-i1 | 5_2_route | 4.4 | drt_violations best 20 last 20 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-4110971 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5442 last 5442 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 4.4 | drt_violations best 424 last 424 rows 9 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 32.1 | drt_violations best 779 last 1754 rows 35 | before-window best 1392, window best 779 | PROGRESS: drt_violations improved 44.0 % in window |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 11.0 | last meaningful line 3.0 h ago (13932/13932 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 27.6 | drt_violations best 19595 last 19595 rows 12 | before-window best 35975, window best 19595 | PROGRESS: drt_violations improved 45.5 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 20.9 | drt_violations best 32431 last 32431 rows 11 | before-window best 45998, window best 32431 | PROGRESS: drt_violations improved 29.5 % in window |  |
| epyc7 | dpkit-native59-3518897 | native59 | pregrt_ff_hold | 5.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-4033310 | sle_sc_v1 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-42512 | sle_stm_v1 | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_stm_v3-3494601 | sle_stm_v3 | 5_1_grt | 2.2 | repair_TNS best 0 last 0 rows 4 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-3781995 | slw_stm_v2 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 34.9 | drt_violations best 48746 last 160916 rows 18 | before-window best 49778, window best 48746 | PROGRESS: drt_violations improved 2.1 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 35.1 | drt_violations best 74496 last 74496 rows 15 | before-window best 78971, window best 74496 | PROGRESS: drt_violations improved 5.7 % in window |  |
| intel1 | otc-1459998-19685 | 1459998 | census_3_place.otrun | 13.2 | last meaningful line 2.4 h ago (107/107 lines) | PROGRESS: log still growing |  |
| intel1 | otc-2044430-3114 | 2044430 | census_3_place.otrun | 16.9 | last meaningful line 2.4 h ago (107/107 lines) | PROGRESS: log still growing |  |
