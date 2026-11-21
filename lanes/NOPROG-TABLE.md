# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 18:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 1, 'GRT-LABEL': 40, 'NO-DATA': 8, 'YOUNG': 229, 'KEEP': 8, 'EXCLUDED': 3, 'PROGRESS': 66}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-kv3_pc_v3-1060726 | kv3_pc_v3 | stage_odb_cap | 7.0 | last meaningful line 0.0 h ago (3854/3854 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -1491.99 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 27.8 | drt_violations best 10168 last 22918 rows 19 | before-window best 10168, window best 22918 | NO-PROGRESS: drt_violations best 22918 vs 10168 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| intel2 | dpkit-ot_s81sl_leaf__t75-2211324 | ot_s81sl_leaf__t75 | pregrt_ff_hold | 3.6 | repair_Violations best 58985 last 58985 rows 12 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -466.10 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub cancels after the report hour) |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-3929554 | dsdv_slice_c1x_C__t6 | 5_1_grt | 25.4 | grt rounds 2 overflow 5:110819 -> 10:81748 | GRT-LABEL: DESIGN-FAIL: overflow 81748 at round 10 > 1000 |  |
| epyc10 | dpkit-hd_lep0N-304519 | hd_lep0N | 5_1_grt | 21.8 | grt rounds 2 overflow 5:87024 -> 10:50446 | GRT-LABEL: DESIGN-FAIL: overflow 50446 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 10.9 | grt rounds 6 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t13-2319777 | ot_s81sl_leaf__t13 | 5_1_grt | 10.6 | grt rounds 3 overflow 5:46776 -> 10:46203 -> 15:36479 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 20.5 | grt rounds 4 overflow 5:27623 -> 10:16079 -> 15:13155 -> 20:11184 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t27-1555125 | ot_s81sl_leaf__t27 | 5_1_grt | 20.9 | grt rounds 6 overflow 5:6443 -> 10:2406 -> 15:2050 -> 20:2048 -> 25:3507 -> 30:1710 | GRT-LABEL: DESIGN-FAIL: overflow 2406 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t29-1248873 | ot_s81sl_leaf__t29 | 5_1_grt | 10.9 | grt rounds 3 overflow 5:43983 -> 10:46937 -> 15:40008 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t46-154311 | ot_s81sl_leaf__t46 | 5_1_grt | 19.1 | grt rounds 3 overflow 5:26008 -> 10:17168 -> 15:15441 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-1259756 | ot_s81sl_leaf__t53 | 5_1_grt | 21.1 | grt rounds 4 overflow 5:57640 -> 10:67281 -> 15:55315 -> 20:59580 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t54__cl501e5681-1253642 | ot_s81sl_leaf__t54 | 5_1_grt | 21.1 | grt rounds 4 overflow 5:47246 -> 10:41621 -> 15:39931 -> 20:40836 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 29.7 | grt rounds 3 overflow 5:46983 -> 10:40238 -> 15:37035 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | 5_1_grt | 5.7 | grt rounds 3 overflow 5:19294 -> 10:15410 -> 15:12400 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | 5_1_grt | 7.0 | grt rounds 6 overflow 5:3688 -> 10:2561 -> 15:2268 -> 20:1901 -> 25:1852 -> 30:1871 | GRT-LABEL: DESIGN-FAIL: overflow 2561 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_serdes-2335115 | hd_serdes | 5_1_grt | 2.9 | grt rounds 4 overflow 5:7819 -> 10:3205 -> 15:1186 -> 20:653 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v2__cl2862d491-418618 | kv3_hgi_v2 | 5_1_grt | 4.4 | grt rounds 3 overflow 5:49203 -> 10:43248 -> 15:37407 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t31-3799196 | ot_s81sl_leaf__t31 | 5_1_grt | 5.1 | grt rounds 4 overflow 5:30377 -> 10:16662 -> 15:14043 -> 20:13888 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3998705 | ot_s81sl_leaf__t69 | 5_1_grt | 5.0 | grt rounds 3 overflow 5:38517 -> 10:38946 -> 15:36882 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_1_grt | 2.5 | grt rounds 6 overflow 5:727 -> 10:550 -> 15:542 -> 20:538 -> 25:186 -> 30:77 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-3773256 | ot_s81sl_leaf__t33 | 5_1_grt | 31.3 | grt rounds 4 overflow 5:19451 -> 10:7287 -> 15:6367 -> 20:6091 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-685873 | ot_s81sl_leaf__t33 | 5_1_grt | 18.7 | grt rounds 3 overflow 5:29589 -> 10:6636 -> 15:5987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t39-529382 | ot_s81sl_leaf__t39 | 5_1_grt | 18.7 | grt rounds 3 overflow 5:59133 -> 10:59412 -> 15:50422 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t41-2604766 | ot_s81sl_leaf__t41 | 5_1_grt | 11.8 | grt rounds 3 overflow 5:41295 -> 10:41518 -> 15:39056 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 20.1 | grt rounds 4 overflow 5:38322 -> 10:24729 -> 15:20068 -> 20:19877 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t61-756109 | ot_s81sl_leaf__t61 | 5_1_grt | 18.7 | grt rounds 3 overflow 5:41921 -> 10:44894 -> 15:44490 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t7-3790497 | ot_s81sl_leaf__t7 | 5_1_grt | 31.3 | grt rounds 4 overflow 5:80612 -> 10:60016 -> 15:48404 -> 20:49826 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-3770871 | dsdv_slice_c1x_C__t1 | 5_1_grt | 25.6 | grt rounds 3 overflow 5:78093 -> 10:63859 -> 15:66890 | GRT-LABEL: DESIGN-FAIL: overflow 63859 at round 10 > 1000 |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-2889394 | dsdv_slice_c1x_C__t9 | 5_1_grt | 26.7 | grt rounds 2 overflow 5:74357 -> 10:60790 | GRT-LABEL: DESIGN-FAIL: overflow 60790 at round 10 > 1000 |  |
| epyc9 | dpkit-hd_lep0N-579160 | hd_lep0N | 5_1_grt | 59.9 | grt rounds 3 overflow 5:49923 -> 10:46799 -> 15:42444 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-1796631 | ot_s81sl_leaf__t22 | 5_1_grt | 27.9 | grt rounds 3 overflow 5:49170 -> 10:53420 -> 15:44462 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 11.0 | grt rounds 3 overflow 5:27490 -> 10:13905 -> 15:10455 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t46-1784404 | ot_s81sl_leaf__t46 | 5_1_grt | 27.9 | grt rounds 4 overflow 5:26917 -> 10:19209 -> 15:17126 -> 20:16680 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 9.8 | grt rounds 3 overflow 5:37849 -> 10:38699 -> 15:36252 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 9.8 | grt rounds 3 overflow 5:24921 -> 10:18037 -> 15:15084 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 20.3 | grt rounds 4 overflow 5:27548 -> 10:11628 -> 15:6221 -> 20:3928 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 9.8 | grt rounds 3 overflow 5:48001 -> 10:50111 -> 15:49341 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 29.4 | grt rounds 3 overflow 5:48547 -> 10:43151 -> 15:39795 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 21.3 | grt rounds 3 overflow 5:43280 -> 10:40835 -> 15:38869 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 21.3 | grt rounds 3 overflow 5:44318 -> 10:38620 -> 15:37968 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 20.6 | grt rounds 3 overflow 5:59628 -> 10:54127 -> 15:50262 | GRT-LABEL: DESIGN-FAIL: overflow 54127 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 16.1 | grt rounds 4 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-ot-s81sl-leaf--t25--cl55642d17-grt-1154794 | ot-s81sl-leaf--t25--cl55642d17-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-62851 | col_h10_r0_p1__t1 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3105141 | col_h10_r0_p1__t1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (220/220 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl911743eb-373639 | col_h10_r0_p1__t1 | 3_3_place_gp | 0.5 | overflow best 0.2751 last 0.2754 rows 17 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-col_h10_r0_p4__t1__pv07945c1e-397364 | col_h10_r0_p4__t1 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (76/76 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv9ae398c2-2898163 | col_h10_r2__t1 | 5_1_grt | 1.3 | last meaningful line 0.3 h ago (197/212 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-3187088 | col_h9_r0_p1__t1 | 3_3_place_gp | 1.1 | overflow best 0.2952 last 0.2952 rows 36 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3218206 | col_h9_r0_p1__t1 | 3_4_place_resized | 1.1 | repair_Remaining best 46998 last 46998 rows 114 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-3222995 | col_h9_r0_p1__t1 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (208/208 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2276310 | col_h9_r0_p2__t1 | postcts_gate_FF | 9.4 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3644485 | col_h9_r0_p2__t1 | 3_3_place_gp | 0.9 | overflow best 0.2547 last 0.2547 rows 41 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv110cabb8-3352541 | col_h9_r0_p3__t1 | 3_3_place_gp | 1.1 | overflow best 0.2905 last 0.2905 rows 36 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b-3126619 | col_h9_r0_p3__t1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (228/228 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3270764 | col_h9_r0_p3__t1 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (192/192 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-3089382 | col_h9_r0_p3__t1 | 3_5_place_dp | 1.2 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-3643245 | col_h9_r0_p4__t1 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (180/180 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pv35382794-3626373 | col_h9_r0_p5__t1 | 3_3_place_gp | 0.9 | overflow best 0.4191 last 0.4226 rows 22 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pvc1b82625-4013216 | col_h9_r0_p5__t1 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-2994465 | col_h9_r0_p5__t1 | 4_1_cts | 1.3 | last meaningful line 0.0 h ago (3052/3052 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t9-1010078 | dsdv_slice_c1x_C__t9 | 1_2_yosys | 2.5 | last meaningful line -0.0 h ago (230/230 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-4062670 | dsdv_slice_lepe_nh_mus_LP__t1 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (185/185 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-2362622 | hd_lep0N | 5_1_grt | 10.6 | last meaningful line 2.5 h ago (198/203 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Eo-4062983 | kv3_hub_Eo | 2_4_floorplan_pdn | 0.8 | last meaningful line 0.2 h ago (20/20 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t3-4025566 | ot_s81sl_kv_leaf__t3 | 2_1_floorplan | 0.8 | repair_Viol best 1304 last 1304 rows 1196 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t4-3962225 | ot_s81sl_kv_leaf__t4 | 2_4_floorplan_pdn | 0.8 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t10-72603 | ot_s81sl_leaf__t10 | 3_3_place_gp | 0.7 | overflow best 0.6076 last 0.6076 rows 11 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t28-451853 | ot_s81sl_leaf__t28 | 3_3_place_gp | 0.5 | overflow best 0.4832 last 0.4845 rows 16 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t43-3632683 | ot_s81sl_leaf__t43 | pregrt_ff_hold | 0.9 | repair_Violations best 228 last 268 rows 54 | YOUNG: stage 0.9 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-4184133 | ot_s81sl_leaf__t44 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t60-4062057 | ot_s81sl_leaf__t60 | 3_3_place_gp | 0.8 | overflow best 0.2219 last 0.2219 rows 41 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t66-2946995 | ot_s81sl_leaf__t66 | 3_5_place_dp | 1.3 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t13-372470 | serdes__t13 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t2-3852722 | serdes__t2 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.998 last 0.998 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-4047305 | sle_fw_v2 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (116/116 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-4041180 | slw_fe_v2 | generate_abstract | 22.1 | last meaningful line 0.4 h ago (948/948 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc2__cl6bcaba89-3790404 | slw_hc2 | 3_3_place_gp | 0.9 | overflow best 0.0994 last 0.0994 rows 51 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-tt_ctlm-4105966 | tt_ctlm | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (3803/3803 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | otc-1309026-28964 | 1309026 | ot_bind_native_77588433c6f91cf0798b4dbf | 0.0 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-1309115-15257 | 1309115 | ot_bind_native_6a16ddf9f7f9126bd52e33b0 | 0.0 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-3235470-31032 | 3235470 | gen_lint_yosys | 1.1 | last meaningful line 1.1 h ago (1/1 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | otc-3883547-31116 | 3883547 | gen_lint_yosys | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | otc-4023010-28741 | 4023010 | gen_lint_yosys | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_185639_3224747-i1-3809500 | eco_20261120_185639_3224747-i1 | 5_1_grt | 0.8 | last meaningful line 0.1 h ago (231/243 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 5.5 | drt_violations best 1708 last 1708 rows 12 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_233525_2680444-i1t-3910623 | eco_20261120_233525_2680444-i1t | 5_2_route | 3.1 | drt_violations best 61156 last 61156 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_003008_2139459-i1-831859 | eco_20261121_003008_2139459-i1 | 5_1_grt | 0.3 | last meaningful line 0.2 h ago (227/1230 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_014354_2681516-i1t-3571482 | eco_20261121_014354_2681516-i1t | 5_2_route | 1.0 | last meaningful line 0.2 h ago (255/256 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_021137_2680521-i1t-410323 | eco_20261121_021137_2680521-i1t | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (250/1365 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | stage_odb_cap | 6.9 | last meaningful line 0.0 h ago (3438/3438 lines) | YOUNG: evidence 6.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-803960 | col_h10_r0_p1__t1 | 3_1_place_gp_skip_io | 0.5 | overflow best 0.9085 last 0.9191 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pv5b623e07-3666069 | col_h10_r0_p4__t1 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (236/236 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1642331 | col_h10_r1__t1 | 2_1_floorplan | 0.0 | repair_Viol best 3559 last 3559 rows 308 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-1320857 | col_h10_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.2772 last 0.3016 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-853867 | col_h9_r0_p1__t1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.3517 last 0.3517 rows 34 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-855446 | col_h9_r0_p2__t1 | stage_odb_cap | 0.4 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-145230 | col_h9_r0_p2__t1 | stage_odb_cap | 7.0 | last meaningful line 0.0 h ago (3671/3671 lines) | YOUNG: evidence 7.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-1632723 | col_h9_r0_p2__t1 | 2_1_floorplan | 0.0 | repair_Viol best 5231 last 5231 rows 148 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv110cabb8-3033723 | col_h9_r0_p3__t1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (807/807 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-419785 | col_h9_r0_p3__t1 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (72/72 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-coll_ftc-1206090 | coll_ftc | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (251/251 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t4-528316 | dsdv_slice_c1x_C__t4 | sdc_lint | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t6-626411 | dsdv_slice_c1x_C__t6 | stage_odb_cap | 3.5 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t8-612303 | dsdv_slice_c1x_C__t8 | stage_odb_cap | 3.5 | last meaningful line 0.0 h ago (164/164 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1630739 | dsdv_slice_lepe_nh_mus_C__t1 | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (76/76 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_C__t1-2506911 | dsdv_slice_lepw_mus_C__t1 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t1-3583234 | ot_s81sl_kv_leaf__t1 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (72/72 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | stage_odb_cap | 6.6 | last meaningful line 0.0 h ago (567/567 lines) | YOUNG: evidence 6.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-954928 | ot_s81sl_leaf__t36 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (404/404 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t52-645358 | ot_s81sl_leaf__t52 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (96/96 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t68-2798472 | ot_s81sl_leaf__t68 | stage_odb_cap | 5.1 | last meaningful line 0.0 h ago (2604/2604 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t8-1240171 | ot_s81sl_leaf__t8 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.9015 last 0.9329 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-serdes__t14-3326726 | serdes__t14 | 3_3_place_gp | 1.2 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t15__cla2127225-539609 | serdes__t15 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.1 h ago (92/92 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t15__cla3d02796-450387 | serdes__t15 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.1 h ago (92/92 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t16-3293794 | serdes__t16 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (80/80 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | 4_1_cts | 1.6 | last meaningful line 0.0 h ago (4719/4719 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | 4_1_cts | 1.6 | last meaningful line 0.1 h ago (4966/4966 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-2762040 | sle_fw_v2 | 4_1_cts | 1.4 | last meaningful line 0.2 h ago (4763/4763 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v2-3023909 | sle_sc_v2 | 5_1_grt | 4.1 | repair_Remaining best 308610 last 308610 rows 97 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-2275472 | sle_sc_v3 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (277/277 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (5517/5517 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (372/372 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | 5_1_grt | 4.3 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1570756 | sle_stm_v2 | 5_1_grt | 4.5 | repair_Remaining best 197578 last 197578 rows 203 | YOUNG: stage 0.8 h < 1 h |  |
| epyc2 | dpkit-slice_station__t24__cleece78ec-1646967 | slice_station__t24 | 4_1_cts | 0.0 | last meaningful line 0.0 h ago (1121/1121 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t25-3307284 | slice_station__t25 | 3_5_place_dp | 1.2 | last meaningful line 0.0 h ago (110/110 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t52-2803346 | slice_station__t52 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (3664/3664 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (295/295 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (408/408 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3019094 | slw_fe_v2 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (488/488 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-1889978 | slw_fw_v1 | 4_1_cts | 1.8 | last meaningful line 0.1 h ago (5042/5042 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (340/340 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | 5_1_grt | 4.0 | last meaningful line 0.0 h ago (134/134 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v3-4010623 | slw_fw_v3 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (323/323 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (315/315 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | stage_odb_cap | 3.7 | last meaningful line 0.0 h ago (408/408 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (338/338 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (422/422 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (266/266 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (401/401 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (172/172 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-3141066 | svc_hi_dsdv_svc_pvso_entry__t2 | port_bind | 4.0 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t5-801765 | svc_hi_dsdv_svc_rs__t5 | 1_2_yosys | 0.5 | last meaningful line 0.0 h ago (179/179 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-508253 | svc_lo_dsdv_svc_rs__t1 | 1_2_yosys | 0.6 | last meaningful line 0.0 h ago (156/156 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t2-897008 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 0.4 | last meaningful line 0.0 h ago (107/107 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t3-473545 | svc_lo_dsdv_svc_rs__t3 | 1_2_yosys | 0.6 | last meaningful line 0.0 h ago (163/163 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t5-40726 | svc_lo_dsdv_svc_rs__t5 | port_bind | 7.0 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t7-2982698 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 4.1 | last meaningful line 0.0 h ago (622/622 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs_w__t1-609483 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 3.5 | last meaningful line 0.0 h ago (562/562 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | otc-516902-16365 | 516902 | gen_lint_yosys | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-count-p1_bc-3133296 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (762/762 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i1-1701387 | eco_20261120_134605_3273412-i1 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (130/130 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i1t-2059062 | eco_20261120_170022_4017640-i1t | 5_2_route | 1.7 | last meaningful line 0.4 h ago (268/269 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1-1663436 | eco_recover1120-i1 | 5_2_route | 3.2 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-cbn-q01--clab6e67f2-grt-2333074 | cbn-q01--clab6e67f2-grt | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (300/300 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 3.0 | last meaningful line 1.3 h ago (198/201 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cle0015330-418927 | kv3_hgi_v2 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (331/331 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2-2363517 | kv3_pv_v2 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (1096/1096 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1802160 | kv3_pv_v8 | 4_1_cts | 6.6 | last meaningful line 0.8 h ago (15744/15744 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1803775 | kv3_pv_v8 | 4_1_cts | 6.6 | last meaningful line 0.3 h ago (15650/15650 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-561953 | kv3_pv_v8 | 4_1_cts | 4.4 | last meaningful line 0.5 h ago (15659/15659 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-725922 | kv3_pv_v8 | 4_1_cts | 9.3 | last meaningful line 1.5 h ago (15762/15762 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 3.0 | repair_TNS best 300839 last 300839 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-668507 | ot_s81sl_leaf__t73 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (503/503 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t4-1483997 | serdes__t4 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3233970 | sle_st_b_v1 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (186/186 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-437345 | sle_stm_v1 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (542/542 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t43-449200 | slice_station__t43 | 5_2_route | 4.4 | drt_violations best 32866 last 32866 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3248657 | slw_fw_v1 | tt_setup_repair | 2.2 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-3255088 | slw_fw_v1 | pregrt_ff_hold | 2.2 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-3208717 | slw_hc0 | pregrt_ff_hold | 2.2 | repair_TNS best 2516.35 last 2516.35 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cl16607c7a-441369 | slw_hc2 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (361/361 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-443851 | slw_sc_v1 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (492/492 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3263016 | slw_st_b_v1 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (162/162 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-791387 | slw_stm_v1 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (440/440 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3259392 | slw_stm_v1 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (196/196 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 9.3 |  | NO-DATA: no log found |  |
| epyc7 | klegacy-dsdv_bksel_c_rfda3pt-1968026 | dsdv_bksel_c_rfda3pt | postcts_gate_TT | 3.2 | last meaningful line 0.0 h ago (420/420 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_124815_3297714-i1-942798 | eco_20261120_124815_3297714-i1 | 5_2_route | 3.2 | drt_violations best 73 last 73 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | so_2226540_ff_79897 | so_2226540_ff_79897 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc7 | so_2226540_tt_79897 | so_2226540_tt_79897 | signoff | 0.2 |  | NO-DATA: empty log |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc22584f3-2469769 | col_h9_r1__t1 | 6_report | 11.8 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t36-39168 | slice_station__t36 | 5_2_route | 7.7 | last meaningful line 0.7 h ago (275/276 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 37.7 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1655589 | col_h10_r0_p4__t1 | 5_2_route | 9.3 | drt_violations best 12440 last 12440 rows 2 | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-4060695 | col_h10_r1__t1 | 5_1_grt | 2.3 | last meaningful line 0.1 h ago (199/202 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-1942764 | col_h10_r1__t1 | 5_1_grt | 3.2 | last meaningful line 1.0 h ago (199/218 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pve28d14fa-4078698 | col_h10_r1__t1 | 5_1_grt | 2.3 | last meaningful line 0.3 h ago (199/205 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-1933496 | dsdv_slice_c1x_C__t1 | 1_2_yosys | 3.2 | last meaningful line 0.0 h ago (53/53 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t4-4812 | dsdv_slice_c1x_C__t4 | 1_1_yosys_canonicalize | 2.2 | last meaningful line 0.8 h ago (125/125 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-3384294 | dsdv_slice_c3x_C__t1 | 1_1_yosys_canonicalize | 2.5 | last meaningful line 1.0 h ago (132/132 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-894481 | dsdv_slice_lepw_mu_C__t1 | 1_1_yosys_canonicalize | 1.6 | last meaningful line 0.1 h ago (143/143 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-1952006 | hd_ctl | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (1041/1041 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-hd_host_n-4082127 | hd_host_n | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (1264/1264 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-1366470 | ot_s81sl_kv_leaf__t5 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (239/239 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-4078805 | ot_s81sl_leaf__t39 | 5_1_grt | 2.3 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t15__cla3d02796-3958052 | serdes__t15 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (352/352 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-4074295 | slice_station__t37 | 4_1_cts | 2.3 | last meaningful line 0.0 h ago (4142/4142 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-23175 | slice_station__t51 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (782/782 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-80410 | slw_fe_v1 | 5_1_grt | 2.2 | repair_TNS best 8452.91 last 8452.91 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-2003480 | slw_fe_v2 | 5_1_grt | 3.1 | last meaningful line 2.2 h ago (215/771 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | stage_odb_cap | 3.1 | last meaningful line 0.0 h ago (274/274 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-63032 | slw_hc1 | 4_1_cts | 2.2 | last meaningful line 0.1 h ago (5224/5224 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc9 | dpkit-svc_hi_dsdv_svc_rs__t6-1947287 | svc_hi_dsdv_svc_rs__t6 | 1_2_yosys | 3.2 | last meaningful line 0.2 h ago (637/637 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs__t3-1340352 | svc_lo_dsdv_svc_rs__t3 | 1_2_yosys | 1.3 | last meaningful line 0.0 h ago (330/330 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs_w__t1-4075465 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 4.0 | last meaningful line 0.3 h ago (648/648 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | kv102-face-qkd_hr_core_peer-1116 | kv102-face-qkd_hr_core_peer | s81-die-r3-c-rsync | 102.9 |  | NO-DATA: empty log |  |
| epyc9 | prd-eco_20261120_185716_1464729-i1t-2754533 | eco_20261120_185716_1464729-i1t | 5_2_route | 7.8 | drt_violations best 72611 last 72611 rows 1 | YOUNG: evidence 4.7 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | postcts_gate_TT | 10.0 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv8d734760-4087165 | col_h9_r0_p3__t1 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-4075990 | col_h9_r0_p3__t1 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (80/80 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | 5_2_route | 9.9 | last meaningful line 1.0 h ago (284/285 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-4074955 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.7 | overflow best 0.2901 last 0.2901 rows 38 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-3373537 | col_h9_r0_p5__t1 | 3_3_place_gp | 1.0 | overflow best 0.2524 last 0.2524 rows 36 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3341852 | col_h9_r2__t1 | 5_2_route | 9.8 | drt_violations best 5902 last 5902 rows 3 | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1103979 | dsdv_slice_c1x_C__t3 | sdc_lint | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_mu_C__t1-543594 | dsdv_slice_lepe_mu_C__t1 | 1_1_yosys_canonicalize | 2.5 | last meaningful line 0.5 h ago (129/129 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-4162448 | dsdv_slice_lepe_nh_mus_C__t1 | 1_1_yosys_canonicalize | 2.7 | last meaningful line 1.0 h ago (131/131 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-450022 | dsdv_slice_lepw_mu_C__t1 | 1_1_yosys_canonicalize | 2.5 | last meaningful line 0.7 h ago (143/143 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-glue-3352856 | glue | 3_3_place_gp | 1.0 | overflow best 0.0989 last 0.0989 rows 41 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (380/380 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-513808 | kv3_pv_v12 | stage_odb_cap | 5.5 | last meaningful line 0.0 h ago (740/740 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t2-1333460 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 3.8 | last meaningful line 0.0 h ago (298/298 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t2-479703 | ot_s81sl_leaf__t2 | stage_odb_cap | 0.4 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t7-3312277 | ot_s81sl_leaf__t7 | 3_3_place_gp | 1.1 | overflow best 0.1921 last 0.1921 rows 41 | YOUNG: stage 0.8 h < 1 h |  |
| intel1 | dpkit-serdes__t12-90360 | serdes__t12 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.0 h ago (91/91 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-2480956 | sle_fe_v1 | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (292/292 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3505370 | slice_station__t40 | generate_abstract | 9.8 | last meaningful line 0.1 h ago (210/210 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | 5_2_route | 6.6 | last meaningful line 0.1 h ago (129/129 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_pvso_entry__t1-18505 | svc_hi_dsdv_svc_pvso_entry__t1 | 1_2_yosys | 0.6 | last meaningful line 0.0 h ago (185/185 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t2-996017 | svc_hi_dsdv_svc_rs__t2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (39/39 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t3-432817 | svc_hi_dsdv_svc_rs__t3 | 1_2_yosys | 0.4 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t4-4054912 | svc_hi_dsdv_svc_rs__t4 | 1_2_yosys | 0.7 | last meaningful line 0.0 h ago (224/224 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t6-1410020 | svc_hi_dsdv_svc_rs__t6 | 1_2_yosys | 3.8 | last meaningful line 0.8 h ago (623/623 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t6-1380810 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 5.1 | last meaningful line 0.3 h ago (690/690 lines) | YOUNG: evidence 5.1 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t7-1446461 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 3.7 | last meaningful line 0.0 h ago (531/531 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | otc-1006993-6312 | 1006993 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-1193819-6962 | 1193819 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (6/6 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | otc-473923-2002 | 473923 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | prd-eco_20261120_175848_3183588-i1t-312780 | eco_20261120_175848_3183588-i1t | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (240/1444 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | so_522370_ff_11969 | so_522370_ff_11969 | signoff | 0.4 |  | NO-DATA: empty log |  |
| intel1 | so_522370_tt_11969 | so_522370_tt_11969 | signoff | 0.4 |  | NO-DATA: empty log |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-175119 | col_h10_r0_p4__t1 | pregrt_ff_hold | 2.4 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p6__t1__pv0012ba28-182001 | col_h9_r0_p6__t1 | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (1085/1085 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t10-2197686 | dsdv_slice_c1x_C__t10 | 3_1_place_gp_skip_io | 3.6 | overflow best 0.8397 last 0.8614 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t3-2191361 | dsdv_slice_c1x_C__t3 | 3_1_place_gp_skip_io | 3.6 | overflow best 0.5658 last 0.5658 rows 33 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t7-931054 | dsdv_slice_c1x_C__t7 | 3_3_place_gp | 4.6 | overflow best 0.4952 last 0.4952 rows 30 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (950/950 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 15.9 | last meaningful line 1.3 h ago (225/229 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 15.9 | last meaningful line 0.8 h ago (226/229 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t62-971183 | ot_s81sl_leaf__t62 | stage_odb_cap | 4.6 | last meaningful line 0.0 h ago (2188/2188 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-279781 | ot_s81sl_leaf__t9 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (371/371 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-phy__t1-2671887 | phy__t1 | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (1658/1658 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-171983 | sle_sc_v1 | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (442/442 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-169076 | sle_sc_v1 | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (311/311 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (294/294 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (756/756 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl7b3062fa-155084 | sle_stm_v2 | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (812/812 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t27-184972 | slice_station__t27 | 5_1_grt | 2.4 | last meaningful line 0.2 h ago (204/436 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t43-189037 | slice_station__t43 | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (783/783 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t49-221823 | slice_station__t49 | 5_1_grt | 2.3 | last meaningful line 0.9 h ago (203/547 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (310/310 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-195191 | slw_sc_v1 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (318/318 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v2-195133 | slw_sc_v2 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (398/398 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (283/283 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-320845 | svc_hi_dsdv_svc_rs__t1 | 1_2_yosys | 2.3 | last meaningful line 0.3 h ago (459/459 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t2-2176981 | svc_hi_dsdv_svc_rs__t2 | 1_2_yosys | 3.6 | last meaningful line 0.8 h ago (599/599 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t5-907989 | svc_hi_dsdv_svc_rs__t5 | 2_1_floorplan | 4.6 | last meaningful line 0.2 h ago (90/90 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-svc_lo_dsdv_svc_rs__t6-416042 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 2.2 | last meaningful line 0.2 h ago (498/498 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel2 | prd-eco_20261120_155439_476619-i1t-3320689 | eco_20261120_155439_476619-i1t | 5_2_route | 2.8 | last meaningful line 0.2 h ago (265/266 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162132_484876-i1t-190176 | eco_20261120_162132_484876-i1t | 5_2_route | 2.4 | last meaningful line 0.2 h ago (263/264 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162140_2433056-i1t-160659 | eco_20261120_162140_2433056-i1t | 5_2_route | 2.4 | last meaningful line 0.0 h ago (264/265 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | prd-eco_20261120_174547_3236169-i1t-2273142 | eco_20261120_174547_3236169-i1t | 5_1_grt | 0.9 | last meaningful line 0.2 h ago (232/388 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | prd-eco_20261120_182729_483429-i1t-3309803 | eco_20261120_182729_483429-i1t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | so_2909615_ff_59318 | so_2909615_ff_59318 | stage_odb_cap | 0.5 | last meaningful line 0.3 h ago (1299/1299 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | so_2909615_tt_59318 | so_2909615_tt_59318 | stage_odb_cap | 0.5 | last meaningful line 0.3 h ago (1299/1299 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 31.6 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv62bca836-2457630 | col_h9_r1__t1 | stage_odb_cap | 11.8 |  | KEEP: col_h9_r1__t1__cl49d7a23e__pv62bca836	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-2459808 | col_h9_r1__t1 | stage_odb_cap | 11.8 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4187921 | col_h10_r1__t1 | 5_1_grt | 2.2 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-902390 | col_h10_r2__t1 | 5_2_route | 28.9 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-coll_core-1096606 | coll_core | 5_1_grt | 24.1 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw2b_coll	QC-PLAN-R5	coll_core proof, GRT repa |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 18.9 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 11.6 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 65.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | 5_2_route | 41.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | 5_1_grt | 42.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-col_h10_r1__t1__cld01bb4ae-2907339 | col_h10_r1__t1 | pregrt_ff_hold | 1.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | stage_odb_cap | 20.9 | last meaningful line 0.0 h ago (10510/10510 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | stage_odb_cap | 22.0 | last meaningful line 0.0 h ago (11047/11047 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-native59-3021964 | native59 | pregrt_ff_hold | 19.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | stage_odb_cap | 9.4 | last meaningful line 0.0 h ago (4951/4951 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2315890 | ot_s81sl_leaf__t44 | stage_odb_cap | 10.6 | last meaningful line 0.0 h ago (768/768 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t69-2660757 | ot_s81sl_leaf__t69 | stage_odb_cap | 10.6 | last meaningful line 0.0 h ago (5923/5923 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | stage_odb_cap | 9.4 | last meaningful line 0.0 h ago (4388/4388 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | stage_odb_cap | 23.8 | last meaningful line 0.0 h ago (12173/12173 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | stage_odb_cap | 24.3 | last meaningful line 0.0 h ago (12206/12206 lines) | PROGRESS: log still growing |  |
| epyc10 | prd-eco_20261120_133204_279056-i1t-3773198 | eco_20261120_133204_279056-i1t | 5_2_route | 13.2 | drt_violations best 44 last 44 rows 15 | before-window best 300, window best 44 | PROGRESS: drt_violations improved 85.3 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 16.0 | last meaningful line 1.4 h ago (1381/1381 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-463270 | col_h10_r1__t1 | 3_5_place_dp | 0.6 | repair_Violations best 0 last 0 rows 40 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvce76611c-507225 | col_h10_r1__t1 | 3_5_place_dp | 0.6 | repair_Violations best 0 last 0 rows 34 | PROGRESS: repair_Violations reached 0 |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (7590/7590 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 13.1 | last meaningful line 0.0 h ago (7153/7153 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (7438/7438 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 7.6 | last meaningful line 0.0 h ago (742/742 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | stage_odb_cap | 7.9 | last meaningful line 0.0 h ago (560/560 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | stage_odb_cap | 7.1 | last meaningful line 0.0 h ago (4090/4090 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | stage_odb_cap | 9.2 | last meaningful line 0.0 h ago (4657/4657 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-4168631 | col_h9_r0_p2__t1 | stage_odb_cap | 7.7 | last meaningful line 0.0 h ago (1071/1071 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4157811 | col_h9_r0_p2__t1 | stage_odb_cap | 7.7 | last meaningful line 0.0 h ago (990/990 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-478083 | col_h9_r0_p2__t1 | stage_odb_cap | 18.7 | last meaningful line 0.0 h ago (10508/10508 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-4171287 | col_h9_r0_p2__t1 | stage_odb_cap | 7.7 | last meaningful line 0.0 h ago (1129/1129 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pv35382794-4154870 | col_h9_r0_p5__t1 | stage_odb_cap | 7.7 | last meaningful line 0.0 h ago (1174/1174 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc1b82625-2466645 | col_h9_r0_p5__t1 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (1214/1214 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-4155323 | col_h9_r0_p5__t1 | stage_odb_cap | 7.7 | last meaningful line 0.0 h ago (1014/1014 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc93af856-4170137 | col_h9_r0_p5__t1 | stage_odb_cap | 7.7 | last meaningful line 0.0 h ago (1064/1064 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf71da13a-2469088 | col_h9_r0_p5__t1 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (1072/1072 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvf731e6ec-2474248 | col_h9_r0_p5__t1 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (1292/1292 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-4170471 | col_h9_r1__t1 | stage_odb_cap | 7.7 | last meaningful line 0.0 h ago (772/772 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-4170921 | col_h9_r1__t1 | stage_odb_cap | 7.7 | last meaningful line 0.0 h ago (921/921 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2cabd9a9-2468121 | col_h9_r1__t1 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (1204/1204 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2404958 | col_h9_r1__t1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (997/997 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-2461304 | col_h9_r1__t1 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (1043/1043 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4108910d-2463920 | col_h9_r1__t1 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (1208/1208 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv47efee8f-2460589 | col_h9_r1__t1 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (1169/1169 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49636389-2470568 | col_h9_r1__t1 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (1215/1215 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-4158882 | col_h9_r1__t1 | stage_odb_cap | 7.7 | last meaningful line 0.0 h ago (966/966 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4ef1b59c-4156066 | col_h9_r1__t1 | stage_odb_cap | 7.7 | last meaningful line 0.0 h ago (782/782 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv70f04488-4156907 | col_h9_r1__t1 | stage_odb_cap | 7.7 | last meaningful line 0.0 h ago (978/978 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv9a5bd576-2405919 | col_h9_r1__t1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (988/988 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc25aad1b-2466145 | col_h9_r1__t1 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (997/997 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvfed9fee6-2471805 | col_h9_r1__t1 | stage_odb_cap | 11.8 | last meaningful line 0.0 h ago (1224/1224 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | stage_odb_cap | 9.6 | last meaningful line 0.0 h ago (2434/2434 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv697f40c9-3741672 | col_h9_r0_p1__t1 | stage_odb_cap | 11.5 | last meaningful line 0.0 h ago (1322/1322 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2119395 | col_h9_r0_p1__t1 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (1325/1325 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-1256935 | col_h9_r0_p1__t1 | stage_odb_cap | 11.0 | last meaningful line 0.0 h ago (2074/2074 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-1252986 | col_h9_r0_p1__t1 | stage_odb_cap | 11.0 | last meaningful line 0.0 h ago (1330/1330 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_fe_v1__cl8210183c-4013675 | sle_fe_v1 | stage_odb_cap | 11.4 | last meaningful line 0.0 h ago (5891/5891 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-2332778 | sle_fw_v2 | stage_odb_cap | 10.7 | last meaningful line 0.0 h ago (5619/5619 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | stage_odb_cap | 21.8 | last meaningful line 0.0 h ago (11652/11652 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | stage_odb_cap | 22.0 | last meaningful line 0.0 h ago (11695/11695 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | 5_2_route | 9.8 | drt_violations best 58 last 58 rows 10 | before-window best 73630, window best 58 | PROGRESS: drt_violations improved 99.9 % in window |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | stage_odb_cap | 9.9 | last meaningful line 0.0 h ago (5523/5523 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (5129/5129 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (5296/5296 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (5084/5084 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 9.9 | last meaningful line 0.0 h ago (5168/5168 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | 5_2_route | 22.5 | drt_violations best 8797 last 8797 rows 3 | before-window best 100416, window best 8797 | PROGRESS: drt_violations improved 91.2 % in window |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t2-1130517 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 7.1 | last meaningful line 0.3 h ago (860/860 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 28.9 | last meaningful line 0.0 h ago (1725/1725 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 24.0 | last meaningful line 0.0 h ago (1446/1446 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 19.5 | last meaningful line 0.0 h ago (1498/1498 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slice_station__t41-218779 | slice_station__t41 | 5_1_grt | 2.3 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
