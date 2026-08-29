# Shared HBM/SRAM tensor-accelerator implementation plan

**Plan ID:** TA-HBM-3.0

**Status:** implementation blocked on TA-A3-ARCH-0

**Hardware products:** one programmable tensor accelerator

**Deployment targets:** Qwen3-8B and DeepSeek-V4 Flash
**Issue date:** 2026-08-29

## 1. Mission and definition of done

This lane builds one production-quality HBM/SRAM tensor accelerator, compiler,
functional simulator, cycle simulator, and RTL 3.0 hierarchy. The identical
elaborated hardware must run:

- Qwen3-8B at the exact 8,000-token acceptance context; and
- DeepSeek-V4 Flash at the exact 200,000-token acceptance context.

Different checkpoint images, descriptors, programs, numeric profiles, and
firmware-approved deployments are allowed. Model-selected RTL parameters,
generated model modules, hard-coded layer counts, and resynthesis are not.

The lane is complete only when both checkpoints:

1. compile through the common production graph and kernel contracts;
2. produce legal HBM, SRAM, descriptor, schedule, and ABI 3.0 artifacts;
3. execute complete natural prefill and ordinary decode from those artifacts;
4. stop on the first official EOS and return legitimate decoded tokens;
5. match the frozen target numerical/token policy;
6. correlate representative complete programs with RTL 3.0;
7. reconcile execution and timing counters; and
8. recompile and execute against one characterized 130-nm capability.

The design is called a tensor accelerator. It is not a GPU, does not implement
SIMT threads or warps, and is not represented as a reproduction of an NVIDIA
product.

## 2. Retained starting point

### 2.1 Useful assets

The merged main branch provides:

- production Model Graph v2 and a complete Qwen exporter;
- a complete Qwen 617-operation neutral Kernel IR;
- Qwen HBM shard, SRAM plan, state, and ABI 2.5 deployment artifacts;
- complete Qwen functional model execution and independent references;
- exact short token, state, and counter goldens;
- ABI 2.5 decoder and bounded DMA, add, RMSNorm, projection, per-head RMSNorm,
  and RoPE RTL slices;
- a complete DeepSeek semantic/operator ledger and qualified target references;
- DeepSeek checkpoint locking and canonical assignment;
- several DeepSeek artifact-driven vertical slices; and
- existing HBM, SRAM-boundary, stage, RAS, power, link, and physical-methodology
  RTL blocks.

### 2.2 Boundaries that remain open

The current implementation is not the target system:

- Qwen ABI 2.5 expands one forward step into 924,386 commands and relies on
  software sequencing;
- no command processor implements complete program fetch, loops, events,
  queues, traps, or transactional retirement;
- no on-device argmax/EOS generation loop exists;
- no common DeepSeek graph or Kernel IR export exists;
- no DeepSeek HBM deployment or full execution exists;
- no one-hardware capability proof covers the combined model union;
- the functional simulator is not a production cycle model;
- current RTL slices are individually bounded and partly command-range-specific;
  and
- no complete layer is connected through one production controller RTL path.

Existing artifacts are migration goldens. They are not modified to make ABI 3.0
appear complete.

## 3. Hardware architecture

The planned hierarchy is:

~~~text
host transport / IOMMU
        |
submission and completion queues
        |
RV32 management complex
        |
deployment/session tables and ABI 3.0 admission
        |
deterministic microsequencer
        |
event scoreboard and engine queues
        |
+-------+---------+----------+----------+----------+----------+
| DMA/HBM | tensor | vector | attention | route/reduce | state/select |
+-------+---------+----------+----------+----------+----------+
        |
banked SRAM scratchpad + deterministic NoC
        |
external HBM controller/PHY boundary
~~~

### 3.1 Management and command processing

The management complex and microsequencer implement TA-ADR-003 exactly. Firmware
owns administrative policy; the hardware sequencer owns all per-model execution.
The acceptance path has no firmware tensor operation and no Python per-command
loop.

The controller must support:

- authenticated deployment admission;
- separate host, descriptor, and device ABI versions;
- compact bounded loops and predicates;
- asynchronous engine launch;
- queue-space waits and event dependencies;
- acquire/release fences;
- per-session transaction serialization and cross-session concurrency;
- atomic multi-resource state commit;
- first-fault poison, cancel, drain, discard, and completion;
- generation until EOS or maximum bound; and
- stable counters and trace checkpoints.

### 3.2 HBM hierarchy

