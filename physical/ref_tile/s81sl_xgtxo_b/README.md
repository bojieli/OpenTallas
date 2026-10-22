# s81sl_xgtxo_b -- S81 end-slice u_xg combined master ot_s81sl_xgt_xo (FALLBACK; S81-FIX2/XG, 10-21)

Top `ot_s81sl_xgt_xo` (rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xgt_xo.sv), SAME PORTS as ot_s81sl_xg / ot_s81sl_xg_xo /
ot_s81sl_xgt (die binding = master swap of u_xg in the slice parents, no port or net change):
- u_r `ot_s81sl_rstopt_xo` = RG-FFN ot_s81sl_rstopt (00f45f497: kept one-hot DKS selects, ot_rst_relay leaves on control /
  valid only, datapath unreset) + RG-HEAD head XB egress (c2fa3f9b3 ot_s81sl_rstop_xo: s_0N -> ro_w, flagged XB beats, hops 1),
  merged semantically: the 3 egress sources (xl line-from-E delivered, xo own, xa V-assembled) are kept one-hot selects
  (pin-decoded for xl, next-state for xo / xa), one copy per <= 30 bits, fed by decode AND a kept split leaf.
- u_s `ot_s81sl_xs4` = the native-bounded x streamer of the xg5 lineage (claude/s81-xg5fp-1021 ab6b3f7b4, incl. XG5d rng/bad
  fix): main ot_s81sl_xs function + a K=1 capture stage on every input.  Main ot_s81sl_xs (inside xg / xg_xo / xgt) is the
  census failure of every xg gate (xs ctl net 4,050 loads; xs3 1,156 drivers > 32) and is NOT used.
Floorplan: 648 x 864 = the s81sl_xg5fb map (banks x 43.2 / 216 / 432, ROM 345.6, exp 561.6; mac 0-3 S y 86.4 / mac 4-7 N y 611.28; ROMs 3 S + 4 N; exp 3 S + 3 N): different macro arrangement, taller.  Kit generated from physical/ref_tile/s81sl_xgtxo_b/spec.json (results/rtl/s81_xgtxo_1021/scripts/gen_specs.py on the
s81sl_xg5fb spec; macro instance paths u_s.g_bank / g_mac / g_ex identical because u_s is the same xs4).
Replaces: s81sl_xgxo / s81sl_xgxo_b (FAILED: control net 4,050 loads, reset 2,517 loads; no ot_s81sl_xg view ever closed).

## Cycle delta vs ot_s81sl_xg_xo (-> MU.S81.CAL)
- ring path (ro_e / ro_w / vo / nx_* / dl_*, the s_0N head egress): +0 edges (rstopt and rstop_xo are both 0-edge).
- slice x path (issuer word is_d and gather beats -> frame word xw_v / xw_d): +1 edge (xs4 capture stage, uniform), i.e. frame
  word = production lane word + OFF - 3 (was OFF - 4).  Where: the slice x-chain issue in the stage calendar (one edge later
  per x stream start); the ring all-gather calendar and head egress are unchanged.
- fault: +1 edge (status only).

## Benches (Verilator 5.050, fleet ot-epyc5; logs results/rtl/s81_xgtxo_1021/bench)
- xgtxo_bench (tools/s81_slice/xgtxo_bench.sh): production static PQ slot lockstep at the xg RING PINS (W/E line beats, own
  4-fragment path, V 4-fragment path), x path compared at +1: 7 positive cases (L0/L2, near/far/rand, slices 0/3/5/8/9/14/15)
  PASS mismatches 0, ring own_line 20/20, stray 0; offm1 + muttiercol (rstopt) + mutbank/mutoff/mutwcopy/mutexp (xs4) FAIL as
  expected -> XGTXO_BENCH PASS.
- rstopt_xo (tools/s81_slice/rstopt_xo_bench.sh = the RG-HEAD rstop_xo bench, tb unchanged, master swapped): rstop_sid 16 stops
  144 checks PASS; rstop_xo 138 checks PASS, die ring R1 egress 80/80 exact (bad 0, other outward 0, gather 80 at every stop),
  R2 unflagged egress 0.  Mutants xooff / xoall / xonoflag FAIL rstop_xo, tiercol FAILs rstop_sid.
