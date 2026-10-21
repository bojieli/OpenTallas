# hbm_su_qcore_r10_1020 -- qcore r11 RTL (r10 + driver copies) in the r6n outline (DRIVE-HBM/HBM-QCORE8, 10-20)

RTL: Codex ot_hbm_su_static_qcore_r9 (codex/hbm-qcore7-native32-1020 @779bb7be3, merged into claude/hbm-qcore8-1020). Same ports/edges/function as r5/r6n.
Main path = r6n (gate WARN 0 fail, regated with current main tools); first of r6n / r9 to CLOSE binds, cancel the other.
Benches (Verilator 5.050): r9 lockstep vs r5 PASS checks=9104 (all outputs every edge), MUT256 FAIL errors=12150 (Codex witnesses);
pre-tree on r9 (su_pretree_r9_run.sh) m0 PASS / m512, m1024 FAIL (witnesses results/rtl/hbm_qcore8_1020/).

SAFE-DESIGN checklist (owner 10-19; guidance under the 10-20 09:35 rule freeze):
1 Pins: PASS -- pin registers on (keep_pin_regs, io_flop_at_pins); reset_landing 2 stages (main ot_pin_regs OT_RST_LAND).
2 Reach: PASS -- 280.8 x 280.8 tile, every path < 405 um.
3 Fanout: r11 FIXED in RTL -- r9/r10 roots >32 split with kept DRIVER copies (sector hit predecode + 2 row/COLL copies, pretree per-byte mode/valid copies, rc_x one-hot x4, reducer wsel x2); residual = ot_hdc_fp32_add_lat internals.
4 Depth: FIXED in r6 RTL -- per-sector one-hot last-writer decode and k+1 read registers gated by sector match (r5: one shared read cone, -314 ps).
5 Storage: WAIVED (rule freeze) -- 8,192 b runtime-indexed flop RF in 8 sector modules (1 kb each) -- sector storage 8 x 4 x 32 b per sector (<2 kb each); reduction lines in 2 SRAM macros.
6 Floorplan: PASS -- 2 SRAMs on the 43.2 lattice, outline = closed d4g slot 280.8 square (aspect 1), util ~0.3 (pin-bound W/E faces 3.8/1.9 pins/um); regions removed (DPL crash).
7 Clock: single centre root on a 281 um tile; gate must show pin-flop spread <= 80 TT+FF; io_hold_margin 0.03.
8 Schedule: static; r6 adds 0 edges over r5 (conflict-fault lag <= 2 edges recorded in the HH-11 bench).