HBM holds:

- all immutable weights and scales;
- persistent KV and compressor state;
- program/descriptor bundles where configured;
- long-lived token and output buffers; and
- spill objects explicitly admitted by the compiler.

Every allocation has one object ID, address window, bound, alignment, integrity
policy, owner, and lifetime. Weight pages must be resident before execution.
Host demand paging and unreported framework memory are illegal.

The HBM frontend supports multiple channels/pseudo-channels, tagged requests,
out-of-order responses, integrity/error status, bounded retries, backpressure,
and per-object accounting. Channel count and timing are capability values
selected after physical and package review.

### 3.3 SRAM hierarchy

SRAM is explicitly managed, banked scratchpad rather than an implicit coherent
cache. The physical planner allocates:

- activation tiles;
- staged weights and scales;
- FP32 accumulators;
- attention working sets;
- route/index buffers;
- state prepare buffers;
- descriptor and queue storage where selected; and
- output/token staging.

The compiler proves lifetime, bank, port, alignment, and capacity legality.
The cycle model and RTL enforce arbitration, conflicts, response latency, ECC,
and backpressure. A logical allocation that passes aggregate capacity but
violates a bank or port bound fails.

### 3.4 Compute and service engines

One hardware capability includes:

| Engine | Qwen requirement | DeepSeek requirement |
|---|---|---|
| Tensor | BF16 by BF16, FP32 accumulation | BF16, FP8 E4M3FN, MXFP4 E2M1 with E8M0 scales, dense/shared/routed forms |
| Vector | RMSNorm, head RMSNorm, RoPE, add, SiLU-gate, conversions | the same base plus FP8/FP4 QDQ, Hadamard, compression, mHC, sqrt-softplus, target capture |
| Attention | dense causal GQA | dense and sparse attention, compressed views, model-specific scale/mask descriptors |
| Route | no-op for ordinary Qwen | biased/top-k route, hash/index, expert dispatch, weight normalization |
| Reduce | tensor/vector reductions and vocabulary gather | partition/tile/group/expert/mHC/vocabulary reductions |
| State | 36 Qwen KV resources | window KV, compressed KV, compressor and other declared resources |
| Selection | deterministic vocabulary argmax and EOS | deterministic vocabulary argmax and EOS; optional sampling is later |

The datapath may share lanes between modes, but every mode has independently
characterized latency, initiation interval, energy, numeric status, and counter
semantics.

### 3.5 No model-specific hardware switch

The release build must prove:

- one RTL source inventory;
- one elaboration parameter set;
- one synthesized netlist digest;
- one capability record;
- no model ID input to a generate block or hard-coded command decoder; and
- successful admission and execution of both deployments on that same build.

Conditional behavior comes only from legal descriptors and capability bits.

## 4. Compiler implementation

### 4.1 Common frontend dependency

This lane consumes, but does not own, the common production Model Graph and
Tensor Kernel schemas.

The Qwen adapter must reproduce all 617 current operations and 36 transactional
states. The DeepSeek adapter must export the ordinary target-model path from the
2,136-node ledger with every included node, predicate, state effect, numeric
contract, and checkpoint role accounted for. DSpark speculative execution is a
separate profile and does not block the first ordinary target deployment.

### 4.2 HBM/SRAM Physical Plan IR

The backend emits a versioned physical plan containing:

- immutable and mutable object inventory;
- HBM channel, address, alignment, stripe, and integrity mapping;
- SRAM region, bank, port, lifetime, and ownership allocation;
- tensor tile and vector chunk definitions;
- state prepare/commit extents;
- engine and queue assignment;
- event dependency graph;
- compact loop/control descriptors;
- static capacity and worst-case outstanding-work proofs;
- expected functional counters;
- expected cycle-counter bounds; and
- source graph/kernel/capability bindings.

No physical field is copied back into the neutral graph or Kernel IR.

### 4.3 Lowering stages

The deterministic lowering sequence is:

1. validate the common graph, kernel, checkpoint, numeric, workload, and
   capability identities;
2. select legal tensor/vector/attention/route kernels;
3. construct symbolic loop nests and tile domains;
4. allocate persistent HBM objects;
5. allocate/reuse SRAM by proven lifetimes and bank/port constraints;
6. schedule DMA and engines with explicit events;
7. construct state transactions and generation control;
8. emit typed descriptors and ABI 3.0 programs;
9. emit HBM images/shards, manifests, and expected counters;
10. run independent inverse, liveness, capacity, and command legality checks;
    and
