# DIE-KV-36 KV-022: sys_SD / sys_SD_v1 OT_CLAND groups off the PHY macro (fix-only delta)

Cause (CHECKED): the event26 sidecar `collector.types[T].tree` was composed before the x6 PHY abstract
(ot_qfd_serdes_112g_x6_phy_w522 @ 17.28,54.0 size 1848.96x972) existed: 17 taps, 25 relays on the macro
(e.g. u_cland_collect_rst_n_t10 @ 1702.08,406.08). The current reset tree (`reset_tree.for_type` on the
current plan, macro = blockage) has 69 relays, 15 taps, depth 5, max hop 376.2 um, 0 relays on the macro.

Delta (`mk_sd36.py`, no new check kinds): collector tree := current reset_tree.for_type tree; each local
source re-tapped to the nearest current rst_n_t* (<= 405 um); asserts collector depth <= boot budget.
- Variant A: i_host_fdi -> t13 (279.9 um), i_host_link_rst_n -> t5 (124.2 um); max hop 361.5; depth 6 (was 6).
- Variant B: both sources -> t5 (337.8 / 124.2 um); max hop 354.2; depth 6.

Results (CHECKED): strict bind A/B errors 0 unbound 0 undriven 0 multiply_bound 0; kit-rtl + PHY specialize rc 0;
gen phys rc 0; KIT_PREFLIGHT PASS issues 0 (4 kits); OT_CLAND groups on macro+halo: 0/25 (A), 0/15 (B).
Place: epyc2 kits{A,B}/<T>, `run_kit.sh <T> cts 24 8` via ot-run (port_bind = in-flow face_guard pre-floor).

Not done (UNCHECKED): die_islands_um (46 clock + 105 relay die cells over the macro) are tile blockages only;
siting those die cells off the macro needs the die clock tool rerun with the macro as blockage (die-plan item).
Files: var.sh (bind+kit-rtl), gen.sh (gen phys+preflight), sd36{A,B}_delta.json, recipe_kv27f_sd36{A,B}.json,
bind_report_{A,B}.json, preflight_{A,B}_<T>.json, probe_tree.py.

## Iteration 1 place result (A/B, 16:20-16:33 PDT 10-29, epyc2)
All 4 kits failed 3_3 GP: `OT_CLAND no legal nonoverlapping row/site in reserved band for u_cland_collect_rst_rl_12/_4_`.
The PHY-macro failure (rst_n_t10) was gone. All windows were checked against all bands (CHECKED). The only
dense-band hit is rl_12 (window 1877.04-1881.36 x 179.28-183.60), which lies inside ring:i_host_fdi (1872.72-1883.52 x
17.28-436.32, ~7.1k cells). The other windows share small raw-copy windows only and placed fine.
Routing the collector path around rl_12 does not work: south of t5 the only path is the E rim (macro+halo to x 1870.56,
core edge x 1896.48), and every alternative hop is >405 um (t5->rl_11 709 um; i_host_link_rst_n->t13 ~518 um).

## Iteration 2 (fix-only window move, `patch_win.py`, launched 16:38 PDT)
Free strip x 1883.52-1896.48 at y 150-215: 0 face flops / cland cells (CHECKED from ot_face_flops.txt).
- V1 (A state): rl_12 collect + raw-copy windows -> 1885.68-1890.00 x 179.28-183.60 (center +8.64 um; hops ~363 um, depth 6).
- V2 (B state): rl_12 windows -> whole free strip 1883.52-1896.48 x 179.28-183.60.
Result (CHECKED): all 4 (V1/V2 x SD/SD_v1) PASS 3_3 GP + 3_4 + 3_5 DPL -> 3_place.odb; OT_CLAND 12308/12290/12278/12260
cells FIRM, preserved through DPL. Units oth-ubuntu-2394388/2394367/2394377/2394368-1793317063.
CTS then fails on all 4: `cts.tcl, 6 clock landing export endpoint missing`. landing_exports.tcl does findBTerm on the
scalar `fclk_out_o_serdes_W_rx_flit` / `_tx_up`, but the netlist declares `output [0:0]` (bterm probably `...[0]`).
This is a landing-export generator mismatch, not a place issue.
AUTO-GEOM on V2 SD_v1 3_place (absolute rules, --all-kits, GRT probe skipped after a 900-s timeout): FAIL
pin_unreg 530, r2r 2551 um, r2r_count 3433, partial_face 1, channel_h/v, col_v, clock_reach 2038 um, clock_tap_sinks 5756.
Render viewed (iter2_V2_SD_v1_3_place_auto_geom.png): logic is packed in the SE corner (x~1450-1870, y<54) + E rim;
clock entries clk/clk_t1/clk_t2 sit on the S rim far west of the logic. The worst sink at (1897,870) is driven from clk @ (190,22).
This is a tile clock-entry/plan item for the die owner, not a collector item.
