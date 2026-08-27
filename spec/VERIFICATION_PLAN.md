# Verification and signoff plan

**Document:** SPEC-DV 1.0  
**Status:** frozen campaign plan; implementation evidence pending

Verification is the long pole. The plan below is a campaign contract, not a claim
that the current disposable RTL has already passed it. `verification.json` is the
machine-readable source for environments, planned checks, independence targets,
and closure thresholds.

## DV-1 Evidence and campaign control

### DV-1.1 Evidence classes

Every test, proof, lint result, and generated report records its command, tool
version, parameters, seed, input hashes, output hashes, and evidence class. A
synthetic or proxy result cannot be relabeled measured product behavior.

### DV-1.2 Reproducible campaign record

The campaign runner creates a clean run directory containing manifests, compiler
and RTL commits, simulator/linter/solver versions, environment lock, logs,
waveform/failure artifacts, coverage databases, waiver ledger, and a deterministic
summary. A second run in an independent directory must reproduce canonical results
byte-for-byte except for an outer timestamp record.

## DV-2 Reference models and requirements

### DV-2.1 Requirement-driven verification

Each RTL block has a requirement allocation, ICD contract, executable reference
model, assertions, directed tests, constrained-random tests, and a named planned
check. The traceability generator rejects an unallocated must requirement or a
verification reference that is not present in `verification.json`.

### DV-2.2 Reference-model independence

Numeric, CRC/ECC, routing, schedule, credit, session, and pipeline scoreboards use
independent implementations where practical. A checker may not simply call the
same RTL algorithm under test. Differential tests compare canonical bits, status,
ordering, credit conservation, and commit/abort side effects.

## DV-3 Static and elaboration closure

### DV-3.1 Multi-frontend static checks

Run at least two independent parser/lint frontends (for example Verilator and
iverilog/Verible where available), strict warning policy, parameter legality,
elaboration, hierarchy, undriven/multiple-driver, latch, combinational-loop,
width/sign, inferred-memory, and ROM-write-path checks. Record waivers with owner,
risk, expiration, and re-entry test. No unexplained severity-1/2 finding is open.

### DV-3.2 CDC/RDC and clock checks

Run structural CDC/RDC checks from the inventory in `CLOCK_RESET_POWER.md`,
including reset generation, async FIFO pointers, synchronizer attributes,
reconvergence, generated clocks, isolation, and test overrides. Public structural
checks are methodology evidence; target-qualified tools remain external.

## DV-4 Formal verification

### DV-4.1 Safety and conservation

Use at least two solver configurations for tractable blocks. Prove reset safety,
valid stability, FIFO no-overflow/underflow, credit conservation, route legality,
schedule conflict freedom, duplicate suppression, poison monotonicity, no-write ROM,
state commit atomicity, reduction ordering, retry idempotence, and legal power FSM
transitions.

### DV-4.2 Progress and non-vacuity

Bounded and inductive proofs cover eventual response under fair ready/clock
assumptions, watchdog escalation, quiesce/drain, and schedule completion. Every
assumption is listed. Cover statements demonstrate reachable accepted, stalled,
retry, corrected-error, poisoned, reset, degraded, and recovery scenarios; a proof
that succeeds only because valid is constrained false is rejected.

## DV-5 Simulation and constrained-random

### DV-5.1 Directed matrix

Run all required model profiles: DeepSeek Flash/Pro at 200K and 1M, Kimi at 200K
and 1M, and Qwen3-8B at 8K. Exercise batches 1, 8, 32, 64, and 128 plus capacity
endpoints and integer optimum points. Include one- and multi-stage pipeline
configurations, dense and routed numeric modes, and the no-speculation boundary for
Qwen.

### DV-5.2 Constrained-random stress

Randomize independent clocks, ready/valid stalls, HBM response order, packet retry,
route IDs/duplicates, schedule slots, session reuse/generation, faults, resets,
thermal requests, and power states. Retain seeds and shrink failing traces. Run
long enough to cover counter wrap, epoch wrap guards, watchdog boundaries, and
credit exhaustion.

## DV-6 Numerical and end-to-end correctness

### DV-6.1 Bit-exact formats

Exhaustively test E2M1, E8M0, FP8 E4M3FN, BF16, saturation, NaN/infinity,
subnormal, scale-selection, nibble order, block padding, and CRC known answers.
Compare integer DV, target-format blocks, reductions, and vector macro boundaries
against independent references.

### DV-6.2 Model and pipeline differential

Use pinned public model implementations and canonical tensor slices to compare
layer outputs, KV/state transitions, accepted speculative prefixes, and terminal
errors. Full quality/production serving qualification is an external gate, but the
public test must expose exactly which layer, format, or macro remains unqualified.

## DV-7 Fault, RAS, repair, and DFT

### DV-7.1 Fault campaign

Inject every fault class in `RAS_REPAIR_DFT.md`: bit errors, CRC corruption,
wrong/dropped/duplicate/reordered records, schedule violations, credit faults,
ROM/mask/repair faults, HBM errors, link retries, clock/reset loss, sensor alarms,
watchdogs, BIST outcomes, clustered defects, and exhaustion. Record detection,
classification, containment, retries, recovery, final state, credits, and telemetry.

### DV-7.2 DFT and degraded operation

Verify scan/test-mode isolation, IDCODE/BYPASS, ROM/SRAM/link BIST control,
signature comparison, repair map legality, tile/link quarantine, capacity
publication, schedule recompilation, and fail-closed boot. Target ATPG coverage is
external until qualified cells/macros and ATPG are available.

## DV-8 Coverage and closure

### DV-8.1 Coverage thresholds

Closure targets are 95% line, 90% branch, 85% toggle, 100% must-bin functional,
100% planned formal, 100% planned fault-site activation/containment, and 100%
requirement-to-pass-evidence mapping. Exclusions require a review record and owner.

### DV-8.2 Coverage quality

Coverage is merged across unit, tile, reticle, stage, and pipeline environments.
Cross coverage includes numeric mode × error × backpressure × reset × repair ×
power state. Dead code, unreachable bins, vacuous assertions, and unhit error paths
are reviewed rather than hidden by broad exclusions.

## DV-9 Reproducibility and review

### DV-9.1 Artifact retention

Keep canonical source manifests, tool versions, commands, seeds, logs, waveforms,
proof traces, coverage databases, static reports, timing constraints, and waivers.
Failures are never overwritten by a later run. CI verifies clean-tree operation,
credential scans, deterministic generated artifacts, and traceability.

## DV-10 Synthesis entry

### DV-10.1 Gate ordering

Synthesis starts only after the frozen RTL has zero open severity-1/2 bugs, zero
unexplained static findings, passing two-simulator and two-frontend checks,
reviewed CDC/RDC, passing formal safety/progress/non-vacuity, closed must bins,
complete fault/repair evidence, and an owned waiver ledger. Open-PDK synthesis and
physical proxy runs then report methodology only; they do not close product PPA.
