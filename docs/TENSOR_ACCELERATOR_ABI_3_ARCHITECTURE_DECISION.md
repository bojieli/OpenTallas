# Tensor-accelerator ABI 3.0 and RTL 3.0 architecture decision

**Decision ID:** TA-ADR-003

**Status:** accepted and controlling at ABI 3.0

**Issue date:** 2026-08-29
**Applies to:** the shared HBM/SRAM tensor-accelerator chip and cluster
profiles, their compiler and simulator, and the Qwen3 conventional and
DeepSeek-V4 wafer-scale ROM families

**ABI scope decision (2026-09-03):** ABI 3.0 is sufficient for this RTL and
architecture-simulation program and remains the sole required program and host
ABI. The proposed
[ABI 3.1 state amendment](TENSOR_ACCELERATOR_ABI_3_1_STATE_AMENDMENT.md) is
withdrawn and MUST NOT be implemented or used as an execution gate. Mutable KV,
compressed-KV, ring, and compressor data are ordinary compiler-allocated
HBM/SRAM tensors addressed by existing ABI 3.0 memory objects, tensor views,
loops, predicates, DMA, and engine operations. Program ordering and a
token-step fence make completed writes visible before the next token. A failed
functional, cycle, cluster, or RTL simulation stops; durable root publication,
outcome journals, idempotent retry, crash recovery, anti-rollback persistence,
and concurrent-serving isolation are outside the required claim boundary.

No new wire field, descriptor minor, feature bit, or state-member abstraction
may be introduced unless a focused implementation proof first demonstrates
that the required model operation cannot be lowered into the frozen ABI 3.0
instruction and descriptor set. Increased instruction count or compiler effort
alone is not such a proof. The default remedy is explicit compiler lowering
using existing primitives.

The mandatory DeepSeek execution and promotion boundary is specified by
[the exact-200K simulator execution design](DEEPSEEK_200K_SIMULATOR_EXECUTION_DESIGN.md).
It requires one 200,000-token natural prompt followed by ordinary decoding
through the first official EOS or exactly 256 generated tokens, on both the
wafer-scale ROM target and the exact 32-chip HBM/SRAM cluster, with complete
external-oracle agreement.

## 1. Decision

OpenTallas will use a bounded tensor-accelerator programming model, not a GPU,
SIMT machine, TPU clone, or general-purpose NPU instruction set. The production
control plane has two processors with deliberately different responsibilities:

1. a small, standard management processor loads an admitted deployment, handles
   the host queue, memory protection, telemetry, terminal fault reporting, and
   fresh-run reset; and
2. a deterministic hardware microsequencer issues bounded descriptors to
   dedicated DMA, tensor, vector, attention, routing, reduction, selection,
   and link engines.

The model data path has no general-purpose scalar fallback. The management
processor may not execute tensor operations, calculate missing model results,
select tokens in firmware, or hide an unsupported accelerator operation.

ABI 3.0 is split into three separately versioned but release-bound interfaces:

| Interface | Purpose | Primary consumer |
|---|---|---|
| Host Queue ABI | deployment, run, generation, completion, and administration requests | host driver and management firmware |
| Deployment and Descriptor ABI | authenticated objects, shapes, numerics, schedules, memory windows, programs, and compatibility records | compiler, firmware, simulator, and microsequencer |
| Device Micro-ISA | loops, predicates, events, fences, engine launch, ordered live-buffer access, completion, and traps | hardware microsequencer |

“RTL 3.0” names the hardware family defined by these ABI 3.0 contracts; RTL
3.0 is not a separate ISA version.

The product topology is:

~~~text
Qwen and DeepSeek source/checkpoint adapters
                    |
        backend-neutral Model Graph IR
                    |
        backend-neutral Tensor Kernel IR
                    |
          +---------+---------+
          |                   |
 shared HBM/SRAM backend                 ROM backend family
          |                                     |
 one conventional-chip RTL         +------------+------------+
          |                         |                         |
    +-----+------+           Qwen conventional       DeepSeek wafer-scale
    |            |           ROM chip                ROM accelerator
 one chip    32-chip cluster
 for Qwen    for DeepSeek
~~~

The HBM/SRAM backend has one versioned ABI 3.x contract, one programmable
tile/controller architecture, one engine-interface set, one numerical
contract, one compiler backend, one simulator, and one conventional
accelerator-chip netlist. Qwen3-8B uses one such HBM/SRAM chip. DeepSeek-V4
Flash uses exactly 32 nodes of that same chip, connected by a separately
modeled high-bandwidth, low-latency, NVLink-class cluster fabric. No
model-specific chip RTL, datapath, or micro-ISA fork is permitted. Each node
implements the union of required Qwen and DeepSeek engine modes; DeepSeek
capacity and work are sharded by the compiler across the 32 identical nodes.

Qwen-ROM and DeepSeek-ROM are different physical products. Qwen-ROM is a
conventional reticle-bounded chip/package. DeepSeek-ROM is a mandatory
wafer-scale accelerator with an on-wafer fabric and distributed HBM attachment.
The DeepSeek comparison is therefore wafer-scale ROM versus a 32-node
HBM/SRAM-chip cluster, not wafer versus wafer and not one oversized HBM chip.

### 1.1 Simplest required execution profile

The four acceptance deployments use the smallest ABI 3.0 subset that executes
the models without a host-compute fallback:

- one admitted batch-one run performs prefill and ordinary greedy decode;
- KV, compressed KV, compressor history, token, and intermediate tensors are
  ordinary live memory objects and tensor views;
- existing DMA and engine operations write those buffers directly;
- existing dependency events order producers and consumers, and one fence at
  the token boundary makes the completed token and buffer writes visible;
- the first unrecoverable trap ends the run with a failed completion, and a
  later run starts from freshly initialized buffers; and
- CRC and bounded replay repair packets only. They never retry a layer, token,
  or model transaction.

The frozen ABI 3.0 wire registry still describes `STATE` records for backward
compatibility, but the four required acceptance deployments emit zero `STATE`
descriptors and zero `STATE` instructions. Their absence is a structural
certificate condition. A production program therefore does not require feature
bit 6 merely because its capability retains compatibility support. Feature bit
10 is likewise required by the builder only when a communication descriptor
actually requests packet integrity or replay; it is absent from a single-chip
program with no link traffic. The state controller, checkpoint/restart, durable
publication, and recovery protocol are therefore not dependencies of model
correctness, RTL correlation, long-context acceptance, or the ROM-versus-HBM
comparison.

## 2. Why a new boundary is required

The unified main branch contains several useful but incompatible execution
contracts:

- OTTA command ABI 2.5 is a Qwen-oriented HBM/SRAM functional contract. One
  complete Qwen forward step expands to 924,386 fixed 64-byte commands. Python
  is effectively the global sequencer, loops and events are not architectural,
  and token argmax is outside the command stream.
- The ABI 2.x RTL admits individual records and executes bounded Qwen slices.
  It is not a complete command processor, program controller, layer controller,
  or production cycle model.
- The general ROM stage shell uses a different host/stage ABI and cannot be
  represented as ABI 2.5 execution.
- Qwen ROM microcode is a model-semantic ABI executed by a PyTorch-backed
  service engine.
- DeepSeek fixture microcode consists of operator-local test ABIs.
- The 64-byte hardware descriptor ISA draft in
  compiler/microcode/hardware_isa.py has strong integrity and descriptor-binding
  ideas, but it is structurally lowered only, ROM-centric, DeepSeek-specific,
  and has no bound descriptor tables, certified schedules, service engines, or
  RTL controller.

None of those contracts is renamed ABI 3.0. They remain immutable migration
inputs and differential oracles.

## 3. Product and backend boundaries

### 3.1 Shared contracts

The following are shared across all four model/backend targets:

- pinned source, checkpoint, tokenizer, chat-template, and generation-policy
  identities;
- semantic graph and target numerical contracts;
- backend-neutral kernel semantics;
- session and transactional-state meaning;
- prompt, token, EOS, and agent-environment governance;
- independent numerical references and comparison rules;
- artifact identity, evidence schemas, and claim policy; and
- common workload definitions for same-model ROM-versus-HBM comparisons.

### 3.2 HBM/SRAM-only sharing

Qwen-HBM and DeepSeek-HBM share:

- one capability ABI and feature-discovery mechanism;
- one management complex and microsequencer;
- one node-local HBM/SRAM hierarchy and address model plus one versioned
  32-node cluster address/topology extension;
- one set of tensor, vector, attention, route, reduce, memory, and selection
  engine interfaces;
- one event, queue, trap, counter, and fail-stop model;
- one causal functional simulator and one cycle-model implementation; and
- one synthesized conventional-chip RTL/netlist and one cluster-fabric protocol
  and endpoint architecture.

Model identity may choose descriptors and programs. It may not select hidden
model-specific RTL behavior.

Within either technology view, the Qwen and DeepSeek HBM deployments use the
same chip RTL, elaboration parameters, capability record, and signoff netlist.
Only the deployment topology differs: one node for Qwen and 32 identical nodes
for DeepSeek. The cluster switches, cables/board or package fabric, link PHYs,
and system RAS are external system components with separately versioned
assumptions.

### 3.3 Mandatory physical scale profiles

The four targets use three non-interchangeable physical topologies:

| Physical topology | Required target | Physical boundary |
|---|---|---|
| Conventional single chip | Qwen-HBM and Qwen-ROM | one reticle-bounded accelerator chip/package per backend |
| 32-node conventional-chip cluster | DeepSeek-HBM | 32 copies of the Qwen HBM/SRAM chip connected by an NVLink-class fabric |
| Wafer-scale logical accelerator | DeepSeek-ROM | distributed reticle/tile ROM assembly presented to the host as one accelerator device |

The DeepSeek topology choices are mandatory, not optional capacity escapes.
DeepSeek-HBM is compiled across exactly 32 identical accelerator nodes; its
critical inter-node path uses the modeled cluster fabric and may not be replaced
by host paging or host sequencing of operators. DeepSeek-ROM is compiled across
a wafer-scale reticle/tile hierarchy; its critical model path uses on-wafer
communication, not a host-orchestrated collection of ROM chips or an ordinary
off-package stage pipeline.

The 32-node HBM cluster contract requires:

- a versioned node/switch/link topology, node-local and global object mapping,
  and deterministic shard/replica ownership;
- collective, multicast, point-to-point, expert-dispatch, sparse-gather, and
  reduction descriptors with bounded credits and explicit completion;
- actual link latency, serialization, switch contention, bandwidth, retry,
  congestion, and failure modeling in data-bearing cycle simulation;
