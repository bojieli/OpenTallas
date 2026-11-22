# FAM-S81-SERDES-R7 J8 PHY/ENG rows (for S81-J6-ASSEMBLY-R5)
Base: J7eL6 plan a6771d121e95 + the 6 serdes START ops (lanes/handoff/FAM-S81-SERDES-R6-j8-serdes-start-rows.json, no t16 writer).
Apply in order (JSON-pointer ops with expected_old): phy_eng_pair_delta.json (29), eng_view_lib_delta.measured.json (2), eng_ft_regs_fix.json (2), phy_seam_shift.json (7).
View files the eng lib ops name: epyc9 /srv/opentallas-scratch2/claude/fam-s81-serdes-r7/engrr_vJ_eco1_1108/dsdv_eng_rr_e -> physical/die_plan/s81/cores/views/engrr_vJ_eco1_1108/dsdv_eng_rr_e (20 MB, also intel2 path in the gate script).
Gate (epyc9 fam-s81-serdes-r7/gates/J8p3, tools rt 404887a342b0, tree candJ8s): result plan sha 9fe026d10b26; strict bind RC 0, LATCHECK 873/873 PASS, PRE PASS 0 findings, G0 vs J7eL6 base: 0 new errors, 0 fixed (9 inherited).
Why the 2 fix deltas: pair delta moved eng ft bit_sites but not regs_um (G0 hop 924 um / 505 um); seam shift -48.384 um clears the phy__t1 private kit GRT-0116 NE-corner hotspot (dfi_i0 E window entered the 44 um N std strip above the HBM PHY macro). phy__t1 kit rerun on J8p3 to confirm GRT.

## 06:1x PENDING 5th delta: phy_macro_grid.json (1 op, phy__t1 HBM PHY macro x 77.76 -> 77.748)
J8p3 phy__t1 kit: GRT overflow 225 -> 42 gcells but still GRT-0116 at the NE corner (M5 vertical at the macro top edge). The macro M5 pins sat 12 nm off the M5 track grid. Proof kit on J8p4 (plan da9f7b436c25) running (spec s81_phy__t1_1122061135). Take this op only if that kit clears GRT; R7 posts the verdict.
