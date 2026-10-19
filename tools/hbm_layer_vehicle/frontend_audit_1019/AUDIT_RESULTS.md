# SVG frontend audit receipts

Read-only audit; engine RTL unchanged. The cache remains frozen at bb7c14755. Full frontier is immutable a7da66a75 with old issuer; current cohort issuer and collector are distinct825607a54 snapshots. Exact top/params/sources/clock declarations live in each JSON spec. The strict source-bound recursive BUF/INV rule counts unique terminal(cell,type,inputport) loads and treats C as clock only on sequential cells. No resynthesis was used for reclassification.

| Exact scope | Max data/control | Nets >32 | Max reset | Raw reset input load | TT stdcell area um² |
|---|---:|---:|---:|---|---:|
| Frozen safe cache |32|0|25|8|5751.50382|
| Old issuer, a7da baseline |415|31|303|303|1067.60592|
| Current cohort issuer, ID_COHORT1 |414|33|323|323|1084.48956|
| PC owner, LB2/OWNER_AW5 |162|104|1629|1629|981.61308|
| Collector default XRT2 |94|5|127|2|236.44386|
| Collector actual l17 XRT1 |96|5|135|2|235.18998|
| Full baseline frontier |2352|616|6510|stream880 / HBM1|10791.4599|

Max reset includes internal distributed nets, so low raw reset count does not qualify the collector or frontier. The current collector does have all79 published ID bits (valid1+layer8+IDs54+cohort16) and fault on FF Q. This establishes a native output boundary only, not a safe internal implementation or its route_act deadline.

Both issuer versions have registered reserve fields but combinational reserve_v and reserve_total, start_v/bank/epoch, and program_start_v/base/limit/loops/context. Owner k_v, k_addr, length low bits, response_ok, response ordinal/epoch/bank and issue_done are combinational; k_tag and fault trace to FF Q. Full frontier command83 and output trace faces are Q, but k_v/address/length/kr_rdy and aggregate fault remain combinational. The cache output trace is1088 SRAM Q plus11 FF Q in packet1099, and six additional status bits on FF Q. Every SRAM output is the already qualified registered macro read output; this audit does not infer registration from an arbitrary blackbox.

The full frontier retains9308 stream clock sinks,145 global HBM sinks, four distinct PC HBM roots with1600 sinks each, and four distinct pair HBM roots with four sinks each. These count actual mapped FF/memory clock ports inside the audited hierarchy. Qualified cache/pair/calendar blackbox clock pins and their internal state are outside these counts. Each vector clock bit is reported separately in `frontend_boundary_summary.json`; aliases alone never merge clock roots. Inputs into blackboxes remain actual physical pin loads in the fanout audit.

Evidence:

- `original_mapped_census_summaries.json`: exact original source hashes, standard-cell area and known/unknown-cell census. Full frontier has only the three explicitly excluded types (cache1, pair4, calendar1); all standalone maps have unknown0.
- `frontend_collapsed_reports.json.gz`: full recursive terminal-pin reports for baseline issuer, PC owner, current issuer, default collector and full frontier.
- `frontend_collapsed_summary.json`: compact mapped hashes and worst loads.
- `frontend_boundary_summary.json`: input native-capture classification, output Q origins and per-bit clock roots for those same maps.
- `collector_l17_audit.json.gz`: exact actual-l17 collector params, source hashes, original census, recursive loads and Q/clock audit.
- `cache_bb7c_collapsed.json.gz` and `cache_bb7c_boundary.json`: frozen cache no-resynthesis reclassification and Q trace.
- `owner_link_model_receipt.json`: fleet PASS1,131,520 legal source-topology cases over all64 row counts, four PCs, eight physical three-bit SM straps and four row-low values. Wrong-lane and wrong-target model mutants each rejected1,131,520 times. This is not a cycle miter or a reset/tag-lifecycle proof.
- `owner_sram_option.json`: exact32x64 dualclock primitive view hashes, physical area, and explicit candidate buffer/state costs.

Mapped run roots are on ot-epyc8 under `/srv/opentallas-scratch/claude/codex-frontend-{29a6dc56a,25455d885}-<spec>/map/<top>`, and actual l17 collector on ot-epyc7 under `/srv/opentallas-scratch/claude/codex-frontend-0aa17a770-collector_l17_current/map/ot_hbm_router_ids_static`. Frozen cache mapping stays at `/srv/opentallas-scratch/claude/codex-cache-map-bb7c14755/map/ot_hbm_svc_static_sm_packed136_native_safe`. ORFS image digest is16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29, RVT TT ABC target833.333ps; this is structural evidence, not placed timing/route qualification.

A future registered frontend must close the source chronology, all captured event/data association, bounded readiness reservation, fixed clock/reset graph, current cohort semantics and compiled launch deadline. Candidate stage/state equations are in `REGISTERED_FRONTEND_MODEL.md`. No wrapper-only qualification, gate or submission is claimed.