- per-node HBM capacity/locality and explicit remote-traffic accounting;
- one coordinated run namespace, ordered live-buffer visibility,
  token-selection, and EOS semantics without a host per-layer execution loop;
  and
- bounded packet-level link replay followed by fail-stop behavior. An
  unrecoverable node or link failure ends the run and must never return a
  successful partially sharded result.

The wafer-scale contract requires:

- a versioned reticle/tile topology and physical-coordinate descriptor;
- one global logical deployment, address, event, transaction, session, and
  counter namespace over the distributed tiles;
- low-latency, high-bandwidth on-wafer unicast, multicast, reduction,
  sparse-gather, and expert-dispatch services with bounded credits;
- distributed HBM controllers and PHY attachment points around the
  wafer/package boundary, with explicit channel locality, capacity, bandwidth,
  latency, and failure domains;
- bounded global barriers and collectives, deadlock freedom, deterministic
  routing/ordering where architecturally visible, and complete congestion
  accounting;
- clock, reset, power, thermal, RAS, and fault-containment domains;
- tile/link quarantine, spare activation, degraded-topology discovery, and
  yield-aware recompilation; and
- host submission to one logical accelerator; firmware may report health and
  reset for a fresh run but may not sequence model stages across the wafer.

Public contemporary Cerebras-class wafer-scale specifications and public
NVIDIA NVLink/NVL72-class specifications are sourced reference envelopes and
sensitivity points, not achieved OpenTallas values. The architecture review
must source-lock the exact public vendor documents and dates. OpenTallas
minimum bisection bandwidth, collective throughput, and maximum communication
latency are then derived from compiled DeepSeek communication traces and each
physical methodology; they are not copied from vendor headlines.

The historical 8-by-8 reticle and 4,096-tile public proxy in
`spec/ARCHITECTURE.md` remains historical evidence. It does not silently define
the new wafer dimensions, tile count, bandwidth, latency, or physical closure.

**Amendment of 2026-09-03: a fourth physical profile.** An N-node
conventional-chip cluster whose nodes hold their weight shard in mask ROM is
admitted as the profile of TA-DS-ROM-ARRAY (Flash at exactly 32 nodes under
`CLUSTER_32`; Pro at a derived node count under the proposed `CLUSTER_N`).
It obeys the 32-node HBM cluster contract above in full, with "node-local
HBM" read as "node-local memory" wherever weights are concerned, and it adds
nothing to the wafer contract. The storage class of a cluster node's weight
objects is not a topology property: `CLUSTER_32` admits ROM-resident and
HBM-resident weights alike, and no validator, verifier, fabric model, or
device may branch on the combination. A `CLUSTER_32` capability declares
exactly 32 nodes. The plan is
[`DEEPSEEK_V4_ROM_ARRAY_IMPLEMENTATION_PLAN.md`](DEEPSEEK_V4_ROM_ARRAY_IMPLEMENTATION_PLAN.md).

### 3.4 ROM specialization

Qwen-ROM and DeepSeek-ROM separately own:

- immutable weight and scale images;
- physical ROM placement, repair, and mask personalization;
- model-specific physical partitions and schedule topology within the mandatory
  scale profile;
- model-specific compute-lane mix where justified;
- physical signoff, production netlist, and mask release; and
- separate end-to-end qualification.

They may reuse ABI 3.0 host/session records, management firmware, state engines,
link blocks, integrity logic, and microsequencer structures only where the
resulting behavior is explicitly requirement-compatible.

### 3.5 Physical verification views

Every target is evaluated in two separate technology views:

1. **SKY130:** the mature open 130-nm implementation and verification baseline.
   It carries synthesized, placed-and-routed, extracted, and activity-derived
   evidence to the extent supported by the available libraries and macro views.
2. **ASAP7:** an academic predictive 7-nm projection. It provides a controlled
   scaling and architecture-sensitivity view, not foundry signoff or production
   manufacturability evidence.

Within each technology view, Qwen-HBM is compared only with Qwen-ROM and
DeepSeek-HBM only with DeepSeek-ROM under common PVT, clock-view, SRAM, external
HBM, link-boundary, workload, and evidence-class rules. SKY130 and ASAP7 area,
frequency, energy, density, interconnect, or thermal values are never combined
into one result. Passing ASAP7 does not close a SKY130 gate, and passing SKY130
does not validate a commercial 7-nm product.

The wafer-scale ROM methodology is hierarchical in both views: characterize a
tile, close a representative reticle region, model the on-wafer stitched fabric,
then assemble wafer-level power, clock, thermal, yield, repair, and timing
evidence. The 32-node HBM methodology closes the conventional chip once per
technology view and separately models the cluster switches, PHYs, links, and
system behavior.

## 4. Management processor

The management processor is a bounded 32-bit RISC-V control core implementing
RV32IMC with Zicsr and Zifencei, machine mode, physical memory protection, no
floating-point extension, and no vector extension. A compatible implementation
may add hardened security features without changing the ABI.

Its responsibilities in the required simulation and RTL profile are:

- ABI and capability discovery;
- submission/completion queue creation and ownership;
- deployment admission, descriptor-window validation, and activation;
- run allocation and teardown;
- IOMMU or device memory-window programming;
- interrupt handling, first-fault capture, telemetry, and health monitoring;
  and
- terminal abort and fresh-run reset.

