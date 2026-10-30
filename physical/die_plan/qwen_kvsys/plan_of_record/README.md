# KV plan of record: event28w_c

`plan_c.json` is the current event28w_c plan with only filesystem references relocated to this directory. The original byte-identical plan is preserved in `plan_c.original.json.gz` (SHA256 16980115aa4afb56; full SHA in relocation.json). `eW_sidecar.json` is the unchanged native crossing sidecar. `pins/` contains the 36 exact pin tables referenced by the plan; relocation.json maps every source path and payload hash.

This package replaces host-dependent references for consumers; the older ../die_plan.json is historical and does not define the current interfaces. No geometry, core placement, pin value, clock, reset, or latency change is adopted here. The clock.mesh.sites_file reference is historical and its payload was absent beside the source plan; this package does not claim a fresh clock qualification. Existing clock results are on the separate kv_e26a_w243 tree.

Known core-view coverage: q0 and q3 exact plan pins match their signed views. E0 fMX pins match 28 of 38 instances; ten raw-table/MX entries require the explicitly reviewed orientation correction or another signed view. RX frozen outline is 259.2 square; 236.736 trial profiles do not match this plan. SD physical-macro declarations and the measured band/reset fixes remain separate pending fixes. Do not infer die SIGNED or completeness PASS from this data publication.
