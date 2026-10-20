# Footprint-aware successor model

The actual replay passes the missing-instance guard and reaches the physical audit, but fails 18,351 of 126,817 audited buses. The accompanying JSON pins this diagnosis to the exact packet SHA. The diagnostic process remains live after the audit; this is not a terminal GEN result.

The existing relay planner calls independent process-local Router jobs against non-relay obstacles and then pads equal-age sinks at the same nearest-free point. It never reserves the full multi-tile row against other buses. The failure packet distinguishes 2,003 rows lacking free footprint from 2,259 rows with no feasible reach. Fifty-one failed rows share one planned site.

A concrete counterexample is rf0027_k02_00: 17 NS 624-bit tiles, each 64.8 by 23.76 um in the actual emitted LEF, create a 1101.6 um transverse row. Its planned endpoint span already reaches 482.1 um and the least-violating placed span is 545.3 um. A point-grid path with nominal 405 um steps cannot establish physical reach for this row.

The successor must start from source-pinned actual parent and relay pin coordinates for each tile, route separate tile lanes with shared nonoverlap reservations, then choose station counts before exporting the contract. Place pads as explicit reserved stages, include forwarded-clock edges, and equalize sink ages only after successful geometry. If no legal corridor exists, report the required channel/parent-placement change instead of relocating outside the reach bound. Rebuild relay contracts and compiler ages from the final stage counts; data/reset separation remains required. The current bounded-fail guard prevents fallback from making failed rows look successful.

No existing release bindings or calendars are changed by this model. Implementing reservation on shared centroid points alone is insufficient. Full placement/reach proof, actual PNG review, native census and clock/PG closure remain mandatory.
