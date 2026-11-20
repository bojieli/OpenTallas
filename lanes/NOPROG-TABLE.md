# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 08:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 4, 'GRT-LABEL': 16, 'YOUNG': 84, 'NO-DATA': 2, 'KEEP': 2, 'EXCLUDED': 8, 'PROGRESS': 36}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2997578 | slw_sc_v1 | 5_2_route | 14.5 | drt_violations best 146550 last 146550 rows 1 | before-window best 146550, window best 146550 | NO-PROGRESS: drt_violations best 146550 vs 146550 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2896534 | col_h10_r2__t1 | 5_2_route | 11.3 | drt_violations best 80992 last 80992 rows 1 | before-window best 80992, window best 80992 | NO-PROGRESS: drt_violations best 80992 vs 80992 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-2901316 | col_h9_r2__t1 | 5_2_route | 11.3 | drt_violations best 62999 last 62999 rows 1 | before-window best 62999, window best 62999 | NO-PROGRESS: drt_violations best 62999 vs 62999 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | prd-eco_20261120_003409_1651933-i1t-1681241 | eco_20261120_003409_1651933-i1t | 5_1_grt | 7.9 | last meaningful line 6.5 h ago (244/275 lines) | NO-PROGRESS: no new non-iteration log line for 6.5 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-dsdv_slice_lepw_mu_LP__t2-3004885 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 10.5 | grt rounds 4 overflow 5:62 -> 10:91 -> 15:25 -> 20:8 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | 5_1_grt | 3.0 | grt rounds 3 overflow 5:11189 -> 10:21600 -> 15:18120 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-502720 | ot_s81sl_leaf__t34 | 5_1_grt | 21.3 | grt rounds 5 overflow 5:39901 -> 10:35125 -> 15:32751 -> 20:33130 -> 25:38341 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-517470 | ot_s81sl_leaf__t4 | 5_1_grt | 21.3 | grt rounds 4 overflow 5:35892 -> 10:23163 -> 15:21368 -> 20:20290 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-3946553 | ot_s81sl_leaf__t54 | 5_1_grt | 10.1 | grt rounds 3 overflow 5:42877 -> 10:27534 -> 15:25376 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-col_h10_r1__t1__cld01bb4ae-2998457 | col_h10_r1__t1 | 5_1_grt | 19.4 | grt rounds 5 overflow 5:49459 -> 10:15428 -> 15:4782 -> 20:3247 -> 25:3339 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-coll_core-532020 | coll_core | 5_1_grt | 17.6 | grt rounds 4 overflow 5:40992 -> 10:31129 -> 15:29680 -> 20:30528 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-cbn_q00__cldbcda913-3330181 | cbn_q00 | 5_1_grt | 11.1 | grt rounds 6 overflow 5:11997 -> 10:8426 -> 15:4780 -> 20:1359 -> 25:485 -> 30:457 | GRT-LABEL: DESIGN-FAIL: overflow 8426 at round 10 > 1000 |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | 5_1_grt | 13.8 | grt rounds 6 overflow 5:8256 -> 10:2829 -> 15:2649 -> 20:2194 -> 25:1976 -> 30:1864 | GRT-LABEL: DESIGN-FAIL: overflow 2829 at round 10 > 1000 |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 134.4 | grt rounds 6 overflow 5:3621 -> 10:1409 -> 15:822 -> 20:367 -> 25:132 -> 30:21 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 134.4 | grt rounds 6 overflow 5:3459 -> 10:2012 -> 15:1178 -> 20:769 -> 25:322 -> 30:29 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3739403 | ot_s81sl_leaf__t25 | 5_1_grt | 10.9 | grt rounds 3 overflow 5:29114 -> 10:25683 -> 15:21703 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 10.3 | grt rounds 3 overflow 5:27810 -> 10:12039 -> 15:6927 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 19.4 | grt rounds 3 overflow 5:49160 -> 10:43104 -> 15:40285 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 11.3 | grt rounds 2 overflow 5:46995 -> 10:41355 | GRT-LABEL: DESIGN-FAIL: overflow 41355 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 5.8 | grt rounds 3 overflow 5:12280 -> 10:11222 -> 15:10201 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 5.7 | last meaningful line 1.1 h ago (1369/1369 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-4083127 | col_h10_r0_p1__t1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (1302/1302 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2831053 | col_h10_r0_p4__t1 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (1388/1388 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3989312 | col_h10_r1__t1 | 5_1_grt | 2.8 | last meaningful line 0.5 h ago (199/208 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3973910 | col_h10_r1__t1 | pregrt_ff_hold | 2.8 | repair_Violations best 957 last 960 rows 114 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv74ebbc00-4014190 | col_h10_r1__t1 | 5_1_grt | 2.8 | last meaningful line 0.5 h ago (199/209 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-2782358 | col_h10_r1__t1 | 5_1_grt | 3.0 | last meaningful line 0.0 h ago (199/201 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvce76611c-3560691 | col_h10_r1__t1 | 5_1_grt | 2.9 | last meaningful line 0.5 h ago (199/211 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-3559181 | col_h10_r1__t1 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (1350/1350 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-4011286 | col_h10_r2__t1 | 5_1_grt | 2.8 | last meaningful line 0.0 h ago (176/176 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl8b686b3e-2806632 | col_h10_r2__t1 | 5_1_grt | 3.0 | last meaningful line 0.2 h ago (231/308 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__clac068e56-3628511 | col_h10_r2__t1 | 5_2_route | 8.0 | drt_violations best 71562 last 71562 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4028772 | col_h9_r0_p2__t1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (1258/1258 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p5__t1__pv35382794-4060983 | col_h9_r0_p5__t1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (815/815 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4028288 | col_h9_r1__t1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (1359/1359 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (1480/1480 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pve273b259-3097415 | col_h9_r1__t1 | 5_2_route | 8.2 | drt_violations best 82734 last 82734 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-3012090 | dsdv_slice_lepw_mus_LP__t2 | 5_1_grt | 10.5 | repair_Remaining best 297935 last 297935 rows 48 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi-4022037 | kv3_hgi | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (1260/1260 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (1033/1033 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t2-4070866 | ot_s81sl_leaf__t2 | tt_setup_repair | 2.8 | repair_Viol best 369 last 369 rows 46 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3281164 | sle_su_l1 | 5_1_grt | 2.9 | last meaningful line 0.0 h ago (793/799 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-191709 | slw_fw_v1 | 5_2_route | 11.5 | last meaningful line 0.3 h ago (277/278 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-195673 | slw_fw_v1 | 5_2_route | 11.5 | last meaningful line 0.3 h ago (275/276 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-3017015 | svc_lo_dsdv_svc_rs__t1 | 2_1_floorplan | 10.4 | repair_Viol best 45452 last 45452 rows 689 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t2-2905735 | svc_lo_dsdv_svc_rs__t2 | 2_1_floorplan | 10.5 | repair_Viol best 54713 last 54713 rows 740 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-2277016 | svc_lo_dsdv_svc_rs__t4 | 2_1_floorplan | 10.7 | repair_Viol best 45668 last 45668 rows 903 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003408_3748325-i1-3762223 | eco_20261120_003408_3748325-i1 | 5_2_route | 7.9 | drt_violations best 399 last 399 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748476-i1-3763736 | eco_20261120_003409_3748476-i1 | 5_2_route | 7.9 | drt_violations best 572 last 572 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1t-3763698 | eco_20261120_003409_3748726-i1t | 5_2_route | 7.9 | drt_violations best 29470 last 29470 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1t-2162531 | eco_recover1120-i1t | 5_2_route | 5.0 | last meaningful line 0.3 h ago (134/134 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-642785 | col_h9_r0_p1__t1 | 5_2_route | 8.6 | last meaningful line 0.5 h ago (272/273 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv6882e5ea-505829 | col_h9_r0_p2__t1 | 5_2_route | 8.7 | last meaningful line 0.5 h ago (283/284 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pvd86cb19a-505172 | col_h9_r0_p2__t1 | 5_2_route | 8.7 | last meaningful line 0.5 h ago (283/284 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-505237 | col_h9_r0_p4__t1 | 5_2_route | 8.7 | drt_violations best 97439 last 97439 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-504263 | col_h9_r0_p4__t1 | 5_2_route | 8.7 | last meaningful line 0.5 h ago (286/287 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49f0ba38-263250 | col_h9_r1__t1 | 5_2_route | 9.0 | drt_violations best 83292 last 83292 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv87d52780-504670 | col_h9_r1__t1 | 5_2_route | 8.7 | drt_violations best 83292 last 83292 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8ea75ee5-505402 | col_h9_r1__t1 | 5_2_route | 8.7 | drt_violations best 82734 last 82734 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvadbd1880-505510 | col_h9_r1__t1 | 5_2_route | 8.7 | drt_violations best 83292 last 83292 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-505372 | col_h9_r1__t1 | 5_2_route | 8.7 | drt_violations best 83292 last 83292 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvbb600efe-505577 | col_h9_r1__t1 | 5_2_route | 8.7 | drt_violations best 83025 last 83025 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-1780810 | slw_hc1 | 5_2_route | 16.1 | drt_violations best 122546 last 122546 rows 1 | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cle683a076-2387979 | slw_hc1 | 5_2_route | 15.3 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | kvcore-pcfh_-2846360 | kvcore-pcfh_ | 3_3_place_gp | 0.3 | overflow best 0.1571 last 0.1571 rows 42 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | otc-2848231-29567 | 2848231 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc7 | phscan-1854121 | phscan | 5_2_route | 0.2 | last meaningful line 0.1 h ago (283/284 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_083952_3300104-i1t-1853493 | eco_20261120_083952_3300104-i1t | 5_2_route | 7.8 | drt_violations best 22529 last 22529 rows 1 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_124815_3297714-i1t-3989767 | eco_20261120_124815_3297714-i1t | 5_2_route | 3.6 | last meaningful line 0.3 h ago (271/272 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_161628_1023465-i1t-2964619 | eco_20261120_161628_1023465-i1t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-fin-1174867 | fin | 6_report | 0.2 | last meaningful line 0.0 h ago (222/222 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-residual-i2r-1167548 | residual-i2r | 5_2_route | 5.4 | drt_violations best 18566 last 18566 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel1 | dpkit-cbn_q01__cldd6ea846-4146854 | cbn_q01 | 5_1_grt | 10.7 | last meaningful line 0.2 h ago (144/144 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl89936551_h-2365139 | cbx_q10 | tt_setup_repair_grt | 11.6 | repair_Viol best 38 last 38 rows 56 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-3326220 | col_h10_r2__t1 | 5_2_route | 11.1 | drt_violations best 74773 last 74773 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-3202568 | col_h9_r0_p4__t1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (3529/3529 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-4183728 | col_h9_r1__t1 | 5_2_route | 10.6 | drt_violations best 84302 last 84302 rows 1 | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-3731937 | col_h9_r1__t1 | 5_2_route | 10.9 | last meaningful line 0.5 h ago (277/278 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3191459 | col_h9_r2__t1 | 5_1_grt | 0.4 | last meaningful line 0.1 h ago (146/146 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2898480 | col_h9_r2__t1 | 5_2_route | 11.3 | drt_violations best 60304 last 60304 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2898962 | col_h9_r2__t1 | 5_2_route | 11.3 | drt_violations best 59723 last 59723 rows 1 | YOUNG: evidence 6.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3688123 | dsdv_slice_c1x_C__t5 | sdc_lint | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-918334 | dsdv_slice_iq_C__t1 | stage_odb_cap | 3.6 | last meaningful line 0.0 h ago (632/632 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Eo-393779 | kv3_hub_Eo | 4_1_cts | 10.5 | last meaningful line 0.5 h ago (6429/6429 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Wo-1210047 | kv3_hub_Wo | stage_odb_cap | 1.7 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-1330096 | kv3_pv_v12 | 3_5_place_dp | 10.1 | last meaningful line 0.8 h ago (119/119 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 11.3 | last meaningful line 1.8 h ago (216/224 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | postcts_gate_FF | 11.5 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | tt_setup_repair_grt | 11.8 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | postcts_gate_FF | 12.5 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | postcts_gate_TT | 12.5 | last meaningful line 0.1 h ago (372/372 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | postcts_gate_TT | 12.9 | last meaningful line 0.1 h ago (2181/2181 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-842919 | slw_st_b_v1 | 5_1_grt | 10.3 | repair_Remaining best 539972 last 539972 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t2-3187697 | svc_hi_dsdv_svc_rs__t2 | 2_1_floorplan | 9.2 | repair_Viol best 54816 last 54816 rows 1045 | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t3-2197154 | svc_hi_dsdv_svc_rs__t3 | 2_1_floorplan | 9.7 | repair_Viol best 55518 last 55518 rows 1039 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | otc-2295728-27466 | 2295728 | - | 28.1 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261120_003407_1650578-i1-1677571 | eco_20261120_003407_1650578-i1 | 5_2_route | 7.9 | drt_violations best 650 last 650 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | prd-eco_recover1120-i1t-303123 | eco_recover1120-i1t | 5_1_grt | 5.0 | last meaningful line 3.8 h ago (249/308 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel1 | prd-eco_recover1120-i1t-319029 | eco_recover1120-i1t | 5_1_grt | 5.0 | last meaningful line 3.9 h ago (249/351 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel1 | prd-eco_recover1120-i1t-330433 | eco_recover1120-i1t | 5_1_grt | 5.0 | last meaningful line 2.6 h ago (249/322 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | tt_setup_repair | 5.6 | repair_Viol best 1290 last 1290 rows 256 | YOUNG: stage 0.2 h < 1 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | tt_setup_repair | 5.6 | repair_Viol best 1192 last 1192 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2391268 | kv3_hgi_v1 | 5_1_grt | 5.8 | repair_TNS best 1.0129e+06 last 1.0129e+06 rows 5 | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel2 | dpkit-sle_hc0__cl929603c0__cl38badc56-1455458 | sle_hc0 | generate_abstract | 17.0 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2435819 | slw_hc1 | 5_2_route | 12.9 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-svc_lo_dsdv_svc_rs__t5-448347 | svc_lo_dsdv_svc_rs__t5 | 2_1_floorplan | 11.8 | repair_Viol best 54729 last 54729 rows 733 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-372309 | col_h10_r1__t1 | 5_1_grt | 21.3 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 21.3 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc7 | dpkit-kv3_hg_v1p6-1282096 | kv3_hg_v1p6 | 5_1_grt | 40.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v1__cl42bc8b12-557506 | kv3_hgi_v1 | 5_1_grt | 55.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc_v1__cl23f6a148-3798940 | kv3_pc_v1 | 5_1_grt | 68.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pv_v8-2521551 | kv3_pv_v8 | 5_1_grt | 38.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 55.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_pc_v3-2166515 | kv3_pc_v3 | 5_1_grt | 54.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | stage_odb_cap | 31.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | stage_odb_cap | 32.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-382185 | col_h10_r2__t1 | 5_2_route | 21.3 | drt_violations best 28 last 28 rows 48 | before-window best 99, window best 28 | PROGRESS: drt_violations improved 71.7 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-384874 | col_h10_r2__t1 | 5_2_route | 21.3 | drt_violations best 20 last 20 rows 49 | before-window best 85, window best 20 | PROGRESS: drt_violations improved 76.5 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-385072 | col_h10_r2__t1 | 5_2_route | 21.3 | drt_violations best 20 last 20 rows 51 | before-window best 99, window best 20 | PROGRESS: drt_violations improved 79.8 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3629353 | col_h10_r2__t1 | stage_odb_cap | 8.0 | last meaningful line 0.0 h ago (4550/4550 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv1c15776f-3629501 | col_h9_r1__t1 | stage_odb_cap | 8.0 | last meaningful line 0.0 h ago (765/765 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 17.6 | drt_violations best 11104 last 11104 rows 14 | before-window best 17057, window best 11104 | PROGRESS: drt_violations improved 34.9 % in window |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-768070 | slw_su_l1 | 5_2_route | 17.3 | drt_violations best 8002 last 8002 rows 16 | before-window best 11097, window best 8002 | PROGRESS: drt_violations improved 27.9 % in window |  |
| epyc7 | dpkit-tt_ctlm-4084399 | tt_ctlm | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (5138/5138 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-tt_ctlm-4118116 | tt_ctlm | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (5124/5124 lines) | PROGRESS: log still growing |  |
| epyc7 | ksyn-kv3_pc_v6_keepes-1828369 | ksyn-kv3_pc_v6_keepes | lec | 11.7 | LEC last write -0.0 h ago | PROGRESS: LEC still writing |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | pregrt_ff_hold | 10.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_su_l0__cl7a55c676-2377674 | sle_su_l0 | 5_2_route | 11.5 | drt_violations best 0 last 0 rows 5 | PROGRESS: drt_violations reached 0 |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 18.7 | last meaningful line 0.0 h ago (1113/1113 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 13.7 | last meaningful line 0.0 h ago (835/835 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_lep0N-830501 | hd_lep0N | stage_odb_cap | 11.7 | last meaningful line 0.0 h ago (694/694 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-1602787 | hd_mesh | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (838/838 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-4092448 | hd_mesh | stage_odb_cap | 12.0 | last meaningful line 0.0 h ago (758/758 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_sys_c-480894 | kv3_sys_c | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (703/703 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-1118548 | ot_s81sl_kv_leaf__t5 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (851/851 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t10-1107312 | ot_s81sl_leaf__t10 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (839/839 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (887/887 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t58-1113172 | ot_s81sl_leaf__t58 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (807/807 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t68-1111390 | ot_s81sl_leaf__t68 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (775/775 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-serdes__t1__clb45db5be-1142519 | serdes__t1 | stage_odb_cap | 9.2 | last meaningful line 0.0 h ago (691/691 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl6740750e-482449 | sle_fw_v2 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (703/703 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | stage_odb_cap | 12.4 | last meaningful line 0.0 h ago (815/815 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_hc0__cl05696ed1-1266312 | sle_hc0 | stage_odb_cap | 17.1 | last meaningful line 0.0 h ago (1071/1071 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c-1455485 | sle_hc0 | stage_odb_cap | 17.0 | last meaningful line 0.0 h ago (1075/1075 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2444359 | sle_st_b_v1 | stage_odb_cap | 15.8 | last meaningful line 0.0 h ago (944/944 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (703/703 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (703/703 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v3-489810 | slw_fw_v3 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (703/703 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | stage_odb_cap | 12.0 | last meaningful line 0.0 h ago (717/717 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (703/703 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-495397 | slw_st_b_v2 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (703/703 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-498208 | slw_st_b_v2 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (703/703 lines) | PROGRESS: log still growing |  |
