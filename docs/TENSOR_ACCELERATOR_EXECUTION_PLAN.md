# Production tensor-accelerator compilation and simulation plan

**Document status:** active working execution plan; architecture-review approval
and gate closure remain evidence controlled

**Plan version:** 1.9

**Initial issue:** 2026-08-28

**Last reconciled:** 2026-08-29 against the committed `main` baseline, the
concurrent-session working trees, and the isolated `ta-integration` worktree

**Reconciled implementation heads:** `main@3baf87c` and admitted accelerator
implementation `ta-integration@324f48d`; dirty and untracked implementation
files in either worktree remain working state, not release evidence. Commit
`c07331b` is the coherent connected-layer implementation handoff, and `1f4e52f`
reconciles its evidence boundary into this plan. The connected implementation
links the previously qualified embedding, attention, transactional-KV, residual,
and MLP paths in one generated full-width Qwen layer deployment and closes neutral
lowering, ABI 2.4 commands, 16-bank SRAM and tiled-HBM planning, independent
reconstruction, causal artifact-only execution, strict schemas, corruption
rejection, full compiler/runtime regression, strict ABI 2.0 through 2.3 replay,
a retained execution report, and two byte-identical clean builds and runs.
Commit `2222f76` additionally admits bounded QW-FM1 final-output-family and ABI
2.5 development evidence; Section 1.9 records its exact non-full-model boundary.
Commit `74c0d59` subsequently closes QW-FM1 at the complete neutral-semantic
boundary for all 617 operations and 36 state resources; Section 1.10 records
that evidence and its exact non-physical boundary. Commit `324f48d` closes
QW-FM2 and QW-FM3 at deterministic physical compilation and independent
reconstruction; Section 1.11 records its exact non-execution boundary. The next
open horizon is artifact-only execution of the retained 36-layer deployment to
exact one-step logits and token selection.
Connected-layer or final-output-fixture closure does not imply a complete-model,
timing, RTL, physical, or comparison gate.

This integration copy is the authoritative tensor-accelerator program plan.
The concurrent-session planning draft was reviewed as governance input; no
dirty concurrent implementation, generated artifact, or checkpoint payload was
admitted with it. Implementation evidence enters this branch only through the
gate and handoff rules in Sections 16 and 17.

**Primary targets:** Qwen3-8B at an 8,000-token prompt context and
DeepSeek-V4-Flash-0731

**Primary architecture:** programmable tensor accelerator with HBM-resident
weights and mutable state, plus banked on-chip SRAM

**Comparison architecture:** OpenTallas ROM-resident-weight design

**Primary outcome:** compile and execute each complete pinned model through an
artifact-driven simulator and produce verified autoregressive decoding results

## Executive recommendation

Build the HBM-plus-banked-SRAM design as a programmable **tensor accelerator**,
not as a simplified general-purpose graphics processor. One hardware hierarchy,
capability ABI, and instruction set must accept separately compiled Qwen3-8B and
DeepSeek-V4 Flash deployments without resynthesis. The design is dynamic where
the models require it—sequence position, masks, sparse indices, expert choices,
addresses, queue occupancy, and state generations—but every dynamic dimension
has an explicit hardware bound and a fail-closed compiler or runtime check.

Do not freeze the active Qwen and DeepSeek ROM sessions. Let them continue to
own model-source fidelity, checkpoint locks, tokenizer and generation semantics,
independent numerical references, golden traces, and ROM-specific lowering.
Protect the common program with a narrower boundary: only the integration owner
changes the production-neutral IRs, tensor-accelerator capability and command
ABI, HBM/SRAM physical planner, and common simulator. The integration lane
consumes coherent, tested commits and immutable manifests, never dirty files from
another session. When a shared contract must change, pause only that interface
long enough to review and version it.

There is already a credible backend-neutral **Model Graph IR v2** and a real
Qwen adapter. It is a useful foundation, not a completed common compiler. The
committed production Tensor Kernel IR now represents every operation in the
complete 617-operation Qwen graph, including dynamic embedding, matrix,
RMSNorm, RoPE, KV preparation, GQA attention, residual, SiLU, last-row
selection, vocabulary projection, and the terminal 36-resource state commit,
without physical addresses or SRAM-bank assignments. This closes Qwen neutral
semantic coverage, not physical deployment or execution. It does not yet cover
DeepSeek's mixed-format, routing, expert, sparse-attention, compressor, and
complete state-operation union. The plan therefore preserves Model Graph IR v2,
grows a genuinely
model- and backend-neutral Tensor Kernel IR additively, and branches into ROM
and HBM/SRAM physical plans only after target arithmetic is explicit. A kernel
family is part of the production baseline only after it passes through neutral
representation, physical planning, independent checking, causal artifact-only
execution, and a coherent reviewed commit.

Use Qwen as the first complete-machine bring-up because it exercises the dense
BF16, GQA, KV, vocabulary, and decode paths with less dynamic control. Its
mandatory release gate is the actual checkpoint at exactly 8,000 resident prompt
tokens, followed by frozen greedy decoding through the common artifact-only
simulator. DeepSeek semantics and capability-union review proceed concurrently;
after Qwen short generation is stable, DeepSeek enters the same compiler and
simulator by distinct ordinary-path layer classes and then as a complete model.

Treat functional correctness, modeled timing, RTL correlation, and 130-nm
physical characterization as separate evidence gates. HBM remains external to
the 130-nm synthesized boundary. A ROM-versus-HBM/SRAM result is publishable only
after both backends use the same pinned checkpoint, tokenizer, graph semantics,
numeric profile, workload, process/PVT scope, HBM assumptions, output boundary,
and evidence class. Until then, accelerator runs are implementation evidence,
not performance claims.

## 1. Purpose and decision

This plan promotes the HBM-plus-SRAM tensor accelerator from an optional
analytical counterfactual to a first-class executable backend. It must share
model semantics, numerical contracts, source locks, and correctness vectors with
the ROM backend while retaining an independent physical plan, command schedule,
and memory system.

The program is successful only when a pinned checkpoint travels through an
unbroken, reproducible chain:

~~~text
pinned source, tokenizer, and checkpoint
  -> backend-neutral model graph
  -> target-numeric tensor kernels
  -> legal HBM and SRAM physical plan
  -> accelerator command stream and deployment artifacts
  -> artifact-only functional and timing simulation
  -> prefill, KV/state updates, logits, sampling, and decode loop
  -> exact expected token IDs and decoded text
  -> reconciled operations, bytes, stalls, cycles, energy events, and state
~~~

No analytical throughput estimate, handwritten command trace, framework fallback,
synthetic checkpoint, or successful RTL protocol test can substitute for that
chain.

This plan extends the executable-system program in
[EXECUTABLE_SYSTEM_RECOVERY_PLAN.md](EXECUTABLE_SYSTEM_RECOVERY_PLAN.md). It uses
the numerical requirements in [NUMERICS.md](../spec/NUMERICS.md), the artifact and
ABI principles in [FIRMWARE_COMPILER.md](../spec/FIRMWARE_COMPILER.md), and the
verification independence rules in
[VERIFICATION_PLAN.md](../spec/VERIFICATION_PLAN.md). It is additive while the
current ROM sessions finish their model-specific milestones. It becomes normative
only after architecture review and traceability integration.

### 1.1 Plan authority and change control

This document is the program plan, not the engineering backlog. It fixes the
intended outcome, system boundary, evidence chain, architectural partition,
dependency order, decision rights, release gates, and conditions that require a
redesign. Issue trackers and per-commit task lists are subordinate execution
records; completing them does not close a gate unless the evidence required here
also exists.

The plan is deliberately capability- and evidence-driven rather than
date-driven. Calendar targets may be attached after benchmark-host capacity,
checkpoint availability, simulator throughput, RTL scope, and public-PDK tool
throughput are measured. A schedule that assumes those quantities before
measurement would create false precision. Gate order and dependencies are
normative even when calendar estimates change.

Changes to a pinned workload, arithmetic rule, graph or kernel contract,
hardware capability, command ABI, simulator timing rule, process corner, or
comparison boundary require a versioned decision record. The record identifies
which compiled artifacts and closed gates are invalidated and must be rerun. A
result produced before such a change remains historical evidence and is not
silently relabeled.

### 1.2 Reconciled implementation baseline

The implementation is already beyond a paper-design starting point, but it is
well short of an end-to-end accelerator claim. The baseline at this revision is:

| Program surface | Evidence present | Remaining plan obligation |
|---|---|---|
| Neutral semantics | Production Model Graph IR v2 defines checkpoint bindings, runtime symbols, bounded predicates, and transactional state. Commit `74c0d59` independently proves one-to-one neutral lowering for all 617 Qwen operations, 1,053 tensors, 399 checkpoint-bound weights, and 36 transactional KV resources, including final normalization, last-row selection, vocabulary projection, and terminal atomic commit | Reconcile the complete DeepSeek ordinary graph and prove zero unknown operations and complete state coverage for that second model profile |
| Qwen source and checkpoint | Pinned Qwen configuration/checkpoint adapter and deterministic graph identity exist | Keep the adapter semantic-only and bind the complete tokenizer, workload, and target-reference release manifests |
| Target arithmetic | Committed ordered BF16 matrix, full-width and per-head Qwen RMSNorm, position-indexed RoPE, causal GQA/softmax, transactional-KV, exact BF16 residual-add, materialized-BF16 SiLU-multiply, last-row selection, final RMSNorm, and full vocabulary-projection contracts have independent scalar oracles and separate optimized implementations. One connected actual-checkpoint layer reproduces every declared intermediate, `hidden.1`, and committed KV state exactly under those contracts | Connect the admitted contracts to authentic `hidden.36` and complete logits, qualify every DeepSeek ordinary-path numeric family at full target dimensions, and preserve first-divergence evidence when 36 layer instances are assembled |
| Compiler/simulator slice | Commit `324f48d` compiles and independently reconstructs all 36 Qwen layers, final normalization, selection, vocabulary projection, and terminal commit in one deterministic physical deployment; the earlier connected-layer simulator still supplies the deepest data-bearing execution evidence | Execute the retained complete deployment to exact logits and one token decision; physical compilation is not complete-model execution evidence |
| Qwen model-specific execution | The concurrent Qwen service path has passed deterministic deployment and an exact 8,000-token prefill plus 32-token release gate | This is reference evidence, not `TA-QWEN-4`; rerun the same workload through the common HBM/SRAM command simulator with no model-specific service fallback |
| DeepSeek reference coverage | Graph extraction and several exact numeric, routing, lookup, indexing, structural, and selected linear paths exist | Close every ordinary target-only operator, state transition, layer class, and generation path; keep DSpark/speculation in a separate profile |
| Physical evidence | Repository flows can support public-node exploration | Characterize the frozen accelerator at 130 nm; all current development capabilities and cycle costs remain explicitly uncharacterized |

The integration baseline is the isolated `ta-integration` branch. Work in the
dirty shared `main` worktree belongs to the concurrent Qwen and DeepSeek sessions
and is neither copied nor rewritten. Integration rebases only onto coherent,
committed `main` history. Locally cached checkpoints are referenced by immutable
identity and are not duplicated into another worktree or deployment tree.

The integration worktree now contains committed segmented-K BF16 support,
production command ABIs 2.0 through 2.5, strict uncharacterized development
capabilities, neutral lookup/matrix/RMSNorm/RoPE/KV/attention/state/add/SiLU
kernel artifacts, independent slice and connected-layer checkers, and causal
functional simulators. Their round-trip, corruption, differential, schema,
determinism, reproducibility, compatibility, rollback, and regression tests
pass. The connected evidence qualifies one declared full-width Qwen layer at
the functional, data-bearing compiler/simulator boundary. It does not freeze
the complete cross-model instruction set, establish timing, or close a
complete-model program gate.

Commit `2317064` contains `bf16_add_rne_v1` and
`qwen3_silu_mul_bf16_v1`, an independent scalar reference, a separate optimized
implementation, exhaustive differential coverage over all 65,280 finite BF16
gate encodings, and an authentic full-width layer-0 qualification. Its strict
report schema, retained report, targeted checks, and complete compiler/runtime
regression pass. That commit closes numerical qualification. Commit `7433b24`
closes the corresponding neutral Kernel IR records, ABI commands, physical
lowering, independent deployment reconstruction, and artifact-only command
execution for the bounded downstream slice. Commit `c07331b` then composes that
work with embedding, Q/K/V, attention, and KV in one authenticated command
stream. Its seven additional strict schemas raise the production schema catalog
from 55 to 62. The complete-model assembly and final-output path remain open.

Command ABI 2.2 adds bounded `ROPE_BF16` under an uncharacterized development
capability for 32 query heads, eight KV heads, head dimension 128, and 8,000
positions. The retained `qwen3_rope_fp32_bf16_v1` contract and connected
actual-checkpoint qualification cover embedding through Q, K, and V projection,
per-head Q/K normalization, and position-7,999 RoPE. The retained
capability ID is
`fd46cec29fc2f621eb5130e0e6b52da2967f6c8abf8e2e39439efd7b5640ccba`;
the coefficient-table SHA-256 is
`82b9d0c0dc0c98906ced230591852dbd27d73760de42df8de253ae29243034b9`;
and the qualification report ID is
`42be4b6e14ca271c583e0b8f4bb0bc9a5e854e4e5aa918b0e90acc6217d763ae`.
The 3,082-command unified deployment is reconstructed by a separately
implemented checker and executed through the artifact-only simulator. The build
ID is
`b84d8f049fd16d90bed1aeb67c7317919d80ca3096055688d3a2144a81c06b63`;
the independent-check ID is
`249852ee5f014040de56712e2bbb2d35123d1ffe1025c11e2fcfa8c1ae912023`;
and the execution-report ID is
`af4b5b5d3ea68689f073fdc22584699462ad64c44295120cea7a5e7873383730`.
Its Q-rotary, K-rotary, and V hashes match the independent qualification.
All ten artifact classes validate against strict Draft 2020-12 schemas. Missing
and reordered commands, rehashed HBM corruption, SRAM corruption, out-of-range
runtime IDs, forged values and counters, and causally missing DMA, matrix,
RMSNorm, or RoPE work fail. The retained report and two fresh-directory builds
are byte-identical. This closes the slice-level compiler and functional-simulator
evidence at `ta-integration@f94384c`, not the complete `TA-COMP-2` or `TA-SIM-3`
program gates.

