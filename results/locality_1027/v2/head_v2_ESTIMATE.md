# 12.14b ESTIMATE v2: head region map / clock feed / crossings (LOCALITY-SCORE-2, analytic, UNCHECKED)

Inputs: plan physical/die_plan/s81_head/die_plan.json (sha256 7af819954806), 326 partitions, 427 ports; v = 340 ps/mm TT; P = 833 ps, budget P/2 = 416.5 ps.
Feeds: fwd = neighbour-forwarded from a parent LEAF (H-tree regions); spine = one spine along the max-bit spanning tree of the region adjacency (through every region centre; H-tree region trees hang off it); fish = the same spine + fishbone region trees (long-axis spine + ribs, leaf delay = Manhattan distance); dme = the spine made zero-skew (DME pads at the spine nodes: nominal d = 0, unshared = height of the last common spine node; LAND-HEAD-3's balanced spine form); top = one balanced die H-tree. Maps: given, v1 = connectivity greedy (span cap), tree_sXcY = proposer v2 (start span X mm, crossing graph made a tree by merge/re-cut up to cap Y mm).
Modes: CURRENT RING = landed_phase_ocv margin with the nominal d (phase-dependent); COUNT-ALIGNED = budget - max(p_up, p_dn), nominal d absorbed by the ring count (ASSUMED definition = LAND-HEAD-3's reading, pending the MESO-COUNT-1 window verdict; it re-centres d per corner, i.e. it ASSUMES the ring count is trained at reset at the operating PVT); STATIC COUNT = one whole-cycle k per crossing for TT and FF (= FOLD: the corner-to-corner shift of d stays in the window). Derate: clk_aocv g021 + droop regions + core latency class B (shared model).

Calibration: derate CHECKED: the 427 measured LAND-HEAD-3 spine_fishbone branches (unshared a/b, distance) through margins(): p model - measured mean -1.3 / min -8.4 ps TT, -1.2 / -8.6 FF; count-aligned worst model +198.2 / +236.2 vs measured +189.8 / +227.6 (model <= 8.6 ps optimistic; calib_derate.py). Geometry UNCHECKED: measured rib hops d 250-290 ps per ~708 um (353-410 ps/mm) vs v -> spine delay up to ~15 % optimistic, so VSCALE=1.15 is run as the pessimistic reading (v2_vs115 table in LOCALITY.md). HEAD partition map: the spine model gives on-feed U <= 1.12 ns (CA +317 / +337) but the 12 channel-loop off-feed ports at 6.1 ns (CA +47 / +119); the built feed closed those loops at one column node (U 2.43 ns, +190 / +228), which is what the tree proposer (merge the loop) and the hop reading (re-time the loop) model.

Hop modes (12.13c): every off-feed crossing (loop-closing or far) is re-timed as a hop chain along the feed-tree path, one fixed-latency landing per tree edge; only feed parent<->child crossings remain. Cost = extra landing cycles (bit-hops), reported per map.

| mode | best map | feed | worst TT / FF ps | <100 TT / FF | >=100 TT and FF |
|---|---|---|---|---|---|
| ring | v1_s3.5 | top | -48 / 28 | 30 / 8 | no |
| ca | v1_s3.5 | fish | 140 / 190 | 0 / 0 | YES |
| ring+hop | v1_s3.5 | dme | -94 / -12 | 96 / 56 | no |
| ca+hop | v1_s3.5 | fish | 309 / 331 | 0 / 0 | YES |
| static | v1_s3.5 | top | -48 / 28 | 30 / 8 | no |
| static+hop | landpart | fish | 12 / -34 | 61 / 61 | no |

| map | feed | regions | max span mm | bit-mm inside | crossing ports | off-feed (loop) ports / pairs | worst unshared ns (on / off feed) | max tree hops | CURRENT RING TT/FF (<100) | COUNT-ALIGNED TT/FF (<100) | hop chains: n / max hops / extra bit-hops | RING+HOP TT/FF (<100) | CA+HOP TT/FF (<100) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| landpart | fwd | 326 | 2.89 | 0.0 % | 427 | 12 / 12 | 1.61 / 10.38 | 24 | -9961 / -8434 (415/415) | -167 / -55 (12/12) | 12 / 24 / 155940 | -867 / -675 (403/403) | 286 / 312 (0/0) |
| landpart | spine | 326 | 2.89 | 0.0 % | 427 | 12 / 12 | 1.36 / 6.30 | 24 | -5678 / -4778 (163/151) | 33 / 107 (12/0) | 12 / 24 / 155940 | -609 / -455 (151/139) | 298 / 321 (0/0) |
| landpart | fish | 326 | 2.89 | 0.0 % | 427 | 12 / 12 | 1.12 / 6.12 | 24 | -5664 / -4767 (151/151) | 47 / 119 (12/0) | 12 / 24 / 155940 | -591 / -440 (139/139) | 317 / 337 (0/0) |
| landpart | dme | 326 | 2.89 | 0.0 % | 427 | 12 / 12 | 8.41 / 8.41 | 24 | -256 / -142 (174/126) | -256 / -142 (174/126) | 12 / 24 / 155940 | -187 / -92 (162/114) | -187 / -92 (162/114) |
| landpart | top | 326 | 2.89 | 0.0 % | 427 | 427 / 374 | 0.00 / 6.35 | 2 | -60 / 17 (33/33) | -60 / 17 (33/33) | - | - | - |
| v1_s3.5 | fwd | 85 | 3.01 | 57.1 % | 162 | 12 / 12 | 1.94 / 4.18 | 5 | -1459 / -1176 (162/162) | 92 / 150 (12/0) | 12 / 5 / 27120 | -1335 / -1075 (150/150) | 272 / 300 (0/0) |
| v1_s3.5 | spine | 85 | 3.01 | 57.1 % | 162 | 12 / 12 | 2.31 / 3.65 | 5 | -1249 / -997 (162/162) | 126 / 179 (0/0) | 12 / 5 / 27120 | -1159 / -924 (150/150) | 239 / 273 (0/0) |
| v1_s3.5 | fish | 85 | 3.01 | 57.1 % | 162 | 12 / 12 | 1.40 / 3.47 | 5 | -1235 / -986 (162/162) | 140 / 190 (0/0) | 12 / 5 / 27120 | -1089 / -865 (150/150) | 309 / 331 (0/0) |
| v1_s3.5 | dme | 85 | 3.01 | 57.1 % | 162 | 12 / 12 | 6.90 / 6.90 | 5 | -136 / -43 (108/68) | -136 / -43 (108/68) | 12 / 5 / 27120 | -94 / -12 (96/56) | -94 / -12 (96/56) |
| v1_s3.5 | top | 85 | 3.01 | 57.1 % | 162 | 162 / 120 | 0.00 / 6.10 | 2 | -48 / 28 (30/8) | -48 / 28 (30/8) | - | - | - |
| tree_s2c3.5 | fwd | 182 | 2.89 | 26.2 % | 283 | 12 / 12 | 1.61 / 8.27 | 12 | -7739 / -6538 (283/283) | -60 / 31 (12/12) | 12 / 12 / 74580 | -867 / -675 (271/271) | 286 / 312 (0/0) |
| tree_s2c3.5 | spine | 182 | 2.89 | 26.2 % | 283 | 12 / 12 | 1.36 / 6.30 | 12 | -5675 / -4776 (283/259) | 36 / 109 (12/0) | 12 / 12 / 74580 | -609 / -455 (271/247) | 298 / 321 (0/0) |
| tree_s2c3.5 | fish | 182 | 2.89 | 26.2 % | 283 | 12 / 12 | 1.12 / 6.12 | 12 | -5661 / -4765 (259/259) | 50 / 121 (12/0) | 12 / 12 / 74580 | -591 / -440 (247/247) | 317 / 337 (0/0) |
| tree_s2c3.5 | dme | 182 | 2.89 | 26.2 % | 283 | 12 / 12 | 8.41 / 8.41 | 12 | -249 / -137 (126/102) | -249 / -137 (126/102) | 12 / 12 / 74580 | -187 / -92 (114/90) | -187 / -92 (114/90) |
| tree_s2c3.5 | top | 182 | 2.89 | 26.2 % | 283 | 283 / 230 | 0.00 / 6.11 | 2 | -49 / 27 (47/8) | -49 / 27 (47/8) | - | - | - |
| tree_s3.5c5 | fwd | 85 | 3.01 | 57.1 % | 162 | 12 / 12 | 1.94 / 4.18 | 5 | -1459 / -1176 (162/162) | 92 / 150 (12/0) | 12 / 5 / 27120 | -1335 / -1075 (150/150) | 272 / 300 (0/0) |
| tree_s3.5c5 | spine | 85 | 3.01 | 57.1 % | 162 | 12 / 12 | 2.31 / 3.65 | 5 | -1249 / -997 (162/162) | 126 / 179 (0/0) | 12 / 5 / 27120 | -1159 / -924 (150/150) | 239 / 273 (0/0) |
| tree_s3.5c5 | fish | 85 | 3.01 | 57.1 % | 162 | 12 / 12 | 1.40 / 3.47 | 5 | -1235 / -986 (162/162) | 140 / 190 (0/0) | 12 / 5 / 27120 | -1089 / -865 (150/150) | 309 / 331 (0/0) |
| tree_s3.5c5 | dme | 85 | 3.01 | 57.1 % | 162 | 12 / 12 | 6.90 / 6.90 | 5 | -136 / -43 (108/68) | -136 / -43 (108/68) | 12 / 5 / 27120 | -94 / -12 (96/56) | -94 / -12 (96/56) |
| tree_s3.5c5 | top | 85 | 3.01 | 57.1 % | 162 | 162 / 120 | 0.00 / 6.10 | 2 | -48 / 28 (30/8) | -48 / 28 (30/8) | - | - | - |
| tree_s1.5c3 | fwd | 206 | 2.89 | 23.3 % | 307 | 12 / 12 | 1.61 / 8.62 | 14 | -8113 / -6856 (295/295) | -81 / 14 (12/12) | 12 / 14 / 88140 | -867 / -675 (283/283) | 286 / 312 (0/0) |
| tree_s1.5c3 | spine | 206 | 2.89 | 23.3 % | 307 | 12 / 12 | 1.36 / 6.30 | 14 | -5678 / -4778 (295/271) | 33 / 107 (12/0) | 12 / 14 / 88140 | -609 / -455 (283/259) | 298 / 321 (0/0) |
| tree_s1.5c3 | fish | 206 | 2.89 | 23.3 % | 307 | 12 / 12 | 1.12 / 6.12 | 14 | -5664 / -4767 (271/271) | 47 / 119 (12/0) | 12 / 14 / 88140 | -591 / -440 (259/259) | 317 / 337 (0/0) |
| tree_s1.5c3 | dme | 206 | 2.89 | 23.3 % | 307 | 12 / 12 | 8.41 / 8.41 | 14 | -256 / -142 (126/102) | -256 / -142 (126/102) | 12 / 14 / 88140 | -187 / -92 (114/90) | -187 / -92 (114/90) |
| tree_s1.5c3 | top | 206 | 2.89 | 23.3 % | 307 | 307 / 254 | 0.00 / 6.35 | 2 | -60 / 17 (33/33) | -60 / 17 (33/33) | - | - | - |

Worst crossings, best ring (v1_s3.5 / top, current ring: phase-dependent, the nominal d counts): R045->R034 565 b OFF-feed hops 2, unshared 6.10 ns, d -0, p 464/388, margin -48/28; R034->R045 565 b OFF-feed hops 2, unshared 6.10 ns, d 0, p 464/388, margin -48/28; R045->R034 277 b OFF-feed hops 2, unshared 6.10 ns, d -0, p 464/388, margin -48/28; R034->R045 276 b OFF-feed hops 2, unshared 6.10 ns, d 0, p 464/388, margin -48/28; R045->R034 64 b OFF-feed hops 2, unshared 6.10 ns, d -0, p 464/388, margin -48/28
  Render: head_v2_best_ring.png
Worst crossings, best ca (v1_s3.5 / fish, count-aligned: nominal d absorbed by the ring count, only the derated variation counts): R074->R070 565 b OFF-feed hops 5, unshared 3.47 ns, d 1375, p 277/226, margin 140/190; R071->R064 565 b OFF-feed hops 5, unshared 3.47 ns, d 1375, p 277/226, margin 140/190; R063->R059 565 b OFF-feed hops 5, unshared 3.47 ns, d 1375, p 277/226, margin 140/190; R060->R053 565 b OFF-feed hops 5, unshared 3.47 ns, d 1375, p 277/226, margin 140/190; R048->R047 565 b OFF-feed hops 5, unshared 3.47 ns, d -1375, p 277/226, margin 140/190
  Render: head_v2_best_ca.png
Worst crossings, best ring+hop (v1_s3.5 / dme, current ring, off-feed crossings re-timed as hop chains along the feed tree (12.13c)): R034->R040 565 b on-feed hops 1, unshared 6.90 ns, d 0, p 511/429, margin -94/-12; R035->R034 565 b on-feed hops 1, unshared 6.90 ns, d 0, p 511/429, margin -94/-12; R034->R039 565 b on-feed hops 1, unshared 6.90 ns, d 0, p 511/429, margin -94/-12; R033->R034 565 b on-feed hops 1, unshared 6.90 ns, d 0, p 511/429, margin -94/-12; R045->R034 565 b on-feed hops 1, unshared 6.90 ns, d 0, p 508/426, margin -91/-10
  Hop cost: 12 off-feed crossings become chains, max 5 tree hops, 27120 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: head_v2_best_ring+hop.png
Worst crossings, best ca+hop (v1_s3.5 / fish, count-aligned, off-feed crossings re-timed as hop chains along the feed tree (12.13c)): R006->R001 64 b on-feed hops 1, unshared 1.40 ns, d 1398, p 108/86, margin 309/331; R001->R006 64 b on-feed hops 1, unshared 1.40 ns, d -1398, p 108/86, margin 309/331; R008->R004 64 b on-feed hops 1, unshared 1.40 ns, d 1398, p 108/86, margin 309/331; R004->R008 64 b on-feed hops 1, unshared 1.40 ns, d -1398, p 108/86, margin 309/331; R079->R080 64 b on-feed hops 1, unshared 1.40 ns, d 1398, p 108/86, margin 309/331
  Hop cost: 12 off-feed crossings become chains, max 5 tree hops, 27120 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: head_v2_best_ca+hop.png
Worst crossings, best static (v1_s3.5 / top, static count: one whole-cycle k per crossing for TT and FF (no reset-time training)): R045->R034 565 b OFF-feed hops 2, unshared 6.10 ns, d -0, p 464/388, margin -48/28; R034->R045 565 b OFF-feed hops 2, unshared 6.10 ns, d 0, p 464/388, margin -48/28; R045->R034 277 b OFF-feed hops 2, unshared 6.10 ns, d -0, p 464/388, margin -48/28; R034->R045 276 b OFF-feed hops 2, unshared 6.10 ns, d 0, p 464/388, margin -48/28; R045->R034 64 b OFF-feed hops 2, unshared 6.10 ns, d -0, p 464/388, margin -48/28
  Render: head_v2_best_static.png
Worst crossings, best static+hop (landpart / fish, static count + hop chains): host->sst5 64 b on-feed hops 1, unshared 0.49 ns, d 491, p 60/47, margin 27/-34; sst5->sst4 64 b on-feed hops 1, unshared 0.49 ns, d 491, p 60/47, margin 27/-34; sst4->mesh0S 64 b on-feed hops 1, unshared 0.49 ns, d 491, p 60/47, margin 27/-34; mesh0S->sst4 64 b on-feed hops 1, unshared 0.49 ns, d -491, p 60/47, margin 27/-34; sst4->sst5 64 b on-feed hops 1, unshared 0.49 ns, d -491, p 60/47, margin 27/-34
  Hop cost: 12 off-feed crossings become chains, max 24 tree hops, 155940 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: head_v2_best_static+hop.png

Tree proposer log (start -> end: loop-closing bits, loop pairs, regions): tree_s2c3.5: 6780 b/12 p/182 r -> 6780 b/12 p/182 r; tree_s3.5c5: 6780 b/12 p/85 r -> 6780 b/12 p/85 r; tree_s1.5c3: 6780 b/12 p/206 r -> 6780 b/12 p/206 r

Verdict rule (12.14b): build only a map/feed whose estimated margin is >= 100 ps TT and FF on every crossing in the ring mode that will be built. Every number here is an ESTIMATE (UNCHECKED) until a GRT + landed_phase_ocv run.
