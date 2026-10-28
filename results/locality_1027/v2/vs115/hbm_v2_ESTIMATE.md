# 12.14b ESTIMATE v2: hbm region map / clock feed / crossings (LOCALITY-SCORE-2, analytic, UNCHECKED)

Inputs: plan /srv/opentallas-scratch2/claude/hbm-streets2-1027/c18/die_plan.json (sha256 6a711a87b7e7), 88 partitions, 631 ports; v = 391 ps/mm TT; P = 833 ps, budget P/2 = 416.5 ps.
Feeds: fwd = neighbour-forwarded from a parent LEAF (H-tree regions); spine = one spine along the max-bit spanning tree of the region adjacency (through every region centre; H-tree region trees hang off it); fish = the same spine + fishbone region trees (long-axis spine + ribs, leaf delay = Manhattan distance); dme = the spine made zero-skew (DME pads at the spine nodes: nominal d = 0, unshared = height of the last common spine node; LAND-HEAD-3's balanced spine form); top = one balanced die H-tree. Maps: given, v1 = connectivity greedy (span cap), tree_sXcY = proposer v2 (start span X mm, crossing graph made a tree by merge/re-cut up to cap Y mm).
Modes: CURRENT RING = landed_phase_ocv margin with the nominal d (phase-dependent); COUNT-ALIGNED = budget - max(p_up, p_dn), nominal d absorbed by the ring count (ASSUMED definition = LAND-HEAD-3's reading, pending the MESO-COUNT-1 window verdict; it re-centres d per corner, i.e. it ASSUMES the ring count is trained at reset at the operating PVT); STATIC COUNT = one whole-cycle k per crossing for TT and FF (= FOLD: the corner-to-corner shift of d stays in the window). Derate: clk_aocv g021 + droop regions + core latency class B (shared model).

Calibration: derate CHECKED: the 427 measured LAND-HEAD-3 spine_fishbone branches (unshared a/b, distance) through margins(): p model - measured mean -1.3 / min -8.4 ps TT, -1.2 / -8.6 FF; count-aligned worst model +198.2 / +236.2 vs measured +189.8 / +227.6 (model <= 8.6 ps optimistic; calib_derate.py). Geometry UNCHECKED: measured rib hops d 250-290 ps per ~708 um (353-410 ps/mm) vs v -> spine delay up to ~15 % optimistic, so VSCALE=1.15 is run as the pessimistic reading (v2_vs115 table in LOCALITY.md). HEAD partition map: the spine model gives on-feed U <= 1.12 ns (CA +317 / +337) but the 12 channel-loop off-feed ports at 6.1 ns (CA +47 / +119); the built feed closed those loops at one column node (U 2.43 ns, +190 / +228), which is what the tree proposer (merge the loop) and the hop reading (re-time the loop) model.

Hop modes (12.13c): every off-feed crossing (loop-closing or far) is re-timed as a hop chain along the feed-tree path, one fixed-latency landing per tree edge; only feed parent<->child crossings remain. Cost = extra landing cycles (bit-hops), reported per map.

| mode | best map | feed | worst TT / FF ps | <100 TT / FF | >=100 TT and FF |
|---|---|---|---|---|---|
| ring | tree_s3.5c5 | top | -424 / -285 | 383 / 285 | no |
| ca | tree_s3.5c5 | top | -424 / -285 | 383 / 285 | no |
| ring+hop | tree_s1.5c3 | dme | -382 / -257 | 267 / 225 | no |
| ca+hop | tree_s3.5c5 | fish | 181 / 227 | 0 / 0 | YES |
| static | tree_s3.5c5 | top | -424 / -285 | 383 / 285 | no |
| static+hop | v1_s3.5 | fish | -240 / -264 | 188 / 175 | no |

| map | feed | regions | max span mm | bit-mm inside | crossing ports | off-feed (loop) ports / pairs | worst unshared ns (on / off feed) | max tree hops | CURRENT RING TT/FF (<100) | COUNT-ALIGNED TT/FF (<100) | hop chains: n / max hops / extra bit-hops | RING+HOP TT/FF (<100) | CA+HOP TT/FF (<100) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c18quad | fwd | 4 | 28.40 | 86.2 % | 60 | 12 / 4 | 11.97 / 18.25 | 3 | -9398 / -7954 (60/60) | -1064 / -798 (52/43) | 12 / 3 / 19880 | -9398 / -7954 (48/48) | -307 / -174 (40/31) |
| c18quad | spine | 4 | 28.40 | 86.2 % | 60 | 12 / 4 | 12.52 / 12.54 | 3 | -7087 / -5975 (60/60) | -688 / -491 (60/60) | 12 / 3 / 19880 | -7087 / -5975 (48/48) | -394 / -250 (48/48) |
| c18quad | fish | 4 | 28.40 | 86.2 % | 60 | 12 / 4 | 7.00 / 9.93 | 3 | -6041 / -5089 (60/60) | -461 / -302 (52/26) | 12 / 3 / 19880 | -6041 / -5089 (48/48) | -30 / 54 (40/14) |
| c18quad | dme | 4 | 28.40 | 86.2 % | 60 | 12 / 4 | 12.54 / 12.54 | 3 | -689 / -491 (60/60) | -689 / -491 (60/60) | 12 / 3 / 19880 | -539 / -381 (48/48) | -539 / -381 (48/48) |
| c18quad | top | 4 | 28.40 | 86.2 % | 60 | 60 / 10 | 0.00 / 11.00 | 2 | -482 / -327 (60/60) | -482 / -327 (60/60) | - | - | - |
| v1_s3.5 | fwd | 66 | 8.80 | 8.2 % | 527 | 96 / 62 | 4.35 / 17.26 | 12 | -15982 / -13565 (523/515) | -666 / -468 (60/39) | 96 / 12 / 165985 | -3883 / -3249 (431/431) | 138 / 187 (0/0) |
| v1_s3.5 | spine | 66 | 8.80 | 8.2 % | 527 | 96 / 62 | 4.81 / 10.14 | 12 | -6475 / -5451 (487/423) | -480 / -318 (48/29) | 96 / 12 / 165985 | -3342 / -2786 (391/327) | 100 / 159 (0/0) |
| v1_s3.5 | fish | 66 | 8.80 | 8.2 % | 527 | 96 / 62 | 3.73 / 9.73 | 12 | -6449 / -5429 (413/387) | -447 / -291 (31/11) | 96 / 12 / 165985 | -3244 / -2703 (317/297) | 182 / 228 (0/0) |
| v1_s3.5 | dme | 66 | 8.80 | 8.2 % | 527 | 96 / 62 | 11.53 / 11.53 | 12 | -605 / -422 (347/305) | -605 / -422 (347/305) | 96 / 12 / 165985 | -393 / -265 (251/209) | -393 / -265 (251/209) |
| v1_s3.5 | top | 66 | 8.80 | 8.2 % | 527 | 527 / 180 | 0.00 / 11.00 | 2 | -424 / -285 (389/285) | -424 / -285 (389/285) | - | - | - |
| tree_s2c3.5 | fwd | 82 | 8.80 | 1.4 % | 611 | 110 / 69 | 4.07 / 18.27 | 13 | -17046 / -14473 (605/601) | -721 / -513 (66/49) | 110 / 13 / 236403 | -3883 / -3249 (501/501) | 174 / 221 (0/0) |
| tree_s2c3.5 | spine | 82 | 8.80 | 1.4 % | 611 | 110 / 69 | 4.81 / 10.14 | 13 | -6475 / -5451 (571/491) | -480 / -318 (45/29) | 110 / 13 / 236403 | -3342 / -2786 (461/397) | 100 / 159 (0/0) |
| tree_s2c3.5 | fish | 82 | 8.80 | 1.4 % | 611 | 110 / 69 | 3.44 / 9.73 | 13 | -6449 / -5429 (497/456) | -447 / -291 (31/11) | 110 / 13 / 236403 | -3239 / -2699 (387/346) | 204 / 246 (0/0) |
| tree_s2c3.5 | dme | 82 | 8.80 | 1.4 % | 611 | 110 / 69 | 11.53 / 11.53 | 13 | -605 / -422 (391/331) | -605 / -422 (391/331) | 110 / 13 / 236403 | -385 / -260 (281/225) | -385 / -260 (281/225) |
| tree_s2c3.5 | top | 82 | 8.80 | 1.4 % | 611 | 611 / 216 | 0.00 / 11.15 | 2 | -434 / -293 (435/278) | -434 / -294 (435/278) | - | - | - |
| tree_s3.5c5 | fwd | 63 | 8.80 | 9.0 % | 519 | 84 / 52 | 4.98 / 17.81 | 12 | -16570 / -14066 (515/510) | -719 / -510 (63/37) | 84 / 12 / 158962 | -3883 / -3249 (435/435) | 96 / 156 (1/0) |
| tree_s3.5c5 | spine | 63 | 8.80 | 9.0 % | 519 | 84 / 52 | 4.81 / 10.71 | 12 | -7222 / -6087 (479/405) | -518 / -350 (47/31) | 84 / 12 / 158962 | -3342 / -2786 (395/324) | 100 / 159 (0/0) |
| tree_s3.5c5 | fish | 63 | 8.80 | 9.0 % | 519 | 84 / 52 | 3.73 / 10.38 | 12 | -7196 / -6066 (402/382) | -485 / -322 (29/12) | 84 / 12 / 158962 | -3244 / -2703 (321/301) | 181 / 227 (0/0) |
| tree_s3.5c5 | dme | 63 | 8.80 | 9.0 % | 519 | 84 / 52 | 11.53 / 11.53 | 12 | -615 / -429 (342/300) | -615 / -429 (342/300) | 84 / 12 / 158962 | -393 / -266 (258/216) | -393 / -266 (258/216) |
| tree_s3.5c5 | top | 63 | 8.80 | 9.0 % | 519 | 519 / 165 | 0.00 / 11.00 | 2 | -424 / -285 (383/285) | -424 / -285 (383/285) | - | - | - |
| tree_s1.5c3 | fwd | 88 | 8.80 | 0.0 % | 631 | 116 / 75 | 4.07 / 18.27 | 14 | -17046 / -14473 (625/613) | -721 / -513 (70/49) | 116 / 14 / 260961 | -3883 / -3249 (515/515) | 174 / 221 (0/0) |
| tree_s1.5c3 | spine | 88 | 8.80 | 0.0 % | 631 | 116 / 75 | 4.81 / 10.14 | 14 | -6475 / -5451 (569/493) | -480 / -318 (49/33) | 116 / 14 / 260961 | -3342 / -2786 (465/393) | 100 / 159 (0/0) |
| tree_s1.5c3 | fish | 88 | 8.80 | 0.0 % | 631 | 116 / 75 | 3.44 / 9.73 | 14 | -6449 / -5429 (507/446) | -447 / -291 (31/11) | 116 / 14 / 260961 | -3239 / -2699 (391/330) | 204 / 246 (0/0) |
| tree_s1.5c3 | dme | 88 | 8.80 | 0.0 % | 631 | 116 / 75 | 11.53 / 11.53 | 14 | -605 / -422 (383/341) | -605 / -422 (383/341) | 116 / 14 / 260961 | -382 / -257 (267/225) | -382 / -257 (267/225) |
| tree_s1.5c3 | top | 88 | 8.80 | 0.0 % | 631 | 631 / 234 | 0.00 / 11.15 | 2 | -434 / -293 (435/278) | -434 / -294 (435/278) | - | - | - |

Worst crossings, best ring (tree_s3.5c5 / top, current ring: phase-dependent, the nominal d counts): T059->T060 2456 b OFF-feed hops 2, unshared 11.00 ns, d 0, p 840/701, margin -424/-285; T060->T059 2048 b OFF-feed hops 2, unshared 11.00 ns, d 0, p 840/701, margin -424/-285; T060->T059 2048 b OFF-feed hops 2, unshared 11.00 ns, d 0, p 840/701, margin -424/-285; T010->T028 2628 b OFF-feed hops 2, unshared 11.00 ns, d -0, p 816/683, margin -400/-267; T028->T010 2816 b OFF-feed hops 2, unshared 11.00 ns, d 0, p 816/683, margin -400/-267
  Render: hbm_v2_best_ring.png
Worst crossings, best ca (tree_s3.5c5 / top, count-aligned: nominal d absorbed by the ring count, only the derated variation counts): T059->T060 2456 b OFF-feed hops 2, unshared 11.00 ns, d 0, p 840/701, margin -424/-285; T060->T059 2048 b OFF-feed hops 2, unshared 11.00 ns, d 0, p 840/701, margin -424/-285; T060->T059 2048 b OFF-feed hops 2, unshared 11.00 ns, d 0, p 840/701, margin -424/-285; T010->T028 2628 b OFF-feed hops 2, unshared 11.00 ns, d -0, p 816/683, margin -400/-267; T028->T010 2816 b OFF-feed hops 2, unshared 11.00 ns, d 0, p 816/683, margin -400/-267
  Render: hbm_v2_best_ca.png
Worst crossings, best ring+hop (tree_s1.5c3 / dme, current ring, off-feed crossings re-timed as hop chains along the feed tree (12.13c)): T067->T046 1719 b on-feed hops 1, unshared 11.53 ns, d 0, p 798/674, margin -382/-257; T046->T067 1615 b on-feed hops 1, unshared 11.53 ns, d 0, p 798/674, margin -382/-257; T067->T046 514 b on-feed hops 1, unshared 11.53 ns, d 0, p 798/674, margin -382/-257; T067->T046 268 b on-feed hops 1, unshared 11.53 ns, d 0, p 798/674, margin -382/-257; T046->T067 22 b on-feed hops 1, unshared 11.53 ns, d 0, p 798/674, margin -382/-257
  Hop cost: 116 off-feed crossings become chains, max 14 tree hops, 260961 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: hbm_v2_best_ring+hop.png
Worst crossings, best ca+hop (tree_s3.5c5 / fish, count-aligned, off-feed crossings re-timed as hop chains along the feed tree (12.13c)): T047->T053 173 b on-feed hops 1, unshared 3.73 ns, d 3422, p 235/190, margin 181/227; T007->T000 1615 b on-feed hops 1, unshared 3.73 ns, d 3426, p 235/189, margin 182/228; T009->T006 1615 b on-feed hops 1, unshared 3.73 ns, d 3426, p 235/189, margin 182/228; T007->T000 173 b on-feed hops 1, unshared 3.73 ns, d 3426, p 235/189, margin 182/228; T009->T006 173 b on-feed hops 1, unshared 3.73 ns, d 3426, p 235/189, margin 182/228
  Hop cost: 84 off-feed crossings become chains, max 12 tree hops, 158962 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: hbm_v2_best_ca+hop.png
Worst crossings, best static (tree_s3.5c5 / top, static count: one whole-cycle k per crossing for TT and FF (no reset-time training)): T059->T060 2456 b OFF-feed hops 2, unshared 11.00 ns, d 0, p 840/701, margin -424/-285; T060->T059 2048 b OFF-feed hops 2, unshared 11.00 ns, d 0, p 840/701, margin -424/-285; T060->T059 2048 b OFF-feed hops 2, unshared 11.00 ns, d 0, p 840/701, margin -424/-285; T010->T028 2628 b OFF-feed hops 2, unshared 11.00 ns, d -0, p 816/683, margin -400/-267; T028->T010 2816 b OFF-feed hops 2, unshared 11.00 ns, d 0, p 816/683, margin -400/-267
  Render: hbm_v2_best_static.png
Worst crossings, best static+hop (v1_s3.5 / fish, static count + hop chains): R010->R028 2628 b on-feed hops 1, unshared 3.21 ns, d 3213, p 201/161, margin 184/-264; R028->R010 2816 b on-feed hops 1, unshared 3.21 ns, d -3213, p 201/161, margin 184/-264; R010->R028 2816 b on-feed hops 1, unshared 3.21 ns, d 3213, p 201/161, margin 184/-264; R028->R010 2456 b on-feed hops 1, unshared 3.21 ns, d -3213, p 201/161, margin 184/-264; R028->R010 1171 b on-feed hops 1, unshared 3.21 ns, d -3213, p 201/161, margin 184/-264
  Hop cost: 96 off-feed crossings become chains, max 12 tree hops, 165985 extra bit-hops (each extra hop = one more landing cycle on that path; price it in the die's token model)
  Render: hbm_v2_best_static+hop.png

Tree proposer log (start -> end: loop-closing bits, loop pairs, regions): tree_s2c3.5: 73785 b/45 p/84 r -> 65295 b/43 p/82 r; tree_s3.5c5: 53089 b/38 p/66 r -> 46538 b/32 p/63 r; tree_s1.5c3: 73785 b/47 p/88 r -> 73785 b/47 p/88 r

Verdict rule (12.14b): build only a map/feed whose estimated margin is >= 100 ps TT and FF on every crossing in the ring mode that will be built. Every number here is an ESTIMATE (UNCHECKED) until a GRT + landed_phase_ocv run.
