# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 18:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 3, 'GRT-LABEL': 39, 'YOUNG': 242, 'NO-DATA': 9, 'KEEP': 8, 'EXCLUDED': 3, 'PROGRESS': 67}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-cbn_q00__cldbcda913-1076792 | cbn_q00 | 5_1_grt | 6.8 | grt rounds 6 overflow 5:12227 -> 10:8336 -> 15:4776 -> 20:1436 -> 25:480 -> 30:459 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -446.29 ps (< -300, gate TT >= -42); job age 6. | UNSIGNABLE (hub cancels after the report hour) |
| epyc7 | dpkit-kv3_pc_v3-1060726 | kv3_pc_v3 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (3704/3704 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -1491.99 ps (< -300, gate TT >= -42); job age | UNSIGNABLE (hub cancels after the report hour) |
| intel2 | dpkit-ot_s81sl_leaf__t75-2211324 | ot_s81sl_leaf__t75 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (467/467 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -466.10 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub cancels after the report hour) |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-3929554 | dsdv_slice_c1x_C__t6 | 5_1_grt | 25.2 | grt rounds 2 overflow 5:110819 -> 10:81748 | GRT-LABEL: DESIGN-FAIL: overflow 81748 at round 10 > 1000 |  |
| epyc10 | dpkit-hd_lep0N-304519 | hd_lep0N | 5_1_grt | 21.5 | grt rounds 2 overflow 5:87024 -> 10:50446 | GRT-LABEL: DESIGN-FAIL: overflow 50446 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 10.6 | grt rounds 6 overflow 5:11004 -> 10:7238 -> 15:3184 -> 20:1683 -> 25:1055 -> 30:418 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t13-2319777 | ot_s81sl_leaf__t13 | 5_1_grt | 10.4 | grt rounds 3 overflow 5:46508 -> 10:46203 -> 15:36479 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 20.3 | grt rounds 4 overflow 5:27623 -> 10:16079 -> 15:13155 -> 20:11184 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t27-1555125 | ot_s81sl_leaf__t27 | 5_1_grt | 20.6 | grt rounds 6 overflow 5:6443 -> 10:2406 -> 15:2050 -> 20:2048 -> 25:3507 -> 30:1710 | GRT-LABEL: DESIGN-FAIL: overflow 2406 at round 10 > 1000 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t29-1248873 | ot_s81sl_leaf__t29 | 5_1_grt | 10.6 | grt rounds 3 overflow 5:43983 -> 10:46937 -> 15:40008 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t46-154311 | ot_s81sl_leaf__t46 | 5_1_grt | 18.9 | grt rounds 3 overflow 5:26008 -> 10:17168 -> 15:15441 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t53__clb66fa5cb-1259756 | ot_s81sl_leaf__t53 | 5_1_grt | 20.9 | grt rounds 4 overflow 5:57640 -> 10:67281 -> 15:55315 -> 20:59580 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t54__cl501e5681-1253642 | ot_s81sl_leaf__t54 | 5_1_grt | 20.9 | grt rounds 4 overflow 5:47246 -> 10:41621 -> 15:39931 -> 20:40836 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 29.4 | grt rounds 3 overflow 5:46983 -> 10:40238 -> 15:37035 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | phscan-4140488 | phscan | 5_1_grt | 1.1 | grt rounds 4 overflow 5:57640 -> 10:67281 -> 15:55315 -> 20:59580 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | 5_1_grt | 6.7 | grt rounds 6 overflow 5:2761 -> 10:2433 -> 15:2287 -> 20:2095 -> 25:2087 -> 30:2077 | GRT-LABEL: DESIGN-FAIL: overflow 2433 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_serdes-2335115 | hd_serdes | 5_1_grt | 2.7 | grt rounds 3 overflow 5:26757 -> 10:24991 -> 15:19478 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t31-3799196 | ot_s81sl_leaf__t31 | 5_1_grt | 4.9 | grt rounds 4 overflow 5:30377 -> 10:16662 -> 15:14043 -> 20:13888 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3998705 | ot_s81sl_leaf__t69 | 5_1_grt | 4.7 | grt rounds 3 overflow 5:38517 -> 10:38946 -> 15:36882 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_1_grt | 2.2 | grt rounds 6 overflow 5:727 -> 10:550 -> 15:542 -> 20:538 -> 25:186 -> 30:77 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-3773256 | ot_s81sl_leaf__t33 | 5_1_grt | 31.3 | grt rounds 4 overflow 5:19451 -> 10:7287 -> 15:6367 -> 20:6091 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t33-685873 | ot_s81sl_leaf__t33 | 5_1_grt | 18.7 | grt rounds 3 overflow 5:29589 -> 10:6636 -> 15:5987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t39-529382 | ot_s81sl_leaf__t39 | 5_1_grt | 18.7 | grt rounds 3 overflow 5:59133 -> 10:59412 -> 15:50422 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t41-2604766 | ot_s81sl_leaf__t41 | 5_1_grt | 11.8 | grt rounds 3 overflow 5:41295 -> 10:41518 -> 15:39056 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 20.1 | grt rounds 4 overflow 5:38322 -> 10:24729 -> 15:20068 -> 20:19877 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t61-756109 | ot_s81sl_leaf__t61 | 5_1_grt | 18.7 | grt rounds 3 overflow 5:41921 -> 10:44894 -> 15:44490 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t7-3790497 | ot_s81sl_leaf__t7 | 5_1_grt | 31.3 | grt rounds 4 overflow 5:80612 -> 10:60016 -> 15:48404 -> 20:49826 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-3770871 | dsdv_slice_c1x_C__t1 | 5_1_grt | 25.3 | grt rounds 3 overflow 5:78093 -> 10:63859 -> 15:66890 | GRT-LABEL: DESIGN-FAIL: overflow 63859 at round 10 > 1000 |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t9-2889394 | dsdv_slice_c1x_C__t9 | 5_1_grt | 26.4 | grt rounds 2 overflow 5:74357 -> 10:60790 | GRT-LABEL: DESIGN-FAIL: overflow 60790 at round 10 > 1000 |  |
| epyc9 | dpkit-hd_lep0N-579160 | hd_lep0N | 5_1_grt | 59.6 | grt rounds 3 overflow 5:49923 -> 10:46799 -> 15:42444 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t22-1796631 | ot_s81sl_leaf__t22 | 5_1_grt | 27.7 | grt rounds 3 overflow 5:49170 -> 10:53420 -> 15:44462 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 10.8 | grt rounds 3 overflow 5:27490 -> 10:16178 -> 15:10455 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t46-1784404 | ot_s81sl_leaf__t46 | 5_1_grt | 27.7 | grt rounds 4 overflow 5:26917 -> 10:19209 -> 15:17126 -> 20:16680 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 9.8 | grt rounds 3 overflow 5:37849 -> 10:38699 -> 15:36252 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 9.8 | grt rounds 3 overflow 5:24921 -> 10:18037 -> 15:15084 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 20.3 | grt rounds 4 overflow 5:27548 -> 10:11628 -> 15:6221 -> 20:3928 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 9.8 | grt rounds 3 overflow 5:48001 -> 10:50111 -> 15:49341 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 29.4 | grt rounds 3 overflow 5:48547 -> 10:43151 -> 15:39795 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 21.3 | grt rounds 3 overflow 5:43280 -> 10:40835 -> 15:38869 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 21.3 | grt rounds 3 overflow 5:44318 -> 10:38620 -> 15:37968 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 20.6 | grt rounds 3 overflow 5:59628 -> 10:54127 -> 15:50262 | GRT-LABEL: DESIGN-FAIL: overflow 54127 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 15.8 | grt rounds 4 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-62851 | col_h10_r0_p1__t1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.8701 last 0.8847 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3105141 | col_h10_r0_p1__t1 | 3_3_place_gp | 0.9 | overflow best 0.387 last 0.387 rows 18 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl911743eb-373639 | col_h10_r0_p1__t1 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (8/8 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r0_p4__t1__pv07945c1e-397364 | col_h10_r0_p4__t1 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.6921 last 0.8441 rows 15 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-col_h10_r1__t1__cld01bb4ae-2907339 | col_h10_r1__t1 | pregrt_ff_hold | 1.0 | repair_TNS best 17992.3 last 17992.3 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-356912 | col_h10_r2__t1 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv9ae398c2-2898163 | col_h10_r2__t1 | 5_1_grt | 1.0 | last meaningful line 0.0 h ago (197/202 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-3187088 | col_h9_r0_p1__t1 | 3_3_place_gp | 0.9 | overflow best 0.3819 last 0.3819 rows 4 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3218206 | col_h9_r0_p1__t1 | 3_3_place_gp | 0.9 | overflow best 0.3772 last 0.3772 rows 7 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-3222995 | col_h9_r0_p1__t1 | 3_3_place_gp | 0.9 | overflow best 0.3834 last 0.3834 rows 4 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-2941587 | col_h9_r0_p1__t1 | 3_3_place_gp | 1.0 | overflow best 0.2238 last 0.2238 rows 39 | YOUNG: stage 0.6 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3120804 | col_h9_r0_p2__t1 | 3_4_place_resized | 0.9 | repair_Remaining best 107575 last 107575 rows 4 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-2276310 | col_h9_r0_p2__t1 | tt_setup_repair_grt | 9.1 | repair_Viol best 1087 last 1087 rows 99 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3644485 | col_h9_r0_p2__t1 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (116/116 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv110cabb8-3352541 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.8 | overflow best 0.4685 last 0.4685 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b-3126619 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.9 | overflow best 0.3785 last 0.3785 rows 13 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3270764 | col_h9_r0_p3__t1 | 3_3_place_gp | 0.9 | overflow best 0.5076 last 0.5076 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-3089382 | col_h9_r0_p3__t1 | 3_3_place_gp | 1.0 | overflow best 0.33 last 0.33 rows 34 | YOUNG: stage 0.5 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-3051672 | col_h9_r0_p3__t1 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (180/180 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-3368604 | col_h9_r0_p4__t1 | 3_3_place_gp | 0.8 | overflow best 0.2838 last 0.2838 rows 35 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv89bf360c-3644639 | col_h9_r0_p4__t1 | 3_3_place_gp | 0.7 | overflow best 0.34 last 0.34 rows 20 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-3643245 | col_h9_r0_p4__t1 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pv35382794-3626373 | col_h9_r0_p5__t1 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (104/104 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pvc1b82625-4013216 | col_h9_r0_p5__t1 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (64/64 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-2994465 | col_h9_r0_p5__t1 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (192/192 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t9-1010078 | dsdv_slice_c1x_C__t9 | 1_1_yosys_canonicalize | 2.3 | last meaningful line 1.0 h ago (131/131 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepe_nh_mus_LP__t1-4062670 | dsdv_slice_lepe_nh_mus_LP__t1 | 3_3_place_gp | 0.5 | last meaningful line 0.0 h ago (99/99 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-2362622 | hd_lep0N | 5_1_grt | 10.4 | last meaningful line 2.3 h ago (198/202 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc10 | dpkit-hd_mesh-4142193 | hd_mesh | 3_3_place_gp | 0.5 | overflow best 0.6703 last 0.6703 rows 26 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-kv3_hub_Eo-4062983 | kv3_hub_Eo | 2_1_floorplan | 0.5 | last meaningful line 0.3 h ago (82/82 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t3-4025566 | ot_s81sl_kv_leaf__t3 | synth_odb_v | 0.5 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_kv_leaf__t4-3962225 | ot_s81sl_kv_leaf__t4 | synth_odb_v | 0.5 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t10-72603 | ot_s81sl_leaf__t10 | stage_odb_cap | 0.4 | last meaningful line 0.0 h ago (76/76 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t25__cl55642d17-4189009 | ot_s81sl_leaf__t25 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t28-451853 | ot_s81sl_leaf__t28 | 3_1_place_gp_skip_io | 0.3 | overflow best 0.4116 last 0.4116 rows 31 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t43-3632683 | ot_s81sl_leaf__t43 | tt_setup_repair | 0.7 | repair_Violations best 48 last 109 rows 82 | YOUNG: stage 0.7 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-4184133 | ot_s81sl_leaf__t44 | 3_3_place_gp | 0.5 | overflow best 0.6172 last 0.62 rows 7 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t60-4062057 | ot_s81sl_leaf__t60 | 3_3_place_gp | 0.5 | overflow best 0.6482 last 0.6482 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t66-2946995 | ot_s81sl_leaf__t66 | 3_3_place_gp | 1.0 | overflow best 0.1911 last 0.1911 rows 40 | YOUNG: stage 0.7 h < 1 h |  |
| epyc10 | dpkit-serdes__t13-372470 | serdes__t13 | 1_2_yosys | 0.3 | last meaningful line 0.2 h ago (316/316 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t2-3852722 | serdes__t2 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.1 h ago (92/92 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-4047305 | sle_fw_v2 | 3_3_place_gp | 0.5 | overflow best 0.3789 last 0.3836 rows 17 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-slw_fe_v2__clf110fab2-4041180 | slw_fe_v2 | generate_abstract | 21.8 | last meaningful line 0.1 h ago (948/948 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc2__cl6bcaba89-3790404 | slw_hc2 | 3_3_place_gp | 0.6 | overflow best 0.8964 last 0.8965 rows 15 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-tt_ctlm-4105966 | tt_ctlm | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3754/3754 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | otc-3235470-31032 | 3235470 | gen_lint_yosys | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc10 | otc-3883547-31116 | 3883547 | gen_lint_yosys | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | otc-4023010-28741 | 4023010 | gen_lint_yosys | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_185639_3224747-i1-3809500 | eco_20261120_185639_3224747-i1 | 5_1_grt | 0.6 | last meaningful line 0.3 h ago (138/138 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 5.2 | drt_violations best 1708 last 1708 rows 12 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_233525_2680444-i1t-3910623 | eco_20261120_233525_2680444-i1t | 5_2_route | 2.9 | drt_violations best 61156 last 61156 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_003008_2139459-i1-831859 | eco_20261121_003008_2139459-i1 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_014354_2681516-i1t-3571482 | eco_20261121_014354_2681516-i1t | 5_2_route | 0.7 | last meaningful line 0.1 h ago (254/254 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-gunit--t1-grt-1211009 | gunit--t1-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97-803960 | col_h10_r0_p1__t1 | 2_1_floorplan | 0.2 | repair_Viol best 5514 last 5514 rows 1275 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pv5b623e07-3666069 | col_h10_r0_p4__t1 | stage_odb_cap | 0.8 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-463270 | col_h10_r1__t1 | 3_3_place_gp | 0.4 | overflow best 0.3364 last 0.3376 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvce76611c-507225 | col_h10_r1__t1 | 3_3_place_gp | 0.4 | overflow best 0.35 last 0.3629 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-567843 | col_h10_r2__t1 | 3_5_place_dp | 0.3 | repair_Violations best 6138 last 6138 rows 12 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-853867 | col_h9_r0_p1__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-855446 | col_h9_r0_p2__t1 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9972 last 0.9972 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-145230 | col_h9_r0_p2__t1 | stage_odb_cap | 6.7 | last meaningful line 0.0 h ago (3521/3521 lines) | YOUNG: evidence 6.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv110cabb8-3033723 | col_h9_r0_p3__t1 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (702/702 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-419785 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.4 | overflow best 0.9315 last 0.9315 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-coll_ftc-1206090 | coll_ftc | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t4-528316 | dsdv_slice_c1x_C__t4 | sdc_lint | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t6-626411 | dsdv_slice_c1x_C__t6 | 3_1_place_gp_skip_io | 3.3 | overflow best 0.5033 last 0.5033 rows 34 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t8-612303 | dsdv_slice_c1x_C__t8 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (104/104 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepe_nh_mus_C__t1-1630739 | dsdv_slice_lepe_nh_mus_C__t1 | stage_odb_cap | 3.0 | last meaningful line 0.2 h ago (16/16 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_C__t1-2506911 | dsdv_slice_lepw_mus_C__t1 | 3_3_place_gp | 2.7 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t1-3583234 | ot_s81sl_kv_leaf__t1 | 3_1_place_gp_skip_io | 0.8 | overflow best 0.9341 last 0.9421 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | stage_odb_cap | 6.4 | last meaningful line 0.0 h ago (552/552 lines) | YOUNG: evidence 6.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-954928 | ot_s81sl_leaf__t36 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (389/389 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t52-645358 | ot_s81sl_leaf__t52 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | stage_odb_cap | 5.5 | last meaningful line 0.0 h ago (457/457 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t68-2798472 | ot_s81sl_leaf__t68 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (2454/2454 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t8-1240171 | ot_s81sl_leaf__t8 | 1_1_yosys_canonicalize | 0.0 | last meaningful line -0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t14-3326726 | serdes__t14 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t15__cla2127225-539609 | serdes__t15 | lec | 0.3 | LEC last write 0.0 h ago | YOUNG: evidence 0.3 h < 6 h |  |
| epyc2 | dpkit-serdes__t15__cla3d02796-450387 | serdes__t15 | 2_1_floorplan | 0.4 | last meaningful line 0.0 h ago (86/86 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t16-3293794 | serdes__t16 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | 4_1_cts | 1.4 | last meaningful line 0.2 h ago (4713/4713 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | 4_1_cts | 1.3 | last meaningful line 0.2 h ago (4961/4961 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-2762040 | sle_fw_v2 | 4_1_cts | 1.2 | last meaningful line 0.2 h ago (4761/4761 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v2-3023909 | sle_sc_v2 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (423/423 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-2275472 | sle_sc_v3 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (262/262 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | 4_1_cts | 1.2 | last meaningful line 0.1 h ago (5490/5490 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | stage_odb_cap | 3.5 | last meaningful line 0.0 h ago (357/357 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | stage_odb_cap | 4.0 | last meaningful line 0.0 h ago (374/374 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl55be2264-1570756 | sle_stm_v2 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (386/386 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t22-4024236 | slice_station__t22 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (112/112 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t25-3307284 | slice_station__t25 | 3_3_place_gp | 0.9 | overflow best 0.4097 last 0.4097 rows 33 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-slice_station__t45-4011795 | slice_station__t45 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (114/114 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t52-2803346 | slice_station__t52 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (248/248 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (280/280 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | stage_odb_cap | 3.5 | last meaningful line 0.0 h ago (393/393 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3019094 | slw_fe_v2 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (475/475 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-1889978 | slw_fw_v1 | 4_1_cts | 1.5 | last meaningful line 0.1 h ago (5039/5039 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (325/325 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (410/410 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v3-4010623 | slw_fw_v3 | 3_3_place_gp | 0.6 | overflow best 0.2785 last 0.2814 rows 29 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | stage_odb_cap | 4.0 | last meaningful line 0.0 h ago (308/308 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (301/301 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | stage_odb_cap | 3.5 | last meaningful line 0.0 h ago (393/393 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (323/323 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (407/407 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (251/251 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (386/386 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (158/158 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-3141066 | svc_hi_dsdv_svc_pvso_entry__t2 | 1_2_yosys | 3.8 | last meaningful line 0.0 h ago (776/776 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t5-801765 | svc_hi_dsdv_svc_rs__t5 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (80/80 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-508253 | svc_lo_dsdv_svc_rs__t1 | 1_2_yosys | 0.4 | last meaningful line 0.0 h ago (88/88 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t2-897008 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 0.2 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t3-473545 | svc_lo_dsdv_svc_rs__t3 | 1_2_yosys | 0.4 | last meaningful line 0.0 h ago (93/93 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-690848 | svc_lo_dsdv_svc_rs__t4 | 2_1_floorplan | 7.6 | last meaningful line 0.1 h ago (94/94 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t5-40726 | svc_lo_dsdv_svc_rs__t5 | 1_synth | 6.8 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t7-2982698 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 3.8 | last meaningful line 0.0 h ago (582/582 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs_w__t1-609483 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 3.3 | last meaningful line 0.0 h ago (521/521 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | otc-516902-16365 | 516902 | gen_lint_yosys | 0.4 | last meaningful line 0.4 h ago (1/1 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1-3133296 | eco_20261120_003409_3748726-i1 | 5_3_fillcell | 7.0 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i1t-2059062 | eco_20261120_170022_4017640-i1t | 5_2_route | 1.5 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1-1663436 | eco_recover1120-i1 | 5_2_route | 3.0 | last meaningful line 0.3 h ago (270/271 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | prd-fin-3754125 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | so_1087823_ff_70386 | so_1087823_ff_70386 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_1087823_tt_70386 | so_1087823_tt_70386 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_3850255_ff_28327 | so_3850255_ff_28327 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (336/336 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | so_3850255_tt_28327 | so_3850255_tt_28327 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (336/336 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__clab6e67f2-3976533 | cbn_q01 | 3_5_place_dp | 1.6 | last meaningful line 0.0 h ago (100/100 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 2.7 | last meaningful line 1.0 h ago (198/201 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cl2862d491-418618 | kv3_hgi_v2 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (315/315 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v2__cle0015330-418927 | kv3_hgi_v2 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (316/316 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2-2363517 | kv3_pv_v2 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (1036/1036 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1802160 | kv3_pv_v8 | 4_1_cts | 6.4 | last meaningful line 0.5 h ago (15744/15744 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1803775 | kv3_pv_v8 | 4_1_cts | 6.4 | last meaningful line 0.1 h ago (15650/15650 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-561953 | kv3_pv_v8 | 4_1_cts | 4.1 | last meaningful line 0.3 h ago (15659/15659 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-725922 | kv3_pv_v8 | 4_1_cts | 9.1 | last meaningful line 1.3 h ago (15762/15762 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc7 | dpkit-native59-2890501 | native59 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (360/360 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 2.8 | repair_TNS best 300839 last 300839 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-668507 | ot_s81sl_leaf__t73 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (488/488 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t4-1483997 | serdes__t4 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.2 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3233970 | sle_st_b_v1 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (171/171 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-437345 | sle_stm_v1 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (527/527 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t43-449200 | slice_station__t43 | 5_2_route | 4.1 | drt_violations best 32866 last 32866 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3248657 | slw_fw_v1 | 4_1_cts | 1.9 | last meaningful line 0.1 h ago (5152/5152 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-3255088 | slw_fw_v1 | 4_1_cts | 1.9 | last meaningful line 0.1 h ago (5185/5185 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-3208717 | slw_hc0 | 4_1_cts | 1.9 | last meaningful line 0.2 h ago (5314/5314 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc2__cla3497502__cl16607c7a-441369 | slw_hc2 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (346/346 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-443851 | slw_sc_v1 | postcts_gate_FF | 4.1 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3263016 | slw_st_b_v1 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-791387 | slw_stm_v1 | stage_odb_cap | 4.0 | last meaningful line 0.0 h ago (425/425 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3259392 | slw_stm_v1 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (181/181 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 9.1 |  | NO-DATA: no log found |  |
| epyc7 | klegacy-dsdv_bksel_c_rfda3pt-1968026 | dsdv_bksel_c_rfda3pt | 5_1_grt | 2.9 | last meaningful line 0.1 h ago (1348/1461 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_124815_3297714-i1-942798 | eco_20261120_124815_3297714-i1 | 5_2_route | 2.9 | drt_violations best 73 last 73 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc22584f3-2469769 | col_h9_r1__t1 | 6_report | 11.8 | last meaningful line 0.0 h ago (52/52 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t36-39168 | slice_station__t36 | 5_2_route | 7.7 | last meaningful line 0.7 h ago (275/276 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 37.7 |  | NO-DATA: no log found |  |
| epyc9 | ap-ageom-kw-ot-s81sl-leaf--t38-grt-2585347 | ot-s81sl-leaf--t38-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1655589 | col_h10_r0_p4__t1 | 5_2_route | 9.1 | drt_violations best 12440 last 12440 rows 2 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-4060695 | col_h10_r1__t1 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (178/178 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-1942764 | col_h10_r1__t1 | 5_1_grt | 2.9 | last meaningful line 0.8 h ago (199/215 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pve28d14fa-4078698 | col_h10_r1__t1 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (199/201 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-1933496 | dsdv_slice_c1x_C__t1 | 1_1_yosys_canonicalize | 2.9 | last meaningful line 1.3 h ago (125/125 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t4-4812 | dsdv_slice_c1x_C__t4 | 1_1_yosys_canonicalize | 2.0 | last meaningful line 0.5 h ago (125/125 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_c3x_C__t1-3384294 | dsdv_slice_c3x_C__t1 | 1_1_yosys_canonicalize | 2.3 | last meaningful line 0.8 h ago (131/131 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-894481 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 1.4 | last meaningful line 1.4 h ago (1/1 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-1952006 | hd_ctl | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (891/891 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | dpkit-hd_host_n-4082127 | hd_host_n | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (1114/1114 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-1366470 | ot_s81sl_kv_leaf__t5 | tt_setup_repair | 1.0 | last meaningful line 0.0 h ago (336/336 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-4078805 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 2.0 | repair_Violations best 25901 last 25901 rows 4 | YOUNG: stage 0.6 h < 1 h |  |
| epyc9 | dpkit-serdes__t15__cla3d02796-3958052 | serdes__t15 | 3_4_place_resized | 2.1 | last meaningful line 0.0 h ago (411/411 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-4074295 | slice_station__t37 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (676/676 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-23175 | slice_station__t51 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (644/644 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-80410 | slw_fe_v1 | 5_1_grt | 1.9 | last meaningful line 0.7 h ago (268/1325 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-2003480 | slw_fe_v2 | 5_1_grt | 2.9 | repair_TNS best 6978.63 last 6978.63 rows 8 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (259/259 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-63032 | slw_hc1 | 4_1_cts | 1.9 | last meaningful line 0.2 h ago (5220/5220 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | dpkit-svc_hi_dsdv_svc_rs__t6-1947287 | svc_hi_dsdv_svc_rs__t6 | 1_2_yosys | 2.9 | last meaningful line 0.0 h ago (488/488 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs__t3-1340352 | svc_lo_dsdv_svc_rs__t3 | 1_2_yosys | 1.0 | last meaningful line 0.0 h ago (280/280 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs_w__t1-4075465 | svc_lo_dsdv_svc_rs_w__t1 | 1_2_yosys | 3.8 | last meaningful line 0.0 h ago (648/648 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc9 | kv102-face-qkd_hr_core_peer-1116 | kv102-face-qkd_hr_core_peer | s81-die-r3-c-rsync | 102.7 |  | NO-DATA: empty log |  |
| epyc9 | prd-eco_20261120_185716_1464729-i1t-2754533 | eco_20261120_185716_1464729-i1t | 5_2_route | 7.5 | drt_violations best 72611 last 72611 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
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
| intel2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-175119 | col_h10_r0_p4__t1 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (793/793 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p6__t1__pv0012ba28-182001 | col_h9_r0_p6__t1 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (935/935 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t10-2197686 | dsdv_slice_c1x_C__t10 | 2_2_floorplan_macro | 3.3 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t3-2191361 | dsdv_slice_c1x_C__t3 | 3_1_place_gp_skip_io | 3.3 | overflow best 0.8857 last 0.8857 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-dsdv_slice_c1x_C__t7-931054 | dsdv_slice_c1x_C__t7 | 3_3_place_gp | 4.3 | overflow best 0.7167 last 0.7167 rows 20 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | 5_1_grt | 2.0 | last meaningful line 0.0 h ago (190/191 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 15.6 | last meaningful line 1.0 h ago (225/228 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 15.6 | last meaningful line 0.5 h ago (226/228 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t62-971183 | ot_s81sl_leaf__t62 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (2038/2038 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-279781 | ot_s81sl_leaf__t9 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (356/356 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-phy__t1-2671887 | phy__t1 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (1508/1508 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel2 | dpkit-serdes__t1__clb45db5be-162109 | serdes__t1 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (244/244 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-171983 | sle_sc_v1 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (427/427 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-169076 | sle_sc_v1 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (296/296 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (279/279 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (621/621 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl7b3062fa-155084 | sle_stm_v2 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (677/677 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t27-184972 | slice_station__t27 | 5_1_grt | 2.1 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t41-218779 | slice_station__t41 | 5_1_grt | 2.1 | last meaningful line 0.0 h ago (183/185 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t43-189037 | slice_station__t43 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (648/648 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t49-221823 | slice_station__t49 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (284/284 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | pregrt_ff_hold | 2.1 | repair_TNS best 49579.7 last 49579.7 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-195191 | slw_sc_v1 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (304/304 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v2-195133 | slw_sc_v2 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (384/384 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (268/268 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-320845 | svc_hi_dsdv_svc_rs__t1 | 1_2_yosys | 2.0 | last meaningful line 0.1 h ago (459/459 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t2-2176981 | svc_hi_dsdv_svc_rs__t2 | 1_2_yosys | 3.3 | last meaningful line 0.5 h ago (599/599 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t5-907989 | svc_hi_dsdv_svc_rs__t5 | 2_1_floorplan | 4.3 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-svc_lo_dsdv_svc_rs__t6-416042 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 2.0 | last meaningful line 0.0 h ago (485/485 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel2 | prd-eco_20261120_155439_476619-i1t-3320689 | eco_20261120_155439_476619-i1t | 5_2_route | 2.6 | last meaningful line 0.3 h ago (263/264 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162132_484876-i1t-190176 | eco_20261120_162132_484876-i1t | 5_2_route | 2.1 | last meaningful line 0.1 h ago (262/262 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162140_2433056-i1t-160659 | eco_20261120_162140_2433056-i1t | 5_2_route | 2.1 | last meaningful line 0.3 h ago (131/131 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | prd-eco_20261120_174547_3236169-i1t-2273142 | eco_20261120_174547_3236169-i1t | 5_1_grt | 0.7 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | so_2909615_ff_59318 | so_2909615_ff_59318 | stage_odb_cap | 0.2 | last meaningful line 0.2 h ago (1299/1299 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | so_2909615_tt_59318 | so_2909615_tt_59318 | stage_odb_cap | 0.2 | last meaningful line 0.2 h ago (1299/1299 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 31.3 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv62bca836-2457630 | col_h9_r1__t1 | stage_odb_cap | 11.8 |  | KEEP: col_h9_r1__t1__cl49d7a23e__pv62bca836	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv48cfde67-2459808 | col_h9_r1__t1 | stage_odb_cap | 11.8 |  | KEEP: col_h9_r1__t1__clf32cde8d__pv48cfde67	S81-COL-INHERIT	representative (COORD 11-1 |  |
| epyc9 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-4187921 | col_h10_r1__t1 | 5_1_grt | 2.0 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-col_h10_r2__t1__cl99efd374__pv4c1f67ff-902390 | col_h10_r2__t1 | 5_2_route | 28.7 |  | KEEP: col_h10_r2__t1__cl99efd374__pv4c1f67ff	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-coll_core-1096606 | coll_core | 5_1_grt | 23.8 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw2b_coll	QC-PLAN-R5	coll_core proof, GRT repa |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 18.6 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 11.4 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 65.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | 5_2_route | 41.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | 5_1_grt | 42.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | stage_odb_cap | 20.6 | last meaningful line 0.0 h ago (10360/10360 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | stage_odb_cap | 21.8 | last meaningful line 0.0 h ago (10897/10897 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-native59-3021964 | native59 | pregrt_ff_hold | 19.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | stage_odb_cap | 9.2 | last meaningful line 0.0 h ago (4801/4801 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2315890 | ot_s81sl_leaf__t44 | stage_odb_cap | 10.4 | last meaningful line 0.0 h ago (753/753 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t69-2660757 | ot_s81sl_leaf__t69 | stage_odb_cap | 10.3 | last meaningful line 0.0 h ago (5773/5773 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | stage_odb_cap | 9.1 | last meaningful line 0.0 h ago (4248/4248 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | stage_odb_cap | 23.6 | last meaningful line 0.0 h ago (12023/12023 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | stage_odb_cap | 24.1 | last meaningful line 0.0 h ago (12056/12056 lines) | PROGRESS: log still growing |  |
| epyc10 | prd-eco_20261120_133204_279056-i1t-3773198 | eco_20261120_133204_279056-i1t | 5_2_route | 12.9 | drt_violations best 44 last 44 rows 15 | before-window best 347, window best 44 | PROGRESS: drt_violations improved 87.3 % in window |  |
| epyc10 | prd-eco_20261121_021137_2680521-i1t-410323 | eco_20261121_021137_2680521-i1t | 5_1_grt | 0.3 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 15.7 | last meaningful line 1.1 h ago (1381/1381 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | stage_odb_cap | 13.0 | last meaningful line 0.0 h ago (7440/7440 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 12.8 | last meaningful line 0.0 h ago (7003/7003 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 13.0 | last meaningful line 0.0 h ago (7288/7288 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 7.3 | last meaningful line 0.0 h ago (707/707 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | stage_odb_cap | 6.7 | last meaningful line 0.0 h ago (4133/4133 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | stage_odb_cap | 7.7 | last meaningful line 0.0 h ago (546/546 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (3940/3940 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | stage_odb_cap | 9.0 | last meaningful line 0.0 h ago (4507/4507 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-sle_st_b_v2__pv41c959f3-3745640 | sle_st_b_v2 | generate_abstract | 9.7 | last meaningful line 0.0 h ago (323/323 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 27.6 | drt_violations best 10168 last 22918 rows 19 | before-window best 10389, window best 10168 | PROGRESS: drt_violations improved 2.1 % in window |  |
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
| epyc9 | dpkit-cbf_q00__cl1b5a6458-2899182 | cbf_q00 | stage_odb_cap | 19.9 | last meaningful line 0.0 h ago (1347/1347 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | stage_odb_cap | 9.3 | last meaningful line 0.0 h ago (2419/2419 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv697f40c9-3741672 | col_h9_r0_p1__t1 | stage_odb_cap | 11.3 | last meaningful line 0.0 h ago (1307/1307 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2119395 | col_h9_r0_p1__t1 | stage_odb_cap | 10.6 | last meaningful line 0.0 h ago (1310/1310 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-1256935 | col_h9_r0_p1__t1 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (2059/2059 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-1252986 | col_h9_r0_p1__t1 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (1315/1315 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_fe_v1__cl8210183c-4013675 | sle_fe_v1 | stage_odb_cap | 11.2 | last meaningful line 0.0 h ago (5741/5741 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_fw_v2__cl6740750e-2332778 | sle_fw_v2 | stage_odb_cap | 10.5 | last meaningful line 0.0 h ago (5469/5469 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | stage_odb_cap | 21.5 | last meaningful line 0.0 h ago (11502/11502 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | stage_odb_cap | 21.8 | last meaningful line 0.0 h ago (11545/11545 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | 5_2_route | 9.8 | drt_violations best 58 last 58 rows 10 | before-window best 73630, window best 58 | PROGRESS: drt_violations improved 99.9 % in window |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | stage_odb_cap | 9.9 | last meaningful line 0.0 h ago (5523/5523 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (5129/5129 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (5296/5296 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (5084/5084 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 9.9 | last meaningful line 0.0 h ago (5168/5168 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | 5_2_route | 22.5 | drt_violations best 8797 last 8797 rows 3 | before-window best 100416, window best 8797 | PROGRESS: drt_violations improved 91.2 % in window |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t2-1130517 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 7.1 | last meaningful line 0.3 h ago (860/860 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 28.7 | last meaningful line 0.0 h ago (1710/1710 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 23.7 | last meaningful line 0.0 h ago (1431/1431 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 19.3 | last meaningful line 0.0 h ago (1483/1483 lines) | PROGRESS: log still growing |  |
