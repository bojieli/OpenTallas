# hdie_pc_ctrl_mc3c6_s350 (HBM-MC3E, 10-20)

MC3c v6 HBM pseudo-channel controller (release controller; MC3b rejected for ACT starvation), source 272b37645
(qualification c79819972, 833 native receipt aa54e94ad), new compact floorplan. Generator:
tools/hbm_layer_vehicle/mc3e_stack_kit.py s350 (spec derived from hdie_pc_ctrl_mc3c6_p540; same RTL/params/benches).

Geometry: 349.92 x 213.84 um (aspect 1.64), 6 columns; S stacks response[i]/write[i] (cols 0-3), queue/pending, resp_id; N stacks head pairs + post pairs; band y 78.85-133.92 full width. Exact 1229-pin plan in post_iop_exact.tcl / pin_plan.json (data group i over column i on N and S).

Clock decision: clk = die hb_ckgen.pll_hbm (hbm domain, functional 1024 ps JEDEC edges; die PERIOD table stream
833.333 / hbm 1024 / serial 1111.111). Routed and signed off at 833.333 ps (route = sign-off; conservative: setup
slack at 1024 >= +190 ps; hold period-independent). The stream<->hbm crossing lands at the parent station, not here.

## Safe-design checklist (pre-gate)
1 Pins: PASS - every port is a flop D/Q in RTL (pin_regs.reason); reset lands in 2 kept face stages + 3-edge forest.
2 Reach: model PASS - longest planned macro<->face hop ~250 um (t242) / ~190 um (s350); native placed reach from the gate owed.
3 Fanout: PASS - mapped native census (main 042aa171b tool) max dynamic/reset load 32, 39123 cells, 0 offenders
  (receipt aa54e94ad at 833.333); the gate re-runs the mandatory census on this exact kit's synthesis before floorplan.
4 Depth: PASS at source (v6 regional same-edge partition, no added cycle over MC3c); gate TT paths owed.
5 Storage: PASS - 23 p192 SRAM macros, no large flop arrays.
6 Floorplan: fill 36% (WARN band 35-50%), one full-width std band, >=20 um channels, R0 abutted N-S stacks (ref_tile
  abutted_stack; pins W/E only), macro pin faces 3.8 pins/um, boundary <=2.6 (t242) / 1.8 (s350) pins/um.
  DEVIATION: macros are on the asap7 track lattice (at_exact, 0.048 M4 pitch multiples), NOT on the literal 43.2 um
  child lattice: a literal-43.2 layout of 23 macros with >=20 um channels is ~16-18% fill (Codex 388.8 square also
  has 15.66 um N-S channels and fails ref_tile gen) -> coordinator/ROOT decision owed.
7 Clock: W-face entry at the band centre (spine); spread <=80 TT+FF from the gate owed; io_hold_margin 0.03.
8 Schedule: static; +1 post edge over MC3b already priced (DS -0.06 % / Qwen -0.03 %); BW 91.68/92.76/91.70 B/edge.
