# S81 G4/G8 service geometry feasibility

GEOMETRY ONLY, NOT A DIE RESULT. Coordinator authorized G4 primary and G8 fallback after SVCFIT showed no service fits 122 frames. Parent owner directives prioritize closure and allow frame/die cost. Baseline source is immutable ep6 `/srv/opentallas-scratch/claude/s81-die11/mu7v2c/plan/plan.json` (4ae44d2dd chain).

Reproduce: `python3 tools/s81_dv/service_band_candidate.py --plan BASELINE --groups 4 --out OUT` (then 8).

Actual rectangular child packing: rest1728x1555.2 + 43.2um cell-row separator + attention1296x2160 (G4) /1814.4x2160(G8). All16 regions in one south row. Slots1728/1814.4x3758.4. G4 service103.912mm², G8 109.108mm²; unchanged legal31968.5x25000 outline (799.2125mm²). Real child macro geometry/CTS remains to be built.

Both retain96 frames/880 ROM slots vs122/1130; remove actual colliding frames, move S slices330.08um north, and reserve granted bk_sel907.2x3283.2, seqhost432x777.6, gunit950x1469. Both have zero block overlaps or outline violations (0.05um tolerance for the preexisting facts width rounded0.012um below SerDes edge). No reticle growth. Reader strips still require joint reservation. Exact inventory qualification is owned by token_qualification; no scaled stage or performance claim is made.

Files intentionally omit links rather than claim stale endpoints are routed. Deleted frame links, moved endpoints, corner-reader placement, actual service clocks and <=405um relay channels all need regeneration before trial GRT. Composite boxes do not establish internal relay cell rows. Stage/calendars require exact allocator qualification. No strict-bind/GRT/STA/IR closure claim for these candidates.

Baseline SHA256: 0e1a4250943e5adf78c39e576908dfb9870cdd116d2bbe868e7964ec26f45641
