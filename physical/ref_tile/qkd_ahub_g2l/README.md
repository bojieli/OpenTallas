# qkd_ahub_g2l (KV-AHUB3 10-19) -- gate l1 on 9ffb16f94: FAIL (clock_rule), terminal for this kit form
Gate: PRE_ROUTE_GATE FAIL (1 fail, 14 warn); trial GRT overflow 0; fill 37% (std 7,220.7 um2). PNGs inspected: gate_layout/floorplan.png, density.png.
clock_rule (pin-flop / child-pair spread, limit 80):
- ck_c: 11,690 flops over the whole 730 x 536 outline (textbook.clock_domain WARN); TT insertion 1029.7, soft 686.8..1029.7 vs u_recip
  655.6..674.3 -> 374.1 TT / 331.4 FF.  Cause (density PNG): the core logic mass sits in the W half between the Z trees, while the
  core region also owns the E-face ap2/ap3/am2/am3 pin flops (x 734) and the W-face ap0/ap1/am0/am1/fr pin flops (x 0): one root
  over 734 um of pin flops -- the single-region core is still the full-width band.
- ck_z0..3 (813 sinks each): soft vs u_zh 120.7/96.4, 109.5/85.3, 160.0/137.7, 185.9/161.3 (TT/FF): the region trees are not
  insertion-aware (Z pin tapped at the same depth as the soft flops; zh internal 328..366 vs soft up to 523) and the zo write rings /
  reset leaves drift toward their core-side readers.
Safe-design checklist vs this gate: 1 pins PASS; 2 reach PASS (GRT 0, landed legs); 3 fanout PASS (no high_fanout FAIL);
4 depth not judged (gate stopped at clock rule); 5 storage waived (landing rings); 6 floorplan PASS (a7 geometry, lattice waiver
zh0/zh1 43.224); 7 clock FAIL (above); 8 schedule PASS (HUB_RECIP/PUB +6, priced).
Next structural step (fresh agent): (a) split the core region into io_w / core / io_e regions (W stacks + fr, E stacks) with landed
ap/am crossings (AP_OFS / am lag re-priced in KV-GEN9) or move the core mass to the centre beside recip; (b) region trees with
insertion-aware child taps (spine per region, ot_ref_child_ins) so each Z pin is tapped ~246 ps early; (c) region placement
bounds (landing write halves beside their source, read halves beside the reader).
