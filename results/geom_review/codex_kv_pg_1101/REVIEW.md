# KV sys_c macro PG connection

Viewed `sys_c_pg.png`, rendered from the existing macro LEFs and plan using `plan_review.draw_base`. PASS-COND for normal prototype gates. All six footprints and 4.32-um halos remain disjoint; no placement, pin, tap or external supply changes. The four replay SRAMs and profile ROM have M4 PG pins and connect to existing M5 straps; the existing UCIe model has M6 PG pins and connects to existing M7 straps. `core_pg_connect: true` invokes the already supported per-LEF connection form; all six previously unconnected macros are now covered by an explicit macro grid.

This fixes the G0 PG continuity warning. It introduces no RTL, scheduling or latency change. Final physical PG/ERC and ordinary routed sign-off remain required.
