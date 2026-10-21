# S81 COLL SRAM-edge DRC collection

Exact original `dscoll_lane_e_s8nq-s8nq-67cd98218` is NEEDS_RTL: TT +40.71 ps, FF +4.82 ps, **55 DRC**. Preserve this failure; positive timing does not qualify a view.

The final routed report contains 40 Short and 15 Metal Spacing markers, all on M4 and all naming actual `ot_sram_1r1w2c_256x64_m1` instances. Correlation against all 55 actual final-DEF macro placements finds 52 markers at east edges and 3 at west edges; every marker centre is within 0.1495 um of the named macro vertical edge. `drc_summary.json` contains every original type/source/net/bbox/layer, actual placement and edge distance. Original report and route metrics are unchanged; final DEF SHA is pinned with its extracted placements.

The failed source's pre_grt.tcl sources grt_macro_top_layer but does not source sram_edge_guard. Existing structural successors `s8ng/s8nh` add the real macro-edge via guard around the straddling M5 GCell, retaining actual M4 pin access. Their gates already completed WARN and their automatic submissions are currently routing. `guarded_routes.json` pins actual source/job/host/run identities. Main ng uses depth6; fallback nh adds outside1.2. These are unqualified source candidates, not adopted views. A previous depth-only result is not closure.

No new gate, route, source change, depth sweep, CTS retry, timing waiver or selected-view change was made for this collection. Preserve all four guarded routes; inspect their exact final DRC/timing verdicts before deciding the next structural change. Once an actual current candidate is CLOSED, bind its exact parameter-free NTF master and source to LINK5; do not alias an old lane or infer CRED12 closure.
