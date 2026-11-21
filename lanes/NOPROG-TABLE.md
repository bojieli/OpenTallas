# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 14:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 3, 'NO-PROGRESS': 1, 'GRT-LABEL': 33, 'YOUNG': 96, 'NO-DATA': 9, 'KEEP': 1, 'EXCLUDED': 5, 'PROGRESS': 29}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 30.1 | grt rounds 6 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -2893.36 ps (< -300, gate TT >= -42); job age 3 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 43.6 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 43 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc2 | dpkit-cbf_q00__cl870de686-3870117 | cbf_q00 | pregrt_ff_hold | 4.0 | repair_TNS best 3.60575e+06 last 3.60575e+06 rows 1 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -540.84 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc7 | dpkit-slw_su_l0__cl1a1c1f8f-1472945 | slw_su_l0 | 5_2_route | 11.4 | drt_violations best 4 last 4 rows 47 | before-window best 4, window best 4 | NO-PROGRESS: drt_violations best 4 vs 4 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-kv3_hgi_v8-3126306 | kv3_hgi_v8 | 5_1_grt | 10.1 | grt rounds 3 overflow 5:39297 -> 10:16436 -> 15:15865 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t39-243585 | ot_s81sl_leaf__t39 | 5_1_grt | 3.8 | grt rounds 2 overflow 5:179 -> 10:39 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 28.7 | grt rounds 3 overflow 5:62850 -> 10:60456 -> 15:49678 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 28.6 | grt rounds 4 overflow 5:56489 -> 10:43484 -> 15:40478 -> 20:43612 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 43.1 | grt rounds 4 overflow 5:9510 -> 10:5086 -> 15:3245 -> 20:2910 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 32.3 | grt rounds 4 overflow 5:54036 -> 10:38067 -> 15:34597 -> 20:37416 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_sc_v2-2660942 | slw_sc_v2 | 5_1_grt | 5.2 | grt rounds 2 overflow 5:394 -> 10:24 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 22.2 | grt rounds 3 overflow 5:77963 -> 10:71866 -> 15:58855 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 27.2 | grt rounds 3 overflow 5:61320 -> 10:67332 -> 15:69180 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 16.6 | grt rounds 3 overflow 5:50395 -> 10:49359 -> 15:39411 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 16.6 | grt rounds 3 overflow 5:50187 -> 10:49123 -> 15:39498 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 26.3 | grt rounds 3 overflow 5:77888 -> 10:49482 -> 15:43107 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 14.0 | grt rounds 3 overflow 5:79338 -> 10:74939 -> 15:54687 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 22.3 | grt rounds 3 overflow 5:71545 -> 10:71003 -> 15:50597 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 16.1 | grt rounds 3 overflow 5:73809 -> 10:69973 -> 15:51390 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 17.8 | grt rounds 4 overflow 5:42922 -> 10:39064 -> 15:36370 -> 20:37813 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 17.8 | grt rounds 4 overflow 5:41833 -> 10:36208 -> 15:31830 -> 20:32437 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_st_a_v2__pv4242de79-2391789 | sle_st_a_v2 | 5_1_grt | 1.5 | grt rounds 2 overflow 5:21672 -> 10:8153 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_1_grt | 1.6 | grt rounds 2 overflow 5:4526 -> 10:3466 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hgi_v2__cl2862d491-3732038 | kv3_hgi_v2 | 5_1_grt | 6.7 | grt rounds 2 overflow 5:72991 -> 10:37675 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 17.4 | grt rounds 4 overflow 5:19113 -> 10:12610 -> 15:11259 -> 20:10671 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hgi_v2__cle0015330-660102 | kv3_hgi_v2 | 5_1_grt | 6.3 | grt rounds 2 overflow 5:59354 -> 10:37389 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hgi_v8-3224135 | kv3_hgi_v8 | 5_1_grt | 10.9 | grt rounds 4 overflow 5:39297 -> 10:9376 -> 15:6005 -> 20:4797 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 30.3 | grt rounds 4 overflow 5:26517 -> 10:13016 -> 15:8921 -> 20:7819 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 41.0 | grt rounds 6 overflow 5:18899 -> 10:19233 -> 15:12971 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 41.3 | grt rounds 5 overflow 5:34987 -> 10:28632 -> 15:24645 -> 20:22699 -> 25:31808 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 5_1_grt | 18.3 | grt rounds 4 overflow 5:54170 -> 10:7759 -> 15:5073 -> 20:4181 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 23.8 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 18.8 | grt rounds 4 overflow 5:36131 -> 10:30276 -> 15:24310 -> 20:22194 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 40.1 | grt rounds 3 overflow 5:56283 -> 10:53405 -> 15:50242 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 35.4 | grt rounds 3 overflow 5:59246 -> 10:46138 -> 15:53864 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 35.4 | grt rounds 3 overflow 5:60515 -> 10:47029 -> 15:53055 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 35.6 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2275786 | col_h10_r2__t1 | 5_2_route | 5.3 | drt_violations best 75691 last 75691 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc10 | dpkit-hd_lep0N-22377 | hd_lep0N | 4_2_tapbal_grt | 6.6 | last meaningful line 2.0 h ago (48/53 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v3-1328903 | slw_fw_v3 | 5_2_route | 11.2 | drt_violations best 95479 last 95479 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1t-894339 | eco_20261121_154936_3396612-i1t | 5_2_route | 6.1 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_184648_4039100-i1t-1413255 | eco_20261121_184648_4039100-i1t | 5_2_route | 3.2 | drt_violations best 4953 last 4953 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | ap-render-1413110ea3ad-1796689 | ap-render-1413110ea3ad | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-cbf_q00__cl1b5a6458-1726234 | cbf_q00 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 104 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-cbf_q01_s2-1733979 | cbf_q01_s2 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 51 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-cbn_q01__clab6e67f2-19353 | cbn_q01 | 3_4_place_resized | 1.4 | last meaningful line 0.2 h ago (20/20 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-cbx_q10__cl89936551_h-1143192 | cbx_q10 | 3_3_place_gp | 0.6 | overflow best 0.208 last 0.208 rows 33 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-2629912 | col_h9_r0_p2__t1 | 5_2_route | 11.3 | drt_violations best 135164 last 135164 rows 1 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_kv512_C__t1-359428 | dsdv_slice_kv512_C__t1 | 3_3_place_gp | 1.2 | overflow best 0.71 last 0.71 rows 4 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-kv3_hgi_v5-244656 | kv3_hgi_v5 | 3_5_place_dp | 1.3 | last meaningful line 0.1 h ago (121/121 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 3_1_place_gp_skip_io | 5.4 | overflow best 0.7161 last 0.7254 rows 20 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | 4_1_cts | 2.4 | last meaningful line 0.1 h ago (7402/7402 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-native59-22224 | native59 | 3_3_place_gp | 1.4 | overflow best 0.2988 last 0.3172 rows 232 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-native59-3868183 | native59 | pregrt_ff_hold | 4.0 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2374083 | sle_hc1 | postcts_gate_TT | 11.5 | last meaningful line 0.1 h ago (399/399 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-427216 | sle_st_a_v1 | 5_1_grt | 1.1 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-254386 | sle_st_a_v2 | 5_1_grt | 1.2 | last meaningful line 0.3 h ago (204/211 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-425101 | sle_st_a_v2 | 5_1_grt | 1.1 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-425190 | sle_su_l1 | pregrt_ff_hold | 1.1 | repair_TNS best 1.20757e+06 last 1.20757e+06 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-slice_station__t36-3125329 | slice_station__t36 | 5_2_route | 7.8 | last meaningful line 0.1 h ago (262/262 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t51-342871 | slice_station__t51 | pregrt_ff_hold | 1.2 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2408517 | slw_fe_v1 | postcts_gate_FF | 11.4 | last meaningful line 0.0 h ago (1496/1496 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | 5_1_grt | 7.0 | repair_Remaining best 225403 last 225403 rows 171 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2449519 | slw_hc3 | 5_2_route | 11.4 | drt_violations best 5873 last 5873 rows 2 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-1019838 | slw_sc_v1 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (5490/5490 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3868961 | slw_sc_v1 | 5_1_grt | 4.0 | last meaningful line 0.0 h ago (171/172 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-844610 | slw_st_a_v1 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (8918/8918 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2420111 | slw_st_b_v2 | 5_2_route | 11.4 | last meaningful line 0.0 h ago (254/254 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_c__cl19bb38ef-2385009 | slw_su_c | 5_1_grt | 8.3 | last meaningful line 0.3 h ago (212/215 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_070700_2142563-i1-4024972 | eco_20261121_070700_2142563-i1 | 5_2_route | 1.5 | last meaningful line 0.1 h ago (135/135 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_102155_957464-i1t-245136 | eco_20261121_102155_957464-i1t | 5_2_route | 3.6 | drt_violations best 7246 last 7246 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_105744_956410-i1t-1036390 | eco_20261121_105744_956410-i1t | 5_2_route | 3.0 | drt_violations best 11576 last 11576 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_123328_2268168-i1t-4175816 | eco_20261121_123328_2268168-i1t | 5_2_route | 1.4 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_124930_2356681-i1t-415105 | eco_20261121_124930_2356681-i1t | 5_1_grt | 1.1 | last meaningful line 0.6 h ago (232/1509 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-cbn-q00--cl622f65d2-grt-402270 | cbn-q00--cl622f65d2-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-cbn-q01--cldd6ea846-grt-284591 | cbn-q01--cldd6ea846-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-kv3-hgi-v3-grt-250950 | kv3-hgi-v3-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-bk_sel__t2-3723154 | bk_sel__t2 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (2635/2635 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00_s2-2812888 | cbf_q00_s2 | 3_4_place_resized | 1.3 | last meaningful line 0.0 h ago (319/319 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q11-3840796 | cbf_q11 | pregrt_ff_hold | 0.6 | repair_TNS best 11249.1 last 11249.1 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-kv3_hg_v1p2-3964783 | kv3_hg_v1p2 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.9971 last 0.9971 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-serdes__t12-331217 | serdes__t12 | 1_2_yosys | 0.1 | last meaningful line 0.1 h ago (279/279 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5564/5564 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2969215 | sle_hc0 | 4_1_cts | 1.3 | last meaningful line 0.2 h ago (5438/5438 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-1459492 | sle_hc1 | 5_2_route | 11.4 | last meaningful line 0.1 h ago (279/280 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-3504337 | sle_hc1 | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (5718/5718 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cle683a076-3820341 | slw_hc1 | 4_1_cts | 0.7 | last meaningful line 0.1 h ago (5402/5402 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3695652 | slw_sc_v2 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (4228/4228 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3669665 | slw_st_b_v1 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (5239/5239 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-149618 | tt_ctlm | 3_3_place_gp | 0.2 | overflow best 0.6692 last 0.6692 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | prd-eco_20261121_100942_929932-i1-3347652 | eco_20261121_100942_929932-i1 | 5_2_route | 2.6 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_173326_4009105-i1-295057 | eco_20261121_173326_4009105-i1 | 5_1_grt | 0.1 | last meaningful line 0.1 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_184012_3245689-i1t-2500922 | eco_20261121_184012_3245689-i1t | 5_2_route | 3.1 | drt_violations best 5501 last 5501 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_193535_3253336-i1t-4078609 | eco_20261121_193535_3253336-i1t | 5_2_route | 2.4 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_203749_4020394-i1-2795396 | eco_20261121_203749_4020394-i1 | 5_2_route | 1.3 | last meaningful line 0.1 h ago (131/131 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-cbn-q00--cld7bf7197-grt-3123362 | cbn-q00--cld7bf7197-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-kv3-hg-v1-grt-3086875 | kv3-hg-v1-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1890854 | cbn_q01 | 3_4_place_resized | 1.1 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-2597778 | col_h9_r0_p2__t1 | pregrt_ff_hold | 0.5 | repair_TNS best 18445.5 last 18445.5 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | 5_1_grt | 1.7 | last meaningful line 0.2 h ago (39/39 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | pregrt_ff_hold | 1.7 | repair_TNS best 52717.4 last 52717.4 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-coll_core-2853781 | coll_core | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_mu_LP__t2-3534677 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 2.7 | repair_TNS best 228788 last 228788 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-2007910 | kv3_hg_v1p2 | 3_3_place_gp | 1.0 | overflow best 0.783 last 0.783 rows 2 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_hroot-4110897 | kv3_hroot | 5_2_route | 6.4 | drt_violations best 82476 last 82476 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor-3733934 | kv3_io_cor | 5_2_route | 6.7 | drt_violations best 59 last 70 rows 42 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-3274788 | serdes__t1 | 5_2_route | 10.6 | drt_violations best 114810 last 114810 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-1802792 | sle_ctl | 3_3_place_gp | 1.2 | overflow best 0.0997 last 0.0997 rows 47 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa-1023417 | sle_hc0 | postcts_gate_TT | 8.6 | last meaningful line 0.1 h ago (372/372 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3985339 | sle_hc2 | 5_1_grt | 6.5 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-1013642 | sle_hc2 | postcts_gate_TT | 8.6 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-850569 | slw_fe_v1 | postcts_gate_FF | 8.7 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-2906124 | slw_hc1 | postcts_gate_TT | 10.9 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1012001 | slw_hc3 | postcts_gate_FF | 8.6 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-1012945 | slw_hc3 | postcts_gate_TT | 8.6 | last meaningful line 0.1 h ago (355/355 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-1964882 | slw_su_l0 | pregrt_ff_hold | 1.1 | repair_TNS best 1.24219e+06 last 1.24219e+06 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | otc-1547845-17008 | 1547845 | orfs_flow | 4.7 | repair_Viol best 93 last 93 rows 33 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 57.2 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3350653 | col_h9_r1__t1 | 5_2_route | 7.7 | drt_violations best 86855 last 86855 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-1513640 | sle_hc0 | 5_2_route | 9.2 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2616668 | sle_hc1 | 5_1_grt | 8.3 | last meaningful line 0.2 h ago (212/955 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-882856 | slw_hc3 | 5_2_route | 9.6 | drt_violations best 6689 last 6689 rows 2 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | otc-3085280-30126 | 3085280 | - | 13.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 13.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 13.3 |  | NO-DATA: no log found |  |
| epyc9 | prd-count-p1_tc-2327283 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_143815_74711-i2-3554105 | eco_20261121_143815_74711-i2 | 5_2_route | 2.4 | drt_violations best 554 last 554 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_154823_2000128-i2-4171153 | eco_20261121_154823_2000128-i2 | 5_2_route | 1.6 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 3.0 | drt_violations best 13075 last 13075 rows 3 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_195859_2616880-i1-966712 | eco_20261121_195859_2616880-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_201548_1094504-i1t-4087489 | eco_20261121_201548_1094504-i1t | 5_2_route | 1.7 | drt_violations best 39685 last 39685 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-4146127 | col_h10_r2__t1 | 5_2_route | 10.4 | drt_violations best 417 last 417 rows 5 | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | 5_2_route | 18.3 | drt_violations best 91173 last 91173 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-2204474 | slw_st_b_v1 | postcts_gate_TT | 11.4 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco1-i1-2520913 | eco1-i1 | 5_2_route | 11.2 | drt_violations best 112 last 112 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i2t-1252392 | eco_20261120_192428_3309571-i2t | 5_2_route | 1.7 | last meaningful line 0.1 h ago (271/272 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | prd-eco_20261121_075836_1991905-i1t-1821063 | eco_20261121_075836_1991905-i1t | 5_2_route | 6.0 | drt_violations best 23424 last 23424 rows 2 | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i1t-2148021 | eco_20261121_082001_3216437-i1t | 5_2_route | 5.6 | drt_violations best 18210 last 18210 rows 2 | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3655958 | coll_ftm | 5_2_route | 1.2 | last meaningful line 0.1 h ago (232/233 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | prd-eco_20261121_072804_212710-i1-2335895 | eco_20261121_072804_212710-i1 | 5_2_route | 1.8 | last meaningful line 0.1 h ago (262/263 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | prd-eco_20261121_111944_190475-i1-3971139 | eco_20261121_111944_190475-i1 | 5_2_route | 2.9 | drt_violations best 7 last 7 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel2 | prd-eco_20261121_115902_173230-i1t-1237159 | eco_20261121_115902_173230-i1t | 5_2_route | 2.2 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 30.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-eco1-i1-100513 | eco1-i1 | 5_2_route | 10.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-1617813 | eco1-i1 | 5_1_grt | 1.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-1714380 | eco1-i1 | 5_1_grt | 1.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-4178763 | eco1-i1 | 5_2_route | 3.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-fin-92562 | fin | 6_report | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-hd_lep0N-1588394 | hd_lep0N | pregrt_ff_hold | 8.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-serdes__t4-293755 | serdes__t4 | 5_1_grt | 3.8 | repair_TNS best 0 last 0 rows 20 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slice_station__t36-3668002 | slice_station__t36 | 5_1_grt | 4.3 | repair_TNS best 0 last 0 rows 13 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slice_station__t37-173045 | slice_station__t37 | 5_1_grt | 3.8 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_2_route | 18.6 | drt_violations best 10168 last 49296 rows 18 | before-window best 11596, window best 10168 | PROGRESS: drt_violations improved 12.3 % in window |  |
| epyc10 | prd-eco_20261121_203102_3392434-i1t-646001 | eco_20261121_203102_3392434-i1t | 5_1_grt | 1.4 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 35.2 | last meaningful line 0.4 h ago (1497/1497 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-hd_mesh-2472048 | hd_mesh | pregrt_ff_hold | 11.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-248840 | sle_st_a_v1 | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_2_route | 20.8 | drt_violations best 9327 last 9327 rows 17 | before-window best 12080, window best 9327 | PROGRESS: drt_violations improved 22.8 % in window |  |
| epyc2 | prd-eco_20261120_170022_4017640-i2t-2328774 | eco_20261120_170022_4017640-i2t | 5_2_route | 8.4 | drt_violations best 99 last 99 rows 11 | before-window best 72780, window best 99 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 11.1 | drt_violations best 3 last 9 rows 44 | before-window best 234, window best 3 | PROGRESS: drt_violations improved 98.7 % in window |  |
| epyc2 | prd-eco_20261121_080323_3018643-i1-1109108 | eco_20261121_080323_3018643-i1 | 5_1_grt | 0.6 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-993515 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve230954c-1731757 | sle_hc1 | pregrt_ff_hold | 7.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_2_route | 21.7 | drt_violations best 13126 last 54684 rows 18 | before-window best 13507, window best 13126 | PROGRESS: drt_violations improved 2.8 % in window |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | 5_2_route | 17.4 | drt_violations best 15 last 15 rows 50 | before-window best 98, window best 15 | PROGRESS: drt_violations improved 84.7 % in window |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | 5_2_route | 17.4 | drt_violations best 27 last 27 rows 50 | before-window best 67, window best 27 | PROGRESS: drt_violations improved 59.7 % in window |  |
| epyc8 | dpkit-glue-504992 | glue | pregrt_ff_hold | 5.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-hd_host_e-3833588 | hd_host_e | 5_2_route | 6.6 | drt_violations best 25 last 25 rows 58 | before-window best 33926, window best 25 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-1899674 | slw_fe_v1 | 5_1_grt | 8.0 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | pregrt_ff_hold | 1.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-1897237 | slw_st_a_v2 | pregrt_ff_hold | 1.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | pregrt_ff_hold | 0.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | prd-eco_20261121_214321_3818039-i1t-2911659 | eco_20261121_214321_3818039-i1t | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | 5_2_route | 18.1 | drt_violations best 203629 last 203629 rows 1 | before-window best 203629, window best 203629 | PROGRESS: drt_violations: active iteration at 67848 < best completed total 203629 (in-iter |  |
| intel1 | dpkit-sle_ctl__cl67434795-622153 | sle_ctl | pregrt_ff_hold | 12.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-kv3_io_ft-1149261 | kv3_io_ft | 5_1_grt | 0.5 | repair_TNS best 0 last 0 rows 17 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slice_station__t12-4094445 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 0 last 0 rows 4 | PROGRESS: drt_violations reached 0 |  |
