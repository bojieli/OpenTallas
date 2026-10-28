# LOCALITY-SCORE-1 (2026-10-27): locality score + 12.14b ESTIMATE, all 5 dies

Tool: `tools/die_plan/locality.py` (+ `test_locality.py`, 11 tests). The model is in its docstring. Margins come from
`tools/s81_head/landed_phase_ocv.analyse`, which is reused unchanged from LAND-HEAD-2 be648cbdd7, with the
clk_aocv g021 table, regional droop and class-B core latency. Rerun: `bash results/locality_1027/run_all.sh` from the
repo root. Per die: `<die>_ESTIMATE.md` (one page), `<die>_<map>_<feed>.json/.png` and `*_crossings.json.gz`
(all rows), plus `<die>_traffic.json` (top 200 bit-mm pairs).

Feeds:
- top = one balanced die H-tree (the die-wide form that 12.13f stops)
- fwd = neighbour-forwarded max-bit spanning tree
- spt = neighbour-forwarded shortest-path tree

Readings:
- RAW = unfolded d
- FOLD = count-aligned d - kP
- PAD = whole-cycle padded forwarded hops

The gate stays the measured landed_phase_ocv >= 100 ps TT and FF.

Calibration (CHECKED against measured runs):
- HEAD part map, top feed: model -59.9 TT / +17.2 FF with 33 crossings < 100 ps. The LAND-HEAD-2 measured d=0 bound is
  -60.7 / +13.3 with 33 crossings < 100 ps.
- KV land128, top feed: model -52.5 / +23.7. The LAND-KV-1 measured bound is -136.4 / -47.1, so the model is ~85 ps
  optimistic there (the built tree has 7.2 ns unshared against the ideal 6.2 ns).

## Findings (ESTIMATE, UNCHECKED beyond the calibration)
1. No map passes 100/100 under any feed (all 5 dies, baseline and proposed).
2. top: the unshared clock is about 6 ns on every map, which gives about -50..-75 TT and +5..+30 FF. This confirms
   that the die-wide form cannot close.
3. fwd/spt: crossings ON the feed tree are short wherever regions are small (HEAD proposed: on-feed <= 1.9 ns). The
   killers are OFF-feed crossings: regions that are adjacent but not parent and child on the feed. Their last common
   point sits far up the forwarded chain (10-20 ns). So a forwarded feed needs a region map whose CROSSING GRAPH IS A
   TREE (chain or fishbone along the dataflow), as the QC slices are (0 off-feed).
4. PAD does not track PVT. A whole-cycle pad set at TT leaves an FF residual of about 14.5 % of the forwarded delay
   (QC slices: PAD TT +116 but FF -297). FOLD splits that residual, but needs the MESO-COUNT verdict.
5. QC slices: the slice tree is 26 mm tall (I = 3.0 ns), so on-feed unshared is 3.6 ns, giving FOLD -126/-238 and
   PAD +116/-297. The fix is a shorter slice clock (the QC-SLICECLK-3 spine column), not more regions.
6. HEAD proposed (85 regions, span <= 3 mm): fwd PAD -7 TT / -140 FF. Only 12 off-feed crossings fail. They sit at
   the column seams at x ~3.1 / 14.5 mm. This is the closest form of all 5 dies.
7. Tracks are not the limit. The worst boundary demand is <= 1.08x face supply (S81: 2 boundaries > 1). Every other
   die is <= 0.92x.

## v2 (LOCALITY-SCORE-2, 2026-10-27): tree-constrained proposer, spine/fishbone feeds, current-ring vs count-aligned

Rerun: `bash results/locality_1027/run_all_v2.sh` (VSCALE=1.15 OUT=... for the pessimistic spine delay). Per die:
`v2/<die>_v2_ESTIMATE.md` (one page), `v2/<die>_v2.json` (all map x feed rows + best per mode), `v2/<die>_v2_best_<mode>.png`
(renders, viewed), `v2/<die>_<map>_<feed>_v2_crossings.json.gz`, `v2/vs115/` (v x 1.15). CLI: `locality.py v2 --plan P --die D
--v-ps-mm V --map TAG=MAP --tree 2:3.5,3.5:5,1.5:3 --out DIR`.

