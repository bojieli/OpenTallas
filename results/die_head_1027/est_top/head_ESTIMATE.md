# 12.14b ESTIMATE: head region map / clock feed / crossings (LOCALITY-SCORE-1, analytic, UNCHECKED)

Inputs: plan /srv/opentallas-scratch2/claude/land-head-1/compose/fb1_lat.json (sha256 d472fcc1beda), 326 partitions, 427 ports; trunk delay v = 340 ps/mm TT (measured, see LOCALITY.md); P = 833 ps, budget P/2; face supply 6 pins/um.
Model: tools/die_plan/locality.py docstring (equal-length region trees from the box centre, I = v (w+h)/2; fwd = neighbour-forwarded max-bit spanning tree, top = one balanced die H-tree; margins by landed_phase_ocv.analyse with clk_aocv g021 + droop regions + core latency class B). Off-feed = a crossing whose two regions are not parent/child in the feed tree (its last common point sits up the tree).
Calibration (CHECKED vs measured, top feed): HEAD part map -59.9 TT / +17.2 FF, 33 < 100 vs LAND-HEAD-2 d=0 bound -60.7 / +13.3, 33 < 100; KV land128 -52.5 / +23.7 vs LAND-KV-1 perfect-balance bound -136.4 / -47.1 (model 6.2 ns unshared vs 7.2 ns built: the model is ~70-85 ps optimistic where the built tree is deeper than an ideal H-tree).

| map | feed | regions | max span mm | max I ns | bit-mm inside | crossing ports / pairs | far ports | off-feed ports | worst unshared ns | RAW TT/FF | FOLD TT/FF | PAD TT/FF (unsh. ns, max pad) | FOLD <100 TT/FF | PAD <100 TT/FF | track ratio worst (>1) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| f3_27 | top | 27 | 8.66 | 1.89 | 78.9 % | 93 / 52 | 0 | 93 | 7.03 | -140 / -47 | -140 / -47 | - | 81 / 55 | - | 0.234 (0) |

Readings: RAW = today's ring with unfolded nominal d; FOLD = count-aligned crossing (d - kP, one k for TT and FF); PAD = forwarded hops padded to whole cycles at TT (pad = clock delay, charged as unshared). The gate stays 12.13d (measured landed_phase_ocv >= 100 ps TT and FF on every crossing after GRT).

Worst crossings, f3_27 (top, FOLD): R07->R10 565 b, unshared 7.03 ns, d 0, p 557/464, margin -140/-47; R10->R07 565 b, unshared 7.03 ns, d 0, p 557/464, margin -140/-47; R07->R10 277 b, unshared 7.03 ns, d 0, p 557/464, margin -140/-47; R10->R07 276 b, unshared 7.03 ns, d 0, p 557/464, margin -140/-47; R07->R10 64 b, unshared 7.03 ns, d 0, p 557/464, margin -140/-47
  Tracks: worst boundaries R07|R10 1939 b over 1382.4 um face = 0.234x supply; R04|R10 1939 b over 1382.4 um face = 0.234x supply; R07|R19 3324 b over 3145.0 um face = 0.176x supply; crossing bits by region hops {1: 36348}

Verdict rule (12.14b): build a map/feed only if its estimated PAD or FOLD margin is >= 100 ps TT and FF on every crossing and its track ratio is <= 1; otherwise fix the map (smaller span, cut along low-traffic seams) first. Every number on this page is an ESTIMATE (UNCHECKED) until a GRT + landed_phase_ocv run.
