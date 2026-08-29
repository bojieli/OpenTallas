# OpenTallas executable-system recovery plan

**Document status:** active implementation plan  
**Initial issue:** 2026-08-28  
**Primary gate:** `COMP-01 — executable model mapping`  
**Applies to:** checkpoint ingestion, model semantics, compiler, runtime, RTL,
verification, performance accounting, and physical re-entry

## 1. Decision and purpose

OpenTallas has not yet validated an executable model-to-chip system. The current
repository contains useful checkpoint inventories, operator and traffic
accounting, a technology-independent control shell, reduced integer-DV tile RTL,
public-PDK ROM methodology vehicles, predictive digital implementation evidence,
and conditional architecture studies. It does not yet contain the compiler,
operator-complete execution engine, generated physical images, or end-to-end
model differential evidence required to show that the proposed machine runs the
declared model correctly.

The missing executable path invalidates any interpretation of the current
analytical speedups as achieved architecture performance. It does not by itself
prove that local mask-ROM weights are infeasible. The architecture is therefore
reset to an **unvalidated hypothesis** with a falsifiable recovery program.

This plan establishes the required unbroken evidence chain:

```text
pinned official source and checkpoint
  -> executable semantic graph
  -> exact canonical tensors
  -> legal physical ROM/HBM placement
  -> microcode and certified schedules
  -> functional service-engine execution
  -> RTL/co-simulation execution
  -> matching operators, layers, state transitions, and logits
  -> reconciled byte/operation/stall/cycle counters
  -> implementation-derived PPA and system comparison
```

No later link may substitute for an earlier one. In particular, PPA for proxy
arithmetic, a passing protocol shell, or a capacity calculation cannot establish
model correctness.

## 2. Claim policy effective immediately

Until `COMP-01` closes:

- analytical OpenTallas token rates are conditional scenarios or break-even
  requirements, not achieved throughput;
- ROM density, bandwidth, clock, power, repair, and yield inputs remain governed
  assumptions unless supported by the declared evidence class;
- SKY130A and IHP SG13G2 results establish local ROM topology and verification
  methodology only;
- ASAP7 results establish predictive behavior for the exact implemented digital
  proxy only;
- integer-DV results establish enumerated control, ordering, and fault behavior,
  not target numerical correctness;
- NVIDIA superiority, product readiness, and target-node manufacturability claims
  remain prohibited; and
- a result may be promoted only when its input artifact hashes, implementation,
  test scope, and independent checker are named.

Failure of an exact semantic, layout, schedule, timing, capacity, power, thermal,
or quality gate can reject or force redesign of the architecture. Passing public
and predictive gates means only that the tested design has not yet been disproven.

## 3. Current repository baseline

### 3.1 Evidence retained

The following work remains part of the program:

| Existing evidence | Retained use | Prohibited inference |
|---|---|---|
| Pinned tensor inventories and model profiles | Source identity, shape, dtype, role, and byte requirements | Complete payload compilation or executable correctness |
| Tensor-contraction inventory | Initial operation and numeric-format requirements | Executable operator semantics or achieved cycles |
| Analytical capacity/traffic model | Constraint screening and break-even analysis | Legal placement, scheduling, or silicon performance |
| Command/session/schedule/RAS RTL | Control-shell and protocol evidence for enumerated configurations | A transformer layer was executed |
| Integer-DV tile and synthetic ROM image | Local control, routing-mask, reduction, and fault methodology | DeepSeek numerical execution |
| SKY130A/IHP ROM slices | Public-PDK layout, extraction, SPICE, and programming-method evidence | Target-node macro density or yield |
| ASAP7 digital campaign | Predictive timing/congestion evidence for exact proxy RTL | Foundry N7/N4 closure or missing operators |
| GPU measurements and public specifications | External comparison anchors under declared scope | An OpenTallas speedup without the executable path |

### 3.2 Critical missing artifacts

The recovery program must produce all of the following:

1. an executable target-model IR imported from pinned official source;
2. an independent target-precision semantic reference;
3. complete checkpoint-payload ingestion and validation;
4. canonical tensor and scale conversion;
5. legal stage/tile/macro/row/column placement;
6. emitted ROM, scale, integrity, microcode, schedule, and KV artifacts;
7. an inverse image reconstruction checker;
8. an executable software service engine consuming those artifacts;
9. complete operator implementations and cost models;
10. a schedule compiler plus independently implemented checker;
11. a generated-artifact-driven RTL or RTL/software co-simulation path;
12. layer, state, routing, and logits differential evidence; and
13. counters derived from execution rather than inserted analytical ceilings.

## 4. Program scope and target lock

### 4.1 Product boundary

The initial executable product boundary is decode from an input hidden state and
session state through final logits. Host-side token sampling is out of the first
hardware boundary. Prefill, speculative decoding, fleet scheduling, and training
are separately versioned extensions and may not be silently included in a decode
claim.

### 4.2 Target progression

Implementation proceeds through three targets:

1. **Deterministic compiler fixture.** A tiny model-shaped fixture exercises every
   artifact format, legality failure, and inverse map quickly. It is unit-test
   evidence only.
2. **Real checkpoint vertical slice.** Full-size tensor dimensions and real
   checkpoint values for representative DeepSeek Flash layer classes exercise
   the actual formats, routes, attention state, and placement rules.
3. **Complete pinned model.** The complete released checkpoint is compiled and
   executed in the functional architecture model, with representative complete
   layers executed in RTL/co-simulation.

The fixture cannot close a real-model milestone. Reduced tensor dimensions cannot
close the vertical-slice milestone.

### 4.3 Source lock

Every build binds:

- official model repository and immutable revision;
- checkpoint repository and immutable revision;
- every config, index, tokenizer, code, and tensor-payload hash;
- declared remote-code policy and reviewed source set;
- compiler, schema, numeric-profile, and micro-op ABI versions;
- hardware capability and defect-map hashes; and
- target context, batch, decode mode, and output boundary.

Mutable branch names, download timestamps, cache paths, hostnames, and local
absolute paths do not participate in canonical identity.

## 5. Repository organization

All implementation remains in this repository. The intended additive hierarchy
is:

```text
compiler/
  README.md
  frontend/       # source locks, graph import, checkpoint payload readers
  ir/             # versioned semantic and physical IR types/validation
  canonical/      # dtype, scale, packing, padding, and tensor transforms
  placement/      # stage/reticle/tile/macro/row/column mapping
  microcode/      # lowering, encoding, disassembly, and static verification
  schedule/       # schedule generation and certificate emission
  image/          # ROM/scale/integrity image construction and manifests
  checking/       # independent round-trip and schedule checkers
  cli/            # reproducible command-line entry points

runtime/
  reference/      # independent target-precision operator semantics
  service_engine/ # artifact-driven functional micro-op interpreter

schemas/
  compiler/       # versioned JSON/binary schemas and compatibility fixtures

tests/
  compiler/       # compiler unit, property, rejection, and reproducibility tests
  runtime/        # semantic and service-engine differential tests

testdata/
  compiler/       # small redistributable fixtures and known answers
  vertical_slice/ # hashes/manifests for real slices; payloads only if redistributable
```

The existing `src/opentallas` analytical package remains available during the
transition. It must not become the semantic oracle for the compiler. Once
execution counters exist, analytical studies import generated summaries through a
versioned boundary rather than reimplementing compiler decisions.

Large checkpoints, full ROM images, tool caches, waveform databases, and ordinary
build products remain outside Git. Small deterministic fixtures, schemas, hashes,
known answers, reports, and reproduction commands are committed.

## 6. Architectural separation and independence

Four implementations have distinct responsibilities:

