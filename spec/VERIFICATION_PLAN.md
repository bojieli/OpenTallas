# Verification and signoff plan

**Document:** SPEC-DV 1.0  
**Status:** frozen campaign plan; canonical RTL coverage and complete
pre-synthesis public-tool re-entry closed

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

Run the product-analysis profiles for DeepSeek Flash/Pro at 8K, 32K, 200K, and
1M with batches 1, 8, 32, and 64. The broader public-reference suite also retains
Kimi at 200K/1M, Qwen3-8B at 8K, batch 128 stress, and capacity endpoints. Include
one- and multi-stage pipeline configurations, dense and routed numeric modes, and
the no-speculation boundary for Qwen. A legacy fixed proxy partition tests the
interface; technology-envelope stage counts test analytical packing separately.

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

### DV-6.3 Executable mapping gate

`COMP-01` is a separate hard gate above the existing protocol-shell campaigns.
The compiler shall ingest complete pinned checkpoint payloads and emit legal ROM,
scale, integrity, microcode, schedule, KV-layout, known-answer, and deployment
artifacts. An independent image checker shall reconstruct canonical tensor hashes;
an independently implemented schedule checker shall reconstruct conflicts, paths,
and occupancy. The software service engine and representative RTL/co-simulation
shall consume the generated artifacts and compare operator outputs, layer
boundaries, router and sparse-attention selections, prepared/committed KV state,
and final logits against independent references. Operation, ROM/HBM byte, flit,
stall, and cycle counters shall reconcile without an unpriced functional black
box. The complete closure contract and milestone order are in
`../docs/EXECUTABLE_SYSTEM_RECOVERY_PLAN.md`.

Until this gate passes, successful stage completion tests establish only the
abstract service-boundary behavior exercised by their test doubles. They do not
establish that a transformer layer or complete model executed.

## DV-7 Fault, RAS, repair, and DFT

### DV-7.1 Fault campaign

Inject every fault class in `RAS_REPAIR_DFT.md`: bit errors, CRC corruption,
wrong/dropped/duplicate/reordered records, schedule violations, credit faults,
ROM/mask/repair faults, HBM errors, link retries, clock/reset loss, sensor alarms,
watchdogs, BIST outcomes, clustered defects, and exhaustion. Record detection,
classification, containment, retries, recovery, final state, credits, and telemetry.

The canonical deterministic public-RTL subset is `fault_campaign.json`, executed by
`tools/rtl_fault_campaign.py`. It rejects duplicate, missing, stale, or bench-moved
site IDs, treats unexpected warnings as fatal, and requires exactly one PASS line per
planned site from both Icarus/vvp and pinned Verilator 5.050. The current subset has
87 sites spanning route/ROM/HBM integrity, stage links, RAS telemetry, BIST/DFT,
power, schedules, sessions, and stage abort cleanup. A 100% result applies only to
that enumerated site set. Statistical injection, all reset phases, stage/reticle/
pipeline degradation, target macro fault grading, and physical faults remain open.

### DV-7.2 DFT and degraded operation

Verify scan/test-mode isolation, IDCODE/BYPASS, ROM/SRAM/link BIST control,
signature comparison, repair map legality, tile/link quarantine, capacity
publication, schedule recompilation, and fail-closed boot. Target ATPG coverage is
external until qualified cells/macros and ATPG are available.

## DV-8 Coverage and closure

### DV-8.1 Coverage thresholds

Closure targets are 95% line, 90% branch, 85% toggle, 100% must-bin functional,
100% planned FSM-state bins, 100% planned formal, 100% planned fault-site
activation/containment, and 100% requirement-to-pass-evidence mapping. Exclusions
require a review record and owner.

### DV-8.2 Coverage quality

Coverage is merged across unit, tile, reticle, stage, and pipeline environments.
Cross coverage includes numeric mode × error × backpressure × reset × repair ×
power state. Dead code, unreachable bins, vacuous assertions, and unhit error paths
are reviewed rather than hidden by broad exclusions.

