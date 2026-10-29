# HEAD landed regression after landslots/fclklat/ringstart

Source6b03fc6b22 (canonical main at start) includes landslots528a7d3edb, fclklat920b91086d, ringstart52a35ca59d. Reused exact DH17 CA/clock inputs, regenerated16landed wrappers+top+cells, gen strap audit3214bitsPASS.

DIE_SPINE vehicle (same measured bundle and ctl-driver substitutions as TOK-HEAD-LAND-2): TT and FF each PASS2positions, row21946 bits4173a558, fault0, GO→result8780 at both positions. Added latency0 relative to LAND2. TT bootcland_start124, landingready342. This is the landed spine regression; production HOST/HBC programme and full real-head release are separate. Existing LAND2 real-bundle/ROM/K controls remain evidence; no new claim that they were rerun here.

Runs intel1 codex-head-land3: TT unit410721-1793257381 exit0, runtime377.496s; FF unit428749-1793257474 exit0,371.688s. Builds units366790/396904. Runtimeobjects remain scratch only.

The first copied plan lacked relative cores/pin resources and sparse source assets; failures retained and diagnosed; required source assets restored without RTL change. Compose362external START-pin errors were already known and then fixed by canonicalc0fb metadata only: separate receipt codex/head-tstart-1029@7b05ef0d7 gives0contracterrors,346uses,16open launchoutputs. Later per-bus origin fix65d758764 has its own exactness/LEC proof; it is not silently included in this6b03-source run.

Input snapshots are compressed here; released checkpoint images and benchmark recipes are the prior main TOK-HEAD-LAND-2 and head_die_spine_1027 sources. No new physical sign-off/GRT/freeze or all-native-core token release is claimed.
