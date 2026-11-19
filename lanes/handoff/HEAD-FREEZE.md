# HEAD-FREEZE: clock-site reservations vs the live die clock tree (FABLE-FIX-HEAD-MESH, 2026-11-18 PST; COORD ruling r711)

Status: OPEN die-freeze item. Not part of the r5 delta. Do not act type by type.

## Finding
The HEAD plan's `clock.reserved_sites_um` rows (kind `die_clock_tree`) do not match the die clock tree in the live tree
(`prep/NF15f/die_clock/kit_tree.json`, rs8 fresh clock GEN, 44,509 cells). The clock GEN was re-run fresh; the reservation
tool (`tools/die_plan/clksite_reserve.py`) was not re-run from its output.

Measured on snapshot `kw45/snap_s81_head/s81_head_r4_s0` (plan 37c183cd). Method: every clock cell site inside an instance
of the type, body 1.62 x 0.27 um, mapped to the type frame; a row "holds a cell" when a body lies inside the row rect.

| Type | Rows | Rows holding no cell | Clock cell bodies (union over instances) | Bodies with no row |
|---|---|---|---|---|
| hd_mesh | 633 | 554 | 759 | 701 |
| hd_serdes | 100 | 53 | 558 | 465 |
| hd_lep0N | 628 | 626 | 637 | 635 |
| hd_tile | 0 | 0 | 3,570 | 3,570 |
| hd_ctl | 0 | 0 | 192 | 192 |

hd_mesh row centre to nearest cell origin: median 0.54 um, p90 2.16 um, max 108.9 um; 379 of 633 rows within 1.5 um.
Other HEAD types: not measured yet.

Caveat: this is one reader's containment check. A partial offset convention (0.54 um median) may explain part of the
"no cell" count on hd_mesh; it does not explain rows 100 um from any cell, nor types with cells and zero rows.

## Die-assembly risk: cells with no row (hd_tile)
264 hd_tile instances carry 37,731 die clock cell placements = 3,549 distinct body sites in the type frame.
Against the signed hd_tile DB (`signed-export-1114/s81_head/hd_tile__ax_77c210ac4b/6_final.odb`, event NF15d2r1, outline
717.12 x 1036.80 = the NF15f outline, 902,507 instances):

| Body sites | Count |
|---|---|
| over a hard macro | 0 |
| over placed logic cells | 856 (1,565 standard cells hit) |
| over filler / tap cells only | 2,663 |
| free | 30 |

So 24% of the clock cell sites in a tile sit on placed logic. Metal (route) conflicts were not measured; a site over
filler still needs its M1-M7 access free. The signed DB is from NF15d2r1, not NF15f: recheck on the NF15f hd_tile when it exists.

Evidence: epyc9 `/srv/opentallas-scratch2/claude/fable-fix-head-mesh/r5/` (`hd_tile_clk_rects.txt`, `ovl.tcl`, `ovl.log`).

## Plan (COORD ruling)
1. When hd_mesh and hd_lep0N are signed off: regenerate ALL HEAD reservations from the live die clock tree in ONE event,
   with a fixed script (clksite_reserve.py PLAN ROWS --tree kit_tree.json, then the rows applied, receipt re-issued,
   live_tree apply) and a second, independent containment check (0 bodies without a row, 0 rows without a body).
2. Set HEAD plan_frozen.
3. Re-sign the affected types as a batch, ECO first: a type whose new reservation only REMOVES obstructions needs a
   re-route ECO at most; a type that gains rows over placed cells (hd_tile: 856 sites) needs cells moved off those
   sites (placement ECO + re-route), or the clock cells re-sited by the die clock tool with those cells as keepouts.

## Related
- r5 delta (applied separately): hd_mesh rows 633 -> 631 (two stale rows on the north coll_oa pin row dropped), route_layers
  narrowed on the two clk tap sites. Die clock tree unchanged.
- `die.clock.face_pin_keepout_um` (die_clock.py, opt-in, default 0) keeps clock cells off partition face pin rows; set it in
  the regeneration event so a fresh tree cannot land on a pin row.
- Open DRT-0255 class (M8 PG track guard) is separate: see lanes/posts/FABLE-FIX-HEAD-MESH.md.
