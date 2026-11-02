233.28 × 302.4 directional CTL geometry PREP

This remains PREP. No GEN, floorplan, placement, STA or route was run for this outline. Current-source parent composition stays HELD on the historical6849-pin namespace; canonical7076 POR is not adopted.

The233.28×302.4 footprint reallocates width to the limiting horizontal routing direction. W+H remains535.68um, preserving the rectangular L1 corner bound. Exact retained SYNTH logic9589.44096um² plus six SRAMs12538.48896um² gives16.53% logic-only fill. Parent origin967.68,172.8 is a strict subset of the old371.52-square slot. Globalck/rst_n roots are unchanged. Boundarypor_n and all face coordinates require parent requalification.

Same six R0 SRAMs at x25.92/155.52 and y43.2/129.6/216 enlarge both horizontal halo-open streets29.16→37.8um. Central vertical street68.664um; edge streets21.6/21.144um. Global changes relative the actual250×285 native case are X±17.28 and Y−8.64/0/+8.64, all on the existing PG phase. Max macro-centre pair302.4um; conservative macro-corner pair394.656um. W/E pin peak falls9.2→8.7/um; N6.3/S1.8 remain pin-access budgets, never route qualification.

`FF_site_model_PREP.json` uses actual native source connectivity and conservative translated prior-row/TAP intersections:18,768 existing FFs, same54 physical master selections,350 extra nearby data-FF density moves, each constrained against all actual sequential neighbours at400um. Typed reach390.53/0>405, pinp9028.98/max145/0unregistered, FF-only empty.4762. These are modeled source-phase sites, not new native ROW/TAP qualification.

`source_cut_model_PREP.json` recalculates the NEW macro/pin/FF net boxes and native-phase PG prediction. Whole cuts H.56769/V.486 are sized, but LOCAL proxy remains FAIL: H1.715/V1.700. The separate.57225 edge/street coupon holds OLD net boxes and OLD macro cut shadow to isolate added444–558 derated tracks; it is not a new-geometry PASS. Full current-source local hotspot repair is in../kv_ctl_hotspot_1102. No threshold or classifier is changed.

The source-cell constructor is pinned to a60a58293; pinning reproduces the identical saved cell model. Actual new native ROW/TAP/PG and subsequent placement, buffer counts, pin access, timing and routing remain open.
