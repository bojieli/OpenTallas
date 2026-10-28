# 12.14b ESTIMATE: HBM throughput-weighted region map + latency hiding (DIE-HBM-3, 2026-10-27 22:4x PDT)

This is an analytic page only: no region or clock build. **CHECKED** means I ran the tool myself. **UNCHECKED** marks model numbers. Nothing here has had a NUMBER-CHECK. The plan is C20e (`intel2:/srv/opentallas-scratch2/claude/die-hbm-1027/c20e`). Data is in `intel2:/srv/opentallas-scratch2/claude/die-hbm-1027/region3/`. The scripts are in this folder.

## (2) HBM clock wire speed
- **Source:** the built HBM die clock tree R15-F2 (`intel1:/srv/opentallas-scratch2/claude/path-hbm-r15-1026/runF2/mesh_b`):
  - die_clock_mesh H-tree, BUFx24 repeaters, M8/M9 with a 2W NDR (0.16/0.08);
  - combined die GRT, 50 iterations;
  - arrivals taken from its `tree_TT/FF.txt`.
- **Method:** the same as the HEAD measurement (LAND-HEAD-1 sl300). For every driver→load tree net longer than 200 µm, I took the arrival difference over the Manhattan length. Script: `wirespeed.py`.
- **Result (CHECKED):**
  - TT: 1,980 segments, median **210.1 ps/mm**, aggregate **209.1 ps/mm** (p10 175.6, p90 266.0). Repeater-to-repeater only: 175.3.
  - FF: 171.5 / 168.8 ps/mm.
