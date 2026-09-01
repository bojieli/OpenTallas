# Shared HBM/SRAM tensor-accelerator implementation plan

**Plan ID:** TA-HBM-3.0

**Status:** implementation blocked on TA-A3-ARCH-0

**Hardware product:** one programmable conventional accelerator chip

**Deployment targets:** one chip for Qwen3-8B; exactly 32 identical chips for
DeepSeek-V4 Flash
**Issue date:** 2026-08-29

## 1. Mission and definition of done

This lane builds one production-quality conventional HBM/SRAM accelerator chip,
compiler, functional simulator, cycle simulator, and RTL 3.0 hierarchy. The
identical elaborated chip/netlist must run:

- Qwen3-8B on one node at the exact 8,000-token acceptance context; and
- DeepSeek-V4 Flash across exactly 32 identical nodes at the exact 200,000-token
  acceptance context.

Different checkpoint images, descriptors, programs, numeric profiles, and
firmware-approved deployments are allowed. Model-selected RTL parameters,
generated model modules, hard-coded layer counts, a DeepSeek-only chip
elaboration, and resynthesis are not. Each chip includes the inter-chip digital
endpoint and DeepSeek engine modes even when deployed alone for Qwen.

The lane is complete only when both checkpoints:

1. compile through the common production graph and kernel contracts;
2. produce legal HBM, SRAM, descriptor, schedule, and ABI 3.0 artifacts;
3. execute complete natural prefill and ordinary decode from those artifacts;
4. stop on the first official EOS and return legitimate decoded tokens;
5. match the frozen target numerical/token policy;
6. correlate representative complete programs with RTL 3.0;
7. reconcile execution and timing counters; and
8. execute DeepSeek through a causal 32-node fabric model with real data,
   routing, collectives, link contention, and fail-stop behavior;
9. recompile and execute against separately characterized SKY130 and ASAP7
   capabilities.

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
- no ABI 3.0 inter-chip endpoint, cluster physical plan, or causal 32-node
  functional/cycle execution exists;
- the functional simulator is not a production cycle model;
- current RTL slices are individually bounded and partly command-range-specific;
  and
- no complete layer is connected through one production controller RTL path.

Existing artifacts are migration goldens. They are not modified to make ABI 3.0
appear complete.

## 3. Hardware architecture

The planned per-chip hierarchy is:

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
+-------+---------+----------+----------+----------+----------+----------+
| DMA/HBM | tensor | vector | attention | route/reduce | state/select | fabric |
+-------+---------+----------+----------+----------+----------+----------+
        |
banked SRAM scratchpad + deterministic NoC
        +--------------------+
        |                    |
external HBM boundary   inter-chip digital endpoint
                             |
                   external PHY/switch/link model
~~~

One node forms the Qwen system. Exactly 32 copies of this hierarchy plus the
versioned external fabric form the DeepSeek HBM system.

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
selected after physical and package review. In the DeepSeek cluster, HBM is
node-local. Remote data movement is explicit inter-chip DMA or messaging and is
accounted separately; no simulator may flatten 32 node memories into a
zero-cost uniform address space.

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

Within each technology view, the proof uses one chip for Qwen and 32
byte-identical netlist copies for DeepSeek. It does not require the Qwen
one-node system to hold the complete DeepSeek image, and it does not permit a
wider DeepSeek-only chip.

### 3.6 Inter-chip communication subsystem

Inter-chip communication is part of the accelerator RTL and ABI. Every chip
implements:

- a versioned fabric endpoint and topology/epoch registers;
- bounded remote DMA and message send/receive engines;
- packetization, reassembly, sequencing, and transaction tagging;
- virtual channels, ingress/egress queues, credits, arbitration, and
  backpressure;
- multicast, broadcast, gather, scatter, reduction, and barrier participation;
- ordered expert-dispatch, sparse-gather, activation, vocabulary, and
  state-commit traffic classes;
- CRC/integrity, bounded retry/replay, duplicate suppression, timeout, poison,
  abort, and link/node-reset handling; and
- bytes, packets, flits, retries, latency histograms, congestion, occupancy,
  collective, and fault counters.

Descriptors bind source/destination node or admitted group, local/remote object
windows, byte extents, route/ordering class, virtual channel, retry bound,
completion event, and timeout. There is no implicit global cache coherence and
no firmware per-layer cluster loop. A cluster transaction either reaches its
declared global state/token commit or fails without exposing partial progress.

The high-speed analog PHY, switches, cables/board or package fabric remain
external sourced boundaries. The digital endpoint, queues, flow control,
collective participation, faults, and counters are synthesized and correlated.
Public NVIDIA NVLink/NVL72-class specifications define a source-locked reference
envelope and sensitivity range; OpenTallas does not claim wire compatibility or
copy unsourced headline bandwidth into its capability.

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
- one-node or exact 32-node topology identity;
- node-local HBM ownership, sharding/replication, remote object windows, and
  communication placement;
