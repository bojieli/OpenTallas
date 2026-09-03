# DeepSeek-V4 Flash ROM hardware implementation plan

**Plan ID:** TA-DS-ROM-3.0

**Status:** active under frozen ABI 3.0; TA-A3-ARCH-0 is closed

**Model profile:** DeepSeek-V4-Flash-0731 ordinary target-only inference

**Mandatory context:** exactly 200,000 natural prompt tokens

**Physical topology:** one wafer-scale logical ROM accelerator with distributed
HBM mutable-buffer attachment
**Issue date:** 2026-08-29

## 1. Mission

This lane builds a DeepSeek-V4 Flash-specific immutable-weight ROM compiler,
artifact-driven simulator, cycle model, RTL hierarchy, and physical plan. It may
use a different tensor-lane mix, wafer partition, netlist, and masks from the
Qwen ROM product. It does not need to run Qwen dynamically.

Wafer scale is mandatory for this lane, not one candidate discovered after
compilation. The complete ordinary model is distributed across a reticle/tile
hierarchy with a very-low-latency, very-high-bandwidth on-wafer fabric and
distributed HBM attachment for mutable buffers. The host sees one logical
accelerator and does not sequence a pipeline of conventional chips. If this
wafer boundary cannot meet capacity, communication, power, thermal, yield,
repair, timing, or correctness gates, the architecture is redesigned or
rejected rather than silently becoming an off-package cluster.

The first release executes the complete ordinary target-model prefill/decode
path. DSpark draft generation and speculative acceptance are separate
extensions. Their current semantic and microprogram evidence is retained, but
cannot substitute for ordinary target-model execution.

The lane is complete only when:

- all ordinary-path graph nodes and checkpoint roles lower into generated
  deployment artifacts;
- every immutable tensor/scale has one legal ROM location and inverse proof;
- all required mixed-format, MoE, sparse-attention, compressor, mHC, and buffer
  operations execute causally;
- a complete checkpoint-derived transformer block and then complete model run
  match independent references;
- the first official EOS stops ordinary decode with legitimate token output;
- the exact 200,000-token natural context executes end to end;
- all required on-wafer transfers, multicast, sparse gather, expert dispatch,
  collectives, reductions, HBM locality, and synchronization execute causally;
- representative generated programs execute through ROM RTL/co-simulation; and
- separate SKY130 and ASAP7 wafer reports can be compared with the DeepSeek
  32-node HBM deployment in the matching technology view.

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
- a frozen wafer reticle/tile topology, distributed-HBM plan, or causal
  on-wafer-fabric model;
- an operator-complete artifact-driven service engine;
- a checkpoint-derived complete transformer block;
- complete ordinary prefill/decode;
- generated-artifact RTL controller/operator integration;
- exact 200,000-token execution; and
- execution-derived performance and same-technology-view comparison.

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
- KV window, compressor history, compressed KV, and related buffers;
- mHC pre/head/post paths;
- final normalization and target vocabulary head;
- deterministic greedy argmax;
- token append, EOS, and run-local control data; and
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
credit speculation before its target verification, token-step fence, RNG, and
acceptance semantics are pinned and executed.

## 4. Architecture

The mandatory DeepSeek ROM hierarchy is:

~~~text
host and reviewed management/session boundary
                    |
DeepSeek target microprogram and generation controller
                    |
wafer-global control/event/session boundary
                    |
reticle/tile hierarchy over a stitched on-wafer fabric
                    |
+---------------------+------------------------------+
| immutable ROM regions and scale ROM               |
| FP8 dense/shared tensor service                    |
| MXFP4/E8M0 routed expert tensor service            |
| BF16 control and vocabulary service                |
| vector, normalization, mHC, compression            |
| route, top-k, dispatch, sparse gather, reduction   |
| SRAM activation/index/accumulator service          |
| HBM KV/compressor/compressed-buffer service        |
+---------------------+------------------------------+
                    |
distributed HBM controllers/PHY attachment for mutable buffers
~~~

### 4.1 Control architecture

The ROM lane reuses the accepted ABI 3.0 management, run, live-buffer,
trap, counter, trace, and EOS semantics where compatible. The
model-specific sequencer may exploit static on-wafer and ROM schedules, but must
still:

- execute an authenticated bounded program;
- consume bound tensor/numeric/memory/schedule descriptors;
- handle runtime routes, indices, phases, and guards;
- issue asynchronous engines through explicit events;
- prevent deadlock and queue overflow;
- write mutable buffers directly and order their visibility with existing
  events plus the token-step fence;
- perform on-device target vocabulary selection; and
- publish precise success or failure.

