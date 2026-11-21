# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 22:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'GRT-LABEL': 25, 'YOUNG': 200, 'NO-DATA': 11, 'KEEP': 3, 'EXCLUDED': 1, 'PROGRESS': 68}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | stage_odb_cap | 10.9 | last meaningful line 0.0 h ago (5828/5828 lines) | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -324.26 ps (< -300, gate TT >= -42); job age 10 | UNSIGNABLE (hub cancels after the report hour) |
| epyc7 | dpkit-hd_serdes-2335115 | hd_serdes | tt_setup_repair_grt | 6.9 | repair_Viol best 2885 last 2885 rows 73 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -312.17 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub cancels after the report hour) |
| epyc10 | dpkit-col_h9_r0_p5__t1__pveda1ecc9-2994465 | col_h9_r0_p5__t1 | 5_1_grt | 5.3 | grt rounds 3 overflow 5:22576 -> 10:2267 -> 15:1587 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t6-3929554 | dsdv_slice_c1x_C__t6 | 5_1_grt | 29.4 | grt rounds 3 overflow 5:103028 -> 10:81748 -> 15:87287 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_lep0N-2362622 | hd_lep0N | 5_1_grt | 14.6 | grt rounds 2 overflow 5:95762 -> 10:93332 | GRT-LABEL: DESIGN-FAIL: overflow 93332 at round 10 > 1000 |  |
| epyc10 | dpkit-hd_lep0N-304519 | hd_lep0N | 5_1_grt | 25.8 | grt rounds 3 overflow 5:52450 -> 10:47147 -> 15:94955 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t11-1241138 | ot_s81sl_leaf__t11 | 5_1_grt | 14.9 | grt rounds 6 overflow 5:10650 -> 10:7511 -> 15:4081 -> 20:1683 -> 25:1055 -> 30:418 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t13-2319777 | ot_s81sl_leaf__t13 | 5_1_grt | 14.6 | grt rounds 3 overflow 5:46776 -> 10:46641 -> 15:36400 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t17-2145310 | ot_s81sl_leaf__t17 | 5_1_grt | 24.5 | grt rounds 4 overflow 5:27623 -> 10:16079 -> 15:12231 -> 20:10781 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t43-3632683 | ot_s81sl_leaf__t43 | 5_1_grt | 4.9 | grt rounds 3 overflow 5:74610 -> 10:60436 -> 15:72289 | GRT-LABEL: DESIGN-FAIL: overflow 60436 at round 10 > 1000 |  |
| epyc10 | dpkit-sle_ctl__cla4f6f12f-281401 | sle_ctl | 5_1_grt | 33.7 | grt rounds 4 overflow 5:46983 -> 10:40238 -> 15:37035 -> 20:39027 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 7.0 | grt rounds 2 overflow 5:94966 -> 10:134399 | GRT-LABEL: DESIGN-FAIL: overflow 134399 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 2.6 | grt rounds 3 overflow 5:46351 -> 10:38484 -> 15:36882 | GRT-LABEL: DESIGN-FAIL: overflow 38484 at round 10 > 1000 |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 2.5 | grt rounds 3 overflow 5:42154 -> 10:40024 -> 15:36226 | GRT-LABEL: DESIGN-FAIL: overflow 40024 at round 10 > 1000 |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 2.2 | grt rounds 2 overflow 5:23091 -> 10:15850 | GRT-LABEL: DESIGN-FAIL: overflow 15850 at round 10 > 1000 |  |
| epyc8 | dpkit-ot_s81sl_leaf__t39-529382 | ot_s81sl_leaf__t39 | 5_1_grt | 23.0 | grt rounds 4 overflow 5:59133 -> 10:59535 -> 15:50667 -> 20:55563 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t5-3374098 | ot_s81sl_leaf__t5 | 5_1_grt | 24.3 | grt rounds 4 overflow 5:38322 -> 10:24729 -> 15:20068 -> 20:18920 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-dsdv_slice_c1x_C__t1-3770871 | dsdv_slice_c1x_C__t1 | 5_1_grt | 29.3 | grt rounds 3 overflow 5:70746 -> 10:63859 -> 15:66890 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-hd_lep0N-579160 | hd_lep0N | 5_1_grt | 63.6 | grt rounds 3 overflow 5:80150 -> 10:46799 -> 15:42444 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 14.8 | grt rounds 3 overflow 5:26741 -> 10:14063 -> 15:10455 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 14.0 | grt rounds 3 overflow 5:38739 -> 10:38699 -> 15:36252 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 8.5 | grt rounds 4 overflow 5:18843 -> 10:14920 -> 15:12366 -> 20:11039 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pc_v3-3350496 | kv3_pc_v3 | 5_1_grt | 3.0 | grt rounds 6 overflow 5:48103 -> 10:38508 -> 15:15585 -> 20:16567 -> 25:14112 -> 30:13066 | GRT-LABEL: DESIGN-FAIL: overflow 38508 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 14.0 | grt rounds 3 overflow 5:24849 -> 10:17793 -> 15:14785 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 25.5 | grt rounds 4 overflow 5:43280 -> 10:40835 -> 15:38869 -> 20:43366 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 24.9 | grt rounds 3 overflow 5:55450 -> 10:53941 -> 15:50262 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 20.1 | grt rounds 5 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pv67036687-3369276 | col_h10_r0_p1__t1 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (345/345 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r0_p1__t1__cl911743eb-2636344 | col_h10_r0_p1__t1 | stage_odb_cap | 3.1 | last meaningful line 0.0 h ago (296/296 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h10_r2__t1__cl99efd374__pv9ae398c2-2898163 | col_h10_r2__t1 | 5_2_route | 5.3 | drt_violations best 71562 last 71562 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pv8c197f8e-2643204 | col_h9_r0_p1__t1 | stage_odb_cap | 3.1 | last meaningful line 0.0 h ago (433/433 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-3339751 | col_h9_r0_p1__t1 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (373/373 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-3401748 | col_h9_r0_p2__t1 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (354/354 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-3397522 | col_h9_r0_p2__t1 | 5_1_grt | 2.6 | last meaningful line 0.6 h ago (246/442 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-3315861 | col_h9_r0_p3__t1 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (1116/1116 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-3393842 | col_h9_r0_p3__t1 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (1014/1014 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-3382024 | col_h9_r0_p4__t1 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (341/341 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-3435904 | col_h9_r0_p4__t1 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (327/327 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pv35382794-3396237 | col_h9_r0_p5__t1 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (367/367 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-col_h9_r0_p5__t1__pvc1b82625-3387718 | col_h9_r0_p5__t1 | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (343/343 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t10-2501459 | dsdv_slice_c1x_C__t10 | 3_1_place_gp_skip_io | 3.1 | overflow best 0.2458 last 0.2458 rows 39 | YOUNG: stage 0.4 h < 1 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t7-3316818 | dsdv_slice_c1x_C__t7 | 3_1_place_gp_skip_io | 2.6 | overflow best 0.8875 last 0.8875 rows 4 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-hd_lep0N-2086479 | hd_lep0N | 4_1_cts | 3.4 | last meaningful line 0.0 h ago (10806/10806 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hub_Ei-2127701 | kv3_hub_Ei | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (540/540 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2132807 | ot_s81sl_leaf__t44 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (344/344 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc10 | dpkit-ot_s81sl_leaf__t66-2946995 | ot_s81sl_leaf__t66 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (2564/2564 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc10 | dpkit-sle_fw_v2__cl6740750e-4047305 | sle_fw_v2 | 5_1_grt | 4.8 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | dpkit-slw_hc2__cla3497502__cl16607c7a-2442091 | slw_hc2 | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (1488/1488 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (1820/1820 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc10 | dpkit-tt_ctlm-4105966 | tt_ctlm | stage_odb_cap | 4.7 | last meaningful line 0.0 h ago (450/450 lines) | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_133204_279056-i1-2847364 | eco_20261120_133204_279056-i1 | 5_2_route | 2.9 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261120_233525_2680444-i1-102804 | eco_20261120_233525_2680444-i1 | 5_2_route | 2.1 | drt_violations best 2029 last 2029 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_014354_2681516-i1-2427560 | eco_20261121_014354_2681516-i1 | 5_2_route | 0.8 | last meaningful line 0.2 h ago (255/256 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | prd-fin-3809500 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (643/643 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-1642331 | col_h10_r1__t1 | stage_odb_cap | 4.0 | last meaningful line 0.0 h ago (2119/2119 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-853867 | col_h9_r0_p1__t1 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (2162/2162 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-855446 | col_h9_r0_p2__t1 | stage_odb_cap | 4.4 | last meaningful line 0.0 h ago (2245/2245 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| epyc2 | dpkit-coll_ftc-1206090 | coll_ftc | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (1993/1993 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__cl9d029624-2271374 | sle_fw_v1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (563/563 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-2362790 | sle_fw_v1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (685/685 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v2__cl69f5e854-2762040 | sle_fw_v2 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (468/468 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v3-2275472 | sle_sc_v3 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (514/514 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2748037 | sle_st_b_v1 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (488/488 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v1__clbe630b9c-2151392 | sle_stm_v1 | tt_setup_repair_grt | 8.3 | last meaningful line 0.0 h ago (591/591 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t52-2803346 | slice_station__t52 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (2739/2739 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v2__cle312294d-3019094 | slw_fe_v2 | postcts_gate_TT | 8.1 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-1889978 | slw_fw_v1 | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (522/522 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-964135 | slw_fw_v2 | 5_1_grt | 6.2 | last meaningful line 2.3 h ago (213/1122 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v3-4010623 | slw_fw_v3 | stage_odb_cap | 4.9 | last meaningful line 0.0 h ago (2235/2235 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc0__cl1bc59e1c-2142814 | slw_hc0 | postcts_gate_TT | 8.3 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-3066176 | slw_hc1 | 5_1_grt | 8.1 | last meaningful line 0.9 h ago (218/1034 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3063209 | slw_st_b_v2 | 5_1_grt | 6.8 | repair_Remaining best 375537 last 375537 rows 122 | YOUNG: stage 0.6 h < 1 h |  |
| epyc2 | dpkit-slw_stm_v2__cl1ca9c415-3028791 | slw_stm_v2 | tt_setup_repair_grt | 8.1 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-960699 | slw_stm_v2 | stage_odb_cap | 6.2 | last meaningful line 0.0 h ago (503/503 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | stage_odb_cap | 5.6 | last meaningful line 0.0 h ago (412/412 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t5-801765 | svc_hi_dsdv_svc_rs__t5 | 2_4_floorplan_pdn | 4.5 | last meaningful line 0.2 h ago (23/23 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-508253 | svc_lo_dsdv_svc_rs__t1 | 1_2_yosys | 4.6 | last meaningful line 0.6 h ago (665/665 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t3-473545 | svc_lo_dsdv_svc_rs__t3 | 1_2_yosys | 4.6 | last meaningful line 0.8 h ago (651/651 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | prd-count-p1_tc-2059062 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (58/58 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i2t-458842 | eco_20261120_134605_3273412-i2t | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1t-3059556 | eco_20261120_192837_2855950-i1t | 5_2_route | 3.2 | drt_violations best 124200 last 124200 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | so_163617_ff_92727 | so_163617_ff_92727 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (706/706 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | so_163617_tt_92727 | so_163617_tt_92727 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (706/706 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-kv3-pv-v12-grt-3691965 | kv3-pv-v12-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-ot-s81sl-leaf--t31-grt-3794612 | ot-s81sl-leaf--t31-grt | stage_odb_cap | 0.1 | last meaningful line 0.1 h ago (212/212 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00__cl870de686-279762 | cbf_q00 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (432/432 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q11-283336 | cbf_q11 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (284/284 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__clab6e67f2-24246 | cbn_q01 | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (390/390 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__cldd6ea846-299390 | cbn_q01 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (341/341 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-cbx_q10__cl94a12200_h-1923109 | cbx_q10 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (273/273 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-645545 | col_h9_r0_p5__t1 | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (755/755 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t1-25580 | dsdv_slice_c1x_C__t1 | 1_1_yosys_canonicalize | 2.4 | last meaningful line 1.0 h ago (126/126 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_c1x_C__t8-3964056 | dsdv_slice_c1x_C__t8 | 1_1_yosys_canonicalize | 2.5 | last meaningful line 1.2 h ago (129/129 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 1.3 | last meaningful line 0.5 h ago (214/219 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 1.3 | last meaningful line 0.5 h ago (214/219 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv-2749034 | kv3_pv | 3_1_place_gp_skip_io | 0.6 | overflow best 0.8909 last 0.8909 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v8-1802160 | kv3_pv_v8 | tt_setup_repair | 10.6 | repair_Violations best 27874 last 27874 rows 18 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v8-1803775 | kv3_pv_v8 | hold_gate | 10.6 | last meaningful line -0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-197680 | kv3_pv_v8 | 3_5_place_dp | 2.3 | last meaningful line 0.1 h ago (47/47 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-561953 | kv3_pv_v8 | 4_1_cts | 8.4 | last meaningful line 1.5 h ago (15720/15720 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc7 | dpkit-native59-304297 | native59 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (447/447 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t28-2944418 | ot_s81sl_leaf__t28 | 3_3_place_gp | 0.5 | overflow best 0.3539 last 0.3631 rows 28 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1223391 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 1.6 | last meaningful line 0.0 h ago (62/62 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2178470 | ot_s81sl_leaf__t39 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (259/259 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | pregrt_ff_hold | 7.0 | repair_Violations best 18899 last 18899 rows 42 | YOUNG: evidence 4.7 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | tt_setup_repair | 0.8 | repair_Viol best 1187 last 1187 rows 9 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-3897522 | ot_s81sl_leaf__t39 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-serdes__t13-26511 | serdes__t13 | 2_4_floorplan_pdn | 2.4 | last meaningful line 1.8 h ago (130/130 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-2431677 | sle_ctl | 3_3_place_gp | 0.8 | overflow best 0.6742 last 0.6742 rows 3 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-4021915 | sle_fe_v1 | stage_odb_cap | 2.5 | last meaningful line 0.0 h ago (418/418 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2795334 | sle_hc0 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2989450 | sle_hc1 | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-2851055 | sle_hc1 | 3_3_place_gp | 0.6 | overflow best 0.3004 last 0.3249 rows 59 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-slice_station__t25-501299 | slice_station__t25 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (341/341 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-3255088 | slw_fw_v1 | 5_1_grt | 6.2 | last meaningful line 1.8 h ago (223/1119 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-2725341 | slw_st_b_v2 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (76/76 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2852636 | slw_su_l1 | 5_2_route | 6.5 | drt_violations best 124819 last 124819 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t6-2568141 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 0.7 | last meaningful line 0.0 h ago (198/198 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 13.3 |  | NO-DATA: no log found |  |
| epyc7 | tg2130-v8c_conv-3155764 | tg2130-v8c_conv | 4_1_cts | 0.4 | last meaningful line 0.1 h ago (15074/15074 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q01-4192371 | cbf_q01 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (573/573 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pve183b536-4140201 | col_h9_r0_p2__t1 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (766/766 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pvef55eb84-4139703 | col_h9_r0_p2__t1 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (758/758 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv70731479-4138470 | col_h9_r0_p4__t1 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (637/637 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (685/685 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bab1162-4136986 | col_h9_r1__t1 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (629/629 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-4137431 | col_h9_r1__t1 | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (200/211 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv534ef85e-4134713 | col_h9_r1__t1 | 5_1_grt | 2.2 | last meaningful line 0.1 h ago (200/212 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pvf0f1ccb2-4137352 | col_h9_r1__t1 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (404/404 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__clf32cde8d__pv3b9ba75c-4140136 | col_h9_r1__t1 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (463/463 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-coll_core-4193397 | coll_core | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (598/598 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc8 | dpkit-ot_s81sl_leaf__t45-4168642 | ot_s81sl_leaf__t45 | 5_1_grt | 2.2 | last meaningful line 0.3 h ago (202/207 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t27-4170423 | slice_station__t27 | postcts_gate_FF | 2.2 | last meaningful line 0.0 h ago (1258/1258 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-4159358 | slice_station__t37 | 5_1_grt | 2.2 | repair_Viol best 26 last 26 rows 99 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t49-4183263 | slice_station__t49 | postcts_gate_TT | 2.2 | last meaningful line 0.0 h ago (1247/1247 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | otc-1750399-14580 | 1750399 | - | 41.9 |  | NO-DATA: no log found |  |
| epyc8 | otc-4136921-3314 | 4136921 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-4136953-11523 | 4136953 | - | 2.2 |  | NO-DATA: no log found |  |
| epyc8 | otc-4137215-10978 | 4137215 | - | 2.2 |  | NO-DATA: no log found |  |
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
| intel1 | dpkit-cbx_q10__cl89936551_h-4158517 | cbx_q10 | 2_1_floorplan | 0.2 | repair_Viol best 847 last 847 rows 405 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-3216520 | col_h10_r0_p1__t1 | stage_odb_cap | 3.1 | last meaningful line 0.0 h ago (1162/1162 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3218543 | col_h10_r0_p4__t1 | stage_odb_cap | 3.1 | last meaningful line 0.0 h ago (1358/1358 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv0713a75a-3219217 | col_h10_r1__t1 | 5_1_grt | 3.1 | last meaningful line -0.0 h ago (89/89 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-3220432 | col_h10_r1__t1 | stage_odb_cap | 3.1 | last meaningful line 0.0 h ago (1445/1445 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r1__t1__cld01bb4ae-1995133 | col_h10_r1__t1 | 5_1_grt | 3.8 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3793362 | col_h10_r2__t1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (230/230 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | stage_odb_cap | 3.1 | last meaningful line 0.0 h ago (1191/1191 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvb49c16c8-3224057 | col_h9_r0_p1__t1 | stage_odb_cap | 3.1 | last meaningful line 0.0 h ago (1208/1208 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-3779183 | col_h9_r0_p2__t1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (1174/1174 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3784557 | col_h9_r0_p3__t1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (951/951 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47-3785724 | col_h9_r0_p3__t1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (1061/1061 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5-3790077 | col_h9_r0_p3__t1 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (1075/1075 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p5__t1__pvbca8d846-2942763 | col_h9_r0_p5__t1 | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (396/396 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p6__t1__pv0012ba28-201902 | col_h9_r0_p6__t1 | 2_1_floorplan | 0.0 | repair_Viol best 3023 last 3023 rows 96 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t3-1103979 | dsdv_slice_c1x_C__t3 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (108/108 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3005235 | dsdv_slice_c1x_C__t5 | 1_1_yosys_canonicalize | 3.2 | last meaningful line 1.2 h ago (129/129 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-glue-3352856 | glue | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (2331/2331 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_hgi_v2__cle0015330-2321002 | kv3_hgi_v2 | stage_odb_cap | 3.6 | last meaningful line 0.0 h ago (1639/1639 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | dpkit-leaf_base-3975806 | leaf_base | 3_3_place_gp | 0.3 | last meaningful line 0.2 h ago (88/88 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | stage_odb_cap | 3.5 | last meaningful line 0.0 h ago (1716/1716 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-3863987 | sle_ctl | 2_1_floorplan | 0.3 | repair_Viol best 4007 last 4007 rows 535 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-sle_sc_v2-89418 | sle_sc_v2 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (82/82 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-205979 | sle_st_a_v1 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3344099 | sle_st_b_v1 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (1003/1003 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v2__cl55be2264-93654 | sle_stm_v2 | reg_fanout | 0.1 |  | NO-DATA: empty log |  |
| intel1 | dpkit-slice_station__t22-2407667 | slice_station__t22 | tt_setup_repair_grt | 3.5 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-4163143 | slice_station__t40 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9982 last 0.9982 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-slice_station__t40__clc8fb2c8c-4164253 | slice_station__t40 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9982 last 0.9982 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-4161917 | slw_fe_v1 | 2_1_floorplan | 0.2 | last meaningful line 0.1 h ago (85/85 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v2__clf110fab2-4163465 | slw_fe_v2 | 2_1_floorplan | 0.2 | last meaningful line 0.1 h ago (85/85 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | 5_2_route | 10.9 | drt_violations best 67710 last 67710 rows 1 | YOUNG: evidence 4.5 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1a1c1f8f-110077 | slw_su_l0 | 3_1_place_gp_skip_io | 0.1 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_pvso_entry__t1-18505 | svc_hi_dsdv_svc_pvso_entry__t1 | 1_synth | 4.9 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t2-996017 | svc_hi_dsdv_svc_rs__t2 | reg_fanout | 4.4 |  | NO-DATA: empty log |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t3-432817 | svc_hi_dsdv_svc_rs__t3 | reg_fanout | 4.7 |  | NO-DATA: empty log |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t4-4054912 | svc_hi_dsdv_svc_rs__t4 | 2_1_floorplan | 4.9 | last meaningful line 0.0 h ago (90/90 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t6-1410020 | svc_hi_dsdv_svc_rs__t6 | 3_1_place_gp_skip_io | 8.0 | overflow best 0.2108 last 0.2884 rows 157 | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t4-1991847 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 3.8 | last meaningful line 0.0 h ago (543/543 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t5-28461 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i1t-2831293 | eco_20261120_192428_3309571-i1t | 5_2_route | 3.3 | drt_violations best 69729 last 69729 rows 1 | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | prd-eco_20261120_211023_313122-i1t-1859870 | eco_20261120_211023_313122-i1t | 5_2_route | 1.5 | last meaningful line 0.0 h ago (123/123 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_20261120_221308_1904487-i1t-3602686 | eco_20261120_221308_1904487-i1t | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (244/1362 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | prd-fin-1846100 | fin | 6_report | 0.3 | last meaningful line 0.0 h ago (251/251 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-eng__t1-323145 | eng__t1 | stage_odb_cap | 6.3 | last meaningful line 0.0 h ago (3340/3340 lines) | YOUNG: evidence 6.3 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 19.9 | last meaningful line 4.8 h ago (226/234 lines) | YOUNG: evidence 5.6 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t9-279781 | ot_s81sl_leaf__t9 | stage_odb_cap | 6.3 | last meaningful line 0.0 h ago (607/607 lines) | YOUNG: evidence 6.3 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl115da35f-171983 | sle_sc_v1 | stage_odb_cap | 6.4 | last meaningful line 0.0 h ago (679/679 lines) | YOUNG: evidence 6.4 h < 7.5 h |  |
| intel2 | dpkit-sle_sc_v1__cl7479a5ec-169076 | sle_sc_v1 | stage_odb_cap | 6.4 | last meaningful line 0.0 h ago (548/548 lines) | YOUNG: evidence 6.4 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-195086 | sle_st_b_v2 | stage_odb_cap | 6.3 | last meaningful line 0.0 h ago (532/532 lines) | YOUNG: evidence 6.3 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__clfde1249e-154384 | sle_st_b_v2 | stage_odb_cap | 6.4 | last meaningful line 0.0 h ago (3102/3102 lines) | YOUNG: evidence 6.4 h < 7.5 h |  |
| intel2 | dpkit-sle_stm_v2__cl7b3062fa-155084 | sle_stm_v2 | stage_odb_cap | 6.4 | last meaningful line 0.0 h ago (3175/3175 lines) | YOUNG: evidence 6.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t27-184972 | slice_station__t27 | stage_odb_cap | 6.4 | last meaningful line 0.0 h ago (3310/3310 lines) | YOUNG: evidence 6.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t41-218779 | slice_station__t41 | 5_2_route | 6.3 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t43-189037 | slice_station__t43 | stage_odb_cap | 6.4 | last meaningful line 0.0 h ago (3162/3162 lines) | YOUNG: evidence 6.4 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t49-221823 | slice_station__t49 | stage_odb_cap | 6.3 | last meaningful line 0.0 h ago (538/538 lines) | YOUNG: evidence 6.3 h < 7.5 h |  |
| intel2 | dpkit-slw_fe_v1__cl95cd1d0c-176657 | slw_fe_v1 | stage_odb_cap | 6.4 | last meaningful line 0.0 h ago (547/547 lines) | YOUNG: evidence 6.4 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-195191 | slw_sc_v1 | postcts_gate_TT | 6.3 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v2-195133 | slw_sc_v2 | stage_odb_cap | 6.3 | last meaningful line 0.0 h ago (635/635 lines) | YOUNG: evidence 6.3 h < 7.5 h |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-212393 | slw_st_b_v1 | stage_odb_cap | 6.3 | last meaningful line 0.0 h ago (522/522 lines) | YOUNG: evidence 6.3 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-320845 | svc_hi_dsdv_svc_rs__t1 | 3_1_place_gp_skip_io | 6.3 | overflow best 0.4391 last 0.4391 rows 54 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | prd-eco_20261120_155439_476619-i1t-3320689 | eco_20261120_155439_476619-i1t | 5_2_route | 6.8 | drt_violations best 5813 last 5813 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162132_484876-i1t-190176 | eco_20261120_162132_484876-i1t | 5_2_route | 6.4 | drt_violations best 5942 last 5942 rows 1 | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel2 | prd-eco_20261120_162140_2433056-i1-3186007 | eco_20261120_162140_2433056-i1 | 5_1_grt | 1.1 | last meaningful line 0.4 h ago (234/1350 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | prd-eco_20261120_174547_3236169-i1t-2273142 | eco_20261120_174547_3236169-i1t | 5_2_route | 4.9 | drt_violations best 6296 last 6296 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel2 | prd-eco_20261120_182729_483429-i1t-3309803 | eco_20261120_182729_483429-i1t | 5_2_route | 4.2 | last meaningful line 0.3 h ago (277/278 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 35.6 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc9 | dpkit-coll_core-987854 | coll_core | 5_1_grt | 22.6 |  | KEEP: fable-fix-qc-collcore/opus/pkits/pkw4_coll	QC-PLAN-R5	coll_core read-register cl |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 15.4 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | 5_2_route | 45.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-kv3_pv_v8-1559990 | kv3_pv_v8 | stage_odb_cap | 24.9 | last meaningful line 0.0 h ago (12910/12910 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-kv3_pv_v8-4169642 | kv3_pv_v8 | stage_odb_cap | 26.0 | last meaningful line 0.0 h ago (13447/13447 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | stage_odb_cap | 13.4 | last meaningful line 0.0 h ago (7351/7351 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2315890 | ot_s81sl_leaf__t44 | stage_odb_cap | 14.6 | last meaningful line 0.0 h ago (1007/1007 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-ot_s81sl_leaf__t69-2660757 | ot_s81sl_leaf__t69 | stage_odb_cap | 14.6 | last meaningful line 0.0 h ago (8313/8313 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | stage_odb_cap | 13.4 | last meaningful line 0.0 h ago (6788/6788 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | stage_odb_cap | 27.8 | last meaningful line 0.0 h ago (14563/14563 lines) | PROGRESS: log still growing |  |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | stage_odb_cap | 28.3 | last meaningful line 0.0 h ago (14606/14606 lines) | PROGRESS: log still growing |  |
| epyc10 | prd-eco_20261120_211525_1604334-i1t-1948725 | eco_20261120_211525_1604334-i1t | 5_2_route | 9.5 | drt_violations best 131 last 131 rows 30 | before-window best 48990, window best 131 | PROGRESS: drt_violations improved 99.7 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 20.0 | last meaningful line 0.6 h ago (1430/1430 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 17.1 | last meaningful line 0.0 h ago (9543/9543 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 17.3 | last meaningful line 0.0 h ago (9828/9828 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 11.6 | last meaningful line 0.1 h ago (1124/1124 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | stage_odb_cap | 10.6 | last meaningful line 0.0 h ago (806/806 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | stage_odb_cap | 9.7 | last meaningful line 0.0 h ago (711/711 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_sc_v2-3023909 | sle_sc_v2 | stage_odb_cap | 8.1 | last meaningful line 0.0 h ago (677/677 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-70093 | sle_st_b_v2 | stage_odb_cap | 7.7 | last meaningful line 0.0 h ago (609/609 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-961361 | slw_fe_v1 | 5_1_grt | 6.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-58079 | slw_fe_v1 | stage_odb_cap | 7.7 | last meaningful line 0.0 h ago (645/645 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-slw_fw_v2__cl8f84514c-3078005 | slw_fw_v2 | stage_odb_cap | 8.0 | last meaningful line 0.0 h ago (663/663 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-26636 | slw_sc_v1 | stage_odb_cap | 7.7 | last meaningful line 0.0 h ago (647/647 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | stage_odb_cap | 9.4 | last meaningful line 0.0 h ago (640/640 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t2-3141066 | svc_hi_dsdv_svc_pvso_entry__t2 | stage_odb_cap | 8.0 | last meaningful line 0.0 h ago (624/624 lines) | PROGRESS: log still growing |  |
| epyc7 | ap-ageom-kw-col-h10-r2--t1--cl1f5d6c2a--pv418d3dc0-grt-3824584 | col-h10-r2--t1--cl1f5d6c2a--pv418d3dc0-grt | 3_5_place_dp | 0.1 | repair_Violations best 0 last 0 rows 35 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | stage_odb_cap | 11.0 | last meaningful line 0.0 h ago (6673/6673 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | stage_odb_cap | 11.9 | last meaningful line 0.0 h ago (800/800 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-kv3_hgi_v2__cl2862d491-418618 | kv3_hgi_v2 | stage_odb_cap | 8.4 | last meaningful line 0.0 h ago (570/570 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | stage_odb_cap | 11.1 | last meaningful line 0.0 h ago (6478/6478 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | stage_odb_cap | 13.2 | last meaningful line 0.0 h ago (7057/7057 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-3988031 | sle_stm_v1 | 5_1_grt | 2.5 | repair_TNS best 0 last 0 rows 19 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-3248657 | slw_fw_v1 | 5_1_grt | 6.2 | repair_TNS best 0 last 0 rows 10 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_hc0__cl4f54b7a3-118433 | slw_hc0 | pregrt_ff_hold | 2.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v1__cl63e5a7a2-443851 | slw_sc_v1 | stage_odb_cap | 8.4 | last meaningful line 0.0 h ago (731/731 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl2086fa2c-4010968 | slw_stm_v1 | 5_1_grt | 2.5 | repair_TNS best 0 last 0 rows 8 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3259392 | slw_stm_v1 | 5_1_grt | 6.2 | repair_TNS best 0 last 0 rows 5 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-4168631 | col_h9_r0_p2__t1 | stage_odb_cap | 11.9 | last meaningful line 0.0 h ago (1325/1325 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv2744f675-478083 | col_h9_r0_p2__t1 | stage_odb_cap | 23.0 | last meaningful line 0.0 h ago (13048/13048 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-4171287 | col_h9_r0_p2__t1 | stage_odb_cap | 11.9 | last meaningful line 0.0 h ago (1383/1383 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pv35382794-4154870 | col_h9_r0_p5__t1 | stage_odb_cap | 11.9 | last meaningful line 0.0 h ago (1429/1429 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc6e5797f-4155323 | col_h9_r0_p5__t1 | stage_odb_cap | 11.9 | last meaningful line 0.0 h ago (1269/1269 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r0_p5__t1__pvc93af856-4170137 | col_h9_r0_p5__t1 | stage_odb_cap | 11.9 | last meaningful line 0.0 h ago (1318/1318 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-4170471 | col_h9_r1__t1 | 5_2_route | 11.9 | drt_violations best 13103 last 13103 rows 2 | before-window best 81345, window best 13103 | PROGRESS: drt_violations improved 83.9 % in window |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv152ea348-4170921 | col_h9_r1__t1 | stage_odb_cap | 11.9 | last meaningful line 0.0 h ago (1175/1175 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9-2404958 | col_h9_r1__t1 | stage_odb_cap | 12.5 | last meaningful line 0.0 h ago (1251/1251 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv70f04488-4156907 | col_h9_r1__t1 | stage_odb_cap | 11.9 | last meaningful line 0.0 h ago (1233/1233 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv9a5bd576-2405919 | col_h9_r1__t1 | 5_2_route | 12.5 | drt_violations best 0 last 0 rows 9 | PROGRESS: drt_violations reached 0 |  |
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
| intel1 | dpkit-ot_s81sl_kv_leaf__t2-1333460 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 8.0 | last meaningful line 0.0 h ago (562/562 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 14.0 | last meaningful line 0.0 h ago (7836/7836 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 14.0 | last meaningful line 0.0 h ago (7624/7624 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 14.2 | last meaningful line 0.0 h ago (7708/7708 lines) | PROGRESS: log still growing |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t7-1446461 | svc_lo_dsdv_svc_rs__t7 | 1_2_yosys | 8.0 | last meaningful line 0.5 h ago (975/975 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 32.9 | last meaningful line 0.0 h ago (1964/1964 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 28.0 | last meaningful line 0.0 h ago (1685/1685 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 19.9 | last meaningful line 5.3 h ago (225/234 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 23.5 | last meaningful line 0.0 h ago (1737/1737 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t62-971183 | ot_s81sl_leaf__t62 | stage_odb_cap | 8.6 | last meaningful line 0.0 h ago (4578/4578 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-ot_s81sl_leaf__t75-2211324 | ot_s81sl_leaf__t75 | stage_odb_cap | 7.6 | last meaningful line 0.0 h ago (719/719 lines) | PROGRESS: log still growing |  |
