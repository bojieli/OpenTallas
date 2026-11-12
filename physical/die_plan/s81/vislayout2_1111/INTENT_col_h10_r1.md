# INTENT: col_h10_r1 family, form JUNCTION-SLOT (VISLAYOUT2-S81/H10R1, 2026-11-12)

Types: col_h10_r1__t1__cl95b37463 (11 inst) and col_h10_r1__t1__cld01bb4ae (1 inst). The two share one floorplan: 89 hard cores
with identical positions. Outline 1442.88 x 1226.88 um, unchanged. Positions only: no cycle, port, RTL, outline, orient or core-shape change.

## Floorplan (y up)
| band | y (um) | contents |
|---|---|---|
| S bf group e5 | 17-216 | e5 root (bf_front_roots) + e5w / e5e views (bf_col3_c, 2 x bf16_half) |
| row-1 c band | 242-305 | c6 / c7 small-ROM rows, s6 / s7, t4, t4p (base), n13 |
| ROM row 1 | 337-558 | e6 (u_w x 43, u_e x 311), e7 (u_w x 605, u_e x 873); junctions at x 311 / 873 |
| row-2 c band | 579-656 | c8 / c9 rows, s8 / s9, t5, bn6 / bs6 / bs8 (base) |
| ROM row 2 | 691-913 | e8, e9 (same x as row 1) |
| top c band | 933-996 | c10 row, s10, t6, t6p, bn8 / bn9 |
| N bf group e10 | 1011-1210 | as e5 |

## Dataflow (core_conns, dump_links)
| Link | Bits | Ends |
|---|---|---|
| bs* -> both halves of its ROM pair | 2 x 2420 per bank | bank N face -> ROM S face xs_q pins (u_w local x 164-189, u_e 164-189) |
| frame_int_i1 (S, x 6-277) -> every ROM half | 605 per half (bus) | S window -> ROM S faces |
| bn* -> ROM N faces | 443 + 441 per bank | bank -> ROM N face |
| payload chain e5 -> t4p -> t5p -> t6p -> e10 | 536 per hop | S bf root N face -> stage payloads -> N bf root |
| s* <-> its ROM pair, c* <-> s* | 605 / 304; 30-42 | sequencer / small ROM |
| n14.fo -> n13 (1 FIRM station), n12 <-> n13, n13 <-> e10w.u_c | 71 / 33 / 63 | node tree |

## Defects seen (before)
- The base is unmeasured in real GRT. cl95b37463 is triage class U, with no routed DB. cld01bb4ae is class N, a flow
  failure: gen_lint INFRA, an unstarted ot-run waiter.
- The banks sit away from their junctions:
  - bs7 (e7) and bs9 (e9) are at x 1252.8, 380 um E of the x-873 junction. Their 4 x 2420-b fans run W along the
    32-um street under the ROM S faces and over the e7/e9 interiors. The ROM elem OBS covers M1-M5, so these are
    M6/M7 bits.
  - bs6 (e6) sits on the WRONG row, at y 648, under row 2. Its fans climb 300 um over the e6 interior.
  - bs8 sits 8.6 um under the e8 S face. The legaliser needs 31.2 um (pin-driven facing-face channel: bank N 604 +
    ROM pair S 1214 pins x 0.0171), so a plain re-legalise throws bs8 into the top band (734, 968).
- The payload chain detours via the E corner:
  - t4p and t5p sit at x 1123.
  - e5 -> t4p runs 732 um E.
  - t5p -> t6p runs 804 um diagonally across the e9 interior.
- bn7 sits at x 1123, 611 um from e7.u_w. bn8 sits at x 864, over e9, 844 um from e8.u_w.
- route_supply edge_outline (ring-bin fix): p99 0.983 (max 1.19, 13 hot bins, mstreet H M2 at (643, 92)). RUDY ovfH is
  4.94M and ovfV 1.64M. explorer bit-mm is 16732.
- A plain re-legalise of the base already fails for the e5 / e10 bf clusters ("no legal spot near its seed"). It moves 17 cores and costs +16 %
  bit-mm.

## Hand arrangement (seed_h10r1.py v1b)
1. JUNCTION SLOT in each c band: the banks sit in an x-slot of the c band, under their pair junction, 34.56 um below the
   ROM S face (>= the 31.2-um pin channel). This needs no vertical move of any ROM row.
   - bs6 (276.48, 276.48), bs7 (838.08, 276.48), bs8 (276.48, 630.72), bs9 (838.08, 630.72).
   - The slot is freed by compacting c*_0..4 to x 34.56-245.4 (43.2-um pitch on the 8.64 lattice), and by
     re-pitching the c7 / c9 rows around the slot, with s7 / s9 moving to x 907.2 just E of the bank.
