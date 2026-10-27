# HEAD R18 tree: outer-anchored half lattices (COORD R17 ruling 5)

Generated Tue Oct 27 08:04:54 AM PDT 2026. Branch claude/head-r18-tree-1027 (from claude/head-r17-tree-1027@e20c843292).

## Command
python3 tools/s81_head/head_mesh_r3.py physical/die_plan/s81_head/die_plan.json --stage results/qc_clk_mesh3/stage_table.json --pg-lanes --spine-columns --pins-a 162.00,163.44,319.68 --pins-b 144.72,146.16,285.12 --r18 --m8-max-pitch 144 --out results/s81_head_r18/tree
python3 tools/s81_head/head_mesh_export.py results/s81_head_r18/tree --pitch-from-straps
python3 tools/die_plan/master_plan.py <snapped plan head-r17-plan 2b67cdc6c3, sha a48c8d57> --out <mp> --mesh results/s81_head_r18/tree --declared-slots  -> master_plan_gates_r18_snapplan.json
The generator re-run reproduces tree_nodes/straps/drivers/stubs byte-identical.

## Root cause of the R17 +762/+611 ps
R17 path root->driver 17,488 um vs the Manhattan bound 13,997 um. Each binary lattice was centred on its leaf set, so the
unused slots of a power-of-two lattice were wasted at BOTH ends: x half-rows 11 columns on 16 slots (+1,417 um),
y 14 rows (12 tile + 2 station rows moved onto lattice slots) on 16 slots (+1,037 um + the station moves).

## R18 change (structure only; no meander, no trim, no measured value)
1. Outer-anchored half lattices: each half (x: either side of the spine, y: either side of the centre row) has its own
   binary lattice with its OUTERMOST leaf on the extreme slot; pruned slots lie on the spine/centre side. Path = bound.
2. Station rows keep their mesh straps but carry no tree drivers (fed through the M9 columns, like the serdes-strip rows):
   removes the 36 off-island station drivers and their x-trees. 264 drivers (12 tile rows x 22).
3. Every x-tree is translated 4.32 um outward-consistent (+ on the left half, - mirrored) so x nodes sit on the snapped
   tile-edge islands (4.32 / 704.16) instead of on tile boundaries; legs unchanged.
4. d1 sizing as R17 (drive_mult = base x children).

| item | R17 e20c843292 | R18 |
|---|---|---|
| stages root->driver | 45 | 37 |
| path root->driver | 17,488 um | 13,992.5 um (= bound) |
| plan-model insertion TT/FF | 3857.9 / 3103.6 ps | 3104.4 / 2494.0 ps (UNCHECKED, plan model) |
| driver skew (model) | 0.157 / 0.130 ps | 0.0 / 0.0 ps |
| tree wire / repeaters | 685 mm / 1140 | 526 mm / 840 |
| sibling_reps (GEOM-24 a) | PASS | PASS (0 findings / all paths 37 stages) |
| master_plan tree_balance | PASS | PASS (313 families, 0 unequal) |
| die_pair_skew_model TT/FF | 90.3 / 84.6 | 78.6 / 74.2 ps (nominal 31.7/32.5 + derate 46.8/41.7), UNCHECKED |
| clock_sites drivers off island | 36 | 0 |
| clock_sites tree nodes off island | 109 | 48 (snapped plan) |
| export VIA89 = strap crossings | 11700/11700 | 11538, origin/main mesh_via_findings 0 findings |

## Remaining FAIL: islands the symmetric tree needs are not declared (needs a declared-slot plan delta, ASK)
The snapped plan islands are the snapped sites of earlier trees; no exact equal-leg pair exists on them (searched).
Needed, identical per type (12.2a1), mirror-symmetric:
- hd_tile channel row y 354.24: x 349.92 and 358.56 (the drivers, 264).
- hd_spn and hd_spn_end channel rows y 354.24 / 1391.04: x 4.32, 669.6, 712.8, 1378.08 (pruned-side x nodes next to the
  spine), and the spine trunk column x 691.2 at y 354.24, 872.64, 1391.04, 1909.44 (row roots + y nodes; current
  spine islands sit at 693.06, 1.86 um off the trunk at the partition tap 691.2).
- the plan root (spine root_um, hd_spn frame (691.2, 0)) is a partition-edge point (as in R17).
Unchanged from R17 (not caused here): clock_entry (tap rename clk->ft_mstrap_i), clock_shield, tree_commensurate,
core_reach, core_insertion_model, island_ft_inputs, tree_on_islands (master_plan island_tree form).
Routing note: the out-and-back legs next to the spine (row root -> half-lattice top -> back toward the spine) run
on the same channel row for up to ~1.4 mm; they need two tracks there (render viewed).

## Not done
Built DB / RCX / MC / die_sta_related.py: not run (needs the island delta and INFRA-FIRST-HEAD-5 adoption; HEAD-5
e5f4fb2cd1 is READY + GEOM-25 PASS-COND, NUMBER-CHECK owed, not adopted at 08:04). Built on the current PG
(plan c218aebc); --pg-lanes re-snap on plan 33029005 is the next step once adopted.