11. reproduce the build byte-for-byte in a second clean directory.

### 4.4 Independent checker

The checker must not import allocator, scheduler, lowering, or expected-result
code. It independently:

- rereads the graph, kernel, checkpoint, workload, and capability;
- reconstructs every HBM object and logical tensor hash;
- proves every SRAM interval, lifetime, bank, and port use;
- validates descriptor and program integrity;
- reconstructs loop work, events, queue occupancy, and absence of cyclic waits;
- proves state prepare/commit/discard closure;
- derives expected operation and byte counters; and
- rejects out-of-range, overlap, missing-work, unknown-feature, and corrupted
  artifacts.

## 5. Simulator implementation

### 5.1 Four distinct boundaries

The simulator suite has four explicit boundaries:

| Mode | Executes values | Executes ABI/control | Executes contention/timing | Claim |
|---|---:|---:|---:|---|
| independent target reference | yes | no | no | numerical oracle |
| artifact-only functional device | yes | yes | causal ordering only | full functional model execution |
| data-bearing cycle simulator | yes | yes | yes | architectural cycle/counter result |
| RTL/co-simulation | yes | RTL | RTL plus environment model | implementation correlation |

Reports never collapse these rows into one “simulation passed” statement.

### 5.2 Artifact-only functional device

The functional device:

- parses and verifies the same deployment artifacts as RTL;
- models host submission, admission, session, program, events, queues, state,
  selection, EOS, and traps;
- performs target-precision arithmetic through independently qualified native
  kernels;
- executes no framework graph or model class;
- has no hidden operator callback;
- cannot read compiler intermediates absent from the deployment;
- records every operator boundary, state generation, selected token, and
  counter; and
- supports authenticated checkpoint/restart without changing results.

Optimized compiled kernels and deterministic parallel execution are permitted
when every optimized kernel is bit-differentially qualified against the scalar
target reference. Optimization may change wall time, not operation ordering
where ordering is architectural.

### 5.3 Cycle simulator

The cycle simulator is event-driven and uses the same descriptors and numeric
results. It models:

- microsequencer fetch/decode/issue/retire;
- queue depth, event latency, scoreboard occupancy, and barriers;
- SRAM ports, banks, conflicts, arbitration, and ECC latency;
- HBM channels, bursts, row behavior, outstanding tags, responses, refresh,
  errors, and retries;
- NoC links, credits, contention, and backpressure;
- engine pipeline latency and initiation interval;
- state prepare/commit/drain behavior;
- clock/power states and watchdogs; and
- exact cycle, stall, byte, utilization, and energy-event counters.

Timing-only replay may accelerate design exploration, but it cannot close
correctness. The mandatory long runs remain data-bearing and causally dependent
on arithmetic, memory responses, selection, and state.

### 5.4 Scalability gate

Before launching the exact Qwen 8K or DeepSeek 200K campaign, the simulator must
publish:

- measured transactions per host second by phase and context;
- host memory, temporary disk, checkpoint, trace, and report growth;
- a deterministic restart interval;
- projected completion time from at least three increasing natural contexts;
- a two-times resource margin against the authorized campaign host; and
- evidence that trace compression or native kernels preserve exact results.

If the projection is infeasible, optimize and requalify the simulator. Do not
replace the required context with a smaller one.

## 6. RTL 3.0 implementation

### 6.1 Additive implementation policy

New RTL is implemented under an ABI 3.0 hierarchy after the architecture and
schemas freeze. Existing ot_ta_* blocks remain evidence until deliberately
wrapped or refactored behind a reviewed engine interface.

The initial RTL work packages are:

1. host submission/completion and capability registers;
2. deployment, object-window, session, and transaction tables;
3. program fetch, fixed-record decode, loop stack, predicates, and retirement;
4. event scoreboard, engine queues, fences, timeout, and watchdog;
5. state prepare/commit/discard and recovery;
6. DMA/HBM and banked-SRAM arbitration;
7. tensor/vector/attention/route/reduce/selection engine adapters;
8. trace and counter blocks;
9. RAS, reset, power, CDC/RDC, and test integration; and
10. generated-program top-level harness.

### 6.2 Reuse criteria for existing slices

An existing Qwen RTL engine may be reused only after proving that:

