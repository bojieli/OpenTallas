# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 17:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 1, 'CANCEL-NOW': 3, 'GRT-LABEL': 37, 'YOUNG': 76, 'NO-DATA': 11, 'KEEP': 1, 'EXCLUDED': 2, 'PROGRESS': 23}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | tt_setup_repair_grt | 32.9 | repair_Violations best 256 last 256 rows 19 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -581.92 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 46.3 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 46 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel1 | dpkit-sle_ctl__cl67434795-622153 | sle_ctl | pregrt_ff_hold | 15.5 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORTED (cancel next pass) |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-2950576 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | dump_placed | 0.5 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-3920455 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 3_3_place_gp | 0.2 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-3920455-lec | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | lec | 0.0 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-kv3_hgi_v8-3126306 | kv3_hgi_v8 | 5_1_grt | 12.8 | grt rounds 4 overflow 5:37484 -> 10:8165 -> 15:5582 -> 20:4797 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 31.4 | grt rounds 4 overflow 5:62850 -> 10:60456 -> 15:49678 -> 20:49999 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 31.4 | grt rounds 4 overflow 5:56489 -> 10:43484 -> 15:40478 -> 20:43412 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 45.8 | grt rounds 4 overflow 5:9510 -> 10:5086 -> 15:3245 -> 20:2874 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 35.3 | grt rounds 4 overflow 5:54036 -> 10:38366 -> 15:34625 -> 20:37416 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-248840 | sle_st_a_v1 | 5_1_grt | 4.3 | grt rounds 2 overflow 5:3539 -> 10:2906 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-427216 | sle_st_a_v1 | 5_1_grt | 4.1 | grt rounds 2 overflow 5:4512 -> 10:1167 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-254386 | sle_st_a_v2 | 5_1_grt | 4.2 | grt rounds 2 overflow 5:12031 -> 10:4878 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-425101 | sle_st_a_v2 | 5_1_grt | 4.1 | grt rounds 2 overflow 5:13907 -> 10:5441 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-844610 | slw_st_a_v1 | 5_1_grt | 3.8 | grt rounds 2 overflow 5:3827 -> 10:2935 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 25.2 | grt rounds 3 overflow 5:76845 -> 10:72294 -> 15:58855 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 30.2 | grt rounds 3 overflow 5:61525 -> 10:66596 -> 15:69180 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 19.6 | grt rounds 3 overflow 5:50395 -> 10:49359 -> 15:39411 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 19.6 | grt rounds 3 overflow 5:50621 -> 10:49445 -> 15:39498 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 29.3 | grt rounds 3 overflow 5:46939 -> 10:49559 -> 15:42999 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 17.0 | grt rounds 3 overflow 5:79338 -> 10:74939 -> 15:54793 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 25.3 | grt rounds 4 overflow 5:95535 -> 10:71003 -> 15:50597 -> 20:56554 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 19.1 | grt rounds 4 overflow 5:73809 -> 10:69973 -> 15:51390 -> 20:58440 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 20.8 | grt rounds 4 overflow 5:44451 -> 10:39064 -> 15:36370 -> 20:37882 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 20.8 | grt rounds 4 overflow 5:41833 -> 10:36208 -> 15:31830 -> 20:31076 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_st_a_v2__pv4242de79-2391789 | sle_st_a_v2 | 5_1_grt | 4.5 | grt rounds 2 overflow 5:21672 -> 10:8153 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hgi_v2__cl2862d491-3732038 | kv3_hgi_v2 | 5_1_grt | 9.7 | grt rounds 2 overflow 5:72991 -> 10:37675 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 20.4 | grt rounds 4 overflow 5:19113 -> 10:12610 -> 15:11259 -> 20:10290 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_1_grt | 4.1 | grt rounds 2 overflow 5:22926 -> 10:4651 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_1_grt | 3.9 | grt rounds 2 overflow 5:3304 -> 10:2843 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hgi_v8-3224135 | kv3_hgi_v8 | 5_1_grt | 13.9 | grt rounds 5 overflow 5:37484 -> 10:8165 -> 15:5582 -> 20:4765 -> 25:4799 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 33.3 | grt rounds 4 overflow 5:34386 -> 10:12131 -> 15:8208 -> 20:7819 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 44.0 | grt rounds 6 overflow 5:17310 -> 10:19233 -> 15:11889 -> 20:10171 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 44.3 | grt rounds 5 overflow 5:32681 -> 10:30734 -> 15:24645 -> 20:22699 -> 25:31808 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 5_1_grt | 21.3 | grt rounds 5 overflow 5:54170 -> 10:7759 -> 15:5073 -> 20:4181 -> 25:5669 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 26.8 | grt rounds 6 overflow 5:40892 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: overflow 13501 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 21.8 | grt rounds 4 overflow 5:36357 -> 10:30023 -> 15:24172 -> 20:21320 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 43.1 | grt rounds 4 overflow 5:56283 -> 10:53405 -> 15:50242 -> 20:55216 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 38.1 | grt rounds 3 overflow 5:59246 -> 10:46138 -> 15:53864 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 38.1 | grt rounds 3 overflow 5:60515 -> 10:47029 -> 15:53055 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 38.3 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-slice_station__t24__cl66b71008-2281540 | slice_station__t24 | 5_1_grt | 0.9 | grt rounds 4 overflow 5:4098 -> 10:3741 -> 15:3172 -> 20:3097 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_lep0N-1588394 | hd_lep0N | 5_1_grt | 11.0 | last meaningful line 0.8 h ago (199/204 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-22377 | hd_lep0N | 4_2_tapbal_grt | 9.4 | last meaningful line 4.8 h ago (48/58 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t4-293755 | serdes__t4 | 5_2_route | 6.5 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t36-3668002 | slice_station__t36 | 5_2_route | 7.1 | drt_violations best 46297 last 46297 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t37-173045 | slice_station__t37 | 5_2_route | 6.6 | drt_violations best 30922 last 30922 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v3-1328903 | slw_fw_v3 | generate_abstract | 13.9 | last meaningful line 0.4 h ago (1030/1030 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | otc-1366343-2403 | 1366343 | equiv_reset_residual_depth | 0.2 | last meaningful line 0.1 h ago (790761/790761 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1t-894339 | eco_20261121_154936_3396612-i1t | 5_2_route | 8.9 | drt_violations best 108921 last 108921 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_184648_4039100-i1-3762453 | eco_20261121_184648_4039100-i1 | 5_2_route | 1.8 | last meaningful line 0.1 h ago (264/265 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_203102_3392434-i1t-646001 | eco_20261121_203102_3392434-i1t | 5_2_route | 4.2 | last meaningful line 0.2 h ago (289/290 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q01_s2-921403 | cbf_q01_s2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5328/5328 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 3_3_place_gp | 8.4 | overflow best 0.0992 last 0.0992 rows 45 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | 4_1_cts | 5.4 | last meaningful line 1.0 h ago (7577/7577 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2374083 | sle_hc1 | 5_2_route | 14.5 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-425190 | sle_su_l1 | 5_1_grt | 4.1 | last meaningful line 1.5 h ago (221/886 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t36-3125329 | slice_station__t36 | 5_2_route | 10.8 | drt_violations best 45900 last 45900 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t51-342871 | slice_station__t51 | 5_1_grt | 4.2 | last meaningful line 2.0 h ago (215/705 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2408517 | slw_fe_v1 | 5_2_route | 14.4 | drt_violations best 96105 last 96105 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | postcts_gate_TT | 10.0 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-1019838 | slw_sc_v1 | 5_1_grt | 3.7 | repair_Remaining best 369310 last 369310 rows 70 | YOUNG: stage 0.9 h < 1 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3868961 | slw_sc_v1 | postcts_gate_TT | 7.0 | last meaningful line 0.1 h ago (988/988 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2420111 | slw_st_b_v2 | 5_2_route | 14.4 | drt_violations best 9878 last 9878 rows 2 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | otc-1199295-32620 | 1199295 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | otc-3002702-20247 | 3002702 | - | 1.9 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261121_070700_2142563-i1-4024972 | eco_20261121_070700_2142563-i1 | 5_2_route | 4.5 | drt_violations best 38 last 38 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_080323_3018643-i1-1109108 | eco_20261121_080323_3018643-i1 | 5_2_route | 3.6 | drt_violations best 13 last 13 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_102155_957464-i1-3731479 | eco_20261121_102155_957464-i1 | 5_2_route | 1.4 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_105744_956410-i1-174847 | eco_20261121_105744_956410-i1 | 5_1_grt | 0.8 | last meaningful line 0.3 h ago (239/1339 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_123328_2268168-i1t-4175816 | eco_20261121_123328_2268168-i1t | 5_2_route | 4.4 | drt_violations best 14003 last 14003 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_124930_2356681-i1t-415105 | eco_20261121_124930_2356681-i1t | 5_2_route | 4.1 | drt_violations best 14226 last 14226 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q11-3840796 | cbf_q11 | 5_1_grt | 3.6 | last meaningful line 0.5 h ago (25/25 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | 4_1_cts | 2.9 | last meaningful line 0.1 h ago (9084/9084 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve230954c-1731757 | sle_hc1 | postcts_gate_FF | 10.7 | last meaningful line 0.0 h ago (822/822 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3695652 | slw_sc_v2 | 5_1_grt | 3.8 | last meaningful line 0.7 h ago (288/866 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 4.6 | drt_violations best 181727 last 181727 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-svc_hi_dsdv_svc_rs__t4-3500692 | svc_hi_dsdv_svc_rs__t4 | 2_4_floorplan_pdn | 0.0 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | eco-abs-3344243 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1024/1024 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | eco-abs-3491304 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (634/634 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 2.0 | last meaningful line 0.3 h ago (622/622 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_173326_4009105-i1-295057 | eco_20261121_173326_4009105-i1 | 5_2_route | 3.1 | drt_violations best 24 last 24 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_184012_3245689-i1-2542120 | eco_20261121_184012_3245689-i1 | 5_1_grt | 1.1 | last meaningful line 0.6 h ago (236/1371 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_193535_3253336-i1-3373883 | eco_20261121_193535_3253336-i1 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | so_3463672_ff_28626 | so_3463672_ff_28626 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | so_3463672_tt_28626 | so_3463672_tt_28626 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | 5_1_grt | 4.7 | last meaningful line 3.0 h ago (39/39 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_1_grt | 4.7 | last meaningful line 2.5 h ago (39/39 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-glue-504992 | glue | postcts_gate_FF | 8.9 | last meaningful line 0.1 h ago (27/27 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa-1023417 | sle_hc0 | 5_2_route | 11.6 | drt_violations best 93499 last 93499 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3985339 | sle_hc2 | postcts_gate_FF | 9.5 | last meaningful line -0.0 h ago (19984/19984 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-1013642 | sle_hc2 | 5_2_route | 11.6 | drt_violations best 85433 last 85433 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-1899674 | slw_fe_v1 | postcts_gate_FF | 11.0 | last meaningful line 0.0 h ago (1829/1829 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-850569 | slw_fe_v1 | 5_2_route | 11.7 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-2906124 | slw_hc1 | 5_2_route | 13.9 | last meaningful line 0.1 h ago (280/281 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1012001 | slw_hc3 | 6_report | 11.6 | last meaningful line 0.0 h ago (267/267 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-1964882 | slw_su_l0 | postcts_gate_TT | 4.1 | last meaningful line -0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-1918520-32288 | 1918520 | 2_1_floorplan | 0.1 | repair_Viol best 1204 last 1204 rows 1078 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | otc-3509414-20478 | 3509414 | gate.ys | 2.7 | last meaningful line 2.5 h ago (51328/51328 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261121_214321_3818039-i1-1999865 | eco_20261121_214321_3818039-i1 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (7/7 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | so_1945331_ff_85475 | so_1945331_ff_85475 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | so_1945331_tt_85475 | so_1945331_tt_85475 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-hd_mesh-3170867 | hd_mesh | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (4889/4889 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2616668 | sle_hc1 | 5_2_route | 11.3 | drt_violations best 100102 last 100102 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | eco-abs-3343305 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (623/623 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-2984693-16614 | 2984693 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-3085280-30126 | 3085280 | - | 16.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 16.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 16.3 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261121_070035_1645318-i2t-1219117 | eco_20261121_070035_1645318-i2t | 5_2_route | 2.7 | drt_violations best 73831 last 73831 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_143815_74711-i2r-2484763 | eco_20261121_143815_74711-i2r | 5_2_route | 1.2 | last meaningful line 0.1 h ago (261/262 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 6.0 | drt_violations best 1022 last 1022 rows 19 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_195859_2616880-i2-3151974 | eco_20261121_195859_2616880-i2 | 5_1_grt | 0.3 | last meaningful line 0.2 h ago (229/1719 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-2204474 | slw_st_b_v1 | 5_2_route | 14.4 | drt_violations best 92995 last 92995 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | otc-3999731-13707 | 3999731 | 3_3_place_gp | 1.2 | overflow best 0.0993 last 0.0997 rows 434 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i2-437055 | eco_20261120_192428_3309571-i2 | 5_2_route | 0.4 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1t-203702 | eco_20261121_161716_4143584-i1t | 5_2_route | 0.7 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | so_624369_ff_28506 | so_624369_ff_28506 | signoff | 0.2 |  | NO-DATA: empty log |  |
| intel1 | so_624369_tt_28506 | so_624369_tt_28506 | signoff | 0.2 |  | NO-DATA: empty log |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4007898 | col_h9_r1__t1 | pregrt_ff_hold | 1.7 | repair_Violations best 46 last 46 rows 14 | YOUNG: stage 1.0 h < 1 h |  |
| intel2 | dpkit-coll_ftm-845526 | coll_ftm | 5_2_route | 1.5 | last meaningful line 0.1 h ago (238/239 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-840680 | kv3_io_ft | generate_abstract | 1.5 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-2578021 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (224/225 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t24__cl66b71008-14958 | slice_station__t24 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t24__cl66b71008-62102 | slice_station__t24 | 3_3_place_gp | 0.0 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | kvcore-ot_nhb_zh__151.2x151.2_ahubrecover_-2738349 | kvcore-ot_nhb_zh__151.2x151.2_ahubrecover_ | 5_2_route | 0.6 | drt_violations best 29307 last 29307 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | kvcore-ot_qkh_recip_leaf__216x216_ahubrecover_-3813197 | kvcore-ot_qkh_recip_leaf__216x216_ahubrecover_ | 5_2_route | 0.3 | drt_violations best 9545 last 9545 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | otc-2434779-27076 | 2434779 | gate.ys | 0.8 | last meaningful line 0.8 h ago (51328/51328 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | prd-eco_20261121_115902_173230-i1-2657830 | eco_20261121_115902_173230-i1 | 5_1_grt | 0.7 | last meaningful line 0.2 h ago (231/1259 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 33.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-eco1-i1-1617813 | eco1-i1 | 5_2_route | 4.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-1714380 | eco1-i1 | 5_2_route | 4.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_2_route | 21.4 | drt_violations best 10168 last 22918 rows 19 | before-window best 10756, window best 10168 | PROGRESS: drt_violations improved 5.5 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 38.2 | last meaningful line 0.1 h ago (1503/1503 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-2629912 | col_h9_r0_p2__t1 | 5_2_route | 14.3 | drt_violations best 33 last 33 rows 32 | before-window best 135164, window best 33 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc2 | dpkit-native59-3868183 | native59 | pregrt_ff_hold | 7.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_2_route | 23.8 | drt_violations best 9327 last 39114 rows 18 | before-window best 9939, window best 9327 | PROGRESS: drt_violations improved 6.2 % in window |  |
| epyc2 | prd-eco_20261120_170022_4017640-i2t-2328774 | eco_20261120_170022_4017640-i2t | 5_2_route | 11.4 | drt_violations best 98 last 98 rows 12 | before-window best 1667, window best 98 | PROGRESS: drt_violations improved 94.1 % in window |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 14.1 | drt_violations best 1 last 12 rows 51 | before-window best 3, window best 1 | PROGRESS: drt_violations improved 66.7 % in window |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-582858 | cbn_q01 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2969215 | sle_hc0 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-3504337 | sle_hc1 | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3669665 | slw_st_b_v1 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbn_q00__cld7bf7197-3404310 | cbn_q00 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | 5_2_route | 20.4 | drt_violations best 27 last 27 rows 50 | before-window best 29, window best 27 | PROGRESS: drt_violations improved 6.9 % in window |  |
| epyc8 | dpkit-dsdv_slice_lepe_mu_LP__t2-3534677 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 5.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-serdes__t14-3301476 | serdes__t14 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-3274788 | serdes__t1 | 5_2_route | 13.6 | drt_violations best 17728 last 17728 rows 2 | before-window best 114810, window best 17728 | PROGRESS: drt_violations improved 84.6 % in window |  |
| epyc9 | dpkit-hd_ctl-2344011 | hd_ctl | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | 5_2_route | 21.1 | drt_violations best 16 last 16 rows 59 | before-window best 203629, window best 16 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | otc-3352679-20733 | 3352679 | 4_1_cts | 1.9 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | prd-eco_20261121_075836_1991905-i1t-1821063 | eco_20261121_075836_1991905-i1t | 5_2_route | 9.0 | drt_violations best 4486 last 4486 rows 10 | before-window best 190712, window best 4486 | PROGRESS: drt_violations improved 97.6 % in window |  |
| intel1 | prd-eco_20261121_082001_3216437-i1t-2148021 | eco_20261121_082001_3216437-i1t | 5_2_route | 8.6 | drt_violations best 38 last 38 rows 14 | before-window best 185697, window best 38 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel2 | otc-3988485-11221 | 3988485 | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
