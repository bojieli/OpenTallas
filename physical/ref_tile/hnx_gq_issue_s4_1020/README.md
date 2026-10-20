# hnx_gq_issue_s4_1020 (HNX-UNITS/GQ 10-20) -- next-release HBM (P=3) COLL gather master ISSUE leaf, s4 = native-census rebuild of s3

Same geometry, macros, pins and stage table as hnx_gq_issue_s3_1019; CTS: unclustered TritonCTS leaves (as s3).
Predecessor s3 (c349adf8a): PRE_GATE_NATIVE_CENSUS_REFUSED, 683 drivers > 32 loads, max 1,351 (classes A-I in the s3 README;
evidence results/arch/hbm_next_1019/units/coll/census_s3/). Source branch claude/hnx-gq-s3-1019.

## What s4 changes (0 schedule edges; configured rises 2 edges later = initialization only)
- A/H programme: ot_hnx_gq_prog_target (GQ copy of the hc safe target ot_hnx_prog_target, b72f6e65f): bitmap as kept per-row
  copies, no bitmap reset, 2-stage scan; reset_ctrl_copies x8 (kit OT_RST_COPIES_RE splits them); reset-free config registers;
  kept per-row write strobes (5 per row, <= 28 row-file enables each) and 9 kept launch copies, both on the SAME edge as
  program_cfg_we / program_start_v (registered from the next-state). The row file and B write from the strobes.
- B/C/D/E calendar: next-state form (*_n); every wide control is a kept register bank loaded with its next-edge value:
  fire x40 (two kept-hierarchy ot_hnx_gq_fire_fn), wrap x2, wrap_ld x13, ev_in_v x15, i_adv x6, lastk/iend x2, lq x12;
  each copy group derives its own select terms (no shared >32 net).
- F/G: per-bank VM request muxes on kept g_qbg / sfv / scd copies and registered bank one-hots qoh (from qa's next state);
  g_r2 x6, g_src/g_rsa x4 (sb rows), R[1]/R[49:37] x2 (qa loads); registered row one-hots at stages 7/13/22, stage-22 entry
  copy; a1 lp_we x18 for ra_lp_data; ex fire clear on fire copy bank A.
- I aq14: shift count as a registered 7-b one-hot (rs_of() is always 20..26; <= 13 loads per bit), 4:1 and 3:1 max in two
  kept-hierarchy halves with own compares, scale exponent s1_power x4 kept copies.
- Reset relay REGIONS 40 (flow split <= 32).

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- every input is captured by a flop at the pin and every output is a flop Q (stage table unchanged from n2; auto pin
  registers opted out, keep_pin_regs); reset lands in 2 registered face stages (reset_landing, rst_n x4 copies), then the 24-region
  kept relay (flow split <= 32 loads).
2 Reach: PASS by stage plan -- each transport (read face -> feed register -> quantiser S0 at the macros -> output registers -> P at
  the east face) is a registered hop on a 432 x 345.6 tile; the gate's netlist lint (> 500 um per stage) and the placement PNG
  are the check; any > 405 um hop found there gets a relay.
3 Fanout: s4 REBUILD (s3 census FAIL 683 > 32) -- see 'What s4 changes' above; the mapped-netlist native census (floorplan step,
  limit 32 incl. reset, no waivers) is the check; numbers in 'PRE-GATE NATIVE CENSUS' below.
4 Depth: FIXED -- S9 (8-b field select + 11-b subtract) | S10 (11-b subtract, compare, 5-b add, mux) | S11 (13-b chunk shift, sticky
  OR, 5-b round add); scale stage 4 rebalanced (scale13r); descriptor consumers read registered rows; no combinational in->out path.
5 Storage: FIXED for the element lines (2 x 9,216 b in 8 SRAM rings). Waived with reason: descriptor file 2,192 b (just over the
  ~2 kb guidance) stays a config-written flop file with ONE registered read port (no runtime-indexed mux, no combinational
  consumer; brief option "registered single-read design"); the 40 x 21 b event line is the static schedule itself (9 taps), narrow.
6 Floorplan: PASS -- 8 macros on the 43.2 lattice (K geometry: x 43.2/172.8/302.4, y 43.2/129.6/216), halos 16.2 x / 2.16 y,
  channels 34.8 / 45.4 um, full-face pins (<= 6/um), one full-width std-cell band, aspect 1.25. Fill below 40% expected (macro- and
  channel-limited outline, 31.1k um2 hard area): the safe side, measured by the gate.
7 Clock: single centre-reachable root on a small tile, TritonCTS with route.cts_sink {"sink_clustering": false} (short local leaves; precedent qkd_d2d_static; LH-SU k1); the gate must show pin-flop spread <= 80 ps at TT and FF;
  io_hold_margin 0.03 (>= 0.025).
8 Schedule: PASS -- static, no credits; quantiser +1 edge absorbed (data calendar unchanged); +1 launch -> fire edge
  (FIRE_FROM_LAUNCH 3 -> 4, tools/hbm_next/hnx_coll_gq_train.py) and the rule "no descriptor row rewrite in the edge before its
  fire" handed to HNEXT.CMTP (lane L2H-P3.md); cost one edge per programme launch, not per gather.

## Benches (Verilator 5.050, fleet; tools/hbm_next/hnx_gq_s3_bench.sh STAGE all)
Fleet ot-epyc9, Verilator 5.050, bundle 3fcf420a2 (results/arch/hbm_next_1019/units/coll/bench_s4/verdict_all_3fcf420a2.txt): s0/s1/s2 COLLQ PASS
(vm_words_checked 2,644 / 8,284 / 21,248), faults f1..f5 FAULT PASS, schedule + train checks 0 conflicts, AQ14 lockstep
AQ14_EXACT_PASS. Mutants FAIL with the SAME error counts as s3 (witnesses results/arch/hbm_next_1019/units/coll/witness_s4/):
m9 600, m2 64, m8 22,037, aqec / aqrs / aql AQ14_NUMERIC_MISMATCH (aqrs now flips the one-hot shift-count copy).

## PRE-GATE NATIVE CENSUS
Pending (synthesis gate without --cts; numbers appended here).
