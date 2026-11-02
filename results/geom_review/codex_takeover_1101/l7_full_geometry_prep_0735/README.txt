PREP ONLY. QC owns normal ot-run admission/collection (8GB2T, no duplicate).
Copy input.odb from Intel1 codex-qc-l7-lvt-readout-1102/LVT_DATA_GEOMETRY_CHECKPOINT.odb.
Retain exact constraint.sdc, freeze.json, config.mk, face_guard.json, pins.json,
plan_pins.json, core.json, boundary_guard_context.json, sram_pincol_halo.json,
physical_overlay.json, physical_grt_receipt.json, combined_coverage.json and
native_import_compare.json from that same source directory as source context.
Exact source and baseline l7_grt_cont1131 have NO land_slots.json (bounded checks).
Record that absence; do not invent a land_slots or borrow L1 contracts.
This dump only reads saved DB and sources normal geom_dump.tcl at global scope.
It does not load SDC/Liberty, route, place, estimate parasitics, analyze timing,
connect PG, change net flags, or write an ODB. Existing saved CLOCK flags and
MTerm sequential-clock recognition feed normal geometry clock classification.
geom.tsv O records are actual native macro master obstruction/pin layer masks.
native_obstacles.tsv preserves actual macro bodies + explicit block obstacles,
without adding artificial halo geometry. Preserve the exact pin-column halo
rectangles (including rects decompositions) separately for canonical union LOOK;
do not replace their union with overlapping strip bounding boxes or count twice.
Output must have L7_READONLY_GEOM_CLOSED; partial TSV is not reviewable.
Send closed geom.tsv + context files + pg_census/native_obstacles to geometry.
Current all-kits M5 rules/PNG will be rendered locally, GRT=NA until actual same
source complete route evidence is supplied; no L1 partialface flags borrowed.
