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

## SAFE-DESIGN checklist (owner 10-19) + pre-gate native census
1 Pins: PASS -- source-registered (rs pin flops / relay outputs; issuer relay + xs4 capture; xs4 output flops); reset_landing 2.
2 Reach: gather port now internal (rs relay flop -> xs4 capture flop, one registered hop each side); outline 648 x 561.6.
3 Fanout: rs4 mapped census PASS max 32 (S81-XG4); xs4 87 roots fixed structurally (above); the gate runs the mapped census
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
