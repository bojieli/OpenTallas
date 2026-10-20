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
(clk + the four face roots clk_n/s/e/w, unchanged). The four SRAMs are bound as raw-memory sinks of root clk
(soft_root_macro_bindings, exact instance/master/pin/root). Without that binding, census run 2 (ot-epyc9
hnx_vms_bank_safe3-20261020-064122) stopped at CTS with "CTS source clk must reach only standard-cell clock pins". RTL: clk_macro0..3 ports removed from hnx_vms_bank_q0_faces / core / body
(the bench TB drove them all from clk already). Pins: the four clk_macro pins removed (hnx_vms_bank_safe3_pins.tcl).
Geometry, macro origins, band, data RTL and latency: unchanged from safe2.

Die impact (next-release P3 only): the die frame no longer delivers clk_macro0..3 to the VM bank. The macros take their
phase from the bank's own clk tree, so the DIE VM slot loses 4 clock entries.

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS. Every data input has an explicit RTL face register (faces wrapper, kept); rst_n gets 2-stage reset landing.
2 Reach: PASS by plan. Outline 475.2 x 280.8; every face and macro edge is < 260 um from the central band. Gate textbook reach 0.0 um (safe2).
3 Fanout: FIXED. The first census (ot-epyc7 hnx_vms_bank_safe3-20261020-063231) FAILED: max 624 loads, 28 drivers. safe2 had the
  same RTL; the census did not exist when it ran. Fix eac29e067 uses KEPT identical copies, same edges:
  - c_sel (624 loads): 27 copies per bit, 12 bits each.
  - rr_d / pr_d enables d_v&&d_p==f (513 / 259 loads): registered d_ren / d_pen copies, 22 / 23 per face.
  - valid-bit payload masks (277..282) and the pq mask (276): 10 valid pin-register copies per source in the faces wrapper, <= 29 bits each.
  - rn (95 loads): 11 relay copies in fixed groups of <= 25.
  - rslot_d (82 / 36 loads): 4 copies.
  - m_mC (39 loads): opt_merge had folded it with m_mB; the masks are now kept, in half-word copies.
  Census run 2: PASS, max 29 loads (limit 32). Std area 3711 -> 3823 um2.
4 Depth: PASS. safe2 textbook depth 408.4 ps (< 600). The 3:1 capture mux is after the c_* capture registers; no in->out path.
5 Storage: PASS. All VM storage is in the four 1024x256 SRAM macros; no runtime-indexed flop arrays.
6 Floorplan: PASS. Macro origins on the 43.2 lattice (2x2); one full-width std band y129.6..151.2; macro pin face 5.89/um;
  external faces <= 4.5/um; aspect 1.69; fill 40% (WARN: macro-dominated, std band 36%).
7 Clock: FIXED (this kit). The macros are on the same root as their launch/capture registers; face roots are centre-fed beside the band;
  pin-flop spread <= 80 (safe2 TT/FF 0.0); io_hold_margin 0.03.
8 Schedule: PASS. Static, no credits or backpressure; no data cycle added. Reset release +2 edges (priced at reset only).

PRE-GATE NATIVE CENSUS: PASS, mapped dynamic loads max 29 <= 32, reset included (census run 2 at eac29e067). Census run 2
also gave: textbook PASS (depth 408.4 ps, reach 0.0 um), pin geometry PASS (3929 pins), no tied ports, storage all in SRAM.
Bench (Verilator 5.050, fleet): HNX_VM_BENCH PASS 2/2 (lockstep bit-identical to d4g, upper-half scoreboard) and
MUTANTS FAIL-AS-REQUIRED 3/3, on both 105811946 (clock change) and eac29e067 (census fixes).

REPORT ONLY: critical fork of hfd_vms_bank. No REVIEW.json or submit_exact; coordinator reviews gate PNGs.

## Gate 1 (--cts, 10-20 06:52, ot-epyc9 hnx_vms_bank_safe3-20261020-065241): CTS FAIL
Root clk_e (E face root) had a pin-flop spread of 89.6 ps TT, over the 80 limit. The H-tree path depth was 4-5 with size 16 /
diameter 30 clustering (safe2 had 22 ps on the same root). The other roots passed: clk 0.0 (SRAMs as raw sinks, insertion
~310 ps), clk_n 69.4, clk_s 39.6. This is a clock-tree build fix, not a timing relaxation, run as two parallel variants:
- safe3 uses automatic sink clustering with -balance_levels.
- safe3b uses size 8 / diameter 20 clustering with -balance_levels.
Bind whichever passes the checklist first.