2. PAYLOAD COLUMN in the e6|e7 / e8|e9 street (x 579-605):
   - t4p (552.96, 250.56) sits over the e5 root N face.
   - t5p (552.96, 604.8) is in the row-2 band.
   - t6p stays at (648, 933).
   - The 536-b chain now runs straight N through the street, not over the e9 interior. t4 / t5 move to x 371.52; c6_5 /
     c6_6 and c8_5 / c8_6 go to 466.56 / 509.76.
3. N-FACE BANKS:
   - bn6 and bn7 stack under bs8 / bs9 at y 604.8, just above the e6 / e7 N faces.
   - bn8 goes to (267.84, 933.12) over the e8 junction, with s10 at 345.6. bn9 goes to (838.08, 933.12) over the e9
     junction.
4. NODES:
   - n13 (648, 233.28) and n12 (699.84, 233.28) sit beside t4p in the row-1 band; n12 leaves its illegal bottom
     sliver.
   - n24, a 1-bit TYPE node that sat in the street, goes to the E strip (1313.28, 812.16).
   - The E corner, where bs7 / bs9 / t4p / t5p / bn7 were, is now free.
5. Legaliser (core_place --no-search on the seed) kept every seeded position. It nudged only e10w (-8.64), the e5 root
   (+8.64) and c9_0 / c9_1 (+-8.64). Taps: these types have grid taps only (no added_taps), so there are no tap moves.

## Scores (ready7 head 580d790a93c3 -> form v1b)
| type | before (verdict/region/dir/p99/max/hot) | after |
|---|---|---|
| cl95b37463 | ok/mstreet/H/0.983/1.192/13 | ok/mstreet/H/0.876/0.994/3 |
| cld01bb4ae | ok/mstreet/H/0.982/1.192/13 | ok/mstreet/H/0.875/0.994/3 |

- explorer bit-mm 16732 -> 11656 (-30.3 %); RUDY ovfH 4.94M -> 3.15M, ovfV 1.64M -> 0.52M; cutH 0.74 -> 0.63.
- Stations: 5 re-sited, regs 9 -> 9, need_more 0 on both types.
- G0 on the composed plan: 77 -> 77 errors, 0 new, 0 col_h10_r1 warnings before and after.
- Plans:
  - ready7 chain 580d790a93c3 -> 075ecf5205fa (delta_h10r1_on_ready7.json).
  - h2_2249 chain e05d5710b3e1 -> a533fc694fc2 (delta_h10r1_on_h2_2249.json).
  - Apply MATCH on both.
- The remaining hottest bin is the frame_int_i1 fan at the S window, (524, 124) over the e5w views. That is the 8 x 605-b
  broadcast from a fixed port window; it is a port / cycle matter, not a position.

## Build
The strict bind of a533fc694fc2 and full-flow builds of BOTH types run on epyc7, using build_type_pc.sh (poscheck after
preflight; route is refused on a FAIL). cld01bb4ae's base failure was an infra waiter. KW-FIX-45 has no named fix for this type. The only
unmerged flow patch on record (gen_phys flow_tag / grt_transition_mode copy, 31b4aa4824 on claude/vislayout2-qc-1111) is
not in src_t51f, so this build runs without it.

## STATUS 2026-11-12: NOT FOR BUILD (station-bits model)
COORD flagged a route_supply model gap. internal_stations entries without "bits" are routed as 1 bit, and
station_face_dedupe then drops the face bus. The kit, however, pads the whole bus through those sites
(u_lpad_<bus>.r[k][0..W-1]). Scored with that fixed locally (bus: stations carry the bus width):

| plan | verdict / region / dir / p99 / max / hot |
|---|---|
| base | FLAG / face / H / 2.667 / 3.041 / 387 at (470, 5) |
| v1b (this form) | FLAG / face / H / 2.636 / 2.993 / 317 at (848, 5) |
| v1c: 5 frame_int_i1 regs re-sited to the y-229 street (resite_stn.py, equal arc 337 um, same ends, same count) | FLAG / street / H / 1.885 |
| v1d: c-row midline y 273 | FLAG / street / H / 1.700 |
| v1f: gap above the c rows y 321 | FLAG / mstreet / H / 1.757 |
| v1e: two streets (y 229, e6/e7 street, y 568) | FLAG / street / V / 1.971 |

The 1264-b frame_int_i1 relay chain (face -> bn6/bn7/bn8.rs, to_um (1296, 851)) has 3 of 5 regs on the S outline.
Every interior H corridor in this floorplan is 20-32 um. The padded chain alone needs about 50 um, and one 337-um stage
cannot hop a 536-um ROM pair on M6/M7. A positions-only form therefore cannot close it. The strict bind was stopped
and no build was started. This needs a decision outside positions: what that station carries, or a frame_int_i1 trunk plan.
