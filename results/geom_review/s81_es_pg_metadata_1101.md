# S81 ES0/ES1 PG metadata review — 2026-11-01 05:53 PST

Verdict: PASS for the metadata correction. The remaining cut-density failure class is open separately.

Viewed `s81_es_pg_metadata_1101.png` (tools/die_plan/render.py render function, unchanged partition/clock placement) and `s81_es_pg_metadata_detail_1101.png` (PHY-domain closeup). Both ES domains contain their placed MY logical PHY rectangles. IO and PHY bump rectangles now coincide with that existing footprint; the core VDD strips are disjoint from VDDPHY and connect around its west/south faces. No block, station, pin, channel, tap, or PG stripe moves. The existing floorplan data flow, abutting pins and channels are unaffected. The unchanged 63.64-um guard remains around the PHY footprint where the domain includes it. PG grid layers, width, pitch and domain outlines are unchanged.

Correction: reapply the existing `ws3_1029/pg_es_fix_1029.py` derivation to the current source and also update its previously missed `die.io` rectangles. ES0 IO capacity is corrected from the whole-slot 152 to the physical 102 sites (26 signals); ES1 retains 102 sites. `die_io.check_pg_domains` reports 6 ERRORs before and 0 after across 14 domains; the 7 pre-existing PHY_SHORT warnings remain. The existing matching-domain IR receipt `physical/die_plan/s81/ws3_1029/pg_es_fix_ir_1029.json` reports worst core VDD 17.59 mV and VDDPHY 9.82 mV. This metadata repair does not claim a new routed or IR pass.

No RTL, latency, clock, partition geometry, hard-core placement, or plan sidecar changes. New cycles: 0. Remaining S81-007 work: 12 lower-layer cut-density findings across 10 unsigned types, requiring physical track reservation rather than a scalar budget-only change.
