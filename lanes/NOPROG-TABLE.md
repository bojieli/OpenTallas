# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 23:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'NO-PROGRESS': 2, 'GRT-STUCK': 2, 'CANCEL-NOW': 2, 'GRT-LABEL': 18, 'YOUNG': 117, 'NO-DATA': 3, 'EXCLUDED': 2, 'KEEP': 1, 'PROGRESS': 16}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 52.8 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 52 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc7 | dpkit-cbf_q11-3840796 | cbf_q11 | 5_1_grt | 9.6 | last meaningful line 6.5 h ago (25/25 lines) | NO-PROGRESS: no new non-iteration log line for 6.5 h | REPORTED (cancel next pass) |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 26.8 | grt rounds 5 overflow 5:44451 -> 10:38859 -> 15:36410 -> 20:37714 -> 25:43219 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (15:36410 -> 20:37714 -> 25:43219; best 3 | REPORTED (cancel next pass) |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 8.0 | last meaningful line 6.3 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 6.3 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 44.6 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-STUCK: GRT overflow flat/rising over 3 rounds (20:9748 -> 25:30868 -> 30:14987; best 14 | REPORT-ONLY: lane-own kit (opus-kv-hg decides; nev |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-2376473 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 5_2_route | 0.2 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-1670834 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 5_1_grt | 0.7 |  | CANCEL-NOW: HBM is parked | CANCELLED |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_1_grt | 0.8 | grt rounds 2 overflow 5:4204 -> 10:1924 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 37.9 | grt rounds 4 overflow 5:62755 -> 10:60390 -> 15:49497 -> 20:49999 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 52.3 | grt rounds 6 overflow 5:11659 -> 10:5657 -> 15:3245 -> 20:2874 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: overflow 5657 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 31.2 | grt rounds 3 overflow 5:77484 -> 10:71484 -> 15:59403 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 36.2 | grt rounds 3 overflow 5:61525 -> 10:63713 -> 15:55011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 25.6 | grt rounds 3 overflow 5:51174 -> 10:49018 -> 15:39411 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 25.6 | grt rounds 3 overflow 5:49711 -> 10:49628 -> 15:39714 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 35.3 | grt rounds 3 overflow 5:45659 -> 10:49338 -> 15:43120 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 23.0 | grt rounds 4 overflow 5:110533 -> 10:75296 -> 15:54463 -> 20:61561 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 31.3 | grt rounds 4 overflow 5:95535 -> 10:71407 -> 15:50563 -> 20:56703 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 25.1 | grt rounds 4 overflow 5:97308 -> 10:70056 -> 15:50304 -> 20:58448 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | 5_1_grt | 8.9 | grt rounds 2 overflow 5:39369 -> 10:31446 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 26.7 | grt rounds 4 overflow 5:20337 -> 10:12248 -> 15:11083 -> 20:10187 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-3022331 | sle_ctl | 5_1_grt | 4.9 | grt rounds 1 overflow 5:100 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 39.5 | grt rounds 4 overflow 5:32844 -> 10:12056 -> 15:8164 -> 20:7397 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 50.3 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-331468 | slw_st_a_v1 | 5_1_grt | 0.9 | grt rounds 2 overflow 5:1433 -> 10:638 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 33.0 | grt rounds 6 overflow 5:18843 -> 10:13916 -> 15:11809 -> 20:11039 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-hd-lep0N-w-grt-71388 | hd-lep0N-w-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-bk_sel__t2-88557 | bk_sel__t2 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-3359919 | cbf_q00 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (101/101 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (7056/7056 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (5511/5511 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_su_c-3368948 | sle_su_c | pregrt_ff_hold | 1.0 | repair_TNS best 42884.7 last 42884.7 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slice_station__t51-3353873 | slice_station__t51 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (3789/3789 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (5161/5161 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (4707/4707 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | pregrt_ff_hold | 0.7 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | eco-abs-4134028 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.2 h ago (269/269 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | otc-1452780-18337 | 1452780 | cut_equiv | 2.8 | last meaningful line 0.0 h ago (862363/862363 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | otc-1610195-24003 | 1610195 | cut_equiv | 2.6 | last meaningful line 0.0 h ago (1117414/1117414 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1-396779 | eco_20261121_154936_3396612-i1 | 5_2_route | 3.7 | drt_violations best 22 last 22 rows 46 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl1b5a6458-557330 | cbf_q00 | 5_1_grt | 3.9 | last meaningful line 1.5 h ago (25/25 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00_s2-3732063 | cbf_q00_s2 | 3_4_place_resized | 1.1 | last meaningful line 0.3 h ago (21/21 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q01_s2-557381 | cbf_q01_s2 | 5_1_grt | 3.9 | last meaningful line 1.3 h ago (25/25 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q00__cl622f65d2-646648 | cbn_q00 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.8435 last 0.8435 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-cbn_q01__cld9ff4c40-3858041 | cbn_q01 | 3_4_place_resized | 1.0 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-3860266 | cbn_q11 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-cbx_q10__cl89936551-505277 | cbx_q10 | 3_3_place_gp | 0.5 | overflow best 0.0935 last 0.0935 rows 40 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4022236 | col_h9_r2__t1 | 5_1_grt | 1.0 | last meaningful line 0.1 h ago (204/213 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-coll_core-3871027 | coll_core | postplace_setup | 1.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 3_5_place_dp | 14.7 | last meaningful line 1.8 h ago (122/122 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | 5_2_route | 11.6 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_io_cor-579275 | kv3_io_cor | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (3212/3212 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-native59-3892390 | native59 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (5483/5483 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (4870/4870 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 3_3_place_gp | 1.0 | overflow best 0.0991 last 0.0991 rows 47 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-3888951 | sle_fw_v2 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | 3_3_place_gp | 1.0 | overflow best 0.1086 last 0.1086 rows 252 | YOUNG: stage 0.8 h < 1 h |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | 3_4_place_resized | 1.0 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-3918557 | sle_st_a_v1 | 5_1_grt | 1.0 | last meaningful line 0.0 h ago (207/216 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-3912335 | sle_st_a_v2 | 5_1_grt | 1.0 | last meaningful line 0.0 h ago (204/208 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3926258 | sle_st_a_v2 | 5_1_grt | 1.0 | last meaningful line 0.3 h ago (206/214 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv4242de79-3919753 | sle_st_a_v2 | 5_1_grt | 1.0 | last meaningful line 0.0 h ago (204/209 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-3919840 | sle_stm_v1 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (5789/5789 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (4516/4517 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (6092/6092 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3849055 | sle_su_l1 | pregrt_ff_hold | 1.0 | repair_TNS best 119168 last 119168 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 3_5_place_dp | 1.0 | last meaningful line 0.1 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (5773/5773 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | 3_4_place_resized | 1.0 | last meaningful line 0.1 h ago (372/372 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 3_4_place_resized | 1.0 | last meaningful line 0.0 h ago (393/393 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | 3_3_place_gp | 1.0 | overflow best 0.1995 last 0.1995 rows 241 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-1019838 | slw_sc_v1 | 5_2_route | 9.9 | drt_violations best 22331 last 22331 rows 2 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-4003861 | slw_st_a_v2 | 5_1_grt | 1.0 | last meaningful line 0.3 h ago (197/203 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (4971/4971 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (6198/6198 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-tt_ctlm-4018901 | tt_ctlm | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (3854/3854 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | so_874858_ff_8920 | so_874858_ff_8920 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | so_874858_tt_8920 | so_874858_tt_8920 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc7 | ap-ageom-kw-ot-s81sl-leaf--t39-grt-3300206 | ot-s81sl-leaf--t39-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-3023973 | col_h10_r0_p4__t1 | pregrt_ff_hold | 0.4 | repair_TNS best 50604.1 last 50604.1 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2998565 | col_h10_r2__t1 | pregrt_ff_hold | 0.4 | repair_TNS best 27577.7 last 27577.7 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_c3x_C__t1-2476105 | dsdv_slice_c3x_C__t1 | 1_1_yosys_canonicalize | 0.9 | last meaningful line 0.2 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-iqf__t1-2959976 | iqf__t1 | pregrt_ff_hold | 0.5 | repair_TNS best 8213.37 last 8213.37 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-kv3_hg_v1p2-672395 | kv3_hg_v1p2 | 5_1_grt | 4.6 | last meaningful line 1.3 h ago (307/1314 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | postcts_gate_TT | 9.5 | last meaningful line -0.0 h ago (106187/106187 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | postplace_setup | 0.8 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2969215 | sle_hc0 | 5_2_route | 10.3 | drt_violations best 99685 last 99685 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-3504337 | sle_hc1 | 5_2_route | 9.9 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v3-2675829 | slw_fw_v3 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (4594/4594 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3695652 | slw_sc_v2 | 5_2_route | 9.8 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3669665 | slw_st_b_v1 | 5_2_route | 9.8 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | so_3067826_ff_23381 | so_3067826_ff_23381 | generate_abstract | 0.4 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | so_3067826_tt_23381 | so_3067826_tt_23381 | generate_abstract | 0.4 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q00__cld7bf7197-3404310 | cbn_q00 | 5_1_grt | 9.0 | last meaningful line 3.5 h ago (25/25 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q11__cl5cc92dfe-4053720 | cbn_q11 | 3_1_place_gp_skip_io | 0.3 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1220915 | col_h9_r0_p2__t1 | 5_1_grt | 2.8 | last meaningful line 0.0 h ago (211/213 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (2813/2813 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | tt_setup_repair_grt | 10.9 | last meaningful line 1.8 h ago (18/18 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_1_grt | 10.9 | last meaningful line 0.0 h ago (203/208 lines) | YOUNG: evidence 3.4 h < 6 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1722167 | col_h9_r1__t1 | 5_1_grt | 2.3 | repair_TNS best 1172.77 last 1172.77 rows 2 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-3144441 | kv3_hg_v1p2 | 5_1_grt | 4.8 | last meaningful line 1.5 h ago (307/1315 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t16-3214240 | serdes__t16 | 3_3_place_gp | 1.0 | overflow best 0.8967 last 0.8967 rows 4 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-slice_station__t24__cleece78ec-3214521 | slice_station__t24 | tt_setup_repair_grt | 1.0 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-3216548 | slice_station__t37 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (3990/3990 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 10.4 | drt_violations best 1165 last 1165 rows 15 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 10.2 | drt_violations best 53153 last 53153 rows 10 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc8 | kvcore-k_s1_-3692320 | kvcore-k_s1_ | 6_report | 0.6 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261122_024317_3271969-i1t-3547037 | eco_20261122_024317_3271969-i1t | 5_2_route | 4.4 | drt_violations best 35461 last 35461 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc8 | so_115701_ff_77235 | so_115701_ff_77235 | 6_report | 0.0 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | so_115701_tt_77235 | so_115701_tt_77235 | 6_report | 0.0 | last meaningful line 0.0 h ago (54/54 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-kv3-pc--cl254f2e73-grt-1193293 | kv3-pc--cl254f2e73-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-598842 | col_h10_r1__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 14204.7 last 14204.7 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-931628 | col_h10_r1__t1 | pregrt_ff_hold | 0.4 | repair_TNS best 69984.3 last 69984.3 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-glue-344102 | glue | pregrt_ff_hold | 0.9 | repair_TNS best 4183.13 last 4183.13 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-hd_ctl-585534 | hd_ctl | 5_2_route | 0.7 | last meaningful line 0.0 h ago (256/257 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v6-1440068 | kv3_pv_v6 | 3_5_place_dp | 3.7 | last meaningful line 0.1 h ago (56/56 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_sys_c-996818 | kv3_sys_c | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3554/3554 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-phy__t1-440520 | phy__t1 | 5_1_grt | 0.8 | last meaningful line 0.0 h ago (1189/1194 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | tt_setup_repair | 0.9 | repair_Remaining best 142239 last 142239 rows 256 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | 4_1_cts | 0.9 | last meaningful line 0.0 h ago (5150/5150 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (5524/5524 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (5642/5642 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | otc-1758840-26581 | 1758840 | orfs_synth | 3.5 | last meaningful line 3.3 h ago (421/421 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | otc-4019702-12021 | 4019702 | orfs_synth | 1.3 | last meaningful line 1.3 h ago (418/418 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | prd-fin-745368 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (159/159 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl1b5a6458-1250934 | cbf_q00 | 3_4_place_resized | 1.2 | last meaningful line 0.3 h ago (21/21 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl870de686-2420314 | cbf_q00 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (1243/1243 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-cbf_q01-2572003 | cbf_q01 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 269 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-cbn_q00__cldbcda913-2242427 | cbn_q00 | 3_3_place_gp | 0.4 | overflow best 0.6451 last 0.6451 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-2418569 | cbn_q01 | 2_1_floorplan | 0.2 | repair_Viol best 6148 last 6148 rows 833 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3056/3056 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_pc__cl5a95b461-1446915 | kv3_pc | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_pc_v3-1356430 | kv3_pc_v3 | 3_3_place_gp | 1.1 | overflow best 0.2126 last 0.2126 rows 41 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-serdes__t12-2270834 | serdes__t12 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-1537635 | sle_st_a_v1 | 5_1_grt | 1.0 | last meaningful line 0.0 h ago (207/209 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5248/5249 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-838976 | slw_hc3 | pregrt_ff_hold | 1.6 | repair_TNS best 87586.5 last 87586.5 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_st_a_v2__cl9f076a5c-2381091 | slw_st_a_v2 | 3_4_place_resized | 0.3 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (5497/5497 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 1.9 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_2_route | 5.3 | last meaningful line 0.2 h ago (284/285 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2222604 | coll_ftm | 5_2_route | 2.2 | drt_violations best 295 last 295 rows 2 | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-1820924 | dsdv_slice_lepe_mu_LP__t2 | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (264/264 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-2382735 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-2420088 | slice_station__t12 | 5_1_grt | 0.2 | repair_Remaining best 13223 last 13223 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | otc-4021645-5164 | 4021645 | - | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 40.1 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel2 | otc-3068005-16889 | 3068005 | asbuilt.yosys | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-coll_ftc-3642118 | coll_ftc | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 44.5 | last meaningful line 1.1 h ago (1552/1552 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-serdes__t14-4042057 | serdes__t14 | pregrt_ff_hold | 1.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 10.6 | drt_violations best 55390 last 55390 rows 11 | before-window best 181727, window best 55390 | PROGRESS: drt_violations improved 69.5 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | otc-2471981-17038 | 2471981 | tt_setup_repair_grt | 1.7 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-859834 | col_h10_r1__t1 | 3_5_place_dp | 0.4 | repair_Violations best 0 last 0 rows 37 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-hd_mesh-3170867 | hd_mesh | pregrt_ff_hold | 6.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3696149 | slw_hc3 | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | otc-3997493-16991 | 3997493 | tt_setup_repair_grt | 1.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 12.2 | drt_violations best 571 last 982 rows 37 | before-window best 811, window best 571 | PROGRESS: drt_violations improved 29.6 % in window |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-2221122 | col_h9_r1__t1 | 3_5_place_dp | 0.4 | repair_Violations best 0 last 0 rows 36 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | prd-eco_20261121_161716_4143584-i1t-203702 | eco_20261121_161716_4143584-i1t | 5_2_route | 6.9 | drt_violations best 32 last 84 rows 18 | before-window best 98048, window best 32 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel2 | dpkit-kv3_io_ft-1983578 | kv3_io_ft | 5_1_grt | 0.5 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS reached 0 |  |
