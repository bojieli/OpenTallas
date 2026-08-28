# Requirement-by-requirement public-program audit

**As of:** 2026-08-28 UTC  
**Decision boundary:** this audit covers public, pre-NDA analytical and digital-
proxy work. It does not authorize a product architecture, target-node ROM macro,
wafer implementation, tapeout, price, or production-performance claim.

Status meanings:

- **Pass** — the stated public artifact exists, is reproducible, and closes its
  declared public evidence boundary.
- **Conditional** — useful work exists, but a named part remains synthetic,
  assumed, proxy-only, or dependent on external evidence.
- **Open** — a required artifact or measurement does not yet exist.

## Requested re-baseline objective

| ID | Requirement | Status | Concrete evidence | Remaining boundary |
|---|---|---|---|---|
| OBJ-01 | Replace the exploratory hypothesis-driven calculation with an evidence-first re-baseline. | **Pass** | `docs/METHODOLOGY.md`, `docs/SOURCES.md`, `docs/ASSUMPTIONS.md`, `src/opentallas/operations.py`, and generated `results/iso-node/` artifacts. | Public ROM and runtime inputs remain bounded extrapolations where no measurement exists. |
| OBJ-02 | Keep technology generations comparable: N6/N7 ROM with HBM2e versus A100 80 GB, and N4/4NP-class ROM with HBM3e versus B300. | **Pass** | `configs/hardware/technology_inputs.json`, `configs/hardware/n7_architecture_attribution.json`, `configs/hardware/leading_node_market.json`, and both `results/iso-node/*/REPORT.md` files. | WSE-2/WSE-3 remain feasibility anchors only; no cross-node performance inheritance is permitted. |
| OBJ-03 | Use official DeepSeek V4 storage and arithmetic roles instead of treating the model as pure FP4. | **Pass** | Pinned model configs/inventories plus exact format buckets in `src/opentallas/operations.py`; source pins in `docs/SOURCES.md`. | Numerical quality and achieved format-specific silicon rates require model-owner and target-PDK evidence. |
| OBJ-04 | Count work from released operator shapes and distinguish immutable weights from mutable KV/state. | **Pass** | `src/opentallas/operations.py`, `src/opentallas/profiling.py`, `tools/run_model_traffic_screen.py`, and `results/model-traffic/`. | Production allocator traffic, rereads, cache behavior, routing tails, and prefix/speculation behavior remain unmeasured. |
| OBJ-05 | Use realistic, source-traceable A100 and B300 execution/capacity/bandwidth assumptions. | **Conditional** | Public facts and assumption provenance in `docs/SOURCES.md`; explicit A100 deployment bounds and B300 FP32 sweep in the iso-node reports. | Reproducible exact-checkpoint GPU traces and counters are still EXT-04 in `results/PRE_NDA_READINESS.md`. |
| OBJ-06 | Explore aggressive leading-node ROM possibilities only when backed by public evidence or transparent derivation. | **Conditional** | Deterministic conservative/central/aggressive derivations in `tools/build_iso_node_studies.py`; fabricated-ROM and simulated 3D-METRO anchors are kept distinct in `docs/SOURCES.md`. | No public fabricated N7/N4 product-sized ROM macro establishes the selected density, read service, full-array power, or yield. |
| OBJ-07 | Redesign and account for low-cost on-wafer communication rather than assuming it away. | **Conditional** | `src/opentallas/noc.py`, `tools/noc_sweep.py`, `results/noc/`, two all-reduces/layer in `src/opentallas/analytical.py`, and explicit collective/cross-stage timing in both iso-node reports. | A target-node placed/extracted hierarchical NoC, clocks, skew, contention, power, and degraded-route evidence remain EXT-09. |
| OBJ-08 | Continue the public program autonomously while keeping internal architecture-correctness and external foundry, OSAT, model-owner, and silicon gates explicit. | **Conditional** | This audit, `results/DECISION.md`, `results/PRE_NDA_READINESS.md`, specifications, RTL, tests, and public campaigns. | Internal `COMP-01` remains open; the external gates listed in `results/PRE_NDA_READINESS.md` cannot be closed without new authority, partners, PDKs, measurements, or silicon. |
| OBJ-09 | Establish an executable checkpoint-to-chip mapping rather than validating isolated analytical and RTL proxies. | **Open** | `docs/EXECUTABLE_SYSTEM_RECOVERY_PLAN.md`, the `COMP-01` decision gate, and `SYS-FUNC-014`/`DV-EXEC-001` define the required semantic IR, complete checkpoint ingestion, physical images, microcode, service engine, independent checkers, and differential evidence. The exact-integer fixture under `compiler/`, `runtime/`, and `testdata/compiler/` now closes the first deterministic artifact/interpreter plumbing slice. | The fixture is not a real checkpoint or transformer layer. Target formats, complete DeepSeek operator semantics, physical placement, certified schedules, full-dimension real-checkpoint execution, complete-model execution, and representative RTL/co-simulation execution remain unimplemented. |

## Section 11 public pre-NDA deliverables

This table maps the eight deliverables in `rom-inference-program-plan.md` to the
current repository rather than treating completion of one artifact as completion
of the product.

