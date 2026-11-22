# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 20:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'UNSIGNABLE': 1, 'CANCEL-NOW': 2, 'GRT-LABEL': 14, 'NO-DATA': 4, 'YOUNG': 78, 'KEEP': 1, 'EXCLUDED': 1, 'PROGRESS': 13}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 49.8 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 49 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| intel2 | hbmcore-hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_-3461878 | hfd_hgi_vm_calendar_f20_dd5b84a9fbfa_ | 5_2_route | 0.2 |  | CANCEL-NOW: HBM is parked | REPORTED (cancel next pass) |
| intel2 | hbmcore-ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_-2612029 | ot_hgi_coll_tkm_m_tp192__tile0_e77e9f31fd71_ | hold_gate | 0.7 |  | CANCEL-NOW: HBM is parked | CANCELLED |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 34.9 | grt rounds 4 overflow 5:62755 -> 10:62005 -> 15:49088 -> 20:49999 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 34.9 | grt rounds 5 overflow 5:56489 -> 10:43484 -> 15:40478 -> 20:43412 -> 25:50457 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 49.3 | grt rounds 5 overflow 5:9510 -> 10:5086 -> 15:3245 -> 20:2874 -> 25:3124 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 38.6 | grt rounds 4 overflow 5:54036 -> 10:38366 -> 15:34625 -> 20:37819 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 23.7 | grt rounds 4 overflow 5:18628 -> 10:12430 -> 15:11108 -> 20:10290 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 36.5 | grt rounds 4 overflow 5:32844 -> 10:12056 -> 15:8208 -> 20:7612 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 47.3 | grt rounds 6 overflow 5:18562 -> 10:18456 -> 15:11655 -> 20:10171 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 47.5 | grt rounds 5 overflow 5:32681 -> 10:30734 -> 15:25360 -> 20:23105 -> 25:31808 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 30.0 | grt rounds 6 overflow 5:19221 -> 10:14920 -> 15:12366 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 25.0 | grt rounds 4 overflow 5:35977 -> 10:30023 -> 15:24172 -> 20:20900 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 46.4 | grt rounds 4 overflow 5:67513 -> 10:54044 -> 15:50242 -> 20:55216 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 41.4 | grt rounds 3 overflow 5:59246 -> 10:46138 -> 15:41146 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 41.4 | grt rounds 3 overflow 5:60515 -> 10:47029 -> 15:41606 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 41.6 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | ap-ageom-kw-coll-core-grt-1230675 | coll-core-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc10 | ap-ageom-kw-sle-hc1--cl7d360508--pv77c16c8a-dump-1288001 | sle-hc1--cl7d360508--pv77c16c8a-dump | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | ap-ageom-kw-sle-hc1--cl7d360508--pv77c16c8a-grt-1288001 | sle-hc1--cl7d360508--pv77c16c8a-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (124/124 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | ap-ageom-kw-slw-fe-v2--cle312294d-grt-1273245 | slw-fe-v2--cle312294d-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (125/125 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | dpkit-kv3_hg_v1p4-4003232 | kv3_hg_v1p4 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (97/97 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t4-293755 | serdes__t4 | 5_2_route | 10.0 | drt_violations best 14023 last 14023 rows 3 | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc10 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-711880 | sle_st_b_v1 | 3_3_place_gp | 0.5 | overflow best 0.1923 last 0.1923 rows 41 | YOUNG: stage 0.3 h < 1 h |  |
| epyc10 | dpkit-sle_su_c-988292 | sle_su_c | 3_1_place_gp_skip_io | 0.3 | overflow best 0.187 last 0.187 rows 40 | YOUNG: stage 0.2 h < 1 h |  |
| epyc10 | dpkit-slw_hc1__cl68f9248e__cle683a076-145776 | slw_hc1 | 3_4_place_resized | 0.9 | repair_Remaining best 209641 last 209641 rows 176 | YOUNG: stage 0.0 h < 1 h |  |
| epyc10 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-708114 | slw_st_b_v2 | 3_4_place_resized | 0.5 | last meaningful line -0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | otc-1188835-20759 | 1188835 | cut_equiv | 0.1 | last meaningful line 0.0 h ago (271186/271186 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1-396779 | eco_20261121_154936_3396612-i1 | 5_2_route | 0.7 | last meaningful line 0.0 h ago (275/275 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_203102_3392434-i1t-646001 | eco_20261121_203102_3392434-i1t | 5_2_route | 7.7 | drt_violations best 10 last 10 rows 56 | YOUNG: evidence 5.3 h < 7.5 h |  |
| epyc10 | prd-fin-3026978 | fin | 6_report | 0.0 | last meaningful line 0.0 h ago (44/44 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-cbn-q00--cldbcda913-dump-1801551 | cbn-q00--cldbcda913-dump | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-cbn-q00--cldbcda913-grt-1801551 | cbn-q00--cldbcda913-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-col-h9-r2--t1--cl774acf45--pv11b6518d-grt-1753557 | col-h9-r2--t1--cl774acf45--pv11b6518d-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | ap-ageom-kw-slw-fe-v1--clfe325744--cl08d14f0d-grt-1698957 | slw-fe-v1--clfe325744--cl08d14f0d-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (125/125 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-cbf_q00__cl870de686-411021 | cbf_q00 | 3_4_place_resized | 0.9 | last meaningful line 0.1 h ago (21/21 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q00__cl622f65d2-1109962 | cbn_q00 | 3_3_place_gp | 0.6 | overflow best 0.238 last 0.238 rows 34 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-kv3_hg-481577 | kv3_hg | 3_5_place_dp | 0.9 | last meaningful line 0.0 h ago (43/43 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1-4188706 | kv3_hg_v1 | 3_4_place_resized | 1.1 | last meaningful line 0.0 h ago (407/407 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hg_v1p2-253468 | kv3_hg_v1p2 | 3_3_place_gp | 1.0 | overflow best 0.0999 last 0.0999 rows 43 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-kv3_hg_v1p5-328056 | kv3_hg_v1p5 | 3_3_place_gp | 1.0 | overflow best 0.1 last 0.1 rows 43 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 3_4_place_resized | 11.7 | last meaningful line 1.7 h ago (519/519 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | 5_1_grt | 8.6 | last meaningful line 0.5 h ago (226/1032 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv-767971 | kv3_pv | 3_1_place_gp_skip_io | 0.8 | overflow best 0.2335 last 0.2335 rows 34 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-serdes__t12-735850 | serdes__t12 | 3_4_place_resized | 0.8 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-425190 | sle_su_l1 | 5_2_route | 7.4 | drt_violations best 264 last 264 rows 4 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | 5_2_route | 13.3 | drt_violations best 95161 last 95161 rows 1 | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-1019838 | slw_sc_v1 | 5_2_route | 6.9 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-col-h9-r0-p2--t1--cl0045af7b--pva2793873-grt-1025052 | col-h9-r0-p2--t1--cl0045af7b--pva2793873-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | ap-ageom-kw-col-h9-r0-p2--t1--cl9f71e63d--pva4376595-grt-1015774 | col-h9-r0-p2--t1--cl9f71e63d--pva4376595-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc8 | dpkit-cbn_q00__cld7bf7197-3404310 | cbn_q00 | 5_1_grt | 6.0 | last meaningful line 0.5 h ago (25/25 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_1_grt | 7.9 | last meaningful line 0.3 h ago (40/40 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | dpkit-coll_ftc-964552 | coll_ftc | 4_1_cts | 0.1 | last meaningful line 0.0 h ago (2999/2999 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-kv3_hg_v1p2-3144441 | kv3_hg_v1p2 | tt_setup_repair | 1.8 | repair_Violations best 697 last 779 rows 133 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-serdes__t14-3301476 | serdes__t14 | tt_setup_repair_grt | 6.1 | last meaningful line 0.1 h ago (18/18 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-sle_ctl__cla4f6f12f-3022331 | sle_ctl | 4_1_cts | 1.9 | last meaningful line 0.0 h ago (8511/8511 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3985339 | sle_hc2 | generate_abstract | 12.7 | last meaningful line 0.0 h ago (160/160 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-850569 | slw_fe_v1 | generate_abstract | 15.0 | last meaningful line 0.3 h ago (720/720 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | 5_2_route | 7.4 | drt_violations best 49816 last 49816 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v2__cl9f076a5c-187481 | slw_st_a_v2 | 5_1_grt | 0.9 | repair_Remaining best 130200 last 130200 rows 6 | YOUNG: stage 0.4 h < 1 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 7.2 | drt_violations best 74856 last 74856 rows 3 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc8 | prd-eco_20261122_024317_3271969-i1t-3547037 | eco_20261122_024317_3271969-i1t | 5_2_route | 1.4 | last meaningful line 0.1 h ago (282/282 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc8 | prd-eco_20261122_041149_1964199-i1-1023260 | eco_20261122_041149_1964199-i1 | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-cbn-q11--cl5cc92dfe-dump-2393557 | cbn-q11--cl5cc92dfe-dump | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-cbn-q11--cl5cc92dfe-grt-2393557 | cbn-q11--cl5cc92dfe-grt | 3_5_place_dp | 0.0 | last meaningful line 0.0 h ago (144/144 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | ap-ageom-kw-slw-fe-v2--clf110fab2-grt-2295098 | slw-fe-v2--clf110fab2-grt | 3_5_place_dp | 0.1 | last meaningful line 0.1 h ago (125/125 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-cbf_q01-1450063 | cbf_q01 | 3_3_place_gp | 0.7 | overflow best 0.1978 last 0.1978 rows 34 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-col_h10_r1__t1__cld01bb4ae-2289240 | col_h10_r1__t1 | 4_1_cts | 0.1 | repair_Violations best 55 last 114 rows 23 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-hd_ctl-1585232 | hd_ctl | pregrt_ff_hold | 0.6 | repair_TNS best 429435 last 429435 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc9 | dpkit-kv3_pv_v6-1440068 | kv3_pv_v6 | 2_1_floorplan | 0.7 | last meaningful line 0.3 h ago (1180/1180 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc9 | dpkit-kv3_pv_v8-1614044 | kv3_pv_v8 | 3_1_place_gp_skip_io | 0.6 | overflow best 0.8396 last 0.8518 rows 17 | YOUNG: stage 0.1 h < 1 h |  |
| epyc9 | dpkit-sle_hc1__cl22c1ff36__pve230954c-990147 | sle_hc1 | 3_4_place_resized | 0.9 | last meaningful line 0.0 h ago (429/429 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | dpkit-sle_st_b_v1__pv0e7b1dcc-1810235 | sle_st_b_v1 | 3_3_place_gp | 0.4 | overflow best 0.4584 last 0.4584 rows 30 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1823667 | sle_st_b_v2 | 3_3_place_gp | 0.4 | overflow best 0.5652 last 0.5652 rows 28 | YOUNG: stage 0.2 h < 1 h |  |
| epyc9 | dpkit-slw_hc3__clccfc3e6b__pvcca9ff41-2192754 | slw_hc3 | 3_3_place_gp | 0.2 | overflow best 0.9511 last 0.9511 rows 16 | YOUNG: stage 0.0 h < 1 h |  |
| epyc9 | otc-1136852-24964 | 1136852 | parts_equiv | 0.9 | last meaningful line 0.0 h ago (793237/793237 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc9 | otc-1732719-5782 | 1732719 | - | 0.5 |  | NO-DATA: no log found |  |
| epyc9 | otc-1758840-26581 | 1758840 | orfs_synth | 0.5 | last meaningful line 0.3 h ago (421/421 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | otc-1843583-16057 | 1843583 | lec | 0.4 | LEC last write 0.0 h ago | YOUNG: evidence 0.4 h < 6 h |  |
| epyc9 | otc-2096666-11448 | 2096666 | 3_2_place_iop | 0.2 | last meaningful line 0.2 h ago (34/34 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 19.9 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 19.5 |  | NO-DATA: no log found |  |
| epyc9 | prd-eco_20261121_070035_1645318-i2-745368 | eco_20261121_070035_1645318-i2 | 5_2_route | 1.1 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc9 | prd-eco_r3_residual-i1-799917 | eco_r3_residual-i1 | 5_2_route | 1.1 | last meaningful line 0.1 h ago (257/258 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_io_cor_v1-3312033 | kv3_io_cor_v1 | 3_3_place_gp | 0.4 | overflow best 0.1784 last 0.2799 rows 40 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-kv3_io_ft-2751771 | kv3_io_ft | 5_2_route | 0.9 | last meaningful line 0.0 h ago (226/227 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-3460400 | sle_st_a_v1 | 3_4_place_resized | 0.2 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-3631586 | sle_st_b_v2 | 1_2_yosys | 0.0 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t12-3454375 | slice_station__t12 | 5_1_grt | 0.2 | repair_Remaining best 8223 last 8223 rows 6 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-slw_hc3__cld86a7ad4__pvfd488b8f-3125768 | slw_hc3 | 3_5_place_dp | 0.5 | last meaningful line 0.0 h ago (81/81 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-3224056 | slw_st_b_v1 | 3_3_place_gp | 0.4 | overflow best 0.6431 last 0.6431 rows 24 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i3t-3010955 | eco_20261120_192428_3309571-i3t | 5_2_route | 0.7 | last meaningful line 0.1 h ago (258/259 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i1-1189865 | eco_20261121_082001_3216437-i1 | 5_2_route | 2.7 | drt_violations best 43516 last 43516 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1t-203702 | eco_20261121_161716_4143584-i1t | 5_2_route | 3.9 | drt_violations best 3979 last 3979 rows 8 | YOUNG: evidence 3.6 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_1_grt | 2.3 | repair_Viol best 886 last 886 rows 2 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4007898 | col_h9_r1__t1 | 5_1_grt | 5.0 | last meaningful line 3.0 h ago (40/40 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel2 | dpkit-coll_ftm-3132815 | coll_ftm | 5_2_route | 2.0 | drt_violations best 9684 last 9684 rows 1 | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-hd_turn_a-3466801 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (218/219 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | otc-2920128-4921 | 2920128 | 3_5_place_dp | 0.6 | last meaningful line 0.0 h ago (83/83 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 37.1 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel2 | otc-3265713-26458 | 3265713 | - | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 41.5 | last meaningful line 1.8 h ago (1548/1548 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-cbf_q00__cl1b5a6458-557330 | cbf_q00 | pregrt_ff_hold | 0.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-cbf_q01_s2-557381 | cbf_q01_s2 | pregrt_ff_hold | 0.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 17.4 | drt_violations best 1 last 2 rows 54 | before-window best 3, window best 1 | PROGRESS: drt_violations improved 66.7 % in window |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | 5_1_grt | 7.9 | repair_TNS best 0 last 0 rows 14 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | otc-431765-18007 | 431765 | tt_setup_repair_grt | 0.6 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | otc-451257-8041 | 451257 | tt_setup_repair_grt | 0.6 | repair_Violations best 0 last 0 rows 2 | PROGRESS: repair_Violations reached 0 |  |
| epyc8 | otc-709044-23442 | 709044 | tt_setup_repair_grt | 0.4 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | dpkit-hd_mesh-3170867 | hd_mesh | pregrt_ff_hold | 3.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc9 | otc-1453349-16601 | 1453349 | tt_setup_repair_grt | 0.7 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | otc-1458714-4592 | 1458714 | tt_setup_repair_grt | 0.7 | repair_Violations best 0 last 0 rows 1 | PROGRESS: repair_Violations reached 0 |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 9.2 | drt_violations best 571 last 733 rows 29 | before-window best 7891, window best 571 | PROGRESS: drt_violations improved 92.8 % in window |  |
| intel1 | prd-eco_20261121_075836_1991905-i1t-1821063 | eco_20261121_075836_1991905-i1t | 5_2_route | 12.2 | drt_violations best 91 last 91 rows 14 | before-window best 16417, window best 91 | PROGRESS: drt_violations improved 99.4 % in window |  |
