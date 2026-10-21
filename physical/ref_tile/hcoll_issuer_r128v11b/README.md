# hcoll_issuer_r128v11b -- HBM-COLLECT10/ISS2 10-21 SAFE successor (FALLBACK) after the FAILED --cts gates of hcoll_issuer_r128v10 / r128v10b

Gate verdict (both, ot-epyc5 ref_gate .../hcoll_issuer_r128v10{,b}-20261021-064100): FAIL native_census / floorplan_run / textbook_execution.
Only real cause: the pre-gate native census refused the mapped netlist (floorplan.tcl PRE_GATE_NATIVE_CENSUS_REFUSED, flow RC 1 after 51 s);
the floorplan and textbook FAILs are that abort (no PDN/PPL/MPL error, no geometry problem). Census: 17,980 roots, max 34, ONE violation
u_ot_pr_core.u.fwn_c[0]$_DFF_PN0_/QN -> 34 loads (the CN counter-forwarding select of the 16 low counter bits, merged by synthesis
into the raw-count take compare). FIX (RTL, ot_hgi_coll_issuer_m128v8): fwt_c / fwn_c widened from 2 to 4 KEPT copies (keep attr), each
selecting 8 counter bits (~17 loads each); reset leaf rcp[5] 24 -> 28 loads. ADDED CYCLES: 0 (port- and edge-identical; same edge, same
value replicated). Geometry: 302.4 x 432, clock spine, W-centre entry (= r128v9b/v10b), unchanged.

## SAFE review (safe_1021, 8 points)
1 Pins: PASS -- cfg/start/start_pc registered in RTL, outputs flop Q; rst_n -> 2-stage kit landing -> 32 kept rcp copies; W face 1,536 pins <= 3.74/um.
2 Reach: PASS by floorplan -- tile <= 432 um tall, rd_out -> bank regs -> W pins through row channels <= ~260 um; metadata loop <= ~130 um.
3 Fanout: FIXED -- v10 census max 34 (fwn_c[0]); fwt_c/fwn_c now 4 kept copies (<= ~17 loads); all other drivers <= 32 in the v10 census. Gate census re-judges.
4 Depth: PASS -- v10 raw-count record removed the SRAM -> 32-b decrement chain (v9b TT -135); macro -> state = SRAM -> 2:1 -> 2:1.
5 Storage: PASS -- programme 6 x 128x256 SRAM + metadata 4 x 128x64 SRAM; flops only 1 kb counters / 640 b row-valid / 512 b fixed-slot assembly.
6 Floorplan: PASS -- macros x on the 43.2 lattice, channels >= 21 / 29.7 um, std-cell band continuous, fill ~43 % / ~41 % from synth area, aspect <= 1.43.
7 Clock: single region, clock spine (equal-delay, macro clock pins own leaves); io_hold_margin 0.03; spread judged by this --cts gate.
8 Reset/schedule: PASS -- reset only on control/valid + kept copies (rcp landing per group <= 32); static schedule, 0 added cycles (miter vs v6 every port every edge).

## Predecessor README (r128v10b)


Failed route (ot-epyc6, routed 6_finish + closed-loop path_summary): TT -135.42 ps (64 D pins, TNS -2.70 ns) / FF -20.25 / DRC 0.
CLASS = LOGIC DEPTH behind a macro read (not fanout, not wire, not clock): every TT violator is g_meta[*].u_sram/rd_out ->
rt / rn / pr_t / pr_n / pr_c, 15-16 levels: 326 ps SRAM clk->q, then the record's 32-bit count-1 decrement borrow chain
(AND2-AO21-OR5-OR4-OR5-OR5-OR5-OR3-OR2-OR4-XNOR-NAND-OA211-AOI21, ~540 ps) in the same edge; the spine launch clock was 33 ps
late (517 vs 484 ps). The v9/v9b gates already showed it as macro->reg -107 / -101 ps.
FIX (RTL, ot_hgi_coll_issuer_m128v8 in ot_hgi_coll_static_issuer_v7r128.sv): the metadata record keeps the RAW count field;
the decrement moves into the loop decision on the registered side: take = has && q < cnt-1 == has && (q + ~cnt + 2 < 2^32)
(carry-save of q / ~cnt / 2, then one 32-bit carry-out). The macro -> state path is now SRAM -> 2:1 take mux -> 2:1 adv mux
(+ a 32-input OR for 'has'). The q -> take path gains one carry-save (XOR/MAJ) level in place of the precomputed compare operand.
ADDED CYCLES: 0 (port- and edge-identical; miter vs v6 every port every edge). Geometry: 302.4 x 432, clock spine, W-centre entry (= r128v9b), unchanged.
FF hold -20 (fv_c->r_ce_in, aen_*->assemble, vm*->data, assemble->wd_in; <= 6 levels): route hold repair residue, not
structural; hold_eco mm session + io_hold_margin 0.03 kept.
Checklist delta vs predecessor: 4 Depth FIXED (decrement removed from the macro-read stage); 1-3, 5-8 unchanged (below).
Benches re-run on the new RTL: lanes/HBM-COLLECT10_logs/iss_bench (pos / reload / nofwd / swap, q3/q2 parent EQ).

