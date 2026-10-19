# hcoll_gq_issue_k2_1019 (LEAD-HBM/LH-SU 10-19) -- GQ issue leaf, K source + rebuilt clock leaves

Source: codex/hbm-gqissue-sram-proof-1019 @151a73129 (OT_GQ_FAN32, OT_COLLQ_SRAM, local16 target opt-in) = rg2 kit
geometry, without the rg2 geometric clock helper (bnd_branch.tcl / clock_graph.tcl: its 8-level BUFx24 leaves drove
~300 sinks in SMH rg2 and failed spread 149.5/136.4). CTS: TritonCTS with route.cts_sink = {"size": 16, "diameter_um": 40, "extra": "-sink_clustering_levels 2 -distance_between_buffers 40"}.
Parallel variant: k1 (bind whichever closes first, cancel the other).

Why: s1 gate (4903cd023, ep8 ref_gate/hcoll_gq_issue_sram_1019-20261019-081144) CTS FAIL: max-cap clusters 32 / 144 um
-> boundary pin-flop spread TT 449.4..642.6 (193) / FF ~169 > 80, FF hold -128.5 before repair, 20,331 hold buffers,
SS setup -6.3 ps (rb_lp_data pin regs). On a 432 x 345.6 tile the spread is leaf wiring, not distance
(precedents: qkd_d2d_static unclustered 637 -> 442..508; qkd_astk_ep -distance_between_buffers 40).

SAFE-DESIGN checklist (owner 10-19):
1 Pins: PASS -- every input captured at the pin / every output a flop Q (RTL stage table); reset_landing 2 stages, rst_n x4 copies, relay split <=32.
2 Reach: PASS by geometry -- 432 x 345.6 tile, every path < 405 um; recheck on placement.
3 Fanout: PASS -- mapped census (results/rtl/gqissue_sram_1019/ctl_fan32_1019, netlist e0716f0c) all 24,548 register outputs <=32 loads incl. reset; kept copies (keep_hierarchy + flop-cell keep).
4 Depth: PASS at source -- registered one-hot selects one edge ahead, scale s3->s4 split (r4); physical TT setup measured by this gate.
5 Storage: PASS -- quantiser lines in 8 x ot_sram_1r1w_128x256 SRAM rings (no flop rings); remaining state small fixed control.
6 Floorplan: PASS -- 8 macros on the 43.2 lattice, channels 34.8/45.4 um, full-face pins (IOP 4,032 pins accessible), one std-cell band; fill ~33.6% (low fill kept for macro channels; below 40% is the safe side).
7 Clock: FIXED here -- single centre-reachable root on a small tile with short local leaves ({"size": 16, "diameter_um": 40, "extra": "-sink_clustering_levels 2 -distance_between_buffers 40"}); gate must show pin-flop spread <=80 TT+FF; io_hold_margin 0.03.
8 Schedule: PASS -- static; 0 added data/reset edges vs r4 (local16 target +2 cfg edges/launch priced, owner GQ16 09:45).
