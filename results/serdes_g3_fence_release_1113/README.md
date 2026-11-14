Private G3 geometry diagnosis, not a source/physical signoff or adoption.

G3 has six legal-grid dbRegion fences. Every grouped cell is site-aligned, but 3,051 ungrouped repair buffers have x-site phase -1 DBU, often exactly at a region xmax minus one DBU. Final DPL also has ten overlaps. This is distinct from the earlier fractional region-boundary error.

Two bounded failed-ODB fixtures, first direct APIs then the exact optional source hook, remove only six sl_* group fences before DPL. Both check_placement PASS and preserve all 51,054 clock ITerm net names. Five groups retain every cell in their original bounds; only 2/40,904 syn cells leave by at most 0.216um. Mean displacement0.1um/max3.4um. No source, clock, net, macro or pin change. No CTS/GRT/signoff implied; G3 captures RST_TREE0 and is a geometry-only diagnostic.

The source hook defaults OFF. A future reviewed form may explicitly set `dict set sl_cfg release_regions_before_dpl 1`. The hook records original member names and bounds before release. Actual placement locality, clock-group assignment, access and route/timing remain required for that new form. H2 and all current kits are unchanged.

Exact-hook fixture: E9 hard-s81-serdes-1/g3_fence_hook_fixture, ot-run unit1508663-1794615879 exit0. Existing old fixture receipt retained separately. Source release hook only; unrelated uncommitted outward-grid serdes_lanes.tcl edit excluded.
