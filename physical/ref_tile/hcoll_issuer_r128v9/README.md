# hcoll_issuer_r128v9 -- COLLQ7 10-21 clock-spine successor of hcoll_issuer_r128v8

r128v8 --cts gate FAILED clock_rule only (r128v8 TT/FF pin-flop spread 150.3/141.9, r128v8b 105.9/107.5; GRT ovf 0, census PASS max32,
placement macro->reg -152/-118 ps from the late TritonCTS SRAM clock). Class: sink-driven TritonCTS over a macro-dominated tile
(1,536 W pin flops over the full face + 10 SRAM clock pins). Fix: clock 'spine' (pre-placed equal-delay spine, measured-arrival
leaf padding, SRAM clock pins own leaves); same RTL bf2ba3fe5 / outline / macros.
Checklist item 7 now: spine, spread pending gate; all other items unchanged from the predecessor (below). Benches re-run on
bf2ba3fe5: pos 600 progs 1,478,710 checks PASS, reload/nofwd/swap REJECTED (witnesses refreshed), q3/q2 parent EQ EXIT 0.

## Predecessor README
# hcoll_issuer_r128v8 -- 128-row COLL issuer leaf, v8 body (HBM-COLLQ6-ISS 10-20)

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