| Deliverable | Status | Implemented artifacts/checks | Gap or qualification |
|---|---|---|---|
| 1. Pinned evidence inventories, executable analytical models, regenerated curves, and binding constraints | **Pass** | `data/inventory/`, `configs/`, `src/opentallas/`, `tools/run_iso_node_studies.py`, `tools/run_model_traffic_screen.py`, `results/iso-node/`, and `results/model-traffic/`; generated arithmetic audits pass 6,565 N7 and 3,921 leading-node checks. Here “executable analytical models” means reproducible equations and study generators, not an executable accelerator. | Audits close arithmetic identities/configured ceilings, not model execution, architecture correctness, or physical truth; those remain under `COMP-01` and the external gates. |
| 2. Complete system, architecture, numeric, interface, power, RAS/DFT, firmware, floorplan, verification, synthesis, and physical-proxy specifications | **Pass** | `spec/SYSTEM_REQUIREMENTS.md` through `spec/VERIFICATION_PLAN.md`, machine-readable contracts under `spec/*.json`, and `python3 tools/check_spec.py`. | Product budgets remain hypotheses until external target-node evidence replaces them. |
| 3. Bidirectional requirements traceability | **Pass** | `spec/requirements.json`, `spec/verification.json`, `spec/manifest.json`, generated `spec/TRACEABILITY.md`, tests, assertions, formal/coverage/fault artifacts, and bug/waiver ledgers. | Traceability demonstrates allocation/evidence linkage; it does not promote proxy evidence to silicon signoff. |
| 4. CPU routing, balance, NoC, fault/degradation, and sensitivity simulations with real/synthetic separation | **Conditional** | `tools/router_traces.py`, `tools/noc_sweep.py`, `src/opentallas/routing.py`, `src/opentallas/noc.py`, `results/routing/`, `results/noc/`, and fault/sensitivity campaigns. | Released/synthetic inputs are available; representative production router/KV/runtime traces are not. |
| 5. Open-PDK ROM/read-path experiments and target-node correlation gap | **Conditional** | `docs/OPEN_PDK_SELECTION.md`; locked SKY130A physical/PVT/mismatch/full-RC evidence; and an independently implemented IHP SG13G2 v0.3.0 chain covering 4/4 official model compilation replay, device smoke, zero-error DRC, unique ten-port LVS, exact via audit, capacitance PEX, 33/33 PVT/load cases, 5/5 detailed-RC semantic replays, and 165/165 RC electrical cases. Hashed reports/artifacts are under `results/spice/`. | This closes two local open-PDK methodology slices, not a compact macro or yield study. Compact/full-array resistance, IHP statistical mismatch/yield, target-node macro correlation, full-array activity, and silicon remain open; behavioral RTL is still not a characterized ROM macro. |
| 6. Technology-independent RTL with golden models, assertions/formal, tests, coverage, CDC/RDC, fault injection, and ledgers | **Conditional** | RTL under `rtl/`; formal, simulation, static, coverage, and fault runners under `tools/`; reports and machine-readable evidence under `results/rtl/`. | This is a public-reference digital proxy. ROM/SRAM/HBM/PHY/analog macros and product numerical quality are external. |
| 7. Reproducible synthesis and open-library physical proxies with constraints, reports, logs, tool versions, and black-box boundaries | **Pass** | `spec/implementation_proxy.json`, `tools/rtl_implementation_campaign.py`, and canonical fingerprint `87e057764094b9ed` close 7/7 cases, 2/2 generic proofs, 1/1 actual mapped proof, 2/2 physical proxies, and 2/2 post-route proofs. `tools/run_clean_rtl_implementation_replay.py` reproduced the exact source/tool fingerprint from deterministic clean commit `34a0d2ec…` and hash-verified 386 referenced artifacts. Reports are `results/rtl/IMPLEMENTATION_REPORT.md`, `IMPLEMENTATION_STATUS.md`, and `CLEAN_BASELINE_REPLAY.md`; `spec/verification.json` is `closed`. | The exact `numeric_e16_l16` scaling point uses a bounded structural Liberty mapping profile whose QoR is not directly comparable with default-profile cases. All results remain Nangate45 methodology/scaling proxies; target macros, numerical PPA, full-chip/wafer implementation, package, manufacturing, and signoff remain external. |
| 8. Pre-NDA pass/fail/open readiness report | **Pass** | `results/PRE_NDA_READINESS.md` and `results/DECISION.md` enumerate completed public gates, external evidence requests, owners, pass criteria, and phase-transition rules. | Product architecture freeze, test chip, tapeout, and production claims remain unauthorized. |

## Current disposition

Continue the internal `COMP-01` executable-system program, public evidence
acquisition, exact GPU/runtime benchmarking, compact-array ROM/read-path
refinement, and partner question packages. Hold product architecture freeze and
any target-node, wafer, cost, production-throughput, or Huawei-Tau-derived claim
until `COMP-01` and the applicable external gates close. Tau/韬 is a cross-layer
delay-reduction framework; any physical 3-D ROM proposal is a separate study with
explicit tier, bond, vertical-link, periphery, power, thermal, yield, repair,
test, package, and economic parameters.
