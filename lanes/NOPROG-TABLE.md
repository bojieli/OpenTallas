# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 07:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'GRT-LABEL': 15, 'YOUNG': 91, 'NO-DATA': 5, 'KEEP': 2, 'EXCLUDED': 10, 'PROGRESS': 43}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-slw_fw_v2__cl8537f156-3323404 | slw_fw_v2 | 5_2_route | 13.2 | drt_violations best 92593 last 92593 rows 1 | before-window best 92593, window best 92593 | NO-PROGRESS: drt_violations best 92593 vs 92593 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-2618689 | slw_stm_v1 | 5_2_route | 14.0 | drt_violations best 71340 last 71340 rows 1 | before-window best 71340, window best 71340 | NO-PROGRESS: drt_violations best 71340 vs 71340 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-dsdv_slice_lepw_mu_LP__t2-3004885 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 9.5 | grt rounds 3 overflow 5:232 -> 10:137 -> 15:41 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-502720 | ot_s81sl_leaf__t34 | 5_1_grt | 20.3 | grt rounds 5 overflow 5:39901 -> 10:35125 -> 15:32751 -> 20:33130 -> 25:38341 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-517470 | ot_s81sl_leaf__t4 | 5_1_grt | 20.3 | grt rounds 4 overflow 5:35892 -> 10:24430 -> 15:21368 -> 20:20290 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-3946553 | ot_s81sl_leaf__t54 | 5_1_grt | 9.1 | grt rounds 3 overflow 5:42877 -> 10:30539 -> 15:25376 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-col_h10_r1__t1__cld01bb4ae-2998457 | col_h10_r1__t1 | 5_1_grt | 18.4 | grt rounds 5 overflow 5:49459 -> 10:15428 -> 15:4782 -> 20:3247 -> 25:3339 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-coll_core-532020 | coll_core | 5_1_grt | 16.6 | grt rounds 3 overflow 5:40992 -> 10:31129 -> 15:29680 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-cbn_q00__cldbcda913-3330181 | cbn_q00 | 5_1_grt | 10.1 | grt rounds 6 overflow 5:11997 -> 10:8426 -> 15:4780 -> 20:1359 -> 25:485 -> 30:457 | GRT-LABEL: DESIGN-FAIL: overflow 8426 at round 10 > 1000 |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | 5_1_grt | 12.8 | grt rounds 6 overflow 5:8256 -> 10:2829 -> 15:2649 -> 20:2194 -> 25:1976 -> 30:1864 | GRT-LABEL: DESIGN-FAIL: overflow 2829 at round 10 > 1000 |  |
| intel1 | dpkit-cbx_q10__cl89936551_h-2365139 | cbx_q10 | 5_1_grt | 10.6 | grt rounds 6 overflow 5:2357 -> 10:2032 -> 15:2072 -> 20:1832 -> 25:1797 -> 30:1694 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 133.4 | grt rounds 6 overflow 5:3621 -> 10:1409 -> 15:822 -> 20:367 -> 25:132 -> 30:21 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 133.4 | grt rounds 6 overflow 5:3459 -> 10:2012 -> 15:1178 -> 20:769 -> 25:322 -> 30:29 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3739403 | ot_s81sl_leaf__t25 | 5_1_grt | 9.9 | grt rounds 3 overflow 5:29114 -> 10:25408 -> 15:21703 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 9.3 | grt rounds 3 overflow 5:27810 -> 10:11713 -> 15:6927 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 18.4 | grt rounds 3 overflow 5:49160 -> 10:43178 -> 15:40285 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 4.8 | grt rounds 3 overflow 5:12280 -> 10:17088 -> 15:13970 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 4.7 | last meaningful line 0.1 h ago (1369/1369 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-4083127 | col_h10_r0_p1__t1 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (704/704 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3973910 | col_h10_r1__t1 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (751/751 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-2782358 | col_h10_r1__t1 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (849/849 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvce76611c-3560691 | col_h10_r1__t1 | pregrt_ff_hold | 1.9 | repair_Violations best 258 last 258 rows 18 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-3559181 | col_h10_r1__t1 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (752/752 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3580023 | col_h10_r2__t1 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (883/883 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-4011286 | col_h10_r2__t1 | 5_1_grt | 1.8 | last meaningful line 0.0 h ago (195/197 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl8b686b3e-2806632 | col_h10_r2__t1 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (967/967 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-2814863 | col_h10_r2__t1 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (950/950 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4028772 | col_h9_r0_p2__t1 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (670/670 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p5__t1__pv35382794-4060983 | col_h9_r0_p5__t1 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (404/404 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4028288 | col_h9_r1__t1 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (771/771 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (882/882 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pve273b259-3097415 | col_h9_r1__t1 | 5_2_route | 7.2 | drt_violations best 82734 last 82734 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-4030221 | col_h9_r2__t1 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (867/867 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3265799 | col_h9_r2__t1 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (934/934 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-3012090 | dsdv_slice_lepw_mus_LP__t2 | 5_1_grt | 9.5 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-iqf__t1-2878121 | iqf__t1 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (231/231 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi-4022037 | kv3_hgi | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (670/670 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (467/467 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t2-4070866 | ot_s81sl_leaf__t2 | 4_1_cts | 1.8 | last meaningful line 0.0 h ago (91/91 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3281164 | sle_su_l1 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (194/194 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t40__cl1ea9de02-4030840 | slice_station__t40 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (624/624 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-191709 | slw_fw_v1 | 5_2_route | 10.5 | last meaningful line 0.3 h ago (272/272 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-195673 | slw_fw_v1 | 5_2_route | 10.5 | last meaningful line 0.3 h ago (270/270 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-3017015 | svc_lo_dsdv_svc_rs__t1 | 2_1_floorplan | 9.4 | repair_Viol best 45452 last 45452 rows 365 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t2-2905735 | svc_lo_dsdv_svc_rs__t2 | 2_1_floorplan | 9.5 | repair_Viol best 54713 last 54713 rows 416 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-2277016 | svc_lo_dsdv_svc_rs__t4 | 2_1_floorplan | 9.7 | repair_Viol best 45668 last 45668 rows 546 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_194944_478551-i1-4136079 | eco_20261119_194944_478551-i1 | 5_2_route | 4.9 | drt_violations best 4 last 4 rows 9 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003408_3748325-i1-3762223 | eco_20261120_003408_3748325-i1 | 5_2_route | 6.9 | drt_violations best 399 last 399 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748476-i1-3763736 | eco_20261120_003409_3748476-i1 | 5_2_route | 6.9 | drt_violations best 572 last 572 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1t-3763698 | eco_20261120_003409_3748726-i1t | 5_2_route | 6.9 | last meaningful line 0.1 h ago (276/277 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1t-2162531 | eco_recover1120-i1t | 5_1_grt | 4.0 | last meaningful line 3.2 h ago (249/990 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-642785 | col_h9_r0_p1__t1 | 5_2_route | 7.6 | last meaningful line 0.1 h ago (143/143 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv6882e5ea-505829 | col_h9_r0_p2__t1 | 5_2_route | 7.7 | last meaningful line 0.8 h ago (279/280 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pvd86cb19a-505172 | col_h9_r0_p2__t1 | 5_2_route | 7.7 | last meaningful line 0.5 h ago (279/280 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-505237 | col_h9_r0_p4__t1 | 5_2_route | 7.7 | last meaningful line 0.3 h ago (288/289 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-504263 | col_h9_r0_p4__t1 | 5_2_route | 7.7 | last meaningful line 0.5 h ago (282/283 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49f0ba38-263250 | col_h9_r1__t1 | 5_2_route | 8.0 | last meaningful line 0.8 h ago (280/281 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv87d52780-504670 | col_h9_r1__t1 | 5_2_route | 7.7 | last meaningful line 0.8 h ago (278/279 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8ea75ee5-505402 | col_h9_r1__t1 | 5_2_route | 7.7 | last meaningful line 0.6 h ago (278/279 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvadbd1880-505510 | col_h9_r1__t1 | 5_2_route | 7.7 | last meaningful line 0.5 h ago (278/279 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-505372 | col_h9_r1__t1 | 5_2_route | 7.7 | last meaningful line 0.5 h ago (278/279 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvbb600efe-505577 | col_h9_r1__t1 | 5_2_route | 7.7 | drt_violations best 83025 last 83025 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-1780810 | slw_hc1 | 5_2_route | 15.1 | drt_violations best 122546 last 122546 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cle683a076-2387979 | slw_hc1 | 5_2_route | 14.3 | last meaningful line 0.3 h ago (277/278 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2997578 | slw_sc_v1 | 5_2_route | 13.5 | drt_violations best 146550 last 146550 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-4084399 | tt_ctlm | 5_2_route | 8.3 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_083952_3300104-i1t-1853493 | eco_20261120_083952_3300104-i1t | 5_2_route | 6.8 | last meaningful line 0.5 h ago (279/280 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_124815_3297714-i1t-3989767 | eco_20261120_124815_3297714-i1t | 5_2_route | 2.6 | last meaningful line 0.3 h ago (265/266 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | prd-residual-i2r-1167548 | residual-i2r | 5_2_route | 4.4 | drt_violations best 18566 last 18566 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | prd-residual-i2r-1174867 | residual-i2r | 5_2_route | 4.4 | drt_violations best 15 last 15 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | so_872151_ff_39030 | so_872151_ff_39030 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc7 | so_872151_tt_39030 | so_872151_tt_39030 | signoff | 0.3 |  | NO-DATA: empty log |  |
| epyc7 | so_918105_ff_42653 | so_918105_ff_42653 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc7 | so_918105_tt_42653 | so_918105_tt_42653 | signoff | 0.2 |  | NO-DATA: empty log |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-3326220 | col_h10_r2__t1 | 5_2_route | 10.1 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2896534 | col_h10_r2__t1 | 5_2_route | 10.3 | last meaningful line 0.5 h ago (267/268 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-4183728 | col_h9_r1__t1 | 5_2_route | 9.6 | last meaningful line 0.5 h ago (275/276 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-3731937 | col_h9_r1__t1 | 5_2_route | 9.9 | last meaningful line 0.5 h ago (271/272 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2898480 | col_h9_r2__t1 | 5_2_route | 10.3 | last meaningful line 0.5 h ago (265/266 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2898962 | col_h9_r2__t1 | 5_2_route | 10.3 | last meaningful line 0.5 h ago (267/268 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-2901316 | col_h9_r2__t1 | 5_2_route | 10.3 | drt_violations best 62999 last 62999 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-918334 | dsdv_slice_iq_C__t1 | 3_3_place_gp | 2.6 | overflow best 0.5926 last 0.5926 rows 25 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Eo-393779 | kv3_hub_Eo | 4_1_cts | 9.5 | last meaningful line 0.3 h ago (6398/6398 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Wo-1210047 | kv3_hub_Wo | 2_1_floorplan | 0.7 | last meaningful line 0.5 h ago (84/84 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-1330096 | kv3_pv_v12 | 3_5_place_dp | 9.1 | last meaningful line 0.0 h ago (73/73 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3n-3612346 | kv3_pv_v3n | 3_5_place_dp | 8.0 | last meaningful line 0.2 h ago (120/120 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 10.3 | last meaningful line 2.0 h ago (216/224 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 10.3 | last meaningful line 0.8 h ago (216/221 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-sle_sc_v2-855260 | sle_sc_v2 | 3_3_place_gp | 0.8 | overflow best 0.2097 last 0.2097 rows 43 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | 5_1_grt | 10.5 | last meaningful line 1.5 h ago (224/856 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v2__cl7b3062fa-694049 | sle_stm_v2 | postcts_gate_FF | 11.3 | last meaningful line 0.1 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l0__cl7a55c676-2377674 | sle_su_l0 | 5_2_route | 10.5 | drt_violations best 44902 last 44902 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | 5_1_grt | 10.8 | repair_TNS best 7115.06 last 7115.06 rows 3 | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3031839 | slw_fe_v1 | 3_5_place_dp | 1.2 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | 5_1_grt | 11.5 | last meaningful line 0.1 h ago (929/935 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | tt_setup_repair_grt | 11.5 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | postcts_gate_TT | 11.9 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-842919 | slw_st_b_v1 | 5_1_grt | 9.3 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t2-3187697 | svc_hi_dsdv_svc_rs__t2 | 2_1_floorplan | 8.2 | repair_Viol best 54816 last 54816 rows 660 | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t3-2197154 | svc_hi_dsdv_svc_rs__t3 | 2_1_floorplan | 8.7 | repair_Viol best 55518 last 55518 rows 693 | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | otc-2100452-1459 | 2100452 | gen_lint_yosys | 1.4 | last meaningful line 1.4 h ago (1/1 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | otc-2295728-27466 | 2295728 | - | 27.1 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261120_003407_1650578-i1-1677571 | eco_20261120_003407_1650578-i1 | 5_2_route | 6.9 | last meaningful line 0.1 h ago (266/267 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | prd-eco_recover1120-i1t-303123 | eco_recover1120-i1t | 5_1_grt | 4.0 | last meaningful line 2.8 h ago (249/308 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | prd-eco_recover1120-i1t-319029 | eco_recover1120-i1t | 5_1_grt | 4.0 | last meaningful line 2.9 h ago (249/351 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | prd-eco_recover1120-i1t-330433 | eco_recover1120-i1t | 5_1_grt | 4.0 | last meaningful line 1.6 h ago (249/322 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 4_1_cts | 4.6 | last meaningful line 0.0 h ago (3822/3822 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 4_1_cts | 4.6 | last meaningful line 0.0 h ago (3841/3841 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2391268 | kv3_hgi_v1 | 5_1_grt | 4.8 | last meaningful line 0.1 h ago (730/760 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | 5_2_route | 11.4 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c-1455485 | sle_hc0 | 5_2_route | 16.0 | drt_violations best 7832 last 7832 rows 3 | YOUNG: evidence 5.9 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | 5_1_grt | 10.8 | last meaningful line 0.2 h ago (1038/1084 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-372309 | col_h10_r1__t1 | 5_1_grt | 20.3 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 20.3 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-2585815 | dsdv_slice_lepe_mu_LP__t2 | stage_odb_cap | 37.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hg_v1p6-1282096 | kv3_hg_v1p6 | 5_1_grt | 39.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v1__cl42bc8b12-557506 | kv3_hgi_v1 | 5_1_grt | 54.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc_v1__cl23f6a148-3798940 | kv3_pc_v1 | 5_1_grt | 67.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc_v1__cl7f648944-3798924 | kv3_pc_v1 | tt_setup_repair_grt | 67.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pv_v8-2521551 | kv3_pv_v8 | 5_1_grt | 37.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 54.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_pc_v3-2166515 | kv3_pc_v3 | 5_1_grt | 53.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | stage_odb_cap | 30.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | stage_odb_cap | 31.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2831053 | col_h10_r0_p4__t1 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3989312 | col_h10_r1__t1 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv74ebbc00-4014190 | col_h10_r1__t1 | pregrt_ff_hold | 1.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-382185 | col_h10_r2__t1 | 5_2_route | 20.3 | drt_violations best 28 last 28 rows 48 | before-window best 247, window best 28 | PROGRESS: drt_violations improved 88.7 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-384874 | col_h10_r2__t1 | 5_2_route | 20.3 | drt_violations best 28 last 28 rows 48 | before-window best 247, window best 28 | PROGRESS: drt_violations improved 88.7 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-385072 | col_h10_r2__t1 | 5_2_route | 20.3 | drt_violations best 28 last 28 rows 48 | before-window best 247, window best 28 | PROGRESS: drt_violations improved 88.7 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3629353 | col_h10_r2__t1 | stage_odb_cap | 7.0 | last meaningful line 0.0 h ago (3960/3960 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r2__t1__clac068e56-3628511 | col_h10_r2__t1 | stage_odb_cap | 7.0 | last meaningful line 0.0 h ago (3962/3962 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv1c15776f-3629501 | col_h9_r1__t1 | stage_odb_cap | 7.0 | last meaningful line 0.0 h ago (706/706 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r2__t1__cl87f3ff59-2810629 | col_h9_r2__t1 | 5_1_grt | 2.0 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | otc-2824388-15608 | 2824388 | 4_1_cts | 0.2 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 16.6 | drt_violations best 11104 last 11104 rows 14 | before-window best 18123, window best 11104 | PROGRESS: drt_violations improved 38.7 % in window |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-768070 | slw_su_l1 | 5_2_route | 16.3 | drt_violations best 8002 last 8002 rows 16 | before-window best 13874, window best 8002 | PROGRESS: drt_violations improved 42.3 % in window |  |
| epyc7 | dpkit-tt_ctlm-4118116 | tt_ctlm | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (4524/4524 lines) | PROGRESS: log still growing |  |
| epyc7 | ksyn-kv3_pc_v6_keepes-1828369 | ksyn-kv3_pc_v6_keepes | lec | 10.7 | LEC last write 0.0 h ago | PROGRESS: LEC still writing |  |
| intel1 | dpkit-cbn_q01__cldd6ea846-4146854 | cbn_q01 | pregrt_ff_hold | 9.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | pregrt_ff_hold | 9.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261120_003409_1651933-i1t-1681241 | eco_20261120_003409_1651933-i1t | 5_1_grt | 6.9 | last meaningful line 5.5 h ago (244/275 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 17.7 | last meaningful line 0.0 h ago (1054/1054 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 12.7 | last meaningful line 0.0 h ago (776/776 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_lep0N-830501 | hd_lep0N | stage_odb_cap | 10.7 | last meaningful line 0.0 h ago (634/634 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-1602787 | hd_mesh | stage_odb_cap | 12.3 | last meaningful line 0.0 h ago (778/778 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-4092448 | hd_mesh | stage_odb_cap | 11.0 | last meaningful line 0.0 h ago (698/698 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_sys_c-480894 | kv3_sys_c | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (644/644 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-1118548 | ot_s81sl_kv_leaf__t5 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (792/792 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t10-1107312 | ot_s81sl_leaf__t10 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (780/780 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (827/827 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t58-1113172 | ot_s81sl_leaf__t58 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (748/748 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t68-1111390 | ot_s81sl_leaf__t68 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (716/716 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-serdes__t1__clb45db5be-1142519 | serdes__t1 | stage_odb_cap | 8.2 | last meaningful line 0.0 h ago (632/632 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl6740750e-482449 | sle_fw_v2 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (644/644 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_hc0__cl05696ed1-1266312 | sle_hc0 | stage_odb_cap | 16.1 | last meaningful line 0.0 h ago (1012/1012 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_hc0__cl929603c0__cl38badc56-1455458 | sle_hc0 | 5_2_route | 16.0 | drt_violations best 9348 last 9348 rows 3 | before-window best 102297, window best 9348 | PROGRESS: drt_violations improved 90.9 % in window |  |
| intel2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2444359 | sle_st_b_v1 | stage_odb_cap | 14.8 | last meaningful line 0.0 h ago (885/885 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (643/643 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (643/643 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v3-489810 | slw_fw_v3 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (643/643 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2435819 | slw_hc1 | stage_odb_cap | 11.9 | last meaningful line 0.0 h ago (768/768 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | stage_odb_cap | 11.0 | last meaningful line 0.0 h ago (658/658 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-495397 | slw_st_b_v2 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (643/643 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-498208 | slw_st_b_v2 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (643/643 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t1-1341320 | svc_hi_dsdv_svc_pvso_entry__t1 | stage_odb_cap | 8.1 | last meaningful line 0.0 h ago (483/483 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-svc_lo_dsdv_svc_rs__t5-448347 | svc_lo_dsdv_svc_rs__t5 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (644/644 lines) | PROGRESS: log still growing |  |
