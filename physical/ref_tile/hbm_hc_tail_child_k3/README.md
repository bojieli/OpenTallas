# hbm_hc_tail_child_k3 -- HC Sinkhorn tail child MAIN (TPIPE 1, SKP 1, SDIV 16), FAM-HBM-B/HCTAIL 10-21

Element ot_hbm_hc_tail_child_static (hard child x2 in ot_hbm_hc_root_static TAILC=1). Square 388.8 x 388.8; mixes W,
bases+scales+launch N, result/result_v/fault E, clk+rst_n S. Parallel fallback = hbm_hc_tail_child_k3b.
Rebuilt after the k2b --cts gate STRUCTURAL FAIL (10-21 04:36): Sinkhorn step 7,533 ps arrival vs the 5,833 ps MCP7
budget (234 cells), and ~2,100 single-period tail paths (~38 levels, 1.65 ns, -417 ps: row max 4-way scan, operand
24:1 AND-OR select into unit stage 1, unit-internal stages of add/mul/exp, the radix-4 divider recurrence).

## Structural changes (RTL @26d9af0f9)
- Sinkhorn step: ot_hdc_sinkhorn_cp (rtl/hdc/v41/ot_hdc_sinkhorn_cp.sv + ot_hdc_sk_arith_cp.sv). The step cone is cut by
  free-running registers; its inputs (er / a_* / st) change only on a ce edge and are held, so the cuts settle the exact
  value D <= 15 edges after a ce edge (steady step P1 M1 X1 M2 X2 M3 X3 ME XE S1 S2 S3 Q1 Q2 Q3). SDIV 16 >= D + 1.
  NO multicycle path (no tailc_skmcp SDC in this kit); every segment <= ~16 ASAP7 levels.
- Tail (ot_hgi_hc_tail_os_static TPIPE 1): operand register before every unit; mul_lat 9, add_lat 7, exp LM 6 / LA 4
  (DEPTH 78), ot_hdc_fdiv (one quotient bit a stage, DEPTH 31); row max = registered 2-level tree. Calendar re-derived:
  P2 35, MAX 67, P3 69, P4 93, P5 196, P6 212, P7 252, EREADY 270 (was 197).
- Child: CAP = 41 SDIV + 2 = 658, TR = 271, L = TR + SDIV + CAP + 2 = 947 (was 496): +451 edges, handed to the root
  schedule (TAILC emit offset TE 2 -> 453; root xr4).

## Source = gate-level cloned netlist
rtl/hbm_accel/generic/peers/static_hc/native/ot_hbm_hc_tail_child_static_k3.v (sha256 20929e2b...b876): RTL -> chparam
SDIV 16 TPIPE 1 SKP 1 -> per-module ABC map -> bound_fanout_clone.py --limit 24 --tag sk_=g_skce.sink. (6,686 clones,
structural invariant PASS) -> retained re-synth -> compact_netlist.py. Recipe + evidence results/rtl/hbm_hc_root_safe_1020/
tail_child_hc9/ (nl.sh, cen.sh). 72,334 um2 (TT RVT), 45,859 flops (k2: 62,877 / 19,925), 21,816 Sinkhorn flops.
Benches (Verilator 5.050): RTL lockstep vs released unit PASS 48 (child = unit + 453 edges, bit-exact); mutants MUT1
row-max FAIL 44/48, SKP 1 at SDIV 12 FAIL 48/48 (proves the cut depth); native lockstep = tailc_native_lockstep.

## SAFE-DESIGN CHECKLIST (owner 10-19) + PRE-GATE NATIVE CHECK
1 Pins: PASS -- RTL pin flop + 2nd stage on every data input, output pin flops; rst_n reset_landing 2, ot_rst_relay 3 regions + kept leaf.
2 Reach: PASS by plan -- side 388.8 um < 405, every pin->core hop registered; post-GRT 405 check by the gate.
3 Fanout: PASS -- native32 census of the retained netlist: max 24 loads, 0 violations, 650,173 roots
  (uncloned per-module map: 2,493 drivers > 32, max 3,432 = reset; fixed by the cloner).
4 Depth: fixed -- no multicycle; Sinkhorn step in 16 single-period segments; tail cones pipelined (TPIPE 1).
5 Storage: PASS -- no runtime-indexed flop array > 2 kb (cut registers are fixed pipeline registers).
6 Floorplan: PASS -- no macros, util ~0.49 of synthesis area (72.3k / 148k core), square, one full std-cell band, pins <= 6/um.
7 Clock: ONE root (clk, 45,859 flops; > 15k is guidance), no derived clock; pin-flop spread <= 80 by the --cts gate;
  io_hold_margin 0.03.
8 Schedule: static, no backpressure; +451 edges (child L 947) recorded for the root schedule (TE).
