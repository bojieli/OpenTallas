# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 12:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'CANCEL-NOW': 1, 'GRT-LABEL': 29, 'YOUNG': 123, 'NO-DATA': 14, 'EXCLUDED': 8, 'KEEP': 1, 'PROGRESS': 30}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 28.9 | grt rounds 6 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -2893.36 ps (< -300, gate TT >= -42); job age 2 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 42.3 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 42 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-1242636 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 5_1_grt | 0.7 |  | CANCEL-NOW: HBM is parked | CANCELLED |
| epyc10 | dpkit-kv3_hgi_v8-3126306 | kv3_hgi_v8 | 5_1_grt | 8.8 | grt rounds 2 overflow 5:51928 -> 10:23820 | GRT-LABEL: DESIGN-FAIL: overflow 23820 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 27.4 | grt rounds 3 overflow 5:62850 -> 10:60456 -> 15:49611 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 27.4 | grt rounds 4 overflow 5:56489 -> 10:43484 -> 15:40478 -> 20:43612 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 41.8 | grt rounds 4 overflow 5:9510 -> 10:5086 -> 15:3391 -> 20:2910 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 31.1 | grt rounds 4 overflow 5:51489 -> 10:38067 -> 15:34597 -> 20:37416 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 21.0 | grt rounds 3 overflow 5:77963 -> 10:71866 -> 15:58855 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 25.9 | grt rounds 3 overflow 5:61289 -> 10:67332 -> 15:69180 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 15.3 | grt rounds 3 overflow 5:50395 -> 10:49359 -> 15:39411 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 15.3 | grt rounds 3 overflow 5:50187 -> 10:49123 -> 15:39498 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 25.1 | grt rounds 3 overflow 5:46870 -> 10:49482 -> 15:43107 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 12.8 | grt rounds 3 overflow 5:79338 -> 10:75315 -> 15:54687 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 21.0 | grt rounds 3 overflow 5:71545 -> 10:71003 -> 15:50597 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 14.8 | grt rounds 3 overflow 5:73809 -> 10:69973 -> 15:51022 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 16.6 | grt rounds 4 overflow 5:42922 -> 10:39064 -> 15:36370 -> 20:37813 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 16.5 | grt rounds 4 overflow 5:41833 -> 10:36208 -> 15:31830 -> 20:32437 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hgi_v2__cl2862d491-3732038 | kv3_hgi_v2 | 5_1_grt | 5.5 | grt rounds 2 overflow 5:72991 -> 10:37675 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 16.2 | grt rounds 4 overflow 5:19113 -> 10:12610 -> 15:11530 -> 20:10671 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hgi_v2__cle0015330-660102 | kv3_hgi_v2 | 5_1_grt | 5.0 | grt rounds 2 overflow 5:59354 -> 10:37389 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hgi_v8-3224135 | kv3_hgi_v8 | 5_1_grt | 9.6 | grt rounds 3 overflow 5:39297 -> 10:9376 -> 15:15865 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 29.0 | grt rounds 3 overflow 5:26517 -> 10:13016 -> 15:8921 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 39.8 | grt rounds 6 overflow 5:18899 -> 10:21694 -> 15:12971 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 40.0 | grt rounds 4 overflow 5:34987 -> 10:28632 -> 15:24645 -> 20:22699 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 5_1_grt | 17.1 | grt rounds 4 overflow 5:54170 -> 10:7759 -> 15:5073 -> 20:4181 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 22.5 | grt rounds 5 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 17.5 | grt rounds 4 overflow 5:36131 -> 10:30276 -> 15:24310 -> 20:22194 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 38.9 | grt rounds 3 overflow 5:56283 -> 10:53405 -> 15:50242 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 33.9 | grt rounds 3 overflow 5:59246 -> 10:47822 -> 15:53864 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 33.9 | grt rounds 3 overflow 5:60515 -> 10:48832 -> 15:53055 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 34.1 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9864 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2275786 | col_h10_r2__t1 | 5_1_grt | 4.0 | last meaningful line 0.1 h ago (1480/1510 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-2582333 | col_h9_r0_p2__t1 | 5_2_route | 9.2 | last meaningful line 0.2 h ago (289/290 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-22377 | hd_lep0N | 4_2_tapbal_grt | 5.4 | last meaningful line 0.8 h ago (48/50 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1-2739404 | kv3_hg_v1 | 3_3_place_gp | 1.2 | overflow best 0.1994 last 0.1994 rows 38 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-kv3_hgi_v3-114444 | kv3_hgi_v3 | 3_3_place_gp | 0.5 | last meaningful line -0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Eo-2185518 | kv3_hub_Eo | 3_3_place_gp | 1.5 | overflow best 0.2579 last 0.2654 rows 33 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t39-243585 | ot_s81sl_leaf__t39 | 5_1_grt | 2.6 | last meaningful line 0.3 h ago (204/210 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t4-293755 | serdes__t4 | 5_1_grt | 2.5 | last meaningful line 0.0 h ago (182/182 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_stm_v2__cl55be2264-3762017 | sle_stm_v2 | 3_5_place_dp | 0.8 | last meaningful line 0.1 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t36-3668002 | slice_station__t36 | 5_1_grt | 3.1 | last meaningful line 1.1 h ago (215/694 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v3-1328903 | slw_fw_v3 | 5_2_route | 9.9 | last meaningful line 0.0 h ago (270/271 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | otc-3133178-2913 | 3133178 | gen_lint_yosys | 1.0 | last meaningful line 1.0 h ago (1/1 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | otc-40400-27015 | 40400 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc10 | prd-eco_20261121_014354_2681516-i3-1261179 | eco_20261121_014354_2681516-i3 | 5_2_route | 2.0 | drt_violations best 360 last 360 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1t-894339 | eco_20261121_154936_3396612-i1t | 5_1_grt | 4.9 | repair_Viol best 2419 last 2419 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_184648_4039100-i1t-1413255 | eco_20261121_184648_4039100-i1t | 5_2_route | 1.9 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_203102_3392434-i1t-646001 | eco_20261121_203102_3392434-i1t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (155/155 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-slw-st-a-v2--cl9f076a5c-grt-61332 | slw-st-a-v2--cl9f076a5c-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl870de686-3870117 | cbf_q00 | pregrt_ff_hold | 2.7 | repair_TNS best 3.60575e+06 last 3.60575e+06 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q01__clab6e67f2-19353 | cbn_q01 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 284 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-2629912 | col_h9_r0_p2__t1 | 5_2_route | 10.1 | drt_violations best 135164 last 135164 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v5-244656 | kv3_hgi_v5 | 1_2_yosys | 0.0 | last meaningful line -0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 2_3_floorplan_tapcell | 4.2 | last meaningful line -0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | 4_1_cts | 1.1 | last meaningful line 1.0 h ago (7042/7042 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4n-4044420 | kv3_pv_v4n | 3_5_place_dp | 6.0 | last meaningful line 0.5 h ago (58/58 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v5n-4101656 | kv3_pv_v5n | 3_4_place_resized | 6.0 | last meaningful line 1.0 h ago (752/752 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-native59-22224 | native59 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (495/495 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-native59-3868183 | native59 | 4_1_cts | 2.7 | last meaningful line 0.0 h ago (5239/5239 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t14-3447555 | serdes__t14 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.1 h ago (92/92 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t16-1729365 | serdes__t16 | 3_3_place_gp | 1.3 | overflow best 0.7175 last 0.7175 rows 29 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2762287 | sle_fw_v1 | 3_3_place_gp | 0.8 | overflow best 0.0999 last 0.0999 rows 47 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2761739 | sle_fw_v1 | 3_3_place_gp | 0.8 | overflow best 0.3728 last 0.3728 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-18148 | sle_fw_v2 | 2_1_floorplan | 0.1 | last meaningful line 0.1 h ago (86/86 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2735775 | sle_hc1 | 3_3_place_gp | 0.8 | overflow best 0.2998 last 0.4701 rows 130 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2374083 | sle_hc1 | 5_1_grt | 10.2 | last meaningful line 0.5 h ago (212/952 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2746212 | sle_hc1 | 3_3_place_gp | 0.8 | overflow best 0.301 last 0.545 rows 117 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-248840 | sle_st_a_v1 | 1_1_yosys_canonicalize | 0.0 | last meaningful line -0.0 h ago (40/40 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2847822 | sle_stm_v1 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (50/50 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t18-249551 | slice_station__t18 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t36-3125329 | slice_station__t36 | postcts_gate_FF | 6.6 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2408517 | slw_fe_v1 | postcts_gate_TT | 10.2 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-2789993 | slw_fe_v2 | 3_3_place_gp | 0.8 | overflow best 0.4346 last 0.4346 rows 20 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3032983 | slw_fw_v1 | 3_3_place_gp | 0.7 | last meaningful line 0.0 h ago (235/235 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2449519 | slw_hc3 | 5_2_route | 10.2 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2817277 | slw_sc_v1 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (384/384 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v2-2660942 | slw_sc_v2 | 5_1_grt | 4.0 | last meaningful line 0.1 h ago (196/199 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2420111 | slw_st_b_v2 | postcts_gate_TT | 10.2 | last meaningful line 0.1 h ago (1101/1101 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_c__cl19bb38ef-3446986 | slw_su_c | 3_3_place_gp | 0.5 | overflow best 0.5104 last 0.5104 rows 8 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | otc-180679-7619 | 180679 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i3-297348 | eco_20261120_134605_3273412-i3 | 5_2_route | 2.3 | drt_violations best 17645 last 17645 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_070700_2142563-i1-4024972 | eco_20261121_070700_2142563-i1 | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (145/145 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_102155_957464-i1t-245136 | eco_20261121_102155_957464-i1t | 5_2_route | 2.3 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_105744_956410-i1t-1036390 | eco_20261121_105744_956410-i1t | 5_2_route | 1.8 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_123328_2268168-i1t-4175816 | eco_20261121_123328_2268168-i1t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | so_3117836_ff_30095 | so_3117836_ff_30095 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc2 | so_3117836_tt_30095 | so_3117836_tt_30095 | signoff | 0.7 |  | NO-DATA: empty log |  |
| epyc2 | so_3796756_ff_84508 | so_3796756_ff_84508 | generate_abstract | 0.4 | last meaningful line 0.2 h ago (707/707 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | so_3796756_tt_84508 | so_3796756_tt_84508 | generate_abstract | 0.4 | last meaningful line 0.2 h ago (707/707 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-sle-st-a-v2--pv30dda31f--pvd2ec7769-grt-2731043 | sle-st-a-v2--pv30dda31f--pvd2ec7769-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-slw-su-l0--cl1a1c1f8f-grt-2919808 | slw-su-l0--cl1a1c1f8f-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-bk_sel__t2-1136009 | bk_sel__t2 | 3_3_place_gp | 0.7 | overflow best 0.2114 last 0.2163 rows 37 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-cbf_q00_s2-2812888 | cbf_q00_s2 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 111 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-cbf_q11-1342043 | cbf_q11 | 3_4_place_resized | 0.6 | last meaningful line -0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-2115469 | cbn_q01 | 3_3_place_gp | 0.4 | last meaningful line -0.0 h ago (129/129 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q11__cl5cc92dfe-2809953 | cbn_q11 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 274 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-cbx_q10__cl89936551-2741700 | cbx_q10 | 2_1_floorplan | 0.1 | repair_Viol best 4612 last 4612 rows 576 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-cbx_q10__cl89936551_h-2224155 | cbx_q10 | 3_3_place_gp | 0.3 | overflow best 0.4744 last 0.4744 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-cbx_q10__cl94a12200_h-2223621 | cbx_q10 | 3_3_place_gp | 0.3 | overflow best 0.2969 last 0.3201 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-kv3_hg_v1p2-3294731 | kv3_hg_v1p2 | 3_5_place_dp | 1.4 | last meaningful line 0.1 h ago (46/46 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-616014 | sle_ctl | 3_3_place_gp | 0.8 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-149983 | sle_fe_v1 | 3_4_place_resized | 1.0 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2969215 | sle_hc0 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-1459492 | sle_hc1 | postcts_gate_FF | 10.1 | last meaningful line -0.0 h ago (86176/86176 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-3979568 | sle_hc1 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv4242de79-2391789 | sle_st_a_v2 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (6102/6102 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v1__pv0e7b1dcc-1217547 | sle_st_b_v1 | 3_3_place_gp | 0.6 | overflow best 0.2166 last 0.2166 rows 40 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-2160304 | sle_st_b_v1 | 3_3_place_gp | 0.4 | overflow best 0.7547 last 0.7547 rows 6 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cle683a076-3970050 | slw_hc1 | 3_3_place_gp | 1.1 | overflow best 0.0993 last 0.0993 rows 227 | YOUNG: stage 0.8 h < 1 h |  |
| epyc7 | prd-eco_20261121_100942_929932-i1-3347652 | eco_20261121_100942_929932-i1 | 5_1_grt | 1.3 | last meaningful line 0.8 h ago (236/1334 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_173326_4009105-i1t-1250567 | eco_20261121_173326_4009105-i1t | 5_2_route | 3.1 | drt_violations best 13019 last 13019 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_184012_3245689-i1t-2500922 | eco_20261121_184012_3245689-i1t | 5_2_route | 1.9 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_193535_3253336-i1t-4078609 | eco_20261121_193535_3253336-i1t | 5_2_route | 1.1 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_203749_4020394-i1-2795396 | eco_20261121_203749_4020394-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | so_2736504_ff_33535 | so_2736504_ff_33535 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | so_2736504_tt_33535 | so_2736504_tt_33535 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | clkgrtff-hookra_seg-1554446 | clkgrtff-hookra_seg | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-cbn_q11__cl49ae4555-1289900 | cbn_q11 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1593385 | col_h9_r0_p2__t1 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (1418/1418 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | tt_setup_repair | 0.4 | repair_Viol best 182 last 182 rows 74 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | tt_setup_repair | 0.4 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-coll_core-783129 | coll_core | 3_3_place_gp | 0.6 | overflow best 0.6295 last 0.6325 rows 14 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-coll_ftc-745291 | coll_ftc | 3_3_place_gp | 0.6 | overflow best 0.0995 last 0.0995 rows 43 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_mu_LP__t2-3534677 | dsdv_slice_lepe_mu_LP__t2 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (4350/4350 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-hd_host_e-3833588 | hd_host_e | 5_2_route | 5.4 | drt_violations best 27 last 27 rows 56 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hroot-4110897 | kv3_hroot | 5_2_route | 5.2 | last meaningful line 0.2 h ago (250/251 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor-3733934 | kv3_io_cor | 5_2_route | 5.5 | drt_violations best 45858 last 45858 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-3818815 | kv3_io_cor_v1 | 5_2_route | 5.4 | drt_violations best 6 last 6 rows 57 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-3274788 | serdes__t1 | 5_2_route | 9.3 | last meaningful line 0.2 h ago (294/295 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa-1023417 | sle_hc0 | 5_1_grt | 7.3 | last meaningful line 1.0 h ago (211/941 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1295515 | sle_hc1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9982 last 0.9982 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-1013642 | sle_hc2 | 5_1_grt | 7.3 | last meaningful line 0.7 h ago (210/900 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl115da35f-1093172 | sle_sc_v1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.1724 last 0.1793 rows 44 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-1899674 | slw_fe_v1 | 5_1_grt | 6.7 | repair_Remaining best 223699 last 223699 rows 166 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-850569 | slw_fe_v1 | 5_1_grt | 7.5 | last meaningful line 2.2 h ago (217/1463 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-2906124 | slw_hc1 | 5_1_grt | 9.6 | repair_Remaining best 130401 last 130401 rows 360 | YOUNG: stage 0.6 h < 1 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1012001 | slw_hc3 | 5_1_grt | 7.3 | last meaningful line 0.5 h ago (210/963 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1352564 | slw_st_a_v1 | 3_3_place_gp | 0.3 | overflow best 0.302 last 0.3143 rows 30 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-1278911 | slw_st_a_v2 | 3_4_place_resized | 0.3 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-1547845-17008 | 1547845 | orfs_flow | 3.5 | repair_Viol best 93 last 93 rows 33 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc8 | otc-1576193-17345 | 1576193 | gold.ys | 0.1 | last meaningful line 0.1 h ago (10689/10689 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-1731407-20660 | 1731407 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 55.9 |  | NO-DATA: no log found |  |
| epyc8 | otc-559540-13695 | 559540 | route | 4.6 | last meaningful line 0.2 h ago (470/470 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3350653 | col_h9_r1__t1 | 5_2_route | 6.5 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-1513640 | sle_hc0 | postcts_gate_FF | 7.9 | last meaningful line 0.1 h ago (372/372 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-882856 | slw_hc3 | 5_2_route | 8.4 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | otc-3085280-30126 | 3085280 | - | 12.4 |  | NO-DATA: no log found |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 12.4 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 12.0 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261121_070035_1645318-i1-2327283 | eco_20261121_070035_1645318-i1 | 5_2_route | 2.8 | drt_violations best 7857 last 7857 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_143815_74711-i2-3554105 | eco_20261121_143815_74711-i2 | 5_2_route | 1.2 | last meaningful line 0.2 h ago (259/260 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 1.7 | last meaningful line 0.1 h ago (271/272 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_195859_2616880-i1t-3870494 | eco_20261121_195859_2616880-i1t | 5_2_route | 0.8 | last meaningful line 0.0 h ago (253/254 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_201548_1094504-i1t-4087489 | eco_20261121_201548_1094504-i1t | 5_2_route | 0.5 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-4146127 | col_h10_r2__t1 | 5_2_route | 9.1 | drt_violations best 85869 last 85869 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | 5_2_route | 17.0 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | prd-eco1-i1-2520913 | eco1-i1 | 5_2_route | 10.0 | drt_violations best 112 last 112 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i2t-1252392 | eco_20261120_192428_3309571-i2t | 5_2_route | 0.4 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261121_075836_1991905-i1t-1821063 | eco_20261121_075836_1991905-i1t | 5_2_route | 4.7 | drt_violations best 190712 last 190712 rows 1 | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i1t-2148021 | eco_20261121_082001_3216437-i1t | 5_2_route | 4.4 | drt_violations best 185697 last 185697 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel2 | dpkit-coll_core-1128328 | coll_core | 3_4_place_resized | 0.8 | last meaningful line 0.1 h ago (361/361 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-1242372 | kv3_io_ft | 5_2_route | 0.7 | last meaningful line 0.0 h ago (216/217 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | prd-eco_20261121_072804_212710-i1-2335895 | eco_20261121_072804_212710-i1 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (229/247 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | prd-eco_20261121_111944_190475-i1-3971139 | eco_20261121_111944_190475-i1 | 5_2_route | 1.4 | last meaningful line 0.1 h ago (134/134 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | prd-eco_20261121_115902_173230-i1t-1237159 | eco_20261121_115902_173230-i1t | 5_1_grt | 0.7 | last meaningful line 0.3 h ago (229/1308 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | so_2629767_ff_98462 | so_2629767_ff_98462 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel2 | so_2629767_tt_98462 | so_2629767_tt_98462 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc10 | otc-340662-9775 | 340662 | - | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | otc-666311-18648 | 666311 | asbuilt.yosys | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | otc-924821-31887 | 924821 | asbuilt.yosys | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 29.6 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-eco1-i1-100513 | eco1-i1 | 5_2_route | 9.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-4178763 | eco1-i1 | 5_2_route | 2.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-92562 | eco1-i1 | 5_2_route | 9.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-fin-1671443 | fin | 6_report | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-fin-1673812 | fin | 6_report | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-hd_lep0N-1588394 | hd_lep0N | pregrt_ff_hold | 7.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slice_station__t36-3913104 | slice_station__t36 | 5_2_route | 5.6 | drt_violations best 0 last 0 rows 8 | PROGRESS: drt_violations reached 0 |  |
| epyc10 | dpkit-slice_station__t37-173045 | slice_station__t37 | 5_1_grt | 2.6 | repair_TNS best 0 last 0 rows 16 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_2_route | 17.4 | drt_violations best 10389 last 10389 rows 16 | before-window best 14325, window best 10389 | PROGRESS: drt_violations improved 27.5 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 34.0 | last meaningful line 0.9 h ago (1493/1493 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-hd_mesh-2472048 | hd_mesh | pregrt_ff_hold | 10.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | pregrt_ff_hold | 5.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3868961 | slw_sc_v1 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_su_c__cl19bb38ef-2385009 | slw_su_c | pregrt_ff_hold | 7.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | 5_2_route | 23.4 | drt_violations best 9406 last 49919 rows 18 | before-window best 9588, window best 9406 | PROGRESS: drt_violations: falling inside the active iteration (49919 -> 24173) |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_2_route | 19.6 | drt_violations best 9551 last 9551 rows 16 | before-window best 13013, window best 9551 | PROGRESS: drt_violations improved 26.6 % in window |  |
| epyc2 | prd-eco_20261120_170022_4017640-i2t-2328774 | eco_20261120_170022_4017640-i2t | 5_2_route | 7.1 | drt_violations best 99 last 99 rows 11 | before-window best 72780, window best 99 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 9.9 | drt_violations best 3 last 20 rows 42 | before-window best 8867, window best 3 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc2 | prd-eco_20261121_080323_3018643-i1t-1786242 | eco_20261121_080323_3018643-i1t | 5_2_route | 4.7 | drt_violations best 0 last 0 rows 16 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-993515 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve230954c-1731757 | sle_hc1 | pregrt_ff_hold | 6.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l0__cl1a1c1f8f-1472945 | slw_su_l0 | 5_2_route | 10.1 | drt_violations best 4 last 4 rows 47 | before-window best 47342, window best 4 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | pregrt_ff_hold | 0.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_2_route | 20.5 | drt_violations best 13126 last 54684 rows 18 | before-window best 14002, window best 13126 | PROGRESS: drt_violations improved 6.3 % in window |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | 5_2_route | 16.2 | drt_violations best 15 last 15 rows 50 | before-window best 609, window best 15 | PROGRESS: drt_violations improved 97.5 % in window |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | 5_2_route | 16.2 | drt_violations best 27 last 27 rows 50 | before-window best 346, window best 27 | PROGRESS: drt_violations improved 92.2 % in window |  |
| epyc8 | dpkit-glue-504992 | glue | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3985339 | sle_hc2 | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-1012945 | slw_hc3 | 5_1_grt | 7.3 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2616668 | sle_hc1 | pregrt_ff_hold | 7.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | prd-eco_20261121_154823_2000128-i2-4171153 | eco_20261121_154823_2000128-i2 | 5_1_grt | 0.4 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | 5_2_route | 16.8 | drt_violations best 203629 last 203629 rows 1 | before-window best 203629, window best 203629 | PROGRESS: drt_violations: active iteration at 116334 < best completed total 203629 (in-ite |  |
| intel1 | dpkit-sle_ctl__cl67434795-622153 | sle_ctl | pregrt_ff_hold | 11.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-2204474 | slw_st_b_v1 | 5_1_grt | 10.2 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slice_station__t12-936184 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 0 last 0 rows 4 | PROGRESS: drt_violations reached 0 |  |