| Component | Responsibility | Independence rule |
|---|---|---|
| Official-model adapter | Capture the pinned source graph and intermediate reference values | Must preserve official behavior and record every adaptation |
| Target-precision reference | Define OpenTallas formats, operation order, state, and exceptional behavior | Must not call compiler lowering or RTL algorithms |
| Compiler and service engine | Lower the graph, emit artifacts, and execute the micro-op contract | May share schemas, never expected-result calculations |
| RTL/co-simulation scoreboard | Drive generated artifacts and compare visible behavior | Must consume independently generated known answers |

The placement inverse checker and schedule checker are also independent programs.
They parse emitted artifacts and reconstruct legality without invoking the
generator's placement or routing algorithm.

## 7. Model IR and semantic completeness

### 7.1 IR requirements

Each semantic IR node records:

- stable operation identifier and source location;
- ordered inputs, outputs, shapes, layouts, and state effects;
- source and architectural dtypes;
- scale blocks, accumulation type, rounding points, and reduction order;
- static attributes and runtime predicates;
- legal fusion boundaries;
- hardware, functional-macro, or host implementation class;
- scratch, activation, ROM, SRAM, and HBM storage requirements;
- micro-op lowering identifier;
- reference-vector identity; and
- cycle/traffic accounting class.

Unknown operations, implicit broadcasting, inferred state mutation, or an
unpriced generic operation are compile errors.

### 7.2 Required DeepSeek semantic ledger

The ledger must cover at least:

- embedding lookup and final vocabulary head;
- RMSNorm and every other normalization boundary;
- residual paths and architectural hidden-state conversions;
- query, key, value, output, LoRA, and grouped projections;
- RoPE construction and application;
- causal/window/compressed attention masks;
- QK score formation, scale, softmax, and AV reduction;
- KV construction, compression, layout, append, read, prepare, and commit;
- indexer projections, FP4 index scan, top-k, ties, and sparse gather;
- router projection, hash routing, top-k, duplicate/tie policy, and weights;
- shared and routed expert dispatch and reduction;
- SwiGLU, SiLU/sigmoid, multiplication, and gating;
- compressor pooling and overlap behavior;
- mHC projections, Sinkhorn transforms, and head projection;
- scale application, padding, saturation, and exceptional-value propagation;
- final normalization and logits; and
- any draft/acceptance path included by a later declared scope.

An operation count is not a semantic implementation. Every auxiliary count in the
current analytical inventory must resolve to one or more executable nodes before a
model is complete.

### 7.3 Numeric qualification

The reference and implementation must explicitly cover:

- MXFP4 E2M1 data and E8M0 block scales;
- FP8 E4M3FN data and scales;
- FP4 index data;
- BF16 architectural state and vector boundaries;
- FP32 accumulation and mHC paths;
- exact scale selection and application;
- round-to-nearest ties-to-even at every declared boundary;
- signed zero, subnormal, saturation, NaN, and infinity policies; and
- deterministic reduction order.

Each operator receives exhaustive encoding tests where finite, boundary tests,
property tests, randomized differential tests, real checkpoint known answers, and
model-quality qualification.

## 8. Compiler artifact contract

One deterministic build emits:

```text
source.lock.json
model.ir.json
operator_coverage.json
tensor_manifest.json
canonical_tensor_index.json
stage_partition.json
physical_map.json
rom_stageNN_image.bin
rom_stageNN_image.hex          # optional development view
scale_stageNN_image.bin
integrity_stageNN_image.bin
microcode_stageNN.bin
microcode_stageNN.disasm
schedule_stageNN.bin
schedule_certificate.json
kv_layout.json
known_answers.json
deployment_manifest.json
roundtrip_report.json
numerical_report.json
execution_expectations.json
```

Payloads may be stored in a content-addressed external build directory. The
manifest contains their hashes, sizes, and schema identities. A public small
fixture uses the identical path and formats.

### 8.1 Determinism

Identical source locks, compiler revision, capabilities, defect map, and options
must emit byte-identical artifacts. Canonical serialization rejects duplicate
keys, unstable iteration order, noncanonical numbers, timestamps, host paths, and
random seeds not explicitly included as inputs.

### 8.2 Failure policy

The compiler fails closed on:

