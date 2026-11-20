# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 13:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'GRT-LABEL': 9, 'NO-DATA': 7, 'YOUNG': 110, 'KEEP': 1, 'EXCLUDED': 3, 'PROGRESS': 34}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | 5_1_grt | 18.8 | grt rounds 6 overflow 5:8256 -> 10:2829 -> 15:2649 -> 20:2194 -> 25:1976 -> 30:1864 | GRT-LABEL: DESIGN-FAIL: overflow 2829 at round 10 > 1000 |  |
| intel1 | dpkit-kv3_hgi-3506865 | kv3_hgi | 5_1_grt | 4.8 | grt rounds 3 overflow 5:48999 -> 10:45315 -> 15:50678 | GRT-LABEL: DESIGN-FAIL: overflow 45315 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t17-3543298 | ot_s81sl_leaf__t17 | 5_1_grt | 4.8 | grt rounds 3 overflow 5:30456 -> 10:19532 -> 15:15084 | GRT-LABEL: DESIGN-FAIL: overflow 19532 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 15.3 | grt rounds 3 overflow 5:27316 -> 10:11628 -> 15:6429 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-3506660 | ot_s81sl_leaf__t53 | 5_1_grt | 4.8 | grt rounds 3 overflow 5:50814 -> 10:51002 -> 15:49341 | GRT-LABEL: DESIGN-FAIL: overflow 51002 at round 10 > 1000 |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 24.4 | grt rounds 3 overflow 5:48547 -> 10:43104 -> 15:40069 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 16.3 | grt rounds 3 overflow 5:43280 -> 10:41355 -> 15:38838 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 16.3 | grt rounds 3 overflow 5:58470 -> 10:41949 -> 15:37968 | GRT-LABEL: DESIGN-FAIL: overflow 41949 at round 10 > 1000 |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 10.8 | grt rounds 4 overflow 5:13197 -> 10:11019 -> 15:9952 -> 20:10000 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | ap-ageom-kw-sle-stm-v1--clbe630b9c-grt-1318074 | sle-stm-v1--clbe630b9c-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | ap-ageom-kw-slw-fw-v2--cl8f84514c-grt-1319908 | slw-fw-v2--cl8f84514c-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | cll_t60_base | cll_t60_base | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | cll_t60_slew | cll_t60_slew | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | dpkit-cbf_q11-330676 | cbf_q11 | stage_odb_cap | 1.7 | last meaningful line 0.0 h ago (342/342 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-cbn_q01__clab6e67f2-924790 | cbn_q01 | 2_1_floorplan | 0.2 | repair_Viol best 1128 last 1128 rows 359 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-cbn_q11__cl49ae4555-861738 | cbn_q11 | 2_1_floorplan | 0.2 | repair_Viol best 1128 last 1128 rows 501 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-cbx_q10__cl89936551-1317776 | cbx_q10 | 2_1_floorplan | 0.1 | repair_Viol best 847 last 847 rows 107 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-cbx_q10__cl94a12200-1261172 | cbx_q10 | 2_1_floorplan | 0.1 | repair_Viol best 847 last 847 rows 232 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-col_h10_r0_p4__t1__pvcc166a6d-2409529 | col_h10_r0_p4__t1 | 5_1_grt | 4.0 | last meaningful line 1.6 h ago (239/807 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv69c7e9a6-1507206 | col_h10_r1__t1 | pregrt_ff_hold | 1.4 | repair_TNS best 32133.1 last 32133.1 rows 1 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2420858 | col_h10_r1__t1 | 5_1_grt | 4.0 | last meaningful line 1.8 h ago (199/221 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv7a8a5452-2406768 | col_h10_r2__t1 | 5_2_route | 4.0 | last meaningful line 0.1 h ago (253/254 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-145230 | col_h9_r0_p2__t1 | stage_odb_cap | 1.7 | last meaningful line 0.0 h ago (553/553 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-1237361 | dsdv_slice_lepw_mus_LP__t2 | 5_1_grt | 1.5 | last meaningful line 0.7 h ago (226/1603 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | dpkit-iqf__t1-3398365 | iqf__t1 | 3_4_place_resized | 0.7 | last meaningful line -0.0 h ago (5/5 lines) | YOUNG: evidence -0.0 h < 7.5 h |  |
| epyc2 | dpkit-kv3_pv_v4-3841157 | kv3_pv_v4 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (336/336 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_kv_leaf__t2-1908982 | ot_s81sl_kv_leaf__t2 | 1_2_yosys | 2.3 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t15-918505 | ot_s81sl_leaf__t15 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.7028 last 0.7028 rows 22 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t32-1533256 | ot_s81sl_leaf__t32 | pregrt_ff_hold | 1.4 | repair_TNS best 12458.6 last 12458.6 rows 1 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t36-954928 | ot_s81sl_leaf__t36 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (56/56 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t44__clf4ea6d4b-725289 | ot_s81sl_leaf__t44 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.4919 last 0.4919 rows 31 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t46-861295 | ot_s81sl_leaf__t46 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.8973 last 0.9013 rows 7 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t55-56710 | ot_s81sl_leaf__t55 | 4_1_cts | 0.5 | last meaningful line 0.0 h ago (3455/3455 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t57-3394778 | ot_s81sl_leaf__t57 | 3_3_place_gp | 0.7 | overflow best 0.2773 last 0.2773 rows 38 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-ot_s81sl_leaf__t65-722706 | ot_s81sl_leaf__t65 | 3_1_place_gp_skip_io | 0.2 | overflow best 0.9059 last 0.9303 rows 14 | YOUNG: stage 0.1 h < 1 h |  |
| epyc2 | dpkit-sle_ctl__cl67434795__padW5-1501671 | sle_ctl | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (196/196 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_fw_v1__clf58b4dfb-3347897 | sle_fw_v1 | 3_5_place_dp | 1.9 | last meaningful line 0.0 h ago (69/69 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl115da35f-127322 | sle_sc_v1 | stage_odb_cap | 1.7 | last meaningful line 0.0 h ago (360/360 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | dpkit-sle_sc_v1__cl7479a5ec-2924472 | sle_sc_v1 | 3_4_place_resized | 0.9 | repair_Remaining best 98419 last 98419 rows 239 | YOUNG: stage 0.0 h < 1 h |  |
| epyc2 | dpkit-sle_st_b_v1__pv0e7b1dcc-4038564 | sle_st_b_v1 | 3_3_place_gp | 0.5 | overflow best 0.7588 last 0.7588 rows 7 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-sle_st_b_v2__cl14c98df5__pvcd986c42-1500025 | sle_st_b_v2 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (228/228 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-sle_stm_v2__cl7b3062fa-2891222 | sle_stm_v2 | stage_odb_cap | 0.9 | last meaningful line 0.0 h ago (140/140 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t29__clc7772371-3911511 | slice_station__t29 | 5_1_grt | 2.8 | repair_Viol best 23 last 23 rows 1 | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fe_v1__clfe325744__cl08d14f0d-164358 | slw_fe_v1 | 3_3_place_gp | 0.4 | overflow best 0.5108 last 0.5108 rows 5 | YOUNG: stage 0.2 h < 1 h |  |
| epyc2 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-4043558 | slw_sc_v1 | 3_3_place_gp | 0.5 | overflow best 0.2786 last 0.2786 rows 22 | YOUNG: stage 0.3 h < 1 h |  |
| epyc2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-1506133 | slw_st_b_v1 | stage_odb_cap | 1.4 | last meaningful line 0.0 h ago (224/224 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_stm_v2__cl9beb65e6-3486824 | slw_stm_v2 | 3_3_place_gp | 0.7 | overflow best 0.2103 last 0.2103 rows 35 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-slw_su_l1__cla2a78701-943691 | slw_su_l1 | 4_1_cts | 0.2 | last meaningful line 0.0 h ago (2416/2416 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-690848 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 2.6 | last meaningful line 0.1 h ago (487/487 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t5-40726 | svc_lo_dsdv_svc_rs__t5 | 1_2_yosys | 1.8 | last meaningful line 0.2 h ago (463/463 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | otc-3492910-9967 | 3492910 | gen_lint_yosys | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003408_3748325-i2r-1014755 | eco_20261120_003408_3748325-i2r | 5_2_route | 3.4 | last meaningful line 0.1 h ago (270/271 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748476-i2r-2879183 | eco_20261120_003409_3748476-i2r | 5_2_route | 3.0 | last meaningful line 0.2 h ago (274/275 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1-3133296 | eco_20261120_003409_3748726-i1 | 5_2_route | 2.0 | last meaningful line 0.1 h ago (134/134 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1t-2162531 | eco_recover1120-i1t | 5_2_route | 10.0 | drt_violations best 26911 last 26911 rows 1 | YOUNG: evidence 5.6 h < 7.5 h |  |
| epyc2 | so_1439079_ff_72722 | so_1439079_ff_72722 | stage_odb_cap | 0.0 | last meaningful line 0.0 h ago (554/554 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | so_1439079_tt_72722 | so_1439079_tt_72722 | stage_odb_cap | 0.0 | last meaningful line 0.0 h ago (554/554 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | ap-ageom-kw-sle-stm-v1--cl27746664-dump-3617506 | sle-stm-v1--cl27746664-dump | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | ap-ageom-kw-sle-stm-v1--cl27746664-grt-3617506 | sle-stm-v1--cl27746664-grt | - | 0.0 |  | NO-DATA: no log found |  |
| epyc7 | dpkit-cbn_q00__cldbcda913-1076792 | cbn_q00 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (805/805 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-1136289 | cbn_q01 | stage_odb_cap | 1.7 | last meaningful line 0.0 h ago (1212/1212 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-hd_lep0N-3749933 | hd_lep0N | stage_odb_cap | 2.7 | last meaningful line 0.0 h ago (246/246 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc7 | dpkit-hd_serdes-379194 | hd_serdes | 5_1_grt | 2.2 | last meaningful line 0.0 h ago (79/79 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pc_v3-1060726 | kv3_pc_v3 | stage_odb_cap | 1.8 | last meaningful line 0.0 h ago (775/775 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v1-3573937 | kv3_pv_v1 | 3_5_place_dp | 2.8 | last meaningful line 0.0 h ago (129/129 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2-3267427 | kv3_pv_v2 | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (404/404 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v2n-3268154 | kv3_pv_v2n | stage_odb_cap | 2.9 | last meaningful line 0.0 h ago (428/428 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v3-3038377 | kv3_pv_v3 | 3_4_place_resized | 3.0 | repair_Remaining best 161384 last 161384 rows 523 | YOUNG: stage 0.1 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v3n-3830624 | kv3_pv_v3n | stage_odb_cap | 2.6 | last meaningful line 0.0 h ago (276/276 lines) | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v4n-3427796 | kv3_pv_v4n | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (316/316 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5-3465794 | kv3_pv_v5 | stage_odb_cap | 2.8 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v5n-3392006 | kv3_pv_v5n | 3_3_place_gp | 2.9 | overflow best 0.1657 last 0.1657 rows 36 | YOUNG: stage 0.6 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v7-3012201 | kv3_pv_v7 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (244/244 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc7 | dpkit-kv3_pv_v8-1802160 | kv3_pv_v8 | 3_3_place_gp | 1.4 | overflow best 0.0997 last 0.0997 rows 42 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v8-1803775 | kv3_pv_v8 | 3_3_place_gp | 1.4 | overflow best 0.1128 last 0.1128 rows 40 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-kv3_pv_v8-725922 | kv3_pv_v8 | 4_1_cts | 4.1 | last meaningful line 0.0 h ago (15672/15672 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-ot_s81sl_leaf__t39-1017632 | ot_s81sl_leaf__t39 | tt_setup_repair | 1.8 | repair_Violations best 39 last 106 rows 105 | YOUNG: stage 0.3 h < 1 h |  |
| epyc7 | dpkit-serdes__t13-734348 | serdes__t13 | 5_1_grt | 4.1 | repair_TNS best 203213 last 203213 rows 37 | YOUNG: evidence 2.6 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc0__cl929603c0__cl38badc56-3750132 | sle_hc0 | postcts_gate_TT | 4.7 | last meaningful line 0.1 h ago (772/772 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-sle_hc1__cl7d360508-3739575 | sle_hc1 | 5_2_route | 4.7 | last meaningful line 0.1 h ago (281/282 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl115da35f-944972 | sle_sc_v1 | stage_odb_cap | 4.0 | last meaningful line 0.0 h ago (1519/1519 lines) | YOUNG: evidence 4.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-3469980 | sle_st_b_v1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (397/397 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_a_v1__clfc5867a6__pvdf8e5ca4-3544902 | slw_st_a_v1 | 2_1_floorplan | 0.0 | repair_Viol best 2328 last 2328 rows 317 | YOUNG: stage 0.0 h < 1 h |  |
| epyc7 | dpkit-slw_st_b_v1__cle6023ec2-3472539 | slw_st_b_v1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (405/405 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-3418471 | slw_stm_v1 | 2_1_floorplan | 0.1 | last meaningful line 0.0 h ago (604/604 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | ffss0600-lec-R1 | ffss0600-lec-R1 | - | 4.1 |  | NO-DATA: no log found |  |
| intel1 | dpkit-cbf_q00__cl1b5a6458-3533052 | cbf_q00 | stage_odb_cap | 1.0 | last meaningful line 0.0 h ago (96/96 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-cbf_q00__cl870de686-1852213 | cbf_q00 | 3_3_place_gp | 1.7 | overflow best 0.3672 last 0.3672 rows 29 | YOUNG: stage 0.5 h < 1 h |  |
| intel1 | dpkit-cbx_q10__cl89936551-1999472 | cbx_q10 | postcts_gate_TT | 4.9 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl94a12200_h-1912437 | cbx_q10 | stage_odb_cap | 5.0 | last meaningful line 0.0 h ago (2241/2241 lines) | YOUNG: evidence 5.0 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-2023527 | col_h10_r0_p4__t1 | 5_1_grt | 4.9 | repair_Viol best 503 last 503 rows 9 | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-3465820 | col_h10_r2__t1 | 5_2_route | 4.8 | last meaningful line 0.2 h ago (269/270 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv622a6f97-1878510 | col_h9_r0_p2__t1 | 5_1_grt | 1.7 | last meaningful line 0.8 h ago (207/213 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2092707 | col_h9_r0_p3__t1 | tt_setup_repair_grt | 4.9 | last meaningful line 0.0 h ago (20/20 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3-1919805 | col_h9_r1__t1 | 5_1_grt | 4.9 | last meaningful line 1.0 h ago (235/735 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__cl774acf45__pv11b6518d-3191459 | col_h9_r2__t1 | 5_2_route | 5.4 | last meaningful line 0.2 h ago (265/266 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-3341852 | col_h9_r2__t1 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (336/336 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_c1x_C__t5-3688123 | dsdv_slice_c1x_C__t5 | stage_odb_cap | 5.3 | last meaningful line 0.0 h ago (296/296 lines) | YOUNG: evidence 5.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Ei-2525627 | kv3_hub_Ei | 2_4_floorplan_pdn | 1.4 | last meaningful line 0.0 h ago (23/23 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_io_cor_v1-3394684 | kv3_io_cor_v1 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (2139/2139 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-513808 | kv3_pv_v12 | 2_1_floorplan | 0.5 | last meaningful line 0.3 h ago (144/144 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v1n-2947167 | kv3_pv_v1n | stage_odb_cap | 3.3 | last meaningful line 0.0 h ago (380/380 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t11-3380523 | ot_s81sl_leaf__t11 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (2306/2306 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t43-3364026 | ot_s81sl_leaf__t43 | stage_odb_cap | 4.8 | last meaningful line 0.0 h ago (2094/2094 lines) | YOUNG: evidence 4.8 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t47-1939701 | ot_s81sl_leaf__t47 | stage_odb_cap | 4.9 | last meaningful line 0.0 h ago (2178/2178 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t58-371134 | ot_s81sl_leaf__t58 | 3_3_place_gp | 0.6 | overflow best 0.5814 last 0.5814 rows 7 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2007320 | sle_ctl | stage_odb_cap | 1.6 | last meaningful line 0.0 h ago (256/256 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 5_1_grt | 15.6 | last meaningful line 3.0 h ago (217/226 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | 5_2_route | 16.5 | last meaningful line 0.2 h ago (281/282 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t40__cl1ea9de02-3505370 | slice_station__t40 | 5_2_route | 4.8 | last meaningful line 0.2 h ago (267/268 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t52-381736 | slice_station__t52 | 3_3_place_gp | 0.6 | overflow best 0.3557 last 0.3557 rows 3 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | 5_2_route | 16.8 | last meaningful line 0.5 h ago (264/265 lines) | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-2982583 | slw_fw_v1 | stage_odb_cap | 1.2 | last meaningful line 0.0 h ago (204/204 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | 5_2_route | 17.5 | last meaningful line 0.2 h ago (270/271 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | 5_2_route | 17.5 | last meaningful line 0.2 h ago (283/284 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl63e5a7a2-2927245 | slw_sc_v1 | stage_odb_cap | 1.3 | last meaningful line 0.0 h ago (236/236 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | 5_2_route | 17.9 | last meaningful line 0.5 h ago (276/277 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-2092009 | slw_stm_v2 | 5_1_grt | 1.6 | last meaningful line 0.5 h ago (217/762 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t2-1130517 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 2.1 | last meaningful line 0.2 h ago (463/463 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-svc_lo_dsdv_svc_rs__t6-1380810 | svc_lo_dsdv_svc_rs__t6 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (37/37 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | so_1205352_ff_51495 | so_1205352_ff_51495 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (493/493 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | so_1205352_tt_51495 | so_1205352_tt_51495 | generate_abstract | 0.2 | last meaningful line 0.2 h ago (493/493 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | 5_2_route | 16.8 | last meaningful line 0.0 h ago (271/272 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | 5_2_route | 16.8 | drt_violations best 108699 last 108699 rows 1 | YOUNG: evidence 6.7 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-489810 | slw_fw_v3 | 5_2_route | 16.8 | drt_violations best 12911 last 12911 rows 3 | YOUNG: evidence 7.2 h < 7.5 h |  |
| intel2 | prd-eco_20261120_103658_2442812-i1-1367643 | eco_20261120_103658_2442812-i1 | 5_2_route | 2.8 | last meaningful line 0.3 h ago (266/267 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 26.3 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 60.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | stage_odb_cap | 36.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | 5_1_grt | 37.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 10.7 | last meaningful line 1.1 h ago (1375/1375 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r0_p1__t1__cl911743eb-4083127 | col_h10_r0_p1__t1 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (4272/4272 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv86f5e3b9-311443 | col_h10_r1__t1 | pregrt_ff_hold | 1.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvf724da2a-320050 | col_h10_r1__t1 | pregrt_ff_hold | 1.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-382185 | col_h10_r2__t1 | 5_2_route | 26.3 | drt_violations best 20 last 20 rows 53 | before-window best 28, window best 20 | PROGRESS: drt_violations improved 28.6 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-384874 | col_h10_r2__t1 | 5_2_route | 26.3 | drt_violations best 20 last 20 rows 52 | before-window best 28, window best 20 | PROGRESS: drt_violations improved 28.6 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-4011286 | col_h10_r2__t1 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (4379/4379 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-385072 | col_h10_r2__t1 | 5_2_route | 26.3 | drt_violations best 20 last 20 rows 53 | before-window best 28, window best 20 | PROGRESS: drt_violations improved 28.6 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl8b686b3e-2806632 | col_h10_r2__t1 | stage_odb_cap | 8.0 | last meaningful line 0.0 h ago (4537/4537 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-4028772 | col_h9_r0_p2__t1 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (4238/4238 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv047ea3b3-4028288 | col_h9_r1__t1 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (4339/4339 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv4bd36c74-2878413 | col_h9_r1__t1 | stage_odb_cap | 8.0 | last meaningful line 0.0 h ago (4450/4450 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hgi_v4-4076302 | kv3_hgi_v4 | stage_odb_cap | 7.8 | last meaningful line 0.0 h ago (4013/4013 lines) | PROGRESS: log still growing |  |
| epyc2 | dpkit-kv3_hroot-2852002 | kv3_hroot | stage_odb_cap | 8.0 | last meaningful line 0.0 h ago (4308/4308 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-642785 | col_h9_r0_p1__t1 | 5_2_route | 13.6 | drt_violations best 22296 last 22296 rows 2 | before-window best 150968, window best 22296 | PROGRESS: drt_violations improved 85.2 % in window |  |
| epyc7 | dpkit-sle_st_b_v2__pv41c959f3-3745640 | sle_st_b_v2 | 5_1_grt | 4.7 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 22.6 | drt_violations best 10168 last 49296 rows 18 | before-window best 11104, window best 10168 | PROGRESS: drt_violations improved 8.4 % in window |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-768070 | slw_su_l1 | 5_2_route | 22.3 | drt_violations best 7619 last 38244 rows 18 | before-window best 8002, window best 7619 | PROGRESS: drt_violations improved 4.8 % in window |  |
| epyc7 | klegacy-dsdv_bksel_c_rfda3p-2239264 | dsdv_bksel_c_rfda3p | 5_1_grt | 3.3 | repair_TNS best 0 last 0 rows 174 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | prd-eco_20261120_124815_3297714-i1t-3989767 | eco_20261120_124815_3297714-i1t | 5_2_route | 8.6 | drt_violations best 75 last 75 rows 10 | before-window best 28098, window best 75 | PROGRESS: drt_violations improved 99.7 % in window |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2057329 | col_h9_r0_p3__t1 | tt_setup_repair_grt | 4.9 | repair_Violations best 0 last 0 rows 12 | PROGRESS: repair_Violations reached 0 |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 23.7 | last meaningful line 0.0 h ago (1412/1412 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 18.7 | last meaningful line 0.0 h ago (1133/1133 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-4092448 | hd_mesh | stage_odb_cap | 17.0 | last meaningful line 0.0 h ago (1056/1056 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | pregrt_ff_hold | 10.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | pregrt_ff_hold | 10.6 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 14.3 | last meaningful line 0.0 h ago (1185/1185 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl6740750e-482449 | sle_fw_v2 | stage_odb_cap | 16.8 | last meaningful line 0.0 h ago (1001/1001 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | stage_odb_cap | 17.4 | last meaningful line 0.0 h ago (1113/1113 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2435819 | slw_hc1 | stage_odb_cap | 17.9 | last meaningful line 0.0 h ago (1125/1125 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | stage_odb_cap | 17.0 | last meaningful line 0.0 h ago (1015/1015 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | stage_odb_cap | 16.8 | last meaningful line 0.0 h ago (1001/1001 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-495397 | slw_st_b_v2 | stage_odb_cap | 16.8 | last meaningful line 0.0 h ago (1001/1001 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-498208 | slw_st_b_v2 | stage_odb_cap | 16.8 | last meaningful line 0.0 h ago (1001/1001 lines) | PROGRESS: log still growing |  |
