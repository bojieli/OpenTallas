# S81 J9 SVC7 shared seam planned review

2026-11-23 14:59 PST. Exact base 1c65201fcd75, shape candidate 667b23feb46f, guarded row ff67c12a1fa1. Viewed the exact planned footprint render from E10 `s81-j9-r6/compose/g0_hard_svc_1054/svc7_retain_1454/layout.png`. Both SVC7 bounding boxes extend 120.96 µm north into unused area. The new north edge at y7179.84 leaves 8.64 µm to seqhost. The edited seam stays between the two tiles and there are no north-face ports in the added strip. The two through-ATT window centers retain their prior positions.

The E10 unit 29539 check passed with zero target abutment or face errors and no new findings in 29 affected lanes. Peak demand is 64 pins per 10 µm with zero shared tracks. A separate scope found both generated reset anchors consistent and made no tap or reset name changes. TAPOFF added seven rows to the sole configured table. The corrected digest cdb489ab4e22 passed the scoped census with no missing or stale entries. SVC7_RS has no TAPOFF table. The wrapper returned one because it expected two tables after the census had passed.

The verdict covers the revised floorplan and modeled reach. This row remains separate from the running B2 plan pending exact assembly, native binding, and placed visual review.
