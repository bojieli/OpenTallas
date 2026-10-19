# Fault candidate reset loads: admission OPEN

The manifest enumerates all1351 new closed qkd_astk_fault_join rst_n pins from the356-source GEN4 candidate. It traces only exact qkd_rlys_1 registered reset stations, stopping at explicit host outputs(258targets) or qkd_rst_region{,_pr} release outputs(1093targets). Every root and intermediate node has its actual native output coordinate, bit, clock, root identity and measured depth. Target depths are1..36 relative to the identified output. This is not a common global release epoch or a physical branch admission.

The additive planner must find an earlier existing source at depth d that can reach target D in exactly D-d registered edges with legal native clock/phase, loads and <=405um final reach. Preserve every old load and release edge. Existing aliases must not directly drive distant new loads. Pin coordinates and plan are input-hashed; unknown roots, cycles or duplicate reset relay drivers refuse certification.

The final sticky collector must remain reset until every source clear has propagated through the whole fault path, accounting for source/reset cohort skew, reused transport stages and all downstream consumers. HOLD128 or abstract quiet182 alone proves neither clear safety nor fault retirement. The compiler must separately price the complete functional-check cutoff and full fault path into STATUS, while global sticky health remains continuously live. No masking, source clearing at cutoff or reset timing waiver is emitted here.

Four focused tests cover trace depth, native target placement, regional-root identity, unknown-root blocking, reset cycles and multiple drivers. Native branch construction, clear-cohort simulation and exact timing remain OPEN.

The complete existing_reset_nodes census includes2751 existing stations/root outputs across ALL branches of the relevant reset roots. It includes alternate branches outside the new-target ancestry, permitting a complete necessary source-node feasibility check. Every node carries root_id and normalized clock_bit alongside the original clock expression. An alternate-branch fixture verifies this coverage.
