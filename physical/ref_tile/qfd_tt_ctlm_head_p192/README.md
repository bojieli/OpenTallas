# qfd_tt_ctlm_head_p192 (QW-SRAM3 10-19, INF.SRAM real-parent gate)

Unchanged closed `qfd_tt_ctlm_head` RTL/params/pins; both 64x512 program SRAMs bind the successor
`ot_sram_1r1w_64x512_m1_r2c2_p192_mir` (171.288 x 153.912 um, W/E 793 pins at 0.192 um = 5.21/um; old master
171.288 x 77.76, 10.2/um) through `rtl/lib/sram_p192_1019/ot_sram_1r1w_64x512_m1_r2c2__p192.sv` (same ports,
behaviour and read latency). Generator `tools/mem_compiler/build_qw_p192_1019.py` (recipe of bb61ae67c).
Liberty adds the M4 pin-lead RC: TT clk->q 365.6 -> 408.8 ps, min period 434.6 ps (< 833).

Safe-design checklist (10-19):
1 Pins: RTL already registers every port at the face (io_flop_at_pins cols 4, inhold/outhold); pin_regs opt-out recorded (unchanged closed contract). Reset landing: unchanged head reset (waived, SRAM-only change).
2 Reach: gate wire_reach lint (macro stack 308 um tall; pin regs at faces).
3 Fanout: unchanged RTL; gate high_fanout lint.
4 Depth: unchanged RTL; SRAM CQ +43 ps TT is inside the measured margin (gate/route confirm).
5 Storage: program store in SRAM macros (this change only fixes their pin access).
6 Floorplan: macros x=43.2 (lattice), abutted N-S stack y=43.2/197.136 (no N/S macro pins); W 43.2 um pin channel, E 44.7 um full-height std band; macro faces 5.21 pins/um; 259.2 x 388.8 (aspect 1.5); util from gate synthesis.
7 Clock: unchanged spine (closed head 33.3 ps spread); gate --cts measures TT/FF pin-flop spread <=80.
8 Schedule: zero added cycles.