- missing, duplicated, overlapping, unexpected, or hash-mismatched tensors;
- unsupported operation, shape, dtype, scale layout, or numeric profile;
- integer overflow or address-unit ambiguity;
- illegal alignment, padding, or nonzero padding data;
- indivisible region or local capacity overflow;
- identifier, loop, context, top-k, or instruction-field overflow;
- invalid ROM/scale/integrity association;
- insufficient repair or integrity reserve;
- HBM/KV allocation overflow;
- buffer, credit, schedule, or macro-latency overflow;
- route conflicts, cycles, nontermination, or disabled-resource use; and
- any required tensor or operation lacking an explicit execution role.

Warnings do not legalize an image. Every release-relevant warning has a reviewed,
expiring waiver or becomes an error.

## 9. Physical mapping and inverse proof

The versioned logical key is:

```text
{image_region, tensor_id, layer, expert_or_shared_id, output_row,
 reduction_block, element, scale_or_data}
```

The physical key is:

```text
{stage, reticle, tile, macro, logical_row, logical_column,
 nibble_or_byte_lane, scale_address, integrity_block}
```

Mapping accounts for decoder/periphery regions, block and row alignment, padding,
integrity data, repair reserves, fragmentation, immutable microprogram storage,
and physically indivisible units. Dense, shared, routed, scale, metadata, and
diagnostic regions cannot alias.

The independent inverse checker reconstructs every canonical tensor and scale
from physical images, verifies padding and integrity data, and compares the full
canonical content hashes. Aggregate byte equality cannot substitute for inverse
reconstruction.

## 10. Micro-op and software service-engine contract

### 10.1 Why the service engine starts with the compiler

The compiler cannot be validated by inspecting emitted files alone. A software
service engine must consume the same images, descriptors, microcode, schedules,
and KV layout intended for RTL. It is the executable architecture model and the
source of reconciled counters; it is not a latency spreadsheet.

### 10.2 Initial micro-op families

The existing conceptual operations are refined into explicit, versioned families:

```text
CONTROL       LOOP, BRANCH_PRED, BARRIER, COMPLETE, TRAP
STATE         KV_READ, KV_PREPARE, KV_COMMIT, STATE_READ, STATE_WRITE
ROM           ROM_MATMUL, ROM_LOOKUP, SCALE_READ
MATRIX        MATMUL_DENSE, MATMUL_ROUTED, REDUCE
VECTOR        RMSNORM, RESIDUAL, ROPE, SILU, GATE, CONVERT
ATTENTION     MASK, SOFTMAX, ATTEND, COMPRESS, INDEX_SCAN, GATHER
ROUTING       ROUTER_SCORE, TOPK, HASH_ROUTE, EXPERT_WEIGHT
MHC           MHC_PROJECT, SINKHORN, MHC_COMBINE
TRANSPORT     HBM_READ, HBM_WRITE, STAGE_SEND, STAGE_RECV
```

The exact encoding follows semantic and implementation review. The generic
`VECTOR` name cannot remain an unbounded zero-cost black box in a performance
model.

### 10.3 Interpreter-visible state

The service engine models:

- program counter, loop state, layer, tensor, and descriptor selection;
- architectural activations and numeric status;
- session, context position, KV base/limit, and generation;
- prepared versus committed mutable state;
- ROM/HBM addresses, tags, bursts, and response order;
- expert and sparse-attention selections;
- buffers, credits, dependencies, and schedule slots;
- poison, abort, exceptional values, and terminal status; and
- operations, bytes, flits, issued/active/stalled cycles, and occupancy maxima.

Completion is illegal until all required results are available, all errors are
resolved, and the declared state commit has occurred. A test double that merely
returns `done` cannot close an executable milestone.

## 11. Schedule compilation and checking

The schedule compiler consumes the actual physical graph, logical placement,
operator dependencies, payload sizes, macro latencies, link widths, buffers,
credits, and repair/quarantine map. It emits per-slot selections, expected
valid/type/sequence data, collective membership, and a certificate.

