# DIE-QC-18-PINILV (2026-10-28, COORD 13:45 approved): QC A0 node a0k6 = a0k3 + per-adder W-face pin plan

Problem (a0k3, AP 0a4950716786, CHECKED review paths_tt_setup.txt): TT setup -221.66 ps, worst u_w.q[828] -> g_add[9] x_swap,
CLK->D 976.6 ps; the a/b pin bands (a 10.9-110.2, b 111.5-210.8, y 312.5-411.8) put each adder's A1 inputs 73-174 um apart.

Fix (opt-in, RTL unchanged, 0 cycles): recipe `ot_qwen_tile_node_ilv` (suffix a0k6) = the a0k3 recipe + `pins_file`
`node_pins_ilv.json` (tools/mkpins.py): W-face group p = a[32p+:32] | b[32p+:32] | y[32p+:32] (96 pins, 0.192 um pitch on the
M4 track grid, 18.4 um per adder); adders 0-9 from y 10.908 (to 195.036), va 195.228, adders 10-15 from 312.492 (to 422.892).
t_out/t_vout (211.4-311.3), vy 311.916, E face, clk centre entry unchanged. core_pin_sites_gate PASS (0 dup/pitch).
Plan tree: core_family_slice.py run (family a0node, --fit results/model_refit3_1026/uf_phys3_v1.json, INVBUF TT/FF libs); the
same args reproduce the committed a0k3 slice and plan_d1 byte-identically (CHECKED). New census 12102 sinks -> slices_ilv:
2,2,8,8, 8 stages, 587 cells, 256 leaves, leaf spread 11.92 um, PLAN TT 250.12 w13.96 / FF 189.22 w11.42 (UNCHECKED, plan model).

Kit intel2:/srv/opentallas-scratch2/claude/die-qc18-1028/pinilv/kits/ot_qwen_tile_node_a0k6 (kit_hash b5747b9451d162bd).
CHECKED: KIT_PREFLIGHT PASS 0 issues; placed rc 0: RTL_LINT PASS, SELRANGE PASS, FACE_GUARD 2565/2565, LEC EQUIVALENT 14420/14420.
AUTO-GEOM on 3_place (geom_check.sh --all-kits): FAIL on the same contract items as a0k3 only (aspect 9.09, pin_reg_p90 42.17 =
t_out TOREG ft, partial_face E); col_v 0.538 ok (a0k3 1.584 FAIL), r2r max 240.2 (a0k3 378.8), GRT 0 ov, clock_reach 11.2.
Render viewed: uniform fill, W pins full length (small gap 195-211 at the va / ft boundary), E pins 192-311, centre entry.

Placement-parasitics setup probe (TT, propagated plan tree, CHECKED probe/): a0k6 WNS +65.70 (kit setRC_rcx + 3_place.sdc),
+57.95 in the FLOW-GEN-2 form (stock setRC + constraint.sdc) vs FG2's a0k3 -50.5 (fg2-1028/rbprobe/probe.log): ~+108 ps;
0 violating endpoints, no x_swap endpoint within 100 ps. Routed TT result: autopilot row (see lane line).

Parent track check (parent_check/, estimate, no rebuild): A0 nk 3_place traced node a/b/y (every 4th bit) -> parent face
register -> port buffer: 307/372 port buffers south of the node (median parent y 599, node 688.7-1120.7). Max cut 1228 nets
(x4) at the node south end in BOTH plans (demand-neutral at the bottleneck); along the strip +3..+8 % at local y 50-125
(e.g. 948 -> 1024 at y 100); total vertical port->pin length +2.6 % (400157 -> 410533 um, x4). The parent port places are
place_pins placeholders (UNCHECKED vs plan). The parent's provisional node LEF keeps the a0k3 band order: adopting a0k6 needs
the A0 parent to read node_pins_ilv.json (parent nets re-route, same bit count).
