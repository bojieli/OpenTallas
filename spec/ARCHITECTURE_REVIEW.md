# Architecture review and gate disposition

**Review record:** AR-1.0  
**Review date:** 2026-08-27 UTC  
**Disposition:** PASS for public-reference RTL entry; HOLD for product silicon

## Scope reviewed

The review covers the analytical baseline through commit `82a2a23`, the pinned
DeepSeek/Kimi profiles, the Qwen3-8B 8K dense-control addendum, the B200/B300 x1,
x2, x4, x8, and x16 comparison normalization, and this specification package.
The decision is intentionally limited to public tools and non-NDA evidence.

## Evidence disposition

| Area | Disposition | Rationale |
|---|---|---|
| model identity/storage | pass for analysis | pinned revisions; safetensors headers fully classified; Qwen all-BF16 inventory independently checked |
| workload/KV accounting | pass for analysis | equations, tests, and explicit BF16 Qwen GQA assumption; no production quality claim |
| B200/B300 comparison | pass for conditional simulation | published system values normalized with explicit x1/x2 assumptions; no SKU claim for fractional configurations |
| target ordering | pass | Flash primary proof; Pro stretch; Qwen dense control; Kimi stress control |
| interfaces/numeric/RAS/DFT | pass for specification entry | exact records and planned checks exist; the 87-site dual-simulator logical fault subset passes, while macro/physical faults, numerical qualification, and full DFT closure remain pending |
| floorplan/PPA | conditional | budgets are hypotheses and proxy methodology, not characterized silicon |
| verification | conditional | bounded formal, two-simulator unit/integration, 87-site directed fault, unit coverage, and strict static/CDC/RDC artifacts exist; full stage/reticle/pipeline coverage, random fault/degradation, numerical differential, and synthesis-entry closure remain open |
| product authorization | hold | ROM density/bandwidth, HBM/package, PPA, yield, traces, security, and commercial gates remain open |

## Decisions frozen

1. Serious RTL may begin only from this reviewed package and its generated
   traceability record.
2. Qwen3-8B remains a dense control at 8,192 context tokens, with BF16 full-GQA
   cache and no speculative scenario; it is not promoted to a product target.
3. DeepSeek V4 Flash is the primary proof target. Pro is a stretch architecture
   target and Kimi is a negative/stress control.
4. TPU is outside scope. GPU comparisons are B200/B300 only.
5. Open-PDK synthesis/physical work is proxy methodology and is forbidden as a
   substitute for target-node signoff.

## Entry criteria for RTL

The machine checker must pass; all manifest documents and generated traceability
must be present; Qwen fields and partitions must match the analytical profile; no
normative TODO/TBD placeholders may remain; and the review commit must be pushed.

## Exit criteria before synthesis

The verification plan's DV-10.1 gate is mandatory: static/lint, two simulators,
formal, CDC/RDC, coverage, numerical differential tests, RAS/repair/DFT fault
campaign, deterministic build, and requirement evidence must close first. Product
silicon remains blocked even after public-reference closure.

## Open external gates

Model-owner checkpoint lifetime and quality agreement; production B200/B300 kernel
and router/KV traces; target-node ROM/standard-cell/macro characterization; HBM
beachfront and package/PI/SI/thermal/reliability; secure boot/DFT/ATPG; yield,
repair, cost, schedule, and commercial review. These are tracked as external
evidence requirements, not hidden assumptions.
