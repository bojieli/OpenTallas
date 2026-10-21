# qfd_tt_head_static_h16s -- safe32 TT head leaf with SEG_CAL (TOK.QW.LAYER.3.SEG), QW-ORPHANS 10-20

Source: Codex bound_r3 (codex/qw-head-safe32-1020 94a0cffc1 + its 02:12 WIP, copied verbatim) =
results/rtl/qw_head_safe32_1020/bound_r3/native32_param.v (+ native32_helpers.sv): STAGE_ME=1, SEGCAL=1,
generated from the safe32 head RTL (FIFO 4x560 FF -> SRAM, regional reset leaves, bounded copies; zero added edges).
Not critical (critical_tiles.txt). Successor of h16c (closed head stays bound until this one closes + parent rebinds).

## Proofs carried
- default-OFF intake: whole-head equivalence PASS (results/rtl/qlb_c4b_1018/lmh_cal/closed_equiv/wholehead_1020).
- bound_r3 on V5.050: img0 PASS 123/123, imgh PASS 131/131, BMUT3 FAIL 129/131 (witness bench_witness/bench_h16s_bmut3.log);
  random hardware init seeds 1/17 PASS 131/131 (results/rtl/qw_head_safe32_1020/bound_{parent,random}_r3).
- NOT yet: formal equivalence native32 vs safe32 RTL (benches only).

## PRE-GATE native census (ORFS synth-only, RVT TT, mapped sha c4da447f...; HAND_BACK_NATIVE_boundr3.json)
- roots 48012, max dynamic loads 32 (limit 32), 0 violations, 0 role errors -- reset nets included. PASS.
- synth area 41871.76 um2 (macros 33051, std ~8820; seq 2478.6); FF 6481 generic.
- constant output: me_clk_en = 1'b1 (TIEHI). CONTRACT = CONSTANT: identical to the closed source
  (ot_qwen_rom_core_ctrl_static.sv:1222 assign me_clk_en_w=1'b1; static schedule, no ME_STALL clock gate); kept as a port for
  parent interface compatibility; consumers (qfd_tt_ctlm_b2 mee/mer) see 1. Not a tied functional INPUT.

## SAFE-DESIGN checklist
1 Pins: flow pin registers ON (as h16c, +0 cycles vs h16c); rst_n lands in 2 stages in source (u_0 D=1 -> u_1, then
  <=16-load reset leaves). PASS (h16c inherited raw RSTN1 retired).
2 Reach: no single-cycle wire >405 um expected (outline 345.6x302.4; macro-to-pin <~300 um); gate wire_reach measures. PENDING gate.
3 Fanout: census max 32 incl reset. PASS.
4 Depth: unchanged edges vs closed head; gate logic_depth/TT timing measures. PENDING gate.
5 Storage: FIFO (4x1024 b) -> 6x ot_sram_1r1w_32x128_m1 (2 of 8 RTL banks dropped by synthesis: unconsumed bits);
  programme store 2x ot_sram_1r1w_64x512_m1_r2c2. PASS.
6 Floorplan: ALL 8 macros on the 43.2 lattice (h16c x22.464 / y121.008 retired): 64x512 MY at (129.6,43.2),(129.6,172.8);
  32x128 MY column x=43.2, y=43.2..259.2 pitch 43.2. Pin faces (W/E) channels: 41 um (W edge), 35 um (32x128 E -> 64x512 W),
  42.5 um (64x512 E -> tile E face); N/S non-pin gaps 22.4 / 51.8 um (>=20). Full-width std band y 2.16..43.2 (S pins).
  Aspect 1.14. Fill 40% = (33051 + 8820)/104509: WARN, lattice+channel bound (a 6-small + 2-big column pair is the
  smallest legal arrangement found; tighter options break the >=20 um rule or the lattice). Waived-with-reason, not squeezed.
7 Clock: multiple_cts_roots leaf: ck_head (core, ~6.5k FF), ck_pm0 (5 SRAM sinks), ck_pm1 (3 SRAM sinks), same PLL fixed
  phase. CHANGE vs h16c: ck_pm0/ck_pm1 were raw direct entries to one SRAM each; the RTL now puts 4+2 FIFO SRAMs on them, which the
  one-instance direct-entry API refuses, so they are CTS roots here. Parent must compensate per root (pin-flop spread
  <=80 TT/FF judged at gate + parent). io_hold_margin 0.03. PENDING gate.
8 Schedule: static, 0 added edges (cycles_added 0). PASS.
