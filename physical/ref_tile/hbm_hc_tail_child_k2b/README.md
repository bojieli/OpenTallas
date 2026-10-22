# hbm_hc_tail_child_k2b -- HC Sinkhorn tail child tile, SKCE 1 (H.STA.BLK.1), HBM-HCROOT8 10-20

Element ot_hbm_hc_tail_child_static (hard child x2 in ot_hbm_hc_root_static TAILC=1).  PARALLEL FALLBACK. Outline 440.64 x 293.76 (aspect 1.5); all inputs N (3.7 pins/um), outputs S, clk,rst_n W.
Successor of k1/k1b, whose --cts gates FAILED at 4_1_cts: the logic-derived /7 Sinkhorn clock (flop -> INVx1 -> 3,088
sinks) was never treed (CTS-0040 'Net was not found for sclk') and the ffrepair SDC lost its driver.

## Source = gate-level cloned netlist
rtl/hbm_accel/generic/peers/static_hc/native/ot_hbm_hc_tail_child_static_k2.v (sha256 9d859060...a882): RTL @47be76436
(SKCE 1: Sinkhorn ot_hdc_sinkhorn_ce on clk with the one-flop /7 step ENABLE) -> per-module ABC map -> bound_fanout_clone.py
--limit 24 --tag sk_=g_skce.sink. (6,798 clones, structural invariant PASS) -> retained re-synth -> compact_netlist.py.
Evidence results/rtl/hbm_hc_root_safe_1020/tail_child_hc8/ (pipe2.sh = exact recipe).
Benches (Verilator 5.050): RTL lockstep vs released unit m0 TAILC PASS 48 (result = unit + 2 edges, bit-exact), MUT1 FAIL
44/48; native lockstep of THIS netlist = tailc_native_lockstep (witness tailc_k2_native_m0_run.log).

## SAFE-DESIGN CHECKLIST (owner 10-19) + PRE-GATE NATIVE CHECK
1 Pins: PASS -- RTL pin flop + 2nd stage on every data input, output pin flops (pin_regs opted out: they ARE the RTL's);
  rst_n reset_landing 2 stages, then ot_rst_relay 3 regions + kept leaf per region.
2 Reach: PASS by plan -- side <= 441 um, every pin->core hop registered; post-GRT 405 um check by the gate.
3 Fanout: PASS -- native32 census of this netlist: max 24 loads, 0 violations, 615,504 roots (uncloned map: 2,533 > 32).
4 Depth: released fp32 add/mul/fdiv/exp units; the Sinkhorn step (one normalisation, ~5.4 ns TT, 138 levels) is the
  DECLARED multicycle 7 / hold 6 between the Sinkhorn's own 3,083 registers (sk_c*, physical/hbm_hc_tail_child/tailc_skmcp.sdc),
  valid because they update only on the 1-in-7 enable; priced since 10-15 (L = 198 + SDIV + CAP + 2).  Every other path is
  single-period.  No combinational in->out path.
5 Storage: PASS -- no runtime-indexed flop array > 2 kb.
6 Floorplan: PASS -- no macros, util ~0.5 of synthesis area, aspect <= 2:1, one full std-cell band, pins on full faces <= 6/um.
7 Clock: PASS -- ONE root (clk, 19,925 flops), no derived/generated clock; pin-flop spread <= 80 by the --cts gate;
  io_hold_margin 0.03.
8 Schedule: static; result edges unchanged (child = unit + 2, TAILC; HC_MIX unchanged).
