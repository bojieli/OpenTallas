# INFRA-FIRST-QC-R34 (2026-10-27 18:00-19:05 PDT)

Base: claude/qc-infra-r33-1027@bfc57feb37 (R32 export window 3 / tol 30, trunk_escape 100, R31 dry15c plan).
Data: intel2:/srv/opentallas-scratch2/claude/qc-infra-r34/. All runs are my own dry builds (die_clock_mesh build, collect-all
plan errors). Numbers below are UNCHECKED unless marked.

## Result: dry18 682 -> 266 no_clock_track. Not 0, so no GRT and no STA.

| run | change (all opt-in, default output unchanged) | no_clock_track |
|---|---|---|
| base | R32 dry16_w3t30 packet, this branch's builder | 682 (reproduces R32; CHECKED) |
| v1 | builder: merge_collinear_m8 | 574 |
| v2 | + escape_alt_side | 424 |
| v3 / v5 | + escape_avoid_16w (planned 16w rows), +- more offsets | 735 (worse) |
| v4 | v2 + escape offsets 4.32/8.64/12.96/17.28 | 424 (no change) |
| v6 | v2 + escape-first only for 16w | 567 (worse) |
| **d18_r2** | v2 + export --top-rep-col-clear 2 | **266** |
| d18_r3 | v2 + --top-rep-col-clear 3 | 269 |
| d18_r2b6 / r3b6 | + --a0-band-row-clear 6 (band row x-trees off top-leg rows) | 306 / 293 (worse) |
| d18_r2 e200 / e400 / true | trunk_escape 200 / 400 / window-full only | 269 / 570 / 527 |

Export with no new options: cells and nets identical to the R32 dry16 spec. Only `summary` differs (tool sha and the new stats
key); CHECKED by a key-wise compare. Every R34 export: geometry PASS, reach 448.524. Band residual TT median is 35.2
(--a0-band-row-clear runs: 34.6), max 144.1, unchanged. 56 clock tests PASS (test_explicit_clock_v2/_mesh,
test_qc_clk_mesh3(_export), test_die_clock_mesh_r13).

## Fixes and root causes found
- (c) The real cause of R33's 104+ "top_node escape drop drv" was not escapes landing on 16w lanes. A top x-tree node drives
  two collinear 16w M8 legs (west and east) of ONE logical net. They were routed as two V2 branches; each escaped on its
  own, and both needed an M9 drop at the SAME driver bar column. Fix (`merge_collinear_m8`, builder): two
  opposite-direction M8 legs of one net with the same NDR become one straight trunk through the driver. Electrically this
  is the same pair of legs from the driver tap, with no cell or stage change. This also cleared 88 of the 96
  col_node-under-leaf-leg errors (R33 class (a)), because the leaf legs no longer escape separately.
- Fix `escape_alt_side` (builder): a cell already linked to an escaped trunk on one side takes its next escaped trunk on
  the other side (repeater in/out, node parent/kid).
- R33 (c) as literally specified (skip lanes holding a PLANNED 16w trunk) made it worse: 735.
- Fix `--top-rep-col-clear N` (export): a horizontal top repeater within N island x-pitches of a column-tree column moves
  N pitches clear of it, along its own row. 240 reps move, max 8.91 um; the two adjacent segments change by up to 8.9 um.
  This was not re-priced (UNCHECKED, estimated well under 2 ps).
- R33 (b) as `--a0-band-row-clear` (band row x-trees on the nearest slot row with no top leg): worse, 306 / 293. Not
  adopted.

## Why the remaining 266 do not clear by position (diagnostic OT_V2_BLOCKERS=1: d18_r2_plan_errors_blockers.json)
The M8 PG grid has a stripe every 4.32 um (alternating VDD/VSS, 0.48 um wide). Each PG gap holds at most one 16w shielded
wire. Every gap lies inside the +-2.5 um pin window of one island slot row (rows are 8.64 apart). So no escape track sits
outside all windows: an escaped trunk at +-7.32 is in the neighbour row's window, and the failures cascade.
Example: top_rep ckt_17675 at (2779.4, 1321.4). Its out-net driver jog is blocked by:
- the VSS stripe at 1321.92;
- an escaped band 8w trunk ckm_w_ckt_23073 at 1323.00, spanning x 2727-2993;
- its own in-net jog at 1320.84.

Remaining classes (d18_r2_classes.txt):
- 106 + 17 top_rep escape jog drv (frame x 318 / 308);
- about 64 top_node at frame x 627-629 (escape jog/drop to its kids);
- 18 band_node escape jog;
- 11 chan_node trunk;
- the rest small.

## Next (needs a COORD ruling: plan-level)
COORD's layer-separation fallback is the right direction, but horizontal runs must stay on M8 (M9 is vertical only), so
"band on the other layer" cannot apply to horizontal band rows. Two plan-level forms:
- (A) ROW ALLOTMENT: in the master plan, reserve whole M8 slot rows (window + gap) per tree class. 16w top-tree horizontals
  get dedicated rows with no other island cells; band and column cells get the others. This is a plan reservation, not an
  ECO.
- (B) Flow-oriented repeaters: orient each horizontal-leg repeater MY/R180 so A faces the incoming leg. In and out trunks
  then share one track with no escape. The predictor's unit_sites and clock_routed.pin_point model only R0/MX today, so (B)
  needs MY support in those tools.
