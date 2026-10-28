# QC-SMALLREG-1 (METHODOLOGY 12.15d): smaller QC clock regions, each with a plain balanced tree

Base: main 810b714798. Builder is used as-is: die_trial `--tree-form link_htree` plus `balance_legalize`. The clock builder was not edited, because DIE-QC-3 owns those fixes.
Plan: die_plan_sliceclk.json, sha256 5545cbfca017 (QC-SLICECLK-1, the same plan DIE-QC-2 used).
Data: intel2:/srv/opentallas-scratch2/claude/qc-smallreg-1027.
**All numbers are OWN and UNCHECKED.** No independent NUMBER-CHECK has been run.

## Outcome
**Smaller regions bring in-region spread down from 372 to 164 ps TT / 146 ps FF, but not to <= 150.**
- These are grp-map numbers: routed GRT clock, die STA with --cppr-lca, table OCV, shared droop, spice clock x1.0485/x1.0552.
- The ~14 ps that is left over in TT is not caused by region size. It comes from the builder's balance step:
  - `balance_legalize` leaves 1,172 merge nodes unbalanced, the worst by 280 um.
  - Inside each c partition, the 4 glue taps sit on a branch that is 281 um shorter and has one fewer stage than the 24 core taps. At the routed 0.29 ps/um that is 136 ps of nominal spread.
- The row map that COORD preferred measures worse than grp: 229 / 254 ps. Larger regions are therefore not the answer either.

## Region maps (`mkmaps.py`, `maps/`)
- **grp** (DIE-QC-3 grp map): 317 regions.
  - Each c partition (1.24 x 2.61 mm) is its own region.
  - sl partitions are grouped by shared bits into boxes no larger than the c-partition box.
  - HUB partitions are single regions.
- **row**: 221 regions. The two c partitions of one c row are merged (2.47 x 2.61 mm). sl and HUB are as in grp.
- **quad**: 173 regions. Each 2x2 c block is merged (2.47 x 5.23 mm).
- No region can be smaller than grp: a smaller region would cut through a c partition, i.e. through a hard core's glue.
- Feeds come from locality `score --feed fish` (`maps/feed_*.json`).

## ESTIMATE before the build (12.14b)
Columns:
- **est spread**: `est_sr.py` (DIE-KV-3 est_htree method) on ideal builder geometry, at 334 ps/mm, x1.05, with g021 OCV and droop shared inside a region. It is the worst of TT setup and FF hold.
- **cal**: est spread x1.78, the ratio of measured to estimated spread on KV H200B.
- **CA**: locality v3 with the count_align_plan from MESO-RECONCILE @32e8cbb16 (min-ambiguity start tree), spice x1.0485 TT / x1.0552 FF.
- **price**: nativev7 harness (copy of DIE-QC-3's), physical cycles per port, against a 4,051.0 tok/s base.

| map | regions | est spread | cal | crossings | D4 / D8 / FAIL | CA lo / hi | tok/s |
|---|---|---|---|---|---|---|---|
| grp | 317 | 60.8 | 108 | 2,558 | 2,399 / 159 / 0 | 111.0 / 257.9 | 3,771.5 (-6.9 %)* |
| row | 221 | 73.2 | 131 | 2,414 | 2,409 / 5 / 0 | 111.0 / 190.0 | 3,780.1 (-6.7 %) |
| quad | 173 | 98.1 | 175 (48 regions > 150) | 2,001 | (main planner) 1,996 / 5 / 0 | 104.1 / 209.8 | - |

\* The grp price used the main-planner latencies.

- Row cost on critical token paths: the CB16 path goes from 16 to 44 cycles (grp: 49). Slice hops add +51 and l9 adds +9, so the chained layer grows from 8,129 to 8,719 cycles.
- The estimate assumed balanced trees. The build showed they are not balanced.

## MEASURED
Build:
- `runK.sh`: kit with link_htree, rep 250, --tree-site-legal and --tree-site-slide, then a combo GRT with the clock routed (TT + FF, 50 iterations, -critical_nets_percentage 0).
- `postS.sh`: spice-scaled arrivals, proof, and main die_sta_related with --cppr-lca, --clock-ocv table, --clock-droop shared, droop regions = clock regions, and HB4.

GRT overflow is 0 on every layer in every build. Usage is 2.92-2.93 %, with 47,260 clock nets (M8 0.65 %, M9 1.14 %).

| build | per-partition nominal spread x spice, max TT / FF | intra skew TT / FF | seam skew TT / FF | TT intra setup | FF intra hold raw | HB4 cells, TT setup after HB4 |
|---|---|---|---|---|---|---|
| grp leaf 200 | 143 / 125 | **164.2 / 145.7** | 56.1 / 50.9 | +423.8 | -209.5 | 9.76 M + 0.29 M; +203.6 intra / +357.1 seam, hold 0 |
| grp leaf 400 | 150 / 133 | 172.1 / 152.3 | 47.9 / 43.4 | +396.7 | -210.1 | 9.46 M + 0.26 M; +196.1 / +382.6 |
| row leaf 200 | 195 / 173 | 229.3 / 203.6 | 253.6 / 225.4 | +340.8 | -283.6 | - |
| DIE-QC-2 C1w5 (reference) | 372 | - | - | +114 | -476 | HB4 fails setup |

- "landed" rows in sta_*.log are FAIL. They time the plan's 264 slice landings against the old window, which does not apply to these maps. This needs the plan delta (clock_landing_plan.compose with these crossings), which has not been done.
- Builder options swept at placement: none removes the imbalance.
  - leaf 100/150: worst imbalance 978 um, worse. I killed those runs.
  - leaf 250/300: identical to leaf 200.
  - full=1: 7,798 nodes unbalanced.
  - --tree-site-legal without --tree-site-slide: identical to the slide run.

## Root cause (`measured/Ggrp/decomp_*.txt`, `path_*.txt`)
- In c_W2_tn_00, merge nodes b16853 and b16773 sit on the legal x = 10,129 column with `balance_imbalance_um` = 279.8.
  - That is where balance_legalize found no legal point on the zero-skew locus and fell back to site.nearest.
- Path lengths:
  - Glue taps t24-27: 2,471 um and 15 stages.
  - Core taps: 2,727-2,752 um and 16 stages.
- Fit: 0.29 ps/um. Arrival spread is 136 ps, and the residual after removing length is 97 ps, which includes the stage mismatch.
- The same pattern repeats in every c partition. It is a builder balance issue, so it goes to DIE-QC-3.

## Next
- Rerun `runK.sh Ggrp regions_grp.json feed_grp.json --leaf-um 200`, then `postS.sh`, once DIE-QC-3 pushes its balance fixes:
  - balance_legalize must find a balancing site for blocked merges, or detour the short kid leg;
  - M8 R must be corrected.
- If grp then reaches <= 150 ps:
  1. Compose the plan delta (landing cohorts for 2,558 crossings), then run G0C.
  2. Run measured CA with landed_phase_ocv on the routed rows.
- The grp map is the smallest legal cut. Region size is no longer the lever.
