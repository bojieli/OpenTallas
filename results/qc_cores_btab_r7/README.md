# QC-CORES-1 btab_m0_r7 (qfd_dv_s8x_btab, 12 copies), 2026-10-27

Base: claude/qc-su-btab-r5-1026@9a9b3382b8 (r5 kit: same MIF0 synth, floorplan, SRAM sites, M2-M5 SRAM-corner keep-offs, leg keep-off planner, k=6 --chain --straight L3). Kit: intel1:/srv/opentallas-scratch2/claude/qccores1-btab-1027/btab_m0_r7 (nickname kq_qfd_dv_s8x_btab_mif0r7).

## Change 1: read-mux bounded-density grid (GEOM-REVIEW-7 condition)
- kit/pre_gpl_r7.tcl selects the same 512 members as r5: 256 AO22 (bank 0/1) and 256 AO221 (bank 2/3 + AO22, driving the E output register at x ~347).
- r5 put all 512 in one inclusive region; GPL packed them into x 252-258 (hot band, 155/167 DRT violations at iteration 5).
- r7 uses 64 inclusive regions: stage A over x 255-293, stage B over x 302-340, 4 columns 6.48 um wide on a 9.72 pitch, 8 equal-count bands per stage, ordered by pin-median target y. The regions are released before DPL (pre_dpl_r7.tcl).
- Measured on the r7 3_place (CHECKED, sweep/mux_r7_3place.tsv vs mux_r5_3place.tsv):
  - AO22: x 254.1-284.5 in 4 columns (r5: x 253.8-256.7).
  - AO221: x 300.9-331.5, 64 per 10-um column (r5: x 254.0-256.6).
  - Caveat: AO221 sits at y 141-167, above the output registers (y 104-154), because its target is the median of its bank 2/3 flops and its output.

## Change 2 (attempted): equal-load islands (MODEL-REFIT-3 RCX island-size shift)
- su_tree_uf_ls_r7.py adds OT_R7_BALANCE / OT_R7_BAND: sinks are assigned to islands with equal counts, or within a band, by maze distance, and the islands are re-sited.
- On this geometry every balanced variant FAILS P_asbuilt (plan model, UNCHECKED):

| variant | as-built TT window | as-built TT mean |
|---|---|---|
| k6 exact | 53.4 | 267 |
| k8 exact | 53.2 | 286 |
| k6 band 1.3 | 45.1 | 262 |
| k7 exact | 43.2 | 310 |
| k7 band 1.15 | 33.0 | 294 |

- k6 band 1.15, k7 band 1.3 and k8 bands 1.15/1.3 hit the 1700 s timeout in the fix-up loop.
- Cause, read from the leaf predictions: equal counts force non-compact islands. A few leaves span two sink clusters, and because the planner uses one length per level, T3 rises from 28.6 um to 52-80 um and every path pays for it.
- Equal island load needs a planner change: a per-island level length, or islands drawn from the pin-flop column structure. It is not a reassignment.

## Built plan: Voronoi (OT_R7_BALANCE=0, = the r5 planner) on the r7 placement
- plan/btab_r7_k6_vor_L3: all gates PASS.
  - Islands [844, 357, 631, 500, 314, 796].
  - As-built pred TT 254.08 w13.33, FF early 188.4 w13.43 (plan model, UNCHECKED). Per COORD, the predictor reads ~15 ps high on TT.
  - The island-size spread remains, so the RCX window risk is still open.
- Spec: kit/mscts_spec_r7.tcl = gate.asbuilt.tcl, sha256 3110cb43...
- Leg vs SRAM clock-pin column check (CHECKED, recomputed from edge_paths_um):
  - 0 of 88 legs enter x 224.42-239.54 over the macro rows +-4.32.
  - Inside the widened keep-off (+4.32): 2.38 um in total over 3 edges (Q0, Q5B2, Q5B2L3), boundary touches.
  - G5: 0 nodes in pin columns, 0 legs across SRAM.
- Render viewed: plan/btab_r7_k6_vor_plan_place.png.
