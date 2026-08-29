# Four-target tensor-accelerator and ROM implementation master plan

**Plan ID:** TA-MASTER-3.0

**Status:** active planning baseline; implementation paused at TA-A3-ARCH-0

**Planning baseline:** main at b6c38ee74b695145898c54c65a2a0f9eec3c281c

**Issue date:** 2026-08-29
**Program owner:** integration and evidence owner

## 1. Purpose

This document converts the unified repository into separable work packages for
four executable model/backend targets:

1. Qwen3-8B on the shared HBM/SRAM tensor accelerator;
2. DeepSeek-V4 Flash on a 32-node cluster of the same HBM/SRAM accelerator chip
   used by Qwen;
3. Qwen3-8B on a Qwen-specific immutable-ROM design; and
4. DeepSeek-V4 Flash on a DeepSeek-specific immutable-ROM design.

The plan is written for multiple implementation agents. It defines the common
contracts, dependency order, file ownership, handoff artifacts, merge gates, and
acceptance evidence so that parallel work does not fork the architecture or
overwrite another lane.

It is governed by
[the ABI 3.0 architecture decision](TENSOR_ACCELERATOR_ABI_3_ARCHITECTURE_DECISION.md).
The lane-specific plans are:

- [shared HBM/SRAM tensor accelerator](HBM_SRAM_TENSOR_ACCELERATOR_IMPLEMENTATION_PLAN.md);
- [Qwen3 ROM hardware](QWEN3_ROM_HARDWARE_IMPLEMENTATION_PLAN.md); and
- [DeepSeek-V4 ROM hardware](DEEPSEEK_V4_ROM_HARDWARE_IMPLEMENTATION_PLAN.md).

The existing
[production tensor-accelerator execution plan](TENSOR_ACCELERATOR_EXECUTION_PLAN.md)
remains the evidence ledger for completed Qwen HBM work. The existing
[executable-system recovery plan](EXECUTABLE_SYSTEM_RECOVERY_PLAN.md) remains
the detailed DeepSeek ROM recovery ledger. Where their old concurrency or ABI
language conflicts with this post-unification plan, this document and
TA-ADR-003 control new work.

## 2. Current unified baseline

The authoritative checkout was fast-forward checked against origin/main on
2026-08-29. The stopped colleague handoffs were unified at 39a607e, including
the preserved DeepSeek attention-preparation work at 16fe72d. The first ABI 3.0
four-lane planning bundle was then committed at b6c38ee; this topology refresh
uses that clean main commit as its planning baseline.

No regression suite was run during this reconciliation. Earlier focused suites
and targeted numeric/accelerator suites have retained passing evidence. A broad
compiler/runtime run was interrupted near 43 percent with no observed failure
and must not be reported as passed.

The old pre-unification plan draft remains recoverable as stash@{0}. It is not
an implementation input and must not be popped into a target worktree.

### 2.1 Compiler and IR reality

The repository does not yet have one production IR stack for both models:

- production Model Graph v2 is structurally suitable as a common starting point
  and has a complete Qwen exporter;
- Qwen has a complete 617-operation neutral Kernel IR and an independent
  checker;
- DeepSeek has a separate, complete 2,136-node and 46-operator semantic graph,
  but no exporter into production Model Graph v2 or a common production Kernel
  IR;
- the older Model Graph v1 and compiler/ir model support small fixtures and
  cannot represent the full target union; and
- physical placement and command formats are currently backend- and
  implementation-specific.

The first common compiler deliverable is therefore an additive production Model
Graph and Tensor Kernel contract that admits both exporters without importing
ROM, HBM, SRAM, schedule, or model-specific runtime behavior.

### 2.2 ISA and controller reality

The unified tree contains multiple non-equivalent ISAs:

- OTTA ABI 2.5: Qwen-oriented HBM/SRAM commands and functional evidence;
- Qwen microcode ABI 1.0: semantic Qwen ROM service instructions;
- DeepSeek operator-local fixture microcode;
- a general ROM host/stage shell ABI; and
- the structural hardware descriptor ISA draft in hardware_isa.py.

