# DeepSeek-V4 Flash ROM hardware implementation plan

**Plan ID:** TA-DS-ROM-3.0

**Status:** audit-ready; implementation blocked on TA-A3-ARCH-0

**Model profile:** DeepSeek-V4-Flash-0731 ordinary target-only inference

**Mandatory context:** exactly 200,000 natural prompt tokens
**Issue date:** 2026-08-29

## 1. Mission

This lane builds a DeepSeek-V4 Flash-specific immutable-weight ROM compiler,
artifact-driven simulator, cycle model, RTL hierarchy, and physical plan. It may
use a different tensor-lane mix, stage topology, netlist, and masks from the
Qwen ROM product. It does not need to run Qwen dynamically.

The first release executes the complete ordinary target-model prefill/decode
path. DSpark draft generation and speculative acceptance are separate
extensions. Their current semantic and microprogram evidence is retained, but
cannot substitute for ordinary target-model execution.

The lane is complete only when:

- all ordinary-path graph nodes and checkpoint roles lower into generated
  deployment artifacts;
- every immutable tensor/scale has one legal ROM location and inverse proof;
- all required mixed-format, MoE, sparse-attention, compressor, mHC, and state
  operations execute causally;
- a complete checkpoint-derived transformer block and then complete model run
  match independent references;
- the first official EOS stops ordinary decode with legitimate token output;
- the exact 200,000-token natural context executes end to end;
- representative generated programs execute through ROM RTL/co-simulation; and
- a same-node physical report can be compared with the DeepSeek HBM deployment.

## 2. Retained baseline

### 2.1 Closed semantic and checkpoint work

The unified repository retains:

- an immutable official source/config/tokenizer/checkpoint lock;
- 72,317 checkpoint tensors;
- a complete 77,116-assignment MP=4 canonical application and independent replay;
- a source-mapped graph with 2,136 nodes and 46 operator kinds;
- qualified target-precision reference owners for all 46 kinds;
- explicit phase, predicate, guarded-output, tensor-role, and mutable-state
  contracts;
- qualified BF16, FP8 E4M3FN, FP4/MXFP4 E2M1, E8M0, conversion, reduction,
  routing, sparse-attention, compressor, mHC, KV, vocabulary, and selection
  semantics; and
- several content-addressed vertical slices with independent checking and
  service execution.

The preserved attention-preparation source at 16fe72d is a partial operator
handoff and remains part of this baseline.

### 2.2 Partial executable evidence

Current executable slices include combinations of:

- token lookup;
- selected and complete-output Query-A FP8 projection;
- HC_PRE to Query-A;
- grouped output;
- a controlled compressor/state harness;
- LM-head selected-row evidence;
- a five-step Markov microprogram; and
- operator-local schedule and service paths.

These slices are valuable numerical, artifact, state, and failure oracles.

### 2.3 Open system boundary

The repository still lacks:

- one common production graph/kernel export;
- complete graph-to-hardware lowering;
- full immutable physical placement and capacity proof;
- a certified complete physical schedule;
- an operator-complete artifact-driven service engine;
- a checkpoint-derived complete transformer block;
- complete ordinary prefill/decode;
- generated-artifact RTL controller/operator integration;
- exact 200,000-token execution; and
- execution-derived performance and same-node comparison.

The structural hardware descriptor ISA draft maps the 46 semantic kinds to
macro-op families, but has no bound descriptors or complete executor. Its
ROM_MATMUL family is not promoted into the neutral IR or renamed ABI 3.0.

## 3. Release profiles

### 3.1 Ordinary target-only profile

The first mandatory profile includes:

- target token embedding;
- all ordinary target transformer layers;
- dense/shared and routed expert paths;
- target attention and sparse-index behavior;
- KV window, compressor, compressed-KV, and related state;
- mHC pre/head/post paths;
- final normalization and target vocabulary head;
- deterministic greedy argmax;
- token append, EOS, and session state; and
- pinned tokenizer/chat/tool protocol.

Every conditional ordinary path remains represented with explicit guards and
bounded route/index descriptors.

### 3.2 Speculative extension

The following are separately versioned and do not block ordinary closure:

