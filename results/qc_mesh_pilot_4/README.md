# QC-MESH-PILOT-4 (2026-10-29): M6-jog failure classification + mesh-pilot verdict

All numbers UNCHECKED (NUMBER-CHECK pending). Diagnostic only: no plan, tool, gate or design change; no build.

## 1. Codex M6-jog diagnostic (adopted, intel2 unit oth-ubuntu-1052760, EXIT 0 02:05)
Input = 484 clock-island base pins with no PG-clear M8 track (prebuild26_columns/base_feasibility.json).
Result jog26/backbone_plan.json: 24 solved / 460 FAIL (251 cells; 24 cells have any pass). Not adoptable (status FAIL).

Classification: jog_backbones_diag.py = Codex jog_backbones.py (8ee contents) with per-candidate stage/obstacle
logging only; it reproduces 24/460 exactly. Per failure (19-20 M7 columns within +-0.7 um x 29-30 M8 tracks in the island):
- deepest stage reached: M8 shielded-tree witness (router.place M8 .08/.32) for 460/460; M6 jog + M7 riser clear on
  nearly every column (nearest column: 442 reach M8, 18 first blocked by a future straight-column M7 reservation).
- riser attempts: 251,986 M8 place fail, 9,097 M7 riser hits reserved power access, 184 hits future columns.
- m8probe.py: same candidates against (a) empty M8, (b) die PG only, (c) PG + reserved power access
  (access119_minarea/reserved_access.json): 460/460 solvable with PG only (median 160 legal (column,track) pairs),
  0/460 with power access. Each 3.13 x 2.43 um island has 14-40 (median 31) reserved M8 power-access shapes within
  0.4 um (0.192x0.04 min-area patches, 0.054/0.04 stubs, 3.316-um M8 bars), which with the 0.32-um shield spacing
  leave no M8 track.
FIRST OBSTACLE = reserved physical power-access M8 patches inside/around the clock islands (not M6/M7 signal/OBS,
not die PG). M6 jogs cannot fix it (they move x by <=0.7 um; the conflict is M8 tracks across the whole island).
Fix class: joint clock/power access reservation -- keep the island M8 band (>=1 shielded .08/.32 track per island,
plus witness) out of the power-access planner, or move those patches to the island edge. Owner: QC PG-access planner
(Geom agent) with ROOT physical-clock; not this lane.

## 2. Mesh-pilot clips (inherited, collect only)
| trial | clips EXIT0 | design DRC | note |
|---|---|---|---|
| A3 (verdict trial) | mid core c0 c1 c3 (5/6) | 0 | c1 EXIT0 ~02:30 and c3 01:44: 2 M9 MinStep each on net n_in = clip entry harness. c2: Codex 40 GB retry live (intel1 codex-qcmp3-a3-c2retry-907923, 42nd guide iteration, 14 viol, 8.8 GB at 02:37) |
| A2 (reserved-leg) | 6/6 | 18 M8 MinStep in c2 | c2r was run with -droute_end_iter 4 (5 iterations): unconverged route, not proof of a structural class; every fully iterated clip on A2/B/A3 ends harness-only |
| B | 5/6 | 0 | c2 OOM 137 twice (24/40 GB) |

Pair U (A2 full DRT, 60-sample MC, Codex): 43.35 TT / 41.36 FF ps <= 61. A3 GRT (PILOT-1): 51.3/48.3.

## Verdict for DIE-QC-27
Timing condition met (pair U <= 61 on routed arrivals) -> mesh PLAN work for the 192 A0 regions may proceed
(reserved M9 tree-leg track + plan-computed core-tap join, COORD 21:41). Region BUILD stays held until a
c2 column routes DRC-clean at full iterations (A3 c2retry) -- the only open physical item; W180 hold buffering
is the fallback only if that c2 shows a real design DRC class. Duty/both-edge and full-die signoff remain unqualified.
