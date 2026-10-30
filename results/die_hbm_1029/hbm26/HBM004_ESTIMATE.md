# HBM-004 estimate (DIE-HBM-26, 2026-10-29 ~21:00 PDT) — 92 UNPLANNED pairs, 82,285 b, plan d25b + g4

All numbers are plan arithmetic / bind counts. Bind counts CHECKED (full-cap probe of the d25b+g4 strict bind:
92 errors, 82,285 b, unplanned_bit_list uncapped). Face capacities, hop counts and tok/s are UNCHECKED estimates.
Per-pair table: `hbm004_classes.json` (driver family, sink, gap, planned bits, lane_add verdict).

## Classes (both halves; NE = NW mirror)

| class | pairs | bits | what | fix kind |
|---|---|---|---|---|
| SPLIT | 28 | 40,547 | one source family scattered over non-adjacent partitions: scorer hb_idx__s_{NE,NW} over b100/b101/b102/b103 (up to 11.9 mm apart), SFU core sfucore over b110/b111/b112/b113 (up to 12.8 mm), SU3 slice su30<->su31 (1.15 mm, b110/b100 between) | MAP / RE-HOME (12.13): make the family contiguous |
| WIDEN | 19 | 24,078 | pair has plan lanes but the as-built is wider: hub->su00/su20 (+2,846 each, pgp command 1,904 b + vmb/sucore), su00/su20->hub (+1,207), hub<->hub (+2,775/+2,730), NW_hub->root (+2,065), sm*->hub (+37) — the folded r18h5 census took max over folded quadrants while the as-built half carries both quadrant instances (q0 S role + q1 N role) | widen existing lanes (same cycles, 0 tok/s) where the face has room |
| NEW | 40 | 16,066 | links the plan never had: sfup/sfus hub<->b113/b111 (2,277/693/160), sfucore ctl b113<->su11/su20/su31 (596/516 x3), coll<->EP hub<->spb0 (632/615), scorer SE tail b002->root 297, small fault/obs/fl 1-9 b | lane add (hop chains) or re-home |
| REMAP | 5 | 1,594 | the plan HAS an unused lane of the same family/width at another partition: b103->root 297 vs unused L64m b101->root 297; root->b000 180 vs unused L80m root->b101 171; b111->hub 410 vs unused L81m b110->hub 161 | map fix (put the leaf where the plan lane ends) |

## Variant A built (lane_add.py on d25b, near 1200 um, locality default) — CHECKED
built 2 pairs / 2,798 b (su31->su30 1,399 x2 via abutting chain), FAR 79 / 54,498 b (not laned by 12.13), FAILED 11
(no free face window: su30|b100, b010|su00, su21|hub, NW_hub|root; no macro-free 6-station chain hub->su20; cycle
mismatch 15 vs existing 8 for su00->hub). Not adopted: closes 2 of 92. Report `lane_add_A_near1200_report.json`.
Variant B (near 4000 um, max-hops 8) DONE (CHECKED): built the same 2 pairs / 2,798 b (out sha d67c2f065cbd = A), FAR 51 / 34,932 b, FAILED 39 (no macro-free station chain / no free window). Widening reach does not help: hop chains are blocked by macros and full faces.

## Face capacity (6 pins/um plan budget, existing ports counted) — UNCHECKED arithmetic
| face | edge um | cap | used | WIDEN add | verdict |
|---|---|---|---|---|---|
| NE_hub\|NE_su01 (hub<->su00 chain) | 760.3 | 4,562 | 4,187 | +4,053 | 1.8x over |
| NE_hub\|NE_su21 (hub<->su20 chain) | 976.3 | 5,858 | 5,516 | +4,053 | 1.6x over |
| NW_hub\|root | 4,320 | 25,920 | 20,240 | +2,065 (+5,505 hub<->hub if via root) | fits alone; 1.07x over with hub<->hub |
| NE_hub\|root | 4,320 | 25,920 | 12,085 | +5,505 | fits |
| NE_su30\|NE_b100 (su30->su31 chain) | 1,555 | 9,331 | 6,468 | +3,356 | 1.05x over |
So the SU WIDEN pairs cannot be closed by lanes on the d25b floorplan: su00/su20 do not touch the hub and the
only hub faces toward them (via su01/su21) are 760/976 um. The 1,904-b pgp command (101 sinks/bit) per SU is the
largest single item.

## Recommendation (2 parallel fix variants, both a plan event; tok/s UNCHECKED)
* V-RP (re-plan, locality first): reorder the S/N rows so b100..b103 and b110..b113 are contiguous (scorer and SFU
  core become abutting blocks -> SPLIT 40.5k b become ADJ 2-cycle lanes on 1,555-um faces), and give su00/su20 a
  direct hub face (swap su00<->su01, su20<->su21) for the WIDEN + pgp command bits. Cost: one re-plan event,
  re-run G0/G0C, re-bind; latency: ADJ lanes = the 2 boundary flops bind already gives an UNPLANNED direct pair, so
  0 added cycles vs today's bind view.
* V-MAP (no floorplan move): REMAP the 5 pairs onto the unused plan lanes; map su_NE3 slice into one of su30/su31
  (removes 4,755 b/half if the cut moves); keep SFU/scorer far pairs as hop chains (~405 um/hop: scorer b100->b102
  8.9 mm ~ 22 cycles, SFU ctl b113->su31 13.3 mm ~ 33 cycles) -> tok/s risk on the index/SFU loops, needs the
  token model before adoption.
Default if no COORD answer in 30 min: V-RP estimate first (row order + face arithmetic), V-MAP REMAP part built in
parallel (small, map-only).
