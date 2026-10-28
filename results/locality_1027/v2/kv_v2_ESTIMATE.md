# 12.14b ESTIMATE v2: kv region map / clock feed / crossings (LOCALITY-SCORE-2, analytic, UNCHECKED)

Inputs: plan physical/die_plan/qwen_kvsys/die_plan.json (sha256 59a8a3ebb4d5), 160 partitions, 3939 ports; v = 321 ps/mm TT; P = 833 ps, budget P/2 = 416.5 ps.
Feeds: fwd = neighbour-forwarded from a parent LEAF (H-tree regions); spine = one spine along the max-bit spanning tree of the region adjacency (through every region centre; H-tree region trees hang off it); fish = the same spine + fishbone region trees (long-axis spine + ribs, leaf delay = Manhattan distance); dme = the spine made zero-skew (DME pads at the spine nodes: nominal d = 0, unshared = height of the last common spine node; LAND-HEAD-3's balanced spine form); top = one balanced die H-tree. Maps: given, v1 = connectivity greedy (span cap), tree_sXcY = proposer v2 (start span X mm, crossing graph made a tree by merge/re-cut up to cap Y mm).
Modes: CURRENT RING = landed_phase_ocv margin with the nominal d (phase-dependent); COUNT-ALIGNED = budget - max(p_up, p_dn), nominal d absorbed by the ring count (ASSUMED definition = LAND-HEAD-3's reading, pending the MESO-COUNT-1 window verdict; it re-centres d per corner, i.e. it ASSUMES the ring count is trained at reset at the operating PVT); STATIC COUNT = one whole-cycle k per crossing for TT and FF (= FOLD: the corner-to-corner shift of d stays in the window). Derate: clk_aocv g021 + droop regions + core latency class B (shared model).

Calibration: derate CHECKED: the 427 measured LAND-HEAD-3 spine_fishbone branches (unshared a/b, distance) through margins(): p model - measured mean -1.3 / min -8.4 ps TT, -1.2 / -8.6 FF; count-aligned worst model +198.2 / +236.2 vs measured +189.8 / +227.6 (model <= 8.6 ps optimistic; calib_derate.py). Geometry UNCHECKED: measured rib hops d 250-290 ps per ~708 um (353-410 ps/mm) vs v -> spine delay up to ~15 % optimistic, so VSCALE=1.15 is run as the pessimistic reading (v2_vs115 table in LOCALITY.md). HEAD partition map: the spine model gives on-feed U <= 1.12 ns (CA +317 / +337) but the 12 channel-loop off-feed ports at 6.1 ns (CA +47 / +119); the built feed closed those loops at one column node (U 2.43 ns, +190 / +228), which is what the tree proposer (merge the loop) and the hop reading (re-time the loop) model.

Hop modes (12.13c): every off-feed crossing (loop-closing or far) is re-timed as a hop chain along the feed-tree path, one fixed-latency landing per tree edge; only feed parent<->child crossings remain. Cost = extra landing cycles (bit-hops), reported per map.

| mode | best map | feed | worst TT / FF ps | <100 TT / FF | >=100 TT and FF |
|---|---|---|---|---|---|
| ring | land128 | top | -52 / 24 | 519 / 189 | no |
| ca | land128 | top | -52 / 24 | 519 / 189 | no |
| ring+hop | tree_s3.5c5 | dme | -318 / -201 | 992 / 846 | no |
| ca+hop | tree_s3.5c5 | fish | 218 / 255 | 0 / 0 | YES |
| static | land128 | top | -52 / 24 | 519 / 189 | no |
| static+hop | land128 | fwd | 46 / -17 | 44 / 196 | no |

| map | feed | regions | max span mm | bit-mm inside | crossing ports | off-feed (loop) ports / pairs | worst unshared ns (on / off feed) | max tree hops | CURRENT RING TT/FF (<100) | COUNT-ALIGNED TT/FF (<100) | hop chains: n / max hops / extra bit-hops | RING+HOP TT/FF (<100) | CA+HOP TT/FF (<100) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| land128 | fwd | 128 | 2.16 | 8.9 % | 3619 | 1350 / 162 | 1.44 / 16.27 | 27 | -15600 / -13238 (3619/3619) | -634 / -434 (313/301) | 1350 / 27 / 807172 | -669 / -506 (2269/2269) | 292 / 316 (0/0) |
| land128 | spine | 128 | 2.16 | 8.9 % | 3619 | 1350 / 162 | 1.20 / 11.63 | 27 | -10628 / -8997 (3619/3619) | -357 / -208 (289/277) | 1350 / 27 / 807172 | -460 / -327 (2269/2269) | 305 / 327 (0/0) |
| land128 | fish | 128 | 2.16 | 8.9 % | 3619 | 1350 / 162 | 1.07 / 11.49 | 27 | -10617 / -8988 (3619/3619) | -345 / -199 (289/266) | 1350 / 27 / 807172 | -449 / -318 (2269/2269) | 317 / 337 (0/0) |
| land128 | dme | 128 | 2.16 | 8.9 % | 3619 | 1350 / 162 | 11.63 / 11.63 | 27 | -585 / -408 (2115/1833) | -585 / -408 (2115/1833) | 1350 / 27 / 807172 | -387 / -262 (1063/917) | -388 / -262 (1063/917) |
| land128 | top | 128 | 2.16 | 8.9 % | 3619 | 3619 / 416 | 0.00 / 6.22 | 2 | -52 / 24 (519/189) | -52 / 24 (519/189) | - | - | - |
| v1_s3.5 | fwd | 50 | 3.44 | 53.6 % | 1885 | 717 / 84 | 2.26 / 17.33 | 15 | -16429 / -13944 (1885/1885) | -688 / -478 (307/301) | 717 / 15 / 314642 | -1310 / -1053 (1168/1168) | 243 / 276 (0/0) |
| v1_s3.5 | spine | 50 | 3.44 | 53.6 % | 1885 | 717 / 84 | 2.29 / 13.44 | 15 | -11979 / -10148 (1885/1885) | -484 / -313 (301/286) | 717 / 15 / 314642 | -1146 / -913 (1168/1168) | 240 / 274 (0/0) |
| v1_s3.5 | fish | 50 | 3.44 | 53.6 % | 1885 | 717 / 84 | 1.65 / 13.16 | 15 | -11968 / -10139 (1885/1885) | -461 / -294 (295/269) | 717 / 15 / 314642 | -1077 / -855 (1168/1168) | 278 / 305 (0/0) |
| v1_s3.5 | dme | 50 | 3.44 | 53.6 % | 1885 | 717 / 84 | 13.44 / 13.44 | 15 | -727 / -526 (1411/1259) | -727 / -526 (1411/1259) | 717 / 15 / 314642 | -513 / -368 (772/672) | -513 / -368 (772/672) |
| v1_s3.5 | top | 50 | 3.44 | 53.6 % | 1885 | 1885 / 182 | 0.00 / 6.41 | 2 | -76 / 5 (548/207) | -76 / 5 (548/207) | - | - | - |
| tree_s2c3.5 | fwd | 72 | 3.18 | 38.0 % | 2553 | 554 / 90 | 2.62 / 15.56 | 17 | -12042 / -10200 (2553/2553) | -611 / -417 (316/301) | 554 / 17 / 417555 | -1498 / -1213 (1999/1999) | 221 / 257 (0/0) |
| tree_s2c3.5 | spine | 72 | 3.18 | 38.0 % | 2553 | 554 / 90 | 2.24 / 11.48 | 17 | -8575 / -7245 (2553/2553) | -389 / -237 (301/289) | 554 / 17 / 417555 | -1241 / -994 (1999/1999) | 239 / 272 (0/0) |
| tree_s2c3.5 | fish | 72 | 3.18 | 38.0 % | 2553 | 554 / 90 | 2.10 / 11.34 | 17 | -8558 / -7231 (2553/2553) | -379 / -228 (292/277) | 554 / 17 / 417555 | -1223 / -979 (1999/1999) | 249 / 281 (0/0) |
| tree_s2c3.5 | dme | 72 | 3.18 | 38.0 % | 2553 | 554 / 90 | 12.44 / 12.44 | 17 | -648 / -461 (1344/1229) | -648 / -461 (1344/1229) | 554 / 17 / 417555 | -455 / -318 (842/753) | -455 / -318 (842/753) |
| tree_s2c3.5 | top | 72 | 3.18 | 38.0 % | 2553 | 2553 / 232 | 0.00 / 6.61 | 2 | -84 / -2 (533/189) | -84 / -2 (533/189) | - | - | - |
| tree_s3.5c5 | fwd | 39 | 4.72 | 59.7 % | 1621 | 473 / 62 | 3.55 / 13.19 | 11 | -11503 / -9746 (1615/1615) | -491 / -322 (193/85) | 473 / 11 / 190265 | -2135 / -1756 (1148/1148) | 167 / 214 (0/0) |
| tree_s3.5c5 | spine | 39 | 4.72 | 59.7 % | 1621 | 473 / 62 | 2.82 / 9.29 | 11 | -6415 / -5403 (1615/1615) | -296 / -165 (85/79) | 473 / 11 / 190265 | -1374 / -1106 (1148/1148) | 202 / 242 (0/0) |
| tree_s3.5c5 | fish | 39 | 4.72 | 59.7 % | 1621 | 473 / 62 | 2.62 / 9.06 | 11 | -6389 / -5381 (1615/1615) | -278 / -150 (85/79) | 473 / 11 / 190265 | -1359 / -1094 (1148/1148) | 218 / 255 (0/0) |
| tree_s3.5c5 | dme | 39 | 4.72 | 59.7 % | 1621 | 473 / 62 | 10.19 / 10.19 | 11 | -458 / -304 (1407/1177) | -458 / -304 (1407/1177) | 473 / 11 / 190265 | -318 / -201 (992/846) | -318 / -200 (992/846) |
| tree_s3.5c5 | top | 39 | 4.72 | 59.7 % | 1621 | 1621 / 138 | 0.00 / 7.00 | 2 | -124 / -35 (679/607) | -124 / -35 (679/607) | - | - | - |
| tree_s1.5c3 | fwd | 158 | 2.36 | 0.7 % | 3905 | 1350 / 193 | 1.47 / 16.41 | 27 | -15857 / -13457 (3905/3905) | -624 / -426 (313/301) | 1350 / 27 / 801422 | -935 / -733 (2555/2555) | 292 / 316 (0/0) |
| tree_s1.5c3 | spine | 158 | 2.36 | 0.7 % | 3905 | 1350 / 193 | 1.57 / 11.43 | 27 | -10628 / -8997 (3905/3572) | -342 / -197 (289/277) | 1350 / 27 / 801422 | -811 / -627 (2555/2245) | 287 / 312 (0/0) |
| tree_s1.5c3 | fish | 158 | 2.36 | 0.7 % | 3905 | 1350 / 193 | 1.10 / 11.30 | 27 | -10617 / -8988 (3905/3572) | -330 / -187 (289/266) | 1350 / 27 / 801422 | -774 / -596 (2555/2245) | 324 / 344 (0/0) |
| tree_s1.5c3 | dme | 158 | 2.36 | 0.7 % | 3905 | 1350 / 193 | 11.43 / 11.43 | 27 | -570 / -395 (2091/1809) | -570 / -396 (2091/1809) | 1350 / 27 / 801422 | -379 / -255 (1039/893) | -379 / -255 (1039/893) |
| tree_s1.5c3 | top | 158 | 2.36 | 0.7 % | 3905 | 3905 / 507 | 0.00 / 6.46 | 2 | -68 / 11 (519/189) | -68 / 11 (519/189) | - | - | - |

Worst crossings, best ring (land128 / top, current ring: phase-dependent, the nominal d counts): hg_EN_7->hub_Eo 1 b OFF-feed hops 2, unshared 6.22 ns, d 0, p 469/393, margin -52/24; hg_EN_7->hub_Eo 267 b OFF-feed hops 2, unshared 6.22 ns, d 0, p 469/393, margin -52/24; hg_EN_7->hub_Eo 138 b OFF-feed hops 2, unshared 6.22 ns, d 0, p 469/393, margin -52/24; hub_Eo->hg_EN_7 572 b OFF-feed hops 2, unshared 6.22 ns, d -0, p 469/393, margin -52/24; hg_WN_7->hub_Wo 1 b OFF-feed hops 2, unshared 6.22 ns, d 0, p 469/393, margin -52/24
  Render: kv_v2_best_ring.png
Worst crossings, best ca (land128 / top, count-aligned: nominal d absorbed by the ring count, only the derated variation counts): hg_EN_7->hub_Eo 1 b OFF-feed hops 2, unshared 6.22 ns, d 0, p 469/393, margin -52/24; hg_EN_7->hub_Eo 267 b OFF-feed hops 2, unshared 6.22 ns, d 0, p 469/393, margin -52/24; hg_EN_7->hub_Eo 138 b OFF-feed hops 2, unshared 6.22 ns, d 0, p 469/393, margin -52/24; hub_Eo->hg_EN_7 572 b OFF-feed hops 2, unshared 6.22 ns, d -0, p 469/393, margin -52/24; hg_WN_7->hub_Wo 1 b OFF-feed hops 2, unshared 6.22 ns, d 0, p 469/393, margin -52/24
  Render: kv_v2_best_ca.png
Worst crossings, best ring+hop (tree_s3.5c5 / dme, current ring, off-feed crossings re-timed as hop chains along the feed tree (12.13c)): T007->T011 1 b on-feed hops 1, unshared 10.19 ns, d 0, p 734/617, margin -318/-201; T007->T011 44 b on-feed hops 1, unshared 10.19 ns, d 0, p 734/617, margin -318/-201; T007->T011 4 b on-feed hops 1, unshared 10.19 ns, d 0, p 734/617, margin -318/-201; T007->T011 44 b on-feed hops 1, unshared 10.19 ns, d 0, p 734/617, margin -318/-201; T007->T011 256 b on-feed hops 1, unshared 10.19 ns, d 0, p 734/617, margin -318/-201
  Hop cost: 473 off-feed crossings become chains, max 11 tree hops, 190265 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: kv_v2_best_ring+hop.png
Worst crossings, best ca+hop (tree_s3.5c5 / fish, count-aligned, off-feed crossings re-timed as hop chains along the feed tree (12.13c)): T015->T019 1 b on-feed hops 1, unshared 2.62 ns, d 1576, p 199/162, margin 218/255; T015->T019 267 b on-feed hops 1, unshared 2.62 ns, d 1576, p 199/162, margin 218/255; T015->T019 138 b on-feed hops 1, unshared 2.62 ns, d 1576, p 199/162, margin 218/255; T019->T015 572 b on-feed hops 1, unshared 2.62 ns, d -1576, p 199/162, margin 218/255; T015->T019 1 b on-feed hops 1, unshared 2.62 ns, d 1576, p 199/162, margin 218/255
  Hop cost: 473 off-feed crossings become chains, max 11 tree hops, 190265 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: kv_v2_best_ca+hop.png
Worst crossings, best static (land128 / top, static count: one whole-cycle k per crossing for TT and FF (no reset-time training)): hg_EN_7->hub_Eo 1 b OFF-feed hops 2, unshared 6.22 ns, d 0, p 469/393, margin -52/24; hg_EN_7->hub_Eo 267 b OFF-feed hops 2, unshared 6.22 ns, d 0, p 469/393, margin -52/24; hg_EN_7->hub_Eo 138 b OFF-feed hops 2, unshared 6.22 ns, d 0, p 469/393, margin -52/24; hub_Eo->hg_EN_7 572 b OFF-feed hops 2, unshared 6.22 ns, d -0, p 469/393, margin -52/24; hg_WN_7->hub_Wo 1 b OFF-feed hops 2, unshared 6.22 ns, d 0, p 469/393, margin -52/24
  Render: kv_v2_best_static.png
Worst crossings, best static+hop (land128 / fwd, static count + hop chains): io_E5->hgi_EN_0 5 b on-feed hops 1, unshared 0.87 ns, d -538, p 90/72, margin 46/-17; io_E5->hgi_EN_0 4 b on-feed hops 1, unshared 0.87 ns, d -538, p 90/72, margin 46/-17; io_E5->hgi_EN_0 1 b on-feed hops 1, unshared 0.87 ns, d -538, p 90/72, margin 46/-17; io_E5->hgi_EN_0 2 b on-feed hops 1, unshared 0.87 ns, d -538, p 90/72, margin 46/-17; io_E5->hgi_EN_0 59 b on-feed hops 1, unshared 0.87 ns, d -538, p 90/72, margin 46/-17
  Hop cost: 1350 off-feed crossings become chains, max 27 tree hops, 807172 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: kv_v2_best_static+hop.png

Tree proposer log (start -> end: loop-closing bits, loop pairs, regions): tree_s2c3.5: 143251 b/81 p/128 r -> 62759 b/45 p/72 r; tree_s3.5c5: 79771 b/42 p/50 r -> 60227 b/31 p/39 r; tree_s1.5c3: 143252 b/113 p/160 r -> 143251 b/112 p/158 r

Verdict rule (12.14b): build only a map/feed whose estimated margin is >= 100 ps TT and FF on every crossing in the ring mode that will be built. Every number here is an ESTIMATE (UNCHECKED) until a GRT + landed_phase_ocv run.
