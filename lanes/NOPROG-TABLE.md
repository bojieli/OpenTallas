# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 21:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'CANCEL-NOW': 2, 'GRT-LABEL': 20, 'YOUNG': 47, 'NO-DATA': 37, 'EXCLUDED': 2, 'KEEP': 1, 'PROGRESS': 17}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-1155917 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | dump_placed | 0.5 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-590838 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | 5_1_grt | 0.7 |  | CANCEL-NOW: HBM is parked | CANCELLED |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 39.6 | grt rounds 4 overflow 5:54036 -> 10:38366 -> 15:34625 -> 20:37819 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 29.5 | grt rounds 3 overflow 5:77484 -> 10:71484 -> 15:58855 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 34.4 | grt rounds 3 overflow 5:61525 -> 10:63713 -> 15:69180 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 23.8 | grt rounds 3 overflow 5:51174 -> 10:48756 -> 15:39411 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 23.8 | grt rounds 3 overflow 5:49711 -> 10:49445 -> 15:39714 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 33.6 | grt rounds 3 overflow 5:45659 -> 10:49448 -> 15:43227 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 21.3 | grt rounds 4 overflow 5:110533 -> 10:75296 -> 15:54463 -> 20:62289 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 29.5 | grt rounds 4 overflow 5:95535 -> 10:71407 -> 15:50563 -> 20:56554 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 23.3 | grt rounds 4 overflow 5:97308 -> 10:70056 -> 15:50304 -> 20:58440 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 25.1 | grt rounds 4 overflow 5:44451 -> 10:38859 -> 15:36410 -> 20:37714 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 25.0 | grt rounds 6 overflow 5:41833 -> 10:36208 -> 15:31830 -> 20:31076 -> 25:35283 -> 30:32085 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | 5_1_grt | 7.2 | grt rounds 2 overflow 5:39369 -> 10:31446 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 24.7 | grt rounds 4 overflow 5:18628 -> 10:12430 -> 15:11108 -> 20:10187 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 37.5 | grt rounds 4 overflow 5:32844 -> 10:12056 -> 15:8164 -> 20:7612 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 48.3 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11846 -> 20:10171 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 48.5 | grt rounds 5 overflow 5:32681 -> 10:30734 -> 15:25360 -> 20:23105 -> 25:31808 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 31.0 | grt rounds 6 overflow 5:19221 -> 10:14920 -> 15:12366 -> 20:11039 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 42.4 | grt rounds 3 overflow 5:55974 -> 10:46138 -> 15:41146 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 42.4 | grt rounds 3 overflow 5:60515 -> 10:47029 -> 15:41606 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 42.6 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 3_4_place_resized | 12.7 | last meaningful line 2.8 h ago (519/519 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | tt_setup_repair_grt | 9.6 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv-767971 | kv3_pv | 3_5_place_dp | 1.8 | last meaningful line 0.1 h ago (52/52 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t14-2503693 | serdes__t14 | 2_4_floorplan_pdn | 0.3 | last meaningful line 0.0 h ago (92/92 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | 5_2_route | 14.3 | drt_violations best 95161 last 95161 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-1019838 | slw_sc_v1 | 5_2_route | 7.9 | last meaningful line 0.3 h ago (281/282 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-kv3-hgi-v2--cle0015330-dump-3018533 | kv3-hgi-v2--cle0015330-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-kv3-hgi-v2--cle0015330-grt-3018533 | kv3-hgi-v2--cle0015330-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-kv3-hgi-v3-dump-3576652 | kv3-hgi-v3-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-kv3-hgi-v3-grt-3576652 | kv3-hgi-v3-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-kv3-io-cor-dump-2777088 | kv3-io-cor-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-kv3-io-cor-grt-2777088 | kv3-io-cor-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-sle-fw-v1--clf58b4dfb-dump-3869548 | sle-fw-v1--clf58b4dfb-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-sle-fw-v1--clf58b4dfb-grt-3869548 | sle-fw-v1--clf58b4dfb-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-sle-fw-v2--cl69f5e854-dump-3604873 | sle-fw-v2--cl69f5e854-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-sle-fw-v2--cl69f5e854-grt-3604873 | sle-fw-v2--cl69f5e854-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-sle-hc1--cl22c1ff36--pve289215f-dump-3821286 | sle-hc1--cl22c1ff36--pve289215f-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-sle-hc1--cl22c1ff36--pve289215f-grt-3821286 | sle-hc1--cl22c1ff36--pve289215f-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-sle-stm-v1--clbe630b9c-dump-3136323 | sle-stm-v1--clbe630b9c-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-sle-stm-v1--clbe630b9c-grt-3136323 | sle-stm-v1--clbe630b9c-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-sle-stm-v2--cl55be2264-dump-2917558 | sle-stm-v2--cl55be2264-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-sle-stm-v2--cl55be2264-grt-2917558 | sle-stm-v2--cl55be2264-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-sle-stm-v2--cl7b3062fa-dump-3130731 | sle-stm-v2--cl7b3062fa-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-sle-stm-v2--cl7b3062fa-grt-3130731 | sle-stm-v2--cl7b3062fa-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-slw-fe-v1--cl95cd1d0c-dump-3476849 | slw-fe-v1--cl95cd1d0c-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-slw-fe-v1--cl95cd1d0c-grt-3476849 | slw-fe-v1--cl95cd1d0c-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-slw-fw-v1--clf51c11d8--cl592e3d37-dump-3834564 | slw-fw-v1--clf51c11d8--cl592e3d37-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-slw-fw-v1--clf51c11d8--cl592e3d37-grt-3834564 | slw-fw-v1--clf51c11d8--cl592e3d37-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-slw-st-a-v2--cl9f076a5c-grt-2297493 | slw-st-a-v2--cl9f076a5c-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-slw-st-b-v1--cle6023ec2-grt-3286037 | slw-st-b-v1--cle6023ec2-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-slw-st-b-v2--pva66d0f22--pvb80e2003-dump-3374506 | slw-st-b-v2--pva66d0f22--pvb80e2003-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-slw-st-b-v2--pva66d0f22--pvb80e2003-grt-3374506 | slw-st-b-v2--pva66d0f22--pvb80e2003-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-slw-stm-v2--cl1ca9c415-dump-3395825 | slw-stm-v2--cl1ca9c415-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-slw-stm-v2--cl1ca9c415-grt-3395825 | slw-stm-v2--cl1ca9c415-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-tt-ctlm-dump-2994560 | tt-ctlm-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-tt-ctlm-grt-2994560 | tt-ctlm-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbf_q11-3840796 | cbf_q11 | 5_1_grt | 7.9 | last meaningful line 4.8 h ago (25/25 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| epyc7 | dpkit-kv3_hg_v1p2-672395 | kv3_hg_v1p2 | 5_1_grt | 2.8 | last meaningful line 0.7 h ago (43/43 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | 5_1_grt | 7.8 | last meaningful line 2.2 h ago (217/1516 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2969215 | sle_hc0 | postcts_gate_FF | 8.5 | last meaningful line 0.0 h ago (774/774 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-3504337 | sle_hc1 | postcts_gate_TT | 8.2 | last meaningful line 0.0 h ago (849/849 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3695652 | slw_sc_v2 | postcts_gate_TT | 8.0 | last meaningful line 0.0 h ago (920/920 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3669665 | slw_st_b_v1 | 5_1_grt | 8.0 | last meaningful line 1.9 h ago (218/1302 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 8.9 | drt_violations best 59812 last 59812 rows 10 | YOUNG: evidence 5.5 h < 7.5 h |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 6.2 | last meaningful line 4.5 h ago (622/622 lines) | YOUNG: evidence 6.2 h < 7.5 h |  |
| epyc7 | otc-2109716-1750 | 2109716 | - | 2.1 |  | NO-DATA: no log found |  |
| epyc7 | otc-2320461-12373 | 2320461 | gen_lint_check | 0.0 | last meaningful line -0.0 h ago (236/236 lines) | YOUNG: evidence -0.0 h < 7.5 h |  |
| epyc7 | otc-2367330-7554 | 2367330 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | otc-2902337-8701 | 2902337 | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | otc-3265937-25672 | 3265937 | gen_lint_check | 0.0 | last meaningful line 0.0 h ago (96/96 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | phscan-2687317 | phscan | - | 0.0 |  | NO-DATA: no log found |  |
| epyc8 | dpkit-cbn_q00__cld7bf7197-3404310 | cbn_q00 | 5_1_grt | 7.0 | last meaningful line 1.5 h ago (25/25 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-1220988 | col_h9_r0_p2__t1 | pregrt_ff_hold | 0.8 | repair_TNS best 45191.2 last 45191.2 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pva4376595-1220915 | col_h9_r0_p2__t1 | pregrt_ff_hold | 0.8 | repair_TNS best 119483 last 119483 rows 1 | YOUNG: stage 0.5 h < 1 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_1_grt | 8.9 | last meaningful line 1.3 h ago (40/40 lines) | YOUNG: evidence 1.4 h < 6 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1722167 | col_h9_r1__t1 | pregrt_ff_hold | 0.3 | repair_TNS best 9520.14 last 9520.14 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-3144441 | kv3_hg_v1p2 | 5_1_grt | 2.8 | last meaningful line 0.8 h ago (43/43 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 8.4 | drt_violations best 1570 last 1570 rows 8 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 8.2 | drt_violations best 56293 last 56293 rows 6 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261122_024317_3271969-i1t-3547037 | eco_20261122_024317_3271969-i1t | 5_2_route | 2.4 | last meaningful line 0.2 h ago (291/292 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261122_041149_1964199-i1-1023260 | eco_20261122_041149_1964199-i1 | 5_2_route | 1.0 | last meaningful line 0.0 h ago (268/269 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v6-1440068 | kv3_pv_v6 | 3_3_place_gp | 1.7 | overflow best 0.6892 last 0.6892 rows 11 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v8-1614044 | kv3_pv_v8 | 3_5_place_dp | 1.6 | last meaningful line 0.2 h ago (53/53 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-3008659 | sle_st_b_v1 | 3_3_place_gp | 0.2 | overflow best 0.7488 last 0.7488 rows 12 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-3120937 | sle_st_b_v2 | 2_2_floorplan_macro | 0.1 | last meaningful line 0.0 h ago (13/13 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-3239813 | slw_hc3 | 2_4_floorplan_pdn | 0.1 | last meaningful line 0.0 h ago (9/9 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | otc-1732719-5782 | 1732719 | - | 1.5 |  | NO-DATA: no log found |  |
| epyc9 | otc-1758840-26581 | 1758840 | orfs_synth | 1.5 | last meaningful line 1.3 h ago (421/421 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc9 | otc-2096666-11448 | 2096666 | 3_2_place_iop | 1.2 | last meaningful line 1.0 h ago (34/34 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i2-745368 | eco_20261121_070035_1645318-i2 | 5_2_route | 2.1 | drt_violations best 14377 last 14377 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc9 | prd-eco_r3_residual-i1-799917 | eco_r3_residual-i1 | 5_2_route | 2.1 | drt_violations best 164 last 164 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-207847 | slw_hc3 | 3_3_place_gp | 0.2 | overflow best 0.7884 last 0.7884 rows 28 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-216407 | slw_st_b_v1 | 2_1_floorplan | 0.2 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i3t-3010955 | eco_20261120_192428_3309571-i3t | 5_2_route | 1.7 | drt_violations best 19107 last 19107 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1t-203702 | eco_20261121_161716_4143584-i1t | 5_2_route | 4.9 | drt_violations best 92 last 92 rows 13 | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_1_grt | 3.3 | repair_Viol best 886 last 886 rows 2 | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | so_386962_ff_96632 | so_386962_ff_96632 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | so_386962_tt_96632 | so_386962_tt_96632 | signoff | 0.1 |  | NO-DATA: empty log |  |
| intel1 | so_404452_ff_28012 | so_404452_ff_28012 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | so_404452_tt_28012 | so_404452_tt_28012 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4007898 | col_h9_r1__t1 | 5_1_grt | 6.0 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-2222604 | coll_ftm | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (151/163 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-2227944 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-2215245 | kv3_io_ft | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (70/70 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | otc-217268-25606 | 217268 | asbuilt.yosys | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 38.1 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel2 | otc-2574367-13183 | 2574367 | - | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 42.5 | last meaningful line 0.9 h ago (1550/1550 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-cbf_q00__cl1b5a6458-557330 | cbf_q00 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-cbf_q01_s2-557381 | cbf_q01_s2 | pregrt_ff_hold | 1.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 18.4 | drt_violations best 1 last 2 rows 54 | before-window best 1, window best 2 | PROGRESS: drt_violations: falling inside the active iteration (2 -> 1) |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | 5_1_grt | 8.9 | last meaningful line 0.1 h ago (1538/1554 lines) | PROGRESS: log still growing |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-3022331 | sle_ctl | pregrt_ff_hold | 2.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-187481 | slw_st_a_v2 | 5_1_grt | 1.9 | repair_TNS best 0 last 0 rows 18 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | otc-431765-18007 | 431765 | tt_setup_repair_grt | 1.6 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | otc-451257-8041 | 451257 | tt_setup_repair_grt | 1.6 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | otc-709044-23442 | 709044 | tt_setup_repair_grt | 1.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2289240 | col_h10_r1__t1 | pregrt_ff_hold | 1.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-hd_ctl-1585232 | hd_ctl | pregrt_ff_hold | 1.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | dpkit-hd_mesh-3170867 | hd_mesh | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | otc-1453349-16601 | 1453349 | tt_setup_repair_grt | 1.7 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | otc-1458714-4592 | 1458714 | tt_setup_repair_grt | 1.7 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 10.2 | drt_violations best 571 last 650 rows 30 | before-window best 2288, window best 571 | PROGRESS: drt_violations improved 75.0 % in window |  |
| intel1 | prd-eco_20261121_075836_1991905-i1t-1821063 | eco_20261121_075836_1991905-i1t | 5_2_route | 13.2 | drt_violations best 48 last 266 rows 18 | before-window best 8548, window best 48 | PROGRESS: drt_violations improved 99.4 % in window |  |
