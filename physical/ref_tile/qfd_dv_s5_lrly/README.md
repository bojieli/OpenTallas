# qfd_dv_s5_lrly (QW-SLICE6 10-19, Q.STA.SLICE.2) -- one SU lane's relay leaf, one master x 8 per slice

RTL `rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv` module `qfd_dv_s5_lrly`: the per-lane relay stages of `qfd_dv_su8_entries`
(LTD lane, RD 2: broadcast fields RD-1, live / offsets stage 2 (stage 1 in suvm), memory answers RD-1, read requests
RD-1, results RD) and the `qfd_dv_su_lane` glue (IREG / OREG pin flops, its reset register). Every register is one of
qfd_dv_slice2's (SU_LT 1): 0 added edges (lockstep `run_s5.sh eq 0` vs qfd_dv_slice2 at offset 0). Placed at the path
midpoint between suvm (r_su centre) and its lane cell (closed lane head + 3 SFU), so every hop is <= 405 um.
Kits: `qfd_dv_s5_lrly` (main, 108 x 216, suvm-side ports W, lane-head side E) and `qfd_dv_s5_lrlyb` (parallel
fallback, 129.6 square, pins on four faces).

SAFE-DESIGN checklist (owner 10-19):
1. Pins: PASS -- pure relay RTL: every input lands in its first relay / IREG flop, every output is a relay / OREG flop Q;
   rst_n lands in 2 registered stages (qfd_dv_s5_rst2), then the su8 lane reset rl and su_lane rsr (h_rst_n to the lane group).
2. Reach: PASS -- 108 x 216 tile; the parent places it at the suvm <-> lane-cell midpoint (hops <= 405 um).
3. Fanout: PASS -- relay flops drive 1 load each; the reset registers fan out to ~2.1k async sinks through CTS-like
   buffering (synthesis buffer tree); no data register > 32 loads.
4. Depth: PASS -- no logic between relay stages (wires only), no in->out combinational path.
5. Storage: PASS -- no runtime-indexed arrays; delay lines are 1-2 deep (no >= 3 deep chains).
6. Floorplan: pin-bound -- 2,127 signal pins at <= 4.9 pins/um (main) / 4.1 (fallback); util ~5% (WARN, fill_reason
   pin_bound); one full-width std-cell area, no macros; aspect 2:1 (main) / 1:1 (fallback).
7. Clock: single centre-fed root (~2.1k sinks), io_hold_margin 0.03.
8. Schedule: static, 0 added edges.
