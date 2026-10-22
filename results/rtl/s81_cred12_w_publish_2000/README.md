# CRED12 W lane publication

Bounded main-based publication of the existing CLOSED W lane record a595e6dab for job dscoll_lane_w_s12h-dscoll_lane_w_s12h-c8c2b1bfe. The original record, gate failure/success artifacts, views and witnesses are preserved. No new route or view alias was created.

The ten RTL source blobs match closed-source c8c2b1bfe exactly. Only two shared source files differ from main: CORE_CRED defaults to8 and LOCAL_POP defaults to0. Static specialization of those default branches, with comments/whitespace removed, equals the previous main source exactly. source_identity.json records both identities. This establishes default behavior preservation; it does not claim that a CRED8 view has the new CRED12 source hash.

Qualification reused: original CLOSED record reports TT+25.87ps, FF+1.15ps and DRC0. Behavioral production-shape reach bench and mutants5/6/7/8 are retained under results/rtl/s81_lepab_regional_1021/peer_m*.log; daemon fail witnesses and original verdict live under results/closure_loop/dscoll_lane_w_s12h-dscoll_lane_w_s12h-c8c2b1bfe. Replay uses tools/s81_slice/coll_reach12.sh with Verilator5.050; the referenced w_s12g spec supplies the same source list as w_s12h. Its spec alone is included as a replay input.

The actual floorplan PNG was viewed during collection. The physical contract remains the inherited pin-bound725.8x583.2um55-macro lane. Bind the new view only at CORE_CRED12. The central integration owner publishes main.
