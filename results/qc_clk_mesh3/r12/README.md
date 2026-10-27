# QC-CLK-MESH r12 (INFRA-FIRST-QC-R12, 2026-10-26 22:30 PDT): mesh3 top tree on ONE per-type island lattice

Numbers are UNCHECKED unless marked CHECKED. CHECKED values were recomputed by `scripts/numcheck_r12.py`, with the output in `numcheck.txt`.

## (1) Island lattice + legal re-solve (`qc_clk_mesh3.py --islands type --island-corr`)
- **Islands**: each partition type has one slot grid in its own type frame. The grid is symmetric, so it works for both R0 and MX instances. Pitch is x 4.86 um and y 19.3 um, with an 8.64 um edge inset.
  - A slot is removed if it lies on a hard core in ANY instance of that type.
  - The die lattice is the union of these per-type lattices; no window is drawn across a seam.
  - The merge and repeater solve chooses top-tree node and repeater sites only from slots.
  - Each horizontal row uses one slot row per partition, and each vertical leg uses one slot column per partition.
  - `assign_islands()` gives each group one slot.
- **Export** (`sites/r12_top_sites_summary.json`): 4703 groups, 8494 BUFx24, 4702 nets (M8 4547, M9 155).
  - Island checks: off-lattice 0, seam straddles 0, cells outside the die 0, overlaps 0. Gate PASS.
  - lattice_identical_per_type true. Max move from the model position is 24.2 um.
  - Compared with R11, the 914 straddles and 19 die-edge cells are gone by construction.
- **Re-solve on the snapped sites**: each iteration feeds the legal-minus-model per-edge delay back as `--island-corr` (`resolve/it*.json`). Values are top-tree leaf spread in ps.

  | Iteration | TT model | TT legal | FF model | FF legal |
  |---|---|---|---|---|
  | it0 | 12.4 | 59.1 | 10.5 | 50.5 |
  | it1, using it0 corr | 13.4 | 32.8 | 12.6 | 28.0 |
  | it2 | 16.7 | 40.6 | 13.5 | 34.8 |

  The loop does not converge. It1 is the best, and the full solve uses it.
- **Full legal solve** (`legal_isl/`, it0 corr): 35530 instances; reach 443.7 um max, 0 nets over; 69 top stages.

  | Metric | R12 (TT / FF) | R10 legal, not on islands (TT / FF) |
  |---|---|---|
  | Nominal entry skew | 22.10 / 19.65 CHECKED | 26.27 / 22.94 |
  | Per-seam-pair U max (773 pairs) | 103.09 / 95.34 CHECKED | 103.15 / 92.73 |
  | MC whole-die (INFO) | 296.0 / 259.5 | — |

- **Related-pair die STA** (997 ordered pairs, all 377 entries, `--pair-unc`):

  | View | TT setup worst | FF hold zero-logic worst | FF kit-contract hold (W 40) |
  |---|---|---|---|
  | `sta` | +558.09 CHECKED | -93.91 CHECKED (997/997 need data hold buffers, approved) | +24.65 PASS |
  | `sta_cv`: RP1 signed + VMR GRT core views on the 12 su_c | +558.09 | -101.06 | +5.17 PASS (need 34.83) |

  For reference, R10 `sta_cv` gives kit-contract +11.21.

## (2) Builder extensions (tools from c540e671da)
- **Changes**:
  - `die_clock_mesh.py`: adds NDR `16w` (0.64 um, wide spacing, VIA78/89 arrays) and `build --explicit-cells SITES.json`, which takes mesh3's cells and nets instead of a midpoint H-tree.
  - `die_clock_128.py`: `ties=` / `l_drops=`.
  - `clock_routed.py`: stacked-unit A/Y tie straps and a 6x6 VIA89 array.
- **Tests**: `test_clock128_r12.py` 4 PASS; `test_qc_clk_mesh3.py` 10 PASS, including 2 new island tests.
- **Dry run on the r12 export** (`dry_build/`): PLAN ERROR 3049, made up of 1368 `no_clock_track` and 1681 `no_pin_stack`.
  - The M7 riser is 2.6-3.7 um, above the 2.5 um window.
  - A shielded 16W wire takes about 2.92 + 0.5 um. Overlapping x-tree legs on the same row do not fit in the track window.

## (3)/(4) Not done in this lane
There is no physical route, DRC, RCX or resistor-graph check yet, and no RCX-fed STA. Blockers:
- The 3049 plan errors above.
- The 0.64 um RCX rules file (`rcx_width_rules.py write --widths 0.64`) has not been generated.
- The 6x6 VIA89 array has not been through DRC.
- MX row flipping is not handled in the builder.
