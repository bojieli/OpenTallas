# S81 literal graded clock physical candidate (2026-10-27 14:55 PDT)

Source base main 5b3f0f6b2; source branch codex/s81-die-1351. Geometry only, no route or die timing approval.

Literal physical rails: 192 M8 +192 M9 rails, width .08..1.76um, 8.64um separation between adjacent parallel rails (each occupies its own existing PG gap), .48um PG width, 1um long-PRL spacing. Every crossing has a real width-fitting via array. 73,344 segments /36,864 crossings /2,067,480 cuts. Three-rail fringe capacitance is explicit in driver inventory: 40,540 real BUFx24 cells at3747 sites, not7494 old units. No R divided by rail count.

The historical single128w M8 stripe was5.12um and exceeds actual M8 MAXWIDTH2.0. Its predictor is a non-realizable sensitivity. The cached ASAP7 M9 block has no MAXWIDTH and the technology has no SLOT rule; do not apply M8 MAXWIDTH to M9 PG.

Final placement runtime intel1:/srv/opentallas-scratch2/claude/codex-s81-graded-1351/p128_stage18
- hard-core bodies0; actual exported pin hops above405um0; FT2um halo hits0; clock body overlaps0.
- Three cap leaf nodes and their six real banks jointly move to actual soft channels, banks reshaped into one column. Fixed-bank diamond intersections had forced the old nodes inside the hard cores.
- BSEL h110101 whole leg detours around the macro through its left soft channel with the SAME six stages.
- Every one of the four level2 legs now has18segments instead17; all four have exactly one additional real buffer. No instance-specific stage exception.
- Literal metal unchanged by placement. Driver attachment anchors in graded_metal.json updated after bank movement. These jogs, all tree wires, pin stacks and PG/shields still need actual encoding and full metal census.

geometry.png and joint_geometry.png personally viewed: PASS-COND bank/rail arrangement only. No route. Runtime stage18 unit intel1 oth-ubuntu-1273509-1793137853 exit0. Reproduction scripts intentionally preserve their immutable takeover runtime paths.

Legacy combo explicitly rejects the graded marker until physical_encoder_qualified. It cannot silently emit uniform4w metal. FLOW rc_canary exclusively owns native coupon extraction of the exact widths1.60/1.68/1.76 and true crossconnections. First extraction produced a TREE instead of actual25-cycle mesh because native coincident coordinates were not graph junctions; receipt preserved, no equivalent-R claim. Native junction/graph correction remains OPEN. Field width tables198samples PASS but do not qualify topology. Existing RCX asset only supports up to1.28um.

Pending: literal full-mesh/tree/pin-stack encoder, actual local-domain PG/shield/clock metal census, native extracted coupling and topology, slew/EM/IR, matched current endpoint views and die timing. Rebuild any stale path-length summaries from actual cells/nets before timing. Physical placement PASS is not release closure.
