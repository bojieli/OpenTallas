# hbm_su_qcore_r15c_1021 -- qcore r13c RTL, ALT (port/slot-identical): r14a N stack at 280.8^2 exact, macros x86.4, only the real pin-face channel added (HBM-COLLECT10/QCORE, 10-21)

RTL unchanged from r13c (ot_hbm_su_static_qcore_r13 @8ea344306; native census PASS max 32; benches 5.050 PASS / mutants FAIL,
results/rtl/hbm_qcore9_1020).

Why: route hbm_su_qcore_r14a_1021-q14a-a6e06749c EARLY_FAIL_CONGESTION (GRT-0116). First GRT pass overflow 0; after post-GRT
repair_design (~800 buffers) overflow 7 (M2 1 / M3 3 / M4 3). Every marker (congestion-20.rpt) sits in cap-0 gcells at the SRAM E pin
face, x175.6-181.3 / y174-222 (u_red.mb + low u_red.ma), nets u_ot_pr_core.raw5_s[*] / g_sec[*] (sector read data). r14b gate:
same face (x177.8-180.7, y34.8-100.3), overflow 6.
Root cause (flow): the kit's "10.8-um pin-face halo" only set MACRO_PLACE_HALO, which feeds rtl_macro_placer (unused: fixed
placement). The row cut that keeps std cells away from a macro is MACRO_ROWS_HALO_X/Y (ASAP7 default 2 x 2): the r14a
2_3_floorplan_tapcell.log prints "Halo Around Macro : 2 2". Std cells sat 2 um from the 410 M4 pins per 41-um SRAM face (10/um).
Fix: MACRO_ROWS_HALO_X 21.6 / MACRO_ROWS_HALO_Y 5.4 (orfs_vars) = a real cell-free pin-escape channel on both SRAM pin faces
(the abutted N-S faces carry no pins). Halo also mirrored in route.macro_halo_x_um 21.6.

SAFE-DESIGN checklist (8 points; also in lanes/HBM-COLLECT10.md):
1 Pins: PASS -- tile faces <= 3.6 pins/um (W), all outputs flops, inputs captured at k (pin_regs opt-out reason in spec: an added
  edge would break the fixed n+1 commit / n+3 read / E+11 calendar); reset lands 2 stages, 24 copies.
2 Reach: PASS -- tile <= 302.4 um; no single-cycle wire > 405 um (r14a textbook reach 201 um).
3 Fanout: PASS -- native census max 32 (r13c netlist; RTL unchanged; gate re-runs the census).
4 Depth: PASS (guidance WARN) -- worst estimated stage pretree l1 ~640 ps / 17 levels; r14a gate reg->reg +15.9 ps at TT placement.
5 Storage: WAIVED (rule freeze, unchanged since r9) -- 8 kb RF as 8 sector modules of 1 kb flops; reduction lines in 2 SRAM macros.
6 Floorplan: FIXED -- 2 SRAMs one abutted N-S bank at a pin-free edge, on the lattice; REAL 21.6-um pin-face channels; one
  contiguous std-cell band; total fill ~0.32-0.37 (below the 40% guidance on purpose: the area is set by the SRAM pin faces /
  E-W routing, measured, not by cell area); PD 0.38; aspect <= 1.08.
7 Clock: single centre-N root clk_ctl; r14a measured TT 63.6 / FF 59.9 pin-flop spread <= 80; io_hold_margin 0.03.
8 Schedule: static; 0 edges added (RTL unchanged); port-identical to r13c/r14a.