The canonical public-reference campaign is `coverage_plan.json`, executed by
`tools/rtl_coverage_campaign.py`. It runs five deterministic coverage-focused
benches and four supplemental directed-fault benches under Icarus/vvp and pinned
Verilator 5.050. Every mandatory bin must appear exactly once in both engines, the
semantic PASS stream must match, and every unexpected warning is fatal. Native
Verilator line, branch, and toggle points are merged across cases and hierarchy by
the exact source key `{file,line,column,class,type,description,source-span}`; a
repeated parameter instance cannot inflate a hit.

The source-current closed result is 96.512% line, 94.662% branch, 85.210% toggle,
89/89 mandatory bins, and 28/28 FSM-state bins. `coverage_waivers.json` contains
zero exclusions. Four fault supplements contribute control-path coverage but do
not replace the separate exact 87-site fault-campaign gate. The result is logical
RTL evidence on reduced public configurations only; it is not ATPG, target-node,
macro/PHY, numerical-quality, manufacturing, or product-silicon signoff.

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

### DV-10.2 Implementation and physical-proxy closure

The canonical post-entry campaign is governed by `implementation_proxy.json` and
`tools/rtl_implementation_campaign.py`. Its complete seven-case selection is the
only canonical run; CLI-selected or equivalence/physical-skipped runs are labeled
partial and cannot close this gate. A run admitted with `--allow-dirty` also remains
`partial_noncanonical` even if its technical gates pass. The governed evidence
state is `pending_governed_run` while result paths must be absent, then changes to
`closed` only after a clean-baseline, full-selection `pass` JSON and matching report
exist. The run fingerprints the runner, specification, CDC/RDC constraint inventory,
RTL sources, tool executables, library collateral, and immutable OpenROAD image.
Unexpected synthesis or OpenROAD warning codes fail.

The closed public baseline has fingerprint `87e057764094b9ed`. Its exact source
inventory was copied into an isolated deterministic git commit and the full
campaign reran without any dirty-tree or skip option; source inventory, pinned
tool identities, technical closure signatures, and 386 referenced artifact
hashes pass the replay audit. The displaced dirty-tree run remains explicitly
archived rather than promoted or deleted. The large `numeric_e16_l16`
scaling-only point alone uses the reviewed bounded structural Liberty recipe
`strash; &get -n; &nf; &put` with a 300-second outer timeout. It retains all
structural and STA-coverage gates, but its QoR is not compared directly with the
default delay-oriented cases.

Every mapped case must contain zero internal cells, latches, blackboxes, structural
errors, and unconstrained endpoints. Representative generic equivalence is required
for arithmetic and stage control; the arithmetic representative also proves the
actual ABC-mapped netlist. Required physical representatives must close final setup,
hold, electrical limits, placement legality, antenna checks, detailed-route DRC,
and zero flow errors. A separate final-netlist connectivity audit proves the
max-fanout-32 contract and permits a one-pin net only when it is exactly one unused
cell output with no load or top-level connection. Exact ORFS synthesized-to-final
equivalence replaces the disabled host-incompatible optional Kepler helper. That
gate expands both cell netlists through the pinned Liberty library, normalizes them
to AIG with arbitrary common initial state, audits public IO and every state index,
then requires warning-free inductive ABC `dsec` closure. Private autogenerated state
symbol alignment is bounded and recorded; public state-name mismatches fail. Power
and IR-drop fields are retained as non-gating diagnostics under PPA-6.3's evidence
limits.

Any RTL, implementation constraint, warning disposition, tool/library identity, or
runner change invalidates the fingerprint and reopens the affected synthesis, STA,
equivalence, physical, and source-current pre-synthesis gates. Nangate45 results are
methodology/scaling proxies only; product synthesis, STA, LEC, DRC/LVS, SI/PI,
reliability, DFT, and target-node macro closure remain external.