Measured boot, signatures, attestation, firmware update, multi-tenant quotas,
repair activation, and warm recovery may be added by a later secured-product
profile. They are not required to compile, simulate, correlate, or compare the
four accelerator targets.

It must not:

- interpret the model graph during execution;
- execute tensor, attention, normalization, routing, or selection arithmetic;
- repair unsupported micro-ISA operations in software;
- supply precomputed activations, logits, routes, or token IDs;
- sequence individual tensor tiles in an acceptance run; or
- turn a device error into a successful completion.

Firmware is allowed to submit an already admitted device program, handle a
terminal trap, and report completion. That is control, not model execution.

## 5. Hardware microsequencer

The microsequencer is the only model-program control engine in the production
data path. It owns:

- program fetch, integrity check, decode, and retirement;
- bounded loop setup and loop-stack state;
- predicates over declared request fields, engine status, and descriptor values;
- asynchronous engine-queue issue;
- dependency events and the global transaction scoreboard;
- queue-space and completion waits;
- acquire/release memory fences;
- precise control traps and first asynchronous engine fault capture;
- stop-issue and terminal completion on the first failure; and
- architectural counters.

The sequencer supports no arbitrary integer load/store program, recursive call,
self-modifying program, indirect jump from tensor data, unbounded loop, or
general scalar ALU. Its control decisions are limited to verified descriptors,
bounded counters, predicates, events, and explicit engine status.

### 5.1 Compact control flow

ABI 3.0 programs describe loop nests over layers, tiles, positions, heads,
experts, and vocabulary partitions. They do not repeat one instruction per
element or DMA burst. The verifier proves:

- every loop has a finite descriptor-bound maximum;
- the product of active loop bounds fits the declared work bound;
- branch targets are instruction boundaries in the authenticated program;
- loop nesting does not exceed the capability;
- every wait refers to an event that can be produced or a host-visible timeout;
- every prepared state has exactly one reachable commit or discard; and
- every terminal path produces one completion.

The minimum compliant implementation supports four nested loops and 32-bit trip
counts. A release capability may advertise larger bounds.

### 5.2 Predicates

Predicates may use:

- prefill versus decode phase;
- request position, span, batch, and generation limit;
- deployment feature bits;
- valid-lane and edge-tile masks;
- route or sparse-index validity;
- selected-token EOS membership;
- engine success or failure; and
- explicit boolean results emitted by route, selection, or state engines.

Predicates may suppress a launch or choose one of two statically verified
control paths. They may not reinterpret tensor payload bits as executable
instructions.

## 6. ABI encoding policy

All ABI 3.0 records are little-endian, naturally aligned, length-bounded, and
reserved-zero. Unknown major versions, unknown mandatory feature bits, nonzero
reserved fields, invalid lengths, and unsupported descriptor types fail closed.

### 6.1 Device program

The proposed ABI 3.0 device instruction is a fixed 32-byte record. Each record
contains:

- major opcode and subopcode;
- flags and predicate ID;
- one descriptor or control-table ID;
- wait-set ID;
- signal-event ID;
- loop/control ID or branch target;
- source operation/debug ID; and
- CRC32C.

The final bit layout is frozen by the ABI schema review, but the 32-byte width,
ID-based operands, fixed-width decode, and per-record CRC32C are architectural
decisions. A program header binds:

- ABI major/minor;
- instruction width and count;
- required capability bits;
- deployment and descriptor-table digests;
- physical topology, active-resource, and topology-epoch digests;
- program body SHA-256;
- entrypoint table;
- declared maximum work and watchdog class; and
- optional signature metadata.

No physical tensor address or unbounded tensor dimension appears directly in a
microinstruction.

### 6.2 Descriptor records

Descriptors use a common 64-byte-aligned header followed by a typed payload in
64-byte multiples. The common header records type, version, length, flags,
object IDs, numeric-profile ID, schedule ID, access permissions, and CRC32C.
The deployment manifest binds the ordered descriptor table with SHA-256.

Descriptor families are:

| Family | Required meaning |
|---|---|
| Memory object | storage class, base or region, bound, alignment, permissions, integrity, and ownership |
| Tensor view | dtype, layout, rank, dimensions, strides, offsets, scale objects, and edge masks |
| Numeric | input, accumulator, output, rounding, reduction order, saturation, NaN, and conversion rules |
| Schedule | engine queue, tile mapping, bank/port use, NoC path, issue window, and resource bound |
| Topology | one-chip, exact 32-node cluster, or wafer profile; node/reticle/tile coordinates, active/quarantined resources, HBM locality, link classes, route groups, and epoch |
| Communication | source/destination objects and nodes/groups, byte extent, route/virtual channel, ordering, integrity/retry, collective/reduction contract, credit bound, timeout, and completion event |
| State (compatibility registry only) | legacy state class, session binding, generation, objects, cursor, capacity, and commit policy; not emitted by the four acceptance deployments |
| Event/wait set | producer set, completion condition, timeout class, and memory-order scope |
| Loop/control | lower bound, upper bound, step, induction bindings, predicate, and maximum iteration product |
| Operator | source graph/kernel IDs, counter class, legal engine family, and diagnostic boundary |

IDs are 32-bit and local to one authenticated deployment bundle. Object byte
sizes and addresses are 64-bit.

### 6.3 Host submission and completion

The host interface uses submission and completion rings with explicit producer
and consumer ownership. The frozen record layout contains:

- opcode, ABI version, flags, and request size;
- deployment ID and deployment generation;
- session ID and session generation where applicable;
- transaction ID and compatibility idempotency field;
- input/output memory-window IDs and bounded offsets;
- entrypoint and generation-policy descriptor IDs;
- deadline/watchdog class; and
- request CRC32C.

Every completion contains:

- matching deployment, session, generation, and transaction identity;
- success, trap class, engine fault, and first-fault program counter;
- completed position and compatibility state-generation field;
- produced-token count and output-token extent;
- final selected token and EOS reason when applicable;
- counter-snapshot ID;
- fault, overflow, and compatibility recovery status; and
- completion CRC32C.

For the simplest required profile, compatibility-only identity, idempotency,
state-generation, poison, and recovery fields are zero and have no behavioral
effect. No host request is retried. The operations required by the four
acceptance paths are:

- capability query;
- deployment admit, activate, deactivate, and remove;
- prefill;
- decode one token;
- generate until EOS or a declared bound;
- counter snapshot;
- terminal abort; and
- fresh-run reset and diagnostics.

One host request targets one logical accelerator deployment. For DeepSeek-HBM,
the admitted 32-node topology has one coordinator-visible request/completion
boundary; for DeepSeek-ROM, the wafer has one such boundary. Internal node or
reticle submissions are generated by the authenticated device program. Host
software does not submit one model-layer request per node or reticle.

## 7. Device Micro-ISA families

The frozen instruction registry is:

| Family | Operations |
|---|---|
| Control | NOP, LOOP_ENTER, LOOP_NEXT, BRANCH_PRED, JUMP, COMPLETE, YIELD, TRAP |
| Synchronization | WAIT, TEST_EVENT, FENCE, BARRIER, CANCEL, DRAIN |
| DMA | ISSUE_DMA, ISSUE_GATHER, ISSUE_SCATTER, ISSUE_INDEXED_COPY |
| Tensor | ISSUE_TENSOR |
| Vector | ISSUE_VECTOR |
| Attention | ISSUE_ATTENTION |
| Routing | ISSUE_ROUTE |
| Reduction | ISSUE_REDUCE |
| Selection | ISSUE_ARGMAX, ISSUE_TOPK, ISSUE_TOKEN_APPEND |
| State (compatibility only) | STATE_READ, STATE_PREPARE, STATE_COMMIT, STATE_DISCARD |
| Pipeline/link | ISSUE_SEND, ISSUE_RECEIVE, ISSUE_REMOTE_DMA, ISSUE_MULTICAST, ISSUE_COLLECTIVE |

Engine operation details live in typed descriptors, not in an expanding set of
model-semantic opcodes. For example, the neutral kernel operation MATMUL may
bind either an HBM weight view or a ROM weight view. ROM_MATMUL is not a
backend-neutral operation.

The four required acceptance programs use control, WAIT/FENCE/BARRIER, DMA,
tensor, vector, attention, routing, reduction, selection, and link operations.
They emit no `STATE`, `CANCEL`, or `DRAIN` instruction. Those encodings remain
decodable only so freezing the accepted ABI 3.0 does not require a new ABI.

For the 32-node cluster and wafer-scale profiles, the pipeline/link family
additionally includes bounded multicast and collective launch descriptors.
These descriptors name admitted topology groups, routing classes, reduction
contracts, byte counts, credit limits, and completion events; they do not expose
arbitrary packet injection or a scalar network-programming fallback.

Greedy argmax and token append are mandatory ABI 3.0 device operations. Sampling
is an optional capability with an explicitly versioned RNG and probability
contract; it is not required for initial greedy Qwen or DeepSeek acceptance.

## 8. Engine contracts

### 8.1 DMA and memory

The DMA engines support bounded multidimensional transfer, transpose where
declared, fill, indexed gather/scatter, and integrity status across host memory,
HBM, SRAM, and immutable ROM address spaces. A descriptor specifies exact source
and destination objects, ranges, alignment, burst policy, expected bytes, and
completion event. Out-of-range, permission, ECC, CRC, or response failures
poison the transaction.

### 8.2 Tensor

The tensor engine contract supports:

- Qwen BF16 operands with FP32 accumulation;
- DeepSeek FP8 E4M3FN dense/shared contractions;
- DeepSeek MXFP4 E2M1 routed weights with E8M0 scales;
- paired and grouped projections through descriptors rather than model opcodes;
- explicit transpose, scale orientation, tile and edge masks;
- frozen reduction order and conversion points; and
- exact status and counters for products, additions, conversions, saturation,
  and exceptional values.

### 8.3 Vector and reduction

The vector/reduction contract covers at minimum RMSNorm, per-head RMSNorm, RoPE,
residual add, SiLU-gate multiply, conversions, scale application, softmax
primitives, compression primitives, mHC primitives, ordered sums, vocabulary
gather, and target-hidden capture. Each operation has a named numerical
contract. There is no generic unpriced vector callback.

### 8.4 Attention

The attention engine supports Qwen GQA and DeepSeek dense/sparse attention via
different descriptors on the same HBM/SRAM hardware. It exposes causal masks,
absolute positions, KV views, sparse indices, scale, reduction order, and state
dependencies. Context-dependent bytes and operations are counted from executed
indices, not planning formulas.

### 8.5 Route and expert