- point-to-point, multicast, gather, reduction, barrier, and global-commit
  descriptors with link counter expectations;
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
9. for DeepSeek, partition the program and objects over exactly 32 identical
   node capabilities and schedule explicit communication/collectives;
10. emit HBM images/shards, manifests, and expected local/fabric counters;
11. run independent inverse, liveness, capacity, communication, collective,
    and command legality checks; and
12. reproduce the build byte-for-byte in a second clean directory.

### 4.4 Independent checker

The checker must not import allocator, scheduler, lowering, or expected-result
code. It independently:

- rereads the graph, kernel, checkpoint, workload, and capability;
- reconstructs every HBM object and logical tensor hash;
- proves every SRAM interval, lifetime, bank, and port use;
- validates descriptor and program integrity;
- reconstructs loop work, events, queue occupancy, and absence of cyclic waits;
- reconstructs node ownership, remote transfers, routes, collective membership,
  credit bounds, global commits, and cluster deadlock freedom;
- proves state prepare/commit/discard closure;
- derives expected operation and byte counters; and
- rejects out-of-range, overlap, missing-work, unknown-feature, and corrupted
  artifacts.

**Implementation status (2026-09-01).** The independent checker now also
reconstructs the frozen companion-object rule for block-scaled layer weights;
without that rule it falsely split DeepSeek scale runs by checkpoint adjacency
and reported 322 expected objects against the correct 224. The governed
`tools/check_hbm_deployments.py` source-locks that checker, the planner/lowering,
the graph, both shared-chip capability profiles, and the shipped ABI bytes, then
performs two clean rebuilds. Its Qwen certificate passes all 18 deployment
checks, including an independent disjointness and capacity proof over the
emitted HBM-plus-state address map, and closes checklist W4.6.

The same tool's DeepSeek mode is intentionally a retained failure, not a green
short-run proxy. It passes generic ABI/placement reconstruction after the scale
fix, but separately refuses W4.7 because the 200K physical plan exceeds
node-local HBM, required expert/sparse/reduction sites are replicated instead
of communicated, and the final barrier does not causally gate state commits.
Those findings are published in
`results/abi3/hbm_deepseek_deployment_findings.json` and are the implementation
inputs for the remaining cluster work.

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

For DeepSeek, functional mode instantiates 32 node-local object spaces and
executes every remote transfer and collective causally. It may omit physical
link cycles in this mode, but it may not replace communication with direct
cross-node memory reads or precombined reductions.

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
- 32-node endpoint queues, serialization, PHY/link/switch latency, routes,
  virtual channels, credits, retries, collectives, congestion, and failures;
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

The DeepSeek projection additionally measures 32-node host RAM, event count,
fabric-event rate, checkpoint size, trace growth, and simulated cycles per host
second. A one-node or timing-only extrapolation cannot close the campaign.

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
8. inter-chip endpoint, remote DMA, packet queues, virtual channels, credits,
   collectives, integrity/replay, global commit, RAS, and fabric counters;
9. trace and counter blocks;
10. RAS, reset, power, CDC/RDC, and test integration; and
11. one-node and 32-node generated-program top-level harnesses.

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
7. two-node remote-DMA and collective slice with link stalls/faults;
8. 32-node DeepSeek route/reduce/state-commit slice;
9. on-device vocabulary argmax, token append, and EOS;
10. one complete short generation transaction;
11. multi-session backpressure, error, abort, reset, and link retry; and
12. representative layer/program cycle correlation.

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

All Qwen acceptance evidence uses exactly one conventional accelerator node.
Cluster resources may not be credited to the Qwen chip-versus-chip comparison.

## 8. DeepSeek deployment track

### 8.1 Ordinary target profile

The first DeepSeek profile includes the target model's complete ordinary
prefill/decode path and excludes speculative DSpark draft/acceptance. It must
still cover all ordinary dense/shared/routed experts, FP8/MXFP4 formats, routing,
sparse attention, compressor and KV state, mHC operations, vocabulary head, and
greedy selection.

The common capability must represent optional DSpark extensions, but the
ordinary target profile is closed before enabling them.

The deployment topology is exactly 32 copies of the Qwen HBM/SRAM chip. Compiler
partitioning may use tensor, pipeline, expert, sequence, or hybrid sharding only
when all communication and state semantics remain explicit. Diagnostics may use
2, 4, 8, or 16 nodes, but only the 32-node artifact and execution close the
DeepSeek HBM gates.

### 8.2 Bring-up order

DeepSeek progresses through:

1. common-IR export and exact coverage report;
2. dense BF16 and FP8 checkpoint-derived slices;
3. routed MXFP4 dispatch and expert reduction;
4. sparse attention and index selection;
5. compressor, window-KV, compressed-KV, and mHC transactions;
6. inter-node expert dispatch, sparse gather, activation movement, reductions,
   global state commit, and vocabulary aggregation;