There is no production ABI 3.0 encoder, verifier, functional sequencer, command
processor RTL, or cycle model. Existing ABI 2.x RTL covers record admission and
bounded Qwen operations, not a complete controller.

### 2.3 Model-lane reality

| Lane | Retained evidence | Open boundary |
|---|---|---|
| Qwen ROM | complete checkpoint images, graph, 617-record semantic microprogram, artifact-driven PyTorch service execution, exact differential, EOS campaign, and two agent tasks | service arithmetic is framework-backed; the 36 image files are layer images rather than a qualified one-chip topology; operator-complete RTL and matching SKY130/ASAP7 physical closure are open |
| Qwen HBM | complete graph/kernel/physical artifacts, 924,386 ABI 2.5 commands, full-model functional execution, short exact generation, restart, and bounded RTL slices | ABI 3.0, production controller/cycle model, exact 8,000 natural and stress runs, full natural/agent campaign, complete RTL, and physical closure are open; science remains an exact failure |
| DeepSeek ROM | complete source/checkpoint lock, 2,136-node/46-kind graph, qualified operator references, canonical checkpoint assignment, and several executable vertical slices | complete graph-to-microcode, service engine, physical placement/schedule, transformer block, full model, RTL, and 200,000-token execution are open |
| DeepSeek HBM | the DeepSeek semantic/reference work can seed the common backend | no common-IR export, HBM physical plan, ABI 3.0 program, full functional simulator execution, RTL execution, or 200,000-token run exists |

## 3. Product target matrix

| Target ID | Model | Weight tier | Physical topology | Hardware identity | Mandatory context |
|---|---|---|---|---|---:|
| TA-QW-HBM | Qwen3-8B | external HBM with SRAM tiling | one conventional chip/package | shared HBM/SRAM chip RTL 3.0 and netlist | exactly 8,000 natural prompt tokens; separate repeated-special stress |
| TA-DS-HBM | DeepSeek-V4 Flash | node-local external HBM with SRAM tiling | exactly 32 accelerator nodes over an NVLink-class fabric | 32 copies of the identical TA-QW-HBM chip/netlist | exactly 200,000 natural prompt tokens |
| TA-QW-ROM | Qwen3-8B | mask ROM plus HBM/SRAM KV | one conventional chip/package | Qwen-specific conventional netlist and masks | the same Qwen workload contract |
| TA-DS-ROM | DeepSeek-V4 Flash | distributed mask ROM plus HBM/SRAM mutable state | one wafer-scale logical accelerator | DeepSeek-specific wafer-scale netlist, stitching, and masks | the same DeepSeek workload contract |

The two HBM rows use one conventional accelerator-chip design. Qwen uses one
node; DeepSeek uses exactly 32 identical nodes. The chip therefore contains the
DeepSeek-capable tensor/vector/route/state modes and a production inter-chip
fabric endpoint even when a Qwen deployment does not exercise them. A model may
select programs, descriptors, numeric profiles, memory images, and a one-node or
32-node topology. It may not select a different chip elaboration or netlist.

The two ROM rows are separate physical products and scale classes. Qwen-ROM is
the conventional chip-versus-chip comparison. DeepSeek-ROM is mandatory
wafer-scale and is compared with the 32-node HBM cluster. It is not legal to
replace the DeepSeek ROM wafer with a conventional multi-chip stage pipeline or
to describe the HBM cluster as one oversized chip.

Every row has two separately reported physical verification views: SKY130 is
the mature open 130-nm baseline, and ASAP7 is an academic predictive 7-nm
projection. Same-model ROM/HBM comparisons are performed independently inside
each view; numbers from the two technology views are never mixed.

## 4. Shared evidence stack

The common stack is:

~~~text
source + checkpoint + tokenizer + generation policy
                    |
             source adapter
                    |
        production Model Graph IR
                    |
        production Tensor Kernel IR
                    |
     +--------------+----------------+
     |                               |
HBM/SRAM chip/cluster Plan IR   ROM chip/wafer Plan IR
     |                               |
ABI 3.0 deployment/program       ROM image/program/schedule
     |                               |
