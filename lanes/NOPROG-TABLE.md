# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 22:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'GRT-STUCK': 2, 'UNSIGNABLE': 1, 'CANCEL-NOW': 3, 'GRT-LABEL': 16, 'NO-DATA': 5, 'YOUNG': 113, 'KEEP': 1, 'PROGRESS': 13}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 37.1 | grt rounds 6 overflow 5:56489 -> 10:43484 -> 15:40478 -> 20:43412 -> 25:50457 -> 30:60036 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (20:43412 -> 25:50457 -> 30:60036; best 5 | REPORTED (cancel next pass) |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 52.1 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 52 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 44.1 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (20:9748 -> 25:30868 -> 30:14987; best 14 | REPORT-ONLY: lane-own kit (opus-kv-hg decides; nev |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-695996 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 6_report | 0.5 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-1670834 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 3_3_place_gp | 0.2 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-1670834-lec | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | lec | 0.0 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 37.2 | grt rounds 4 overflow 5:62755 -> 10:60390 -> 15:49497 -> 20:49999 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 51.6 | grt rounds 6 overflow 5:11659 -> 10:5086 -> 15:3245 -> 20:2874 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: overflow 5086 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 30.7 | grt rounds 3 overflow 5:77484 -> 10:71484 -> 15:59403 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 35.7 | grt rounds 3 overflow 5:61525 -> 10:63713 -> 15:55011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 25.1 | grt rounds 3 overflow 5:51174 -> 10:49018 -> 15:39411 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 25.1 | grt rounds 3 overflow 5:49711 -> 10:49628 -> 15:39714 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 34.8 | grt rounds 3 overflow 5:45659 -> 10:49338 -> 15:43120 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 22.5 | grt rounds 4 overflow 5:110533 -> 10:75296 -> 15:54463 -> 20:62289 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 30.8 | grt rounds 4 overflow 5:95535 -> 10:71407 -> 15:50563 -> 20:56703 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 24.6 | grt rounds 4 overflow 5:97308 -> 10:70056 -> 15:50304 -> 20:58448 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 26.3 | grt rounds 4 overflow 5:44451 -> 10:38859 -> 15:36410 -> 20:37714 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | 5_1_grt | 8.4 | grt rounds 2 overflow 5:39369 -> 10:31446 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 25.9 | grt rounds 4 overflow 5:20337 -> 10:12248 -> 15:11108 -> 20:10187 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 39.0 | grt rounds 4 overflow 5:32844 -> 10:12056 -> 15:8164 -> 20:7397 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 49.8 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 32.3 | grt rounds 6 overflow 5:18843 -> 10:13916 -> 15:11809 -> 20:11039 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-slw-fw-v2--cl8537f156-grt-3540325 | slw-fw-v2--cl8537f156-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-bk_sel__t2-3372674 | bk_sel__t2 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.759 last 0.77 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-3359919 | cbf_q00 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9975 last 0.9975 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-coll_core-2602583 | coll_core | 3_5_place_dp | 0.9 | last meaningful line 0.1 h ago (115/115 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-3244284 | hd_lep0N | 3_1_place_gp_skip_io | 0.3 | overflow best 0.2529 last 0.2529 rows 36 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2826/2826 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-2216313 | sle_st_b_v1 | 3_5_place_dp | 1.2 | last meaningful line 0.0 h ago (118/118 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_su_c-3368948 | sle_su_c | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (4827/4828 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t45-3352558 | slice_station__t45 | 3_3_place_gp | 0.2 | overflow best 0.3139 last 0.3164 rows 31 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slice_station__t51-3353873 | slice_station__t51 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.4886 last 0.4886 rows 34 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-1452780-18337 | 1452780 | cut_equiv | 2.1 | last meaningful line 0.0 h ago (860038/860038 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | otc-1610195-24003 | 1610195 | cut_equiv | 1.9 | last meaningful line 0.0 h ago (1111446/1111446 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1-396779 | eco_20261121_154936_3396612-i1 | 5_2_route | 3.0 | drt_violations best 23 last 23 rows 7 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_203102_3392434-i1-2229259 | eco_20261121_203102_3392434-i1 | 5_2_route | 1.2 | last meaningful line 0.0 h ago (270/270 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_021210_171272-i1-1528590 | eco_20261122_021210_171272-i1 | 5_3_fillcell | 1.9 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl1b5a6458-557330 | cbf_q00 | 5_1_grt | 3.4 | last meaningful line 1.0 h ago (25/25 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00_s2-3732063 | cbf_q00_s2 | 3_3_place_gp | 0.6 | overflow best 0.242 last 0.242 rows 33 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-cbf_q01_s2-557381 | cbf_q01_s2 | 5_1_grt | 3.4 | last meaningful line 0.8 h ago (25/25 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q01__cld9ff4c40-3858041 | cbn_q01 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.6805 last 0.6805 rows 25 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-3860266 | cbn_q11 | 3_3_place_gp | 0.5 | overflow best 0.7097 last 0.7097 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-3868890 | cbx_q10 | 3_4_place_resized | 0.5 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4022236 | col_h9_r2__t1 | pregrt_ff_hold | 0.5 | repair_TNS best 21692.2 last 21692.2 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-coll_core-3871027 | coll_core | 3_3_place_gp | 0.5 | overflow best 0.3666 last 0.3666 rows 24 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 3_5_place_dp | 14.2 | last meaningful line 1.3 h ago (122/122 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | 5_2_route | 11.1 | last meaningful line 0.2 h ago (273/273 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-native59-3892390 | native59 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5308/5309 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4812/4812 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 3_3_place_gp | 0.5 | last meaningful line -0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-3888951 | sle_fw_v2 | 3_3_place_gp | 0.5 | overflow best 0.0988 last 0.0988 rows 42 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 3_3_place_gp | 0.5 | overflow best 0.3206 last 0.4078 rows 76 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | 3_3_place_gp | 0.5 | overflow best 0.6495 last 0.6495 rows 29 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-3918557 | sle_st_a_v1 | tt_setup_repair | 0.5 | repair_Viol best 7 last 7 rows 21 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-3912335 | sle_st_a_v2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5921/5921 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3926258 | sle_st_a_v2 | 5_1_grt | 0.5 | last meaningful line 0.0 h ago (86/86 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv4242de79-3919753 | sle_st_a_v2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (6209/6209 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-3919840 | sle_stm_v1 | 3_3_place_gp | 0.5 | overflow best 0.0993 last 0.0993 rows 44 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | 3_3_place_gp | 0.5 | overflow best 0.0994 last 0.0994 rows 43 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | 3_4_place_resized | 0.5 | repair_Remaining best 83150 last 83150 rows 211 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3849055 | sle_su_l1 | pregrt_ff_hold | 0.5 | repair_TNS best 1.20324e+06 last 1.20324e+06 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 3_3_place_gp | 0.5 | overflow best 0.2014 last 0.2014 rows 35 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5717/5717 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | generate_abstract | 15.8 | last meaningful line 0.2 h ago (722/722 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.1354 last 0.1354 rows 50 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | 3_3_place_gp | 0.5 | overflow best 0.6541 last 0.6541 rows 29 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-1019838 | slw_sc_v1 | 5_2_route | 9.4 | drt_violations best 139030 last 139030 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-4003861 | slw_st_a_v2 | hold_gate | 0.5 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | 3_3_place_gp | 0.5 | overflow best 0.2869 last 0.2869 rows 36 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (6008/6008 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-tt_ctlm-4018901 | tt_ctlm | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-col-h10-r0-p4--t1--pvcc166a6d-grt-2785969 | col-h10-r0-p4--t1--pvcc166a6d-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-iqf--t1-grt-2897226 | iqf--t1-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbf_q11-3840796 | cbf_q11 | 5_1_grt | 9.1 | last meaningful line 6.0 h ago (25/25 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c3x_C__t1-2476105 | dsdv_slice_c3x_C__t1 | sdc_lint | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hg_v1p2-672395 | kv3_hg_v1p2 | 5_1_grt | 4.1 | last meaningful line 0.8 h ago (307/1313 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2842999 | ot_s81sl_leaf__t39 | 3_1_place_gp_skip_io | 0.1 | last meaningful line 0.0 h ago (7/7 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | postcts_gate_TT | 9.0 | last meaningful line 0.0 h ago (1792/1792 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | 3_3_place_gp | 0.3 | overflow best 0.9131 last 0.9131 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | 3_3_place_gp | 0.3 | overflow best 0.9253 last 0.9253 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2969215 | sle_hc0 | 5_2_route | 9.8 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-3504337 | sle_hc1 | 5_2_route | 9.4 | last meaningful line 0.1 h ago (264/264 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v3-2675829 | slw_fw_v3 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (4245/4245 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3695652 | slw_sc_v2 | 5_2_route | 9.3 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3669665 | slw_st_b_v1 | postcts_gate_FF | 9.3 | last meaningful line 0.0 h ago (494/494 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | eco-abs-1967534 | eco-abs | generate_abstract | 0.7 | last meaningful line 0.4 h ago (1030/1030 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | otc-2277411-9957 | 2277411 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-cbn_q00__cld7bf7197-3404310 | cbn_q00 | 5_1_grt | 8.3 | last meaningful line 2.8 h ago (25/25 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1220988 | col_h9_r0_p2__t1 | 5_1_grt | 2.1 | last meaningful line 0.3 h ago (210/217 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1220915 | col_h9_r0_p2__t1 | 5_1_grt | 2.1 | last meaningful line 0.0 h ago (210/212 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3204482 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9192 last 0.9192 rows 8 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | tt_setup_repair_grt | 10.2 | last meaningful line 1.0 h ago (18/18 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_1_grt | 10.2 | last meaningful line 2.5 h ago (40/40 lines) | YOUNG: evidence 2.7 h < 6 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1722167 | col_h9_r1__t1 | 5_1_grt | 1.6 | repair_TNS best 7462.9 last 7462.9 rows 2 | YOUNG: stage 0.8 h < 1 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-3144441 | kv3_hg_v1p2 | 5_1_grt | 4.0 | last meaningful line 0.8 h ago (307/1313 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t16-3214240 | serdes__t16 | port_bind | 0.2 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-3022331 | sle_ctl | 5_1_grt | 4.2 | repair_Remaining best 344592 last 344592 rows 42 | YOUNG: stage 0.6 h < 1 h |  |
| epyc8 | dpkit-slice_station__t24__cleece78ec-3214521 | slice_station__t24 | 3_4_place_resized | 0.2 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-3216548 | slice_station__t37 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.5455 last 0.5455 rows 33 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 9.6 | drt_violations best 1433 last 1433 rows 13 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 9.4 | drt_violations best 53604 last 53604 rows 9 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261122_024317_3271969-i1t-3547037 | eco_20261122_024317_3271969-i1t | 5_2_route | 3.7 | drt_violations best 35461 last 35461 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-glue-344102 | glue | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4860/4860 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-585534 | hd_ctl | postcts_gate_TT | 0.2 | last meaningful line 0.0 h ago (899/899 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pc__cl254f2e73-62108 | kv3_pc | 3_3_place_gp | 0.6 | overflow best 0.3289 last 0.3289 rows 35 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v6-1440068 | kv3_pv_v6 | 3_4_place_resized | 3.2 | last meaningful line 0.3 h ago (655/655 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-kv3_sys_c-1592 | kv3_sys_c | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-phy__t1-440520 | phy__t1 | pregrt_ff_hold | 0.3 | repair_TNS best 509548 last 509548 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (3999/3999 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5064/5065 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | pregrt_ff_hold | 1.0 | repair_TNS best 29715.4 last 29715.4 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | pregrt_ff_hold | 0.8 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (5489/5489 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5607/5607 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | otc-1758840-26581 | 1758840 | orfs_synth | 3.0 | last meaningful line 2.8 h ago (421/421 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | otc-4019702-12021 | 4019702 | orfs_synth | 0.8 | last meaningful line 0.8 h ago (418/418 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i2-745368 | eco_20261121_070035_1645318-i2 | 5_2_route | 3.6 | drt_violations best 8 last 8 rows 47 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | so_751607_ff_4713 | so_751607_ff_4713 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (550/550 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | so_751607_tt_4713 | so_751607_tt_4713 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (550/550 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl1b5a6458-1250934 | cbf_q00 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.5711 last 0.5711 rows 30 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-cbf_q01_s2-1275625 | cbf_q01_s2 | 3_3_place_gp | 0.5 | overflow best 0.4581 last 0.4581 rows 6 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_hroot-1194403 | kv3_hroot | 3_3_place_gp | 0.5 | overflow best 0.1533 last 0.1533 rows 45 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-kv3_pc__cl5a95b461-1446915 | kv3_pc | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.1 h ago (61/61 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_pc_v3-1356430 | kv3_pc_v3 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_sys_c-1261696 | kv3_sys_c | 3_3_place_gp | 0.5 | overflow best 0.6609 last 0.6721 rows 23 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-1537635 | sle_st_a_v1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (9488/9488 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1018623 | sle_st_b_v2 | 3_3_place_gp | 0.6 | overflow best 0.1927 last 0.1927 rows 41 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-838976 | slw_hc3 | 4_1_cts | 0.8 | last meaningful line 0.2 h ago (4741/4741 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5414/5414 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i3t-3010955 | eco_20261120_192428_3309571-i3t | 5_2_route | 2.9 | drt_violations best 17 last 17 rows 7 | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 1.2 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1t-203702 | eco_20261121_161716_4143584-i1t | 5_2_route | 6.2 | drt_violations best 40 last 40 rows 16 | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_2_route | 4.6 | last meaningful line 0.0 h ago (277/277 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2222604 | coll_ftm | 5_2_route | 1.7 | drt_violations best 9684 last 9684 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-1820924 | dsdv_slice_lepe_mu_LP__t2 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-1678149 | hd_turn_a | postcts_gate_FF | 0.2 | last meaningful line 0.0 h ago (526/526 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | so_1944852_ff_62785 | so_1944852_ff_62785 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_1944852_tt_62785 | so_1944852_tt_62785 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 39.6 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 44.0 | last meaningful line 0.6 h ago (1552/1552 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-serdes__t14-4042057 | serdes__t14 | 4_1_cts | 0.5 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | ap-ageom-kw-col-h10-r2--t1--cl99efd374--pv1619ecc6-grt-2844749 | col-h10-r2--t1--cl99efd374--pv1619ecc6-grt | 3_5_place_dp | 0.1 | repair_Violations best 0 last 0 rows 34 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 10.1 | drt_violations best 55390 last 55390 rows 11 | before-window best 181727, window best 55390 | PROGRESS: drt_violations improved 69.5 % in window |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 7.5 | last meaningful line 5.8 h ago (622/622 lines) | PROGRESS: log still growing |  |
| epyc8 | otc-2471981-17038 | 2471981 | tt_setup_repair_grt | 0.9 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | ap-ageom-kw-col-h10-r1--t1--cld01bb4ae-grt-743972 | col-h10-r1--t1--cld01bb4ae-grt | 3_5_place_dp | 0.0 | repair_Violations best 0 last 0 rows 39 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-598842 | col_h10_r1__t1 | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-hd_mesh-3170867 | hd_mesh | pregrt_ff_hold | 6.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3696149 | slw_hc3 | pregrt_ff_hold | 1.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-331468 | slw_st_a_v1 | pregrt_ff_hold | 0.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | otc-3997493-16991 | 3997493 | tt_setup_repair_grt | 0.8 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 11.7 | drt_violations best 571 last 1532 rows 35 | before-window best 1361, window best 571 | PROGRESS: drt_violations improved 58.0 % in window |  |
