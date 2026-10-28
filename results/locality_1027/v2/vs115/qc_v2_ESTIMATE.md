# 12.14b ESTIMATE v2: qc region map / clock feed / crossings (LOCALITY-SCORE-2, analytic, UNCHECKED)

Inputs: plan physical/die_plan/qwen_compute/die_plan.json (sha256 54a1aeb5065d), 377 partitions, 3005 ports; v = 228.8 ps/mm TT; P = 833 ps, budget P/2 = 416.5 ps.
Feeds: fwd = neighbour-forwarded from a parent LEAF (H-tree regions); spine = one spine along the max-bit spanning tree of the region adjacency (through every region centre; H-tree region trees hang off it); fish = the same spine + fishbone region trees (long-axis spine + ribs, leaf delay = Manhattan distance); dme = the spine made zero-skew (DME pads at the spine nodes: nominal d = 0, unshared = height of the last common spine node; LAND-HEAD-3's balanced spine form); top = one balanced die H-tree. Maps: given, v1 = connectivity greedy (span cap), tree_sXcY = proposer v2 (start span X mm, crossing graph made a tree by merge/re-cut up to cap Y mm).
Modes: CURRENT RING = landed_phase_ocv margin with the nominal d (phase-dependent); COUNT-ALIGNED = budget - max(p_up, p_dn), nominal d absorbed by the ring count (ASSUMED definition = LAND-HEAD-3's reading, pending the MESO-COUNT-1 window verdict; it re-centres d per corner, i.e. it ASSUMES the ring count is trained at reset at the operating PVT); STATIC COUNT = one whole-cycle k per crossing for TT and FF (= FOLD: the corner-to-corner shift of d stays in the window). Derate: clk_aocv g021 + droop regions + core latency class B (shared model).

Calibration: derate CHECKED: the 427 measured LAND-HEAD-3 spine_fishbone branches (unshared a/b, distance) through margins(): p model - measured mean -1.3 / min -8.4 ps TT, -1.2 / -8.6 FF; count-aligned worst model +198.2 / +236.2 vs measured +189.8 / +227.6 (model <= 8.6 ps optimistic; calib_derate.py). Geometry UNCHECKED: measured rib hops d 250-290 ps per ~708 um (353-410 ps/mm) vs v -> spine delay up to ~15 % optimistic, so VSCALE=1.15 is run as the pessimistic reading (v2_vs115 table in LOCALITY.md). HEAD partition map: the spine model gives on-feed U <= 1.12 ns (CA +317 / +337) but the 12 channel-loop off-feed ports at 6.1 ns (CA +47 / +119); the built feed closed those loops at one column node (U 2.43 ns, +190 / +228), which is what the tree proposer (merge the loop) and the hop reading (re-time the loop) model.

Hop modes (12.13c): every off-feed crossing (loop-closing or far) is re-timed as a hop chain along the feed-tree path, one fixed-latency landing per tree edge; only feed parent<->child crossings remain. Cost = extra landing cycles (bit-hops), reported per map.

| mode | best map | feed | worst TT / FF ps | <100 TT / FF | >=100 TT and FF |
|---|---|---|---|---|---|
| ring | tree_s1.5c3 | top | -97 / -14 | 290 / 290 | no |
| ca | slices | fish | 248 / 279 | 0 / 0 | YES |
| ring+hop | slices | dme | -198 / -100 | 237 / 193 | no |
| ca+hop | slices | fish | 248 / 279 | 0 / 0 | YES |
| static | tree_s1.5c3 | top | -98 / -14 | 290 / 290 | no |
| static+hop | tree_s3.5c5 | fish | -25 / 45 | 419 / 785 | no |

| map | feed | regions | max span mm | bit-mm inside | crossing ports | off-feed (loop) ports / pairs | worst unshared ns (on / off feed) | max tree hops | CURRENT RING TT/FF (<100) | COUNT-ALIGNED TT/FF (<100) | hop chains: n / max hops / extra bit-hops | RING+HOP TT/FF (<100) | CA+HOP TT/FF (<100) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| slices | fwd | 13 | 26.27 | 97.7 % | 264 | 0 / 0 | 4.19 / 0.00 | 1 | -3903 / -3267 (264/264) | 111 / 167 (0/0) | 0 / 0 / 0 | -3903 / -3267 (264/264) | 111 / 167 (0/0) |
| slices | spine | 13 | 26.27 | 97.7 % | 264 | 0 / 0 | 4.52 / 0.00 | 1 | -1149 / -913 (264/264) | 81 / 139 (22/0) | 0 / 0 / 0 | -1149 / -913 (264/264) | 81 / 139 (22/0) |
| slices | fish | 13 | 26.27 | 97.7 % | 264 | 0 / 0 | 1.76 / 0.00 | 1 | -1369 / -1103 (264/264) | 248 / 279 (0/0) | 0 / 0 / 0 | -1369 / -1103 (264/264) | 248 / 279 (0/0) |
| slices | dme | 13 | 26.27 | 97.7 % | 264 | 0 / 0 | 8.52 / 0.00 | 1 | -198 / -100 (237/193) | -198 / -100 (237/193) | 0 / 0 / 0 | -198 / -100 (237/193) | -198 / -100 (237/193) |
| slices | top | 13 | 26.27 | 97.7 % | 264 | 264 / 24 | 0.00 / 7.24 | 2 | -126 / -38 (264/87) | -126 / -38 (264/87) | - | - | - |
| v1_s3.5 | fwd | 142 | 3.28 | 34.1 % | 1418 | 21 / 11 | 1.39 / 4.61 | 10 | -775 / -597 (1413/1404) | 5 / 79 (3/2) | 21 / 10 / 27296 | -775 / -597 (1397/1388) | 296 / 320 (0/0) |
| v1_s3.5 | spine | 142 | 3.28 | 34.1 % | 1418 | 21 / 11 | 1.57 / 4.20 | 10 | -907 / -705 (1404/1404) | 49 / 116 (2/0) | 21 / 10 / 27296 | -704 / -536 (1388/1388) | 282 / 307 (0/0) |
| v1_s3.5 | fish | 142 | 3.28 | 34.1 % | 1418 | 21 / 11 | 1.10 / 3.67 | 10 | -825 / -635 (1399/1246) | 90 / 150 (2/0) | 21 / 10 / 27296 | -625 / -469 (1383/1230) | 312 / 333 (0/0) |
| v1_s3.5 | dme | 142 | 3.28 | 34.1 % | 1418 | 21 / 11 | 8.82 / 4.20 | 10 | -217 / -116 (638/522) | -217 / -116 (638/522) | 21 / 10 / 27296 | -217 / -116 (632/520) | -217 / -116 (632/520) |
| v1_s3.5 | top | 142 | 3.28 | 34.1 % | 1418 | 1418 / 291 | 0.00 / 6.87 | 2 | -102 / -18 (272/272) | -102 / -18 (272/272) | - | - | - |
| tree_s2c3.5 | fwd | 248 | 3.20 | 25.4 % | 1686 | 207 / 131 | 1.43 / 6.16 | 10 | -5750 / -4840 (1604/1532) | 29 / 105 (50/0) | 207 / 10 / 414969 | -868 / -676 (1473/1443) | 297 / 321 (0/0) |
| tree_s2c3.5 | spine | 248 | 3.20 | 25.4 % | 1686 | 207 / 131 | 1.46 / 4.90 | 10 | -4432 / -3715 (1533/1478) | 98 / 158 (2/0) | 207 / 10 / 414969 | -715 / -546 (1419/1415) | 289 / 314 (0/0) |
| tree_s2c3.5 | fish | 248 | 3.20 | 25.4 % | 1686 | 207 / 131 | 1.01 / 4.83 | 10 | -4427 / -3711 (1487/1309) | 103 / 165 (0/0) | 207 / 10 / 414969 | -686 / -521 (1408/1248) | 326 / 344 (0/0) |
| tree_s2c3.5 | dme | 248 | 3.20 | 25.4 % | 1686 | 207 / 131 | 9.39 / 9.39 | 10 | -339 / -210 (719/621) | -339 / -210 (719/621) | 207 / 10 / 414969 | -253 / -147 (593/519) | -253 / -147 (593/519) |
| tree_s2c3.5 | top | 248 | 3.20 | 25.4 % | 1686 | 1686 / 529 | 0.00 / 6.87 | 2 | -104 / -19 (362/362) | -104 / -19 (362/362) | - | - | - |
| tree_s3.5c5 | fwd | 136 | 4.79 | 35.4 % | 1354 | 5 / 2 | 1.64 / 3.78 | 7 | -1020 / -806 (1354/1354) | 85 / 144 (5/0) | 5 / 7 / 7182 | -1020 / -806 (1349/1349) | 283 / 309 (0/0) |
| tree_s3.5c5 | spine | 136 | 4.79 | 35.4 % | 1354 | 5 / 2 | 1.77 / 3.29 | 7 | -905 / -707 (1349/1349) | 121 / 174 (0/0) | 5 / 7 / 7182 | -905 / -707 (1344/1344) | 273 / 301 (0/0) |
| tree_s3.5c5 | fish | 136 | 4.79 | 35.4 % | 1354 | 5 / 2 | 1.18 / 2.95 | 7 | -858 / -668 (1354/1222) | 145 / 194 (0/0) | 5 / 7 / 7182 | -858 / -668 (1349/1217) | 312 / 333 (0/0) |
| tree_s3.5c5 | dme | 136 | 4.79 | 35.4 % | 1354 | 5 / 2 | 9.10 / 3.87 | 7 | -235 / -132 (582/465) | -235 / -132 (582/465) | 5 / 7 / 7182 | -235 / -132 (577/465) | -235 / -132 (577/465) |
| tree_s3.5c5 | top | 136 | 4.79 | 35.4 % | 1354 | 1354 / 272 | 0.00 / 6.85 | 2 | -101 / -17 (263/263) | -101 / -17 (263/263) | - | - | - |
| tree_s1.5c3 | fwd | 274 | 2.68 | 25.5 % | 1759 | 255 / 180 | 1.39 / 6.42 | 11 | -6095 / -5133 (1704/1489) | 24 / 101 (58/0) | 255 / 11 / 478431 | -698 / -531 (1498/1294) | 296 / 320 (0/0) |
| tree_s1.5c3 | spine | 274 | 2.68 | 25.5 % | 1759 | 255 / 180 | 1.46 / 5.04 | 11 | -4653 / -3904 (1500/1333) | 92 / 156 (24/0) | 255 / 11 / 478431 | -583 / -432 (1294/1138) | 289 / 314 (0/0) |
| tree_s1.5c3 | fish | 274 | 2.68 | 25.5 % | 1759 | 255 / 180 | 1.10 / 4.97 | 11 | -4647 / -3899 (1489/1388) | 99 / 161 (12/0) | 255 / 11 / 478431 | -536 / -393 (1294/1215) | 312 / 333 (0/0) |
| tree_s1.5c3 | dme | 274 | 2.68 | 25.5 % | 1759 | 255 / 180 | 10.79 / 10.79 | 11 | -456 / -307 (1097/965) | -456 / -307 (1097/965) | 255 / 11 / 478431 | -341 / -222 (859/763) | -341 / -222 (859/763) |
| tree_s1.5c3 | top | 274 | 2.68 | 25.5 % | 1759 | 1759 / 631 | 0.00 / 6.80 | 2 | -97 / -14 (290/290) | -98 / -14 (290/290) | - | - | - |

Worst crossings, best ring (tree_s1.5c3 / top, current ring: phase-dependent, the nominal d counts): T148->T147 10 b OFF-feed hops 2, unshared 6.80 ns, d 0, p 514/430, margin -97/-14; T148->T147 512 b OFF-feed hops 2, unshared 6.80 ns, d 0, p 514/430, margin -97/-14; T148->T147 1 b OFF-feed hops 2, unshared 6.80 ns, d 0, p 514/430, margin -97/-14; T148->T147 1 b OFF-feed hops 2, unshared 6.80 ns, d 0, p 514/430, margin -97/-14; T148->T147 32 b OFF-feed hops 2, unshared 6.80 ns, d 0, p 514/430, margin -97/-14
  Render: qc_v2_best_ring.png
Worst crossings, best ca (slices / fish, count-aligned: nominal d absorbed by the ring count, only the derated variation counts): HUB->W5 597 b on-feed hops 1, unshared 1.73 ns, d -358, p 169/137, margin 248/279; HUB->W5 1 b on-feed hops 1, unshared 1.73 ns, d -358, p 169/137, margin 248/279; W5->HUB 597 b on-feed hops 1, unshared 1.73 ns, d 358, p 169/137, margin 248/279; W5->HUB 1 b on-feed hops 1, unshared 1.73 ns, d 358, p 169/137, margin 248/279; W5->HUB 1 b on-feed hops 1, unshared 1.73 ns, d 358, p 169/137, margin 248/279
  Render: qc_v2_best_ca.png
Worst crossings, best ring+hop (slices / dme, current ring, off-feed crossings re-timed as hop chains along the feed tree (12.13c)): E0->W0 10 b on-feed hops 1, unshared 8.52 ns, d 0, p 614/516, margin -198/-100; E0->W0 512 b on-feed hops 1, unshared 8.52 ns, d 0, p 614/516, margin -198/-100; E0->W0 1 b on-feed hops 1, unshared 8.52 ns, d 0, p 614/516, margin -198/-100; E0->W0 1 b on-feed hops 1, unshared 8.52 ns, d 0, p 614/516, margin -198/-100; E0->W0 32 b on-feed hops 1, unshared 8.52 ns, d 0, p 614/516, margin -198/-100
  Hop cost: 0 off-feed crossings become chains, max 0 tree hops, 0 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: qc_v2_best_ring+hop.png
Worst crossings, best ca+hop (slices / fish, count-aligned, off-feed crossings re-timed as hop chains along the feed tree (12.13c)): HUB->W5 597 b on-feed hops 1, unshared 1.73 ns, d -358, p 169/137, margin 248/279; HUB->W5 1 b on-feed hops 1, unshared 1.73 ns, d -358, p 169/137, margin 248/279; W5->HUB 597 b on-feed hops 1, unshared 1.73 ns, d 358, p 169/137, margin 248/279; W5->HUB 1 b on-feed hops 1, unshared 1.73 ns, d 358, p 169/137, margin 248/279; W5->HUB 1 b on-feed hops 1, unshared 1.73 ns, d 358, p 169/137, margin 248/279
  Hop cost: 0 off-feed crossings become chains, max 0 tree hops, 0 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: qc_v2_best_ca+hop.png
Worst crossings, best static (tree_s1.5c3 / top, static count: one whole-cycle k per crossing for TT and FF (no reset-time training)): T148->T147 10 b OFF-feed hops 2, unshared 6.80 ns, d 0, p 514/430, margin -98/-14; T148->T147 512 b OFF-feed hops 2, unshared 6.80 ns, d 0, p 514/430, margin -98/-14; T148->T147 1 b OFF-feed hops 2, unshared 6.80 ns, d 0, p 514/430, margin -98/-14; T148->T147 1 b OFF-feed hops 2, unshared 6.80 ns, d 0, p 514/430, margin -98/-14; T148->T147 32 b OFF-feed hops 2, unshared 6.80 ns, d 0, p 514/430, margin -98/-14
  Render: qc_v2_best_static.png
Worst crossings, best static+hop (tree_s3.5c5 / fish, static count + hop chains): T074->T075 116 b on-feed hops 1, unshared 1.18 ns, d 1178, p 97/77, margin -25/165; T074->T075 520 b on-feed hops 1, unshared 1.18 ns, d 1178, p 97/77, margin -25/165; T074->T075 453 b on-feed hops 1, unshared 1.18 ns, d 1178, p 97/77, margin -25/165; T074->T075 512 b on-feed hops 1, unshared 1.18 ns, d 1178, p 97/77, margin -25/165; T074->T075 1 b on-feed hops 1, unshared 1.18 ns, d 1178, p 97/77, margin -25/165
  Hop cost: 5 off-feed crossings become chains, max 7 tree hops, 7182 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: qc_v2_best_static+hop.png

Tree proposer log (start -> end: loop-closing bits, loop pairs, regions): tree_s2c3.5: 144164 b/160 p/300 r -> 97005 b/119 p/248 r; tree_s3.5c5: 7226 b/8 p/142 r -> 1197 b/1 p/136 r; tree_s1.5c3: 284842 b/230 p/327 r -> 114694 b/155 p/274 r

Verdict rule (12.14b): build only a map/feed whose estimated margin is >= 100 ps TT and FF on every crossing in the ring mode that will be built. Every number here is an ESTIMATE (UNCHECKED) until a GRT + landed_phase_ocv run.
