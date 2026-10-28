# 12.14b ESTIMATE v2: kv region map / clock feed / crossings (LOCALITY-SCORE-2, analytic, UNCHECKED)

Inputs: plan physical/die_plan/qwen_kvsys/die_plan.json (sha256 59a8a3ebb4d5), 160 partitions, 3939 ports; v = 369.1 ps/mm TT; P = 833 ps, budget P/2 = 416.5 ps.
Feeds: fwd = neighbour-forwarded from a parent LEAF (H-tree regions); spine = one spine along the max-bit spanning tree of the region adjacency (through every region centre; H-tree region trees hang off it); fish = the same spine + fishbone region trees (long-axis spine + ribs, leaf delay = Manhattan distance); dme = the spine made zero-skew (DME pads at the spine nodes: nominal d = 0, unshared = height of the last common spine node; LAND-HEAD-3's balanced spine form); top = one balanced die H-tree. Maps: given, v1 = connectivity greedy (span cap), tree_sXcY = proposer v2 (start span X mm, crossing graph made a tree by merge/re-cut up to cap Y mm).
Modes: CURRENT RING = landed_phase_ocv margin with the nominal d (phase-dependent); COUNT-ALIGNED = budget - max(p_up, p_dn), nominal d absorbed by the ring count (ASSUMED definition = LAND-HEAD-3's reading, pending the MESO-COUNT-1 window verdict; it re-centres d per corner, i.e. it ASSUMES the ring count is trained at reset at the operating PVT); STATIC COUNT = one whole-cycle k per crossing for TT and FF (= FOLD: the corner-to-corner shift of d stays in the window). Derate: clk_aocv g021 + droop regions + core latency class B (shared model).

Calibration: derate CHECKED: the 427 measured LAND-HEAD-3 spine_fishbone branches (unshared a/b, distance) through margins(): p model - measured mean -1.3 / min -8.4 ps TT, -1.2 / -8.6 FF; count-aligned worst model +198.2 / +236.2 vs measured +189.8 / +227.6 (model <= 8.6 ps optimistic; calib_derate.py). Geometry UNCHECKED: measured rib hops d 250-290 ps per ~708 um (353-410 ps/mm) vs v -> spine delay up to ~15 % optimistic, so VSCALE=1.15 is run as the pessimistic reading (v2_vs115 table in LOCALITY.md). HEAD partition map: the spine model gives on-feed U <= 1.12 ns (CA +317 / +337) but the 12 channel-loop off-feed ports at 6.1 ns (CA +47 / +119); the built feed closed those loops at one column node (U 2.43 ns, +190 / +228), which is what the tree proposer (merge the loop) and the hop reading (re-time the loop) model.

Hop modes (12.13c): every off-feed crossing (loop-closing or far) is re-timed as a hop chain along the feed-tree path, one fixed-latency landing per tree edge; only feed parent<->child crossings remain. Cost = extra landing cycles (bit-hops), reported per map.

| mode | best map | feed | worst TT / FF ps | <100 TT / FF | >=100 TT and FF |
|---|---|---|---|---|---|
| ring | land128 | top | -113 / -28 | 519 / 189 | no |
| ca | land128 | top | -113 / -28 | 519 / 189 | no |
| ring+hop | tree_s3.5c5 | dme | -416 / -284 | 1004 / 874 | no |
| ca+hop | tree_s3.5c5 | fish | 195 / 236 | 0 / 0 | YES |
| static | land128 | top | -113 / -28 | 519 / 189 | no |
| static+hop | land128 | fwd | 7 / 47 | 118 / 44 | no |

| map | feed | regions | max span mm | bit-mm inside | crossing ports | off-feed (loop) ports / pairs | worst unshared ns (on / off feed) | max tree hops | CURRENT RING TT/FF (<100) | COUNT-ALIGNED TT/FF (<100) | hop chains: n / max hops / extra bit-hops | RING+HOP TT/FF (<100) | CA+HOP TT/FF (<100) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| land128 | fwd | 128 | 2.16 | 8.9 % | 3619 | 1350 / 162 | 1.65 / 18.71 | 27 | -17989 / -15276 (3619/3619) | -779 / -552 (316/304) | 1350 / 27 / 807172 | -826 / -640 (2269/2269) | 279 / 305 (0/0) |
| land128 | spine | 128 | 2.16 | 8.9 % | 3619 | 1350 / 162 | 1.39 / 13.37 | 27 | -12273 / -10400 (3619/3619) | -461 / -293 (301/286) | 1350 / 27 / 807172 | -585 / -434 (2269/2269) | 295 / 319 (0/0) |
| land128 | fish | 128 | 2.16 | 8.9 % | 3619 | 1350 / 162 | 1.23 / 13.21 | 27 | -12260 / -10389 (3619/3619) | -448 / -283 (298/277) | 1350 / 27 / 807172 | -573 / -424 (2269/2269) | 307 / 328 (0/0) |
| land128 | dme | 128 | 2.16 | 8.9 % | 3619 | 1350 / 162 | 13.37 / 13.37 | 27 | -722 / -521 (2313/2018) | -722 / -521 (2313/2018) | 1350 / 27 / 807172 | -495 / -354 (1193/1034) | -495 / -354 (1193/1034) |
| land128 | top | 128 | 2.16 | 8.9 % | 3619 | 3619 / 416 | 0.00 / 7.16 | 2 | -113 / -28 (519/189) | -113 / -28 (519/189) | - | - | - |
| v1_s3.5 | fwd | 50 | 3.44 | 53.6 % | 1885 | 717 / 84 | 2.60 / 19.93 | 15 | -18942 / -16088 (1885/1885) | -841 / -602 (393/301) | 717 / 15 / 314642 | -1562 / -1268 (1168/1168) | 224 / 260 (0/0) |
| v1_s3.5 | spine | 50 | 3.44 | 53.6 % | 1885 | 717 / 84 | 2.63 / 15.46 | 15 | -13826 / -11724 (1885/1885) | -606 / -413 (304/295) | 717 / 15 / 314642 | -1374 / -1107 (1168/1168) | 220 / 257 (0/0) |
| v1_s3.5 | fish | 50 | 3.44 | 53.6 % | 1885 | 717 / 84 | 1.90 / 15.14 | 15 | -13813 / -11713 (1885/1885) | -581 / -392 (301/289) | 717 / 15 / 314642 | -1295 / -1041 (1168/1168) | 264 / 294 (0/0) |
| v1_s3.5 | dme | 50 | 3.44 | 53.6 % | 1885 | 717 / 84 | 15.46 / 15.46 | 15 | -884 / -656 (1487/1411) | -884 / -656 (1487/1411) | 717 / 15 / 314642 | -638 / -475 (822/772) | -638 / -475 (822/772) |
| v1_s3.5 | top | 50 | 3.44 | 53.6 % | 1885 | 1885 / 182 | 0.00 / 7.37 | 2 | -140 / -49 (698/548) | -140 / -49 (698/548) | - | - | - |
| tree_s2c3.5 | fwd | 72 | 3.18 | 38.0 % | 2553 | 554 / 90 | 3.01 / 17.89 | 17 | -13896 / -11783 (2553/2553) | -752 / -532 (319/310) | 554 / 17 / 417555 | -1778 / -1452 (1999/1999) | 198 / 239 (0/0) |
| tree_s2c3.5 | spine | 72 | 3.18 | 38.0 % | 2553 | 554 / 90 | 2.58 / 13.20 | 17 | -9912 / -8386 (2553/2553) | -499 / -327 (313/295) | 554 / 17 / 417555 | -1484 / -1201 (1999/1999) | 219 / 256 (0/0) |
| tree_s2c3.5 | fish | 72 | 3.18 | 38.0 % | 2553 | 554 / 90 | 2.42 / 13.04 | 17 | -9893 / -8370 (2553/2553) | -486 / -316 (307/292) | 554 / 17 / 417555 | -1462 / -1183 (1999/1999) | 231 / 266 (0/0) |
| tree_s2c3.5 | dme | 72 | 3.18 | 38.0 % | 2553 | 554 / 90 | 14.30 / 14.30 | 17 | -794 / -581 (1531/1327) | -794 / -581 (1531/1327) | 554 / 17 / 417555 | -573 / -418 (1003/825) | -573 / -418 (1003/825) |
| tree_s2c3.5 | top | 72 | 3.18 | 38.0 % | 2553 | 2553 / 232 | 0.00 / 7.60 | 2 | -148 / -57 (691/533) | -148 / -57 (691/533) | - | - | - |
| tree_s3.5c5 | fwd | 39 | 4.72 | 59.7 % | 1621 | 473 / 62 | 4.08 / 15.17 | 11 | -13279 / -11262 (1621/1615) | -615 / -423 (326/137) | 473 / 11 / 190265 | -2509 / -2075 (1148/1148) | 138 / 190 (0/0) |
| tree_s3.5c5 | spine | 39 | 4.72 | 59.7 % | 1621 | 473 / 62 | 3.24 / 10.69 | 11 | -7429 / -6267 (1615/1615) | -391 / -243 (146/85) | 473 / 11 / 190265 | -1635 / -1329 (1148/1148) | 178 / 222 (0/0) |
| tree_s3.5c5 | fish | 39 | 4.72 | 59.7 % | 1621 | 473 / 62 | 3.01 / 10.41 | 11 | -7399 / -6243 (1615/1615) | -370 / -226 (111/82) | 473 / 11 / 190265 | -1617 / -1314 (1148/1148) | 195 / 236 (0/0) |
| tree_s3.5c5 | dme | 39 | 4.72 | 59.7 % | 1621 | 473 / 62 | 11.72 / 11.72 | 11 | -577 / -403 (1419/1231) | -577 / -403 (1419/1231) | 473 / 11 / 190265 | -416 / -284 (1004/874) | -416 / -284 (1004/874) |
| tree_s3.5c5 | top | 39 | 4.72 | 59.7 % | 1621 | 1621 / 138 | 0.00 / 8.05 | 2 | -195 / -95 (785/607) | -195 / -95 (785/607) | - | - | - |
| tree_s1.5c3 | fwd | 158 | 2.36 | 0.7 % | 3905 | 1350 / 193 | 1.69 / 18.86 | 27 | -18284 / -15528 (3905/3905) | -767 / -542 (316/304) | 1350 / 27 / 801422 | -1131 / -900 (2555/2555) | 279 / 305 (0/0) |
| tree_s1.5c3 | spine | 158 | 2.36 | 0.7 % | 3905 | 1350 / 193 | 1.81 / 13.15 | 27 | -12273 / -10400 (3905/3905) | -444 / -280 (301/286) | 1350 / 27 / 801422 | -990 / -780 (2555/2555) | 273 / 301 (0/0) |
| tree_s1.5c3 | fish | 158 | 2.36 | 0.7 % | 3905 | 1350 / 193 | 1.26 / 12.99 | 27 | -12260 / -10389 (3905/3905) | -431 / -269 (298/277) | 1350 / 27 / 801422 | -946 / -743 (2555/2555) | 316 / 337 (0/0) |
| tree_s1.5c3 | dme | 158 | 2.36 | 0.7 % | 3905 | 1350 / 193 | 13.15 / 13.15 | 27 | -704 / -507 (2289/1994) | -704 / -507 (2289/1994) | 1350 / 27 / 801422 | -486 / -346 (1169/1010) | -486 / -346 (1169/1010) |
| tree_s1.5c3 | top | 158 | 2.36 | 0.7 % | 3905 | 3905 / 507 | 0.00 / 7.43 | 2 | -130 / -42 (519/519) | -130 / -42 (519/519) | - | - | - |

Worst crossings, best ring (land128 / top, current ring: phase-dependent, the nominal d counts): hg_EN_7->hub_Eo 1 b OFF-feed hops 2, unshared 7.16 ns, d 0, p 529/444, margin -113/-28; hg_EN_7->hub_Eo 267 b OFF-feed hops 2, unshared 7.16 ns, d 0, p 529/444, margin -113/-28; hg_EN_7->hub_Eo 138 b OFF-feed hops 2, unshared 7.16 ns, d 0, p 529/444, margin -113/-28; hub_Eo->hg_EN_7 572 b OFF-feed hops 2, unshared 7.16 ns, d 0, p 529/444, margin -113/-28; hg_WN_7->hub_Wo 1 b OFF-feed hops 2, unshared 7.16 ns, d 0, p 529/444, margin -113/-28
  Render: kv_v2_best_ring.png
Worst crossings, best ca (land128 / top, count-aligned: nominal d absorbed by the ring count, only the derated variation counts): hg_EN_7->hub_Eo 1 b OFF-feed hops 2, unshared 7.16 ns, d 0, p 529/444, margin -113/-28; hg_EN_7->hub_Eo 267 b OFF-feed hops 2, unshared 7.16 ns, d 0, p 529/444, margin -113/-28; hg_EN_7->hub_Eo 138 b OFF-feed hops 2, unshared 7.16 ns, d 0, p 529/444, margin -113/-28; hub_Eo->hg_EN_7 572 b OFF-feed hops 2, unshared 7.16 ns, d 0, p 529/444, margin -113/-28; hg_WN_7->hub_Wo 1 b OFF-feed hops 2, unshared 7.16 ns, d 0, p 529/444, margin -113/-28
  Render: kv_v2_best_ca.png
Worst crossings, best ring+hop (tree_s3.5c5 / dme, current ring, off-feed crossings re-timed as hop chains along the feed tree (12.13c)): T007->T011 1 b on-feed hops 1, unshared 11.72 ns, d 0, p 832/700, margin -416/-284; T007->T011 44 b on-feed hops 1, unshared 11.72 ns, d 0, p 832/700, margin -416/-284; T007->T011 4 b on-feed hops 1, unshared 11.72 ns, d 0, p 832/700, margin -416/-284; T007->T011 44 b on-feed hops 1, unshared 11.72 ns, d 0, p 832/700, margin -416/-284; T007->T011 256 b on-feed hops 1, unshared 11.72 ns, d 0, p 832/700, margin -416/-284
  Hop cost: 473 off-feed crossings become chains, max 11 tree hops, 190265 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: kv_v2_best_ring+hop.png
Worst crossings, best ca+hop (tree_s3.5c5 / fish, count-aligned, off-feed crossings re-timed as hop chains along the feed tree (12.13c)): T015->T019 1 b on-feed hops 1, unshared 3.01 ns, d 1812, p 221/180, margin 195/236; T015->T019 267 b on-feed hops 1, unshared 3.01 ns, d 1812, p 221/180, margin 195/236; T015->T019 138 b on-feed hops 1, unshared 3.01 ns, d 1812, p 221/180, margin 195/236; T019->T015 572 b on-feed hops 1, unshared 3.01 ns, d -1812, p 221/180, margin 195/236; T015->T019 1 b on-feed hops 1, unshared 3.01 ns, d 1812, p 221/180, margin 195/236
  Hop cost: 473 off-feed crossings become chains, max 11 tree hops, 190265 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: kv_v2_best_ca+hop.png
Worst crossings, best static (land128 / top, static count: one whole-cycle k per crossing for TT and FF (no reset-time training)): hg_EN_7->hub_Eo 1 b OFF-feed hops 2, unshared 7.16 ns, d 0, p 529/444, margin -113/-28; hg_EN_7->hub_Eo 267 b OFF-feed hops 2, unshared 7.16 ns, d 0, p 529/444, margin -113/-28; hg_EN_7->hub_Eo 138 b OFF-feed hops 2, unshared 7.16 ns, d 0, p 529/444, margin -113/-28; hub_Eo->hg_EN_7 572 b OFF-feed hops 2, unshared 7.16 ns, d 0, p 529/444, margin -113/-28; hg_WN_7->hub_Wo 1 b OFF-feed hops 2, unshared 7.16 ns, d 0, p 529/444, margin -113/-28
  Render: kv_v2_best_static.png
Worst crossings, best static+hop (land128 / fwd, static count + hop chains): hub_C->hub_Ei 35 b on-feed hops 1, unshared 1.65 ns, d -1107, p 136/110, margin 7/193; hub_C->hub_Ei 35 b on-feed hops 1, unshared 1.65 ns, d -1107, p 136/110, margin 7/193; hub_C->hub_Ei 1 b on-feed hops 1, unshared 1.65 ns, d -1107, p 136/110, margin 7/193; hub_Ei->hub_C 1 b on-feed hops 1, unshared 1.65 ns, d 1107, p 136/110, margin 7/193; hub_Ei->hub_C 43 b on-feed hops 1, unshared 1.65 ns, d 1107, p 136/110, margin 7/193
  Hop cost: 1350 off-feed crossings become chains, max 27 tree hops, 807172 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: kv_v2_best_static+hop.png

Tree proposer log (start -> end: loop-closing bits, loop pairs, regions): tree_s2c3.5: 143251 b/81 p/128 r -> 62759 b/45 p/72 r; tree_s3.5c5: 79771 b/42 p/50 r -> 60227 b/31 p/39 r; tree_s1.5c3: 143252 b/113 p/160 r -> 143251 b/112 p/158 r

Verdict rule (12.14b): build only a map/feed whose estimated margin is >= 100 ps TT and FF on every crossing in the ring mode that will be built. Every number here is an ESTIMATE (UNCHECKED) until a GRT + landed_phase_ocv run.
