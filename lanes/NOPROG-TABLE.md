# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 04:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'CANCEL-NOW': 1, 'GRT-LABEL': 20, 'YOUNG': 92, 'NO-DATA': 6, 'EXCLUDED': 2, 'KEEP': 1, 'PROGRESS': 24}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 13.2 | last meaningful line 11.5 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 11.5 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-583234 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 5_2_route | 0.2 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 42.7 | grt rounds 4 overflow 5:104318 -> 10:62060 -> 15:49497 -> 20:49757 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 57.1 | grt rounds 6 overflow 5:9444 -> 10:5570 -> 15:3582 -> 20:2874 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | klegacy-bksel_q_oll0-788485 | bksel_q_oll0 | 5_1_grt | 1.2 | grt rounds 3 overflow 5:23566 -> 10:1860 -> 15:27 | GRT-LABEL: DESIGN-FAIL: overflow 1860 at round 10 > 1000 |  |
| epyc2 | klegacy-bksel_q_oll0-788485-lec | bksel_q_oll0 | 5_1_grt | 1.2 | grt rounds 3 overflow 5:23566 -> 10:1860 -> 15:27 | GRT-LABEL: DESIGN-FAIL: overflow 1860 at round 10 > 1000 |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-3023973 | col_h10_r0_p4__t1 | 5_1_grt | 5.7 | grt rounds 2 overflow 5:62130 -> 10:209 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 36.5 | grt rounds 3 overflow 5:64751 -> 10:65943 -> 15:59403 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 41.4 | grt rounds 3 overflow 5:61400 -> 10:63297 -> 15:55011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 30.8 | grt rounds 4 overflow 5:51174 -> 10:49018 -> 15:39466 -> 20:42804 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 30.8 | grt rounds 3 overflow 5:59202 -> 10:49628 -> 15:39607 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 40.6 | grt rounds 4 overflow 5:82307 -> 10:49854 -> 15:42880 -> 20:44278 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 30.3 | grt rounds 4 overflow 5:105414 -> 10:69762 -> 15:50712 -> 20:57946 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 5.2 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | 5_1_grt | 14.2 | grt rounds 2 overflow 5:39369 -> 10:31446 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | clkgrt-base-1763391 | clkgrt-base | 5_1_grt | 3.0 | grt rounds 2 overflow 5:60327 -> 10:46634 | GRT-LABEL: DESIGN-FAIL: overflow 46634 at round 10 > 1000 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_1_grt | 4.8 | grt rounds 2 overflow 5:63492 -> 10:344 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 31.4 | grt rounds 5 overflow 5:20337 -> 10:12248 -> 15:11083 -> 20:10120 -> 25:22767 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hroot-3564680 | kv3_hroot | 5_1_grt | 3.0 | grt rounds 2 overflow 5:4295 -> 10:1894 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 44.5 | grt rounds 5 overflow 5:32844 -> 10:12056 -> 15:8164 -> 20:7397 -> 25:22417 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 55.3 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 38.0 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10993 -> 25:8231 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-1532241 | cbf_q00 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2286764 | cbf_q00 | hold_gate | 0.2 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 5.2 | last meaningful line 0.5 h ago (199/206 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-coll_ftc-3642118 | coll_ftc | 5_2_route | 5.5 | drt_violations best 5772 last 5772 rows 3 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-hd_ctl-2275016 | hd_ctl | tt_setup_repair_grt | 3.3 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_host_e-1541416 | hd_host_e | 5_2_route | 3.8 | drt_violations best 28 last 30 rows 51 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-1727564 | hd_lep0N_w | 4_2_tapbal_grt | 3.7 | last meaningful line 3.3 h ago (46/129 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 5.6 | drt_violations best 10671 last 10671 rows 6 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | 4_1_cts | 1.1 | last meaningful line 0.2 h ago (5533/5533 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | 5_1_grt | 5.4 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t51-3353873 | slice_station__t51 | 5_2_route | 5.7 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | 5_1_grt | 5.5 | repair_TNS best 230.773 last 230.773 rows 9 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | otc-1420229-24210 | 1420229 | - | 0.9 |  | NO-DATA: no log found |  |
| epyc10 | otc-616218-14777 | 616218 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2t-853863 | eco_20261121_154936_3396612-i2t | 5_2_route | 4.2 | drt_violations best 9794 last 9794 rows 4 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-slice-station--t37-grt-2010853 | slice-station--t37-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4022236 | col_h9_r2__t1 | 5_2_route | 6.0 | drt_violations best 1389 last 1393 rows 32 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 5_1_grt | 6.0 | last meaningful line 2.0 h ago (278/1225 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_1_grt | 6.0 | repair_Remaining best 229279 last 229279 rows 237 | YOUNG: stage 1.0 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-3888951 | sle_fw_v2 | 5_1_grt | 6.0 | last meaningful line 0.9 h ago (316/1084 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | tt_setup_repair_grt | 6.0 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | postcts_gate_FF | 6.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3849055 | sle_su_l1 | 5_2_route | 6.0 | drt_violations best 13829 last 13829 rows 2 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_1_grt | 6.0 | repair_Remaining best 249942 last 249942 rows 180 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_1_grt | 6.0 | repair_TNS best 6989.24 last 6989.24 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | 5_1_grt | 6.0 | last meaningful line 0.0 h ago (190/192 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_1_grt | 6.0 | last meaningful line 0.5 h ago (226/1099 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | 5_1_grt | 6.0 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | otc-1925828-31318 | 1925828 | s81.t.slice_station__t27 | 0.1 | last meaningful line 0.1 h ago (2/2 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-cbn-q00--cld7bf7197-grt-4020022 | cbn-q00--cld7bf7197-grt | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbf_q00_s2-2908697 | cbf_q00_s2 | 3_4_place_resized | 1.2 | last meaningful line 0.1 h ago (21/21 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-2791325 | sle_ctl | 3_3_place_gp | 1.3 | overflow best 0.0988 last 0.0988 rows 48 | YOUNG: stage 0.5 h < 1 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | 6_report | 14.8 | last meaningful line 0.2 h ago (53/53 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | 5_1_grt | 6.0 | last meaningful line 0.2 h ago (214/272 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | 5_1_grt | 6.0 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t29__cl2e5c855a-4051807 | slice_station__t29 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v3-2675829 | slw_fw_v3 | 5_2_route | 6.0 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | otc-3828137-8889 | 3828137 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc7 | otc-4189132-16954 | 4189132 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_105456_3667962-i1-2785704 | eco_20261122_105456_3667962-i1 | 5_2_route | 1.3 | last meaningful line 0.0 h ago (270/271 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_110517_3693274-i1-3246240 | eco_20261122_110517_3693274-i1 | 5_1_grt | 0.9 | last meaningful line 0.6 h ago (237/1434 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-col-h9-r0-p2--t1--cl9f71e63d--pva4376595-grt-709467 | col-h9-r0-p2--t1--cl9f71e63d--pva4376595-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1220915 | col_h9_r0_p2__t1 | 5_2_route | 7.6 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-643864 | col_h9_r0_p2__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3121/3121 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-132151 | col_h9_r0_p3__t1 | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (234/234 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-70042 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.6 | overflow best 0.2458 last 0.2458 rows 37 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 4.9 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_2_route | 15.7 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-3822452 | kv3_hub_Ei | 3_3_place_gp | 0.9 | overflow best 0.0993 last 0.0993 rows 48 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | 4_1_cts | 1.1 | last meaningful line 0.1 h ago (6450/6450 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3890798 | kv3_hub_Eo | 3_3_place_gp | 0.9 | overflow best 0.5787 last 0.5787 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (6233/6233 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-3879851 | kv3_hub_Wo | 3_3_place_gp | 0.9 | overflow best 0.7165 last 0.7165 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-kv3_pc_v3-3778372 | kv3_pc_v3 | 3_3_place_gp | 0.9 | overflow best 0.6287 last 0.6287 rows 26 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | otc-342043-29119 | 342043 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | otc-684404-20113 | 684404 | s81.t.s81p_slice_station__t36 | 0.1 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | otc-796748-28106 | 796748 | s81.t.s81p_slice_station__t36 | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | prd-eco-i1-2157331 | eco-i1 | 5_2_route | 2.6 | drt_violations best 905 last 905 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | prd-eco-i1t-3166843 | eco-i1t | 5_2_route | 1.4 | drt_violations best 40634 last 40634 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-col-h9-r0-p2--t1--cl0045af7b--pva2793873-grt-3101764 | col-h9-r0-p2--t1--cl0045af7b--pva2793873-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2348402 | col_h10_r1__t1 | 5_2_route | 4.1 | last meaningful line 0.0 h ago (267/267 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-907630 | col_h10_r2__t1 | 5_1_grt | 1.9 | last meaningful line 0.2 h ago (233/1232 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-glue-344102 | glue | tt_setup_repair_grt | 5.9 | last meaningful line 0.0 h ago (672/672 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_host_n-2990279 | hd_host_n | 3_3_place_gp | 0.2 | overflow best 0.0993 last 0.0993 rows 49 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-kv3_hroot-3019559 | kv3_hroot | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3313/3313 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_sys_c-996818 | kv3_sys_c | 5_1_grt | 5.3 | repair_Viol best 247 last 247 rows 19 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 5_1_grt | 5.9 | last meaningful line 2.5 h ago (221/1137 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | 5_1_grt | 6.5 | last meaningful line 0.2 h ago (226/294 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | 5_1_grt | 5.9 | last meaningful line 0.5 h ago (214/926 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | 5_1_grt | 5.9 | last meaningful line 0.2 h ago (213/941 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3696149 | slw_hc3 | 5_2_route | 6.6 | last meaningful line 0.1 h ago (275/276 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-331468 | slw_st_a_v1 | 5_2_route | 5.9 | drt_violations best 39741 last 39741 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | otc-3185279-18598 | 3185279 | ot_bind_native_8251bd358efc6cb1f1cbbf83 | 0.0 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco-i1-1034174 | eco-i1 | 5_2_route | 1.8 | last meaningful line 0.0 h ago (255/256 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | prd-eco-i1t-4120075 | eco-i1t | 5_2_route | 2.6 | last meaningful line 0.2 h ago (294/295 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_2_route | 4.8 | drt_violations best 11334 last 11334 rows 5 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc9 | prd-fin-1371951 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (351/351 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3916217 | col_h10_r1__t1 | pregrt_ff_hold | 0.6 | repair_TNS best 59490.1 last 59490.1 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | pregrt_ff_hold | 0.6 | repair_TNS best 52805.8 last 52805.8 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-3818189 | col_h9_r0_p1__t1 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (97/97 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-3869407 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.7 | overflow best 0.1982 last 0.1982 rows 40 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3048820 | col_h9_r1__t1 | 5_2_route | 4.6 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 5.3 | last meaningful line 0.2 h ago (259/260 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-1537459 | kv3_hub_Ei | 3_4_place_resized | 2.4 | last meaningful line 0.3 h ago (354/354 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-serdes__t12-3861414 | serdes__t12 | 3_3_place_gp | 0.7 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-serdes__t14-3188947 | serdes__t14 | 3_4_place_resized | 1.3 | last meaningful line 0.0 h ago (335/335 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-838976 | slw_hc3 | postcts_gate_FF | 6.6 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | 5_1_grt | 6.2 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-371707-13395 | 371707 | s81.c.ot_s81_svc_hslice | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 2.4 | drt_violations best 20664 last 20664 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-802974 | coll_ftm | 5_2_route | 2.0 | drt_violations best 9684 last 9684 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1385359 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-614508 | hd_turn_a | postcts_gate_FF | 0.2 | last meaningful line 0.0 h ago (515/515 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-595098 | kv3_io_ft | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (71/71 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 1.5 | repair_TNS best 306043 last 306043 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-92918 | ot_s81sl_kv_leaf__t5 | 3_1_place_gp_skip_io | 0.5 | last meaningful line -0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-157517 | slice_station__t12 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (202/202 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | prd-eco_20261122_041142_2199995-i1t-1449367 | eco_20261122_041142_2199995-i1t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (151/151 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-3759084-8720 | 3759084 | asbuilt.yosys | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 45.1 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel2 | otc-399294-10043 | 399294 | - | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-coll_core-2083685 | coll_core | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | 5_1_grt | 5.5 | repair_TNS best 0 last 0 rows 14 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | 5_1_grt | 5.4 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | otc-1610195-24003 | 1610195 | cut_equiv | 7.4 | last meaningful line 0.1 h ago (1160025/1160025 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 49.5 | last meaningful line 1.9 h ago (1556/1556 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-native59-3892390 | native59 | pregrt_ff_hold | 6.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | pregrt_ff_hold | 6.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | pregrt_ff_hold | 6.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | pregrt_ff_hold | 6.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | 5_1_grt | 6.0 | repair_TNS best 0 last 0 rows 16 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-tt_ctlm-4018901 | tt_ctlm | 5_1_grt | 6.0 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 15.9 | drt_violations best 51519 last 51519 rows 14 | before-window best 55390, window best 51519 | PROGRESS: drt_violations improved 7.0 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-399482 | col_h9_r0_p6__t1 | 3_5_place_dp | 0.4 | repair_Violations best 0 last 0 rows 15 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | pregrt_ff_hold | 1.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 15.1 | drt_violations best 597 last 1942 rows 27 | before-window best 1470, window best 597 | PROGRESS: drt_violations improved 59.4 % in window |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 14.9 | drt_violations best 46518 last 46518 rows 13 | before-window best 54158, window best 46518 | PROGRESS: drt_violations improved 14.1 % in window |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | pregrt_ff_hold | 5.9 | repair_Violations best 0 last 0 rows 5 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | 5_1_grt | 6.3 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-phy__t1-161516 | phy__t1 | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-serdes__t16-2998841 | serdes__t16 | 3_5_place_dp | 1.4 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 6.9 | drt_violations best 13015 last 13015 rows 8 | before-window best 152197, window best 13015 | PROGRESS: drt_violations improved 91.4 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_2_route | 10.3 | drt_violations best 600 last 600 rows 4 | before-window best 170434, window best 600 | PROGRESS: drt_violations improved 99.6 % in window |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 4.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
