Qcore r15a critical review packet (not approval / not submission)

Frozen consumed source: start99d98fa9836a66ea6aa08dfda2436ab30f1563d8 plus ten listed daemon helper overlays. Identity is exact_content_snapshot, commit=null; source_snapshot.json is authoritative, not merely start commit. ArchiveSHA 4f8ab9c4c07f62f5e98e5ba4dbfd1edde6947e21147130b294d3d94cdd9e8fe8 manifestSHA f6a9e3180ecbfcaa9891c3420fe7735bbeb1cec2b14433779b02d77ee18104fa. Actual gate generated11:30:16, collected11:44.

Gate WARN (0FAIL/4WARN), nativePASS max32, GRT overflow0 worstM2 54.25%. TT placement diagnostic reg/reg -76.1ps; this is not routed closure or a submission qualification. b/c remain live; stale local08:35 source-failure receipts are unrelated.

Eight-point SAFE facts (open findings intentionally retained):
1 Pins: gate geometryPASS1473 pins/rectangles/trackchecks; zero inaccessible/outside/missing. GeometrySHA0f56baab957b00a9dc781e66b3564db84d81dfa49c13ee206f5dca0408224aff. Existing capture-at-pin opt-out recorded in gate; reset landing max2 sinks, port1. Input/output timing contract unchanged.
2 Reach: textbook212.1um <405, tile302.4x280.8um. No fresh timing exception invented.
3 Fanout: actual gate mapped nativePASS max32 includes reset.
4 Depth: guidanceWARN~640.1ps/17levels pretree stage >600. Actual diagnosticTT setup -76.1ps, hold+37.9ps. Requires owner disposition/real route; no PASS assertion.
5 Storage: existing kit records8kbRF flop storage freeze waiver, reducer two SRAMs. This packet does not grant a new waiver.
6 Floorplan: PNG visually inspected: one abutted two-macro vertical bank uppercentre, connected surrounding cell band, no interior islands. Std20897um2+macro7783/core82413;29.2% placeable std density,34.8% totalfill,PD0.38. Aspect1.077. Pin-face channel actual21.6um horizontal/5.4vertical halo. Existing README says lattice; numeric origins(97.2,216.0),(97.2,174.96) are NOT both multiples43.2, so strict43.2 lattice criterion remains unresolved. Macro410M4pins/41umface ~10/um exceeds6, actual halo addresses escape but is not a literal density waiver. Tile faces documented<=3.6/um. No selfapproval.
7 Clock: rootcentreN,25427sinks guidanceWARN; TT/FF maxinsertion422.5/354.0ps; ALLspread87.2/89.6ps, owner boundary pinspread57.1/52.8ps (<80). Macroeachownleaf (onepin/net), TTarr335.3/336.2, FF264.4/264.9. Parent compensation not demonstrated here. io_hold_margin0.03 existing kit. Clock data preserved raw in gate.
8 Schedule: unchanged r13c RTL, static calendar,0 addededges. Existing kit cites PASS/mutants results/rtl/hbm_qcore9_1020; this collection did not rerun or invent source-specific bench approval. Frozen source/bench scope remains that original evidence, not new connected DS lowering.

No REVIEW.json written. No submit or main merge. Parent/root must resolve critical disposition.
