# hnx_vms_bank_safe4: P3 VM bank, safe3 plus face-root pin flops grouped beside their face clock entry

Lane HNX-UNITS/VM, 2026-10-20, branch `claude/hnx-vm-safe4-1020`. This is a critical fork of hfd_vms_bank, so it is REPORT ONLY:
no REVIEW.json and no submit_exact. The coordinator reviews the gate PNGs.

## Why
- safe2 (Codex, 10-19): the cross-clock macro->reg paths through the direct SRAM entries failed. safe3 fixed them by putting the
  SRAM clock pins on the core clk root (no direct entries).
- safe3 / safe3b gates 1-3 (10-20): CTS FAIL on root clk_e only. Pin-flop spread was 89.6 / 85.2 / 102.4 / 89.6 ps TT across
  four clustering variants. The placed sinks show the cause (gate3 3_place.odb):
  - clk_e: 95% at x >= 348, with a 3% tail to x 127 (rr1 / eg output registers pulled by timing-driven GPL);
  - clk_w: spread over x 2..459.
  The face tree then covers a 21.6 um x ~350 um strip with a far tail. No CTS option fixes that.

## Change (placement only; RTL, netlist, cycles and schedule are identical to safe3 @eac29e067)
`physical/hbm_next/vm/hnx_vms_bank_safe4_face_window.tcl` is the PRE_DETAIL_PLACE hook. After GPL and resize, it moves every
clk_e / clk_w sink that lies outside its 125 um face window (the band end beside its face clock pin) onto the window edge, at
the same y. DPL then legalises it. The N / S roots are centre-fed and already pass (28-69 ps), so they are untouched.
Dry run on the gate3 3_4 odb, with DPL and check_placement clean: 58 clk_e and 470 clk_w sinks moved. Result: clk_e x 346..472,
clk_w x 2..138.

## SAFE-DESIGN checklist
| # | item | result |
|---|---|---|
| 1 | pins registered, 2-stage reset landing | PASS (RTL pin registers on the face clocks; reset_landing 2) |
| 2 | reach <= 405 um | PASS by geometry: face window to the farthest SRAM pin face <= ~390 um (band end to the opposite macro column); the gate measures it |
| 3 | fanout <= 32 | PASS: pre-gate native census max 29 (safe3 run 2, eac29e067; RTL unchanged); the census also runs in-flow at the floorplan |
| 4 | depth <= 600 ps | PASS: textbook depth 408.4 ps |
| 5 | storage > 2 kb in SRAM | PASS: four 1024x256 SRAMs, no flop arrays |
| 6 | lattice / band / util / aspect | PASS: 2x2 SRAMs on the 43.2 lattice, one full-width band y129.6..151.2, aspect 1.69, fill 40% (WARN, macro-bound) |
| 7 | clock | FIXED here: the face-root pin flops sit beside their entry. SRAMs are on the clk root (safe3). io_hold_margin 0.03 |
| 8 | static schedule | PASS: no cycle added (reset release +2, priced at reset only) |

Bench: RTL is identical to safe3 (eac29e067), whose bench passed (HNX_VM_BENCH PASS 2/2 on Verilator 5.050, mutants FAIL 3/3);
no new bench is owed.
