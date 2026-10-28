# INFRA-FIRST-QC-R32 (2026-10-27 16:20-17:25 PDT): clock export pin-window allotment, dry16, per-bit FT pin model

Base: claude/qc-infra-r31-1027@c34041d80b (exact dry14/dry15 builder + R31 trunk_escape). Export inputs = Codex
model_band8w (8w band export, R26/R8 lineage); baseline re-export with this source is BYTE-IDENTICAL to the dry14 spec
(sha c10a2615..., own run exp0). Dry builds: event plan = R31 dry15c plan.json (event_n100_ft_leg), builder snapshot
src_r32a (= c34041d80b builder), OT_V2_COLLECT_PLAN_ERRORS census. Data: intel2:/srv/opentallas-scratch2/claude/qc-infra-r32/.

## 1. Root cause of dry15c 1,179 (own census, CHECKED from the dry15c error list + spec)
Each tree edge is one shielded piece from the driver Y pin; every horizontal piece and every M9 driver jog needs a track in
the driver island pin window (+-2.455 um). By driver composition (failing / all drivers):
top x-tree node 2x M8 16w + M8 8w band feed 271/271; same + M9 8w band feed 96/189; 2x M8 16w alone 23/253; anchors with
vertical top legs (M9 16w x2 + 1..5 band feeds) 0 failures. I.e. band feeds anchored on top x-tree nodes (whose window
already holds the parent L landing + two horizontal 16w kids) cannot fit.

## 2. Export fix (opt-in, default output byte-identical; tools/die_plan/qc_clk_mesh3.py band_trees)
--a0-band-window N: count horizontal top-tree pieces per anchor (kid legs + parent landing) + band feeds already allotted;
a feed whose best anchor would exceed N moves to the best other anchor level (same equal-levels rule, same cells/stage
count, no trims) if its worst TT/FF match loss <= --a0-band-window-tol ps. --a0-band-col-dx (band y-tree column offset)
also added; tried, worse (below). Export summary carries the band_trees stats only when an R32 option is set.
| export | moved feeds | max match loss | over cap kept | band resid TT med/p90/max ps | reach max |
|---|---|---|---|---|---|
| base (dry14 spec) | - | - | - | 31.1 / 39.1 / 144.1 | 448.524 |
| window 3, tol 10 | 280 | 8.9 ps | 216 | 32.9 / 39.1 / 144.1 | 448.524 |
| window 3, tol 30 | 480 | 28.5 ps | 16 | 35.2 / 40.4 / 144.1 | 448.524 |
All exports geometry PASS, 0 errors, max stage 448.524 <= 450 (own runs, UNCHECKED numbers).

## 3. dry16 census (no_clock_track, own runs)
| run | spec | trunk_escape | errors |
|---|---|---|---|
| dry15c (R31) | base | 100 | 1,179 |
| dry16_w3t10 | window 3 tol 10 | 100 | 1,027 |
| **dry16_w3t30** | window 3 tol 30 (sha 7941170c on packet) | 100 | **682** |
| dry16_w3t30_etrue / e400 / enone | same | true / 400 / off | 810 / 828 / 1,218 |
| dry16_w3t30_dxm8 | + band column -8.64 | 100 | 928 (band column onto the top-leaf lane) ; +8.64 / +17.28 export FAIL (east edge) |
dry16 NOT 0 -> no READY, no GRT/STA.
Remaining 682 (dry16_w3t30_driver_classes.txt / _edge_families.txt): periodic, ~16-17 per W/E column partition
(c_*_bn / c_*_bf) + 32 channel. In every column period (e.g. x 7500-8200) the column-tree column (col+750), the band
y-tree column (col+751), the top-tree leaf leg (top_rep col+732) and the band x-tree node (col+751..795) converge on ONE
x: escape jogs of the 16w x-tree kid (108), band x-tree escape jogs (108), x-tree node escape drops (108+), col_node M9
driver jogs (130), col_tap drops. Next structural fix (export): give the three trees disjoint island columns at the feed
column (column tree, band y-tree, top leaf leg = 3 slot columns, >= 1 island pitch apart, chosen per type so W/E
mirrors stay identical) and land the x-tree parent leg vertically (on the node column) so x-tree node windows hold 2 pieces.

## 4. Per-bit FT pin model (COORD ruling (3)) -- ft_pin_hops.py, ft_pin_hops_event_n100.json
Model: bit i leaves on its out face at the linear out-window point (packet convention); it ENTERS where the abutting
neighbour same-named slot leaves (neighbour out pin of bit i, both orientations mapped). Event plan: 250 slot instances,
45 neighbour-matched: worst in hop 377.16 um, worst out hop 401.30 um (all slots) -> 0 over 405.
coll_ftc crec_rx_s0 (coll_f4): in 349.18 / out 349.03 um -- its N pins are coll_f5 (coll_ftn) crec_rx_s0 S out window
[4.32,118.656] in the SAME bit order as coll_f4 bank0 -> no register move needed; R31 465 um was the reversed-order
pessimistic bound, not a reachable pin order (UNCHECKED: depends on the kit pin assigner keeping the linear per-bit order on
both faces; the check now asserts it). 205 instances have a non-slot source (logic partition pins) -> pessimistic window
model; 41 exceed 405 (slw/sle_su_c cws1/cws2, slw_su_l0 cws3, coll_ftc ard/dd/out_data/dr/tl_st/crec_tx, coll_ftn
crec_rx; worst 490.6) until the source kits declare per-bit pin x -> FT packet owner / kit pin assigner.

Tests: test_qc_clk_mesh3, test_qc_clk_mesh3_export, test_band_feed_r15, test_explicit_clock_v2, test_qc_track_allotment:
44 PASS.
