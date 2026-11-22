# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 19:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'CANCEL-NOW': 2, 'GRT-LABEL': 25, 'YOUNG': 93, 'NO-DATA': 11, 'KEEP': 1, 'PROGRESS': 11}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 48.6 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 48 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-3479878 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 6_report | 0.5 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-3485599 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 3_3_place_gp | 0.5 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 33.7 | grt rounds 4 overflow 5:95946 -> 10:62005 -> 15:49678 -> 20:49999 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 33.6 | grt rounds 5 overflow 5:56489 -> 10:43484 -> 15:40478 -> 20:43412 -> 25:50457 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 48.1 | grt rounds 5 overflow 5:9510 -> 10:5086 -> 15:3245 -> 20:2874 -> 25:3124 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 37.3 | grt rounds 4 overflow 5:54036 -> 10:38366 -> 15:34625 -> 20:37416 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 27.2 | grt rounds 3 overflow 5:77484 -> 10:72294 -> 15:58855 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 32.2 | grt rounds 3 overflow 5:61525 -> 10:63713 -> 15:69180 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 21.6 | grt rounds 3 overflow 5:53769 -> 10:49359 -> 15:39411 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 21.6 | grt rounds 3 overflow 5:50621 -> 10:49445 -> 15:39714 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 31.3 | grt rounds 3 overflow 5:45785 -> 10:49448 -> 15:42999 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 19.0 | grt rounds 4 overflow 5:110533 -> 10:74939 -> 15:54793 -> 20:62289 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 27.3 | grt rounds 4 overflow 5:95535 -> 10:71407 -> 15:50597 -> 20:56554 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 21.1 | grt rounds 4 overflow 5:97308 -> 10:70056 -> 15:51390 -> 20:58440 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 22.8 | grt rounds 4 overflow 5:44451 -> 10:38859 -> 15:36410 -> 20:37882 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 22.8 | grt rounds 5 overflow 5:41833 -> 10:36208 -> 15:31830 -> 20:31076 -> 25:35283 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hgi_v2__cl2862d491-3732038 | kv3_hgi_v2 | 5_1_grt | 11.5 | grt rounds 2 overflow 5:72991 -> 10:37675 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 22.2 | grt rounds 4 overflow 5:18628 -> 10:12430 -> 15:11259 -> 20:10290 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 35.3 | grt rounds 4 overflow 5:32844 -> 10:12131 -> 15:8208 -> 20:7612 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 46.0 | grt rounds 6 overflow 5:18562 -> 10:18043 -> 15:11655 -> 20:10171 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 46.3 | grt rounds 5 overflow 5:32681 -> 10:30734 -> 15:25360 -> 20:22699 -> 25:31808 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 28.8 | grt rounds 6 overflow 5:19221 -> 10:22267 -> 15:17882 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 23.8 | grt rounds 4 overflow 5:36357 -> 10:30023 -> 15:24172 -> 20:20900 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 45.1 | grt rounds 4 overflow 5:67513 -> 10:54044 -> 15:50242 -> 20:55216 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 40.1 | grt rounds 3 overflow 5:59246 -> 10:46138 -> 15:41146 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 40.1 | grt rounds 3 overflow 5:60515 -> 10:47029 -> 15:53055 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 40.3 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-serdes__t4-293755 | serdes__t4 | 5_2_route | 8.8 | drt_violations best 138627 last 138627 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc10 | eco-abs-3818411 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (1024/1024 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1t-894339 | eco_20261121_154936_3396612-i1t | 5_2_route | 11.1 | drt_violations best 26 last 26 rows 57 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_203102_3392434-i1t-646001 | eco_20261121_203102_3392434-i1t | 5_2_route | 6.4 | drt_violations best 28193 last 28193 rows 2 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_012008_1324318-i1t-2203496 | eco_20261122_012008_1324318-i1t | 5_2_route | 1.6 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_021210_171272-i1t-3026978 | eco_20261122_021210_171272-i1t | 5_2_route | 0.8 | last meaningful line 0.1 h ago (258/259 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl1b5a6458-2747914 | cbf_q00 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4884/4884 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q01_s2-2747548 | cbf_q01_s2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5337/5337 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 3_4_place_resized | 10.4 | last meaningful line 0.5 h ago (519/519 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2374083 | sle_hc1 | 5_2_route | 16.5 | drt_violations best 20758 last 20758 rows 2 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-248840 | sle_st_a_v1 | tt_setup_repair_grt | 6.3 | repair_Viol best 64 last 64 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-3727923 | sle_st_a_v2 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-425190 | sle_su_l1 | 5_2_route | 6.1 | drt_violations best 80565 last 80565 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t36-3125329 | slice_station__t36 | generate_abstract | 12.8 | last meaningful line 0.2 h ago (450/450 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2408517 | slw_fe_v1 | 5_2_route | 16.4 | drt_violations best 9253 last 9253 rows 3 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | 5_2_route | 12.0 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-1019838 | slw_sc_v1 | postcts_gate_TT | 5.7 | last meaningful line 0.1 h ago (2194/2194 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3868961 | slw_sc_v1 | 5_2_route | 9.0 | last meaningful line 0.1 h ago (271/272 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v2__clf4365a62-3806895 | slw_st_a_v2 | 2_1_floorplan | 0.1 | repair_Viol best 2348 last 2348 rows 638 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | prd-eco_20261121_105744_956410-i1-174847 | eco_20261121_105744_956410-i1 | 5_2_route | 2.8 | drt_violations best 7 last 7 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_123328_2268168-i1-2396653 | eco_20261121_123328_2268168-i1 | 5_1_grt | 0.8 | last meaningful line 0.3 h ago (236/1282 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_124930_2356681-i1-2553432 | eco_20261121_124930_2356681-i1 | 5_1_grt | 0.6 | last meaningful line 0.2 h ago (234/321 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_185640_2629364-i1t-3849783 | eco_20261121_185640_2629364-i1t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-fin-3731479 | fin | 6_report | 0.3 | last meaningful line 0.1 h ago (621/621 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q11-3840796 | cbf_q11 | 5_1_grt | 5.6 | last meaningful line 2.5 h ago (25/25 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hg_v1p2-672395 | kv3_hg_v1p2 | 4_1_cts | 0.6 | last meaningful line 0.2 h ago (3898/3898 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | 5_1_grt | 5.5 | last meaningful line 0.0 h ago (189/194 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2969215 | sle_hc0 | 5_1_grt | 6.3 | last meaningful line 0.1 h ago (137/137 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve230954c-1731757 | sle_hc1 | 5_2_route | 12.7 | drt_violations best 144620 last 144620 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t37-1519314 | slice_station__t37 | 3_1_place_gp_skip_io | 0.1 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t45-1496004 | slice_station__t45 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.8127 last 0.8127 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slice_station__t51-1618628 | slice_station__t51 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v3-1709520 | slw_fw_v3 | reg_fanout | 0.0 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-slw_sc_v2-3695652 | slw_sc_v2 | 5_1_grt | 5.8 | repair_TNS best 1128.96 last 1128.96 rows 7 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 6.6 | drt_violations best 65226 last 65226 rows 5 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | fefw-r3-lec-sefe | fefw-r3-lec-sefe | - | 0.3 |  | NO-DATA: no log found |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 4.0 | last meaningful line 2.3 h ago (622/622 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_100942_929932-i2t-68122 | eco_20261121_100942_929932-i2t | 5_2_route | 1.2 | last meaningful line 0.3 h ago (133/133 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_184012_3245689-i1-2542120 | eco_20261121_184012_3245689-i1 | 5_2_route | 3.1 | drt_violations best 11 last 11 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_193535_3253336-i1-3373883 | eco_20261121_193535_3253336-i1 | 5_2_route | 2.2 | last meaningful line 0.3 h ago (276/277 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | resign-resign_je-73056ffceee0b348-lec | resign-resign_je-73056ffceee0b348-lec | gold.ys | 0.4 | last meaningful line 0.3 h ago (10019/10019 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | so_616824_ff_34594 | so_616824_ff_34594 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (719/719 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | so_616824_tt_34594 | so_616824_tt_34594 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (719/719 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q00__cld7bf7197-3404310 | cbn_q00 | pregrt_ff_hold | 4.5 | repair_Violations best 45092 last 45106 rows 66 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | 5_1_grt | 6.5 | last meaningful line 0.0 h ago (202/203 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_1_grt | 6.5 | last meaningful line 4.3 h ago (39/39 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_mu_LP__t2-3534677 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 7.4 | last meaningful line 0.1 h ago (199/203 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-3144441 | kv3_hg_v1p2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t14-3301476 | serdes__t14 | 5_1_grt | 4.6 | repair_TNS best 350.383 last 350.383 rows 10 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-3022331 | sle_ctl | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (8053/8053 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa-1023417 | sle_hc0 | 6_report | 13.3 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3985339 | sle_hc2 | 5_2_route | 11.3 | drt_violations best 83965 last 83965 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-1899674 | slw_fe_v1 | 5_2_route | 12.7 | last meaningful line 0.3 h ago (274/275 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-850569 | slw_fe_v1 | 5_2_route | 13.5 | drt_violations best 14745 last 14745 rows 2 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-2906124 | slw_hc1 | 5_2_route | 15.6 | drt_violations best 14489 last 14489 rows 2 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 5.9 | last meaningful line 0.2 h ago (262/263 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-1964882 | slw_su_l0 | 5_2_route | 5.8 | drt_violations best 80394 last 80394 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 5.7 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | prd-eco_20261121_214321_3818039-i1-1999865 | eco_20261121_214321_3818039-i1 | 5_2_route | 1.8 | drt_violations best 6 last 6 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | so_3364965_ff_17103 | so_3364965_ff_17103 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | so_3364965_tt_17103 | so_3364965_tt_17103 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-hd_ctl-282607 | hd_ctl | 5_2_route | 0.5 | last meaningful line 0.0 h ago (262/263 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_mesh-3170867 | hd_mesh | pregrt_ff_hold | 2.3 | repair_TNS best 384532 last 384532 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | otc-3085280-30126 | 3085280 | - | 18.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 18.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 18.3 |  | NO-DATA: no log found |  |
| epyc9 | prd-count-p1_bc-1219117 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (103/103 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-count-p1_bc-3564572 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (496/496 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | so_373497_ff_50897 | so_373497_ff_50897 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc9 | so_373497_tt_50897 | so_373497_tt_50897 | signoff | 0.4 |  | NO-DATA: empty log |  |
| intel1 | prd-eco_20261120_192428_3309571-i2-437055 | eco_20261120_192428_3309571-i2 | 5_2_route | 2.4 | drt_violations best 12 last 12 rows 4 | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i1-1189865 | eco_20261121_082001_3216437-i1 | 5_2_route | 1.5 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1t-203702 | eco_20261121_161716_4143584-i1t | 5_2_route | 2.7 | drt_violations best 98048 last 98048 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_1_grt | 1.1 | last meaningful line 0.5 h ago (209/217 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | so_2079901_ff_2567 | so_2079901_ff_2567 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | so_2079901_tt_2567 | so_2079901_tt_2567 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (1028/1028 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | so_2241325_ff_52557 | so_2241325_ff_52557 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (835/835 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | so_2241325_tt_52557 | so_2241325_tt_52557 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (835/835 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | so_2299516_ff_56902 | so_2299516_ff_56902 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | so_2299516_tt_56902 | so_2299516_tt_56902 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4007898 | col_h9_r1__t1 | 5_1_grt | 3.7 | last meaningful line 1.8 h ago (40/40 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3132815 | coll_ftm | 5_1_grt | 0.7 | repair_TNS best 17.138 last 17.138 rows 4 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-3496050 | hd_turn_a | 5_2_route | 0.5 | drt_violations best 4744 last 4744 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-kv3_hgi_v2__cle0015330-483554 | kv3_hgi_v2 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.1 h ago (478/478 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_hgi_v3-440043 | kv3_hgi_v3 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_cor-137854 | kv3_io_cor | 3_3_place_gp | 0.4 | overflow best 0.4026 last 0.4026 rows 25 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-sle_fw_v1__clf58b4dfb-52899 | sle_fw_v1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.8795 last 0.8795 rows 25 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-544842 | sle_fw_v2 | 2_1_floorplan | 0.2 | last meaningful line 0.1 h ago (85/85 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-82779 | sle_hc1 | 3_3_place_gp | 0.4 | overflow best 0.644 last 0.644 rows 29 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-sle_stm_v1__clbe630b9c-319854 | sle_stm_v1 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl55be2264-59788 | sle_stm_v2 | 3_3_place_gp | 0.4 | overflow best 0.372 last 0.372 rows 23 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-sle_stm_v2__cl7b3062fa-389744 | sle_stm_v2 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-3517303 | slice_station__t12 | postcts_gate_FF | 0.5 | last meaningful line 0.0 h ago (163/163 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-106360 | slw_fe_v1 | 3_3_place_gp | 0.4 | overflow best 0.5196 last 0.5196 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-170626 | slw_fw_v1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.9984 last 0.9984 rows 10 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slw_st_a_v2__cl9f076a5c-386692 | slw_st_a_v2 | 3_3_place_gp | 0.2 | overflow best 0.5513 last 0.5513 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-slw_st_b_v1__cle6023ec2-332407 | slw_st_b_v1 | 2_1_floorplan | 0.3 | last meaningful line 0.0 h ago (83/83 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-252358 | slw_st_b_v2 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_stm_v2__cl1ca9c415-555114 | slw_stm_v2 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (605/605 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-tt_ctlm-393296 | tt_ctlm | 3_3_place_gp | 0.2 | overflow best 0.8361 last 0.8361 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | otc-2434779-27076 | 2434779 | gate.ys | 2.8 | last meaningful line 2.7 h ago (51328/51328 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel2 | otc-2600775-23472 | 2600775 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | otc-348114-24792 | 348114 | 3_3_place_gp | 0.3 | overflow best 0.3696 last 0.3868 rows 28 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | prd-eco_20261121_115902_173230-i1-2657830 | eco_20261121_115902_173230-i1 | 5_2_route | 2.7 | drt_violations best 51 last 51 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 35.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 40.2 | last meaningful line 0.5 h ago (1548/1548 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | pregrt_ff_hold | 7.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-native59-3868183 | native59 | pregrt_ff_hold | 9.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_2_route | 25.8 | drt_violations best 9327 last 18160 rows 19 | before-window best 9551, window best 9327 | PROGRESS: drt_violations improved 2.3 % in window |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 16.1 | drt_violations best 1 last 12 rows 51 | before-window best 3, window best 1 | PROGRESS: drt_violations improved 66.7 % in window |  |
| epyc2 | prd-eco_20261121_070700_2142563-i2t-3221691 | eco_20261121_070700_2142563-i2t | 5_1_grt | 0.3 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-3504337 | sle_hc1 | pregrt_ff_hold | 5.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3669665 | slw_st_b_v1 | pregrt_ff_hold | 5.8 | repair_Violations best 0 last 0 rows 19 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 8.0 | drt_violations best 655 last 655 rows 24 | before-window best 194272, window best 655 | PROGRESS: drt_violations improved 99.7 % in window |  |
| intel1 | prd-eco_20261121_075836_1991905-i1t-1821063 | eco_20261121_075836_1991905-i1t | 5_2_route | 11.0 | drt_violations best 91 last 91 rows 14 | before-window best 190712, window best 91 | PROGRESS: drt_violations improved 100.0 % in window |  |
