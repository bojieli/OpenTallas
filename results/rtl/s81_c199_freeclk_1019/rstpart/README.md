# C199 free-clock + reset partition (OT_BF_RSTPART), kit s81sf_bfcol_c199rp -- S81-C199-FRAME 10-19

Successor of s81sf_bfcol_c199r (CTS stopped: 84.09 ps cross-ICG carry skew, receipts e518611e4/3135fc769) on the
free-clock source e51975a97 (124422-cycle identity 55812b482; mapped census be8676abc: 51965 FF, data/control fan-out
<= 32, but 21 reset nets > 32: 16 x 102 lane synchronisers, 552 lane tree, 285 segment tree, 136 chains, 42 pair, 38).

## Reset partition (RTL 1f4bbbb6f, opt-in, default off; requires OT_BF_TILE_FREECLK)
rst_n_pin -> kit reset_landing L0 -> L1 (2 registered stages, +2 release, as c199r)
  -> 6 kept copies of r_rst (b_rst_v[0..5], d = 1, async clear from the landed pin)            L1 load: 8
  -> kept region synchroniser copies (ot_v41_rst_copy: NOT parameterised, keep_hierarchy)     <= 21 per b_rst_v
  -> async resets                                                                             <= 35 per copy
Every copy is the register function of the single synchroniser it replaces (d = 1, async clear from the same source,
same free clock), so every reset releases on the same edge: no added cycle, no data edge.

| region (copy)                                   | loads | was (net)          |
|-------------------------------------------------|-------|--------------------|
| BF lane body v_r/vp (u_rl, x16)                 | 9     | 102 (lane rst)     |
| BF lane multiplier u_m (u_rm, x16)              | 33    | 102                |
| lane chain body / fwd selects / adder (chain4_rp u_rb/u_rf/u_ra, x16) | 17 / 8 / 35 | 102 |
| lane tree: xst+levels 0-1 / levels 2-3 (u_rt0/u_rt1) | 22 / 20 | 552 (tree rst) |
| lane tree adders u_a (x15)                      | 34    | 552                |
| q chains u_c0/u_c1 (chain4_rp, 3 copies each)   | 25 / 8 / 35 | 136 (rst_mc) |
| q lanes u_l0/u_l1 (u_rsl) ; g_mi + g_fx (u_rs)  | 24 ; 14 | 38 (rst_m)       |
| pair adder (u_rsp) ; pair valid pipe (u_rspv)   | 34 ; 8 | 42 (rst_mp)       |
| segment tree control / adder / per tree pair x8 (segtree5_rp) | 17 / 35 / 28 | 285 (rst_mt) |
| outputs o_v, bkf_r (u_rst)                      | ~3    | 285                |
Over 32: one leaf FP adder / multiplier output word per copy (fadd/fadd2 y[32] + err[2] + valid = 34/35, bmul 33):
"~32" at leaf-instance granularity; splitting a 32-bit result word over two reset copies buys nothing physically
(the word is one placement cluster). Waived with this reason.

## SAFE-DESIGN checklist
1 Pins: PASS -- RTL registers every pin at the face (g_pin.r_*, kit pin_regs opt-out reason as c199r); reset lands in
  2 registered stages (reset_landing 2).
2 Reach: PASS (same 432x216 floorplan as c199r; reset copies are per region, placed by the placer next to their loads;
  gate wire-per-stage lint is the check).
3 Fan-out: fixed -- reset partition above; data/control <= 32 (be8676abc census, unchanged by RSTPART). Kept copies
  must survive synthesis: checked on the gate's synthesized ODB (reset-sink census per driver, tools census tcl
  rst_groups.tcl in this dir).
4 Depth: PASS -- RSTPART adds no logic to any data path (lint @d6d1730cb worst 493.4 ps); re-read in the gate lint.
5 Storage: waived -- unchanged closed compact199 storage (segment tree held 80x32 one-hot register file with registered
  one-hot selects, chain accumulators 16x32); no new storage.
6 Floorplan: PASS (c199r kit): ROMs on the 43.2 lattice, shared 23.45 um pin channel, 777 E-face inputs 3.6/um, outline
  432x216 (2:1), mapped std area 48768 um2 -> 0.52 of the outline; full-width std-cell band right of the ROMs.
7 Clock: centre-fed single CTS tree on the free clock (no ICG -> the 84.09 ps cross-ICG carry skew is gone); clock pin
  N 298-302 above the register mass; ~52k sinks on one root: judged by pin-flop spread <= 80 ps TT+FF in the gate
  (owner clock rule), not by sink count; io_hold 0.03.
8 Schedule: 0 data edges (output-cycle identity bench), reset +2 (landing, already handed to MU-DIE-S81 by c199r).
  Idle clocks of the free-clock tiles are paid activity: power unpriced (open).

## Evidence
- Bench (Verilator 5.050, fleet): tools/s81/bf_rstpart_bench.py -- baseline (default column) vs rstpart
  (FREECLK+RSTPART) per-cycle valid/metadata/busy/fault trace identity; negatives OT_BF_RSTPART_MUT_STUCK (lane 5 body
  copy never releases) and OT_BF_RSTPART_MUT_TREE (segment trees 6-7 held in reset) must FAIL. Results below.
- Gate: pre_route_gate.py physical/ref_tile/s81sf_bfcol_c199rp --commit 1bccd2de5 --remote auto --cts (critical
  ot_v41_bf_: no REVIEW.json / submit by the lane; PNGs + checklist to COORD-REVIEW-QUEUE).

## Bench result (10-19 11:44, ot-epyc6 unit oth-ubuntu-2572809-1792434968, Verilator 5.050, source 1f4bbbb6f)
- baseline (default column, RSPLIT+TAGREP) and rstpart (+FREECLK+RSTPART): both PASS 456 numerical rows / 124422
  cycles / 1990752 wake assertions / TXN MATCH compared=456, lag 5.831/14.994/9.090 ns (= c199r).
- Per-cycle output/status trace: rstpart == baseline byte for byte, 124422 lines, sha256 c6cf9839...95bf0d
  (rstpart_exact.json).
- rp_mut_stuck: DIFF TXN lane=0 n=16 at 7018 ns (fail_witness/rp_mut_stuck.log).
- rp_mut_tree: values still match (TXN MATCH, lag max 46.648 ns) but the per-cycle trace differs from line 2941
  (2449 ns): caught by bf_rstpart_bench's per-cycle rule, not by a DIFF TXN regex, so it is NOT a job.json bench
  (fail_witness/rp_mut_tree_run.log is the run log).
