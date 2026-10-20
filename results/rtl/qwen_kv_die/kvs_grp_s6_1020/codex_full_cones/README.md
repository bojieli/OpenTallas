# Original GRP full sequential cones and lattice model

Original s6a/hs6a CTS databases both **PASS** full sequential-cone405um reach: 32 tiny SRAMs, 5248 endpoint pairs each, zero Liberty role errors. Macro endpoints use actual ITerm getAvgXY; standard cells use centres. All combinational gates are traversed by actual Liberty output-function dependencies. FF/latch, both synchronous SRAM types, and ports are stage boundaries. Only actual Liberty clock input pins and declared ck/hck input ports are excluded; resets and all data/control pins remain covered. Actual behavioural SRAM sources establish registered reads even though macro Liberty omits ff groups.

| Vehicle | Original max centre/actual-pin L1 um | Original conservative pin bound um | Best possible grown fixed-endpoint bound um | 405 matching | Hall witness |
|---|---:|---:|---:|---:|---|
| qkd_kvs_grp_s6a | 381.021 | 381.696 | 448.512 | 28/32 | 31 rings / 27 points |
| qkd_kvs_grp_h_s6a | 380.697 | 381.372 | 449.160 | 27/32 | 32 rings / 27 points |

The 388.8x432 model enumerates all36 legal43.2um bbox-lower-left points against actual fixed row SRAM boxes,20um die/row separation. All original standard-cell and port endpoints stay fixed; tiny SRAM orientations and identities stay fixed. There are no inter-ring combinational-stage dependencies, so the per-ring constraint matrix admits an exact bipartite-matching test. Neither vehicle has a32-ring assignment meeting405um; Hall subset witnesses retain every allowed point. The minimum bound includes the actual standard-cell BBox half-L1 proxy radius (maximum0.837um). Even subtracting that radius leaves lower bounds447.675/448.323um, above405.

This is **model-only fixed-endpoint infeasibility**, not a universal rejection of a new placement that moves standard cells or row macros. It authorizes no gate or waiver. The supplied minimum-origin-movement GRP plan has504.294um conservative full-stage reach. Its identities do not belong to hs6a, so applying that GRP assignment to hs6a fails closed; hs6a gets its own identity-preserving full-grid calculation.

`full_sequential_cones.json.gz` retains every ring pin/root/endpoint pair, actual macro pin coordinates, net names/IDs, orientations and all macro boxes. `summary.json` retains top30 original full-graph path witnesses. `candidate_projection.json` retains all ring-by-point costs, minimizing assignments,405 Hall witnesses, worst projected stages and actual-master path witnesses. BBox lower-left placement anchors differ from raw OpenDB getOrigin for MY macros; both are retained and projection translates actual pins using bbox anchors. Distances are endpoint Manhattan, **not routed wirelength** or a sum of combinational wire segments.

Read-only sources: original ep9 `/srv/opentallas-scratch/claude/ref_gate/qkd_kvs_grp{s6a,_h_s6a}-20261020-024704`4_1_cts.odb and exact src/cts.log liberties. Exact ODB/Liberty/behavioural-source/log/script SHA receipts are in the reports. Audit code source508fea73c; lattice/Hall codee24745d67; parent source branch base d3d7cdf03. Candidate input is a byte-pinned copy of the parent's then-uncommitted `candidate_origins.json`, not a source RTL change.

Initial missing private-import failure and initial physical-only TAPCELL role error were preserved before repair. Only instances with no non-power/ground pins are omitted as physical-only; no signal cell receives that exemption.
