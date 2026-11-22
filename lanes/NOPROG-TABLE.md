# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 03:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'CANCEL-NOW': 2, 'GRT-LABEL': 20, 'YOUNG': 92, 'NO-DATA': 7, 'KEEP': 1, 'PROGRESS': 30}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 12.7 | last meaningful line 11.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 11.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-3046893 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 5_2_route | 0.5 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-3053572 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 3_4_place_resized | 0.5 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 42.2 | grt rounds 4 overflow 5:104318 -> 10:62060 -> 15:49497 -> 20:49757 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 56.6 | grt rounds 6 overflow 5:9444 -> 10:5570 -> 15:3582 -> 20:2874 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-3023973 | col_h10_r0_p4__t1 | 5_1_grt | 5.1 | grt rounds 2 overflow 5:62130 -> 10:209 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 36.0 | grt rounds 3 overflow 5:64751 -> 10:65943 -> 15:59403 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 40.9 | grt rounds 3 overflow 5:61400 -> 10:62947 -> 15:55011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 30.3 | grt rounds 4 overflow 5:51174 -> 10:49018 -> 15:39466 -> 20:42804 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 30.3 | grt rounds 3 overflow 5:59202 -> 10:49628 -> 15:39607 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 40.1 | grt rounds 4 overflow 5:82307 -> 10:49854 -> 15:42880 -> 20:44324 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 29.8 | grt rounds 4 overflow 5:105414 -> 10:69762 -> 15:50712 -> 20:57946 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 4.7 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | 5_1_grt | 13.7 | grt rounds 2 overflow 5:39369 -> 10:31446 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | clkgrt-base-1763391 | clkgrt-base | 5_1_grt | 2.5 | grt rounds 2 overflow 5:60327 -> 10:46634 | GRT-LABEL: DESIGN-FAIL: overflow 46634 at round 10 > 1000 |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1220915 | col_h9_r0_p2__t1 | 5_1_grt | 7.1 | grt rounds 2 overflow 5:87414 -> 10:72 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_1_grt | 4.3 | grt rounds 2 overflow 5:63492 -> 10:344 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 30.9 | grt rounds 5 overflow 5:20337 -> 10:12248 -> 15:11083 -> 20:10120 -> 25:22767 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-1503152 | col_h10_r1__t1 | 5_1_grt | 4.3 | grt rounds 10 overflow 25:206 -> 30:94 -> 35:43 -> 40:71 -> 45:33 -> 50:66 | GRT-LABEL: DESIGN-FAIL: overflow rising at round 50: 33 -> 66 |  |
| epyc9 | dpkit-kv3_hroot-3564680 | kv3_hroot | 5_1_grt | 2.5 | grt rounds 2 overflow 5:4295 -> 10:1894 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 44.0 | grt rounds 5 overflow 5:32844 -> 10:12056 -> 15:8164 -> 20:7397 -> 25:22417 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 54.8 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 37.3 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10993 -> 25:8231 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-1434883 | cbf_q00 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5052/5052 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-1532241 | cbf_q00 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9818 last 0.9818 rows 2 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 4.7 | last meaningful line 0.0 h ago (199/201 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-coll_ftc-3642118 | coll_ftc | 5_2_route | 5.0 | drt_violations best 51451 last 51451 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-hd_ctl-2275016 | hd_ctl | 5_1_grt | 2.8 | repair_TNS best 72.953 last 72.953 rows 4 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-hd_host_e-1541416 | hd_host_e | 5_2_route | 3.3 | drt_violations best 28 last 30 rows 51 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-1727564 | hd_lep0N_w | 4_2_tapbal_grt | 3.2 | last meaningful line 2.8 h ago (46/125 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 5.1 | drt_violations best 36979 last 36979 rows 2 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | 4_1_cts | 0.6 | last meaningful line 0.2 h ago (5477/5477 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t51-3353873 | slice_station__t51 | 5_2_route | 5.2 | last meaningful line 0.0 h ago (254/254 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | 5_1_grt | 5.0 | last meaningful line 0.7 h ago (220/1429 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | 5_1_grt | 5.0 | last meaningful line 1.7 h ago (220/1143 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | otc-1420229-24210 | 1420229 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc10 | otc-1595026-24344 | 1595026 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc10 | otc-612802-27651 | 612802 | pdr_B | 1.0 | last meaningful line 0.0 h ago (3/3 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-616218-14777 | 616218 | - | 1.0 |  | NO-DATA: no log found |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2t-853863 | eco_20261121_154936_3396612-i2t | 5_2_route | 3.7 | drt_violations best 19915 last 19915 rows 2 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4022236 | col_h9_r2__t1 | 5_2_route | 5.2 | drt_violations best 1389 last 1391 rows 19 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_io_cor-579275 | kv3_io_cor | 6_report | 4.7 | last meaningful line 0.1 h ago (1069/1069 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_1_grt | 5.3 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-3888951 | sle_fw_v2 | 5_1_grt | 5.3 | repair_Remaining best 328912 last 328912 rows 117 | YOUNG: stage 1.0 h < 1 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | tt_setup_repair_grt | 5.2 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3849055 | sle_su_l1 | 5_2_route | 5.3 | drt_violations best 83845 last 83845 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_1_grt | 5.2 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_1_grt | 5.2 | repair_Remaining best 344275 last 344275 rows 96 | YOUNG: stage 0.8 h < 1 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_1_grt | 5.2 | last meaningful line 0.1 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | klegacy-bksel_q_oll0-788485 | bksel_q_oll0 | 5_1_grt | 0.5 | last meaningful line 0.0 h ago (312/312 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | klegacy-bksel_q_oll0-788485-lec | bksel_q_oll0 | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (312/312 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-1087890-2714 | 1087890 | s81_head.t.ot_s81hd_st_n3_turn | 0.2 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-1256127-32685 | 1256127 | s81_head.t.ot_s81hd_st_n3_turn | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00_s2-2908697 | cbf_q00_s2 | 3_3_place_gp | 0.7 | overflow best 0.5164 last 0.5164 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-2747549 | cbn_q00 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (300/300 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-2791325 | sle_ctl | 3_2_place_iop | 0.8 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | 6_report | 14.3 | last meaningful line 0.1 h ago (22/22 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t29__cl2e5c855a-3216105 | slice_station__t29 | 3_3_place_gp | 0.4 | overflow best 0.3022 last 0.3022 rows 36 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slice_station__t29__clc7772371-3216906 | slice_station__t29 | 3_3_place_gp | 0.4 | overflow best 0.1982 last 0.1982 rows 48 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slice_station__t6__cl54a9ceeb-3208476 | slice_station__t6 | 3_3_place_gp | 0.4 | overflow best 0.198 last 0.198 rows 47 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | prd-eco_20261122_105456_3667962-i1-2785704 | eco_20261122_105456_3667962-i1 | 5_1_grt | 0.8 | last meaningful line 0.4 h ago (239/1146 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_110517_3693274-i1-3246240 | eco_20261122_110517_3693274-i1 | 5_1_grt | 0.4 | last meaningful line 0.1 h ago (237/314 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-cbn-q00--cl622f65d2-grt-196639 | cbn-q00--cl622f65d2-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3864566 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.4 | overflow best 0.2781 last 0.2781 rows 35 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-41017 | col_h9_r0_p2__t1 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (318/318 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-132151 | col_h9_r0_p3__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 707 | YOUNG: stage 0.0 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-70042 | col_h9_r0_p3__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3023 last 3023 rows 1119 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | postcts_gate_FF | 4.4 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | tt_setup_repair_grt | 15.2 | last meaningful line 3.0 h ago (18/18 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | 4_1_cts | 1.2 | last meaningful line 0.2 h ago (7446/7446 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-3822452 | kv3_hub_Ei | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.1 h ago (57/57 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | 4_1_cts | 0.6 | last meaningful line 0.1 h ago (6107/6107 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3890798 | kv3_hub_Eo | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-3879851 | kv3_hub_Wo | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_pc_v3-3778372 | kv3_pc_v3 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-178255-17383 | 178255 | qwen_kvsys.t.kv_cland_w523_ew_23deb | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco-i1-2157331 | eco-i1 | 5_2_route | 2.1 | drt_violations best 905 last 905 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | prd-eco-i1t-3166843 | eco-i1t | 5_2_route | 0.9 | last meaningful line 0.1 h ago (253/254 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-col-h10-r1--t1--cld01bb4ae-grt-2501754 | col-h10-r1--t1--cld01bb4ae-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2348402 | col_h10_r1__t1 | tt_setup_measure_grt | 3.6 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-907630 | col_h10_r2__t1 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hroot-1734783 | kv3_hroot | 3_4_place_resized | 0.7 | repair_Remaining best 22442 last 22442 rows 72 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | dpkit-kv3_sys_c-996818 | kv3_sys_c | 5_1_grt | 4.8 | repair_Viol best 247 last 247 rows 9 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | 5_1_grt | 6.0 | last meaningful line 0.1 h ago (143/143 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t45-2066564 | slice_station__t45 | 3_4_place_resized | 0.5 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | 5_1_grt | 5.4 | last meaningful line 0.0 h ago (189/191 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | 5_1_grt | 5.4 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3696149 | slw_hc3 | 5_2_route | 6.1 | last meaningful line 0.1 h ago (260/260 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-331468 | slw_st_a_v1 | 5_2_route | 5.4 | drt_violations best 39741 last 39741 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | prd-eco-i1-1034174 | eco-i1 | 5_1_grt | 1.3 | last meaningful line 0.8 h ago (223/1913 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | prd-eco-i1t-4120075 | eco-i1t | 5_2_route | 2.1 | last meaningful line 0.2 h ago (288/289 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | prd-eco2-i1-1371951 | eco2-i1 | 5_2_route | 1.0 | drt_violations best 19563 last 19563 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_2_route | 4.3 | drt_violations best 12136 last 12136 rows 4 | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | ap-ageom-kw-cbf-q00--cl870de686-grt-3640742 | cbf-q00--cl870de686-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (144/144 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | ap-ageom-kw-cbf-q01-s2-grt-3609418 | cbf-q01-s2-grt | 3_5_place_dp | 0.2 | last meaningful line 0.2 h ago (144/144 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-cbn_q00__cldbcda913-2769684 | cbn_q00 | 3_5_place_dp | 0.8 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-cbn_q11__cl5cc92dfe-2877519 | cbn_q11 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (86/86 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3048820 | col_h9_r1__t1 | 5_2_route | 3.9 | last meaningful line 0.1 h ago (269/269 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 4.5 | last meaningful line 0.1 h ago (247/248 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-1537459 | kv3_hub_Ei | 3_3_place_gp | 1.7 | overflow best 0.0988 last 0.0988 rows 44 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-kv3_pc__cl5a95b461-2425782 | kv3_pc | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (83/83 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-serdes__t14-3188947 | serdes__t14 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.1 h ago (92/92 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-serdes__t16-2998841 | serdes__t16 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.1 h ago (94/94 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-838976 | slw_hc3 | 5_1_grt | 5.8 | last meaningful line 0.1 h ago (1028/1034 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | otc-3726082-17019 | 3726082 | qwen_compute.t.sle_hc2__cl9c4c4509__cl3edce1b8 | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-3727667-26279 | 3727667 | qwen_compute.t.sle_hc2__cl9c4c4509__cl3edce1b8 | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 6.2 | drt_violations best 15183 last 15183 rows 6 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 1.7 | drt_violations best 20664 last 20664 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_2_route | 9.6 | drt_violations best 29294 last 29294 rows 2 | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-802974 | coll_ftm | 5_2_route | 1.5 | last meaningful line 0.1 h ago (240/241 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-hd_host_n-2200297 | hd_host_n | 5_2_route | 1.0 | drt_violations best 4406 last 4406 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-3064360 | hd_turn_a | 5_2_route | 0.5 | drt_violations best 5492 last 5492 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-3889860 | hd_turn_a | 5_2_route | 0.3 | last meaningful line 0.0 h ago (207/207 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 1.0 | repair_TNS best 306043 last 306043 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-92918 | ot_s81sl_kv_leaf__t5 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t18-3804050 | slice_station__t18 | 3_3_place_gp | 0.4 | overflow best 0.3844 last 0.385 rows 26 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slice_station__t40__cl1ea9de02-3804079 | slice_station__t40 | 3_3_place_gp | 0.4 | overflow best 0.2308 last 0.2312 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slice_station__t6__cl0755c26e-3779936 | slice_station__t6 | 3_3_place_gp | 0.4 | overflow best 0.1987 last 0.1987 rows 47 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | otc-2832794-13038 | 2832794 | gen_lint_yosys | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | so_78673_ff_74161 | so_78673_ff_74161 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_78673_tt_74161 | so_78673_tt_74161 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 44.6 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-coll_core-2083685 | coll_core | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | 5_1_grt | 4.9 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | otc-1452780-18337 | 1452780 | cut_equiv | 7.1 | last meaningful line 0.0 h ago (872283/872283 lines) | PROGRESS: log still growing |  |
| epyc10 | otc-1610195-24003 | 1610195 | cut_equiv | 6.9 | last meaningful line 0.0 h ago (1159708/1159708 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 48.7 | last meaningful line 1.1 h ago (1556/1556 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-native59-3892390 | native59 | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 5_1_grt | 5.3 | repair_TNS best 0 last 0 rows 19 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | 5_1_grt | 5.3 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | pregrt_ff_hold | 5.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | pregrt_ff_hold | 5.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | pregrt_ff_hold | 5.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | 5_1_grt | 5.2 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-tt_ctlm-4018901 | tt_ctlm | pregrt_ff_hold | 5.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | pregrt_ff_hold | 5.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | pregrt_ff_hold | 5.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fw_v3-2675829 | slw_fw_v3 | tt_setup_repair_grt | 5.5 | repair_Violations best 0 last 0 rows 6 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 15.4 | drt_violations best 51519 last 51519 rows 14 | before-window best 59812, window best 51519 | PROGRESS: drt_violations improved 13.9 % in window |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 14.6 | drt_violations best 597 last 5065 rows 26 | before-window best 1561, window best 597 | PROGRESS: drt_violations improved 61.8 % in window |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 14.4 | drt_violations best 46518 last 46518 rows 13 | before-window best 55180, window best 46518 | PROGRESS: drt_violations improved 15.7 % in window |  |
| epyc9 | dpkit-glue-344102 | glue | 5_1_grt | 5.4 | repair_TNS best 0 last 0 rows 16 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 5_1_grt | 5.4 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | pregrt_ff_hold | 5.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | 5_1_grt | 5.8 | repair_TNS best 0 last 0 rows 4 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | pregrt_ff_hold | 5.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | tt_setup_repair_grt | 49.1 | repair_Violations best 0 last 0 rows 15 | PROGRESS: repair_Violations reached 0 |  |
