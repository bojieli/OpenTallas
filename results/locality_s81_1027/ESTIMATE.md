# S81 locality estimate (12.13 / 12.14b), DIE-S81, 2026-10-27

This is an analytic estimate made before any build. No GRT was run and no plan event was made. Every number here is UNCHECKED (my own script and nobody else's) unless marked otherwise.
Input: the land-s81 plan `claude/land-s81-1027@20a7f28c24` (physical/die_plan/s81/die_plan.json: 398 parts, 2,306 ports) and its 179-region map (results/land_s81_1027/regions/regions.json).
Script: `scripts/s81_locality.py` (traffic matrix, locality score, link-following feed estimate and greedy proposer), plus the renderer `scripts/render_s81_locality.py`. Both are minimal, local and handed over to LOCALITY-SCORE-1 (tools/die_plan/locality.py had not landed).

## Model
- **Traffic.** For each plan port, bits = width and bit-mm = width x Manhattan distance between the part centres. Summed over part pairs this gives 472 pairs, 1,105,401 bits and 1.62 M bit-mm.
- **Unshared clock U per crossing.** U = the larger side of: the feed path from the LCA region root to this region's root (ps/mm x Manhattan + 60 ps per forwarding hop), plus root to part centre, plus core latency (250 ps TT).
- **Derated margin.** margin = P/2 - 0.095 x U, assuming nominal d = 0 (balanced). The 0.095 is calibrated on two points: KV (5.66 ns gives -136 ps) and the HEAD guidance (3.4 ns gives +100 ps). Pass means margin >= 100 ps.
- **Wire speed.** The plan model D0+K·L at 450 um spacing gives **176 ps/mm**. Routed GRT-RC is measured at **321 ps/mm** on KV and **335 ps/mm (median), 349 ps/mm (aggregate)** on HEAD (LAND-HEAD-1 sl300 out_TT arrivals, 1,666 segments over 200 um; my measurement). The routed number is the real one.
- **Feed.**
  - die-tree: the current form, with every region root fed from the die-centre source.
  - link-following: clock follows data. The feed is a shortest-path tree over the region link graph, rooted at the region nearest the die centre ("spt"). A maximum-traffic spanning tree ("maxbits") was also tried and is worse.
- **Proposer.** Greedy merging of regions, heaviest crossing first. A merge is allowed only if the merged bbox span is <= S and fill >= 0.5. The hard PHY region is kept as it is.

## Results (part-pair crossings; LAND-S81-1 counted 1,173 ports on the 239 pairs of the 179 map)
| map | regions | bits inside | bit-mm inside | crossing pairs | die-tree fail @321 | link-feed fail @176 | @250 | @321 (worst) |
|---|---|---|---|---|---|---|---|---|
| current (LAND-S81-1) | 179 | 48.6 % | 47.6 % | 239 | 202 | 6 | 15 | 27 (-278 ps) |
| **regrouped S=4.4 mm** | **98** | **60.1 %** | **57.8 %** | **157** | 124 | **3 (+40)** | 18 | **28 (-205 ps)** |
| regrouped S=6.0 mm | 60 | 75.3 % | 72.6 % | 106 | - | 3 (+95) | 21 | 42 (-141 ps) |

- **Regrouping by connectivity works on traffic.** At S=4.4 mm, crossing bits drop from 568.5 k to 441.5 k and the number of crossings drops by 34 %.
- **The die-tree form fails whatever the region map.** 124-202 crossings fail, the same root cause LAND-S81-1 found.
- **Clock-follows-data closes the tree edges.** Of the 113 tree-edge crossings (SPT @321), 112 pass. The one that fails is svc_12->svc_13, at +58 ps, set by the insertion of the 11.5 mm PHY region (1.6-2.7 ns).
- **The failures are the cycle-closing links.** Of the 44 non-tree crossings, 27 fail at 321 ps/mm. They sit in the central slice spine (x 9-23 mm): the N<->S slice links across the y = 12.4 mm cut, the E-W slice neighbours s_2S<->s_3S, and the PHY-band links eng/iqf/svc_0 -> svc_14/svc_2. See s81_locality_spt321.png (viewed). All frame/column regions pass.
- **Hop-chaining the failing links along the tree is too expensive.** At 321 ps/mm it costs +114 crossings and +1.29 M bit-mm (+80 % of all bit-mm). At 176 ps/mm it costs +21 crossings and +0.13 M bit-mm.
- **Band FAILs.** The regrouped map removes 2 of the 20 ring storage-band FAILs (svc_hi t2 attn_i2 and col_h10_r1 frame_int_i1). 18 remain, so the svc13/PD7f band-room delta is still needed.

## Verdict
**At the measured routed wire speed the estimate does NOT pass (28/157 fail, worst -205 ps), so no build.** It would pass with 3 hop-chains (+21 crossings) only if the region-feed links ran at <= ~180-200 ps/mm.

Three things could make it feasible. Any one is enough for the 27 cycle-closing links, and PHY-region insertion needs a spine either way:
1. MESO-COUNT-1 proves count-aligned crossings, which absorb the whole-cycle unshared clock on the non-tree links.
2. A fast feed-link wire class (M9, wide wire, upsized repeaters) is measured at <= 200 ps/mm on GRT-RC.
3. The central slice spine is regrouped into N/S column regions that contain the centre cut, and the feed is routed along the slice pipeline order. This is a proposer target for LOCALITY-SCORE-1.

The PHY region (phy_hbm+eng+iqf+svc_2..12, 11.5 x 3.7 mm) needs its own spine along the band in every case.
