# qfd_n59_qbank10_c -- native59 Q-seat bank, qbank10 (QW-CB16A0-3 10-20) -- variant _c: 2-level 30x40 CTS sink clustering

Structural successor of qbank9 (all three qbank9 gates TERMINAL FAIL; Codex geometry HARD HOLD 03267fbf0, stage graph d012644bc,
model 6507f9b64).  RTL rtl/qwen_split/qfd_native59_qbank.sv QB_ALIGN=1 QB_LOCAL32=1 QB_STAGE=1 QB_M546=1 (QB_STAGE=0 QB_M546=0 =
qbank9 bit for bit: q9_rnd PASS).

Root causes addressed (one failed route = structural redesign, no squeezing):
- geometry: legacy ot_sram_1r1w_32x512_m1 had 10.18 pins/um faces, macros abutted (0.036-um channels), off-lattice origins ->
  8 x ot_sram_1r1w_32x546_m1_p192_mir (32 deep, 5.15 pins/um per E/W face) in a 4 x 2 grid at literal 43.2 origins
  x {43.2, 259.2, 475.2, 691.2}, y {43.2, 259.2}: 38.2-um column channels, 55.6-um full-width row channel, 43.2 / 55.6 edge bands.
  Writers 0-3 in the west half, 4-7 in the east half (the two read partials).  Spare columns 512..545 are driven by kept
  same-edge lane-15 copies (no tie cells); rd_out[545:512] unread.
- reach (84 stage spans > 405, max 508): Codex necessary 380-um model implemented: +561 input capture FFs (every input port, and
  rst_n through two kept copies), qrow_a split into two 4-writer partials (+512 FF, merged by qrow_r with 512 OR2), +1076 output
  FFs (pure one-edge delay of every output).  Bank = qbank9 + 2 edges on every path: flat lockstep SOFF 5 / BOFF 0 / ROFF 6
  (was 3 / 0 / 4).  The parent (lp.py) and the die schedule must take the +2 (Codex price 8696df980 SOFF5/BOFF0/ROFF6).
- clock (qbank9 155-170 ps): per-flop TT dump of qbank9_c 4_1_cts.odb: every boundary flop 394..419 ps EXCEPT one S-face west
  branch (f_dd[0..~40] at x 130-160: 470-549 ps).  qbank10 centres both pin bands (S 325.6-474, N 325.6-586.4, ck 452.1) on the
  wider outline; _c adds 2-level clustering.  The gate measures TT/FF pin-flop spread (<= 80).

## Safe-design checklist + pre-gate native census
1 Pins: PASS -- every input lands in i_* (S face), every output is an o_* flop (N face); rst_n: kit reset landing (2 stages,
  32 copies) then rst_q x2 kept copies.  pin_regs off (RTL flop-first, edge contract benched).
2 Reach: model PASS (Codex necessary endpoint LP at 380 um for the p192 4x2 grid); placed reach measured by the gate.
3 Fanout: qbank9 strict census max <= 32 (722cd9bda); qbank10 adds rst_q (3 kept copies, 20 reset-copy loads each), i_* (each
  drives the loads the raw pin drove, <= 17), spare-column mask copies xm (17 each), partial/merge regs (1-2 loads).  The gate's
  in-flow census (limit 32, refuse, before layout) is the binding pre-gate census; a WARN hiding a violation = FAIL.
4 Depth: partial gather = 4-way AND-OR per bit + bypass mux, then register; qrow_r = OR2.
5 Storage: Q seats in 8 SRAM macros (32 x 546), no flop arrays.
6 Floorplan: macros on 43.2; channels 38.2 / 55.6 um >= 20 um, faces 5.15 pins/um <= 6; outline 907.2 x 475.2 (aspect 1.91);
  macro fill 52.9 %; full-width std-cell bands (bottom 43.2, middle 55.6, top 55.6).
7 Clock: one centre-fed root ck at the S-face centre; spread measured TT/FF; io_hold_margin 0.03.
8 Schedule: static; +2 edges on every bank path (input +1, output +1); benched.
Benches (Verilator 5.050, ep7; receipts results/arch/qw_n59_qbank10_1020/receipts): rnd rnd_s2 reset8 dv mu PASS at 5/0/6;
q9_rnd (QB_STAGE 0) and m546_only (macro swap alone, 3/0/4) PASS; mutants REJECTED: mut_old_offsets (3/0/4), mut_qb1
(qb_row one edge early), mut_mask, mut_select.
