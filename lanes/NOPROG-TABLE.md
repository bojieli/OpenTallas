# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 01:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'GRT-LABEL': 12, 'YOUNG': 193, 'NO-DATA': 3, 'KEEP': 2, 'EXCLUDED': 15, 'PROGRESS': 40}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| intel1 | dpkit-slw_fw_v2__cl8f84514c-2549308 | slw_fw_v2 | 5_2_route | 14.4 | drt_violations best 85626 last 85626 rows 1 | before-window best 85626, window best 85626 | NO-PROGRESS: drt_violations best 85626 vs 85626 before window: < 2 % in 7.5 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-2436381 | dsdv_slice_c1x_C__t10 | 5_1_grt | 22.5 | grt rounds 2 overflow 5:66206 -> 10:63889 | GRT-LABEL: DESIGN-FAIL: overflow 63889 at round 10 > 1000 |  |
| epyc2 | dpkit-ot_s81sl_leaf__t3-871532 | ot_s81sl_leaf__t3 | 5_1_grt | 14.4 | grt rounds 6 overflow 5:23964 -> 10:331 -> 15:68 -> 20:58 -> 25:58 -> 30:28 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t34-502720 | ot_s81sl_leaf__t34 | 5_1_grt | 14.5 | grt rounds 4 overflow 5:39901 -> 10:35125 -> 15:32751 -> 20:33511 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-517470 | ot_s81sl_leaf__t4 | 5_1_grt | 14.5 | grt rounds 3 overflow 5:33299 -> 10:24430 -> 15:21822 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | llc-369418-5116173.pin1 | llc-369418-5116173.pin1 | 5_1_grt | 0.7 | grt rounds 6 overflow 5:23964 -> 10:331 -> 15:68 -> 20:58 -> 25:58 -> 30:28 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-col_h10_r1__t1__cld01bb4ae-2998457 | col_h10_r1__t1 | 5_1_grt | 12.6 | grt rounds 4 overflow 5:49459 -> 10:15428 -> 15:4782 -> 20:3465 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-coll_core-532020 | coll_core | 5_1_grt | 10.8 | grt rounds 3 overflow 5:41395 -> 10:31221 -> 15:29694 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | llc-2212797-5048104.pin1 | llc-2212797-5048104.pin1 | 5_1_grt | 0.7 | grt rounds 3 overflow 5:41051 -> 10:42286 -> 15:35874 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | llc-2212797-5049283.pin1 | llc-2212797-5049283.pin1 | 5_1_grt | 0.4 | grt rounds 6 overflow 5:23589 -> 10:21148 -> 15:17728 -> 20:6878 -> 25:11843 -> 30:8123 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 127.7 | grt rounds 6 overflow 5:3621 -> 10:1409 -> 15:822 -> 20:367 -> 25:132 -> 30:21 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 127.7 | grt rounds 6 overflow 5:3459 -> 10:2012 -> 15:1178 -> 20:769 -> 25:322 -> 30:29 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 12.6 | grt rounds 3 overflow 5:55253 -> 10:43864 -> 15:40285 | GRT-LABEL: DESIGN-FAIL: overflow 43864 at round 10 > 1000 |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3917137 | col_h10_r0_p4__t1 | 5_1_grt | 3.3 | last meaningful line 0.2 h ago (237/439 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-2838743 | col_h10_r1__t1 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (706/706 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2846210 | col_h10_r1__t1 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (700/700 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv74ebbc00-3105751 | col_h10_r1__t1 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (621/621 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3628147 | col_h10_r1__t1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (434/434 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvce76611c-3097921 | col_h10_r1__t1 | stage_odb_cap | 1.5 | last meaningful line 0.0 h ago (630/630 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3629353 | col_h10_r2__t1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (540/540 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__clac068e56-3628511 | col_h10_r2__t1 | 5_1_grt | 1.2 | last meaningful line 0.0 h ago (197/200 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-3903280 | col_h9_r0_p3__t1 | 5_1_grt | 3.3 | last meaningful line 0.5 h ago (208/214 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p5__t1__pvee6f8140-3629044 | col_h9_r0_p5__t1 | 5_1_grt | 1.2 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pve273b259-3097415 | col_h9_r1__t1 | 5_1_grt | 1.5 | last meaningful line 0.1 h ago (200/203 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-2535259 | dsdv_slice_lepe_nh_mus_C__t1 | stage_odb_cap | 3.9 | last meaningful line 0.0 h ago (336/336 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-2827044 | dsdv_slice_lepw_mu_C__t1 | 3_4_place_resized | 3.8 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_LP__t2-3004885 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 3.7 | repair_TNS best 19128 last 19128 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-3012090 | dsdv_slice_lepw_mus_LP__t2 | stage_odb_cap | 3.7 | last meaningful line 2.3 h ago (347/347 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-eng__t1-1985070 | eng__t1 | postcts_gate_TT | 4.1 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-iqf__t1-1986835 | iqf__t1 | postcts_gate_TT | 4.1 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-3937754 | ot_s81sl_leaf__t44 | 5_1_grt | 3.3 | last meaningful line 0.0 h ago (202/203 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-3946553 | ot_s81sl_leaf__t54 | 5_1_grt | 3.3 | last meaningful line 0.5 h ago (200/206 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t15__cla3d02796-2869955 | serdes__t15 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (192/192 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t29__cl2e5c855a-2846396 | slice_station__t29 | postcts_gate_FF | 1.6 | last meaningful line -0.0 h ago (10573/10573 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t4-2666489 | svc_hi_dsdv_svc_rs__t4 | reg_fanout | 3.8 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t5-3105046 | svc_hi_dsdv_svc_rs__t5 | synth_odb_v | 3.7 | last meaningful line 0.1 h ago (4/4 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t6-3103921 | svc_hi_dsdv_svc_rs__t6 | port_bind | 3.7 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-3017015 | svc_lo_dsdv_svc_rs__t1 | 1_2_yosys | 3.7 | last meaningful line 0.1 h ago (633/633 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t2-2905735 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 3.7 | last meaningful line 0.0 h ago (643/643 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-2277016 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 4.0 | last meaningful line 0.0 h ago (668/668 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | llc-503912-5115423.pin2 | llc-503912-5115423.pin2 | 5_2_route | 0.0 | drt_violations best 148 last 148 rows 25 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | prd-eco_20261119_182440_1167722-i1-3155529 | eco_20261119_182440_1167722-i1 | 5_2_route | 1.5 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_184546_1168863-i1-2177945 | eco_20261119_184546_1168863-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_184643_1170981-i1-721450 | eco_20261119_184643_1170981-i1 | 5_2_route | 0.6 | last meaningful line 0.0 h ago (257/257 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_193300_4163996-i1t-764001 | eco_20261119_193300_4163996-i1t | 5_2_route | 6.2 | drt_violations best 12 last 12 rows 42 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_194719_4168975-i1-1911689 | eco_20261119_194719_4168975-i1 | 5_1_grt | 0.3 | last meaningful line 0.2 h ago (243/1266 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_194944_478551-i1t-1291719 | eco_20261119_194944_478551-i1t | 5_2_route | 5.9 | drt_violations best 24 last 24 rows 12 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_195623_475807-i1-2402593 | eco_20261119_195623_475807-i1 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_195829_480745-i1t-1724745 | eco_20261119_195829_480745-i1t | 5_2_route | 5.7 | drt_violations best 16 last 16 rows 10 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_224849_4166833-i1-701492 | eco_20261119_224849_4166833-i1 | 5_2_route | 2.9 | drt_violations best 52632 last 52632 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003408_3748325-i1-3762223 | eco_20261120_003408_3748325-i1 | 5_1_grt | 1.2 | last meaningful line 0.6 h ago (250/295 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748476-i1-3763736 | eco_20261120_003409_3748476-i1 | 5_1_grt | 1.2 | last meaningful line 0.6 h ago (253/312 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1t-3763698 | eco_20261120_003409_3748726-i1t | 5_1_grt | 1.2 | last meaningful line 0.6 h ago (245/281 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_012809_1875270-i1-1919589 | eco_20261120_012809_1875270-i1 | 5_2_route | 0.3 | last meaningful line 0.0 h ago (217/218 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_012809_1875451-i1t-1935748 | eco_20261120_012809_1875451-i1t | 5_2_route | 0.3 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-fin-1040055 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (49/49 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q01-767696 | cbf_q01 | 5_2_route | 10.5 | last meaningful line 0.9 h ago (138/138 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-642785 | col_h9_r0_p1__t1 | 5_1_grt | 1.8 | last meaningful line 0.1 h ago (153/153 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv6882e5ea-505829 | col_h9_r0_p2__t1 | 5_1_grt | 1.9 | last meaningful line 0.2 h ago (156/156 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-505081 | col_h9_r0_p2__t1 | 5_1_grt | 1.9 | last meaningful line 0.3 h ago (156/156 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pvd86cb19a-505172 | col_h9_r0_p2__t1 | 5_1_grt | 1.9 | last meaningful line 0.1 h ago (207/208 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-505111 | col_h9_r0_p2__t1 | 5_1_grt | 1.9 | last meaningful line 0.1 h ago (207/208 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pvabc9823e-505736 | col_h9_r0_p2__t1 | 5_1_grt | 1.9 | last meaningful line 0.2 h ago (157/157 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-263184 | col_h9_r0_p4__t1 | 5_1_grt | 2.2 | last meaningful line 1.0 h ago (203/215 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-263121 | col_h9_r0_p4__t1 | 5_1_grt | 2.2 | last meaningful line 1.0 h ago (203/216 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-505237 | col_h9_r0_p4__t1 | 5_1_grt | 1.9 | last meaningful line 0.3 h ago (203/207 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-504263 | col_h9_r0_p4__t1 | 5_1_grt | 1.9 | last meaningful line 0.3 h ago (203/208 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-642825 | col_h9_r0_p5__t1 | 5_1_grt | 1.8 | last meaningful line 0.1 h ago (159/159 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv8995e794-643354 | col_h9_r0_p5__t1 | 5_1_grt | 1.8 | last meaningful line 0.2 h ago (156/156 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pvb22875c0-913556 | col_h9_r0_p5__t1 | 5_1_grt | 1.6 | last meaningful line 0.1 h ago (151/151 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pvbca8d846-643457 | col_h9_r0_p5__t1 | 5_1_grt | 1.8 | last meaningful line 0.1 h ago (156/156 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4593e8e5-263606 | col_h9_r1__t1 | 5_1_grt | 2.2 | last meaningful line 0.3 h ago (200/208 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv461b5256-264100 | col_h9_r1__t1 | 5_1_grt | 2.2 | last meaningful line 0.5 h ago (200/212 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49f0ba38-263250 | col_h9_r1__t1 | 5_1_grt | 2.2 | last meaningful line 0.3 h ago (200/206 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv5ffbfb8b-264037 | col_h9_r1__t1 | 5_1_grt | 2.2 | last meaningful line 0.3 h ago (200/209 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv7466df46-263651 | col_h9_r1__t1 | 5_1_grt | 2.2 | last meaningful line 0.3 h ago (200/208 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv87d52780-504670 | col_h9_r1__t1 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (200/204 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv88891f20-263326 | col_h9_r1__t1 | 5_1_grt | 2.2 | last meaningful line 0.3 h ago (200/208 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8ea75ee5-505402 | col_h9_r1__t1 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (179/179 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvadbd1880-505510 | col_h9_r1__t1 | 5_1_grt | 1.9 | last meaningful line 0.1 h ago (186/199 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-505372 | col_h9_r1__t1 | 5_1_grt | 1.9 | last meaningful line 0.1 h ago (149/149 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvb2dac3cf-504529 | col_h9_r1__t1 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (179/179 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvbb600efe-505577 | col_h9_r1__t1 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (181/181 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__clf32cde8d__pv63f488e9-504463 | col_h9_r1__t1 | 5_1_grt | 1.9 | last meaningful line 0.2 h ago (150/150 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-565125 | serdes__t13 | 3_3_place_gp | 1.9 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cl67434795__padW5-3154753 | sle_ctl | tt_setup_repair | 3.4 | repair_Violations best 535 last 568 rows 75 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-sle_fw_v2__cl69f5e854-1519412 | sle_fw_v2 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (216/216 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__clbe630b9c-1471474 | sle_stm_v1 | 3_5_place_dp | 1.2 | last meaningful line -0.0 h ago (69/69 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v2__cl55be2264-1517063 | sle_stm_v2 | 3_5_place_dp | 1.2 | last meaningful line -0.0 h ago (9/9 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v2__cl7b3062fa-1309127 | sle_stm_v2 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (232/232 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-1311283 | slw_fe_v1 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (244/244 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v2__cle312294d-1508559 | slw_fe_v2 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (228/228 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1505946 | slw_fe_v2 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (224/224 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__cl51d45468-1491786 | slw_fw_v1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (216/216 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-1279521 | slw_fw_v1 | 3_3_place_gp | 1.3 | overflow best 0.0997 last 0.0997 rows 42 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v2__cl8537f156-3323404 | slw_fw_v2 | 5_2_route | 7.4 | last meaningful line 0.1 h ago (136/136 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v3-1493304 | slw_fw_v3 | 3_4_place_resized | 1.2 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl1bc59e1c-1024005 | slw_hc0 | 5_2_route | 10.3 | drt_violations best 103810 last 103810 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-1780810 | slw_hc1 | postcts_gate_TT | 9.3 | last meaningful line -0.0 h ago (63152/63152 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cle683a076-2387979 | slw_hc1 | 5_1_grt | 8.6 | last meaningful line 0.0 h ago (167/167 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-1385105 | slw_sc_v1 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (252/252 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2997578 | slw_sc_v1 | postcts_gate_FF | 7.8 | last meaningful line -0.0 h ago (30898/30898 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-1322537 | slw_sc_v1 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pvc2ec5bfb-240135 | slw_st_b_v2 | 5_2_route | 11.2 | last meaningful line 1.0 h ago (275/276 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-2618689 | slw_stm_v1 | 5_2_route | 8.3 | last meaningful line 0.3 h ago (131/131 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 10.8 | drt_violations best 18123 last 18123 rows 6 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-768070 | slw_su_l1 | 5_2_route | 10.5 | drt_violations best 13874 last 13874 rows 10 | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-1066664 | tt_ctlm | stage_odb_cap | 5.7 | last meaningful line 0.0 h ago (3026/3026 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-1066712 | tt_ctlm | stage_odb_cap | 5.7 | last meaningful line 0.0 h ago (2994/2994 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-4084399 | tt_ctlm | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (1100/1100 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-4118116 | tt_ctlm | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (1086/1086 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | klegacy-dsdv_bksel_c_rfdqctl-1318076 | dsdv_bksel_c_rfdqctl | 3_3_place_gp | 1.3 | overflow best 0.2977 last 0.4075 rows 194 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | klegacy-dsdv_bksel_c_rfdqctl-1318076-lec | dsdv_bksel_c_rfdqctl | 3_3_place_gp | 1.1 | overflow best 0.2977 last 0.4075 rows 194 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | ksyn-kv3_pc_v6_keepes-1828369 | ksyn-kv3_pc_v6_keepes | lec | 4.9 | LEC last write 0.1 h ago | YOUNG: evidence 4.9 h < 6 h |  |
| epyc7 | llc-2212797-5139832.pin1 | llc-2212797-5139832.pin1 | postcts_gate_FF | 0.7 | last meaningful line -0.0 h ago (30444/30444 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | llc-2387163-5155490.pin2 | llc-2387163-5155490.pin2 | tt_setup_repair | 0.2 | repair_Violations best 535 last 568 rows 75 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | otc-1680355-6756 | 1680355 | lec | 1.1 | LEC last write 0.0 h ago | YOUNG: evidence 1.1 h < 6 h |  |
| epyc7 | otc-1686179-16650 | 1686179 | lec | 1.1 | LEC last write 0.1 h ago | YOUNG: evidence 1.1 h < 6 h |  |
| epyc7 | prd-eco_20261120_083952_3300104-i1t-1853493 | eco_20261120_083952_3300104-i1t | 5_1_grt | 1.0 | last meaningful line 0.3 h ago (140/140 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl870de686-780826 | cbf_q00 | tt_setup_repair_grt | 12.7 | repair_Remaining best 215180 last 215180 rows 53 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-cbn_q01__cldd6ea846-4146854 | cbn_q01 | 4_1_cts | 3.9 | last meaningful line 0.0 h ago (74/74 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl911743eb-4173007 | col_h10_r0_p1__t1 | 5_1_grt | 3.9 | last meaningful line 0.1 h ago (156/156 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2896534 | col_h10_r2__t1 | tt_setup_repair_grt | 4.5 | repair_Viol best 1389 last 1389 rows 934 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-828940 | col_h9_r0_p2__t1 | 5_1_grt | 3.5 | last meaningful line 0.1 h ago (207/208 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-422922 | col_h9_r0_p2__t1 | 5_1_grt | 3.7 | last meaningful line 0.1 h ago (207/208 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-826204 | col_h9_r0_p2__t1 | 5_1_grt | 3.5 | last meaningful line 0.1 h ago (208/209 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-834658 | col_h9_r0_p4__t1 | 5_1_grt | 3.5 | last meaningful line 0.5 h ago (203/207 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-4183728 | col_h9_r1__t1 | 5_1_grt | 3.9 | last meaningful line 0.2 h ago (145/145 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-3731937 | col_h9_r1__t1 | 5_1_grt | 4.1 | last meaningful line 0.1 h ago (149/149 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2898480 | col_h9_r2__t1 | 5_1_grt | 4.5 | last meaningful line 0.0 h ago (428/434 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2898962 | col_h9_r2__t1 | tt_setup_repair_grt | 4.5 | repair_Viol best 1470 last 1470 rows 423 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-2901316 | col_h9_r2__t1 | postcts_gate_FF | 4.5 | last meaningful line 0.0 h ago (17935/17935 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p2-911752 | kv3_hg_v1p2 | 3_4_place_resized | 3.5 | last meaningful line 0.0 h ago (387/387 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p3-339808 | kv3_hg_v1p3 | 3_3_place_gp | 3.7 | overflow best 0.0985 last 0.0985 rows 45 | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p6-275673 | kv3_hg_v1p6 | 3_4_place_resized | 3.8 | repair_Remaining best 145873 last 145873 rows 181 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_hg_v3-354170 | kv3_hg_v3 | 3_5_place_dp | 3.7 | last meaningful line 0.2 h ago (46/46 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v4-670738 | kv3_hgi_v4 | 5_1_grt | 5.6 | last meaningful line 0.8 h ago (210/214 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Eo-393779 | kv3_hub_Eo | 3_3_place_gp | 3.7 | overflow best 0.5387 last 0.5387 rows 10 | YOUNG: stage 0.9 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v1-1207085 | kv3_pv_v1 | 3_3_place_gp | 3.4 | last meaningful line 0.3 h ago (38/38 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-1330096 | kv3_pv_v12 | 3_1_place_gp_skip_io | 3.3 | overflow best 0.4848 last 0.4848 rows 29 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v12-3619680 | kv3_pv_v12 | 3_3_place_gp | 6.2 | overflow best 0.0991 last 0.0991 rows 44 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v2-1275856 | kv3_pv_v2 | 3_3_place_gp | 3.3 | last meaningful line 0.2 h ago (35/35 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v2n-880645 | kv3_pv_v2n | 3_3_place_gp | 3.5 | last meaningful line 0.5 h ago (36/36 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3-1202037 | kv3_pv_v3 | 3_3_place_gp | 3.4 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3-2271227 | kv3_pv_v3 | 3_5_place_dp | 6.8 | last meaningful line 0.2 h ago (119/119 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3n-2253357 | kv3_pv_v3n | 3_4_place_resized | 6.9 | last meaningful line 0.8 h ago (668/668 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3n-3612346 | kv3_pv_v3n | 2_4_floorplan_pdn | 2.3 | last meaningful line 0.3 h ago (93/93 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v4-1798134 | kv3_pv_v4 | 3_1_place_gp_skip_io | 3.1 | overflow best 0.2886 last 0.2886 rows 33 | YOUNG: stage 0.8 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v5-2012658 | kv3_pv_v5 | 3_1_place_gp_skip_io | 3.0 | overflow best 0.8048 last 0.8048 rows 9 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v5n-2045384 | kv3_pv_v5n | 2_4_floorplan_pdn | 3.0 | last meaningful line 0.1 h ago (94/94 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v6-1303282 | kv3_pv_v6 | 3_1_place_gp_skip_io | 3.3 | overflow best 0.3132 last 0.3132 rows 33 | YOUNG: stage 0.7 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v7-1908786 | kv3_pv_v7 | 3_4_place_resized | 7.0 | last meaningful line 0.8 h ago (543/543 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v8-1723535 | kv3_pv_v8 | 3_3_place_gp | 3.2 | overflow best 0.7198 last 0.7198 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t1-2548759 | ot_s81sl_kv_leaf__t1 | 3_4_place_resized | 2.8 | repair_Remaining best 185312 last 185312 rows 101 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t4-2390066 | ot_s81sl_kv_leaf__t4 | 3_3_place_gp | 2.9 | overflow best 0.3678 last 0.3678 rows 35 | YOUNG: stage 1.0 h < 1 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3739403 | ot_s81sl_leaf__t25 | 5_1_grt | 4.1 | last meaningful line 0.0 h ago (198/199 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 3.5 | last meaningful line 0.5 h ago (198/204 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-838589 | ot_s81sl_leaf__t53 | 5_1_grt | 3.5 | last meaningful line 0.1 h ago (150/150 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-serdes__t1__clfe1f0815-2617990 | serdes__t1 | 3_3_place_gp | 2.8 | overflow best 0.8196 last 0.8196 rows 7 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | dpkit-serdes__t2-2062410 | serdes__t2 | 3_3_place_gp | 3.0 | overflow best 0.6456 last 0.6456 rows 32 | YOUNG: stage 0.8 h < 1 h |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 4_1_cts | 4.5 | last meaningful line 0.3 h ago (6191/6191 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 4_1_cts | 4.5 | last meaningful line 0.2 h ago (6096/6096 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 4_1_cts | 3.9 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | 4_1_cts | 4.8 | last meaningful line 0.2 h ago (4393/4393 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l0__cl7a55c676-2377674 | sle_su_l0 | postcts_gate_FF | 4.8 | last meaningful line 0.0 h ago (450/450 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l1__cl5ea486db-3621997 | sle_su_l1 | tt_setup_repair_grt | 6.2 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t24__cleece78ec-2385680 | slice_station__t24 | 5_2_route | 4.8 | last meaningful line 0.5 h ago (232/233 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t52-2567012 | slice_station__t52 | 5_1_grt | 4.7 | last meaningful line 0.1 h ago (131/131 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t7__cl362204c4-2903658 | slice_station__t7 | 5_2_route | 4.5 | last meaningful line 0.4 h ago (239/240 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | pregrt_ff_hold | 5.1 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | 5_1_grt | 6.2 | last meaningful line 0.1 h ago (136/136 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-3106017 | slw_stm_v2 | pregrt_ff_hold | 4.4 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1a1c1f8f-3380863 | slw_su_l0 | 5_2_route | 6.3 | last meaningful line 0.5 h ago (254/255 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t2-3187697 | svc_hi_dsdv_svc_rs__t2 | 1_2_yosys | 2.5 | last meaningful line 0.0 h ago (414/414 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t3-2197154 | svc_hi_dsdv_svc_rs__t3 | 1_2_yosys | 2.9 | last meaningful line 0.0 h ago (457/457 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | llc-2479263-5147859.pin1 | llc-2479263-5147859.pin1 | - | 0.7 |  | NO-DATA: no log found |  |
| intel1 | llc-2479263-5153811.pin1 | llc-2479263-5153811.pin1 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (67/67 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | llc-2617980-5122312.pin2 | llc-2617980-5122312.pin2 | tt_setup_repair_grt | 0.7 | repair_Remaining best 215180 last 215180 rows 53 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | otc-2295728-27466 | 2295728 | - | 21.4 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261120_003407_1650578-i1-1677571 | eco_20261120_003407_1650578-i1 | 5_1_grt | 1.2 | last meaningful line 0.3 h ago (150/150 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | prd-eco_20261120_003409_1651933-i1t-1681241 | eco_20261120_003409_1651933-i1t | 5_1_grt | 1.2 | last meaningful line 0.5 h ago (155/155 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-1241882 | col_h9_r0_p1__t1 | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (258/258 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-coll_ftc-4062937 | coll_ftc | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (315/315 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel2 | dpkit-hd_lep0N-830501 | hd_lep0N | stage_odb_cap | 4.9 | last meaningful line 0.0 h ago (292/292 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel2 | dpkit-hd_mesh-1602787 | hd_mesh | stage_odb_cap | 6.5 | last meaningful line 0.0 h ago (436/436 lines) | YOUNG: evidence 6.5 h < 7.5 h |  |
| intel2 | dpkit-hd_mesh-4092448 | hd_mesh | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (356/356 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_cor_v1-3099429 | kv3_io_cor_v1 | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (343/343 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel2 | dpkit-kv3_sys_c-480894 | kv3_sys_c | stage_odb_cap | 5.1 | last meaningful line 0.0 h ago (301/301 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t10-1107312 | ot_s81sl_leaf__t10 | 5_1_grt | 2.5 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (485/485 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t58-1113172 | ot_s81sl_leaf__t58 | pregrt_ff_hold | 2.5 | repair_Violations best 6988 last 7015 rows 151 | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t68-1111390 | ot_s81sl_leaf__t68 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (373/373 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel2 | dpkit-serdes__t13-1003366 | serdes__t13 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (154/154 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel2 | dpkit-serdes__t14-1137423 | serdes__t14 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (287/287 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel2 | dpkit-serdes__t1__clb45db5be-1142519 | serdes__t1 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (289/289 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl6740750e-482449 | sle_fw_v2 | stage_odb_cap | 5.1 | last meaningful line 0.0 h ago (301/301 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | stage_odb_cap | 5.7 | last meaningful line 0.0 h ago (413/413 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c-1455485 | sle_hc0 | 5_2_route | 10.2 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 5.1 | last meaningful line 0.0 h ago (301/301 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | stage_odb_cap | 5.1 | last meaningful line 0.0 h ago (301/301 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-489810 | slw_fw_v3 | stage_odb_cap | 5.1 | last meaningful line 0.0 h ago (301/301 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (315/315 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | stage_odb_cap | 5.1 | last meaningful line 0.0 h ago (301/301 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-495397 | slw_st_b_v2 | stage_odb_cap | 5.1 | last meaningful line 0.0 h ago (301/301 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-498208 | slw_st_b_v2 | stage_odb_cap | 5.0 | last meaningful line 0.0 h ago (301/301 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t1-1341320 | svc_hi_dsdv_svc_pvso_entry__t1 | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-1267600 | svc_hi_dsdv_svc_rs__t1 | 1_2_yosys | 2.4 | last meaningful line 0.0 h ago (477/477 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-svc_lo_dsdv_svc_rs__t5-448347 | svc_lo_dsdv_svc_rs__t5 | stage_odb_cap | 5.1 | last meaningful line 0.0 h ago (301/301 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel2 | prd-count-p1_tc-3397066 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-372309 | col_h10_r1__t1 | 5_1_grt | 14.6 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 14.6 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t7-2914199 | dsdv_slice_c1x_C__t7 | 5_1_grt | 24.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-2585815 | dsdv_slice_lepe_mu_LP__t2 | stage_odb_cap | 32.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hg_v1p6-1282096 | kv3_hg_v1p6 | 5_1_grt | 33.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v1__cl141fc26e-558101 | kv3_hgi_v1 | 5_1_grt | 48.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v1__cl42bc8b12-557506 | kv3_hgi_v1 | 5_1_grt | 48.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v3-1645316 | kv3_hgi_v3 | 5_1_grt | 32.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl254f2e73-3798670 | kv3_pc | 5_1_grt | 62.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc_v1__cl23f6a148-3798940 | kv3_pc_v1 | 5_1_grt | 62.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc_v1__cl7f648944-3798924 | kv3_pc_v1 | 5_1_grt | 62.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pv_v8-2521551 | kv3_pv_v8 | 5_1_grt | 32.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t4-3460836 | dsdv_slice_c1x_C__t4 | 5_1_grt | 23.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 49.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_pc_v3-2166515 | kv3_pc_v3 | 5_1_grt | 48.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | stage_odb_cap | 24.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | stage_odb_cap | 25.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 66.0 | last meaningful line 0.4 h ago (1624/1624 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-382185 | col_h10_r2__t1 | 5_2_route | 14.6 | drt_violations best 148 last 148 rows 25 | before-window best 5476, window best 148 | PROGRESS: drt_violations improved 97.3 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-384874 | col_h10_r2__t1 | 5_2_route | 14.6 | drt_violations best 148 last 148 rows 26 | before-window best 6513, window best 148 | PROGRESS: drt_violations improved 97.7 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-385072 | col_h10_r2__t1 | 5_2_route | 14.6 | drt_violations best 148 last 148 rows 25 | before-window best 5912, window best 148 | PROGRESS: drt_violations improved 97.5 % in window |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv1c15776f-3629501 | col_h9_r1__t1 | pregrt_ff_hold | 1.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-191709 | slw_fw_v1 | pregrt_ff_hold | 4.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-195673 | slw_fw_v1 | pregrt_ff_hold | 4.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | llc-369418-5150620.pin1 | llc-369418-5150620.pin1 | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-3455838 | cbn_q01 | pregrt_ff_hold | 3.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3298474 | sle_sc_v1 | 5_2_route | 12.3 | drt_violations best 24640 last 24640 rows 2 | before-window best 148257, window best 24640 | PROGRESS: drt_violations improved 83.4 % in window |  |
| epyc7 | dpkit-tt_ctlm-426389 | tt_ctlm | stage_odb_cap | 6.4 | last meaningful line 0.0 h ago (3453/3453 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-cbf_q11-2627513 | cbf_q11 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-cbn_q00__cldbcda913-3330181 | cbn_q00 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | pregrt_ff_hold | 7.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-cbx_q10__cl89936551-3322021 | cbx_q10 | pregrt_ff_hold | 4.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-cbx_q10__cl89936551_h-2365139 | cbx_q10 | pregrt_ff_hold | 4.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-3326220 | col_h10_r2__t1 | 5_1_grt | 4.3 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-1305862 | col_h9_r0_p1__t1 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-2349309 | col_h9_r0_p3__t1 | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2622406 | col_h9_r0_p3__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2628597 | col_h9_r0_p3__t1 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r2__t1__clb8d86cd5__pv982ec12c-2337034 | col_h9_r2__t1 | 5_2_route | 14.6 | drt_violations best 66 last 66 rows 12 | before-window best 4130, window best 66 | PROGRESS: drt_violations improved 98.4 % in window |  |
| intel1 | dpkit-sle_stm_v1__clbe630b9c-4044402 | sle_stm_v1 | pregrt_ff_hold | 6.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_stm_v2__cl7b3062fa-694049 | sle_stm_v2 | pregrt_ff_hold | 5.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | pregrt_ff_hold | 5.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | pregrt_ff_hold | 5.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-842919 | slw_st_b_v1 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t7-888978 | svc_lo_dsdv_svc_rs__t7 | 2_1_floorplan | 15.7 | last meaningful line 0.5 h ago (1375/1375 lines) | PROGRESS: log still growing |  |
| intel1 | llc-2617980-5152274.pin2 | llc-2617980-5152274.pin2 | pregrt_ff_hold | 0.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 11.9 | last meaningful line 0.0 h ago (711/711 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t3-1117539 | dsdv_slice_c1x_C__t3 | stage_odb_cap | 19.0 | last meaningful line 0.0 h ago (1087/1087 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-dsdv_slice_lepe_mu_C__t1-1117806 | dsdv_slice_lepe_mu_C__t1 | stage_odb_cap | 19.0 | last meaningful line 0.0 h ago (1086/1086 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-glue-4013867 | glue | stage_odb_cap | 7.7 | last meaningful line 0.0 h ago (518/518 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 7.0 | last meaningful line 0.0 h ago (433/433 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_pv_v5n-1632118 | kv3_pv_v5n | stage_odb_cap | 6.5 | last meaningful line 0.0 h ago (389/389 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-1118548 | ot_s81sl_kv_leaf__t5 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_hc0__cl05696ed1-1266312 | sle_hc0 | stage_odb_cap | 10.4 | last meaningful line 0.0 h ago (669/669 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_hc0__cl929603c0__cl38badc56-1455458 | sle_hc0 | stage_odb_cap | 10.2 | last meaningful line 0.0 h ago (662/662 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2444359 | sle_st_b_v1 | stage_odb_cap | 9.1 | last meaningful line 0.0 h ago (543/543 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2435819 | slw_hc1 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (425/425 lines) | PROGRESS: log still growing |  |
