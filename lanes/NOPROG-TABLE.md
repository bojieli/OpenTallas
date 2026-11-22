# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 18:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'UNSIGNABLE': 1, 'GRT-LABEL': 30, 'YOUNG': 76, 'NO-DATA': 8, 'KEEP': 1, 'EXCLUDED': 2, 'PROGRESS': 12}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-22377 | hd_lep0N | 4_2_tapbal_grt | 10.9 | last meaningful line 6.3 h ago (48/60 lines) | NO-PROGRESS: no new non-iteration log line for 6.3 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 47.8 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 47 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc10 | dpkit-hd_lep0N-1588394 | hd_lep0N | 5_1_grt | 12.5 | grt rounds 2 overflow 5:89584 -> 10:90077 | GRT-LABEL: DESIGN-FAIL: overflow 90077 at round 10 > 1000 |  |
| epyc10 | dpkit-kv3_hgi_v8-3126306 | kv3_hgi_v8 | 5_1_grt | 14.4 | grt rounds 5 overflow 5:37484 -> 10:8165 -> 15:5582 -> 20:4765 -> 25:4799 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 32.9 | grt rounds 4 overflow 5:95946 -> 10:62005 -> 15:49678 -> 20:49999 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 32.9 | grt rounds 5 overflow 5:56489 -> 10:43484 -> 15:40478 -> 20:43412 -> 25:50457 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 47.3 | grt rounds 5 overflow 5:9510 -> 10:5086 -> 15:3245 -> 20:2874 -> 25:3124 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 36.8 | grt rounds 4 overflow 5:54036 -> 10:38366 -> 15:34625 -> 20:37416 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-248840 | sle_st_a_v1 | 5_1_grt | 5.8 | grt rounds 2 overflow 5:3539 -> 10:2906 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-844610 | slw_st_a_v1 | 5_1_grt | 5.3 | grt rounds 2 overflow 5:3827 -> 10:2935 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 26.7 | grt rounds 3 overflow 5:77484 -> 10:72294 -> 15:58855 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 31.7 | grt rounds 3 overflow 5:61525 -> 10:66596 -> 15:69180 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 21.1 | grt rounds 3 overflow 5:53769 -> 10:49359 -> 15:39411 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 21.1 | grt rounds 3 overflow 5:50621 -> 10:49445 -> 15:39714 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 30.8 | grt rounds 3 overflow 5:45785 -> 10:49559 -> 15:42999 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 18.5 | grt rounds 4 overflow 5:110533 -> 10:74939 -> 15:54793 -> 20:62289 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 26.8 | grt rounds 4 overflow 5:95535 -> 10:71407 -> 15:50597 -> 20:56554 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 20.6 | grt rounds 4 overflow 5:97308 -> 10:70056 -> 15:51390 -> 20:58440 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 22.3 | grt rounds 4 overflow 5:44451 -> 10:38859 -> 15:36410 -> 20:37882 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 22.3 | grt rounds 5 overflow 5:41833 -> 10:36208 -> 15:31830 -> 20:31076 -> 25:35283 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hgi_v2__cl2862d491-3732038 | kv3_hgi_v2 | 5_1_grt | 11.2 | grt rounds 2 overflow 5:72991 -> 10:37675 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 21.9 | grt rounds 4 overflow 5:18628 -> 10:12430 -> 15:11259 -> 20:10290 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 34.8 | grt rounds 4 overflow 5:34386 -> 10:12131 -> 15:8208 -> 20:7612 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 45.5 | grt rounds 6 overflow 5:17310 -> 10:18043 -> 15:11655 -> 20:10171 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 45.8 | grt rounds 5 overflow 5:32681 -> 10:30734 -> 15:25360 -> 20:22699 -> 25:31808 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 5_1_grt | 22.8 | grt rounds 6 overflow 5:54170 -> 10:7759 -> 15:5073 -> 20:4181 -> 25:5669 -> 30:2596 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 28.3 | grt rounds 6 overflow 5:40892 -> 10:22267 -> 15:17882 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 23.3 | grt rounds 4 overflow 5:36357 -> 10:30023 -> 15:24172 -> 20:21320 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 44.6 | grt rounds 4 overflow 5:67513 -> 10:53405 -> 15:50242 -> 20:55216 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 39.6 | grt rounds 3 overflow 5:59246 -> 10:46138 -> 15:41146 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 39.6 | grt rounds 3 overflow 5:60515 -> 10:47029 -> 15:53055 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 39.8 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_ctl-2948889 | hd_ctl | 3_3_place_gp | 0.1 | overflow best 0.2976 last 0.4087 rows 105 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-serdes__t4-293755 | serdes__t4 | 5_2_route | 8.0 | drt_violations best 138627 last 138627 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | otc-2578348-23800 | 2578348 | io_relocation_transitive_equiv | 0.5 | last meaningful line 0.4 h ago (847534/847534 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1t-894339 | eco_20261121_154936_3396612-i1t | 5_2_route | 10.4 | drt_violations best 44 last 44 rows 15 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_184648_4039100-i1-3762453 | eco_20261121_184648_4039100-i1 | 5_2_route | 3.3 | drt_violations best 243 last 243 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_203102_3392434-i1t-646001 | eco_20261121_203102_3392434-i1t | 5_2_route | 5.7 | drt_violations best 169411 last 169411 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_012008_1324318-i1t-2203496 | eco_20261122_012008_1324318-i1t | 5_2_route | 0.9 | last meaningful line 0.1 h ago (261/261 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_021210_171272-i1t-3026978 | eco_20261122_021210_171272-i1t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | so_2995311_ff_28888 | so_2995311_ff_28888 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc10 | so_2995311_tt_28888 | so_2995311_tt_28888 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-2629912 | col_h9_r0_p2__t1 | 6_report | 15.8 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 3_4_place_resized | 9.9 | last meaningful line 0.0 h ago (519/519 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2374083 | sle_hc1 | 5_2_route | 16.0 | drt_violations best 20758 last 20758 rows 2 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-427216 | sle_st_a_v1 | postcts_gate_FF | 5.6 | last meaningful line 0.0 h ago (83/83 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-425190 | sle_su_l1 | 5_2_route | 5.6 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t36-3125329 | slice_station__t36 | generate_abstract | 12.3 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2408517 | slw_fe_v1 | 5_2_route | 15.9 | drt_violations best 14154 last 14154 rows 2 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | 5_2_route | 11.5 | last meaningful line 0.1 h ago (133/133 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-1019838 | slw_sc_v1 | postcts_gate_FF | 5.2 | last meaningful line -0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3868961 | slw_sc_v1 | 5_2_route | 8.5 | last meaningful line 0.1 h ago (266/266 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-count-p1_tc-3731479 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_105744_956410-i1-174847 | eco_20261121_105744_956410-i1 | 5_2_route | 2.3 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_123328_2268168-i1-2396653 | eco_20261121_123328_2268168-i1 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (142/142 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_124930_2356681-i1-2553432 | eco_20261121_124930_2356681-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_2221172_ff_16256 | so_2221172_ff_16256 | generate_abstract | 0.5 | last meaningful line 0.2 h ago (752/752 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | so_2221172_tt_16256 | so_2221172_tt_16256 | generate_abstract | 0.5 | last meaningful line 0.2 h ago (752/752 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | so_2708666_ff_91653 | so_2708666_ff_91653 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (586/586 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | so_2708666_tt_91653 | so_2708666_tt_91653 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (586/586 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q11-3840796 | cbf_q11 | 5_1_grt | 5.1 | last meaningful line 2.0 h ago (25/25 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hg_v1p2-672395 | kv3_hg_v1p2 | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | 5_1_grt | 5.0 | last meaningful line 0.0 h ago (132/132 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve230954c-1731757 | sle_hc1 | 5_2_route | 12.2 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3695652 | slw_sc_v2 | 5_1_grt | 5.3 | repair_TNS best 2185.2 last 2185.2 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 6.1 | drt_violations best 68439 last 68439 rows 4 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 3.5 | last meaningful line 1.8 h ago (622/622 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_100942_929932-i2t-68122 | eco_20261121_100942_929932-i2t | 5_1_grt | 0.7 | last meaningful line 0.3 h ago (236/1327 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_184012_3245689-i1-2542120 | eco_20261121_184012_3245689-i1 | 5_2_route | 2.6 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_193535_3253336-i1-3373883 | eco_20261121_193535_3253336-i1 | 5_2_route | 1.7 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | so_616824_ff_34594 | so_616824_ff_34594 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (719/719 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | so_616824_tt_34594 | so_616824_tt_34594 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (719/719 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q00__cld7bf7197-3404310 | cbn_q00 | pregrt_ff_hold | 4.3 | repair_Violations best 45533 last 45533 rows 41 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | 5_1_grt | 6.2 | last meaningful line 4.5 h ago (39/39 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_1_grt | 6.2 | last meaningful line 4.0 h ago (39/39 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_mu_LP__t2-3534677 | dsdv_slice_lepe_mu_LP__t2 | 5_1_grt | 7.2 | last meaningful line 0.1 h ago (149/149 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-3144441 | kv3_hg_v1p2 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t14-3301476 | serdes__t14 | 5_1_grt | 4.4 | repair_TNS best 1205.35 last 1205.35 rows 4 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-3022331 | sle_ctl | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (74/74 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa-1023417 | sle_hc0 | 5_2_route | 13.1 | drt_violations best 7465 last 7465 rows 3 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3985339 | sle_hc2 | 5_2_route | 11.0 | drt_violations best 83965 last 83965 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-1013642 | sle_hc2 | generate_abstract | 13.1 | last meaningful line 0.0 h ago (186/186 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-1899674 | slw_fe_v1 | 5_2_route | 12.5 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-850569 | slw_fe_v1 | 5_2_route | 13.2 | drt_violations best 95161 last 95161 rows 1 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-2906124 | slw_hc1 | 5_2_route | 15.4 | drt_violations best 14489 last 14489 rows 2 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 5.6 | last meaningful line 0.0 h ago (258/259 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-1964882 | slw_su_l0 | 5_2_route | 5.6 | drt_violations best 80394 last 80394 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 5.4 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | prd-eco_20261121_214321_3818039-i1-1999865 | eco_20261121_214321_3818039-i1 | 5_2_route | 1.5 | last meaningful line 0.2 h ago (257/258 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | so_2987712_ff_58143 | so_2987712_ff_58143 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc8 | so_2987712_tt_58143 | so_2987712_tt_58143 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-hd_mesh-3170867 | hd_mesh | pregrt_ff_hold | 1.8 | repair_TNS best 384532 last 384532 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2616668 | sle_hc1 | generate_abstract | 12.8 | last meaningful line 0.1 h ago (1028/1028 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-3085280-30126 | 3085280 | - | 18.2 |  | NO-DATA: no log found |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 18.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 17.8 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261121_070035_1645318-i2t-1219117 | eco_20261121_070035_1645318-i2t | 5_2_route | 4.2 | drt_violations best 13 last 13 rows 32 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_201548_1094504-i2t-3564572 | eco_20261121_201548_1094504-i2t | 5_2_route | 1.3 | drt_violations best 28938 last 28938 rows 1 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | prd-fin-2484763 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (589/589 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-2204474 | slw_st_b_v1 | 6_report | 15.9 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | ot-canary-1932965 | ot-canary | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | otc-1134716-1202 | 1134716 | 3_5_place_dp | 1.0 | last meaningful line 0.1 h ago (116/116 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-3999731-13707 | 3999731 | 3_5_place_dp | 2.7 | last meaningful line 0.0 h ago (80/80 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i2-437055 | eco_20261120_192428_3309571-i2 | 5_2_route | 1.9 | drt_violations best 534 last 534 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i1-1189865 | eco_20261121_082001_3216437-i1 | 5_2_route | 1.0 | last meaningful line 0.1 h ago (265/266 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1t-203702 | eco_20261121_161716_4143584-i1t | 5_2_route | 2.2 | drt_violations best 98048 last 98048 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_1_grt | 0.6 | last meaningful line 0.0 h ago (209/212 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4007898 | col_h9_r1__t1 | 5_1_grt | 3.2 | last meaningful line 1.3 h ago (40/40 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3132815 | coll_ftm | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (151/163 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-485420 | kv3_io_ft | 5_2_route | 1.2 | drt_violations best 5406 last 5406 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | otc-2434779-27076 | 2434779 | gate.ys | 2.3 | last meaningful line 2.3 h ago (51328/51328 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | otc-2600775-23472 | 2600775 | 3_3_place_gp | 0.6 | overflow best 0.1975 last 0.1975 rows 65 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | otc-2646376-19818 | 2646376 | gate.ys | 0.6 | last meaningful line 0.5 h ago (51328/51328 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | otc-2716032-12279 | 2716032 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (83/83 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | otc-2772680-21361 | 2772680 | qx.otrun | 0.5 | last meaningful line 0.0 h ago (2838/2838 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | prd-eco_20261121_115902_173230-i1-2657830 | eco_20261121_115902_173230-i1 | 5_2_route | 2.2 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 35.4 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | eco-abs-1711872 | eco-abs | generate_abstract | 0.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | eco-abs-1868015 | eco-abs | generate_abstract | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_2_route | 22.9 | drt_violations best 10168 last 22918 rows 19 | before-window best 10389, window best 10168 | PROGRESS: drt_violations improved 2.1 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 39.7 | last meaningful line 0.1 h ago (1548/1548 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | pregrt_ff_hold | 6.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-native59-3868183 | native59 | pregrt_ff_hold | 8.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_2_route | 25.3 | drt_violations best 9327 last 18160 rows 19 | before-window best 9551, window best 9327 | PROGRESS: drt_violations improved 2.3 % in window |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 15.6 | drt_violations best 1 last 12 rows 51 | before-window best 3, window best 1 | PROGRESS: drt_violations improved 66.7 % in window |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | pregrt_ff_hold | 4.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2969215 | sle_hc0 | pregrt_ff_hold | 5.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-3504337 | sle_hc1 | pregrt_ff_hold | 5.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3669665 | slw_st_b_v1 | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 7.5 | drt_violations best 658 last 658 rows 23 | before-window best 194272, window best 658 | PROGRESS: drt_violations improved 99.7 % in window |  |
| intel1 | prd-eco_20261121_075836_1991905-i1t-1821063 | eco_20261121_075836_1991905-i1t | 5_2_route | 10.5 | drt_violations best 91 last 91 rows 14 | before-window best 190712, window best 91 | PROGRESS: drt_violations improved 100.0 % in window |  |
