# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 23:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 1, 'GRT-STUCK': 1, 'CANCEL-NOW': 2, 'GRT-LABEL': 24, 'YOUNG': 97, 'EXCLUDED': 4, 'KEEP': 1, 'PROGRESS': 22}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 53.3 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 53 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 8.7 | last meaningful line 7.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 7.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 45.1 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (20:9748 -> 25:30868 -> 30:14987; best 14 | REPORT-ONLY: lane-own kit (opus-kv-hg decides; nev |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-3680339 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 3_3_place_gp | 0.2 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-3680339-lec | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | lec | 0.0 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_1_grt | 1.3 | grt rounds 2 overflow 5:4204 -> 10:1924 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 38.4 | grt rounds 4 overflow 5:62755 -> 10:60390 -> 15:49497 -> 20:49999 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 52.8 | grt rounds 6 overflow 5:11659 -> 10:5657 -> 15:3245 -> 20:2874 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: overflow 5657 at round 10 > 1000 |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-3918557 | sle_st_a_v1 | 5_1_grt | 1.5 | grt rounds 2 overflow 5:719 -> 10:277 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-3912335 | sle_st_a_v2 | 5_1_grt | 1.5 | grt rounds 2 overflow 5:19179 -> 10:8579 | GRT-LABEL: DESIGN-FAIL: overflow 8579 at round 10 > 1000 |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3926258 | sle_st_a_v2 | 5_1_grt | 1.5 | grt rounds 2 overflow 5:13924 -> 10:5411 | GRT-LABEL: DESIGN-FAIL: overflow 5411 at round 10 > 1000 |  |
| epyc2 | dpkit-sle_st_a_v2__pv4242de79-3919753 | sle_st_a_v2 | 5_1_grt | 1.5 | grt rounds 2 overflow 5:12436 -> 10:5004 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-4003861 | slw_st_a_v2 | 5_1_grt | 1.5 | grt rounds 2 overflow 5:21357 -> 10:15408 | GRT-LABEL: DESIGN-FAIL: overflow 15408 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 32.0 | grt rounds 3 overflow 5:77484 -> 10:71484 -> 15:59403 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 36.9 | grt rounds 3 overflow 5:60207 -> 10:63713 -> 15:55011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 26.3 | grt rounds 3 overflow 5:51174 -> 10:49018 -> 15:39411 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 26.3 | grt rounds 3 overflow 5:49711 -> 10:49628 -> 15:39607 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 36.1 | grt rounds 3 overflow 5:45659 -> 10:49338 -> 15:43120 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 23.8 | grt rounds 4 overflow 5:110533 -> 10:75296 -> 15:54463 -> 20:61561 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 32.0 | grt rounds 4 overflow 5:95535 -> 10:71407 -> 15:50563 -> 20:56703 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 25.8 | grt rounds 4 overflow 5:105414 -> 10:70056 -> 15:50304 -> 20:58448 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | 5_1_grt | 9.7 | grt rounds 2 overflow 5:39369 -> 10:31446 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 26.9 | grt rounds 4 overflow 5:20337 -> 10:12248 -> 15:11083 -> 20:10187 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-3022331 | sle_ctl | 5_1_grt | 5.2 | grt rounds 1 overflow 5:100 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-hd_mesh-3170867 | hd_mesh | 5_1_grt | 7.0 | grt rounds 3 overflow 5:1303 -> 10:4557 -> 15:936 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 40.0 | grt rounds 4 overflow 5:32844 -> 10:12056 -> 15:8164 -> 20:7397 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 50.8 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-331468 | slw_st_a_v1 | 5_1_grt | 1.4 | grt rounds 2 overflow 5:1433 -> 10:638 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 33.5 | grt rounds 6 overflow 5:18843 -> 10:13916 -> 15:11809 -> 20:10993 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-bk_sel__t2-88557 | bk_sel__t2 | tt_setup_repair | 0.5 | last meaningful line 0.0 h ago (577/577 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-378709 | coll_core | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (60/60 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | pregrt_ff_hold | 1.0 | repair_TNS best 86683.9 last 86683.9 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-coll_ftc-3642118 | coll_ftc | 5_1_grt | 1.2 | last meaningful line 0.0 h ago (175/188 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-372805 | hd_lep0N | 3_1_place_gp_skip_io | 0.2 | overflow best 0.4748 last 0.4748 rows 31 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-hd_lep0N_w-232307 | hd_lep0N_w | 4_2_tapbal_grt | 0.4 | last meaningful line 0.0 h ago (46/51 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | pregrt_ff_hold | 1.1 | repair_TNS best 26647.3 last 26647.3 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-slice_station__t51-3353873 | slice_station__t51 | pregrt_ff_hold | 1.5 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | pregrt_ff_hold | 1.3 | repair_TNS best 74763.8 last 74763.8 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | pregrt_ff_hold | 1.2 | repair_TNS best 20342.7 last 20342.7 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | otc-1452780-18337 | 1452780 | cut_equiv | 3.3 | last meaningful line 0.2 h ago (869113/869113 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | otc-1610195-24003 | 1610195 | cut_equiv | 3.1 | last meaningful line 0.0 h ago (1124577/1124577 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | so_437353_ff_75627 | so_437353_ff_75627 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (275/275 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | so_437353_tt_75627 | so_437353_tt_75627 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (275/275 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | so_602714_ff_23512 | so_602714_ff_23512 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (184/184 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | so_602714_tt_23512 | so_602714_tt_23512 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (184/184 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl1b5a6458-557330 | cbf_q00 | 5_1_grt | 4.4 | last meaningful line 2.0 h ago (25/25 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q01_s2-557381 | cbf_q01_s2 | 5_1_grt | 4.4 | last meaningful line 1.8 h ago (25/25 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q00__cl622f65d2-646648 | cbn_q00 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | 5_2_route | 12.2 | last meaningful line 0.3 h ago (282/283 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_io_cor-579275 | kv3_io_cor | 5_1_grt | 0.9 | last meaningful line 0.0 h ago (160/160 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-native59-3892390 | native59 | pregrt_ff_hold | 1.5 | repair_TNS best 8757.48 last 8757.48 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-serdes__t14-4042057 | serdes__t14 | 5_1_grt | 1.5 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | pregrt_ff_hold | 1.5 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-3888951 | sle_fw_v2 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (4942/4942 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (5481/5481 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-3919840 | sle_stm_v1 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (5883/5883 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | tt_setup_measure | 1.5 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (6333/6333 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (5334/5335 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (5913/5913 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | 4_1_cts | 1.5 | last meaningful line 0.2 h ago (4607/4607 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (4916/4916 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-1019838 | slw_sc_v1 | 5_2_route | 10.4 | drt_violations best 17177 last 17177 rows 3 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (5355/5355 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | pregrt_ff_hold | 1.5 | repair_TNS best 24150 last 24150 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-3023973 | col_h10_r0_p4__t1 | pregrt_ff_hold | 1.1 | repair_TNS best 50604.1 last 50604.1 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_c3x_C__t1-2476105 | dsdv_slice_c3x_C__t1 | 2_4_floorplan_pdn | 1.6 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hg_v1p2-672395 | kv3_hg_v1p2 | 5_1_grt | 5.3 | last meaningful line 2.0 h ago (307/1316 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 0.7 | repair_TNS best 86800.8 last 86800.8 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | postcts_gate_FF | 10.3 | last meaningful line -0.0 h ago (101531/101531 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (5429/5429 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | 4_1_cts | 1.5 | last meaningful line 0.2 h ago (5402/5402 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2969215 | sle_hc0 | 5_2_route | 11.0 | drt_violations best 12518 last 12518 rows 2 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-3504337 | sle_hc1 | 5_2_route | 10.7 | drt_violations best 106492 last 106492 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v3-2675829 | slw_fw_v3 | pregrt_ff_hold | 1.5 | repair_TNS best 6020.25 last 6020.25 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_sc_v2-3695652 | slw_sc_v2 | 5_2_route | 10.5 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3669665 | slw_st_b_v1 | 5_2_route | 10.5 | last meaningful line 0.1 h ago (271/272 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q00__cld7bf7197-3404310 | cbn_q00 | 5_1_grt | 9.3 | last meaningful line 3.8 h ago (25/25 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q11__cl5cc92dfe-4053720 | cbn_q11 | 3_3_place_gp | 0.5 | overflow best 0.0999 last 0.0999 rows 44 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1220915 | col_h9_r0_p2__t1 | 5_1_grt | 3.1 | last meaningful line 0.3 h ago (211/217 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3411/3411 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | pregrt_ff_hold | 0.4 | repair_TNS best 27683.5 last 27683.5 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | tt_setup_repair_grt | 11.2 | last meaningful line 2.0 h ago (18/18 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_1_grt | 11.2 | repair_Remaining best 132861 last 132861 rows 20 | YOUNG: evidence 3.7 h < 6 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1722167 | col_h9_r1__t1 | 5_1_grt | 2.6 | repair_TNS best 24.917 last 24.917 rows 17 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-3144441 | kv3_hg_v1p2 | 5_1_grt | 5.0 | last meaningful line 1.8 h ago (307/1316 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t16-3214240 | serdes__t16 | 3_3_place_gp | 1.2 | overflow best 0.1979 last 0.1979 rows 43 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-slice_station__t24__cleece78ec-3214521 | slice_station__t24 | 5_2_route | 1.2 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-3216548 | slice_station__t37 | 4_1_cts | 1.2 | last meaningful line 0.0 h ago (4153/4153 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 10.6 | drt_violations best 1162 last 1162 rows 16 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 10.4 | drt_violations best 53153 last 53153 rows 10 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc8 | kvcore-k_s1_-3692320 | kvcore-k_s1_ | lec | 0.9 | LEC last write 0.0 h ago | YOUNG: evidence 0.9 h < 6 h |  |
| epyc8 | prd-eco_20261122_024317_3271969-i1t-3547037 | eco_20261122_024317_3271969-i1t | 5_2_route | 4.7 | drt_violations best 35461 last 35461 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc8 | prd-eco_s1-i1-280620 | eco_s1-i1 | 5_2_route | 0.1 | last meaningful line 0.0 h ago (221/221 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | resign-kvahubrh1s1-lec | resign-kvahubrh1s1-lec | lec | 0.2 | LEC last write 0.0 h ago | YOUNG: evidence 0.2 h < 6 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-1503152 | col_h10_r1__t1 | 4_1_cts | 0.3 | repair_Violations best 17 last 17 rows 3 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-1715439 | col_h10_r1__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (116/116 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-931628 | col_h10_r1__t1 | pregrt_ff_hold | 0.9 | repair_TNS best 69984.3 last 69984.3 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-hd_ctl-585534 | hd_ctl | 5_2_route | 1.2 | drt_violations best 6988 last 6988 rows 2 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v6-1440068 | kv3_pv_v6 | 3_5_place_dp | 4.2 | last meaningful line 0.2 h ago (139/139 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-phy__t1-440520 | phy__t1 | 5_1_grt | 1.3 | last meaningful line 0.1 h ago (1168/1168 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | 4_1_cts | 1.4 | last meaningful line 0.2 h ago (5156/5156 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | pregrt_ff_hold | 1.4 | repair_TNS best 9325.56 last 9325.56 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | pregrt_ff_hold | 1.4 | repair_TNS best 13787.9 last 13787.9 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | otc-1758840-26581 | 1758840 | orfs_synth | 4.0 | last meaningful line 3.8 h ago (421/421 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | otc-4019702-12021 | 4019702 | orfs_synth | 1.8 | last meaningful line 1.8 h ago (418/418 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_1_grt | 0.3 | last meaningful line 0.2 h ago (251/421 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | ap-ageom-kw-cbn-q00--cldbcda913-grt-3143329 | cbn-q00--cldbcda913-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (149/149 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl870de686-2420314 | cbf_q00 | 3_3_place_gp | 0.7 | overflow best 0.5332 last 0.5332 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-cbf_q01-2572003 | cbf_q01 | 3_3_place_gp | 0.6 | last meaningful line 0.0 h ago (223/223 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-2418569 | cbn_q01 | 3_3_place_gp | 0.7 | overflow best 0.6125 last 0.6125 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-coll_core-3034599 | coll_core | 2_1_floorplan | 0.2 | repair_Viol best 1203 last 1203 rows 477 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-serdes__t12-2270834 | serdes__t12 | 3_3_place_gp | 0.9 | overflow best 0.6319 last 0.6319 rows 32 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-1537635 | sle_st_a_v1 | 5_1_grt | 1.5 | last meaningful line 0.5 h ago (207/215 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (5334/5334 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | pregrt_ff_hold | 1.7 | repair_TNS best 64740.7 last 64740.7 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i3-2690478 | eco_20261120_192428_3309571-i3 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 2.4 | drt_violations best 152197 last 152197 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_2_route | 5.8 | last meaningful line 0.2 h ago (288/289 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3997/3998 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-3303433 | hd_turn_a | 5_2_route | 0.5 | drt_violations best 4923 last 4923 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-kv3_io_ft-1983578 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5406 last 5406 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-2420088 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (227/228 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | otc-326399-23782 | 326399 | asbuilt.yosys | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | otc-1598469-19703 | 1598469 | asbuilt.yosys | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 40.6 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel2 | otc-3593902-19517 | 3593902 | - | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | otc-3882846-4506 | 3882846 | - | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-sle_su_c-3368948 | sle_su_c | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | pregrt_ff_hold | 1.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 45.0 | last meaningful line 1.6 h ago (1552/1552 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4022236 | col_h9_r2__t1 | 5_1_grt | 1.5 | repair_TNS best 0 last 0 rows 14 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3849055 | sle_su_l1 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-tt_ctlm-4018901 | tt_ctlm | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-iqf__t1-2959976 | iqf__t1 | 5_1_grt | 1.2 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 11.4 | drt_violations best 53583 last 53583 rows 12 | before-window best 87690, window best 53583 | PROGRESS: drt_violations improved 38.9 % in window |  |
| epyc8 | otc-2471981-17038 | 2471981 | tt_setup_repair_grt | 1.9 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-598842 | col_h10_r1__t1 | pregrt_ff_hold | 1.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-glue-344102 | glue | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_sys_c-996818 | kv3_sys_c | pregrt_ff_hold | 0.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3696149 | slw_hc3 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | otc-3997493-16991 | 3997493 | tt_setup_repair_grt | 1.8 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 12.7 | drt_violations best 571 last 982 rows 37 | before-window best 702, window best 571 | PROGRESS: drt_violations improved 18.7 % in window |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3048820 | col_h9_r1__t1 | 4_1_cts | 0.1 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | pregrt_ff_hold | 0.8 | repair_Violations best 0 last 0 rows 39 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-838976 | slw_hc3 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_161716_4143584-i1t-203702 | eco_20261121_161716_4143584-i1t | 5_2_route | 7.4 | drt_violations best 32 last 46 rows 19 | before-window best 98048, window best 32 | PROGRESS: drt_violations improved 100.0 % in window |  |
