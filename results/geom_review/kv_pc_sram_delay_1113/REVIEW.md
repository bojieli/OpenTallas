# Private SRAM-delay concept visual review

Reviewed concept.png directly, 2026-11-13. This is a sizing sketch of the existing31.968x17.280um macro, not an actual placed parent.

Five macros form a2x3 grid with the sixth cell reserved for standard logic/channel space. Macro rectangles do not overlap;17.28um interior streets and outer margin leave visible clock/data routing corridors. Wide data enters from west and exits east, clock branch point lies in the central corridor. Outline115.776x120.960um is a candidate local footprint only;878FF plus mux logic must be distributed in reserved standard space, and their mapped area is not known. This cannot establish parent slot fit, real macro pin alignment, pin density, tap reach, PDN continuity or clock balance.

Verdict: conditional concept feasible for private integration sizing; NOT a route approval. Render and review the actual parent placement with real pins/halos/PDN/clock before P&R. Added latency0; II1. See estimate.json and rtl/test/kv_r8_sram_delay/README.md for exact hardware/proof limits.
