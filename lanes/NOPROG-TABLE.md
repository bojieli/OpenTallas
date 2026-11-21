# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 15:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 3, 'CANCEL-NOW': 3, 'GRT-LABEL': 38, 'YOUNG': 96, 'NO-DATA': 9, 'KEEP': 1, 'EXCLUDED': 5, 'PROGRESS': 26}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 31.1 | grt rounds 6 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -2893.36 ps (< -300, gate TT >= -42); job age 3 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 44.6 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 44 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc9 | dpkit-kv3_hgi_v2__cle0015330-660102 | kv3_hgi_v2 | tt_setup_repair_grt | 7.3 | repair_Violations best 0 last 0 rows 29 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -739.67 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-2183615 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 5_2_route | 0.2 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-2189253 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 3_3_place_gp | 0.2 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-2189253-lec | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | lec | 0.1 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-kv3_hgi_v8-3126306 | kv3_hgi_v8 | 5_1_grt | 11.1 | grt rounds 3 overflow 5:39297 -> 10:9376 -> 15:6005 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t39-243585 | ot_s81sl_leaf__t39 | 5_1_grt | 4.8 | grt rounds 2 overflow 5:179 -> 10:39 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 29.7 | grt rounds 3 overflow 5:62850 -> 10:60456 -> 15:49678 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 29.6 | grt rounds 4 overflow 5:56489 -> 10:43484 -> 15:40478 -> 20:43412 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 44.1 | grt rounds 4 overflow 5:9510 -> 10:5086 -> 15:3245 -> 20:2874 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 33.3 | grt rounds 4 overflow 5:54036 -> 10:38366 -> 15:34597 -> 20:37416 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-427216 | sle_st_a_v1 | 5_1_grt | 2.1 | grt rounds 2 overflow 5:4512 -> 10:1167 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-254386 | sle_st_a_v2 | 5_1_grt | 2.2 | grt rounds 2 overflow 5:12031 -> 10:4878 | GRT-LABEL: DESIGN-FAIL: overflow 4878 at round 10 > 1000 |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-425101 | sle_st_a_v2 | 5_1_grt | 2.1 | grt rounds 2 overflow 5:13907 -> 10:5441 | GRT-LABEL: DESIGN-FAIL: overflow 5441 at round 10 > 1000 |  |
| epyc2 | dpkit-slw_su_c__cl19bb38ef-2385009 | slw_su_c | 5_1_grt | 9.3 | grt rounds 2 overflow 5:27462 -> 10:11725 | GRT-LABEL: DESIGN-FAIL: overflow 11725 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 23.2 | grt rounds 3 overflow 5:76845 -> 10:71866 -> 15:58855 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 28.2 | grt rounds 3 overflow 5:61320 -> 10:67332 -> 15:69180 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 17.6 | grt rounds 3 overflow 5:50395 -> 10:49359 -> 15:39411 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 17.6 | grt rounds 3 overflow 5:50621 -> 10:49123 -> 15:39498 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 27.3 | grt rounds 3 overflow 5:77888 -> 10:49333 -> 15:43107 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 15.0 | grt rounds 3 overflow 5:79338 -> 10:74939 -> 15:54793 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 23.3 | grt rounds 3 overflow 5:71545 -> 10:71003 -> 15:50597 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 17.1 | grt rounds 3 overflow 5:73809 -> 10:69973 -> 15:51390 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 18.8 | grt rounds 4 overflow 5:42922 -> 10:39064 -> 15:36370 -> 20:37882 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 18.8 | grt rounds 4 overflow 5:41833 -> 10:36208 -> 15:31830 -> 20:31076 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_st_a_v2__pv4242de79-2391789 | sle_st_a_v2 | 5_1_grt | 2.5 | grt rounds 2 overflow 5:21672 -> 10:8153 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_1_grt | 2.6 | grt rounds 2 overflow 5:4526 -> 10:3466 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hgi_v2__cl2862d491-3732038 | kv3_hgi_v2 | 5_1_grt | 7.7 | grt rounds 2 overflow 5:72991 -> 10:37675 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 18.4 | grt rounds 4 overflow 5:19113 -> 10:12610 -> 15:11259 -> 20:10671 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_1_grt | 2.1 | grt rounds 2 overflow 5:22926 -> 10:4651 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-1897237 | slw_st_a_v2 | 5_1_grt | 2.1 | grt rounds 2 overflow 5:103 -> 10:56 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_1_grt | 1.9 | grt rounds 2 overflow 5:3304 -> 10:2843 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hgi_v8-3224135 | kv3_hgi_v8 | 5_1_grt | 11.9 | grt rounds 4 overflow 5:37484 -> 10:8165 -> 15:6005 -> 20:4797 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 31.3 | grt rounds 4 overflow 5:34386 -> 10:13016 -> 15:8921 -> 20:7819 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 42.0 | grt rounds 6 overflow 5:18899 -> 10:19233 -> 15:11889 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 42.3 | grt rounds 5 overflow 5:34987 -> 10:28632 -> 15:24645 -> 20:22699 -> 25:31808 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 5_1_grt | 19.3 | grt rounds 5 overflow 5:54170 -> 10:7759 -> 15:5073 -> 20:4181 -> 25:5669 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 24.8 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 19.8 | grt rounds 4 overflow 5:36131 -> 10:30276 -> 15:24310 -> 20:21320 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 41.1 | grt rounds 4 overflow 5:56283 -> 10:53405 -> 15:50242 -> 20:55216 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 36.1 | grt rounds 3 overflow 5:59246 -> 10:46138 -> 15:53864 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 36.1 | grt rounds 3 overflow 5:60515 -> 10:47029 -> 15:53055 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 36.3 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2275786 | col_h10_r2__t1 | 5_2_route | 6.3 | drt_violations best 15193 last 15193 rows 2 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-22377 | hd_lep0N | 4_2_tapbal_grt | 7.6 | last meaningful line 3.0 h ago (48/55 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t36-3668002 | slice_station__t36 | postcts_gate_FF | 5.3 | last meaningful line 0.0 h ago (1528/1528 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t37-173045 | slice_station__t37 | postcts_gate_FF | 4.8 | last meaningful line 0.0 h ago (1289/1289 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v3-1328903 | slw_fw_v3 | 5_2_route | 12.2 | drt_violations best 18167 last 18167 rows 2 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | otc-3502525-10491 | 3502525 | equiv_reset_alias | 0.3 | last meaningful line 0.1 h ago (790761/790761 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | otc-3735948-16317 | 3735948 | hierarchical_drc | 0.1 | last meaningful line 0.1 h ago (334/334 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1t-894339 | eco_20261121_154936_3396612-i1t | 5_2_route | 7.1 | last meaningful line 0.1 h ago (287/288 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_184648_4039100-i1-3762453 | eco_20261121_184648_4039100-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_203102_3392434-i1t-646001 | eco_20261121_203102_3392434-i1t | 5_2_route | 2.4 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl1b5a6458-1726234 | cbf_q00 | 3_4_place_resized | 1.1 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q01_s2-1733979 | cbf_q01_s2 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (50/50 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbx_q10__cl89936551_h-2367654 | cbx_q10 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3699/3699 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-2629912 | col_h9_r0_p2__t1 | 5_2_route | 12.3 | drt_violations best 135164 last 135164 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_kv512_C__t1-359428 | dsdv_slice_kv512_C__t1 | 3_4_place_resized | 2.2 | last meaningful line 0.0 h ago (418/418 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-hd_mesh-2472048 | hd_mesh | 5_1_grt | 12.4 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v5-244656 | kv3_hgi_v5 | 4_1_cts | 2.3 | last meaningful line 0.0 h ago (5945/5945 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 3_3_place_gp | 6.4 | overflow best 0.0992 last 0.0992 rows 45 | YOUNG: stage 0.8 h < 1 h |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | 4_1_cts | 3.4 | last meaningful line 0.2 h ago (7406/7406 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-native59-22224 | native59 | 3_5_place_dp | 2.4 | last meaningful line 0.2 h ago (111/111 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-native59-3868183 | native59 | pregrt_ff_hold | 5.0 | repair_TNS best 8684.22 last 8684.22 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2374083 | sle_hc1 | postcts_gate_FF | 12.5 | last meaningful line 0.0 h ago (731/731 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-248840 | sle_st_a_v1 | 5_1_grt | 2.3 | last meaningful line 0.7 h ago (207/215 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t36-3125329 | slice_station__t36 | 5_2_route | 8.8 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t51-342871 | slice_station__t51 | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2408517 | slw_fe_v1 | 5_2_route | 12.4 | last meaningful line 0.1 h ago (269/269 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3868961 | slw_sc_v1 | 5_1_grt | 5.0 | last meaningful line 0.0 h ago (887/890 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-844610 | slw_st_a_v1 | 5_1_grt | 1.8 | last meaningful line 0.2 h ago (201/208 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2420111 | slw_st_b_v2 | 5_2_route | 12.4 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | otc-2888712-11974 | 2888712 | asbuilt.yosys | 0.0 | last meaningful line -0.0 h ago (104/104 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_070700_2142563-i1-4024972 | eco_20261121_070700_2142563-i1 | 5_2_route | 2.5 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_080323_3018643-i1-1109108 | eco_20261121_080323_3018643-i1 | 5_2_route | 1.6 | last meaningful line 0.0 h ago (266/267 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_105744_956410-i1t-1036390 | eco_20261121_105744_956410-i1t | 5_2_route | 4.0 | drt_violations best 11576 last 11576 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_123328_2268168-i1t-4175816 | eco_20261121_123328_2268168-i1t | 5_2_route | 2.4 | last meaningful line 0.2 h ago (266/267 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_124930_2356681-i1t-415105 | eco_20261121_124930_2356681-i1t | 5_2_route | 2.1 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | so_2676771_ff_74724 | so_2676771_ff_74724 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | so_2676771_tt_74724 | so_2676771_tt_74724 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-bk_sel__t2-3723154 | bk_sel__t2 | 5_1_grt | 1.7 | last meaningful line 0.3 h ago (202/205 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q00__cldbcda913-850288 | cbn_q00 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (4898/4898 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-582858 | cbn_q01 | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (5874/5874 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-993515 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 5.6 | repair_TNS best 23538.3 last 23538.3 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hg_v1p2-3964783 | kv3_hg_v1p2 | 3_5_place_dp | 1.5 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t12-331217 | serdes__t12 | 3_4_place_resized | 1.1 | last meaningful line 0.0 h ago (344/344 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | 4_1_cts | 0.9 | last meaningful line 0.1 h ago (9008/9008 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (5620/5620 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2969215 | sle_hc0 | 4_1_cts | 2.3 | last meaningful line 0.0 h ago (5579/5579 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve230954c-1731757 | sle_hc1 | 5_1_grt | 8.7 | last meaningful line 0.3 h ago (213/896 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-1459492 | sle_hc1 | 5_2_route | 12.4 | drt_violations best 101196 last 101196 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-3504337 | sle_hc1 | 4_1_cts | 1.9 | last meaningful line 0.2 h ago (5749/5749 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cle683a076-3820341 | slw_hc1 | 4_1_cts | 1.7 | last meaningful line 0.2 h ago (5458/5458 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3669665 | slw_st_b_v1 | pregrt_ff_hold | 1.8 | repair_TNS best 18840.2 last 18840.2 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | otc-1390878-19193 | 1390878 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | otc-1428496-29152 | 1428496 | 6_report | 0.1 | last meaningful line 0.0 h ago (87/87 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_100942_929932-i1-3347652 | eco_20261121_100942_929932-i1 | 5_2_route | 3.6 | drt_violations best 65 last 65 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_173326_4009105-i1-295057 | eco_20261121_173326_4009105-i1 | 5_2_route | 1.1 | last meaningful line 0.1 h ago (136/136 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_184012_3245689-i1t-2500922 | eco_20261121_184012_3245689-i1t | 5_2_route | 4.1 | drt_violations best 5501 last 5501 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_193535_3253336-i1t-4078609 | eco_20261121_193535_3253336-i1t | 5_2_route | 3.4 | drt_violations best 19860 last 19860 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_203749_4020394-i1-2795396 | eco_20261121_203749_4020394-i1 | 5_2_route | 2.3 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q00__cld7bf7197-3404310 | cbn_q00 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (5091/5091 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q11__cl49ae4555-3905648 | cbn_q11 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (4305/4305 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-2597778 | col_h9_r0_p2__t1 | 5_1_grt | 1.5 | last meaningful line 0.3 h ago (41/41 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | 5_1_grt | 2.7 | last meaningful line 1.0 h ago (39/39 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_1_grt | 2.7 | last meaningful line 0.5 h ago (39/39 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor-3733934 | kv3_io_cor | 6_report | 7.7 | last meaningful line 0.1 h ago (1070/1070 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t14-3301476 | serdes__t14 | 3_3_place_gp | 0.9 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-3274788 | serdes__t1 | 5_2_route | 11.6 | drt_violations best 114810 last 114810 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa-1023417 | sle_hc0 | postcts_gate_FF | 9.6 | last meaningful line 0.1 h ago (765/765 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3985339 | sle_hc2 | 5_1_grt | 7.5 | last meaningful line 0.1 h ago (963/980 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-1013642 | sle_hc2 | postcts_gate_FF | 9.6 | last meaningful line 0.1 h ago (777/777 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-850569 | slw_fe_v1 | postcts_gate_FF | 9.7 | last meaningful line -0.0 h ago (79971/79971 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-2906124 | slw_hc1 | postcts_gate_TT | 11.9 | last meaningful line -0.0 h ago (82588/82588 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1012001 | slw_hc3 | 5_2_route | 9.6 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-1012945 | slw_hc3 | 5_2_route | 9.6 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | otc-3509414-20478 | 3509414 | gate.ys | 0.7 | last meaningful line 0.5 h ago (51328/51328 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | otc-3794871-12099 | 3794871 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261121_214321_3818039-i1t-2911659 | eco_20261121_214321_3818039-i1t | 5_2_route | 1.2 | last meaningful line 0.1 h ago (255/256 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3350653 | col_h9_r1__t1 | 5_2_route | 8.7 | drt_violations best 1927 last 1927 rows 4 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hg-1650521 | kv3_hg | port_bind | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-1513640 | sle_hc0 | 5_2_route | 10.2 | drt_violations best 93214 last 93214 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2616668 | sle_hc1 | postcts_gate_TT | 9.3 | last meaningful line 0.1 h ago (405/405 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | eco-abs-1602048 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.1 h ago (551/551 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-1494620-16385 | 1494620 | 3_3_place_gp | 0.3 | overflow best 0.279 last 0.279 rows 36 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | otc-1713770-16189 | 1713770 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-3085280-30126 | 3085280 | - | 14.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 14.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 14.3 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261121_070035_1645318-i2t-1219117 | eco_20261121_070035_1645318-i2t | 5_2_route | 0.7 | last meaningful line 0.1 h ago (266/267 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_154823_2000128-i2-4171153 | eco_20261121_154823_2000128-i2 | 5_2_route | 2.6 | drt_violations best 254 last 254 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 4.0 | drt_violations best 3018 last 3018 rows 12 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_195859_2616880-i1-966712 | eco_20261121_195859_2616880-i1 | 5_2_route | 1.1 | drt_violations best 6152 last 6152 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | prd-eco_20261121_201548_1094504-i1-1641941 | eco_20261121_201548_1094504-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-4146127 | col_h10_r2__t1 | 5_2_route | 11.4 | drt_violations best 57 last 57 rows 8 | YOUNG: evidence 5.9 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | 5_2_route | 19.3 | drt_violations best 91173 last 91173 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-2204474 | slw_st_b_v1 | 5_2_route | 12.4 | last meaningful line 0.2 h ago (133/133 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i2t-1252392 | eco_20261120_192428_3309571-i2t | 5_2_route | 2.7 | drt_violations best 34043 last 34043 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | prd-fin-2520913 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (1070/1070 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3655958 | coll_ftm | 5_2_route | 2.0 | drt_violations best 9684 last 9684 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-2185319 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (216/217 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-3165684 | hd_turn_a | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (108/108 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-1149261 | kv3_io_ft | 5_2_route | 1.2 | drt_violations best 5406 last 5406 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-2212511 | slice_station__t12 | 5_1_grt | 0.2 | repair_Remaining best 13223 last 13223 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slice_station__t24__cl66b71008-3119345 | slice_station__t24 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | otc-2246034-6849 | 2246034 | - | 0.2 |  | NO-DATA: no log found |  |
| intel2 | prd-eco_20261121_115902_173230-i1t-1237159 | eco_20261121_115902_173230-i1t | 5_2_route | 3.0 | drt_violations best 4890 last 4890 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel2 | prd-fin-3971139 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (595/595 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 31.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | otc-3261676-29903 | 3261676 | - | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-100513 | eco1-i1 | 5_2_route | 11.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-1617813 | eco1-i1 | 5_2_route | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-1714380 | eco1-i1 | 5_2_route | 2.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-4178763 | eco1-i1 | 5_2_route | 4.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-hd_lep0N-1588394 | hd_lep0N | pregrt_ff_hold | 9.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-serdes__t4-293755 | serdes__t4 | 5_1_grt | 4.8 | repair_TNS best 0 last 0 rows 20 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_2_route | 19.6 | drt_violations best 10168 last 49296 rows 18 | before-window best 11104, window best 10168 | PROGRESS: drt_violations improved 8.4 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 36.2 | last meaningful line 0.2 h ago (1499/1499 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-425190 | sle_su_l1 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | 5_1_grt | 8.0 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-1019838 | slw_sc_v1 | pregrt_ff_hold | 1.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_2_route | 21.8 | drt_violations best 9327 last 39114 rows 18 | before-window best 11011, window best 9327 | PROGRESS: drt_violations improved 15.3 % in window |  |
| epyc2 | prd-eco_20261120_170022_4017640-i2t-2328774 | eco_20261120_170022_4017640-i2t | 5_2_route | 9.4 | drt_violations best 98 last 98 rows 12 | before-window best 72780, window best 98 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 12.1 | drt_violations best 2 last 2 rows 48 | before-window best 3, window best 2 | PROGRESS: drt_violations improved 33.3 % in window |  |
| epyc2 | prd-eco_20261121_102155_957464-i1t-245136 | eco_20261121_102155_957464-i1t | 5_2_route | 4.6 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-cbf_q11-3840796 | cbf_q11 | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v2-3695652 | slw_sc_v2 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_2_route | 22.7 | drt_violations best 13126 last 54684 rows 18 | before-window best 13507, window best 13126 | PROGRESS: drt_violations improved 2.8 % in window |  |
| epyc7 | otc-1066871-28645 | 1066871 | 4_1_cts | 0.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | 5_2_route | 18.4 | drt_violations best 15 last 15 rows 52 | before-window best 24, window best 15 | PROGRESS: drt_violations improved 37.5 % in window |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | 5_2_route | 18.4 | drt_violations best 27 last 27 rows 50 | before-window best 55, window best 27 | PROGRESS: drt_violations improved 50.9 % in window |  |
| epyc8 | dpkit-dsdv_slice_lepe_mu_LP__t2-3534677 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-glue-504992 | glue | pregrt_ff_hold | 6.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-1899674 | slw_fe_v1 | 5_1_grt | 9.0 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-1964882 | slw_su_l0 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | 5_2_route | 19.1 | drt_violations best 39637 last 39637 rows 2 | before-window best 203629, window best 39637 | PROGRESS: drt_violations improved 80.5 % in window |  |
| intel1 | dpkit-sle_ctl__cl67434795-622153 | sle_ctl | pregrt_ff_hold | 13.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_075836_1991905-i1t-1821063 | eco_20261121_075836_1991905-i1t | 5_2_route | 7.0 | drt_violations best 10385 last 10385 rows 4 | before-window best 190712, window best 10385 | PROGRESS: drt_violations improved 94.6 % in window |  |
| intel1 | prd-eco_20261121_082001_3216437-i1t-2148021 | eco_20261121_082001_3216437-i1t | 5_2_route | 6.6 | drt_violations best 7202 last 7202 rows 4 | before-window best 185697, window best 7202 | PROGRESS: drt_violations improved 96.1 % in window |  |
| intel2 | prd-eco_20261121_072804_212710-i1-2335895 | eco_20261121_072804_212710-i1 | 5_2_route | 2.6 | drt_violations best 0 last 0 rows 1 | PROGRESS: drt_violations reached 0 |  |
