# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 02:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'GRT-LABEL': 11, 'YOUNG': 169, 'NO-DATA': 5, 'KEEP': 2, 'EXCLUDED': 15, 'PROGRESS': 43}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| intel1 | dpkit-slw_fw_v2__cl8f84514c-2549308 | slw_fw_v2 | 5_2_route | 14.6 | drt_violations best 85626 last 85626 rows 1 | before-window best 85626, window best 85626 | NO-PROGRESS: drt_violations best 85626 vs 85626 before window: < 2 % in 7.5 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2436381 | dsdv_slice_c1x_C__t10 | 5_1_grt | 23.0 | grt rounds 2 overflow 5:66206 -> 10:63889 | GRT-LABEL: DESIGN-FAIL: overflow 63889 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-502720 | ot_s81sl_leaf__t34 | 5_1_grt | 15.0 | grt rounds 4 overflow 5:39901 -> 10:35125 -> 15:32751 -> 20:33130 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-517470 | ot_s81sl_leaf__t4 | 5_1_grt | 15.0 | grt rounds 3 overflow 5:33299 -> 10:24430 -> 15:21822 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-col_h10_r1__t1__cld01bb4ae-2998457 | col_h10_r1__t1 | 5_1_grt | 13.1 | grt rounds 4 overflow 5:49459 -> 10:15428 -> 15:4782 -> 20:3465 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-coll_core-532020 | coll_core | 5_1_grt | 11.3 | grt rounds 3 overflow 5:41395 -> 10:31221 -> 15:29694 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | llc-2212797-5048104.pin1 | llc-2212797-5048104.pin1 | 5_1_grt | 1.2 | grt rounds 3 overflow 5:41051 -> 10:42286 -> 15:35874 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | llc-2387163-5128856.pin2 | llc-2387163-5128856.pin2 | 5_1_grt | 0.3 | grt rounds 3 overflow 5:41395 -> 10:31221 -> 15:29694 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 127.9 | grt rounds 6 overflow 5:3621 -> 10:1409 -> 15:822 -> 20:367 -> 25:132 -> 30:21 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 127.9 | grt rounds 6 overflow 5:3459 -> 10:2012 -> 15:1178 -> 20:769 -> 25:322 -> 30:29 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 12.9 | grt rounds 3 overflow 5:55253 -> 10:43864 -> 15:40285 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-serdes__t14-1137423 | serdes__t14 | 5_1_grt | 3.0 | grt rounds 1 overflow 5:12 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3917137 | col_h10_r0_p4__t1 | tt_setup_repair_grt | 3.8 | repair_Viol best 1411 last 1411 rows 738 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-2838743 | col_h10_r1__t1 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (1006/1006 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2846210 | col_h10_r1__t1 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (990/990 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv74ebbc00-3105751 | col_h10_r1__t1 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (921/921 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3628147 | col_h10_r1__t1 | 5_1_grt | 1.7 | last meaningful line 0.0 h ago (178/178 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvce76611c-3097921 | col_h10_r1__t1 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (920/920 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3629353 | col_h10_r2__t1 | 5_1_grt | 1.7 | repair_Remaining best 62610 last 62610 rows 26 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-col_h10_r2__t1__clac068e56-3628511 | col_h10_r2__t1 | 5_1_grt | 1.7 | repair_Remaining best 31610 last 31610 rows 57 | YOUNG: stage 0.7 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-3903280 | col_h9_r0_p3__t1 | 5_1_grt | 3.8 | last meaningful line 1.0 h ago (208/220 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p5__t1__pvee6f8140-3629044 | col_h9_r0_p5__t1 | stage_odb_cap | 1.7 | last meaningful line 0.0 h ago (468/468 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv1c15776f-3629501 | col_h9_r1__t1 | 5_1_grt | 1.7 | last meaningful line 0.0 h ago (200/203 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pve273b259-3097415 | col_h9_r1__t1 | 5_1_grt | 2.0 | repair_Remaining best 100306 last 100306 rows 24 | YOUNG: stage 0.8 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_LP__t2-3004885 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 4.2 | repair_TNS best 14.28 last 14.28 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-3937754 | ot_s81sl_leaf__t44 | 5_1_grt | 3.8 | last meaningful line 0.5 h ago (202/207 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-3946553 | ot_s81sl_leaf__t54 | 5_1_grt | 3.8 | last meaningful line 1.0 h ago (200/208 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t15__cla3d02796-2869955 | serdes__t15 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (312/312 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t29__cl2e5c855a-2846396 | slice_station__t29 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (330/330 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t4-2666489 | svc_hi_dsdv_svc_rs__t4 | 2_1_floorplan | 4.3 | repair_Viol best 50584 last 50584 rows 16 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t5-3105046 | svc_hi_dsdv_svc_rs__t5 | 2_1_floorplan | 4.2 | repair_Viol best 55750 last 55750 rows 31 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t6-3103921 | svc_hi_dsdv_svc_rs__t6 | 2_1_floorplan | 4.2 | repair_Viol best 55780 last 55780 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-3017015 | svc_lo_dsdv_svc_rs__t1 | 1_2_yosys | 4.2 | last meaningful line 0.2 h ago (665/665 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t2-2905735 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 4.2 | last meaningful line 0.3 h ago (653/653 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-2277016 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 4.5 | last meaningful line 0.3 h ago (672/672 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | llc-369418-5116173.pin1 | llc-369418-5116173.pin1 | col_h10_r2__t1__cl1f5d6c2a__pvec003743-route-dear-crayfish-378888-1795115423.pin2 | 1.2 | last meaningful line 0.3 h ago (12/12 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_182440_1167722-i1-3155529 | eco_20261119_182440_1167722-i1 | 5_2_route | 2.0 | drt_violations best 4822 last 4822 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_184546_1168863-i1-2177945 | eco_20261119_184546_1168863-i1 | 5_2_route | 0.6 | last meaningful line 0.0 h ago (257/257 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_184643_1170981-i1-721450 | eco_20261119_184643_1170981-i1 | 5_2_route | 1.1 | last meaningful line 0.1 h ago (264/265 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_193300_4163996-i1-3122467 | eco_20261119_193300_4163996-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (146/146 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_194246_4168801-i1-2661476 | eco_20261119_194246_4168801-i1 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (243/1341 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_194719_4168975-i1-1911689 | eco_20261119_194719_4168975-i1 | 5_2_route | 0.8 | last meaningful line 0.0 h ago (258/259 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_194944_478551-i1t-1291719 | eco_20261119_194944_478551-i1t | 5_2_route | 6.4 | drt_violations best 4 last 4 rows 50 | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_195623_475807-i1-2402593 | eco_20261119_195623_475807-i1 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_224849_4166833-i1-701492 | eco_20261119_224849_4166833-i1 | 5_2_route | 3.4 | drt_violations best 52632 last 52632 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003408_3748325-i1-3762223 | eco_20261120_003408_3748325-i1 | 5_1_grt | 1.7 | last meaningful line 1.1 h ago (250/295 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748476-i1-3763736 | eco_20261120_003409_3748476-i1 | 5_1_grt | 1.7 | last meaningful line 1.1 h ago (253/312 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1t-3763698 | eco_20261120_003409_3748726-i1t | 5_1_grt | 1.7 | last meaningful line 1.1 h ago (245/281 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_012809_1875270-i1-1919589 | eco_20261120_012809_1875270-i1 | 5_2_route | 0.8 | drt_violations best 224 last 224 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | prd-eco_20261120_012809_1875451-i1t-1935748 | eco_20261120_012809_1875451-i1t | 5_2_route | 0.8 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-fin-1724745 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (64/64 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q01-767696 | cbf_q01 | 5_2_route | 11.0 | last meaningful line 0.1 h ago (262/263 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-642785 | col_h9_r0_p1__t1 | 5_1_grt | 2.3 | last meaningful line 0.0 h ago (208/209 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv6882e5ea-505829 | col_h9_r0_p2__t1 | 5_1_grt | 2.4 | last meaningful line 0.3 h ago (207/211 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-505081 | col_h9_r0_p2__t1 | 5_1_grt | 2.4 | last meaningful line 0.3 h ago (206/211 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pvd86cb19a-505172 | col_h9_r0_p2__t1 | 5_1_grt | 2.4 | last meaningful line 0.5 h ago (207/213 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-505111 | col_h9_r0_p2__t1 | 5_1_grt | 2.4 | last meaningful line 0.5 h ago (207/211 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pvabc9823e-505736 | col_h9_r0_p2__t1 | 5_1_grt | 2.4 | last meaningful line 0.3 h ago (207/210 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-505237 | col_h9_r0_p4__t1 | 5_1_grt | 2.4 | last meaningful line 0.8 h ago (203/212 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-504263 | col_h9_r0_p4__t1 | 5_1_grt | 2.4 | last meaningful line 0.8 h ago (203/213 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-642825 | col_h9_r0_p5__t1 | 5_1_grt | 2.3 | last meaningful line 0.3 h ago (209/214 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv8995e794-643354 | col_h9_r0_p5__t1 | 5_1_grt | 2.3 | last meaningful line 0.1 h ago (208/211 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pvb22875c0-913556 | col_h9_r0_p5__t1 | 5_1_grt | 2.1 | last meaningful line 0.0 h ago (208/210 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pvbca8d846-643457 | col_h9_r0_p5__t1 | 5_1_grt | 2.3 | last meaningful line 0.1 h ago (208/211 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49f0ba38-263250 | col_h9_r1__t1 | 5_1_grt | 2.7 | repair_Remaining best 25306 last 25306 rows 99 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv87d52780-504670 | col_h9_r1__t1 | 5_1_grt | 2.4 | repair_Remaining best 82306 last 82306 rows 42 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv88891f20-263326 | col_h9_r1__t1 | 5_1_grt | 2.7 | repair_Remaining best 20306 last 20306 rows 104 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8ea75ee5-505402 | col_h9_r1__t1 | 5_1_grt | 2.4 | last meaningful line 0.3 h ago (200/212 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvadbd1880-505510 | col_h9_r1__t1 | 5_1_grt | 2.4 | last meaningful line 0.5 h ago (200/212 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-505372 | col_h9_r1__t1 | 5_1_grt | 2.4 | last meaningful line 0.3 h ago (200/212 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-504529 | col_h9_r1__t1 | 5_1_grt | 2.5 | last meaningful line 0.3 h ago (200/212 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvbb600efe-505577 | col_h9_r1__t1 | 5_1_grt | 2.4 | last meaningful line 0.3 h ago (200/212 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-504463 | col_h9_r1__t1 | 5_1_grt | 2.4 | last meaningful line 0.3 h ago (201/212 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-565125 | serdes__t13 | 3_3_place_gp | 2.4 | overflow best 0.8387 last 0.8387 rows 22 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v2__cle312294d-1508559 | slw_fe_v2 | stage_odb_cap | 1.7 | last meaningful line 0.0 h ago (344/344 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-1279521 | slw_fw_v1 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (360/360 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v2__cl8537f156-3323404 | slw_fw_v2 | 5_2_route | 7.9 | last meaningful line 0.2 h ago (139/139 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl1bc59e1c-1024005 | slw_hc0 | 5_2_route | 10.8 | drt_violations best 103810 last 103810 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-1780810 | slw_hc1 | postcts_gate_FF | 9.8 | last meaningful line 0.0 h ago (854/854 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2997578 | slw_sc_v1 | 5_2_route | 8.3 | last meaningful line 0.1 h ago (133/133 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pvc2ec5bfb-240135 | slw_st_b_v2 | 5_2_route | 11.7 | last meaningful line 0.7 h ago (277/278 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-2618689 | slw_stm_v1 | 5_2_route | 8.8 | last meaningful line 0.7 h ago (132/132 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 11.3 | drt_violations best 17391 last 17391 rows 7 | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-768070 | slw_su_l1 | 5_2_route | 11.0 | drt_violations best 11097 last 11097 rows 11 | YOUNG: evidence 6.4 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-1066664 | tt_ctlm | stage_odb_cap | 6.2 | last meaningful line 0.0 h ago (3326/3326 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-1066712 | tt_ctlm | stage_odb_cap | 6.2 | last meaningful line 0.0 h ago (3292/3292 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-4084399 | tt_ctlm | stage_odb_cap | 3.1 | last meaningful line 0.0 h ago (1400/1400 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-4118116 | tt_ctlm | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (1386/1386 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | ksyn-kv3_pc_v6_keepes-1828369 | ksyn-kv3_pc_v6_keepes | lec | 5.4 | LEC last write 0.0 h ago | YOUNG: evidence 5.4 h < 6 h |  |
| epyc7 | llc-2212797-5139832.pin1 | llc-2212797-5139832.pin1 | 5_2_route | 1.2 | last meaningful line 0.1 h ago (133/133 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | otc-1680355-6756 | 1680355 | lec | 1.6 | LEC last write 0.0 h ago | YOUNG: evidence 1.6 h < 6 h |  |
| epyc7 | otc-1686179-16650 | 1686179 | lec | 1.6 | LEC last write 0.0 h ago | YOUNG: evidence 1.6 h < 6 h |  |
| epyc7 | prd-eco_20261120_083952_3300104-i1t-1853493 | eco_20261120_083952_3300104-i1t | 5_1_grt | 1.5 | last meaningful line 0.7 h ago (141/141 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl870de686-780826 | cbf_q00 | tt_setup_repair_grt | 12.9 | repair_Remaining best 128180 last 128180 rows 140 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | dpkit-cbn_q01__cldd6ea846-4146854 | cbn_q01 | 4_1_cts | 4.2 | last meaningful line 0.0 h ago (5328/5328 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl911743eb-4173007 | col_h10_r0_p1__t1 | 5_1_grt | 4.1 | last meaningful line 0.2 h ago (159/159 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-3326220 | col_h10_r2__t1 | tt_setup_repair_grt | 4.6 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2896534 | col_h10_r2__t1 | tt_setup_repair_grt | 4.8 | repair_Viol best 1389 last 1389 rows 1606 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-828940 | col_h9_r0_p2__t1 | 5_1_grt | 3.8 | last meaningful line 0.3 h ago (207/210 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-422922 | col_h9_r0_p2__t1 | 5_1_grt | 3.9 | last meaningful line 0.3 h ago (207/210 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-826204 | col_h9_r0_p2__t1 | 5_1_grt | 3.8 | last meaningful line 0.3 h ago (208/211 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-834658 | col_h9_r0_p4__t1 | 5_1_grt | 3.8 | last meaningful line 0.8 h ago (203/209 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-4183728 | col_h9_r1__t1 | 5_1_grt | 4.1 | last meaningful line 0.1 h ago (149/149 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-3731937 | col_h9_r1__t1 | 5_1_grt | 4.4 | last meaningful line 0.2 h ago (151/151 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2898480 | col_h9_r2__t1 | tt_setup_repair_grt | 4.8 | repair_Viol best 1454 last 1454 rows 255 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2898962 | col_h9_r2__t1 | tt_setup_repair_grt | 4.8 | repair_Viol best 1470 last 1470 rows 1159 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-2901316 | col_h9_r2__t1 | 5_2_route | 4.8 | last meaningful line 0.2 h ago (133/133 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p2-911752 | kv3_hg_v1p2 | 3_5_place_dp | 3.7 | last meaningful line 0.1 h ago (47/47 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p3-339808 | kv3_hg_v1p3 | 3_4_place_resized | 4.0 | last meaningful line 0.2 h ago (388/388 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p6-275673 | kv3_hg_v1p6 | 3_5_place_dp | 4.0 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v3-354170 | kv3_hg_v3 | 3_5_place_dp | 4.0 | last meaningful line 0.3 h ago (46/46 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v4-670738 | kv3_hgi_v4 | 5_1_grt | 5.8 | last meaningful line 1.0 h ago (210/215 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Eo-393779 | kv3_hub_Eo | 3_3_place_gp | 4.0 | overflow best 0.432 last 0.432 rows 24 | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v1-1207085 | kv3_pv_v1 | 3_3_place_gp | 3.6 | overflow best 0.7678 last 0.7678 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v12-1330096 | kv3_pv_v12 | 3_1_place_gp_skip_io | 3.6 | overflow best 0.1547 last 0.1547 rows 41 | YOUNG: stage 1.0 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v12-3619680 | kv3_pv_v12 | 3_3_place_gp | 6.4 | overflow best 0.0991 last 0.0991 rows 44 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v2-1275856 | kv3_pv_v2 | 3_3_place_gp | 3.6 | last meaningful line 0.3 h ago (35/35 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v2n-880645 | kv3_pv_v2n | 3_3_place_gp | 3.7 | last meaningful line 0.0 h ago (470/470 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3-1202037 | kv3_pv_v3 | 3_3_place_gp | 3.6 | last meaningful line 0.2 h ago (37/37 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3-2271227 | kv3_pv_v3 | 3_5_place_dp | 7.1 | last meaningful line 0.4 h ago (119/119 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3n-2253357 | kv3_pv_v3n | 3_5_place_dp | 7.1 | last meaningful line 0.0 h ago (74/74 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3n-3612346 | kv3_pv_v3n | 3_1_place_gp_skip_io | 2.5 | overflow best 0.9005 last 0.9005 rows 4 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v4-1798134 | kv3_pv_v4 | 3_1_place_gp_skip_io | 3.4 | overflow best 0.1101 last 0.1101 rows 43 | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v5-2012658 | kv3_pv_v5 | 3_1_place_gp_skip_io | 3.3 | overflow best 0.6505 last 0.6505 rows 22 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v5n-2045384 | kv3_pv_v5n | 3_1_place_gp_skip_io | 3.3 | overflow best 0.8169 last 0.8169 rows 10 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v6-1303282 | kv3_pv_v6 | 3_3_place_gp | 3.6 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v7-1908786 | kv3_pv_v7 | 3_4_place_resized | 7.3 | last meaningful line 1.0 h ago (543/543 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v8-1723535 | kv3_pv_v8 | 3_3_place_gp | 3.4 | overflow best 0.6369 last 0.6369 rows 8 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t1-2548759 | ot_s81sl_kv_leaf__t1 | 3_5_place_dp | 3.0 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-2390066 | ot_s81sl_kv_leaf__t4 | 3_4_place_resized | 3.1 | last meaningful line 0.1 h ago (351/351 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3739403 | ot_s81sl_leaf__t25 | 5_1_grt | 4.4 | last meaningful line 0.3 h ago (198/201 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 3.8 | last meaningful line 0.8 h ago (198/205 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-838589 | ot_s81sl_leaf__t53 | 5_1_grt | 3.8 | last meaningful line 0.3 h ago (151/151 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-serdes__t1__clfe1f0815-2617990 | serdes__t1 | 3_3_place_gp | 3.0 | overflow best 0.7838 last 0.7838 rows 23 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-serdes__t2-2062410 | serdes__t2 | 3_4_place_resized | 3.3 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 4_1_cts | 4.8 | last meaningful line 0.1 h ago (6210/6210 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 4_1_cts | 4.8 | last meaningful line 0.3 h ago (6097/6097 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 4_1_cts | 4.1 | last meaningful line 0.2 h ago (73/73 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | pregrt_ff_hold | 5.0 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__clbe630b9c-4044402 | sle_stm_v1 | 5_1_grt | 6.2 | last meaningful line 0.0 h ago (171/171 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l0__cl7a55c676-2377674 | sle_su_l0 | 5_2_route | 5.0 | last meaningful line 0.1 h ago (124/124 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l1__cl5ea486db-3621997 | sle_su_l1 | postcts_gate_FF | 6.4 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t24__cleece78ec-2385680 | slice_station__t24 | 5_2_route | 5.0 | last meaningful line 0.1 h ago (236/237 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t52-2567012 | slice_station__t52 | 5_1_grt | 4.9 | last meaningful line 0.2 h ago (133/133 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t7__cl362204c4-2903658 | slice_station__t7 | 5_2_route | 4.8 | drt_violations best 4118 last 4118 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | pregrt_ff_hold | 5.3 | repair_TNS best 46312.7 last 46312.7 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | 5_1_grt | 6.4 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-3106017 | slw_stm_v2 | pregrt_ff_hold | 4.7 | repair_TNS best 32069.3 last 32069.3 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-slw_su_l0__cl1a1c1f8f-3380863 | slw_su_l0 | 5_2_route | 6.6 | last meaningful line 0.3 h ago (256/257 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t2-3187697 | svc_hi_dsdv_svc_rs__t2 | 1_2_yosys | 2.7 | last meaningful line 0.1 h ago (421/421 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t3-2197154 | svc_hi_dsdv_svc_rs__t3 | 1_2_yosys | 3.2 | last meaningful line 0.3 h ago (457/457 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | llc-2479263-5147859.pin1 | llc-2479263-5147859.pin1 | - | 1.0 |  | NO-DATA: no log found |  |
| intel1 | llc-2479263-5153811.pin1 | llc-2479263-5153811.pin1 | 4_1_cts | 1.0 | last meaningful line 0.2 h ago (73/73 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | llc-2617980-5122312.pin2 | llc-2617980-5122312.pin2 | tt_setup_repair_grt | 0.9 | repair_Remaining best 128180 last 128180 rows 140 | YOUNG: stage 0.6 h < 1 h |  |
| intel1 | objective_cray | objective_cray | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | otc-2295728-27466 | 2295728 | - | 21.6 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261120_003407_1650578-i1-1677571 | eco_20261120_003407_1650578-i1 | 5_1_grt | 1.4 | last meaningful line 0.6 h ago (150/150 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | vigorous_saha | vigorous_saha | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | wizardly_pasteur | wizardly_pasteur | - | 0.0 |  | NO-DATA: no log found |  |
| intel2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-1241882 | col_h9_r0_p1__t1 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (288/288 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel2 | dpkit-coll_ftc-4062937 | coll_ftc | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (345/345 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel2 | dpkit-hd_lep0N-830501 | hd_lep0N | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (322/322 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel2 | dpkit-hd_mesh-4092448 | hd_mesh | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (385/385 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_cor_v1-3099429 | kv3_io_cor_v1 | stage_odb_cap | 6.3 | last meaningful line 0.0 h ago (373/373 lines) | YOUNG: evidence 6.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_sys_c-480894 | kv3_sys_c | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (331/331 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-1118548 | ot_s81sl_kv_leaf__t5 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (479/479 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t10-1107312 | ot_s81sl_leaf__t10 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (467/467 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (515/515 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t58-1113172 | ot_s81sl_leaf__t58 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (435/435 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t68-1111390 | ot_s81sl_leaf__t68 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (403/403 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel2 | dpkit-serdes__t13-1003366 | serdes__t13 | stage_odb_cap | 3.1 | last meaningful line 0.0 h ago (183/183 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel2 | dpkit-serdes__t1__clb45db5be-1142519 | serdes__t1 | 5_1_grt | 3.0 | repair_Remaining best 222335 last 222335 rows 174 | YOUNG: stage 0.9 h < 1 h |  |
| intel2 | dpkit-sle_fw_v2__cl6740750e-482449 | sle_fw_v2 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (331/331 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | stage_odb_cap | 6.2 | last meaningful line 0.0 h ago (443/443 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2444359 | sle_st_b_v1 | postcts_gate_FF | 9.6 | last meaningful line -0.0 h ago (12020/12020 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (331/331 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (331/331 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-489810 | slw_fw_v3 | 5_1_grt | 5.6 | repair_Remaining best 369638 last 369638 rows 9 | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | 5_1_grt | 5.8 | last meaningful line 0.9 h ago (231/868 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (331/331 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-495397 | slw_st_b_v2 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (331/331 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-498208 | slw_st_b_v2 | stage_odb_cap | 5.5 | last meaningful line 0.0 h ago (330/330 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t1-1341320 | svc_hi_dsdv_svc_pvso_entry__t1 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (170/170 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-1267600 | svc_hi_dsdv_svc_rs__t1 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (172/172 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel2 | dpkit-svc_lo_dsdv_svc_rs__t5-448347 | svc_lo_dsdv_svc_rs__t5 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (331/331 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel2 | prd-fin-3397066 | fin | 6_report | 0.3 | last meaningful line 0.1 h ago (1065/1065 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-372309 | col_h10_r1__t1 | 5_1_grt | 15.1 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 15.1 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t7-2914199 | dsdv_slice_c1x_C__t7 | 5_1_grt | 24.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-2585815 | dsdv_slice_lepe_mu_LP__t2 | stage_odb_cap | 32.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hg_v1p6-1282096 | kv3_hg_v1p6 | 5_1_grt | 33.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v1__cl141fc26e-558101 | kv3_hgi_v1 | 5_1_grt | 49.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v1__cl42bc8b12-557506 | kv3_hgi_v1 | 5_1_grt | 49.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v3-1645316 | kv3_hgi_v3 | 5_1_grt | 33.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl254f2e73-3798670 | kv3_pc | tt_setup_repair_grt | 62.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc_v1__cl23f6a148-3798940 | kv3_pc_v1 | 5_1_grt | 62.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc_v1__cl7f648944-3798924 | kv3_pc_v1 | 5_1_grt | 62.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pv_v8-2521551 | kv3_pv_v8 | 5_1_grt | 32.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t4-3460836 | dsdv_slice_c1x_C__t4 | 5_1_grt | 24.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 49.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_pc_v3-2166515 | kv3_pc_v3 | 5_1_grt | 48.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | stage_odb_cap | 25.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | stage_odb_cap | 26.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 66.5 | last meaningful line 0.9 h ago (1624/1624 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-382185 | col_h10_r2__t1 | 5_2_route | 15.1 | drt_violations best 99 last 99 rows 30 | before-window best 4998, window best 99 | PROGRESS: drt_violations improved 98.0 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-384874 | col_h10_r2__t1 | 5_2_route | 15.1 | drt_violations best 99 last 99 rows 30 | before-window best 5912, window best 99 | PROGRESS: drt_violations improved 98.3 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-385072 | col_h10_r2__t1 | 5_2_route | 15.1 | drt_violations best 99 last 99 rows 30 | before-window best 4998, window best 99 | PROGRESS: drt_violations improved 98.0 % in window |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-3012090 | dsdv_slice_lepw_mus_LP__t2 | pregrt_ff_hold | 4.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-191709 | slw_fw_v1 | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-195673 | slw_fw_v1 | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | llc-369418-5150620.pin1 | llc-369418-5150620.pin1 | pregrt_ff_hold | 1.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-3455838 | cbn_q01 | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_ctl__cl67434795__padW5-3154753 | sle_ctl | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3298474 | sle_sc_v1 | 5_2_route | 12.8 | drt_violations best 24640 last 24640 rows 2 | before-window best 148257, window best 24640 | PROGRESS: drt_violations improved 83.4 % in window |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cle683a076-2387979 | slw_hc1 | 5_1_grt | 9.1 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-tt_ctlm-426389 | tt_ctlm | stage_odb_cap | 6.9 | last meaningful line 0.0 h ago (3753/3753 lines) | PROGRESS: log still growing |  |
| epyc7 | klegacy-dsdv_bksel_c_rfdqctl-1318076 | dsdv_bksel_c_rfdqctl | 4_1_cts | 1.8 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | klegacy-dsdv_bksel_c_rfdqctl-1318076-lec | dsdv_bksel_c_rfdqctl | 4_1_cts | 1.6 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | llc-2387163-5155490.pin2 | llc-2387163-5155490.pin2 | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-cbf_q11-2627513 | cbf_q11 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-cbn_q00__cldbcda913-3330181 | cbn_q00 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | pregrt_ff_hold | 7.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-cbx_q10__cl89936551-3322021 | cbx_q10 | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-cbx_q10__cl89936551_h-2365139 | cbx_q10 | pregrt_ff_hold | 5.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-1305862 | col_h9_r0_p1__t1 | pregrt_ff_hold | 3.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-2349309 | col_h9_r0_p3__t1 | pregrt_ff_hold | 3.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2622406 | col_h9_r0_p3__t1 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2628597 | col_h9_r0_p3__t1 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r2__t1__clb8d86cd5__pv982ec12c-2337034 | col_h9_r2__t1 | 5_2_route | 14.8 | drt_violations best 66 last 66 rows 12 | before-window best 3655, window best 66 | PROGRESS: drt_violations improved 98.2 % in window |  |
| intel1 | dpkit-sle_stm_v2__cl7b3062fa-694049 | sle_stm_v2 | pregrt_ff_hold | 5.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | pregrt_ff_hold | 6.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | pregrt_ff_hold | 6.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-842919 | slw_st_b_v1 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t7-888978 | svc_lo_dsdv_svc_rs__t7 | 2_1_floorplan | 16.0 | last meaningful line 0.8 h ago (1375/1375 lines) | PROGRESS: log still growing |  |
| intel1 | llc-2617980-5152274.pin2 | llc-2617980-5152274.pin2 | pregrt_ff_hold | 1.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | prd-eco_20261120_003409_1651933-i1t-1681241 | eco_20261120_003409_1651933-i1t | 5_1_grt | 1.4 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 12.4 | last meaningful line 0.0 h ago (741/741 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t3-1117539 | dsdv_slice_c1x_C__t3 | stage_odb_cap | 19.5 | last meaningful line 0.0 h ago (1116/1116 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_C__t1-1117806 | dsdv_slice_lepe_mu_C__t1 | stage_odb_cap | 19.5 | last meaningful line 0.0 h ago (1116/1116 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-glue-4013867 | glue | stage_odb_cap | 8.2 | last meaningful line 0.0 h ago (547/547 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 7.5 | last meaningful line 0.0 h ago (463/463 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-1602787 | hd_mesh | stage_odb_cap | 7.0 | last meaningful line 0.0 h ago (466/466 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_hc0__cl05696ed1-1266312 | sle_hc0 | stage_odb_cap | 10.9 | last meaningful line 0.0 h ago (699/699 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_hc0__cl929603c0__cl38badc56-1455458 | sle_hc0 | stage_odb_cap | 10.7 | last meaningful line 0.0 h ago (692/692 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c-1455485 | sle_hc0 | stage_odb_cap | 10.7 | last meaningful line 0.0 h ago (703/703 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2435819 | slw_hc1 | stage_odb_cap | 6.6 | last meaningful line 0.0 h ago (455/455 lines) | PROGRESS: log still growing |  |
