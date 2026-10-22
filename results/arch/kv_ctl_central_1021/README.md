# Central KV control placement and real relay corridors

Exact parent283f5922a; optionalOT_KV_CTL_CENTRAL=1, defaultoff. Coupled recipe: OT_KV_PVT_HUB_CLEAR=259.2 and OT_KV_SN_LIFT=604.8 (old432). Keep all other exactdsg3c432flags. No RTL/source calendar waivers.

Baseline PREP failed CTL->HROOT_ES stage48 at(11394,20379.6),8125um remaining. Its portraitCTL was(6565.536,25961.04), remote fromSroots. More fundamentally, native groups left only100.248um control corridors; a2524bit standard row is151.2um wide and the pre-expansion pin frame125.28um high.

The candidate grows actual die width345.6um, moves engine geometry and native group anchors172.8um per side, relocates actualCTL westofPVFIN, reserves a tile-free216um horizontal band, and sendsS-root CTL words directly through this band instead of visitingN-stacktop. ExistingPVT_HUB_CLEAR expands the real horizontal macro gap; SN_LIFT moves actualN macro rows. The channel reservation applies only to future tile placement, so relay planners may enter it. A fail-closed guard rejects existing frames in the crossing band.

Actual pre-relay construction ran on ep5 throughot-run8GB, unit869414 exit0:1122instances; CTL(5473.008,12467.52),345.576x475.176. Allfourcontrolchannels273.048um. Horizontalband(1296.84,13106.88,11228.568,216), zero frame intersections. Complete frame-pair scan:0old/0new overlaps; area+12.1698256896mm2. Receipt and snapshots committed. Waypoint tests on actualsnapshot passed ep5unit945823: defaultoff matches original paths, directS-root paths below14mm, reverse paths exact, EMB paths unchanged.

The first geometry variant withoutSN_LIFT604.8 failed the independent band inspection: six N-engine frames crossed band13106.88..13322.88 (astk_WN,head_WN_0_0,head_WN_4_0 andE counterparts). Its original central.log/err are retained. Lifting actualN rows clears those intersections; merely declaring a gap did not.

This is GEOMETRY ONLY. The actual new die is13822.272x28475.28um. Bounding rectangle fits33x26mm only in90degree orientation; coherent actualGEN/frame/pin-map/LEF-grid/SerDes/package-facing transformation remains owed. No reticle qualification is claimed by swapping dimensions. Actual GEN must derive relay counts/ages and check matching-bit reach, reset/native/calendar/bind/clock. No GRT, timing closure or performance gain is claimed. K-DIE owns the full successor and reticle contract.
