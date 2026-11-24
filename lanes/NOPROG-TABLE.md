# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 02:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 3, 'NO-PROGRESS': 3, 'GRT-LABEL': 1, 'NO-DATA': 7, 'YOUNG': 40, 'PROGRESS': 17}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-714159 | dsdv_slice_lepw_mu_LP__t2 | postcts_gate_FF | 3.9 | last meaningful line 0.0 h ago (16/16 lines) | UNSIGNABLE: tt_setup_keep.log latest setup WNS -305.81 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair_grt | 7.9 | repair_Violations best 4629 last 8639 rows 23 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -743.27 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | tt_setup_repair_grt | 7.6 | last meaningful line 0.0 h ago (23/23 lines) | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -773.59 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 14.4 | last meaningful line 9.8 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 9.8 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 9.9 | last meaningful line 9.8 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 9.8 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 13.7 | last meaningful line 9.8 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 9.8 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | 5_1_grt | 7.5 | grt rounds 2 overflow 5:91995 -> 10:83281 | GRT-LABEL: DESIGN-FAIL: overflow 83281 at round 10 > 1000 |  |
| epyc10 | otc-1268478-25114 | 1268478 | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | 4_1_cts | 1.0 | last meaningful line 0.1 h ago (10750/10750 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_102841_2122262-i2-336844 | eco_20261123_102841_2122262-i2 | 5_1_grt | 0.6 | last meaningful line 0.2 h ago (237/1299 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i2-3480472 | eco_20261123_103136_2028090-i2 | 5_2_route | 1.7 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-native59-3518897 | native59 | pregrt_ff_hold | 1.8 | repair_TNS best 5344.07 last 5344.07 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-1550300 | sle_sc_v1 | 1_synth | 0.1 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | 5_1_grt | 2.4 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v3-1547847 | sle_sc_v3 | 1_synth | 0.1 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v3-2137984 | sle_sc_v3 | 5_1_grt | 2.9 | last meaningful line 0.4 h ago (1944/1973 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-1592356 | sle_stm_v1 | 1_2_yosys | 0.1 | last meaningful line -0.0 h ago (325/325 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-1611503 | sle_stm_v3 | 1_2_yosys | 0.1 | last meaningful line -0.0 h ago (469/469 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_su_l1__cl5ea486db-1547678 | sle_su_l1 | 1_synth | 0.1 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-1549720 | slw_sc_v2 | 1_synth | 0.1 | last meaningful line 0.0 h ago (26/26 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-1552958 | slw_stm_v2 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (602/602 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | eloquent_morse | eloquent_morse | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (104/104 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | exciting_almeida | exciting_almeida | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (104/104 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | hwest_mix2_tt | hwest_mix2_tt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc7 | prd-eco_20261123_171023_3055226-i2t-1608228 | eco_20261123_171023_3055226-i2t | 5_2_route | 3.3 | drt_violations best 2043 last 2043 rows 1 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | unruffled_merkle | unruffled_merkle | extract | 0.0 | last meaningful line 0.0 h ago (76/76 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-coll_core-1578986 | coll_core | 5_1_grt | 4.2 | last meaningful line 0.2 h ago (260/1265 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-1668089 | kv3_hg_v1p2 | tt_setup_repair | 0.3 | repair_Violations best 324 last 1708 rows 40 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-kv3_hgi_v4-2330527 | kv3_hgi_v4 | 5_1_grt | 1.9 | last meaningful line 0.5 h ago (292/1302 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-1531184 | sle_ctl | pregrt_ff_hold | 2.3 | repair_TNS best 234906 last 234906 rows 1 | YOUNG: stage 0.2 h < 1 h |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-1287720 | slw_fe_v2 | 5_1_grt | 6.1 | last meaningful line 0.0 h ago (2019/2053 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-3737398 | slw_su_l1 | tt_setup_repair_grt | 6.8 | repair_Violations best 12 last 16 rows 55 | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i3t-3968210 | eco_20261123_120225_75582-i3t | 5_2_route | 1.2 | last meaningful line 0.1 h ago (285/286 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i3-662867 | eco_20261123_163717_2005956-i3 | 5_2_route | 0.7 | last meaningful line 0.1 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | otc-3385995-22518 | 3385995 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261123_224216_149959-i2t-1506838 | eco_20261123_224216_149959-i2t | 5_2_route | 2.5 | drt_violations best 1796 last 1796 rows 1 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i2t-2658135 | eco_20261123_224647_4153453-i2t | 5_2_route | 1.3 | last meaningful line 0.1 h ago (272/273 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | relec1122-ml-r6_22ee41ca | relec1122-ml-r6_22ee41ca | - | 1.3 |  | NO-DATA: no log found |  |
| epyc9 | so_3705212_ff_71998 | so_3705212_ff_71998 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | so_3705212_tt_71998 | so_3705212_tt_71998 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (1034/1034 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | so_3761956_ff_99226 | so_3761956_ff_99226 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (1034/1034 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | so_3761956_tt_99226 | so_3761956_tt_99226 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (1034/1034 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3079865 | slice_station__t40 | 5_2_route | 4.1 | drt_violations best 21249 last 21249 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | fwcap_ab_pfqn | fwcap_ab_pfqn | 3_1_place_gp_skip_io | 0.4 | overflow best 0.6669 last 0.6669 rows 29 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | otc-1670752-16443 | 1670752 | - | 1.3 |  | NO-DATA: no log found |  |
| intel1 | otc-2194855-5583 | 2194855 | flow | 0.7 | last meaningful line 0.0 h ago (2508/2508 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | otc-2414738-28743 | 2414738 | 3_5_place_dp | 0.5 | last meaningful line 0.1 h ago (118/118 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i1-1832688 | eco_20261123_191853_2879776-i1 | 5_1_grt | 1.1 | last meaningful line 0.7 h ago (239/1455 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3177651 | coll_ftm | 5_2_route | 2.0 | drt_violations best 10185 last 10185 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-687411 | kv3_io_ft | 5_2_route | 1.2 | drt_violations best 5487 last 5487 rows 1 | YOUNG: stage 0.7 h < 1 h |  |
| intel2 | eco-abs-1941114 | eco-abs | generate_abstract | 0.6 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 1.2 | last meaningful line 0.1 h ago (276/276 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | so_3208889_ff_92848 | so_3208889_ff_92848 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | so_3208889_tt_92848 | so_3208889_tt_92848 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 29.1 | drt_violations best 912 last 912 rows 29 | before-window best 4252, window best 912 | PROGRESS: drt_violations improved 78.6 % in window |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 7.7 | last meaningful line 0.3 h ago (13711/13711 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-cbf_q00__cl1b5a6458-3305635 | cbf_q00 | pregrt_ff_hold | 2.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-2841416 | cbn_q00 | pregrt_ff_hold | 2.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 24.3 | drt_violations best 28844 last 28844 rows 9 | before-window best 186589, window best 28844 | PROGRESS: drt_violations improved 84.5 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 17.6 | drt_violations best 40914 last 40914 rows 9 | before-window best 391102, window best 40914 | PROGRESS: drt_violations improved 89.5 % in window |  |
| epyc7 | dpkit-glue-2294683 | glue | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc2__clcc5e3e61-1959134 | sle_hc2 | pregrt_ff_hold | 3.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_stm_v3-2036429 | sle_stm_v3 | tt_setup_repair_grt | 2.9 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_1_grt | 2.6 | grt_overflow best 0 last 23 rows 2 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | pregrt_ff_hold | 2.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 31.7 | drt_violations best 48746 last 160916 rows 18 | before-window best 50945, window best 48746 | PROGRESS: drt_violations improved 4.3 % in window |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-197119 | sle_ctl | pregrt_ff_hold | 4.8 | last meaningful line 0.0 h ago (92/92 lines) | PROGRESS: log still growing |  |
| epyc8 | prd-eco_20261123_164145_1995767-i2t-1761120 | eco_20261123_164145_1995767-i2t | 5_1_grt | 0.2 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 31.9 | drt_violations best 76746 last 76746 rows 14 | before-window best 80382, window best 76746 | PROGRESS: drt_violations improved 4.5 % in window |  |
