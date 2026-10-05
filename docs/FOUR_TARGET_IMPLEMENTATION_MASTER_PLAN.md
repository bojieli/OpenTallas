# Four-target tensor-accelerator and ROM implementation master plan

**Plan ID:** TA-MASTER-3.0

**Status:** active execution baseline; ABI 3.0 is frozen and sufficient

**Original planning baseline:** main at b6c38ee74b695145898c54c65a2a0f9eec3c281c

**Current contract refresh:** 2026-09-03, ABI 3.0 simulation-scope decision

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
ABI 3.0 is the sole required program and host ABI for all four targets. The
[withdrawn ABI 3.1 proposal](TENSOR_ACCELERATOR_ABI_3_1_STATE_AMENDMENT.md) is
an historical design record and is not an implementation or evidence gate.

The DeepSeek end-to-end implementation additionally follows
[the exact-200K simulator execution design](DEEPSEEK_200K_SIMULATOR_EXECUTION_DESIGN.md).
Its two independent hard gates are a mutually correlated ABI 3.0
compiler/runtime/simulator/RTL implementation and an external oracle continued
through first official EOS or exactly 256 generated tokens. Neither an
eight-token oracle prefix nor an artifact-only structural replay is a full
execution.

The current implementation and evidence snapshot is maintained in the
[four-target progress report](FOUR_TARGET_PROGRESS_REPORT.md). That report is
the concise handoff; this document remains the controlling delivery plan, and
the unified checklist remains the requirement-by-requirement ledger.

### 1.1 Current execution override

TA-A3-ARCH-0 is closed and the released ABI 3.0 contract is sufficient. The
ordered implementation packages are:

1. audit each remaining Qwen and DeepSeek mutable-buffer update against
   existing ABI 3.0 memory objects, tensor views, loops, predicates, and
   operations;
2. lower mutable KV, compressed-KV, ring, and compressor tensors explicitly as
   ordinary HBM/SRAM buffers, decomposing a complex update into existing
   operations and scratch views when one operator record is insufficient;
3. preserve the integrated operation-derived feature rule:
   `TRANSACTIONAL_STATE` is absent from every production program and
   `INTEGRITY_RETRY` is required only by a deployment with a real packet link,
   where its scope is packet-local;
4. execute those operations directly against simulator HBM/SRAM buffers and
   enforce a fence after all memory and communication work for one token;
5. correlate the same ABI 3.0 program, addresses, counters, and completion
   boundary through the cycle model and RTL; and
6. run focused conformance checks, then rebuild and re-execute all four target
   deployments.

The required profile is uninterrupted and fail-stop. A failed model step ends
the run; durable roots, outcome journals, idempotent replay, power-loss
recovery, anti-rollback persistence, and concurrent-session isolation are not
part of the accelerator or comparison claim. Optional long-campaign
checkpointing is host-side simulator tooling performed only after a completed
token step. A lane may not invent a private ABI, IR operation, live-buffer
convention, or evidence exception.
Long-running campaigns may execute concurrently only after their
source digest, deployment digest, workload, oracle, topology, and output path
are frozen. Historical local W10 captures bind an obsolete pre-live-buffer source
identity and are diagnostic only; one stress capture also diverges from its
oracle. They are not committed acceptance evidence and must not seed a paired
run. Fresh captures start only from one committed live-buffer source identity.

At the 2026-09-03 integration checkpoint, all four current deployment
certificates report zero ABI `STATE` resources. The shared simulator has
host-only performance observations and an opt-in decoded immutable-weight cache
whose default is disabled. The Qwen long-run checker independently authenticates
and admits the serialized deployment and verifies token text. The first Qwen
HBM natural capture A terminated without a result after it had been observed
healthy for at least 2:28:07 while still in exact-8K prefill. It establishes no
token, acceptance verdict, exact timing, peak RSS, TPOT, or resource headroom.
A fresh capture A must use a durable detached service and the final frozen
source/deployment identity. Capture B may start only after that A completes,
passes, and demonstrates resource headroom.

