# FALLBACK-S81-2 2026-10-26: S81 G=2 landed-region fallback, no-early-tap re-price -> v5.0 early-tap re-price, band room, latency regen, region trees (all numbers UNCHECKED unless marked)

Base: claude/fallback-s81-1026@0773aa1237. Input plan: PATH-S81 B2 g0fix (epyc1 path-s81-taps-1026/src/.../die_plan_phyfit_g0fix.json).
Run data: epyc1:/srv/opentallas-scratch2/claude/fallback-s81-2-1026/ (plans 125 MB, kits, not committed).

## 1. Price (compose_tok_ds, base 784.9 AR / 2,749.3 MTP per user)

`tools/die_plan/fallback_regions.py --core {early,land,rebuild,tap}` (new flag; default `early` = old behaviour).
With land/rebuild/tap every partition is std class, so G=2 gives 168 regions, 1,199 landed ports / 571,217 bits, 587 lanes.

| core mode | meaning | lane table | AR | MTP |
|---|---|---|---|---|
| land (COORD 17:49, WITHDRAWN 18:4x) | every legacy core port landed +3 (450 lanes, +2,361 cycles) | plan-regen | 757.6 (-3.48 %) | 2,660.3 (-3.24 %) |
| land | | fallback_regions face | 758.9 (-3.31 %) | 2,664.5 (-3.08 %) |
| **tap (v5.0 18:4x) = rebuild** | die CTS taps each legacy core early by its signed-view insertion; only cross-region ports land | **plan-regen** | **766.4 (-2.36 %)** | **2,689.5 (-2.18 %)** |
| tap = rebuild | | fallback_regions face / fwd | 767.7 (-2.19 %) / 773.9 (-1.40 %) | 2,693.8 (-2.02 %) / 2,714.1 (-1.28 %) |

- "plan-regen" = the composed plan's own regenerated latency table (gen.py latency): +4,083 lane cycles vs the
  fallback_regions face estimate +3,597 (175 lanes differ; compose counts the real landed network). Use plan-regen.
- Finding for `land`: landing a legacy core port also needs the core changed (sink-side ring inside the core, or a core
  clock export for the forwarded clock), so `land` was never core-rebuild-free.
- AOCV delta of v5.0 early taps (clk_aocv table b0c11ff91, g = 0.21 %/mm, class-B stages = insertion / 36.2 ps,
  0.3 mm core span, shared droop, FF = TT x 202.5/250): unshared core-internal pessimism per core<->partition pair
  rom_elem 552: 17.4 TT setup / 12.7 FF hold (+6.4 / +4.6 vs a 250-ps core); bf_col 645: 18.8 / 13.9 (+7.7 / +5.8);
  bk_sel 430: 14.9 / 10.8 (+3.9 / +2.7); gunit 520: 16.9 / 12.3 (+5.8 / +4.2) ps. MODEL, UNCHECKED.

## 2. Ring storage-band placement: 126 -> 60, band-room delta for the 60

- `clock_landing_plan._storage_band`: when the face-strip and compact-bank searches find nothing, an exhaustive
  macro-free grid scan (same legality: outline margin, obstacles, every corner <= 403 um from the bus pin, same area)
  runs. Byte-identical where a band was already found. Offline on the old plan: 65/126 fixed.
- Recomposed on the 168-region table: 60 FAILs remain (compose_r1.log, placement_failures_r1.json).
- These 60 have no macro-free room near the face. Top-down delta (band_delta_r1.json): 22 types / 36 faces need a
  face strip of 21.6-38.9 um (each band behind its own window). Types: 15 svc (2 x 1.44 x 2.45 mm), 8 slice C,
  bk_sel, one col.
- NOT applied: an outline strip shifts the abutted lattice (row/column cut + port windows) and is a S81 die-plan
  change for the plan owner (12.9a) as one PLAN-DELTA. Die headroom to reticle is about +1.05 mm x / +1.26 mm y.

## 3. Latency table regenerated -> G0 = only the 24 base errors (CHECKED: message-set equality with g0fix base)

- gen.py latency --inplace on the composed plan. Main schema gap fixed: latency.lanes allows `clock_landing`, which
  schema.lane_latency / gen.py already emit. Before the fix all 587 rows were schema errors.
- Plan dir = symlinks to the PATH-S81 src plan dir inputs (plandir/).

## 4. Region local trees (die_trial --region-trees, opt-in)

- A die reference tree (same bisection) reaches one root per region (bbox centre). Below it, a full-depth equal-depth
  local tree (leaf 300 um) feeds every partition entry. Combined with --htree-full-depth --tree-site-legal (FALLBACK-HEAD).
- No-early-tap kit (kit/, superseded by v5.0): 168 regions, 7,887 entries, 30,787 cells, 0 illegal sites. Region depth
  6-10 levels below the region root, all region roots at level 15.
- v5.0 kit (kit_tap/): adds the early core taps as tree leaves. die_trial's ctree does not model the early-by-insertion
  offset: the macro latency is a die-STA annotation, and the GRT geometry is the same.
- Renders: kit*/tree_regions.png (viewed). Black = reference tree, blue = local trees, red = region roots.
