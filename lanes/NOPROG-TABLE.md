# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 10:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'GRT-LABEL': 16, 'YOUNG': 89, 'KEEP': 1, 'EXCLUDED': 3, 'PROGRESS': 29}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-dsdv_slice_lepw_mu_LP__t2-3004885 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 12.0 | grt rounds 4 overflow 5:62 -> 10:91 -> 15:25 -> 20:8 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-3946553 | ot_s81sl_leaf__t54 | 5_1_grt | 11.6 | grt rounds 3 overflow 5:43291 -> 10:27555 -> 15:25376 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-cbn_q00__cldbcda913-3330181 | cbn_q00 | 5_1_grt | 12.6 | grt rounds 6 overflow 5:11997 -> 10:8426 -> 15:4780 -> 20:1359 -> 25:485 -> 30:457 | GRT-LABEL: DESIGN-FAIL: overflow 8426 at round 10 > 1000 |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | 5_1_grt | 15.3 | grt rounds 6 overflow 5:8256 -> 10:2829 -> 15:2649 -> 20:2194 -> 25:1976 -> 30:1864 | GRT-LABEL: DESIGN-FAIL: overflow 2829 at round 10 > 1000 |  |
| intel1 | dpkit-cbn_q01__cldd6ea846-4146854 | cbn_q01 | 5_1_grt | 12.2 | grt rounds 2 overflow 5:14481 -> 10:8943 | GRT-LABEL: DESIGN-FAIL: overflow 8943 at round 10 > 1000 |  |
| intel1 | dpkit-cbx_q10__cl89936551-1999472 | cbx_q10 | 5_1_grt | 1.4 | grt rounds 2 overflow 5:1998 -> 10:1858 | GRT-LABEL: DESIGN-FAIL: overflow 1858 at round 10 > 1000 |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 135.9 | grt rounds 6 overflow 5:3621 -> 10:1409 -> 15:822 -> 20:367 -> 25:132 -> 30:21 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 135.9 | grt rounds 6 overflow 5:3459 -> 10:2012 -> 15:1178 -> 20:769 -> 25:322 -> 30:29 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 1.3 | grt rounds 2 overflow 5:34209 -> 10:21585 | GRT-LABEL: DESIGN-FAIL: overflow 21585 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3739403 | ot_s81sl_leaf__t25 | 5_1_grt | 12.4 | grt rounds 3 overflow 5:29114 -> 10:25683 -> 15:21143 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 11.8 | grt rounds 3 overflow 5:27810 -> 10:12039 -> 15:6429 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 1.3 | grt rounds 2 overflow 5:51746 -> 10:53387 | GRT-LABEL: DESIGN-FAIL: overflow 53387 at round 10 > 1000 |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 20.9 | grt rounds 3 overflow 5:49160 -> 10:43104 -> 15:40285 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 12.8 | grt rounds 2 overflow 5:46995 -> 10:41355 | GRT-LABEL: DESIGN-FAIL: overflow 41355 at round 10 > 1000 |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 12.8 | grt rounds 2 overflow 5:58470 -> 10:41949 | GRT-LABEL: DESIGN-FAIL: overflow 41949 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 7.3 | grt rounds 3 overflow 5:11862 -> 10:11192 -> 15:10179 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-4083127 | col_h10_r0_p1__t1 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (2192/2192 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2831053 | col_h10_r0_p4__t1 | tt_setup_repair_grt | 4.5 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2409529 | col_h10_r0_p4__t1 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (150/150 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3989312 | col_h10_r1__t1 | 5_1_grt | 4.3 | last meaningful line 2.0 h ago (199/223 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3973910 | col_h10_r1__t1 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (2239/2239 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2420858 | col_h10_r1__t1 | tt_setup_repair | 0.5 | repair_Viol best 197 last 197 rows 188 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv74ebbc00-4014190 | col_h10_r1__t1 | 5_1_grt | 4.3 | last meaningful line 2.0 h ago (199/224 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-2782358 | col_h10_r1__t1 | stage_odb_cap | 4.5 | last meaningful line 0.0 h ago (2337/2337 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvce76611c-3560691 | col_h10_r1__t1 | 5_1_grt | 4.4 | last meaningful line 2.0 h ago (199/225 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-3559181 | col_h10_r1__t1 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (2240/2240 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-4011286 | col_h10_r2__t1 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (2299/2299 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl8b686b3e-2806632 | col_h10_r2__t1 | stage_odb_cap | 4.5 | last meaningful line 0.0 h ago (2457/2457 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-2406768 | col_h10_r2__t1 | stage_odb_cap | 0.5 | last meaningful line 0.2 h ago (1052/1052 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4028772 | col_h9_r0_p2__t1 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (2148/2148 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p5__t1__pv35382794-4060983 | col_h9_r0_p5__t1 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (1445/1445 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4028288 | col_h9_r1__t1 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (2249/2249 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | 5_2_route | 4.5 | last meaningful line -0.0 h ago (43/43 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-3012090 | dsdv_slice_lepw_mus_LP__t2 | 5_1_grt | 12.0 | repair_Viol best 222 last 222 rows 64 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (1933/1933 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 4.5 | last meaningful line 0.0 h ago (2228/2228 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t2-4070866 | ot_s81sl_leaf__t2 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (1867/1867 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2594730 | sle_fw_v1 | 3_3_place_gp | 0.4 | overflow best 0.3389 last 0.3389 rows 2 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2604299 | sle_fw_v1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.8607 last 0.8607 rows 25 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_fw_v2__cl6740750e-2587375 | sle_fw_v2 | 3_3_place_gp | 0.4 | overflow best 0.3622 last 0.3622 rows 20 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_st_b_v2__clfde1249e-2926341 | sle_st_b_v2 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3281164 | sle_su_l1 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (343/343 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t29__clc7772371-2032336 | slice_station__t29 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (116/116 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-191709 | slw_fw_v1 | 5_2_route | 13.0 | last meaningful line 0.3 h ago (289/290 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-195673 | slw_fw_v1 | 5_2_route | 13.0 | last meaningful line 0.3 h ago (287/288 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2811301 | slw_sc_v1 | 3_3_place_gp | 0.4 | overflow best 0.3634 last 0.3635 rows 4 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-2924479 | slw_sc_v1 | 3_3_place_gp | 0.4 | overflow best 0.3662 last 0.3662 rows 2 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-3017015 | svc_lo_dsdv_svc_rs__t1 | 2_1_floorplan | 11.9 | repair_Viol best 45452 last 45452 rows 1219 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t2-2905735 | svc_lo_dsdv_svc_rs__t2 | 2_1_floorplan | 12.0 | last meaningful line 0.0 h ago (1377/1377 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1t-3763698 | eco_20261120_003409_3748726-i1t | 5_2_route | 9.4 | drt_violations best 59 last 59 rows 6 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1t-2162531 | eco_recover1120-i1t | 5_2_route | 6.5 | last meaningful line 0.1 h ago (279/280 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | so_1879836_ff_39339 | so_1879836_ff_39339 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (336/336 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | so_1879836_tt_39339 | so_1879836_tt_39339 | generate_abstract | 0.6 | last meaningful line 0.5 h ago (336/336 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | so_2464050_ff_42109 | so_2464050_ff_42109 | generate_abstract | 0.5 | last meaningful line 0.3 h ago (392/392 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | so_2464050_tt_42109 | so_2464050_tt_42109 | generate_abstract | 0.5 | last meaningful line 0.3 h ago (392/392 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | so_47441_ff_58787 | so_47441_ff_58787 | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (855/855 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_47441_tt_58787 | so_47441_tt_58787 | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (855/855 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl870de686-3269452 | cbf_q00 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00_s2-1902764 | cbf_q00_s2 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (244/244 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-2023527 | col_h10_r0_p4__t1 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (232/232 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-2094926 | col_h9_r0_p1__t1 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (209/211 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2057329 | col_h9_r0_p3__t1 | 5_1_grt | 1.4 | last meaningful line 0.1 h ago (195/208 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | 5_1_grt | 1.4 | last meaningful line 0.0 h ago (190/190 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-3202568 | col_h9_r0_p4__t1 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (435/435 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-4183728 | col_h9_r1__t1 | 5_2_route | 12.1 | drt_violations best 84302 last 84302 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-3731937 | col_h9_r1__t1 | 5_2_route | 12.4 | drt_violations best 81753 last 81753 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-1885956 | col_h9_r2__t1 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (585/585 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3341852 | col_h9_r2__t1 | 5_1_grt | 1.3 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-coll_core-1983638 | coll_core | 2_1_floorplan | 0.2 | repair_Viol best 1922 last 1922 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-control_r2-1882631 | control_r2 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (4449/4449 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3688123 | dsdv_slice_c1x_C__t5 | sdc_lint | 1.8 | last meaningful line 1.8 h ago (1/1 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-grouped_r2-3317228 | grouped_r2 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (4582/4582 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 1.3 | last meaningful line 0.5 h ago (203/208 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-2201770 | kv3_hgi_v1 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (1300/1300 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Eo-393779 | kv3_hub_Eo | tt_setup_repair | 12.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Wo-1210047 | kv3_hub_Wo | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (448/448 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (200/200 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (272/272 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-3285005 | ot_s81sl_leaf__t40 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (272/272 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | 3_4_place_resized | 1.3 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (288/288 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 12.1 | last meaningful line 0.2 h ago (167/167 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v2__cl6740750e-3309324 | sle_fw_v2 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (216/216 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-2376384 | sle_st_a_v2 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | postcts_gate_FF | 13.0 | last meaningful line 0.2 h ago (760/760 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | postcts_gate_TT | 13.3 | last meaningful line 0.2 h ago (1844/1844 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-1908466 | slw_fe_v2 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (260/260 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v2__cl8537f156-3287968 | slw_fw_v2 | 3_3_place_gp | 1.3 | overflow best 0.0991 last 0.0991 rows 42 | YOUNG: stage 0.9 h < 1 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | postcts_gate_TT | 14.0 | last meaningful line -0.0 h ago (63233/63233 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | postcts_gate_FF | 14.0 | last meaningful line 0.0 h ago (650/650 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | postcts_gate_FF | 14.4 | last meaningful line 0.2 h ago (2173/2173 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-842919 | slw_st_b_v1 | 5_1_grt | 11.8 | last meaningful line 1.7 h ago (224/1162 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2118342 | slw_st_b_v2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (361/361 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-2003277 | slw_su_l1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco_20261120_003407_1650578-i1-1677571 | eco_20261120_003407_1650578-i1 | 5_2_route | 9.4 | drt_violations best 650 last 650 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | pregrt_ff_hold | 7.1 | repair_TNS best 72075 last 72075 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | tt_setup_repair | 7.1 | repair_Violations best 3433 last 3475 rows 142 | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2391268 | kv3_hgi_v1 | 5_1_grt | 7.3 | repair_Viol best 10 last 10 rows 2 | YOUNG: evidence 6.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-1118548 | ot_s81sl_kv_leaf__t5 | 5_1_grt | 10.8 | repair_Viol best 607 last 607 rows 74 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl6740750e-482449 | sle_fw_v2 | 5_2_route | 13.3 | drt_violations best 96968 last 96968 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel2 | dpkit-svc_lo_dsdv_svc_rs__t5-448347 | svc_lo_dsdv_svc_rs__t5 | 2_1_floorplan | 13.3 | repair_Viol best 54729 last 54729 rows 1177 | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel2 | so_3859242_ff_32268 | so_3859242_ff_32268 | stage_odb_cap | 0.7 | last meaningful line 0.5 h ago (1005/1005 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | so_3859242_tt_32268 | so_3859242_tt_32268 | stage_odb_cap | 0.7 | last meaningful line 0.5 h ago (1005/1005 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 22.8 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 57.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | stage_odb_cap | 33.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | stage_odb_cap | 33.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 7.2 | last meaningful line 0.9 h ago (1371/1371 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-382185 | col_h10_r2__t1 | 5_2_route | 22.8 | drt_violations best 20 last 20 rows 51 | before-window best 43, window best 20 | PROGRESS: drt_violations improved 53.5 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-384874 | col_h10_r2__t1 | 5_2_route | 22.8 | drt_violations best 20 last 20 rows 51 | before-window best 43, window best 20 | PROGRESS: drt_violations improved 53.5 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-385072 | col_h10_r2__t1 | 5_2_route | 22.8 | drt_violations best 20 last 20 rows 51 | before-window best 43, window best 20 | PROGRESS: drt_violations improved 53.5 % in window |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | 5_1_grt | 1.3 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3191459 | col_h9_r2__t1 | 5_1_grt | 1.9 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3505370 | slice_station__t40 | 5_1_grt | 1.3 | repair_TNS best 0 last 0 rows 19 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261120_091653_2376724-i1-614277 | eco_20261120_091653_2376724-i1 | 5_1_grt | 0.7 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | prd-eco_recover1120-i1t-303123 | eco_recover1120-i1t | 5_1_grt | 6.5 | last meaningful line 5.3 h ago (249/308 lines) | PROGRESS: log still growing |  |
| intel1 | prd-eco_recover1120-i1t-319029 | eco_recover1120-i1t | 5_1_grt | 6.5 | last meaningful line 5.4 h ago (249/351 lines) | PROGRESS: log still growing |  |
| intel1 | prd-eco_recover1120-i1t-330433 | eco_recover1120-i1t | 5_1_grt | 6.5 | last meaningful line 4.1 h ago (249/322 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 20.2 | last meaningful line 0.0 h ago (1203/1203 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 15.2 | last meaningful line 0.0 h ago (924/924 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_lep0N-830501 | hd_lep0N | stage_odb_cap | 13.2 | last meaningful line 0.0 h ago (783/783 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-1602787 | hd_mesh | stage_odb_cap | 14.8 | last meaningful line 0.0 h ago (927/927 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-4092448 | hd_mesh | stage_odb_cap | 13.5 | last meaningful line 0.0 h ago (847/847 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_sys_c-480894 | kv3_sys_c | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (792/792 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t10-1107312 | ot_s81sl_leaf__t10 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (929/929 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (976/976 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t58-1113172 | ot_s81sl_leaf__t58 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (897/897 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | stage_odb_cap | 13.9 | last meaningful line 0.0 h ago (904/904 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (792/792 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (792/792 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v3-489810 | slw_fw_v3 | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (792/792 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2435819 | slw_hc1 | stage_odb_cap | 14.4 | last meaningful line 0.0 h ago (916/916 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | stage_odb_cap | 13.5 | last meaningful line 0.0 h ago (806/806 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (792/792 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-495397 | slw_st_b_v2 | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (792/792 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-498208 | slw_st_b_v2 | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (792/792 lines) | PROGRESS: log still growing |  |
