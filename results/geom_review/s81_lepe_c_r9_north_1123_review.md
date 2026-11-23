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

## Revised split with staggered CP2

I inspected `r9_body_clock_geometry.png @ab2fa12936d2` beside the earlier
rendering in the same scratch review folder. Its exact plan is epyc9
`flow-stripbody-r2/codex_r9_north/split_body_clocks/plan_c_reset_fixed.json
@7a68dd07af9e`. The 181.44 µm CP2 move opens the former CP2 footprint
between the formatter and CP3. The cap, XR and CP2 early clock sites now
follow their macro movements. Both strip footprints remain clear.

The planned footprints and translated clocks pass visual review. The
source split and reset selection finished with rc0. FSTART now uses depth-5
`rst_rl_88` at 235.248 µm from the consumer site. The one-cycle local copy
retains release depth 6. All 41 changed and new lane prices are in
`split_body_clocks/latency_rows.json @dce59cadc723`. A scoped strict bind
and planned geometry checks are active. Placed congestion and signoff
still need their own evidence before any route decision.