The independent checker proves or reconstructs:

- legal sources and destinations;
- output conflict freedom for every slot;
- complete path termination;
- no cyclic resource dependency;
- sequence continuity and terminal consumption;
- exact expected packets, flits, and reduction sources;
- per-buffer occupancy trace and maximum;
- credit conservation and bounds;
- absence of disabled or quarantined resources; and
- schedule identity, epoch length, and CRC.

The key architecture hypothesis—that dynamic expert IDs alter local ROM masks
rather than global physical routes—must be demonstrated by generated placement and
schedule evidence. If real routing or sparse-attention behavior requires arbitrary
data-dependent global paths, the static-NoC architecture must be redesigned or
rejected.

## 12. Validation ladder

### 12.1 Level A: schemas and deterministic fixtures

- Schema validation and incompatible-version rejection
- Golden serialization and byte-identical rebuild
- Checkpoint truncation, duplication, overlap, and hash-failure tests
- Every placement and instruction field boundary
- Inverse reconstruction for all fixture tensors
- Interpreter success and intentional-failure programs

### 12.2 Level B: executable operators

- Independent scalar semantics
- Exhaustive finite encodings where tractable
- Random matrix/vector differential tests
- Reduction-order and exceptional-value tests
- Synthesizable block or qualified functional-macro comparison
- Measured latency, initiation interval, area, and activity proxy

### 12.3 Level C: real full-dimension vertical slice

The minimum DeepSeek Flash slice includes representative layer classes with
compression ratios `0`, `4`, and `128`, together with shared and routed experts,
router decisions, attention state, and mHC behavior. Candidate layers are selected
from the pinned official graph; current profile indices 0, 2, and 3 are initial
coverage anchors, not a substitute for source inspection.

The decisive chain is:

```text
real checkpoint values and shapes
  -> canonical tensors
  -> generated physical images
  -> generated microcode and schedules
  -> functional service-engine execution
  -> correct activation, route, sparse index, and KV transition
  -> exact byte/operation/flit/stall/cycle reconciliation
```

Reduced dimensions and handwritten `weights.hex` data remain unit tests and cannot
close this level.

### 12.4 Level D: RTL/co-simulation vertical slice

The abstract service boundary is replaced or backed by an executable engine that:

- fetches and decodes generated microcode;
- reads generated ROM and scale images;
- issues and consumes modeled HBM traffic;
- invokes exact RTL operators or bit-exact qualified models;
- enforces schedule, tag, backpressure, poison, and commit semantics; and
- produces the same visible state and counters as the functional engine.

### 12.5 Level E: complete model

- Compile every payload byte of the pinned checkpoint
- Hash every physical image and descriptor
- Prove all local capacity and inverse reconstruction
- Execute at least one complete decode step in the functional engine
- Compare every declared layer boundary, route, KV transition, and final logits
- Run representative complete layers and error paths in RTL/co-simulation
- Qualify task quality and long-context numerical behavior

### 12.6 Level F: implementation re-entry

Only execution-qualified RTL and generated activity enter renewed synthesis, P&R,
NoC, HBM, power, and thermal analysis. Proxy results remain archived but do not
silently supply missing operator costs or clocks.

## 13. Milestones and hard exit gates

### 13.1 Current evidence ledger (2026-08-29)

This ledger reports implementation evidence against the gates below. A partial
row must not be read as milestone closure.