- **Caveat:**
  - The arrivals in this run come from the planner's native SPEF (`die_clock_128.py`) on the pre-routed fixed clock wires, not from `estimate_parasitics -global_routing`. HEAD's 335/349 used GRT-RC with default-width wires.
  - The native SPEF has R = 2.74e-3 kΩ/µm and C = 0.1215 fF/µm (median over 1,744 two-pin nets, CHECKED). The ASAP7 setRC values for a 2W M8/M9 wire are R ≈ 4.34e-3 and C ≈ 0.128 (with the combo's ×1.3).
  - So the native R is about 0.63× the 2W value. My attempt to re-time the tree on rescaled SPEF crashed: OpenSTA/OpenROAD segfault right after `read_spef`, 3 tries.
- **Wire speeds used:**
  - **219.6 ps/mm** = measured 209.1 × 1.05 spice (CHECKED measurement, optimistic RC).
  - **279 ps/mm** = analytic stage model (BUFx24, ~309 µm stages, 2W setRC R/C, +5.1 % via R per CLOCK.md 10-25, × 1.05). UNCHECKED. This is my primary number.
  - **366.4 ps/mm** = the HEAD default-width value × 1.05, kept as the pessimistic bound (DIE-HBM-2).

## (3) Throughput-weighted proposer
- **Lane weight (UNCHECKED model):**
  - Add +6 cycles to one lane, run `b1_lane_traversal.op_deltas`, and get the added cycles per op.
  - Multiply each op's added cycles by that op's ds_ar S2-schedule sensitivity: SU 956, COLL 469, SM/ATT 441, HC 159, DMA 50, IDX.TOPK 40, COLL.TOPK_MERGE 9, IDX 8 ds_ar cycles per op-cycle.
  - 69 of 230 lanes carry weight. The heaviest are L0/L24 (SU), then L4, L6, L137.
  - Output: `sens.json`.
- **Proposer:** `locality.propose` / `propose_tree` (main code, run through a patched copy) on a pair weight of bits + λ·(critical weight). λ = 10 × the die's total bits.
- **Span cap:** I used **half-perimeter (w+h)/2** as the legal span instead of max side.
  - Why: the HBM partitions are themselves larger than 3–4 mm. Bank columns are 4.32 mm tall, the hubs are 8.22 × 4.32 mm, SM is 5.8 × 4.5 mm (hard), and PHY_N is 8.8 × 2.1 mm (hard).
  - With a 3–4 mm max-side cap, nearly every partition stays alone. Only 1.4–12 % of the critical weight can ever lie inside a region, and the proposer only reaches 1.4–9 % (CHECKED, `critgeo.py`, `maps/`).
  - Half-perimeter is what sets the in-region insertion I = v·(w+h)/2.
- **Ring math:** count-aligned with the MESO-COUNT-2 parameters (`count_align_plan.py` @0af33ccde0: union of corners, directed start tree, sync aperture 26.5 ps).
  - Main's DSU is shimmed in.
  - Regions the directed start tree does not reach ("unreached") are counted as FAIL.

## Results (fish feed; feed choice and crossing classes are scored by the tool, CHECKED; tok/s UNCHECKED model)
| map | regions | crossings | D4/D8/FAIL @219.6 | @279 | @366.4 | worst lo/hi margin @279 | critical weight inside |
|---|---|---|---|---|---|---|---|
| **tok_l10_v1_c5** (best) | 34 | 327 | 315/8/4 | 292/31/4 | 218/102/7 | 117.8 / 141.4 | 63 % |
| tok_l10_v1_c4 | 38 | 363 | 349/10/4 | 350/9/4 | 282/74/7 | 131.8 / 142.1 | 54 % |
| tok_l10_tree_s3c6 | 44 | 397 | 385/8/4 | 373/20/4 | 315/75/7 | 129.2 / 142.1 | 47 % |
| DIE-HBM-2 t82 (control) | 82 | 609 | – | – | 584/25/0 @366 | – | 0 % |

- **The 4 FAIL at ≤279 ps/mm** are L117/L117m/L138/L138m: 26 bits in total, status links, "unreached" by the directed start tree. A reverse start-forward wire into those regions would fix them, so they are not a geometry failure.
- **At 366.4 ps/mm** there are 3 more FAILs: L8_5, L21_0, L22_0 (6.5 kb), the PHY_N ↔ mca/spt loop.

### TOK price, ds_ar (tok/s on planU3f = 1906 floor; UNCHECKED)
- **Control:** my pricer reproduces DIE-HBM-2 t82 at 1687.9 and the quad at 1888.5 (CHECKED).

| map @ v | no hiding | hide (landing = pipeline latency, unit not blocked) | hide + SX look-ahead (more records in flight) | qwen_ar loss (no hiding / hide) |
|---|---|---|---|---|
| **tok_l10_v1_c5 @279** | **1805.4 (−5.3 %)** | **1846.0 (−3.1 %)** | **1854.4 (−2.7 %)** | 1.11 % / 0.87 % |
| tok_l10_v1_c5 @219.6 | 1805.4 | 1846.2 | 1854.2 | 1.14 % / 0.88 % |
| tok_l10_v1_c5 @366.4 | 1790.7 | 1838.6 | 1847.6 | 1.29 % / 1.00 % |
| tok_l10_v1_c4 @279 | 1793.0 | 1837.8 | 1847.0 | |
| tok_l10_tree_s3c6 @279 | 1779.0 | 1826.9 | 1838.8 | |
| DIE-HBM-2 t82 (control) | 1687.9 | 1771.6 | 1790.4 | |
| quad (control, 12.13-rejected) | 1888.5 | 1892.2 | 1895.9 | |

- **Added cycles per op on the best map** (k1, compared with t82 in brackets): HC +6 (+64), COLL +13 (+59), SM/ATT +34 (+41), IDX.TOPK +25, IDX +22, COLL.TOPK_MERGE +16. SM stays high because each hard SM partition is its own region.

### In-region spread (UNCHECKED; balanced tree from the bbox centre)
- **Model:** spread = I·(5.11 % droop + 3 % nets + 0.21 %/mm·diag) + 20 ps.
- **Over the ≤~150 ps target:**
  - The **soft hub partitions alone, NW_hub/NE_hub (8.22 × 4.32 mm)**: 158 ps @219.6, 196 @279, 251 @366.4.
  - PHY_N (hard): 172 @279.
  - SM singles (hard): 159 @279.
- **Multi-partition soft regions:** max side 5.8 mm, worst R030 at 154 @279 and 125 @219.6.
- **Hard partitions** carry their own island clocks (12.2a1), so they are outside the die region tree. **The hubs must be split into ≥2 regions each.** That split adds in-hub crossings, which are not priced here.

## Verdict
1. **The best throughput-weighted map is tok_l10_v1_c5:** 34 regions, fish feed, 327 crossings.
   - At the primary 279 ps/mm: 0 geometry FAIL; 4 FAIL are unreached 26-bit status links, fixable with a start-forward wire; lo/hi margins 117.8/141.4.
   - **ds_ar: 1805 tok/s without hiding (−5.3 %), 1846 with hiding (−3.1 %), 1854 with hiding plus SX look-ahead (−2.7 %).**
   - This beats the 63- and 82-region maps by about 100–160 tok/s, but it is **still under the 1906 floor** in every variant.
2. **Latency hiding recovers 40–50 tok/s.** The rest is landing latency on true RAW dependency chains (SM x-load, IDX.TOPK → COLL merge). The S2 schedule cannot overlap those.
3. **The 12.13 span cap of ~3–4 mm cannot be met on HBM.** The partitions themselves are 4.3–8.8 mm, so I used half-perimeter ≤ 5 mm. The spread limit then fails only on the unsplit soft hubs.
4. **No build (12.14b).** Every passing map is 2.7–5.3 % under 1906. OWNER options are already batched by COORD (floor trade). The open choices are: accept about 1846–1854 tok/s with latency hiding, which needs a sequencer change (SX) and the landing-as-latency RTL contract; or accept the quad −1 % with a 12.13 exception, which COORD has rejected.
