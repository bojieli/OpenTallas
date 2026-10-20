# P3 VM safe3 (HNX-UNITS/VM, 2026-10-20): SRAMs on the core clk root

Predecessor safe2 (96935a9b8, gate /home/ubuntu/artifacts/hnx/vm_safe2/gate.log): GRT overflow 0, TT/FF pin spread 0,
reg->reg +34.8 ps, but PRE_ROUTE_GATE FAIL on two cross_clock setup groups:
- ot_entry_6 (clk_macro1, SRAM u_b) -> ot_entry_0 (clk): 23 endpoints, worst -10.9 ps, u_b/rd_out[30] -> c_b[30]
- ot_entry_8 (clk_macro3, SRAM u_a1) -> ot_entry_0 (clk): 1 endpoint, -1.1 ps, u_a1/rd_out[172] -> c_a1[172]

Classification: each SRAM clk pin was a raw direct die entry (clk_macro0..3, `raw_liberty_clock_pin`, no CTS, TT
arrival ~10 ps) and the capture registers c_* (and the m_* launch registers on the write/address side) are on
the core clk CTS root (TT 259..300 ps). The sign-off SDC aligns every entry to the same phase with source latency, but it
times each distinct-entry pair with the die inter-entry reserve (OT_IO_SKEW_INTER 150 ps) instead of the in-root 60 ps.
The rd_out -> c_* hop is a direct macro -> flop wire with no logic, but SRAM clk->rd_out is ~545-610 ps TT, so
833 - 150 - clk->Q - wire - setup is just below zero. The macro sits on a different clock root from the registers it
talks to, so the path is not short.

Structural fix (no false path, multicycle, margin or uncertainty change): remove the four direct macro entries. All four
SRAM clk pins (u_a, u_b, u_c, u_a1) are now driven by the core `clk`. That is the same CTS root, balanced with the m_*
launch and c_* capture registers, so rd_out -> c_* and m_* -> SRAM are in-root hops (60 ps). Spec clock = multiple_cts_roots
(clk + the four face roots clk_n/s/e/w, unchanged). RTL: clk_macro0..3 ports removed from hnx_vms_bank_q0_faces / core / body
(the bench TB drove them all from clk already). Pins: the four clk_macro pins removed (hnx_vms_bank_safe3_pins.tcl).
Geometry, macro origins, band, data RTL and latency: unchanged from safe2.

Die impact (next-release P3 only): the die frame no longer delivers clk_macro0..3 to the VM bank. The macros take their
phase from the bank's own clk tree, so the DIE VM slot loses 4 clock entries.

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS. Every data input has an explicit RTL face register (faces wrapper, kept); rst_n gets 2-stage reset landing.
2 Reach: PASS by plan. Outline 475.2 x 280.8; every face and macro edge is < 260 um from the central band. Gate textbook reach 0.0 um (safe2).
3 Fanout: census below (mapped netlist, limit 32 incl. reset).
4 Depth: PASS. safe2 textbook depth 408.4 ps (< 600). The 3:1 capture mux is after the c_* capture registers; no in->out path.
5 Storage: PASS. All VM storage is in the four 1024x256 SRAM macros; no runtime-indexed flop arrays.
6 Floorplan: PASS. Macro origins on the 43.2 lattice (2x2); one full-width std band y129.6..151.2; macro pin face 5.89/um;
  external faces <= 4.5/um; aspect 1.69; fill 40% (WARN: macro-dominated, std band 36%).
7 Clock: FIXED (this kit). The macros are on the same root as their launch/capture registers; face roots are centre-fed beside the band;
  pin-flop spread <= 80 (safe2 TT/FF 0.0); io_hold_margin 0.03.
8 Schedule: PASS. Static, no credits or backpressure; no data cycle added. Reset release +2 edges (priced at reset only).

PRE-GATE NATIVE CENSUS: see the "Census" line (filled from the fleet synth run before the --cts gate).

REPORT ONLY: critical fork of hfd_vms_bank. No REVIEW.json or submit_exact; coordinator reviews gate PNGs.
