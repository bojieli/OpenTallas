# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 19:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'CANCEL-NOW': 3, 'GRT-LABEL': 14, 'YOUNG': 83, 'NO-DATA': 9, 'KEEP': 1, 'EXCLUDED': 2, 'PROGRESS': 15}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 49.3 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 49 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-1756223 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 5_2_route | 0.4 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-2612029 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 3_3_place_gp | 0.2 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-2612029-lec | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | lec | 0.0 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 34.4 | grt rounds 4 overflow 5:95946 -> 10:62005 -> 15:49088 -> 20:49999 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 34.4 | grt rounds 5 overflow 5:56489 -> 10:43484 -> 15:40478 -> 20:43412 -> 25:50457 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 48.8 | grt rounds 5 overflow 5:9510 -> 10:5086 -> 15:3245 -> 20:2874 -> 25:3124 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 38.1 | grt rounds 4 overflow 5:54036 -> 10:38366 -> 15:34625 -> 20:37819 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 23.2 | grt rounds 4 overflow 5:18628 -> 10:12430 -> 15:11108 -> 20:10290 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 36.0 | grt rounds 4 overflow 5:32844 -> 10:12056 -> 15:8208 -> 20:7612 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 46.8 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11655 -> 20:10171 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 47.0 | grt rounds 5 overflow 5:32681 -> 10:30734 -> 15:25360 -> 20:22699 -> 25:31808 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 29.3 | grt rounds 6 overflow 5:19221 -> 10:14920 -> 15:17882 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 24.3 | grt rounds 4 overflow 5:36357 -> 10:30023 -> 15:24172 -> 20:20900 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 45.6 | grt rounds 4 overflow 5:67513 -> 10:54044 -> 15:50242 -> 20:55216 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 40.9 | grt rounds 3 overflow 5:59246 -> 10:46138 -> 15:41146 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 40.9 | grt rounds 3 overflow 5:60515 -> 10:47029 -> 15:41606 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 41.1 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-sle-st-a-v2--pv30dda31f--pv88773f93-grt-633321 | sle-st-a-v2--pv30dda31f--pv88773f93-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-cbn_q11__cl49ae4555-3982749 | cbn_q11 | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (286/286 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-114812 | coll_core | 3_3_place_gp | 0.5 | overflow best 0.2913 last 0.2913 rows 35 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-kv3_hg_v1p4-4003232 | kv3_hg_v1p4 | 3_3_place_gp | 0.6 | overflow best 0.7498 last 0.754 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-serdes__t4-293755 | serdes__t4 | 5_2_route | 9.5 | drt_violations best 138627 last 138627 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc10 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-9110 | sle_hc1 | 3_3_place_gp | 0.5 | overflow best 0.2982 last 0.5625 rows 71 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v2__cle312294d-98349 | slw_fe_v2 | 3_3_place_gp | 0.5 | overflow best 0.473 last 0.4736 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-145776 | slw_hc1 | 3_3_place_gp | 0.4 | overflow best 0.2998 last 0.2998 rows 49 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | prd-eco_20261121_203102_3392434-i1t-646001 | eco_20261121_203102_3392434-i1t | 5_2_route | 7.2 | drt_violations best 25 last 25 rows 12 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_021210_171272-i1t-3026978 | eco_20261122_021210_171272-i1t | 5_2_route | 1.5 | drt_violations best 453 last 453 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-cbx-q10--cl89936551-grt-1120068 | cbx-q10--cl89936551-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl870de686-411021 | cbf_q00 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.4782 last 0.4782 rows 32 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-cbn_q00__cl622f65d2-1109962 | cbn_q00 | 2_1_floorplan | 0.1 | repair_Viol best 6261 last 6261 rows 315 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-cbn_q00__cldbcda913-1048513 | cbn_q00 | 2_1_floorplan | 0.1 | repair_Viol best 6754 last 6754 rows 495 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-kv3_hg-481577 | kv3_hg | 3_1_place_gp_skip_io | 0.4 | overflow best 0.7832 last 0.7832 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-kv3_hg_v1-4188706 | kv3_hg_v1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.3104 last 0.3104 rows 35 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-kv3_hg_v1p2-253468 | kv3_hg_v1p2 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.8006 last 0.8006 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-kv3_hg_v1p5-328056 | kv3_hg_v1p5 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.8674 last 0.8674 rows 6 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 3_4_place_resized | 11.2 | last meaningful line 1.2 h ago (519/519 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | 5_1_grt | 8.1 | last meaningful line 0.1 h ago (185/198 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv-767971 | kv3_pv | 2_1_floorplan | 0.3 | last meaningful line 0.1 h ago (385/385 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t12-735850 | serdes__t12 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-142291 | sle_fw_v1 | 3_3_place_gp | 0.5 | overflow best 0.1975 last 0.1975 rows 41 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-797330 | sle_st_a_v1 | 3_5_place_dp | 0.3 | last meaningful line 0.0 h ago (116/116 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-425190 | sle_su_l1 | 5_2_route | 6.9 | drt_violations best 80565 last 80565 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-230949 | slw_fe_v1 | 3_3_place_gp | 0.5 | overflow best 0.0986 last 0.0986 rows 42 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | 5_2_route | 12.8 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-1019838 | slw_sc_v1 | 5_2_route | 6.4 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-410259 | slw_stm_v2 | 3_3_place_gp | 0.4 | overflow best 0.1978 last 0.1978 rows 36 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | prd-eco_20261121_185640_2629364-i1t-3849783 | eco_20261121_185640_2629364-i1t | 5_1_grt | 0.8 | last meaningful line 0.5 h ago (210/218 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q00__cld7bf7197-3404310 | cbn_q00 | 5_1_grt | 5.5 | last meaningful line 0.2 h ago (25/25 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | 5_1_grt | 7.4 | repair_TNS best 1686.47 last 1686.47 rows 7 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_1_grt | 7.4 | last meaningful line 0.3 h ago (202/211 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-3144441 | kv3_hg_v1p2 | 4_1_cts | 1.3 | last meaningful line 0.1 h ago (4340/4340 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-3022331 | sle_ctl | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (8491/8491 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3985339 | sle_hc2 | 5_2_route | 12.2 | drt_violations best 5608 last 5608 rows 3 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-850569 | slw_fe_v1 | 6_report | 14.5 | last meaningful line 0.0 h ago (762/762 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 6.9 | drt_violations best 49816 last 49816 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-187481 | slw_st_a_v2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (7823/7823 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-1964882 | slw_su_l0 | 5_2_route | 6.8 | drt_violations best 106 last 106 rows 5 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 6.7 | drt_violations best 168894 last 168894 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | otc-406689-11488 | 406689 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | prd-eco_20261122_024317_3271969-i1t-3547037 | eco_20261122_024317_3271969-i1t | 5_1_grt | 0.9 | last meaningful line 0.5 h ago (249/1454 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | so_196861_ff_95523 | so_196861_ff_95523 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc8 | so_196861_tt_95523 | so_196861_tt_95523 | signoff | 0.4 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-cbf_q01-1450063 | cbf_q01 | 2_1_floorplan | 0.2 | repair_Viol best 6148 last 6148 rows 926 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-cbn_q11__cl5cc92dfe-1531991 | cbn_q11 | 2_1_floorplan | 0.1 | repair_Viol best 6148 last 6148 rows 1068 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1695684 | col_h9_r0_p2__t1 | 2_1_floorplan | 0.0 | repair_Viol best 5231 last 5231 rows 212 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1701601 | col_h9_r0_p2__t1 | 2_1_floorplan | 0.0 | repair_Viol best 3023 last 3023 rows 143 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-glue-1005623 | glue | 3_3_place_gp | 0.4 | overflow best 0.0994 last 0.0994 rows 41 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-hd_ctl-1585232 | hd_ctl | 4_1_cts | 0.1 | last meaningful line -0.0 h ago (3174/3174 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v6-1440068 | kv3_pv_v6 | 2_1_floorplan | 0.2 | repair_Viol best 978 last 978 rows 226 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v8-1614044 | kv3_pv_v8 | synth_odb_v | 0.1 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-1002097 | sle_fw_v2 | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-1097329 | sle_hc0 | 3_3_place_gp | 0.4 | overflow best 0.1835 last 0.1835 rows 47 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-1233696 | sle_hc0 | 3_3_place_gp | 0.3 | overflow best 0.2085 last 0.2085 rows 45 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-990147 | sle_hc1 | 3_3_place_gp | 0.4 | overflow best 0.3007 last 0.5711 rows 105 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-997171 | slw_fe_v2 | 3_3_place_gp | 0.4 | overflow best 0.0994 last 0.0994 rows 43 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-1196347 | slw_hc0 | 3_3_place_gp | 0.4 | overflow best 0.2068 last 0.2068 rows 45 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-1155498 | slw_hc0 | 3_3_place_gp | 0.4 | overflow best 0.2071 last 0.2071 rows 45 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-1486999 | slw_st_a_v1 | 3_3_place_gp | 0.1 | overflow best 0.5533 last 0.5592 rows 18 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | otc-1136852-24964 | 1136852 | parts_equiv | 0.4 | last meaningful line 0.3 h ago (792572/792572 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | otc-1453134-30595 | 1453134 | tt_setup_repair_grt | 0.2 | last meaningful line 0.2 h ago (369/369 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-1621145-13723 | 1621145 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-1732719-5782 | 1732719 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 19.4 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 19.0 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261121_070035_1645318-i2-745368 | eco_20261121_070035_1645318-i2 | 5_2_route | 0.6 | last meaningful line 0.0 h ago (265/265 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco_r3_residual-i1-799917 | eco_r3_residual-i1 | 5_1_grt | 0.6 | last meaningful line 0.3 h ago (230/1339 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_io_ft-2751771 | kv3_io_ft | 3_3_place_gp | 0.1 | overflow best 0.1022 last 0.1022 rows 32 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | eco-abs-2832548 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-2842003-32643 | 2842003 | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261121_082001_3216437-i1-1189865 | eco_20261121_082001_3216437-i1 | 5_2_route | 2.0 | last meaningful line 0.1 h ago (281/282 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1t-203702 | eco_20261121_161716_4143584-i1t | 5_2_route | 3.2 | drt_violations best 11347 last 11347 rows 3 | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_1_grt | 1.6 | last meaningful line 1.0 h ago (209/225 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | so_2241325_tt_52557 | so_2241325_tt_52557 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (835/835 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-1820684 | col_h10_r1__t1 | 3_5_place_dp | 0.3 | repair_Violations best 1.36667e+06 last 1.36667e+06 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4007898 | col_h9_r1__t1 | 5_1_grt | 4.5 | last meaningful line 2.5 h ago (40/40 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3132815 | coll_ftm | 5_2_route | 1.5 | last meaningful line 0.1 h ago (234/235 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-1760085 | hd_turn_a | 5_2_route | 0.4 | drt_violations best 347 last 347 rows 2 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-2621920 | hd_turn_a | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (349/380 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_hgi_v3-440043 | kv3_hgi_v3 | 3_4_place_resized | 1.0 | last meaningful line 0.1 h ago (218/218 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v1__clf58b4dfb-52899 | sle_fw_v1 | 3_3_place_gp | 1.2 | overflow best 0.0986 last 0.0986 rows 43 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-544842 | sle_fw_v2 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-82779 | sle_hc1 | 3_3_place_gp | 1.1 | overflow best 0.2014 last 0.2014 rows 256 | YOUNG: stage 0.9 h < 1 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-106360 | slw_fe_v1 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-170626 | slw_fw_v1 | 3_4_place_resized | 1.1 | repair_Remaining best 75350 last 75350 rows 274 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-252358 | slw_st_b_v2 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (122/122 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-slw_stm_v2__cl1ca9c415-555114 | slw_stm_v2 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | otc-2920128-4921 | 2920128 | 3_3_place_gp | 0.1 | overflow best 0.6375 last 0.6375 rows 3 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | otc-2992664-14935 | 2992664 | - | 0.0 |  | NO-DATA: no log found |  |
| intel2 | quizzical_cray | quizzical_cray | asbuilt.yosys | 0.0 | last meaningful line -0.0 h ago (121/121 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 36.6 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | otc-2677126-12415 | 2677126 | - | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | otc-2583533-1 | 2583533 | - | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1-396779 | eco_20261121_154936_3396612-i1 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 41.0 | last meaningful line 1.3 h ago (1548/1548 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-cbf_q00__cl1b5a6458-557330 | cbf_q00 | pregrt_ff_hold | 0.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-cbf_q01_s2-557381 | cbf_q01_s2 | pregrt_ff_hold | 0.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 16.9 | drt_violations best 1 last 2 rows 54 | before-window best 3, window best 1 | PROGRESS: drt_violations improved 66.7 % in window |  |
| epyc8 | dpkit-serdes__t14-3301476 | serdes__t14 | 5_1_grt | 5.6 | repair_TNS best 0 last 0 rows 14 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | otc-431765-18007 | 431765 | tt_setup_repair_grt | 0.1 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | otc-451257-8041 | 451257 | tt_setup_repair_grt | 0.1 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-hd_ctl-282607 | hd_ctl | 5_2_route | 1.2 | drt_violations best 0 last 0 rows 6 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | dpkit-hd_mesh-3170867 | hd_mesh | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | otc-1453349-16601 | 1453349 | tt_setup_repair_grt | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | otc-1458714-4592 | 1458714 | tt_setup_repair_grt | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 8.7 | drt_violations best 571 last 1158 rows 27 | before-window best 194272, window best 571 | PROGRESS: drt_violations improved 99.7 % in window |  |
| intel1 | prd-eco_20261121_075836_1991905-i1t-1821063 | eco_20261121_075836_1991905-i1t | 5_2_route | 11.5 | drt_violations best 91 last 91 rows 14 | before-window best 190712, window best 91 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel2 | dpkit-slice_station__t12-3517303 | slice_station__t12 | 5_2_route | 1.2 | drt_violations best 0 last 0 rows 4 | PROGRESS: drt_violations reached 0 |  |
