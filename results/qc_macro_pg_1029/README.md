# Actual native QC macro PG access

The h800 physical source has 377 macro instances, 754 native supply terms and 137306 M7 PG pin rectangles. Its prewire ODB has no PG special wires and those 754 terms are unbound. This packet implements explicit, physically enclosed M7→M8 VIA78 access rather than relying on logical global connection.

`plan_joins.py` finds direct crossings of the actual native M7 pin with same-net canonical M8 rows. The actual technology VIA78 pads are M7 [-16,-27,16,27], M8 [-27,-20,27,20] DBU. 135616 native rectangles have a direct crossing; 1690 short fragments do not. No metal is extended beyond native pins or canonical stripe geometry. `check_select.py` deliberately selects a bounded **one contact per macro term coupon**, checks actual h800 signal/OBS plus the 484 joint clock reservations, and allows a hosting M7 OBS exception only when the whole via enclosure is inside that host's actual same-net PG pin.

All754 selected contacts passed; no obstacle rejection or failed term. The coupon was rendered and personally viewed before materialization (`results/geom_review/qc_native_macro_pg_coupon_1029.md`). `emit_coupon.py` constructed actual special-wire geometry and term bindings in a copy of the source ODB. `read_coupon.py` re-read that ODB and traced every native term through an actual VIA78, same-net M8 stripe, VIA89 and M9 stripe: **PASS754/754**, actual754VIA78/754VIA89/232grid rectangles. No RTL/cycle change.

This is a bounded physical connectivity result. It does not establish distributed current capacity, all native PG fragment continuity, IR, die PG closure or SIGNED. The 1690 short-fragment direct-crossing misses are retained; all1690 have a rowphase-legal possible M8 gap bridge to same-net M9, pending full obstacle planning. No such bridge was materialized by this packet.

Run root on intel2: `/srv/opentallas-scratch2/claude/codex-qc-macropg-1029`.
Actual input: `/srv/opentallas-scratch2/claude/codex-qc-1029/baseline26/mechanics119_h800/clock_grafted.odb`.
Actual geometry: `codex-qc-mesh5-1029/census119_h800/geometry.json`.
Clock reservations: `codex-qc-mesh5-1029/joint_seed/joint_clock_reserved.json`.
Canonical PG rows: `codex-qc-pg-access-1029/census119/pg_rects.json`.

Jobs terminal via ot-run: inventory2659690, obstacle selection2778568, materialization2814656, actual readback2830212. All exit0. Original source ODB untouched. Coupon `coupon_v1/coupon.odb`; native full candidate `direct_v1/join_plan.json` (135616contacts+1690misses retained); selected plan `checked_v1/selected_plan.json`; actual path receipts `coupon_v1/connectivity.json`.
