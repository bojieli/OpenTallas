# HBM bank-block ladder plan delta (DIE-LAYOUT-HBM, 2026-11-11, DO_NOT_COUNT)

COORD ruling 11-11: the 2x4 ladder REDESIGN is approved with no growth. Build the plan delta with these parts: outlines and positions, ring stations -> 0 with latency kept by lat pads, then EQ, G0 and one die GRT probe.

- Base: `c2aff36a6ca5` (HBM plan of record t10 + the DIE-LAYOUT-HBM positions-only delta).
- New plan: `280ef01a6fc9` = `ladder_delta_c13.json.gz` applied to the base. Rebuild it with `scripts/ladder_delta.py apply BASE die_plan.json`; the result is byte-identical (sha checked).
- Generator: `scripts/ladder.py TOOLS PLAN_DIR scripts/specC6.json OUT`.
- **On t11** (DIE-HBM-100 post-cut `584df6bfcfc2` = d46a + d6_hubdrop + d8_cells_q_spt1 + d7 dl): t11 differs from `c2aff36a6ca5` only in 3 partition types (q_hub_ne, q_hub_nw, q_spt1), and the ladder touches none of them. The same delta applied to t11 gives **`5957a416a762`**. G0 on t11 goes from 621 to 537, with the same class counts as below; the diff is in `tables/g0_t11_ladder_vs_t11.txt`.

## Form (variant C of the 2x4 ladder)
- **b000 is unchanged.** It keeps its full-height 457.92 um column on the hub face. The hub face, the b000 type and every hub window are byte-identical.
- **Top row:** b001 b002 b003, height 1840.32 (NE) / 1788.48 (NW).
- **Bottom row:** b010 b011 b012 b013, height 2479.68 (NE) / 2531.52 (NW).
- **Bank block:** same 4492.80 x 4320 block, with no growth. All seams are on the 8.64 grid, and no neighbour window straddles a seam.
- **Why not the strict 2x4:** the b000|b010 seam would need >= 1478-1671 um at 6 pins/um for its 26.2 kb hub-ring traffic, but only 855-1097 um is available. b000 therefore stays a column, and both b001 and b010 abut it.
- **Ring links:** every ring link (hub-b000-b001-b002-b003-b013-b012-b011-b010-b000-hub, plus b001-b011 and b010-b001) is now an abutted seam. These links now cross no neighbour column.
- **Type reshapes:** 14 bank types are reshaped (outlines are in `ladder_report.json` types). Hard cores were re-packed on shelves with 17-35 um streets (`scripts/pack.py`). Every core fits, and core sizes are unchanged.
- **Dips:** 20 dips were re-laned straight between neighbours, removing slots that only dipped into a bank. NE: L5011-14, L5076, L5080, L5083, L5086-88, L5092-94. NW: L1211-14, L1278, L1280, L1281.

## Stations and latency
- **Bank FT slots:** 414 -> 271.
- **Bank station flops:** 1,095k -> 528k (NE 498k -> 273k, NW 597k -> 255k).
- **Station model:** each crossed slot is solved under the check.py model. S0 is the input pin site. Every input bit reaches S1 within 405, as does each later hop. Stations are >= ceil(route/405).
- **Latency kept by lat pads:** lane `fixed_cycles` = old natural - new natural. This is 110 lanes, 876 pad cycles and 602k pad bits, landed at the face by the bind. The table is regenerated with schema `lane_latency` for the touched lanes only. Untouched lanes keep their entries, including the 4 pre-existing table/plan mismatches L12s/L12ms/L96/L96m.
- **Latency up:** 16 lanes, 8.5 kb. Each has a longer bank route than in the old plan, and in several the old route violated the S0 reach rule.

| lane | bits | cycles before -> after |
|---|---|---|
| L166m | 3332 | 2 -> 5 |
| L8300 | 1615 | 20 -> 21 |
| L5064 | 1091 | 22 -> 23 |
| L5060 | 749 | 31 -> 35 |
| L5056 | 516 | 21 -> 26 |
| L3001 | 499 | 35 -> 41 |
| L5054 | 317 | 20 -> 25 |
| L3002 | 267 | 31 -> 43 |
| L5089 | 74 | 43 -> 44 |
| L187 / L187m | 35 each | 2 -> 4 |
| L732 | 4 | 12 -> 18 |
| L732m | 4 | 12 -> 15 |
| L733 / L733m | 3 each | 10 -> 12 |
| L205 | 1 | 9 -> 10 |

