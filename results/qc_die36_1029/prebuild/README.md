# DIE-QC-36 — QC-001 clock prebuild: legal column-aware clock-cell re-site + router-track backbone

Run root intel2 `/srv/opentallas-scratch2/claude/die-qc36/` (inputs as DIE-QC-35 `results/qc_die35_1029/prebuild/README.md`).

## 1. Legal re-site of the stacked clock cells (CHECKED, `dqc36_resite.py`, `resite_report.json`)
- Objective = DIE-QC-35 what-if (no two different-net clock pins in one M7 column |dx|<=0.064 um within DY 4.4 um = one M8 PG
  pitch), now LEGAL: whole-site x shift in the same row on the site grid, no overlap with any other clock cell (post-move) or
  any of the 48,259 provider (non-clock) placed cells, unchanged partition containment, and the cell stays wholly inside its
  own clock-island window (`islands119_cellmap/cell_windows.json`, 3.132 x 2.43 um holes) -> PG islands stay valid.
- Result: 44,590 cells, **4,078 moved, 0 unresolved, 0 still stacked (independent recount), 0 overlaps, 0 outside island,
  0 partition-edge change, max 0.324 um (6 sites)**; baseline also 0 overlap / 0 off-grid. Shift histogram in the report
  (-6:111 -4:341 -3:44 -2:947 +1:58 +2:2005 +3:30 +4:388 +5:34 +6:120). Connectivity untouched (sites only; clock graph
  sha256 00b9a8d6...), so the strict bind graph is unchanged. Output tree `resite/tree_resite.json` sha256 48b559ec...
- Odd-site shifts are fine: original sites are 35,811 even / 8,779 odd, provider cells 28,883 / 19,376.

## 2. E1 = fixed_tree_provider on the legal sites, no backbone, no PG access (unit oth-ubuntu-2639643, `run_e1_resite_noaccess.sh`)
- Track stage **PASS**: fixed_wires.json for all 44,591 nets (render `prebuild_e1_resite_noaccess/review_region.png` VIEWED:
  c_E2_bf_10 trunks in streets / over macros on M8/M9, continuous, no stray metal). [CHECKED run.log]
- Next stage FAIL `pin-access shorts` (expected, same as DIE-QC-35 d4 what-if): encoder census 535 shorts / 89 spacing over
  1,686,945 shapes, 20,707 top-access conflicts; column clips 2,108/89,180. The legal re-site reproduces the what-if; what is
  left is the M6-entry jog layer (VIA78 landings on PG straps) = step 3.

## 3. Backbone re-derivation, witness = router track (`dqc36_backbone.py`, fork of Codex jog_backbones --joint-clock --all-bases)
- Same geometry proof (island union coverage, M6/M7 SIGNAL/OBS/PG/future-column clearance, M8 0.192x0.08 landing, 0.08/0.32
  shielded witness) but the M8 witness = the router trunk/driver track of that pin (E1 `stacks[].riser_from` y), so each M7
  window contains the track the shared trunk uses (DIE-QC-35 cause 1). Fallback to the nearest witness only when no column at
  the router track is clear (counted). Old-site M1..M7 clock base stacks are shifted with their cell. Emits backbone_plan.json,
  joint_clock_reserved.json (input of plan_access --joint-clock-reserved) and clock_base_resite.json.
