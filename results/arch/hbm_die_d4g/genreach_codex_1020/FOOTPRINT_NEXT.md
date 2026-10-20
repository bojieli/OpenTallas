# Footprint-aware successor model

The actual replay passes the missing-instance guard and reaches the physical audit, but fails 18,351 of 126,817 audited buses. The accompanying JSON pins this diagnosis to the exact packet SHA. The diagnostic process remains live after the audit; this is not a terminal GEN result.

The existing relay planner calls independent process-local Router jobs against non-relay obstacles and then pads equal-age sinks at the same nearest-free point. It never reserves the full multi-tile row against other buses. The failure packet distinguishes 2,003 rows lacking free footprint from 2,259 rows with no feasible reach. Fifty-one failed rows share one planned site.

ERRATUM 01:36: the earlier attribution of rf0027_k02_00 to seventeen NS624 real relays was wrong and is withdrawn. The exact contract contains seventeen hbfd_land_136_NS SYNTH cells, area324.74034um2 each, no macros,280 port bits. Current generator square area/0.60 and ceil snapping yield23.328x23.76um per tile,396.576um row width. The measured failing planned482.1um and least-violating545.3um spans remain actual; the1101.6um width belongs only to an unrelated synthetic17xNS624 coupon. Actual leaf pin locations are not available before SYNTH abstract generation, so this packet does not claim a complete pin-exact route diagnosis for that row.

The successor must start from source-pinned actual parent and relay pin coordinates for each tile, route separate tile lanes with shared nonoverlap reservations, then choose station counts before exporting the contract. Place pads as explicit reserved stages, include forwarded-clock edges, and equalize sink ages only after successful geometry. If no legal corridor exists, report the required channel/parent-placement change instead of relocating outside the reach bound. Rebuild relay contracts and compiler ages from the final stage counts; data/reset separation remains required. The current bounded-fail guard prevents fallback from making failed rows look successful.

No existing release bindings or calendars are changed by this model. Implementing reservation on shared centroid points alone is insufficient. Full placement/reach proof, actual PNG review, native census and clock/PG closure remain mandatory.

Endpoint model erratum: production tuples encode [instance,port,low,high_exclusive], not low/width. The model now uses high-low and has a nonzero-low regression; every caller is confined to model tests/coupons. No production caller or contract changed.
