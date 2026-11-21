# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 22:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'UNSIGNABLE': 2, 'GRT-LABEL': 27, 'NO-DATA': 13, 'YOUNG': 204, 'KEEP': 3, 'EXCLUDED': 3, 'PROGRESS': 62}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-2362622 | hd_lep0N | 5_1_grt | 14.4 | last meaningful line 6.3 h ago (198/207 lines) | NO-PROGRESS: no new non-iteration log line for 6.3 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | stage_odb_cap | 10.7 | last meaningful line 0.0 h ago (5678/5678 lines) | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -324.26 ps (< -300, gate TT >= -42); job age 10 | UNSIGNABLE (hub cancels after the report hour) |
| epyc7 | dpkit-hd_serdes-2335115 | hd_serdes | tt_setup_repair_grt | 6.7 | repair_Remaining best 42958 last 42958 rows 233 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -373.10 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub cancels after the report hour) |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-4170471 | col_h9_r1__t1 | 5_2_route | 11.7 | drt_violations best 81345 last 81345 rows 1 | before-window best 81345, window best 81345 | NO-PROGRESS: drt_violations best 81345 vs 81345 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3435904 | col_h9_r0_p4__t1 | 5_1_grt | 2.3 | grt rounds 2 overflow 5:22749 -> 10:2145 | GRT-LABEL: DESIGN-FAIL: overflow 2145 at round 10 > 1000 |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-3929554 | dsdv_slice_c1x_C__t6 | 5_1_grt | 29.2 | grt rounds 3 overflow 5:103028 -> 10:81748 -> 15:87287 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_lep0N-304519 | hd_lep0N | 5_1_grt | 25.5 | grt rounds 3 overflow 5:52450 -> 10:50446 -> 15:94955 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 14.6 | grt rounds 6 overflow 5:10650 -> 10:10032 -> 15:4081 -> 20:1683 -> 25:1055 -> 30:418 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t13-2319777 | ot_s81sl_leaf__t13 | 5_1_grt | 14.4 | grt rounds 3 overflow 5:46776 -> 10:46641 -> 15:36400 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 24.3 | grt rounds 4 overflow 5:27623 -> 10:16079 -> 15:12231 -> 20:10781 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t43-3632683 | ot_s81sl_leaf__t43 | 5_1_grt | 4.7 | grt rounds 2 overflow 5:74610 -> 10:60436 | GRT-LABEL: DESIGN-FAIL: overflow 60436 at round 10 > 1000 |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 33.4 | grt rounds 4 overflow 5:46983 -> 10:40238 -> 15:37035 -> 20:39027 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | 5_1_grt | 9.5 | grt rounds 4 overflow 5:19163 -> 10:15333 -> 15:11945 -> 20:8925 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3019094 | slw_fe_v2 | 5_1_grt | 7.8 | grt rounds 1 overflow 5:7402 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_1_grt | 5.3 | grt rounds 6 overflow 5:932 -> 10:787 -> 15:732 -> 20:661 -> 25:275 -> 30:99 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | 5_1_grt | 10.7 | grt rounds 6 overflow 5:3688 -> 10:2561 -> 15:2268 -> 20:1901 -> 25:1852 -> 30:1871 | GRT-LABEL: DESIGN-FAIL: overflow 2561 at round 10 > 1000 |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 6.7 | grt rounds 2 overflow 5:94966 -> 10:134399 | GRT-LABEL: DESIGN-FAIL: overflow 134399 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 2.3 | grt rounds 3 overflow 5:46351 -> 10:38484 -> 15:36882 | GRT-LABEL: DESIGN-FAIL: overflow 38484 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 2.3 | grt rounds 3 overflow 5:42154 -> 10:42391 -> 15:36226 | GRT-LABEL: DESIGN-FAIL: overflow 42391 at round 10 > 1000 |  |
| epyc8 | dpkit-ot_s81sl_leaf__t39-529382 | ot_s81sl_leaf__t39 | 5_1_grt | 22.7 | grt rounds 3 overflow 5:59133 -> 10:59535 -> 15:50667 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 24.1 | grt rounds 4 overflow 5:38322 -> 10:24729 -> 15:20068 -> 20:18920 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-3770871 | dsdv_slice_c1x_C__t1 | 5_1_grt | 29.3 | grt rounds 3 overflow 5:70746 -> 10:63859 -> 15:66890 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-hd_lep0N-579160 | hd_lep0N | 5_1_grt | 63.6 | grt rounds 3 overflow 5:80150 -> 10:46799 -> 15:42444 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 14.8 | grt rounds 3 overflow 5:26741 -> 10:14063 -> 15:10455 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 13.8 | grt rounds 3 overflow 5:37849 -> 10:38699 -> 15:36252 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 8.3 | grt rounds 4 overflow 5:19221 -> 10:14920 -> 15:12366 -> 20:11039 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pc_v3-3350496 | kv3_pc_v3 | 5_1_grt | 2.8 | grt rounds 6 overflow 5:48103 -> 10:17709 -> 15:15585 -> 20:16567 -> 25:14112 -> 30:13066 | GRT-LABEL: DESIGN-FAIL: overflow 17709 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 13.8 | grt rounds 3 overflow 5:24849 -> 10:17793 -> 15:14785 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 25.3 | grt rounds 4 overflow 5:43280 -> 10:40835 -> 15:38869 -> 20:43366 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 24.6 | grt rounds 3 overflow 5:55450 -> 10:53941 -> 15:50262 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 19.8 | grt rounds 5 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-render-d333ed3bc5fa-3237681 | ap-render-d333ed3bc5fa | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3369276 | col_h10_r0_p1__t1 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (330/330 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl911743eb-2636344 | col_h10_r0_p1__t1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (281/281 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv9ae398c2-2898163 | col_h10_r2__t1 | 5_2_route | 5.0 | drt_violations best 71562 last 71562 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2643204 | col_h9_r0_p1__t1 | 5_1_grt | 2.8 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-3339751 | col_h9_r0_p1__t1 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (358/358 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3401748 | col_h9_r0_p2__t1 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (339/339 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-3397522 | col_h9_r0_p2__t1 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (305/305 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-3315861 | col_h9_r0_p3__t1 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (966/966 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3393842 | col_h9_r0_p3__t1 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (864/864 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-3382024 | col_h9_r0_p4__t1 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (326/326 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pv35382794-3396237 | col_h9_r0_p5__t1 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (352/352 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pvc1b82625-3387718 | col_h9_r0_p5__t1 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (328/328 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-2994465 | col_h9_r0_p5__t1 | stage_odb_cap | 5.0 | last meaningful line 0.0 h ago (2522/2522 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t10-2501459 | dsdv_slice_c1x_C__t10 | 3_1_place_gp_skip_io | 2.9 | overflow best 0.8357 last 0.84 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t7-3316818 | dsdv_slice_c1x_C__t7 | 1_2_yosys | 2.3 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-hd_lep0N-2086479 | hd_lep0N | 4_1_cts | 3.2 | last meaningful line 0.1 h ago (10752/10752 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Ei-2127701 | kv3_hub_Ei | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (480/480 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2132807 | ot_s81sl_leaf__t44 | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (329/329 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t66-2946995 | ot_s81sl_leaf__t66 | stage_odb_cap | 5.0 | last meaningful line 0.0 h ago (2414/2414 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-4047305 | sle_fw_v2 | stage_odb_cap | 4.5 | last meaningful line 0.0 h ago (2077/2077 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc2__cla3497502__cl16607c7a-2442091 | slw_hc2 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (1338/1338 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | stage_odb_cap | 3.1 | last meaningful line 0.0 h ago (1670/1670 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | dpkit-tt_ctlm-4105966 | tt_ctlm | stage_odb_cap | 4.5 | last meaningful line 0.0 h ago (435/435 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc10 | prd-count-p1_tc-3809500 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (46/46 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_133204_279056-i1-2847364 | eco_20261120_133204_279056-i1 | 5_2_route | 2.7 | last meaningful line 0.3 h ago (274/275 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_233525_2680444-i1-102804 | eco_20261120_233525_2680444-i1 | 5_2_route | 1.9 | drt_violations best 2029 last 2029 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_014354_2681516-i1-2427560 | eco_20261121_014354_2681516-i1 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (247/247 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1642331 | col_h10_r1__t1 | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (1969/1969 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-853867 | col_h9_r0_p1__t1 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (2012/2012 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-855446 | col_h9_r0_p2__t1 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (2095/2095 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc2 | dpkit-coll_ftc-1206090 | coll_ftc | stage_odb_cap | 4.0 | last meaningful line 0.0 h ago (1843/1843 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (548/548 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (670/670 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-2762040 | sle_fw_v2 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (453/453 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-2275472 | sle_sc_v3 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (499/499 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (473/473 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | 5_1_grt | 7.5 | last meaningful line 0.2 h ago (217/283 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t52-2803346 | slice_station__t52 | stage_odb_cap | 5.2 | last meaningful line 0.0 h ago (2589/2589 lines) | YOUNG: evidence 5.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | stage_odb_cap | 5.9 | last meaningful line 0.0 h ago (517/517 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-1889978 | slw_fw_v1 | stage_odb_cap | 5.5 | last meaningful line 0.0 h ago (507/507 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | stage_odb_cap | 5.9 | last meaningful line 0.0 h ago (562/562 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | 5_1_grt | 7.8 | last meaningful line 0.2 h ago (1191/1210 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v3-4010623 | slw_fw_v3 | stage_odb_cap | 4.6 | last meaningful line 0.0 h ago (2085/2085 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | 5_2_route | 7.5 | last meaningful line 0.0 h ago (137/137 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | stage_odb_cap | 6.6 | last meaningful line 0.0 h ago (560/560 lines) | YOUNG: evidence 6.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | stage_odb_cap | 5.9 | last meaningful line 0.0 h ago (488/488 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t5-801765 | svc_hi_dsdv_svc_rs__t5 | 2_2_floorplan_macro | 4.2 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-508253 | svc_lo_dsdv_svc_rs__t1 | 1_2_yosys | 4.4 | last meaningful line 0.4 h ago (665/665 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t3-473545 | svc_lo_dsdv_svc_rs__t3 | 1_2_yosys | 4.4 | last meaningful line 0.5 h ago (651/651 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_170022_4017640-i1t-2059062 | eco_20261120_170022_4017640-i1t | 5_2_route | 5.5 | drt_violations best 15 last 15 rows 10 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1t-3059556 | eco_20261120_192837_2855950-i1t | 5_2_route | 3.0 | drt_violations best 124200 last 124200 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | so_163617_ff_92727 | so_163617_ff_92727 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (706/706 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_163617_tt_92727 | so_163617_tt_92727 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (706/706 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_44553_ff_16940 | so_44553_ff_16940 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (880/880 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | so_44553_tt_16940 | so_44553_tt_16940 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (880/880 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-slw-su-c--cl19bb38ef-grt-3186229 | slw-su-c--cl19bb38ef-grt | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (264/264 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-slw-su-c--cl92142dac-grt-3223871 | slw-su-c--cl92142dac-grt | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (268/268 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00__cl870de686-279762 | cbf_q00 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (417/417 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q11-283336 | cbf_q11 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (269/269 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__clab6e67f2-24246 | cbn_q01 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (375/375 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-299390 | cbn_q01 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (326/326 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-cbx_q10__cl94a12200_h-1923109 | cbx_q10 | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-3115050 | col_h10_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.2772 last 0.3025 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-645545 | col_h9_r0_p5__t1 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (605/605 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t1-25580 | dsdv_slice_c1x_C__t1 | 1_1_yosys_canonicalize | 2.1 | last meaningful line 0.8 h ago (126/126 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t8-3964056 | dsdv_slice_c1x_C__t8 | 1_1_yosys_canonicalize | 2.3 | last meaningful line 1.0 h ago (128/128 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 1.1 | last meaningful line 0.3 h ago (214/217 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 1.1 | last meaningful line 0.3 h ago (214/217 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv-2749034 | kv3_pv | 2_4_floorplan_pdn | 0.4 | last meaningful line 0.1 h ago (77/77 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1802160 | kv3_pv_v8 | tt_setup_repair | 10.4 | last meaningful line 0.0 h ago (15/15 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1803775 | kv3_pv_v8 | tt_setup_repair | 10.4 | repair_Violations best 13477 last 13477 rows 22 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v8-197680 | kv3_pv_v8 | 3_4_place_resized | 2.0 | last meaningful line 0.1 h ago (570/570 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-561953 | kv3_pv_v8 | 4_1_cts | 8.1 | last meaningful line 1.3 h ago (15720/15720 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc7 | dpkit-native59-304297 | native59 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (432/432 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t28-2944418 | ot_s81sl_leaf__t28 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t31-2004800 | ot_s81sl_leaf__t31 | 3_3_place_gp | 0.9 | overflow best 0.2541 last 0.2541 rows 39 | YOUNG: stage 0.6 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1223391 | ot_s81sl_leaf__t39 | 4_1_cts | 1.4 | last meaningful line 0.0 h ago (3480/3480 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2178470 | ot_s81sl_leaf__t39 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (117/117 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 6.8 | repair_TNS best 13519.9 last 13519.9 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 4_1_cts | 0.6 | last meaningful line 0.0 h ago (3262/3262 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-26511 | serdes__t13 | 2_4_floorplan_pdn | 2.1 | last meaningful line 1.5 h ago (130/130 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-2431677 | sle_ctl | 3_1_place_gp_skip_io | 0.6 | overflow best 0.7214 last 0.7214 rows 19 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-4021915 | sle_fe_v1 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (403/403 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2795334 | sle_hc0 | stage_odb_cap | 0.4 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2989450 | sle_hc1 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-2851055 | sle_hc1 | 3_3_place_gp | 0.3 | overflow best 0.8733 last 0.8733 rows 8 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-slice_station__t25-501299 | slice_station__t25 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (326/326 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-3255088 | slw_fw_v1 | stage_odb_cap | 5.9 | last meaningful line 0.0 h ago (612/612 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2725341 | slw_st_b_v2 | stage_odb_cap | 0.4 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-4010968 | slw_stm_v1 | 5_1_grt | 2.3 | last meaningful line 1.5 h ago (263/980 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3259392 | slw_stm_v1 | stage_odb_cap | 5.9 | last meaningful line 0.0 h ago (419/419 lines) | YOUNG: evidence 5.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_2_route | 6.2 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t6-2568141 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 0.5 | last meaningful line 0.0 h ago (116/116 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 13.1 |  | NO-DATA: no log found |  |
| epyc7 | otc-3104699-30680 | 3104699 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc7 | tg2130-v8c_conv-3155764 | tg2130-v8c_conv | 4_1_cts | 0.2 | last meaningful line 0.1 h ago (71/71 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q01-4192371 | cbf_q01 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (438/438 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-4140201 | col_h9_r0_p2__t1 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (751/751 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pvef55eb84-4139703 | col_h9_r0_p2__t1 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (743/743 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (622/622 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (670/670 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bab1162-4136986 | col_h9_r1__t1 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (614/614 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-4137431 | col_h9_r1__t1 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (568/568 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv534ef85e-4134713 | col_h9_r1__t1 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (624/624 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvf0f1ccb2-4137352 | col_h9_r1__t1 | 5_1_grt | 1.9 | last meaningful line 0.0 h ago (200/205 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-4140136 | col_h9_r1__t1 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (448/448 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-coll_core-4193397 | coll_core | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (463/463 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 1.9 | last meaningful line 0.5 h ago (198/207 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t45-4168642 | ot_s81sl_leaf__t45 | 5_1_grt | 1.9 | last meaningful line 0.1 h ago (202/205 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t27-4170423 | slice_station__t27 | postcts_gate_TT | 1.9 | last meaningful line 0.0 h ago (1248/1248 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-4159358 | slice_station__t37 | 5_1_grt | 1.9 | repair_Viol best 26 last 26 rows 82 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t49-4183263 | slice_station__t49 | postcts_gate_FF | 1.9 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 41.7 |  | NO-DATA: no log found |  |
| epyc8 | otc-4136921-3314 | 4136921 | - | 1.9 |  | NO-DATA: no log found |  |
| epyc8 | otc-4136953-11523 | 4136953 | - | 1.9 |  | NO-DATA: no log found |  |
| epyc8 | otc-4137215-10978 | 4137215 | - | 1.9 |  | NO-DATA: no log found |  |
| epyc8 | so_1613319_ff_43090 | so_1613319_ff_43090 | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (1017/1017 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | so_1613319_tt_43090 | so_1613319_tt_43090 | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (1017/1017 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-sle-su-c-grt-3900274 | sle-su-c-grt | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (308/308 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-slw-fw-v1--clf51c11d8--cl592e3d37-grt-3979866 | slw-fw-v1--clf51c11d8--cl592e3d37-grt | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (316/316 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3331047 | col_h10_r2__t1 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (1828/1828 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pva2e3974f-1256935 | col_h9_r0_p1__t1 | 5_2_route | 14.8 | drt_violations best 55 last 55 rows 14 | YOUNG: evidence 7.2 h < 7.5 h |  |
| epyc9 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-3619477 | col_h9_r0_p5__t1 | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (375/375 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-2673936 | dsdv_slice_lepe_mu_LP__t2 | 4_1_cts | 1.0 | last meaningful line 0.0 h ago (45/45 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-dsdv_slice_lepe_mu_LP__t2-3249388 | dsdv_slice_lepe_mu_LP__t2 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.2272 last 0.2272 rows 40 | YOUNG: stage 0.4 h < 1 h |  |
| epyc9 | dpkit-dsdv_slice_lepw_mu_C__t1-894481 | dsdv_slice_lepw_mu_C__t1 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (420/420 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc9 | dpkit-hd_mesh-3444928 | hd_mesh | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (1574/1574 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_kv_leaf__t5-1366470 | ot_s81sl_kv_leaf__t5 | stage_odb_cap | 5.0 | last meaningful line 0.0 h ago (462/462 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc9 | dpkit-ot_s81sl_leaf__t39-4078805 | ot_s81sl_leaf__t39 | 5_1_grt | 6.0 | last meaningful line 0.1 h ago (188/201 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-serdes__t15__cla2127225-2815774 | serdes__t15 | 3_1_place_gp_skip_io | 0.9 | overflow best 0.8997 last 0.9049 rows 18 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-serdes__t1__clb45db5be-2784503 | serdes__t1 | 3_1_place_gp_skip_io | 0.9 | overflow best 0.8618 last 0.8714 rows 13 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-serdes__t4-3289948 | serdes__t4 | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.1 h ago (130/130 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-3513710 | sle_hc2 | stage_odb_cap | 0.4 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-sle_sc_v1__cl7479a5ec-2241453 | sle_sc_v1 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_sc_v3-4104638 | sle_sc_v3 | rtl_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_a_v2__pv30dda31f__pvd2ec7769-4075837 | sle_st_a_v2 | selrange | 0.0 |  | NO-DATA: empty log |  |
| epyc9 | dpkit-sle_su_l1__cl5ea486db-4105324 | sle_su_l1 | rtl_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t37-4074295 | slice_station__t37 | tt_setup_repair_grt | 6.0 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slice_station__t51-23175 | slice_station__t51 | stage_odb_cap | 6.0 | last meaningful line 0.0 h ago (3019/3019 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-80410 | slw_fe_v1 | postcts_gate_TT | 5.9 | last meaningful line 0.1 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-2212686 | slw_fe_v1 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (248/248 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-1953943 | slw_fe_v2 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (280/280 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v2__clf110fab2-1998391 | slw_fe_v2 | stage_odb_cap | 6.9 | last meaningful line 0.0 h ago (496/496 lines) | YOUNG: evidence 6.9 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc1__cl68f9248e__cle683a076-2337581 | slw_hc1 | 3_3_place_gp | 1.2 | overflow best 0.2978 last 0.3079 rows 136 | YOUNG: stage 0.9 h < 1 h |  |
| epyc9 | dpkit-slw_st_a_v1__clb036e152-4055316 | slw_st_a_v1 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_st_b_v1__cle6023ec2-4103287 | slw_st_b_v1 | sdc_lint | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs__t2-3396484 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 0.5 | last meaningful line 0.0 h ago (121/121 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-svc_lo_dsdv_svc_rs_w__t1-4075465 | svc_lo_dsdv_svc_rs_w__t1 | 2_1_floorplan | 7.8 | last meaningful line 0.1 h ago (94/94 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | kv102-face-qkd_hr_core_peer-1116 | kv102-face-qkd_hr_core_peer | s81-die-r3-c-rsync | 106.7 |  | NO-DATA: empty log |  |
| epyc9 | otc-4114030-4226 | 4114030 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (8/8 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_185716_1464729-i1-1722084 | eco_20261120_185716_1464729-i1 | 5_2_route | 1.6 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | ap-ageom-kw-col-h9-r0-p2--t1--cl0045af7b--pv622a6f97-grt-3852599 | col-h9-r0-p2--t1--cl0045af7b--pv622a6f97-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | ap-ageom-kw-r2-lepw-mu-grt-3864846 | r2-lepw-mu-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-col_base-3975523 | col_base | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_e10-3975285 | col_e10 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3216520 | col_h10_r0_p1__t1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (1012/1012 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3218543 | col_h10_r0_p4__t1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (1208/1208 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-3219217 | col_h10_r1__t1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (1288/1288 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3220432 | col_h10_r1__t1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (1295/1295 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-1995133 | col_h10_r1__t1 | pregrt_ff_hold | 3.5 | repair_Violations best 706 last 706 rows 23 | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (1041/1041 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-3224057 | col_h9_r0_p1__t1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (1058/1058 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3779183 | col_h9_r0_p2__t1 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (1024/1024 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (801/801 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-3785724 | col_h9_r0_p3__t1 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (911/911 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-3790077 | col_h9_r0_p3__t1 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (935/935 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-2942763 | col_h9_r0_p5__t1 | 5_1_grt | 3.0 | last meaningful line 0.0 h ago (148/148 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_rw3-3976384 | col_rw3 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_rw4-3977138 | col_rw4 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1103979 | dsdv_slice_c1x_C__t3 | 3_1_place_gp_skip_io | 4.1 | overflow best 0.8144 last 0.8144 rows 24 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3005235 | dsdv_slice_c1x_C__t5 | 1_1_yosys_canonicalize | 3.0 | last meaningful line 1.0 h ago (128/128 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-glue-3352856 | glue | stage_odb_cap | 5.0 | last meaningful line 0.0 h ago (2181/2181 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v2__cle0015330-2321002 | kv3_hgi_v2 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (1489/1489 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-leaf_base-3975806 | leaf_base | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-leaf_e10-3976645 | leaf_e10 | reg_fanout | 0.0 |  | NO-DATA: empty log |  |
| intel1 | dpkit-leaf_rw3-3976261 | leaf_rw3 | synth_odb_v | 0.0 | last meaningful line 0.0 h ago (4/4 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-leaf_rw4-3977245 | leaf_rw4 | reg_fanout | 0.0 |  | NO-DATA: empty log |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (1566/1566 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-3863987 | sle_ctl | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (868/868 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t22-2407667 | slice_station__t22 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (1551/1551 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | 5_2_route | 10.6 | drt_violations best 67710 last 67710 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_pvso_entry__t1-18505 | svc_hi_dsdv_svc_pvso_entry__t1 | 1_2_yosys | 4.6 | last meaningful line 0.7 h ago (776/776 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t2-996017 | svc_hi_dsdv_svc_rs__t2 | 1_synth | 4.1 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t3-432817 | svc_hi_dsdv_svc_rs__t3 | 1_synth | 4.4 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t4-4054912 | svc_hi_dsdv_svc_rs__t4 | synth_odb_v | 4.7 | last meaningful line 0.1 h ago (4/4 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t6-1410020 | svc_hi_dsdv_svc_rs__t6 | 3_1_place_gp_skip_io | 7.8 | overflow best 0.2108 last 0.2913 rows 135 | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t4-1991847 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 3.5 | last meaningful line 0.0 h ago (522/522 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i1t-2831293 | eco_20261120_192428_3309571-i1t | 5_2_route | 3.0 | drt_violations best 69729 last 69729 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | prd-eco_20261120_194249_3446526-i1t-3450960 | eco_20261120_194249_3446526-i1t | 5_2_route | 2.7 | last meaningful line 0.3 h ago (270/271 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | prd-eco_20261120_211023_313122-i1t-1859870 | eco_20261120_211023_313122-i1t | 5_1_grt | 1.3 | last meaningful line 0.5 h ago (231/1130 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | prd-fin-1846100 | fin | 6_1_fill | 0.0 | last meaningful line 0.0 h ago (12/12 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | stage_odb_cap | 6.0 | last meaningful line 0.0 h ago (3190/3190 lines) | YOUNG: evidence 6.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 19.6 | last meaningful line 5.0 h ago (225/234 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 19.6 | last meaningful line 4.5 h ago (226/234 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t75-2211324 | ot_s81sl_leaf__t75 | stage_odb_cap | 7.3 | last meaningful line 0.0 h ago (704/704 lines) | YOUNG: evidence 7.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-279781 | ot_s81sl_leaf__t9 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (592/592 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-171983 | sle_sc_v1 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (664/664 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-169076 | sle_sc_v1 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (533/533 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (517/517 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (2962/2962 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl7b3062fa-155084 | sle_stm_v2 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (3035/3035 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t27-184972 | slice_station__t27 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (3160/3160 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t41-218779 | slice_station__t41 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (571/571 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t43-189037 | slice_station__t43 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (3012/3012 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t49-221823 | slice_station__t49 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (523/523 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (532/532 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-195191 | slw_sc_v1 | tt_setup_repair_grt | 6.1 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v2-195133 | slw_sc_v2 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (620/620 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | stage_odb_cap | 6.1 | last meaningful line 0.0 h ago (507/507 lines) | YOUNG: evidence 6.1 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-320845 | svc_hi_dsdv_svc_rs__t1 | 3_1_place_gp_skip_io | 6.0 | overflow best 0.9525 last 0.9525 rows 32 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | prd-eco_20261120_155439_476619-i1t-3320689 | eco_20261120_155439_476619-i1t | 5_2_route | 6.6 | drt_violations best 5813 last 5813 rows 1 | YOUNG: evidence 5.2 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162132_484876-i1t-190176 | eco_20261120_162132_484876-i1t | 5_2_route | 6.1 | drt_violations best 5942 last 5942 rows 1 | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162140_2433056-i1-3186007 | eco_20261120_162140_2433056-i1 | 5_1_grt | 0.8 | last meaningful line 0.1 h ago (234/317 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel2 | prd-eco_20261120_174547_3236169-i1t-2273142 | eco_20261120_174547_3236169-i1t | 5_2_route | 4.7 | drt_violations best 6296 last 6296 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel2 | prd-eco_20261120_182729_483429-i1t-3309803 | eco_20261120_182729_483429-i1t | 5_2_route | 4.0 | last meaningful line 0.2 h ago (275/276 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 35.3 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 22.6 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 15.4 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 69.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | 5_2_route | 45.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | 5_1_grt | 46.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | stage_odb_cap | 24.6 | last meaningful line 0.0 h ago (12760/12760 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | stage_odb_cap | 25.8 | last meaningful line 0.0 h ago (13297/13297 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | stage_odb_cap | 13.2 | last meaningful line 0.0 h ago (7201/7201 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2315890 | ot_s81sl_leaf__t44 | stage_odb_cap | 14.4 | last meaningful line 0.0 h ago (992/992 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t69-2660757 | ot_s81sl_leaf__t69 | stage_odb_cap | 14.3 | last meaningful line 0.0 h ago (8163/8163 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | stage_odb_cap | 13.1 | last meaningful line 0.0 h ago (6638/6638 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | stage_odb_cap | 27.6 | last meaningful line 0.0 h ago (14423/14423 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | stage_odb_cap | 28.1 | last meaningful line 0.0 h ago (14456/14456 lines) | PROGRESS: log still growing |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 9.2 | drt_violations best 140 last 140 rows 29 | before-window best 48990, window best 140 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 19.7 | last meaningful line 0.4 h ago (1430/1430 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 16.8 | last meaningful line 0.0 h ago (9393/9393 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 17.0 | last meaningful line 0.0 h ago (9678/9678 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 11.3 | last meaningful line 0.2 h ago (1119/1119 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | stage_odb_cap | 10.4 | last meaningful line 0.0 h ago (791/791 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_sc_v2-3023909 | sle_sc_v2 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (662/662 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | stage_odb_cap | 8.0 | last meaningful line 0.0 h ago (611/611 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | 5_1_grt | 7.5 | repair_TNS best 0 last 0 rows 19 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | stage_odb_cap | 8.0 | last meaningful line 0.0 h ago (545/545 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (538/538 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (644/644 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | stage_odb_cap | 9.2 | last meaningful line 0.0 h ago (625/625 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-3141066 | svc_hi_dsdv_svc_pvso_entry__t2 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (564/564 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | stage_odb_cap | 11.7 | last meaningful line 0.0 h ago (785/785 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-kv3_hgi_v2__cl2862d491-418618 | kv3_hgi_v2 | stage_odb_cap | 8.1 | last meaningful line 0.0 h ago (555/555 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (6328/6328 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | stage_odb_cap | 13.0 | last meaningful line 0.0 h ago (6907/6907 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-3988031 | sle_stm_v1 | 5_1_grt | 2.3 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3248657 | slw_fw_v1 | 5_1_grt | 5.9 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-118433 | slw_hc0 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-443851 | slw_sc_v1 | stage_odb_cap | 8.1 | last meaningful line 0.0 h ago (716/716 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-4168631 | col_h9_r0_p2__t1 | stage_odb_cap | 11.7 | last meaningful line 0.0 h ago (1310/1310 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-478083 | col_h9_r0_p2__t1 | stage_odb_cap | 22.7 | last meaningful line 0.0 h ago (12898/12898 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-4171287 | col_h9_r0_p2__t1 | stage_odb_cap | 11.7 | last meaningful line 0.0 h ago (1368/1368 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pv35382794-4154870 | col_h9_r0_p5__t1 | stage_odb_cap | 11.7 | last meaningful line 0.0 h ago (1414/1414 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-4155323 | col_h9_r0_p5__t1 | stage_odb_cap | 11.7 | last meaningful line 0.0 h ago (1254/1254 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc93af856-4170137 | col_h9_r0_p5__t1 | stage_odb_cap | 11.7 | last meaningful line 0.0 h ago (1303/1303 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-4170921 | col_h9_r1__t1 | stage_odb_cap | 11.7 | last meaningful line 0.0 h ago (1160/1160 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2404958 | col_h9_r1__t1 | stage_odb_cap | 12.3 | last meaningful line 0.0 h ago (1237/1237 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv70f04488-4156907 | col_h9_r1__t1 | stage_odb_cap | 11.7 | last meaningful line 0.0 h ago (1218/1218 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv9a5bd576-2405919 | col_h9_r1__t1 | stage_odb_cap | 12.3 | last meaningful line 0.0 h ago (1227/1227 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvd7af8531-883067 | col_h10_r0_p1__t1 | stage_odb_cap | 13.3 | last meaningful line 0.0 h ago (2658/2658 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-1655589 | col_h10_r0_p4__t1 | 5_2_route | 13.1 | drt_violations best 31 last 31 rows 61 | before-window best 91026, window best 31 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv697f40c9-3741672 | col_h9_r0_p1__t1 | 5_2_route | 15.3 | drt_violations best 27 last 29 rows 49 | before-window best 151250, window best 27 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2119395 | col_h9_r0_p1__t1 | stage_odb_cap | 14.6 | last meaningful line 0.0 h ago (1550/1550 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-1252986 | col_h9_r0_p1__t1 | stage_odb_cap | 14.8 | last meaningful line 0.0 h ago (1555/1555 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-hd_ctl-1952006 | hd_ctl | 5_1_grt | 6.9 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc9 | dpkit-sle_fe_v1__cl8210183c-4013675 | sle_fe_v1 | stage_odb_cap | 15.2 | last meaningful line 0.0 h ago (8131/8131 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | stage_odb_cap | 25.5 | last meaningful line 0.0 h ago (13902/13902 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | stage_odb_cap | 25.8 | last meaningful line 0.0 h ago (13945/13945 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-slw_fe_v2__cle312294d-2003480 | slw_fe_v2 | 5_1_grt | 6.9 | last meaningful line 5.9 h ago (215/921 lines) | PROGRESS: log still growing |  |
| epyc9 | tg2130-tap-grid-2130-3904388 | tg2130-tap-grid-2130 | tg_cts | 0.1 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3793362 | col_h10_r2__t1 | 5_1_grt | 2.6 | repair_TNS best 0 last 0 rows 3 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-ot_s81sl_kv_leaf__t2-1333460 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 7.8 | last meaningful line 0.0 h ago (532/532 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 13.8 | last meaningful line 0.0 h ago (7686/7686 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 13.8 | last meaningful line 0.0 h ago (7484/7484 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 13.9 | last meaningful line 0.0 h ago (7558/7558 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t7-1446461 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 7.7 | last meaningful line 0.3 h ago (975/975 lines) | PROGRESS: log still growing |  |
| intel1 | prd-eco_20261120_221308_1904487-i1t-3602686 | eco_20261120_221308_1904487-i1t | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 32.7 | last meaningful line 0.0 h ago (1949/1949 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 27.7 | last meaningful line 0.0 h ago (1670/1670 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 23.3 | last meaningful line 0.0 h ago (1722/1722 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t62-971183 | ot_s81sl_leaf__t62 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (4428/4428 lines) | PROGRESS: log still growing |  |