- its interface is descriptor- and capability-driven;
- it does not require one command index range, one graph node, or one model ID;
- numeric behavior matches the registered contract for all supported modes;
- errors and partial writes obey ABI 3.0 poison/state rules;
- counters use ABI 3.0 event definitions;
- stalls and reset are legal at every advertised boundary; and
- both Icarus/Verilator and formal checks pass for the new wrapper.

Prior campaign evidence remains attached to the old boundary and is not
silently relabeled ABI 3.0 evidence.

### 6.3 RTL correlation sequence

RTL bring-up proceeds through:

1. descriptor admission and control-flow fixtures;
2. loop/event/queue/state failure cases;
3. one DMA plus tensor or vector fixture;
4. Qwen ABI 2.5-equivalent full-width operation slices;
5. one connected Qwen layer;
6. one DeepSeek mixed-format route/state slice;
7. on-device vocabulary argmax, token append, and EOS;
8. one complete short generation transaction;
9. multi-session backpressure, error, abort, and reset; and
10. representative layer/program cycle correlation.

## 7. Qwen deployment track

### 7.1 Migration gate

The first Qwen ABI 3.0 program is compared with retained ABI 2.5 evidence:

- graph and kernel coverage;
- every declared numerical boundary;
- state prepare and atomic commit;
- selected token and EOS behavior;
- logically equivalent operation and byte counters; and
- intentional compression from 924,386 unrolled commands into bounded loops.

The current science natural-chat mismatch remains failed. ABI migration does not
reset or waive it.

### 7.2 Acceptance workloads

Qwen closure requires:

- short one-token and 32-decision exact differential;
- six natural chat/reasoning prompts through first EOS;
- both simple bash-agent tasks with causal tool turns and withheld tests;
- exactly 8,000 natural prompt tokens followed by frozen ordinary decode;
- a separate exactly 8,000 repeated-special-token stress run;
- the separate 8,192 capacity boundary; and
- legitimate token IDs, retained rendered context, decoded text, EOS, state,
  counters, and no post-EOS execution.

Only the natural run supports language-quality claims. Repeated-special input is
capacity/stress evidence.

## 8. DeepSeek deployment track

### 8.1 Ordinary target profile

The first DeepSeek profile includes the target model's complete ordinary
prefill/decode path and excludes speculative DSpark draft/acceptance. It must
still cover all ordinary dense/shared/routed experts, FP8/MXFP4 formats, routing,
sparse attention, compressor and KV state, mHC operations, vocabulary head, and
greedy selection.

The common capability must represent optional DSpark extensions, but the
ordinary target profile is closed before enabling them.

### 8.2 Bring-up order

DeepSeek progresses through:

1. common-IR export and exact coverage report;
2. dense BF16 and FP8 checkpoint-derived slices;
3. routed MXFP4 dispatch and expert reduction;
4. sparse attention and index selection;
5. compressor, window-KV, compressed-KV, and mHC transactions;
6. one complete checkpoint-derived transformer block;
7. complete one-step model execution;
8. short natural generation through EOS;
9. simple agentic/tool-template generation;
10. exactly 200,000 natural prompt tokens plus ordinary decode; and
11. optional DSpark/speculative extension after target closure.

### 8.3 Long-context requirements

All 200,000 positions are represented with ordinary 32-bit position and 64-bit
state/object fields. The compiler proves HBM capacity for model, scales,
metadata, KV, compressor, output, reserve, and integrity. The simulator executes
actual state reads/writes and sparse indices; it may not use an analytical
attention/KV shortcut.

## 9. Verification strategy

Every milestone includes:

- strict canonical schemas and duplicate-key rejection;
- deterministic build in two clean directories;
- independent inverse and schedule checking;
- positive, boundary, corruption, unsupported-feature, resource-exhaustion,
  and state-rollback cases;
- scalar-versus-optimized numerical differential;
- causal perturbation tests showing omitted commands/data/state change or prevent
  completion;
- Icarus and Verilator RTL comparison where RTL is in scope;
- formal safety/progress/non-vacuity for queues, events, state, and memory
  ownership;
- CDC/RDC, lint, coverage, and owned waiver records at the applicable gate;
- retained failures and first-divergence data; and
- machine-readable evidence with exact source, artifact, tool, and command
  identities.

No skipped or interrupted suite is a pass.

## 10. 130-nm implementation and HBM boundary

One public 130-nm flow is selected for the comparison after the existing
SKY130A/IHP audit. All HBM and ROM results in a comparison pair use the same
selected process, libraries, PVT policy, clock-view policy, SRAM methodology,
and evidence class. Evidence from different PDKs is not numerically mixed.

