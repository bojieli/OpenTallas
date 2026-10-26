# INFRA-FIRST lane (owner D-INFRA-FIRST 2026-10-26 01:37): one shared die tool -> PG/clock/reset fixed pre-routes before die signal GRT
2026-10-26 01:41 PDT INFRA-FIRST (fresh lead): branch claude/infra-first-0140 (= main 767c6c90b6, has die_clock_mesh fdb5b851c7/d0803fe0b7), sparse wt epyc1:/srv/opentallas-scratch2/claude/wt/infra-first-0140, data epyc1/epyc2:/srv/opentallas-scratch2/claude/infra-first-0140/. Builds ON die_trial.py (kit/psm/grt), die_clock_mesh.py (+ CLOCK-MESH-2 regional meshes, coordinated in CLOCK-MESH.md), apply_clkmesh_sites.py, reset_tree.py (wf_plan), pg_regions/partition_ir/phy_ir. No fork; new code = tools/die_plan/die_infra.py (orchestrator, opt-in) + opt-in flags; default paths unchanged until COORD approves.

## METHOD (D-INFRA-FIRST, owner 01:37 + COORD 01:4x additions) -- per die, in order
1. PG: die grid on M9 + part of M8, sized from per-region IR (PDNSim per region; published PHY power 4.37 W/macro (S81-PHY-ASSUME), core power per type density). Report % of M8/M9 tracks taken.
2. CLOCK: equal-length H-tree -> one mesh per clock region (driver sites in reserved islands, apply_clkmesh_sites.py, never on hard cores), LANDED (forwarded-clock) crossings at region seams (COORD 01:22).
3. RESET: die reset wavefront (owner 10-24 / decision 13): rst_n -> root partition, parent rst_o_<k> -> child arst_n die hops (<= hop_um, M8/M9), START broadcast hops.
4. FREEZE 1-3 AS FIXED PRE-ROUTES: special nets / FIXED wires + their NDR footprint as obstructions in the die kit, so die GRT sees the exact leftover capacity. Skew gate on the pre-routed clock ALONE (die_clock_mesh_post.sh method: like-edge related pairs, CPPR, TT+FF, <= 80 ps).
5. DIE SIGNAL GRT on the leftover, >= 50 iterations (M4-M7, + leftover M8/M9 only if FT-M89-PROBE justifies).
6. FREEZE on GRT0 incl. clock + related-pair skew <= 80 TT/FF. Report: GRT overflow, skew TT/FF, IR, clock power, island area per type, leftover M8/M9.
7. (COORD) THE DIE ABSORBS RESIDUALS: a tile whose measured clock insertion differs from plan is compensated at die level by a per-tile mesh stub trim / declared core-latency offset (die_clock_mesh.py knob), never a tile rebuild. Boundary timing rests on registered pins + channel repeaters. A tile is rebuilt only for its own internal failures.
8. (COORD) PRE-FREEZE TRIAL PLACEMENT of every tile type: a quick place with the clock islands and pre-route keep-outs in; must show fit, pin access and an r2r reach census before the die plan freezes.
Order: QC prototype -> S81-HEAD -> hand the tool to PATH-KV / PATH-S81 / PATH-HBM.