### 1.3 Closed projection evidence and its boundary

The first real HBM/SRAM vertical slice is retained as a reproducible baseline,
not as a proxy for end-to-end inference. It binds row zero of Qwen's
`model.embed_tokens.weight` to
`model.layers.0.self_attn.q_proj.weight` and executes the actual 4,096 by 4,096
BF16 projection. The source-weight SHA-256 is
`fd56b85bf301661c8655ed517928304d25df7d6b3ea3d9be85c021159d61bad8`;
the output SHA-256 is
`b8ee116d31d645204b14b342db84d2f200e8c300f6dc17bb472d0cf3e1b42012`.

The retained capability is intentionally classified
`uncharacterized_development`. It declares a 256-GiB external-HBM address space,
16 SRAM banks of 1 MiB each, and the full data-format union required by both
models, but qualifies only `bf16_tensor`. It contains no clock, bandwidth,
latency, or energy values and enables no performance claim. Its capability ID is
`7ab91e973a310eca05a26c1cbfed299f6416e3c25c9041a5bf44081c6f741ab5`.

The physical plan uses `M=1`, `N=64`, and `K=256`. The generated program has
1,024 HBM-to-SRAM DMA commands, 1,024 ordered matrix commands, and one terminal
`COMPLETE` command. Independent checking reconstructs the source payload and
validates coverage, banks, ranges, dependencies, reduction ordering,
termination, and expected counters without invoking generator internals. The
artifact-only simulator executes 16,777,216 multiplications and the same number
of ordered accumulation additions, transfers 33,554,432 HBM bytes, and matches
all declared SRAM traffic and output bits exactly.

The canonical build ID is
`23e937621f93a01802884afea4be503719080a1fad9aec11afbc159ae689d8c1` and
the execution-report ID is
`278f616ca6bec57f7df69e2ef18ff12057c3604292de64bc73beca731c2e1103`.
Two clean-directory builds and executions are byte-identical. Missing,
reordered, malformed, corrupted, over-claimed, or incompletely covered work is
rejected or causally changes the result. These facts close the slice-level
instances of compiler and functional-simulator evidence only. Complete neutral
kernel coverage, timing simulation, Qwen and DeepSeek end-to-end execution, RTL,
130-nm characterization, and the governed comparison remain open.

### 1.4 Closed embedding-through-RMSNorm evidence and its boundary

The second committed vertical slice, `ta-integration@0771d84`, begins from a
runtime token ID, selects the corresponding authentic Qwen embedding row with a
bounded indexed HBM transfer, loads the actual layer-0 input-normalization
weight, and executes full-width RMSNorm through the common command path. The
neutral kernel artifact contains `EMBEDDING_LOOKUP` and `RMS_NORM`; HBM
addresses, row stride, SRAM banks, and transfers remain confined to the physical
plan.

Command ABI 2.1 is an additive extension of ABI 2.0. Its retained capability is
still `uncharacterized_development`, qualifies `bf16_tensor` and `vector_fp32`,
and has capability ID
`2c4d246c06bda5cfe4c583df29f68deff17ea8286b87cb2c9598197fcb296ccd`.
The canonical build ID is
`4cdd371c63dda8db64f0fe101777de1f0de0043ca8c01474f4b554cfefe65ba6`;
the execution-report ID is
`ef9143adedbf06a57340539b212dc9d76648323e1c2b72269ae2e748d8a1c28f`;
the output SHA-256 is
`976d6de1a3ed91a066c7efed4354e578edf366a3b51a7e6077d68282981ffa58`;
and the independent RMSNorm qualification ID is
`542afccabfde8b5f9628a1b27ba394312305780db5f850a276f651c64e7dd972`.

The four-command program performs one indexed DMA, one direct DMA, one RMSNorm,
and one terminal `COMPLETE`. Independent checking validates source identity,
runtime-index bounds, placement, command order, byte coverage, and declared
counter formulas without importing generator internals. Fresh-directory
reproduction is byte-identical, ABI 2.0 projection replay remains exact, and
missing or corrupted causal work fails. This closes only the slice-level
compiler and functional-simulator evidence for embedding lookup and RMSNorm. It
does not by itself qualify Q/K/V preparation, attention, KV state, a complete
layer, timing, RTL, physical implementation, or end-to-end decoding.

### 1.5 Closed Q/K/V-preparation evidence and its boundary

The third committed vertical slice, `ta-integration@f94384c`, starts from a
runtime token and position, executes the authentic layer-0 embedding and input
RMSNorm, performs the full Q, K, and V projections, normalizes Q and K per head,
loads the selected row of an authenticated 8,000-position RoPE coefficient
table, and produces Q-rotary, K-rotary, and V through one generated deployment.

ABI 2.2 additively introduces bounded `ROPE_BF16` while strict ABI 2.0 and 2.1
replay remains byte-identical. The 3,082-command schedule contains 1,541 DMAs,
1,536 ordered matrix commands, three RMSNorm commands, one RoPE command, and one
terminal `COMPLETE`. Its SRAM plan assigns an exact role to each of 16 one-MiB
banks. The independent checker authenticates every source, reconstructs all
1,536 projection tiles and the complete coefficient table, proves HBM coverage
and zero padding, verifies SRAM allocation and the full legal schedule, and
recomputes every counter without importing compiler lowering.

The canonical build ID is
`b84d8f049fd16d90bed1aeb67c7317919d80ca3096055688d3a2144a81c06b63`;
the execution-report ID is
`af4b5b5d3ea68689f073fdc22584699462ad64c44295120cea7a5e7873383730`;
and the Q-rotary, K-rotary, and V payload SHA-256 values are respectively
`a846335c825cf9fb06213220acf157c6a805376b1324a7cec09d6fa4621e718d`,
`ce427ae533331720b9b58dde633e3ca352fa9fe0d3dd09d8cab222b799963858`,
and `b07011da7a3d58dcccceb91e596ceebc2084ab3c2fc9d0b6a9a8704e91ef8dc5`.
Strict schema, causality, corruption, compatibility, no-overwrite, full
compiler/runtime regression, and two-clean-directory reproduction evidence is
retained.

This closes only connected Q/K/V preparation for one authentic token at
position 7,999. It does not execute attention, prepare or commit KV state,
complete a layer, generate a token, establish timing, correlate RTL, provide
130-nm characterization, or enable a performance or architecture-comparison
claim.

### 1.6 Closed attention and transactional-KV evidence and its boundary

The fourth committed vertical slice, `ta-integration@d353f9d`, begins with the
authentic retained Q/K/V qualification, constructs a nonempty causal history,
prepares one new K/V entry, executes full-width Qwen GQA score scaling, causal
masking, softmax, and value aggregation, and atomically commits the new state.
The scalar semantic oracle and the optimized NumPy implementation are separate;
the artifact-only simulator uses the optimized implementation and does not
import compiler lowering or the scalar oracle.

Command ABI 2.3 additively introduces `KV_PREPARE_BF16`,
`GQA_ATTENTION_BF16`, and `STATE_COMMIT` while preserving strict replay of ABI
2.0 through 2.2 artifacts. Canonical development capability V4 bounds attention
at 8,000 positions and transactional state at 64 resources. The neutral Tensor
Kernel IR contains `KV_PREPARE`, `ATTENTION`, and `STATE_COMMIT`; physical HBM
addresses, four-bank SRAM allocation, transaction descriptors, and command
opcodes remain backend-lowering concerns.

The deployment contains a 32,784,512-byte HBM image and seven commands: three
required Q/K/V transfers, KV prepare, GQA attention, state commit, and terminal
completion. The separately implemented checker authenticates the input payloads,
reconstructs the HBM and SRAM plan, validates transaction generations and
resource bounds, proves schedule legality and required command causality, and
recomputes output, state, and counter expectations without importing compiler
lowering. The retained identities are:

- capability:
  `f7c9ef5c254ef2aa19607bc5451f2bec03e790a0cc74326c478d7ab60246635e`;
- qualification:
  `82bd8f8b687e6674d72220b6a749e43da5224a22ba3bbeba562284a449d5a5bd`;
- build:
  `df11a02f915722127788d21501609b693b388f0e6c02f8ca4a83dc8f878cac95`;
- physical plan:
  `52bf4f067e77cf71d266a391fc6affae1e74ce817f08f43848d3650621dc3ff7`;
- independent check:
  `d6e971ed42ffa386ca22b7be53818bf5f84da478a25081107777934d28478b3d`;
- neutral Kernel IR:
  `04b2294e406ccc915bfd0c72cd5baf024221559941e31361fc8c85b03cc120a6`;
- execution report:
  `cf62189cc5d3e4e370b76e68767e6630e884077bb8dc39e3ba7c05646f43ef13`;
- attention output:
  `d53e8a3890eb01357fb60ec2607a716179cec0eb556e28629963af655cd3e1fb`;
  and
- committed state:
  `c446dd569837a2acf3f6a2333799794caaf0a7ae2919f42edecfcd6f7fd6bc56`.

Missing or reordered Q/K/V transfers, missing attention or commit, rehashed HBM
or SRAM corruption, forged output/counter expectations, stale generations,
mixed transaction descriptors, corrupt committed state, and abort paths fail or
preserve the prior committed state as required. Compiler/checker/simulator
import-independence tests, the full compiler/runtime regression, and two clean
byte-identical builds are retained.

This closes one authentic attention and one-resource transactional-KV
qualification slice. The one-resource commit is explicitly a subset of the
Qwen graph's terminal 36-resource model-forward commit; it is not evidence for
a complete layer, all-layer atomicity, full prefill/decode, cycle timing, RTL,
130-nm behavior, or a ROM comparison. The capability remains
`uncharacterized_development`, so the slice authorizes no latency, bandwidth,
energy, or performance claim.

### 1.7 Closed post-attention and MLP evidence and its boundary

The fifth committed vertical slice, `ta-integration@7433b24`, begins with the
authentic retained attention output and the checkpoint-authenticated
`hidden.0` residual. It executes graph nodes `node.0010` through `node.0017`:
attention output projection, BF16 residual add, post-attention RMSNorm, gate and
up projections, a materialized-BF16 SiLU multiply, down projection, and the
final BF16 residual producing `hidden.1`. The neutral Tensor Kernel IR contains
generic `MATMUL`, `ADD`, `RMS_NORM`, and `SILU_MUL` records; it contains no HBM
address, SRAM bank, or command opcode.

Command ABI 2.4 additively introduces bounded `ADD_BF16` and
`SILU_MUL_BF16` while retaining exact ABI 2.0 through 2.3 replay. Development
capability V5 remains `uncharacterized_development`, retains external HBM at the
130-nm boundary, and admits the declared 1-by-16,384 maximum vector shape. The
compiler assigns 13 distinct SRAM banks and tiles all four authentic projection
weights into a 335,568,896-byte HBM image. The measured legal program contains
20,488 commands: 10,240 weight-tile DMAs, three direct DMAs, 10,240 ordered
matrix commands, two residual adds, one RMSNorm, one SiLU multiply, and terminal
completion. This corrects the pre-execution planning estimate that had
undercounted the down projection: its 4,096-by-12,288 weight requires
64-by-48, or 3,072, tiles.

The separately implemented checker does not import compiler lowering. It
rereads the locked checkpoint, rediscovers all eight graph operations,
reconstructs every projection tile and HBM byte, proves HBM alignment, coverage,
and zero padding, proves SRAM roles, bounds, and non-overlap, reconstructs the
entire ABI program, and derives counters and output expectations. The
artifact-only simulator imports neither the checker, qualification computation,
framework, nor scalar oracle. It tracks initialized SRAM bytes, requires a fresh
causal DMA for every matrix tile, enforces complete N coverage and strictly
increasing K segments, executes the independent optimized kernels, and fails
completion if any required intermediate, command, or final output is absent.

The retained identities are:

- capability:
  `773ec796177d0ae3dc795459afd7cf4f59203ac637afed0ee703c62401c1bb47`;
- qualification:
  `94cc82dd113e16f05795c0de36930800701014e37e08267ce355ecfba3cfeea9`;
- build:
  `9609e03551b2b4e9509fcd1c6be08dd546dc20aac97289958e70b1d4325ec3a2`;
- physical plan:
  `4c7ffe6e22945f4fdbf1b0027994886c26b1567eca53aef149a25d607030f853`;
- independent check:
  `357a7df565fa86809215f30cee278145e285103db426c10868980d231107ad27`;
- neutral Kernel IR:
  `ff09706b8e1540c020c2fa6e4f0b9b6741e89f5ca6f9e3eb71f6b60307909175`;
- HBM image:
  `e42c0dc596d99bdcf9b5fc569a39bdfe8f3eaa7ebc396a43eef9792bbd236081`;
- execution report:
  `783c48f0fd81d174c54ab82ddf3945a7b518d55e33c84707cb02a0337e879db7`;
  and
- final `hidden.1`:
  `7c65791e13e3814af26b0114a5437a3ff44e91b5728ca5e1f23f1f2b7929bf7a`.

All eight declared intermediate hashes and all 37 counters match independent
expectations exactly; 167,772,160 projection multiplications and ordered
additions, 8,192 residual additions, and 12,288 SiLU elements execute with no
observed saturation. Seven new strict schemas raise the production schema
catalog from 48 to 55. Two clean builds and two causal runs are byte-identical.
Missing or reordered commands, missing vector work, rehashed HBM corruption,
SRAM corruption, physical leakage into neutral IR, dependency coupling, and
overwrite attempts fail. The full compiler/runtime regression and the complete
ABI 2.0 through 2.3 compatibility campaign pass.

