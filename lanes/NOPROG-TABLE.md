# NOPROG-TABLE (NOPROG-WATCHDOG, generated 2026-11-20 03:30 PST)

Window 6 h, improvement >= 2 % from best. Verdict counts: {'GRT-LABEL': 14, 'NO-DATA': 4, 'YOUNG': 131, 'KEEP': 2, 'EXCLUDED': 12, 'PROGRESS': 45}. Hosts without report: none.

| host | container | type | stage | age h | metric trend | verdict | action |
|---|---|---|---|---|---|---|---|
| epyc2 | dpkit-ot_s81sl_leaf__t34-502720 | ot_s81sl_leaf__t34 | 5_1_grt | 16.3 | grt rounds 4 overflow 5:39901 -> 10:35125 -> 15:32751 -> 20:33130 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t4-517470 | ot_s81sl_leaf__t4 | 5_1_grt | 16.3 | grt rounds 3 overflow 5:33299 -> 10:24430 -> 15:21368 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | dpkit-ot_s81sl_leaf__t54__cl706d9749-3946553 | ot_s81sl_leaf__t54 | 5_1_grt | 5.1 | grt rounds 2 overflow 5:45500 -> 10:30539 | GRT-LABEL: DESIGN-FAIL: overflow 30539 at round 10 > 1000 |  |
| epyc7 | dpkit-col_h10_r1__t1__cld01bb4ae-2998457 | col_h10_r1__t1 | 5_1_grt | 14.4 | grt rounds 4 overflow 5:49459 -> 10:15428 -> 15:4782 -> 20:3247 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv5c8f2166-642825 | col_h9_r0_p5__t1 | 5_1_grt | 3.6 | grt rounds 3 overflow 5:8479 -> 10:3309 -> 15:1717 | GRT-LABEL: DESIGN-FAIL: overflow 3309 at round 10 > 1000 |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pv8995e794-643354 | col_h9_r0_p5__t1 | 5_1_grt | 3.6 | grt rounds 3 overflow 5:8479 -> 10:3309 -> 15:1717 | GRT-LABEL: DESIGN-FAIL: overflow 3309 at round 10 > 1000 |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pvb22875c0-913556 | col_h9_r0_p5__t1 | 5_1_grt | 3.3 | grt rounds 2 overflow 5:8479 -> 10:3309 | GRT-LABEL: DESIGN-FAIL: overflow 3309 at round 10 > 1000 |  |
| epyc7 | dpkit-col_h9_r0_p5__t1__pvbca8d846-643457 | col_h9_r0_p5__t1 | 5_1_grt | 3.6 | grt rounds 3 overflow 5:8479 -> 10:3309 -> 15:1717 | GRT-LABEL: DESIGN-FAIL: overflow 3309 at round 10 > 1000 |  |
| epyc7 | dpkit-coll_core-532020 | coll_core | 5_1_grt | 12.6 | grt rounds 3 overflow 5:41395 -> 10:31555 -> 15:30006 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kit-2538957 | kit | 5_1_grt | 129.4 | grt rounds 6 overflow 5:3621 -> 10:1409 -> 15:822 -> 20:367 -> 25:132 -> 30:21 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-kit-2546869 | kit | 5_1_grt | 129.4 | grt rounds 6 overflow 5:3459 -> 10:2012 -> 15:1178 -> 20:769 -> 25:322 -> 30:29 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| intel1 | dpkit-ot_s81sl_leaf__t25__cl431c660f-3739403 | ot_s81sl_leaf__t25 | 5_1_grt | 5.9 | grt rounds 2 overflow 5:32732 -> 10:26928 | GRT-LABEL: DESIGN-FAIL: overflow 26928 at round 10 > 1000 |  |
| intel1 | dpkit-ot_s81sl_leaf__t40__cl86ea32b3__sid5S-837666 | ot_s81sl_leaf__t40 | 5_1_grt | 5.3 | grt rounds 2 overflow 5:33935 -> 10:14403 | GRT-LABEL: DESIGN-FAIL: overflow 14403 at round 10 > 1000 |  |
| intel1 | dpkit-sle_ctl__cl372cea1c-784571 | sle_ctl | 5_1_grt | 14.4 | grt rounds 3 overflow 5:49015 -> 10:43864 -> 15:40285 | GRT-LABEL: DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion) |  |
| epyc2 | ap-ageom-kw-eng--t1-grt-1979906 | eng--t1-grt | - | 0.1 |  | NO-DATA: no log found |  |
| epyc2 | dhr1-drt7-cut_small-p16g | dhr1-drt7-cut_small-p16g | drt_TT | 0.7 | last meaningful line 0.5 h ago (1363/1363 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv1a6ec9c2-2838743 | col_h10_r1__t1 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (1744/1744 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv6a7ae122-2846210 | col_h10_r1__t1 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (1738/1738 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv74ebbc00-3105751 | col_h10_r1__t1 | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (1669/1669 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pva3a8bfd1-3628147 | col_h10_r1__t1 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (537/537 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pvce76611c-3097921 | col_h10_r1__t1 | stage_odb_cap | 3.2 | last meaningful line 0.0 h ago (1668/1668 lines) | YOUNG: evidence 3.2 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-3629353 | col_h10_r2__t1 | 5_1_grt | 3.0 | last meaningful line 0.4 h ago (235/479 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r0_p3__t1__cl31d0dc4b-3903280 | col_h9_r0_p3__t1 | tt_setup_repair_grt | 5.1 | repair_Viol best 809 last 809 rows 849 | YOUNG: stage 0.4 h < 1 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pv1c15776f-3629501 | col_h9_r1__t1 | stage_odb_cap | 3.0 | last meaningful line 0.0 h ago (468/468 lines) | YOUNG: evidence 3.0 h < 7.5 h |  |
| epyc2 | dpkit-col_h9_r1__t1__cl49d7a23e__pve273b259-3097415 | col_h9_r1__t1 | tt_setup_measure_grt | 3.2 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | dpkit-dsdv_slice_lepw_mu_LP__t2-3004885 | dsdv_slice_lepw_mu_LP__t2 | pregrt_ff_hold | 5.5 | repair_TNS best 14.28 last 14.28 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc2 | dpkit-slice_station__t29__cl2e5c855a-2846396 | slice_station__t29 | stage_odb_cap | 3.4 | last meaningful line 0.0 h ago (405/405 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| epyc2 | dpkit-slw_fw_v1__cl51d45468-191709 | slw_fw_v1 | 5_1_grt | 6.5 | repair_Remaining best 189585 last 189585 rows 250 | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t4-2666489 | svc_hi_dsdv_svc_rs__t4 | 2_1_floorplan | 5.6 | repair_Viol best 50584 last 50584 rows 647 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t5-3105046 | svc_hi_dsdv_svc_rs__t5 | 2_1_floorplan | 5.4 | repair_Viol best 55750 last 55750 rows 652 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | dpkit-svc_hi_dsdv_svc_rs__t6-3103921 | svc_hi_dsdv_svc_rs__t6 | 2_1_floorplan | 5.4 | repair_Viol best 55780 last 55780 rows 536 | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t1-3017015 | svc_lo_dsdv_svc_rs__t1 | 1_2_yosys | 5.4 | last meaningful line 0.1 h ago (673/673 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t2-2905735 | svc_lo_dsdv_svc_rs__t2 | 1_2_yosys | 5.5 | last meaningful line 0.0 h ago (680/680 lines) | YOUNG: evidence 5.4 h < 7.5 h |  |
| epyc2 | dpkit-svc_lo_dsdv_svc_rs__t4-2277016 | svc_lo_dsdv_svc_rs__t4 | 1_2_yosys | 5.7 | last meaningful line 0.0 h ago (879/879 lines) | YOUNG: evidence 5.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_182440_1167722-i1-3155529 | eco_20261119_182440_1167722-i1 | 5_3_fillcell | 3.2 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_184546_1168863-i1-2177945 | eco_20261119_184546_1168863-i1 | 5_2_route | 1.9 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_184643_1170981-i1-721450 | eco_20261119_184643_1170981-i1 | 5_2_route | 2.4 | drt_violations best 3666 last 3666 rows 1 | YOUNG: evidence 2.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_193300_4163996-i1-3122467 | eco_20261119_193300_4163996-i1 | 5_2_route | 1.4 | last meaningful line 0.4 h ago (262/263 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_194246_4168801-i1-2661476 | eco_20261119_194246_4168801-i1 | 5_2_route | 1.6 | last meaningful line 0.1 h ago (268/269 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_194719_4168975-i1-1911689 | eco_20261119_194719_4168975-i1 | 5_2_route | 2.0 | drt_violations best 3511 last 3511 rows 1 | YOUNG: evidence 1.6 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_194944_478551-i1-4136079 | eco_20261119_194944_478551-i1 | 5_2_route | 0.9 | last meaningful line 0.1 h ago (258/259 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_195623_475807-i1-2402593 | eco_20261119_195623_475807-i1 | 5_2_route | 1.8 | last meaningful line 0.2 h ago (272/273 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_195829_480745-i1-3584348 | eco_20261119_195829_480745-i1 | 5_2_route | 1.2 | last meaningful line 0.1 h ago (262/263 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | prd-eco_20261119_224849_4166833-i1-701492 | eco_20261119_224849_4166833-i1 | 5_2_route | 4.7 | drt_violations best 7385 last 7385 rows 2 | YOUNG: evidence 3.5 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003408_3748325-i1-3762223 | eco_20261120_003408_3748325-i1 | 5_1_grt | 2.9 | last meaningful line 2.3 h ago (250/588 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748476-i1-3763736 | eco_20261120_003409_3748476-i1 | 5_1_grt | 2.9 | last meaningful line 2.3 h ago (253/641 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_003409_3748726-i1t-3763698 | eco_20261120_003409_3748726-i1t | 5_1_grt | 2.9 | last meaningful line 2.3 h ago (245/281 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc2 | prd-eco_20261120_012809_1875451-i1-1613064 | eco_20261120_012809_1875451-i1 | 5_1_grt | 0.2 | last meaningful line 0.2 h ago (249/1222 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| epyc2 | prd-eco_recover1120-i1t-2162531 | eco_recover1120-i1t | 5_1_grt | 0.0 | last meaningful line 0.0 h ago (13/13 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-cbf_q01-767696 | cbf_q01 | 5_2_route | 12.3 | last meaningful line 0.8 h ago (266/267 lines) | YOUNG: evidence 3.1 h < 7.5 h |  |
| epyc7 | dpkit-cbn_q01__cld9ff4c40-3455838 | cbn_q01 | 5_1_grt | 4.9 | last meaningful line 0.0 h ago (181/181 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p1__t1__pvb3e2a60a-642785 | col_h9_r0_p1__t1 | 5_1_grt | 3.6 | repair_Remaining best 154573 last 154573 rows 84 | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pv6882e5ea-505829 | col_h9_r0_p2__t1 | 5_1_grt | 3.7 | repair_Remaining best 32751 last 32751 rows 159 | YOUNG: evidence 2.8 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pvd86cb19a-505172 | col_h9_r0_p2__t1 | 5_1_grt | 3.7 | repair_Remaining best 23751 last 23751 rows 168 | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pv5752c4ff-505111 | col_h9_r0_p2__t1 | 5_1_grt | 3.7 | last meaningful line 1.8 h ago (207/218 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p2__t1__cl9f71e63d__pvabc9823e-505736 | col_h9_r0_p2__t1 | 5_1_grt | 3.7 | last meaningful line 1.5 h ago (207/217 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-505237 | col_h9_r0_p4__t1 | 5_1_grt | 3.7 | last meaningful line 1.0 h ago (239/1340 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv49f0ba38-263250 | col_h9_r1__t1 | postcts_gate_TT | 4.0 | last meaningful line -0.0 h ago (25597/25597 lines) | YOUNG: evidence 0.1 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv87d52780-504670 | col_h9_r1__t1 | postcts_gate_FF | 3.7 | last meaningful line 0.0 h ago (16/16 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pv8ea75ee5-505402 | col_h9_r1__t1 | tt_setup_measure_grt | 3.7 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvadbd1880-505510 | col_h9_r1__t1 | tt_setup_measure_grt | 3.7 | last meaningful line 0.0 h ago (30/30 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvafa6f454-505372 | col_h9_r1__t1 | tt_setup_repair_grt | 3.7 | repair_Viol best 757 last 757 rows 985 | YOUNG: stage 0.4 h < 1 h |  |
| epyc7 | dpkit-col_h9_r1__t1__cl49d7a23e__pvbb600efe-505577 | col_h9_r1__t1 | tt_setup_measure_grt | 3.7 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| epyc7 | dpkit-sle_sc_v1__cl7479a5ec-3298474 | sle_sc_v1 | 6_report | 14.1 | last meaningful line 0.0 h ago (1079/1079 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_fw_v2__cl8537f156-3323404 | slw_fw_v2 | 5_2_route | 9.2 | last meaningful line 0.1 h ago (278/279 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc0__cl1bc59e1c-1024005 | slw_hc0 | 5_2_route | 12.0 | drt_violations best 103810 last 103810 rows 1 | YOUNG: evidence 5.1 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl3449ea95-1780810 | slw_hc1 | 5_2_route | 11.1 | last meaningful line 0.2 h ago (139/139 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| epyc7 | dpkit-slw_hc1__cl68f9248e__cle683a076-2387979 | slw_hc1 | postcts_gate_TT | 10.3 | last meaningful line 0.0 h ago (755/755 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-2997578 | slw_sc_v1 | 5_2_route | 9.5 | last meaningful line 0.3 h ago (267/267 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| epyc7 | dpkit-slw_st_b_v2__pvc2ec5bfb-240135 | slw_st_b_v2 | 5_2_route | 12.9 | drt_violations best 85240 last 85240 rows 1 | YOUNG: evidence 4.6 h < 7.5 h |  |
| epyc7 | dpkit-slw_stm_v1__cl05fc43f7__cl389df4e9-2618689 | slw_stm_v1 | 5_2_route | 10.0 | last meaningful line 0.5 h ago (265/266 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| epyc7 | dpkit-slw_su_l1__cla2a78701-531187 | slw_su_l1 | 5_2_route | 12.6 | drt_violations best 16045 last 16045 rows 10 | YOUNG: evidence 7.4 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-4084399 | tt_ctlm | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (2140/2140 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc7 | dpkit-tt_ctlm-4118116 | tt_ctlm | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (2126/2126 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| epyc7 | prd-eco_20261120_083952_3300104-i1t-1853493 | eco_20261120_083952_3300104-i1t | 5_2_route | 2.8 | last meaningful line 0.1 h ago (133/133 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| epyc7 | prd-residual-i2r-1167548 | residual-i2r | 5_1_grt | 0.4 | last meaningful line 0.1 h ago (235/278 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| epyc7 | prd-residual-i2r-1174867 | residual-i2r | 5_1_grt | 0.4 | last meaningful line 0.0 h ago (135/135 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel1 | ap-ageom-sle_sc_v1__cl7479a5ec-dump-247463 | ap-ageom-sle_sc_v1 | - | 0.0 |  | NO-DATA: no log found |  |
| intel1 | dpkit-cbf_q00__cl870de686-780826 | cbf_q00 | tt_setup_repair_grt | 14.4 | repair_Remaining best 42180 last 42180 rows 226 | YOUNG: evidence 2.1 h < 7.5 h |  |
| intel1 | dpkit-cbf_q11-2627513 | cbf_q11 | 5_1_grt | 4.5 | last meaningful line 0.3 h ago (197/206 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-cbn_q01__clab6e67f2-1767064 | cbn_q01 | pregrt_ff_hold | 8.8 | repair_Violations best 58 last 58 rows 13 | YOUNG: evidence 4.0 h < 7.5 h |  |
| intel1 | dpkit-cbn_q01__cldd6ea846-4146854 | cbn_q01 | pregrt_ff_hold | 5.7 | last meaningful line 0.0 h ago (34/34 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl89936551-3322021 | cbx_q10 | 5_1_grt | 6.1 | last meaningful line 0.2 h ago (137/137 lines) | YOUNG: evidence 0.3 h < 7.5 h |  |
| intel1 | dpkit-cbx_q10__cl89936551_h-2365139 | cbx_q10 | 5_1_grt | 6.6 | last meaningful line 0.2 h ago (138/138 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r0_p1__t1__cl911743eb-4173007 | col_h10_r0_p1__t1 | 5_1_grt | 5.6 | last meaningful line 1.3 h ago (209/214 lines) | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl8b686b3e-3326220 | col_h10_r2__t1 | 5_2_route | 6.1 | last meaningful line 0.1 h ago (136/136 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h10_r2__t1__cl99efd374__pv1619ecc6-2896534 | col_h10_r2__t1 | 5_2_route | 6.3 | last meaningful line 0.3 h ago (252/252 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p1__t1__pvf9acce4c-1305862 | col_h9_r0_p1__t1 | 5_1_grt | 5.1 | last meaningful line 0.3 h ago (157/157 lines) | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p2__t1__cl0045af7b__pva2793873-422922 | col_h9_r0_p2__t1 | 5_1_grt | 5.4 | last meaningful line 0.2 h ago (241/315 lines) | YOUNG: evidence 3.4 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl0cd90c0e__pv13474472-2349309 | col_h9_r0_p3__t1 | 5_1_grt | 4.6 | last meaningful line 0.0 h ago (209/210 lines) | YOUNG: evidence 1.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898-2622406 | col_h9_r0_p3__t1 | 5_1_grt | 4.5 | last meaningful line 0.2 h ago (159/159 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a-2628597 | col_h9_r0_p3__t1 | 5_1_grt | 4.5 | last meaningful line 0.3 h ago (158/158 lines) | YOUNG: evidence 1.1 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31-834658 | col_h9_r0_p4__t1 | 5_1_grt | 5.3 | last meaningful line 0.2 h ago (429/458 lines) | YOUNG: evidence 3.3 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv2f96c04f-4183728 | col_h9_r1__t1 | tt_setup_repair_grt | 5.6 | repair_Viol best 1538 last 1538 rows 197 | YOUNG: stage 0.2 h < 1 h |  |
| intel1 | dpkit-col_h9_r1__t1__cl49d7a23e__pv36da905c-3731937 | col_h9_r1__t1 | tt_setup_repair_grt | 5.9 | last meaningful line 0.0 h ago (14/14 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clb8d86cd5__pv6a2b031b-2898480 | col_h9_r2__t1 | 5_2_route | 6.3 | last meaningful line 0.2 h ago (136/136 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4-2898962 | col_h9_r2__t1 | 5_2_route | 6.3 | last meaningful line 0.0 h ago (250/250 lines) | YOUNG: evidence 1.0 h < 7.5 h |  |
| intel1 | dpkit-col_h9_r2__t1__clce45cab5__pvdc7d4221-2901316 | col_h9_r2__t1 | 5_2_route | 6.3 | last meaningful line 0.7 h ago (251/252 lines) | YOUNG: evidence 1.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p2-911752 | kv3_hg_v1p2 | 3_5_place_dp | 5.2 | last meaningful line 0.0 h ago (84/84 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p3-339808 | kv3_hg_v1p3 | 3_5_place_dp | 5.5 | last meaningful line 1.3 h ago (47/47 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_hg_v1p6-275673 | kv3_hg_v1p6 | 3_5_place_dp | 5.5 | last meaningful line 1.5 h ago (48/48 lines) | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_hub_Eo-393779 | kv3_hub_Eo | 3_4_place_resized | 5.5 | last meaningful line 0.1 h ago (469/469 lines) | YOUNG: evidence 0.2 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v1-1207085 | kv3_pv_v1 | 3_4_place_resized | 5.1 | last meaningful line 0.0 h ago (31/31 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-1330096 | kv3_pv_v12 | 3_3_place_gp | 5.1 | overflow best 0.5283 last 0.5283 rows 19 | YOUNG: evidence 1.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v12-3619680 | kv3_pv_v12 | 3_4_place_resized | 7.9 | last meaningful line 0.5 h ago (594/594 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v2-1275856 | kv3_pv_v2 | 3_3_place_gp | 5.1 | overflow best 0.0994 last 0.0994 rows 43 | YOUNG: evidence 2.0 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v2n-880645 | kv3_pv_v2n | 3_3_place_gp | 5.2 | overflow best 0.0994 last 0.0994 rows 43 | YOUNG: evidence 2.4 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3-1202037 | kv3_pv_v3 | 3_3_place_gp | 5.1 | overflow best 0.194 last 0.194 rows 33 | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v3n-3612346 | kv3_pv_v3n | 3_3_place_gp | 4.0 | last meaningful line 0.3 h ago (39/39 lines) | YOUNG: evidence 0.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v4-1798134 | kv3_pv_v4 | 3_3_place_gp | 4.9 | overflow best 0.2267 last 0.2267 rows 33 | YOUNG: evidence 1.5 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v5n-2045384 | kv3_pv_v5n | 3_3_place_gp | 4.8 | last meaningful line 0.0 h ago (510/510 lines) | YOUNG: evidence 0.8 h < 7.5 h |  |
| intel1 | dpkit-kv3_pv_v7-1908786 | kv3_pv_v7 | 3_5_place_dp | 8.8 | last meaningful line 0.8 h ago (119/119 lines) | YOUNG: evidence 1.2 h < 7.5 h |  |
| intel1 | dpkit-ot_s81sl_leaf__t53__cl958451dd-838589 | ot_s81sl_leaf__t53 | 5_1_grt | 5.3 | last meaningful line 0.5 h ago (204/209 lines) | YOUNG: evidence 2.2 h < 7.5 h |  |
| intel1 | dpkit-sle_ctl__cl67434795-7485 | sle_ctl | 4_1_cts | 5.6 | last meaningful line 0.3 h ago (7758/7758 lines) | YOUNG: evidence 1.8 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v1__clbe630b9c-4044402 | sle_stm_v1 | 5_1_grt | 7.7 | last meaningful line 1.0 h ago (186/186 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-sle_stm_v2__cl7b3062fa-694049 | sle_stm_v2 | 5_1_grt | 7.3 | last meaningful line 0.2 h ago (141/141 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel1 | dpkit-sle_su_l0__cl7a55c676-2377674 | sle_su_l0 | 5_2_route | 6.5 | last meaningful line 0.2 h ago (255/255 lines) | YOUNG: evidence 1.6 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t24__cleece78ec-2385680 | slice_station__t24 | 5_2_route | 6.5 | last meaningful line 0.5 h ago (242/243 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel1 | dpkit-slice_station__t7__cl362204c4-2903658 | slice_station__t7 | 6_report | 6.3 | last meaningful line 0.0 h ago (24/24 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel1 | dpkit-slw_sc_v1__cl64543eaf__cl4590432d-3640277 | slw_sc_v1 | 5_1_grt | 7.9 | last meaningful line 1.0 h ago (143/143 lines) | YOUNG: evidence 2.3 h < 7.5 h |  |
| intel1 | dpkit-slw_stm_v2__cl1ca9c415-3106017 | slw_stm_v2 | 5_1_grt | 6.2 | last meaningful line 0.5 h ago (142/142 lines) | YOUNG: evidence 0.9 h < 7.5 h |  |
| intel1 | dpkit-slw_su_l0__cl1a1c1f8f-3380863 | slw_su_l0 | 5_2_route | 8.1 | last meaningful line 0.7 h ago (262/263 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t2-3187697 | svc_hi_dsdv_svc_rs__t2 | 1_2_yosys | 4.2 | last meaningful line 0.1 h ago (599/599 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel1 | dpkit-svc_hi_dsdv_svc_rs__t3-2197154 | svc_hi_dsdv_svc_rs__t3 | 1_2_yosys | 4.7 | last meaningful line 0.3 h ago (625/625 lines) | YOUNG: evidence 4.6 h < 7.5 h |  |
| intel1 | otc-2295728-27466 | 2295728 | - | 23.1 |  | NO-DATA: no log found |  |
| intel1 | prd-eco_20261120_003407_1650578-i1-1677571 | eco_20261120_003407_1650578-i1 | 5_1_grt | 2.9 | last meaningful line 1.0 h ago (244/384 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | prd-eco_20261120_003409_1651933-i1t-1681241 | eco_20261120_003409_1651933-i1t | 5_1_grt | 2.9 | last meaningful line 1.5 h ago (244/275 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel1 | prd-eco_recover1120-i1t-303123 | eco_recover1120-i1t | 5_1_grt | 0.0 | last meaningful line -0.0 h ago (5/5 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | cw9a-cw9a | cw9a-cw9a | - | 0.6 |  | NO-DATA: no log found |  |
| intel2 | dpkit-col_h9_r0_p1__t1__pv697f40c9-1241882 | col_h9_r0_p1__t1 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (363/363 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel2 | dpkit-hd_lep0N-830501 | hd_lep0N | 4_1_cts | 6.7 | last meaningful line 0.0 h ago (8606/8606 lines) | YOUNG: evidence 3.9 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680076 | kv3_hg_v1p6 | 2_1_floorplan | 0.6 | last meaningful line 0.1 h ago (1410/1410 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-kv3_hg_v1p6-2680438 | kv3_hg_v1p6 | 2_1_floorplan | 0.6 | last meaningful line 0.1 h ago (1410/1410 lines) | YOUNG: evidence 0.4 h < 7.5 h |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2391268 | kv3_hgi_v1 | 3_4_place_resized | 0.8 | last meaningful line -0.0 h ago (19/19 lines) | YOUNG: evidence 0.0 h < 7.5 h |  |
| intel2 | dpkit-kv3_hgi_v1__cl141fc26e-2426424 | kv3_hgi_v1 | 3_3_place_gp | 0.8 | overflow best 0.0996 last 0.0996 rows 50 | YOUNG: stage 0.4 h < 1 h |  |
| intel2 | dpkit-ot_s81sl_kv_leaf__t5-1118548 | ot_s81sl_kv_leaf__t5 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (553/553 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t10-1107312 | ot_s81sl_leaf__t10 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (542/542 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t28-1126913 | ot_s81sl_leaf__t28 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (589/589 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t58-1113172 | ot_s81sl_leaf__t58 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (509/509 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel2 | dpkit-ot_s81sl_leaf__t68-1111390 | ot_s81sl_leaf__t68 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (477/477 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel2 | dpkit-serdes__t13-1003366 | serdes__t13 | stage_odb_cap | 4.3 | last meaningful line 0.0 h ago (258/258 lines) | YOUNG: evidence 4.3 h < 7.5 h |  |
| intel2 | dpkit-serdes__t14-1137423 | serdes__t14 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (391/391 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel2 | dpkit-serdes__t1__clb45db5be-1142519 | serdes__t1 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (394/394 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel2 | dpkit-sle_fw_v2__cl69f5e854-3239385 | sle_fw_v2 | 5_1_grt | 7.4 | last meaningful line 2.3 h ago (216/1036 lines) | YOUNG: evidence 2.7 h < 7.5 h |  |
| intel2 | dpkit-slw_sc_v1__cl64543eaf__cl5e017c6f-4065313 | slw_sc_v1 | 5_1_grt | 7.0 | last meaningful line 0.2 h ago (967/989 lines) | YOUNG: evidence 2.9 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_pvso_entry__t1-1341320 | svc_hi_dsdv_svc_pvso_entry__t1 | stage_odb_cap | 4.1 | last meaningful line 0.0 h ago (244/244 lines) | YOUNG: evidence 4.1 h < 7.5 h |  |
| intel2 | dpkit-svc_hi_dsdv_svc_rs__t1-1267600 | svc_hi_dsdv_svc_rs__t1 | stage_odb_cap | 4.2 | last meaningful line 0.0 h ago (247/247 lines) | YOUNG: evidence 4.2 h < 7.5 h |  |
| intel2 | so_2524286_ff_96178 | so_2524286_ff_96178 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (1034/1034 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| intel2 | so_2524286_tt_96178 | so_2524286_tt_96178 | generate_abstract | 0.7 | last meaningful line 0.5 h ago (1034/1034 lines) | YOUNG: evidence 0.7 h < 7.5 h |  |
| epyc2 | dpkit-col_h10_r1__t1__cl95b37463__pv799da6f8-372309 | col_h10_r1__t1 | 5_1_grt | 16.3 |  | KEEP: col_h10_r1__t1__cl95b37463__pv799da6f8	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvf1512c16-387127 | col_h10_r2__t1 | 5_2_route | 16.3 |  | KEEP: col_h10_r2__t1__cl1f5d6c2a__pvf1512c16	S81-COL-INHERIT	representative (COORD 11- |  |
| epyc2 | otc-1219850-14359 | 1219850 | - | 0.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-dsdv_slice_lepe_mu_LP__t2-2585815 | dsdv_slice_lepe_mu_LP__t2 | stage_odb_cap | 33.7 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hg_v1p6-1282096 | kv3_hg_v1p6 | 5_1_grt | 35.0 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v1__cl42bc8b12-557506 | kv3_hgi_v1 | 5_1_grt | 50.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_hgi_v3-1645316 | kv3_hgi_v3 | tt_setup_repair_grt | 34.6 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc_v1__cl23f6a148-3798940 | kv3_pc_v1 | 5_1_grt | 63.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pc_v1__cl7f648944-3798924 | kv3_pc_v1 | 5_1_grt | 63.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc7 | dpkit-kv3_pv_v8-2521551 | kv3_pv_v8 | 5_1_grt | 33.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_io_cor-767906 | kv3_io_cor | 5_2_route | 50.8 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel1 | dpkit-kv3_pc_v3-2166515 | kv3_pc_v3 | 5_1_grt | 49.9 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv0c1de895-1681005 | col_h10_r2__t1 | stage_odb_cap | 26.5 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| intel2 | dpkit-kv3_pv_v8-376552 | kv3_pv_v8 | stage_odb_cap | 27.4 |  | EXCLUDED: plan priority job (bind/LATCHECK/G0/die-proto) |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv16277ca6-382185 | col_h10_r2__t1 | 5_2_route | 16.3 | drt_violations best 72 last 76 rows 39 | before-window best 1437, window best 72 | PROGRESS: drt_violations improved 95.0 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvcd889288-384874 | col_h10_r2__t1 | 5_2_route | 16.3 | drt_violations best 44 last 44 rows 40 | before-window best 1437, window best 44 | PROGRESS: drt_violations improved 96.9 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pvec003743-385072 | col_h10_r2__t1 | 5_2_route | 16.3 | drt_violations best 72 last 76 rows 39 | before-window best 1437, window best 72 | PROGRESS: drt_violations improved 95.0 % in window |  |
| epyc2 | dpkit-col_h10_r2__t1__clac068e56-3628511 | col_h10_r2__t1 | 5_1_grt | 3.0 | repair_TNS best 0 last 0 rows 4 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-dsdv_slice_lepw_mus_LP__t2-3012090 | dsdv_slice_lepw_mus_LP__t2 | pregrt_ff_hold | 5.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc2 | dpkit-slw_fw_v1__clf51c11d8__clc7ddab13-195673 | slw_fw_v1 | 5_1_grt | 6.5 | grt_overflow best 0 last 0 rows 1 | PROGRESS: grt_overflow reached 0 |  |
| epyc7 | dpkit-col_h9_r0_p4__t1__clcb2fbfe8__pvec137455-504263 | col_h9_r0_p4__t1 | 5_1_grt | 3.7 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-sle_ctl__cl67434795__padW5-3154753 | sle_ctl | pregrt_ff_hold | 5.2 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | dpkit-slw_su_l1__clcc9d0155-768070 | slw_su_l1 | 5_2_route | 12.3 | drt_violations best 10304 last 10304 rows 12 | before-window best 111405, window best 10304 | PROGRESS: drt_violations improved 90.8 % in window |  |
| epyc7 | dpkit-tt_ctlm-1066664 | tt_ctlm | stage_odb_cap | 7.5 | last meaningful line 0.0 h ago (4064/4064 lines) | PROGRESS: log still growing |  |
| epyc7 | dpkit-tt_ctlm-1066712 | tt_ctlm | stage_odb_cap | 7.5 | last meaningful line 0.0 h ago (4032/4032 lines) | PROGRESS: log still growing |  |
| epyc7 | klegacy-dsdv_bksel_c_rfdqctl-1318076 | dsdv_bksel_c_rfdqctl | 5_1_grt | 3.0 | repair_TNS best 0 last 0 rows 183 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | klegacy-dsdv_bksel_c_rfdqctl-1318076-lec | dsdv_bksel_c_rfdqctl | 5_1_grt | 2.9 | repair_TNS best 0 last 0 rows 183 | PROGRESS: repair_TNS reached 0 |  |
| epyc7 | ksyn-kv3_pc_v6_keepes-1828369 | ksyn-kv3_pc_v6_keepes | lec | 6.7 | LEC last write 0.2 h ago | PROGRESS: LEC still writing |  |
| intel1 | dpkit-cbn_q00__cldbcda913-3330181 | cbn_q00 | pregrt_ff_hold | 6.1 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-col_h9_r2__t1__clb8d86cd5__pv982ec12c-2337034 | col_h9_r2__t1 | 5_2_route | 16.3 | drt_violations best 65 last 65 rows 13 | before-window best 100, window best 65 | PROGRESS: drt_violations improved 35.0 % in window |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE0-2899102 | sle_ctl | pregrt_ff_hold | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_ctl__cl503337ff__padE4-2900534 | sle_ctl | pregrt_ff_hold | 6.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-sle_stm_v1__cl27746664-2381188 | sle_stm_v1 | pregrt_ff_hold | 6.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slice_station__t52-2567012 | slice_station__t52 | 5_1_grt | 6.4 | repair_TNS best 0 last 0 rows 12 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_fe_v1__cl95cd1d0c-1873789 | slw_fe_v1 | pregrt_ff_hold | 6.8 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc0__cl4f54b7a3-315618 | slw_hc0 | pregrt_ff_hold | 7.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_hc2__cl6bcaba89-314198 | slw_hc2 | pregrt_ff_hold | 7.5 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel1 | dpkit-slw_st_b_v1__cle6023ec2-842919 | slw_st_b_v1 | pregrt_ff_hold | 5.3 | repair_TNS best 0 last 0 rows 1 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0-2688718 | col_h10_r2__t1 | stage_odb_cap | 13.7 | last meaningful line 0.0 h ago (816/816 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-coll_ftc-4062937 | coll_ftc | stage_odb_cap | 7.0 | last meaningful line 0.0 h ago (419/419 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-glue-4013867 | glue | stage_odb_cap | 9.4 | last meaningful line 0.0 h ago (622/622 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_host_e-775407 | hd_host_e | stage_odb_cap | 8.7 | last meaningful line 0.0 h ago (537/537 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-1602787 | hd_mesh | stage_odb_cap | 8.3 | last meaningful line 0.0 h ago (540/540 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-hd_mesh-4092448 | hd_mesh | stage_odb_cap | 7.0 | last meaningful line 0.0 h ago (460/460 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_io_cor_v1-3099429 | kv3_io_cor_v1 | stage_odb_cap | 7.5 | last meaningful line 0.0 h ago (447/447 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-kv3_sys_c-480894 | kv3_sys_c | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (405/405 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_fw_v2__cl6740750e-482449 | sle_fw_v2 | 5_1_grt | 6.8 | repair_TNS best 0 last 0 rows 11 | PROGRESS: repair_TNS reached 0 |  |
| intel2 | dpkit-sle_hc0__cl05696ed1-1266312 | sle_hc0 | stage_odb_cap | 12.1 | last meaningful line 0.0 h ago (774/774 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_hc0__cl929603c0__cl38badc56-1455458 | sle_hc0 | stage_odb_cap | 12.0 | last meaningful line 0.0 h ago (766/766 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_hc0__cl929603c0__cl4baa7c9c-1455485 | sle_hc0 | stage_odb_cap | 12.0 | last meaningful line 0.0 h ago (777/777 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pv0e7b1dcc-2444359 | sle_st_b_v1 | stage_odb_cap | 10.8 | last meaningful line 0.0 h ago (647/647 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-sle_st_b_v1__pvc5a85fd4__pv38472fb8-486644 | sle_st_b_v1 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (405/405 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v1__clf51c11d8__cl592e3d37-488539 | slw_fw_v1 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (405/405 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_fw_v3-489810 | slw_fw_v3 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (405/405 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_hc1__cl68f9248e__cl144ee7b3-2435819 | slw_hc1 | stage_odb_cap | 7.9 | last meaningful line 0.0 h ago (529/529 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v1__cl6357f1cc__pv6ace3e48-492590 | slw_st_b_v1 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (405/405 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pv3d7bec84-495397 | slw_st_b_v2 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (405/405 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-slw_st_b_v2__pva66d0f22__pvb80e2003-498208 | slw_st_b_v2 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (405/405 lines) | PROGRESS: log still growing |  |
| intel2 | dpkit-svc_lo_dsdv_svc_rs__t5-448347 | svc_lo_dsdv_svc_rs__t5 | stage_odb_cap | 6.8 | last meaningful line 0.0 h ago (405/405 lines) | PROGRESS: log still growing |  |
