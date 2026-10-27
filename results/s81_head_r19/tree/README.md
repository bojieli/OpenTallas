# HEAD R19 tree: R18 structure on the adopted PG (M9 12.96@34.56), 32 M9 straps re-snapped, root node on its snap_inside island

Generated Tue Oct 27 10:42:57 AM PDT 2026. Branch claude/head-r19-tree-1027 = claude/head-r18-tree-1027@952a57009 + origin/main 60b5ddf52 (clean merge).
Sub-lane HEAD-R19-TREE of HEAD-CORE-R19. Plan geometry + plan model only; every number below is own-tool output, **UNCHECKED** (no NUMBER-CHECK).

## Inputs
- Plan: main s81_head die_plan.json (d84d7778 = head-r17-plan 2b67cdc6c3 snapped islands) + the ADOPTED INFRA-FIRST-HEAD-5 PG delta
  (die.pg.grid M9 width 6.48 -> 12.96, pitch 34.56, offset 17.28; the only line claude/infra-head5-1027@e5f4fb2cd1 changes in the plan)
  = **db53ff61** (`physical/die_plan/s81_head/die_plan_r19pg.json`, not committed; recreate with the one-line width edit).
  Not applied to the main plan here (that is the infra-head5 merge).

## Commands
```
python3 tools/s81_head/head_mesh_r3.py physical/die_plan/s81_head/die_plan_r19pg.json --stage results/qc_clk_mesh3/stage_table.json \
   --pg-lanes --spine-columns --pins-a 162.00,163.44,319.68 --pins-b 144.72,146.16,285.12 --r18 --snap-root --m8-max-pitch 144 \
   --out results/s81_head_r19/tree
python3 tools/s81_head/head_mesh_export.py results/s81_head_r19/tree --pitch-from-straps
python3 tools/die_plan/master_plan.py physical/die_plan/s81_head/die_plan_r19pg.json --out <mp> --mesh results/s81_head_r19/tree --declared-slots
   -> master_plan_gates_r19.json
python3 tools/s81_head/head_r19_slot_delta.py physical/die_plan/s81_head/die_plan_r19pg.json results/s81_head_r19/tree \
   results/s81_head_r19/tree/slot_delta.json --trial-plan <trial plan>      (trial plan d1e87c73, NOT adopted)
python3 tools/die_plan/master_plan.py <trial plan> --out <mp> --mesh results/s81_head_r19/tree --declared-slots
   -> master_plan_gates_r19_trialdelta.json
```

## 1. Determinism (R18 claim checked)
- R18 command re-run twice on the R18 plan (c218aebc), current code (incl. merged main qc_clk_mesh3 changes): all 9 outputs
  byte-identical run1 = run2, and drivers/straps/stubs/tree_nodes/4 PNGs byte-identical to the committed R18 files;
  head_mesh_r3.json differs only in the `plan` path string. **PASS, no fix needed.**
- R19 command run with PYTHONHASHSEED=0 and =4242: all 9 outputs byte-identical. **PASS.**

## 2. Changes (structure unchanged; no meander, trim, pad or measured value)
1. `--snap-root`: the plan root (spine root_um (8760.96, 8778.24) = hd_spn sp2 frame (691.2, 0.0), a partition abutment edge)
   was the only tree site on an outline edge (own edge census over all 1418 node/driver/repeater sites; R18: 1, R19: 0).
   The first tree node (SRC) now sits on the snap_inside centre (691.2, 4.32) = the already-declared hd_spn island
   [686.88,0,695.52,8.64]; root stub 4.32 um (straight, single child). All other edge merge nodes were already at the snap_inside
   centres (R18 x-offset 4.32: tile 4.32 / 704.16, spine 4.32 / 1378.08).
2. `--pg-lanes` on db53ff61: lane band is now [7.80, 8.64] um from a VSS centre (12.96 stripe + 1.0 spacing + 0.32 half lane).
   **32 of 95 M9 straps moved, every one by exactly 3.24 um** (18 x -3.24, 14 x +3.24; R18 centres sat 3.24 too close to/inside
   the VSS stripe). M8: 0 of 122 moved. New mesh gate `lane_band`: M9 95/95 and M8 122/122 inside the band,
   **0 off band, max residual 0.000 um** (GEOM-25 condition 1 met on the plan). Riser jog nominal -> lane: M9 <= 8.64, M8 <= 1.08.
3. Gate additions only: `lane_band` (head_mesh_r3), per-type slot-delta tool head_r19_slot_delta.py, zoom renderer head_r19_zoom.py,
   test_head_r19.py (PASS); test_head_r17_sym.py 6/6 PASS.

