Native explicit-mesh terminal via coupon

Source: codex/qc-clock-1027@93362be6bb, including entry terminal layer support. Geometry image review.png viewed before native execution: isolated separate 30x20um vehicles, no macro/other-net collision. Mechanism-only qualification, no clock-tree driver, routing, RCX, STA or die claim.

PASS unit oth-ubuntu-2325388-1793120560 on intel2, 8GB admitted. Actual E.routed_mesh_tcl dbWire encoder, native OpenDB readback: M9 branch to M5 endpoint has exact VIA89/78/67/56 stack at [15,8] plus turn/crossings (9 total); M8 branch to M9 endpoint has VIA89 at [8,10] plus turn/crossings (6 total). Every graph metal edge is present and both BTerms keep exact declared layer/location on the same actual net. Native ODB files retained.

Initial unit2314011 failed in coupon setup before encoding because place_pin required tracks. Missing ODB then caused reader abort134; logs preserved under initial_missing_tracks. Fresh successor adds explicit M5/M8/M9 tracks and fail-fast shell. Source encoder unchanged. Default NDR warnings on lower layers use existing tech widths. No flow defaults changed.
