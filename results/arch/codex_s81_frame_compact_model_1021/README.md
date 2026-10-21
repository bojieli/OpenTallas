# Actual S81 frame compaction placement model

MODEL ONLY. No RTL, kit, clock/reset policy, outline or ABI was changed. No synthesis, simulation, physical gate, route or validation campaign was launched. This packet is separate from codex/s81-frrst2-1021.

The actual preferred rf3rl h9 is1436.832x3369.6um,115 hard children plus105 raw configuration ROMs (220 rectangles). h10 is1436.832x3672um,123 hard children plus112 ROMs (235 rectangles). Each keeps12 Q elements and24 Q banks. h9 has6 bf_col +3 fronts; h10 has8 bf_col +4 fronts. ROM dimensions38.04x62.952 are included, never treated as empty space.

For five h9 plus two h10 per column, current body height=24192um. With760 streets +250 top allowance +3758 current service band, total=28960um. To meet25000, frame bodies must total<=20232um:3960um/16.37% reduction. This is a necessary height bound, not a full die fit claim.

The fixed-x model preserves each real rectangle's x, size, orientation and original vertical order whenever horizontal projections overlap or are separated by less than20um. An acyclic predecessor graph assigns the earliest y on43.2um hard-child or2.16um raw-ROM lattice, with22.16um outer margin and20um rectangle channels. Despite some noncritical rectangles moving down, maximum outline heights remain3369.6/3672: no dead vertical whitespace can remove the critical chain under these constraints. Concrete placements and binding predecessors are h9.json/h10.json.

The binding chain repeatedly contains a Q element, a cfg7_seq at x345.6, a qbank_N at x345.6, then the next Q element; other gaps are bound by the62.952um raw ROM stripe. The row-structured frame_kit packs whole bands below whole big rows. To reduce height, at least some small children must move horizontally or reorder relative to those rows.

One explicit repack proposal retained big-child x and order, set their row pitch to302.4um, and placed small actual rectangles near their compressed original positions with20um spacing and the same lattices. Target outlines were2894.4/3196.8um. It placed157/220 h9 and166/235 h10 rectangles;63/69 remain UNPLACED, mostly ROMs/sequencers. repack_h9.json/repack_h10.json list every proposed rectangle and every missing instance. This is an incomplete heuristic result, not an impossibility proof and not a legal replacement floorplan. No lower outline is adopted.

Even if all rectangles could be packed at those target outlines, five h9 +two h10=20865.6um; +1010 leaves3124.4um for the service band,633.6um short of3758. For h10=3196.8, h9 must be<=2767.68 (2764.8 on43.2 lattice); for h9=2894.4, h10 must be<=2880 (2851.2 on43.2 lattice). A full solution needs a stronger frame rearrangement and/or the die lead's two-dimensional service redistribution.

Physical work remains substantial: sideways small-child/ROM packing must preserve actual connectivity/reach and regional reset/clock structure, reserve soft-cell/relay sites, regenerate kit placements and close the existing interface. This packet establishes no timing, routing, utilization, reset CDC or clock-spread result and warrants no new gate by itself. No hypothetical resize of a hardened child is used.
