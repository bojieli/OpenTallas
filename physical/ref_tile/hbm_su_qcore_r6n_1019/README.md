# hbm_su_qcore_r6n_1019 -- qcore r6 RTL without placement regions (LEAD2-HBM/L2H-SU, 10-19)

Predecessors: route hbm_su_qcore_r5_1017-r5-1a1108053 NEEDS_RTL TT -314.4; r6 kit (claude/hh11-qcore6-1019 @c663070f1, sector
storage + gated k+1 reads, PRETREE 1) gate 10-19 01:45 FAILED: (a) textbook.reset_landing rst_n 121 unlanded sinks (worktree
ot_pin_regs.tcl predated OT_RST_LAND; main tools land it), (b) cts_run: DPL crash "detail_place.tcl, 42 bad optional access" from
the INCLUSIVE sector_regions.tcl region groups, so no CTS/GRT. r6n = same RTL/outline/pins, NO pin_hook_before_flops regions,
tools/common_flow from main. Benches: r6 witnesses (results/rtl/hbm_su3_1017/qcore_r6_{pos,mut256}.log, su_pretree_1018/qcore_r6_m*).

SAFE-DESIGN checklist (owner 10-19):
1 Pins: PASS -- pin registers on (keep_pin_regs, io_flop_at_pins); reset_landing 2 stages (main ot_pin_regs OT_RST_LAND).
2 Reach: PASS -- 280.8 x 280.8 tile, every path < 405 um.
3 Fanout: FIXED in r6 RTL -- 8 kept sector modules each with raw writer copies / read-addr copies per (class, half); census owed on the gate netlist (hf_report 32).
4 Depth: FIXED in r6 RTL -- per-sector one-hot last-writer decode and k+1 read registers gated by sector match (r5: one shared read cone, -314 ps).
5 Storage: PASS -- sector storage 8 x 4 x 32 b per sector (<2 kb each); reduction lines in 2 SRAM macros.
6 Floorplan: PASS -- 2 SRAMs on the 43.2 lattice, outline = closed d4g slot 280.8 square (aspect 1), util ~0.3 (pin-bound W/E faces 3.8/1.9 pins/um); regions removed (DPL crash).
7 Clock: single centre root on a 281 um tile; gate must show pin-flop spread <= 80 TT+FF; io_hold_margin 0.03.
8 Schedule: static; r6 adds 0 edges over r5 (conflict-fault lag <= 2 edges recorded in the HH-11 bench).
