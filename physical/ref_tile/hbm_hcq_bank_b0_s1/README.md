# hbm_hcq_bank_b0_s1 (HBM-ELEMOWN3 10-19, H.STA.BLK.17, element ot_hbm_hc_bankq0_static)
Successor of hbm_hcq_bank_b0_1017 (route b0-ring1-47247cc08 CANCELLED: same bank_distance defect as e0 ring1; the 07:30 b0/cb/e0/ca/e2 --cts gates
all FAILED spread 82-155 ps + incremental-GRT stall >4 h). Root cause (L2H-HC, cb_s1 README): the 8 weight SRAMs sat in ONE abutted N-S stack
(pitch 70.512, off the 43.2 lattice) whose E-face pins faced the lane leaves' W faces across a 41.3 um channel.
Redesign = the L2H-HC cb_s1 SAFE geometry (PARALLEL rule: gated alongside cb_s1, whose --cts gate shows trial GRT overflow 0 and CTS
insertion 1146-1194 ps TT on registered pins): 4 abutted SRAM PAIRS on the lane rows (y 43.2/216/388.8/561.6), lanes x302.4/475.2, x-SRAMs
x648 on lattice rows, SRAM->lane pin channel 84.5 um, outline 734.4x734.4 -> 777.6x734.4 (slot_change_request, next die gen).
b0 keeps its own pin plan (descriptor/beat/clk/rst + s_o on E, chain out N, s_i on S with pin_order_desc) and RTL params CPO=1 DRLY=2.
## SAFE-DESIGN checklist
1 Pins: PASS - HH-9 chain pin registers (CPO) in RTL, keep_pin_regs, io_flop_at_pins, reset landing 2 stages.
2 Reach: PASS - tile 777.6 um; every lane sits beside its SRAM pair (row-local); face flop -> face flop chain hops.
3 Fanout: unchanged RTL (b0_1017); the gate lint measures it.
4 Depth: unchanged RTL (bank gate depth ~178 ps).
5 Storage: PASS - weights + x in SRAM macros.
6 Floorplan: FIXED - macros on lattice rows (abutted pairs), channels >= 20 um, pin channel 41.3 -> 84.5 um, aspect 1.06; fill ~47% (cb_s1).
7 Clock: spine port clk; gate measures pin-flop spread (cb_s1 registered-pin span 48 ps TT); io_hold_margin 0.03. Fallback: regional roots per lane-row pair.
8 Schedule: static; no cycle change (DRLY 2 = GEN2d closed ring).
Benches: hc_ring_exact / hc_ring_mut1 (HC_DRLY 2, Verilator 5.050); mut1 fail witness results/rtl/hbm_hc_ring_1019_drly2/ring_mut1.log
(captured ot-epyc5 hcbank-8f47efe11 bench/m1, same RTL).
