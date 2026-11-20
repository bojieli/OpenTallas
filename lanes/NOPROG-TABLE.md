# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 05:00 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'NO-PROGRESS': 1, 'GRT-LABEL': 18, 'YOUNG': 113, 'NO-DATA': 1, 'KEEP': 2, 'EXCLUDED': 10, 'PROGRESS': 32}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| intel1 | dpkit-col_h9_r2__t1__clb8d86cd5__pv982ec12c-2337034 | col_h9_r2__t1 | 5_2_route | 17.8 | drt_violations best 65 last 65 rows 13 | before-window best 66, window best 65 | NO-PROGRESS: drt_violations best 65 vs 66 before window: < 2 % in 6 h | REPORTED (cancel next pass) |
| epyc2 | dpkit-ot_s81sl_leaf__t34-502720 | ot_s81sl_leaf__t34 | 5_1_grt | 17.8 | grt rounds 4 overflow 5:39901 -> 10:35125 -> 15:32751 -> 20:33130 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-517470 | ot_s81sl_leaf__t4 | 5_1_grt | 17.8 | grt rounds 3 overflow 5:33299 -> 10:24430 -> 15:21368 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-3946553 | ot_s81sl_leaf__t54 | 5_1_grt | 6.6 | grt rounds 2 overflow 5:45500 -> 10:30539 | GRT-LABEL: DESIGN-FAIL: overflow 30539 at round 10 > 1000 |  |
| epyc7 | dpkit-col_h10_r1__t1__cld01bb4ae-2998457 | col_h10_r1__t1 | 5_1_grt | 15.9 | grt rounds 4 overflow 5:49459 -> 10:15428 -> 15:4782 -> 20:3247 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-505111 | col_h9_r0_p2__t1 | 5_1_grt | 5.2 | grt rounds 3 overflow 5:743 -> 10:873 -> 15:312 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-642825 | col_h9_r0_p5__t1 | 5_1_grt | 5.1 | grt rounds 3 overflow 5:5377 -> 10:3001 -> 15:1717 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv8995e794-643354 | col_h9_r0_p5__t1 | 5_1_grt | 5.1 | grt rounds 3 overflow 5:5377 -> 10:3001 -> 15:1717 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pvb22875c0-913556 | col_h9_r0_p5__t1 | 5_1_grt | 4.8 | grt rounds 3 overflow 5:5377 -> 10:3001 -> 15:1717 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pvbca8d846-643457 | col_h9_r0_p5__t1 | 5_1_grt | 5.1 | grt rounds 3 overflow 5:5377 -> 10:3001 -> 15:1717 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-coll_core-532020 | coll_core | 5_1_grt | 14.1 | grt rounds 3 overflow 5:40992 -> 10:31129 -> 15:30006 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | 5_1_grt | 10.3 | grt rounds 2 overflow 5:8256 -> 10:2829 | GRT-LABEL: DESIGN-FAIL: overflow 2829 at round 10 > 1000 |  |
| intel1 | dpkit-cbx_q10__cl89936551_h-2365139 | cbx_q10 | 5_1_grt | 8.1 | grt rounds 2 overflow 5:2357 -> 10:2032 | GRT-LABEL: DESIGN-FAIL: overflow 2032 at round 10 > 1000 |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 130.9 | grt rounds 6 overflow 5:3621 -> 10:1409 -> 15:822 -> 20:367 -> 25:132 -> 30:21 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 130.9 | grt rounds 6 overflow 5:3459 -> 10:2012 -> 15:1178 -> 20:769 -> 25:322 -> 30:29 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3739403 | ot_s81sl_leaf__t25 | 5_1_grt | 7.4 | grt rounds 3 overflow 5:32732 -> 10:26928 -> 15:21703 | GRT-LABEL: DESIGN-FAIL: overflow 26928 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 6.8 | grt rounds 3 overflow 5:33935 -> 10:14403 -> 15:6927 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-838589 | ot_s81sl_leaf__t53 | 5_1_grt | 6.8 | grt rounds 2 overflow 5:51746 -> 10:53387 | GRT-LABEL: DESIGN-FAIL: overflow 53387 at round 10 > 1000 |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 15.9 | grt rounds 3 overflow 5:49015 -> 10:43178 -> 15:40285 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 2.2 | last meaningful line 0.6 h ago (1365/1365 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2846210 | col_h10_r1__t1 | stage_odb_cap | 4.9 | last meaningful line 0.0 h ago (2628/2628 lines) | YOUNG: evidence 4.9 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3629353 | col_h10_r2__t1 | stage_odb_cap | 4.5 | last meaningful line 0.0 h ago (2480/2480 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__clac068e56-3628511 | col_h10_r2__t1 | stage_odb_cap | 4.5 | last meaningful line 0.0 h ago (2472/2472 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv1c15776f-3629501 | col_h9_r1__t1 | stage_odb_cap | 4.5 | last meaningful line 0.0 h ago (557/557 lines) | YOUNG: evidence 4.5 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pve273b259-3097415 | col_h9_r1__t1 | 5_2_route | 4.7 | last meaningful line 0.3 h ago (268/269 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_LP__t2-3004885 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 7.0 | repair_TNS best 14.28 last 14.28 rows 1 | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t29__cl2e5c855a-2846396 | slice_station__t29 | 5_2_route | 4.9 | drt_violations best 16705 last 16705 rows 1 | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-191709 | slw_fw_v1 | 5_1_grt | 8.0 | last meaningful line 0.3 h ago (1158/1175 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-195673 | slw_fw_v1 | 5_1_grt | 8.0 | last meaningful line 0.1 h ago (1122/1128 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t6-3103921 | svc_hi_dsdv_svc_rs__t6 | 2_1_floorplan | 6.9 | repair_Viol best 55780 last 55780 rows 1258 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t2-2905735 | svc_lo_dsdv_svc_rs__t2 | 1_synth | 7.0 | last meaningful line 0.0 h ago (38/38 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-2277016 | svc_lo_dsdv_svc_rs__t4 | port_bind | 7.2 | last meaningful line 0.0 h ago (1/1 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | otc-1975536-21771 | 1975536 | gen_lint_yosys | 0.7 | last meaningful line 0.7 h ago (1/1 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | otc-2600645-5708 | 2600645 | gen_lint_yosys | 0.5 | last meaningful line 0.5 h ago (1/1 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc2 | otc-4159560-26620 | 4159560 | gen_lint_yosys | 0.1 | last meaningful line 0.1 h ago (1/1 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc2 | prd-count-p1_bc-721450 | count-p1_bc | prd_count_p1_bc | 0.0 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_184546_1168863-i1-2177945 | eco_20261119_184546_1168863-i1 | 5_2_route | 3.4 | drt_violations best 3666 last 3666 rows 1 | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_193300_4163996-i1-3122467 | eco_20261119_193300_4163996-i1 | 5_2_route | 2.9 | drt_violations best 4176 last 4176 rows 1 | YOUNG: evidence 2.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_194246_4168801-i1-2661476 | eco_20261119_194246_4168801-i1 | 5_2_route | 3.1 | drt_violations best 3511 last 3511 rows 1 | YOUNG: evidence 2.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_194719_4168975-i1-1911689 | eco_20261119_194719_4168975-i1 | 5_2_route | 3.5 | drt_violations best 3511 last 3511 rows 1 | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_194944_478551-i1-4136079 | eco_20261119_194944_478551-i1 | 5_2_route | 2.4 | last meaningful line 0.4 h ago (272/273 lines) | YOUNG: evidence 1.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_195623_475807-i1-2402593 | eco_20261119_195623_475807-i1 | 5_2_route | 3.3 | drt_violations best 3511 last 3511 rows 1 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_195829_480745-i1-3584348 | eco_20261119_195829_480745-i1 | 5_2_route | 2.7 | drt_violations best 3511 last 3511 rows 1 | YOUNG: evidence 2.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003408_3748325-i1-3762223 | eco_20261120_003408_3748325-i1 | 5_2_route | 4.4 | last meaningful line 0.1 h ago (263/263 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748476-i1-3763736 | eco_20261120_003409_3748476-i1 | 5_2_route | 4.4 | last meaningful line 0.0 h ago (263/263 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1t-3763698 | eco_20261120_003409_3748726-i1t | 5_2_route | 4.4 | last meaningful line 0.1 h ago (132/132 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_012809_1875451-i1-1613064 | eco_20261120_012809_1875451-i1 | 5_2_route | 1.7 | drt_violations best 32 last 32 rows 1 | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1t-2162531 | eco_recover1120-i1t | 5_1_grt | 1.5 | last meaningful line 0.7 h ago (249/320 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q01-767696 | cbf_q01 | 5_2_route | 13.8 | last meaningful line 0.7 h ago (274/275 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-642785 | col_h9_r0_p1__t1 | 5_1_grt | 5.1 | last meaningful line 0.1 h ago (209/211 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv6882e5ea-505829 | col_h9_r0_p2__t1 | 5_2_route | 5.2 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pvd86cb19a-505172 | col_h9_r0_p2__t1 | 5_2_route | 5.2 | last meaningful line 0.0 h ago (145/145 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-505237 | col_h9_r0_p4__t1 | 5_2_route | 5.2 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-504263 | col_h9_r0_p4__t1 | 5_2_route | 5.2 | last meaningful line 0.2 h ago (271/271 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49f0ba38-263250 | col_h9_r1__t1 | 5_2_route | 5.5 | last meaningful line 0.5 h ago (268/269 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv87d52780-504670 | col_h9_r1__t1 | 5_2_route | 5.2 | last meaningful line 0.5 h ago (266/267 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8ea75ee5-505402 | col_h9_r1__t1 | 5_2_route | 5.2 | last meaningful line 0.7 h ago (264/265 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvadbd1880-505510 | col_h9_r1__t1 | 5_2_route | 5.2 | last meaningful line 0.5 h ago (266/267 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-505372 | col_h9_r1__t1 | 5_2_route | 5.2 | last meaningful line 0.5 h ago (264/265 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvbb600efe-505577 | col_h9_r1__t1 | 5_2_route | 5.2 | last meaningful line 0.4 h ago (268/269 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc7 | dpkit-sle_ctl__cl67434795__padW5-3154753 | sle_ctl | 5_1_grt | 6.7 | last meaningful line 0.5 h ago (167/167 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v2__cl8537f156-3323404 | slw_fw_v2 | 5_2_route | 10.7 | last meaningful line 1.0 h ago (284/285 lines) | YOUNG: evidence 3.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl1bc59e1c-1024005 | slw_hc0 | 5_2_route | 13.5 | drt_violations best 14490 last 14490 rows 2 | YOUNG: evidence 6.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-1780810 | slw_hc1 | 5_2_route | 12.6 | last meaningful line 0.2 h ago (278/279 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cle683a076-2387979 | slw_hc1 | 5_2_route | 11.8 | last meaningful line 0.0 h ago (131/131 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2997578 | slw_sc_v1 | 5_2_route | 11.0 | last meaningful line 0.5 h ago (274/275 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pvc2ec5bfb-240135 | slw_st_b_v2 | 5_2_route | 14.4 | drt_violations best 85240 last 85240 rows 1 | YOUNG: evidence 6.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-2618689 | slw_stm_v1 | 5_2_route | 11.5 | last meaningful line 0.7 h ago (273/274 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-4084399 | tt_ctlm | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (3040/3040 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-4118116 | tt_ctlm | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (3026/3026 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_083952_3300104-i1t-1853493 | eco_20261120_083952_3300104-i1t | 5_2_route | 4.3 | last meaningful line 0.5 h ago (267/268 lines) | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_124815_3297714-i1t-3989767 | eco_20261120_124815_3297714-i1t | 5_1_grt | 0.1 | last meaningful line 0.0 h ago (133/133 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | prd-residual-i2r-1167548 | residual-i2r | 5_2_route | 1.9 | last meaningful line 0.2 h ago (257/258 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| epyc7 | prd-residual-i2r-1174867 | residual-i2r | 5_2_route | 1.9 | last meaningful line 0.2 h ago (127/127 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | dpkit-cbn_q00__cldbcda913-3330181 | cbn_q00 | 5_1_grt | 7.6 | last meaningful line 0.4 h ago (150/150 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p4__t1__pv07945c1e-397135 | col_h10_r0_p4__t1 | 2_4_floorplan_pdn | 0.2 | last meaningful line 0.0 h ago (385/385 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-3326220 | col_h10_r2__t1 | 5_2_route | 7.6 | last meaningful line 0.5 h ago (255/256 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2896534 | col_h10_r2__t1 | 5_2_route | 7.8 | last meaningful line 0.2 h ago (257/258 lines) | YOUNG: evidence 2.8 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-4183728 | col_h9_r1__t1 | 5_2_route | 7.1 | last meaningful line 0.1 h ago (260/260 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-3731937 | col_h9_r1__t1 | 5_2_route | 7.4 | last meaningful line 0.2 h ago (136/136 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2898480 | col_h9_r2__t1 | 5_2_route | 7.8 | last meaningful line 0.7 h ago (253/254 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2898962 | col_h9_r2__t1 | 5_2_route | 7.8 | last meaningful line 0.2 h ago (255/256 lines) | YOUNG: evidence 2.5 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pv09b9967e-562242 | col_h9_r2__t1 | 3_3_place_gp | 0.2 | overflow best 0.4468 last 0.4468 rows 1 | YOUNG: stage 0.0 h < 1 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-2901316 | col_h9_r2__t1 | 5_2_route | 7.8 | last meaningful line 0.7 h ago (255/256 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| intel1 | dpkit-dsdv_slice_iq_C__t1-918334 | dsdv_slice_iq_C__t1 | 1_2_yosys | 0.1 | last meaningful line 0.0 h ago (259/259 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Eo-393779 | kv3_hub_Eo | 3_5_place_dp | 7.0 | last meaningful line 0.5 h ago (113/113 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-1330096 | kv3_pv_v12 | 3_3_place_gp | 6.6 | overflow best 0.0985 last 0.0985 rows 44 | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-3619680 | kv3_pv_v12 | 3_5_place_dp | 9.4 | last meaningful line 0.3 h ago (119/119 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v2-1275856 | kv3_pv_v2 | 3_5_place_dp | 6.6 | last meaningful line 0.0 h ago (35/35 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v2n-880645 | kv3_pv_v2n | 3_5_place_dp | 6.7 | last meaningful line 0.0 h ago (36/36 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3-1202037 | kv3_pv_v3 | 3_4_place_resized | 6.6 | last meaningful line 0.1 h ago (688/688 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3n-3612346 | kv3_pv_v3n | 3_3_place_gp | 5.5 | overflow best 0.134 last 0.134 rows 41 | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v4-1798134 | kv3_pv_v4 | 3_4_place_resized | 6.4 | repair_Remaining best 62501 last 62501 rows 493 | YOUNG: stage 0.1 h < 1 h |  |
| intel1 | dpkit-kv3_pv_v5n-2045384 | kv3_pv_v5n | 3_3_place_gp | 6.3 | overflow best 0.0994 last 0.0994 rows 44 | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t69-3048874 | ot_s81sl_leaf__t69 | 3_5_place_dp | 0.7 | last meaningful line 0.0 h ago (60/60 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | 5_1_grt | 7.8 | last meaningful line 0.1 h ago (165/165 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | 5_1_grt | 7.8 | last meaningful line 0.1 h ago (161/161 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 4_1_cts | 7.1 | last meaningful line 0.7 h ago (7788/7788 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | 5_1_grt | 8.0 | last meaningful line 0.1 h ago (141/141 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v2__cl7b3062fa-694049 | sle_stm_v2 | 5_1_grt | 8.8 | last meaningful line 0.4 h ago (218/795 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l0__cl7a55c676-2377674 | sle_su_l0 | 5_2_route | 8.0 | last meaningful line 0.2 h ago (264/265 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t24__cleece78ec-2385680 | slice_station__t24 | 5_2_route | 8.0 | drt_violations best 7204 last 7204 rows 1 | YOUNG: evidence 5.4 h < 7.5 h |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | 5_1_grt | 8.3 | last meaningful line 0.1 h ago (188/191 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | 5_1_grt | 9.0 | last meaningful line 0.0 h ago (126/126 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | 5_1_grt | 9.0 | last meaningful line 0.2 h ago (130/130 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | 5_1_grt | 9.4 | repair_Remaining best 246519 last 246519 rows 192 | YOUNG: evidence 3.8 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1a1c1f8f-3380863 | slw_su_l0 | 5_2_route | 9.6 | drt_violations best 43448 last 43448 rows 1 | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t2-3187697 | svc_hi_dsdv_svc_rs__t2 | port_bind | 5.7 | last meaningful line 0.2 h ago (1/1 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t3-2197154 | svc_hi_dsdv_svc_rs__t3 | synth_odb_v | 6.2 | last meaningful line 0.2 h ago (4/4 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | otc-2295728-27466 | 2295728 | - | 24.6 |  | NO-DATA: no log found |  |
| intel1 | otc-2677942-26726 | 2677942 | gen_lint_yosys | 0.8 | last meaningful line 0.8 h ago (1/1 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | otc-3239598-26208 | 3239598 | gen_lint_yosys | 0.6 | last meaningful line 0.6 h ago (1/1 lines) | YOUNG: evidence 0.6 h < 7.5 h |  |
| intel1 | prd-eco_20261120_003407_1650578-i1-1677571 | eco_20261120_003407_1650578-i1 | 5_2_route | 4.4 | last meaningful line 0.1 h ago (117/117 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | prd-eco_20261120_003409_1651933-i1t-1681241 | eco_20261120_003409_1651933-i1t | 5_1_grt | 4.4 | last meaningful line 3.0 h ago (244/275 lines) | YOUNG: evidence 4.4 h < 7.5 h |  |
| intel1 | prd-eco_recover1120-i1t-303123 | eco_recover1120-i1t | 5_1_grt | 1.5 | last meaningful line 0.3 h ago (249/308 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | prd-eco_recover1120-i1t-319029 | eco_recover1120-i1t | 5_1_grt | 1.5 | last meaningful line 0.4 h ago (249/351 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | prd-eco_recover1120-i1t-330433 | eco_recover1120-i1t | 5_1_grt | 1.5 | last meaningful line 0.6 h ago (154/154 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-1241882 | col_h9_r0_p1__t1 | 5_1_grt | 5.7 | repair_Viol best 17 last 17 rows 11 | YOUNG: evidence 3.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 3_3_place_gp | 2.1 | overflow best 0.209 last 0.2532 rows 38 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 3_3_place_gp | 2.1 | overflow best 0.1865 last 0.1865 rows 40 | YOUNG: stage 0.8 h < 1 h |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2391268 | kv3_hgi_v1 | 5_1_grt | 2.3 | last meaningful line 0.3 h ago (202/210 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 5_1_grt | 2.3 | last meaningful line 0.5 h ago (202/208 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-1118548 | ot_s81sl_kv_leaf__t5 | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (643/643 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t10-1107312 | ot_s81sl_leaf__t10 | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (631/631 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (678/678 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t58-1113172 | ot_s81sl_leaf__t58 | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (599/599 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t68-1111390 | ot_s81sl_leaf__t68 | stage_odb_cap | 5.8 | last meaningful line 0.0 h ago (567/567 lines) | YOUNG: evidence 5.8 h < 7.5 h |  |
| intel2 | dpkit-serdes__t14-1137423 | serdes__t14 | tt_setup_repair_grt | 5.7 | repair_Viol best 2872 last 2872 rows 491 | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | dpkit-serdes__t1__clb45db5be-1142519 | serdes__t1 | stage_odb_cap | 5.7 | last meaningful line 0.0 h ago (483/483 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| intel2 | dpkit-slw_fw_v3-489810 | slw_fw_v3 | postcts_gate_TT | 8.3 | last meaningful line 0.0 h ago (1991/1991 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2435819 | slw_hc1 | 5_1_grt | 9.4 | last meaningful line 1.0 h ago (220/979 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t1-1341320 | svc_hi_dsdv_svc_pvso_entry__t1 | 2_1_floorplan | 5.6 | repair_Viol best 63954 last 63954 rows 89 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-1267600 | svc_hi_dsdv_svc_rs__t1 | 2_1_floorplan | 5.7 | repair_Viol best 45139 last 45139 rows 333 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-372309 | col_h10_r1__t1 | 5_1_grt | 17.8 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 17.8 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-2585815 | dsdv_slice_lepe_mu_LP__t2 | stage_odb_cap | 35.2 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hg_v1p6-1282096 | kv3_hg_v1p6 | 5_1_grt | 36.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v1__cl42bc8b12-557506 | kv3_hgi_v1 | 5_1_grt | 52.1 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc_v1__cl23f6a148-3798940 | kv3_pc_v1 | 5_1_grt | 65.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc_v1__cl7f648944-3798924 | kv3_pc_v1 | 5_1_grt | 65.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pv_v8-2521551 | kv3_pv_v8 | 5_1_grt | 35.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 52.3 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_pc_v3-2166515 | kv3_pc_v3 | 5_1_grt | 51.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | stage_odb_cap | 28.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | stage_odb_cap | 28.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-382185 | col_h10_r2__t1 | 5_2_route | 17.8 | drt_violations best 43 last 43 rows 46 | before-window best 247, window best 43 | PROGRESS: drt_violations improved 82.6 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-384874 | col_h10_r2__t1 | 5_2_route | 17.8 | drt_violations best 43 last 43 rows 46 | before-window best 247, window best 43 | PROGRESS: drt_violations improved 82.6 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-385072 | col_h10_r2__t1 | 5_2_route | 17.8 | drt_violations best 43 last 43 rows 46 | before-window best 247, window best 43 | PROGRESS: drt_violations improved 82.6 % in window |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-3012090 | dsdv_slice_lepw_mus_LP__t2 | pregrt_ff_hold | 7.0 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-3017015 | svc_lo_dsdv_svc_rs__t1 | 1_2_yosys | 6.9 | last meaningful line 0.0 h ago (910/910 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 14.1 | drt_violations best 13349 last 13349 rows 12 | before-window best 114805, window best 13349 | PROGRESS: drt_violations improved 88.4 % in window |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-768070 | slw_su_l1 | 5_2_route | 13.8 | drt_violations best 8483 last 8483 rows 14 | before-window best 17480, window best 8483 | PROGRESS: drt_violations improved 51.5 % in window |  |
| epyc7 | ksyn-kv3_pc_v6_keepes-1828369 | ksyn-kv3_pc_v6_keepes | lec | 8.2 | LEC last write 0.1 h ago | PROGRESS: LEC still writing |  |
| intel1 | dpkit-cbn_q01__cldd6ea846-4146854 | cbn_q01 | pregrt_ff_hold | 7.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_stm_v1__clbe630b9c-4044402 | sle_stm_v1 | 5_1_grt | 9.2 | repair_TNS best 0 last 0 rows 9 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-842919 | slw_st_b_v1 | pregrt_ff_hold | 6.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 15.2 | last meaningful line 0.0 h ago (905/905 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-coll_ftc-4062937 | coll_ftc | stage_odb_cap | 8.5 | last meaningful line 0.0 h ago (509/509 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 10.2 | last meaningful line 0.0 h ago (627/627 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_lep0N-830501 | hd_lep0N | stage_odb_cap | 8.2 | last meaningful line 0.0 h ago (486/486 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-1602787 | hd_mesh | stage_odb_cap | 9.8 | last meaningful line 0.0 h ago (629/629 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-4092448 | hd_mesh | stage_odb_cap | 8.5 | last meaningful line 0.0 h ago (549/549 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_io_cor_v1-3099429 | kv3_io_cor_v1 | stage_odb_cap | 9.0 | last meaningful line 0.0 h ago (537/537 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_sys_c-480894 | kv3_sys_c | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (495/495 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl6740750e-482449 | sle_fw_v2 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (495/495 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | stage_odb_cap | 8.9 | last meaningful line 0.0 h ago (607/607 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_hc0__cl05696ed1-1266312 | sle_hc0 | stage_odb_cap | 13.6 | last meaningful line 0.0 h ago (863/863 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_hc0__cl929603c0__cl38badc56-1455458 | sle_hc0 | stage_odb_cap | 13.5 | last meaningful line 0.0 h ago (855/855 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c-1455485 | sle_hc0 | stage_odb_cap | 13.5 | last meaningful line 0.0 h ago (866/866 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2444359 | sle_st_b_v1 | stage_odb_cap | 12.3 | last meaningful line 0.0 h ago (736/736 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (494/494 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | 5_1_grt | 8.3 | repair_TNS best 0 last 0 rows 15 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | stage_odb_cap | 8.5 | last meaningful line 0.0 h ago (509/509 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (494/494 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-495397 | slw_st_b_v2 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (494/494 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-498208 | slw_st_b_v2 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (494/494 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-svc_lo_dsdv_svc_rs__t5-448347 | svc_lo_dsdv_svc_rs__t5 | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (495/495 lines) | PROGRESS: log still growing |  |