| Gate | Current direct evidence | Status |
|---|---|---|
| M0 | Repository baseline and additive compiler/runtime layout are committed on `main`; large generated payloads remain outside Git | Ongoing because concurrent model and simulation work may keep the worktree active |
| M1 | The pinned official graph has a complete 2,136-node/46-kind ledger; 32 kinds now have qualified target references, including all 62 raw-compressor/pool/FP32-to-BF16/compressed-KV transaction and valid-view sites, all 46 sparse-attention sites with explicit logical traffic accounting, and fail-closed greedy/target-adapted sampling | Partial: 14 operator references and operator-complete semantics remain open |
| M2 | The official 72,317-tensor checkpoint is locked; the complete 77,116-assignment MP=4 application was independently re-read with verification `b20ac53d48714c2328470b45f44b06aed11bed4c6dc7ef48f27185c5ba813f28` | Checkpoint/canonical payload gate achieved; this does not imply executable operators |
| M3 | Lookup and complete-output query-A deployments have content-addressed images and independent payload roundtrips | Partial: complete stage placement, capacity, repair, and physical-address legality remain open |
| M4 | Artifact-only fixed-microcode paths execute official lookup tensors and all 1,024 Query-A FP8 outputs. The real HC_PRE→Query-A chain ends at artifact-only result `d30df5494e60c3f261cc6bec15320680ee3e87d867873e1d0fc100f7776336c0`. A separate official-width layer-2 ratio-four post-projection compressor harness now executes immutable causal raw/compressed state, conditional pool/conversion, abort, retirement, commit, and valid-view semantics with report `69c585d6a048604cd0a69e2bc1c2e99927aa25023f2a9526e5c04f224a36cc51` | Partial: the compressor request starts after learned projection and its direct BF16 cache payload omits official RMSNorm/RoPE/QDQ; neither path yet completes attention, a transformer block, complete graph-to-microcode lowering, or full-model execution |
| M5 | No certified physical schedule exists | Open |
| M6 | Official lookup differential `830f0d8a0730d012e6be41eb1507f10ef1b70f1829efbbad7b3e50cd2b3e2a95`, selected-row FP8 differential `9b4cacd415df0fbd77b08c24bbb4b48b737f0b3305abfd08ba719d4302e3b800`, complete-output FP8 differential `f8d95b84c683b9772755b6146da0af84955987e19e0ea05fe4a5ad05c7f0c499`, and official-APE transactional-slice report `69c585d6a048604cd0a69e2bc1c2e99927aa25023f2a9526e5c04f224a36cc51` are exact | Partial: these isolated or post-projection slices are not a checkpoint-derived layer or all layer classes |
| M7 | No generated-artifact RTL controller/operator integration evidence | Open |
| M8 | No complete DeepSeek V4 Flash prefill/decode execution | Open |
| M9 | No schedule-driven performance closure or same-scope NVIDIA comparison | Open |

The governed evidence records are
[`DEEPSEEK_V4_LOOKUP_EVIDENCE.md`](DEEPSEEK_V4_LOOKUP_EVIDENCE.md) and
[`DEEPSEEK_V4_FP8_LINEAR_EVIDENCE.md`](DEEPSEEK_V4_FP8_LINEAR_EVIDENCE.md), and
[`DEEPSEEK_V4_FP8_LINEAR_FULL_EVIDENCE.md`](DEEPSEEK_V4_FP8_LINEAR_FULL_EVIDENCE.md),
and
[`DEEPSEEK_V4_SPARSE_ATTENTION_EVIDENCE.md`](DEEPSEEK_V4_SPARSE_ATTENTION_EVIDENCE.md),
and
[`DEEPSEEK_V4_COMPRESSOR_EVIDENCE.md`](DEEPSEEK_V4_COMPRESSOR_EVIDENCE.md).
Neither changes the `COMP-01` closure criteria.

### M0 — governed baseline

Deliverables:

- clean, reviewed, and pushed repository baseline;
- this recovery plan and top-level `COMP-01` gate;
- transient-artifact policy; and
- separated ownership for live validation outputs and additive compiler source.

Exit: applicable current tests pass, every dirty file is classified, and no live
writer can mutate a committed artifact during capture.

### M1 — semantic graph and operator ledger

Deliverables:

- source lock;
- executable semantic IR schema;
- official graph adapter;
- complete operator-coverage report; and
- target-precision reference skeleton plus known answers.

Exit: every graph node has one defined semantic operation, state effect, lowering
class, and reference-vector owner. Unknown or unpriced nodes are zero.

### M2 — complete checkpoint front end

