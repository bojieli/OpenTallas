# smh_xs_ring_c32k_1019 -- SAFE variant B-km (compact + regional roots) of smh_xs (H.STA.BLK.14.1), LH-SMATT/XS 10-19

Predecessor rg2 terminal FAIL (see smh_xs_ring_kmr_1019/README.md): 432x345.6 at 28% fill, one root over 20.5k sinks,
boundary spread 149.5 / 136.4 ps, TT ring read address -80 ps. Variant B removes the cause (a sparse, oversize outline with
the register mass far from the clock pin) by a COMPACT rebuild:
* OT_SMH_XSRING32: the 4-slot ring is 7 x ot_sram_1r1w_32x128_m1 (51.4 x 20.8 um, 7,483 um2) instead of 4 x 128x256
  (15,553 um2); same registered-read/write semantics, 5-bit address {3'b0, slot}.
* Floorplan 388.8 x 216 (83,981 um2, -44% vs rg2; aspect 1.8): x store = one abutted N-S stack of 4 x 128x256 at x 216,
  y 23.76..187.92 (pins W/E only, gap 0); ring = two columns at x 43.2 / 129.6, y 43.2 / 86.4 / 129.6 (/ 172.8), all ring
  origins on the 43.2 lattice, 22.4 um N-S gaps, 34.8 um W-E channels; W face (rl1 landing) -> ring -> N face (o_iw);
  S face (bk1 beat) -> rotation band (S strip + 78 um E region) -> x store -> N face (o_ix).
* OT_SMH_RING_LOCAL_ADDR / _WADDR / _RST2 as variant A (macro-local kept posedge address captures, own ring reset relay).
* Clock: 16 regional roots by 2-D k-means (physical/common_flow/clock_split_km.tcl, ~1,290 sinks each) under a
  latency-balanced CTS top tree; parallel fallback of the single-root kit smh_xs_ring_c32_1019 (same RTL + geometry).

Region numbers: K = 16 placed k-means regions, ~1,290 sinks each (~20.6k total).

## SAFE 8-item checklist
1. Pins: PASS (RTL pin registers, OT_SMH_XSRST 2-stage face reset landing; faces N 1,624 pins 4.2/um, S 2,069 5.3/um,
   W 831 3.8/um, E 19).
2. Reach: PASS by construction (compact 388.8 x 216, address capture beside each macro); placed reach re-measured by the gate.
3. Fanout: FIXED (1 address flop set per macro, ring on its own relay so the leaf relay <= 32; strap tree <= 32 kept).
4. Depth: PASS, data logic unchanged; half-cycle address path removed.
5. Storage: PASS, SRAM ring (7 macros) + 4 x-store SRAMs, no flop delay line.
6. Floorplan: PASS. Ring macros on the 43.2 lattice; x-store stack origin x 216 on the lattice, y on the 2.16 row/track grid
   (an abutted stack needs pitch = 41.04); channels >= 20 um except the deliberate pin-free N-S abutment; full faces
   <= 6/um; fill (23,048 macro + 13,468 synth std) / 83,981 = 43% (owner band 40-60%; < 50% parent-kit warn because the
   S face needs >= 345.6 um + corners for 2,069 bk1 pins); one contiguous std-cell region (S strip, W strip, ring
   channels, 78 um E region, N band).
7. Clock: 16 regional roots beside the register mass; acceptance = gate pin-flop spread <= 80 TT+FF; io_hold_margin 0.03, hold 0.03.
8. Schedule: PASS, static, 0 added edges. Benches 5.050: vs legacy 5000 cyc PASS; vs rg2 ring 5000 cyc PASS + 34,118
   per-macro read/write address checks 0 mismatches; read/write-slot mutants FAIL. Logs results/rtl/smhxs_ring_1019/safe_ab/B_*.log.

Critical tile: no REVIEW.json / submit; gate PNGs go to lanes/COORD-REVIEW-QUEUE.md.
