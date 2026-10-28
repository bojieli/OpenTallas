# DIE-KV-3 12.14b ESTIMATE: balanced local H-tree inside each land128 region under the link feed (analytic, UNCHECKED)

Written BEFORE the build (COORD 21:38 CROSS-DIE NOTE: in-region spread <= ~150 ps with OCV + droop before any build).
Plan hm_r26q9b (c7f1723ad2, the KV working plan), map land128 (128 regions: 96 single-partition, 32 two-partition),
feed = locality feed 'fish' (DIE-KV-2 l128/feed_land128_fish.json), rep 250 um, T = 833 ps.
Tool: `est_htree.py` (this dir): geometry = the die_trial builder itself (`build_link_fishbone(local='htree', leaf_um)`,
no site slide); delay = stage model calibrated to the LAND-KV-1 measured trunk (321 ps/mm at rep 250: 20 ps/stage +
wire); OCV = main `clk_aocv.branch_pessimism` with the APPROVED g021 table (FF hold: capture late + launch early) on the
branches below each pair's LCA; droop: both taps in one clock region = one droop region -> 0 (shared rule, 12.4a b1).
Pairs: every ordered tap pair inside one partition (die STA 'intra') and inside one region (seam pairs of 2-part regions).

## Results (hold-side spread = skew + OCV, worst pair of the die)
| local form | leaf um | buffers (nodes+reps) | clock wire mm (feed / region / last-mile) | in-region insertion max / p50 ps | intra spread ps | region-pair spread ps | regions > 150 ps |
|---|---|---|---|---|---|---|---|
| fishbone (DIE-KV-2) | - | 5,289 (2,931+2,358) | 1,021 (190 / 830 / 0.1) | 594 / 393 | **412** (measured 567) | 328 | 120 |
| H-tree | 100 | 13,799 | 1,511 (190 / 1,321 / 133) | 729 / 520 | 47.8 | 42.6 | 0 |
| H-tree | 150 | 12,855 | 1,482 (190 / 1,291 / 145) | 678 / 520 | 50.0 | 41.9 | 0 |
| **H-tree** | **200** | **9,959 (8,421+1,538)** | **1,352 (190 / 1,162 / 256)** | **678 / 470** | **55.3** | **41.7** | **0** |
| H-tree | 300 | 9,015 | 1,293 (190 / 1,103 / 294) | 627 / 470 | 66.1 | 46.0 | 0 |
- Calibration: the same model gives 412 ps on the fishbone where the routed die STA measured 567 ps (x1.38: GRT RC,
  slew, budget core-latency tolerance). Scaled, the leaf-200 H-tree is ~76 ps, inside the ~150 ps target with 2x room.
- Worst regions are the 24-tap pv_N_* (2.16 x 1.52 mm): nominal skew 12 ps (last-mile legs only), the rest is OCV on
  ~0.6 ns of unshared insertion (both branches split at the region root).
- Per-region insertion (region root -> tap, TT): p10/p50/p90/max 470/470/637/678 ps (est_h200_per_region.json).
- Cost vs fishbone: +4.7k buffers (BUFx24), +330 mm of M8/M9 clock wire (+32 %); DIE-KV-2 M8 1.57 % / M9 0.60 % usage
  -> ~2.1 % / 0.8 % (tracks: ample).
- CA crossings: tree-edge crossings still share the clock down to the parent region centre; the unshared part grows by
  the H-tree insertion (~0.47-0.68 ns per side vs 0.13-0.59 fishbone) -> lag intervals widen by OCV on ~+0.3 ns
  (~+15-25 ps); DIE-KV-2 measured hi >= 138.7 -> expect ~115-125 (>= 100). Measured after the build.

## Verdict
BUILD die_trial --tree-form link_htree (new opt-in, general) --leaf-um 200 --rep-um 250 --tree-site-legal --tree-site-slide
on hm_r26q9b + land128 + fish feed. Gates after build: die GRT0 incl clock TT+FF (50 it, critical 0), CA on measured
rows (MESO-INTEG-1 K convention), die STA related pairs (main die_sta_related, droop, HB4).
