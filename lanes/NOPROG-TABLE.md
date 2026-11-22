# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 00:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 1, 'GRT-STUCK': 1, 'CANCEL-NOW': 2, 'GRT-LABEL': 26, 'YOUNG': 76, 'NO-DATA': 4, 'EXCLUDED': 1, 'KEEP': 1, 'PROGRESS': 34}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 53.8 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 53 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 9.3 | last meaningful line 7.5 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 7.5 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 45.6 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (20:9748 -> 25:30868 -> 30:14987; best 14 | REPORT-ONLY: lane-own kit (opus-kv-hg decides; nev |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-4041960 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 6_report | 0.5 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-3680339 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | hold_gate | 0.7 |  | CANCEL-NOW: HBM is parked | CANCELLED |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_1_grt | 1.8 | grt rounds 2 overflow 5:4204 -> 10:1924 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 38.9 | grt rounds 4 overflow 5:62755 -> 10:60390 -> 15:49497 -> 20:49999 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 53.3 | grt rounds 6 overflow 5:11659 -> 10:5657 -> 15:3670 -> 20:2874 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-3918557 | sle_st_a_v1 | 5_1_grt | 2.0 | grt rounds 2 overflow 5:719 -> 10:277 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-3912335 | sle_st_a_v2 | 5_1_grt | 2.0 | grt rounds 2 overflow 5:19179 -> 10:8579 | GRT-LABEL: DESIGN-FAIL: overflow 8579 at round 10 > 1000 |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3926258 | sle_st_a_v2 | 5_1_grt | 2.0 | grt rounds 2 overflow 5:13924 -> 10:5411 | GRT-LABEL: DESIGN-FAIL: overflow 5411 at round 10 > 1000 |  |
| epyc2 | dpkit-sle_st_a_v2__pv4242de79-3919753 | sle_st_a_v2 | 5_1_grt | 2.0 | grt rounds 2 overflow 5:12436 -> 10:5004 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-4003861 | slw_st_a_v2 | 5_1_grt | 2.0 | grt rounds 2 overflow 5:21357 -> 10:15408 | GRT-LABEL: DESIGN-FAIL: overflow 15408 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 32.5 | grt rounds 3 overflow 5:63793 -> 10:71484 -> 15:59403 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 37.4 | grt rounds 3 overflow 5:60207 -> 10:63713 -> 15:55011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 26.8 | grt rounds 3 overflow 5:51174 -> 10:49018 -> 15:39466 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 26.8 | grt rounds 3 overflow 5:49711 -> 10:49628 -> 15:39607 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 36.6 | grt rounds 4 overflow 5:45659 -> 10:49338 -> 15:43120 -> 20:44324 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 24.3 | grt rounds 4 overflow 5:110533 -> 10:75296 -> 15:54463 -> 20:61561 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 32.5 | grt rounds 4 overflow 5:95535 -> 10:71407 -> 15:50563 -> 20:56703 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 26.3 | grt rounds 4 overflow 5:105414 -> 10:69762 -> 15:50304 -> 20:58448 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | 5_1_grt | 10.2 | grt rounds 2 overflow 5:39369 -> 10:31446 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hg_v1p2-3144441 | kv3_hg_v1p2 | 5_1_grt | 5.8 | grt rounds 2 overflow 5:60327 -> 10:46634 | GRT-LABEL: DESIGN-FAIL: overflow 46634 at round 10 > 1000 |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 27.7 | grt rounds 4 overflow 5:20337 -> 10:12248 -> 15:11083 -> 20:10120 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-3022331 | sle_ctl | 5_1_grt | 5.9 | grt rounds 1 overflow 5:100 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 40.5 | grt rounds 4 overflow 5:32844 -> 10:12056 -> 15:8164 -> 20:7397 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 51.3 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-331468 | slw_st_a_v1 | 5_1_grt | 1.9 | grt rounds 2 overflow 5:1433 -> 10:638 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 34.0 | grt rounds 6 overflow 5:18843 -> 10:13916 -> 15:11809 -> 20:10993 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_1_grt | 1.3 | grt rounds 2 overflow 5:3380 -> 10:1424 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-1537635 | sle_st_a_v1 | 5_1_grt | 2.0 | grt rounds 2 overflow 5:1403 -> 10:764 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-hd-lep0N-w-grt-1413282 | hd-lep0N-w-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (123/123 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-bk_sel__t2-88557 | bk_sel__t2 | 5_1_grt | 1.0 | last meaningful line 0.0 h ago (201/205 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-1290877 | cbf_q00 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5181/5181 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-cbn_q11__cl49ae4555-779889 | cbn_q11 | 3_3_place_gp | 0.5 | overflow best 0.632 last 0.6385 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-coll_core-378709 | coll_core | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (115/115 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-876737 | coll_core | 3_3_place_gp | 0.4 | overflow best 0.2656 last 0.2691 rows 33 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-coll_ftc-3642118 | coll_ftc | 5_1_grt | 1.7 | repair_TNS best 62.315 last 62.315 rows 3 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | dpkit-hd_host_e-1541416 | hd_host_e | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (861/862 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-879190 | hd_lep0N | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t16-1431122 | serdes__t16 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (319/319 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-1452780-18337 | 1452780 | cut_equiv | 3.8 | last meaningful line 0.0 h ago (869544/869544 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc10 | otc-1610195-24003 | 1610195 | cut_equiv | 3.6 | last meaningful line 0.0 h ago (1138612/1138612 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2t-853863 | eco_20261121_154936_3396612-i2t | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (257/804 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4022236 | col_h9_r2__t1 | postcts_gate_TT | 2.0 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | 5_2_route | 12.7 | last meaningful line 0.3 h ago (286/287 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-native59-3892390 | native59 | pregrt_ff_hold | 2.0 | repair_TNS best 8757.48 last 8757.48 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-serdes__t14-4042057 | serdes__t14 | 5_1_grt | 2.0 | last meaningful line 0.2 h ago (235/831 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 4_1_cts | 2.0 | last meaningful line 0.1 h ago (5027/5027 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-3888951 | sle_fw_v2 | 4_1_cts | 2.0 | last meaningful line 0.1 h ago (5004/5004 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 4_1_cts | 2.0 | last meaningful line 0.1 h ago (5164/5164 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | 4_1_cts | 2.0 | last meaningful line 0.1 h ago (5810/5810 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-3919840 | sle_stm_v1 | pregrt_ff_hold | 2.0 | repair_TNS best 33976.5 last 33976.5 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3849055 | sle_su_l1 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (178/190 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 4_1_cts | 2.0 | last meaningful line 0.1 h ago (5420/5420 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | pregrt_ff_hold | 2.0 | repair_TNS best 80432.6 last 80432.6 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | 4_1_cts | 2.0 | last meaningful line 0.1 h ago (4958/4958 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 4_1_cts | 2.0 | last meaningful line 0.1 h ago (5225/5225 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | 4_1_cts | 2.0 | last meaningful line 0.0 h ago (5282/5282 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-1019838 | slw_sc_v1 | 6_report | 10.9 | last meaningful line 0.0 h ago (650/650 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | pregrt_ff_hold | 2.0 | repair_TNS best 21262.9 last 21262.9 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-3023973 | col_h10_r0_p4__t1 | 5_1_grt | 1.7 | last meaningful line 0.0 h ago (156/156 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c3x_C__t1-2476105 | dsdv_slice_c3x_C__t1 | 3_3_place_gp | 2.1 | overflow best 0.7075 last 0.7075 rows 20 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-kv3_hg_v1p2-672395 | kv3_hg_v1p2 | 5_1_grt | 5.8 | last meaningful line 2.5 h ago (307/1317 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 1.2 | last meaningful line 0.0 h ago (204/206 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | 5_2_route | 10.8 | last meaningful line 0.0 h ago (263/263 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | 4_1_cts | 2.0 | last meaningful line 0.2 h ago (5433/5433 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | 4_1_cts | 2.0 | last meaningful line 0.3 h ago (5431/5431 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2969215 | sle_hc0 | 5_2_route | 11.5 | drt_violations best 8130 last 8130 rows 3 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-3504337 | sle_hc1 | 5_2_route | 11.2 | drt_violations best 13475 last 13475 rows 2 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3695652 | slw_sc_v2 | 5_2_route | 11.0 | drt_violations best 143212 last 143212 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3669665 | slw_st_b_v1 | 5_2_route | 11.0 | last meaningful line 0.1 h ago (281/282 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q00__cld7bf7197-3404310 | cbn_q00 | 5_1_grt | 10.0 | last meaningful line 4.5 h ago (25/25 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1220915 | col_h9_r0_p2__t1 | 5_1_grt | 3.8 | repair_Remaining best 62573 last 62573 rows 175 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 119763 last 119763 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_1_grt | 1.2 | last meaningful line 0.0 h ago (204/212 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | tt_setup_repair_grt | 11.9 | last meaningful line 2.8 h ago (18/18 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_1_grt | 11.9 | repair_Viol best 156 last 156 rows 7 | YOUNG: evidence 4.4 h < 6 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1722167 | col_h9_r1__t1 | 5_1_grt | 3.3 | last meaningful line 0.0 h ago (1580/1586 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-498729 | kv3_hub_Eo | 3_1_place_gp_skip_io | 0.6 | overflow best 0.5407 last 0.5407 rows 30 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_hub_Wo-495489 | kv3_hub_Wo | 3_1_place_gp_skip_io | 0.6 | overflow best 0.6346 last 0.6346 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slice_station__t24__cleece78ec-3214521 | slice_station__t24 | 5_2_route | 2.0 | drt_violations best 7859 last 7859 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 11.4 | drt_violations best 1045 last 4367 rows 18 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc8 | resign-kvahubrh1s2-lec | resign-kvahubrh1s2-lec | lec | 0.3 | LEC last write 0.3 h ago | YOUNG: evidence 0.3 h < 6 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-1503152 | col_h10_r1__t1 | pregrt_ff_hold | 0.8 | repair_TNS best 30855.3 last 30855.3 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2348402 | col_h10_r1__t1 | 4_1_cts | 0.1 | repair_Violations best 12 last 34 rows 21 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-598842 | col_h10_r1__t1 | 5_1_grt | 1.7 | last meaningful line 0.3 h ago (203/209 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-1875468 | dsdv_slice_iq_C__t1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.8698 last 0.8976 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v6-1440068 | kv3_pv_v6 | 3_5_place_dp | 4.7 | last meaningful line 0.5 h ago (139/139 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | otc-4019702-12021 | 4019702 | orfs_synth | 2.3 | last meaningful line 2.3 h ago (418/418 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | prd-eco1-i1t-2348772 | eco1-i1t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_2_route | 0.8 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl870de686-2420314 | cbf_q00 | 3_4_place_resized | 1.2 | last meaningful line 0.2 h ago (21/21 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-cbf_q01-2572003 | cbf_q01 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-cbf_q01_s2-3730726 | cbf_q01_s2 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 75 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-cbf_q11-3484067 | cbf_q11 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-2418569 | cbn_q01 | 3_4_place_resized | 1.2 | last meaningful line 0.2 h ago (20/20 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3048820 | col_h9_r1__t1 | pregrt_ff_hold | 0.6 | repair_TNS best 9448.21 last 9448.21 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-coll_core-3034599 | coll_core | 3_3_place_gp | 0.7 | overflow best 0.1981 last 0.1981 rows 40 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (5475/5475 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i3-2690478 | eco_20261120_192428_3309571-i3 | 5_2_route | 1.0 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 2.9 | drt_violations best 152197 last 152197 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_2_route | 6.3 | last meaningful line 0.2 h ago (292/293 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-4053367 | coll_ftm | 5_1_grt | 0.5 | repair_Remaining best 27817 last 27817 rows 22 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | tt_setup_repair | 0.8 | repair_Viol best 350 last 350 rows 34 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-831843 | hd_turn_a | postcts_gate_FF | 0.2 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | so_1124771_ff_44418 | so_1124771_ff_44418 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_1124771_tt_44418 | so_1124771_tt_44418 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_1142316_ff_91035 | so_1142316_ff_91035 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_1142316_tt_91035 | so_1142316_tt_91035 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | stoic_golick | stoic_golick | asbuilt.yosys | 0.0 | last meaningful line -0.0 h ago (104/104 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-2398806-5940 | 2398806 | asbuilt.yosys | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 41.1 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_su_c-3368948 | sle_su_c | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slice_station__t51-3353873 | slice_station__t51 | 5_1_grt | 2.0 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | pregrt_ff_hold | 1.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | pregrt_ff_hold | 1.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 45.5 | last meaningful line 0.2 h ago (1554/1554 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_io_cor-579275 | kv3_io_cor | 5_1_grt | 1.4 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-tt_ctlm-4018901 | tt_ctlm | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-iqf__t1-2959976 | iqf__t1 | 5_1_grt | 1.7 | repair_TNS best 0 last 0 rows 20 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fw_v3-2675829 | slw_fw_v3 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 11.9 | drt_violations best 53583 last 53583 rows 12 | before-window best 81322, window best 53583 | PROGRESS: drt_violations improved 34.1 % in window |  |
| epyc8 | dpkit-slice_station__t37-3216548 | slice_station__t37 | 5_1_grt | 2.0 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 11.2 | drt_violations best 50163 last 50163 rows 11 | before-window best 168894, window best 50163 | PROGRESS: drt_violations improved 70.3 % in window |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-931628 | col_h10_r1__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-glue-344102 | glue | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-kv3_sys_c-996818 | kv3_sys_c | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | pregrt_ff_hold | 2.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3696149 | slw_hc3 | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 13.2 | drt_violations best 571 last 982 rows 37 | before-window best 658, window best 571 | PROGRESS: drt_violations improved 13.2 % in window |  |
| intel1 | ap-ageom-kw-serdes--t12-grt-3662579 | serdes--t12-grt | 3_5_place_dp | 0.1 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-838976 | slw_hc3 | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_161716_4143584-i1t-203702 | eco_20261121_161716_4143584-i1t | 5_2_route | 7.9 | drt_violations best 32 last 46 rows 19 | before-window best 98048, window best 32 | PROGRESS: drt_violations improved 100.0 % in window |  |