The route engine supports bounded top-k, biased top-k, weight normalization,
expert dispatch, gather/scatter, duplicate handling, invalid-ID rejection, and
expert reduction. Minimum architectural limits are 1,024 expert IDs and top-16
selection. Actual deployments may use smaller declared subsets.

### 8.6 State

KV, compressor, compressed-KV, ring, and other mutable resources are ordinary
compiler-allocated HBM/SRAM tensors. Existing memory objects and tensor views
carry their bases, strides, extents, and dynamic layer/position terms. Engines
write those tensors directly. Existing events order producer and consumer
operations, and a token-step fence must complete every required state and
communication write before the next token begins. If an engine, link, or
address operation fails, the simulation stops; partially written state is never
consumed by another token in that failed run.

### 8.7 Selection and EOS

The selection engine performs vocabulary reduction and deterministic tie
handling according to a numeric/profile descriptor. TOKEN_APPEND validates the
selected ID against the tokenizer vocabulary contract, writes it to the output
token ring and next-token input, tests the authenticated EOS set, and advances
the generation cursor only after the token-step fence succeeds.

A GENERATE request stops on the first official EOS token or the declared
maximum-new-token bound. EOS is included in the returned token sequence. No
post-EOS model transaction may execute.

The immutable `GENERATION_POLICY.max_new_tokens` field is the compiled safety
ceiling. The authenticated request symbol `MAX_NEW_TOKENS` is the active bound
for that generation and must be in `1..policy.max_new_tokens`. `TOKEN_APPEND`
tests that request value after appending the selected token and returns
`MAX_NEW_TOKENS` on the completion that commits the final allowed non-EOS
token. Reaching either EOS or the request cap retires the session on the device;
a host loop stopping without that terminal completion is not a compliant
length stop. This is an ABI 3.0 semantic clarification and changes no record or
descriptor layout.

### 8.8 Inter-chip and on-wafer communication

Inter-chip communication is a first-class accelerator engine, not a simulator
annotation. Every conventional HBM/SRAM chip contains the same synthesizable
digital fabric endpoint, remote-DMA path, packet queues, virtual channels,
credit accounting, integrity/replay logic, collective participation logic,
interrupt/fault reporting, and architectural counters. The high-speed analog
PHY and external switches may remain sourced boundary components, but the chip
cannot rely on host software to emulate their protocol or sequence model work.

Link descriptors bind source and destination nodes or topology groups, local and
remote object windows, byte ranges, ordering class, transaction and sequence
IDs, virtual channel, integrity mode, retry bound, completion event, timeout,
and exact counter class. Remote access is explicit DMA or message movement;
there is no implicit coherent global cache. Collectives bind their participant
set, reduction numeric contract and order, tree/route class, buffer ownership,
and terminal completion.

The 32-node HBM cluster must execute DeepSeek sharding, expert dispatch, sparse
gather, activation transfer, reductions, vocabulary aggregation, the
token-step state/communication fence, argmax, token append, and EOS without a
host per-layer loop. The
wafer-scale ROM fabric implements the same architectural communication meaning
with a separate on-wafer physical endpoint. Link CRC/error, duplicate packet,
retry exhaustion, credit loss, node reset, stale epoch, and timeout all produce
declared fail-stop behavior; the failed run cannot start another generation
step.

## 9. Events, queues, and memory ordering

Each engine has one or more bounded submission/completion queues. Queue depth,
issue width, outstanding operations, event count, and scoreboard size are
capabilities, not assumptions embedded in programs.

Events are single-assignment within one transaction. An engine completion
publishes its writes before signaling its event. A WAIT has acquire semantics
for the declared objects. FENCE supports engine, SRAM-bank, HBM-window, state,
and system scopes. There is no implicit cache coherence between host, HBM, SRAM,
and engine-local storage.

Programs may have multiple independent operations in flight. The verifier and
cycle simulator must prove bounded queue occupancy and absence of cyclic waits
for every admitted schedule.

Distributed events and fences have explicit tile, reticle, node, HBM-region,
cluster, and wafer-device scopes as applicable. A global operation is legal
only when its participant set, tree or route class, maximum skew, buffering,
timeout, and failure behavior are bound in the deployment. Neither simulator
may model a global barrier or collective as zero-latency.

## 10. Architectural state

The following state is architecturally visible or reconstructable:

- active firmware, ABI, capability, deployment, and descriptor-table identities;
- queue producer/consumer indices and ownership;
- active deployment generation and schedule epoch;
- session ID, generation, model, phase, position, context bound, and state map;
- transaction ID, program counter, loop stack, predicates, events, pending
  engines, poison, and first fault;
- current mutable state tensors and their completed token position;
- selected token, EOS status, and output-token extent; and
- all mandatory counters and sticky overflow flags.

Microarchitectural pipeline registers and cache replacement state are not
architectural unless a release capability explicitly makes them deterministic.

## 11. Traps, poison, and recovery

Trap classes are stable ABI values:

- admission and version;
- authentication and integrity;
- descriptor and address;
- capability and resource;
- illegal instruction or control flow;
- numeric and exceptional value;
- DMA/HBM/SRAM/ROM;
- tensor/vector/attention/route/reduce/selection engine;
- state transaction (compatibility registry only; unreachable in the four
  acceptance deployments);
- timeout/watchdog;
- link/NoC;
- power/reset/thermal; and
- internal invariant.

