# qfd_dv_s5_red -- SU reducer leaf (QW-SLICE6 / Q.STA.SLICE.2)

Top `qfd_dv_s5_red` (rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv): the qfd_dv_su8_entries reducer -- input registers rd_* (lane
results, lane-0 class / address) + `ot_hdc_vreduce` SW 8 LV 4 (R-ARITH: 8-element chunks summed sequentially, pairwise
tree, time levels).  One master per slice, at the SU block centre beside suvm: lane result ports N, outputs S (sc, ctl).

## SAFE-DESIGN checklist (owner 10-19)
1. Pins: flow pin registers on every data input / output (recipe 4, pin_regs on: +1 in, +1 out); rst_n lands in 2
   registered stages in the RTL (qfd_dv_s5_rst2) then the su8 control reset register rc.
2. Reach: one tile <= ~200 um. PASS.
3. Fanout: per-lane datapaths, no broadcast > 32 except the valid lines (repair_design; gate high_fanout judges).
4. Depth: LAT-3 qadd / qmul (ot_hdc_fastfp), one op per stage. gate --cts path classes.
5. Storage: no indexed array; BUT the lane-skew data delay lines u_xd (32 b, depth 3..18), u_ct (26 b x 21), u_sqd
   (283 b x 3), the level tag lines and vred_op's u_m are flop shift chains (~3.4 kb total, every one < 2 kb): item 5
   asks delay lines >= 3 deep as rings.  Main keeps the closed-family shift lines (as qfd_dv_slice2 today); the
   PARALLEL FALLBACK qfd_dv_s5_redb (+define+OT_S5_RED_RING, rtl/qwen_dv/s5/qfd_dv_s5_vreduce_rb.sv) builds every data
   line >= 3 deep as a flop ring (qfd_dv_lane_h_safe2's closed ring structure), cycle-exact.  The 1-bit valid taps stay
   lines (every tap is read).
6. Floorplan: no macros; square outline from synthesis area at 40-60 % util.
7. Clock: one centre-fed root; spread <= 80 ps TT/FF (gate); io_hold_margin 0.03.
8. Schedule: static; pin registers +1 in / +1 out: the reducer result reaches sc / VM 2 edges later, SU idle sees
   rd_v / busy 2 later (status) -> parent lp record / compiler NOTICE.

## Benches
eq lockstep + b2 (FACE 3); mutant OT_S5_RED_MUT (SUM classed as MAX) must FAIL (witness .../witness/red_mut.log).
