# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-19 02:45 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'CANCEL-NOW': 1, 'NO-DATA': 1, 'YOUNG': 38, 'EXCLUDED': 120, 'KEEP': 1, 'PROGRESS': 3}. Hosts without report: ['epyc2'].

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-kv3_pv_v5-1633948 | kv3_pv_v5 | 2_1_floorplan | 0.3 |  | CANCEL-NOW: SUPERSEDED: kit plan sha is not a live adopted plan (kit_wave_stages) | REPORTED (cancel next pass) |
| epyc7 | ap-ageom-kw-seqhost--t1-grt-1912382 | seqhost--t1-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-col_h9_r0_p6__t1__pv87853a7e-1642827 | col_h9_r0_p6__t1 | 3_3_place_gp | 0.3 | overflow best 0.3381 last 0.3708 rows 11 | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1370086 | col_h9_r1__t1 | 3_5_place_dp | 0.4 | last meaningful line -0.0 h ago (41/41 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv11dcdcd2-1369454 | col_h9_r1__t1 | 3_4_place_resized | 0.4 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv2833ee2b-1600717 | col_h9_r2__t1 | 3_4_place_resized | 0.3 | repair_Remaining best 43380 last 43380 rows 9 | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pvf57acd2b-1356146 | col_h9_r2__t1 | 4_1_cts | 0.5 | repair_Violations best 38 last 38 rows 23 | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t18-1361963 | slice_station__t18 | 3_3_place_gp | 0.5 | overflow best 0.3872 last 0.3927 rows 12 | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slice_station__t6__cl0755c26e-1361993 | slice_station__t6 | 3_3_place_gp | 0.5 | overflow best 0.3044 last 0.3047 rows 20 | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-svc_hi_dsdv_svc_rs__t2-1407097 | svc_hi_dsdv_svc_rs__t2 | 2_1_floorplan | 6.4 | last meaningful line 0.0 h ago (719/719 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv7466df46-4051635 | col_h9_r1__t1 | stage_odb_cap | 0.4 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 104.7 | repair_TNS best 128761 last 128761 rows 5 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 104.7 | repair_TNS best 187663 last 187663 rows 10 | YOUNG: series started inside the last 6 h |  |
| intel1 | dpkit-serdes__t3-3718642 | serdes__t3 | 2_4_floorplan_pdn | 0.6 | last meaningful line 0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-3804269 | sle_ctl | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (32/32 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-3913234 | sle_ctl | 2_4_floorplan_pdn | 0.5 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-3920020 | sle_ctl | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (28/28 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cla4f6f12f-3872951 | sle_ctl | stage_odb_cap | 0.5 | last meaningful line 0.0 h ago (29/29 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-sle_st_a_v1__cl989804f6__cled3c1d7b-4043595 | sle_st_a_v1 | 3_3_place_gp | 0.4 | overflow best 0.5716 last 0.5716 rows 2 | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_st_a_v1__clb036e152-185825 | slw_st_a_v1 | 3_3_place_gp | 0.2 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_st_a_v2__clf4365a62-4185538 | slw_st_a_v2 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (186/186 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-4043804 | slw_st_b_v1 | stage_odb_cap | 0.4 | last meaningful line 0.0 h ago (25/25 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t6-2962916 | svc_hi_dsdv_svc_rs__t6 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (68/68 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t3-3948521 | svc_lo_dsdv_svc_rs__t3 | 1_2_yosys | 0.5 | last meaningful line 0.0 h ago (72/72 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-glue-1185052 | glue | stage_odb_cap | 2.0 | last meaningful line 0.0 h ago (336/336 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel2 | dpkit-glue-1185552 | glue | 3_5_place_dp | 2.0 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-glue-1649578 | glue | stage_odb_cap | 1.7 | last meaningful line 0.0 h ago (260/260 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel2 | dpkit-glue-2807342 | glue | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (64/64 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-glue-3337111 | glue | 2_1_floorplan | 0.5 | last meaningful line 0.1 h ago (84/84 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel2 | dpkit-glue-696646 | glue | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (494/494 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-kv3_pv_v6-726930 | kv3_pv_v6 | stage_odb_cap | 2.4 | last meaningful line 0.0 h ago (141/141 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t2-961961 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 2.2 | last meaningful line 0.0 h ago (71/71 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-sle_ctl__cl372cea1c-3983628 | sle_ctl | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (192/192 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v2__cl14c98df5__pv41c959f3-1032752 | sle_st_b_v2 | stage_odb_cap | 2.1 | last meaningful line 0.0 h ago (229/229 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-126377 | svc_hi_dsdv_svc_rs__t1 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (171/171 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t4-4085948 | svc_hi_dsdv_svc_rs__t4 | stage_odb_cap | 3.1 | last meaningful line 0.0 h ago (185/185 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel2 | dpkit-svc_lo_dsdv_svc_rs__t6-4125381 | svc_lo_dsdv_svc_rs__t6 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (180/180 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel2 | dpkit-tt_ctlm-2898270 | tt_ctlm | 3_3_place_gp | 0.8 | overflow best 0.2306 last 0.2955 rows 231 | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-tt_ctlm-3093236 | tt_ctlm | 3_3_place_gp | 0.6 | overflow best 0.2242 last 0.3841 rows 123 | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | prd-eco1-i1t-557513 | eco1-i1t | 5_2_route | 2.5 | last meaningful line 0.3 h ago (282/283 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-824442 | col_h9_r0_p1__t1 | stage_odb_cap | 4.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv87d52780-509217 | col_h9_r1__t1 | pregrt_ff_hold | 1.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8aaf8508-511084 | col_h9_r1__t1 | pregrt_ff_hold | 1.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv4754d912-537237 | col_h9_r2__t1 | 5_1_grt | 1.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pv6827937d-946511 | col_h9_r2__t1 | pregrt_ff_hold | 0.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-col_h9_r2__t1__clce45cab5__pve0486b40-2998491 | col_h9_r2__t1 | stage_odb_cap | 5.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-2585815 | dsdv_slice_lepe_mu_LP__t2 | stage_odb_cap | 9.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hg-1915102 | kv3_hg | stage_odb_cap | 9.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hg_v1-2418370 | kv3_hg_v1 | stage_odb_cap | 9.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hg_v1p2-1272161 | kv3_hg_v1p2 | stage_odb_cap | 10.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hg_v1p3-1277043 | kv3_hg_v1p3 | stage_odb_cap | 10.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hg_v1p4-1277844 | kv3_hg_v1p4 | stage_odb_cap | 10.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hg_v1p5-1654158 | kv3_hg_v1p5 | stage_odb_cap | 9.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hg_v1p6-1282096 | kv3_hg_v1p6 | stage_odb_cap | 10.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hg_v3-851478 | kv3_hg_v3 | stage_odb_cap | 10.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi-494964 | kv3_hgi | stage_odb_cap | 10.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v1__cl141fc26e-558101 | kv3_hgi_v1 | stage_odb_cap | 25.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v1__cl42bc8b12-557506 | kv3_hgi_v1 | stage_odb_cap | 25.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v2__cl2862d491-2474191 | kv3_hgi_v2 | stage_odb_cap | 15.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v3-1645316 | kv3_hgi_v3 | stage_odb_cap | 9.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v4-1358957 | kv3_hgi_v4 | stage_odb_cap | 10.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v5-1357233 | kv3_hgi_v5 | stage_odb_cap | 10.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v6-1351662 | kv3_hgi_v6 | stage_odb_cap | 10.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v7-1501843 | kv3_hgi_v7 | stage_odb_cap | 10.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v8-3892603 | kv3_hgi_v8 | stage_odb_cap | 11.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hub_Ei-352732 | kv3_hub_Ei | stage_odb_cap | 7.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl254f2e73-3798670 | kv3_pc | 5_1_grt | 39.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc__cl5a95b461-2957945 | kv3_pc | stage_odb_cap | 15.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc_v1__cl23f6a148-3798940 | kv3_pc_v1 | 5_1_grt | 39.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc_v1__cl7f648944-3798924 | kv3_pc_v1 | 5_1_grt | 39.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pv_v1-1408894 | kv3_pv_v1 | stage_odb_cap | 10.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pv_v12-432486 | kv3_pv_v12 | stage_odb_cap | 7.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pv_v2-2210830 | kv3_pv_v2 | stage_odb_cap | 9.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pv_v5n-361968 | kv3_pv_v5n | stage_odb_cap | 7.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pv_v6n-361768 | kv3_pv_v6n | stage_odb_cap | 7.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pv_v7-1001895 | kv3_pv_v7 | stage_odb_cap | 6.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pv_v8-2521551 | kv3_pv_v8 | stage_odb_cap | 9.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl38badc56-1367911 | sle_hc0 | stage_odb_cap | 10.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c-1372517 | sle_hc0 | stage_odb_cap | 10.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-sle_su_l1__cl5ea486db-3880635 | sle_su_l1 | stage_odb_cap | 4.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-sle_su_l1__clc6d66f5b-3883311 | sle_su_l1 | stage_odb_cap | 4.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-slice_station__t40__clc8fb2c8c-553037 | slice_station__t40 | 4_1_cts | 1.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-slice_station__t41-2579258 | slice_station__t41 | stage_odb_cap | 12.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-slice_station__t43-2589284 | slice_station__t43 | stage_odb_cap | 9.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-3885638 | slw_su_l1 | stage_odb_cap | 4.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-3883445 | slw_su_l1 | stage_odb_cap | 4.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q00__cl870de686-2998531 | cbf_q00 | stage_odb_cap | 8.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbf_q00_s2-3653077 | cbf_q00_s2 | stage_odb_cap | 0.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-cbn_q01__cldd6ea846-2160920 | cbn_q01 | stage_odb_cap | 7.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-3045625 | col_h10_r0_p4__t1 | stage_odb_cap | 1.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3051494 | col_h10_r1__t1 | stage_odb_cap | 1.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv6882e5ea-2285455 | col_h9_r0_p2__t1 | stage_odb_cap | 5.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pvd86cb19a-2286723 | col_h9_r0_p2__t1 | stage_odb_cap | 5.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pvcb7f0079-3448179 | col_h9_r0_p3__t1 | 3_1_place_gp_skip_io | 0.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r0_p4__t1__cl8ef405e8__pv91095415-2299233 | col_h9_r0_p4__t1 | stage_odb_cap | 5.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r0_p6__t1__pv7808008f-2312079 | col_h9_r0_p6__t1 | stage_odb_cap | 5.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r0_p6__t1__pv8d617470-2313167 | col_h9_r0_p6__t1 | stage_odb_cap | 5.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r0_p6__t1__pvbdbd69f2-2313718 | col_h9_r0_p6__t1 | stage_odb_cap | 5.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r0_p6__t1__pvea45abf3-2314520 | col_h9_r0_p6__t1 | 5_2_route | 5.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r2__t1__clb8d86cd5__pv982ec12c-763883 | col_h9_r2__t1 | tt_setup_repair_grt | 6.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv22267ca0-1274608 | col_h9_r2__t1 | tt_setup_repair_grt | 5.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv2f87774f-1277671 | col_h9_r2__t1 | tt_setup_repair_grt | 5.7 |  | KEEP: col_h9_r2__t1__clce45cab5__pv2f87774f	S81-COL-INHERIT	representative (COORD 11-1 |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv31e47bd5-773896 | col_h9_r2__t1 | tt_setup_repair_grt | 6.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv4937edd4-1281437 | col_h9_r2__t1 | tt_setup_repair_grt | 5.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv843b0fff-3454082 | col_h9_r2__t1 | 4_1_cts | 0.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv8b5a5980-1292551 | col_h9_r2__t1 | tt_setup_repair_grt | 5.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9cc104a8-778119 | col_h9_r2__t1 | 5_2_route | 6.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv9e92407b-780153 | col_h9_r2__t1 | tt_setup_repair_grt | 6.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvb3258867-3456177 | col_h9_r2__t1 | stage_odb_cap | 0.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvb6ec679e-1296691 | col_h9_r2__t1 | tt_setup_repair_grt | 5.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvb7e88dd2-3458204 | col_h9_r2__t1 | stage_odb_cap | 0.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvd2454d1a-783772 | col_h9_r2__t1 | tt_setup_repair_grt | 6.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvd60e699f-2678239 | col_h9_r2__t1 | stage_odb_cap | 1.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pve0bffaf8-1322503 | col_h9_r2__t1 | tt_setup_repair_grt | 5.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pve171243a-1323510 | col_h9_r2__t1 | tt_setup_repair_grt | 5.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-coll_ftc-2201815 | coll_ftc | 5_1_grt | 5.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t4-3460836 | dsdv_slice_c1x_C__t4 | sdc_lint | 0.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | stage_odb_cap | 26.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_pc_v3-2166515 | kv3_pc_v3 | stage_odb_cap | 25.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_fe_v1__cl8210183c-2488921 | sle_fe_v1 | stage_odb_cap | 4.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_hc0__cl05696ed1-1772825 | sle_hc0 | stage_odb_cap | 17.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_sc_v1__cl7479a5ec-250105 | sle_sc_v1 | stage_odb_cap | 22.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_sc_v3-2419118 | sle_sc_v3 | stage_odb_cap | 18.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_stm_v2__cl55be2264-1617954 | sle_stm_v2 | stage_odb_cap | 2.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-sle_stm_v2__cl7b3062fa-458489 | sle_stm_v2 | stage_odb_cap | 8.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slice_station__t24__cl66b71008-3365805 | slice_station__t24 | stage_odb_cap | 6.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slice_station__t50__cld84c9e24-988405 | slice_station__t50 | stage_odb_cap | 7.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-3439443 | slw_fe_v1 | 3_3_place_gp | 0.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_fw_v1__cl51d45468-3632168 | slw_fw_v1 | stage_odb_cap | 0.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_fw_v2__cl8537f156-3140413 | slw_fw_v2 | stage_odb_cap | 16.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-3438226 | slw_hc2 | 3_3_place_gp | 0.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_sc_v1__cl63e5a7a2-3806663 | slw_sc_v1 | stage_odb_cap | 22.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-250959 | slw_sc_v1 | stage_odb_cap | 22.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-3808936 | slw_sc_v1 | stage_odb_cap | 22.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-3653069 | slw_st_b_v2 | 3_3_place_gp | 0.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-460246 | slw_st_b_v2 | stage_odb_cap | 8.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3443409 | slw_stm_v1 | 3_3_place_gp | 0.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-cbf_q00__cl1b5a6458-4059423 | cbf_q00 | stage_odb_cap | 3.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-cbf_q11-1100281 | cbf_q11 | 4_1_cts | 2.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-cbn_q00__cld7bf7197-4063666 | cbn_q00 | stage_odb_cap | 3.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-cbn_q00__cld7bf7197-4065128 | cbn_q00 | stage_odb_cap | 3.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pvd11cc58b-4071240 | col_h10_r0_p4__t1 | stage_odb_cap | 3.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r0_p4__t1__pvd8c0565f-553983 | col_h10_r0_p4__t1 | 5_1_grt | 2.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-1677642 | col_h10_r1__t1 | stage_odb_cap | 1.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | stage_odb_cap | 1.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h9_r0_p1__t1__pva2e3974f-849596 | col_h9_r0_p1__t1 | stage_odb_cap | 2.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h9_r0_p5__t1__pvc93af856-772923 | col_h9_r0_p5__t1 | stage_odb_cap | 2.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h9_r0_p6__t1__pvb38a9d6c-1150224 | col_h9_r0_p6__t1 | 5_1_grt | 2.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4593e8e5-1683478 | col_h9_r1__t1 | stage_odb_cap | 1.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pvbb600efe-2508931 | col_h9_r1__t1 | tt_setup_repair | 1.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h9_r1__t1__cl49d7a23e__pvc22584f3-1685199 | col_h9_r1__t1 | stage_odb_cap | 1.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h9_r2__t1__clce45cab5__pvb3f647ea-1688285 | col_h9_r2__t1 | stage_odb_cap | 1.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-coll_ft__cl78c7b300-811265 | coll_ft | stage_odb_cap | 2.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-hd_lep0N-1818676 | hd_lep0N | stage_odb_cap | 1.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-hd_mesh-4160741 | hd_mesh | stage_odb_cap | 3.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_hub_Wo-506479 | kv3_hub_Wo | 3_3_place_gp | 2.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v1n-643469 | kv3_pv_v1n | stage_odb_cap | 2.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v2n-643135 | kv3_pv_v2n | 3_3_place_gp | 2.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | stage_odb_cap | 2.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t1-4170754 | ot_s81sl_kv_leaf__t1 | stage_odb_cap | 3.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-ot_s81sl_leaf__t42-1154129 | ot_s81sl_leaf__t42 | stage_odb_cap | 2.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pv_v3-302824 | kv3_pv_v3 | stage_odb_cap | 7.2 | last meaningful line 0.0 h ago (429/429 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-svc_lo_dsdv_svc_rs__t7-2581236 | svc_lo_dsdv_svc_rs__t7 | stage_odb_cap | 9.0 | last meaningful line 0.0 h ago (536/536 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_a_v2__clf4365a62-810674 | slw_st_a_v2 | 5_1_grt | 12.9 | last meaningful line 0.0 h ago (1510/1510 lines) | PROGRESS: log still growing |  |
