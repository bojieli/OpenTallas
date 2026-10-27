Native N4 extraction smallest cut

Exact surviving source is bundled in source_snapshot.tar.gz from epyc2 hbm-mu-quad-3-1027/n4rtl/bundle. The test instantiates original hub N4EXT0 and two actual ot_hnx_fused_tnode plus hub N4EXT1. Stable zero pad straps, fully warmed reset, one833psclock. It compares UP headers (including fin with valid0), valid data, four DOWN buses, done/fault/busy. A positive rounding witness detects altered pairing; same binary +MUT_PAIR gives32 errors. Baseline714checks0errors. No added node/calendar edges.

Scope excludes32 actual leaves, VM bank transactions, physical stations, routed clocks and whole FUSED/kernel/token completion. The inherited fulltree baseline remains failed for both internal and extracted configurations; original pre has no output writes, post writes fullsectorcount with wrongdata and no done. These are separate from the old runner line78 sd-unbound problem.
