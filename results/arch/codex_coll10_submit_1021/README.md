# COLL q10 gate collection

The original q10a and q10b gate results and actual PNGs were collected into this own worktree from the paused source tree without modifying that tree. Both gates finished WARN with zero FAILs, native mapped census PASS max32 and zero trial GRT overflow. Both have the same mapped native netlist SHA 68b2d033b4603e1ce949fe697ea27bbd34b341981884c40f623839033814b1f5. Compact native receipts retain the actual remote raw report path, hash and library/netlist identity.

ROOT independently inspected q10a floorplan/density PNGs, the raw gate JSON, native receipt and exact SRAM coordinates, then approved this geometry for ordinary qualification. The bound approval is transcribed in gate_layout/REVIEW.json. Coordinates are legal on actual routing tracks; the macro origins are not all on a 43.2 um lattice. ROOT review of q10b is pending.

Exact-source validation materialized every consumed source path. The remaining normal submit blocker is the captured textbook_lint helper ancestry. The existing verified frozen-helper recovery validates the complete original source snapshot, original script and original log, but its helper verifier cannot accept the three executed gate overlay entries outside the separate route-only plan: native_census.py, native_census.tcl and ref_route.sh. They are present in the immutable full source manifest. The original plan and source have not been altered. Integration has this bounded recovery defect; no new physical gate, threshold change or waiver is requested.

Final routed SS/FF and die timing remain open. These are TT pathfinding gates.

ROOT subsequently approved q10b independently. Normal submit_exact automatically used current main tools and passed ordinary source qualification for q10a. The old branch-local checker was stale; frozen recovery is unnecessary. q10a was submitted normally as qfd_coll_split_q10a-q10a-3ecbc6e75. No recovery helper change or rule waiver was used.
