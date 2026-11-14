# QC-S28-E (DIE-QC-99 s28 items from GEOM-VIS-1): ASPECT-OVERSIZE class + glue clock taps

Base: plan_qc99_s28 2f0c17d5f1a3 (claude/qc-event-s28-1111@88018018ef). DO_NOT_COUNT. Stage S2 (type floorplan) /
S1 (die floorplan proposal).

## Item 1: ASPECT-OVERSIZE (QC members: 622x1339 / 613x1339 slice types, 1236x2540 cb*, glue)

Scope. cb* (1236x2532/2540) belongs to S28-C (cbx) and S28-D (cb* centre spine) and is not touched here. glue is
777.6x1468.8 (aspect 1.89 < 2.0). GEOM-VIS-1 put it in the class, but its real smells are taps and an empty S 60 %,
which item 2 covers. That leaves the slice band: 89 types, 12 slices x 4 rows x 4 columns.

Die geometry. The slice band is fully tiled. It runs x 1564..31211 (die 31216) and y 10143..15500, between the cb rows.
Each slice column is 2470.6 x 5356.8, split into four 1339.2 rows
([hc0|hc1|hc2|hc3], [st_a|ctl|st_b], [fw|stm|sc|fe], [su_l1|su_c|su_l0]) with columns 622.08/613.44/613.44/622.08
(gen_plan CW lattice; PLAN-QCv2 slice_layout_search.py chose the cell order). Aspect 2.15-2.18 comes from that lattice.
Content plays no part in it.

Findings (numbers in ASPECT_DECISION_s28e.tsv):
- Not area-bound. Measured fill_of_free is 3-8 % and empty_area 0.70-0.94 on every slice type (GEOM-VIS-1 auto_geom
  copies).
- Width alone does not fix it. Run route_supply (edge_outline) with su/st widened to 777.6, sc to 734.4 and hc1 to
  691.2, contents unchanged: 30 of 41 types move by less than 0.05. The worst region is the landing ring
  (band-local), i.e. LAND-RING-2 / S28-B strip density. Real gains: slw_su_l1 1.697 -> 1.237,
  slw_st_a_v1 pv 1.215 -> 0.835, slw_st_b_v1 pv 1.151 -> 0.912, slw_sc 1.14 -> 1.01-1.04.
  Picture: width_whatif_route_supply.png.
- N/S face windows span 85-99 % of every type's width (slack.py). Any seam move therefore re-windows the inter-row
  seams, which makes it a die-level event, not a per-type one.
- Rows are mis-sized in height (QC-S28-DIEVIEW content-natural heights): hc needs ~370-520 (content in the S 40 %,
  slw_hc3 content y <= 1002, x <= 368), the fw/fe/sc/stm row needs ~1780 (E/W face-pin wall: fw E 5.6-7.5 kb on
  1339 um), st/ctl 1222 is OK, and su needs ~1400 (su_l1 core column 1325 in 1339).

Decision. There is NO per-type outline change inside the 1339 lattice: it cannot fix the binding constraints.
Proposed instead is ONE die event (S1), with no die growth:
- P1 row re-pitch: hc 1339 -> 520, mid row 1339 -> 1780, st/ctl 1339, su 1339 -> 1400. The sum is 5039 vs 5357, so
  318 um are left for the cb H streets or a die y shrink. Instances shift in y only. Strip-internal N/S hops change by
  at most the row deltas. The hc-row ft stations (y 1026-1043) re-site, and their cycle count may DROP (EQ statement
  at the event).
- P2 su columns: 777.6 | 915.84 | 777.6 (su_c donor; macro 31 %, p99 0.88-0.94).
- P3 st columns: 777.6 | 915.84 | 777.6 (ctl donor; fill 3 %). st_a still carries 417-436k cells, over the 400k
  OpenROAD cap: R8 split / soft area is still needed (VL2QC-STA flag).
- P4 sc 613.44 -> 734.4 from fe (fe fill 1-3.5 %, p99 0.61).
SUPERSEDED BY HF-1c (claude/qc-s28-floorplan-1112@ea7be452d3): rows su 1399.68 / mid 1831.68 (s28 widths) / st 1339.2 / hc 717.12, cbn_q00 +34.56 with cbx_q10 _h split types. HF-1c is P1 in final numbers; P4 was dropped (fe stranding). P2/P3 (su/st column widths) remain an optional follow-up. Earlier note on HF-1:
- P1 and P4 match HF-1: hc 622/613 x 777.6, mid row x 1831.68, sc 656.64, fe 578.88.
- HF-1 keeps the su and st/ctl rows the same shape (only moved). P2/P3 are this lane's ADDITIONAL column proposals,
  with the measured width-only gains above: su_l1 -0.46, st_a pv -0.38, st_b pv -0.24 p99. Ranked after P1.
