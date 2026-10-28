# 12.14b ESTIMATE v2: qc region map / clock feed / crossings (LOCALITY-SCORE-2, analytic, UNCHECKED)

Inputs: plan physical/die_plan/qwen_compute/die_plan.json (sha256 54a1aeb5065d), 377 partitions, 3005 ports; v = 199 ps/mm TT; P = 833 ps, budget P/2 = 416.5 ps.
Feeds: fwd = neighbour-forwarded from a parent LEAF (H-tree regions); spine = one spine along the max-bit spanning tree of the region adjacency (through every region centre; H-tree region trees hang off it); fish = the same spine + fishbone region trees (long-axis spine + ribs, leaf delay = Manhattan distance); dme = the spine made zero-skew (DME pads at the spine nodes: nominal d = 0, unshared = height of the last common spine node; LAND-HEAD-3's balanced spine form); top = one balanced die H-tree. Maps: given, v1 = connectivity greedy (span cap), tree_sXcY = proposer v2 (start span X mm, crossing graph made a tree by merge/re-cut up to cap Y mm).
Modes: CURRENT RING = landed_phase_ocv margin with the nominal d (phase-dependent); COUNT-ALIGNED = budget - max(p_up, p_dn), nominal d absorbed by the ring count (ASSUMED definition = LAND-HEAD-3's reading, pending the MESO-COUNT-1 window verdict; it re-centres d per corner, i.e. it ASSUMES the ring count is trained at reset at the operating PVT); STATIC COUNT = one whole-cycle k per crossing for TT and FF (= FOLD: the corner-to-corner shift of d stays in the window). Derate: clk_aocv g021 + droop regions + core latency class B (shared model).

Calibration: derate CHECKED: the 427 measured LAND-HEAD-3 spine_fishbone branches (unshared a/b, distance) through margins(): p model - measured mean -1.3 / min -8.4 ps TT, -1.2 / -8.6 FF; count-aligned worst model +198.2 / +236.2 vs measured +189.8 / +227.6 (model <= 8.6 ps optimistic; calib_derate.py). Geometry UNCHECKED: measured rib hops d 250-290 ps per ~708 um (353-410 ps/mm) vs v -> spine delay up to ~15 % optimistic, so VSCALE=1.15 is run as the pessimistic reading (v2_vs115 table in LOCALITY.md). HEAD partition map: the spine model gives on-feed U <= 1.12 ns (CA +317 / +337) but the 12 channel-loop off-feed ports at 6.1 ns (CA +47 / +119); the built feed closed those loops at one column node (U 2.43 ns, +190 / +228), which is what the tree proposer (merge the loop) and the hop reading (re-time the loop) model.

Hop modes (12.13c): every off-feed crossing (loop-closing or far) is re-timed as a hop chain along the feed-tree path, one fixed-latency landing per tree edge; only feed parent<->child crossings remain. Cost = extra landing cycles (bit-hops), reported per map.

| mode | best map | feed | worst TT / FF ps | <100 TT / FF | >=100 TT and FF |
|---|---|---|---|---|---|
| ring | tree_s1.5c3 | top | -39 / 36 | 290 / 51 | no |
| ca | slices | fish | 264 / 292 | 0 / 0 | YES |
| ring+hop | slices | dme | -127 / -40 | 215 / 151 | no |
| ca+hop | slices | fish | 264 / 292 | 0 / 0 | YES |
| static | tree_s1.5c3 | top | -39 / 36 | 290 / 51 | no |
| static+hop | tree_s3.5c5 | fish | 45 / -19 | 917 / 679 | no |

| map | feed | regions | max span mm | bit-mm inside | crossing ports | off-feed (loop) ports / pairs | worst unshared ns (on / off feed) | max tree hops | CURRENT RING TT/FF (<100) | COUNT-ALIGNED TT/FF (<100) | hop chains: n / max hops / extra bit-hops | RING+HOP TT/FF (<100) | CA+HOP TT/FF (<100) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| slices | fwd | 13 | 26.27 | 97.7 % | 264 | 0 / 0 | 3.64 / 0.00 | 1 | -3346 / -2792 (264/264) | 143 / 194 (0/0) | 0 / 0 / 0 | -3346 / -2792 (264/264) | 143 / 194 (0/0) |
| slices | spine | 13 | 26.27 | 97.7 % | 264 | 0 / 0 | 3.93 / 0.00 | 1 | -952 / -745 (264/264) | 118 / 170 (0/0) | 0 / 0 / 0 | -952 / -745 (264/264) | 118 / 170 (0/0) |
| slices | fish | 13 | 26.27 | 97.7 % | 264 | 0 / 0 | 1.53 / 0.00 | 1 | -1142 / -910 (264/264) | 264 / 292 (0/0) | 0 / 0 / 0 | -1142 / -910 (264/264) | 264 / 292 (0/0) |
| slices | dme | 13 | 26.27 | 97.7 % | 264 | 0 / 0 | 7.41 / 0.00 | 1 | -127 / -40 (215/151) | -127 / -40 (215/151) | 0 / 0 / 0 | -127 / -40 (215/151) | -127 / -40 (215/151) |
| slices | top | 13 | 26.27 | 97.7 % | 264 | 264 / 24 | 0.00 / 6.30 | 2 | -64 / 14 (178/65) | -64 / 14 (178/65) | - | - | - |
| v1_s3.5 | fwd | 142 | 3.28 | 34.1 % | 1418 | 21 / 11 | 1.21 / 4.01 | 10 | -624 / -468 (1404/1399) | 51 / 117 (2/0) | 21 / 10 / 27296 | -624 / -468 (1388/1388) | 307 / 328 (0/0) |
| v1_s3.5 | spine | 142 | 3.28 | 34.1 % | 1418 | 21 / 11 | 1.36 / 3.65 | 10 | -741 / -564 (1404/1190) | 89 / 149 (2/0) | 21 / 10 / 27296 | -563 / -416 (1388/1182) | 294 / 318 (0/0) |
| v1_s3.5 | fish | 142 | 3.28 | 34.1 % | 1418 | 21 / 11 | 0.96 / 3.20 | 10 | -671 / -504 (1377/973) | 125 / 178 (0/0) | 21 / 10 / 27296 | -495 / -358 (1361/965) | 321 / 340 (0/0) |
| v1_s3.5 | dme | 142 | 3.28 | 34.1 % | 1418 | 21 / 11 | 7.67 / 3.65 | 10 | -144 / -54 (526/409) | -144 / -54 (526/409) | 21 / 10 / 27296 | -144 / -54 (520/409) | -144 / -54 (520/409) |
| v1_s3.5 | top | 142 | 3.28 | 34.1 % | 1418 | 1418 / 291 | 0.00 / 5.98 | 2 | -43 / 32 (272/21) | -43 / 32 (272/21) | - | - | - |
| tree_s2c3.5 | fwd | 248 | 3.20 | 25.4 % | 1686 | 207 / 131 | 1.24 / 5.35 | 10 | -4954 / -4161 (1538/1521) | 72 / 140 (20/0) | 207 / 10 / 414969 | -707 / -538 (1449/1443) | 308 / 330 (0/0) |
| tree_s2c3.5 | spine | 248 | 3.20 | 25.4 % | 1686 | 207 / 131 | 1.27 / 4.26 | 10 | -3808 / -3182 (1524/1223) | 132 / 186 (0/0) | 207 / 10 / 414969 | -573 / -424 (1419/1164) | 300 / 323 (0/0) |
| tree_s2c3.5 | fish | 248 | 3.20 | 25.4 % | 1686 | 207 / 131 | 0.88 / 4.20 | 10 | -3802 / -3178 (1481/1226) | 138 / 193 (0/0) | 207 / 10 / 414969 | -547 / -402 (1404/1167) | 332 / 350 (0/0) |
| tree_s2c3.5 | dme | 248 | 3.20 | 25.4 % | 1686 | 207 / 131 | 8.17 / 8.17 | 10 | -251 / -137 (695/516) | -251 / -137 (695/516) | 207 / 10 / 414969 | -176 / -81 (583/428) | -176 / -81 (583/428) |
| tree_s2c3.5 | top | 248 | 3.20 | 25.4 % | 1686 | 1686 / 529 | 0.00 / 5.98 | 2 | -45 / 31 (362/37) | -45 / 31 (362/37) | - | - | - |
| tree_s3.5c5 | fwd | 136 | 4.79 | 35.4 % | 1354 | 5 / 2 | 1.43 / 3.29 | 7 | -838 / -651 (1354/1354) | 121 / 174 (0/0) | 5 / 7 / 7182 | -838 / -651 (1349/1349) | 295 / 319 (0/0) |
| tree_s3.5c5 | spine | 136 | 4.79 | 35.4 % | 1354 | 5 / 2 | 1.54 / 2.86 | 7 | -739 / -565 (1349/1133) | 153 / 200 (0/0) | 5 / 7 / 7182 | -739 / -565 (1344/1128) | 286 / 312 (0/0) |
| tree_s3.5c5 | fish | 136 | 4.79 | 35.4 % | 1354 | 5 / 2 | 1.02 / 2.57 | 7 | -697 / -531 (1354/957) | 174 / 219 (0/0) | 5 / 7 / 7182 | -697 / -531 (1349/952) | 321 / 340 (0/0) |
| tree_s3.5c5 | dme | 136 | 4.79 | 35.4 % | 1354 | 5 / 2 | 7.92 / 3.37 | 7 | -160 / -68 (577/387) | -160 / -68 (577/387) | 5 / 7 / 7182 | -160 / -68 (577/387) | -160 / -68 (577/387) |
| tree_s3.5c5 | top | 136 | 4.79 | 35.4 % | 1354 | 1354 / 272 | 0.00 / 5.96 | 2 | -42 / 33 (263/21) | -42 / 33 (263/21) | - | - | - |
| tree_s1.5c3 | fwd | 274 | 2.68 | 25.5 % | 1759 | 255 / 180 | 1.21 / 5.58 | 11 | -5253 / -4416 (1507/1467) | 68 / 136 (46/0) | 255 / 11 / 478431 | -557 / -411 (1312/1294) | 307 / 328 (0/0) |
| tree_s1.5c3 | spine | 274 | 2.68 | 25.5 % | 1759 | 255 / 180 | 1.27 / 4.39 | 11 | -3999 / -3346 (1357/1135) | 128 / 185 (0/0) | 255 / 11 / 478431 | -458 / -326 (1162/962) | 300 / 323 (0/0) |
| tree_s1.5c3 | fish | 274 | 2.68 | 25.5 % | 1759 | 255 / 180 | 0.96 / 4.33 | 11 | -3994 / -3342 (1443/1252) | 133 / 189 (0/0) | 255 / 11 / 478431 | -416 / -291 (1270/1079) | 321 / 340 (0/0) |
| tree_s1.5c3 | dme | 274 | 2.68 | 25.5 % | 1759 | 255 / 180 | 9.39 / 9.39 | 11 | -353 / -221 (1013/682) | -353 / -221 (1013/682) | 255 / 11 / 478431 | -253 / -147 (799/507) | -253 / -147 (799/507) |
| tree_s1.5c3 | top | 274 | 2.68 | 25.5 % | 1759 | 1759 / 631 | 0.00 / 5.92 | 2 | -39 / 36 (290/51) | -39 / 36 (290/51) | - | - | - |

Worst crossings, best ring (tree_s1.5c3 / top, current ring: phase-dependent, the nominal d counts): T148->T147 10 b OFF-feed hops 2, unshared 5.92 ns, d 0, p 456/381, margin -39/36; T148->T147 512 b OFF-feed hops 2, unshared 5.92 ns, d 0, p 456/381, margin -39/36; T148->T147 1 b OFF-feed hops 2, unshared 5.92 ns, d 0, p 456/381, margin -39/36; T148->T147 1 b OFF-feed hops 2, unshared 5.92 ns, d 0, p 456/381, margin -39/36; T148->T147 32 b OFF-feed hops 2, unshared 5.92 ns, d 0, p 456/381, margin -39/36
  Render: qc_v2_best_ring.png
Worst crossings, best ca (slices / fish, count-aligned: nominal d absorbed by the ring count, only the derated variation counts): HUB->W5 597 b on-feed hops 1, unshared 1.51 ns, d -311, p 153/124, margin 264/292; HUB->W5 1 b on-feed hops 1, unshared 1.51 ns, d -311, p 153/124, margin 264/292; W5->HUB 597 b on-feed hops 1, unshared 1.51 ns, d 311, p 153/124, margin 264/292; W5->HUB 1 b on-feed hops 1, unshared 1.51 ns, d 311, p 153/124, margin 264/292; W5->HUB 1 b on-feed hops 1, unshared 1.51 ns, d 311, p 153/124, margin 264/292
  Render: qc_v2_best_ca.png
Worst crossings, best ring+hop (slices / dme, current ring, off-feed crossings re-timed as hop chains along the feed tree (12.13c)): E0->W0 10 b on-feed hops 1, unshared 7.41 ns, d 0, p 544/456, margin -127/-40; E0->W0 512 b on-feed hops 1, unshared 7.41 ns, d 0, p 544/456, margin -127/-40; E0->W0 1 b on-feed hops 1, unshared 7.41 ns, d 0, p 544/456, margin -127/-40; E0->W0 1 b on-feed hops 1, unshared 7.41 ns, d 0, p 544/456, margin -127/-40; E0->W0 32 b on-feed hops 1, unshared 7.41 ns, d 0, p 544/456, margin -127/-40
  Hop cost: 0 off-feed crossings become chains, max 0 tree hops, 0 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: qc_v2_best_ring+hop.png
Worst crossings, best ca+hop (slices / fish, count-aligned, off-feed crossings re-timed as hop chains along the feed tree (12.13c)): HUB->W5 597 b on-feed hops 1, unshared 1.51 ns, d -311, p 153/124, margin 264/292; HUB->W5 1 b on-feed hops 1, unshared 1.51 ns, d -311, p 153/124, margin 264/292; W5->HUB 597 b on-feed hops 1, unshared 1.51 ns, d 311, p 153/124, margin 264/292; W5->HUB 1 b on-feed hops 1, unshared 1.51 ns, d 311, p 153/124, margin 264/292; W5->HUB 1 b on-feed hops 1, unshared 1.51 ns, d 311, p 153/124, margin 264/292
  Hop cost: 0 off-feed crossings become chains, max 0 tree hops, 0 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: qc_v2_best_ca+hop.png
Worst crossings, best static (tree_s1.5c3 / top, static count: one whole-cycle k per crossing for TT and FF (no reset-time training)): T148->T147 10 b OFF-feed hops 2, unshared 5.92 ns, d 0, p 456/381, margin -39/36; T148->T147 512 b OFF-feed hops 2, unshared 5.92 ns, d 0, p 456/381, margin -39/36; T148->T147 1 b OFF-feed hops 2, unshared 5.92 ns, d 0, p 456/381, margin -39/36; T148->T147 1 b OFF-feed hops 2, unshared 5.92 ns, d 0, p 456/381, margin -39/36; T148->T147 32 b OFF-feed hops 2, unshared 5.92 ns, d 0, p 456/381, margin -39/36
  Render: qc_v2_best_static.png
Worst crossings, best static+hop (tree_s3.5c5 / fish, static count + hop chains): T112->T124 516 b on-feed hops 1, unshared 0.64 ns, d 521, p 74/58, margin 45/-19; T112->T124 516 b on-feed hops 1, unshared 0.64 ns, d 521, p 74/58, margin 45/-19; T112->T124 516 b on-feed hops 1, unshared 0.64 ns, d 521, p 74/58, margin 45/-19; T112->T124 516 b on-feed hops 1, unshared 0.64 ns, d 521, p 74/58, margin 45/-19; T124->T112 514 b on-feed hops 1, unshared 0.64 ns, d -521, p 74/58, margin 45/-19
  Hop cost: 5 off-feed crossings become chains, max 7 tree hops, 7182 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: qc_v2_best_static+hop.png

Tree proposer log (start -> end: loop-closing bits, loop pairs, regions): tree_s2c3.5: 144164 b/160 p/300 r -> 97005 b/119 p/248 r; tree_s3.5c5: 7226 b/8 p/142 r -> 1197 b/1 p/136 r; tree_s1.5c3: 284842 b/230 p/327 r -> 114694 b/155 p/274 r

Verdict rule (12.14b): build only a map/feed whose estimated margin is >= 100 ps TT and FF on every crossing in the ring mode that will be built. Every number here is an ESTIMATE (UNCHECKED) until a GRT + landed_phase_ocv run.
