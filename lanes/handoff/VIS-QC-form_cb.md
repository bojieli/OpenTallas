# VISQC-CB-1: structural form for the QC cb family (17 types). Status DRAFT (VIS-QC, 11-22 23:4x PST)

## What the renders show (read: 23 kit renders + 6 tap overlays)
- Every cb type has the same floorplan: four hard tiles `qfd_tile_nk_a0c` 457.92 x 1157.76 um in a 2x2 grid on a
  1235.5 x 2531.5 (2540 / 2566) um die. All non-tile logic (~170k std cells pre-floorplan, 290-460k after place)
  lives in thin strips: W margin x 0-86.4, central channel x 544.3-691.2 (147 um), E margin x 1149.1-1235.5,
  H channel y 1235.5-1304.7 (69 um), N/S margins ~70 um.
- The strips are NOT globally full: place density is <0.4 in most of the channel. GRT routes in every kit
  (final total overflow 707-4615, max per-gcell 2-19); congestion is not what stops the family.
- What IS concentrated: (a) clock-tap load and (b) local piles at margin pin rows/landings.
  Six kits with a CTS tap census: 8-23 over-cap taps each, debt 6.9k-16.7k sinks
  (q00 rev5 15/12954, cbn_q01 cldd6ea846 23/16652, cbn_q00 cld7bf7197 15/10966, cbf_q01_s2 9/9443,
  cbf_q11 8/7572, cbx_q10 cl94a12200 9/6887). 60 % of the over-cap taps are in the 147-um central channel at
  x 557-679, mostly at y 1880-2220 and 860-1000; the rest at the E/W margins (x 48-82, 1158-1179) at the same
  y bands.
- Over-cap taps line up with the hotspots: GRT reaches 100 % at x 691 (right tiles' W-face pin windows)
  y 1021-1066 and 2125-2214 in 7 kits, and the heaviest taps sit exactly there (q01_s2 t117 6649 at (592,2121);
  q11 t76/t79 3659/3431 at (635,2069/2164); x10 t64/t67 2998/2776 at (670,2104/2208); n01_dd t113 6979 at
  (635,2182)). The q00 rev5 stop (D10 latch -207 ps, clock skew 321 ps) is launched from an over-cap channel tap
  (clk_t60 1531, insertion 570 ps vs capture clk_t82 249 ps).
- Outliers: cbn_q00 cldbcda913 / cl622f65d2 (9-macro form) put 5 hard cland landing macros in the 69-um N/S
  margins; the V1 GRT shows the full-length W-margin strip and the N margin under the NE landing at ~100 %.
  q00 rev5's only real GRT hotspot is the NE-corner landing u_cland_nb_i00 (1150-1230, 2450-2470).

## The form (one row per type, 0 cycles, no growth)
1. Channel tap grid sized from placed sinks (main fix). For each cb type, add taps in the central channel and the
   E/W margins from the placed sink bins (tap_split.py / sink_bins_from_place.py, TAP-GRID-R5 method), cap 900,
   radius <= 150 um, sited on the channel centre line (x ~618 central, ~43 W, ~1192 E) at the y bands of the
   bus pin windows. Measured need: q00 +15, cbn_q01 cldd6ea846 +19, cbn_q00 cld7bf7197 +13, cbf_q01_s2 +11,
   cbf_q11 +9, cbx_q10 cl94 +8 extra taps. Types without a CTS census (11 of 17) take the same bands
   (y 860-1066 and 1880-2220 in the central channel, plus the matching margin bands) and get exact counts from
   their placed DB. CB-R4 already proved the method offline on two pieces: q00 t60 triple t115-117
   (t60 1531 -> 460) and the t86 four-tap test (3930 -> 977); Glue +21 (debt 18,254 -> 977). This row turns
   those one-off splits into a family form.
2. Margin landings off the corners and out of the 69-um margins (outliers only):
   - q00 (both cl): re-site u_cland_nb_i00 from the NE corner to the E margin at y 2200-2460, so its 517-bit row
     no longer meets the N pin row in the corner.
   - cbn_q00 9-macro (cldbcda913, cl622f65d2): either move the hard N/S landing macros onto the tile-free margin
     centres or grow the N/S margins from 69 to >= 110 um (+82 um die height, pre-approved). Easiest for closure:
     the re-site (no die change); growth only if the probe still shows the margin strip at 100 %.
3. Not proposed: central-channel widening. The pin-window GRT hotspots reach 100 % but don't overflow; the tile
   LEF pin windows are inside the signed hard tile. Revisit only if form 1 leaves GRT overflow > 1000 there.

## Fast probe (about 1 h, no kit)
- Fork the V4 tree (ot-tree-fork), apply rows 1+2 on q00 (cl1b5a6458) and cbn_q01 cldd6ea846, then
  run plan_gate_pre --baseline-plan <V4> and the place + PRE_CTS tap assignment (clock_taps.tcl writes
  ot_clock_taps.json) + quick GRT map.
- PASS = 0 over-cap taps in ot_clock_taps.json, no tap within 150 um of the x 691 pin windows above 900, and the
  NE-corner GRT overflow (1150-1230, 2450-2470) under 100. Re-render with vq_render.py and READ it.
- Then one sealed --goal route kit plus one OT_PROBE_THROUGH=1 kit on q00 cl1b5a6458 (the -207 ps D10 type).

## Is it already in V4?
No. V4 L0 carries cb row A + HB4 rev5 (latch exceptions; CTS -157 -> -62), which is the timing form, not the
tap or landing geometry. The cb tap pieces (q00 t115-117 triple, t86 split, TAP-GRID-R5 package row 19) and the
cbx bc_i30 re-site (row 6) sit in L2, which was dropped from V4. Without row 1, V4 cb kits should show the same
8-23 over-cap channel taps, and the same skew-driven D10/NK latch stops as V2.
