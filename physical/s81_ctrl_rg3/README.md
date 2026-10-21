# s81ctrl_rg3 / s81ctrl_rg3s: dsfd_ctrl_rg3 hard kits (DRIVE-S81-IDX4-KITS, 10-20; MU.BAL.SX.3, mu7i4 die)

dsfd_ctrl_rg3 = the closed n32s controller (dsfd_ctrl_rg2 under S81CTRL_SRAM_FIFO + S81CTRL_SRAM_P192 + S81CTRL_NATIVE32,
2 x ot_s81ph_ctrl_pcr, 4 x 16x340 dual-clock SRAM FIFOs) PLUS the static-slot client face of the non-inline index reader
dsdv_idx_rg3 (rrq 92 b in, rrd 544 b out; landing FIFO 24 x 44 b a PC in flops; return demux on the reader tag range).
Kits are ref_tile gen of spec_rg3.json (main) / spec_rg3s.json (parallel fallback); everything except the top, the
sources and the pin plan is the n32s kit (outline 388.8 x 324 = the die ctrl-view slot, same macro origins, K8 clock
split + hclk split hooks, reset landing 2 stages).
- main s81ctrl_rg3: N face re-pinned per PC half (PC0 rq rd rrq rrd | clk ck_o | PC1 rq rd rrq rrd), 1,884 pins on
  4.5-384.3 um = 4.96 pins/um alternating M3/M5 tracks (dsfd_ctrl_rg3_n_pins.tcl, gen_pins.py mode n). S / W = n32s.
- fallback s81ctrl_rg3s: every n32s pin unchanged; rrq/rrd of PC0 on the W face, PC1 on the E face (M4, 318 pins a face,
  ~1/um; dsfd_ctrl_rg3_s_pins.tcl, gen_pins.py mode s).

SAFE checklist (pre-gate):
1 Pins PASS: rrq lands in flops at the pin, rrd leaves flops (RTL); svc rq / rd / PHY faces = n32s; reset_landing 2 stages.
2 Reach PASS (verify post-GRT): outline unchanged (half-perimeter 712.8 um); new lanes are face flops.
3 Fanout PASS: pre-gate native census (results/rtl/s81_idx4kits_1020/native_ctrl3s, kit defines, SRAM bb, ot_keep_regs
  hook, textbook 32/405): hf_max_net 0 / hf_max_reset 0 / hf_max_port 0 (no driver > 32); only refusal = reset_landing
  4 sinks, which the flow's reset_landing fixes (as n32s). 6,583 FF (n32s 2,956), 4 SRAM.
4 Depth PASS: census depth 338.4 ps / 10 levels; move decision = AND of 3 registered flags.
5 Storage PASS: landing FIFO 24 x 44 = 1,056 b a PC in a flop ring (< 2 kb); the 4 FIFOs > 2 kb stay SRAM.
6 Floorplan PASS/WARN: n32s macros 2x2 on the 43.2 lattice, mid band 50.5 um; fill 39% (std ~3,000 um2 estimate from
  the FF ratio; macro-dominated WARN as n32s 38%); aspect 1.2; N face 4.96 pins/um (<= 6) main.
7 Clock PASS (re-measure): K8 regional core roots + hclk split unchanged; io_hold_margin 0.03.
8 Schedule PASS: reader request +s+3 controller edges, response +s+1 (priced by S81-CAL, lanes/S81-IDX3R.md).
Benches (closure loop, Verilator 5.050): ctrl3_ctrls PASS (tb_dsfd_ctrl_rg3_mux, rg3 vs record rg2 bit-identical +
reader traffic, kit defines), mutants cms1-4 FAIL; witnesses results/rtl/s81_idx4kits_1020/witness/.