- DSpark noise embedding and draft projections;
- five-step Markov draft generation;
- confidence and target-verification behavior;
- speculative acceptance and fallback;
- stochastic sampling and exact RNG replay; and
- seven-token or other serving-engine candidate policies.

The capability may reserve compatible fields, but no performance result may
credit speculation before its target verification, state commit, RNG, and
acceptance semantics are pinned and executed.

## 4. Architecture

The candidate DeepSeek ROM hierarchy is:

~~~text
host and reviewed management/session boundary
                    |
DeepSeek target microprogram and generation controller
                    |
model-specific multi-stage pipeline selected by physical compiler
                    |
+---------------------+------------------------------+
| immutable ROM regions and scale ROM               |
| FP8 dense/shared tensor service                    |
| MXFP4/E8M0 routed expert tensor service            |
| BF16 control and vocabulary service                |
| vector, normalization, mHC, compression            |
| route, top-k, dispatch, sparse gather, reduction   |
| SRAM activation/index/accumulator service          |
| HBM KV/compressor/compressed-state service         |
+---------------------+------------------------------+
                    |
deterministic stage links, credits, integrity, state
~~~

### 4.1 Control architecture

The ROM lane reuses the accepted ABI 3.0 management, session, state,
trap/recovery, counter, trace, and EOS semantics where compatible. The
model-specific sequencer may exploit static stage and ROM schedules, but must
still:

- execute an authenticated bounded program;
- consume bound tensor/numeric/state/schedule descriptors;
- handle runtime routes, indices, phases, and guards;
- issue asynchronous engines through explicit events;
- prevent deadlock and queue overflow;
- atomically prepare/commit/discard all mutable state;
- perform on-device target vocabulary selection; and
- publish precise success or failure.

Neither management firmware nor Python may compute an omitted operator, route,
logit, or token.

### 4.2 Immutable tensor service

The physical compiler maps:

- dense/shared FP8 matrices and scales;
- routed MXFP4 matrices and E8M0 block scales;
- BF16 embeddings, normalization, vocabulary, and control weights;
- compression, attention, mHC, router, and target-only auxiliary tensors;
- padding, integrity, BIST, repair, spare, and manifest regions; and
- explicitly excluded DSpark-only tensors for the ordinary profile.

Each format has a frozen nibble/byte order, scale orientation, block geometry,
padding rule, decode pipeline, accumulation contract, and repair interaction.
The inverse checker reconstructs canonical logical payload hashes, not only
aggregate image bytes.

### 4.3 Dynamic routing on static ROM

Expert IDs and sparse indices are runtime data. The physical schedule may be
static, but selection cannot be compile-time constant.

The design must:

- validate expert count, range, duplicates, and ordering;
- broadcast or distribute route records with transaction identity;
- enable only selected expert ROM regions;
- apply routed weights/scales exactly once;
- gather/reduce results in the frozen order;
- handle zero/edge route cases defined by the graph; and
- count actual selected work and communication.

A design that expands all experts as dense work may be used as a diagnostic
oracle but does not close the intended routed architecture or comparison.

### 4.4 Mutable state at 200K

ROM holds no mutable KV or compressor state. HBM/SRAM state objects cover:

- windowed and ordinary attention KV;
- compressed KV and valid-prefix metadata;
- raw compressor state and monotonic versions;
- per-session cursors, tombstones, generations, and retirement;
- mHC or other explicitly declared mutable resources;
- token/output/checkpoint buffers; and
- prepare/commit/discard extents.

The compiler proves capacity and addresses for exactly 200,000 prompt positions
plus the frozen decode allowance. State views never expose stale capacity rows.
Abort, reset, timeout, invalid route/index, or numeric failure advances neither
position nor committed state.

## 5. Common IR migration

### 5.1 Export requirement

After the common schema freezes, a DeepSeek exporter translates the ordinary
target path into the shared production Model Graph IR. It must preserve:

- all included nodes in source order or explicit control regions;
- tensors, shapes, layouts, checkpoint bindings, and source anchors;
- prefill/decode phases;
- runtime predicates, guards, and optional values;
- state read, prepare, commit, discard, and retirement effects;
- numeric-contract IDs and reduction/conversion boundaries;
- entrypoints and outputs; and
- exact coverage of ordinary target-only checkpoint roles.

