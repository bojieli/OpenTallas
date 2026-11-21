# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 13:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 1, 'CANCEL-NOW': 1, 'GRT-LABEL': 30, 'YOUNG': 133, 'NO-DATA': 9, 'EXCLUDED': 7, 'KEEP': 1, 'PROGRESS': 23}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 29.1 | grt rounds 6 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -2893.36 ps (< -300, gate TT >= -42); job age 2 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 42.6 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 42 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | 5_2_route | 23.7 | drt_violations best 9406 last 22242 rows 19 | before-window best 9480, window best 9406 | NO-PROGRESS: drt_violations best 9406 vs 9480 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-2690547 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 5_2_route | 0.2 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-kv3_hgi_v8-3126306 | kv3_hgi_v8 | 5_1_grt | 9.1 | grt rounds 3 overflow 5:51928 -> 10:23820 -> 15:26195 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t39-243585 | ot_s81sl_leaf__t39 | 5_1_grt | 2.8 | grt rounds 2 overflow 5:179 -> 10:39 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 27.7 | grt rounds 3 overflow 5:62850 -> 10:60456 -> 15:49611 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 27.6 | grt rounds 4 overflow 5:56489 -> 10:43484 -> 15:40478 -> 20:43612 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 42.1 | grt rounds 4 overflow 5:9510 -> 10:5086 -> 15:3391 -> 20:2910 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 31.3 | grt rounds 4 overflow 5:51489 -> 10:38067 -> 15:34597 -> 20:37416 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 21.2 | grt rounds 3 overflow 5:77963 -> 10:71866 -> 15:58855 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 26.2 | grt rounds 3 overflow 5:61320 -> 10:67332 -> 15:69180 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 15.6 | grt rounds 3 overflow 5:50395 -> 10:49359 -> 15:39411 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 15.6 | grt rounds 3 overflow 5:50187 -> 10:49123 -> 15:39498 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 25.3 | grt rounds 3 overflow 5:46870 -> 10:49482 -> 15:43107 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 13.0 | grt rounds 3 overflow 5:79338 -> 10:75315 -> 15:54687 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 21.3 | grt rounds 3 overflow 5:71545 -> 10:71003 -> 15:50597 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 15.1 | grt rounds 3 overflow 5:73809 -> 10:69973 -> 15:51022 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 16.8 | grt rounds 4 overflow 5:42922 -> 10:39064 -> 15:36370 -> 20:37813 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 16.8 | grt rounds 4 overflow 5:41833 -> 10:36208 -> 15:31830 -> 20:32437 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hgi_v2__cl2862d491-3732038 | kv3_hgi_v2 | 5_1_grt | 5.7 | grt rounds 2 overflow 5:72991 -> 10:37675 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 16.4 | grt rounds 4 overflow 5:19113 -> 10:12610 -> 15:11530 -> 20:10671 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hgi_v2__cle0015330-660102 | kv3_hgi_v2 | 5_1_grt | 5.3 | grt rounds 2 overflow 5:59354 -> 10:37389 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hgi_v8-3224135 | kv3_hgi_v8 | 5_1_grt | 9.9 | grt rounds 3 overflow 5:39297 -> 10:9376 -> 15:15865 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 29.3 | grt rounds 3 overflow 5:26517 -> 10:13016 -> 15:8921 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 40.0 | grt rounds 6 overflow 5:18899 -> 10:21694 -> 15:12971 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 40.3 | grt rounds 4 overflow 5:34987 -> 10:28632 -> 15:24645 -> 20:22699 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 5_1_grt | 17.3 | grt rounds 4 overflow 5:54170 -> 10:7759 -> 15:5073 -> 20:4181 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 22.8 | grt rounds 5 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 17.8 | grt rounds 4 overflow 5:36131 -> 10:30276 -> 15:24310 -> 20:22194 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 39.1 | grt rounds 3 overflow 5:56283 -> 10:53405 -> 15:50242 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 34.1 | grt rounds 3 overflow 5:59246 -> 10:47822 -> 15:53864 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 34.1 | grt rounds 3 overflow 5:60515 -> 10:48832 -> 15:53055 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 34.3 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9864 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2275786 | col_h10_r2__t1 | postcts_gate_TT | 4.3 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-2582333 | col_h9_r0_p2__t1 | 5_2_route | 9.5 | drt_violations best 141625 last 141625 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-22377 | hd_lep0N | 4_2_tapbal_grt | 5.6 | last meaningful line 1.0 h ago (48/50 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1-2739404 | kv3_hg_v1 | 3_5_place_dp | 1.5 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v3-114444 | kv3_hgi_v3 | 3_3_place_gp | 0.7 | overflow best 0.0984 last 0.0984 rows 50 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-kv3_hub_Eo-2185518 | kv3_hub_Eo | 3_3_place_gp | 1.7 | overflow best 0.0991 last 0.0991 rows 46 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | dpkit-serdes__t4-293755 | serdes__t4 | 5_1_grt | 2.8 | repair_Remaining best 71298 last 71298 rows 351 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | dpkit-slice_station__t36-3913104 | slice_station__t36 | 6_report | 5.8 | last meaningful line 0.1 h ago (505/505 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t37-173045 | slice_station__t37 | 5_1_grt | 2.8 | last meaningful line 1.1 h ago (213/618 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v3-1328903 | slw_fw_v3 | 5_2_route | 10.2 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_014354_2681516-i3-1261179 | eco_20261121_014354_2681516-i3 | 5_2_route | 2.2 | drt_violations best 360 last 360 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1t-894339 | eco_20261121_154936_3396612-i1t | 5_1_grt | 5.1 | repair_Viol best 2419 last 2419 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_184648_4039100-i1t-1413255 | eco_20261121_184648_4039100-i1t | 5_2_route | 2.2 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_203102_3392434-i1t-646001 | eco_20261121_203102_3392434-i1t | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (209/211 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl870de686-3870117 | cbf_q00 | pregrt_ff_hold | 3.0 | repair_TNS best 3.60575e+06 last 3.60575e+06 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q01__clab6e67f2-19353 | cbn_q01 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (55/55 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-2629912 | col_h9_r0_p2__t1 | 5_2_route | 10.3 | drt_violations best 135164 last 135164 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_kv512_C__t1-359428 | dsdv_slice_kv512_C__t1 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (400/400 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v5-244656 | kv3_hgi_v5 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 2_4_floorplan_pdn | 4.4 | last meaningful line 0.1 h ago (121/121 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | 4_1_cts | 1.4 | last meaningful line 1.2 h ago (7042/7042 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v1-457811 | kv3_pv_v1 | postplace_setup | 0.1 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4n-4044420 | kv3_pv_v4n | 3_5_place_dp | 6.3 | last meaningful line 0.8 h ago (58/58 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v5n-4101656 | kv3_pv_v5n | 3_5_place_dp | 6.2 | last meaningful line 0.1 h ago (58/58 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-native59-22224 | native59 | 2_1_floorplan | 0.4 | repair_Viol best 18803 last 18803 rows 764 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-native59-3868183 | native59 | 4_1_cts | 3.0 | last meaningful line 0.1 h ago (5293/5293 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t14-3447555 | serdes__t14 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.8593 last 0.8687 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-serdes__t16-1729365 | serdes__t16 | 3_4_place_resized | 1.6 | repair_Remaining best 269438 last 269438 rows 66 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2762287 | sle_fw_v1 | 3_4_place_resized | 1.1 | last meaningful line 0.1 h ago (404/404 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2761739 | sle_fw_v1 | 3_3_place_gp | 1.1 | overflow best 0.2026 last 0.2026 rows 36 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-18148 | sle_fw_v2 | 3_3_place_gp | 0.4 | overflow best 0.3911 last 0.3978 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve230954c-2735775 | sle_hc1 | 3_3_place_gp | 1.1 | overflow best 0.2986 last 0.3766 rows 213 | YOUNG: stage 0.8 h < 1 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2374083 | sle_hc1 | 5_1_grt | 10.5 | last meaningful line 0.7 h ago (212/983 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2746212 | sle_hc1 | 3_3_place_gp | 1.1 | overflow best 0.2975 last 0.3808 rows 201 | YOUNG: stage 0.8 h < 1 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-248840 | sle_st_a_v1 | 3_3_place_gp | 0.3 | overflow best 0.2579 last 0.2579 rows 36 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-427216 | sle_st_a_v1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (9494/9495 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-254386 | sle_st_a_v2 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (5921/5921 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-425101 | sle_st_a_v2 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-425190 | sle_su_l1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3310/3310 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t36-3125329 | slice_station__t36 | postcts_gate_TT | 6.8 | last meaningful line 0.0 h ago (1515/1515 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t51-342871 | slice_station__t51 | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (3478/3478 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2408517 | slw_fe_v1 | postcts_gate_TT | 10.4 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | 5_1_grt | 6.0 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-2789993 | slw_fe_v2 | 3_3_place_gp | 1.0 | overflow best 0.0991 last 0.0991 rows 42 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3032983 | slw_fw_v1 | 3_3_place_gp | 1.0 | overflow best 0.1615 last 0.1615 rows 37 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2449519 | slw_hc3 | 5_2_route | 10.4 | drt_violations best 70989 last 70989 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2817277 | slw_sc_v1 | 3_5_place_dp | 1.0 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v2-2660942 | slw_sc_v2 | 5_1_grt | 4.2 | last meaningful line 0.3 h ago (196/205 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2420111 | slw_st_b_v2 | postcts_gate_FF | 10.4 | last meaningful line 0.0 h ago (482/482 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_c__cl19bb38ef-2385009 | slw_su_c | pregrt_ff_hold | 7.3 | repair_Violations best 261 last 261 rows 15 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_c__cl19bb38ef-3446986 | slw_su_c | 3_3_place_gp | 0.8 | overflow best 0.1966 last 0.1966 rows 42 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | otc-180679-7619 | 180679 | gen_lint_yosys | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | otc-547410-14100 | 547410 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | prd-count-p1_bc-1786242 | count-p1_bc | prd_count_p1_bc | 0.1 | last meaningful line 0.0 h ago (578/578 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i3-297348 | eco_20261120_134605_3273412-i3 | 5_2_route | 2.6 | drt_violations best 17645 last 17645 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_070700_2142563-i1-4024972 | eco_20261121_070700_2142563-i1 | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (240/310 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_102155_957464-i1t-245136 | eco_20261121_102155_957464-i1t | 5_2_route | 2.6 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_105744_956410-i1t-1036390 | eco_20261121_105744_956410-i1t | 5_2_route | 2.0 | last meaningful line 0.3 h ago (271/272 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_123328_2268168-i1t-4175816 | eco_20261121_123328_2268168-i1t | 5_1_grt | 0.4 | last meaningful line 0.3 h ago (140/140 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_124930_2356681-i1t-415105 | eco_20261121_124930_2356681-i1t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-cbf-q11-grt-3343587 | cbf-q11-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-slw-sc-v2-grt-3216314 | slw-sc-v2-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbf_q00_s2-2812888 | cbf_q00_s2 | 2_1_floorplan | 0.3 | repair_Viol best 6148 last 6148 rows 1065 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-cbn_q00__cl622f65d2-3281049 | cbn_q00 | 2_1_floorplan | 0.1 | repair_Viol best 6261 last 6261 rows 145 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-2115469 | cbn_q01 | 3_3_place_gp | 0.6 | overflow best 0.2296 last 0.2296 rows 33 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-cbn_q11__cl5cc92dfe-2809953 | cbn_q11 | 3_3_place_gp | 0.3 | overflow best 0.5024 last 0.5024 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-cbx_q10__cl89936551-2741700 | cbx_q10 | 3_3_place_gp | 0.4 | overflow best 0.5601 last 0.5741 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-cbx_q10__cl89936551_h-2224155 | cbx_q10 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (51/51 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-cbx_q10__cl94a12200_h-2223621 | cbx_q10 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (73/73 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hg_v1p2-3294731 | kv3_hg_v1p2 | 3_5_place_dp | 1.6 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-616014 | sle_ctl | 3_3_place_gp | 1.1 | overflow best 0.5085 last 0.5085 rows 17 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-149983 | sle_fe_v1 | 3_5_place_dp | 1.3 | last meaningful line 0.0 h ago (110/110 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2969215 | sle_hc0 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (5041/5041 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-1459492 | sle_hc1 | 5_2_route | 10.4 | last meaningful line 0.1 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_a_v2__pv4242de79-2391789 | sle_st_a_v2 | pregrt_ff_hold | 0.5 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v1__pv0e7b1dcc-1217547 | sle_st_b_v1 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (79/79 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-2160304 | sle_st_b_v1 | 3_3_place_gp | 0.6 | overflow best 0.4187 last 0.4187 rows 32 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cle683a076-3970050 | slw_hc1 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | pregrt_ff_hold | 0.6 | repair_Violations best 1197 last 1197 rows 34 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | otc-3192599-24476 | 3192599 | gold.ys | 0.1 | last meaningful line 0.1 h ago (12175/12175 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_100942_929932-i1-3347652 | eco_20261121_100942_929932-i1 | 5_2_route | 1.6 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_173326_4009105-i1t-1250567 | eco_20261121_173326_4009105-i1t | 5_2_route | 3.4 | drt_violations best 13019 last 13019 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_184012_3245689-i1t-2500922 | eco_20261121_184012_3245689-i1t | 5_2_route | 2.1 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_193535_3253336-i1t-4078609 | eco_20261121_193535_3253336-i1t | 5_2_route | 1.4 | last meaningful line 0.1 h ago (131/131 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_203749_4020394-i1-2795396 | eco_20261121_203749_4020394-i1 | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-slw-st-a-v1--clfc5867a6--pvf82a6c28-grt-1964126 | slw-st-a-v1--clfc5867a6--pvf82a6c28-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-slw-st-a-v2--cl9f076a5c-grt-1832352 | slw-st-a-v2--cl9f076a5c-grt | 3_5_place_dp | 0.2 | last meaningful line 0.2 h ago (127/127 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q00__cld7bf7197-1884788 | cbn_q00 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 316 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1890854 | cbn_q01 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 338 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-cbn_q11__cl49ae4555-1289900 | cbn_q11 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1593385 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.3 | overflow best 0.3008 last 0.3012 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 9520.14 last 9520.14 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | pregrt_ff_hold | 0.7 | repair_TNS best 52717.4 last 52717.4 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-coll_core-783129 | coll_core | 3_3_place_gp | 0.8 | overflow best 0.1438 last 0.1438 rows 42 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-coll_ftc-745291 | coll_ftc | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-hd_host_e-3833588 | hd_host_e | 5_2_route | 5.6 | drt_violations best 27 last 27 rows 56 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-2007910 | kv3_hg_v1p2 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (186/186 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hroot-4110897 | kv3_hroot | 5_2_route | 5.4 | last meaningful line 0.2 h ago (254/255 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor-3733934 | kv3_io_cor | 5_2_route | 5.7 | drt_violations best 8731 last 8731 rows 2 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-3818815 | kv3_io_cor_v1 | 6_report | 5.6 | last meaningful line 0.1 h ago (1068/1068 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-3274788 | serdes__t1 | 5_2_route | 9.6 | last meaningful line 0.4 h ago (294/295 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-1802792 | sle_ctl | 2_1_floorplan | 0.2 | repair_Viol best 2867 last 2867 rows 1115 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa-1023417 | sle_hc0 | 5_1_grt | 7.6 | last meaningful line 0.1 h ago (1002/1008 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-1295515 | sle_hc1 | 3_3_place_gp | 0.5 | overflow best 0.7013 last 0.7013 rows 27 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-1013642 | sle_hc2 | 5_1_grt | 7.6 | last meaningful line 1.0 h ago (210/944 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_sc_v1__cl115da35f-1093172 | sle_sc_v1 | 3_3_place_gp | 0.7 | overflow best 0.3454 last 0.3458 rows 11 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-1899674 | slw_fe_v1 | 5_1_grt | 7.0 | repair_Remaining best 81699 last 81699 rows 308 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-2906124 | slw_hc1 | 5_1_grt | 9.9 | last meaningful line 0.5 h ago (218/919 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1012001 | slw_hc3 | 5_1_grt | 7.6 | last meaningful line 0.2 h ago (1015/1032 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-1012945 | slw_hc3 | 5_1_grt | 7.6 | last meaningful line 0.5 h ago (209/950 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-1897237 | slw_st_a_v2 | 3_1_place_gp_skip_io | 0.1 | overflow best 0.9803 last 0.9803 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-1964882 | slw_su_l0 | 3_3_place_gp | 0.1 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-1547845-17008 | 1547845 | orfs_flow | 3.7 | repair_Viol best 93 last 93 rows 33 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc8 | otc-1576193-17345 | 1576193 | gold.ys | 0.4 | last meaningful line 0.2 h ago (10689/10689 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 56.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-559540-13695 | 559540 | route | 4.8 | last meaningful line 0.2 h ago (472/472 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3350653 | col_h9_r1__t1 | 5_2_route | 6.7 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-1513640 | sle_hc0 | postcts_gate_FF | 8.2 | last meaningful line 0.0 h ago (775/775 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-882856 | slw_hc3 | 5_2_route | 8.6 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | otc-3085280-30126 | 3085280 | - | 12.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 12.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 12.3 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261121_070035_1645318-i1-2327283 | eco_20261121_070035_1645318-i1 | 5_2_route | 3.1 | drt_violations best 20 last 20 rows 6 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_143815_74711-i2-3554105 | eco_20261121_143815_74711-i2 | 5_2_route | 1.4 | last meaningful line 0.1 h ago (265/266 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_154823_2000128-i2-4171153 | eco_20261121_154823_2000128-i2 | 5_1_grt | 0.6 | last meaningful line 0.2 h ago (231/1299 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 2.0 | drt_violations best 194272 last 194272 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_195859_2616880-i1t-3870494 | eco_20261121_195859_2616880-i1t | 5_2_route | 1.0 | drt_violations best 61656 last 61656 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | prd-eco_20261121_201548_1094504-i1t-4087489 | eco_20261121_201548_1094504-i1t | 5_2_route | 0.7 | last meaningful line 0.0 h ago (261/262 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-4146127 | col_h10_r2__t1 | 5_2_route | 9.4 | drt_violations best 85869 last 85869 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | 5_2_route | 17.3 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | prd-eco1-i1-2520913 | eco1-i1 | 5_2_route | 10.2 | drt_violations best 112 last 112 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i2t-1252392 | eco_20261120_192428_3309571-i2t | 5_2_route | 0.7 | last meaningful line 0.1 h ago (256/256 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | prd-eco_20261121_075836_1991905-i1t-1821063 | eco_20261121_075836_1991905-i1t | 5_2_route | 5.0 | drt_violations best 190712 last 190712 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i1t-2148021 | eco_20261121_082001_3216437-i1t | 5_2_route | 4.6 | drt_violations best 185697 last 185697 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-2692442 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-1242372 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5406 last 5406 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | prd-eco_20261121_072804_212710-i1-2335895 | eco_20261121_072804_212710-i1 | 5_1_grt | 0.6 | last meaningful line 0.3 h ago (229/1287 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | prd-eco_20261121_111944_190475-i1-3971139 | eco_20261121_111944_190475-i1 | 5_2_route | 1.6 | last meaningful line 0.0 h ago (268/269 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | prd-eco_20261121_115902_173230-i1t-1237159 | eco_20261121_115902_173230-i1t | 5_2_route | 1.0 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | so_3541505_ff_55010 | so_3541505_ff_55010 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel2 | so_3541505_tt_55010 | so_3541505_tt_55010 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc10 | otc-666311-18648 | 666311 | asbuilt.yosys | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | otc-924821-31887 | 924821 | asbuilt.yosys | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 29.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-eco1-i1-100513 | eco1-i1 | 5_2_route | 9.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-1617813 | eco1-i1 | 5_1_grt | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-1714380 | eco1-i1 | 5_1_grt | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-4178763 | eco1-i1 | 5_2_route | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-92562 | eco1-i1 | 5_2_route | 9.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-hd_lep0N-1588394 | hd_lep0N | pregrt_ff_hold | 7.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slice_station__t36-3668002 | slice_station__t36 | 5_1_grt | 3.3 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_2_route | 17.6 | drt_violations best 10389 last 10389 rows 16 | before-window best 14325, window best 10389 | PROGRESS: drt_violations improved 27.5 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 34.2 | last meaningful line 0.2 h ago (1495/1495 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-hd_mesh-2472048 | hd_mesh | pregrt_ff_hold | 10.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3868961 | slw_sc_v1 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_2_route | 19.8 | drt_violations best 9551 last 9551 rows 16 | before-window best 13013, window best 9551 | PROGRESS: drt_violations improved 26.6 % in window |  |
| epyc2 | prd-eco_20261120_170022_4017640-i2t-2328774 | eco_20261120_170022_4017640-i2t | 5_2_route | 7.4 | drt_violations best 99 last 99 rows 11 | before-window best 72780, window best 99 | PROGRESS: drt_violations improved 99.9 % in window |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 10.1 | drt_violations best 3 last 9 rows 43 | before-window best 8867, window best 3 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-993515 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve230954c-1731757 | sle_hc1 | pregrt_ff_hold | 6.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l0__cl1a1c1f8f-1472945 | slw_su_l0 | 5_2_route | 10.4 | drt_violations best 4 last 4 rows 47 | before-window best 47342, window best 4 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_2_route | 20.7 | drt_violations best 13126 last 54684 rows 18 | before-window best 14002, window best 13126 | PROGRESS: drt_violations improved 6.3 % in window |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | 5_2_route | 16.4 | drt_violations best 15 last 15 rows 50 | before-window best 564, window best 15 | PROGRESS: drt_violations improved 97.3 % in window |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | 5_2_route | 16.4 | drt_violations best 27 last 27 rows 50 | before-window best 264, window best 27 | PROGRESS: drt_violations improved 89.8 % in window |  |
| epyc8 | dpkit-dsdv_slice_lepe_mu_LP__t2-3534677 | dsdv_slice_lepe_mu_LP__t2 | tt_setup_repair | 1.7 | repair_Violations best 0 last 0 rows 15 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-glue-504992 | glue | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3985339 | sle_hc2 | pregrt_ff_hold | 5.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-850569 | slw_fe_v1 | 5_1_grt | 7.7 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2616668 | sle_hc1 | pregrt_ff_hold | 7.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | 5_2_route | 17.1 | drt_violations best 203629 last 203629 rows 1 | before-window best 203629, window best 203629 | PROGRESS: drt_violations: active iteration at 100938 < best completed total 203629 (in-ite |  |
| intel1 | dpkit-sle_ctl__cl67434795-622153 | sle_ctl | pregrt_ff_hold | 11.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-2204474 | slw_st_b_v1 | 5_1_grt | 10.4 | repair_TNS best 0 last 0 rows 20 | PROGRESS: repair_TNS reached 0 |  |