This closes only the bounded post-attention/MLP slice. Its retained attention
output is an authenticated handoff artifact, not a command-connected predecessor
inside the same deployment. It therefore does not close a complete Qwen layer,
all-layer KV atomicity, model generation, timing, RTL, 130-nm characterization,
or the governed ROM comparison. The required connected deployment is now closed
separately at `c07331b` and recorded in Section 1.8; the boundary stated here
continues to apply to the historical slice evidence.

### 1.8 Closed connected-layer evidence and its boundary

Commit `ta-integration@c07331b` closes the next architectural horizon: one
generated, full-width Qwen layer connects runtime token and position inputs to
`hidden.1` and committed `kv.layer.0` state without an injected Q/K/V,
attention, or downstream activation handoff. A single 19-kernel neutral Tensor
Kernel IR covers embedding lookup, four RMSNorm instances, seven projections,
RoPE, KV prepare, GQA attention, two residual adds, SiLU-multiply, and state
commit. It contains no HBM address, SRAM bank, or command opcode.

The physical plan builds one 422,765,184-byte HBM image, tiles all seven
projections, and assigns 26 live-range-checked SRAM regions across the existing
16 one-MiB banks. Intermediate Q/K/V, attention, and downstream activations are
caused by the command stream and SRAM lifetimes; no retained activation region
can bypass a predecessor. The ABI 2.4 program has 23,570 commands:

| Command class | Count |
|---|---:|
| Direct HBM/SRAM DMA | 11,780 |
| Indexed DMA | 2 |
| Ordered BF16 matrix tile | 11,776 |
| RMSNorm | 4 |
| RoPE | 1 |
| KV prepare | 1 |
| GQA attention | 1 |
| Residual add | 2 |
| SiLU-multiply | 1 |
| State commit | 1 |
| Completion | 1 |

The simulator independently authenticates source locks, Model Graph IR,
neutral Kernel IR, physical plan, HBM regions and tiles, SRAM layout, commands,
checker output, expectations, and execution request. It interprets the one
integrated command stream causally and imports no compiler builder, independent
checker, qualification computation, framework, or scalar oracle. `STATE_COMMIT`
is legal only after successful production of `hidden.1`; failure before that
boundary leaves the prior state intact.

The canonical connected-layer identities are:

- build:
  `80f3698dfedd2852ee2800be2d5cb1397dd2100d755c52fd30e0e6c2d17cd01e`;
- physical plan:
  `4b58c336aa79b9d9d863b1470f498e1ae1a64620743e23e417b085106810379c`;
- independent check:
  `7304eb5b8777fe0631e567102549cc5f9a902b1feaa23d5fee382590ceb1ebfc`;
- neutral Kernel IR:
  `4c3723a04ec8ce213267f8c005b10d50bf6300c4c98321846b7082ea9f7dbef1`;
- source lock:
  `f1f6d7b3fc7d7e8cfa9bf2e925d7f3ae00460ca6e9bdcab51fe81edf43216ce6`;
- execution expectations:
  `09fab39f148c8e1c01f654d24f342b15ba607394669ae0c3cc146a0e6c964a7c`;
- qualification bundle:
  `d7dbe713822c87bf5ce4b781cb77961af1d4dd08f6b54d50287fae301e740dcf`;
- HBM image:
  `b3ef0d7d81fc9b78122c56c57e2a6ec7499d83d742aec3960ee40eb2c09deb23`;
- command program:
  `ab2318259cfdc669d6050423cf8da9643baa5d012b50816ede06bb2cad28114a`;
- execution report:
  `86453b0822f2fd5f045da0fea67f51361e16999c263ded30b1ad497d7f50cca2`;
- `hidden.1`:
  `7c65791e13e3814af26b0114a5437a3ff44e91b5728ca5e1f23f1f2b7929bf7a`;
  and
- committed KV state:
  `c446dd569837a2acf3f6a2333799794caaf0a7ae2919f42edecfcd6f7fd6bc56`.

All 72 counters reconcile exactly. The run writes 385,901,568 bytes into SRAM
through DMA, reads 385,918,208 useful and transferred HBM bytes, and writes
4,160 useful and transferred HBM bytes. Two clean builds and two causal runs are
byte-identical. Missing or reordered KV prepare, attention, downstream, SiLU,
commit, or completion work; early commit; fully rehashed HBM corruption; SRAM
plan corruption; physical leakage into neutral IR; source corruption; and
overwrite attempts fail. All 62 production schemas, the full compiler/runtime
regression, and strict ABI 2.0 through 2.3 compatibility replay pass.

This evidence closes one connected layer only. It does not execute the other 35
layers, final RMSNorm, vocabulary projection, logits, token selection, prefill,
or decode. It supplies no characterized clock, cycle, bandwidth, energy, RTL,
130-nm, or ROM-comparison evidence and therefore closes none of `TA-QWEN-4`,
`TA-RTL-6`, `TA-PHY-7`, or `TA-CMP-8`.

### 1.9 Admitted final-output-family evidence and its boundary

Commit `ta-integration@2222f76` admits bounded Qwen final-output-family evidence.
It closes the source, numeric, neutral-schema, and development-command contract
needed to begin complete graph lowering. At that commit it did not close QW-FM1
and it still does not execute the selection command through a physical
deployment or authorize a complete-model or performance claim. Section 1.10
records the later QW-FM1 semantic closure.

The admitted change additively provides:

- neutral `LAST_TOKEN_SELECT` semantics under `exact_index_select_v1`, with a
  logical row-count symbol and no physical address, SRAM bank, command opcode,
  or Qwen-specific name in the Tensor Kernel IR;
- a generic bounded `DMA_SRAM_INDEXED_TO_SRAM` command definition in ABI 2.5,
  while the connected-layer artifacts remain explicitly bound to ABI 2.4 and
  physical lowering/checking/execution of the new command remains open;
- development capability V6, ID
  `ab4942fe56415580b6a38b9177e4652290f3d556ee2feba9da0aa668eec99f43`,
  which adds only `exact_index_select_v1`, remains
  `uncharacterized_development`, and permits no performance claim;
- independent optimized and scalar selection implementations that select
  logical row `logical_rows - 1`, reject nonfinite BF16 in the selected row,
  and prove that unread capacity-row contents cannot affect the result; and
- a strict retained qualification artifact for graph nodes `node.0613`
  final RMSNorm, `node.0614` last-token selection, and `node.0615` the
  151,936-way vocabulary projection using authentic checkpoint weights.

The retained qualification report ID is
`bbd7abf87cdb0bd1450efe3da688b2f0ba8b2353e14f44e4a698f57cf3d2339d`.
It reports final-normalization and selected-row hash
`f7d59069dc6d3671f93fbe96b0f2f607b3b9b4962adedece208125b973c8ccc3`,
logit hash
`f367621a1bbc2e90410e00c67a9ff48ad93d5f683bdad8b86644bfeab123cff6`,
unique greedy token ID `118195`, and zero projection saturations. The source
payloads are the authentic `model.norm.weight` and `lm_head.weight` tensors.

That result deliberately uses the retained connected-layer `hidden.1` as an
operator-family fixture. It is not `hidden.36`, is not caused by a 36-layer
command program, and is explicitly labeled `full_model_claim: false`. The
fixture proves that the final-output numerical families can operate at the real
width and vocabulary size; it does not prove that a complete Qwen deployment
produces those values or that token `118195` is a valid end-to-end model result.

Admission resolved the original strict-schema mismatch: the schema now admits
minor 5, distinguishes the ABI 2.4 and 2.5 contract sets, and requires
transactional state for both. Adversarial schema tests reject ABI 2.4 selection
overclaim, ABI 2.5 selection omission, and missing ABI 2.5 state. The focused
campaign, formatting, lint, bytecode compilation, broad compiler/runtime
regression, and two fresh qualification reproductions pass; both reproductions
are byte-identical to the retained report.

At admission, two dependent obligations remained. The second—complete
617-operation and 36-resource neutral coverage with the final-output records
occurring exactly once—closed at `74c0d59`. The first remains: an independent
physical checker and the artifact-only simulator must consume the selection
command without sharing generator or expected-result code. The independent
physical-checker part closed at `324f48d`; artifact-only execution remains open.
Admitting the operator-family fixture, neutral semantic bundle, or physical
deployment does not erase the QW-FM4 obligation.

The physical admission review must also prove how logical last-row selection
maps onto tiled execution. An 8,000-by-4,096 BF16 activation is larger than the
declared 16 MiB SRAM, so the implementation may not assume that the complete
sequence tensor is SRAM resident. The compiler must either select from the
last live tile or use a certified streaming/fusion transformation while
preserving the neutral `LAST_TOKEN_SELECT` effect, exact index semantics, and
observable counter accounting. The physical plan and independent checker must
derive the logical-to-tile mapping and reject off-by-one, stale-tile, truncated,
and out-of-range selections.

Capability V6 remains an 8,000-token development qualification, not the final
cross-model capability. The separate Qwen 8,192 boundary and DeepSeek's larger
declared context profiles remain open capability, compiler, state-capacity, and
execution decisions. They may not be inferred from the existence of a wider
context-address field or from a two-row selection fixture.

### 1.10 Closed Qwen complete-neutral-semantic evidence and its boundary

Commit `ta-integration@74c0d59` closes QW-FM1 at the Qwen semantic and numeric
boundary. It emits one backend-neutral Tensor Kernel IR record for each of the
617 operations in the pinned Model Graph IR and independently reconstructs that
mapping without importing the forward lowerer. This is complete Qwen neutral
coverage; it is not a full physical deployment, command program, or model run.

The retained bundle binds graph ID
`989ab0d4dae37c783e2eff349e1ed1fe16279288e12a19a94975f43b0254426f`,
checkpoint-lock ID
`fa32932d73c1f605a69db3a803f1f25ef5b022a98cc3c6b5fe42b7f7af024e2a`,
capability V6, and all four admitted Q/K/V, attention, connected-layer, and
final-output qualification reports. Its identities are:

- semantic coverage report:
  `00dbdf8dbb0278bac831027a1396f79a08a399a83c6ce0387cd981fabf62b106`;
- complete neutral Kernel IR:
  `270b7609f2ea101593b3870a498bda3320336c94b27862dca7f991352727e050`;
  and
- independent semantic check:
  `280ee81a2229b12d079d0b104a1f88e23df59989e60bd011adfaaa68910a2215`.

The coverage proof accounts for all 1,053 tensors, including 399
checkpoint-bound weights, 652 activations, one input, and one output. It checks
the exact prefill and decode request predicates, checked nonnegative `i64` to
`u32` token-index conversion, `span_tokens` dynamic row extents, consecutive
RoPE positions, all 36 `read_committed -> prepare -> read_prepared -> commit`
state-effect sequences, and one terminal 36-resource atomic commit. The neutral
artifact includes `hidden.36`, final RMSNorm, logical last-row selection, the
151,936-way vocabulary projection, and committed logits exactly once. It
contains no HBM/ROM/SRAM placement, physical address, bank assignment, or
command opcode.

The independent checker rereads the graph, capability, four qualification
reports, coverage report, and complete Kernel IR. It separately derives graph
cardinality and identities, runtime symbols and entrypoints, every source
operation's arity, tensor shape and dtype, exact source attributes, layer
ownership, numeric contract, state effects, qualification binding, dynamic
kernel shape, and backend neutrality. Adversarial tests reject unknown source
attributes, relocated state effects, request-predicate drift, mixed checkpoint
identities, forged claims, capability substitution, qualification rebinding,
dynamic-shape drift, and numeric-contract drift. All 65 strict production
schemas validate. The 554-test compiler/runtime campaign passes with only the
declared unavailable-source skips, and two fresh builds are byte-identical to
each other and the retained bundle.

The coverage artifact intentionally fixes `full_model_execution`,
`physical_plan`, and `timing_or_performance` to false. It does not allocate or
copy the approximately 16.38-GB immutable payload, prove SRAM liveness, emit a
complete ABI 2.5 program, execute `hidden.36`, compute complete-model logits,
generate a token, or advance any committed KV state. Those obligations began at
QW-FM2; the physical parts close in Section 1.11, while QW-FM4 execution remains
open. `TA-SEM-1` also remains open because the complete DeepSeek ordinary-path
semantic and numeric union is not yet closed.

### 1.11 Closed Qwen full-model physical compilation and reconstruction

Commit `ta-integration@324f48d` closes QW-FM2 and QW-FM3 at the physical-artifact
boundary. It does not close QW-FM4 or claim that any complete-model activation,
logit, state transition, or token has executed. The compiler consumes the one
pinned Qwen checkpoint and the QW-FM1 semantic bundle, streams every one of the
399 authenticated weight tensors into a deployment image, assigns every
materialized graph value to a checked SRAM lifetime, and lowers all 617 graph
operations into one ABI 2.5 command template.

The retained identities are:

- deployment build ID:
  `3460d88ce16f5ef0ca4d1277daf8ebb19ae555e88822f95d55deb4aa8cad290f`;
- physical-plan ID:
  `ba1d95462450d2cd059e6b55271c73ea90895515c9a4129bba1b51df265109c3`;
- independent physical-check ID:
  `a2de72293d32d603a84c28f6ae49d8e07cf67c56e88a507f0ab456990558a15a`;
- physical source-lock ID:
  `b00cd2cd720802ef778d03f3ef888325384e6673867fe202000c1b67e1744d24`;
- logical HBM-image SHA-256:
  `c266c5d0060c45fad0f8d19a238eb217e63657569735f06e635a13ec4c25e058`;
  and
- command-program SHA-256:
  `f0ce6b50b01f462f837a28504e6ff9a024a24d24abf339f924875d0c2059bcec`.