Excluded speculative nodes/tensors are listed with reasons and their own
extension profile identity. They are not silently dropped.

### 5.2 Kernel lowering

The common Tensor Kernel IR decomposes or names every operation through
registered backend-neutral families. It records iteration domains, dependencies,
views, numerics, counter classes, and legal fusion. It does not contain:

- ROM_MATMUL;
- physical stage, macro, wordline, or route slot;
- HBM/SRAM address or bank;
- framework function names as execution callbacks; or
- an opaque DeepSeek operation with no engine/numeric contract.

Compound semantic operations such as mHC, compressor, sparse attention, and
routed SwiGLU may lower to several kernels when intermediate values and ordering
remain explicit.

### 5.3 Coverage gates

The exporter emits:

- included and excluded graph-node counts;
- operation-kind and checkpoint-role coverage;
- state-resource/action coverage;
- numeric/reference-owner coverage;
- lowering and cost-class coverage;
- unknown/opaque operation count;
- source and graph identity; and
- an independent reconstruction report.

Unknown, unpriced, unreferenced, or unbound counts must be zero for the ordinary
profile.

## 6. ROM physical compiler

The deterministic compiler performs:

1. source/checkpoint/common-IR validation;
2. ordinary-profile tensor and operation closure;
3. canonical format/scale/layout conversion;
4. candidate stage partition and capacity analysis;
5. ROM macro/region placement with repair and reserve;
6. tensor/vector/route/reduce/state engine assignment;
7. SRAM activation/index/accumulator allocation;
8. HBM state layout for the declared context;
9. deterministic NoC/stage-link schedule and credit proof;
10. compact program, descriptor, event, and queue emission;
11. known-answer, counter, capacity, and trace contracts;
12. image/manifest publication;
13. independent inverse and schedule checking; and
14. byte-identical second clean build.

### 6.1 Stage topology

The current public-reference proxy uses a two-stage Flash partition, while
technology-envelope studies may choose another count. Neither is assumed by the
new compiler.

Candidate partitions are evaluated with exact:

- post-padding/scale/integrity/repair ROM bytes;
- largest indivisible layer/tensor region;
- routed and dense bandwidth;
- cross-stage activation and collective traffic;
- local SRAM and HBM state capacity;
- clock, wire, power, thermal, and yield constraints; and
- complete schedule legality.

The selected stage count is one physical-design result for this DeepSeek ROM
release. It does not constrain the Qwen ROM or shared HBM hardware.

### 6.2 Independent image checker

The checker independently:

- reopens the complete canonical checkpoint application;
- reconstructs every included logical tensor and scale from ROM images;
- checks format packing, padding, integrity, spares, and repair remaps;
- proves unique placement and legal capacity per physical stage;
- verifies excluded extension tensors cannot be addressed;
- reconstructs HBM/SRAM object bounds and state capacity;
- checks program/descriptors against graph/kernel IDs; and
- emits exact missing, duplicate, alias, overflow, and corruption failures.

### 6.3 Independent schedule checker

The schedule checker reconstructs:

- all producer/consumer dependencies;
- ROM bank/tensor-lane/vector/route/reduce use;
- SRAM bank/port/occupancy conflicts;
- runtime route and sparse-index bounds;
- NoC and stage-link paths, slots, credits, and retry buffers;
- event producers, wait sets, queue occupancy, and deadlock freedom;
- state transaction order; and
- expected work, byte, flit, and stall counter bounds.

It does not call the schedule generator.

## 7. Functional simulator

### 7.1 Artifact-only target device

The functional simulator verifies and consumes only the published deployment:

- common graph/kernel identities;
- ROM images and physical map;
- tensor/numeric/state/schedule descriptors;
- generated target microprogram;
- HBM/SRAM initial state;
- request/workload and tokenizer/generation policy; and
- expected counter contract.

It executes all included ordinary-path operations through independently
qualified target-precision native kernels. Operator-local service code is reused
only after adapting it to bound descriptors and removing caller-supplied
intermediates that are not deployment inputs.

The simulator must not:

