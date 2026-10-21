# s81sl_xg5fb -- structural floorplan successor of s81sl_xg5 (S81-XG5FP-1021, S81.STA.LEAF.5, 10-21)

Same RTL / pins / clock / census fixes as s81sl_xg5 @ xg5c e1c24fa0a; only the macro floorplan and outline change.

```
S81-XG5FP (10-21, LEAD-S81): STRUCTURAL floorplan successor of s81sl_xg5 after both xg5/xg5k routes crashed at
3_5 DPL-0038 (util 121%): 3_3 GPL routability never converged (36-47% of gcells overflowed, weighted congestion 1.6-2.0,
8 inflation rounds), then repair_design inserted 965k buffers for 231k slew violations.
Cause: the 37 macros obstruct M1-M4 and the tile routes M2-M5, so NO horizontal (M2/M4) wire can cross a macro. The xg5
plan stacked 8 SRAMs per bank column (y 108-437) and all 7 ROMs in one column (y 64.8-505.6 = 441 of 561.6 um): at the
ROM column only 121 um of height is free for W<->E wires (~1.4k M2+M4 tracks) while the ring needs ri_w->ro_e +
ri_e->ro_w (2 x 1,104 b) + nx (346 b) + the 3,072-b gather port + 6,144 SRAM read bits across it.  SRAM pin faces
(W/E, 412 pins on 41 um = 10/um, 3.3k per 8-stack face) face 34.8-43 um channels, the W one shared with 2,554 tile pins.
Fix (xg5fb): no column stacks more than 4 SRAMs (164 um) or 2+2 ROMs; every column is split into a S stack and a N
stack with a full-width macro-free centre band, so >= 420 um of height is free for W<->E routing at every x, and
8-stack pin faces become 4-stack faces (1.65k pins) (xg5 channels, half the pins per face); W pin face no longer abuts an SRAM face.
fb: 648 x 864 (same x columns as xg5: banks 43.2 / 216 / 432, ROM 345.6, exp 561.6); mac 0-3 S y 86.4, mac 4-7 N
y 611.28; ROMs 3 S (y 86.4) + 4 N (y 524.88); exp SRAMs 3 S + 3 N.
RTL, pins (faces/order), clock K=16, census fixes = xg5c e1c24fa0a unchanged.


```

## SAFE-DESIGN checklist delta vs s81sl_xg5 (items 1-5, 7, 8 unchanged = xg5 README below)
6 Floorplan: FIXED -- macros on the track lattice (offtrack 0, x on 43.2 / 21.6 grid as xg5), stacks <= 4 SRAMs / 2 ROMs per column
  half, full-width macro-free centre band (>= 420 um free height for W<->E wires at every x), 34.8-78 um channels (xg5 x map) between
  4-stack pin faces, W/E pin faces >= 43 um from any macro face; fill ~26% recorded as routing/perimeter-bound.
2 Reach: ring W->E crossing 648.0 um over pin flop -> RELAY flop -> out flop (2 hops <= 405 um each).

---

# s81sl_xg5 -- S81 slice gather sub-leaf, rs + xs4 re-merged (S81-TILES-E, S81.STA.LEAF.5, 10-20)

Top `ot_s81sl_xg5` (rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xg5.sv) = ot_s81sl_rs (S81-XG4) + ot_s81sl_xs4 (S81-XG4XS + XG5 census
fixes) + a 1-edge issuer relay. Generator results/rtl/s81_slice_1019/xg5/gen_xg5_spec.py (base: the original s81sl_xg spec).
Decision: LEAD9-S81 14:30 (owner 09:09 REPARTITION rule for pin-bound tiles): the split rs4 leaf had 13,750 signal pins in
864 x 518.4 (util 2.6%, minimum outline at <= 6 pins/um ~3.7%) and placement TT -313.8 ps; merged, the 3 x 1,031-b gather
port is internal and the tile returns to the original xg slot.

## XG5 xs4 native census fixes (xs4a/b gates: 87 drivers > 32, max 64)
weq 4 x 25 b -> 9 x 11 b chunks per calendar row; issuer we 2 -> 4 copies (<= 16 b); table groups: kept wps copy of wp for the
source writes; ctl bv 36 -> 69 copies (16 lane bits each, 4 OR-source copies, 2 extra reset leaves); ctl hold-in-reset payload
enables split to <= 16 b with 24 extra same-depth leaves rst_x; 192-line arrival lookup decoded through a kept 2-level
predecode (ot_s81sl_xs4_pdec: 12 x 16 one-hots); calendar due / fetch terms from kept per-consumer instances
(ot_s81sl_xs4_due / _fetch; all three listed in synth_keep_modules, non-parameterised). xs4_equiv on the fixed source:
base PASS, 6 mutants FAIL as expected (witnesses results/rtl/s81_slice_1019/xg5/xs4_equiv_*.log).

## XG5c census fixes (DRIVE-S81-XG 10-20; xg5b gate census: 3 roots > 32, max 57, all in ot_s81sl_xs4_cal)
pok[2] base_q + nrows enables (36) -> pq 4 -> 6 kept copies (pok[4] nrows, pok[5] consume_index); due[4] last_ts mux (57)
-> kept u_due4l0 / u_due4l1 (12 b each); due5 consume_index (37) -> kept u_due5c. Same function per copy (value-preserving).
Fallback kit s81sl_xg5k = same RTL / outline / macros, clock k-means K=24.

## SAFE-DESIGN checklist (owner 10-19) + pre-gate native census
1 Pins: PASS -- source-registered (rs pin flops / relay outputs; issuer relay + xs4 capture; xs4 output flops); reset_landing 2.
2 Reach: gather port now internal (rs relay flop -> xs4 capture flop, one registered hop each side); outline 648 x 561.6.
3 Fanout: rs4 mapped census PASS max 32 (S81-XG4); xs4 87 roots fixed structurally (above); merged census xg5b 3 > 32 fixed (XG5c); the gate runs the mapped census
  on the merged netlist before floorplan.
4 Depth: rs / xs4 cones unchanged (kept copies only).
5 Storage: 24 x 128x256 x-buffer SRAMs, 7 ROMs, 6 exponent SRAMs (xs4).
6 Floorplan: 37 macros, pins on L/R faces only -> deliberate N-S abutted stacks (gap 0.024, bare faces; x on the 43.2 lattice);
  channels 34.8-78 um between columns, 108 um S / N face strips; util ~40% (std est. 30k + macros 115.8k in 363.9k);
  pins on full faces <= 5.8/um.
7 Clock: k-means regional split K=16 (clock_split_km.tcl); spread judged by the --cts gate (TT/FF <= 80); io_hold 0.03.
8 Schedule: ring outputs = main xg + 1 edge per stop; x path (xw_v / xw_d / fault) = main xg + 2 edges (gather and issuer
  both +1 into xs4, xs4 +1) -> MU.S81.CAL. Lockstep bench tools/s81_slice/xg5_bench.sh (production PQ slot at the xg ring
  pins, compare offset +2; rs + xs4 mutants inside must FAIL).
