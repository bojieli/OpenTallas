# 12.14b ESTIMATE v2: head region map / clock feed / crossings (LOCALITY-SCORE-2, analytic, UNCHECKED)

Inputs: plan physical/die_plan/s81_head/die_plan.json (sha256 7af819954806), 326 partitions, 427 ports; v = 391 ps/mm TT; P = 833 ps, budget P/2 = 416.5 ps.
Feeds: fwd = neighbour-forwarded from a parent LEAF (H-tree regions); spine = one spine along the max-bit spanning tree of the region adjacency (through every region centre; H-tree region trees hang off it); fish = the same spine + fishbone region trees (long-axis spine + ribs, leaf delay = Manhattan distance); dme = the spine made zero-skew (DME pads at the spine nodes: nominal d = 0, unshared = height of the last common spine node; LAND-HEAD-3's balanced spine form); top = one balanced die H-tree. Maps: given, v1 = connectivity greedy (span cap), tree_sXcY = proposer v2 (start span X mm, crossing graph made a tree by merge/re-cut up to cap Y mm).
Modes: CURRENT RING = landed_phase_ocv margin with the nominal d (phase-dependent); COUNT-ALIGNED = budget - max(p_up, p_dn), nominal d absorbed by the ring count (ASSUMED definition = LAND-HEAD-3's reading, pending the MESO-COUNT-1 window verdict; it re-centres d per corner, i.e. it ASSUMES the ring count is trained at reset at the operating PVT); STATIC COUNT = one whole-cycle k per crossing for TT and FF (= FOLD: the corner-to-corner shift of d stays in the window). Derate: clk_aocv g021 + droop regions + core latency class B (shared model).

Calibration: derate CHECKED: the 427 measured LAND-HEAD-3 spine_fishbone branches (unshared a/b, distance) through margins(): p model - measured mean -1.3 / min -8.4 ps TT, -1.2 / -8.6 FF; count-aligned worst model +198.2 / +236.2 vs measured +189.8 / +227.6 (model <= 8.6 ps optimistic; calib_derate.py). Geometry UNCHECKED: measured rib hops d 250-290 ps per ~708 um (353-410 ps/mm) vs v -> spine delay up to ~15 % optimistic, so VSCALE=1.15 is run as the pessimistic reading (v2_vs115 table in LOCALITY.md). HEAD partition map: the spine model gives on-feed U <= 1.12 ns (CA +317 / +337) but the 12 channel-loop off-feed ports at 6.1 ns (CA +47 / +119); the built feed closed those loops at one column node (U 2.43 ns, +190 / +228), which is what the tree proposer (merge the loop) and the hop reading (re-time the loop) model.

Hop modes (12.13c): every off-feed crossing (loop-closing or far) is re-timed as a hop chain along the feed-tree path, one fixed-latency landing per tree edge; only feed parent<->child crossings remain. Cost = extra landing cycles (bit-hops), reported per map.

| mode | best map | feed | worst TT / FF ps | <100 TT / FF | >=100 TT and FF |
|---|---|---|---|---|---|
| ring | v1_s3.5 | top | -108 / -23 | 46 / 30 | no |
| ca | v1_s3.5 | fish | 106 / 162 | 0 / 0 | YES |
| ring+hop | v1_s3.5 | dme | -161 / -68 | 96 / 78 | no |
| ca+hop | v1_s3.5 | fish | 299 / 322 | 0 / 0 | YES |
| static | v1_s3.5 | top | -108 / -23 | 46 / 30 | no |
| static+hop | v1_s3.5 | fish | 27 / 27 | 36 / 34 | no |

| map | feed | regions | max span mm | bit-mm inside | crossing ports | off-feed (loop) ports / pairs | worst unshared ns (on / off feed) | max tree hops | CURRENT RING TT/FF (<100) | COUNT-ALIGNED TT/FF (<100) | hop chains: n / max hops / extra bit-hops | RING+HOP TT/FF (<100) | CA+HOP TT/FF (<100) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| landpart | fwd | 326 | 2.89 | 0.0 % | 427 | 12 / 12 | 1.85 / 11.94 | 24 | -11509 / -9754 (427/415) | -246 / -119 (12/12) | 12 / 24 / 155940 | -1054 / -834 (415/403) | 272 / 300 (0/0) |
| landpart | spine | 326 | 2.89 | 0.0 % | 427 | 12 / 12 | 1.57 / 7.24 | 24 | -6584 / -5551 (415/163) | -16 / 67 (12/12) | 12 / 24 / 155940 | -758 / -582 (403/151) | 286 / 311 (0/0) |
| landpart | fish | 326 | 2.89 | 0.0 % | 427 | 12 / 12 | 1.28 / 7.04 | 24 | -6568 / -5538 (415/151) | -0 / 80 (12/12) | 12 / 24 / 155940 | -736 / -564 (403/139) | 307 / 329 (0/0) |
| landpart | dme | 326 | 2.89 | 0.0 % | 427 | 12 / 12 | 9.68 / 9.68 | 24 | -344 / -217 (219/162) | -344 / -217 (219/162) | 12 / 24 / 155940 | -266 / -159 (207/150) | -266 / -159 (207/150) |
| landpart | top | 326 | 2.89 | 0.0 % | 427 | 427 / 374 | 0.00 / 7.31 | 2 | -121 / -35 (73/33) | -121 / -35 (73/33) | - | - | - |
| v1_s3.5 | fwd | 85 | 3.01 | 57.1 % | 162 | 12 / 12 | 2.23 / 4.80 | 5 | -1732 / -1409 (162/162) | 52 / 117 (12/0) | 12 / 5 / 27120 | -1591 / -1293 (150/150) | 256 / 288 (0/0) |
| v1_s3.5 | spine | 85 | 3.01 | 57.1 % | 162 | 12 / 12 | 2.65 / 4.20 | 5 | -1490 / -1203 (162/162) | 91 / 150 (12/0) | 12 / 5 / 27120 | -1389 / -1120 (150/150) | 219 / 256 (0/0) |
| v1_s3.5 | fish | 85 | 3.01 | 57.1 % | 162 | 12 / 12 | 1.61 / 3.99 | 5 | -1475 / -1190 (162/162) | 106 / 162 (0/0) | 12 / 5 / 27120 | -1309 / -1053 (150/150) | 299 / 322 (0/0) |
| v1_s3.5 | dme | 85 | 3.01 | 57.1 % | 162 | 12 / 12 | 7.93 / 7.93 | 5 | -209 / -104 (108/90) | -208 / -104 (108/90) | 12 / 5 / 27120 | -161 / -68 (96/78) | -161 / -68 (96/78) |
| v1_s3.5 | top | 85 | 3.01 | 57.1 % | 162 | 162 / 120 | 0.00 / 7.02 | 2 | -108 / -23 (46/30) | -108 / -23 (46/30) | - | - | - |
| tree_s2c3.5 | fwd | 182 | 2.89 | 26.2 % | 283 | 12 / 12 | 1.85 / 9.51 | 12 | -8954 / -7574 (283/283) | -123 / -20 (12/12) | 12 / 12 / 74580 | -1054 / -834 (271/271) | 272 / 300 (0/0) |
| tree_s2c3.5 | spine | 182 | 2.89 | 26.2 % | 283 | 12 / 12 | 1.57 / 7.24 | 12 | -6580 / -5549 (283/259) | -13 / 70 (12/12) | 12 / 12 / 74580 | -758 / -582 (271/247) | 286 / 311 (0/0) |
| tree_s2c3.5 | fish | 182 | 2.89 | 26.2 % | 283 | 12 / 12 | 1.28 / 7.04 | 12 | -6564 / -5535 (283/259) | 3 / 83 (12/12) | 12 / 12 / 74580 | -736 / -564 (271/247) | 307 / 329 (0/0) |
| tree_s2c3.5 | dme | 182 | 2.89 | 26.2 % | 283 | 12 / 12 | 9.68 / 9.68 | 12 | -337 / -211 (171/114) | -336 / -211 (171/114) | 12 / 12 / 74580 | -266 / -159 (159/102) | -266 / -159 (159/102) |
| tree_s2c3.5 | top | 182 | 2.89 | 26.2 % | 283 | 283 / 230 | 0.00 / 7.03 | 2 | -108 / -23 (63/47) | -108 / -24 (63/47) | - | - | - |
| tree_s3.5c5 | fwd | 85 | 3.01 | 57.1 % | 162 | 12 / 12 | 2.23 / 4.80 | 5 | -1732 / -1409 (162/162) | 52 / 117 (12/0) | 12 / 5 / 27120 | -1591 / -1293 (150/150) | 256 / 288 (0/0) |
| tree_s3.5c5 | spine | 85 | 3.01 | 57.1 % | 162 | 12 / 12 | 2.65 / 4.20 | 5 | -1490 / -1203 (162/162) | 91 / 150 (12/0) | 12 / 5 / 27120 | -1389 / -1120 (150/150) | 219 / 256 (0/0) |
| tree_s3.5c5 | fish | 85 | 3.01 | 57.1 % | 162 | 12 / 12 | 1.61 / 3.99 | 5 | -1475 / -1190 (162/162) | 106 / 162 (0/0) | 12 / 5 / 27120 | -1309 / -1053 (150/150) | 299 / 322 (0/0) |
| tree_s3.5c5 | dme | 85 | 3.01 | 57.1 % | 162 | 12 / 12 | 7.93 / 7.93 | 5 | -209 / -104 (108/90) | -208 / -104 (108/90) | 12 / 5 / 27120 | -161 / -68 (96/78) | -161 / -68 (96/78) |
| tree_s3.5c5 | top | 85 | 3.01 | 57.1 % | 162 | 162 / 120 | 0.00 / 7.02 | 2 | -108 / -23 (46/30) | -108 / -23 (46/30) | - | - | - |
| tree_s1.5c3 | fwd | 206 | 2.89 | 23.3 % | 307 | 12 / 12 | 1.85 / 9.91 | 14 | -9383 / -7940 (307/295) | -147 / -39 (12/12) | 12 / 14 / 88140 | -1054 / -834 (295/283) | 272 / 300 (0/0) |
| tree_s1.5c3 | spine | 206 | 2.89 | 23.3 % | 307 | 12 / 12 | 1.57 / 7.24 | 14 | -6584 / -5551 (295/271) | -16 / 67 (12/12) | 12 / 14 / 88140 | -758 / -582 (283/259) | 286 / 311 (0/0) |
| tree_s1.5c3 | fish | 206 | 2.89 | 23.3 % | 307 | 12 / 12 | 1.28 / 7.04 | 14 | -6568 / -5538 (295/271) | -0 / 80 (12/12) | 12 / 14 / 88140 | -736 / -564 (283/259) | 307 / 329 (0/0) |
| tree_s1.5c3 | dme | 206 | 2.89 | 23.3 % | 307 | 12 / 12 | 9.68 / 9.68 | 14 | -344 / -217 (159/114) | -344 / -217 (159/114) | 12 / 14 / 88140 | -266 / -159 (147/102) | -266 / -159 (147/102) |
| tree_s1.5c3 | top | 206 | 2.89 | 23.3 % | 307 | 307 / 254 | 0.00 / 7.31 | 2 | -121 / -35 (73/33) | -121 / -35 (73/33) | - | - | - |

Worst crossings, best ring (v1_s3.5 / top, current ring: phase-dependent, the nominal d counts): R045->R034 565 b OFF-feed hops 2, unshared 7.02 ns, d 0, p 524/439, margin -108/-23; R034->R045 565 b OFF-feed hops 2, unshared 7.02 ns, d -0, p 524/439, margin -108/-23; R045->R034 277 b OFF-feed hops 2, unshared 7.02 ns, d 0, p 524/439, margin -108/-23; R034->R045 276 b OFF-feed hops 2, unshared 7.02 ns, d -0, p 524/439, margin -108/-23; R045->R034 64 b OFF-feed hops 2, unshared 7.02 ns, d 0, p 524/439, margin -108/-23
  Render: head_v2_best_ring.png
Worst crossings, best ca (v1_s3.5 / fish, count-aligned: nominal d absorbed by the ring count, only the derated variation counts): R074->R070 565 b OFF-feed hops 5, unshared 3.99 ns, d 1581, p 311/254, margin 106/162; R071->R064 565 b OFF-feed hops 5, unshared 3.99 ns, d 1581, p 311/254, margin 106/162; R063->R059 565 b OFF-feed hops 5, unshared 3.99 ns, d 1581, p 311/254, margin 106/162; R060->R053 565 b OFF-feed hops 5, unshared 3.99 ns, d 1581, p 311/254, margin 106/162; R048->R047 565 b OFF-feed hops 5, unshared 3.99 ns, d -1581, p 311/254, margin 106/162
  Render: head_v2_best_ca.png
Worst crossings, best ring+hop (v1_s3.5 / dme, current ring, off-feed crossings re-timed as hop chains along the feed tree (12.13c)): R045->R051 565 b on-feed hops 1, unshared 7.93 ns, d 0, p 577/485, margin -161/-68; R046->R045 565 b on-feed hops 1, unshared 7.93 ns, d 0, p 577/485, margin -161/-68; R045->R050 565 b on-feed hops 1, unshared 7.93 ns, d 0, p 577/485, margin -161/-68; R044->R045 565 b on-feed hops 1, unshared 7.93 ns, d 0, p 577/485, margin -161/-68; R056->R045 565 b on-feed hops 1, unshared 7.93 ns, d 0, p 574/482, margin -157/-66
  Hop cost: 12 off-feed crossings become chains, max 5 tree hops, 27120 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: head_v2_best_ring+hop.png
Worst crossings, best ca+hop (v1_s3.5 / fish, count-aligned, off-feed crossings re-timed as hop chains along the feed tree (12.13c)): R006->R001 64 b on-feed hops 1, unshared 1.61 ns, d 1608, p 118/94, margin 299/322; R001->R006 64 b on-feed hops 1, unshared 1.61 ns, d -1608, p 118/94, margin 299/322; R008->R004 64 b on-feed hops 1, unshared 1.61 ns, d 1608, p 118/94, margin 299/322; R004->R008 64 b on-feed hops 1, unshared 1.61 ns, d -1608, p 118/94, margin 299/322; R079->R080 64 b on-feed hops 1, unshared 1.61 ns, d 1608, p 118/94, margin 299/322
  Hop cost: 12 off-feed crossings become chains, max 5 tree hops, 27120 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: head_v2_best_ca+hop.png
Worst crossings, best static (v1_s3.5 / top, static count: one whole-cycle k per crossing for TT and FF (no reset-time training)): R045->R034 565 b OFF-feed hops 2, unshared 7.02 ns, d 0, p 524/439, margin -108/-23; R034->R045 565 b OFF-feed hops 2, unshared 7.02 ns, d -0, p 524/439, margin -108/-23; R045->R034 277 b OFF-feed hops 2, unshared 7.02 ns, d 0, p 524/439, margin -108/-23; R034->R045 276 b OFF-feed hops 2, unshared 7.02 ns, d -0, p 524/439, margin -108/-23; R045->R034 64 b OFF-feed hops 2, unshared 7.02 ns, d 0, p 524/439, margin -108/-23
  Render: head_v2_best_static.png
Worst crossings, best static+hop (v1_s3.5 / fish, static count + hop chains): R007->R006 64 b on-feed hops 1, unshared 0.56 ns, d 564, p 64/50, margin 99/27; R006->R007 64 b on-feed hops 1, unshared 0.56 ns, d -564, p 64/50, margin 99/27; R007->R008 64 b on-feed hops 1, unshared 0.56 ns, d 564, p 64/50, margin 99/27; R008->R007 64 b on-feed hops 1, unshared 0.56 ns, d -564, p 64/50, margin 99/27; R078->R079 64 b on-feed hops 1, unshared 0.56 ns, d 564, p 64/50, margin 99/27
  Hop cost: 12 off-feed crossings become chains, max 5 tree hops, 27120 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: head_v2_best_static+hop.png

Tree proposer log (start -> end: loop-closing bits, loop pairs, regions): tree_s2c3.5: 6780 b/12 p/182 r -> 6780 b/12 p/182 r; tree_s3.5c5: 6780 b/12 p/85 r -> 6780 b/12 p/85 r; tree_s1.5c3: 6780 b/12 p/206 r -> 6780 b/12 p/206 r

Verdict rule (12.14b): build only a map/feed whose estimated margin is >= 100 ps TT and FF on every crossing in the ring mode that will be built. Every number here is an ESTIMATE (UNCHECKED) until a GRT + landed_phase_ocv run.