- call the official model or PyTorch as a hidden operator;
- accept caller-supplied base logits, routes, activations, or state that the
  graph should produce;
- use a synthetic tensor in an acceptance run;
- skip non-selected experts without executing the route that selected them; or
- call the current structural lowering table as if it were an executor.

### 7.2 State and generation

One request:

1. validates session, position, context, program, and memory windows;
2. executes prefill or decode graph work;
3. prepares all affected KV/compressor state;
4. computes target vocabulary logits;
5. performs deterministic target argmax and token validation;
6. tests the official EOS set;
7. atomically commits state and token position;
8. returns the token and trace/counters; and
9. loops for GENERATE until first EOS or the declared bound.

The returned sequence includes EOS. No post-EOS request executes.

### 7.3 Scalability

Before 200K, execute increasing natural contexts and publish:

- functional and cycle transactions per host second;
- time by tensor, vector, attention, route, state, and selection class;
- host RAM, accelerator-state image, temporary disk, and trace growth;
- checkpoint/restart time and identity;
- actual sparse/routed work distributions;
- projected 200K completion time and resource margin; and
- exact differential evidence for every simulator optimization.

If projection is infeasible, optimize native kernels, streaming, state storage,
and trace representation. Do not replace 200K with an analytical-only run.

## 8. Cycle simulator

The data-bearing cycle model includes:

- program fetch, loops, events, queue occupancy, and retirement;
- per-format ROM reads, decode, scale, tensor issue, and reduction;
- dynamic expert route distribution and actual selected work;
- sparse-index gather and attention work;
- vector/compression/mHC pipelines;
- SRAM banks/ports/ECC/arbitration and HBM state timing;
- NoC and stage-link credits, retries, and contention;
- prepare/commit/discard and error drain;
- vocabulary/argmax/EOS latency;
- power/thermal throttle events; and
- exact utilization, stall, byte, flit, cycle, and energy-event counters.

The same deployment drives functional and cycle modes. A timing schedule that
does not carry or depend on real data cannot close correctness or 200K.

## 9. RTL plan

RTL integration proceeds vertically:

1. target program admission, loop/event/queue/state control;
2. immutable multi-format ROM wrapper, integrity, repair, and no-write proof;
3. FP8 dense/shared tensor slice with real payloads;
4. MXFP4/E8M0 routed tensor slice with runtime expert IDs;
5. vector/RMSNorm/conversion and ordered reduction;
6. sparse-index/attention and HBM state;
7. compressor and mHC representative transactions;
8. target vocabulary gather/argmax/token/EOS;
9. one complete checkpoint-derived transformer block;
10. multi-stage generated schedule with backpressure;
11. abort, reset, retry, repair degradation, and recovery;
12. representative complete target program correlation; and
13. formal, coverage, CDC/RDC, DFT, power, and physical entry.

The existing ot_stage_* shell may seed lifecycle, session, link, RAS, power, and
test behavior. Its abstract functional macro cannot remain in an acceptance path.
The new generated program must causally drive real service blocks or qualified
co-simulation boundaries.

## 10. Workload and correctness plan

### 10.1 Short ordinary generation

Before the mandatory context:

- render pinned natural chat contexts;
- tokenize with the authenticated local tokenizer;
- execute complete target prefill and at least 32 ordinary decode steps or first
  EOS;
- retain every token ID and decoded fragment;
- verify tokenizer legality and no post-EOS execution;
- compare logits, routes, sparse indices, states, and tokens at frozen
  boundaries; and
- run a simple pinned agentic/tool context through causal environment turns.

These short runs close protocol and semantics only, not long-context capacity or
performance.

### 10.2 Exact 200,000-token acceptance

The mandatory workload contains exactly 200,000 natural prompt tokens rendered
under the frozen DeepSeek message/template contract, followed by ordinary
target-model greedy decode through the first official EOS or a predeclared
maximum-new-token bound.

The retained evidence includes:

- complete rendered context or content-addressed lossless chunks;
- exact prompt-token count and IDs;
- every generated token ID including EOS when reached;
- raw and visible decoded output;
- vocabulary legality and tokenizer round-trip;
- every route/top-k/sparse-index decision required by the acceptance policy;
- committed KV/compressor state generations and checkpoint identities;
- functional and cycle operation/memory/link/state/token counters;
- wall-clock and simulator-resource measurements;
- first divergence if any; and
- same-workload comparison with the DeepSeek HBM result.

