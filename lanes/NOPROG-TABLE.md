# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 10:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 4, 'CANCEL-NOW': 3, 'GRT-LABEL': 20, 'YOUNG': 95, 'NO-DATA': 17, 'EXCLUDED': 7, 'KEEP': 1, 'PROGRESS': 31}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-dsdv_slice_lepe_mu_LP__t2-3984741 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 3.3 | repair_TNS best 221214 last 221214 rows 1 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -423.28 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 26.6 | grt rounds 6 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -2893.36 ps (< -300, gate TT >= -42); job age 2 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 40.1 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 40 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-3736166 | slw_st_a_v2 | tt_setup_repair_grt | 3.2 | last meaningful line 0.0 h ago (23/23 lines) | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -322.66 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-1346125 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 5_1_grt | 0.2 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-1353027 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 3_3_place_gp | 0.2 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-1353027-lec | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | lec | 0.0 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 25.2 | grt rounds 3 overflow 5:62850 -> 10:60664 -> 15:49611 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 25.1 | grt rounds 4 overflow 5:56489 -> 10:43484 -> 15:40646 -> 20:43612 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 39.6 | grt rounds 4 overflow 5:8939 -> 10:4958 -> 15:3391 -> 20:2910 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 28.8 | grt rounds 4 overflow 5:51489 -> 10:38067 -> 15:34597 -> 20:37772 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_st_a_v1__clb036e152-4100253 | slw_st_a_v1 | 5_1_grt | 3.7 | grt rounds 2 overflow 5:576 -> 10:153 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hroot-4110897 | kv3_hroot | 5_1_grt | 2.9 | grt rounds 2 overflow 5:3253 -> 10:1440 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 13.9 | grt rounds 4 overflow 5:20011 -> 10:12763 -> 15:11530 -> 20:11080 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-kv3_hgi_v8-3224135 | kv3_hgi_v8 | 5_1_grt | 7.4 | grt rounds 2 overflow 5:51928 -> 10:23820 | GRT-LABEL: DESIGN-FAIL: overflow 23820 at round 10 > 1000 |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 26.8 | grt rounds 3 overflow 5:26517 -> 10:13378 -> 15:8965 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 37.5 | grt rounds 6 overflow 5:23729 -> 10:18456 -> 15:11846 -> 20:10134 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: overflow 18456 at round 10 > 1000 |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 37.8 | grt rounds 4 overflow 5:34987 -> 10:28632 -> 15:24645 -> 20:22699 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 5_1_grt | 14.8 | grt rounds 4 overflow 5:54170 -> 10:7759 -> 15:5295 -> 20:4273 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 20.3 | grt rounds 5 overflow 5:17839 -> 10:13501 -> 15:11502 -> 20:10666 -> 25:8529 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 15.3 | grt rounds 4 overflow 5:36131 -> 10:32007 -> 15:25602 -> 20:22194 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-serdes__t15__cla2127225-4147451 | serdes__t15 | 5_1_grt | 6.9 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 36.6 | grt rounds 3 overflow 5:56283 -> 10:53405 -> 15:50242 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | 5_1_grt | 18.0 | grt rounds 6 overflow 5:35006 -> 10:1235 -> 15:721 -> 20:1026 -> 25:797 -> 30:354 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 31.6 | grt rounds 3 overflow 5:59246 -> 10:47822 -> 15:53864 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 31.6 | grt rounds 3 overflow 5:61726 -> 10:48832 -> 15:53055 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 31.8 | grt rounds 6 overflow 5:13197 -> 10:11019 -> 15:9952 -> 20:9864 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2275786 | col_h10_r2__t1 | 5_1_grt | 1.8 | repair_Remaining best 75552 last 75552 rows 35 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-2582333 | col_h9_r0_p2__t1 | 5_2_route | 7.0 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3507811 | col_h9_r0_p2__t1 | 5_1_grt | 3.6 | last meaningful line 0.2 h ago (243/322 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1331394 | col_h9_r0_p6__t1 | 5_2_route | 7.7 | drt_violations best 1635 last 1635 rows 17 | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-1588394 | hd_lep0N | pregrt_ff_hold | 4.7 | repair_TNS best 97406.1 last 97406.1 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-hd_lep0N-22377 | hd_lep0N | 4_1_cts | 3.1 | last meaningful line 0.1 h ago (10503/10503 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-4150550 | hd_lep0N | 3_3_place_gp | 0.5 | last meaningful line 0.1 h ago (37/37 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hgi_v8-3126306 | kv3_hgi_v8 | 5_1_grt | 6.6 | last meaningful line 0.0 h ago (155/155 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t39-243585 | ot_s81sl_leaf__t39 | 4_1_cts | 0.3 | last meaningful line 0.1 h ago (72/72 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t36-3668002 | slice_station__t36 | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (4031/4031 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t36-3913104 | slice_station__t36 | 5_2_route | 3.3 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t37-173045 | slice_station__t37 | 4_1_cts | 0.3 | last meaningful line 0.0 h ago (3894/3895 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slw_fw_v3-1328903 | slw_fw_v3 | 5_1_grt | 7.7 | last meaningful line 0.1 h ago (1922/1928 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-tt_ctlm-1606453 | tt_ctlm | 5_1_grt | 7.5 | last meaningful line 0.1 h ago (197/203 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | ot-sc-coleco-615236 | ot-sc-coleco | route | 0.1 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | otc-231389-16241 | 231389 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc10 | prd-eco_20261120_233525_2680444-i3-2847283 | eco_20261120_233525_2680444-i3 | 5_2_route | 1.4 | drt_violations best 220 last 220 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_014354_2681516-i3t-1349005 | eco_20261121_014354_2681516-i3t | 5_3_fillcell | 2.3 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1t-894339 | eco_20261121_154936_3396612-i1t | 5_1_grt | 2.6 | repair_Viol best 2419 last 2419 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | so_4114438_ff_33641 | so_4114438_ff_33641 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc10 | so_4114438_tt_33641 | so_4114438_tt_33641 | signoff | 0.5 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-cbf_q00__cl870de686-3870117 | cbf_q00 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (5522/5522 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-2301911 | col_h10_r1__t1 | 5_2_route | 8.0 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-2629912 | col_h9_r0_p2__t1 | 5_2_route | 7.8 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3129306 | col_h9_r2__t1 | 5_2_route | 4.3 | drt_violations best 60767 last 60767 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v3-3867769 | kv3_hg_v3 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.1 h ago (535/535 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 2_1_floorplan | 1.9 | last meaningful line 1.3 h ago (1415/1415 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-72198 | kv3_hub_Ei | 3_5_place_dp | 3.7 | last meaningful line 0.1 h ago (115/115 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v1-1304161 | kv3_pv_v1 | 3_3_place_gp | 2.8 | overflow best 0.0998 last 0.0998 rows 41 | YOUNG: stage 0.9 h < 1 h |  |
| epyc2 | dpkit-kv3_pv_v4n-4044420 | kv3_pv_v4n | 3_3_place_gp | 3.8 | overflow best 0.0996 last 0.0996 rows 42 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v5n-4101656 | kv3_pv_v5n | 3_3_place_gp | 3.7 | overflow best 0.0988 last 0.0988 rows 42 | YOUNG: stage 1.0 h < 1 h |  |
| epyc2 | dpkit-native59-3868183 | native59 | 2_1_floorplan | 0.5 | last meaningful line 0.1 h ago (1359/1359 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | 6_report | 17.4 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | 5_2_route | 17.2 | drt_violations best 10756 last 10756 rows 2 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_c-2630248 | sle_su_c | 5_1_grt | 7.8 | last meaningful line 1.3 h ago (210/218 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | pregrt_ff_hold | 3.5 | repair_TNS best 52762.2 last 52762.2 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-2449519 | slw_hc3 | 5_1_grt | 7.9 | last meaningful line 0.1 h ago (1016/1022 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3868961 | slw_sc_v1 | 3_3_place_gp | 0.5 | overflow best 0.1633 last 0.189 rows 26 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-slw_sc_v2-2660942 | slw_sc_v2 | 4_1_cts | 1.7 | last meaningful line 0.1 h ago (4185/4185 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i3-297348 | eco_20261120_134605_3273412-i3 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i2t-2328774 | eco_20261120_170022_4017640-i2t | 5_2_route | 4.9 | drt_violations best 2948 last 2948 rows 5 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_070700_2142563-i1t-551142 | eco_20261121_070700_2142563-i1t | 5_2_route | 3.3 | drt_violations best 7883 last 7883 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_080323_3018643-i1t-1786242 | eco_20261121_080323_3018643-i1t | 5_2_route | 2.4 | last meaningful line 0.2 h ago (273/274 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_102155_957464-i1t-245136 | eco_20261121_102155_957464-i1t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i2-3115487 | eco_recover1120-i2 | 5_2_route | 4.3 | drt_violations best 22 last 22 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | so_208376_ff_3411 | so_208376_ff_3411 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_208376_tt_3411 | so_208376_tt_3411 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_54805_ff_38281 | so_54805_ff_38281 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc2 | so_54805_tt_38281 | so_54805_tt_38281 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc8 | clkgrt-base-940398 | clkgrt-base | - | 2.0 |  | NO-DATA: no log found |  |
| epyc8 | clkgrt-clkfirst_seg-2522552 | clkgrt-clkfirst_seg | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | clkgrt-hook-2522447 | clkgrt-hook | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | clkgrt-hook_seg-2522660 | clkgrt-hook_seg | - | 0.1 |  | NO-DATA: no log found |  |
| epyc8 | clkgrt-resaware-943509 | clkgrt-resaware | - | 2.0 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-cbx_q10__cl89936551_h-1010361 | cbx_q10 | pregrt_ff_hold | 5.1 | repair_Violations best 81394 last 81394 rows 117 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_c1x_C__t9-950441 | dsdv_slice_c1x_C__t9 | 4_1_cts | 5.1 | last meaningful line 0.1 h ago (3205/3205 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-glue-504992 | glue | pregrt_ff_hold | 2.4 | repair_TNS best 5552.06 last 5552.06 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-hd_host_e-3833588 | hd_host_e | 5_2_route | 3.1 | drt_violations best 27 last 27 rows 31 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hgi_v2__cl2862d491-3732038 | kv3_hgi_v2 | 5_1_grt | 3.2 | last meaningful line 0.3 h ago (206/213 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor-3733934 | kv3_io_cor | postcts_gate_FF | 3.2 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_io_cor_v1-3818815 | kv3_io_cor_v1 | 5_2_route | 3.1 | last meaningful line 0.0 h ago (243/243 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-3274788 | serdes__t1 | 5_2_route | 7.1 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t40__clc8fb2c8c-1220503 | slice_station__t40 | 5_2_route | 4.9 | drt_violations best 17073 last 17073 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-850569 | slw_fe_v1 | 5_1_grt | 5.2 | last meaningful line 0.1 h ago (186/189 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | otc-1547845-17008 | 1547845 | orfs_flow | 1.2 | repair_Viol best 93 last 93 rows 33 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | otc-1687286-17300 | 1687286 | orfs_synth | 1.0 | last meaningful line 1.0 h ago (269/269 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 53.7 |  | NO-DATA: no log found |  |
| epyc8 | otc-559540-13695 | 559540 | - | 2.3 |  | NO-DATA: no log found |  |
| epyc8 | prd-fin-2046754 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-3350653 | col_h9_r1__t1 | 5_1_grt | 4.2 | repair_TNS best 2320.32 last 2320.32 rows 4 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-1887604 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 8.2 | last meaningful line 0.0 h ago (197/200 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-2618359 | hd_ctl | 5_2_route | 4.8 | last meaningful line 0.0 h ago (246/247 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-kv3_hgi_v2__cle0015330-660102 | kv3_hgi_v2 | 5_1_grt | 2.8 | last meaningful line 0.5 h ago (206/215 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v3n-113758 | kv3_pv_v3n | 3_4_place_resized | 3.4 | last meaningful line 0.2 h ago (788/788 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_ctl__cla4f6f12f-492382 | sle_ctl | 5_1_grt | 6.4 | repair_Viol best 671 last 671 rows 70 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-1513640 | sle_hc0 | pregrt_ff_hold | 5.7 | last meaningful line 0.0 h ago (63/63 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-1095767 | sle_su_l1 | 5_2_route | 6.0 | last meaningful line 0.1 h ago (273/274 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t52-3236701 | slice_station__t52 | 5_2_route | 7.4 | drt_violations best 32044 last 32044 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | generate_abstract | 18.9 | last meaningful line 0.2 h ago (862/862 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-882856 | slw_hc3 | 5_1_grt | 6.1 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | eco-abs-2693292 | eco-abs | generate_abstract | 0.1 | last meaningful line 0.0 h ago (551/551 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-3085280-30126 | 3085280 | - | 10.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 10.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 9.8 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261121_070035_1645318-i1-2327283 | eco_20261121_070035_1645318-i1 | 5_2_route | 0.6 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_125224_4071554-i1-1728728 | eco_20261121_125224_4071554-i1 | 5_2_route | 1.4 | last meaningful line 0.2 h ago (260/261 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_154823_2000128-i1-767217 | eco_20261121_154823_2000128-i1 | 5_2_route | 2.7 | drt_violations best 1166 last 1166 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-4146127 | col_h10_r2__t1 | 5_2_route | 6.9 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | 5_2_route | 14.6 | drt_violations best 203629 last 203629 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel1 | dpkit-coll_ftc-3714034 | coll_ftc | 5_2_route | 7.1 | last meaningful line 0.2 h ago (262/263 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg-2345328 | kv3_hg | 3_5_place_dp | 1.9 | last meaningful line 0.3 h ago (44/44 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-622153 | sle_ctl | pregrt_ff_hold | 9.0 | repair_TNS best 27573.4 last 27573.4 rows 1 | YOUNG: stage 1.0 h < 1 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | postcts_gate_TT | 14.8 | last meaningful line -0.0 h ago (72906/72906 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v2__cl55be2264-2229034 | sle_stm_v2 | 5_1_grt | 7.9 | last meaningful line 0.1 h ago (1036/1042 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-slw_su_c__cl92142dac-2179614 | slw_su_c | 5_1_grt | 7.9 | last meaningful line 0.8 h ago (212/218 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | prd-eco1-i1-2520913 | eco1-i1 | 5_2_route | 7.7 | last meaningful line 0.0 h ago (264/264 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i1-967583 | eco_20261120_192428_3309571-i1 | 5_2_route | 6.2 | drt_violations best 5261 last 5261 rows 9 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | prd-eco_20261121_075836_1991905-i1t-1821063 | eco_20261121_075836_1991905-i1t | 5_2_route | 2.5 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i1t-2148021 | eco_20261121_082001_3216437-i1t | 5_2_route | 2.1 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | dpkit-cbn_q01__clab6e67f2-34160 | cbn_q01 | 3_3_place_gp | 0.8 | overflow best 0.4182 last 0.4271 rows 22 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-coll_core-1327906 | coll_core | 2_1_floorplan | 0.2 | repair_Viol best 1923 last 1923 rows 1128 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-coll_ftm-1358957 | coll_ftm | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (116/116 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-1350127 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (214/215 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | 6_report | 18.1 | last meaningful line 0.0 h ago (600/600 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | 5_2_route | 18.1 | drt_violations best 95394 last 95394 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-1380090 | slice_station__t12 | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (148/160 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | 6_report | 18.1 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | 6_1_fill | 18.1 | last meaningful line 0.0 h ago (13/13 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | eco-abs-1118126 | eco-abs | generate_abstract | 0.4 | last meaningful line 0.3 h ago (1028/1028 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | prd-eco_20261121_072804_212710-i1t-1822102 | eco_20261121_072804_212710-i1t | 5_2_route | 3.0 | drt_violations best 4432 last 4432 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel2 | so_1088173_ff_47547 | so_1088173_ff_47547 | generate_abstract | 0.5 | last meaningful line 0.3 h ago (1007/1007 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | so_1088173_tt_47547 | so_1088173_tt_47547 | generate_abstract | 0.5 | last meaningful line 0.3 h ago (1007/1007 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | otc-210535-29818 | 210535 | asbuilt.yosys | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | otc-567114-21483 | 567114 | asbuilt.yosys | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 27.4 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-eco1-i1-100513 | eco1-i1 | 5_1_grt | 6.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1-92562 | eco1-i1 | 5_2_route | 6.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1671443 | eco1-i1t | 5_2_route | 11.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-eco1-i1t-1673812 | eco1-i1t | 5_2_route | 11.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-fin-1664760 | fin | 6_report | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3401748 | col_h9_r0_p2__t1 | 5_2_route | 14.3 | drt_violations best 29440 last 29440 rows 8 | before-window best 211425, window best 29440 | PROGRESS: drt_violations improved 86.1 % in window |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3393842 | col_h9_r0_p3__t1 | 5_2_route | 14.3 | drt_violations best 48 last 48 rows 13 | before-window best 196822, window best 48 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc10 | dpkit-serdes__t4-293755 | serdes__t4 | 4_1_cts | 0.3 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_2_route | 15.1 | drt_violations best 10756 last 10756 rows 15 | before-window best 18123, window best 10756 | PROGRESS: drt_violations improved 40.7 % in window |  |
| epyc10 | tg2130-gen-281350 | tg2130-gen | tg_cts | 0.3 | repair_Violations best 0 last 0 rows 3 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 31.7 | last meaningful line 0.6 h ago (1489/1489 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-hd_mesh-2472048 | hd_mesh | pregrt_ff_hold | 7.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | 5_2_route | 17.3 | drt_violations best 0 last 0 rows 8 | PROGRESS: drt_violations reached 0 |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2374083 | sle_hc1 | pregrt_ff_hold | 8.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slice_station__t36-3125329 | slice_station__t36 | 5_1_grt | 4.3 | repair_TNS best 0 last 0 rows 19 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2408517 | slw_fe_v1 | 5_1_grt | 7.9 | repair_TNS best 0 last 0 rows 7 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2420111 | slw_st_b_v2 | 5_1_grt | 7.9 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_su_c__cl19bb38ef-2385009 | slw_su_c | pregrt_ff_hold | 4.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | 5_2_route | 21.2 | drt_violations best 9406 last 49919 rows 18 | before-window best 10156, window best 9406 | PROGRESS: drt_violations improved 7.4 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_2_route | 17.3 | drt_violations best 10277 last 10277 rows 14 | before-window best 17797, window best 10277 | PROGRESS: drt_violations improved 42.3 % in window |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 7.6 | drt_violations best 3 last 30 rows 37 | before-window best 8867, window best 3 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | 5_2_route | 13.9 | drt_violations best 15 last 15 rows 50 | before-window best 100396, window best 15 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | 5_2_route | 13.9 | drt_violations best 29 last 35 rows 42 | before-window best 99683, window best 29 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc8 | dpkit-dsdv_slice_lepe_mu_LP__t2-4122597 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa-1023417 | sle_hc0 | pregrt_ff_hold | 5.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3985339 | sle_hc2 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-1013642 | sle_hc2 | pregrt_ff_hold | 5.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slice_station__t51-719348 | slice_station__t51 | 5_1_grt | 5.3 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-1899674 | slw_fe_v1 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-2906124 | slw_hc1 | pregrt_ff_hold | 7.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_hc3__clccfc3e6b__pv39aac7a1-1012001 | slw_hc3 | pregrt_ff_hold | 5.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_hc3__cld86a7ad4__pv6c2c33ed-1012945 | slw_hc3 | pregrt_ff_hold | 5.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2616668 | sle_hc1 | pregrt_ff_hold | 4.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-serdes__t1__clb45db5be-2382703 | serdes__t1 | 5_1_grt | 7.8 | repair_TNS best 0 last 0 rows 4 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-2204474 | slw_st_b_v1 | pregrt_ff_hold | 7.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-kv3_io_ft-1351697 | kv3_io_ft | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
