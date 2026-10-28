# LAND-KV-2: KV landed form (12.13 locality first): rep spacing, connectivity regroup, feed study

Work dir intel1:/srv/opentallas-scratch2/claude/land-kv-1027. Tools are main 9dc6da3a13 (droop derate merged, RM-82) plus
the LAND-KV-1 band_reserve="live" commit. Shared steps only, no forks: die_trial kit --rep-um, compose, cells_fix,
gen.py latency, check.py, mk_combo GRT (50 iterations, -critical_nets_percentage 0), landed_phase_ocv (LAND-HEAD-2),
main die_sta_related (--clock-ocv table, --clock-droop shared, default --data-droop class, HB4).
All numbers come from my own runs and are UNCHECKED (no NUMBER-CHECK yet).

## Runs
| Run | Regions | Rep (um) | GRT ovfl TT/FF | Clock nets >320 ps slew | LPO worst TT / FF | fail<0 TT (nominal / OCV-only) | root-LCA |
|---|---|---|---|---|---|---|---|
| L (LAND-KV-1) | 128 | 405 | 0/0 | 74 (worst 684) | -808.7 / -649.1 | 598 (93 / 505) | 189 |
| R25 | 128 | 250 | 0/0 | 1 (684, sys_c root leg) | **-709.2 / -543.0** | 558 (92 / 466) | 189 |
| G2 | 51 (regroup) | 250 | 0/0 | 1 (764, slid-root leg) | -934.1 / -717.4 | 626 (182 / 444) | 294 |

- Rep 300 left 69 nets at 333-341 ps, all on fan-out-2 branch legs. Rep 250 clears all of them except one.
- The remaining net is an 800 um leg where a slid region root stacks its repeaters at both ends of a hard core (the sys_c root in R25, r3715 in G2). This is a site-slide placement issue, not a spacing issue.
- G2 plan: pd/landed2.json (sha in plans.sha256). Compose has 0 placement failures. G0C PASS (0 errors) once the latency table was regenerated with gen.py. Types go 60 -> 77. Abutted pin check PASS.

## Die STA (main die_sta_related, MODELLED: 0 real views, droop class derate applied)
| Run | intra TT setup / FF hold | seam TT setup / FF hold | HB4 intra / seam (TT setup, FF hold) | LANDED window TT / FF |
|---|---|---|---|---|
| R25 | +441.5 / -170.5 | +414.7 / -181.7 | +311.7, 0 / +272.9, +0.15 | -555.1 / -433.9 |
| G2 | +46.9 / -514.7 | +167.0 / -409.5 | +16.3, 0 / +84.5, 0 | -571.6 / -427.0 |

## Locality study (regroup_lk2.py, regroup_map_lk2.py)
- Baseline map: 128 groups, 3595 cross-region ports, 519k bits. Only 9.1% of bit-mm stays inside a region (span median 1.5 mm).
- Convex greedy merge by bits, under a 3.5 mm span cap: 51 regions, 1901 crossings (-47%), 263k bits, 55% of bit-mm inside a region.
- Under the die H-tree feed this makes landed timing WORSE:
  - Bigger regions put more crossings under the root split (189 -> 294).
  - Deeper local trees widen intra/seam skew (548 ps).
  - So regrouping only pays together with a feed that is not a die-wide tree.
- Top cut: 189 crossings straddle y = 13.5 mm (the hub). The minimum over 30-70% of the die height is 145, at y = 11.6 mm.
- Link-following feed (feed_model_lk2.py, ANALYTIC). Feed = max-bit spanning tree of the region link graph, rooted at hub_C. OCV coefficient k is fitted on the LPO rows (median 0.05, max 0.078 of unshared).
  - Unpadded forwarded hops in the current zero-centred window: EVERY tree-edge crossing fails nominal. The hop delay alone is above P/2 (1166 of 1166 on G2).
  - Whole-cycle-padded hops with count-aligned landing: non-tree graph edges still sit 3-13 tree hops apart. Worst -184 (k 0.05) / -521 (k 0.078); 185-313 crossings under 0 on G2. The 128 map is worse: tree depth 28, worst -671.
- => No feed tree passes the >=100 ps gate with the current ring window on an 11 x 27 mm KV die. The crossing tolerance must come from MESO-COUNT-1 (calibrated or count-aligned phase).

## State to keep
R25 is the best measured landed KV form: 128 groups, rep 250, GRT0 incl clock TT+FF. Its plan is unchanged from LAND-KV-1.
The G2 regroup map (c3500_regions.json) is ready for whichever feed MESO-COUNT-1 / LAND-HEAD-3 lands.