Synchronous decode/admission traps are precise and issue no engine work.
Asynchronous engine faults record the first failing instruction and engine,
block new model work, and publish one failed completion. Writes already issued
need not be rolled back because a failed run produces no successful model
result and its buffers are not reused. The required simulator profile is
fail-stop: the campaign records the failure and does not retry that model step.

Warm-reset recovery and reuse of a failed session are outside the required
simulation profile. A new run begins from freshly initialized state. Late
responses are ignored after the failed run terminates.

## 12. Security and integrity

The production contract distinguishes integrity from authenticity:

- CRC32C detects record corruption;
- SHA-256 binds programs, descriptor tables, images, and manifests;
- signed release manifests authenticate approved deployments and firmware;
- measured boot and optional attestation report firmware, ABI, capability, and
  active deployment identities;
- deployment-generation anti-rollback may be added by a later secured-product
  profile; it is not required for RTL, simulation, or comparison acceptance;
- memory windows and descriptor permissions constrain DMA and engine access;
- debug/test modes are lifecycle controlled and block inference where required;
  and
- immutable ROM has no functional write path.

Public-reference builds may use unsigned manifests, but must label that security
boundary and may not claim production authentication.

## 13. Counters and observability

Mandatory counters are unsigned 64-bit saturating values with sticky overflow.
Their event definitions are versioned and identical in the functional simulator,
cycle simulator, and RTL.

Counter groups cover:

- instructions fetched, issued, retired, predicated off, trapped, and replayed;
- per-engine descriptors, useful work, queue stalls, busy and idle cycles;
- HBM, SRAM, ROM, host, and link requested/useful/transferred bytes;
- bank conflicts, bursts, response classes, ECC/CRC events, and retries;
- tensor products/additions/conversions and vector/reduction elements;
- attention score/value work and actual context/sparse-index extents;
- routed experts, selected IDs, dispatched bytes, and reduction work;
- compatibility state counters, all zero in the four acceptance deployments;
- selected tokens, EOS stops, maximum-length stops, and invalid tokens;
- terminal fault, watchdog, and fresh-run reset events; and
- latency histograms with fixed bucket definitions.

Trace packets carry deployment, session-generation, transaction, program
counter, operator ID, descriptor ID, engine, event, and timestamp. Trace loss is
reported; it cannot silently change a passing evidence claim.

## 14. Versioning and capability negotiation

Major versions are incompatible. Minor versions are additive only:

- a 3.x implementation accepts a program only when all required feature bits and
  descriptor minor versions are supported;
- optional unsupported features cause admission failure unless the bundle
  contains a separately authenticated legal alternative;
- reserved bits are zero and checked;
- capabilities report exact limits and implemented numeric contracts;
- a program binds the capability digest against which it was compiled; and
- no driver, firmware, simulator, or RTL may silently emulate an unsupported
  operation.

The capability union must represent, even before every engine is implemented:

- Qwen dense BF16, GQA, per-head normalization, RoPE, KV, vocabulary projection,
  argmax, and 8,000-token acceptance plus the separate 8,192 capacity boundary;
- DeepSeek BF16/FP8/MXFP4/E8M0, routed experts, sparse attention, compression,
  mHC, KV variants, vocabulary projection, selection, and at least 200,000
  positions; and
- the existing public architectural capacity endpoint of 1,048,576 positions
  without requiring that endpoint for the first full execution.

Capabilities also report topology class, node/tile/reticle coordinates,
destination widths, link classes, collective limits, HBM locality, fault
domains, and active/quarantined resources. A program is admitted only against
the exact chip, cluster or wafer topology and health digest for which it was
compiled.

Minimum field widths are 64-bit memory addresses and byte sizes, 32-bit
descriptor IDs and loop counts, 32-bit token positions, 32-bit session IDs with
separate generation, 16-bit layer IDs, 16-bit expert IDs, and 8-bit top-k counts.

## 15. Compiler and IR boundary

ABI 3.0 does not make either current model graph canonical by renaming it. The
compiler program must introduce an additive common production graph and kernel
contract with these rules:

- the Model Graph IR owns source semantics, tensors, phases, predicates,
  state effects, numeric-contract IDs, and generation entrypoints;
- the Tensor Kernel IR owns target-numeric operations, iteration domains, tensor
  views, dependencies, legal fusion boundaries, and counter classes;
- neither IR contains a ROM address, HBM address, SRAM bank, stage, queue,
  schedule slot, physical engine number, or ROM_MATMUL semantic operation;
- backend Physical Plan IRs own placement, tiling, schedules, memory targets,
  descriptor instances, and ABI 3.0 programs; and
- unknown, generic-callback, unpriced, or framework-owned operations are compile
  errors.

Qwen and DeepSeek exporters must both pass one common schema and verifier.
Backend-specific extensions are permitted only after the semantic operation is
represented in the shared IR and the extension is confined to physical lowering.

## 16. ROM and HBM lowering

An immutable logical weight object has the same graph and kernel identity in both
backends.

- The HBM/SRAM backend binds it to authenticated HBM extents and emits DMA,
  SRAM-tile, tensor, topology-aware communication, and eviction descriptors.
- A ROM backend binds it to immutable ROM regions, repair maps, local tensor
  issue, and static route descriptors.

Mutable state remains in declared SRAM/HBM state objects for both. The ROM
backend must not hide mutable weights or state in a mask image. The HBM backend
must not treat an operating-system page fault or undeclared host paging as a
legal weight fetch.

