# HBM-CORE-LAT-R4 XCAL: ot_hbm_svc_sm_xcal_rel_t SRAM re-pack (COORD ruling R3 (2)), Tue Oct 27 01:38:03 PDT 2026
TRIAL kit (TRIAL-no-frozen-master-plan); placement only, NO CTS. Data intel2:/srv/opentallas-scratch2/claude/hbm-core-lat-r4-xcal.
- Outline 207.36^2 -> 241.92 x 224.64 (+26 % area). Why: 4 SRAMs (2x 174.744x70.488 program, 2x 94.824x41.064 tab) are 82 % of the
  207.36 core; every macro has ~370 pins on BOTH vertical edges, so a centre std band needs width (tab row: 8.64 outer strips + 17.7 centre
  pocket) and two ~6-um full-width bands (H-bars) between the tab row and the programs. No smaller pack keeps std cells on both edges of every SRAM.
- Pack (macro_place_r4.json, one per type): program_hi R0 (33.588,10.8), program_lo MX (33.588,143.1), tab_lo R0 (15.12,91.8), tab_hi MY (131.976,91.8).
  Std area: S/N face rows, W/E strips 27.1 um beside programs / 8.64 beside tabs, bands y 83.45-89.64 and 135.02-140.94, centre pocket x 112.10-129.82.
- In-core islands (slice_r4.json, identical for all 4 pin variants): ck_entry 8.64^2 at the centre (clk M5 pin 120.984,112.32 on the 0.048 lattice),
  ck_l1_s/n on the bands at x=120.96, ck_l2_sw/se/nw/ne at band x strip (17.28 / 224.64, 86.4 / 138.24). Placement blockages only (pushdown cells not yet instantiated).
- Pins: B2o tables stretched to the new outline (N/S x*1.1667, E/W y*1.0833, snapped 0.048) = TRIAL; the plan owner re-derives (pins/).
- Slot (slot_check_r4.json, vs planS2snap partitions + ft/internal-station regs + die_ft_bands): Q2 grow W+S, Q3 W+S, Q1 W: inside the partition,
  >=30.24 to edges/cores, no station reg inside. Q0: grow W puts bus:L77_o station column x=142.56 inside (plan delta: shift the column 34.56 W),
  grow E overlaps the q_spt0 NS die_ft_band (x>=380.16) by 12.96 -> plan-owner choice.
- Q0 kit (view d66b700ee2f0): sdc_lint PASS, face_guard 505/505 PASS, port_bind PASS, LEC EQUIVALENT 5593/5593 (CHECKED, kit_Q0/). Placed util 9.6 %.
  Sinks 3142 FF + 4 SRAM CK: W strip 1560, S band 837, E strip 283, pocket 236, N band 13 (Q0 pins on S+W faces).
- Tree plan (core_infra_htree --r6, fixed level-2 islands; sweep plan/sweep.txt, 60 candidates): chosen nb 6,4,5,1 leaf 4 smax 70:
  PLAN MODEL TT 297.9 window 25.2 / FF 243.7 window 24.5, path wire 337 um, 253 cells (UNCHECKED; the model ran 90-125 ps LOW vs measured on gq_issue/pc_ctrl_leaf).
  R3 207.36 pack: 1331.9 / 1122.1 window 240. Best free (no islands) 2244 m70: 370.3 w18.1.
- Renders: xcal_Q0_r4A_placed.png, xcal_Q0_r4A_plan.png (node->node straight lines; real edges follow strips/bands).