A 199,999-token run, repeated synthetic token run, capacity-only allocation, or
timing replay does not close this gate.

### 10.3 Agentic context

The agentic workload uses the pinned DeepSeek chat/tool template and a small
deterministic environment. The model must generate the tool call; a strict
parser validates it; the actual isolated action result becomes the next prompt;
and final output is checked independently. The workload remains separate from
the 200K natural-language quality claim unless a 200K agent prompt is explicitly
frozen.

## 11. 130-nm physical plan

The DeepSeek ROM and DeepSeek HBM comparison uses one selected public 130-nm
process and common PVT, clock-view, SRAM, HBM, and evidence policies.

Physical convergence includes:

- format-specific ROM macro/slice characterization;
- FP8 and MXFP4/E8M0 tensor tiles;
- vector/route/reduce/state/control tiles;
- representative stage floorplan and deterministic NoC;
- clock, route, congestion, EM/IR proxy, power, and thermal analysis;
- repair/spare/BIST/DFT and yield sensitivity;
- stage-link and package assumptions;
- actual execution activity; and
- compiler/capability feedback followed by recompilation and rerun.

HBM state, HBM PHY, package, and production mask-ROM evidence remain separately
classified. A public PDK result is methodology evidence, not target foundry
signoff.

## 12. Milestones

| Gate | Outcome | Exit evidence |
|---|---|---|
| DROM-A0 | architecture/profile accepted | TA-A3-ARCH-0 and ordinary/speculative split review |
| DROM-I1 | common-IR export | zero unknown/unpriced operations, complete ordinary tensor/state/numeric coverage |
| DROM-P2 | complete ROM physical plan | all included tensors inverse-reconstruct; stage/capacity/repair/schedule legal |
| DROM-V3 | complete checkpoint block | artifact-only dense/routed/sparse/state block exact against independent references |
| DROM-F4 | complete short target model | ordinary prefill/decode, target argmax/EOS, legitimate output, no fallback |
| DROM-S5 | data-bearing cycle closure | causal mixed-format/route/state timing and reconciled counters |
| DROM-R6 | representative ROM RTL | generated program and complete block correlate under faults/stalls |
| DROM-C7 | chat and agent context | natural output and causal tool protocol pass |
| DROM-200K8 | exact mandatory context | 200,000 natural tokens plus ordinary decode, state/token/counter evidence |
| DROM-PHY9 | same-node physical convergence | characterized capability, recompile, rerun |
| DROM-REL10 | DeepSeek ROM release | reproducible release and governed DeepSeek ROM-versus-HBM comparison |

## 13. Agent ownership and handoff

The DeepSeek ROM agent owns only the allocated DeepSeek ROM compiler, simulator,
RTL, physical, and result paths. It consumes common schemas and target numerical
references without editing them to fit a backend.

Every handoff records:

- main baseline and delivered commit;
- source/checkpoint/tokenizer/common-schema identities;
- ordinary versus speculative profile coverage;
- graph/kernel/physical/program/schedule identities;
- image inverse and schedule certificate identities;
- functional/cycle/RTL report identities;
- exact tests, payload scope, and not-run gates;
- synthetic or caller-supplied data still present in a diagnostic;
- first failure/divergence;
- physical evidence class and external assumptions; and
- next gate authorized.

## 14. Immediate next work after TA-A3-ARCH-0

The first DeepSeek ROM implementation tranche is:

1. define the ordinary target-only graph slice and explicit DSpark exclusions;
2. export a small but connected source region into the common IR;
3. bind one checkpoint-derived path that includes dense compute, a runtime
   predicate or route, and a transactional state effect;
4. lower it to a ROM Physical Plan and bound descriptors;
5. execute it through the common control/state semantics without caller-supplied
   intermediates;
6. compare every boundary with independent target references; and
7. add breadth only after the entire vertical chain passes.

This replaces the current collection of isolated operator accomplishments with
one continuously verified model-to-hardware path.
