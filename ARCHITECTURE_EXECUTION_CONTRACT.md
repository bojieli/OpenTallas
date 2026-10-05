# Architecture ownership and verification contract

Status: adopted workflow; quantitative implementation contract pending review.

## Objective and authority

Optimize demonstrated single-user decode latency for DeepSeek-V4.1-Flash and Qwen3-8B, separately for ROM and HBM weights. Multiuser utilization is secondary. Exact arithmetic, finite storage/traffic, physical feasibility and power constraints are mandatory. No arbitrary token-rate target is assigned.

The root agent owns the complete architecture: partitioning, tensor placement, storage representation, interconnect, resource allocation, pipeline latency, clock assumptions and budgets. Subagents propose, implement and verify bounded portions. A proposal is not adopted until root records the decision and affected contracts.

## Current architectural decisions

- **2026-09-29, method (binding, see AGENTS.md):**
  - A unified microarchitecture analytical model sizes every block before RTL or place and route. It covers compute and communication intensity, port bytes, boundary bits, routing tracks, replicas and their multiplexer cost, slot fit, and token-latency share.
  - The floorplan comes next. Then one hardened element sized to the full goal is replicated.
  - HBM comparators replicate a GPU organisation; only the ROM designs are novel.
- DeepSeek ROM weights remain near local digital MACs. Wide operand buses stay within explicitly placed local groups; partition crossings require budgeted interfaces.
- Adopt bit-exact output-row splitting for expert/shared w2 and the specified fixed-order wo_b reduction. Arithmetic order is part of the interface.
- HBM stores packed KV. Index, selected KV, window KV, RoPE and comparator weights require a complete region and shared-service ledger.
- Initial integrated acceptance is a single-user real layer path. Golden-preloaded selected IDs or rows validate arithmetic only.
- Qwen ROM/HBM use the same arithmetic/program contract. Source-equivalent compiler restructuring must pass identical-source exact controls before scaling.
- Current clock targets are verification constraints, not achieved operating frequencies. Unclosed paths cannot contribute achieved-rate evidence.

## Required implementation contract

Each revision must bind a workload/program and checkpoint to:

| Category | Required fields |
| --- | --- |
| Execution | Complete dependency DAG through feedback, operation ownership, rounding points, producer readiness |
| Storage | Address units, region bounds, bank/stack/PC ownership, ports, packed representation, capacity reserve |
| Service | Latency, initiation interval, burst envelope, arbitration, queue/credit limits, backpressure and completion |
| Physical | Actual macro/library versions, macro/register groups, pins/channels, load and clock assumptions, wire-delay budget |
| Budget | Area, storage, power, link/memory service and critical-path time; each measured, derived or unresolved |
| Evidence | Source and input hashes, scope, test assertions, physical stage, pass/fail and provenance |

Unknown numeric values remain null with an owner and required experiment. A complete rate remains null while a critical dependency has unknown or infeasible service. One machine-readable contract should feed generators, checks and the schedule; separately copied constants are not authoritative.

## Review and refinement loop

1. Root defines the contract revision and allocation from the complete workload.
2. Owners propose implementation and verification plans against that revision.
3. Root reviews topology, timing/storage budgets and file boundaries before architecture-changing implementation or a new expensive physical experiment.
4. Owners implement and verify arithmetic, protocol, simultaneous finite-resource traffic and physical timing at the stated boundary.
5. A failed gate reports the violated budget, reproducer, causal evidence and alternative remedies with latency/area/power costs.
6. Root decides whether to fix implementation within contract or revise the architecture. A revision invalidates dependent evidence and updates the execution schedule before another rate claim.
7. Integrate approved changes, rerun affected checks, publish evidence and update TASKS.

No automatic extra pipeline stage, wider engine, larger queue or floorplan retry is an architectural decision. Ongoing distinct measurements may finish; failed and superseded results remain labeled.

## Immediate review gates

- Physical locality: macro-associated control/data/capture register placement, channel and timing budgets before another VM/MAC neighborhood route. Existing internal negative timing is a real contract failure.
- Shared HBM: proposed single-user complete region/service ledger and executable overlap/width checks before activating incomplete die clients.
- Index: query lifetime, reader bursts, scorer/selector service and bounded queues before selecting replicated width.
- Layer connectivity: actual selected-ID origin, descriptor completion and all full-shape width/parameter propagation before claiming end-to-end execution.
- Qwen compilation: arithmetic/tree/latency equivalence plus bounded resource measurements before full-width launch.

## Roles

Root owns decisions, integration, publication and TASKS. v41_model_reprice proposes the dependency/budget schema and verifies schedules. v41_hbm_region_audit verifies region/service allocation. v41_fullshape_core prepares executable connection requirements. v41_vm_bank_physical proposes placement/timing contracts; v41_me_he_macro_pipeline verifies the agreed operand pipeline. v41_index_score_major verifies streaming index contracts. Qwen owners retain their separate compilation, HBM-service and physical scopes. Completed feature agents wait for a defined implementation assignment rather than starting speculative new features.
