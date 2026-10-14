# HBM diagnostic timing tools and candidate evidence, 2026-10-13

This standalone change preserves timing-tool fixes and candidate records from
`claude/hbm-native-die-1013@31a02920b`. It does not change the main die generator,
publish the v13 contract, qualify its geometry, or authorize M6 grants.

The clock constraints retain physical delivery at phi minus boundary insertion.
Explicit per-pin ETM clock tree paths are recorded as metadata. Real ETM probes
show propagated source clocks retain the I/O tables without subtracting those
paths; adding them to the physical source latency would double-count insertion.
Common/common setup uncertainty is 150 ps under the existing owner clock rule;
any pair involving an early tap receives 210 ps in both directions. Only
cross-domain pairs remain false paths. Routed boundary metadata establishes
spread; missing or placement-estimated spread remains unmeasured.

`tools/hbm_die_sta_plan.py --ds-var <current preset> --out <plan directory>`
exports the existing generator's pins and hops without changing geometry.
`tools/hbm_die_sta_classes.py <plan directory> <paths reports> --case <STA case>
--out <JSON> --md <table>` classifies the actual bound libraries and reports
untimed coverage. Generator-only fallback is diagnostic and can over-count
placeholders. `hbm_die_views.py die --placeholder-all` is optional pathfinding
coverage; analytic placeholder rows do not prove real-view die timing.

`SM_fit_inventory.json` is an incomplete-fit candidate inventory, with its model
hash verified against the retained source. It preserves all 32 SMs and the
reticle target; occupied rectangles do not establish routing or physical fit.

The adjacent `pin_assign_1013` records are provisional contract-derived quant
contacts. Existing source-spec hashes and same-layer nonoverlap were checked.
They require source/spec adoption with renewed digests, actual GRT-guide and
neighbor access review, correct parent-origin residue and PG exclusions before
any final grant or submission. Their recorded guide observation is historical.

Validation: the original five clock-constraint tests and two classifier tests
pass, plus a new exporter regression preserving exact hop lengths and missing
pins. Changed Python tools compile; both CLI parsers load on main.