- The per-type re-pitch inside the HF-1 outlines is NOT in this delta. It needs HF-1's composed die windows first,
  then a monotone y/x map of every type-local coordinate (slot_channel_event / STREET-RULE-1 legalize form) per row
  family, which can be done as the next stage.
All of these keep core shapes (cores only move) and the cb seams. Neighbour-die seams / reticle / pad rows are
untouched (the slice band is interior). No slice or glue type is SIGNED (PROTECTED-DBS.txt and kit_wave_stages:
0 QC slice/glue sign-offs). Signed hard children inside (cland rings, su lane cores) keep their views: they move
only, so the parents re-kit and there is NO child re-sign.

## Item 2: glue clk_d2d (22k) and clk_t6 (14k)

- clk_d2d is the die-to-die forwarded d2d clock (mesochronous). It is ONE RTL port in glue (plan
  clock.edge_clocks[0], tap 406,743), so the plan cannot split it into clk taps. QC is in gen_phys EDGE_SPLIT_DIES:
  the kit's clock_edge_split.tcl splits its sinks before CTS into groups of <= OT_EDGE_SPLIT_MAX_SINKS (default
  1500) and <= OT_EDGE_SPLIT_SPAN_UM (default 300; half-diagonal 212 > the 200-um tap radius rule), one root buffer
  each, and balances them post-CTS. The GEOM-VIS "single tap" is the 3_place view (before the split).
  REACH-FIX-1 class item: emit OT_EDGE_SPLIT_MAX_SINKS = plan tap cap (1200) and SPAN <= 280 um from the plan, for
  every edge port (QC coll_s, coll_n, coll_ucie, glue; KV kv3_sys_SD). Reach data (11-10 attempt_9 3_place):
  21,796 sinks, entry (405.6, 743.0), logic in the N third (y 900-1450) plus a W strip, farthest leaf 1850 um.
- The clk family of glue is the one fixed here. glue was the last soft QC type on the R4 grid (pitch 400 -> 8 taps,
  cap 3000, no bins). Measured: clk_t6 14,033 and clk_t7 4,118 sinks, so the cap moves find no tap within 200 um.
  DELIVERED: the QC density form (tap_density_class_1106 recipe): tap_mode density, tap_max_sinks 1200,
  tap_target_sinks 900, tap_radius_um 200, and sink_bins_file plan_of_record/sink_bins/glue.json.
  - BINS ARE A PROXY. No glue 3_place.odb survives on any host. The file spreads the measured per-tap counts
    (22,796) over each grid tap's nearest-tap cell, weighted by the rendered place density (glue_proxy_bins.py).
    Replace it at glue's first s28 3_place.odb with sinkdump28.tcl + make_s28.py bins, then rerun
    make_s28e.py compose.
  - Taps 8 -> 61. Kit rule (taps.assign) on the bins: max 14,000 -> 970 per tap, 2 -> 0 over cap, reach 367 -> 185 um.
  - Collector: landing source taps were re-pointed (2 remaps, max 61.5 um), and the collector tree was re-published
    and reattached. The reset tree goes 5 -> 6 deep, which gives +1 COLLECTOR cycle on glue's 32 ring collectors
    (reset-release wavefront only; no data, bus, station or pin cycle). A target of 1200 also gives depth 6
    (58 taps, radius-bound).

## Files
- apply_s28e.py: `apply PLAN_IN PLAN_OUT delta_s28e.json --sidecar IN OUT --repo TREE`. It is guarded by the
  canonical sha of the base glue object and of the sidecar collector.types.glue, and fails closed.
- delta_s28e.json: glue type (new), sidecar entry, bins sha.
- make_s28e.py (compose + hist), glue_proxy_bins.py, slack.py / whatif.py / yext.py (item 1 analysis),
  ASPECT_DECISION_s28e.tsv, evidence/.

## Gates (glue delta, plan 277e908d1240 + sidecar 4ad925a263ba)
- schema PASS 0. G0 265/265 errors, 0 new. G0C 365/365 errors, 0 new; 3 warnings GONE (glue clock_reach 371, clk_t6 tap_sinks 3281, tapcap count line), 1 count line re-worded (108 vs 107 types with a sink inventory). station_lint 3 NONMONOTONE, same as base.
- strict bind (bind-strict-src, src28b + glue bins): rc 0, 377 partitions, 1921 crossings, 790,393 bits, 0 errors. bus_groups sha 315252676904 is identical to s28. bind_latency differs only in reset glue: depth 5->6, release_after_pin 6->7, part release 123->124.
- EQ: +1 reset-release cycle on glue only (no data/bus/station/pin cycle). Owner pre-approval 11-12 (cycles) applies.
- Re-sign scope: 0 signed types or cores (glue is unsigned). glue gets a fresh kit and build.