Neither management firmware nor Python may compute an omitted operator, route,
logit, or token.

Global control uses one deployment/session/transaction namespace. Reticle-local
sequencers may issue admitted subprograms, but no firmware or host loop may
sequence model layers, experts, or collectives across the wafer.

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

### 4.4 Mutable live buffers at 200K

ROM holds no mutable KV or compressor data. Ordinary HBM/SRAM memory objects
cover:

- windowed and ordinary attention KV;
- compressed KV and valid-prefix metadata;
- raw compressor history;
- run-local cursors and valid extents;
- mHC or other explicitly declared mutable resources;
- token/output buffers; and
- compiler-proved capacity and tensor-view extents.

The compiler proves capacity and addresses for exactly 200,000 prompt positions
plus the frozen decode allowance. Tensor views never expose stale capacity
rows. A timeout, invalid route/index, numeric failure, or unrecoverable link
fault terminates the run; partial buffers are discarded with that failed run
rather than rolled back or reused.

HBM is physically distributed around the wafer/package boundary. The compiler
binds every mutable memory object to one or more attachment/locality domains
and prices all access and replication. A single zero-latency uniform HBM abstraction is
illegal in cycle or physical acceptance.

## 5. Common IR migration

### 5.1 Export requirement

After the common schema freezes, a DeepSeek exporter translates the ordinary
target path into the shared production Model Graph IR. It must preserve:

- all included nodes in source order or explicit control regions;
- tensors, shapes, layouts, checkpoint bindings, and source anchors;
- prefill/decode phases;
- runtime predicates, guards, and optional values;
- mutable-buffer reads/writes, valid extents, dependencies, and token-step
  fence effects;
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
- live-buffer object/access coverage;
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
4. mandatory wafer reticle/tile partition and capacity analysis;
5. ROM macro/region placement with repair and reserve;
6. tensor/vector/route/reduce engine assignment;
7. SRAM activation/index/accumulator allocation;
8. HBM live-buffer layout for the declared context;
9. deterministic local/on-wafer schedule, collective plan, and credit proof;
10. compact program, descriptor, event, and queue emission;
11. known-answer, counter, capacity, and trace contracts;
12. image/manifest publication;
13. independent inverse and schedule checking; and
14. byte-identical second clean build.

### 6.1 Wafer topology and communication contract

The compiler selects quantitative reticle/tile counts, placement, routes, and
HBM attachment points inside the mandatory wafer-scale boundary. It does not
inherit the historical two-stage partition, 8-by-8 reticle grid, 4,096-tile
proxy, 100-TB/s proxy, or stage-link assumptions from `spec/ARCHITECTURE.md`.

Candidate wafer partitions are evaluated with exact:

- post-padding/scale/integrity/repair ROM bytes and largest indivisible region;
- reticle/tile capacity, local SRAM, and distributed HBM buffer capacity;
- dense, routed, sparse, activation, multicast, reduction, collective, and
  vocabulary traffic derived from compiled execution;
- on-wafer path length, bisection bandwidth, serialization, hop/switch latency,
  credits, buffers, congestion, retry, and synchronization bounds;
- clock, reset, power, thermal, fault-containment, stitching, and yield domains;
- spare tiles/links, quarantine, degraded topology, repair maps, and
  yield-aware recompilation; and
- complete schedule legality and deadlock freedom.

Public contemporary Cerebras-class specifications are source-locked as a
reference envelope and sensitivity point. They are not copied as achieved
OpenTallas bandwidth or latency. The release capability freezes its own minimum
bisection/collective bandwidth and maximum communication latency from compiled
DeepSeek traces plus the selected SKY130 or ASAP7 methodology.

### 6.2 Independent image checker

The checker independently:

- reopens the complete canonical checkpoint application;
- reconstructs every included logical tensor and scale from ROM images;
- checks format packing, padding, integrity, spares, and repair remaps;
- proves unique placement and legal capacity per reticle, tile, and wafer;
- verifies excluded extension tensors cannot be addressed;
- reconstructs HBM/SRAM object bounds and live-buffer capacity;
- checks program/descriptors against graph/kernel IDs; and
- emits exact missing, duplicate, alias, overflow, and corruption failures.

### 6.3 Independent schedule checker

The schedule checker reconstructs:

- all producer/consumer dependencies;
- ROM bank/tensor-lane/vector/route/reduce use;
- SRAM bank/port/occupancy conflicts;
- runtime route and sparse-index bounds;
- local and on-wafer paths, slots, collectives, credits, and retry buffers;
- event producers, wait sets, queue occupancy, and deadlock freedom;
- live-buffer producer/consumer and token-fence order; and
- expected work, byte, flit, and stall counter bounds.

