# HEAD-R17 plan (ROOT-MERGE-32 hold fix) 2026-10-27 07:43 PDT

Base claude/root-merge-32-head-1027@bd44111bbe (main a14244af63 tools). ROOT-MERGE-32 held head-r16: main die_islands rule
(landing_islands.check_die_islands) -> 15 s81_head clock.die_islands_um rects outside the type outline (hd_tile 10, hd_spn 1,
hd_ctl 2, hd_host 2), G0 4 errors (reproduced, CHECKED).

ROOT CAUSE: head_infra_delta_r4.py centred an 8.64 um island on every tree site WITHOUT clipping ("the part outside lies in
the abutting partition"). The R3/R15 channel-row tree merges two adjacent tile drivers (tile centres x 354.24) at their
midpoint = the shared tile edge, so merge nodes + adjacent leg repeaters sit at x 0..0.5 / W-0.5..W (also 1 hd_spn y=0, 1
node+1 rep at hd_ctl/hd_host x=0). Half of those islands lay in the neighbour partition: breaks the die_islands rule and
12.2a1 one-netlist pushdown.

FIX (structural, generator): snap_inside() clamps every island centre to [4.32, W-4.32] x [4.32, H-4.32]; duplicates after
the snap merge (hd_tile 69 -> 61 islands); refusal on hard-core overlap kept; per-type site_moves (max 4.32 um) reported in
delta_report.json. Islands stay per type (identical on all 264 hd_tile replicas). Regenerated: census of the R15 m5 tree
(head_slot_census.py) -> head_infra_delta_r4.py on the bd44111bbe plan; only die_islands_um changed (CHECKED: all other plan
content dict-equal; the 351 unchanged islands reproduce exactly). Plan sha256 d84d7778ce5f.

G0  (python3 tools/die_plan/check.py physical/die_plan/s81_head/die_plan.json --out g0):               PASS 0 errors / 6 warnings (CHECKED g0/g0_report.json)
G0C (python3 tools/die_plan/check.py physical/die_plan/s81_head/die_plan.json --completeness --out g0c): PASS 0 errors / 6 warnings (CHECKED g0c/g0_report.json)
Portbind: not rerun -- no bind tool reads clock.die_islands_um (grep), ports/lanes unchanged.
Render islands_vs_outline.png (viewed): every island inside its outline; old rects red dashed.
Tests tests/test_head_infra_snap_r17.py 3 PASS (run with python3 directly, no pytest on intel2).

INTERACTION (tree owner): master_plan --declared-slots on the R15 m5 tree: island_lattice PASS -> FAIL, 122 tree nodes
displaced max 4.32 um (the edge merge nodes now sit on the island boundary; clock_sites stays PASS, mesh drivers 0
displaced; all other gates unchanged vs R15, master_plan_gates.json). The tree must put those merge nodes / repeaters at
the snapped island centres (edge +/- 4.32 into the owning tile; site_moves); the tree fork claude/head-r17-tree-1027
re-sites nodes and must re-run census + this generator on its tree.