## Gates (all vs base c2aff36a6ca5)
- **G0 (tools d54b96cc27):** 624 -> 537 errors. The new-vs-base message diff is in `tables/g0_new_vs_base_t10.txt`.

  | class | before | after |
  |---|---|---|
  | faces | 171 | 139 |
  | stations | 155 | 119 |
  | hops | 118 | 98 |
  | layers | 84 | 81 |
  | cuts | 13 | 17 |

  clock, geometry, latency, m89 and core_pin_form are equal.

  This is **not 0 new**:
  - **Cuts** (13 -> 17 lines): 11 new cut lines at 0.63-0.81, all in bank segments: NW_b001 x4, NE_b001 x2, NW_b010 x3, NE_b010 x1, NE_b011 x1. Some base lines are gone: b000 drops from 9 lines at 0.61-0.96 to 4 (NE only, 0.64-0.77), and both NW_b103 lines disappear. This vertical travel is structural. About 6-7 kb enters b001 from su00/b113 on its N face and must reach the hub-window heights, so it crosses either b000 or b001 (the base put all of it in b000). A cut-load-aware router (`lgeom.route seg_pen`) spreads it. The worst line is 0.81 (NW_b001 y 10250). The worst base line was 0.96 (NE_b000).
  - **Faces:** the b000 east edges are at 6.6/um in 4 windows. The same faces in the base were at 12.4-12.7/um. The b000 east face carries 26.2 kb (NE) / 26.0 kb (NW) on 4320 um, which is 6.06/um and over the 6/um budget in any geometry. A type face budget (`face_pins_per_um` with its G2 proof) is the only clean fix.
  - **Renamed pre-existing errors:** the remaining new-message groups were renamed by the rebuilt port ids and slot names: L7500 M9 layer/m89 rows, L3003/L8300m first-hop rows, and dense neighbour windows now reported on the new bank face names.
- **EQ (`tables/lane_eq.txt`):**
  - 422 = 422 lanes, with every launch and capture end (part.bus) and every width unchanged.
  - latency_groups are byte-identical, and no non-bank partition moved.
  - Table cycles are unchanged except the 16 latency-up lanes above.
  - Non-bank types change only on the dip re-sites: q_b103, q_su00/01 (+ physical_v1) and q_su20__physical_v1.
- **station_lint:** 195 -> 59 flagged chains. 0 new, and 0 left on bank types (the base had 136 on q_b001/b010/b000/b002).
- **Explorer die:** hop>reach 109 -> 93, with 0 newly over. bit-mm 820,081 -> 711,740 (-13%). Bypasses 0 -> 0.
- **route_supply p99 per bank type:**

  | type | before | after |
  |---|---|---|
  | q_b001 | 5.16 | 2.28 |
  | q_b001__physical_v1 | 5.54 | 3.68 |
  | q_b002 | 5.77 | 2.04 |
  | q_b002__physical_v1 | 5.84 | 2.55 |
  | q_b003 | 9.01 | 2.83 |
  | q_b003__physical_v1 | 8.88 | 3.04 |
  | q_b010 | 11.75 | 1.95 |
  | q_b010__physical_v1 | 11.74 | 3.04 |
  | q_b011 | 4.99 | 1.93 |
  | q_b011__physical_v1 | 4.99 | 2.45 |
  | q_b012 | 4.73 | 1.49 |
  | q_b012__physical_v1 | 4.77 | 1.83 |
  | q_b013 | 5.01 | 2.08 |
  | q_b013__physical_v1 | 5.01 | 1.29 |
  | q_b000__physical_v1 | 3.97 | 3.54 |
  | q_b000 | 4.15 | **4.91 (worse)** |

  q_b000 is worse in its face region, from the denser b000 east windows. All bank types are still above 0.8, as they were in the base.
- **Die GRT on abstracts** (die_trial kit, M4-M9, one probe per arm, ot-run epyc2, DO_NOT_COUNT; the arms are base c2aff36a6ca5 and ladder 280ef01a6fc9):
  - Overflow is 0 in both arms, and the ladder converges faster (4 extra iterations vs 9).
  - Wirelength: 833.7M -> 729.2M um (-12.5%).
  - Routed nets: 493,510 -> 401,631 (fewer station-hop nets).
  - Usage: 7.71% -> 7.12% overall, and 17.2% -> 15.2% on M7.
  - The full congestion tables are in `tables/die_grt.txt`.

## Views
- `views/ladder_before_after_banks.png`: NE/NW bank blocks before and after, showing partitions, hard cores and FT slot routes.
- `views/explorer_die_before.png` and `views/explorer_die_after.png`: explorer die view.
