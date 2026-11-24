# S81-OPEN-LEAFBAND handoff (Opus 5.5), updated 11-23 21:58 PST

JOB (COORD 19:2x): fix the c7a LAND-CAP finding (16 band x hard-core overlaps, 12 fills >= 0.9, 12 leaf types) -> ROW-REBASED for c8.

STATE: the row is delivered and IN c8 (INT 21:52, ba9b277a852b; TGR5 0 conflicts on top of it).
- Cause: step 03 r2_near moved all 27 leaf hard cores (C4 geometry) and kept the B1 band rects (bisect E9 s81-open-leafband/bisect.log).
- Row: E9 s81-open-leafband/ops_leafband_v1.json 8f2a6b3cedb4 (leafband_fix.py, cland_band_fit.resite). c7a + row -> p5 0d5a32d7f4ab (full tail = fast path, byte-identical). LAND-CAP 0/0. PRE adds 0 findings (147 = 19 ANCHORDRY + 128 GEOM from KVLEAF v2 step 10, already reported to SLICE/INT).
- Findings posted: (1) the amd1_tree ELAB needed B1 dsdv_svc_mem_ar.sv 124d9bd0719a (land_mem); INT carried it 20:20. (2) KVLEAF v2 -> 128 GEOM-STATION-IN-CORE.

RUNNING: E10 scoped strict on the 12 types (lb_scope.sh fast2, unit oth-ubuntu-2252819-1795493817). It is in the type_define_effect variant elabs, ~25 min per define. INT's c8 scope covers only t40 of my 12 types, so this run is the evidence for the other 11. Post SCOPED result -> INT.

CLEANUP after the scope result: ot-delete E10 s81-open-leafband/tree (100 GB; E10 disk is tight) plus gate_fast/gate_fast2; E9 s81-open-leafband/v1, fast, tail_v1 (215 MB plans).