## 17. Migration and retained evidence

ABI 2.5 and the hardware descriptor ISA draft are frozen as inputs:

1. retain their encoders, decoders, artifacts, and evidence;
2. create independent normalized execution traces for admitted programs;
3. lower the same Qwen graph/kernel operations to ABI 3.0;
4. compare operation boundaries, target values, state transitions, selected
   tokens, and logically equivalent counters;
5. preserve intentional differences such as loop compression and explicit
   on-device selection; and
6. do not resume the paused Qwen campaigns until equivalence passes at the
   declared boundary.

Binary compatibility with ABI 2.5 is not required. Reproducible semantic and
state equivalence is required.

The descriptor draft contributes fixed-record integrity, authenticated table
references, and fail-closed validation ideas. Its prepare/commit machinery,
ROM_MATMUL family, and DeepSeek-only lowering table do not define the required
ABI 3.0 acceptance profile.

## 18. Verification consequences

ABI 3.0 implementation begins with one tiny deterministic fixture, then:

1. Qwen ABI 2.5-to-3.0 functional equivalence;
2. one real Qwen full-width connected layer;
3. one DeepSeek full-width dense/route/state vertical slice;
4. complete Qwen short generation through first EOS;
5. complete DeepSeek short ordinary generation through first EOS;
6. microsequencer and representative engine RTL correlation;
7. exact Qwen 8,000-natural-token and separate repeated-special-token runs;
8. causal DeepSeek 32-node cluster bring-up with real routes, contention,
   collectives, per-node HBM traffic, and link faults;
9. causal DeepSeek ROM wafer-fabric bring-up with real routes, contention,
   collectives, distributed HBM state traffic, faults, and degraded topology;
10. exact DeepSeek 200,000-natural-token execution on both frozen topologies;
11. chat and agentic workloads with legitimate decoded token evidence;
12. separate SKY130 and ASAP7 physical convergence; and
13. same-model, same-technology-view, topology-complete
    ROM-versus-HBM/SRAM comparison.

“Artifact-only execution” means complete functional numerical execution driven
only by compiled deployment artifacts. It is a full model execution at the
functional-simulator boundary, but it is not automatically RTL, cycle-accurate,
timing-closed, or silicon execution. Every report must state which boundary ran.

No acceptance run may use Python to sequence individual device operations,
framework operators as uncompiled fallbacks, injected intermediate activations,
precomputed logits/routes, or host-side argmax. Host software may tokenize,
submit a bounded request, execute an agent environment between model turns, and
decode returned token IDs.

## 19. Decisions deliberately deferred

The qualitative single-chip, 32-node cluster, and wafer-scale split is not
deferred. The following quantitative choices are selected only after compiler
legality, execution-derived communication analysis, and SKY130/ASAP7
characterization:

- HBM channel and stack count;
- SRAM bank count, capacity, macro organization, and ECC geometry;
- tensor/vector/attention/route engine counts and lane widths;
- exact local and on-wafer NoC topology, wafer reticle/tile count, cluster
  switch topology, link widths, routing classes, and physical queue depths;
- operating frequency and voltage;
- Qwen-ROM conventional partition count and DeepSeek-ROM wafer partitioning;
- ROM macro geometry and repair overhead; and
- conventional-package details, 32-node NVLink-class fabric/PHY realization,
  wafer-scale HBM attachment, stitching, and high-speed link implementation.

These are capability values, not ABI semantics. Changing them within advertised
bounds does not change the model programming contract.

## 20. Architecture freeze gate (closed)

TA-A3-ARCH-0 closes only when review records confirm:

- the four target boundaries and reuse rules are accepted;
- Qwen single-chip, DeepSeek 32-node HBM cluster, and DeepSeek wafer-scale ROM
  profiles are accepted, including proof that both HBM deployments use the same
  conventional accelerator-chip netlist;
- management firmware and microsequencer responsibilities are unambiguous;
- host, deployment/descriptor, and micro-ISA layers are separate and complete;
- instruction families, loops, predicates, events, queues, ordering, live
  buffers, EOS, traps, fail-stop behavior, counters, and versioning are
  requirement-traced;
- the Qwen and DeepSeek capability union has no unrepresented ordinary-path
  operation or buffer class;
- the cluster and wafer topology, global address/event/session model, HBM
  locality, collectives, synchronization, fault domains, repair, and degraded
  behavior are versioned and requirement-traced;
- the public Cerebras-class and NVLink/NVL72-class reference envelopes are
  source-locked and clearly separated from execution-derived OpenTallas
  bandwidth/latency requirements;
- SKY130 is defined as the mature 130-nm implementation view and ASAP7 as the
  academic predictive 7-nm view, with no cross-technology-view mixing;
- ROM and HBM lowering do not leak into the neutral IR;
- ABI 2.5 migration and equivalence criteria are approved;
- the exact Qwen 8,000 and DeepSeek 200,000 acceptance boundaries are retained;
  and
- no unresolved decision can change an externally visible ABI semantic.

The pre-closure rule was that compiler, simulator, and RTL implementation of
ABI 3.0 remained paused while documentation audits, independent reference
work, and non-mutating evidence preservation continued. TA-A3-ARCH-0 has since
closed. Implementation and focused conformance continue directly on ABI 3.0;
there is no minor-version gate.
