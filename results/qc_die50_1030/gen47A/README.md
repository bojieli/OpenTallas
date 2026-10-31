# DIE-QC-50/gen47A: Route A, the drawn fixed clock prebuild rebuilt for gen47 (2026-10-30)

This is Route A of the QC freeze-gate clock measure (COORD ruling ~16:05). It rebuilds the Codex 2249 / DIE-QC-36..42
drawn fixed-clock chain for the gen47 tree. That chain is source -> leaf drivers -> re-site -> backbone -> prebuild ->
materialize -> PG access -> apply -> GRT50 -> RCX -> die_sta_related. It runs on the gen47b import database
(bfb917d68: 48,296 clock cells and the 50,020-cell START/reset provider).

Route B (clock NDR + DRT + RCX) belongs to sibling [DIE-QC-50/gen47ndr] and is not touched here.

- Plan: plan_qc49 9deec4c7.
- Tree: gen47 `tree.json` 4bad7469, kit `ctree.v` 15f44729.
- Run root: epyc2 `/srv/opentallas-scratch2/claude/die-qc-50/gen47A`.
- Scripts: `scripts/`, launched through ot-run on epyc2.
- Copied references, read-only: `ref_chain/` holds Codex 2249 `src/`, DIE-QC-41 `run_f1d_r3.sh` + adapter, Codex
  `qc_clock_physical_1029/` (jog_backbones, native_landing_plan, native_pin_census, fixed_tree), and the DIE-QC-36/37
  backbone and re-site scripts.

## Verdict
QC is NOT FROZEN, and there is no drawn clock yet. Route A gets through:
- leaf drivers;
- re-import;
- leaf-pin lower access;
- a legal column-aware re-site, including native M7 pin columns;
- the prebuild's endpoint-landing and window stages.

It stops at the prebuild **track stage**: 67 no_clock_track. All of them sit in two channel row bands of the
`sl_*_st_a` template (y ~13967 and ~14304, repeated in every slice). Net ordering does not fix it, and neither does a
larger max-move. The default M7 window there is clipped by the hard-core halos to about 4.3 um, which leaves room for
about 4 shielded M8 trunks, and gen47 puts about 5-6 nets in it. The DIE-QC-37 answer to the same class (R7 range-window
backbone: M6 jog to a column whose riser range is limited by actual metal, not by the 2.16-um halo window) is the next
step. Its input E1-style wire set is produced by the diagnostic `E1d` run (section 4).

## Step ledger
| # | step | status | output (epyc2 gen47A/) | numbers |
|---|---|---|---|---|
| 0a | ot_clk leaf drivers (main `tools/clk/leaf_drivers.py`, config `leaf/qc_leaf_gen47.yaml` = DIE-QC-37 qc_leaf_fixed_rf knobs) | DONE | `leaf/` | 2,489 trunk nets, 3,369 clusters, 6,738 new CKINVDC (x5p33 trunk side -> x16 leaf side), max leaf HPWL 9.45 um, +2,554 um2 [CHECKED run.log] |
| 0b | preflight + Codex apply_cells on gen47b `source_bound.odb` | DONE | `import/` | preflight READY_FOR_REVIEW, issues {}, 56,758 cells; ALL_MAPPED_CELLS_IMPORTED 56,758 (23,230 FF / 33,528 comb), 113,516 PG terms; native cells/conn sha == gen47b (6b87ca4a / 398a9ccb) [CHECKED]. Crops `review/leaf_b1038.png` and `leaf_b0.png` viewed (self PASS-COND) |
| 0c | leaf A-pin loads (DIE-QC-39 `leaf_inventory.py`) + main provider_clock_loads + plan_provider_clock_access | DONE | `access/` | 3,369 loads on 2,489 nets, LOWER_ACCESS_GEOMETRY_PASS 3,369/3,369 [CHECKED] |
| 1 | column-aware re-site (`resite47.py` = DIE-QC-36 dqc36_resite + native M7 pin columns + island-hole legality from the bound OBS) | DONE | `resite/` | 2,581 / 48,296 moved, 0 unresolved, 0 still stacked, 0 native-column, 0 overlaps, 0 outside holes, max 0.324 um; graph sha unchanged [CHECKED report.json] |
| 1b | move cells in the ODB (`prepare_source47.py`: FIRM -> move -> FIRM) + re-export + access | DONE | `source/provider.odb`, `access_rs/` | 2,581 moved; LOWER_ACCESS_GEOMETRY_PASS 3,369/3,369 [CHECKED] |
| 2 | prebuild: main `fixed_tree_provider.py` + DIE-QC-41/42 adapter (copy, die-local patches below) | FAIL track stage | `prov_P*` | see 3 |
| 2d | E1-style diagnostic prebuild (diagnostic repo copy `e1diag_repo/`, see 4) | DIAG: track 67 recorded; pin-access census PASS; top-access FAIL | `prov_E1d` | encoder census 0 shorts / 0 spacing on 1,112,509 shapes; top_access_conflicts 3,441 on 1,113 nets [CHECKED prebuild.json, diag_top.json] |
| 3 | range-window backbone (dqc37_backbone.py R6/R7 recipe) on gen47 | NOT STARTED | | inputs listed in Next |
| 4 | prebuild PASS -> materialize (Codex prepare_root + fixed_pg.tcl + fixed_clock_only.tcl) | NOT STARTED | | |
| 5 | PG access plan (reserve_clock + pg_shield_supply_context + pg_access_plan_b7a872287 cover/fallback) + apply | NOT STARTED | | 113,516 new provider PG terms + 96,592 clock PG terms |
| 6 | die GRT 50 it with the fixed clock + clock_preservation | NOT STARTED | | |
| 7 | RCX of the drawn clock, both-edge readout, main die_sta_related (DIE-QC-45 args, 313 droop regions) | NOT STARTED | | gate: TT intra setup >= 0 |

