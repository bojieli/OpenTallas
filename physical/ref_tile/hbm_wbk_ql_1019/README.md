# hbm_wbk_ql_1019 -- d4g wbk_<q> x4 (ot_hbm_svc_wb_kport_q), per-domain RTL reset landing

Successor of hbm_wbk_q_1018 (LEAD2-HBM/L2H-WBK, 2026-10-19, RELEASE_TREE H.STA.BLK.5).

Why: the 1018 gate hung 22 h in synth_odb (old OT_GF crossing search, fixed on main 70ff321ae) and was killed. The
regate with main tools (e00856000) FAILed floorplan_run `OT_MULTI_ROOT: input hbm_rst_n has wrong domain for
hbm_rst_n__ot_rl0`: the kit reset landing (ot_pin_regs.tcl OT_RST_LAND) supports ONE landing clock and landed both
stream_rst_n and hbm_rst_n on stream_clk, while hbm_rst_n belongs to hbm_clk.

Fix (RTL, structural): ot_hbm_svc_wb_kport_q lands each reset at its face in two plain registered stages on its own
clock -- stream_rst_n: srst_l0 -> srst_l1 on stream_clk; hbm_rst_n: hrst_l0 -> hrst_l1 on hbm_clk. The landed resets
drive every reset in the tile (the top's async-reset flops, the 16 K pin skids, u_wb). The cross-domain reset
combination is unchanged inside u_wb (reset_both -> per-domain ot_reset_sync: asynchronous assert, release through
its own 2-stage pipe; the reviewed-gray-FIFO policy admits a cross-domain async control only into an ot_reset_sync
pipe stage). Kit `reset_landing` is opted out with that reason. Same floorplan, macros, pins and data paths.

A tool-side variant (per-port landing clocks in ref_tile / ot_pin_regs) was NOT built: main (f77a3184a)
reset_landing_plan takes one clock only, and the shared helpers are ROOT-owned.

Benches (Verilator 5.050, ot-epyc5, commit 0a4e769c1 RTL; results/rtl/rbh_stk_1018/wbk_ql_1019/):
wbq_e / wbq_w / wbq_e_wopen PASS (8 blocks, 5,563 sectors, 8 lockstep windows vs the GEN0 master);
4 mutants (quad, span, premature, ksaddr) rejected with WB_INTEGRITY (committed fail witnesses);
wb_default (GEN0 kshare 4/4 QUALIFIED + cutthrough CDC bench incl. mutant) PASS.

## SAFE-DESIGN checklist (owner 10-19)

1. Pins: PASS (fixed). Every pin is registered in RTL (stream pin flops, flop outputs, one hbm_clk skid per K port;
   kit pin_regs opt-out with reason). Each reset lands in 2 registered stages at the face ON ITS OWN DOMAIN (this
   change); each reset port net has one sink.
2. Reach: measured by the gate. Pin-bound slot 777.6 x 518.4 (exact die sub-slot); stream logic sits between the S
   face and the 4 SRAM columns, K skids at the N face. clock_span WARN (777 um root): per-root trees
   (stream_clk, 4 stream_fifo_clk roots, hbm_clk), each over its own region.
3. Fanout: PASS. Data cones unchanged from the 1018 review; landed resets: srst_l1 ~200 async loads + 6 reset-sync
   pipes, hrst_l1 ~50 loads, built as an equal-depth tree from a register (no port-driven reset tree).
4. Depth: PASS (unchanged): fold = 2 XORs before each K skid; window base/span in 2 registered stages; no
   combinational in->out.
5. Storage: PASS: 32 payload SRAMs (ot_sram_1r1w_128x256), no runtime-indexed flop arrays beyond the 2-entry
   reservation receipts.
6. Floorplan: PASS with recorded waiver: 4 abutted 8-high SRAM columns, column origins on the 43.2 lattice (x 86.4 /
   259.2 / 432 / 604.8, y 86.4; stacked at the macro height 41.04 on pinless N/S faces). Macro W/E faces carry 10
   pins/um (intrinsic to the macro); channels between columns are 78 um (172.8 pitch), 2.4x the 32 um k9 channels
   that stalled. One full-width std-cell band; aspect 1.5:1. Util measured by the gate.
7. Clock: regional roots per domain (stream_clk / stream_fifo_clk[0..3] / hbm_clk), crossings through the reviewed
   gray FIFOs + level synchronisers; gate runs --cts for pin-flop spread <= 80 TT+FF; io_hold_margin 0.03 (was 0.025 in
   1018) and route hold margin 0.03.
8. Schedule: PASS. Static; no credits on the on-die DMA side (K-port ready is the HBM off-die boundary). Added cycles:
   reset assertion/release +2 edges per domain (scheduled constant, reset_release_cycles 2); no data latency change.