The bounded RTL integration slice now drives 6 real `DMA.GATHER`, 4 exact BF16
`TENSOR.EMBED_LOOKUP`, 2 Qwen BF16 `VECTOR.RMS_NORM`, and 2 DeepSeek
stride-zero BF16 `DMA.TRANSFER` launches from the four shipped decode images.
Icarus and Verilator each check 58,368 result words through 52 resolved views
with 124,189 checks. The token-zero embedding row is a bounded synthetic probe,
not a decoded model token, and the campaign authenticates four selected 8 KiB
embedding rows plus two selected 8 KiB RMS gain ranges rather than their
complete segments. Its next fail-closed boundaries are Qwen `TENSOR.MATMUL` at
PC 11, DeepSeek ROM `LINK.MULTICAST` at PC 13, and DeepSeek HBM `VECTOR.MHC`
at PC 14.

The exact-200K external-oracle tooling now has one fail-closed
`--gate-b-production` profile. It fixes the exact prompt, EOS-or-256 horizon,
200,320-position KV allocation, tiled-prefill geometry, source/input identities,
full-checkpoint pre-run hash, qualified package/device/numeric stack, and
completion rehash. This is launch readiness at tooling scope only: the full
166.9 GB hash and production model run have not occurred, and the retained
eight-token oracle remains rejected. The remaining critical path is completion
of Qwen captures A/B, execution of DeepSeek Gate B, operator-complete RTL
integration, both mandatory exact-length accelerator pairs, and complete
same-view SKY130/ASAP7 characterization; it is not another ABI revision.

The final DeepSeek accelerator-pair checker is also implemented and covered by
26 focused tests. It independently authenticates the future one-wafer ROM and
exactly-32-node HBM records and enforces exact-200K input, first-EOS-included or
exactly-256 output, oracle-identical tokens/text, per-step success, zero
production `STATE`, counters, implementation identity, and association equality
after node normalization. Tooling readiness does not close the still-unrun
pair.

The authoritative requirement-by-requirement progress ledger is
[the unified execution checklist](UNIFIED_EXECUTION_CHECKLIST.md). Sections 2,
13, 14, and 15 below retain the original unification snapshot and launch
packets for provenance; their old statuses and immediate actions do not
override this subsection or the unified checklist.

### 1.2 Ordered release gates and evidence flow

The program has two highest-priority outcomes, in strict order:

1. **Gate 1 — correct output tokens.** The complete compiled model must execute
   from authenticated deployment artifacts on the target simulator. Every
   generated vocabulary ID and the raw and visible decoded text must equal an
   independently frozen oracle. The natural input context must decode and
   re-encode to the exact pinned prompt IDs. The execution must include and
   stop immediately after the first official EOS, or produce exactly 256
   tokens when no EOS occurs, with no post-terminal model transaction. Qwen
   additionally requires genuinely distinct, heterogeneous sequences at
   B=1/2/4/8; cloning one B=1 request is not batch evidence.
2. **Gate 2 — desired TPOT.** Only a Gate-1-passing execution may supply its
   own performance result. That same record must retain the raw architectural
   request-start and token-commit ticks. TPOT is derived from consecutive
   commit-tick deltas using a characterized SKY130 or ASAP7 target clock and
   is reported per sequence together with the raw deltas, statistic, batch
   size, and aggregate throughput. The execution record and timing report must
   bind the identical checkpoint, tokenizer, workload, source release, IR,
   deployment, capability, topology, and process/PVT identities.

Host wall time, RTL-simulator wall time, retired-instruction counters,
functional-device bookkeeping ticks, isolated operator latency, and analytical
roofline projections are useful diagnostics but are not TPOT. A failure or
divergence at Gate 1 invalidates the associated performance row rather than
leaving a partially eligible measurement. The current 100-microsecond/token
figure is an aspirational architecture north star. It becomes a release pass
criterion only if explicit per-model, per-topology, per-process/PVT,
per-batch, and per-statistic numerical SLO rows are frozen in the comparison
contracts before the qualifying runs.

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

