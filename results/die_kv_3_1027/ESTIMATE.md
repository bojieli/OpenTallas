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

## MEASURED (2026-10-27 22:17 PDT; intel1 run dir /srv/opentallas-scratch2/claude/die-kv-3-1027; files in measured/)
All builds: hm_r26q9b + land128 + feed_land128_fish, --rep-um 250, die GRT incl clock (M4-M7 signal, M8-M9 clock),
TT + FF, 50 congestion it, critical 0: overflow 0 on M1-M9 in every build (H200B: M8 1.6 % / M9 0.6 %), EXIT 0.
Die STA = main die_sta_related (shared model, clk_aocv g021 + shared droop). CA = landed_phase_ocv -> count_align_plan
+ count_align_bind (MESO-INTEG-1 convention, K_tree=-1-PAD), x1.00 and spice x1.05.

| build | tree | cells | clock wire mm | intra skew TT/FF ps | intra FF hold / kit-contract (W 80) | seam skew TT/FF | seam FF kit-contract | CA x1.00 FAIL, lo/hi | CA x1.05 FAIL |
|---|---|---|---|---|---|---|---|---|---|
| DIE-KV-2 fishbone | link_fishbone | 5,289 | 1,021 | 567 | -538 | - | - | 0, 104.3/138.7 | - |
| H200 | link_htree leaf 200, slide legalize | 10,482 | 1,631 | 505 / 432 | -479.7 | 230 / 198 | - | 0, 105.0/108.9 | - |
| **H200B** | **+ balance_legalize** | **10,537 (8,421 nodes + 2,116 reps)** | **1,709** | **98.6 / 86.3** | **-131.2 / -6.26 (12 pairs, need W 86.3)** | **169.7 / 146.3** | **-66.3 (323 pairs)** | **0, 113.0/143.5** | **7** |
| H200C | + level-uniform reps (reverted) | - | - | - / 88 | - | - / 151 | - | 0, -/107.0 | 19 |
| H200F | leaf 200 full (empty halves kept) | 27,916 | 3,582 | 113.1 / 99.1 | -144.9 / -19.1 (41) | 142.4 / 127.5 | -47.5 (203) | 0, 104.6/136.5 | 81 |
| H300F | leaf 300 full | 19,261 | 2,975 | 127.9 / 108.8 | -157.0 / -28.8 (36) | 109.2 / 97.3 | -17.3 (40) | 10 | 82 |

- Chosen: **H200B** (link_htree leaf 200 + balance_legalize). In-region spread with OCV + droop 98.6 ps TT / 86.3 FF
  (target <= ~150 met; estimate 55 x1.38 = 76 -> measured 86-99). FF intra hold -538 -> -131 raw; vs the 80 ps kit
  contract only 12 pairs short by <= 6.3 ps.
- Seam (2-part phy/pc regions): phy taps 70-150 ps earlier than pc taps (pruned sparse half = lighter load). Full trees
  (F) trade 2.6x cells / 2.1x wire for no net gain (balance_legalize leaves 689 unbalanced nodes on the full tree).
- HB4 to close at raw FF hold (plan delay model): intra 6.94 M cells (28,869 pairs), seam 145,650 cells (445 pairs).
  At the kit-contract window W=80: intra 12 pairs, seam 323 pairs.
- CA x1.00 (H200B): 3,595 crossings, D4 3,451 / D8 144 / FAIL 0, plan lo/hi 113.0/143.5; bind 0 identity/loop errors on
  3,468 fundamental cycles, 2000-chip MC 0 violations, sim min 113.0/143.6. x1.05: 7 FAIL (pv_S_0/1 <-> hgi_WS_0/1;
  start-tree path ambiguity 5, interval width 5.7 ns) -> bind fails closed.
- Render (viewed): measured/clock_tree_H200B.png: one H-tree per region, root at region centre, feed fish legs between
  region roots; diagonals in the PNG are node-to-node draw lines (routing is Manhattan in GRT).
