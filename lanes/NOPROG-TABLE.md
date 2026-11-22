# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 01:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 1, 'GRT-STUCK': 1, 'CANCEL-NOW': 2, 'GRT-LABEL': 29, 'NO-DATA': 5, 'YOUNG': 72, 'EXCLUDED': 1, 'KEEP': 1, 'PROGRESS': 38}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 54.6 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -1270.44 ps (< -300, gate TT >= -42); job age 5 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 10.0 | last meaningful line 8.3 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 8.3 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 46.3 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (20:9748 -> 25:30868 -> 30:14987; best 14 | REPORT-ONLY: lane-own kit (opus-kv-hg decides; nev |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-1560320 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 6_1_merge | 0.5 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-1566346 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 3_5_place_dp | 0.5 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_1_grt | 2.6 | grt rounds 2 overflow 5:4204 -> 10:1924 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 39.7 | grt rounds 4 overflow 5:62755 -> 10:60390 -> 15:49497 -> 20:49757 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 54.1 | grt rounds 6 overflow 5:9444 -> 10:5657 -> 15:3670 -> 20:2874 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-3918557 | sle_st_a_v1 | 5_1_grt | 2.7 | grt rounds 2 overflow 5:719 -> 10:277 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-3912335 | sle_st_a_v2 | 5_1_grt | 2.8 | grt rounds 2 overflow 5:19179 -> 10:8579 | GRT-LABEL: DESIGN-FAIL: overflow 8579 at round 10 > 1000 |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3926258 | sle_st_a_v2 | 5_1_grt | 2.7 | grt rounds 2 overflow 5:13924 -> 10:5411 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v2__pv4242de79-3919753 | sle_st_a_v2 | 5_1_grt | 2.7 | grt rounds 2 overflow 5:12436 -> 10:5004 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-4003861 | slw_st_a_v2 | 5_1_grt | 2.7 | grt rounds 2 overflow 5:21357 -> 10:15408 | GRT-LABEL: DESIGN-FAIL: overflow 15408 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 33.2 | grt rounds 3 overflow 5:63793 -> 10:71484 -> 15:59403 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 38.2 | grt rounds 3 overflow 5:60207 -> 10:63713 -> 15:55011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hg_v1p2-672395 | kv3_hg_v1p2 | 5_1_grt | 6.6 | grt rounds 2 overflow 5:58877 -> 10:46109 | GRT-LABEL: DESIGN-FAIL: overflow 46109 at round 10 > 1000 |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 27.6 | grt rounds 3 overflow 5:51174 -> 10:49018 -> 15:39466 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 27.6 | grt rounds 3 overflow 5:49711 -> 10:49628 -> 15:39607 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 37.3 | grt rounds 4 overflow 5:82307 -> 10:49338 -> 15:43120 -> 20:44324 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 25.0 | grt rounds 4 overflow 5:111429 -> 10:75296 -> 15:54463 -> 20:61561 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 33.3 | grt rounds 4 overflow 5:95257 -> 10:71407 -> 15:50563 -> 20:56703 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 27.1 | grt rounds 4 overflow 5:105414 -> 10:69762 -> 15:50304 -> 20:58448 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | 5_1_grt | 10.9 | grt rounds 2 overflow 5:39369 -> 10:31446 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1220915 | col_h9_r0_p2__t1 | 5_1_grt | 4.6 | grt rounds 2 overflow 5:87414 -> 10:72 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_1_grt | 1.9 | grt rounds 2 overflow 5:40465 -> 10:379 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hg_v1p2-3144441 | kv3_hg_v1p2 | 5_1_grt | 6.5 | grt rounds 2 overflow 5:60327 -> 10:46634 | GRT-LABEL: DESIGN-FAIL: overflow 46634 at round 10 > 1000 |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 28.4 | grt rounds 4 overflow 5:20337 -> 10:12248 -> 15:11083 -> 20:10120 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-3022331 | sle_ctl | 5_1_grt | 6.7 | grt rounds 1 overflow 5:100 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 41.3 | grt rounds 5 overflow 5:32844 -> 10:12056 -> 15:8164 -> 20:7397 -> 25:22417 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 52.0 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-331468 | slw_st_a_v1 | 5_1_grt | 2.6 | grt rounds 2 overflow 5:1433 -> 10:638 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 34.8 | grt rounds 6 overflow 5:18843 -> 10:13916 -> 15:11809 -> 20:10993 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_1_grt | 2.0 | grt rounds 2 overflow 5:3380 -> 10:1424 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-1537635 | sle_st_a_v1 | 5_1_grt | 2.7 | grt rounds 2 overflow 5:1403 -> 10:764 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-hd-lep0N-grt-2663301 | hd-lep0N-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | brave_lederberg | brave_lederberg | bound.yosys | 0.0 | last meaningful line 0.0 h ago (197/197 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-bk_sel__t2-88557 | bk_sel__t2 | 5_1_grt | 1.8 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-2083685 | coll_core | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (7047/7047 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-2606019 | coll_core | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (6558/6558 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_ctl-2275016 | hd_ctl | tt_setup_repair | 0.3 | repair_Remaining best 116019 last 116019 rows 63 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-hd_host_e-1541416 | hd_host_e | 5_1_grt | 0.8 | last meaningful line 0.0 h ago (705/726 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-1727564 | hd_lep0N_w | 4_2_tapbal_grt | 0.7 | last meaningful line 0.3 h ago (46/55 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t16-1431122 | serdes__t16 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.9021 last 0.9034 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slice_station__t51-3353873 | slice_station__t51 | 5_1_grt | 2.7 | last meaningful line 0.7 h ago (212/647 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | otc-1452780-18337 | 1452780 | cut_equiv | 4.6 | last meaningful line 0.1 h ago (870213/870213 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc10 | otc-1610195-24003 | 1610195 | cut_equiv | 4.4 | last meaningful line 0.0 h ago (1154540/1154540 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2t-853863 | eco_20261121_154936_3396612-i2t | 5_2_route | 1.2 | last meaningful line 0.1 h ago (281/282 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4022236 | col_h9_r2__t1 | 5_2_route | 2.7 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | 5_2_route | 13.4 | drt_violations best 111110 last 111110 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-kv3_io_cor-579275 | kv3_io_cor | postcts_gate_FF | 2.2 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-native59-3892390 | native59 | pregrt_ff_hold | 2.8 | repair_TNS best 8757.48 last 8757.48 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 4_1_cts | 2.8 | last meaningful line 0.0 h ago (5207/5207 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 4_1_cts | 2.8 | last meaningful line 0.1 h ago (5356/5356 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | pregrt_ff_hold | 2.8 | repair_TNS best 14472.7 last 14472.7 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | pregrt_ff_hold | 2.7 | repair_TNS best 52190.2 last 52190.2 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | pregrt_ff_hold | 2.7 | repair_TNS best 47594.4 last 47594.4 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 4_1_cts | 2.7 | last meaningful line 0.2 h ago (5381/5381 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | tt_setup_measure | 2.7 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | so_2551522_ff_10230 | so_2551522_ff_10230 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc2 | so_2551522_tt_10230 | so_2551522_tt_10230 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-3023973 | col_h10_r0_p4__t1 | 5_1_grt | 2.4 | last meaningful line 0.0 h ago (191/191 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c3x_C__t1-2476105 | dsdv_slice_c3x_C__t1 | 3_5_place_dp | 2.9 | last meaningful line 0.2 h ago (36/36 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-iqf__t1-2959976 | iqf__t1 | tt_setup_repair_grt | 2.5 | repair_Viol best 21 last 21 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 1.9 | last meaningful line 0.1 h ago (205/208 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | 5_2_route | 11.5 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | pregrt_ff_hold | 2.8 | repair_TNS best 18267.8 last 18267.8 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | pregrt_ff_hold | 2.8 | repair_TNS best 18267.8 last 18267.8 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-3504337 | sle_hc1 | 6_report | 11.9 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v3-2675829 | slw_fw_v3 | 5_1_grt | 2.7 | last meaningful line 0.0 h ago (77/77 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3695652 | slw_sc_v2 | 5_2_route | 11.8 | drt_violations best 143212 last 143212 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3669665 | slw_st_b_v1 | 5_2_route | 11.8 | drt_violations best 97368 last 97368 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | so_921011_ff_86668 | so_921011_ff_86668 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | so_921011_tt_86668 | so_921011_tt_86668 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-cbn_q00__cld7bf7197-3404310 | cbn_q00 | 5_1_grt | 10.8 | last meaningful line 5.3 h ago (25/25 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q00__cldbcda913-1547766 | cbn_q00 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (71/71 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | tt_setup_repair_grt | 12.7 | last meaningful line 0.5 h ago (18/18 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1722167 | col_h9_r1__t1 | 5_2_route | 4.1 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-1501063 | kv3_hub_Ei | 2_1_floorplan | 0.3 | last meaningful line 0.2 h ago (101/101 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-1446095 | kv3_hub_Eo | 2_1_floorplan | 0.3 | last meaningful line 0.2 h ago (105/105 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-1456285 | kv3_hub_Wo | 2_1_floorplan | 0.3 | last meaningful line 0.2 h ago (105/105 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pc_v1__cl23f6a148-1659424 | kv3_pc_v1 | 2_1_floorplan | 0.1 | repair_Viol best 8517 last 8517 rows 229 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-cbn_q00__cl622f65d2-2769900 | cbn_q00 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-1503152 | col_h10_r1__t1 | 5_1_grt | 1.5 | last meaningful line 0.0 h ago (203/207 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2348402 | col_h10_r1__t1 | pregrt_ff_hold | 0.8 | repair_TNS best 70719.1 last 70719.1 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-931628 | col_h10_r1__t1 | 5_1_grt | 2.1 | last meaningful line 0.3 h ago (203/209 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_iq_C__t1-1875468 | dsdv_slice_iq_C__t1 | 3_4_place_resized | 1.2 | repair_Remaining best 322633 last 322633 rows 65 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-hd_ctl-3141540 | hd_ctl | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3254/3254 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hroot-2659302 | kv3_hroot | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_sys_c-996818 | kv3_sys_c | 5_1_grt | 2.0 | last meaningful line 0.2 h ago (1292/1731 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | otc-4019702-12021 | 4019702 | orfs_synth | 3.1 | last meaningful line 3.0 h ago (418/418 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc9 | prd-eco1-i1t-2348772 | eco1-i1t | 5_2_route | 0.8 | drt_violations best 60429 last 60429 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_2_route | 1.5 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | prd-eco_r7k5-i1-3266898 | eco_r7k5-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | ap-ageom-kw-cbf-q11-grt-413758 | cbf-q11-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl1b5a6458-3962582 | cbf_q00 | 3_3_place_gp | 0.7 | overflow best 0.5266 last 0.539 rows 5 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-cbf_q00_s2-4005862 | cbf_q00_s2 | 3_3_place_gp | 0.6 | overflow best 0.3634 last 0.3634 rows 24 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-cbf_q01_s2-3730726 | cbf_q01_s2 | 3_4_place_resized | 0.8 | repair_Remaining best 199964 last 199964 rows 54 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-cbn_q01__cld9ff4c40-4945 | cbn_q01 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.8891 last 0.8947 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-cbn_q11__cl5cc92dfe-303693 | cbn_q11 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-246609 | cbx_q10 | 3_3_place_gp | 0.3 | overflow best 0.4946 last 0.4946 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3048820 | col_h9_r1__t1 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_pc__cl254f2e73-3961065 | kv3_pc | 3_3_place_gp | 0.6 | overflow best 0.8022 last 0.805 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_pc__cl5a95b461-3962503 | kv3_pc | 3_3_place_gp | 0.6 | overflow best 0.8007 last 0.8012 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_pc_v3-28674 | kv3_pc_v3 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.0 h ago (64/64 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i3-2690478 | eco_20261120_192428_3309571-i3 | 5_2_route | 1.7 | drt_violations best 231 last 231 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 3.7 | drt_violations best 152197 last 152197 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_2_route | 7.1 | drt_violations best 170434 last 170434 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-4053367 | coll_ftm | 5_2_route | 1.2 | last meaningful line 0.1 h ago (230/231 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 1.5 | repair_TNS best 224262 last 224262 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-2569555 | hd_turn_a | postcts_gate_FF | 0.2 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-1593723 | slice_station__t12 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (203/203 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-3109669-29879 | 3109669 | asbuilt.yosys | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 41.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-coll_ftc-3642118 | coll_ftc | 5_1_grt | 2.5 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_su_c-3368948 | sle_su_c | pregrt_ff_hold | 2.7 | repair_Violations best 0 last 0 rows 15 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | pregrt_ff_hold | 2.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 46.2 | last meaningful line 0.9 h ago (1554/1554 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-serdes__t14-4042057 | serdes__t14 | 5_1_grt | 2.7 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-3888951 | sle_fw_v2 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-3919840 | sle_stm_v1 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3849055 | sle_su_l1 | 5_1_grt | 2.8 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-tt_ctlm-4018901 | tt_ctlm | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 12.6 | drt_violations best 52295 last 52295 rows 13 | before-window best 65226, window best 52295 | PROGRESS: drt_violations improved 19.8 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slice_station__t37-3216548 | slice_station__t37 | 5_1_grt | 2.7 | repair_TNS best 0 last 0 rows 4 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 12.1 | drt_violations best 1045 last 1424 rows 20 | before-window best 49816, window best 1045 | PROGRESS: drt_violations improved 97.9 % in window |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 11.9 | drt_violations best 47754 last 47754 rows 12 | before-window best 168894, window best 47754 | PROGRESS: drt_violations improved 71.7 % in window |  |
| epyc9 | dpkit-glue-344102 | glue | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | pregrt_ff_hold | 2.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3696149 | slw_hc3 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 14.0 | drt_violations best 571 last 869 rows 40 | before-window best 655, window best 571 | PROGRESS: drt_violations improved 12.8 % in window |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-838976 | slw_hc3 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_161716_4143584-i1t-203702 | eco_20261121_161716_4143584-i1t | 5_2_route | 8.7 | drt_violations best 32 last 39 rows 20 | before-window best 98048, window best 32 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel2 | dpkit-kv3_io_ft-1566613 | kv3_io_ft | 5_1_grt | 0.5 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
