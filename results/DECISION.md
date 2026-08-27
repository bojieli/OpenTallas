# Technical gate decision

**Decision: CONDITIONAL CONTINUE for simulation/test-chip work; no evidence-based
authorization for product silicon.**

The released-format midpoint has some DeepSeek low-batch speed and cost wins, but
the result changes sign by batch and depends on unmeasured ROM bandwidth, compute
density, HBM beachfront, and physical collective timing. It therefore supports the
next measurement phase, not the brief's product-level performance claims.

## Evidence currently passed

- Without speculation, 6 of 20 required DeepSeek points beat the fastest same-batch GPU configuration under midpoint assumptions.
- With the assumed five-candidate/70%-acceptance speculative midpoint enabled on both sides, only 2 of 20 required DeepSeek points retain a same-batch speed win; acceptance and draft cost are not measured.
- 11 of 20 required DeepSeek points beat the cheapest feasible same-batch GPU on modeled partial TCO (hardware/NRE amortization plus active electricity).
- Flash B8 no-speculation ROM/GPU ratios are 1.14× at 200K and 1.08× at 1M; Pro B8 ratios are 0.81× and 0.83×, respectively.
- 4 of 4 DeepSeek B64 points are feasible and lose on same-batch speed; no DeepSeek B64 speed case survives the midpoint.
- Exact checkpoint manifests/configs are pinned and fully accounted without full payload downloads; main-decode, draft-only, and resident-only bytes are separated.
- Closed-form MoE coverage matches uniform trace simulation; correlated stress traces expose the load-balance tail.
- Hierarchical collective and placement sweeps execute on CPU and report their own lower bounds.
- Pipeline capacity charges batch × stages resident sessions, so infeasible high-context points are no longer reported as throughput wins.

## Gates not passed

- No foundry measurement establishes ROM bit density or PB/s-class full-array read bandwidth.
- No synthesis result establishes the multi-POP/s per-wafer compute density needed by the provisional ultra tiers.
- No production router or GPU profiler trace establishes engaged bandwidth, tail imbalance, or actual KV HBM reads.
- The model owner/checkpoint-freeze commitment has not occurred.
- Packaging, beachfront HBM, yield/repair, clock/power delivery, cooling, NRE, and unit cost remain assumptions.
- Partial TCO excludes staffing, financing, networking, floor space, maintenance, replacement inventory, and idle-period electricity.

## Target ordering

1. **DeepSeek V4 Flash** as the primary proof target: smallest measured image and strongest low-batch margin, while the speculative result makes clear that the margin still needs trace validation.
2. **DeepSeek V4 Pro** as a stretch architecture target, not a current product-performance claim: it requires six released-format midpoint stages, loses at B8, and loses even at B1 under the assumed speculative midpoint.
3. **Kimi K3** as a negative/stress control: its dense MLA traffic makes 1M context beachfront-bound and it does not show a robust speed case here.

## Next pass criteria

Continue only if circuit simulation/test macro and synthesis put the required read/compute point inside a power/cooling envelope, and if measured V4 router/KV traces leave ROM faster than the best B300 production point at the intended batch. A checkpoint-freeze commitment remains an independent mandatory gate.

## Provisional tier audit

- B=1: brief target 7,000 tok/s; collective/pipeline-only ceiling 26,843 tok/s; grid maximum 8,538 tok/s (compute_C5).
- B=8: brief target 5,500 tok/s; collective/pipeline-only ceiling 4,450 tok/s; grid maximum 1,921 tok/s (kv_beachfront_C8).
- B=32: brief target 2,250 tok/s; collective/pipeline-only ceiling 1,153 tok/s; grid maximum 488 tok/s (kv_beachfront_C8).
