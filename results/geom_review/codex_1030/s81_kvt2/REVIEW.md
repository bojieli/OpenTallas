# S81 event3 kv_leaf t2 macrofit

Independent Codex GEOM review, 2026-10-30: **PASS-COND for macro packing and layer clearance only**. Viewed packing.png. Current source intel2 wt/codex-s81-0336 physical/die_plan/s81/plan_h2_2249.json SHA25639aa595f5bd3; all183 contents' instance/module/origin/outline/LEF/lib fields independently match delta_kvt2site_1030.json.

The picture preserves the unchanged1442.88x1226.88 outline, horizontal station strips, clock taps, landing areas and wide channels. Recomputed183/183 macros inside outline, zero macro overlaps, zero overlaps with the30 declared station rectangles. Four actual referenced LEFs have OBS onlyM1-M4, permitting FT travel on M5/M7 over a macro without an obstacle-layer conflict. Maximum declared M7-only corridor track use .329<.6. The placement exception is specifically macro bodies under corridors away from stations; it does not exempt station/register/clock islands from macro avoidance.

Conditions: this review establishes fit and route-layer compatibility; it does not establish macro-to-core data reach, timing or PG. Reported worst bus-to-macro1432.4um requires the actual staged leaf implementation; no one-cycle connection over that distance is approved. H2 child r2r failures remain open. Full strict bind, event3 die clock, actual kit review and real-view sign-off remain their existing gates.