New in the model (docstrings of `propose_tree`, `hop_delay`, `leaf_delay`, `fish_shared_um`, `dme_heights`, `hop_rows`):
- proposer v2 `propose_tree`: start from the v1 connectivity map and make the region CROSSING GRAPH the feed tree. The
  feed tree is the maximum-bit spanning tree of the region adjacency. Each loop-closing pair is merged (the pair, or else
  its whole fundamental cycle, absorbing clusters wholly inside the box, up to a cap), or one end partition is re-cut.
  A step is kept only if the loop-closing bits drop. Whatever remains is counted (off-feed).
- feeds `spine` (one spine through the region centres along the feed tree; H-tree regions hang off it at the centre),
  `fish` (the same spine + fishbone region trees: long-axis spine + ribs), `dme` (the spine made zero-skew: d = 0,
  unshared = height of the last common spine node; LAND-HEAD-3's balanced form), next to `fwd` and `top`.
- readings:
  - CURRENT RING (`raw`, the nominal d counts);
  - COUNT-ALIGNED (`ca` = P/2 - max(p_up, p_dn): LAND-HEAD-3's reading, ASSUMED until MESO-COUNT-1 posts the window).
    It re-centres d per corner, so it assumes the ring count is trained at reset at the operating PVT;
  - STATIC COUNT (`fold`: one k for TT and FF);
  - each of the three again with HOP chains (12.13c). Every off-feed crossing is re-timed along the feed-tree path, one
    landing per edge, so only parent<->child crossings remain. Cost = extra bit-hops / max hops (price it in tokens).

Calibration: the derate is CHECKED against LAND-HEAD-3's routed spine_fishbone (427 measured branches through
`margins()`, `calib_derate.py`): p is within -8.6..0 ps (model slightly optimistic); CA worst is +198/+236 in the model vs
+190/+228 measured. The geometry is UNCHECKED: measured rib hops run 353-410 ps/mm against v = 340, so the v x 1.15 run
is the pessimistic reading.

Best per die (ESTIMATE, UNCHECKED; worst TT/FF ps over all crossings; PASS = >= 100 TT and FF):

| die | current ring | count-aligned | count-aligned + hop chains | static count + hop | v x1.15: CA ; CA+hop |
|---|---|---|---|---|---|
| head | v1_s3.5/top -48/+28 | v1_s3.5/fish +140/+190 PASS | v1_s3.5/fish +309/+331 PASS (max 5 hops, 27,120 extra bit-hops) | +12/-34 | +106/+162 PASS ; +299/+322 PASS |
| qc | top -39/+36 | slices/fish +264/+292 PASS | same (0 off-feed) PASS | +45/-19 | +248/+279 PASS ; same |
| kv | land128/top -52/+24 | top -52/+24 (off-feed kills spine) | tree_s3.5c5/fish +218/+255 PASS (max 11 hops, 190,265 bit-hops) | +46/-17 | -113/-28 ; +195/+236 PASS |
| hbm | top -325/-202 | top -325/-202 | tree_s3.5c5/fish +206/+247 PASS (max 12 hops, 158,962 bit-hops) | -269/-143 | -424/-285 ; +181/+227 PASS |
| s81 | top -387/-256 | top -387/-256 | land179/fish +195/+238 PASS (max 19 hops, 306,970 bit-hops) | -197/-155 | -495/-347 ; +169/+217 PASS |

Findings:
1. CURRENT RING: no die reaches 100 TT under any map or feed. The best is the die-wide top tree (d = 0), and the balanced
   spine (dme) is worse because unshared = the height of the common node. This agrees with LAND-HEAD-3's <= ~+70 TT bound.
2. COUNT-ALIGNED + clock-follows-data (spine with fishbone regions) passes on HEAD and QC directly. KV, HBM and S81 pass
   only when their off-feed crossings become hop chains. That costs latency: up to 11 / 12 / 19 tree hops.
3. STATIC COUNT fails everywhere: the TT->FF shift of the nominal d (~15 % of d) does not fit the window. So the CA passes
   need reset-time count training (or a window that is not phase-centred). This is the MESO-COUNT-1 question.
4. The tree proposer cuts loop-closing bits by 12-83 % (QC tree_s3.5c5 7,226 -> 1,197 b). HEAD's 12 channel loops are
   longer than the 3.5-5 mm cap: the built feed closes them at one column node, and the hop reading re-times them.
5. Not scored here: intra-region related pairs. Big regions (QC 26 mm slices) carry their own root-split pessimism
   (QC-SLICECLK-2: 183 TT), and that goes to die STA. HBM region boxes can overlap where a region is L-shaped. The box rule
   checks only partition centres.

## v3 (LOCALITY-SCORE-3, 2026-10-27): the ADOPTED count-aligned ring at measured clock wire speeds

`python3 tools/die_plan/locality.py v3 ...` / `results/locality_1027/run_all_v3.sh` -> `v3/` (nominal v) and
`v3/vs115/` (v x 1.15, the measured LAND-HEAD-3 rib-hop pessimism).  Per die: `<die>_v3_ESTIMATE.md` (one page),
`<die>_v3.json`, `<die>_v3_crossings.tsv` (per crossing K-kind, L lo/hi, DEPTH, latency, margins), render
`<die>_v3_best_cap.png` (VIEWED; green = DEPTH4, orange = some DEPTH8, red = FAIL at DEPTH8).

Crossing form = MESO-COUNT-1 `ot_dp_clk_landing_ca` (COORD 20:35): reads by count, K and DEPTH 4/8 fixed per crossing
at design time for TT+FF jointly (no per-chip training), window (DEPTH-1)T, derated lag inside
[(0.5T+ap), (DEPTH-0.5)T-ap], ap = T/8.  The math is `tools/die_plan/count_align_plan.py` called unchanged through its
CLI entry (joint-corner union, Kruskal start tree, path ambiguity), per connected component; this tool only supplies the
modelled d / p_up / p_dn / unshared per crossing.  The v2 `ca` column (P/2 - max p) is SUPERSEDED.
Test: `test_cap_reproduces_meso_count_head3` = MESO-COUNT-1 HEAD result on the LAND-HEAD-3 rows
(`tools/die_plan/testdata/land_head3_sfbR_ocv_ttff.json.gz`): 427/427 DEPTH4, 0 FAIL, latency {2: 349, 3: 78},
worst 104.1 ps low side, coll_EN1_u__0 L [1065, 1432] lat 3.
Calibration: the modelled HEAD partition map with spine / fish feed also gives 427/427 DEPTH4 (built form measured
427/427 DEPTH4).

Latency: `phys` = ceil(lat + d_TT/T) = physical write->read cycles incl. RDREG, skew-free (sums around any closed
dataflow loop to the loop cost) -> the TOK pricing number.  `lat` = the schedule constant in the die-wide count
(K + 1 + origin difference); it carries d/T, so it can be <= 0 on one direction of a skewed pair.
Best = 12.13 first (no die-wide `top` feed; max region span <= max(5 mm, largest partition side)), then FAIL@D8,
max phys latency, phys bit-cycles, D8 count.

| die | v ps/mm | best map / feed | regions | crossings | DEPTH4 | DEPTH8 | FAIL@D8 (hop chains) | worst lo / hi ps | phys latency (cycles: crossings) | v x1.15 |
|---|---|---|---|---|---|---|---|---|---|---|
| HEAD | 349 | v1_s3.5 / fish | 85 | 162 | 162 | 0 | 0 | 104.1 / 1117 | {2: 37, 3: 125} | v1_s3.5/dme: 93 D4, 69 D8, 0 FAIL |
| QC | 199 | tree_s3.5c5 / fish | 136 | 1354 | 1354 | 0 | 0 | 104.1 / 1125 | {2: 52, 3: 1302} | 0 FAIL, 0 D8 |
| KV | 321 | land128 / fish | 128 | 3619 | 3357 | 262 | 0 | 104.1 / 189 | {2: 11, 3: 3510, 4: 44, 5: 54} | same form: 262 D8, 0 FAIL (hi 138) |
| HBM | 349 (not measured: highest measured die) | tree_s3.5c5 / fish | 63 | 519 | 499 | 20 | 0 | 104.1 / 134 | {2: 46, 3: 410, 4: 60, 5: 3} | v1_s3.5/fish: 55 D8, 0 FAIL (hi 121) |
| S81 | 335 | v1_s3.5 / fish | 210 | 1336 | 1297 | 39 | 0 | 104.1 / 188 | {2: 292, 3: 955, 4: 77, 5: 12} | no form with 0 FAIL: best 4 FAIL -> chains of 31 hops (impractical; re-cut instead) |

All numbers ESTIMATE (UNCHECKED) until GRT + landed_phase_ocv rows + count_align_plan on the real rows.  Not scored:
intra-region related pairs (die STA); HBM tree map region boxes overlap (box rule checks centres only).