functional + cycle simulator     functional + cycle simulator
     |                               |
shared chip RTL 3.0              model-specific ROM RTL
     |                               |
SKY130 implementation view + ASAP7 projection and same-workload comparison
~~~

Shared source artifacts are immutable inputs to each backend build. Backend
plans are independently legal; one backend's placement or schedule is never
copied into the other merely to make counters comparable.

## 5. Program invariants

Every agent and lane must preserve these invariants:

- “tensor accelerator” is the programmable HBM/SRAM product name;
- “RTL 3.0” is the implementation of ABI 3.0, not a model or separate ISA;
- HBM Qwen uses one node and HBM DeepSeek uses exactly 32 nodes of one identical
  conventional chip capability/netlist without resynthesis;
- every HBM/SRAM chip includes the digital inter-chip endpoint, remote DMA,
  packet queues/credits, collectives, integrity/retry, faults, and counters
  required for causal 32-node execution;
- Qwen ROM is conventional single-chip and DeepSeek ROM is mandatory
  wafer-scale hardware;
- Qwen acceptance uses exactly 8,000 natural prompt tokens, plus a separate
  repeated-special-token stress workload;
- DeepSeek acceptance uses exactly 200,000 natural prompt tokens;
- smaller contexts are diagnostics and never substitute for those targets;
- decode returns legitimate tokenizer tokens, includes the first official EOS,
  and performs no post-EOS model transaction;
- chat and agentic prompts use pinned official templates and retained rendered
  context;
- exact failures remain failures even when output text is semantically plausible;
- functional, cycle, RTL, post-layout, and silicon evidence are separately
  labeled;
- no framework fallback, injected activation, precomputed route/logit, host
  argmax, or Python per-command sequencing closes production execution;
- HBM and ROM comparisons use the same model, prompt IDs, numerics, state,
  generation policy, technology view, PVT scope, external-memory assumptions,
  and measurement boundary; topology cost remains explicit rather than forced
  equal; and
- SKY130 implementation evidence and ASAP7 predictive evidence remain separate;
- no performance claim precedes correct end-to-end execution.

## 6. Dependency and parallelism policy

### 6.1 Architecture barrier

TA-A3-ARCH-0 is a serial barrier. Before it closes, agents may:

- audit and annotate existing artifacts;
- review the proposed ABI decision;
- enumerate model operator/capability requirements;
- source-lock the public NVLink/NVL72-class and Cerebras-class reference
  envelopes and derive, but do not yet implement, trace-based fabric targets;
- prepare independent known-answer and workload definitions; and
- refine lane plans without changing implementation contracts.

They may not implement a new common IR schema, ABI 3.0 binary format,
microsequencer, controller RTL, or resume an ABI 2.5 model campaign.

### 6.2 Work after the barrier

After TA-A3-ARCH-0, four work packages may operate in parallel when they remain
inside their ownership surfaces:

1. common ABI/IR and integration;
2. shared HBM/SRAM backend and RTL 3.0;
3. Qwen ROM;
4. DeepSeek ROM.

The common owner publishes schemas and fixtures first. Lane agents consume
released versions; they do not add private copies or modify a shared schema to
fit one model.

### 6.3 Contract-change rule

If a lane discovers that a shared contract cannot represent a required
operation, state, numeric rule, or bound:

1. preserve the failing artifact;
2. stop at the shared boundary;
3. submit a versioned change request with both-model impact;
4. have the common owner update the ADR/schema and compatibility fixtures;
5. rerun affected equivalence gates; and
6. only then resume lane lowering.

A lane may not use an opaque callback, generic framework call, or
model-prefixed opcode to bypass this process.

## 7. Agent charters

### 7.1 ABI, neutral IR, and integration agent

**Objective:** close TA-A3-ARCH-0 and publish the common schemas, verifier,
capability contract, fixtures, compatibility rules, and release manifest.

**Owns after architecture approval:**

- additive ABI 3.0 specifications and schemas;
- additive production Model Graph and Tensor Kernel schemas;
- common capability and numeric-contract registries;
- micro-ISA and descriptor encoders/decoders/verifiers;
- common workload/evidence schemas;
- ABI 2.5 normalized-trace and equivalence definitions; and
- the master status and release matrix.