7. one complete checkpoint-derived transformer block across the cluster;
8. complete one-step 32-node model execution;
9. short natural generation through EOS;
10. simple agentic/tool-template generation;
11. exactly 200,000 natural prompt tokens plus ordinary decode; and
12. optional DSpark/speculative extension after target closure.

### 8.3 Long-context requirements

All 200,000 positions are represented with ordinary 32-bit position and 64-bit
state/object fields. The compiler proves per-node and aggregate HBM capacity for
model, scales, metadata, KV, compressor, output, reserve, and integrity, plus
all sharding and replication overhead. The simulator executes actual state
reads/writes, sparse indices, remote movement, and collectives; it may not use
an analytical attention/KV or fabric shortcut.

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

## 10. SKY130/ASAP7 implementation and HBM/fabric boundary

Two separately governed technology views are mandatory:

- SKY130 is the mature open 130-nm implementation and verification baseline;
- ASAP7 is the academic predictive 7-nm projection and is never described as
  production foundry signoff.

Within a view, same-model HBM and ROM reports use common PVT, clock-view, SRAM,
external HBM, link-boundary, and evidence policies. SKY130 and ASAP7 values are
never numerically mixed.

Each chip implementation includes:

- management and microsequencer logic;
- engine datapaths and local control;
- banked SRAM macro/compiler views or explicitly labeled proxies;
- NoC, queue, state, RAS, power, and test logic;
- the digital HBM controller/interface boundary; and
- the digital inter-chip endpoint, queues, flow control, integrity/replay,
  collective participation, RAS, and counters.

HBM DRAM, high-speed HBM/link PHYs, cluster switches, cables/board or package
fabric, interposer/package, and stacks are external. Their area, latency, power,
capacity, and energy are separately sourced and reported. The HBM accelerator
pays all executed weight and inter-node traffic; ROM designs still pay their
mutable-state HBM traffic.

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
| HBM-CL3 | cluster communication closure | same chip endpoint at 2 then 32 nodes; remote DMA, collectives, credits, faults, and global commit correlate |
| HBM-S4 | data-bearing cycle closure | causal HBM/SRAM/NoC/32-node-fabric timing and reconciled counters for both models |
| HBM-R5 | RTL 3.0 representative closure | same generated ABI programs, two-simulator/formal/fault evidence |
| HBM-Q8K6 | Qwen mandatory context | exact natural 8K plus separate stress, chat and agent results |
| HBM-D200K6 | DeepSeek mandatory context | exact natural 200K plus ordinary decode and short agent result |
| HBM-P7-SKY | SKY130 converged capability | characterized RTL, recompilation, rerun, activity-derived reports |
| HBM-P7-A7 | ASAP7 predictive capability | separate academic characterization, recompilation, rerun, and limitations |
| HBM-REL8 | shared chip release | one conventional chip netlist/capability admits Qwen as one node and DeepSeek as 32 identical nodes |

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
| DeepSeek union makes the shared chip impractical | compile and characterize representative slices early | one identical chip netlist cannot legally support Qwen-one-node and DeepSeek-32-node deployments |
| fabric endpoint is treated as an external shortcut | make communication an ABI engine, RTL block, and causal simulator resource | DeepSeek completion depends on host sequencing or unmodeled zero-cost transfers |
| 32-node communication dominates | trace-derived sharding and causal NVLink-class sensitivity | no legal 32-node schedule reaches a competitive bound |
| command/control remains too verbose | compact verified loops and descriptor reuse | program/control traffic dominates useful execution |
| long simulation is infeasible | native exact kernels, event-driven timing, checkpoint/restart | full data-bearing target cannot finish reproducibly |
| SRAM conflicts erase tensor use | bank-aware allocation and causal cycle model | legal schedules cannot reach a useful bound |
| HBM weight traffic dominates | actual traffic scheduling and sensitivity | conservative implementation cannot meet comparison objective |
| mixed formats fail numeric quality | exact references and frozen quality gates | tokens/quality fail under implementable rules |
| dynamic routing deadlocks queues | bounded occupancy proof and randomized stress | no finite deadlock-free schedule exists |
| state failure partially advances a session | atomic prepare/commit/discard | any fault exposes partial token state |
| model logic leaks into RTL | same-netlist audit and adversarial deployment | DeepSeek requires a different chip elaboration or resynthesis |

## 14. Immediate work after architecture approval

The first implementation is not a complete Qwen rerun. It is:

1. publish the common ABI 3.0 fixture and capability;
2. build the HBM/SRAM Physical Plan IR and independent checker for that fixture;
3. execute it through the functional microsequencer including loop, event,
   state, argmax, and EOS behavior;
4. correlate the controller path in reduced RTL;
5. extend the fixture through two identical endpoints with remote DMA,
   collective, stalls, retry, failure, and global-commit checking; and
6. only then migrate one retained Qwen operation and one representative
   DeepSeek operation.

This order makes the production controller and evidence boundary real before
the repository accumulates another model-specific command stream.
