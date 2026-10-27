# HBM-CORE-LAT-R5 xcal_rel_t (2026-10-27 02:51 PDT) -- COORD RULING HBM-CORE-LAT-R4 (4)+(5): no level padding + plan-computed per-branch sizing
Re-pack outline 241.92x224.64 (+26 %, ruling (4) ACCEPTED), R4 Q0 kit placement (LEC EQUIVALENT 5593/5593, R4 CHECKED) unchanged.
Tool: tools/die_plan/core_infra_htree.py --r6 --no-pad (new, opt-in): every edge keeps its own SHORTEST legal length (no detour
to the level maximum); one repeater count per level (same cell chain on every root->leaf path). Then
results/qc_su_prog_l1_1026/su_branch_size.py (12.8 d1, uf_phys3 OT_PHYS_FIT=model_refit3_1026/uf_phys3_v1.json, calibrated BUFx8..x24,
slew <= 60/initial) picks branch/repeater cells before build. Islands = R4 slice l2 sites (SW,SE,NW,NE order), --no-side-hub, leaf 4.
PLAN MODEL (uf_phys3 phys_gate, UNCHECKED):
- R4 padded nb6451 m70 (reproduced): TT 290.6 w23.6 / FF 223.1 w22.2 (ht 297.9 = R4 figure)
- no-pad nb6451 m70: TT 242.9 max 274.2 w46.1 / FF 185.9 w40.2
- no-pad sweep (plan/sweep_nopad.tsv, 20 variants): best nb5452 smax 100: TT 226.8 max 259.3 w46.0 / FF 174.2 w39.6
- + per-branch sizing (32 cells changed, plan/nb5452_m100_sized.size.json): TT 235.0 w24.8 / FF 178.5 w22.2 (guard gate FAIL: window >20, FF <187.5)
MEASURED post-CTS (kit_cts/, intel2 unit oth-ubuntu-876409-1793094608, do-cts on the R4 3_place.odb, plan-built tree, TritonCTS off,
no pads/trims; PLACEMENT RC estimate_parasitics, UNCHECKED): 104 nodes, 64 leaves depth 5, 3142 reg sinks + 4 macro leaves;
TT mean 162.2 (136.5-173.5, spread 37.0) / FF mean 123.5 (104.5-131.7, spread 27.1); FF hold gate PASS reg2reg wns -33.33 (103 ep).
=> the core is SHALLOW vs 250/202.5 (-88 TT): model over-predicts this tree by ~73 ps on placement RC (GRT/RCX not run).
Fix per 12.8c: designed fixed trunk at the entry (same chain per type) once a GRT-basis insertion is measured; spread 37 > 20 ->
GEOM-REVIEW-17 tree-form items (i) l1_s/l1_n H, (ii) far kids to nearest island, NE-island single pocket child still open.
Render (viewed): xcal_Q0_r5_plan.png (node->node straight lines; real edges follow the maze).
Q0 slot delta REQ posted to HBM-MU-QUAD-3/4 (COORD-REVIEW-QUEUE): shift bus:L77_o column 34.56 W (GEOM-REVIEW-17 (4)), grow W.
