# hbm_su_qcore_r14b_1021 -- qcore r13c RTL, structural floorplan redesign after the r13c --cts gate FAIL (HBM-QCORE10, 10-21)

RTL unchanged from r13c (ot_hbm_su_static_qcore_r13 @8ea344306; native census PASS max 32; benches 5.050 PASS / mutants FAIL,
results/rtl/hbm_qcore9_1020). Kit-scoped SYNTH_CANONICALIZE_TCL = this kit's synth_canonicalize.tcl (r13 copy, kit path only).

r13c gate (ref_gate/hbm_su_qcore_r13_1020-20261020-232047): synth/CTS fine (setup +22 ps, spread TT 58.8 / FF 53.5) but trial GRT
overflow 155 (M4 99, M2 53), max 1 track over. Classification:
- outline/util: NOT the cause (std density 32% of placeable).
- tile pin density: NOT the cause (W 3.6 pins/um, E lower).
- macro fragmentation (cause): the two SRAMs in the middle rows (y43, y173) split the std-cell area into three bands; the 43-um band
  under u_red.mb carried E-W sector traffic (sectors 0-4 mixed) and overflowed one M4 track at x155-163 down to the S edge; plus
  cap-0 gcells at the SRAM W/E pin faces (410 M4 pins per 41-um face, 10 pins/um, halo 5.4).
Fix: S stack (fallback): u_red.mb (86.4,23.76) + u_red.ma (86.4,64.8) abutted, 21.6 um over the pin-free S core edge; logic band y112-279 directly under the centre N clock pin. One contiguous std-cell band; macro W/E pin-face halo 10.8 um (2x pin-escape zone), PD 0.45 -> 0.38.
Outline (exact 280.8^2 d4g slot), pin faces and ports unchanged: no die change.

SAFE-DESIGN checklist (owner 10-19; guidance under the 10-20 rule freeze):
1 Pins: PASS -- keep_pin_regs/io_flop_at_pins; reset lands 2 stages, 24 landing copies.
2 Reach: PASS -- 280.8 um tile, every path < 405 um.
3 Fanout: PASS -- native census max 32 (r13c netlist; RTL unchanged).
4 Depth: r13c gate worst reg->reg +22.3 ps at TT placement (pretree l1 ~640 ps est, WARN only).
5 Storage: WAIVED (rule freeze) -- 8,192 b flop RF in 8 sector modules (1 kb each); reduction lines in 2 SRAM macros.
6 Floorplan: FIXED -- SRAMs as one abutted N-S bank (bare touching faces), 21.6 um from the core edge, pin-face halo 10.8; one
  full-width std-cell band; util ~0.32-0.36; aspect 1:1.
7 Clock: single centre-N root (r13c measured spread TT 58.8 / FF 53.5 <= 80); io_hold_margin 0.03.
8 Schedule: static; 0 edges added (RTL unchanged).