## 2. Original unified baseline (historical snapshot)

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
| TA-DS-ROM | DeepSeek-V4 Flash | distributed mask ROM plus live HBM/SRAM buffers | one wafer-scale logical accelerator | DeepSeek-specific wafer-scale netlist, stitching, and masks | the same DeepSeek workload contract |
| TA-DS-ROM-ARRAY-FLASH | DeepSeek-V4 Flash | mask ROM plus node-local HBM/SRAM buffers | exactly 32 reticle-class ROM chips over the TA-DS-HBM NVLink-class fabric | DeepSeek-specific conventional ROM netlist and masks, one die replicated | the same DeepSeek workload contract |
| TA-DS-HBM-PRO | DeepSeek-V4 Pro | node-local external HBM with SRAM tiling | N accelerator nodes over a two-level fabric (`CLUSTER_N`) | N copies of the identical TA-QW-HBM chip/netlist | exactly 200,000 natural prompt tokens |
| TA-DS-ROM-ARRAY-PRO | DeepSeek-V4 Pro | mask ROM plus node-local HBM/SRAM buffers | N reticle-class ROM chips over a two-level fabric (`CLUSTER_N`) | DeepSeek-Pro-specific conventional ROM netlist and masks, one die replicated | the same Pro workload contract |
| TA-DS41-ROM-WAFER | DeepSeek-V4.1 Flash | distributed mask ROM plus live HBM buffers; Engram tables resident in wafer-edge HBM | two wafer-scale logical accelerators in a pipeline, one crossing per token | DeepSeek-V4.1-specific wafer-scale netlist, stitching, and masks | exactly 200,000 natural prompt tokens (`TA-DS41-CTX-200K-1`); plan `DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md` |
| TA-DS41-ROM-ARRAY | DeepSeek-V4.1 Flash | mask ROM plus node-local HBM/SRAM buffers | 64 reticle-class ROM chips over the TA-DS-HBM NVLink-class fabric (`CLUSTER_N`) — derived 2026-09-13 from the plan's own whole-expert ownership rule, which its 51-node analytical design point violates (384 routed experts per layer do not divide by 51); the 51-node row it replaces is the roofline design point, not a placement | DeepSeek-V4.1-specific conventional ROM netlist and masks, one die replicated | the same V4.1 workload contract |
| TA-DS41-HBM | DeepSeek-V4.1 Flash | node-local external HBM with SRAM tiling; Engram tables in host memory | N accelerator nodes over an NVLink-class fabric | N copies of the identical TA-QW-HBM chip/netlist | the same V4.1 workload contract |

The two HBM rows use one conventional accelerator-chip design. Qwen uses one
node; DeepSeek uses exactly 32 identical nodes. The chip therefore contains the
DeepSeek-capable tensor/vector/route/buffer-management modes and a production
inter-chip fabric endpoint even when a Qwen deployment does not exercise them.
A model may select programs, descriptors, numeric profiles, memory images, and
a one-node or 32-node topology. It may not select a different chip elaboration
or netlist.

The ROM rows are separate physical products and scale classes. Qwen-ROM is
the conventional chip-versus-chip comparison. TA-DS-ROM (the wafer) is
compared with the 32-node HBM cluster and with TA-DS-ROM-ARRAY-FLASH, which is
its packaging control: the same ROM tile on the cluster fabric. The array rows
were added on 2026-09-03 by
[`DEEPSEEK_V4_ROM_ARRAY_IMPLEMENTATION_PLAN.md`](DEEPSEEK_V4_ROM_ARRAY_IMPLEMENTATION_PLAN.md);
they do not retire the wafer row. It remains illegal to *relabel* the wafer
target as a multi-chip stage pipeline or to describe any cluster as one
oversized chip: a result carries the `topology_class` and `node_count` of the
target that produced it.

The three V4.1 rows were added on 2026-09-13 by
[`DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md`](DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md),
which amends this section and ADR-003 section 3.3 and retires, weakens and
replaces nothing above. They repeat the V4 comparison structure on a newer
model: TA-DS41-ROM-WAFER is compared with TA-DS41-HBM for storage class and with
TA-DS41-ROM-ARRAY for packaging, and the three contracts live in
`configs/abi3/comparison_contracts/deepseek_v41_*_v1.json` under gate
DS41-CMP11. Four properties of these rows are load-bearing and easy to lose:

1. **The primary target is two wafers, and the pair is not a wafer.** It is
   one `WAFER_LOGICAL_DEVICE` of two `WAFER`-class nodes — one deployment, one
   session, one submission, two complete wafer logical devices of silicon
   (ADR-003 section 3.3, amendment of 2026-09-13). The relabelling prohibition
   of the paragraph above applies to it in both directions: the pair may not be
   reported as one wafer, and neither wafer may be reported as half of one.
