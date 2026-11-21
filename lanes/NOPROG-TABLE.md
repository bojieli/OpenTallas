# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 11:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 6, 'CANCEL-NOW': 2, 'GRT-LABEL': 31, 'YOUNG': 97, 'NO-DATA': 13, 'EXCLUDED': 6, 'KEEP': 1, 'PROGRESS': 30}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 27.9 | grt rounds 6 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -2893.36 ps (< -300, gate TT >= -42); job age 2 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 41.3 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 41 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc7 | dpkit-cbf_q11-283336 | cbf_q11 | 5_1_grt | 15.2 | grt rounds 6 overflow 5:6375 -> 10:5827 -> 15:5482 -> 20:5460 -> 25:8886 -> 30:7683 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -675.23 ps (< -300, gate TT >= -42); job age 15 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc8 | dpkit-dsdv_slice_c1x_C__t9-950441 | dsdv_slice_c1x_C__t9 | pregrt_ff_hold | 6.4 | repair_TNS best 807293 last 807293 rows 1 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -832.47 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc8 | dpkit-dsdv_slice_lepe_mu_LP__t2-4122597 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -369.28 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-492382 | sle_ctl | 5_1_grt | 7.7 | repair_Viol best 671 last 671 rows 288 | UNSIGNABLE: 5_1_grt.tmp.log setup repair FLAT at WNS -84.97 ps (gate TT >= -42, repair no lo | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-4192649 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 5_2_route | 0.2 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-3550202 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 4_1_cts | 0.7 |  | CANCEL-NOW: HBM is parked | CANCELLED |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 26.4 | grt rounds 3 overflow 5:62850 -> 10:60456 -> 15:49611 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 26.4 | grt rounds 4 overflow 5:56489 -> 10:43484 -> 15:40478 -> 20:43612 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 40.8 | grt rounds 4 overflow 5:9510 -> 10:5086 -> 15:3391 -> 20:2910 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 29.8 | grt rounds 4 overflow 5:51489 -> 10:38067 -> 15:34597 -> 20:37772 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_su_c-2630248 | sle_su_c | 5_1_grt | 8.8 | grt rounds 2 overflow 5:38588 -> 10:37924 | GRT-LABEL: DESIGN-FAIL: overflow 37924 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 20.0 | grt rounds 3 overflow 5:77963 -> 10:75300 -> 15:58855 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 24.9 | grt rounds 3 overflow 5:61289 -> 10:67332 -> 15:69180 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 14.3 | grt rounds 3 overflow 5:50395 -> 10:49359 -> 15:39905 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 14.3 | grt rounds 3 overflow 5:50187 -> 10:49068 -> 15:39498 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 24.1 | grt rounds 3 overflow 5:46870 -> 10:49482 -> 15:43107 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 11.8 | grt rounds 3 overflow 5:78427 -> 10:75315 -> 15:54687 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 20.0 | grt rounds 3 overflow 5:71545 -> 10:71003 -> 15:50882 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 13.8 | grt rounds 3 overflow 5:73809 -> 10:70141 -> 15:51022 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 15.6 | grt rounds 4 overflow 5:42922 -> 10:39064 -> 15:36674 -> 20:37813 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 15.5 | grt rounds 4 overflow 5:41833 -> 10:36208 -> 15:32951 -> 20:32437 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-cbx_q10__cl89936551_h-1010361 | cbx_q10 | 5_1_grt | 6.3 | grt rounds 2 overflow 5:25215 -> 10:24712 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hgi_v2__cl2862d491-3732038 | kv3_hgi_v2 | 5_1_grt | 4.5 | grt rounds 2 overflow 5:72991 -> 10:37675 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hroot-4110897 | kv3_hroot | 5_1_grt | 4.2 | grt rounds 2 overflow 5:3253 -> 10:1440 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 15.2 | grt rounds 4 overflow 5:20011 -> 10:12763 -> 15:11530 -> 20:10671 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hgi_v2__cle0015330-660102 | kv3_hgi_v2 | 5_1_grt | 4.0 | grt rounds 2 overflow 5:59354 -> 10:37389 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hgi_v8-3224135 | kv3_hgi_v8 | 5_1_grt | 8.6 | grt rounds 3 overflow 5:34501 -> 10:16436 -> 15:26195 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 28.0 | grt rounds 3 overflow 5:26517 -> 10:13016 -> 15:8921 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 38.8 | grt rounds 6 overflow 5:23729 -> 10:21694 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: overflow 21694 at round 10 > 1000 |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 39.0 | grt rounds 4 overflow 5:34987 -> 10:28632 -> 15:24645 -> 20:22699 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 5_1_grt | 16.1 | grt rounds 4 overflow 5:54170 -> 10:7759 -> 15:5073 -> 20:4273 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 21.5 | grt rounds 5 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 16.5 | grt rounds 4 overflow 5:36131 -> 10:30276 -> 15:25602 -> 20:22194 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 37.9 | grt rounds 3 overflow 5:56283 -> 10:53405 -> 15:50242 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 32.9 | grt rounds 3 overflow 5:59246 -> 10:47822 -> 15:53864 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 32.9 | grt rounds 3 overflow 5:60515 -> 10:48832 -> 15:53055 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 33.1 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9952 -> 20:9864 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2275786 | col_h10_r2__t1 | 5_1_grt | 3.0 | repair_TNS best 2.053 last 2.053 rows 5 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-2582333 | col_h9_r0_p2__t1 | 5_2_route | 8.2 | last meaningful line 0.2 h ago (281/282 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-22377 | hd_lep0N | 4_1_cts | 4.4 | last meaningful line 0.1 h ago (10619/10619 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-4150550 | hd_lep0N | 3_4_place_resized | 1.7 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1-2739404 | kv3_hg_v1 | 2_1_floorplan | 0.2 | repair_Viol best 7321 last 7321 rows 252 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_hgi_v8-3126306 | kv3_hgi_v8 | 5_1_grt | 7.8 | last meaningful line 1.0 h ago (208/216 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Eo-2185518 | kv3_hub_Eo | 2_1_floorplan | 0.5 | last meaningful line 0.3 h ago (82/82 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t39-243585 | ot_s81sl_leaf__t39 | 5_1_grt | 1.6 | last meaningful line 0.1 h ago (188/201 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t29__clc7772371-2494215 | slice_station__t29 | 3_3_place_gp | 0.4 | overflow best 0.3234 last 0.3234 rows 34 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-slice_station__t36-3668002 | slice_station__t36 | 5_1_grt | 2.1 | last meaningful line 0.1 h ago (215/271 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t36-3913104 | slice_station__t36 | 5_2_route | 4.6 | drt_violations best 47902 last 47902 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t37-173045 | slice_station__t37 | 5_1_grt | 1.6 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v3-1328903 | slw_fw_v3 | postcts_gate_FF | 8.9 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-tt_ctlm-1606453 | tt_ctlm | 5_1_grt | 8.8 | last meaningful line 0.2 h ago (1771/1819 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc10 | otc-3076060-6592 | 3076060 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-3133178-2913 | 3133178 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_014354_2681516-i3-1261179 | eco_20261121_014354_2681516-i3 | 5_2_route | 1.0 | last meaningful line 0.1 h ago (263/264 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1t-894339 | eco_20261121_154936_3396612-i1t | 5_1_grt | 3.9 | repair_Viol best 2419 last 2419 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_184648_4039100-i1t-1413255 | eco_20261121_184648_4039100-i1t | 5_1_grt | 0.9 | last meaningful line 0.3 h ago (232/1282 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | prd-fin-2847283 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (50/50 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl870de686-3870117 | cbf_q00 | pregrt_ff_hold | 1.5 | repair_TNS best 4.18571e+06 last 4.18571e+06 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-2629912 | col_h9_r0_p2__t1 | 5_2_route | 8.8 | last meaningful line 0.2 h ago (281/282 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3129306 | col_h9_r2__t1 | 5_2_route | 5.3 | drt_violations best 60767 last 60767 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v3-3867769 | kv3_hg_v3 | 3_5_place_dp | 1.5 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 2_1_floorplan | 2.9 | last meaningful line 2.3 h ago (1415/1415 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v1-1304161 | kv3_pv_v1 | 3_5_place_dp | 3.8 | last meaningful line 0.2 h ago (57/57 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4n-4044420 | kv3_pv_v4n | 3_4_place_resized | 4.8 | last meaningful line 0.2 h ago (754/754 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v5n-4101656 | kv3_pv_v5n | 3_3_place_gp | 4.7 | overflow best 0.0988 last 0.0988 rows 42 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-native59-3868183 | native59 | 3_3_place_gp | 1.5 | overflow best 0.0999 last 0.0999 rows 177 | YOUNG: stage 0.8 h < 1 h |  |
| epyc2 | dpkit-serdes__t16-1729365 | serdes__t16 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (191/191 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | generate_abstract | 18.4 | last meaningful line 0.2 h ago (1031/1031 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | generate_abstract | 18.3 | last meaningful line 0.2 h ago (939/939 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | generate_abstract | 18.2 | last meaningful line 0.1 h ago (361/361 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t36-3125329 | slice_station__t36 | 5_1_grt | 5.3 | last meaningful line 2.0 h ago (215/691 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2449519 | slw_hc3 | postcts_gate_FF | 8.9 | last meaningful line -0.0 h ago (29582/29582 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3868961 | slw_sc_v1 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (5591/5591 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-count-p1_tc-3115487 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (594/594 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i3-297348 | eco_20261120_134605_3273412-i3 | 5_2_route | 1.1 | last meaningful line 0.0 h ago (266/267 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i2t-2328774 | eco_20261120_170022_4017640-i2t | 5_2_route | 5.9 | drt_violations best 99 last 99 rows 11 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_070700_2142563-i1t-551142 | eco_20261121_070700_2142563-i1t | 5_2_route | 4.3 | drt_violations best 7883 last 7883 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_080323_3018643-i1t-1786242 | eco_20261121_080323_3018643-i1t | 5_2_route | 3.4 | drt_violations best 8738 last 8738 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_102155_957464-i1t-245136 | eco_20261121_102155_957464-i1t | 5_2_route | 1.1 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_105744_956410-i1t-1036390 | eco_20261121_105744_956410-i1t | 5_1_grt | 0.5 | last meaningful line 0.1 h ago (237/258 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-slice-station--t6--cl0755c26e-grt-175934 | slice-station--t6--cl0755c26e-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-993515 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 2.4 | repair_TNS best 221121 last 221121 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc7 | dpkit-hd_spn-86625 | hd_spn | 5_2_route | 3.3 | drt_violations best 23471 last 23471 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hg_v1p2-3294731 | kv3_hg_v1p2 | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.0 h ago (535/535 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v5-3339336 | kv3_hgi_v5 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.6944 last 0.7462 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-149983 | sle_fe_v1 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (428/428 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-4021915 | sle_fe_v1 | generate_abstract | 15.5 | last meaningful line 0.4 h ago (681/681 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-3919282 | sle_hc0 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-1459492 | sle_hc1 | postcts_gate_TT | 9.1 | last meaningful line 0.2 h ago (860/860 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-3979568 | sle_hc1 | reg_fanout | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cle683a076-3970050 | slw_hc1 | synth_odb_v | 0.1 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-4112562 | slw_sc_v2 | 2_3_floorplan_tapcell | 0.1 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 26.3 |  | NO-DATA: no log found |  |
| epyc7 | otc-4029726-7913 | 4029726 | orfs_synth | 0.1 | last meaningful line 0.1 h ago (269/269 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_100942_929932-i1-3347652 | eco_20261121_100942_929932-i1 | 5_1_grt | 0.3 | last meaningful line 0.2 h ago (142/142 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_173326_4009105-i1t-1250567 | eco_20261121_173326_4009105-i1t | 5_2_route | 2.1 | last meaningful line 0.1 h ago (281/282 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_184012_3245689-i1t-2500922 | eco_20261121_184012_3245689-i1t | 5_2_route | 0.9 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_193535_3253336-i1t-4078609 | eco_20261121_193535_3253336-i1t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | clkgrt-hook_ra-3253448 | clkgrt-hook_ra | - | 0.6 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-dsdv_slice_lepe_mu_LP__t2-3534677 | dsdv_slice_lepe_mu_LP__t2 | 3_3_place_gp | 0.4 | overflow best 0.7256 last 0.7315 rows 9 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-hd_host_e-3833588 | hd_host_e | 5_2_route | 4.4 | drt_violations best 27 last 27 rows 56 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor-3733934 | kv3_io_cor | 5_2_route | 4.5 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-3818815 | kv3_io_cor_v1 | 5_2_route | 4.4 | drt_violations best 40736 last 40736 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-3274788 | serdes__t1 | 5_2_route | 8.3 | last meaningful line 0.5 h ago (286/287 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa-1023417 | sle_hc0 | 5_1_grt | 6.3 | last meaningful line 0.1 h ago (135/135 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-1899674 | slw_fe_v1 | 5_1_grt | 5.7 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-850569 | slw_fe_v1 | 5_1_grt | 6.5 | repair_TNS best 18.769 last 18.769 rows 6 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | otc-1547845-17008 | 1547845 | orfs_flow | 2.5 | repair_Viol best 93 last 93 rows 33 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 54.9 |  | NO-DATA: no log found |  |
| epyc8 | otc-3408918-8310 | 3408918 | orfs_synth | 0.5 | last meaningful line 0.5 h ago (269/269 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | otc-559540-13695 | 559540 | route | 3.6 | last meaningful line 0.1 h ago (464/464 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | so_3869222_ff_95953 | so_3869222_ff_95953 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | so_3869222_tt_95953 | so_3869222_tt_95953 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3350653 | col_h9_r1__t1 | 5_1_grt | 5.5 | repair_Viol best 140 last 140 rows 10 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-1887604 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 9.4 | repair_TNS best 1088.99 last 1088.99 rows 11 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-2618359 | hd_ctl | 6_report | 6.1 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v3n-113758 | kv3_pv_v3n | 3_5_place_dp | 4.6 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-1513640 | sle_hc0 | 5_1_grt | 6.9 | last meaningful line 0.1 h ago (1030/1047 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-1095767 | sle_su_l1 | 5_2_route | 7.2 | drt_violations best 6686 last 6686 rows 3 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-3236701 | slice_station__t52 | 6_1_fill | 8.6 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-882856 | slw_hc3 | postcts_gate_TT | 7.4 | last meaningful line -0.0 h ago (22929/22929 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | eco-abs-3447233 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.1 h ago (546/546 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | eco-abs-3541566 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.2 h ago (253/253 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-3085280-30126 | 3085280 | - | 11.4 |  | NO-DATA: no log found |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 11.4 |  | NO-DATA: no log found |  |
| epyc9 | otc-3604345-3264 | 3604345 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 11.0 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261121_070035_1645318-i1-2327283 | eco_20261121_070035_1645318-i1 | 5_2_route | 1.8 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_143815_74711-i2-3554105 | eco_20261121_143815_74711-i2 | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 0.7 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-4146127 | col_h10_r2__t1 | 5_2_route | 8.1 | drt_violations best 85869 last 85869 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | 5_2_route | 15.8 | drt_violations best 203629 last 203629 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-3714034 | coll_ftc | 5_2_route | 8.4 | drt_violations best 72742 last 72742 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-serdes__t1__clb45db5be-2382703 | serdes__t1 | tt_setup_repair_grt | 9.1 | repair_Viol best 3989 last 3989 rows 30 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | 5_2_route | 16.0 | last meaningful line 0.1 h ago (131/131 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-2204474 | slw_st_b_v1 | 5_1_grt | 9.2 | last meaningful line 0.1 h ago (179/192 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_su_c__cl92142dac-2179614 | slw_su_c | 5_1_grt | 9.2 | last meaningful line 2.0 h ago (212/221 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | prd-eco1-i1-2520913 | eco1-i1 | 5_2_route | 9.0 | last meaningful line 0.3 h ago (273/274 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | prd-eco_20261121_075836_1991905-i1t-1821063 | eco_20261121_075836_1991905-i1t | 5_2_route | 3.7 | drt_violations best 190712 last 190712 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i1t-2148021 | eco_20261121_082001_3216437-i1t | 5_2_route | 3.4 | last meaningful line 0.3 h ago (281/282 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-1358957 | coll_ftm | 5_2_route | 1.5 | last meaningful line 0.1 h ago (238/239 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-1351697 | kv3_io_ft | generate_abstract | 1.5 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | generate_abstract | 19.4 | last meaningful line 0.0 h ago (359/359 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | prd-eco_20261121_072804_212710-i1t-1822102 | eco_20261121_072804_212710-i1t | 5_2_route | 4.2 | drt_violations best 4432 last 4432 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel2 | prd-eco_20261121_111944_190475-i1-3971139 | eco_20261121_111944_190475-i1 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (142/142 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | so_4085282_ff_17496 | so_4085282_ff_17496 | signoff | 0.3 |  | NO-DATA: empty log |  |
| intel2 | so_4085282_tt_17496 | so_4085282_tt_17496 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc10 | otc-2355868-22490 | 2355868 | - | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 28.7 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-eco1-i1-100513 | eco1-i1 | 5_2_route | 8.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-4178763 | eco1-i1 | 5_1_grt | 1.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-92562 | eco1-i1 | 5_2_route | 8.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1671443 | eco1-i1t | 5_2_route | 12.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1673812 | eco1-i1t | 5_2_route | 12.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3393842 | col_h9_r0_p3__t1 | 5_2_route | 15.6 | drt_violations best 7 last 7 rows 62 | before-window best 135, window best 7 | PROGRESS: drt_violations improved 94.8 % in window |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1331394 | col_h9_r0_p6__t1 | 5_2_route | 8.9 | drt_violations best 1635 last 1641 rows 29 | before-window best 74750, window best 1635 | PROGRESS: drt_violations improved 97.8 % in window |  |
| epyc10 | dpkit-hd_lep0N-1588394 | hd_lep0N | pregrt_ff_hold | 6.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-serdes__t4-293755 | serdes__t4 | pregrt_ff_hold | 1.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_2_route | 16.4 | drt_violations best 10389 last 10389 rows 16 | before-window best 16045, window best 10389 | PROGRESS: drt_violations improved 35.3 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 32.7 | last meaningful line 0.4 h ago (1491/1491 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-hd_mesh-2472048 | hd_mesh | pregrt_ff_hold | 8.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2374083 | sle_hc1 | pregrt_ff_hold | 9.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2408517 | slw_fe_v1 | 5_1_grt | 8.9 | repair_TNS best 0 last 0 rows 20 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_sc_v2-2660942 | slw_sc_v2 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2420111 | slw_st_b_v2 | 5_1_grt | 8.9 | repair_TNS best 0 last 0 rows 16 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_su_c__cl19bb38ef-2385009 | slw_su_c | pregrt_ff_hold | 5.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | 5_2_route | 22.2 | drt_violations best 9406 last 49919 rows 18 | before-window best 10156, window best 9406 | PROGRESS: drt_violations improved 7.4 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_2_route | 18.3 | drt_violations best 9939 last 9939 rows 15 | before-window best 15697, window best 9939 | PROGRESS: drt_violations improved 36.7 % in window |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 8.6 | drt_violations best 3 last 20 rows 42 | before-window best 8867, window best 3 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve230954c-1731757 | sle_hc1 | pregrt_ff_hold | 5.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l0__cl1a1c1f8f-1472945 | slw_su_l0 | 5_2_route | 9.1 | drt_violations best 4 last 4 rows 45 | before-window best 47342, window best 4 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_2_route | 19.5 | drt_violations best 13126 last 54684 rows 18 | before-window best 14441, window best 13126 | PROGRESS: drt_violations improved 9.1 % in window |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | 5_2_route | 15.2 | drt_violations best 15 last 15 rows 50 | before-window best 8750, window best 15 | PROGRESS: drt_violations improved 99.8 % in window |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | 5_2_route | 15.2 | drt_violations best 27 last 27 rows 47 | before-window best 8873, window best 27 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc8 | dpkit-glue-504992 | glue | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3985339 | sle_hc2 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-1013642 | sle_hc2 | pregrt_ff_hold | 6.3 | repair_Violations best 0 last 0 rows 4 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-2906124 | slw_hc1 | pregrt_ff_hold | 8.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1012001 | slw_hc3 | pregrt_ff_hold | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-1012945 | slw_hc3 | pregrt_ff_hold | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2616668 | sle_hc1 | pregrt_ff_hold | 6.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_ctl__cl67434795-622153 | sle_ctl | pregrt_ff_hold | 10.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261120_192428_3309571-i1-967583 | eco_20261120_192428_3309571-i1 | 5_2_route | 7.5 | drt_violations best 9 last 9 rows 15 | before-window best 19520, window best 9 | PROGRESS: drt_violations improved 100.0 % in window |  |
