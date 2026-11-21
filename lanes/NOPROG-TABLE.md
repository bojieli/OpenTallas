# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 11:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 5, 'CANCEL-NOW': 2, 'GRT-LABEL': 30, 'YOUNG': 96, 'NO-DATA': 19, 'EXCLUDED': 6, 'KEEP': 1, 'PROGRESS': 34}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984741 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -423.28 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 27.1 | grt rounds 6 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -2893.36 ps (< -300, gate TT >= -42); job age 2 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 40.6 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 40 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc7 | dpkit-cbf_q11-283336 | cbf_q11 | 5_1_grt | 14.5 | grt rounds 6 overflow 5:6375 -> 10:5827 -> 15:5482 -> 20:5460 -> 25:8886 -> 30:7683 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -675.23 ps (< -300, gate TT >= -42); job age 14 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc8 | dpkit-dsdv_slice_lepe_mu_LP__t2-4122597 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 3.4 | repair_TNS best 0 last 0 rows 1 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -369.28 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-2627365 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 5_1_grt | 0.2 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-1353027 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | hold_gate | 0.7 |  | CANCEL-NOW: HBM is parked | CANCELLED |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 25.7 | grt rounds 3 overflow 5:62850 -> 10:60664 -> 15:49611 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 25.6 | grt rounds 4 overflow 5:56489 -> 10:43484 -> 15:40646 -> 20:43612 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 40.1 | grt rounds 4 overflow 5:9510 -> 10:4958 -> 15:3391 -> 20:2910 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 29.3 | grt rounds 4 overflow 5:51489 -> 10:38067 -> 15:34597 -> 20:37772 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_su_c-2630248 | sle_su_c | 5_1_grt | 8.3 | grt rounds 2 overflow 5:38588 -> 10:37924 | GRT-LABEL: DESIGN-FAIL: overflow 37924 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 19.2 | grt rounds 3 overflow 5:77963 -> 10:75300 -> 15:58855 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 24.2 | grt rounds 3 overflow 5:61289 -> 10:67332 -> 15:79226 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 13.6 | grt rounds 3 overflow 5:50395 -> 10:49359 -> 15:39905 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 13.6 | grt rounds 3 overflow 5:50865 -> 10:49068 -> 15:39498 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 23.3 | grt rounds 3 overflow 5:46870 -> 10:49482 -> 15:43296 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 11.0 | grt rounds 3 overflow 5:78427 -> 10:75752 -> 15:54687 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 19.3 | grt rounds 3 overflow 5:71545 -> 10:71003 -> 15:50882 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 13.1 | grt rounds 3 overflow 5:77758 -> 10:70141 -> 15:51022 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 14.8 | grt rounds 4 overflow 5:42922 -> 10:38638 -> 15:36674 -> 20:37813 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 14.8 | grt rounds 4 overflow 5:41833 -> 10:37631 -> 15:32951 -> 20:32437 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hgi_v2__cl2862d491-3732038 | kv3_hgi_v2 | 5_1_grt | 3.7 | grt rounds 2 overflow 5:72991 -> 10:37675 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hroot-4110897 | kv3_hroot | 5_1_grt | 3.4 | grt rounds 2 overflow 5:3253 -> 10:1440 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 14.4 | grt rounds 4 overflow 5:20011 -> 10:12763 -> 15:11530 -> 20:10671 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hgi_v2__cle0015330-660102 | kv3_hgi_v2 | 5_1_grt | 3.3 | grt rounds 2 overflow 5:59354 -> 10:37389 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hgi_v8-3224135 | kv3_hgi_v8 | 5_1_grt | 7.9 | grt rounds 2 overflow 5:51928 -> 10:23820 | GRT-LABEL: DESIGN-FAIL: overflow 23820 at round 10 > 1000 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 27.3 | grt rounds 3 overflow 5:26517 -> 10:13016 -> 15:8965 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 38.0 | grt rounds 6 overflow 5:23729 -> 10:21694 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: overflow 21694 at round 10 > 1000 |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 38.3 | grt rounds 4 overflow 5:34987 -> 10:28632 -> 15:24645 -> 20:22699 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 5_1_grt | 15.3 | grt rounds 4 overflow 5:54170 -> 10:7759 -> 15:5073 -> 20:4273 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 20.8 | grt rounds 5 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 15.8 | grt rounds 4 overflow 5:36131 -> 10:32007 -> 15:25602 -> 20:22194 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 37.1 | grt rounds 3 overflow 5:56283 -> 10:53405 -> 15:50242 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 32.1 | grt rounds 3 overflow 5:59246 -> 10:47822 -> 15:53864 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 32.1 | grt rounds 3 overflow 5:60515 -> 10:48832 -> 15:53055 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 32.3 | grt rounds 6 overflow 5:13197 -> 10:11019 -> 15:9952 -> 20:9864 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2275786 | col_h10_r2__t1 | 5_1_grt | 2.3 | last meaningful line 0.6 h ago (326/1279 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-2582333 | col_h9_r0_p2__t1 | 5_2_route | 7.5 | last meaningful line 0.3 h ago (277/278 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3507811 | col_h9_r0_p2__t1 | 5_1_grt | 4.1 | last meaningful line 0.1 h ago (474/503 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1331394 | col_h9_r0_p6__t1 | 5_2_route | 8.2 | drt_violations best 1635 last 1637 rows 22 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-1588394 | hd_lep0N | pregrt_ff_hold | 5.2 | repair_TNS best 97406.1 last 97406.1 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc10 | dpkit-hd_lep0N-22377 | hd_lep0N | 4_1_cts | 3.6 | last meaningful line 0.2 h ago (10534/10534 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-4150550 | hd_lep0N | 3_3_place_gp | 1.0 | last meaningful line 0.3 h ago (179/179 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v8-3126306 | kv3_hgi_v8 | 5_1_grt | 7.1 | last meaningful line 0.3 h ago (208/210 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t39-243585 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 0.8 | last meaningful line -0.0 h ago (40/40 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t36-3668002 | slice_station__t36 | tt_setup_repair | 1.3 | last meaningful line 0.0 h ago (338/339 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t36-3913104 | slice_station__t36 | 5_2_route | 3.8 | last meaningful line 0.3 h ago (273/274 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t37-173045 | slice_station__t37 | 4_1_cts | 0.8 | last meaningful line 0.0 h ago (4007/4007 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v3-1328903 | slw_fw_v3 | postcts_gate_FF | 8.2 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | ot-sc-coleco-615236 | ot-sc-coleco | route | 0.6 | last meaningful line 0.1 h ago (392/392 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_233525_2680444-i3-2847283 | eco_20261120_233525_2680444-i3 | 5_2_route | 1.9 | drt_violations best 220 last 220 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_014354_2681516-i3-1261179 | eco_20261121_014354_2681516-i3 | 5_1_grt | 0.2 | last meaningful line 0.2 h ago (240/725 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1t-894339 | eco_20261121_154936_3396612-i1t | 5_1_grt | 3.1 | repair_Viol best 2419 last 2419 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_184648_4039100-i1t-1413255 | eco_20261121_184648_4039100-i1t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl870de686-3870117 | cbf_q00 | pregrt_ff_hold | 1.0 | repair_TNS best 4.18571e+06 last 4.18571e+06 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-2301911 | col_h10_r1__t1 | 5_2_route | 8.5 | drt_violations best 91969 last 91969 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-2629912 | col_h9_r0_p2__t1 | 5_2_route | 8.3 | last meaningful line 0.2 h ago (277/278 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3129306 | col_h9_r2__t1 | 5_2_route | 4.8 | drt_violations best 60767 last 60767 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v3-3867769 | kv3_hg_v3 | 3_3_place_gp | 1.0 | overflow best 0.6502 last 0.6502 rows 23 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 2_1_floorplan | 2.4 | last meaningful line 1.8 h ago (1415/1415 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-72198 | kv3_hub_Ei | 3_5_place_dp | 4.2 | last meaningful line 0.5 h ago (115/115 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v1-1304161 | kv3_pv_v1 | 3_4_place_resized | 3.3 | last meaningful line 0.2 h ago (642/642 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4n-4044420 | kv3_pv_v4n | 3_4_place_resized | 4.3 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v5n-4101656 | kv3_pv_v5n | 3_3_place_gp | 4.2 | overflow best 0.0988 last 0.0988 rows 42 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-native59-3868183 | native59 | 3_3_place_gp | 1.0 | overflow best 0.2979 last 0.4282 rows 83 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | generate_abstract | 17.9 | last meaningful line 0.0 h ago (1029/1029 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | 6_report | 17.8 | last meaningful line 0.2 h ago (982/982 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2408517 | slw_fe_v1 | 5_1_grt | 8.4 | last meaningful line 1.5 h ago (269/1500 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2449519 | slw_hc3 | postcts_gate_TT | 8.4 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3868961 | slw_sc_v1 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-559152-16703 | 559152 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261120_134605_3273412-i3-297348 | eco_20261120_134605_3273412-i3 | 5_1_grt | 0.6 | last meaningful line 0.3 h ago (236/1394 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i2t-2328774 | eco_20261120_170022_4017640-i2t | 5_2_route | 5.4 | drt_violations best 1667 last 1667 rows 8 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_070700_2142563-i1t-551142 | eco_20261121_070700_2142563-i1t | 5_2_route | 3.8 | drt_violations best 7883 last 7883 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_080323_3018643-i1t-1786242 | eco_20261121_080323_3018643-i1t | 5_2_route | 2.9 | last meaningful line 0.1 h ago (281/282 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_102155_957464-i1t-245136 | eco_20261121_102155_957464-i1t | 5_1_grt | 0.6 | last meaningful line 0.1 h ago (233/256 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_105744_956410-i1t-1036390 | eco_20261121_105744_956410-i1t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i2-3115487 | eco_recover1120-i2 | 5_2_route | 4.8 | drt_violations best 22 last 22 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-993515 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 1.6 | repair_TNS best 221121 last 221121 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-hd_spn-86625 | hd_spn | 5_2_route | 2.5 | last meaningful line 0.1 h ago (261/262 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_io_cor_v1-2072739 | kv3_io_cor_v1 | 5_2_route | 4.4 | drt_violations best 6 last 7 rows 31 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-4021915 | sle_fe_v1 | 6_report | 14.8 | last meaningful line 0.1 h ago (721/721 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-1459492 | sle_hc1 | postcts_gate_TT | 8.4 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l0__cl1a1c1f8f-1472945 | slw_su_l0 | 5_2_route | 8.4 | drt_violations best 4 last 4 rows 45 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 25.6 |  | NO-DATA: no log found |  |
| epyc7 | prd-count-p1_tc-881383 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (1051/1051 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_173326_4009105-i1t-1250567 | eco_20261121_173326_4009105-i1t | 5_2_route | 1.4 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_184012_3245689-i1t-2500922 | eco_20261121_184012_3245689-i1t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | r6pinq-2818127 | r6pinq | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | so_2696616_ff_76693 | so_2696616_ff_76693 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | so_2696616_tt_76693 | so_2696616_tt_76693 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc8 | clkgrt-base-940398 | clkgrt-base | - | 2.5 |  | NO-DATA: no log found |  |
| epyc8 | clkgrt-hook-2522447 | clkgrt-hook | - | 0.6 |  | NO-DATA: no log found |  |
| epyc8 | clkgrt-resaware-943509 | clkgrt-resaware | - | 2.5 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-cbx_q10__cl89936551_h-1010361 | cbx_q10 | 5_1_grt | 5.6 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t9-950441 | dsdv_slice_c1x_C__t9 | 4_1_cts | 5.6 | last meaningful line 0.0 h ago (3286/3286 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-glue-504992 | glue | pregrt_ff_hold | 2.9 | last meaningful line 0.1 h ago (42/42 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-hd_host_e-3833588 | hd_host_e | 5_2_route | 3.6 | drt_violations best 27 last 27 rows 56 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor-3733934 | kv3_io_cor | 5_2_route | 3.7 | last meaningful line 0.0 h ago (247/247 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-3818815 | kv3_io_cor_v1 | 5_2_route | 3.6 | last meaningful line 0.1 h ago (254/255 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-3274788 | serdes__t1 | 5_2_route | 7.6 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t40__clc8fb2c8c-1220503 | slice_station__t40 | 5_2_route | 5.4 | drt_violations best 17073 last 17073 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t51-719348 | slice_station__t51 | postcts_gate_TT | 5.8 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-850569 | slw_fe_v1 | 5_1_grt | 5.7 | repair_Remaining best 227403 last 227403 rows 169 | YOUNG: stage 1.0 h < 1 h |  |
| epyc8 | otc-1547845-17008 | 1547845 | orfs_flow | 1.7 | repair_Viol best 93 last 93 rows 33 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 54.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-3061540-13986 | 3061540 | gate.ys | 0.1 | last meaningful line 0.1 h ago (13956/13956 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-559540-13695 | 559540 | - | 2.8 |  | NO-DATA: no log found |  |
| epyc8 | so_3127883_ff_11247 | so_3127883_ff_11247 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (197/197 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | so_3127883_tt_11247 | so_3127883_tt_11247 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (197/197 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3350653 | col_h9_r1__t1 | 5_1_grt | 4.7 | repair_TNS best 89.882 last 89.882 rows 4 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-1887604 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 8.7 | repair_TNS best 2514 last 2514 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc9 | dpkit-hd_ctl-2618359 | hd_ctl | 5_2_route | 5.3 | drt_violations best 55830 last 55830 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v3n-113758 | kv3_pv_v3n | 3_5_place_dp | 3.9 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-492382 | sle_ctl | 5_1_grt | 6.9 | repair_Viol best 671 last 671 rows 136 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-1513640 | sle_hc0 | 5_1_grt | 6.2 | last meaningful line 0.0 h ago (186/187 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-1095767 | sle_su_l1 | 5_2_route | 6.5 | drt_violations best 69790 last 69790 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-3236701 | slice_station__t52 | 5_2_route | 7.9 | drt_violations best 32044 last 32044 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | eco-abs-2693292 | eco-abs | generate_abstract | 0.6 | last meaningful line 0.2 h ago (553/553 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | otc-3085280-30126 | 3085280 | - | 10.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 10.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 10.3 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261121_070035_1645318-i1-2327283 | eco_20261121_070035_1645318-i1 | 5_2_route | 1.1 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_125224_4071554-i1-1728728 | eco_20261121_125224_4071554-i1 | 5_2_route | 1.9 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_154823_2000128-i1-767217 | eco_20261121_154823_2000128-i1 | 5_2_route | 3.2 | drt_violations best 2 last 2 rows 5 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | so_2842391_ff_87706 | so_2842391_ff_87706 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc9 | so_2842391_tt_87706 | so_2842391_tt_87706 | - | 0.4 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-4146127 | col_h10_r2__t1 | 5_2_route | 7.4 | last meaningful line 0.4 h ago (274/275 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | 5_2_route | 15.1 | drt_violations best 203629 last 203629 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-3714034 | coll_ftc | 5_2_route | 7.6 | last meaningful line 0.2 h ago (268/269 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | postcts_gate_FF | 15.3 | last meaningful line 0.0 h ago (1180/1180 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v2__cl55be2264-2229034 | sle_stm_v2 | postcts_gate_FF | 8.4 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-2204474 | slw_st_b_v1 | 5_1_grt | 8.4 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_su_c__cl92142dac-2179614 | slw_su_c | 5_1_grt | 8.4 | last meaningful line 1.3 h ago (212/219 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | prd-eco1-i1-2520913 | eco1-i1 | 5_2_route | 8.2 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | prd-eco_20261121_075836_1991905-i1t-1821063 | eco_20261121_075836_1991905-i1t | 5_2_route | 3.0 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i1t-2148021 | eco_20261121_082001_3216437-i1t | 5_2_route | 2.6 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel2 | dpkit-cbn_q01__clab6e67f2-34160 | cbn_q01 | 3_4_place_resized | 1.3 | last meaningful line 0.3 h ago (20/20 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-1358957 | coll_ftm | 5_1_grt | 0.7 | repair_TNS best 17.138 last 17.138 rows 6 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-2632676 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (206/207 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-1351697 | kv3_io_ft | 5_2_route | 0.7 | last meaningful line 0.0 h ago (214/215 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | 5_2_route | 18.6 | drt_violations best 9079 last 9079 rows 3 | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-1380090 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (225/226 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | generate_abstract | 18.6 | last meaningful line 0.1 h ago (613/613 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | prd-eco_20261121_072804_212710-i1t-1822102 | eco_20261121_072804_212710-i1t | 5_2_route | 3.5 | drt_violations best 4432 last 4432 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel2 | so_2497855_ff_60135 | so_2497855_ff_60135 | signoff | 0.3 |  | NO-DATA: empty log |  |
| intel2 | so_2497855_tt_60135 | so_2497855_tt_60135 | signoff | 0.3 |  | NO-DATA: empty log |  |
| intel2 | so_3425470_ff_36958 | so_3425470_ff_36958 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_3425470_tt_36958 | so_3425470_tt_36958 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_3455588_ff_69266 | so_3455588_ff_69266 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (1034/1034 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | so_3455588_tt_69266 | so_3455588_tt_69266 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (1034/1034 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-1651090-11429 | 1651090 | asbuilt.yosys | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 27.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-eco1-i1-100513 | eco1-i1 | 5_2_route | 7.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-4178763 | eco1-i1 | 5_1_grt | 0.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-92562 | eco1-i1 | 5_2_route | 7.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1671443 | eco1-i1t | 5_2_route | 11.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1673812 | eco1-i1t | 5_2_route | 11.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3401748 | col_h9_r0_p2__t1 | 5_2_route | 14.8 | drt_violations best 28640 last 28640 rows 9 | before-window best 211425, window best 28640 | PROGRESS: drt_violations improved 86.5 % in window |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3393842 | col_h9_r0_p3__t1 | 5_2_route | 14.9 | drt_violations best 14 last 15 rows 36 | before-window best 196822, window best 14 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc10 | dpkit-serdes__t4-293755 | serdes__t4 | 4_1_cts | 0.8 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_2_route | 15.6 | drt_violations best 10756 last 10756 rows 15 | before-window best 17057, window best 10756 | PROGRESS: drt_violations improved 36.9 % in window |  |
| epyc10 | dpkit-tt_ctlm-1606453 | tt_ctlm | 5_1_grt | 8.0 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 32.2 | last meaningful line 1.1 h ago (1489/1489 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-hd_mesh-2472048 | hd_mesh | pregrt_ff_hold | 8.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2374083 | sle_hc1 | pregrt_ff_hold | 8.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | 5_2_route | 17.7 | drt_violations best 0 last 0 rows 8 | PROGRESS: drt_violations reached 0 |  |
| epyc2 | dpkit-slice_station__t36-3125329 | slice_station__t36 | 5_1_grt | 4.8 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | pregrt_ff_hold | 4.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_sc_v2-2660942 | slw_sc_v2 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2420111 | slw_st_b_v2 | 5_1_grt | 8.4 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_su_c__cl19bb38ef-2385009 | slw_su_c | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | 5_2_route | 21.7 | drt_violations best 9406 last 49919 rows 18 | before-window best 10156, window best 9406 | PROGRESS: drt_violations improved 7.4 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_2_route | 17.8 | drt_violations best 9939 last 9939 rows 15 | before-window best 16539, window best 9939 | PROGRESS: drt_violations improved 39.9 % in window |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 8.1 | drt_violations best 3 last 20 rows 42 | before-window best 8867, window best 3 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve230954c-1731757 | sle_hc1 | pregrt_ff_hold | 4.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_2_route | 18.7 | drt_violations best 13155 last 13155 rows 16 | before-window best 14441, window best 13155 | PROGRESS: drt_violations improved 8.9 % in window |  |
| epyc7 | tg2130-v8c_conv-3155764 | tg2130-v8c_conv | 4_1_cts | 12.7 | repair_Violations best 0 last 0 rows 32 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | 5_2_route | 14.4 | drt_violations best 15 last 15 rows 50 | before-window best 100396, window best 15 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | 5_2_route | 14.4 | drt_violations best 29 last 29 rows 44 | before-window best 99683, window best 29 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa-1023417 | sle_hc0 | pregrt_ff_hold | 5.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3985339 | sle_hc2 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-1013642 | sle_hc2 | pregrt_ff_hold | 5.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-1899674 | slw_fe_v1 | pregrt_ff_hold | 5.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-2906124 | slw_hc1 | pregrt_ff_hold | 7.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1012001 | slw_hc3 | pregrt_ff_hold | 5.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-1012945 | slw_hc3 | pregrt_ff_hold | 5.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2616668 | sle_hc1 | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-882856 | slw_hc3 | 5_1_grt | 6.6 | repair_TNS best 0 last 0 rows 2 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-serdes__t1__clb45db5be-2382703 | serdes__t1 | 5_1_grt | 8.3 | repair_TNS best 0 last 0 rows 16 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_ctl__cl67434795-622153 | sle_ctl | pregrt_ff_hold | 9.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261120_192428_3309571-i1-967583 | eco_20261120_192428_3309571-i1 | 5_2_route | 6.7 | drt_violations best 4784 last 4784 rows 10 | before-window best 19520, window best 4784 | PROGRESS: drt_violations improved 75.5 % in window |  |
