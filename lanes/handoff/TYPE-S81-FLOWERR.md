# TYPE-S81-FLOWERR handoff (18:1x 11-14)

Scope: 36 S81 'other flow error' types, excluding col_h9_r1/r2 and col_h10_r1/r2 (S81-COL-INHERIT).
Findings: 32 are DEDUP rows (duplicate kit identity, canonical twin RUNNING/QUEUED; not failures, nothing to relaunch); 1 FAIL (gunit__t1 pipeline traceback); 2 PENDING-DEP plan error (serdes PG domain, NEEDS-PLAN to DIE-S81-92); 1 ORPHAN (slice_station__t28 client gone).

## Items (identity | stage | status | class)
col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97 | gen_lint | DEDUP | DEDUP-twin-running
col_h10_r0_p4__t1__pvc9270d09 | place | DEDUP | DEDUP-twin-running
col_h10_r0_p4__t1__pvcc166a6d | preflight | DEDUP | DEDUP-twin-running
col_h10_r0_p4__t1__pvd11cc58b | place | DEDUP | DEDUP-twin-running
col_h10_r0_p4__t1__pvd8c0565f | place | DEDUP | DEDUP-twin-running
col_h9_r0_p1__t1__pv697f40c9 | identity | DEDUP | DEDUP-twin-running
col_h9_r0_p1__t1__pvb3e2a60a | selfcontained | DEDUP | DEDUP-twin-running
col_h9_r0_p1__t1__pvb49c16c8 | gen_lint | DEDUP | DEDUP-twin-running
col_h9_r0_p1__t1__pvf9acce4c | place | DEDUP | DEDUP-twin-running
col_h9_r0_p2__t1__cl0045af7b__pv6882e5ea | place | DEDUP | DEDUP-twin-running
col_h9_r0_p2__t1__cl0045af7b__pva2793873 | place | DEDUP | DEDUP-twin-running
col_h9_r0_p2__t1__cl0045af7b__pve183b536 | identity | DEDUP | DEDUP-twin-running
col_h9_r0_p2__t1__cl9f71e63d__pvef55eb84 | identity | DEDUP | DEDUP-twin-running
col_h9_r0_p3__t1__cl0cd90c0e__pv13474472 | identity | DEDUP | DEDUP-twin-running
col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b | identity | DEDUP | DEDUP-twin-running
col_h9_r0_p3__t1__cl0cd90c0e__pv8d734760 | identity | DEDUP | DEDUP-twin-running
col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a | identity | DEDUP | DEDUP-twin-running
col_h9_r0_p4__t1__cl8ef405e8__pv775e5cef | geom | DEDUP | DEDUP-twin-running
col_h9_r0_p4__t1__cl8ef405e8__pv91095415 | geom | DEDUP | DEDUP-twin-running
col_h9_r0_p5__t1__pv8995e794 | geom | DEDUP | DEDUP-twin-running
col_h9_r0_p5__t1__pvb22875c0 | geom | DEDUP | DEDUP-twin-running
col_h9_r0_p5__t1__pvc1b82625 | geom | DEDUP | DEDUP-twin-running
col_h9_r0_p5__t1__pvc6e5797f | geom | DEDUP | DEDUP-twin-running
col_h9_r0_p5__t1__pveda1ecc9 | geom | DEDUP | DEDUP-twin-running
col_h9_r0_p5__t1__pvee6f8140 | geom | DEDUP | DEDUP-twin-running
col_h9_r0_p5__t1__pvf71da13a | geom | DEDUP | DEDUP-twin-running
col_h9_r0_p6__t1__pv0012ba28 | identity | DEDUP | DEDUP-twin-running
col_h9_r0_p6__t1__pv082a7609 | identity | DEDUP | DEDUP-twin-running
col_h9_r0_p6__t1__pv87853a7e | identity | DEDUP | DEDUP-twin-running
col_h9_r0_p6__t1__pv9da72aa7 | identity | DEDUP | DEDUP-twin-running
col_h9_r0_p6__t1__pvb38a9d6c | identity | DEDUP | DEDUP-twin-running
col_h9_r0_p6__t1__pvbdbd69f2 | identity | DEDUP | DEDUP-twin-running
gunit__t1 | pipeline | FAIL | FLOW-pipeline-traceback (investigating)
serdes__t15__cla3d02796 | gen | PENDING-DEP | PLAN (PG domain holds no macro) -> NEEDS-PLAN DIE-S81-92
serdes__t4 | gen | PENDING-DEP | PLAN (PG domain holds no macro) -> NEEDS-PLAN DIE-S81-92
slice_station__t28 | queue | ORPHAN | ORPHAN client gone (relaunch)

## Result 18:3x
Classes: DEDUP 32 (twin running, not failures) · FAIL FLOW tool TypeError 1 (gunit__t1) · PLAN PG-domain 2 (serdes__t4, t15) · ORPHAN-but-live private job 1 (slice_station__t28, typeslicet28 on epyc8).
Launched: nothing (no design-class item in scope). ASKs to KIT-OPS-5 and NEEDS-PLAN to DIE-S81-92 posted in COORD-REVIEW-QUEUE.md.