## 3. Numbers, R18 vs R19 (UNCHECKED, plan model = ngspice stage-table fit)
| item | R18 952a57009 | R19 |
|---|---|---|
| PG M9 | 6.48@34.56 (plan c218aebc) | 12.96@34.56 (db53ff61) |
| stages root->driver | 37 | 37 |
| path root->driver | 13,992.5 um (= bound) | 13,996.8 um (= bound from the snapped root node; +4.32 root stub) |
| plan-model insertion TT/FF | 3104.4 / 2494.0 ps | **3105.0 / 2494.5 ps** (+0.5 ps from the 4.32-um root stub; band = pre-R17 level) |
| driver skew (model) | 0.0 / 0.0 | 0.0 / 0.0 |
| tree wire / repeaters | 526 mm / 840 | 526.1 mm / 840 |
| sibling_reps (GEOM-24 a) | PASS | PASS (0 findings) |
| master_plan tree_balance | PASS 313 families | PASS 313 families, 0 unequal; 1905 tap classes, 0 unequal |
| die_pair_skew_model TT/FF | 78.6 / 74.2 | 78.6 / 74.2 ps (nominal 31.7/32.5 + derate 46.8/41.7); with core residual 173.0/168.6 (diagnostic) |
| clock_sites drivers / tree nodes off island | 0 / 48 | 0 / 48 (same 4 per row x 12: L101, L1, R0, R010) |
| island_lattice displaced (nodes / drivers) | 337 / 264 | 337 / 264 (max 23.46 / 1.96 um) |
| M9 straps off the PG half-gap band | 32 (on 12.96 PG) | **0** (max move 3.24 um) |
| export VIA89 = strap crossings | 11538 | 11538 (95 x 122 lattice 11590) |
| mesh continuity / drivers on strap / tap stubs / m9_spacing | PASS | PASS (1 component; 264/264; max stub 31.2 um; min M9 gap 172.8) |

master_plan (--declared-slots) gate verdicts are identical R18 -> R19: PASS reach_gap, bay_fill, corridor_tracks, entry_pins,
lot_fit, early_taps, tree_balance, footless_stubs; FAIL clock_shield, clock_entry, core_reach, core_insertion_model,
die_pair_skew_model (diagnostic), tree_commensurate, clock_sites, island_lattice, tree_on_islands, island_ft_inputs;
NOT RUN static_ir, infra_sites, clock_rep_sites, tap_region_containment.

## 4. Declared-slot PLAN-DELTA still needed (ASK; per type, identical per instance, 8.64-um squares centred on the site; NOT applied)
slot_delta.json (head_r19_slot_delta.py; every site already snap_inside, no slot overlaps a hard core):
- **hd_tile** (2): (349.92, 354.24), (358.56, 354.24) - the 264 mesh drivers (channel row, +-4.32 from the channel cross).
- **hd_spn** (12) and **hd_spn_end** (12), same coordinates:
  (4.32, 354.24), (4.32, 1391.04), (1378.08, 354.24), (1378.08, 1391.04) - pruned-side edge x nodes (L101 / R010);
  (669.6, 354.24), (669.6, 1391.04), (712.8, 354.24), (712.8, 1391.04) - pruned-side level-2 nodes (R0 / L1);
  (691.2, 354.24), (691.2, 872.64), (691.2, 1391.04), (691.2, 1909.44) - row roots + Y nodes on the trunk at the partition tap x
  (existing islands at 693.06 are 1.86 um off).
- With exactly this delta on a trial copy of db53ff61 (master_plan_gates_r19_trialdelta.json): **clock_sites PASS (0/0 off island),
  island_lattice PASS (0 displaced, max 0.0 um)**; all other verdicts unchanged.

## 5. Renders (viewed)
- r3_mesh_tree.png: 12 tile rows each with one red channel-row tree; y-trunk on the spine; M8/M9 mesh over the tile array and to the
  serdes strip rows; no red off-site x anywhere; drivers (green) at the outer tile ends of every row.
- r3_zoom_spine.png: trunk with Y/YU/YD nodes and row roots; row nodes R0/L1 just either side of the trunk; repeaters stacked on the
  rows next to the spine where the out-and-back legs overlap (needs 2 tracks there, as R18 noted); no node on a grey core.
- r3_zoom_tile.png: tree rows in the channel between the eA rows, nodes/repeaters never on a core. r3_zoom_corner.png: SW outer driver
  at x ~635, no off-site site; reserve frame/serdes rows clear.
- r19_zoom_strap.png: M9 clock strap 2933.04 -> 2929.80 now sits in the half-gap 1.0 um off the VSS stripe; the R18 centre (dashed)
  lay inside the 12.96-um VSS stripe.
- r19_zoom_root.png: SRC on the declared hd_spn island 4.32 um above the sp2 edge (8778.24). **Seen: the vertical y-trunk line
  x 8760.96 is the centre of a VDD M9 stripe** (8743.68 + 17.28): the trunk legs cannot route on M9 at the node x; they need an
  M9 lane at 8752.32 (taken by the spine clock strap) or 8769.6-8770.44 (free VSS-side lane), i.e. an 8.64-um riser at each trunk
  node. Not modelled by the plan model (it charges straight legs); OPEN for the route probe (same class as Codex no_clock_track).
- r19_zoom_spinerow.png: L101 / R0 / r00_ / L1 in the proposed delta slots (magenta); plan islands (olive) at tile 704.16 and 693.06.

## Remaining FAILs / ASKs
- ASK: adopt the 26-slot declared-slot delta above (one batched PLAN-DELTA with any other HEAD plan change); then clock_sites and
  island_lattice pass on the plan.
- OPEN: trunk track assignment vs the 12.96 VDD stripe (section 5); clock_shield (217 straps unshielded in the gate's form);
  clock_entry / core_reach / core_insertion_model / tree_commensurate / island_ft_inputs / tree_on_islands (master_plan island_tree
  form) unchanged since R17, not caused by the tree.
- Not done: built DB / RCX / MC / die_sta_related.py (needs the slot delta + infra-head5 merge); no ot-run route probe launched.