**Must not own:**

- Qwen or DeepSeek source semantics;
- backend placement algorithms;
- expected numerical values;
- model-specific ROM images; or
- lane performance results.

**Handoff:** versioned schema bundle, capability-union report, fixtures,
independent schema checker, compatibility matrix, and reviewed architecture
record.

### 7.2 Shared HBM/SRAM agent

**Objective:** implement one conventional HBM/SRAM accelerator chip, backend,
simulator, and RTL 3.0 hierarchy; run Qwen on one node and DeepSeek on exactly 32
identical nodes without chip resynthesis.

**Owns after the common schema release:**

- HBM/SRAM Physical Plan IR;
- weight/state allocation, tiling, DMA, schedule, and descriptor lowering;
- common functional and cycle simulator;
- management/microsequencer and HBM/SRAM engine RTL;
- synthesizable inter-chip endpoint, remote DMA, packet/collective engines,
  credits, integrity/retry, RAS, counters, and cluster control contracts;
- 32-node functional and data-bearing cycle simulation with real routing,
  contention, collectives, HBM locality, and failures;
- Qwen and DeepSeek HBM deployment profiles; and
- separate SKY130 and ASAP7 chip characterization plus externally classified
  cluster-fabric/PHY assumptions.

**Must not own:** model graph semantics, tokenizer goldens, ROM placement, or
common-schema versioning.

**Handoff:** deterministic deployment, independent legality report, execution
report, counter trace, RTL correlation, and characterized capability for each
model.

### 7.3 Qwen ROM agent

**Objective:** transform the retained complete Qwen functional ROM path into a
causal model-specific conventional single-chip ROM hardware and simulator path.

**Owns:** Qwen ROM physical partition, images, repair map, Qwen ROM schedules,
ROM tensor/vector/attention integration, Qwen ROM simulator, Qwen ROM RTL and
physical reports, and Qwen ROM workload results.

**Must not own:** DeepSeek paths, shared ABI/IR schemas, HBM backend algorithms,
or common Qwen semantic goldens.

**Handoff:** full one-chip Qwen ROM deployment, inverse proof, schedule
certificate, artifact-only and cycle execution, RTL correlation, exact
8K/chat/agent evidence, and separate SKY130/ASAP7 physical results.

### 7.4 DeepSeek ROM agent

**Objective:** close the recovery-plan gaps from the complete semantic/reference
ledger through a causal DeepSeek-specific wafer-scale ROM hardware path.

**Owns:** DeepSeek target-only graph export, wafer reticle/tile ROM
placement/images/repair, on-wafer schedules and service lowering,
mixed-format/MoE/sparse/compressor/mHC ROM integration, distributed-HBM state,
wafer-fabric simulation and RTL, and DeepSeek ROM workload results.

**Must not own:** shared schemas, Qwen semantics, HBM backend lowering, or
speculative DSpark acceptance in the first ordinary-target release.

**Handoff:** complete target-only wafer deployment, inverse and schedule proofs,
end-to-end functional and on-wafer cycle execution, representative RTL and
reticle closure, exact 200K ordinary generation, and SKY130/ASAP7 physical
views.

### 7.5 Independent verification agent

An independent verifier may run alongside one implementation lane when a
concurrency slot is available. It owns inverse reconstruction, schedule
checking, differential oracles, adversarial artifacts, and evidence review. It
must not import the generator's allocation, scheduling, lowering, or
expected-result implementation.

## 8. Planned repository ownership

New work should be additive under versioned, lane-specific roots. Exact paths
are frozen at the architecture/schema review, but the intended ownership is:

~~~text
spec/abi3/                         common ABI owner
schemas/abi3/                      common ABI owner
compiler/ir/v3/                    common IR owner
compiler/backends/hbm_sram/        shared HBM/SRAM owner
compiler/backends/rom/common/      common ROM contracts after review
compiler/backends/rom/qwen3/       Qwen ROM owner
compiler/backends/rom/deepseek_v4/ DeepSeek ROM owner
runtime/abi3/                      common ABI owner
runtime/sim/hbm_sram/              shared HBM/SRAM owner
runtime/sim/rom/qwen3/             Qwen ROM owner
runtime/sim/rom/deepseek_v4/       DeepSeek ROM owner
rtl/abi3/                          common/RTL 3.0 owner
rtl/hbm_sram/                      shared HBM/SRAM owner
rtl/rom/common/                    reviewed common ROM blocks
rtl/rom/qwen3/                     Qwen ROM owner
rtl/rom/deepseek_v4/               DeepSeek ROM owner
~~~

Existing compiler/tensor_accelerator, compiler/qwen3, compiler/microcode,
runtime/service_engine, runtime/tensor_accelerator, and rtl/ot_ta_* sources are
retained evidence. Migration begins additively. An agent must not rewrite a
legacy path merely to make its new API appear canonical.

## 9. Main-branch and handoff protocol

Main is the only integration branch. Parallel agents use isolated worktrees but
deliver reviewed commits directly to main in a serialized push window:

1. record the starting main commit;
2. edit only the allocated surfaces;
3. retain generated large artifacts outside Git;
4. create one coherent, reviewable commit;
5. fetch current origin/main and replay the commit on that exact head;
6. resolve conflicts with the integration owner when a shared document changed;
7. run only the tests authorized for the current gate;
8. push a fast-forward update to main; and
9. publish a handoff record with commit, artifacts, tests, failures, and open
   assumptions.

Force pushes, broad conflict deletion, hidden integration branches, and shared
mutable output directories are prohibited. A direct-main policy does not permit
two agents to push the same shared file concurrently.

Every handoff names:

- baseline and delivered commit;
- plan/work-package and gate IDs;
- source/checkpoint/schema/ABI/capability identities;
- modified path set;
- generated artifact identities and external locations;
- exact commands and test scope;
- known failures and not-run gates;
- next consumer and required input; and
- whether a contract change is requested.

## 10. Program phases and gates

### Phase A — architecture and target freeze

**Work:** review TA-ADR-003, freeze ordinary-path model profiles, exact workload
boundaries, ABI layering, control responsibilities, state, EOS, traps, counters,
minimum capability union, one-node/32-node HBM topology, inter-chip endpoint,
DeepSeek ROM wafer boundary, and dual technology-view policy.

**Exit:** TA-A3-ARCH-0.

### Phase B — common IR and ABI fixture

**Work:** publish additive Model Graph, Kernel IR, capability, deployment,
descriptor, host-queue, and micro-ISA schemas. Lower a tiny deterministic
fixture through both HBM and ROM storage classes. Execute it in an independent
functional sequencer and reject corrupted or unsupported variants.

**Exit:** TA-A3-IR-1. Two clean builds are byte-identical, inverse reconstruction
passes, state rollback is exact, and no backend field appears in neutral IR.

### Phase C — legacy equivalence and real vertical slices

**Work:** establish Qwen ABI 2.5-to-3.0 semantic/state equivalence; lower one
connected Qwen layer and representative DeepSeek dense, route, sparse-attention,
state, remote-DMA, and collective slices. In parallel, ROM lanes map the same
source/kernel boundaries to conventional Qwen and wafer-scale DeepSeek plans.

**Exit:** TA-A3-SLICE-2. Independent references, artifact-only execution,
counters, and failure semantics match for every declared slice.

### Phase D — complete short model execution

**Work:** compile and run complete Qwen and DeepSeek ordinary paths. Execute
prefill, repeated decode, on-device argmax, state commit, EOS, legitimate token
decode, and checkpoint/restart from artifacts. Add chat and simple agent
workloads using pinned templates.

**Exit:** TA-E2E-SHORT-3 independently for all four targets. A short pass does
not close long context, timing, or RTL.

### Phase E — RTL 3.0 and ROM RTL correlation

**Work:** implement the microsequencer, queues/events/traps/state controller,
inter-chip endpoint, wafer endpoint, and representative engines. Drive generated
programs through RTL/co-simulation with stalls, faults, resets, link retries,
and backpressure. ROM lanes integrate their model-specific weight service and
physical schedules.

