# KV fresh full-union source rebuild (DIE-KV-30-SRC), 2026-10-29 09:41 PDT

Fixes the open KV native provider source defect handed back by Codex 2026-10-29 09:03
(old source LEFs cut provider holes only, so 14,634 of 15,296 packed clock bodies sat on soft M1 OBS).
Clean fresh rebuild, no in-place OpenDB OBS edit (the failed `apply_abstracts.py` adapter is not used).

Runtime: `intel1:/srv/opentallas-scratch2/claude/die-kv-30-1029/src_full` (Codex inputs mounted read-only).

## What changed vs codex/kv-0822-1029 (c1e6a96ed)
- `/work/abstracts` = the 56 `codex-kv-0822/full_abstracts/*.lef` (full per-type clock+provider union, 29,431 windows).
- Everything else identical: same `source.tcl` and prepared `combo.v` (START/reset pins already in the LEFs),
  same `bind_native_source.py` + `packed_tree.json` homes, same `export_constraints.py`,
  same `proposal_open/placements.json` (sha b5bfd1e2...), same `apply_cells.py` import and `actual_reach.py`.
- Preflight of the SAME placements against the NEW fresh constraints (proposal constraints = old planning constraints).
- PG: the codex/kv-pg-0834 grid3 recipe (prepare_grid.py -> pdn_top3.tcl (paths only) -> readback_grid.py), same 13,073
  die_trial.pg_stripes reservations removed only during pdngen and restored. Array-expanding export not run.

## Readback (all CHECKED, receipts/)
| item | old (codex-kv-0822) | new (src_full) |
|---|---|---|
| instances native / after import | 15,456 / 38,127 | 15,456 / 38,127 |
| provider cells FF+comb | 22,671 = 10,530+12,141 | 22,671 = 10,530+12,141 |
| clock cells | 15,296 | 15,296 |
| clock bodies hitting any master OBS (M1/M2/M3) | 14,634 | **0** |
| provider bodies hitting any master OBS | 0 | 0 |
| std-cell hits on 1,628 hard-core rects | 0 | 0 |
| block / clock / provider placement sha | 6f86acff / 9ef93d9f / d11589b3 | identical |
| native_cells_sha / native_connections_sha | bf2001c3 / 30d8ec31 | identical |
| master signal-pin geometry sha (56 types, 527,674 shapes), sizes | - | 56/56 equal |
| master OBS rects / PG pin shapes VDD,VSS | 30,592 / 10,845, 10,849 | 73,027 / 14,142, 14,093 |
| fresh constraints lower_OBS | 98,109 | 212,388 |
| preflight (same placements, new constraints) | READY, 0 issues | READY_FOR_REVIEW, 0 issues |
| actual reach | 15,271 arcs, max 355.326 um, 0 >405 | 15,271 arcs, max 355.326 um, 0 >405 |
| PG grid readback | 38,127 cells, 31,845 block OBS | 38,127 cells, 31,845 block OBS |
| VDD / VSS / VDDPHY shapes | 1,711,367 / 1,700,546 / 8,648 | 1,711,367 / 1,700,546 / 8,648 |
| non-PG sha | cce6226e... | cce6226e... (unchanged) |
| pdngen runtime | 155.96 s | 149.83 s |

VDDPHY still has 0 ITerms (licensed PHY supply binding open with KV/PHY), as before.

## Review
`review/` PNGs viewed by Claude: die overview + 40x30 um zoom old vs new (clock bodies were on solid M1 OBS, now inside
white windows) and an 80x50 um zoom of the imported ODB (clock + provider bodies all inside windows).

## Not claimed
No std-cell PG access, macro PG closure, IR, DRC, GRT, routed clock/load timing, sign-off or freeze. 0 cycles added.
Next: PG helper's export_overlay.py refresh of native OBS + macro PG pins from `pg_grid/native_grid.odb`, then plan_access --native-overlay.
