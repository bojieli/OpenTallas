# OSS-CLOCK-3 task 3: street-aware local routing in opentools/mscts (QC E0 slice)

Run: intel2:/srv/opentallas-scratch2/claude/oss-clock-3-1027/E0_street_fix (`mscts.run build qc_E0_spec.json --balance-at tree`,
docker python:3.12-slim, 8 GB cap). OpenSTA (orfs:asap7lock, INVBUF RVT NLDM) on intel1, same dir name.
Labels: CHECKED-own = measured by this lane from the files named here; UNCHECKED = not independently re-checked.

## Root cause (OSS-CLOCK-2 build: snake 15.8 %, 49 stages > 480 um, max 759.5 um)
- Merges routed as x-first L paths. Over the 462 x ~1162 um core keepouts an L path has long vertical runs with no
  legal repeater site -> stages up to 760 um; repeaters slid out of keepouts gave unequal stages.
- Merge points were then moved off keepouts along the L path and rebalanced -> merge snakes 32.2 mm; leaf balance
  11.8 mm; legal_rebalance 15.0 mm (re-equalising the slid repeaters).

## Fix (general, no QC-specific code)
- `mscts/street.py` Router: monotone staircase candidates (2 L's, Z through a street column/row next to a keepout
  edge, 3-bend column+row); score = (unrepeatable span over reach, bends, span). Repeater placement `place()`:
  fewest equal stages >= ceil(L/reach), sites snapped to the nearer keepout edge, no stubs. If the child pin is inside
  its own keepout, the snake tail counts as blocked too (repeater snaps to the edge, not onto the pin).
- `region.py` street merge: merge point = legal point on the DME merging segment chosen by route score; a balanced
  off-box detour point when the segment is blocked and cheaper than a snake; delays from the exact placed stages
  (secant/bisection, with one extra repeater on either side to cross the stage-count delay step); merge cost
  max(D, 2*unit*dt) + blocked-site penalty.
- `trunk.py`: exact-stage leaf balance and `--balance-at tree` (balance at trunk branch points instead of every leg).
- `legal.py` keeps the merge-time stages; ledger adds stages / stages_over_rep / detours. `--no-street` = old path.
- Tried and dropped: off-box jog routes when no monotone street exists (snake 54.8 mm, detours 36.9 mm on E0);
  kept as `Router(jog=True)` opt-in only.

## E0 slice (584 sinks, 80 keepouts, 78 crossings)        legacy (OSS-CLOCK-2) -> street (this)
| metric | legacy | street | label |
|---|---|---|---|
| snake / tree wire | 15.8 % | 16.63 mm / 333.4 mm = 4.99 % | CHECKED-own |
| (snake + detour) / wire | - | 5.4 % (9 detour merges, 1.34 mm) | CHECKED-own |
| tree wire | 374.2 mm | 333.4 mm | CHECKED-own |
| nodes (incl. 584 sinks) | 1607 | 1531 (615 merge + 331 rep + root) | CHECKED-own |
| max stage | 759.5 um | 463.3 um | CHECKED-own |
| stages > 480 / > 450 | 49 / - | 0 / 62 of 1522 (horizontal crossings of 462-um cores) | CHECKED-own |
| buffers inside keepouts | - | 0 (render count + view) | CHECKED-own |
| OpenSTA latency skew TT / FF | 30.6 / 26.6 ps | 39.3 / 21.6 ps | CHECKED-own |
| model skew TT / FF | - | 1.0 / 20.8 ps | CHECKED-own |
| worst crossing margin TT / FF (model, OSS-CLOCK-2 metric) | 228.6 / 243.6 ps | 233.1 / 251.4 ps, 0 of 78 < 100 | CHECKED-own |
| crossing d model vs STA max TT / FF | - | 6.8 / 2.2 ps | CHECKED-own |

- STA TT skew 39.3 ps is model scatter, not structure: model - STA per sink sd 4.8 ps (legacy 4.6 ps); regression on
  short stages -0.8 ps/stage, on wire +6.1 ps/mm. Next step for skew is the stage delay model, not routing.
- `--balance-at leaf`: snake 6.2 %, STA skew 38.3 / 21.5 ps, margins 233.1 / 251.6 ps (CHECKED-own).
- Quarter sub-slice L2_3283 (144 sinks, 8 crossings, `mscts_subslice.py`): OpenSTA skew TT 21.5 / FF 13.6 ps,
  model/STA 1.025 / 1.04 (CHECKED-own). ngspice TT: see the end of this file.

## Renders
`mscts_E0_street.png` (whole slice), `mscts_E0_street_zoom.png` (x 17300-18900, y 9900-11400, small macro keepouts):
viewed; repeaters on street edges, 0 inside keepouts. `mscts_render.py tree.json spec.json out.png [x0 y0 x1 y1]`.

## Tests
`cd opentools/mscts && python3 -m pytest -q tests`: 14 passed (5 new street tests).
