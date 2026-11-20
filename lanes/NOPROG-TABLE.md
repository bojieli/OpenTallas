# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 06:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'GRT-LABEL': 16, 'YOUNG': 117, 'NO-DATA': 1, 'KEEP': 2, 'EXCLUDED': 10, 'PROGRESS': 40}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| intel1 | dpkit-slice_station__t24__cleece78ec-2385680 | slice_station__t24 | 5_2_route | 8.8 | drt_violations best 7204 last 7204 rows 1 | before-window best 7204, window best 7204 | NO-PROGRESS: drt_violations best 7204 vs 7204 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel1 | dpkit-slw_su_l0__cl1a1c1f8f-3380863 | slw_su_l0 | 5_2_route | 10.3 | drt_violations best 43448 last 43448 rows 1 | before-window best 43448, window best 43448 | NO-PROGRESS: drt_violations best 43448 vs 43448 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-ot_s81sl_leaf__t34-502720 | ot_s81sl_leaf__t34 | 5_1_grt | 18.8 | grt rounds 5 overflow 5:39901 -> 10:35125 -> 15:32751 -> 20:33130 -> 25:38341 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-517470 | ot_s81sl_leaf__t4 | 5_1_grt | 18.8 | grt rounds 4 overflow 5:33299 -> 10:24430 -> 15:21368 -> 20:20290 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-3946553 | ot_s81sl_leaf__t54 | 5_1_grt | 7.6 | grt rounds 3 overflow 5:45500 -> 10:30539 -> 15:25376 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-col_h10_r1__t1__cld01bb4ae-2998457 | col_h10_r1__t1 | 5_1_grt | 16.9 | grt rounds 5 overflow 5:49459 -> 10:15428 -> 15:4782 -> 20:3247 -> 25:3339 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pvb22875c0-913556 | col_h9_r0_p5__t1 | 5_1_grt | 5.8 | grt rounds 3 overflow 5:5377 -> 10:2831 -> 15:1655 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-coll_core-532020 | coll_core | 5_1_grt | 15.1 | grt rounds 3 overflow 5:40992 -> 10:31129 -> 15:29680 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | 5_1_grt | 11.1 | grt rounds 4 overflow 5:8256 -> 10:2829 -> 15:2649 -> 20:2194 | GRT-LABEL: DESIGN-FAIL: overflow 2829 at round 10 > 1000 |  |
| intel1 | dpkit-cbx_q10__cl89936551_h-2365139 | cbx_q10 | 5_1_grt | 8.8 | grt rounds 6 overflow 5:2357 -> 10:2032 -> 15:2072 -> 20:1832 -> 25:1797 -> 30:1694 | GRT-LABEL: DESIGN-FAIL: overflow 2032 at round 10 > 1000 |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 131.7 | grt rounds 6 overflow 5:3621 -> 10:1409 -> 15:822 -> 20:367 -> 25:132 -> 30:21 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 131.7 | grt rounds 6 overflow 5:3459 -> 10:2012 -> 15:1178 -> 20:769 -> 25:322 -> 30:29 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3739403 | ot_s81sl_leaf__t25 | 5_1_grt | 8.1 | grt rounds 3 overflow 5:28193 -> 10:26928 -> 15:21703 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 7.5 | grt rounds 3 overflow 5:27842 -> 10:14403 -> 15:6927 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-838589 | ot_s81sl_leaf__t53 | 5_1_grt | 7.5 | grt rounds 2 overflow 5:51746 -> 10:53387 | GRT-LABEL: DESIGN-FAIL: overflow 53387 at round 10 > 1000 |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 16.6 | grt rounds 3 overflow 5:49015 -> 10:43178 -> 15:40285 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_stm_v2__cl7b3062fa-694049 | sle_stm_v2 | 5_1_grt | 9.6 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 3.3 | grt rounds 2 overflow 5:24897 -> 10:17088 | GRT-LABEL: DESIGN-FAIL: overflow 17088 at round 10 > 1000 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 3.2 | last meaningful line 0.2 h ago (1367/1367 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-4083127 | col_h10_r0_p1__t1 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pv5b623e07-2831053 | col_h10_r0_p4__t1 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (80/80 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3989312 | col_h10_r1__t1 | 4_1_cts | 0.3 | repair_Violations best 28 last 50 rows 14 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-3973910 | col_h10_r1__t1 | 3_3_place_gp | 0.3 | overflow best 0.4218 last 0.4218 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv74ebbc00-4014190 | col_h10_r1__t1 | 4_1_cts | 0.3 | repair_Violations best 28 last 68 rows 13 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-2782358 | col_h10_r1__t1 | 3_3_place_gp | 0.5 | overflow best 0.3155 last 0.3155 rows 28 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-3559181 | col_h10_r1__t1 | 3_3_place_gp | 0.4 | overflow best 0.3745 last 0.3842 rows 7 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3580023 | col_h10_r2__t1 | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-4011286 | col_h10_r2__t1 | 3_3_place_gp | 0.3 | overflow best 0.2935 last 0.3101 rows 9 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl8b686b3e-2806632 | col_h10_r2__t1 | 4_1_cts | 0.5 | last meaningful line -0.0 h ago (2025/2025 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3629353 | col_h10_r2__t1 | stage_odb_cap | 5.5 | last meaningful line 0.0 h ago (3070/3070 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__clac068e56-3628511 | col_h10_r2__t1 | stage_odb_cap | 5.5 | last meaningful line 0.0 h ago (3072/3072 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4028772 | col_h9_r0_p2__t1 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p5__t1__pv35382794-4060983 | col_h9_r0_p5__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.6197 last 0.6197 rows 28 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4028288 | col_h9_r1__t1 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv1c15776f-3629501 | col_h9_r1__t1 | stage_odb_cap | 5.5 | last meaningful line 0.0 h ago (617/617 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | 3_5_place_dp | 0.5 | last meaningful line -0.0 h ago (46/46 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pve273b259-3097415 | col_h9_r1__t1 | 5_2_route | 5.7 | last meaningful line 0.2 h ago (276/277 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__cl774acf45__pv858fb2ba-4030221 | col_h9_r2__t1 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__cl87f3ff59-2810629 | col_h9_r2__t1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (1981/1981 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3265799 | col_h9_r2__t1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (47/47 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_LP__t2-3004885 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 8.0 | repair_TNS best 16723.2 last 16723.2 rows 1 | YOUNG: evidence 7.1 h < 7.5 h |  |
| epyc2 | dpkit-gunit__t1-3267504 | gunit__t1 | 3_3_place_gp | 0.4 | last meaningful line 0.0 h ago (71/71 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-iqf__t1-2878121 | iqf__t1 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (2497/2497 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hgi-4022037 | kv3_hgi | 3_1_place_gp_skip_io | 0.3 | overflow best 0.6344 last 0.7452 rows 22 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9963 last 0.9963 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | 3_3_place_gp | 0.5 | overflow best 0.6566 last 0.6686 rows 24 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t2-4070866 | ot_s81sl_leaf__t2 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9245 last 0.9309 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-3281164 | sle_su_l1 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (2368/2368 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t29__cl2e5c855a-2846396 | slice_station__t29 | 5_2_route | 5.9 | drt_violations best 1302 last 1302 rows 3 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t40__cl1ea9de02-4030840 | slice_station__t40 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9916 last 0.9916 rows 18 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-191709 | slw_fw_v1 | 5_2_route | 9.0 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-195673 | slw_fw_v1 | postcts_gate_TT | 9.0 | last meaningful line 0.1 h ago (935/935 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-2810173 | slw_fw_v2 | 3_3_place_gp | 0.5 | overflow best 0.3871 last 0.3871 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t2-2905735 | svc_lo_dsdv_svc_rs__t2 | 2_1_floorplan | 8.0 | repair_Viol best 54713 last 54713 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-2277016 | svc_lo_dsdv_svc_rs__t4 | 2_1_floorplan | 8.2 | repair_Viol best 45668 last 45668 rows 13 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | eco-abs-1244122 | eco-abs | generate_abstract | 0.0 | last meaningful line 0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-4159560-26620 | 4159560 | gen_lint_yosys | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | prd-count-p1_tc-2661476 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (61/61 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_193300_4163996-i1-3122467 | eco_20261119_193300_4163996-i1 | 5_2_route | 3.9 | drt_violations best 4176 last 4176 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_194944_478551-i1-4136079 | eco_20261119_194944_478551-i1 | 5_2_route | 3.4 | drt_violations best 3666 last 3666 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_195623_475807-i1-2402593 | eco_20261119_195623_475807-i1 | 5_2_route | 4.3 | drt_violations best 3511 last 3511 rows 1 | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_195829_480745-i1-3584348 | eco_20261119_195829_480745-i1 | 5_2_route | 3.7 | drt_violations best 3511 last 3511 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003408_3748325-i1-3762223 | eco_20261120_003408_3748325-i1 | 5_2_route | 5.4 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748476-i1-3763736 | eco_20261120_003409_3748476-i1 | 5_2_route | 5.4 | last meaningful line 0.4 h ago (268/269 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1t-3763698 | eco_20261120_003409_3748726-i1t | 5_2_route | 5.4 | last meaningful line 0.5 h ago (264/265 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1t-2162531 | eco_recover1120-i1t | 5_1_grt | 2.5 | last meaningful line 1.7 h ago (249/320 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q01-767696 | cbf_q01 | 5_2_route | 14.8 | last meaningful line 0.7 h ago (278/279 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-642785 | col_h9_r0_p1__t1 | 5_1_grt | 6.1 | last meaningful line 0.2 h ago (245/389 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv6882e5ea-505829 | col_h9_r0_p2__t1 | 5_2_route | 6.2 | last meaningful line 0.5 h ago (273/274 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pvd86cb19a-505172 | col_h9_r0_p2__t1 | 5_2_route | 6.2 | last meaningful line 0.5 h ago (273/274 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-505237 | col_h9_r0_p4__t1 | 5_2_route | 6.2 | last meaningful line 0.3 h ago (278/279 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-504263 | col_h9_r0_p4__t1 | 5_2_route | 6.2 | last meaningful line 0.3 h ago (276/277 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49f0ba38-263250 | col_h9_r1__t1 | 5_2_route | 6.5 | last meaningful line 0.5 h ago (274/275 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv87d52780-504670 | col_h9_r1__t1 | 5_2_route | 6.2 | last meaningful line 0.3 h ago (272/273 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8ea75ee5-505402 | col_h9_r1__t1 | 5_2_route | 6.2 | last meaningful line 0.7 h ago (270/271 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvadbd1880-505510 | col_h9_r1__t1 | 5_2_route | 6.2 | last meaningful line 0.7 h ago (270/271 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-505372 | col_h9_r1__t1 | 5_2_route | 6.2 | last meaningful line 0.7 h ago (270/271 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvbb600efe-505577 | col_h9_r1__t1 | 5_2_route | 6.2 | last meaningful line 0.5 h ago (274/275 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v2__cl8537f156-3323404 | slw_fw_v2 | 5_2_route | 11.7 | drt_violations best 92593 last 92593 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-1780810 | slw_hc1 | 5_2_route | 13.6 | last meaningful line 0.3 h ago (284/285 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cle683a076-2387979 | slw_hc1 | 5_2_route | 12.8 | last meaningful line 0.3 h ago (139/139 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2997578 | slw_sc_v1 | 5_2_route | 12.0 | last meaningful line 0.7 h ago (278/279 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-2618689 | slw_stm_v1 | 5_2_route | 12.5 | last meaningful line 0.7 h ago (277/278 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-4084399 | tt_ctlm | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (3638/3638 lines) | YOUNG: evidence 6.8 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-4118116 | tt_ctlm | 5_1_grt | 6.8 | last meaningful line 0.0 h ago (194/199 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_083952_3300104-i1t-1853493 | eco_20261120_083952_3300104-i1t | 5_2_route | 5.3 | last meaningful line 0.5 h ago (271/272 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_124815_3297714-i1t-3989767 | eco_20261120_124815_3297714-i1t | 5_1_grt | 1.1 | last meaningful line 0.2 h ago (234/329 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | prd-residual-i2r-1167548 | residual-i2r | 5_2_route | 2.9 | last meaningful line 0.3 h ago (265/266 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | prd-residual-i2r-1174867 | residual-i2r | 5_2_route | 2.9 | last meaningful line 0.2 h ago (260/261 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-bk_sel__t2-3192657 | bk_sel__t2 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.9113 last 0.974 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-cbn_q00__cldbcda913-3330181 | cbn_q00 | 5_1_grt | 8.3 | last meaningful line 0.3 h ago (206/215 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-3326220 | col_h10_r2__t1 | 5_2_route | 8.3 | last meaningful line 0.8 h ago (257/258 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2896534 | col_h10_r2__t1 | 5_2_route | 8.5 | last meaningful line 1.0 h ago (257/258 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-4183728 | col_h9_r1__t1 | 5_2_route | 7.9 | last meaningful line 0.2 h ago (265/266 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-3731937 | col_h9_r1__t1 | 5_2_route | 8.1 | last meaningful line 0.2 h ago (260/260 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2898480 | col_h9_r2__t1 | 5_2_route | 8.5 | last meaningful line 0.8 h ago (255/256 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2898962 | col_h9_r2__t1 | 5_2_route | 8.5 | last meaningful line 1.0 h ago (255/256 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-2901316 | col_h9_r2__t1 | 5_2_route | 8.5 | last meaningful line 0.5 h ago (259/260 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-918334 | dsdv_slice_iq_C__t1 | 2_4_floorplan_pdn | 0.9 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-glue-293542 | glue | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (189/189 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Eo-393779 | kv3_hub_Eo | 4_1_cts | 7.7 | last meaningful line 0.1 h ago (27/27 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-1330096 | kv3_pv_v12 | 3_4_place_resized | 7.3 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-3619680 | kv3_pv_v12 | 3_5_place_dp | 10.2 | last meaningful line 1.0 h ago (119/119 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v2-1275856 | kv3_pv_v2 | 3_5_place_dp | 7.3 | last meaningful line 0.5 h ago (118/118 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v2n-880645 | kv3_pv_v2n | 3_5_place_dp | 7.5 | last meaningful line 0.5 h ago (119/119 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3-1202037 | kv3_pv_v3 | 3_4_place_resized | 7.4 | last meaningful line 0.8 h ago (688/688 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3n-3612346 | kv3_pv_v3n | 3_3_place_gp | 6.3 | overflow best 0.0996 last 0.0996 rows 44 | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v4-1798134 | kv3_pv_v4 | 3_4_place_resized | 7.1 | last meaningful line 0.5 h ago (606/606 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 8.5 | last meaningful line 0.3 h ago (216/218 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 8.5 | last meaningful line 0.5 h ago (165/165 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 4_1_cts | 7.9 | last meaningful line 0.2 h ago (7811/7811 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | 5_1_grt | 8.8 | last meaningful line 0.8 h ago (142/142 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__clbe630b9c-4044402 | sle_stm_v1 | 5_1_grt | 10.0 | last meaningful line 0.3 h ago (923/940 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l0__cl7a55c676-2377674 | sle_su_l0 | 5_2_route | 8.8 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | 5_1_grt | 9.1 | repair_Remaining best 118774 last 118774 rows 242 | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | 5_1_grt | 9.8 | last meaningful line 0.2 h ago (135/135 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | 5_1_grt | 9.8 | last meaningful line 0.5 h ago (135/135 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | 5_1_grt | 10.2 | last meaningful line 1.1 h ago (232/953 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t2-3187697 | svc_hi_dsdv_svc_rs__t2 | 2_1_floorplan | 6.5 | repair_Viol best 54816 last 54816 rows 4 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t3-2197154 | svc_hi_dsdv_svc_rs__t3 | 2_1_floorplan | 6.9 | repair_Viol best 55518 last 55518 rows 80 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | otc-2295728-27466 | 2295728 | - | 25.4 |  | NO-DATA: no log found |  |
| intel1 | otc-2677942-26726 | 2677942 | gen_lint_yosys | 1.6 | last meaningful line 1.6 h ago (1/1 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | otc-3239598-26208 | 3239598 | gen_lint_yosys | 1.4 | last meaningful line 1.4 h ago (1/1 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | prd-eco_20261120_003407_1650578-i1-1677571 | eco_20261120_003407_1650578-i1 | 5_2_route | 5.2 | last meaningful line 0.1 h ago (126/126 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | prd-eco_20261120_003409_1651933-i1t-1681241 | eco_20261120_003409_1651933-i1t | 5_1_grt | 5.2 | last meaningful line 3.7 h ago (244/275 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel1 | prd-eco_recover1120-i1t-303123 | eco_recover1120-i1t | 5_1_grt | 2.3 | last meaningful line 1.1 h ago (249/308 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | prd-eco_recover1120-i1t-319029 | eco_recover1120-i1t | 5_1_grt | 2.2 | last meaningful line 1.1 h ago (249/351 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | prd-eco_recover1120-i1t-330433 | eco_recover1120-i1t | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (186/186 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-1241882 | col_h9_r0_p1__t1 | tt_setup_repair_grt | 6.7 | repair_Viol best 1134 last 1134 rows 1008 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 3_5_place_dp | 3.1 | last meaningful line 0.5 h ago (47/47 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 3_5_place_dp | 3.1 | last meaningful line 0.5 h ago (47/47 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2391268 | kv3_hgi_v1 | 5_1_grt | 3.3 | last meaningful line 1.3 h ago (202/229 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel2 | dpkit-serdes__t1__clb45db5be-1142519 | serdes__t1 | 5_1_grt | 6.7 | repair_Viol best 333 last 333 rows 240 | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t1-1341320 | svc_hi_dsdv_svc_pvso_entry__t1 | 2_1_floorplan | 6.6 | repair_Viol best 63954 last 63954 rows 496 | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-1267600 | svc_hi_dsdv_svc_rs__t1 | 2_1_floorplan | 6.7 | repair_Viol best 45139 last 45139 rows 787 | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel2 | dpkit-svc_lo_dsdv_svc_rs__t5-448347 | svc_lo_dsdv_svc_rs__t5 | 2_1_floorplan | 9.3 | repair_Viol best 54729 last 54729 rows 28 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-372309 | col_h10_r1__t1 | 5_1_grt | 18.8 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 18.8 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-2585815 | dsdv_slice_lepe_mu_LP__t2 | stage_odb_cap | 36.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hg_v1p6-1282096 | kv3_hg_v1p6 | 5_1_grt | 37.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v1__cl42bc8b12-557506 | kv3_hgi_v1 | 5_1_grt | 53.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc_v1__cl23f6a148-3798940 | kv3_pc_v1 | 5_1_grt | 66.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc_v1__cl7f648944-3798924 | kv3_pc_v1 | 5_1_grt | 66.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pv_v8-2521551 | kv3_pv_v8 | 5_1_grt | 36.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 53.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_pc_v3-2166515 | kv3_pc_v3 | 5_1_grt | 52.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | stage_odb_cap | 29.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | stage_odb_cap | 29.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvce76611c-3560691 | col_h10_r1__t1 | 4_1_cts | 0.4 | repair_Violations best 0 last 0 rows 3 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-382185 | col_h10_r2__t1 | 5_2_route | 18.8 | drt_violations best 43 last 43 rows 46 | before-window best 247, window best 43 | PROGRESS: drt_violations improved 82.6 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-384874 | col_h10_r2__t1 | 5_2_route | 18.8 | drt_violations best 43 last 43 rows 46 | before-window best 247, window best 43 | PROGRESS: drt_violations improved 82.6 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-385072 | col_h10_r2__t1 | 5_2_route | 18.8 | drt_violations best 43 last 43 rows 46 | before-window best 247, window best 43 | PROGRESS: drt_violations improved 82.6 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-2814863 | col_h10_r2__t1 | 3_5_place_dp | 0.5 | repair_Violations best 0 last 0 rows 29 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-3012090 | dsdv_slice_lepw_mus_LP__t2 | pregrt_ff_hold | 8.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-3017015 | svc_lo_dsdv_svc_rs__t1 | lec | 7.9 | LEC last write 0.1 h ago | PROGRESS: LEC still writing |  |
| epyc2 | prd-eco_20261119_184546_1168863-i1-2177945 | eco_20261119_184546_1168863-i1 | 5_2_route | 4.4 | drt_violations best 0 last 0 rows 39 | PROGRESS: drt_violations reached 0 |  |
| epyc7 | dpkit-slw_hc0__cl1bc59e1c-1024005 | slw_hc0 | 5_2_route | 14.5 | drt_violations best 9523 last 9523 rows 3 | before-window best 103810, window best 9523 | PROGRESS: drt_violations improved 90.8 % in window |  |
| epyc7 | dpkit-slw_st_b_v2__pvc2ec5bfb-240135 | slw_st_b_v2 | 5_2_route | 15.4 | drt_violations best 10027 last 10027 rows 2 | before-window best 85240, window best 10027 | PROGRESS: drt_violations improved 88.2 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 15.1 | drt_violations best 11596 last 11596 rows 13 | before-window best 35429, window best 11596 | PROGRESS: drt_violations improved 67.3 % in window |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-768070 | slw_su_l1 | 5_2_route | 14.8 | drt_violations best 8483 last 8483 rows 14 | before-window best 14755, window best 8483 | PROGRESS: drt_violations improved 42.5 % in window |  |
| epyc7 | ksyn-kv3_pc_v6_keepes-1828369 | ksyn-kv3_pc_v6_keepes | lec | 9.2 | LEC last write 0.2 h ago | PROGRESS: LEC still writing |  |
| intel1 | dpkit-cbn_q01__cldd6ea846-4146854 | cbn_q01 | pregrt_ff_hold | 7.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-842919 | slw_st_b_v1 | pregrt_ff_hold | 7.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 16.2 | last meaningful line 0.0 h ago (965/965 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 11.2 | last meaningful line 0.0 h ago (686/686 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_lep0N-830501 | hd_lep0N | stage_odb_cap | 9.2 | last meaningful line 0.0 h ago (545/545 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-1602787 | hd_mesh | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (689/689 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-4092448 | hd_mesh | stage_odb_cap | 9.5 | last meaningful line 0.0 h ago (609/609 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_sys_c-480894 | kv3_sys_c | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (554/554 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-1118548 | ot_s81sl_kv_leaf__t5 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (702/702 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t10-1107312 | ot_s81sl_leaf__t10 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (690/690 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (738/738 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t58-1113172 | ot_s81sl_leaf__t58 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (658/658 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t68-1111390 | ot_s81sl_leaf__t68 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (626/626 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl6740750e-482449 | sle_fw_v2 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (554/554 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | stage_odb_cap | 9.9 | last meaningful line 0.0 h ago (666/666 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_hc0__cl05696ed1-1266312 | sle_hc0 | stage_odb_cap | 14.6 | last meaningful line 0.0 h ago (922/922 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_hc0__cl929603c0__cl38badc56-1455458 | sle_hc0 | stage_odb_cap | 14.5 | last meaningful line 0.0 h ago (915/915 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c-1455485 | sle_hc0 | stage_odb_cap | 14.5 | last meaningful line 0.0 h ago (926/926 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2444359 | sle_st_b_v1 | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (796/796 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (554/554 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (554/554 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v3-489810 | slw_fw_v3 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (554/554 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2435819 | slw_hc1 | stage_odb_cap | 10.4 | last meaningful line 0.0 h ago (678/678 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | stage_odb_cap | 9.5 | last meaningful line 0.0 h ago (568/568 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (554/554 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-495397 | slw_st_b_v2 | 5_1_grt | 9.3 | repair_TNS best 0 last 0 rows 10 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-498208 | slw_st_b_v2 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (554/554 lines) | PROGRESS: log still growing |  |