The exact logical HBM image is 17,573,089,792 bytes in 17 fixed logical 1-GiB
shards. It contains 16,381,470,720 immutable checkpoint-weight bytes,
1,179,648,000 bytes of zero-initialized K/V capacity for all 36 layers at 8,000
tokens, a 4,096,000-byte authenticated RoPE table, two 2,304-byte state tables,
and 7,870,464 alignment/padding bytes. HBM remains external to the synthesized
130-nm boundary. The no-host-paging capacity certificate leaves
257,304,817,152 bytes of declared HBM margin.

The SRAM plan has 18 reusable slots across the 16 one-MiB banks, 617 tensor
assignments, 36 HBM-resident state handles, 145 staged normalization weights,
and 542 workspace assignments. Its most occupied bank uses 303,872 bytes. The
59,160,736-byte program contains exactly 924,386 commands, including 461,920
matrix tiles, 462,065 direct HBM-to-SRAM transfers, 37 indexed HBM transfers,
one indexed SRAM selection, and one terminal 36-resource `STATE_COMMIT`. The
command-capacity margin is 15,852,830.

The independent checker does not import the physical compiler. It separately
rereads the graph, capability, checkpoint lock, semantic artifacts, physical
plan, capacity certificate, request, and command program; rereads every locked
checkpoint payload; reconstructs the deployed direct and tiled hashes; verifies
all shard files, sparse-zero extents, coefficient identity, metadata, and
descriptors; re-derives SRAM capacities and overlapping lifetimes; and rebuilds
every command and kernel range. It audits both a prepublication candidate and a
published deployment, including the retained check and final manifest.

Two authentic builds completed from clean output directories without copying a
checkpoint tree. The first deployment was removed before the second was built;
all non-HBM artifact bytes, all shard hashes and geometry, and both manifests
were identical. A subsequent postpublication audit reproduced the retained
check ID. Corruption, truncation, early-commit/reorder, stale-generation,
claim-forgery, unsafe-path, range, overwrite, and checker-import-independence
tests reject their targets. All 71 strict tensor-accelerator schemas validate,
and the 563-item compiler/runtime campaign passes with only declared
unavailable-source skips.

The manifest fixes `full_model_execution` and `timing_or_performance` to false.
No `hidden.36` value, final-normalization value, complete logits, selected token,
or committed model step follows from this closure. QW-FM4 artifact-only
execution is now the active Qwen work package.

## 2. Meaning of production-grade

Production-grade in this plan describes the quality of the compiler, simulator,
verification, and release process. It requires:

- cryptographically pinned inputs and content-addressed outputs;
- versioned schemas, IRs, numeric profiles, capabilities, and command ABIs;
- deterministic, fail-closed compilation with no implicit defaults;
- complete operation, tensor, state, and storage coverage;
- independent generators and legality checkers;
- an artifact-driven simulator that does not import compiler lowering or model
  framework execution as its implementation;
- bit-defined arithmetic, ordering, exceptional behavior, and state commits;
- directed, randomized, property, corruption, fault, and compatibility tests;
- requirement-to-evidence traceability and reviewed waiver control;
- two-clean-directory reproducibility for canonical release artifacts;
- retained tool versions, commands, logs, manifests, seeds, hashes, and reports;
  and
- performance and energy claims derived from executed schedules and characterized
  hardware events rather than unpriced operators or inserted ceilings.

The public 130-nm work can apply production-grade methodology, but it cannot be
called foundry production signoff. Qualified HBM PHY IP, production SRAM
compilers, proprietary timing and reliability decks, package extraction, and
silicon correlation remain external gates.

## 3. System boundary

### 3.1 End-to-end boundary

The release boundary begins with text or a canonical token-ID fixture and ends
with generated token IDs and decoded text. The host performs pinned tokenization,
generation-loop control, and token selection. The tensor accelerator performs
every model-forward operation used by prefill and decode. The simulator must not
call the official model or a framework model between tokens.

The complete path is:

~~~text
prompt text
  -> pinned tokenizer and message encoding
  -> prompt token IDs
  -> accelerator prefill
  -> committed model and KV state
  -> final-position logits
  -> frozen host token-selection policy
  -> selected token
  -> accelerator decode step
  -> repeated logits and state commits
  -> stop/EOS handling
  -> pinned text decoder
  -> output text
~~~

Greedy decoding is the first mandatory policy because it gives an unambiguous
correctness result. Seeded stochastic sampling is a later qualification profile
with its random-number stream and selection algorithm included in the request
identity.

### 3.2 Initial inclusion

The first release includes:

- actual Qwen3-8B and DeepSeek-V4 Flash checkpoint payloads;
- ordinary target-model prefill and autoregressive decode;
- complete embeddings, all transformer layers, final normalization, vocabulary
  projection, logits, KV/state updates, and generation-loop behavior;
- Qwen dense BF16 and GQA execution;
- DeepSeek dense, routed-expert, sparse-attention, compressor, routing, selection,
  and mixed-format execution required by the pinned ordinary path;
- HBM storage for weights and large mutable state;
- SRAM tiling, buffering, staging, and metadata;
- one hardware capability set that accepts separately compiled deployments for
  either model; and
- batch-one correctness, with bounded multi-session and larger-batch behavior
  specified and tested separately.

### 3.3 Initial exclusions

The first closure does not silently include:

- training, fine-tuning, or backward execution;
- arbitrary user-defined general-purpose compute kernels;
- simultaneous residency or concurrent execution of both target models;
- speculative draft/acceptance execution unless a separately frozen DeepSeek
  profile is enabled;
- host paging of active weights during a measured decode;
- a claim of end-to-end correctness at an unexecuted context length;
- a production HBM PHY synthesized from the public 130-nm PDK; or
- task-quality equivalence inferred only from one prompt.

These may be added through versioned profiles after the ordinary decode path is
closed.

## 4. Target workload contracts

### 4.1 Qwen3-8B verification target

The mandatory Qwen gate uses the exact pinned Qwen3-8B checkpoint and tokenizer.
The principal long-context fixture contains exactly 8,000 resident prompt tokens
before the first generated token. A separate 8,192-token capacity-boundary test
is retained because existing OpenTallas studies use that boundary. The two
numbers must never be conflated in reports.

The initial acceptance manifest freezes:

- model repository, revision, configuration, tokenizer, and every payload hash;
- 36-layer dense decoder structure;
- BF16 weight and activation contract;
- 32 attention heads, eight KV heads, and GQA semantics;
- prompt tokens, attention mask, position IDs, and generation boundary;
- ordinary, non-speculative decode;
- greedy token selection;
- a nontrivial generated-token count, no shorter than 32 tokens for the main
  long-context fixture unless EOS is the expected earlier result;
- expected per-step logits hashes, token IDs, state hashes, and decoded text; and
- separate short prompts that exercise EOS, stop limits, tokenizer edge cases,
  and layer-by-layer diagnostics.

Passing a short Qwen prompt does not close the 8,000-token gate.

### 4.2 DeepSeek-V4 Flash target

The mandatory DeepSeek gate uses the exact
DeepSeek-V4-Flash-0731 release at its pinned immutable revision and the complete
checkpoint payload. The first end-to-end profile is ordinary target-only prefill
and decode; DSpark or another speculative path requires an additional manifest,
semantic ledger, and acceptance gate.

The DeepSeek workload contract includes:

- all expected tensors and scale associations;
- all graph nodes and operator kinds in the pinned ordinary path;
- BF16, FP8 E4M3FN, MXFP4 E2M1, E8M0 scales, FP4 indexing, and FP32 boundaries;
- dense and routed experts, routing bias, top-k and tie semantics, shared experts,
  expert weighting, and deterministic reduction;
- ordinary, windowed, compressed, and sparse attention behavior selected by the
  source graph;
- compressor state, learned indices, KV/state prepare and commit, mHC, and
  Sinkhorn behavior where present;
- final logits, token selection, EOS/length behavior, and output text; and
- full tensor, memory, operation, communication, and state accounting.

The first complete-model correctness run uses a predeclared practical prompt
suite and an 8,000-token long-context profile. The official maximum context of
1,048,576 tokens is a separate capacity and qualification profile. The project
must not claim one-million-token end-to-end correctness until that path has
actually executed under its declared state, numerical, and performance policy.

### 4.3 Meaning of one dynamic accelerator

One dynamic accelerator means one RTL hierarchy, capability ABI, and instruction
set supports both models without resynthesis or hardware regeneration. Each model
may have its own compiled program, tensor layouts, schedules, and deployment
manifest. Model selection occurs between jobs by loading and validating a new
deployment.

Runtime-dynamic values include sequence length within a declared bound, current
position, active sessions, masks, expert selections, sparse indices, HBM
addresses, and buffer occupancy. Hardware bounds such as instruction fields,
tensor dimensions, top-k, expert count, tag count, SRAM capacity, and context
address width are explicit capabilities. A compiler error, not undefined
behavior, results when a deployment exceeds them.

## 5. Definition of done and hard program gates

| Gate | Required evidence | Claim enabled |
|---|---|---|
| TA-GOV-0 | Reconciled session commits, source ownership, clean integration worktree, pinned tools and inputs | Common implementation may begin |
| TA-SEM-1 | Complete neutral graphs and independent target-precision semantics for both models; zero unknown operations | Semantic coverage |
| TA-COMP-2 | Deterministic HBM/SRAM deployment, complete payload coverage, legal physical plan, command stream, and independent reconstruction/checking | Compiler correctness for declared profiles |
| TA-SIM-3 | Artifact-only functional and cycle/event simulation; exact state/counter reconciliation; no framework or host-compute fallback | Executable architecture correctness |
| TA-QWEN-4 | Actual checkpoint, full 36-layer prefill/decode, 8,000-token prompt, exact target logits/tokens/text and state | Qwen3-8B 8K end-to-end correctness |
| TA-DSV4-5 | Actual complete checkpoint, all ordinary-path layers/operators, prefill/decode, exact target logits/tokens/text and state | DeepSeek-V4 Flash end-to-end correctness for executed contexts |
| TA-RTL-6 | Generated programs execute representative complete kernels/layers through RTL co-simulation and match the architectural simulator | RTL correlation for tested scope |
| TA-PHY-7 | 130-nm characterized compute, SRAM, control, and interconnect feed the frozen capability model; timing and energy are traceable | Public-PDK physical-proxy performance |
| TA-CMP-8 | ROM and HBM/SRAM backends use identical model, numeric, workload, process, and reporting scopes | Governed architecture comparison |

No gate closes through document status alone. Every gate requires machine-readable
evidence, commands, hashes, tests, and a reviewed report.

## 6. Architectural evidence chain

The two physical backends branch only after shared semantics and target-numeric
kernels:

~~~text
                       independent official-source adapter
                                      |
pinned checkpoint ----> neutral Model Graph IR <---- target reference oracle
                                      |
                             Tensor Kernel IR
                                      |
                     +----------------+----------------+
                     |                                 |
              ROM physical plan                HBM/SRAM physical plan
                     |                                 |
             ROM command program             DMA/tensor/vector program
                     |                                 |
              ROM execution model          tensor-accelerator simulator
                     +----------------+----------------+
                                      |
                         common differential harness
                                      |
                         logits, state, tokens, text
~~~

The common frontend prevents semantic drift. The separate physical plans prevent
ROM assumptions from contaminating HBM/SRAM scheduling.

## 7. Tensor-accelerator architecture

### 7.1 Architectural principles

The accelerator is a bounded, programmable inference processor rather than a
general-purpose processor. It exposes only the operation
families, data formats, memory operations, synchronization, and state transitions
needed by the target capability union. It is sufficiently programmable to accept
both models and later compatible transformer deployments within explicit limits.

The baseline consists of:

1. a command processor and descriptor engine;
2. one or more tensor-compute clusters;
3. vector, reduction, normalization, and nonlinear service engines;
4. deterministic selection, routing, gather, and scatter support;
5. a banked SRAM scratchpad complex;
6. HBM request, response, protection, and address-mapping machinery;
7. an on-chip interconnect with bounded queues and backpressure;
8. session, KV, compressor, and generation state control;
9. telemetry, performance counters, poison/abort, ECC, and watchdog behavior; and
10. a versioned host and firmware ABI.

### 7.2 Tensor-compute cluster

The tensor cluster must support the union of:

- BF16-by-BF16 matrix operations with FP32 accumulation for Qwen;
- FP8 activation and dense/shared-weight operations required by DeepSeek;
- MXFP4 routed weights with E8M0 block scaling and compatible activation
  conversion;
- manifest-declared tiling, transpose, scale orientation, and edge masking;
- canonical reduction ordering and explicit conversion boundaries; and
- accumulator/result status for saturation and exceptional values.

The architectural contract freezes arithmetic and ordering. The physical
implementation may contain shared lanes or mode-specific lanes, but it may not
change visible results with stalls, routing, tile assignment, or clock throttling.

### 7.3 Vector and irregular-operation engines

The service side must have priced, executable implementations for RMSNorm,
residual addition, RoPE, scale/conversion, SiLU/SwiGLU, softmax, attention
reductions, compressor operations, index scoring, top-k, routing weights, mHC,
Sinkhorn, and final-logit preparation as required by the graph.

An unbounded VECTOR instruction is prohibited. Each operation has a shape
contract, latency/throughput model, scratch requirement, numerical reference,
compiler lowering, and simulator implementation. An operation may be decomposed
into smaller primitives only when the decomposition preserves the frozen numeric
contract.

### 7.4 HBM and SRAM hierarchy

HBM stores immutable weights, large KV/state regions, deployment images, and
spillable activations. SRAM stores active tiles, double buffers, reductions,
metadata, route/index results, and hot KV/state windows selected by the compiler.

The hardware exposes:

- HBM channels, pseudo-channels, burst and alignment rules, address mapping,
  outstanding tags, queue depths, and error behavior;
- SRAM bank count, width, ports, read/write latency, ECC granularity, arbitration,
  and ownership;
- asynchronous DMA descriptors and completion dependencies;
- gather/scatter and bounded indirect transfers for experts and sparse attention;
- barriers, events, and producer-consumer queues;
- explicit cache or scratchpad behavior, never an undocumented combination; and
- complete counters for useful bytes, transferred bytes, row activity, conflicts,
  stalls, retries, corrections, and occupancy.

