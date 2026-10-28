# 12.14b ESTIMATE v2: s81 region map / clock feed / crossings (LOCALITY-SCORE-2, analytic, UNCHECKED)

Inputs: plan physical/die_plan/s81/die_plan.json (sha256 1980053c1d7a), 398 partitions, 2306 ports; v = 340 ps/mm TT; P = 833 ps, budget P/2 = 416.5 ps.
Feeds: fwd = neighbour-forwarded from a parent LEAF (H-tree regions); spine = one spine along the max-bit spanning tree of the region adjacency (through every region centre; H-tree region trees hang off it); fish = the same spine + fishbone region trees (long-axis spine + ribs, leaf delay = Manhattan distance); dme = the spine made zero-skew (DME pads at the spine nodes: nominal d = 0, unshared = height of the last common spine node; LAND-HEAD-3's balanced spine form); top = one balanced die H-tree. Maps: given, v1 = connectivity greedy (span cap), tree_sXcY = proposer v2 (start span X mm, crossing graph made a tree by merge/re-cut up to cap Y mm).
Modes: CURRENT RING = landed_phase_ocv margin with the nominal d (phase-dependent); COUNT-ALIGNED = budget - max(p_up, p_dn), nominal d absorbed by the ring count (ASSUMED definition = LAND-HEAD-3's reading, pending the MESO-COUNT-1 window verdict; it re-centres d per corner, i.e. it ASSUMES the ring count is trained at reset at the operating PVT); STATIC COUNT = one whole-cycle k per crossing for TT and FF (= FOLD: the corner-to-corner shift of d stays in the window). Derate: clk_aocv g021 + droop regions + core latency class B (shared model).

Calibration: derate CHECKED: the 427 measured LAND-HEAD-3 spine_fishbone branches (unshared a/b, distance) through margins(): p model - measured mean -1.3 / min -8.4 ps TT, -1.2 / -8.6 FF; count-aligned worst model +198.2 / +236.2 vs measured +189.8 / +227.6 (model <= 8.6 ps optimistic; calib_derate.py). Geometry UNCHECKED: measured rib hops d 250-290 ps per ~708 um (353-410 ps/mm) vs v -> spine delay up to ~15 % optimistic, so VSCALE=1.15 is run as the pessimistic reading (v2_vs115 table in LOCALITY.md). HEAD partition map: the spine model gives on-feed U <= 1.12 ns (CA +317 / +337) but the 12 channel-loop off-feed ports at 6.1 ns (CA +47 / +119); the built feed closed those loops at one column node (U 2.43 ns, +190 / +228), which is what the tree proposer (merge the loop) and the hop reading (re-time the loop) model.

Hop modes (12.13c): every off-feed crossing (loop-closing or far) is re-timed as a hop chain along the feed-tree path, one fixed-latency landing per tree edge; only feed parent<->child crossings remain. Cost = extra landing cycles (bit-hops), reported per map.

| mode | best map | feed | worst TT / FF ps | <100 TT / FF | >=100 TT and FF |
|---|---|---|---|---|---|
| ring | tree_s2c3.5 | top | -387 / -256 | 637 / 437 | no |
| ca | tree_s2c3.5 | top | -387 / -256 | 637 / 437 | no |
| ring+hop | tree_s2c3.5 | dme | -609 / -452 | 883 / 687 | no |
| ca+hop | land179 | fish | 195 / 238 | 0 / 0 | YES |
| static | tree_s2c3.5 | top | -387 / -256 | 637 / 437 | no |
| static+hop | v1_s3.5 | fish | -197 / -155 | 257 / 257 | no |

| map | feed | regions | max span mm | bit-mm inside | crossing ports | off-feed (loop) ports / pairs | worst unshared ns (on / off feed) | max tree hops | CURRENT RING TT/FF (<100) | COUNT-ALIGNED TT/FF (<100) | hop chains: n / max hops / extra bit-hops | RING+HOP TT/FF (<100) | CA+HOP TT/FF (<100) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| land179 | fwd | 179 | 11.54 | 47.6 % | 1173 | 195 / 67 | 5.00 / 20.29 | 19 | -15028 / -12740 (1173/1173) | -1135 / -845 (120/110) | 195 / 19 / 306970 | -4089 / -3424 (978/978) | 106 / 165 (0/0) |
| land179 | spine | 179 | 11.54 | 47.6 % | 1173 | 195 / 67 | 4.82 / 14.93 | 19 | -10737 / -9082 (1173/1173) | -770 / -548 (110/70) | 195 / 19 / 306970 | -3598 / -3004 (978/978) | 106 / 164 (0/0) |
| land179 | fish | 179 | 11.54 | 47.6 % | 1173 | 195 / 67 | 3.46 / 14.72 | 19 | -10720 / -9068 (1173/1173) | -749 / -531 (88/59) | 195 / 19 / 306970 | -3019 / -2511 (978/978) | 195 / 238 (0/0) |
| land179 | dme | 179 | 11.54 | 47.6 % | 1173 | 195 / 67 | 16.84 / 16.84 | 19 | -1096 / -822 (827/728) | -1096 / -822 (827/728) | 195 / 19 / 306970 | -728 / -551 (632/533) | -728 / -551 (632/533) |
| land179 | top | 179 | 11.54 | 47.6 % | 1173 | 1173 / 423 | 0.00 / 11.70 | 2 | -461 / -317 (1002/675) | -461 / -317 (1002/675) | - | - | - |
| v1_s3.5 | fwd | 210 | 8.66 | 37.5 % | 1336 | 288 / 128 | 3.29 / 17.93 | 25 | -16073 / -13638 (1321/1321) | -1132 / -848 (125/73) | 288 / 25 / 448712 | -2187 / -1801 (1048/1048) | 193 / 235 (0/0) |
| v1_s3.5 | spine | 210 | 8.66 | 37.5 % | 1336 | 288 / 128 | 2.80 / 13.75 | 25 | -12120 / -10267 (1321/1313) | -829 / -599 (101/51) | 288 / 25 / 448712 | -1675 / -1364 (1048/1048) | 212 / 249 (0/0) |
| v1_s3.5 | fish | 210 | 8.66 | 37.5 % | 1336 | 288 / 128 | 2.06 / 13.54 | 25 | -12104 / -10253 (1313/1313) | -808 / -582 (73/51) | 288 / 25 / 448712 | -1142 / -909 (1048/1048) | 256 / 287 (0/0) |
| v1_s3.5 | dme | 210 | 8.66 | 37.5 % | 1336 | 288 / 128 | 17.27 / 17.27 | 25 | -1171 / -881 (930/806) | -1171 / -881 (930/806) | 288 / 25 / 448712 | -744 / -566 (658/534) | -744 / -566 (658/534) |
| v1_s3.5 | top | 210 | 8.66 | 37.5 % | 1336 | 1336 / 546 | 0.00 / 10.79 | 2 | -387 / -256 (656/429) | -387 / -256 (656/429) | - | - | - |
| tree_s2c3.5 | fwd | 376 | 8.66 | 7.1 % | 2109 | 269 / 128 | 3.29 / 17.84 | 36 | -11540 / -9770 (2093/2093) | -1019 / -758 (91/67) | 269 / 36 / 668130 | -2189 / -1802 (1840/1840) | 191 / 233 (0/0) |
| tree_s2c3.5 | spine | 376 | 8.66 | 7.1 % | 2109 | 269 / 128 | 2.80 / 12.65 | 36 | -7668 / -6468 (2093/2093) | -622 / -432 (67/48) | 269 / 36 / 668130 | -1675 / -1364 (1840/1840) | 214 / 252 (0/0) |
| tree_s2c3.5 | fish | 376 | 8.66 | 7.1 % | 2109 | 269 / 128 | 2.06 / 12.40 | 36 | -7651 / -6455 (2093/2093) | -602 / -416 (60/43) | 269 / 36 / 668130 | -1142 / -909 (1840/1840) | 256 / 287 (0/0) |
| tree_s2c3.5 | dme | 376 | 8.66 | 7.1 % | 2109 | 269 / 128 | 15.32 / 15.32 | 36 | -954 / -706 (1146/947) | -954 / -706 (1146/947) | 269 / 36 / 668130 | -609 / -452 (883/687) | -609 / -452 (883/687) |
| tree_s2c3.5 | top | 376 | 8.66 | 7.1 % | 2109 | 2109 / 878 | 0.00 / 10.79 | 2 | -387 / -256 (637/437) | -387 / -256 (637/437) | - | - | - |
| tree_s3.5c5 | fwd | 194 | 8.66 | 41.9 % | 1222 | 223 / 103 | 3.78 / 17.26 | 22 | -10982 / -9286 (1216/1216) | -1114 / -834 (102/73) | 223 / 22 / 350384 | -2467 / -2039 (999/999) | 157 / 206 (0/0) |
| tree_s3.5c5 | spine | 194 | 8.66 | 41.9 % | 1222 | 223 / 103 | 3.91 / 13.53 | 22 | -8249 / -6956 (1216/1216) | -828 / -599 (76/54) | 223 / 22 / 350384 | -2089 / -1717 (999/999) | 144 / 193 (0/0) |
| tree_s3.5c5 | fish | 194 | 8.66 | 41.9 % | 1222 | 223 / 103 | 2.80 / 13.29 | 22 | -8232 / -6942 (1216/1216) | -807 / -582 (67/50) | 223 / 22 / 350384 | -1678 / -1366 (999/999) | 211 / 250 (0/0) |
| tree_s3.5c5 | dme | 194 | 8.66 | 41.9 % | 1222 | 223 / 103 | 16.40 / 16.40 | 22 | -1089 / -814 (836/696) | -1089 / -814 (836/696) | 223 / 22 / 350384 | -699 / -526 (620/493) | -699 / -526 (620/493) |
| tree_s3.5c5 | top | 194 | 8.66 | 41.9 % | 1222 | 1222 / 489 | 0.00 / 10.79 | 2 | -391 / -259 (635/422) | -391 / -259 (635/422) | - | - | - |
| tree_s1.5c3 | fwd | 376 | 8.66 | 7.1 % | 2109 | 269 / 128 | 3.29 / 17.84 | 36 | -11540 / -9770 (2093/2093) | -1019 / -758 (91/67) | 269 / 36 / 668130 | -2189 / -1802 (1840/1840) | 191 / 233 (0/0) |
| tree_s1.5c3 | spine | 376 | 8.66 | 7.1 % | 2109 | 269 / 128 | 2.80 / 12.65 | 36 | -7668 / -6468 (2093/2093) | -622 / -432 (67/48) | 269 / 36 / 668130 | -1675 / -1364 (1840/1840) | 214 / 252 (0/0) |
| tree_s1.5c3 | fish | 376 | 8.66 | 7.1 % | 2109 | 269 / 128 | 2.06 / 12.40 | 36 | -7651 / -6455 (2093/2093) | -602 / -416 (60/43) | 269 / 36 / 668130 | -1142 / -909 (1840/1840) | 256 / 287 (0/0) |
| tree_s1.5c3 | dme | 376 | 8.66 | 7.1 % | 2109 | 269 / 128 | 15.32 / 15.32 | 36 | -954 / -706 (1146/947) | -954 / -706 (1146/947) | 269 / 36 / 668130 | -609 / -452 (883/687) | -609 / -452 (883/687) |
| tree_s1.5c3 | top | 376 | 8.66 | 7.1 % | 2109 | 2109 / 878 | 0.00 / 10.79 | 2 | -387 / -256 (637/437) | -387 / -256 (637/437) | - | - | - |

Worst crossings, best ring (tree_s2c3.5 / top, current ring: phase-dependent, the nominal d counts): T004->T005 1368 b OFF-feed hops 2, unshared 10.79 ns, d -0, p 803/672, margin -387/-256; T005->T004 1120 b OFF-feed hops 2, unshared 10.79 ns, d 0, p 803/672, margin -387/-256; T017->T005 1368 b OFF-feed hops 2, unshared 10.79 ns, d 0, p 791/663, margin -374/-247; T005->T017 1120 b OFF-feed hops 2, unshared 10.79 ns, d 0, p 791/663, margin -374/-247; T371->T370 1 b OFF-feed hops 2, unshared 10.79 ns, d 0, p 785/659, margin -369/-243
  Render: s81_v2_best_ring.png
Worst crossings, best ca (tree_s2c3.5 / top, count-aligned: nominal d absorbed by the ring count, only the derated variation counts): T004->T005 1368 b OFF-feed hops 2, unshared 10.79 ns, d -0, p 803/672, margin -387/-256; T005->T004 1120 b OFF-feed hops 2, unshared 10.79 ns, d 0, p 803/672, margin -387/-256; T017->T005 1368 b OFF-feed hops 2, unshared 10.79 ns, d 0, p 791/663, margin -374/-247; T005->T017 1120 b OFF-feed hops 2, unshared 10.79 ns, d 0, p 791/663, margin -374/-247; T371->T370 1 b OFF-feed hops 2, unshared 10.79 ns, d 0, p 785/659, margin -369/-242
  Render: s81_v2_best_ca.png
Worst crossings, best ring+hop (tree_s2c3.5 / dme, current ring, off-feed crossings re-timed as hop chains along the feed tree (12.13c)): T145->T123 1104 b on-feed hops 1, unshared 15.32 ns, d 0, p 1026/869, margin -609/-452; T123->T145 70 b on-feed hops 1, unshared 15.32 ns, d 0, p 1026/869, margin -609/-452; T123->T145 70 b on-feed hops 1, unshared 15.32 ns, d 0, p 1026/869, margin -609/-452; T123->T145 70 b on-feed hops 1, unshared 15.32 ns, d 0, p 1026/869, margin -609/-452; T145->T123 1104 b on-feed hops 1, unshared 15.32 ns, d 0, p 1026/869, margin -609/-452
  Hop cost: 269 off-feed crossings become chains, max 36 tree hops, 668130 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: s81_v2_best_ring+hop.png
Worst crossings, best ca+hop (land179 / fish, count-aligned, off-feed crossings re-timed as hop chains along the feed tree (12.13c)): std_b4_2_0->hard_phy_hbm 2133 b on-feed hops 1, unshared 3.46 ns, d 3214, p 221/178, margin 195/238; std_b4_2_0->hard_phy_hbm 682 b on-feed hops 1, unshared 3.46 ns, d 3214, p 221/178, margin 195/238; hard_phy_hbm->std_b4_2_0 2133 b on-feed hops 1, unshared 3.46 ns, d -3214, p 221/178, margin 195/238; hard_phy_hbm->std_b4_2_0 512 b on-feed hops 1, unshared 3.46 ns, d -3214, p 221/178, margin 195/238; hard_phy_hbm->std_b4_2_0 1607 b on-feed hops 1, unshared 3.46 ns, d -3214, p 221/178, margin 195/238
  Hop cost: 195 off-feed crossings become chains, max 19 tree hops, 306970 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: s81_v2_best_ca+hop.png
Worst crossings, best static (tree_s2c3.5 / top, static count: one whole-cycle k per crossing for TT and FF (no reset-time training)): T004->T005 1368 b OFF-feed hops 2, unshared 10.79 ns, d -0, p 803/672, margin -387/-256; T005->T004 1120 b OFF-feed hops 2, unshared 10.79 ns, d 0, p 803/672, margin -387/-256; T017->T005 1368 b OFF-feed hops 2, unshared 10.79 ns, d 0, p 791/663, margin -374/-247; T005->T017 1120 b OFF-feed hops 2, unshared 10.79 ns, d 0, p 791/663, margin -374/-247; T371->T370 1 b OFF-feed hops 2, unshared 10.79 ns, d 0, p 785/659, margin -369/-242
  Render: s81_v2_best_static.png
Worst crossings, best static+hop (v1_s3.5 / fish, static count + hop chains): R005->R019 1120 b on-feed hops 1, unshared 1.53 ns, d 1325, p 121/97, margin -197/19; R019->R005 1368 b on-feed hops 1, unshared 1.53 ns, d -1325, p 121/97, margin -197/19; R078->R055 1104 b on-feed hops 1, unshared 1.32 ns, d -1325, p 104/82, margin -179/34; R055->R032 1104 b on-feed hops 1, unshared 1.32 ns, d 1325, p 104/82, margin -179/34; R032->R055 70 b on-feed hops 1, unshared 1.32 ns, d -1325, p 104/82, margin -179/34
  Hop cost: 288 off-feed crossings become chains, max 25 tree hops, 448712 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: s81_v2_best_static+hop.png

Tree proposer log (start -> end: loop-closing bits, loop pairs, regions): tree_s2c3.5: 124232 b/75 p/398 r -> 107624 b/65 p/376 r; tree_s3.5c5: 110290 b/66 p/210 r -> 84575 b/53 p/194 r; tree_s1.5c3: 124232 b/75 p/398 r -> 107624 b/65 p/376 r

Verdict rule (12.14b): build only a map/feed whose estimated margin is >= 100 ps TT and FF on every crossing in the ring mode that will be built. Every number here is an ESTIMATE (UNCHECKED) until a GRT + landed_phase_ocv run.