Deliverables:

- streaming safetensors/index reader;
- payload hash and coverage validation;
- tensor-role classification;
- canonical format/layout conversion; and
- canonical round-trip checker.

Exit: complete payload coverage and canonical hash equality; synthetic weights are
absent from acceptance tests.

### M3 — image and placement compiler

Deliverables:

- stage partition and physical placement;
- ROM/scale/integrity images;
- address descriptors and manifest; and
- independent inverse checker.

Exit: every logical element has one legal physical location and every emitted
image reconstructs to the canonical hash.

### M4 — executable service engine

Deliverables:

- micro-op schema, assembler, disassembler, and verifier;
- graph-to-microcode lowering;
- artifact-driven functional interpreter;
- KV prepare/commit and error semantics; and
- reconciled counter report.

Exit: a real checkpoint-derived transformer block executes from generated
artifacts and matches the target-precision reference.

### M5 — certified schedules

Deliverables:

- schedule generator;
- schedule/certificate schema;
- independent schedule checker; and
- real placement/routing traces.

Exit: conflict, path, occupancy, credit, quarantine, and count checks pass for the
vertical slice.

### M6 — real-model vertical slice

Deliverables:

- representative full-dimension DeepSeek images and programs;
- official/reference/service-engine differential report; and
- exact execution-accounting report.

Exit: all selected layer classes, routes, indices, state transitions, and outputs
pass with no unexplained counter difference.

### M7 — RTL executable integration

Deliverables:

- microprogram controller;
- executable ROM/HBM/operator service path;
- generated-artifact RTL testbench; and
- software/RTL differential evidence.

Exit: service completion is causally dependent on correct execution and commit,
and representative programs match the functional engine.

### M8 — operator-complete full model

Deliverables:

- all target arithmetic and vector operators;
- complete-model compilation;
- full functional decode execution; and
- representative RTL layer closure.

Exit: end-to-end logits, KV state, routing, numeric status, and task quality meet
the frozen acceptance policy.

### M9 — performance and physical revalidation

Deliverables:

- generated-schedule-driven cycle model;
- exact operator PPA and activity;
- updated NoC/HBM/power/thermal analysis;
- measured same-scope GPU baseline; and
- governed comparison report.

Exit: every reported performance term traces to execution or characterized
implementation evidence. Target-node feasibility remains open until foundry,
memory, package, and signoff evidence closes it.

## 14. `COMP-01` closure criteria

`COMP-01` closes only when all of the following are true:

1. The exact source and checkpoint revisions are cryptographically pinned.
2. The complete declared decode graph has executable semantics.
3. Every required checkpoint payload is ingested and assigned an execution role.
4. Physical images inverse-reconstruct to canonical tensor hashes.
5. Generated microcode and schedules pass independent legality checks.
6. The functional service engine consumes only generated deployment artifacts.
7. Representative real full-dimension layers match routes, state, and outputs.
8. The complete model executes at least one declared decode step functionally.
9. Representative complete layers execute through RTL/co-simulation.
10. Operations, ROM bytes, HBM bytes, flits, stalls, and cycles reconcile exactly.
11. Numerical and task-quality acceptance criteria pass.
12. All residual abstraction boundaries are enumerated and priced; none hides a
    required operation or state transition.

Closing `COMP-01` establishes executable architecture correctness for the tested
scope. It does not close target-node PPA, manufacturability, package, yield, or
commercial superiority.

## 15. Comparator strategy

The primary commercial comparison remains measured execution of the same pinned
model, arithmetic/quality policy, context, batch/concurrency, and latency boundary
on actual NVIDIA hardware.

After the common semantic IR and service engine work, an HBM-weight backend may be
added as an architectural counterfactual. It reuses model semantics, operators,
microcode where legal, KV layout, correctness vectors, and counters while replacing
local immutable reads with DMA/cache/prefetch operations. It is not represented as
a clean-room NVIDIA GPU.