The first implementation should prefer compiler-managed SRAM over a transparent
cache because placement and traffic then remain reproducible and independently
checkable. A cache may be evaluated later as a versioned alternative.

### 7.5 Dense and MoE execution

Qwen uses predictable dense weight streams. The compiler can channel-stripe
weights, double-buffer tiles, overlap HBM reads with compute, and retain
frequently reused metadata.

DeepSeek routing is data dependent. Router results produce bounded DMA and
dispatch work for selected experts. The architecture must not assume that a
fully static global schedule can name expert addresses before routing. It may use
compiled templates and runtime descriptors, with bounded queues and a worst-case
resource certificate. The simulator must consume the actual selected experts and
model their actual addresses and contention.

### 7.6 Capacity policy

The release configuration must hold the complete active checkpoint and required
state within its declared HBM capacity. If one package cannot hold DeepSeek plus
the selected context state, the architecture must either define a deterministic
multi-package sharding topology or reject the profile. Host paging is not counted
as HBM execution and cannot be hidden in a performance result.

Capacity includes payloads, scales, padding, alignment, command images, metadata,
ECC/integrity overhead, KV/state, buffering reserve, allocator fragmentation, and
fault reserve.

## 8. Compiler design

The current IR answer is deliberately split. Production Model Graph IR v2
already exists and is the backend-neutral semantic graph boundary. It is suitable
for both targets in structure, but Qwen and DeepSeek require separate coverage
proofs against their pinned ordinary execution paths. The production Tensor
Kernel IR now represents every operation in the complete 617-operation Qwen
graph, including lookup, ordered BF16 matrix, RMSNorm, RoPE, KV prepare,
GQA attention, residual add, materialized SiLU-multiply, final normalization,
last-row selection, vocabulary projection, and terminal transactional commit.
This is a real backend-neutral lowering boundary and closes Qwen neutral-semantic
coverage. It does not yet cover DeepSeek's complete ordinary-path operation,
numeric-format, routing, expert, sparse-attention, compressor, and state union.
Complete Qwen neutral coverage and physical compilation must not be mistaken for
a complete cross-model Kernel IR or complete-model execution.

The compiler therefore evolves additively from the existing Model Graph v2
contract. It does not adopt a private Qwen service IR, copy a dirty concurrent
session implementation, or force ROM placement concepts into neutral semantics.
The common lowering boundary is:

~~~text
model-specific source adapter
  -> production Model Graph IR v2
  -> backend-neutral Tensor Kernel IR
  -> backend-specific Physical Plan IR
  -> backend command program and deployment
~~~

The ROM and HBM/SRAM paths share the first two representations and then diverge.
This is the mechanism that lets one accelerator ABI accept separately compiled
Qwen and DeepSeek programs while also giving the ROM comparison a controlled
semantic baseline.

### 8.1 Source and checkpoint frontends

Each frontend binds an immutable model revision, all reviewed source files,
configuration, tokenizer, generation behavior, checkpoint index, shard headers,
payload hashes, and remote-code policy. It emits a complete tensor inventory and
a source-mapped semantic graph.

Qwen- and DeepSeek-specific code ends at the adapter boundary. Shared compilation
does not import model-specific deployment assumptions.

### 8.2 Backend-neutral Model Graph IR

The Model Graph IR expresses mathematical and stateful model behavior:

- stable operation and value identifiers;
- ordered inputs and outputs;
- symbolic dimensions with explicit bounds and divisibility constraints;
- tensor shape, layout meaning, source dtype, architectural dtype, and mutability;
- runtime predicates and structured control regions;
- persistent state, prepare/commit effects, aliases, and lifetime;
- exact scale, rounding, reduction, masking, and exceptional-value semantics;
- legal fusion and reassociation constraints;
- source anchors and reference-vector identities; and
- operation and state coverage status.

It may classify a value as immutable weight, persistent state, or transient
activation. It does not contain ROM_LOOKUP, HBM_READ, SRAM bank numbers, physical
addresses, or backend-specific instruction names.

The existing small ROM-bound IR remains a regression fixture. It is not
incompatibly redefined as the production-neutral IR.

### 8.3 Tensor Kernel IR

The Tensor Kernel IR makes target numerical execution explicit while remaining
independent of physical addresses. It represents:

- tiled matrix loops and reduction order;
- vector/reduction kernels and their rounding boundaries;
- attention score, masking, softmax, and value aggregation;
- conversion, packing, scale blocks, padding, and layout transforms;
- route, top-k, gather/scatter, and expert-reduction regions;
- state reads, prepares, commits, and barriers;
- scratch requirements and legal tile candidates;
- data dependencies and legal overlap;
- runtime shape and selection predicates; and
- exact operation and byte-accounting formulas.

Optimization passes may fuse, tile, specialize, or eliminate work only with a
machine-checkable semantic certificate. Floating-point reassociation is forbidden
unless the numeric profile explicitly permits it.

### 8.4 HBM/SRAM Physical Plan IR

The tensor-accelerator backend binds kernels and tensors to:

- HBM image, channel, pseudo-channel, address, burst, and alignment;
- SRAM allocation, bank, lifetime interval, port demand, and reuse generation;
- tensor tile, loop nest, engine, queue, and event dependency;
- DMA prefetch, double-buffer, gather/scatter, and spill operations;
- KV/state regions and transactional commit generations;
- runtime expert/index descriptor bounds;
- NoC routes and collective membership;
- expected operation, byte, queue, and cycle-accounting classes; and
- capability and fault/degraded-resource identities.

The planner must prove capacity, non-aliasing, initialization, liveness, bank-port
legality, bounded queues, descriptor-field bounds, state atomicity, and eventual
completion. Dynamic paths carry worst-case certificates and runtime guards.

### 8.5 Command ISA and ABI

The command stream contains explicit families for:

- control flow, loops, predicates, barriers, completion, and traps;
- HBM/SRAM DMA, gather/scatter, fill, and synchronization;
- tensor matrix and reduction work;
- vector, attention, normalization, conversion, and nonlinear work;
- route, top-k, expert dispatch, and selection;
- state and KV read, prepare, commit, discard, and generation advance;
- telemetry and assertion checkpoints; and
- poison, abort, drain, and error reporting.

Every instruction has fixed versioned semantics, field bounds, side effects,
completion behavior, and counter rules. Unknown opcodes, reserved bits, illegal
shapes, capability mismatches, and malformed dependencies fail before execution.

### 8.6 Deterministic deployment artifacts

A release build emits at least:

- source and checkpoint locks;
- neutral graph and operator-coverage report;
- Tensor Kernel IR and transformation certificate;
- canonical tensor index and content hashes;
- sharded HBM image and address map;
- SRAM allocation and liveness plan;
- DMA, kernel, and state schedules;
- command binaries and disassembly;
- capability, numeric-profile, and ABI bindings;
- tokenizer and generation-policy bindings;
- known-answer and trace-checkpoint manifests;
- independent reconstruction and legality reports;
- execution expectations and counter formulas; and
- one deployment manifest covering every artifact hash and schema.

Timestamps, host paths, directory order, uncontrolled seeds, and environment
incidents do not affect canonical identity.

### 8.7 Independent compiler checking

Independent checkers parse emitted artifacts without calling allocation,
scheduling, or lowering code. They must:

- reconstruct every canonical tensor from the HBM image;
- prove complete payload coverage and padding/integrity rules;
- replay SRAM lifetimes and detect alias or port conflicts;
- validate DMA ranges, dependency graphs, queue bounds, and termination;
- verify runtime-dynamic descriptor bounds;
- recompute operation and byte expectations;
- disassemble and validate every command;
- prove state prepare/commit ordering; and
- reject any tensor or operation without an execution role.

Generator/checker agreement is necessary but not sufficient; known-answer
execution is still required.

## 9. Simulator design

### 9.1 One simulator, multiple fidelity modes

The tensor-accelerator simulator is one architectural implementation with shared
artifact loading, command decode, state machines, memory maps, and counters. It
supports three modes:

1. **Bit-exact functional mode.** Executes complete data values and all visible
   state as quickly as practical. It is required for full-model development and
   differential diagnosis.
2. **Data-bearing timing mode.** Executes the same values while scheduling engines,
   DMA, SRAM, HBM, queues, dependencies, and backpressure in modeled hardware
   cycles. It is the decisive end-to-end simulator mode.
3. **Timing-only replay mode.** Omits or hashes selected data for large design
   sweeps after a matching data-bearing trace exists. It may support performance
   exploration but cannot close correctness.

The full-model program must be capable of running in data-bearing timing mode.
Checkpoint/restart, deterministic partitioning, trace filtering, and optimized
target-numeric kernels make that run tractable; they do not change architectural
results.

### 9.2 Artifact-only execution

The simulator accepts only deployment artifacts, runtime inputs, capability data,
and declared memory/device models. It may not import:

- the compiler's internal graph or scheduling objects;
- expected-result calculations;
- Qwen or DeepSeek framework execution;
- model-specific handwritten tensor paths;
- an analytical token-rate result; or
- hidden host fallbacks for unsupported operations.

Every executed instruction, memory transaction, state update, and result is caused
by a deployment artifact.

### 9.3 Numerical execution

An independent scalar target-precision reference defines expected behavior.
The simulator uses a separately implemented optimized numerical library with:

- explicit format decode and encode;
- controlled FP32 and BF16 rounding;
- canonical reduction order;
- deterministic top-k and tie handling;
- exceptional-value and saturation status;
- exact mask, padding, scale, and state behavior; and
- scalar-versus-optimized differential tests for every kernel.

Host compiler flags, FMA contraction, vector width, thread scheduling, and host
endianness may not alter target bits.

### 9.4 SRAM, NoC, and engine timing

The timing model represents:

- command fetch, decode, issue, dependency wakeup, and retirement;
- engine initiation interval, pipeline occupancy, and completion;
- SRAM bank and port arbitration, latency, ECC, conflicts, and backpressure;
- DMA queues, descriptor fetch, bursts, gathers, scatters, and completion events;
- NoC links, routes, widths, credits, buffering, arbitration, and contention;
- barriers, reductions, routing decisions, and state commits;
- queue high-water marks, blocked reasons, deadlock watchdogs, and poison drain;
  and
- clock-domain crossings and fixed interface latencies where architecturally
  relevant.

Timing must be causal: removing a required command or memory response must prevent
completion or change the result, rather than merely decrement a counter.

### 9.5 HBM timing

The HBM model consumes real physical addresses and represents channels,
pseudo-channels, banks, rows, bursts, command timing, refresh, queue policy,
turnaround, outstanding requests, interleaving, and backpressure. A pinned,
qualified external DRAM timing engine may be integrated, but its version,
configuration, patches, and validation vectors become release inputs.

Published bandwidth alone is not an HBM simulator. The model must expose useful
payload bandwidth, protocol overhead, row behavior, queue occupancy, latency
distribution, and energy events.

### 9.6 Trace and observability

The simulator provides deterministic, filterable traces at:

- generation step;
- graph operation and kernel;
- command issue and retirement;
- HBM/SRAM/NoC transaction;
- tensor and state checkpoint;
- route/top-k/sparse-index decision;
- queue, stall, and resource occupancy; and
- error, poison, abort, and commit.

Full values may be replaced by cryptographic hashes at configured trace points.
A divergence tool locates the first mismatching operation, tensor, command,
memory range, or state generation.

### 9.7 Simulator scalability

Full Qwen and DeepSeek execution must not require all checkpoint, canonical, and
deployed bytes to reside in host RAM. The simulator uses verified memory mapping,
bounded streaming buffers, content-addressed shard access, and deterministic
parallel kernels. Parallelism may reduce wall-clock time but cannot alter target
ordering or simulated cycles.

Large release campaigns support checkpoint/restart with a checkpoint identity
covering simulator version, deployment hash, runtime request, architectural state,
memory state, pending events, and counter state.

## 10. Independent correctness oracles

Three paths remain separate:

1. **Official-model path.** The pinned upstream implementation or a reviewed
   faithful adapter produces source-semantics traces and official baseline
   outputs.
2. **Target-precision reference path.** An independent implementation applies
   OpenTallas numerical and state rules without compiler lowering or simulator
   algorithms.
3. **Compiler/simulator path.** The deployment compiler and artifact-only
   simulator execute the target machine.

The compiler/simulator must match the target-precision reference bit-for-bit at
architectural boundaries. The target-precision reference must match official
semantics under predeclared tensor tolerances and task-quality policy. For the
frozen greedy golden suite, token IDs and decoded text must match exactly. A
top-one token divergence is a failed workload even when a logit tolerance passes.

Golden prompts, expected outputs, tolerances, and quality datasets are frozen
before simulator results are inspected. Failing examples are retained rather than
removed from the suite.

## 11. End-to-end verification matrix

### 11.1 Progressive tests

| Level | Payload and dimensions | Execution | Required comparison |
|---|---|---|---|
| Fixture | Small redistributable values | Complete compiler and simulator path | Exact artifacts, state, values, failures, and counters |
| Operator | Target formats and representative shapes | Every scalar/vector/tensor/state kernel | Exhaustive boundaries and randomized target-reference differential |
| Full-dimension slice | Real checkpoint values, unreduced dimensions | Representative Qwen layer and all DeepSeek layer classes | Inputs, intermediate tensors, routes, indices, state, outputs, bytes, and cycles |
| Short full model | Complete real checkpoint | Prompt prefill plus at least 32 decode steps or expected EOS | Every layer checkpoint, logits, token IDs, state, and text |
| Qwen 8,000 | Complete Qwen checkpoint | Exact 8,000-token prompt plus decode | Bit-exact target results and exact golden tokens/text |
| DeepSeek 8,000 | Complete DeepSeek checkpoint | Exact 8,000-token prompt plus ordinary decode | Bit-exact target results, routing/state, and exact golden tokens/text |
| Long-context qualification | Complete checkpoint and declared state | 8,192 and later 32K/200K/1M profiles as applicable | Capacity, state, correctness, timing, and quality for each claimed context |
| Fault/degraded | Valid deployment plus injected faults | Representative commands and sessions | Containment, no bad commit, exact diagnostics, drain, and recovery |

