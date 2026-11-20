# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 14:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'GRT-LABEL': 10, 'NO-DATA': 4, 'YOUNG': 109, 'KEEP': 1, 'EXCLUDED': 3, 'PROGRESS': 29}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc7 | dpkit-hd_serdes-379194 | hd_serdes | 5_1_grt | 2.7 | grt rounds 3 overflow 5:11153 -> 10:33587 -> 15:27687 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | 5_1_grt | 19.3 | grt rounds 6 overflow 5:8256 -> 10:2829 -> 15:2649 -> 20:2194 -> 25:1976 -> 30:1864 | GRT-LABEL: DESIGN-FAIL: overflow 2829 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 5.3 | grt rounds 3 overflow 5:48999 -> 10:45315 -> 15:50678 | GRT-LABEL: DESIGN-FAIL: overflow 45315 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 5.3 | grt rounds 3 overflow 5:30456 -> 10:19532 -> 15:15084 | GRT-LABEL: DESIGN-FAIL: overflow 19532 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 15.8 | grt rounds 3 overflow 5:27316 -> 10:11628 -> 15:6429 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 5.3 | grt rounds 3 overflow 5:50814 -> 10:51002 -> 15:49341 | GRT-LABEL: DESIGN-FAIL: overflow 51002 at round 10 > 1000 |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 24.9 | grt rounds 3 overflow 5:48547 -> 10:43104 -> 15:40069 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 16.8 | grt rounds 3 overflow 5:43280 -> 10:41355 -> 15:38838 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 16.8 | grt rounds 3 overflow 5:58470 -> 10:41949 -> 15:37968 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 11.3 | grt rounds 4 overflow 5:13197 -> 10:11019 -> 15:9952 -> 20:10000 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | ap-ageom-kw-sle-fw-v1--clf58b4dfb-dump-216963 | sle-fw-v1--clf58b4dfb-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | ap-ageom-kw-sle-fw-v1--clf58b4dfb-grt-216963 | sle-fw-v1--clf58b4dfb-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (611/611 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q01__clab6e67f2-924790 | cbn_q01 | 3_1_place_gp_skip_io | 0.7 | overflow best 0.8817 last 0.8828 rows 12 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-861738 | cbn_q11 | 3_1_place_gp_skip_io | 0.7 | overflow best 0.5632 last 0.5632 rows 27 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-cbn_q11__cl5cc92dfe-3259666 | cbn_q11 | 2_1_floorplan | 0.3 | repair_Viol best 1128 last 1128 rows 1153 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-cbx_q10__cl89936551-1317776 | cbx_q10 | 3_3_place_gp | 0.6 | overflow best 0.4428 last 0.4715 rows 20 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-cbx_q10__cl94a12200-1261172 | cbx_q10 | 3_3_place_gp | 0.6 | overflow best 0.1184 last 0.1184 rows 41 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2409529 | col_h10_r0_p4__t1 | tt_setup_repair_grt | 4.5 | repair_Viol best 2511 last 2511 rows 56 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-1507206 | col_h10_r1__t1 | pregrt_ff_hold | 1.9 | repair_Violations best 1159 last 1193 rows 29 | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2420858 | col_h10_r1__t1 | 5_1_grt | 4.5 | last meaningful line 2.3 h ago (199/225 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-311443 | col_h10_r1__t1 | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-320050 | col_h10_r1__t1 | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (149/149 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-2406768 | col_h10_r2__t1 | 5_2_route | 4.5 | last meaningful line 0.2 h ago (257/258 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-145230 | col_h9_r0_p2__t1 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (843/843 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-1237361 | dsdv_slice_lepw_mus_LP__t2 | 5_1_grt | 2.0 | repair_Viol best 282 last 282 rows 42 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4-3841157 | kv3_pv_v4 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (456/456 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 2.8 | last meaningful line 0.0 h ago (336/336 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t15-918505 | ot_s81sl_leaf__t15 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | stage_odb_cap | 1.9 | last meaningful line 0.0 h ago (286/286 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-954928 | ot_s81sl_leaf__t36 | 4_1_cts | 0.7 | last meaningful line 0.0 h ago (3715/3715 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-725289 | ot_s81sl_leaf__t44 | 3_3_place_gp | 0.7 | overflow best 0.4673 last 0.4779 rows 25 | YOUNG: stage 0.5 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-861295 | ot_s81sl_leaf__t46 | 3_3_place_gp | 0.7 | overflow best 0.6106 last 0.6106 rows 1 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (191/191 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-722706 | ot_s81sl_leaf__t65 | 3_3_place_gp | 0.7 | overflow best 0.5961 last 0.6052 rows 14 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t68-2798472 | ot_s81sl_leaf__t68 | stage_odb_cap | 0.3 | last meaningful line 0.0 h ago (40/40 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-serdes__t15__cla2127225-2739353 | serdes__t15 | 1_2_yosys | 0.3 | last meaningful line 0.2 h ago (316/316 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-4038564 | sle_st_b_v1 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (152/152 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_st_b_v2__clfde1249e-2763157 | sle_st_b_v2 | 2_4_floorplan_pdn | 0.3 | last meaningful line -0.0 h ago (10/10 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-164358 | slw_fe_v1 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (160/160 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v2__cl8537f156-3671630 | slw_fw_v2 | 2_1_floorplan | 0.2 | last meaningful line 0.1 h ago (86/86 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4043558 | slw_sc_v1 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (192/192 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3486824 | slw_stm_v2 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (204/204 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | stage_odb_cap | 0.7 | last meaningful line 0.0 h ago (120/120 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-690848 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 3.1 | last meaningful line 0.0 h ago (561/561 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t5-40726 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 2.3 | last meaningful line 0.5 h ago (463/463 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | otc-3418299-1777 | 3418299 | gen_lint_yosys | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | otc-3434320-23245 | 3434320 | gen_lint_yosys | 0.2 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003408_3748325-i2r-1014755 | eco_20261120_003408_3748325-i2r | 5_2_route | 3.9 | last meaningful line 0.1 h ago (274/275 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748476-i2r-2879183 | eco_20261120_003409_3748476-i2r | 5_2_route | 3.5 | last meaningful line 0.1 h ago (280/281 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1-3133296 | eco_20261120_003409_3748726-i1 | 5_2_route | 2.5 | last meaningful line 0.2 h ago (264/264 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_134605_3273412-i1t-3754125 | eco_20261120_134605_3273412-i1t | 5_1_grt | 0.2 | last meaningful line 0.0 h ago (136/136 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1t-2162531 | eco_recover1120-i1t | 5_2_route | 10.5 | drt_violations best 1686 last 1686 rows 2 | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-kv3-pv-v1-grt-4045897 | kv3-pv-v1-grt | 3_5_place_dp | 0.2 | last meaningful line 0.2 h ago (142/142 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-bk_sel__t2-4106372 | bk_sel__t2 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9975 last 0.9975 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-cbf_q01_s2-3869485 | cbf_q01_s2 | 3_3_place_gp | 0.3 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q00__cldbcda913-1076792 | cbn_q00 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (1105/1105 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (1468/1468 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | 4_1_cts | 3.2 | last meaningful line 0.0 h ago (10554/10554 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pc_v3-1060726 | kv3_pc_v3 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (1045/1045 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2-3267427 | kv3_pv_v2 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (524/524 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2n-3268154 | kv3_pv_v2n | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (548/548 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v3-3038377 | kv3_pv_v3 | stage_odb_cap | 3.5 | last meaningful line 0.0 h ago (536/536 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v3n-3830624 | kv3_pv_v3n | stage_odb_cap | 3.1 | last meaningful line 0.0 h ago (396/396 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v4n-3427796 | kv3_pv_v4n | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (436/436 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5-3465794 | kv3_pv_v5 | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (376/376 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5n-3392006 | kv3_pv_v5n | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (368/368 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v7-3012201 | kv3_pv_v7 | stage_odb_cap | 3.5 | last meaningful line 0.0 h ago (364/364 lines) | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1802160 | kv3_pv_v8 | 3_5_place_dp | 1.9 | last meaningful line 0.2 h ago (44/44 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1803775 | kv3_pv_v8 | 3_5_place_dp | 1.9 | last meaningful line 0.1 h ago (44/44 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-725922 | kv3_pv_v8 | 4_1_cts | 4.6 | last meaningful line 0.5 h ago (15672/15672 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t31-3799196 | ot_s81sl_leaf__t31 | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (147/147 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | stage_odb_cap | 2.3 | last meaningful line 0.0 h ago (1240/1240 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t69-3998705 | ot_s81sl_leaf__t69 | pregrt_ff_hold | 0.2 | repair_Violations best 242 last 261 rows 11 | YOUNG: stage 0.2 h < 1 h |  |
| epyc7 | dpkit-serdes__t13-734348 | serdes__t13 | 5_1_grt | 4.6 | repair_TNS best 195828 last 195828 rows 45 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_fe_v1__cl8210183c-37263 | sle_fe_v1 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (85/85 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl38badc56-3750132 | sle_hc0 | postcts_gate_FF | 5.2 | last meaningful line 0.0 h ago (763/763 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508-3739575 | sle_hc1 | 5_2_route | 5.2 | drt_violations best 121622 last 121622 rows 1 | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | 5_1_grt | 4.5 | last meaningful line 0.0 h ago (139/139 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3469980 | sle_st_b_v1 | 3_3_place_gp | 0.6 | overflow best 0.2107 last 0.2107 rows 40 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-sle_st_b_v2__pv41c959f3-3745640 | sle_st_b_v2 | 5_1_grt | 5.2 | last meaningful line 0.0 h ago (1091/1097 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3472539 | slw_st_b_v1 | 3_4_place_resized | 0.6 | last meaningful line 0.0 h ago (451/451 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3418471 | slw_stm_v1 | stage_odb_cap | 0.6 | last meaningful line 0.0 h ago (96/96 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 4.6 |  | NO-DATA: no log found |  |
| epyc7 | klegacy-dsdv_bksel_c_rfda3p-2239264 | dsdv_bksel_c_rfda3p | 5_2_route | 3.8 | last meaningful line 0.0 h ago (244/245 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-count-p1_tc-3989767 | count-p1_tc | prd_count_p1_tc | 0.1 | last meaningful line 0.0 h ago (42/42 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | ap-ageom-kw-slw-fw-v2--cl8537f156-grt-2872839 | slw-fw-v2--cl8537f156-grt | - | 0.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-cbf_q00__cl1b5a6458-3533052 | cbf_q00 | 3_3_place_gp | 1.5 | overflow best 0.2429 last 0.2429 rows 34 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-cbf_q00__cl870de686-1852213 | cbf_q00 | stage_odb_cap | 2.2 | last meaningful line 0.0 h ago (384/384 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | stage_odb_cap | 5.5 | last meaningful line 0.0 h ago (2539/2539 lines) | YOUNG: evidence 5.5 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-2023527 | col_h10_r0_p4__t1 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (469/469 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | 5_2_route | 5.3 | drt_violations best 73630 last 73630 rows 1 | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-1878510 | col_h9_r0_p2__t1 | 5_1_grt | 2.2 | last meaningful line 1.3 h ago (207/216 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | postcts_gate_FF | 5.4 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | tt_setup_repair_grt | 5.4 | repair_Viol best 2090 last 2090 rows 43 | YOUNG: stage 0.3 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3191459 | col_h9_r2__t1 | 5_2_route | 5.9 | last meaningful line 0.5 h ago (267/268 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl87f3ff59-2161178 | col_h9_r2__t1 | 3_3_place_gp | 0.3 | overflow best 0.2147 last 0.2147 rows 24 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3341852 | col_h9_r2__t1 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (366/366 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3688123 | dsdv_slice_c1x_C__t5 | 3_4_place_resized | 5.8 | repair_Remaining best 78251 last 78251 rows 240 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_hub_Ei-2525627 | kv3_hub_Ei | 3_3_place_gp | 1.9 | overflow best 0.4181 last 0.4185 rows 7 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (2439/2439 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-513808 | kv3_pv_v12 | 2_1_floorplan | 1.0 | last meaningful line 0.7 h ago (144/144 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v1n-2947167 | kv3_pv_v1n | stage_odb_cap | 3.8 | last meaningful line 0.0 h ago (500/500 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (2606/2606 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (2394/2394 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 5.4 | last meaningful line 0.0 h ago (2468/2468 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t58-371134 | ot_s81sl_leaf__t58 | stage_odb_cap | 1.1 | last meaningful line 0.0 h ago (204/204 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 16.1 | last meaningful line 3.5 h ago (217/226 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | 5_2_route | 17.0 | last meaningful line 0.5 h ago (283/284 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3505370 | slice_station__t40 | 5_2_route | 5.3 | last meaningful line 0.5 h ago (269/270 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t52-381736 | slice_station__t52 | 3_5_place_dp | 1.1 | last meaningful line 0.0 h ago (33/33 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | 5_2_route | 17.3 | last meaningful line 0.3 h ago (268/269 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-2982583 | slw_fw_v1 | stage_odb_cap | 1.7 | last meaningful line 0.0 h ago (324/324 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | 5_2_route | 18.0 | last meaningful line 0.5 h ago (272/273 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | 5_2_route | 18.0 | drt_violations best 89452 last 89452 rows 1 | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | 5_2_route | 18.4 | last meaningful line 0.7 h ago (278/279 lines) | YOUNG: evidence 3.7 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | 5_1_grt | 2.1 | repair_TNS best 194.76 last 194.76 rows 6 | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t2-1130517 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 2.6 | last meaningful line 0.5 h ago (463/463 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t6-1380810 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 0.6 | last meaningful line 0.0 h ago (163/163 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-tt_ctlm-2876778 | tt_ctlm | 1_2_yosys | 0.1 | last meaningful line -0.0 h ago (295/295 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | eloquent_tesla | eloquent_tesla | lec | 0.0 | LEC last write -0.0 h ago | YOUNG: evidence 0.0 h < 6 h |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-498208 | slw_st_b_v2 | 5_2_route | 17.3 | drt_violations best 83854 last 83854 rows 1 | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel2 | prd-eco_20261120_103658_2442812-i1-1367643 | eco_20261120_103658_2442812-i1 | 5_2_route | 3.3 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 26.8 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 61.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | stage_odb_cap | 37.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | 5_1_grt | 37.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 11.2 | last meaningful line 0.1 h ago (1377/1377 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-4083127 | col_h10_r0_p1__t1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (4572/4572 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-382185 | col_h10_r2__t1 | 5_2_route | 26.8 | drt_violations best 20 last 20 rows 53 | before-window best 28, window best 20 | PROGRESS: drt_violations improved 28.6 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-384874 | col_h10_r2__t1 | 5_2_route | 26.8 | drt_violations best 20 last 20 rows 53 | before-window best 28, window best 20 | PROGRESS: drt_violations improved 28.6 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-4011286 | col_h10_r2__t1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (4679/4679 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-385072 | col_h10_r2__t1 | 5_2_route | 26.8 | drt_violations best 20 last 20 rows 53 | before-window best 28, window best 20 | PROGRESS: drt_violations improved 28.6 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl8b686b3e-2806632 | col_h10_r2__t1 | stage_odb_cap | 8.5 | last meaningful line 0.0 h ago (4837/4837 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4028772 | col_h9_r0_p2__t1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (4538/4538 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4028288 | col_h9_r1__t1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (4639/4639 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | stage_odb_cap | 8.5 | last meaningful line 0.0 h ago (4750/4750 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (4313/4313 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 8.5 | last meaningful line 0.0 h ago (4608/4608 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-642785 | col_h9_r0_p1__t1 | 5_2_route | 14.1 | drt_violations best 31 last 31 rows 12 | before-window best 150968, window best 31 | PROGRESS: drt_violations improved 100.0 % in window |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 23.1 | drt_violations best 10168 last 49296 rows 18 | before-window best 11104, window best 10168 | PROGRESS: drt_violations improved 8.4 % in window |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-768070 | slw_su_l1 | 5_2_route | 22.8 | drt_violations best 7619 last 17503 rows 19 | before-window best 8002, window best 7619 | PROGRESS: drt_violations improved 4.8 % in window |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 24.2 | last meaningful line 0.0 h ago (1441/1441 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 19.2 | last meaningful line 0.0 h ago (1163/1163 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | pregrt_ff_hold | 11.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | pregrt_ff_hold | 11.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 14.8 | last meaningful line 0.0 h ago (1215/1215 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl6740750e-482449 | sle_fw_v2 | stage_odb_cap | 17.3 | last meaningful line 0.0 h ago (1031/1031 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | stage_odb_cap | 17.9 | last meaningful line 0.0 h ago (1143/1143 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 17.3 | last meaningful line 0.0 h ago (1031/1031 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | stage_odb_cap | 17.3 | last meaningful line 0.0 h ago (1031/1031 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v3-489810 | slw_fw_v3 | stage_odb_cap | 17.3 | last meaningful line 0.0 h ago (1031/1031 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2435819 | slw_hc1 | stage_odb_cap | 18.4 | last meaningful line 0.0 h ago (1155/1155 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | stage_odb_cap | 17.5 | last meaningful line 0.0 h ago (1045/1045 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | stage_odb_cap | 17.3 | last meaningful line 0.0 h ago (1031/1031 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-495397 | slw_st_b_v2 | stage_odb_cap | 17.3 | last meaningful line 0.0 h ago (1031/1031 lines) | PROGRESS: log still growing |  |
