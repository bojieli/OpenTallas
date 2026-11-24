# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-24 01:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 2, 'NO-PROGRESS': 3, 'GRT-LABEL': 1, 'YOUNG': 39, 'NO-DATA': 7, 'PROGRESS': 15}. Hosts without report: ['epyc11'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-cbn_q01__cldd6ea846-171180 | cbn_q01 | tt_setup_repair_grt | 7.6 | repair_Viol best 959 last 959 rows 22 | UNSIGNABLE: tt_setup_repair_grt.log latest setup WNS -743.27 ps (< -300, gate TT >= -42); jo | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| epyc9 | prd-eco-i3-707330 | eco-i3 | 5_2_route | 3.1 | drt_violations best 2 last 2 rows 1 | UNSIGNABLE: ECO-FLAT: TT setup -104.66 -> -132.71 ps (gate -42); FF hold -1.83 -> -1.83 ps ( | UNSIGNABLE (hub: ot-run --cancel --reason design o |
| intel1 | otc-1368171-23750 | 1368171 | census_4_cts_tt66ce.otrun | 14.1 | last meaningful line 9.5 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 9.5 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-1459998-19685 | 1459998 | census_4_cts_tt66ce.otrun | 9.7 | last meaningful line 9.5 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 9.5 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| intel1 | otc-2044430-3114 | 2044430 | census_4_cts_tt66ce.otrun | 13.4 | last meaningful line 9.5 h ago (5/5 lines) | NO-PROGRESS: no new non-iteration log line for 9.5 h | REPORT-ONLY: lane-own kit (head-r18 decides; never |
| epyc8 | dpkit-cbn_q01__cld9ff4c40-1611182 | cbn_q01 | 5_1_grt | 7.3 | grt rounds 2 overflow 5:87660 -> 10:82099 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-dsdv_slice_lepw_mu_LP__t2-714159 | dsdv_slice_lepw_mu_LP__t2 | 5_1_grt | 3.7 | last meaningful line 0.1 h ago (2814/2839 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_ctl__cla4f6f12f-4119316 | sle_ctl | 4_1_cts | 0.8 | last meaningful line 0.1 h ago (10723/10723 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc2 | prd-eco_20261123_103136_2028090-i2-3480472 | eco_20261123_103136_2028090-i2 | 5_2_route | 1.4 | last meaningful line 0.0 h ago (271/271 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-native59-3518897 | native59 | pregrt_ff_hold | 1.6 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 2.5 h |  |
| epyc7 | dpkit-sle_sc_v3-2137984 | sle_sc_v3 | 5_1_grt | 2.6 | last meaningful line 0.2 h ago (1944/1959 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-sle_stm_v3-2036429 | sle_stm_v3 | 5_1_grt | 2.7 | last meaningful line 0.4 h ago (916/949 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-2258416 | slw_hc1 | pregrt_ff_hold | 2.5 | repair_TNS best 29497.8 last 29497.8 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-slw_sc_v2-2556435 | slw_sc_v2 | 5_1_grt | 2.3 | last meaningful line 0.0 h ago (249/262 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | frosty_proskuriakova | frosty_proskuriakova | asbuilt.yosys | 0.0 | last meaningful line 0.0 h ago (104/104 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | hwest_mix_ff | hwest_mix_ff | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | hwest_mix_tt | hwest_mix_tt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | otc-1295204-5612 | 1295204 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-1298299-24894 | 1298299 | gen_lint_yosys | 0.0 | last meaningful line 0.0 h ago (2/2 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261123_171023_3055226-i2t-1608228 | eco_20261123_171023_3055226-i2t | 5_2_route | 3.0 | drt_violations best 2043 last 2043 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc8 | dpkit-cbf_q00_s2-1801202 | cbf_q00_s2 | 5_1_grt | 7.2 | last meaningful line 0.5 h ago (256/1264 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc8 | dpkit-coll_core-1578986 | coll_core | 5_1_grt | 4.0 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-1668089 | kv3_hg_v1p2 | port_bind | 0.0 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hgi_v4-2330527 | kv3_hgi_v4 | 5_1_grt | 1.6 | last meaningful line 0.2 h ago (292/1298 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-1531184 | sle_ctl | hold_gate | 2.0 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v2__clf110fab2-1287720 | slw_fe_v2 | 5_1_grt | 5.8 | last meaningful line 0.0 h ago (2019/2019 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc0__cl1bc59e1c-85806 | slw_hc0 | tt_setup_repair_grt | 6.3 | last meaningful line 0.0 h ago (622/622 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-3737398 | slw_su_l1 | tt_setup_repair_grt | 6.5 | repair_Violations best 12 last 16 rows 55 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_120225_75582-i3t-3968210 | eco_20261123_120225_75582-i3t | 5_2_route | 0.9 | last meaningful line 0.1 h ago (279/280 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261123_163717_2005956-i3-662867 | eco_20261123_163717_2005956-i3 | 5_1_grt | 0.5 | last meaningful line 0.4 h ago (237/2268 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc8 | so_1445330_ff_78612 | so_1445330_ff_78612 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (233/233 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | so_1445330_tt_78612 | so_1445330_tt_78612 | generate_abstract | 0.1 | last meaningful line 0.1 h ago (233/233 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | eco-abs-2836023 | eco-abs | generate_abstract | 0.8 | last meaningful line 0.4 h ago (1030/1030 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc9 | eco-abs-3043228 | eco-abs | generate_abstract | 0.6 | last meaningful line 0.2 h ago (1030/1030 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | otc-3385995-22518 | 3385995 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261123_224216_149959-i2t-1506838 | eco_20261123_224216_149959-i2t | 5_2_route | 2.3 | drt_violations best 1796 last 1796 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261123_224647_4153453-i2t-2658135 | eco_20261123_224647_4153453-i2t | 5_2_route | 1.0 | last meaningful line 0.0 h ago (261/261 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc9 | relec1122-ml-r6_22ee41ca | relec1122-ml-r6_22ee41ca | - | 1.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3079865 | slice_station__t40 | 5_2_route | 3.9 | drt_violations best 21249 last 21249 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | fwcap_ab_pfqn | fwcap_ab_pfqn | 2_1_floorplan | 0.1 | last meaningful line 0.1 h ago (85/85 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | otc-1670752-16443 | 1670752 | - | 1.0 |  | NO-DATA: no log found |  |
| intel1 | otc-2194855-5583 | 2194855 | flow | 0.4 | last meaningful line 0.0 h ago (2373/2373 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | otc-2414738-28743 | 2414738 | 3_3_place_gp | 0.2 | overflow best 0.6488 last 0.6488 rows 27 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | prd-eco_20261123_191853_2879776-i1-1832688 | eco_20261123_191853_2879776-i1 | 5_1_grt | 0.9 | last meaningful line 0.4 h ago (239/1436 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | so_2636788_ff_30692 | so_2636788_ff_30692 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel1 | so_2636788_tt_30692 | so_2636788_tt_30692 | signoff | 0.0 |  | NO-DATA: empty log |  |
| intel2 | dpkit-coll_ftm-3177651 | coll_ftm | 5_2_route | 1.7 | drt_violations best 10185 last 10185 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | dpkit-hd_turn_a-2261561 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-687411 | kv3_io_ft | 5_2_route | 1.0 | drt_violations best 5487 last 5487 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-slice_station__t12-730523 | slice_station__t12 | 5_2_route | 1.0 | drt_violations best 2964 last 2964 rows 1 | YOUNG: stage 0.6 h < 1 h |  |
| intel2 | eco-abs-1941114 | eco-abs | generate_abstract | 0.4 | last meaningful line 0.3 h ago (1028/1028 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | prd-eco_20261123_063813_234645-i2-847740 | eco_20261123_063813_234645-i2 | 5_2_route | 0.9 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i3t-2703581 | eco_20261121_154936_3396612-i3t | 5_2_route | 28.8 | drt_violations best 954 last 1010 rows 28 | before-window best 4252, window best 954 | PROGRESS: drt_violations improved 77.6 % in window |  |
| epyc2 | dpkit-kv3_hub_C-303843 | kv3_hub_C | 4_1_cts | 7.5 | last meaningful line 0.2 h ago (13711/13711 lines) | PROGRESS: log still growing |  |
| epyc2 | prd-eco_20261123_102841_2122262-i2-336844 | eco_20261123_102841_2122262-i2 | 5_1_grt | 0.4 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-cbf_q00__cl1b5a6458-3305635 | cbf_q00 | pregrt_ff_hold | 1.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-cbn_q00__cld7bf7197-2841416 | cbn_q00 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-3088062 | col_h9_r0_p3__t1 | 5_2_route | 24.1 | drt_violations best 28844 last 28844 rows 9 | before-window best 186589, window best 28844 | PROGRESS: drt_violations improved 84.5 % in window |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0a45e191-3287553 | col_h9_r1__t1 | 5_2_route | 17.4 | drt_violations best 40914 last 40914 rows 9 | before-window best 391102, window best 40914 | PROGRESS: drt_violations improved 89.5 % in window |  |
| epyc7 | dpkit-glue-2294683 | glue | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc2__clcc5e3e61-1959134 | sle_hc2 | pregrt_ff_hold | 2.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-2783494 | sle_sc_v1 | pregrt_ff_hold | 2.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_stm_v1__cl27746664-2676153 | sle_stm_v1 | pregrt_ff_hold | 2.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_stm_v2__cl1ca9c415-2246167 | slw_stm_v2 | pregrt_ff_hold | 2.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-1710439 | slw_su_l1 | 5_2_route | 31.4 | drt_violations best 48746 last 160916 rows 18 | before-window best 50945, window best 48746 | PROGRESS: drt_violations improved 4.3 % in window |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-197119 | sle_ctl | pregrt_ff_hold | 4.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_su_l1__clcc9d0155-3367220 | slw_su_l1 | 5_2_route | 31.6 | drt_violations best 76746 last 76746 rows 14 | before-window best 80382, window best 76746 | PROGRESS: drt_violations improved 4.5 % in window |  |
