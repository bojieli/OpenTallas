# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-22 04:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'CANCEL-NOW': 3, 'GRT-LABEL': 20, 'YOUNG': 84, 'NO-DATA': 4, 'EXCLUDED': 2, 'KEEP': 1, 'PROGRESS': 33}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 13.5 | last meaningful line 11.8 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 11.8 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-583234 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 6_report | 0.5 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-1523684 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 3_3_place_gp | 0.2 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-1523684-lec | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | lec | 0.0 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-coll_core-3827287 | coll_core | 5_1_grt | 5.7 | grt rounds 2 overflow 5:11623 -> 10:2042 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 43.2 | grt rounds 4 overflow 5:104318 -> 10:62060 -> 15:49023 -> 20:49757 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 57.6 | grt rounds 6 overflow 5:9444 -> 10:5570 -> 15:3582 -> 20:3173 -> 25:3124 -> 30:1525 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-3888951 | sle_fw_v2 | 5_1_grt | 6.3 | grt rounds 1 overflow 5:26779 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-3023973 | col_h10_r0_p4__t1 | 5_1_grt | 5.9 | grt rounds 2 overflow 5:62130 -> 10:209 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 36.7 | grt rounds 3 overflow 5:64751 -> 10:67162 -> 15:59403 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 41.7 | grt rounds 3 overflow 5:61400 -> 10:63297 -> 15:55011 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 31.1 | grt rounds 4 overflow 5:51174 -> 10:49018 -> 15:39466 -> 20:42804 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 31.1 | grt rounds 3 overflow 5:59202 -> 10:48240 -> 15:39607 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 40.8 | grt rounds 4 overflow 5:82513 -> 10:49854 -> 15:42880 -> 20:44278 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 30.6 | grt rounds 4 overflow 5:105414 -> 10:69762 -> 15:50712 -> 20:57946 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3444730 | ot_s81sl_leaf__t39 | 5_1_grt | 5.4 | grt rounds 2 overflow 5:827 -> 10:318 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | 5_1_grt | 14.4 | grt rounds 2 overflow 5:39369 -> 10:31446 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | clkgrt-base-1763391 | clkgrt-base | 5_1_grt | 3.5 | grt rounds 2 overflow 5:60327 -> 10:46634 | GRT-LABEL: DESIGN-FAIL: overflow 46634 at round 10 > 1000 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-86653 | col_h9_r0_p3__t1 | 5_1_grt | 5.3 | grt rounds 2 overflow 5:63492 -> 10:344 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 31.9 | grt rounds 5 overflow 5:20337 -> 10:12248 -> 15:11083 -> 20:10120 -> 25:22767 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hroot-3564680 | kv3_hroot | 5_1_grt | 3.3 | grt rounds 2 overflow 5:4295 -> 10:1894 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 44.8 | grt rounds 5 overflow 5:32844 -> 10:12056 -> 15:8164 -> 20:7397 -> 25:22417 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 55.5 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 38.3 | grt rounds 6 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8231 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-coll_ftc-3642118 | coll_ftc | generate_abstract | 6.0 | last meaningful line 0.0 h ago (1024/1024 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_ctl-2275016 | hd_ctl | 5_2_route | 3.8 | last meaningful line 0.0 h ago (118/118 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_host_e-1541416 | hd_host_e | 5_2_route | 4.3 | drt_violations best 28 last 30 rows 51 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N_w-1727564 | hd_lep0N_w | 4_2_tapbal_grt | 4.2 | last meaningful line 3.8 h ago (46/132 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hroot-3517685 | kv3_hroot | 5_2_route | 6.1 | drt_violations best 7642 last 7642 rows 10 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | dpkit-sle_fe_v1__cl1cbb7497-1218154 | sle_fe_v1 | 4_1_cts | 1.6 | last meaningful line 0.0 h ago (5668/5668 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3716104 | sle_st_b_v1 | 5_1_grt | 5.9 | last meaningful line 0.2 h ago (226/946 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t51-3353873 | slice_station__t51 | 5_2_route | 6.2 | last meaningful line 0.1 h ago (275/276 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v2__cl8537f156-3629191 | slw_fw_v2 | tt_setup_repair_grt | 6.0 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3644806 | slw_st_b_v2 | 5_1_grt | 5.9 | last meaningful line 1.5 h ago (218/1162 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | otc-1420229-24210 | 1420229 | - | 1.4 |  | NO-DATA: no log found |  |
| epyc10 | otc-616218-14777 | 616218 | - | 2.0 |  | NO-DATA: no log found |  |
| epyc10 | prd-eco_20261121_154936_3396612-i2t-853863 | eco_20261121_154936_3396612-i2t | 5_2_route | 4.7 | drt_violations best 8983 last 8983 rows 5 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-4022236 | col_h9_r2__t1 | 5_2_route | 6.2 | drt_violations best 1389 last 1394 rows 36 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3881556 | sle_fw_v1 | 5_1_grt | 6.3 | last meaningful line 0.6 h ago (221/1030 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-3924103 | sle_stm_v2 | postcts_gate_TT | 6.3 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-3932533 | sle_stm_v2 | postcts_gate_FF | 6.2 | last meaningful line 0.0 h ago (1688/1688 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3849055 | sle_su_l1 | 5_2_route | 6.3 | drt_violations best 9265 last 9265 rows 3 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t37-2177556 | slice_station__t37 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3611/3611 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__cl95cd1d0c-3940689 | slw_fe_v1 | 5_1_grt | 6.2 | last meaningful line 0.7 h ago (220/1411 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-3955497 | slw_fe_v1 | 5_1_grt | 6.2 | repair_TNS best 3854.93 last 3854.93 rows 6 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3952036 | slw_fw_v1 | 5_1_grt | 6.2 | repair_TNS best 0.969 last 0.969 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cle6023ec2-4002239 | slw_st_b_v1 | 5_1_grt | 6.2 | last meaningful line 0.1 h ago (219/295 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-4015786 | slw_stm_v2 | 5_1_grt | 6.2 | last meaningful line 0.1 h ago (1057/1063 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | klegacy-bksel_q_oll0-788485 | bksel_q_oll0 | lec | 1.5 | LEC last write 0.1 h ago | YOUNG: evidence 1.5 h < 6 h |  |
| epyc2 | otc-2202886-16532 | 2202886 | qwen_compute.t.slw_stm_v2__cl1ca9c415 | 0.1 | last meaningful line 0.1 h ago (2/2 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00_s2-2908697 | cbf_q00_s2 | 3_4_place_resized | 1.4 | last meaningful line 0.0 h ago (331/331 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-145913 | dsdv_slice_kv512_C__t1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (400/400 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-2791325 | sle_ctl | 3_4_place_resized | 1.5 | last meaningful line 0.1 h ago (435/435 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | 6_report | 15.0 | last meaningful line 0.1 h ago (649/649 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t29__cl2e5c855a-4051807 | slice_station__t29 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.1985 last 0.1985 rows 45 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_fw_v3-2675829 | slw_fw_v3 | 5_2_route | 6.2 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | otc-3828137-8889 | 3828137 | - | 0.6 |  | NO-DATA: no log found |  |
| epyc7 | otc-96114-15417 | 96114 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261122_105456_3667962-i1-2785704 | eco_20261122_105456_3667962-i1 | 5_2_route | 1.5 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261122_110517_3693274-i1-3246240 | eco_20261122_110517_3693274-i1 | 5_1_grt | 1.1 | last meaningful line 0.9 h ago (237/1443 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1220915 | col_h9_r0_p2__t1 | 5_2_route | 8.1 | last meaningful line 0.2 h ago (286/287 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-1158230 | col_h9_r0_p3__t1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (3131/3131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-4167505 | col_h9_r0_p6__t1 | 5_2_route | 5.4 | last meaningful line 0.1 h ago (280/281 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_2_route | 16.2 | last meaningful line 0.1 h ago (277/278 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Ei-3822452 | kv3_hub_Ei | 3_4_place_resized | 1.4 | last meaningful line 0.1 h ago (275/275 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3515913 | kv3_hub_Eo | 4_1_cts | 1.6 | last meaningful line 0.2 h ago (6509/6509 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3890798 | kv3_hub_Eo | 3_3_place_gp | 1.4 | overflow best 0.0997 last 0.0997 rows 44 | YOUNG: stage 0.6 h < 1 h |  |
| epyc8 | dpkit-kv3_hub_Wo-3521232 | kv3_hub_Wo | 4_1_cts | 1.6 | last meaningful line 0.0 h ago (6631/6631 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Wo-3879851 | kv3_hub_Wo | 3_3_place_gp | 1.4 | overflow best 0.0987 last 0.0987 rows 46 | YOUNG: stage 0.6 h < 1 h |  |
| epyc8 | dpkit-kv3_pc_v3-3778372 | kv3_pc_v3 | 3_4_place_resized | 1.4 | last meaningful line 0.0 h ago (373/373 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-342043-29119 | 342043 | gen_lint_yosys | 0.9 | last meaningful line 0.1 h ago (7/7 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | otc-796748-28106 | 796748 | qwen_compute.t.slw_su_l0__cl1a1c1f8f | 0.5 | last meaningful line 0.1 h ago (4/4 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | prd-eco-i1-2157331 | eco-i1 | 5_3_fillcell | 3.1 | last meaningful line 0.2 h ago (22/22 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | prd-eco-i1t-3166843 | eco-i1t | 5_2_route | 1.9 | drt_violations best 40634 last 40634 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-col-h9-r0-p1--t1--pv697f40c9-grt-3279750 | col-h9-r0-p1--t1--pv697f40c9-grt | 3_5_place_dp | 0.2 | last meaningful line 0.2 h ago (140/140 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-col-h9-r0-p3--t1--cl0cd90c0e--pv13474472-grt-3446539 | col-h9-r0-p3--t1--cl0cd90c0e--pv13474472-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2348402 | col_h10_r1__t1 | 5_2_route | 4.3 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-907630 | col_h10_r2__t1 | 5_1_grt | 2.1 | repair_TNS best 71.147 last 71.147 rows 4 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-glue-344102 | glue | postcts_gate_FF | 6.1 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hroot-3019559 | kv3_hroot | 4_2_tapbal_grt | 0.4 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_sys_c-996818 | kv3_sys_c | 5_1_grt | 5.5 | repair_Viol best 247 last 247 rows 23 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-315908 | sle_hc1 | 5_1_grt | 6.2 | last meaningful line 0.0 h ago (138/138 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3792492 | sle_st_b_v1 | 5_1_grt | 6.7 | last meaningful line 0.4 h ago (226/1073 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3990001 | sle_st_b_v2 | 5_1_grt | 6.6 | last meaningful line 1.2 h ago (227/1133 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3696149 | slw_hc3 | 5_2_route | 6.8 | drt_violations best 74054 last 74054 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-331468 | slw_st_a_v1 | 5_2_route | 6.1 | drt_violations best 39741 last 39741 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | prd-eco-i1-1034174 | eco-i1 | 5_2_route | 2.1 | last meaningful line 0.1 h ago (259/260 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | prd-eco-i1t-4120075 | eco-i1t | 5_2_route | 2.8 | drt_violations best 3383 last 3383 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i3t-1483960 | eco_20261121_070035_1645318-i3t | 5_2_route | 5.0 | drt_violations best 10655 last 10655 rows 6 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc9 | so_3352428_ff_75780 | so_3352428_ff_75780 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (336/336 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | so_3352428_tt_75780 | so_3352428_tt_75780 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (336/336 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3916217 | col_h10_r1__t1 | pregrt_ff_hold | 0.9 | repair_TNS best 59490.1 last 59490.1 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-3924033 | col_h10_r1__t1 | pregrt_ff_hold | 0.9 | repair_TNS best 52805.8 last 52805.8 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-546077 | col_h10_r1__t1 | 2_1_floorplan | 0.1 | repair_Viol best 3559 last 3559 rows 1222 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3048820 | col_h9_r1__t1 | 5_2_route | 4.9 | last meaningful line 0.3 h ago (280/281 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-hd_lep0N_w-509634 | hd_lep0N_w | 3_1_place_gp_skip_io | 0.1 | overflow best 0.587 last 0.587 rows 24 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-kv3_hroot-2366276 | kv3_hroot | 5_2_route | 5.5 | drt_violations best 87099 last 87099 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-1537459 | kv3_hub_Ei | 3_4_place_resized | 2.7 | last meaningful line 0.5 h ago (354/354 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-serdes__t12-3861414 | serdes__t12 | 3_3_place_gp | 0.9 | overflow best 0.5164 last 0.5164 rows 35 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-838976 | slw_hc3 | 5_2_route | 6.8 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1235664 | slw_st_b_v1 | 5_1_grt | 6.5 | last meaningful line 0.2 h ago (143/143 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | otc-371707-13395 | 371707 | qwen_compute.t.sle_st_b_v2__clfde1249e | 0.3 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-461535-7628 | 461535 | qwen_compute.t.sle_st_b_v2__clfde1249e | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1-1522262 | eco_20261121_161716_4143584-i1 | 5_2_route | 2.7 | drt_violations best 2262 last 2262 rows 4 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1722071 | col_h9_r0_p2__t1 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (3037/3038 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-802974 | coll_ftm | 5_2_route | 2.2 | drt_violations best 187 last 187 rows 3 | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1385359 | dsdv_slice_lepe_nh_mus_C__t1 | sdc_lint | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-1520809 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-614508 | hd_turn_a | 5_2_route | 0.5 | drt_violations best 5492 last 5492 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-92918 | ot_s81sl_kv_leaf__t5 | 3_3_place_gp | 0.8 | overflow best 0.8506 last 0.8506 rows 19 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-157517 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (227/228 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | prd-eco_20261122_041142_2199995-i1t-1449367 | eco_20261122_041142_2199995-i1t | 5_2_route | 0.3 | last meaningful line 0.0 h ago (219/220 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | otc-2166440-17463 | 2166440 | - | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | otc-3236621-30936 | 3236621 | - | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 45.4 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc10 | dpkit-cbf_q00__cl1b5a6458-2286764 | cbf_q00 | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-coll_core-2083685 | coll_core | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-3572126 | slw_fe_v1 | 5_1_grt | 6.0 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | otc-1610195-24003 | 1610195 | cut_equiv | 7.9 | last meaningful line 0.1 h ago (1160408/1160408 lines) | PROGRESS: log still growing |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 49.7 | last meaningful line 0.2 h ago (1558/1558 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-native59-3892390 | native59 | pregrt_ff_hold | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-3900617 | sle_fw_v1 | 5_1_grt | 6.3 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-3898323 | sle_hc1 | pregrt_ff_hold | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-3899470 | sle_hc1 | pregrt_ff_hold | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3945997 | slw_fe_v2 | 5_1_grt | 6.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cle683a076-3964971 | slw_hc1 | pregrt_ff_hold | 6.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-tt_ctlm-4018901 | tt_ctlm | 5_1_grt | 6.2 | repair_TNS best 0 last 0 rows 27 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv48712631-2630006 | sle_hc0 | 5_1_grt | 6.3 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa__pv6e886d59-2631018 | sle_hc0 | 5_1_grt | 6.3 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 16.1 | drt_violations best 51519 last 51519 rows 14 | before-window best 55390, window best 51519 | PROGRESS: drt_violations improved 7.0 % in window |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-643864 | col_h9_r0_p2__t1 | tt_setup_repair | 0.6 | repair_Violations best 0 last 0 rows 13 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 4_1_cts | 0.3 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-kv3_hub_Ei-2959667 | kv3_hub_Ei | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 15.6 | drt_violations best 597 last 1701 rows 28 | before-window best 1433, window best 597 | PROGRESS: drt_violations improved 58.3 % in window |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 15.4 | drt_violations best 46518 last 46518 rows 13 | before-window best 53604, window best 46518 | PROGRESS: drt_violations improved 13.2 % in window |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-362241 | sle_fw_v2 | 5_1_grt | 6.1 | repair_TNS best 0 last 0 rows 6 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvd0aa3ddc-288520 | slw_hc0 | 5_1_grt | 6.2 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc0__cl4f54b7a3__pvde134a90-303632 | slw_hc0 | 5_1_grt | 6.2 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | ap-ageom-kw-serdes--t14-grt-554201 | serdes--t14-grt | 3_5_place_dp | 0.1 | repair_Violations best 0 last 0 rows 9 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | ap-ageom-kw-serdes--t16-grt-519946 | serdes--t16-grt | 3_5_place_dp | 0.1 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-phy__t1-161516 | phy__t1 | pregrt_ff_hold | 0.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-2323566 | sle_st_b_v2 | pregrt_ff_hold | 5.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261121_082001_3216437-i2t-526594 | eco_20261121_082001_3216437-i2t | 5_2_route | 7.2 | drt_violations best 13015 last 13015 rows 8 | before-window best 152197, window best 13015 | PROGRESS: drt_violations improved 91.4 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_2_route | 10.6 | drt_violations best 54 last 54 rows 7 | before-window best 170434, window best 54 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_LP__t2-3588408 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-hd_host_n-1689611 | hd_host_n | 5_1_grt | 0.1 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-kv3_io_ft-595098 | kv3_io_ft | 5_1_grt | 0.5 | repair_TNS best 0 last 0 rows 20 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-2175611 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
