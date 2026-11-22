# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 20:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'CANCEL-NOW': 1, 'GRT-LABEL': 14, 'YOUNG': 78, 'NO-DATA': 8, 'KEEP': 1, 'EXCLUDED': 1, 'PROGRESS': 14}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 49.6 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 49 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-2612029 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 3_4_place_resized | 0.5 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 34.7 | grt rounds 4 overflow 5:95946 -> 10:62005 -> 15:49088 -> 20:49999 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 34.6 | grt rounds 5 overflow 5:56489 -> 10:43484 -> 15:40478 -> 20:43412 -> 25:50457 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 49.1 | grt rounds 5 overflow 5:9510 -> 10:5086 -> 15:3245 -> 20:2874 -> 25:3124 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 38.3 | grt rounds 4 overflow 5:54036 -> 10:38366 -> 15:34625 -> 20:37819 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 23.4 | grt rounds 4 overflow 5:18628 -> 10:12430 -> 15:11108 -> 20:10290 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 36.3 | grt rounds 4 overflow 5:32844 -> 10:12056 -> 15:8208 -> 20:7612 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 47.0 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11655 -> 20:10171 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 47.3 | grt rounds 5 overflow 5:32681 -> 10:30734 -> 15:25360 -> 20:22699 -> 25:31808 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 29.8 | grt rounds 6 overflow 5:19221 -> 10:14920 -> 15:12366 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 24.8 | grt rounds 4 overflow 5:35977 -> 10:30023 -> 15:24172 -> 20:20900 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 46.1 | grt rounds 4 overflow 5:67513 -> 10:54044 -> 15:50242 -> 20:55216 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 41.1 | grt rounds 3 overflow 5:59246 -> 10:46138 -> 15:41146 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 41.1 | grt rounds 3 overflow 5:60515 -> 10:47029 -> 15:41606 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 41.3 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-cbn-q11--cl49ae4555-grt-915478 | cbn-q11--cl49ae4555-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-114812 | coll_core | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p4-4003232 | kv3_hg_v1p4 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t4-293755 | serdes__t4 | 5_2_route | 9.8 | drt_violations best 19849 last 19849 rows 2 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-9110 | sle_hc1 | 3_3_place_gp | 0.8 | overflow best 0.1928 last 0.1928 rows 160 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-711880 | sle_st_b_v1 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (369/369 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_su_c-988292 | sle_su_c | 2_1_floorplan | 0.0 | last meaningful line 0.0 h ago (86/86 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-98349 | slw_fe_v2 | 3_4_place_resized | 0.7 | last meaningful line 0.0 h ago (372/372 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-145776 | slw_hc1 | 3_3_place_gp | 0.7 | overflow best 0.2998 last 0.5902 rows 169 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-708114 | slw_st_b_v2 | 3_3_place_gp | 0.2 | overflow best 0.786 last 0.786 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1-396779 | eco_20261121_154936_3396612-i1 | 5_1_grt | 0.5 | last meaningful line 0.3 h ago (254/966 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_203102_3392434-i1t-646001 | eco_20261121_203102_3392434-i1t | 5_2_route | 7.4 | drt_violations best 12 last 12 rows 43 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl870de686-411021 | cbf_q00 | 3_3_place_gp | 0.7 | overflow best 0.298 last 0.298 rows 32 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-cbn_q00__cl622f65d2-1109962 | cbn_q00 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.8426 last 0.8484 rows 21 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-cbn_q00__cldbcda913-1048513 | cbn_q00 | 3_3_place_gp | 0.4 | overflow best 0.342 last 0.342 rows 28 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-kv3_hg-481577 | kv3_hg | 3_3_place_gp | 0.7 | overflow best 0.6425 last 0.6425 rows 24 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-kv3_hg_v1-4188706 | kv3_hg_v1 | 3_3_place_gp | 0.8 | overflow best 0.4455 last 0.4455 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-kv3_hg_v1p2-253468 | kv3_hg_v1p2 | 3_3_place_gp | 0.7 | overflow best 0.6928 last 0.6928 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-kv3_hg_v1p5-328056 | kv3_hg_v1p5 | 3_3_place_gp | 0.7 | overflow best 0.7625 last 0.7635 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 3_4_place_resized | 11.4 | last meaningful line 1.5 h ago (519/519 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | 5_1_grt | 8.4 | repair_Remaining best 271770 last 271770 rows 180 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-kv3_pv-767971 | kv3_pv | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.0 h ago (79/79 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t12-735850 | serdes__t12 | 3_3_place_gp | 0.5 | overflow best 0.9561 last 0.9561 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-142291 | sle_fw_v1 | 3_4_place_resized | 0.8 | last meaningful line 0.1 h ago (405/405 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-425190 | sle_su_l1 | 5_2_route | 7.1 | drt_violations best 12740 last 12740 rows 2 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-230949 | slw_fe_v1 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | 5_2_route | 13.0 | last meaningful line 0.3 h ago (280/281 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-1019838 | slw_sc_v1 | 5_2_route | 6.7 | last meaningful line 0.0 h ago (258/258 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-410259 | slw_stm_v2 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q00__cld7bf7197-3404310 | cbn_q00 | 5_1_grt | 5.8 | last meaningful line 0.3 h ago (25/25 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | 5_1_grt | 7.7 | repair_TNS best 43.389 last 43.389 rows 3 | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_1_grt | 7.7 | last meaningful line 0.2 h ago (40/40 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-3144441 | kv3_hg_v1p2 | tt_setup_repair | 1.5 | repair_Violations best 1610 last 1653 rows 48 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-serdes__t14-3301476 | serdes__t14 | 5_1_grt | 5.9 | repair_Viol best 169 last 169 rows 2 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-3022331 | sle_ctl | 4_1_cts | 1.7 | last meaningful line 0.3 h ago (8492/8492 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3985339 | sle_hc2 | 6_report | 12.5 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-850569 | slw_fe_v1 | generate_abstract | 14.7 | last meaningful line 0.0 h ago (720/720 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 7.1 | drt_violations best 49816 last 49816 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-187481 | slw_st_a_v2 | 5_1_grt | 0.6 | last meaningful line 0.0 h ago (203/205 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-1964882 | slw_su_l0 | generate_abstract | 7.1 | last meaningful line 0.0 h ago (468/468 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 6.9 | drt_violations best 80670 last 80670 rows 2 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261122_024317_3271969-i1t-3547037 | eco_20261122_024317_3271969-i1t | 5_2_route | 1.2 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | so_196861_ff_95523 | so_196861_ff_95523 | signoff | 0.6 |  | NO-DATA: empty log |  |
| epyc9 | ap-ageom-kw-slw-st-a-v1--clfc5867a6--pvf82a6c28-grt-1928132 | slw-st-a-v1--clfc5867a6--pvf82a6c28-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-cbf_q01-1450063 | cbf_q01 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.3162 last 0.3162 rows 35 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-cbn_q11__cl5cc92dfe-1531991 | cbn_q11 | 3_3_place_gp | 0.4 | overflow best 0.2251 last 0.2254 rows 34 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1695684 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.3 | overflow best 0.3665 last 0.3728 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1701601 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.3 | overflow best 0.3652 last 0.3663 rows 4 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-glue-1005623 | glue | 3_5_place_dp | 0.7 | last meaningful line 0.1 h ago (112/112 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-1585232 | hd_ctl | pregrt_ff_hold | 0.4 | repair_TNS best 429435 last 429435 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v6-1440068 | kv3_pv_v6 | 2_1_floorplan | 0.4 | last meaningful line 0.0 h ago (1180/1180 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v8-1614044 | kv3_pv_v8 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (107/107 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-1002097 | sle_fw_v2 | 3_5_place_dp | 0.7 | last meaningful line 0.1 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-1233696 | sle_hc0 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (111/111 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-990147 | sle_hc1 | 3_3_place_gp | 0.7 | overflow best 0.2976 last 0.5181 rows 222 | YOUNG: stage 0.5 h < 1 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-1810235 | sle_st_b_v1 | 2_2_floorplan_macro | 0.2 | last meaningful line -0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1823667 | sle_st_b_v2 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-997171 | slw_fe_v2 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1196347 | slw_hc0 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-1155498 | slw_hc0 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (113/113 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-1136852-24964 | 1136852 | parts_equiv | 0.6 | last meaningful line 0.5 h ago (792572/792572 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | otc-1732719-5782 | 1732719 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc9 | otc-1758840-26581 | 1758840 | orfs_synth | 0.2 | last meaningful line 0.2 h ago (421/421 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-1843583-16057 | 1843583 | lec | 0.2 | LEC last write 0.1 h ago | YOUNG: evidence 0.2 h < 6 h |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 19.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 19.3 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261121_070035_1645318-i2-745368 | eco_20261121_070035_1645318-i2 | 5_2_route | 0.9 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | prd-eco_r3_residual-i1-799917 | eco_r3_residual-i1 | 5_2_route | 0.8 | last meaningful line 0.1 h ago (128/128 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | so_2004557_ff_11552 | so_2004557_ff_11552 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | so_2004557_tt_11552 | so_2004557_tt_11552 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | dpkit-kv3_io_cor_v1-3312033 | kv3_io_cor_v1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_io_ft-2751771 | kv3_io_ft | 5_2_route | 0.6 | last meaningful line 0.0 h ago (203/203 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3125768 | slw_hc3 | 3_3_place_gp | 0.3 | overflow best 0.6512 last 0.6512 rows 33 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-3224056 | slw_st_b_v1 | reg_fanout | 0.2 |  | NO-DATA: empty log |  |
| intel1 | ot-canary-3420121 | ot-canary | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261120_192428_3309571-i3t-3010955 | eco_20261120_192428_3309571-i3t | 5_2_route | 0.4 | last meaningful line 0.0 h ago (247/247 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i1-1189865 | eco_20261121_082001_3216437-i1 | 5_2_route | 2.5 | drt_violations best 43516 last 43516 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1t-203702 | eco_20261121_161716_4143584-i1t | 5_2_route | 3.7 | drt_violations best 4917 last 4917 rows 6 | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_1_grt | 2.1 | repair_Remaining best 299010 last 299010 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4007898 | col_h9_r1__t1 | 5_1_grt | 4.7 | last meaningful line 2.8 h ago (40/40 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3132815 | coll_ftm | 5_2_route | 1.7 | last meaningful line 0.1 h ago (242/243 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-2621920 | hd_turn_a | 5_2_route | 0.5 | drt_violations best 4894 last 4894 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-sle_fw_v1__clf58b4dfb-52899 | sle_fw_v1 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-82779 | sle_hc1 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-170626 | slw_fw_v1 | 3_5_place_dp | 1.4 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | otc-2920128-4921 | 2920128 | 3_3_place_gp | 0.3 | overflow best 0.1706 last 0.1706 rows 39 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 36.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel2 | otc-3265713-26458 | 3265713 | - | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | prd-eco_20261122_021210_171272-i1t-3026978 | eco_20261122_021210_171272-i1t | 5_2_route | 1.8 | drt_violations best 0 last 0 rows 4 | PROGRESS: drt_violations reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 41.2 | last meaningful line 1.5 h ago (1548/1548 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-cbf_q00__cl1b5a6458-557330 | cbf_q00 | pregrt_ff_hold | 0.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-cbf_q01_s2-557381 | cbf_q01_s2 | pregrt_ff_hold | 0.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 17.1 | drt_violations best 1 last 2 rows 54 | before-window best 3, window best 1 | PROGRESS: drt_violations improved 66.7 % in window |  |
| epyc8 | otc-431765-18007 | 431765 | tt_setup_repair_grt | 0.4 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | otc-451257-8041 | 451257 | tt_setup_repair_grt | 0.4 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | otc-709044-23442 | 709044 | tt_setup_repair_grt | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | ap-ageom-kw-col-h10-r1--t1--cld01bb4ae-grt-2003621 | col-h10-r1--t1--cld01bb4ae-grt | 3_5_place_dp | 0.1 | repair_Violations best 0 last 0 rows 42 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-hd_mesh-3170867 | hd_mesh | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | otc-1453349-16601 | 1453349 | tt_setup_repair_grt | 0.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | otc-1458714-4592 | 1458714 | tt_setup_repair_grt | 0.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 9.0 | drt_violations best 571 last 836 rows 28 | before-window best 13075, window best 571 | PROGRESS: drt_violations improved 95.6 % in window |  |
| intel1 | prd-eco_20261121_075836_1991905-i1t-1821063 | eco_20261121_075836_1991905-i1t | 5_2_route | 12.0 | drt_violations best 91 last 91 rows 14 | before-window best 23424, window best 91 | PROGRESS: drt_violations improved 99.6 % in window |  |
