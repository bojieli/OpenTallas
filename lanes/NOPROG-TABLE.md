# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 15:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'CANCEL-NOW': 2, 'GRT-LABEL': 40, 'YOUNG': 87, 'NO-DATA': 8, 'KEEP': 1, 'EXCLUDED': 4, 'PROGRESS': 26}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 31.6 | grt rounds 6 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -2893.36 ps (< -300, gate TT >= -42); job age 3 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 45.1 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 45 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-3999022 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 5_2_route | 0.2 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-2189253 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | hold_margin_read | 0.7 |  | CANCEL-NOW: HBM is parked | CANCELLED |
| epyc10 | dpkit-kv3_hgi_v8-3126306 | kv3_hgi_v8 | 5_1_grt | 11.6 | grt rounds 4 overflow 5:39297 -> 10:9376 -> 15:6005 -> 20:4797 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t39-243585 | ot_s81sl_leaf__t39 | 5_1_grt | 5.3 | grt rounds 2 overflow 5:179 -> 10:39 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 30.2 | grt rounds 3 overflow 5:62850 -> 10:60456 -> 15:49678 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 30.1 | grt rounds 4 overflow 5:56489 -> 10:43484 -> 15:40478 -> 20:43412 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 44.6 | grt rounds 4 overflow 5:9510 -> 10:5086 -> 15:3245 -> 20:2874 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-hd_mesh-2472048 | hd_mesh | 5_1_grt | 12.9 | grt rounds 6 overflow 5:638 -> 10:34465 -> 15:25552 -> 20:54 -> 25:52 -> 30:50 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 33.8 | grt rounds 4 overflow 5:54036 -> 10:38366 -> 15:34597 -> 20:37416 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-248840 | sle_st_a_v1 | 5_1_grt | 2.8 | grt rounds 2 overflow 5:3539 -> 10:2906 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-427216 | sle_st_a_v1 | 5_1_grt | 2.6 | grt rounds 2 overflow 5:4512 -> 10:1167 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-254386 | sle_st_a_v2 | 5_1_grt | 2.7 | grt rounds 2 overflow 5:12031 -> 10:4878 | GRT-LABEL: DESIGN-FAIL: overflow 4878 at round 10 > 1000 |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-425101 | sle_st_a_v2 | 5_1_grt | 2.6 | grt rounds 2 overflow 5:13907 -> 10:5441 | GRT-LABEL: DESIGN-FAIL: overflow 5441 at round 10 > 1000 |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-844610 | slw_st_a_v1 | 5_1_grt | 2.3 | grt rounds 2 overflow 5:3827 -> 10:2935 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_su_c__cl19bb38ef-2385009 | slw_su_c | 5_1_grt | 9.8 | grt rounds 2 overflow 5:27462 -> 10:11725 | GRT-LABEL: DESIGN-FAIL: overflow 11725 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 23.7 | grt rounds 3 overflow 5:76845 -> 10:71866 -> 15:58855 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 28.7 | grt rounds 3 overflow 5:61320 -> 10:66596 -> 15:69180 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 18.1 | grt rounds 3 overflow 5:50395 -> 10:49359 -> 15:39411 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 18.1 | grt rounds 3 overflow 5:50621 -> 10:49123 -> 15:39498 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 27.8 | grt rounds 3 overflow 5:46939 -> 10:49333 -> 15:43107 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 15.5 | grt rounds 3 overflow 5:79338 -> 10:74939 -> 15:54793 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 23.8 | grt rounds 3 overflow 5:71545 -> 10:71003 -> 15:50597 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 17.6 | grt rounds 3 overflow 5:73809 -> 10:69973 -> 15:51390 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 19.3 | grt rounds 4 overflow 5:42922 -> 10:39064 -> 15:36370 -> 20:37882 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 19.3 | grt rounds 4 overflow 5:41833 -> 10:36208 -> 15:31830 -> 20:31076 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_st_a_v2__pv4242de79-2391789 | sle_st_a_v2 | 5_1_grt | 3.0 | grt rounds 2 overflow 5:21672 -> 10:8153 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hgi_v2__cl2862d491-3732038 | kv3_hgi_v2 | 5_1_grt | 8.2 | grt rounds 2 overflow 5:72991 -> 10:37675 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 18.9 | grt rounds 4 overflow 5:19113 -> 10:12610 -> 15:11259 -> 20:10290 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_1_grt | 2.6 | grt rounds 2 overflow 5:22926 -> 10:4651 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-1897237 | slw_st_a_v2 | 5_1_grt | 2.6 | grt rounds 2 overflow 5:103 -> 10:56 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_1_grt | 2.4 | grt rounds 2 overflow 5:3304 -> 10:2843 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hgi_v8-3224135 | kv3_hgi_v8 | 5_1_grt | 12.4 | grt rounds 4 overflow 5:37484 -> 10:8165 -> 15:5582 -> 20:4797 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 31.8 | grt rounds 4 overflow 5:34386 -> 10:12131 -> 15:8921 -> 20:7819 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 42.5 | grt rounds 6 overflow 5:18899 -> 10:19233 -> 15:11889 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 42.8 | grt rounds 5 overflow 5:34987 -> 10:28632 -> 15:24645 -> 20:22699 -> 25:31808 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 5_1_grt | 19.8 | grt rounds 5 overflow 5:54170 -> 10:7759 -> 15:5073 -> 20:4181 -> 25:5669 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 25.3 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 20.3 | grt rounds 4 overflow 5:36357 -> 10:30276 -> 15:24310 -> 20:21320 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 41.6 | grt rounds 4 overflow 5:56283 -> 10:53405 -> 15:50242 -> 20:55216 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 36.6 | grt rounds 3 overflow 5:59246 -> 10:46138 -> 15:53864 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 36.6 | grt rounds 3 overflow 5:60515 -> 10:47029 -> 15:53055 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 36.8 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2275786 | col_h10_r2__t1 | 5_2_route | 6.8 | drt_violations best 1387 last 1387 rows 11 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-22377 | hd_lep0N | 4_2_tapbal_grt | 8.1 | last meaningful line 3.5 h ago (48/56 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t4-293755 | serdes__t4 | tt_setup_repair_grt | 5.3 | repair_Viol best 1688 last 1688 rows 25 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-slice_station__t36-3668002 | slice_station__t36 | 5_2_route | 5.8 | last meaningful line 0.1 h ago (265/266 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t37-173045 | slice_station__t37 | 5_2_route | 5.3 | last meaningful line 0.1 h ago (264/265 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v3-1328903 | slw_fw_v3 | 5_2_route | 12.7 | drt_violations best 12845 last 12845 rows 3 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | otc-3502525-10491 | 3502525 | equiv_reset_alias | 0.8 | last meaningful line 0.0 h ago (792520/792520 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1t-894339 | eco_20261121_154936_3396612-i1t | 5_2_route | 7.6 | last meaningful line 0.3 h ago (291/292 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_184648_4039100-i1-3762453 | eco_20261121_184648_4039100-i1 | 5_1_grt | 0.6 | last meaningful line 0.2 h ago (234/1276 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_203102_3392434-i1t-646001 | eco_20261121_203102_3392434-i1t | 5_2_route | 2.9 | last meaningful line 0.0 h ago (277/278 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl1b5a6458-1726234 | cbf_q00 | 3_5_place_dp | 1.6 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q01_s2-3354717 | cbf_q01_s2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (4958/4958 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-2629912 | col_h9_r0_p2__t1 | 5_2_route | 12.8 | drt_violations best 20554 last 20554 rows 2 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v5-244656 | kv3_hgi_v5 | pregrt_ff_hold | 2.8 | repair_TNS best 272670 last 272670 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 3_3_place_gp | 6.9 | overflow best 0.0992 last 0.0992 rows 45 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | 4_1_cts | 3.9 | last meaningful line 0.2 h ago (7410/7410 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-native59-3868183 | native59 | pregrt_ff_hold | 5.5 | repair_TNS best 8684.22 last 8684.22 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2374083 | sle_hc1 | 5_2_route | 13.0 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-425190 | sle_su_l1 | 5_1_grt | 2.6 | last meaningful line 0.0 h ago (191/194 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t36-3125329 | slice_station__t36 | 5_2_route | 9.3 | last meaningful line 0.1 h ago (277/278 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2408517 | slw_fe_v1 | 5_2_route | 12.9 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2420111 | slw_st_b_v2 | 5_2_route | 12.9 | drt_violations best 84153 last 84153 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | otc-3002702-20247 | 3002702 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc2 | otc-3518253-14245 | 3518253 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261121_070700_2142563-i1-4024972 | eco_20261121_070700_2142563-i1 | 5_2_route | 3.0 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_080323_3018643-i1-1109108 | eco_20261121_080323_3018643-i1 | 5_2_route | 2.1 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_123328_2268168-i1t-4175816 | eco_20261121_123328_2268168-i1t | 5_2_route | 2.9 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_124930_2356681-i1t-415105 | eco_20261121_124930_2356681-i1t | 5_2_route | 2.6 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | prd-fin-245136 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (621/621 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-bk_sel__t2-3723154 | bk_sel__t2 | 5_1_grt | 2.2 | last meaningful line 0.8 h ago (202/209 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-582858 | cbn_q01 | pregrt_ff_hold | 1.4 | repair_TNS best 51417.4 last 51417.4 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-993515 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 6.1 | repair_TNS best 23538.3 last 23538.3 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (9035/9035 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | 4_1_cts | 2.0 | last meaningful line 0.4 h ago (5622/5622 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2969215 | sle_hc0 | pregrt_ff_hold | 2.8 | repair_TNS best 13103.6 last 13103.6 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve230954c-1731757 | sle_hc1 | 5_1_grt | 9.2 | last meaningful line 0.1 h ago (1010/1027 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-1459492 | sle_hc1 | 5_2_route | 12.9 | drt_violations best 13726 last 13726 rows 2 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-3504337 | sle_hc1 | tt_setup_repair | 2.4 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cle683a076-3820341 | slw_hc1 | 4_1_cts | 2.2 | last meaningful line 0.2 h ago (5464/5464 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3695652 | slw_sc_v2 | 5_1_grt | 2.3 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | postcts_gate_FF | 3.1 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 0.5 | last meaningful line 0.3 h ago (310/310 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_100942_929932-i1-3347652 | eco_20261121_100942_929932-i1 | 5_2_route | 4.1 | drt_violations best 65 last 65 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_173326_4009105-i1-295057 | eco_20261121_173326_4009105-i1 | 5_2_route | 1.6 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_193535_3253336-i1t-4078609 | eco_20261121_193535_3253336-i1t | 5_2_route | 3.9 | drt_violations best 19860 last 19860 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_203749_4020394-i1-2795396 | eco_20261121_203749_4020394-i1 | 5_2_route | 2.8 | drt_violations best 1 last 1 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | prd-fin-2500922 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q00__cld7bf7197-3404310 | cbn_q00 | tt_setup_repair | 1.3 | repair_Violations best 93 last 252 rows 48 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-2597778 | col_h9_r0_p2__t1 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (154/154 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | 5_1_grt | 3.2 | last meaningful line 1.5 h ago (39/39 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_1_grt | 3.2 | last meaningful line 1.0 h ago (39/39 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-glue-504992 | glue | 5_1_grt | 7.4 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-3274788 | serdes__t1 | 5_2_route | 12.1 | drt_violations best 114810 last 114810 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa-1023417 | sle_hc0 | 5_2_route | 10.1 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3985339 | sle_hc2 | postcts_gate_TT | 8.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-1013642 | sle_hc2 | 5_2_route | 10.1 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-1899674 | slw_fe_v1 | 5_1_grt | 9.5 | last meaningful line 0.1 h ago (1547/1564 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-850569 | slw_fe_v1 | 5_2_route | 10.2 | last meaningful line 0.0 h ago (263/263 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-2906124 | slw_hc1 | postcts_gate_FF | 12.4 | last meaningful line 0.0 h ago (843/843 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1012001 | slw_hc3 | 5_2_route | 10.1 | drt_violations best 73752 last 73752 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-1012945 | slw_hc3 | 5_2_route | 10.1 | drt_violations best 69941 last 69941 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-1964882 | slw_su_l0 | 5_1_grt | 2.6 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-3509414-20478 | 3509414 | gate.ys | 1.2 | last meaningful line 1.0 h ago (51328/51328 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261121_214321_3818039-i1t-2911659 | eco_20261121_214321_3818039-i1t | 5_2_route | 1.7 | drt_violations best 40634 last 40634 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | so_483869_ff_27211 | so_483869_ff_27211 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | so_483869_tt_27211 | so_483869_tt_27211 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-kv3_hg-1650521 | kv3_hg | 3_3_place_gp | 0.6 | overflow best 0.6696 last 0.6696 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-kv3_hgi_v2__cle0015330-1926152 | kv3_hgi_v2 | 3_3_place_gp | 0.2 | overflow best 0.2377 last 0.2377 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-1513640 | sle_hc0 | 5_2_route | 10.7 | drt_violations best 11607 last 11607 rows 2 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2616668 | sle_hc1 | postcts_gate_FF | 9.8 | last meaningful line 0.1 h ago (392/392 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-3085280-30126 | 3085280 | - | 15.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 15.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 14.8 |  | NO-DATA: no log found |  |
| epyc9 | prd-count-p1_tc-4171153 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (564/564 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i2t-1219117 | eco_20261121_070035_1645318-i2t | 5_2_route | 1.2 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 4.5 | drt_violations best 1965 last 1965 rows 14 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_195859_2616880-i2t-2177655 | eco_20261121_195859_2616880-i2t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_201548_1094504-i1-1641941 | eco_20261121_201548_1094504-i1 | 5_2_route | 0.6 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | so_2142689_ff_5248 | so_2142689_ff_5248 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (557/557 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | so_2142689_tt_5248 | so_2142689_tt_5248 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (557/557 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | 5_2_route | 19.8 | drt_violations best 91173 last 91173 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-2204474 | slw_st_b_v1 | 5_2_route | 12.9 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | eco-abs-3425169 | eco-abs | generate_abstract | 0.4 | last meaningful line 0.2 h ago (1025/1025 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-3659904-21621 | 3659904 | 3_3_place_gp | 0.1 | last meaningful line 0.0 h ago (110/110 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i2t-1252392 | eco_20261120_192428_3309571-i2t | 5_2_route | 3.2 | drt_violations best 3629 last 3629 rows 3 | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4007898 | col_h9_r1__t1 | 3_3_place_gp | 0.2 | overflow best 0.3088 last 0.3156 rows 30 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-4004149 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-2212511 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (227/228 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t24__cl66b71008-4080541 | slice_station__t24 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | eco-abs-807995 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | otc-3944303-10926 | 3944303 | - | 0.3 |  | NO-DATA: no log found |  |
| intel2 | otc-776460-13624 | 776460 | signoff | 0.0 | last meaningful line 0.0 h ago (3/3 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | prd-eco_20261121_115902_173230-i1t-1237159 | eco_20261121_115902_173230-i1t | 5_2_route | 3.5 | drt_violations best 4890 last 4890 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel2 | so_4054830_ff_99762 | so_4054830_ff_99762 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (555/555 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | so_4054830_tt_99762 | so_4054830_tt_99762 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (555/555 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 32.4 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-eco1-i1-1617813 | eco1-i1 | 5_2_route | 2.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-1714380 | eco1-i1 | 5_2_route | 2.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-fin-100513 | fin | 6_report | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-fin-4178763 | fin | 6_report | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-hd_lep0N-1588394 | hd_lep0N | pregrt_ff_hold | 9.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_2_route | 20.1 | drt_violations best 10168 last 49296 rows 18 | before-window best 11104, window best 10168 | PROGRESS: drt_violations improved 8.4 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 36.7 | last meaningful line 0.6 h ago (1499/1499 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-slice_station__t51-342871 | slice_station__t51 | 5_1_grt | 2.7 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | 5_1_grt | 8.5 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-1019838 | slw_sc_v1 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3868961 | slw_sc_v1 | 5_1_grt | 5.5 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_2_route | 22.3 | drt_violations best 9327 last 39114 rows 18 | before-window best 10277, window best 9327 | PROGRESS: drt_violations improved 9.2 % in window |  |
| epyc2 | prd-eco_20261120_170022_4017640-i2t-2328774 | eco_20261120_170022_4017640-i2t | 5_2_route | 9.9 | drt_violations best 98 last 98 rows 12 | before-window best 72780, window best 98 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 12.6 | drt_violations best 1 last 12 rows 51 | before-window best 3, window best 1 | PROGRESS: drt_violations improved 66.7 % in window |  |
| epyc2 | prd-eco_20261121_105744_956410-i1t-1036390 | eco_20261121_105744_956410-i1t | 5_2_route | 4.5 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-cbf_q11-3840796 | cbf_q11 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3669665 | slw_st_b_v1 | pregrt_ff_hold | 2.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_2_route | 23.2 | drt_violations best 13126 last 54684 rows 18 | before-window best 13507, window best 13126 | PROGRESS: drt_violations improved 2.8 % in window |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | 5_2_route | 18.9 | drt_violations best 15 last 15 rows 52 | before-window best 20, window best 15 | PROGRESS: drt_violations improved 25.0 % in window |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | 5_2_route | 18.9 | drt_violations best 27 last 27 rows 50 | before-window best 37, window best 27 | PROGRESS: drt_violations improved 27.0 % in window |  |
| epyc8 | dpkit-dsdv_slice_lepe_mu_LP__t2-3534677 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-serdes__t14-3301476 | serdes__t14 | 3_5_place_dp | 1.4 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-4146127 | col_h10_r2__t1 | 5_2_route | 11.9 | drt_violations best 57 last 57 rows 8 | before-window best 85869, window best 57 | PROGRESS: drt_violations improved 99.9 % in window |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | 5_2_route | 19.6 | drt_violations best 27329 last 27329 rows 3 | before-window best 203629, window best 27329 | PROGRESS: drt_violations improved 86.6 % in window |  |
| intel1 | dpkit-sle_ctl__cl67434795-622153 | sle_ctl | pregrt_ff_hold | 14.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | otc-3352302-1814 | 3352302 | 4_1_cts | 0.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | otc-3352679-20733 | 3352679 | 4_1_cts | 0.4 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | prd-eco_20261121_075836_1991905-i1t-1821063 | eco_20261121_075836_1991905-i1t | 5_2_route | 7.5 | drt_violations best 7187 last 7187 rows 6 | before-window best 190712, window best 7187 | PROGRESS: drt_violations improved 96.2 % in window |  |
| intel1 | prd-eco_20261121_082001_3216437-i1t-2148021 | eco_20261121_082001_3216437-i1t | 5_2_route | 7.1 | drt_violations best 4299 last 4299 rows 7 | before-window best 185697, window best 4299 | PROGRESS: drt_violations improved 97.7 % in window |  |
| intel2 | otc-4063418-6988 | 4063418 | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 3 | PROGRESS: repair_Violations reached 0 |  |