It does not call the schedule generator.

**Implementation status (2026-09-01).** This checker is now
`compiler/backends/rom/common/check.py`, governed by
`make abi3-rom-schedule-check`. The committed two-product artifact is
`results/abi3/rom_schedule_checks.json`; it binds the checker, campaign tool,
neutral IR, capability, deployment manifest, descriptor table, and program by
SHA-256. The checker parses the emitted ROM plan as data and reconstructs the
wafer coordinate table and its topology digest without importing
`compiler.backends.rom.common.program`, `.image`, `qwen3`, or `deepseek_v4`.
Focused mutations keep the descriptor table and program digest-consistent and
are admitted by the generic ABI verifier, then demonstrate that the independent
checker refuses a wrong queue, ROM bank, tile width, producer event, or credit
bound.

The certificate is static and artifact-semantic. Its byte/flit/stall quantities
are conservative bounds over maximum loop trips, not observed cycle counters;
it proves that the published route-coordinate table is complete, disjoint, and
digest-bound, not that a physical link closes timing. Cycle contention and
physical implementation remain the later RTL/physical gates rather than being
silently promoted here.

## 7. Functional simulator

### 7.1 Artifact-only target device

The functional simulator verifies and consumes only the published deployment:

- common graph/kernel identities;
- ROM images and physical map;
- tensor/numeric/memory/schedule descriptors;
- generated target microprogram;
- HBM/SRAM initial buffer images;
- request/workload and tokenizer/generation policy; and
- expected counter contract.

It executes all included ordinary-path operations through independently
qualified target-precision native kernels. Operator-local service code is reused
only after adapting it to bound descriptors and removing caller-supplied
intermediates that are not deployment inputs.

The simulator must not:

- call the official model or PyTorch as a hidden operator;
- accept caller-supplied base logits, routes, activations, or buffers that the
  graph should produce;
- use a synthetic tensor in an acceptance run;
- skip non-selected experts without executing the route that selected them; or
- call the current structural lowering table as if it were an executor.

Functional mode instantiates the declared reticle/tile topology, distributed
object ownership, and HBM locality. It executes every cross-tile transfer and
collective causally. It may omit physical link cycles in this mode, but it may
not replace communication with direct global-memory access or a precombined
reduction.

### 7.2 Live buffers and generation

One request:

1. validates run, position, context, program, and memory windows;
2. executes prefill or decode graph work;
3. writes all affected KV/compressor buffers through declared views;
4. computes target vocabulary logits;
5. performs deterministic target argmax and token validation;
6. tests the official EOS set;
7. executes the token-step fence, exposing the completed writes and token;
8. returns the token and trace/counters; and
9. loops for GENERATE until first EOS or the declared bound.

The returned sequence includes EOS. No post-EOS request executes.

### 7.3 Scalability

Before 200K, execute increasing natural contexts and publish:

- functional and cycle transactions per host second;
- time by tensor, vector, attention, route, buffer access, and selection class;
- host RAM, accelerator-memory image, temporary disk, and trace growth;
- actual sparse/routed work distributions;
- on-wafer event/flit rates, communication critical path, and distributed-HBM
  locality;
- projected 200K completion time and resource margin; and
- exact differential evidence for every simulator optimization.

If projection is infeasible, optimize native kernels, streaming, buffer storage,
and trace representation. Do not replace 200K with an analytical-only run.

## 8. Cycle simulator

The data-bearing cycle model includes:

- program fetch, loops, events, queue occupancy, and retirement;
- per-format ROM reads, decode, scale, tensor issue, and reduction;
- dynamic expert route distribution and actual selected work;
- sparse-index gather and attention work;
- vector/compression/mHC pipelines;
- SRAM banks/ports/ECC/arbitration and HBM buffer timing;
- local/on-wafer routes, serialization, credits, retries, collectives,
  congestion, and contention;
- live-buffer writes, token-step fence visibility, and terminal error handling;
- vocabulary/argmax/EOS latency;
- power/thermal throttle events; and
- exact utilization, stall, byte, flit, cycle, and energy-event counters.

The same deployment drives functional and cycle modes. A timing schedule that
does not carry or depend on real data cannot close correctness or 200K.

## 9. RTL plan

RTL integration proceeds vertically:

1. target program admission, loop/event/queue/fence control;
2. immutable multi-format ROM wrapper, integrity, repair, and no-write proof;
3. FP8 dense/shared tensor slice with real payloads;
4. MXFP4/E8M0 routed tensor slice with runtime expert IDs;
5. vector/RMSNorm/conversion and ordered reduction;
6. sparse-index/attention and HBM buffers;
7. compressor and mHC representative transactions;
8. target vocabulary gather/argmax/token/EOS;
9. one complete checkpoint-derived transformer block;
10. reticle-local and cross-reticle generated schedules with backpressure;
11. wafer multicast/collective, distributed-HBM, and token-step fence paths;
12. fail-stop fault completion, fresh-run reset, tile/link detection, and ROM
    repair degradation;
