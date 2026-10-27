# E2/E6 final whole-band placements

Geometry PASS for the separate final e2_reach3/e6_reach3 successors only. Older original reach failures,partial-band failure,and PG-invalid placements remain failed/withdrawn history.

The source policy relocates the coherent4-bit c2+12-bit lt2 S-face capture band and sets each cell's destination-row orientation BEFORE its location. Actual final3_5_place_dp ODBs were independently read,rendered,and full-placement/SW-zoom images codex_0930_e2_final.png and codex_0930_e6_final.png viewed directly. The small cluster sits in open space just inside the S-face pin band;the body and centre remain open;no macro/wall;pin positions and interface are unchanged. No RTL or added cycle.

- E2:390,696all-timed connected arcs,33,850non-clock DFF input pins,max397.251um,0>405,0combinational loops. All28,988DFFs are row/rail-compatible,pin-window max3.0pins/um.
- E6:390,696all-timed connected arcs,33,850non-clock inputs,max399.303um,0>405,0loops. All28,988DFFs are row/rail-compatible,pin-window max4.3pins/um.

The full graphs include SET/RESET/scan/enable inputs as well as data D. Row checks accept rail-compatible R0/MY andMX/R180 pairs against actual OpenDB rows. Values/checkpoints are in codex_0930_head_final.json;pin summaries have matching per-type JSON. Read-only raw outputs intel2:/srv/opentallas-scratch2/claude/geom26/codex_r2r/e{2,6}_final_{r2r_all_timed,row_audit_all}.log.

Use new exact tags KV-CORES-CODEX E2 final and KV-CORES-CODEX E6 final on fresh route rows with the corrected hook/source and matching flow canary. Normal clock,timing,DRT,and routed LEC/sign-off remain; this is not SIGNED evidence.
