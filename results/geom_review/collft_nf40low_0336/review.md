# coll_ft near-face FF-only placement trial

Viewed planned_nf40low.png. Scoped PASS-COND for fresh PLACE-only diagnostic under parent model approval. Overall geometry remains FAIL; no GRT or route clearance.

Six shallow edge strips retain the original 0.4 reservation, 11645 exact bit-correlated FF anchors and 54 protected status/START/reset sites. Pin p90 24.57um, collapsed relay chains 0. Residual pinmax163.26um, 138 START/reset captures (136 START,2 reset), clock reach361.65um and root-port tap load3056 remain unresolved. Transplanted old combinational placement gives col_v3.693; only fresh GPL can measure this candidate. Original failed results remain unchanged.

The rejected dense strip used55.95% raw fill and violated0.4 reserve. Intermediate18.9um strip failed analytic packing after2474 anchors. Accepted analytic model lowers south strips to4.32um and raises north strips to989.28um while preserving full reserve footprints and protected cells.

Local shared-tool proposal: opt-in named FF anchors, global bit mapping64*dch+localbit for ring-read FFs, reserve >= actualWidth/0.4, fail on missing/oversized FFs. Apply before GPL so all unfrozen combinational logic reflows. The kit-local helper does not change RTL or cycles; no shared generator edit is proposed for immediate merge. Expected actual names may differ after synthesis; the helper fails closed and any failure must be diagnosed before retry.

Exact paths: intel2:/srv/opentallas-scratch2/claude/codex-collft-0336/gen_nf40low_ff/coll_ft__cla4a25d77/coll_ft__cla4a25d77. Actual G1 required after PLACE, with failures retained.

First pilot stopped before GPL with ODB-0360 because protected FSTART was already FIRM. Distinct ff2 kit changes only transient FIRM→PLACED→FIRM around same anchor orientation/location, matching shared cland_put behavior. All coordinates, reserve, RTL and downstream gates unchanged. Original failed kit and log preserved. PLACE-only scope remains.