**Exit:** TA-RTL-4 for each hardware family. Simulator and RTL agree on results,
architectural state, faults, and counters for representative complete programs.

### Phase F — mandatory contexts

**Qwen:** exactly 8,000 natural prompt tokens followed by ordinary decode to
first EOS, plus a separate repeated-special-token stress run. Chat and agentic
outputs retain rendered context, generated token IDs, decoded text, tool actions,
and no post-EOS execution.

**DeepSeek:** exactly 200,000 natural prompt tokens followed by ordinary
target-model decode to first EOS or the frozen maximum bound. A separate short
agentic scenario validates the tool protocol; smaller long-context tests remain
diagnostics.

**Exit:** TA-QW-8K-5 and TA-DS-200K-5 for both backends. Same-model ROM and HBM
outputs meet the frozen numerical/token policy.

### Phase G — SKY130 and ASAP7 convergence

**Work:** characterize exact RTL blocks, SRAM/ROM views, interconnect, and
control first in the mature SKY130 130-nm flow and separately in the academic
ASAP7 7-nm flow. Feed separately versioned capability/cost tables back into the
compiler, recompile, and rerun both models in each view. HBM dies, high-speed
PHYs, cluster switches, packages, and wafer-specific non-digital components
remain separately sourced boundary assumptions.

**Exit:** TA-PHY-6-SKY130 and TA-PHY-6-ASAP7. Every comparison report names one
technology/flow/corner policy; no area, frequency, energy, density, link, or
thermal value is borrowed across views. ASAP7 remains predictive evidence.

### Phase H — governed comparison

**Work:** compare Qwen-ROM with Qwen-HBM and DeepSeek-ROM with DeepSeek-HBM using
identical workload and evidence boundaries. Report latency, throughput, energy,
area, memory, utilization, stalls, capacity, uncertainty, and correctness.

**Exit:** TA-CMP-7-SKY130 and TA-CMP-7-ASAP7. Every number traces to executed
counters and characterized implementation in the same view or is visibly
labeled external/assumed; no cross-view composite is admitted.

## 11. End-to-end acceptance contract

A target is functionally complete only when:

- the pinned prompt is rendered and tokenized by the frozen template/tokenizer;
- every model operation and state transition is in the compiled deployment;
- the simulator consumes only authenticated artifacts;
- prefill and every decode step execute causally;
- token selection occurs through the declared accelerator selection operation;
- every produced ID is legal and decodes under the pinned tokenizer;
- the first official EOS is returned and stops execution;
- raw IDs, raw decoded text, visible decoded text, and input context are retained;
- chat responses pass question-specific checks;
- agent actions are model-generated, parsed fail-closed, executed in the frozen
  sandbox, and returned in the next rendered context;
- independent reference/golden comparisons meet the predeclared policy;
- state, operation, memory, queue, and token counters reconcile; and
- a failure cannot commit partial state or be promoted by semantic plausibility.

Artifact-only functional execution is full numerical model execution at the
functional-simulator boundary. It is not an RTL or timing claim. Cycle, RTL,
post-layout, and silicon completion are separate rows in every status report.

## 12. Comparison protocol

Only same-model pairs are compared:

- TA-QW-ROM versus TA-QW-HBM; and
- TA-DS-ROM versus TA-DS-HBM.

Each pair freezes:

- source/checkpoint/tokenizer/template and prompt-token IDs;
- graph and numerical profiles;
- context, batch, concurrency, EOS and generation limits;
- output and latency boundaries;
- technology view, voltage, temperature, clock-view policy, SRAM/ROM
  methodology, and external HBM/fabric source;
- correctness and evidence class; and
- reporting definitions.

For Qwen, the comparison boundary is one HBM/SRAM chip versus one Qwen ROM chip.
For DeepSeek, it is the complete 32-node HBM/SRAM cluster versus one DeepSeek
ROM wafer-scale accelerator, including all fabric endpoints, links, switches,
distributed HBM, wafer fabric, and system power. The HBM design is not a claimed
reproduction of a commercial GPU. Public NVIDIA NVLink/NVL72-class data must be
a source-locked link-envelope reference, and measured NVIDIA hardware remains a
separate external comparator.

