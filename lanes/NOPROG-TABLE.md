# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 13:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 3, 'GRT-LABEL': 4, 'NO-DATA': 11, 'YOUNG': 82, 'PROGRESS': 25}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 46.0 | last meaningful line 20.0 h ago (622/622 lines) | NO-PROGRESS: no new non-iteration log line for 20.0 h | REPORT-ONLY: lane-own kit (romw-1119 decides; neve |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | pregrt_ff_hold | 14.1 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc9 | dpkit-kv3_pc_v3-299010 | kv3_pc_v3 | pregrt_ff_hold | 12.9 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 6 h | REPORT-ONLY: lane-own kit (FAM-KV-IOPC-R4 decides; |
| epyc10 | dpkit-coll_core-2755880 | coll_core | 5_1_grt | 8.0 | grt rounds 2 overflow 5:6694 -> 10:735 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-3134610 | dsdv_slice_kv512_C__t1 | 5_1_grt | 11.3 | grt rounds 2 overflow 5:166212 -> 10:139687 | GRT-LABEL: DESIGN-FAIL: overflow 139687 at round 10 > 1000 |  |
| epyc8 | dpkit-kv3_hub_C-2984711 | kv3_hub_C | 5_1_grt | 16.2 | grt rounds 2 overflow 5:13375 -> 10:10994 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_pv_v3e-280312 | kv3_pv_v3e | 5_1_grt | 8.9 | grt rounds 0 overflow  | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-dsdv-slice-lepe-nh-mus-C--t1-dump-2345226 | dsdv-slice-lepe-nh-mus-C--t1-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | ap-ageom-kw-dsdv-slice-lepe-nh-mus-C--t1-grt-2345226 | dsdv-slice-lepe-nh-mus-C--t1-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc10 | dpkit-coll_core-3843742 | coll_core | 5_1_grt | 7.1 | last meaningful line 0.3 h ago (200/206 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_c1x_C__t8-2955109 | dsdv_slice_c1x_C__t8 | pregrt_ff_hold | 7.9 | repair_TNS best 27524.8 last 27524.8 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc10 | dpkit-dsdv_slice_lepw_mus_C__t1-439143 | dsdv_slice_lepw_mus_C__t1 | 3_3_place_gp | 3.4 | overflow best 0.7527 last 0.7527 rows 7 | YOUNG: stage 0.1 h < 1 h |  |
| epyc10 | dpkit-kv3_hub_Wo-1048008 | kv3_hub_Wo | 5_1_grt | 9.2 | last meaningful line 0.3 h ago (1315/2053 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc10 | eco-abs-2111514 | eco-abs | generate_abstract | 0.3 | last meaningful line 0.2 h ago (369/369 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | otc-1692786-27381 | 1692786 | signoff | 0.7 | last meaningful line 0.6 h ago (3/3 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc10 | otc-274226-16996 | 274226 | 4_1_cts | 3.5 | last meaningful line 0.2 h ago (8709/8709 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc10 | prd-count-p1_tc-3082261 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (48/48 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261123_130918_3027414-i1-366371 | eco_20261123_130918_3027414-i1 | 5_2_route | 3.4 | drt_violations best 1 last 1 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t10-1266566 | dsdv_slice_c1x_C__t10 | 3_4_place_resized | 2.1 | last meaningful line 0.0 h ago (399/399 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_c1x_C__t3-1222805 | dsdv_slice_c1x_C__t3 | 3_5_place_dp | 2.1 | last meaningful line 0.1 h ago (36/36 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_C-2221699 | kv3_hub_C | 3_4_place_resized | 8.2 | last meaningful line 0.1 h ago (449/449 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | otc-2072262-2525 | 2072262 | signoff | 1.3 | last meaningful line 1.3 h ago (3/3 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | otc-2508762-7926 | 2508762 | signoff | 1.0 | last meaningful line 0.8 h ago (3/3 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | otc-356178-19590 | 356178 | signoff | 2.8 | last meaningful line 2.8 h ago (3/3 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | prd-count-p1_tc-3323150 | count-p1_tc | prd_count_p1_tc | 0.0 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_181101_3945375-i2t-1118869 | eco_20261122_181101_3945375-i2t | 5_2_route | 2.2 | last meaningful line 0.1 h ago (282/283 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | prd-eco_20261122_190506_3875261-i2t-153753 | eco_20261122_190506_3875261-i2t | 5_2_route | 3.0 | drt_violations best 8883 last 8883 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i1t-768660 | eco_20261123_102841_2122262-i1t | 5_2_route | 2.5 | last meaningful line 0.1 h ago (280/281 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i1t-830727 | eco_20261123_103136_2028090-i1t | 5_2_route | 2.4 | last meaningful line 0.2 h ago (282/283 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | so_3083871_ff_5117 | so_3083871_ff_5117 | generate_abstract | 0.4 | last meaningful line 0.2 h ago (911/911 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | so_3083871_tt_5117 | so_3083871_tt_5117 | generate_abstract | 0.4 | last meaningful line 0.2 h ago (911/911 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_1_grt | 11.3 | last meaningful line 0.1 h ago (2618/2642 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | pregrt_ff_hold | 4.6 | repair_TNS best 275302 last 275302 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_kv512_C__t1-935860 | dsdv_slice_kv512_C__t1 | 3_5_place_dp | 3.0 | last meaningful line 0.8 h ago (36/36 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepw_mu_LP__t2-3679922 | dsdv_slice_lepw_mu_LP__t2 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (4460/4460 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-dsdv_slice_lepw_mus_LP__t2-3772065 | dsdv_slice_lepw_mus_LP__t2 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (5245/5246 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-hd_ctl-865079 | hd_ctl | postcts_gate_TT | 3.1 | last meaningful line 0.0 h ago (902/902 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5n-1629928 | kv3_pv_v5n | 3_5_place_dp | 2.4 | last meaningful line 0.1 h ago (140/140 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5ne-1567175 | kv3_pv_v5ne | 3_5_place_dp | 2.5 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | otc-3723552-11009 | 3723552 | - | 4.3 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261123_080018_715668-i1t-847605 | eco_20261123_080018_715668-i1t | 5_3_fillcell | 12.9 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_124118_879330-i1-896574 | eco_20261123_124118_879330-i1 | 5_2_route | 3.1 | drt_violations best 364 last 364 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_160238_2681508-i1-2430323 | eco_20261123_160238_2681508-i1 | 5_2_route | 1.7 | drt_violations best 22 last 22 rows 1 | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i1t-127041 | eco_20261123_171023_3055226-i1t | 5_2_route | 3.8 | drt_violations best 15147 last 15147 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171842_3718765-i1-3800902 | eco_20261123_171842_3718765-i1 | 5_1_grt | 0.4 | last meaningful line 0.2 h ago (258/876 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_184706_2375049-i1t-1905995 | eco_20261123_184706_2375049-i1t | 5_2_route | 2.2 | drt_violations best 40230 last 40230 rows 1 | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v3-2034945 | kv3_hg_v3 | pregrt_ff_hold | 5.9 | repair_TNS best 449968 last 449968 rows 1 | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hub_Eo-3667658 | kv3_hub_Eo | 5_1_grt | 9.2 | last meaningful line 0.2 h ago (2124/2137 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t27-3500785 | slice_station__t27 | 5_2_route | 4.0 | last meaningful line 0.3 h ago (263/264 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t37-196363 | slice_station__t37 | postcts_gate_FF | 3.6 | last meaningful line -0.0 h ago (20836/20836 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t38-3922551 | slice_station__t38 | 5_2_route | 3.8 | last meaningful line 0.3 h ago (269/270 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t42__clcf44e680-182679 | slice_station__t42 | 5_2_route | 3.6 | last meaningful line 0.1 h ago (269/270 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t43-157875 | slice_station__t43 | 5_2_route | 3.6 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t49-194878 | slice_station__t49 | 5_2_route | 3.6 | last meaningful line 0.5 h ago (250/251 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cl39451317-3753261 | slice_station__t50 | 5_2_route | 3.9 | last meaningful line 0.3 h ago (260/261 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t50__cld84c9e24-169001 | slice_station__t50 | 5_2_route | 3.6 | last meaningful line 0.3 h ago (262/263 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t6__cl0755c26e-3930284 | slice_station__t6 | 5_2_route | 3.8 | drt_violations best 16050 last 16050 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc8 | dpkit-slice_station__t6__cl54a9ceeb-3927462 | slice_station__t6 | 5_2_route | 3.8 | drt_violations best 16940 last 16940 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i1-805274 | eco_20261123_120225_75582-i1 | 5_2_route | 3.4 | drt_violations best 15245 last 15245 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_140713_549985-i1-1751532 | eco_20261123_140713_549985-i1 | 5_2_route | 2.9 | drt_violations best 3 last 3 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i1-1884148 | eco_20261123_163717_2005956-i1 | 5_1_grt | 0.8 | last meaningful line 0.5 h ago (240/1854 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1t-2762092 | eco_20261123_164145_1995767-i1t | 5_1_grt | 4.3 | repair_Viol best 2085 last 2085 rows 1 | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc9 | dpkit-sle_fw_v1__cl9d029624-2868290 | sle_fw_v1 | 5_2_route | 14.0 | drt_violations best 137762 last 137762 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc9 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-152496 | slw_fe_v1 | 5_2_route | 13.0 | drt_violations best 9225 last 9225 rows 3 | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-4155393 | slw_fw_v1 | 6_report | 16.0 | last meaningful line 0.0 h ago (1058/1058 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-tt_ctlm-3806984 | tt_ctlm | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (105/105 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-1627700-2565 | 1627700 | - | 14.7 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco-i2-3887394 | eco-i2 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (89/89 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_142403_3177550-i2-3394943 | eco_20261123_142403_3177550-i2 | 5_2_route | 0.6 | last meaningful line 0.0 h ago (253/254 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i1t-2251452 | eco_20261123_190031_3093983-i1t | 5_2_route | 2.0 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_205006_3008284-i1-3778492 | eco_20261123_205006_3008284-i1 | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | qc-coll-s-reform-maplec-1123 | qc-coll-s-reform-maplec | - | 2.7 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-hdctl_counted_fsmhint | relec1122-ml-hdctl_counted_fsmhint | - | 1.9 |  | NO-DATA: no log found |  |
| epyc9 | relec1122-ml-hdctl_r8_fsmhint | relec1122-ml-hdctl_r8_fsmhint | - | 1.9 |  | NO-DATA: no log found |  |
| epyc9 | so_3829600_ff_86335 | so_3829600_ff_86335 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc9 | so_3829600_tt_86335 | so_3829600_tt_86335 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t4-19056 | dsdv_slice_c1x_C__t4 | 1_1_yosys_canonicalize | 2.5 | last meaningful line 1.0 h ago (127/127 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t6-459624 | dsdv_slice_c1x_C__t6 | 1_1_yosys_canonicalize | 2.1 | last meaningful line 0.7 h ago (132/132 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t7-1834998 | dsdv_slice_c1x_C__t7 | sdc_lint | 0.9 | last meaningful line 0.9 h ago (1/1 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c3x_C__t1-142746 | dsdv_slice_c3x_C__t1 | 1_1_yosys_canonicalize | 2.4 | last meaningful line 1.0 h ago (134/134 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_lepw_mu_C__t1-2396125 | dsdv_slice_lepw_mu_C__t1 | sdc_lint | 0.3 | last meaningful line 0.3 h ago (1/1 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-3836737 | kv3_hub_Ei | generate_abstract | 30.7 | last meaningful line 0.4 h ago (1030/1030 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-sle_fw_v1__clf58b4dfb-2888208 | sle_fw_v1 | 5_2_route | 16.4 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl9beb65e6-1695218 | slw_stm_v2 | 5_2_route | 17.1 | drt_violations best 71799 last 71799 rows 1 | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts.otrun | 1.4 | last meaningful line 0.5 h ago (5/5 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts.otrun | 0.7 | last meaningful line 0.5 h ago (5/5 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | otc-2759871-31481 | 2759871 | 3_5_place_dp | 3.8 | last meaningful line 0.0 h ago (80/80 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | otc-3099315-18388 | 3099315 | 3_5_place_dp | 3.5 | last meaningful line 1.5 h ago (29/29 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | otc-571036-12201 | 571036 | signoff | 2.0 | last meaningful line 1.8 h ago (3/3 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | prd-eco_20261122_143408_943433-i2-876871 | eco_20261122_143408_943433-i2 | 5_2_route | 1.8 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | prd-eco_20261123_090657_914087-i1t-2682219 | eco_20261123_090657_914087-i1t | 5_1_grt | 3.8 | repair_Viol best 1637 last 1637 rows 1 | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel1 | prd-fin-2683723 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (86/86 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | so_2586274_ff_8228 | so_2586274_ff_8228 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | so_2586274_tt_8228 | so_2586274_tt_8228 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel2 | dpkit-col_h10_r1__t1__cld01bb4ae-2731145 | col_h10_r1__t1 | 5_2_route | 9.0 | last meaningful line 0.1 h ago (287/288 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-370750 | coll_ftm | 5_2_route | 2.0 | drt_violations best 10172 last 10172 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-2409011 | kv3_io_ft | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (72/72 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-1945948 | slice_station__t12 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (223/224 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i1-811516 | eco_20261123_051704_3678821-i1 | 5_2_route | 1.7 | last meaningful line 0.0 h ago (254/254 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i1-995418 | eco_20261123_063813_234645-i1 | 5_2_route | 1.5 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc10 | dpkit-coll_core-2130490 | coll_core | pregrt_ff_hold | 5.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | dpkit-kv3_pv_v3-928238 | kv3_pv_v3 | pregrt_ff_hold | 9.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 16.1 | drt_violations best 15220 last 15220 rows 13 | before-window best 21706, window best 15220 | PROGRESS: drt_violations improved 29.9 % in window |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_C__t1-1837420 | dsdv_slice_lepw_mu_C__t1 | 5_1_grt | 18.8 | last meaningful line 5.8 h ago (211/219 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-1469791 | kv3_hroot | 5_2_route | 14.4 | drt_violations best 1269 last 2288 rows 28 | before-window best 1269, window best 1269 | PROGRESS: drt_violations: falling inside the active iteration (2288 -> 2018) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 18.8 | drt_violations best 1743 last 5229 rows 18 | before-window best 22046, window best 1743 | PROGRESS: drt_violations improved 92.1 % in window |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-2116652 | slw_st_a_v1 | 5_2_route | 21.0 | drt_violations best 9239 last 9239 rows 14 | before-window best 12416, window best 9239 | PROGRESS: drt_violations improved 25.6 % in window |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 17.6 | drt_violations best 44158 last 44158 rows 13 | before-window best 51596, window best 44158 | PROGRESS: drt_violations improved 14.4 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 18.0 | drt_violations best 50150 last 50150 rows 13 | before-window best 56276, window best 50150 | PROGRESS: drt_violations improved 10.9 % in window |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv06a1adf6-2948886 | col_h9_r2__t1 | 5_2_route | 11.4 | drt_violations best 1396 last 1401 rows 25 | before-window best 172065, window best 1396 | PROGRESS: drt_violations improved 99.2 % in window |  |
| epyc7 | dpkit-slw_fe_v2__clf110fab2-1127301 | slw_fe_v2 | 5_2_route | 23.7 | drt_violations best 5 last 5 rows 49 | before-window best 259, window best 5 | PROGRESS: drt_violations improved 98.1 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 18.7 | drt_violations best 56454 last 56454 rows 13 | before-window best 65992, window best 56454 | PROGRESS: drt_violations improved 14.5 % in window |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 29.4 | drt_violations best 20 last 20 rows 54 | before-window best 38, window best 20 | PROGRESS: drt_violations improved 47.4 % in window |  |
| epyc8 | dpkit-col_h9_r0_p6__t1__pv0012ba28-1047525 | col_h9_r0_p6__t1 | 5_2_route | 32.8 | drt_violations best 6907 last 6907 rows 21 | before-window best 7732, window best 6907 | PROGRESS: drt_violations improved 10.7 % in window |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | pregrt_ff_hold | 9.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-kv3_hroot-2788764 | kv3_hroot | 5_2_route | 20.3 | drt_violations best 14710 last 31045 rows 19 | before-window best 14710, window best 31045 | PROGRESS: drt_violations: falling inside the active iteration (31045 -> 25831) |  |
| epyc8 | dpkit-kv3_pv_v6-2906713 | kv3_pv_v6 | 4_1_cts | 7.5 | last meaningful line 0.5 h ago (10034/10034 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 16.9 | drt_violations best 33 last 33 rows 30 | before-window best 183055, window best 33 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc9 | dpkit-kv3_pv_v4-678105 | kv3_pv_v4 | 4_1_cts | 6.8 | last meaningful line 0.6 h ago (11136/11136 lines) | PROGRESS: log still growing |  |
| epyc9 | dpkit-slw_fe_v1__cl95cd1d0c-4083439 | slw_fe_v1 | 5_1_grt | 16.0 | repair_TNS best 2083.03 last 2083.03 rows 5 | before-window best 3413.35, window best 2083.03 | PROGRESS: repair_TNS improved 39.0 % in window |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pv697f40c9-648802 | col_h9_r0_p1__t1 | 5_2_route | 32.5 | drt_violations best 28 last 28 rows 54 | before-window best 175829, window best 28 | PROGRESS: drt_violations improved 100.0 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 32.2 | drt_violations best 29547 last 29547 rows 12 | before-window best 37704, window best 29547 | PROGRESS: drt_violations improved 21.6 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 18.9 | drt_violations best 89667 last 89667 rows 8 | before-window best 132000, window best 89667 | PROGRESS: drt_violations improved 32.1 % in window |  |
| intel1 | prd-eco_20261121_175441_3776558-i2t-3207837 | eco_20261121_175441_3776558-i2t | 5_2_route | 16.2 | drt_violations best 280 last 445 rows 18 | before-window best 90237, window best 280 | PROGRESS: drt_violations improved 99.7 % in window |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3816505 | sle_fw_v2 | 5_2_route | 26.2 | drt_violations best 2178 last 4340 rows 19 | before-window best 5930, window best 2178 | PROGRESS: drt_violations improved 63.3 % in window |  |
