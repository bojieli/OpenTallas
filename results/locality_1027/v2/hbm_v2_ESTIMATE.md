# 12.14b ESTIMATE v2: hbm region map / clock feed / crossings (LOCALITY-SCORE-2, analytic, UNCHECKED)

Inputs: plan /srv/opentallas-scratch2/claude/hbm-streets2-1027/c18/die_plan.json (sha256 6a711a87b7e7), 88 partitions, 631 ports; v = 340 ps/mm TT; P = 833 ps, budget P/2 = 416.5 ps.
Feeds: fwd = neighbour-forwarded from a parent LEAF (H-tree regions); spine = one spine along the max-bit spanning tree of the region adjacency (through every region centre; H-tree region trees hang off it); fish = the same spine + fishbone region trees (long-axis spine + ribs, leaf delay = Manhattan distance); dme = the spine made zero-skew (DME pads at the spine nodes: nominal d = 0, unshared = height of the last common spine node; LAND-HEAD-3's balanced spine form); top = one balanced die H-tree. Maps: given, v1 = connectivity greedy (span cap), tree_sXcY = proposer v2 (start span X mm, crossing graph made a tree by merge/re-cut up to cap Y mm).
Modes: CURRENT RING = landed_phase_ocv margin with the nominal d (phase-dependent); COUNT-ALIGNED = budget - max(p_up, p_dn), nominal d absorbed by the ring count (ASSUMED definition = LAND-HEAD-3's reading, pending the MESO-COUNT-1 window verdict; it re-centres d per corner, i.e. it ASSUMES the ring count is trained at reset at the operating PVT); STATIC COUNT = one whole-cycle k per crossing for TT and FF (= FOLD: the corner-to-corner shift of d stays in the window). Derate: clk_aocv g021 + droop regions + core latency class B (shared model).

Calibration: derate CHECKED: the 427 measured LAND-HEAD-3 spine_fishbone branches (unshared a/b, distance) through margins(): p model - measured mean -1.3 / min -8.4 ps TT, -1.2 / -8.6 FF; count-aligned worst model +198.2 / +236.2 vs measured +189.8 / +227.6 (model <= 8.6 ps optimistic; calib_derate.py). Geometry UNCHECKED: measured rib hops d 250-290 ps per ~708 um (353-410 ps/mm) vs v -> spine delay up to ~15 % optimistic, so VSCALE=1.15 is run as the pessimistic reading (v2_vs115 table in LOCALITY.md). HEAD partition map: the spine model gives on-feed U <= 1.12 ns (CA +317 / +337) but the 12 channel-loop off-feed ports at 6.1 ns (CA +47 / +119); the built feed closed those loops at one column node (U 2.43 ns, +190 / +228), which is what the tree proposer (merge the loop) and the hop reading (re-time the loop) model.

Hop modes (12.13c): every off-feed crossing (loop-closing or far) is re-timed as a hop chain along the feed-tree path, one fixed-latency landing per tree edge; only feed parent<->child crossings remain. Cost = extra landing cycles (bit-hops), reported per map.

| mode | best map | feed | worst TT / FF ps | <100 TT / FF | >=100 TT and FF |
|---|---|---|---|---|---|
| ring | v1_s3.5 | top | -325 / -202 | 365 / 211 | no |
| ca | v1_s3.5 | top | -325 / -202 | 365 / 211 | no |
| ring+hop | tree_s1.5c3 | dme | -288 / -177 | 237 / 214 | no |
| ca+hop | tree_s3.5c5 | fish | 206 / 247 | 0 / 0 | YES |
| static | v1_s3.5 | top | -325 / -202 | 365 / 211 | no |
| static+hop | tree_s1.5c3 | fish | -269 / -143 | 256 / 200 | no |

| map | feed | regions | max span mm | bit-mm inside | crossing ports | off-feed (loop) ports / pairs | worst unshared ns (on / off feed) | max tree hops | CURRENT RING TT/FF (<100) | COUNT-ALIGNED TT/FF (<100) | hop chains: n / max hops / extra bit-hops | RING+HOP TT/FF (<100) | CA+HOP TT/FF (<100) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c18quad | fwd | 4 | 28.40 | 86.2 % | 60 | 12 / 4 | 10.41 / 15.87 | 3 | -8125 / -6868 (60/60) | -884 / -650 (43/43) | 12 / 3 / 19880 | -8125 / -6868 (48/48) | -222 / -104 (31/31) |
| c18quad | spine | 4 | 28.40 | 86.2 % | 60 | 12 / 4 | 10.89 / 10.91 | 3 | -6117 / -5148 (60/60) | -556 / -381 (60/60) | 12 / 3 / 19880 | -6117 / -5148 (48/48) | -298 / -170 (48/48) |
| c18quad | fish | 4 | 28.40 | 86.2 % | 60 | 12 / 4 | 6.09 / 8.64 | 3 | -5205 / -4376 (60/60) | -357 / -217 (26/15) | 12 / 3 / 19880 | -5205 / -4376 (48/48) | 20 / 95 (14/3) |
| c18quad | dme | 4 | 28.40 | 86.2 % | 60 | 12 / 4 | 10.91 / 10.91 | 3 | -556 / -382 (60/60) | -556 / -382 (60/60) | 12 / 3 / 19880 | -426 / -285 (48/48) | -426 / -285 (48/48) |
| c18quad | top | 4 | 28.40 | 86.2 % | 60 | 60 / 10 | 0.00 / 9.57 | 2 | -376 / -239 (60/60) | -376 / -239 (60/60) | - | - | - |
| v1_s3.5 | fwd | 66 | 8.80 | 8.2 % | 527 | 96 / 62 | 3.78 / 15.01 | 12 | -13852 / -11748 (515/515) | -536 / -361 (58/37) | 96 / 12 / 165985 | -3329 / -2776 (431/431) | 168 / 212 (0/0) |
| v1_s3.5 | spine | 66 | 8.80 | 8.2 % | 527 | 96 / 62 | 4.18 / 8.81 | 12 | -5585 / -4692 (443/395) | -374 / -231 (29/17) | 96 / 12 / 165985 | -2859 / -2373 (347/305) | 134 / 187 (0/0) |
| v1_s3.5 | fish | 66 | 8.80 | 8.2 % | 527 | 96 / 62 | 3.24 / 8.46 | 12 | -5563 / -4674 (413/365) | -345 / -207 (15/9) | 96 / 12 / 165985 | -2772 / -2301 (317/275) | 207 / 248 (0/0) |
| v1_s3.5 | dme | 66 | 8.80 | 8.2 % | 527 | 96 / 62 | 10.02 / 10.02 | 12 | -483 / -321 (317/292) | -483 / -321 (317/292) | 96 / 12 / 165985 | -298 / -184 (221/198) | -298 / -184 (221/198) |
| v1_s3.5 | top | 66 | 8.80 | 8.2 % | 527 | 527 / 180 | 0.00 / 9.57 | 2 | -325 / -202 (365/211) | -325 / -202 (365/211) | - | - | - |
| tree_s2c3.5 | fwd | 82 | 8.80 | 1.4 % | 611 | 110 / 69 | 3.54 / 15.89 | 13 | -14778 / -12538 (601/601) | -584 / -401 (51/37) | 110 / 13 / 236403 | -3329 / -2776 (501/501) | 199 / 242 (0/0) |
| tree_s2c3.5 | spine | 82 | 8.80 | 1.4 % | 611 | 110 / 69 | 4.18 / 8.81 | 13 | -5585 / -4692 (511/448) | -374 / -231 (29/13) | 110 / 13 / 236403 | -2859 / -2373 (417/354) | 134 / 187 (0/0) |
| tree_s2c3.5 | fish | 82 | 8.80 | 1.4 % | 611 | 110 / 69 | 2.99 / 8.46 | 13 | -5563 / -4674 (480/434) | -345 / -207 (15/9) | 110 / 13 / 236403 | -2768 / -2297 (370/324) | 226 / 264 (0/0) |
| tree_s2c3.5 | dme | 82 | 8.80 | 1.4 % | 611 | 110 / 69 | 10.02 / 10.02 | 13 | -483 / -321 (355/318) | -483 / -321 (355/318) | 110 / 13 / 236403 | -291 / -180 (245/214) | -291 / -180 (245/214) |
| tree_s2c3.5 | top | 82 | 8.80 | 1.4 % | 611 | 611 / 216 | 0.00 / 9.70 | 2 | -334 / -209 (352/234) | -334 / -209 (352/234) | - | - | - |
| tree_s3.5c5 | fwd | 63 | 8.80 | 9.0 % | 519 | 84 / 52 | 4.33 / 15.49 | 12 | -14364 / -12184 (510/509) | -582 / -398 (57/34) | 84 / 12 / 158962 | -3329 / -2776 (435/435) | 131 / 184 (0/0) |
| tree_s3.5c5 | spine | 63 | 8.80 | 9.0 % | 519 | 84 / 52 | 4.18 / 9.31 | 12 | -6235 / -5246 (432/383) | -408 / -258 (32/18) | 84 / 12 / 158962 | -2859 / -2373 (351/302) | 134 / 187 (0/0) |
| tree_s3.5c5 | fish | 63 | 8.80 | 9.0 % | 519 | 84 / 52 | 3.24 / 9.03 | 12 | -6213 / -5228 (402/360) | -378 / -234 (13/9) | 84 / 12 / 158962 | -2772 / -2301 (321/279) | 206 / 247 (0/0) |
| tree_s3.5c5 | dme | 63 | 8.80 | 9.0 % | 519 | 84 / 52 | 10.02 / 10.02 | 12 | -492 / -328 (306/292) | -492 / -328 (306/292) | 84 / 12 / 158962 | -298 / -185 (222/209) | -298 / -185 (222/209) |
| tree_s3.5c5 | top | 63 | 8.80 | 9.0 % | 519 | 519 / 165 | 0.00 / 9.57 | 2 | -325 / -202 (365/215) | -325 / -202 (365/215) | - | - | - |
| tree_s1.5c3 | fwd | 88 | 8.80 | 0.0 % | 631 | 116 / 75 | 3.54 / 15.89 | 14 | -14778 / -12538 (613/613) | -584 / -401 (55/37) | 116 / 14 / 260961 | -3329 / -2776 (515/515) | 199 / 242 (0/0) |
| tree_s1.5c3 | spine | 88 | 8.80 | 0.0 % | 631 | 116 / 75 | 4.18 / 8.81 | 14 | -5585 / -4692 (521/438) | -374 / -231 (33/15) | 116 / 14 / 260961 | -2859 / -2373 (421/338) | 134 / 187 (0/0) |
| tree_s1.5c3 | fish | 88 | 8.80 | 0.0 % | 631 | 116 / 75 | 2.99 / 8.46 | 14 | -5563 / -4674 (470/424) | -345 / -207 (19/9) | 116 / 14 / 260961 | -2768 / -2297 (354/308) | 226 / 264 (0/0) |
| tree_s1.5c3 | dme | 88 | 8.80 | 0.0 % | 631 | 116 / 75 | 10.02 / 10.02 | 14 | -483 / -321 (353/328) | -483 / -321 (353/328) | 116 / 14 / 260961 | -288 / -177 (237/214) | -288 / -178 (237/214) |
| tree_s1.5c3 | top | 88 | 8.80 | 0.0 % | 631 | 631 / 234 | 0.00 / 9.70 | 2 | -334 / -209 (352/234) | -334 / -209 (352/234) | - | - | - |

Worst crossings, best ring (v1_s3.5 / top, current ring: phase-dependent, the nominal d counts): R062->R063 2456 b OFF-feed hops 2, unshared 9.57 ns, d 0, p 742/618, margin -325/-202; R063->R062 2048 b OFF-feed hops 2, unshared 9.57 ns, d 0, p 742/618, margin -325/-202; R063->R062 2048 b OFF-feed hops 2, unshared 9.57 ns, d 0, p 742/618, margin -325/-202; R010->R028 2628 b OFF-feed hops 2, unshared 9.57 ns, d 0, p 721/603, margin -304/-186; R028->R010 2816 b OFF-feed hops 2, unshared 9.57 ns, d 0, p 721/603, margin -304/-186
  Render: hbm_v2_best_ring.png
Worst crossings, best ca (v1_s3.5 / top, count-aligned: nominal d absorbed by the ring count, only the derated variation counts): R062->R063 2456 b OFF-feed hops 2, unshared 9.57 ns, d 0, p 742/618, margin -325/-202; R063->R062 2048 b OFF-feed hops 2, unshared 9.57 ns, d 0, p 742/618, margin -325/-202; R063->R062 2048 b OFF-feed hops 2, unshared 9.57 ns, d 0, p 742/618, margin -325/-202; R010->R028 2628 b OFF-feed hops 2, unshared 9.57 ns, d 0, p 721/603, margin -304/-186; R028->R010 2816 b OFF-feed hops 2, unshared 9.57 ns, d 0, p 721/603, margin -304/-186
  Render: hbm_v2_best_ca.png
Worst crossings, best ring+hop (tree_s1.5c3 / dme, current ring, off-feed crossings re-timed as hop chains along the feed tree (12.13c)): T067->T046 1719 b on-feed hops 1, unshared 10.02 ns, d 0, p 704/594, margin -288/-177; T046->T067 1615 b on-feed hops 1, unshared 10.02 ns, d 0, p 704/594, margin -288/-177; T067->T046 514 b on-feed hops 1, unshared 10.02 ns, d 0, p 704/594, margin -288/-177; T067->T046 268 b on-feed hops 1, unshared 10.02 ns, d 0, p 704/594, margin -288/-177; T046->T067 22 b on-feed hops 1, unshared 10.02 ns, d 0, p 704/594, margin -288/-177
  Hop cost: 116 off-feed crossings become chains, max 14 tree hops, 260961 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: hbm_v2_best_ring+hop.png
Worst crossings, best ca+hop (tree_s3.5c5 / fish, count-aligned, off-feed crossings re-timed as hop chains along the feed tree (12.13c)): T047->T053 173 b on-feed hops 1, unshared 3.24 ns, d 2976, p 210/169, margin 206/247; T007->T000 1615 b on-feed hops 1, unshared 3.24 ns, d 2979, p 210/169, margin 207/248; T009->T006 1615 b on-feed hops 1, unshared 3.24 ns, d 2979, p 210/169, margin 207/248; T007->T000 173 b on-feed hops 1, unshared 3.24 ns, d 2979, p 210/169, margin 207/248; T009->T006 173 b on-feed hops 1, unshared 3.24 ns, d 2979, p 210/169, margin 207/248
  Hop cost: 84 off-feed crossings become chains, max 12 tree hops, 158962 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: hbm_v2_best_ca+hop.png
Worst crossings, best static (v1_s3.5 / top, static count: one whole-cycle k per crossing for TT and FF (no reset-time training)): R062->R063 2456 b OFF-feed hops 2, unshared 9.57 ns, d 0, p 742/618, margin -325/-202; R063->R062 2048 b OFF-feed hops 2, unshared 9.57 ns, d 0, p 742/618, margin -325/-202; R063->R062 2048 b OFF-feed hops 2, unshared 9.57 ns, d 0, p 742/618, margin -325/-202; R010->R028 2628 b OFF-feed hops 2, unshared 9.57 ns, d 0, p 721/603, margin -304/-186; R028->R010 2816 b OFF-feed hops 2, unshared 9.57 ns, d 0, p 721/603, margin -304/-186
  Render: hbm_v2_best_static.png
Worst crossings, best static+hop (tree_s1.5c3 / fish, static count + hop chains): T086->T085 2456 b on-feed hops 1, unshared 2.99 ns, d 2993, p 191/153, margin -269/202; T085->T086 2048 b on-feed hops 1, unshared 2.99 ns, d -2993, p 191/153, margin -269/202; T085->T086 2048 b on-feed hops 1, unshared 2.99 ns, d -2993, p 191/153, margin -269/202; T018->T000 1615 b on-feed hops 1, unshared 2.96 ns, d 2964, p 186/150, margin -235/230; T031->T006 1615 b on-feed hops 1, unshared 2.96 ns, d 2964, p 186/150, margin -235/230
  Hop cost: 116 off-feed crossings become chains, max 14 tree hops, 260961 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: hbm_v2_best_static+hop.png

Tree proposer log (start -> end: loop-closing bits, loop pairs, regions): tree_s2c3.5: 73785 b/45 p/84 r -> 65295 b/43 p/82 r; tree_s3.5c5: 53089 b/38 p/66 r -> 46538 b/32 p/63 r; tree_s1.5c3: 73785 b/47 p/88 r -> 73785 b/47 p/88 r

Verdict rule (12.14b): build only a map/feed whose estimated margin is >= 100 ps TT and FF on every crossing in the ring mode that will be built. Every number here is an ESTIMATE (UNCHECKED) until a GRT + landed_phase_ocv run.