Die-local patches (the copied adapter is otherwise unmodified; shared tools on main are untouched):
1. `access_windows`: gen47 has 24 clock cells on die channel rows with no partition host. They get no host-outline
   clip, but every partition keep-out and io keep-out is still checked with the same 2.16-um halo. The old tree had
   none of these cells.
2. Diagnostic only: `scripts/mk_e1diag_repo.sh` builds a repo copy at `$A/e1diag_repo/`. In that copy,
   `die_clock_128.fixed_wires` writes its no_clock_track rows to `e1diag_errors.json` and returns the wires, so the run
   continues to the later stages. This is never a qualification. `patch_adapter2.py` was a first in-adapter attempt; it
   did not take effect (the raise still came from the original path; not investigated further).

## 3. Prebuild track-stage runs [CHECKED prov_*/prebuild.json]
| run | change | result |
|---|---|---|
| P0 (no re-site) | - | ValueError: clock stack base intersects native M7 pin (ck_b1746/Y vs t_sl_E0_fw__clk) -> re-site step 1 |
| P1 | re-sited tree, access_rs | track stage FAIL 67 no_clock_track (trunk 39 / driver jog 14 / drop 14); ideal y 13966.695 x38, 14304.735 x14, 14304.195 x12, 13968.315 x2, 2325.375 x1 |
| P2 | P1 failures routed first (OT_DQC41_FIRST) | FAIL 90 (failure moves to neighbours: 13968.3 / 13967.2 / 14304.2) |
| P3 / P4 | max-move 12.96 / 17.28 | FAIL 67 (same; the window is halo-clipped, not radius-limited) |
| P5 | P1 + P2 failures first | FAIL 90 |
| P6 | P5 + every net driven in the two bands first (703) | FAIL 100 |

Mechanism (P1 driver_jog_diag ck_rn1929_0 at x 18551.7):
- The M7 window is [14301.39, 14305.65], clipped by the hard-core halos above and below.
- A VDD M8 strap (14303.28-14303.76) splits that window.
- The H-tree trunk ck_n34 / ck_rn34_1 / ck_rn34_2 and the branch ck_rn1953_0 already hold its tracks, each with a
  shield on each side.

The old tree had the same cells in the same channel (old E1 passed with 0); gen47 adds repeater nets there. This is a
capacity issue, so ordering and radius do not help.

## 4. E1d diagnostic: stages after the track stage [CHECKED prov_E1d/prebuild.json, prov_stats.json, diag_top.json]
For this run the 67 failing nets kept their attempted geometry and the run went on. Results:
- **Pin-access (encoder) census PASS: 0 shorts, 0 spacing** on 1,112,509 access shapes. DIE-QC-37's E1/R7 had 535/89
  here, so the re-site plus native-column guard plus leaf loads clear this stage on gen47.
- **Top-access reservation FAIL: 3,441 conflicts on 1,113 nets.** 120 of them are on the 67 E1-failing nets. By kind:
  - M8 spacing to a PG strap: VSS 1,376, VDD 1,314.
  - M8 to a VSS shield: 272 spacing, 93 shorts.
  - M8 short to a VDD PG strap: 86.
  - M9 spacing to PG/shields: 261.
  - Tree-tree: about 12.

  Example: ck_n12, an M8 min-area pad at y 11040.886-11040.966 next to the VSS strap at 11040.80-11040.88 (gap 0.006).
  The reference R7BFR3 (old tree, same adapter and env) passed this stage and reached PASS_PREBUILD. The gen47 drop
  points therefore land the 0.192x0.08 M8 pads against the qc49 M8 PG straps and shields. This is a separate class from
  the track stage, and it is not caused by the 67 failing nets.
- Endpoint stats: land_reserved 1,259, land_reserve_blocked 118, near 1,005, far_pgclear 116, netaware_none 115; root
  moved +0.92 um to 17008.76.
- `review_region.png` (c_E2_bf_10) was VIEWED. Its M8/M9 trunks run in the channels and around the hard cores, with
  drops at the core faces, the same structure as the old tree. "Drawn" only; no further claim.

## Next (successor), in order
1. Track stage, 67 nets. Run the range-window backbone (DIE-QC-37 R6/R7):
   `ref_chain/dqc37_backbone.py --jog-src ref_chain/qc_clock_physical_1029 --fixed-wires prov_E1d/fixed_wires.json
   --riser-island off --column-select track --riser-max 9.0`.
   Each input still has to be regenerated for gen47:
   - `--cell-windows`: islands from the gen47b bound constraints; resite47.py already derives them.
   - `--geometry`: an h800-style census of `source/provider.odb` via the Codex 2249 readback.
   - `--clock-base-resited`: base stacks from prov_E1d.
   - `--reserved-metal`: native M7 rectangles + PHY stubs.

   Then feed the windows to the adapter the way DIE-QC-41 R7BFR3 did (OT_DQC37 range windows), and keep the 36-pin
   default-window fallback for vertical-trunk drivers.
2. Top access, 3,441. Compare the drop/pad placement against the qc49 M8 PG strap pitch. The likely fix is the pad
   y-offset / pad-on-track rule in the top-access reservation, or a PG-aware drop y in the adapter. Check whether the
   old tree's drops sat on a different strap phase: the old plan was qc-older and the PG pitch is unchanged, so compare
   directly with ref R7BFR3 diag.
3. Then pass 2 (F1=1 FUT=pass-1 fixed_wires) -> PASS_PREBUILD -> steps 4-7 of the ledger.

## Live jobs
None. Every unit is terminal and collected: P1-P6, E1d on epyc2 ot-run.
