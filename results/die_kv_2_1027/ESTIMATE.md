# DIE-KV-2 12.14b ESTIMATE: KV locality clock form, count-aligned crossings (analytic, UNCHECKED)

Written BEFORE the build. Plan hm_r26q9 (sha256 90b72bc2..), v = 321 ps/mm TT (LAND-KV-1 measured trunk), T = 833 ps.
Tool: est_ca.py = main locality.py v2 score() (shared derate: clk_aocv g021 + droop regions + core-lat class) ->
per crossing derated lag interval as the UNION over TT and FF (one K for both corners) -> MESO-COUNT-1
count_align_plan.plan() (start tree, K, DEPTH 4/8, ap = T/8 = 104.1 ps, wander 5 % of unshared).
Margin definition = COORD 20:35 ruling (b): L inside [(0.5T+ap), (DEPTH-0.5)T-ap]; lo = L_lo - 0.5T, hi = (DEPTH-0.5)T - L_hi
(L_lo/L_hi already carry ap), gate >= 100 ps both sides. The low side sits at ap = 104.1 by construction of K.

## 1. Delay x span x derate
- 128-group map: region span <= 2.16 mm, fishbone region insertion <= ~0.7 ns; feed edge = centre -> tap -> centre.
- Feed along links (fish): worst UNSHARED clock on a feed-edge crossing 1.07 ns (land128) / 1.55 (c3500) / 2.85 (tree35);
  off-feed (loop) crossings 8.1-10.6 ns (they share only down to a far feed ancestor).
- Derate on 10 ns unshared: OCV (0.21 %/mm AOCV + class shares) ~5-8 % (~500-800 ps) + TT->FF shift of nominal d
  (~15 % of d) -> derated lag spread up to ~2.4 ns on the worst off-feed crossings + start-tree whole-cycle ambiguity.
- DEPTH 4 window for the spread = 3T - 2ap = 2291 ps; DEPTH 8 = 7T - 2ap = 5623 ps.

## 2. Crossing fit (count-aligned, per map x feed)
| map | regions | crossings | bits across | bits inside | feed | unshared on/off ns | D4 / D8 / FAIL | worst hi margin (fit) | old ring worst TT/FF |
|---|---|---|---|---|---|---|---|---|---|
| land128 (LAND-KV-1) | 128 | 3595 | 519,111 | 13.4 % | fish | 1.07 / 9.11 | 3563 / 32 / 0 | +105.9 | -6224 / -5239 |
| c3500 (LAND-KV-2, 51) | 51 | 1901 | 262,672 | 56.2 % | fish | 1.55 / 10.56 | 1643 / 119 / **139** | +173.8 | -10353 / -8765 |
| c3500 | 51 | 1901 | 262,672 | 56.2 % | top (die tree) | 0 / 6.41 | 1356 / 545 / 0 | +816.8 | -76 / +5 |
| **tree35 (proposer v2, 40)** | 40 | 1659 | 237,934 | 60.3 % | **fish** | 2.85 / 8.13 | 1493 / 166 / **0** | **+117.1** | -3511 / -2931 |
| tree35 | 40 | 1659 | 237,934 | 60.3 % | spine | 3.14 / 8.58 | 1022 / 590 / 47 | +120.2 | |
- The 51-region c3500 map with a link feed FAILS 139 crossings (no DEPTH fits: start-tree path ambiguity up to 5 cycles on
  10.6 ns off-feed loops). The tree-constrained proposer map tree35 (LOCALITY-SCORE-2 propose_tree 3.5/5 mm, main
  d1037e4d41) closes the worst loops: 0 FAIL, 1493 D4 + 166 D8, worst hi +117.1, lo +104.1 -> PASSES the >=100 gate (est).
- vs the 128-group map: crossings 3595 -> 1659 (-54 %), bits 519,111 -> 237,934 (-54 %).
- A die-wide top tree also fits CA (margins +762..+835) but 12.13 stops die-wide release clocks; it is the fallback only.

