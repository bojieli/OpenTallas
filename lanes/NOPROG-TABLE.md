# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 02:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 3, 'NO-PROGRESS': 4, 'GRT-LABEL': 1, 'YOUNG': 38, 'NO-DATA': 6, 'PROGRESS': 14}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair_grt | 8.4 | repair_Violations best 0 last 0 rows 93 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -743.27 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc7 | dpkit-glue-2294683 | glue | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | before-window best 0, window best - | NO-PROGRESS: no new repair_TNS row in 2 h | REPORT-ONLY: lane-own kit (QC-ALLFIX decides; neve |
| epyc7 | dpkit-sle_sc_v3-2137984 | sle_sc_v3 | tt_setup_repair_grt | 3.4 | repair_Violations best 0 last 0 rows 1 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -372.75 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | tt_setup_repair_grt | 8.1 | repair_Violations best 4404 last 4404 rows 33 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -773.59 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 14.9 | last meaningful line 10.3 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 10.3 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 10.4 | last meaningful line 10.3 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 10.3 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 14.2 | last meaningful line 10.3 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 10.3 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | 5_1_grt | 8.0 | grt rounds 2 overflow 5:91995 -> 10:83281 | GRT-LABEL: DESIGN-FAIL: overflow 83281 at round 10 > 1000 |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | 4_1_cts | 1.5 | last meaningful line 0.0 h ago (10772/10772 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i2-336844 | eco_20261123_102841_2122262-i2 | 5_2_route | 1.1 | last meaningful line 0.0 h ago (18/18 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i2-3480472 | eco_20261123_103136_2028090-i2 | 5_2_route | 2.2 | last meaningful line 0.2 h ago (284/285 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q00__cl1b5a6458-3305635 | cbf_q00 | pregrt_ff_hold | 2.5 | repair_Violations best 933 last 933 rows 48 | YOUNG: evidence 1.8 h < 2.5 h |  |
| epyc7 | dpkit-native59-3518897 | native59 | pregrt_ff_hold | 2.3 | repair_TNS best 5344.07 last 5344.07 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-1550300 | sle_sc_v1 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.763 last 0.763 rows 27 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_sc_v3-1547847 | sle_sc_v3 | 3_3_place_gp | 0.6 | overflow best 0.4536 last 0.4536 rows 1 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-1592356 | sle_stm_v1 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | 5_1_grt | 3.0 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-1611503 | sle_stm_v3 | 3_2_place_iop | 0.6 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-2036429 | sle_stm_v3 | postcts_gate_TT | 3.4 | last meaningful line 0.1 h ago (626/626 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__cl5ea486db-1547678 | sle_su_l1 | 3_3_place_gp | 0.6 | overflow best 0.2069 last 0.2069 rows 41 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-slw_sc_v2-1549720 | slw_sc_v2 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.5651 last 0.5651 rows 33 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_1_grt | 3.1 | repair_Remaining best 187498 last 187498 rows 228 | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-1552958 | slw_stm_v2 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | 5_1_grt | 3.3 | last meaningful line 0.0 h ago (255/257 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i2t-1608228 | eco_20261123_171023_3055226-i2t | 5_3_fillcell | 3.8 | last meaningful line 0.0 h ago (21/21 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-coll_core-1578986 | coll_core | 5_1_grt | 4.7 | repair_Remaining best 273635 last 273635 rows 149 | YOUNG: stage 0.8 h < 1 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-1668089 | kv3_hg_v1p2 | pregrt_ff_hold | 0.8 | repair_Violations best 62 last 79 rows 102 | YOUNG: stage 0.8 h < 1 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-197119 | sle_ctl | 5_1_grt | 5.3 | last meaningful line 0.0 h ago (173/173 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-1287720 | slw_fe_v2 | postcts_gate_TT | 6.6 | last meaningful line 0.0 h ago (796/796 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-3737398 | slw_su_l1 | tt_setup_repair_grt | 7.3 | repair_Violations best 12 last 16 rows 55 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i3t-3968210 | eco_20261123_120225_75582-i3t | 5_2_route | 1.7 | last meaningful line 0.2 h ago (295/296 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i3-662867 | eco_20261123_163717_2005956-i3 | 5_2_route | 1.2 | last meaningful line 0.1 h ago (286/287 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_164145_1995767-i2t-1761120 | eco_20261123_164145_1995767-i2t | 5_2_route | 0.7 | last meaningful line 0.0 h ago (153/153 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v3-3937139 | kv3_pv_v3 | 3_3_place_gp | 0.5 | last meaningful line 0.1 h ago (80/80 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-4081870-29819 | 4081870 | - | 0.4 |  | NO-DATA: no log found |  |
| epyc9 | otc-419064-24835 | 419064 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-419170-9202 | 419170 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-419460-14758 | 419460 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | otc-419743-9695 | 419743 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261123_190031_3093983-i3t-46390 | eco_20261123_190031_3093983-i3t | 5_1_grt | 0.3 | last meaningful line 0.1 h ago (239/285 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i2t-2658135 | eco_20261123_224647_4153453-i2t | 5_2_route | 1.8 | last meaningful line 0.2 h ago (282/283 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261124_010152_2867084-i2t-283529 | eco_20261124_010152_2867084-i2t | 5_1_grt | 0.1 | last meaningful line 0.1 h ago (142/142 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-fin-1506838 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (617/617 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3079865 | slice_station__t40 | 6_report | 4.6 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | fwcap_ab_pfqn | fwcap_ab_pfqn | 3_4_place_resized | 0.9 | repair_Remaining best 115286 last 115286 rows 187 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | otc-1670752-16443 | 1670752 | - | 1.8 |  | NO-DATA: no log found |  |
| intel1 | otc-2194855-5583 | 2194855 | flow | 1.2 | last meaningful line 0.0 h ago (2646/2646 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | otc-2414738-28743 | 2414738 | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (3970/3970 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i1-1832688 | eco_20261123_191853_2879776-i1 | 5_2_route | 1.6 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 1.7 | last meaningful line 0.1 h ago (283/284 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | so_3656574_ff_30061 | so_3656574_ff_30061 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (1034/1034 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | so_3656574_tt_30061 | so_3656574_tt_30061 | generate_abstract | 0.4 | last meaningful line 0.3 h ago (1034/1034 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 29.6 | drt_violations best 784 last 784 rows 30 | before-window best 2939, window best 784 | PROGRESS: drt_violations improved 73.3 % in window |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 8.2 | last meaningful line 0.3 h ago (13932/13932 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-2841416 | cbn_q00 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 24.8 | drt_violations best 26552 last 26552 rows 10 | before-window best 131336, window best 26552 | PROGRESS: drt_violations improved 79.8 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 18.1 | drt_violations best 39072 last 39072 rows 10 | before-window best 129916, window best 39072 | PROGRESS: drt_violations improved 69.9 % in window |  |
| epyc7 | dpkit-sle_hc2__clcc5e3e61-1959134 | sle_hc2 | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_1_grt | 2.9 | grt_overflow best 0 last 27 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | pregrt_ff_hold | 3.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 32.2 | drt_violations best 48746 last 160916 rows 18 | before-window best 49778, window best 48746 | PROGRESS: drt_violations improved 2.1 % in window |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-1531184 | sle_ctl | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | otc-16187-7415 | 16187 | 4_1_cts | 0.3 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | otc-4170469-11881 | 4170469 | 4_1_cts | 0.3 | repair_Violations best 0 last 0 rows 41 | PROGRESS: repair_Violations reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 32.4 | drt_violations best 76746 last 76746 rows 14 | before-window best 80382, window best 76746 | PROGRESS: drt_violations improved 4.5 % in window |  |
| intel2 | dpkit-slice_station__t12-4018505 | slice_station__t12 | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