## 13. Current schedule

| Order | Work package | Current status | Start condition |
|---:|---|---|---|
| 1 | Review and freeze TA-ADR-003 | ready for review | current baseline |
| 2 | Common IR/ABI schema and fixture | blocked | TA-A3-ARCH-0 |
| 3 | Qwen ABI 2.5 equivalence | blocked | common ABI fixture |
| 4 | DeepSeek common-IR export and representative slices | blocked | common IR schema |
| 5 | Shared HBM backend/simulator and RTL 3.0 | blocked | schema plus equivalence |
| 6 | Qwen ROM hardware path | audit-ready; implementation blocked | shared semantic/control freeze |
| 7 | DeepSeek ROM hardware path | audit-ready; implementation blocked | shared semantic/control freeze |
| 8 | short end-to-end campaigns | blocked | complete functional deployments |
| 9 | exact Qwen 8K and DeepSeek 200K | blocked | short closure and scalability proof |
| 10 | SKY130/ASAP7 convergence and comparison | blocked | correct cycle and RTL execution |

## 14. Immediate next decision

The next user/reviewer action is to review TA-ADR-003, especially:

- the RV32 management-core boundary;
- the 32-byte device instruction and descriptor-table policy;
- mandatory on-device argmax/EOS generation control;
- host/deployment/micro-ISA separation;
- the HBM/ROM reuse boundary; and
- the one-chip Qwen, 32-node DeepSeek-HBM, and wafer-scale DeepSeek-ROM
  topologies, including inter-chip/on-wafer communication contracts;
- the separate SKY130 and ASAP7 evidence views; and
- the minimum DeepSeek capability union.

No implementation agent should be instructed to “build ABI 3.0” until that
review either accepts the decision or records specific changes. Once accepted,
the common ABI/IR agent starts Phase B. The three backend lanes then consume
that released contract without modifying it privately.

## 15. Agent launch matrix

Use four active roles in total:

1. one architecture, common-ABI/IR, and integration owner;
2. one shared HBM/SRAM tensor-accelerator owner;
3. one Qwen ROM owner; and
4. one DeepSeek ROM owner.

An independent verification role is added at a gate review or temporarily
replaces a lane that is waiting on a dependency. It should not be a fifth
permanent writer during early architecture and schema work.

The recommended operating model is one primary integration session that
launches and coordinates the three lane agents. This gives one place to track
gate state, contract versions, path ownership, and merge order. Manually started
sessions are also valid, but they must use isolated worktrees and the launch
packets below; free-form instructions such as “work on DeepSeek RTL” are not
sufficient.

### 15.1 Launch waves

| Wave | Active writers | Work allowed | Dependency |
|---|---|---|---|
| 0 — now | integration owner only | review and freeze TA-ADR-003; refine plans; no ABI/RTL code | current clean main |
| 1 — after TA-A3-ARCH-0 | common owner; three lanes may audit read-only or write only lane-owned migration inventories | publish common IR/ABI schemas and fixture; prepare backend mappings | architecture freeze |
| 2 — after TA-A3-IR-1 | all four roles | common compatibility work plus three backend vertical slices in owned paths | common schema/fixture release |
| 3 — after slice gates | all four roles, with a rotating independent verifier | complete models, simulators, RTL, and lane evidence | reviewed lane handoffs |
| 4 — long campaigns | one campaign per authorized resource/output root; other agents continue non-conflicting work | Qwen 8K, DeepSeek 200K, RTL/physical correlation | short closure and scalability gate |

The HBM/SRAM agent depends on the common ABI/IR fixture before implementation.
Both ROM agents depend on common semantic, numeric, session, and evidence
contracts, but their physical-plan implementations do not depend on the HBM
backend. Qwen-ROM and DeepSeek-ROM do not depend on one another.

### 15.2 Integration-owner launch packet

Provide the agent:

