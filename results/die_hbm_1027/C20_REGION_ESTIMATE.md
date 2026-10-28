# 12.14b ESTIMATE: HBM region map priced against the 1906 tok/s floor (DIE-HBM-2, 2026-10-27 22:0x PDT)

Analytic page, written before any region or clock build. These are model numbers. CHECKED means I ran the tool myself; nothing here has had an independent NUMBER-CHECK.

## Inputs
- **Plan:** C20a `c9dbfc156c28`. The region form is the same on C20c and C20d: those deltas move no partitions and change no ports, apart from the two NE_b101 windows.
- **Clock wire speed:** v = 349 ps/mm × 1.05 = 366.4 ps/mm. The 349 is HEAD's measured value, because HBM has not been measured yet. The 1.05 is the spice scale from `opentools/mscts/data/asap7_bufx24_spice_cal.json` @285ba72636 (TT 1.0485, FF 1.0552). As a sensitivity case, v × 1.15 = 401.4 ps/mm.
- **Crossing model:** the adopted count-aligned ring, using `main tools/die_plan/locality.py v3` and `count_align_plan.py`, both unchanged. `est/one_map.py` scores a single named map with the fish feed.
- **Low-side margin:** the reported 104.1 ps is the pinned tree-crossing value (NUMBER-CHECK flaw), not a measured margin. It is UNCHECKED until MESO-COUNT-2 fixes K.
- **TOK model:** the TOK-HBM price chain, run on this plan's lane ledger:
  - `b1_lane_traversal.ledger` → `op_deltas` → `accepted_cost.hbm_schedule`, the same path as `path_hbm_r12/combine.py`.
  - Every crossing port adds its physical latency ceil(lat + d/T) = K+1 to its lane. This is the `k1` case.
  - The `k1-1` case assumes the ring replaces one existing boundary hop.
  - Crossings that fail even at DEPTH 8 are priced at 8 cycles, which is a lower bound.
- **Absolute tok/s:** 1.2e9 / (planU3f upper cycles + delta). planU3f upper is 1905.97 tok/s, the OWNER floor.
- **Script:** `est/price_landing.py`. Output: `est/price_maps.json`.

## Results (ds_ar; qwen_ar loss is under 2 % in every case)

| map (fish feed) | regions | crossings | D4/D8/FAIL@D8 @x1.05 | worst hi margin | FAIL@D8 @x1.15 | landing bit-cycles (k1) | ds_ar upper tok/s k1 / k1-1 | ds_ar lower tok/s k1 / k1-1 |
|---|---|---|---|---|---|---|---|---|
| tree_s3.5c5 (the 63-region map) | 63 | 519 | 466/44/**9** (12,168 b) | 128.9 | 0 | 1.53 M | **1701 / 1766** | 1759 / 1805 |
| tree_s2c3.5 | 82 | 609 | 584/25/0 | 113.6 | **3** | 1.62 M | **1688 / 1761** | 1759 / 1808 |
| c18 quad | 4 | 60 | 14/46/0 | 213.2 | 6 | 0.22 M | **1889 / 1892** | 1889 / 1892 |

## Breakdown of the cost
On the 63- and 82-region maps, every lane carries landing latency (230/230 lanes). The added cycles per op, k1 case:

| op family | added cycles |
|---|---|
| HC | +64 |
| COLL.TOPK_MERGE | +63 |
| COLL | +59 |
| SM/ATT | +41 |
| IDX.TOPK | +28 |
| SU | +11 |

On the quad map, landing latency reaches only the IDX, COLL and DMA families.

## Verdict
1. **The 63-region map fails on both counts at the spice-scaled speed.** Nine crossings fail even at DEPTH 8, and ds_ar drops to 1701–1766 tok/s, which is 7.4–10.8 % under the 1906 floor.
2. **No cheaper locality map passes.**
   - The 82-region map passes the margin check at x1.05 but fails 3 crossings at x1.15, and its throughput is worse (1688–1761 tok/s).
   - The quad has 0 FAIL and a 213 ps high margin, and it costs only −0.8 to −1.0 % (1889–1892 tok/s).
   - However, its 28.4 mm regions break the 12.13 span cap, and a die-wide clock inside each quadrant is exactly what 12.13 stops.
   - It is also still 14–17 tok/s under 1906, because planU3f already sits on the floor at 1905.97.
3. **The map form is fragile at this speed.** Which map passes flips between x1.05 and x1.15, so the HBM clock wire speed has to be measured before any map is frozen.
4. **No region or clock build.** Under 12.14b no map can be built today: every passing form is either under the floor or breaks 12.13.
5. **Cause:** fine-grained regions put a landing on every lane, and each landing costs 2–5 cycles. The schedule is static, so the critical HC/COLL/SM chains cross 5–10 regions in series.
6. **Possible ways forward (ASK):**
   - (a) A throughput-aware map: keep the HC, COLL and SM x-load chains inside regions, and land only off-critical lanes. This needs the proposer to take op-family weights.
   - (b) OWNER accepts a throughput floor below 1906 for the locality form.
   - (c) A 12.13 span exception for the quad at −1 %.