The 130-nm implementation includes:

- management and microsequencer logic;
- engine datapaths and local control;
- banked SRAM macro/compiler views or explicitly labeled proxies;
- NoC, queue, state, RAS, power, and test logic; and
- the digital HBM controller/interface boundary.

HBM DRAM, high-speed PHY, interposer/package, and stacks are external. Their
area, latency, power, capacity, and energy are separately sourced and reported.
The HBM accelerator pays all executed weight traffic; ROM designs still pay
their mutable-state HBM traffic.

Characterization feeds exact engine latency, initiation interval, queue/port
rules, frequency, and energy events into a versioned capability. Both models are
then recompiled and rerun. Hand-entered peak throughput cannot close the loop.

## 11. Milestones and exit gates

| Gate | Outcome | Required evidence |
|---|---|---|
| HBM-A0 | ABI/architecture accepted | TA-A3-ARCH-0 review |
| HBM-C1 | common HBM fixture | deterministic physical plan, ABI 3.0 program, independent inverse, functional execution and rejection cases |
| HBM-Q2 | Qwen ABI equivalence | full-width retained goldens, state/token equivalence, compact-loop proof |
| HBM-D2 | DeepSeek representative union | dense, routed, sparse, and state slices from actual checkpoint payloads |
| HBM-E3 | both complete short models | artifact-only prefill/decode, on-device argmax/EOS, legitimate text and exact state |
| HBM-S4 | data-bearing cycle closure | causal HBM/SRAM/NoC/queue timing and reconciled counters for both models |
| HBM-R5 | RTL 3.0 representative closure | same generated ABI programs, two-simulator/formal/fault evidence |
| HBM-Q8K6 | Qwen mandatory context | exact natural 8K plus separate stress, chat and agent results |
| HBM-D200K6 | DeepSeek mandatory context | exact natural 200K plus ordinary decode and short agent result |
| HBM-P7 | 130-nm converged capability | characterized RTL, recompilation, rerun, activity-derived reports |
| HBM-REL8 | shared hardware release | one netlist/capability admits both deployment releases |

## 12. Agent handoff requirements

The HBM/SRAM agent delivers only after the common owner publishes an accepted
schema bundle. Each handoff includes:

- main baseline and delivered commit;
- common schema/ABI/capability versions;
- model source/checkpoint/workload IDs;
- physical-plan, descriptor/program, image, and manifest IDs;
- independent checker and execution-report IDs;
- measured compiler/simulator resource use;
- exact test scope, tools, and not-run gates;
- current first failure if any; and
- the next model or RTL boundary authorized.

The agent does not edit Qwen or DeepSeek source semantics to make backend
lowering pass. It returns a contract-change request to the common owner.

## 13. Principal risks and redesign triggers

| Risk | Required response | Redesign trigger |
|---|---|---|
| DeepSeek union makes the shared datapath impractical | compile and characterize representative slices early | one netlist cannot legally or competitively support both models |
| command/control remains too verbose | compact verified loops and descriptor reuse | program/control traffic dominates useful execution |
| long simulation is infeasible | native exact kernels, event-driven timing, checkpoint/restart | full data-bearing target cannot finish reproducibly |
| SRAM conflicts erase tensor use | bank-aware allocation and causal cycle model | legal schedules cannot reach a useful bound |
| HBM weight traffic dominates | actual traffic scheduling and sensitivity | conservative implementation cannot meet comparison objective |
| mixed formats fail numeric quality | exact references and frozen quality gates | tokens/quality fail under implementable rules |
| dynamic routing deadlocks queues | bounded occupancy proof and randomized stress | no finite deadlock-free schedule exists |
| state failure partially advances a session | atomic prepare/commit/discard | any fault exposes partial token state |
| model logic leaks into RTL | same-netlist audit and adversarial deployment | a new model requires HDL change or resynthesis |

## 14. Immediate work after architecture approval

The first implementation is not a complete Qwen rerun. It is:

1. publish the common ABI 3.0 fixture and capability;
2. build the HBM/SRAM Physical Plan IR and independent checker for that fixture;
3. execute it through the functional microsequencer including loop, event,
   state, argmax, and EOS behavior;
4. correlate the controller path in reduced RTL; and
5. only then migrate one retained Qwen operation and one representative
   DeepSeek operation.

This order makes the production controller and evidence boundary real before
the repository accumulates another model-specific command stream.
