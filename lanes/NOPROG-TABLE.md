# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 16:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 3, 'NO-PROGRESS': 1, 'CANCEL-NOW': 1, 'GRT-LABEL': 40, 'YOUNG': 89, 'NO-DATA': 5, 'KEEP': 1, 'EXCLUDED': 3, 'PROGRESS': 26}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 32.1 | grt rounds 6 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -2893.36 ps (< -300, gate TT >= -42); job age 3 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 45.6 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 45 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc2 | dpkit-kv3_hgi_v5-244656 | kv3_hgi_v5 | pregrt_ff_hold | 3.3 | repair_TNS best 272670 last 272670 rows 1 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -766.50 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_2_route | 24.0 | drt_violations best 13126 last 24036 rows 19 | before-window best 13155, window best 13126 | NO-PROGRESS: drt_violations best 13126 vs 13155 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-1180933 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 3_5_place_dp | 0.5 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-kv3_hgi_v8-3126306 | kv3_hgi_v8 | 5_1_grt | 12.1 | grt rounds 4 overflow 5:37484 -> 10:9376 -> 15:6005 -> 20:4797 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t39-243585 | ot_s81sl_leaf__t39 | 5_1_grt | 5.8 | grt rounds 2 overflow 5:179 -> 10:39 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 30.7 | grt rounds 3 overflow 5:62850 -> 10:60456 -> 15:49678 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 30.6 | grt rounds 4 overflow 5:56489 -> 10:43484 -> 15:40478 -> 20:43412 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 45.1 | grt rounds 4 overflow 5:9510 -> 10:5086 -> 15:3245 -> 20:2874 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-hd_mesh-2472048 | hd_mesh | 5_1_grt | 13.4 | grt rounds 6 overflow 5:638 -> 10:126 -> 15:54 -> 20:54 -> 25:52 -> 30:50 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 34.3 | grt rounds 4 overflow 5:54036 -> 10:38366 -> 15:34597 -> 20:37416 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-248840 | sle_st_a_v1 | 5_1_grt | 3.3 | grt rounds 2 overflow 5:3539 -> 10:2906 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-427216 | sle_st_a_v1 | 5_1_grt | 3.1 | grt rounds 2 overflow 5:4512 -> 10:1167 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-254386 | sle_st_a_v2 | 5_1_grt | 3.2 | grt rounds 2 overflow 5:12031 -> 10:4878 | GRT-LABEL: DESIGN-FAIL: overflow 4878 at round 10 > 1000 |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-425101 | sle_st_a_v2 | 5_1_grt | 3.1 | grt rounds 2 overflow 5:13907 -> 10:5441 | GRT-LABEL: DESIGN-FAIL: overflow 5441 at round 10 > 1000 |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-844610 | slw_st_a_v1 | 5_1_grt | 2.8 | grt rounds 2 overflow 5:3827 -> 10:2935 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-bk_sel__t2-3723154 | bk_sel__t2 | 5_1_grt | 3.0 | grt rounds 2 overflow 5:79017 -> 10:17912 | GRT-LABEL: DESIGN-FAIL: overflow 17912 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 24.5 | grt rounds 3 overflow 5:76845 -> 10:71866 -> 15:58855 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 29.4 | grt rounds 3 overflow 5:61320 -> 10:66596 -> 15:69180 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 18.8 | grt rounds 3 overflow 5:50395 -> 10:49359 -> 15:39411 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 18.8 | grt rounds 3 overflow 5:50621 -> 10:49445 -> 15:39498 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 28.6 | grt rounds 3 overflow 5:46939 -> 10:49559 -> 15:43107 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 16.3 | grt rounds 3 overflow 5:79338 -> 10:74939 -> 15:54793 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 24.5 | grt rounds 4 overflow 5:71545 -> 10:71003 -> 15:50597 -> 20:56554 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 18.3 | grt rounds 3 overflow 5:73809 -> 10:69973 -> 15:51390 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 20.1 | grt rounds 4 overflow 5:42922 -> 10:39064 -> 15:36370 -> 20:37882 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 20.0 | grt rounds 4 overflow 5:41833 -> 10:36208 -> 15:31830 -> 20:31076 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_st_a_v2__pv4242de79-2391789 | sle_st_a_v2 | 5_1_grt | 3.8 | grt rounds 2 overflow 5:21672 -> 10:8153 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hgi_v2__cl2862d491-3732038 | kv3_hgi_v2 | 5_1_grt | 8.7 | grt rounds 2 overflow 5:72991 -> 10:37675 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 19.4 | grt rounds 4 overflow 5:19113 -> 10:12610 -> 15:11259 -> 20:10290 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_1_grt | 3.1 | grt rounds 2 overflow 5:22926 -> 10:4651 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-1897237 | slw_st_a_v2 | 5_1_grt | 3.1 | grt rounds 2 overflow 5:103 -> 10:56 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_1_grt | 2.9 | grt rounds 2 overflow 5:3304 -> 10:2843 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hgi_v8-3224135 | kv3_hgi_v8 | 5_1_grt | 12.9 | grt rounds 4 overflow 5:37484 -> 10:8165 -> 15:5582 -> 20:4765 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 32.3 | grt rounds 4 overflow 5:34386 -> 10:12131 -> 15:8921 -> 20:7819 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 43.0 | grt rounds 6 overflow 5:18899 -> 10:19233 -> 15:11889 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 43.3 | grt rounds 5 overflow 5:34987 -> 10:28632 -> 15:24645 -> 20:22699 -> 25:31808 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 5_1_grt | 20.3 | grt rounds 5 overflow 5:54170 -> 10:7759 -> 15:5073 -> 20:4181 -> 25:5669 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 25.8 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 20.8 | grt rounds 4 overflow 5:36357 -> 10:30023 -> 15:24310 -> 20:21320 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 42.1 | grt rounds 4 overflow 5:56283 -> 10:53405 -> 15:50242 -> 20:55216 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 37.4 | grt rounds 3 overflow 5:59246 -> 10:46138 -> 15:53864 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 37.4 | grt rounds 3 overflow 5:60515 -> 10:47029 -> 15:53055 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 37.6 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_lep0N-1588394 | hd_lep0N | 5_1_grt | 10.2 | last meaningful line 0.1 h ago (199/200 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-22377 | hd_lep0N | 4_2_tapbal_grt | 8.6 | last meaningful line 4.0 h ago (48/57 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t4-293755 | serdes__t4 | postcts_gate_TT | 5.8 | last meaningful line 0.0 h ago (475/475 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t36-3668002 | slice_station__t36 | 5_2_route | 6.3 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t37-173045 | slice_station__t37 | 5_2_route | 5.8 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v3-1328903 | slw_fw_v3 | 6_report | 13.2 | last meaningful line 0.2 h ago (1071/1071 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1t-894339 | eco_20261121_154936_3396612-i1t | 5_2_route | 8.1 | drt_violations best 108921 last 108921 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_184648_4039100-i1-3762453 | eco_20261121_184648_4039100-i1 | 5_1_grt | 1.1 | last meaningful line 0.7 h ago (234/1373 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_203102_3392434-i1t-646001 | eco_20261121_203102_3392434-i1t | 5_2_route | 3.4 | last meaningful line 0.1 h ago (283/284 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q01_s2-3354717 | cbf_q01_s2 | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (5338/5338 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q01_s2-4094513 | cbf_q01_s2 | 3_3_place_gp | 0.1 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-2629912 | col_h9_r0_p2__t1 | 5_2_route | 13.3 | drt_violations best 13607 last 13607 rows 3 | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 3_3_place_gp | 7.4 | overflow best 0.0992 last 0.0992 rows 45 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | 4_1_cts | 4.4 | last meaningful line 0.2 h ago (7577/7577 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-native59-3868183 | native59 | pregrt_ff_hold | 6.0 | repair_TNS best 8684.22 last 8684.22 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2374083 | sle_hc1 | 5_2_route | 13.5 | last meaningful line 0.1 h ago (264/264 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-425190 | sle_su_l1 | 5_1_grt | 3.1 | repair_TNS best 267.818 last 267.818 rows 3 | YOUNG: stage 0.9 h < 1 h |  |
| epyc2 | dpkit-slice_station__t36-3125329 | slice_station__t36 | 5_2_route | 9.8 | drt_violations best 45900 last 45900 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2408517 | slw_fe_v1 | 5_2_route | 13.4 | last meaningful line 0.3 h ago (280/281 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | 5_1_grt | 9.0 | last meaningful line 2.5 h ago (217/1466 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2420111 | slw_st_b_v2 | 5_2_route | 13.4 | drt_violations best 84153 last 84153 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | otc-3002702-20247 | 3002702 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261121_070700_2142563-i1-4024972 | eco_20261121_070700_2142563-i1 | 5_2_route | 3.5 | drt_violations best 38 last 38 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_080323_3018643-i1-1109108 | eco_20261121_080323_3018643-i1 | 5_2_route | 2.6 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_102155_957464-i1-3731479 | eco_20261121_102155_957464-i1 | 5_1_grt | 0.4 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_123328_2268168-i1t-4175816 | eco_20261121_123328_2268168-i1t | 5_2_route | 3.4 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_124930_2356681-i1t-415105 | eco_20261121_124930_2356681-i1t | 5_2_route | 3.1 | last meaningful line 0.3 h ago (276/277 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | prd-fin-1036390 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (748/748 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q11-3840796 | cbf_q11 | pregrt_ff_hold | 2.9 | repair_Violations best 12657 last 12657 rows 12 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-993515 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 6.9 | last meaningful line 0.1 h ago (149/149 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | 4_1_cts | 2.2 | last meaningful line 0.3 h ago (9062/9062 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | pregrt_ff_hold | 2.8 | repair_TNS best 50070.9 last 50070.9 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve230954c-1731757 | sle_hc1 | postcts_gate_TT | 10.0 | last meaningful line 0.1 h ago (390/390 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cle683a076-3820341 | slw_hc1 | 5_1_grt | 2.9 | last meaningful line 0.1 h ago (136/136 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3695652 | slw_sc_v2 | 5_1_grt | 3.0 | last meaningful line 0.3 h ago (196/205 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 3.9 | last meaningful line 0.1 h ago (260/261 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 1.2 | last meaningful line 1.0 h ago (310/310 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_100942_929932-i1-3347652 | eco_20261121_100942_929932-i1 | 5_2_route | 4.8 | drt_violations best 44 last 44 rows 44 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_173326_4009105-i1-295057 | eco_20261121_173326_4009105-i1 | 5_2_route | 2.4 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_184012_3245689-i1-2542120 | eco_20261121_184012_3245689-i1 | 5_1_grt | 0.4 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_203749_4020394-i1-2795396 | eco_20261121_203749_4020394-i1 | 5_2_route | 3.6 | drt_violations best 1 last 1 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-2597778 | col_h9_r0_p2__t1 | 5_1_grt | 2.5 | last meaningful line 0.3 h ago (210/214 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | 5_1_grt | 3.7 | last meaningful line 2.0 h ago (39/39 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_1_grt | 3.7 | last meaningful line 1.5 h ago (39/39 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-glue-504992 | glue | 5_1_grt | 7.9 | last meaningful line 0.3 h ago (222/857 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-3274788 | serdes__t1 | 5_2_route | 12.6 | drt_violations best 114810 last 114810 rows 1 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa-1023417 | sle_hc0 | 5_2_route | 10.6 | last meaningful line 0.0 h ago (263/264 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3985339 | sle_hc2 | postcts_gate_TT | 8.5 | last meaningful line 0.0 h ago (788/788 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-1013642 | sle_hc2 | 5_2_route | 10.6 | last meaningful line 0.2 h ago (265/266 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-1899674 | slw_fe_v1 | postcts_gate_FF | 10.0 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-850569 | slw_fe_v1 | 5_2_route | 10.7 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-2906124 | slw_hc1 | postcts_gate_FF | 12.9 | last meaningful line -0.0 h ago (91786/91786 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1012001 | slw_hc3 | 5_2_route | 10.6 | drt_violations best 73752 last 73752 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-1012945 | slw_hc3 | 5_2_route | 10.6 | drt_violations best 69941 last 69941 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-1964882 | slw_su_l0 | 5_1_grt | 3.1 | last meaningful line 0.2 h ago (228/612 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | otc-3509414-20478 | 3509414 | gate.ys | 1.7 | last meaningful line 1.5 h ago (51328/51328 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261121_214321_3818039-i1t-2911659 | eco_20261121_214321_3818039-i1t | 5_2_route | 2.2 | drt_violations best 40634 last 40634 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-2344011 | hd_ctl | pregrt_ff_hold | 0.3 | repair_TNS best 346383 last 346383 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-kv3_hg-1650521 | kv3_hg | 3_5_place_dp | 1.1 | last meaningful line 0.2 h ago (43/43 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-1513640 | sle_hc0 | generate_abstract | 11.2 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2616668 | sle_hc1 | 5_2_route | 10.3 | last meaningful line 0.1 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | eco-abs-2397520 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.2 h ago (544/544 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | otc-2315854-3380 | 2315854 | 3_3_place_gp | 0.4 | overflow best 0.0993 last 0.0993 rows 43 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | otc-3085280-30126 | 3085280 | - | 15.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 15.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 15.3 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261121_070035_1645318-i2t-1219117 | eco_20261121_070035_1645318-i2t | 5_2_route | 1.7 | last meaningful line 0.2 h ago (282/283 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_143815_74711-i2r-2484763 | eco_20261121_143815_74711-i2r | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 5.0 | drt_violations best 1428 last 1428 rows 16 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_195859_2616880-i2t-2177655 | eco_20261121_195859_2616880-i2t | 5_2_route | 0.5 | last meaningful line 0.0 h ago (253/254 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_201548_1094504-i1-1641941 | eco_20261121_201548_1094504-i1 | 5_2_route | 1.1 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | 5_2_route | 20.3 | drt_violations best 7064 last 7064 rows 3 | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-2204474 | slw_st_b_v1 | 5_2_route | 13.4 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | otc-3999731-13707 | 3999731 | 2_1_floorplan | 0.2 | repair_Viol best 18803 last 18803 rows 832 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | otc-4096985-5573 | 4096985 | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i2t-1252392 | eco_20261120_192428_3309571-i2t | 5_2_route | 3.7 | drt_violations best 21 last 21 rows 12 | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | so_3841414_ff_59953 | so_3841414_ff_59953 | generate_abstract | 0.4 | last meaningful line 0.2 h ago (1029/1029 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | so_3841414_tt_59953 | so_3841414_tt_59953 | generate_abstract | 0.4 | last meaningful line 0.2 h ago (1029/1029 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | so_3941430_ff_30248 | so_3941430_ff_30248 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (524/524 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | so_3941430_tt_30248 | so_3941430_tt_30248 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (524/524 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4007898 | col_h9_r1__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 8448.57 last 8448.57 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-coll_core-1033135 | coll_core | 3_3_place_gp | 0.6 | overflow best 0.2074 last 0.2074 rows 38 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-coll_ftm-845526 | coll_ftm | 5_1_grt | 0.7 | repair_TNS best 17.138 last 17.138 rows 8 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-kv3_io_ft-840680 | kv3_io_ft | 5_2_route | 0.7 | last meaningful line 0.0 h ago (214/215 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t24__cl66b71008-2281540 | slice_station__t24 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (117/117 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | kvcore-ot_nhb_zh__151.2x151.2_ahubrecover_-2332666 | kvcore-ot_nhb_zh__151.2x151.2_ahubrecover_ | 3_3_place_gp | 0.1 | overflow best 0.099 last 0.099 rows 53 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | kvcore-ot_nhb_zh__151.2x151.2_ahubrecover_-2332666-lec | kvcore-ot_nhb_zh__151.2x151.2_ahubrecover_ | lec | 0.1 | LEC last write 0.0 h ago | YOUNG: evidence 0.1 h < 6 h |  |
| intel2 | kvcore-ot_qkh_recip_leaf__216x216_ahubrecover_-2332486-lec | kvcore-ot_qkh_recip_leaf__216x216_ahubrecover_ | lec | 0.1 | LEC last write 0.0 h ago | YOUNG: evidence 0.1 h < 6 h |  |
| intel2 | otc-2434779-27076 | 2434779 | gate.ys | 0.1 | last meaningful line 0.0 h ago (51328/51328 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | otc-2502972-12957 | 2502972 | - | 0.0 |  | NO-DATA: no log found |  |
| intel2 | otc-2524757-7552 | 2524757 | ideal_tt_baseline | 0.0 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | prd-fin-1237159 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (652/652 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | so_2071782_ff_36366 | so_2071782_ff_36366 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (506/506 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | so_2071782_tt_36366 | so_2071782_tt_36366 | generate_abstract | 0.3 | last meaningful line 0.3 h ago (506/506 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 32.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | eco-abs-3985082 | eco-abs | generate_abstract | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-1617813 | eco1-i1 | 5_2_route | 3.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-1714380 | eco1-i1 | 5_2_route | 3.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_2_route | 20.6 | drt_violations best 10168 last 49296 rows 18 | before-window best 11104, window best 10168 | PROGRESS: drt_violations improved 8.4 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 37.2 | last meaningful line 1.1 h ago (1499/1499 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-slice_station__t51-342871 | slice_station__t51 | 5_1_grt | 3.2 | repair_TNS best 0 last 0 rows 19 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-1019838 | slw_sc_v1 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3868961 | slw_sc_v1 | 5_1_grt | 6.0 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_2_route | 22.8 | drt_violations best 9327 last 39114 rows 18 | before-window best 10277, window best 9327 | PROGRESS: drt_violations improved 9.2 % in window |  |
| epyc2 | prd-eco_20261120_170022_4017640-i2t-2328774 | eco_20261120_170022_4017640-i2t | 5_2_route | 10.4 | drt_violations best 98 last 98 rows 12 | before-window best 9846, window best 98 | PROGRESS: drt_violations improved 99.0 % in window |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 13.1 | drt_violations best 1 last 12 rows 51 | before-window best 3, window best 1 | PROGRESS: drt_violations improved 66.7 % in window |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-582858 | cbn_q01 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2969215 | sle_hc0 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-1459492 | sle_hc1 | 5_2_route | 13.6 | drt_violations best 0 last 0 rows 8 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-3504337 | sle_hc1 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3669665 | slw_st_b_v1 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | prd-eco_20261121_193535_3253336-i1t-4078609 | eco_20261121_193535_3253336-i1t | 5_2_route | 4.6 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
| epyc8 | dpkit-cbn_q00__cld7bf7197-3404310 | cbn_q00 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | 5_2_route | 19.4 | drt_violations best 15 last 15 rows 52 | before-window best 17, window best 15 | PROGRESS: drt_violations improved 11.8 % in window |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | 5_2_route | 19.4 | drt_violations best 27 last 27 rows 50 | before-window best 32, window best 27 | PROGRESS: drt_violations improved 15.6 % in window |  |
| epyc8 | dpkit-dsdv_slice_lepe_mu_LP__t2-3534677 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 4.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-serdes__t14-3301476 | serdes__t14 | 4_1_cts | 1.9 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-4146127 | col_h10_r2__t1 | 5_2_route | 12.4 | drt_violations best 0 last 0 rows 12 | PROGRESS: drt_violations reached 0 |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | 5_2_route | 20.1 | drt_violations best 37 last 37 rows 13 | before-window best 203629, window best 37 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-sle_ctl__cl67434795-622153 | sle_ctl | pregrt_ff_hold | 14.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | otc-3352679-20733 | 3352679 | 4_1_cts | 0.9 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | prd-eco_20261121_075836_1991905-i1t-1821063 | eco_20261121_075836_1991905-i1t | 5_2_route | 8.0 | drt_violations best 6197 last 6197 rows 7 | before-window best 190712, window best 6197 | PROGRESS: drt_violations improved 96.8 % in window |  |
| intel1 | prd-eco_20261121_082001_3216437-i1t-2148021 | eco_20261121_082001_3216437-i1t | 5_2_route | 7.6 | drt_violations best 3595 last 3595 rows 9 | before-window best 185697, window best 3595 | PROGRESS: drt_violations improved 98.1 % in window |  |
| intel2 | kvcore-ot_qkh_recip_leaf__216x216_ahubrecover_-2332486 | kvcore-ot_qkh_recip_leaf__216x216_ahubrecover_ | 3_5_place_dp | 0.1 | repair_Violations best 0 last 0 rows 3 | PROGRESS: repair_Violations reached 0 |  |
