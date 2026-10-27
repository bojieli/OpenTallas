# QC-SU-SRAMHALO (2026-10-27): SRAM pin-column exclusion halo, QC SU cores (prog L2 first, BTAB r8/r9 same flag)

**Problem (CHECKED).** claude/qc-su-prog-l2-1026@7b065a34bb prog L2 DRT stuck at 55 markers after 51 iterations (drt_l2_iter50_drc.rpt).
- Breakdown: 27 Short, 15 Lef58EolKeepOut, 5 Metal Spacing, 4 CutSpacingTable, 3 SpacingEndOfLine, 1 Cut Short.
- By layer: M3 28, M4 12, M5 9, V3 4, M2 1, V4 1.
- Window: x263.317-269.964, y121.008-128.155. That is the E pin-column edge, at the top, of SRAM band 2 (ot_sram_1r1w_256x256_m2_r2c2, MY, E edge x=263.544, top y=127.464).
- Nets: 42 markers involve u_twd0 signal nets, 4 are shorts against the SRAM M4 OBS, 9 other; none are clock.
- Cause: about 410 M4 pins per side edge at 0.096 pitch (10.4 pins/um). macro_pin_flops anchors a u_twd0 DFF/INV wall at x268-271, just outside MACRO_ROWS_HALO 4.32 and in front of the column. The halo does not cover the corner above the macro top, so cells sit there too.
- Render: prog_l2_hotspot.png (dump_win.py).
- BTAB r4 showed the same pattern.

**Base/L1.** No routed MIF0 base/L1 exists. prog_m0/m0_r3 reached GRT only, on the same 3_place, so the same hotspot geometry is expected. The signed prog_s8b used a different floorplan (R0, 28 um gaps) and routed with DRC 0.

**Fix: one structural rule in the shared generator, opt-in through recipe key `sram_pincol_halo`.**
1. `gen_core_kit_qc.pincol_halo_strips`, plan-computed from the LEF:
   - Each dense signal-pin column (at least 2 pins/um) gets a hard std-cell placement-blockage strip.
   - Strip depth = rows halo + rho·turn·p_v/fill, where turn = rows halo, p_v = M3 pitch for W/E edges (M4 for N/S), and fill = 0.6. The depth is rounded up to the site grid.
   - The strip runs along the column and extends by the same depth past both column ends, which covers the corners.
   - The blockage rects leave out the fixed TAPCELL endcap column at the row ends. Covering it fails check_placement (DPL-0004 on try 1).
   - OT_MPF_HALO_UM is set to the depth, so the landing flops sit behind the strip.
   - Outputs: sram_pincol_halo.json and the appended macro_place.tcl block.
2. `physical/common_flow/sram_pincol_keepoff.tcl` (shared GRT hook), chained by the generator: M2-M5 L-box routing obstructions at the S/N corners of every pin-carrying macro face. It generalizes BTAB r5 pre_grt_r5.tcl (GEOM-REVIEW-7 PASS; BTAB r5 DRT 0 at it11).
3. `pch_resite_spec.py`: moves mscts spec tree cells out of the strips, to the nearest legal site, sizing unchanged. It doubles as the gate (`--check`). On prog L2 it moved 15 cells, max move 3.942 um; the effect on latency is UNCHECKED.

prog L2 numbers: depth 7.074 um; 8 strips (E x263.544-270.618, W x83.646-90.72).

**Run.** kit epyc2:/srv/opentallas-scratch2/claude/qc-su-prog-l2-1026/kit_l2h (chain_halo.sh) keeps the GRT clock recipe. Results UNCHECKED until collected.