## Predecessor README

r128v8b --cts gate FAILED clock_rule only (r128v8 TT/FF pin-flop spread 150.3/141.9, r128v8b 105.9/107.5; GRT ovf 0, census PASS max32,
placement macro->reg -152/-118 ps from the late TritonCTS SRAM clock). Class: sink-driven TritonCTS over a macro-dominated tile
(1,536 W pin flops over the full face + 10 SRAM clock pins). Fix: clock 'spine' (pre-placed equal-delay spine, measured-arrival
leaf padding, SRAM clock pins own leaves); same RTL bf2ba3fe5 / outline / macros ; FALLBACK also moves clk_control to the W face centre (y 216).
Checklist item 7 now: spine, spread pending gate; all other items unchanged from the predecessor (below). Benches re-run on
bf2ba3fe5: pos 600 progs 1,478,710 checks PASS, reload/nofwd/swap REJECTED (witnesses refreshed), q3/q2 parent EQ EXIT 0.

## Predecessor README
# hcoll_issuer_r128v8b -- 128-row COLL issuer leaf, v8 body (HBM-COLLQ6-ISS 10-20)

SAFE successor of hcoll_issuer_r128v7 / r128v7b (gates FAILED: v7 TT spread 81.5 + trial GRT overflow 1660 + fill 31%;
v7b spread 171.7 / 147.5; both rst_l 799 loads, mapped census 56 drivers > 32). Leaf ot_hgi_coll_issuer_m_r128 (name, ports,
instance u unchanged: no parent re-pointing) now binds ot_hgi_coll_issuer_m128v8 (ot_hgi_coll_static_issuer_v7r128.sv).
r128v8 (MAIN) 302.4 x 410.4, 21 um row through-channels; r128v8b (PARALLEL FALLBACK) 302.4 x 432, 29.7 um. Same RTL; bind
the first to close, cancel the other. Face change vs v7: all control pins moved N -> S (uop_d1 stays W); the parent kit is
not built yet, so it costs nothing.

## Benches (Verilator 5.050, fleet)
- run_issuer_v8r128_miter.sh: leaf v8 vs ot_hgi_coll_issuer_m #(ROWS 128) (v6) every port every edge: PASS 600 progs
  1,478,710 checks (0d09dd0fe), PASS 150 progs (bf2ba3fe5); mutants reload / nofwd / swap REJECTED
  (results/rtl/hbm_coll_iss8_1020/witness/). Re-run on bf2ba3fe5 live (lanes/HBM-COLLQ6-ISS_logs/bench_bf2).
- run_coll_lp_ars_all.sh q3|q2 eq: SAFE parents with this leaf == v8x / v8g: EXIT 0 both (0d09dd0fe), 3 EQ mutants rejected.

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- cfg/start/start_pc registered in RTL (+ mode predecode / mask copies beside them), outputs flop Q
  (busy = busy_r | start_q, as v6/v7; tap_steps = masked bank data flop Q); rst_n -> 2-stage kit landing -> 32 kept copies.
2 Reach: PASS by floorplan -- column-2 rd_out -> bank regs (inter-column channel) -> W pins straight through the row
  channels <= ~260 um; metadata loop <= ~130 um. Gate textbook reach: pending (CTS gate).
3 Fanout: FIXED -- mapped native census (gate pre-floorplan, ot-pve1 20261020-220140, bf2ba3fe5): PASS, max 32,
  0 violations (v7: 56 drivers, max 1,537). Every wide select is a registered KEPT copy (<= 8-14 mux bits).
4 Depth: by construction -- loop: one-hot AND-OR + 32-b compare + incrementer between flops; gate depth pending.
5 Storage: PASS -- programme 6 x 128x256 SRAM, metadata 4 x 128x64 SRAM; flops: loop counters 32 x 32 b (1 kb),
  row-valid 640 b (single-bit reads), assembly 512 b (fixed-slot writes); write_data (512 b) removed.
6 Floorplan: macros x on the 43.2 lattice, y on the 2.16 (M4 track x row) lattice; channels >= 21 um (main) / 29.7 um
  (fallback), inter-column / E 34.8 um, metadata >= 20 um from faces and data rows; W face 1,536 pins 3.74/um (3.56);
  aspect 1.36 (1.43); fill est. ~43% (~41%) from synth std area. Gate PNG review: pending.
7 Clock: one root (clk_control on S at x 100, beside the S/W register mass), unclustered H-tree sinks
  (route.cts_sink sink_clustering false: the v7b 638-ps tail was a clustered far leaf); io_hold_margin 0.03; spread pending.
8 Schedule: PASS -- 0 port edges changed (miter + parent EQ) -> 0 cycles DS / Qwen.

## Gate
(--cts gates on bf2ba3fe5 launched 10-20 ~00:05; logs lanes/HBM-COLLQ6-ISS_logs/gate_cts_*.log)