- xs4_equiv (main xs + 1 edge, 23 cases incl. in-flight reset + 10 fault injections) PASS; 6 xs4 mutants FAIL.

## SAFE-DESIGN checklist (owner 10-19) + PRE-GATE NATIVE CHECK
1 Pins: PASS -- source-registered (rstopt input flops / pin-decoded kept selects registered on the input edge; every ring output
  leaves a flop; is_v / is_d land in xs4 capture flops; xw / fault leave flops); reset_landing 2 stages; recipe pin_regs off
  (would add an unpriced ring-hop edge).
2 Reach: gather port (3 x 1,031 b) internal (rstopt_xo flop -> xs4 capture flop).  WAIVED-with-reason: the ring W->E crossing is
  one registered hop (input flop -> output flop, 0 added edges, as the original xg slot 648 um) over 648 um > 405 um planning
  reach (measured repeated reach 600-750 um; route period 0.77 ns); the --cts gate times it.  If that reg->reg path fails, the
  successor adds the rs-style RELAY (+1 edge per ring stop, priced in MU.S81.CAL as xg5 did), not a squeeze.
3 Fanout: FIXED -- first full-top census (my census.sh, r1) FAIL max 72: BF arrival-line decode in xs4 g_bl (shared AND3 par/bu, 72 loads x 4 groups) + calendar due act (39). Fix: 2 kept ot_s81sl_xs4_bdec predecodes per group (SYNTH_KEEP_MODULES) + kept act_g copy for the age update; value-preserving, benches re-PASS. Mapped native census (tools/ref_tile/native_census.py origin/main, ORFS keep-regs hook, TT RVT) of the whole
  top: full-top census running at gate time (pre_route_gate refuses the floorplan on any driver > 32) and in results/rtl/s81_xgtxo_1021/scripts/census.sh (ot-epyc5, pending_results); parents: rstopt_xo PASS below, xs4 PASS in the xg5 lineage after XG5d.  rstopt_xo alone: PASS max 32, 0 drivers > 32, rst_n 10 loads, 6,899 um2 (rstopt 6,848).  Kept copies survive (keep regs hook; xs4 helper modules
  non-parameterised and in SYNTH_KEEP_MODULES so no paramod rename).
  Full-top census round 1 (@6aac44322, ep5 c_xgtxo.log): FAIL max 72, 5 drivers > 32 (4 x 72 = shared AND3 BF arrival-line
  decode par/bu per group; 1 x 39 = calendar act driving the 24-b age update), rst_n 12.  FIXED (S81-SLICE/XG 10-21): 2 kept
  non-parameterised ot_s81sl_xs4_bdec 2-level predecode instances per group (one per ln copy, in SYNTH_KEEP_MODULES) + kept
  act_g copy for the age update.  Value-preserving, 0 cycles.  The --cts gate re-runs the full-top census (refuses on > 32).
4 Depth: rstopt AND-OR of one-hot kept selects (egress adds 3 terms to the W line OR); xs4 cones unchanged.  PASS.
5 Storage: 24 x 128x256 x-buffer SRAMs, 7 ROMs, 6 exponent SRAMs (xs4); rstopt 4-slot fragment buffers (4 x 276 b, written per
  slot, read as a word: not runtime-indexed).  PASS.
6 Floorplan: 37 macros on the 43.2 lattice, split S/N stacks (<= 4 SRAM / 2+2 ROM per column half), full-width macro-free centre
  band (>= 420 um free height for W<->E wires at every x), 4-stack pin faces on >= 34.8 um channels, pins on full faces
  <= 6/um, aspect 1.33:1.  Fill ~26% recorded as routing/perimeter-bound (fill_reason): a 40-60% outline is
  the xg5 648 x 561.6 slot that failed GPL routability (macro wall, DPL-0038); the outline comes from the macro-free band +
  11,914 face pins, not std area.  Waived-with-reason (40-60% rule).
7 Clock: k-means regional split K=16 (clock_split_km.tcl), one tile clock; pin-flop spread <= 80 ps TT+FF judged by the --cts
  gate; io_hold_margin 0.03.
8 Schedule: static, no credits / backpressure; +1 edge on the slice x path only (above), handed to MU.S81.CAL.