## 3. Tracks
- locality tracks(): 0 region faces over the 8 b/um face supply on all maps (feed legs are M8/M9 clock, not signal tracks).
- Clock: rep 250 um (COORD 20:25 default), BUFx24, M8/M9; feed wire ~ sum of centre->tap->centre legs (reported by the kit).

## 4. Verdict
BUILD tree35 + link_fishbone feed (die_trial --tree-form link_fishbone, new opt-in), rep 250, site-slide, on hm_r26q9
composed with the tree35 landed table. Gate after build: die GRT0 incl clock TT+FF (50 it), count_align_plan on the
measured landed_phase_ocv rows (lo/hi >= 100 both sides), die STA related pairs inside regions (main die_sta_related,
droop class derate, HB4 hold). Caveats: (i) CA counts assume reset-time count training (LOCALITY-SCORE-2 ASK, MESO-COUNT-1
PDR proof ~22:24); (ii) region span 4.72 mm > 3.5 mm -> intra-region skew is larger (die STA shows it);
(iii) logical latency per crossing (K+1+n0) is not priced here (MESO-INTEG-1 owns the schedule/TOK pricing).

## 5. MEASURED (built after the estimate; CHECKED-own, UNCHECKED-indep) -- 2026-10-27 21:16 PDT
Kits: die_trial --tree-form link_fishbone --rep-um 250 --tree-site-legal --tree-site-slide on raw hm_r26q9 (no ring compose),
data intel1:/srv/opentallas-scratch2/claude/die-kv-2-1027 (smoke_q9 = tree35 S35, kit_s35m = merged 37-region, kit_l128 = land128).
- Die GRT incl clock (mk_combo_kv, M4-M7 signal, M8/M9 clock, 50 congestion iterations), TT and FF: overflow 0 on M1-M9 for all
  three; usage M4-M7 4.4-4.8 %, M8 1.57 %, M9 0.60 %. Each kit has ONE clock net with slew ~760 ps > 320 (slid-root leg type);
  the slid-root fix (f3f619b72d, merged into die-kv-2) is not yet re-run on these kits.
- Count-aligned margins on MEASURED landed_phase_ocv rows (count_align_plan, cross-region ports relabelled to regions):
| map | regions | crossings | D4/D8/FAIL | worst lo/hi | max path amb |
|---|---|---|---|---|---|
| tree35 (S35) | 40 | 1659 | 1460/164/**35** | 104.1/131.9 | 6 cycles |
| tree35 merged (S35M) | 37 | 1624 | 1363/203/**58** | 104.1/116.6 | 5 |
| **land128 (L128)** | 128 | 3595 | 3505/90/**0** | **104.1/138.7** | 1 |
  The estimate's tree35 0-FAIL did not hold on measured rows (path ambiguity 4-6 cycles on 8.9 ns unshared loops);
  land128 PASSES the CA gate (>=100 both sides). LOCALITY-SCORE-3 (main 808791c932) also scores land128/fish as its only 0-FAIL KV map.
- Die STA related pairs (main die_sta_related, cppr-lca, clock-ocv table, shared droop + droop regions, HB4), MODELLED clock:
| map | intra TT setup / FF hold / skew | intra HB4 cells -> TT | seam TT / FF hold | seam HB4 cells -> TT/FF |
|---|---|---|---|---|
| L128 | +49.4 / -538.4 / 567 ps | 19.9 M -> -26.0 (1 neg pair) | +189.7 / -408.9 | 14,370 -> +114.7 / +0.14 |
| S35 | -515.9 / -998.6 | 39.9 M -> -515.9 | -895.8 / -1312 | -- |
| S35M | -515.9 / -998.6 / 1122 ps | 40.0 M -> -515.9 | -963.5 / -1363 | 546 k -> -963.5 |
  Verdict: no form closes die STA inside regions. The link_fishbone region trees carry 567 ps (L128) to 1.1 ns (35-40 regions)
  intra-region skew: fishbone trunks are not balanced (no regional mesh / H-tree inside the region). Seam (crossing) pairs on
  L128 close with 14k HB4. Next structural step: region-internal balanced tree or regional mesh (METHODOLOGY v4.6 MSCTS form)
  under the link feed, NOT trims.