### 11.2 Mandatory end-to-end acceptance

For every release golden run:

- tokenizer input and output token IDs match the pinned tokenizer;
- the simulator consumes only compiled artifacts;
- zero graph operations are unknown, skipped, or executed by a framework fallback;
- all checkpoint payload bytes have a declared deployment and execution role;
- prefill and every decode step complete through the accelerator command path;
- logits match the target reference exactly at the declared output boundary;
- selected token IDs and decoded text match the frozen golden result;
- KV, compressor, route, sparse-index, and session state hashes match;
- expected and observed tensor operations, HBM bytes, SRAM bytes, NoC traffic,
  stalls, and cycles reconcile with no unexplained difference;
- two clean executions produce identical architectural results and canonical
  reports; and
- task-quality regression thresholds pass on the frozen evaluation set.

### 11.3 Numerical acceptance policy

Bit equality is required between the simulator and target-precision reference.
Comparison with an upstream BF16/FP8 implementation may use operation-specific,
predeclared tolerances because upstream kernel reduction order can differ. Such
tolerance does not excuse a golden token mismatch.

Every saturation, corrected error, exceptional value, tie, and invalid masked
position is counted and checked. Any NaN, infinity, illegal scale, nonzero
padding, state race, or undeclared saturation fails according to the numeric
profile.

## 12. RTL and simulator correlation

The simulator is the full-model execution vehicle; RTL supplies implementation
correlation. Generated artifacts drive both.

RTL work proceeds only after the command ABI and software vertical slice are
stable. It covers:

- command decode, descriptors, queues, dependencies, and retirement;
- SRAM interfaces and representative bank conflicts;
- HBM request/response, tags, reordering, errors, and backpressure;
- tensor and vector kernels or qualified functional-macro boundaries;
- router/top-k and state prepare/commit;
- NoC flow control, barriers, reductions, poison, and recovery; and
- performance counters and trace checkpoints.

Representative complete Qwen layers and every structurally distinct DeepSeek
layer class execute through RTL or RTL/software co-simulation at full dimensions.
Per-command visible values, side effects, and deterministic control cycles match
the architectural simulator. Macro timing abstractions are separately identified
and characterized.

Full-model gate-level simulation is not required to establish the functional
model path, but a timing-only simulator cannot replace the representative RTL
correlation gate.

## 13. 130-nm implementation and calibration

### 13.1 Primary process methodology

One public 130-nm flow is selected as the primary digital comparison baseline
after a tool/library audit. SKY130A is the natural primary candidate for the
digital accelerator because of its existing repository integration. IHP SG13G2
may provide an independent methodology cross-check, but data from two PDKs must
not be mixed into one same-node result.

The primary flow characterizes:

- tensor and vector arithmetic;
- command/control, queue, NoC, and HBM-controller logic;
- SRAM macro or compiler views at declared sizes and aspect ratios;
- clocking assumptions and legal operating corners;
- placed-and-routed representative tiles and top-level hierarchy;
- dynamic activity from executed model traces;
- leakage, internal, switching, SRAM, and interconnect energy; and
- timing at declared process, voltage, temperature, and extraction corner.

### 13.2 HBM boundary

HBM DRAM dies and a production high-speed PHY are not synthesized as 130-nm
standard-cell logic. The comparison reports:

- 130-nm on-chip controller and digital interface logic;
- separately sourced PHY area, latency, power, and package assumptions;
- external HBM stack capacity, timing, refresh, and energy;
- package/interposer resources; and
- on-chip area and energy separately from external memory/package terms.

This is especially important because the ROM architecture also uses mutable
HBM/SRAM state. The two designs share identical HBM model sources and interface
assumptions where their functions overlap; the tensor accelerator additionally
pays its measured weight traffic.

### 13.3 Characterization feedback loop

Physical implementation and compilation form a controlled loop:

~~~text
candidate architecture
  -> synthesize, place, route, and characterize at 130 nm
  -> publish versioned hardware capabilities and cost tables
  -> recompile both complete models
  -> execute data-bearing cycle simulation
  -> identify bottlenecks and violated bounds
  -> version the architecture if needed
  -> repeat until capability, compiler, simulator, and physical evidence agree
~~~

Hand-entered peak throughput does not close this loop. The frozen release
capability file names the exact implementation artifacts from which every engine
latency, initiation interval, SRAM port rule, NoC width, clock, and energy event
was obtained.

## 14. ROM versus HBM/SRAM comparison protocol

The comparison uses:

- the same pinned checkpoint and tokenizer;
- the same prompt token IDs and generation policy;
- the same semantic graph and target numerical profile;
- the same context, batch, concurrency, stop boundary, and output boundary;
- the same process node, PVT corner, evidence classification, and external HBM
  source;
- independently legal backend-specific physical plans;
- actual generated schedules and execution counters;
- the same quality and correctness gates; and
- common report definitions.

It reports at least:

- prefill latency and throughput;
- time to first token and inter-token latency;
- tokens per second at declared concurrency;
- joules per prompt and joules per generated token;
- on-chip area, SRAM area, controller/compute area, and external memory/package
  resources separately;
- HBM useful and transferred bytes, bandwidth, latency, row behavior, and energy;
- SRAM reads/writes, conflicts, occupancy, and energy;
- compute, vector, routing, NoC, memory, and synchronization utilization;
- queue and stall attribution;
- peak and average power plus thermal assumptions;
- capacity and failure margin; and
- correctness, quality, unsupported scope, and evidence class.

Two clock views are retained: a same-frequency architecture-attribution view and
an independently closed-frequency view. Neither may borrow the other design's
timing closure.

The tensor accelerator is not described as a clean-room implementation of any
branded general-purpose processor. Measured NVIDIA hardware remains a separate
external product comparator under its own governed methodology.

## 15. Execution phases

The critical path is the shortest evidence-producing route to the requested
comparison:

~~~text
shared semantics and numeric contracts
  -> causal real-checkpoint compiler/simulator slice
  -> connected Qwen layer
  -> full Qwen artifact-only execution, exact logits, and short generation
  -> Qwen 8,000-token common-simulator gate
  -> DeepSeek distinct layer classes and ordinary generation
  -> representative RTL correlation
  -> 130-nm characterization and recompilation
  -> governed ROM-versus-HBM/SRAM comparison
~~~

Qwen closes first because it exercises the complete dense inference and state
path without making DeepSeek's data-dependent MoE and sparse control part of the
initial compiler/simulator bring-up. This ordering does not make Qwen-specific
assumptions architectural: every ABI and hardware decision is checked against
the declared union of both models before it freezes. DeepSeek semantic/reference
work, independent checker development, simulator scalability work, and early
physical feasibility experiments may proceed in parallel when they do not alter
the critical-path contracts.

Each phase below is an outcome-bearing work package. Its exit gate is the
decision point for entering dependent work; the numbered progression inside a
phase is diagnostic staging, not a substitute for the exit evidence.

### Phase 0 — concurrent-session handoff and baseline

The Qwen and DeepSeek ROM sessions finish their current model-specific
semantic/reference/deployment milestones, run their tests, and create scoped
commits. Active checkpoint downloads continue. The sessions do not redesign the
common production IR, generic command ISA, accelerator capability schema, or
HBM/SRAM backend.

The integration owner inventories both commits, generated manifests, known
answers, open limitations, and overlapping documents. Work begins in an isolated
worktree from a reconciled baseline.

**Exit gate:** TA-GOV-0. No live writer owns a shared implementation path, every
dirty artifact is classified, and both model frontends have a stable handoff.

### Phase 1 — workload, correctness, and capability freeze

Architecture, compiler, model, runtime, and verification owners review and freeze
the system boundary in Sections 3 and 4. They produce machine-readable workload
manifests for Qwen short, Qwen 8,000, DeepSeek short, and DeepSeek 8,000 profiles;
numeric acceptance rules; hardware field and capacity bounds; and end-to-end
golden-generation procedures.

Candidate HBM channel/stack counts, SRAM capacities, tensor tile shapes, engine
mixes, and package topology are screened against exact model bytes and operation
shapes. Values remain candidates until a legal compiler plan and physical
characterization agree.

**Exit gate:** every required workload, output, context definition, numeric rule,
and architectural bound is explicit; no unresolved term can change what
“correct decoding” means.

### Phase 2 — neutral semantics and independent references

The production Model Graph IR and Tensor Kernel IR schemas are introduced
additively. Qwen and DeepSeek adapters export into the common graph. Independent
target-precision references cover every operation and state transition, beginning
with small known answers and progressing to real checkpoint tensors.

Coverage tooling rejects unknown operations, implicit broadcasts, unbound state,
undefined rounding, and backend-specific semantic nodes.

**Exit gate:** TA-SEM-1. Both ordinary-path graphs have zero unknown operations
and every node has an independent semantic owner, numeric contract, lowering
class, and known-answer strategy.

### Phase 3 — tensor-accelerator architecture and ABI freeze

The command processor, tensor/vector/selection engines, SRAM hierarchy, HBM
frontend, NoC, state machinery, counters, errors, and host ABI are specified at
bit and cycle-contract level. Reduced fixtures explore alternatives, but the
selected v1 capability supports the union of the two model contracts.

The architecture review explicitly tests DeepSeek data-dependent experts and
sparse indices; a design that only supports a compile-time dense schedule does
not pass.

**Exit gate:** all externally visible records, engine contracts, numeric modes,
memory rules, dynamic bounds, errors, and counters are versioned and
requirement-traced.

### Phase 4 — deterministic HBM/SRAM compiler vertical slice

The first vertical slice lowers a small model-shaped fixture through the complete
artifact chain. It emits HBM images, SRAM plans, DMA/kernel/state programs,
manifests, expected counters, and independent reports. Corruption and illegal
capacity cases fail closed.

The slice is then replaced by one real full-dimension Qwen block and
representative full-dimension DeepSeek layer classes using actual checkpoint
values.

**Exit gate:** TA-COMP-2 for the declared slices. Every logical byte reconstructs,
every allocation and command is legal, and two clean builds are byte-identical.

### Phase 5 — artifact-driven simulator vertical slice

Functional, data-bearing timing, and replay modes execute the same compiled
fixture. Optimized arithmetic is differentially checked against the scalar
reference. HBM, SRAM, NoC, queues, dependencies, state commits, errors, traces,
and counters are causal and reconciled.

Real full-dimension Qwen and DeepSeek slices then execute from deployment
artifacts, with divergence localization at operation, command, and memory levels.

**Exit gate:** TA-SIM-3 for the declared slices. The simulator has no framework
fallback, and completion depends on correct data and state execution.

### Phase 6 — Qwen3-8B full-model closure

Qwen is the first complete-model bring-up because its dense BF16/GQA path tests
the neutral graph, vocabulary projection, HBM streaming, SRAM tiling, KV state,
and decode loop without MoE control complexity.

The progression is:

1. short prompt, one generated token, every layer traced;
2. short prompt, at least 32 generated tokens or expected EOS;
3. 8,000-token prefill and first decode token;
4. 8,000-token prefill and the frozen generation length;
5. 8,192-token boundary and capacity stress; and
6. seeded sampling only after greedy closure.

**Exit gate:** TA-QWEN-4. The actual checkpoint produces exact target logits,
tokens, state, and text in artifact-driven data-bearing simulation, with complete
counter reconciliation.

### Phase 7 — DeepSeek-V4 full-model closure

DeepSeek begins with full-dimension layer-class slices covering compression
ratios, dense/shared/routed experts, top-k, sparse attention, compressor state,
mHC, and all numerical formats. It then advances to the complete checkpoint and
ordinary target-only generation loop.

The progression is:

1. every distinct layer class with actual payloads;
2. complete model, one decode step from a valid state;
3. complete short prefill and at least 32 decode steps or expected EOS;
4. complete 8,000-token prefill and frozen generation;
5. longer context profiles only after their state/capacity and runtime costs are
   legal; and
6. speculative execution as a separately versioned extension.

**Exit gate:** TA-DSV4-5. All ordinary-path operations execute, routes and sparse
indices match, state commits match, and final tokens/text pass the frozen
acceptance suite.

### Phase 8 — RTL correlation and robustness closure

Generated programs drive RTL blocks and co-simulation. Static checks, formal
properties, constrained-random stalls, HBM interleaving, fault injection, ECC,
abort/drain, reset, and degraded-resource tests cover the accelerator-specific
requirements. Simulator cycles and counters are correlated at command and
representative layer scope.

**Exit gate:** TA-RTL-6 plus zero open severity-one or severity-two defects, closed
must-bin coverage, reviewed waivers, and retained reproducible campaigns.

### Phase 9 — 130-nm calibration and architecture convergence

The selected public-PDK flow characterizes engines, SRAM, control, and
interconnect. Executed Qwen and DeepSeek activity drives power estimation.
Characterized capabilities feed recompilation and simulation until physical,
compiler, and timing assumptions converge.

**Exit gate:** TA-PHY-7. Every reported on-chip cycle and energy term traces to a
characterized element or is visibly labeled external/assumed.

### Phase 10 — governed comparison and release

Both backends compile the same frozen workload manifests. All correctness gates
run before performance comparison. Reports expose raw counters, attribution,
uncertainty, limitations, and separate on-chip/external-memory terms.

**Exit gate:** TA-CMP-8. A second clean release build and execution reproduce
canonical artifacts and architectural results. Only evidence-supported claims are
promoted.

## 16. CI, regression, and release policy

The campaign is tiered:

- per-commit CI uses redistributable fixtures, schemas, rejection tests, operator
  known answers, compiler determinism, and short simulator programs;
- nightly CI adds randomized kernels, memory contention, long command streams,
  state rollback, and simulator replay;