An SRAM backend begins as a generated capacity/bandwidth bound. Full implementation
is justified only if that bound can affect an architecture decision. ROM bitcell
density alone does not settle model lifetime, repair, stage count, routing, and
system cost, but it does not require an immediate full Graphcore reproduction.

## 16. Architecture kill and redesign criteria

The program stops or returns to architecture design if:

- a checkpoint cannot be frozen for a commercially credible mask lifetime;
- complete semantic recovery or a legally redistributable execution target is not
  possible;
- exact model quality fails under implementable numerical rules;
- physical placement fails after padding, integrity, repair, and fragmentation;
- instruction, descriptor, buffer, credit, or schedule bounds cannot represent the
  model;
- dynamic expert or sparse-attention behavior breaks the static-route premise;
- vector, attention, routing, or state costs erase the local-weight advantage;
- KV/HBM, reductions, or stage transport dominate the decode interval;
- a characterized target ROM cannot meet density, simultaneous-read, power,
  repair, timing, or yield requirements;
- package, PDN, thermal, or yield requirements fail; or
- measured GPU behavior beats the conservative implementation-derived upper bound.

A failed gate is a useful result and must be preserved. Parameters are not relaxed
after seeing a failure without a versioned architecture-change record.

## 17. Verification and CI policy

Every milestone supplies:

- positive tests and explicit rejection tests;
- deterministic build checks in two fresh directories;
- duplicate-key and canonical-schema validation;
- property tests for sizes, offsets, ranges, and round trips;
- independent differential checks;
- retained minimized failures and seeds;
- commands, tool versions, source hashes, artifact hashes, and evidence class;
- no unexplained warnings or silently skipped tests; and
- a machine-readable coverage/qualification report.

Network-dependent full-checkpoint tests are opt-in release gates with pinned local
payload hashes. Ordinary CI uses redistributable fixtures through the exact same
code path.

## 18. Concurrency and repository hygiene

Existing simulations may continue while compiler work is additive. The rules are:

- a running campaign owns a unique build/output directory;
- no campaign writes source or a canonical result path while that path is being
  committed;
- result promotion is atomic after campaign completion and validation;
- large temporary files remain under ignored build/cache directories;
- compiler tests use temporary directories and never emit into the repository
  root;
- scratch artifacts are not committed merely to make `git status` clean;
- canonical evidence is committed with its generator, configuration, hashes, and
  report; and
- a process is stopped only after its output is identified and either captured or
  declared obsolete.

Development occurs directly on `main` under the repository's current operating
policy. Commits remain small enough to review, group one coherent evidence or
implementation change, and are pushed only after the complete local series passes
its applicable gates.

## 19. Initial execution sequence

1. Audit, classify, test, commit, and push the current pre-compiler baseline.
2. Add `COMP-01` to top-level decision and traceability artifacts.
3. Establish additive compiler/runtime directories and schemas.
4. Implement deterministic source locks and artifact identity utilities.
5. Implement the semantic IR validator and operator-coverage ledger.
6. Implement the target-precision reference skeleton.
7. Implement a tiny end-to-end fixture through IR, microcode, service execution,
   and known-answer comparison.
8. Replace fixture weights with a real checkpoint slice and retain full dimensions.
9. Add placement, physical images, inverse checking, and schedule certification.
10. Integrate the first generated program with RTL only after the software ABI and
    vertical-slice behavior are stable.

The first implementation milestone is intentionally narrow but complete: one
deterministic program must travel from semantic IR through generated artifacts to
correct executable state. Breadth is added only after that chain is continuously
tested.

## 20. Review cadence and status reporting

Each milestone review records:

- exact commit and source/checkpoint identities;
- completed deliverables and evidence links;
- failing or waived gates;
- newly learned architecture constraints;
- comparison claims permitted after the milestone;
- the next smallest falsifiable vertical slice; and
- whether continuation, redesign, or termination is recommended.

The plan is changed through ordinary reviewed commits. A milestone cannot be
declared complete by editing this document alone; its named machine-readable and
executable evidence must exist and pass.