2. **The array's node count is a capacity result, not an area match.** At the
   published 815.0 mm² <!-- figure: 815.0 src="configs/hardware/technology.json#reticle.area_mm2.value" name="master plan reticle die area" -->
   reticle die, 64 nodes is well under the silicon of two 46,225.0 mm² <!-- figure: 46,225.0 src="configs/hardware/technology.json#wafer.area_mm2.value" name="master plan wafer die area" -->
   wafers, so the wafer-versus-array pair is the packaging control at unequal
   area and not an iso-area result — and it stays outside the tolerance at the
   plan's 51 as well, so that reading does not depend on which count survives.
   Its contract states the reticle count that would be iso-area, records that no
   such build exists, and refuses the iso-area reading; section 12's comparison
   protocol governs the rest.
3. **The comparator's node count is not yet a number.** TA-DS41-HBM is the
   model-blind chip at a node count derived when the deployment is compiled
   (gate DS41-P3), so its contract carries a null node count with the derivation
   rule beside it rather than a placeholder that would become the denominator of
   every per-node figure.
4. **None of the three rows is implemented evidence.** No DeepSeek-V4.1 token
   has been produced by any lane in this repository, no V4.1 deployment has been
   compiled, and the V4.1 Kernel IR is not emitted yet; the rows register
   targets, and section 11.1's correct-token gate stands in front of every
   performance number any of them may eventually carry.

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
ABI 3.0 deployment/program      ABI 3.0 program + ROM image/schedule
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
- “RTL 3.0” is the shared hardware family, not a model or separate ISA, and it
  executes the frozen ABI 3.0 program contract;
- HBM Qwen uses one node and HBM DeepSeek uses exactly 32 nodes of one identical
  conventional chip capability/netlist without resynthesis;
- every HBM/SRAM chip includes the digital inter-chip endpoint, remote DMA,
  packet queues/credits, collectives, integrity/retry, faults, and counters
  required for causal 32-node execution;
- production deployments require no transactional-state feature; packet
  integrity/replay is required only by a link-bearing topology and never grants
  model-operation retry;
- Qwen ROM is conventional single-chip and DeepSeek ROM is mandatory
  wafer-scale hardware;
- Qwen acceptance uses exactly 8,000 natural prompt tokens, plus a separate
  repeated-special-token stress workload;
- DeepSeek acceptance uses exactly 200,000 natural prompt tokens;
- smaller contexts are diagnostics and never substitute for those targets;
- decode returns legitimate tokenizer tokens, includes the first official EOS,
  and performs no post-EOS model step;
- chat and agentic prompts use pinned official templates and retained rendered
  context;
- exact failures remain failures even when output text is semantically plausible;
- functional, cycle, RTL, post-layout, and silicon evidence are separately
  labeled;
- no framework fallback, injected activation, precomputed route/logit, host
  argmax, or Python per-command sequencing closes production execution;
- HBM and ROM comparisons use the same model, prompt IDs, numerics, initial
  live-buffer contents, generation policy, technology view, PVT scope,
  external-memory assumptions, and measurement boundary; topology cost remains
  explicit rather than forced equal; and
- SKY130 implementation evidence and ASAP7 predictive evidence remain separate;
- no performance claim precedes correct end-to-end execution.

## 6. Dependency and parallelism policy

### 6.1 Original architecture barrier (closed)

This subsection records the issuance-time barrier. W0 closed it; the current
ABI 3.0 execution order is in Section 1.1 and the unified checklist.

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
operation, live-buffer update, numeric rule, or bound:

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
- weight/live-buffer allocation, tiling, DMA, schedule, and descriptor lowering;
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
mixed-format/MoE/sparse/compressor/mHC ROM integration, distributed-HBM live
buffers,
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
boundaries, ABI layering, control responsibilities, live-buffer behavior, EOS,
traps, counters,
minimum capability union, one-node/32-node HBM topology, inter-chip endpoint,
DeepSeek ROM wafer boundary, and dual technology-view policy.

**Exit:** TA-A3-ARCH-0.

### Phase B — common IR and ABI fixture

**Work:** publish additive Model Graph, Kernel IR, capability, deployment,
descriptor, host-queue, and micro-ISA schemas. Lower a tiny deterministic
fixture through both HBM and ROM storage classes. Execute it in an independent
functional sequencer and reject corrupted or unsupported variants.