- scheduled checkpoint CI runs real Qwen layers and full short-model generation;
- controlled large-artifact campaigns run Qwen 8,000 and DeepSeek slices/full
  model from locally pinned checkpoints; and
- release CI runs both independent clean builds, end-to-end goldens, RTL
  correlation, and comparison generation.

No skipped test is interpreted as a pass. Large-payload gates report “not run”
until their exact local checkpoint and compute prerequisites are present.

A release archive contains:

- source, compiler, simulator, RTL, schema, and specification commits;
- clean-tree and tool/environment records;
- input and output hashes;
- capabilities, workload manifests, numeric profiles, and ABI versions;
- deployment and known-answer manifests;
- compiler/checker, simulator, RTL, physical, and quality reports;
- raw counters and trace checkpoints;
- coverage, bug, waiver, and evidence-class ledgers; and
- exact reproduction commands.

## 17. Ownership and concurrency

One integration owner controls:

- the production-neutral IRs;
- generic compiler schemas and artifact identity;
- the tensor-accelerator capability and command ABI;
- the HBM/SRAM backend;
- the common simulator architecture; and
- cross-model release gates.

The Qwen and DeepSeek owners control their model adapters, official-source
evidence, independent references, golden traces, and model-specific tests. After
the shared schemas freeze, they add thin exporters and review semantic fidelity;
they do not fork the common IR.

Independent checkers remain separate modules and receive review from someone
other than the corresponding generator owner whenever staffing permits.

Large campaigns own unique output directories. Source trees and canonical result
paths are never mutated by a running campaign. Promotion is atomic after
validation. Checkpoint downloads and generated multi-gigabyte artifacts remain
outside Git.

The active Qwen and DeepSeek ROM sessions are not frozen merely to start the
tensor-accelerator program. They continue on model-owned source adapters,
semantics, independent references, golden traces, and ROM-specific lowering.
They must not edit the production-neutral IR, generic accelerator ABI,
HBM/SRAM planner, or common simulator while the integration owner controls those
surfaces. The integration owner consumes only coherent commits, never dirty
working-tree files. A handoff records the source commit, generated artifact
identities, tests, known limitations, and semantic coverage delta.

If two sessions need the same shared contract, implementation pauses at that
boundary long enough to review and version the contract; neither session creates
a private incompatible copy. This is a narrow contract freeze, not a freeze of
the model work. Conflicting or incomplete handoffs remain quarantined until they
can be replayed from a clean baseline.

## 18. Principal risks and redesign triggers

| Risk | Required mitigation | Redesign or stop trigger |
|---|---|---|
| Backend-specific semantics leak into the common IR | Neutrality tests and separate physical plans | Model graph requires ROM or HBM operations to express semantics |
| Exact simulation is too slow for full models | Native checked kernels, streaming, deterministic parallelism, checkpoint/restart | End-to-end data-bearing execution cannot be completed or reproduced |
| DeepSeek weights/state exceed the package | Exact compiler capacity proof and explicit sharding study | Required profile depends on undeclared host paging |
| Dynamic experts defeat static scheduling | Runtime descriptors, bounded queues, actual-route simulation | No deadlock-free bounded dispatch plan exists |
| Target arithmetic changes model output | Independent bit reference and predeclared golden/quality suite | Frozen quality or token gates fail |
| SRAM banking or HBM traffic erases utilization | Physical allocator and causal cycle simulation | Conservative implementation-derived bound is not competitive |
| 130-nm frequency, area, or power is infeasible | Early P&R and activity-driven feedback | Required capability cannot close declared physical limits |
| Public HBM/PHY data is insufficient | Separate external assumptions and sensitivity bounds | A result depends on untraceable PHY or package values |
| Compiler and checker share the same defect | Separate implementations, adversarial fixtures, inverse proofs | Independence audit finds shared expected-result logic |
| Concurrent sessions overwrite shared work | Scoped commits, reserved surfaces, isolated worktree | Baseline cannot be reproduced or attributed |

A failing gate is preserved as evidence. Architecture parameters are not relaxed
after observing a failure without a versioned change record and rerun of affected
goldens.

## 19. Current program position and execution horizon

### 19.1 Status at this reconciliation

The real projection, embedding-through-RMSNorm, connected Q/K/V-preparation,
attention/transactional-KV, post-attention/MLP, and connected full-width layer
horizons are complete through `ta-integration@c07331b`; plan reconciliation is
committed through `1f4e52f`, and bounded final-output-family evidence is admitted
at `2222f76`. Complete Qwen neutral-semantic coverage closes narrowly at
`74c0d59`, and complete physical compilation plus reconstruction close at
`324f48d`. Their exact evidence boundaries are recorded in Sections 1.2 through
1.11 and below. The program is not complete: Qwen complete-model execution,
decoding, DeepSeek semantic union, timing, RTL, physical, and comparison gates
remain open.

| Program decision surface | Current state | Consequence |
|---|---|---|
| Integration governance | `324f48d` is the current admitted implementation head; concurrent Qwen/DeepSeek files on `main` remain dirty or untracked | Only committed, reproduced handoffs become release evidence. Full-model simulator work remains isolated and may consume committed or immutable source artifacts without absorbing unrelated concurrent-session state |
| Neutral graph semantics | Model Graph IR v2 and a real Qwen graph exist; committed DeepSeek references continue to accumulate | The semantic graph boundary is retained, but `TA-SEM-1` remains open until both complete ordinary graphs have zero unknown operations |
| Neutral kernel semantics | **QW-FM1 closed at `74c0d59`.** One retained dynamic-shape neutral artifact maps all 617 Qwen operations and 36 state resources exactly once, including final output and terminal commit, and an independent checker reconstructs all source, numeric, tensor, state, and qualification bindings without backend leakage | Preserve the admitted Qwen semantic artifact through physical execution; separately close the remaining DeepSeek operation/state union before `TA-SEM-1` |
| Target arithmetic | Connected actual-checkpoint execution matches all declared layer intermediates, `hidden.1`, and committed KV state. The authentic-weight final-output fixture matches independent references but deliberately consumes `hidden.1`, not `hidden.36` | Connect the admitted contracts to the complete 36-layer output and qualify every remaining DeepSeek contract; retain first-divergence evidence across every assembled layer |
| Command and capability ABI | ABI 2.5 and capability V6 admit bounded indexed SRAM selection with a strict schema and preserve older minor decoding; `324f48d` independently derives the complete physical ABI 2.5 program | Execute ABI 2.5 through artifact-only simulation. Routing, remaining vector operations, synchronization, timing, 8,192-plus context support, and the final hardware capability remain open |
| Compiler and checker | **QW-FM1 closed at `74c0d59`; QW-FM2/QW-FM3 closed at `324f48d`.** Complete Qwen neutral lowering, streamed full-model HBM layout, SRAM lifetime allocation, command lowering, and inverse reconstruction are deterministic and retained | Preserve those artifacts unchanged while implementing the separate common full-model simulator; do not relabel compilation as execution |
| Functional simulation | **Connected-layer horizon closed at `c07331b`.** One 23,570-command deployment executes artifact-only with exact values, all 72 counters, state, and causal command dependence | Execute the complete Qwen model for one exact token decision before short-generation and long-context gates |
| Timing and physical evidence | No clock, latency, HBM timing, bandwidth, or energy value is qualified | No committed slice result may be used for a performance, power, or 130-nm comparison claim |
| End-to-end execution | The common simulator has executed one complete layer but has not executed all 36 layers, produced final logits, or generated a token | `TA-QWEN-4` and `TA-DSV4-5` remain open; the Qwen-specific service result is reference evidence only |

### 19.2 Closed horizon: one complete connected Qwen layer

This controlled outcome closed at `ta-integration@c07331b`: one complete,
full-width Qwen layer executes from the actual checkpoint through the common
compiler, independent checker, and artifact-only simulator. The path begins
with an actual token embedding and ends after the layer's final residual update,
including the layer's transactional KV effects. It is vertical and connected;
the earlier collection of disconnected operator tests did not satisfy it.

The pinned official Qwen implementation remains the source-semantics anchor. Its
reviewed source hash is
`704c914530530a1acb0b443add1f520404e3ac2c28c0ab7e16f80f86cfe8ccb2`.
The source-anchored full-width layer-input RMSNorm profile,
`qwen3_rmsnorm_fp32_bf16_v1`, is now committed and independently qualified. Its
rounding, reduction order, epsilon placement, conversion boundaries, and
exceptional-value rules are frozen for the closed slice.

The closed Q/K/V stage starts with token ID zero, consumes the committed full-width
attention-normalized activation, applies the actual layer-0 Q, K, and V
projections, performs per-head Q and K RMSNorm, and applies position-7,999 RoPE.
The shapes are 32 query heads and eight KV heads at head dimension 128. Exact
retained payload hashes are:

- Q raw:
  `b900b79fd38ff6a9bff470ac27e9672b0c3724b84f6a1f7e964c2ec0918ea0ff`;
- K raw:
  `dd690fbd9886a0af94cc6b2477ef5bfcc84fe66cac66f345f2ec654a83b28403`;
- V:
  `b07011da7a3d58dcccceb91e596ceebc2084ab3c2fc9d0b6a9a8704e91ef8dc5`;
- Q normalized:
  `bf01d5254a7616bfffac6f789fbae1b94c68c5201944c8faf297b803987a401c`;
- K normalized:
  `71af5033456b74d137d248f4019f848aedb8c8f758f952612082ad48d50f6a66`;
- Q rotary:
  `a846335c825cf9fb06213220acf157c6a805376b1324a7cec09d6fa4621e718d`;
  and
- K rotary:
  `ce427ae533331720b9b58dde633e3ca352fa9fe0d3dd09d8cab222b799963858`.

Those values match the independently pinned source path, including a frozen
8,000-position coefficient table and explicitly resolved near-midpoint
trigonometric cases. ABI 2.2 adds a bounded generic `ROPE_BF16` command while
preserving the 2.0 and 2.1 decode paths. The retained Q/K/V HBM image, 16-bank
SRAM plan, command program, independent reconstruction, causal execution report,
strict schemas, corruption and compatibility campaign, two clean reproductions,
and scoped commit agree.
The capability remains explicitly uncharacterized and enables no timing, energy,
RTL, or 130-nm claim.

The attention and transactional-KV stage is now closed at `d353f9d`. It begins
with the authentic rotary Q, rotary K, and V values and a bounded nonempty causal
history, makes prepared state visible only within the transaction, executes GQA
score/mask/softmax/value aggregation from artifact-caused memory reads, and
commits only after successful attention. Missing work, malformed or stale state,
and abort scenarios either fail or preserve the prior committed generation. The
neutral Kernel IR, HBM/SRAM plan, generic commands, independent checker,
artifact-only simulator, backward ABI replay, and two clean reproductions agree.

The downstream stage is closed at `7433b24` for authentic layer-0 graph nodes
`node.0010` through `node.0017`: attention output projection, the first BF16
residual add, post-attention RMSNorm, gate and up projections, SiLU-multiply,
down projection, and the final BF16 residual producing `hidden.1`. Commit
`2317064` establishes the independent scalar references, optimized
implementations, materialized BF16 SiLU boundary, and authentic qualification.
Commit `7433b24` adds generic neutral `ADD` and `SILU_MUL` records, physical
lowering, ABI 2.4 commands, independent inverse checking, and causal
artifact-only execution.

The closed qualification uses the retained attention output, the authentic
`hidden.0` residual input, and the following layer-0 payloads:

| Payload | Shape | SHA-256 |
|---|---:|---|
| Attention output projection | `[4096, 4096]` | `d6fec091373ead7a102c480d4642a9b135e9e2cf0d0c289e0425967c96877ac2` |
| Post-attention RMSNorm | `[4096]` | `3df17c58e1832b24111c91cb19088b06f816de21702ce58acb514c91568cde5d` |
| Gate projection | `[12288, 4096]` | `1f9e6bddfbbfff53f82b684776dd1b36643277b72d40f70abcd287e02ab7ea9e` |
| Up projection | `[12288, 4096]` | `ac3f743828a20694255953a4290079eda84f38e48e608a24731fb0510780db35` |
| Down projection | `[4096, 12288]` | `56ca545862b9b22d1feb9e00433b6cc8b5c22787c215b911902d3d40ce1e8096` |

The qualification's deterministic report identity is
`94cc82dd113e16f05795c0de36930800701014e37e08267ce355ecfba3cfeea9`.
Its generator accounts for 167,772,160 projection multiplications and the same
number of ordered additions, 8,192 residual additions, and 12,288 each of SiLU
exponentials, denominator additions, divisions, SiLU multiplications, and
gate-up multiplications, with no observed saturation. The independent
official-source replay differs at a small number of projection-derived BF16
elements because the accelerator intentionally uses the frozen deterministic
ordered-matrix contract; the evidence is therefore classified
`qualified_deterministic_target_adaptation`, not falsely represented as an
official full-model layer trace. The strict schema, retained artifact,
byte-identical regeneration, qualification tests, adversarial rejection, and
complete compiler/runtime regression close this numerical subgate at `2317064`.

The ABI extension is admitted as ABI 2.4 with strict ABI 2.0 through 2.3 replay,
generic bounded semantics, complete capability/schema validation, and authentic
downstream execution. The closed ABI 2.3 attention deployment remains
byte-for-byte frozen. Commit `c07331b` composes the downstream slice with the
earlier embedding-through-attention path into one generated complete-layer
deployment. Disconnected retained activations remain useful qualification
fixtures but did not contribute inputs to the connected execution.

The horizon is divided by architectural evidence, not by file ownership:

