# qkd_kvs_pc_h_sr9 (KV-PC7 10-20, SAFE successor of qkd_kvs_pc_h_sr8)

Floorplan: die-frame sub-slot 267.84 x 300.24 (exact, pin-bound faces), 23 native ot_sram_1r1w2c_32x64_m1 banks; column A banks mirrored (MY) at x=43.2 (= sr8).
Source claude/kv-pc7-1020 (tools/qwen_kv_die/kv_pc_sram_gen.py TIM_PC7 / UCTL_PC7 / sr_tile reset landing; kvpc_sram_kit.py N9).

Why: gates *-20261020-054430 (sr8): textbook REFUSE reset_landing (rst_n / hrst_n each 9 RESETN: s1 + 8 s2 copies) and
logic_depth 895 / 942 ps; PRE-CTS full stage graph 493 pairs > 405 um (all N <-> S boundary feed-throughs, Codex 29ec0814c).

## SAFE-DESIGN checklist
1 Pins: PASS (RTL pin stages, pin_regs.json reason unchanged); reset lands in 2 registered stages per domain:
  the port clears two KEPT first captures (s1 data, s1r clear), the 8 kept second-stage copies clear from s1r and
  capture s1 -> 2 RESETN loads per port (textbook r2: rst_n 2, hrst_n 2), release still edge 2 (tile lockstep PASS vs
  the 2-stage original; mutant 8 = one-stage landing FAILs).
2 Reach: fixed by pin order: N = o_next [2.16,52.16] | o_grp_h | pc__fo | i_next [55.08,187.08] | x__est | pc__ki | i_grp |
  i_grp_h | o_grp, so i_prev -> up_q -> o_next and i_next -> o_prev run straight N-S (model on the sr8 placement: 0 pairs
  > 405, max 376.0 um); to be confirmed on this gate's placed ODB.
3 Fanout: native census r2 (pve1 091431) PC_H PASS max 32 / 0; PC 1 x 33 (j[9]) -> r3 j 2-copy family; this gate's
  census is the receipt.
4 Depth: r2 textbook 592 ps PC / 592 ps PC_H (was 895 / 942): exact scheduler restructure (no constant twin leaves,
  registered static-row match + open lookaheads, s_pblk direct branch term, !s_go in the last rd_ok / wr_ok gate,
  k1v / write-queue / command-FIFO lookahead per late-select case).  No added edge.
5 Storage: PASS (23 SRAM banks, unchanged from sr8).
6 Floorplan: macros on the 43.2 lattice; util ~34 % waived (pin-bound die frame, fill_reason in spec); pins <= 6 / um.
7 Clock: sr8 pc_h measured ck TT 76.0 / FF 73.2, hck 63.0 / 58.2 ps spread (<= 80); io_hold_margin per kit.
8 Schedule: static, no credits; 0 added edges (reset release edge unchanged).

Benches (Verilator 5.050, 20000 edges, lockstep vs the original modules): results/rtl/qwen_kv_die/kvpc_sram_sr9_1020/.