**Exit:** TA-A3-IR-1. Two clean builds are byte-identical, inverse reconstruction
passes, live-buffer contents and token-boundary ordering are exact, all four
deployments contain zero `STATE` records, and no backend field appears in
neutral IR.

### Phase C — legacy equivalence and real vertical slices

**Work:** establish Qwen ABI 2.5-to-3.0 semantic/live-buffer equivalence; lower one
connected Qwen layer and representative DeepSeek dense, route, sparse-attention,
live-buffer, remote-DMA, and collective slices. In parallel, ROM lanes map the same
source/kernel boundaries to conventional Qwen and wafer-scale DeepSeek plans.

**Exit:** TA-A3-SLICE-2. Independent references, artifact-only execution,
counters, and failure semantics match for every declared slice.

### Phase D — complete short model execution

**Work:** compile and run complete Qwen and DeepSeek ordinary paths. Execute
prefill, repeated decode, on-device argmax, direct live-buffer updates, the
token-step fence, EOS, and legitimate token decode from artifacts. A fault ends
the run; restart and model-operation retry are not part of this phase. Add chat
and simple agent workloads using pinned templates.

**Exit:** TA-E2E-SHORT-3 independently for all four targets. A short pass does
not close long context, timing, or RTL.

### Phase E — RTL 3.0 and ROM RTL correlation

**Work:** implement the microsequencer, queues/events/traps/live-buffer access,
inter-chip endpoint, wafer endpoint, and representative engines. Drive generated
programs through RTL/co-simulation with stalls, faults, resets, link retries,
and backpressure. ROM lanes integrate their model-specific weight service and
physical schedules.

**Exit:** TA-RTL-4 for each hardware family. Simulator and RTL agree on results,
architectural live-buffer contents, faults, and counters for representative
complete programs.

**Current boundary:** generated-RoPE gather and one exact embedding-row lookup
execute in every shipped decode image, followed by Qwen RMSNorm or DeepSeek
stride-zero transfer. Extend Qwen next from `TENSOR.MATMUL`, DeepSeek ROM from
`LINK.MULTICAST`, and DeepSeek HBM from `VECTOR.MHC`; then continue across the
remaining required memory, tensor, vector, attention, route, reduction,
communication, selection, token-append, and EOS operations. A synthetic
token-zero prefix does not satisfy this phase's complete-program exit.

### Phase F — mandatory contexts

**Qwen:** exactly 8,000 natural prompt tokens followed by ordinary decode to
the first official EOS or the frozen 256-token maximum, plus a separate
repeated-special-token stress run. EOS is retained as the final generated token
when reached; a cap stop makes no EOS claim. Chat and agentic outputs retain
rendered context, generated token IDs, decoded text, tool actions, and no
post-EOS execution.

**DeepSeek:** exactly 200,000 natural prompt tokens followed by ordinary
target-model decode to first official EOS, included in the result, or exactly
256 generated tokens when EOS is not reached. The external oracle must first be
produced by the fail-closed Gate-B profile with complete pre-run and completion
identity checks. A separate short agentic scenario validates the tool protocol;
smaller long-context tests remain diagnostics.

**Exit:** TA-QW-8K-5 and TA-DS-200K-5 for both backends. Same-model ROM and HBM
outputs meet the frozen numerical/token policy. The DeepSeek pair must pass
`tools/check_deepseek_v4_200k_accelerator_acceptance.py`; the checker's
existence and synthetic fixtures do not close this exit.

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
- every model operation and live-buffer update is in the compiled deployment;
- the simulator consumes only authenticated artifacts;
- prefill and every decode step execute causally;
- token selection occurs through the declared accelerator selection operation;
- every produced ID is legal and decodes under the pinned tokenizer;
- the first official EOS, when reached before the declared cap, is returned and
  stops execution; otherwise the exact frozen cap is reached and reported
  without an EOS claim;
- raw IDs, raw decoded text, visible decoded text, and input context are retained;
- chat responses pass question-specific checks;
- agent actions are model-generated, parsed fail-closed, executed in the frozen
  sandbox, and returned in the next rendered context;
- independent reference/golden comparisons meet the predeclared policy;
- live-buffer, operation, memory, queue, and token counters reconcile; and
- a failed run is never promoted by semantic plausibility; its partially written
  buffers, if any, are discarded with that run rather than rolled back or reused.