| Evidence stage | Architectural question answered | Required closure evidence |
|---|---|---|
| Layer input and RMSNorm — **closed slice evidence** | Can the neutral graph express lookup and normalization without backend leakage, and can a bounded vector/reduction path consume legal HBM/SRAM placement? | Closed at `0771d84` with independent scalar oracle, separate optimized implementation, actual full-width checkpoint vector, strict kernel/physical artifacts, corruption tests, causal simulation, exact output/counter match, broad regression, fresh-directory reproduction, and strict ABI 2.0 replay |
| Q/K/V preparation — **closed slice evidence** | Can the qualified segmented matrix path compose with Q/K normalization and position-dependent RoPE while preserving shapes, head grouping, and numeric boundaries? | Closed at `f94384c` with actual full-dimension hashes, neutral kernel composition, exact 16-bank allocation, complete HBM roles, deterministic commands, independent reconstruction, causal execution, strict schemas, adversarial rejection, exact counters, retained reports, two clean reproductions, and strict ABI 2.0/2.1 replay |
| Attention and KV transaction — **closed slice evidence** | Can one hardware path execute causal GQA, mask, softmax, value aggregation, and prepare/commit state without a host or framework fallback? | Closed at `d353f9d` with authentic Q/K/V, nonempty history, exact intermediates and state, neutral kernel records, legal HBM/SRAM plans, independent reconstruction, prepare/commit/abort and corruption coverage, bounded resources, full command causality, rollback, backward ABI replay, and two clean byte-identical builds/runs |
| Attention output and MLP — **closed slice evidence** | Can the path complete output projection, residuals, post-attention RMSNorm, gate/up projections, SiLU-multiply, down projection, and final residual? | Closed at `7433b24` with authentic payloads, generic neutral records, ABI 2.4 commands, a 13-bank SRAM plan, complete tiled-HBM reconstruction, exact 20,488-command causal execution, all intermediate/final hashes, 37 counters, zero saturation, strict schemas, corruption rejection, two clean reproductions, full regression, and ABI 2.0–2.3 replay |
| Integrated layer program — **closed connected evidence** | Does one generated deployment—not a handwritten test sequence—execute the entire layer with no unsupported operation or hidden computation? | Closed at `c07331b` with one 19-kernel neutral IR, one 422,765,184-byte HBM image, 26 SRAM regions across 16 banks, 23,570 causal ABI 2.4 commands, exact `hidden.1` and KV state, all 72 counters reconciled, strict schemas and adversarial rejection, full regression, and two byte-identical clean builds/runs |

Each newly admitted kernel receives all seven parts of the production contract at
the same time: source semantics, target numerics, neutral kernel representation,
physical lowering, command semantics, independent checking, and causal simulator
execution. The compiler may reuse the qualified matrix primitive, but it may not
call a whole-layer or framework shortcut. New command families remain bounded and
generic; an instruction whose semantics names Qwen is rejected at architecture
review.

The development capability is versioned whenever a new engine, format, field
bound, SRAM rule, or state primitive becomes visible. Such a version remains
uncharacterized until RTL and 130-nm evidence supplies its costs. DeepSeek's
declared type, routing, sparse-index, expert, and state requirements are checked
against every shared field-width and queue-bound decision even though Qwen is the
first data-bearing layer bring-up. This prevents a Qwen-only ABI from becoming a
premature hardware freeze.

**Horizon exit decision:** satisfied at `c07331b`. The actual layer deployment is
deterministic, independently reconstructable, fully causal, artifact-only,
bit-exact at all declared boundaries, and complete in state and counter
accounting. That closure authorized complete-model Qwen assembly without
relabeling the layer result as `TA-QWEN-4`; QW-FM2 and QW-FM3 have since closed,
so the active work is QW-FM4 artifact-only execution.

### 19.3 Active horizon: full Qwen artifact-only execution and one-step logits

The active outcome is one complete Qwen forward execution from an actual short
prompt to exact final-position logits and the frozen host greedy-token decision.
The entry evidence is the connected layer at `c07331b`, final-output-family
qualification at `2222f76`, complete neutral-semantic bundle at `74c0d59`, and
the deterministic full-model deployment plus independent physical reconstruction
at `324f48d`; their numeric contracts, checker independence, and causal simulator
rules remain unchanged. The full-model result must execute the real 617-operation
Model Graph IR, all 36 transactional KV resources, and actual checkpoint
payloads. Repeating a retained layer result or injecting an activation between
layers is not execution.

The admitted deployment applies the neutral layer pattern to all 36 distinct
layer instances, then lowers `node.0613` final RMSNorm, `node.0614`
`LAST_TOKEN_SELECT`, `node.0615` vocabulary `MATMUL`, and the terminal
36-resource `STATE_COMMIT`. `LAST_TOKEN_SELECT` selects the final sequence
position inside model-forward execution; greedy argmax remains the frozen host
policy at the system boundary in Section 3.1. Artifact-only execution must use
those existing generic kernels and exact command ranges. Any necessary IR or ABI
extension discovered during execution must be bounded, model-neutral, checked
against the DeepSeek capability union, and pass strict backward replay before
admission.

The active horizon is organized as four dependent evidence work packages:

| Work package | Architectural outcome | Required artifact and evidence | Exit condition |
|---|---|---|---|
| QW-FM1 — semantic and numeric closure — **closed at `74c0d59`** | Every one of the 617 graph operations and all 36 state resources has one supported neutral lowering and one frozen numeric contract | Retained coverage ID `00dbdf8b...b106`, Kernel IR ID `270b7609...e050`, and independent check ID `280ee81a...2215`; full-dimensional final-output qualification; exact source/checkpoint/capability bindings; zero backend-specific fields | Satisfied narrowly for Qwen semantics and numerics; no physical-plan or execution claim follows |
| QW-FM2 — deterministic full-model compilation — **closed at `324f48d`** | One deployment represents embedding, 36 distinct layers, final output, and terminal state effects on the existing hardware/ABI | Retained build ID `3460d88c...290f`, physical-plan ID `ba1d9546...09c3`, 17 content-addressed HBM shards, 18-slot SRAM plan, 924,386-command program, capacity certificate, source lock, request, and manifest | Satisfied at the physical-artifact boundary; two authentic clean builds are byte-identical and no checkpoint tree was copied |
| QW-FM3 — independent reconstruction and adversarial closure — **closed at `324f48d`** | A separately implemented checker can prove the deployment without trusting compiler allocation, scheduling, lowering, or expected-result code | Retained independent-check ID `a2de7229...8a15`; separate graph walk, checkpoint reread, inverse HBM reconstruction, SRAM lifetime/bank proof, 36-resource transaction proof, exact command derivation, postpublication audit, and adversarial rejection | Satisfied for physical reconstruction; the checker imports neither the generator nor its RoPE-table generator and fresh audit reproduces the retained identity |
| QW-FM4 — artifact-only one-step execution | The common simulator executes the complete model and returns exact logits, state, and one greedy token | One actual short-prompt request; per-layer first-divergence checkpoints; final-normalization and full-logit hashes; selected token; all 36 prepared and committed KV states; exact operation, command, byte, arithmetic, and state counters; two independent causal runs | Target-reference layer boundaries, final logits, token, and state match exactly; commit occurs only after successful logits; no framework, service, compiler-builder, checker, scalar-oracle, or precomputed-activation fallback is imported |

#### 19.3.1 Full-model scale envelope and construction policy

The current Qwen graph has 617 operations, 1,053 tensors, and 36 transactional
KV resources. QW-FM2 establishes exact counts of 16,381,470,720 immutable
weight bytes and 924,386 commands for one complete forward schedule. The
vocabulary projection contributes 75,968 DMA and matrix-tile commands; the 36
layer schedules contribute the majority of the remainder. These are admitted
compiler and independent-checker results, not planning estimates. They fit
below the current development limits of 256 GiB
external HBM and 16,777,216 commands, but numerical headroom does not itself
prove placement, liveness, or execution.

The deterministic builder streams authenticated tensors directly from the one
pinned checkpoint into a preallocated, memory-mapped, content-addressed HBM
image or set of shards. It does not materialize a multi-gigabyte Python byte
object, duplicate the checkpoint tree, or make canonical identity depend on
host paths. Sparse backing is legal only when hole contents are normatively zero,
the manifest records every extent, and the independent checker reconstructs and
hashes the logical image. Build memory, file-descriptor, temporary-disk, and
wall-clock high-water marks are release evidence rather than undocumented host
requirements.

The SRAM planner reuses the 16 one-MiB banks across proven non-overlapping
lifetimes. Layer scratch does not scale by 36; hidden-state storage alternates
between checked producer and consumer regions, while final-output selection is
performed from the live tile containing the logical final row. Immutable weights
and persistent KV/state remain in declared external-HBM regions; HBM remains
outside the synthesized 130-nm boundary. Capacity reporting includes the
complete checkpoint, alignment and padding, program and metadata, all 36 KV
resources at the declared context, allocator reserve, and integrity overhead.
The plan rejects an allocator that relies on implicit activation retention,
undeclared spill, whole-sequence SRAM residency, or host paging.

Compilation emits incrementally checkable regions and command ranges so a
failure can be localized without accepting a partially valid deployment. The
manifest nevertheless binds them as one model-forward transaction. Per-layer KV
updates remain prepared and private until the vocabulary logits have executed;
one terminal 36-resource `STATE_COMMIT` occurs only after successful final-output
work. A failed build, malformed range, simulator exception, watchdog, or missing
logit command cannot expose a partially advanced model state.

#### 19.3.2 QW-FM decision sequence

QW-FM1 closed at `74c0d59`. QW-FM2 and QW-FM3 closed at `324f48d`; the retained
physical deployment and separately implemented checker now map all 617
operations, 399 weights, and 36 state resources into exact HBM, SRAM, and ABI
artifacts. This decision advances the active work to QW-FM4 without implying
model execution.

Full-model construction and the independent physical checker are developed
against the same artifact schemas but separate algorithms.
The compiler owns forward lowering, allocation, and schedule generation. The
checker owns inverse reconstruction, graph-effect accounting, range/lifetime
proofs, and command derivation. Their agreement admits the deployment for
artifact-only execution; it is not replaced by generator self-validation.

One-step execution then advances through diagnostic boundaries—embedding, every
layer output, every prepared state, final normalization, selected row, complete
logits, and token decision—without injecting any of those values. The first
divergence stops promotion and remains a retained diagnostic. Only an exact
complete one-step result authorizes the 32-step decode campaign, and only that
campaign plus measured simulator feasibility authorizes the exact 8,000-token
gate. The separate 8,192 boundary is run after, and is never substituted for,
the mandatory 8,000-token workload.

The horizon exit is narrower than `TA-QWEN-4`: it closes when QW-FM1 through
QW-FM4 have coherent retained evidence for one exact token decision. It does not
close short generation, the exactly 8,000-token fixture, timing, RTL, physical
characterization, DeepSeek, or the governed comparison. After that exit, the
release route preserves the following ordered decisions:

| Decision point | Execution scope | Evidence required to proceed |
|---|---|---|
| Full model, one step | Short actual prompt, full prefill, one generated-token decision | Every layer/state checkpoint matches; no payload or operation is unassigned; final logits and selected token are exact |
| Short generation | Same complete model, at least 32 greedy decode steps or expected earlier EOS | Per-step logits, tokens, KV generations, stop behavior, decoded text, and counters match the frozen target reference |
| Long prefill readiness | Representative growing contexts plus checkpoint/restart | Simulator wall-clock and host-memory measurements show the data-bearing run is operationally feasible without changing architectural ordering or results |
| Mandatory Qwen gate | Exactly 8,000 resident prompt tokens followed by the frozen decode length | Common-simulator artifact-only execution matches exact target logits, state, token IDs, and text and reconciles all operations, bytes, stalls, cycles, and state |
| Capacity boundary | Separate 8,192-token fixture | Correct capacity and boundary behavior is reported separately and never substituted for the 8,000-token acceptance fixture |

Optimized host kernels, deterministic parallelism, memory mapping, streaming, and
checkpoint/restart may reduce wall-clock cost. A model-specific service call,
whole-model shortcut, precomputed activation injection, or timing-only replay may
not close correctness. If feasibility measurements show the 8,000-token
data-bearing run is too slow, the simulator implementation is optimized and
revalidated; the acceptance boundary is not weakened.

### 19.4 DeepSeek integration lane

DeepSeek ordinary target-only semantics continue in parallel as committed,
model-owned reference work. Coherent source locks, graph exports, numeric
contracts, known answers, and coverage reports are integrated at reviewed
handoffs. Dirty working-tree implementations are never copied. DSpark and
speculative execution remain outside the first DeepSeek deployment profile.

Before the complete command ABI freezes, a capability-union review proves that
the shared fields and bounded engine families can represent DeepSeek FP8,
MXFP4/E8M0, routing, expert dispatch, sparse-index, attention, compressor, and
transactional-state requirements. This review does not claim those paths are
implemented. After Qwen short full-model generation is stable, actual DeepSeek
payloads enter the common path one structurally distinct ordinary layer class at
a time, followed by complete short generation and the declared 8,000-token
profile.

### 19.5 Failure handling and redesign rules for the horizon

The following results cause a versioned redesign rather than a waiver hidden in
the implementation:

- the RMSNorm or later kernel cannot reproduce its frozen target contract at
  full width;
- the Kernel IR needs a backend address, SRAM bank, ROM lookup, or model-specific
  operation to express mathematical semantics;
- a Qwen-oriented field or queue bound cannot represent the declared DeepSeek
  union;
- removing a required command, memory response, or state commit does not prevent
  completion or affect the architectural result;
- the independent checker must import compiler allocation, scheduling, lowering,
  or expected-result code to validate a deployment;
- the simulator requires framework computation or uncompiled intermediate data;
- active checkpoint execution requires an undeclared host-paging path or another
  duplicate checkpoint copy;
- cycle or energy claims require a value absent from the frozen characterized
  capability; or
- a ROM-versus-HBM/SRAM result changes model, arithmetic, workload, process,
  external-memory, or evidence scope between the two backends.

The program preserves vertical completeness at every horizon. Broader operation
coverage is valuable only when every admitted operation has source semantics,
target numerics, neutral lowering, legal storage, causal execution, independent
checks, and retained reproducible evidence.