13. representative complete target program correlation; and
14. formal, coverage, CDC/RDC, DFT, power, and hierarchical physical entry.

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
- terminal-fence KV/compressor/token buffer identities;
- functional and cycle operation/memory/link/buffer/token counters;
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

## 11. SKY130 and ASAP7 wafer-scale physical plan

The DeepSeek ROM wafer is evaluated in two separate technology views. SKY130 is
the mature open 130-nm implementation/verification baseline. ASAP7 is the
academic predictive 7-nm projection and is not production foundry signoff.
Within each view, DeepSeek ROM and the 32-node DeepSeek HBM cluster use common
PVT, clock-view, SRAM, external HBM/fabric-boundary, workload, and evidence
policies. Values are never mixed between SKY130 and ASAP7.

Physical convergence includes:

- format-specific ROM macro/slice characterization;
- FP8 and MXFP4/E8M0 tensor tiles;
- vector/route/reduce/control tiles;
- representative tile and reticle floorplans plus deterministic local/on-wafer
  NoC;
- clock, route, congestion, EM/IR proxy, power, and thermal analysis;
- repair/spare/BIST/DFT and yield sensitivity;
- reticle stitching, wafer clock/power/reset, distributed-HBM/package, on-wafer
  link, cluster-link comparator, and thermal assumptions;
- actual execution activity; and
- compiler/capability feedback followed by recompilation and rerun.

Closure is hierarchical: characterize exact service tiles, close representative
reticle regions, extract cross-reticle links, then assemble wafer-level timing,
power, clock, thermal, repair, and yield models. A tile-only P&R result or an
ideal stitched-wire assumption cannot close the wafer gate.

HBM buffers, HBM PHY, package, and production mask-ROM evidence remain separately
classified. A public PDK result is methodology evidence, not target foundry
signoff.

## 12. Milestones

| Gate | Outcome | Exit evidence |
|---|---|---|
| DROM-A0 | architecture/profile accepted | TA-A3-ARCH-0 and ordinary/speculative split review |
| DROM-I1 | common-IR export | zero unknown/unpriced operations, complete ordinary tensor/buffer/numeric coverage |
| DROM-P2 | complete wafer physical plan | all included tensors inverse-reconstruct; reticle/tile/wafer capacity, repair, fabric, and schedule legal |
| DROM-V3 | complete checkpoint block | artifact-only dense/routed/sparse/live-buffer block exact against independent references |
| DROM-F4 | complete short target model | ordinary prefill/decode, target argmax/EOS, legitimate output, no fallback |
| DROM-S5 | data-bearing cycle closure | causal mixed-format/route/live-buffer/on-wafer timing and reconciled counters |
| DROM-R6 | representative ROM RTL | generated program, complete block, reticle and fabric paths correlate under faults/stalls |
| DROM-C7 | chat and agent context | natural output and causal tool protocol pass |
| DROM-200K8 | exact mandatory context | 200,000 natural tokens plus ordinary decode, buffer/token/counter evidence |
| DROM-PHY9-SKY | SKY130 wafer convergence | hierarchical characterized capability, recompile, rerun |
| DROM-PHY9-A7 | ASAP7 wafer projection | separate academic hierarchical projection, recompile, rerun, limitations |
| DROM-REL10 | DeepSeek ROM release | reproducible release and governed DeepSeek ROM-versus-HBM comparison |

## 13. Agent ownership and handoff

The DeepSeek ROM agent owns only the allocated DeepSeek ROM compiler, simulator,
RTL, physical, and result paths. It consumes common schemas and target numerical
references without editing them to fit a backend.

Every handoff records:

- main baseline and delivered commit;
- source/checkpoint/tokenizer/common-schema identities;
- ordinary versus speculative profile coverage;
- wafer topology, reticle/tile/repair map, distributed-HBM, and fabric
  capability identities;
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
   predicate or route, a cross-tile/on-wafer transfer, and a mutable live-buffer
   effect;
4. lower it to a ROM Physical Plan and bound descriptors;
5. execute it through the common control/live-buffer semantics without caller-supplied
   intermediates;
6. compare every boundary with independent target references; and
7. add breadth only after the entire vertical chain passes.

This replaces the current collection of isolated operator accomplishments with
one continuously verified model-to-hardware path.
