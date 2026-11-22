# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-21 18:15 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 2, 'UNSIGNABLE': 2, 'GRT-LABEL': 33, 'YOUNG': 76, 'NO-DATA': 12, 'KEEP': 1, 'EXCLUDED': 2, 'PROGRESS': 16}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc10 | dpkit-hd_lep0N-22377 | hd_lep0N | 4_2_tapbal_grt | 10.6 | last meaningful line 6.0 h ago (48/60 lines) | NO-PROGRESS: no new non-iteration log line for 6.0 h | REPORTED (cancel next pass) |
| epyc10 | dpkit-slw_su_c__cl92142dac-810405 | slw_su_c | 5_1_grt | 47.6 | grt rounds 6 overflow 5:5596 -> 10:1704 -> 15:1272 -> 20:954 -> 25:457 -> 30:171 | UNSIGNABLE: 5_1_grt.tmp.log latest setup WNS -504.07 ps (< -300, gate TT >= -42); job age 47 | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc7 | dpkit-cbn_q01__cldd6ea846-582858 | cbn_q01 | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | UNSIGNABLE: tt_setup_keep.log latest setup WNS -321.75 ps (< -300, gate TT >= -42); job age  | UNSIGNABLE (hub: NOTICE to the owning lane, cancel |
| epyc8 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef-4139523 | col_h9_r0_p4__t1 | 5_2_route | 21.4 | drt_violations best 27 last 27 rows 52 | before-window best 27, window best 27 | NO-PROGRESS: drt_violations best 27 vs 27 before window: < 2 % in 6 h | CANCELLED |
| epyc10 | dpkit-kv3_hgi_v8-3126306 | kv3_hgi_v8 | 5_1_grt | 14.1 | grt rounds 5 overflow 5:37484 -> 10:8165 -> 15:5582 -> 20:4765 -> 25:4799 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-ot_s81sl_leaf__t44__clf6cf8492-2117867 | ot_s81sl_leaf__t44 | 5_1_grt | 32.7 | grt rounds 4 overflow 5:95946 -> 10:60456 -> 15:49678 -> 20:49999 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-sle_ctl__cl67434795__padW5-2216252 | sle_ctl | 5_1_grt | 32.6 | grt rounds 5 overflow 5:56489 -> 10:43484 -> 15:40478 -> 20:43412 -> 25:50457 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-slw_su_c__cl19bb38ef-1614513 | slw_su_c | 5_1_grt | 47.1 | grt rounds 5 overflow 5:9510 -> 10:5086 -> 15:3245 -> 20:2874 -> 25:3124 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | 5_1_grt | 36.3 | grt rounds 4 overflow 5:54036 -> 10:38366 -> 15:34625 -> 20:37416 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cl18eece69-248840 | sle_st_a_v1 | 5_1_grt | 5.3 | grt rounds 2 overflow 5:3539 -> 10:2906 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-427216 | sle_st_a_v1 | 5_1_grt | 5.1 | grt rounds 2 overflow 5:4512 -> 10:1167 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-sle_st_a_v2__pv30dda31f__pv88773f93-254386 | sle_st_a_v2 | 5_1_grt | 5.2 | grt rounds 2 overflow 5:12031 -> 10:4878 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-slw_st_a_v1__clfc5867a6__pvf82a6c28-844610 | slw_st_a_v1 | 5_1_grt | 4.8 | grt rounds 2 overflow 5:3827 -> 10:2935 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-2272632 | hd_lep0N | 5_1_grt | 26.2 | grt rounds 3 overflow 5:77484 -> 10:72294 -> 15:58855 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 5_1_grt | 31.2 | grt rounds 3 overflow 5:61525 -> 10:66596 -> 15:69180 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1682797 | kv3_hgi_v8 | 5_1_grt | 20.6 | grt rounds 3 overflow 5:53769 -> 10:49359 -> 15:39411 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-kv3_hgi_v8-1683577 | kv3_hgi_v8 | 5_1_grt | 20.6 | grt rounds 3 overflow 5:50621 -> 10:49445 -> 15:39498 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | 5_1_grt | 30.3 | grt rounds 3 overflow 5:46939 -> 10:49559 -> 15:42999 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1646754 | ot_s81sl_leaf__t39 | 5_1_grt | 18.0 | grt rounds 4 overflow 5:79338 -> 10:74939 -> 15:54793 -> 20:62289 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2193109 | ot_s81sl_leaf__t39 | 5_1_grt | 26.3 | grt rounds 4 overflow 5:95535 -> 10:71407 -> 15:50597 -> 20:56554 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-2407691 | ot_s81sl_leaf__t39 | 5_1_grt | 20.1 | grt rounds 4 overflow 5:97308 -> 10:69973 -> 15:51390 -> 20:58440 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3961246 | ot_s81sl_leaf__t69 | 5_1_grt | 21.8 | grt rounds 4 overflow 5:44451 -> 10:38859 -> 15:36370 -> 20:37882 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-ot_s81sl_leaf__t73-3972552 | ot_s81sl_leaf__t73 | 5_1_grt | 21.8 | grt rounds 5 overflow 5:41833 -> 10:36208 -> 15:31830 -> 20:31076 -> 25:35283 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-sle_st_a_v2__pv4242de79-2391789 | sle_st_a_v2 | 5_1_grt | 5.5 | grt rounds 2 overflow 5:21672 -> 10:8153 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-kv3_hgi_v2__cl2862d491-3732038 | kv3_hgi_v2 | 5_1_grt | 10.7 | grt rounds 2 overflow 5:72991 -> 10:37675 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc8 | dpkit-ot_s81sl_leaf__t35-4157424 | ot_s81sl_leaf__t35 | 5_1_grt | 21.4 | grt rounds 4 overflow 5:18628 -> 10:12610 -> 15:11259 -> 20:10290 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-ot_s81sl_leaf__t28-1260879 | ot_s81sl_leaf__t28 | 5_1_grt | 34.3 | grt rounds 4 overflow 5:34386 -> 10:12131 -> 15:8208 -> 20:7612 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-156998 | sle_su_c | 5_1_grt | 45.0 | grt rounds 6 overflow 5:17310 -> 10:18043 -> 15:11889 -> 20:10171 -> 25:10927 -> 30:4543 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc9 | dpkit-sle_su_c-3965819 | sle_su_c | 5_1_grt | 45.3 | grt rounds 5 overflow 5:32681 -> 10:30734 -> 15:25360 -> 20:22699 -> 25:31808 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pva2e3974f-3223601 | col_h9_r0_p1__t1 | 5_1_grt | 22.3 | grt rounds 6 overflow 5:54170 -> 10:7759 -> 15:5073 -> 20:4181 -> 25:5669 -> 30:2596 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kv3_hgi_v1__cl42bc8b12-4108108 | kv3_hgi_v1 | 5_1_grt | 27.8 | grt rounds 6 overflow 5:40892 -> 10:22267 -> 15:11502 -> 20:10666 -> 25:8529 -> 30:5475 | GRT-LABEL: DESIGN-FAIL: overflow 22267 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl55642d17-2427808 | ot_s81sl_leaf__t25 | 5_1_grt | 22.8 | grt rounds 4 overflow 5:36357 -> 10:30023 -> 15:24172 -> 20:21320 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 44.1 | grt rounds 4 overflow 5:67513 -> 10:53405 -> 15:50242 -> 20:55216 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 5_1_grt | 39.4 | grt rounds 3 overflow 5:59246 -> 10:46138 -> 15:53864 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 5_1_grt | 39.4 | grt rounds 3 overflow 5:60515 -> 10:47029 -> 15:53055 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 39.6 | grt rounds 6 overflow 5:12147 -> 10:10883 -> 15:9842 -> 20:9748 -> 25:30868 -> 30:14987 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-slice_station__t24__cl66b71008-14958 | slice_station__t24 | 5_1_grt | 1.3 | grt rounds 5 overflow 5:4165 -> 10:3742 -> 15:3166 -> 20:3053 -> 25:3812 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc10 | dpkit-hd_lep0N-1588394 | hd_lep0N | 5_1_grt | 12.2 | last meaningful line 2.0 h ago (199/208 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc10 | dpkit-serdes__t4-293755 | serdes__t4 | 5_2_route | 7.8 | last meaningful line 0.2 h ago (293/294 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | dpkit-slice_station__t36-3668002 | slice_station__t36 | generate_abstract | 8.3 | last meaningful line 0.2 h ago (460/460 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc10 | otc-2578348-23800 | 2578348 | - | 0.2 |  | NO-DATA: no log found |  |
| epyc10 | prd-eco_20261121_154936_3396612-i1t-894339 | eco_20261121_154936_3396612-i1t | 5_2_route | 10.1 | drt_violations best 10370 last 10370 rows 3 | YOUNG: evidence 4.1 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_184648_4039100-i1-3762453 | eco_20261121_184648_4039100-i1 | 5_2_route | 3.1 | drt_violations best 243 last 243 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261121_203102_3392434-i1t-646001 | eco_20261121_203102_3392434-i1t | 5_2_route | 5.4 | drt_violations best 169411 last 169411 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc10 | prd-eco_20261122_012008_1324318-i1t-2203496 | eco_20261122_012008_1324318-i1t | 5_2_route | 0.6 | last meaningful line 0.0 h ago (128/128 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc10 | so_2784485_ff_99299 | so_2784485_ff_99299 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc10 | so_2784485_tt_99299 | so_2784485_tt_99299 | signoff | 0.0 |  | NO-DATA: empty log |  |
| epyc2 | dpkit-kv3_hub_C-2407914 | kv3_hub_C | 3_3_place_gp | 9.4 | overflow best 0.0992 last 0.0992 rows 45 | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc2 | dpkit-sle_hc1__cl22c1ff36__pve289215f-2374083 | sle_hc1 | 5_2_route | 15.5 | drt_violations best 122959 last 122959 rows 1 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-sle_su_l1__cl5ea486db-425190 | sle_su_l1 | 5_2_route | 5.1 | last meaningful line 0.0 h ago (258/259 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t36-3125329 | slice_station__t36 | 5_2_route | 11.8 | drt_violations best 3321 last 3321 rows 3 | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t51-342871 | slice_station__t51 | tt_setup_repair_grt | 5.2 | last meaningful line 0.0 h ago (22/22 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-2408517 | slw_fe_v1 | 5_2_route | 15.4 | drt_violations best 96105 last 96105 rows 1 | YOUNG: evidence 3.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-333657 | slw_fe_v1 | postcts_gate_FF | 11.0 | last meaningful line 0.0 h ago (1648/1648 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-1019838 | slw_sc_v1 | 5_1_grt | 4.7 | last meaningful line 0.5 h ago (890/991 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3868961 | slw_sc_v1 | postcts_gate_FF | 8.0 | last meaningful line -0.0 h ago (46369/46369 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | eco-abs-1996448 | eco-abs | generate_abstract | 0.2 | last meaningful line 0.1 h ago (748/748 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-count-p1_bc-1109108 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (553/553 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-count-p1_bc-415105 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (879/879 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_102155_957464-i1-3731479 | eco_20261121_102155_957464-i1 | 5_2_route | 2.4 | last meaningful line 0.1 h ago (271/272 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261121_105744_956410-i1-174847 | eco_20261121_105744_956410-i1 | 5_2_route | 1.8 | last meaningful line 0.2 h ago (271/272 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | prd-fin-4175816 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (1052/1052 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | so_2099912_ff_33401 | so_2099912_ff_33401 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc2 | so_2099912_tt_33401 | so_2099912_tt_33401 | signoff | 0.1 |  | NO-DATA: empty log |  |
| epyc7 | dpkit-cbf_q11-3840796 | cbf_q11 | 5_1_grt | 4.6 | last meaningful line 1.5 h ago (25/25 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl22c1ff36__pve230954c-1731757 | sle_hc1 | 5_2_route | 11.7 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v2-3695652 | slw_sc_v2 | 5_1_grt | 4.8 | repair_TNS best 2949.06 last 2949.06 rows 8 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-2113078 | slw_su_l1 | 5_2_route | 5.6 | drt_violations best 81322 last 81322 rows 3 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-svc_hi_dsdv_svc_rs__t4-3854132 | svc_hi_dsdv_svc_rs__t4 | 3_3_place_gp | 0.6 | overflow best 0.7187 last 0.7187 rows 16 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-svc_hi_dsdv_svc_rs__t4_att-3862620 | svc_hi_dsdv_svc_rs__t4_att | 3_3_place_gp | 0.6 | overflow best 0.7126 last 0.7126 rows 24 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | otc-1591883-15574 | 1591883 | tiled_diagnostic | 3.0 | last meaningful line 1.3 h ago (622/622 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_100942_929932-i2t-68122 | eco_20261121_100942_929932-i2t | 5_1_grt | 0.2 | last meaningful line 0.1 h ago (139/139 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_184012_3245689-i1-2542120 | eco_20261121_184012_3245689-i1 | 5_2_route | 2.1 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | prd-eco_20261121_193535_3253336-i1-3373883 | eco_20261121_193535_3253336-i1 | 5_2_route | 1.2 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-fin-295057 | fin | 6_report | 0.1 | last meaningful line 0.0 h ago (654/654 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | so_31186_ff_14099 | so_31186_ff_14099 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (685/685 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | so_31186_tt_14099 | so_31186_tt_14099 | generate_abstract | 0.3 | last meaningful line 0.2 h ago (685/685 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1035014 | col_h9_r1__t1 | 5_1_grt | 5.7 | last meaningful line 4.0 h ago (39/39 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| epyc8 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-1037027 | col_h9_r1__t1 | 5_1_grt | 5.7 | last meaningful line 3.5 h ago (39/39 lines) | YOUNG: evidence 3.6 h < 7.5 h |  |
| epyc8 | dpkit-dsdv_slice_lepe_mu_LP__t2-3534677 | dsdv_slice_lepe_mu_LP__t2 | pregrt_ff_hold | 6.7 | repair_Violations best 5218 last 5218 rows 15 | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc8 | dpkit-serdes__t14-3301476 | serdes__t14 | 5_1_grt | 3.9 | repair_TNS best 3556.35 last 3556.35 rows 3 | YOUNG: stage 0.8 h < 1 h |  |
| epyc8 | dpkit-serdes__t1__clfe1f0815-3274788 | serdes__t1 | 6_report | 14.6 | last meaningful line 0.1 h ago (259/259 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pv1c2f9baa-1023417 | sle_hc0 | 5_2_route | 12.6 | drt_violations best 12111 last 12111 rows 2 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b-3985339 | sle_hc2 | 5_2_route | 10.5 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__cl95cd1d0c-1899674 | slw_fe_v1 | 5_2_route | 12.0 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_fe_v1__clfe325744__cldb4efe33-850569 | slw_fe_v1 | 5_2_route | 12.7 | drt_violations best 95161 last 95161 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_hc1__cl68f9248e__cle683a076-2906124 | slw_hc1 | 5_2_route | 14.9 | drt_violations best 103675 last 103675 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc8 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-1894858 | slw_st_a_v1 | postcts_gate_TT | 5.1 | last meaningful line 0.0 h ago (99/99 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l0__cl1a1c1f8f-1964882 | slw_su_l0 | 5_2_route | 5.1 | last meaningful line 0.1 h ago (267/268 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc8 | dpkit-slw_su_l1__cla2a78701-2140137 | slw_su_l1 | 5_2_route | 4.9 | last meaningful line 0.0 h ago (250/250 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc8 | prd-eco_20261121_214321_3818039-i1-1999865 | eco_20261121_214321_3818039-i1 | 5_2_route | 1.0 | last meaningful line 0.2 h ago (245/246 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc9 | dpkit-hd_ctl-2344011 | hd_ctl | 5_1_grt | 2.3 | last meaningful line 0.0 h ago (1330/1366 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | dpkit-hd_mesh-3170867 | hd_mesh | pregrt_ff_hold | 1.3 | repair_TNS best 384532 last 384532 rows 1 | YOUNG: stage 0.8 h < 1 h |  |
| epyc9 | dpkit-sle_hc1__cl7d360508__pv77c16c8a-2616668 | sle_hc1 | 5_2_route | 12.3 | drt_violations best 8820 last 8820 rows 3 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc9 | otc-3085280-30126 | 3085280 | - | 17.7 |  | NO-DATA: no log found |  |
| epyc9 | otc-3117175-2609 | 3117175 | - | 17.6 |  | NO-DATA: no log found |  |
| epyc9 | otc-3780393-3122 | 3780393 | - | 17.3 |  | NO-DATA: no log found |  |
| epyc9 | otc-3787500-29118 | 3787500 | 3_4_place_resized | 0.5 | last meaningful line 0.1 h ago (404/404 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_070035_1645318-i2t-1219117 | eco_20261121_070035_1645318-i2t | 5_2_route | 3.7 | drt_violations best 2317 last 2317 rows 9 | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_143815_74711-i2r-2484763 | eco_20261121_143815_74711-i2r | 5_2_route | 2.2 | drt_violations best 1 last 1 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc9 | prd-eco_20261121_201548_1094504-i2t-3564572 | eco_20261121_201548_1094504-i2t | 5_2_route | 0.8 | last meaningful line 0.0 h ago (268/269 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc9 | so_4075738_ff_12406 | so_4075738_ff_12406 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (295/295 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc9 | so_4075738_tt_12406 | so_4075738_tt_12406 | generate_abstract | 0.0 | last meaningful line 0.0 h ago (295/295 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-hd_turn_a-1374368 | hd_turn_a | 5_2_route | 0.2 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-2204474 | slw_st_b_v1 | 5_2_route | 15.4 | drt_violations best 11962 last 11962 rows 2 | YOUNG: evidence 3.5 h < 7.5 h |  |
| intel1 | ot-canary-1551334 | ot-canary | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | otc-1134716-1202 | 1134716 | 3_3_place_gp | 0.5 | overflow best 0.2229 last 0.2361 rows 36 | YOUNG: stage 0.4 h < 1 h |  |
| intel1 | otc-1547079-32705 | 1547079 | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | otc-3999731-13707 | 3999731 | 3_5_place_dp | 2.2 | last meaningful line 0.3 h ago (29/29 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | prd-eco_20261120_192428_3309571-i2-437055 | eco_20261120_192428_3309571-i2 | 5_2_route | 1.4 | drt_violations best 534 last 534 rows 1 | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | prd-eco_20261121_082001_3216437-i1-1189865 | eco_20261121_082001_3216437-i1 | 5_1_grt | 0.5 | last meaningful line 0.2 h ago (270/1368 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | prd-eco_20261121_161716_4143584-i1t-203702 | eco_20261121_161716_4143584-i1t | 5_2_route | 1.7 | last meaningful line 0.2 h ago (279/280 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | prd-eco_20261121_175441_3776558-i1t-1508898 | eco_20261121_175441_3776558-i1t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4007898 | col_h9_r1__t1 | 5_1_grt | 3.0 | last meaningful line 1.0 h ago (40/40 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel2 | dpkit-kv3_io_ft-485420 | kv3_io_ft | 5_2_route | 1.0 | last meaningful line 0.0 h ago (230/231 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | otc-2434779-27076 | 2434779 | gate.ys | 2.1 | last meaningful line 2.0 h ago (51328/51328 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | otc-2600775-23472 | 2600775 | 3_3_place_gp | 0.4 | overflow best 0.8866 last 0.8866 rows 3 | YOUNG: stage 0.0 h < 1 h |  |
| intel2 | otc-2646376-19818 | 2646376 | gate.ys | 0.3 | last meaningful line 0.2 h ago (51328/51328 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | otc-2716032-12279 | 2716032 | 3_3_place_gp | 0.3 | overflow best 0.1856 last 0.1856 rows 38 | YOUNG: stage 0.3 h < 1 h |  |
| intel2 | otc-2772680-21361 | 2772680 | qx.otrun | 0.3 | last meaningful line 0.0 h ago (1958/1958 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel2 | otc-3017308-1493 | 3017308 | - | 0.1 |  | NO-DATA: no log found |  |
| intel2 | otc-3020512-25833 | 3020512 | 1_2_yosys | 0.1 | last meaningful line -0.0 h ago (6756/6756 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | otc-3043791-8735 | 3043791 | - | 0.1 |  | NO-DATA: no log found |  |
| intel2 | otc-3044139-2271 | 3044139 | TT | 0.1 | last meaningful line 0.0 h ago (17/17 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | prd-eco_20261121_115902_173230-i1-2657830 | eco_20261121_115902_173230-i1 | 5_2_route | 1.9 | last meaningful line 0.2 h ago (265/266 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc9 | prd-eco_20261120_150342_478824-i1t-3224490 | eco_20261120_150342_478824-i1t | 5_2_route | 34.9 |  | KEEP: col_h9_r2__t1__clc9ad8f7e__pv45d0c698	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | prd-count-p1_bc-1714380 | count-p1_bc | prd_count_p1_bc | 0.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | prd-fin-1617813 | fin | 6_report | 0.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc10 | dpkit-slw_su_l1__cla2a78701-2208350 | slw_su_l1 | 5_2_route | 22.6 | drt_violations best 10168 last 22918 rows 19 | before-window best 10389, window best 10168 | PROGRESS: drt_violations improved 2.1 % in window |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 39.2 | last meaningful line 0.4 h ago (1505/1505 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-2629912 | col_h9_r0_p2__t1 | 5_2_route | 15.3 | drt_violations best 26 last 26 rows 58 | before-window best 135164, window best 26 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc2 | dpkit-kv3_hub_Ei-1925428 | kv3_hub_Ei | pregrt_ff_hold | 6.4 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-native59-3868183 | native59 | pregrt_ff_hold | 8.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_su_l1__clcc9d0155-2366554 | slw_su_l1 | 5_2_route | 24.8 | drt_violations best 9327 last 39114 rows 18 | before-window best 9939, window best 9327 | PROGRESS: drt_violations improved 6.2 % in window |  |
| epyc2 | prd-eco_20261120_192837_2855950-i1-2944598 | eco_20261120_192837_2855950-i1 | 5_2_route | 15.1 | drt_violations best 1 last 12 rows 51 | before-window best 3, window best 1 | PROGRESS: drt_violations improved 66.7 % in window |  |
| epyc7 | dpkit-sle_ctl__cla4f6f12f-503408 | sle_ctl | pregrt_ff_hold | 3.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-3970617 | sle_fe_v1 | pregrt_ff_hold | 4.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304-2969215 | sle_hc0 | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_hc1__cl7d360508__pv97423966-3504337 | sle_hc1 | pregrt_ff_hold | 4.9 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3669665 | slw_st_b_v1 | pregrt_ff_hold | 4.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-cbn_q00__cld7bf7197-3404310 | cbn_q00 | pregrt_ff_hold | 3.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc8 | dpkit-sle_hc2__cl9c4c4509__clf60c5152__pvcf529cc9-1013642 | sle_hc2 | 5_2_route | 12.6 | drt_violations best 0 last 0 rows 7 | PROGRESS: drt_violations reached 0 |  |
| epyc9 | prd-eco_20261121_190011_1997288-i1t-3124286 | eco_20261121_190011_1997288-i1t | 5_2_route | 7.0 | drt_violations best 658 last 658 rows 23 | before-window best 194272, window best 658 | PROGRESS: drt_violations improved 99.7 % in window |  |
| intel1 | prd-eco_20261121_075836_1991905-i1t-1821063 | eco_20261121_075836_1991905-i1t | 5_2_route | 10.0 | drt_violations best 91 last 91 rows 14 | before-window best 190712, window best 91 | PROGRESS: drt_violations improved 100.0 % in window |  |
