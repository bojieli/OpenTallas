# INFRA-FIRST-HEAD-2 R2: s81_head plan delta, qc_clk_mesh3 generalised, first head global tree (D-INFRA-FIRST-HEAD)

Branch claude/infra-head2-1027 (off INFRA-FIRST-HEAD-1 a80ab81733 on main 262d070384; tool file qc_clk_mesh3.py taken
from claude/qc-mesh-r17-1027@75c9eca9a6, where main == R13's copy, so R17's is a strict descendant). Run dir
intel2:/srv/opentallas-scratch2/claude/infra-head2-1027; QC regression epyc2:/srv/opentallas-scratch2/claude/infra-head2-qcreg.

## 1. Plan delta (PLAN-DELTA D-INFRA-FIRST-HEAD, candidate) -- `tools/s81_head/head_infra_delta.py`
- **The ruled move (elemB origin x 216.00 -> 211.68) FAILS G0C**:
  `hard_cores: origin [211.68, 734.4] not on the 8.64-um lattice`. 211.68 / 8.64 = 24.5, and `track_offset_um` may only
  carry a shift below 2.16 (schema BASE_LATTICE_UM). The root cause is the rebuilt elemB outline: 285.12 = 33 x 8.64
  is an odd multiple, so its geometric centre can never sit on the on-lattice tile axis 354.24 with an on-lattice
  origin. The move is kept as `--eb-move` for the record (`data/g0_Amove_*`).
- **Lattice-legal equivalent (applied; plan sha256 674a8ac9...)**: there is NO origin move. Instead the eB clock entry is
  pinned at the tile MY axis: tile x 354.24 = origin 216.00 + core-local 138.24, which is 4.32 um west of the
  geometric centre and on the core's own 8.64 lattice. The island set is then MY-invariant (asym 0.000) and gives the
  same lattice as the R1 census: 66 columns (33 per half), 36 rows.
- Core clock taps move to the 12.8a centre entries (tile frame): eA (177.12 | 531.36, 168.48 | 540.00), eB
  (354.24, 876.96). `core_taps: early` is removed. Insertion = the die common 250, **PENDING** (see 4).
- hd_serdes tap (1442.88, 613.44) inside VDDPHY -> (1442.88, 77.76). This is in the 150-um CORE-VDD digital strip,
  since the VDDPHY zone starts at type-frame y 213.64. Viewed in render/r2_serdes_zoom.png.
- G0/G0C on the delta plan: PASS 0 errors / 6 warnings, 16/16 types clean, cuts unchanged (0.0637 / 0.3587).
- Core outlines are NOT swapped to 319.68 / 285.12. A swap with the old 317.672 pin tables puts 325 pins per MX core
  off the M4 track phase (G0C 19 errors). The outline swap has to come with the rebuilt cores' pin tables, at their
  signed views.

## 2. qc_clk_mesh3 generalised (COORD ASK1)
- The QC constants PER_X / PER_OFF / CHAN_HC / CHAN_LANES / PER_NUDGE, plus the r2 row-group 19, become `--per-x
  --per-off --chan-hc --chan-lanes --per-nudge --row-group`. The default None keeps the QC values (`QC_LATTICE`,
  `set_lattice()` at build start).
- New `grid` subcommand (`grid_tree` / `grid_report`): a delay-balanced zero-skew tree over any drive grid (n//2 split
  + merge() node-on-segment balance + equal stage count). It builds row x-trees, then one y-tree on the trunk column,
  then the source leg.
- **QC regression: byte-identical.** `qcreg.sh` runs `plan` with the R17 d43b args on the R17 tool and on this tool,
  both mounted at the same path. r3_plan.json fe8614d4... is identical and the log 025bdfae... is identical (cmp).
  Explicit QC-default flags differ only in the recorded argv.
- Tests: test_qc_clk_mesh3 10/10 PASS. 4 are new: QC defaults unchanged, explicit flags parse identical, 11x12/half
  non-2^n grid balanced, 3x5 odd grid.

## 3. PG -- NOT DONE this round
No head-specific worst-case power and no PDNSim wider-stripe sweep yet; the R1 70%-of-M9 grid stays rejected. Owed:
- power from the head netlist activity, per type (hd_tile 1.07 M cells; elemA/elemB GRT views);
- a PDNSim sweep over fewer, wider M9 stripes with the clock lanes locked to VSS (QC R14 form);
- 35 mV budget, reporting M8/M9 track share.

## 4. Clock entries vs the rebuilt cores (finding)
The hold2 / R12 kits have EDGE clock pins (read from the kit pins.json):
- elemA: clk M5 at N (293.58, 317.576), DIE_AREA 319.68;
- elemB: clk M4 at W (0.042, 257.58), DIE_AREA 285.12.

So no centre-entry real view exists, and every core tap insertion is PENDING. For reference, elemB GRT max-rise from
the edge pin is 252.55 TT / 196.95 FF (HEAD-CORE-R10, CHECKED there). It is not valid for a centre entry. The 12.8a
clock_entry gate will FAIL until the cores are re-pinned at the centre M9->M5 island (elemA core-local (159.84, 159.84),
elemB (138.24, 142.56)).

## 5. First head global tree (plan model) -- `qc_clk_mesh3.py grid`, render viewed
Drive grid = eB entry of every hd_tile, 22 x 12 (11 x 12 per half, mirrored about x 8760.96), source = the plan spine
root (8760.96, 8778.24). 16W, 2x BUFx24, reach 450 (R17 solve setting). Renders: render/r2_tree.png and
r2_tree_zoom.png. The view shows: x-trees on every eB row, one y-trunk in the spine gap at x 8762.8, a 360.8-um source
leg, and all legs straight.

| item | value | status |
|---|---|---|
| eB move G0C | FAIL (origin 211.68 = 24.5 x 8.64) | CHECKED (arithmetic) |
| delta plan G0/G0C | PASS 0 err / 6 warn, 16/16 | UNCHECKED (tool) |
| eB entry on tile axis, MY asym | 354.24 = 708.48/2, asym 0.000 | CHECKED (arithmetic) |
| island lattice | 66 cols, 36 rows, col pitches 177.12/354.24/1736.64 | UNCHECKED |
| QC plan byte-identical | r3_plan + log cmp equal | CHECKED (cmp) |
| unit tests | 10/10 PASS | CHECKED (run) |
| rebuilt core clk pins at edges | A N(293.58,317.576), B W(0.042,257.58) | CHECKED (kit pins.json) |
| tree stages / repeaters / wire | 36 stages, 696 reps, 464.8 mm | UNCHECKED |
| plan-model arrival TT / FF | 3123.6-3124.2 / 2515.1-2515.6 ps | UNCHECKED |
| nominal driver skew TT / FF | 0.63 / 0.44 ps | UNCHECKED |
| tree sites on islands | 432 of 1224; **552 on hard cores** (tree_on_islands FAIL) | UNCHECKED |

## Not done / next (R3)
1. **Island-quantised tree.** Nodes and repeaters must sit on declared islands (12.2a1). One option: put the row
   trees on the eA rows, which have islands every 354.24 (<= reach 450), and give the merge the QC Islands-style
   snapping. Then mesh drivers at eA or eB islands.
2. Continuous mesh build (straps on every island row and column), master-plan --mesh gates, GEOM REQ of the built
   mesh.
3. PG as in 3.
4. Die GRT >= 50 iterations incl. clock via ot-run, mesh MC, related-pair STA (0.21 %/mm AOCV, droop per mesh).
5. Core re-pin at the centre entries (HEAD-CORE) -> real insertion -> taps.
