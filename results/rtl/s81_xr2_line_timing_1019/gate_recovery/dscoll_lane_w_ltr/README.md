# dscoll_lane_w_ltr / dscoll_lane_e_ltr -- dsfd_coll_lane_w / _e (S81 collective link lane tiles)

Kit lineage: lt RTL (CH_BOARD 700, LCR 1; S81-LINKTO) on the 10-13 CLOSED cxea3 geometry (HF-3, SRAM M5 edge strip + 5.4 um
halo; E = exact MY mirror of W) + tf forwarded-clock SDC (HF-3b) + S81-SAFE-FIX/COLL (10-19) structural fan-out fix.

## S81-SAFE-FIX/COLL 10-19 (branch claude/s81sf-coll-1019)
Root cause (SAFE-AUDIT-S81 item 3, gate textbook.high_fanout on 1_2_yosys netlist): the single reset synchroniser flop
`u.rst_s[1]` drove 6,837 loads = 939 async clears (515 of them the rx beat landing `lr`) + ~5,750 NAND2/OA21 "hold during
reset" enables, because ot_s81ph_link_ep wrote its frame DATA registers (tp_f, xp_f, p_lo/p_hi/p_got, rr_f, rg_f) inside
async-reset processes without a reset value.  Second net: LCR landing FIFO read pointer `u.g_lcri.u_ski.rp[1]` 4,426 loads.
Fix (RTL parameter SAFE, default 1 on the tile tops, 0 = previous netlist for other users of the core):
- reset synchronised then relayed per consumer: rtl/lib/ot_rst_relay.sv REGIONS 5 (local flags / credit rx / credit tx /
  endpoint / gearbox), kept copies (keep regs hook), release +1 edge;
- rx beat landing: reset only on its flag bits lr[0], lr[513], lr[514]; 512 beat bits plain registers;
- ot_s81ph_link_ep DNR 1: frame data registers in reset-free processes (consumers are qualified by tp_v/xp_v/rr_v/rg_v);
- ot_link_credit_rx RREP 70: read pointer kept per 8-bit slice of the 553-bit landing word (70 x 3 ot_s81ph_keep_ff).
Kit: reset_landing {enable, stages 2} (rs lands at the N face in 2 ck flops), route.io_hold_margin_ns 0.03.
Bench (Verilator 5.050, tools/xdie_s81/kit_bench.sh on the TOKEN-XDIE-S81 vehicle, SAFE tile tops):
pass 1,380/1,380 beats bit-exact, 0 late, 0 timeouts (maxlate -2 vs -3 before = the +1 RTL reset-release edge);
mutants board400 FAIL (late 1,212, 24 timeouts) and chb0 FAIL (late 444, 120 timeouts), identical to the gate_g5 witnesses.
Witnesses: results/rtl/s81sf_coll_1019/.

## Safe-design checklist (owner 10-19)
1 Pins: PASS by RTL (rx -> lr landing flops; lo_v/lo_d -> credit-rx landing v_q/d_q, lo_r registered; li_v/li_d from the
  credit-tx sender flops, li_r captured; tx = registered gearbox beat; flt flops; chb -> ep ch_b_q; tf = forwarded clock).
  Kit pin_regs stay off (reason in spec: +1 cycle per pin would move the measured cross-die landing).  reset_landing 2: FIXED.
2 Reach: tile 432 x 336.96 um; judged by the gate wire_reach check (no relays needed at this size).
3 Fanout: FIXED (reset per-consumer relay copies; data registers reset-free; rp kept per 8-bit slice).  Gate textbook
  high_fanout is the check.
4 Depth: WAIVED-with-reason: textbook estimate u_ep snd -> in_ready ~648 ps / 17 levels (pre-existing); the lt route
  measured TT +31.12 ps on this RTL.  No combinational in->out path.
5 Storage: replay buffer / receive FIFO in 10 SRAM macros.  WAIVED-with-reason: the LCR landing FIFO is 8 x 553 flops
  (4.4 kb), depth fixed by the credit loop and read through 70 local 8:1 slices (RREP); an SRAM would add read latency on
  the core face.
6 Floorplan: outline/macros = frozen CLOSED cxea3 geometry (COORD 0id decision): macros on the 0.432 grid (not the 43.2
  lattice), std cells in several channels, W rx/tx/tf partial-face cluster (6.7 pins/um 10-13 plan) -> coordinator review.
  Aspect 1.28; fill ~0.43.
7 Clock: spine (432 um tile, below the ~1 mm regional-root threshold); pin-flop spread <= 80 TT+FF judged by the --cts gate
  (HF-3b: 28.6 / 32.0 ps); io_hold_margin 0.03: PASS.  15.5k sinks on one root = guidance WARN only.
8 Schedule: static; 0 data cycles; reset release +3 edges (2 landing + 1 relay) handed to MU-DIE-S81 INBOX.
