# 12.14b ESTIMATE: head region map / clock feed / crossings (LOCALITY-SCORE-1, analytic, UNCHECKED)

Inputs: plan /srv/opentallas-scratch2/claude/land-head-1/compose/fb1_lat.json (sha256 d472fcc1beda), 326 partitions, 427 ports; trunk delay v = 340 ps/mm TT (measured, see LOCALITY.md); P = 833 ps, budget P/2; face supply 6 pins/um.
Model: tools/die_plan/locality.py docstring (equal-length region trees from the box centre, I = v (w+h)/2; fwd = neighbour-forwarded max-bit spanning tree, top = one balanced die H-tree; margins by landed_phase_ocv.analyse with clk_aocv g021 + droop regions + core latency class B). Off-feed = a crossing whose two regions are not parent/child in the feed tree (its last common point sits up the tree).
Calibration (CHECKED vs measured, top feed): HEAD part map -59.9 TT / +17.2 FF, 33 < 100 vs LAND-HEAD-2 d=0 bound -60.7 / +13.3, 33 < 100; KV land128 -52.5 / +23.7 vs LAND-KV-1 perfect-balance bound -136.4 / -47.1 (model 6.2 ns unshared vs 7.2 ns built: the model is ~70-85 ps optimistic where the built tree is deeper than an ideal H-tree).

| map | feed | regions | max span mm | max I ns | bit-mm inside | crossing ports / pairs | far ports | off-feed ports | worst unshared ns | RAW TT/FF | FOLD TT/FF | PAD TT/FF (unsh. ns, max pad) | FOLD <100 TT/FF | PAD <100 TT/FF | track ratio worst (>1) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| feed36 | fwd | 36 | 13.67 | 2.81 | 73.8 % | 78 / 70 | 0 | 0 | 5.88 | -3044 / -2530 | -545 / -31 | 4 / -337 (6.15, 566) | 42 / 16 | 4 / 32 | 0.279 (0) |

Readings: RAW = today's ring with unfolded nominal d; FOLD = count-aligned crossing (d - kP, one k for TT and FF); PAD = forwarded hops padded to whole cycles at TT (pad = clock delay, charged as unshared). The gate stays 12.13d (measured landed_phase_ocv >= 100 ps TT and FF on every crossing after GRT).

Worst crossings, feed36 (fwd, PAD): F01->F12 565 b, unshared 6.15 ns, d -3332, p 412/338, margin 4/-337; F04->F12 565 b, unshared 6.15 ns, d -3332, p 412/338, margin 4/-337; F12->F03 565 b, unshared 4.98 ns, d 3332, p 331/270, margin 86/-268; F12->F10 565 b, unshared 4.98 ns, d 3332, p 331/270, margin 86/-268; F09->F12 565 b, unshared 4.40 ns, d -3332, p 289/234, margin 128/-233
  Tracks: worst boundaries F19|F29 2052 b over 1226.9 um face = 0.279x supply; F12|F19 2052 b over 1226.9 um face = 0.279x supply; F10|F12 2260 b over 2073.6 um face = 0.182x supply; crossing bits by region hops {1: 32475, 2: 1130}

Verdict rule (12.14b): build a map/feed only if its estimated PAD or FOLD margin is >= 100 ps TT and FF on every crossing and its track ratio is <= 1; otherwise fix the map (smaller span, cut along low-traffic seams) first. Every number on this page is an ESTIMATE (UNCHECKED) until a GRT + landed_phase_ocv run.
