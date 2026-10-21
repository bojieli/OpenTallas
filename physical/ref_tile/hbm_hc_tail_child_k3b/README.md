# hbm_hc_tail_child_k3b -- HC Sinkhorn tail child FALLBACK (TPIPE 1, SKP 0, SDIV 12 + MCP 12), FAM-HBM-B/HCTAIL 10-21

Element ot_hbm_hc_tail_child_static (hard child x2 in ot_hbm_hc_root_static TAILC=1). PARALLEL FALLBACK of
hbm_hc_tail_child_k3. Outline 440.64 x 293.76 (aspect 1.5); all inputs N, outputs S, clk+rst_n W (k2b plan).
Rebuilt after the k2b --cts gate STRUCTURAL FAIL (10-21 04:36): Sinkhorn step 7,533 ps vs the 5,833 ps MCP7 budget;
~2,100 single-period tail paths (~38 levels, -417 ps).

## Structural changes (RTL @HCTAIL)
- Sinkhorn: unchanged combinational step ot_hdc_sinkhorn_ce (instance u_tail.g_skce.sink), step enable 1 in SDIV = 12:
  declared multicycle 12 / hold 11 between its own registers (physical/hbm_hc_tail_child/tailc_skmcp12.sdc): 10.0 ns
  budget vs 7.53 ns measured on k2b.
- Tail: TPIPE 1 exactly as k3 (operand registers; mul_lat 9, add_lat 7, exp LM 6 / LA 4, ot_hdc_fdiv; 2-level row max;
  EREADY 197 -> 270).
- Child: CAP = 41 x 12 + 2 = 494, L = 271 + 12 + 494 + 2 = 779 (was 496): +283 edges for the root schedule (TE 2 -> 285).

## Source = gate-level cloned netlist
rtl/hbm_accel/generic/peers/static_hc/native/ot_hbm_hc_tail_child_static_k3b.v: RTL -> chparam SDIV 12 TPIPE 1 SKP 0 ->
per-module ABC map -> bound_fanout_clone.py --limit 24 --tag sk_=g_skce.sink. -> retained re-synth -> compact_netlist.py.
Recipe + evidence results/rtl/hbm_hc_root_safe_1020/tail_child_hc9/ (nl.sh, cen.sh). sha256 3f21e358...3026; 6,845 clones,
structural invariant PASS; 66,204 um2 (TT RVT), 27,119 flops (k2: 62,877 / 19,925), 3,076 Sinkhorn registers sk_c* (MCP 12).
Benches (Verilator 5.050): RTL lockstep vs released unit PASS 48 (child = unit + 285 edges, bit-exact); MUT1 row-max
FAIL 44/48; native lockstep = tailc_native_lockstep.

## SAFE-DESIGN CHECKLIST (owner 10-19) + PRE-GATE NATIVE CHECK
1 Pins: PASS -- RTL pin flop + 2nd stage on every data input, output pin flops; rst_n reset_landing 2, ot_rst_relay 3 regions + kept leaf.
2 Reach: PASS by plan -- side <= 441 um, every pin->core hop registered; post-GRT 405 check by the gate.
3 Fanout: PASS -- native32 census of the retained netlist: max 24 loads, 0 violations, 630,666 roots
  (uncloned per-module map: 2,549 drivers > 32, max 3,432 = reset; fixed by the cloner).
4 Depth: Sinkhorn step = declared multicycle 12 (waived-with-reason: the cheap variant, 10.0 ns budget vs 7.53 ns
  measured); every other path single-period with the tail cones pipelined (TPIPE 1).
5 Storage: PASS -- no runtime-indexed flop array > 2 kb.
6 Floorplan: PASS -- no macros, util ~0.5 of synthesis area, aspect 1.5, one full std-cell band, pins <= 6/um.
7 Clock: ONE root (clk), no derived clock; pin-flop spread <= 80 by the --cts gate; io_hold_margin 0.03.
8 Schedule: static, no backpressure; +283 edges (child L 779) recorded for the root schedule (TE).
