# INFRA-FIRST-QC-R15: VSS-locked per-level lanes (2026-10-27 00:00 PDT) -- all numbers UNCHECKED

Solver: tools/die_plan/qc_clk_mesh3.py --feed periodic --islands type --lanes vss (opt-in; default path unchanged, 6/6 tests PASS).
- every tree level has its own 8.64 um lane on the M8 VSS stripes (8.64k); child node one lane past parent; repeaters on driving node lane; M9 drop joins lanes; column y-trees on M9 x-lanes
- slot rows VSS-locked per type frame; class key = nearest VSS slot row; vertical-leg repeaters on die 8.64k grid (mirror-safe)
- leaves 25.92 um (3 lanes) off the local root; leaf T = plan-computed downstream column-tree delay (identical per-type tap sizing)
- centre row split at the seam (YC +- 8.64), one driver per half
Results (pkg epyc2:/srv/opentallas-scratch2/claude/qc-mesh-r12/pkg out/r15, out/r15x):
- identity 74/74 types (360 inst) IDENTICAL incl. orientation, 0 identity violations; vss_phase 4619 on VSS, 0 off-phase
- tap skew nominal TT 40.66 / FF 35.85 ps (R13 48.5/39.6); MC 13 samples TT 180-325, FF 152-281 ps (die-wide max-min, not related pair)
- related-pair seam (997 pairs): TT setup 531.25, FF hold zero-logic -119.04 (HB4 needed, 997 neg); kit-contract FF hold plain +13.20 PASS, F4G RP1+VMR core view -4.64 FAIL (need 44.64 > 40 W; 7 neg; worst sl_W0_su_c->c_W0_bn_00). su_c taps ~18 ps early vs R13 (lane geometry, not the leaf re-balance: diag QC_R15_NO_LEAF_T gives same)
- plan delta 17.28 um centre channel (plan_delta/): die H 26282.88, 182 partitions up, 49 crossing channels / 316 seam ports, io window moved: G0 PASS 0 err 111 warn, worst cut 0.2159, worst seg 0.5134 (= baseline)
- full-die dry build (exact_reserve): 176 plan errors (no_pin_stack 157, reserve_overflow 13, no_clock_track 6); ~92 in the YC channel x-tree (folds on one lane: 17.28 um gives 3 lanes, no-fold needs ~5 = 34.56-43.2 um), 84 = column-tree reps (c_W*/E*_t/b, M7 riser outside island window)
- physical build / DRC / RCX / RCX STA NOT run (requires dry 0/0)
Render: render/r15_lanes.png (viewed).
