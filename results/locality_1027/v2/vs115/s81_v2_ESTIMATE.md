# 12.14b ESTIMATE v2: s81 region map / clock feed / crossings (LOCALITY-SCORE-2, analytic, UNCHECKED)

Inputs: plan physical/die_plan/s81/die_plan.json (sha256 1980053c1d7a), 398 partitions, 2306 ports; v = 391 ps/mm TT; P = 833 ps, budget P/2 = 416.5 ps.
Feeds: fwd = neighbour-forwarded from a parent LEAF (H-tree regions); spine = one spine along the max-bit spanning tree of the region adjacency (through every region centre; H-tree region trees hang off it); fish = the same spine + fishbone region trees (long-axis spine + ribs, leaf delay = Manhattan distance); dme = the spine made zero-skew (DME pads at the spine nodes: nominal d = 0, unshared = height of the last common spine node; LAND-HEAD-3's balanced spine form); top = one balanced die H-tree. Maps: given, v1 = connectivity greedy (span cap), tree_sXcY = proposer v2 (start span X mm, crossing graph made a tree by merge/re-cut up to cap Y mm).
Modes: CURRENT RING = landed_phase_ocv margin with the nominal d (phase-dependent); COUNT-ALIGNED = budget - max(p_up, p_dn), nominal d absorbed by the ring count (ASSUMED definition = LAND-HEAD-3's reading, pending the MESO-COUNT-1 window verdict; it re-centres d per corner, i.e. it ASSUMES the ring count is trained at reset at the operating PVT); STATIC COUNT = one whole-cycle k per crossing for TT and FF (= FOLD: the corner-to-corner shift of d stays in the window). Derate: clk_aocv g021 + droop regions + core latency class B (shared model).

Calibration: derate CHECKED: the 427 measured LAND-HEAD-3 spine_fishbone branches (unshared a/b, distance) through margins(): p model - measured mean -1.3 / min -8.4 ps TT, -1.2 / -8.6 FF; count-aligned worst model +198.2 / +236.2 vs measured +189.8 / +227.6 (model <= 8.6 ps optimistic; calib_derate.py). Geometry UNCHECKED: measured rib hops d 250-290 ps per ~708 um (353-410 ps/mm) vs v -> spine delay up to ~15 % optimistic, so VSCALE=1.15 is run as the pessimistic reading (v2_vs115 table in LOCALITY.md). HEAD partition map: the spine model gives on-feed U <= 1.12 ns (CA +317 / +337) but the 12 channel-loop off-feed ports at 6.1 ns (CA +47 / +119); the built feed closed those loops at one column node (U 2.43 ns, +190 / +228), which is what the tree proposer (merge the loop) and the hop reading (re-time the loop) model.

Hop modes (12.13c): every off-feed crossing (loop-closing or far) is re-timed as a hop chain along the feed-tree path, one fixed-latency landing per tree edge; only feed parent<->child crossings remain. Cost = extra landing cycles (bit-hops), reported per map.

| mode | best map | feed | worst TT / FF ps | <100 TT / FF | >=100 TT and FF |
|---|---|---|---|---|---|
| ring | tree_s2c3.5 | top | -495 / -347 | 637 / 437 | no |
| ca | tree_s2c3.5 | top | -495 / -347 | 637 / 437 | no |
| ring+hop | tree_s2c3.5 | dme | -749 / -572 | 1031 / 751 | no |
| ca+hop | land179 | fish | 169 / 217 | 0 / 0 | YES |
| static | tree_s2c3.5 | top | -495 / -347 | 637 / 437 | no |
| static+hop | v1_s3.5 | fish | 14 / -43 | 432 / 257 | no |

| map | feed | regions | max span mm | bit-mm inside | crossing ports | off-feed (loop) ports / pairs | worst unshared ns (on / off feed) | max tree hops | CURRENT RING TT/FF (<100) | COUNT-ALIGNED TT/FF (<100) | hop chains: n / max hops / extra bit-hops | RING+HOP TT/FF (<100) | CA+HOP TT/FF (<100) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| land179 | fwd | 179 | 11.54 | 47.6 % | 1173 | 195 / 67 | 5.75 / 23.33 | 19 | -17332 / -14704 (1173/1173) | -1352 / -1022 (174/120) | 195 / 19 / 306970 | -4757 / -3994 (978/978) | 67 / 133 (13/0) |
| land179 | spine | 179 | 11.54 | 47.6 % | 1173 | 195 / 67 | 5.54 / 17.17 | 19 | -12398 / -10498 (1173/1173) | -934 / -682 (129/106) | 195 / 19 / 306970 | -4192 / -3511 (978/978) | 68 / 133 (14/0) |
| land179 | fish | 179 | 11.54 | 47.6 % | 1173 | 195 / 67 | 3.98 / 16.93 | 19 | -12379 / -10482 (1173/1173) | -911 / -663 (102/88) | 195 / 19 / 306970 | -3527 / -2944 (978/978) | 169 / 217 (0/0) |
| land179 | dme | 179 | 11.54 | 47.6 % | 1173 | 195 / 67 | 19.37 / 19.37 | 19 | -1306 / -996 (893/767) | -1306 / -996 (893/767) | 195 / 19 / 306970 | -885 / -685 (698/572) | -885 / -685 (698/572) |
| land179 | top | 179 | 11.54 | 47.6 % | 1173 | 1173 / 423 | 0.00 / 13.46 | 2 | -580 / -417 (1173/1002) | -580 / -417 (1173/1002) | - | - | - |
| v1_s3.5 | fwd | 210 | 8.66 | 37.5 % | 1336 | 288 / 128 | 3.78 / 20.62 | 25 | -18533 / -15736 (1321/1321) | -1348 / -1026 (147/98) | 288 / 25 / 448712 | -2570 / -2128 (1048/1048) | 166 / 213 (0/0) |
| v1_s3.5 | spine | 210 | 8.66 | 37.5 % | 1336 | 288 / 128 | 3.22 / 15.81 | 25 | -13989 / -11861 (1327/1313) | -1001 / -740 (123/73) | 288 / 25 / 448712 | -1982 / -1626 (1048/1048) | 188 / 229 (0/0) |
| v1_s3.5 | fish | 210 | 8.66 | 37.5 % | 1336 | 288 / 128 | 2.37 / 15.57 | 25 | -13970 / -11845 (1321/1313) | -977 / -720 (107/56) | 288 / 25 / 448712 | -1369 / -1103 (1048/1048) | 239 / 273 (0/0) |
| v1_s3.5 | dme | 210 | 8.66 | 37.5 % | 1336 | 288 / 128 | 19.86 / 19.86 | 25 | -1393 / -1063 (996/865) | -1393 / -1063 (996/865) | 288 / 25 / 448712 | -903 / -702 (724/593) | -903 / -702 (724/593) |
| v1_s3.5 | top | 210 | 8.66 | 37.5 % | 1336 | 1336 / 546 | 0.00 / 12.41 | 2 | -495 / -347 (656/429) | -495 / -347 (656/429) | - | - | - |
| tree_s2c3.5 | fwd | 376 | 8.66 | 7.1 % | 2109 | 269 / 128 | 3.78 / 20.51 | 36 | -13321 / -11289 (2093/2093) | -1219 / -922 (145/84) | 269 / 36 / 668130 | -2573 / -2130 (1840/1840) | 164 / 211 (0/0) |
| tree_s2c3.5 | spine | 376 | 8.66 | 7.1 % | 2109 | 269 / 128 | 3.22 / 14.54 | 36 | -8869 / -7492 (2093/2093) | -764 / -549 (84/57) | 269 / 36 / 668130 | -1982 / -1626 (1840/1840) | 190 / 233 (0/0) |
| tree_s2c3.5 | fish | 376 | 8.66 | 7.1 % | 2109 | 269 / 128 | 2.37 / 14.26 | 36 | -8851 / -7477 (2093/2093) | -740 / -530 (67/54) | 269 / 36 / 668130 | -1369 / -1103 (1840/1840) | 239 / 273 (0/0) |
| tree_s2c3.5 | dme | 376 | 8.66 | 7.1 % | 2109 | 269 / 128 | 17.62 / 17.62 | 36 | -1143 / -863 (1298/1011) | -1143 / -863 (1298/1011) | 269 / 36 / 668130 | -749 / -572 (1031/751) | -749 / -572 (1031/751) |
| tree_s2c3.5 | top | 376 | 8.66 | 7.1 % | 2109 | 2109 / 878 | 0.00 / 12.41 | 2 | -495 / -347 (637/437) | -495 / -347 (637/437) | - | - | - |
| tree_s3.5c5 | fwd | 194 | 8.66 | 41.9 % | 1222 | 223 / 103 | 4.34 / 19.85 | 22 | -12679 / -10730 (1216/1216) | -1328 / -1010 (156/96) | 223 / 22 / 350384 | -2893 / -2403 (999/999) | 125 / 179 (0/0) |
| tree_s3.5c5 | spine | 194 | 8.66 | 41.9 % | 1222 | 223 / 103 | 4.50 / 15.56 | 22 | -9536 / -8053 (1222/1216) | -999 / -740 (118/67) | 223 / 22 / 350384 | -2457 / -2031 (999/999) | 110 / 165 (0/0) |
| tree_s3.5c5 | fish | 194 | 8.66 | 41.9 % | 1222 | 223 / 103 | 3.22 / 15.28 | 22 | -9517 / -8037 (1216/1216) | -975 / -720 (85/60) | 223 / 22 / 350384 | -1986 / -1629 (999/999) | 186 / 230 (0/0) |
| tree_s3.5c5 | dme | 194 | 8.66 | 41.9 % | 1222 | 223 / 103 | 18.86 / 18.86 | 22 | -1299 / -986 (896/740) | -1298 / -986 (896/740) | 223 / 22 / 350384 | -852 / -657 (680/524) | -852 / -657 (680/524) |
| tree_s3.5c5 | top | 194 | 8.66 | 41.9 % | 1222 | 1222 / 489 | 0.00 / 12.41 | 2 | -499 / -351 (707/422) | -499 / -351 (707/422) | - | - | - |
| tree_s1.5c3 | fwd | 376 | 8.66 | 7.1 % | 2109 | 269 / 128 | 3.78 / 20.51 | 36 | -13321 / -11289 (2093/2093) | -1219 / -922 (145/84) | 269 / 36 / 668130 | -2573 / -2130 (1840/1840) | 164 / 211 (0/0) |
| tree_s1.5c3 | spine | 376 | 8.66 | 7.1 % | 2109 | 269 / 128 | 3.22 / 14.54 | 36 | -8869 / -7492 (2093/2093) | -764 / -549 (84/57) | 269 / 36 / 668130 | -1982 / -1626 (1840/1840) | 190 / 233 (0/0) |
| tree_s1.5c3 | fish | 376 | 8.66 | 7.1 % | 2109 | 269 / 128 | 2.37 / 14.26 | 36 | -8851 / -7477 (2093/2093) | -740 / -530 (67/54) | 269 / 36 / 668130 | -1369 / -1103 (1840/1840) | 239 / 273 (0/0) |
| tree_s1.5c3 | dme | 376 | 8.66 | 7.1 % | 2109 | 269 / 128 | 17.62 / 17.62 | 36 | -1143 / -863 (1298/1011) | -1143 / -863 (1298/1011) | 269 / 36 / 668130 | -749 / -572 (1031/751) | -749 / -572 (1031/751) |
| tree_s1.5c3 | top | 376 | 8.66 | 7.1 % | 2109 | 2109 / 878 | 0.00 / 12.41 | 2 | -495 / -347 (637/437) | -495 / -347 (637/437) | - | - | - |

Worst crossings, best ring (tree_s2c3.5 / top, current ring: phase-dependent, the nominal d counts): T004->T005 1368 b OFF-feed hops 2, unshared 12.41 ns, d 0, p 911/764, margin -495/-347; T005->T004 1120 b OFF-feed hops 2, unshared 12.41 ns, d 0, p 911/764, margin -495/-347; T017->T005 1368 b OFF-feed hops 2, unshared 12.41 ns, d -0, p 897/753, margin -480/-337; T005->T017 1120 b OFF-feed hops 2, unshared 12.41 ns, d 0, p 897/753, margin -480/-337; T371->T370 1 b OFF-feed hops 2, unshared 12.41 ns, d -0, p 891/748, margin -474/-332
  Render: s81_v2_best_ring.png
Worst crossings, best ca (tree_s2c3.5 / top, count-aligned: nominal d absorbed by the ring count, only the derated variation counts): T004->T005 1368 b OFF-feed hops 2, unshared 12.41 ns, d 0, p 911/764, margin -495/-347; T005->T004 1120 b OFF-feed hops 2, unshared 12.41 ns, d 0, p 911/764, margin -495/-347; T017->T005 1368 b OFF-feed hops 2, unshared 12.41 ns, d -0, p 897/753, margin -480/-337; T005->T017 1120 b OFF-feed hops 2, unshared 12.41 ns, d 0, p 897/753, margin -480/-337; T371->T370 1 b OFF-feed hops 2, unshared 12.41 ns, d -0, p 891/748, margin -474/-332
  Render: s81_v2_best_ca.png
Worst crossings, best ring+hop (tree_s2c3.5 / dme, current ring, off-feed crossings re-timed as hop chains along the feed tree (12.13c)): T145->T123 1104 b on-feed hops 1, unshared 17.62 ns, d 0, p 1165/988, margin -749/-572; T123->T145 70 b on-feed hops 1, unshared 17.62 ns, d 0, p 1165/988, margin -749/-572; T123->T145 70 b on-feed hops 1, unshared 17.62 ns, d 0, p 1165/988, margin -749/-572; T123->T145 70 b on-feed hops 1, unshared 17.62 ns, d 0, p 1165/988, margin -749/-572; T145->T123 1104 b on-feed hops 1, unshared 17.62 ns, d 0, p 1165/988, margin -749/-572
  Hop cost: 269 off-feed crossings become chains, max 36 tree hops, 668130 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: s81_v2_best_ring+hop.png
Worst crossings, best ca+hop (land179 / fish, count-aligned, off-feed crossings re-timed as hop chains along the feed tree (12.13c)): std_b4_2_0->hard_phy_hbm 2133 b on-feed hops 1, unshared 3.98 ns, d 3696, p 247/199, margin 169/217; std_b4_2_0->hard_phy_hbm 682 b on-feed hops 1, unshared 3.98 ns, d 3696, p 247/199, margin 169/217; hard_phy_hbm->std_b4_2_0 2133 b on-feed hops 1, unshared 3.98 ns, d -3696, p 247/199, margin 169/217; hard_phy_hbm->std_b4_2_0 512 b on-feed hops 1, unshared 3.98 ns, d -3696, p 247/199, margin 169/217; hard_phy_hbm->std_b4_2_0 1607 b on-feed hops 1, unshared 3.98 ns, d -3696, p 247/199, margin 169/217
  Hop cost: 195 off-feed crossings become chains, max 19 tree hops, 306970 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: s81_v2_best_ca+hop.png
Worst crossings, best static (tree_s2c3.5 / top, static count: one whole-cycle k per crossing for TT and FF (no reset-time training)): T004->T005 1368 b OFF-feed hops 2, unshared 12.41 ns, d 0, p 911/764, margin -495/-347; T005->T004 1120 b OFF-feed hops 2, unshared 12.41 ns, d 0, p 911/764, margin -495/-347; T017->T005 1368 b OFF-feed hops 2, unshared 12.41 ns, d -0, p 897/753, margin -480/-337; T005->T017 1120 b OFF-feed hops 2, unshared 12.41 ns, d 0, p 897/753, margin -480/-337; T371->T370 1 b OFF-feed hops 2, unshared 12.41 ns, d -0, p 891/748, margin -474/-332
  Render: s81_v2_best_static.png
Worst crossings, best static+hop (v1_s3.5 / fish, static count + hop chains): R148->R132 1104 b on-feed hops 1, unshared 0.48 ns, d 480, p 60/47, margin 17/-43; R132->R148 70 b on-feed hops 1, unshared 0.48 ns, d -480, p 60/47, margin 17/-43; R132->R148 70 b on-feed hops 1, unshared 0.48 ns, d -480, p 60/47, margin 17/-43; R132->R148 70 b on-feed hops 1, unshared 0.48 ns, d -480, p 60/47, margin 17/-43; R081->R068 1104 b on-feed hops 1, unshared 0.48 ns, d 480, p 60/47, margin 17/-43
  Hop cost: 288 off-feed crossings become chains, max 25 tree hops, 448712 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: s81_v2_best_static+hop.png

Tree proposer log (start -> end: loop-closing bits, loop pairs, regions): tree_s2c3.5: 124232 b/75 p/398 r -> 107624 b/65 p/376 r; tree_s3.5c5: 110290 b/66 p/210 r -> 84575 b/53 p/194 r; tree_s1.5c3: 124232 b/75 p/398 r -> 107624 b/65 p/376 r

Verdict rule (12.14b): build only a map/feed whose estimated margin is >= 100 ps TT and FF on every crossing in the ring mode that will be built. Every number here is an ESTIMATE (UNCHECKED) until a GRT + landed_phase_ocv run.
