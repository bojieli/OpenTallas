# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 22:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'GRT-STUCK': 2, 'UNSIGNABLE': 1, 'CANCEL-NOW': 1, 'GRT-LABEL': 17, 'YOUNG': 98, 'NO-DATA': 3, 'KEEP': 1, 'PROGRESS': 10}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 36.9 | grt rounds 5 overflow 5:56489 -> 10:43484 -> 15:40478 -> 20:43412 -> 25:50457 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (15:40478 -> 20:43412 -> 25:50457; best 4 | REPORTED (cancel next pass) |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 51.8 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 51 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 43.6 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (20:9748 -> 25:30868 -> 30:14987; best 14 | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-3092454 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | hold_gate | 0.7 |  | CANCEL-NOW: HBM is parked | CANCELLED |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 36.9 | grt rounds 4 overflow 5:62755 -> 10:60390 -> 15:49497 -> 20:49999 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 51.3 | grt rounds 6 overflow 5:9510 -> 10:5086 -> 15:3245 -> 20:2874 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: overflow 5086 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 30.5 | grt rounds 3 overflow 5:77484 -> 10:71484 -> 15:58855 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 35.4 | grt rounds 3 overflow 5:61525 -> 10:63713 -> 15:55011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 24.8 | grt rounds 3 overflow 5:51174 -> 10:49018 -> 15:39411 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 24.8 | grt rounds 3 overflow 5:49711 -> 10:49628 -> 15:39714 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 34.6 | grt rounds 3 overflow 5:45659 -> 10:49338 -> 15:43120 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 22.3 | grt rounds 4 overflow 5:110533 -> 10:75296 -> 15:54463 -> 20:62289 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 30.5 | grt rounds 4 overflow 5:95535 -> 10:71407 -> 15:50563 -> 20:56703 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 24.3 | grt rounds 4 overflow 5:97308 -> 10:70056 -> 15:50304 -> 20:58448 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 26.1 | grt rounds 4 overflow 5:44451 -> 10:38859 -> 15:36410 -> 20:37714 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | 5_1_grt | 8.2 | grt rounds 2 overflow 5:39369 -> 10:31446 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 25.7 | grt rounds 4 overflow 5:20337 -> 10:12248 -> 15:11108 -> 20:10187 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2289240 | col_h10_r1__t1 | 5_1_grt | 2.1 | grt rounds 2 overflow 5:2114 -> 10:1324 | GRT-LABEL: DESIGN-FAIL: overflow 1324 at round 10 > 1000 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 38.5 | grt rounds 4 overflow 5:32844 -> 10:12056 -> 15:8164 -> 20:7397 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 49.3 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 32.0 | grt rounds 6 overflow 5:18843 -> 10:13916 -> 15:12366 -> 20:11039 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_core-2602583 | coll_core | 3_3_place_gp | 0.6 | overflow best 0.0992 last 0.0992 rows 46 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-coll_ftc-2553210 | coll_ftc | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-3244284 | hd_lep0N | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (378/378 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-3212550 | hd_lep0N_w | 3_1_place_gp_skip_io | 0.1 | overflow best 0.7768 last 0.7768 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-kv3_hroot-2497950 | kv3_hroot | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-2216313 | sle_st_b_v1 | 3_3_place_gp | 1.0 | overflow best 0.2161 last 0.2161 rows 40 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2218630 | slw_fe_v1 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-2215543 | slw_fw_v2 | 3_4_place_resized | 1.0 | last meaningful line 0.0 h ago (406/406 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-2215364 | slw_st_b_v2 | 3_3_place_gp | 1.0 | overflow best 0.1372 last 0.1372 rows 42 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | otc-1452780-18337 | 1452780 | cut_equiv | 1.8 | last meaningful line 0.0 h ago (859743/859743 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | otc-1610195-24003 | 1610195 | cut_equiv | 1.6 | last meaningful line 0.0 h ago (1109770/1109770 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1-396779 | eco_20261121_154936_3396612-i1 | 5_2_route | 2.7 | drt_violations best 71294 last 71294 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_203102_3392434-i1-2229259 | eco_20261121_203102_3392434-i1 | 5_2_route | 0.9 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_021210_171272-i1-1528590 | eco_20261122_021210_171272-i1 | 5_2_route | 1.6 | drt_violations best 7 last 7 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl1b5a6458-557330 | cbf_q00 | 5_1_grt | 2.9 | last meaningful line 0.5 h ago (25/25 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl870de686-3854055 | cbf_q00 | postplace_setup | 0.0 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00_s2-3732063 | cbf_q00_s2 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 377 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-cbf_q01_s2-557381 | cbf_q01_s2 | 5_1_grt | 2.9 | last meaningful line 0.3 h ago (25/25 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q00__cl622f65d2-3856961 | cbn_q00 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q00__cldbcda913-3859515 | cbn_q00 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q01__clab6e67f2-3871332 | cbn_q01 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q01__cld9ff4c40-3858041 | cbn_q01 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-3860266 | cbn_q11 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbx_q10__cl89936551-3871198 | cbx_q10 | postplace_setup | 0.0 | last meaningful line -0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-3868890 | cbx_q10 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-coll_core-3871027 | coll_core | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (239/239 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 3_5_place_dp | 13.7 | last meaningful line 0.8 h ago (122/122 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | 5_2_route | 10.6 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_io_cor-3574752 | kv3_io_cor | 3_3_place_gp | 0.3 | overflow best 0.356 last 0.356 rows 32 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-native59-3892390 | native59 | selrange | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (201/201 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-3888951 | sle_fw_v2 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (154/154 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-3912335 | sle_st_a_v2 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-3919840 | sle_stm_v1 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3849055 | sle_su_l1 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | 6_report | 15.3 | last meaningful line 0.0 h ago (772/772 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-1019838 | slw_sc_v1 | 5_2_route | 8.9 | drt_violations best 139030 last 139030 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q11-3840796 | cbf_q11 | 5_1_grt | 8.9 | last meaningful line 5.8 h ago (25/25 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2277324 | col_h10_r0_p4__t1 | 3_3_place_gp | 0.3 | overflow best 0.1986 last 0.1986 rows 39 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2513972 | col_h10_r2__t1 | 3_3_place_gp | 0.1 | overflow best 0.3956 last 0.3956 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_c3x_C__t1-2476105 | dsdv_slice_c3x_C__t1 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-iqf__t1-2289342 | iqf__t1 | 3_3_place_gp | 0.3 | overflow best 0.3901 last 0.3901 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-kv3_hg_v1p2-672395 | kv3_hg_v1p2 | 5_1_grt | 3.8 | last meaningful line 0.5 h ago (307/1312 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | postcts_gate_TT | 8.8 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | 1_1_yosys_canonicalize | 0.0 | last meaningful line 0.0 h ago (62/62 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | 1_1_yosys_canonicalize | 0.0 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2969215 | sle_hc0 | 5_2_route | 9.5 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-3504337 | sle_hc1 | 5_2_route | 9.2 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3695652 | slw_sc_v2 | 5_2_route | 9.0 | last meaningful line 0.0 h ago (266/266 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3669665 | slw_st_b_v1 | postcts_gate_TT | 9.0 | last meaningful line -0.0 h ago (51675/51675 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | eco-abs-1967534 | eco-abs | generate_abstract | 0.5 | last meaningful line 0.1 h ago (1030/1030 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | otc-2277411-9957 | 2277411 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-cbn_q00__cld7bf7197-3404310 | cbn_q00 | 5_1_grt | 8.0 | last meaningful line 2.5 h ago (25/25 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1220988 | col_h9_r0_p2__t1 | 5_1_grt | 1.8 | last meaningful line 0.1 h ago (210/213 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | tt_setup_repair_grt | 9.9 | last meaningful line 0.8 h ago (18/18 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_1_grt | 9.9 | last meaningful line 2.3 h ago (40/40 lines) | YOUNG: evidence 2.4 h < 6 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1722167 | col_h9_r1__t1 | 5_1_grt | 1.3 | repair_Remaining best 22413 last 22413 rows 127 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-3144441 | kv3_hg_v1p2 | 5_1_grt | 3.8 | last meaningful line 0.5 h ago (307/1312 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-3022331 | sle_ctl | 5_1_grt | 3.9 | last meaningful line 0.0 h ago (222/231 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 9.4 | drt_violations best 1470 last 1470 rows 12 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 9.2 | drt_violations best 53604 last 53604 rows 9 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261122_024317_3271969-i1t-3547037 | eco_20261122_024317_3271969-i1t | 5_2_route | 3.4 | drt_violations best 35461 last 35461 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc8 | so_3051186_ff_39789 | so_3051186_ff_39789 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (472/472 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | so_3051186_tt_39789 | so_3051186_tt_39789 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (472/472 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-1585232 | hd_ctl | tt_setup_measure_grt | 2.6 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc__cl254f2e73-62108 | kv3_pc | 2_1_floorplan | 0.1 | repair_Viol best 7560 last 7560 rows 1106 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v6-1440068 | kv3_pv_v6 | 3_4_place_resized | 2.7 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_sys_c-1592 | kv3_sys_c | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-phy__t1-69732 | phy__t1 | 3_3_place_gp | 0.1 | overflow best 0.3381 last 0.3381 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5607/5607 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5263/5263 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3696149 | slw_hc3 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (5004/5004 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | eco-abs-133677 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.0 h ago (544/544 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-1732719-5782 | 1732719 | - | 2.5 |  | NO-DATA: no log found |  |
| epyc9 | otc-1758840-26581 | 1758840 | orfs_synth | 2.5 | last meaningful line 2.3 h ago (421/421 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc9 | otc-4019702-12021 | 4019702 | orfs_synth | 0.3 | last meaningful line 0.3 h ago (418/418 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i2-745368 | eco_20261121_070035_1645318-i2 | 5_2_route | 3.1 | drt_violations best 1340 last 1340 rows 10 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl1b5a6458-1250934 | cbf_q00 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (1243/1243 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-cbf_q01_s2-1275625 | cbf_q01_s2 | 2_1_floorplan | 0.2 | repair_Viol best 6148 last 6148 rows 718 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-kv3_hroot-1194403 | kv3_hroot | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (180/180 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_pc__cl5a95b461-1446915 | kv3_pc | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_pc_v3-1356430 | kv3_pc_v3 | 2_1_floorplan | 0.1 | repair_Viol best 8515 last 8515 rows 292 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_sys_c-1261696 | kv3_sys_c | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1018623 | sle_st_b_v2 | 3_3_place_gp | 0.3 | overflow best 0.7697 last 0.7697 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-838976 | slw_hc3 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (4739/4739 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5201/5202 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i3t-3010955 | eco_20261120_192428_3309571-i3t | 5_2_route | 2.7 | drt_violations best 19 last 19 rows 6 | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 0.9 | last meaningful line 0.1 h ago (265/266 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1t-203702 | eco_20261121_161716_4143584-i1t | 5_2_route | 5.9 | drt_violations best 62 last 62 rows 14 | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_2_route | 4.3 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2222604 | coll_ftm | 5_2_route | 1.2 | last meaningful line 0.1 h ago (230/231 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-277685 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (214/215 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-4069341 | hd_turn_a | 5_2_route | 0.5 | drt_violations best 4894 last 4894 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-4082903 | hd_turn_a | 5_2_route | 0.5 | drt_violations best 4894 last 4894 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-4082983 | hd_turn_a | 5_2_route | 0.5 | drt_violations best 5287 last 5287 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-kv3_io_ft-2215245 | kv3_io_ft | 5_2_route | 1.2 | drt_violations best 5406 last 5406 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-3121192 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (227/228 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 39.1 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 43.5 | last meaningful line 0.2 h ago (1552/1552 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 9.9 | drt_violations best 55390 last 55390 rows 11 | before-window best 181727, window best 55390 | PROGRESS: drt_violations improved 69.5 % in window |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 7.2 | last meaningful line 5.5 h ago (622/622 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1220915 | col_h9_r0_p2__t1 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | otc-2471981-17038 | 2471981 | tt_setup_repair_grt | 0.7 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | otc-709044-23442 | 709044 | tt_setup_repair_grt | 2.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-4042439 | col_h10_r1__t1 | 3_5_place_dp | 0.3 | repair_Violations best 0 last 0 rows 36 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-hd_mesh-3170867 | hd_mesh | pregrt_ff_hold | 5.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | otc-3997493-16991 | 3997493 | tt_setup_repair_grt | 0.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 11.2 | drt_violations best 571 last 3267 rows 34 | before-window best 1428, window best 571 | PROGRESS: drt_violations improved 60.0 % in window |  |