- this master plan in full;
- TA-ADR-003 in full;
- the current tensor-accelerator execution plan;
- the executable-system recovery plan; and
- the current clean main commit.

Use this task statement:

> Act as the sole ABI 3.0 and integration owner. First review and close
> TA-A3-ARCH-0; do not implement compiler, simulator, or RTL code before that
> gate. After approval, own only common IR, ABI, capability, schema, fixture,
> compatibility, and integration paths. Publish versioned contracts and handoff
> records for the three backend lanes. Do not change model semantics or produce
> backend expected results.

The integration owner reads all five new plan documents, not merely their final
sections.

### 15.3 Shared-HBM/SRAM launch packet

Provide the agent:

- this master plan, especially Sections 2 through 10 and 15;
- TA-ADR-003 in full;
- the HBM/SRAM implementation plan in full;
- the tensor-accelerator execution plan; and
- the released common schema/fixture handoff.

Use this task statement:

> Act as the shared HBM/SRAM tensor-accelerator owner. Implement one conventional
> RTL 3.0 chip/netlist: Qwen uses one node and DeepSeek uses exactly 32 identical
> nodes without chip resynthesis. The chip must include the inter-chip endpoint,
> remote DMA, packet queues/credits, collectives, integrity/retry, RAS, and
> counters needed for causal cluster execution. Work only in the allocated
> HBM/SRAM compiler, simulator, RTL, and evidence paths. Consume released common
> contracts without privately changing them. Begin with the declared vertical
> slice and independent-checker handoff; do not resume long ABI 2.5 campaigns or
> make performance claims.

This agent may start an audit in Wave 1, but writes implementation only after
TA-A3-IR-1.

### 15.4 Qwen-ROM launch packet

Provide the agent:

- this master plan, especially Sections 2 through 12 and 15;
- TA-ADR-003 Sections 1 through 3, 15 through 18, and 20;
- the Qwen ROM implementation plan in full;
- QWEN3_8B_EXECUTABLE.md;
- the relevant Qwen evidence sections of the tensor-accelerator plan; and
- the released common semantic/control handoff.

Use this task statement:

> Act as the Qwen3-8B ROM hardware owner. Build a Qwen-specific conventional
> single-chip immutable-weight physical design and causal artifact-driven
> execution path. Resolve logical layer images versus internal one-chip physical
> partitions before implementation. Work only in
> allocated Qwen-ROM paths. Preserve common Qwen semantics, numerics, workloads,
> EOS, and evidence contracts; do not edit shared ABI/IR or HBM lowering. Start
> with the migration audit and first connected vertical slice defined by the
> lane plan.

### 15.5 DeepSeek-ROM launch packet

Provide the agent:

- this master plan, especially Sections 2 through 12 and 15;
- TA-ADR-003 Sections 1 through 3, 15 through 18, and 20;
- the DeepSeek ROM implementation plan in full;
- the executable-system recovery plan;
- the governed DeepSeek evidence documents relevant to its first slice; and
- the released common semantic/control handoff.

Use this task statement:

> Act as the DeepSeek-V4 Flash ROM hardware owner. Build the ordinary target-only
> wafer-scale immutable-weight path first; keep DSpark/speculative execution
> separate. The critical model path must use a causal on-wafer fabric and
> distributed HBM state, with topology, collectives, repair, quarantine, and
> yield-aware recompilation. Work only in allocated DeepSeek-ROM paths. Export
> complete ordinary semantics into released common contracts without
> model-specific shared opcodes. Begin with one checkpoint-derived connected
> route/state/communication vertical slice, then follow the lane gates toward
> exact 200,000-token execution.

### 15.6 Required per-agent scope declaration

Every agent's first handoff message must state:

- role and plan ID;
- current gate and allowed work;
- baseline commit;
- documents read;
- writable and read-only paths;
- required upstream artifacts;
- exact deliverable and exit evidence;
- prohibited claims/actions;
- intended commit grouping; and
- blocking dependency, if any.

An agent that cannot state those fields is not ready to write. No agent needs a
persona such as “you are agent 2”; the role, plan ID, ownership, baseline,
dependency, and deliverable are the meaningful identity.