Artifact-only functional execution is full numerical model execution at the
functional-simulator boundary. It is not an RTL or timing claim. Cycle, RTL,
post-layout, and silicon completion are separate rows in every status report.

### 11.1 Correct-token gate before TPOT

The program's two highest-priority outcomes are correct output tokens and the
desired time per output token (TPOT), in that order. No latency or throughput
number is promotable until the exact same execution has passed all functional
acceptance checks above. In particular, the result must retain the complete
input context, legal generated IDs, raw and visible decoded text, exact oracle
agreement, first-EOS-included-or-exact-cap termination, and proof that no model
step ran after EOS.

For each accepted batch point, retain together in one source-bound result:

- batch size and prompt-token count per sequence;
- generated tokens per sequence and in aggregate;
- correct-token count, first divergence index, and stop reason per sequence;
- prefill latency and time to first token;
- every decode-step latency, or raw samples plus a lossless declared summary;
- warm and steady-state TPOT, and aggregate tokens per second; and
- topology, process view, clock/cost table, capability, deployment, workload,
  oracle, source, and implementation identities.

Analytical roofline and cycle-model batch sweeps do not execute the language
model and therefore do not verify tokens. They remain in explicitly projected
columns. Executed TPOT is reported only from a token-correct run; a projected
TPOT may be compared with it but never relabeled as it.

## 12. Comparison protocol

Only same-model pairs are compared:

- TA-QW-ROM versus TA-QW-HBM;
- TA-DS-ROM versus TA-DS-HBM;
- TA-DS-ROM-ARRAY-FLASH versus TA-DS-HBM (the storage-class comparison at
  equal node count and, when the two dies match in area, at iso-area);
- TA-DS-ROM versus TA-DS-ROM-ARRAY-FLASH (the packaging comparison);
- TA-DS-ROM-ARRAY-PRO versus TA-DS-HBM-PRO;
- TA-DS41-ROM-WAFER versus TA-DS41-HBM (the storage-class comparison at
  wafer scale, pending the comparator's derived node count);
- TA-DS41-ROM-ARRAY versus TA-DS41-HBM (the storage-class comparison at
  reticle scale; unlike the V4 pair of this shape it is not equal-node by
  construction, because each side's node count is a capacity result — 64 derived
  on the ROM side, and still underived on the HBM side); and
- TA-DS41-ROM-WAFER versus TA-DS41-ROM-ARRAY (the packaging comparison, whose
  two sides are not iso-area and whose contract therefore carries the
  granularity correction this section requires).

**Every pair is read at iso-area.** Area is accelerator die area per node
times node count; HBM stacks, package, switch silicon, and board are reported
beside it and never in the denominator. The comparator's node count is
derived from the ROM side's silicon and the area ratio is stated on the
artifact, within 2% or with a stated granularity correction. Iso-area is not
iso-cost. The rule is stated in full in
[`DEEPSEEK_V4_ROM_ARRAY_IMPLEMENTATION_PLAN.md`](DEEPSEEK_V4_ROM_ARRAY_IMPLEMENTATION_PLAN.md)
section 3.5.

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
distributed HBM, wafer fabric, and system power. For DeepSeek-V4.1 it is the
two-wafer pipeline, counted as both of its wafers and the crossing between them,
against the HBM/SRAM cluster at the node count gate DS41-P3 derives; the three
contracts under `configs/abi3/comparison_contracts/deepseek_v41_*_v1.json` freeze
every item in the list above, and each records which of its bindings is still
pending rather than omitting it. The HBM design is not a claimed
reproduction of a commercial GPU. Public NVIDIA NVLink/NVL72-class data must be
a source-locked link-envelope reference, and measured NVIDIA hardware remains a
separate external comparator.

## 13. Original schedule (superseded)

This table is the issuance-time dependency snapshot. It is retained for
provenance and is not a statement of current completion.

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

## 14. Original immediate decision (completed)

This was the review packet that closed W0. It is retained to show what was
accepted, not as a request for another architecture-freeze review.

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

## 15. Original agent launch matrix (superseded)

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
> distributed HBM live buffers, with topology, collectives, repair, quarantine, and
> yield-aware recompilation. Work only in allocated DeepSeek-ROM paths. Export
> complete ordinary semantics into released common contracts without
> model-specific shared opcodes. Begin with one checkpoint-derived connected
> route/live-buffer/communication vertical slice, then follow the lane gates toward
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
