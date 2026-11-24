# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-23 22:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 7, 'GRT-LABEL': 3, 'YOUNG': 51, 'NO-DATA': 7, 'PROGRESS': 14}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbf_q00__cl870de686-181856 | cbf_q00 | tt_setup_repair_grt | 4.1 | repair_Remaining best 279551 last 279551 rows 51 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -314.29 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (OPUS-FIX-QC-V4-R2 decid |
| epyc2 | dpkit-slw_su_l1__cla2a78701-3904373 | slw_su_l1 | 5_2_route | 26.9 | drt_violations best 39587 last 39587 rows 17 | before-window best 40073, window best 39587 | NO-PROGRESS: drt_violations best 39587 vs 40073 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc7 | dpkit-hd_lep0N-1324433 | hd_lep0N | 4_2_tapbal_grt | 3.4 | last meaningful line 1.8 h ago (48/56 lines) | UNSIGNABLE: 4_1_cts.json latest setup WNS -3109.07 ps (< -300, gate TT >= -42); job age 3.4  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-cbn_q01__clab6e67f2-1043557 | cbn_q01 | pregrt_ff_hold | 4.1 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (OPUS-FIX-QC-V4-R2 decid |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (OPUS-FIX-QC-V4-R2 decid |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 10.6 | last meaningful line 6.0 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 6.0 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 6.2 | last meaningful line 6.0 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 6.0 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 9.9 | last meaningful line 6.0 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 6.0 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc2 | dpkit-cbn_q11__cl49ae4555-3883814 | cbn_q11 | 5_1_grt | 4.6 | grt rounds 2 overflow 5:166101 -> 10:149070 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hg_v1p2-2726360 | kv3_hg_v1p2 | 5_1_grt | 18.8 | grt rounds 2 overflow 5:72617 -> 10:48604 | GRT-LABEL: DESIGN-FAIL: overflow 48604 at round 10 > 1000 |  |
| epyc9 | dpkit-kv3_pc_v3-2782883 | kv3_pc_v3 | 5_1_grt | 23.3 | grt rounds 2 overflow 5:13730 -> 10:13037 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-dsdv-slice-lepw-mu-LP--t2-grt-612794 | dsdv-slice-lepw-mu-LP--t2-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-coll_ft__cla4a25d77-442903 | coll_ft | 3_4_place_resized | 0.1 | repair_Remaining best 54331 last 54331 rows 34 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-slice_station__t30__cl6a190133-140494 | slice_station__t30 | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (534/564 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t7__cl362204c4-174378 | slice_station__t7 | tt_setup_repair_grt | 0.3 | last meaningful line 0.0 h ago (27/27 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-280835-32015 | 280835 | - | 0.3 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-cbf_q11-2451203 | cbf_q11 | pregrt_ff_hold | 2.0 | repair_Violations best 11912 last 11912 rows 21 | YOUNG: evidence 1.6 h < 2.5 h |  |
| epyc2 | dpkit-cbx_q10__cl89936551_h-2205260 | cbx_q10 | pregrt_ff_hold | 2.2 | repair_TNS best 128.103 last 128.103 rows 1 | YOUNG: evidence 1.5 h < 2.5 h |  |
| epyc2 | dpkit-cbx_q10__cl94a12200_h-2194343 | cbx_q10 | pregrt_ff_hold | 2.2 | repair_Violations best 96574 last 96574 rows 11 | YOUNG: evidence 1.6 h < 2.5 h |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 4.0 | last meaningful line 3.3 h ago (13035/13035 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_st_b_v1__cl6357f1cc__pvffd43fdc-604167 | slw_st_b_v1 | 3_3_place_gp | 0.4 | overflow best 0.619 last 0.619 rows 25 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | otc-1017374-18715 | 1017374 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | prd-eco_20261123_102841_2122262-i2t-3790618 | eco_20261123_102841_2122262-i2t | 5_2_route | 1.1 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i2t-2487500 | eco_20261123_103136_2028090-i2t | 5_2_route | 2.0 | last meaningful line 0.2 h ago (280/281 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-sle-st-b-v1--pv0e7b1dcc-dump-841303 | sle-st-b-v1--pv0e7b1dcc-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 13.9 | drt_violations best 55825 last 55825 rows 4 | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2158649 | hd_lep0N | 4_2_tapbal_grt | 2.4 | last meaningful line 1.3 h ago (48/51 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-2864139 | hd_lep0N | 4_2_tapbal_grt | 1.7 | last meaningful line 0.5 h ago (48/52 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N_w-3258726 | hd_lep0N_w | 5_2_route | 1.4 | drt_violations best 84406 last 84406 rows 1 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | otc-859915-1314 | 859915 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-869902-8685 | 869902 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (2/2 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_retry_1795467809896538497-i1t-60038 | eco_retry_1795467809896538497-i1t | 5_2_route | 9.1 | drt_violations best 16012 last 16012 rows 2 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc7 | so_634240_ff_76457 | so_634240_ff_76457 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | so_634240_tt_76457 | so_634240_tt_76457 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q11__cl5cc92dfe-1712022 | cbn_q11 | 5_1_grt | 3.8 | last meaningful line 0.1 h ago (143/143 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | dpkit-coll_core-1578986 | coll_core | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (7309/7309 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p5-206562 | kv3_hg_v1p5 | 4_1_cts | 1.1 | last meaningful line 0.0 h ago (7132/7132 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-1928525 | sle_ctl | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-197119 | sle_ctl | 4_1_cts | 1.1 | last meaningful line 0.2 h ago (10845/10845 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-1287720 | slw_fe_v2 | pregrt_ff_hold | 2.3 | repair_TNS best 20976.8 last 20976.8 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-3737398 | slw_su_l1 | tt_setup_repair_grt | 3.0 | repair_Violations best 12 last 16 rows 55 | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | prd-count-p1_tc-382519 | count-p1_tc | prd_count_p1_tc | 0.2 | last meaningful line 0.0 h ago (577/577 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i2-3929535 | eco_20261123_120225_75582-i2 | 5_2_route | 1.3 | last meaningful line 0.1 h ago (281/282 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i1-1021701 | eco_20261123_164145_1995767-i1 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | relec1122-ml-r6_afda1e9d | relec1122-ml-r6_afda1e9d | - | 6.1 |  | NO-DATA: no log found |  |
| epyc9 | dpkit-slw_st_b_v1__cle6023ec2-3998529 | slw_st_b_v1 | 3_3_place_gp | 0.4 | overflow best 0.2094 last 0.2094 rows 39 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slw_st_b_v2__pvc2ec5bfb-3942024 | slw_st_b_v2 | 3_3_place_gp | 0.5 | overflow best 0.3886 last 0.3886 rows 33 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | otc-157259-20671 | 157259 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc9 | otc-298560-17802 | 298560 | orfs_synth | 0.0 | last meaningful line 0.0 h ago (241/241 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-47938-12809 | 47938 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | prd-count-p1_bc-51485 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (228/228 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_190031_3093983-i2t-1439699 | eco_20261123_190031_3093983-i2t | 5_2_route | 2.9 | drt_violations best 537 last 537 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i1-914398 | eco_20261123_224647_4153453-i1 | 5_2_route | 3.4 | drt_violations best 57 last 57 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i1-3056982 | eco_20261124_010152_2867084-i1 | 5_2_route | 1.2 | last meaningful line 0.0 h ago (127/127 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_041946_4081528-i1-2378518 | eco_20261124_041946_4081528-i1 | 5_2_route | 1.9 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | prd-fin-456858 | fin | 6_report | 0.2 | last meaningful line 0.1 h ago (728/728 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-native59-2248842 | native59 | 3_3_place_gp | 0.9 | overflow best 0.2994 last 0.5764 rows 130 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-1670658 | sle_fe_v1 | 3_5_place_dp | 1.3 | last meaningful line 0.1 h ago (114/114 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t29__clc7772371-3101070 | slice_station__t29 | 5_1_grt | 0.3 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t30__clcedefe91-2946391 | slice_station__t30 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3079865 | slice_station__t40 | 4_1_cts | 0.4 | last meaningful line 0.0 h ago (2782/2782 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | otc-1882360-28079 | 1882360 | - | 5.7 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261123_191853_2879776-i1t-119447 | eco_20261123_191853_2879776-i1t | 5_2_route | 2.9 | last meaningful line 0.3 h ago (282/283 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2729897 | coll_ftm | 5_1_grt | 0.7 | repair_TNS best 17.396 last 17.396 rows 8 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-3504509 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-3092223 | kv3_io_ft | 5_1_grt | 0.5 | last meaningful line 0.0 h ago (424/448 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | dpkit-slice_station__t12-3132010 | slice_station__t12 | 5_2_route | 0.5 | last meaningful line 0.0 h ago (202/202 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | prd-eco_20261123_051704_3678821-i2-3270561 | eco_20261123_051704_3678821-i2 | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (173/173 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2t-2973514 | eco_20261123_063813_234645-i2t | 5_2_route | 6.0 | drt_violations best 2 last 61 rows 37 | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t24__cl64811a5d-226587 | slice_station__t24 | 5_1_grt | 0.3 | grt_overflow best 0 last 0 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 25.1 | drt_violations best 1939 last 1939 rows 22 | before-window best 11282, window best 1939 | PROGRESS: drt_violations improved 82.8 % in window |  |
| epyc2 | dpkit-ot_s81sl_leaf__t26-1923214 | ot_s81sl_leaf__t26 | 5_2_route | 28.0 | drt_violations best 1617 last 3457 rows 27 | before-window best 1743, window best 1617 | PROGRESS: drt_violations improved 7.2 % in window |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-3239262 | slw_su_l1 | 5_2_route | 27.3 | drt_violations best 46606 last 46606 rows 17 | before-window best 48840, window best 46606 | PROGRESS: drt_violations improved 4.6 % in window |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 20.6 | drt_violations best 49689 last 49689 rows 4 | before-window best 681573, window best 49689 | PROGRESS: drt_violations improved 92.7 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 27.9 | drt_violations best 49778 last 49778 rows 16 | before-window best 54432, window best 49778 | PROGRESS: drt_violations improved 8.6 % in window |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 55.2 | last meaningful line 4.3 h ago (646/646 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | pregrt_ff_hold | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbx_q10__cl89936551-1293593 | cbx_q10 | pregrt_ff_hold | 2.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3108476 | col_h9_r0_p3__t1 | 5_2_route | 38.6 | drt_violations best 17 last 19 rows 58 | before-window best 20, window best 17 | PROGRESS: drt_violations improved 15.0 % in window |  |
| epyc8 | dpkit-slw_hc0__cl1bc59e1c-85806 | slw_hc0 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2749854 | col_h9_r0_p3__t1 | 5_2_route | 26.2 | drt_violations best 15 last 15 rows 60 | before-window best 16, window best 15 | PROGRESS: drt_violations improved 6.2 % in window |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-927920 | col_h9_r0_p2__t1 | 5_2_route | 41.5 | drt_violations best 7378 last 37623 rows 18 | before-window best 24596, window best 7378 | PROGRESS: drt_violations improved 70.0 % in window |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 28.1 | drt_violations best 78971 last 78971 rows 13 | before-window best 88174, window best 78971 | PROGRESS: drt_violations improved 10.4 % in window |  |
