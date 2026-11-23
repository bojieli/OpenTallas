# S81 LEPE C t1 north and south strip plan review

The reviewed split plan is epyc9 `flow-stripbody-r2/codex_r9_north/split/plan_c_reset_fixed.json`
at `a023296a18dd1874a7996df72ec8bf5ccd84bbeedd6cf9ba0fc4a6a5a29f70a4`.
The exact plan rendering is intel2 `flow-stripbody-r2/codex_reset_probe/r9_north_geometry.png`
at `d8501110611f267e01048c0493d1fded6f293c4cfcb58614004403691ce63116`.
I inspected all three piece outlines and their planned hard macro and ROM footprints.

The north strip is clear across 1,442.88 × 86.4 µm with 12 planned clock sites in
one row. The south strip is clear across 1,442.88 × 95.04 µm. Both pass this
plan-footprint review. The north clearance comes from the five recorded Y-only
macro translations in `north_row_receipt.json`. This pass covers the planned
footprints and named clock sites. Strict bind, LATCHECK and placed congestion
remain prerequisites for a route decision.

The body still contains the near-contiguous CP and formatter row. The retained
placed body failed at that wall. Hold this body's P&R here. The independent
stagger proposal moves CP2 181.44 µm north into the visible open area to break
the row. Review the resulting split and verify its reset and crossing latency
before accepting that body.
