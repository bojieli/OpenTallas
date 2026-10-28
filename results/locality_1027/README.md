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
